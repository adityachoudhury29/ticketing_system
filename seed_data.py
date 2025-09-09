#!/usr/bin/env python3
"""
Script to seed the database with sample events for testing.
"""

import asyncio
from datetime import datetime, timedelta
from app.db.session import AsyncSessionLocal
from app.services.booking import EventService
from app.crud.user import get_user_by_email


async def seed_sample_events():
    """Create sample events for testing"""
    async with AsyncSessionLocal() as db:
        try:
            # Get admin user (assumes admin user exists)
            admin_user = await get_user_by_email(db, "admin@evently.com")
            if not admin_user:
                print("Admin user not found. Please create an admin user first.")
                return

            # Sample events
            events_data = [
                {
                    "name": "Tech Conference 2025",
                    "venue": "Convention Center",
                    "description": "Annual technology conference featuring the latest innovations",
                    "start_time": datetime.now() + timedelta(days=30),
                    "end_time": datetime.now() + timedelta(days=30, hours=8),
                    "total_capacity": 500
                },
                {
                    "name": "Rock Concert",
                    "venue": "City Arena",
                    "description": "Amazing rock concert with popular bands",
                    "start_time": datetime.now() + timedelta(days=45),
                    "end_time": datetime.now() + timedelta(days=45, hours=4),
                    "total_capacity": 1000
                },
                {
                    "name": "Comedy Show",
                    "venue": "Downtown Theater",
                    "description": "Stand-up comedy night with famous comedians",
                    "start_time": datetime.now() + timedelta(days=15),
                    "end_time": datetime.now() + timedelta(days=15, hours=2),
                    "total_capacity": 200
                },
                {
                    "name": "Food Festival",
                    "venue": "Central Park",
                    "description": "Outdoor food festival with local restaurants",
                    "start_time": datetime.now() + timedelta(days=60),
                    "end_time": datetime.now() + timedelta(days=62),
                    "total_capacity": 2000
                }
            ]

            created_events = []
            for event_data in events_data:
                event = await EventService.create_event_with_seats(
                    db=db,
                    name=event_data["name"],
                    venue=event_data["venue"],
                    description=event_data["description"],
                    start_time=event_data["start_time"],
                    end_time=event_data["end_time"],
                    total_capacity=event_data["total_capacity"],
                    created_by=admin_user.id
                )
                created_events.append(event)
                print(f"Created event: {event.name} (ID: {event.id})")

            print(f"\nSuccessfully created {len(created_events)} sample events!")
            
        except Exception as e:
            print(f"Error creating sample events: {e}")


if __name__ == "__main__":
    asyncio.run(seed_sample_events())
