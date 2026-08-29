import asyncio

import dramatiq
from atlas.adapters.container import Container
from atlas.adapters.persistence.database import get_session_manager
from atlas.platform.logging import get_logger

logger = get_logger("apps.worker.tasks")


async def _execute_pipeline_async(run_id: str) -> None:
    logger.info("worker.task_started", run_id=run_id)
    session_manager = get_session_manager()

    async with session_manager.session() as session:
        container = Container(session)
        runner = container.get_pipeline_runner()
        await runner.run_pipeline(run_id)
        logger.info("worker.task_finished", run_id=run_id)


@dramatiq.actor
def execute_pipeline_task(run_id: str) -> None:
    """Background worker task executing pipeline stages for a Run."""
    asyncio.run(_execute_pipeline_async(run_id))
