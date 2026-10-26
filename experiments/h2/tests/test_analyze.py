import json
from pathlib import Path

from h2.analyze import (MIN_FAILURES, analyze, analyze_rows, bootstrap_diff, decide, to_markdown, wilson,
                        write_outputs)
from h2.jsonl import append_jsonl


def row(i, ds, hidden_pass, A, B, C, D, E, has_examples=True, unparse=()):
    def g(v, name):
        if v is None:
            return {"verdict": None, "parsed": None}
        return {"verdict": "pass" if v else "fail", "parsed": "unparseable" if name in unparse else ("yes" if v else "no")}
    return {"task_id": f"{ds}/{i}", "dataset": ds, "hidden_pass": hidden_pass, "has_examples": has_examples,
            "A": g(A, "A"), "B": g(B, "B"), "C": g(C, "C"), "D": g(D, "D"), "E": g(E if has_examples else None, "E")}


def synthetic(n_fail=100, n_pass=50, a=60, e=10, b=20, c=50, d=30, no_ex=0):
    """Failing rows: first a say-pass on A, first e on E, first b on B, first c on C, first d on D.

    The last `no_ex` failing rows have no examples (A says pass on them, so A's FPR
    on the with-examples subset differs from its FPR overall).
    """
    rows = []
    for i in range(n_fail):
        has = i < n_fail - no_ex
        rows.append(row(i, "humaneval" if i % 2 else "mbpp", False, i < a, i < b, i < c, i < d, i < e, has_examples=has))
    for i in range(n_pass):  # passing rows: every gate says pass except B on the first 5 (FNR_B = 0.1)
        rows.append(row(1000 + i, "humaneval", True, True, i >= 5, True, True, True))
    return rows


def test_wilson_and_bootstrap_basics():
    assert wilson(0, 0) is None
    lo, hi = wilson(50, 100)
    assert 0.40 < lo < 0.5 < hi < 0.60
    assert wilson(0, 10)[0] == 0.0 and wilson(10, 10)[1] == 1.0
    pairs = [(1, 0)] * 30 + [(0, 0)] * 70
    ci = bootstrap_diff(pairs, n_resamples=2000)
    assert 0.20 < ci[0] < 0.30 < ci[1] < 0.40
    assert bootstrap_diff(pairs, n_resamples=500) == bootstrap_diff(pairs, n_resamples=500)  # seeded
    assert bootstrap_diff([]) is None


def test_rates_by_construction_and_supported_verdict():
    s = analyze_rows(synthetic())
    assert s["n_hidden_fail"] == 100 and s["n_hidden_pass"] == 50 and s["n_excluded_from_E"] == 0
    assert s["fpr"]["A"]["rate"] == 0.60 and s["fpr"]["E"]["rate"] == 0.10
    assert s["fpr"]["B"]["rate"] == 0.20 and s["fpr"]["C"]["rate"] == 0.50 and s["fpr"]["D"]["rate"] == 0.30
    assert s["fnr"]["B"]["rate"] == 0.10 and s["fnr"]["A"]["rate"] == 0.0
    assert abs(s["differences"]["A_minus_E"]["diff"] - 0.50) < 1e-9
    assert abs(s["differences"]["C_minus_B"]["diff"] - 0.30) < 1e-9
    assert abs(s["differences"]["D_minus_B"]["diff"] - 0.10) < 1e-9
    assert s["differences"]["C_minus_B"]["ci_excludes_zero"]
    dec = decide(s)
    assert dec["precondition_holds"] and dec["criterion_1"] and dec["criterion_2"]
    assert dec["verdict"] == "supported" and dec["failing_criteria"] == []


def test_paired_difference_uses_only_problems_with_examples():
    # A says pass on all 60; E on 10; the last 20 failing rows have no examples.
    # A's FPR overall is 0.60; on the 80 with examples A passes 60/80 = 0.75, E passes 10/80 = 0.125.
    s = analyze_rows(synthetic(no_ex=20))
    assert s["n_excluded_from_E"] == 20
    assert s["fpr"]["A"]["n"] == 100 and s["fpr"]["A"]["rate"] == 0.60
    assert s["fpr"]["E"]["n"] == 80 and s["fpr"]["E"]["rate"] == 0.125
    d = s["differences"]["A_minus_E"]
    assert d["n"] == 80 and abs(d["diff"] - (0.75 - 0.125)) < 1e-9
    assert s["differences"]["C_minus_B"]["n"] == 100  # C - B uses all failing proposals


def test_not_supported_branches():
    # criterion 2 fails: C == B
    s = analyze_rows(synthetic(b=50, c=50))
    dec = decide(s)
    assert dec["verdict"] == "not supported" and dec["criterion_1"] and not dec["criterion_2"]
    assert dec["failing_criteria"] and dec["failing_criteria"][0].startswith("criterion 2")
    # criterion 1 fails on the threshold: A - E = 0.15 with a CI excluding 0
    s = analyze_rows(synthetic(a=25, e=10))
    dec = decide(s)
    assert abs(s["differences"]["A_minus_E"]["diff"] - 0.15) < 1e-9
    assert s["differences"]["A_minus_E"]["ci_excludes_zero"] and not dec["criterion_1"]
    assert dec["verdict"] == "not supported"


def test_precondition_branch():
    s = analyze_rows(synthetic(n_fail=MIN_FAILURES - 1, a=40, e=5, b=10, c=30, d=20))
    dec = decide(s)
    assert not dec["precondition_holds"] and dec["verdict"] == "inconclusive: insufficient failures"
    assert dec["failing_criteria"] is None
    s = analyze_rows(synthetic(n_fail=MIN_FAILURES, a=40, e=5, b=10, c=30, d=20))
    assert decide(s)["precondition_holds"]


def test_unparseable_tally():
    rows = synthetic(n_fail=10, n_pass=2, a=5, e=2, b=3, c=4, d=4)
    rows[0]["B"]["parsed"] = "unparseable"
    rows[1]["D"]["parsed"] = "unparseable"
    rows[11]["A"]["parsed"] = "unparseable"
    s = analyze_rows(rows)
    assert s["unparseable"] == {"A": 1, "B": 1, "C": 0, "D": 1, "E": 0}


def test_end_to_end_files(tmp_path: Path):
    rows = synthetic(n_fail=70, n_pass=30, a=50, e=10, b=14, c=35, d=20, no_ex=10)
    for r in rows:
        append_jsonl(tmp_path / "truth.jsonl", {"task_id": r["task_id"], "dataset": r["dataset"], "hidden_pass": r["hidden_pass"]})
        append_jsonl(tmp_path / "self_report.jsonl", {"task_id": r["task_id"], **r["A"]})
        append_jsonl(tmp_path / "gate_e.jsonl", {"task_id": r["task_id"], "has_examples": r["has_examples"], "verdict": r["E"]["verdict"]})
        append_jsonl(tmp_path / "gates_primary.jsonl", {"task_id": r["task_id"], "B": r["B"], "C": r["C"], "D": r["D"]})
    res = analyze(tmp_path, ["primary"], "primary")
    j = res["judges"]["primary"]
    assert j["datasets_present"] == ["humaneval", "mbpp"] and j["n_rows"] == 100
    assert j["pooled"]["n_hidden_fail"] == 70 and j["decision"]["verdict"] == "supported"
    assert sum(j["by_dataset"][d]["n_hidden_fail"] for d in j["by_dataset"]) == 70
    jp, mp = write_outputs(res, tmp_path)
    assert json.loads(jp.read_text())["judges"]["primary"]["decision"]["verdict"] == "supported"
    md = to_markdown(res)
    assert "| A |" in md and "A − E" in md and "supported" in md
