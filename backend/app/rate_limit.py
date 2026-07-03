"""Shared rate-limiting key function.

Consolidates what used to be 4 identical copies of this function (main.py,
jobs.py, credentials.py, profile.py) and fixes a real gap found in a security
audit: slowapi's own `get_remote_address()` reads only `request.client.host`,
never any forwarded-for header. Behind Fly.io's edge proxy, with uvicorn
started without `--proxy-headers` (deliberately — trusting an arbitrary
X-Forwarded-For would let a client forge it), `request.client.host` reflects
Fly's internal proxy address, not the real visitor, for every unauthenticated
request. Fly's own `Fly-Client-IP` header is set by Fly's edge and cannot be
forged by a client outside Fly's network, so it's used first when present.
"""
from fastapi import Request


def get_client_ip(request: Request) -> str:
    fly_client_ip = request.headers.get("fly-client-ip")
    if fly_client_ip:
        return fly_client_ip
    return request.client.host if request.client else "127.0.0.1"


def limiter_key(request: Request) -> str:
    """Rate-limit by the bearer token when present; fall back to the real
    client IP for unauthenticated paths."""
    auth_header = request.headers.get("authorization", "")
    return auth_header or get_client_ip(request)
