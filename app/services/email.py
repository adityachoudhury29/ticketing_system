# app/services/email.py
import smtplib
import asyncio
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List

from ..core.config import settings
from ..models.models import User, Event, Booking

logger = logging.getLogger(__name__)


class EmailService:
    """Email notification service using SMTP (configurable via settings)"""

    def __init__(self):
        # Read configuration from settings (provide sensible defaults)
        self.smtp_server = getattr(settings, "smtp_server", "localhost")
        self.smtp_port = int(getattr(settings, "smtp_port", 587))
        self.username = getattr(settings, "smtp_username", None)
        self.password = getattr(settings, "smtp_password", None)
        self.from_email = getattr(settings, "smtp_from", "noreply@evently.local")
        self.use_tls = bool(getattr(settings, "smtp_use_tls", True))
        # If smtp_enabled is False, sending is simulated (useful for dev)
        self.enabled = bool(getattr(settings, "smtp_enabled", True))

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Send email asynchronously (runs the blocking SMTP work in a thread)."""
        if not self.enabled:
            logger.info("Email disabled - simulation mode. Would send to %s: %s", to_email, subject)
            return True

        loop = asyncio.get_event_loop()
        try:
            # run synchronous sending in a thread to avoid blocking the event loop
            await loop.run_in_executor(None, self._send_email_sync, to_email, subject, body, html_body)
            logger.info("Email sent to %s: %s", to_email, subject)
            return True
        except Exception as exc:
            logger.exception("Failed to send email to %s: %s", to_email, exc)
            return False

    def _send_email_sync(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None):
        """Synchronous SMTP sending using smtplib."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email

        # Plain text part
        text_part = MIMEText(body, "plain", "utf-8")
        msg.attach(text_part)

        # HTML part
        if html_body:
            html_part = MIMEText(html_body, "html", "utf-8")
            msg.attach(html_part)

        # Connect & send
        smtp = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=20)
        try:
            if self.use_tls:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(msg)
        finally:
            smtp.quit()

    # --- High-level templates ---

    async def send_booking_confirmation(self, user: User, booking: Booking, event: Event) -> bool:
        subject = f"Booking Confirmation — {event.name}"
        body = (
            f"Dear {getattr(user, 'name', 'Customer')},\n\n"
            f"Your booking has been confirmed!\n\n"
            f"Event: {event.name}\n"
            f"Venue: {event.venue}\n"
            f"Date: {event.start_time.strftime('%B %d, %Y at %I:%M %p')}\n"
            f"Booking ID: {booking.id}\n"
            f"Number of Tickets: {len(getattr(booking, 'tickets', []))}\n\n"
            f"Seats: {self._format_seats(booking.tickets)}\n\n"
            "Please arrive at least 30 minutes before the event.\n\n"
            "Best regards,\nEvently Team"
        )
        html = (
            f"<p>Dear {getattr(user, 'name', 'Customer')},</p>"
            f"<p>Your booking for <strong>{event.name}</strong> is confirmed.</p>"
            f"<p><strong>Date:</strong> {event.start_time.strftime('%B %d, %Y at %I:%M %p')}</p>"
            f"<p><strong>Booking ID:</strong> {booking.id}</p>"
            f"<p><strong>Seats:</strong> {self._format_seats_html(booking.tickets)}</p>"
            "<p>Please arrive 30 minutes early.</p>"
            "<p>Best regards,<br/>Evently Team</p>"
        )
        return await self.send_email(user.email, subject, body, html)

    async def send_waitlist_notification(self, user: User, event: Event) -> bool:
        subject = f"Seats available — {event.name}"
        body = (
            f"Hi {getattr(user, 'name', 'there')},\n\n"
            f"Seats are available for the event you were waitlisted for:\n\n"
            f"Event: {event.name}\n"
            f"Venue: {event.venue}\n"
            f"Date: {event.start_time.strftime('%B %d, %Y at %I:%M %p')}\n\n"
            "Visit the site and complete your booking before seats run out!\n\n"
            "Best,\nEvently Team"
        )
        html = (
            f"<p>Hi {getattr(user, 'name', 'there')},</p>"
            f"<p>Good news — seats are available for <strong>{event.name}</strong>!</p>"
            f"<p><strong>Date:</strong> {event.start_time.strftime('%B %d, %Y at %I:%M %p')}</p>"
            "<p><a href=\"#\">Complete your booking</a> before seats are gone.</p>"
            "<p>Best,<br/>Evently Team</p>"
        )
        return await self.send_email(user.email, subject, body, html)

    async def send_cancellation_notice(self, user: User, booking: Booking, event: Event) -> bool:
        subject = f"Booking cancelled — {event.name}"
        body = (
            f"Hello {getattr(user, 'name', 'Customer')},\n\n"
            f"Your booking (ID: {booking.id}) for {event.name} has been cancelled.\n\n"
            "If this was not you, contact support immediately.\n\n"
            "Regards,\nEvently Team"
        )
        return await self.send_email(user.email, subject, body)

    # helper formatters
    def _format_seats(self, tickets) -> str:
        if not tickets:
            return "No seats assigned"
        seats = []
        for t in tickets:
            seat = getattr(t, "seat", None)
            if seat and getattr(seat, "seat_identifier", None):
                seats.append(seat.seat_identifier)
        return ", ".join(seats) if seats else "Seat information not available"

    def _format_seats_html(self, tickets) -> str:
        if not tickets:
            return "<em>No seats assigned</em>"
        chips = []
        for t in tickets:
            seat = getattr(t, "seat", None)
            if seat and getattr(seat, "seat_identifier", None):
                chips.append(f"<span style='padding:3px 6px;border-radius:3px;border:1px solid #ddd;margin-right:4px'>{seat.seat_identifier}</span>")
        return " ".join(chips) if chips else "<em>Seat information not available</em>"


# single shared instance
email_service = EmailService()


class NotificationService:
    """Facade used by other parts of the app to send notifications."""

    @staticmethod
    async def send_waitlist_notification(user: User, event: Event):
        try:
            ok = await email_service.send_waitlist_notification(user, event)
            if ok:
                logger.info("Waitlist notification sent to %s", user.email)
                return True
            else:
                logger.warning("Failed to send waitlist notification to %s", user.email)
                return False
        except Exception:
            logger.exception("Error sending waitlist notification to %s", getattr(user, "email", None))
            return False

    @staticmethod
    async def send_booking_confirmation(user: User, booking: Booking, event: Event):
        try:
            logger.info("Sending booking confirmation to %s for booking %s", user.email, booking.id)
            return await email_service.send_booking_confirmation(user, booking, event)
        except Exception:
            logger.exception("Error sending booking confirmation to %s", getattr(user, "email", None))
            return False

    @staticmethod
    async def send_cancellation_notice(user: User, booking: Booking, event: Event):
        try:
            logger.info("Sending cancellation notice to %s for booking %s", user.email, booking.id)
            return await email_service.send_cancellation_notice(user, booking, event)
        except Exception:
            logger.exception("Error sending cancellation notice to %s", getattr(user, "email", None))
            return False
