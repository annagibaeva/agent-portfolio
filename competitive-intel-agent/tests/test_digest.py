from __future__ import annotations
from datetime import date
from src.models import Change, Entry
from src.collector import CompetitorResult
from src.digest import render_digest, email_subject


def _change(title, tag, kind="new"):
    e = Entry(title=title, body="b", entry_date=date(2026, 5, 12),
              url="http://x", content_hash="c", body_hash="b")
    return Change(entry=e, kind=kind)


def _commentary(tags):
    return {
        "changes": [{"index": i, "so_what": f"reason {i}", "tag": t,
                     "confidence": 0.9} for i, t in enumerate(tags)],
        "synthesis": {"themes": ["theme one"], "watch_list": ["watch x"],
                      "suggested_response": "do y", "prior_watchlist_status": []},
    }


def test_render_includes_synthesis_and_changes():
    results = [CompetitorResult("Linear", ok=True,
               changes=[_change("SSO", "Threat")])]
    md = render_digest(results, _commentary(["Threat"]),
                       week="2026-W21", failed=[], stale=[])
    assert "2026-W21" in md
    assert "SSO" in md
    assert "Threat" in md
    assert "theme one" in md


def test_render_lists_failed_and_stale_sources():
    md = render_digest([], {"changes": [], "synthesis": {
        "themes": [], "watch_list": [], "suggested_response": "",
        "prior_watchlist_status": []}},
        week="2026-W21", failed=[("Asana", "timeout")], stale=["Jira"])
    assert "Asana" in md and "timeout" in md
    assert "Jira" in md


def test_email_subject_counts_tags():
    subj = email_subject(_commentary(["Threat", "Threat", "Parity gap"]),
                         week="2026-W21")
    assert "W21" in subj
    assert "2 Threat" in subj


def test_email_subject_quiet_week():
    subj = email_subject({"changes": [], "synthesis": {}}, week="2026-W21")
    assert "quiet" in subj.lower()
