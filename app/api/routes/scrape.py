import time
import traceback
import socket
import ipaddress
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException

from ..deps import verify_api_key
from ..models import BatchRequest, BrowserRequest, ScrapeRequest
from ...jobs import enqueue_job
from ...scraper import scrape_url, render_url, batch_scrape, browser_url

router = APIRouter(prefix="/v1")

def validate_url(url: str):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            raise ValueError("Only HTTP/HTTPS schemes are allowed.")
        
        ip = socket.gethostbyname(parsed.hostname)
        if ipaddress.ip_address(ip).is_private or ipaddress.ip_address(ip).is_loopback:
            raise ValueError("Access to private network addresses is forbidden.")
    except socket.gaierror:
        raise ValueError("Could not resolve hostname.")
    except Exception as e:
        raise ValueError(f"Invalid URL: {e}")


@router.post("/scrape")
async def scrape(req: ScrapeRequest, auth: dict = Depends(verify_api_key)):
    try:
        validate_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        start = time.time()
        result = await scrape_url(
            url=req.url,
            wait_for=req.wait_for,
            extract_json=req.extract_json,
            screenshot=req.screenshot,
            timeout=req.timeout,
        )
        elapsed = round(time.time() - start, 2)
        return {
            "success": True,
            "url": req.url,
            "elapsed_seconds": elapsed,
            "plan": auth["plan"],
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
            **result,
        }
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/render")
async def render(req: ScrapeRequest, auth: dict = Depends(verify_api_key)):
    try:
        validate_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        start = time.time()
        html = await render_url(req.url, wait_for=req.wait_for, timeout=req.timeout)
        elapsed = round(time.time() - start, 2)
        return {
            "success": True,
            "url": req.url,
            "elapsed_seconds": elapsed,
            "html": html,
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
        }
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/render/async")
async def render_async(req: ScrapeRequest, auth: dict = Depends(verify_api_key)):
    try:
        validate_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    job = enqueue_job("render", req.model_dump())
    return {
        "success": True,
        "job_id": job.id,
        "status": job.get_status(),
        "status_url": f"/v1/jobs/{job.id}",
        "plan": auth["plan"],
        "requests_used": auth["usage"],
        "requests_remaining": auth["limit"] - auth["usage"],
    }


@router.post("/batch")
async def batch(req: BatchRequest, auth: dict = Depends(verify_api_key)):
    try:
        for url in req.urls:
            validate_url(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if len(req.urls) > 10:
        raise HTTPException(status_code=400, detail="Max 10 URLs per batch request")
    try:
        results = await batch_scrape(req.urls, wait_for=req.wait_for, timeout=req.timeout)
        return {
            "success": True,
            "count": len(results),
            "results": results,
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
        }
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/scrape/async")
async def scrape_async(req: ScrapeRequest, auth: dict = Depends(verify_api_key)):
    try:
        validate_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    job = enqueue_job("scrape", req.model_dump())
    return {
        "success": True,
        "job_id": job.id,
        "status": job.get_status(),
        "status_url": f"/v1/jobs/{job.id}",
        "plan": auth["plan"],
        "requests_used": auth["usage"],
        "requests_remaining": auth["limit"] - auth["usage"],
    }


@router.post("/browser")
async def browser(req: BrowserRequest, auth: dict = Depends(verify_api_key)):
    try:
        validate_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        start = time.time()
        result = await browser_url(
            url=req.url,
            steps=[step.model_dump() for step in (req.steps or [])],
            wait_for=req.wait_for,
            extract_json=req.extract_json,
            screenshot=req.screenshot,
            timeout=req.timeout,
        )
        elapsed = round(time.time() - start, 2)
        return {
            "success": True,
            "url": req.url,
            "elapsed_seconds": elapsed,
            "plan": auth["plan"],
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
            **result,
        }
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/browser/async")
async def browser_async(req: BrowserRequest, auth: dict = Depends(verify_api_key)):
    try:
        validate_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    payload = req.model_dump()
    payload["steps"] = [step.model_dump() for step in (req.steps or [])]
    job = enqueue_job("browser", payload)
    return {
        "success": True,
        "job_id": job.id,
        "status": job.get_status(),
        "status_url": f"/v1/jobs/{job.id}",
        "plan": auth["plan"],
        "requests_used": auth["usage"],
        "requests_remaining": auth["limit"] - auth["usage"],
    }
