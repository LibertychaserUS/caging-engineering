import pytest

from cagecheck.checker import check
from cagecheck.graph import Abstraction, NamedCage, allow_all, block_edges, block_labels, conj


def lean():
    abs = Abstraction(["a", "b", "g"], "a",
                      [("a", "step", "g"), ("a", "step", "b"), ("b", "step", "g")],
                      {"isGoal": frozenset({"g"})})
    c1 = NamedCage("C1", lambda s, l, d: s == "a" and d == "g")
    c2 = NamedCage("C2", lambda s, l, d: (s == "a" and d == "b") or (s == "b" and d == "g"))
    return abs, c1, c2


def test_lean_singletons_reach_with_witness():
    abs, c1, c2 = lean()
    v1 = check(abs, [c1], "isGoal")
    assert v1.status == "REACHABLE" and v1.witness == [("a", "step", "g")]
    assert v1.frontier is None and v1.cut_by is None and v1.reachable == {"a", "g"}
    v2 = check(abs, [c2], "isGoal")
    assert v2.status == "REACHABLE" and v2.witness == [("a", "step", "b"), ("b", "step", "g")]


def test_lean_conjunction_unreachable_with_annotated_frontier():
    abs, c1, c2 = lean()
    v = check(abs, [c1, c2], "isGoal")
    assert v.status == "UNREACHABLE" and v.witness is None
    assert v.reachable == {"a"}
    assert v.frontier == [("a", "step", "g"), ("a", "step", "b")]
    assert v.cut_by == {("a", "step", "g"): ("C2",), ("a", "step", "b"): ("C1",)}


def test_conj_helper_matches_list_of_cages():
    abs, c1, c2 = lean()
    v = check(abs, [conj(c1, c2)], "isGoal")
    assert v.status == "UNREACHABLE"
    assert v.cut_by == {("a", "step", "g"): ("C1∧C2",), ("a", "step", "b"): ("C1∧C2",)}
    assert conj().name == "⊤" and check(abs, [conj()], "isGoal").status == "REACHABLE"


def test_s0_in_goal_gives_empty_witness():
    abs = Abstraction(["a", "b"], "a", [("a", "x", "b")], {"g": frozenset({"a"})})
    v = check(abs, [block_labels("all", ["x"])], "g")
    assert v.status == "REACHABLE" and v.witness == [] and v.reachable == {"a"}


def test_witness_is_shortest():
    abs = Abstraction(["s", "m1", "m2", "t"], "s",
                      [("s", "long", "m1"), ("m1", "long", "m2"), ("m2", "long", "t"), ("s", "short", "t")],
                      {"t": frozenset({"t"})})
    assert check(abs, [], "t").witness == [("s", "short", "t")]
    assert len(check(abs, [block_labels("ns", ["short"])], "t").witness) == 3


def test_max_steps_bounds_depth_and_empty_frontier_means_bound_only():
    states = [f"s{i}" for i in range(6)]
    edges = [(f"s{i}", "n", f"s{i+1}") for i in range(5)]
    abs = Abstraction(states, "s0", edges, {"end": frozenset({"s5"})})
    v4 = check(abs, [], "end", max_steps=4)
    assert v4.status == "UNREACHABLE" and v4.frontier == [] and v4.reachable == set(states[:5])
    v5 = check(abs, [], "end", max_steps=5)
    assert v5.status == "REACHABLE" and v5.witness == edges
    v0 = check(abs, [], "end", max_steps=0)
    assert v0.reachable == {"s0"}
    with pytest.raises(ValueError):
        check(abs, [], "end", max_steps=-1)


def test_frontier_only_lists_cut_edges_leaving_reachable_set():
    abs = Abstraction(["a", "b", "c", "d"], "a",
                      [("a", "x", "b"), ("b", "y", "c"), ("c", "z", "d"), ("a", "w", "d")],
                      {"d": frozenset({"d"})})
    v = check(abs, [block_edges("k", [("b", "y", "c"), ("a", "w", "d"), ("c", "z", "d")])], "d")
    assert v.status == "UNREACHABLE" and v.reachable == {"a", "b"}
    assert v.frontier == [("a", "w", "d"), ("b", "y", "c")] or v.frontier == [("b", "y", "c"), ("a", "w", "d")]
    assert set(v.frontier) == {("b", "y", "c"), ("a", "w", "d")}  # (c,z,d) is cut but c is not reachable


def test_duplicate_edges_are_tolerated():
    abs = Abstraction(["a", "b"], "a", [("a", "x", "b"), ("a", "x", "b")], {"g": frozenset({"b"})})
    v = check(abs, [block_labels("k", ["x"])], "g")
    assert v.frontier == [("a", "x", "b")]


def test_abstraction_validation():
    with pytest.raises(ValueError):
        Abstraction(["a"], "z", [], {})
    with pytest.raises(ValueError):
        Abstraction(["a"], "a", [("a", "x", "q")], {})
    with pytest.raises(ValueError):
        Abstraction(["a"], "a", [], {"g": frozenset({"q"})})
    with pytest.raises(KeyError):
        check(Abstraction(["a"], "a", [], {}), [allow_all()], "nope")


def test_to_json_shape():
    abs, c1, c2 = lean()
    j = check(abs, [c1, c2], "isGoal").to_json()
    assert j["status"] == "UNREACHABLE" and j["witness"] is None
    assert j["frontier"] == [{"edge": ["a", "step", "g"], "cut_by": ["C2"]},
                             {"edge": ["a", "step", "b"], "cut_by": ["C1"]}]
    assert j["reachable"] == ["a"]
