import random

import pytest

from cagecheck.bruteforce import brute, path_count_bound, reachable_fixpoint, reachable_layers, reachable_paths
from cagecheck.checker import check
from cagecheck.graph import Abstraction, NamedCage, block_labels


def lean():
    abs = Abstraction(["a", "b", "g"], "a",
                      [("a", "step", "g"), ("a", "step", "b"), ("b", "step", "g")],
                      {"isGoal": frozenset({"g"})})
    c1 = NamedCage("C1", lambda s, l, d: s == "a" and d == "g")
    c2 = NamedCage("C2", lambda s, l, d: (s == "a" and d == "b") or (s == "b" and d == "g"))
    return abs, c1, c2


def test_fixpoint_on_lean():
    abs, c1, c2 = lean()
    assert reachable_fixpoint(abs, [c1]) == {"a", "g"}
    assert reachable_fixpoint(abs, [c2]) == {"a", "b", "g"}
    assert reachable_fixpoint(abs, [c1, c2]) == {"a"}
    assert brute(abs, [c1, c2], "isGoal").reached is False
    assert brute(abs, [c2], "isGoal").reached is True


def test_bounded_paths_and_layers_agree_and_count_cycles():
    abs = Abstraction(["a", "b"], "a", [("a", "x", "b"), ("b", "x", "a")], {"g": frozenset({"b"})})
    r1, d1 = reachable_paths(abs, [], 3)
    r2, d2 = reachable_layers(abs, [], 3)
    assert r1 == r2 == {"a", "b"} and d1 == d2 == {"a": 0, "b": 1}
    r0, d0 = reachable_paths(abs, [], 0)
    assert r0 == {"a"} and d0 == {"a": 0}
    assert brute(abs, [block_labels("k", ["x"])], "g", max_steps=5).reachable == {"a"}


def test_path_count_bound():
    abs = Abstraction(["a", "b"], "a", [("a", "x", "b"), ("a", "y", "b"), ("b", "x", "a")], {"g": frozenset()})
    assert path_count_bound(abs, [], 2) == 1 + 2 + 4


def test_brute_runs_without_literal_enumeration_on_dense_long_bound():
    n = 12
    states = [f"s{i}" for i in range(n)]
    edges = [(s, lab, d) for s in states for d in states for lab in "abc"]
    abs = Abstraction(states, "s0", edges, {"g": frozenset({"s11"})})
    r = brute(abs, [], "g", max_steps=12)  # 36**12 paths: must fall back to layers
    assert r.reached and r.reachable == set(states) and r.min_depth["s11"] == 1


@pytest.mark.parametrize("seed", range(5))
def test_random_agreement_small(seed):
    rng = random.Random(seed)
    states = [f"q{i}" for i in range(rng.randint(3, 9))]
    edges = [(s, lab, d) for s in states for d in states for lab in "ab" if rng.random() < 0.2]
    abs = Abstraction(states, states[0], edges, {"g": frozenset(rng.sample(states, 2))})
    cage = block_labels("k", ["a"])
    for ms in (None, 1, 2, 3):
        v = check(abs, [cage], "g", ms)
        b = brute(abs, [cage], "g", ms)
        assert (v.status == "REACHABLE") == b.reached
        assert v.reachable == b.reachable
