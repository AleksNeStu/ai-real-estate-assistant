"""The anonymous traffic of the public demo is counted.

A deployment with the API-key bypass on lets every visitor reach the chat.
Without a limit, a demo whose model is the studio's paid key is an open
wallet — so a request that carries no credential of its own is counted
against the free-tier limiter, and a request that does carry one is not.
"""

import time

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api.routers import chat
from config.settings import get_settings
from utils.free_tier import client_ip, get_free_tier_rate_limiter


def _request(
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    client: tuple[str, int] = ("203.0.113.7", 51234),
) -> Request:
    """A request as the router sees it."""
    raw = [(b"host", b"test")]
    for name, value in (headers or {}).items():
        raw.append((name.lower().encode(), value.encode()))
    if cookies:
        raw.append((b"cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()).encode()))

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/chat",
            "headers": raw,
            "client": client,
        }
    )


class TestTheAddressOfTheCaller:
    """The limit is counted against the visitor, not against the edge."""

    def test_the_socket_address_is_the_last_resort(self):
        assert client_ip(_request()) == "203.0.113.7"

    def test_the_proxy_header_wins(self):
        request = _request({"x-forwarded-for": "198.51.100.4"})
        assert client_ip(request) == "198.51.100.4"

    def test_the_first_address_of_a_chain_is_the_caller(self):
        request = _request({"x-forwarded-for": "198.51.100.4, 10.0.0.1"})
        assert client_ip(request) == "198.51.100.4"

    def test_the_edge_header_is_read_when_there_is_no_proxy_header(self):
        request = _request({"cf-connecting-ip": "198.51.100.9"})
        assert client_ip(request) == "198.51.100.9"


class TestWhoIsAnonymous:
    def test_a_visitor_without_a_session_is_anonymous(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "demo_api_key_bypass", True, raising=False)

        assert chat._request_is_anonymous(_request()) is True

    def test_the_api_key_does_not_make_a_visitor_a_user(self, monkeypatch):
        """The frontend proxy injects the key for every browser request."""
        monkeypatch.setattr(get_settings(), "demo_api_key_bypass", True, raising=False)

        request = _request({"x-api-key": "the-deployment-key"})
        assert chat._request_is_anonymous(request) is True

    def test_a_signed_in_visitor_is_not(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "demo_api_key_bypass", True, raising=False)

        request = _request(cookies={"access_token": "a-jwt"})
        assert chat._request_is_anonymous(request) is False

    def test_a_bearer_token_is_a_session(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "demo_api_key_bypass", True, raising=False)

        request = _request({"authorization": "Bearer a-jwt"})
        assert chat._request_is_anonymous(request) is False

    def test_a_deployment_that_checks_the_key_needs_no_counter(self, monkeypatch):
        """Without the bypass the key dependency already rejected the visitor."""
        monkeypatch.setattr(get_settings(), "demo_api_key_bypass", False, raising=False)

        assert chat._request_is_anonymous(_request()) is False


class TestTheCounter:
    """The counter is a counter: it counts, it trips, and it is per address."""

    async def test_the_limit_trips(self):
        limiter = get_free_tier_rate_limiter()

        for _ in range(limiter.hourly_limit):
            allowed, reason, _ = await limiter.check("198.51.100.4")
            assert allowed is True, reason

        allowed, reason, retry_after = await limiter.check("198.51.100.4")
        assert allowed is False
        assert "Hourly limit" in reason
        assert retry_after > 0

    async def test_another_address_has_its_own_counter(self):
        limiter = get_free_tier_rate_limiter()

        for _ in range(limiter.hourly_limit):
            await limiter.check("198.51.100.4")

        allowed, reason, _ = await limiter.check("198.51.100.5")
        assert allowed is True, reason

    async def test_the_router_refuses_the_request_over_the_limit(self):
        limiter = get_free_tier_rate_limiter()
        for _ in range(limiter.hourly_limit):
            await limiter.check("203.0.113.7")

        with pytest.raises(HTTPException) as raised:
            await chat._check_free_tier_rate_limit(_request())

        assert raised.value.status_code == 429
        assert (raised.value.headers or {}).get("Retry-After")

    async def test_the_dead_buckets_are_swept(self):
        """A public demo sees a new address on every visitor."""
        limiter = get_free_tier_rate_limiter()

        for index in range(limiter.hourly_limit + 1):
            await limiter.check(f"198.51.100.{index}")

        # Nothing has aged out yet, so every bucket is still there.
        assert len(limiter._daily) == limiter.hourly_limit + 1

        # A sweep with a clock far in the future drops them.
        limiter._sweep(time.monotonic() + 2 * 86400)
        assert limiter._daily == {}
        assert limiter._hourly == {}
