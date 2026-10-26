from pathlib import Path

from h2.data import Problem
from h2.jsonl import read_jsonl
from h2.propose import (argue_messages, extract_code, parse_yes_no, run_propose, self_report_messages,
                        verdict_from_parsed)
from h2.prompts import ARGUE_INSTRUCTION, PROPOSE_INSTRUCTION, SELF_REPORT_QUESTION

P = Problem("HumanEval/0", "humaneval", 'def f(x):\n    """doc\n    >>> f(1)\n    1\n    """\n', "f")


def test_extract_code_prefers_block_with_entry_point():
    raw = "Sure.\n```python\nprint('hi')\n```\n```python\ndef f(x):\n    return x\n```\n"
    assert extract_code(raw, "f") == "def f(x):\n    return x"
    assert extract_code(raw) == "print('hi')"
    assert extract_code("def f(x):\n    return x") == "def f(x):\n    return x"
    assert extract_code("```python\ndef f(x):\n    return x") == "def f(x):\n    return x"


def test_parse_yes_no():
    assert parse_yes_no("Yes") == "yes" and parse_yes_no(" yes.") == "yes" and parse_yes_no("PASS") == "yes"
    assert parse_yes_no("No") == "no" and parse_yes_no("**no**") == "no" and parse_yes_no("fail") == "no"
    assert parse_yes_no("Maybe") == "unparseable" and parse_yes_no("") == "unparseable"
    assert verdict_from_parsed("unparseable") == "pass"
    assert verdict_from_parsed("no") == "fail"


def test_run_propose_three_files_and_resume(tmp_path: Path, fake_chat):
    def answer(messages):
        last = messages[-1]["content"]
        if last == SELF_REPORT_QUESTION:
            return "Yes"
        if last.startswith(ARGUE_INSTRUCTION):
            return "It returns x, which is what the problem asks."
        assert last.startswith(PROPOSE_INSTRUCTION) and P.prompt in last
        return "```python\ndef f(x):\n    return x\n```"
    chat = fake_chat(fn=answer)
    done = run_propose({P.task_id: P}, tmp_path, chat)
    assert done == {"proposals": 1, "self_report": 1, "arguments": 1}
    assert len(chat.calls) == 3
    # gate A: same context + own answer appended + the exact question, first token only
    a_call = chat.calls[1]
    assert a_call["messages"] == self_report_messages(P, read_jsonl(tmp_path / "proposals.jsonl")[0])
    assert a_call["messages"][1]["role"] == "assistant" and a_call["max_tokens"] == 1
    assert a_call["temperature"] == 0 and a_call["seed"] == 0
    # argument: fresh context
    assert len(chat.calls[2]["messages"]) == 1 and chat.calls[2]["messages"] == argue_messages(P, read_jsonl(tmp_path / "proposals.jsonl")[0])
    prop = read_jsonl(tmp_path / "proposals.jsonl")[0]
    assert prop["code"] == "def f(x):\n    return x" and prop["solution"].rstrip() == prop["code"]
    assert read_jsonl(tmp_path / "self_report.jsonl")[0]["verdict"] == "pass"
    # resume: nothing redone
    chat2 = fake_chat(fn=answer)
    assert run_propose({P.task_id: P}, tmp_path, chat2) == {"proposals": 0, "self_report": 0, "arguments": 0}
    assert chat2.calls == []
