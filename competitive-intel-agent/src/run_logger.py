from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path


class RunLogger:
    """Structured JSONL logging keyed by run_id."""

    def __init__(self, run_id: str, log_dir: Path) -> None:
        self.run_id = run_id
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        self.path = log_dir / f"{run_id}.jsonl"

    def event(self, event: str, **fields) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id, "event": event, **fields,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def summary(self, *, competitors_ok: int, competitors_failed: int,
                new_entries: int, tokens: int, outcome: str) -> str:
        line = (f"[{self.run_id}] {outcome} — "
                f"{competitors_ok} ok / {competitors_failed} failed, "
                f"{new_entries} new entries, {tokens} tokens")
        self.event("summary", competitors_ok=competitors_ok,
                   competitors_failed=competitors_failed,
                   new_entries=new_entries, tokens=tokens, outcome=outcome)
        return line
