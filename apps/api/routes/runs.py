"""FastAPI Route Handlers for Runs and Steps."""

from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.application.pipeline.runner import PipelineRunner
from atlas.application.usecases.create_run import CreateRunUseCase
from atlas.application.usecases.get_run_status import GetRunStatusUseCase, ListRunsUseCase
from atlas.platform.errors import RunNotFoundError
from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.dependencies import (
    get_create_run_use_case,
    get_execution_repository,
    get_list_runs_use_case,
    get_pipeline_runner,
    get_run_status_use_case,
)
from apps.api.schemas import CreateRunRequest, GateResponse, RunResponse, StepResponse

router = APIRouter(prefix="/runs", tags=["Runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    request: CreateRunRequest,
    use_case: CreateRunUseCase = Depends(get_create_run_use_case),
    runner: PipelineRunner = Depends(get_pipeline_runner),
) -> RunResponse:
    """Create a new pipeline Run and trigger execution."""
    run = await use_case.execute(
        topic_id=request.topic_id,
        channel_id=request.channel_id,
        actor_id=request.actor_id,
        focus_id=request.focus_id,
    )
    # Trigger runner synchronously for direct/fake execution
    updated_run = await runner.run_pipeline(run.id)
    return RunResponse(
        id=updated_run.id,
        topic_id=updated_run.topic_id,
        channel_id=updated_run.channel_id,
        status=updated_run.status,
        captured_focus=updated_run.captured_focus.model_dump(mode="json"),
        trace_id=updated_run.trace_id,
        actor_id=updated_run.actor_id,
        error=updated_run.error,
        created_at=updated_run.created_at,
        updated_at=updated_run.updated_at,
        completed_at=updated_run.completed_at,
    )


@router.get("", response_model=list[RunResponse])
async def list_runs(
    limit: int = 50,
    use_case: ListRunsUseCase = Depends(get_list_runs_use_case),
) -> list[RunResponse]:
    """List pipeline Runs."""
    runs = await use_case.execute(limit=limit)
    return [
        RunResponse(
            id=r.id,
            topic_id=r.topic_id,
            channel_id=r.channel_id,
            status=r.status,
            captured_focus=r.captured_focus.model_dump(mode="json"),
            trace_id=r.trace_id,
            actor_id=r.actor_id,
            error=r.error,
            created_at=r.created_at,
            updated_at=r.updated_at,
            completed_at=r.completed_at,
        )
        for r in runs
    ]


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    use_case: GetRunStatusUseCase = Depends(get_run_status_use_case),
) -> RunResponse:
    """Fetch status of a specific Run."""
    try:
        run = await use_case.execute(run_id)
        return RunResponse(
            id=run.id,
            topic_id=run.topic_id,
            channel_id=run.channel_id,
            status=run.status,
            captured_focus=run.captured_focus.model_dump(mode="json"),
            trace_id=run.trace_id,
            actor_id=run.actor_id,
            error=run.error,
            created_at=run.created_at,
            updated_at=run.updated_at,
            completed_at=run.completed_at,
        )
    except RunNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err.message) from err


@router.get("/{run_id}/steps", response_model=list[StepResponse])
async def get_run_steps(
    run_id: str,
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
) -> list[StepResponse]:
    """Fetch all Steps for a specific Run."""
    steps = await execution_repo.list_steps_for_run(run_id)
    return [
        StepResponse(
            id=s.id,
            run_id=s.run_id,
            step_name=s.step_name,
            step_index=s.step_index,
            status=s.status,
            input_hash=s.input_hash,
            output_artifact_ref=s.output_artifact_ref,
            error=s.error,
            started_at=s.started_at,
            completed_at=s.completed_at,
        )
        for s in steps
    ]


@router.get("/{run_id}/gates", response_model=list[GateResponse])
async def get_run_gates(
    run_id: str,
    execution_repo: ExecutionRepository = Depends(get_execution_repository),
) -> list[GateResponse]:
    """Fetch all Gates for a specific Run."""
    gates = await execution_repo.list_gates_for_run(run_id)
    return [
        GateResponse(
            id=g.id,
            run_id=g.run_id,
            step_id=g.step_id,
            gate_type=g.gate_type,
            status=g.status,
            requested_at=g.requested_at,
            resolved_at=g.resolved_at,
        )
        for g in gates
    ]
