"""Live eval runner — calls the real model and diffs against goldens.

Run manually before any prompt or model change. Approximate cost
per full sweep: $0.25-$1.00. Goldens live in evals/goldens/<case_id>.md.

Usage:
    python -m evals.run_live              # run all, diff vs goldens
    python -m evals.run_live --update     # overwrite goldens with current output
    python -m evals.run_live --case <id>  # run a single case
"""
from __future__ import annotations

import argparse
import asyncio
import difflib
import sys
from pathlib import Path

import agent
import intake
import main
from evals.cases import CASES, EvalCase

GOLDEN_DIR = Path(__file__).parent / "goldens"


async def _generate(case: EvalCase) -> tuple[str, list[str], int]:
    intake_text, u1 = await agent.run_intake(case.idea)
    questions = intake.parse_questions(intake_text)
    qa = [(q.text, case.answers.get(q.checklist_item, "guess")) for q in questions]
    draft_text, u2 = await agent.run_draft(case.idea, qa)
    prd = agent.extract_prd_block(draft_text)
    low = agent.low_confidence_sections(prd)
    tokens = agent.token_total([u1, u2])
    return prd, low, tokens


def _diff(golden: str, current: str, case_id: str) -> str:
    lines = difflib.unified_diff(
        golden.splitlines(keepends=True),
        current.splitlines(keepends=True),
        fromfile=f"{case_id}.golden",
        tofile=f"{case_id}.current",
        n=2,
    )
    return "".join(lines)


async def _run_one(case: EvalCase, *, update: bool) -> bool:
    print(f"\n=== {case.id} ===")
    try:
        prd, low, tokens = await _generate(case)
    except agent.BudgetError as exc:
        ok = case.expected == "budget_exceeded"
        print(f"BudgetError: {exc}  [{'EXPECTED' if ok else 'UNEXPECTED'}]")
        return ok
    except intake.RejectedIdeaError as exc:
        ok = case.expected == "rejected"
        print(f"RejectedIdeaError: {exc}  [{'EXPECTED' if ok else 'UNEXPECTED'}]")
        return ok

    if case.expected == "budget_exceeded":
        print("FAIL: expected BudgetError, got PRD")
        return False
    if case.expected == "rejected":
        print("FAIL: expected RejectedIdeaError, got PRD")
        return False

    if case.must_contain:
        missing = [s for s in case.must_contain if s not in prd]
        if missing:
            print(f"FAIL: PRD missing required substrings: {missing}")
            return False

    print(f"tokens: {tokens}  low-confidence sections: {len(low)}")
    if case.expected == "low_confidence" and len(low) < case.min_low_confidence:
        print(f"FAIL: expected ≥{case.min_low_confidence} low-conf, got {len(low)}")
        return False

    GOLDEN_DIR.mkdir(exist_ok=True)
    golden_path = GOLDEN_DIR / f"{case.id}.md"
    if update or not golden_path.exists():
        golden_path.write_text(prd + "\n", encoding="utf-8")
        print(f"{'updated' if update else 'created'} golden: {golden_path}")
        return True

    golden = golden_path.read_text(encoding="utf-8").rstrip("\n")
    if golden == prd:
        print("OK: matches golden")
        return True
    diff = _diff(golden, prd, case.id)
    print("DIFF vs golden:")
    print(diff)
    return False


async def _amain(args: argparse.Namespace) -> int:
    cases = CASES
    if args.case:
        cases = [c for c in CASES if c.id == args.case]
        if not cases:
            print(f"unknown case: {args.case}", file=sys.stderr)
            return 2

    results: list[tuple[str, bool]] = []
    for case in cases:
        ok = await _run_one(case, update=args.update)
        results.append((case.id, ok))

    print("\n--- summary ---")
    for cid, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {cid}")
    return 0 if all(ok for _, ok in results) else 1


def main_cli() -> int:
    p = argparse.ArgumentParser(description="Live eval runner for pm-workflow-agent")
    p.add_argument("--update", action="store_true", help="Overwrite goldens with current output")
    p.add_argument("--case", type=str, help="Run a single case by id")
    args = p.parse_args()
    try:
        agent.preflight()
    except agent.PreflightError as exc:
        print(f"Pre-flight failed: {exc}", file=sys.stderr)
        return 2
    return asyncio.run(_amain(args))


if __name__ == "__main__":
    raise SystemExit(main_cli())
