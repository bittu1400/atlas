"""Domain routes — the area of knowledge a Topic hangs off.

A Domain carries a Research Profile (preferred APIs, source allowlist, source
tier floor), which is what makes it more than a tag — and what defect V-17
silently blanked when `create` was an upsert.
"""

from atlas.application.usecases.create_domain import CreateDomainUseCase
from atlas.application.usecases.list_run_prerequisites import ListDomainsUseCase
from atlas.domain.focus.models import Domain
from fastapi import APIRouter, Depends, status

from apps.api.dependencies import (
    get_create_domain_use_case,
    get_list_domains_use_case,
    verify_api_key,
)
from apps.api.schemas import CreateDomainRequest, DomainResponse

router = APIRouter(prefix="/domains", tags=["Run prerequisites"])


def _to_response(domain: Domain) -> DomainResponse:
    """Serialize a Domain, keeping the Research Profile visible to the operator."""
    return DomainResponse(
        id=domain.id,
        name=domain.name,
        description=domain.description,
        research_profile=domain.research_profile.model_dump(mode="json"),
    )


@router.get("", response_model=list[DomainResponse])
async def list_domains(
    use_case: ListDomainsUseCase = Depends(get_list_domains_use_case),
    _auth: str = Depends(verify_api_key),
) -> list[DomainResponse]:
    """List every Domain, by ID."""
    return [_to_response(d) for d in await use_case.execute()]


@router.post("", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
async def create_domain(
    request: CreateDomainRequest,
    use_case: CreateDomainUseCase = Depends(get_create_domain_use_case),
    _auth: str = Depends(verify_api_key),
) -> DomainResponse:
    """Register a Domain. An existing ID is a 409, never an overwrite (V-17)."""
    domain = await use_case.execute(
        domain_id=request.id, name=request.name, description=request.description
    )
    return _to_response(domain)
