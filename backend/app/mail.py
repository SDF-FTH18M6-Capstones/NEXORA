"""Outgoing email. Only the verification link is sent today.

MAIL_BACKEND=log writes the message to the application log (local development
only; production refuses it). MAIL_BACKEND=smtp sends through MAIL_SERVER.
"""

import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

log = logging.getLogger(__name__)


def send_verification_email(to: str, token: str) -> None:
    """Email the link that proves `to` belongs to the person who registered it."""
    config = current_app.config
    link = f"{config['FRONTEND_URL'].rstrip('/')}/verify-email?token={token}"
    body = (
        "Confirm your email address for NEXORA by opening this link within "
        f"24 hours:\n\n{link}\n\nIf you did not create an account, ignore this email."
    )
    backend = config["MAIL_BACKEND"]
    if backend == "log":
        log.info("Verification email to %s: %s", to, link)
        return
    message = EmailMessage()
    message["Subject"] = "Confirm your NEXORA email"
    message["From"] = config["MAIL_FROM"]
    message["To"] = to
    message.set_content(body)
    with smtplib.SMTP(config["MAIL_SERVER"], config["MAIL_PORT"], timeout=10) as smtp:
        smtp.starttls()
        if config["MAIL_USERNAME"]:
            smtp.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
        smtp.send_message(message)


def send_safely(to: str, token: str) -> None:
    """A mail outage must never fail the request that asked for the email."""
    try:
        send_verification_email(to, token)
    except Exception:
        log.exception("Could not send the verification email")
