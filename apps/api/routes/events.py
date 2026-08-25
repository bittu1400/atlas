import asyncio
import json
from collections.abc import AsyncGenerator

from atlas.platform.clock import utc_now
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from apps.api.dependencies import verify_api_key

router = APIRouter(prefix="/events", tags=["Realtime Events"])


async def event_generator(run_id: str) -> AsyncGenerator[str]:
    """Generate mock/real SSE events for a specific run with safe JSON encoding."""
    connected_data = json.dumps(
        {
            "event": "connected",
            "run_id": run_id,
            "timestamp": utc_now().isoformat(),
        }
    )
    yield f"data: {connected_data}\n\n"
    await asyncio.sleep(0.01)
    status_data = json.dumps(
        {
            "event": "status",
            "run_id": run_id,
            "state": "active",
        }
    )
    yield f"data: {status_data}\n\n"


@router.get("/runs/{run_id}")
async def stream_run_events(
    run_id: str,
    _auth: str = Depends(verify_api_key),
) -> StreamingResponse:
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

