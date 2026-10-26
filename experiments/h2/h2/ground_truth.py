"""Ground truth: pass/fail on the hidden EvalPlus tests (the non-persuadable adjudicator).

Exact command run per dataset (subprocess, same interpreter as this process):

    python -m evalplus.evaluate --dataset {humaneval|mbpp} \
        --samples <out>/samples_<dataset>.jsonl --parallel <n>

The samples file has one line per problem: {"task_id": ..., "solution": <full code>}.
EvalPlus writes <out>/samples_<dataset>_eval_results.json; a proposal passes
iff base_status == plus_status == "pass" (EvalPlus's own definition of
passing the "+" tests).  EvalPlus requires a sample for every problem of the
dataset, so `propose` must be complete before `truth`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

from .data import Problem
from .jsonl import append_jsonl, read_by_task, write_jsonl

PASS = "pass"


def samples_path(out_dir: Path, dataset: str) -> Path:
    return Path(out_dir) / f"samples_{dataset}.jsonl"


def results_path(samples: Path) -> Path:
    return Path(str(samples).replace(".jsonl", "_eval_results.json"))


def write_samples(problems: dict[str, Problem], proposals: dict[str, dict], path: Path) -> list[str]:
    """Write the EvalPlus samples file; returns the task_ids with no proposal (file not written if any)."""
    missing = [tid for tid in problems if tid not in proposals]
    if missing:
        return missing
    write_jsonl(path, ({"task_id": tid, "solution": proposals[tid]["solution"]} for tid in problems))
    return []


def evalplus_command(dataset: str, samples: Path, parallel: int) -> list[str]:
    return [sys.executable, "-m", "evalplus.evaluate", "--dataset", dataset,
            "--samples", str(samples), "--parallel", str(parallel)]


def run_evalplus(dataset: str, samples: Path, parallel: int = 4,
                 runner: Callable[[list[str]], int] = lambda cmd: subprocess.run(cmd, check=False).returncode) -> Path:
    """Run the EvalPlus CLI unless its results file already exists (resumable)."""
    rp = results_path(samples)
    if rp.exists():
        return rp
    rc = runner(evalplus_command(dataset, samples, parallel))
    if rc != 0 or not rp.exists():
        raise RuntimeError(f"evalplus.evaluate failed for {dataset} (rc={rc}); no results at {rp}")
    return rp


def parse_results(rp: Path) -> dict[str, dict]:
    """task_id -> {base_status, plus_status, hidden_pass} from EvalPlus's results JSON."""
    with open(rp, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for tid, entries in data["eval"].items():
        if not entries:
            continue
        e = entries[0]  # one proposal per problem
        base, plus = e.get("base_status"), e.get("plus_status")
        out[tid] = {"base_status": base, "plus_status": plus, "hidden_pass": base == PASS and plus == PASS}
    return out


def run_truth(problems_by_dataset: dict[str, dict[str, Problem]], out_dir: Path, parallel: int = 4,
              runner=None, log: Callable[[str], None] = lambda s: None) -> dict[str, int]:
    out_dir = Path(out_dir)
    proposals = read_by_task(out_dir / "proposals.jsonl")
    truth_path = out_dir / "truth.jsonl"
    truth = read_by_task(truth_path)
    added = {}
    for dataset, problems in problems_by_dataset.items():
        if all(tid in truth for tid in problems):
            added[dataset] = 0
            continue
        sp = samples_path(out_dir, dataset)
        missing = write_samples(problems, proposals, sp)
        if missing:
            raise RuntimeError(f"{dataset}: {len(missing)} problems have no proposal (first: {missing[:5]}); "
                               "run `propose` to completion first")
        kw = {} if runner is None else {"runner": runner}
        rp = run_evalplus(dataset, sp, parallel, **kw)
        log(f"truth: parsed {rp}")
        n = 0
        for tid, rec in parse_results(rp).items():
            if tid in truth or tid not in problems:
                continue
            truth[tid] = {"task_id": tid, "dataset": dataset, **rec}
            append_jsonl(truth_path, truth[tid])
            n += 1
        added[dataset] = n
    return added
