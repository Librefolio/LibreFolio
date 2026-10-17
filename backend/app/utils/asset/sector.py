"""
Sector normalization utilities.

Provides ENUM-based sector classification and validation for financial assets, and the one map of sector emoji.
"""

from enum import StrEnum

import structlog

logger = structlog.get_logger(__name__)


class FinancialSector(StrEnum):
    """
    Standard financial sector classification.

    Based on GICS (Global Industry Classification Standard) sectors.
    """

    INDUSTRIALS = "Industrials"
    TECHNOLOGY = "Technology"
    FINANCIALS = "Financials"
    CONSUMER_DISCRETIONARY = "Consumer Discretionary"
    HEALTH_CARE = "Health Care"
    REAL_ESTATE = "Real Estate"
    BASIC_MATERIALS = "Basic Materials"
    ENERGY = "Energy"
    CONSUMER_STAPLES = "Consumer Staples"
    TELECOMMUNICATION = "Telecommunication"
    UTILITIES = "Utilities"
    CORPORATE_BONDS = "Corporate Bonds"
    GOVERNMENT_BONDS = "Government Bonds"
    OTHER = "Other"

    @classmethod
    def from_string(cls, sector_name: str) -> "FinancialSector":
        """
        Convert string to FinancialSector enum (case-insensitive with aliases).

        Args:
            sector_name: Input sector name

        Returns:
            FinancialSector enum value
            Returns OTHER if sector not recognized (with warning log)

        Examples:
            >>> FinancialSector.from_string("Technology")
            <FinancialSector.TECHNOLOGY: 'Technology'>
            >>> FinancialSector.from_string("healthcare")
            <FinancialSector.HEALTH_CARE: 'Health Care'>
        """
        if not sector_name:
            return cls.OTHER

        normalized_key = sector_name.strip().lower()

        # Direct mapping with aliases
        mapping = {
            "industrials": cls.INDUSTRIALS,
            "technology": cls.TECHNOLOGY,
            "financials": cls.FINANCIALS,
            "consumer discretionary": cls.CONSUMER_DISCRETIONARY,
            "health care": cls.HEALTH_CARE,
            "healthcare": cls.HEALTH_CARE,  # Alias
            "real estate": cls.REAL_ESTATE,
            "basic materials": cls.BASIC_MATERIALS,
            "materials": cls.BASIC_MATERIALS,  # Short alias
            "energy": cls.ENERGY,
            "consumer staples": cls.CONSUMER_STAPLES,
            "consumer defensive": cls.CONSUMER_STAPLES,  # Yahoo Finance alias
            "telecommunication": cls.TELECOMMUNICATION,
            "telecom": cls.TELECOMMUNICATION,  # Short alias
            "communication services": cls.TELECOMMUNICATION,  # Yahoo Finance alias
            "utilities": cls.UTILITIES,
            "corporate": cls.CORPORATE_BONDS,
            "corporate bond": cls.CORPORATE_BONDS,
            "corporate bonds": cls.CORPORATE_BONDS,
            "government": cls.GOVERNMENT_BONDS,
            "government bond": cls.GOVERNMENT_BONDS,
            "government bonds": cls.GOVERNMENT_BONDS,
            "other": cls.OTHER,
            # Yahoo Finance aliases
            "financial services": cls.FINANCIALS,
            "consumer cyclical": cls.CONSUMER_DISCRETIONARY,
        }

        if normalized_key in mapping:
            return mapping[normalized_key]

        # Not found - log warning and return OTHER
        logger.warning(
            "Sector not in standard classification",
            original_sector=sector_name,
            normalized_to="Other",
        )
        return cls.OTHER

    @classmethod
    def list_all(cls) -> list[str]:
        """
        Get list of all sector values (excluding OTHER).

        Returns:
            List of sector names
        """
        return [sector.value for sector in cls if sector != cls.OTHER]

    @classmethod
    def list_all_with_other(cls) -> list[str]:
        """
        Get list of all sector values (including OTHER).

        Returns:
            List of sector names
        """
        return [sector.value for sector in cls]


# The two allocation buckets the portfolio engine adds on its own, beside the sectors: the cash and the holdings without
# a sector. Never a sector an asset can be classified in, so never offered in a sector select.
LIQUIDITY_BUCKET = "Liquidity"
UNKNOWN_BUCKET = "Unknown"
ALLOCATION_BUCKETS: tuple[str, ...] = (LIQUIDITY_BUCKET, UNKNOWN_BUCKET)

# The emoji of a sector: the one map behind every view that shows one, the `/utilities/sectors` list and the
# allocation views of the portfolio engine, which used to keep a copy each and disagreed on four keys. Besides the
# sectors it names the two allocation buckets. Values: the designer's round 2 (15/10/2026), the same glyphs in the pie
# and in the history.
SECTOR_EMOJI: dict[str, str] = {
    FinancialSector.INDUSTRIALS: "🏭",
    FinancialSector.TECHNOLOGY: "💻",
    FinancialSector.FINANCIALS: "🏦",
    FinancialSector.CONSUMER_DISCRETIONARY: "🛍️",
    FinancialSector.HEALTH_CARE: "🏥",
    FinancialSector.REAL_ESTATE: "🏠",
    FinancialSector.BASIC_MATERIALS: "⛏️",
    FinancialSector.ENERGY: "⚡",
    FinancialSector.CONSUMER_STAPLES: "🛒",
    FinancialSector.TELECOMMUNICATION: "📡",
    FinancialSector.UTILITIES: "💡",
    FinancialSector.CORPORATE_BONDS: "🏢",
    FinancialSector.GOVERNMENT_BONDS: "🏛️",
    FinancialSector.OTHER: "📦",
    LIQUIDITY_BUCKET: "💰",
    UNKNOWN_BUCKET: "❓",
}

# The glyph of a key outside the map: the one of the unclassified bucket, so an unexpected key reads as unclassified.
# With every sector and bucket mapped, only a key outside the enum gets it.
SECTOR_EMOJI_FALLBACK = SECTOR_EMOJI[UNKNOWN_BUCKET]


def sector_emoji(key: str) -> str:
    """The emoji of a sector or an allocation bucket, and the fallback for a key outside the map."""
    return SECTOR_EMOJI.get(key, SECTOR_EMOJI_FALLBACK)


def normalize_sector(sector_name: str) -> str:
    """
    Normalize sector name to standard classification.

    Args:
        sector_name: Input sector name (case-insensitive)

    Returns:
        Normalized sector name from FinancialSector enum
        Returns "Other" if sector not found in mapping
    """
    return FinancialSector.from_string(sector_name).value


def validate_sector(sector_name: str) -> bool:
    """
    Check if sector name is in standard classification.

    Args:
        sector_name: Sector name to validate

    Returns:
        True if sector is recognized (not "Other")
    """

    return FinancialSector.from_string(sector_name) != FinancialSector.OTHER
