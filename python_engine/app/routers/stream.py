"""
Real-time streaming endpoints using Server-Sent Events (SSE).

Provides live market price feeds and system status updates.

DIAGNOSIS: SSE connectivity requires:
- Cache-Control: no-cache, X-Accel-Buffering: no (sse_starlette sets these by default)
- Event format: event + data with "data: {json}\\n\\n" (two newlines)
- Keepalive as comment (": keepalive\\n\\n") to prevent proxy timeout
"""

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from app.services.event_broker import get_price_broker, SSEEvent
from app.services.price_service import get_price_service, PriceTick


router = APIRouter(prefix="/stream", tags=["streaming"])

# SSE headers — sse_starlette sets these by default; explicit for proxy compatibility
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


@router.get("/prices")
async def stream_prices() -> EventSourceResponse:
    """
    Real-time price feed via Server-Sent Events (SSE).
    
    On connection:
    1. Sends last 100 historical ticks as 'history' event
    2. Then streams live ticks as they arrive as 'tick' events
    3. Sends keepalive comments every 30 seconds
    
    Event format:
    - history: {"type": "history", "ticks": [... 100 ticks ...]}
    - tick: {"type": "tick", "tick": {...}}
    - keepalive: comment line (": keepalive\\n\\n")
    
    No authentication required for price feed (public market data).
    """
    price_service = get_price_service()
    
    # Start price service if not already running
    await price_service.start()
    
    async def event_generator() -> AsyncGenerator[dict, None]:
        """Generate SSE events."""
        # Subscribe to price updates
        queue = price_service.subscribe()
        
        try:
            # Step 1: Send historical ticks for initial chart load
            history = price_service.get_history(n=100)
            if history:
                yield {
                    "event": "history",
                    "data": json.dumps({
                        "type": "history",
                        "ticks": [tick.to_dict() for tick in history]
                    })
                }
            
            # Step 2: Stream live ticks as they arrive
            last_keepalive = asyncio.get_event_loop().time()
            
            while True:
                try:
                    # Wait for next tick or alert (with timeout for keepalive)
                    item = await asyncio.wait_for(
                        queue.get(),
                        timeout=30.0
                    )

                    # Handle alert events
                    if isinstance(item, dict) and item.get("__type") == "alert":
                        yield {
                            "event": "alert",
                            "data": item["payload"],
                        }
                        last_keepalive = asyncio.get_event_loop().time()
                        continue

                    # Normal tick
                    tick: PriceTick = item
                    yield {
                        "event": "tick",
                        "data": json.dumps({
                            "type": "tick",
                            "tick": tick.to_dict()
                        })
                    }
                    last_keepalive = asyncio.get_event_loop().time()
                
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent proxy timeout
                    yield ServerSentEvent(comment="keepalive")
                    last_keepalive = asyncio.get_event_loop().time()
        
        except asyncio.CancelledError:
            # Client disconnected
            pass
        
        finally:
            # Cleanup: unsubscribe from price updates
            price_service.unsubscribe(queue)
    
    return EventSourceResponse(event_generator(), headers=SSE_HEADERS)


@router.get("/status")
async def get_stream_status() -> dict:
    """Get current data source status.
    
    Returns info about:
    - Mode (simulation vs live)
    - Health status
    - Latest prices
    - Tick rate
    
    No authentication required (used by health panel).
    """
    price_service = get_price_service()
    
    # Start service if not running (needed to get status)
    await price_service.start()
    
    return price_service.get_status()


@router.get("/recommendations")
async def stream_recommendations() -> EventSourceResponse:
    """Real-time recommendation updates via Server-Sent Events (SSE).
    
    Events:
    - new_recommendation: New recommendation created (PENDING status)
    - status_change: Status changed (APPROVED/REJECTED/DEFERRED)
    - approaching_expiry: SLA approaching (recommendation near 2-hour expiry)
    
    Event data format:
    {
        "event_type": "new_recommendation"|"status_change"|"approaching_expiry",
        "recommendation_id": "<uuid>",
        "status": "PENDING"|"APPROVED"|"REJECTED"|"DEFERRED"|"EXPIRED",
        "timestamp": "<iso8601>",
        "data": {...}
    }
    
    No authentication required for monitoring (sensitive data not exposed in events).
    """
    price_broker = get_price_broker()
    
    async def event_generator() -> AsyncGenerator[dict, None]:
        """Generate SSE events for recommendations."""
        queue = price_broker.subscribe(price_broker.RECOMMENDATION_CHANNEL)
        
        try:
            while True:
                try:
                    # Wait for next event (with timeout for keepalive)
                    event: SSEEvent = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    yield {
                        "event": event.event,
                        "data": json.dumps(event.data),
                        "id": event.id,
                    }
                except asyncio.TimeoutError:
                    yield ServerSentEvent(comment="keepalive")
        except asyncio.CancelledError:
            pass
        finally:
            price_broker.unsubscribe(price_broker.RECOMMENDATION_CHANNEL, queue)
    
    return EventSourceResponse(event_generator(), headers=SSE_HEADERS)
