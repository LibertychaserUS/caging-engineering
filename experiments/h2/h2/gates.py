"""Gates B, C, D (judge model) and E (the problem's own examples, executed).

Judge gates: temperature 0, max_tokens 1; the answer is parsed as pass if it
starts with yes/pass, fail if no/fail, otherwise `unparseable`, which counts
as PASS and is tallied per gate (preregistration rule).  The judge callable
is injected so that a fake can stand in during tests.

Gate E: a small script that defines the solution and runs the examples is
fed on stdin to

    docker run --rm -i --name <uuid> --network none --memory 512m --cpus 1 \
        ce-harness:py312 python -

(`-i` is required for stdin; everything else is the preregistered command.)
The script enforces a 10 s budget with SIGALRM; a hard outer timeout kills
the container.  Pass iff every example holds.  The executor is injectable.
"""
from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .data import Example, Problem, examples_from_json, examples_to_json, extract_examples
from .jsonl import append_jsonl, read_by_task
from .llm import ChatFn
from .prompts import JUDGE_SYSTEM, judge_user_message
from .propose import parse_yes_no, verdict_from_parsed

JUDGE_GATES = ("B", "C", "D")
JUDGE_MAX_TOKENS = 1
SEED = 0
TEMPERATURE = 0.0

DOCKER_IMAGE = "ce-harness:py312"
EXAMPLE_TIME_LIMIT = 10      # seconds, inside the container (SIGALRM)
HARD_TIMEOUT = 40            # seconds, outer backstop incl. container start-up
RESULT_MARK = "__H2_RESULT__ "


# ------------------------------------------------------------ judge gates

def judge_messages(gate: str, problem: Problem, solution: str, argument: str | None) -> list[dict]:
    return [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": judge_user_message(gate, problem.prompt, solution, argument)},
    ]


def judge_gate(gate: str, problem: Problem, solution: str, argument: str | None, chat: ChatFn) -> dict:
    if gate not in JUDGE_GATES:
        raise ValueError(gate)
    res = chat(judge_messages(gate, problem, solution, argument), temperature=TEMPERATURE, seed=SEED,
               max_tokens=JUDGE_MAX_TOKENS)
    parsed = parse_yes_no(res.content)
    return {"gate": gate, "raw": res.content, "parsed": parsed, "verdict": verdict_from_parsed(parsed),
            "usage": res.usage}


# ----------------------------------------------------------------- gate E

@dataclass
class ExecResult:
    rc: int | None
    stdout: str
    stderr: str
    timed_out: bool = False


Executor = Callable[[str], ExecResult]

# The script run inside the container.  Semantics (preregistration is silent;
# fixed here): a doctest example holds when the value of the expression equals
# the expected output parsed as a Python literal (numbers compared with a
# 1e-6 tolerance), or when its repr/printed output equals the expected text
# modulo whitespace; an example with no expected output holds when the
# expression returns None (doctest semantics), except that a comparison
# expression (`f(x) == y`) with no expected output is an assertion (HumanEval
# writes several examples that way).  An `assert` example holds when it does
# not raise.  Any exception or the time limit is a failure.
_SCRIPT = r'''
import ast, contextlib, io, json, math, signal, sys
SOLUTION = json.loads(%(solution)s)
EXAMPLES = json.loads(%(examples)s)
LIMIT = %(limit)d
MARK = %(mark)s
res = {"passed": 0, "total": len(EXAMPLES), "failures": [], "error": None, "timeout": False}

class _Timeout(Exception):
    pass

def _alarm(*_):
    raise _Timeout()

def _emit():
    sys.stdout.flush()
    sys.__stdout__.write(MARK + json.dumps(res) + "\n")
    sys.__stdout__.flush()

def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)

def _eq(got, exp):
    try:
        if got == exp:
            return True
    except Exception:
        pass
    if _num(got) and _num(exp):
        return math.isclose(got, exp, rel_tol=1e-6, abs_tol=1e-6)
    if isinstance(got, (list, tuple)) and isinstance(exp, (list, tuple)) and len(got) == len(exp):
        return all(_eq(a, b) for a, b in zip(got, exp))
    return False

def _norm(s):
    return " ".join(str(s).split())

def _is_compare(src):
    try:
        node = ast.parse(src, mode="eval").body
    except SyntaxError:
        return False
    return isinstance(node, ast.Compare)

signal.signal(signal.SIGALRM, _alarm)
signal.alarm(LIMIT)
ns = {"__name__": "__h2_solution__", "math": math}
try:
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(SOLUTION, "<solution>", "exec"), ns)
except _Timeout:
    res["timeout"] = True
    _emit(); sys.exit(0)
except BaseException as e:
    res["error"] = ("solution raised %%s: %%s" %% (type(e).__name__, e))[:300]
    _emit(); sys.exit(0)

for ex in EXAMPLES:
    src, want, kind = ex["source"], ex.get("want"), ex["kind"]
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            if kind == "assert":
                exec(compile(src, "<example>", "exec"), ns)
                ok = True
            else:
                try:
                    code = compile(src, "<example>", "eval")
                except SyntaxError:
                    exec(compile(src, "<example>", "exec"), ns)
                    got, is_expr = None, False
                else:
                    got, is_expr = eval(code, ns), True
                printed = buf.getvalue()
                if want == "":
                    ok = bool(got) if (is_expr and _is_compare(src)) else (got is None and printed.strip() == "")
                else:
                    ok = False
                    try:
                        exp = eval(compile(want, "<want>", "eval"), {"__builtins__": {}, "math": math, "inf": math.inf, "nan": math.nan})
                        ok = _eq(got, exp)
                    except Exception:
                        pass
                    if not ok:
                        shown = printed if (got is None and printed) else repr(got)
                        ok = _norm(shown) == _norm(want) or (got is not None and _norm(str(got)) == _norm(want))
        if ok:
            res["passed"] += 1
        else:
            res["failures"].append({"source": src, "reason": "mismatch"})
    except _Timeout:
        res["timeout"] = True
        res["failures"].append({"source": src, "reason": "timeout"})
        break
    except BaseException as e:
        res["failures"].append({"source": src, "reason": ("%%s: %%s" %% (type(e).__name__, e))[:200]})
signal.alarm(0)
_emit()
'''


def build_example_script(solution: str, examples: list[Example], time_limit: int = EXAMPLE_TIME_LIMIT) -> str:
    return _SCRIPT % {
        "solution": repr(json.dumps(solution)),
        "examples": repr(json.dumps(examples_to_json(examples))),
        "limit": int(time_limit),
        "mark": repr(RESULT_MARK),
    }


def docker_command(name: str, image: str = DOCKER_IMAGE) -> list[str]:
    return ["docker", "run", "--rm", "-i", "--name", name, "--network", "none",
            "--memory", "512m", "--cpus", "1", image, "python", "-"]


def docker_executor(script: str, *, image: str = DOCKER_IMAGE, hard_timeout: float = HARD_TIMEOUT) -> ExecResult:
    name = f"ce-h2-{uuid.uuid4().hex[:12]}"
    try:
        p = subprocess.run(docker_command(name, image), input=script, text=True, capture_output=True,
                           timeout=hard_timeout)
    except FileNotFoundError as e:
        raise RuntimeError("docker CLI not found; gate E needs Docker") from e
    except subprocess.TimeoutExpired as e:
        subprocess.run(["docker", "kill", name], capture_output=True)
        return ExecResult(None, (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
                          (e.stderr or b"").decode() if isinstance(e.stderr, bytes) else (e.stderr or ""), timed_out=True)
    if p.returncode in (125, 126, 127):  # docker daemon / image / command problems, not the solution's fault
        raise RuntimeError(f"docker run failed (rc={p.returncode}): {p.stderr.strip()[:300]}")
    return ExecResult(p.returncode, p.stdout, p.stderr)


def parse_exec_result(r: ExecResult) -> dict:
    """verdict pass/fail plus detail from an ExecResult."""
    if r.timed_out:
        return {"verdict": "fail", "reason": "hard_timeout", "passed": None, "total": None, "failures": []}
    payload = None
    for line in r.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            payload = json.loads(line[len(RESULT_MARK):])
    if payload is None:
        reason = "killed" if r.rc not in (0, None) else "no_result"
        return {"verdict": "fail", "reason": f"{reason} (rc={r.rc})", "passed": None, "total": None, "failures": []}
    ok = payload["error"] is None and not payload["timeout"] and payload["total"] > 0 \
        and payload["passed"] == payload["total"]
    reason = payload["error"] or ("timeout" if payload["timeout"] else ("ok" if ok else "example_failed"))
    return {"verdict": "pass" if ok else "fail", "reason": reason, "passed": payload["passed"],
            "total": payload["total"], "failures": payload["failures"]}


def gate_e(solution: str, examples: list[Example] | None, executor: Executor = docker_executor) -> dict:
    """Gate E for one proposal; verdict None when the problem has no examples."""
    if not examples:
        return {"gate": "E", "verdict": None, "reason": "no_examples", "passed": None, "total": 0, "failures": []}
    r = executor(build_example_script(solution, examples))
    return {"gate": "E", **parse_exec_result(r)}


# ----------------------------------------------------------------- driver

def run_gate_e(problems: dict[str, Problem], out_dir: Path, executor: Executor = docker_executor,
               log: Callable[[str], None] = lambda s: None) -> int:
    out_dir = Path(out_dir)
    path = out_dir / "gate_e.jsonl"
    proposals = read_by_task(out_dir / "proposals.jsonl")
    done = read_by_task(path)
    n = 0
    for i, (tid, problem) in enumerate(problems.items(), 1):
        if tid in done:
            continue
        if tid not in proposals:
            raise RuntimeError(f"no proposal for {tid}; run `propose` first")
        examples = extract_examples(problem)
        rec = {"task_id": tid, "dataset": problem.dataset, "has_examples": examples is not None,
               "n_examples": len(examples or []), "examples": examples_to_json(examples),
               **gate_e(proposals[tid]["solution"], examples, executor)}
        append_jsonl(path, rec)
        done[tid] = rec
        n += 1
        if i % 25 == 0:
            log(f"gate E: {i}/{len(problems)}")
    return n


def run_judge_gates(problems: dict[str, Problem], out_dir: Path, judge_tag: str, chat: ChatFn,
                    log: Callable[[str], None] = lambda s: None) -> int:
    out_dir = Path(out_dir)
    path = out_dir / f"gates_{judge_tag}.jsonl"
    proposals = read_by_task(out_dir / "proposals.jsonl")
    arguments = read_by_task(out_dir / "arguments.jsonl")
    done = read_by_task(path)
    n = 0
    for i, (tid, problem) in enumerate(problems.items(), 1):
        if tid in done:
            continue
        if tid not in proposals or tid not in arguments:
            raise RuntimeError(f"missing proposal or argument for {tid}; run `propose` first")
        sol, arg = proposals[tid]["solution"], arguments[tid]["argument"]
        rec = {"task_id": tid, "dataset": problem.dataset, "judge_tag": judge_tag}
        for g in JUDGE_GATES:
            rec[g] = judge_gate(g, problem, sol, arg if g != "B" else None, chat)
        append_jsonl(path, rec)
        done[tid] = rec
        n += 1
        if i % 25 == 0:
            log(f"judge {judge_tag}: {i}/{len(problems)}")
    return n
