"""Alert repository for listing and acknowledging alerts."""

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    """Repository for Alert model operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Alert, db)

    async def list_alerts(
        self,
        status: str | None = None,
        limit: int = 20,
    ) -> list[Alert]:
        """List recent alerts. status: 'active' | 'acknowledged' | 'all'."""
        query = select(Alert).order_by(desc(Alert.created_at)).limit(limit)

        if status == "active":
            query = query.where(Alert.is_acknowledged.is_(False))
        elif status == "acknowledged":
            query = query.where(Alert.is_acknowledged.is_(True))

        result = await self.db.execute(query)
        return list(result.scalars().all())
