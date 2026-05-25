from __future__ import annotations
from src.models import Change, DiffResult, Entry


def classify(entries: list[Entry], known: dict[str, str]) -> DiffResult:
    new: list[Change] = []
    updated: list[Change] = []
    for e in entries:
        if e.content_hash not in known:
            new.append(Change(entry=e, kind="new"))
        elif known[e.content_hash] != e.body_hash:
            updated.append(Change(entry=e, kind="updated"))
    return DiffResult(new=new, updated=updated)
