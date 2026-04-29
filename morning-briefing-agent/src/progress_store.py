import json
from datetime import date


class ProgressStore:
    def __init__(self, path: str):
        self._path = path

    def _load(self) -> dict:
        with open(self._path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: dict) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def current_day(self, today: date | None = None) -> int:
        today = today or date.today()
        data = self._load()
        start = date.fromisoformat(data["start_date"])
        return (today - start).days + 1

    def log_run(self, day: int, topics: list[str], sent_at: str, summary: str) -> None:
        data = self._load()
        data["days"][str(day)] = {
            "date": date.today().isoformat(),
            "briefing_sent_at": sent_at,
            "topics": topics,
            "time_budget_mins": 480,
            "actual_mins_spent": None,
            "summary": summary,
        }
        self._save(data)

    def cache_anthropic_post(self, post: dict) -> None:
        data = self._load()
        data["last_anthropic_post"] = post
        self._save(data)

    def get_cached_post(self) -> dict | None:
        return self._load().get("last_anthropic_post")
