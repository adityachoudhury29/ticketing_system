from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import exc as sa_exc
from ..models.models import Event, Seat, SeatStatus


async def create_event(
    db: AsyncSession,
    name: str,
    venue: str,
    description: Optional[str],
    start_time: datetime,
    end_time: datetime,
    total_capacity: int,
    created_by: int
) -> Event:
    """Create a new event"""
    db_event = Event(
        name=name,
        venue=venue,
        description=description,
        start_time=start_time,
        end_time=end_time,
        total_capacity=total_capacity,
        created_by=created_by
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event


async def get_event_by_id(db: AsyncSession, event_id: int) -> Optional[Event]:
    """Get event by ID"""
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    return result.scalar_one_or_none()


async def get_events(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    upcoming_only: bool = True
) -> List[Event]:
    """Get list of events"""
    query = select(Event)
    
    if upcoming_only:
        now = datetime.now(timezone.utc)
        query = query.where(Event.start_time > now)
    
    query = query.order_by(Event.start_time).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def update_event(
    db: AsyncSession,
    event_id: int,
    update_data: dict
) -> Optional[Event]:
    """Update an event"""
    if not update_data:
        return await get_event_by_id(db, event_id)
    
    await db.execute(
        update(Event)
        .where(Event.id == event_id)
        .values(**update_data)
    )
    await db.commit()
    return await get_event_by_id(db, event_id)


async def delete_event(db: AsyncSession, event_id: int) -> bool:
    """Delete an event with ORM cascades (seats, bookings, tickets, waitlist)."""
    try:
        event = await get_event_by_id(db, event_id)
        if not event:
            return False
        await db.delete(event)          # Use ORM delete (triggers relationship cascades)
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        # Let caller turn this into HTTPException; keep message for debugging
        raise RuntimeError(f"Failed to delete event: {e}")


async def create_seats_for_event(db: AsyncSession, event_id: int, seat_identifiers: List[str]) -> List[Seat]:
    """Create seats for an event, skipping existing (idempotent)."""
    if not seat_identifiers:
        return []
    
    # Fetch existing seat identifiers for this event
    existing_result = await db.execute(
        select(Seat.seat_identifier).where(
            and_(Seat.event_id == event_id, Seat.seat_identifier.in_(seat_identifiers))
        )
    )
    existing = {row[0] for row in existing_result.all()}
    new_ids = [sid for sid in seat_identifiers if sid not in existing]
    
    seats = [
        Seat(event_id=event_id, seat_identifier=sid, status=SeatStatus.AVAILABLE)
        for sid in new_ids
    ]
    if not seats:
        return []
    
    db.add_all(seats)
    try:
        await db.commit()
    except sa_exc.IntegrityError:
        await db.rollback()
        raise
    return seats


async def get_event_seats(db: AsyncSession, event_id: int) -> List[Seat]:
    """Get all seats for an event"""
    result = await db.execute(
        select(Seat).where(Seat.event_id == event_id).order_by(Seat.id)
    )
    return result.scalars().all()


async def get_available_seats_count(db: AsyncSession, event_id: int) -> int:
    """Count available seats for an event"""
    result = await db.execute(
        select(func.count(Seat.id)).where(
            and_(Seat.event_id == event_id, Seat.status == SeatStatus.AVAILABLE)
        )
    )
    return result.scalar() or 0

from sqlalchemy import select, func, desc, Date
from ..models.models import Booking, BookingStatus, Event, Ticket

async def get_popular_events_stats(db: AsyncSession, limit: int = 10):
    """
    Return (event_id, event_name, booking_count) ordered by booking_count desc.
    """
    stmt = (
        select(
            Event.id.label("event_id"),
            Event.name.label("event_name"),
            func.count(Booking.id).label("booking_count")
        )
        .join(Booking, Booking.event_id == Event.id)
        .where(Booking.status == BookingStatus.CONFIRMED)
        .group_by(Event.id, Event.name)
        .order_by(desc(func.count(Booking.id)))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.all()


async def get_daily_booking_trends(
    db: AsyncSession,
    days: int = 30
):
    """
    Returns list of (day, bookings, revenue) for the last `days` (inclusive today).
    Missing days will be synthesized with zeros.
    """
    from datetime import datetime, timedelta, timezone
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days - 1)

    # Aggregate bookings per day
    stmt = (
        select(
            func.date(Booking.created_at).label("day"),
            func.count(Booking.id).label("bookings"),
            func.coalesce(func.sum(Ticket.price), 0).label("revenue")
        )
        .join(Ticket, Ticket.booking_id == Booking.id, isouter=True)
        .where(
            Booking.status == BookingStatus.CONFIRMED,
            func.date(Booking.created_at) >= start_date,
            func.date(Booking.created_at) <= end_date
        )
        .group_by(func.date(Booking.created_at))
        .order_by(func.date(Booking.created_at))
    )
    result = await db.execute(stmt)
    rows = {r.day: (r.bookings, r.revenue) for r in result.all()}

    # Fill gaps
    output = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        b, rev = rows.get(d, (0, 0))
        output.append({"date": d.isoformat(), "bookings": b, "revenue": rev})
    return output