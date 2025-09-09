# Evently - Event Ticketing Platform Backend

A complete, production-ready, and scalable backend for an event ticketing platform with seat-level booking and concurrency control.

## 🚀 Features

- **Seat-Level Booking**: Users can select and book specific seats
- **Concurrency Control**: Pessimistic locking prevents overselling
- **High Performance**: Redis caching for read-heavy operations
- **Async Processing**: Celery workers for background tasks
- **Scalable Architecture**: Microservices-ready design
- **Production Ready**: Docker containerization with PostgreSQL

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   PostgreSQL    │    │     Redis       │
│                 │◄──►│                 │    │                 │
│  • REST APIs    │    │  • Event Data   │    │  • Caching      │
│  • Auth         │    │  • Bookings     │    │  • Sessions     │
│  • Validation   │    │  • Users        │    │  • Task Queue   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              ▲
         ▼                                              │
┌─────────────────┐                              ┌─────────────────┐
│ Celery Workers  │                              │   Load Balancer │
│                 │                              │                 │
│ • Notifications │                              │  (Nginx/HAProxy)│
│ • Analytics     │                              │                 │
│ • Cleanup       │                              └─────────────────┘
└─────────────────┘
```

## 🛠️ Technology Stack

- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with AsyncPG
- **ORM**: SQLAlchemy (Async)
- **Caching**: Redis
- **Task Queue**: Celery
- **Validation**: Pydantic
- **Authentication**: JWT tokens
- **Containerization**: Docker & Docker Compose

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)
- Git

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd evently-backend
cp .env.example .env  # Edit with your settings
```

### 2. Run with Docker

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f fastapi-app
```

### 3. Access the Application

- **API Documentation**: http://localhost:8000/docs
- **API Base URL**: http://localhost:8000
- **Flower (Celery Monitor)**: http://localhost:5555
- **Health Check**: http://localhost:8000/health

## 📚 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login

### Events (Public)
- `GET /events/` - List upcoming events (cached)
- `GET /events/{event_id}` - Get event details
- `GET /events/{event_id}/seats` - Get seat map

### Bookings (Authenticated)
- `POST /bookings/` - Create booking with seat selection
- `GET /bookings/my-bookings` - User's booking history
- `POST /bookings/{booking_id}/cancel` - Cancel booking

### Waitlist (Authenticated)
- `POST /waitlist/join` - Join event waitlist
- `GET /waitlist/my-entries` - User's waitlist entries

### Admin (Admin Only)
- `POST /admin/events` - Create event
- `PUT /admin/events/{event_id}` - Update event
- `DELETE /admin/events/{event_id}` - Delete event
- `GET /admin/analytics/summary` - Analytics dashboard

## 🔒 Concurrency Control

The system implements **pessimistic locking** for seat booking:

1. **Transaction Start**: Begin database transaction
2. **Seat Locking**: `SELECT ... FOR UPDATE` on specific seats
3. **Validation**: Check if seats are available
4. **Booking Creation**: Create booking and tickets
5. **Commit**: Release locks and confirm booking

This prevents overselling even under high concurrency.

## 📊 Caching Strategy

**Cache-Aside Pattern** with Redis:
- **Events List**: 30 minutes TTL
- **Event Details**: 1 hour TTL  
- **Seat Maps**: 5 minutes TTL (frequent updates)

Cache invalidation occurs on:
- Event modifications
- Seat status changes
- Booking creations/cancellations

## 🔄 Background Tasks

Celery handles async operations:
- **Waitlist Notifications**: When seats become available
- **Analytics Generation**: Daily/weekly reports
- **Cleanup Tasks**: Remove expired bookings

## 🗄️ Database Schema

```sql
-- Core entities with relationships
Users (id, email, role, created_at)
Events (id, name, venue, start_time, total_capacity)
Seats (id, event_id, seat_identifier, status)
Bookings (id, user_id, event_id, status, created_at)
Tickets (id, booking_id, seat_id, qr_code_data)
WaitlistEntries (id, user_id, event_id, joined_at)
```

## 🧪 Testing

```bash
# Run tests (when implemented)
docker-compose exec fastapi-app pytest

# Load testing with hey or wrk
hey -n 1000 -c 50 http://localhost:8000/events/
```

## 📈 Monitoring & Observability

- **Application Logs**: Structured JSON logging
- **Health Checks**: `/health` endpoint
- **Celery Monitoring**: Flower dashboard
- **Database Metrics**: PostgreSQL built-in stats

## 🚀 Production Deployment

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Redis
REDIS_URL=redis://host:6379/0

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Celery
CELERY_BROKER_URL=redis://host:6379/0
```

### Scaling Considerations

1. **Horizontal Scaling**: Multiple FastAPI instances behind load balancer
2. **Database**: Read replicas for analytics
3. **Cache**: Redis Cluster for high availability
4. **Workers**: Scale Celery workers based on queue length

### Security Best Practices

- Use strong SECRET_KEY in production
- Enable HTTPS/TLS
- Configure CORS appropriately
- Implement rate limiting
- Use environment-specific .env files

## 🤝 Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv myenv
source myenv/bin/activate  # or myenv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run locally (requires Redis and PostgreSQL)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Code Structure

```
app/
├── api/          # API route handlers
├── core/         # Core functionality (config, security)
├── crud/         # Database operations
├── models/       # SQLAlchemy models
├── schemas/      # Pydantic schemas
├── services/     # Business logic
├── worker/       # Celery tasks
└── main.py       # FastAPI application
```

## 📝 License

[Your License Here]

## 🆘 Support

For issues and questions:
1. Check the [API Documentation](http://localhost:8000/docs)
2. Review application logs: `docker-compose logs -f`
3. Open an issue in the repository
