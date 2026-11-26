# Live authentication flow verification — 2026-11-25

TaskMaster #138 — "the login flow is verified against the running deployment".

> **Update — 2026-11-26.** The flow was walked again against the released build
> (`5.7.0`) and **passed every step**: `VERDICT: PASS`, 14 passed, 0 failed.
> See "The re-run on the released build" below. The run this file originally
> records failed on one step, and the failure is kept here with its cause.

## What was checked

The authentication flow was walked end to end against the **running public demo**
(`https://realty.kittray.com`), not against a local stack, with a throwaway test
account. The check was carried out by

`scripts/ops/verify_live_auth_flow.py`

which reads every input from the environment and prints one `PASS` / `FAIL` line
per step. Nothing is read from `argv`, and no credential, password or token is
printed or written anywhere.

Reproduce with:

```bash
export AIRE_BASE_URL="https://realty.kittray.com"
export AIRE_TEST_EMAIL="<a neutral test alias>"
export AIRE_TEST_PASSWORD="<the password of that test account>"
python scripts/ops/verify_live_auth_flow.py
```

The script exits `0` when every step that ran passed, `1` when a step failed and
`2` when the environment does not carry what the run needs — in which case it
names the missing variable and sends nothing. Nothing is ever invented.

The test account is a neutral alias on the shared tester mailbox
(`auto.tester.py+<alias>@gmail.com`). No project address, no brand and no
personal mailbox was used. The deployment re-seeds (and drops the test users)
on its next start.

## The deployment that answered

| | |
|---|---|
| Address | `https://realty.kittray.com` |
| Backend image | `ghcr.io/aleksnestu/ai-real-estate-assistant/backend:5.6.0` |
| Build SHA | `da08881ef92d037539449b98b7ce1aed0cb1291f` |
| Built at | `2026-11-24T00:25:59Z` |
| Deploy run | `45297018441` |
| `ENVIRONMENT` | `staging` (the CSRF middleware only enforces in `production`) |
| `SEED_ON_STARTUP` | `true` (the demo drops and re-creates its users on a start) |

## The result

**VERDICT: FAIL** — 11 steps passed, 1 failed.

```
=== Public routes answer without a login
PASS  GET /api/v1/capabilities -> 200
PASS  GET /api/v1/properties -> 200

=== Account routes answer 401 without a token
PASS  GET /api/v1/favorites -> 401
PASS  GET /api/v1/saved-searches -> 401

=== Google OAuth is offered as an entry point
PASS  the authorize endpoint is accounts.google.com (the flow was not followed)

=== Register the test account
PASS  POST /api/v1/auth/register -> 201

=== Log in and receive a JWT
PASS  POST /api/v1/auth/login -> 200, token_type=bearer

=== Call an authenticated endpoint with the token
PASS  GET /api/v1/favorites with the bearer token -> 200
PASS  GET /api/v1/auth/me with the bearer token -> 200

=== Refresh the token
FAIL  POST /api/v1/auth/refresh -> 500: {"detail":"TypeError: can't compare offset-naive and offset-aware datetimes", ...}
INFO  the rotation did not happen, so the refresh token of the login is still the live one

=== Log out
PASS  POST /api/v1/auth/logout -> 200
PASS  the refresh token of the live session is refused -> 401

=== The access token after the logout
INFO  the access token still answers -> 200 (a stateless JWT is not revoked by the logout; the refresh token is)
```

### Step by step

| Step | Result | Note |
|---|---|---|
| `GET /api/v1/capabilities` without a login | PASS | 200 — the public surface needs no credential |
| `GET /api/v1/properties` without a login | PASS | 200 |
| `GET /api/v1/favorites` without a token | PASS | 401 — the account surface is closed |
| `GET /api/v1/saved-searches` without a token | PASS | 401 |
| `GET /api/v1/auth/oauth/google` | PASS | 200 and the authorize endpoint is `accounts.google.com`. **Entry point only**: the URL was read, not followed. No Google sign-in was attempted and no Google account was touched. |
| `POST /api/v1/auth/register` | PASS | 201, the test account was created |
| `POST /api/v1/auth/login` | PASS | 200, a bearer JWT was issued |
| `GET /api/v1/favorites` with the JWT | PASS | 200 |
| `GET /api/v1/auth/me` with the JWT | PASS | 200 |
| `POST /api/v1/auth/refresh` | **FAIL** | 500 — see below |
| `POST /api/v1/auth/logout` | PASS | 200 |
| the refresh token after the logout | PASS | 401 — the session is closed |
| the access token after the logout | INFO | 200 — a stateless JWT carries no revocation list, so the logout revokes the refresh token and not the access token. This is the design, not a defect; the script reports it instead of demanding a 401. |

## The finding: the refresh endpoint answers 500

`POST /api/v1/auth/refresh` fails on the deployment with

```
TypeError: can't compare offset-naive and offset-aware datetimes
```

**Cause** — `apps/api/db/models.py:124`, `RefreshToken.is_expired`:

```python
return datetime.now(UTC) >= self.expires_at
```

`expires_at` is written as an aware datetime and stored in SQLite, which keeps
no time zone, so it comes back **naive**; `datetime.now(UTC)` is **aware**. The
comparison raises, the request dies with a 500, and `stored_token.is_valid` can
never be evaluated.

**What it breaks** — the rotation never happens: no new access token is issued,
the old refresh token is never revoked, and a signed-in visitor cannot renew
their session. The access token simply expires and the visitor has to sign in
again. The same comparison shape sits in `PasswordResetToken.is_expired` and
`EmailVerificationToken.is_expired` (`apps/api/db/models.py:188` and
`apps/api/db/models.py:226`), so the password-reset and email-verification
paths carry the same defect; they were not exercised in this run.

This is a defect in the product's code, not in the deployment. **It is fixed**
— see "The fix" below.

## The fix

`apps/api/db/models.py` now reads a stored expiry through one helper:

```python
def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return datetime.now(UTC) >= expires_at
```

The value was written as UTC, so a value that comes back without a zone is
read as UTC; Postgres keeps the zone and is unaffected. The three
`is_expired` properties — `RefreshToken`, `PasswordResetToken`,
`EmailVerificationToken` — all go through it, so the password-reset and the
email-verification paths carry the fix too.

The proof that it is the same defect and the same fix:
`apps/api/tests/unit/test_token_expiry_timezone.py` writes a token through
the repository into SQLite, drops the session's copy, reads it back the way
the endpoint reads it, and asserts that the value arrives **without** a zone
and is still valid. Before the fix that assertion raised `TypeError`; after it
the token is valid and the rotation runs.

## The incident during the first run

The first attempt at the flow did not complete, and the reason is worth
recording:

* `POST /api/v1/auth/register` answered **201** (241 ms).
* The `POST /api/v1/auth/login` that followed never answered. The curl wait
  ended in a Cloudflare **524** after 125 s, and a second registration attempt
  answered **524** as well.
* The backend container turned **unhealthy**; its own health check timed out
  (`Health check exceeded timeout (10s)`), and it stopped answering every
  request — including `GET /health` from inside the container.
* The process was alive with **0 % CPU** and no thread blocked on a file lock,
  so it was waiting, not spinning. The last thing it logged was the successful
  registration.

**Recovery** — the backend container was restarted (`docker restart
aire-demo-backend`). It came back on the **same** image (`5.6.0`) and the
deployment answered again (`GET /api/v1/capabilities -> 200`).

**Why the restart was a restart and not a recreate** — the server's own
`AIRE_IMAGE_TAG` still pins `5.5.0` while the running image is `5.6.0`, so any
`docker compose up -d` (a recreate) would have rolled the demo **back** to the
older image. `docker restart` reuses the running container and its image. The
pin has to be corrected by the release chain, otherwise the next recreate of
this deployment rolls it back.

**Not reproduced.** After the restart the flow was run twice more (once with a
fresh alias, once against the account that already existed) and the backend
answered every request. The hang did not come back, so its cause is still
**unknown** — it is recorded here as an observation, not as a diagnosed defect.

## The re-run on the released build — 2026-11-26

The same script, the same command and the same neutral test alias were run
again against the deployment that carries the fix (`5.7.0`, the build that
followed the release of this repository's `v5.7.0` tag).

| | |
|---|---|
| Address | `https://realty.kittray.com` |
| Backend image | `ghcr.io/aleksnestu/ai-real-estate-assistant/backend:5.7.0` |
| Build SHA | `0ead8e51855448ed18555cefb042b9c505c72cbd` |
| Built at | `26.11.2026 01:31` |
| Deploy run | `45736259715` |
| `ENVIRONMENT` | `staging` (the CSRF middleware only enforces in `production`) |

```
=== Public routes answer without a login
PASS  GET /api/v1/capabilities -> 200
PASS  GET /api/v1/properties -> 200

=== Account routes answer 401 without a token
PASS  GET /api/v1/favorites -> 401
PASS  GET /api/v1/saved-searches -> 401

=== Google OAuth is offered as an entry point
PASS  the authorize endpoint is accounts.google.com (the flow was not followed)

=== Register the test account
PASS  POST /api/v1/auth/register -> 201

=== Log in and receive a JWT
PASS  POST /api/v1/auth/login -> 200, token_type=bearer

=== Call an authenticated endpoint with the token
PASS  GET /api/v1/favorites with the bearer token -> 200
PASS  GET /api/v1/auth/me with the bearer token -> 200

=== Refresh the token
PASS  POST /api/v1/auth/refresh -> 200, a new access token was issued
PASS  the refresh token was rotated
PASS  the refresh token before the rotation is refused -> 401

=== Log out
PASS  POST /api/v1/auth/logout -> 200
PASS  the refresh token of the live session is refused -> 401

=== The access token after the logout
INFO  the access token still answers -> 200 (a stateless JWT is not revoked by the logout; the refresh token is)

--- summary ---
passed: 14
failed: 0
skipped: 0

VERDICT: PASS
```

**VERDICT: PASS** — 14 steps passed, 0 failed, and the script exited `0`.

The step that failed on 2026-11-25 now passes in full: the refresh answers
`200`, issues a new access token, **rotates** the refresh token, and the old
refresh token is refused with a `401`. The rotation is the part that was broken
— before the fix the endpoint raised, so nothing was rotated and no new access
token was issued.

The `INFO` line about the access token after the logout is the design, not a
defect: a stateless JWT carries no revocation list, so the logout revokes the
refresh token and not the access token that was already issued. The script
reports it instead of demanding a `401`.

The credentials of the test account live in the **OS User environment**
(`AIRE_TEST_EMAIL`, `AIRE_TEST_PASSWORD`), never in this file, never in a
command line and never in the repository.

## Notes

* The API-key sanity check is covered by the first two blocks: the public
  routes answer through the frontend's proxy with **no** credential of any kind
  supplied by the client, and the account routes answer **401** without a token.
  The browser never holds the API key — the proxy injects it.
* The CSRF double-submit is not exercised here: the deployment runs with
  `ENVIRONMENT=staging` and the middleware only enforces in `production`.
* No secret, token, password or real person's address appears in this file.
