"""Batch runner (DESIGN.md "Runner").

    python -m harness.runner --hypothesis h1 --model primary --seeds 1 2 3 --out results/h1/ --parallel 4

Conditions: h1 -> L0..L6 over all admitted exercises x seeds; h3 -> the 6 singletons and 15
pairs of K1..K6 on h3_subset_80 and the 20 triples on h3_subset_40 (names "K1", "K1+K2",
"K1+K2+K3"), first seed only; h4 -> L3 with memory M0..M3 over each of h4_orders, episodes
of a sequence run in order (episode t+1 receives the memory built from episodes 1..t).
Resume: episode ids already in episodes.jsonl are skipped (for h4 their memory is rebuilt
from the stored audit logs). A HarnessError is retried once with the same seed; a second
failure is recorded in episodes.jsonl with `harness_error` and appended to the manifest's
`harness_failures`. The exercism checkout is given by --exercism-dir or env CE_EXERCISM_DIR.
--dry-run prints the plan (episode counts per condition) and exits; exit code 2 when a
needed manifest field is still null. --exercises restricts the plan (smoke tests only).
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import read as read_audit
from .cage import LADDER, LIBRARY, by_name
from .episode import EpisodeSpec, Exercise, failed_record, run_episode
from .llm import LLMClient, LLMConfig
from .memory import MEMORY_CONDITIONS, EpisodeMemory
from .types import EpisodeRecord, HarnessError

HYPOTHESES = ("h1", "h3", "h4")
H3_SIZES = {1: "h3_subset_80", 2: "h3_subset_80", 3: "h3_subset_40"}


@dataclass(frozen=True)
class PlannedEpisode:
    episode_id: str
    exercise: str
    condition: str
    seed: int
    memory: str = "M0"


Sequence = list[PlannedEpisode]   # episodes that must run in order (length 1 outside h4)


def h3_conditions() -> list[str]:
    names = sorted(LIBRARY)
    return ["+".join(c) for k in (1, 2, 3) for c in itertools.combinations(names, k)]


def plan(manifest: dict[str, Any], hypothesis: str, seeds: list[int], model_label: str,
         only: set[str] | None = None) -> list[Sequence]:
    def ok(ex: str) -> bool:
        return only is None or ex in only

    if hypothesis == "h1":
        exercises = require(manifest, "admitted_exercises")
        if only is not None:
            # Smoke runs may name the manifest's smoke-test exercises, which are never admitted.
            exercises = sorted(set(exercises) | (set(manifest.get("smoke_test_exercises", [])) & only))
        return [[PlannedEpisode(f"h1-{lvl}-{ex}-s{seed}", ex, lvl, seed)]
                for lvl in LADDER for ex in exercises if ok(ex) for seed in seeds]
    if hypothesis == "h3":
        subsets = {k: require(manifest, k) for k in set(H3_SIZES.values())}
        seed = seeds[0]
        return [[PlannedEpisode(f"h3-{cond}-{ex}-s{seed}", ex, cond, seed)]
                for cond in h3_conditions() for ex in subsets[H3_SIZES[cond.count('+') + 1]] if ok(ex)]
    if hypothesis == "h4":
        orders = require(manifest, "h4_orders")
        seed = seeds[0]
        seqs: list[Sequence] = []
        for oi, order in enumerate(orders):
            for mem in MEMORY_CONDITIONS:
                seqs.append([PlannedEpisode(f"h4-L3-{mem}-o{oi}-t{t + 1:02d}-{ex}-s{seed}", ex, "L3", seed, mem)
                             for t, ex in enumerate(order) if ok(ex)])
        return [s for s in seqs if s]
    raise ValueError(hypothesis)


def require(manifest: dict[str, Any], key: str) -> Any:
    v = manifest.get(key)
    if v is None:
        raise HarnessError(f"manifest field {key!r} is still null; run make_manifest.py first")
    return v


def summarize(seqs: list[Sequence]) -> str:
    counts = Counter((e.condition, e.memory) for s in seqs for e in s)
    lines = [f"  {cond:<10} {mem:<4} {n:>5}" for (cond, mem), n in sorted(counts.items())]
    total = sum(counts.values())
    return "\n".join(["  condition  mem  episodes", *lines, f"  total            {total:>5} in {len(seqs)} sequence(s)"])


class Runner:
    def __init__(self, a: argparse.Namespace) -> None:
        self.a = a
        self.manifest_path = Path(a.manifest)
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.out = Path(a.out)
        self.lock = threading.Lock()
        self.exercism_dir = Path(a.exercism_dir or os.environ.get("CE_EXERCISM_DIR", ""))
        self.done: dict[str, EpisodeRecord] = {}
        ep_path = self.out / "episodes.jsonl"
        if ep_path.exists():
            for line in ep_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = EpisodeRecord.from_json(line)
                    self.done[r.episode_id] = r
        self.llm: LLMClient | None = None

    def exercise(self, slug: str) -> Exercise:
        files = (self.manifest.get("exercise_files") or {}).get(slug)
        return Exercise.load(self.exercism_dir, slug, files)

    def record(self, rec: EpisodeRecord) -> None:
        with self.lock:
            with (self.out / "episodes.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(rec.to_json() + "\n")
            self.done[rec.episode_id] = rec
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {rec.episode_id} goal={rec.goal} "
                  f"entries={[k for k, v in rec.u_entries.items() if v]} attempts={rec.u_attempts} "
                  f"calls={rec.tool_calls} tokens={rec.gen_tokens}" + (f" ERROR={rec.harness_error}" if rec.harness_error else ""),
                  flush=True)

    def record_failure(self, spec: EpisodeSpec, error: str) -> None:
        rec = failed_record(spec, error, self.out)
        self.record(rec)
        with self.lock:
            m = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            m.setdefault("harness_failures", []).append(
                {"episode_id": spec.episode_id, "exercise": spec.exercise, "condition": spec.condition,
                 "seed": spec.seed, "memory": spec.memory, "error": error[:300],
                 "date": datetime.now(timezone.utc).date().isoformat()})
            self.manifest_path.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def run_sequence(self, seq: Sequence) -> None:
        assert self.llm is not None
        history: list[EpisodeMemory] = []
        for p in seq:
            ex = self.exercise(p.exercise)
            if p.episode_id in self.done:
                prev = self.done[p.episode_id]
                if prev.harness_error is None and Path(prev.audit_path).exists():
                    history.append(EpisodeMemory.from_audit(ex.slug, f"/work/{ex.slug}", bool(prev.goal),
                                                            read_audit(prev.audit_path)))
                continue
            prefix = MEMORY_CONDITIONS[p.memory](history)
            spec = EpisodeSpec(p.episode_id, p.exercise, p.condition, by_name(p.condition), p.seed,
                               self.a.served_model, p.memory, prefix)
            mem: EpisodeMemory | None = None
            last_error = ""
            for attempt in range(2):
                try:
                    rec, mem = run_episode(spec, ex, self.llm, self.out)
                    self.record(rec)
                    break
                except HarnessError as e:
                    last_error = str(e)
                    print(f"harness error on {p.episode_id} (attempt {attempt + 1}): {last_error}", file=sys.stderr, flush=True)
            else:
                self.record_failure(spec, last_error)
            if mem is not None:
                history.append(mem)

    def run(self, seqs: list[Sequence]) -> int:
        self.out.mkdir(parents=True, exist_ok=True)
        cfg = LLMConfig.from_env()
        self.a.served_model = cfg.model
        self.llm = LLMClient(cfg)
        role = self.manifest["sources"]["models"][f"agent_{self.a.model}"]
        (self.out / "run.json").write_text(json.dumps({
            "hypothesis": self.a.hypothesis, "model_role": self.a.model, "hf_id": role.get("hf_id"),
            "served_model": cfg.model, "seeds": self.a.seeds, "temperature": cfg.temperature, "top_p": cfg.top_p,
            "started": datetime.now(timezone.utc).isoformat(),
            "preregistration_commit": self.manifest.get("preregistration_commit")}, indent=2) + "\n")
        pending = [s for s in seqs if any(e.episode_id not in self.done for e in s)]
        print(f"{sum(len(s) for s in seqs)} episodes planned, {len(self.done)} already recorded, "
              f"{len(pending)} sequence(s) to run with --parallel {self.a.parallel}", flush=True)
        try:
            with ThreadPoolExecutor(max_workers=self.a.parallel) as pool:
                list(pool.map(self.run_sequence, pending))
        finally:
            self.llm.close()
        failures = sum(1 for r in self.done.values() if r.harness_error)
        print(f"done: {len(self.done)} recorded, {failures} harness failure(s)")
        return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m harness.runner", description=__doc__.split("\n\n")[0])
    ap.add_argument("--hypothesis", required=True, choices=HYPOTHESES)
    ap.add_argument("--model", default="primary", choices=("primary", "secondary"))
    ap.add_argument("--seeds", type=int, nargs="+", default=[1])
    ap.add_argument("--out", required=True)
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--manifest", default=str(Path(__file__).resolve().parents[2] / "manifest.json"))
    ap.add_argument("--exercism-dir", default=None)
    ap.add_argument("--exercises", nargs="*", default=None, help="restrict the plan (smoke tests only)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    a.served_model = ""

    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    try:
        seqs = plan(manifest, a.hypothesis, a.seeds, a.model, set(a.exercises) if a.exercises else None)
    except HarnessError as e:
        print(f"cannot plan {a.hypothesis}: {e}", file=sys.stderr)
        return 2
    print(f"plan for {a.hypothesis} (model {a.model}, seeds {a.seeds}):\n{summarize(seqs)}")
    if a.dry_run:
        return 0
    if not a.exercism_dir and not os.environ.get("CE_EXERCISM_DIR"):
        print("need --exercism-dir or CE_EXERCISM_DIR", file=sys.stderr)
        return 2
    return Runner(a).run(seqs)


if __name__ == "__main__":
    sys.exit(main())
