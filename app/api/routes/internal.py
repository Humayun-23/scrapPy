from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..core.redis import get_redis

router = APIRouter()


@router.get("/internal/proxy-auth")
async def proxy_auth(username: str, password: str):
    try:
        if len(username) == 16 and len(password) == 32:
            redis = await get_redis()
            return JSONResponse({"ok": True})
        return JSONResponse({"ok": False})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)})
