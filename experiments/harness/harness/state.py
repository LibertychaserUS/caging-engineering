"""AbstractState tracker, updated by the tool layer after each executed action (DESIGN.md "Tools").

Rules (choices where the design is silent are marked *):
- solution: after any executed write_file or run_shell, the stub module(s) are re-read from
  the container; content equal to the original stub -> "no"; differing but still containing a
  `pass` line or `NotImplementedError` -> "partial"; else "yes". With several stub files the
  weakest status wins (*).
- tests_run_since_write: True after an executed run_tests_tool or shell_tests; False after any
  executed write-class action or whenever the stub content changed (*).
- cwd: a leading `cd <path>` (the whole command, or followed by && / ;) that exits 0 moves the
  tracked cwd; nothing else does (*). cwd_in_dir follows.
- tool_calls: incremented by the loop for every tool call the model makes, blocked or not (*).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Literal

from .tools import ClassifyContext, ToolResult, resolve
from .types import AbstractState, Action, WRITE_CLASSES

_STUB_MARK_RE = re.compile(r"^\s*pass\s*(#.*)?$|NotImplementedError", re.M)
_LEADING_CD_RE = re.compile(r"^\s*cd\s+(\S+)\s*(?:$|&&|;)")


def solution_status(original: str, current: str | None) -> Literal["no", "partial", "yes"]:
    if current is None or current == original:
        return "no"
    return "partial" if _STUB_MARK_RE.search(current) else "yes"


@dataclass
class StateTracker:
    exercise_dir: str
    test_files: tuple[str, ...]
    stub_files: tuple[str, ...]
    stub_originals: dict[str, str]
    cwd: str = ""
    state: AbstractState = field(default_factory=AbstractState)
    _last_stub: dict[str, str | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.cwd:
            self.cwd = self.exercise_dir
        self._last_stub = {p: self.stub_originals.get(p) for p in self.stub_files}
        self.state.cwd_in_dir = self.ctx().in_dir(self.cwd)

    def ctx(self) -> ClassifyContext:
        return ClassifyContext(self.exercise_dir, self.test_files, self.stub_files, self.cwd)

    def after_execute(self, action: Action, result: ToolResult, read: Callable[[str], str | None]) -> None:
        if action.klass in WRITE_CLASSES:
            self.state.tests_run_since_write = False
        if action.tool in ("write_file", "run_shell"):
            changed = False
            statuses: list[Literal["no", "partial", "yes"]] = []
            for p in self.stub_files:
                cur = read(p)
                if cur != self._last_stub.get(p):
                    changed = True
                    self._last_stub[p] = cur
                statuses.append(solution_status(self.stub_originals.get(p, ""), cur))
            if statuses:
                order = {"no": 0, "partial": 1, "yes": 2}
                self.state.solution = min(statuses, key=lambda s: order[s])
            if changed:
                self.state.tests_run_since_write = False
        if action.klass in ("run_tests_tool", "shell_tests") and result.rc is not None:
            self.state.tests_run_since_write = True
        if action.tool == "run_shell" and result.rc == 0:
            m = _LEADING_CD_RE.match(str(action.args.get("command", "")))
            if m:
                self.cwd = resolve(m.group(1), self.cwd)
                self.state.cwd_in_dir = self.ctx().in_dir(self.cwd)
