"""
Mock FX providers for testing purposes only.

Two providers:
- MockFXProvider  (MOCKFX)      — returns a fixed rate (default 1.2345)
- MockFXFailProvider (MOCKFX_FAIL) — always raises FXServiceError

Both produce distinguishable results:
- MOCKFX rates are always exactly `fixed_rate` (1.2345) for every date/currency
- MOCKFX_FAIL never returns data, only errors

After sync, tests can verify `provider_used` in the response to know which
provider served the data, and check the actual rate values to confirm MOCKFX
was the source (rate == 1.2345).

WARNING: TESTING ONLY. Hidden from public API list.
"""

from datetime import date, timedelta
from decimal import Decimal

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FX_HISTORY_MIN_FALLBACK, FXProviderStartDate, FXRateLimitedError, FXRateProvider, FXServiceError
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingScope, SettingType
from backend.app.services.provider_registry import register_provider

logger = get_logger(__name__)

_SUPPORTED = ["USD", "GBP", "CHF", "JPY"]

# Fixed rate used by MockFXProvider — tests can assert on this exact value
MOCKFX_FIXED_RATE = Decimal("1.234500")


@register_provider(FXProviderRegistry)
class MockFXProvider(FXRateProvider):
    """
    Mock FX provider — returns a fixed rate for all dates/currencies.

    The fixed rate (MOCKFX_FIXED_RATE = 1.2345) makes test assertions trivial:
    after a sync, any rate stored with source="MOCKFX" must equal exactly 1.2345.

    WARNING: FOR TESTING ONLY — DO NOT USE IN PRODUCTION
    """

    test_only = True
    #: The «too many requests» mode, for in-process tests only (never the shared test backend, where a pause would
    #: outlive the test): while ``rate_limited`` is true every call refuses with ``rate_limited_retry_after`` as its
    #: ``Retry-After`` (None: no header). Set them with ``monkeypatch.setattr`` on the class.
    rate_limited: bool = False
    rate_limited_retry_after: float | None = None
    settings_fields = (
        PluginSettingField(key="api_key", type=SettingType.STRING, scope=SettingScope.SYSTEM, secret=True, label="API key (testing)"),
        PluginSettingField(key="decimals", type=SettingType.INTEGER, scope=SettingScope.SYSTEM, label="Decimals (testing)", default=6, minimum=0, maximum=10),
    )

    @property
    def code(self) -> str:
        return "MOCKFX"

    @property
    def provider_code(self) -> str:
        return self.code

    @property
    def name(self) -> str:
        return "Mock FX Provider (TESTING ONLY)"

    @property
    def base_currency(self) -> str:
        return "EUR"

    @property
    def docs_url(self) -> str | None:
        return None

    def _refuse_if_asked(self) -> None:
        if type(self).rate_limited:
            raise FXRateLimitedError("MockFX refused for too many requests (testing)", retry_after=type(self).rate_limited_retry_after)

    async def get_supported_currencies(self) -> list[str]:
        self._refuse_if_asked()
        return list(_SUPPORTED)

    async def fetch_rates(
        self,
        date_range: tuple[FXProviderStartDate, date],
        currencies: list[str],
        base_currency: str | None = None,
    ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """Return the fixed rate MOCKFX_FIXED_RATE for every date/currency; refuse while ``rate_limited`` is set."""
        self._refuse_if_asked()
        start, end = date_range
        if start == "min":
            start = FX_HISTORY_MIN_FALLBACK
        base = base_currency or self.base_currency
        result: dict[str, list[tuple[date, str, str, Decimal]]] = {}

        for cur in currencies:
            observations: list[tuple[date, str, str, Decimal]] = []
            d = start
            while d <= end:
                observations.append((d, base, cur, MOCKFX_FIXED_RATE))
                d += timedelta(days=1)
            result[cur] = observations

        logger.debug(
            "MockFX: generated rates",
            currencies=len(currencies),
            days=(end - start).days + 1,
            fixed_rate=str(MOCKFX_FIXED_RATE),
        )
        return result


@register_provider(FXProviderRegistry)
class MockFXFailProvider(FXRateProvider):
    """
    Mock FX provider that always fails — for testing fallback logic.

    Always raises FXServiceError with a distinctive message that tests can
    match in the `errors[]` array of the sync response.

    WARNING: FOR TESTING ONLY — DO NOT USE IN PRODUCTION
    """

    test_only = True

    # Distinctive error message — tests assert on this string
    FAIL_MESSAGE = "MOCKFX_FAIL: simulated provider failure for testing"

    @property
    def code(self) -> str:
        return "MOCKFX_FAIL"

    @property
    def provider_code(self) -> str:
        return self.code

    @property
    def name(self) -> str:
        return "Mock FX Fail Provider (TESTING ONLY)"

    @property
    def base_currency(self) -> str:
        return "EUR"

    @property
    def docs_url(self) -> str | None:
        return None

    async def get_supported_currencies(self) -> list[str]:
        return list(_SUPPORTED)

    async def fetch_rates(
        self,
        date_range: tuple[FXProviderStartDate, date],
        currencies: list[str],
        base_currency: str | None = None,
    ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """Always raises FXServiceError for testing fallback."""
        raise FXServiceError(self.FAIL_MESSAGE)
