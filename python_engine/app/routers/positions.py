"""Positions API endpoints.

Provides access to hedge positions from approved recommendations.
"""

from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import AnalystUser, DatabaseSession
from app.repositories import PositionRepository
from app.repositories.market_data import MarketDataRepository
from app.db.models import HedgePosition, PositionStatus
from app.services.price_service import get_price_service

router = APIRouter()


def _calculate_position_pnl(
    position: HedgePosition,
    current_price: float,
) -> dict[str, Any]:
    """
    Calculate mark-to-market P&L for a single hedge position.

    For FUTURES:
      pnl = (entry_price - current_price) × (notional_usd / entry_price) × hedge_ratio
      Positive = gain (price fell = futures short gains value)

    For OPTIONS (bought put):
      pnl = max(0, entry_price - current_price) × (notional_usd / entry_price) × hedge_ratio
      Approximation — full Black-Scholes not required

    Cash savings = (current_price - entry_price) × (notional_usd / entry_price) × hedge_ratio
    If positive: spot is higher than entry = hedge is saving money
    """
    entry = float(position.entry_price)
    notional = float(position.notional_usd)
    hr = float(position.hedge_ratio)
    notional_bbls = notional / entry if entry > 0 else 0.0
    price_diff = entry - current_price  # positive = hedge is valuable

    if position.instrument_type.value == "FUTURES":
        pnl_usd = price_diff * notional_bbls * hr
    elif position.instrument_type.value in ("OPTIONS", "COLLAR"):
        intrinsic = max(0.0, price_diff)
        pnl_usd = intrinsic * notional_bbls * hr
    else:  # SWAP
        pnl_usd = price_diff * notional_bbls * hr

    cash_savings_usd = (current_price - entry) * notional_bbls * hr
    pnl_pct = (pnl_usd / notional * 100) if notional else 0.0

    return {
        "mtm_pnl_usd": round(pnl_usd, 2),
        "mtm_pnl_pct": round(pnl_pct, 4),
        "cash_savings_usd": round(cash_savings_usd, 2),
        "current_price": current_price,
        "price_change_usd": round(current_price - entry, 2),
        "is_profitable": pnl_usd > 0,
    }


@router.get("", response_model=dict)
async def list_positions(
    current_user: AnalystUser,
    db: DatabaseSession,
    status: Optional[str] = Query(None, description="Filter by status: OPEN, CLOSED, EXPIRED"),
    include_closed: bool = Query(True, description="Include closed/rolled positions"),
) -> dict:
    """List hedge positions. Returns real data from database; empty when no positions exist."""
    repo = PositionRepository(db)
    market_repo = MarketDataRepository(db)

    if status and status.upper() in ("OPEN", "CLOSED", "EXPIRED"):
        positions = await repo.get_positions_by_status(PositionStatus(status.upper()))
    elif include_closed:
        open_pos = await repo.get_open_positions()
        closed_pos = await repo.get_positions_by_status(PositionStatus.CLOSED)
        expired_pos = await repo.get_positions_by_status(PositionStatus.EXPIRED)
        positions = open_pos + closed_pos + expired_pos
    else:
        positions = await repo.get_open_positions()

    # Get current jet fuel price for P&L (PriceService first, then DB)
    current_price: Optional[float] = None
    last_tick = get_price_service().get_last_tick()
    if last_tick:
        current_price = last_tick.jet_fuel_spot
    if current_price is None:
        db_tick = await market_repo.get_latest_tick()
        if db_tick:
            current_price = float(db_tick.jet_fuel_spot)

    total_collateral = await repo.get_total_open_collateral()
    reserves = 15_000_000.0  # from platform config
    limit_pct = 15.0
    utilization = (total_collateral / reserves * 100) if reserves > 0 else 0.0

    items = []
    total_pnl = 0.0
    total_savings = 0.0
    open_count = 0

    for p in positions:
        price_for_pnl = current_price if current_price is not None else float(p.entry_price)
        pnl_data = _calculate_position_pnl(p, price_for_pnl)

        # Only include P&L for OPEN positions in portfolio totals
        if p.status == PositionStatus.OPEN:
            total_pnl += pnl_data["mtm_pnl_usd"]
            total_savings += pnl_data["cash_savings_usd"]
            open_count += 1

        items.append({
            "id": str(p.id),
            "instrument_type": p.instrument_type.value,
            "proxy": p.proxy,
            "notional_usd": float(p.notional_usd),
            "hedge_ratio": float(p.hedge_ratio),
            "entry_price": float(p.entry_price),
            "expiry_date": str(p.expiry_date),
            "collateral_usd": float(p.collateral_usd),
            "ifrs9_r2": float(p.ifrs9_r2),
            "status": p.status.value,
            "mtm_pnl_usd": pnl_data["mtm_pnl_usd"],
            "mtm_pnl_pct": pnl_data["mtm_pnl_pct"],
            "cash_savings_usd": pnl_data["cash_savings_usd"],
            "current_price": pnl_data["current_price"],
            "price_change_usd": pnl_data["price_change_usd"],
            "is_profitable": pnl_data["is_profitable"],
        })

    total_open_notional = sum(float(p.notional_usd) for p in positions if p.status == PositionStatus.OPEN)
    avg_pnl_pct = (total_pnl / total_open_notional * 100) if total_open_notional else 0.0

    return {
        "items": items,
        "collateral_summary": {
            "total_usd": total_collateral,
            "reserves_usd": reserves,
            "utilization_pct": round(utilization, 2),
            "limit_pct": limit_pct,
            "available_capacity_usd": max(0, reserves * (limit_pct / 100) - total_collateral),
        },
        "portfolio_pnl": {
            "total_mtm_pnl_usd": round(total_pnl, 2),
            "total_cash_savings_usd": round(total_savings, 2),
            "avg_pnl_pct": round(avg_pnl_pct, 4),
        },
    }
