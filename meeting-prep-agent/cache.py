"""Per-run memoization for attendee-keyed API results."""
from __future__ import annotations

_cache: dict[tuple[str, str], object] = {}


def get(namespace: str, key: str):
    return _cache.get((namespace, key))


def set_(namespace: str, key: str, value):
    _cache[(namespace, key)] = value


def clear():
    _cache.clear()
