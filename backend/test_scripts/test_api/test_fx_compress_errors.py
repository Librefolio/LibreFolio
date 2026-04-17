"""Tests for _compress_convert_errors in fx.py API module."""

from backend.app.api.v1.fx import _compress_convert_errors


class TestCompressConvertErrors:
    """Test error compression for FX conversion errors."""

    def test_empty_list(self):
        assert _compress_convert_errors([]) == []

    def test_single_error_kept_as_is(self):
        errors = ["Conversion 1: No FX rate found for CHF/JPY on or before 2026-03-01. Please sync rates."]
        result = _compress_convert_errors(errors)
        assert len(result) == 1
        assert "CHF/JPY" in result[0]
        assert "2026-03-01" in result[0]

    def test_multiple_dates_compressed(self):
        errors = [
            "Conversion 1: No FX rate found for CHF/JPY on or before 2026-03-01. Please sync rates.",
            "Conversion 2: No FX rate found for CHF/JPY on or before 2026-03-02. Please sync rates.",
            "Conversion 3: No FX rate found for CHF/JPY on or before 2026-03-03. Please sync rates.",
        ]
        result = _compress_convert_errors(errors)
        assert len(result) == 1
        assert "3 dates" in result[0]
        assert "2026-03-01" in result[0]
        assert "2026-03-03" in result[0]

    def test_different_pairs_separate(self):
        errors = [
            "Conversion 1: No FX rate found for CHF/JPY on or before 2026-03-01. Please sync.",
            "Conversion 2: No FX rate found for EUR/USD on or before 2026-03-01. Please sync.",
        ]
        result = _compress_convert_errors(errors)
        assert len(result) == 2

    def test_non_matching_errors_preserved(self):
        errors = [
            "Some other error",
            "Conversion 1: No FX rate found for CHF/JPY on or before 2026-03-01. Please sync.",
        ]
        result = _compress_convert_errors(errors)
        assert len(result) == 2
        assert "Some other error" in result

    def test_mixed_matching_and_non_matching(self):
        errors = [
            "Conversion 1: No FX rate found for CHF/JPY on or before 2026-03-01. Please sync.",
            "Conversion 2: No FX rate found for CHF/JPY on or before 2026-03-02. Please sync.",
            "Unrelated error message",
        ]
        result = _compress_convert_errors(errors)
        assert len(result) == 2  # 1 compressed + 1 other
        compressed = [r for r in result if "2 dates" in r]
        assert len(compressed) == 1
