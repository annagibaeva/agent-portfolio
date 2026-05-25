from __future__ import annotations

from typing import Any
import warnings

import pandas as pd
from pandas.api.types import is_numeric_dtype

from dq_agent.models import (
    CategoricalProfile,
    ColumnProfile,
    DataProfile,
    DateProfile,
    Finding,
    NumericProfile,
    StringProfile,
)


def _clean_examples(values: list[Any], limit: int = 5) -> list[Any]:
    examples: list[Any] = []
    for value in values:
        if pd.isna(value):
            continue
        if hasattr(value, "item"):
            value = value.item()
        examples.append(value)
        if len(examples) >= limit:
            break
    return examples


def _infer_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "empty"
    if is_numeric_dtype(non_null):
        return "number"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(non_null, errors="coerce")
    if parsed.notna().sum() >= max(1, int(len(non_null) * 0.8)):
        return "date"
    return "string"


def _is_mixed_type(series: pd.Series) -> bool:
    non_null = series.dropna()
    types = {type(value).__name__ for value in non_null}
    return len(types) > 1


def _numeric_profile(series: pd.Series) -> NumericProfile:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return NumericProfile()
    q1 = float(numeric.quantile(0.25))
    q3 = float(numeric.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = numeric[(numeric < lower) | (numeric > upper)]
    return NumericProfile(
        min=float(numeric.min()),
        max=float(numeric.max()),
        mean=float(numeric.mean()),
        median=float(numeric.median()),
        std=float(numeric.std()) if len(numeric) > 1 else 0.0,
        p25=q1,
        p75=q3,
        outlier_count=int(len(outliers)),
        outlier_examples=_clean_examples(outliers.tolist()),
    )


def _categorical_profile(series: pd.Series) -> CategoricalProfile:
    non_null = series.dropna()
    counts = non_null.astype(str).value_counts().head(10)
    return CategoricalProfile(
        cardinality=int(non_null.nunique()),
        top_values={str(key): int(value) for key, value in counts.items()},
    )


def _date_profile(series: pd.Series) -> DateProfile:
    non_null = series.dropna()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(non_null, errors="coerce")
    valid = parsed.dropna()
    return DateProfile(
        min=valid.min().isoformat() if not valid.empty else None,
        max=valid.max().isoformat() if not valid.empty else None,
        parse_failure_count=int(parsed.isna().sum()),
    )


def _string_profile(series: pd.Series) -> StringProfile:
    min_length: int | None = None
    max_length: int | None = None
    sample_values: list[str] = []
    seen_samples: set[str] = set()

    for value in series:
        if pd.isna(value):
            continue
        text = str(value)
        length = len(text)
        min_length = length if min_length is None else min(min_length, length)
        max_length = length if max_length is None else max(max_length, length)
        if len(sample_values) < 5 and text not in seen_samples:
            sample_values.append(text)
            seen_samples.add(text)

    return StringProfile(
        min_length=min_length,
        max_length=max_length,
        sample_values=sample_values,
    )


def profile_dataframe(
    dataframe: pd.DataFrame,
    primary_key: str | None = None,
) -> tuple[DataProfile, list[Finding]]:
    columns: dict[str, ColumnProfile] = {}
    findings: list[Finding] = []

    for column in dataframe.columns:
        series = dataframe[column]
        null_count = int(series.isna().sum())
        non_null_count = int(series.notna().sum())
        inferred = _infer_type(series)
        is_empty = non_null_count == 0
        is_mixed = _is_mixed_type(series)
        numeric = _numeric_profile(series) if inferred == "number" else None
        categorical = _categorical_profile(series) if inferred in {"string", "date"} else None
        date = _date_profile(series) if inferred == "date" else None
        string = _string_profile(series) if inferred in {"string", "date"} else None

        columns[str(column)] = ColumnProfile(
            name=str(column),
            inferred_type=inferred,
            null_count=null_count,
            null_percentage=round((null_count / len(dataframe)) * 100, 2) if len(dataframe) else 0.0,
            non_null_count=non_null_count,
            numeric=numeric,
            categorical=categorical,
            date=date,
            string=string,
            is_empty=is_empty,
            is_mixed_type=is_mixed,
        )

        if is_empty:
            findings.append(
                Finding(
                    finding_id="empty-column",
                    title=f"Column `{column}` is empty",
                    severity="warning",
                    affected_columns=[str(column)],
                    failed_row_count=len(dataframe),
                    explanation="The column contains no non-null values.",
                    remediation="Remove the column or populate it before downstream use.",
                    impact="review",
                )
            )
        if is_mixed:
            findings.append(
                Finding(
                    finding_id="mixed-type-column",
                    title=f"Column `{column}` contains mixed Python value types",
                    severity="warning",
                    affected_columns=[str(column)],
                    explanation="The column contains multiple underlying value types.",
                    remediation="Normalize values to one expected type before analysis.",
                    impact="review",
                )
            )
        if numeric and numeric.outlier_count:
            findings.append(
                Finding(
                    finding_id="numeric-outlier-candidates",
                    title=f"Column `{column}` has numeric outlier candidates",
                    severity="warning",
                    affected_columns=[str(column)],
                    failed_row_count=numeric.outlier_count,
                    examples=numeric.outlier_examples,
                    explanation="Values fall outside the 1.5x IQR range.",
                    remediation="Review whether these values are valid business events or data errors.",
                    impact="review",
                )
            )

    duplicate_rows = int(dataframe.duplicated().sum())
    duplicate_primary_key_count: int | None = None
    if primary_key and primary_key in dataframe.columns:
        duplicate_primary_key_count = int(dataframe[primary_key].dropna().duplicated().sum())
        if duplicate_primary_key_count:
            findings.append(
                Finding(
                    finding_id="duplicate-primary-key",
                    title=f"Primary key `{primary_key}` contains duplicate values",
                    severity="error",
                    affected_columns=[primary_key],
                    failed_row_count=duplicate_primary_key_count,
                    examples=_clean_examples(dataframe.loc[dataframe[primary_key].duplicated(), primary_key].tolist()),
                    explanation="Primary key values should uniquely identify rows.",
                    remediation="Deduplicate records or choose a valid primary key.",
                )
            )

    return (
        DataProfile(
            row_count=len(dataframe),
            column_count=len(dataframe.columns),
            columns=columns,
            duplicate_row_count=duplicate_rows,
            duplicate_primary_key_count=duplicate_primary_key_count,
        ),
        findings,
    )
