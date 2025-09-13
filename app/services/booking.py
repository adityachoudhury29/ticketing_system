from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from ..crud import booking as booking_crud, event as event_crud
from ..models.models import Booking, Seat, SeatStatus, Event
from .cache import CacheService, get_event_seats_cache_key
from .pricing import DynamicPricingService
import logging

logger = logging.getLogger(__name__)

class BookingService:
    """Service for handling booking operations"""
    
    @staticmethod
    async def create_booking(
        db: AsyncSession,
        user_id: UUID,
        event_id: UUID,
        seat_identifiers: List[str],
        acknowledged_price_per_ticket: Optional[float] = None
    ) -> Booking:
        """
        Create a booking with proper transaction handling and dynamic pricing.
        This method now handles its own transaction.
        """
        try:
            # Verify event exists first
            event = await event_crud.get_event_by_id(db, event_id)
            if not event:
                raise ValueError("Event not found")
            
            # Calculate dynamic pricing
            current_price = DynamicPricingService.calculate_current_price(
                event.base_price, event.start_time
            )
            
            # Check if price was acknowledged (optional safety check)
            if acknowledged_price_per_ticket is not None:
                price_diff = abs(current_price - acknowledged_price_per_ticket)
                if price_diff > 0.01:  # Allow small rounding differences
                    raise ValueError(
                        f"Price has changed. Current price: ${current_price:.2f}, "
                        f"acknowledged: ${acknowledged_price_per_ticket:.2f}"
                    )
            
            # Calculate pricing details
            num_tickets = len(seat_identifiers)
            pricing_details = DynamicPricingService.calculate_total_booking_cost(
                event.base_price, event.start_time, num_tickets
            )
            
            # Create booking with pricing information
            booking = await booking_crud.create_booking_with_seats(
                db, user_id, event_id, seat_identifiers,
                base_price_per_ticket=event.base_price,
                final_price_per_ticket=current_price,
                price_multiplier=pricing_details["price_multiplier"],
                total_amount=pricing_details["total_cost"]
            )
            
            # Commit the transaction
            await db.commit()
            
            # Invalidate seat cache after successful commit
            CacheService.delete(get_event_seats_cache_key(event_id))
            
            # Send booking confirmation email asynchronously
            try:
                from ..worker.tasks import send_booking_confirmation_email
                send_booking_confirmation_email.delay(str(booking.id))
            except Exception as e:
                print(f"Failed to enqueue booking confirmation email task: {e}")
                pass
            
            return booking
            
        except (ValueError, RuntimeError) as e:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            raise RuntimeError(f"Failed to create booking: {str(e)}")
    
    @staticmethod
    async def cancel_booking(
        db: AsyncSession,
        booking_id: UUID,
        user_id: UUID
    ) -> Optional[Booking]:
        booking = await booking_crud.cancel_booking(db, booking_id, user_id)
        logger.info("Cancelled booking %s for user %s", booking_id, user_id)
        if booking:
            logger.info("Booking %s cancelled successfully", booking_id)
            # Invalidate seat cache
            CacheService.delete(get_event_seats_cache_key(booking.event_id))
            
            # Send cancellation email asynchronously
            try:
                logger.info("Enqueuing cancellation email for booking %s", booking.id)
                from ..worker.tasks import send_booking_cancellation_email
                send_booking_cancellation_email.delay(str(booking.id))
            except Exception as e:
                # Log error but don't fail the cancellation
                logger.exception("Failed to enqueue cancellation email task for booking %s %s", booking.id, e)
                pass
            
            # Notify ALL waitlisted users when seats become available
            available = await event_crud.get_available_seats_count(db, booking.event_id)
            if available > 0:
                try:
                    logger.info("Seats became available for event %s, notifying all waitlisted users", booking.event_id)
                    from ..worker.tasks import notify_all_waitlist_users
                    notify_all_waitlist_users.delay(str(booking.event_id))
                except Exception as e:
                    logger.exception("Failed to enqueue waitlist notification task for event %s: %s", booking.event_id, e)
        return booking

class EventService:
    """Service for handling event operations"""

    @staticmethod
    def generate_default_seat_layout(total_capacity: int) -> List[str]:
        # Simple linear layout A01-01 ... A01-NN
        return [f"A01-{i:02d}" for i in range(1, total_capacity + 1)]

    @staticmethod
    async def create_event_with_seats(
        db: AsyncSession,
        name: str,
        venue: str,
        description: Optional[str],
        start_time,
        end_time,
        total_capacity: int,
        created_by: UUID,
        base_price: float = 50.0,
        seat_layout: Optional[List[str]] = None
    ):
        """
        Create an event and its seats atomically using the session's existing transaction.
        Avoid nested 'db.begin()' which caused: 'A transaction is already begun on this Session.'
        """
        try:
            # Build event
            event = Event(
                name=name,
                venue=venue,
                description=description,
                start_time=start_time,
                end_time=end_time,
                total_capacity=total_capacity,
                base_price=base_price,
                created_by=created_by
            )
            db.add(event)
            await db.flush()  # Get event.id

            # Seat layout
            if not seat_layout:
                seat_layout = EventService.generate_default_seat_layout(total_capacity)

            # De-duplicate provided identifiers (defensive)
            unique = []
            seen = set()
            for sid in seat_layout:
                if sid not in seen:
                    seen.add(sid)
                    unique.append(sid)

            seats = [
                Seat(event_id=event.id, seat_identifier=sid, status=SeatStatus.AVAILABLE)
                for sid in unique
            ]
            db.add_all(seats)

            # Commit (single transaction)
            await db.commit()

        except Exception:
            await db.rollback()
            raise

        # Invalidate caches & refresh
        CacheService.delete_pattern("events:list:*")
        await db.refresh(event)
        return event