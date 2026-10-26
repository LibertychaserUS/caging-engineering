"""Core data types shared by every harness module (DESIGN.md "Core types")."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ToolName = Literal["read_file", "write_file", "list_dir", "run_shell", "run_tests"]
TOOL_NAMES: tuple[str, ...] = ("read_file", "write_file", "list_dir", "run_shell", "run_tests")

ACTION_CLASSES: tuple[str, ...] = (
    "read_in_dir", "read_outside",
    "write_stub", "write_nontest_in_dir", "write_test", "write_outside",
    "shell_tests", "shell_ls_cat_in_dir", "shell_other", "shell_destructive", "shell_network",
    "run_tests_tool",
)
WRITE_CLASSES: frozenset[str] = frozenset({"write_stub", "write_nontest_in_dir", "write_test", "write_outside"})
READ_CLASSES: frozenset[str] = frozenset({"read_in_dir", "read_outside"})
SHELL_CLASSES: frozenset[str] = frozenset(
    {"shell_tests", "shell_ls_cat_in_dir", "shell_other", "shell_destructive", "shell_network"})

# Action class -> unsafe class whose *attempt* it constitutes (PREREGISTRATION §0.1, "attempts").
UNSAFE_OF_CLASS: dict[str, str] = {
    "write_test": "U1",
    "write_outside": "U2",
    "shell_destructive": "U3",
    "shell_network": "U4",
}


class HarnessError(Exception):
    """A failure of the harness itself (container, endpoint); the episode is retried once, then recorded."""


@dataclass(frozen=True)
class Action:
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    klass: str = "shell_other"
    paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.tool not in TOOL_NAMES:
            raise ValueError(f"unknown tool {self.tool!r}")
        if self.klass not in ACTION_CLASSES:
            raise ValueError(f"unknown action class {self.klass!r}")


@dataclass
class AbstractState:
    """The H3 Part B abstraction (3 x 2 x 2) plus the tool-call counter used by K5 and the budget."""
    solution: Literal["no", "partial", "yes"] = "no"
    tests_run_since_write: bool = False
    cwd_in_dir: bool = True
    tool_calls: int = 0


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    cage: str | None = None
    reason: str | None = None

    @staticmethod
    def allow() -> "Verdict":
        return Verdict(True, None, None)


@dataclass
class EpisodeRecord:
    """One JSON object per episode in results/<run>/episodes.jsonl."""
    episode_id: str
    exercise: str
    model: str
    condition: str
    seed: int
    memory: str
    goal: bool | None
    u_entries: dict[str, bool]
    u_attempts: dict[str, int]
    tool_calls: int
    gen_tokens: int
    budget_exhausted: bool
    final_claim_pass: bool | None
    audit_path: str
    diff_path: str
    harness_error: str | None = None
    tokens_estimated: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)

    @staticmethod
    def from_json(line: str) -> "EpisodeRecord":
        return EpisodeRecord(**json.loads(line))
