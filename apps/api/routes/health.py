"""Health and Status Route Handlers."""

from atlas.adapters.persistence.database import get_session_manager
from atlas.platform.clock import utc_now
from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint returning system and database readiness."""
    db_status = "healthy"
    try:
        session_manager = get_session_manager()
        async with session_manager.session() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unreachable"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "service": "atlas-backend",
        "timestamp": utc_now().isoformat(),
    }
