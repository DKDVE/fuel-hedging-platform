"""Mock FastAPI backend for frontend testing without database.

This provides mock endpoints to test the frontend UI.
"""

from fastapi import FastAPI, HTTPException, Request, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import random
import math
import json
import asyncio
from typing import List, Dict, Any, Optional
from sse_starlette.sse import EventSourceResponse
from jose import jwt, JWTError

app = FastAPI(title="Mock Hedge Platform API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# RBAC SYSTEM
# ============================================================

MOCK_USERS = {
    "analyst@airline.com": {"role": "analyst", "password": "analyst123", "full_name": "Alice Analyst"},
    "risk@airline.com": {"role": "risk_manager", "password": "risk123", "full_name": "Robert Risk"},
    "cfo@airline.com": {"role": "cfo", "password": "cfo123", "full_name": "Carol CFO"},
    "admin@airline.com": {"role": "admin", "password": "admin123", "full_name": "Admin User"},
    "test@airline.com": {"role": "risk_manager", "password": "testpass123", "full_name": "Test User"},
}

ROLE_PERMISSIONS = {
    'analyst': {
        'read:analytics',
        'read:positions',
    },
    'risk_manager': {
        'read:analytics',
        'read:positions',
        'read:audit',
        'approve:recommendation',
        'export:data',
    },
    'cfo': {
        'read:analytics',
        'read:positions',
        'read:audit',
        'approve:recommendation',
        'escalate:recommendation',
        'export:data',
    },
    'admin': {
        'read:analytics',
        'read:positions',
        'read:audit',
        'approve:recommendation',
        'escalate:recommendation',
        'edit:config',
        'manage:users',
        'trigger:pipeline',
        'export:data',
    },
}

JWT_SECRET = "dev-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"

def get_current_user_from_token(access_token: Optional[str]) -> Dict[str, Any]:
    """Decode JWT and return user info. Raise 401 if invalid."""
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please log in."
        )
    
    try:
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token. Please log in again."
        )

def check_permission(request: Request, required_permission: str):
    """Check if user has required permission. Raise 403 if not."""
    token = request.cookies.get("access_token")
    user = get_current_user_from_token(token)
    role = user.get("role")
    
    permissions = ROLE_PERMISSIONS.get(role, set())
    
    if required_permission not in permissions:
        raise HTTPException(
            status_code=403,
            detail={
                "detail": f"Your role ({role}) does not have permission to perform this action.",
                "error_code": "insufficient_permissions",
                "required_permission": required_permission
            }
        )
    
    return user

# ============================================================
# MOCK DATA
# ============================================================

MOCK_USER = {
    "id": 1,
    "email": "admin@airline.com",
    "full_name": "Admin User",
    "role": "admin",
    "is_active": True,
    "created_at": "2024-01-01T00:00:00Z"
}

def generate_mock_prices():
    """Generate mock price data."""
    base_prices = {
        "Jet Fuel": 95.50,
        "Brent Crude": 82.30,
        "WTI Crude": 78.90,
        "Heating Oil": 92.40,
        "Crack Spread": 13.20,
        "Volatility Index": 18.50
    }
    return [
        {
            "instrument": name,
            "price": base_price + random.uniform(-2, 2),
            "change_pct": random.uniform(-3, 3),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        for name, base_price in base_prices.items()
    ]

@app.get("/")
async def root():
    return {"message": "Mock Hedge Platform API", "status": "running"}

@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}

@app.get("/healthz")
async def healthcheck():
    return {"status": "ok"}

# Real-time streaming price data
PRICE_STATE = {
    "jet_fuel": 94.50,
    "heating_oil": 89.20,
    "brent": 82.10,
    "wti": 79.40,
    "ticks": []
}

def generate_tick():
    """Generate a realistic price tick using random walk."""
    # Apply small random changes (±0.3%)
    for key in ["jet_fuel", "heating_oil", "brent", "wti"]:
        change = random.uniform(-0.003, 0.003)
        PRICE_STATE[key] *= (1 + change)
        PRICE_STATE[key] = max(PRICE_STATE[key], 1.0)  # Prevent negative prices
    
    tick = {
        "time": datetime.utcnow().isoformat() + "Z",
        "jet_fuel_spot": round(PRICE_STATE["jet_fuel"], 2),
        "heating_oil_futures": round(PRICE_STATE["heating_oil"], 2),
        "brent_futures": round(PRICE_STATE["brent"], 2),
        "wti_futures": round(PRICE_STATE["wti"], 2),
        "crack_spread": round(PRICE_STATE["jet_fuel"] - PRICE_STATE["heating_oil"], 2),
        "volatility_index": round(random.uniform(15, 22), 2),
        "source": "simulation",
        "quality_flag": None
    }
    
    # Keep last 500 ticks
    PRICE_STATE["ticks"].append(tick)
    if len(PRICE_STATE["ticks"]) > 500:
        PRICE_STATE["ticks"] = PRICE_STATE["ticks"][-500:]
    
    return tick

# Initialize with some historical ticks
for _ in range(100):
    generate_tick()

@app.get("/api/v1/stream/prices")
async def stream_prices():
    """SSE endpoint for real-time price stream."""
    async def event_generator():
        # Send historical ticks first
        history_ticks = PRICE_STATE["ticks"][-100:]
        yield {
            "event": "history",
            "data": json.dumps({
                "type": "history",
                "ticks": history_ticks
            })
        }
        
        # Then stream live ticks
        while True:
            await asyncio.sleep(2)  # 2 second intervals
            tick = generate_tick()
            yield {
                "event": "tick",
                "data": json.dumps({
                    "type": "tick",
                    "tick": tick
                })
            }
    
    return EventSourceResponse(event_generator())

@app.get("/api/v1/stream/status")
async def stream_status():
    """Get current data source status."""
    latest = PRICE_STATE["ticks"][-1] if PRICE_STATE["ticks"] else None
    prev = PRICE_STATE["ticks"][-2] if len(PRICE_STATE["ticks"]) > 1 else None
    
    instruments = {}
    if latest and prev:
        for name, key in [("jet_fuel", "jet_fuel_spot"), ("heating_oil", "heating_oil_futures"), 
                          ("brent", "brent_futures"), ("wti", "wti_futures")]:
            current = latest[key]
            previous = prev[key]
            change_pct = ((current - previous) / previous * 100) if previous > 0 else 0.0
            instruments[name] = {
                "last_price": current,
                "change_pct": round(change_pct, 2)
            }
    
    return {
        "mode": "simulation",
        "source_healthy": True,
        "last_tick_at": latest["time"] if latest else None,
        "ticks_per_minute": 30.0,
        "instruments": instruments
    }

@app.post("/api/v1/auth/login")
async def login(request: Request):
    body = await request.json()
    email = body.get("email")
    password = body.get("password")
    
    # Validate credentials
    user_data = MOCK_USERS.get(email)
    if not user_data or user_data["password"] != password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    # Create JWT with user info
    token_data = {
        "sub": email,
        "email": email,
        "role": user_data["role"],
        "full_name": user_data["full_name"],
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    
    access_token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # Create response with httpOnly cookie
    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": email,
            "email": email,
            "full_name": user_data["full_name"],
            "role": user_data["role"],
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z"
        }
    })
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=1800,  # 30 minutes
        samesite="lax"
    )
    
    return response

@app.get("/api/v1/auth/me")
async def get_current_user(access_token: Optional[str] = Cookie(None)):
    user = get_current_user_from_token(access_token)
    return {
        "id": user.get("email"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "role": user.get("role"),
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z"
    }

@app.get("/api/v1/market/live-prices")
async def get_live_prices():
    return generate_mock_prices()

@app.get("/api/v1/market-data/live-feed")
async def get_live_market_feed():
    """Generate realistic price ticks for live chart."""
    base_date = datetime.utcnow()
    ticks = []
    
    # Starting prices
    jet_fuel_base = 95.50
    heating_oil_base = 92.40
    brent_base = 82.30
    wti_base = 78.90
    
    # Generate last 100 price ticks (5 minutes each = ~8 hours of data)
    for i in range(100):
        # Simulate correlated price movements with random walk
        jet_fuel_change = random.gauss(0, 0.3)
        
        # Other instruments move with jet fuel but with different correlation
        heating_oil_change = jet_fuel_change * 0.85 + random.gauss(0, 0.2)
        brent_change = jet_fuel_change * 0.60 + random.gauss(0, 0.25)
        wti_change = jet_fuel_change * 0.55 + random.gauss(0, 0.25)
        
        jet_fuel_base += jet_fuel_change
        heating_oil_base += heating_oil_change
        brent_base += brent_change
        wti_base += wti_change
        
        # Add some intraday trends
        trend_factor = 0.02 * math.sin(i / 20)
        jet_fuel_base += trend_factor
        heating_oil_base += trend_factor * 0.8
        brent_base += trend_factor * 0.6
        wti_base += trend_factor * 0.5
        
        ticks.append({
            "time": (base_date - timedelta(minutes=5 * (100 - i))).isoformat() + "Z",
            "jet_fuel_spot": round(jet_fuel_base, 2),
            "heating_oil_futures": round(heating_oil_base, 2),
            "brent_crude_futures": round(brent_base, 2),
            "wti_crude_futures": round(wti_base, 2),
        })
    
    return ticks

@app.get("/api/v1/analytics/forecast/latest")
async def get_latest_forecast(request: Request):
    check_permission(request, 'read:analytics')
    base_date = datetime.now().date()
    base_price = 95.5
    volatility = 2.5
    
    # Generate more realistic forecast with increasing uncertainty
    forecast_points = []
    for i in range(90):  # Extended to 90 days
        day_volatility = volatility * (1 + i * 0.02)  # Uncertainty increases over time
        actual_price = None
        
        # Only show actuals for past 30 days
        if i < 30:
            actual_price = base_price + random.gauss(0, volatility)
            base_price = actual_price  # Walk forward
        
        forecast_price = base_price + i * 0.15 + random.gauss(0, volatility)
        
        forecast_points.append({
            "date": (base_date + timedelta(days=i - 30)).isoformat(),
            "actual": actual_price,
            "forecast": forecast_price,
            "lower_bound": forecast_price - 1.96 * day_volatility,
            "upper_bound": forecast_price + 1.96 * day_volatility
        })
    
    return {
        "forecast_id": 1,
        "model_used": "ensemble",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "horizon_days": 90,
        "forecast_points": forecast_points,
        "metrics": {
            "mape": round(random.uniform(5.5, 7.5), 2),
            "rmse": round(random.uniform(2.8, 3.5), 2),
            "r2": round(random.uniform(0.85, 0.92), 3)
        }
    }

@app.get("/api/v1/analytics/summary")
async def get_analytics_summary(request: Request):
    check_permission(request, 'read:analytics')
    """Get analytics summary for dashboard."""
    return {
        "current_var_usd": 3850000,  # $3.85M VaR
        "current_hedge_ratio": 0.72,  # 72% hedge ratio
        "collateral_pct": 11.2,  # 11.2% collateral
        "mape_pct": 6.8,  # 6.8% forecast error
        "var_reduction_pct": 42.0,  # 42% VaR reduction
        "ifrs9_compliance_status": "COMPLIANT",
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/api/v1/analytics/run")
async def trigger_analytics_run(request: Request):
    check_permission(request, 'trigger:pipeline')
    """Trigger analytics pipeline - sends request to n8n."""
    import os
    
    # Get n8n webhook URL from environment
    n8n_url = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook/fuel-hedge-advisor")
    
    try:
        # Try to import httpx and send request
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    n8n_url,
                    json={
                        "trigger_type": "manual",
                        "triggered_by": "dashboard",
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                )
                response.raise_for_status()
            n8n_status = "triggered"
        except (ImportError, Exception):
            # If httpx not available or n8n fails, continue with mock response
            n8n_status = "mock"
        
        return {
            "status": "triggered",
            "message": "Analytics pipeline started successfully" if n8n_status == "triggered" else "Analytics pipeline started (mock mode)",
            "run_id": f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "triggered_at": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "status": "triggered",
            "message": "Analytics pipeline started (mock mode)",
            "run_id": f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "triggered_at": datetime.utcnow().isoformat() + "Z"
        }


@app.get("/api/v1/analytics/history")
async def get_analytics_history(page: int = 1, limit: int = 20):
    """Get historical analytics runs with walk-forward VaR and MAPE data."""
    items = []
    
    # Generate realistic historical data
    base_date = datetime.utcnow()
    base_dynamic_var = 8500000  # $8.5M
    base_static_var = 13200000  # $13.2M
    base_mape = 6.5
    
    for i in range(1, limit + 1):
        # Add some trending and noise
        trend_factor = 1 - (i * 0.005)
        noise = random.gauss(0, 0.1)
        
        dynamic_var = base_dynamic_var * (trend_factor + noise)
        static_var = base_static_var * (trend_factor + noise * 0.5)
        mape = base_mape + random.gauss(0, 1.2)
        
        # Mark every 30 days as retraining
        is_retraining = (i % 30) == 0
        
        items.append({
            "date": (base_date - timedelta(days=limit - i)).isoformat(),
            "run_id": i,
            "timestamp": (base_date - timedelta(days=limit - i)).isoformat(),
            "model_used": random.choice(["arima", "xgboost", "lstm", "ensemble"]),
            "mape": round(max(4.0, min(12.0, mape)), 2),
            "hedge_ratio": round(random.uniform(0.65, 0.80), 2),
            "var_reduction": round(random.uniform(0.35, 0.50), 2),
            "dynamic_var": round(dynamic_var, 2),
            "static_var": round(static_var, 2),
            "retraining_date": is_retraining,
            "status": random.choice(["COMPLETED", "COMPLETED", "COMPLETED", "FAILED"])
        })
    
    return {
        "items": items,
        "total": 200,
        "page": page,
        "limit": limit
    }

@app.get("/api/v1/analytics/var-walk-forward")
async def get_var_walk_forward(days: int = 90):
    """Get walk-forward VaR analysis data."""
    base_date = datetime.utcnow()
    data_points = []
    
    base_dynamic_var = 8500000
    base_static_var = 13200000
    
    for i in range(days):
        # Simulate market cycles
        cycle_factor = 1 + 0.2 * math.sin(i / 15)
        trend_factor = 1 - (i * 0.002)
        noise = random.gauss(0, 0.08)
        
        dynamic_var = base_dynamic_var * cycle_factor * trend_factor * (1 + noise)
        static_var = base_static_var * cycle_factor * trend_factor * (1 + noise * 0.5)
        
        # Mark every 30 days as retraining event
        is_retraining = (i % 30) == 0
        
        data_points.append({
            "date": (base_date - timedelta(days=days - i)).isoformat(),
            "dynamic_var": round(dynamic_var, 2),
            "static_var": round(static_var, 2),
            "retraining_date": is_retraining
        })
    
    return {
        "data_points": data_points,
        "summary": {
            "avg_dynamic_var": round(sum(d["dynamic_var"] for d in data_points) / len(data_points), 2),
            "avg_static_var": round(sum(d["static_var"] for d in data_points) / len(data_points), 2),
            "improvement_pct": round(
                ((sum(d["static_var"] for d in data_points) - sum(d["dynamic_var"] for d in data_points)) 
                 / sum(d["static_var"] for d in data_points)) * 100, 
                2
            )
        }
    }

@app.get("/api/v1/analytics/mape-history")
async def get_mape_history(days: int = 180):
    """Get rolling MAPE history."""
    base_date = datetime.utcnow()
    data_points = []
    
    base_mape = 6.8
    target_threshold = 8.0
    alert_threshold = 10.0
    
    for i in range(days):
        # Simulate improving accuracy over time with some volatility spikes
        trend = -0.01 * (i / 30)  # Gradual improvement
        seasonal = 1.5 * math.sin(i / 20)  # Seasonal variation
        noise = random.gauss(0, 0.8)
        
        # Occasional accuracy degradation events
        if i % 45 == 0 and i > 0:
            noise += random.uniform(2, 4)
        
        mape = base_mape + trend + seasonal + noise
        mape = max(4.0, min(14.0, mape))  # Clamp to reasonable range
        
        data_points.append({
            "date": (base_date - timedelta(days=days - i)).isoformat(),
            "mape": round(mape, 2)
        })
    
    within_target = sum(1 for d in data_points if d["mape"] < target_threshold)
    
    return {
        "data_points": data_points,
        "target_threshold": target_threshold,
        "alert_threshold": alert_threshold,
        "summary": {
            "avg_mape": round(sum(d["mape"] for d in data_points) / len(data_points), 2),
            "min_mape": round(min(d["mape"] for d in data_points), 2),
            "max_mape": round(max(d["mape"] for d in data_points), 2),
            "within_target_pct": round((within_target / len(data_points)) * 100, 1),
            "violations": sum(1 for d in data_points if d["mape"] > alert_threshold)
        }
    }

@app.get("/api/v1/recommendations/pending")
async def get_pending_recommendations(request: Request):
    check_permission(request, 'approve:recommendation')
    return [{
        "id": "rec_1a2b3c4d5e6f7g8h",  # UUID-like string
        "run_id": "run_9z8y7x6w5v4u3t2s",  # UUID-like string
        "status": "PENDING_APPROVAL",
        "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z",
        "expires_at": (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
        # Top-level fields for display
        "optimal_hedge_ratio": 0.72,
        "expected_var_reduction": 0.42,
        "hedge_effectiveness_r2": 0.89,
        "collateral_impact": 0.125,
        "constraints_satisfied": True,
        "ifrs9_eligible": True,
        "action_required": True,
        "risk_level": "MODERATE",
        "recommendation_text": "Current market conditions favor a hedge ratio of 72% with diversified instrument mix. All risk constraints satisfied.",
        "instrument_mix": {
            "futures": 0.45,
            "options": 0.30,
            "collars": 0.15,
            "swaps": 0.10
        },
        # Detailed optimization result
        "optimization_result": {
            "optimal_hedge_ratio": 0.72,
            "expected_var_reduction": 0.42,
            "instrument_mix": {
                "futures": 0.45,
                "options": 0.30,
                "collars": 0.15,
                "swaps": 0.10
            },
            "collateral_required_usd": 12500000,
            "ifrs9_eligible": True,
            "ifrs9_r2": 0.89
        },
        "agent_outputs": [
            {
                "agent_id": "basis_risk",
                "risk_level": "LOW",
                "recommendation": "Hedge ratio within acceptable limits",
                "metrics": {"hedge_ratio": 0.72, "basis_correlation": 0.94},
                "constraints_satisfied": True,
                "action_required": False,
                "ifrs9_eligible": True,
                "generated_at": datetime.utcnow().isoformat() + "Z"
            },
            {
                "agent_id": "liquidity",
                "risk_level": "MODERATE",
                "recommendation": "Adequate market depth",
                "metrics": {"collateral_pct": 0.125},
                "constraints_satisfied": True,
                "action_required": True,
                "ifrs9_eligible": None,
                "generated_at": datetime.utcnow().isoformat() + "Z"
            },
            {
                "agent_id": "operational",
                "risk_level": "LOW",
                "recommendation": "Operational capacity sufficient",
                "metrics": {"max_coverage": 0.85},
                "constraints_satisfied": True,
                "action_required": False,
                "ifrs9_eligible": None,
                "generated_at": datetime.utcnow().isoformat() + "Z"
            },
            {
                "agent_id": "ifrs9",
                "risk_level": "LOW",
                "recommendation": "Highly effective hedge relationship",
                "metrics": {"prospective_r2": 0.89, "retrospective_ratio": 1.02},
                "constraints_satisfied": True,
                "action_required": False,
                "ifrs9_eligible": True,
                "generated_at": datetime.utcnow().isoformat() + "Z"
            },
            {
                "agent_id": "macro",
                "risk_level": "MODERATE",
                "recommendation": "Volatility elevated but manageable",
                "metrics": {"volatility_idx": 18.5},
                "constraints_satisfied": True,
                "action_required": True,
                "ifrs9_eligible": None,
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        ],
        "approvals": [
            {
                "id": "appr_abc123def456",
                "approver_id": "user_789xyz012",
                "approver_name": "John Smith",
                "approver_role": "RISK_MANAGER",
                "decision": "APPROVED",
                "created_at": (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z",
                "comments": "Hedge ratio looks good. Risk metrics are within acceptable limits.",
                "response_time_minutes": 45
            }
        ]
    }]

@app.get("/api/v1/recommendations")
async def get_recommendations(request: Request, page: int = 1, limit: int = 10):
    """List all recommendations with pagination."""
    check_permission(request, 'read:analytics')
    items = []
    for i in range(1, limit + 1):
        status = random.choice(["PENDING_APPROVAL", "APPROVED", "APPROVED", "REJECTED"])
        hedge_ratio = round(random.uniform(0.65, 0.80), 2)
        var_reduction = round(random.uniform(0.35, 0.50), 2)
        r2_value = round(random.uniform(0.82, 0.95), 2)
        collateral_impact = round(random.uniform(0.10, 0.15), 3)
        
        # Generate instrument mix
        futures_pct = round(random.uniform(0.35, 0.50), 2)
        options_pct = round(random.uniform(0.20, 0.35), 2)
        remaining = 1.0 - futures_pct - options_pct
        collars_pct = round(remaining * random.uniform(0.4, 0.7), 2)
        swaps_pct = round(remaining - collars_pct, 2)
        
        items.append({
            "id": f"rec_{i:016x}",
            "run_id": f"run_{i:016x}",
            "status": status,
            "created_at": (datetime.utcnow() - timedelta(days=i)).isoformat() + "Z",
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z" if status == "PENDING_APPROVAL" else None,
            "optimal_hedge_ratio": hedge_ratio,
            "expected_var_reduction": var_reduction,
            "hedge_effectiveness_r2": r2_value,
            "collateral_impact": collateral_impact,
            "constraints_satisfied": True,
            "ifrs9_eligible": r2_value >= 0.80,
            "action_required": status == "PENDING_APPROVAL",
            "risk_level": random.choice(["LOW", "LOW", "MODERATE"]),
            "recommendation_text": f"Historical recommendation #{i}: Hedge ratio of {hedge_ratio*100:.0f}% recommended based on market conditions at the time.",
            "instrument_mix": {
                "futures": futures_pct,
                "options": options_pct,
                "collars": collars_pct,
                "swaps": swaps_pct
            },
            "optimization_result": {
                "optimal_hedge_ratio": hedge_ratio,
                "expected_var_reduction": var_reduction,
                "instrument_mix": {
                    "futures": futures_pct,
                    "options": options_pct,
                    "collars": collars_pct,
                    "swaps": swaps_pct
                },
                "collateral_required_usd": int(collateral_impact * 100000000),
                "ifrs9_eligible": r2_value >= 0.80,
                "ifrs9_r2": r2_value
            },
            "agent_outputs": [
                {
                    "agent_id": "basis_risk",
                    "risk_level": random.choice(["LOW", "LOW", "MODERATE"]),
                    "recommendation": "Basis risk within acceptable limits",
                    "metrics": {"hedge_ratio": hedge_ratio, "basis_correlation": round(random.uniform(0.85, 0.95), 2)},
                    "constraints_satisfied": True,
                    "action_required": False,
                    "ifrs9_eligible": True,
                    "generated_at": (datetime.utcnow() - timedelta(days=i)).isoformat() + "Z"
                },
                {
                    "agent_id": "liquidity",
                    "risk_level": random.choice(["LOW", "MODERATE"]),
                    "recommendation": "Liquidity conditions adequate",
                    "metrics": {"collateral_pct": collateral_impact},
                    "constraints_satisfied": True,
                    "action_required": collateral_impact > 0.13,
                    "ifrs9_eligible": None,
                    "generated_at": (datetime.utcnow() - timedelta(days=i)).isoformat() + "Z"
                },
                {
                    "agent_id": "operational",
                    "risk_level": "LOW",
                    "recommendation": "Operational capacity sufficient",
                    "metrics": {"max_coverage": round(random.uniform(0.75, 0.90), 2)},
                    "constraints_satisfied": True,
                    "action_required": False,
                    "ifrs9_eligible": None,
                    "generated_at": (datetime.utcnow() - timedelta(days=i)).isoformat() + "Z"
                },
                {
                    "agent_id": "ifrs9",
                    "risk_level": "LOW" if r2_value >= 0.85 else "MODERATE",
                    "recommendation": "Hedge effectiveness meets IFRS 9 requirements",
                    "metrics": {"prospective_r2": r2_value, "retrospective_ratio": round(random.uniform(0.95, 1.10), 2)},
                    "constraints_satisfied": True,
                    "action_required": False,
                    "ifrs9_eligible": True,
                    "generated_at": (datetime.utcnow() - timedelta(days=i)).isoformat() + "Z"
                },
                {
                    "agent_id": "macro",
                    "risk_level": random.choice(["LOW", "MODERATE", "MODERATE"]),
                    "recommendation": "Macroeconomic conditions stable",
                    "metrics": {"volatility_idx": round(random.uniform(14.0, 24.0), 1)},
                    "constraints_satisfied": True,
                    "action_required": False,
                    "ifrs9_eligible": None,
                    "generated_at": (datetime.utcnow() - timedelta(days=i)).isoformat() + "Z"
                }
            ],
            "approvals": [
                {
                    "id": f"appr_{i:012x}",
                    "approver_id": f"user_{random.randint(100, 999)}",
                    "approver_name": random.choice(["John Smith", "Jane Doe", "Mike Johnson", "Sarah Williams"]),
                    "approver_role": random.choice(["RISK_MANAGER", "CFO", "ADMIN"]),
                    "decision": "APPROVED" if status == "APPROVED" else "REJECTED" if status == "REJECTED" else "PENDING",
                    "created_at": (datetime.utcnow() - timedelta(days=i, hours=2)).isoformat() + "Z" if status in ["APPROVED", "REJECTED"] else None,
                    "comments": random.choice([
                        "Risk metrics look good",
                        "Approved with monitoring",
                        "Within risk tolerance",
                        "IFRS 9 compliant"
                    ]) if status == "APPROVED" else "Risk too high" if status == "REJECTED" else None,
                    "response_time_minutes": random.randint(30, 180) if status in ["APPROVED", "REJECTED"] else None
                }
            ] if status in ["APPROVED", "REJECTED"] else []
        })
    return {
        "items": items,
        "total": 100,
        "page": page,
        "limit": limit,
        "pages": 10
    }

@app.post("/api/v1/recommendations/{recommendation_id}/approve")
async def approve_recommendation(recommendation_id: str, request: Request):
    """Approve a recommendation."""
    check_permission(request, 'approve:recommendation')
    body = await request.json()
    return {
        "success": True,
        "recommendation_id": recommendation_id,
        "status": "APPROVED",
        "approver": "current_user",
        "approved_at": datetime.utcnow().isoformat() + "Z",
        "comments": body.get("comments", "")
    }

@app.post("/api/v1/recommendations/{recommendation_id}/reject")
async def reject_recommendation(recommendation_id: str, request: Request):
    """Reject a recommendation."""
    check_permission(request, 'approve:recommendation')
    body = await request.json()
    return {
        "success": True,
        "recommendation_id": recommendation_id,
        "status": "REJECTED",
        "approver": "current_user",
        "rejected_at": datetime.utcnow().isoformat() + "Z",
        "comments": body.get("comments", "")
    }

@app.get("/api/v1/analytics/hypotheses")
async def get_hypotheses():
    return [
        {
            "hypothesis_id": "H1",
            "name": "Dynamic HR > Static",
            "status": "PASS",
            "metric_value": 0.42,
            "threshold": 0.40,
            "last_tested": datetime.utcnow().isoformat() + "Z"
        },
        {
            "hypothesis_id": "H2",
            "name": "Basis Risk < 5%",
            "status": "PASS",
            "metric_value": 0.028,
            "threshold": 0.05,
            "last_tested": datetime.utcnow().isoformat() + "Z"
        },
        {
            "hypothesis_id": "H3",
            "name": "MAPE < 8%",
            "status": "PASS",
            "metric_value": 6.8,
            "threshold": 8.0,
            "last_tested": datetime.utcnow().isoformat() + "Z"
        },
        {
            "hypothesis_id": "H4",
            "name": "IFRS 9 R² > 80%",
            "status": "PASS",
            "metric_value": 0.89,
            "threshold": 0.80,
            "last_tested": datetime.utcnow().isoformat() + "Z"
        }
    ]

@app.get("/api/v1/analytics/walk-forward")
async def get_walk_forward():
    base_date = datetime.now().date() - timedelta(days=180)
    return [
        {
            "date": (base_date + timedelta(days=i)).isoformat(),
            "dynamic_var": 850000 + random.uniform(-100000, 50000),
            "static_var": 1200000 + random.uniform(-150000, 100000)
        }
        for i in range(0, 180, 7)
    ]

@app.get("/api/v1/analytics/mape-history")
async def get_mape_history():
    base_date = datetime.now().date() - timedelta(days=90)
    return [
        {
            "date": (base_date + timedelta(days=i)).isoformat(),
            "mape": 6.5 + random.uniform(-2, 2)
        }
        for i in range(90)
    ]

@app.get("/api/v1/positions/open")
async def get_open_positions():
    return [
        {
            "position_id": i,
            "instrument": random.choice(["Brent Futures", "WTI Options", "Heating Oil Collar"]),
            "hedge_ratio": round(random.uniform(0.65, 0.85), 2),
            "notional_usd": random.randint(5000000, 15000000),
            "collateral_usd": random.randint(500000, 2000000),
            "ifrs9_r2": round(random.uniform(0.82, 0.95), 2),
            "status": random.choice(["OPEN", "OPEN", "CLOSED"]),
            "entry_date": (datetime.now().date() - timedelta(days=random.randint(1, 90))).isoformat()
        }
        for i in range(1, 16)
    ]

@app.get("/api/v1/positions/collateral-summary")
async def get_collateral_summary():
    return {
        "total_collateral_usd": 18500000,
        "collateral_limit_usd": 125000000,
        "utilization_pct": 0.148,
        "threshold_pct": 0.15
    }

@app.get("/api/v1/audit/approvals")
async def get_audit_approvals(request: Request):
    check_permission(request, 'read:audit')
    return [
        {
            "recommendation_id": i,
            "status": random.choice(["APPROVED", "APPROVED", "REJECTED"]),
            "submitted_at": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat() + "Z",
            "approved_at": (datetime.now() - timedelta(days=random.randint(0, 29))).isoformat() + "Z",
            "approver_name": random.choice(["John Smith", "Jane Doe", "Mike Johnson"]),
            "approver_role": random.choice(["CFO", "ADMIN", "RISK_MANAGER"])
        }
        for i in range(1, 21)
    ]

@app.get("/api/v1/audit/ifrs9")
async def get_ifrs9_compliance():
    base_date = datetime.now().date()
    return [
        {
            "period_start": (base_date - timedelta(days=(i+1)*30)).isoformat(),
            "period_end": (base_date - timedelta(days=i*30)).isoformat(),
            "prospective_r2": round(random.uniform(0.82, 0.95), 2),
            "retrospective_ratio": round(random.uniform(0.95, 1.15), 2),
            "status": random.choice(["PASS", "PASS", "PASS", "WARN"]),
            "designation": "HIGHLY_EFFECTIVE"
        }
        for i in range(12)
    ]

@app.get("/api/v1/config/constraints")
async def get_constraints():
    return {
        "hr_hard_cap": 0.80,
        "hr_soft_warn": 0.70,
        "collateral_limit": 0.15,
        "ifrs9_r2_min": 0.80,
        "mape_target": 8.0
    }

@app.patch("/api/v1/config/constraints")
async def update_constraints(request: Request):
    body = await request.json()
    return body

@app.get("/api/v1/health/sources")
async def get_api_health():
    return [
        {
            "source": "EIA API",
            "status": "healthy",
            "last_fetch": (datetime.utcnow() - timedelta(minutes=random.randint(1, 60))).isoformat() + "Z",
            "latency_ms": random.randint(100, 500)
        },
        {
            "source": "CME API",
            "status": "healthy",
            "last_fetch": (datetime.utcnow() - timedelta(minutes=random.randint(1, 60))).isoformat() + "Z",
            "latency_ms": random.randint(100, 500)
        },
        {
            "source": "ICE API",
            "status": "degraded",
            "last_fetch": (datetime.utcnow() - timedelta(minutes=random.randint(1, 60))).isoformat() + "Z",
            "latency_ms": random.randint(800, 1500)
        },
        {
            "source": "n8n Webhook",
            "status": "healthy",
            "last_fetch": (datetime.utcnow() - timedelta(minutes=random.randint(1, 60))).isoformat() + "Z",
            "latency_ms": random.randint(50, 300)
        }
    ]

@app.patch("/api/v1/recommendations/{rec_id}")
async def update_recommendation(rec_id: int, request: Request):
    body = await request.json()
    return {"recommendation_id": rec_id, "status": body.get("status", "APPROVED")}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Mock Backend API on http://localhost:8000")
    print("📊 Frontend can connect at http://localhost:5173")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
