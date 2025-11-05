"""
FX (Foreign Exchange) service.
Handles currency conversion and FX rate management with support for multiple providers.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from decimal import ROUND_DOWN

from sqlalchemy import func, select as sql_select, or_, and_
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.types import Numeric
from sqlmodel import select

from backend.app.db.models import FxRate

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_column_decimal_precision(model_class, column_name: str) -> tuple[int, int]:
    """
    Get the decimal precision (total, scale) from a Numeric column definition.

    This is a generic helper that works with any SQLModel table and Numeric column.

    Args:
        model_class: SQLModel class (e.g., FxRate, PriceHistory, Transaction)
        column_name: Name of the Numeric column

    Returns:
        tuple: (precision, scale) e.g. (24, 10) means 24 total digits, 10 after decimal

    Raises:
        AttributeError: If column doesn't exist
        ValueError: If column is not a Numeric type

    Example:
        precision, scale = get_column_decimal_precision(FxRate, 'rate')
        # Returns (24, 10) from Numeric(24, 10)
    """

    # Get the SQLAlchemy column from SQLModel
    if not hasattr(model_class, '__table__'):
        raise ValueError(f"{model_class.__name__} is not a SQLModel table")

    if column_name not in model_class.__table__.columns:
        raise AttributeError(f"Column '{column_name}' not found in {model_class.__name__}")

    column = model_class.__table__.columns[column_name]

    # Check if column is Numeric type
    if not isinstance(column.type, Numeric):
        raise ValueError(
            f"Column '{column_name}' in {model_class.__name__} is not a Numeric type "
            f"(found: {type(column.type).__name__})"
            )

    # Extract precision and scale from Numeric type
    return column.type.precision, column.type.scale


def truncate_decimal_to_db_precision(
    value: Decimal,
    model_class,
    column_name: str
    ) -> Decimal:
    """
    Truncate a Decimal value to match database column precision.

    This is a generic helper that prevents false "update" detections when comparing
    fetched values with stored values that have been truncated by the database.

    Args:
        value: Decimal value to truncate
        model_class: SQLModel class (e.g., FxRate, PriceHistory, Transaction)
        column_name: Name of the Numeric column

    Returns:
        Decimal: Value truncated to database precision

    Example:
        >>> from backend.app.db.models import FxRate
        >>> rate = Decimal("1.065757220505168922519450069")
        >>> truncate_decimal_to_db_precision(rate, FxRate, 'rate')
        Decimal("1.0657572205")  # Truncated to 10 decimals (Numeric(24, 10))
    """

    _, scale = get_column_decimal_precision(model_class, column_name)
    # Create quantization string: "0.0000000001" for scale=10
    quantize_str = "0." + "0" * scale
    return value.quantize(Decimal(quantize_str), rounding=ROUND_DOWN)


# Backward compatibility helpers for FxRate.rate column
def get_rate_decimal_precision() -> tuple[int, int]:
    """
    Get the decimal precision from FxRate.rate column.

    This is a convenience wrapper for backward compatibility.
    For new code, prefer get_column_decimal_precision(FxRate, 'rate').
    """
    return get_column_decimal_precision(FxRate, 'rate')


def truncate_rate_to_db_precision(rate: Decimal) -> Decimal:
    """
    Truncate a rate value to match FxRate.rate column precision.

    This is a convenience wrapper for backward compatibility.
    For new code, prefer truncate_decimal_to_db_precision(rate, FxRate, 'rate').
    """
    return truncate_decimal_to_db_precision(rate, FxRate, 'rate')


# Import providers to auto-register them
# This must be at the end of imports to avoid circular dependencies
# Providers will call FXProviderFactory.register() on import


# ============================================================================
# ABSTRACT BASE CLASS FOR FX PROVIDERS
# ============================================================================

class FXRateProvider(ABC):
    """
    Abstract base class for FX rate providers.

    Each provider represents a central bank or financial data source that
    provides authoritative exchange rates.

    Example providers:
    - ECBProvider: European Central Bank (EUR as base)
    - FEDProvider: Federal Reserve (USD as base)
    - BOEProvider: Bank of England (GBP as base)

    To add a new provider:
    1. Create a new class inheriting from FXRateProvider
    2. Implement all abstract methods
    3. Register in FXProviderFactory
    4. See docs/fx-provider-development-guide.md for details
    """

    @property
    @abstractmethod
    def code(self) -> str:
        """
        Provider code (e.g., 'ECB', 'FED', 'BOE').
        Used as identifier in database and configuration.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g., 'European Central Bank')."""
        pass

    @property
    @abstractmethod
    def base_currency(self) -> str:
        """
        Primary/default base currency for this provider (e.g., 'EUR' for ECB, 'USD' for FED).

        For single-base providers, this is the only base currency.
        For multi-base providers, this is the preferred/default base currency.

        Provider APIs typically return rates as:
        1 base_currency = X quote_currency
        """
        pass

    @property
    def base_currencies(self) -> list[str]:
        """
        List of base currencies supported by this provider.

        Single-base providers (ECB, FED, BOE, SNB) return a list with one element.
        Multi-base providers (e.g., commercial APIs) can return multiple currencies.

        Default implementation returns [self.base_currency] for backward compatibility.

        Returns:
            List of ISO 4217 currency codes that can be used as base

        Example:
            ECBProvider.base_currencies → ["EUR"]  # Single-base
            HypotheticalAPI.base_currencies → ["EUR", "GBP", "USD"]  # Multi-base
        """
        return [self.base_currency]

    @property
    def description(self) -> str:
        """
        Provider description.
        Override if you want custom description.
        """
        return f"Official exchange rates from {self.name}"

    @property
    def test_currencies(self) -> list[str]:
        """
        List of common currencies that should be available for testing.

        Override this to specify currencies that MUST be present for tests to pass.
        These are typically major currencies that the provider should always support.

        Default: Common major currencies
        """
        return ["USD", "EUR", "GBP", "JPY", "CHF"]

    @property
    def multi_unit_currencies(self) -> set[str]:
        """
        Set of currencies quoted per 100 units instead of per 1 unit.

        Some central banks quote certain currencies (typically those with small
        unit values) per 100 units to make rates more readable.

        Example:
        - Normal: 1 EUR = 1.08 USD
        - Multi-unit: 100 JPY = 0.67 CHF (instead of 1 JPY = 0.0067 CHF)

        Common multi-unit currencies:
        - JPY (Japanese Yen)
        - SEK (Swedish Krona)
        - NOK (Norwegian Krone)
        - DKK (Danish Krone)

        Override this property to specify which currencies this provider
        quotes per 100 units. Default is empty set (no multi-unit currencies).

        Returns:
            Set of ISO 4217 currency codes quoted per 100 units
        """
        return set()

    @abstractmethod
    async def get_supported_currencies(self) -> list[str]:
        """
        Get list of supported currencies for this provider.

        Implementation can be:
        - Static: return hardcoded list (if API doesn't provide list)
        - Dynamic: fetch from API (like ECB)
        - Cached: fetch once, cache in memory

        Returns:
            List of ISO 4217 currency codes (e.g., ['USD', 'GBP', 'JPY'])

        Raises:
            FXServiceError: If API request fails (for dynamic fetching)
        """
        pass

    @abstractmethod
    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str],
        base_currency: str | None = None
        ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch FX rates from provider API for given date range and currencies.

        Providers return raw data as provided by their API, with multi-unit
        adjustment applied if needed. NO inversion or alphabetical ordering.
        The service layer will handle normalization for database storage.

        Args:
            date_range: (start_date, end_date) inclusive
            currencies: List of quote currency codes to fetch
            base_currency: Base currency to use. If None, use provider's default base_currency.
                          Must be one of base_currencies. Single-base providers should
                          validate and raise ValueError if a different base is requested.

        Returns:
            Dictionary mapping currency -> [(date, base, quote, rate), ...]
            Where:
            - date: Rate date
            - base: Base currency used (specified base_currency or provider's default)
            - quote: Quote currency (from currencies list)
            - rate: Raw rate as provided by API (after multi-unit adjustment)

            Rate semantics: 1 base = rate * quote
            Example: (2025-01-01, 'EUR', 'USD', 1.08) means 1 EUR = 1.08 USD

        Example (single-base):
            ECB.fetch_rates((2025-01-01, 2025-01-03), ['USD', 'GBP'])
            Returns:
            {
                'USD': [
                    (date(2025-01-01), 'EUR', 'USD', Decimal('1.08')),
                    (date(2025-01-02), 'EUR', 'USD', Decimal('1.09')),
                ],
                'GBP': [
                    (date(2025-01-01), 'EUR', 'GBP', Decimal('0.85')),
                    (date(2025-01-02), 'EUR', 'GBP', Decimal('0.86')),
                ]
            }

        Example (multi-base with explicit base):
            HypAPI.fetch_rates((2025-01-01, 2025-01-03), ['JPY'], base_currency='USD')
            Returns:
            {
                'JPY': [
                    (date(2025-01-01), 'USD', 'JPY', Decimal('149.25')),
                    (date(2025-01-02), 'USD', 'JPY', Decimal('150.10')),
                ]
            }

        Raises:
            ValueError: If base_currency is not in base_currencies
            FXServiceError: If API request fails
        """
        pass


# ============================================================================
# SERVICE LAYER HELPER FUNCTIONS
# ============================================================================

def normalize_rate_for_storage(
    base: str,
    quote: str,
    rate: Decimal
    ) -> tuple[str, str, Decimal]:
    """
    Normalize FX rate for alphabetical storage in database.

    Database stores rates with: base < quote (alphabetically)
    This function handles the conversion if needed.

    Args:
        base: Base currency (e.g., 'EUR')
        quote: Quote currency (e.g., 'USD')
        rate: Rate value (1 base = rate * quote)

    Returns:
        Tuple of (normalized_base, normalized_quote, normalized_rate)

    Example:
        normalize_rate_for_storage('EUR', 'USD', 1.08)
        → ('EUR', 'USD', 1.08) because EUR < USD

        normalize_rate_for_storage('EUR', 'CHF', 0.95)
        → ('CHF', 'EUR', 1.0526...) because CHF < EUR (inverted)
    """
    if base < quote:
        # Already in correct order
        return base, quote, rate
    else:
        # Invert: swap currencies and invert rate
        return quote, base, Decimal("1") / rate


# ============================================================================
# PROVIDER FACTORY
# ============================================================================

class FXProviderFactory:
    """
    Factory for creating FX rate provider instances.

    Usage:
        provider = FXProviderFactory.get_provider('ECB')
        currencies = await provider.get_supported_currencies()
        rates = await provider.fetch_rates(date_range, currencies)
    """

    _providers: dict[str, type[FXRateProvider]] = {}

    @classmethod
    def register(cls, provider_class: type[FXRateProvider]) -> None:
        """
        Register a provider class.

        This is typically called automatically when a provider module is imported.

        Args:
            provider_class: Class inheriting from FXRateProvider

        Example:
            class ECBProvider(FXRateProvider):
                ...

            # Register automatically
            FXProviderFactory.register(ECBProvider)
        """
        instance = provider_class()
        code = instance.code.upper()
        cls._providers[code] = provider_class
        logger.info(f"Registered FX provider: {code} ({instance.name})")

    @classmethod
    def get_provider(cls, code: str) -> FXRateProvider:
        """
        Get provider instance by code.

        Args:
            code: Provider code (case-insensitive, e.g., 'ECB', 'ecb', 'Ecb')

        Returns:
            Provider instance

        Raises:
            ValueError: If provider not found

        Example:
            provider = FXProviderFactory.get_provider('ECB')
        """
        code_upper = code.upper()
        provider_class = cls._providers.get(code_upper)

        if not provider_class:
            available = ', '.join(sorted(cls._providers.keys()))
            raise ValueError(
                f"Unknown FX provider: {code}. "
                f"Available providers: {available or 'none registered'}"
                )

        return provider_class()

    @classmethod
    def get_all_providers(cls) -> list[dict]:
        """
        Get metadata for all registered providers.

        Returns:
            List of provider metadata dictionaries

        Example:
                [
                    {
                        'code': 'ECB',
                        'name': 'European Central Bank',
                        'base_currency': 'EUR',
                        'base_currencies': ['EUR'],
                        'description': 'Official rates from ECB'
                    },
                    {
                        'code': 'HYPAPI',
                        'name': 'Hypothetical Multi-Base API',
                        'base_currency': 'USD',
                        'base_currencies': ['EUR', 'GBP', 'USD'],
                        'description': 'Multi-base provider example'
                    },
                    ...
                ]
        """
        providers = []
        for code in sorted(cls._providers.keys()):
            provider_class = cls._providers[code]
            instance = provider_class()
            providers.append({
                'code': instance.code,
                'name': instance.name,
                'base_currency': instance.base_currency,
                'base_currencies': instance.base_currencies,
                'description': instance.description
                })
        return providers

    @classmethod
    def is_registered(cls, code: str) -> bool:
        """Check if a provider is registered."""
        return code.upper() in cls._providers


# ============================================================================
# LEGACY ECB CONSTANTS (TO BE MOVED TO ECBProvider)
# ============================================================================

# ECB API endpoints
# For detailed explanation of these parameters, see: docs/fx-implementation.md (ECB API Parameters section)
ECB_BASE_URL = "https://data-api.ecb.europa.eu/service/data"
ECB_DATASET = "EXR"  # Exchange Rates
ECB_FREQUENCY = "D"  # Daily
ECB_REFERENCE_AREA = "EUR"  # Base currency
ECB_SERIES = "SP00"  # Series variation (spot rate)


# ============================================================================
# EXCEPTIONS
# ============================================================================

class FXServiceError(Exception):
    """Base exception for FX service errors."""
    pass


class RateNotFoundError(FXServiceError):
    """Raised when no FX rate is found for a conversion."""
    pass


# ============================================================================
# MULTI-PROVIDER ORCHESTRATOR
# ============================================================================

async def ensure_rates_multi_source(
    session,  # AsyncSession
    date_range: tuple[date, date],
    currencies: list[str],
    provider_code: str = "ECB",
    base_currency: str | None = None
    ) -> dict[str, int]:
    """
    Synchronize FX rates using configured provider.

    This orchestrator uses the provider system to fetch rates from the appropriate source.
    It supports both single-base and multi-base providers.

    Algorithm:
    1. Get provider instance from factory
    2. Validate base_currency (if specified) against provider's supported bases
    3. Fetch rates from provider API with specified base
    4. Normalize rates for storage (alphabetical ordering)
    5. Batch upsert to database

    Args:
        session: Database session
        date_range: (start_date, end_date) inclusive
        currencies: List of currency codes to sync
        provider_code: Provider to use (default: 'ECB')
        base_currency: Base currency to use for multi-base providers.
                      If None, uses provider's default base_currency.
                      Must be one of provider's base_currencies.

    Returns:
        Dict with sync statistics:
        {
            'provider': 'ECB',
            'base_currency': 'EUR',
            'total_fetched': 100,
            'total_changed': 50,
            'currencies_synced': ['USD', 'GBP', ...]
        }

    Raises:
        ValueError: If base_currency is not supported by provider
        FXServiceError: If provider not found or API request fails
    """

    # Get provider instance
    try:
        provider = FXProviderFactory.get_provider(provider_code)
    except ValueError as e:
        raise FXServiceError(str(e)) from e

    # Validate base_currency if specified
    if base_currency is not None:
        if base_currency not in provider.base_currencies:
            raise ValueError(
                f"Provider {provider.code} does not support {base_currency} as base. "
                f"Supported bases: {', '.join(provider.base_currencies)}"
                )

    actual_base = base_currency if base_currency else provider.base_currency

    logger.info(
        f"Syncing FX rates using {provider.name} ({provider.code}) "
        f"with base {actual_base} "
        f"for {len(currencies)} currencies from {date_range[0]} to {date_range[1]}"
        )

    start_date, end_date = date_range

    # ========================================================================
    # PARALLEL EXECUTION: API fetch + DB query
    # ========================================================================

    # Build DB query for all possible pairs in the requested currencies and date range
    # This query fetches ALL rates between any of the requested currencies
    # (e.g., if currencies=['USD', 'GBP'], fetch USD/GBP, GBP/USD, etc.)
    all_pairs_conditions = []

    # Pairs between requested currencies
    for i, curr1 in enumerate(currencies):
        for curr2 in currencies[i + 1:]:  # Avoid duplicates, only pairs
            # Store alphabetically: smaller currency as base
            if curr1 < curr2:
                base, quote = curr1, curr2
            else:
                base, quote = curr2, curr1

            all_pairs_conditions.append(
                and_(
                    FxRate.base == base,
                    FxRate.quote == quote,
                    FxRate.date >= start_date,
                    FxRate.date <= end_date
                    )
                )

    # Also include pairs with the base currency (if different from requested currencies)
    if actual_base not in currencies:
        for currency in currencies:
            if actual_base < currency:
                base, quote = actual_base, currency
            else:
                base, quote = currency, actual_base

            all_pairs_conditions.append(
                and_(
                    FxRate.base == base,
                    FxRate.quote == quote,
                    FxRate.date >= start_date,
                    FxRate.date <= end_date
                    )
                )

    # Create tasks for parallel execution
    fetch_task = asyncio.create_task(
        provider.fetch_rates(date_range, currencies, base_currency=base_currency)
        )

    if all_pairs_conditions:
        existing_stmt = select(FxRate).where(or_(*all_pairs_conditions))
        db_task = asyncio.create_task(session.execute(existing_stmt))
    else:
        # No pairs to query (shouldn't happen, but handle gracefully)
        db_task = None

    # Wait for both operations to complete
    # Handle case where fx_rates table doesn't exist yet (fresh database)
    if db_task:
        try:
            rates_by_currency, db_result = await asyncio.gather(fetch_task, db_task)
            existing_rates = db_result.scalars().all()
            existing_lookup = {(rate.base, rate.quote, rate.date): rate.rate for rate in existing_rates}
        except Exception as e:
            # If table doesn't exist or other DB error, proceed with empty lookup
            # All rates will be considered new inserts
            logger.warning(
                f"Could not query existing rates (table may not exist yet): {e}. "
                f"Proceeding with fresh sync - all rates will be inserted."
                )
            rates_by_currency = await fetch_task
            existing_lookup = {}
    else:
        rates_by_currency = await fetch_task
        existing_lookup = {}

    # ========================================================================
    # Process API results and normalize for storage
    # ========================================================================

    # Statistics
    total_fetched = 0
    total_changed = 0
    currencies_synced = []

    # Normalize all observations and collect unique pairs from API
    all_normalized = []  # [(currency, obs_date, base, quote, rate), ...]
    api_pairs = set()  # {(base, quote, date), ...}

    for currency, observations in rates_by_currency.items():
        if not observations:
            logger.info(f"No rates available for {currency} in date range")
            continue

        currencies_synced.append(currency)
        total_fetched += len(observations)

        # Normalize for storage (alphabetical ordering)
        for obs_date, base, quote, rate in observations:
            norm_base, norm_quote, norm_rate = normalize_rate_for_storage(base, quote, rate)
            all_normalized.append((currency, obs_date, norm_base, norm_quote, norm_rate))
            api_pairs.add((norm_base, norm_quote, obs_date))

    # ========================================================================
    # Compare DB vs API: Log rates in DB but not in API
    # ========================================================================

    db_only_pairs = set(existing_lookup.keys()) - api_pairs
    if db_only_pairs:
        logger.info(
            f"Found {len(db_only_pairs)} rate(s) in database not returned by API "
            f"(this is normal if API doesn't provide historical data for some pairs)"
            )
        # Optional: Log first few examples at debug level
        for base, quote, rate_date in list(db_only_pairs)[:5]:
            logger.debug(f"  DB-only rate: {base}/{quote} on {rate_date}")

    # Track changes per currency (for logging)
    changes_by_currency = {}

    # Process each normalized observation
    for currency, obs_date, base, quote, rate_value in all_normalized:
        key = (base, quote, obs_date)
        old_rate = existing_lookup.get(key)

        # Truncate new rate to DB precision for comparison
        # This prevents false "updates" when values are identical after truncation
        rate_truncated = truncate_rate_to_db_precision(rate_value)

        if old_rate is None:
            # New insert
            if currency not in changes_by_currency:
                changes_by_currency[currency] = 0
            changes_by_currency[currency] += 1
            logger.debug(f"New rate: {base}/{quote} on {obs_date} = {rate_truncated}")
        else:
            # Truncate old rate too for proper comparison
            old_rate_truncated = truncate_rate_to_db_precision(old_rate)
            if old_rate_truncated != rate_truncated:
                # Updated value (only if different after truncation)
                if currency not in changes_by_currency:
                    changes_by_currency[currency] = 0
                changes_by_currency[currency] += 1
                logger.info(f"Updated rate: {base}/{quote} on {obs_date}: {old_rate_truncated} → {rate_truncated}")
        # else: Same value after truncation, no change to log

    total_changed = sum(changes_by_currency.values())

    # Process each currency for batch insert
    for currency, observations in rates_by_currency.items():
        if not observations:
            continue

        # Normalize for storage and truncate to DB precision
        normalized_observations = []
        for obs_date, base, quote, rate in observations:
            norm_base, norm_quote, norm_rate = normalize_rate_for_storage(base, quote, rate)
            # Truncate to DB precision to match what will actually be stored
            norm_rate_truncated = truncate_rate_to_db_precision(norm_rate)
            normalized_observations.append((obs_date, norm_base, norm_quote, norm_rate_truncated))

        if normalized_observations:
            _, base, quote, _ = normalized_observations[0]
            changed_count = changes_by_currency.get(currency, 0)

            # Batch INSERT/UPDATE with truncated rates
            values_list = [
                {
                    'date': obs_date,
                    'base': base,
                    'quote': quote,
                    'rate': rate_value,
                    'source': provider.code,
                    'fetched_at': func.current_timestamp()
                    }
                for obs_date, base, quote, rate_value in normalized_observations
                ]

            batch_stmt = insert(FxRate).values(values_list)
            batch_stmt = batch_stmt.on_conflict_do_update(
                index_elements=['date', 'base', 'quote'],
                set_={
                    'rate': batch_stmt.excluded.rate,
                    'source': batch_stmt.excluded.source,
                    'fetched_at': func.current_timestamp()
                    }
                )

            await session.execute(batch_stmt)

            logger.info(
                f"Synced {currency}: {len(observations)} fetched, "
                f"{changed_count} changed"
                )

    await session.commit()

    logger.info(
        f"Sync complete: {total_fetched} rates fetched, {total_changed} changed "
        f"from {provider.name} using base {actual_base}"
        )

    return {
        'provider': provider.code,
        'base_currency': actual_base,
        'total_fetched': total_fetched,
        'total_changed': total_changed,
        'currencies_synced': currencies_synced
        }


# ============================================================================
# CURRENCY CONVERSION FUNCTIONS
# ============================================================================


async def convert(
    session,  # AsyncSession
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    as_of_date: date,
    return_rate_info: bool = False
    ) -> Decimal | tuple[Decimal, date, bool]:
    """
    Convert a single amount from one currency to another.
    This is a convenience wrapper around convert_bulk() for single conversions.

    Args:
        session: Database session
        amount: Amount to convert
        from_currency: Source currency code (ISO 4217)
        to_currency: Target currency code (ISO 4217)
        as_of_date: Date for which to use the FX rate
        return_rate_info: If True, return (amount, rate_date, backward_fill_applied)

    Returns:
        If return_rate_info=False: Converted amount
        If return_rate_info=True: Tuple of (converted_amount, rate_date, backward_fill_applied)

    Raises:
        RateNotFoundError: If no rate is found at all for this currency pair
    """
    # Call bulk version with single item (raise_on_error=True for backward compatibility)
    results, errors = await convert_bulk(
        session,
        [(amount, from_currency, to_currency, as_of_date)],
        raise_on_error=True
        )

    converted_amount, rate_date, backward_fill_applied = results[0]

    if return_rate_info:
        return converted_amount, rate_date, backward_fill_applied
    return converted_amount


async def convert_bulk(
    session,  # AsyncSession
    conversions: list[tuple[Decimal, str, str, date]],  # [(amount, from, to, date), ...]
    raise_on_error: bool = True
    ) -> tuple[list[tuple[Decimal, date, bool] | None], list[str]]:
    """
    Convert multiple amounts in a single batch operation. Use date in fx_rates table already cached.
    Uses unlimited backward-fill: if rate for exact date is not found,
    uses the most recent rate available (no time limit).

    Rates are stored alphabetically (base < quote): 1 base = rate * quote

    Args:
        session: Database session
        conversions: List of (amount, from_currency, to_currency, as_of_date) tuples
        raise_on_error: If True, raise on first error. If False, collect errors and continue

    Returns:
        Tuple of (results, errors) where:
        - results: List of (converted_amount, rate_date, backward_fill_applied) or None for failed conversions
        - errors: List of error messages for failed conversions

        If raise_on_error=True, raises on first error (legacy behavior)

    Raises:
        RateNotFoundError: If any conversion fails and raise_on_error=True
    """
    if not conversions:
        return ([], [])

    # OPTIMIZATION: Collect all unique currency pairs needed
    pairs_needed = {}  # {(base, quote, max_date): [indices_needing_this_pair]}
    conversion_metadata = []  # Store metadata for each conversion

    for idx, (amount, from_currency, to_currency, as_of_date) in enumerate(conversions):
        # Identity conversions don't need DB lookup
        if from_currency == to_currency:
            conversion_metadata.append({
                'idx': idx,
                'amount': amount,
                'from': from_currency,
                'to': to_currency,
                'date': as_of_date,
                'identity': True
                })
            continue

        # Determine alphabetical ordering
        if from_currency < to_currency:
            base, quote = from_currency, to_currency
            direct = True
        else:
            base, quote = to_currency, from_currency
            direct = False

        conversion_metadata.append({
            'idx': idx,
            'amount': amount,
            'from': from_currency,
            'to': to_currency,
            'date': as_of_date,
            'identity': False,
            'base': base,
            'quote': quote,
            'direct': direct
            })

        # Group conversions by pair and max date needed
        # We'll fetch the most recent rate for each pair that satisfies all dates
        pair_key = (base, quote)
        if pair_key not in pairs_needed:
            pairs_needed[pair_key] = {'max_date': as_of_date, 'indices': []}
        else:
            # Track the maximum date needed for this pair
            if as_of_date > pairs_needed[pair_key]['max_date']:
                pairs_needed[pair_key]['max_date'] = as_of_date

        pairs_needed[pair_key]['indices'].append(idx)

    # OPTIMIZATION: Single batch query for all needed rates
    # Build OR clauses for all pairs
    if pairs_needed:

        conditions = []
        for (base, quote), info in pairs_needed.items():
            # For each pair, get all rates up to the max date needed
            conditions.append(
                and_(
                    FxRate.base == base,
                    FxRate.quote == quote,
                    FxRate.date <= info['max_date']
                    )
                )

        # Single query fetching all rates needed
        stmt = select(FxRate).where(or_(*conditions)).order_by(
            FxRate.base, FxRate.quote, FxRate.date.desc()
            )

        result = await session.execute(stmt)
        all_rates = result.scalars().all()

        # Build lookup dictionary: {(base, quote): [rates_sorted_desc_by_date]}
        rates_lookup = {}
        for rate in all_rates:
            pair_key = (rate.base, rate.quote)
            if pair_key not in rates_lookup:
                rates_lookup[pair_key] = []
            rates_lookup[pair_key].append(rate)
    else:
        rates_lookup = {}

    # Process conversions using cached rates
    results = []
    errors = []

    for meta in conversion_metadata:
        idx = meta['idx']

        try:
            # Identity conversion
            if meta['identity']:
                results.append((meta['amount'], meta['date'], False))
                continue

            # Find appropriate rate for this conversion
            pair_key = (meta['base'], meta['quote'])
            pair_rates = rates_lookup.get(pair_key, [])

            # Find first rate <= requested date (backward-fill)
            rate_record = None
            for rate in pair_rates:
                if rate.date <= meta['date']:
                    rate_record = rate
                    break

            if not rate_record:
                # No rate found at all for this pair
                error_msg = (
                    f"No FX rate found for {meta['base']}/{meta['quote']} on or before {meta['date']}. "
                    f"Please sync rates using POST /api/v1/fx/sync/bulk"
                )
                if raise_on_error:
                    raise RateNotFoundError(f"Conversion failed at index {idx}: {error_msg}")
                else:
                    errors.append(f"Conversion {idx}: {error_msg}")
                    results.append(None)
                    continue

            # Track if backward-fill was applied
            backward_fill_applied = rate_record.date < meta['date']

            # Log if using backward-fill
            if backward_fill_applied:
                days_back = (meta['date'] - rate_record.date).days
                logger.info(
                    f"Using backward-fill: rate for {meta['base']}/{meta['quote']} from {rate_record.date} "
                    f"({days_back} days back, requested: {meta['date']})"
                    )

            # Apply conversion
            if meta['direct']:
                converted = meta['amount'] * rate_record.rate
            else:
                converted = meta['amount'] / rate_record.rate

            results.append((converted, rate_record.date, backward_fill_applied))

        except RateNotFoundError:
            if raise_on_error:
                raise
            # Already appended error above
        except Exception as e:
            error_msg = f"Conversion {idx} failed: {str(e)}"
            if raise_on_error:
                raise RateNotFoundError(error_msg) from e
            else:
                errors.append(error_msg)
                results.append(None)

    return (results, errors)


async def upsert_rates_bulk(
    session,  # AsyncSession
    rates: list[tuple[date, str, str, Decimal, str]]  # [(date, base, quote, rate, source), ...]
    ) -> list[tuple[bool, str]]:  # [(success, action), ...]
    """
    Insert or update multiple FX rates in a single batch operation.

    Args:
        session: Database session
        rates: List of (date, base, quote, rate, source) tuples

    Returns:
        List of (success, action) tuples where action is 'inserted' or 'updated'
        Results are in the same order as input rates

    Raises:
        ValueError: If validation fails for any rate
    """

    if not rates:
        return []

    # Validate and normalize all rates first
    normalized_rates = []
    for rate_date, base, quote, rate_value, source in rates:
        base = base.upper()
        quote = quote.upper()

        if base == quote:
            raise ValueError(f"Base and quote must be different (got {base} == {quote})")

        if rate_value <= 0:
            raise ValueError(f"Rate must be positive (got {rate_value})")

        # Ensure alphabetical ordering
        if base > quote:
            base, quote = quote, base
            rate_value = Decimal("1") / rate_value

        normalized_rates.append((rate_date, base, quote, rate_value, source))

    # OPTIMIZATION: Single batch query to check all existing rates
    conditions = []
    for rate_date, base, quote, _, _ in normalized_rates:
        conditions.append(
            and_(
                FxRate.date == rate_date,
                FxRate.base == base,
                FxRate.quote == quote
                )
            )

    # Fetch all existing rates in one query
    stmt = sql_select(FxRate).where(or_(*conditions))
    result = await session.execute(stmt)
    existing_rates = result.scalars().all()

    # Build lookup set for existing rates
    existing_keys = {
        (rate.date, rate.base, rate.quote)
        for rate in existing_rates
        }

    # OPTIMIZATION: Prepare results tracking (before batch insert)
    results = []
    for rate_date, base, quote, rate_value, source in normalized_rates:
        key = (rate_date, base, quote)
        action = "updated" if key in existing_keys else "inserted"
        results.append((True, action))

    # OPTIMIZATION: Single batch INSERT with multiple VALUES
    # Prepare all values for batch insert
    values_list = [
        {
            'date': rate_date,
            'base': base,
            'quote': quote,
            'rate': rate_value,
            'source': source,
            'fetched_at': func.current_timestamp()
            }
        for rate_date, base, quote, rate_value, source in normalized_rates
        ]

    # Single batch INSERT statement (all rates at once)
    batch_insert = insert(FxRate).values(values_list)

    # On conflict: update all fields for each row
    batch_insert = batch_insert.on_conflict_do_update(
        index_elements=['date', 'base', 'quote'],
        set_={
            'rate': batch_insert.excluded.rate,
            'source': batch_insert.excluded.source,
            'fetched_at': func.current_timestamp()
            }
        )

    # Execute single batch statement (replaces N individual executes)
    await session.execute(batch_insert)

    # Single commit for all upserts
    await session.commit()
    return results


async def delete_rates_bulk(
    session,  # AsyncSession
    deletions: list[tuple[str, str, date, date | None]]  # [(from_currency, to_currency, start_date, end_date?), ...]
    ) -> list[tuple[bool, int, int, str | None]]:  # [(success, existing_count, deleted_count, message), ...]
    """
    Delete multiple FX rates in a single batch operation.

    This function efficiently handles bulk deletions by:
    1. Normalizing all currency pairs (alphabetical ordering)
    2. Fetching existing counts in a single batch query (optimization)
    3. Executing deletions in a single batch (optimization)

    Args:
        session: Database session
        deletions: List of (from_currency, to_currency, start_date, end_date?) tuples
                  - from_currency, to_currency: Will be normalized to alphabetical order
                  - start_date: Start date (inclusive)
                  - end_date: End date (inclusive), optional. If None, only start_date is deleted

    Returns:
        List of (success, existing_count, deleted_count, message) tuples
        - success: Always True (errors handled gracefully)
        - existing_count: Number of rates present before deletion
        - deleted_count: Number of rates actually deleted
        - message: Warning/error message if any (e.g., "no rates found")

    Example:
        deletions = [
            ("USD", "EUR", date(2025, 1, 1), None),  # Single day
            ("GBP", "USD", date(2025, 1, 1), date(2025, 1, 5))  # Range
        ]
        results = await delete_rates_bulk(session, deletions)
    """
    from sqlalchemy import delete as sql_delete, func as sql_func

    if not deletions:
        return []

    # Normalize all deletions (alphabetical ordering)
    normalized_deletions = []
    for from_cur, to_cur, start_date, end_date in deletions:
        from_cur = from_cur.upper()
        to_cur = to_cur.upper()

        # Normalize to alphabetical order (base < quote)
        if from_cur > to_cur:
            base, quote = to_cur, from_cur
        else:
            base, quote = from_cur, to_cur

        normalized_deletions.append((base, quote, start_date, end_date))

    # OPTIMIZATION: Single batch query to fetch ALL matching rates across all deletions
    # Build OR conditions for all deletions
    all_conditions = []
    for base, quote, start_date, end_date in normalized_deletions:
        if end_date:
            # Date range
            condition = and_(
                FxRate.base == base,
                FxRate.quote == quote,
                FxRate.date >= start_date,
                FxRate.date <= end_date
            )
        else:
            # Single date
            condition = and_(
                FxRate.base == base,
                FxRate.quote == quote,
                FxRate.date == start_date
            )
        all_conditions.append(condition)

    # SINGLE QUERY: Fetch all matching rates (id, base, quote, date)
    stmt = sql_select(FxRate.id, FxRate.base, FxRate.quote, FxRate.date).where(
        or_(*all_conditions)
    )
    result = await session.execute(stmt)
    all_matching_rates = result.all()

    # Build lookup: {(base, quote, date): id}
    rate_lookup = {(r.base, r.quote, r.date): r.id for r in all_matching_rates}

    # Count existing rates per deletion request
    existing_counts = {}
    ids_to_delete = set()

    for idx, (base, quote, start_date, end_date) in enumerate(normalized_deletions):
        count = 0
        for (r_base, r_quote, r_date), r_id in rate_lookup.items():
            if r_base == base and r_quote == quote:
                if end_date:
                    # Check if date is in range
                    if start_date <= r_date <= end_date:
                        count += 1
                        ids_to_delete.add(r_id)
                else:
                    # Check if date matches exactly
                    if r_date == start_date:
                        count += 1
                        ids_to_delete.add(r_id)

        existing_counts[idx] = count

    # CHUNKED DELETE: Remove all matched IDs in batches to avoid SQLite limits
    # SQLite has SQLITE_MAX_VARIABLE_NUMBER = 999 by default
    # We use chunks of 500 to be safe and improve performance with large datasets
    deleted_count_total = 0
    if ids_to_delete:
        ids_list = list(ids_to_delete)
        chunk_size = 500  # Safe for SQLite (max 999) and optimal for performance

        # Process in chunks within same transaction
        for i in range(0, len(ids_list), chunk_size):
            chunk = ids_list[i:i + chunk_size]
            delete_stmt = sql_delete(FxRate).where(FxRate.id.in_(chunk))
            delete_result = await session.execute(delete_stmt)
            deleted_count_total += delete_result.rowcount

        logger.info(f"Deleted {deleted_count_total} rate(s) in {(len(ids_list) + chunk_size - 1) // chunk_size} batch(es)")

    # Build results per deletion request
    results = []
    for idx, (base, quote, start_date, end_date) in enumerate(normalized_deletions):
        existing_count = existing_counts[idx]
        deleted_count = existing_count  # All existing were deleted

        # Prepare result message
        message = None
        if deleted_count == 0:
            if end_date:
                message = f"No rates found for {base}/{quote} from {start_date} to {end_date}"
            else:
                message = f"No rates found for {base}/{quote} on {start_date}"

        results.append((True, existing_count, deleted_count, message))

    # Single commit for all deletions
    await session.commit()

    return results


# ============================================================================
# AUTO-REGISTER PROVIDERS
# ============================================================================
# Import providers to register them automatically in the factory
# This happens when the fx module is imported
from backend.app.services.fx_providers.ecb import ECBProvider  # noqa: F401
from backend.app.services.fx_providers.fed import FEDProvider  # noqa: F401
from backend.app.services.fx_providers.boe import BOEProvider  # noqa: F401
from backend.app.services.fx_providers.snb import SNBProvider  # noqa: F401
