import base64
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def build_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds)


def _yesterday_query() -> str:
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y/%m/%d")
    return f"after:{yesterday}"


def _fetch_messages(service, query: str) -> list[dict]:
    result = service.users().messages().list(userId="me", q=query, maxResults=10).execute()
    messages = []
    for item in result.get("messages", []):
        msg = service.users().messages().get(
            userId="me", id=item["id"], format="metadata",
            metadataHeaders=["Subject", "From"],
        ).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        messages.append({
            "subject": headers.get("Subject", "(No subject)"),
            "from": headers.get("From", ""),
            "snippet": msg.get("snippet", ""),
        })
    return messages


def search_meeting_threads(creds: Credentials | None = None) -> list[dict] | None:
    try:
        service = build_service(creds)
        query = f"subject:(meeting OR call OR webinar OR invite OR agenda) {_yesterday_query()} category:primary"
        return _fetch_messages(service, query)
    except Exception:
        return None


def search_substacks(creds: Credentials | None = None) -> list[dict] | None:
    try:
        service = build_service(creds)
        query = f"from:(@substack.com OR @substackmail.com) {_yesterday_query()}"
        return _fetch_messages(service, query)
    except Exception:
        return None


def send_email(subject: str, html_body: str, to: str, creds: Credentials | None = None) -> bool:
    try:
        service = build_service(creds)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["To"] = to
        msg["From"] = "me"
        msg.attach(MIMEText(html_body, "html"))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except Exception:
        return False
