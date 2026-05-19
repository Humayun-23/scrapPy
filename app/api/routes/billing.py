import stripe
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..models import CheckoutRequest
from ...core.keys import create_api_key, set_user_plan
from ...core.redis import get_redis
from ...core.settings import (
    PLANS,
    STRIPE_CANCEL_URL,
    STRIPE_SUCCESS_URL,
    STRIPE_WEBHOOK_SECRET,
    get_price_id,
    normalize_email,
    require_stripe,
)

router = APIRouter(prefix="/v1/billing")


@router.post("/checkout")
async def billing_checkout(req: CheckoutRequest):
    plan = req.plan
    if plan not in PLANS or plan == "free":
        raise HTTPException(status_code=400, detail="Paid plan required")
    success_url = req.success_url or STRIPE_SUCCESS_URL
    cancel_url = req.cancel_url or STRIPE_CANCEL_URL
    if not success_url or not cancel_url:
        raise HTTPException(status_code=400, detail="Missing success_url or cancel_url")
    require_stripe()
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": get_price_id(plan), "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        customer_email=normalize_email(req.email),
        metadata={"plan": plan, "email": normalize_email(req.email)},
        allow_promotion_codes=True,
    )
    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/webhook")
async def billing_webhook(request: Request):
    require_stripe()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Missing STRIPE_WEBHOOK_SECRET")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Webhook error: {exc}")

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email") or session.get("customer_details", {}).get("email")
        metadata = session.get("metadata") or {}
        plan = metadata.get("plan")
        if email and plan in PLANS and plan != "free":
            email = normalize_email(email)
            redis = await get_redis()
            await set_user_plan(redis, email, plan, session.get("customer"))
            keys = await redis.smembers(f"keys:email:{email}")
            if not keys:
                await create_api_key(redis, email, plan)
            else:
                for api_key in keys:
                    await redis.hset(f"apikey:{api_key}", mapping={"plan": plan})

    return JSONResponse({"received": True})
