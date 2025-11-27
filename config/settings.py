"""
Application settings and configuration.

This module provides centralized configuration management for the application.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    """Application settings."""

    # Application
    app_title: str = "AI Real Estate Assistant - Modern"
    app_icon: str = "🏠"
    version: str = "3.0.0"

    # Paths
    data_dir: Path = Field(default_factory=lambda: Path("./data"))
    chroma_dir: Path = Field(default_factory=lambda: Path("./chroma_db"))
    assets_dir: Path = Field(default_factory=lambda: Path("./assets"))

    # API Keys (loaded from environment)
    openai_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    anthropic_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )
    google_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY")
    )
    grok_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("XAI_API_KEY")
    )
    deepseek_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY")
    )

    # Model Defaults
    default_temperature: float = 0.0
    default_max_tokens: int = 4096
    default_k_results: int = 5

    # Vector Store
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Data Loading
    max_properties: int = 2000
    batch_size: int = 100

    # UI Settings
    page_layout: str = "wide"
    initial_sidebar_state: str = "expanded"

    # Dataset URLs
    default_datasets: list = Field(
        default_factory=lambda: [
            "https://raw.githubusercontent.com/AleksNeStu/projects-data/main/dataset/pl/apartments_pl_2024_01.csv",
            "https://raw.githubusercontent.com/AleksNeStu/projects-data/main/dataset/pl/apartments_pl_2024_02.csv",
            "https://raw.githubusercontent.com/AleksNeStu/projects-data/main/dataset/pl/apartments_pl_2024_03.csv",
            "https://raw.githubusercontent.com/AleksNeStu/projects-data/main/dataset/pl/apartments_pl_2024_04.csv",
            "https://raw.githubusercontent.com/AleksNeStu/projects-data/main/dataset/pl/apartments_pl_2024_05.csv",
        ]
    )

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = AppSettings()


def get_settings() -> AppSettings:
    """
    Get application settings.

    Returns:
        AppSettings instance
    """
    return settings


def update_api_key(provider: str, api_key: str):
    """
    Update API key for a provider.

    Args:
        provider: Provider name ('openai', 'anthropic', 'google', 'grok', 'deepseek')
        api_key: API key value
    """
    global settings

    if provider == "openai":
        settings.openai_api_key = api_key
        os.environ["OPENAI_API_KEY"] = api_key
    elif provider == "anthropic":
        settings.anthropic_api_key = api_key
        os.environ["ANTHROPIC_API_KEY"] = api_key
    elif provider == "google":
        settings.google_api_key = api_key
        os.environ["GOOGLE_API_KEY"] = api_key
    elif provider == "grok":
        settings.grok_api_key = api_key
        os.environ["XAI_API_KEY"] = api_key
    elif provider == "deepseek":
        settings.deepseek_api_key = api_key
        os.environ["DEEPSEEK_API_KEY"] = api_key

    # Clear provider cache to pick up new API key
    from models.provider_factory import ModelProviderFactory
    ModelProviderFactory.clear_cache()
