from __future__ import annotations

from typing import Any

import pandas as pd

from dq_agent.config import RulesConfig
from dq_agent.expressions import ExpressionError, evaluate_expression
from dq_agent.models import Finding
from dq_agent.profiler import _infer_type


def _examples(series: pd.Series, mask: pd.Series | None = None, limit: int = 5) -> list[Any]:
    values = series[mask] if mask is not None else series
    cleaned: list[Any] = []
    for value in values.dropna().head(limit).tolist():
        if hasattr(value, "item"):
            value = value.item()
        cleaned.append(value)
    return cleaned


def evaluate_rules(dataframe: pd.DataFrame, rules: RulesConfig) -> list[Finding]:
    findings: list[Finding] = []

    for column in rules.required_columns:
        if column not in dataframe.columns:
            findings.append(
                Finding(
                    finding_id="required-column-missing",
                    title=f"Required column `{column}` is missing",
                    severity="error",
                    affected_columns=[column],
                    explanation="The dataset does not include a configured required column.",
                    remediation="Add the missing column or update the dataset contract.",
                )
            )

    for column in rules.non_null:
        if column not in dataframe.columns:
            continue
        mask = dataframe[column].isna()
        if mask.any():
            findings.append(
                Finding(
                    finding_id="non-null-violation",
                    title=f"Column `{column}` contains null values",
                    severity="error",
                    affected_columns=[column],
                    failed_row_count=int(mask.sum()),
                    explanation="The column is configured as required for every row.",
                    remediation="Backfill, remove, or correct rows with missing values.",
                )
            )

    for column, allowed in rules.allowed_values.items():
        if column not in dataframe.columns:
            continue
        mask = dataframe[column].notna() & ~dataframe[column].isin(allowed)
        if mask.any():
            findings.append(
                Finding(
                    finding_id="allowed-values-violation",
                    title=f"Column `{column}` contains unexpected values",
                    severity="error",
                    affected_columns=[column],
                    failed_row_count=int(mask.sum()),
                    examples=_examples(dataframe[column], mask),
                    explanation=f"Values must be one of: {', '.join(map(str, allowed))}.",
                    remediation="Normalize unexpected values or update the allowed values rule.",
                )
            )

    for column, bounds in rules.bounds.items():
        if column not in dataframe.columns:
            continue
        numeric = pd.to_numeric(dataframe[column], errors="coerce")
        mask = pd.Series(False, index=dataframe.index)
        if bounds.min is not None:
            mask = mask | (numeric < bounds.min)
        if bounds.max is not None:
            mask = mask | (numeric > bounds.max)
        mask = mask.fillna(False)
        if mask.any():
            findings.append(
                Finding(
                    finding_id="bounds-violation",
                    title=f"Column `{column}` violates configured numeric bounds",
                    severity=bounds.severity,
                    affected_columns=[column],
                    failed_row_count=int(mask.sum()),
                    examples=_examples(dataframe[column], mask),
                    explanation="One or more values fall outside configured min/max bounds.",
                    remediation="Correct invalid values or adjust the configured bounds.",
                )
            )

    for column, expected_type in rules.expected_schema.items():
        if column not in dataframe.columns:
            continue
        actual = _infer_type(dataframe[column])
        if actual != expected_type:
            findings.append(
                Finding(
                    finding_id="schema-type-mismatch",
                    title=f"Column `{column}` type differs from expected schema",
                    severity="warning",
                    affected_columns=[column],
                    explanation=f"Expected `{expected_type}` but inferred `{actual}`.",
                    remediation="Confirm the schema contract or normalize the column type.",
                    impact="review",
                )
            )

    for expression_rule in rules.expressions:
        try:
            passed = evaluate_expression(dataframe, expression_rule.expression)
        except ExpressionError as exc:
            findings.append(
                Finding(
                    finding_id="expression-error",
                    title=f"Expression rule `{expression_rule.name}` could not be evaluated",
                    severity="error",
                    explanation=str(exc),
                    remediation="Fix the expression syntax or referenced columns.",
                )
            )
            continue
        mask = ~passed
        if mask.any():
            findings.append(
                Finding(
                    finding_id="expression-violation",
                    title=f"Expression rule `{expression_rule.name}` failed",
                    severity=expression_rule.severity,
                    failed_row_count=int(mask.sum()),
                    examples=dataframe.loc[mask].head(5).to_dict(orient="records"),
                    explanation=f"Rows must satisfy: {expression_rule.expression}",
                    remediation="Correct rows that violate the expression or update the rule.",
                )
            )

    return findings
