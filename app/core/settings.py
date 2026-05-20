import os
from urllib.parse import urlencode

from fastapi import HTTPException

PLANS = {
    "free": {"requests": 100, "price": 0},
    "starter": {"requests": 10_000, "price": 29},
    "growth": {"requests": 50_000, "price": 139},
    "scale": {"requests": 200_000, "price": 449},
    "enterprise": {"requests": 999_999, "price": 999},
}

# Map your plans to your DodoPayments product IDs
DODOPAYMENTS_PRODUCT_IDS = {
    "starter": os.getenv("DODOPAYMENTS_PRODUCT_STARTER", "pdt_0NfEsMpd3CzJlmLus7wXT"),
    "growth": os.getenv("DODOPAYMENTS_PRODUCT_GROWTH", "pdt_0NfEsT6GnNMKqy2mzvm3j"),
    "scale": os.getenv("DODOPAYMENTS_PRODUCT_SCALE", "pdt_0NfEsaRBZYRlOw6MhdUrR"),
    "enterprise": os.getenv("DODOPAYMENTS_PRODUCT_ENTERPRISE", ""),
}

DODOPAYMENTS_SELLER_ID = os.getenv("DODOPAYMENTS_SELLER_ID")
DODOPAYMENTS_CHECKOUT_BASE = os.getenv("DODOPAYMENTS_CHECKOUT_BASE", "https://checkout.dodopayments.com/buy")
DODOPAYMENTS_RETURN_URL = os.getenv("DODOPAYMENTS_RETURN_URL")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_dodopayments_url(plan: str, email: str, redirect_url: str | None = None) -> str:
    product_id = DODOPAYMENTS_PRODUCT_IDS.get(plan)
    if not product_id:
        raise HTTPException(status_code=500, detail=f"Missing DodoPayments product ID for plan: {plan}")
    redirect_url = redirect_url or DODOPAYMENTS_RETURN_URL
    if not redirect_url:
        raise HTTPException(status_code=500, detail="Missing DodoPayments redirect_url")
    base = DODOPAYMENTS_CHECKOUT_BASE.rstrip("/")
    query = urlencode({"quantity": 1, "redirect_url": redirect_url, "email": email})
    return f"{base}/{product_id}?{query}"
