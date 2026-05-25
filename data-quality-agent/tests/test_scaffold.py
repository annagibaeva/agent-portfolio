from pathlib import Path

import pandas as pd

from dq_agent.models import SourceMetadata
from dq_agent.scaffold import draft_config_text


def test_draft_config_text_uses_profiled_columns_and_low_cardinality_values(tmp_path: Path):
    source = tmp_path / "customers.csv"
    metadata = SourceMetadata(
        source_path=str(source),
        source_format="csv",
        dataset_name="customers",
        row_count=2,
        columns=["customer_id", "email", "status", "revenue"],
    )
    dataframe = pd.DataFrame(
        {
            "customer_id": [1, 2],
            "email": ["a@example.com", "b@example.com"],
            "status": ["active", "paused"],
            "revenue": [10, 20],
        }
    )

    text = draft_config_text(
        dataframe,
        metadata,
        output_path=tmp_path / "customers-dq.yml",
        dataset_name="customers",
        primary_key="customer_id",
    )

    assert "required_columns:" in text
    assert "- customer_id" in text
    assert "non_null:" in text
    assert "- customer_id" in text
    assert "allowed_values:" in text
    assert "status:" in text
    assert "- active" in text
    assert "email:" not in text
    assert "output:" in text
