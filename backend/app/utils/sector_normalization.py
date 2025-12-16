"""
Sector normalization utilities.

Provides ENUM-based sector classification and validation for financial assets.
"""
from enum import Enum
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class FinancialSector(str, Enum):
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
            "materials": cls.BASIC_MATERIALS,  # Alias
            "energy": cls.ENERGY,
            "consumer staples": cls.CONSUMER_STAPLES,
            "telecommunication": cls.TELECOMMUNICATION,
            "telecom": cls.TELECOMMUNICATION,  # Alias
            "utilities": cls.UTILITIES,
            "other": cls.OTHER
        }

        if normalized_key in mapping:
            return mapping[normalized_key]

        # Not found - log warning and return OTHER
        logger.warning(
            "Sector not in standard classification",
            original_sector=sector_name,
            normalized_to="Other"
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

