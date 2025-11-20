"""
Tests for geographic area normalization utilities.

Tests country code normalization, weight parsing, and validation of
geographic area distributions for asset classification metadata.
"""
from decimal import Decimal

from backend.app.utils.geo_normalization import (
    normalize_country_to_iso3,
    parse_decimal_weight,
    quantize_weight,
    validate_and_normalize_geographic_area,
    )


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def print_test(name, passed=True):
    """Print test result."""
    status = "✅" if passed else "❌"
    print(f"{status} {name}")


def test_normalize_country_to_iso3():
    """Test country code normalization to ISO-3166-A3."""
    print_section("Test 1: Country Code Normalization")

    # ISO-3 passthrough
    assert normalize_country_to_iso3("USA") == "USA"
    assert normalize_country_to_iso3("GBR") == "GBR"
    assert normalize_country_to_iso3("ITA") == "ITA"
    print_test("ISO-3 passthrough (USA, GBR, ITA)")

    # ISO-2 to ISO-3
    assert normalize_country_to_iso3("US") == "USA"
    assert normalize_country_to_iso3("GB") == "GBR"
    assert normalize_country_to_iso3("IT") == "ITA"
    print_test("ISO-2 to ISO-3 conversion (US->USA, GB->GBR, IT->ITA)")

    # Country names
    assert normalize_country_to_iso3("United States") == "USA"
    assert normalize_country_to_iso3("Italy") == "ITA"
    assert normalize_country_to_iso3("United Kingdom") == "GBR"
    print_test("Country names to ISO-3 (fuzzy matching)")

    # Case insensitive
    assert normalize_country_to_iso3("usa") == "USA"
    assert normalize_country_to_iso3("Us") == "USA"
    print_test("Case insensitive handling")

    # Whitespace
    assert normalize_country_to_iso3(" USA ") == "USA"
    assert normalize_country_to_iso3("  US  ") == "USA"
    print_test("Whitespace trimming")

    # Invalid codes
    try:
        normalize_country_to_iso3("XX")
        print_test("Invalid code raises ValueError", False)
    except ValueError:
        print_test("Invalid code raises ValueError")

    # Empty string
    try:
        normalize_country_to_iso3("")
        print_test("Empty string raises ValueError", False)
    except ValueError:
        print_test("Empty string raises ValueError")


def test_parse_decimal_weight():
    """Test weight parsing to Decimal."""
    print_section("Test 2: Decimal Weight Parsing")

    # String to Decimal
    assert parse_decimal_weight("0.6") == Decimal("0.6")
    assert parse_decimal_weight("0.333333") == Decimal("0.333333")
    print_test("String to Decimal")

    # Float to Decimal
    result = parse_decimal_weight(0.6)
    assert isinstance(result, Decimal)
    print_test("Float to Decimal")

    # Int to Decimal
    assert parse_decimal_weight(1) == Decimal("1")
    assert parse_decimal_weight(0) == Decimal("0")
    print_test("Int to Decimal")

    # Decimal passthrough
    value = Decimal("0.6")
    assert parse_decimal_weight(value) == value
    print_test("Decimal passthrough")


def test_quantize_weight():
    """Test weight quantization to 4 decimals."""
    print_section("Test 3: Weight Quantization")

    # Quantize to 4 decimals
    assert quantize_weight(Decimal("0.123456789")) == Decimal("0.1235")
    assert quantize_weight(Decimal("0.60375")) == Decimal("0.6038")
    print_test("Quantize to 4 decimals")

    # ROUND_HALF_EVEN
    assert quantize_weight(Decimal("0.12345")) == Decimal("0.1234")
    assert quantize_weight(Decimal("0.12355")) == Decimal("0.1236")
    print_test("ROUND_HALF_EVEN rounding mode")

    # Fewer decimals padded
    assert quantize_weight(Decimal("0.6")) == Decimal("0.6000")
    print_test("Padding to 4 decimals")


def test_validate_and_normalize_geographic_area():
    """Test complete geographic area validation pipeline."""
    print_section("Test 4: Geographic Area Validation")

    # Valid ISO-3 codes
    data = {"USA": "0.6", "GBR": "0.3", "ITA": "0.1"}
    result = validate_and_normalize_geographic_area(data)
    assert result == {
        "USA": Decimal("0.6000"),
        "GBR": Decimal("0.3000"),
        "ITA": Decimal("0.1000")
        }
    assert sum(result.values()) == Decimal("1.0")
    print_test("Valid ISO-3 codes with exact sum")

    # ISO-2 to ISO-3 conversion
    data = {"US": 0.5, "IT": 0.5}
    result = validate_and_normalize_geographic_area(data)
    assert "USA" in result
    assert "ITA" in result
    assert "US" not in result
    print_test("ISO-2 to ISO-3 conversion in validation")

    # Country names normalized
    data = {"United States": 0.5, "Italy": 0.5}
    result = validate_and_normalize_geographic_area(data)
    assert "USA" in result
    assert "ITA" in result
    print_test("Country names normalized")

    # Sum within tolerance
    data = {"USA": Decimal("0.5"), "ITA": Decimal("0.499999")}
    result = validate_and_normalize_geographic_area(data)
    assert sum(result.values()) == Decimal("1.0")
    print_test("Sum within tolerance renormalized")

    # Sum out of tolerance
    data = {"USA": 0.5, "ITA": 0.4}  # Sum = 0.9
    try:
        validate_and_normalize_geographic_area(data)
        print_test("Sum out of tolerance raises ValueError", False)
    except ValueError:
        print_test("Sum out of tolerance raises ValueError")

    # Single country 100%
    data = {"USA": 1.0}
    result = validate_and_normalize_geographic_area(data)
    assert result == {"USA": Decimal("1.0000")}
    print_test("Single country with 100% weight")

    # Empty dict
    try:
        validate_and_normalize_geographic_area({})
        print_test("Empty dict raises ValueError", False)
    except ValueError:
        print_test("Empty dict raises ValueError")

    # Invalid country
    data = {"USA": 0.5, "INVALID": 0.5}
    try:
        validate_and_normalize_geographic_area(data)
        print_test("Invalid country raises ValueError", False)
    except ValueError:
        print_test("Invalid country raises ValueError")

    # Negative weight
    data = {"USA": 1.2, "ITA": -0.2}
    try:
        validate_and_normalize_geographic_area(data)
        print_test("Negative weight raises ValueError", False)
    except ValueError:
        print_test("Negative weight raises ValueError")

    # Duplicate after normalization
    data = {"US": 0.5, "USA": 0.5}
    try:
        validate_and_normalize_geographic_area(data)
        print_test("Duplicate country raises ValueError", False)
    except ValueError:
        print_test("Duplicate country raises ValueError")

    # Zero weight allowed
    data = {"USA": 1.0, "ITA": 0.0}
    result = validate_and_normalize_geographic_area(data)
    assert result["USA"] == Decimal("1.0000")
    assert result["ITA"] == Decimal("0.0000")
    print_test("Zero weight allowed")

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
    print_test("Many countries with fractional weights")


def test_geographic_area_edge_cases():
    """Test geographic area edge cases for Phase 6.4."""
    print_section("Test 5: Geographic Area Edge Cases (Phase 6.4)")

    # Case 1: Sum = 0.999999 (within tolerance) → normalized to 1.0
    data = {"USA": "0.333333", "GBR": "0.333333", "ITA": "0.333333"}
    result = validate_and_normalize_geographic_area(data)
    total = sum(result.values())
    assert abs(total - Decimal("1.0")) < Decimal("0.0001"), f"Sum should be ~1.0, got {total}"
    print_test("Edge case 1: Sum 0.999999 (within tolerance) normalized")

    # Case 2: Sum = 1.000001 (within tolerance) → normalized to 1.0
    data = {"USA": "0.333334", "GBR": "0.333334", "ITA": "0.333333"}
    result = validate_and_normalize_geographic_area(data)
    total = sum(result.values())
    assert abs(total - Decimal("1.0")) < Decimal("0.0001"), f"Sum should be ~1.0, got {total}"
    print_test("Edge case 2: Sum 1.000001 (within tolerance) normalized")

    # Case 3: Sum = 0.95 (out of tolerance) → ValueError
    try:
        data = {"USA": "0.95"}
        validate_and_normalize_geographic_area(data)
        print_test("Edge case 3: Sum 0.95 should raise ValueError", False)
    except ValueError as e:
        assert "sum" in str(e).lower()
        print_test("Edge case 3: Sum 0.95 raises ValueError")

    # Case 4: Sum = 1.05 (out of tolerance) → ValueError
    try:
        data = {"USA": "1.05"}
        validate_and_normalize_geographic_area(data)
        print_test("Edge case 4: Sum 1.05 should raise ValueError", False)
    except ValueError as e:
        assert "sum" in str(e).lower()
        print_test("Edge case 4: Sum 1.05 raises ValueError")

    # Case 5: Single country weight = 1.0 → valid
    data = {"USA": "1.0"}
    result = validate_and_normalize_geographic_area(data)
    assert result == {"USA": Decimal("1.0000")}
    assert sum(result.values()) == Decimal("1.0")
    print_test("Edge case 5: Single country with 100% allocation valid")

    # Case 6: Empty dict → ValueError (no countries)
    try:
        data = {}
        validate_and_normalize_geographic_area(data)
        print_test("Edge case 6: Empty dict should raise ValueError", False)
    except ValueError as e:
        assert "empty" in str(e).lower() or "no countries" in str(e).lower()
        print_test("Edge case 6: Empty dict raises ValueError")

    # Case 7: Negative weight → ValueError
    try:
        data = {"USA": "-0.5", "GBR": "1.5"}
        validate_and_normalize_geographic_area(data)
        print_test("Edge case 7: Negative weight should raise ValueError", False)
    except ValueError as e:
        assert "negative" in str(e).lower() or "non-negative" in str(e).lower()
        print_test("Edge case 7: Negative weight raises ValueError")

    # Case 8: Zero weight → valid (country with 0% allocation)
    data = {"USA": "0.6", "GBR": "0.4", "ITA": "0.0"}
    result = validate_and_normalize_geographic_area(data)
    assert result["ITA"] == Decimal("0.0000")
    assert sum(result.values()) == Decimal("1.0")
    print_test("Edge case 8: Zero weight valid (0% allocation)")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  Geographic Area Normalization - Test Suite")
    print("=" * 60)

    try:
        test_normalize_country_to_iso3()
        test_parse_decimal_weight()
        test_quantize_weight()
        test_validate_and_normalize_geographic_area()
        test_geographic_area_edge_cases()

        print("\n" + "=" * 60)
        print("  ✅ All tests passed!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
