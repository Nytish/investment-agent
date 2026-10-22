"""
APEX 2.0 — Gmail Alert Sender

Two modes:
  1. SMTP with Gmail App Password (standalone, Mac Mini M4)
  2. Dry run (print only) when GMAIL_APP_PASSWORD not set

Setup: Google Account → Security → 2-Step Verification → App Passwords
       Set env var: export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
"""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from notify.opportunity_scanner import Opportunity

RECIPIENT = "nitish.bidwe@gmail.com"
SENDER = "nitish.bidwe@gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def send_alert(opportunity: Opportunity, dry_run: bool = False) -> bool:
    """
    Send a single alert email.
    Returns True on success (including dry run), False on SMTP failure.
    """
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    if dry_run or not app_password:
        print(f"[DRY RUN] Subject: {opportunity.subject}")
        print("-" * 60)
        print(opportunity.body)
        print("-" * 60)
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = opportunity.subject
        msg["From"] = SENDER
        msg["To"] = RECIPIENT
        msg["X-APEX-Severity"] = opportunity.severity
        if opportunity.ticker:
            msg["X-APEX-Ticker"] = opportunity.ticker

        msg.attach(MIMEText(opportunity.body, "plain", "utf-8"))

        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(SENDER, app_password)
            smtp.send_message(msg)
        return True
    except smtplib.SMTPException as exc:
        print(f"[APEX] SMTP error sending {opportunity.name!r}: {exc}")
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
