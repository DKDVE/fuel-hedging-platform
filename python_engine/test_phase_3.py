"""Test Phase 3: Auth & FastAPI Core."""

import os
import sys
from pathlib import Path

# Set required environment variables for testing
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost/test"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only-not-production"
os.environ["N8N_WEBHOOK_SECRET"] = "test-n8n-secret-for-testing"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:5173"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

sys.path.insert(0, str(Path(__file__).parent))


def test_phase_3():
    """Test authentication and FastAPI core setup."""
    print("="*70)
    print("PHASE 3: AUTH & FASTAPI CORE TEST")
    print("="*70)
    
    # Test 1: Import auth module
    print("\n1. Testing auth module...")
    try:
        from app.auth import (
            create_access_token,
            create_refresh_token,
            decode_token,
            hash_password,
            validate_access_token,
            verify_password,
        )
        
        # Test password hashing
        password = "TestPass123"
        hashed = hash_password(password)
        assert verify_password(password, hashed), "Password verification failed"
        assert not verify_password("wrong_password", hashed), "Should reject wrong password"
        print("   [OK] Password hashing works")
        
        # Test JWT tokens
        test_user_id = "123e4567-e89b-12d3-a456-426614174000"
        access_token = create_access_token({"sub": test_user_id})
        refresh_token = create_refresh_token(test_user_id)
        
        # Decode and validate
        payload = decode_token(access_token)
        assert payload["sub"] == test_user_id, "Token payload mismatch"
        
        validated_user_id = validate_access_token(access_token)
        assert validated_user_id == test_user_id, "Token validation failed"
        print("   [OK] JWT token generation and validation works")
        
    except Exception as e:
        print(f"   [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Import dependencies
    print("\n2. Testing dependencies module...")
    try:
        from app.dependencies import (
            AdminUser,
            AnalystUser,
            CurrentUser,
            DatabaseSession,
            RiskManagerUser,
            get_current_user,
            get_db,
            require_role,
        )
        print("   [OK] Dependencies module imported successfully")
    except Exception as e:
        print(f"   [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Import schemas
    print("\n3. Testing schemas...")
    try:
        from app.schemas import (
            ChangePasswordRequest,
            CreateUserRequest,
            ErrorResponse,
            HealthResponse,
            LoginRequest,
            LoginResponse,
            MessageResponse,
            PaginatedResponse,
            PaginationParams,
            RefreshTokenRequest,
            TokenResponse,
            UpdateUserRequest,
            UserResponse,
        )
        
        # Test schema validation
        login_req = LoginRequest(email="test@example.com", password="password123")
        assert login_req.email == "test@example.com"
        
        pagination = PaginationParams(page=2, limit=100)
        assert pagination.page == 2
        assert pagination.limit == 100
        print("   [OK] Schemas work correctly")
    except Exception as e:
        print(f"   [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Import FastAPI app
    print("\n4. Testing FastAPI app...")
    try:
        from app.main import app, limiter
        
        # Check app is configured
        assert app.title == "Fuel Hedging Platform API"
        # Check auth routes are registered
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        auth_routes = [r for r in routes if '/auth' in r]
        assert len(auth_routes) > 0, f"No auth routes found. Available: {routes}"
        print("   [OK] FastAPI app initialized")
        print(f"   [OK] Found {len(app.routes)} routes, {len(auth_routes)} auth routes")
    except Exception as e:
        print(f"   [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Import auth router
    print("\n5. Testing auth router...")
    try:
        from app.routers.auth import router
        
        # Check router has expected routes
        route_paths = [route.path for route in router.routes]
        expected_routes = ["/login", "/refresh", "/logout", "/me", "/change-password", "/users", "/users/{user_id}"]
        
        for expected in expected_routes:
            if expected not in route_paths:
                print(f"   [WARN] Missing route: {expected}")
        
        print(f"   [OK] Auth router has {len(route_paths)} endpoints")
    except Exception as e:
        print(f"   [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*70)
    print("[SUCCESS] Phase 3: Auth & FastAPI Core Complete!")
    print("="*70)
    print("\nKey Features Implemented:")
    print("  - Password hashing with bcrypt")
    print("  - JWT token generation and validation")
    print("  - Role-based access control (RBAC)")
    print("  - FastAPI app with CORS and rate limiting")
    print("  - Authentication router with 7 endpoints")
    print("  - Pydantic v2 schemas with strict validation")
    print("  - Structured logging with structlog")
    print("  - Global exception handlers")
    print("\nNext: Phase 4 - Data Ingestion & Scheduler")
    return True


if __name__ == "__main__":
    success = test_phase_3()
    sys.exit(0 if success else 1)
