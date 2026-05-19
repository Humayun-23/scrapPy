import asyncio
import os
from typing import Any

from redis import Redis
from rq import Queue
from rq.job import Job

from .scraper import scrape_url, render_url, browser_url

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
    try:
        if job_type == "scrape":
            return asyncio.run(_run_scrape(payload))
        if job_type == "render":
            return asyncio.run(_run_render(payload))
        if job_type == "browser":
            return asyncio.run(_run_browser(payload))
        return {"success": False, "error": f"Unknown job type: {job_type}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def _run_scrape(payload: dict[str, Any]) -> dict[str, Any]:
    result = await scrape_url(
        url=payload["url"],
        wait_for=payload.get("wait_for"),
        extract_json=payload.get("extract_json", False),
        screenshot=payload.get("screenshot", False),
        extract_markdown=payload.get("extract_markdown", False),
        timeout=payload.get("timeout", 30),
    )
    return {"success": True, **result}


async def _run_render(payload: dict[str, Any]) -> dict[str, Any]:
    html = await render_url(
        url=payload["url"],
        wait_for=payload.get("wait_for"),
        timeout=payload.get("timeout", 30),
    )
    return {"success": True, "html": html}


async def _run_browser(payload: dict[str, Any]) -> dict[str, Any]:
    result = await browser_url(
        url=payload["url"],
        steps=payload.get("steps") or [],
        wait_for=payload.get("wait_for"),
        extract_json=payload.get("extract_json", False),
        screenshot=payload.get("screenshot", False),
        extract_markdown=payload.get("extract_markdown", False),
        timeout=payload.get("timeout", 30),
    )
    return {"success": True, **result}
