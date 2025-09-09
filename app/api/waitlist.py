from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..db.session import get_db
from ..schemas.schemas import WaitlistJoin, WaitlistResponse
from ..crud.waitlist import join_waitlist, get_user_waitlist_entries
from ..core.deps import get_current_user
from ..models.models import User

router = APIRouter()


@router.post("/join", response_model=WaitlistResponse)
async def join_event_waitlist(
    waitlist_data: WaitlistJoin,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Join the waitlist for a full event"""
    try:
        waitlist_entry = await join_waitlist(
            db=db,
            user_id=current_user.id,
            event_id=waitlist_data.event_id
        )
        
        return WaitlistResponse.model_validate(waitlist_entry)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while joining the waitlist. Please try again."
        )


@router.get("/my-entries", response_model=List[WaitlistResponse])
async def get_my_waitlist_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the authenticated user's waitlist entries"""
    entries = await get_user_waitlist_entries(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    
    return [WaitlistResponse.model_validate(entry) for entry in entries]
