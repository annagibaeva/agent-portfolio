from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from dq_agent.config import ConfigError, load_config
from dq_agent.connectors import ConnectorError, load_source
from dq_agent.profiler import profile_dataframe
from dq_agent.reports import build_report, write_json_report, write_markdown_memo
from dq_agent.rules import evaluate_rules
from dq_agent.scaffold import default_config_path, write_draft_config
from dq_agent.verdict import exit_code_for_verdict


app = typer.Typer(help="Profile datasets and generate data-readiness reports.")


def _default_outputs(source: Path) -> tuple[Path, Path]:
    report_dir = source.parent / "dq-reports"
    stem = source.stem
    return report_dir / f"{stem}-readiness.md", report_dir / f"{stem}-profile.json"


def _print_summary(report, markdown_path: Path, json_path: Path) -> None:
    errors = sum(1 for finding in report.findings if finding.severity == "error")
    warnings = sum(1 for finding in report.findings if finding.severity == "warning")
    infos = sum(1 for finding in report.findings if finding.severity == "info")
    typer.echo(f"Dataset: {report.dataset_name}")
    typer.echo(f"Rows: {report.profile.row_count:,}")
    typer.echo(f"Columns: {report.profile.column_count:,}")
    typer.echo(f"Verdict: {report.verdict}")
    typer.echo(f"Findings: {errors} errors, {warnings} warnings, {infos} info")
    typer.echo(f"Markdown: {markdown_path}")
    typer.echo(f"JSON: {json_path}")


@app.command()
def profile(
    path: Path,
    sheet: Optional[str] = typer.Option(None, "--sheet", help="Excel sheet name to load."),
    source_format: Optional[str] = typer.Option(None, "--format", help="Input format override."),
    out: Optional[Path] = typer.Option(None, "--out", help="Markdown output path."),
    json_out: Optional[Path] = typer.Option(None, "--json-out", help="JSON output path."),
) -> None:
    try:
        markdown_path, json_path = _default_outputs(path)
        markdown_path = out or markdown_path
        json_path = json_out or json_path
        loaded = load_source(path, source_format=source_format, sheet_name=sheet)
        data_profile, profile_findings = profile_dataframe(loaded.dataframe)
        report = build_report(loaded.metadata, data_profile, profile_findings)
        write_markdown_memo(report, markdown_path)
        write_json_report(report, json_path)
        _print_summary(report, markdown_path, json_path)
        raise typer.Exit(exit_code_for_verdict(report.verdict))
    except ConnectorError as exc:
        typer.echo(f"Execution failure: {exc}", err=True)
        raise typer.Exit(3) from exc


@app.command("init-config")
def init_config(
    path: Path,
    sheet: Optional[str] = typer.Option(None, "--sheet", help="Excel sheet name to load."),
    source_format: Optional[str] = typer.Option(None, "--format", help="Input format override."),
    dataset_name: Optional[str] = typer.Option(None, "--dataset-name", help="Reusable dataset contract name."),
    primary_key: Optional[str] = typer.Option(None, "--primary-key", help="Primary key column for uniqueness and non-null checks."),
    out: Optional[Path] = typer.Option(None, "--out", help="Draft config output path."),
) -> None:
    try:
        loaded = load_source(path, source_format=source_format, sheet_name=sheet, dataset_name=dataset_name)
        config_path = out or default_config_path(path)
        write_draft_config(
            loaded.dataframe,
            loaded.metadata,
            config_path,
            dataset_name=dataset_name,
            primary_key=primary_key,
        )
        typer.echo(f"Draft config: {config_path}")
        typer.echo("Review and edit the rules, then run:")
        typer.echo(f"dq-agent run {config_path}")
        raise typer.Exit(0)
    except ConnectorError as exc:
        typer.echo(f"Execution failure: {exc}", err=True)
        raise typer.Exit(3) from exc


@app.command()
def run(config: Path) -> None:
    try:
        agent_config = load_config(config)
        loaded = load_source(
            agent_config.input.path,
            source_format=agent_config.input.format,
            sheet_name=agent_config.input.sheet,
            dataset_name=agent_config.dataset.name,
        )
        data_profile, profile_findings = profile_dataframe(
            loaded.dataframe,
            primary_key=agent_config.dataset.primary_key,
        )
        rule_findings = evaluate_rules(loaded.dataframe, agent_config.rules)
        report = build_report(
            loaded.metadata,
            data_profile,
            profile_findings + rule_findings,
            dataset_name=agent_config.dataset.name,
        )
        write_markdown_memo(report, agent_config.output.markdown)
        write_json_report(report, agent_config.output.json)
        _print_summary(report, agent_config.output.markdown, agent_config.output.json)
        raise typer.Exit(exit_code_for_verdict(report.verdict))
    except (ConfigError, ConnectorError) as exc:
        typer.echo(f"Execution failure: {exc}", err=True)
        raise typer.Exit(3) from exc
