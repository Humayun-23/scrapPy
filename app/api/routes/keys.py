import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks

from ..deps import verify_api_key
from ..models import KeyCreateRequest
from ...core.keys import create_api_key
from ...core.redis import get_redis
from ...core.settings import PLANS, normalize_email

router = APIRouter(prefix="/v1")


def send_api_key_email(email_address: str, api_key: str):
    """Sends the API key using Brevo's HTTP API, bypassing SMTP blocks."""
    brevo_api_key = os.getenv("BREVO_API_KEY")
    email_from = os.getenv("EMAIL_FROM")
    
    if not brevo_api_key or not email_from:
        print(f"\n[EMAIL MOCK] To: {email_address} | Subject: Your Scrappie API Key\nKey: {api_key}\n")
        return

    url = "https://api.brevo.com/v3/smtp/email"
    payload = {
        "sender": {"email": email_from, "name": "Scrappie API"},
        "to": [{"email": email_address}],
        "subject": "Your Scrappie API Key",
        "htmlContent": f"<p>Welcome to Scrappie!</p><p>Your free API key is: <strong>{api_key}</strong></p><p>Keep it secret, keep it safe.</p>"
    }
    
    headers = {
        "accept": "application/json",
        "api-key": brevo_api_key,
        "content-type": "application/json"
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            print(f"[EMAIL SUCCESS] API key sent to {email_address} via API")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"Failed to send email to {email_address}: {e.code} - {err_msg}")
    except Exception as e:
        print(f"Failed to send email to {email_address}: {e}")


@router.post("/keys/create")
async def create_key(req: KeyCreateRequest, request: Request, background_tasks: BackgroundTasks):
    if req.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose: {list(PLANS.keys())}")
    redis = await get_redis()
    
    # 1. IP-based Rate Limiting (max 3 per day per IP)
    client_ip = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For") or (request.client.host if request.client else "unknown")
    client_ip = client_ip.split(",")[0].strip()
    rate_limit_key = f"rate_limit:keys:create:{client_ip}"
    
    requests_today = await redis.get(rate_limit_key)
    if requests_today and int(requests_today) >= 3:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Maximum 3 keys per IP per day.")
        
    # Increment usage and set a 24-hour expiry for the first request
    pipe = redis.pipeline()
    pipe.incr(rate_limit_key)
    if not requests_today:
        pipe.expire(rate_limit_key, 86400)
    await pipe.execute()

    # 2. Generate Key
    email = normalize_email(req.email)
    api_key = await create_api_key(redis, email, req.plan)
    
    # 3. Send email in background to avoid blocking the HTTP response
    background_tasks.add_task(send_api_key_email, email, api_key)
    
    # 4. Return generic success message
    return {
        "success": True,
        "plan": req.plan,
        "monthly_limit": PLANS[req.plan]["requests"],
        "message": f"If {email} is valid, your API key has been sent there.",
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


@router.get("/admin/stats")
async def get_admin_stats(request: Request):
    """Returns aggregate usage statistics for all API keys."""
    admin_secret = os.getenv("ADMIN_SECRET")
    if not admin_secret or request.headers.get("x-admin-secret") != admin_secret:
        raise HTTPException(
            status_code=403, 
            detail="Forbidden. Set ADMIN_SECRET env var and pass x-admin-secret header."
        )

    redis = await get_redis()
    free_keys, paid_keys, total_requests = 0, 0, 0

    # Scan through all API keys in Redis
    async for key in redis.scan_iter("apikey:*"):
        raw_data = await redis.hgetall(key)
        if not raw_data:
            continue
            
        # Safely decode from bytes to strings
        key_data = {
            (k.decode("utf-8") if isinstance(k, bytes) else k):
            (v.decode("utf-8") if isinstance(v, bytes) else v)
            for k, v in raw_data.items()
        }
        
        if key_data.get("plan", "free") == "free":
            free_keys += 1
        else:
            paid_keys += 1
            
        total_requests += int(key_data.get("usage") or 0)

    return {
        "free_users": free_keys,
        "upgraded_users": paid_keys,
        "total_api_requests": total_requests
    }
