"""FastAPI Application Entrypoint for Atlas.

As specified in ARCHITECTURE.md §1 & §2:
- FastAPI route handlers parse, delegate to application use cases, and serialize.
- Business logic is strictly prohibited in route handlers.
- Long-running work is executed via background worker / runner.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from atlas.adapters.persistence.database import get_session_manager
from atlas.platform.errors import (
    AtlasError,
    GateAlreadyResolvedError,
    GateNotFoundError,
    RunNotFoundError,
    StepNotFoundError,
)
from atlas.platform.logging import get_logger
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.routes.events import router as events_router
from apps.api.routes.gates import router as gates_router
from apps.api.routes.health import router as health_router
from apps.api.routes.quota import router as quota_router
from apps.api.routes.runs import router as runs_router

logger = get_logger("apps.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Manage application startup and graceful shutdown."""
    logger.info("api.starting")
    # Initialize DB connection pool
    session_manager = get_session_manager()
    yield
    logger.info("api.shutting_down")
    await session_manager.close()


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="Atlas API",
        description="Knowledge-first autonomous documentary production system",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Domain Exception Handlers
    @app.exception_handler(RunNotFoundError)
    async def run_not_found_handler(_request: Request, exc: RunNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "RunNotFoundError", "message": exc.message, "run_id": exc.run_id},
        )

    @app.exception_handler(StepNotFoundError)
    async def step_not_found_handler(_request: Request, exc: StepNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "StepNotFoundError", "message": exc.message, "step_id": exc.step_id},
        )

    @app.exception_handler(GateNotFoundError)
    async def gate_not_found_handler(_request: Request, exc: GateNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "GateNotFoundError", "message": exc.message, "gate_id": exc.gate_id},
        )

    @app.exception_handler(GateAlreadyResolvedError)
    async def gate_already_resolved_handler(
        _request: Request, exc: GateAlreadyResolvedError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "GateAlreadyResolvedError",
                "message": exc.message,
                "gate_id": exc.gate_id,
            },
        )

    @app.exception_handler(AtlasError)
    async def atlas_generic_error_handler(_request: Request, exc: AtlasError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.__class__.__name__, "message": exc.message},
        )

    # Include Routes
    app.include_router(health_router)
    app.include_router(runs_router)
    app.include_router(gates_router)
    app.include_router(quota_router)
    app.include_router(events_router)

    return app


app = create_app()
