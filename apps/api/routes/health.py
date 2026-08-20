"""Health and Status Route Handlers."""

from atlas.platform.clock import utc_now
from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint returning system readiness."""
    return {
        "status": "healthy",
        "service": "atlas-backend",
        "timestamp": utc_now().isoformat(),
    }
