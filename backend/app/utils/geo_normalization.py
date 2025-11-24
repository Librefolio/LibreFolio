"""
Geographic area normalization utilities for LibreFolio.

Provides functions to normalize country codes to ISO-3166-A3 format and
validate geographic area weight distributions for asset classification.

Usage:
    from backend.app.utils.geo_normalization import validate_and_normalize_geographic_area

    # Normalize and validate geographic area
    data = {"USA": "0.6", "Italy": 0.3, "GB": 0.1}
    normalized = validate_and_normalize_geographic_area(data)
    # Returns: {"USA": Decimal("0.6000"), "ITA": Decimal("0.3000"), "GBR": Decimal("0.1000")}

Key Features:
- Country code normalization (name/ISO-2/ISO-3 → ISO-3166-A3)
- Weight parsing (int/float/str → Decimal)
- Sum validation (must equal 1.0 within tolerance)
- Automatic renormalization (adjusts smallest weight if sum != 1.0)
- Quantization to 4 decimals (ROUND_HALF_EVEN)
"""
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any

import pycountry

from backend.app.utils.financial_math import parse_decimal_value

# Tolerance for sum validation (1e-6 = 0.000001)
SUM_TOLERANCE = Decimal("0.000001")

# Target sum for geographic area weights
TARGET_SUM = Decimal("1.0")

# Quantization template for 4 decimals
WEIGHT_QUANTIZER = Decimal("0.0001")

# TODO: aggiungere un endpoint API per passare country name e restituire una lista di ISO3,
#  dico lista perchè nel caso di eur mi aspetto che restituisca DEU, FRA, ITA, ESP, etc. o per ASIA restituire CHN, JPN, IND, KOR, etc.
def normalize_country_to_iso3(country_input: str) -> str:
    """
    Normalize country code/name to ISO-3166-A3 format.

    Accepts:
    - ISO-3166-A3 codes (e.g., USA, GBR, ITA) - returned as-is if valid
    - ISO-3166-A2 codes (e.g., US, GB, IT) - converted to A3
    - Country names (e.g., United States, Italy) - fuzzy matched to A3

    Args:
        country_input: Country code or name (any format)

    Returns:
        ISO-3166-A3 code (uppercase, 3 letters)

    Raises:
        ValueError: If country not found or ambiguous

    Examples:
        >>> normalize_country_to_iso3("USA")
        "USA"
        >>> normalize_country_to_iso3("US")
        "USA"
        >>> normalize_country_to_iso3("United States")
        "USA"
        >>> normalize_country_to_iso3("Italy")
        "ITA"
    """
    if not country_input or not isinstance(country_input, str):
        raise ValueError(f"Invalid country input: {country_input} (must be non-empty string)")

    # Normalize input
    country_str = country_input.strip().upper()

    if not country_str:
        raise ValueError("Country input cannot be empty or whitespace")

    # Try ISO-3166-A3 first (most common case)
    if len(country_str) == 3:
        try:
            country = pycountry.countries.get(alpha_3=country_str)
            if country:
                return country.alpha_3
        except (KeyError, AttributeError):
            pass

    # Try ISO-3166-A2
    if len(country_str) == 2:
        try:
            country = pycountry.countries.get(alpha_2=country_str)
            if country:
                return country.alpha_3
        except (KeyError, AttributeError):
            pass

    # Try fuzzy name search (case-insensitive)
    try:
        results = pycountry.countries.search_fuzzy(country_input)
        if results and len(results) > 0:
            # Return first match (best match)
            return results[0].alpha_3
    except LookupError:
        pass

    # Not found
    raise ValueError(
        f"Country '{country_input}' not found. "
        f"Please use ISO-3166-A2 (e.g., US), ISO-3166-A3 (e.g., USA), or full country name."
        )


def parse_decimal_weight(value: Any) -> Decimal:
    """
    Parse weight value to Decimal.

    Wrapper around parse_decimal_value() from financial_math for consistency.

    Args:
        value: Weight value (int, float, str, or Decimal)

    Returns:
        Decimal representation

    Raises:
        ValueError: If value cannot be parsed

    Examples:
        >>> parse_decimal_weight("0.6")
        Decimal("0.6")
        >>> parse_decimal_weight(0.3)
        Decimal("0.3")
        >>> parse_decimal_weight(Decimal("0.1"))
        Decimal("0.1")
    """
    try:
        return parse_decimal_value(value)
    except Exception as e:
        raise ValueError(f"Invalid weight value '{value}': {e}")


def quantize_weight(value: Decimal) -> Decimal:
    """
    Quantize weight to 4 decimals using ROUND_HALF_EVEN.

    Args:
        value: Decimal weight value

    Returns:
        Quantized Decimal (4 decimal places)

    Examples:
        >>> quantize_weight(Decimal("0.60375"))
        Decimal("0.6038")
        >>> quantize_weight(Decimal("0.333333"))
        Decimal("0.3333")
    """
    return value.quantize(WEIGHT_QUANTIZER, rounding=ROUND_HALF_EVEN)


def validate_and_normalize_geographic_area(data: dict[str, Any]) -> dict[str, Decimal]:
    """
    Validate and normalize geographic area weight distribution.

    This is the main validation function that:
    1. Normalizes all country codes to ISO-3166-A3
    2. Parses all weights to Decimal
    3. Validates sum is within tolerance of 1.0
    4. Quantizes weights to 4 decimals
    5. Renormalizes if sum != 1.0 (adjusts smallest weight)

    Args:
        data: Dict of country codes/names to weights
              Keys: Any format (ISO-2, ISO-3, name)
              Values: Numeric (int, float, str, Decimal)

    Returns:
        Dict of ISO-3166-A3 codes to quantized Decimal weights
        Guaranteed to sum to exactly 1.0

    Raises:
        ValueError: If validation fails (empty, invalid codes, sum out of tolerance, negative weights)

    Examples:
        >>> validate_and_normalize_geographic_area({"USA": 0.6, "ITA": 0.3, "GBR": 0.1})
        {"USA": Decimal("0.6000"), "ITA": Decimal("0.3000"), "GBR": Decimal("0.1000")}

        >>> validate_and_normalize_geographic_area({"US": "0.5", "Italy": "0.5"})
        {"USA": Decimal("0.5000"), "ITA": Decimal("0.5000")}

        >>> validate_and_normalize_geographic_area({"USA": 0.333, "ITA": 0.333, "GBR": 0.334})
        {"USA": Decimal("0.3330"), "ITA": Decimal("0.3330"), "GBR": Decimal("0.3340")}
    """
    if not data or not isinstance(data, dict):
        raise ValueError("Geographic area must be a non-empty dictionary")

    if len(data) == 0:
        raise ValueError("Geographic area must contain at least one country")

    # Step 1: Normalize country codes and parse weights
    normalized: dict[str, Decimal] = {}

    for country_input, weight_value in data.items():
        # Normalize country code
        try:
            iso3_code = normalize_country_to_iso3(country_input)
        except ValueError as e:
            raise ValueError(f"Invalid country '{country_input}': {e}")

        # Check for duplicates (after normalization)
        if iso3_code in normalized:
            raise ValueError(
                f"Duplicate country after normalization: '{country_input}' → {iso3_code} "
                f"(already present in geographic area)"
                )

        # Parse weight
        try:
            weight = parse_decimal_weight(weight_value)
        except ValueError as e:
            raise ValueError(f"Invalid weight for country '{country_input}': {e}")

        # Validate weight is non-negative
        if weight < 0:
            raise ValueError(f"Weight for country '{country_input}' cannot be negative: {weight}")

        normalized[iso3_code] = weight

    # Step 2: Calculate sum
    total_sum = sum(normalized.values())

    # Step 3: Check sum is within tolerance
    sum_diff = abs(total_sum - TARGET_SUM)

    if sum_diff > SUM_TOLERANCE:
        raise ValueError(
            f"Geographic area weights must sum to 1.0 (±{SUM_TOLERANCE}). "
            f"Current sum: {total_sum} (difference: {sum_diff})"
            )

    # Step 4: Quantize all weights to 4 decimals
    quantized: dict[str, Decimal] = {
        country: quantize_weight(weight)
        for country, weight in normalized.items()
        }

    # Step 5: Renormalize if sum != 1.0 after quantization
    quantized_sum = sum(quantized.values())

    if quantized_sum != TARGET_SUM:
        # Find smallest weight (will be adjusted)
        min_country = min(quantized, key=quantized.get)
        min_weight = quantized[min_country]

        # Calculate adjustment needed
        adjustment = TARGET_SUM - quantized_sum

        # Apply adjustment to smallest weight
        adjusted_weight = min_weight + adjustment

        # Validate adjustment doesn't make weight negative
        if adjusted_weight < 0:
            raise ValueError(
                f"Cannot renormalize: adjustment would make weight negative. "
                f"Country: {min_country}, Original: {min_weight}, Adjustment: {adjustment}"
                )

        # Apply adjustment
        quantized[min_country] = adjusted_weight

    # Final validation: sum must be exactly 1.0
    final_sum = sum(quantized.values())
    if final_sum != TARGET_SUM:
        # This should never happen, but be defensive
        raise ValueError(
            f"Internal error: final sum is {final_sum} after renormalization "
            f"(expected {TARGET_SUM})"
            )

    return quantized
