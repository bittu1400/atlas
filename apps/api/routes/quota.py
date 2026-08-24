from atlas.application.usecases.get_run_status import GetQuotaStatusUseCase
from fastapi import APIRouter, Depends

from apps.api.dependencies import get_quota_status_use_case, verify_api_key
from apps.api.schemas import QuotaStatusResponse

router = APIRouter(prefix="/quota", tags=["Quota & Metering"])


@router.get("", response_model=QuotaStatusResponse)
async def get_quota_status(
    use_case: GetQuotaStatusUseCase = Depends(get_quota_status_use_case),
    _auth: str = Depends(verify_api_key),
) -> QuotaStatusResponse:
    """Fetch real-time quota allocation and consumption across providers."""
    status_data = await use_case.execute()
    return QuotaStatusResponse(
        status=status_data["status"],
        providers=status_data["providers"],
    )
