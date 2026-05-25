from __future__ import annotations

import json
from pathlib import Path

from dq_agent.models import DataProfile, Finding, QualityReport, SourceMetadata
from dq_agent.verdict import determine_verdict


def build_report(
    source: SourceMetadata,
    profile: DataProfile,
    findings: list[Finding],
    dataset_name: str | None = None,
) -> QualityReport:
    name = dataset_name or source.dataset_name or Path(source.source_path).stem
    return QualityReport(
        source=source,
        dataset_name=name,
        profile=profile,
        findings=findings,
        verdict=determine_verdict(findings),
    )


def write_json_report(report: QualityReport, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, default=str),
        encoding="utf-8",
    )


def write_markdown_memo(report: QualityReport, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown_memo(report), encoding="utf-8")


def render_markdown_memo(report: QualityReport) -> str:
    severity_counts = {
        "error": sum(1 for finding in report.findings if finding.severity == "error"),
        "warning": sum(1 for finding in report.findings if finding.severity == "warning"),
        "info": sum(1 for finding in report.findings if finding.severity == "info"),
    }
    findings = sorted(report.findings, key=lambda f: {"error": 0, "warning": 1, "info": 2}[f.severity])
    lines = [
        f"# Data Readiness Memo: {report.dataset_name}",
        "",
        "## Verdict",
        report.verdict,
        "",
        "## Executive Summary",
        (
            f"Reviewed {report.profile.row_count:,} rows and {report.profile.column_count:,} columns from "
            f"`{report.source.source_path}`. Findings: {severity_counts['error']} errors, "
            f"{severity_counts['warning']} warnings, {severity_counts['info']} info."
        ),
        "",
        "## Key Findings",
    ]
    if findings:
        for finding in findings:
            lines.append(f"- **{finding.severity.upper()}**: {finding.title}")
    else:
        lines.append("- No quality issues were found.")

    lines.extend(["", "## Recommended Fixes"])
    if findings:
        for finding in findings:
            lines.append(f"- {finding.remediation}")
    else:
        lines.append("- No fixes are required.")

    lines.extend(
        [
            "",
            "## Next Steps",
            "1. Use this memo for first-pass review.",
            f"2. Draft a reusable config with `dq-agent init-config {report.source.source_path}`.",
            "3. Edit the config to reflect the dataset contract for your team.",
            "4. Re-run repeatable checks with `dq-agent run <config.yml>`.",
            "",
            "## Dataset Profile",
            f"- Source format: `{report.source.source_format}`",
            f"- Rows: {report.profile.row_count:,}",
            f"- Columns: {report.profile.column_count:,}",
            f"- Duplicate rows: {report.profile.duplicate_row_count:,}",
            "",
            "## Rule Results",
            "- Rule result tracking is represented by the findings list in MVP v1.",
            "",
            "## Technical Appendix",
        ]
    )
    for column_name, column in report.profile.columns.items():
        lines.append(
            f"- `{column_name}`: type `{column.inferred_type}`, nulls {column.null_count} "
            f"({column.null_percentage}%)"
        )
    return "\n".join(lines) + "\n"
