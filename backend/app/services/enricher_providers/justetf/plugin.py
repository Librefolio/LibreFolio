"""The justETF enricher (plan 68, C1): the profile of an ETF, ETC or ETN from its page on justETF, by ISIN.

It reads the fund page through our library ``justetf-scraping`` (``get_etf_overview``) and translates it into the voices
of the profile catalogue; the full list (``load_overview``) serves the search. The price provider of the same name is
another plugin: nothing is shared with it (plan §C, rule 1).

What it gives, from one page: the description (the page's prose), TER, fund size, index, fund provider, replication,
distribution policy, domicile, fund currency, inception date, countries and sectors, and the legal form of an ETC or
ETN. Not read: «currency hedged» (the library reads a line the page no longer has, so every fund comes out hedged), the
top holdings and the listings. An ETF gets no legal form: the library does not read the page's «UCITS compliance» line,
and an ETF is not necessarily UCITS (a Swiss one is not).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping
from datetime import date
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
    from justetf_scraping import get_etf_overview, load_overview
except ImportError:  # pragma: no cover — the library is in the lock; without it every call answers «error»
    get_etf_overview = None
    load_overview = None

logger = get_logger(__name__)

PROVIDER_NAME = "justETF"

#: One pace for every call of this plugin to justetf.com, whatever read, «Riconosci» or search it comes from (plan 68, C5;
#: the round-30 rule: the plugin paces its own calls). Module level: the registry builds a new instance for every call,
#: so a pacer on ``self`` would never be shared. Per process (``utils/runtime/pacing.py``).
_PACER = Pacer(1.0)
#: The error code of a read the library or the site failed (not a refusal for too many requests).
SOURCE_ERROR = "SOURCE_ERROR"
_PAGE_URL = "https://www.justetf.com/en/etf-profile.html?isin={isin}"

_FUND_VOICES = frozenset(
    {
        "description",
        "ter",
        "fund_size",
        "index_name",
        "fund_provider",
        "replication",
        "distribution_policy",
        "fund_domicile",
        "fund_currency",
        "inception_date",
        "geography",
        "sector",
        "legal_form",
    }
)
#: The ETF family and the ETCs (a commodity held through a note); a degree of 10, before a second source.
_COVERED = frozenset({AssetType.COMMODITY} | {t for t in AssetType if t == AssetType.ETF or t.value.startswith("ETF_")})
#: The types an ETC or an ETN may be filed under: only there the plugin declares ``legal_form`` (the declared voices
#: drive the wait for the second round and what the window says it would fill).
_ETC_ETN_TYPES = frozenset({AssetType.ETF, AssetType.ETF_COMMODITY, AssetType.ETF_CRYPTO, AssetType.COMMODITY})
#: The voices dated by the fund's holdings date.
_HOLDINGS_VOICES = ("geography", "sector")
_DAY_MONTH_YEAR = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_DEGREE = 10

_REPLICATION = {
    "physical(full replication)": "physical_full",
    "physical(optimized sampling)": "physical_sampling",
    "physical(sampling)": "physical_sampling",
    "physical(physically backed)": "physical_backed",
    "synthetic(unfunded swap)": "synthetic_unfunded_swap",
    "synthetic(funded swap)": "synthetic_funded_swap",
}
_DISTRIBUTION = {"accumulating": "accumulating", "distributing": "distributing"}
_LEGAL_FORM = {"etc": "etc_etn", "etn": "etc_etn"}
_MONTHS = {name: number for number, name in enumerate(("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"), start=1)}
_ENGLISH_DATE = re.compile(r"(\d{1,2}) ([A-Za-z]+) (\d{4})")
#: The fields of a sheet only a fund the site knows has: none of them present is the empty «ETF Screener» page.
_FOUND_FIELDS = ("legal_structure", "ter", "fund_provider", "index")
#: justETF's sector names that are not the standard ones (``utils/asset/sector.py``), translated by this plugin. Only
#: names whose meaning is clear: «Non-Corporate» appears in equity funds too, where it is no government bond, so it is
#: left to the catalogue («Other»).
_SECTORS = {
    "finance": "Financials",
    "consumer non-cyclicals": "Consumer Staples",
    "consumer cyclicals": "Consumer Discretionary",
    "consumer services": "Consumer Discretionary",
    "non-energy materials": "Basic Materials",
    "business services": "Industrials",
    "sovereign": "Government Bonds",
    "government agencies": "Government Bonds",
    "municipal": "Government Bonds",
}
OTHER = "Other"
_MILLION = Decimal(1_000_000)
_HUNDRED = Decimal(100)


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _text(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _choice(table: Mapping[str, str], value: Any, field: str, isin: str) -> str | None:
    text = _text(value)
    if text is None:
        return None
    choice = table.get(text.lower())
    if choice is None:
        logger.warning("justETF value not translated, voice left out", field=field, value=text, isin=isin)
    return choice


def _country(name: Any, isin: str) -> str | None:
    text = _text(name)
    if text is None:
        return None
    try:
        return normalize_country_to_iso3(text)
    except ValueError:
        logger.warning("justETF country not translated", country=text, isin=isin)
        return None


def _english_date(value: Any) -> str | None:
    match = _ENGLISH_DATE.fullmatch(_text(value) or "")
    month = _MONTHS.get(match.group(2).lower()) if match else None
    if match is None or month is None:
        return None
    try:
        return date(int(match.group(3)), month, int(match.group(1))).isoformat()
    except ValueError:
        return None


def _weights(rows: Any, key_of, isin: str) -> dict[str, str]:
    """``[{"name", "percentage"}]`` → key → weight as a fraction. A name ``key_of`` cannot translate goes to «Other»:
    no weight is lost, so the map still sums to one (the catalogue refuses one that does not)."""
    weights: dict[str, Decimal] = {}
    for row in rows or ():
        percentage = _decimal(row.get("percentage")) if isinstance(row, Mapping) else None
        if percentage is None or percentage <= 0:
            continue
        key = key_of(row.get("name"), isin) or OTHER
        weights[key] = weights.get(key, Decimal(0)) + percentage / _HUNDRED
    return {key: format(weight, "f") for key, weight in weights.items()}


def _geography_key(name: Any, isin: str) -> str | None:
    # «Other» is a key of its own, kept as it is: the country helper's fuzzy search would read it as a country
    return OTHER if isinstance(name, str) and name.strip().lower() == "other" else _country(name, isin)


def _sector_key(name: Any, isin: str) -> str | None:
    # The generic helper first: a name it knows goes on as it is; the table holds only justETF's own words
    text = _text(name)
    if text is None or validate_sector(text):
        return text
    return _SECTORS.get(text.lower(), text)


def _holdings_date(value: Any) -> date | None:
    """«30/09/2026» → 2026-09-30; None for anything else."""
    match = _DAY_MONTH_YEAR.fullmatch(_text(value) or "")
    if match is None:
        return None
    try:
        return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
    except ValueError:
        return None


def overview_source_dates(overview: Mapping[str, Any], voices: Mapping[str, Any]) -> dict[str, date]:
    """The holdings date of the sheet, on the countries and sectors it gives."""
    day = _holdings_date(overview.get("holdings_date"))
    return {key: day for key in _HOLDINGS_VOICES if key in voices} if day is not None else {}


def is_found(overview: Mapping[str, Any]) -> bool:
    """Whether the sheet is a fund's: for an ISIN it does not know, the site answers an empty «ETF Screener» page."""
    return any(overview.get(field) is not None for field in _FOUND_FIELDS)


def overview_voices(overview: Mapping[str, Any]) -> dict[str, Any]:
    """The catalogue voices of one fund sheet, as raw values; a voice the sheet does not give is absent."""
    isin = str(overview.get("isin") or "")
    ter = _decimal(overview.get("ter"))
    size = _decimal(overview.get("fund_size_eur"))
    voices: dict[str, Any] = {
        "description": _text(overview.get("description")),
        "ter": format(ter / _HUNDRED, "f") if ter is not None else None,
        "fund_size": {"amount": format(size * _MILLION, "f"), "currency": "EUR"} if size is not None else None,
        "index_name": _text(overview.get("index")),
        "fund_provider": _text(overview.get("fund_provider")),
        "replication": _choice(_REPLICATION, overview.get("replication"), "replication", isin),
        "distribution_policy": _choice(_DISTRIBUTION, overview.get("distribution_policy"), "distribution_policy", isin),
        "fund_domicile": _country(overview.get("fund_domicile"), isin),
        "fund_currency": _text(overview.get("fund_currency")),
        "inception_date": _english_date(overview.get("inception_date")),
        "geography": _weights(overview.get("countries"), _geography_key, isin) or None,
        "sector": _weights(overview.get("sectors"), _sector_key, isin) or None,
        # An ETF is left out: «ETF» does not say whether it is UCITS
        "legal_form": _LEGAL_FORM.get((_text(overview.get("legal_structure")) or "").lower()),
    }
    return {key: value for key, value in voices.items() if value is not None}


@register_provider(EnricherRegistry)
class JustETFEnricher(EnricherPlugin):
    """The profile of an ETF, ETC or ETN from its page on justETF."""

    code = "justetf"
    name = "justETF"
    icon = "https://www.justetf.com/android-chrome-144x144.png?v2"
    terms = EnricherTerms.PRICE_SOURCE
    accepted_identifier_types = ("ISIN",)
    voices = {asset_type: _FUND_VOICES if asset_type in _ETC_ETN_TYPES else _FUND_VOICES - {"legal_form"} for asset_type in _COVERED}
    default_priority = {asset_type: _DEGREE if asset_type in _COVERED else None for asset_type in AssetType}

    def page_url(self, binding: EnricherBinding) -> str | None:
        return _PAGE_URL.format(isin=binding.identifier)

    @property
    def test_cases(self) -> list[dict]:
        return [
            {"binding": {"identifier_type": "ISIN", "identifier": "IE00B4L5Y983"}, "asset_type": AssetType.ETF.value},
            {"binding": {"identifier_type": "ISIN", "identifier": "IE00B4ND3602"}, "asset_type": AssetType.COMMODITY.value},
        ]

    @staticmethod
    def _isin(binding: EnricherBinding) -> str | None:
        if binding.identifier_type != "ISIN":
            return None
        return binding.identifier.strip().upper() or None

    @staticmethod
    def _overview(isin: str) -> Mapping[str, Any]:
        if get_etf_overview is None:
            raise RuntimeError("justetf-scraping is not installed")
        _PACER.wait()
        return get_etf_overview(isin, include_gettex=False)

    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        isin = self._isin(binding)
        if isin is None:
            return EnricherRecognition(found=False)
        overview = self._overview(isin)
        if not is_found(overview):
            return EnricherRecognition(found=False)
        return EnricherRecognition(found=True, name=_text(overview.get("name")), page_url=self.page_url(binding))

    def read(self, bindings: list[EnricherBinding], keys: Iterable[str] | None = None) -> Iterator[EnricherReadItem]:
        refused: float | None | bool = False  # after a refusal, the rest is refused too, with no call
        for index, binding in enumerate(bindings):
            isin = self._isin(binding)
            if isin is None:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
                continue
            if refused is not False:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED, retry_after=refused)
                continue
            try:
                overview = self._overview(isin)
            except Exception as error:  # noqa: BLE001 — isolation boundary: one fund's failure is that fund's outcome
                limited = rate_limited_from_exception(error, PROVIDER_NAME)
                if limited is not None:
                    refused = limited.retry_after
                    logger.warning("justETF refused for too many requests", isin=isin, retry_after=refused)
                    yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED, retry_after=refused)
                else:
                    logger.warning("justETF read failed", isin=isin, exc_info=error)
                    yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=SOURCE_ERROR, error_message=type(error).__name__)
                continue
            if not is_found(overview):
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
            else:
                values = overview_voices(overview)
                yield EnricherReadItem(index=index, status=EnricherReadStatus.OK, values=values, source_dates=overview_source_dates(overview, values))

    def search(self, query: str) -> list[EnricherSearchResult]:
        if load_overview is None:
            raise RuntimeError("justetf-scraping is not installed")
        _PACER.wait()
        try:
            frame = load_overview()
        except Exception as error:
            limited = rate_limited_from_exception(error, PROVIDER_NAME)
            if limited is None:
                raise
            raise EnricherRateLimited(f"{PROVIDER_NAME} refused the search for too many requests", retry_after=limited.retry_after) from error
        needle = query.strip().lower()
        if not needle:
            return []
        results: list[EnricherSearchResult] = []
        for isin, row in frame.iterrows():
            haystack = " ".join(str(row.get(column) or "") for column in ("name", "ticker", "wkn")) + f" {isin}"
            if needle in haystack.lower():
                binding = EnricherBinding(identifier_type="ISIN", identifier=str(isin))
                results.append(EnricherSearchResult(name=str(row.get("name") or isin), binding=binding, asset_type=AssetType.ETF, page_url=self.page_url(binding)))
        return results
