"""Proposals, gate A (self-report) and the proposer's argument for correctness.

Per problem three records are stored, each in its own resumable JSONL file:
  proposals.jsonl   task_id, dataset, prompt, raw, code, solution, usage, finish_reason
  self_report.jsonl task_id, raw, parsed, verdict             (gate A)
  arguments.jsonl   task_id, argument, usage                   (for gates C and D)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from .data import Problem, compose_solution
from .jsonl import append_jsonl, read_by_task
from .llm import ChatFn
from .prompts import SELF_REPORT_QUESTION, argue_prompt, propose_prompt

PROPOSAL_MAX_TOKENS = 1024
ARGUMENT_MAX_TOKENS = 400
SELF_REPORT_MAX_TOKENS = 1  # the first token is the answer (preregistration: single token)
SEED = 0
TEMPERATURE = 0.0

_FENCE = re.compile(r"```(?:[A-Za-z0-9_+-]*)[ \t]*\n(.*?)```", re.S)


def extract_code(raw: str, entry_point: str | None = None) -> str:
    """The code in the model's answer.

    First fenced block that defines the entry point, else the first fenced
    block, else the whole answer (the proposer was told to return only code).
    """
    blocks = [b for b in _FENCE.findall(raw)]
    if not blocks:
        # an unterminated fence: take everything after the opening fence
        m = re.search(r"```(?:[A-Za-z0-9_+-]*)[ \t]*\n(.*)$", raw, re.S)
        return (m.group(1) if m else raw).strip("\n")
    if entry_point:
        for b in blocks:
            if re.search(rf"^[ \t]*def\s+{re.escape(entry_point)}\s*\(", b, re.M):
                return b.strip("\n")
    return blocks[0].strip("\n")


def parse_yes_no(text: str) -> str:
    """'yes' | 'no' | 'unparseable' from the first token of an answer."""
    t = text.strip().lower().lstrip("*\"'`([ \t\n.:-")
    if t.startswith(("yes", "pass")):
        return "yes"
    if t.startswith(("no", "fail")):
        return "no"
    return "unparseable"


def verdict_from_parsed(parsed: str) -> str:
    """Preregistration rule: unparseable counts as pass."""
    return "fail" if parsed == "no" else "pass"


def propose_messages(problem: Problem) -> list[dict]:
    return [{"role": "user", "content": propose_prompt(problem.prompt)}]


def propose_one(problem: Problem, chat: ChatFn) -> dict:
    res = chat(propose_messages(problem), temperature=TEMPERATURE, seed=SEED, max_tokens=PROPOSAL_MAX_TOKENS)
    code = extract_code(res.content, problem.entry_point)
    return {
        "task_id": problem.task_id,
        "dataset": problem.dataset,
        "prompt": problem.prompt,
        "raw": res.content,
        "code": code,
        "solution": compose_solution(problem, code),
        "usage": res.usage,
        "finish_reason": res.finish_reason,
    }


def self_report_messages(problem: Problem, proposal: dict) -> list[dict]:
    """Gate A: the same context, the model's own answer appended, then the question."""
    return propose_messages(problem) + [
        {"role": "assistant", "content": proposal["raw"]},
        {"role": "user", "content": SELF_REPORT_QUESTION},
    ]


def self_report_one(problem: Problem, proposal: dict, chat: ChatFn) -> dict:
    res = chat(self_report_messages(problem, proposal), temperature=TEMPERATURE, seed=SEED,
               max_tokens=SELF_REPORT_MAX_TOKENS)
    parsed = parse_yes_no(res.content)
    return {"task_id": problem.task_id, "gate": "A", "raw": res.content, "parsed": parsed,
            "verdict": verdict_from_parsed(parsed), "usage": res.usage}


def argue_messages(problem: Problem, proposal: dict) -> list[dict]:
    """Fresh context: the proposer is instructed to argue for correctness."""
    return [{"role": "user", "content": argue_prompt(problem.prompt, proposal["solution"])}]


def argue_one(problem: Problem, proposal: dict, chat: ChatFn) -> dict:
    res = chat(argue_messages(problem, proposal), temperature=TEMPERATURE, seed=SEED, max_tokens=ARGUMENT_MAX_TOKENS)
    return {"task_id": problem.task_id, "argument": res.content.strip(), "usage": res.usage,
            "finish_reason": res.finish_reason}


def run_propose(problems: dict[str, Problem], out_dir: Path, chat: ChatFn,
                log: Callable[[str], None] = lambda s: None) -> dict[str, int]:
    """Resumable: a task already present in a file is not redone for that file."""
    out_dir = Path(out_dir)
    p_path, a_path, g_path = out_dir / "proposals.jsonl", out_dir / "arguments.jsonl", out_dir / "self_report.jsonl"
    proposals = read_by_task(p_path)
    arguments = read_by_task(a_path)
    reports = read_by_task(g_path)
    done = {"proposals": 0, "self_report": 0, "arguments": 0}
    for i, (tid, problem) in enumerate(problems.items(), 1):
        if tid not in proposals:
            proposals[tid] = propose_one(problem, chat)
            append_jsonl(p_path, proposals[tid])
            done["proposals"] += 1
        if tid not in reports:
            reports[tid] = self_report_one(problem, proposals[tid], chat)
            append_jsonl(g_path, reports[tid])
            done["self_report"] += 1
        if tid not in arguments:
            arguments[tid] = argue_one(problem, proposals[tid], chat)
            append_jsonl(a_path, arguments[tid])
            done["arguments"] += 1
        if i % 25 == 0:
            log(f"propose: {i}/{len(problems)}")
    return done
