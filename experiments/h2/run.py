"""H2 pipeline CLI.  Subcommands, in order: propose, truth, gates, analyze.

Every step is resumable (task_ids already in its output file are skipped).
Endpoints come from the environment only (CE_LLM_* for the proposer,
CE_JUDGE_* for the judge); keys are never printed or stored.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from h2 import analyze as an
from h2.data import datasets_for, load_problems
from h2.gates import run_gate_e, run_judge_gates
from h2.ground_truth import run_truth
from h2.llm import LLMClient, config_from_env
from h2.propose import run_propose


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _problems(args) -> dict[str, dict]:
    out = {}
    for ds in datasets_for(args.dataset):
        ps = load_problems(ds)
        if args.limit:
            ps = dict(list(ps.items())[: args.limit])
            log(f"[{ds}] --limit {args.limit}: pipeline check only; not an analysis run")
        out[ds] = ps
    return out


def _flat(by_ds: dict[str, dict]) -> dict:
    flat = {}
    for ps in by_ds.values():
        flat.update(ps)
    return flat


def _meta(out: Path, **kv) -> None:
    p = out / "meta.json"
    data = json.loads(p.read_text()) if p.exists() else {}
    data.update(kv)
    out.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))


def cmd_propose(args) -> None:
    client = LLMClient(config_from_env("proposer"))
    _meta(args.out, proposer_model=client.model)
    try:
        done = run_propose(_flat(_problems(args)), args.out, client, log)
    finally:
        client.close()
    log(f"propose: new records {done}")


def cmd_truth(args) -> None:
    added = run_truth(_problems(args), args.out, parallel=args.parallel, log=log)
    log(f"truth: new records per dataset {added}")


def cmd_gates(args) -> None:
    problems = _flat(_problems(args))
    if not args.skip_e:
        n = run_gate_e(problems, args.out, log=log)
        log(f"gate E: new records {n}")
    if not args.skip_judge:
        client = LLMClient(config_from_env("judge"))
        _meta(args.out, **{f"judge_model_{args.judge_tag}": client.model})
        try:
            n = run_judge_gates(problems, args.out, args.judge_tag, client, log)
        finally:
            client.close()
        log(f"judge gates ({args.judge_tag}): new records {n}")


def cmd_analyze(args) -> None:
    tags = args.judge_tag or sorted(p.stem[len("gates_"):] for p in Path(args.out).glob("gates_*.jsonl"))
    if not tags:
        sys.exit("analyze: no gates_<judge-tag>.jsonl found; run `gates` first")
    result = an.analyze(args.out, tags, args.primary_judge)
    jp, mp = an.write_outputs(result, args.out)
    log(f"analyze: wrote {jp} and {mp}")
    for tag, j in result["judges"].items():
        log(f"  {tag}: {j['decision']['verdict']} (hidden failures {j['decision']['n_hidden_fail']})")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="h2", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--dataset", default="both", choices=["humaneval", "mbpp", "both"])
        p.add_argument("--out", type=Path, required=True, help="results/h2/<proposer-tag>/")
        p.add_argument("--limit", type=int, default=0, help="first N problems per dataset (pipeline checks only)")

    p = sub.add_parser("propose", help="proposals, gate A self-report, arguments (proposer endpoint)")
    common(p); p.set_defaults(fn=cmd_propose)
    p = sub.add_parser("truth", help="hidden-test ground truth via evalplus.evaluate")
    common(p); p.add_argument("--parallel", type=int, default=4); p.set_defaults(fn=cmd_truth)
    p = sub.add_parser("gates", help="gate E (docker) and judge gates B, C, D (judge endpoint)")
    common(p)
    p.add_argument("--judge-tag", default="primary", help="label for this judge's output file")
    p.add_argument("--skip-e", action="store_true"); p.add_argument("--skip-judge", action="store_true")
    p.set_defaults(fn=cmd_gates)
    p = sub.add_parser("analyze", help="rates, intervals, precondition, verdict")
    common(p)
    p.add_argument("--judge-tag", action="append", help="restrict to these judge tags (default: all found)")
    p.add_argument("--primary-judge", default="primary")
    p.set_defaults(fn=cmd_analyze)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
