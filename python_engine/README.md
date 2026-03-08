## Fuel Hedging Platform - Backend

FastAPI + Python 3.11 backend for the aviation fuel hedging platform.

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Environment Variables

Create a `.env` file in the `python_engine` directory with the following variables:

```env
DATABASE_URL=postgresql+asyncpg://hedge_user:hedge_password@localhost:5432/hedge_platform
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
FRONTEND_ORIGIN=http://localhost:5173
ENVIRONMENT=development
LOG_LEVEL=INFO
N8N_WEBHOOK_SECRET=<generate with: openssl rand -hex 32>
```

### Testing

```bash
pytest tests/ -v --cov
```
