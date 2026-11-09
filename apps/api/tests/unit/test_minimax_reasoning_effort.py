"""How hard the MiniMax model thinks.

M3.1 Flash always reasons, and it reasons at 'max' when the parameter is
missing. 'max' is the most expensive way to answer a question that the
catalogue already answers, so the effort is a setting of the deployment -
and a typo in it must not reach the API.
"""

import pytest

from models.providers.minimax import MiniMaxProvider


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> MiniMaxProvider:
    monkeypatch.setenv("REALT_MINIMAX_API_KEY", "test-key")
    return MiniMaxProvider()


def _effort(provider: MiniMaxProvider, monkeypatch: pytest.MonkeyPatch, value: str) -> str | None:
    from config.settings import get_settings

    monkeypatch.setattr(get_settings(), "minimax_reasoning_effort", value, raising=False)
    return provider._reasoning_effort("MiniMax-M3.1-Flash")


class TestTheEffortOfTheDeployment:
    def test_no_setting_means_no_parameter(
        self, provider: MiniMaxProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without the setting the API decides - and its default is 'max'."""
        assert _effort(provider, monkeypatch, "") is None
        assert _effort(provider, monkeypatch, None) is None

    def test_the_setting_reaches_the_api(
        self, provider: MiniMaxProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _effort(provider, monkeypatch, "low") == "low"
        assert _effort(provider, monkeypatch, "  MINIMAL  ") == "minimal"

    def test_a_typo_is_ignored(
        self, provider: MiniMaxProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unknown value would make every request fail."""
        assert _effort(provider, monkeypatch, "deep") is None
        assert _effort(provider, monkeypatch, "12") is None

    def test_the_flash_model_is_never_told_to_stop_reasoning(
        self, provider: MiniMaxProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """M3.1 Flash answers HTTP 400 to 'none'."""
        from config.settings import get_settings

        monkeypatch.setattr(get_settings(), "minimax_reasoning_effort", "none", raising=False)
        assert provider._reasoning_effort("MiniMax-M3.1-Flash") is None
        # The bigger model accepts it.
        assert provider._reasoning_effort("MiniMax-M3") == "none"

    def test_the_model_carries_the_effort_in_the_request(
        self, provider: MiniMaxProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from config.settings import get_settings

        monkeypatch.setattr(get_settings(), "minimax_reasoning_effort", "low", raising=False)
        model = provider.create_model("MiniMax-M3.1-Flash", max_tokens=256)
        assert model.extra_body == {"reasoning": {"effort": "low"}}
        assert model.max_tokens == 256
