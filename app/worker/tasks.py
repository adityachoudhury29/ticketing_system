from .celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, selectinload
from uuid import UUID
from ..core.config import settings
from ..models.models import User, Event, Booking, WaitlistEntry
from ..services.email import EmailService
import logging

logger = logging.getLogger(__name__)

# Create synchronous database engine and session for Celery
# Convert async postgresql+asyncpg URL to sync psycopg2 URL
sync_database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
sync_engine = create_engine(sync_database_url, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Create a synchronous email service instance
email_service = EmailService()


@celery_app.task
def notify_waitlist_user(event_id):  # Can be UUID object or string
    """
    DEPRECATED: Background task to notify the next user on the waitlist.
    Use notify_all_waitlist_users instead for better user experience.
    """
    try:
        with SyncSessionLocal() as db:
            # Get the next waitlist user for this event
            # Handle both UUID objects and strings
            if isinstance(event_id, str):
                event_uuid = UUID(event_id)
            else:
                event_uuid = event_id  # Already a UUID object
            
            waitlist_entry = db.query(WaitlistEntry).filter(
                WaitlistEntry.event_id == event_uuid
            ).first()
            
            if not waitlist_entry:
                logger.info("No waitlist entry found for event %s", event_id)
                return f"No waitlist entry for event {event_id}"

            # Get user and event
            user = db.query(User).filter(User.id == waitlist_entry.user_id).first()
            event = db.query(Event).filter(Event.id == event_uuid).first()

            if not user or not event:
                logger.error("Missing user or event while notifying waitlist (user=%s event=%s)", user, event)
                return f"Missing data for event {event_id}"

            # Send the notification email (synchronously)
            import asyncio
            sent = asyncio.run(email_service.send_waitlist_notification(user, event))
            if sent:
                logger.info("Sent waitlist email to user %s for event %s", user.email, event.id)
            else:
                logger.warning("Failed to send waitlist email to user %s for event %s", user.email, event.id)

        return f"Processed waitlist notification for event {event_id}"
    except Exception as e:
        logger.exception("Failed to process waitlist notification for event %s: %s", event_id, e)
        raise


@celery_app.task
def notify_all_waitlist_users(event_id):  # Can be UUID object or string
    """
    Background task to notify ALL users on the waitlist
    when seats become available for an event.
    This gives everyone a fair chance to book newly available seats.
    """
    try:
        with SyncSessionLocal() as db:
            # Handle both UUID objects and strings
            if isinstance(event_id, str):
                event_uuid = UUID(event_id)
            else:
                event_uuid = event_id  # Already a UUID object
            
            # Get all waitlist users for this event, ordered by join time
            waitlist_entries = db.query(WaitlistEntry).filter(
                WaitlistEntry.event_id == event_uuid
            ).order_by(WaitlistEntry.joined_at).all()
            
            if not waitlist_entries:
                logger.info("No waitlist entries found for event %s", event_id)
                return f"No waitlist entries for event {event_id}"

            # Get event details
            event = db.query(Event).filter(Event.id == event_uuid).first()
            if not event:
                logger.error("Event %s not found while notifying waitlist", event_id)
                return f"Event {event_id} not found"

            # Send notifications to all waitlisted users
            successful_notifications = 0
            failed_notifications = 0
            
            for waitlist_entry in waitlist_entries:
                user = db.query(User).filter(User.id == waitlist_entry.user_id).first()
                
                if not user:
                    logger.warning("User %s not found for waitlist entry", waitlist_entry.user_id)
                    failed_notifications += 1
                    continue

                try:
                    # Send the notification email (synchronously)
                    import asyncio
                    sent = asyncio.run(email_service.send_waitlist_notification(user, event))
                    if sent:
                        logger.info("Sent waitlist email to user %s for event %s", user.email, event.id)
                        successful_notifications += 1
                    else:
                        logger.warning("Failed to send waitlist email to user %s for event %s", user.email, event.id)
                        failed_notifications += 1
                except Exception as e:
                    logger.exception("Error sending waitlist notification to user %s: %s", user.email, e)
                    failed_notifications += 1

        logger.info(
            "Waitlist notification summary for event %s: %d successful, %d failed",
            event_id, successful_notifications, failed_notifications
        )
        return f"Sent {successful_notifications} waitlist notifications for event {event_id} ({failed_notifications} failed)"
        
    except Exception as e:
        logger.exception("Failed to process waitlist notifications for event %s: %s", event_id, e)
        raise


@celery_app.task
def send_booking_confirmation_email(booking_id):  # Can be UUID object or string
    """
    Background task to send booking confirmation email.
    """
    try:
        with SyncSessionLocal() as db:
            # Get booking with tickets loaded
            # Handle both UUID objects and strings
            if isinstance(booking_id, str):
                booking_uuid = UUID(booking_id)
            else:
                booking_uuid = booking_id  # Already a UUID object
            
            booking = db.query(Booking).options(
                selectinload(Booking.tickets)
            ).filter(Booking.id == booking_uuid).first()
            
            if not booking:
                logger.error("Booking %s not found for confirmation email", booking_id)
                return f"Booking {booking_id} not found"

            # Get user and event
            user = db.query(User).filter(User.id == booking.user_id).first()
            event = db.query(Event).filter(Event.id == booking.event_id).first()

            if not user or not event:
                logger.error("Missing user or event for booking confirmation email (user=%s event=%s)", user, event)
                return f"Missing data for booking {booking_id}"

            # Send the confirmation email (synchronously)
            import asyncio
            sent = asyncio.run(email_service.send_booking_confirmation(user, booking, event))
            if sent:
                logger.info("Sent booking confirmation email to user %s for booking %s", user.email, booking.id)
            else:
                logger.warning("Failed to send booking confirmation email to user %s for booking %s", user.email, booking.id)

        return f"Sent booking confirmation email for booking {booking_id}"
    except Exception as e:
        logger.exception("Failed to send booking confirmation email for booking %s: %s", booking_id, e)
        raise


@celery_app.task
def send_booking_cancellation_email(booking_id):  # Can be UUID object or string
    """
    Background task to send booking cancellation email.
    """
    try:
        with SyncSessionLocal() as db:
            # Get booking with tickets loaded (even if cancelled)
            # Handle both UUID objects and strings
            if isinstance(booking_id, str):
                booking_uuid = UUID(booking_id)
            else:
                booking_uuid = booking_id  # Already a UUID object
            
            booking = db.query(Booking).options(
                selectinload(Booking.tickets)
            ).filter(Booking.id == booking_uuid).first()
            
            if not booking:
                logger.error("Booking %s not found for cancellation email", booking_id)
                return f"Booking {booking_id} not found"

            # Get user and event
            user = db.query(User).filter(User.id == booking.user_id).first()
            event = db.query(Event).filter(Event.id == booking.event_id).first()

            if not user or not event:
                logger.error("Missing user or event for booking cancellation email (user=%s event=%s)", user, event)
                return f"Missing data for booking {booking_id}"

            # Send the cancellation email (synchronously)
            import asyncio
            sent = asyncio.run(email_service.send_cancellation_notice(user, booking, event))
            if sent:
                logger.info("Sent booking cancellation email to user %s for booking %s", user.email, booking.id)
            else:
                logger.warning("Failed to send booking cancellation email to user %s for booking %s", user.email, booking.id)

        return f"Sent booking cancellation email for booking {booking_id}"
    except Exception as e:
        logger.exception("Failed to send booking cancellation email for booking %s: %s", booking_id, e)
        raise
