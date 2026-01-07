# Plan: Distribution Refactoring & Utilities Endpoints

## STATO IMPLEMENTAZIONE: ✅ COMPLETATO E VERIFICATO

**Data completamento**: 2025-12-16  
**Report di verifica**: `/VERIFICATION_REPORT.md`

### Punti Completati e Verificati:
1. ✅ **Creato** `/backend/app/utils/sector_normalization.py` - ENUM FinancialSector con 12 settori
2. ✅ **Modificato** `/backend/app/utils/geo_normalization.py` - semplificato, delega a BaseDistribution
3. ✅ **Modificato** `/backend/app/schemas/assets.py` - BaseDistribution, FASectorArea, FAGeographicArea refactored
4. ✅ **Rimosso** `FABulkAssetDeleteRequest` da assets.py
5. ✅ **Rimosso** campo `sector` (str) da `FAClassificationParams`
6. ✅ **Rimosso** campo `changes` da `FAMetadataRefreshResult`
7. ✅ **Creato** `/backend/app/schemas/utilities.py` - CountryNormalizationResponse, SectorListResponse
8. ✅ **Creato** `/backend/app/api/v1/utilities.py` - endpoint /sectors e /countries/normalize
9. ✅ **Modificato** `/backend/app/api/v1/router.py` - registrato utilities_router
10. ✅ **Modificato** `/backend/app/api/v1/assets.py` - DELETE usa query params List[int]
11. ✅ **Modificato** `/backend/app/services/asset_source_providers/justetf.py` - usa FASectorArea
12. ✅ **Modificato** `/backend/app/services/asset_source.py` - rimosso changes=None
13. ✅ **Aggiornato** tutti i test files - DELETE usa query params

### Test Completati:
- ✅ `./test_runner.py api all` - **PASS**
- ✅ `./test_runner.py external asset-providers` - **PASS**
- ✅ `./test_runner.py utils` - **PASS**
- ✅ `./test_runner.py services` - **PASS**

### TODO Futuri (Non Bloccanti):
- ⏳ Espansione regioni in `/utilities/countries/normalize` (EUR → lista paesi)
- ⏳ Sector hierarchy opzionale (sub-settori GICS completi)

---

## Obiettivo
Refactoring completo del sistema di distribuzione (Geographic/Sector) con classe base comune e creazione di endpoint utilities per supporto frontend.

---

## Modifiche Principali

### 1. Sistema Distribution con ENUM
- Creare classe base `BaseDistribution` per gestire validazione pesi comuni
- Specializzare in `FAGeographicArea` e `FASectorArea`
- Usare ENUM `FinancialSector` per classificazione settori standard
- Rimuovere campo deprecato `sector` (stringa) da `FAClassificationParams`

### 2. Endpoint Utilities
- Nuovo router `/api/v1/utilities` per supporto frontend
- Endpoint per normalizzazione country (preparato per espansione regioni EUR/ASIA)
- Endpoint per lista settori standard riconosciuti dal sistema

### 3. Cleanup
- Eliminare `FABulkAssetDeleteRequest` - usare direttamente `List[int]` come query params
- Rimuovere campo `changes` deprecato da `FAMetadataRefreshResult`
- Refactoring `geo_normalization.py` per delegare validazione pesi a `BaseDistribution`

---

## File 1: Creare `/backend/app/utils/sector_normalization.py`

```python
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
```

---

## File 2: Modificare `/backend/app/utils/geo_normalization.py`

**Rimuovere funzioni** che saranno nella classe base:
- `quantize_weight()` → Va in `BaseDistribution`
- Logica validazione somma in `validate_and_normalize_geographic_area()` → Va in `BaseDistribution`

**Mantenere solo**:
- `normalize_country_to_iso3()` - normalizzazione ISO-3166-A3
- Nuova funzione `normalize_country_keys()` - delega validazione pesi a BaseDistribution

**Codice modificato**:

```python
"""
Geographic area normalization utilities for LibreFolio.

Provides functions to normalize country codes to ISO-3166-A3 format.
Weight validation is handled by BaseDistribution in schemas/assets.py.
"""
from decimal import Decimal
from typing import Any

import pycountry

from backend.app.utils.decimal_utils import parse_decimal_value


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
    
    This function only handles country code normalization.
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


# Backward compatibility - delegate to normalize_country_keys + BaseDistribution
def validate_and_normalize_geographic_area(data: dict[str, Any]) -> dict[str, Decimal]:
    """
    Validate and normalize geographic area weight distribution.
    
    DEPRECATED: This function is kept for backward compatibility.
    New code should use FAGeographicArea(distribution=data).distribution
    
    Args:
        data: Dict of country codes/names to weights
    
    Returns:
        Dict of ISO-3166-A3 codes to quantized Decimal weights
    
    Raises:
        ValueError: If validation fails
    """
    # Import here to avoid circular dependency
    from backend.app.schemas.assets import FAGeographicArea
    
    geo_area = FAGeographicArea(distribution=data)
    return geo_area.distribution
```

---

## File 3: Modificare `/backend/app/schemas/assets.py`

### 3.1 Aggiungere imports (dopo le import esistenti, ~linea 30):

```python
from backend.app.utils.sector_fin_utils import FinancialSector, normalize_sector
from backend.app.utils.geo_utils import normalize_country_keys
```

### 3.2 Prima di FAScheduledYieldParams (linea ~390), aggiungere BaseDistribution:

```python
# ============================================================================
# DISTRIBUTION BASE MODELS
# ============================================================================

class BaseDistribution(BaseModel):
    """
    Base class for distribution models (geographic, sector, etc.).
    
    Handles common validation:
    - Weights must be Decimal with 4 decimal places
    - Weights must sum to 1.0 (±1e-6 tolerance)
    - Auto-renormalization if sum != 1.0
    - Quantization with ROUND_HALF_EVEN
    
    Child classes must override validate_distribution() to normalize keys
    before calling parent validation.
    """
    model_config = ConfigDict(extra="forbid")
    
    distribution: dict[str, Decimal] = Field(..., description="Distribution weights (must sum to 1.0)")
    
    @classmethod
    def _validate_and_normalize_weights(
        cls,
        weights: dict[str, Decimal],
        allow_empty: bool = False
    ) -> dict[str, Decimal]:
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
        from decimal import ROUND_HALF_EVEN
        
        if not weights and not allow_empty:
            raise ValueError("Distribution cannot be empty")
        
        if not weights:
            return {}
        
        # Quantize all weights to 4 decimals
        quantizer = Decimal('0.0001')
        quantized = {}
        
        for key, weight in weights.items():
            # Ensure it's a Decimal
            if not isinstance(weight, Decimal):
                weight = Decimal(str(weight))
            
            # Check non-negative
            if weight < 0:
                raise ValueError(f"Weight for '{key}' cannot be negative: {weight}")
            
            quantized[key] = weight.quantize(quantizer, rounding=ROUND_HALF_EVEN)
        
        # Calculate sum
        total = sum(quantized.values())
        target = Decimal('1.0')
        tolerance = Decimal('0.000001')
        
        # Check if sum is within tolerance
        if abs(total - target) > tolerance:
            # Check if it's a rounding issue we can fix
            if total == Decimal('0'):
                raise ValueError("Distribution weights sum to zero")
            
            # Try to renormalize
            renormalized = {
                k: (v / total).quantize(quantizer, rounding=ROUND_HALF_EVEN)
                for k, v in quantized.items()
            }
            
            # Check if renormalization helped
            new_total = sum(renormalized.values())
            if abs(new_total - target) > tolerance:
                raise ValueError(
                    f"Distribution weights must sum to 1.0 (±{tolerance}). "
                    f"Current sum: {total} (difference: {abs(total - target)})"
                )
            
            quantized = renormalized
            total = new_total
        
        # Fine-tune to ensure exactly 1.0
        if total != target:
            # Adjust the smallest weight
            min_key = min(quantized, key=quantized.get)
            adjustment = target - total
            adjusted_weight = quantized[min_key] + adjustment
            
            if adjusted_weight < 0:
                raise ValueError(
                    f"Cannot renormalize: adjustment would make weight negative. "
                    f"Key: {min_key}, Original: {quantized[min_key]}, Adjustment: {adjustment}"
                )
            
            quantized[min_key] = adjusted_weight
        
        # Final validation
        final_sum = sum(quantized.values())
        if final_sum != target:
            raise ValueError(
                f"Internal error: final sum is {final_sum} after renormalization (expected {target})"
            )
        
        return quantized
```

### 3.3 Sostituire FAGeographicArea:

```python
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
```

### 3.4 Aggiungere FASectorArea:

```python
class FASectorArea(BaseDistribution):
    """
    Sector allocation distribution with standard classification.
    
    Validates sector names against FinancialSector enum:
    - Industrials, Technology, Financials, Consumer Discretionary,
      Health Care, Real Estate, Basic Materials, Energy, Consumer Staples,
      Telecommunication, Utilities, Other
    
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
```

### 3.5 Modificare FAClassificationParams (rimuovere campo sector):

```python
class FAClassificationParams(BaseModel):
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
    model_config = ConfigDict(extra="forbid")

    short_description: Optional[str] = None
    geographic_area: Optional[FAGeographicArea] = None
    sector_area: Optional[FASectorArea] = None
```

### 3.6 Rimuovere FABulkAssetDeleteRequest e campo changes

- Cancellare completamente classe `FABulkAssetDeleteRequest` (linea ~576-582)
- Rimuovere campo `changes` da `FAMetadataRefreshResult` (mantenere solo `warnings`)

### 3.7 Aggiornare __all__ export:

```python
__all__ = [
    # ...existing exports...
    "BaseDistribution",
    "FAGeographicArea",
    "FASectorArea",
    "FAClassificationParams",
    # Remove "FABulkAssetDeleteRequest"
    # ...rest of exports...
]
```

---

## File 4: Creare nuovo router `/backend/app/api/v1/utilities.py`

```python
"""
Utility endpoints for frontend support.

Provides helper endpoints for:
- Country/region normalization
- Sector classification listing
- Other frontend utilities
"""
from typing import List
from fastapi import APIRouter, Query

from backend.app.schemas.utilities import (
    CountryNormalizationResponse,
    SectorListResponse
    )
from backend.app.utils.sector_fin_utils import FinancialSector
from backend.app.utils.geo_utils import normalize_country_to_iso3

router = APIRouter(prefix="/utilities", tags=["Utilities"])


@router.get("/countries/normalize", response_model=CountryNormalizationResponse)
async def normalize_country(
        name: str = Query(..., min_length=1, description="Country name or code to normalize")
        ):
    """
    Normalize country name/code to ISO-3166-A3 format.
    
    Accepts:
    - ISO-3166-A3 codes (e.g., USA, GBR)
    - ISO-3166-A2 codes (e.g., US, GB)
    - Country names (e.g., "United States", "Italy")
    - Regions (e.g., "EUR", "ASIA") - returns list of countries
    
    **Example Requests**:
    ```
    GET /api/v1/utilities/countries/normalize?name=USA
    GET /api/v1/utilities/countries/normalize?name=Italy
    GET /api/v1/utilities/countries/normalize?name=EUR
    ```
    
    **Response**:
    ```json
    {
      "query": "Italy",
      "iso3_codes": ["ITA"],
      "match_type": "exact"
    }
    ```
    
    TODO: Implement region expansion (EUR → [DEU, FRA, ITA, ESP, ...])
    """
    try:
        iso3_code = normalize_country_to_iso3(name)
        return CountryNormalizationResponse(
            query=name,
            iso3_codes=[iso3_code],
            match_type="exact"
            )
    except ValueError as e:
        # Could be a region - for now return error
        # TODO: Implement region mapping
        return CountryNormalizationResponse(
            query=name,
            iso3_codes=[],
            match_type="not_found",
            error=str(e)
            )


@router.get("/sectors", response_model=SectorListResponse)
async def list_sectors(
        include_other: bool = Query(True, description="Include 'Other' in the list")
        ):
    """
    Get list of all standard financial sectors.
    
    Returns the list of sectors that the system recognizes and stores.
    Based on GICS (Global Industry Classification Standard).
    
    **Example Request**:
    ```
    GET /api/v1/utilities/sectors
    GET /api/v1/utilities/sectors?include_other=false
    ```
    
    **Response**:
    ```json
    {
      "sectors": [
        "Industrials",
        "Technology",
        "Financials",
        "Consumer Discretionary",
        "Health Care",
        "Real Estate",
        "Basic Materials",
        "Energy",
        "Consumer Staples",
        "Telecommunication",
        "Utilities",
        "Other"
      ],
      "count": 12
    }
    ```
    """
    if include_other:
        sectors = FinancialSector.list_all_with_other()
    else:
        sectors = FinancialSector.list_all()

    return SectorListResponse(
        sectors=sectors,
        count=len(sectors)
        )
```

---

## File 5: Creare `/backend/app/schemas/utilities.py`

```python
"""
Pydantic schemas for utility endpoints.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class CountryNormalizationResponse(BaseModel):
    """Response for country normalization endpoint."""
    model_config = ConfigDict(extra="forbid")
    
    query: str = Field(..., description="Original query string")
    iso3_codes: List[str] = Field(..., description="List of ISO-3166-A3 country codes")
    match_type: str = Field(..., description="Match type: exact, region, multi-match, not_found")
    error: Optional[str] = Field(None, description="Error message if normalization failed")


class SectorListResponse(BaseModel):
    """Response for sectors list endpoint."""
    model_config = ConfigDict(extra="forbid")
    
    sectors: List[str] = Field(..., description="List of standard financial sector names")
    count: int = Field(..., description="Number of sectors in the list")
```

---

## File 6: Registrare router in `/backend/app/api/v1/router.py`

```python
# Add import
from backend.app.api.v1.utilities import router as utilities_router

# Add to router list (in appropriate location)
router.include_router(utilities_router)
```

---

## File 7: Modificare `/backend/app/services/asset_source_providers/justetf.py`

```python
# Import at top
from backend.app.schemas.assets import FASectorArea

# In fetch_asset_metadata method (~line 380-450):

# Build sector distribution
sector_area = None
sectors = overview.get('sectors', [])
if sectors:
    distribution = {}
    for sector_item in sectors:
        sector_name = sector_item.get('name')
        percentage = sector_item.get('percentage')
        if sector_name and percentage is not None:
            weight = Decimal(str(percentage)) / Decimal('100')
            # Accumulate if sector appears multiple times
            if sector_name in distribution:
                distribution[sector_name] += weight
            else:
                distribution[sector_name] = weight
    
    if distribution:
        try:
            # FASectorArea will normalize sector names and validate weights
            sector_area = FASectorArea(distribution=distribution)
        except Exception as e:
            logger.warning(f"Could not create FASectorArea for {identifier}: {e}")

# Create classification params (remove old 'sector' field)
classification_params = FAClassificationParams(
    short_description=short_description,
    geographic_area=geographic_area,
    sector_area=sector_area
)
```

---

## File 8: Modificare endpoint DELETE in `/backend/app/api/v1/assets.py`

```python
# Remove import
# from backend.app.schemas.assets import FABulkAssetDeleteRequest

# Modify endpoint
@asset_router.delete("", response_model=FABulkAssetDeleteResponse, tags=["FA CRUD"])
async def delete_assets_bulk(
    asset_ids: List[int] = Query(..., min_length=1, description="List of asset IDs to delete"),
    session: AsyncSession = Depends(get_session_generator)
):
    """
    Delete multiple assets in bulk (partial success allowed).

    **Warning**: This will CASCADE DELETE:
    - Provider assignments (asset_provider_assignments table)
    - Price history (price_history table)

    **Blocks deletion** if asset has transactions (foreign key constraint).

    **Request Example**:
    ```
    DELETE /api/v1/assets?asset_ids=1&asset_ids=2&asset_ids=3
    ```
    """
    try:
        return await AssetCRUDService.delete_assets_bulk(asset_ids, session)
    except Exception as e:
        logger.error(f"Error in bulk asset deletion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## File 9: Modificare `/backend/app/services/asset_source.py`

Rimuovere `changes=None` (linea ~797):

```python
results.append(FAMetadataRefreshResult(
    asset_id=patch_result.asset_id,
    success=patch_result.success,
    message=patch_result.message
))
```

---

## File 10: Aggiornare tutti i test

Modificare tutte le chiamate DELETE per usare query params invece di body JSON.

**Files da modificare**:
- `backend/test_scripts/test_api/test_assets_provider.py` (linee 763, 882, 1003)
- `backend/test_scripts/test_api/test_assets_crud.py` (linee 382-383, 426-427, 460-461)

**Cambio**:
```python
# PRIMA
await client.request(
    "DELETE",
    f"{API_BASE}/assets",
    json=FABulkAssetDeleteRequest(asset_ids=[asset_id]).model_dump(mode="json"),
    timeout=TIMEOUT
)

# DOPO
await client.delete(
    f"{API_BASE}/assets",
    params={"asset_ids": [asset_id]},  # or asset_ids for list
    timeout=TIMEOUT
)
```

---

## Note sulla Migrazione Dati

### Database Schema
`classification_params` è un campo JSON - **NON serve migration Alembic**.
Le modifiche sono solo a livello di validazione Python.

### Migrazione Dati Esistenti (se necessario)

Se esistono dati con vecchio campo `sector` (stringa), creare script:

```python
# Script: migrate_sector_to_sector_area.py
"""
Migrate existing sector strings to FASectorArea format.
"""
import json
from decimal import Decimal
from sqlalchemy import select
from backend.app.db.models import Asset
from backend.app.db import get_session

async def migrate_sectors():
    async with get_session() as session:
        # Get all assets with classification_params
        stmt = select(Asset).where(Asset.classification_params.isnot(None))
        result = await session.execute(stmt)
        assets = result.scalars().all()
        
        migrated_count = 0
        for asset in assets:
            params = json.loads(asset.classification_params)
            
            # Check if has old 'sector' field
            if 'sector' in params and params['sector']:
                sector_name = params['sector']
                
                # Create sector_area from single sector
                params['sector_area'] = {
                    'distribution': {
                        sector_name: "1.0"
                    }
                }
                
                # Remove old field
                del params['sector']
                
                # Save back
                asset.classification_params = json.dumps(params)
                session.add(asset)
                migrated_count += 1
                print(f"Migrated asset {asset.id}: {sector_name} -> sector_area")
        
        await session.commit()
        print(f"Migration complete: {migrated_count} assets migrated")

if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate_sectors())
```

---

## Ordine di Esecuzione

1. ✅ Creare `backend/app/utils/sector_normalization.py`
2. ✅ Modificare `backend/app/utils/geo_normalization.py`
3. ✅ Modificare `backend/app/schemas/assets.py`
4. ✅ Creare `backend/app/schemas/utilities.py`
5. ✅ Creare `backend/app/api/v1/utilities.py`
6. ✅ Modificare `backend/app/api/v1/router.py` (registrare utilities)
7. ✅ Modificare `backend/app/api/v1/assets.py` (DELETE endpoint)
8. ✅ Modificare `backend/app/services/asset_source_providers/justetf.py`
9. ✅ Modificare `backend/app/services/asset_source.py`
10. ✅ Aggiornare tutti i test
11. ✅ (Opzionale) Eseguire script migrazione dati
12. ✅ Test completo: `./test_runner.py api all`

---

## Testing

### Test Unitari
```bash
# Test geo/sector normalization
./test_runner.py utils

# Test API utilities
./test_runner.py api utilities

# Test asset provider (justetf)
./test_runner.py external asset-providers

# Test CRUD con nuovo DELETE
./test_runner.py api assets-crud
```

### Test Integrazione
```bash
# Test completo
./test_runner.py api all
./test_runner.py external all
```

---

## TODO Futuri

1. **Espansione regioni** in `normalize_country()`:
   - EUR → [DEU, FRA, ITA, ESP, PRT, GRC, IRL, ...]
   - ASIA → [CHN, JPN, IND, KOR, SGP, ...]
   - Usare pycountry per mappare continenti/regioni

2. **Sector hierarchy** (opzionale):
   - Sub-settori (es. Technology → Software, Hardware, Semiconductors)
   - Mappatura GICS completa

3. **API endpoint per upsert prices**:
   - `POST /api/v1/assets/prices/{asset_id}`
   - Body: `List[FAPricePoint]`

---

## Stima Tempo

- **File creation**: 30 min
- **Schema refactoring**: 45 min
- **API updates**: 30 min
- **Provider updates**: 20 min
- **Test updates**: 30 min
- **Testing**: 30 min

**Totale: ~3 ore**
