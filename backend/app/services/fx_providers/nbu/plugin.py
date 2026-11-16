"""
National Bank of Ukraine (NBU) FX rate provider.

This provider fetches the official exchange rates of the hryvnia (UAH) set by the National Bank of Ukraine, from its
open-data API. Every rate is «UAH per 1 unit of the foreign currency»: UAH is the base of the provider.

API documentation: https://bank.gov.ua/en/open-data/api-dev
Terms: https://bank.gov.ua/en/useterms — the bank asks for a reference to the source for any further use of its
materials; the provider's description names it. robots.txt (16/11/2026): ``Disallow:`` empty for every user agent.
Cloudflare is in front of bank.gov.ua: a 403 is reported as a refusal and never retried or worked around.

Measured on 16/11/2026:

- ``NBU_Exchange/exchange_site?start=YYYYMMDD&end=YYYYMMDD&valcode=<cur>&sort=exchangedate&order=asc&json`` answers a
  JSON list, one object per day, with ``exchangedate`` (the day the rate is valid), ``calcdate`` (the business day the
  bank set it), ``rate`` per ``units`` units and ``rate_per_unit``; ``group`` "3" marks the metals. One currency's whole
  history (USD from 1996) is ~2 MB in one second.
- Saturdays, Sundays and holidays have rows, copies of the last business day's value (same ``calcdate``). Tomorrow's
  row is published in the afternoon before (asked on 16/11: 17.11, ``calcdate`` 16.11).
- Before 02.09.1996 the values are in karbovanets (USD 176100 on 01.09.1996, 1.761 on 02.09.1996): ``FIRST_DAY``.
- An unknown ``valcode`` or an empty range answers ``[]``. A malformed date answers HTTP 200 with a body that is no
  JSON (``[{ Wrong date format/period }]``).
- ``NBUStatService/v1/statdirectory/exchange?json`` lists the day's 45 entries: 40 currencies, the SDR, 4 metals.

D2 (developer decision, lane 75): every row is returned under its ``exchangedate``, weekend copies and tomorrow's row
included; the core drops the days after the sync's end and reads tomorrow's row again at the next sync.
"""

import asyncio
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateLimitedError, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)


class _Refused(FXServiceError):
    """The bank refused the client (HTTP 403): no other currency is asked."""


@register_provider(FXProviderRegistry)
class NBUProvider(FXRateProvider):
    """
    National Bank of Ukraine FX rate provider.

    Provides the official daily exchange rates with UAH as base currency (UAH per unit of each foreign currency).
    Data source: NBU open-data API, range endpoint ``NBU_Exchange/exchange_site``, one request per currency.

    Coverage: discovered from the API at runtime (40 currencies plus UAH on 2026-11-16).
    Update frequency: daily; a rate set on a business day is valid from the next day, weekends repeat Friday's.
    """

    RANGE_URL = "https://bank.gov.ua/NBU_Exchange/exchange_site"
    CATALOG_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange"
    #: The first day of the hryvnia: earlier values are karbovanets.
    FIRST_DAY = date(1996, 9, 2)
    #: Pause between two requests of one call (D9: an explicit, slow pace).
    PAUSE_SECONDS = 0.3
    #: Entries of the catalogue that are no currency: the four metals and the IMF's SDR.
    NOT_CURRENCIES = frozenset({"XAU", "XAG", "XPT", "XPD", "XDR"})

    # What the catalogue returned on 2026-11-16, without metals and SDR, plus UAH. Listed while the first discovery
    # after a restart is slow or fails; the live list replaces it as soon as one arrives.
    FALLBACK_CURRENCIES = (
        "AED",
        "AUD",
        "AZN",
        "BDT",
        "CAD",
        "CHF",
        "CNY",
        "CZK",
        "DKK",
        "DZD",
        "EGP",
        "EUR",
        "GBP",
        "GEL",
        "HKD",
        "HUF",
        "IDR",
        "ILS",
        "INR",
        "JPY",
        "KRW",
        "KZT",
        "LBP",
        "MDL",
        "MXN",
        "MYR",
        "NOK",
        "NZD",
        "PLN",
        "RON",
        "RSD",
        "SAR",
        "SEK",
        "SGD",
        "THB",
        "TND",
        "TRY",
        "UAH",
        "USD",
        "VND",
        "ZAR",
    )

    @property
    def code(self) -> str:
        return "NBU"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "National Bank of Ukraine"

    @property
    def icon(self) -> str | None:
        return "https://bank.gov.ua/frontend/icon/favicon-32x32.png"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/nbu/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "National Bank of Ukraine — official exchange rates of about 40 currencies against UAH, among them KZT, GEL, AZN, MDL, RSD, EGP, LBP and TND. One rate per day, weekends included. Source: National Bank of Ukraine (bank.gov.ua).",
            "it": "Banca Nazionale d'Ucraina — tassi di cambio ufficiali di circa 40 valute contro UAH, tra cui KZT, GEL, AZN, MDL, RSD, EGP, LBP e TND. Un tasso al giorno, weekend compresi. Fonte: Banca Nazionale d'Ucraina (bank.gov.ua).",
            "fr": "Banque nationale d'Ukraine — taux de change officiels d'environ 40 devises contre UAH, dont KZT, GEL, AZN, MDL, RSD, EGP, LBP et TND. Un taux par jour, week-ends compris. Source : Banque nationale d'Ukraine (bank.gov.ua).",
            "es": "Banco Nacional de Ucrania — tipos de cambio oficiales de unas 40 monedas contra UAH, entre ellas KZT, GEL, AZN, MDL, RSD, EGP, LBP y TND. Un tipo por día, fines de semana incluidos. Fuente: Banco Nacional de Ucrania (bank.gov.ua).",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "NBU rates are the bank's official rates. Each is set on a business day and valid from the next day, so it is stored under the day it is valid. At weekends and on holidays the bank repeats the last business day's rate.",
            "it": "I tassi NBU sono i tassi ufficiali della banca. Ciascuno è fissato in un giorno lavorativo e vale dal giorno dopo, quindi è salvato sotto il giorno in cui vale. Nei weekend e nei festivi la banca ripete il tasso dell'ultimo giorno lavorativo.",
            "fr": "Les taux NBU sont les taux officiels de la banque. Chacun est fixé un jour ouvrable et vaut à partir du lendemain : il est enregistré au jour où il vaut. Le week-end et les jours fériés, la banque répète le taux du dernier jour ouvrable.",
            "es": "Los tipos NBU son los tipos oficiales del banco. Cada uno se fija en un día hábil y vale desde el día siguiente, así que se guarda en el día en que vale. Los fines de semana y festivos el banco repite el tipo del último día hábil.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        return "info"

    @property
    def base_currency(self) -> str:
        return "UAH"

    @property
    def test_currencies(self) -> list[str]:
        return ["UAH", "USD", "EUR", "GBP", "JPY", "PLN"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(self.FALLBACK_CURRENCIES)

    async def get_supported_currencies(self) -> list[str]:
        """The currencies of the day's rates (metals and SDR dropped), plus UAH."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.CATALOG_URL, params={"json": ""})
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            raise FXServiceError(f"NBU catalogue request failed: {e}") from e
        entries = self._read_json_list(response.text, "the catalogue")
        currencies = {entry.get("cc") for entry in entries if isinstance(entry, dict)}
        live = {c for c in currencies if isinstance(c, str) and len(c) == 3 and c not in self.NOT_CURRENCIES}
        if not live:
            raise FXServiceError("NBU catalogue lists no currency")
        return sorted(live | {self.base_currency})

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch each asked currency's rates, one range request per currency, in series with a pause:
        ``(exchangedate, CUR, 'UAH', UAH per 1 CUR)``.

        A currency whose answer fails or is not the bank's JSON list is skipped with one warning (XRL-H09); a row that
        is unreadable loses its day only (X-R50). A 403 stops the call (``FXServiceError``), a 429 too
        (``FXRateLimitedError``): both refuse the client, not one currency.

        Raises:
            ValueError: base_currency is neither None nor UAH
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: the bank refused the client (HTTP 403)
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"NBU provider only supports UAH as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = self.FIRST_DAY if start_date == "min" else max(start_date, self.FIRST_DAY)
        wanted = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in wanted}
        if request_start > end_date:
            return results

        for index, currency in enumerate(wanted):
            if index:
                await asyncio.sleep(self.PAUSE_SECONDS)
            try:
                results[currency] = await self._fetch_one(currency, request_start, end_date)
            except (FXRateLimitedError, _Refused):
                raise
            except FXServiceError as e:
                logger.warning(f"NBU fetch failed for {currency}, skipping: {e}")
        return results

    async def _fetch_one(self, currency: str, start: date, end: date) -> list[tuple[date, str, str, Decimal]]:
        params = {"start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"), "valcode": currency.lower(), "sort": "exchangedate", "order": "asc", "json": ""}
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(self.RANGE_URL, params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            if e.response.status_code == 403:
                raise _Refused("NBU refused the request (HTTP 403; bank.gov.ua is behind Cloudflare): not retried, no other currency asked") from e
            raise FXServiceError(f"NBU API error for {currency}: {e}") from e
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            raise FXServiceError(f"NBU API error for {currency}: {e}") from e

        rows = self._read_json_list(response.text, currency)
        observations = []
        for row in rows:
            if not isinstance(row, dict) or row.get("cc") != currency or row.get("group") == "3":
                continue
            observation = self._parse_row(row)
            if observation is not None:
                observations.append(observation)
        return observations

    def _parse_row(self, row: dict) -> tuple[date, str, str, Decimal] | None:
        """One row as ``(exchangedate, CUR, 'UAH', UAH per 1 CUR)``, or None when its day or value is unreadable."""
        try:
            day = datetime.strptime(str(row.get("exchangedate")), "%d.%m.%Y").date()
            per_unit = row.get("rate_per_unit")
            value = Decimal(per_unit) if per_unit is not None else Decimal(row["rate"]) / Decimal(row["units"])
        except (ValueError, TypeError, KeyError, InvalidOperation, ArithmeticError):
            logger.debug(f"NBU: skipping an unreadable row for {row.get('cc')}: {row!r}")
            return None
        if not value.is_finite() or value <= 0:
            logger.debug(f"NBU: skipping a value that is no rate for {row.get('cc')} on {day}: {value}")
            return None
        return day, row["cc"], self.base_currency, value

    @staticmethod
    def _read_json_list(body: str, what: str) -> list:
        """The bank's JSON list, numbers read as ``Decimal``; anything else (an HTML page, the bank's «Wrong date
        format» body, an object) is an ``FXServiceError``."""
        head = body.lstrip()[:200].lower()
        kind = "an HTML page" if head.startswith("<") else f"first bytes {body.lstrip()[:40]!r}"
        try:
            data = json.loads(body, parse_float=Decimal, parse_int=Decimal)
        except ValueError:
            raise FXServiceError(f"NBU answer for {what} is not the JSON list: {kind}") from None
        if not isinstance(data, list):
            raise FXServiceError(f"NBU answer for {what} is not the JSON list: {kind}")
        return data
