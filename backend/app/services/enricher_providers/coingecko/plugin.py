"""The CoinGecko enricher (82 CG-B): the profile of a cryptocurrency, by its CoinGecko id («bitcoin»).

It reads ``/coins/{id}``, **one call per coin**, through CoinGecko's official SDK (``services/coingecko/sdk.py``, the door
the price provider uses too: no retry on a 429, the key never in a message). The account is the shared settings group
``coingecko``: its API key is required, and its credits are the price provider's too.

What it gives for a coin, only as the source says it:

- **description**: CoinGecko's English text, as plain text (markup removed, when it has some);
- **website**: the first address of the coin's home pages, only an ``http(s)`` one (the profile shows it as a link);
- **inception_date**: the day of the first block («genesis»). Many tokens have none: the voice is then absent;
- **market_cap**: the capitalisation in the binding's ``vs_currency`` (CoinGecko gives every currency in the same answer),
  as an exact decimal, on the day of ``market_data.last_updated``. CoinGecko answers 0 for a coin whose supply it does not
  know: that is not a capitalisation, and the voice is absent;
- **crypto_categories**: CoinGecko's own categories, all of them, its words and its order, as one text («Meme; Frog-Themed»).
  It mixes kinds with ecosystems, holdings and indices: choosing some, or translating them, would be our reading of them.

Never read: the **legal form** (CoinGecko lists every kind of token, a stablecoin or a tokenised share among them: calling
it «crypto» would be a deduction), the supply and the prices (the price provider's).

A coin CoinGecko does not know answers 404: «not found», never an error. A price assignment of CoinGecko already has the
binding (``COINGECKO_ID``), handed to it by «Riconosci»'s seed (ENR-2); elsewhere it comes from ``search``. Terms: self-
hosted instances only (``EnricherTerms.SELF_HOSTED``), with CoinGecko's own attribution in its settings card and manual
page (TL42).
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterable, Iterator, Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from backend.app.db.models import AssetType
from backend.app.logging_config import get_logger
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError
from backend.app.services.coingecko import sdk
from backend.app.services.coingecko.currencies import DEFAULT_VS_CURRENCY, VS_CURRENCIES
from backend.app.services.enrichers.base import (
    RATE_LIMITED,
    EnricherBinding,
    EnricherPlugin,
    EnricherRateLimited,
    EnricherReadItem,
    EnricherReadStatus,
    EnricherRecognition,
    EnricherSearchResult,
    EnricherTerms,
)
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.platform.provider_registry import register_provider
from backend.app.services.plugin_settings.groups.coingecko import COINGECKO_GROUP_NAME, PLAN_DEMO
from backend.app.utils.runtime.pacing import Pacer

logger = get_logger(__name__)

#: One pace for every call of this plugin to CoinGecko, whatever read, «Riconosci» or search it comes from. Module level:
#: the registry builds a new instance for every call. Per process (``utils/runtime/pacing.py``). The Demo plan allows 100
#: calls a minute; the price provider spends the same account's.
_PACER = Pacer(1.0)
#: The error code of a read the SDK or the source failed (not a refusal for too many requests).
SOURCE_ERROR = "SOURCE_ERROR"
_IDENTIFIER_TYPE = "COINGECKO_ID"
#: The results a search gives at most: CoinGecko's most capitalised first.
_MAX_RESULTS = 20
#: Between two categories of the one text they make.
_CATEGORY_SEPARATOR = "; "
_TAG = re.compile(r"<[^>]+>")
_WEB_ADDRESS = re.compile(r"https?://\S+", re.IGNORECASE)


def _text(value: Any) -> str | None:
    """A text of the source, or None when it is not one or is blank."""
    return value.strip() or None if isinstance(value, str) else None


def plain_description(body: Mapping[str, Any]) -> str | None:
    """CoinGecko's English description as plain text: tags removed, entities read, line ends as ``\\n``."""
    described = body.get("description")
    raw = _text(described.get("en")) if isinstance(described, Mapping) else None
    if raw is None:
        return None
    return _text(html.unescape(_TAG.sub("", raw)).replace("\r\n", "\n"))


def website(body: Mapping[str, Any]) -> str | None:
    """The first ``http(s)`` address among the coin's home pages."""
    links = body.get("links")
    pages = links.get("homepage") if isinstance(links, Mapping) else None
    for page in pages if isinstance(pages, list) else ():
        address = _text(page)
        if address and _WEB_ADDRESS.fullmatch(address):
            return address
    return None


def inception_date(body: Mapping[str, Any]) -> str | None:
    """The day of the first block, ISO; None for a coin that has none or a day that is not one."""
    day = _text(body.get("genesis_date"))
    if day is None:
        return None
    try:
        return date.fromisoformat(day).isoformat()
    except ValueError:
        return None


def _market_data(body: Mapping[str, Any]) -> Mapping[str, Any]:
    data = body.get("market_data")
    return data if isinstance(data, Mapping) else {}


def _vs_currency(binding: EnricherBinding) -> str | None:
    """The currency of the binding's market capitalisation: ``vs_currency``, any case, EUR when absent; None for a value that is
    none of CoinGecko's (the voice is then absent, never read in another currency)."""
    chosen = _text(binding.params.get("vs_currency"))
    currency = chosen.upper() if chosen else DEFAULT_VS_CURRENCY
    return currency if currency in VS_CURRENCIES else None


def market_cap(body: Mapping[str, Any], currency: str) -> dict[str, Any] | None:
    """The capitalisation in ``currency``: an exact positive number, or None."""
    caps = _market_data(body).get("market_cap")
    amount = caps.get(currency.lower()) if isinstance(caps, Mapping) else None
    if isinstance(amount, bool) or not isinstance(amount, int | Decimal) or amount <= 0:
        return None
    return {"amount": amount, "currency": currency}


def market_day(body: Mapping[str, Any]) -> date | None:
    """The UTC day of CoinGecko's market data, when it says one."""
    stamp = _text(_market_data(body).get("last_updated"))
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(UTC).date() if stamp else None
    except ValueError:
        return None


def categories(body: Mapping[str, Any]) -> str | None:
    """The coin's categories as one text: the source's words, in its order."""
    listed = body.get("categories")
    words = [word for word in map(_text, listed if isinstance(listed, list) else ()) if word]
    return _CATEGORY_SEPARATOR.join(words) or None


def coin_voices(body: Mapping[str, Any], currency: str | None) -> dict[str, Any]:
    """The voices ``body`` (``/coins/{id}``) gives, the capitalisation in ``currency``: the absent ones are left out."""
    values = {
        "description": plain_description(body),
        "website": website(body),
        "inception_date": inception_date(body),
        "market_cap": market_cap(body, currency) if currency is not None else None,
        "crypto_categories": categories(body),
    }
    return {key: value for key, value in values.items() if value is not None}


@register_provider(EnricherRegistry)
class CoinGeckoEnricher(EnricherPlugin):
    """The profile of a cryptocurrency, from CoinGecko."""

    code = "coingecko"
    name = "CoinGecko"
    icon = "https://www.coingecko.com/favicon.ico"
    help_url = "/mkdocs/user/assets/providers/coingecko/"
    terms = EnricherTerms.SELF_HOSTED
    accepted_identifier_types = (_IDENTIFIER_TYPE,)
    settings_groups = (COINGECKO_GROUP_NAME,)
    voices = {AssetType.CRYPTO: frozenset({"description", "website", "inception_date", "market_cap", "crypto_categories"})}
    #: The only source for cryptocurrencies.
    default_priority = {asset_type: 10 if asset_type == AssetType.CRYPTO else None for asset_type in AssetType}

    #: The tests' door to the SDK: an ``httpx.Client`` on a fake transport, so no request leaves. Never set in the app.
    _http_client: Any = None

    def page_url(self, binding: EnricherBinding) -> str | None:
        coin = self._coin(binding)
        return f"https://www.coingecko.com/en/coins/{coin}" if coin else None

    @property
    def params_schema(self) -> list[dict]:
        # The binding's parameter, as the price provider's: a price assignment's seed brings it along (ENR-2)
        return [
            {
                "key": "vs_currency",
                "type": "select",
                "required": False,
                "options": list(VS_CURRENCIES),
                "default": DEFAULT_VS_CURRENCY,
                "label": "Market capitalisation currency",
                "x-i18n-key": "enrichers.coingecko.params.vs_currency",
            }
        ]

    @property
    def test_cases(self) -> list[dict]:
        return [{"binding": {"identifier_type": _IDENTIFIER_TYPE, "identifier": "bitcoin"}, "asset_type": AssetType.CRYPTO.value}]

    @staticmethod
    def _coin(binding: EnricherBinding) -> str | None:
        return sdk.coin_id(binding.identifier) if binding.identifier_type == _IDENTIFIER_TYPE else None

    def _call(self, request: Any) -> Any:
        """One call to CoinGecko, after the plugin's pace, on the shared account's key and plan."""
        group = self.settings.group(COINGECKO_GROUP_NAME)
        api_key = group.secret("api_key")
        if not api_key:
            # The boundary refuses an unconfigured enricher first: this is one reached without it (a test)
            raise AssetSourceError("CoinGecko has no API key", "NOT_CONFIGURED")
        _PACER.wait()
        raw = sdk.call(api_key, group.get("plan") or PLAN_DEMO, request, http_client=self._http_client)
        return sdk.decimal_json(raw.http_response.text)

    def _coin_body(self, coin: str, *, market_data: bool) -> Mapping[str, Any] | None:
        """``/coins/{id}`` without what the profile never reads; None when CoinGecko does not know the coin."""
        try:
            body = self._call(
                lambda client: client.coins.with_raw_response.get_id(
                    coin,
                    localization=False,
                    tickers=False,
                    market_data=market_data,
                    community_data=False,
                    developer_data=False,
                    sparkline=False,
                )
            )
        except AssetSourceError as error:
            if (error.details or {}).get("http_status") == 404:
                return None
            raise
        return body if isinstance(body, Mapping) and _text(body.get("id")) else None

    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        coin = self._coin(binding)
        if coin is None:
            return EnricherRecognition(found=False)
        body = self._coin_body(coin, market_data=False)
        if body is None:
            return EnricherRecognition(found=False)
        return EnricherRecognition(found=True, name=_text(body.get("name")), page_url=self.page_url(binding))

    def read(self, bindings: list[EnricherBinding], keys: Iterable[str] | None = None) -> Iterator[EnricherReadItem]:
        refused: float | None | bool = False  # after a refusal, the rest is refused too, with no call
        for index, binding in enumerate(bindings):
            coin = self._coin(binding)
            if coin is None:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
                continue
            if refused is not False:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED, retry_after=refused)
                continue
            try:
                body = self._coin_body(coin, market_data=True)
            except AssetRateLimitedError as error:
                refused = error.retry_after
                logger.warning("CoinGecko refused for too many requests", coin=coin, retry_after=refused)
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED, retry_after=refused)
                continue
            except Exception as error:  # noqa: BLE001 — isolation boundary: one coin's failure is that coin's outcome
                logger.warning("CoinGecko read failed", coin=coin, exc_info=error)
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=SOURCE_ERROR, error_message=type(error).__name__)
                continue
            if body is None:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
                continue
            values = coin_voices(body, _vs_currency(binding))
            day = market_day(body)
            dates = {"market_cap": day} if day is not None and "market_cap" in values else {}
            yield EnricherReadItem(index=index, status=EnricherReadStatus.OK, values=values, source_dates=dates)

    def search(self, query: str) -> list[EnricherSearchResult]:
        """The coins CoinGecko finds for ``query`` (a name or a ticker), the most capitalised first, each bound by its id:
        many coins share a symbol, so the row says the name and the symbol, and the binding the id."""
        text = query.strip()
        if not text:
            return []
        try:
            body = self._call(lambda client: client.search.with_raw_response.get(query=text))
        except AssetRateLimitedError as error:
            raise EnricherRateLimited("CoinGecko refused the search for too many requests", retry_after=error.retry_after) from error
        found = body.get("coins") if isinstance(body, Mapping) else None
        coins: list[tuple[str, Mapping[str, Any]]] = []
        for coin in found if isinstance(found, list) else ():
            coin_id = sdk.coin_id(_text(coin.get("id")) or "") if isinstance(coin, Mapping) else None
            if coin_id is not None:
                coins.append((coin_id, coin))
        coins.sort(key=lambda item: (not isinstance(item[1].get("market_cap_rank"), int), item[1].get("market_cap_rank") or 0))
        results = []
        for coin_id, coin in coins[:_MAX_RESULTS]:
            symbol = _text(coin.get("symbol"))
            name = _text(coin.get("name")) or coin_id
            binding = EnricherBinding(identifier_type=_IDENTIFIER_TYPE, identifier=coin_id)
            results.append(EnricherSearchResult(name=f"{name} ({symbol.upper()})" if symbol else name, binding=binding, asset_type=AssetType.CRYPTO, page_url=self.page_url(binding)))
        return results
