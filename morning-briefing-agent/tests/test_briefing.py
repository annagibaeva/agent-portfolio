import json
from datetime import date
from unittest.mock import patch

import pytest

from briefing import run


@pytest.fixture
def temp_progress(tmp_path):
    p = tmp_path / "progress.json"
    p.write_text(json.dumps({
        "start_date": "2026-04-24",
        "plan_file": "tests/fixtures/sample_plan.md",
        "resources_file": "tests/fixtures/sample_resources.md",
        "last_anthropic_post": None,
        "days": {},
    }))
    return str(p)


def test_run_sends_email_on_success(temp_progress):
    with patch("briefing.list_today_events", return_value=[{"title": "Sync", "time": "10:00", "attendees": []}]), \
         patch("briefing.search_meeting_threads", return_value=[]), \
         patch("briefing.search_substacks", return_value=[]), \
         patch("briefing.fetch_anthropic_post", return_value={"title": "Test", "url": "https://anthropic.com"}), \
         patch("briefing.compose_brief_sections", return_value={"meeting_context": "OK", "ai_pulse": "OK"}), \
         patch("briefing.send_email", return_value=True) as mock_send, \
         patch("briefing.get_google_credentials", return_value=None), \
         patch("briefing.PROGRESS_FILE", temp_progress), \
         patch("briefing.PLAN_FILE", "tests/fixtures/sample_plan.md"), \
         patch("briefing.RESOURCES_FILE", "tests/fixtures/sample_resources.md"):
        run(today=date(2026, 4, 24))
    mock_send.assert_called_once()


def test_run_sends_email_even_when_calendar_fails(temp_progress):
    with patch("briefing.list_today_events", return_value=None), \
         patch("briefing.search_meeting_threads", return_value=[]), \
         patch("briefing.search_substacks", return_value=[]), \
         patch("briefing.fetch_anthropic_post", return_value=None), \
         patch("briefing.compose_brief_sections", return_value={"meeting_context": "OK", "ai_pulse": "OK"}), \
         patch("briefing.send_email", return_value=True) as mock_send, \
         patch("briefing.get_google_credentials", return_value=None), \
         patch("briefing.PROGRESS_FILE", temp_progress), \
         patch("briefing.PLAN_FILE", "tests/fixtures/sample_plan.md"), \
         patch("briefing.RESOURCES_FILE", "tests/fixtures/sample_resources.md"):
        run(today=date(2026, 4, 24))
    mock_send.assert_called_once()


def test_run_logs_to_progress(temp_progress):
    with patch("briefing.list_today_events", return_value=[]), \
         patch("briefing.search_meeting_threads", return_value=[]), \
         patch("briefing.search_substacks", return_value=[]), \
         patch("briefing.fetch_anthropic_post", return_value=None), \
         patch("briefing.compose_brief_sections", return_value={"meeting_context": "OK", "ai_pulse": "OK"}), \
         patch("briefing.send_email", return_value=True), \
         patch("briefing.get_google_credentials", return_value=None), \
         patch("briefing.PROGRESS_FILE", temp_progress), \
         patch("briefing.PLAN_FILE", "tests/fixtures/sample_plan.md"), \
         patch("briefing.RESOURCES_FILE", "tests/fixtures/sample_resources.md"):
        run(today=date(2026, 4, 24))
    data = json.loads(open(temp_progress).read())
    assert "1" in data["days"]
