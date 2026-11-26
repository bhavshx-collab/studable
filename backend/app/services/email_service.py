"""
Studable API — Transactional Email Service.

Provides asynchronous email sending via SMTP with graceful local fallback.
Used for:
- Email address verification
- Password reset links
- Moderation / account notifications
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_smtp_sync(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Synchronous SMTP delivery helper executed in worker thread."""
    if not settings.SMTP_HOST:
        logger.info(
            "[DEV EMAIL LOG] SMTP not configured. Simulating delivery to: %s | Subject: %s",
            to_email,
            subject,
        )
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAILS_FROM_EMAIL, [to_email], msg.as_string())
        logger.info("Email successfully sent to %s via SMTP", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s via SMTP: %s", to_email, exc)
        return False


async def send_email(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Non-blocking email dispatch."""
    return await asyncio.to_thread(_send_smtp_sync, to_email, subject, html_body, text_body)


async def send_verification_email(to_email: str, token: str) -> bool:
    """Send an account email verification message."""
    verify_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
    subject = "Verify your Studable account"
    text_body = (
        f"Welcome to Studable!\n\n"
        f"Please verify your email address by opening the following link:\n"
        f"{verify_url}\n\n"
        f"This link will expire in 24 hours.\n"
        f"If you did not create an account, you can safely ignore this email."
    )
    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; background: #0B0D14; color: #F5F6FA; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
      <h2 style="color: #36B9E9; margin-top: 0;">Welcome to Studable</h2>
      <p style="color: #9299AC; line-height: 1.6;">Thank you for registering. Confirm your email to start discovering and connecting with peers:</p>
      <div style="margin: 32px 0;">
        <a href="{verify_url}" style="background: #36B9E9; color: #0B0D14; font-weight: 600; text-decoration: none; padding: 12px 24px; border-radius: 8px; display: inline-block;">Verify Email Address</a>
      </div>
      <p style="color: #636A80; font-size: 12px;">Link: <a href="{verify_url}" style="color: #36B9E9;">{verify_url}</a></p>
      <p style="color: #636A80; font-size: 12px; margin-top: 24px;">If you did not request this, please disregard this email.</p>
    </div>
    """
    return await send_email(to_email, subject, html_body, text_body)


async def send_password_reset_email(to_email: str, token: str) -> bool:
    """Send a password reset instructions message."""
    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
    subject = "Reset your Studable password"
    text_body = (
        f"Hello,\n\n"
        f"A password reset was requested for your Studable account.\n"
        f"Use the link below to set a new password:\n"
        f"{reset_url}\n\n"
        f"This link expires in 15 minutes.\n"
        f"If you did not request this, your account is secure and no action is required."
    )
    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; background: #0B0D14; color: #F5F6FA; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
      <h2 style="color: #36B9E9; margin-top: 0;">Password Reset Request</h2>
      <p style="color: #9299AC; line-height: 1.6;">We received a request to reset your password. Click below to proceed:</p>
      <div style="margin: 32px 0;">
        <a href="{reset_url}" style="background: #36B9E9; color: #0B0D14; font-weight: 600; text-decoration: none; padding: 12px 24px; border-radius: 8px; display: inline-block;">Reset Password</a>
      </div>
      <p style="color: #636A80; font-size: 12px;">Link: <a href="{reset_url}" style="color: #36B9E9;">{reset_url}</a></p>
      <p style="color: #636A80; font-size: 12px; margin-top: 24px;">This link is valid for 15 minutes. If you did not make this request, you can safely ignore this email.</p>
    </div>
    """
    return await send_email(to_email, subject, html_body, text_body)
