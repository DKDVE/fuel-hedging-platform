"""Test suite for Phase 2B analytics modules.

Tests all analytics implementations:
- Forecasters (ARIMA, XGBoost, Ensemble)
- VaR engine
- Optimizer
- Basis risk analyzer
- Stress testing
"""

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_test_dataset(n_days: int = 500) -> pd.DataFrame:
    """Create synthetic test dataset matching expected schema."""
    np.random.seed(42)
    
    dates = pd.date_range(start='2023-01-01', periods=n_days, freq='D')
    
    # Base prices with trend and seasonality
    t = np.arange(n_days)
    trend = 80 + 0.02 * t
    seasonality = 10 * np.sin(2 * np.pi * t / 365)
    noise = np.random.normal(0, 5, n_days)
    
    jet_fuel = trend + seasonality + noise
    heating_oil = jet_fuel * 0.95 + np.random.normal(0, 2, n_days)
    brent = jet_fuel * 1.1 + np.random.normal(0, 3, n_days)
    wti = jet_fuel * 1.05 + np.random.normal(0, 3, n_days)
    crack_spread = jet_fuel - heating_oil
    volatility = np.abs(np.random.normal(15, 5, n_days))
    
    df = pd.DataFrame({
        'Date': dates,
        'Jet_Fuel_Spot_USD_bbl': jet_fuel,
        'Heating_Oil_Futures_USD_bbl': heating_oil,
        'Brent_Crude_Futures_USD_bbl': brent,
        'WTI_Crude_Futures_USD_bbl': wti,
        'Crack_Spread_USD_bbl': crack_spread,
        'Volatility_Index_pct': volatility,
    })
    
    return df


def test_basis_risk_analyzer() -> bool:
    """Test basis risk analysis."""
    print("\n=== Testing Basis Risk Analyzer ===")
    
    try:
        from app.analytics.basis import BasisRiskAnalyzer
        
        # Create test data
        df = create_test_dataset(365)
        
        # Initialize analyzer
        analyzer = BasisRiskAnalyzer(window_days=90)
        print("OK Analyzer initialized")
        
        # Run analysis
        result = analyzer.analyze(df)
        print("OK Analysis completed")
        
        # Validate result structure
        assert hasattr(result, 'r2_heating_oil')
        assert hasattr(result, 'r2_brent')
        assert hasattr(result, 'r2_wti')
        assert hasattr(result, 'crack_spread_current')
        assert hasattr(result, 'crack_spread_zscore')
        assert hasattr(result, 'risk_level')
        assert hasattr(result, 'recommended_proxy')
        assert hasattr(result, 'ifrs9_eligible')
        print("OK Result structure valid")
        
        # Validate R² values (should be high for correlated test data)
        assert 0.0 <= result.r2_heating_oil <= 1.0
        assert 0.0 <= result.r2_brent <= 1.0
        assert 0.0 <= result.r2_wti <= 1.0
        print(f"OK R² values: HO={result.r2_heating_oil:.4f}, Brent={result.r2_brent:.4f}, WTI={result.r2_wti:.4f}")
        
        # Validate risk level
        assert result.risk_level in ['LOW', 'MODERATE', 'HIGH', 'CRITICAL']
        print(f"OK Risk level: {result.risk_level}")
        
        # Validate recommended proxy
        assert result.recommended_proxy in ['heating_oil', 'brent', 'wti']
        print(f"OK Recommended proxy: {result.recommended_proxy}")
        
        # Test immutability
        try:
            result.r2_heating_oil = 0.5  # type: ignore
            print("FAIL Result is not frozen!")
            return False
        except Exception:
            print("OK Result is immutable")
        
        return True
        
    except Exception as e:
        print(f"FAIL Basis risk analyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_var_engine() -> bool:
    """Test VaR calculation."""
    print("\n=== Testing VaR Engine ===")
    
    try:
        from app.analytics.risk import HistoricalSimVaR
        
        # Create test data (need at least 252 observations)
        df = create_test_dataset(300)
        
        # Initialize VaR engine
        var_engine = HistoricalSimVaR(
            confidence=0.95,
            holding_period_days=30,
            min_observations=252,
        )
        print("OK VaR engine initialized")
        
        # Test single VaR calculation
        notional = 10_000_000  # $10M
        hedge_ratio = 0.60
        var_result = var_engine.compute_var(df, hedge_ratio, notional)
        print("OK VaR computed")
        
        # Validate result structure
        assert var_result.hedge_ratio == 0.60
        assert var_result.var_usd > 0
        assert var_result.cvar_usd >= var_result.var_usd  # CVaR >= VaR
        assert var_result.confidence == 0.95
        assert var_result.holding_period_days == 30
        print(f"OK VaR=${var_result.var_usd:,.0f}, CVaR=${var_result.cvar_usd:,.0f}")
        
        # Test VaR curve
        var_curve = var_engine.var_curve(df, notional)
        print("OK VaR curve computed")
        
        # Should have 7 points
        assert len(var_curve) == 7
        print(f"OK VaR curve has {len(var_curve)} points")
        
        # VaR should generally decrease as hedge ratio increases
        var_values = [v.var_usd for v in var_curve]
        print(f"   VaR curve: {[f'{v:,.0f}' for v in var_values]}")
        
        # Check first VaR (unhedged) is highest
        assert var_values[0] >= var_values[-2]  # Compare 0% to 80%
        print("OK VaR decreases with hedging")
        
        # Test marginal reduction
        marginal = var_engine.compute_marginal_var_reduction(df, notional)
        print("OK Marginal VaR reduction computed")
        assert '0_to_20' in marginal
        assert '70_to_80' in marginal
        print(f"   Marginal reduction 0->20%: {marginal['0_to_20']:.2f}%")
        print(f"   Marginal reduction 70->80%: {marginal['70_to_80']:.2f}%")
        
        # Test insufficient data error
        try:
            small_df = create_test_dataset(100)
            var_engine.compute_var(small_df, 0.5, notional)
            print("FAIL Should have raised ModelError for insufficient data")
            return False
        except Exception as e:
            if "ModelError" in str(type(e).__name__) or "Insufficient" in str(e):
                print("OK Correctly raises error for insufficient data")
            else:
                raise
        
        return True
        
    except Exception as e:
        print(f"FAIL VaR engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_optimizer() -> bool:
    """Test hedge optimizer."""
    print("\n=== Testing Hedge Optimizer ===")
    
    try:
        from app.analytics.optimizer import (
            HedgeOptimizer,
            build_optimizer_constraints,
            validate_solution_constraints,
        )
        
        # Create test VaR metrics
        var_metrics = {
            'hr_0': 500000,
            'hr_20': 400000,
            'hr_40': 320000,
            'hr_60': 270000,
            'hr_70': 250000,
            'hr_80': 240000,
            'hr_100': 235000,
        }
        
        # Build constraints
        config_snapshot = {
            'hr_cap': 0.80,
            'collateral_limit': 0.15,
            'max_coverage_ratio': 1.10,
        }
        constraints = build_optimizer_constraints(
            config_snapshot,
            cash_reserves=50_000_000,
            forecast_consumption_bbl=100_000,
        )
        print("OK Constraints built")
        
        # Initialize optimizer
        optimizer = HedgeOptimizer(max_iterations=100, tolerance=1e-6)
        print("OK Optimizer initialized")
        
        # Run optimization
        result = optimizer.optimize(var_metrics, constraints)
        print("OK Optimization completed")
        
        # Validate result structure
        assert hasattr(result, 'optimal_hr')
        assert hasattr(result, 'instrument_mix')
        assert hasattr(result, 'proxy_weights')
        assert hasattr(result, 'solver_converged')
        assert hasattr(result, 'constraint_violations')
        print("OK Result structure valid")
        
        # Validate HR within bounds
        assert 0.0 <= result.optimal_hr <= 0.80
        print(f"OK Optimal HR: {result.optimal_hr:.4f} (within bounds)")
        
        # Validate instrument mix sums to ~1.0
        instrument_sum = sum(result.instrument_mix.values())
        assert 0.99 <= instrument_sum <= 1.01
        print(f"OK Instrument mix sums to {instrument_sum:.4f}")
        
        # Validate proxy weights sum to ~1.0
        proxy_sum = sum(result.proxy_weights.values())
        assert 0.99 <= proxy_sum <= 1.01
        print(f"OK Proxy weights sum to {proxy_sum:.4f}")
        
        # Validate constraint violations
        print(f"   Constraint violations: {len(result.constraint_violations)}")
        if result.constraint_violations:
            print(f"   Violations: {result.constraint_violations}")
        
        # Test validation function
        violations = validate_solution_constraints(
            result.optimal_hr,
            result.instrument_mix,
            result.proxy_weights,
            result.collateral_usd,
            constraints,
        )
        print(f"OK Constraint validation: {len(violations)} violations")
        
        # Test constraint violation scenario
        bad_hr = 0.95  # Above cap
        violations = validate_solution_constraints(
            bad_hr,
            result.instrument_mix,
            result.proxy_weights,
            result.collateral_usd,
            constraints,
        )
        assert len(violations) > 0
        print("OK Correctly detects HR constraint violation")
        
        return True
        
    except Exception as e:
        print(f"FAIL Optimizer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_forecasters() -> bool:
    """Test forecasting models."""
    print("\n=== Testing Forecasters ===")
    
    try:
        from app.analytics.forecaster import (
            ArimaForecaster,
            XGBoostForecaster,
            EnsembleForecaster,
        )
        
        # Create test data
        df = create_test_dataset(400)
        
        # Test ARIMA
        print("\n--- ARIMA Forecaster ---")
        arima = ArimaForecaster(order=(2, 1, 2), horizon_days=30)
        arima_result = arima.predict(df)
        print("OK ARIMA forecast generated")
        
        assert len(arima_result.forecast_values) == 30
        assert arima_result.mape >= 0
        assert arima_result.model_weights == {"arima": 1.0}
        print(f"   MAPE: {arima_result.mape:.2f}%")
        print(f"   First 5 forecasts: {[f'{x:.2f}' for x in arima_result.forecast_values[:5]]}")
        
        # Test XGBoost
        print("\n--- XGBoost Forecaster ---")
        xgboost = XGBoostForecaster(n_lags=7, horizon_days=30)
        xgboost_result = xgboost.predict(df)
        print("OK XGBoost forecast generated")
        
        assert len(xgboost_result.forecast_values) == 30
        assert xgboost_result.mape >= 0
        assert xgboost_result.model_weights == {"xgboost": 1.0}
        print(f"   MAPE: {xgboost_result.mape:.2f}%")
        
        # Test Ensemble (without LSTM since model file doesn't exist)
        print("\n--- Ensemble Forecaster ---")
        ensemble = EnsembleForecaster(
            arima_forecaster=arima,
            lstm_forecaster=None,  # Will be created but will fail gracefully
            xgboost_forecaster=xgboost,
            weights={"arima": 0.25, "lstm": 0.45, "xgboost": 0.30},
            horizon_days=30,
        )
        
        ensemble_result = ensemble.predict(df)
        print("OK Ensemble forecast generated")
        
        assert len(ensemble_result.forecast_values) == 30
        assert ensemble_result.mape >= 0
        print(f"   MAPE: {ensemble_result.mape:.2f}%")
        print(f"   Model weights: {ensemble_result.model_weights}")
        
        # Weights should adjust if LSTM failed
        weight_sum = sum(ensemble_result.model_weights.values())
        assert 0.99 <= weight_sum <= 1.01
        print("OK Ensemble weights sum to 1.0")
        
        # Test result immutability
        try:
            arima_result.mape = 100.0  # type: ignore
            print("FAIL Result is not frozen!")
            return False
        except Exception:
            print("OK Results are immutable")
        
        return True
        
    except Exception as e:
        print(f"FAIL Forecaster test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stress_testing() -> bool:
    """Test stress testing scenarios."""
    print("\n=== Testing Stress Test Engine ===")
    
    try:
        from app.analytics.risk import StressTestEngine, STRESS_SCENARIOS
        
        # Initialize engine
        notional = 10_000_000
        cash_reserves = 50_000_000
        engine = StressTestEngine(notional, cash_reserves)
        print("OK Stress test engine initialized")
        
        # Check scenarios loaded
        assert len(STRESS_SCENARIOS) == 5
        print(f"OK {len(STRESS_SCENARIOS)} scenarios loaded")
        
        # Run a single scenario
        current_jet_fuel = 100.0
        current_proxy = 95.0
        hedge_ratio = 0.70
        
        scenario = STRESS_SCENARIOS[0]  # Oil Supply Shock
        result = engine.run_scenario(
            scenario,
            current_jet_fuel,
            current_proxy,
            hedge_ratio,
        )
        print(f"OK Scenario '{result.scenario_name}' executed")
        
        # Validate result
        assert result.hedge_ratio == 0.70
        assert result.hedge_effectiveness_pct >= 0
        assert result.passes_collateral_limit in [True, False]
        print(f"   Portfolio loss: ${result.portfolio_loss_usd:,.0f}")
        print(f"   Hedge effectiveness: {result.hedge_effectiveness_pct:.1f}%")
        print(f"   Passes collateral limit: {result.passes_collateral_limit}")
        
        # Run all scenarios
        all_results = engine.run_all_scenarios(
            current_jet_fuel,
            current_proxy,
            hedge_ratio,
        )
        assert len(all_results) == 5
        print(f"OK All {len(all_results)} scenarios executed")
        
        # Print summary
        for r in all_results:
            print(f"   {r.scenario_name}: Loss=${r.portfolio_loss_usd:,.0f}, "
                  f"Effectiveness={r.hedge_effectiveness_pct:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"FAIL Stress test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_protocol_compliance() -> bool:
    """Test that implementations satisfy Protocol contracts."""
    print("\n=== Testing Protocol Compliance ===")
    
    try:
        from app.analytics.protocols import (
            Forecaster,
            RiskEngine,
            Optimizer,
            BasisAnalyzer,
        )
        from app.analytics.forecaster import EnsembleForecaster
        from app.analytics.risk import HistoricalSimVaR
        from app.analytics.optimizer import HedgeOptimizer
        from app.analytics.basis import BasisRiskAnalyzer
        
        # Check runtime checkable
        ensemble = EnsembleForecaster()
        var_engine = HistoricalSimVaR()
        optimizer = HedgeOptimizer()
        basis = BasisRiskAnalyzer()
        
        assert isinstance(ensemble, Forecaster)
        print("OK EnsembleForecaster implements Forecaster protocol")
        
        assert isinstance(var_engine, RiskEngine)
        print("OK HistoricalSimVaR implements RiskEngine protocol")
        
        assert isinstance(optimizer, Optimizer)
        print("OK HedgeOptimizer implements Optimizer protocol")
        
        assert isinstance(basis, BasisAnalyzer)
        print("OK BasisRiskAnalyzer implements BasisAnalyzer protocol")
        
        return True
        
    except Exception as e:
        print(f"FAIL Protocol compliance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main() -> None:
    """Run all analytics tests."""
    print("="*70)
    print("PHASE 2B ANALYTICS MODULE TEST SUITE")
    print("="*70)
    
    results = {}
    
    # Run all tests
    results["Basis Risk Analyzer"] = test_basis_risk_analyzer()
    results["VaR Engine"] = test_var_engine()
    results["Optimizer"] = test_optimizer()
    results["Forecasters"] = test_forecasters()
    results["Stress Testing"] = test_stress_testing()
    results["Protocol Compliance"] = test_protocol_compliance()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All analytics tests passed!")
        print("Ready to proceed with Phase 3: Auth & FastAPI Core")
    else:
        print("\n[WARNING] Some tests failed. Review errors above.")


if __name__ == "__main__":
    main()
