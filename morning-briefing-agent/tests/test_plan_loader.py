import os
from src.plan_loader import PlanLoader

FIXTURE_PLAN = os.path.join(os.path.dirname(__file__), "fixtures", "sample_plan.md")
FIXTURE_RESOURCES = os.path.join(os.path.dirname(__file__), "fixtures", "sample_resources.md")


def loader():
    return PlanLoader(FIXTURE_PLAN, FIXTURE_RESOURCES)


def test_extract_day1_topic():
    result = loader().load(day=1)
    assert "Claude Code" in result["topic"]


def test_extract_day1_morning_tasks():
    result = loader().load(day=1)
    assert any("best practices" in t.lower() for t in result["morning_tasks"])


def test_extract_day1_afternoon_tasks():
    result = loader().load(day=1)
    assert any("CLAUDE.md" in t for t in result["afternoon_tasks"])


def test_extract_day1_quiz_count():
    result = loader().load(day=1)
    assert result["quiz_count"] == 2


def test_extract_day1_star_resources():
    result = loader().load(day=1)
    assert len(result["star_resources"]) == 2
    assert all(r["url"].startswith("http") for r in result["star_resources"])


def test_star_resources_exclude_circle_items():
    result = loader().load(day=1)
    titles = [r["title"] for r in result["star_resources"]]
    assert not any("Common Workflows" in t for t in titles)


def test_day2_loads_correctly():
    result = loader().load(day=2)
    assert "Subagents" in result["topic"] or "Skills" in result["topic"]


def test_missing_day_raises():
    import pytest
    with pytest.raises(ValueError, match="Day 99 not found"):
        loader().load(day=99)
