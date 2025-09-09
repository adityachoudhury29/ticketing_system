import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from datetime import datetime
from ..core.config import settings
from ..models.models import User, Event, Booking


class EmailService:
    """Email notification service"""
    
    def __init__(self):
        # Email configuration (would be in settings in production)
        self.smtp_server = "smtp.gmail.com"  # Configure as needed
        self.smtp_port = 587
        self.username = "achoudhury2004@gmail.com"  # Configure in settings
        self.password = "your-app-password"  # Configure in settings
        self.from_email = "noreply@evently.com"
        self.enabled = True  # Set to True when properly configured
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """Send email asynchronously"""
        if not self.enabled:
            print(f"📧 Email disabled - Would send to {to_email}: {subject}")
            return True
        
        try:
            # Run email sending in thread to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_email_sync, to_email, subject, body, html_body
            )
            return True
        except Exception as e:
            print(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def _send_email_sync(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ):
        """Synchronous email sending"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email
        
        # Add text part
        text_part = MIMEText(body, "plain")
        msg.attach(text_part)
        
        # Add HTML part if provided
        if html_body:
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
    
    async def send_booking_confirmation(
        self,
        user: User,
        booking: Booking,
        event: Event
    ) -> bool:
        """Send booking confirmation email"""
        subject = f"Booking Confirmation - {event.name}"
        
        body = f"""
Dear Customer,

Your booking has been confirmed!

Event Details:
- Event: {event.name}
- Venue: {event.venue}
- Date: {event.start_time.strftime('%B %d, %Y at %I:%M %p')}
- Booking ID: {booking.id}
- Number of Tickets: {len(booking.tickets)}

Seat Details:
{self._format_seats(booking.tickets)}

Please arrive at least 30 minutes before the event starts.

Thank you for choosing Evently!

Best regards,
Evently Team
        """
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .event-details {{ background-color: #f9f9f9; padding: 15px; border-left: 4px solid #4CAF50; }}
        .seats {{ background-color: #fff3cd; padding: 10px; border: 1px solid #ffeaa7; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Booking Confirmed!</h1>
    </div>
    <div class="content">
        <p>Dear Customer,</p>
        <p>Your booking has been confirmed for <strong>{event.name}</strong>!</p>
        
        <div class="event-details">
            <h3>Event Details</h3>
            <ul>
                <li><strong>Event:</strong> {event.name}</li>
                <li><strong>Venue:</strong> {event.venue}</li>
                <li><strong>Date:</strong> {event.start_time.strftime('%B %d, %Y at %I:%M %p')}</li>
                <li><strong>Booking ID:</strong> {booking.id}</li>
                <li><strong>Number of Tickets:</strong> {len(booking.tickets)}</li>
            </ul>
        </div>
        
        <div class="seats">
            <h4>Your Seats:</h4>
            {self._format_seats_html(booking.tickets)}
        </div>
        
        <p><strong>Important:</strong> Please arrive at least 30 minutes before the event starts.</p>
        
        <p>Thank you for choosing Evently!</p>
        
        <p>Best regards,<br>Evently Team</p>
    </div>
</body>
</html>
        """
        
        return await self.send_email(user.email, subject, body, html_body)
    
    async def send_cancellation_notice(
        self,
        user: User,
        booking: Booking,
        event: Event
    ) -> bool:
        """Send booking cancellation notice"""
        subject = f"Booking Cancelled - {event.name}"
        
        body = f"""
Dear Customer,

Your booking has been cancelled.

Event Details:
- Event: {event.name}
- Venue: {event.venue}
- Date: {event.start_time.strftime('%B %d, %Y at %I:%M %p')}
- Booking ID: {booking.id}
- Cancelled Tickets: {len(booking.tickets)}

If you cancelled this booking, no further action is required.
If you did not cancel this booking, please contact our support team immediately.

Best regards,
Evently Team
        """
        
        return await self.send_email(user.email, subject, body)
    
    async def send_waitlist_notification(
        self,
        user: User,
        event: Event
    ) -> bool:
        """Send waitlist availability notification"""
        subject = f"Seats Available - {event.name}"
        
        body = f"""
Dear Customer,

Good news! Seats are now available for the event you're waitlisted for.

Event Details:
- Event: {event.name}
- Venue: {event.venue}
- Date: {event.start_time.strftime('%B %d, %Y at %I:%M %p')}

Book your seats now before they're gone!

Visit our website to complete your booking: [BOOKING_LINK]

This opportunity won't last long, so act quickly!

Best regards,
Evently Team
        """
        
        return await self.send_email(user.email, subject, body)
    
    async def send_event_reminder(
        self,
        user: User,
        booking: Booking,
        event: Event,
        hours_before: int = 24
    ) -> bool:
        """Send event reminder"""
        subject = f"Event Reminder - {event.name} in {hours_before} hours"
        
        body = f"""
Dear Customer,

This is a reminder that your event is coming up in {hours_before} hours!

Event Details:
- Event: {event.name}
- Venue: {event.venue}
- Date: {event.start_time.strftime('%B %d, %Y at %I:%M %p')}
- Your Seats: {self._format_seats(booking.tickets)}

Don't forget to:
- Arrive at least 30 minutes early
- Bring a valid ID
- Check the venue's policies

We look forward to seeing you there!

Best regards,
Evently Team
        """
        
        return await self.send_email(user.email, subject, body)
    
    def _format_seats(self, tickets) -> str:
        """Format seat information for plain text"""
        if not tickets:
            return "No seats assigned"
        
        seats = []
        for ticket in tickets:
            if hasattr(ticket, 'seat') and ticket.seat:
                seats.append(ticket.seat.seat_identifier)
        
        return ", ".join(seats) if seats else "Seat information not available"
    
    def _format_seats_html(self, tickets) -> str:
        """Format seat information for HTML"""
        if not tickets:
            return "<p>No seats assigned</p>"
        
        seats = []
        for ticket in tickets:
            if hasattr(ticket, 'seat') and ticket.seat:
                seats.append(f"<span style='background-color: #e3f2fd; padding: 2px 6px; border-radius: 3px;'>{ticket.seat.seat_identifier}</span>")
        
        return " ".join(seats) if seats else "<p>Seat information not available</p>"


# Global email service instance
email_service = EmailService()


class NotificationService:
    """High-level notification service"""
    
    @staticmethod
    async def send_booking_confirmation(user: User, booking: Booking, event: Event):
        """Send booking confirmation with error handling"""
        try:
            success = await email_service.send_booking_confirmation(user, booking, event)
            if success:
                print(f"✅ Booking confirmation sent to {user.email}")
            else:
                print(f"❌ Failed to send booking confirmation to {user.email}")
        except Exception as e:
            print(f"❌ Error sending booking confirmation: {str(e)}")
    
    @staticmethod
    async def send_cancellation_notice(user: User, booking: Booking, event: Event):
        """Send cancellation notice with error handling"""
        try:
            success = await email_service.send_cancellation_notice(user, booking, event)
            if success:
                print(f"✅ Cancellation notice sent to {user.email}")
            else:
                print(f"❌ Failed to send cancellation notice to {user.email}")
        except Exception as e:
            print(f"❌ Error sending cancellation notice: {str(e)}")
    
    @staticmethod
    async def send_waitlist_notification(user: User, event: Event):
        """Send waitlist notification with error handling"""
        try:
            success = await email_service.send_waitlist_notification(user, event)
            if success:
                print(f"✅ Waitlist notification sent to {user.email}")
            else:
                print(f"❌ Failed to send waitlist notification to {user.email}")
        except Exception as e:
            print(f"❌ Error sending waitlist notification: {str(e)}")
    
    @staticmethod
    async def send_bulk_notifications(
        users_and_events: List[tuple[User, Event]],
        notification_type: str = "waitlist"
    ):
        """Send bulk notifications"""
        tasks = []
        
        for user, event in users_and_events:
            if notification_type == "waitlist":
                task = NotificationService.send_waitlist_notification(user, event)
            else:
                continue
            
            tasks.append(task)
        
        # Send all notifications concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
