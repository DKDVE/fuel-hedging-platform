#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Seeding database (if empty)..."
python manage.py seed_db || true

echo "Loading historical price data from data/fuel_hedging_dataset.csv (if not already loaded)..."
python manage.py load_csv || true

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
