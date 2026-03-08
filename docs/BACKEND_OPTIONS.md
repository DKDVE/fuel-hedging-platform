# 🔧 BACKEND OPTIONS FOR LOCAL TESTING

You have **3 options** to run the full backend with database:

---

## ✅ **OPTION 1: Use Mock Backend (Currently Running)**

**Best for**: Testing frontend UI only  
**Status**: ✅ Already running on port 8000

This is what's currently running - a simplified mock API that returns realistic data without requiring a database. Perfect for testing all frontend features.

**Pros**:
- ✅ No database setup needed
- ✅ Fast and lightweight
- ✅ All frontend features work
- ✅ Realistic mock data

**Cons**:
- ❌ Not the real backend
- ❌ No data persistence
- ❌ No ML analytics

**Current Status**: This is what you're using now and it's working perfectly!

---

## 🐳 **OPTION 2: Use Docker Compose (Recommended for Full Backend)**

**Best for**: Running the complete backend with PostgreSQL, Redis, and n8n

### **Start Everything**
```bash
cd /mnt/e/fuel_hedging_proj
docker compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- FastAPI Backend (port 8000)
- n8n Worker (port 5678)

### **Initialize Database**
```bash
# Wait for services to be healthy (30-60 seconds)
docker compose ps

# Run migrations
docker compose exec api alembic upgrade head

# Seed initial data
docker compose exec api python -m app.db.seed
```

### **Check Status**
```bash
docker compose ps
docker compose logs api
```

### **Stop Everything**
```bash
docker compose down
```

**Pros**:
- ✅ Full production-like environment
- ✅ Real PostgreSQL database
- ✅ All analytics features work
- ✅ Easy to start/stop

**Cons**:
- ❌ Requires Docker Desktop with WSL2 integration
- ❌ More resource-intensive
- ❌ Slower startup time

---

## 📦 **OPTION 3: Install PostgreSQL Locally**

**Best for**: Running backend without Docker

### **Install PostgreSQL**
```bash
# On Ubuntu/WSL2
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL
sudo service postgresql start

# Create database and user
sudo -u postgres psql
```

In PostgreSQL prompt:
```sql
CREATE DATABASE hedge_platform;
CREATE USER hedge_user WITH PASSWORD 'hedge_password';
GRANT ALL PRIVILEGES ON DATABASE hedge_platform TO hedge_user;
\q
```

### **Install Redis**
```bash
sudo apt install redis-server
sudo service redis-server start
```

### **Create .env File**
```bash
cd /mnt/e/fuel_hedging_proj/python_engine
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://hedge_user:hedge_password@localhost:5432/hedge_platform
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=dev-local-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
FRONTEND_ORIGIN=http://localhost:5173
ENVIRONMENT=development
LOG_LEVEL=INFO
N8N_WEBHOOK_SECRET=dev-n8n-secret
EOF
```

### **Run Migrations and Seed**
```bash
cd /mnt/e/fuel_hedging_proj/python_engine
source venv/bin/activate
alembic upgrade head
python -m app.db.seed
```

### **Start Backend**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Pros**:
- ✅ Full backend features
- ✅ No Docker needed
- ✅ Direct database access

**Cons**:
- ❌ Manual setup required
- ❌ Need to install PostgreSQL + Redis
- ❌ More complex configuration

---

## 🎯 **RECOMMENDATION FOR NOW**

### **Keep using the Mock Backend!**

Since you want to **test the frontend and see all the pages**, the mock backend is perfect. It's already running and working correctly.

**What you can test with the mock backend:**
- ✅ All 7 pages load and display correctly
- ✅ Dark theme and UI components
- ✅ Navigation and sidebar
- ✅ Interactive features (tables, charts, modals)
- ✅ Role-based access control
- ✅ Form validation
- ✅ Responsive design

**What you CAN'T test with the mock backend:**
- ❌ Real database operations
- ❌ ML analytics (ARIMA, XGBoost, LSTM)
- ❌ Actual data persistence
- ❌ Real authentication
- ❌ n8n AI agents

---

## 📊 **CURRENT STATUS**

```
✅ Frontend: http://localhost:5173 (Running)
✅ Mock Backend: http://localhost:8000 (Running)
🎉 Ready to test all UI features!
```

---

## 💡 **NEXT STEPS**

### **For Now (Test Frontend UI)**
Just open http://localhost:5173 and explore all pages!

### **Later (Test Full Backend)**
When you want to test the real backend with database:
1. Enable Docker Desktop WSL2 integration
2. Run `docker compose up -d`
3. Run migrations and seed
4. Access full backend at http://localhost:8000

---

**You're all set to test the frontend right now! 🚀**

The mock backend provides everything you need to see the complete UI in action.
