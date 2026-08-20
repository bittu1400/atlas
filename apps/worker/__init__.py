"""Worker Background Application."""

from apps.worker.tasks import execute_pipeline_task

__all__ = ["execute_pipeline_task"]
