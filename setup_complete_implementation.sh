#!/bin/bash
# ============================================================
# Complete Implementation Script
# Executes all 4 phases of the implementation plan
# ============================================================

set -e  # Exit on error

PROJECT_ROOT="/mnt/e/fuel_hedging_proj"
cd "$PROJECT_ROOT"

echo "========================================="
echo "Fuel Hedging Platform - Complete Setup"
echo "========================================="
echo ""

# ============================================================
# PHASE 0: Prerequisites Check
# ============================================================
echo "[Phase 0] Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop with WSL2 integration."
    exit 1
fi

# Check required API keys
if [ -z "$EIA_API_KEY" ]; then
    echo "⚠️  EIA_API_KEY not set. Get free key from: https://www.eia.gov/opendata/register.php"
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set. Get from: https://platform.openai.com/api-keys"
fi

echo "✅ Prerequisites check complete"
echo ""

# ============================================================
# PHASE 1: Restore Core Implementation Files
# ============================================================
echo "[Phase 1] Creating core implementation files..."

# This script DOES NOT create the files - instead it documents what needs to be created
# The actual file creation is handled by the AI assistant

cat << 'EOF' > "$PROJECT_ROOT/docs/FILES_TO_CREATE.md"
# Files That Need To Be Created

## Priority 1: Core Data Layer (EIA + yfinance)
1. `python_engine/app/clients/__init__.py`
2. `python_engine/app/clients/base.py`
3. `python_engine/app/clients/eia.py`
4. `python_engine/app/clients/yfinance_client.py`
5. `python_engine/scripts/backfill_prices.py`

## Priority 2: SSE Event Broker
6. `python_engine/app/services/event_broker.py` ✅ CREATED

## Priority 3: N8N Workflow
7. `n8n/workflows/fuel_hedge_advisor_v2_complete.json`

## Priority 4: Frontend Components
8. `frontend/src/hooks/useRecommendationStream.ts`
9. `frontend/src/components/dashboard/PendingRecommendationBanner.tsx`
10. `frontend/src/components/ui/DataSourceBadge.tsx`

## Priority 5: Configuration
11. `.env.example`
12. `nginx/nginx.conf`
13. `docker-compose.prod.yml`

## Priority 6: Documentation
14. `docs/RUNBOOK.md`
15. `docs/API_REFERENCE.md`

EOF

echo "✅ Documentation created: docs/FILES_TO_CREATE.md"
echo ""

# ============================================================
# PHASE 2: Configuration
# ============================================================
echo "[Phase 2] Setting up configuration..."

# Create .env.example if it doesn't exist
if [ ! -f ".env.example" ]; then
    cat << 'EOF' > .env.example
# ============================================================
# Fuel Hedging Platform - Environment Variables
# ============================================================

# Database
DATABASE_URL=postgresql+asyncpg://hedge_user:hedge_password@postgres:5432/hedge_platform

# Redis
REDIS_URL=redis://redis:6379/0

# JWT Authentication
JWT_SECRET_KEY=generate-with-openssl-rand-hex-32-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Frontend
FRONTEND_ORIGIN=http://localhost:5173

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO

# N8N Integration
N8N_WEBHOOK_SECRET=generate-with-openssl-rand-hex-32-change-in-production
N8N_INTERNAL_URL=http://n8n:5678
N8N_TRIGGER_PATH=/webhook/fuel-hedge-trigger

# Market Data Sources
USE_LIVE_FEED=false
EIA_API_KEY=
MASSIVE_API_KEY=

# External APIs
CME_API_KEY=
ICE_API_KEY=
OPENAI_API_KEY=

# Monitoring (Optional)
SENTRY_DSN=
EOF
    echo "✅ Created .env.example"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env and add your API keys"
fi

echo ""

# ============================================================
# PHASE 3: Summary
# ============================================================
echo "========================================="
echo "Setup Script Complete!"
echo "========================================="
echo ""
echo "✅ Phase 0: Prerequisites checked"
echo "✅ Phase 1: File creation plan documented"
echo "✅ Phase 2: Configuration templates created"
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Review docs/FILES_TO_CREATE.md for list of files to create"
echo "2. Edit .env file and add your API keys:"
echo "   - EIA_API_KEY (free from eia.gov/opendata/register.php)"
echo "   - OPENAI_API_KEY (from platform.openai.com/api-keys)"
echo ""
echo "3. Generate strong secrets:"
echo "   openssl rand -hex 32  # For JWT_SECRET_KEY"
echo "   openssl rand -hex 32  # For N8N_WEBHOOK_SECRET"
echo ""
echo "4. Start Docker services:"
echo "   docker compose up -d"
echo ""
echo "5. Run tests:"
echo "   See docs/TESTING_GUIDE.md"
echo ""
echo "========================================="
