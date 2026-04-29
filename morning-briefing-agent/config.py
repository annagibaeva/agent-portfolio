import os

PLAN_FILE = r"C:\Users\annag\OneDrive\Documents\Claude-Cowork\PROJECTS\agent-pm-learning-plan.md"
RESOURCES_FILE = r"C:\Users\annag\Downloads\agent-pm-resources.md"
_BASE = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(_BASE, "progress.json")
LOG_FILE = os.path.join(_BASE, "logs", "briefing.log")
TOKEN_FILE = os.path.join(_BASE, "token.json")
CREDENTIALS_FILE = os.path.join(_BASE, "credentials.json")

EMAIL_TO = "annagibaeva05@gmail.com"
MODEL = "claude-sonnet-4-6"
ANTHROPIC_BLOG_URL = "https://www.anthropic.com/engineering"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
