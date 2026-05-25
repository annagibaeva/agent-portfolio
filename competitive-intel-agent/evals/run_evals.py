"""Run golden eval cases. Exits non-zero on any failure."""
from __future__ import annotations
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_server.server import collect_source
from src.commentary import CommentaryError, validate_commentary
from src.hashing import body_hash, content_hash

CASES = Path(__file__).parent / "cases"


def _known_from_titled(t: dict) -> dict[str, str]:
    ch = content_hash(t["title"], date.fromisoformat(t["date"]), t["url"])
    return {ch: body_hash(t["old_body"])}


def run_case(case: dict) -> tuple[bool, str]:
    if "expect_commentary_error" in case:
        try:
            validate_commentary(case["commentary_payload"], case["n_changes"])
            return False, "expected CommentaryError, none raised"
        except CommentaryError:
            return True, "ok"

    known = case.get("known", {})
    if "known_titled" in case:
        known = _known_from_titled(case["known_titled"])

    import mcp_server.server as server
    feed = case.get("feed")
    html = case.get("html", "")

    def fake_fetch(url, **k):
        from mcp_server.fetcher import FetchError
        if case.get("feed_error") and url == "http://feed":
            raise FetchError("feed down")
        return feed if url == "http://feed" and feed else html
    server.fetch_url = fake_fetch

    result = collect_source(
        feed_url="http://feed" if (feed or case.get("feed_error")) else None,
        html_url="http://html", css_hint=case.get("css_hint"),
        known=known, run_date=date(2026, 5, 19))

    if "expect_ok" in case and result["ok"] != case["expect_ok"]:
        return False, f"ok mismatch: {result}"
    if result["ok"]:
        if "expect_new" in case and len(result["new"]) != case["expect_new"]:
            return False, f"new count: {len(result['new'])}"
        if "expect_updated" in case and \
                len(result["updated"]) != case["expect_updated"]:
            return False, f"updated count: {len(result['updated'])}"
    if case.get("expect_seeded"):
        if not (not known and result["ok"] and result["new"]):
            return False, "expected seedable cold-start state"
    return True, "ok"


def main() -> int:
    failures = 0
    for path in sorted(CASES.glob("*.json")):
        case = json.loads(path.read_text())
        ok, msg = run_case(case)
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {case['name']}: {msg}")
        if not ok:
            failures += 1
    print(f"\n{failures} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
