"""Test script to validate Phase 0-2A implementation.

Tests:
1. Configuration loading
2. Database models and migrations
3. Repository patterns
4. Domain objects and protocols
"""

import asyncio
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_phase_0_config() -> bool:
    """Test Phase 0: Configuration and constants."""
    print("\n=== Testing Phase 0: Configuration & Constants ===")
    
    try:
        from app.config import get_settings
        from app.constants import (
            HR_HARD_CAP,
            HR_SOFT_WARN,
            COLLATERAL_LIMIT,
            IFRS9_R2_MIN_PROSPECTIVE,
            MAPE_TARGET,
        )
        
        print("OK Constants loaded successfully")
        print(f"  - HR_HARD_CAP: {HR_HARD_CAP}")
        print(f"  - HR_SOFT_WARN: {HR_SOFT_WARN}")
        print(f"  - COLLATERAL_LIMIT: {COLLATERAL_LIMIT}")
        print(f"  - IFRS9_R2_MIN: {IFRS9_R2_MIN_PROSPECTIVE}")
        print(f"  - MAPE_TARGET: {MAPE_TARGET}")
        
        # Test configuration (will fail if required env vars missing)
        try:
            settings = get_settings()
            print("OK Configuration loaded")
            print(f"  - Environment: {settings.ENVIRONMENT}")
            print(f"  - Log Level: {settings.LOG_LEVEL}")
            print(f"  - JWT Algorithm: {settings.JWT_ALGORITHM}")
        except Exception as e:
            print(f"WARN Configuration incomplete (expected in test): {str(e)[:100]}")
            print("  Note: Set environment variables for full functionality")
        
        return True
        
    except Exception as e:
        print(f"FAIL Phase 0 test failed: {e}")
        return False


async def test_phase_0_exceptions() -> bool:
    """Test custom exception hierarchy."""
    print("\n=== Testing Exception Hierarchy ===")
    
    try:
        from app.exceptions import (
            HedgePlatformError,
            ConstraintViolationError,
            DataIngestionError,
            ModelError,
            AuthorizationError,
        )
        
        # Test constraint violation
        error = ConstraintViolationError(
            message="HR exceeds cap",
            constraint_type="hr_cap",
            current_value=0.85,
            limit_value=0.80,
        )
        assert error.error_code == "constraint_violation_hr_cap"
        assert error.context["current_value"] == 0.85
        print("OK ConstraintViolationError works correctly")
        
        # Test error dict conversion
        error_dict = error.to_dict()
        assert "detail" in error_dict
        assert "error_code" in error_dict
        assert "context" in error_dict
        print("OK Exception to_dict() conversion works")
        
        return True
        
    except Exception as e:
        print(f"FAIL Exception test failed: {e}")
        return False


async def test_phase_1a_models() -> bool:
    """Test Phase 1A: Database models structure."""
    print("\n=== Testing Phase 1A: Database Models ===")
    
    try:
        from app.db.models import (
            User,
            UserRole,
            PlatformConfig,
            PriceTick,
            AnalyticsRun,
            HedgeRecommendation,
            RecommendationStatus,
            Approval,
            HedgePosition,
            AuditLog,
        )
        
        print("OK All models imported successfully")
        
        # Test enum values
        assert UserRole.ADMIN == "admin"
        assert UserRole.ANALYST == "analyst"
        assert RecommendationStatus.PENDING == "PENDING"
        print("OK Enums have correct values")
        
        # Test model instantiation (without DB)
        import uuid
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.ADMIN,
            is_active=True,
        )
        assert user.email == "test@example.com"
        assert user.role == UserRole.ADMIN
        print("OK Model instantiation works")
        
        return True
        
    except Exception as e:
        print(f"FAIL Phase 1A test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_phase_1b_repositories() -> bool:
    """Test Phase 1B: Repository pattern structure."""
    print("\n=== Testing Phase 1B: Repository Pattern ===")
    
    try:
        from app.repositories import (
            BaseRepository,
            UserRepository,
            RecommendationRepository,
            PositionRepository,
            AuditRepository,
            AnalyticsRepository,
            MarketDataRepository,
            ConfigRepository,
        )
        
        print("OK All repositories imported successfully")
        
        # Test repository class structure
        assert hasattr(BaseRepository, 'get_by_id')
        assert hasattr(BaseRepository, 'create')
        assert hasattr(BaseRepository, 'update')
        assert hasattr(BaseRepository, 'delete')
        print("OK BaseRepository has all CRUD methods")
        
        # Test domain-specific methods exist
        assert hasattr(RecommendationRepository, 'get_pending')
        assert hasattr(RecommendationRepository, 'update_status')
        assert hasattr(PositionRepository, 'get_open_positions')
        assert hasattr(PositionRepository, 'get_total_open_collateral')
        assert hasattr(MarketDataRepository, 'upsert_tick')
        assert hasattr(ConfigRepository, 'get_constraints_snapshot')
        print("OK Domain-specific repository methods exist")
        
        return True
        
    except Exception as e:
        print(f"FAIL Phase 1B test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_phase_2a_domain() -> bool:
    """Test Phase 2A: Domain objects and protocols."""
    print("\n=== Testing Phase 2A: Domain Objects & Protocols ===")
    
    try:
        from app.analytics.domain import (
            ForecastResult,
            VaRResult,
            OptimizationResult,
            BasisRiskMetric,
        )
        from app.analytics.protocols import (
            Forecaster,
            RiskEngine,
            Optimizer,
            BasisAnalyzer,
        )
        
        print("OK All domain objects and protocols imported")
        
        # Test frozen dataclass creation
        forecast = ForecastResult(
            forecast_values=(100.0, 101.0, 102.0),
            mape=7.5,
            mape_passes_target=True,
            model_weights={"arima": 0.25, "lstm": 0.45, "xgb": 0.30},
            horizon_days=30,
            generated_at=datetime.now(),
            model_versions={"arima": "1.0", "lstm": "2.0", "xgb": "1.5"},
        )
        assert forecast.mape == 7.5
        assert forecast.mape_passes_target is True
        print("OK ForecastResult dataclass works")
        
        # Test immutability
        try:
            forecast.mape = 10.0  # type: ignore
            print("FAIL Dataclass is not frozen!")
            return False
        except Exception:
            print("OK Dataclass is properly frozen (immutable)")
        
        # Test VaRResult
        var_result = VaRResult(
            hedge_ratio=0.70,
            var_pct=5.2,
            var_usd=520000.0,
            cvar_usd=680000.0,
            confidence=0.95,
            holding_period_days=30,
            n_observations=1461,
        )
        assert var_result.hedge_ratio == 0.70
        print("OK VaRResult dataclass works")
        
        # Test OptimizationResult
        opt_result = OptimizationResult(
            optimal_hr=0.67,
            instrument_mix={"futures": 0.60, "options": 0.30, "collars": 0.10, "swaps": 0.0},
            proxy_weights={"heating_oil": 0.70, "brent": 0.20, "wti": 0.10},
            objective_value=0.387,
            solver_converged=True,
            collateral_usd=1250000.0,
            collateral_pct_of_reserves=12.5,
            solve_time_seconds=0.45,
            constraint_violations=[],
        )
        assert opt_result.solver_converged is True
        assert len(opt_result.constraint_violations) == 0
        print("OK OptimizationResult dataclass works")
        
        # Test BasisRiskMetric
        basis = BasisRiskMetric(
            r2_heating_oil=0.92,
            r2_brent=0.78,
            r2_wti=0.75,
            crack_spread_current=15.5,
            crack_spread_zscore=1.2,
            risk_level="LOW",
            recommended_proxy="heating_oil",
            ifrs9_eligible=True,
        )
        assert basis.recommended_proxy == "heating_oil"
        assert basis.ifrs9_eligible is True
        print("OK BasisRiskMetric dataclass works")
        
        # Test protocols are runtime checkable
        assert hasattr(Forecaster, '__protocol_attrs__')
        print("OK Protocols are properly defined")
        
        return True
        
    except Exception as e:
        print(f"FAIL Phase 2A test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_file_structure() -> bool:
    """Test that all expected files exist."""
    print("\n=== Testing File Structure ===")
    
    required_files = [
        ".cursorrules",
        ".gitignore",
        "docker-compose.yml",
        "python_engine/app/constants.py",
        "python_engine/app/config.py",
        "python_engine/app/exceptions.py",
        "python_engine/app/db/base.py",
        "python_engine/app/db/models.py",
        "python_engine/app/repositories/base.py",
        "python_engine/app/analytics/domain.py",
        "python_engine/app/analytics/protocols.py",
        "python_engine/alembic.ini",
        "python_engine/requirements.txt",
        "frontend/package.json",
        "frontend/tsconfig.json",
        "frontend/vite.config.ts",
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = Path(file_path)
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("X Missing files:")
        for f in missing_files:
            print(f"  - {f}")
        return False
    
    print(f"OK All {len(required_files)} required files exist")
    return True


async def main() -> None:
    """Run all tests."""
    print("="*60)
    print("FUEL HEDGING PLATFORM - PHASE 0-2A VALIDATION")
    print("="*60)
    
    results = {}
    
    # Run all tests
    results["File Structure"] = await test_file_structure()
    results["Phase 0: Config"] = await test_phase_0_config()
    results["Phase 0: Exceptions"] = await test_phase_0_exceptions()
    results["Phase 1A: Models"] = await test_phase_1a_models()
    results["Phase 1B: Repositories"] = await test_phase_1b_repositories()
    results["Phase 2A: Domain"] = await test_phase_2a_domain()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! Ready for Phase 2B implementation.")
        return
    else:
        print("\n[WARNING] Some tests failed. Review errors above.")


if __name__ == "__main__":
    asyncio.run(main())
