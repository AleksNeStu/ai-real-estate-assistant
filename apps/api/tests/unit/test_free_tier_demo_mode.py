"""The free tier must never reach a paid provider on a demo deployment.

A public demo is open to anyone: if the anonymous chat endpoint builds a real
OpenRouter/Google/Ollama client, every visitor spends the operator's keys.
"""

from __future__ import annotations

import pytest

from utils import free_tier


class TestFreeTierDemoMode:
    """`get_llm_for_free_user` honours the demo flag before the cascade."""

    def test_demo_mode_returns_the_mock(self, monkeypatch):
        monkeypatch.setattr(free_tier, "get_settings", lambda: _settings(demo_llm_mode=True))

        llm = free_tier.get_llm_for_free_user()

        assert llm is not None
        assert type(llm).__name__ == "MockLLM"

    def test_demo_mode_never_builds_a_real_provider(self, monkeypatch):
        """The provider factories are not even called in demo mode."""
        calls: list[str] = []

        def _fail(name: str):
            def _boom():
                raise AssertionError(f"demo mode must not build the {name} provider")

            return _boom

        monkeypatch.setattr(free_tier, "get_settings", lambda: _settings(demo_llm_mode=True))
        for name in free_tier._PROVIDERS_BY_NAME:
            monkeypatch.setitem(free_tier._PROVIDERS_BY_NAME, name, _fail(name))

        free_tier.get_llm_for_free_user()

        assert calls == []

    def test_free_tier_disabled_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            free_tier,
            "get_settings",
            lambda: _settings(demo_llm_mode=False, free_tier_enabled=False),
        )

        assert free_tier.get_llm_for_free_user() is None

    def test_a_demo_with_a_real_model_reaches_the_cascade(self, monkeypatch):
        """The split: a demo catalogue may still answer with a real model."""
        built: list[str] = []

        def _fake(name: str):
            def _build():
                built.append(name)
                return None

            return _build

        monkeypatch.setattr(free_tier, "get_settings", lambda: _settings(demo_llm_mode=False))
        for name in free_tier._PROVIDERS_BY_NAME:
            monkeypatch.setitem(free_tier._PROVIDERS_BY_NAME, name, _fake(name))

        free_tier.get_llm_for_free_user()

        assert built == list(free_tier._PROVIDERS_BY_NAME)


class _Settings:
    def __init__(self, demo_llm_mode: bool, free_tier_enabled: bool = True) -> None:
        self.demo_llm_mode = demo_llm_mode
        self.free_tier_enabled = free_tier_enabled
        self.free_tier_provider_cascade: list[str] = []


def _settings(demo_llm_mode: bool, free_tier_enabled: bool = True) -> _Settings:
    return _Settings(demo_llm_mode=demo_llm_mode, free_tier_enabled=free_tier_enabled)


@pytest.mark.parametrize("demo_llm_mode", [True, False])
def test_settings_helper_is_consistent(demo_llm_mode: bool) -> None:
    assert _settings(demo_llm_mode).demo_llm_mode is demo_llm_mode
