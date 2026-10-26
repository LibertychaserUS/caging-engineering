import json
from pathlib import Path

from h2.data import Problem
from h2.ground_truth import evalplus_command, parse_results, results_path, run_evalplus, write_samples
from h2.jsonl import read_jsonl


def test_write_samples_and_missing(tmp_path: Path):
    ps = {"Mbpp/2": Problem("Mbpp/2", "mbpp", "p", "f"), "Mbpp/3": Problem("Mbpp/3", "mbpp", "p", "g")}
    props = {"Mbpp/2": {"solution": "def f(): pass"}}
    assert write_samples(ps, props, tmp_path / "s.jsonl") == ["Mbpp/3"]
    assert not (tmp_path / "s.jsonl").exists()
    props["Mbpp/3"] = {"solution": "def g(): pass"}
    assert write_samples(ps, props, tmp_path / "s.jsonl") == []
    assert [r["task_id"] for r in read_jsonl(tmp_path / "s.jsonl")] == ["Mbpp/2", "Mbpp/3"]


def test_command_and_results_parsing(tmp_path: Path):
    sp = tmp_path / "samples_humaneval.jsonl"
    cmd = evalplus_command("humaneval", sp, 2)
    assert cmd[1:] == ["-m", "evalplus.evaluate", "--dataset", "humaneval", "--samples", str(sp), "--parallel", "2"]
    rp = results_path(sp)
    assert rp.name == "samples_humaneval_eval_results.json"
    rp.write_text(json.dumps({"hash": "x", "eval": {
        "HumanEval/0": [{"base_status": "pass", "plus_status": "pass"}],
        "HumanEval/1": [{"base_status": "pass", "plus_status": "fail"}],
        "HumanEval/2": [{"base_status": "fail", "plus_status": "fail"}],
    }}))
    parsed = parse_results(rp)
    assert [parsed[t]["hidden_pass"] for t in ("HumanEval/0", "HumanEval/1", "HumanEval/2")] == [True, False, False]
    # resumable: results present -> runner not invoked
    called = []
    assert run_evalplus("humaneval", sp, 2, runner=lambda c: called.append(c) or 0) == rp
    assert called == []
