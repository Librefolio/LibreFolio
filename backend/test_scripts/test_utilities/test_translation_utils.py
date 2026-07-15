"""
Tests for translation utilities.
"""

from backend.app.utils.translation_utils import get_babel_locale


def test_get_babel_locale_returns_requested_language():
    """Valid language code returns matching Babel locale."""
    locale = get_babel_locale("it")

    assert locale.language == "it"


def test_get_babel_locale_falls_back_to_english():
    """Invalid language code falls back to English locale."""
    locale = get_babel_locale("invalid_lang")

    assert locale.language == "en"
