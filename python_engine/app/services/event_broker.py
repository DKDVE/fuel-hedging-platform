"""Event broker for Server-Sent Events (SSE) broadcasts."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog

log = structlog.get_logger()


@dataclass
class SSEEvent:
    """Server-Sent Event structure."""

    event: str
    data: dict[str, Any]
    id: str | None = None


class EventBroker:
    """Central event broker for SSE streams."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, channel: str) -> asyncio.Queue:
        """Subscribe to a channel."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=50)
        self._subscribers[channel].append(queue)
        log.info(
            "sse_subscription",
            channel=channel,
            total_subscribers=len(self._subscribers[channel]),
        )
        return queue

    def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from a channel."""
        if queue in self._subscribers[channel]:
            self._subscribers[channel].remove(queue)
            log.info(
                "sse_unsubscription",
                channel=channel,
                total_subscribers=len(self._subscribers[channel]),
            )

    async def publish_event(self, channel: str, event: SSEEvent) -> None:
        """Publish event to all subscribers of a channel."""
        subscribers = self._subscribers[channel]
        if not subscribers:
            log.debug("no_subscribers", channel=channel)
            return

        for queue in subscribers[:]:  # Copy to avoid modification during iteration
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Queue full, drop oldest and try again
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except Exception as e:
                    log.warning("failed_to_publish_event", channel=channel, error=str(e))

        log.debug(
            "event_published",
            channel=channel,
            event=event.event,
            subscribers=len(subscribers),
        )


class PriceEventBroker(EventBroker):
    """Specialized event broker for price and recommendation streams."""

    PRICE_CHANNEL = "prices"
    RECOMMENDATION_CHANNEL = "recommendations"

    async def broadcast_price_tick(self, tick_data: dict[str, Any]) -> None:
        """Broadcast a single price tick to all price stream subscribers."""
        event = SSEEvent(
            event="tick",
            data={
                "type": "tick",
                "tick": tick_data,
            },
        )
        await self.publish_event(self.PRICE_CHANNEL, event)

    async def broadcast_price_history(self, ticks: list[dict[str, Any]]) -> None:
        """Broadcast historical price data (on new connection)."""
        event = SSEEvent(
            event="history",
            data={
                "type": "history",
                "ticks": ticks,
            },
        )
        await self.publish_event(self.PRICE_CHANNEL, event)

    async def broadcast_recommendation_event(
        self,
        event_type: str,
        recommendation_id: UUID,
        status: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast recommendation status change or new recommendation."""
        event = SSEEvent(
            event=event_type,
            data={
                "event_type": event_type,
                "recommendation_id": str(recommendation_id),
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data or {},
            },
            id=str(recommendation_id),
        )
        await self.publish_event(self.RECOMMENDATION_CHANNEL, event)

        log.info(
            "recommendation_event_broadcast",
            event_type=event_type,
            recommendation_id=str(recommendation_id),
            status=status,
        )


# Global singleton
_event_broker: EventBroker | None = None
_price_broker: PriceEventBroker | None = None


def get_event_broker() -> EventBroker:
    """Get or create global event broker instance."""
    global _event_broker
    if _event_broker is None:
        _event_broker = EventBroker()
    return _event_broker


def get_price_broker() -> PriceEventBroker:
    """Get or create global price event broker instance."""
    global _price_broker
    if _price_broker is None:
        _price_broker = PriceEventBroker()
    return _price_broker
