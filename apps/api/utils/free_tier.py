"""
Free tier rate limiting and LLM cascade for unauthenticated/demo users.

Provides hourly/daily request limits and cascades through the providers the
deployment can afford, in the order the cascade is configured:
MiniMax → Ollama (local, on our own VPS) → OpenRouter free models.

The cascade is walked twice: once to find the providers whose client can be
built, and once more, at call time, to find the one that can actually
answer. A provider that builds and then fails — depleted credits, a rate
limit, an outage — must not end the request; the next provider takes over.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any, Optional, Sequence, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field
from starlette.requests import Request

from config.settings import get_settings

logger = logging.getLogger(__name__)

# How many checks pass between two sweeps of the dead buckets.
SWEEP_EVERY_CHECKS = 100

# How long a provider that could not be built stays out of the cascade.
PROVIDER_UNAVAILABLE_TTL_SECONDS = 300


class FreeTierRateLimiter:
    """In-memory rate limiter with hourly and daily windows, keyed by client IP."""

    def __init__(self, hourly_limit: int = 20, daily_limit: int = 200) -> None:
        self.hourly_limit = hourly_limit
        self.daily_limit = daily_limit
        self._hourly: dict[str, list[float]] = defaultdict(list)
        self._daily: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._checks_since_sweep = 0

    async def check(self, key: str) -> tuple[bool, Optional[str], int]:
        """Check if request is allowed.

        Returns (allowed, reason_if_blocked, retry_after_seconds).
        """
        now = time.monotonic()

        async with self._lock:
            hour_cutoff = now - 3600
            day_cutoff = now - 86400

            self._hourly[key] = [t for t in self._hourly[key] if t > hour_cutoff]
            self._daily[key] = [t for t in self._daily[key] if t > day_cutoff]

            if len(self._daily[key]) >= self.daily_limit:
                oldest = self._daily[key][0]
                retry_after = int(oldest + 86400 - now) + 1
                return False, "Daily limit exceeded", max(retry_after, 1)

            if len(self._hourly[key]) >= self.hourly_limit:
                oldest = self._hourly[key][0]
                retry_after = int(oldest + 3600 - now) + 1
                return False, "Hourly limit exceeded", max(retry_after, 1)

            self._hourly[key].append(now)
            self._daily[key].append(now)

            self._checks_since_sweep += 1
            if self._checks_since_sweep >= SWEEP_EVERY_CHECKS:
                self._sweep(now)
                self._checks_since_sweep = 0

            return True, None, 0

    def _sweep(self, now: float) -> None:
        """Drop the buckets that no live request belongs to.

        The limiter is keyed by address, and the addresses of a public demo
        are not a fixed set — every visitor brings a new one. A bucket whose
        last request is older than a day is dead weight, so it goes; without
        the sweep the dictionary grows with every address the demo has ever
        seen.
        """
        cutoff = now - 86400
        stale = [key for key, times in self._daily.items() if not times or times[-1] <= cutoff]
        for key in stale:
            self._daily.pop(key, None)
            self._hourly.pop(key, None)

    def get_usage(self, key: str) -> dict[str, int]:
        """Return current usage counts for a key."""
        now = time.monotonic()
        hourly = len([t for t in self._hourly.get(key, []) if t > now - 3600])
        daily = len([t for t in self._daily.get(key, []) if t > now - 86400])
        return {"hourly_used": hourly, "daily_used": daily}

    def reset(self) -> None:
        self._hourly.clear()
        self._daily.clear()


# Module-level singleton
_rate_limiter: Optional[FreeTierRateLimiter] = None


def get_free_tier_rate_limiter() -> FreeTierRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        settings = get_settings()
        _rate_limiter = FreeTierRateLimiter(
            hourly_limit=settings.free_tier_hourly_limit,
            daily_limit=settings.free_tier_daily_limit,
        )
    return _rate_limiter


def client_ip(request: Request) -> str:
    """The address of the caller, as the edge knows it.

    A deployment behind a reverse proxy or a Cloudflare Worker sees the
    edge's address on the socket, not the visitor's. The header the edge sets
    carries the real address, and it is the header the limit is counted
    against — otherwise every visitor of the public demo shares one bucket.

    The order is the order of trust: the conventional proxy header first, then
    the edge's own header, then the socket as the last resort.
    """
    for header in ("x-forwarded-for", "cf-connecting-ip", "x-real-ip"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _try_create_minimax() -> Optional[BaseChatModel]:
    """Try to create an LLM using MiniMax.

    MiniMax is the demo's primary: the key is already provisioned and paid
    for, so the demo does not depend on somebody else's free tier.
    """
    settings = get_settings()
    if not settings.minimax_api_key:
        return None

    try:
        from models.provider_factory import ModelProviderFactory

        provider = ModelProviderFactory.get_provider("minimax")
        model_id = settings.minimax_default_model
        return provider.create_model(model_id=model_id, temperature=0.0, max_tokens=2048)
    except Exception:
        return None


def _try_create_openrouter_free() -> Optional[BaseChatModel]:
    """Try to create an LLM using OpenRouter's free models."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        return None

    try:
        from models.provider_factory import ModelProviderFactory

        provider = ModelProviderFactory.get_provider("openrouter")
        free_ids = cast(list[str], getattr(provider, "get_free_model_ids", lambda: [])())
        model_id = settings.free_tier_default_model
        if model_id not in free_ids and free_ids:
            model_id = free_ids[0]
        if not model_id:
            return None
        return provider.create_model(model_id=model_id, temperature=0.0, max_tokens=2048)
    except Exception:
        return None


def _try_create_google_flash() -> Optional[BaseChatModel]:
    """Try to create an LLM using Google Gemini Flash (has free tier).

    The model must be one Google still serves. gemini-2.0-flash was retired on
    2026-06-01, and the provider does not check the id it is handed - it builds
    the client and lets the request fail with a 404. So the cascade picked a
    model that cannot answer, and the fallback that was supposed to carry the
    free tier carried nothing. The provider's own current GA model is the one
    named here, the same one its connection check uses.
    """
    settings = get_settings()
    if not settings.google_api_key:
        return None

    try:
        from models.provider_factory import ModelProviderFactory

        provider = ModelProviderFactory.get_provider("google")
        return provider.create_model(model_id="gemini-3.8-flash", temperature=0.0, max_tokens=2048)
    except Exception:
        return None


def _try_create_ollama() -> Optional[BaseChatModel]:
    """Try to create an LLM using local Ollama."""
    settings = get_settings()
    if not getattr(settings, "ollama_default_model", None):
        return None

    try:
        from models.provider_factory import ModelProviderFactory

        provider = ModelProviderFactory.get_provider("ollama")
        ok, _ = provider.validate_connection()
        if not ok:
            return None
        return provider.create_model(
            model_id=settings.ollama_default_model, temperature=0.0, max_tokens=2048
        )
    except Exception:
        return None


_PROVIDERS_BY_NAME = {
    "minimax": _try_create_minimax,
    "ollama": _try_create_ollama,
    "openrouter": _try_create_openrouter_free,
    "google": _try_create_google_flash,
}


class FreeTierProvidersUnavailable(RuntimeError):
    """Every provider of the free cascade failed to answer.

    The message names the providers and nothing else: the visitor gets the
    names, the raw provider error stays in the server log. A visitor who
    cannot get an answer has no use for a stack trace.
    """

    def __init__(self, failures: Sequence[tuple[str, str]]) -> None:
        self.failures = list(failures)
        names = ", ".join(name for name, _ in self.failures) or "none"
        super().__init__(f"no free LLM provider could answer ({names})")


class CascadingFreeTierModel(BaseChatModel):
    """The free cascade, walked at call time.

    The cascade used to end at the first provider whose client could be
    *built*. A provider that builds and then fails — depleted prepaid
    credits, a rate limit, an outage — ended the request instead of the
    next provider taking over: a provider that is registered but cannot
    answer was a fallback that never fell back.

    This model tries the providers in order and moves on when one fails.
    It reports the providers that failed only when every one of them has
    failed, and then it names them rather than passing a provider's raw
    error to the visitor.
    """

    providers: list[tuple[str, Any]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "cascading-free-tier"

    @property
    def model_name(self) -> str:
        """The name of the first provider — the context manager sizes the
        history against a model, and the first provider is the one that
        normally answers."""
        for _, model in self.providers:
            name = getattr(model, "model_name", None) or getattr(model, "model", None)
            if name:
                return str(name)
        return "gpt-4o-mini"

    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Bind the tools on every provider that can carry them.

        A provider that cannot bind tools is dropped from the cascade
        rather than breaking it: the fallback exists to answer, and a
        provider that cannot answer with tools is not one of them.
        """
        bound: list[tuple[str, Any]] = []
        for name, model in self.providers:
            try:
                bound.append((name, model.bind_tools(tools, tool_choice=tool_choice, **kwargs)))
            except Exception as exc:  # noqa: BLE001 - a provider that cannot bind is skipped
                logger.warning("Free tier provider %s cannot bind tools: %s", name, exc)
        if not bound:
            return self
        return CascadingFreeTierModel(providers=bound)

    def _failed(self, name: str, exc: Exception) -> tuple[str, str]:
        logger.warning("Free tier provider %s failed: %s: %s", name, type(exc).__name__, exc)
        return (name, type(exc).__name__)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        failures: list[tuple[str, str]] = []
        for name, model in self.providers:
            try:
                message = model.invoke(messages, stop=stop, **kwargs)
            except Exception as exc:  # noqa: BLE001 - the cascade is the point
                failures.append(self._failed(name, exc))
                continue
            return ChatResult(generations=[ChatGeneration(message=message)])
        raise FreeTierProvidersUnavailable(failures)

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        failures: list[tuple[str, str]] = []
        for name, model in self.providers:
            try:
                message = await model.ainvoke(messages, stop=stop, **kwargs)
            except Exception as exc:  # noqa: BLE001 - the cascade is the point
                failures.append(self._failed(name, exc))
                continue
            return ChatResult(generations=[ChatGeneration(message=message)])
        raise FreeTierProvidersUnavailable(failures)


# The built clients, per provider. The factory is stored next to the client
# so a patched or replaced factory (a test, a configuration change) is never
# served a client built by the old one.
_BUILT_CLIENTS: dict[str, tuple[Any, BaseChatModel]] = {}

# The providers whose client could not be built, and until when they stay
# out of the cascade.
_UNAVAILABLE_UNTIL: dict[str, tuple[Any, float]] = {}


def reset_free_tier_provider_cache() -> None:
    """Forget the built clients (a configuration change, a test)."""
    _BUILT_CLIENTS.clear()
    _UNAVAILABLE_UNTIL.clear()


def _build_provider(provider_name: str) -> Optional[BaseChatModel]:
    """The client of one provider, built once and remembered."""
    factory = _PROVIDERS_BY_NAME.get(provider_name)
    if factory is None:
        return None

    built = _BUILT_CLIENTS.get(provider_name)
    if built is not None and built[0] is factory:
        return built[1]

    unavailable = _UNAVAILABLE_UNTIL.get(provider_name)
    if unavailable is not None and unavailable[0] is factory and time.monotonic() < unavailable[1]:
        return None

    try:
        client = factory()
    except Exception as exc:  # noqa: BLE001 - a provider that cannot build is skipped
        logger.warning("Free tier provider %s could not be built: %s", provider_name, exc)
        client = None

    if client is None:
        _UNAVAILABLE_UNTIL[provider_name] = (
            factory,
            time.monotonic() + PROVIDER_UNAVAILABLE_TTL_SECONDS,
        )
        return None

    _BUILT_CLIENTS[provider_name] = (factory, client)
    return client


def get_llm_for_free_user() -> Optional[BaseChatModel]:
    """Cascade through free LLM providers in configured order.

    Returns a model that tries the providers in order at call time and
    moves on when one fails, or None if no provider can be built at all.
    """
    settings = get_settings()
    if settings.demo_llm_mode:
        # A demo deployment must never reach a paid provider: the mock answers
        # every request, so a visitor cannot spend the operator's keys.
        from core.demo import get_demo_llm

        return get_demo_llm()

    if not settings.free_tier_enabled:
        return None

    cascade = settings.free_tier_provider_cascade
    if not cascade:
        # Every provider that can answer is in this list. The order is the
        # order they are tried in, and a provider that fails at call time
        # hands the request over to the next one.
        cascade = ["minimax", "ollama", "openrouter", "google"]

    providers: list[tuple[str, BaseChatModel]] = []
    for provider_name in cascade:
        client = _build_provider(provider_name)
        if client is not None:
            providers.append((provider_name, client))

    if not providers:
        return None

    return CascadingFreeTierModel(providers=providers)
