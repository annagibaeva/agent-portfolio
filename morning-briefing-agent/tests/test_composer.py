from unittest.mock import MagicMock, patch
from src.composer import compose_brief_sections


SAMPLE_DATA = {
    "events": [{"title": "Sync with Sarah", "time": "10:00", "attendees": ["sarah@example.com"]}],
    "meeting_threads": [{"subject": "Re: project sync", "from": "sarah@example.com", "snippet": "See you at 10am"}],
    "substacks": [{"subject": "Latent Space Weekly", "from": "newsletter@substack.com", "snippet": "AI news..."}],
    "anthropic_post": {"title": "Writing effective tools", "url": "https://anthropic.com/engineering/test"},
    "day_content": {"day": 1, "topic": "Claude Code", "morning_tasks": ["Read best practices"]},
}


def mock_anthropic_response(text: str):
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=text)]
    mock_client.messages.create.return_value = mock_message
    return mock_client


def test_returns_meeting_context_and_ai_pulse():
    mock_client = mock_anthropic_response(
        "MEETING_CONTEXT\nSarah call: agenda draft received.\nAI_PULSE\nLatest post on tools."
    )
    with patch("src.composer.anthropic.Anthropic", return_value=mock_client):
        result = compose_brief_sections(SAMPLE_DATA, api_key="test-key")
    assert "meeting_context" in result
    assert "ai_pulse" in result


def test_returns_fallback_on_api_error():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API error")
    with patch("src.composer.anthropic.Anthropic", return_value=mock_client):
        result = compose_brief_sections(SAMPLE_DATA, api_key="test-key")
    assert result["meeting_context"] == "[unavailable — check Gmail]"
    assert result["ai_pulse"] == "[unavailable — check Anthropic blog]"


def test_prompt_includes_email_content_delimited():
    mock_client = mock_anthropic_response("MEETING_CONTEXT\nOK\nAI_PULSE\nOK")
    with patch("src.composer.anthropic.Anthropic", return_value=mock_client):
        compose_brief_sections(SAMPLE_DATA, api_key="test-key")
    call_args = mock_client.messages.create.call_args
    prompt = call_args[1]["messages"][0]["content"]
    assert "---EMAIL DATA---" in prompt
    assert "---END EMAIL DATA---" in prompt
