"""The anonymous traffic of the public demo is counted.

A deployment with the API-key bypass on lets every visitor reach the chat.
Without a limit, a demo whose model is the studio's paid key is an open
wallet — so a request that carries no credential of its own is counted
against the free-tier limiter, and a request that does carry one is not.
"""

from starlette.requests import Request

from api.routers import chat
from config.settings import get_settings
from utils.free_tier import client_ip


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
