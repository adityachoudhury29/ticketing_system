from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, Any
import time
import re
from functools import wraps
from ..services.cache import CacheService, REDIS_AVAILABLE
from ..core.exceptions import EventlyBaseException


class RateLimitExceeded(EventlyBaseException):
    """Raised when rate limit is exceeded"""
    pass


class RateLimiter:
    """Rate limiter using sliding window algorithm"""
    
    def __init__(self, calls: int, period: int, per: str = "minute"):
        """
        Initialize rate limiter
        
        Args:
            calls: Number of allowed calls
            period: Time period 
            per: Time unit ('second', 'minute', 'hour')
        """
        self.calls = calls
        self.period = period
        
        # Convert to seconds
        multipliers = {"second": 1, "minute": 60, "hour": 3600}
        self.period_seconds = period * multipliers.get(per, 60)
    
    def _get_key(self, identifier: str) -> str:
        """Generate cache key for rate limiting"""
        return f"rate_limit:{identifier}"
    
    def _get_window_start(self) -> int:
        """Get current time window start"""
        now = int(time.time())
        return (now // self.period_seconds) * self.period_seconds
    
    async def is_allowed(self, identifier: str) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit
        
        Returns:
            (is_allowed, info_dict)
        """
        if not REDIS_AVAILABLE:
            # If Redis is not available, allow all requests
            return True, {"remaining": self.calls, "reset_time": 0}
        
        try:
            key = self._get_key(identifier)
            current_time = int(time.time())
            window_start = self._get_window_start()
            
            # Get current count from cache with proper error handling
            try:
                current_count = CacheService.get(key)
                if current_count is None:
                    current_count = 0
                else:
                    current_count = int(current_count)
            except Exception:
                current_count = 0
            
            # Check if we're in a new window
            if current_count == 0:
                # New window, start counting
                try:
                    CacheService.set(key, 1, expire=self.period_seconds)
                except Exception:
                    pass  # If cache fails, allow request
                return True, {
                    "remaining": self.calls - 1,
                    "reset_time": window_start + self.period_seconds
                }
            
            if current_count >= self.calls:
                # Rate limit exceeded
                return False, {
                    "remaining": 0,
                    "reset_time": window_start + self.period_seconds
                }
            
            # Increment counter
            try:
                CacheService.set(key, current_count + 1, expire=self.period_seconds)
            except Exception:
                pass  # If cache fails, allow request
            
            return True, {
                "remaining": self.calls - (current_count + 1),
                "reset_time": window_start + self.period_seconds
            }
            
        except Exception as e:
            # If rate limiting fails, allow the request
            print(f"Rate limiting error: {e}")
            return True, {"remaining": self.calls, "reset_time": 0}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for applying rate limits"""
    
    def __init__(self, app):
        super().__init__(app)
        # Define different rate limits for different endpoints
        self.limits = {
            # Authentication endpoints - stricter limits
            r"^/auth/login/?$": RateLimiter(calls=5, period=1, per="minute"),
            r"^/auth/register/?$": RateLimiter(calls=3, period=1, per="minute"),
            
            # Booking endpoints - moderate limits
            r"^/bookings/?$": RateLimiter(calls=10, period=1, per="minute"),
            r"^/bookings/.*": RateLimiter(calls=20, period=1, per="minute"),
            
            # Public endpoints - more lenient
            r"^/events/?$": RateLimiter(calls=100, period=1, per="minute"),
            r"^/events/.*": RateLimiter(calls=50, period=1, per="minute"),
            
            # Admin endpoints - moderate limits
            r"^/admin/.*": RateLimiter(calls=30, period=1, per="minute"),
        }
        
        # Default rate limit for unspecified endpoints
        self.default_limit = RateLimiter(calls=60, period=1, per="minute")
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get user ID from authentication
        # For now, use IP address as fallback
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Use first IP in case of multiple proxies
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return client_ip
    
    def _get_rate_limiter(self, path: str) -> RateLimiter:
        """Get appropriate rate limiter for the path"""
        for pattern, limiter in self.limits.items():
            if re.match(pattern, path):
                return limiter
        
        return self.default_limit
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to request"""
        try:
            path = request.url.path
            client_id = self._get_client_identifier(request)
            rate_limiter = self._get_rate_limiter(path)
            
            # Check rate limit
            is_allowed, info = await rate_limiter.is_allowed(f"{path}:{client_id}")
            
            if not is_allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "message": "Rate limit exceeded",
                        "reset_time": info["reset_time"]
                    },
                    headers={
                        "X-RateLimit-Limit": str(rate_limiter.calls),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset_time"])
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            response.headers["X-RateLimit-Limit"] = str(rate_limiter.calls)
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset_time"])
            
            return response
            
        except Exception as e:
            # If rate limiting fails, continue with request
            print(f"Rate limiting middleware error: {e}")
            return await call_next(request)


# Decorator for function-level rate limiting
def rate_limit(calls: int, period: int, per: str = "minute"):
    """
    Decorator to apply rate limiting to specific functions
    
    Usage:
        @rate_limit(calls=10, period=1, per="minute")
        async def some_endpoint():
            pass
    """
    def decorator(func: Callable) -> Callable:
        limiter = RateLimiter(calls, period, per)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # If no request found, proceed without rate limiting
                return await func(*args, **kwargs)
            
            client_id = request.client.host if request.client else "unknown"
            key = f"{func.__name__}:{client_id}"
            
            is_allowed, info = await limiter.is_allowed(key)
            
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": f"Rate limit exceeded for {func.__name__}",
                        "reset_time": info["reset_time"]
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# IP-based rate limiting for specific security scenarios
class IPRateLimiter:
    """Simple IP-based rate limiter for security purposes"""
    
    def __init__(self):
        self.attempts = {}  # In-memory storage for simplicity
        self.max_attempts = 10
        self.window_size = 300  # 5 minutes
    
    def is_ip_allowed(self, ip: str) -> bool:
        """Check if IP is allowed based on recent attempts"""
        now = time.time()
        
        if ip not in self.attempts:
            self.attempts[ip] = []
        
        # Clean old attempts
        self.attempts[ip] = [
            attempt_time for attempt_time in self.attempts[ip]
            if now - attempt_time < self.window_size
        ]
        
        # Check if under limit
        if len(self.attempts[ip]) >= self.max_attempts:
            return False
        
        # Record this attempt
        self.attempts[ip].append(now)
        return True
    
    def clear_ip(self, ip: str):
        """Clear attempts for an IP (e.g., after successful auth)"""
        if ip in self.attempts:
            del self.attempts[ip]


# Global IP rate limiter instance
ip_rate_limiter = IPRateLimiter()
