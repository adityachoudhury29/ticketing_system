#!/usr/bin/env python3
"""
Script to create an admin user for the Evently platform.
Run this after setting up the database.
"""

import asyncio
import sys
from app.db.session import AsyncSessionLocal
from app.crud.user import create_user
from app.models.models import UserRole


async def create_admin_user():
    """Create an admin user"""
    async with AsyncSessionLocal() as db:
        try:
            admin_user = await create_user(
                db=db,
                email="admin@evently.com",
                password="admin123",  # Change this in production!
                role=UserRole.ADMIN
            )
            print(f"Admin user created successfully!")
            print(f"Email: {admin_user.email}")
            print(f"ID: {admin_user.id}")
            print(f"Role: {admin_user.role.value}")
            
        except Exception as e:
            print(f"Error creating admin user: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_admin_user())
