import os
from fastapi import HTTPException

PLANS = {
    "free": {"requests": 100, "price": 0},
    "starter": {"requests": 10_000, "price": 29},
    "growth": {"requests": 50_000, "price": 139},
    "scale": {"requests": 200_000, "price": 449},
    "enterprise": {"requests": 999_999, "price": 999},
}

# Map your plans to your Gumroad product permalinks
GUMROAD_PRODUCT_PERMALINKS = {
    "starter": os.getenv("GUMROAD_PERMALINK_STARTER", "xtrhwc"),
    "growth": os.getenv("GUMROAD_PERMALINK_GROWTH", "jmjlku"),
    "scale": os.getenv("GUMROAD_PERMALINK_SCALE", "ufivvq"),
    "enterprise": os.getenv("GUMROAD_PERMALINK_ENTERPRISE", "enterprise"),
}

GUMROAD_SELLER_ID = os.getenv("GUMROAD_SELLER_ID")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_gumroad_url(plan: str, email: str) -> str:
    permalink = GUMROAD_PRODUCT_PERMALINKS.get(plan)
    if not permalink:
        raise HTTPException(status_code=500, detail=f"Missing Gumroad permalink for plan: {plan}")
    return f"https://roshid0.gumroad.com/l/{permalink}?email={email}"
