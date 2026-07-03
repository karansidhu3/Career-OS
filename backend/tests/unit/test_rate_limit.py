from unittest.mock import MagicMock

from app.rate_limit import get_client_ip, limiter_key


def _make_request(headers: dict, client_host: str | None = "1.2.3.4") -> MagicMock:
    request = MagicMock()
    request.headers = headers
    request.client = MagicMock(host=client_host) if client_host else None
    return request


def test_get_client_ip_prefers_fly_client_ip_header():
    request = _make_request({"fly-client-ip": "203.0.113.7"}, client_host="10.0.0.1")
    assert get_client_ip(request) == "203.0.113.7"


def test_get_client_ip_falls_back_to_request_client_host():
    request = _make_request({}, client_host="10.0.0.1")
    assert get_client_ip(request) == "10.0.0.1"


def test_get_client_ip_falls_back_to_loopback_when_no_client():
    request = _make_request({}, client_host=None)
    assert get_client_ip(request) == "127.0.0.1"


def test_get_client_ip_ignores_x_forwarded_for():
    """The whole point: X-Forwarded-For is not trusted (a client can set it to
    anything), unlike Fly-Client-IP, which is set by Fly's own edge."""
    request = _make_request({"x-forwarded-for": "6.6.6.6"}, client_host="10.0.0.1")
    assert get_client_ip(request) == "10.0.0.1"


def test_limiter_key_uses_authorization_header_when_present():
    request = _make_request({"authorization": "Bearer abc123"}, client_host="10.0.0.1")
    assert limiter_key(request) == "Bearer abc123"


def test_limiter_key_falls_back_to_client_ip_when_unauthenticated():
    request = _make_request({"fly-client-ip": "203.0.113.7"})
    assert limiter_key(request) == "203.0.113.7"
