"""Common Pydantic schemas used across the API."""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    
    model_config = ConfigDict(extra="forbid")
    
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(default=50, ge=1, le=200, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    
    model_config = ConfigDict(extra="forbid")
    
    items: list[T] = Field(..., description="List of items for current page")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")


class TimestampMixin(BaseModel):
    """Mixin for created_at and updated_at timestamps."""
    
    created_at: datetime
    updated_at: datetime


class UUIDMixin(BaseModel):
    """Mixin for UUID primary key."""
    
    id: UUID


class MessageResponse(BaseModel):
    """Simple message response."""
    
    model_config = ConfigDict(extra="forbid")
    
    message: str


class HealthResponse(BaseModel):
    """Health check response."""
    
    model_config = ConfigDict(extra="forbid")
    
    status: str = Field(..., description="Health status")
    environment: str = Field(..., description="Deployment environment")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
