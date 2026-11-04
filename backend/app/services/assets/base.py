"""
Contract of the asset pricing plugins.

- AssetSourceProvider: the abstract base class every plugin in ``services/asset_source_providers/`` extends.
  ``__init_subclass__`` wraps each concrete ``get_history_value`` with the OHLC guard defined here.
- AssetSourceError: the error a plugin raises, with an ``error_code`` the API localizes.
- AssetHistoryStartDate / ASSET_HISTORY_MIN_FALLBACK: the start date of a history request ("min" = from the
  earliest available point).

The runtime the core gives every plugin call (thread isolation, caches, parameter hashing) lives in ``core.py``;
``registry.py`` discovers the plugins.
"""

import functools
import re
from abc import ABC, abstractmethod
from datetime import date as date_type
from typing import ClassVar, Dict, Literal, Optional

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
from backend.app.schemas.assets.assets import FAAssetPatchItem
from backend.app.schemas.provider import (
    DEFAULT_SEARCH_PRIORITY,
    FAProviderKind,
    FAProviderTier,
    FAQuoteBaseSuggestion,
    FAVolumeKind,
)
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.utils.runtime.cooldown import RateLimitedError, retry_after_seconds

# Initialize structured logger
logger = get_logger(__name__)

AssetHistoryStartDate = date_type | Literal["min"]
ASSET_HISTORY_MIN_FALLBACK = date_type(1900, 1, 1)


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


class AssetRateLimitedError(AssetSourceError, RateLimitedError):
    """The provider refused for too many requests, or is paused after such a refusal: ``error_code="RATE_LIMITED"``.

    ``retry_after`` is a wait in seconds: the provider's ``Retry-After`` (or None) when a plugin raises it, the pause the
    call boundary decided when it reaches a caller (``core.call_provider``). ``scope`` narrows the pause to a part of the
    provider, such as the host of a scraped site. A subclass of ``AssetSourceError``: every ``except AssetSourceError``
    keeps catching it. A plugin raises it and never retries in its thread: the boundary pauses the provider.
    """

    def __init__(self, message: str, *, retry_after: float | None = None, scope: str | None = None, details: Optional[dict] = None):
        AssetSourceError.__init__(self, message, "RATE_LIMITED", details)
        self.retry_after = retry_after
        self.scope = scope


def rate_limited_from_response(response: object, provider_name: str, *, scope: str | None = None) -> AssetRateLimitedError | None:
    """An ``AssetRateLimitedError`` when ``response`` (``httpx`` or ``requests``) is an HTTP 429, else None.

    The error carries the response's ``Retry-After`` in seconds, None when absent or unreadable.
    """
    if getattr(response, "status_code", None) != 429:
        return None
    headers = getattr(response, "headers", None)
    retry_after = retry_after_seconds(headers.get("Retry-After")) if headers is not None and hasattr(headers, "get") else None
    return AssetRateLimitedError(f"{provider_name}: too many requests (HTTP 429)", retry_after=retry_after, scope=scope)


#: The words of a library that reports an HTTP 429 only in its message: «Got status 429», «HTTP 429», «HTTP Error 429»
#: (urllib), «status code 429», or the reason phrase «Too Many Requests» (requests, httpx, urllib). 429 as a whole number.
_STATUS_429_IN_TEXT = re.compile(r"\b(?:status(?:\s+code)?|http(?:\s+error)?)\s*:?\s*429\b|too many requests", re.IGNORECASE)


def rate_limited_from_exception(error: BaseException, provider_name: str, *, scope: str | None = None) -> AssetRateLimitedError | None:
    """An ``AssetRateLimitedError`` when ``error`` is a refusal for too many requests, else None.

    Recognised: an ``AssetRateLimitedError`` already (returned as it is); an exception with a ``response`` that is an
    HTTP 429 (``requests.HTTPError``, ``httpx.HTTPStatusError``, with its ``Retry-After``); a message that says
    «status 429», «status code 429», «HTTP 429», «HTTP Error 429» or «Too Many Requests», as libraries without an error
    class of their own do. For a plugin's ``except``.
    """
    if isinstance(error, AssetRateLimitedError):
        return error
    refused = rate_limited_from_response(getattr(error, "response", None), provider_name, scope=scope)
    if refused is not None:
        return refused
    if _STATUS_429_IN_TEXT.search(str(error)):
        return AssetRateLimitedError(f"{provider_name}: too many requests (HTTP 429)", scope=scope)
    return None


def raise_if_rate_limited(error: BaseException, provider_name: str, *, scope: str | None = None) -> None:
    """Raise an ``AssetRateLimitedError`` (from ``error``) when ``error`` is a refusal for too many requests.

    For the first line of a plugin's ``except``: the other errors go on to the plugin's own handling.
    """
    refused = rate_limited_from_exception(error, provider_name, scope=scope)
    if refused is error:
        raise refused
    if refused is not None:
        raise refused from error


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


def _validate_search_declarations(cls: type) -> None:
    """Check a provider class's ``tier`` and ``search_priority`` when it is defined, so a wrong declaration stops the
    import instead of reaching the search: ``tier`` an ``FAProviderTier`` (a valid string is normalised),
    ``search_priority`` a whole number of at least 0."""
    try:
        cls.tier = FAProviderTier(cls.tier)
    except ValueError:
        raise TypeError(f"{cls.__name__}.tier must be one of {[tier.value for tier in FAProviderTier]}, not {cls.tier!r}") from None
    priority = cls.search_priority
    if isinstance(priority, bool) or not isinstance(priority, int) or priority < 0:
        raise TypeError(f"{cls.__name__}.search_priority must be a whole number of at least 0, not {priority!r}")


class AssetSourceProvider(PluginSettingsMixin, ABC):
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
    - Filling gaps on read only (stored history keeps the provider's own points)
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
    4. Core stores the points exactly as returned: nothing is filled on write
    5. Gaps (weekends, holidays) are filled only when prices are read: the read
       path (assets/price_query.py) adds the missing days with
       backward_fill_info, and valuation carries the last observation forward
       (financial_math/price_marks.py)

    Required implementations:
    - provider_code: Unique identifier for this provider
    - provider_name: Human-readable name
    - test_cases: Test data for automated testing
    - get_current_value(): Fetch latest price
    - get_history_value(): Fetch historical prices (raw, no filling)
    - test_search_query: Search query for tests (None if search unsupported)

    Optional overrides:
    - settings_fields: the settings the plugin needs (plugin_settings/fields.py), read with self.settings
    - test_only: True for a provider that exists for the tests, never listed to users and, outside test mode, not
      found by the registry at all (X-R44)
    - tier, search_priority: where the provider stands in the asset search (F21; see below)
    - get_icon(): Provider icon URL
    - supports_history: False if provider cannot fetch historical data
    - search(): Search for assets by query
    - validate_params(): Validate provider-specific parameters
    - fetch_asset_metadata(): Fetch asset metadata (type, sector, etc.)

    Providers auto-register via @register_provider(AssetProviderRegistry) decorator.
    """

    #: Where the provider stands in the asset search (F21). ``premium``: a source the instance vouches for, such as
    #: licensed data; when at least one is available, the search lists its results first. ``community`` (the default):
    #: every other source. An instance overrides it with LIBREFOLIO_ASSET_PROVIDERS_PREMIUM
    #: (``services/assets/provider_policy.py``). A valid string (``"premium"``) is accepted and normalised.
    tier: ClassVar[FAProviderTier] = FAProviderTier.COMMUNITY

    #: The provider's place in the search inside its tier, lower first: a whole number of at least 0. An instance
    #: overrides it with LIBREFOLIO_ASSET_PROVIDERS_ORDER.
    search_priority: ClassVar[int] = DEFAULT_SEARCH_PRIORITY

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
        _validate_search_declarations(cls)
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
        - DO NOT fill gaps (weekends, holidays) - the read path handles this
        - DO NOT set backward_fill_info - the read path computes it

        CORE WILL:
        - Store the returned points as they are (no gap filling on write)
        - Fill gaps only on read (assets/price_query.py): each missing day
          repeats the last known price and carries backward_fill_info
        - Handle date range chunking for large requests

        Example:
            Plugin returns: [Mon: 100, Tue: 101, Wed: 102, Fri: 104]
            Stored:         the same four points
            Read as:        [Mon: 100, Tue: 101, Wed: 102, Thu: 102*, Fri: 104]
                            (* = backward_fill_info with days_back=1)

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

    async def suggest_quote_base(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict | None = None,
    ) -> FAQuoteBaseSuggestion | None:
        """
        Suggest how many units one price of this asset refers to (optional feature, Z-32 d).

        PLUGIN RESPONSIBILITY:
        - Return ``FAQuoteBaseSuggestion`` only when the provider's own data says it (Yahoo Finance: 100 for a line it
          quotes in pence, ``GBp``), else None.
        - The same suggestion can ride on each search result, under the key ``quote_base_suggestion``.

        CORE WILL:
        - Call this in the provider probe's metadata operation only, once ``fetch_asset_metadata`` has answered, and
          return it beside the patch, never inside: the asset form proposes it, and a stored asset changes only when
          the user saves. The metadata refresh never calls it.
        - Treat any error as no suggestion.
        """
        return None  # Default: no suggestion

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

    def cooldown_scope(self, identifier: str, identifier_type: IdentifierType | None = None, provider_params: dict | None = None) -> str | None:
        """The part of this provider a pause after «too many requests» applies to, for this identifier.

        None, the default, pauses the whole provider. A provider that reaches many sites (the CSS scraper) returns the
        site's host, so a refusal from one site pauses that site only. Called before every call: no I/O here.
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
