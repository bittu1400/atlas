"""Focus routes — the scoping a Run captures by value.

The listing resolves the Active Focus pointer: a Run created without an
explicit Focus takes the active one (Invariant 6), so a picker that cannot
show which that is hides the default it is about to apply.
"""

from atlas.application.usecases.create_focus import CreateFocusUseCase
from atlas.application.usecases.list_run_prerequisites import FocusListing, ListFocusesUseCase
from atlas.domain.focus.models import Facet
from fastapi import APIRouter, Depends, status

from apps.api.dependencies import (
    get_create_focus_use_case,
    get_list_focuses_use_case,
    verify_api_key,
)
from apps.api.schemas import CreateFocusRequest

router = APIRouter(prefix="/focuses", tags=["Run prerequisites"])


@router.get("", response_model=list[FocusListing])
async def list_focuses(
    use_case: ListFocusesUseCase = Depends(get_list_focuses_use_case),
    _auth: str = Depends(verify_api_key),
) -> list[FocusListing]:
    """List every Focus, newest first, flagging the active one."""
    return await use_case.execute()


@router.post("", response_model=FocusListing, status_code=status.HTTP_201_CREATED)
async def create_focus(
    request: CreateFocusRequest,
    use_case: CreateFocusUseCase = Depends(get_create_focus_use_case),
    _auth: str = Depends(verify_api_key),
) -> FocusListing:
    """Register a Focus. Creating one does not make it the Active Focus."""
    focus = await use_case.execute(
        name=request.name,
        facets=[Facet(dimension=f.dimension, value=f.value) for f in request.facets],
        scope_mode=request.scope_mode,
        entity_id=request.entity_id,
        actor_id=request.actor_id,
    )
    return FocusListing.from_focus(focus, is_active=False)
