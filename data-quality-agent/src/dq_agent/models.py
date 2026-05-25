from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


Severity = Literal["info", "warning", "error"]
Verdict = Literal["Ready", "Ready with caveats", "Needs review", "Not ready"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SourceMetadata(BaseModel):
    source_path: str
    source_format: str
    dataset_name: str | None = None
    sheet_name: str | None = None
    loaded_at: str = Field(default_factory=utc_now_iso)
    row_count: int
    columns: list[str]


class NumericProfile(BaseModel):
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    p25: float | None = None
    p75: float | None = None
    outlier_count: int = 0
    outlier_examples: list[Any] = Field(default_factory=list)


class CategoricalProfile(BaseModel):
    cardinality: int = 0
    top_values: dict[str, int] = Field(default_factory=dict)


class DateProfile(BaseModel):
    min: str | None = None
    max: str | None = None
    parse_failure_count: int = 0


class StringProfile(BaseModel):
    min_length: int | None = None
    max_length: int | None = None
    sample_values: list[str] = Field(default_factory=list)


class ColumnProfile(BaseModel):
    name: str
    inferred_type: str
    null_count: int
    null_percentage: float
    non_null_count: int
    numeric: NumericProfile | None = None
    categorical: CategoricalProfile | None = None
    date: DateProfile | None = None
    string: StringProfile | None = None
    is_empty: bool = False
    is_mixed_type: bool = False


class DataProfile(BaseModel):
    row_count: int
    column_count: int
    columns: dict[str, ColumnProfile]
    duplicate_row_count: int = 0
    duplicate_primary_key_count: int | None = None


class Finding(BaseModel):
    finding_id: str
    title: str
    severity: Severity
    affected_columns: list[str] = Field(default_factory=list)
    failed_row_count: int | None = None
    examples: list[Any] = Field(default_factory=list)
    explanation: str
    remediation: str
    impact: Literal["standard", "review"] = "standard"


class RuleResult(BaseModel):
    name: str
    passed: bool
    finding_id: str | None = None


class QualityReport(BaseModel):
    source: SourceMetadata
    dataset_name: str
    profile: DataProfile
    findings: list[Finding]
    rule_results: list[RuleResult] = Field(default_factory=list)
    verdict: Verdict
    generated_at: str = Field(default_factory=utc_now_iso)
    tool_version: str = "0.1.0"
