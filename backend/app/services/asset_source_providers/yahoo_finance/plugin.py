"""
Yahoo Finance asset pricing provider.

Uses yfinance library to fetch stock/ETF/crypto prices from Yahoo Finance.
Supports both current values and historical OHLC (Open, High, Low, Close) data.
"""

# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

import importlib
import math
import re
import time as _time_mod
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.app.db import IdentifierType
from backend.app.db.models import ProviderInputType
from backend.app.logging_config import get_logger
from backend.app.utils.runtime.cache import get_ttl_cache

try:
    import pandas as pd
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    pd = None
    YFINANCE_AVAILABLE = False

try:
    from yfinance.exceptions import YFRateLimitError
except ImportError:  # pragma: no cover — yfinance missing, or a version without it: the message words still count
    YFRateLimitError = None

from datetime import UTC
from datetime import datetime as _dt

from backend.app.schemas.assets.assets import FAAssetPatchItem
from backend.app.schemas.assets.events import FAAssetEventPoint
from backend.app.schemas.assets.metadata import (
    FAClassificationParams,
    FASectorArea,
)
from backend.app.schemas.common import Currency as CurrencyAmount
from backend.app.schemas.prices import (
    FACurrentValue,
    FACurrentValueRequest,
    FAHistoricalData,
    FAPricePoint,
)
from backend.app.schemas.provider import FAQuoteBaseSuggestion, FAVolumeKind
from backend.app.services.assets.base import AssetHistoryStartDate, AssetRateLimitedError, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.platform.provider_registry import register_provider
from backend.app.utils.asset.sector import validate_sector
from backend.app.utils.currency_units import minor_unit_factor

logger = get_logger(__name__)

# ── Retry helpers for transient yfinance errors ─────────────────────────

# «Too many requests» is never retried in the thread: the core pauses the provider (decision 34, release 1.3).
# A whole-word 429, so a ticker such as 4290.T in a message is no refusal.
_RATE_LIMIT_PATTERN = re.compile(r"\b429\b|too many requests|rate limit")

# Keywords that indicate transient network/API errors worth retrying
_TRANSIENT_KEYWORDS = frozenset(
    [
        "curl",
        "connection",
        "timeout",
        "timed out",
        "reset",
        "abruptly",
        "nonetype",
        "temporary",
        "503",
        "ssl",
        "eof",
        "broken pipe",
        "gaierror",
    ]
)

_YF_MAX_RETRIES = 3
_YF_BASE_DELAY = 1.5  # seconds


def _is_rate_limited(exc: Exception) -> bool:
    """True for a «too many requests» refusal: yfinance's ``YFRateLimitError``, or its words in the message."""
    if YFRateLimitError is not None and isinstance(exc, YFRateLimitError):
        return True
    return _RATE_LIMIT_PATTERN.search(str(exc).lower()) is not None


def _is_transient(exc: Exception) -> bool:  # pragma: no cover
    """Return True if the exception looks like a transient network error."""
    err = str(exc).lower()
    return any(kw in err for kw in _TRANSIENT_KEYWORDS)


def _yf_with_retry(fn, *, label: str = "yfinance"):
    """
    Execute a yfinance operation with retry on transient errors.

    Up to three attempts, with exponential backoff between them (1.5 s, then 3 s).
    Non-transient errors are raised immediately. A «too many requests» refusal is raised at once as
    ``AssetRateLimitedError``, never retried: the call boundary pauses the provider (``core.call_provider``).

    Args:
        fn: Zero-arg callable that performs the yfinance operation
        label: Human-readable label for logging

    Returns:
        Result of fn()

    Raises:
        AssetRateLimitedError on a refusal for too many requests; otherwise the last exception if all retries are
        exhausted or non-transient
    """
    last_exc: Exception | None = None
    for attempt in range(1, _YF_MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            if _is_rate_limited(e):
                raise AssetRateLimitedError(f"Yahoo Finance refused for too many requests ({label})") from e
            last_exc = e
            if not _is_transient(e) or attempt == _YF_MAX_RETRIES:
                raise
            delay = _YF_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(f"{label} transient error (attempt {attempt}/{_YF_MAX_RETRIES}): {e}, retrying in {delay:.1f}s")
            _time_mod.sleep(delay)
    raise last_exc  # pragma: no cover – safety net


# ── Fund data (lot #50) ──────────────────────────────────────────────────

#: The ``quoteType`` values whose ``Ticker.funds_data`` is read besides ``info``.
_FUND_QUOTE_TYPES = frozenset({"etf", "mutualfund"})

#: The longest ``short_description`` the metadata keeps.
_DESCRIPTION_LIMIT = 500

#: Yahoo's eleven fund sectors (``funds_data.sector_weightings`` keys, written with underscores) on the standard
#: sectors. ``FinancialSector.from_string`` does not know these spellings: through it they would all land in «Other».
_YAHOO_FUND_SECTORS = {
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


@dataclass(frozen=True)
class _FundExtras:
    """What ``funds_data`` adds to a fund's metadata; each piece is None when Yahoo has none or it could not be read."""

    sector_area: FASectorArea | None = None
    description: str | None = None
    ter: str | None = None  # already formatted, «0.03»: a percentage
    issuer: str | None = None


def _read_fund_piece(read, *, identifier: str, piece: str):
    """One piece of a fund's data, or None when it is missing or cannot be read.

    A «too many requests» refusal is the exception: it leaves as ``AssetRateLimitedError`` (the core pauses the
    provider), the rule of every other Yahoo call. Any other failure (a fund Yahoo has no profile for, a field that is
    absent, a malformed answer) costs only this piece: it is isolation by design, so the asset's metadata still comes
    back, and the failure is logged where it is caught.
    """
    try:
        return _yf_with_retry(read, label=f"fund_{piece}({identifier})")
    except AssetRateLimitedError:
        raise
    except Exception as exc:  # isolation boundary: fund data is best effort, never a reason to lose the metadata
        logger.warning("Fund data unavailable from Yahoo Finance", identifier=identifier, piece=piece, exc_info=exc)
        return None


def _fund_sector_area(weightings, identifier: str) -> FASectorArea | None:
    """Yahoo's sector weightings as a ``FASectorArea``: names on the standard sectors, weights renormalised to 1.

    A key Yahoo adds that is not in the table goes to «Other», as an unknown sector of any provider does. A weight that
    is not a positive finite number is dropped.
    """
    if not weightings:
        return None
    distribution: dict[str, Decimal] = {}
    for key, raw in dict(weightings).items():
        try:
            weight = float(raw)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(weight) or weight <= 0:
            continue
        sector = _YAHOO_FUND_SECTORS.get(str(key).strip().lower())
        if sector is None:
            logger.warning("Unknown sector from provider, mapped to Other", provider_code="yfinance", identifier=identifier, original_sector=str(key), mapped_to="Other")
            sector = "Other"
        distribution[sector] = distribution.get(sector, Decimal("0")) + Decimal(str(weight))
    total = sum(distribution.values(), Decimal("0"))
    if total <= 0:
        return None
    return FASectorArea(distribution={sector: share / total for sector, share in distribution.items()})


def _fund_ter(operations) -> str | None:
    """The annual report expense ratio as a percentage string («0.03»), or None when Yahoo has none.

    Yahoo gives a fraction (0.0003 = 0.03 %): it is shown as a percentage, rounded to two decimals. A missing value
    (``None``, ``NaN``), or one that is not positive, is left out.
    """
    if operations is None or len(operations) == 0:
        return None
    try:
        ratio = float(operations.iloc[0, 0])
    except (TypeError, ValueError, IndexError):
        return None
    if not math.isfinite(ratio) or ratio <= 0:
        return None
    percentage = (Decimal(str(ratio)) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(percentage.normalize(), "f") if percentage > 0 else None


def _read_fund_extras(ticker, identifier: str) -> _FundExtras:
    """Read a fund's sectors, description, expense ratio and issuer from ``Ticker.funds_data`` (lot #50).

    Every piece is read apart, so the one Yahoo lacks (VWCE.DE has no expense ratio and an empty description) does not
    cost the others. Runs in the core's thread, like every provider call: the sync yfinance reads are safe here.
    """
    funds_data = _read_fund_piece(lambda: ticker.funds_data, identifier=identifier, piece="funds_data")
    if funds_data is None:
        return _FundExtras()
    weightings = _read_fund_piece(lambda: funds_data.sector_weightings, identifier=identifier, piece="sectors")
    overview = _read_fund_piece(lambda: funds_data.fund_overview, identifier=identifier, piece="overview")
    operations = _read_fund_piece(lambda: funds_data.fund_operations, identifier=identifier, piece="operations")
    description = _read_fund_piece(lambda: funds_data.description, identifier=identifier, piece="description")

    issuer = overview.get("family") if isinstance(overview, dict) else None
    return _FundExtras(
        sector_area=_fund_sector_area(weightings, identifier),
        description=description.strip() if isinstance(description, str) and description.strip() else None,
        ter=_fund_ter(operations),
        issuer=issuer.strip() if isinstance(issuer, str) and issuer.strip() else None,
    )


def _fund_description(head: str, extras: _FundExtras) -> str:
    """The description with the expense ratio and the issuer after it («head | TER: 0.03% | Issuer: X»).

    The 500-character cap cuts the head, never the tail: the figures are the point of the addition.
    """
    tail = ""
    if extras.ter:
        tail += f" | TER: {extras.ter}%"
    if extras.issuer:
        tail += f" | Issuer: {extras.issuer}"
    if not tail:
        return head[:_DESCRIPTION_LIMIT]
    room = _DESCRIPTION_LIMIT - len(tail)
    if len(head) > room:
        head = head[: max(room - 3, 0)] + "..."
    return head + tail


@dataclass(frozen=True)
class _YahooHistoryAcquisition:
    history: object
    currency: str
    dividends: object | None
    splits: object | None


#: The unknown Area/Location names ``_exchange_zone`` already logged, once per name and process
_UNKNOWN_ZONES_LOGGED: set[str] = set()


def _exchange_zone(name: str | None) -> ZoneInfo | None:
    """Yahoo's ``exchangeTimezoneName`` as a ``ZoneInfo``, or None when it is empty or names no known zone.

    An Area/Location name (``Europe/Rome``) the server's timezone database does not know is logged once per name and
    process: on a host without one (Windows without the ``tzdata`` package, a minimal container) the current value is
    then dated in UTC, the day before for a session that crosses UTC midnight (backlog Z-36). A fixed offset or another
    name without an area is not logged.
    """
    if not name or not name.strip():
        return None
    key = name.strip()
    try:
        return ZoneInfo(key)
    except ZoneInfoNotFoundError:
        if "/" in key and key not in _UNKNOWN_ZONES_LOGGED:
            _UNKNOWN_ZONES_LOGGED.add(key)
            logger.warning("Exchange timezone unknown to this server's timezone database: the current value is dated in UTC", timezone=key[:64])
        return None
    except ValueError:
        return None


# ── Current values in bulk (project 76, C5) ──────────────────────────────


def _bulk_quote_available() -> bool:
    """Whether yfinance's request helper for the v7 quote list can be reached (project 76, C5).

    yfinance does not expose the list read: ``.info`` calls it inside, through ``YfData().get_raw_json``. If a release
    moves or renames that internal, this is False, the provider declares no bulk support, and the core keeps the
    per-asset path: the bulk read switches itself off instead of failing.
    """
    if not YFINANCE_AVAILABLE:
        return False
    try:
        data = importlib.import_module("yfinance.data")
        const = importlib.import_module("yfinance.const")
    except ImportError:
        return False
    return callable(getattr(getattr(data, "YfData", None), "get_raw_json", None)) and isinstance(getattr(const, "_QUERY1_URL_", None), str)


def _fetch_v7_quotes(symbols: list[str]) -> list[dict]:
    """The v7 quotes of ``symbols``, in ONE request (``/v7/finance/quote?symbols=A,B,…``): the list Yahoo returns,
    empty when it returns none. Through ``_yf_with_retry``: a refusal for too many requests leaves at once as
    ``AssetRateLimitedError``, a transient error is retried. The internal helper is the one ``.info`` uses."""
    data = importlib.import_module("yfinance.data")
    base_url = importlib.import_module("yfinance.const")._QUERY1_URL_
    params = {"symbols": ",".join(symbols), "formatted": "false"}
    answer = _yf_with_retry(lambda: data.YfData().get_raw_json(f"{base_url}/v7/finance/quote?", params=params), label=f"bulk_quote({len(symbols)} symbols)")
    result = ((answer or {}).get("quoteResponse") or {}).get("result") or []
    return [quote for quote in result if isinstance(quote, dict)]


#: The symbols a v7 quote-list request asked and Yahoo did not return, already logged: once per symbol and process
_UNRETURNED_SYMBOLS_LOGGED: set[str] = set()


def _report_unreturned_symbols(symbols: set[str]) -> None:
    """Log, once per symbol, a symbol the v7 quote list did not return: its asset is served its last stored price. A
    delisted ticker, or one Yahoo answers under another symbol (an alias), which the bulk read cannot match while
    ``.info`` takes the first quote whatever its symbol."""
    for symbol in sorted(symbols - _UNRETURNED_SYMBOLS_LOGGED):
        _UNRETURNED_SYMBOLS_LOGGED.add(symbol)
        logger.warning("Yahoo Finance returned no v7 quote for a symbol: its last stored price is served", symbol=symbol[:32])


def _bulk_symbol(item: FACurrentValueRequest) -> str | AssetSourceError:
    """The Yahoo symbol of one bulk item, or the error that is that item's answer: ``INVALID_IDENTIFIER_TYPE`` for an
    identifier that is no TICKER or ISIN; an ISIN resolved as ``yf.Ticker(isin)`` resolves it for ``.info`` (one
    lookup), ``NOT_FOUND`` when it resolves to nothing. A refusal for too many requests leaves at once, for the whole
    call."""
    if item.identifier_type not in (IdentifierType.TICKER, IdentifierType.ISIN):
        return AssetSourceError(f"Yahoo Finance only supports TICKER and ISIN, got {item.identifier_type}", "INVALID_IDENTIFIER_TYPE", {"identifier": item.identifier})
    symbol: object = item.identifier
    if item.identifier_type == IdentifierType.ISIN:
        try:
            symbol = _yf_with_retry(lambda: yf.Ticker(item.identifier).ticker, label=f"isin_symbol({item.identifier})")
        except AssetRateLimitedError:
            raise
        except Exception as error:  # noqa: BLE001 — an ISIN Yahoo cannot resolve is that asset's answer, not the call's
            return AssetSourceError(f"No Yahoo Finance symbol for ISIN {item.identifier}: {error}", "NOT_FOUND", {"identifier": item.identifier})
    if not symbol:
        return AssetSourceError(f"No Yahoo Finance symbol for {item.identifier}", "NOT_FOUND", {"identifier": item.identifier})
    return str(symbol)


def _quote_from_info(info: dict, identifier: str, source: str) -> FACurrentValue:
    """A current value from Yahoo's quote fields: THE one mapping of ``get_current_value`` (``.info``) and of the bulk
    read (a v7 quote), so the two paths always agree.

    The price is ``regularMarketPrice``, else ``currentPrice``, ``previousClose`` or ``regularMarketPreviousClose`` (the
    v7 quote has only the last); the currency ``currency``, else ``financialCurrency``, else USD; the date
    ``regularMarketTime`` read in the exchange's timezone (Z-33; UTC when unknown), today without a time. No price:
    ``AssetSourceError`` ``NO_DATA``.
    """
    price = info.get("regularMarketPrice")
    if price is None:
        price = info.get("currentPrice") or info.get("previousClose") or info.get("regularMarketPreviousClose")
    if price is None:
        raise AssetSourceError(f"No price available for ticker: {identifier}", "NO_DATA", {"identifier": identifier})
    currency = info.get("currency") or info.get("financialCurrency") or "USD"
    zone = _exchange_zone(info.get("exchangeTimezoneName"))
    market_time = info.get("regularMarketTime")
    as_of_date = _dt.fromtimestamp(market_time, tz=zone or UTC).date() if market_time else date.today()
    return FACurrentValue(value=Decimal(str(price)), currency=currency, as_of_date=as_of_date, source=source)


def _normalize_yahoo_date(index_value) -> date:
    """The calendar date of a Yahoo index value, in its own timezone.

    yfinance stamps a daily bar, a dividend or a split at midnight in the exchange's timezone (``scrapers/history.py``:
    ``tz_localize(tz_exchange)``), so the wall date is the session's date. Converting to UTC first gave the day before
    for every exchange east of UTC (Z-33).
    """
    return index_value.date()


def _acquire_history_data(
    ticker,
    identifier: str,
    start_date: AssetHistoryStartDate,
    end_date: date,
) -> _YahooHistoryAcquisition:
    """Fetch Yahoo history plus best-effort metadata/event series.

    The closes are asked unadjusted (``auto_adjust=False``, Z-35): yfinance's default rewrites every close for the
    dividends paid since, as of the day it is read, so a row saved today and one saved last month carried different
    adjustments, and the dividends (kept as events) counted twice in a return. Yahoo's ``Close`` stays adjusted for splits
    in either mode; the splits themselves come as events.
    """
    if start_date == "min":
        history = _yf_with_retry(
            lambda: ticker.history(period="max", auto_adjust=False),
            label=f"history-max({identifier})",
        )
    else:
        remote_end = (end_date + timedelta(days=1)).isoformat()
        history = _yf_with_retry(
            lambda: ticker.history(
                start=start_date.isoformat(),
                end=remote_end,
                auto_adjust=False,
            ),
            label=f"history({identifier})",
        )

    if history is None or not hasattr(history, "empty"):
        raise AssetSourceError(
            f"yfinance returned invalid data for {identifier} (got {type(history).__name__})",
            "FETCH_ERROR",
            {"identifier": identifier},
        )

    currency = "USD"
    try:
        info = ticker.info
        if info:
            currency = info.get("currency", "USD") or "USD"
    except Exception:
        logger.exception(
            "Failed to fetch yfinance currency metadata; falling back to USD",
            identifier=identifier,
        )

    try:
        dividends = ticker.dividends
    except Exception as exc:
        logger.debug(f"Could not fetch dividends for {identifier}: {exc}")
        dividends = None

    try:
        splits = ticker.splits
    except Exception as exc:
        logger.debug(f"Could not fetch splits for {identifier}: {exc}")
        splits = None

    return _YahooHistoryAcquisition(
        history=history,
        currency=currency,
        dividends=dividends,
        splits=splits,
    )


def _quote_base_suggestion(currency: str | None) -> FAQuoteBaseSuggestion | None:
    """Z-32 (d): a line Yahoo quotes in a minor unit (``GBp``, pence) has one price per 100 units, the factor of
    ``MINOR_UNIT_FACTORS``; None for any other currency, or none."""
    factor = minor_unit_factor(currency)
    return FAQuoteBaseSuggestion(quantity=factor, quote_currency=currency.strip()) if factor and currency else None


def _map_history_prices(
    history,
    identifier: str,
    currency: str,
    start_date: AssetHistoryStartDate,
    end_date: date,
) -> list[FAPricePoint]:
    """Map Yahoo OHLCV rows to canonical price points."""
    if history.empty:
        raise AssetSourceError(
            f"No historical data for ticker: {identifier}",
            "NO_DATA",
            {
                "identifier": identifier,
                "start": str(start_date),
                "end": str(end_date),
            },
        )

    required_columns = {"Open", "High", "Low", "Close", "Volume"}
    if not required_columns.issubset(set(history.columns)):
        raise AssetSourceError(
            f"Unexpected DataFrame columns for {identifier}: {list(history.columns)}",
            "FETCH_ERROR",
            {
                "identifier": identifier,
                "columns": list(history.columns),
            },
        )

    prices: list[FAPricePoint] = []
    for index_value, row in history.iterrows():
        point_date = _normalize_yahoo_date(index_value)
        if start_date != "min" and point_date < start_date:
            continue
        if point_date > end_date:
            continue
        if not pd.notna(row["Close"]):
            logger.debug(f"Skipping {point_date} for {identifier}: Close is NaN")
            continue

        prices.append(
            FAPricePoint(
                date=point_date,
                open=(Decimal(str(row["Open"])) if pd.notna(row["Open"]) else None),
                high=(Decimal(str(row["High"])) if pd.notna(row["High"]) else None),
                low=(Decimal(str(row["Low"])) if pd.notna(row["Low"]) else None),
                close=Decimal(str(row["Close"])),
                volume=(int(row["Volume"]) if pd.notna(row["Volume"]) else None),
                currency=currency,
            )
        )

    if not prices:
        raise AssetSourceError(
            f"No usable price points for ticker: {identifier} (all Close values are NaN)",
            "NO_DATA",
            {
                "identifier": identifier,
                "start": str(start_date),
                "end": str(end_date),
            },
        )
    return prices


def _parse_dividend_events(
    dividends,
    identifier: str,
    currency: str,
    start_date: AssetHistoryStartDate,
    end_date: date,
) -> list[FAAssetEventPoint]:
    """Map positive, in-range Yahoo dividends to canonical events.

    A line quoted in a minor unit (``GBp``, pence) has its dividends in that unit too: the event is an amount of money,
    so it is divided by the unit's factor (1.9542 pence is 0.019542 GBP, Z-32). The prices of such a line are kept as
    Yahoo gives them: the asset's quote base divides them.
    """
    if dividends is None or dividends.empty:
        return []

    factor = Decimal(minor_unit_factor(currency) or 1)
    events: list[FAAssetEventPoint] = []
    for index_value, amount in dividends.items():
        if not pd.notna(amount) or amount <= 0:
            continue
        event_date = _normalize_yahoo_date(index_value)
        if start_date != "min" and event_date < start_date:
            continue
        if event_date > end_date:
            continue
        events.append(
            FAAssetEventPoint(
                date=event_date,
                type="DIVIDEND",
                value=CurrencyAmount(
                    code=currency,
                    amount=Decimal(str(amount)) / factor,
                ),
                notes=f"Yahoo Finance dividend for {identifier}",
            )
        )
    return events


def _parse_split_events(
    splits,
    currency: str,
    start_date: AssetHistoryStartDate,
    end_date: date,
) -> list[FAAssetEventPoint]:
    """Map non-trivial, in-range Yahoo split ratios to canonical events."""
    if splits is None or splits.empty:
        return []

    events: list[FAAssetEventPoint] = []
    for index_value, ratio in splits.items():
        if not pd.notna(ratio) or ratio == 0 or ratio == 1:
            continue
        event_date = _normalize_yahoo_date(index_value)
        if start_date != "min" and event_date < start_date:
            continue
        if event_date > end_date:
            continue
        events.append(
            FAAssetEventPoint(
                date=event_date,
                type="SPLIT",
                value=CurrencyAmount(
                    code=currency,
                    amount=Decimal(str(ratio)),
                ),
                notes=f"Stock split {ratio}:1",
            )
        )
    return events


@register_provider(AssetProviderRegistry)
class YahooFinanceProvider(AssetSourceProvider):
    """Yahoo Finance data provider using yfinance library."""

    _MIN_SEARCH_CHARS = 2
    #: Current values in bulk (project 76, C5): one v7 quote-list request for many symbols, while yfinance's internal
    #: helper is there (``_bulk_quote_available``); otherwise the core keeps one ``.info`` per asset
    supports_bulk_current = _bulk_quote_available()
    #: Symbols per request: a URL of a few hundred characters
    bulk_current_max_items = 50

    def __init__(self):
        super().__init__()
        # TTLCache for currency lookups (24h TTL — currency doesn't change)
        # This is a sub-operation cache (currency discovery), NOT a pricing cache.
        # The core handles caching for get_current_value/get_history_value/search.
        self._currency_cache = get_ttl_cache("yfinance_currency", maxsize=2000, ttl=86400)

    def _fetch_currency(self, symbol: str) -> str | None:
        """The currency Yahoo gives for ``symbol`` (``fast_info``), e.g. ``USD`` or ``GBp``; None when Yahoo has none or
        the read failed.

        Only an answer is cached, 24 h: a currency, or Yahoo answering without one. A refusal for too many requests is
        raised at once as ``AssetRateLimitedError``, with no retry and nothing cached, so that the call boundary pauses
        the provider («never swallow a refusal»): the whole search leaves as rate limited. Any other error gives None,
        not cached, so the next call asks again (Z-39).
        """
        cached, ok = self._currency_cache.get(symbol)
        if ok:
            return cached

        try:
            currency = yf.Ticker(symbol).fast_info.get("currency")
        except Exception as e:
            if _is_rate_limited(e):
                raise AssetRateLimitedError(f"Yahoo Finance refused for too many requests (currency({symbol}))") from e
            logger.debug(f"Could not fetch currency for {symbol}: {e}")
            return None
        self._currency_cache.set(symbol, currency)
        return currency

    @property
    def provider_code(self) -> str:
        return "yfinance"

    @property
    def provider_name(self) -> str:
        return "Yahoo Finance"

    @property
    def supports_meaningful_volume(self) -> bool:
        """Yahoo Finance reports real exchange-traded share volume (the
        `Volume` column from the underlying OHLCV history)."""
        return True

    @property
    def volume_kind(self) -> FAVolumeKind:
        return FAVolumeKind.TRADED_SHARES

    @property
    def accepted_identifier_types(self) -> list:
        return [ProviderInputType.TICKER, ProviderInputType.ISIN]

    @property
    def get_icon(self) -> str:
        """Return provider icon URL (hardcoded)"""
        return "https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png"  # Yahoo Finance logo

    @property
    def provider_help_url(self) -> str:
        return "/mkdocs/user/assets/providers/yahoo-finance/"

    def get_asset_url(self, identifier, identifier_type=None, provider_params=None) -> str | None:
        """Generate URL to Yahoo Finance page for this asset."""
        return f"https://finance.yahoo.com/quote/{identifier}"

    @property
    def test_cases(self) -> list[dict]:
        """Test cases with identifier and provider_params: a US stock, an ETF in Milan and a crypto in EUR, so the
        external bulk check (``test_current_values_bulk``) reads three exchanges in one request."""
        return [
            {
                "identifier": "AAPL",
                "identifier_type": IdentifierType.TICKER,
                "provider_params": None,
                "expected_symbol": "AAPL",
            },
            {"identifier": "SWDA.MI", "identifier_type": IdentifierType.TICKER, "provider_params": None, "expected_symbol": "SWDA.MI"},
            {"identifier": "BTC-EUR", "identifier_type": IdentifierType.TICKER, "provider_params": None, "expected_symbol": "BTC-EUR"},
        ]

    async def get_current_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
    ) -> FACurrentValue:
        """
        Fetch current price from Yahoo Finance.

        The core runs this method in a dedicated thread with its own event loop,
        so sync yfinance calls are safe here. The core also caches the result
        (TTL 2min, or the provider's interval), so we don't need our own cache.

        Args:
            identifier: Yahoo Finance ticker symbol (e.g., "AAPL", "BTC-USD")
            identifier_type: Type of identifier (must be TICKER or ISIN)
            provider_params: Optional parameters (unused for Yahoo Finance)

        Returns:
            FACurrentValue with value, currency, as_of_date, source

        Raises:
            AssetSourceError: If yfinance not available, identifier_type invalid, or data fetch fails
        """
        # Validate identifier_type
        if identifier_type not in [IdentifierType.TICKER, IdentifierType.ISIN]:
            raise AssetSourceError(
                f"Yahoo Finance only supports TICKER and ISIN, got {identifier_type}",
                "INVALID_IDENTIFIER_TYPE",
                {"identifier": identifier, "identifier_type": identifier_type},
            )

        if not YFINANCE_AVAILABLE:
            raise AssetSourceError(
                "yfinance library not available - install with: pipenv install yfinance",
                "NOT_AVAILABLE",
                {"identifier": identifier},
            )

        try:
            # The core executes this entire method in a dedicated thread,
            # so sync yfinance calls are safe — no asyncio.to_thread needed.
            # Wrapped in _yf_with_retry to handle transient network errors
            # (e.g., curl 56, connection reset, 429 rate limits).
            info = _yf_with_retry(
                lambda: yf.Ticker(identifier).info,
                label=f"current_value({identifier})",
            )

            # The one mapping of the quote fields, shared with the bulk read (_quote_from_info): price, currency and the
            # date in the exchange's timezone (Z-33: a session that crosses UTC midnight belongs to its local day)
            result = _quote_from_info(info, identifier, self.provider_name)
            logger.debug(f"current_value for {identifier}: {result.value} {result.currency}")
            return result

        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(
                f"Failed to fetch current value for {identifier}: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)},
            ) from e

    async def get_current_values_bulk(self, items: list[FACurrentValueRequest]) -> dict[str, FACurrentValue | AssetSourceError]:
        """The current values of many assets in ONE v7 quote-list request (project 76, C5), mapped as ``get_current_value``
        maps ``.info`` (``_quote_from_info``), so both paths answer the same.

        An item that is no TICKER or ISIN answers ``INVALID_IDENTIFIER_TYPE``. An ISIN is resolved to its symbol as
        ``yf.Ticker(isin)`` resolves it for ``.info`` (one lookup each); one that resolves to nothing answers
        ``NOT_FOUND``. A symbol Yahoo does not return gets no answer: the core serves its last stored price. A refusal for
        too many requests raises for the whole call, never retried; any other failure of the request is ``FETCH_ERROR``.
        """
        answer: dict[str, FACurrentValue | AssetSourceError] = {}
        by_symbol: dict[str, list[FACurrentValueRequest]] = {}
        for item in items:
            symbol = _bulk_symbol(item)
            if isinstance(symbol, AssetSourceError):
                answer[item.key] = symbol
            else:
                by_symbol.setdefault(symbol.upper(), []).append(item)
        if not by_symbol:
            return answer
        try:
            quotes = _fetch_v7_quotes(list(by_symbol))
        except AssetSourceError:
            raise
        except Exception as error:
            raise AssetSourceError(f"Failed to fetch current values of {len(by_symbol)} symbols: {error}", "FETCH_ERROR", {"symbols": len(by_symbol)}) from error
        returned: set[str] = set()
        for quote in quotes:
            symbol = str(quote.get("symbol") or "").upper()
            returned.add(symbol)
            for item in by_symbol.get(symbol, []):
                try:
                    answer[item.key] = _quote_from_info(quote, item.identifier, self.provider_name)
                except AssetSourceError as error:
                    answer[item.key] = error
        _report_unreturned_symbols(set(by_symbol) - returned)
        return answer

    async def get_history_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None,
        start_date: AssetHistoryStartDate,
        end_date: date,
    ) -> FAHistoricalData:
        """
        Fetch historical OHLC data from Yahoo Finance.

        Args:
            identifier: Yahoo Finance ticker symbol
            identifier_type: Type of identifier (must be TICKER or ISIN)
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            provider_params: Optional parameters (unused)

        Returns:
            FAHistoricalData with prices list, currency, source

        Raises:
            AssetSourceError: If yfinance not available, identifier_type invalid, or data fetch fails
        """
        # Validate identifier_type
        if identifier_type not in [IdentifierType.TICKER, IdentifierType.ISIN]:
            raise AssetSourceError(
                f"Yahoo Finance only supports TICKER and ISIN, got {identifier_type}",
                "INVALID_IDENTIFIER_TYPE",
                {"identifier": identifier, "identifier_type": identifier_type},
            )

        if not YFINANCE_AVAILABLE:
            raise AssetSourceError(
                "yfinance library not available - install with: pipenv install yfinance",
                "NOT_AVAILABLE",
                {"identifier": identifier},
            )

        try:
            # The core executes this method in a dedicated thread,
            # so sync yfinance calls are safe — no asyncio.to_thread needed.
            acquisition = _acquire_history_data(
                yf.Ticker(identifier),
                identifier,
                start_date,
                end_date,
            )
            prices = _map_history_prices(
                acquisition.history,
                identifier,
                acquisition.currency,
                start_date,
                end_date,
            )

            events: list[FAAssetEventPoint] = []
            try:
                dividend_events = _parse_dividend_events(
                    acquisition.dividends,
                    identifier,
                    acquisition.currency,
                    start_date,
                    end_date,
                )
                events.extend(dividend_events)
                if dividend_events:
                    logger.debug(f"Parsed {len(dividend_events)} DIVIDEND events for {identifier}")
            except Exception as e:
                logger.debug(f"Could not parse dividends for {identifier}: {e}")

            try:
                split_events = _parse_split_events(
                    acquisition.splits,
                    acquisition.currency,
                    start_date,
                    end_date,
                )
                events.extend(split_events)
                if split_events:
                    logger.debug(f"Parsed {len(split_events)} SPLIT events for {identifier}")
            except Exception as e:
                logger.debug(f"Could not parse splits for {identifier}: {e}")

            return FAHistoricalData(
                prices=prices,
                events=events,
                currency=acquisition.currency,
                source=self.provider_name,
            )

        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(
                f"Failed to fetch history for {identifier}: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)},
            ) from e

    @property
    def test_search_query(self) -> str | None:
        """Search query to use in tests."""
        return "Apple"

    async def search(self, query: str) -> list[dict]:
        """
        Search Yahoo Finance for matching tickers.

        Uses yfinance.Search for real search functionality.
        The core caches results (Layer 2 query cache, 15min TTL)
        and runs this in a dedicated thread.

        Args:
            query: Search query (e.g., "Apple", "Microsoft", "AAPL")

        Returns:
            List of matching tickers with metadata.
            Each result: {identifier, display_name, currency, type}, and quote_base_suggestion for a line quoted in a
            minor unit (GBp: 100 units per price, Z-32 d).

        Raises:
            AssetSourceError: If yfinance not available or search fails
        """
        if not YFINANCE_AVAILABLE:
            raise AssetSourceError(
                "yfinance library not available - install with: pipenv install yfinance",
                "NOT_AVAILABLE",
                {"query": query},
            )

        # Minimum search length
        if len(query) < self._MIN_SEARCH_CHARS:
            return []

        try:
            # The core executes this method in a dedicated thread,
            # so sync yfinance calls are safe — no asyncio.to_thread needed.
            search_result = _yf_with_retry(
                lambda: yf.Search(query),
                label=f"search({query})",
            )
            raw_quotes = getattr(search_result, "quotes", []) or []

            results = []

            # Same mapping as fetch_asset_metadata, for normalizing search results
            search_type_map = {
                "equity": "STOCK",
                "etf": "ETF",
                "mutualfund": "FUND",
                "cryptocurrency": "CRYPTO",
                "currency": "OTHER",
                "future": "OTHER",
                "option": "OTHER",
                "index": "INDEX",
            }

            for quote in raw_quotes[:20]:
                if not quote.get("isYahooFinance", True):
                    continue
                symbol = quote.get("symbol", "")
                currency = self._fetch_currency(symbol) if symbol else None

                # Normalize quoteType using the same map as fetch_asset_metadata
                raw_type = (quote.get("quoteType", "Unknown") or "").lower()
                normalized_type = search_type_map.get(raw_type, "OTHER")

                item = {
                    "identifier": symbol,
                    "identifier_type": IdentifierType.TICKER,  # YFinance uses ticker symbols
                    "display_name": quote.get("longname", quote.get("shortname", symbol)),
                    "currency": currency,
                    "type": normalized_type,
                }
                suggestion = _quote_base_suggestion(currency)
                if suggestion is not None:
                    item["quote_base_suggestion"] = suggestion.model_dump()
                results.append(item)

            logger.debug(f"Search for '{query}': found {len(results)} results")
            return results

        except AssetRateLimitedError:
            raise  # the core pauses the provider: not an empty result
        except Exception as e:
            logger.warning(f"Search failed for '{query}': {e}")
            return []

    async def suggest_quote_base(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
    ) -> FAQuoteBaseSuggestion | None:
        """Z-32 (d): 100 units per price for a line Yahoo quotes in pence (``GBp``), read from the currency of
        ``fast_info`` (``_fetch_currency``, cached 24 h, the one the search reads); None otherwise. The core runs it in
        the provider's thread, like ``search``."""
        if not YFINANCE_AVAILABLE or not identifier:
            return None
        return _quote_base_suggestion(self._fetch_currency(identifier))

    def validate_params(self, params: Dict | None) -> None:
        """
        Validate provider parameters.

        For Yahoo Finance, identifier is passed directly to methods,
        no special params needed.
        """
        # Yahoo Finance doesn't require specific params
        # Identifier is passed as method argument

    async def fetch_asset_metadata(  # noqa: C901 — flat field mapping with fallbacks
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
    ) -> FAAssetPatchItem | None:
        """
        Fetch asset metadata from Yahoo Finance.

        Extracts investment type, description, and sector from yfinance ticker info.
        Geographic area is not available from Yahoo Finance.

        Args:
            identifier: Yahoo Finance ticker symbol
            identifier_type: Type of identifier (must be TICKER or ISIN)
            provider_params: Optional parameters (unused)

        Returns:
            FAAssetPatchItem with metadata fields (asset_id will be None, filled by caller)
            or None if fetch fails.
            Contains: asset_type, classification_params (sector, short_description)

        Note:
            Returns RAW data - normalization happens in core service layer.
        """
        # Validate identifier_type
        if identifier_type not in [IdentifierType.TICKER, IdentifierType.ISIN]:
            raise AssetSourceError(
                f"Yahoo Finance only supports TICKER and ISIN, got {identifier_type}",
                "INVALID_IDENTIFIER_TYPE",
                {"identifier": identifier, "identifier_type": identifier_type},
            )

        if not YFINANCE_AVAILABLE:
            logger.warning(f"yfinance not available, cannot fetch metadata for {identifier}")
            return None

        try:
            # The core executes this method in a dedicated thread,
            # so sync yfinance calls are safe — no asyncio.to_thread needed.
            t = yf.Ticker(identifier)
            info = _yf_with_retry(
                lambda: t.info,
                label=f"metadata({identifier})",
            )
            # Also attempt ISIN lookup (may not be available for all markets)
            identifier_isin = None
            try:
                isin_val = t.isin
                if isin_val and isin_val != "-" and len(isin_val) == 12:
                    identifier_isin = isin_val
            except Exception:
                logger.exception("Failed to fetch yfinance ISIN metadata", identifier=identifier)

            if not info:
                logger.warning(f"No info data returned from yfinance for {identifier}")
                return None

            # Map quoteType to asset_type
            quote_type = info.get("quoteType", "").lower()
            asset_type_map = {
                "equity": "STOCK",
                "etf": "ETF",
                "mutualfund": "FUND",
                "cryptocurrency": "CRYPTO",
                "currency": "OTHER",
                "future": "OTHER",
                "option": "OTHER",
                "index": "INDEX",
            }
            asset_type = asset_type_map.get(quote_type, "OTHER")

            # A fund (ETF, mutual fund) also has its own data: sectors, description, expense ratio, issuer (lot #50)
            extras = _read_fund_extras(t, identifier) if quote_type in _FUND_QUOTE_TYPES else None

            # Get description (truncate to 500 chars)
            long_business_summary = info.get("longBusinessSummary", "")
            short_name = info.get("shortName", "")
            long_name = info.get("longName", "")

            # Prefer longBusinessSummary, then the fund's own description, fallback to names
            if long_business_summary:
                short_description = long_business_summary
            elif extras is not None and extras.description:
                short_description = extras.description
            elif long_name:
                short_description = long_name
            elif short_name:
                short_description = short_name
            else:
                short_description = f"{identifier} from Yahoo Finance"
            short_description = _fund_description(short_description, extras) if extras is not None else short_description[:_DESCRIPTION_LIMIT]

            # Get sector
            sector = info.get("sector")

            # Build FAClassificationParams
            classification_data = {"short_description": short_description}
            if extras is not None and extras.sector_area is not None:
                classification_data["sector_area"] = extras.sector_area
            elif sector:
                # Log warning if sector is not in standard classification
                if not validate_sector(sector):
                    logger.warning(
                        "Unknown sector from provider, mapped to Other",
                        provider_code="yfinance",
                        identifier=identifier,
                        original_sector=sector,
                        mapped_to="Other",
                    )
                # Convert single sector string to FASectorArea distribution
                classification_data["sector_area"] = FASectorArea(distribution={sector: Decimal("1.0")})

            classification = FAClassificationParams(**classification_data)

            # Extract currency from info
            currency = info.get("currency") or info.get("financialCurrency")

            # Extract identifiers
            symbol = info.get("symbol")
            identifier_ticker = symbol if symbol else None

            # identifier_isin already fetched in _sync_fetch_metadata above

            # Build FAAssetPatchItem (asset_id will be filled by caller)
            patch_item = FAAssetPatchItem(
                asset_id=0,  # Placeholder, will be set by caller
                asset_type=asset_type,
                currency=currency,
                classification_params=classification,
                identifier_ticker=identifier_ticker,
                identifier_isin=identifier_isin,
            )

            logger.debug(f"Fetched metadata from yfinance for {identifier}: asset_type={asset_type}, sector={sector}")
            return patch_item

        except AssetRateLimitedError:
            raise  # the core pauses the provider: not "no metadata"
        except Exception as e:
            logger.warning(f"Could not fetch metadata for {identifier}: {e}")
            return None
