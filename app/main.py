from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import time
from typing import Optional
from pydantic import BaseModel

from .api.routes import billing, health, internal, job_market, keys, proxy
from .jobs_scraper import scrape_naukri, get_salary_intelligence, get_skills_trending
from pydantic import BaseModel, Field
from typing import Optional
import time

from .jobs_scraper import scrape_naukri, get_salary_intelligence, get_skills_trending


# Assuming verify_api_key handles validation internally
from .api.routes.keys import verify_api_key

def create_app() -> FastAPI:
    app = FastAPI(
        title="Scrappy API",
        description="Stealth web scraping powered by CloakBrowser + Hysteria2",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(job_market.router)
    app.include_router(proxy.router)
    app.include_router(billing.router)
    app.include_router(keys.router)
    app.include_router(internal.router)

    return app


app = create_app()

class JobSearchRequest(BaseModel):
    query: str
    location: str = "india"
    experience_min: Optional[int] = 0
    experience_max: Optional[int] = 10
    limit: Optional[int] = 50

class SalaryRequest(BaseModel):
    role: str
    location: str = "india"
    experience: int = 3

class SkillsRequest(BaseModel):
    category: str = "backend"
    location: str = "india"

@app.post("/v1/jobs/search")
async def jobs_search(req: JobSearchRequest, auth: dict = Depends(verify_api_key)):
    """Search Indian job listings from Naukri.com"""
    try:
        start = time.time()
        result = await scrape_naukri(
            query=req.query,
            location=req.location,
            experience_min=req.experience_min,
            experience_max=req.experience_max,
            limit=req.limit,
        )
        elapsed = round(time.time() - start, 2)
        return {
            "success": True,
            "query": req.query,
            "location": req.location,
            "returned": len(result["jobs"]),
            "cached": result.get("cached", False),
            "elapsed_seconds": elapsed,
            "jobs": result["jobs"],
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/jobs/salary")
async def jobs_salary(req: SalaryRequest, auth: dict = Depends(verify_api_key)):
    """Get salary intelligence for a role in India"""
    try:
        result = await get_salary_intelligence(
            role=req.role,
            location=req.location,
            experience=req.experience,
        )
        if not result:
            raise HTTPException(status_code=404, 
                              detail="Not enough salary data for this query")
        return {
            "success": True,
            "role": req.role,
            "location": req.location,
            "experience_years": req.experience,
            **result,
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/jobs/skills")
async def jobs_skills(req: SkillsRequest, auth: dict = Depends(verify_api_key)):
    """Get trending skills by category in India"""
    try:
        result = await get_skills_trending(
            category=req.category,
            location=req.location,
        )
        return {
            "success": True,
            "category": req.category,
            "location": req.location,
            "trending_skills": result,
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class JobSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=100)
    location: str = Field(default="india", max_length=50)
    experience_min: Optional[int] = Field(default=0, ge=0)
    experience_max: Optional[int] = Field(default=10, ge=0, le=50)
    limit: Optional[int] = Field(default=50, ge=1, le=100) # Prevents massive requests overloading RAM

class SalaryRequest(BaseModel):
    role: str = Field(..., min_length=2, max_length=100)
    location: str = Field(default="india", max_length=50)
    experience: int = Field(default=3, ge=0, le=50)

class SkillsRequest(BaseModel):
    category: str = Field(default="backend", max_length=50)
    location: str = Field(default="india", max_length=50)

@app.post("/v1/jobs/search")
async def jobs_search(req: JobSearchRequest, auth: dict = Depends(verify_api_key)):
    """Search Indian job listings from Naukri.com"""
    try:
        start = time.time()
        result = await scrape_naukri(
            query=req.query,
            location=req.location,
            experience_min=req.experience_min,
            experience_max=req.experience_max,
            limit=req.limit,
        )
        elapsed = round(time.time() - start, 2)
        return {
            "success": True,
            "query": req.query,
            "location": req.location,
            "returned": len(result["jobs"]),
            "cached": result.get("cached", False),
            "elapsed_seconds": elapsed,
            "jobs": result["jobs"],
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/jobs/salary")
async def jobs_salary(req: SalaryRequest, auth: dict = Depends(verify_api_key)):
    """Get salary intelligence for a role in India"""
    try:
        result = await get_salary_intelligence(
            role=req.role,
            location=req.location,
            experience=req.experience,
        )
        if not result:
            raise HTTPException(status_code=404, detail="Not enough salary data for this query")
        return {
            "success": True,
            "role": req.role,
            "location": req.location,
            "experience_years": req.experience,
            **result,
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/jobs/skills")
async def jobs_skills(req: SkillsRequest, auth: dict = Depends(verify_api_key)):
    """Get trending skills by category in India"""
    try:
        result = await get_skills_trending(
            category=req.category,
            location=req.location,
        )
        return {
            "success": True,
            "category": req.category,
            "location": req.location,
            "trending_skills": result,
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
