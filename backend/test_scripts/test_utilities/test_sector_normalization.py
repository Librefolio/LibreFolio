"""
Tests for sector normalization utilities.

Tests the FinancialSector enum and normalization functions.
"""
import pytest

from backend.app.utils.sector_normalization import (
    FinancialSector,
    normalize_sector,
    validate_sector
    )


# ============================================================
# FinancialSector Enum Tests
# ============================================================

class TestFinancialSectorEnum:
    """Tests for FinancialSector enum."""

    def test_all_sectors_have_values(self):
        """All sectors should have string values."""
        for sector in FinancialSector:
            assert isinstance(sector.value, str)
            assert len(sector.value) > 0

    def test_expected_sectors_exist(self):
        """All expected GICS-inspired sectors should exist."""
        expected = [
            "Industrials", "Technology", "Financials", "Consumer Discretionary",
            "Health Care", "Real Estate", "Basic Materials", "Energy",
            "Consumer Staples", "Telecommunication", "Utilities", "Other"
            ]
        actual = [s.value for s in FinancialSector]
        for sector in expected:
            assert sector in actual, f"Missing sector: {sector}"

    def test_list_all_excludes_other(self):
        """list_all() should exclude OTHER."""
        sectors = FinancialSector.list_all()
        assert "Other" not in sectors
        assert len(sectors) == 11  # 12 total - 1 (Other)

    def test_list_all_with_other_includes_all(self):
        """list_all_with_other() should include all sectors."""
        sectors = FinancialSector.list_all_with_other()
        assert "Other" in sectors
        assert len(sectors) == 12


# ============================================================
# from_string Tests
# ============================================================

class TestFinancialSectorFromString:
    """Tests for FinancialSector.from_string() method."""

    @pytest.mark.parametrize("input_val,expected", [
        # Exact matches (case-insensitive)
        ("Technology", FinancialSector.TECHNOLOGY),
        ("technology", FinancialSector.TECHNOLOGY),
        ("TECHNOLOGY", FinancialSector.TECHNOLOGY),
        ("Financials", FinancialSector.FINANCIALS),
        ("financials", FinancialSector.FINANCIALS),
        ("Industrials", FinancialSector.INDUSTRIALS),
        ("Consumer Discretionary", FinancialSector.CONSUMER_DISCRETIONARY),
        ("consumer discretionary", FinancialSector.CONSUMER_DISCRETIONARY),
        ("Health Care", FinancialSector.HEALTH_CARE),
        ("Real Estate", FinancialSector.REAL_ESTATE),
        ("Basic Materials", FinancialSector.BASIC_MATERIALS),
        ("Energy", FinancialSector.ENERGY),
        ("Consumer Staples", FinancialSector.CONSUMER_STAPLES),
        ("Telecommunication", FinancialSector.TELECOMMUNICATION),
        ("Utilities", FinancialSector.UTILITIES),
        ("Other", FinancialSector.OTHER),
        ])
    def test_exact_matches(self, input_val, expected):
        """Exact sector names should be recognized."""
        assert FinancialSector.from_string(input_val) == expected

    @pytest.mark.parametrize("input_val,expected", [
        # Aliases
        ("healthcare", FinancialSector.HEALTH_CARE),  # No space
        ("materials", FinancialSector.BASIC_MATERIALS),  # Short form
        ("telecom", FinancialSector.TELECOMMUNICATION),  # Short form
        ])
    def test_aliases(self, input_val, expected):
        """Aliases should be recognized."""
        assert FinancialSector.from_string(input_val) == expected

    @pytest.mark.parametrize("input_val", [
        # Unknown sectors should map to OTHER
        "Unknown",
        "Software",
        "Hardware",
        "Banking",
        "Insurance",
        "Aerospace",
        "Gaming",
        "Automotive",
        "SomeRandomSector",
        ])
    def test_unknown_sectors_map_to_other(self, input_val):
        """Unknown sector names should map to OTHER."""
        result = FinancialSector.from_string(input_val)
        assert result == FinancialSector.OTHER

    def test_empty_string_maps_to_other(self):
        """Empty string should map to OTHER."""
        assert FinancialSector.from_string("") == FinancialSector.OTHER

    def test_none_maps_to_other(self):
        """None should map to OTHER."""
        assert FinancialSector.from_string(None) == FinancialSector.OTHER

    def test_whitespace_trimmed(self):
        """Whitespace should be trimmed."""
        assert FinancialSector.from_string("  Technology  ") == FinancialSector.TECHNOLOGY
        assert FinancialSector.from_string("\tFinancials\n") == FinancialSector.FINANCIALS


# ============================================================
# normalize_sector Function Tests
# ============================================================

class TestNormalizeSector:
    """Tests for normalize_sector() function."""

    def test_returns_string_value(self):
        """Should return the string value, not enum."""
        result = normalize_sector("Technology")
        assert result == "Technology"
        assert isinstance(result, str)

    def test_case_insensitive(self):
        """Should be case-insensitive."""
        assert normalize_sector("technology") == "Technology"
        assert normalize_sector("TECHNOLOGY") == "Technology"
        assert normalize_sector("TeCHNoLoGy") == "Technology"

    def test_alias_normalization(self):
        """Should normalize aliases to standard names."""
        assert normalize_sector("healthcare") == "Health Care"
        assert normalize_sector("materials") == "Basic Materials"
        assert normalize_sector("telecom") == "Telecommunication"

    def test_unknown_returns_other(self):
        """Unknown sectors should return 'Other'."""
        assert normalize_sector("SomeUnknownSector") == "Other"
        assert normalize_sector("Banking") == "Other"


# ============================================================
# validate_sector Function Tests
# ============================================================

class TestValidateSector:
    """Tests for validate_sector() function."""

    def test_valid_sectors_return_true(self):
        """Known sectors should return True."""
        assert validate_sector("Technology") is True
        assert validate_sector("Financials") is True
        assert validate_sector("healthcare") is True  # Alias

    def test_other_returns_false(self):
        """'Other' should return False (not a recognized sector)."""
        assert validate_sector("Other") is False
        assert validate_sector("other") is False

    def test_unknown_returns_false(self):
        """Unknown sectors should return False."""
        assert validate_sector("Banking") is False
        assert validate_sector("Unknown") is False


# ============================================================
# Edge Cases
# ============================================================

class TestEdgeCases:
    """Edge case tests."""

    def test_sector_enum_is_str_enum(self):
        """FinancialSector should be usable as string."""
        sector = FinancialSector.TECHNOLOGY
        # Should be comparable to string
        assert sector == "Technology"
        # Should be usable in f-strings
        assert f"{sector.value}" == "Technology"

    def test_sector_in_dict_key(self):
        """Sectors should work as dict keys."""
        data = {
            FinancialSector.TECHNOLOGY: 0.5,
            FinancialSector.FINANCIALS: 0.5
            }
        assert data[FinancialSector.TECHNOLOGY] == 0.5
        # Also works with string lookup since it's a str enum
        assert data["Technology"] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
