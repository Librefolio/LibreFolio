"""The Yahoo Finance enricher (plan 68, C3): the profile of a share, and a second source for funds, by Yahoo ticker.

It reads ``yfinance`` (the library is not ours: no library work) and translates ``Ticker.info`` and, for a fund, its
``funds_data`` sector weightings into the voices of the profile catalogue. The price provider of the same name is another
plugin: nothing is shared with it (plan §C, rule 1).

What it gives, by Yahoo's ``quoteType`` (not by the asset type: Yahoo files an ETC as EQUITY):

- **a share** (``EQUITY``): sector (when the generic helper knows Yahoo's name), industry, the company's country,
  market capitalisation (only in an ISO currency: a London price in pence would be 100× off) and the company summary;
- **a fund** (``ETF``, ``MUTUALFUND``): TER, the fund's manager, its inception date, the sector breakdown and the
  summary.

Bound by ticker only (plan: «lega col ticker»): the cascade asks the strongest identifier first, and an ISIN would let
Yahoo choose the listing. Never read: the ISIN Yahoo gives for a ticker (wrong for several shares), the fund's size
(incoherent units), the legal form (Yahoo's type is not one), the holdings and the prices.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from backend.app.db.models import AssetType
from backend.app.logging_config import get_logger
from backend.app.services.assets.base import rate_limited_from_exception
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
from backend.app.utils.asset.geo import normalize_country_to_iso3
from backend.app.utils.asset.sector import validate_sector
from backend.app.utils.runtime.pacing import Pacer

try:
    import yfinance as yf
except ImportError:  # pragma: no cover — the library is in the lock; without it every call answers «error»
    yf = None

logger = get_logger(__name__)

PROVIDER_NAME = "Yahoo Finance"

#: One pace for every call of this plugin to Yahoo, whatever read, «Riconosci» or search it comes from (plan 68, C5;
#: the round-30 rule: the plugin paces its own calls). Module level: the registry builds a new instance for every call,
#: so a pacer on ``self`` would never be shared. Per process (``utils/runtime/pacing.py``).
_PACER = Pacer(0.5)
#: The error code of a read the library or the site failed (not a refusal for too many requests).
SOURCE_ERROR = "SOURCE_ERROR"
_TICKER = "TICKER"
_HUNDRED = Decimal(100)

_STOCK_VOICES = frozenset({"sector", "industry", "issuer_country", "market_cap", "description"})
_FUND_VOICES = frozenset({"ter", "fund_provider", "inception_date", "sector", "description"})
_FUND_TYPES = frozenset({AssetType.FUND} | {t for t in AssetType if t == AssetType.ETF or t.value.startswith("ETF_")})
_FUND_QUOTE_TYPES = frozenset({"ETF", "MUTUALFUND"})
#: The search's quote types the enricher reads, and the asset type each is (ENR-3b): indices, currencies, futures,
#: options and crypto are left out, the enricher reads nothing of them. The price provider's map, kept to those types.
_SEARCH_TYPES = {"equity": AssetType.STOCK, "etf": AssetType.ETF, "mutualfund": AssetType.FUND}
#: A shorter text finds nothing worth a call (the price provider's minimum).
_MIN_SEARCH_CHARS = 2
#: The quotes of a search the results are taken from (the price provider's cut).
_MAX_SEARCH_QUOTES = 20
OTHER = "Other"

#: Yahoo's fund sectors (``funds_data.sector_weightings`` keys) the generic helper does not know, on the standard
#: sectors. A copy of the price provider's table, kept until D6 removes that one (plan §C).
_FUND_SECTORS = {
    "realestate": "Real Estate",
    "consumer_cyclical": "Consumer Discretionary",
    "basic_materials": "Basic Materials",
    "consumer_defensive": "Consumer Staples",
    "technology": "Technology",
    "communication_services": "Telecommunication",
    "financial_services": "Financials",
    "utilities": "Utilities",
    "industrials": "Industrials",
    "energy": "Energy",
    "healthcare": "Health Care",
}


def _text(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _is_iso_currency(code: str | None) -> bool:
    """An upper-case three-letter code: Yahoo writes minor units in mixed case (``GBp``, ``ZAc``) or as ``ILA``."""
    return code is not None and len(code) == 3 and code.isalpha() and code.isupper() and code != "ILA"


def _country(name: Any, ticker: str) -> str | None:
    text = _text(name)
    if text is None:
        return None
    try:
        return normalize_country_to_iso3(text)
    except ValueError:
        logger.warning("Yahoo country not translated, voice left out", country=text, ticker=ticker)
        return None


def _epoch_date(value: Any) -> date | None:
    """Yahoo's dates are UTC midnights (every recorded one, the Frankfurt fund's included): read in UTC."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return datetime.fromtimestamp(int(value), UTC).date()
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _fund_sector_key(key: Any) -> str | None:
    name = _text(key)
    if name is None:
        return None
    readable = name.replace("_", " ")
    if validate_sector(readable):
        return readable
    return _FUND_SECTORS.get(name.lower())


def fund_sectors(weightings: Any, ticker: str) -> dict[str, str] | None:
    """The sector breakdown of a fund: weights as fractions; a key no table knows folds into «Other» (no weight lost)."""
    if not isinstance(weightings, Mapping):
        return None
    sectors: dict[str, Decimal] = {}
    for key, raw in weightings.items():
        weight = _decimal(raw)
        if weight is None or weight <= 0:
            continue
        sector = _fund_sector_key(key)
        if sector is None:
            logger.warning("Yahoo fund sector not translated, folded into Other", sector=str(key), ticker=ticker)
            sector = OTHER
        sectors[sector] = sectors.get(sector, Decimal(0)) + weight
    return {sector: format(weight, "f") for sector, weight in sectors.items()} or None


def stock_voices(info: Mapping[str, Any], ticker: str) -> dict[str, Any]:
    """The voices of a share from its ``info``."""
    sector = _text(info.get("sector"))
    cap = _decimal(info.get("marketCap"))
    currency = _text(info.get("currency"))
    market_cap = None
    if cap is not None and cap > 0:
        if _is_iso_currency(currency):
            market_cap = {"amount": format(cap, "f"), "currency": currency}
        else:
            logger.warning("Yahoo market cap left out: not an ISO currency", currency=currency, ticker=ticker)
    voices: dict[str, Any] = {
        "sector": {sector: "1"} if sector is not None and validate_sector(sector) else None,
        "industry": _text(info.get("industry")),
        "issuer_country": _country(info.get("country"), ticker),
        "market_cap": market_cap,
        "description": _text(info.get("longBusinessSummary")),
    }
    return {key: value for key, value in voices.items() if value is not None}


def fund_info_voices(info: Mapping[str, Any]) -> dict[str, Any]:
    """The voices of a fund from its ``info`` (the sectors come from ``funds_data``)."""
    ter = _decimal(info.get("netExpenseRatio"))  # a percent
    voices: dict[str, Any] = {
        "ter": format(ter / _HUNDRED, "f") if ter is not None and ter >= 0 else None,
        "fund_provider": _text(info.get("fundFamily")),
        "inception_date": _epoch_date(info.get("fundInceptionDate")),
        "description": _text(info.get("longBusinessSummary")),
    }
    return {key: value for key, value in voices.items() if value is not None}


def _info(ticker: Any) -> Any:
    """``ticker.info``, the call that reaches Yahoo, after the plugin's pace."""
    _PACER.wait()
    return ticker.info


def _found(info: Any) -> bool:
    """An ``info`` of a listing Yahoo knows: a quote type and a name (an unknown ticker answers an almost empty dict)."""
    return isinstance(info, Mapping) and bool(_text(info.get("quoteType"))) and bool(_text(info.get("longName")) or _text(info.get("shortName")))


@register_provider(EnricherRegistry)
class YahooFinanceEnricher(EnricherPlugin):
    """The profile of a share, and a second source for funds, from Yahoo Finance."""

    code = "yfinance"
    name = "Yahoo Finance"
    icon = "https://s.yimg.com/cv/apiv2/default/icons/favicon_y19_32x32_custom.svg"
    terms = EnricherTerms.PRICE_SOURCE
    accepted_identifier_types = (_TICKER,)
    voices = {AssetType.STOCK: _STOCK_VOICES, **dict.fromkeys(_FUND_TYPES, _FUND_VOICES)}
    #: The main source for shares; after justETF and Borsa Italiana for funds.
    default_priority = {asset_type: 10 if asset_type == AssetType.STOCK else 20 if asset_type in _FUND_TYPES else None for asset_type in AssetType}

    def page_url(self, binding: EnricherBinding) -> str | None:
        return f"https://finance.yahoo.com/quote/{binding.identifier}"

    @property
    def test_cases(self) -> list[dict]:
        return [
            {"binding": {"identifier_type": _TICKER, "identifier": "AAPL"}, "asset_type": AssetType.STOCK.value},
            {"binding": {"identifier_type": _TICKER, "identifier": "IWDA.L"}, "asset_type": AssetType.ETF.value},
        ]

    @staticmethod
    def _ticker(symbol: str) -> Any:
        if yf is None:
            raise RuntimeError("yfinance is not installed")
        return yf.Ticker(symbol)

    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        if binding.identifier_type != _TICKER or not _text(binding.identifier):
            return EnricherRecognition(found=False)
        try:
            info = _info(self._ticker(binding.identifier))
        except ValueError:  # «Invalid ISIN number» and the like: Yahoo does not know it
            return EnricherRecognition(found=False)
        if not _found(info):
            return EnricherRecognition(found=False)
        # Never an ISIN: the one Yahoo gives for a ticker is wrong for several shares
        return EnricherRecognition(found=True, name=_text(info.get("longName")) or _text(info.get("shortName")), page_url=self.page_url(binding))

    def search(self, query: str) -> list[EnricherSearchResult]:
        """The listings Yahoo finds for ``query`` (a name, an ISIN, a ticker), each bound by its symbol with the market's
        suffix (``SWDA.MI``): the binding ``recognize`` and ``read`` take (ENR-3b). Copied from the price provider's
        search (``yf.Search``), not imported (a plugin never imports another). No currency per result: the binding does
        not use it, and it would be one more call to Yahoo for each. A refusal for too many requests raises
        ``EnricherRateLimited``; another failure goes to the route as it is."""
        text = query.strip()
        if len(text) < _MIN_SEARCH_CHARS:
            return []
        if yf is None:
            raise RuntimeError("yfinance is not installed")
        _PACER.wait()
        try:
            found = yf.Search(text)
        except Exception as error:
            limited = rate_limited_from_exception(error, PROVIDER_NAME)
            if limited is None:
                raise
            raise EnricherRateLimited(f"{PROVIDER_NAME} refused the search for too many requests", retry_after=limited.retry_after) from error
        results: list[EnricherSearchResult] = []
        for quote in (getattr(found, "quotes", None) or [])[:_MAX_SEARCH_QUOTES]:
            if not isinstance(quote, Mapping) or not quote.get("isYahooFinance", True):
                continue
            symbol = _text(quote.get("symbol"))
            asset_type = _SEARCH_TYPES.get((_text(quote.get("quoteType")) or "").lower())
            if symbol is None or asset_type is None:
                continue
            binding = EnricherBinding(identifier_type=_TICKER, identifier=symbol)
            name = _text(quote.get("longname")) or _text(quote.get("shortname")) or symbol
            market = _text(quote.get("exchDisp")) or _text(quote.get("exchange"))
            results.append(EnricherSearchResult(name=name, binding=binding, asset_type=asset_type, page_url=self.page_url(binding), market=market))
        return results

    def _fund_sectors(self, ticker: Any, symbol: str) -> dict[str, str] | None:
        """The sector breakdown from ``funds_data``; a failure other than a refusal costs only this voice."""
        try:
            _PACER.wait()
            weightings = ticker.funds_data.sector_weightings
        except Exception as error:  # noqa: BLE001 — isolation boundary: the fund's info voices still go out
            if rate_limited_from_exception(error, PROVIDER_NAME) is not None:
                raise
            logger.warning("Yahoo fund sectors unavailable", ticker=symbol, exc_info=error)
            return None
        return fund_sectors(weightings, symbol)

    def _voices(self, ticker: Any, symbol: str, info: Mapping[str, Any], wanted: frozenset[str] | None) -> dict[str, Any]:
        quote_type = (_text(info.get("quoteType")) or "").upper()
        if quote_type == "EQUITY":
            return stock_voices(info, symbol)
        if quote_type in _FUND_QUOTE_TYPES:
            voices = fund_info_voices(info)
            if wanted is None or "sector" in wanted:
                sectors = self._fund_sectors(ticker, symbol)
                if sectors is not None:
                    voices["sector"] = sectors
            return voices
        return {}

    def read(self, bindings: list[EnricherBinding], keys: Iterable[str] | None = None) -> Iterator[EnricherReadItem]:
        wanted = None if keys is None else frozenset(keys)
        refused = False
        for index, binding in enumerate(bindings):
            symbol = _text(binding.identifier) if binding.identifier_type == _TICKER else None
            if symbol is None:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
                continue
            if refused:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED)
                continue
            try:
                ticker = self._ticker(symbol)
                info = _info(ticker)
                if not _found(info):
                    yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
                    continue
                values = self._voices(ticker, symbol, info, wanted)
            except ValueError as error:
                if rate_limited_from_exception(error, PROVIDER_NAME) is None:
                    yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
                    continue
                refused = True
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED)
                continue
            except Exception as error:  # noqa: BLE001 — isolation boundary: one ticker's failure is that ticker's outcome
                limited = rate_limited_from_exception(error, PROVIDER_NAME)
                if limited is not None:
                    refused = True
                    logger.warning("Yahoo refused for too many requests", ticker=symbol)
                    yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED, retry_after=limited.retry_after)
                    continue
                logger.warning("Yahoo read failed", ticker=symbol, exc_info=error)
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=SOURCE_ERROR, error_message=type(error).__name__)
                continue
            yield EnricherReadItem(index=index, status=EnricherReadStatus.OK, values=values)
