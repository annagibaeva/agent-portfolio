"""Standalone SMTP smoke test. Run: python smtp_test.py"""
import os
import smtplib
from email.message import EmailMessage

REQUIRED = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "DIGEST_RECIPIENT"]
missing = [k for k in REQUIRED if not os.environ.get(k)]
if missing:
    raise SystemExit(f"Missing env vars: {missing}")

msg = EmailMessage()
msg["Subject"] = "Competitive Intel Agent — SMTP smoke test"
msg["From"] = os.environ["SMTP_USER"]
msg["To"] = os.environ["DIGEST_RECIPIENT"]
msg.set_content("If you can read this, SMTP is wired up correctly.")

port = int(os.environ.get("SMTP_PORT", "587"))
with smtplib.SMTP(os.environ["SMTP_HOST"], port) as s:
    s.starttls()
    s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
    s.send_message(msg)
print("sent")
