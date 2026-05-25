from pathlib import Path

import pandas as pd

from dq_agent.models import Finding, SourceMetadata
from dq_agent.profiler import profile_dataframe
from dq_agent.reports import build_report, write_json_report, write_markdown_memo


def test_report_writers_include_verdict_and_findings(tmp_path: Path):
    df = pd.DataFrame({"customer_id": [1, 2], "status": ["active", "paused"]})
    profile, _ = profile_dataframe(df)
    findings = [
        Finding(
            finding_id="example-warning",
            title="Example warning",
            severity="warning",
            affected_columns=["status"],
            explanation="A warning happened.",
            remediation="Review status values.",
        )
    ]
    metadata = SourceMetadata(
        source_path="customers.csv",
        source_format="csv",
        dataset_name="customers",
        row_count=2,
        columns=["customer_id", "status"],
    )

    report = build_report(metadata, profile, findings, dataset_name="customers")
    markdown_path = tmp_path / "memo.md"
    json_path = tmp_path / "report.json"
    write_markdown_memo(report, markdown_path)
    write_json_report(report, json_path)

    assert "Ready with caveats" in markdown_path.read_text(encoding="utf-8")
    assert "Example warning" in markdown_path.read_text(encoding="utf-8")
    assert '"verdict": "Ready with caveats"' in json_path.read_text(encoding="utf-8")
