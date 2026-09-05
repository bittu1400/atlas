"""Topic routes — the candidate subject a Run is launched against.

Until these existed, `topics` was empty on any database a test had not seeded
and the dashboard's Launch form was a free-text box over IDs it could not
enumerate (defect V-15).
"""

from atlas.application.usecases.create_topic import CreateTopicUseCase
from atlas.application.usecases.list_run_prerequisites import ListTopicsUseCase
from atlas.domain.knowledge.models import Topic
from fastapi import APIRouter, Depends, status

from apps.api.dependencies import (
    get_create_topic_use_case,
    get_list_topics_use_case,
    verify_api_key,
)
from apps.api.schemas import CreateTopicRequest, TopicResponse

router = APIRouter(prefix="/topics", tags=["Run prerequisites"])


def _to_response(topic: Topic) -> TopicResponse:
    return TopicResponse(
        id=topic.id,
        title=topic.title,
        domain_id=topic.domain_id,
        entity_id=topic.entity_id,
        status=topic.status,
        created_at=topic.created_at,
    )


@router.get("", response_model=list[TopicResponse])
async def list_topics(
    use_case: ListTopicsUseCase = Depends(get_list_topics_use_case),
    _auth: str = Depends(verify_api_key),
) -> list[TopicResponse]:
    """List every Topic, newest first."""
    return [_to_response(t) for t in await use_case.execute()]


@router.post("", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    request: CreateTopicRequest,
    use_case: CreateTopicUseCase = Depends(get_create_topic_use_case),
    _auth: str = Depends(verify_api_key),
) -> TopicResponse:
    """Register a Topic in `proposed`. An unknown Domain is a 404, a duplicate ID a 409."""
    topic = await use_case.execute(
        topic_id=request.id,
        title=request.title,
        domain_id=request.domain_id,
        entity_id=request.entity_id,
    )
    return _to_response(topic)
