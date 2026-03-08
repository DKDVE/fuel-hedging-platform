# Quick Start Guide

## Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+ (or use Docker Compose)

## Setup Steps

### 1. Environment Variables

Create `python_engine/.env`:
```bash
DATABASE_URL=postgresql+asyncpg://hedge_user:hedge_password@localhost:5432/hedge_platform
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=generate-with-openssl-rand-hex-32-change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
FRONTEND_ORIGIN=http://localhost:5173
ENVIRONMENT=development
LOG_LEVEL=INFO
N8N_WEBHOOK_SECRET=generate-with-openssl-rand-hex-32-change-me
```

Create `frontend/.env.local`:
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### 2. Start Infrastructure (Option A: Docker Compose)

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

### 3. Start Infrastructure (Option B: Manual)

```bash
# Install Python dependencies
cd python_engine
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed development data
python app/db/seed.py

# Start API
uvicorn app.main:app --reload
```

```bash
# Install frontend dependencies
cd frontend
npm install

# Start development server
npm run dev
```

### 4. Access Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173
- **n8n**: http://localhost:5678
- **PostgreSQL**: localhost:5432

### 5. Default Users (Development)

| Role | Email | Password |
|------|-------|---admin@airline.com-------|
| Admin |  | admin123 |
| CFO | cfo@airline.com | cfo123 |
| Risk Manager | risk@airline.com | risk123 |
| Risk Manager (Test) | test@airline.com | testpass123 |
| Analyst | analyst@airline.com | analyst123 |

⚠️ **Change these passwords in production!**

## Development Workflow

### Backend Development

```bash
cd python_engine

# Run tests
pytest tests/ -v --cov

# Type checking
mypy app/ --strict

# Linting
ruff check app/
ruff format app/

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Frontend Development

```bash
cd frontend

# Run tests
npm test

# Type checking
npm run type-check

# Linting
npm run lint
npm run lint:fix

# Format code
npm run format

# Build for production
npm run build
```

## Troubleshooting

### Database Connection Issues

1. Ensure PostgreSQL is running: `docker-compose ps`
2. Check connection string in `.env`
3. Verify TimescaleDB extension: `docker-compose exec postgres psql -U hedge_user -d hedge_platform -c "SELECT * FROM pg_extension;"`

### Migration Issues

```bash
# Check current migration
alembic current

# View migration history
alembic history

# Downgrade if needed
alembic downgrade -1
```

### Frontend Build Issues

```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf .vite dist
npm run dev
```

## Project Structure

```
fuel-hedging-platform/
├── python_engine/         # FastAPI backend
│   ├── app/
│   │   ├── analytics/    # ML models & calculations
│   │   ├── db/           # Database models
│   │   ├── repositories/ # Data access layer
│   │   ├── auth/         # Authentication (Phase 3)
│   │   ├── routers/      # API endpoints (Phase 5)
│   │   └── services/     # Business logic (Phase 4-5)
│   ├── alembic/          # Database migrations
│   └── tests/            # Backend tests
├── frontend/              # React frontend
│   └── src/
│       ├── components/   # React components (Phase 6)
│       ├── pages/        # Page components (Phase 6)
│       ├── hooks/        # Custom hooks (Phase 6)
│       ├── lib/          # Utilities (Phase 6)
│       └── types/        # TypeScript types (Phase 6)
├── n8n/                   # Workflow automation (Phase 7)
├── data/                  # Dataset storage
├── models/                # ML model artifacts
└── docs/                  # Documentation

Current Status: Phase 0-2A Complete ✅
Next: Phase 2B - Analytics Implementations
```

## Next Steps

1. **Phase 2B**: Implement analytics modules (forecaster, VaR, optimizer, basis analyzer)
2. **Phase 3**: Build authentication & FastAPI core
3. **Phase 4**: Create data ingestion pipeline
4. **Phase 5**: Develop API routers
5. **Phase 6**: Build React frontend
6. **Phase 7**: Migrate n8n workflows
7. **Phase 8**: Set up CI/CD

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [React Documentation](https://react.dev/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Plan Document](plan.md) - Full implementation roadmap
