"""
Tests for the model a tool speaks with.

Task #37: five tools built their own LLM instead of using the one the
application resolved, so on the demo - which has no provider key - every
one of them died with "Zhipu AI API key required" while the rest of the
application ran on the mock model.
"""

from unittest.mock import patch

from core.demo import MockLLM
from tools.listing_generator_tools import (
    HeadlineGeneratorTool,
    PropertyDescriptionGeneratorTool,
    SocialMediaContentGeneratorTool,
)
from tools.llm_resolution import resolve_tool_llm
from tools.neighborhood_summary import NeighborhoodSummaryTool
from tools.price_forecast_tools import PriceForecastTool

AI_TOOLS = (
    PropertyDescriptionGeneratorTool,
    HeadlineGeneratorTool,
    SocialMediaContentGeneratorTool,
    PriceForecastTool,
    NeighborhoodSummaryTool,
)


class TestResolveToolLLM:
    def test_the_injected_model_is_used_as_it_is(self):
        model = object()

        assert resolve_tool_llm(model) is model

    def test_a_demo_deployment_speaks_with_the_mock_model(self):
        with patch("config.settings.settings.demo_mode", True):
            model = resolve_tool_llm()

        assert isinstance(model, MockLLM)

    def test_a_demo_deployment_never_asks_a_provider_for_a_model(self):
        with patch("config.settings.settings.demo_mode", True):
            with patch("models.provider_factory.ModelProviderFactory.create_model") as create_model:
                resolve_tool_llm()

        create_model.assert_not_called()


class TestTheToolsSpeakWithTheApplicationModel:
    def test_every_tool_keeps_the_injected_model(self):
        model = object()

        for tool_class in AI_TOOLS:
            tool = tool_class(llm=model)
            assert tool._llm is model, tool_class.__name__

    def test_every_tool_speaks_with_the_mock_model_on_a_demo(self):
        with patch("config.settings.settings.demo_mode", True):
            for tool_class in AI_TOOLS:
                tool = tool_class()
                assert isinstance(tool._llm, MockLLM), tool_class.__name__

    def test_no_tool_asks_a_provider_for_a_model_on_a_demo(self):
        with patch("config.settings.settings.demo_mode", True):
            with patch("models.provider_factory.ModelProviderFactory.create_model") as create_model:
                for tool_class in AI_TOOLS:
                    tool_class()

        create_model.assert_not_called()
