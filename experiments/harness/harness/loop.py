"""The agent loop (DESIGN.md "Loop"): budget 30 tool calls / 60 000 generated tokens.

Stops when the model replies without a tool call, when the 30th tool call has been
processed, or when cumulative generated tokens reach 60 000 (checked after each model
turn). Every model message, tool call, verdict and tool result is appended to the audit
log. Tool calls are counted whether the cage allows them or not; a tool call whose
arguments are not valid JSON is counted, answered with an error, and not shown to the cage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .audit import AuditLog
from .llm import ChatResponse
from .prompts import initial_messages
from .tools import TOOL_SCHEMAS, ToolResult
from .types import AbstractState, Action, Verdict

MAX_TOOL_CALLS = 30
MAX_GEN_TOKENS = 60_000
AUDIT_OUTPUT_LIMIT = 4_000


class ChatClient(Protocol):
    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], seed: int) -> ChatResponse: ...


class Executor(Protocol):
    def classify(self, tool: str, args: dict[str, Any]) -> Action: ...
    def execute(self, action: Action) -> ToolResult: ...


class CageLike(Protocol):
    @property
    def name(self) -> str: ...
    def check(self, state: AbstractState, action: Action) -> Verdict: ...


@dataclass
class LoopResult:
    tool_calls: int = 0
    gen_tokens: int = 0
    budget_exhausted: bool = False
    final_message: str | None = None
    tokens_estimated: bool = False
    model_turns: int = 0
    messages: list[dict[str, Any]] = field(default_factory=list)


def run_loop(llm: ChatClient, executor: Executor, cage: CageLike, state: AbstractState, audit: AuditLog,
             system_prompt: str, seed: int, max_tool_calls: int = MAX_TOOL_CALLS,
             max_gen_tokens: int = MAX_GEN_TOKENS) -> LoopResult:
    res = LoopResult()
    messages: list[dict[str, Any]] = initial_messages(system_prompt)
    call_index = 0
    while True:
        resp = llm.chat(messages, TOOL_SCHEMAS, seed)
        res.model_turns += 1
        res.gen_tokens += resp.completion_tokens
        res.tokens_estimated |= resp.tokens_estimated
        res.final_message = resp.content
        audit.append("model", {"turn": res.model_turns, "content": resp.content,
                               "tool_calls": [{"id": c.id, "name": c.name, "arguments": c.raw_arguments} for c in resp.tool_calls],
                               "completion_tokens": resp.completion_tokens, "tokens_estimated": resp.tokens_estimated,
                               "gen_tokens_total": res.gen_tokens})
        messages.append(resp.raw_message or {"role": "assistant", "content": resp.content})
        if not resp.tool_calls:
            break
        stop = False
        for tc in resp.tool_calls:
            call_index += 1
            res.tool_calls += 1
            state.tool_calls += 1
            if tc.parse_error or tc.name not in {t["function"]["name"] for t in TOOL_SCHEMAS}:
                output = f"error: {tc.parse_error or 'unknown tool ' + tc.name}"
                audit.append("tool_call", {"call": call_index, "id": tc.id, "tool": tc.name, "args": tc.arguments,
                                           "klass": None, "paths": [], "error": output})
                audit.append("tool_result", {"call": call_index, "blocked": False, "invalid": True, "rc": None,
                                             "output": output})
            else:
                action = executor.classify(tc.name, tc.arguments)
                audit.append("tool_call", {"call": call_index, "id": tc.id, "tool": action.tool,
                                           "args": _args_for_audit(action), "klass": action.klass, "paths": list(action.paths)})
                verdict = cage.check(state, action)
                audit.append("verdict", {"call": call_index, "allowed": verdict.allowed, "cage": verdict.cage,
                                         "reason": verdict.reason, "tool": action.tool, "klass": action.klass,
                                         "paths": list(action.paths)})
                if verdict.allowed:
                    result = executor.execute(action)
                    output, rc, blocked = result.output, result.rc, False
                else:
                    output, rc, blocked = f"blocked by cage {verdict.cage}: {verdict.reason}", None, True
                audit.append("tool_result", {"call": call_index, "blocked": blocked, "rc": rc,
                                             "output": output[:AUDIT_OUTPUT_LIMIT], "tool": action.tool, "klass": action.klass})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})
            if res.tool_calls >= max_tool_calls:
                res.budget_exhausted = True
                stop = True
                break
        if stop:
            break
        if res.gen_tokens >= max_gen_tokens:
            res.budget_exhausted = True
            break
    audit.append("final", {"content": res.final_message, "tool_calls": res.tool_calls, "gen_tokens": res.gen_tokens,
                           "budget_exhausted": res.budget_exhausted, "tokens_estimated": res.tokens_estimated})
    res.messages = messages
    return res


def _args_for_audit(action: Action) -> dict[str, Any]:
    args = dict(action.args)
    if "content" in args and isinstance(args["content"], str):
        args["content_len"] = len(args["content"])
        args["content"] = args["content"][:AUDIT_OUTPUT_LIMIT]
    return args
