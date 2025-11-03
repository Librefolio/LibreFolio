"""
FX (Foreign Exchange) service.
Handles currency conversion and FX rate management with support for multiple providers.
"""
import logging
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select as sql_select, or_, and_
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import select

from backend.app.db.models import FxRate

logger = logging.getLogger(__name__)


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

    # Fetch rates from provider with specified base
    rates_by_currency = await provider.fetch_rates(date_range, currencies, base_currency=base_currency)

    # Statistics
    total_fetched = 0
    total_changed = 0
    currencies_synced = []

    start_date, end_date = date_range

    # Process each currency
    for currency, observations in rates_by_currency.items():
        if not observations:
            logger.info(f"No rates available for {currency} in date range")
            continue

        currencies_synced.append(currency)
        total_fetched += len(observations)

        # Normalize for storage (alphabetical ordering)
        # Observations now come as (date, base, quote, rate)
        normalized_observations = []
        for obs_date, base, quote, rate in observations:
            # Apply alphabetical normalization
            norm_base, norm_quote, norm_rate = normalize_rate_for_storage(base, quote, rate)
            normalized_observations.append((obs_date, norm_base, norm_quote, norm_rate))

        # Get base/quote from first observation (all same for this currency after normalization)
        if normalized_observations:
            _, base, quote, _ = normalized_observations[0]

            # Query existing rates for tracking changes
            existing_stmt = select(FxRate).where(
                FxRate.base == base,
                FxRate.quote == quote,
                FxRate.date >= start_date,
                FxRate.date <= end_date
                )
            result = await session.execute(existing_stmt)
            existing_rates = result.scalars().all()
            existing_by_date = {rate.date: rate.rate for rate in existing_rates}

            # Track changes for logging
            changed_count = 0
            for obs_date, _, _, rate_value in normalized_observations:
                old_rate = existing_by_date.get(obs_date)
                if old_rate is None:
                    # New insert
                    changed_count += 1
                    logger.debug(f"New rate: {base}/{quote} on {obs_date} = {rate_value}")
                elif old_rate != rate_value:
                    # Updated value
                    changed_count += 1
                    logger.info(f"Updated rate: {base}/{quote} on {obs_date}: {old_rate} → {rate_value}")

            total_changed += changed_count

            # Batch INSERT/UPDATE
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
    Convert multiple amounts in a single batch operation.
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
                    f"Please sync rates using POST /api/v1/fx/sync"
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


# ============================================================================
# AUTO-REGISTER PROVIDERS
# ============================================================================
# Import providers to register them automatically in the factory
# This happens when the fx module is imported
from backend.app.services.fx_providers.ecb import ECBProvider  # noqa: F401
from backend.app.services.fx_providers.fed import FEDProvider  # noqa: F401
from backend.app.services.fx_providers.boe import BOEProvider  # noqa: F401
from backend.app.services.fx_providers.snb import SNBProvider  # noqa: F401
