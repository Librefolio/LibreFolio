"""CoinGecko price provider (project 76): cryptocurrency prices in a national currency, from a CoinGecko account.

**The account** is the shared settings group ``coingecko`` (``plugin_settings/groups/coingecko.py``): its API key
(required) and its plan (Demo or Pro). Without the key the provider is «to configure» and every call answers
NOT_CONFIGURED at the boundary. Its calls are counted, and limited, on the group: one account's credits.

**The SDK** is CoinGecko's own (``coingecko-sdk``, pinned), behind ``_sdk.py``: no retry and no sleep on a 429, the
plan's API root, the errors translated, the key never in a message.

**An asset** is priced by its CoinGecko id (``bitcoin``, ``pepe``: the assignment's identifier) in the currency of
``vs_currency`` (``provider_params``), which must be the asset's currency: one of ``VS_CURRENCIES``.

**Prices** (lot P2). A current price is ``/simple/price`` with ``precision=full``, the many assets of a refresh in ONE
request (``supports_bulk_current``); the value is read as a decimal from the response's text, never through a float.
The history is ``/coins/{id}/market_chart/range`` with ``interval=daily``: CoinGecko's point at 00:00 UTC of day D is
the close of day D−1, and a point at another time (a «now» point) is dropped. The Demo plan gives the last 365 days only
(10012 beyond): a start before today − 364 is moved there, logged, so the request never meets the refusal, and the
history says that first day (``history_starts``, P2b): the refresh tells the user from which day to import by hand.

Search and metadata are lot P3.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, TypeVar

from backend.app.db import AssetType, IdentifierType
from backend.app.db.models import ProviderInputType
from backend.app.logging_config import get_logger
from backend.app.schemas.assets.assets import FAAssetPatchItem
from backend.app.schemas.prices import FACurrentValue, FACurrentValueRequest, FAHistoricalData, FAPricePoint
from backend.app.schemas.provider import FAProviderAttribution
from backend.app.services.asset_source_providers.coingecko import _sdk
from backend.app.services.asset_source_providers.coingecko._currencies import DEFAULT_VS_CURRENCY, VS_CURRENCIES
from backend.app.services.assets.base import AssetHistoryStartDate, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.platform.provider_registry import register_provider
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType
from backend.app.services.plugin_settings.groups.coingecko import COINGECKO_GROUP_NAME, PLAN_DEMO

T = TypeVar("T")
logger = get_logger(__name__)

#: The days of history the Demo plan answers: today and the 364 before (CoinGecko's 10012 beyond).
DEMO_HISTORY_DAYS = 365
#: The first day CoinGecko has prices for (bitcoin, 28 April 2013): the start of a history from «min» on a paid plan.
COINGECKO_FIRST_DAY = date(2013, 4, 28)
_DAY_MS = 86_400_000
#: The margin past each edge of a history request, in seconds (the midnight and range filters drop what it adds).
_EDGE_SECONDS = 3600


def _utc_today() -> date:
    """Today in UTC, CoinGecko's calendar (a seam for the tests)."""
    return datetime.now(UTC).date()


def _midnight(day: date) -> int:
    """00:00 UTC of ``day``, in Unix seconds."""
    return int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp())


def _decimal_json(text: str) -> Any:
    """A response's JSON with its decimals as ``Decimal``: the digits CoinGecko wrote, never a float's."""
    return json.loads(text, parse_float=Decimal)


#: What a CoinGecko id looks like («bitcoin», «usd-coin», «pepe»): letters, digits, dots, dashes and underscores, never a
#: path or a query. Anything else is no coin of CoinGecko's and asks nothing.
_COIN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _coin_id(identifier: str) -> str:
    """``identifier`` as a CoinGecko id, or NOT_FOUND without a request."""
    coin = (identifier or "").strip()
    if not _COIN_ID.fullmatch(coin) or ".." in coin:
        raise AssetSourceError("Not a CoinGecko coin id", "NOT_FOUND", {"identifier": coin[:64]})
    return coin


#: The longest ticker an asset keeps (``FAAssetPatchItem.identifier_ticker``): a longer symbol is left out.
_TICKER_MAX_LENGTH = 20


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


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

    #: The many assets of a refresh in one ``/simple/price`` request: one credit for all of them.
    supports_bulk_current = True
    bulk_current_max_items = 100

    @property
    def provider_code(self) -> str:
        return "coingecko"

    @property
    def provider_name(self) -> str:
        return "CoinGecko"

    @property
    def get_icon(self) -> str:
        # CoinGecko's own favicon, by URL, as the other providers' icons: it follows CoinGecko's updates (P1b-b)
        return "https://www.coingecko.com/favicon.ico"

    @property
    def provider_help_url(self) -> str:
        # Its page in the user guide (P6): the key, the year of history, the credits, the attribution
        return "/mkdocs/user/assets/providers/coingecko/"

    @property
    def attribution(self) -> FAProviderAttribution:
        # CoinGecko's terms: every price shown with «Powered by CoinGecko», prominent, linked to its site (P4)
        return FAProviderAttribution(text="Powered by CoinGecko", url="https://www.coingecko.com/")

    @property
    def supports_meaningful_volume(self) -> bool:
        """CoinGecko's volume is a 24-hour aggregate over every exchange, not one market's: not shown as volume."""
        return False

    @property
    def accepted_identifier_types(self) -> list:
        # The CoinGecko id («bitcoin») is CoinGecko's own code, not a ticker: COINGECKO_ID, which reaches the plugin as
        # OTHER (the consultant's rule, P3). The asset's ticker is the symbol (BTC), from the metadata.
        return [ProviderInputType.COINGECKO_ID]

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
        # The generic external tests (``test_external/test_asset_providers.py``) reach the real CoinGecko only with the
        # key in the environment; without it the provider answers NOT_CONFIGURED and they skip. Its prices are pinned
        # on the P0 recordings (``test_services/test_coingecko_prices.py``).
        return [{"identifier": "bitcoin", "identifier_type": IdentifierType.OTHER, "provider_params": {"vs_currency": "EUR"}}]

    @property
    def test_search_query(self) -> str | None:
        return "bitcoin"

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

    @property
    def current_min_refresh_seconds(self) -> float | None:
        """The setting ``current_refresh_minutes``, in seconds: the account's credits decide (no I/O: a bound value)."""
        try:
            return float(self.settings.get("current_refresh_minutes")) * 60
        except (TypeError, ValueError):
            return None

    @property
    def supports_history(self) -> bool:
        return True

    def _vs_currency(self, provider_params: Dict | None) -> str:
        """The asset's currency, as ``validate_params`` accepts it, in upper case."""
        self.validate_params(provider_params)
        return str((provider_params or {})["vs_currency"]).strip().upper()

    def _prices(self, ids: list[str], currencies: list[str]) -> dict:
        """``/simple/price`` for ``ids`` in ``currencies``: one request, its body with decimals."""
        raw = self._call(
            lambda client: client.simple.price.with_raw_response.get(
                ids=",".join(ids),
                vs_currencies=",".join(currency.lower() for currency in currencies),
                include_last_updated_at=True,
                precision="full",
            )
        )
        body = _decimal_json(raw.http_response.text)
        return body if isinstance(body, dict) else {}

    def _quote(self, body: dict, identifier: str, currency: str) -> FACurrentValue:
        """One coin's price in ``currency`` out of a ``/simple/price`` body; NOT_FOUND for an unknown id, NO_DATA for
        a coin without that currency."""
        coin = body.get(identifier)
        if not isinstance(coin, dict):
            raise AssetSourceError("CoinGecko does not know this coin", "NOT_FOUND", {"identifier": identifier})
        value = coin.get(currency.lower())
        if value is None:
            raise AssetSourceError("CoinGecko has no price of this coin in this currency", "NO_DATA", {"identifier": identifier, "currency": currency})
        updated = coin.get("last_updated_at")
        as_of = datetime.fromtimestamp(int(updated), UTC).date() if isinstance(updated, int | Decimal) else _utc_today()
        return FACurrentValue(value=value, currency=currency, as_of_date=as_of, source=self.provider_name)

    async def get_current_value(self, identifier: str, identifier_type: IdentifierType, provider_params: Dict | None = None) -> FACurrentValue:
        coin = _coin_id(identifier)
        currency = self._vs_currency(provider_params)
        return self._quote(self._prices([coin], [currency]), coin, currency)

    async def get_current_values_bulk(self, items: list[FACurrentValueRequest]) -> dict[str, FACurrentValue | AssetSourceError]:
        """Every item in ONE ``/simple/price`` request (each id and currency once); each answered under its key, an
        item's own error (bad parameters, an unknown coin) for that item only. A refusal refuses the whole call."""
        answers: dict[str, FACurrentValue | AssetSourceError] = {}
        wanted: list[tuple[FACurrentValueRequest, str, str]] = []
        for item in items:
            try:
                wanted.append((item, _coin_id(item.identifier), self._vs_currency(item.provider_params)))
            except AssetSourceError as error:
                answers[item.key] = error
        if not wanted:
            return answers
        body = self._prices(_unique(coin for _, coin, _ in wanted), _unique(currency for _, _, currency in wanted))
        for item, coin, currency in wanted:
            try:
                answers[item.key] = self._quote(body, coin, currency)
            except AssetSourceError as error:
                answers[item.key] = error
        return answers

    async def get_history_value(self, identifier: str, identifier_type: IdentifierType, provider_params: Dict | None, start_date: AssetHistoryStartDate, end_date: date) -> FAHistoricalData:
        """The daily closes from ``start_date`` to ``end_date``: CoinGecko's point at 00:00 UTC of D is the close of D−1."""
        coin = _coin_id(identifier)
        currency = self._vs_currency(provider_params)
        plan = self.settings.group(COINGECKO_GROUP_NAME).get("plan") or PLAN_DEMO
        start = COINGECKO_FIRST_DAY if start_date == "min" else start_date
        # P2b: on the Demo plan the source has no price before its window's first day, and says so
        first_day: date | None = None
        if plan == PLAN_DEMO:
            floor = _utc_today() - timedelta(days=DEMO_HISTORY_DAYS - 1)
            first_day = floor
            if start < floor:
                logger.info("CoinGecko's Demo plan gives one year of history: the start moves to its first day", identifier=coin, asked=str(start), first_day=str(floor))
                start = floor
        if start > end_date:
            return FAHistoricalData(prices=[], events=[], currency=currency, source=self.provider_name, history_starts=first_day)
        raw = self._call(
            lambda client: client.coins.market_chart.with_raw_response.get_range(
                coin,
                vs_currency=currency.lower(),
                # One hour past each edge's midnight: those two points come whether CoinGecko's ends are inclusive or not
                from_=str(_midnight(start + timedelta(days=1)) - _EDGE_SECONDS),
                to=str(_midnight(end_date + timedelta(days=1)) + _EDGE_SECONDS),
                interval="daily",
                precision="full",
            )
        )
        body = _decimal_json(raw.http_response.text)
        points: dict[date, FAPricePoint] = {}
        for entry in (body.get("prices") if isinstance(body, dict) else None) or []:
            if not isinstance(entry, list) or len(entry) < 2 or entry[1] is None:
                continue
            stamp = int(entry[0])
            if stamp % _DAY_MS:
                continue  # not a midnight: the price «now», no day's close
            day = datetime.fromtimestamp(stamp // 1000, UTC).date() - timedelta(days=1)
            if start <= day <= end_date:
                points[day] = FAPricePoint(date=day, close=entry[1], currency=currency)
        return FAHistoricalData(prices=[points[day] for day in sorted(points)], events=[], currency=currency, source=self.provider_name, history_starts=first_day)

    # =========================================================================
    # Search, metadata, the asset's page (lot P3)
    # =========================================================================

    def _preferred_currency(self) -> str:
        """The user's currency for the search's rows: the setting, when CoinGecko prices in it; else the default."""
        preferred = str(self.settings.get("preferred_currency") or "").strip().upper()
        return preferred if preferred in VS_CURRENCIES else DEFAULT_VS_CURRENCY

    def _json(self, request: Callable[[Any], Any]) -> Any:
        """A raw SDK call's body as plain JSON."""
        return json.loads(self._call(request).http_response.text)

    async def search(self, query: str) -> list[dict]:
        """CoinGecko's ``/search``: its coins only, by market capitalisation (a coin without a rank last, in CoinGecko's
        order), each in the user's preferred currency. The id is CoinGecko's own code: ``OTHER``."""
        text = (query or "").strip()
        if not text:
            return []
        body = self._json(lambda client: client.search.with_raw_response.get(query=text))
        coins = [coin for coin in (body.get("coins") or []) if isinstance(coin, dict) and isinstance(coin.get("id"), str) and coin["id"]]
        coins.sort(key=lambda coin: (not isinstance(coin.get("market_cap_rank"), int), coin.get("market_cap_rank") or 0))
        currency = self._preferred_currency()
        rows = []
        for coin in coins:
            name = str(coin.get("name") or coin["id"]).strip()
            rows.append(
                {
                    "identifier": coin["id"],
                    "identifier_type": IdentifierType.OTHER,
                    # TL40: the coin's name alone, the name its metadata gives (an asset created from this row is not
                    # offered a rename by «Ask the provider»); the symbol is the asset's ticker, from the metadata
                    "display_name": name,
                    "currency": currency,
                    "type": AssetType.CRYPTO.value,
                    "provider_params": {"vs_currency": currency},
                    # S3: the coin's logo, the very image its metadata gives (``image.large``), so the browser asks it once
                    "icon_url": coin.get("large") if isinstance(coin.get("large"), str) and coin.get("large") else None,
                }
            )
        return rows

    async def fetch_asset_metadata(self, identifier: str, identifier_type: IdentifierType, provider_params: dict | None = None) -> FAAssetPatchItem | None:
        """``/coins/{id}`` without its tickers, markets or translations: the name, CRYPTO, the logo, the symbol as the
        ticker (left out when no ticker column holds it), and ``coingecko:<id>`` among the other identifiers (§3.8)."""
        coin = _coin_id(identifier)
        body = self._json(
            lambda client: client.coins.with_raw_response.get_id(
                coin,
                localization=False,
                tickers=False,
                market_data=False,
                community_data=False,
                developer_data=False,
                sparkline=False,
            )
        )
        if not isinstance(body, dict):
            return None
        symbol = str(body.get("symbol") or "").strip().upper()
        image = body.get("image") if isinstance(body.get("image"), dict) else {}
        return FAAssetPatchItem(
            asset_id=0,
            display_name=str(body.get("name") or "").strip() or None,
            asset_type=AssetType.CRYPTO,
            icon_url=image.get("large") or image.get("small") or None,
            identifier_ticker=symbol if 0 < len(symbol) <= _TICKER_MAX_LENGTH else None,
            identifier_other=[f"{self.provider_code}:{coin}"],
        )

    def get_asset_url(self, identifier: str, identifier_type: IdentifierType, provider_params: dict | None = None) -> str | None:
        """The coin's page on CoinGecko, built from the id alone: never the key, no I/O."""
        try:
            return f"https://www.coingecko.com/en/coins/{_coin_id(identifier)}"
        except AssetSourceError:
            return None
