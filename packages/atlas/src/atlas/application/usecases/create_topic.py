"""Create Topic Use Case.

Defect V-15: `SourceRepositoryPort.save_topic` had no production caller, so
`topics` was empty in any database a test had not seeded and every Run
creation failed its foreign key.
"""

from atlas.application.ports.repositories import FocusRepositoryPort, SourceRepositoryPort
from atlas.domain.knowledge.models import Topic, TopicStatus
from atlas.platform.clock import utc_now
from atlas.platform.errors import DomainNotFoundError, DuplicateEntityError
from atlas.platform.logging import get_logger

logger = get_logger("usecases.create_topic")


class CreateTopicUseCase:
    """Use case to register a Topic against an existing Domain."""

    def __init__(self, source_repo: SourceRepositoryPort, focus_repo: FocusRepositoryPort) -> None:
        self.source_repo = source_repo
        self.focus_repo = focus_repo

    async def execute(
        self,
        topic_id: str,
        title: str,
        domain_id: str,
        entity_id: str | None = None,
    ) -> Topic:
        """Register a Topic in `PROPOSED`, after checking its Domain exists.

        The Domain check is here rather than left to the foreign key for the
        reason V-16 records: a constraint violation is an infrastructure
        exception, and the operator gets a 500 instead of the name of the row
        that is missing.
        """
        if await self.focus_repo.get_domain(domain_id) is None:
            raise DomainNotFoundError(domain_id)
        if await self.source_repo.get_topic(topic_id) is not None:
            raise DuplicateEntityError("Topic", topic_id)

        topic = Topic(
            id=topic_id,
            title=title,
            domain_id=domain_id,
            entity_id=entity_id,
            status=TopicStatus.PROPOSED,
            created_at=utc_now(),
        )
        saved = await self.source_repo.save_topic(topic)
        logger.info("topic.created", topic_id=saved.id, domain_id=domain_id)
        return saved
