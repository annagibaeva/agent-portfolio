"""Google OAuth (installed-app flow) for Calendar + Gmail."""
from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

PROJECT_ROOT = Path(__file__).parent
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"
TOKEN_PATH = Path(os.path.expanduser("~/.config/meeting-prep-agent/token.json"))


def get_credentials(interactive: bool = False) -> Credentials:
    creds: Credentials | None = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif interactive:
        if not CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"Place your Google OAuth client at {CREDENTIALS_PATH}. "
                "See README for setup."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        creds = flow.run_local_server(port=0)
    else:
        raise RuntimeError(
            "No valid Google credentials. Run: python main.py --setup-auth"
        )

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    return creds


def setup_auth() -> None:
    creds = get_credentials(interactive=True)
    print(f"Auth ok. Token cached at {TOKEN_PATH}")
