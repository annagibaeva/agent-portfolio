"""Golden eval cases. Imported by test_offline.py and run_live.py."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvalCase:
    id: str
    idea: str
    answers: dict[str, str] = field(default_factory=dict)
    expected: str = "happy_path"
    # happy_path | low_confidence | budget_exceeded | rejected
    min_low_confidence: int = 0
    # For happy_path cases: substrings that must appear somewhere in the PRD.
    must_contain: tuple[str, ...] = ()


LONG_SSO_IDEA = (
    "Enterprise SSO rollout across TaskFlow covering SAML 2.0 and OIDC. "
    + ("Detailed requirements include identity provider federation, "
       "just-in-time provisioning, SCIM 2.0 user lifecycle, group-to-role "
       "mapping, audit logging, session policy enforcement, IdP-initiated "
       "and SP-initiated flows, multi-domain support, signing cert rotation, "
       "metadata exchange, error UX, and admin console screens. ") * 40
)


CASES: list[EvalCase] = [
    EvalCase(
        id="happy_path_complete",
        idea=(
            "A bulk-edit toolbar for TaskFlow lists so users can update "
            "status, assignee, or due date on 20+ tasks at once."
        ),
        answers={
            "problem": "Power users editing >10 tasks daily; 12 tickets last month.",
            "persona": "Project managers running 50+ task sprints.",
            "metric": "30% of weekly bulk-eligible sessions use it within 60 days.",
            "dependencies": "Bulk API v2 (shipping in 3.0).",
            "scope": "In: status/assignee/due date. Out: custom fields, archiving.",
            "release": "v3.1 / Q3 2026.",
        },
        expected="happy_path",
    ),
    EvalCase(
        id="heavy_dependencies",
        idea=(
            "An audit log export for TaskFlow that streams every workspace "
            "event to customer-owned S3 buckets in near-real-time, with PII "
            "redaction and SOC2-grade tamper-evidence."
        ),
        answers={
            "problem": "Top blocker in 6 enterprise deals; required for healthcare/finance verticals.",
            "persona": "Compliance officers and security teams at enterprise customers.",
            "metric": "100% of enterprise tenants enabled within 90 days of GA.",
            "dependencies": (
                "Data eng (Kinesis pipeline); Security (PII detection model + SOC2 audit); "
                "Legal (S3 cross-account DPA template); Platform (multi-region replication); "
                "Sales (enterprise gating in pricing)."
            ),
            "scope": (
                "In: workspace events, S3 destination, PII redaction. "
                "Out: Splunk/Datadog connectors, custom event filtering, retroactive export."
            ),
            "release": "v3.3 / Q1 2027.",
        },
        expected="happy_path",
        must_contain=("Data eng", "Security", "Legal", "Platform", "Sales"),
    ),
    EvalCase(
        id="non_idea_rejected",
        idea="asdf qwer zxcv",
        answers={},
        expected="rejected",
    ),
    EvalCase(
        id="low_confidence_partial_answers",
        idea=(
            "A Slack-style command palette in TaskFlow so users can search "
            "and jump to anything with Cmd+K."
        ),
        answers={
            "problem": "Navigation is slow for power users.",
            "persona": "Engineering-led teams.",
        },
        expected="low_confidence",
        min_low_confidence=3,
    ),
    EvalCase(
        id="vague_idea_many_questions",
        idea="Make TaskFlow better for managers.",
        answers={},
        expected="low_confidence",
        min_low_confidence=4,
    ),
    EvalCase(
        id="budget_exceeded",
        idea=LONG_SSO_IDEA,
        answers={
            "problem": "Enterprise sales blocked on SSO; 8 deals waiting.",
            "persona": "IT admins at 500+ employee customers.",
            "metric": "100% of new enterprise tenants onboarded via SSO.",
            "dependencies": "Identity team; security review; legal.",
            "scope": "In: SAML, OIDC, SCIM. Out: social login, passkeys.",
            "release": "v3.0 / Q2 2026.",
        },
        expected="budget_exceeded",
    ),
]
