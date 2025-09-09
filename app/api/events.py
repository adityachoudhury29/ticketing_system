from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..db.session import get_db
from ..schemas.schemas import EventResponse, SeatMapResponse, SeatResponse
from ..crud.event import get_events, get_event_by_id, get_event_seats
from ..services.cache import CacheService, get_events_cache_key, get_event_cache_key, get_event_seats_cache_key
from ..core.deps import get_current_user_optional
from ..models.models import User

router = APIRouter()


@router.get("/", response_model=List[EventResponse])
async def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get list of upcoming events (public endpoint with caching)"""
    
    # Try to get from cache first
    cache_key = get_events_cache_key(skip, limit)
    cached_events = CacheService.get(cache_key)
    
    if cached_events:
        return cached_events
    
    # Get from database
    events = await get_events(db, skip=skip, limit=limit, upcoming_only=True)
    
    # Convert to response format
    events_response = [EventResponse.model_validate(event) for event in events]
    
    # Cache for 30 minutes
    CacheService.set(cache_key, [event.model_dump() for event in events_response], expire=1800)
    
    return events_response


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get detailed information for a single event"""
    
    # Try cache first
    cache_key = get_event_cache_key(event_id)
    cached_event = CacheService.get(cache_key)
    
    if cached_event:
        return EventResponse(**cached_event)
    
    # Get from database
    event = await get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    event_response = EventResponse.model_validate(event)
    
    # Cache for 1 hour
    CacheService.set(cache_key, event_response.model_dump(), expire=3600)
    
    return event_response


@router.get("/{event_id}/seats", response_model=SeatMapResponse)
async def get_event_seat_map(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get the seat map and status for an event.
    This is essential for frontend to render visual seat selection.
    """
    
    # Check if event exists
    event = await get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Try cache first (shorter cache time due to frequent updates)
    cache_key = get_event_seats_cache_key(event_id)
    cached_seats = CacheService.get(cache_key)
    
    if cached_seats:
        return SeatMapResponse(
            event_id=event_id,
            seats=[SeatResponse(**seat) for seat in cached_seats]
        )
    
    # Get from database
    seats = await get_event_seats(db, event_id)
    seats_response = [SeatResponse.model_validate(seat) for seat in seats]
    
    # Cache for 5 minutes (seats change frequently during booking)
    CacheService.set(
        cache_key, 
        [seat.model_dump() for seat in seats_response], 
        expire=300
    )
    
    return SeatMapResponse(event_id=event_id, seats=seats_response)
