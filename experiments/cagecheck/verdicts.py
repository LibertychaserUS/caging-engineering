#!/usr/bin/env python3
"""H3 Part B: record the checker's verdicts for every singleton, pair and triple of K1–K6.

Writes ``experiments/cagecheck/verdicts.json`` (next to this script) with, for
each of the 6 + 15 + 20 = 41 combinations, the verdict for goal set ``G``
(solution == yes) and for the auxiliary goal set ``tests_run`` (tests run at
least once), each with its witness path or its annotated frontier.

Sanity requirements taken from the preregistration are asserted; the script
fails loudly (non-zero exit, no file written) if any is violated:
  * every singleton is REACHABLE for G;
  * K1∧K2 is UNREACHABLE for G;
  * K3∧K4 is REACHABLE for G and UNREACHABLE for tests_run.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cagecheck.checker import check  # noqa: E402
from cagecheck.t1 import (  # noqa: E402
    ABSTRACTION_ID, LIBRARY, LIBRARY_NAMES, PREREGISTRATION_TAG, combination, combination_name,
    t1_abstraction,
)

GOALS = ("G", "tests_run")
DEFAULT_OUT = HERE / "verdicts.json"


class SanityError(AssertionError):
    pass


def build_verdicts(today: str | None = None) -> dict[str, Any]:
    abs = t1_abstraction()
    rows: list[dict[str, Any]] = []
    for size in (1, 2, 3):
        for names in combinations(LIBRARY_NAMES, size):
            cages, bound = combination(names)
            verdicts = {g: check(abs, cages, g, bound) for g in GOALS}
            row: dict[str, Any] = {
                "cages": list(names),
                "name": combination_name(names),
                "size": size,
                "max_steps": bound,
            }
            for g in GOALS:
                row[g] = verdicts[g].status
            row["witness"] = {g: verdicts[g].to_json()["witness"] for g in GOALS}
            row["frontier"] = {g: verdicts[g].to_json()["frontier"] for g in GOALS}
            row["reachable"] = sorted(verdicts["G"].reachable)
            rows.append(row)

    by_name = {r["name"]: r for r in rows}
    problems: list[str] = []
    for k in LIBRARY_NAMES:
        if by_name[k]["G"] != "REACHABLE":
            problems.append(f"singleton {k} is {by_name[k]['G']} for G (must be REACHABLE)")
    if by_name["K1∧K2"]["G"] != "UNREACHABLE":
        problems.append("K1∧K2 must be UNREACHABLE for G")
    if by_name["K3∧K4"]["G"] != "REACHABLE":
        problems.append("K3∧K4 must be REACHABLE for G")
    if by_name["K3∧K4"]["tests_run"] != "UNREACHABLE":
        problems.append("K3∧K4 must be UNREACHABLE for tests_run")
    if problems:
        raise SanityError("preregistration sanity requirements violated: " + "; ".join(problems))

    return {
        "generated": today or date.today().isoformat(),
        "abstraction": ABSTRACTION_ID,
        "preregistration_tag": PREREGISTRATION_TAG,
        "states": abs.states,
        "s0": abs.s0,
        "goals": {g: sorted(abs.goals[g]) for g in GOALS},
        "library": {k: {"description": v.description, "max_steps": v.max_steps} for k, v in LIBRARY.items()},
        "n_combinations": len(rows),
        "unreachable": {g: [r["name"] for r in rows if r[g] == "UNREACHABLE"] for g in GOALS},
        "combinations": rows,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    try:
        doc = build_verdicts()
    except SanityError as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 2
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n = doc["n_combinations"]
    for g in GOALS:
        print(f"{g}: {len(doc['unreachable'][g])}/{n} UNREACHABLE: {', '.join(doc['unreachable'][g]) or '-'}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
