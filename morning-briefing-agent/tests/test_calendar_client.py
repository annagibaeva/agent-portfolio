from datetime import date
from unittest.mock import MagicMock, patch
from src.calendar_client import list_today_events


def make_mock_service(events: list[dict]):
    mock_service = MagicMock()
    mock_service.events().list().execute.return_value = {"items": events}
    return mock_service


def test_returns_formatted_events():
    mock_service = make_mock_service([
        {
            "summary": "Sync with Sarah",
            "start": {"dateTime": "2026-04-24T10:00:00+08:00"},
            "end": {"dateTime": "2026-04-24T10:30:00+08:00"},
            "attendees": [{"email": "sarah@example.com"}, {"email": "anna@example.com"}],
        }
    ])
    with patch("src.calendar_client.build_service", return_value=mock_service):
        events = list_today_events(today=date(2026, 4, 24))
    assert len(events) == 1
    assert events[0]["title"] == "Sync with Sarah"
    assert events[0]["time"] == "10:00"
    assert "sarah@example.com" in events[0]["attendees"]


def test_all_day_event_shows_all_day():
    mock_service = make_mock_service([
        {"summary": "Public Holiday", "start": {"date": "2026-04-24"}, "end": {"date": "2026-04-25"}, "attendees": []}
    ])
    with patch("src.calendar_client.build_service", return_value=mock_service):
        events = list_today_events(today=date(2026, 4, 24))
    assert events[0]["time"] == "All day"


def test_empty_calendar_returns_empty_list():
    mock_service = make_mock_service([])
    with patch("src.calendar_client.build_service", return_value=mock_service):
        events = list_today_events(today=date(2026, 4, 24))
    assert events == []


def test_api_error_returns_none():
    mock_service = MagicMock()
    mock_service.events().list().execute.side_effect = Exception("API error")
    with patch("src.calendar_client.build_service", return_value=mock_service):
        result = list_today_events(today=date(2026, 4, 24))
    assert result is None
