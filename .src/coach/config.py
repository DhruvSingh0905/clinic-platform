"""Configuration loader for Coach Platform."""
import os
from dotenv import load_dotenv

load_dotenv()

# Server
COACH_DB_PATH = os.getenv("COACH_DB_PATH", "coach_platform.db")
SEED_MOCK = os.getenv("COACH_SEED_MOCK", "true").lower() == "true"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))

# Anthropic / LLM
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CDE_MODEL = os.getenv("CDE_MODEL", "claude-sonnet-4-20250514")

# OAuth integrations
WHOOP_CLIENT_ID = os.getenv("WHOOP_CLIENT_ID", "")
WHOOP_CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET", "")
WITHINGS_CLIENT_ID = os.getenv("WITHINGS_CLIENT_ID", "")
WITHINGS_CLIENT_SECRET = os.getenv("WITHINGS_CLIENT_SECRET", "")
DEXCOM_CLIENT_ID = os.getenv("DEXCOM_CLIENT_ID", "")
DEXCOM_CLIENT_SECRET = os.getenv("DEXCOM_CLIENT_SECRET", "")
DEXCOM_SANDBOX = os.getenv("DEXCOM_SANDBOX", "true").lower() == "true"
OAUTH_CALLBACK_BASE = os.getenv("OAUTH_CALLBACK_BASE", "http://localhost:8001")

# File storage
UPLOADS_DIR = os.getenv("UPLOADS_DIR", "uploads")

# Google Calendar
GOOGLE_CALENDAR_CREDENTIALS_PATH = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH", "")
GOOGLE_CALENDAR_TOKEN_PATH = os.getenv("GOOGLE_CALENDAR_TOKEN_PATH", "google_token.json")
