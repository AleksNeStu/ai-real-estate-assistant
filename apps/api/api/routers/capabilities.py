"""
Deployment capabilities.

The interface must not promise what the deployment cannot do. The sign-in page
has to know whether an OAuth provider is configured before it renders the
button, and the footer has to know whether e-mail is actually sent before it
promises a subscription. Both answers live in the backend, so they are
published here instead of being guessed in the browser.

The enablement rules below mirror the ones the OAuth endpoints themselves
apply (`api/routers/auth_jwt.py`), so a capability never disagrees with the
endpoint it describes.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_user_optional
from config.settings import get_settings
from db.database import get_db
from services.build_info import build_metadata, is_privileged
from utils.free_tier import client_ip

router = APIRouter(tags=["Capabilities"])


async def _signed_in_email(request: Request, session: AsyncSession) -> Optional[str]:
    """The signed-in account's address, if there is one - and never an error.

    This endpoint is public and the landing page asks it on every visit, so a
    stale cookie must not turn it into a 401 and take the page's lead capture
    down with it. An unusable token means "nobody is signed in" here rather
    than a failure.
    """
    scheme, _, token = (request.headers.get("authorization") or "").partition(" ")
    credentials = (
        HTTPAuthorizationCredentials(scheme=scheme, credentials=token) if scheme and token else None
    )
    try:
        user = await get_current_user_optional(
            request=request,
            access_token=request.cookies.get("access_token"),
            credentials=credentials,
            session=session,
        )
    except HTTPException:
        return None
    return user.email if user else None


def build_capabilities(
    *, email_enabled: bool, build: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Describe what this deployment can actually do."""
    settings = get_settings()

    google = bool(
        settings.auth_oauth_google_enabled
        and settings.google_client_id
        and settings.google_client_secret
    )
    apple = bool(
        settings.auth_oauth_apple_enabled and settings.apple_client_id and settings.apple_team_id
    )

    capabilities = {
        "auth": {
            "jwt_enabled": settings.auth_jwt_enabled,
            # True means an anonymous visitor gets a synthetic user, so the
            # account routes work without signing in. False means they do not,
            # and the interface has to ask for an account instead.
            "demo_user_bypass": settings.demo_user_bypass,
            "oauth": {"google": google, "apple": apple},
        },
        "email": {
            # False means a dummy service is in place: nothing is ever sent.
            "enabled": email_enabled,
            "provider": "smtp" if email_enabled else "dummy",
        },
        "llm": {
            "demo_mode": settings.demo_mode,
            # "local-model" means the canned answers; "provider" means a real
            # model answers and the interface may say so.
            "mode": "local-model" if settings.demo_llm_mode else "provider",
            "provider": settings.default_provider,
            "model": settings.default_model,
        },
        "lead_capture": {
            # The waitlist may only promise an e-mail when one can be sent.
            "waitlist_enabled": email_enabled,
        },
        "observability": {
            "error_tracking": bool(settings.sentry_dsn),
        },
    }
    # The build metadata is only ever published to a privileged caller. For
    # everybody else the key is absent, so the interface has nothing to show
    # and nothing to hide.
    if build:
        capabilities["build"] = build
    return capabilities


@router.get(
    "/capabilities",
    summary="What this deployment can actually do",
    description=(
        "Reports the enabled authentication providers, whether e-mail is really "
        "sent, and whether error tracking is configured. The frontend uses it "
        "to hide features the deployment cannot serve. A caller on the "
        "deployment's privileged list also gets the build it is talking to."
    ),
)
async def capabilities(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    email_enabled = bool(getattr(request.app.state, "email_enabled", False))

    email = await _signed_in_email(request, session)
    privileged = is_privileged(email=email, ip=client_ip(request))
    build = build_metadata() if privileged else None

    return build_capabilities(email_enabled=email_enabled, build=build)
