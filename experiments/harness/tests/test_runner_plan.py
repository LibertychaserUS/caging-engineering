"""Runner planning (--dry-run) without a model or Docker."""
from __future__ import annotations

import json

import pytest

from harness.runner import h3_conditions, main, plan
from harness.types import HarnessError


def manifest(n_admitted=137):
    admitted = [f"ex{i:03d}" for i in range(n_admitted)]
    return {"admitted_exercises": admitted, "h3_subset_80": admitted[:80], "h3_subset_40": admitted[:40],
            "h4_orders": [admitted[i:i + 40] for i in (0, 40, 80)],
            "sources": {"models": {"agent_primary": {"hf_id": "x"}, "agent_secondary": {"hf_id": "y"}}}}


def test_h3_condition_names():
    c = h3_conditions()
    assert len(c) == 41 and c[:6] == ["K1", "K2", "K3", "K4", "K5", "K6"]
    assert "K1+K2" in c and "K1+K2+K3" in c and "K4+K5+K6" in c
    assert sum("+" not in x for x in c) == 6 and sum(x.count("+") == 1 for x in c) == 15 and sum(x.count("+") == 2 for x in c) == 20


def test_h1_plan():
    seqs = plan(manifest(), "h1", [1, 2, 3], "primary")
    eps = [e for s in seqs for e in s]
    assert len(eps) == 7 * 137 * 3 and all(len(s) == 1 for s in seqs)
    assert {e.condition for e in eps} == {f"L{i}" for i in range(7)}
    assert len({e.episode_id for e in eps}) == len(eps)


def test_h3_plan():
    eps = [e for s in plan(manifest(), "h3", [1], "primary") for e in s]
    assert len(eps) == 21 * 80 + 20 * 40 == 2480
    triples = {e.exercise for e in eps if e.condition.count("+") == 2}
    assert len(triples) == 40 and all(e.seed == 1 for e in eps)


def test_h4_plan_sequences():
    seqs = plan(manifest(), "h4", [1], "primary")
    assert len(seqs) == 12 and all(len(s) == 40 for s in seqs)
    assert sum(len(s) for s in seqs) == 480
    assert {e.condition for s in seqs for e in s} == {"L3"}
    assert {e.memory for s in seqs for e in s} == {"M0", "M1", "M2", "M3"}
    assert seqs[0][0].episode_id.startswith("h4-L3-M0-o0-t01-")


def test_null_field_is_reported(tmp_path, capsys):
    m = manifest()
    m["h4_orders"] = None
    with pytest.raises(HarnessError):
        plan(m, "h4", [1], "primary")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m))
    assert main(["--hypothesis", "h4", "--out", str(tmp_path / "o"), "--manifest", str(p), "--dry-run"]) == 2
    assert "h4_orders" in capsys.readouterr().err
    assert main(["--hypothesis", "h1", "--out", str(tmp_path / "o"), "--manifest", str(p), "--dry-run"]) == 0
    assert "total" in capsys.readouterr().out


def test_h1_only_may_name_smoke_exercises():
    from harness.runner import plan
    m = manifest()
    m["smoke_test_exercises"] = ["leap", "bob"]
    seqs = plan(m, "h1", [1], "primary", {"leap"})
    assert len(seqs) == 7 and all(seq[0].exercise == "leap" for seq in seqs)
