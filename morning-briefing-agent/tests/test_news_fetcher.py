from unittest.mock import MagicMock, patch
from src.news_fetcher import fetch_anthropic_post

SAMPLE_HTML = """
<html><body>
<article>
  <h3><a href="/engineering/writing-tools-for-agents">Writing effective tools for AI agents</a></h3>
  <p>Tool descriptions are prompts; this post teaches you how to write them well.</p>
</article>
</body></html>
"""


def test_returns_title_and_url():
    with patch("src.news_fetcher.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HTML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        result = fetch_anthropic_post()
    assert result["title"] == "Writing effective tools for AI agents"
    assert "anthropic.com" in result["url"]


def test_returns_none_on_network_error():
    with patch("src.news_fetcher.requests.get") as mock_get:
        mock_get.side_effect = Exception("timeout")
        result = fetch_anthropic_post()
    assert result is None


def test_returns_none_when_no_article_found():
    with patch("src.news_fetcher.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>No articles here</p></body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        result = fetch_anthropic_post()
    assert result is None
