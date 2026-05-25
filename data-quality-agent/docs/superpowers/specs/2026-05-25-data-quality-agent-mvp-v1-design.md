# Data Quality Agent MVP v1 Design

## Recommendation

Build MVP v1 as a Python CLI for data analysts and data engineers. The agent will inspect local CSV, XLSX, and JSON files, profile the data, run built-in quality checks plus configurable validation rules, and produce both a Markdown data-readiness memo and a machine-readable JSON report.

The design should favor a clear, modular engine over a heavyweight data quality framework. The first version should be easy to run locally, easy to configure, and structured so future versions can add database connectors, historical drift detection, and Python plugin checks without rewriting the core.

## Goals

- Support quick one-off profiling from the command line.
- Support repeatable config-driven runs for team workflows.
- Profile CSV, XLSX, and JSON files.
- Identify common quality issues: nulls, duplicates, suspicious values, outliers, invalid values, and schema mismatches against an expected schema.
- Support declarative rules plus lightweight expressions.
- Produce a mixed-audience data-readiness memo with a clear verdict and technical appendix.
- Produce a JSON report that can later support CI, dashboards, or automation.
- Keep the architecture extensible for later database connections and Python plugin checks.

## Non-Goals For MVP v1

- Database connections.
- Historical profile storage.
- Automated schema drift detection across prior runs.
- Python plugin checks.
- Web UI.
- Scheduling.
- Cloud storage.
- PII classification.
- Automatic data repair.
- Multi-sheet Excel profiling in a single run.

## Target Users

Primary users are data analysts, data scientists, and data engineers who need to quickly assess whether a dataset is ready for analysis, modeling, reporting, or downstream pipeline use.

The CLI is technical-user first, but the Markdown memo should be readable by a mixed audience. It should lead with a short verdict and executive summary, then provide detailed evidence in the technical appendix.

## CLI Interface

The CLI should support two modes.

### Quick Profile Mode

Used for fast, local inspection without a config file.

```bash
dq-agent profile data.csv
dq-agent profile data.xlsx --sheet Customers
dq-agent profile data.json --out reports/readiness.md
```

Defaults:

- Infer file format from extension unless `--format` is provided.
- Generate a Markdown memo.
- Generate a JSON report next to the Markdown memo unless disabled.
- Use built-in checks only.
- Use warning severity for statistical outliers unless configured otherwise.

### Config-Driven Mode

Used for repeatable workflows with explicit rules and output paths.

```bash
dq-agent run dq-config.yml
```

Example config:

```yaml
input:
  path: data/customers.csv
  format: csv

dataset:
  name: customers
  primary_key: customer_id

rules:
  required_columns:
    - customer_id
    - email
    - created_at

  non_null:
    - customer_id
    - email

  allowed_values:
    status:
      - active
      - paused
      - cancelled

  bounds:
    revenue:
      min: 0

  expressions:
    - name: valid_date_order
      expression: "end_date >= start_date"
      severity: error

output:
  markdown: reports/customers-readiness.md
  json: reports/customers-profile.json
```

## Architecture

The agent should be organized into five modules.

### 1. Connector Layer

Responsibility: load supported source files and return a normalized dataframe plus source metadata.

MVP connectors:

- CSV.
- XLSX, one selected sheet at a time.
- JSON and JSONL.

Connector output should include:

- Dataframe.
- Source path.
- Source format.
- Dataset name, if provided.
- Sheet name, if applicable.
- Load timestamp.
- Row count.
- Column names.

Connector errors should be explicit and user-readable:

- File not found.
- Unsupported format.
- Missing Excel sheet.
- Malformed JSON.
- Encoding or parsing failure.
- Empty file or empty sheet.

### 2. Profiler

Responsibility: calculate structured profile data. The profiler should not generate prose.

Required profile fields:

- Row count.
- Column count.
- Column names.
- Inferred data types.
- Null count and null percentage per column.
- Duplicate row count.
- Duplicate primary key count when a primary key is provided.
- Numeric min, max, mean, median, standard deviation, and selected percentiles.
- Numeric outlier candidates.
- Categorical cardinality and top values.
- Date min, max, and range when a date-like column is detected.
- String min length, max length, and sample values.
- Empty columns.
- Mixed-type columns where detectable.

Outlier detection should default to warning-level findings. Statistical outliers are not automatically errors because rare values may be valid.

### 3. Rule Engine

Responsibility: evaluate built-in checks and config-driven rules, returning structured findings.

MVP rule types:

- Required columns.
- Non-null columns.
- Allowed values.
- Numeric bounds.
- Expected schema, if provided.
- Lightweight row-level expressions.

Findings should include:

- Finding ID.
- Title.
- Severity: `info`, `warning`, or `error`.
- Affected columns.
- Failed row count, when applicable.
- Example failed values or rows, capped to a small number.
- Explanation.
- Suggested remediation.

Lightweight expressions should be evaluated with a constrained evaluator, not arbitrary Python execution. MVP expressions should support comparisons, boolean operators, column references, numeric literals, string literals, null checks, and basic date comparisons.

Python plugin checks should not be implemented in v1, but the rule engine should be designed so a later plugin check can return the same finding object shape.

### 4. Report Generator

Responsibility: generate Markdown and JSON outputs from the same profile and findings objects.

The Markdown memo should include:

```markdown
# Data Readiness Memo: <dataset_name>

## Verdict
<Ready | Ready with caveats | Needs review | Not ready>

## Executive Summary
<Short mixed-audience summary.>

## Key Findings
- <Highest severity findings first.>

## Recommended Fixes
- <Concrete remediation steps.>

## Dataset Profile
<Rows, columns, source, key stats.>

## Rule Results
<Rules evaluated and pass/fail status.>

## Technical Appendix
<Column-level profile and examples.>
```

The JSON report should include:

- Source metadata.
- Dataset metadata.
- Profile object.
- Findings list.
- Rule results.
- Readiness verdict.
- Generated timestamp.
- Tool version.

### 5. CLI Orchestrator

Responsibility: parse commands, read config, call the connector, profiler, rule engine, and report generator, then return an appropriate exit code.

Exit codes:

- `0`: run completed and no blocking issues were found.
- `1`: run completed with warnings or review-needed findings.
- `2`: run completed with error-severity findings that make the dataset not ready.
- `3`: execution failure, such as invalid config, unreadable file, or parsing failure.

## Readiness Verdict

The readiness verdict should be deterministic and explainable.

- `Ready`: no warning or error findings.
- `Ready with caveats`: warning findings only.
- `Needs review`: one or more findings marked with `review` impact. MVP should reserve this for built-in checks where the agent has evidence of risk but cannot determine failure, such as mixed-type columns, parse coercion, or outlier-heavy numeric columns without configured bounds.
- `Not ready`: one or more error findings.

MVP should keep verdict logic simple. Teams can tune severity through config rather than modifying scoring code.

## Data Flow

1. User runs `dq-agent profile <path>` or `dq-agent run <config>`.
2. CLI parses arguments and config.
3. Connector loads the source into a normalized dataframe and metadata object.
4. Profiler generates a structured profile.
5. Rule engine evaluates built-in checks and configured rules.
6. Verdict engine determines readiness.
7. Report generator writes Markdown and JSON outputs.
8. CLI prints a short terminal summary and exits with the correct code.

## Terminal Summary

The CLI should print a concise summary after each successful run:

```text
Dataset: customers
Rows: 42,318
Columns: 18
Verdict: Ready with caveats
Findings: 2 errors, 5 warnings, 3 info
Markdown: reports/customers-readiness.md
JSON: reports/customers-profile.json
```

For execution failures, the CLI should print the reason and exit with code `3`.

## Config Validation

The config file should be validated before loading data.

Validation should catch:

- Missing `input.path`.
- Unsupported `input.format`.
- Missing output paths when required.
- Invalid severity values.
- Invalid rule structures.
- Expression syntax that cannot be parsed.

Invalid config should produce a clear error message and exit with code `3`.

## Stress-Tested Assumptions

- Universal use across teams requires a shared engine plus team-specific rules. A single global ruleset cannot understand every business domain.
- Schema drift detection requires either historical profiles or an expected schema. MVP v1 should support expected schema checks but not historical drift.
- Statistical outliers are review signals, not automatic data failures.
- Questionable values require context. The agent can flag likely issues, but team-specific rules are needed for business judgment.
- Excel support should stay narrow in v1. One selected sheet per run avoids ambiguous workbook behavior.
- Database support should be deferred until the file-based engine is useful and stable.
- Arbitrary Python checks should be deferred until the rule engine, finding shape, and safety model are proven.

## Future Extension Path

### v2: Database Support

- Add Postgres connector first.
- Support table profiling and custom SQL query profiling.
- Require read-only credentials.
- Add query timeout and row limit controls.

### v3: Drift And Team Workflows

- Store historical profile artifacts.
- Compare current profile against prior baseline.
- Add schema and distribution drift detection.
- Support team-level rule packs.

### v4: Python Plugin Checks

- Allow custom Python checks through an explicit plugin interface.
- Require plugins to return the standard finding object.
- Add safety guidance for local execution and trusted code only.

## Implementation Defaults For Planning

- Use `pandas` as the dataframe engine in v1, behind a small connector/profiler interface so `polars` can be added later.
- Use `typer` for the CLI.
- Use `pydantic` for config and result models.
- Use `pyyaml` for YAML config parsing.
- Use `openpyxl` through `pandas` for XLSX support.
- Implement a constrained expression evaluator instead of using unrestricted Python execution.
- In quick profile mode, default outputs to a `dq-reports/` directory next to the input file.
- JSON reports should include failed value examples by default, capped to five examples per finding. Full failed rows should require an explicit opt-in flag to reduce privacy risk.
