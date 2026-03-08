"""API endpoints for hedge recommendation workflow.

Handles recommendation CRUD, approval actions, and n8n webhook receiver.
"""

import hmac
from datetime import date, datetime, timezone
from uuid import UUID

import httpx
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, require_permission
from app.config import Settings, get_settings
from app.db.base import get_db
from app.exceptions import BusinessRuleViolation, DataIngestionError, NotFoundError
from app.repositories import AnalyticsRepository
from app.schemas.recommendations import (
    AgentOutputPayload,
    AgentOutputPayloadN8n,
    ApproveRequest,
    DeferRequest,
    HedgeRecommendationResponse,
    RecommendationCreatedResponse,
    RecommendationListResponse,
    RejectRequest,
)
from app.schemas.auth import UserResponse
from app.services.event_broker import PriceEventBroker, get_price_broker
from app.services.recommendation_service import RecommendationService, get_recommendation_service

router = APIRouter()
log = structlog.get_logger()


# ============================================================
# PUBLIC ENDPOINTS (with authentication)
# ============================================================


@router.get("/pending", response_model=list[HedgeRecommendationResponse])
async def get_pending_recommendations(
    session: AsyncSession = Depends(get_db),
    broker: PriceEventBroker = Depends(get_price_broker),
    user: UserResponse = Depends(require_permission("approve:recommendation")),
) -> list[HedgeRecommendationResponse]:
    """Get all pending recommendations awaiting approval.
    
    Requires 'approve:recommendation' permission.
    """
    log.info("get_pending_recommendations", user_email=user.email)
    
    service = get_recommendation_service(session, broker)
    return await service.get_pending()


@router.get("/{recommendation_id}", response_model=HedgeRecommendationResponse)
async def get_recommendation(
    recommendation_id: UUID,
    session: AsyncSession = Depends(get_db),
    broker: PriceEventBroker = Depends(get_price_broker),
    user: UserResponse = Depends(get_current_user),
) -> HedgeRecommendationResponse:
    """Get a single recommendation by ID.
    
    All authenticated users can view recommendations.
    """
    log.info("get_recommendation", recommendation_id=str(recommendation_id), user_email=user.email)
    
    try:
        service = get_recommendation_service(session, broker)
        return await service.get_by_id(recommendation_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=RecommendationListResponse)
async def list_recommendations(
    page: int = 1,
    limit: int = 10,
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
    broker: PriceEventBroker = Depends(get_price_broker),
    user: UserResponse = Depends(get_current_user),
) -> RecommendationListResponse:
    """List recommendations with pagination.
    
    Optional status filter: PENDING, APPROVED, REJECTED, DEFERRED, EXPIRED, CONSTRAINT_VIOLATED.
    """
    log.info(
        "list_recommendations",
        page=page,
        limit=limit,
        status=status,
        user_email=user.email,
    )
    
    if limit > 100:
        raise HTTPException(status_code=400, detail="Maximum limit is 100")
    
    try:
        service = get_recommendation_service(session, broker)
        return await service.list_paginated(page=page, limit=limit, status=status)
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{recommendation_id}/approve", response_model=HedgeRecommendationResponse)
async def approve_recommendation(
    recommendation_id: UUID,
    payload: ApproveRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    broker: PriceEventBroker = Depends(get_price_broker),
    user: UserResponse = Depends(require_permission("approve:recommendation")),
) -> HedgeRecommendationResponse:
    """Approve a recommendation.
    
    Requires 'approve:recommendation' permission (risk_manager, cfo, admin).
    """
    log.info(
        "approve_recommendation",
        recommendation_id=str(recommendation_id),
        user_email=user.email,
    )
    
    try:
        service = get_recommendation_service(session, broker)
        result = await service.approve(
            recommendation_id=recommendation_id,
            approver_id=user.id,
            ip_address=request.client.host if request.client else "unknown",
            comments=payload.comments,
        )
        await session.commit()
        return result
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{recommendation_id}/reject", response_model=HedgeRecommendationResponse)
async def reject_recommendation(
    recommendation_id: UUID,
    payload: RejectRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    broker: PriceEventBroker = Depends(get_price_broker),
    user: UserResponse = Depends(require_permission("approve:recommendation")),
) -> HedgeRecommendationResponse:
    """Reject a recommendation.
    
    Requires 'approve:recommendation' permission (risk_manager, cfo, admin).
    """
    log.info(
        "reject_recommendation",
        recommendation_id=str(recommendation_id),
        user_email=user.email,
    )
    
    try:
        service = get_recommendation_service(session, broker)
        result = await service.reject(
            recommendation_id=recommendation_id,
            approver_id=user.id,
            ip_address=request.client.host if request.client else "unknown",
            reason=payload.reason,
        )
        await session.commit()
        return result
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{recommendation_id}/defer", response_model=HedgeRecommendationResponse)
async def defer_recommendation(
    recommendation_id: UUID,
    payload: DeferRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    broker: PriceEventBroker = Depends(get_price_broker),
    user: UserResponse = Depends(require_permission("approve:recommendation")),
) -> HedgeRecommendationResponse:
    """Defer a recommendation for later review.
    
    Requires 'approve:recommendation' permission (risk_manager, cfo, admin).
    """
    log.info(
        "defer_recommendation",
        recommendation_id=str(recommendation_id),
        user_email=user.email,
    )
    
    try:
        service = get_recommendation_service(session, broker)
        result = await service.defer(
            recommendation_id=recommendation_id,
            approver_id=user.id,
            ip_address=request.client.host if request.client else "unknown",
            reason=payload.reason,
        )
        await session.commit()
        return result
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# N8N WEBHOOK ENDPOINT (API key authentication)
# ============================================================


async def _resolve_run_id(run_id_str: str, analytics_repo: AnalyticsRepository) -> UUID:
    """Resolve run_id to a valid analytics_runs UUID.
    
    - If valid UUID and run exists: use it
    - Else (manual-xxx or invalid): get or create run for today
    """
    try:
        uid = UUID(run_id_str)
        existing = await analytics_repo.get_by_id(uid)
        if existing:
            return uid
    except (ValueError, TypeError):
        pass
    # Manual or invalid: use today's run or create
    run = await analytics_repo.get_or_create_manual_run(date.today())
    return run.id


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RecommendationCreatedResponse)
async def create_recommendation_from_n8n(
    payload: AgentOutputPayloadN8n,
    request: Request,
    n8n_key: str = Header(alias="X-N8N-API-Key"),
    session: AsyncSession = Depends(get_db),
    broker: PriceEventBroker = Depends(get_price_broker),
    settings: Settings = Depends(get_settings),
) -> RecommendationCreatedResponse:
    """N8N webhook endpoint — create recommendation from AI agent committee.
    
    This endpoint is called by n8n after:
    1. All 5 AI agents complete their analysis
    2. Committee synthesizer aggregates results
    3. CRO risk gate validates constraints
    4. Payload is assembled
    
    Accepts n8n flat payload format. run_id can be UUID or manual-{timestamp}.
    Authentication: X-N8N-API-Key header (constant-time comparison).
    """
    log.info(
        "n8n_webhook_received",
        run_id=payload.run_id,
        agent_count=len(payload.agent_outputs),
    )

    # Validate API key using constant-time comparison
    if not hmac.compare_digest(n8n_key, settings.N8N_WEBHOOK_SECRET):
        log.error(
            "n8n_authentication_failed",
            ip=request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid n8n API key",
        )

    try:
        analytics_repo = AnalyticsRepository(session)
        resolved_run_id = await _resolve_run_id(payload.run_id, analytics_repo)
        internal_payload = payload.to_agent_output_payload(resolved_run_id)

        service = get_recommendation_service(session, broker)
        recommendation = await service.create_from_n8n(internal_payload)
        await session.commit()

        log.info(
            "recommendation_created_from_n8n",
            recommendation_id=str(recommendation.id),
            sequence_number=recommendation.sequence_number,
            status=recommendation.status,
        )

        return RecommendationCreatedResponse(
            recommendation_id=recommendation.id,
            status=recommendation.status,
            sequence_number=recommendation.sequence_number,
            expires_at=recommendation.expires_at or datetime.now(timezone.utc),
            message=f"Recommendation #{recommendation.sequence_number} created successfully",
        )

    except DataIngestionError as e:
        log.error("n8n_webhook_processing_failed", error=str(e), source=e.source)
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.error("n8n_webhook_unexpected_error", error=str(e))
        await session.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# INTERNAL ENDPOINTS (APScheduler trigger)
# ============================================================


@router.post("/internal/n8n-trigger", include_in_schema=False)
async def trigger_n8n_workflow(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Internal endpoint called by APScheduler or pipeline to trigger n8n workflow.
    
    Expects JSON body: { run_id, analytics_summary?, trigger_type? }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    run_id = body.get("run_id", "scheduled-run")
    analytics_summary = body.get("analytics_summary", {})
    trigger_type = body.get("trigger_type", "scheduled")

    n8n_url = settings.N8N_TRIGGER_URL or f"{settings.N8N_INTERNAL_URL.rstrip('/')}{settings.N8N_TRIGGER_PATH}"
    log.info("triggering_n8n_workflow", run_id=run_id, target_host=n8n_url.split("/")[2] if "//" in n8n_url else "unknown")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                n8n_url,
                json={
                    "run_id": run_id,
                    "analytics_summary": analytics_summary,
                    "trigger_type": trigger_type,
                    "triggered_at": datetime.now(timezone.utc).isoformat(),
                },
                headers={"X-N8N-API-Key": settings.N8N_WEBHOOK_SECRET},
            )
            response.raise_for_status()

            log.info(
                "n8n_workflow_triggered",
                run_id=run_id,
                status_code=response.status_code,
            )

            return {
                "triggered": True,
                "run_id": run_id,
                "status_code": response.status_code,
            }

    except httpx.HTTPStatusError as e:
        log.error(
            "n8n_trigger_http_error",
            status_code=e.response.status_code,
            body=e.response.text,
            run_id=run_id,
        )
        raise DataIngestionError(
            f"n8n trigger failed: HTTP {e.response.status_code} - {e.response.text}",
            source="n8n_trigger",
        ) from e
    except httpx.RequestError as e:
        log.error(
            "n8n_trigger_request_error",
            error=str(e),
            run_id=run_id,
            target_url=n8n_url,
            hint="Set N8N_TRIGGER_URL to the exact n8n webhook URL from Render dashboard (e.g. https://hedge-n8n-xxx.onrender.com/webhook/fuel-hedge-trigger)",
        )
        raise DataIngestionError(
            f"n8n trigger network error: {e}. Set N8N_TRIGGER_URL to the exact n8n URL from Render.",
            source="n8n_trigger",
        ) from e
