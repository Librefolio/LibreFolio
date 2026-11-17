"""CoinGecko price provider (project 76): cryptocurrency prices in a national currency, from a CoinGecko account.

**The account** is the shared settings group ``coingecko`` (``plugin_settings/groups/coingecko.py``): its API key
(required) and its plan (Demo or Pro). Without the key the provider is «to configure» and every call answers
NOT_CONFIGURED at the boundary. Its calls are counted, and limited, on the group: one account's credits.

**The SDK** is CoinGecko's own (``coingecko-sdk``, pinned), behind ``_sdk.py``: no retry and no sleep on a 429, the
plan's API root, the errors translated, the key never in a message.

**An asset** is priced by its CoinGecko id (``bitcoin``, ``pepe``: the assignment's identifier) in the currency of
``vs_currency`` (``provider_params``), which must be the asset's currency: one of ``VS_CURRENCIES``.

Lot P1 is the skeleton: identity, settings, parameters, the client. The prices are lot P2, search and metadata P3.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any, Dict, TypeVar

from backend.app.db import IdentifierType
from backend.app.db.models import ProviderInputType
from backend.app.schemas.prices import FACurrentValue, FAHistoricalData
from backend.app.services.asset_source_providers.coingecko import _sdk
from backend.app.services.asset_source_providers.coingecko._currencies import DEFAULT_VS_CURRENCY, VS_CURRENCIES
from backend.app.services.assets.base import AssetHistoryStartDate, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.platform.provider_registry import register_provider
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType
from backend.app.services.plugin_settings.groups.coingecko import COINGECKO_GROUP_NAME, PLAN_DEMO

T = TypeVar("T")

#: How often a current price may be asked again, in minutes (the plan, §4.1): the Demo plan's credits decide.
REFRESH_MINUTES: tuple[str, ...] = ("10", "15", "30", "60", "120", "240")
DEFAULT_REFRESH_MINUTES = "30"


@register_provider(AssetProviderRegistry)
class CoinGeckoProvider(AssetSourceProvider):
    """Cryptocurrency prices from CoinGecko, through its official SDK."""

    #: Every call reaches CoinGecko: counted, and limited, on the ``coingecko`` group (U2).
    calls_external_service = True
    settings_groups = (COINGECKO_GROUP_NAME,)
    settings_fields = (
        PluginSettingField(
            key="current_refresh_minutes",
            type=SettingType.SELECT,
            scope=SettingScope.SYSTEM,
            label="Price refresh",
            description="How long a current price stays fresh before CoinGecko is asked again. Longer saves the account's credits.",
            default=DEFAULT_REFRESH_MINUTES,
            # «10 min» reads the same in every language: no key to translate
            options=tuple(SettingOption(minutes, f"{minutes} min") for minutes in REFRESH_MINUTES),
            label_key="pluginSettings.asset.coingecko.label.current_refresh_minutes",
            description_key="pluginSettings.asset.coingecko.description.current_refresh_minutes",
        ),
        PluginSettingField(
            key="preferred_currency",
            type=SettingType.SELECT,
            scope=SettingScope.USER,
            label="Preferred currency",
            description="The currency the search shows each coin's price in.",
            default=DEFAULT_VS_CURRENCY,
            options=tuple(SettingOption(currency, currency) for currency in VS_CURRENCIES),
            label_key="pluginSettings.asset.coingecko.label.preferred_currency",
            description_key="pluginSettings.asset.coingecko.description.preferred_currency",
        ),
    )

    #: The tests' door to the SDK: an ``httpx.Client`` on a fake transport, so no request leaves. Never set in the app.
    _http_client: Any = None

    @property
    def provider_code(self) -> str:
        return "coingecko"

    @property
    def provider_name(self) -> str:
        return "CoinGecko"

    @property
    def supports_meaningful_volume(self) -> bool:
        """CoinGecko's volume is a 24-hour aggregate over every exchange, not one market's: not shown as volume."""
        return False

    @property
    def accepted_identifier_types(self) -> list:
        # The CoinGecko id («bitcoin») travels as a ticker-like identifier: no input type names a provider's own id.
        return [ProviderInputType.TICKER]

    @property
    def params_schema(self) -> list[dict]:
        return [
            {
                "key": "vs_currency",
                "type": "select",
                "required": True,
                "options": list(VS_CURRENCIES),
                "default": DEFAULT_VS_CURRENCY,
                "label": "Price currency",
                "description": "The currency CoinGecko prices the coin in: it must be the asset's currency.",
            }
        ]

    def validate_params(self, params: Dict | None) -> None:
        """``vs_currency`` is required and one of ``VS_CURRENCIES`` (any case)."""
        currency = (params or {}).get("vs_currency")
        if not isinstance(currency, str) or not currency.strip():
            raise AssetSourceError("CoinGecko needs vs_currency, the currency of the price", "MISSING_PARAMS", {"param": "vs_currency"})
        if currency.strip().upper() not in VS_CURRENCIES:
            raise AssetSourceError("CoinGecko does not price in this currency", "INVALID_PARAMS", {"param": "vs_currency"})

    @property
    def test_cases(self) -> list[dict]:
        # The generic provider tests reach the network: CoinGecko needs a key there, which they do not have (lot P2)
        return []

    @property
    def test_search_query(self) -> str | None:
        # Search is lot P3
        return None

    # =========================================================================
    # The client
    # =========================================================================

    def _call(self, request: Callable[[Any], T]) -> T:
        """Run ``request`` on a client built from the group's key and plan; the SDK's errors translated (``_sdk``).

        Called in the provider's thread (``core.call_provider``): the SDK's sync calls are allowed there.
        """
        group = self.settings.group(COINGECKO_GROUP_NAME)
        api_key = group.secret("api_key")
        if not api_key:
            # The boundary refuses an unconfigured provider first: this is a provider reached without it (a test)
            raise AssetSourceError("CoinGecko has no API key", "NOT_CONFIGURED")
        client = _sdk.build_client(api_key, group.get("plan") or PLAN_DEMO, http_client=self._http_client)
        try:
            return request(client)
        except Exception as error:  # noqa: BLE001 — every failure of the SDK becomes the provider's own error, its cause kept
            translated = _sdk.translate(error, secret=api_key)
            if translated is error:
                raise
            raise translated from error
        finally:
            # A client of its own per call: its connection pool closed with it. The tests' injected client is theirs.
            if self._http_client is None:
                client.close()

    # =========================================================================
    # Prices (lot P2)
    # =========================================================================

    async def get_current_value(self, identifier: str, identifier_type: IdentifierType, provider_params: Dict | None = None) -> FACurrentValue:
        raise AssetSourceError("CoinGecko's current price comes with lot P2", "NOT_IMPLEMENTED")

    async def get_history_value(self, identifier: str, identifier_type: IdentifierType, provider_params: Dict | None, start_date: AssetHistoryStartDate, end_date: date) -> FAHistoricalData:
        raise AssetSourceError("CoinGecko's history comes with lot P2", "NOT_IMPLEMENTED")
