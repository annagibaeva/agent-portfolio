"""Competitive Intel Agent — weekly orchestrator.

Usage:
  python main.py                      dry-run (no email)
  python main.py --send               full run, sends email
  python main.py --competitor Linear  re-run one source
  python main.py --demo               run against local fixtures
"""
from __future__ import annotations
import argparse
import sys
from datetime import date
from pathlib import Path

from src.collector import collect_all
from src.commentary import CommentaryError, generate_commentary
from src.config import load_config
from src.db import Database
from src.digest import email_subject, render_digest, render_html
from src.emailer import send_digest
from src.run_logger import RunLogger
from src.staleness import stale_sources

LOG_DIR = Path(__file__).parent / "logs"
DIGEST_DIR = Path(__file__).parent / "digests"


def iso_week_label(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def build_history(db, names: list[str]) -> dict[str, list[int]]:
    """Per-competitor entry counts for the 2 prior runs, most recent first."""
    runs = db.recent_runs(limit=3)
    prior_ids = [r["id"] for r in runs]
    history: dict[str, list[int]] = {}
    for name in names:
        counts = db.entry_counts_by_run(name, prior_ids)
        history[name] = [counts.get(rid, 0) for rid in prior_ids]
    return history


def run(send: bool, only: str | None) -> int:
    cfg = load_config()
    db = Database(cfg)
    run_id = db.open_run()
    log = RunLogger(run_id=run_id, log_dir=LOG_DIR)
    today = date.today()
    week = iso_week_label(today)

    sources = db.active_competitors()
    if only:
        sources = [s for s in sources if s.name == only]
    if not sources:
        db.close_run(run_id, status="failed", outcome="no competitors")
        log.summary(competitors_ok=0, competitors_failed=0, new_entries=0,
                    tokens=0, outcome="failed: no competitors")
        return 1

    names = [s.name for s in sources]
    history = build_history(db, names)
    results = collect_all(sources, db, run_id=run_id, run_date=today)
    for r in results:
        log.event("collect", competitor=r.name, ok=r.ok,
                  seeded=r.seeded, changes=len(r.changes), error=r.error)

    failed = [(r.name, r.error or "unknown") for r in results if not r.ok]
    if len(failed) == len(results):
        db.close_run(run_id, status="failed", competitors_failed=len(failed),
                     outcome="all sources failed")
        log.summary(competitors_ok=0, competitors_failed=len(failed),
                    new_entries=0, tokens=0, outcome="failed: all sources down")
        return 1

    all_changes = [c for r in results for c in r.changes]
    tokens = 0
    commentary: dict = {"changes": [], "synthesis": {}}
    if all_changes:
        try:
            prior = db.last_watchlist()
            commentary, tokens = generate_commentary(
                cfg.anthropic_api_key, all_changes, prior)
            for i, c in enumerate(commentary["changes"]):
                db.insert_commentary({
                    "run_id": run_id, "kind": "per_change",
                    "so_what": c["so_what"], "tag": c["tag"],
                    "confidence": c["confidence"]})
            db.insert_commentary({"run_id": run_id, "kind": "synthesis",
                                  "synthesis": commentary["synthesis"]})
        except CommentaryError as exc:
            log.event("commentary_failed", error=str(exc))
            commentary = {"changes": [], "synthesis": {}}

    stale = stale_sources(results, history, threshold=3)
    markdown = render_digest(results, commentary, week=week,
                             failed=failed, stale=stale)
    DIGEST_DIR.mkdir(exist_ok=True)
    (DIGEST_DIR / f"{week}.md").write_text(markdown, encoding="utf-8")

    subject = email_subject(commentary, week=week)
    sent = send_digest(
        subject=subject, html=render_html(markdown),
        recipient=cfg.digest_recipient, smtp_host=cfg.smtp_host,
        smtp_port=cfg.smtp_port, smtp_user=cfg.smtp_user,
        smtp_password=cfg.smtp_password, dry_run=not send)

    status = "partial" if failed else "success"
    new_entries = sum(len(r.changes) for r in results)
    db.close_run(run_id, status=status, competitors_ok=len(results) - len(failed),
                 competitors_failed=len(failed), new_entries=new_entries,
                 tokens=tokens, outcome=f"digest written; email sent={sent}")
    print(log.summary(competitors_ok=len(results) - len(failed),
                      competitors_failed=len(failed), new_entries=new_entries,
                      tokens=tokens, outcome=status))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Competitive Intel Agent")
    p.add_argument("--send", action="store_true", help="send the digest email")
    p.add_argument("--competitor", help="re-run a single competitor by name")
    p.add_argument("--demo", action="store_true", help="run against fixtures")
    args = p.parse_args()
    if args.demo:
        from demo import run_demo
        return run_demo()
    return run(send=args.send, only=args.competitor)


if __name__ == "__main__":
    sys.exit(main())
