"""Business logic layer for hedge recommendation workflow.

Orchestrates repository calls, validation, and event broadcasting.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Sequence
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import DecisionType, RecommendationStatus, HedgeRecommendation
from app.exceptions import BusinessRuleViolation, NotFoundError
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.recommendations import (
    AgentOutputPayload,
    ApprovalRecord,
    HedgeRecommendationResponse,
    InstrumentMix,
    OptimizationResult,
    RecommendationListResponse,
    AgentOutput,
)
from app.services.event_broker import PriceEventBroker

log = structlog.get_logger()


# ============================================================
# DOMAIN CONSTANTS (from .cursorrules)
# ============================================================

HR_HARD_CAP = Decimal("0.80")
HR_SOFT_WARN = Decimal("0.70")
COLLATERAL_LIMIT = Decimal("0.15")
IFRS9_R2_MIN_PROSPECTIVE = Decimal("0.80")
RECOMMENDATION_SLA_HOURS = 2  # 2-hour approval window


class RecommendationService:
    """Service layer for recommendation workflow operations."""

    def __init__(
        self,
        repo: RecommendationRepository,
        broker: PriceEventBroker,
        settings: Settings,
    ) -> None:
        self.repo = repo
        self.broker = broker
        self.settings = settings

    async def create_from_n8n(
        self,
        payload: AgentOutputPayload,
    ) -> HedgeRecommendationResponse:
        """Create recommendation from n8n webhook payload.
        
        Validates constraints, stores in DB, broadcasts SSE event.
        """
        log.info(
            "recommendation_service.create_from_n8n",
            run_id=str(payload.run_id),
            agent_count=len(payload.agent_outputs),
        )

        # Extract optimizer results
        opt_result = payload.optimization_result
        optimal_hr = Decimal(str(opt_result["optimal_hedge_ratio"]))
        instrument_mix = opt_result["instrument_mix"]
        var_hedged = Decimal(str(opt_result.get("var_hedged", 0)))
        var_unhedged = Decimal(str(opt_result.get("var_unhedged", 0)))
        var_reduction_pct = Decimal(str(opt_result.get("var_reduction_pct", 0)))
        collateral_usd = Decimal(str(opt_result["collateral_required_usd"]))
        
        # Validate hard constraints
        constraints_satisfied = self._validate_hard_constraints(
            optimal_hr=optimal_hr,
            collateral_usd=collateral_usd,
            agent_outputs=payload.agent_outputs,
        )

        # Determine status based on constraints
        status = (
            RecommendationStatus.PENDING
            if constraints_satisfied
            else RecommendationStatus.CONSTRAINT_VIOLATED
        )

        # Store in database
        recommendation = await self.repo.create(
            run_id=payload.run_id,
            optimal_hr=optimal_hr,
            instrument_mix=instrument_mix,
            proxy_weights=opt_result.get("proxy_weights", {}),
            var_hedged=var_hedged,
            var_unhedged=var_unhedged,
            var_reduction_pct=var_reduction_pct,
            collateral_usd=collateral_usd,
            agent_outputs={"agents": [agent.model_dump(mode="json") for agent in payload.agent_outputs]},
            status=status,
        )

        # Broadcast SSE event for real-time UI update
        await self.broker.broadcast_recommendation_event(
            event_type="new_recommendation",
            recommendation_id=recommendation.id,
            status=status.value,
            data={
                "sequence_number": recommendation.sequence_number,
                "optimal_hr": float(optimal_hr),
                "risk_level": self._compute_risk_level(payload.agent_outputs),
            },
        )

        log.info(
            "recommendation_created",
            recommendation_id=str(recommendation.id),
            sequence_number=recommendation.sequence_number,
            status=status.value,
            constraints_satisfied=constraints_satisfied,
        )

        # Convert to response schema
        return self._to_response_schema(recommendation, payload.agent_outputs)

    async def get_pending(self) -> list[HedgeRecommendationResponse]:
        """Get all pending recommendations (for approval workflow)."""
        recommendations = await self.repo.get_pending()
        
        # Check for expired recommendations
        await self._expire_old_recommendations(recommendations)
        
        # Re-fetch after expiration updates
        recommendations = await self.repo.get_pending()

        responses: list[HedgeRecommendationResponse] = []
        for rec in recommendations:
            resolved_agents = await self._resolve_agent_outputs(rec)
            responses.append(self._to_response_schema(rec, resolved_agents))
        return responses

    async def get_by_id(self, recommendation_id: UUID) -> HedgeRecommendationResponse:
        """Get single recommendation by ID."""
        recommendation = await self.repo.get_by_id(recommendation_id)
        resolved_agents = await self._resolve_agent_outputs(recommendation)
        return self._to_response_schema(recommendation, resolved_agents)

    async def list_paginated(
        self,
        page: int = 1,
        limit: int = 10,
        *,
        status: str | None = None,
    ) -> RecommendationListResponse:
        """Get paginated list of recommendations."""
        # Convert string status to enum if provided
        status_enum = None
        if status:
            try:
                status_enum = RecommendationStatus(status.upper())
            except ValueError:
                raise BusinessRuleViolation(f"Invalid status: {status}")

        recommendations, total = await self.repo.list_paginated(
            page=page,
            limit=limit,
            status=status_enum,
        )

        items: list[HedgeRecommendationResponse] = []
        for rec in recommendations:
            resolved_agents = await self._resolve_agent_outputs(rec)
            items.append(self._to_response_schema(rec, resolved_agents))
        pages = (total + limit - 1) // limit  # Ceiling division

        return RecommendationListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

    async def approve(
        self,
        recommendation_id: UUID,
        approver_id: UUID,
        ip_address: str,
        comments: str | None = None,
        custom_hedge_ratio: float | None = None,
        custom_instrument_mix: dict | None = None,
    ) -> HedgeRecommendationResponse:
        """Approve a recommendation.
        
        Updates status to APPROVED and records approval decision.
        """
        log.info(
            "approving_recommendation",
            recommendation_id=str(recommendation_id),
            approver_id=str(approver_id),
        )

        # Get current recommendation
        recommendation = await self.repo.get_by_id(recommendation_id)

        # Validate state
        if recommendation.status != RecommendationStatus.PENDING:
            raise BusinessRuleViolation(
                f"Cannot approve recommendation in {recommendation.status.value} state"
            )

        # Calculate response time
        response_lag_minutes = self._calculate_response_lag(recommendation.created_at)

        # Build full audit comment
        full_comment = comments or ""
        if custom_hedge_ratio is not None:
            full_comment = (
                f"[Custom HR: {custom_hedge_ratio:.1%}] " + full_comment
            ).strip()
        if custom_instrument_mix is not None:
            mix_str = ", ".join(
                f"{k}={v:.0%}" for k, v in custom_instrument_mix.items() if v > 0
            )
            full_comment = (
                f"[Custom mix: {mix_str}] " + full_comment
            ).strip()

        # Persist CFO overrides to recommendation so downstream position creation
        # uses the approved strategy even when positions are created later.
        if custom_hedge_ratio is not None:
            recommendation.optimal_hr = Decimal(str(custom_hedge_ratio))
        if custom_instrument_mix is not None:
            recommendation.instrument_mix = custom_instrument_mix
        await self.repo.session.flush()

        # Record approval
        await self.repo.add_approval(
            recommendation_id=recommendation_id,
            approver_id=approver_id,
            decision=DecisionType.APPROVE,
            response_lag_minutes=response_lag_minutes,
            override_reason=full_comment or None,
            ip_address=ip_address,
        )

        # Update status
        updated_recommendation = await self.repo.update_status(
            recommendation_id,
            RecommendationStatus.APPROVED,
        )

        # Broadcast status change event
        await self.broker.broadcast_recommendation_event(
            event_type="status_change",
            recommendation_id=recommendation_id,
            status="APPROVED",
            data={"approver_id": str(approver_id)},
        )

        log.info(
            "recommendation_approved",
            recommendation_id=str(recommendation_id),
            approver_id=str(approver_id),
            response_lag_minutes=float(response_lag_minutes),
        )

        resolved_agents = await self._resolve_agent_outputs(updated_recommendation)
        return self._to_response_schema(updated_recommendation, resolved_agents)

    async def reject(
        self,
        recommendation_id: UUID,
        approver_id: UUID,
        ip_address: str,
        reason: str,
    ) -> HedgeRecommendationResponse:
        """Reject a recommendation."""
        log.info(
            "rejecting_recommendation",
            recommendation_id=str(recommendation_id),
            approver_id=str(approver_id),
        )

        recommendation = await self.repo.get_by_id(recommendation_id)

        if recommendation.status != RecommendationStatus.PENDING:
            raise BusinessRuleViolation(
                f"Cannot reject recommendation in {recommendation.status.value} state"
            )

        response_lag_minutes = self._calculate_response_lag(recommendation.created_at)

        await self.repo.add_approval(
            recommendation_id=recommendation_id,
            approver_id=approver_id,
            decision=DecisionType.REJECT,
            response_lag_minutes=response_lag_minutes,
            override_reason=reason,
            ip_address=ip_address,
        )

        updated_recommendation = await self.repo.update_status(
            recommendation_id,
            RecommendationStatus.REJECTED,
        )

        await self.broker.broadcast_recommendation_event(
            event_type="status_change",
            recommendation_id=recommendation_id,
            status="REJECTED",
            data={"approver_id": str(approver_id)},
        )

        log.info(
            "recommendation_rejected",
            recommendation_id=str(recommendation_id),
            approver_id=str(approver_id),
        )

        resolved_agents = await self._resolve_agent_outputs(updated_recommendation)
        return self._to_response_schema(updated_recommendation, resolved_agents)

    async def defer(
        self,
        recommendation_id: UUID,
        approver_id: UUID,
        ip_address: str,
        reason: str,
    ) -> HedgeRecommendationResponse:
        """Defer a recommendation for later review."""
        log.info(
            "deferring_recommendation",
            recommendation_id=str(recommendation_id),
            approver_id=str(approver_id),
        )

        recommendation = await self.repo.get_by_id(recommendation_id)

        if recommendation.status != RecommendationStatus.PENDING:
            raise BusinessRuleViolation(
                f"Cannot defer recommendation in {recommendation.status.value} state"
            )

        response_lag_minutes = self._calculate_response_lag(recommendation.created_at)

        await self.repo.add_approval(
            recommendation_id=recommendation_id,
            approver_id=approver_id,
            decision=DecisionType.DEFER,
            response_lag_minutes=response_lag_minutes,
            override_reason=reason,
            ip_address=ip_address,
        )

        updated_recommendation = await self.repo.update_status(
            recommendation_id,
            RecommendationStatus.DEFERRED,
        )

        await self.broker.broadcast_recommendation_event(
            event_type="status_change",
            recommendation_id=recommendation_id,
            status="DEFERRED",
            data={"approver_id": str(approver_id)},
        )

        log.info(
            "recommendation_deferred",
            recommendation_id=str(recommendation_id),
            approver_id=str(approver_id),
        )

        resolved_agents = await self._resolve_agent_outputs(updated_recommendation)
        return self._to_response_schema(updated_recommendation, resolved_agents)

    # ============================================================
    # PRIVATE HELPERS
    # ============================================================

    def _extract_agent_outputs_from_json(
        self,
        raw_agent_outputs: object,
    ) -> list[AgentOutput]:
        """Parse agent outputs from DB JSON payloads.

        Supports both list payloads and {'agents': [...]} payloads.
        """
        if not raw_agent_outputs:
            return []

        agents_raw = (
            raw_agent_outputs.get("agents")
            if isinstance(raw_agent_outputs, dict)
            else raw_agent_outputs
        )
        if not isinstance(agents_raw, list):
            return []

        parsed: list[AgentOutput] = []
        for item in agents_raw:
            if not isinstance(item, dict):
                continue
            try:
                parsed.append(AgentOutput(**item))
            except Exception:
                # Skip malformed historical records rather than failing whole response.
                continue
        return parsed

    async def _resolve_agent_outputs(
        self,
        recommendation: HedgeRecommendation,
    ) -> list[AgentOutput]:
        """Resolve best available agent outputs for a recommendation.

        Priority:
        1) recommendation.agent_outputs
        2) latest recommendation for the same run that has agent outputs
        """
        direct = self._extract_agent_outputs_from_json(recommendation.agent_outputs)
        if direct:
            return direct

        sibling_result = await self.repo.session.execute(
            select(HedgeRecommendation.agent_outputs)
            .where(HedgeRecommendation.run_id == recommendation.run_id)
            .order_by(HedgeRecommendation.sequence_number.desc())
            .limit(20)
        )
        for raw in sibling_result.scalars().all():
            parsed = self._extract_agent_outputs_from_json(raw)
            if parsed:
                return parsed

        return []

    def _validate_hard_constraints(
        self,
        optimal_hr: Decimal,
        collateral_usd: Decimal,
        agent_outputs: list[AgentOutput],
    ) -> bool:
        """Check if recommendation satisfies all hard constraints.
        
        Returns False if any constraint is violated.
        """
        # HR cap (hard limit)
        if optimal_hr > HR_HARD_CAP:
            log.warning(
                "hr_cap_violated",
                optimal_hr=float(optimal_hr),
                cap=float(HR_HARD_CAP),
            )
            return False

        # Collateral limit (fraction of reserves)
        # TODO: Get actual reserve balance from config or DB
        # For now, assume collateral_usd is already validated in optimizer
        
        # All agents must satisfy their constraints
        if not all(agent.constraints_satisfied for agent in agent_outputs):
            log.warning("agent_constraints_violated")
            return False

        return True

    def _compute_risk_level(self, agent_outputs: list[AgentOutput]) -> str:
        """Aggregate agent risk levels into overall recommendation risk.
        
        Returns highest risk level across all agents.
        Returns LOW when no agent data (e.g. pipeline-created recommendations).
        """
        if not agent_outputs:
            return "LOW"
        risk_priority = {"CRITICAL": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}
        max_risk = max(agent_outputs, key=lambda a: risk_priority.get(a.risk_level, 0))
        return max_risk.risk_level

    def _calculate_response_lag(self, created_at: datetime) -> Decimal:
        """Calculate time elapsed since recommendation creation (in minutes)."""
        now = datetime.now(timezone.utc)
        delta = now - created_at
        return Decimal(str(delta.total_seconds() / 60))

    async def _expire_old_recommendations(
        self,
        recommendations: Sequence[HedgeRecommendation],
    ) -> None:
        """Mark pending recommendations past SLA as expired."""
        now = datetime.now(timezone.utc)
        expiry_threshold = timedelta(hours=RECOMMENDATION_SLA_HOURS)

        for rec in recommendations:
            if rec.status == RecommendationStatus.PENDING:
                age = now - rec.created_at
                if age > expiry_threshold:
                    log.warning(
                        "recommendation_expired_sla",
                        recommendation_id=str(rec.id),
                        age_hours=age.total_seconds() / 3600,
                    )
                    await self.repo.mark_expired(rec.id)

    def _to_response_schema(
        self,
        recommendation: HedgeRecommendation,
        agent_outputs: list[AgentOutput] | None = None,
    ) -> HedgeRecommendationResponse:
        """Convert DB model to API response schema."""
        # Extract agent outputs from JSONB (pipeline-created recs may have empty agents)
        if agent_outputs is None:
            agent_outputs = self._extract_agent_outputs_from_json(recommendation.agent_outputs)

        # Calculate expiry time (2 hours from creation for PENDING)
        expires_at = None
        if recommendation.status == RecommendationStatus.PENDING:
            expires_at = recommendation.created_at + timedelta(hours=RECOMMENDATION_SLA_HOURS)

        # Build instrument mix
        mix = recommendation.instrument_mix
        instrument_mix = InstrumentMix(
            futures=Decimal(str(mix.get("futures", 0))),
            options=Decimal(str(mix.get("options", 0))),
            collars=Decimal(str(mix.get("collars", 0))),
            swaps=Decimal(str(mix.get("swaps", 0))),
        )

        # Build optimization result
        opt_result = OptimizationResult(
            optimal_hedge_ratio=recommendation.optimal_hr,
            expected_var_reduction=recommendation.var_reduction_pct / 100,
            instrument_mix=instrument_mix,
            collateral_required_usd=recommendation.collateral_usd,
            ifrs9_eligible=any(
                agent.ifrs9_eligible is True for agent in agent_outputs
            ),
            ifrs9_r2=Decimal(str(
                next(
                    (agent.metrics.get("prospective_r2", agent.metrics.get("r2_prospective", 0))
                     for agent in agent_outputs if agent.agent_id == "ifrs9"),
                    0
                )
            )),
        )

        # Build approval records
        approvals = [
            ApprovalRecord(
                id=approval.id,
                approver_id=approval.approver_id,
                approver_name=approval.approver.email if approval.approver else "Unknown",
                approver_role=approval.approver.role.value if approval.approver else "unknown",
                decision=approval.decision.value,
                created_at=approval.created_at,
                comments=approval.override_reason,
                response_time_minutes=approval.response_lag_minutes,
            )
            for approval in recommendation.approvals
        ]

        # Compute summary fields
        risk_level = self._compute_risk_level(agent_outputs)
        constraints_satisfied = all(agent.constraints_satisfied for agent in agent_outputs)
        action_required = any(agent.action_required for agent in agent_outputs)
        ifrs9_eligible = any(agent.ifrs9_eligible is True for agent in agent_outputs)

        # Generate recommendation text summary
        recommendation_text = self._generate_recommendation_text(
            optimal_hr=recommendation.optimal_hr,
            var_reduction_pct=recommendation.var_reduction_pct,
            constraints_satisfied=constraints_satisfied,
            risk_level=risk_level,
        )

        return HedgeRecommendationResponse(
            id=recommendation.id,
            run_id=recommendation.run_id,
            status=recommendation.status.value,
            created_at=recommendation.created_at,
            expires_at=expires_at,
            optimal_hedge_ratio=recommendation.optimal_hr,
            expected_var_reduction=recommendation.var_reduction_pct / 100,
            hedge_effectiveness_r2=opt_result.ifrs9_r2,
            collateral_impact=recommendation.collateral_usd / 100_000_000,  # Fraction of $100M reserves
            constraints_satisfied=constraints_satisfied,
            ifrs9_eligible=ifrs9_eligible,
            action_required=action_required,
            risk_level=risk_level,
            recommendation_text=recommendation_text,
            instrument_mix=instrument_mix,
            optimization_result=opt_result,
            agent_outputs=agent_outputs,
            approvals=approvals,
            escalation_flag=recommendation.escalation_flag,
            sequence_number=recommendation.sequence_number,
        )

    def _generate_recommendation_text(
        self,
        optimal_hr: Decimal,
        var_reduction_pct: Decimal,
        constraints_satisfied: bool,
        risk_level: str,
    ) -> str:
        """Generate human-readable recommendation summary."""
        hr_pct = optimal_hr * 100
        var_pct = var_reduction_pct

        if not constraints_satisfied:
            return (
                f"CONSTRAINT VIOLATION: Proposed hedge ratio of {hr_pct:.0f}% "
                f"violates one or more risk constraints. Manual review required."
            )

        if risk_level == "LOW":
            return (
                f"Recommend hedge ratio of {hr_pct:.0f}% with diversified instrument mix. "
                f"Expected VaR reduction: {var_pct:.0f}%. All risk constraints satisfied."
            )
        elif risk_level == "MODERATE":
            return (
                f"Recommend hedge ratio of {hr_pct:.0f}% under moderate risk conditions. "
                f"Expected VaR reduction: {var_pct:.0f}%. Monitor collateral and volatility closely."
            )
        else:  # HIGH or CRITICAL
            return (
                f"HIGH RISK: Hedge ratio of {hr_pct:.0f}% recommended despite elevated risk signals. "
                f"Expected VaR reduction: {var_pct:.0f}%. Escalate for CFO review."
            )


def get_recommendation_service(
    session: AsyncSession,
    broker: PriceEventBroker,
) -> RecommendationService:
    """Dependency injection factory for FastAPI."""
    repo = RecommendationRepository(session)
    settings = get_settings()
    return RecommendationService(repo, broker, settings)
