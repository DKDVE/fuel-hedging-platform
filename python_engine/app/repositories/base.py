"""Base repository class with generic CRUD operations.

All specific repositories inherit from this to get standard operations.
"""

import uuid
from typing import Generic, Optional, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic async repository for database operations.
    
    Provides standard CRUD methods that all specific repositories inherit.
    """

    def __init__(self, model: Type[ModelT], db: AsyncSession) -> None:
        """Initialize repository with model class and database session.
        
        Args:
            model: SQLAlchemy model class
            db: Async database session
        """
        self.model = model
        self.db = db

    async def get_by_id(self, id: uuid.UUID) -> Optional[ModelT]:
        """Get a single record by ID.
        
        Args:
            id: Record UUID
            
        Returns:
            Model instance or None if not found
        """
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, obj: ModelT) -> ModelT:
        """Create a new record.
        
        Args:
            obj: Model instance to create
            
        Returns:
            Created model instance with database-generated fields populated
        """
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelT) -> ModelT:
        """Update an existing record.
        
        Args:
            obj: Model instance with updated fields
            
        Returns:
            Updated model instance
        """
        merged = await self.db.merge(obj)
        await self.db.flush()
        await self.db.refresh(merged)
        return merged

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete a record by ID.
        
        Args:
            id: Record UUID
            
        Returns:
            True if deleted, False if not found
        """
        obj = await self.get_by_id(id)
        if obj is None:
            return False
        await self.db.delete(obj)
        await self.db.flush()
        return True

    async def count(self) -> int:
        """Count total records in table.
        
        Returns:
            Total number of records
        """
        result = await self.db.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def exists(self, id: uuid.UUID) -> bool:
        """Check if a record exists by ID.
        
        Args:
            id: Record UUID
            
        Returns:
            True if exists, False otherwise
        """
        result = await self.db.execute(
            select(self.model.id).where(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None
