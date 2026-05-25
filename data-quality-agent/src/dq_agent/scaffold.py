from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from dq_agent.connectors import infer_format
from dq_agent.models import SourceMetadata


def guess_primary_key(columns: list[str]) -> str | None:
    for column in columns:
        normalized = column.lower()
        if normalized in {"id", "uuid"} or normalized.endswith("_id"):
            return column
    return None


def default_config_path(source_path: str | Path) -> Path:
    source = Path(source_path)
    return source.parent / f"{source.stem}-dq-config.yml"


def draft_config_text(
    dataframe: pd.DataFrame,
    metadata: SourceMetadata,
    output_path: str | Path,
    dataset_name: str | None = None,
    primary_key: str | None = None,
) -> str:
    columns = [str(column) for column in dataframe.columns]
    name = dataset_name or metadata.dataset_name or Path(metadata.source_path).stem
    key = primary_key or guess_primary_key(columns)
    config: dict[str, Any] = {
        "input": {
            "path": metadata.source_path,
            "format": metadata.source_format or infer_format(Path(metadata.source_path)),
        },
        "dataset": {
            "name": name,
            "primary_key": key,
        },
        "rules": {
            "required_columns": columns,
            "non_null": [key] if key else [],
            "allowed_values": _suggest_allowed_values(dataframe),
            "bounds": {},
            "expressions": [],
        },
        "output": {
            "markdown": str(Path(output_path).with_name(f"{name}-readiness.md")),
            "json": str(Path(output_path).with_name(f"{name}-profile.json")),
        },
    }
    return yaml.safe_dump(config, sort_keys=False, allow_unicode=False)


def write_draft_config(
    dataframe: pd.DataFrame,
    metadata: SourceMetadata,
    output_path: str | Path,
    dataset_name: str | None = None,
    primary_key: str | None = None,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        draft_config_text(dataframe, metadata, path, dataset_name=dataset_name, primary_key=primary_key),
        encoding="utf-8",
    )
    return path


def _suggest_allowed_values(dataframe: pd.DataFrame, max_values: int = 10) -> dict[str, list[Any]]:
    suggestions: dict[str, list[Any]] = {}
    for column in dataframe.columns:
        column_name = str(column)
        if not _looks_like_enum_column(column_name):
            continue
        series = dataframe[column].dropna()
        if series.empty:
            continue
        if pd.api.types.is_numeric_dtype(series):
            continue
        values = sorted(str(value) for value in series.astype(str).unique().tolist())
        if 1 < len(values) <= max_values:
            suggestions[column_name] = values
    return suggestions


def _looks_like_enum_column(column_name: str) -> bool:
    normalized = column_name.lower()
    if normalized == "id" or normalized.endswith("_id"):
        return False
    excluded_tokens = ("uuid", "email", "phone", "url", "name")
    if any(token in normalized for token in excluded_tokens):
        return False
    if normalized.endswith("_date") or normalized.endswith("_time") or normalized.endswith("_at"):
        return False
    enum_tokens = ("status", "type", "category", "segment", "tier", "plan", "state", "country", "region")
    return any(token in normalized for token in enum_tokens)
