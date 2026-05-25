from pathlib import Path

from typer.testing import CliRunner

from dq_agent.cli import app


def test_profile_command_writes_markdown_and_json(tmp_path: Path):
    source = tmp_path / "customers.csv"
    source.write_text("customer_id,status\n1,active\n2,paused\n", encoding="utf-8")
    markdown = tmp_path / "memo.md"
    json_report = tmp_path / "report.json"

    result = CliRunner().invoke(
        app,
        ["profile", str(source), "--out", str(markdown), "--json-out", str(json_report)],
    )

    assert result.exit_code == 0
    assert "Verdict: Ready" in result.stdout
    assert markdown.exists()
    assert json_report.exists()


def test_run_command_uses_config_and_returns_error_exit_for_blocking_findings(tmp_path: Path):
    source = tmp_path / "customers.csv"
    source.write_text("customer_id,status\n,unknown\n", encoding="utf-8")
    markdown = tmp_path / "memo.md"
    json_report = tmp_path / "report.json"
    config = tmp_path / "dq.yml"
    config.write_text(
        f"""
input:
  path: {source}
  format: csv
dataset:
  name: customers
  primary_key: customer_id
rules:
  non_null:
    - customer_id
  allowed_values:
    status:
      - active
      - paused
output:
  markdown: {markdown}
  json: {json_report}
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["run", str(config)])

    assert result.exit_code == 2
    assert "Verdict: Not ready" in result.stdout
    assert markdown.exists()
    assert json_report.exists()
