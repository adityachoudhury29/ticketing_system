from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager
from .api import auth, events, bookings, waitlist, admin, monitoring
from .db.session import engine
from .models.models import Base
from .core.config import settings
from .core.exceptions import EventlyBaseException, to_http_exception
from .core.rate_limiting import RateLimitMiddleware
from .core.monitoring import performance_middleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting up Evently API...")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Evently API...")
    await engine.dispose()


# Create FastAPI application
app = FastAPI(
    title="Evently API",
    description="A production-ready event ticketing platform with seat-level booking",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Performance monitoring middleware
app.middleware("http")(performance_middleware)


# Enhanced exception handlers
@app.exception_handler(EventlyBaseException)
async def evently_exception_handler(request: Request, exc: EventlyBaseException):
    """Handle custom Evently exceptions"""
    logger.warning(f"Business logic exception: {exc.message} - Details: {exc.details}")
    http_exc = to_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
        headers=getattr(http_exc, 'headers', {})
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "message": "An internal server error occurred",
            "details": {},
            "request_id": getattr(request.state, 'request_id', 'unknown')
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "1.0.0"
    }


# Include API routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
app.include_router(waitlist.router, prefix="/waitlist", tags=["Waitlist"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Evently API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }
