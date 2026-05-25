from pathlib import Path

from dq_agent.config import load_config


def test_load_config_parses_rules_and_outputs(tmp_path: Path):
    data_file = tmp_path / "customers.csv"
    data_file.write_text("customer_id,email,status\n1,a@example.com,active\n", encoding="utf-8")
    config_file = tmp_path / "dq.yml"
    config_file.write_text(
        f"""
input:
  path: {data_file}
  format: csv
dataset:
  name: customers
  primary_key: customer_id
rules:
  required_columns:
    - customer_id
    - email
  non_null:
    - customer_id
  allowed_values:
    status:
      - active
      - paused
  bounds:
    revenue:
      min: 0
  expressions:
    - name: valid_status
      expression: "status == 'active'"
      severity: warning
output:
  markdown: {tmp_path / "memo.md"}
  json: {tmp_path / "report.json"}
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.input.path == data_file
    assert config.dataset.name == "customers"
    assert config.rules.required_columns == ["customer_id", "email"]
    assert config.rules.allowed_values["status"] == ["active", "paused"]
    assert config.output.markdown.name == "memo.md"
