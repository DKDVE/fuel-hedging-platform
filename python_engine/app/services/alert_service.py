"""
alert_service.py

Monitors platform metrics and creates alerts when thresholds are exceeded.
Deduplicates alerts: the same alert_type is not re-created within 1 hour.
Publishes new alerts via PriceService so connected SSE clients are notified immediately.
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    COLLATERAL_LIMIT,
    HR_HARD_CAP,
    HR_SOFT_WARN,
    IFRS9_R2_MIN_PROSPECTIVE,
    IFRS9_R2_WARN,
    MAPE_ALERT,
    MAPE_TARGET,
)
from app.core.units import normalize_ratio_value
from app.db.models import Alert, AlertSeverity, AlertType
from app.services.price_service import get_price_service

log = structlog.get_logger()


class AlertService:
    """Monitors metrics and creates alerts when thresholds are exceeded."""

    def __init__(self) -> None:
        self._price_service = get_price_service()

    async def check_all(
        self,
        db: AsyncSession,
        latest_run: object | None,
        pending_recs: list[object],
    ) -> None:
        """
        Run all threshold checks. Call from the 15-minute scheduler job.
        Creates alerts for any violations found. Deduplicates within 1 hour.
        """
        if latest_run:
            await self._check_var(db, latest_run)
            await self._check_collateral(db, latest_run)
            await self._check_mape(db, latest_run)
            await self._check_ifrs9(db, latest_run)
            await self._check_hr(db, latest_run)

        await self._check_recommendation_sla(db, pending_recs)
        await self._check_price_spike(db)

    async def _create_alert(
        self,
        db: AsyncSession,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        metric_value: float | None = None,
        threshold_value: float | None = None,
    ) -> Alert | None:
        """
        Create alert. Returns None if a duplicate exists within 1 hour (dedup).
        """
        dedup_key = f"{alert_type.value}:{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"
        existing = await db.execute(
            select(Alert).where(Alert.dedup_key == dedup_key).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            return None

        alert = Alert(
            id=uuid4(),
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            metric_value=metric_value,
            threshold_value=threshold_value,
            dedup_key=dedup_key,
        )
        db.add(alert)
        await db.flush()
        await db.refresh(alert)

        # Publish via price service so connected clients get notified
        self._price_service.publish_alert({
            "type": "alert",
            "id": str(alert.id),
            "alert_type": alert_type.value,
            "severity": severity.value,
            "title": title,
            "message": message,
            "created_at": alert.created_at.isoformat(),
        })

        log.info("alert_created", alert_type=alert_type.value, severity=severity.value)
        return alert

    async def _check_var(self, db: AsyncSession, run: object) -> None:
        var_results = getattr(run, "var_results", None) or {}
        var_usd = float(var_results.get("var_usd", 0) or 0)
        var_limit = 5_000_000
        if var_usd > var_limit * 0.80:
            pct = var_usd / var_limit * 100
            severity = AlertSeverity.CRITICAL if pct > 95 else AlertSeverity.WARNING
            await self._create_alert(
                db,
                AlertType.VAR_APPROACHING_LIMIT,
                severity,
                title=f"VaR at {pct:.0f}% of limit",
                message=(
                    f"Portfolio VaR is ${var_usd/1e6:.2f}M, approaching the "
                    f"${var_limit/1e6:.0f}M limit ({pct:.0f}% utilised). "
                    "Consider reducing hedge ratio or notional exposure."
                ),
                metric_value=var_usd,
                threshold_value=var_limit * 0.80,
            )

    async def _check_collateral(self, db: AsyncSession, run: object) -> None:
        opt = getattr(run, "optimizer_result", None) or {}
        collateral_ratio = normalize_ratio_value(opt.get("collateral_pct_of_reserves", 0) or 0)
        if collateral_ratio > 0.13:
            severity = AlertSeverity.CRITICAL if collateral_ratio > 0.145 else AlertSeverity.WARNING
            await self._create_alert(
                db,
                AlertType.COLLATERAL_HIGH,
                severity,
                title=f"Collateral at {collateral_ratio*100:.1f}% of reserves",
                message=(
                    f"Collateral utilisation ({collateral_ratio*100:.1f}%) is "
                    f"approaching the {COLLATERAL_LIMIT*100:.0f}% limit. "
                    "New positions may be restricted."
                ),
                metric_value=collateral_ratio,
                threshold_value=COLLATERAL_LIMIT,
            )

    async def _check_mape(self, db: AsyncSession, run: object) -> None:
        mape = float(getattr(run, "mape", 0) or 0)
        if mape > MAPE_ALERT:
            await self._create_alert(
                db,
                AlertType.MAPE_DEGRADED,
                AlertSeverity.WARNING,
                title=f"Forecast accuracy degraded: MAPE {mape:.1f}%",
                message=(
                    f"Ensemble forecast MAPE ({mape:.1f}%) exceeds the "
                    f"{MAPE_ALERT:.0f}% alert threshold (target: {MAPE_TARGET:.0f}%). "
                    "Model retraining is recommended."
                ),
                metric_value=mape,
                threshold_value=MAPE_ALERT,
            )

    async def _check_ifrs9(self, db: AsyncSession, run: object) -> None:
        basis = getattr(run, "basis_metrics", None) or {}
        r2 = float(basis.get("r2_heating_oil", 1.0) or 1.0)
        if r2 < IFRS9_R2_MIN_PROSPECTIVE:
            await self._create_alert(
                db,
                AlertType.IFRS9_WARNING,
                AlertSeverity.CRITICAL,
                title=f"IFRS 9 R² below minimum: {r2:.4f}",
                message=(
                    f"Heating oil R² ({r2:.4f}) has fallen below the IFRS 9 "
                    f"minimum of {IFRS9_R2_MIN_PROSPECTIVE}. "
                    "Hedge de-designation may be required. Consult your accountant."
                ),
                metric_value=r2,
                threshold_value=IFRS9_R2_MIN_PROSPECTIVE,
            )
        elif r2 < IFRS9_R2_WARN + 0.05:
            await self._create_alert(
                db,
                AlertType.IFRS9_WARNING,
                AlertSeverity.WARNING,
                title=f"IFRS 9 R² approaching threshold: {r2:.4f}",
                message=(
                    f"Heating oil R² ({r2:.4f}) is approaching the IFRS 9 "
                    f"minimum of {IFRS9_R2_MIN_PROSPECTIVE}. Monitor closely."
                ),
                metric_value=r2,
                threshold_value=IFRS9_R2_MIN_PROSPECTIVE,
            )

    async def _check_hr(self, db: AsyncSession, run: object) -> None:
        opt = getattr(run, "optimizer_result", None) or {}
        hr = float(opt.get("optimal_hr", 0) or 0)
        if hr > HR_SOFT_WARN:
            severity = (
                AlertSeverity.CRITICAL if hr > HR_HARD_CAP * 0.97 else AlertSeverity.WARNING
            )
            await self._create_alert(
                db,
                AlertType.HR_APPROACHING_CAP,
                severity,
                title=f"Hedge ratio at {hr*100:.1f}% — approaching cap",
                message=(
                    f"Recommended hedge ratio ({hr*100:.1f}%) exceeds the "
                    f"{HR_SOFT_WARN*100:.0f}% soft warning threshold. "
                    "Marginal VaR reduction is diminishing (H1 hypothesis)."
                ),
                metric_value=hr,
                threshold_value=HR_HARD_CAP,
            )

    async def _check_recommendation_sla(
        self, db: AsyncSession, pending_recs: list[object]
    ) -> None:
        now = datetime.now(timezone.utc)
        for rec in pending_recs:
            created_at = getattr(rec, "created_at", now)
            if hasattr(created_at, "tzinfo") and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_hours = (now - created_at).total_seconds() / 3600
            if age_hours > 4:
                seq = getattr(rec, "sequence_number", "?")
                await self._create_alert(
                    db,
                    AlertType.RECOMMENDATION_SLA,
                    AlertSeverity.WARNING,
                    title=f"Recommendation #{seq} SLA exceeded",
                    message=(
                        f"Recommendation #{seq} has been pending "
                        f"{age_hours:.1f} hours (SLA: 4 hours). "
                        "Escalation is required."
                    ),
                    metric_value=age_hours,
                    threshold_value=4.0,
                )

    async def _check_price_spike(self, db: AsyncSession) -> None:
        last_tick = self._price_service.get_last_tick()
        if last_tick and last_tick.volatility_index > 25:
            await self._create_alert(
                db,
                AlertType.PRICE_SPIKE,
                AlertSeverity.WARNING,
                title=f"Elevated price volatility: {last_tick.volatility_index:.1f}%",
                message=(
                    f"Current volatility index ({last_tick.volatility_index:.1f}%) "
                    "is elevated. Monitor hedge positions closely."
                ),
                metric_value=last_tick.volatility_index,
                threshold_value=25.0,
            )
