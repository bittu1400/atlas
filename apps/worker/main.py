import asyncio
import sys

from atlas.platform.logging import get_logger

from apps.worker.tasks import execute_pipeline_task

logger = get_logger("apps.worker")


def main() -> None:
    """Worker entrypoint."""
    if len(sys.argv) > 1:
        run_id = sys.argv[1]
        logger.info("worker.running_single_task", run_id=run_id)
        asyncio.run(execute_pipeline_task(run_id))
    else:
        logger.info("worker.running_poll_loop")
        # Polling loop for jobs
        console_msg = "Atlas Worker running. Pass <run_id> to execute a specific job."
        print(console_msg)


if __name__ == "__main__":
    main()
