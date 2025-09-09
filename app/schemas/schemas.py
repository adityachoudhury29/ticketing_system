from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import List, Optional
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class SeatStatus(str, Enum):
    AVAILABLE = "available"
    LOCKED = "locked"
    BOOKED = "booked"


class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: str
    role: UserRole
    created_at: datetime


# Event schemas
class EventCreate(BaseModel):
    name: str
    venue: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    total_capacity: int


class EventUpdate(BaseModel):
    name: Optional[str] = None
    venue: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_capacity: Optional[int] = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    venue: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    total_capacity: int
    created_at: datetime


# Seat schemas
class SeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    seat_identifier: str
    status: SeatStatus


class SeatMapResponse(BaseModel):
    event_id: int
    seats: List[SeatResponse]


# Booking schemas
class BookingCreate(BaseModel):
    event_id: int
    seat_identifiers: List[str]


# Ticket schemas
class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    seat_id: int
    qr_code_data: str


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    event_id: int
    status: BookingStatus
    created_at: datetime
    tickets: List[TicketResponse]


# Waitlist schemas
class WaitlistJoin(BaseModel):
    event_id: int


class WaitlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    event_id: int
    joined_at: datetime


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# Analytics schemas
class AnalyticsSummary(BaseModel):
    total_events: int
    total_bookings: int
    total_revenue: float
    total_users: int


class PopularEvent(BaseModel):
    event_id: int
    event_name: str
    booking_count: int


class DailyTrend(BaseModel):
    date: str
    bookings: int
    revenue: float
