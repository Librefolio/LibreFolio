"""
Tests for geographic area normalization utilities.

Tests country code normalization, weight parsing, and validation of
geographic area distributions for asset classification metadata.
"""
from decimal import Decimal

import pytest

from backend.app.utils.geo_normalization import (
    normalize_country_to_iso3,
    validate_and_normalize_geographic_area,
    )


def test_normalize_country_to_iso3():
    """Test country code normalization to ISO-3166-A3."""
    # ISO-3 passthrough
    assert normalize_country_to_iso3("USA") == "USA"
    assert normalize_country_to_iso3("GBR") == "GBR"
    assert normalize_country_to_iso3("ITA") == "ITA"

    # ISO-2 to ISO-3
    assert normalize_country_to_iso3("US") == "USA"
    assert normalize_country_to_iso3("GB") == "GBR"
    assert normalize_country_to_iso3("IT") == "ITA"

    # Country names
    assert normalize_country_to_iso3("United States") == "USA"
    assert normalize_country_to_iso3("Italy") == "ITA"
    assert normalize_country_to_iso3("United Kingdom") == "GBR"

    # Case insensitive
    assert normalize_country_to_iso3("usa") == "USA"
    assert normalize_country_to_iso3("Us") == "USA"

    # Whitespace
    assert normalize_country_to_iso3(" USA ") == "USA"
    assert normalize_country_to_iso3("  US  ") == "USA"

    # Empty string raises ValueError
    with pytest.raises(ValueError):
        normalize_country_to_iso3("")


def test_validate_and_normalize_geographic_area():
    """Test complete geographic area validation pipeline."""
    # Valid ISO-3 codes
    data = {"USA": "0.6", "GBR": "0.3", "ITA": "0.1"}
    result = validate_and_normalize_geographic_area(data)
    assert result == {
        "USA": Decimal("0.6000"),
        "GBR": Decimal("0.3000"),
        "ITA": Decimal("0.1000")
        }
    assert sum(result.values()) == Decimal("1.0")

    # ISO-2 to ISO-3 conversion
    data = {"US": 0.5, "IT": 0.5}
    result = validate_and_normalize_geographic_area(data)
    assert "USA" in result
    assert "ITA" in result
    assert "US" not in result

    # Country names normalized
    data = {"United States": 0.5, "Italy": 0.5}
    result = validate_and_normalize_geographic_area(data)
    assert "USA" in result
    assert "ITA" in result

    # Sum within tolerance (1% tolerance)
    data = {"USA": Decimal("0.5"), "ITA": Decimal("0.499999")}
    result = validate_and_normalize_geographic_area(data)
    assert sum(result.values()) == Decimal("1.0")

    # Sum within tolerance - will be renormalized to 1.0
    data = {"USA": 0.5, "ITA": 0.495}  # Sum = 0.995, within 1% of 1.0
    result = validate_and_normalize_geographic_area(data)
    assert sum(result.values()) == Decimal("1.0")

    # Sum out of tolerance (> 1% deviation)
    data = {"USA": 0.5, "ITA": 0.4}  # Sum = 0.9, 10% deviation
    with pytest.raises(ValueError):
        validate_and_normalize_geographic_area(data)

    # Single country 100%
    data = {"USA": 1.0}
    result = validate_and_normalize_geographic_area(data)
    assert result == {"USA": Decimal("1.0000")}

    # Empty dict
    with pytest.raises(ValueError):
        validate_and_normalize_geographic_area({})

    # Invalid country
    data = {"USA": 0.5, "INVALID": 0.5}
    with pytest.raises(ValueError):
        validate_and_normalize_geographic_area(data)

    # Negative weight
    data = {"USA": 1.2, "ITA": -0.2}
    with pytest.raises(ValueError):
        validate_and_normalize_geographic_area(data)

    # Duplicate after normalization
    data = {"US": 0.5, "USA": 0.5}
    with pytest.raises(ValueError):
        validate_and_normalize_geographic_area(data)

    # Zero weight allowed
    data = {"USA": 1.0, "ITA": 0.0}
    result = validate_and_normalize_geographic_area(data)
    assert result["USA"] == Decimal("1.0000")
    assert result["ITA"] == Decimal("0.0000")

    # Many countries
    data = {
        "USA": 0.25,
        "GBR": 0.25,
        "ITA": 0.25,
        "FRA": 0.25
        }
    result = validate_and_normalize_geographic_area(data)
    assert len(result) == 4
    assert sum(result.values()) == Decimal("1.0")


def test_geographic_area_edge_cases():
    """Test geographic area edge cases for Phase 6.4."""
    # Case 1: Sum = 0.999999 (within tolerance) → normalized to 1.0
    data = {"USA": "0.333333", "GBR": "0.333333", "ITA": "0.333333"}
    result = validate_and_normalize_geographic_area(data)
    total = sum(result.values())
    assert abs(total - Decimal("1.0")) < Decimal("0.0001"), f"Sum should be ~1.0, got {total}"

    # Case 2: Sum = 1.000001 (within tolerance) → normalized to 1.0
    data = {"USA": "0.333334", "GBR": "0.333334", "ITA": "0.333333"}
    result = validate_and_normalize_geographic_area(data)
    total = sum(result.values())
    assert abs(total - Decimal("1.0")) < Decimal("0.0001"), f"Sum should be ~1.0, got {total}"

    # Case 3: Sum = 0.95 (out of tolerance) → ValueError
    data = {"USA": "0.95"}
    with pytest.raises(ValueError, match="sum"):
        validate_and_normalize_geographic_area(data)

    # Case 4: Sum = 1.05 (out of tolerance) → ValueError
    data = {"USA": "1.05"}
    with pytest.raises(ValueError, match="sum"):
        validate_and_normalize_geographic_area(data)

    # Case 5: Single country weight = 1.0 → valid
    data = {"USA": "1.0"}
    result = validate_and_normalize_geographic_area(data)
    assert result == {"USA": Decimal("1.0000")}
    assert sum(result.values()) == Decimal("1.0")

    # Case 6: Empty dict → ValueError (no countries)
    data = {}
    with pytest.raises(ValueError):
        validate_and_normalize_geographic_area(data)

    # Case 7: Negative weight → ValueError
    data = {"USA": "-0.5", "GBR": "1.5"}
    with pytest.raises(ValueError, match="(negative|non-negative)"):
        validate_and_normalize_geographic_area(data)

    # Case 8: Zero weight → valid (country with 0% allocation)
    data = {"USA": "0.6", "GBR": "0.4", "ITA": "0.0"}
    result = validate_and_normalize_geographic_area(data)
    assert result["ITA"] == Decimal("0.0000")
    assert sum(result.values()) == Decimal("1.0")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
