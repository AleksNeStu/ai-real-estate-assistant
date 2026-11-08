"""
AI-powered listing content generation tools.

This module provides tools for generating property descriptions, headlines,
and social media content using LLMs.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from tools.llm_resolution import resolve_tool_llm

logger = logging.getLogger(__name__)

# Supported languages for content generation
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "English",
    "pl": "Polish",
    "es": "Spanish",
    "de": "German",
    "fr": "French",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
}

# Tone descriptions for prompts
TONE_DESCRIPTIONS: Dict[str, str] = {
    "professional": "Formal, trustworthy, business-oriented",
    "friendly": "Warm, approachable, conversational",
    "luxury": "Elegant, sophisticated, premium-focused",
    "engaging": "Energetic, attention-grabbing, interactive",
}

# Platform-specific constraints for social media
PLATFORM_CONSTRAINTS: Dict[str, Dict[str, Any]] = {
    "facebook": {
        "max_length": 63206,  # Facebook allows very long posts
        "hashtag_style": "moderate",  # 3-5 hashtags
        "emoji_style": "moderate",
    },
    "instagram": {
        "max_length": 2200,
        "hashtag_style": "heavy",  # 8-30 hashtags
        "emoji_style": "heavy",
    },
    "linkedin": {
        "max_length": 3000,
        "hashtag_style": "light",  # 3-5 hashtags
        "emoji_style": "light",  # Professional, minimal emojis
    },
    "twitter": {
        "max_length": 280,
        "hashtag_style": "light",  # 1-3 hashtags
        "emoji_style": "light",
    },
}


class PropertyDescriptionInput(BaseModel):
    """Input for property description generation."""

    property_data: str = Field(
        description="Property details as JSON string or structured text",
    )
    tone: str = Field(
        default="professional",
        description="Tone of the description (professional, friendly, luxury)",
    )
    language: str = Field(
        default="en",
        description="Output language code (en, pl, es, de, fr, it, pt, ru)",
    )
    max_words: int = Field(
        default=150,
        ge=50,
        le=300,
        description="Maximum word count for the description",
    )


class HeadlineInput(BaseModel):
    """Input for headline generation."""

    property_data: str = Field(
        description="Property details as JSON string or structured text",
    )
    count: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of headline variations to generate",
    )
    style: str = Field(
        default="catchy",
        description="Headline style (catchy, professional, seo)",
    )
    language: str = Field(
        default="en",
        description="Output language code (en, pl, es, de, fr, it, pt, ru)",
    )


class SocialMediaInput(BaseModel):
    """Input for social media content generation."""

    property_data: str = Field(
        description="Property details as JSON string or structured text",
    )
    platform: str = Field(
        description="Target platform (facebook, instagram, linkedin, twitter)",
    )
    tone: str = Field(
        default="engaging",
        description="Content tone (engaging, professional, luxury)",
    )
    language: str = Field(
        default="en",
        description="Output language code (en, pl, es, de, fr, it, pt, ru)",
    )
    include_emojis: bool = Field(
        default=True,
        description="Whether to include emojis in the content",
    )
    include_call_to_action: bool = Field(
        default=True,
        description="Whether to include a call-to-action",
    )


class PropertyDescriptionGeneratorTool(BaseTool):
    """
    Tool for generating AI-powered property descriptions.

    Uses LLMs to create compelling, property-specific descriptions
    with customizable tone and multilingual support.
    """

    name: str = "listing_description_generator"
    description: str = (
        "Generate AI-powered property descriptions. "
        "Input: property details (JSON or text), tone (professional/friendly/luxury), language. "
        "Returns: compelling property description (120-180 words)."
    )
    args_schema: type[PropertyDescriptionInput] = PropertyDescriptionInput

    _llm: BaseChatModel | None = PrivateAttr(default=None)

    def __init__(self, llm: Optional[BaseChatModel] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # The model comes from the application - the injected one, or the
        # mock model of a demo deployment.
        self._llm = resolve_tool_llm(
            llm,
            task_type="description generator",
            temperature=0.7,
            max_tokens=1000,
        )

    def _build_prompt(
        self,
        property_data: str,
        tone: str,
        language: str,
        max_words: int,
    ) -> str:
        """Build the prompt for description generation."""
        language_name = SUPPORTED_LANGUAGES.get(language, "English")
        tone_desc = TONE_DESCRIPTIONS.get(tone, TONE_DESCRIPTIONS["professional"])

        prompt = f"""You are a professional real estate copywriter. Write a compelling property description in {language_name}.

Property Details:
{property_data}

Requirements:
- Tone: {tone_desc}
- Length: {max_words} words maximum
- Include: key features, location benefits, and lifestyle appeal
- End with: a clear call-to-action to schedule a viewing
- Format: Use short paragraphs (2-3 sentences each) for readability
- Avoid: overly salesy language, excessive punctuation, clichés

Write the property description now:"""

        return prompt

    def _run(
        self,
        property_data: str,
        tone: str = "professional",
        language: str = "en",
        max_words: int = 150,
    ) -> str:
        """Generate property description."""
        try:
            # Input validation first
            if language not in SUPPORTED_LANGUAGES:
                return f"Error: Unsupported language '{language}'. Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}"

            if tone not in TONE_DESCRIPTIONS:
                return f"Error: Unsupported tone '{tone}'. Supported: {', '.join(TONE_DESCRIPTIONS.keys())}"

            # LLM availability check
            if self._llm is None:
                return (
                    "Error: LLM not available. Please configure an API key "
                    "for a supported provider (OpenAI, Anthropic, Google, etc.)."
                )

            prompt = self._build_prompt(property_data, tone, language, max_words)

            response = self._llm.invoke(prompt)
            # Type narrowing: get string content from response
            description: str
            if hasattr(response, "content"):
                description = str(response.content)
            else:
                description = str(response)

            # Clean up the output
            description = description.strip()
            if description.startswith('"') and description.endswith('"'):
                description = description[1:-1]

            return description

        except Exception as e:
            logger.error("Error generating property description: %s", e)
            return f"Error generating property description: {str(e)}"

    async def _arun(
        self,
        property_data: str,
        tone: str = "professional",
        language: str = "en",
        max_words: int = 150,
    ) -> str:
        """Async version."""
        return self._run(property_data, tone, language, max_words)


class HeadlineGeneratorTool(BaseTool):
    """
    Tool for generating property listing headlines.

    Creates multiple headline variations optimized for different
    purposes and styles.
    """

    name: str = "listing_headline_generator"
    description: str = (
        "Generate catchy property listing headlines. "
        "Input: property details, count (1-10), style (catchy/professional/seo), language. "
        "Returns: list of headline variations with character counts."
    )
    args_schema: type[HeadlineInput] = HeadlineInput

    _llm: BaseChatModel | None = PrivateAttr(default=None)

    def __init__(self, llm: Optional[BaseChatModel] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # The model comes from the application - the injected one, or the
        # mock model of a demo deployment.
        self._llm = resolve_tool_llm(
            llm,
            task_type="headline generator",
            temperature=0.8,  # Higher temperature for creativity
            max_tokens=500,
        )

    def _build_prompt(
        self,
        property_data: str,
        count: int,
        style: str,
        language: str,
    ) -> str:
        """Build the prompt for headline generation."""
        language_name = SUPPORTED_LANGUAGES.get(language, "English")

        style_instructions = {
            "catchy": "Attention-grabbing, emotional, uses power words",
            "professional": "Clear, informative, trustworthy",
            "seo": "Keyword-rich, search-optimized, descriptive",
        }

        instruction = style_instructions.get(style, style_instructions["catchy"])

        prompt = f"""You are a real estate marketing expert. Write {count} compelling listing headlines in {language_name}.

Property Details:
{property_data}

Requirements:
- Style: {instruction}
- Length: 40-80 characters per headline (ideal for listings)
- Variety: Mix of benefit-focused, feature-focused, and curiosity-driven headlines
- Format: Return as a numbered list

Generate {count} unique headlines now:"""

        return prompt

    def _run(
        self,
        property_data: str,
        count: int = 5,
        style: str = "catchy",
        language: str = "en",
    ) -> str:
        """Generate property headlines."""
        try:
            # Input validation first
            if language not in SUPPORTED_LANGUAGES:
                return f"Error: Unsupported language '{language}'. Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}"

            # LLM availability check
            if self._llm is None:
                return (
                    "Error: LLM not available. Please configure an API key "
                    "for a supported provider (OpenAI, Anthropic, Google, etc.)."
                )

            prompt = self._build_prompt(property_data, count, style, language)

            response = self._llm.invoke(prompt)
            # Type narrowing: get string content from response
            content: str
            if hasattr(response, "content"):
                content = str(response.content)
            else:
                content = str(response)

            # Parse the response and add character counts
            lines = content.strip().split("\n")
            result_lines = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Remove numbering if present
                clean_line = line
                if line and line[0].isdigit() and (". " in line[:5] or ") " in line[:5]):
                    clean_line = line.split(".", 1)[-1].split(")", 1)[-1].strip()

                char_count = len(clean_line)
                result_lines.append(f"{clean_line} [{char_count} chars]")

            if not result_lines:
                return content

            return "\n".join(result_lines)

        except Exception as e:
            logger.error("Error generating headlines: %s", e)
            return f"Error generating headlines: {str(e)}"

    async def _arun(
        self,
        property_data: str,
        count: int = 5,
        style: str = "catchy",
        language: str = "en",
    ) -> str:
        """Async version."""
        return self._run(property_data, count, style, language)


class SocialMediaContentGeneratorTool(BaseTool):
    """
    Tool for generating platform-specific social media content.

    Creates optimized content for Facebook, Instagram, LinkedIn, and Twitter
    with appropriate formatting, hashtags, and emojis.
    """

    name: str = "social_media_content_generator"
    description: str = (
        "Generate social media content for property listings. "
        "Input: property details, platform (facebook/instagram/linkedin/twitter), tone, language. "
        "Returns: platform-optimized content with hashtags and emojis."
    )
    args_schema: type[SocialMediaInput] = SocialMediaInput

    _llm: BaseChatModel | None = PrivateAttr(default=None)

    def __init__(self, llm: Optional[BaseChatModel] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # The model comes from the application - the injected one, or the
        # mock model of a demo deployment.
        self._llm = resolve_tool_llm(
            llm,
            task_type="social media generator",
            temperature=0.7,
            max_tokens=800,
        )

    def _get_platform_hashtags(self, platform: str, _language: str) -> str:
        """Get platform-specific hashtag counts."""
        counts = {
            "facebook": "3-5",
            "instagram": "8-15",
            "linkedin": "3-5",
            "twitter": "1-3",
        }
        return counts.get(platform, "3-5")

    def _build_prompt(
        self,
        property_data: str,
        platform: str,
        tone: str,
        language: str,
        include_emojis: bool,
        include_call_to_action: bool,
    ) -> str:
        """Build the prompt for social media content generation."""
        language_name = SUPPORTED_LANGUAGES.get(language, "English")
        tone_desc = TONE_DESCRIPTIONS.get(tone, TONE_DESCRIPTIONS["engaging"])
        constraints = PLATFORM_CONSTRAINTS.get(platform, PLATFORM_CONSTRAINTS["facebook"])

        hashtag_count = self._get_platform_hashtags(platform, platform)
        emoji_instruction = "Include relevant emojis" if include_emojis else "Do NOT use emojis"
        cta_instruction = (
            "End with a clear call-to-action"
            if include_call_to_action
            else "No call-to-action needed"
        )

        platform_guidance = {
            "facebook": "Facebook-friendly: engaging opener, bullet points for features, community feel",
            "instagram": "Instagram-style: visual hooks in text, line breaks for readability, aesthetic focus",
            "linkedin": "LinkedIn-appropriate: professional tone, industry insights, business value",
            "twitter": "Twitter/X format: concise, punchy, one key highlight, space-saving",
        }

        guidance = platform_guidance.get(platform, platform_guidance["facebook"])

        prompt = f"""You are a social media expert for real estate. Create a {platform} post in {language_name}.

Property Details:
{property_data}

Requirements:
- Tone: {tone_desc}
- Format: {guidance}
- Length: Maximum {constraints["max_length"]} characters
- Hashtags: Include {hashtag_count} relevant hashtags at the end
- Emojis: {emoji_instruction}
- Call-to-action: {cta_instruction}
- Language: {language_name}

Platform-specific notes:
- Make it shareable and engaging
- Highlight the property's unique selling points
- Use appropriate formatting for {platform}

Generate the {platform} post now:"""

        return prompt

    def _run(
        self,
        property_data: str,
        platform: str,
        tone: str = "engaging",
        language: str = "en",
        include_emojis: bool = True,
        include_call_to_action: bool = True,
    ) -> str:
        """Generate social media content."""
        try:
            # Input validation first
            if platform not in PLATFORM_CONSTRAINTS:
                platforms = ", ".join(PLATFORM_CONSTRAINTS.keys())
                return f"Error: Unsupported platform '{platform}'. Supported: {platforms}"

            if language not in SUPPORTED_LANGUAGES:
                return f"Error: Unsupported language '{language}'. Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}"

            # LLM availability check
            if self._llm is None:
                return (
                    "Error: LLM not available. Please configure an API key "
                    "for a supported provider (OpenAI, Anthropic, Google, etc.)."
                )

            prompt = self._build_prompt(
                property_data,
                platform,
                tone,
                language,
                include_emojis,
                include_call_to_action,
            )

            response = self._llm.invoke(prompt)

            # Get string content from response with proper type narrowing
            content: str
            if hasattr(response, "content"):
                content = str(response.content)
            else:
                content = str(response)

            # Clean up the output
            content = content.strip()
            if content.startswith('"') and content.endswith('"'):
                content = content[1:-1]

            # Add platform info header
            header = f"=== {platform.upper()} Content ===\n"

            return header + content

        except Exception as e:
            logger.error("Error generating social media content: %s", e)
            return f"Error generating social media content: {str(e)}"

    async def _arun(
        self,
        property_data: str,
        platform: str,
        tone: str = "engaging",
        language: str = "en",
        include_emojis: bool = True,
        include_call_to_action: bool = True,
    ) -> str:
        """Async version."""
        return self._run(
            property_data, platform, tone, language, include_emojis, include_call_to_action
        )


def create_listing_generator_tools() -> List[BaseTool]:
    """
    Create all listing generation tools.

    Returns:
        List of initialized tool instances
    """
    return [
        PropertyDescriptionGeneratorTool(),
        HeadlineGeneratorTool(),
        SocialMediaContentGeneratorTool(),
    ]
