"""
API Key Validation Utility.

Provides functionality to validate API keys for different providers
by making test requests to their APIs.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of API key validation."""
    is_valid: bool
    provider: str
    message: str
    error_details: Optional[str] = None


class APIKeyValidator:
    """Utility class for validating API keys across different providers."""

    @staticmethod
    def validate_openai(api_key: str) -> ValidationResult:
        """
        Validate OpenAI API key by making a test request.

        Args:
            api_key: OpenAI API key to validate

        Returns:
            ValidationResult with validation status and message
        """
        try:
            import openai

            client = openai.OpenAI(api_key=api_key)
            # Make a minimal test request
            client.models.list()

            return ValidationResult(
                is_valid=True,
                provider="OpenAI",
                message="API key is valid"
            )
        except Exception as e:
            error_msg = str(e)
            if (
                "authentication" in error_msg.lower()
                or "api_key" in error_msg.lower()
            ):
                return ValidationResult(
                    is_valid=False,
                    provider="OpenAI",
                    message="Invalid API key",
                    error_details=error_msg
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    provider="OpenAI",
                    message="Validation error",
                    error_details=error_msg
                )

    @staticmethod
    def validate_anthropic(api_key: str) -> ValidationResult:
        """
        Validate Anthropic API key by making a test request.

        Args:
            api_key: Anthropic API key to validate

        Returns:
            ValidationResult with validation status and message
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            # Make a minimal test request - list models or minimal completion
            # Anthropic doesn't have a models.list endpoint, so we'll try a minimal message
            client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}]
            )

            return ValidationResult(
                is_valid=True,
                provider="Anthropic",
                message="API key is valid"
            )
        except Exception as e:
            error_msg = str(e)
            if "authentication" in error_msg.lower() or "api_key" in error_msg.lower() or "401" in error_msg:
                return ValidationResult(
                    is_valid=False,
                    provider="Anthropic",
                    message="Invalid API key",
                    error_details=error_msg
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    provider="Anthropic",
                    message="Validation error",
                    error_details=error_msg
                )

    @staticmethod
    def validate_google(api_key: str) -> ValidationResult:
        """
        Validate Google (Gemini) API key by making a test request.

        Args:
            api_key: Google API key to validate

        Returns:
            ValidationResult with validation status and message
        """
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            # List available models as a test
            list(genai.list_models())

            return ValidationResult(
                is_valid=True,
                provider="Google",
                message="API key is valid"
            )
        except Exception as e:
            error_msg = str(e)
            if (
                "api key" in error_msg.lower()
                or "authentication" in error_msg.lower()
                or "401" in error_msg
                or "403" in error_msg
            ):
                return ValidationResult(
                    is_valid=False,
                    provider="Google",
                    message="Invalid API key",
                    error_details=error_msg
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    provider="Google",
                    message="Validation error",
                    error_details=error_msg
                )

    @staticmethod
    def validate_grok(api_key: str) -> ValidationResult:
        """
        Validate Grok (xAI) API key by making a test request.

        Args:
            api_key: Grok API key to validate

        Returns:
            ValidationResult with validation status and message
        """
        try:
            import requests

            # Grok uses OpenAI-compatible API
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            # Test request to list models
            response = requests.get(
                "https://api.x.ai/v1/models",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return ValidationResult(
                    is_valid=True,
                    provider="Grok",
                    message="API key is valid"
                )
            elif response.status_code in [401, 403]:
                return ValidationResult(
                    is_valid=False,
                    provider="Grok",
                    message="Invalid API key",
                    error_details=f"HTTP {response.status_code}"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    provider="Grok",
                    message="Validation error",
                    error_details=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                provider="Grok",
                message="Validation error",
                error_details=str(e)
            )

    @staticmethod
    def validate_deepseek(api_key: str) -> ValidationResult:
        """
        Validate DeepSeek API key by making a test request.

        Args:
            api_key: DeepSeek API key to validate

        Returns:
            ValidationResult with validation status and message
        """
        try:
            import requests

            # DeepSeek uses OpenAI-compatible API
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            # Test request to list models
            response = requests.get(
                "https://api.deepseek.com/v1/models",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return ValidationResult(
                    is_valid=True,
                    provider="DeepSeek",
                    message="API key is valid"
                )
            elif response.status_code in [401, 403]:
                return ValidationResult(
                    is_valid=False,
                    provider="DeepSeek",
                    message="Invalid API key",
                    error_details=f"HTTP {response.status_code}"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    provider="DeepSeek",
                    message="Validation error",
                    error_details=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                provider="DeepSeek",
                message="Validation error",
                error_details=str(e)
            )

    @classmethod
    def validate_key(cls, provider: str, api_key: str) -> ValidationResult:
        """
        Validate API key for any provider.

        Args:
            provider: Provider name (openai, anthropic, google, grok, deepseek)
            api_key: API key to validate

        Returns:
            ValidationResult with validation status and message
        """
        validators = {
            "openai": cls.validate_openai,
            "anthropic": cls.validate_anthropic,
            "google": cls.validate_google,
            "grok": cls.validate_grok,
            "deepseek": cls.validate_deepseek,
        }

        validator = validators.get(provider.lower())
        if not validator:
            return ValidationResult(
                is_valid=False,
                provider=provider,
                message="Unknown provider",
                error_details=f"No validator for provider: {provider}"
            )

        return validator(api_key)
