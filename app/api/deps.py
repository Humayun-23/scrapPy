from datetime import datetime

from fastapi import Header, HTTPException

from ..core.redis import get_redis
from ..core.settings import PLANS


async def verify_api_key(x_api_key: str = Header(...)):
    redis = await get_redis()
    key_data = await redis.hgetall(f"apikey:{x_api_key}")
    if not key_data:
        raise HTTPException(status_code=401, detail="Invalid API key")
    plan = key_data.get("plan", "free")
    limit = PLANS[plan]["requests"]
    month = datetime.utcnow().strftime("%Y-%m")
    usage_key = f"usage:{x_api_key}:{month}"
    usage = int(await redis.get(usage_key) or 0)
    if usage >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly limit of {limit} requests reached. Upgrade your plan.",
        )
    await redis.incr(usage_key)
    await redis.expire(usage_key, 60 * 60 * 24 * 32)
    return {"api_key": x_api_key, "plan": plan, "usage": usage + 1, "limit": limit}
