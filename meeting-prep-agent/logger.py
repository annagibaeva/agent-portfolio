"""Structured JSONL run logger."""
from __future__ import annotations

import json
import secrets
import time
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"


def new_run_id() -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"run-{ts}-{secrets.token_hex(3)}"


def log(run_id: str, **fields) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    path = LOG_DIR / f"{run_id}.jsonl"
    entry = {"ts": time.time(), "run_id": run_id, **fields}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
