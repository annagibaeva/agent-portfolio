from __future__ import annotations
import time

import httpx

_UA = "CompetitiveIntelAgent/1.0 (+portfolio)"


class FetchError(RuntimeError):
    """Raised when a URL cannot be fetched after retries."""


def fetch_url(url: str, *, client: httpx.Client | None = None,
              retries: int = 2, timeout: float = 10.0) -> str:
    owns = client is None
    client = client or httpx.Client(timeout=timeout,
                                    headers={"User-Agent": _UA},
                                    follow_redirects=True)
    try:
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPError as exc:
                last = exc
                if attempt < retries:
                    time.sleep(2 ** attempt)
        raise FetchError(f"{url}: {last}")
    finally:
        if owns:
            client.close()
