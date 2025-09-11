from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from ..db.session import get_db
from ..schemas.schemas import BookingCreate, BookingResponse, TicketResponse
from ..crud.booking import get_user_bookings, get_booking_by_id
from ..services.booking import BookingService
from ..core.deps import get_current_user
from ..models.models import User

router = APIRouter()

@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_data: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # BookingService now handles its own transaction
        booking = await BookingService.create_booking(
            db, current_user.id, booking_data.event_id, booking_data.seat_identifiers
        )
        
        # Build response - booking is now committed and relationships are loaded
        response = BookingResponse(
            id=booking.id,
            event_id=booking.event_id,
            status=booking.status,
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
