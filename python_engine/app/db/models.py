"""SQLAlchemy ORM models for the fuel hedging platform.

All models inherit from Base and include automatic UUID PKs and timestamps.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ===== ENUMS =====


class UserRole(str, enum.Enum):
    """User role types with specific permissions."""

    ANALYST = "analyst"
    RISK_MANAGER = "risk_manager"
    CFO = "cfo"
    ADMIN = "admin"


class RecommendationStatus(str, enum.Enum):
    """Hedge recommendation workflow states."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"
    EXPIRED = "EXPIRED"
    CONSTRAINT_VIOLATED = "CONSTRAINT_VIOLATED"


class DecisionType(str, enum.Enum):
    """Approval decision types."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"
    DEFER = "DEFER"


class InstrumentType(str, enum.Enum):
    """Financial instrument types for hedging."""

    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"
    COLLAR = "COLLAR"
    SWAP = "SWAP"


class AnalyticsRunStatus(str, enum.Enum):
    """Analytics pipeline run states."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PositionStatus(str, enum.Enum):
    """Hedge position lifecycle states."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


class AlertSeverity(str, enum.Enum):
    """Alert severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertType(str, enum.Enum):
    """Types of platform alerts."""

    VAR_APPROACHING_LIMIT = "VAR_APPROACHING_LIMIT"
    COLLATERAL_HIGH = "COLLATERAL_HIGH"
    MAPE_DEGRADED = "MAPE_DEGRADED"
    RECOMMENDATION_SLA = "RECOMMENDATION_SLA"
    PRICE_SPIKE = "PRICE_SPIKE"
    PIPELINE_FAILED = "PIPELINE_FAILED"
    IFRS9_WARNING = "IFRS9_WARNING"
    HR_APPROACHING_CAP = "HR_APPROACHING_CAP"


# ===== MODELS =====


class User(Base):
    """Application users with role-based access control.
    
    Roles determine permissions via ROLE_PERMISSIONS mapping in auth module.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    approvals: Mapped[list["Approval"]] = relationship(back_populates="approver")
    config_updates: Mapped[list["PlatformConfig"]] = relationship(back_populates="updater")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")

    @property
    def full_name(self) -> str:
        """Full name for API responses (not stored; returns email prefix)."""
        return self.email.split("@")[0] if self.email else ""

    def __repr__(self) -> str:
        return f"<User(email={self.email}, role={self.role.value}, active={self.is_active})>"


class PlatformConfig(Base):
    """Platform configuration key-value store.
    
    Stores runtime configuration like HR cap, collateral limits, etc.
    Admin can update via UI without redeployment.
    """

    __tablename__ = "platform_config"

    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    updater: Mapped["User"] = relationship(back_populates="config_updates")

    __table_args__ = (
        CheckConstraint(
            "key IN ('hr_cap', 'collateral_limit', 'ifrs9_r2_min', 'mape_target', "
            "'var_reduction_target', 'max_coverage_ratio', 'pipeline_timeout')",
            name="valid_config_keys",
        ),
    )

    def __repr__(self) -> str:
        return f"<PlatformConfig(key={self.key})>"


class PriceTick(Base):
    """Market price observations (TimescaleDB hypertable).
    
    Partitioned by time for efficient querying of time-series data.
    Composite PK (time, id) required by TimescaleDB for hypertable partitioning.
    """

    __tablename__ = "price_ticks"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        primary_key=True,
    )
    jet_fuel_spot: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    heating_oil_futures: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    brent_futures: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    wti_futures: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    crack_spread: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    volatility_index: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    quality_flag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="API")

    __table_args__ = (
        UniqueConstraint("time", "source", name="unique_tick_time_source"),
        Index("idx_price_ticks_time_desc", "time", postgresql_ops={"time": "DESC"}),
        CheckConstraint("jet_fuel_spot > 0", name="positive_jet_fuel"),
        CheckConstraint("heating_oil_futures > 0", name="positive_heating_oil"),
        CheckConstraint("brent_futures > 0", name="positive_brent"),
        CheckConstraint("wti_futures > 0", name="positive_wti"),
    )

    def __repr__(self) -> str:
        return f"<PriceTick(time={self.time}, jet_fuel={self.jet_fuel_spot})>"


class AnalyticsRun(Base):
    """Daily analytics pipeline execution record.
    
    Stores all results from forecasting, VaR, basis analysis, and optimization.
    """

    __tablename__ = "analytics_runs"

    run_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    mape: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    forecast_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    var_results: Mapped[dict] = mapped_column(JSONB, nullable=False)
    basis_metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    optimizer_result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model_versions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    duration_seconds: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[AnalyticsRunStatus] = mapped_column(
        Enum(AnalyticsRunStatus),
        nullable=False,
    )

    # Relationships
    recommendations: Mapped[list["HedgeRecommendation"]] = relationship(
        back_populates="analytics_run"
    )

    __table_args__ = (
        CheckConstraint("mape >= 0 AND mape <= 100", name="valid_mape"),
        CheckConstraint("duration_seconds > 0", name="positive_duration"),
    )

    def __repr__(self) -> str:
        return f"<AnalyticsRun(date={self.run_date}, mape={self.mape}, status={self.status.value})>"


class HedgeRecommendation(Base):
    """Hedge recommendation from n8n agents awaiting approval.
    
    Contains optimizer output + agent consensus + risk metrics.
    """

    __tablename__ = "hedge_recommendations"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analytics_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    optimal_hr: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    instrument_mix: Mapped[dict] = mapped_column(JSONB, nullable=False)
    proxy_weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    var_hedged: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    var_unhedged: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    var_reduction_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    collateral_usd: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    agent_outputs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus),
        nullable=False,
        default=RecommendationStatus.PENDING,
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        autoincrement=True,
    )
    escalation_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    analytics_run: Mapped["AnalyticsRun"] = relationship(back_populates="recommendations")
    approvals: Mapped[list["Approval"]] = relationship(back_populates="recommendation")
    positions: Mapped[list["HedgePosition"]] = relationship(back_populates="recommendation")

    __table_args__ = (
        CheckConstraint("optimal_hr >= 0 AND optimal_hr <= 0.80", name="hr_within_cap"),
        CheckConstraint("var_reduction_pct >= 0 AND var_reduction_pct <= 100", name="valid_var_reduction"),
        CheckConstraint("collateral_usd >= 0", name="non_negative_collateral"),
        Index("idx_recommendations_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<HedgeRecommendation(seq={self.sequence_number}, hr={self.optimal_hr}, status={self.status.value})>"


class Approval(Base):
    """Approval/rejection decision record with response time tracking."""

    __tablename__ = "approvals"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hedge_recommendations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision: Mapped[DecisionType] = mapped_column(Enum(DecisionType), nullable=False)
    response_lag_minutes: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str] = mapped_column(INET, nullable=False)

    # Relationships
    recommendation: Mapped["HedgeRecommendation"] = relationship(back_populates="approvals")
    approver: Mapped["User"] = relationship(back_populates="approvals")

    __table_args__ = (
        CheckConstraint("response_lag_minutes >= 0", name="non_negative_response_lag"),
    )

    def __repr__(self) -> str:
        return f"<Approval(decision={self.decision.value}, lag={self.response_lag_minutes}min)>"


class HedgePosition(Base):
    """Active or historical hedge position created from approved recommendation."""

    __tablename__ = "hedge_positions"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hedge_recommendations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    instrument_type: Mapped[InstrumentType] = mapped_column(Enum(InstrumentType), nullable=False)
    proxy: Mapped[str] = mapped_column(String(50), nullable=False)
    notional_usd: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    hedge_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    collateral_usd: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    ifrs9_r2: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    status: Mapped[PositionStatus] = mapped_column(
        Enum(PositionStatus),
        nullable=False,
        default=PositionStatus.OPEN,
    )

    # Relationships
    recommendation: Mapped["HedgeRecommendation"] = relationship(back_populates="positions")

    __table_args__ = (
        CheckConstraint("notional_usd > 0", name="positive_notional"),
        CheckConstraint("hedge_ratio >= 0 AND hedge_ratio <= 1.0", name="valid_hedge_ratio"),
        CheckConstraint("entry_price > 0", name="positive_entry_price"),
        CheckConstraint("collateral_usd >= 0", name="non_negative_collateral"),
        CheckConstraint("ifrs9_r2 >= 0 AND ifrs9_r2 <= 1.0", name="valid_r2"),
        Index("idx_positions_status_expiry", "status", "expiry_date"),
    )

    def __repr__(self) -> str:
        return f"<HedgePosition(type={self.instrument_type.value}, notional={self.notional_usd}, status={self.status.value})>"


class Alert(Base):
    """
    Platform alert generated when a monitored metric crosses a threshold.
    Displayed in the notification bell. Persisted for audit history.
    """

    __tablename__ = "alerts"

    alert_type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, name="alerttype", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alertseverity", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    threshold_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    is_acknowledged: Mapped[bool] = mapped_column(default=False, index=True)
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dedup_key: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        Index("idx_alerts_created_at_desc", "created_at", postgresql_ops={"created_at": "DESC"}),
    )


class AuditLog(Base):
    """Audit trail for all state-changing actions.
    
    Immutable record for compliance and forensics.
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    before_state: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ip_address: Mapped[str] = mapped_column(INET, nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs", lazy="selectin")

    __table_args__ = (
        Index("idx_audit_created_at_desc", "created_at", postgresql_ops={"created_at": "DESC"}),
        Index("idx_audit_action_created", "action", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(action={self.action}, resource={self.resource_type}, time={self.created_at})>"


class BacktestRun(Base):
    """Pre-computed walk-forward backtest results.

    Stores weekly backtest results and summary for the Analytics Backtesting tab.
    """

    __tablename__ = "backtest_runs"

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    notional_usd: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    weekly_results: Mapped[dict] = mapped_column(JSONB, nullable=False)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    dataset_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<BacktestRun(computed_at={self.computed_at}, notional={self.notional_usd})>"
