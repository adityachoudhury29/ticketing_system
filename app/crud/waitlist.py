from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from typing import Optional, List
from uuid import UUID
from ..models.models import WaitlistEntry


async def join_waitlist(db: AsyncSession, user_id: UUID, event_id: UUID) -> WaitlistEntry:
    """Add user to event waitlist"""
    # Check if user is already on waitlist
    existing = await db.execute(
        select(WaitlistEntry).where(
            and_(WaitlistEntry.user_id == user_id, WaitlistEntry.event_id == event_id)
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("User already on waitlist for this event")
    
    waitlist_entry = WaitlistEntry(user_id=user_id, event_id=event_id)
    db.add(waitlist_entry)
    await db.commit()
    await db.refresh(waitlist_entry)
    return waitlist_entry


async def get_next_waitlist_user(db: AsyncSession, event_id: UUID) -> Optional[WaitlistEntry]:
    """Get the next user on the waitlist for an event"""
    result = await db.execute(
        select(WaitlistEntry)
        .where(WaitlistEntry.event_id == event_id)
        .order_by(WaitlistEntry.joined_at)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def remove_from_waitlist(db: AsyncSession, user_id: UUID, event_id: UUID) -> bool:
    """Remove user from waitlist"""
    result = await db.execute(
        delete(WaitlistEntry).where(
            and_(WaitlistEntry.user_id == user_id, WaitlistEntry.event_id == event_id)
        )
    )
    await db.commit()
    return result.rowcount > 0


async def get_user_waitlist_entries(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[WaitlistEntry]:
    """Get user's waitlist entries"""
    result = await db.execute(
        select(WaitlistEntry)
        .where(WaitlistEntry.user_id == user_id)
        .order_by(WaitlistEntry.joined_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_all_waitlist_users(db: AsyncSession, event_id: UUID) -> List[WaitlistEntry]:
    """Get all users on the waitlist for an event, ordered by join time (first-come, first-served)"""
    result = await db.execute(
        select(WaitlistEntry)
        .where(WaitlistEntry.event_id == event_id)
        .order_by(WaitlistEntry.joined_at)
    )
    return result.scalars().all()
