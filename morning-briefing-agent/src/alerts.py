from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage


def send_smtp_alert(subject: str, body: str) -> bool:
    """Send a plaintext alert via SMTP using env vars. Returns True on success.

    Required env vars: ALERT_SMTP_HOST, ALERT_SMTP_USER, ALERT_SMTP_PASS, ALERT_TO.
    Optional: ALERT_SMTP_PORT (default 587).
    """
    host = os.environ.get("ALERT_SMTP_HOST")
    user = os.environ.get("ALERT_SMTP_USER")
    password = os.environ.get("ALERT_SMTP_PASS")
    to = os.environ.get("ALERT_TO")
    port = int(os.environ.get("ALERT_SMTP_PORT", "587"))

    if not all([host, user, password, to]):
        logging.warning("SMTP alert skipped — ALERT_SMTP_* env vars not configured")
        return False

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.starttls()
            s.login(user, password)
            s.send_message(msg)
        return True
    except Exception:
        logging.exception("SMTP alert send failed")
        return False
