import uuid
from datetime import datetime
from typing import Optional


async def create_api_key(redis, email: str, plan: str, provided_key: Optional[str] = None) -> str:
    api_key = provided_key or ("sk_" + str(uuid.uuid4()).replace("-", ""))
    await redis.hset(f"apikey:{api_key}", mapping={
        "email": email,
        "plan": plan,
        "created_at": datetime.utcnow().isoformat(),
        "active": "true",
    })
    await redis.sadd(f"keys:email:{email}", api_key)
    return api_key


async def set_user_plan(redis, email: str, plan: str, stripe_customer_id: Optional[str] = None) -> None:
    user_key = f"user:{email}"
    payload = {"plan": plan}
    if stripe_customer_id:
        payload["stripe_customer_id"] = stripe_customer_id
    if await redis.exists(user_key):
        await redis.hset(user_key, mapping=payload)
    else:
        await redis.hset(user_key, mapping={
            "email": email,
            "plan": plan,
            "created_at": datetime.utcnow().isoformat(),
            **payload,
        })
