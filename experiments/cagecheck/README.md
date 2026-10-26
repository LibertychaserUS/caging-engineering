# cagecheck — the H3 cage consistency check

Decides whether a goal set stays reachable on a finite abstraction under the conjunction of
cages (edge predicates), and returns a witness path or the frontier at which every route is cut.
Implements H3 Part A (checker + brute-force validation) and Part B (verdicts for the T1 cage
library K1–K6) of `experiments/PREREGISTRATION.md` (tag `prereg-frozen-2026-10-26`).
Python 3.12, standard library only; `pytest` for the tests.

    uv run --python 3.12 --with pytest pytest -q      # unit tests
    uv run --python 3.12 python validate.py           # Part A: prints "agreement: N/N", exit 1 on any mismatch
    uv run --python 3.12 python verdicts.py           # Part B: writes verdicts.json

`validate.py` compares `cagecheck.checker` (BFS) with `cagecheck.bruteforce` (naive fixpoint; for
`max_steps`, depth layers plus literal path enumeration where it fits) on 1 000 seeded random
instances and the hand-written cases, including the three-state counterexample of `formal/CagingCore.lean`.

`verdicts.json` lists all 41 combinations (6 singletons, 15 pairs, 20 triples) of K1–K6 on the
"t1 v1" abstraction (`cagecheck/t1.py`, whose docstring records every modelling choice). Per
combination: `G` and `tests_run` are `REACHABLE`/`UNREACHABLE`; `witness` holds a shortest allowed
path per goal (or null); `frontier` holds, per goal, every edge leaving the reachable set that some
cage cuts, each with `cut_by` (or null). K5 is the bound `max_steps = 12`; a frontier that is empty
under `UNREACHABLE` would mean the bound alone is responsible. These verdicts are recorded before any
agent run; H3's soundness criterion is scored against them.
