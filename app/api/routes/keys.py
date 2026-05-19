import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks

from ..deps import verify_api_key
from ..models import KeyCreateRequest
from ...core.keys import create_api_key
from ...core.redis import get_redis
from ...core.settings import PLANS, normalize_email

router = APIRouter(prefix="/v1")


def send_api_key_email(email_address: str, api_key: str):
    """Sends the generated API key to the user's email."""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    
    if not all([smtp_server, smtp_user, smtp_pass]):
        # Fallback for local development if SMTP is not configured
        print(f"\n[EMAIL MOCK] To: {email_address} | Subject: Your Scrappie API Key\nKey: {api_key}\n")
        return

    msg = EmailMessage()
    msg.set_content(f"Welcome to Scrappie!\n\nYour free API key is: {api_key}\n\nKeep it secret, keep it safe.")
    msg["Subject"] = "Your Scrappie API Key"
    msg["From"] = smtp_from
    msg["To"] = email_address

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            print(f"[EMAIL SUCCESS] API key sent to {email_address}")
    except Exception as e:
        print(f"Failed to send email to {email_address}: {e}")


@router.post("/keys/create")
async def create_key(req: KeyCreateRequest, request: Request, background_tasks: BackgroundTasks):
    if req.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose: {list(PLANS.keys())}")
    redis = await get_redis()
    
    # 1. IP-based Rate Limiting (max 3 per day per IP)
    client_ip = request.headers.get("X-Forwarded-For") or (request.client.host if request.client else "unknown")
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
