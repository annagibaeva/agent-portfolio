from __future__ import annotations
import smtplib
from email.message import EmailMessage


def send_digest(*, subject: str, html: str, recipient: str,
                smtp_host: str, smtp_port: int, smtp_user: str,
                smtp_password: str, dry_run: bool = True,
                smtp_cls=smtplib.SMTP) -> bool:
    """Send the digest email. Returns True if sent, False if dry-run."""
    if dry_run:
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg.set_content("HTML digest — view in an HTML-capable client.")
    msg.add_alternative(html, subtype="html")
    with smtp_cls(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)
    return True
