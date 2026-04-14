"""Platform configuration repository for runtime settings."""

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PlatformConfig
from app.repositories.base import BaseRepository


class ConfigRepository(BaseRepository[PlatformConfig]):
    """Repository for PlatformConfig model operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(PlatformConfig, db)

    async def get_by_key(self, key: str) -> Optional[PlatformConfig]:
        """Get configuration by key.
        
        Args:
            key: Configuration key
            
        Returns:
            Configuration entry or None if not found
        """
        result = await self.db.execute(
            select(PlatformConfig).where(PlatformConfig.key == key)
        )
        return result.scalar_one_or_none()

    async def get_value(self, key: str) -> Optional[dict[str, Any]]:
        """Get configuration value by key.
        
        Args:
            key: Configuration key
            
        Returns:
            Configuration value dict or None if not found
        """
        config = await self.get_by_key(key)
        return config.value if config else None

    async def set_value(
        self, 
        key: str, 
        value: dict[str, Any], 
        user_id: uuid.UUID,
        description: Optional[str] = None
    ) -> PlatformConfig:
        """Set or update configuration value.
        
        Args:
            key: Configuration key
            value: New value dict
            user_id: User making the change
            description: Optional description (only used for new keys)
            
        Returns:
            Updated or created configuration entry
        """
        existing = await self.get_by_key(key)
        
        if existing:
            existing.value = value
            existing.updated_by_id = user_id
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            new_config = PlatformConfig(
                id=uuid.uuid4(),
                key=key,
                value=value,
                description=description or f"Configuration for {key}",
                updated_by_id=user_id,
            )
            self.db.add(new_config)
            await self.db.flush()
            await self.db.refresh(new_config)
            return new_config

    async def get_all(self) -> list[PlatformConfig]:
        """Get all configuration entries.
        
        Returns:
            List of all configurations
        """
        result = await self.db.execute(
            select(PlatformConfig).order_by(PlatformConfig.key)
        )
        return list(result.scalars().all())

    async def get_constraints_snapshot(self) -> dict[str, float]:
        """Get a snapshot of all constraint values for optimizer.
        
        Returns dict with constraint values that the optimizer needs.
        Falls back to constants if DB config not found.
        
        Returns:
            Dict of constraint values
        """
        from app.constants import (
            COLLATERAL_LIMIT,
            HR_HARD_CAP,
            IFRS9_R2_MIN_PROSPECTIVE,
            MAX_COVERAGE_RATIO,
        )
        
        all_configs = await self.get_all()
        config_dict = {cfg.key: cfg.value.get("value") for cfg in all_configs}
        
        # Return snapshot with fallbacks to constants
        return {
            "hr_cap": config_dict.get("hr_cap", HR_HARD_CAP),
            "collateral_limit": config_dict.get("collateral_limit", COLLATERAL_LIMIT),
            "ifrs9_r2_min": config_dict.get("ifrs9_r2_min", IFRS9_R2_MIN_PROSPECTIVE),
            "max_coverage_ratio": config_dict.get("max_coverage_ratio", MAX_COVERAGE_RATIO),
            "monthly_consumption_bbl": config_dict.get("monthly_consumption_bbl", 100_000),
            "hr_band_min": config_dict.get("hr_band_min", 0.40),
        }

    async def get_hr_cap(self) -> float:
        """Get current hedge ratio cap value.
        
        Returns:
            HR cap value (falls back to constant if not in DB)
        """
        from app.constants import HR_HARD_CAP
        
        value = await self.get_value("hr_cap")
        return float(value.get("value", HR_HARD_CAP)) if value else HR_HARD_CAP

    async def get_collateral_limit(self) -> float:
        """Get current collateral limit value.
        
        Returns:
            Collateral limit value (falls back to constant if not in DB)
        """
        from app.constants import COLLATERAL_LIMIT
        
        value = await self.get_value("collateral_limit")
        return float(value.get("value", COLLATERAL_LIMIT)) if value else COLLATERAL_LIMIT

    async def get_monthly_consumption(self) -> float:
        """Get monthly fuel consumption in barrels. Falls back to 100,000."""
        value = await self.get_value("monthly_consumption_bbl")
        return float(value.get("value", 100_000)) if value else 100_000
