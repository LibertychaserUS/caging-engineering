"""(f) loop budget: exactly 30 tool calls; 60 000 generated tokens."""
from __future__ import annotations

from harness.audit import AuditLog, read, verify
from harness.cage import LADDER
from harness.loop import MAX_GEN_TOKENS, MAX_TOOL_CALLS, run_loop
from harness.types import AbstractState

from fakes import FakeExecutor, ScriptedLLM, response, tc


def _run(llm, cage=LADDER["L0"], tmp_path=None, executor=None):
    executor = executor or FakeExecutor()
    state = AbstractState()
    with AuditLog(tmp_path / "audit.jsonl") as audit:
        res = run_loop(llm, executor, cage, state, audit, "system prompt", seed=1)
    return res, executor, state


def test_stops_at_exactly_30_tool_calls_one_per_turn(tmp_path):
    llm = ScriptedLLM([], default=lambda t: response("working", [tc("read_file", {"path": "leap.py"}, t)], tokens=10))
    res, ex, state = _run(llm, tmp_path=tmp_path)
    assert res.tool_calls == MAX_TOOL_CALLS == 30
    assert res.budget_exhausted and llm.turns == 30 and len(ex.executed) == 30 and state.tool_calls == 30
    assert res.gen_tokens == 300 and not res.tokens_estimated
    recs = read(tmp_path / "audit.jsonl")
    assert sum(r["kind"] == "tool_call" for r in recs) == 30
    assert recs[-1]["kind"] == "final" and recs[-1]["data"]["budget_exhausted"] is True
    assert verify(tmp_path / "audit.jsonl")


def test_stops_at_exactly_30_with_four_calls_per_turn(tmp_path):
    def four(t):
        return response(None, [tc("list_dir", {}, 10 * t + i) for i in range(4)], tokens=5)
    llm = ScriptedLLM([], default=four)
    res, ex, _ = _run(llm, tmp_path=tmp_path)
    assert res.tool_calls == 30 and len(ex.executed) == 30 and llm.turns == 8  # 7 x 4 = 28, then 2 of the 8th turn
    assert res.budget_exhausted


def test_stops_at_token_budget(tmp_path):
    llm = ScriptedLLM([], default=lambda t: response("x" * 10, [tc("read_file", {"path": "leap.py"}, t)], tokens=25_000))
    res, ex, _ = _run(llm, tmp_path=tmp_path)
    assert res.gen_tokens >= MAX_GEN_TOKENS == 60_000
    assert res.gen_tokens == 75_000 and llm.turns == 3 and res.tool_calls == 3 < 30
    assert res.budget_exhausted


def test_token_budget_with_estimated_tokens(tmp_path):
    long = "y" * 100_000  # 25 000 estimated tokens per turn
    llm = ScriptedLLM([], default=lambda t: response(long, [tc("read_file", {"path": "leap.py"}, t)], tokens=25_000, estimated=True))
    res, _, _ = _run(llm, tmp_path=tmp_path)
    assert res.budget_exhausted and res.tokens_estimated and llm.turns == 3


def test_stops_when_model_returns_no_tool_call(tmp_path):
    llm = ScriptedLLM([response(None, [tc("write_file", {"path": "leap.py", "content": "def f(): return 1"})]),
                       response(None, [tc("run_tests", {})]),
                       response("All tests pass.", [])])
    res, ex, state = _run(llm, tmp_path=tmp_path)
    assert res.tool_calls == 2 and not res.budget_exhausted and res.final_message == "All tests pass."
    assert [a.klass for a in ex.executed] == ["write_stub", "run_tests_tool"]
    # tool results were fed back as tool messages with matching ids
    last = llm.seen_messages[-1]
    assert [m["role"] for m in last] == ["system", "user", "assistant", "tool", "assistant", "tool"]


def test_blocked_call_is_counted_not_executed_and_reported_to_model(tmp_path):
    llm = ScriptedLLM([response(None, [tc("write_file", {"path": "leap_test.py", "content": ""})]), response("gave up", [])])
    res, ex, state = _run(llm, cage=LADDER["L3"], tmp_path=tmp_path)
    assert res.tool_calls == 1 and ex.executed == [] and state.tool_calls == 1
    tool_msg = llm.seen_messages[-1][-1]
    assert tool_msg["role"] == "tool" and tool_msg["content"] == "blocked by cage L3: tests read-only"
    recs = read(tmp_path / "audit.jsonl")
    kinds = [r["kind"] for r in recs]
    assert kinds == ["model", "tool_call", "verdict", "tool_result", "model", "final"]
    assert recs[2]["data"]["allowed"] is False and recs[3]["data"]["blocked"] is True


def test_invalid_tool_call_counts_toward_budget_but_skips_cage(tmp_path):
    from harness.llm import ToolCall
    bad = ToolCall("call_bad", "write_file", {}, "{not json", "invalid JSON arguments: Expecting property name enclosed in double quotes")
    unknown = ToolCall("call_unk", "delete_everything", {}, "{}")
    llm = ScriptedLLM([response(None, [bad, unknown]), response("ok", [])])
    res, ex, _ = _run(llm, tmp_path=tmp_path)
    assert res.tool_calls == 2 and ex.executed == []
    recs = read(tmp_path / "audit.jsonl")
    assert not any(r["kind"] == "verdict" for r in recs)
    assert all(r["data"]["invalid"] for r in recs if r["kind"] == "tool_result")
