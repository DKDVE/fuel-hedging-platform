"""Alert API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertResponse(BaseModel):
    """Alert response schema."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    alert_type: str
    severity: str
    title: str
    message: str
    metric_value: float | None = None
    threshold_value: float | None = None
    is_acknowledged: bool
    acknowledged_by: UUID | None = None
    acknowledged_at: datetime | None = None
    created_at: datetime
