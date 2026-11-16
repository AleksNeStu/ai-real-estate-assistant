"""The provider catalogue is the list the README publishes.

The README says the product answers from "17 providers" and names them.
Nothing asserted that list: a provider dropped from the registry - or a
module that stopped importing - would have shipped silently, and the README
would have kept claiming a provider the product cannot reach.

These tests hold the list to the claim, and hold every entry to being a
provider the factory can actually build.
"""

import importlib

import pytest

from models.provider_factory import _PROVIDER_CLASS_NAMES, _PROVIDER_MODULES

# The providers the README names, in the order it names them.
THE_SEVENTEEN = [
    "openai",
    "anthropic",
    "google",
    "grok",
    "deepseek",
    "openrouter",
    "groq",
    "mistral",
    "qwen",
    "zai",
    "moonshot",
    "opencode",
    "together",
    "fireworks",
    "huggingface",
    "ollama",
    "minimax",
]

# The environment variable of each provider. The names are not always the
# slug in upper case: Grok is XAI, Qwen is DashScope, and Ollama runs
# locally and needs no key at all.
THE_ENV_VARIABLE = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "grok": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "zai": "ZHIPUAI_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "opencode": "OPENCODE_API_KEY",
    "together": "TOGETHER_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "huggingface": "HUGGINGFACE_API_KEY",
    "ollama": "OLLAMA_API_BASE",
    "minimax": "MINIMAX_API_KEY",
}


def test_the_registry_holds_the_seventeen_providers_the_readme_names():
    assert set(_PROVIDER_MODULES) == set(THE_SEVENTEEN)
    assert len(_PROVIDER_MODULES) == 17


def test_every_provider_has_a_module_and_a_class():
    assert set(_PROVIDER_CLASS_NAMES) == set(_PROVIDER_MODULES)


@pytest.mark.parametrize("slug", THE_SEVENTEEN)
def test_every_provider_module_imports_and_exposes_its_class(slug):
    module = importlib.import_module(_PROVIDER_MODULES[slug])
    class_name = _PROVIDER_CLASS_NAMES[slug]

    assert hasattr(module, class_name), f"{_PROVIDER_MODULES[slug]} does not expose {class_name}"


def test_the_env_example_documents_every_provider():
    """A self-hoster has to be able to configure what the README offers.

    Nine of the seventeen had no variable in the example file, so the claim
    was true and the configuration was impossible without reading
    settings.py. The names are not always the slug in upper case: Grok is
    XAI, Qwen is DashScope, and Ollama needs no key at all.
    """
    from pathlib import Path

    env_example = Path(__file__).resolve().parents[3] / ".env.example"
    text = env_example.read_text(encoding="utf-8")

    for slug, variable in THE_ENV_VARIABLE.items():
        assert variable in text, f"{slug} has no {variable} in .env.example"


def test_the_env_example_names_are_read_by_the_settings():
    """A variable the settings never read is a variable that does nothing.

    The example file and the settings have to agree: the file tells the
    self-hoster what to set, the settings decide what it means.
    """
    from pathlib import Path

    settings_source = (Path(__file__).resolve().parents[3] / "config" / "settings.py").read_text(
        encoding="utf-8"
    )

    for slug, variable in THE_ENV_VARIABLE.items():
        if slug == "ollama":
            # Ollama's base URL is read by the detector, not by the settings.
            continue
        assert variable in settings_source, f"the settings never read {variable} ({slug})"
