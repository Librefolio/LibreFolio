"""
Geographic area utilities for LibreFolio.

Provides functions to normalize country codes to ISO-3166-A3 format.
Weight validation and quantization is handled by BaseDistribution in schemas/assets.py.

Usage:
    from backend.app.utils.geo_utils import normalize_country_keys

    # Normalize country codes in distribution
    data = {"USA": "0.6", "Italy": 0.3, "GB": 0.1}
    normalized = normalize_country_keys(data)
    # Returns: {"USA": Decimal("0.6"), "ITA": Decimal("0.3"), "GBR": Decimal("0.1")}

Key Features:
- Country code normalization (name/ISO-2/ISO-3 → ISO-3166-A3)
- Multi-language country name support via Babel
- Flag emoji generation from ISO-2 codes
- Weight parsing (int/float/str → Decimal)
- Duplicate detection after normalization
"""
from decimal import Decimal
from typing import Any, List

import pycountry
import structlog

from backend.app.utils.decimal_utils import parse_decimal_value
from backend.app.utils.translation_utils import get_babel_locale

logger = structlog.get_logger(__name__)

# Region to country mapping for expansion
# When a region code is detected, it can be expanded to multiple country ISO-3 codes
REGION_MAPPING: dict[str, list[str]] = {
    # Europe
    "EUR": [
        "DEU", "FRA", "ITA", "ESP", "NLD", "AUT", "BEL", "FIN", "GRC", "IRL",
        "LVA", "LTU", "LUX", "MLT", "PRT", "SVK", "SVN", "CYP", "EST"
        ],  # Eurozone 20
    "EU": [
        "DEU", "FRA", "ITA", "ESP", "NLD", "AUT", "BEL", "FIN", "GRC", "IRL",
        "LVA", "LTU", "LUX", "MLT", "PRT", "SVK", "SVN", "CYP", "EST", "POL",
        "CZE", "HUN", "SWE", "DNK", "BGR", "HRV", "ROU"
        ],  # EU27
    "NORDIC": ["SWE", "DNK", "NOR", "FIN", "ISL"],

    # Americas
    "LATAM": [
        "BRA", "MEX", "ARG", "CHL", "COL", "PER", "VEN", "ECU", "BOL",
        "PRY", "URY", "CRI", "PAN", "GTM", "HND", "SLV", "NIC", "DOM", "CUB"
        ],
    "NAFTA": ["USA", "CAN", "MEX"],

    # Asia
    "ASIA": [
        "CHN", "JPN", "IND", "KOR", "SGP", "THA", "VNM", "IDN", "MYS",
        "PHL", "TWN", "HKG", "PAK", "BGD", "LKA", "MMR", "KHM", "LAO", "MNG", "NPL"
        ],
    "ASEAN": ["SGP", "THA", "VNM", "IDN", "MYS", "PHL", "KHM", "LAO", "MMR", "BRN"],

    # Middle East & Africa
    "MENA": [
        "ARE", "SAU", "QAT", "KWT", "OMN", "BHR", "JOR", "LBN", "EGY",
        "MAR", "TUN", "DZA", "IRQ", "YEM"
        ],
    "AFRICA": [
        "ZAF", "EGY", "NGA", "KEN", "ETH", "GHA", "TZA", "UGA", "DZA",
        "MAR", "TUN", "MOZ", "AGO", "SEN", "CIV", "CMR", "ZWE", "RWA", "BEN"
        ],

    # Oceania
    "OCEANIA": ["AUS", "NZL", "FJI", "PNG", "NCL", "PYF", "GUM", "SLB", "VUT"],

    # Economic groups
    "G7": ["USA", "CAN", "GBR", "DEU", "FRA", "ITA", "JPN"],
    "G20": [
        "USA", "CAN", "GBR", "DEU", "FRA", "ITA", "JPN", "CHN", "IND",
        "BRA", "MEX", "RUS", "ZAF", "SAU", "TUR", "KOR", "IDN", "AUS", "ARG"
        ],
    "BRICS": ["BRA", "RUS", "IND", "CHN", "ZAF"],
    }


def is_region(code: str) -> bool:
    """Check if a code is a region rather than a country."""
    return code.upper() in REGION_MAPPING


def expand_region(region_code: str) -> list[str]:
    """
    Expand a region code to its constituent country ISO-3 codes.

    Args:
        region_code: Region code (e.g., "EUR", "ASIA", "G7")

    Returns:
        List of ISO-3166-A3 country codes, or empty list if not a region

    Examples:
        >>> expand_region("G7")
        ["USA", "CAN", "GBR", "DEU", "FRA", "ITA", "JPN"]
        >>> expand_region("USA")  # Not a region
        []
    """
    return REGION_MAPPING.get(region_code.upper(), [])


def iso2_to_flag_emoji(iso2: str) -> str:
    """
    Convert ISO-3166-A2 country code to flag emoji.

    Uses Regional Indicator Symbols (U+1F1E6 to U+1F1FF) to form flag emoji.

    Args:
        iso2: ISO-3166-A2 code (e.g., "US", "IT", "FR")

    Returns:
        Flag emoji string (e.g., "🇺🇸", "🇮🇹", "🇫🇷")

    Examples:
        >>> iso2_to_flag_emoji("US")
        "🇺🇸"
        >>> iso2_to_flag_emoji("IT")
        "🇮🇹"
    """
    if not iso2 or len(iso2) != 2:
        return "🏳️"  # White flag for invalid codes

    iso2_upper = iso2.upper()
    # Convert each letter to Regional Indicator Symbol
    return chr(0x1F1E6 + ord(iso2_upper[0]) - ord('A')) + chr(0x1F1E6 + ord(iso2_upper[1]) - ord('A'))


def list_countries(language: str = 'en') -> List[dict]:
    """
    List all countries with localized names and flag emoji.

    Args:
        language: ISO 639-1 language code (default: 'en')

    Returns:
        List of dicts with 'iso3', 'iso2', 'name', 'flag_emoji'
    """
    locale = get_babel_locale(language)
    countries = []

    for country in pycountry.countries:
        iso2 = country.alpha_2
        iso3 = country.alpha_3

        # Get localized name from Babel
        try:
            name = locale.territories.get(iso2, country.name)
        except Exception:
            name = country.name

        countries.append({
            "iso3": iso3,
            "iso2": iso2,
            "name": name,
            "flag_emoji": iso2_to_flag_emoji(iso2)
            })

    return sorted(countries, key=lambda x: x['name'])


def normalize_country_multilang(input_str: str, language: str = 'en') -> dict:
    """
    Normalize country input to ISO-3166-A3 code(s) with multi-language support.

    Accepts:
    - ISO-3166-A3 codes (e.g., USA, GBR, ITA)
    - ISO-3166-A2 codes (e.g., US, GB, IT)
    - Country names in any supported language

    Args:
        input_str: Country identifier in any format
        language: Language for name matching (default: 'en')

    Returns:
        Dict with:
        - query: Original input
        - iso3_codes: List of matching ISO-3 codes (usually 1, may be multiple if ambiguous)
        - match_type: 'exact', 'multi-match', 'region', 'not_found'
        - error: Error message if any
    """
    if not input_str:
        return {
            "query": input_str,
            "iso3_codes": [],
            "match_type": "not_found",
            "error": "Empty input"
            }

    input_clean = input_str.strip().upper()

    # Check if it's a region code
    if is_region(input_clean):
        return {
            "query": input_str,
            "iso3_codes": expand_region(input_clean),
            "match_type": "region",
            "error": None
            }

    # Try ISO-3166-A3 first
    if len(input_clean) == 3:
        try:
            country = pycountry.countries.get(alpha_3=input_clean)
            if country:
                return {
                    "query": input_str,
                    "iso3_codes": [country.alpha_3],
                    "match_type": "exact",
                    "error": None
                    }
        except Exception:
            pass

    # Try ISO-3166-A2
    if len(input_clean) == 2:
        try:
            country = pycountry.countries.get(alpha_2=input_clean)
            if country:
                return {
                    "query": input_str,
                    "iso3_codes": [country.alpha_3],
                    "match_type": "exact",
                    "error": None
                    }
        except Exception:
            pass

    # Try fuzzy name search
    try:
        results = pycountry.countries.search_fuzzy(input_str)
        if len(results) == 1:
            return {
                "query": input_str,
                "iso3_codes": [results[0].alpha_3],
                "match_type": "exact",
                "error": None
                }
        elif len(results) > 1:
            return {
                "query": input_str,
                "iso3_codes": [c.alpha_3 for c in results],
                "match_type": "multi-match",
                "error": f"Multiple countries match '{input_str}'"
                }
    except LookupError:
        pass

    return {
        "query": input_str,
        "iso3_codes": [],
        "match_type": "not_found",
        "error": f"No country found for '{input_str}'"
        }


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
    raise ValueError(f"Country '{country_input}' not found. Please use ISO-3166-A2 (e.g., US), ISO-3166-A3 (e.g., USA), or full country name.")


def normalize_country_keys(data: dict[str, Any]) -> dict[str, Decimal]:
    """
    Normalize country codes in distribution dictionary to ISO-3166-A3.

    This function only handles country code normalization and weight parsing.
    Weight validation and quantization is done by BaseDistribution.

    Args:
        data: Dict of country codes/names to weights
              Keys: Any format (ISO-2, ISO-3, name)
              Values: Numeric (int, float, str, Decimal)

    Returns:
        Dict with normalized ISO-3166-A3 keys and parsed Decimal values

    Raises:
        ValueError: If country code invalid or duplicates after normalization

    Examples:
        >>> normalize_country_keys({"USA": 0.6, "Italy": 0.3, "GB": 0.1})
        {"USA": Decimal("0.6"), "ITA": Decimal("0.3"), "GBR": Decimal("0.1")}
    """
    if not data or not isinstance(data, dict):
        raise ValueError("Geographic area must be a non-empty dictionary")

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
        weight = parse_decimal_value(weight_value)
        if weight is None:
            raise ValueError(f"Weight for country '{country_input}' cannot be '{weight_value}'")

        # Validate weight is non-negative
        if weight < 0:
            raise ValueError(f"Weight for country '{country_input}' cannot be negative: {weight}")

        normalized[iso3_code] = weight

    return normalized
