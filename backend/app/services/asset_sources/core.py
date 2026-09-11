"""
Asset pricing source service.

This module provides:
- AssetSourceProvider: Abstract base class for pricing providers
- AssetSourceManager: Manager for provider operations and price data
- Synthetic yield calculation for SCHEDULED_YIELD assets
- Backward-fill logic for missing price data
- Helper functions for decimal precision

Similar to fx.py but for price_history table (asset prices vs FX rates).

Key differences from FX:
- Table: price_history (not fx_rates)
- Fields: OHLC (open/high/low/close) + volume (not single rate)
- Lookup: (asset_id, date) not (base, quote, date)
- Synthetic yield: Calculated on-demand for SCHEDULED_YIELD assets

Design principles:
- Bulk-first: All operations have bulk version as PRIMARY
- Singles call bulk with 1 element
- DB optimization: Minimize queries (typically 1-3 max)
- Parallel provider calls where possible
"""

import asyncio
import functools
import hashlib
import json
from abc import ABC, abstractmethod
from datetime import date as date_type
from typing import Dict, Literal, Optional

from backend.app.db.models import (
    IdentifierType,
    ProviderInputType,
)
from backend.app.logging_config import get_logger
from backend.app.schemas import (
    FACurrentValue,
    FAHistoricalData,
    FAPricePoint,
)
from backend.app.schemas.assets import (
    FAAssetPatchItem,
)
from backend.app.schemas.provider import (
    FAProviderKind,
    FAVolumeKind,
)
from backend.app.utils.cache_utils import get_ttl_cache

# Initialize structured logger
logger = get_logger(__name__)

# ============================================================================
# CORE CACHES — automatic TTL expiration via theine timer wheel
# ============================================================================

_asset_history_cache = get_ttl_cache("asset_history_fetch", maxsize=500, ttl=900)  # 15 min
_asset_current_cache = get_ttl_cache("asset_current_fetch", maxsize=300, ttl=120)  # 2 min
_asset_metadata_cache = get_ttl_cache("asset_metadata_fetch", maxsize=200, ttl=1800)  # 30 min
_search_result_cache = get_ttl_cache("search_results", maxsize=5000, ttl=86400)  # 24h — individual items
_search_query_cache = get_ttl_cache("search_queries", maxsize=500, ttl=900)  # 15 min — query→results
_RISK_WARMUP_DAY_MULTIPLIER = 2

AssetHistoryStartDate = date_type | Literal["min"]
ASSET_HISTORY_MIN_FALLBACK = date_type(1900, 1, 1)


def _provider_params_hash(provider_params: Optional[dict]) -> str:
    """
    Stable short hash of `provider_params` for use in cache keys (#R3-4).

    Uses MD5 (non-cryptographic, just for keying) over the JSON-serialized params
    with sorted keys to guarantee determinism regardless of dict iteration order.
    Returns the first 8 hex chars — enough entropy to avoid collisions across the
    small number of concurrently-cached keys per asset.
    """
    if not provider_params:
        return "none"
    try:
        payload = json.dumps(provider_params, sort_keys=True, default=str)
    except Exception:
        payload = repr(sorted(provider_params.items()))
    return hashlib.md5(payload.encode("utf-8")).hexdigest()[:8]


def _parse_provider_params(raw_params):
    """Parse stored provider params into a dictionary."""
    if raw_params is None:
        return {}
    if isinstance(raw_params, dict):
        return raw_params
    if isinstance(raw_params, str):
        try:
            return json.loads(raw_params)
        except Exception:
            return {}
    return {}


# ============================================================================
# THREAD ISOLATION FOR PROVIDER CALLS
# ============================================================================


async def _run_provider_in_thread(coro_factory, *, timeout: float = 60.0):
    """
    Run a provider coroutine in a dedicated thread with its own event loop.

    Protects the main event loop from blocking provider implementations.
    Even a well-written async provider (httpx) works fine — it just uses
    the thread's event loop instead of the main one.

    A badly-written provider that does `requests.get()` directly in an
    async def will block the thread, NOT the main event loop.

    Args:
        coro_factory: Zero-arg callable that returns the coroutine to run.
                     Example: lambda: provider.get_current_value(id, type, params)
        timeout: Maximum time to wait (seconds). Default 60s.

    Returns:
        Result of the coroutine.

    Raises:
        asyncio.TimeoutError: If provider takes longer than timeout.
        Any exception raised by the provider.
    """

    def _sync_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_factory())
        finally:
            loop.close()

    return await asyncio.wait_for(
        asyncio.to_thread(_sync_runner),
        timeout=timeout,
    )


# (Pydantic models for API request/response live in backend.app.schemas.assets)
# They are imported by API modules when needed


# ============================================================================
# EXCEPTIONS
# ============================================================================


class AssetSourceError(Exception):
    """Base exception for asset source errors."""

    def __init__(self, message: str, error_code: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


def _json_safe_details(details: Optional[dict]) -> Optional[dict]:
    """Make an AssetSourceError ``details`` dict safe for a JSON response (I3).

    Providers may put dates, Decimals or other non-primitives in ``details``;
    the probe DTO must serialize, so anything not natively JSON-safe is
    stringified. ``None`` and empty dicts stay ``None`` (field omitted).

    Deliberately NOT :func:`backend.app.utils.json_utils.ensure_json_safe`:
    that one is a *validator* — it rejects non-JSON producer output on contract
    boundaries (signals, AI Export). Here the provider is a third-party plugin
    and the probe must still return a localized error, so we *sanitize*
    (stringify, one list level deep) instead of raising. See
    ``backend/app/utils/json_utils.py`` module docstring (audit 08, report 03 §N-03-A).
    """
    if not details:
        return None
    safe: dict = {}
    for key, value in details.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            safe[str(key)] = value
        elif isinstance(value, (list, tuple)):
            safe[str(key)] = [item if item is None or isinstance(item, (str, int, float, bool)) else str(item) for item in value]
        else:
            safe[str(key)] = str(value)
    return safe


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================


def _repair_ohlc_point(point: FAPricePoint) -> tuple[FAPricePoint, bool]:
    """Widen a point's [low, high] bounds to contain open and close.

    Returns ``(point, changed)``. ``close`` and the traded range are never altered —
    only ``low``/``high`` are extended when they would otherwise exclude a real price
    (e.g. an official fixing reported outside the day's traded range). Points already
    consistent are returned unchanged with ``changed=False``.
    """
    low, high = point.low, point.high
    if low is None or high is None:
        return point, False
    candidates = [v for v in (point.open, point.close) if v is not None]
    if not candidates:
        return point, False
    new_low = min([low, *candidates])
    new_high = max([high, *candidates])
    if new_low == low and new_high == high:
        return point, False
    return point.model_copy(update={"low": new_low, "high": new_high}), True


def _wrap_history_ohlc_guard(func):
    """Post-execution guard: repair impossible-OHLC points from any provider.

    Applied to every concrete ``get_history_value`` via ``__init_subclass__`` so no
    plugin has to remember to call it. Repairs are logged at DEBUG with the count of
    adjusted points — the source values are never dropped, only the candle bounds widened.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> FAHistoricalData:
        result = await func(*args, **kwargs)
        prices = getattr(result, "prices", None)
        if not prices:
            return result
        repaired: list[FAPricePoint] = []
        n_changed = 0
        for p in prices:
            np_, changed = _repair_ohlc_point(p)
            repaired.append(np_)
            n_changed += int(changed)
        if n_changed:
            provider = args[0] if args else None
            pcode = getattr(provider, "provider_code", provider.__class__.__name__ if provider is not None else "?")
            logger.debug(f"OHLC guard: widened [low, high] to contain open/close on {n_changed}/{len(prices)} point(s) from provider '{pcode}'")
            result = result.model_copy(update={"prices": repaired})
        return result

    wrapper._ohlc_guarded = True  # type: ignore[attr-defined]
    return wrapper


class AssetSourceProvider(ABC):
    """
    Abstract base class for asset pricing providers (plugins).

    ARCHITECTURE: Plugin vs Core Responsibilities
    =============================================

    PLUGIN (this class implementations) is responsible for:
    - Fetching RAW data from external sources (APIs, web scraping, etc.)
    - Returning data in the expected schema format (FACurrentValue, FAHistoricalData)
    - Handling provider-specific errors and converting them to AssetSourceError
    - Validating provider_params specific to each provider

    CORE (AssetSourceService) is responsible for:
    - Database storage and caching of fetched data
    - Backward-filling historical prices (filling gaps with last known value)
    - Currency conversion if needed
    - Merging data from multiple sources
    - Transaction management and error recovery

    CORE INFRASTRUCTURE: Thread Isolation & Cache
    ==============================================

    The core runs ALL provider method calls (get_current_value, get_history_value,
    fetch_asset_metadata, search) in a **dedicated thread with its own event loop**
    via _run_provider_in_thread(). This means:

    - You do NOT need asyncio.to_thread() in your provider — the core handles it.
    - Even sync libraries (requests, yfinance) are safe to call directly in your
      async def methods — they block the dedicated thread, NOT the main event loop.
    - Timeout protection: the core enforces per-call timeouts.

    The core also caches results automatically:
    - get_history_value → smart range cache (15min TTL, per-date granularity)
    - get_current_value → 2min TTL cache
    - fetch_asset_metadata → 30min TTL cache
    - search → 2-layer cache (query-level 15min + item-level 24h)

    If you have expensive sub-operations (e.g., currency discovery, ETF list fetch),
    use your own internal caches — the core caches only the final result.

    Example flow for get_history_value:
    1. Core calls plugin.get_history_value(start, end)
    2. Plugin fetches RAW prices from external API (only trading days)
    3. Plugin returns FAHistoricalData with prices list (may have gaps)
    4. Core applies _backward_fill_prices() to fill weekends/holidays
    5. Core stores filled data in database

    Required implementations:
    - provider_code: Unique identifier for this provider
    - provider_name: Human-readable name
    - test_cases: Test data for automated testing
    - get_current_value(): Fetch latest price
    - get_history_value(): Fetch historical prices (raw, no filling)
    - test_search_query: Search query for tests (None if search unsupported)

    Optional overrides:
    - get_icon(): Provider icon URL
    - supports_history: False if provider cannot fetch historical data
    - search(): Search for assets by query
    - validate_params(): Validate provider-specific parameters
    - fetch_asset_metadata(): Fetch asset metadata (type, sector, etc.)

    Providers auto-register via @register_provider(AssetProviderRegistry) decorator.
    """

    def __init_subclass__(cls, **kwargs):
        """Wrap each concrete ``get_history_value`` with a post-execution OHLC guard.

        Some sources (e.g. Borsa Italiana EuroTLX) report the official daily fixing
        as ``close`` even when it falls outside the day's traded ``[low, high]``
        range — legitimate data, but it violates the core upsert integrity rule
        (``low ≤ close ≤ high``) and would be rejected. Wrapping here — at class
        definition, transparently for every present and future plugin — widens the
        candle bounds around ``open``/``close`` instead of dropping real prices.
        """
        super().__init_subclass__(**kwargs)
        impl = cls.__dict__.get("get_history_value")
        if impl is None or getattr(impl, "_ohlc_guarded", False):
            return
        cls.get_history_value = _wrap_history_ohlc_guard(impl)

    @property
    @abstractmethod
    def provider_code(self) -> str:
        """
        Unique provider identifier used in database and API.

        Examples: 'yfinance', 'justetf', 'cssscraper'

        Must be:
        - Lowercase alphanumeric with underscores
        - Unique across all registered providers
        - Stable (changing breaks existing assets)
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Human-readable provider name for UI display.

        Examples: 'Yahoo Finance', 'JustETF', 'CSS Web Scraper'
        """

    @property
    def provider_kind(self) -> FAProviderKind:
        """
        Classifies the provider by how it produces its data (#R3-4).

        Two kinds are currently defined:

        - ``FAProviderKind.ONLINE_SCRAPER`` (default): fetches raw data from
          an external source. Changing ``provider_params`` does NOT invalidate
          the historical series already persisted in the DB (the data came
          from outside the params).
        - ``FAProviderKind.PARAMETRIC_GENERATION``: produces the series
          deterministically from ``provider_params``. A params change means
          the existing series is obsolete **by definition** — callers such as
          ``bulk_assign_providers`` must wipe previously-persisted prices and
          regenerate to stay consistent.

        Override in parametric providers (e.g. scheduled_investment) to
        return ``FAProviderKind.PARAMETRIC_GENERATION``. The default is safe
        for all online/scraping providers.

        The value is exposed to the frontend via ``FAProviderInfo.kind`` and
        used to pick UI labels ("Sync" vs "Regenerate") and decide whether a
        params change requires a destructive-confirm dialog.
        """
        return FAProviderKind.ONLINE_SCRAPER

    @property
    def supports_meaningful_volume(self) -> bool:
        """
        Declares whether this provider's ``volume`` field represents real,
        comparable trading activity (e.g. exchange-traded share volume)
        rather than being absent, synthetic, or of unverified origin.

        Default is ``False`` (safe/unknown). Override to ``True`` only when
        the source's semantics are unambiguous — e.g. a provider that
        surfaces genuine exchange-traded share volume for the instruments it
        serves. Do NOT infer this per-asset-type; a provider that mixes
        volume-bearing and volume-less request paths (e.g. NAV-priced funds
        vs ISIN-quoted stocks under the same provider) should still declare
        the provider-level truth here, and rely on downstream structural
        validation (sufficient non-null observed volume) to reject the
        volume-less paths at the signal level.

        Consumed by ``AssetSourceService`` to derive
        ``SignalSourceCapability`` for volume-dependent signals (MFI, OBV),
        and surfaced to the frontend via ``FAProviderInfo.supports_meaningful_volume``.
        """
        return False

    @property
    def volume_kind(self) -> FAVolumeKind:
        """
        Semantic kind of the volume field when ``supports_meaningful_volume``
        is ``True``. Default ``FAVolumeKind.UNKNOWN``; override alongside
        ``supports_meaningful_volume`` (e.g. ``FAVolumeKind.TRADED_SHARES``).
        """
        return FAVolumeKind.UNKNOWN

    @property
    def get_icon(self) -> str | None:
        """
        Provider icon URL for UI display.

        Returns:
            URL string (remote or local path), or None for default icon
        """
        return None

    @property
    def provider_help_url(self) -> str | None:
        """
        URL to the provider documentation page served by the running instance.

        Returns:
            URL string (e.g., "/mkdocs/user/assets/providers/yahoo-finance/"), or None
        """
        return None

    @classmethod
    def generate_static_url(cls, relative_path: str) -> str:
        """
        Generate URL for a static asset in the plugin's static folder.

        Use this to reference icons, images, or other static files
        bundled with your plugin.

        Structure:
            asset_source_providers/static/{relative_path}

        Args:
            relative_path: Path relative to static folder (e.g., "yfinance/logo.png")

        Returns:
            Full URL path (e.g., "/api/v1/uploads/plugin/asset/yfinance/logo.png")

        Example:
            class YahooFinanceProvider(AssetSourceProvider):
                def get_icon(self) -> str:
                    return self.generate_static_url("yfinance/logo.png")
        """
        return f"/api/v1/uploads/plugin/asset/{relative_path}"

    @property
    @abstractmethod
    def test_cases(self) -> list[dict]:
        """
        Test cases for automated provider testing.

        Each test case must include:
        - identifier: str - Asset identifier to test
        - identifier_type: IdentifierType - Type of identifier
        - provider_params: dict | None - Provider-specific params (if needed)

        Example:
            [
                {
                    'identifier': 'AAPL',
                    'identifier_type': IdentifierType.TICKER,
                    'provider_params': None
                },
                {
                    'identifier': 'https://example.com/price',
                    'identifier_type': IdentifierType.URL,
                    'provider_params': {'css_selector': '.price', 'currency': 'EUR'}
                }
            ]
        """

    @abstractmethod
    async def get_current_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict,
    ) -> FACurrentValue:
        """
        Fetch current/latest price for an asset.

        PLUGIN RESPONSIBILITY:
        - Fetch the latest available price from external source
        - Return price with currency and timestamp
        - Handle provider-specific authentication/rate limiting

        CORE WILL:
        - Cache the result if needed
        - Store in database
        - Handle currency conversion if requested

        Args:
            identifier: Asset identifier (ticker, ISIN, URL, etc.)
            identifier_type: Type of identifier (helps provider parse it)
            provider_params: Provider-specific config (e.g., CSS selectors, API keys)

        Returns:
            FACurrentValue with:
            - value: Decimal price
            - currency: ISO currency code (e.g., 'USD', 'EUR')
            - as_of_date: Date of the price
            - source: Provider name for attribution

        Raises:
            AssetSourceError: With appropriate error_code:
            - INVALID_IDENTIFIER_TYPE: Wrong identifier type for this provider
            - NO_DATA: Asset not found or no price available
            - FETCH_ERROR: Network/API error
            - MISSING_PARAMS: Required provider_params missing
        """

    @property
    def supports_history(self) -> bool:
        """
        Whether this provider can fetch historical price data.

        Override to return False for providers that only support current prices
        (e.g., simple web scrapers without historical data access).

        Default: True (most providers support history)
        """
        return True

    @property
    def supports_search(self) -> bool:
        """
        Whether this provider supports asset search functionality.

        Override to return False for providers that cannot search for assets
        (e.g., scheduled investments, CSS scrapers).

        Default: True if test_search_query is not None, False otherwise.
        This heuristic works for most providers. Override explicitly when needed.
        """
        return self.test_search_query is not None

    @abstractmethod
    async def get_history_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None,
        start_date: AssetHistoryStartDate,
        end_date: date_type,
    ) -> FAHistoricalData:
        """
        Fetch historical prices for a date range.

        PLUGIN RESPONSIBILITY:
        - Fetch RAW historical prices from external source
        - Return only actual data points (trading days with prices)
        - DO NOT fill gaps (weekends, holidays) - core handles this
        - DO NOT set backward_filled flag - core handles this

        CORE WILL:
        - Apply backward_fill_prices() to fill gaps with last known value
        - Set backward_filled=True on filled records
        - Store all records (real + filled) in database
        - Handle date range chunking for large requests

        Example:
            Plugin returns: [Mon: 100, Tue: 101, Wed: 102, Fri: 104]
            Core fills to:  [Mon: 100, Tue: 101, Wed: 102, Thu: 102*, Fri: 104]
                            (* = backward_filled=True)

        Args:
            identifier: Asset identifier
            identifier_type: Type of identifier
            provider_params: Provider-specific config
            start_date: Start date (inclusive) or literal "min" for provider-defined full history.
                Implementations MUST handle "min" explicitly instead of assuming the core
                resolved it to a concrete fallback date.
            end_date: End date (inclusive)

        Returns:
            FAHistoricalData with:
            - prices: List[FAPricePoint] - Raw prices from source
              Each FAPricePoint has: date, open, high, low, close, volume
              (open/high/low/volume can be None if not available)
            - currency: ISO currency code
            - source: Provider name

        Raises:
            AssetSourceError: With appropriate error_code:
            - NOT_SUPPORTED: If supports_history is False
            - NO_DATA: No data available for date range
            - FETCH_ERROR: Network/API error
        """

    @property
    @abstractmethod
    def test_search_query(self) -> str | None:
        """
        Search query string for automated testing.

        Return None if this provider does not support search functionality.
        Otherwise return a query that should return at least one result.

        Examples:
            'Apple' - for stock providers
            'MSCI World' - for ETF providers
            None - for CSS scrapers (no search)
        """

    async def search(self, query: str) -> list[dict]:
        """
        Search for assets matching a query string.

        PLUGIN RESPONSIBILITY:
        - Query external source for matching assets
        - Return standardized result format
        - Handle empty results gracefully (return [])

        CORE WILL:
        - Present results to user for selection
        - Use selected result to create/link asset

        Args:
            query: User search string (e.g., 'Apple', 'MSCI World ETF')

        Returns:
            List of dicts, each containing:
            - identifier: str - Provider-specific identifier
            - identifier_type: IdentifierType - Type of identifier (ISIN, TICKER, etc.)
            - display_name: str - Human-readable name
            - currency: str | None - Trading currency if known
            - type: str | None - Asset type if known (e.g., 'stock', 'etf')

            Empty list if no matches found.

        Raises:
            AssetSourceError:
            - NOT_SUPPORTED: If search not implemented (default behavior)
            - FETCH_ERROR: If search fails due to network/API error
        """
        raise AssetSourceError(
            f"Search not supported by {self.provider_name}",
            "NOT_SUPPORTED",
            {"provider": self.provider_code},
        )

    @abstractmethod
    def validate_params(self, params: dict | None) -> None:
        """
        Validate provider_params structure before use.

        PLUGIN RESPONSIBILITY:
        - Check that all required parameters are present
        - Validate parameter types and formats
        - Raise AssetSourceError if validation fails

        CORE WILL:
        - Call this before get_current_value/get_history_value
        - Store validated params in database

        Implementation patterns:

        1. No params required (most providers):
            def validate_params(self, params: dict | None) -> None:
                pass  # Accept anything

        2. Optional params with defaults:
            def validate_params(self, params: dict | None) -> None:
                if params is None:
                    return  # Use defaults
                # Validate specific keys if present

        3. Required params (e.g., CSS scraper):
            def validate_params(self, params: dict | None) -> None:
                if not params:
                    raise AssetSourceError("Params required", "MISSING_PARAMS")
                if 'css_selector' not in params:
                    raise AssetSourceError("css_selector required", "MISSING_PARAMS")

        Args:
            params: Provider parameters to validate (can be None)

        Raises:
            AssetSourceError: With error_code 'MISSING_PARAMS' or 'INVALID_PARAMS'
        """
        # Default: no validation, accepts any params including None

    @property
    def params_schema(self) -> list[dict]:
        """
        Schema of fields required by provider_params for this provider.
        The frontend uses this to generate dynamic forms.
        Default: empty list (no parameters required).

        Returns:
            List of dicts with keys: key, type, required, description, options, default
        """
        return []

    @property
    def accepted_identifier_types(self) -> list[ProviderInputType]:  # pragma: no cover
        """
        Input types accepted by this provider (for frontend identifier type dropdown).
        Uses ProviderInputType (TICKER, ISIN, URL, AUTO_GENERATED), NOT IdentifierType.
        Default: [TICKER, ISIN].
        """
        return [ProviderInputType.TICKER, ProviderInputType.ISIN]

    @staticmethod
    def map_input_type_to_identifier_type(input_type: str) -> IdentifierType:
        """
        Map a ProviderInputType value to the corresponding IdentifierType.

        Used internally when provider plugin methods require IdentifierType
        (e.g., get_current_value, get_history_value) but the stored/incoming
        value is a ProviderInputType string.
        """
        mapping = {
            ProviderInputType.TICKER.value: IdentifierType.TICKER,
            ProviderInputType.ISIN.value: IdentifierType.ISIN,
            ProviderInputType.URL.value: IdentifierType.OTHER,
            ProviderInputType.AUTO_GENERATED.value: IdentifierType.UUID,
        }
        if input_type in mapping:
            return mapping[input_type]
        # Fallback: try direct match (e.g., TICKER → TICKER)
        try:
            return IdentifierType(input_type)
        except ValueError:
            return IdentifierType.OTHER

    @staticmethod
    def map_identifier_type_to_input_type(id_type: str) -> ProviderInputType | None:
        """
        Reverse mapping: IdentifierType → ProviderInputType.

        Used when auto-populating asset identifier columns from provider data.
        Returns None if no matching ProviderInputType exists (e.g., CUSIP, SEDOL, FIGI
        have no provider equivalent — they are asset-record-only identifiers).
        """
        mapping = {
            IdentifierType.TICKER.value: ProviderInputType.TICKER,
            IdentifierType.ISIN.value: ProviderInputType.ISIN,
            IdentifierType.OTHER.value: ProviderInputType.URL,
            IdentifierType.UUID.value: ProviderInputType.AUTO_GENERATED,
        }
        return mapping.get(id_type)

    async def fetch_asset_metadata(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict | None = None,
    ) -> FAAssetPatchItem | None:
        """
        Fetch asset metadata from provider (optional feature).

        PLUGIN RESPONSIBILITY:
        - Fetch metadata from external source if available
        - Return FAAssetPatchItem with available fields
        - Return None if metadata not supported or unavailable
        - DO NOT store in database - core handles this

        CORE WILL:
        - Call this when user requests metadata refresh
        - Merge returned metadata with existing asset data
        - Store updated metadata in database

        Override this method if your provider can fetch:
        - asset_type: Stock, ETF, Bond, etc.
        - short_description: Brief description of the asset
        - classification_params: Sector, geographic distribution, etc.

        Args:
            identifier: Asset identifier for provider
            identifier_type: Type of identifier (TICKER, ISIN, UUID, etc.)
            provider_params: Provider-specific configuration

        Returns:
            FAAssetPatchItem with metadata fields populated:
            - asset_id: Set to 0 (placeholder, core will set real ID)
            - asset_type: AssetType enum if known
            - classification_params: FAClassificationParams with:
              - sector: Primary sector (e.g., 'Technology')
              - geographic_area: FAGeographicArea with distribution dict
              - short_description: Brief description

            Return None if:
            - Metadata fetching not supported by this provider
            - Asset not found
            - Metadata unavailable for this asset

        Raises:
            AssetSourceError: On fetch failure (network error, etc.)
        """
        return None  # Default: metadata not supported

    def get_asset_url(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict | None = None,
    ) -> str | None:
        """
        Generate URL to the provider's page for this specific asset.

        Used by the frontend to show a "Go to Provider Page" link.
        Override in subclasses that have public web pages.

        Args:
            identifier: Asset identifier
            identifier_type: Type of identifier
            provider_params: Provider-specific params

        Returns:
            URL string or None if provider has no web page for assets
        """
        return None

    @property
    def resolvable_url_domains(self) -> list[str]:
        """Bare domains whose asset pages this provider can resolve via ``resolve_url``.

        Default: empty list → the provider does not support URL resolution. A
        provider that can turn one of its public page URLs back into a search-item
        overrides this with the domains it recognises, e.g. ``["borsaitaliana.it"]``.
        Sub-domains are covered automatically (``www.borsaitaliana.it`` matches).
        """
        return []

    @property
    def supports_url_resolution(self) -> bool:
        """Whether this provider implements ``resolve_url`` (derived from the domains)."""
        return bool(self.resolvable_url_domains)

    async def resolve_url(self, url: str) -> dict | list[dict] | None:
        """Resolve a provider page URL into search-item(s) (inverse of ``get_asset_url``).

        Given a URL on one of ``resolvable_url_domains``, open and extract it, then
        return the SAME shape ``search`` produces — either a single item dict or a
        list of them::

            {identifier, identifier_type, display_name, currency, type, provider_params}

        ``resolve_url`` is only an alternative **entry point** into search: when a
        single page maps to several canonical rows (e.g. one per language, like an
        on-site search hit), return them all as a list; the orchestration flattens and
        de-duplicates by ``(identifier, language)``. This lets an externally-found page
        (e.g. via ``web_link_finder``) be turned into selectable assets exactly like an
        on-site search — funds priced by their stored ``provider_params`` afterwards,
        never by external search.

        PLUGIN RESPONSIBILITY:
        - Recognise whether ``url`` is one of your asset pages; return ``None`` if not.
        - Extract identifier/name/currency/type and any ``provider_params`` needed
          to price the asset later.
        - Return one item, or the full canonical set (list) the same instrument would
          yield from ``search``.
        - Handle errors gracefully (return ``None`` rather than raising).

        Like other provider methods this runs inside the provider thread, so sync
        I/O is fine. Default: not supported → returns ``None``.

        Args:
            url: A candidate provider page URL.

        Returns:
            A search-item dict, a list of them, or ``None`` if the URL is not a
            recognised asset page.
        """
        return None

    def shutdown(self) -> None:  # pragma: no cover  # noqa: B027 — intentional no-op default
        """
        Cleanup resources on application shutdown.

        Override to release persistent connections, stop background threads,
        flush caches, etc.  Called once per provider during app lifespan teardown
        via ``AssetProviderRegistry.shutdown_all_providers()``.

        Default: no-op.
        """


# ============================================================================
# ASSET SOURCE MANAGER
# ============================================================================
