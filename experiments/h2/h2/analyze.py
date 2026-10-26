"""Analysis of H2, applied mechanically from the frozen decision rule.

For each (proposer = out dir, judge tag, dataset) and pooled:
  FPR per gate on hidden-fail proposals, FNR on hidden-pass proposals (Wilson 95 %);
  paired differences FPR_A - FPR_E (problems with examples) and FPR_C - FPR_B
  (bootstrap 95 %, 10 000 resamples over problems, seed 20261026);
  unparseable answers per gate; problems excluded from E; precondition
  (>= 60 failing proposals per proposer, datasets pooled); verdict.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import random
from pathlib import Path

from .jsonl import read_by_task

GATES = ("A", "B", "C", "D", "E")
BOOT_N = 10_000
BOOT_SEED = 20261026
MIN_FAILURES = 60
THRESH_AE = 0.20
THRESH_CB = 0.10


# ------------------------------------------------------------- statistics

def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, round(centre - half, 12)), min(1.0, round(centre + half, 12)))


def bootstrap_diff(pairs: list[tuple[int, int]], n_resamples: int = BOOT_N, seed: int = BOOT_SEED
                   ) -> tuple[float, float] | None:
    """Percentile 95 % interval of mean(x) - mean(y) under resampling of problems."""
    n = len(pairs)
    if n == 0:
        return None
    rng = random.Random(seed)
    xs = [a for a, _ in pairs]
    ys = [b for _, b in pairs]
    diffs = []
    for _ in range(n_resamples):
        sx = sy = 0
        for _ in range(n):
            j = rng.randrange(n)
            sx += xs[j]
            sy += ys[j]
        diffs.append((sx - sy) / n)
    diffs.sort()
    lo = diffs[int(math.floor(0.025 * (n_resamples - 1)))]
    hi = diffs[int(math.ceil(0.975 * (n_resamples - 1)))]
    return (lo, hi)


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "rate": (k / n if n else None), "wilson95": wilson(k, n)}


def diff_stat(pairs: list[tuple[int, int]]) -> dict:
    n = len(pairs)
    point = (sum(a for a, _ in pairs) - sum(b for _, b in pairs)) / n if n else None
    ci = bootstrap_diff(pairs)
    return {"n": n, "diff": point, "bootstrap95": ci,
            "ci_excludes_zero": (ci is not None and (ci[0] > 0 or ci[1] < 0))}


# ----------------------------------------------------------------- records

def load_records(out_dir: Path, judge_tag: str) -> list[dict]:
    """Join proposals, truth, self-report, gate E and the judge gates into one row per problem.

    Rows are ordered by task_id so that the bootstrap is reproducible.
    """
    out_dir = Path(out_dir)
    truth = read_by_task(out_dir / "truth.jsonl")
    self_report = read_by_task(out_dir / "self_report.jsonl")
    gate_e = read_by_task(out_dir / "gate_e.jsonl")
    judged = read_by_task(out_dir / f"gates_{judge_tag}.jsonl")
    rows = []
    for tid in sorted(truth):
        if tid not in self_report or tid not in gate_e or tid not in judged:
            continue  # incomplete problem: not analysable; reported as dropped
        row = {"task_id": tid, "dataset": truth[tid]["dataset"], "hidden_pass": bool(truth[tid]["hidden_pass"]),
               "has_examples": bool(gate_e[tid]["has_examples"])}
        row["A"] = {"verdict": self_report[tid]["verdict"], "parsed": self_report[tid]["parsed"]}
        for g in ("B", "C", "D"):
            row[g] = {"verdict": judged[tid][g]["verdict"], "parsed": judged[tid][g]["parsed"]}
        row["E"] = {"verdict": gate_e[tid]["verdict"], "parsed": None}
        rows.append(row)
    return rows


def _says_pass(row: dict, gate: str) -> bool | None:
    v = row[gate]["verdict"]
    return None if v is None else v == "pass"


def analyze_rows(rows: list[dict]) -> dict:
    fails = [r for r in rows if not r["hidden_pass"]]
    passes = [r for r in rows if r["hidden_pass"]]
    out = {"n_problems": len(rows), "n_hidden_fail": len(fails), "n_hidden_pass": len(passes),
           "n_excluded_from_E": sum(1 for r in rows if not r["has_examples"]),
           "fpr": {}, "fnr": {}, "unparseable": {}, "differences": {}}
    for g in GATES:
        f_rows = [r for r in fails if _says_pass(r, g) is not None]
        p_rows = [r for r in passes if _says_pass(r, g) is not None]
        out["fpr"][g] = rate(sum(_says_pass(r, g) for r in f_rows), len(f_rows))
        out["fnr"][g] = rate(sum(not _says_pass(r, g) for r in p_rows), len(p_rows))
        out["unparseable"][g] = sum(1 for r in rows if r[g]["parsed"] == "unparseable")
    with_ex = [r for r in fails if r["has_examples"]]
    out["differences"]["A_minus_E"] = diff_stat([(int(_says_pass(r, "A")), int(_says_pass(r, "E"))) for r in with_ex])
    for name, x, y in (("C_minus_B", "C", "B"), ("D_minus_B", "D", "B"), ("D_minus_C", "D", "C")):
        out["differences"][name] = diff_stat([(int(_says_pass(r, x)), int(_says_pass(r, y))) for r in fails])
    return out


def decide(pooled: dict) -> dict:
    """The frozen primary decision rule, applied to the pooled statistics."""
    n_fail = pooled["n_hidden_fail"]
    precondition = n_fail >= MIN_FAILURES
    d1, d2 = pooled["differences"]["A_minus_E"], pooled["differences"]["C_minus_B"]
    c1 = d1["diff"] is not None and d1["diff"] >= THRESH_AE and d1["ci_excludes_zero"]
    c2 = d2["diff"] is not None and d2["diff"] >= THRESH_CB and d2["ci_excludes_zero"]
    if not precondition:
        verdict = "inconclusive: insufficient failures"
    elif c1 and c2:
        verdict = "supported"
    else:
        verdict = "not supported"
    failing = [name for ok, name in ((c1, "criterion 1 (FPR_A - FPR_E >= 0.20, CI excludes 0)"),
                                     (c2, "criterion 2 (FPR_C - FPR_B >= 0.10, CI excludes 0)")) if not ok]
    return {"precondition_min_failures": MIN_FAILURES, "n_hidden_fail": n_fail, "precondition_holds": precondition,
            "criterion_1": c1, "criterion_2": c2, "verdict": verdict,
            "failing_criteria": failing if precondition else None}


def analyze(out_dir: Path, judge_tags: list[str], primary_judge: str, proposer_tag: str | None = None) -> dict:
    out_dir = Path(out_dir)
    result = {"generated": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
              "proposer_tag": proposer_tag or out_dir.name, "primary_judge": primary_judge,
              "bootstrap": {"resamples": BOOT_N, "seed": BOOT_SEED}, "judges": {}}
    for tag in judge_tags:
        rows = load_records(out_dir, tag)
        datasets = sorted({r["dataset"] for r in rows})
        per = {ds: analyze_rows([r for r in rows if r["dataset"] == ds]) for ds in datasets}
        pooled = analyze_rows(rows)
        result["judges"][tag] = {"datasets_present": datasets, "n_rows": len(rows), "by_dataset": per,
                                 "pooled": pooled, "decision": decide(pooled),
                                 "is_primary": tag == primary_judge}
    return result


# ---------------------------------------------------------------- outputs

def _pct(r: dict) -> str:
    if r["rate"] is None:
        return "—"
    lo, hi = r["wilson95"]
    return f"{100 * r['rate']:.1f} % [{100 * lo:.1f}, {100 * hi:.1f}] (n={r['n']})"


def _dif(d: dict) -> str:
    if d["diff"] is None:
        return "—"
    lo, hi = d["bootstrap95"]
    return f"{100 * d['diff']:+.1f} pts [{100 * lo:+.1f}, {100 * hi:+.1f}] (n={d['n']})"


def to_markdown(result: dict) -> str:
    lines = [f"# H2 results — proposer `{result['proposer_tag']}`", ""]
    for tag, j in result["judges"].items():
        dec = j["decision"]
        lines += [f"## Judge `{tag}`" + (" (primary)" if j["is_primary"] else ""), "",
                  f"Verdict (pooled): **{dec['verdict']}**; hidden failures {dec['n_hidden_fail']} "
                  f"(precondition ≥ {dec['precondition_min_failures']}: {'holds' if dec['precondition_holds'] else 'fails'})",
                  ""]
        if dec["failing_criteria"]:
            lines += ["Failing: " + "; ".join(dec["failing_criteria"]), ""]
        for scope in list(j["by_dataset"]) + ["pooled"]:
            s = j["pooled"] if scope == "pooled" else j["by_dataset"][scope]
            lines += [f"### {scope}", "",
                      f"problems {s['n_problems']}, hidden fail {s['n_hidden_fail']}, hidden pass {s['n_hidden_pass']}, "
                      f"excluded from E {s['n_excluded_from_E']}", "",
                      "| Gate | FPR (Wilson 95 %) | FNR (Wilson 95 %) | unparseable |", "|---|---|---|---|"]
            for g in GATES:
                lines.append(f"| {g} | {_pct(s['fpr'][g])} | {_pct(s['fnr'][g])} | {s['unparseable'][g]} |")
            lines += ["", "| Difference | estimate (bootstrap 95 %) |", "|---|---|"]
            for name, d in s["differences"].items():
                lines.append(f"| {name.replace('_minus_', ' − ')} | {_dif(d)} |")
            lines.append("")
    return "\n".join(lines)


def write_outputs(result: dict, out_dir: Path) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    jp, mp = out_dir / "results.json", out_dir / "results.md"
    jp.write_text(json.dumps(result, indent=2), encoding="utf-8")
    mp.write_text(to_markdown(result), encoding="utf-8")
    return jp, mp
