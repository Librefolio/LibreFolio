"""
FX (Foreign Exchange) service.
Handles currency conversion and FX rate management with support for multiple providers.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select as sql_select, or_, and_
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.app.db.models import FxConversionRoute, FxRate
from backend.app.db.session import get_async_engine
from backend.app.logging_config import get_logger
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.refresh import FXSyncPairResult, SyncStatus, FXSyncBulkResponse, FXSyncLegDetail
from backend.app.services.provider_registry import FXProviderRegistry
from backend.app.utils.cache_utils import get_ttl_cache
from backend.app.utils.decimal_utils import truncate_fx_rate

logger = get_logger(__name__)

# Cache for FX provider fetch responses — TTL 5min since FX rates update daily.
# Prevents provider rate-limiting if user triggers repeated syncs.
_fx_fetch_cache = get_ttl_cache("fx_provider_responses", maxsize=200, ttl=300)


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
    3. Add @register_provider(FXProviderRegistry) decorator
    4. Place in backend/app/services/fx_providers/ directory
    5. Provider will be auto-discovered on startup
    6. See docs/fx/provider-development.md for details
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
    def icon(self) -> str | None:
        """
        Return provider icon URL (hardcoded).

        Returns:
            Optional icon URL string (can be remote or local path)
        """
        return None  # Default: no icon

    @classmethod
    def generate_static_url(cls, relative_path: str) -> str:
        """
        Generate URL for a static asset in the plugin's static folder.

        Use this to reference icons, images, or other static files
        bundled with your plugin.

        Structure:
            fx_providers/static/{relative_path}

        Args:
            relative_path: Path relative to static folder (e.g., "ecb/logo.png")

        Returns:
            Full URL path (e.g., "/api/v1/uploads/plugin/fx/ecb/logo.png")

        Example:
            class ECBProvider(FXRateProvider):
                def get_icon(self) -> str:
                    return self.generate_static_url("ecb/logo.svg")
        """
        return f"/api/v1/uploads/plugin/fx/{relative_path}"

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

        # ARCHITECTURAL NOTE: multi-base
        # As of March 2026, ALL implemented providers have exactly 1 base currency.
        # The pipeline (sync_pairs_bulk, ensure_rates_multi_source, frontend currency
        # graph) implicitly assumes single-base per provider. When adding a multi-base
        # provider (e.g., Open Exchange Rates, Fixer.io), the following must be reworked:
        #   1. Pipeline Phase 1 grouping key: (provider, base_currency) instead of just provider
        #   2. ensure_rates_multi_source(): explicit base_currency routing
        #   3. Frontend buildCurrencyGraph(): multi-base edge generation
        #   4. chain_steps schema: may need explicit base_currency per step
        # See: plan-fxConversionChain.prompt.md §"Nota architetturale: Multi-base provider"

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
    def description_i18n(self) -> dict[str, str]:
        """
        Multilingual provider descriptions.

        Returns a dict mapping language code → description string.
        Override in subclasses to provide localized descriptions.

        Must include at least 'en'. Frontend falls back to 'en' if
        the requested language is not available.

        Returns:
            Dict[str, str] — e.g. {"en": "...", "it": "...", "fr": "...", "es": "..."}
        """
        return {"en": self.description}

    @property
    def warning_i18n(self) -> dict[str, str]:
        """
        Multilingual provider warnings/caveats.

        Override in subclasses to surface data-quality warnings to the user.
        When non-empty, the frontend displays a ⚠️ triangle on routes using
        this provider, with a tooltip showing the warning text.

        Default: empty dict (no warning).

        Returns:
            Dict[str, str] — e.g. {"en": "...", "it": "...", ...}
        """
        return {}

    @property
    def docs_url(self) -> str | None:
        """
        URL to the documentation page for this provider.

        Override in subclasses to point to a specific docs page.
        Default returns the generic providers list page.

        Returns:
            Optional URL string
        """
        return "/mkdocs/developer/backend/fx/providers_list/"

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
        self, date_range: tuple[date, date], currencies: list[str], base_currency: str | None = None
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

    def shutdown(self) -> None:
        """
        Cleanup resources on application shutdown.

        Override to release persistent connections, stop background threads,
        flush caches, etc.  Called once per provider during app lifespan teardown
        via ``FXProviderRegistry.shutdown_all_providers()``.

        Default: no-op.
        """
        pass


# ============================================================================
# SERVICE LAYER HELPER FUNCTIONS
# ============================================================================


def normalize_rate_for_storage(base: str, quote: str, rate: Decimal) -> tuple[str, str, Decimal]:
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
    provider_code: str,
    base_currency: str | None = None,
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

    if not provider_code:
        raise FXServiceError("Provider code is required")

    # MANUAL provider: skip sync silently — manual pairs don't auto-sync
    if provider_code.upper() == "MANUAL":
        logger.info(
            f"MANUAL provider: skipping sync for {len(currencies)} currencies "
            f"({date_range[0]} to {date_range[1]}) — manual-only pair"
            )
        return {
            "provider": "MANUAL",
            "base_currency": "",
            "total_fetched": 0,
            "total_changed": 0,
            "currencies_synced": [],
            }

    # Get provider instance from registry
    provider = FXProviderRegistry.get_provider_instance(provider_code)
    if not provider:
        available = [p["code"] for p in FXProviderRegistry.list_providers()]
        raise FXServiceError(
            f"Unknown FX provider: {provider_code}. "
            f"Available providers: {', '.join(available) if available else 'none registered'}"
            )

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
                    FxRate.date <= end_date,
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
                    FxRate.date <= end_date,
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
            logger.debug(
                f"Change detection: {len(existing_lookup)} existing rate(s) found in DB "
                f"for {len(all_pairs_conditions)} pair condition(s)"
                )
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
        rate_truncated = truncate_fx_rate(rate_value)

        if old_rate is None:
            # New insert
            if currency not in changes_by_currency:
                changes_by_currency[currency] = 0
            changes_by_currency[currency] += 1
        else:
            # Truncate old rate too for proper comparison
            old_rate_truncated = truncate_fx_rate(old_rate)
            if old_rate_truncated != rate_truncated:
                # Updated value (only if different after truncation)
                if currency not in changes_by_currency:
                    changes_by_currency[currency] = 0
                changes_by_currency[currency] += 1
                logger.debug(f"Updated rate: {base}/{quote} on {obs_date}: {old_rate_truncated} -> {rate_truncated}")
        # else: Same value after truncation, no change to log

    total_changed = sum(changes_by_currency.values())

    if total_changed == 0 and total_fetched > 0:
        logger.info(
            f"All {total_fetched} fetched rate(s) already exist in DB with same values "
            f"(existing_lookup={len(existing_lookup)}, all_normalized={len(all_normalized)})"
            )

    # Process each currency for batch insert
    for currency, observations in rates_by_currency.items():
        if not observations:
            continue

        # Normalize for storage and truncate to DB precision
        normalized_observations = []
        for obs_date, base, quote, rate in observations:
            norm_base, norm_quote, norm_rate = normalize_rate_for_storage(base, quote, rate)
            # Truncate to DB precision to match what will actually be stored
            norm_rate_truncated = truncate_fx_rate(norm_rate)
            normalized_observations.append((obs_date, norm_base, norm_quote, norm_rate_truncated))

        if normalized_observations:
            _, base, quote, _ = normalized_observations[0]
            changed_count = changes_by_currency.get(currency, 0)

            # Batch INSERT/UPDATE with truncated rates
            values_list = [
                {
                    "date": obs_date,
                    "base": base,
                    "quote": quote,
                    "rate": rate_value,
                    "source": provider.code,
                    "fetched_at": func.current_timestamp(),
                    }
                for obs_date, base, quote, rate_value in normalized_observations
                ]

            batch_stmt = insert(FxRate).values(values_list)
            batch_stmt = batch_stmt.on_conflict_do_update(
                index_elements=["date", "base", "quote"],
                set_={
                    "rate": batch_stmt.excluded.rate,
                    "source": batch_stmt.excluded.source,
                    "fetched_at": func.current_timestamp(),
                    },
                )

            await session.execute(batch_stmt)

            logger.info(
                f"Synced {currency}: {len(observations)} fetched, " f"{changed_count} changed"
                )

    await session.commit()

    logger.info(
        f"Sync complete: {total_fetched} rates fetched, {total_changed} changed "
        f"from {provider.name} using base {actual_base}"
        )

    return {
        "provider": provider.code,
        "base_currency": actual_base,
        "total_fetched": total_fetched,
        "total_changed": total_changed,
        "currencies_synced": currencies_synced,
        }


# ============================================================================
# CHAIN COMPUTATION
# ============================================================================


def compute_chain_rate(
    steps: list[dict],
    leg_rates: dict[tuple, Decimal],
    target_date: date,
    ) -> Decimal | None:
    """
    Compute the composite rate for a chain of conversions on a specific date.

    For each step (from_cur, to_cur):
    - Normalize alphabetically: (min, max) for lookup in leg_rates
    - If from_cur < to_cur (direct order): multiply by rate
    - If from_cur > to_cur (inverse order): multiply by 1/rate

    **Strict date matching**: ALL legs must have data for the exact target_date.
    If any leg is missing, returns None and this date is skipped.
    This means chains using providers with sparse data (e.g. SNB monthly)
    will only produce rates on dates where every leg has fresh data.

    Returns: composite rate, or None if any leg is missing for this date.
    """
    composite = Decimal("1")
    for step in steps:
        fc = step["from"]
        tc = step["to"]
        # Normalize alphabetically for lookup
        norm_base = min(fc, tc)
        norm_quote = max(fc, tc)
        key = (norm_base, norm_quote, target_date)
        rate = leg_rates.get(key)
        if rate is None:
            return None
        if fc < tc:
            # Direct order: multiply by rate
            composite *= rate
        else:
            # Inverse order: multiply by 1/rate
            composite *= Decimal("1") / rate
    return composite


# ============================================================================
# PAIR-BASED SYNC (New API)
# ============================================================================


async def _count_actual_changes(
    session,  # AsyncSession
    computed_rates: list[tuple[date, str, str, Decimal]],
    ) -> int:
    """
    Count how many of the computed rates are actually new or changed vs DB.

    Loads existing rates for the same (base, quote, date) tuples from the DB,
    compares with truncated precision, and returns the count of genuine changes.
    This avoids reporting points_changed == points_fetched when re-syncing
    the same date range with identical data.

    Args:
        session: AsyncSession for DB queries
        computed_rates: list of (date, base, quote, rate) — rate already truncated

    Returns:
        Number of rates that are new inserts or actual value changes.
    """
    if not computed_rates:
        return 0

    # Build lookup of new rates
    new_lookup = {(d, b, q): r for d, b, q, r in computed_rates}

    # Load existing rates for comparison
    conditions = []
    for d, b, q, _ in computed_rates:
        conditions.append(and_(FxRate.base == b, FxRate.quote == q, FxRate.date == d))

    # Batch query — chunk if too many conditions (SQLite limit ~999 params)
    existing_lookup: dict[tuple, Decimal] = {}
    chunk_size = 200
    for i in range(0, len(conditions), chunk_size):
        chunk = conditions[i:i + chunk_size]
        stmt = select(FxRate.base, FxRate.quote, FxRate.date, FxRate.rate).where(or_(*chunk))
        result = await session.execute(stmt)
        for row in result.all():
            existing_lookup[(row[2], row[0], row[1])] = row[3]

    # Count changes
    changed = 0
    for d, b, q, new_rate in computed_rates:
        key = (d, b, q)
        old_rate = existing_lookup.get(key)
        if old_rate is None:
            # New insert
            changed += 1
        elif truncate_fx_rate(old_rate) != new_rate:
            # Value actually changed
            changed += 1
    return changed


async def sync_pairs_bulk(
    session,  # AsyncSession — used only for reading route config
    pairs: list[str],  # ["EUR-USD", "CHF-CNY"]
    date_range: tuple[date, date],
    ) -> "FXSyncBulkResponse":
    """
    Sync multiple FX pairs using the 3-phase pipeline:

    Phase 1: Collect legs from all routes, group by provider, create Events
    Phase 2: Fetch in parallel per provider, populate leg_rates, signal Events
    Phase 3: Route coroutines await Events, compute chain rates, upsert+commit

    Parallelization:
    - Inter-provider: different providers fetched in parallel
    - Intra-provider: currencies within same provider fetched in parallel (asyncio.gather in ECB/FED/BOE)
    - Route computation: routes awaiting different legs proceed as soon as their data is ready

    Commit per pair (not atomic bulk): partial success OK.
    """
    start_date, end_date = date_range
    t_start_ns = time.monotonic_ns()

    # Load ALL route configurations in one query
    stmt = select(FxConversionRoute).order_by(FxConversionRoute.base, FxConversionRoute.quote, FxConversionRoute.priority)
    db_result = await session.execute(stmt)
    all_routes = db_result.scalars().all()

    # Build lookup: (base, quote) → [route1, route2, ...] ordered by priority
    route_lookup: dict[tuple[str, str], list] = {}
    for r in all_routes:
        key = (r.base, r.quote)
        if key not in route_lookup:
            route_lookup[key] = []
        route_lookup[key].append(r)

    # ── Phase 1: Collect legs, group by provider, create Events ──
    # For each pair, use the primary (priority=1) route
    pair_route_map: dict[str, "FxConversionRoute"] = {}  # pair_slug → route
    provider_legs: dict[str, set[str]] = {}  # provider_code → {target_currencies}
    leg_events: dict[tuple[str, str, str], asyncio.Event] = {}  # (norm_base, norm_quote, provider) → Event
    leg_rates: dict[tuple, Decimal] = {}  # (norm_base, norm_quote, date) → rate
    leg_errors: dict[tuple[str, str, str], str] = {}  # (norm_base, norm_quote, provider) → error msg

    for pair_slug in pairs:
        base, quote = pair_slug.split("-")
        routes = route_lookup.get((base, quote), [])
        if not routes:
            pair_route_map[pair_slug] = None
            continue

        # Use primary route (first by priority)
        route = routes[0]
        pair_route_map[pair_slug] = route
        steps = route.parsed_steps

        # Skip MANUAL-only routes
        if all(s["provider"].upper() == "MANUAL" for s in steps):
            continue

        for step in steps:
            provider_code = step["provider"]
            if provider_code.upper() == "MANUAL":
                continue

            provider = FXProviderRegistry.get_provider_instance(provider_code)
            if not provider:
                continue

            fc, tc = step["from"], step["to"]
            base_cur = provider.base_currency

            # Determine target currency from provider's perspective
            if fc == base_cur:
                target_cur = tc
            elif tc == base_cur:
                target_cur = fc
            else:
                # Neither from nor to is the provider's base — error
                continue

            if provider_code not in provider_legs:
                provider_legs[provider_code] = set()
            provider_legs[provider_code].add(target_cur)

            # Create Event for this leg
            norm_b = min(fc, tc)
            norm_q = max(fc, tc)
            leg_key = (norm_b, norm_q, provider_code)
            if leg_key not in leg_events:
                leg_events[leg_key] = asyncio.Event()

    # ── Phase 2: Fetch in parallel per provider ──
    async def _fetch_provider(provider_code: str, target_currencies: set[str]):
        """Fetch all currencies for one provider, populate leg_rates, signal Events."""
        try:
            provider = FXProviderRegistry.get_provider_instance(provider_code)
            if not provider:
                raise FXServiceError(f"Unknown provider: {provider_code}")

            # Check TTL cache — skip provider fetch if recent data available
            cache_key = (provider_code, frozenset(target_currencies), date_range)
            cached_result, cache_hit = _fx_fetch_cache.get(cache_key)
            if cache_hit:
                logger.debug("FX provider cache hit, skipping fetch",
                             provider=provider_code, currencies=len(target_currencies))
                rates_by_currency = cached_result
            else:
                rates_by_currency = await provider.fetch_rates(date_range, list(target_currencies), base_currency=None)
                _fx_fetch_cache.set(cache_key, rates_by_currency)

            for currency, observations in rates_by_currency.items():
                for obs_date, obs_base, obs_quote, rate in observations:
                    norm_base, norm_quote, norm_rate = normalize_rate_for_storage(obs_base, obs_quote, rate)
                    leg_rates[(norm_base, norm_quote, obs_date)] = norm_rate

            # Signal all events for this provider
            for target_cur in target_currencies:
                base_cur = provider.base_currency
                norm_b = min(base_cur, target_cur)
                norm_q = max(base_cur, target_cur)
                leg_key = (norm_b, norm_q, provider_code)
                if leg_key in leg_events:
                    leg_events[leg_key].set()

        except Exception as e:
            logger.error(f"Provider {provider_code} fetch failed: {e}")
            provider = FXProviderRegistry.get_provider_instance(provider_code)
            base_cur = provider.base_currency if provider else ""
            for target_cur in target_currencies:
                norm_b = min(base_cur, target_cur)
                norm_q = max(base_cur, target_cur)
                leg_key = (norm_b, norm_q, provider_code)
                leg_errors[leg_key] = str(e)
                if leg_key in leg_events:
                    leg_events[leg_key].set()  # Signal anyway so coroutines don't hang

    provider_tasks = [_fetch_provider(prov, targets) for prov, targets in provider_legs.items()]
    if provider_tasks:
        await asyncio.gather(*provider_tasks)

    # ── Phase 3: Route coroutines — await Events, compute, upsert+commit ──
    async def _process_route(pair_slug: str) -> FXSyncPairResult:
        """Process a single route: await legs, compute chain rate, upsert."""
        t_route_start = time.monotonic_ns()  # Per-route timer
        route = pair_route_map.get(pair_slug)

        if route is None:
            return FXSyncPairResult(
                pair=pair_slug,
                status=SyncStatus.FAILED,
                provider_used=None,
                points_fetched=0,
                points_changed=0,
                message=None,
                errors=[f"No route configuration found for {pair_slug}"],
                elapsed_ms=(time.monotonic_ns() - t_route_start) // 1_000_000,
                )

        steps = route.parsed_steps

        # Check MANUAL-only
        if all(s["provider"].upper() == "MANUAL" for s in steps):
            return FXSyncPairResult(
                pair=pair_slug,
                status=SyncStatus.SKIPPED,
                provider_used=None,
                points_fetched=0,
                points_changed=0,
                message="Manual-only pair, nothing to sync",
                elapsed_ms=None,
                )

        try:
            # Wait for all leg events
            my_events = []
            my_leg_keys = []
            for step in steps:
                fc, tc = step["from"], step["to"]
                prov = step["provider"]
                norm_b = min(fc, tc)
                norm_q = max(fc, tc)
                leg_key = (norm_b, norm_q, prov)
                if leg_key in leg_events:
                    my_events.append(leg_events[leg_key].wait())
                    my_leg_keys.append(leg_key)

            if my_events:
                try:
                    await asyncio.wait_for(asyncio.gather(*my_events), timeout=120.0)
                except asyncio.TimeoutError:
                    raise FXServiceError(
                        f"Timeout waiting for provider data for {pair_slug} "
                        f"(waited 120s for {len(my_events)} leg(s))"
                        )

            # Check for failed legs
            for lk in my_leg_keys:
                if lk in leg_errors:
                    raise FXServiceError(f"Leg {lk[0]}-{lk[1]} ({lk[2]}) failed: {leg_errors[lk]}")

            if len(steps) == 1:
                # 1-step direct route
                step = steps[0]
                provider_code = step["provider"]
                fc, tc = step["from"], step["to"]

                # Collect rates for this pair from leg_rates
                norm_b = min(route.base, route.quote)
                norm_q = max(route.base, route.quote)

                computed_rates = []
                for key, rate in leg_rates.items():
                    if key[0] == norm_b and key[1] == norm_q:
                        d = key[2]
                        if start_date <= d <= end_date:
                            computed_rates.append((d, norm_b, norm_q, truncate_fx_rate(rate)))

                if computed_rates:
                    async with AsyncSession(get_async_engine(), expire_on_commit=False) as pair_session:
                        actual_changed = await _count_actual_changes(pair_session, computed_rates)

                        values_list = [
                            {
                                "date": d, "base": b, "quote": q, "rate": r,
                                "source": provider_code,
                                "fetched_at": func.current_timestamp(),
                                }
                            for d, b, q, r in computed_rates
                            ]
                        batch_stmt = insert(FxRate).values(values_list)
                        batch_stmt = batch_stmt.on_conflict_do_update(
                            index_elements=["date", "base", "quote"],
                            set_={
                                "rate": batch_stmt.excluded.rate,
                                "source": batch_stmt.excluded.source,
                                "fetched_at": func.current_timestamp(),
                                },
                            )
                        await pair_session.execute(batch_stmt)
                        await pair_session.commit()
                else:
                    actual_changed = 0

                elapsed_ms = (time.monotonic_ns() - t_route_start) // 1_000_000
                partial_msg = None if computed_rates else (
                    f"Provider {provider_code} returned no data for "
                    f"{route.base}/{route.quote} in {start_date}–{end_date}"
                )
                # Build per-leg detail for single-step route
                leg_detail = None
                if not computed_rates:
                    leg_detail = [
                        FXSyncLegDetail(
                            provider=provider_code,
                            leg=f"{fc}→{tc}",
                            dates_available=0,
                            error=None,
                            )
                        ]
                return FXSyncPairResult(
                    pair=pair_slug,
                    status=SyncStatus.OK if computed_rates else SyncStatus.PARTIAL,
                    provider_used=provider_code,
                    points_fetched=len(computed_rates),
                    points_changed=actual_changed,
                    message=partial_msg,
                    detail=leg_detail,
                    elapsed_ms=elapsed_ms,
                    )
            else:
                # Multi-step chain
                providers_used = [s["provider"] for s in steps]
                source = "CHAIN:" + "+".join(providers_used)

                # Collect all dates from leg_rates
                all_dates = sorted({key[2] for key in leg_rates.keys()
                                    if start_date <= key[2] <= end_date})

                computed_rates = []
                for d in all_dates:
                    chain_rate = compute_chain_rate(steps, leg_rates, d)
                    if chain_rate is not None:
                        norm_base, norm_quote, norm_rate = normalize_rate_for_storage(route.base, route.quote, chain_rate)
                        norm_rate = truncate_fx_rate(norm_rate)
                        computed_rates.append((d, norm_base, norm_quote, norm_rate))

                if computed_rates:
                    async with AsyncSession(get_async_engine(), expire_on_commit=False) as pair_session:
                        actual_changed = await _count_actual_changes(pair_session, computed_rates)

                        values_list = [
                            {
                                "date": d, "base": b, "quote": q, "rate": r,
                                "source": source,
                                "fetched_at": func.current_timestamp(),
                                }
                            for d, b, q, r in computed_rates
                            ]
                        batch_stmt = insert(FxRate).values(values_list)
                        batch_stmt = batch_stmt.on_conflict_do_update(
                            index_elements=["date", "base", "quote"],
                            set_={
                                "rate": batch_stmt.excluded.rate,
                                "source": batch_stmt.excluded.source,
                                "fetched_at": func.current_timestamp(),
                                },
                            )
                        await pair_session.execute(batch_stmt)
                        await pair_session.commit()
                else:
                    actual_changed = 0

                elapsed_ms = (time.monotonic_ns() - t_route_start) // 1_000_000

                # Build per-leg detail for diagnostics
                chain_leg_details = []
                for step in steps:
                    fc, tc = step["from"], step["to"]
                    prov = step["provider"]
                    norm_b = min(fc, tc)
                    norm_q = max(fc, tc)
                    leg_key_prefix = (norm_b, norm_q)
                    # Count dates this leg has in the requested range
                    leg_date_count = sum(
                        1 for key in leg_rates.keys()
                        if key[0] == leg_key_prefix[0]
                        and key[1] == leg_key_prefix[1]
                        and start_date <= key[2] <= end_date
                        )
                    # Check if this leg had errors
                    leg_err_key = (norm_b, norm_q, prov)
                    leg_error = leg_errors.get(leg_err_key)
                    chain_leg_details.append(FXSyncLegDetail(
                        provider=prov,
                        leg=f"{fc}→{tc}",
                        dates_available=leg_date_count,
                        error=str(leg_error) if leg_error else None,
                        ))

                # Build human-readable message and errors list
                chain_errors: list[str] = []
                if computed_rates:
                    chain_partial_msg = None
                    chain_detail = chain_leg_details  # always include detail for chains
                else:
                    leg_summaries = []
                    for ld in chain_leg_details:
                        if ld.error:
                            leg_summaries.append(f"  • {ld.leg} ({ld.provider}): ERROR — {ld.error}")
                            chain_errors.append(f"{ld.leg} ({ld.provider}): {ld.error}")
                        elif ld.dates_available == 0:
                            leg_summaries.append(f"  • {ld.leg} ({ld.provider}): 0 dates — no data returned")
                        else:
                            leg_summaries.append(f"  • {ld.leg} ({ld.provider}): {ld.dates_available} dates available")
                    chain_partial_msg = (
                        f"Chain {source} produced no complete rates for "
                        f"{route.base}/{route.quote} in {start_date}–{end_date} "
                        f"({len(all_dates)} dates checked).\n"
                        f"Per-leg breakdown:\n" + "\n".join(leg_summaries)
                    )
                    chain_detail = chain_leg_details

                return FXSyncPairResult(
                    pair=pair_slug,
                    status=SyncStatus.OK if computed_rates else SyncStatus.PARTIAL,
                    provider_used=source,
                    points_fetched=len(computed_rates),
                    points_changed=actual_changed,
                    message=chain_partial_msg,
                    errors=chain_errors,
                    detail=chain_detail,
                    elapsed_ms=elapsed_ms,
                    )

        except Exception as e:
            elapsed_ms = (time.monotonic_ns() - t_route_start) // 1_000_000
            logger.error(f"Pair {pair_slug}: sync failed: {e}")
            return FXSyncPairResult(
                pair=pair_slug,
                status=SyncStatus.FAILED,
                provider_used=None,
                points_fetched=0,
                points_changed=0,
                message=None,
                errors=[str(e)],
                elapsed_ms=elapsed_ms,
                )

    # ── Dispatch all routes and assemble response ──
    pair_results = await asyncio.gather(*[_process_route(slug) for slug in pairs])
    result_list = list(pair_results)

    success_count = sum(1 for r in result_list if r.status in (SyncStatus.OK, SyncStatus.PARTIAL, SyncStatus.SKIPPED))
    total_changed = sum(r.points_changed for r in result_list)

    return FXSyncBulkResponse(
        results=result_list,
        success_count=success_count,
        date_range=DateRangeModel(start=start_date, end=end_date),
        total_points_changed=total_changed,
        )


# ============================================================================
# CURRENCY CONVERSION FUNCTIONS
# ============================================================================


async def convert_bulk(
    session,  # AsyncSession
    conversions: list[tuple[Currency, str, date]],  # [(amount_currency, to_currency, date), ...]
    raise_on_error: bool = True,
    ) -> tuple[list[tuple[Currency, date, bool] | None], list[str]]:
    """
    Convert multiple Currency amounts in a single batch operation.
    Uses unlimited backward-fill: if rate for exact date is not found,
    uses the most recent rate available (no time limit).

    ⚡ BREAKING CHANGE: Now accepts/returns Currency objects instead of Decimal.

    Rates are stored alphabetically (base < quote): 1 base = rate * quote

    Args:
        session: Database session
        conversions: List of (Currency, to_currency, as_of_date) tuples
                     where Currency contains amount + from_currency
        raise_on_error: If True, raise on first error. If False, collect errors and continue

    Returns:
        Tuple of (results, errors) where:
        - results: List of (Currency, rate_date, backward_fill_applied) or None for failed conversions
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

    for idx, (amount_currency, to_currency, as_of_date) in enumerate(conversions):
        # Extract from Currency object
        amount = amount_currency.amount
        from_currency = amount_currency.code

        # Identity conversions don't need DB lookup
        if from_currency == to_currency:
            conversion_metadata.append(
                {
                    "idx": idx,
                    "amount": amount,
                    "from": from_currency,
                    "to": to_currency,
                    "date": as_of_date,
                    "identity": True,
                    }
                )
            continue

        # Determine alphabetical ordering
        if from_currency < to_currency:
            base, quote = from_currency, to_currency
            direct = True
        else:
            base, quote = to_currency, from_currency
            direct = False

        conversion_metadata.append(
            {
                "idx": idx,
                "amount": amount,
                "from": from_currency,
                "to": to_currency,
                "date": as_of_date,
                "identity": False,
                "base": base,
                "quote": quote,
                "direct": direct,
                }
            )

        # Group conversions by pair and max date needed
        # We'll fetch the most recent rate for each pair that satisfies all dates
        pair_key = (base, quote)
        if pair_key not in pairs_needed:
            pairs_needed[pair_key] = {"max_date": as_of_date, "indices": []}
        else:
            # Track the maximum date needed for this pair
            if as_of_date > pairs_needed[pair_key]["max_date"]:
                pairs_needed[pair_key]["max_date"] = as_of_date

        pairs_needed[pair_key]["indices"].append(idx)

    # OPTIMIZATION: Single batch query for all needed rates
    # Build OR clauses for all pairs
    if pairs_needed:

        conditions = []
        for (base, quote), info in pairs_needed.items():
            # For each pair, get all rates up to the max date needed
            conditions.append(
                and_(FxRate.base == base, FxRate.quote == quote, FxRate.date <= info["max_date"])
                )

        # Single query fetching all rates needed
        stmt = (
            select(FxRate)
            .where(or_(*conditions))
            .order_by(FxRate.base, FxRate.quote, FxRate.date.desc())
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
        idx = meta["idx"]

        try:
            # Identity conversion - same currency, return as Currency object
            if meta["identity"]:
                result_currency = Currency(code=meta["to"], amount=meta["amount"])
                results.append((result_currency, meta["date"], False))
                continue

            # Find appropriate rate for this conversion
            pair_key = (meta["base"], meta["quote"])
            pair_rates = rates_lookup.get(pair_key, [])

            # Find first rate <= requested date (backward-fill)
            rate_record = None
            for rate in pair_rates:
                if rate.date <= meta["date"]:
                    rate_record = rate
                    break

            if not rate_record:
                # No rate found at all for this pair
                error_msg = (
                    f"No FX rate found for {meta['base']}/{meta['quote']} on or before {meta['date']}. "
                    f"Please sync rates using POST /api/v1/fx/currencies/sync"
                )
                if raise_on_error:
                    raise RateNotFoundError(f"Conversion failed at index {idx}: {error_msg}")
                else:
                    errors.append(f"Conversion {idx}: {error_msg}")
                    results.append(None)
                    continue

            # Track if backward-fill was applied
            backward_fill_applied = rate_record.date < meta["date"]

            # Log if using backward-fill
            if backward_fill_applied:
                days_back = (meta["date"] - rate_record.date).days
                logger.debug(
                    "backward_fill_applied",
                    pair=f"{meta['base']}/{meta['quote']}",
                    rate_date=str(rate_record.date),
                    requested_date=str(meta["date"]),
                    days_back=days_back,
                    )

            # Apply conversion
            if meta["direct"]:
                converted_amount = meta["amount"] * rate_record.rate
            else:
                converted_amount = meta["amount"] / rate_record.rate

            # Return Currency object with target currency
            result_currency = Currency(code=meta["to"], amount=converted_amount)
            results.append((result_currency, rate_record.date, backward_fill_applied))

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

    return results, errors


async def upsert_rates_bulk(
    session,  # AsyncSession
    rates: list[tuple[date, str, str, Decimal, str]],  # [(date, base, quote, rate, source), ...]
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
            and_(FxRate.date == rate_date, FxRate.base == base, FxRate.quote == quote)
            )

    # Fetch all existing rates in one query
    stmt = sql_select(FxRate).where(or_(*conditions))
    result = await session.execute(stmt)
    existing_rates = result.scalars().all()

    # Build lookup set for existing rates
    existing_keys = {(rate.date, rate.base, rate.quote) for rate in existing_rates}

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
            "date": rate_date,
            "base": base,
            "quote": quote,
            "rate": rate_value,
            "source": source,
            "fetched_at": func.current_timestamp(),
            }
        for rate_date, base, quote, rate_value, source in normalized_rates
        ]

    # Single batch INSERT statement (all rates at once)
    batch_insert = insert(FxRate).values(values_list)

    # On conflict: update all fields for each row
    batch_insert = batch_insert.on_conflict_do_update(
        index_elements=["date", "base", "quote"],
        set_={
            "rate": batch_insert.excluded.rate,
            "source": batch_insert.excluded.source,
            "fetched_at": func.current_timestamp(),
            },
        )

    # Execute single batch statement (replaces N individual executes)
    await session.execute(batch_insert)

    # Single commit for all upserts
    await session.commit()
    return results


async def delete_rates_bulk(
    session,  # AsyncSession
    deletions: list[
        tuple[str, str, date, date | None]
    ],  # [(from_currency, to_currency, start_date, end_date?), ...]
    ) -> list[
    tuple[bool, int, int, str | None]
]:  # [(success, existing_count, deleted_count, message), ...]
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
                FxRate.date <= end_date,
                )
        else:
            # Single date
            condition = and_(FxRate.base == base, FxRate.quote == quote, FxRate.date == start_date)
        all_conditions.append(condition)

    # SINGLE QUERY: Fetch all matching rates (id, base, quote, date)
    stmt = sql_select(FxRate.id, FxRate.base, FxRate.quote, FxRate.date).where(or_(*all_conditions))
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
            chunk = ids_list[i: i + chunk_size]
            delete_stmt = sql_delete(FxRate).where(FxRate.id.in_(chunk))
            delete_result = await session.execute(delete_stmt)
            deleted_count_total += delete_result.rowcount

        logger.info(
            f"Deleted {deleted_count_total} rate(s) in {(len(ids_list) + chunk_size - 1) // chunk_size} batch(es)"
            )

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
