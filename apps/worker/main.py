"""Worker entrypoint for running one pipeline task in-process.

There is no polling loop here. Dramatiq owns the queue; `docker-compose.yml`
runs `dramatiq apps.worker.tasks`, which is the only consumer. The loop that
used to live here awaited a stop event on a one-second timeout and never
touched the queue at all — a worker that looked like a worker (defect V-08).
"""

import sys

from atlas.platform.logging import get_logger

from apps.worker.tasks import execute_pipeline_task

logger = get_logger("apps.worker")

USAGE = "usage: python -m apps.worker.main <run_id>   (queue consumer: dramatiq apps.worker.tasks)"


def main() -> None:
    """Execute a single Run by ID, or explain how to consume the queue."""
    if len(sys.argv) != 2:
        print(USAGE, file=sys.stderr)
        raise SystemExit(2)

    run_id = sys.argv[1]
    logger.info("worker.running_single_task", run_id=run_id)
    # A dramatiq actor is a sync callable; calling it runs the task in-process.
    execute_pipeline_task(run_id)


if __name__ == "__main__":
    main()
