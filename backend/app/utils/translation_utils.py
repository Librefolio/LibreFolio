"""
Translation and localization utilities for multi-language support.

Provides common functions for translating country names, currency names,
and normalizing user input to standard ISO formats.

Uses Babel for localization with automatic fallback to English.

⚠️ LANGUAGE CODE SYNC: The language codes accepted here ('en', 'it', 'fr', 'es', etc.)
MUST match the SUPPORTED_LOCALES defined in the frontend (frontend/src/lib/i18n/index.ts).
The frontend passes these codes as `?language=XX` to utility endpoints so Babel can return
correctly localized currency names, country names, and symbols.
Babel supports 1067+ locales, so adding new languages is always safe on this side.
When adding a new language to the frontend, no backend changes are needed — just verify
the code is a valid ISO 639-1 identifier that Babel recognizes.
"""

import structlog
from babel import Locale

logger = structlog.get_logger(__name__)


def get_babel_locale(language: str) -> Locale:
    """
    Get Babel Locale object for given language code.
    Falls back to English if language not supported.

    Args:
        language: ISO 639-1 language code (e.g., 'en', 'it', 'fr', 'es')

    Returns:
        Babel Locale object

    Examples:
        >>> locale = get_babel_locale('it')
        >>> locale.language
        'it'
        >>> locale = get_babel_locale('invalid_lang')  # Falls back to 'en'
        >>> locale.language
        'en'
    """
    try:
        return Locale.parse(language)
    except Exception as e:
        logger.warning(
            "Language not supported, falling back to English", language=language, error=str(e)
            )
        return Locale.parse("en")
