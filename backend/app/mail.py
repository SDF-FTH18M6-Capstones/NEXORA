"""Outgoing email: the verification and password-reset links.

MAIL_BACKEND=log writes the message to the application log (local development
only; production refuses it). MAIL_BACKEND=smtp sends through MAIL_SERVER.
"""

import logging
import smtplib
import threading
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


def send_text_email(to: str, subject: str, body: str) -> None:
    """Send a plain message: logged on the log backend, delivered on smtp."""
    config = current_app.config
    if config["MAIL_BACKEND"] == "log":
        log.info("email to %s (%s):\n%s", to, subject, body)
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


def _send_logged(to: str, token: str, purpose: str) -> None:
    try:
        send_link_email(to, token, purpose)
    except Exception:
        log.exception("Could not send the %s email", purpose)


def send_safely(to: str, token: str, purpose: str = "verify") -> None:
    """A mail outage must never fail the request that asked for the email.

    SMTP goes out on a background thread: a request for a known address would
    otherwise take visibly longer than one for an unknown address.
    """
    if current_app.config["MAIL_BACKEND"] != "smtp":
        _send_logged(to, token, purpose)
        return
    app = current_app._get_current_object()

    def work():
        with app.app_context():
            _send_logged(to, token, purpose)

    threading.Thread(target=work, daemon=True).start()
