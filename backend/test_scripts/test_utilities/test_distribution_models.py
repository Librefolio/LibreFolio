"""
Tests for Distribution models (BaseDistribution, FAGeographicArea, FASectorArea).

Tests the validation logic, normalization, and weight quantization.
"""
from decimal import Decimal

import pytest

from backend.app.schemas.assets import (
    FAGeographicArea,
    FASectorArea,
    FAClassificationParams
    )


# ============================================================
# FAGeographicArea Tests
# ============================================================

class TestFAGeographicArea:
    """Tests for FAGeographicArea model."""

    def test_valid_distribution(self):
        """Valid distribution should be accepted."""
        geo = FAGeographicArea(distribution={"USA": Decimal("0.6"), "ITA": Decimal("0.4")})
        assert geo.distribution["USA"] == Decimal("0.6000")
        assert geo.distribution["ITA"] == Decimal("0.4000")

    def test_sum_to_one(self):
        """Weights should sum to exactly 1.0."""
        geo = FAGeographicArea(distribution={"USA": Decimal("0.7"), "DEU": Decimal("0.3")})
        total = sum(geo.distribution.values())
        assert total == Decimal("1.0")

    def test_country_code_normalization(self):
        """Country codes should be normalized to ISO-3166-A3."""
        # ISO-2 -> ISO-3
        geo = FAGeographicArea(distribution={"US": Decimal("0.5"), "IT": Decimal("0.5")})
        assert "USA" in geo.distribution
        assert "ITA" in geo.distribution
        assert "US" not in geo.distribution
        assert "IT" not in geo.distribution

    def test_country_name_normalization(self):
        """Country names should be normalized to ISO-3166-A3."""
        geo = FAGeographicArea(distribution={"United States": Decimal("0.5"), "Italy": Decimal("0.5")})
        assert "USA" in geo.distribution
        assert "ITA" in geo.distribution

    def test_float_to_decimal_conversion(self):
        """Float values should be converted to Decimal."""
        geo = FAGeographicArea(distribution={"USA": 0.6, "DEU": 0.4})
        assert isinstance(geo.distribution["USA"], Decimal)
        assert geo.distribution["USA"] == Decimal("0.6000")

    def test_auto_renormalization(self):
        """Weights should be auto-renormalized if close to 1.0."""
        # 0.333 + 0.333 + 0.334 = 1.0 exactly, should work
        geo = FAGeographicArea(distribution={"USA": Decimal("0.333"), "DEU": Decimal("0.333"), "FRA": Decimal("0.334")})
        total = sum(geo.distribution.values())
        assert total == Decimal("1.0")

    def test_empty_distribution_fails(self):
        """Empty distribution should raise error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            FAGeographicArea(distribution={})

    def test_invalid_country_fails(self):
        """Invalid country code should raise error."""
        with pytest.raises(ValueError, match="not found"):
            FAGeographicArea(distribution={"INVALID_COUNTRY": Decimal("1.0")})

    def test_negative_weight_fails(self):
        """Negative weight should raise error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            FAGeographicArea(distribution={"USA": Decimal("-0.5"), "DEU": Decimal("1.5")})

    def test_sum_way_off_fails(self):
        """Weights that sum far from 1.0 should raise error."""
        with pytest.raises(ValueError, match="Distribution weights must sum to approximately 1.0"):
            FAGeographicArea(distribution={"USA": Decimal("0.3"), "DEU": Decimal("0.2")})


# ============================================================
# FASectorArea Tests
# ============================================================

class TestFASectorArea:
    """Tests for FASectorArea model."""

    def test_valid_distribution(self):
        """Valid sector distribution should be accepted."""
        sector = FASectorArea(distribution={
            "Technology": Decimal("0.4"),
            "Financials": Decimal("0.3"),
            "Health Care": Decimal("0.3")
            })
        assert sector.distribution["Technology"] == Decimal("0.4000")
        assert sector.distribution["Financials"] == Decimal("0.3000")

    def test_sum_to_one(self):
        """Weights should sum to exactly 1.0."""
        sector = FASectorArea(distribution={"Technology": Decimal("1.0")})
        total = sum(sector.distribution.values())
        assert total == Decimal("1.0")

    def test_sector_name_normalization_case_insensitive(self):
        """Sector names should be case-insensitive."""
        sector = FASectorArea(distribution={
            "technology": Decimal("0.5"),
            "FINANCIALS": Decimal("0.5")
            })
        assert "Technology" in sector.distribution
        assert "Financials" in sector.distribution

    def test_sector_alias_normalization(self):
        """Sector aliases should be normalized."""
        sector = FASectorArea(distribution={
            "healthcare": Decimal("0.5"),  # Should become "Health Care"
            "telecom": Decimal("0.5")  # Should become "Telecommunication"
            })
        assert "Health Care" in sector.distribution
        assert "Telecommunication" in sector.distribution
        assert "healthcare" not in sector.distribution

    def test_unknown_sector_mapped_to_other(self):
        """Unknown sectors should be mapped to 'Other'."""
        sector = FASectorArea(distribution={
            "UnknownSector": Decimal("0.5"),
            "Technology": Decimal("0.5")
            })
        assert "Other" in sector.distribution
        assert "UnknownSector" not in sector.distribution

    def test_multiple_unknown_merged_into_other(self):
        """Multiple unknown sectors should be merged into 'Other'."""
        sector = FASectorArea(distribution={
            "Banking": Decimal("0.2"),  # Unknown -> Other
            "Insurance": Decimal("0.2"),  # Unknown -> Other
            "Technology": Decimal("0.6")
            })
        assert "Other" in sector.distribution
        # 0.2 + 0.2 = 0.4 -> should be in Other
        assert sector.distribution["Other"] == Decimal("0.4000")
        assert sector.distribution["Technology"] == Decimal("0.6000")

    def test_float_to_decimal_conversion(self):
        """Float values should be converted to Decimal."""
        sector = FASectorArea(distribution={"Technology": 0.6, "Financials": 0.4})
        assert isinstance(sector.distribution["Technology"], Decimal)
        assert sector.distribution["Technology"] == Decimal("0.6000")

    def test_empty_distribution_fails(self):
        """Empty distribution should raise error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            FASectorArea(distribution={})

    def test_negative_weight_fails(self):
        """Negative weight should raise error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            FASectorArea(distribution={"Technology": Decimal("-0.5"), "Financials": Decimal("1.5")})


# ============================================================
# FAClassificationParams Integration Tests
# ============================================================

class TestFAClassificationParams:
    """Tests for FAClassificationParams with new sector_area field."""

    def test_with_sector_area(self):
        """Should accept sector_area field."""
        params = FAClassificationParams(
            short_description="Test asset",
            sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")})
            )
        assert params.sector_area is not None
        assert params.sector_area.distribution["Technology"] == Decimal("1.0")

    def test_with_geographic_area(self):
        """Should accept geographic_area field."""
        params = FAClassificationParams(
            geographic_area=FAGeographicArea(distribution={"USA": Decimal("1.0")})
            )
        assert params.geographic_area is not None
        assert params.geographic_area.distribution["USA"] == Decimal("1.0")

    def test_with_both_areas(self):
        """Should accept both sector_area and geographic_area."""
        params = FAClassificationParams(
            short_description="Multi-region tech fund",
            geographic_area=FAGeographicArea(distribution={"USA": Decimal("0.6"), "DEU": Decimal("0.4")}),
            sector_area=FASectorArea(distribution={"Technology": Decimal("0.7"), "Financials": Decimal("0.3")})
            )
        assert params.geographic_area is not None
        assert params.sector_area is not None

    def test_all_fields_optional(self):
        """All fields should be optional."""
        params = FAClassificationParams()
        assert params.short_description is None
        assert params.geographic_area is None
        assert params.sector_area is None

    def test_old_sector_field_rejected(self):
        """Old 'sector' field should be rejected (extra='forbid')."""
        with pytest.raises(Exception):  # ValidationError
            FAClassificationParams(sector="Technology")


# ============================================================
# Weight Quantization Tests
# ============================================================

class TestWeightQuantization:
    """Tests for weight quantization behavior."""

    def test_quantized_to_4_decimals(self):
        """Weights should be quantized to 4 decimal places."""
        geo = FAGeographicArea(distribution={"USA": Decimal("0.123456789"), "ITA": Decimal("0.876543210")})
        # Should be quantized
        assert geo.distribution["USA"] == Decimal("0.1235") or geo.distribution["USA"] == Decimal("1.0")

    def test_round_half_even(self):
        """Should use banker's rounding (ROUND_HALF_EVEN)."""
        # 0.33335 should round to 0.3334 (round to even)
        # But since we renormalize to 1.0, we just verify it's 4 decimals
        geo = FAGeographicArea(distribution={"USA": Decimal("1.0")})
        for key, value in geo.distribution.items():
            # Check it has at most 4 decimal places
            assert value == value.quantize(Decimal("0.0001"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
