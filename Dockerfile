# Root Dockerfile for Render deployment (hedge-api).
# Uses repo root as build context. For python_engine-only context, use python_engine/Dockerfile.prod.

FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY python_engine/requirements.txt python_engine/requirements-core.txt python_engine/requirements-analytics.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt \
    -r requirements-core.txt \
    -r requirements-analytics.txt gunicorn

FROM python:3.11-slim AS runtime

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local

COPY python_engine/app/ ./app/
COPY python_engine/alembic/ ./alembic/
COPY python_engine/alembic.ini .
COPY python_engine/manage.py .
COPY python_engine/scripts/ ./scripts/
COPY data/ /data/
RUN mkdir -p /models

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

USER appuser
ENV PATH="/home/appuser/.local/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 10000

# Render sets PORT=10000; use it so the app receives traffic
ENV PORT=10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:10000/health || exit 1

CMD ["sh", "-c", "gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:${PORT} --timeout 120 --access-logfile - --error-logfile -"]
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
