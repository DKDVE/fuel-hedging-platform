"""Database and data management CLI scripts.

Usage:
    python manage.py load_csv        # Load historical CSV data
    python manage.py train_lstm      # Train LSTM model
    python manage.py run_pipeline    # Run analytics pipeline manually
    python manage.py seed_db         # Seed development data
"""

import asyncio
import sys
from pathlib import Path

import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger()


async def load_csv_data():
    """Load historical CSV data into database."""
    from app.db.base import AsyncSessionLocal
    from app.services.data_ingestion import import_historical_csv

    logger.info("loading_csv_data")

    async with AsyncSessionLocal() as db:
        stats = await import_historical_csv(db)
        await db.commit()

    logger.info("csv_load_complete", **stats)
    print(f"\nCSV Load Complete:")
    print(f"  Imported: {stats['imported']} records")
    print(f"  Updated: {stats['updated']} records")
    print(f"  Skipped: {stats['skipped']} records")
    print(f"  Total: {stats['total']} records")


def train_lstm_model():
    """Train LSTM forecasting model."""
    from app.services.train_lstm import train_lstm_model

    logger.info("training_lstm")

    metrics = train_lstm_model(epochs=50)

    print(f"\nLSTM Training Complete:")
    print(f"  MAPE: {metrics['mape']:.2f}%")
    print(f"  MAE: {metrics['mae']:.4f}")
    print(f"  MSE: {metrics['mse']:.4f}")


async def run_analytics_pipeline():
    """Run analytics pipeline manually."""
    from app.db.base import AsyncSessionLocal
    from app.services.analytics_pipeline import AnalyticsPipeline

    logger.info("running_analytics_pipeline")

    async with AsyncSessionLocal() as db:
        pipeline = AnalyticsPipeline(db)
        run_id = await pipeline.execute_daily_run()

    logger.info("pipeline_complete", run_id=run_id)
    print(f"\nAnalytics Pipeline Complete:")
    print(f"  Run ID: {run_id}")


async def seed_development_data():
    """Seed database with development data."""
    from app.db.seed import seed_database

    logger.info("seeding_database")

    await seed_database()

    print("\nDatabase Seeded Successfully:")
    print("  - Admin user created")
    print("  - Platform configuration set")


def print_usage():
    """Print usage instructions."""
    print("Usage: python manage.py <command>")
    print("\nCommands:")
    print("  load_csv       Load historical CSV data")
    print("  train_lstm     Train LSTM forecasting model")
    print("  run_pipeline   Run analytics pipeline manually")
    print("  seed_db        Seed development data")
    print("\nExamples:")
    print("  python manage.py load_csv")
    print("  python manage.py train_lstm")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "load_csv":
            asyncio.run(load_csv_data())
        elif command == "train_lstm":
            train_lstm_model()
        elif command == "run_pipeline":
            asyncio.run(run_analytics_pipeline())
        elif command == "seed_db":
            asyncio.run(seed_development_data())
        else:
            print(f"Unknown command: {command}")
            print_usage()
            sys.exit(1)

    except Exception as e:
        logger.error("command_failed", command=command, error=str(e), exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
