from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from uuid import UUID


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
    
    id: UUID
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
    base_price: float = 50.0


class EventUpdate(BaseModel):
    name: Optional[str] = None
    venue: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_capacity: Optional[int] = None
    base_price: Optional[float] = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    venue: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    total_capacity: int
    base_price: float
    created_at: datetime


class EventWithPricingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    venue: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    total_capacity: int
    base_price: float
    current_price: float
    price_multiplier: float
    days_until_event: int
    created_at: datetime


# Seat schemas
class SeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    seat_identifier: str
    status: SeatStatus


class SeatMapResponse(BaseModel):
    event_id: UUID
    seats: List[SeatResponse]


# Booking schemas
class BookingCreate(BaseModel):
    event_id: UUID
    seat_identifiers: List[str]


# Ticket schemas
class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    seat_id: UUID
    qr_code_data: str


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    event_id: UUID
    status: BookingStatus
    
    # Pricing information
    base_price_per_ticket: float
    final_price_per_ticket: float
    price_multiplier: float
    total_amount: float
    
    created_at: datetime
    tickets: List[TicketResponse]


# Waitlist schemas
class WaitlistJoin(BaseModel):
    event_id: UUID


class WaitlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    event_id: UUID
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
    event_id: UUID
    event_name: str
    booking_count: int


class DailyTrend(BaseModel):
    date: str
    bookings: int
    revenue: float


class PricingAnalytics(BaseModel):
    total_bookings_with_surge: int
    total_bookings_at_base_price: int
    average_price_multiplier: float
    total_surge_revenue: float  # Extra revenue from dynamic pricing
    base_price_revenue: float   # What revenue would have been at base prices
    actual_revenue: float       # Actual revenue with dynamic pricing
    surge_percentage: float     # Percentage of bookings that had surge pricing


# Venue Heatmap schemas
class SeatHeatmapData(BaseModel):
    seat_id: UUID
    seat_identifier: str
    booking_speed_score: float
    group_booking_score: float
    popularity_score: float
    heat_intensity: float  # Calculated overall heat (0-100)


class VenueHeatmapResponse(BaseModel):
    event_id: UUID
    event_name: str
    total_seats: int
    booked_seats: int
    capacity_percentage: float
    seats_data: List[SeatHeatmapData]
    last_updated: datetime


# Dynamic Pricing schemas
class PricingTier(BaseModel):
    start_date: str
    days_before_event: int
    price_multiplier: float
    price: float
    percentage_increase: float


class EventPricingResponse(BaseModel):
    event_id: UUID
    event_name: str
    event_start_time: str
    base_price: float
    current_price: float
    days_until_event: int
    current_multiplier: float
    pricing_timeline: List[PricingTier]


class BookingCostEstimate(BaseModel):
    base_price_per_ticket: float
    current_price_per_ticket: float
    number_of_tickets: int
    total_cost: float
    days_until_event: int
    price_multiplier: float
    savings_if_base_price: float


class BookingCreateWithPricing(BaseModel):
    event_id: UUID
    seat_identifiers: List[str]
    # Optional field to acknowledge the current price
    acknowledged_price_per_ticket: Optional[float] = None
