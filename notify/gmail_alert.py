"""
APEX 2.0 — Gmail Alert Sender

Uses Google OAuth2 (NOT App Password / NOT your real password).
Your password is never stored or transmitted.

HOW IT WORKS
  1. First run opens a browser window — you approve access once.
  2. A token is saved locally in data/gmail_token.json (gitignored).
  3. All future runs use that token silently. Token auto-refreshes.
  4. Revoke access any time: myaccount.google.com → Security → Third-party apps

SETUP (one-time, ~5 minutes)
  See docs/GMAIL_SETUP.md for the full walkthrough.
  Short version:
    1. Go to console.cloud.google.com → APIs & Services → Credentials
    2. Create OAuth 2.0 Client ID (Desktop app)
    3. Download JSON → save as data/gmail_credentials.json  (gitignored)
    4. Run:  python -m notify.gmail_alert --setup
    5. Browser opens → approve → done.

FALLBACK
  If data/gmail_credentials.json is absent, alerts print to console only.
  The dashboard always shows alerts regardless of email config.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from notify.opportunity_scanner import Opportunity

RECIPIENT = "nitish.bidwe@gmail.com"
SENDER = "nitish.bidwe@gmail.com"

CREDENTIALS_FILE = Path("data/gmail_credentials.json")
TOKEN_FILE = Path("data/gmail_token.json")

# OAuth2 scope — send-only, cannot read your email
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _get_gmail_service():
    """
    Return an authenticated Gmail API service object.
    Raises ImportError if google-auth libraries are not installed.
    Raises FileNotFoundError if credentials file is absent.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ImportError(
            "Gmail OAuth libraries missing. Run: "
            "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        ) from exc

    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"{CREDENTIALS_FILE} not found. "
            "Run `python -m notify.gmail_alert --setup` to configure Gmail OAuth. "
            "See docs/GMAIL_SETUP.md for instructions."
        )

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _build_raw_message(subject: str, body: str, severity: str, ticker: str | None) -> dict:
    """Encode a plain-text email as base64url for the Gmail API."""
    import base64
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER
    msg["To"] = RECIPIENT
    msg["X-APEX-Severity"] = severity
    if ticker:
        msg["X-APEX-Ticker"] = ticker
    msg.attach(MIMEText(body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}


def send_alert(opportunity: Opportunity, dry_run: bool = False) -> bool:
    """
    Send a single alert email via Gmail OAuth2.
    Falls back to console print if credentials are not configured or dry_run=True.
    Returns True on success (including dry run), False on API failure.
    """
    if dry_run:
        _print_dry_run(opportunity)
        return True

    try:
        service = _get_gmail_service()
        message = _build_raw_message(
            subject=opportunity.subject,
            body=opportunity.body,
            severity=opportunity.severity,
            ticker=opportunity.ticker,
        )
        service.users().messages().send(userId="me", body=message).execute()
        print(f"[APEX] Alert sent: {opportunity.name!r} ({opportunity.severity})")
        return True

    except FileNotFoundError as exc:
        # Credentials not set up yet — fall back to console
        print(f"[APEX] Gmail not configured — printing alert instead.")
        print(f"       ({exc})")
        _print_dry_run(opportunity)
        return True  # not a failure; alert was surfaced

    except Exception as exc:
        print(f"[APEX] Gmail send failed for {opportunity.name!r}: {exc}")
        _print_dry_run(opportunity)
        return False


def send_all_alerts(
    opportunities: list[Opportunity],
    dry_run: bool = False,
) -> int:
    """Send all triggered opportunities. Returns count successfully sent."""
    sent = 0
    for opp in opportunities:
        if send_alert(opp, dry_run=dry_run):
            sent += 1
    return sent


def _print_dry_run(opportunity: Opportunity) -> None:
    print(f"[APEX ALERT] {opportunity.severity} — {opportunity.subject}")
    print("-" * 60)
    print(opportunity.body)
    print("-" * 60)


# ── Setup wizard ──────────────────────────────────────────────────────────────

def run_setup() -> None:
    """Interactive first-time setup. Opens browser for OAuth consent."""
    print("APEX Gmail OAuth2 Setup")
    print("=" * 40)

    if not CREDENTIALS_FILE.exists():
        print(f"\n❌  {CREDENTIALS_FILE} not found.")
        print("\nSteps to get it:")
        print("  1. Go to: https://console.cloud.google.com/apis/credentials")
        print("  2. Create → OAuth 2.0 Client ID → Desktop app")
        print(f"  3. Download JSON → save as  {CREDENTIALS_FILE}")
        print("  4. Re-run this script.\n")
        return

    print(f"\n✅  Found {CREDENTIALS_FILE}")
    print("Opening browser for Google consent screen …\n")
    try:
        _get_gmail_service()
        print(f"\n✅  Setup complete. Token saved to {TOKEN_FILE}")
        print("APEX will send alerts to nitish.bidwe@gmail.com silently from now on.")
        print("Revoke anytime: myaccount.google.com → Security → Third-party apps\n")
    except Exception as exc:
        print(f"\n❌  Setup failed: {exc}\n")


if __name__ == "__main__":
    import sys
    if "--setup" in sys.argv:
        run_setup()
    else:
        print("Usage: python -m notify.gmail_alert --setup")
