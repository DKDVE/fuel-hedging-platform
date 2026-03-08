"""Domain constants for the fuel hedging platform.

All values are sourced from Phase 1-2 Report, Phase 3 Methodology, and IFRS 9 standards.
These constants must NEVER be inlined in code — always import from this module.
"""

# === Hedge Ratio Constraints ===

HR_HARD_CAP: float = 0.80
"""Maximum hedge ratio allowed (regulatory hard limit).
Source: Phase 1 Report - regulatory constraint from airline's risk policy."""

HR_SOFT_WARN: float = 0.70
"""Hedge ratio threshold for diminishing returns warning.
Source: H1 hypothesis - marginal VaR reduction drops significantly above 70%."""

# === Collateral Constraints ===

COLLATERAL_LIMIT: float = 0.15
"""Maximum collateral as percentage of cash reserves.
Source: Phase 1 Report - treasury constraint to maintain liquidity."""

# === IFRS 9 Hedge Accounting Thresholds ===

IFRS9_R2_MIN_PROSPECTIVE: float = 0.80
"""Minimum R² for prospective hedge effectiveness (hedge designation).
Source: IFRS 9 standard - 80% correlation required for hedge accounting eligibility."""

IFRS9_R2_WARN: float = 0.65
"""R² warning threshold - below this triggers dedesignation risk alert.
Source: Phase 2 Report - early warning system for hedge effectiveness degradation."""

IFRS9_RETRO_LOW: float = 0.80
"""Retrospective effectiveness lower bound (80% offset ratio).
Source: IFRS 9 standard - actual hedge must offset 80-125% of hedged item changes."""

IFRS9_RETRO_HIGH: float = 1.25
"""Retrospective effectiveness upper bound (125% offset ratio).
Source: IFRS 9 standard - actual hedge must offset 80-125% of hedged item changes."""

# === Forecast Model Performance ===

MAPE_TARGET: float = 8.0
"""Target Mean Absolute Percentage Error for ensemble forecaster.
Source: Phase 2 Report - ensemble model validated at 7.2% MAPE on 2024 data."""

MAPE_ALERT: float = 10.0
"""MAPE threshold for model degradation alert.
Source: Phase 3 Methodology - trigger model retraining when MAPE exceeds 10%."""

# === Risk Management Targets ===

VAR_REDUCTION_TARGET: float = 0.40
"""Target VaR reduction vs unhedged position (40%).
Source: H2 hypothesis - optimal hedging achieves 38.7% VaR reduction."""

MAX_COVERAGE_RATIO: float = 1.10
"""Maximum hedge coverage ratio to prevent over-hedging (110% of forecast consumption).
Source: Phase 1 Report - operational constraint to avoid speculative positions."""

# === Pipeline SLAs ===

PIPELINE_TIMEOUT_MINUTES: int = 15
"""Maximum allowed duration for daily analytics pipeline.
Source: Phase 3 Methodology - pipeline must complete before market open."""
