"""A rotated provider key is picked up without a restart (Task #155).

The provider-instance cache and the chat-model cache key on the FINGERPRINT
of the key the provider carries, not only on the provider name. A key
written into the environment after the process started has to reach the next
request - without a restart and without a manual cache clear.

Keys are compared by fingerprint and never by value, so a failing assertion
can never print one.
"""

import hashlib
import os

import pytest

from api import dependencies
from config.settings import settings
from models.provider_factory import ModelProviderFactory

_FIRST_KEY = "rotated-key-one"
_SECOND_KEY = "rotated-key-two"


def _fingerprint(api_key) -> str:
    """A short, non-reversible fingerprint of a key.

    The oracle is written here, not taken from the implementation: the test
    asks whether the provider carries the new key, and two keys are compared
    by their fingerprints so a failure can never print one.
    """
    if not api_key:
        return ""
    return hashlib.sha256(str(api_key).encode("utf-8")).hexdigest()[:16]


def _model_key_fingerprint(llm) -> str:
    """The fingerprint of the key a chat model carries."""
    for attribute in ("openai_api_key", "api_key"):
        raw = getattr(llm, attribute, None)
        if raw is None:
            continue
        value = raw.get_secret_value() if hasattr(raw, "get_secret_value") else str(raw)
        return _fingerprint(value)
    return ""


@pytest.fixture(autouse=True)
def _clean_caches():
    ModelProviderFactory.clear_cache()
    dependencies.clear_llm_cache()
    yield
    ModelProviderFactory.clear_cache()
    dependencies.clear_llm_cache()


@pytest.fixture(autouse=True)
def _no_demo_llm(monkeypatch):
    """The demo's mock model would answer instead of the provider."""
    monkeypatch.setattr(settings, "demo_llm_mode", False)


def test_a_rotated_key_reaches_the_next_provider(monkeypatch):
    """The provider cache must not answer a rotated key with the old one."""
    monkeypatch.setenv("OPENAI_API_KEY", _FIRST_KEY)

    first = ModelProviderFactory.get_provider("openai")
    assert _fingerprint(first.config.get("api_key")) == _fingerprint(_FIRST_KEY)

    monkeypatch.setenv("OPENAI_API_KEY", _SECOND_KEY)

    second = ModelProviderFactory.get_provider("openai")
    assert second is not first
    assert _fingerprint(second.config.get("api_key")) == _fingerprint(_SECOND_KEY)


def test_an_unchanged_key_still_uses_the_cache(monkeypatch):
    """The cache still answers for a key that did not move."""
    monkeypatch.setenv("OPENAI_API_KEY", _FIRST_KEY)

    first = ModelProviderFactory.get_provider("openai")
    second = ModelProviderFactory.get_provider("openai")

    assert second is first


def test_a_rotated_key_reaches_the_next_model(monkeypatch):
    """The chat-model cache must not answer a rotated key with the old model."""
    monkeypatch.setenv("OPENAI_API_KEY", _FIRST_KEY)

    first, _ = dependencies._create_llm_with_resolved_model_id("openai", "gpt-4o-mini")
    assert _model_key_fingerprint(first) == _fingerprint(_FIRST_KEY)

    monkeypatch.setenv("OPENAI_API_KEY", _SECOND_KEY)

    second, _ = dependencies._create_llm_with_resolved_model_id("openai", "gpt-4o-mini")
    assert second is not first
    assert _model_key_fingerprint(second) == _fingerprint(_SECOND_KEY)


@pytest.mark.asyncio
async def test_the_failover_key_reaches_the_model(monkeypatch):
    """The failover writes a key into the environment; the model must carry
    that one, and the environment must be left as it was."""
    monkeypatch.setenv("OPENAI_API_KEY", _FIRST_KEY)

    llm, _ = await dependencies._create_llm_with_api_key("openai", "gpt-4o-mini", _SECOND_KEY)

    assert _model_key_fingerprint(llm) == _fingerprint(_SECOND_KEY)
    assert os.environ["OPENAI_API_KEY"] == _FIRST_KEY


def test_the_fingerprint_does_not_carry_the_key():
    """A fingerprint says "the same key" without carrying the key."""
    from models.provider_factory import key_fingerprint

    fingerprint = key_fingerprint(_FIRST_KEY)

    assert _FIRST_KEY not in fingerprint
    assert fingerprint == _fingerprint(_FIRST_KEY)
    assert fingerprint != key_fingerprint(_SECOND_KEY)
