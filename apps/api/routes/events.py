"""Server-Sent Events (SSE) Route Handlers for Real-time Run Updates."""

import asyncio
from collections.abc import AsyncGenerator

from atlas.platform.clock import utc_now
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/events", tags=["Realtime Events"])


async def event_generator(run_id: str) -> AsyncGenerator[str]:
    """Generate mock/real SSE events for a specific run."""
    yield f'data: {{"event": "connected", "run_id": "{run_id}", "timestamp": "{utc_now().isoformat()}"}}\n\n'
    await asyncio.sleep(0.01)
    yield f'data: {{"event": "status", "run_id": "{run_id}", "state": "active"}}\n\n'


@router.get("/runs/{run_id}")
async def stream_run_events(run_id: str) -> StreamingResponse:
    """Stream real-time status and step completion events via SSE."""
    return StreamingResponse(
        event_generator(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
