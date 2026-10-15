"""
Asset classification and metadata schemas (FA).

- ``BaseDistribution``: the shared validation of a weight distribution; ``FAGeographicArea`` (ISO-3166-A3 country codes)
  and ``FASectorArea`` (standard sectors) extend it.
- ``FAClassificationParams``: the classification metadata of an asset (all fields optional, for partial updates).
- ``FAAssetMetadataResponse``: an asset with its metadata fields (GET and PATCH responses, bulk reads).
- ``FAMetadataRefreshResult`` / ``FABulkMetadataRefreshResponse``: the outcome of a metadata refresh from the providers.
"""

# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import List, Optional

from pydantic import Field, field_validator

from backend.app.schemas.common import (
    BaseBulkResponse,
    SafeDecimal,
    StrictModel,
)
from backend.app.schemas.provider import FAProviderRefreshFieldsDetail
from backend.app.utils.asset.geo import normalize_country_keys
from backend.app.utils.asset.sector import normalize_sector

# ============================================================================
# ASSET METADATA & CLASSIFICATION
# ============================================================================

# ============================================================================
# DISTRIBUTION BASE MODELS
# ============================================================================


class BaseDistribution(StrictModel):
    """
    Base class for distribution models (geographic, sector, etc.).

    Handles common validation:
    - Weights must be Decimal with 4 decimal places
    - Weights must sum to 1.0 (±1e-6 tolerance)
    - Auto-renormalization if sum != 1.0
    - Quantization with ROUND_HALF_EVEN

    Child classes must override validate_distribution() to normalize keys
    before calling parent validation via _validate_and_normalize_weights().
    """

    distribution: dict[str, SafeDecimal] = Field(..., description="Distribution weights (must sum to 1.0)")

    @classmethod
    def _validate_and_normalize_weights(cls, weights: dict[str, Decimal], allow_empty: bool = False) -> dict[str, Decimal]:  # noqa: C901 — flat validation/normalization passes, no nested logic
        """
        Common validation logic for distribution weights.

        This method:
        1. Validates weights are non-negative
        2. Quantizes to 4 decimals (ROUND_HALF_EVEN)
        3. Validates sum is ~1.0 (tolerance: 1e-6)
        4. Renormalizes if needed (adjusts smallest weight)

        Args:
            weights: Dictionary of weights (keys must already be normalized)
            allow_empty: Whether to allow empty distributions

        Returns:
            Normalized and quantized weights summing to exactly 1.0

        Raises:
            ValueError: If validation fails
        """
        if not weights and not allow_empty:
            raise ValueError("Distribution cannot be empty")

        if not weights:
            return {}

        # First pass: convert to Decimal and validate non-negative
        quantizer = Decimal("0.0001")
        parsed_weights = {}

        for key, weight in weights.items():
            # Ensure it's a Decimal
            if not isinstance(weight, Decimal):
                weight = Decimal(str(weight))

            # Check non-negative
            if weight < 0:
                raise ValueError(f"Weight for '{key}' cannot be negative: {weight}")

            parsed_weights[key] = weight

        # Check if sum is zero (can't normalize)
        raw_total = sum(parsed_weights.values())
        if raw_total == Decimal("0"):
            raise ValueError("Distribution weights sum to zero")

        target = Decimal("1.0")
        tolerance = Decimal("0.01")  # Allow up to 1% deviation before rejecting

        # Check if raw sum is too far from 1.0 to be a rounding issue
        if abs(raw_total - target) > tolerance:
            raise ValueError(f"Distribution weights must sum to approximately 1.0 (±{tolerance}). " f"Current sum: {raw_total} (difference: {abs(raw_total - target)})")

        # Normalize weights to sum to exactly 1.0, then quantize
        quantized = {}
        for key, weight in parsed_weights.items():
            normalized = (weight / raw_total).quantize(quantizer, rounding=ROUND_HALF_EVEN)
            quantized[key] = normalized

        # Calculate sum after quantization
        total = sum(quantized.values())

        # Fine-tune to ensure exactly 1.0
        if total != target:
            # Adjust the smallest weight
            min_key = min(quantized, key=quantized.get)
            adjustment = target - total
            adjusted_weight = quantized[min_key] + adjustment

            if adjusted_weight < 0:
                raise ValueError(f"Cannot renormalize: adjustment would make weight negative. " f"Key: {min_key}, Original: {quantized[min_key]}, Adjustment: {adjustment}")

            quantized[min_key] = adjusted_weight

        # Final validation
        final_sum = sum(quantized.values())
        if final_sum != target:
            raise ValueError(f"Internal error: final sum is {final_sum} after renormalization (expected {target})")

        return quantized


class FAGeographicArea(BaseDistribution):
    """
    Geographic area distribution with ISO-3166-A3 validation.

    Extends BaseDistribution with country code normalization.
    Keys must be ISO-3166-A3 country codes (or names/ISO-2 that will be normalized).

    Examples:
        >>> geo = FAGeographicArea(distribution={"USA": Decimal("0.6"), "ITA": Decimal("0.4")})
        >>> geo.distribution
        {'USA': Decimal('0.6000'), 'ITA': Decimal('0.4000')}

        >>> geo = FAGeographicArea(distribution={"US": 0.5, "Italy": 0.5})
        >>> geo.distribution
        {'USA': Decimal('0.5000'), 'ITA': Decimal('0.5000')}
    """

    @field_validator("distribution")
    @classmethod
    def validate_distribution(cls, v):
        """
        Validate and normalize geographic area distribution.

        Process:
        1. Normalize country keys to ISO-3166-A3 (geo_normalization)
        2. Validate and normalize weights (BaseDistribution)
        """
        if not v:
            raise ValueError("Geographic distribution cannot be empty")

        # Step 1: Normalize country codes
        normalized_countries = normalize_country_keys(v)

        # Step 2: Validate and normalize weights
        return cls._validate_and_normalize_weights(normalized_countries)


class FASectorArea(BaseDistribution):
    """
    Sector allocation distribution with standard classification.

    Validates sector names against FinancialSector enum:
    - Industrials, Technology, Financials, Consumer Discretionary,
      Health Care, Real Estate, Basic Materials, Energy, Consumer Staples,
      Telecommunication, Utilities, Corporate Bonds, Government Bonds, Other

    Unknown sectors are mapped to "Other" with warning log.
    Weights are automatically merged if multiple input keys map to same sector.

    Examples:
        >>> sector_dist = FASectorArea(distribution={
        ...     "Technology": Decimal("0.35"),
        ...     "Financials": Decimal("0.25"),
        ...     "Health Care": Decimal("0.40")
        ... })

        >>> # Aliases and case-insensitive
        >>> sector_dist = FASectorArea(distribution={
        ...     "technology": 0.3,
        ...     "healthcare": 0.3,  # Will be normalized to "Health Care"
        ...     "FINANCIALS": 0.4
        ... })
    """

    @field_validator("distribution")
    @classmethod
    def validate_distribution(cls, v):
        """
        Validate and normalize sector distribution.

        Process:
        1. Normalize sector names using FinancialSector enum
        2. Merge weights for sectors that map to same standard name
        3. Validate and normalize weights (BaseDistribution)
        """
        if not v:
            raise ValueError("Sector distribution cannot be empty")

        # Step 1: Normalize sector names and merge weights
        normalized_sectors: dict[str, Decimal] = {}

        for sector_name, weight in v.items():
            # Normalize sector name using enum
            normalized_name = normalize_sector(sector_name)

            # Parse to Decimal if needed
            if not isinstance(weight, Decimal):
                weight = Decimal(str(weight))

            # Merge weights if multiple keys map to same sector
            if normalized_name in normalized_sectors:
                normalized_sectors[normalized_name] += weight
            else:
                normalized_sectors[normalized_name] = weight

        # Step 2: Validate and normalize weights
        return cls._validate_and_normalize_weights(normalized_sectors)


class FAClassificationParams(StrictModel):
    """
    Asset classification metadata.

    All fields optional (partial updates supported via PATCH).
    geographic_area and sector_area are indivisible blocks (full replace on update, no merge).

    Validation:
    - geographic_area: ISO-3166-A3 codes, weights must sum to 1.0 (±1e-6)
    - sector_area: Standard FinancialSector enum values, weights must sum to 1.0 (±1e-6)
    - Weights quantized to 4 decimals (ROUND_HALF_EVEN)
    - Automatic renormalization if sum != 1.0

    Examples:
        >>> params = FAClassificationParams(
        ...     short_description="Apple Inc. - Technology company",
        ...     geographic_area=FAGeographicArea(distribution={"USA": Decimal("0.6"), "EUR": Decimal("0.4")}),
        ...     sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")})
        ... )
    """

    short_description: Optional[str] = None
    geographic_area: Optional[FAGeographicArea] = None
    sector_area: Optional[FASectorArea] = None


class FAAssetMetadataResponse(StrictModel):
    """
    Asset with metadata fields.

    Used for GET/PATCH responses and bulk read operations.

    Fields:
    - asset_id: Asset database ID
    - display_name: User-friendly asset name
    - currency: Asset currency code
    - icon_url: Asset icon URL (optional)
    - asset_type: Asset type (STOCK, BOND, ETF, etc.)
    - classification_params: Optional classification metadata
    - provider_code: Provider code if assigned (e.g. 'yfinance'), None otherwise
    """

    asset_id: int
    display_name: str
    currency: str
    icon_url: Optional[str] = None
    asset_type: Optional[str] = None
    quote_base_quantity: Optional[int] = Field(1, description="How many units the raw market quote refers to")
    classification_params: Optional[FAClassificationParams] = None
    provider_code: Optional[str] = Field(None, description="Provider code if assigned (e.g. 'yfinance')")


class FAMetadataRefreshResult(StrictModel):
    """
    Result of metadata refresh for single asset.

    Follows FA pattern: { asset_id, success, message, ... }
    Includes fields_detail with old/new values for each refreshed field.
    """

    asset_id: int
    success: bool
    message: str
    fields_detail: Optional[FAProviderRefreshFieldsDetail] = Field(None, description="Details of refreshed fields with old/new values")
    warnings: Optional[List[str]] = None


class FABulkMetadataRefreshResponse(BaseBulkResponse[FAMetadataRefreshResult]):
    """Bulk metadata refresh response (partial success).

    Each result includes fields_detail with:
    - refreshed_fields: List[OldNew[str]] with old/new values
    - missing_data_fields: Fields provider didn't return
    - ignored_fields: Fields skipped (future use)
    """
