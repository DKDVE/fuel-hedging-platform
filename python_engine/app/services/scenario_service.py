"""
scenario_service.py

Runs the optimizer against stressed market conditions.
Pure simulation — does not write to DB, does not create recommendations.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from app.analytics import HedgeOptimizer, HistoricalSimVaR
from app.analytics.optimizer import build_optimizer_constraints
from app.analytics.scenarios import StressScenario


class ScenarioService:
    """
    Runs the optimizer against stressed market conditions.
    Pure simulation — does not write to DB, does not create recommendations.
    """

    def __init__(self) -> None:
        self._optimizer = HedgeOptimizer()
        self._var_engine = HistoricalSimVaR(confidence=0.95, holding_period_days=30)

    def run_scenario(
        self,
        scenario: StressScenario,
        current_price: float,
        historical_df: pd.DataFrame,
        constraints: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Apply scenario shock to current price and run optimizer.

        Returns a dict with:
        - scenario: scenario metadata
        - stressed_prices: what prices look like under this scenario
        - optimizer_result: recommended strategy
        - var_impact: VaR under stressed conditions
        - risk_narrative: plain-English explanation of results
        """
        stressed_price = current_price * (1 + scenario.price_shock_pct)
        notional_usd = 10_000_000  # Default notional for scenario simulation

        # Build stressed dataset: apply shock to most recent N rows
        stressed_df = historical_df.copy()
        jet_col = "Jet_Fuel_Spot_USD_bbl"
        if jet_col not in stressed_df.columns:
            jet_col = next((c for c in stressed_df.columns if "jet" in c.lower() or "Jet" in c), jet_col)
        if jet_col in stressed_df.columns:
            n_shock_rows = min(scenario.duration_days, len(stressed_df))
            shock_factor = 1 + scenario.price_shock_pct
            col_idx = stressed_df.columns.get_loc(jet_col)
            stressed_df.iloc[-n_shock_rows:, col_idx] *= shock_factor

        # Run VaR curve on stressed data
        var_curve = self._var_engine.var_curve(stressed_df, float(notional_usd))
        var_metrics = {f"hr_{int(v.hedge_ratio * 100)}": v.var_usd for v in var_curve}

        # Run optimizer
        opt_result = self._optimizer.optimize(var_metrics, constraints)

        # Get stressed VaR at optimal HR
        stressed_var = next(
            (r for r in var_curve if abs(r.hedge_ratio - opt_result.optimal_hr) < 0.05),
            var_curve[-1] if var_curve else None,
        )

        # Demand-contextualised P&L analysis
        monthly_consumption_bbl = float(constraints.get("forecast_consumption_bbl", 100_000))

        # At the recommended post-scenario HR
        hedged_cost_per_bbl = (
            opt_result.optimal_hr * current_price
            + (1 - opt_result.optimal_hr) * stressed_price
        )
        unhedged_cost_per_bbl = stressed_price

        monthly_saving_usd = (unhedged_cost_per_bbl - hedged_cost_per_bbl) * monthly_consumption_bbl
        monthly_saving_usd = round(float(monthly_saving_usd), 0)

        # What a pre-emptive 70% hedge would have done (industry best-practice)
        preemptive_hr = 0.70
        preemptive_hedged_cost = (
            preemptive_hr * current_price
            + (1 - preemptive_hr) * stressed_price
        )
        preemptive_saving_usd = round(
            float((unhedged_cost_per_bbl - preemptive_hedged_cost) * monthly_consumption_bbl), 0
        )

        narrative = self._generate_narrative(
            scenario, opt_result, stressed_var, current_price, stressed_price
        )

        # Convert numpy types to native Python for JSON serialization
        instrument_mix = {k: float(v) for k, v in opt_result.instrument_mix.items()}

        return {
            "scenario_id": scenario.id,
            "scenario_name": scenario.name,
            "current_price": round(current_price, 2),
            "stressed_price": round(stressed_price, 2),
            "price_change_pct": round(scenario.price_shock_pct * 100, 1),
            "optimizer_result": {
                "optimal_hr": float(opt_result.optimal_hr),
                "instrument_mix": instrument_mix,
                "collateral_usd": float(opt_result.collateral_usd),
                "collateral_pct_of_reserves": float(opt_result.collateral_pct_of_reserves),
                "solver_converged": bool(opt_result.solver_converged),
            },
            "var_impact": {
                "stressed_var_usd": float(stressed_var.var_usd) if stressed_var else None,
                "normal_var_usd": None,
            },
            "risk_narrative": narrative,
            "constraints_satisfied": not bool(opt_result.constraint_violations),
            "demand_pnl": {
                "monthly_consumption_bbl": monthly_consumption_bbl,
                "current_price_per_bbl": round(current_price, 2),
                "stressed_price_per_bbl": round(stressed_price, 2),
                "hedged_cost_per_bbl": round(hedged_cost_per_bbl, 2),
                "unhedged_cost_per_bbl": round(unhedged_cost_per_bbl, 2),
                "monthly_saving_usd": monthly_saving_usd,
                "preemptive_70pct_saving_usd": preemptive_saving_usd,
            },
            "hindsight": self._generate_hindsight(scenario, monthly_saving_usd),
        }

    def _generate_narrative(
        self,
        scenario: StressScenario,
        opt_result: Any,
        var_result: Any,
        current: float,
        stressed: float,
    ) -> str:
        """Generate plain-English risk narrative."""
        direction = "REDUCING" if scenario.price_shock_pct < 0 else "INCREASING"
        if scenario.price_shock_pct < -0.3:
            return (
                f"In a severe price crash, the unhedged position benefits from lower fuel costs. "
                f"The optimizer recommends {direction} the hedge ratio to {opt_result.optimal_hr * 100:.0f}% "
                f"to capture downside savings while maintaining some upside protection. "
                f"Asymmetric instruments (options) are preferred."
            )
        if scenario.price_shock_pct > 0.3:
            return (
                f"In a sharp price spike, hedges protect against cost overruns. "
                f"The optimizer recommends {direction} the hedge ratio to {opt_result.optimal_hr * 100:.0f}% "
                f"to lock in costs before further increases. "
                f"Futures are preferred for immediate, cost-effective coverage."
            )
        return (
            f"Under {scenario.name} conditions, the optimizer recommends a hedge ratio of "
            f"{opt_result.optimal_hr * 100:.0f}%. "
            + (
                "All constraints are satisfied."
                if not opt_result.constraint_violations
                else "Some constraints require review."
            )
        )

    def _generate_hindsight(
        self,
        scenario: StressScenario,
        monthly_saving_usd: float,
    ) -> str:
        """Generate 'what should have been done' hindsight narrative."""
        saving_m = monthly_saving_usd / 1_000_000
        if scenario.price_shock_pct <= -0.30:
            return (
                f"In this scenario, hedging worked against you — lower spot prices meant "
                f"the unhedged position was cheaper. A carrier at 70% hedge would have "
                f"{'paid' if monthly_saving_usd < 0 else 'saved'} approximately "
                f"${abs(saving_m):.1f}M per month vs. an unhedged position. "
                f"The lesson: before a demand collapse, reduce hedge ratio to 40–50% and "
                f"favour options over futures so you retain the ability to exit at low cost."
            )
        if scenario.price_shock_pct >= 0.30:
            return (
                f"A carrier fully unhedged during this scenario paid approximately "
                f"${abs(saving_m):.1f}M per month more than one hedged at 70%. "
                f"The key signal to act on before this type of event: watch the crack spread "
                f"z-score — when it exceeds +1.5σ for more than 5 consecutive days, "
                f"near-term hedging becomes urgent. Heating oil futures with 3-month maturity "
                f"are the most effective instrument at this horizon."
            )
        return (
            f"Under these conditions, a 70% hedge would have "
            f"{'saved' if monthly_saving_usd >= 0 else 'cost'} "
            f"${abs(saving_m):.1f}M per month vs. the unhedged position. "
            f"No unusual action was required — the platform's standard dynamic "
            f"strategy handles this scenario within normal parameters."
        )
