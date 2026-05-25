import pandas as pd

from dq_agent.config import BoundsRule, ExpressionRule, RulesConfig
from dq_agent.rules import evaluate_rules


def test_evaluate_rules_returns_structured_findings():
    df = pd.DataFrame(
        {
            "customer_id": [1, None, 3],
            "status": ["active", "unknown", "paused"],
            "revenue": [10, -5, 20],
            "start_date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "end_date": ["2026-01-02", "2026-01-01", "2026-01-03"],
        }
    )
    rules = RulesConfig(
        required_columns=["customer_id", "email"],
        non_null=["customer_id"],
        allowed_values={"status": ["active", "paused"]},
        bounds={"revenue": BoundsRule(min=0)},
        expected_schema={"customer_id": "number", "status": "string"},
        expressions=[
            ExpressionRule(
                name="valid_date_order",
                expression="end_date >= start_date",
                severity="error",
            )
        ],
    )

    findings = evaluate_rules(df, rules)

    ids = {finding.finding_id for finding in findings}
    assert "required-column-missing" in ids
    assert "non-null-violation" in ids
    assert "allowed-values-violation" in ids
    assert "bounds-violation" in ids
    assert "expression-violation" in ids
    assert next(f for f in findings if f.finding_id == "expression-violation").failed_row_count == 1
