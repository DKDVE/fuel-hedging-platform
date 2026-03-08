"""User repository for authentication and user management."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User instance or None if not found
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_active_users(self) -> list[User]:
        """Get all active users.
        
        Returns:
            List of active users
        """
        result = await self.db.execute(
            select(User).where(User.is_active == True).order_by(User.email)
        )
        return list(result.scalars().all())

    async def get_by_role(self, role: UserRole) -> list[User]:
        """Get all users with a specific role.
        
        Args:
            role: User role to filter by
            
        Returns:
            List of users with the specified role
        """
        result = await self.db.execute(
            select(User)
            .where(User.role == role)
            .where(User.is_active == True)
            .order_by(User.email)
        )
        return list(result.scalars().all())

    async def update_last_login(self, user_id: uuid.UUID, login_time: datetime) -> None:
        """Update user's last login timestamp.
        
        Args:
            user_id: User UUID
            login_time: Login timestamp
        """
        user = await self.get_by_id(user_id)
        if user:
            user.last_login = login_time
            await self.db.flush()

    async def deactivate_user(self, user_id: uuid.UUID) -> bool:
        """Deactivate a user account.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if deactivated, False if user not found
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return False
        user.is_active = False
        await self.db.flush()
        return True

    async def activate_user(self, user_id: uuid.UUID) -> bool:
        """Activate a user account.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if activated, False if user not found
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return False
        user.is_active = True
        await self.db.flush()
        return True
