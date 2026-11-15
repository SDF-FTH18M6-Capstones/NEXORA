"""Outgoing email: the verification and password-reset links.

MAIL_BACKEND=log writes the message to the application log (local development
only; production refuses it). MAIL_BACKEND=smtp sends through MAIL_SERVER.
"""

import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

log = logging.getLogger(__name__)


MESSAGES = {
    "verify": (
        "Confirm your NEXORA email",
        "verify-email",
        "Confirm your email address for NEXORA by opening this link within 24 hours:",
    ),
    "reset": (
        "Reset your NEXORA password",
        "reset-password",
        "Reset your NEXORA password by opening this link within 1 hour:",
    ),
}


def send_link_email(to: str, token: str, purpose: str = "verify") -> None:
    """Email a single-use link: verify an address, or reset a password."""
    config = current_app.config
    subject, page, intro = MESSAGES[purpose]
    link = f"{config['FRONTEND_URL'].rstrip('/')}/{page}?token={token}"
    body = f"{intro}\n\n{link}\n\nIf you did not ask for this, ignore this email."
    backend = config["MAIL_BACKEND"]
    if backend == "log":
        log.info("%s email to %s: %s", purpose, to, link)
        return
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["MAIL_FROM"]
    message["To"] = to
    message.set_content(body)
    with smtplib.SMTP(config["MAIL_SERVER"], config["MAIL_PORT"], timeout=10) as smtp:
        smtp.starttls()
        if config["MAIL_USERNAME"]:
            smtp.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
        smtp.send_message(message)


def send_safely(to: str, token: str, purpose: str = "verify") -> None:
    """A mail outage must never fail the request that asked for the email."""
    try:
        send_link_email(to, token, purpose)
    except Exception:
        log.exception("Could not send the %s email", purpose)
