# Evently - Event Ticketing Platform

A production-ready event ticketing platform backend built with FastAPI, featuring seat-level booking, concurrency control, and real-time notifications.

## Features

- **Seat-Level Booking**: Select and book specific seats for events
- **Concurrency Control**: Prevents overselling with pessimistic locking
- **Background Tasks**: Async processing with Celery workers  
- **Caching**: Redis for high-performance read operations
- **Authentication**: JWT-based user authentication
- **Admin Panel**: Event management and analytics
- **Waitlist**: Join waitlists when events are sold out

## Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL with AsyncPG
- **Cache**: Redis
- **Task Queue**: Celery with Redis broker
- **Authentication**: JWT tokens
- **Containerization**: Docker & Docker Compose

## Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)
- Git

## Quick Start with Docker

1. **Clone the repository**
   ```bash
   git clone https://github.com/adityachoudhury29/ticketing_system
   cd ticketing_system
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**
   ```bash
   sudo docker-compose up -d --build
   ```

4. **Check services status**
   ```bash
   docker-compose ps
   ```

5. **Access the application**
   - API Documentation: http://localhost:8000/docs
   - API Base URL: http://localhost:8000
   - Health Check: http://localhost:8000/health

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login

### Events
- `GET /events/` - List events
- `GET /events/{event_id}` - Get event details
- `GET /events/{event_id}/seats` - Get available seats

### Bookings
- `POST /bookings/` - Create booking
- `GET /bookings/my-bookings` - User's bookings
- `POST /bookings/{booking_id}/cancel` - Cancel booking

### Waitlist
- `POST /waitlist/join` - Join event waitlist
- `GET /waitlist/my-entries` - User's waitlist entries

### Admin
- `POST /admin/events` - Create event
- `PUT /admin/events/{event_id}` - Update event
- `DELETE /admin/events/{event_id}` - Delete event
- `GET /admin/analytics/summary` - Get analytics

## Environment Variables

Copy `.env.example` to `.env` and configure the following:

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - JWT secret key
- `CELERY_BROKER_URL` - Celery broker URL
- `CELERY_RESULT_BACKEND` - Celery result backend
- Email configuration for notifications

## Project Structure

```
app/
├── api/          # API route handlers
├── core/         # Core functionality (config, security, exceptions)
├── crud/         # Database operations
├── models/       # SQLAlchemy models
├── schemas/      # Pydantic schemas for validation
├── services/     # Business logic layer
├── worker/       # Celery tasks and workers
└── main.py       # FastAPI application entry point
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request
