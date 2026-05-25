from __future__ import annotations
import os
from dataclasses import dataclass

_REQUIRED = (
    "ANTHROPIC_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY",
    "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "DIGEST_RECIPIENT",
)


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str
    supabase_url: str
    supabase_service_key: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    digest_recipient: str


def load_config() -> Config:
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
    return Config(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        supabase_url=os.environ["SUPABASE_URL"],
        supabase_service_key=os.environ["SUPABASE_SERVICE_KEY"],
        smtp_host=os.environ["SMTP_HOST"],
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_user=os.environ["SMTP_USER"],
        smtp_password=os.environ["SMTP_PASSWORD"],
        digest_recipient=os.environ["DIGEST_RECIPIENT"],
    )
