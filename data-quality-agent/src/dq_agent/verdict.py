from __future__ import annotations

from dq_agent.models import Finding, Verdict


def determine_verdict(findings: list[Finding]) -> Verdict:
    if any(finding.severity == "error" for finding in findings):
        return "Not ready"
    if any(finding.impact == "review" for finding in findings):
        return "Needs review"
    if any(finding.severity == "warning" for finding in findings):
        return "Ready with caveats"
    return "Ready"


def exit_code_for_verdict(verdict: Verdict) -> int:
    if verdict == "Ready":
        return 0
    if verdict in {"Ready with caveats", "Needs review"}:
        return 1
    return 2
