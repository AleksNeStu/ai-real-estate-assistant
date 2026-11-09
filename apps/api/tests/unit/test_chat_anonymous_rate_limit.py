"""The anonymous traffic of the public demo is counted.

A deployment with the API-key bypass on lets every visitor reach the chat.
Without a limit, a demo whose model is the studio's paid key is an open
wallet — so a request that carries no credential of its own is counted
against the free-tier limiter, and a request that does carry one is not.
"""

from starlette.requests import Request

from api.routers import chat
from config.settings import get_settings


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


class TestWhoIsAnonymous:
    def test_a_visitor_without_a_key_is_anonymous(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "demo_api_key_bypass", True, raising=False)

        assert chat._request_is_anonymous(_request()) is True

    def test_a_request_with_a_real_key_is_not(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "demo_api_key_bypass", True, raising=False)

        assert chat._request_is_anonymous(_request({"x-api-key": "a-real-key"})) is False

    def test_a_signed_in_visitor_is_not(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "demo_api_key_bypass", True, raising=False)

        request = _request(cookies={"access_token": "a-jwt"})
        assert chat._request_is_anonymous(request) is False

    def test_a_deployment_that_checks_the_key_needs_no_counter(self, monkeypatch):
        """Without the bypass the key dependency already rejected the visitor."""
        monkeypatch.setattr(get_settings(), "demo_api_key_bypass", False, raising=False)

        assert chat._request_is_anonymous(_request()) is False
