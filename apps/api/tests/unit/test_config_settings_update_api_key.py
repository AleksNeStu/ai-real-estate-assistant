import os
from unittest.mock import patch

import pytest

from config.settings import update_api_key

# The settings attributes update_api_key writes into. They are restored after
# the test - see the fixture below.
_SETTINGS_ATTRS = (
    "openai_api_key",
    "anthropic_api_key",
    "google_api_key",
    "grok_api_key",
    "deepseek_api_key",
)


@pytest.fixture(autouse=True)
def _restore_the_settings():
    """Give back the provider keys this test's call took.

    update_api_key writes into the global settings object AND the environment.
    monkeypatch restores the environment at teardown, but the settings object
    keeps the fake key for the rest of the worker process - so a later test in
    the same worker reads "openai-key" where it expects the machine's own
    value, and fails on a value it never set. The pollution is invisible in
    the test that caused it and shows up somewhere else entirely.
    """
    from config.settings import settings

    saved = {attr: getattr(settings, attr, None) for attr in _SETTINGS_ATTRS}
    yield
    for attr, value in saved.items():
        setattr(settings, attr, value)


@patch("models.provider_factory.ModelProviderFactory.clear_cache")
def test_update_api_key_sets_env_and_clears_cache(mock_clear_cache, monkeypatch):
    cases = [
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("google", "GOOGLE_API_KEY"),
        ("grok", "XAI_API_KEY"),
        ("deepseek", "DEEPSEEK_API_KEY"),
    ]
    for provider, env_key in cases:
        monkeypatch.delenv(env_key, raising=False)
        update_api_key(provider, f"{provider}-key")
        assert os.environ[env_key] == f"{provider}-key"

    assert mock_clear_cache.call_count == len(cases)
