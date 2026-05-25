"""Apply db/schema.sql and seed the competitors table. Idempotent."""
from __future__ import annotations
from pathlib import Path

import yaml

from src.config import load_config
from src.db import Database


def main() -> None:
    cfg = load_config()
    db = Database(cfg)
    schema = (Path(__file__).parent / "db" / "schema.sql").read_text()
    db.execute_sql(schema)
    seeds = yaml.safe_load(
        (Path(__file__).parent / "seeds" / "competitors.yaml").read_text())
    for s in seeds:
        db.upsert_competitor(s)
    print(f"Schema applied. Seeded {len(seeds)} competitors.")


if __name__ == "__main__":
    main()
