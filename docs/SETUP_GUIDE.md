# Environment Setup Instructions

## Prerequisites
- Python 3.10+
- PostgreSQL 15+ with TimescaleDB extension
- Redis 6.0+
- Node.js 18+ (for frontend)

## Python Backend Setup

### 1. Create Virtual Environment
```powershell
cd E:\fuel_hedging_proj\python_engine
python -m venv venv
```

### 2. Activate Virtual Environment
```powershell
.\venv\Scripts\activate
```

### 3. Install Core Dependencies
```powershell
pip install -r requirements-core.txt
```

### 4. Install Analytics Dependencies
```powershell
pip install -r requirements-analytics.txt
```

### 5. Fix bcrypt Compatibility (if needed)
```powershell
pip install "bcrypt==4.0.1"
```

## Environment Variables

Create a `.env` file in `python_engine/` directory (see `.env.example`):

```env
# Database
DATABASE_URL=postgresql+asyncpg://hedge_user:hedge_password@localhost:5432/hedge_platform

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# n8n
N8N_WEBHOOK_SECRET=<generate with: openssl rand -hex 32>

# CORS
FRONTEND_ORIGIN=http://localhost:5173

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## Database Setup

### 1. Install PostgreSQL 15 & TimescaleDB

### 2. Create Database
```sql
CREATE USER hedge_user WITH PASSWORD 'hedge_password';
CREATE DATABASE hedge_platform OWNER hedge_user;
\c hedge_platform
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

### 3. Run Migrations
```powershell
cd python_engine
alembic upgrade head
```

### 4. Seed Development Data
```powershell
python -m app.db.seed
```

## Running the Application

### Start FastAPI Server
```powershell
cd python_engine
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests
```powershell
# Test Phase 0-2A (structure)
python test_implementation.py

# Test Phase 3 (auth)
python test_phase_3.py

# Test analytics with real data
python test_real_data.py

# Test complete analytics suite
python test_full_analytics.py
```

## Frontend Setup (Phase 6)

### 1. Install Dependencies
```powershell
cd frontend
npm install
```

### 2. Start Development Server
```powershell
npm run dev
```

## Docker Compose (Alternative)

### Start All Services
```powershell
docker-compose up -d
```

This starts:
- FastAPI (port 8000)
- PostgreSQL 15 + TimescaleDB (port 5432)
- n8n (port 5678)
- Redis (port 6379)

### Run Migrations
```powershell
docker-compose exec api alembic upgrade head
```

## Verification

### Check API Health
```powershell
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "development"
}
```

### Check API Documentation
Visit: `http://localhost:8000/api/v1/docs`

## Troubleshooting

### bcrypt Version Issues
If you see `AttributeError: module 'bcrypt' has no attribute '__about__'`:
```powershell
pip uninstall bcrypt
pip install "bcrypt==4.0.1"
```

### SQLAlchemy Index Errors
Ensure `postgresql_ops` syntax is used for descending indexes:
```python
Index("idx_name", "column", postgresql_ops={"column": "DESC"})
```

### TensorFlow Warnings
To suppress oneDNN warnings:
```powershell
$env:TF_ENABLE_ONEDNN_OPTS="0"
```

### Missing LSTM Model
The LSTM forecaster requires a pre-trained model at `/models/lstm_model.h5`.
This will be trained during Phase 4 data ingestion.
Until then, the ensemble automatically sets LSTM weight to 0.

## Current Status

✅ **Operational**:
- Virtual environment with all dependencies
- Database models and migrations
- Repository pattern
- Analytics engine (forecasting, VaR, optimization, basis risk)
- Authentication system
- FastAPI application with 12 routes
- All tests passing

⏳ **Next Steps** (Phase 4):
- Data ingestion from CSV
- APScheduler for daily pipeline
- LSTM model training
- Data quality checks
- Circuit breaker pattern
