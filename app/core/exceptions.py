from fastapi import HTTPException, status
from typing import Optional, Dict, Any


class EventlyBaseException(Exception):
    """Base exception for Evently application"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(EventlyBaseException):
    """Raised when validation fails"""
    pass


class NotFoundError(EventlyBaseException):
    """Raised when a resource is not found"""
    pass


class ConflictError(EventlyBaseException):
    """Raised when there's a conflict (e.g., duplicate resource)"""
    pass


class UnauthorizedError(EventlyBaseException):
    """Raised when user is not authorized"""
    pass


class ForbiddenError(EventlyBaseException):
    """Raised when user doesn't have permission"""
    pass


class BookingError(EventlyBaseException):
    """Raised when booking operations fail"""
    pass


class SeatUnavailableError(BookingError):
    """Raised when requested seats are not available"""
    pass


class EventCapacityError(BookingError):
    """Raised when event is at full capacity"""
    pass


class PaymentError(EventlyBaseException):
    """Raised when payment processing fails"""
    pass


class CacheError(EventlyBaseException):
    """Raised when cache operations fail"""
    pass


# HTTP Exception converters
def to_http_exception(exc: EventlyBaseException) -> HTTPException:
    """Convert custom exceptions to HTTP exceptions"""
    
    if isinstance(exc, ValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "details": exc.details}
        )
    
    elif isinstance(exc, NotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": exc.message, "details": exc.details}
        )
    
    elif isinstance(exc, ConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": exc.message, "details": exc.details}
        )
    
    elif isinstance(exc, UnauthorizedError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": exc.message, "details": exc.details},
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    elif isinstance(exc, ForbiddenError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": exc.message, "details": exc.details}
        )
    
    elif isinstance(exc, (SeatUnavailableError, EventCapacityError)):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": exc.message, "details": exc.details}
        )
    
    elif isinstance(exc, BookingError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "details": exc.details}
        )
    
    elif isinstance(exc, PaymentError):
        return HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"message": exc.message, "details": exc.details}
        )
    
    else:
        # Generic server error for unknown exceptions
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "An internal server error occurred", "details": {}}
        )


# Common error messages
class ErrorMessages:
    # User errors
    USER_NOT_FOUND = "User not found"
    USER_ALREADY_EXISTS = "User with this email already exists"
    INVALID_CREDENTIALS = "Invalid email or password"
    INSUFFICIENT_PERMISSIONS = "Insufficient permissions to perform this action"
    
    # Event errors
    EVENT_NOT_FOUND = "Event not found"
    EVENT_FULL = "Event is at full capacity"
    EVENT_EXPIRED = "Event has already ended"
    EVENT_NOT_STARTED = "Event has not started yet"
    
    # Seat errors
    SEAT_NOT_FOUND = "Seat not found"
    SEAT_UNAVAILABLE = "One or more seats are no longer available"
    SEAT_ALREADY_BOOKED = "Seat is already booked"
    INVALID_SEAT_SELECTION = "Invalid seat selection"
    
    # Booking errors
    BOOKING_NOT_FOUND = "Booking not found"
    BOOKING_ALREADY_CANCELLED = "Booking is already cancelled"
    BOOKING_CANNOT_CANCEL = "Booking cannot be cancelled"
    BOOKING_LIMIT_EXCEEDED = "Maximum booking limit exceeded"
    
    # Waitlist errors
    ALREADY_ON_WAITLIST = "User is already on the waitlist for this event"
    WAITLIST_FULL = "Waitlist is full for this event"
    NOT_ON_WAITLIST = "User is not on the waitlist for this event"
    
    # Payment errors
    PAYMENT_FAILED = "Payment processing failed"
    PAYMENT_CANCELLED = "Payment was cancelled"
    PAYMENT_ALREADY_PROCESSED = "Payment has already been processed"
    INVALID_PAYMENT_METHOD = "Invalid payment method"
    
    # System errors
    CACHE_ERROR = "Cache operation failed"
    DATABASE_ERROR = "Database operation failed"
    EXTERNAL_SERVICE_ERROR = "External service is temporarily unavailable"
    RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Please try again later"
