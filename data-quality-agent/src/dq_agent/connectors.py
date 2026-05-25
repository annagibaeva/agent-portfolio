from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from dq_agent.models import SourceMetadata


class ConnectorError(ValueError):
    pass


@dataclass(frozen=True)
class LoadedSource:
    dataframe: pd.DataFrame
    metadata: SourceMetadata


def infer_format(path: Path) -> str:
    return path.suffix.lstrip(".").lower()


def load_source(
    path: str | Path,
    source_format: str | None = None,
    sheet_name: str | None = None,
    dataset_name: str | None = None,
) -> LoadedSource:
    source_path = Path(path)
    if not source_path.exists():
        raise ConnectorError(f"File not found: {source_path}")

    fmt = (source_format or infer_format(source_path)).lower()
    try:
        if fmt == "csv":
            df = pd.read_csv(source_path)
        elif fmt == "xlsx":
            df = pd.read_excel(source_path, sheet_name=sheet_name or 0)
        elif fmt == "json":
            df = pd.read_json(source_path)
        elif fmt == "jsonl":
            df = pd.read_json(source_path, lines=True)
        else:
            raise ConnectorError(f"Unsupported format: {fmt}")
    except ValueError as exc:
        if fmt == "xlsx" and sheet_name:
            raise ConnectorError(f"Missing Excel sheet: {sheet_name}") from exc
        raise ConnectorError(f"Could not parse {source_path}: {exc}") from exc
    except Exception as exc:
        raise ConnectorError(f"Could not load {source_path}: {exc}") from exc

    if df.empty and len(df.columns) == 0:
        raise ConnectorError(f"Empty file or sheet: {source_path}")

    metadata = SourceMetadata(
        source_path=str(source_path),
        source_format=fmt,
        dataset_name=dataset_name,
        sheet_name=sheet_name if fmt == "xlsx" else None,
        row_count=len(df),
        columns=[str(column) for column in df.columns],
    )
    df.columns = metadata.columns
    return LoadedSource(dataframe=df, metadata=metadata)
