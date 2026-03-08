"""Authentication router.

Handles:
- User login
- Token refresh
- User registration (admin only)
- Password changes
"""

from datetime import timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    validate_refresh_token,
    verify_password,
)
from app.config import get_settings
from app.dependencies import AdminUser, CurrentUser, DatabaseSession
from app.db.models import User
from app.repositories import AuditRepository, UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
    UpdateUserRequest,
    UserResponse,
)

router = APIRouter()
logger = structlog.get_logger()
settings = get_settings()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    credentials: LoginRequest,
    response: Response,
    db: DatabaseSession,
) -> LoginResponse:
    """Authenticate user and set httpOnly cookies.
    
    Rate limit: 5 requests per minute per IP.
    """
    try:
        return await _do_login(request, credentials, response, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("login_unhandled_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "LOGIN_ERROR", "message": "An error occurred during login. Please try again."},
        ) from e


async def _do_login(
    request: Request,
    credentials: LoginRequest,
    response: Response,
    db: DatabaseSession,
) -> LoginResponse:
    """Core login logic (extracted for error handling)."""
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)

    # Find user by email
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        await audit_repo.log_auth_action(
            action="login_failed",
            resource_type="user",
            details={"email": credentials.email, "reason": "invalid_credentials"},
            ip_address=request.client.host if request.client else "127.0.0.1",
            user_agent=request.headers.get("user-agent", "unknown"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
        )

    if not user.is_active:
        await audit_repo.log_auth_action(
            action="login_failed",
            resource_type="user",
            resource_id=user.id,
            user_id=user.id,
            details={"email": credentials.email, "reason": "account_inactive"},
            ip_address=request.client.host if request.client else "127.0.0.1",
            user_agent=request.headers.get("user-agent", "unknown"),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "ACCOUNT_INACTIVE", "message": "User account is inactive"},
        )

    # Create tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token(str(user.id))

    # Set httpOnly cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    # Log successful login
    await audit_repo.log_auth_action(
        action="login_success",
        resource_type="user",
        resource_id=user.id,
        user_id=user.id,
        details={"email": user.email},
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown"),
    )

    logger.info("user_login", user_id=str(user.id), email=user.email)

    return LoginResponse(user=UserResponse.model_validate(user))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    response: Response,
    db: DatabaseSession,
    refresh_token: str | None = Cookie(None),
    refresh_request: RefreshTokenRequest | None = Body(None),
) -> TokenResponse:
    """Refresh access token using refresh token from cookie or body."""
    token = refresh_token or (refresh_request.refresh_token if refresh_request else None)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "MISSING_REFRESH_TOKEN", "message": "Refresh token required (cookie or body)"},
        )
    try:
        user_id = validate_refresh_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_REFRESH_TOKEN", "message": str(e)},
        )
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "USER_NOT_FOUND", "message": "User not found or inactive"},
        )
    
    # Create new tokens
    access_token = create_access_token({"sub": str(user.id)})
    new_refresh_token = create_refresh_token(str(user.id))
    
    # Update cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/logout")
async def logout(response: Response, current_user: CurrentUser) -> MessageResponse:
    """Logout user by clearing cookies."""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    logger.info("user_logout", user_id=str(current_user.id))
    
    return MessageResponse(message="Logout successful")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> MessageResponse:
    """Change own password."""
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_PASSWORD", "message": "Current password is incorrect"},
        )
    
    # Update password
    user_repo = UserRepository(db)
    current_user.hashed_password = hash_password(password_data.new_password)
    await user_repo.update(current_user)
    
    # Log password change
    audit_repo = AuditRepository(db)
    await audit_repo.log_auth_action(
        action="password_changed",
        resource_type="user",
        resource_id=current_user.id,
        user_id=current_user.id,
        details={},
    )
    
    logger.info("password_changed", user_id=str(current_user.id))
    
    return MessageResponse(message="Password changed successfully")


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: CreateUserRequest,
    admin: AdminUser,
    db: DatabaseSession,
) -> UserResponse:
    """Create a new user (admin only)."""
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)
    
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "EMAIL_EXISTS", "message": "Email already registered"},
        )
    
    # Create user
    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
        is_active=True,
    )
    
    created_user = await user_repo.create(new_user)
    
    # Log user creation
    await audit_repo.log_auth_action(
        action="user_created",
        resource_type="user",
        resource_id=created_user.id,
        user_id=admin.id,
        details={"email": created_user.email, "role": created_user.role.value},
    )
    
    logger.info("user_created", user_id=str(created_user.id), created_by=str(admin.id))
    
    return UserResponse.model_validate(created_user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UpdateUserRequest,
    admin: AdminUser,
    db: DatabaseSession,
) -> UserResponse:
    """Update user (admin only)."""
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "USER_NOT_FOUND", "message": "User not found"},
        )
    
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    updated_user = await user_repo.update(user)
    
    # Log update
    await audit_repo.log_auth_action(
        action="user_updated",
        resource_type="user",
        resource_id=user.id,
        user_id=admin.id,
        details=update_data,
    )
    
    logger.info("user_updated", user_id=str(user.id), updated_by=str(admin.id))
    
    return UserResponse.model_validate(updated_user)
