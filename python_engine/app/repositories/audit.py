"""Audit log repository for compliance and forensics."""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AuditLog
from app.exceptions import AuditError
from app.repositories.base import BaseRepository

# Sentinel UUID for audit actions without a user (e.g. failed login)
SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
NULL_RESOURCE_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


class AuditRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog model operations.
    
    Audit writes must NEVER fail silently. If write fails, logs to stderr.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(AuditLog, db)

    async def log_action(
        self,
        user_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID,
        after_state: dict[str, Any],
        before_state: Optional[dict[str, Any]],
        ip_address: str,
        user_agent: str,
    ) -> Optional[AuditLog]:
        """Log a state-changing action to audit trail.
        
        This method catches exceptions and logs to stderr instead of raising,
        because audit write failures should not block the main operation.
        However, it returns None on failure so the caller can decide whether
        to roll back the transaction.
        
        Args:
            user_id: User performing the action
            action: Action name (e.g., 'recommendation_decision')
            resource_type: Type of resource (e.g., 'hedge_recommendation')
            resource_id: Resource UUID
            after_state: State after the action
            before_state: State before the action (None for creates)
            ip_address: Client IP address
            user_agent: Client user agent string
            
        Returns:
            Created audit log or None if write failed
        """
        try:
            audit_log = AuditLog(
                id=uuid.uuid4(),
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                before_state=before_state,
                after_state=after_state,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.db.add(audit_log)
            await self.db.flush()
            await self.db.refresh(audit_log)
            return audit_log
        except Exception as e:
            # Log to stderr but don't raise - audit write failures should not block operations
            import sys
            import json
            error_data = {
                "error": "Audit log write failed",
                "exception": str(e),
                "user_id": str(user_id),
                "action": action,
                "resource_type": resource_type,
                "resource_id": str(resource_id),
            }
            print(json.dumps(error_data), file=sys.stderr)
            return None

    async def log_auth_action(
        self,
        *,
        action: str,
        resource_type: str = "user",
        resource_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: str = "127.0.0.1",
        user_agent: str = "unknown",
    ) -> Optional[AuditLog]:
        """Convenience method for auth-related audit logging.

        Maps simplified params to the full log_action signature.
        Uses SYSTEM_USER_ID when no user (e.g. failed login).
        """
        return await self.log_action(
            user_id=user_id or SYSTEM_USER_ID,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id or NULL_RESOURCE_ID,
            after_state=details or {},
            before_state=None,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def get_by_user(
        self, 
        user_id: uuid.UUID, 
        limit: int = 100
    ) -> list[AuditLog]:
        """Get audit logs for a specific user.
        
        Args:
            user_id: User UUID
            limit: Maximum number of records to return
            
        Returns:
            List of audit logs for the user (newest first)
        """
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_action(
        self, 
        action: str, 
        limit: int = 100
    ) -> list[AuditLog]:
        """Get audit logs for a specific action type.
        
        Args:
            action: Action name to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of audit logs for the action (newest first)
        """
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_resource(
        self, 
        resource_type: str, 
        resource_id: uuid.UUID
    ) -> list[AuditLog]:
        """Get all audit logs for a specific resource.
        
        Args:
            resource_type: Type of resource
            resource_id: Resource UUID
            
        Returns:
            List of audit logs for the resource (chronological order)
        """
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.resource_type == resource_type)
            .where(AuditLog.resource_id == resource_id)
            .order_by(AuditLog.created_at)
        )
        return list(result.scalars().all())

    async def get_recent(
        self, 
        days: int = 7, 
        limit: int = 1000
    ) -> list[AuditLog]:
        """Get recent audit logs.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of records to return
            
        Returns:
            List of recent audit logs (newest first)
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.created_at >= cutoff_date)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_approvals_audit(
        self, 
        days: int = 30
    ) -> list[AuditLog]:
        """Get approval decision audit logs.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of approval-related audit logs
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.action == "recommendation_decision")
            .where(AuditLog.created_at >= cutoff_date)
            .order_by(desc(AuditLog.created_at))
        )
        return list(result.scalars().all())

    async def get_range(
        self,
        date_from: date,
        date_to: date,
        action: Optional[str] = None,
    ) -> list[AuditLog]:
        """Get audit logs within a date range, optionally filtered by action.
        
        Args:
            date_from: Start date (inclusive)
            date_to: End date (inclusive)
            action: Optional action filter
            
        Returns:
            List of audit logs (newest first) with user loaded
        """
        start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
        query = (
            select(AuditLog)
            .options(selectinload(AuditLog.user))
            .where(AuditLog.created_at >= start_dt)
            .where(AuditLog.created_at <= end_dt)
        )
        if action:
            query = query.where(AuditLog.action == action)
        query = query.order_by(desc(AuditLog.created_at))
        result = await self.db.execute(query)
        return list(result.scalars().all())
