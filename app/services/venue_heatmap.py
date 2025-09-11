from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text, desc
from sqlalchemy.orm import selectinload
from ..models.models import (
    Event, Seat, SeatStatus, Booking, BookingStatus, 
    Ticket, SeatAnalytics
)
from ..schemas.schemas import VenueHeatmapResponse, SeatHeatmapData
from .cache import CacheService
import math


class VenueHeatmapService:
    """Service for generating venue heatmap data for admin analytics"""
    
    @staticmethod
    def get_heatmap_cache_key(event_id: UUID) -> str:
        """Generate cache key for venue heatmap"""
        return f"venue_heatmap:{event_id}"
    
    @staticmethod
    async def generate_venue_heatmap(
        db: AsyncSession, 
        event_id: UUID,
        force_refresh: bool = False
    ) -> Optional[VenueHeatmapResponse]:
        """
        Generate venue heatmap data for an event.
        Returns cached result unless force_refresh is True.
        """
        cache_key = VenueHeatmapService.get_heatmap_cache_key(event_id)
        
        # Try cache first (unless force refresh)
        if not force_refresh:
            cached_heatmap = CacheService.get(cache_key)
            if cached_heatmap:
                return VenueHeatmapResponse(**cached_heatmap)
        
        # Get event details
        event_query = select(Event).where(Event.id == event_id)
        event_result = await db.execute(event_query)
        event = event_result.scalar_one_or_none()
        
        if not event:
            return None
        
        # Update analytics data before generating heatmap
        await VenueHeatmapService._update_seat_analytics(db, event_id)
        
        # Get seats with analytics data
        seats_query = (
            select(Seat, SeatAnalytics)
            .outerjoin(SeatAnalytics, and_(
                SeatAnalytics.seat_id == Seat.id,
                SeatAnalytics.event_id == event_id
            ))
            .where(Seat.event_id == event_id)
            .order_by(Seat.seat_identifier)
        )
        
        seats_result = await db.execute(seats_query)
        seats_data = seats_result.fetchall()
        
        # Calculate capacity stats
        total_seats = len(seats_data)
        booked_seats = sum(1 for seat_row in seats_data if seat_row[0].status == SeatStatus.BOOKED)
        capacity_percentage = (booked_seats / total_seats) if total_seats > 0 else 0.0
        
        # Generate heatmap data for each seat
        heatmap_seats = []
        for seat_row in seats_data:
            seat, analytics = seat_row[0], seat_row[1]
            
            # Use analytics data if available, otherwise defaults
            booking_speed_score = analytics.booking_speed_score if analytics else 0.0
            group_booking_score = analytics.group_booking_score if analytics else 0.0
            popularity_score = analytics.popularity_score if analytics else 0.0
            
            # Calculate overall heat intensity (weighted average)
            heat_intensity = VenueHeatmapService._calculate_heat_intensity(
                booking_speed_score, group_booking_score, popularity_score
            )
            
            heatmap_seats.append(SeatHeatmapData(
                seat_id=seat.id,
                seat_identifier=seat.seat_identifier,
                booking_speed_score=booking_speed_score,
                group_booking_score=group_booking_score,
                popularity_score=popularity_score,
                heat_intensity=heat_intensity
            ))
        
        heatmap_response = VenueHeatmapResponse(
            event_id=event_id,
            event_name=event.name,
            total_seats=total_seats,
            booked_seats=booked_seats,
            capacity_percentage=round(capacity_percentage, 3),
            seats_data=heatmap_seats,
            last_updated=datetime.utcnow()
        )
        
        # Cache for 15 minutes (analytics don't change too frequently)
        CacheService.set(cache_key, heatmap_response.model_dump(), expire=900)
        
        return heatmap_response
    
    @staticmethod
    async def _update_seat_analytics(db: AsyncSession, event_id: UUID) -> None:
        """Update seat analytics data for all seats in an event"""
        
        # Get event start time for calculations
        event_query = select(Event.start_time, Event.created_at).where(Event.id == event_id)
        event_result = await db.execute(event_query)
        event_data = event_result.first()
        
        if not event_data:
            return
        
        event_start_time, event_created_at = event_data
        
        # Get all seats for the event
        seats_query = select(Seat).where(Seat.event_id == event_id)
        seats_result = await db.execute(seats_query)
        seats = seats_result.scalars().all()
        
        for seat in seats:
            # Calculate analytics scores for this seat
            booking_speed_score = await VenueHeatmapService._calculate_booking_speed_score(
                db, seat, event_created_at, event_start_time
            )
            
            group_booking_score = await VenueHeatmapService._calculate_group_booking_score(
                db, seat, event_id
            )
            
            popularity_score = await VenueHeatmapService._calculate_popularity_score(
                booking_speed_score, group_booking_score
            )
            
            # Upsert analytics record
            await VenueHeatmapService._upsert_seat_analytics(
                db, event_id, seat.id, booking_speed_score, 
                group_booking_score, popularity_score
            )
    
    @staticmethod
    async def _calculate_booking_speed_score(
        db: AsyncSession, 
        seat: Seat, 
        event_created_at: datetime,
        event_start_time: datetime
    ) -> float:
        """Calculate how quickly this seat was booked (0-100)"""
        
        if seat.status != SeatStatus.BOOKED:
            return 0.0
        
        # Find when this seat was booked
        booking_query = (
            select(Booking.created_at)
            .join(Ticket, Ticket.booking_id == Booking.id)
            .where(
                and_(
                    Ticket.seat_id == seat.id,
                    Booking.status == BookingStatus.CONFIRMED
                )
            )
            .order_by(Booking.created_at)
            .limit(1)
        )
        
        booking_result = await db.execute(booking_query)
        booking_time = booking_result.scalar()
        
        if not booking_time:
            return 0.0
        
        # Calculate how quickly it was booked as percentage of total available time
        total_available_time = (event_start_time - event_created_at).total_seconds()
        booking_delay = (booking_time - event_created_at).total_seconds()
        
        if total_available_time <= 0:
            return 100.0  # Edge case: event in the past
        
        # Lower delay = higher score
        speed_ratio = 1.0 - (booking_delay / total_available_time)
        return max(0.0, min(100.0, speed_ratio * 100))
    
    @staticmethod
    async def _calculate_group_booking_score(
        db: AsyncSession, 
        seat: Seat, 
        event_id: UUID
    ) -> float:
        """Calculate if this seat was part of a larger group booking (0-100)"""
        
        if seat.status != SeatStatus.BOOKED:
            return 0.0
        
        # Find the booking this seat belongs to
        booking_query = (
            select(Booking.id)
            .join(Ticket, Ticket.booking_id == Booking.id)
            .where(
                and_(
                    Ticket.seat_id == seat.id,
                    Booking.status == BookingStatus.CONFIRMED
                )
            )
        )
        
        booking_result = await db.execute(booking_query)
        booking_id = booking_result.scalar()
        
        if not booking_id:
            return 0.0
        
        # Count tickets in this booking
        ticket_count_query = (
            select(func.count(Ticket.id))
            .where(Ticket.booking_id == booking_id)
        )
        
        ticket_count_result = await db.execute(ticket_count_query)
        ticket_count = ticket_count_result.scalar() or 0
        
        # Score based on group size (logarithmic scale)
        if ticket_count <= 1:
            return 0.0
        elif ticket_count <= 2:
            return 25.0
        elif ticket_count <= 4:
            return 50.0
        elif ticket_count <= 8:
            return 75.0
        else:
            return 100.0
    
    @staticmethod
    async def _calculate_popularity_score(
        booking_speed_score: float,
        group_booking_score: float
    ) -> float:
        """Calculate overall popularity score (0-100)"""
        # Weighted combination: 70% speed, 30% group booking
        popularity = (booking_speed_score * 0.7) + (group_booking_score * 0.3)
        return round(popularity, 1)
    
    @staticmethod
    def _calculate_heat_intensity(
        booking_speed_score: float,
        group_booking_score: float, 
        popularity_score: float
    ) -> float:
        """Calculate visual heat intensity for the seat (0-100)"""
        # Use popularity score as primary heat indicator
        # Add slight boost for group bookings to make them stand out
        heat = popularity_score
        if group_booking_score > 0:
            heat = min(100.0, heat + (group_booking_score * 0.1))
        
        return round(heat, 1)
    
    @staticmethod
    async def _upsert_seat_analytics(
        db: AsyncSession,
        event_id: UUID,
        seat_id: UUID,
        booking_speed_score: float,
        group_booking_score: float,
        popularity_score: float
    ) -> None:
        """Insert or update seat analytics record"""
        
        # Check if record exists
        existing_query = select(SeatAnalytics).where(
            and_(
                SeatAnalytics.event_id == event_id,
                SeatAnalytics.seat_id == seat_id
            )
        )
        
        existing_result = await db.execute(existing_query)
        existing_analytics = existing_result.scalar_one_or_none()
        
        if existing_analytics:
            # Update existing record
            existing_analytics.booking_speed_score = booking_speed_score
            existing_analytics.group_booking_score = group_booking_score
            existing_analytics.popularity_score = popularity_score
            existing_analytics.last_updated = datetime.utcnow()
        else:
            # Create new record
            new_analytics = SeatAnalytics(
                event_id=event_id,
                seat_id=seat_id,
                booking_speed_score=booking_speed_score,
                group_booking_score=group_booking_score,
                popularity_score=popularity_score
            )
            db.add(new_analytics)
        
        # Note: Don't commit here - let the caller handle transaction
    
    @staticmethod
    async def invalidate_heatmap_cache(event_id: UUID) -> bool:
        """Invalidate heatmap cache for an event"""
        cache_key = VenueHeatmapService.get_heatmap_cache_key(event_id)
        return CacheService.delete(cache_key)
    
    @staticmethod
    async def get_top_hottest_seats(
        db: AsyncSession, 
        event_id: UUID, 
        limit: int = 10
    ) -> List[SeatHeatmapData]:
        """Get the hottest seats for an event"""
        
        heatmap = await VenueHeatmapService.generate_venue_heatmap(db, event_id)
        if not heatmap:
            return []
        
        # Sort by heat intensity and return top N
        sorted_seats = sorted(
            heatmap.seats_data, 
            key=lambda x: x.heat_intensity, 
            reverse=True
        )
        
        return sorted_seats[:limit]

