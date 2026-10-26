"""OpenAI-compatible chat completion over httpx.

Two endpoint sets, read from the environment and never written anywhere:
  proposer: CE_LLM_BASE_URL, CE_LLM_MODEL, CE_LLM_API_KEY
  judge:    CE_JUDGE_BASE_URL, CE_JUDGE_MODEL, CE_JUDGE_API_KEY
Retries with exponential backoff on transport errors, 408/429 and 5xx; raises
LLMError after the last attempt.  Error messages never include headers.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import httpx

ENV_PREFIX = {"proposer": "CE_LLM", "judge": "CE_JUDGE"}
RETRY_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str
    api_key: str = field(repr=False, default="")

    def __repr__(self) -> str:  # never leak the key
        return f"LLMConfig(model={self.model!r}, key={'set' if self.api_key else 'unset'})"


def config_from_env(role: str) -> LLMConfig:
    prefix = ENV_PREFIX[role]
    base_url = os.environ.get(f"{prefix}_BASE_URL", "")
    model = os.environ.get(f"{prefix}_MODEL", "")
    if not base_url or not model:
        raise LLMError(f"{prefix}_BASE_URL and {prefix}_MODEL must be set for the {role}")
    return LLMConfig(base_url=base_url.rstrip("/"), model=model, api_key=os.environ.get(f"{prefix}_API_KEY", ""))


@dataclass
class ChatResult:
    content: str
    finish_reason: str | None
    usage: dict[str, Any]
    model: str | None = None


class ChatFn(Protocol):
    """What propose.py and gates.py need: a callable with this signature.

    Fakes used in tests implement the same signature.
    """

    def __call__(self, messages: list[dict], *, temperature: float, seed: int, max_tokens: int) -> ChatResult: ...


class LLMClient:
    def __init__(self, cfg: LLMConfig, *, timeout: float = 180.0, max_retries: int = 5,
                 backoff: float = 1.0, transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        self.cfg = cfg
        self.max_retries = max_retries
        self.backoff = backoff
        self._sleep = sleep
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        self._client = httpx.Client(timeout=timeout, headers=headers, transport=transport)

    @property
    def model(self) -> str:
        return self.cfg.model

    def __call__(self, messages: list[dict], *, temperature: float = 0.0, seed: int = 0,
                 max_tokens: int = 1024) -> ChatResult:
        body = {
            "model": self.cfg.model,
            "messages": messages,
            "temperature": temperature,
            "seed": seed,
            "max_tokens": max_tokens,
            "stream": False,
        }
        url = f"{self.cfg.base_url}/chat/completions"
        last = "no attempt made"
        for attempt in range(1, self.max_retries + 1):
            try:
                r = self._client.post(url, json=body)
            except httpx.HTTPError as e:
                last = f"transport error: {type(e).__name__}"
            else:
                if r.status_code == 200:
                    return _parse(r.json())
                last = f"HTTP {r.status_code}: {r.text[:200]!r}"
                if r.status_code not in RETRY_STATUSES:
                    raise LLMError(f"chat completion failed ({last})")
            if attempt < self.max_retries:
                self._sleep(self.backoff * (2 ** (attempt - 1)))
        raise LLMError(f"chat completion failed after {self.max_retries} attempts ({last})")

    def close(self) -> None:
        self._client.close()


def _parse(data: dict) -> ChatResult:
    try:
        choice = data["choices"][0]
        msg = choice.get("message") or {}
        content = msg.get("content")
        if content is None:  # some servers put reasoning elsewhere; treat as empty answer
            content = ""
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"malformed chat completion response: {e}") from e
    return ChatResult(content=content, finish_reason=choice.get("finish_reason"),
                      usage=data.get("usage") or {}, model=data.get("model"))
