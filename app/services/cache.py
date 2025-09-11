import redis
import json
from typing import Optional, Any
from uuid import UUID
from ..core.config import settings

# Redis client with error handling
try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    # Test connection
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    redis_client = None
    REDIS_AVAILABLE = False
    print("⚠️  Redis not available - caching disabled")


class CacheService:
    """Service for caching operations using Redis"""
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """Get value from cache"""
        if not REDIS_AVAILABLE:
            return None
        try:
            value = redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None
    
    @staticmethod
    def set(key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache with expiration"""
        if not REDIS_AVAILABLE:
            return False
        try:
            redis_client.setex(key, expire, json.dumps(value, default=str))
            return True
        except Exception:
            return False
    
    @staticmethod
    def delete(key: str) -> bool:
        """Delete key from cache"""
        if not REDIS_AVAILABLE:
            return False
        try:
            redis_client.delete(key)
            return True
        except Exception:
            return False
    
    @staticmethod
    def delete_pattern(pattern: str) -> bool:
        """Delete all keys matching pattern"""
        if not REDIS_AVAILABLE:
            return False
        try:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
            return True
        except Exception:
            return False


# Cache key generators
def get_events_cache_key(skip: int = 0, limit: int = 100) -> str:
    return f"events:list:{skip}:{limit}"


def get_event_cache_key(event_id: UUID) -> str:
    return f"event:{event_id}"


def get_event_seats_cache_key(event_id: UUID) -> str:
    return f"event:{event_id}:seats"
