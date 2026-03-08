"""Hedge optimization using SLSQP solver.

Optimizes hedge ratio and instrument mix to minimize VaR
while satisfying all constraints (HR cap, collateral limit, etc.).
"""

import time
from typing import Any

import numpy as np
from scipy.optimize import minimize

from app.analytics.domain import OptimizationResult
from app.analytics.optimizer.constraints import validate_solution_constraints


class HedgeOptimizer:
    """SLSQP-based hedge optimizer.
    
    Decision variables (8 total):
    - hedge_ratio (0.0 - 0.80)
    - pct_futures, pct_options, pct_collars, pct_swaps (must sum to 1.0)
    - w_heating_oil, w_brent, w_wti (must sum to 1.0)
    
    Objective: Minimize VaR (or maximize VaR reduction)
    """

    def __init__(self, max_iterations: int = 100, tolerance: float = 1e-6) -> None:
        """Initialize optimizer.
        
        Args:
            max_iterations: Maximum solver iterations
            tolerance: Convergence tolerance
        """
        self.max_iterations = max_iterations
        self.tolerance = tolerance

    def optimize(
        self,
        var_metrics: dict[str, float],
        constraints: dict[str, Any],
    ) -> OptimizationResult:
        """Optimize hedge ratio and instrument mix.
        
        Args:
            var_metrics: VaR values at different hedge ratios:
                {'hr_0': var_usd, 'hr_20': var_usd, ..., 'hr_80': var_usd}
            constraints: Runtime constraints from ConfigRepository
        
        Returns:
            OptimizationResult with optimal decisions
        """
        start_time = time.time()

        # Extract VaR curve for interpolation
        hedge_ratios = []
        var_values = []
        for key, value in sorted(var_metrics.items()):
            if key.startswith("hr_"):
                hr = float(key.split("_")[1]) / 100.0
                hedge_ratios.append(hr)
                var_values.append(value)

        hr_array = np.array(hedge_ratios)
        var_array = np.array(var_values)

        # Objective function: minimize VaR (via interpolation)
        def objective(x: np.ndarray) -> float:
            hedge_ratio = x[0]
            # Linearly interpolate VaR at this hedge ratio
            var_at_hr = np.interp(hedge_ratio, hr_array, var_array)
            return var_at_hr

        # Decision variables bounds
        hr_max = constraints["hr_max"]
        bounds = [
            (0.0, hr_max),  # hedge_ratio
            (0.0, 1.0),  # pct_futures
            (0.0, constraints.get("options_max", 0.50)),  # pct_options
            (0.0, constraints.get("collars_max", 0.30)),  # pct_collars
            (0.0, constraints.get("swaps_max", 0.20)),   # pct_swaps
            (0.0, 1.0),  # w_heating_oil
            (0.0, 1.0),  # w_brent
            (0.0, 1.0),  # w_wti
        ]

        # Constraint functions
        def constraint_instrument_sum(x: np.ndarray) -> float:
            # pct_futures + pct_options + pct_collars + pct_swaps == 1.0
            return x[1] + x[2] + x[3] + x[4] - 1.0

        def constraint_proxy_sum(x: np.ndarray) -> float:
            # w_heating_oil + w_brent + w_wti == 1.0
            return x[5] + x[6] + x[7] - 1.0

        scipy_constraints = [
            {"type": "eq", "fun": constraint_instrument_sum},
            {"type": "eq", "fun": constraint_proxy_sum},
        ]

        # Initial guess (start at 60% HR, futures-heavy, heating oil primary)
        x0 = np.array([0.60, 0.70, 0.20, 0.10, 0.0, 0.70, 0.20, 0.10])

        # Run optimization
        try:
            result = minimize(
                objective,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=scipy_constraints,
                options={
                    "maxiter": self.max_iterations,
                    "ftol": self.tolerance,
                },
            )

            solver_converged = result.success
            optimal_x = result.x if solver_converged else x0

        except Exception:
            # Optimizer failed - return initial guess
            solver_converged = False
            optimal_x = x0

        # Extract solution
        optimal_hr = float(optimal_x[0])
        instrument_mix = {
            "futures": float(optimal_x[1]),
            "options": float(optimal_x[2]),
            "collars": float(optimal_x[3]),
            "swaps": float(optimal_x[4]),
        }
        proxy_weights = {
            "heating_oil": float(optimal_x[5]),
            "brent": float(optimal_x[6]),
            "wti": float(optimal_x[7]),
        }

        # Compute final VaR at optimal HR
        objective_value = float(np.interp(optimal_hr, hr_array, var_array))

        # Estimate collateral requirement
        # Simplified: 15% of notional hedged + buffer for variation margin
        notional_estimate = var_array[0] / 0.05  # Rough estimate from 5% VaR
        collateral_usd = notional_estimate * optimal_hr * 0.15
        cash_reserves = constraints.get("cash_reserves_usd", collateral_usd / 0.15)
        collateral_pct_of_reserves = (
            (collateral_usd / cash_reserves * 100) if cash_reserves > 0 else 0.0
        )

        # Validate constraints
        constraint_violations = validate_solution_constraints(
            optimal_hr,
            instrument_mix,
            proxy_weights,
            collateral_usd,
            constraints,
        )

        solve_time = time.time() - start_time

        return OptimizationResult(
            optimal_hr=round(optimal_hr, 4),
            instrument_mix={k: round(v, 4) for k, v in instrument_mix.items()},
            proxy_weights={k: round(v, 4) for k, v in proxy_weights.items()},
            objective_value=round(objective_value, 2),
            solver_converged=solver_converged,
            collateral_usd=round(collateral_usd, 2),
            collateral_pct_of_reserves=round(collateral_pct_of_reserves, 2),
            solve_time_seconds=round(solve_time, 3),
            constraint_violations=constraint_violations,
        )
