"""
Contract of the FX rate providers.

- FXRateProvider: the abstract base class every plugin in ``services/fx_providers/`` extends.
- FXProviderStartDate / FX_HISTORY_MIN_FALLBACK: the start date of a history fetch ("min" = from the earliest
  available rate).
- FXServiceError / RateNotFoundError / FXNotConfiguredError: the errors of the FX service.

``registry.py`` discovers the providers; ``sync.py``, ``conversion.py`` and ``storage.py`` are the service.
"""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Literal

from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.utils.runtime.cooldown import RateLimitedError, retry_after_seconds

FXProviderStartDate = date | Literal["min"]
FX_HISTORY_MIN_FALLBACK = date(1900, 1, 1)


# ============================================================================
# ABSTRACT BASE CLASS FOR FX PROVIDERS
# ============================================================================


class FXRateProvider(PluginSettingsMixin, ABC):
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
    4. Put it in backend/app/services/fx_providers/<name>/plugin.py, beside an __init__.py holding only its docstring
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

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g., 'European Central Bank')."""

    @property
    def icon(self) -> str | None:  # pragma: no cover
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
    def test_currencies(self) -> list[str]:  # pragma: no cover
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

    @abstractmethod
    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
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

    def shutdown(self) -> None:  # pragma: no cover  # noqa: B027 — intentional no-op default
        """
        Cleanup resources on application shutdown.

        Override to release persistent connections, stop background threads,
        flush caches, etc.  Called once per provider during app lifespan teardown
        via ``FXProviderRegistry.shutdown_all_providers()``.

        Default: no-op.
        """


# ============================================================================
# EXCEPTIONS
# ============================================================================


class FXServiceError(Exception):
    """Base exception for FX service errors."""


class RateNotFoundError(FXServiceError):
    """Raised when no FX rate is found for a conversion."""


class FXNotConfiguredError(FXServiceError):
    """A provider's required settings have no value: the call is refused before any I/O (``fx/runtime.py``)."""

    def __init__(self, provider_code: str, missing: list[str]):
        super().__init__(f"Provider {provider_code} is not configured: {', '.join(missing)} missing")
        self.provider_code = provider_code
        self.missing = missing


class FXRateLimitedError(FXServiceError, RateLimitedError):
    """The provider refused for too many requests, or is paused after such a refusal.

    ``retry_after`` is a wait in seconds: the provider's ``Retry-After`` (or None) when a plugin raises it, the pause
    the call boundary decided when it reaches a caller (``fx/runtime.call_fx_provider``). An ``FXServiceError``: the
    sync records it as a failed leg and tries the next route. A plugin raises it and never retries in its own code.
    """

    error_code = "RATE_LIMITED"

    def __init__(self, message: str, *, retry_after: float | None = None, scope: str | None = None):
        RateLimitedError.__init__(self, message, retry_after=retry_after, scope=scope)


def fx_rate_limited_from_response(response: object, provider_code: str) -> FXRateLimitedError | None:
    """An ``FXRateLimitedError`` when ``response`` (``httpx``) is an HTTP 429, with its ``Retry-After``; else None."""
    if getattr(response, "status_code", None) != 429:
        return None
    headers = getattr(response, "headers", None)
    retry_after = retry_after_seconds(headers.get("Retry-After")) if headers is not None and hasattr(headers, "get") else None
    return FXRateLimitedError(f"{provider_code}: too many requests (HTTP 429)", retry_after=retry_after)


def raise_if_fx_rate_limited(error: BaseException, provider_code: str) -> None:
    """Raise an ``FXRateLimitedError`` (from ``error``) when ``error`` carries an HTTP 429 response (``httpx``).

    For the first line of a plugin's ``except httpx.HTTPError``: the other errors go on to the plugin's own handling.
    """
    refused = fx_rate_limited_from_response(getattr(error, "response", None), provider_code)
    if refused is not None:
        raise refused from error


def longest_refusal(outcomes: object) -> FXRateLimitedError | None:
    """Among the outcomes of calls made together (``asyncio.gather(..., return_exceptions=True)``), the refusal for too
    many requests with the longest ``Retry-After``; None when none was refused.

    A provider that refuses one of its currencies refuses the whole call: the caller raises it, and the sync tries the
    next route while the provider is paused.
    """
    refusals = [outcome for outcome in outcomes if isinstance(outcome, FXRateLimitedError)]  # type: ignore[union-attr]
    if not refusals:
        return None
    return max(refusals, key=lambda refusal: refusal.retry_after if refusal.retry_after is not None else -1.0)


def raise_longest_refusal(outcomes: object) -> None:
    """Raise ``longest_refusal(outcomes)`` when there is one: a provider refusing one currency refuses the whole call."""
    refused = longest_refusal(outcomes)
    if refused is not None:
        raise refused
