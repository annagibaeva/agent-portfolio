from __future__ import annotations
import httpx
import pytest
from mcp_server.fetcher import fetch_url, FetchError


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_url_returns_body_on_200():
    def handler(req):
        return httpx.Response(200, text="hello")
    assert fetch_url("http://x", client=_client(handler)) == "hello"


def test_fetch_url_retries_then_raises():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(500)
    with pytest.raises(FetchError):
        fetch_url("http://x", client=_client(handler), retries=2)
    assert calls["n"] == 3
