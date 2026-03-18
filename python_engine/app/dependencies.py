"""FastAPI dependency injection providers.

This module contains all dependency providers for:
- Database sessions
- Current user authentication
- Repository injection
- Rate limiting
"""

import hmac
from typing import Annotated, AsyncGenerator

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import validate_access_token
from app.config import Settings, get_settings
from app.db.base import AsyncSessionLocal
from app.db.models import User, UserRole
from app.exceptions import AuthenticationError, AuthorizationError
from app.repositories import UserRepository


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session as FastAPI dependency.
    
    Yields:
        AsyncSession: SQLAlchemy async session
        
    Note:
        Session is automatically committed or rolled back on exit.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    access_token: Annotated[str | None, Cookie()] = None,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT cookie or Authorization header.

    Cookie is primary (same-origin). Authorization: Bearer <token> is fallback for
    cross-origin when third-party cookies are blocked (e.g. GitHub Pages → Render).
    """
    token = access_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    
    try:
        user_id = validate_access_token(token)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.to_dict(),
        )
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "USER_NOT_FOUND", "message": "User no longer exists"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "USER_INACTIVE", "message": "User account is inactive"},
        )
    
    return user


def require_role(required_role: UserRole):
    """Factory for role-based access control dependency.
    
    Args:
        required_role: The minimum role required
        
    Returns:
        Dependency function that checks user role
    """
    async def check_role(current_user: User = Depends(get_current_user)) -> User:
        """Check if current user has required role."""
        role_hierarchy = {
            UserRole.ANALYST: 0,
            UserRole.RISK_MANAGER: 1,
            UserRole.CFO: 2,
            UserRole.ADMIN: 3,
        }
        
        user_level = role_hierarchy.get(current_user.role, -1)
        required_level = role_hierarchy.get(required_role, 999)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Requires {required_role.value} role or higher",
                },
            )
        
        return current_user
    
    return check_role


def require_permission(permission: str):
    """Factory for permission-based access control dependency.
    
    Permission-to-role mapping for fuel hedging platform:
    - 'view:analytics' -> ANALYST and above
    - 'trigger:analytics' -> RISK_MANAGER and above
    - 'approve:recommendation' -> RISK_MANAGER and above
    - 'manage:users' -> ADMIN only
    - 'view:recommendations' -> ANALYST and above
    
    Args:
        permission: Permission string in format 'action:resource'
        
    Returns:
        Dependency function that checks user has required permission
        
    Raises:
        HTTPException: 403 if user lacks permission
    """
    # Permission to minimum role mapping
    permission_map = {
        # Analytics permissions
        'view:analytics': UserRole.ANALYST,
        'read:analytics': UserRole.ANALYST,
        'trigger:analytics': UserRole.RISK_MANAGER,
        'trigger:pipeline': UserRole.RISK_MANAGER,
        'read:positions': UserRole.ANALYST,
        'read:audit': UserRole.RISK_MANAGER,
        'export:analytics': UserRole.ANALYST,
        
        # Recommendation permissions
        'view:recommendations': UserRole.ANALYST,
        'approve:recommendation': UserRole.RISK_MANAGER,
        'reject:recommendation': UserRole.RISK_MANAGER,
        'defer:recommendation': UserRole.RISK_MANAGER,
        
        # Market data permissions
        'view:market_data': UserRole.ANALYST,
        'export:market_data': UserRole.ANALYST,
        
        # User management permissions
        'view:users': UserRole.CFO,
        'manage:users': UserRole.ADMIN,
        'create:users': UserRole.ADMIN,
        'update:users': UserRole.ADMIN,
        'delete:users': UserRole.ADMIN,
        
        # System permissions
        'view:system_health': UserRole.ANALYST,
        'manage:system': UserRole.ADMIN,
        'edit:config': UserRole.ADMIN,
    }
    
    required_role = permission_map.get(permission)
    
    if required_role is None:
        # If permission not mapped, require ADMIN by default (fail-secure)
        required_role = UserRole.ADMIN
        
    async def check_permission(current_user: User = Depends(get_current_user)) -> User:
        """Check if current user has required permission."""
        role_hierarchy = {
            UserRole.ANALYST: 0,
            UserRole.RISK_MANAGER: 1,
            UserRole.CFO: 2,
            UserRole.ADMIN: 3,
        }
        
        user_level = role_hierarchy.get(current_user.role, -1)
        required_level = role_hierarchy.get(required_role, 999)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Permission '{permission}' requires {required_role.value} role or higher",
                },
            )
        
        return current_user
    
    return check_permission


async def analytics_or_n8n_auth(
    access_token: Annotated[str | None, Cookie()] = None,
    authorization: Annotated[str | None, Header()] = None,
    n8n_key: Annotated[str | None, Header(alias="X-N8N-API-Key")] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User | None:
    """Accept JWT (returns User) or X-N8N-API-Key (returns None) for analytics read endpoints.

    JWT from cookie or Authorization: Bearer header (cross-origin fallback).
    """
    if n8n_key and hmac.compare_digest(n8n_key, settings.N8N_WEBHOOK_SECRET):
        return None  # n8n auth OK
    token = access_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    if token:
        try:
            user_id = validate_access_token(token)
            user_repo = UserRepository(db)
            user = await user_repo.get_by_id(user_id)
            if user and user.is_active:
                return user
        except AuthenticationError:
            pass
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error_code": "MISSING_TOKEN", "message": "Authentication required"},
    )


# Type aliases for cleaner endpoint signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]
RiskManagerUser = Annotated[User, Depends(require_role(UserRole.RISK_MANAGER))]
AnalystUser = Annotated[User, Depends(require_role(UserRole.ANALYST))]
AnalyticsOrN8nAuth = Annotated[User | None, Depends(analytics_or_n8n_auth)]
