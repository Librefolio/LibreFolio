"""
Tests for BRIMParseError exception class.

Covers:
  - BRIMParseError.__init__ with message only
  - BRIMParseError.__init__ with message and details
  - BRIMParseError.message and .details attributes
"""

import pytest

from backend.app.services.brim_provider import BRIMParseError


class TestBRIMParseError:
    """Tests for BRIMParseError custom exception."""

    def test_message_only(self):
        """BRIMParseError with message only should have empty details."""
        err = BRIMParseError("File is empty")
        assert str(err) == "File is empty"
        assert err.message == "File is empty"
        assert err.details == {}

    def test_message_with_details(self):
        """BRIMParseError with message and details dict."""
        details = {"line": 42, "column": "date", "value": "bad-date"}
        err = BRIMParseError("Invalid date format", details=details)
        assert err.message == "Invalid date format"
        assert err.details == details
        assert err.details["line"] == 42

    def test_none_details_defaults_to_empty(self):
        """Passing details=None should default to empty dict."""
        err = BRIMParseError("Parse failed", details=None)
        assert err.details == {}

    def test_is_exception(self):
        """BRIMParseError should be an Exception subclass."""
        err = BRIMParseError("test")
        assert isinstance(err, Exception)
        with pytest.raises(BRIMParseError, match="test"):
            raise err

