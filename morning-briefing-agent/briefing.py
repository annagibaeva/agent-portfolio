import os
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime

from config import (
    PLAN_FILE, RESOURCES_FILE, PROGRESS_FILE, LOG_FILE,
    TOKEN_FILE, CREDENTIALS_FILE, GOOGLE_SCOPES,
    EMAIL_TO,
)
from google.auth.exceptions import RefreshError
from src.alerts import send_smtp_alert
from src.auth import get_google_credentials
from src.calendar_client import list_today_events
from src.gmail_client import search_meeting_threads, search_substacks, send_email
from src.news_fetcher import fetch_anthropic_post
from src.composer import compose_brief_sections
from src.email_builder import build_email, build_subject
from src.plan_loader import PlanLoader
from src.progress_store import ProgressStore

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def run(today: date | None = None) -> None:
    today = today or date.today()
    store = ProgressStore(PROGRESS_FILE)
    day = store.current_day(today=today)
    week = ((day - 1) // 7) + 1
    pct_complete = min(100, round((day - 1) / 21 * 100))
    date_str = today.isoformat()

    loader = PlanLoader(PLAN_FILE, RESOURCES_FILE)
    try:
        day_content = loader.load(day=day)
    except ValueError:
        day_content = {
            "day": day, "topic": f"Day {day} (beyond plan)",
            "morning_tasks": [], "afternoon_tasks": [],
            "quiz_count": 0, "star_resources": [],
        }

    try:
        creds = get_google_credentials(TOKEN_FILE, CREDENTIALS_FILE, GOOGLE_SCOPES)
    except RefreshError as e:
        logging.error("!!! GOOGLE_AUTH_EXPIRED !!! Re-run `python auth_setup.py` to mint a fresh token. Detail: %s", e)
        send_smtp_alert(
            subject="[morning-briefing-agent] Google OAuth token expired — action required",
            body=(
                "The morning-briefing-agent failed to refresh its Google OAuth token "
                "and cannot read Calendar/Gmail or send the briefing.\n\n"
                "Fix: run `python auth_setup.py` in the agent directory to re-authorize.\n\n"
                f"Error: {e}\n"
            ),
        )
        creds = None
    except Exception:
        logging.exception("Google auth failed — run with no credentials")
        creds = None

    results = {}
    def fetch_calendar(): return list_today_events(creds=creds, today=today)
    def fetch_meetings(): return search_meeting_threads(creds=creds)
    def fetch_subs(): return search_substacks(creds=creds)
    def fetch_news(): return fetch_anthropic_post()

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(fetch_calendar): "events",
            executor.submit(fetch_meetings): "meeting_threads",
            executor.submit(fetch_subs): "substacks",
            executor.submit(fetch_news): "anthropic_post",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception:
                results[key] = None

    if results.get("anthropic_post"):
        store.cache_anthropic_post(results["anthropic_post"])
    else:
        results["anthropic_post"] = store.get_cached_post()

    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        composed = compose_brief_sections({**results, "day_content": day_content}, api_key=api_key)

        email_data = {
            "day": day,
            "week": week,
            "pct_complete": pct_complete,
            "date_str": date_str,
            "events": results.get("events") or [],
            "events_unavailable": results.get("events") is None,
            "gmail_unavailable": results.get("meeting_threads") is None,
            "meeting_context": composed["meeting_context"],
            "day_content": day_content,
            "ai_pulse": composed["ai_pulse"],
            "anthropic_post": results.get("anthropic_post"),
        }
        html = build_email(email_data)
        subject = build_subject(day=day, date_str=date_str)
        sent = send_email(subject=subject, html_body=html, to=EMAIL_TO, creds=creds)

        cal_count = len(results.get("events") or [])
        thread_count = len(results.get("meeting_threads") or [])
        sub_count = len(results.get("substacks") or [])
        status = "OK" if sent else "SEND_FAILED"
        summary = f"Day {day} | {status} | calendar:{cal_count} events | gmail:{thread_count} threads, {sub_count} substacks | sent={sent}"
        if sent:
            logging.info(summary)
        else:
            logging.error(summary)
        store.log_run(day=day, topics=[day_content["topic"]], sent_at=datetime.now().strftime("%H:%M:%S"), summary=summary)
        if not sent:
            sys.exit(1)
    except Exception as e:
        logging.exception("Briefing run failed during compose/send/log")
        store.log_run(
            day=day,
            topics=[day_content["topic"]],
            sent_at=datetime.now().strftime("%H:%M:%S"),
            summary=f"Day {day} | FAILED | {e}",
        )


if __name__ == "__main__":
    run()
