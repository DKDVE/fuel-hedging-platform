"""Quick analytics test with real dataset and installed dependencies."""

import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def test_with_real_data():
    """Test analytics modules with the real fuel hedging dataset."""
    print("="*70)
    print("ANALYTICS TEST WITH REAL DATASET")
    print("="*70)
    
    # Load real dataset
    print("\n1. Loading real dataset...")
    dataset_path = Path(__file__).parent.parent / "data" / "fuel_hedging_dataset.csv"
    df = pd.read_csv(dataset_path)
    print(f"   Loaded {len(df)} observations from {df['Date'].iloc[0]} to {df['Date'].iloc[-1]}")
    
    # Test VaR Engine (import directly to avoid forecaster dependencies)
    print("\n2. Testing VaR Engine...")
    try:
        from app.analytics.risk.var_engine import HistoricalSimVaR
        
        var_engine = HistoricalSimVaR(confidence=0.95, holding_period_days=30)
        notional = 10_000_000  # $10M exposure
        
        var_result = var_engine.compute_var(df, hedge_ratio=0.70, notional=notional)
        print(f"   [OK] VaR (70% HR): ${var_result.var_usd:,.0f}")
        print(f"   [OK] CVaR: ${var_result.cvar_usd:,.0f}")
        
        var_curve = var_engine.var_curve(df, notional)
        print(f"   [OK] VaR curve: {len(var_curve)} points")
        print(f"        0% HR: ${var_curve[0].var_usd:,.0f}")
        print(f"        80% HR: ${var_curve[5].var_usd:,.0f}")
        print(f"        Risk reduction: {((var_curve[0].var_usd - var_curve[5].var_usd) / var_curve[0].var_usd * 100):.1f}%")
    except Exception as e:
        print(f"   [FAIL] {e}")
        return False
    
    # Test Basis Risk Analyzer
    print("\n3. Testing Basis Risk Analyzer...")
    try:
        from app.analytics.basis.basis_risk import BasisRiskAnalyzer
        
        analyzer = BasisRiskAnalyzer(window_days=90)
        basis_result = analyzer.analyze(df)
        
        print(f"   [OK] R² Heating Oil: {basis_result.r2_heating_oil:.4f}")
        print(f"   [OK] R² Brent: {basis_result.r2_brent:.4f}")
        print(f"   [OK] R² WTI: {basis_result.r2_wti:.4f}")
        print(f"   [OK] Recommended proxy: {basis_result.recommended_proxy}")
        print(f"   [OK] IFRS 9 eligible: {basis_result.ifrs9_eligible}")
        print(f"   [OK] Risk level: {basis_result.risk_level}")
    except Exception as e:
        print(f"   [FAIL] {e}")
        return False
    
    # Test Optimizer
    print("\n4. Testing Hedge Optimizer...")
    try:
        from app.analytics.optimizer.hedge_optimizer import HedgeOptimizer
        from app.analytics.optimizer.constraints import build_optimizer_constraints
        
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
        
        # Create VaR metrics from curve
        var_metrics = {f'hr_{int(v.hedge_ratio*100)}': v.var_usd for v in var_curve}
        
        optimizer = HedgeOptimizer()
        opt_result = optimizer.optimize(var_metrics, constraints)
        
        print(f"   [OK] Optimal HR: {opt_result.optimal_hr:.4f}")
        print(f"   [OK] Solver converged: {opt_result.solver_converged}")
        print(f"   [OK] Constraint violations: {len(opt_result.constraint_violations)}")
        print(f"   [OK] Collateral: ${opt_result.collateral_usd:,.0f} ({opt_result.collateral_pct_of_reserves:.1f}% of reserves)")
    except Exception as e:
        print(f"   [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test Stress Testing
    print("\n5. Testing Stress Test Engine...")
    try:
        from app.analytics.risk.stress_test import StressTestEngine, STRESS_SCENARIOS
        
        engine = StressTestEngine(notional=10_000_000, cash_reserves=50_000_000)
        
        # Get current prices
        current_jet_fuel = float(df['Jet_Fuel_Spot_USD_bbl'].iloc[-1])
        current_proxy = float(df['Heating_Oil_Futures_USD_bbl'].iloc[-1])
        
        results = engine.run_all_scenarios(current_jet_fuel, current_proxy, 0.70)
        
        print(f"   [OK] Tested {len(results)} scenarios:")
        for r in results:
            print(f"        {r.scenario_name}: {r.hedge_effectiveness_pct:.1f}% effective")
    except Exception as e:
        print(f"   [FAIL] {e}")
        return False
    
    print("\n" + "="*70)
    print("[SUCCESS] All analytics modules working with real data!")
    print("="*70)
    return True


if __name__ == "__main__":
    success = test_with_real_data()
    sys.exit(0 if success else 1)
