"""OpenAI-compatible chat completions with tool calls (DESIGN.md "llm.py").

Reads CE_LLM_BASE_URL, CE_LLM_MODEL, CE_LLM_API_KEY from the environment; none of them is
ever written to disk. Sends `tools`, `tool_choice="auto"`, `temperature`, `top_p`, `seed`.
Counts `usage.completion_tokens` when the server returns it; otherwise estimates
len(text)/4 and marks the response `tokens_estimated=True`. 5xx responses, timeouts and
connection errors are retried three times with backoff (1, 2, 4 s); a persistent failure,
or any 4xx, raises HarnessError.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from .types import HarnessError

RETRIES = 3
BACKOFF_S: tuple[float, ...] = (1.0, 2.0, 4.0)


def estimate_tokens(text: str) -> int:
    """Rough token count used when the server reports no usage: one token per 4 characters."""
    return (len(text) + 3) // 4


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str
    api_key: str = ""
    temperature: float = 0.3
    top_p: float = 0.95
    timeout_s: float = 180.0

    @classmethod
    def from_env(cls, temperature: float = 0.3, top_p: float = 0.95) -> "LLMConfig":
        base = os.environ.get("CE_LLM_BASE_URL", "").rstrip("/")
        model = os.environ.get("CE_LLM_MODEL", "")
        if not base or not model:
            raise HarnessError("CE_LLM_BASE_URL and CE_LLM_MODEL must be set")
        return cls(base, model, os.environ.get("CE_LLM_API_KEY", ""), temperature, top_p)


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    raw_arguments: str
    parse_error: str | None = None


@dataclass
class ChatResponse:
    content: str | None
    tool_calls: list[ToolCall]
    completion_tokens: int
    tokens_estimated: bool
    raw_message: dict[str, Any] = field(default_factory=dict)  # appended verbatim to the conversation


def parse_message(message: dict[str, Any], usage: dict[str, Any] | None) -> ChatResponse:
    calls: list[ToolCall] = []
    for i, tc in enumerate(message.get("tool_calls") or []):
        fn = tc.get("function") or {}
        raw = fn.get("arguments") or "{}"
        if not isinstance(raw, str):
            raw = json.dumps(raw)
        try:
            args = json.loads(raw) if raw.strip() else {}
            err = None if isinstance(args, dict) else "arguments are not an object"
            if err:
                args = {}
        except json.JSONDecodeError as e:
            args, err = {}, f"invalid JSON arguments: {e.msg}"
        calls.append(ToolCall(str(tc.get("id") or f"call_{i}"), str(fn.get("name", "")), args, raw, err))
    content = message.get("content")
    if isinstance(content, list):  # some servers return content parts
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    if usage and isinstance(usage.get("completion_tokens"), int):
        return ChatResponse(content, calls, usage["completion_tokens"], False, message)
    text = (content or "") + "".join(c.raw_arguments + c.name for c in calls)
    return ChatResponse(content, calls, estimate_tokens(text), True, message)


class LLMClient:
    def __init__(self, cfg: LLMConfig, client: httpx.Client | None = None) -> None:
        self.cfg = cfg
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        self._client = client or httpx.Client(base_url=cfg.base_url, headers=headers, timeout=cfg.timeout_s)

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], seed: int) -> ChatResponse:
        body = {
            "model": self.cfg.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": self.cfg.temperature,
            "top_p": self.cfg.top_p,
            "seed": seed,
        }
        last: str = ""
        for attempt in range(RETRIES + 1):
            try:
                r = self._client.post("/v1/chat/completions", json=body)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last = f"{type(e).__name__}: {e}"
            else:
                if r.status_code < 400:
                    try:
                        data = r.json()
                        return parse_message(data["choices"][0]["message"], data.get("usage"))
                    except (KeyError, IndexError, ValueError) as e:
                        raise HarnessError(f"malformed chat completion: {e}") from e
                if r.status_code < 500:
                    raise HarnessError(f"chat completion rejected: HTTP {r.status_code} {r.text[:300]}")
                last = f"HTTP {r.status_code}"
            if attempt < RETRIES:
                time.sleep(BACKOFF_S[min(attempt, len(BACKOFF_S) - 1)])
        raise HarnessError(f"chat completion failed after {RETRIES + 1} attempts: {last}")

    def close(self) -> None:
        self._client.close()
