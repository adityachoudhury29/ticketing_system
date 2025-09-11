import time
import psutil
from typing import Dict, Any, List
from datetime import datetime, timedelta
from fastapi import Request
from ..db.session import AsyncSessionLocal


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics = {}
        self.request_times = []
        self.max_request_history = 1000
        
    def record_request_time(self, endpoint: str, duration: float):
        """Record request processing time"""
        now = datetime.now()
        self.request_times.append({
            "endpoint": endpoint,
            "duration": duration,
            "timestamp": now
        })
        
        # Keep only recent requests
        if len(self.request_times) > self.max_request_history:
            self.request_times = self.request_times[-self.max_request_history:]
    
    def get_average_response_time(self, minutes: int = 5) -> Dict[str, float]:
        """Get average response time for the last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        recent_requests = [
            req for req in self.request_times 
            if req["timestamp"] > cutoff
        ]
        
        if not recent_requests:
            return {}
        
        # Group by endpoint
        endpoint_times = {}
        for req in recent_requests:
            endpoint = req["endpoint"]
            if endpoint not in endpoint_times:
                endpoint_times[endpoint] = []
            endpoint_times[endpoint].append(req["duration"])
        
        # Calculate averages
        averages = {}
        for endpoint, times in endpoint_times.items():
            averages[endpoint] = sum(times) / len(times)
        
        return averages
    
    def get_slow_requests(self, threshold: float = 1.0, minutes: int = 5) -> List[Dict]:
        """Get requests that took longer than threshold"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [
            req for req in self.request_times
            if req["timestamp"] > cutoff and req["duration"] > threshold
        ]
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}


class DatabaseMonitor:
    """Database performance monitoring"""
    
    @staticmethod
    async def get_database_stats() -> Dict[str, Any]:
        """Get database connection and performance statistics"""
        try:
            async with AsyncSessionLocal() as db:
                # Simple health check query
                start_time = time.time()
                from sqlalchemy import text
                await db.execute(text("SELECT 1"))
                query_time = time.time() - start_time
                
                return {
                    "connection_successful": True,
                    "query_time_ms": query_time * 1000,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "connection_successful": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    async def get_table_sizes() -> Dict[str, Any]:
        """Get approximate table sizes (SQLite specific)"""
        try:
            async with AsyncSessionLocal() as db:
                # SQLite specific queries
                tables = ["users", "events", "seats", "bookings", "tickets", "waitlist_entries"]
                sizes = {}
                
                for table in tables:
                    try:
                        from sqlalchemy import text
                        result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        sizes[table] = count
                    except Exception:
                        sizes[table] = "error"
                
                return {
                    "table_sizes": sizes,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


class CacheMonitor:
    """Cache performance monitoring"""
    
    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """Get cache performance statistics"""
        try:
            from ..services.cache import redis_client, REDIS_AVAILABLE
            
            if not REDIS_AVAILABLE:
                return {
                    "available": False,
                    "message": "Redis not available"
                }
            
            info = redis_client.info()
            
            return {
                "available": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "used_memory_percent": (
                    info.get("used_memory", 0) / 
                    max(info.get("maxmemory", 1), 1) * 100
                    if info.get("maxmemory", 0) > 0 else 0
                ),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0) / 
                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                ),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


class PerformanceMiddleware:
    """Middleware to track request performance"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
    
    async def __call__(self, request: Request, call_next):
        """Track request performance"""
        start_time = time.time()
        
        # Add request ID for tracing
        request.state.request_id = f"req_{int(time.time() * 1000)}_{id(request)}"
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Record metrics
        endpoint = f"{request.method} {request.url.path}"
        self.monitor.record_request_time(endpoint, process_time)
        
        # Add performance headers
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request.state.request_id
        
        return response


# Global monitor instances
performance_monitor = PerformanceMonitor()
performance_middleware = PerformanceMiddleware(performance_monitor)


class HealthChecker:
    """Comprehensive health checking"""
    
    @staticmethod
    async def get_comprehensive_health() -> Dict[str, Any]:
        """Get comprehensive health status"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # Database health
        try:
            db_stats = await DatabaseMonitor.get_database_stats()
            health_status["checks"]["database"] = {
                "status": "healthy" if db_stats.get("connection_successful") else "unhealthy",
                "details": db_stats
            }
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Cache health
        try:
            cache_stats = CacheMonitor.get_cache_stats()
            health_status["checks"]["cache"] = {
                "status": "healthy" if cache_stats.get("available") else "degraded",
                "details": cache_stats
            }
        except Exception as e:
            health_status["checks"]["cache"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # System health
        try:
            system_stats = performance_monitor.get_system_metrics()
            cpu_healthy = system_stats.get("cpu_percent", 0) < 90
            memory_healthy = system_stats.get("memory_percent", 0) < 90
            disk_healthy = system_stats.get("disk_percent", 0) < 90
            
            health_status["checks"]["system"] = {
                "status": "healthy" if all([cpu_healthy, memory_healthy, disk_healthy]) else "degraded",
                "details": system_stats
            }
        except Exception as e:
            health_status["checks"]["system"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Overall status
        check_statuses = [check["status"] for check in health_status["checks"].values()]
        if "unhealthy" in check_statuses:
            health_status["status"] = "unhealthy"
        elif "degraded" in check_statuses:
            health_status["status"] = "degraded"
        
        return health_status
