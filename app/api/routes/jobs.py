from fastapi import APIRouter, Depends, HTTPException
from rq.exceptions import NoSuchJobError

from ..deps import verify_api_key
from ...jobs import fetch_job

router = APIRouter(prefix="/v1/jobs")


@router.get(
    "/{job_id}",
    summary="Get Job Status",
    description="Retrieve the status and optional result of a previously enqueued asynchronous job."
)
async def job_status(job_id: str, auth: dict = Depends(verify_api_key)):
    try:
        job = fetch_job(job_id)
    except NoSuchJobError:
        raise HTTPException(status_code=404, detail="Job not found")
    status = job.get_status()
    response = {"job_id": job.id, "status": status}
    if status == "finished":
        response["result"] = job.result
    return response


@router.post(
    "/{job_id}/cancel",
    summary="Cancel a Job",
    description="Attempt to cancel a pending or currently running asynchronous job."
)
async def job_cancel(job_id: str, auth: dict = Depends(verify_api_key)):
    try:
        job = fetch_job(job_id)
    except NoSuchJobError:
        raise HTTPException(status_code=404, detail="Job not found")
    status = job.get_status()
    if status in {"finished", "failed", "canceled"}:
        raise HTTPException(status_code=409, detail=f"Job already {status}")
    job.cancel()
    if status == "started":
        return {"job_id": job.id, "status": "cancel_requested"}
    return {"job_id": job.id, "status": "canceled"}
