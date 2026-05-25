from __future__ import annotations

from src.config import Config
from src.models import Entry, Source


class Database:
    """Thin Supabase wrapper. All run-time persistence lives here."""

    def __init__(self, cfg: Config) -> None:
        from supabase import create_client  # lazy import keeps tests light
        self.client = create_client(cfg.supabase_url, cfg.supabase_service_key)

    # --- competitors ---
    def active_competitors(self) -> list[Source]:
        rows = self.client.table("competitors").select("*").eq(
            "active", True).execute().data
        return [Source(name=r["name"], feed_url=r["feed_url"],
                       html_url=r["html_url"], css_hint=r["css_hint"])
                for r in rows]

    def competitor_id(self, name: str) -> str | None:
        rows = self.client.table("competitors").select("id").eq(
            "name", name).execute().data
        return rows[0]["id"] if rows else None

    def upsert_competitor(self, row: dict) -> None:
        self.client.table("competitors").upsert(
            row, on_conflict="name").execute()

    # --- entries ---
    def known_hashes(self, competitor_name: str) -> dict[str, str]:
        cid = self.competitor_id(competitor_name)
        if not cid:
            return {}
        rows = self.client.table("changelog_entries").select(
            "content_hash, body_hash").eq("competitor_id", cid).execute().data
        return {r["content_hash"]: r["body_hash"] for r in rows}

    def insert_entry(self, competitor_id: str, entry: Entry,
                     run_id: str) -> str:
        row = {
            "competitor_id": competitor_id, "title": entry.title,
            "body": entry.body, "entry_date": entry.entry_date.isoformat(),
            "url": entry.url, "content_hash": entry.content_hash,
            "body_hash": entry.body_hash, "first_seen_run": run_id,
            "last_updated_run": run_id,
        }
        res = self.client.table("changelog_entries").upsert(
            row, on_conflict="competitor_id,content_hash",
            ignore_duplicates=True).execute()
        return res.data[0]["id"] if res.data else ""

    def update_entry_body(self, competitor_id: str, entry: Entry,
                          run_id: str) -> None:
        self.client.table("changelog_entries").update({
            "body": entry.body, "body_hash": entry.body_hash,
            "last_updated_run": run_id,
        }).eq("competitor_id", competitor_id).eq(
            "content_hash", entry.content_hash).execute()

    # --- runs ---
    def open_run(self) -> str:
        res = self.client.table("runs").insert(
            {"status": "running"}).execute()
        return res.data[0]["id"]

    def close_run(self, run_id: str, **fields) -> None:
        self.client.table("runs").update(fields).eq("id", run_id).execute()

    def recent_runs(self, limit: int = 3) -> list[dict]:
        return self.client.table("runs").select("*").order(
            "started_at", desc=True).limit(limit).execute().data

    # --- commentary ---
    def insert_commentary(self, row: dict) -> None:
        self.client.table("commentary").insert(row).execute()

    def last_watchlist(self) -> list[str]:
        rows = self.client.table("commentary").select("synthesis").eq(
            "kind", "synthesis").order(
            "created_at", desc=True).limit(1).execute().data
        if not rows or not rows[0].get("synthesis"):
            return []
        return rows[0]["synthesis"].get("watch_list", [])

    def execute_sql(self, sql: str) -> None:
        """Run raw DDL via the Supabase Postgres RPC `exec_sql`."""
        self.client.rpc("exec_sql", {"sql": sql}).execute()
