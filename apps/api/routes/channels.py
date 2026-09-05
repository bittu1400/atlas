"""Channel routes — the publishing identity a Run targets."""

from atlas.application.usecases.create_channel import CreateChannelUseCase
from atlas.application.usecases.list_run_prerequisites import ListChannelsUseCase
from atlas.domain.publishing.models import Channel
from fastapi import APIRouter, Depends, status

from apps.api.dependencies import (
    get_create_channel_use_case,
    get_list_channels_use_case,
    verify_api_key,
)
from apps.api.schemas import ChannelResponse, CreateChannelRequest

router = APIRouter(prefix="/channels", tags=["Run prerequisites"])


def _to_response(channel: Channel) -> ChannelResponse:
    return ChannelResponse(
        id=channel.id,
        name=channel.name,
        audience_timezone=channel.audience_timezone,
        style_profile=channel.style_profile,
        created_at=channel.created_at,
    )


@router.get("", response_model=list[ChannelResponse])
async def list_channels(
    use_case: ListChannelsUseCase = Depends(get_list_channels_use_case),
    _auth: str = Depends(verify_api_key),
) -> list[ChannelResponse]:
    """List every Channel, by ID."""
    return [_to_response(c) for c in await use_case.execute()]


@router.post("", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    request: CreateChannelRequest,
    use_case: CreateChannelUseCase = Depends(get_create_channel_use_case),
    _auth: str = Depends(verify_api_key),
) -> ChannelResponse:
    """Register a Channel. An existing ID is a 409, never an overwrite (V-17)."""
    channel = await use_case.execute(
        channel_id=request.id,
        name=request.name,
        audience_timezone=request.audience_timezone,
        style_profile=request.style_profile,
    )
    return _to_response(channel)
