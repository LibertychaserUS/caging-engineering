#!/usr/bin/env python3
"""H3 Part A: validate ``cagecheck.checker`` against ``cagecheck.bruteforce``.

Runs 1 000 random instances (5–50 states, 1–4 cages, random edge density,
labels from a small alphabet, random goal set, ``max_steps`` in about a third
of the cases) with a fixed seed, plus the hand-written cases (the Lean
three-state counterexample, a chain, a diamond, a bound-only case, the T1
sanity cases).  For each instance the two implementations must agree on the
status and on the reachable set; the checker's witness must be a valid allowed
path of the right length, and the hand-written expectations must hold.

Prints ``agreement: N/N`` and exits non-zero on any disagreement.
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cagecheck.bruteforce import brute  # noqa: E402
from cagecheck.checker import Verdict, check  # noqa: E402
from cagecheck.graph import Abstraction, Cage, Edge, NamedCage, block_edges, block_labels  # noqa: E402
from cagecheck.t1 import LIBRARY_NAMES, combination, t1_abstraction  # noqa: E402

DEFAULT_SEED = 20261026
DEFAULT_N = 1000
ALPHABET = ("a", "b", "c")
PATH_BUDGET = 60_000  # bound on d**k for the explicit path enumeration


@dataclass
class Case:
    name: str
    abs: Abstraction
    cages: list[Cage]
    goal: str
    max_steps: int | None = None
    expect_status: str | None = None
    expect_reachable: frozenset[str] | None = None
    expect_witness: list[Edge] | None = None
    expect_frontier: list[Edge] | None = None
    expect_cut_by: dict[Edge, tuple[str, ...]] | None = None
    expect_witness_len: int | None = None


@dataclass
class Outcome:
    case: str
    ok: bool
    problems: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------------
# Hand-written cases
# ----------------------------------------------------------------------------

def lean_three_state() -> tuple[Abstraction, NamedCage, NamedCage]:
    """``formal/CagingCore.lean``: states a, b, g; edges a→g, a→b, b→g.

    C₁ keeps only a→g; C₂ keeps only a→b and b→g.
    """
    abs = Abstraction(
        states=["a", "b", "g"],
        s0="a",
        edges=[("a", "step", "g"), ("a", "step", "b"), ("b", "step", "g")],
        goals={"isGoal": frozenset({"g"})},
    )
    c1 = NamedCage("C1", lambda s, l, d: s == "a" and d == "g")
    c2 = NamedCage("C2", lambda s, l, d: (s == "a" and d == "b") or (s == "b" and d == "g"))
    return abs, c1, c2


def hand_written_cases() -> list[Case]:
    cases: list[Case] = []

    # 1. Lean three-state counterexample.
    lean, c1, c2 = lean_three_state()
    cases.append(Case("lean/C1", lean, [c1], "isGoal", expect_status="REACHABLE",
                      expect_witness=[("a", "step", "g")], expect_reachable=frozenset({"a", "g"})))
    cases.append(Case("lean/C2", lean, [c2], "isGoal", expect_status="REACHABLE",
                      expect_witness=[("a", "step", "b"), ("b", "step", "g")],
                      expect_reachable=frozenset({"a", "b", "g"})))
    cases.append(Case("lean/C1∧C2", lean, [c1, c2], "isGoal", expect_status="UNREACHABLE",
                      expect_reachable=frozenset({"a"}),
                      expect_frontier=[("a", "step", "g"), ("a", "step", "b")],
                      expect_cut_by={("a", "step", "g"): ("C2",), ("a", "step", "b"): ("C1",)}))
    cases.append(Case("lean/none", lean, [], "isGoal", expect_status="REACHABLE",
                      expect_witness=[("a", "step", "g")]))

    # 2. Chain s0 → s1 → ... → s5.
    chain_states = [f"s{i}" for i in range(6)]
    chain_edges: list[Edge] = [(f"s{i}", "n", f"s{i+1}") for i in range(5)]
    chain = Abstraction(chain_states, "s0", chain_edges, {"end": frozenset({"s5"}), "start": frozenset({"s0"})})
    cases.append(Case("chain/open", chain, [], "end", expect_status="REACHABLE", expect_witness=chain_edges,
                      expect_reachable=frozenset(chain_states)))
    cut = block_edges("cut23", [("s2", "n", "s3")])
    cases.append(Case("chain/cut", chain, [cut], "end", expect_status="UNREACHABLE",
                      expect_reachable=frozenset({"s0", "s1", "s2"}),
                      expect_frontier=[("s2", "n", "s3")], expect_cut_by={("s2", "n", "s3"): ("cut23",)}))
    cases.append(Case("chain/goal-is-s0", chain, [block_labels("all", ["n"])], "start",
                      expect_status="REACHABLE", expect_witness=[], expect_reachable=frozenset({"s0"})))

    # 3. Diamond s0 → l → t, s0 → r → t, plus a direct s0 → t only via label "x".
    dia = Abstraction(
        ["s0", "l", "r", "t"], "s0",
        [("s0", "L", "l"), ("l", "L", "t"), ("s0", "R", "r"), ("r", "R", "t"), ("s0", "x", "t")],
        {"t": frozenset({"t"})},
    )
    no_l = block_labels("noL", ["L"])
    no_r = block_labels("noR", ["R"])
    no_x = block_labels("noX", ["x"])
    cases.append(Case("diamond/open", dia, [], "t", expect_status="REACHABLE", expect_witness=[("s0", "x", "t")]))
    cases.append(Case("diamond/noL∧noX", dia, [no_l, no_x], "t", expect_status="REACHABLE",
                      expect_witness=[("s0", "R", "r"), ("r", "R", "t")],
                      expect_reachable=frozenset({"s0", "r", "t"})))
    cases.append(Case("diamond/noL∧noR∧noX", dia, [no_l, no_r, no_x], "t", expect_status="UNREACHABLE",
                      expect_reachable=frozenset({"s0"}),
                      expect_frontier=[("s0", "L", "l"), ("s0", "R", "r"), ("s0", "x", "t")],
                      expect_cut_by={("s0", "L", "l"): ("noL",), ("s0", "R", "r"): ("noR",),
                                     ("s0", "x", "t"): ("noX",)}))
    # 4. Only max_steps makes it unreachable: short route cut, long route exceeds the bound.
    cases.append(Case("diamond/noX bound 1", dia, [no_x], "t", max_steps=1, expect_status="UNREACHABLE",
                      expect_reachable=frozenset({"s0", "l", "r"}),
                      expect_frontier=[("s0", "x", "t")], expect_cut_by={("s0", "x", "t"): ("noX",)}))
    cases.append(Case("chain/bound 4", chain, [], "end", max_steps=4, expect_status="UNREACHABLE",
                      expect_reachable=frozenset({"s0", "s1", "s2", "s3", "s4"}), expect_frontier=[]))
    cases.append(Case("chain/bound 5", chain, [], "end", max_steps=5, expect_status="REACHABLE",
                      expect_witness=chain_edges))
    cases.append(Case("chain/bound 0", chain, [], "end", max_steps=0, expect_status="UNREACHABLE",
                      expect_reachable=frozenset({"s0"}), expect_frontier=[]))

    # 5. T1 sanity cases from the preregistration.
    t1 = t1_abstraction()
    for k in LIBRARY_NAMES:
        cages, bound = combination([k])
        cases.append(Case(f"t1/{k}/G", t1, cages, "G", bound, expect_status="REACHABLE"))
        cases.append(Case(f"t1/{k}/tests_run", t1, cages, "tests_run", bound, expect_status="REACHABLE"))
    cages, bound = combination(["K1", "K2"])
    cases.append(Case("t1/K1∧K2/G", t1, cages, "G", bound, expect_status="UNREACHABLE"))
    cages, bound = combination(["K3", "K4"])
    cases.append(Case("t1/K3∧K4/G", t1, cages, "G", bound, expect_status="REACHABLE"))
    cases.append(Case("t1/K3∧K4/tests_run", t1, cages, "tests_run", bound, expect_status="UNREACHABLE"))
    cases.append(Case("t1/none/G", t1, [], "G", expect_status="REACHABLE", expect_witness_len=1))
    return cases


# ----------------------------------------------------------------------------
# Random instances
# ----------------------------------------------------------------------------

def random_cage(rng: random.Random, i: int, states: list[str], edges: list[Edge]) -> Cage:
    kind = rng.choice(("labels", "into", "from", "edges"))
    name = f"c{i}:{kind}"
    if kind == "labels":
        k = rng.randint(1, len(ALPHABET) - 1)
        return block_labels(name, rng.sample(ALPHABET, k))
    if kind == "into":
        k = rng.randint(1, max(1, len(states) // 2))
        blocked = frozenset(rng.sample(states, k))
        return NamedCage(name, lambda s, l, d, b=blocked: d not in b)
    if kind == "from":
        k = rng.randint(1, max(1, len(states) // 2))
        blocked = frozenset(rng.sample(states, k))
        return NamedCage(name, lambda s, l, d, b=blocked: s not in b)
    q = rng.uniform(0.1, 0.6)
    return block_edges(name, [e for e in edges if rng.random() < q])


def random_instance(rng: random.Random, i: int) -> Case:
    n = rng.randint(5, 50)
    states = [f"q{j}" for j in range(n)]
    bounded = rng.random() < 1 / 3
    max_steps: int | None = None
    if rng.random() < 0.5:
        p = rng.uniform(0.01, 0.08)
    else:
        p = rng.uniform(0.05, 0.35)
    if bounded:
        max_steps = rng.randint(1, 6)
        d_max = PATH_BUDGET ** (1.0 / max_steps)
        p = min(p, d_max / (n * len(ALPHABET)))
    edges: list[Edge] = [
        (s, lab, d) for s in states for d in states for lab in ALPHABET if rng.random() < p
    ]
    s0 = rng.choice(states)
    gsize = rng.randint(1, max(1, n // 4))
    goal = set(rng.sample(states, gsize))
    if rng.random() < 0.05:
        goal.add(s0)
    abs = Abstraction(states, s0, edges, {"g": frozenset(goal)})
    cages = [random_cage(rng, j, states, edges) for j in range(rng.randint(1, 4))]
    return Case(f"random/{i}", abs, cages, "g", max_steps)


# ----------------------------------------------------------------------------
# Comparison
# ----------------------------------------------------------------------------

def _valid_path(case: Case, path: list[Edge]) -> str | None:
    edge_set = set(case.abs.edges)
    goal_states = case.abs.goal_set(case.goal)
    at = case.abs.s0
    for e in path:
        if e not in edge_set:
            return f"witness edge {e} not in abstraction"
        if e[0] != at:
            return f"witness not contiguous at {e}"
        if not all(c(*e) for c in case.cages):
            return f"witness edge {e} is cut by a cage"
        at = e[2]
    if at not in goal_states:
        return f"witness ends in {at}, not a goal state"
    if case.max_steps is not None and len(path) > case.max_steps:
        return f"witness length {len(path)} exceeds max_steps {case.max_steps}"
    return None


def run_case(case: Case) -> tuple[Outcome, Verdict]:
    v = check(case.abs, case.cages, case.goal, case.max_steps)
    b = brute(case.abs, case.cages, case.goal, case.max_steps)
    problems: list[str] = []
    if (v.status == "REACHABLE") != b.reached:
        problems.append(f"status: checker {v.status}, brute reached={b.reached}")
    if v.reachable != b.reachable:
        problems.append(f"reachable set differs: only-checker={sorted(v.reachable - b.reachable)} "
                        f"only-brute={sorted(b.reachable - v.reachable)}")
    if v.status == "REACHABLE":
        assert v.witness is not None
        err = _valid_path(case, v.witness)
        if err:
            problems.append(err)
        if b.min_depth is not None:
            best = min(b.min_depth[s] for s in case.abs.goal_set(case.goal) if s in b.min_depth)
            if len(v.witness) != best:
                problems.append(f"witness length {len(v.witness)} but brute shortest is {best}")
        if v.frontier is not None or v.cut_by is not None:
            problems.append("frontier must be None when REACHABLE")
    else:
        assert v.frontier is not None and v.cut_by is not None
        if v.witness is not None:
            problems.append("witness must be None when UNREACHABLE")
        for e in v.frontier:
            if e[0] not in v.reachable:
                problems.append(f"frontier edge {e} does not leave the reachable set")
            names = v.cut_by.get(e, ())
            actual = tuple(c.name for c in case.cages if not c(*e))
            if names != actual:
                problems.append(f"cut_by for {e}: {names} vs recomputed {actual}")
        expected_frontier = [e for e in dict.fromkeys(case.abs.edges)
                             if e[0] in v.reachable and any(not c(*e) for c in case.cages)]
        if v.frontier != expected_frontier:
            problems.append("frontier is not exactly the cut edges leaving the reachable set")
    # Hand-written expectations.
    if case.expect_status is not None and v.status != case.expect_status:
        problems.append(f"expected {case.expect_status}, got {v.status}")
    if case.expect_reachable is not None and v.reachable != case.expect_reachable:
        problems.append(f"expected reachable {sorted(case.expect_reachable)}, got {sorted(v.reachable)}")
    if case.expect_witness is not None and v.witness != case.expect_witness:
        problems.append(f"expected witness {case.expect_witness}, got {v.witness}")
    if case.expect_witness_len is not None and (v.witness is None or len(v.witness) != case.expect_witness_len):
        problems.append(f"expected witness of length {case.expect_witness_len}, got {v.witness}")
    if case.expect_frontier is not None and v.frontier != case.expect_frontier:
        problems.append(f"expected frontier {case.expect_frontier}, got {v.frontier}")
    if case.expect_cut_by is not None and v.cut_by != case.expect_cut_by:
        problems.append(f"expected cut_by {case.expect_cut_by}, got {v.cut_by}")
    return Outcome(case.name, not problems, problems), v


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=DEFAULT_N, help="number of random instances")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--verbose", action="store_true", help="print a breakdown before the summary line")
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    cases = hand_written_cases() + [random_instance(rng, i) for i in range(args.n)]
    outcomes: list[Outcome] = []
    stats = {"REACHABLE": 0, "UNREACHABLE": 0, "bounded": 0}
    for case in cases:
        out, v = run_case(case)
        outcomes.append(out)
        stats[v.status] += 1
        stats["bounded"] += case.max_steps is not None
    bad = [o for o in outcomes if not o.ok]
    for o in bad:
        print(f"DISAGREEMENT {o.case}: " + "; ".join(o.problems), file=sys.stderr)
    if args.verbose:
        n_hand = len(hand_written_cases())
        print(f"hand-written: {n_hand}, random: {args.n} (bounded: {stats['bounded']}), "
              f"verdicts: {stats['REACHABLE']} REACHABLE / {stats['UNREACHABLE']} UNREACHABLE")
    print(f"agreement: {len(outcomes) - len(bad)}/{len(outcomes)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
