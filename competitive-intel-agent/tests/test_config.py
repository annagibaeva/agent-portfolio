from __future__ import annotations
import pytest
from src.config import Config, load_config


def test_load_config_reads_env(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY",
              "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "DIGEST_RECIPIENT"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setenv("SMTP_PORT", "587")
    cfg = load_config()
    assert isinstance(cfg, Config)
    assert cfg.smtp_port == 587


def test_load_config_missing_var_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        load_config()
