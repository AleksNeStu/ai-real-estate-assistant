#!/usr/bin/env python3
"""Verify the authentication flow end to end against a running deployment.

The script talks to a deployed instance of this project (the public demo, a
staging box, a local stack) and walks the whole auth path:

    register -> login -> authenticated call -> refresh -> logout -> the old
    refresh token no longer works

It also checks the two promises the demo makes about its own surface:

  * the public routes answer WITHOUT a login;
  * the account routes answer 401 WITHOUT a token.

Every input comes from the environment. Nothing is ever read from argv and no
credential, token or password is printed, logged or written to disk.

Environment
-----------
  AIRE_BASE_URL        base URL of the deployment, e.g. https://realty.kittray.com
                       (required; the API is reached at <base>/api/v1)
  AIRE_TEST_EMAIL      e-mail of the test account (required for the auth steps)
  AIRE_TEST_PASSWORD   password of the test account (required for the auth steps)

Exit codes
----------
  0  every step that ran passed
  1  at least one step failed
  2  the environment does not carry what the run needs (the missing variable
     names are printed; nothing is invented)
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from typing import Any, Optional

BASE_URL_ENV = "AIRE_BASE_URL"
EMAIL_ENV = "AIRE_TEST_EMAIL"
PASSWORD_ENV = "AIRE_TEST_PASSWORD"  # pragma: allowlist secret - the NAME of a variable, not a value

# The public surface of the demo: it answers without a login.
PUBLIC_PATHS = ("/api/v1/capabilities", "/api/v1/properties")

# The account surface: it answers 401 without a token.
ACCOUNT_PATHS = ("/api/v1/favorites", "/api/v1/saved-searches")

GOOGLE_AUTHORIZE_HOST = "accounts.google.com"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_MISSING_ENV = 2


class StepError(Exception):
    """A step could not be carried out (as opposed to a step that failed)."""


class Client:
    """A tiny HTTP client that keeps cookies between calls."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            _NoRedirect(),
        )
        self.opener.addheaders = []

    def url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> tuple[int, str, bytes]:
        """Perform one request and return (status, body-as-text, raw-body)."""
        url = self.url(path)
        data = None
        request_headers = {
            "Accept": "application/json",
            "User-Agent": "ai-real-estate-assistant-live-auth-check/1.0",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)

        request = urllib.request.Request(url, data=data, method=method)
        for name, value in request_headers.items():
            request.add_header(name, value)

        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read()
                return response.status, raw.decode("utf-8", "replace"), raw
        except urllib.error.HTTPError as error:
            raw = error.read()
            return error.code, raw.decode("utf-8", "replace"), raw
        except urllib.error.URLError as error:
            raise StepError(
                f"the deployment could not be reached: {error.reason}"
            ) from error
        except OSError as error:
            raise StepError(f"the deployment could not be reached: {error}") from error

    def cookie(self, name: str) -> Optional[str]:
        for cookie in self.jar:
            if cookie.name == name:
                return cookie.value
        return None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Surface a redirect instead of following it.

    The standard handler follows the redirect and the caller never sees the
    status code that was actually answered. Answering it as an error keeps
    the status visible - which matters when the check is about "does this
    route answer 200 / 401 / 302".
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102, ANN001
        return None


class Reporter:
    """Prints one PASS/FAIL line per step and keeps the tally."""

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def step(self, title: str) -> None:
        print(f"\n=== {title}")

    def ok(self, detail: str) -> None:
        self.passed += 1
        print(f"PASS  {detail}")

    def fail(self, detail: str) -> None:
        self.failed += 1
        print(f"FAIL  {detail}")

    def skip(self, detail: str) -> None:
        self.skipped += 1
        print(f"SKIP  {detail}")

    def info(self, detail: str) -> None:
        print(f"INFO  {detail}")


def mask_email(email: str) -> str:
    """Mask an address so the output never carries a full inbox."""
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    head = local[:1] if local else ""
    return f"{head}***@{domain}"


def parse_json(body: str) -> dict[str, Any]:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def check_public_surface(client: Client, reporter: Reporter) -> None:
    """The public routes must answer without a login."""
    reporter.step("Public routes answer without a login")
    for path in PUBLIC_PATHS:
        status, _body, _raw = client.request("GET", path)
        if status == 200:
            reporter.ok(f"GET {path} -> {status}")
        else:
            reporter.fail(f"GET {path} -> {status} (expected 200 without a login)")


def check_account_surface(client: Client, reporter: Reporter) -> None:
    """The account routes must answer 401 without a token."""
    reporter.step("Account routes answer 401 without a token")
    for path in ACCOUNT_PATHS:
        status, _body, _raw = client.request("GET", path)
        if status == 401:
            reporter.ok(f"GET {path} -> {status}")
        else:
            reporter.fail(f"GET {path} -> {status} (expected 401 without a token)")


def check_oauth_entry_point(client: Client, reporter: Reporter) -> None:
    """The Google entry point must OFFER the flow, not complete it.

    The authorization URL is read and nothing more: the flow is never
    followed, no Google sign-in is attempted and no account of any kind is
    used.
    """
    reporter.step("Google OAuth is offered as an entry point")
    status, body, _raw = client.request("GET", "/api/v1/auth/oauth/google")
    if status != 200:
        reporter.fail(f"GET /api/v1/auth/oauth/google -> {status} (expected 200)")
        return
    authorization_url = parse_json(body).get("authorization_url", "")
    if not isinstance(authorization_url, str) or not authorization_url:
        reporter.fail("the response carried no authorization_url")
        return
    host = urllib.parse.urlparse(authorization_url).netloc
    if host != GOOGLE_AUTHORIZE_HOST:
        reporter.fail(
            f"the authorize endpoint is {host or '(none)'}, expected {GOOGLE_AUTHORIZE_HOST}"
        )
        return
    reporter.ok(f"the authorize endpoint is {host} (the flow was not followed)")


def check_register(
    client: Client,
    reporter: Reporter,
    email: str,
    password: str,
) -> tuple[Optional[str], bool]:
    """Register the test account and return (access token, account existed)."""
    reporter.step("Register the test account")
    status, body, _raw = client.request(
        "POST",
        "/api/v1/auth/register",
        body={
            "email": email,
            "password": password,
            "full_name": "Live Auth Check",
            "consent_given": True,
        },
    )
    if status == 201:
        reporter.ok("POST /api/v1/auth/register -> 201")
    elif status == 409:
        reporter.ok("POST /api/v1/auth/register -> 409 (the account already exists)")
    else:
        reporter.fail(f"POST /api/v1/auth/register -> {status}: {body[:200]}")
        return None, False

    token = parse_json(body).get("access_token")
    if not isinstance(token, str) or not token:
        reporter.info(
            "the registration answer carried no access token (expected on 409)"
        )
        return None, status == 409
    return token, status == 409


def check_login(
    client: Client,
    reporter: Reporter,
    email: str,
    password: str,
    account_existed: bool = False,
) -> tuple[Optional[str], Optional[str]]:
    """Log in and return (access token, refresh token)."""
    reporter.step("Log in and receive a JWT")
    status, body, _raw = client.request(
        "POST",
        "/api/v1/auth/login",
        body={"email": email, "password": password},
    )
    if status != 200:
        detail = f"POST /api/v1/auth/login -> {status}: {body[:200]}"
        if status == 401 and account_existed:
            detail += (
                " - the account already existed, so the password in the environment "
                "does not belong to it"
            )
        reporter.fail(detail)
        return None, None
    payload = parse_json(body)
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if not isinstance(access_token, str) or not access_token:
        reporter.fail("the login answer carried no access token")
        return None, None
    if not isinstance(refresh_token, str) or not refresh_token:
        reporter.fail("the login answer carried no refresh token")
        return access_token, None
    reporter.ok(
        f"POST /api/v1/auth/login -> 200, token_type={payload.get('token_type', '?')}"
    )
    return access_token, refresh_token


def check_authenticated_call(
    client: Client,
    reporter: Reporter,
    access_token: str,
) -> None:
    """An account route must answer 200 when the token is presented."""
    reporter.step("Call an authenticated endpoint with the token")
    status, body, _raw = client.request(
        "GET",
        "/api/v1/favorites",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if status == 200:
        reporter.ok("GET /api/v1/favorites with the bearer token -> 200")
    else:
        reporter.fail(
            f"GET /api/v1/favorites with the bearer token -> {status}: {body[:200]}"
        )

    status, body, _raw = client.request(
        "GET",
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if status == 200:
        reporter.ok("GET /api/v1/auth/me with the bearer token -> 200")
    else:
        reporter.fail(
            f"GET /api/v1/auth/me with the bearer token -> {status}: {body[:200]}"
        )


def check_refresh(
    client: Client,
    reporter: Reporter,
    refresh_token: str,
) -> tuple[Optional[str], Optional[str]]:
    """Exchange the refresh token and return (new access token, new refresh token)."""
    reporter.step("Refresh the token")
    status, body, _raw = client.request(
        "POST",
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={refresh_token}"},
    )
    if status != 200:
        reporter.fail(f"POST /api/v1/auth/refresh -> {status}: {body[:200]}")
        return None, None
    payload = parse_json(body)
    new_access = payload.get("access_token")
    new_refresh = payload.get("refresh_token")
    if not isinstance(new_access, str) or not new_access:
        reporter.fail("the refresh answer carried no access token")
        return None, None
    reporter.ok("POST /api/v1/auth/refresh -> 200, a new access token was issued")
    if isinstance(new_refresh, str) and new_refresh:
        reporter.ok("the refresh token was rotated")
    else:
        reporter.fail("the refresh answer carried no new refresh token")
    return new_access, new_refresh if isinstance(new_refresh, str) else None


def check_revoked_refresh(
    client: Client,
    reporter: Reporter,
    refresh_token: str,
    label: str,
) -> None:
    """A revoked refresh token must be refused."""
    status, body, _raw = client.request(
        "POST",
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={refresh_token}"},
    )
    if status == 401:
        reporter.ok(f"{label} is refused -> 401")
    else:
        reporter.fail(f"{label} is NOT refused -> {status}: {body[:200]}")


def check_logout(client: Client, reporter: Reporter, refresh_token: str) -> None:
    """Log out."""
    reporter.step("Log out")
    status, body, _raw = client.request(
        "POST",
        "/api/v1/auth/logout",
        headers={"Cookie": f"refresh_token={refresh_token}"},
    )
    if status == 200:
        reporter.ok("POST /api/v1/auth/logout -> 200")
    else:
        reporter.fail(f"POST /api/v1/auth/logout -> {status}: {body[:200]}")


def check_stale_access_token(
    client: Client,
    reporter: Reporter,
    access_token: str,
) -> None:
    """Report what the deployment does with an access token after the logout.

    The access token is a stateless JWT: the deployment can revoke the
    refresh token, but it carries no revocation list for the access token.
    This step therefore REPORTS the answer instead of demanding one - the
    behaviour is the design, and a change in it would be a product decision.
    """
    reporter.step("The access token after the logout")
    status, _body, _raw = client.request(
        "GET",
        "/api/v1/favorites",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if status == 401:
        reporter.ok("the access token is refused -> 401")
    else:
        reporter.info(
            f"the access token still answers -> {status} "
            "(a stateless JWT is not revoked by the logout; the refresh token is)"
        )


def main() -> int:
    base_url = os.environ.get(BASE_URL_ENV, "").strip()
    email = os.environ.get(EMAIL_ENV, "").strip()
    password = os.environ.get(PASSWORD_ENV, "")

    missing = []
    if not base_url:
        missing.append(BASE_URL_ENV)
    if not email:
        missing.append(EMAIL_ENV)
    if not password:
        missing.append(PASSWORD_ENV)

    reporter = Reporter()
    print("Live authentication flow check")
    print(f"base url: {base_url or '(not set)'}")
    if email:
        print(f"test account: {mask_email(email)}")

    if missing:
        print("\nThe environment does not carry what this run needs:")
        for name in missing:
            print(f"  missing environment variable: {name}")
        print(
            "\nNothing was invented and nothing was sent. Set the variables above and run again."
        )
        return EXIT_MISSING_ENV

    client = Client(base_url)
    reporter.info(f"the API is reached at {client.url('/api/v1')}")

    # The steps that need no credentials run first: they answer whether the
    # deployment is up at all.
    try:
        check_public_surface(client, reporter)
        check_account_surface(client, reporter)
        check_oauth_entry_point(client, reporter)
    except StepError as error:
        reporter.fail(str(error))
        print("\nVERDICT: FAIL - the deployment could not be reached")
        return EXIT_FAILED

    try:
        register_token, account_existed = check_register(
            client, reporter, email, password
        )
        access_token, refresh_token = check_login(
            client, reporter, email, password, account_existed
        )

        if access_token and refresh_token:
            check_authenticated_call(client, reporter, access_token)

            new_access, new_refresh = check_refresh(client, reporter, refresh_token)

            if new_refresh:
                check_revoked_refresh(
                    client,
                    reporter,
                    refresh_token,
                    "the refresh token before the rotation",
                )
                live_refresh = new_refresh
                stale_access = new_access
            else:
                # The rotation did not happen, so the refresh token of the
                # login is still the live one. It is logged out below.
                reporter.info(
                    "the rotation did not happen, so the refresh token of the login is still the live one"
                )
                live_refresh = refresh_token
                stale_access = access_token

            check_logout(client, reporter, live_refresh)
            check_revoked_refresh(
                client, reporter, live_refresh, "the refresh token of the live session"
            )
            if stale_access:
                check_stale_access_token(client, reporter, stale_access)
        else:
            reporter.skip("the authenticated steps (no token was issued)")
    except StepError as error:
        reporter.fail(str(error))

    print("\n--- summary ---")
    print(f"passed: {reporter.passed}")
    print(f"failed: {reporter.failed}")
    print(f"skipped: {reporter.skipped}")
    if reporter.failed:
        print("\nVERDICT: FAIL")
        return EXIT_FAILED
    print("\nVERDICT: PASS")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
