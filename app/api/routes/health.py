from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    return {
        "service": "Scrappy API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "operational",
    }


@router.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
