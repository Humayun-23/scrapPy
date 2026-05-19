from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import JSONResponse

from ..models import CheckoutRequest
from ...core.keys import create_api_key, set_user_plan
from ...core.redis import get_redis
from ...core.settings import (
    PLANS,
    GUMROAD_PRODUCT_PERMALINKS,
    get_gumroad_url,
    normalize_email,
    GUMROAD_SELLER_ID,
)

router = APIRouter(prefix="/v1/billing")


@router.post("/checkout")
async def billing_checkout(req: CheckoutRequest):
    plan = req.plan
    if plan not in PLANS or plan == "free":
        raise HTTPException(status_code=400, detail="Paid plan required")

    checkout_url = get_gumroad_url(plan, req.email)
    return {"checkout_url": checkout_url, "session_id": "gumroad"}


@router.post("/webhook")
async def billing_webhook(request: Request):
    content_type = request.headers.get("Content-Type", "")
    
    try:
        # Handle both JSON and Form-Encoded payloads gracefully
        if "application/json" in content_type:
            payload = await request.json()
        else:
            payload = await request.form()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse payload: {str(exc)}")
    
    email = payload.get("email")
    permalink = payload.get("permalink")
    seller_id = payload.get("seller_id")
    
    # Security check: verify the ping actually came from your Gumroad account
    if GUMROAD_SELLER_ID and seller_id != GUMROAD_SELLER_ID:
        raise HTTPException(status_code=403, detail="Invalid seller_id")
    
    if not email or not permalink:
        return JSONResponse({"received": True, "status": "ignored - missing data"})

    # Match the Gumroad product permalink back to our plans
    plan = None
    for p, link in GUMROAD_PRODUCT_PERMALINKS.items():
        if link == permalink:
            plan = p
            break
            
    if email and plan in PLANS and plan != "free":
        email = normalize_email(email)
        redis = await get_redis()
        
        # Gumroad doesn't use standard customer IDs, so we use purchaser_id or sale_id
        customer_id = payload.get("purchaser_id", "")
        await set_user_plan(redis, email, plan, customer_id)
        
        keys = await redis.smembers(f"keys:email:{email}")
        if not keys:
            await create_api_key(redis, email, plan)
        else:
            for api_key in keys:
                await redis.hset(f"apikey:{api_key}", mapping={"plan": plan})

    return JSONResponse({"received": True})
