from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import JSONResponse

from ..models import CheckoutRequest
from ...core.keys import create_api_key, set_user_plan
from ...core.redis import get_redis
from ...core.settings import (
    PLANS,
    DODOPAYMENTS_PRODUCT_IDS,
    get_dodopayments_url,
    normalize_email,
    DODOPAYMENTS_SELLER_ID,
)

router = APIRouter(prefix="/v1/billing")


@router.post("/checkout")
async def billing_checkout(req: CheckoutRequest):
    plan = req.plan
    if plan not in PLANS or plan == "free":
        raise HTTPException(status_code=400, detail="Paid plan required")

    redis = await get_redis()
    key_data = await redis.hgetall(f"apikey:{req.api_key}")
    if not key_data:
        raise HTTPException(status_code=404, detail="Invalid API key. Please generate a free key first.")
    
    # Safely decode bytes to strings (Redis returns bytes by default)
    key_data = {
        (k.decode("utf-8") if isinstance(k, bytes) else k):
        (v.decode("utf-8") if isinstance(v, bytes) else v)
        for k, v in key_data.items()
    }

    email = key_data.get("email")

    checkout_url = get_dodopayments_url(plan, email)
    return {"checkout_url": checkout_url, "session_id": "dodopayments"}


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
    
    data = payload.get("data") if isinstance(payload, dict) else None
    source = data if isinstance(data, dict) else payload

    email = source.get("email") or source.get("customer_email")
    product_id = source.get("product_id") or source.get("product") or ""
    seller_id = source.get("seller_id") or payload.get("seller_id")
    license_key = source.get("license_key")
    
    print(f"\n[WEBHOOK] Received Ping | Email: {email} | Product ID: {product_id}")

    # Security check: verify the ping actually came from your DodoPayments account
    if DODOPAYMENTS_SELLER_ID and seller_id != DODOPAYMENTS_SELLER_ID:
        print("[WEBHOOK] Rejected: Invalid seller_id")
        raise HTTPException(status_code=403, detail="Invalid seller_id")
    
    if not email or not product_id:
        print("[WEBHOOK] Ignored: Missing email or product_id")
        return JSONResponse({"received": True, "status": "ignored - missing data"})

    # Match the DodoPayments product ID back to our plans
    plan = None
    for p, pid in DODOPAYMENTS_PRODUCT_IDS.items():
        if pid and pid in product_id:
            plan = p
            break
            
    if not plan:
        print(f"[WEBHOOK] Ignored: Product ID '{product_id}' does not match any known plans.")
        return JSONResponse({"received": True, "status": "ignored - unknown product"})
            
    if email and plan in PLANS and plan != "free":
        email = normalize_email(email)
        redis = await get_redis()
        
        # DodoPayments doesn't use standard customer IDs, so we use a fallback ID when present
        customer_id = source.get("customer_id") or source.get("subscription_id") or ""
        await set_user_plan(redis, email, plan, customer_id)
        
        print(f"[WEBHOOK] Success! Upgrading user {email} to {plan} plan.")
        
        keys = await redis.smembers(f"keys:email:{email}")
        if not keys:
            # Direct purchase: use the DodoPayments license key as their API key
            await create_api_key(redis, email, plan, provided_key=license_key)
        else:
            # Safely decode bytes to strings to prevent malformed Redis keys
            keys_str = {k.decode("utf-8") if isinstance(k, bytes) else k for k in keys}
            # Upgrade their existing 'sk_' keys
            for api_key in keys_str:
                await redis.hset(f"apikey:{api_key}", mapping={"plan": plan})
            # Also register the DodoPayments license key so both work seamlessly
            if license_key and license_key not in keys_str:
                await create_api_key(redis, email, plan, provided_key=license_key)

    return JSONResponse({"received": True})
