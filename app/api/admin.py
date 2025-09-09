from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime, timedelta
from ..db.session import get_db
from ..schemas.schemas import (
    EventCreate, EventUpdate, EventResponse, 
    AnalyticsSummary, PopularEvent, DailyTrend
)
from ..crud.event import create_event, get_event_by_id, update_event, delete_event, get_events
from ..crud.booking import get_booking_analytics, get_popular_events_stats, get_daily_booking_trends
from ..crud.user import get_users
from ..services.booking import EventService
from ..services.cache import CacheService
from ..core.deps import get_current_admin_user
from ..models.models import User
from ..schemas.schemas import EventCreate, EventResponse

router = APIRouter()


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_new_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Create a new event and initialize its seats (returns 201)."""
    # Basic validations
    if event_data.end_time <= event_data.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be after start_time"
        )
    if event_data.total_capacity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="total_capacity must be > 0"
        )
    try:
        event = await EventService.create_event_with_seats(
            db=db,
            name=event_data.name,
            venue=event_data.venue,
            description=event_data.description,
            start_time=event_data.start_time,
            end_time=event_data.end_time,
            total_capacity=event_data.total_capacity,
            created_by=current_admin.id
        )
        # Invalidate cached event lists
        CacheService.delete_pattern("events:list:*")
        return EventResponse.model_validate(event)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_existing_event(
    event_id: int,
    event_data: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update an existing event"""
    # Check if event exists
    existing_event = await get_event_by_id(db, event_id)
    if not existing_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Update event
    update_data = event_data.model_dump(exclude_unset=True)
    updated_event = await update_event(db, event_id, update_data)
    
    # Clear related caches
    CacheService.delete_pattern("events:list:*")
    CacheService.delete(f"event:{event_id}")
    
    return EventResponse.model_validate(updated_event)


@router.delete("/events/{event_id}")
async def delete_existing_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    existing_event = await get_event_by_id(db, event_id)
    if not existing_event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    try:
        success = await delete_event(db, event_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete event")
    CacheService.delete_pattern("events:list:*")
    CacheService.delete(f"event:{event_id}")
    CacheService.delete(f"event:{event_id}:seats")
    return {"message": "Event deleted successfully"}


@router.get("/events", response_model=List[EventResponse])
async def list_all_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_past: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all events (including past events for admin)"""
    events = await get_events(
        db, skip=skip, limit=limit, upcoming_only=not include_past
    )
    
    return [EventResponse.model_validate(event) for event in events]


@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get overall analytics summary"""
    try:
        # Get booking analytics
        booking_data = await get_booking_analytics(db)
        
        # Get total events count
        all_events = await get_events(db, skip=0, limit=10000, upcoming_only=False)
        total_events = len(all_events)
        
        # Get total users count  
        all_users = await get_users(db, skip=0, limit=10000)
        total_users = len(all_users)
        
        return AnalyticsSummary(
            total_events=total_events,
            total_bookings=booking_data["total_bookings"],
            total_revenue=booking_data["total_revenue"],
            total_users=total_users
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analytics: {str(e)}"
        )


@router.get("/analytics/events/popular", response_model=List[PopularEvent])
async def get_popular_events(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get most popular events by confirmed booking count"""
    rows = await get_popular_events_stats(db, limit=limit)
    return [
        PopularEvent(event_id=r.event_id, event_name=r.event_name, booking_count=r.booking_count)
        for r in rows
    ]


@router.get("/analytics/trends/daily", response_model=List[DailyTrend])
async def get_daily_trends(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get real daily booking trends (confirmed bookings and revenue)"""
    data = await get_daily_booking_trends(db, days=days)
    return [DailyTrend(**row) for row in data]