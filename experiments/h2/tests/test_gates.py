import subprocess
import sys
from pathlib import Path

import pytest

from h2.data import Example, Problem
from h2.gates import (ExecResult, build_example_script, docker_command, gate_e, judge_gate, judge_messages,
                      parse_exec_result, run_gate_e, run_judge_gates)
from h2.jsonl import append_jsonl, read_jsonl
from h2.prompts import JUDGE_QUESTION, RUBRIC

P = Problem("HumanEval/0", "humaneval", 'def f(x):\n    """doc\n    >>> f(1)\n    1\n    """\n', "f")
SOL = "def f(x):\n    return x\n"
ARG = "It returns its input, as required."


# ------------------------------------------------------------ judge gates

def test_judge_parsing_and_tally(fake_chat):
    chat = fake_chat(answers=["Yes", "No", "Hmm"])
    b = judge_gate("B", P, SOL, None, chat)
    c = judge_gate("C", P, SOL, ARG, chat)
    d = judge_gate("D", P, SOL, ARG, chat)
    assert (b["parsed"], b["verdict"]) == ("yes", "pass")
    assert (c["parsed"], c["verdict"]) == ("no", "fail")
    assert (d["parsed"], d["verdict"]) == ("unparseable", "pass")  # unparseable counts as pass, tallied
    for call in chat.calls:
        assert call["temperature"] == 0 and call["max_tokens"] == 1 and call["seed"] == 0


def test_judge_sees_exactly_what_the_gate_table_says():
    mb = judge_messages("B", P, SOL, None)[1]["content"]
    mc = judge_messages("C", P, SOL, ARG)[1]["content"]
    md = judge_messages("D", P, SOL, ARG)[1]["content"]
    assert P.prompt in mb and SOL in mb and ARG not in mb and RUBRIC not in mb and mb.endswith(JUDGE_QUESTION)
    assert ARG in mc and RUBRIC not in mc and mc.startswith(mb.split(JUDGE_QUESTION)[0])
    assert ARG in md and RUBRIC in md
    with pytest.raises(ValueError):
        judge_messages("C", P, SOL, None)


def test_run_judge_gates_resume(tmp_path: Path, fake_chat):
    append_jsonl(tmp_path / "proposals.jsonl", {"task_id": P.task_id, "solution": SOL})
    append_jsonl(tmp_path / "arguments.jsonl", {"task_id": P.task_id, "argument": ARG})
    chat = fake_chat(answers=["yes", "yes", "no"])
    assert run_judge_gates({P.task_id: P}, tmp_path, "primary", chat) == 1
    rec = read_jsonl(tmp_path / "gates_primary.jsonl")[0]
    assert [rec[g]["verdict"] for g in "BCD"] == ["pass", "pass", "fail"]
    assert run_judge_gates({P.task_id: P}, tmp_path, "primary", fake_chat(answers=[])) == 0


# ----------------------------------------------------------------- gate E

def local_executor(script: str) -> ExecResult:
    """Fake of the docker executor: runs the same script in a local interpreter."""
    p = subprocess.run([sys.executable, "-I", "-"], input=script, text=True, capture_output=True, timeout=30)
    return ExecResult(p.returncode, p.stdout, p.stderr)


def test_gate_e_with_fake_executor_results():
    ex = [Example("doctest", "f(1)", "1")]
    ok = ExecResult(0, '__H2_RESULT__ {"passed": 1, "total": 1, "failures": [], "error": null, "timeout": false}\n', "")
    assert gate_e(SOL, ex, lambda s: ok)["verdict"] == "pass"
    bad = ExecResult(0, '__H2_RESULT__ {"passed": 0, "total": 1, "failures": [{"source": "f(1)", "reason": "mismatch"}], "error": null, "timeout": false}\n', "")
    assert gate_e(SOL, ex, lambda s: bad)["verdict"] == "fail"
    assert gate_e(SOL, ex, lambda s: ExecResult(None, "", "", timed_out=True))["reason"] == "hard_timeout"
    assert gate_e(SOL, ex, lambda s: ExecResult(137, "", ""))["verdict"] == "fail"
    assert gate_e(SOL, None, lambda s: ok)["verdict"] is None  # excluded, no executor call
    assert docker_command("n")[:3] == ["docker", "run", "--rm"] and "--network" in docker_command("n")


def test_example_script_semantics():
    def run(sol, examples, limit=10):
        return parse_exec_result(local_executor(build_example_script(sol, examples, limit)))

    doct = [Example("doctest", "f(1)", "1"), Example("doctest", "f([1, 2])", "[1,\n2]")]
    assert run(SOL, doct)["verdict"] == "pass"
    assert run("def f(x):\n    return 0\n", doct)["passed"] == 0
    # comparison with no expected output is an assertion; plain call with no output needs None
    assert run(SOL, [Example("doctest", "f(2) == 2", "")])["verdict"] == "pass"
    assert run(SOL, [Example("doctest", "f(2) == 3", "")])["verdict"] == "fail"
    assert run(SOL, [Example("doctest", "f(None)", "")])["verdict"] == "pass"
    assert run(SOL, [Example("doctest", "f(1)", "")])["verdict"] == "fail"
    # numeric tolerance and repr fallback
    assert run("def f(x):\n    return 0.1 + 0.2\n", [Example("doctest", "f(0)", "0.3")])["verdict"] == "pass"
    assert run("def f(x):\n    return float('inf')\n", [Example("doctest", "f(0)", "inf")])["verdict"] == "pass"
    # asserts (MBPP+) and math available
    asserts = [Example("assert", "assert f(3) == 3", None), Example("assert", "assert math.isclose(f(1.0), 1.0)", None)]
    assert run(SOL, asserts)["verdict"] == "pass"
    assert run(SOL, [Example("assert", "assert f(3) == 4", None)])["failures"][0]["reason"].startswith("AssertionError")
    # solution that fails to define, raises, or loops
    assert run("def g(x):\n    return x\n", doct)["failures"][0]["reason"].startswith("NameError")
    assert run("raise ValueError('boom')\n", doct)["reason"].startswith("solution raised ValueError")
    r = run("def f(x):\n    while True:\n        pass\n", doct, limit=1)
    assert r["verdict"] == "fail" and r["reason"] == "timeout"


def test_run_gate_e_records_exclusions(tmp_path: Path):
    no_ex = Problem("HumanEval/9", "humaneval", 'def h(x):\n    """Example: h(1) -> 1"""\n', "h")
    for p in (P, no_ex):
        append_jsonl(tmp_path / "proposals.jsonl", {"task_id": p.task_id, "solution": SOL})
    calls = []
    def ex(script):
        calls.append(script)
        return ExecResult(0, '__H2_RESULT__ {"passed": 1, "total": 1, "failures": [], "error": null, "timeout": false}\n', "")
    assert run_gate_e({P.task_id: P, no_ex.task_id: no_ex}, tmp_path, ex) == 2
    recs = {r["task_id"]: r for r in read_jsonl(tmp_path / "gate_e.jsonl")}
    assert recs[P.task_id]["verdict"] == "pass" and recs[P.task_id]["has_examples"]
    assert recs[no_ex.task_id]["verdict"] is None and not recs[no_ex.task_id]["has_examples"]
    assert len(calls) == 1
    assert run_gate_e({P.task_id: P, no_ex.task_id: no_ex}, tmp_path, ex) == 0
