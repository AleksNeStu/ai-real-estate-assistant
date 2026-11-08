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

from typing import Any

from fastapi import APIRouter, Request

from config.settings import get_settings

router = APIRouter(tags=["Capabilities"])


def build_capabilities(*, email_enabled: bool) -> dict[str, Any]:
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

    return {
        "auth": {
            "jwt_enabled": settings.auth_jwt_enabled,
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


@router.get(
    "/capabilities",
    summary="What this deployment can actually do",
    description=(
        "Reports the enabled authentication providers, whether e-mail is really "
        "sent, and whether error tracking is configured. The frontend uses it "
        "to hide features the deployment cannot serve."
    ),
)
async def capabilities(request: Request) -> dict[str, Any]:
    email_enabled = bool(getattr(request.app.state, "email_enabled", False))
    return build_capabilities(email_enabled=email_enabled)
