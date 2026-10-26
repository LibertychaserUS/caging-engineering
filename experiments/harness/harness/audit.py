"""Hash-chained, append-only JSONL audit log (DESIGN.md "Audit").

Line: {"seq", "ts", "kind", "data", "prev", "hash"} with
  hash = sha256(prev + canonical_json(line without "hash")).
The first line's prev is GENESIS (64 zeros). Canonical JSON: sorted keys, compact
separators, ensure_ascii=False, UTF-8.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

GENESIS = "0" * 64
KINDS = ("model", "tool_call", "verdict", "tool_result", "final", "adjudication")


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def line_hash(prev: str, line_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256((prev + canonical(line_without_hash)).encode("utf-8")).hexdigest()


class AuditLog:
    """Appends to `path`; if the file already has lines, the chain continues from its last hash."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.seq = 0
        self.prev = GENESIS
        if self.path.exists() and self.path.stat().st_size > 0:
            for rec in iter_lines(self.path):
                self.seq = rec["seq"] + 1
                self.prev = rec["hash"]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def append(self, kind: str, data: dict[str, Any]) -> dict[str, Any]:
        if kind not in KINDS:
            raise ValueError(f"unknown audit kind {kind!r}")
        rec: dict[str, Any] = {
            "seq": self.seq,
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "data": data,
            "prev": self.prev,
        }
        rec["hash"] = line_hash(self.prev, rec)
        self._fh.write(canonical(rec) + "\n")
        self._fh.flush()
        self.seq += 1
        self.prev = rec["hash"]
        return rec

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "AuditLog":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def iter_lines(path: str | Path) -> Iterator[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if raw:
                yield json.loads(raw)


def read(path: str | Path) -> list[dict[str, Any]]:
    return list(iter_lines(path))


def verify(path: str | Path) -> bool:
    """True iff every line's hash recomputes from its predecessor and seq numbers are contiguous."""
    prev = GENESIS
    expected_seq = 0
    try:
        for rec in iter_lines(path):
            if rec.get("seq") != expected_seq or rec.get("prev") != prev:
                return False
            body = {k: v for k, v in rec.items() if k != "hash"}
            if line_hash(prev, body) != rec.get("hash"):
                return False
            prev = rec["hash"]
            expected_seq += 1
    except (json.JSONDecodeError, KeyError, TypeError, OSError):
        return False
    return True
