"""Pydantic schemas for hedge recommendation system.

All schemas enforce strict validation and match database models exactly.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================
# AGENT OUTPUT SCHEMAS (from n8n)
# ============================================================


class AgentOutput(BaseModel):
    """Individual AI agent output from n8n workflow.
    
    Each agent (basis_risk, liquidity, operational, ifrs9, macro) must
    return this exact structure.
    """

    model_config = ConfigDict(extra='forbid')

    agent_id: Literal['basis_risk', 'liquidity', 'operational', 'ifrs9', 'macro']
    risk_level: Literal['LOW', 'MODERATE', 'HIGH', 'CRITICAL']
    recommendation: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Agent's recommendation text",
    )
    metrics: dict[str, float | str | bool] = Field(
        ...,
        description="Agent-specific metrics (numbers, or categorical strings e.g. vol_regime='MODERATE', hedge_timing_signal='HEDGE_NOW')",
    )
    constraints_satisfied: bool
    action_required: bool
    ifrs9_eligible: bool | None = Field(
        ...,
        description="True if hedge qualifies for IFRS 9 accounting (only for relevant agents)",
    )
    generated_at: datetime


class AgentOutputPayload(BaseModel):
    """Full payload from n8n POST /api/v1/recommendations endpoint.
    
    Sent by n8n after all 5 agents complete + CRO gate passes.
    """

    model_config = ConfigDict(extra='forbid')

    run_id: UUID = Field(..., description="FK to analytics_runs.id")
    agent_outputs: list[AgentOutput] = Field(..., min_length=5, max_length=5)
    optimization_result: dict = Field(
        ...,
        description="Output from portfolio optimizer (hedge ratio, instrument mix, etc.)",
    )
    analytics_summary: dict = Field(
        ...,
        description="Summary of forecast, VaR, basis analysis results",
    )
    generated_at: datetime

    @field_validator('agent_outputs')
    @classmethod
    def validate_agent_ids(cls, v: list[AgentOutput]) -> list[AgentOutput]:
        """Ensure all 5 required agents are present exactly once."""
        agent_ids = {agent.agent_id for agent in v}
        required = {'basis_risk', 'liquidity', 'operational', 'ifrs9', 'macro'}
        if agent_ids != required:
            raise ValueError(
                f"Must include all 5 agents. Got: {agent_ids}, Required: {required}"
            )
        return v


class AgentOutputPayloadN8n(BaseModel):
    """Payload format sent by n8n workflow (flat structure).
    
    Accepts run_id as string (UUID or manual-xxx). Router transforms to AgentOutputPayload.
    """

    model_config = ConfigDict(extra='forbid')

    run_id: str = Field(..., description="UUID string or manual-{timestamp}")
    triggered_at: datetime = Field(..., description="When workflow was triggered")
    optimal_hr: float = Field(..., ge=0, le=0.80)
    instrument_mix: dict = Field(
        ...,
        description="futures, options, collars, swaps (sum to 1.0)",
    )
    proxy_weights: dict = Field(default_factory=dict)
    var_hedged_usd: float = Field(default=0, ge=0)
    var_unhedged_usd: float = Field(default=0, ge=0)
    var_reduction_pct: float = Field(default=0, ge=0, le=100)
    collateral_usd: float = Field(..., ge=0)
    collateral_pct_of_reserves: float = Field(default=0, ge=0, le=100)
    solver_converged: bool = Field(default=True)
    agent_outputs: list[AgentOutput] = Field(..., min_length=5, max_length=5)
    committee_consensus: dict = Field(default_factory=dict)
    cro_decision: dict = Field(default_factory=dict)

    @field_validator('agent_outputs')
    @classmethod
    def validate_agent_ids(cls, v: list[AgentOutput]) -> list[AgentOutput]:
        """Ensure all 5 required agents are present exactly once."""
        agent_ids = {agent.agent_id for agent in v}
        required = {'basis_risk', 'liquidity', 'operational', 'ifrs9', 'macro'}
        if agent_ids != required:
            raise ValueError(
                f"Must include all 5 agents. Got: {agent_ids}, Required: {required}"
            )
        return v

    def to_agent_output_payload(
        self,
        resolved_run_id: UUID,
    ) -> AgentOutputPayload:
        """Transform n8n payload to internal AgentOutputPayload."""
        return AgentOutputPayload(
            run_id=resolved_run_id,
            agent_outputs=self.agent_outputs,
            optimization_result={
                "optimal_hedge_ratio": self.optimal_hr,
                "instrument_mix": self.instrument_mix,
                "proxy_weights": self.proxy_weights,
                "var_hedged": self.var_hedged_usd,
                "var_unhedged": self.var_unhedged_usd,
                "var_reduction_pct": self.var_reduction_pct,
                "collateral_required_usd": self.collateral_usd,
            },
            analytics_summary={
                "committee_consensus": self.committee_consensus,
                "cro_decision": self.cro_decision,
            },
            generated_at=self.triggered_at,
        )


# ============================================================
# RECOMMENDATION RESPONSE SCHEMAS (to frontend)
# ============================================================


class InstrumentMix(BaseModel):
    """Instrument allocation percentages (must sum to 1.0)."""

    model_config = ConfigDict(extra='forbid')

    futures: Decimal = Field(..., ge=0, le=1)
    options: Decimal = Field(..., ge=0, le=1)
    collars: Decimal = Field(..., ge=0, le=1)
    swaps: Decimal = Field(..., ge=0, le=1)

    @field_validator('swaps')
    @classmethod
    def validate_sum_to_one(cls, v: Decimal, info) -> Decimal:
        """Ensure allocations sum to 1.0 (100%)."""
        if 'futures' not in info.data or 'options' not in info.data or 'collars' not in info.data:
            return v  # Skip validation if fields not yet populated
        
        total = info.data['futures'] + info.data['options'] + info.data['collars'] + v
        if not (0.99 <= total <= 1.01):  # Allow 1% tolerance for rounding
            raise ValueError(f"Instrument allocations must sum to 1.0, got {total}")
        return v


class OptimizationResult(BaseModel):
    """Portfolio optimizer output."""

    model_config = ConfigDict(extra='forbid')

    optimal_hedge_ratio: Decimal = Field(..., ge=0, le=0.80, description="HR_HARD_CAP = 0.80")
    expected_var_reduction: Decimal = Field(..., ge=0, le=1)
    instrument_mix: InstrumentMix
    collateral_required_usd: Decimal = Field(..., ge=0)
    ifrs9_eligible: bool
    ifrs9_r2: Decimal = Field(..., ge=0, le=1)


class ApprovalRecord(BaseModel):
    """Single approval/rejection decision."""

    model_config = ConfigDict(extra='forbid')

    id: UUID
    approver_id: UUID
    approver_name: str
    approver_role: str
    decision: Literal['APPROVE', 'REJECT', 'DEFER']
    created_at: datetime
    comments: str | None = None
    response_time_minutes: Decimal


class HedgeRecommendationResponse(BaseModel):
    """Full recommendation object returned to frontend.
    
    Used in GET /recommendations/:id and GET /recommendations/pending.
    """

    model_config = ConfigDict(extra='forbid')

    id: UUID
    run_id: UUID
    status: Literal['PENDING', 'APPROVED', 'REJECTED', 'DEFERRED', 'EXPIRED', 'CONSTRAINT_VIOLATED']
    created_at: datetime
    expires_at: datetime | None = Field(
        None,
        description="Expiry time for PENDING recommendations (2-hour SLA)",
    )
    
    # Top-level summary fields for quick display
    optimal_hedge_ratio: Decimal = Field(..., ge=0, le=0.80)
    expected_var_reduction: Decimal = Field(..., ge=0, le=1)
    hedge_effectiveness_r2: Decimal = Field(..., ge=0, le=1)
    collateral_impact: Decimal = Field(..., ge=0, description="As fraction of total reserves")
    constraints_satisfied: bool
    ifrs9_eligible: bool
    action_required: bool
    risk_level: Literal['LOW', 'MODERATE', 'HIGH', 'CRITICAL']
    recommendation_text: str
    
    # Detailed breakdown
    instrument_mix: InstrumentMix
    optimization_result: OptimizationResult
    agent_outputs: list[AgentOutput]
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    
    # Metadata
    escalation_flag: bool
    sequence_number: int


class RecommendationListResponse(BaseModel):
    """Paginated list of recommendations."""

    model_config = ConfigDict(extra='forbid')

    items: list[HedgeRecommendationResponse]
    total: int
    page: int
    limit: int
    pages: int


class RecommendationCreatedResponse(BaseModel):
    """Response after n8n webhook creates a new recommendation."""

    model_config = ConfigDict(extra='forbid')

    recommendation_id: UUID
    status: str
    sequence_number: int
    expires_at: datetime
    message: str


class RecommendationWithRun(BaseModel):
    """Recommendation with embedded analytics run data."""

    model_config = ConfigDict(extra='forbid')

    recommendation: HedgeRecommendationResponse
    run_data: dict = Field(default_factory=dict, description="Embedded analytics_runs data")


# ============================================================
# QUERY PARAMS
# ============================================================


class RecommendationQueryParams(BaseModel):
    """Query parameters for filtering recommendations."""

    model_config = ConfigDict(extra='forbid')

    status: Literal['PENDING', 'APPROVED', 'REJECTED', 'DEFERRED', 'EXPIRED', 'CONSTRAINT_VIOLATED'] | None = None
    run_id: UUID | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=200)


# ============================================================
# UPDATE SCHEMAS
# ============================================================


class UpdateRecommendationRequest(BaseModel):
    """Request to update recommendation metadata."""

    model_config = ConfigDict(extra='forbid')

    notes: str | None = Field(None, max_length=1000)
    escalation_flag: bool | None = None


# ============================================================
# APPROVAL ACTION SCHEMAS (from frontend)
# ============================================================


class ApproveRequest(BaseModel):
    """Payload for POST /recommendations/:id/approve."""

    model_config = ConfigDict(extra='forbid')

    comments: str | None = Field(None, max_length=1000)


class RejectRequest(BaseModel):
    """Payload for POST /recommendations/:id/reject."""

    model_config = ConfigDict(extra='forbid')

    reason: str = Field(..., min_length=10, max_length=1000)


class DeferRequest(BaseModel):
    """Payload for POST /recommendations/:id/defer."""

    model_config = ConfigDict(extra='forbid')

    reason: str = Field(..., min_length=10, max_length=1000)
    defer_until: datetime | None = Field(
        None,
        description="Optional rescheduled review time",
    )


# ============================================================
# SSE EVENT SCHEMAS
# ============================================================


class RecommendationEvent(BaseModel):
    """SSE event for /stream/recommendations endpoint."""

    model_config = ConfigDict(extra='forbid')

    event_type: Literal['new_recommendation', 'status_change', 'approaching_expiry']
    recommendation_id: UUID
    status: str
    timestamp: datetime
    data: dict = Field(default_factory=dict)
