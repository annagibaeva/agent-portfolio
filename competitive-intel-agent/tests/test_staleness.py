from __future__ import annotations
from src.staleness import stale_sources
from src.collector import CompetitorResult


def test_source_failing_three_runs_is_stale():
    history = {"Jira": [0, 0]}
    this_run = [CompetitorResult("Jira", ok=True, seeded=False, changes=[])]
    assert "Jira" in stale_sources(this_run, history, threshold=3)


def test_source_with_recent_activity_not_stale():
    history = {"Linear": [0, 5]}
    this_run = [CompetitorResult("Linear", ok=True, seeded=False, changes=[])]
    assert stale_sources(this_run, history, threshold=3) == []


def test_seeded_source_not_flagged():
    history = {"NewComp": []}
    this_run = [CompetitorResult("NewComp", ok=True, seeded=True, changes=[])]
    assert stale_sources(this_run, history, threshold=3) == []
