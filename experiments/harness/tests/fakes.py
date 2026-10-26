"""Fakes shared by the loop / adjudication / memory tests: no Docker, no model."""
from __future__ import annotations

from typing import Any, Callable

from harness.llm import ChatResponse, ToolCall
from harness.tools import ClassifyContext, ToolResult, classify
from harness.types import Action

from conftest import EXERCISE_DIR, STUB_FILE, TEST_FILE


def tc(name: str, args: dict[str, Any], i: int = 0) -> ToolCall:
    import json
    raw = json.dumps(args)
    return ToolCall(f"call_{i}", name, args, raw)


def response(content: str | None, calls: list[ToolCall], tokens: int = 10, estimated: bool = False) -> ChatResponse:
    msg = {"role": "assistant", "content": content,
           "tool_calls": [{"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.raw_arguments}} for c in calls]}
    return ChatResponse(content, calls, tokens, estimated, msg)


class ScriptedLLM:
    """Returns the scripted responses in order; after the script is exhausted, repeats `default`."""

    def __init__(self, script: list[ChatResponse], default: Callable[[int], ChatResponse] | None = None) -> None:
        self.script = list(script)
        self.default = default
        self.turns = 0
        self.seen_messages: list[list[dict[str, Any]]] = []

    def chat(self, messages, tools, seed) -> ChatResponse:
        self.seen_messages.append(list(messages))
        self.turns += 1
        if self.script:
            return self.script.pop(0)
        if self.default is None:
            return response("done", [])
        return self.default(self.turns)


class FakeExecutor:
    """Classifies for real; 'executes' by recording and returning a canned result (rc from `rcs`)."""

    def __init__(self, cwd: str = EXERCISE_DIR, rcs: dict[str, int] | None = None) -> None:
        self.ctx = ClassifyContext(EXERCISE_DIR, (TEST_FILE,), (STUB_FILE,), cwd)
        self.executed: list[Action] = []
        self.rcs = rcs or {}

    def classify(self, tool: str, args: dict[str, Any]) -> Action:
        return classify(tool, args, self.ctx)

    def execute(self, action: Action) -> ToolResult:
        self.executed.append(action)
        rc = self.rcs.get(action.klass, 0)
        return ToolResult(f"ok ({action.klass})", rc, rc == 0)
