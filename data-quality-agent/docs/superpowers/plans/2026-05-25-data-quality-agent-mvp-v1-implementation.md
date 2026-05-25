# Data Quality Agent MVP v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that profiles CSV, XLSX, and JSON files, evaluates built-in and config-driven quality rules, and writes Markdown plus JSON readiness reports.

**Architecture:** The package is split into small modules: CLI orchestration, config/model definitions, connectors, profiler, rule engine, verdict logic, and report writers. The core functions exchange typed Pydantic models so later database connectors and Python plugin checks can reuse the same profile/finding/report shape.

**Tech Stack:** Python 3.11+, pandas, openpyxl, typer, pydantic, pyyaml, pytest.

---

## File Structure

- `pyproject.toml`: package metadata, dependencies, CLI entry point, pytest config.
- `README.md`: install and usage instructions.
- `src/dq_agent/__init__.py`: package version.
- `src/dq_agent/__main__.py`: `python -m dq_agent` entry point.
- `src/dq_agent/cli.py`: Typer commands and terminal summary.
- `src/dq_agent/config.py`: YAML loading and Pydantic config models.
- `src/dq_agent/models.py`: profile, finding, report, and metadata models.
- `src/dq_agent/connectors.py`: CSV, XLSX, JSON, and JSONL loading.
- `src/dq_agent/profiler.py`: dataframe profiling and built-in profile findings.
- `src/dq_agent/rules.py`: required columns, non-null, allowed values, bounds, expected schema, and expression rules.
- `src/dq_agent/expressions.py`: constrained expression evaluator.
- `src/dq_agent/verdict.py`: deterministic readiness verdict and exit code mapping.
- `src/dq_agent/reports.py`: Markdown and JSON report generation.
- `tests/fixtures/`: sample datasets.
- `tests/test_*.py`: focused unit and CLI tests.

## Tasks

### Task 1: Scaffold Package And Core Models

- [ ] Create package metadata and source layout.
- [ ] Add Pydantic models for metadata, profiles, findings, and report payloads.
- [ ] Add tests that validate model defaults and serialization.

### Task 2: Implement Connectors

- [ ] Add connector tests for CSV, XLSX, JSON array, and JSONL.
- [ ] Implement file loading and source metadata.
- [ ] Return clear errors for missing files, unsupported formats, missing sheets, and empty datasets.

### Task 3: Implement Profiler

- [ ] Add profiler tests for nulls, duplicates, numeric stats, categorical stats, date stats, string stats, empty columns, and mixed-type detection.
- [ ] Implement dataframe profiling into structured models.
- [ ] Add warning/review findings for outliers, empty columns, mixed types, and duplicate primary keys.

### Task 4: Implement Rule Engine And Expressions

- [ ] Add rule tests for required columns, non-null, allowed values, numeric bounds, expected schema, and expressions.
- [ ] Implement constrained expression parsing for comparisons and boolean operators.
- [ ] Ensure findings include severity, affected columns, counts, capped examples, explanations, and remediation.

### Task 5: Implement Verdict And Reports

- [ ] Add tests for verdict selection and exit code mapping.
- [ ] Add tests for Markdown and JSON report contents.
- [ ] Implement memo sections, JSON report payload, timestamps, and output writing.

### Task 6: Implement CLI

- [ ] Add CLI tests for `profile` and `run`.
- [ ] Implement quick profile defaults and config-driven mode.
- [ ] Print concise terminal summaries.
- [ ] Return exit codes `0`, `1`, `2`, and `3`.

### Task 7: Documentation And Verification

- [ ] Update README with install, CLI usage, config example, outputs, and limitations.
- [ ] Run the full pytest suite.
- [ ] Run the CLI against fixture files and inspect generated Markdown/JSON.
- [ ] Commit implementation changes without staging unrelated parent-repo files.
