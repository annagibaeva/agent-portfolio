from src.email_builder import build_email, build_subject


SAMPLE = {
    "day": 5,
    "week": 1,
    "pct_complete": 24,
    "date_str": "2026-04-28",
    "events": [{"time": "10:00", "title": "Sync with Sarah", "attendees": ["sarah@example.com"]}],
    "meeting_context": "Sarah call: agenda draft received. 3 open threads.",
    "day_content": {
        "topic": "Morning Briefing Agent",
        "morning_tasks": ["Read agent design patterns post"],
        "afternoon_tasks": ["Build the agent"],
        "quiz_count": 10,
        "star_resources": [{"title": "Building Effective Agents", "url": "https://anthropic.com/research/building-effective-agents"}],
    },
    "ai_pulse": "Anthropic posted on writing effective tools. Latent Space covered agent evals.",
    "anthropic_post": {"title": "Writing effective tools", "url": "https://anthropic.com/engineering/test"},
    "events_unavailable": False,
    "gmail_unavailable": False,
}


def test_subject_includes_day_and_date():
    subject = build_subject(day=5, date_str="2026-04-28")
    assert "Day 5" in subject
    assert "2026-04-28" in subject


def test_html_contains_progress_section():
    html = build_email(SAMPLE)
    assert "Day 5 of 21" in html
    assert "Week 1" in html
    assert "24%" in html


def test_html_contains_schedule_section():
    html = build_email(SAMPLE)
    assert "10:00" in html
    assert "Sync with Sarah" in html


def test_html_contains_learning_section():
    html = build_email(SAMPLE)
    assert "Morning Briefing Agent" in html
    assert "Read agent design patterns post" in html


def test_html_contains_resources():
    html = build_email(SAMPLE)
    assert "Building Effective Agents" in html
    assert "https://anthropic.com/research/building-effective-agents" in html


def test_html_contains_ai_pulse():
    html = build_email(SAMPLE)
    assert "Writing effective tools" in html


def test_unavailable_flag_shows_warning():
    data = {**SAMPLE, "events_unavailable": True}
    html = build_email(data)
    assert "unavailable" in html.lower()


def test_output_is_valid_html():
    html = build_email(SAMPLE)
    assert html.startswith("<!DOCTYPE html>") or "<html" in html
