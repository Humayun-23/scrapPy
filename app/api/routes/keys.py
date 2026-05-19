from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from ..deps import verify_api_key
from ..models import KeyCreateRequest
from ...core.keys import create_api_key
from ...core.redis import get_redis
from ...core.settings import PLANS, normalize_email

router = APIRouter(prefix="/v1")


@router.post("/keys/create")
async def create_key(req: KeyCreateRequest):
    if req.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose: {list(PLANS.keys())}")
    redis = await get_redis()
    email = normalize_email(req.email)
    api_key = await create_api_key(redis, email, req.plan)
    return {
        "api_key": api_key,
        "plan": req.plan,
        "monthly_limit": PLANS[req.plan]["requests"],
        "message": "Store this key securely. It won't be shown again.",
    }


@router.get("/keys/usage")
async def key_usage(auth: dict = Depends(verify_api_key)):
    return {
        "plan": auth["plan"],
        "requests_used": auth["usage"],
        "requests_remaining": auth["limit"] - auth["usage"],
        "monthly_limit": auth["limit"],
        "reset_date": (
            datetime.utcnow().replace(day=1) + timedelta(days=32)
        ).replace(day=1).strftime("%Y-%m-%d"),
    }


@router.get("/plans")
async def list_plans():
    return {
        "plans": [
            {
                "name": name,
                "monthly_requests": data["requests"],
                "price_usd": data["price"],
                "price_per_1k": round(data["price"] / data["requests"] * 1000, 3)
                if data["price"] > 0
                else 0,
            }
            for name, data in PLANS.items()
        ]
    }
