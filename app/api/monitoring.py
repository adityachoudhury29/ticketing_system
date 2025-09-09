from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from ..db.session import get_db
from ..core.deps import get_current_admin_user
from ..core.monitoring import (
    performance_monitor, DatabaseMonitor, CacheMonitor, HealthChecker
)
from ..models.models import User

router = APIRouter()


@router.get("/health/basic")
async def basic_health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": performance_monitor.get_system_metrics().get("timestamp")
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with all subsystems"""
    return await HealthChecker.get_comprehensive_health()


@router.get("/metrics/performance")
async def get_performance_metrics(
    current_admin: User = Depends(get_current_admin_user)
):
    """Get API performance metrics (admin only)"""
    return {
        "response_times": {
            "average_5min": performance_monitor.get_average_response_time(5),
            "average_15min": performance_monitor.get_average_response_time(15),
            "average_60min": performance_monitor.get_average_response_time(60),
        },
        "slow_requests": performance_monitor.get_slow_requests(threshold=1.0, minutes=15),
        "system_metrics": performance_monitor.get_system_metrics()
    }


@router.get("/metrics/database")
async def get_database_metrics(
    current_admin: User = Depends(get_current_admin_user)
):
    """Get database metrics (admin only)"""
    db_stats = await DatabaseMonitor.get_database_stats()
    table_sizes = await DatabaseMonitor.get_table_sizes()
    
    return {
        "connection_stats": db_stats,
        "table_info": table_sizes
    }


@router.get("/metrics/cache")
async def get_cache_metrics(
    current_admin: User = Depends(get_current_admin_user)
):
    """Get cache metrics (admin only)"""
    return CacheMonitor.get_cache_stats()


@router.get("/metrics/summary")
async def get_metrics_summary(
    current_admin: User = Depends(get_current_admin_user)
):
    """Get summary of all metrics (admin only)"""
    return {
        "performance": {
            "avg_response_time_5min": performance_monitor.get_average_response_time(5),
            "system": performance_monitor.get_system_metrics()
        },
        "database": await DatabaseMonitor.get_database_stats(),
        "cache": CacheMonitor.get_cache_stats(),
        "health": await HealthChecker.get_comprehensive_health()
    }
