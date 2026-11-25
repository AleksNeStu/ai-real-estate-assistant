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

THE INGESTION KEYS DESCRIBE THIS DEPLOYMENT

The formats are the ones this deployment can read - the reader of ``.xls`` and
``.ods`` is an extra - and the register is a source the deployment holds or
does not hold: it is read from the sales the ingest stored, so the answer is
a fact about the running database and not about a list of cities. A page that
reads these keys therefore never offers a file the deployment would refuse.

The register is published as it is known: True when the deployment holds it,
False when it holds none, and None when the deployment could not be asked. A
deployment that holds no register and a deployment that could not be asked
are two different facts, and the endpoint publishes both.

THE DEMO FLAGS ARE PUBLISHED SPLIT

The demo was one flag for four different things: the seeded catalogue, the
canned model, the fake API key and the synthetic user. The settings module
already splits it (`config/settings.py`), and the deployment that runs a real
model with a seeded catalogue is a real one. Publishing the master flag under
``llm`` made that deployment answer "demo mode" while its chat answered with
a live model, so the master flag is not published at all. Each split flag is
published where it means something: the canned model under ``llm``, the seeded
catalogue under ``data``, the synthetic user under ``auth``.
"""

import logging
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_user_optional
from config.settings import get_settings
from db.database import get_db
from services.build_info import build_metadata, is_privileged
from utils.free_tier import client_ip

logger = logging.getLogger(__name__)

# What was said out loud, and when. The endpoint is public and every page
# reads it, so a warning per request would flood the log and a warning once
# per process would hide a database that stays away.
REGISTER_WARNING_SECONDS = 60.0
_warned_at: Optional[float] = None

# How long the answer about the register is kept, and the answer itself.
# The register changes when the ingest runs, which is rare; the endpoint is
# public and every page reads it, so the database is read once a minute
# instead of once per request.
REGISTER_CACHE_SECONDS = 60.0

# How long a failed read is kept. A failure is not an answer: the database
# may be back in a moment, and a deployment that recovered must be seen at
# once. The failure is still kept for a while, so a database that stays away
# is not asked on every request.
REGISTER_FAILURE_CACHE_SECONDS = 5.0

# The answer, when it was given, and how long it is kept.
_register_cache: Optional[tuple[float, Optional[bool], float]] = None


def _now() -> float:
    """The clock the answer is kept by.

    A test may hold it still: the answer is kept for a minute and said out
    loud once a minute, and a test that waits for a real minute is a test
    that waits.
    """
    return time.monotonic()


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


def _ingest_capabilities(*, register: Optional[bool]) -> dict[str, Any]:
    """What this deployment can read into the catalogue.

    The formats are the ones the import chain accepts AND the ones the
    deployment can read: the reader of ``.xls`` and ``.ods`` is an extra, so a
    deployment without it fails at the read. Every other format the chain
    accepts is read by the CSV loader, and pandas reads it without an extra.
    The interface must not offer a file the deployment cannot open.

    The register is a source of its own: it is read from the sales the ingest
    stored, so whether the deployment holds it is a fact about this
    deployment's own database and not a fact about a list of cities. It is
    published as it is known: True when the deployment holds it, False when
    it holds none, and None when the deployment could not be asked.

    A deployment that cannot even name the sources answers that it reads no
    format: the endpoint is public and every page reads it, so a broken
    import must not take the whole answer with it. The register is a fact of
    its own - it was read from the database, not from the formats - so it
    is published even then.
    """
    try:
        from data.excel_loader import EXCEL_ENGINES, reader_installed
        from services.property_import import EXCEL_SUFFIXES, SUPPORTED_SUFFIXES

        def readable(suffix: str) -> bool:
            """True when this deployment can read this format."""
            if suffix in EXCEL_SUFFIXES:
                # A spreadsheet is read by the engine that reads it, and that
                # engine is an extra for everything but .xlsx.
                engine = EXCEL_ENGINES.get(suffix)
                return engine is not None and reader_installed(engine)
            # Every other format the chain accepts is read by the CSV loader
            # - the chain hands it there - and pandas reads it without an
            # extra.
            return True

        formats = sorted(suffix for suffix in SUPPORTED_SUFFIXES if readable(suffix))
        return {
            "formats": formats,
            "excel": any(suffix in EXCEL_SUFFIXES for suffix in formats),
            "register": register,
        }
    except Exception as error:
        # The answer is a capability, not the deployment itself: a source
        # that cannot be named is a source this deployment cannot read, and
        # a public endpoint that every page reads must not answer a 500.
        # The register is a fact of its own - it was read from the database
        # and it does not depend on the formats - so it is published even
        # when the formats could not be named.
        logger.warning(
            "The sources of the catalogue could not be read (%s); the deployment reads no format",
            error,
        )
        return {"formats": [], "excel": False, "register": register}


def _warn_about_the_register(error: Exception) -> None:
    """Say the failure out loud, once a minute.

    The endpoint is public and every page reads it, so a warning per request
    would flood the log; a warning once per process would hide a database
    that stays away.
    """
    global _warned_at
    now = _now()
    if _warned_at is not None and now - _warned_at < REGISTER_WARNING_SECONDS:
        return
    _warned_at = now
    logger.warning(
        "The register could not be read (%s); the answer is the unknown one",
        error,
    )


async def _register_readable(session: AsyncSession) -> Optional[bool]:
    """Whether this deployment holds the official price register.

    True when it holds it - the sales of the cities the site knows are in its
    catalogue - False when it holds none, and None when the deployment could
    not be asked: the read of the register failed.
    The three are different answers: a deployment that holds no register is
    a fact, and a deployment that could not be asked is not the same fact.

    The register is read from the sales the ingest stored, for the cities the
    site knows: a register source names a city, and a source of a city the
    site does not know cannot be read at all. A deployment that stored no
    sale of any of them holds no register, and a sync of the register finds
    no sale until the ingest has run - which is why the source is offered
    whatever the answer is: registering the source is how the register gets
    into the deployment.

    The answer is kept for a minute. The register changes when the ingest
    runs, which is rare, and this endpoint is public and read by every page
    - so the database is read once a minute and not once per request. A read
    that fails answers the unknown one: the deployment could not be asked
    now, and an answer from a moment ago is not an answer about the
    deployment now. A failure is kept for a shorter while than an answer,
    so a database that comes back is seen at once.

    The read is one indexed question that stops at the first row. Every
    worker keeps its own answer, so two workers can differ for up to a
    minute after an ingest - the register changes when the ingest runs, and
    the next answer settles it.
    """
    global _register_cache
    now = _now()
    if _register_cache is not None and now - _register_cache[0] < _register_cache[2]:
        return _register_cache[1]
    try:
        from data.places import PLACES
        from data.rcn.rcn_models import normalize_text
        from db.property_transaction_repo import has_sales_of_cities

        cities = [normalize_text(place.register_city) for place in PLACES if place.register_city]
        readable: Optional[bool] = await has_sales_of_cities(session, cities)
    except Exception as error:
        # A register that could not be read now is a register this deployment
        # has not answered about now. An answer from a moment ago is not an
        # answer about the deployment now - a database that is away says
        # nothing about what the deployment holds. The endpoint is public, so
        # the answer is a capability and never a failure.
        _warn_about_the_register(error)
        # The failed statement left the session's transaction unusable, and
        # the session is committed when the request ends: the transaction is
        # put back in order here, so the request still ends in an answer.
        # The route writes nothing of its own - the audit entry is written
        # after the route - so nothing is lost by the rollback.
        try:
            await session.rollback()
        except Exception:
            logger.warning("The session could not be put back in order after the failed read")
        _register_cache = (_now(), None, REGISTER_FAILURE_CACHE_SECONDS)
        return None
    _register_cache = (_now(), readable, REGISTER_CACHE_SECONDS)
    return readable


def build_capabilities(
    *,
    email_enabled: bool,
    build: Optional[dict[str, Any]] = None,
    register: Optional[bool] = None,
) -> dict[str, Any]:
    """Describe what this deployment can actually do.

    The builder is pure: it reads the settings and the facts it is given.
    The register is one of those facts, because whether the deployment holds
    the register is a question about the database and the database is not
    read here.
    """
    settings = get_settings()

    # The enablement rules below mirror the ones the OAuth endpoints
    # themselves apply, so a capability never disagrees with the endpoint it
    # describes. The Google endpoint needs the redirect URI as well as the
    # credentials - without it the click answers 500 - and the whole
    # auth router only exists when JWT is enabled, so without that the
    # click answers 404. The Apple endpoint reads its private key from a
    # file and reuses the same redirect URI setting.
    #
    # The callback sends the visitor back to the interface only when the
    # frontend URL is one it can redirect to; without one it answers with
    # the tokens as a JSON body. A button that leads to JSON is a dead end,
    # so the browser flow is part of the capability the interface reads.
    frontend_url = getattr(settings, "frontend_url", None)
    browser_flow = isinstance(frontend_url, str) and frontend_url.startswith("http")
    google = bool(
        settings.auth_jwt_enabled
        and settings.auth_oauth_google_enabled
        and settings.google_client_id
        and settings.google_client_secret
        and settings.google_redirect_uri
        and browser_flow
    )
    apple = bool(
        settings.auth_jwt_enabled
        and settings.auth_oauth_apple_enabled
        and settings.apple_client_id
        and settings.apple_team_id
        and settings.apple_private_key_path
        and settings.google_redirect_uri
        and browser_flow
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
            # True means the answers come from the canned local model and not
            # from a provider. The master flag is not published: it is the
            # fallback of the four split flags, and a deployment that set
            # only DEMO_MODE read "demo mode" while a real model answered
            # the chat.
            "demo_llm_mode": settings.demo_llm_mode,
            # "local-model" means the canned answers; "provider" means a real
            # model answers and the interface may say so.
            "mode": "local-model" if settings.demo_llm_mode else "provider",
            "provider": settings.default_provider,
            "model": settings.default_model,
        },
        "data": {
            # True means the catalogue of the deployment is the seeded demo
            # one and not the listings of the register or of an import.
            "demo_data_mode": settings.demo_data_mode,
        },
        "ingest": _ingest_capabilities(register=register),
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
        "sent, and whether error tracking is configured. The demo flags are "
        "published split - the canned model, the seeded catalogue - so a "
        "deployment that answers with a real model never reads as a demo. The "
        "ingestion keys say which file formats the deployment can read and "
        "whether it holds the official register - true when it holds it, "
        "false when it holds none, and null when the deployment could not be "
        "asked. The frontend uses it to hide features the deployment cannot "
        "serve. A caller on the deployment's privileged list also gets the "
        "build it is talking to."
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

    register = await _register_readable(session)

    return build_capabilities(email_enabled=email_enabled, build=build, register=register)
