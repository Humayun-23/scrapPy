from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from ..deps import verify_api_key
from ..models import ProxyRequest
from ...proxy import get_proxy_credentials

router = APIRouter(prefix="/v1/proxy")


@router.post("/credentials")
async def proxy_credentials(req: ProxyRequest, auth: dict = Depends(verify_api_key)):
    if auth["plan"] == "free":
        raise HTTPException(status_code=403, detail="Proxy access requires a paid plan")
    creds = get_proxy_credentials(region=req.region, api_key=auth["api_key"])
    return {
        "success": True,
        "region": req.region,
        "socks5": f"socks5://{creds['user']}:{creds['pass']}@{creds['host']}:{creds['socks5_port']}",
        "http": f"http://{creds['user']}:{creds['pass']}@{creds['host']}:{creds['http_port']}",
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "note": "Powered by Hysteria2 — QUIC transport masquerading as HTTP/3",
    }
