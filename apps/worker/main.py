import asyncio
import contextlib
import signal
import sys

from atlas.platform.logging import get_logger

from apps.worker.tasks import execute_pipeline_task

logger = get_logger("apps.worker")


async def run_worker_loop() -> None:
    """Continuous background worker polling loop with graceful shutdown."""
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    logger.info("worker.poll_loop_started")
    try:
        while not stop_event.is_set():
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop_event.wait(), timeout=1.0)
    finally:
        logger.info("worker.poll_loop_stopped")


def main() -> None:
    """Worker entrypoint."""
    if len(sys.argv) > 1:
        run_id = sys.argv[1]
        logger.info("worker.running_single_task", run_id=run_id)
        asyncio.run(execute_pipeline_task(run_id))
    else:
        logger.info("worker.running_poll_loop")
        asyncio.run(run_worker_loop())


if __name__ == "__main__":
    main()
