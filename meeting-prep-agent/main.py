"""Meeting Prep Agent — CLI entry point."""
from __future__ import annotations

import argparse
import asyncio
import sys

# Windows console defaults to cp1252 which chokes on unicode (≠, em-dashes, etc.)
# Reconfigure stdio to UTF-8 before anything else prints.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, Exception):
    pass

from dotenv import load_dotenv

import auth
import cache
import logger
import meetings
from agent import run_for_meeting


def _parse_args():
    p = argparse.ArgumentParser(description="Meeting Prep Agent")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--daily", action="store_true", help="Brief every relevant meeting today")
    g.add_argument("--meeting", type=str, help="Substring match a meeting in the next 7d")
    g.add_argument("--setup-auth", action="store_true", help="Run Google OAuth setup")
    p.add_argument("--tz", type=str, default=None, help="Override USER_TZ")
    return p.parse_args()


async def _run_daily(run_id: str, tz: str | None) -> int:
    ms = meetings.list_today(tz_name=tz)
    if not ms:
        print("No meetings to brief today.")
        return 0
    print(f"Briefing {len(ms)} meeting(s)...")
    failures = 0
    for m in ms:
        cache.clear()
        print(f"  → {m.title} ({m.start_local})")
        result = await run_for_meeting(m, run_id)
        if result["status"] != "ok":
            failures += 1
            print(f"    error: {result['error']}")
    print(f"Done. {len(ms) - failures}/{len(ms)} succeeded.")
    return 1 if failures else 0


async def _run_one(run_id: str, query_str: str, tz: str | None) -> int:
    m = meetings.find_by_query(query_str, tz_name=tz)
    if not m:
        print(f"No meeting matching '{query_str}' in the next 7 days.")
        return 1
    print(f"Briefing: {m.title} ({m.start_local})")
    cache.clear()
    result = await run_for_meeting(m, run_id)
    if result["status"] == "ok":
        print("ok")
        return 0
    print(f"error: {result['error']}")
    return 1


def main() -> int:
    load_dotenv()
    args = _parse_args()

    if args.setup_auth:
        auth.setup_auth()
        return 0

    run_id = logger.new_run_id()
    print(f"run_id: {run_id}")

    if args.daily:
        return asyncio.run(_run_daily(run_id, args.tz))
    if args.meeting:
        return asyncio.run(_run_one(run_id, args.meeting, args.tz))

    print("Specify --daily, --meeting <query>, or --setup-auth.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
