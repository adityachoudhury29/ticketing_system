from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
import uuid
import logging
from ..models.models import Booking, Ticket, Seat, SeatStatus, BookingStatus

logger = logging.getLogger(__name__)

async def create_booking_with_seats(
    db: AsyncSession,
    user_id: UUID,
    event_id: UUID,
    seat_identifiers: List[str]
) -> Booking:
    """
    Create a booking with pessimistic locking.
    NO COMMIT here; caller (service layer) is responsible for commit/rollback.
    """
    # Lock the seats first
    seat_query = (
        select(Seat)
        .where(
            and_(
                Seat.event_id == event_id,
                Seat.seat_identifier.in_(seat_identifiers)
            )
        )
        .with_for_update()
    )
    result = await db.execute(seat_query)
    locked_seats = result.scalars().all()

    if len(locked_seats) != len(seat_identifiers):
        found = {s.seat_identifier for s in locked_seats}
        missing = sorted(set(seat_identifiers) - found)
        raise ValueError(f"Seats not found: {missing}")

    unavailable = [s.seat_identifier for s in locked_seats if s.status != SeatStatus.AVAILABLE]
    if unavailable:
        raise ValueError(f"Seats no longer available: {sorted(unavailable)}")

    # Update seat status
    for seat in locked_seats:
        seat.status = SeatStatus.BOOKED

    # Create booking
    booking = Booking(
        user_id=user_id,
        event_id=event_id,
        status=BookingStatus.CONFIRMED
    )
    db.add(booking)
    await db.flush()  # Get booking.id

    # Create tickets
    tickets: List[Ticket] = []
    for seat in locked_seats:
        ticket = Ticket(
            booking_id=booking.id,
            seat_id=seat.id,
            qr_code_data=f"booking_{booking.id}_seat_{seat.id}_{uuid.uuid4().hex[:8]}"
        )
        tickets.append(ticket)
    
    db.add_all(tickets)
    await db.flush()  # Get ticket IDs
    
    # Refresh the booking with tickets loaded to avoid lazy loading issues
    await db.refresh(booking)
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.tickets))
        .where(Booking.id == booking.id)
    )
    booking_with_tickets = result.scalar_one()
    
    return booking_with_tickets


async def get_user_bookings(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[Booking]:
    """Get user's bookings with tickets"""
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.tickets))
        .where(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_booking_by_id(db: AsyncSession, booking_id: UUID) -> Optional[Booking]:
    """Get booking by ID with tickets"""
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.tickets))
        .where(Booking.id == booking_id)
    )
    return result.scalar_one_or_none()


async def cancel_booking(
    db: AsyncSession,
    booking_id: UUID,
    user_id: UUID
) -> Optional[Booking]:
    """
    Cancel a booking owned by user_id (idempotent).
    Returns the (possibly already cancelled) booking or None if not found.
    """
    try:
        result = await db.execute(
            select(Booking)
            .options(
                selectinload(Booking.tickets).selectinload(Ticket.seat),
                selectinload(Booking.event)
            )
            .where(and_(Booking.id == booking_id, Booking.user_id == user_id))
        )
        booking = result.scalar_one_or_none()
        if not booking:
            return None

        if booking.status == BookingStatus.CANCELLED:
            return booking  # Idempotent

        # Release seats
        for ticket in booking.tickets:
            if ticket.seat and ticket.seat.status == SeatStatus.BOOKED:
                ticket.seat.status = SeatStatus.AVAILABLE

        booking.status = BookingStatus.CANCELLED
        await db.commit()
        await db.refresh(booking)
        return booking
    except Exception as e:
        await db.rollback()
        logger.error(f"Error cancelling booking {booking_id}: {e}", exc_info=True)
        raise


async def get_booking_analytics(db: AsyncSession) -> dict:
    """Get booking analytics"""
    # Total bookings
    total_bookings_result = await db.execute(
        select(func.count(Booking.id)).where(Booking.status == BookingStatus.CONFIRMED)
    )
    total_bookings = total_bookings_result.scalar() or 0
    
    # Revenue calculation (assuming each ticket is $50 for simplicity)
    total_tickets_result = await db.execute(
        select(func.count(Ticket.id))
        .join(Booking)
        .where(Booking.status == BookingStatus.CONFIRMED)
    )
    total_tickets = total_tickets_result.scalar() or 0
    total_revenue = total_tickets * 50.0  # $50 per ticket
    
    return {
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
        "total_tickets": total_tickets
    }
