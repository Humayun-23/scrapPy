import os

import stripe
from fastapi import HTTPException

PLANS = {
    "free": {"requests": 100, "price": 0},
    "starter": {"requests": 10_000, "price": 49},
    "growth": {"requests": 50_000, "price": 149},
    "scale": {"requests": 200_000, "price": 499},
    "enterprise": {"requests": 999_999, "price": 999},
}

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL")
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL")

STRIPE_PRICE_IDS = {
    "starter": os.getenv("STRIPE_PRICE_STARTER"),
    "growth": os.getenv("STRIPE_PRICE_GROWTH"),
    "scale": os.getenv("STRIPE_PRICE_SCALE"),
    "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE"),
}


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_price_id(plan: str) -> str:
    price_id = STRIPE_PRICE_IDS.get(plan)
    if not price_id:
        raise HTTPException(status_code=500, detail=f"Missing Stripe price ID for plan: {plan}")
    return price_id


def require_stripe() -> None:
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_SECRET_KEY")
    stripe.api_key = STRIPE_SECRET_KEY
