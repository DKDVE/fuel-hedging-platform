"""Pydantic schemas for analytics runs."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import AnalyticsRunStatus
from app.schemas.common import TimestampMixin, UUIDMixin


class AnalyticsRunResponse(BaseModel):
    """Analytics run response."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    run_date: date
    status: AnalyticsRunStatus
    forecast_mape: Optional[Decimal] = Field(None, description="Forecast MAPE (%)")
    var_95_usd: Optional[Decimal] = Field(None, description="VaR at 95% confidence (USD)")
    basis_r2: Optional[Decimal] = Field(None, description="Basis risk R²")
    optimal_hr: Optional[Decimal] = Field(None, description="Optimal hedge ratio")
    pipeline_start_time: Optional[datetime] = None
    pipeline_end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AnalyticsRunQueryParams(BaseModel):
    """Query parameters for analytics runs."""

    model_config = ConfigDict(extra="forbid")

    status: Optional[AnalyticsRunStatus] = Field(None, description="Filter by status")
    start_date: Optional[date] = Field(None, description="Start date")
    end_date: Optional[date] = Field(None, description="End date")
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=50, ge=1, le=200, description="Items per page")


class TriggerAnalyticsRequest(BaseModel):
    """Manual analytics trigger request."""

    model_config = ConfigDict(extra="forbid")

    notional_usd: Optional[Decimal] = Field(
        None,
        description="Override notional amount (USD)",
        ge=0,
    )


class TriggerPipelineResponse(BaseModel):
    """Response for pipeline trigger (202 Accepted)."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="accepted", description="Status")
    message: str = Field(..., description="Human-readable message")
    run_id: str = Field(..., description="Run UUID")
    triggered_at: str = Field(..., description="ISO 8601 UTC timestamp")
    triggered_by: Optional[str] = Field(None, description="User email who triggered")


class LoadCsvResponse(BaseModel):
    """Response for CSV load."""

    model_config = ConfigDict(extra="forbid")

    imported: int = Field(..., description="New records imported")
    updated: int = Field(..., description="Existing records updated")
    skipped: int = Field(..., description="Rows skipped due to errors")
    total: int = Field(..., description="Total rows in CSV")


class AnalyticsRunDetail(AnalyticsRunResponse):
    """Detailed analytics run with metrics."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    duration_seconds: Optional[float] = Field(None, description="Pipeline execution time (seconds)")
    recommendations_count: int = Field(default=0, description="Number of recommendations generated")


class AnalyticsSummary(BaseModel):
    """Summary statistics for analytics runs."""

    model_config = ConfigDict(extra="forbid")

    total_runs: int
    successful_runs: int
    failed_runs: int
    average_mape: Optional[Decimal] = None
    average_var_reduction: Optional[Decimal] = None
    average_duration_seconds: Optional[float] = None


class DashboardSummaryResponse(BaseModel):
    """Dashboard KPI summary derived from latest analytics run."""

    model_config = ConfigDict(extra="forbid")

    ai_brief: Optional[dict] = Field(default=None, description="LLM generated dashboard brief")
    current_var_usd: float = Field(default=0.0, description="Current VaR in USD")
    current_hedge_ratio: float = Field(default=0.0, description="Current hedge ratio 0-1")
    collateral_pct: float = Field(default=0.0, description="Collateral as % of notional")
    mape_pct: float = Field(default=0.0, description="Forecast MAPE %")
    var_reduction_pct: float = Field(default=0.0, description="VaR reduction %")
    ifrs9_compliance_status: str = Field(default="unknown", description="IFRS9 compliance")
    last_updated: str = Field(default="", description="ISO 8601 of latest run")
    agent_outputs: list[dict] = Field(default_factory=list, description="Agent status for grid")
    r2_heating_oil: Optional[float] = Field(default=None, description="Heating oil proxy R² for IFRS 9")
    total_notional_usd: Optional[float] = Field(default=None, description="Total open position notional")
