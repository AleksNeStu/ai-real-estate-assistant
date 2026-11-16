"""The CSRF double-submit, end to end between the cookie and the middleware.

The middleware compares the `X-CSRF-Token` header with the `csrf_token`
cookie, and it enforces that in production. The cookie was only ever set
when a caller passed a token - and no caller did - so the cookie never
existed, and a deployment that set ENVIRONMENT=production answered every
state-changing request with 403 "CSRF token missing": the login, the
search, the chat.

These tests hold the two halves together: the sign-in sets the cookie, and
the middleware accepts exactly the requests that carry it back.
"""

import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from api.middleware.csrf import CSRFMiddleware
from api.routers.auth_jwt import _set_auth_cookies


class TestTheCsrfCookie:
    """The cookie the browser sends back."""

    def test_sign_in_always_sets_the_cookie(self):
        response = Response()

        _set_auth_cookies(response, "access-token", "refresh-token")

        cookies = response.headers.getlist("set-cookie")
        assert any("csrf_token=" in cookie for cookie in cookies)

    def test_the_cookie_is_readable_by_javascript(self):
        # The browser has to read it and send it back as a header, so it
        # cannot be httpOnly.
        response = Response()

        _set_auth_cookies(response, "access-token", "refresh-token")

        csrf = next(c for c in response.headers.getlist("set-cookie") if "csrf_token=" in c)
        assert "HttpOnly" not in csrf

    def test_a_caller_may_still_pass_its_own_token(self):
        response = Response()

        _set_auth_cookies(response, "access-token", "refresh-token", csrf_token="mine")

        csrf = next(c for c in response.headers.getlist("set-cookie") if "csrf_token=" in c)
        assert "mine" in csrf


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(CSRFMiddleware)

    @app.post("/api/v1/thing")
    async def thing():
        return {"ok": True}

    @app.get("/api/v1/thing")
    async def read_thing():
        return {"ok": True}

    return TestClient(app)


class TestTheCsrfMiddleware:
    """The check the middleware performs."""

    @pytest.fixture(autouse=True)
    def _production(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            yield

    def test_a_matching_header_and_cookie_are_accepted(self):
        with _client() as client:
            client.cookies.set("csrf_token", "token-value")
            response = client.post(
                "/api/v1/thing",
                headers={"X-CSRF-Token": "token-value"},
            )

        assert response.status_code == 200

    def test_a_request_without_the_header_is_refused(self):
        with _client() as client:
            client.cookies.set("csrf_token", "token-value")
            response = client.post("/api/v1/thing")

        assert response.status_code == 403
        assert "CSRF" in response.json()["detail"]

    def test_a_mismatching_header_is_refused(self):
        with _client() as client:
            client.cookies.set("csrf_token", "token-value")
            response = client.post(
                "/api/v1/thing",
                headers={"X-CSRF-Token": "another-value"},
            )

        assert response.status_code == 403

    def test_a_safe_method_is_never_checked(self):
        with _client() as client:
            response = client.get("/api/v1/thing")

        assert response.status_code == 200

    def test_a_development_deployment_is_not_checked(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            with _client() as client:
                response = client.post("/api/v1/thing")

        assert response.status_code == 200
