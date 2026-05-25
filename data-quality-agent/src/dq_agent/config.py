from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


Severity = Literal["info", "warning", "error"]


class InputConfig(BaseModel):
    path: Path
    format: str | None = None
    sheet: str | None = None


class DatasetConfig(BaseModel):
    name: str | None = None
    primary_key: str | None = None


class BoundsRule(BaseModel):
    min: float | None = None
    max: float | None = None
    severity: Severity = "error"


class ExpressionRule(BaseModel):
    name: str
    expression: str
    severity: Severity = "error"


class RulesConfig(BaseModel):
    required_columns: list[str] = Field(default_factory=list)
    non_null: list[str] = Field(default_factory=list)
    allowed_values: dict[str, list[str | int | float | bool]] = Field(default_factory=dict)
    bounds: dict[str, BoundsRule] = Field(default_factory=dict)
    expected_schema: dict[str, str] = Field(default_factory=dict)
    expressions: list[ExpressionRule] = Field(default_factory=list)


class OutputConfig(BaseModel):
    markdown: Path
    json_path: Path = Field(alias="json")

    @property
    def json(self) -> Path:
        return self.json_path


class AgentConfig(BaseModel):
    input: InputConfig
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    rules: RulesConfig = Field(default_factory=RulesConfig)
    output: OutputConfig

    @field_validator("input")
    @classmethod
    def validate_supported_format(cls, value: InputConfig) -> InputConfig:
        source_format = (value.format or value.path.suffix.lstrip(".")).lower()
        if source_format not in {"csv", "xlsx", "json", "jsonl"}:
            raise ValueError(f"Unsupported input format: {source_format}")
        return value


class ConfigError(ValueError):
    pass


def load_config(path: str | Path) -> AgentConfig:
    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML config: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Config must be a YAML mapping.")

    try:
        return AgentConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigError(f"Invalid config: {exc}") from exc
