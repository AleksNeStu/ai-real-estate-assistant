"""
Ollama model provider implementation.

Supports local Llama, Mistral, Qwen, and other open-source models via Ollama.
"""

import os
from typing import List, Optional
from langchain_community.chat_models import ChatOllama
from langchain_core.language_models import BaseChatModel

from .base import (
    LocalModelProvider,
    ModelInfo,
    ModelCapability,
)


class OllamaProvider(LocalModelProvider):
    """Ollama local model provider."""

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def display_name(self) -> str:
        return "Ollama (Local)"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        # Default to local Ollama instance
        if "base_url" not in self.config:
            self.config["base_url"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def list_models(self) -> List[ModelInfo]:
        """List popular Ollama models."""
        return [
            # Llama 3.3 Series - Latest (2024-2025)
            ModelInfo(
                id="llama3.3:70b",
                display_name="Llama 3.3 70B (Latest)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=None,  # Local, no cost
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Latest large Llama model (70B parameters) - requires 40GB+ RAM",
                recommended_for=["highest quality local", "complex tasks", "powerful hardware"]
            ),
            ModelInfo(
                id="llama3.3:8b",
                display_name="Llama 3.3 8B (Recommended)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Latest balanced Llama model (8B parameters) - requires 8GB RAM",
                recommended_for=["best balance", "general purpose", "local inference"]
            ),

            # Llama 3.2 Series - Lightweight
            ModelInfo(
                id="llama3.2:3b",
                display_name="Llama 3.2 3B (Fast)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Small, efficient Llama 3.2 model (3B parameters) - requires 4GB RAM",
                recommended_for=["fast responses", "low memory", "laptops"]
            ),
            ModelInfo(
                id="llama3.2:1b",
                display_name="Llama 3.2 1B (Ultra-fast)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Tiny but capable Llama model (1B parameters) - requires 2GB RAM",
                recommended_for=["ultra-fast", "minimal resources", "edge devices"]
            ),

            # Llama 3.1 Series - Proven
            ModelInfo(
                id="llama3.1:70b",
                display_name="Llama 3.1 70B",
                provider_name=self.display_name,
                context_window=128000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Proven large Llama model (70B parameters) - requires 40GB+ RAM",
                recommended_for=["high quality", "complex reasoning", "powerful hardware"]
            ),
            ModelInfo(
                id="llama3.1:8b",
                display_name="Llama 3.1 8B",
                provider_name=self.display_name,
                context_window=128000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Proven balanced Llama model (8B parameters) - requires 8GB RAM",
                recommended_for=["stable", "general purpose", "local inference"]
            ),

            # Other Popular Open Source Models
            ModelInfo(
                id="mistral:7b",
                display_name="Mistral 7B",
                provider_name=self.display_name,
                context_window=32768,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Efficient Mistral model (7B parameters) - requires 8GB RAM",
                recommended_for=["efficient", "code generation", "european languages"]
            ),
            ModelInfo(
                id="qwen2.5:7b",
                display_name="Qwen 2.5 7B",
                provider_name=self.display_name,
                context_window=32768,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Alibaba's Qwen model (7B parameters) - requires 8GB RAM",
                recommended_for=["multilingual", "chinese", "code", "math"]
            ),
            ModelInfo(
                id="phi3:3.8b",
                display_name="Phi-3 3.8B",
                provider_name=self.display_name,
                context_window=128000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Microsoft's small but capable model (3.8B parameters) - requires 4GB RAM",
                recommended_for=["compact", "efficient", "low resource"]
            ),
            ModelInfo(
                id="deepseek-coder:6.7b",
                display_name="DeepSeek Coder 6.7B",
                provider_name=self.display_name,
                context_window=16384,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Specialized coding model (6.7B parameters) - requires 8GB RAM",
                recommended_for=["code generation", "programming", "technical tasks"]
            ),
        ]

    def create_model(
        self,
        model_id: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        streaming: bool = True,
        **kwargs
    ) -> BaseChatModel:
        """Create Ollama model instance."""
        # Note: Ollama doesn't require pre-validation of model availability
        # as it can pull models on-demand

        base_url = self.config.get("base_url", "http://localhost:11434")

        # Create model
        return ChatOllama(
            model=model_id,
            temperature=temperature,
            num_predict=max_tokens,
            streaming=streaming,
            base_url=base_url,
            **kwargs
        )

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate Ollama connection."""
        try:
            import requests
            base_url = self.config.get("base_url", "http://localhost:11434")

            # Check if Ollama is running
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                return True, None
            else:
                return False, f"Ollama returned status code {response.status_code}"

        except requests.exceptions.ConnectionError:
            return False, (
                "Could not connect to Ollama. "
                "Make sure Ollama is running (ollama serve)"
            )
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def list_available_models(self) -> List[str]:
        """
        List models actually available/downloaded in local Ollama.

        Returns:
            List of model names
        """
        try:
            import requests
            base_url = self.config.get("base_url", "http://localhost:11434")

            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except Exception:
            return []
