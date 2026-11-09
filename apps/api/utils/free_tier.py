"""
Free tier rate limiting and LLM cascade for unauthenticated/demo users.

Provides hourly/daily request limits and cascades through the providers the
deployment can afford, in the order the cascade is configured:
MiniMax → Ollama (local, on our own VPS) → OpenRouter free models.
"""

import asyncio
import time
from collections import defaultdict
from typing import Optional

from langchain_core.language_models import BaseChatModel
from starlette.requests import Request

from config.settings import get_settings


class FreeTierRateLimiter:
    """In-memory rate limiter with hourly and daily windows, keyed by client IP."""

    def __init__(self, hourly_limit: int = 20, daily_limit: int = 200) -> None:
        self.hourly_limit = hourly_limit
        self.daily_limit = daily_limit
        self._hourly: dict[str, list[float]] = defaultdict(list)
        self._daily: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

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
            return True, None, 0

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
        free_ids = provider.get_free_model_ids()
        model_id = settings.free_tier_default_model
        if model_id not in free_ids and free_ids:
            model_id = free_ids[0]
        if not model_id:
            return None
        return provider.create_model(model_id=model_id, temperature=0.0, max_tokens=2048)
    except Exception:
        return None


def _try_create_google_flash() -> Optional[BaseChatModel]:
    """Try to create an LLM using Google Gemini Flash (has free tier)."""
    settings = get_settings()
    if not settings.google_api_key:
        return None

    try:
        from models.provider_factory import ModelProviderFactory

        provider = ModelProviderFactory.get_provider("google")
        return provider.create_model(model_id="gemini-2.0-flash", temperature=0.0, max_tokens=2048)
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


def get_llm_for_free_user() -> Optional[BaseChatModel]:
    """Cascade through free LLM providers in configured order.

    Returns the first successful LLM, or None if all fail.
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
        # Every provider that can answer is in this list. A provider that is
        # registered but unreachable is a fallback that never falls back.
        cascade = ["minimax", "ollama", "openrouter", "google"]

    for provider_name in cascade:
        factory = _PROVIDERS_BY_NAME.get(provider_name)
        if factory is None:
            continue
        llm = factory()
        if llm is not None:
            return llm

    return None
