from __future__ import annotations
from src.collector import CompetitorResult


def stale_sources(results: list[CompetitorResult],
                  history: dict[str, list[int]],
                  threshold: int = 3) -> list[str]:
    """Return names of sources with zero entries for `threshold` runs in a row.

    `history` maps competitor name -> entry counts of the previous runs
    (most recent first), covering up to threshold-1 prior runs.
    """
    stale: list[str] = []
    for r in results:
        if not r.ok or r.seeded:
            continue
        this_count = len(r.changes)
        prior = history.get(r.name, [])[: threshold - 1]
        if this_count == 0 and len(prior) >= threshold - 1 \
                and all(c == 0 for c in prior):
            stale.append(r.name)
    return stale
