from unittest.mock import MagicMock, patch
from src.gmail_client import search_meeting_threads, search_substacks, send_email


def make_message(subject: str, sender: str, snippet: str) -> dict:
    return {
        "id": "msg123",
        "payload": {
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
            ]
        },
        "snippet": snippet,
    }


def make_mock_gmail(messages: list[dict]):
    mock_service = MagicMock()
    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": m["id"]} for m in messages]
    }
    mock_service.users().messages().get().execute.side_effect = messages
    return mock_service


def test_search_meeting_threads_returns_list():
    msg = make_message("Re: project sync", "sarah@example.com", "See you at 10am")
    mock_service = make_mock_gmail([msg])
    with patch("src.gmail_client.build_service", return_value=mock_service):
        result = search_meeting_threads()
    assert isinstance(result, list)


def test_search_meeting_threads_returns_none_on_error():
    mock_service = MagicMock()
    mock_service.users().messages().list().execute.side_effect = Exception("API error")
    with patch("src.gmail_client.build_service", return_value=mock_service):
        result = search_meeting_threads()
    assert result is None


def test_search_substacks_returns_list():
    msg = make_message("Latent Space Weekly", "newsletter@substack.com", "This week in AI...")
    mock_service = make_mock_gmail([msg])
    with patch("src.gmail_client.build_service", return_value=mock_service):
        result = search_substacks()
    assert isinstance(result, list)


def test_search_substacks_returns_none_on_error():
    mock_service = MagicMock()
    mock_service.users().messages().list().execute.side_effect = Exception("API error")
    with patch("src.gmail_client.build_service", return_value=mock_service):
        result = search_substacks()
    assert result is None


def test_send_email_calls_gmail_send():
    mock_service = MagicMock()
    mock_service.users().messages().send().execute.return_value = {"id": "sent123"}
    with patch("src.gmail_client.build_service", return_value=mock_service):
        result = send_email(
            subject="Test",
            html_body="<p>Hello</p>",
            to="anna@example.com",
            creds=None,
        )
    assert result is True
    mock_service.users().messages().send.assert_called()
