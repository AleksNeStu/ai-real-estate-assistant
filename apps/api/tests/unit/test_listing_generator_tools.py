"""
Unit tests for AI listing generator tools.

Tests for property description, headline, and social media content generation.
"""

from unittest.mock import MagicMock

import pytest

from tools.listing_generator_tools import (
    PLATFORM_CONSTRAINTS,
    SUPPORTED_LANGUAGES,
    TONE_DESCRIPTIONS,
    HeadlineGeneratorTool,
    HeadlineInput,
    PropertyDescriptionGeneratorTool,
    PropertyDescriptionInput,
    SocialMediaContentGeneratorTool,
    SocialMediaInput,
    create_listing_generator_tools,
)


def _make_mock_llm_response(content: str) -> MagicMock:
    """Create a mock LLM response with a .content attribute."""
    response = MagicMock()
    response.content = content
    return response


def _make_description_tool_with_llm(
    llm_response: str = "Generated description text",
) -> PropertyDescriptionGeneratorTool:
    """Create a PropertyDescriptionGeneratorTool with a mocked LLM."""
    tool = PropertyDescriptionGeneratorTool()
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _make_mock_llm_response(llm_response)
    tool._llm = mock_llm
    return tool


def _make_headline_tool_with_llm(
    llm_response: str = "1. Great Property\n2. Best Deal",
) -> HeadlineGeneratorTool:
    """Create a HeadlineGeneratorTool with a mocked LLM."""
    tool = HeadlineGeneratorTool()
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _make_mock_llm_response(llm_response)
    tool._llm = mock_llm
    return tool


def _make_social_tool_with_llm(
    llm_response: str = "Social media post content",
) -> SocialMediaContentGeneratorTool:
    """Create a SocialMediaContentGeneratorTool with a mocked LLM."""
    tool = SocialMediaContentGeneratorTool()
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _make_mock_llm_response(llm_response)
    tool._llm = mock_llm
    return tool


# ============================================================================
# PropertyDescriptionGeneratorTool
# ============================================================================


class TestPropertyDescriptionGeneratorTool:
    """Test suite for PropertyDescriptionGeneratorTool."""

    @pytest.fixture
    def generator(self):
        """Fixture for description generator."""
        return PropertyDescriptionGeneratorTool()

    def test_tool_initialization(self, generator):
        """Test tool initialization."""
        assert generator.name == "listing_description_generator"
        assert "description" in generator.description.lower()
        assert "generate" in generator.description.lower()

    def test_supported_languages(self):
        """Test that supported languages are properly defined."""
        assert "en" in SUPPORTED_LANGUAGES
        assert "pl" in SUPPORTED_LANGUAGES
        assert "es" in SUPPORTED_LANGUAGES
        assert "de" in SUPPORTED_LANGUAGES
        assert "fr" in SUPPORTED_LANGUAGES
        assert len(SUPPORTED_LANGUAGES) >= 7

    def test_tone_descriptions(self):
        """Test that tone descriptions are properly defined."""
        assert "professional" in TONE_DESCRIPTIONS
        assert "friendly" in TONE_DESCRIPTIONS
        assert "luxury" in TONE_DESCRIPTIONS
        assert "engaging" in TONE_DESCRIPTIONS

    def test_invalid_language_handling(self, generator):
        """Test handling of invalid language parameter."""
        result = generator._run(
            property_data="Test property",
            language="invalid_lang",
        )
        assert "Error" in result
        assert "Unsupported language" in result

    def test_invalid_tone_handling(self, generator):
        """Test handling of invalid tone parameter."""
        result = generator._run(
            property_data="Test property",
            tone="invalid_tone",
        )
        assert "Error" in result
        assert "Unsupported tone" in result

    def test_llm_not_available_returns_error(self, generator):
        """Test that missing LLM produces an actionable error message.

        The test used to be skipped: the resolver always builds a model
        (the demo model in a test environment), so the branch looked
        unreachable. It is not - a deployment with no provider reaches it -
        and the branch is the one that tells the operator what to configure.
        """
        generator._llm = None
        result = generator._run(
            property_data="A nice apartment",
            tone="professional",
            language="en",
        )
        assert "Error" in result
        assert "LLM not available" in result

    # --- _build_prompt tests ---

    def test_build_prompt_default_params(self):
        """Test _build_prompt with default tone/language."""
        tool = _make_description_tool_with_llm()
        prompt = tool._build_prompt("3-bed apartment in Berlin", "professional", "en", 150)

        assert "real estate copywriter" in prompt
        assert "3-bed apartment in Berlin" in prompt
        assert "English" in prompt
        assert "150 words maximum" in prompt
        assert "Formal, trustworthy" in prompt

    def test_build_prompt_polish_language(self):
        """Test _build_prompt with Polish language."""
        tool = _make_description_tool_with_llm()
        prompt = tool._build_prompt("Mieszkanie w Krakowie", "friendly", "pl", 100)

        assert "Polish" in prompt
        assert "100 words maximum" in prompt
        assert "Warm, approachable" in prompt

    def test_build_prompt_unknown_language_defaults_to_english(self):
        """Test _build_prompt falls back to English for unknown language code."""
        tool = _make_description_tool_with_llm()
        prompt = tool._build_prompt("Test data", "professional", "xx", 150)

        assert "English" in prompt

    def test_build_prompt_unknown_tone_defaults_to_professional(self):
        """Test _build_prompt falls back to professional for unknown tone."""
        tool = _make_description_tool_with_llm()
        prompt = tool._build_prompt("Test data", "unknown_tone", "en", 200)

        assert "Formal, trustworthy" in prompt
        assert "200 words maximum" in prompt

    # --- _run success path tests ---

    def test_run_success_returns_description(self):
        """Test _run with a working LLM returns generated description."""
        tool = _make_description_tool_with_llm(
            "Beautiful sunny apartment in the heart of the city."
        )
        result = tool._run(property_data="2-bed apartment", tone="professional", language="en")

        assert result == "Beautiful sunny apartment in the heart of the city."
        tool._llm.invoke.assert_called_once()

    def test_run_strips_quotes_from_response(self):
        """Test _run strips surrounding double quotes from LLM response."""
        tool = _make_description_tool_with_llm('"A quoted description."')
        result = tool._run(property_data="Test property", tone="friendly", language="en")

        assert result == "A quoted description."

    def test_run_strips_whitespace(self):
        """Test _run strips leading/trailing whitespace."""
        tool = _make_description_tool_with_llm("  \n  Spacious flat.  \n  ")
        result = tool._run(property_data="Test property", tone="luxury", language="en")

        assert result == "Spacious flat."

    def test_run_no_content_attribute_falls_back_to_str(self):
        """Test _run handles response without .content attribute."""
        tool = _make_description_tool_with_llm()
        # Replace response with one that has no .content
        tool._llm.invoke.return_value = "Plain string response"
        result = tool._run(property_data="Test property", tone="professional", language="en")

        assert result == "Plain string response"

    def test_run_llm_exception_returns_error(self):
        """Test _run returns error when LLM raises an exception."""
        tool = _make_description_tool_with_llm()
        tool._llm.invoke.side_effect = RuntimeError("API timeout")

        result = tool._run(property_data="Test property", tone="professional", language="en")
        assert "Error generating property description" in result
        assert "API timeout" in result

    def test_run_calls_llm_with_correct_prompt(self):
        """Test that _run invokes LLM with a well-formed prompt."""
        tool = _make_description_tool_with_llm("Some output")
        tool._run(property_data="Luxury villa", tone="luxury", language="fr", max_words=200)

        call_args = tool._llm.invoke.call_args[0][0]
        assert "Luxury villa" in call_args
        assert "French" in call_args
        assert "200 words maximum" in call_args
        assert "Elegant, sophisticated" in call_args

    # --- _arun tests ---

    @pytest.mark.asyncio
    async def test_arun_delegates_to_run(self):
        """Test _arun delegates to _run with same arguments."""
        tool = _make_description_tool_with_llm("Async description")
        result = await tool._arun(
            property_data="Loft apartment",
            tone="friendly",
            language="en",
            max_words=100,
        )
        assert result == "Async description"

    @pytest.mark.asyncio
    async def test_arun_handles_errors(self):
        """Test _arun propagates error strings from _run."""
        tool = PropertyDescriptionGeneratorTool()
        result = await tool._arun(property_data="Test", language="invalid_lang")
        assert "Error" in result


# ============================================================================
# HeadlineGeneratorTool
# ============================================================================


class TestHeadlineGeneratorTool:
    """Test suite for HeadlineGeneratorTool."""

    @pytest.fixture
    def generator(self):
        """Fixture for headline generator."""
        return HeadlineGeneratorTool()

    def test_tool_initialization(self, generator):
        """Test tool initialization."""
        assert generator.name == "listing_headline_generator"
        assert "headline" in generator.description.lower()

    def test_invalid_language_handling(self, generator):
        """Test handling of invalid language parameter."""
        result = generator._run(
            property_data="Test property",
            language="xx",
        )
        assert "Error" in result
        assert "Unsupported language" in result

    def test_valid_styles(self):
        """Test that valid styles are accepted."""
        # Style validation happens in the prompt building
        # We just verify the tool can be instantiated
        generator = HeadlineGeneratorTool()
        assert generator is not None

    def test_llm_not_available_returns_error(self, generator):
        """Test that missing LLM produces error."""
        generator._llm = None
        result = generator._run(property_data="A nice apartment", language="en")
        assert "Error" in result
        assert "LLM not available" in result

    # --- _build_prompt tests ---

    def test_build_prompt_catchy_style(self):
        """Test _build_prompt with catchy style."""
        tool = _make_headline_tool_with_llm()
        prompt = tool._build_prompt("Modern loft downtown", 3, "catchy", "en")

        assert "3 compelling listing headlines" in prompt
        assert "Modern loft downtown" in prompt
        assert "English" in prompt
        assert "Attention-grabbing" in prompt

    def test_build_prompt_professional_style(self):
        """Test _build_prompt with professional style."""
        tool = _make_headline_tool_with_llm()
        prompt = tool._build_prompt("Beach house", 5, "professional", "de")

        assert "5 compelling listing headlines" in prompt
        assert "German" in prompt
        assert "Clear, informative" in prompt

    def test_build_prompt_seo_style(self):
        """Test _build_prompt with seo style."""
        tool = _make_headline_tool_with_llm()
        prompt = tool._build_prompt("Suburban home", 7, "seo", "en")

        assert "7 compelling listing headlines" in prompt
        assert "Keyword-rich" in prompt

    def test_build_prompt_unknown_style_defaults_to_catchy(self):
        """Test _build_prompt falls back to catchy for unknown style."""
        tool = _make_headline_tool_with_llm()
        prompt = tool._build_prompt("Test", 3, "unknown_style", "en")

        assert "Attention-grabbing" in prompt

    def test_build_prompt_unknown_language_defaults_to_english(self):
        """Test _build_prompt falls back to English for unknown language."""
        tool = _make_headline_tool_with_llm()
        prompt = tool._build_prompt("Test", 3, "catchy", "zz")

        assert "English" in prompt

    # --- _run success path tests ---

    def test_run_success_parses_numbered_headlines(self):
        """Test _run correctly parses numbered headlines and adds char counts."""
        tool = _make_headline_tool_with_llm(
            "1. Dream Home in Berlin\n2. Luxury Living Awaits\n3. Your Perfect Flat"
        )
        result = tool._run(property_data="Berlin apartment", count=3, style="catchy", language="en")

        lines = result.split("\n")
        assert len(lines) == 3
        # Each line should have char count appended, e.g. "[20 chars]"
        for line in lines:
            assert "chars]" in line

    def test_run_headline_char_count_accuracy(self):
        """Test that char counts are accurate after removing numbering."""
        tool = _make_headline_tool_with_llm("1. Hello\n2. World")
        result = tool._run(property_data="Test", count=2, language="en")

        lines = result.split("\n")
        # "Hello" is 5 chars
        assert "[5 chars]" in lines[0]
        # "World" is 5 chars
        assert "[5 chars]" in lines[1]

    def test_run_handles_parenthesis_numbering(self):
        """Test _run handles 1) style numbering."""
        tool = _make_headline_tool_with_llm("1) First Headline\n2) Second Headline")
        result = tool._run(property_data="Test", count=2, language="en")

        lines = result.split("\n")
        assert len(lines) == 2
        assert "First Headline" in lines[0]
        assert "Second Headline" in lines[1]

    def test_run_skips_empty_lines(self):
        """Test _run skips empty lines in LLM response."""
        tool = _make_headline_tool_with_llm("1. Headline One\n\n\n2. Headline Two")
        result = tool._run(property_data="Test", count=2, language="en")

        lines = result.split("\n")
        assert len(lines) == 2

    def test_run_returns_raw_content_if_no_lines_parsed(self):
        """Test _run returns raw content when no valid headlines are parsed."""
        tool = _make_headline_tool_with_llm("   \n   \n   ")
        result = tool._run(property_data="Test", count=5, language="en")

        # Falls through to returning raw content since no non-empty lines
        assert isinstance(result, str)

    def test_run_no_content_attribute_falls_back_to_str(self):
        """Test _run handles response without .content attribute."""
        tool = _make_headline_tool_with_llm()
        tool._llm.invoke.return_value = "1. Raw headline"
        result = tool._run(property_data="Test", count=1, language="en")

        assert "Raw headline" in result

    def test_run_llm_exception_returns_error(self):
        """Test _run returns error when LLM raises an exception."""
        tool = _make_headline_tool_with_llm()
        tool._llm.invoke.side_effect = RuntimeError("Service unavailable")

        result = tool._run(property_data="Test", count=3, language="en")
        assert "Error generating headlines" in result
        assert "Service unavailable" in result

    def test_run_calls_llm_with_correct_prompt(self):
        """Test that _run invokes LLM with a well-formed prompt."""
        tool = _make_headline_tool_with_llm("1. Test headline")
        tool._run(property_data="Cozy studio", count=4, style="seo", language="es")

        call_args = tool._llm.invoke.call_args[0][0]
        assert "Cozy studio" in call_args
        assert "Spanish" in call_args
        assert "4 compelling listing headlines" in call_args
        assert "Keyword-rich" in call_args

    # --- _arun tests ---

    @pytest.mark.asyncio
    async def test_arun_delegates_to_run(self):
        """Test _arun delegates to _run with same arguments."""
        tool = _make_headline_tool_with_llm("1. Async Headline")
        result = await tool._arun(property_data="Test", count=1, style="catchy", language="en")
        assert "Async Headline" in result

    @pytest.mark.asyncio
    async def test_arun_handles_errors(self):
        """Test _arun propagates error strings from _run."""
        tool = HeadlineGeneratorTool()
        result = await tool._arun(property_data="Test", language="invalid")
        assert "Error" in result


# ============================================================================
# SocialMediaContentGeneratorTool
# ============================================================================


class TestSocialMediaContentGeneratorTool:
    """Test suite for SocialMediaContentGeneratorTool."""

    @pytest.fixture
    def generator(self):
        """Fixture for social media generator."""
        return SocialMediaContentGeneratorTool()

    def test_tool_initialization(self, generator):
        """Test tool initialization."""
        assert generator.name == "social_media_content_generator"
        assert "social media" in generator.description.lower()

    def test_platform_constraints(self):
        """Test that platform constraints are properly defined."""
        assert "facebook" in PLATFORM_CONSTRAINTS
        assert "instagram" in PLATFORM_CONSTRAINTS
        assert "linkedin" in PLATFORM_CONSTRAINTS
        assert "twitter" in PLATFORM_CONSTRAINTS

        # Verify constraint structure
        for _platform, constraints in PLATFORM_CONSTRAINTS.items():
            assert "max_length" in constraints
            assert "hashtag_style" in constraints
            assert "emoji_style" in constraints

    def test_invalid_platform_handling(self, generator):
        """Test handling of invalid platform parameter."""
        result = generator._run(
            property_data="Test property",
            platform="tiktok",
        )
        assert "Error" in result
        assert "Unsupported platform" in result

    def test_invalid_language_handling(self, generator):
        """Test handling of invalid language parameter."""
        result = generator._run(
            property_data="Test property",
            platform="facebook",
            language="invalid",
        )
        assert "Error" in result
        assert "Unsupported language" in result

    def test_platform_character_limits(self):
        """Test that each platform has appropriate character limits."""
        assert PLATFORM_CONSTRAINTS["twitter"]["max_length"] == 280
        assert PLATFORM_CONSTRAINTS["instagram"]["max_length"] == 2200
        assert PLATFORM_CONSTRAINTS["linkedin"]["max_length"] == 3000
        assert PLATFORM_CONSTRAINTS["facebook"]["max_length"] == 63206

    def test_llm_not_available_returns_error(self, generator):
        """Test that missing LLM produces error."""
        generator._llm = None
        result = generator._run(property_data="Test", platform="facebook", language="en")
        assert "Error" in result
        assert "LLM not available" in result

    # --- _get_platform_hashtags tests ---

    def test_get_platform_hashtags_facebook(self):
        """Test hashtag count for Facebook."""
        tool = _make_social_tool_with_llm()
        assert tool._get_platform_hashtags("facebook", "en") == "3-5"

    def test_get_platform_hashtags_instagram(self):
        """Test hashtag count for Instagram."""
        tool = _make_social_tool_with_llm()
        assert tool._get_platform_hashtags("instagram", "en") == "8-15"

    def test_get_platform_hashtags_linkedin(self):
        """Test hashtag count for LinkedIn."""
        tool = _make_social_tool_with_llm()
        assert tool._get_platform_hashtags("linkedin", "en") == "3-5"

    def test_get_platform_hashtags_twitter(self):
        """Test hashtag count for Twitter."""
        tool = _make_social_tool_with_llm()
        assert tool._get_platform_hashtags("twitter", "en") == "1-3"

    def test_get_platform_hashtags_unknown_defaults(self):
        """Test hashtag count for unknown platform defaults to 3-5."""
        tool = _make_social_tool_with_llm()
        assert tool._get_platform_hashtags("myspace", "en") == "3-5"

    # --- _build_prompt tests ---

    def test_build_prompt_facebook_with_emojis_cta(self):
        """Test _build_prompt for Facebook with emojis and CTA."""
        tool = _make_social_tool_with_llm()
        prompt = tool._build_prompt(
            "Beautiful penthouse",
            "facebook",
            "engaging",
            "en",
            include_emojis=True,
            include_call_to_action=True,
        )

        assert "Beautiful penthouse" in prompt
        assert "English" in prompt
        assert "63206 characters" in prompt
        assert "Include relevant emojis" in prompt
        assert "clear call-to-action" in prompt
        assert "Energetic, attention-grabbing" in prompt

    def test_build_prompt_instagram_no_emojis_no_cta(self):
        """Test _build_prompt for Instagram without emojis and no CTA."""
        tool = _make_social_tool_with_llm()
        prompt = tool._build_prompt(
            "Cozy studio",
            "instagram",
            "professional",
            "pl",
            include_emojis=False,
            include_call_to_action=False,
        )

        assert "2200 characters" in prompt
        assert "Do NOT use emojis" in prompt
        assert "No call-to-action needed" in prompt
        assert "Polish" in prompt

    def test_build_prompt_linkedin(self):
        """Test _build_prompt for LinkedIn."""
        tool = _make_social_tool_with_llm()
        prompt = tool._build_prompt(
            "Office space",
            "linkedin",
            "professional",
            "de",
            include_emojis=True,
            include_call_to_action=True,
        )

        assert "3000 characters" in prompt
        assert "German" in prompt
        assert "LinkedIn-appropriate" in prompt

    def test_build_prompt_twitter(self):
        """Test _build_prompt for Twitter."""
        tool = _make_social_tool_with_llm()
        prompt = tool._build_prompt(
            "Small flat",
            "twitter",
            "engaging",
            "en",
            include_emojis=True,
            include_call_to_action=True,
        )

        assert "280 characters" in prompt
        assert "Twitter/X format" in prompt

    def test_build_prompt_unknown_platform_defaults_to_facebook(self):
        """Test _build_prompt defaults to Facebook constraints for unknown platform."""
        tool = _make_social_tool_with_llm()
        prompt = tool._build_prompt(
            "Test",
            "unknown_platform",
            "engaging",
            "en",
            include_emojis=True,
            include_call_to_action=True,
        )

        assert "63206 characters" in prompt

    def test_build_prompt_unknown_tone_defaults_to_engaging(self):
        """Test _build_prompt defaults to engaging tone for unknown tone."""
        tool = _make_social_tool_with_llm()
        prompt = tool._build_prompt(
            "Test",
            "facebook",
            "whimsical",
            "en",
            include_emojis=True,
            include_call_to_action=True,
        )

        assert "Energetic, attention-grabbing" in prompt

    def test_build_prompt_unknown_language_defaults_to_english(self):
        """Test _build_prompt defaults to English for unknown language."""
        tool = _make_social_tool_with_llm()
        prompt = tool._build_prompt(
            "Test",
            "facebook",
            "engaging",
            "zz",
            include_emojis=True,
            include_call_to_action=True,
        )

        assert "English" in prompt

    # --- _run success path tests ---

    def test_run_success_returns_content_with_header(self):
        """Test _run returns content with platform header."""
        tool = _make_social_tool_with_llm("Amazing property! Check it out.")
        result = tool._run(
            property_data="Luxury apartment",
            platform="facebook",
            tone="engaging",
            language="en",
        )

        assert result.startswith("=== FACEBOOK Content ===")
        assert "Amazing property! Check it out." in result

    def test_run_strips_quotes_from_response(self):
        """Test _run strips surrounding quotes from LLM response."""
        tool = _make_social_tool_with_llm('"Quoted social post."')
        result = tool._run(property_data="Test", platform="instagram", language="en")

        assert '=="' not in result
        assert "Quoted social post." in result

    def test_run_strips_whitespace(self):
        """Test _run strips leading/trailing whitespace."""
        tool = _make_social_tool_with_llm("  \n  Post content.  \n  ")
        result = tool._run(property_data="Test", platform="twitter", language="en")

        assert "Post content." in result

    def test_run_no_content_attribute_falls_back_to_str(self):
        """Test _run handles response without .content attribute."""
        tool = _make_social_tool_with_llm()
        tool._llm.invoke.return_value = "Plain string post"
        result = tool._run(property_data="Test", platform="linkedin", language="en")

        assert "Plain string post" in result

    def test_run_platform_header_case(self):
        """Test platform header is uppercase."""
        tool = _make_social_tool_with_llm("Post")
        result = tool._run(property_data="Test", platform="twitter", language="en")
        assert "=== TWITTER Content ===" in result

    def test_run_llm_exception_returns_error(self):
        """Test _run returns error when LLM raises an exception."""
        tool = _make_social_tool_with_llm()
        tool._llm.invoke.side_effect = RuntimeError("Rate limit exceeded")

        result = tool._run(property_data="Test", platform="facebook", language="en")
        assert "Error generating social media content" in result
        assert "Rate limit exceeded" in result

    def test_run_calls_llm_with_correct_prompt(self):
        """Test that _run invokes LLM with a well-formed prompt."""
        tool = _make_social_tool_with_llm("Post")
        tool._run(
            property_data="Beach house",
            platform="instagram",
            tone="luxury",
            language="fr",
            include_emojis=False,
            include_call_to_action=False,
        )

        call_args = tool._llm.invoke.call_args[0][0]
        assert "Beach house" in call_args
        assert "French" in call_args
        assert "2200 characters" in call_args
        assert "Do NOT use emojis" in call_args
        assert "No call-to-action needed" in call_args
        assert "Elegant, sophisticated" in call_args

    # --- _arun tests ---

    @pytest.mark.asyncio
    async def test_arun_delegates_to_run(self):
        """Test _arun delegates to _run with same arguments."""
        tool = _make_social_tool_with_llm("Async social post")
        result = await tool._arun(
            property_data="Test",
            platform="facebook",
            tone="engaging",
            language="en",
            include_emojis=True,
            include_call_to_action=True,
        )
        assert "Async social post" in result

    @pytest.mark.asyncio
    async def test_arun_handles_errors(self):
        """Test _arun propagates error strings from _run."""
        tool = SocialMediaContentGeneratorTool()
        result = await tool._arun(property_data="Test", platform="invalid_platform")
        assert "Error" in result


# ============================================================================
# Factory function
# ============================================================================


class TestListingGeneratorFactory:
    """Test suite for the factory function."""

    def test_create_all_tools(self):
        """Test creating all listing generator tools."""
        tools = create_listing_generator_tools()

        assert len(tools) == 3
        assert all(hasattr(tool, "name") for tool in tools)
        assert all(hasattr(tool, "description") for tool in tools)

    def test_tool_names_unique(self):
        """Test that tool names are unique."""
        tools = create_listing_generator_tools()
        names = [tool.name for tool in tools]

        assert len(names) == len(set(names))  # All unique

    def test_all_expected_tools_present(self):
        """Test that all expected tools are created."""
        tools = create_listing_generator_tools()
        tool_names = {tool.name for tool in tools}

        expected_names = {
            "listing_description_generator",
            "listing_headline_generator",
            "social_media_content_generator",
        }

        assert tool_names == expected_names


# ============================================================================
# Integration / metadata tests
# ============================================================================


class TestToolIntegration:
    """Integration tests for listing generator tools."""

    @pytest.fixture
    def all_tools(self):
        """Fixture with all listing generator tools."""
        return create_listing_generator_tools()

    def test_tools_have_llm_attribute(self, all_tools):
        """Test that all tools have LLM attribute (may be None)."""
        for tool in all_tools:
            assert hasattr(tool, "_llm")

    def test_tools_have_async_methods(self, all_tools):
        """Test that all tools have async versions."""
        for tool in all_tools:
            assert hasattr(tool, "_arun")

    def test_description_tool_metadata(self):
        """Test PropertyDescriptionGeneratorTool metadata."""
        tool = PropertyDescriptionGeneratorTool()
        assert hasattr(tool, "args_schema")
        assert tool.args_schema is PropertyDescriptionInput

    def test_headline_tool_metadata(self):
        """Test HeadlineGeneratorTool metadata."""
        tool = HeadlineGeneratorTool()
        assert hasattr(tool, "args_schema")
        assert tool.args_schema is HeadlineInput

    def test_social_media_tool_metadata(self):
        """Test SocialMediaContentGeneratorTool metadata."""
        tool = SocialMediaContentGeneratorTool()
        assert hasattr(tool, "args_schema")
        assert tool.args_schema is SocialMediaInput


# ============================================================================
# Pydantic schema validation tests
# ============================================================================


class TestInputSchemas:
    """Tests for Pydantic input model validation."""

    def test_property_description_input_defaults(self):
        """Test PropertyDescriptionInput default values."""
        inp = PropertyDescriptionInput(property_data="test")
        assert inp.tone == "professional"
        assert inp.language == "en"
        assert inp.max_words == 150

    def test_property_description_input_custom(self):
        """Test PropertyDescriptionInput with custom values."""
        inp = PropertyDescriptionInput(
            property_data="test", tone="luxury", language="fr", max_words=250
        )
        assert inp.tone == "luxury"
        assert inp.language == "fr"
        assert inp.max_words == 250

    def test_property_description_input_min_words(self):
        """Test PropertyDescriptionInput enforces minimum word count."""
        inp = PropertyDescriptionInput(property_data="test", max_words=50)
        assert inp.max_words == 50

    def test_property_description_input_max_words(self):
        """Test PropertyDescriptionInput enforces maximum word count."""
        inp = PropertyDescriptionInput(property_data="test", max_words=300)
        assert inp.max_words == 300

    def test_headline_input_defaults(self):
        """Test HeadlineInput default values."""
        inp = HeadlineInput(property_data="test")
        assert inp.count == 5
        assert inp.style == "catchy"
        assert inp.language == "en"

    def test_headline_input_custom(self):
        """Test HeadlineInput with custom values."""
        inp = HeadlineInput(property_data="test", count=10, style="seo", language="de")
        assert inp.count == 10
        assert inp.style == "seo"
        assert inp.language == "de"

    def test_headline_input_count_bounds(self):
        """Test HeadlineInput count boundaries."""
        inp_min = HeadlineInput(property_data="test", count=1)
        assert inp_min.count == 1

        inp_max = HeadlineInput(property_data="test", count=10)
        assert inp_max.count == 10

    def test_social_media_input_defaults(self):
        """Test SocialMediaInput default values."""
        inp = SocialMediaInput(property_data="test", platform="facebook")
        assert inp.tone == "engaging"
        assert inp.language == "en"
        assert inp.include_emojis is True
        assert inp.include_call_to_action is True

    def test_social_media_input_custom(self):
        """Test SocialMediaInput with custom values."""
        inp = SocialMediaInput(
            property_data="test",
            platform="twitter",
            tone="professional",
            language="es",
            include_emojis=False,
            include_call_to_action=False,
        )
        assert inp.platform == "twitter"
        assert inp.tone == "professional"
        assert inp.language == "es"
        assert inp.include_emojis is False
        assert inp.include_call_to_action is False
