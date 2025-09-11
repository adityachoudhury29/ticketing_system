from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey, Enum,
    UniqueConstraint, Index, Float
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
import uuid
from ..db.session import Base


class UserRole(PyEnum):
    USER = "user"
    ADMIN = "admin"


class SeatStatus(PyEnum):
    AVAILABLE = "available"
    LOCKED = "locked"
    BOOKED = "booked"


class BookingStatus(PyEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    bookings = relationship("Booking", back_populates="user")
    waitlist_entries = relationship("WaitlistEntry", back_populates="user")
    created_events = relationship("Event", back_populates="creator")


class Event(Base):
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    venue = Column(String, nullable=False)
    description = Column(Text)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    total_capacity = Column(Integer, nullable=False)
    base_price = Column(Float, nullable=False, default=50.0)  # Base price per seat
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="created_events")
    seats = relationship("Seat", back_populates="event", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="event", cascade="all, delete-orphan")
    waitlist_entries = relationship("WaitlistEntry", back_populates="event", cascade="all, delete-orphan")
    seat_analytics = relationship("SeatAnalytics", back_populates="event", cascade="all, delete-orphan")


class Seat(Base):
    __tablename__ = "seats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    seat_identifier = Column(String, nullable=False)  # e.g., 'A1', 'SEC-B-R5-S12'
    status = Column(Enum(SeatStatus), default=SeatStatus.AVAILABLE, index=True)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('event_id', 'seat_identifier', name='uq_event_seat'),
        Index('ix_seats_event_status', 'event_id', 'status'),
    )
    
    # Relationships
    event = relationship("Event", back_populates="seats")
    tickets = relationship("Ticket", back_populates="seat")


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.CONFIRMED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    event = relationship("Event", back_populates="bookings")
    tickets = relationship("Ticket", back_populates="booking", cascade="all, delete-orphan")


class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    seat_id = Column(UUID(as_uuid=True), ForeignKey("seats.id"), nullable=False)
    qr_code_data = Column(String, nullable=False)
    
    # Relationships
    booking = relationship("Booking", back_populates="tickets")
    seat = relationship("Seat", back_populates="tickets")


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'event_id', name='uq_user_event_waitlist'),
    )
    
    # Relationships
    user = relationship("User", back_populates="waitlist_entries")
    event = relationship("Event", back_populates="waitlist_entries")


class SeatAnalytics(Base):
    __tablename__ = "seat_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    seat_id = Column(UUID(as_uuid=True), ForeignKey("seats.id"), nullable=False)
    
    # Analytics data
    booking_speed_score = Column(Float, default=0.0)  # How fast this seat was booked (0-100)
    group_booking_score = Column(Float, default=0.0)  # Part of larger group bookings (0-100)
    popularity_score = Column(Float, default=0.0)     # Overall popularity metric (0-100)
    
    # Metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('event_id', 'seat_id', name='uq_event_seat_analytics'),
        Index('ix_seat_analytics_event_popularity', 'event_id', 'popularity_score'),
    )
    
    # Relationships
    event = relationship("Event", back_populates="seat_analytics")
    seat = relationship("Seat")
