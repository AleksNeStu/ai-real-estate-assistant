"""
Internationalization (i18n) module for AI Real Estate Assistant.
"""

from .translations import (
    get_text,
    get_language_name,
    get_available_languages,
    LANGUAGES,
    TRANSLATIONS
)

__all__ = [
    'get_text',
    'get_language_name',
    'get_available_languages',
    'LANGUAGES',
    'TRANSLATIONS'
]
