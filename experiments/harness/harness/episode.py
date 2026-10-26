"""run_episode(spec) -> EpisodeRecord (DESIGN.md "episode.py").

Staging: as make_manifest.py, the container receives every regular top-level file of the
exercise (stub, visible tests, support modules) and nothing from the dot-directories; the
official example therefore never enters the container. The instruction text is
.docs/introduction.md + .docs/instructions.md + .docs/instructions.append.md (those that
exist), inserted verbatim into the system prompt. Solution and test file names come from
the manifest's `exercise_files` when given, else from .meta/config.json.
"""
from __future__ import annotations

import json
import posixpath
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adjudicate import adjudicate, goal_in_fresh_container
from .audit import AuditLog, read as read_audit
from .cage import Cage
from .container import Container, sha256_file
from .llm import LLMClient
from .loop import run_loop
from .memory import EpisodeMemory
from .prompts import build_system_prompt
from .state import StateTracker
from .tools import ToolExecutor
from .types import EpisodeRecord, HarnessError

INSTRUCTION_FILES = ("introduction.md", "instructions.md", "instructions.append.md")


@dataclass(frozen=True)
class Exercise:
    slug: str
    src_dir: Path
    solution: tuple[str, ...]   # relative paths of the stub module(s)
    test: tuple[str, ...]       # relative paths of the visible test file(s)
    instructions: str

    @classmethod
    def load(cls, exercism_dir: Path, slug: str, files: dict[str, Any] | None = None) -> "Exercise":
        src = exercism_dir / "exercises" / "practice" / slug
        if not src.is_dir():
            raise HarnessError(f"exercise directory not found: {src}")
        if files is None:
            files = json.loads((src / ".meta" / "config.json").read_text(encoding="utf-8"))["files"]
        docs = src / ".docs"
        text = "\n\n".join((docs / n).read_text(encoding="utf-8").strip() for n in INSTRUCTION_FILES if (docs / n).exists())
        if not text:
            raise HarnessError(f"no instructions for {slug}")
        return cls(slug, src, tuple(files["solution"]), tuple(files["test"]), text)

    def stage(self, dst: Path) -> None:
        dst.mkdir(parents=True, exist_ok=True)
        for p in self.src_dir.iterdir():
            if p.is_file() and not p.name.startswith("."):
                shutil.copy(p, dst / p.name)


@dataclass(frozen=True)
class EpisodeSpec:
    episode_id: str
    exercise: str
    condition: str
    cage: Cage
    seed: int
    model: str
    memory: str = "M0"
    memory_prefix: str = ""


def run_episode(spec: EpisodeSpec, ex: Exercise, llm: LLMClient, out_dir: Path,
                image: str | None = None) -> tuple[EpisodeRecord, EpisodeMemory]:
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_path = out_dir / "audit" / f"{spec.episode_id}.jsonl"
    diff_path = out_dir / "diff" / f"{spec.episode_id}.json"
    final_dir = out_dir / "final" / spec.episode_id
    if audit_path.exists():
        audit_path.unlink()  # a retry starts a fresh chain
    workdir = f"/work/{ex.slug}"
    test_abs = [posixpath.join(workdir, t) for t in ex.test]
    stub_abs = [posixpath.join(workdir, s) for s in ex.solution]

    with tempfile.TemporaryDirectory(prefix="ce-stage-") as tmp:
        stage = Path(tmp) / ex.slug
        ex.stage(stage)
        hashes_before = {posixpath.join(workdir, t): sha256_file(stage / t) for t in ex.test}
        stub_originals = {posixpath.join(workdir, s): (stage / s).read_text(encoding="utf-8") for s in ex.solution
                          if (stage / s).exists()}
        container = Container.start(stage, ex.slug, image)
        try:
            tracker = StateTracker(workdir, tuple(test_abs), tuple(stub_abs), stub_originals)
            executor = ToolExecutor(container, tracker)
            system_prompt = build_system_prompt(ex.instructions, spec.memory_prefix)
            with AuditLog(audit_path) as audit:
                loop = run_loop(llm, executor, spec.cage, tracker.state, audit, system_prompt, spec.seed)
                diff = container.diff()
                hashes_after = container.hash_files(test_abs)
                container.copy_out(workdir, final_dir)
                adj = adjudicate(diff=diff, exercise_dir=workdir, test_hashes_before=hashes_before,
                                 test_hashes_after=hashes_after, audit_records=read_audit(audit_path),
                                 final_message=loop.final_message)
                goal = goal_in_fresh_container(final_dir, ex.slug, list(ex.test), ex.src_dir, image)
                audit.append("adjudication", {"goal": goal, "u_entries": adj.u_entries, "u_attempts": adj.u_attempts,
                                              "final_claim_pass": adj.final_claim_pass, "test_runs": adj.test_runs,
                                              "outside": adj.outside, "changed_tests": adj.changed_tests})
        finally:
            container.stop()

    diff_path.parent.mkdir(parents=True, exist_ok=True)
    diff_path.write_text(json.dumps({"diff": diff, "test_hashes_before": hashes_before,
                                     "test_hashes_after": hashes_after, "outside": adj.outside}, indent=1))
    record = EpisodeRecord(
        episode_id=spec.episode_id, exercise=ex.slug, model=spec.model, condition=spec.condition, seed=spec.seed,
        memory=spec.memory, goal=goal, u_entries=adj.u_entries, u_attempts=adj.u_attempts,
        tool_calls=loop.tool_calls, gen_tokens=loop.gen_tokens, budget_exhausted=loop.budget_exhausted,
        final_claim_pass=adj.final_claim_pass, audit_path=str(audit_path), diff_path=str(diff_path),
        harness_error=None, tokens_estimated=loop.tokens_estimated)
    mem = EpisodeMemory.from_audit(ex.slug, workdir, goal, read_audit(audit_path))
    return record, mem


def failed_record(spec: EpisodeSpec, error: str, out_dir: Path) -> EpisodeRecord:
    return EpisodeRecord(
        episode_id=spec.episode_id, exercise=spec.exercise, model=spec.model, condition=spec.condition, seed=spec.seed,
        memory=spec.memory, goal=None, u_entries={}, u_attempts={}, tool_calls=0, gen_tokens=0, budget_exhausted=False,
        final_claim_pass=None, audit_path=str(out_dir / "audit" / f"{spec.episode_id}.jsonl"),
        diff_path="", harness_error=error)
