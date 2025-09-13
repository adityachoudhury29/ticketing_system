from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from ..db.session import get_db
from ..schemas.schemas import (
    BookingCreate, BookingCreateWithPricing, BookingResponse, TicketResponse,
    EventPricingResponse, BookingCostEstimate
)
from ..crud.booking import get_user_bookings, get_booking_by_id
from ..services.booking import BookingService
from ..services.pricing import DynamicPricingService
from ..core.deps import get_current_user
from ..models.models import User

router = APIRouter()

@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_data: BookingCreateWithPricing,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # BookingService now handles its own transaction with dynamic pricing
        booking = await BookingService.create_booking(
            db, current_user.id, booking_data.event_id, 
            booking_data.seat_identifiers,
            booking_data.acknowledged_price_per_ticket
        )
        
        # Build response - booking is now committed and relationships are loaded
        response = BookingResponse(
            id=booking.id,
            event_id=booking.event_id,
            status=booking.status,
            base_price_per_ticket=booking.base_price_per_ticket,
            final_price_per_ticket=booking.final_price_per_ticket,
            price_multiplier=booking.price_multiplier,
            total_amount=booking.total_amount,
            created_at=booking.created_at,
            tickets=[
                TicketResponse(
                    id=t.id,
                    seat_id=t.seat_id,
                    qr_code_data=t.qr_code_data
                )
                for t in booking.tickets
            ]
        )
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create booking")

@router.get("/my-bookings", response_model=List[BookingResponse])
async def get_my_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bookings = await get_user_bookings(db, current_user.id, skip=skip, limit=limit)
    return [BookingResponse.model_validate(b) for b in bookings]

@router.delete("/{booking_id}", response_model=BookingResponse, status_code=200)
async def cancel_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a booking (DELETE semantic). Returns the cancelled booking.
    """
    booking = await BookingService.cancel_booking(db, booking_id, current_user.id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return BookingResponse.model_validate(booking)

@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = await get_booking_by_id(db, booking_id)
    if not booking or booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    return BookingResponse.model_validate(booking)


@router.get("/pricing/event/{event_id}", response_model=EventPricingResponse)
async def get_event_pricing(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get pricing timeline for an event"""
    try:
        pricing_info = await DynamicPricingService.get_event_pricing_timeline(db, event_id)
        return EventPricingResponse.model_validate(pricing_info)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/pricing/estimate", response_model=BookingCostEstimate)
async def estimate_booking_cost(
    booking_data: BookingCreate,
    db: AsyncSession = Depends(get_db)
):
    """Estimate the cost of a booking without creating it"""
    try:
        # Get event details
        from ..crud.event import get_event_by_id
        event = await get_event_by_id(db, booking_data.event_id)
        if not event:
            raise ValueError("Event not found")
        
        # Calculate cost
        num_tickets = len(booking_data.seat_identifiers)
        cost_estimate = DynamicPricingService.calculate_total_booking_cost(
            event.base_price, event.start_time, num_tickets
        )
        
        return BookingCostEstimate.model_validate(cost_estimate)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
