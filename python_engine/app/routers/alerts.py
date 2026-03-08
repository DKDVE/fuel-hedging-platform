"""Alerts API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import CurrentUser, DatabaseSession, require_permission
from app.repositories import AlertRepository
from app.schemas.alerts import AlertResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _alert_to_response(a) -> AlertResponse:
    return AlertResponse(
        id=a.id,
        alert_type=a.alert_type.value,
        severity=a.severity.value,
        title=a.title,
        message=a.message,
        metric_value=float(a.metric_value) if a.metric_value is not None else None,
        threshold_value=float(a.threshold_value) if a.threshold_value is not None else None,
        is_acknowledged=a.is_acknowledged,
        acknowledged_by=a.acknowledged_by,
        acknowledged_at=a.acknowledged_at,
        created_at=a.created_at,
    )


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    db: DatabaseSession,
    current_user=Depends(require_permission("read:analytics")),
    status: str | None = Query(default="active", pattern="^(active|acknowledged|all)$"),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[AlertResponse]:
    """Returns recent alerts. Default: only unacknowledged (active) alerts."""
    status_filter = status if status else "active"
    if status_filter == "all":
        status_filter = None

    repo = AlertRepository(db)
    alerts = await repo.list_alerts(status=status_filter, limit=limit)
    return [_alert_to_response(a) for a in alerts]


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> AlertResponse:
    """Mark an alert as acknowledged by the current user."""
    from datetime import datetime, timezone

    repo = AlertRepository(db)
    alert = await repo.get_by_id(alert_id)

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NOT_FOUND", "message": "Alert not found"},
        )

    alert.is_acknowledged = True
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(alert)

    return _alert_to_response(alert)
