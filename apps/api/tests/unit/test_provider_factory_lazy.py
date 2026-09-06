"""Tests for the environment-conditional lazy provider loading in
``models.provider_factory``.

The factory loads provider modules eagerly on local dev / CI (no
``RENDER`` env var) and lazily on Render (``RENDER=true``) to stay
under the 512 MB free-tier memory cap.

These tests pin both behaviours so a future refactor doesn't break
either environment. We use ``importlib.reload`` on the factory
module so the module-level ``if not IS_RENDER`` branch is re-evaluated
under the patched env var, without disturbing already-loaded provider
modules in ``sys.modules`` (which would break sibling tests that mock
``models.providers.*``).
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import patch

import pytest


def _reload_factory_with_env(monkeypatch: pytest.MonkeyPatch, render: bool):
    """Reload the factory module with a controlled RENDER env var.

    We only drop ``models.provider_factory`` from ``sys.modules`` and
    reload it; provider submodules are left in place so any sibling
    tests mocking them aren't disturbed.
    """
    sys.modules.pop("models.provider_factory", None)
    if render:
        monkeypatch.setenv("RENDER", "true")
    else:
        monkeypatch.delenv("RENDER", raising=False)
    return importlib.import_module("models.provider_factory")


def test_non_render_eager_loads_all_providers(monkeypatch):
    """Without ``RENDER=true``, every provider module is imported at
    factory load time. ``_PROVIDERS`` is fully populated."""
    factory = _reload_factory_with_env(monkeypatch, render=False)

    # Eager path populates the class registry with all 13 providers.
    assert len(factory._PROVIDERS) == len(factory._PROVIDER_MODULES)
    for slug, module_path in factory._PROVIDER_MODULES.items():
        assert slug in factory._PROVIDERS, (
            f"Expected {slug} to be eagerly loaded in non-Render mode"
        )
        cls = factory._PROVIDERS[slug]
        assert cls.__module__ == module_path
        assert cls.__name__ == factory._PROVIDER_CLASS_NAMES[slug]


def test_render_laziness_defers_module_imports(monkeypatch):
    """On Render (``RENDER=true``), no provider module is imported at
    factory load. Classes are resolved only on first ``get_provider``
    call for that slug."""
    factory = _reload_factory_with_env(monkeypatch, render=True)
    ProviderCls = factory.ModelProviderFactory

    # Lazy path: registry empty at import time.
    assert factory._PROVIDERS == {}, (
        "Expected empty _PROVIDERS on Render, got: "
        f"{list(factory._PROVIDERS.keys())}"
    )

    # get_provider('zai') triggers exactly one module import.
    with patch(
        "importlib.import_module", wraps=importlib.import_module
    ) as spy:
        ProviderCls.get_provider("zai")
    imported_modules = [
        call.args[0]
        for call in spy.call_args_list
        if call.args and isinstance(call.args[0], str)
    ]
    zai_imports = [m for m in imported_modules if m == "models.providers.zai"]
    assert zai_imports, (
        f"Expected get_provider('zai') to import models.providers.zai, "
        f"but got calls: {imported_modules}"
    )

    # And the registry is now populated for that one slug.
    assert "zai" in factory._PROVIDERS


def test_class_name_resolution_acronym_brands():
    """Brand-style class names (OpenAI, DeepSeek, OpenRouter,
    OpenCode) must map correctly, not collapse to ``OpenaiProvider``
    etc."""
    factory = importlib.import_module("models.provider_factory")
    for slug, expected in [
        ("openai", "OpenAIProvider"),
        ("deepseek", "DeepSeekProvider"),
        ("openrouter", "OpenRouterProvider"),
        ("opencode", "OpenCodeProvider"),
        ("anthropic", "AnthropicProvider"),
        ("zai", "ZaiProvider"),
        ("groq", "GroqProvider"),
    ]:
        actual = factory._class_name_for(slug)
        assert actual == expected, f"{slug}: expected {expected}, got {actual}"


def test_unknown_provider_raises(monkeypatch):
    factory = _reload_factory_with_env(monkeypatch, render=True)
    ProviderCls = factory.ModelProviderFactory
    with pytest.raises(ValueError, match="Unknown provider"):
        ProviderCls.get_provider("nonexistent_llm")


def test_get_provider_works_after_lazy_load(monkeypatch):
    """End-to-end: on Render, a single get_provider call resolves a
    class, instantiates it, caches it, and a second call returns the
    same instance."""
    factory = _reload_factory_with_env(monkeypatch, render=True)
    ProviderCls = factory.ModelProviderFactory

    p1 = ProviderCls.get_provider("groq")
    p2 = ProviderCls.get_provider("groq")
    assert p1 is p2  # cached
    assert "groq" in factory._PROVIDERS
    assert factory._PROVIDERS["groq"].__name__ == "GroqProvider"


def test_non_render_get_provider_returns_cached(monkeypatch):
    """Eager mode: get_provider returns cached instance and the
    registry is already populated."""
    factory = _reload_factory_with_env(monkeypatch, render=False)
    ProviderCls = factory.ModelProviderFactory

    p1 = ProviderCls.get_provider("anthropic")
    p2 = ProviderCls.get_provider("anthropic")
    assert p1 is p2
    assert "anthropic" in factory._PROVIDERS
