"""Pydantic schemas for authentication and user management.

All schemas use Pydantic v2 with strict validation.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models import UserRole


# Request schemas
class LoginRequest(BaseModel):
    """User login request."""
    
    model_config = ConfigDict(extra="forbid")
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""
    
    model_config = ConfigDict(extra="forbid")
    
    refresh_token: str = Field(..., description="The refresh token")


class CreateUserRequest(BaseModel):
    """Create new user request (admin only)."""
    
    model_config = ConfigDict(extra="forbid")
    
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    password: str = Field(..., min_length=8, description="Initial password")
    role: UserRole = Field(default=UserRole.ANALYST, description="User role")


class UpdateUserRequest(BaseModel):
    """Update user request (admin only)."""
    
    model_config = ConfigDict(extra="forbid")
    
    full_name: str | None = Field(None, min_length=1, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None


class ChangePasswordRequest(BaseModel):
    """Change own password request."""
    
    model_config = ConfigDict(extra="forbid")
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


# Response schemas
class UserResponse(BaseModel):
    """User data response."""
    
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """Token response (for programmatic clients)."""
    
    model_config = ConfigDict(extra="forbid")
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class LoginResponse(BaseModel):
    """Login response with user data.
    
    Includes refresh_token when ENVIRONMENT=production for cross-origin fallback:
    browsers may block third-party cookies (e.g. GitHub Pages → Render API).
    Frontend stores it in memory and sends in body on /auth/refresh when cookie fails.
    """

    model_config = ConfigDict(extra="forbid")

    user: UserResponse
    message: str = Field(default="Login successful")
    refresh_token: str | None = Field(default=None, description="For cross-origin fallback when cookies blocked")
    access_token: str | None = Field(default=None, description="Short-lived JWT when cookies blocked (use Authorization header)")


class MessageResponse(BaseModel):
    """Generic message response."""
    
    model_config = ConfigDict(extra="forbid")
    
    message: str
    detail: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    model_config = ConfigDict(extra="forbid")
    
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    context: dict[str, Any] | None = Field(None, description="Additional error context")
