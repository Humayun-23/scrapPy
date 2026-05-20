import asyncio
import os
from typing import Any

from redis import Redis
from rq import Queue
from rq.job import Job

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
JOB_QUEUE_NAME = os.getenv("JOB_QUEUE_NAME", "scrappy")
JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "180"))
JOB_RESULT_TTL_SECONDS = int(os.getenv("JOB_RESULT_TTL_SECONDS", "3600"))


def _get_queue() -> Queue:
    return Queue(
        name=JOB_QUEUE_NAME,
        connection=Redis.from_url(REDIS_URL),
        default_timeout=JOB_TIMEOUT_SECONDS,
    )


def enqueue_job(job_type: str, payload: dict[str, Any]) -> Job:
    queue = _get_queue()
    return queue.enqueue(
        run_job,
        job_type,
        payload,
        job_timeout=JOB_TIMEOUT_SECONDS,
        result_ttl=JOB_RESULT_TTL_SECONDS,
    )


def fetch_job(job_id: str) -> Job:
    return Job.fetch(job_id, connection=Redis.from_url(REDIS_URL))


def run_job(job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"success": False, "error": f"Job processing is no longer supported for {job_type}"}
