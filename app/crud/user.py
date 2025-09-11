from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from uuid import UUID
from ..models.models import User, UserRole
from ..core.security import get_password_hash, verify_password


async def create_user(db: AsyncSession, email: str, password: str, role: UserRole = UserRole.USER) -> User:
    """Create a new user"""
    hashed_password = get_password_hash(password)
    db_user = User(
        email=email,
        hashed_password=hashed_password,
        role=role
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password"""
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """Get list of users"""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()
