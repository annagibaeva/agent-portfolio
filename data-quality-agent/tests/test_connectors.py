from pathlib import Path

import pandas as pd
import pytest

from dq_agent.connectors import ConnectorError, load_source


def test_load_csv_returns_dataframe_and_metadata(tmp_path: Path):
    source = tmp_path / "customers.csv"
    source.write_text("customer_id,email\n1,a@example.com\n", encoding="utf-8")

    loaded = load_source(source)

    assert list(loaded.dataframe.columns) == ["customer_id", "email"]
    assert loaded.metadata.source_format == "csv"
    assert loaded.metadata.row_count == 1


def test_load_xlsx_uses_selected_sheet(tmp_path: Path):
    source = tmp_path / "book.xlsx"
    with pd.ExcelWriter(source) as writer:
        pd.DataFrame({"ignore": [1]}).to_excel(writer, sheet_name="Other", index=False)
        pd.DataFrame({"customer_id": [1]}).to_excel(writer, sheet_name="Customers", index=False)

    loaded = load_source(source, sheet_name="Customers")

    assert list(loaded.dataframe.columns) == ["customer_id"]
    assert loaded.metadata.sheet_name == "Customers"


def test_load_jsonl(tmp_path: Path):
    source = tmp_path / "events.jsonl"
    source.write_text('{"event":"created"}\n{"event":"updated"}\n', encoding="utf-8")

    loaded = load_source(source, source_format="jsonl")

    assert loaded.metadata.row_count == 2
    assert loaded.dataframe["event"].tolist() == ["created", "updated"]


def test_unsupported_format_raises_clear_error(tmp_path: Path):
    source = tmp_path / "data.parquet"
    source.write_text("not supported", encoding="utf-8")

    with pytest.raises(ConnectorError, match="Unsupported format"):
        load_source(source)
