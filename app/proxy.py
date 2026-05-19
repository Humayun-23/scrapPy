"""
proxy.py — Hysteria2 proxy credential generator
Generates per-user SOCKS5/HTTP proxy credentials backed by Hysteria2 nodes.
"""
import os
import hashlib

# Your Hysteria2 server nodes — add more for multi-region
NODES = {
    "us": {
        "host": os.getenv("HYSTERIA_US_HOST", "us1.scrappy.io"),
        "socks5_port": int(os.getenv("HYSTERIA_US_SOCKS5_PORT", "1080")),
        "http_port":   int(os.getenv("HYSTERIA_US_HTTP_PORT",   "8080")),
    },
    "eu": {
        "host": os.getenv("HYSTERIA_EU_HOST", "eu1.scrappy.io"),
        "socks5_port": int(os.getenv("HYSTERIA_EU_SOCKS5_PORT", "1080")),
        "http_port":   int(os.getenv("HYSTERIA_EU_HTTP_PORT",   "8080")),
    },
    "asia": {
        "host": os.getenv("HYSTERIA_ASIA_HOST", "sg1.scrappy.io"),
        "socks5_port": int(os.getenv("HYSTERIA_ASIA_SOCKS5_PORT", "1080")),
        "http_port":   int(os.getenv("HYSTERIA_ASIA_HTTP_PORT",   "8080")),
    },
}

PROXY_SECRET = os.getenv("PROXY_SECRET")
if not PROXY_SECRET:
    raise ValueError("CRITICAL SECURITY RISK: PROXY_SECRET environment variable is missing and must be set in production.")


def get_proxy_credentials(region: str, api_key: str) -> dict:
    """
    Generate deterministic proxy credentials for an API key + region.
    Hysteria2 server validates these via its auth backend (see hysteria-server.yaml).
    """
    if region not in NODES:
        region = "us"

    node = NODES[region]

    # Deterministic username/password from api_key so no DB lookup needed
    # Hysteria2 auth backend calls our /internal/proxy-auth endpoint to verify
    username = hashlib.sha256(f"{api_key}:{region}".encode()).hexdigest()[:16]
    password = hashlib.sha256(f"{api_key}:{PROXY_SECRET}".encode()).hexdigest()[:32]

    return {
        "host":        node["host"],
        "socks5_port": node["socks5_port"],
        "http_port":   node["http_port"],
        "user":        username,
        "pass":        password,
        "region":      region,
    }


# ── Internal auth endpoint (Hysteria2 calls this to validate proxy users) ─────
# Add this route in main.py if you want Hysteria2's auth backend to call home:
#
# @app.get("/internal/proxy-auth")
# async def proxy_auth(username: str, password: str):
#     """Called by Hysteria2 server to verify proxy credentials."""
#     # Verify by recomputing the expected credentials
#     # In production: look up the api_key from the username hash in Redis
#     return {"ok": True}  # or {"ok": False}
