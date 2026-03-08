"""Database seed script for development environment.

Creates:
- System user (for audit actions without a real user)
- Default admin user
- Default configuration values
- Sample data for testing
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.config import get_settings
from app.core.security import hash_password
from app.repositories.audit import SYSTEM_USER_ID
from app.constants import (
    COLLATERAL_LIMIT,
    HR_HARD_CAP,
    IFRS9_R2_MIN_PROSPECTIVE,
    MAPE_TARGET,
    MAX_COVERAGE_RATIO,
    PIPELINE_TIMEOUT_MINUTES,
    VAR_REDUCTION_TARGET,
)
from app.db.base import AsyncSessionLocal
from app.db.models import PlatformConfig, User, UserRole


async def seed_database() -> None:
    """Seed the database with initial development data."""
    
    settings = get_settings()
    
    async with AsyncSessionLocal() as session:
        # Ensure system user exists (for audit actions: failed login, etc.)
        result = await session.execute(select(User).where(User.id == SYSTEM_USER_ID))
        if result.scalar_one_or_none() is None:
            system_user = User(
                id=SYSTEM_USER_ID,
                email="system@internal",
                hashed_password=hash_password("unused"),
                role=UserRole.ADMIN,
                is_active=False,
            )
            session.add(system_user)
            await session.flush()
            print("✓ Created system user for audit logging")

        # Check if admin user already exists (admin@airline.com = frontend default)
        result = await session.execute(
            select(User).where(User.email == "admin@airline.com")
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print("✓ Admin user already exists")
        else:
            # Create admin user (admin@airline.com matches frontend default)
            admin_user = User(
                id=uuid.uuid4(),
                email="admin@airline.com",
                hashed_password=hash_password("admin123"),  # Change in production!
                role=UserRole.ADMIN,
                is_active=True,
                last_login=None,
            )
            session.add(admin_user)
            await session.flush()
            print(f"✓ Created admin user: {admin_user.email}")
            
            # Create platform configuration entries
            config_entries = [
                PlatformConfig(
                    id=uuid.uuid4(),
                    key="hr_cap",
                    value={"value": float(HR_HARD_CAP)},
                    description="Maximum hedge ratio (regulatory hard limit)",
                    updated_by_id=admin_user.id,
                ),
                PlatformConfig(
                    id=uuid.uuid4(),
                    key="collateral_limit",
                    value={"value": float(COLLATERAL_LIMIT)},
                    description="Maximum collateral as percentage of cash reserves",
                    updated_by_id=admin_user.id,
                ),
                PlatformConfig(
                    id=uuid.uuid4(),
                    key="ifrs9_r2_min",
                    value={"value": float(IFRS9_R2_MIN_PROSPECTIVE)},
                    description="Minimum R² for IFRS 9 hedge effectiveness",
                    updated_by_id=admin_user.id,
                ),
                PlatformConfig(
                    id=uuid.uuid4(),
                    key="mape_target",
                    value={"value": float(MAPE_TARGET)},
                    description="Target MAPE percentage for ensemble forecaster",
                    updated_by_id=admin_user.id,
                ),
                PlatformConfig(
                    id=uuid.uuid4(),
                    key="var_reduction_target",
                    value={"value": float(VAR_REDUCTION_TARGET)},
                    description="Target VaR reduction vs unhedged position",
                    updated_by_id=admin_user.id,
                ),
                PlatformConfig(
                    id=uuid.uuid4(),
                    key="max_coverage_ratio",
                    value={"value": float(MAX_COVERAGE_RATIO)},
                    description="Maximum hedge coverage ratio (prevents over-hedging)",
                    updated_by_id=admin_user.id,
                ),
                PlatformConfig(
                    id=uuid.uuid4(),
                    key="pipeline_timeout",
                    value={"value": PIPELINE_TIMEOUT_MINUTES},
                    description="Maximum allowed duration for daily analytics pipeline (minutes)",
                    updated_by_id=admin_user.id,
                ),
            ]
            
            for config_entry in config_entries:
                session.add(config_entry)
            
            print(f"✓ Created {len(config_entries)} platform configuration entries")
        
        # Create additional test users for different roles
        test_users = [
            {
                "email": "analyst@hedgeplatform.com",
                "password": "analyst123",
                "role": UserRole.ANALYST,
            },
            {
                "email": "riskmanager@hedgeplatform.com",
                "password": "riskmanager123",
                "role": UserRole.RISK_MANAGER,
            },
            {
                "email": "cfo@hedgeplatform.com",
                "password": "cfo123",
                "role": UserRole.CFO,
            },
        ]
        
        created_count = 0
        for user_data in test_users:
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                user = User(
                    id=uuid.uuid4(),
                    email=user_data["email"],
                    hashed_password=hash_password(user_data["password"]),
                    role=user_data["role"],
                    is_active=True,
                    last_login=None,
                )
                session.add(user)
                created_count += 1
        
        if created_count > 0:
            print(f"✓ Created {created_count} test users")
        else:
            print("✓ Test users already exist")
        
        await session.commit()
        
        print("\n=== Development Database Seeded Successfully ===")
        print("\nDefault Users:")
        print("  Admin:        admin@airline.com / admin123")
        print("  Analyst:      analyst@hedgeplatform.com / analyst123")
        print("  Risk Manager: riskmanager@hedgeplatform.com / riskmanager123")
        print("  CFO:          cfo@hedgeplatform.com / cfo123")
        print("\n⚠️  Change these passwords in production!")


if __name__ == "__main__":
    asyncio.run(seed_database())
