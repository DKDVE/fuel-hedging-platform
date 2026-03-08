"""Audit API endpoints.

Returns real audit data from database. No mock/fake data.
"""

import csv
import io
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from app.db.models import Approval, AuditLog
from app.dependencies import AnalystUser, DatabaseSession, require_permission
from app.repositories.audit import AuditRepository

router = APIRouter()


@router.get("/approvals", response_model=dict)
async def list_approvals(
    current_user: AnalystUser,
    db: DatabaseSession,
    days: int = Query(30, ge=1, le=365),
) -> dict:
    """List approval decisions from database. Empty when no approvals exist."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(Approval)
        .options(selectinload(Approval.approver))
        .where(Approval.created_at >= cutoff)
        .order_by(desc(Approval.created_at))
        .limit(500)
    )
    approvals = result.scalars().all()

    items = []
    for a in approvals:
        approver_name = a.approver.full_name if a.approver else "Unknown"
        items.append({
            "id": str(a.id),
            "recommendation_id": str(a.recommendation_id),
            "date": a.created_at.isoformat() if a.created_at else None,
            "approver": approver_name,
            "role": a.approver.role.value if a.approver else "N/A",
            "decision": a.decision.value,
            "reason": a.override_reason,
            "response_time_mins": float(a.response_lag_minutes),
        })

    return {"items": items}


@router.get("/logs", response_model=dict)
async def list_audit_logs(
    current_user: AnalystUser,
    db: DatabaseSession,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    """List audit log entries. Empty when no logs exist."""
    from app.repositories.audit import AuditRepository

    repo = AuditRepository(db)
    logs = await repo.get_recent(days=days, limit=limit)

    items = [
        {
            "id": str(log.id),
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id),
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "user_id": str(log.user_id),
        }
        for log in logs
    ]

    return {"items": items}


def _summarise_state(state: dict | None) -> str:
    """Convert JSONB state to short human-readable string for CSV."""
    if state is None:
        return ""
    if "status" in state:
        return f"status={state['status']}"
    if "optimal_hr" in state:
        return f"hr={state.get('optimal_hr', '?')}"
    return f"{len(state)} fields"


@router.get("/export")
async def export_audit_csv(
    db: DatabaseSession,
    current_user=Depends(require_permission("read:audit")),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    action: str | None = Query(default=None),
) -> Response:
    """
    Export audit log as CSV for regulatory/compliance purposes.
    Date range defaults to last 90 days if not specified.
    Returns CSV with all audit fields including before/after state.
    """
    if date_from is None:
        date_from = date.today() - timedelta(days=90)
    if date_to is None:
        date_to = date.today()

    repo = AuditRepository(db)
    records = await repo.get_range(date_from, date_to, action)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "timestamp",
            "user_email",
            "user_role",
            "action",
            "resource_type",
            "resource_id",
            "ip_address",
            "before_state_summary",
            "after_state_summary",
        ],
    )
    writer.writeheader()

    for record in records:
        user_email = record.user.email if record.user else "system"
        user_role = record.user.role.value if record.user else "system"
        writer.writerow({
            "timestamp": record.created_at.isoformat() if record.created_at else "",
            "user_email": user_email,
            "user_role": user_role,
            "action": record.action,
            "resource_type": record.resource_type,
            "resource_id": str(record.resource_id) if record.resource_id else "",
            "ip_address": str(record.ip_address) if record.ip_address else "",
            "before_state_summary": _summarise_state(record.before_state),
            "after_state_summary": _summarise_state(record.after_state),
        })

    csv_content = output.getvalue()
    filename = f"audit_log_{date_from}_{date_to}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
