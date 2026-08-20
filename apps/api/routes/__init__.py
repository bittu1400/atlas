"""FastAPI API Routes."""

from apps.api.routes.events import router as events_router
from apps.api.routes.gates import router as gates_router
from apps.api.routes.health import router as health_router
from apps.api.routes.quota import router as quota_router
from apps.api.routes.runs import router as runs_router

__all__ = ["events_router", "gates_router", "health_router", "quota_router", "runs_router"]
