"""FastAPI Application Entrypoint for Atlas.

As specified in ARCHITECTURE.md §1 & §2:
- FastAPI route handlers parse, delegate to application use cases, and serialize.
- Business logic is strictly prohibited in route handlers.
- Long-running work is executed via background worker / runner.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from atlas.adapters.persistence.database import get_session_manager
from atlas.platform.config import get_settings
from atlas.platform.errors import (
    AtlasError,
    ChannelNotFoundError,
    DomainNotFoundError,
    GateAlreadyResolvedError,
    GateNotFoundError,
    InvalidStateTransitionError,
    QualityGateFailedError,
    QuotaExceededError,
    RateLimitExceededError,
    RunNotFoundError,
    StepExecutionError,
    StepNotFoundError,
    TopicNotFoundError,
)
from atlas.platform.logging import get_logger
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    settings = get_settings()

    app = FastAPI(
        title="Atlas API",
        description="Knowledge-first autonomous documentary production system",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS configuration with trusted origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
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

    @app.exception_handler(TopicNotFoundError)
    async def topic_not_found_handler(_request: Request, exc: TopicNotFoundError) -> JSONResponse:
        """Defect V-16: without this, an unknown topic ID was a 500 from the FK."""
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "TopicNotFoundError",
                "message": exc.message,
                "topic_id": exc.topic_id,
            },
        )

    @app.exception_handler(ChannelNotFoundError)
    async def channel_not_found_handler(
        _request: Request, exc: ChannelNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "ChannelNotFoundError",
                "message": exc.message,
                "channel_id": exc.channel_id,
            },
        )

    @app.exception_handler(DomainNotFoundError)
    async def domain_not_found_handler(_request: Request, exc: DomainNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "DomainNotFoundError",
                "message": exc.message,
                "domain_id": exc.domain_id,
            },
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

    @app.exception_handler(InvalidStateTransitionError)
    async def invalid_state_transition_handler(
        _request: Request, exc: InvalidStateTransitionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "InvalidStateTransitionError",
                "message": exc.message,
                "current_state": exc.current_state,
                "target_state": exc.target_state,
            },
        )

    @app.exception_handler(RateLimitExceededError)
    async def rate_limit_handler(_request: Request, exc: RateLimitExceededError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "RateLimitExceededError",
                "message": exc.message,
                "provider": exc.provider,
            },
        )

    @app.exception_handler(QuotaExceededError)
    async def quota_exceeded_handler(_request: Request, exc: QuotaExceededError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "QuotaExceededError",
                "message": exc.message,
                "provider": exc.provider,
            },
        )

    @app.exception_handler(QualityGateFailedError)
    async def quality_gate_failed_handler(
        _request: Request, exc: QualityGateFailedError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "QualityGateFailedError",
                "message": exc.message,
                "weighted_score": exc.weighted_score,
            },
        )

    @app.exception_handler(StepExecutionError)
    async def step_execution_handler(_request: Request, exc: StepExecutionError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "StepExecutionError",
                "message": exc.message,
                "step_name": exc.step_name,
            },
        )

    @app.exception_handler(AtlasError)
    async def atlas_generic_error_handler(_request: Request, exc: AtlasError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.__class__.__name__, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("api.unhandled_exception", error=str(exc), error_type=exc.__class__.__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected server error occurred",
            },
        )

    # Include Routes
    app.include_router(health_router)
    app.include_router(runs_router)
    app.include_router(gates_router)
    app.include_router(quota_router)

    return app


app = create_app()
