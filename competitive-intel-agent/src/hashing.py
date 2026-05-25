from __future__ import annotations
import hashlib
import re
from datetime import date

_WS = re.compile(r"\s+")
_TAG = re.compile(r"<[^>]+>")


def normalize(text: str) -> str:
    return _WS.sub(" ", _TAG.sub(" ", text)).strip().lower()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(title: str, entry_date: date, url: str) -> str:
    return _sha(f"{normalize(title)}|{entry_date.isoformat()}|{normalize(url)}")


def body_hash(body: str) -> str:
    return _sha(normalize(body))
