import random

import validate
import verdicts


def test_hand_written_cases_all_agree():
    cases = validate.hand_written_cases()
    assert any(c.name.startswith("lean/") for c in cases)
    for case in cases:
        outcome, _ = validate.run_case(case)
        assert outcome.ok, (case.name, outcome.problems)


def test_random_sample_agrees():
    rng = random.Random(validate.DEFAULT_SEED)
    for i in range(60):
        case = validate.random_instance(rng, i)
        outcome, _ = validate.run_case(case)
        assert outcome.ok, (case.name, outcome.problems)


def test_validate_main_reports_full_agreement(capsys):
    assert validate.main(["--n", "40", "--seed", "7"]) == 0
    assert capsys.readouterr().out.strip() == "agreement: 70/70"


def test_build_verdicts_counts_and_sanity():
    doc = verdicts.build_verdicts(today="2026-10-26")
    assert doc["n_combinations"] == 41 and len(doc["combinations"]) == 41
    assert doc["abstraction"] == "t1 v1" and doc["preregistration_tag"] == "prereg-frozen-2026-10-26"
    assert doc["unreachable"]["G"] == ["K1∧K2", "K1∧K2∧K3", "K1∧K2∧K4", "K1∧K2∧K5", "K1∧K2∧K6"]
    assert doc["unreachable"]["tests_run"] == ["K3∧K4", "K1∧K3∧K4", "K2∧K3∧K4", "K3∧K4∧K5", "K3∧K4∧K6"]
    row = next(r for r in doc["combinations"] if r["name"] == "K1∧K2")
    assert row["witness"]["G"] is None and row["frontier"]["G"]
    assert all(set(f["cut_by"]) <= {"K1", "K2"} and f["cut_by"] for f in row["frontier"]["G"])
