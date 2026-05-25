import pandas as pd

from dq_agent.profiler import profile_dataframe


def test_profile_dataframe_calculates_column_stats_and_findings():
    df = pd.DataFrame(
        {
            "customer_id": [1, 1, None, 4],
            "revenue": [10, 12, 11, 5000],
            "status": ["active", "paused", "active", "cancelled"],
            "created_at": ["2026-01-01", "2026-01-02", "bad-date", "2026-01-04"],
            "empty_col": [None, None, None, None],
            "mixed": [1, "two", 3, "four"],
        }
    )

    profile, findings = profile_dataframe(df, primary_key="customer_id")

    assert profile.row_count == 4
    assert profile.columns["customer_id"].null_count == 1
    assert profile.columns["revenue"].numeric.max == 5000
    assert profile.columns["status"].categorical.cardinality == 3
    assert profile.duplicate_row_count == 0
    assert any(f.finding_id == "duplicate-primary-key" for f in findings)
    assert any(f.finding_id == "empty-column" and f.affected_columns == ["empty_col"] for f in findings)
    assert any(f.finding_id == "mixed-type-column" and f.affected_columns == ["mixed"] for f in findings)
