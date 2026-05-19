from datetime import datetime

from fastapi import Header, HTTPException

from ..core.redis import get_redis
from ..core.settings import PLANS


async def verify_api_key(x_api_key: str = Header(...)):
    redis = await get_redis()
    key_data = await redis.hgetall(f"apikey:{x_api_key}")
    if not key_data:
        raise HTTPException(status_code=401, detail="Invalid API key")
        
    # Safely decode bytes to strings (Redis returns bytes by default)
    key_data = {
        (k.decode("utf-8") if isinstance(k, bytes) else k):
        (v.decode("utf-8") if isinstance(v, bytes) else v)
        for k, v in key_data.items()
    }

    plan = key_data.get("plan", "free")
    limit = PLANS[plan]["requests"]
    month = datetime.utcnow().strftime("%Y-%m")
    usage_key = f"usage:{x_api_key}:{month}"

    # Use INCR first to avoid race conditions on concurrent requests
    usage = await redis.incr(usage_key)
    if usage == 1:
        await redis.expire(usage_key, 60 * 60 * 24 * 32)

    if usage > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly limit of {limit} requests reached. Upgrade your plan.",
        )
    return {"api_key": x_api_key, "plan": plan, "usage": usage, "limit": limit}
