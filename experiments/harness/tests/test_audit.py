"""(d) audit hash chain: append, verify, detect tampering."""
from __future__ import annotations

import json

from harness.audit import GENESIS, AuditLog, read, verify


def test_chain_append_and_verify(tmp_path):
    p = tmp_path / "a.jsonl"
    with AuditLog(p) as log:
        r0 = log.append("model", {"content": "hi", "tool_calls": []})
        r1 = log.append("tool_call", {"call": 1, "tool": "read_file", "args": {"path": "x"}})
        r2 = log.append("final", {"content": "done"})
    assert r0["prev"] == GENESIS and r1["prev"] == r0["hash"] and r2["prev"] == r1["hash"]
    assert [r["seq"] for r in read(p)] == [0, 1, 2]
    assert verify(p)


def test_chain_continues_across_reopen(tmp_path):
    p = tmp_path / "a.jsonl"
    with AuditLog(p) as log:
        log.append("model", {"n": 1})
    with AuditLog(p) as log:
        log.append("model", {"n": 2})
    recs = read(p)
    assert recs[1]["seq"] == 1 and recs[1]["prev"] == recs[0]["hash"]
    assert verify(p)


def test_tampered_line_detected(tmp_path):
    p = tmp_path / "a.jsonl"
    with AuditLog(p) as log:
        for i in range(5):
            log.append("tool_result", {"call": i, "blocked": False, "rc": 0, "output": "ok"})
    lines = p.read_text().splitlines()
    rec = json.loads(lines[2])
    rec["data"]["output"] = "tampered"
    lines[2] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    p.write_text("\n".join(lines) + "\n")
    assert not verify(p)


def test_deleted_and_reordered_lines_detected(tmp_path):
    p = tmp_path / "a.jsonl"
    with AuditLog(p) as log:
        for i in range(4):
            log.append("model", {"n": i})
    lines = p.read_text().splitlines()
    (tmp_path / "del.jsonl").write_text("\n".join(lines[:2] + lines[3:]) + "\n")
    (tmp_path / "swap.jsonl").write_text("\n".join([lines[0], lines[2], lines[1], lines[3]]) + "\n")
    (tmp_path / "trunc.jsonl").write_text("\n".join(lines[:3]) + "\n")
    assert not verify(tmp_path / "del.jsonl")
    assert not verify(tmp_path / "swap.jsonl")
    assert verify(tmp_path / "trunc.jsonl")  # truncation of the tail is not detectable by the chain alone
    (tmp_path / "garbage.jsonl").write_text("not json\n")
    assert not verify(tmp_path / "garbage.jsonl")
