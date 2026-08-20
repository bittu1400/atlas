"""FastAPI Route Handlers for Gates and Approvals."""

from atlas.application.pipeline.runner import PipelineRunner
from atlas.application.usecases.approve_gate import ApproveGateUseCase
from atlas.application.usecases.get_run_status import ListGatesUseCase
from atlas.application.usecases.reject_gate import RejectGateUseCase
from atlas.domain.execution.models import RejectionFeedback
from atlas.platform.errors import (
    GateAlreadyResolvedError,
    GateNotFoundError,
)
from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.dependencies import (
    get_approve_gate_use_case,
    get_list_gates_use_case,
    get_pipeline_runner,
    get_reject_gate_use_case,
)
from apps.api.schemas import (
    ApprovalResponse,
    ApproveGateRequest,
    GateResponse,
    RejectGateRequest,
)

router = APIRouter(prefix="/gates", tags=["Gates & Approvals"])


@router.get("/pending", response_model=list[GateResponse])
async def list_pending_gates(
    use_case: ListGatesUseCase = Depends(get_list_gates_use_case),
) -> list[GateResponse]:
    """List all Gates awaiting operator review."""
    gates = await use_case.execute(pending_only=True)
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


@router.post("/{gate_id}/approve", response_model=ApprovalResponse)
async def approve_gate(
    gate_id: str,
    request: ApproveGateRequest,
    use_case: ApproveGateUseCase = Depends(get_approve_gate_use_case),
    runner: PipelineRunner = Depends(get_pipeline_runner),
) -> ApprovalResponse:
    """Approve a pending Gate and resume pipeline execution."""
    try:
        updated_gate, approval = await use_case.execute(gate_id=gate_id, actor_id=request.actor_id)
        # Continue running pipeline after approval
        await runner.run_pipeline(updated_gate.run_id)

        return ApprovalResponse(
            id=approval.id,
            gate_id=approval.gate_id,
            run_id=approval.run_id,
            actor_id=approval.actor_id,
            decision=approval.decision,
            feedback=approval.feedback.model_dump(mode="json") if approval.feedback else None,
            created_at=approval.created_at,
        )
    except GateNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err.message) from err
    except GateAlreadyResolvedError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err.message) from err


@router.post("/{gate_id}/reject", response_model=ApprovalResponse)
async def reject_gate(
    gate_id: str,
    request: RejectGateRequest,
    use_case: RejectGateUseCase = Depends(get_reject_gate_use_case),
) -> ApprovalResponse:
    """Reject a Gate with mandatory structured feedback (SPEC §7)."""
    try:
        feedback = RejectionFeedback(
            target_ref=request.target_ref,
            rubric_dimension=request.rubric_dimension,
            reason=request.reason,
            action=request.action,
        )
        updated_gate, approval = await use_case.execute(
            gate_id=gate_id, feedback=feedback, actor_id=request.actor_id
        )

        return ApprovalResponse(
            id=approval.id,
            gate_id=approval.gate_id,
            run_id=approval.run_id,
            actor_id=approval.actor_id,
            decision=approval.decision,
            feedback=approval.feedback.model_dump(mode="json") if approval.feedback else None,
            created_at=approval.created_at,
        )
    except GateNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err.message) from err
    except GateAlreadyResolvedError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err.message) from err
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)
        ) from err
