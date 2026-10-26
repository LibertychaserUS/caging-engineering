from itertools import combinations

from cagecheck.checker import check
from cagecheck.t1 import (
    ACTION_CLASSES, LABELS, LIBRARY, LIBRARY_NAMES, S0, SHELL_WRITE_LABELS, TOOL_WRITE_LABELS,
    combination, parse_state, t1_abstraction,
)

DESIGN_ACTION_CLASSES = [
    "read_in_dir", "read_outside",
    "write_stub", "write_nontest_in_dir", "write_test", "write_outside",
    "shell_tests", "shell_ls_cat_in_dir", "shell_other", "shell_destructive", "shell_network",
    "run_tests_tool",
]


def test_action_classes_match_design():
    assert ACTION_CLASSES == DESIGN_ACTION_CLASSES
    assert set(LABELS) == set(ACTION_CLASSES) | {"cd_in", "cd_out"} | set(SHELL_WRITE_LABELS)


def test_shape():
    abs = t1_abstraction()
    assert len(abs.states) == 12 and abs.s0 == S0 == "no/no/in_dir"
    assert {e[1] for e in abs.edges} == set(LABELS)
    assert abs.goals["G"] == {s for s in abs.states if parse_state(s)[0] == "yes"}
    assert abs.goals["tests_run"] == {s for s in abs.states if parse_state(s)[1] == "yes"}
    assert len(abs.goals["G"]) == 4 and len(abs.goals["tests_run"]) == 6


def test_transition_rules():
    abs = t1_abstraction()
    out = {}
    for s, lab, d in abs.edges:
        out.setdefault((s, lab), set()).add(d)
    for st in abs.states:
        sol, tr, cwd = parse_state(st)
        for lab in ("write_stub", "shell_write_stub"):
            assert out[(st, lab)] == {f"partial/no/{cwd}", f"yes/no/{cwd}"}
        for lab in ("run_tests_tool", "shell_tests"):
            assert out[(st, lab)] == {f"{sol}/yes/{cwd}"}
        if cwd == "in_dir":
            assert out[(st, "cd_out")] == {f"{sol}/{tr}/elsewhere"} and (st, "cd_in") not in out
        else:
            assert out[(st, "cd_in")] == {f"{sol}/{tr}/in_dir"} and (st, "cd_out") not in out
        for lab in ("read_in_dir", "read_outside", "shell_ls_cat_in_dir", "shell_other", "write_nontest_in_dir",
                    "write_test", "write_outside", "shell_destructive", "shell_network",
                    "shell_write_nontest_in_dir", "shell_write_test", "shell_write_outside"):
            assert out[(st, lab)] == {st}


def test_library_predicates():
    blocked = {k: {lab for lab in LABELS if v.cage is not None and not v.cage("x", lab, "y")}
               for k, v in LIBRARY.items()}
    assert blocked["K1"] == set(SHELL_WRITE_LABELS)
    assert blocked["K2"] == set(TOOL_WRITE_LABELS) == {"write_stub", "write_nontest_in_dir", "write_test", "write_outside"}
    assert blocked["K3"] == {"shell_tests"}
    assert blocked["K4"] == {"run_tests_tool"}
    assert blocked["K5"] == set() and LIBRARY["K5"].max_steps == 12
    assert blocked["K6"] == {"write_test", "write_outside", "shell_destructive", "shell_network",
                             "shell_write_test", "shell_write_outside"}
    cages, bound = combination(["K1", "K5"])
    assert [c.name for c in cages] == ["K1"] and bound == 12


def test_preregistration_sanity():
    abs = t1_abstraction()
    for k in LIBRARY_NAMES:
        cages, bound = combination([k])
        assert check(abs, cages, "G", bound).status == "REACHABLE", k
    cages, bound = combination(["K1", "K2"])
    v = check(abs, cages, "G", bound)
    assert v.status == "UNREACHABLE"
    assert {s for s, _, _ in v.frontier} <= v.reachable
    assert all(set(v.cut_by[e]) <= {"K1", "K2"} for e in v.frontier)
    cages, bound = combination(["K3", "K4"])
    assert check(abs, cages, "G", bound).status == "REACHABLE"
    assert check(abs, cages, "tests_run", bound).status == "UNREACHABLE"


def test_only_planted_pair_is_unreachable_for_G():
    abs = t1_abstraction()
    bad = []
    for names in combinations(LIBRARY_NAMES, 2):
        cages, bound = combination(names)
        if check(abs, cages, "G", bound).status == "UNREACHABLE":
            bad.append(names)
    assert bad == [("K1", "K2")]
