"""
Read-only access to the empire memory ledger at ~/.principles-claw/memory/ledger.jsonl.

v1 only surfaces ledger.jsonl. atlas-ledger.jsonl and palestra-ledger.jsonl
exist alongside but are agent-specific and large; v1 leaves them for v1.5.

Tail-style read: returns the last N entries by reading the whole file (it's
~125KB; that's cheap). If the file grows by 10x we'll switch to a seek-from-end
strategy.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import LEDGER_PATH


def read_tail(n: int = 50) -> list[dict]:
    if not LEDGER_PATH.exists():
        return []
    out: list[dict] = []
    with LEDGER_PATH.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out[-n:]


def ledger_meta() -> dict:
    if not LEDGER_PATH.exists():
        return {"exists": False, "path": str(LEDGER_PATH)}
    st = LEDGER_PATH.stat()
    return {
        "exists": True,
        "path": str(LEDGER_PATH),
        "size_bytes": st.st_size,
        "modified": int(st.st_mtime),
    }
