"""Authentication and authorization module.

Handles:
- Password hashing (bcrypt)
- JWT token generation and validation
- User authentication logic
- Token refresh mechanism

All JWT tokens use HS256 algorithm with httpOnly cookies.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt

from app.config import get_settings
from app.core.security import hash_password, verify_password
from app.exceptions import AuthenticationError, AuthorizationError
from app.schemas.auth import UserResponse

settings = get_settings()


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.
    
    Args:
        data: The payload to encode (must include 'sub' for user_id)
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(user_id: str) -> str:
    """Create a JWT refresh token with longer expiration.
    
    Args:
        user_id: The user's UUID as string
        
    Returns:
        Encoded JWT refresh token
    """
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_access_token({"sub": user_id, "type": "refresh"}, expires_delta)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.
    
    Args:
        token: The JWT token string
        
    Returns:
        The decoded token payload
        
    Raises:
        AuthenticationError: If token is invalid, expired, or malformed
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(
            message="Invalid authentication token",
            error_code="TOKEN_INVALID",
            context={"reason": str(e)}
        )


def validate_access_token(token: str) -> str:
    """Validate an access token and extract user_id.
    
    Args:
        token: The JWT access token
        
    Returns:
        The user_id (UUID as string) from token payload
        
    Raises:
        AuthenticationError: If token is invalid or missing user_id
    """
    payload = decode_token(token)
    
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(
            message="Token missing user identifier",
            error_code="TOKEN_MALFORMED"
        )
    
    # If token has a type field, ensure it's not a refresh token
    token_type = payload.get("type")
    if token_type == "refresh":
        raise AuthenticationError(
            message="Refresh token cannot be used for access",
            error_code="TOKEN_TYPE_MISMATCH"
        )
    
    return user_id


def validate_refresh_token(token: str) -> str:
    """Validate a refresh token and extract user_id.
    
    Args:
        token: The JWT refresh token
        
    Returns:
        The user_id (UUID as string) from token payload
        
    Raises:
        AuthenticationError: If token is invalid or not a refresh token
    """
    payload = decode_token(token)
    
    user_id: Optional[str] = payload.get("sub")
    token_type = payload.get("type")
    
    if user_id is None:
        raise AuthenticationError(
            message="Token missing user identifier",
            error_code="TOKEN_MALFORMED"
        )
    
    if token_type != "refresh":
        raise AuthorizationError(
            message="Token is not a refresh token",
            error_code="TOKEN_TYPE_MISMATCH"
        )
    
    return user_id


async def get_current_user(access_token: Optional[str] = Cookie(None)) -> UserResponse:
    """
    FastAPI dependency to get the current authenticated user from JWT cookie.
    
    Args:
        access_token: JWT token from httpOnly cookie
        
    Returns:
        User response object
        
    Raises:
        HTTPException(401): If token is missing, invalid, or user not found
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
        )
    
    try:
        # Validate token and get user_id
        user_id = validate_access_token(access_token)
        
        # In mock backend, we decode the payload to get user info
        # In production, this would query the database
        payload = decode_token(access_token)
        
        # Create user response from token payload
        # Note: In production, fetch from database using user_id
        return UserResponse(
            id=user_id,
            email=payload.get("email", ""),
            full_name=payload.get("full_name", ""),
            role=payload.get("role", "analyst"),
            is_active=True,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token. Please log in again.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
        )
