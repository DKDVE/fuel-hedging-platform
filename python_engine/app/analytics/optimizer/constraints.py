"""Constraint definitions for hedge optimization.

Constraints are loaded from database at runtime, allowing admin
to update limits without redeployment.
"""

from typing import Any


def build_optimizer_constraints(
    config_snapshot: dict[str, float],
    cash_reserves: float,
    forecast_consumption_bbl: float,
) -> dict[str, Any]:
    """Build constraint dictionary for optimizer.
    
    Args:
        config_snapshot: Runtime constraints from ConfigRepository:
            {'hr_cap': 0.80, 'collateral_limit': 0.15, ...}
        cash_reserves: Available cash reserves (USD)
        forecast_consumption_bbl: Forecasted fuel consumption (barrels)
    
    Returns:
        Constraint dictionary for scipy optimizer
    """
    hr_cap = config_snapshot["hr_cap"]
    collateral_limit = config_snapshot["collateral_limit"]
    max_coverage = config_snapshot.get("max_coverage_ratio", 1.10)

    constraints = {
        # Hedge ratio bounds
        "hr_min": 0.0,
        "hr_max": hr_cap,
        
        # Collateral limit (% of cash reserves)
        "collateral_limit_pct": collateral_limit,
        "cash_reserves_usd": cash_reserves,
        
        # Coverage ratio (prevent over-hedging)
        "max_coverage_ratio": max_coverage,
        "forecast_consumption_bbl": forecast_consumption_bbl,
        
        # Instrument mix must sum to 1.0
        "instrument_sum_min": 0.999,
        "instrument_sum_max": 1.001,
        
        # Proxy weights must sum to 1.0
        "proxy_sum_min": 0.999,
        "proxy_sum_max": 1.001,
        
        # Individual instrument bounds
        "futures_min": 0.0,
        "futures_max": 1.0,
        "options_min": 0.0,
        "options_max": 0.50,  # Max 50% in options
        "collars_min": 0.0,
        "collars_max": 0.30,  # Max 30% in collars
        "swaps_min": 0.0,
        "swaps_max": 0.20,   # Max 20% in swaps
        
        # Proxy bounds
        "heating_oil_min": 0.0,
        "heating_oil_max": 1.0,
        "brent_min": 0.0,
        "brent_max": 1.0,
        "wti_min": 0.0,
        "wti_max": 1.0,
    }

    return constraints


def validate_solution_constraints(
    hedge_ratio: float,
    instrument_mix: dict[str, float],
    proxy_weights: dict[str, float],
    collateral_usd: float,
    constraints: dict[str, Any],
) -> list[str]:
    """Validate that a solution satisfies all constraints.
    
    Args:
        hedge_ratio: Proposed hedge ratio
        instrument_mix: Proposed instrument allocation
        proxy_weights: Proposed proxy weights
        collateral_usd: Required collateral
        constraints: Constraint dictionary
    
    Returns:
        List of violated constraint names (empty if all satisfied)
    """
    violations = []

    # Hedge ratio constraints
    if hedge_ratio < constraints["hr_min"]:
        violations.append(f"hedge_ratio_below_min_{hedge_ratio:.4f}")
    if hedge_ratio > constraints["hr_max"]:
        violations.append(f"hedge_ratio_above_max_{hedge_ratio:.4f}")

    # Collateral constraint
    collateral_limit_usd = (
        constraints["cash_reserves_usd"] * constraints["collateral_limit_pct"]
    )
    if collateral_usd > collateral_limit_usd:
        violations.append(
            f"collateral_exceeds_limit_{collateral_usd:.0f}_gt_{collateral_limit_usd:.0f}"
        )

    # Instrument mix sum
    instrument_sum = sum(instrument_mix.values())
    if not (constraints["instrument_sum_min"] <= instrument_sum <= constraints["instrument_sum_max"]):
        violations.append(f"instrument_mix_sum_invalid_{instrument_sum:.4f}")

    # Proxy weights sum
    proxy_sum = sum(proxy_weights.values())
    if not (constraints["proxy_sum_min"] <= proxy_sum <= constraints["proxy_sum_max"]):
        violations.append(f"proxy_weights_sum_invalid_{proxy_sum:.4f}")

    # Individual instrument bounds
    for instrument, weight in instrument_mix.items():
        min_key = f"{instrument}_min"
        max_key = f"{instrument}_max"
        if min_key in constraints and weight < constraints[min_key]:
            violations.append(f"{instrument}_below_min_{weight:.4f}")
        if max_key in constraints and weight > constraints[max_key]:
            violations.append(f"{instrument}_above_max_{weight:.4f}")

    # Individual proxy bounds
    for proxy, weight in proxy_weights.items():
        min_key = f"{proxy}_min"
        max_key = f"{proxy}_max"
        if min_key in constraints and weight < constraints[min_key]:
            violations.append(f"{proxy}_below_min_{weight:.4f}")
        if max_key in constraints and weight > constraints[max_key]:
            violations.append(f"{proxy}_above_max_{weight:.4f}")

    return violations
