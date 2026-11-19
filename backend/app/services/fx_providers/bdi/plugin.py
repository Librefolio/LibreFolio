"""
Banca d'Italia (BDI) FX rate provider.

This provider fetches the daily exchange rates the Banca d'Italia publishes for about 150 currencies against the euro
(the «terze valute» portal). Every rate is «foreign currency per 1 EUR»: EUR is the base of the provider.

Portal: https://www.bancaditalia.it/compiti/operazioni-cambi/portale-tassi/index.html
API instructions: https://tassidicambio.bancaditalia.it/terzevalute-wf-ui-web/assets/files/Operating_Instructions.pdf
Terms: the site is © Banca d'Italia (https://www.bancaditalia.it/footer/copyright/index.html); the bank calls the rates
indicative, not a financial benchmark under Regulation (EU) 2016/1011. Developer decision D1 (lane 75, 16/11/2026): the
provider is offered for a self-hosted instance that stores the rates for its owner; nothing downloaded from the bank is
committed (tests use synthetic answers only). The description names the source.

Measured on 16/11/2026:

- ``dailyTimeSeries?startDate=…&endDate=…&baseCurrencyIsoCode=<CUR>&currencyIsoCode=EUR&lang=en`` with ``Accept:
  application/json`` answers ``resultsInfo`` (``exchangeConventionCode`` "C") and ``rates`` (``referenceDate``,
  ``avgRate`` as a string, ``exchangeConvention`` «Foreign currency amount for 1 Euro.»). All 171 currencies of a day had
  convention C. One currency's whole history (USD from 1999) is ~0.8 MB in ~1.8 s.
- ``baseCurrencyIsoCode`` is the foreign currency: the other way round the API answers HTTP 400 with a plain-text
  «WARNING! Parameter currencyIsoCode can take the value of: EUR, USD or ITL».
- The euro series start on 1999-01-04 (``FIRST_DAY``); a weekend range answers 200 with ``totalRecords: 0``.
- A suspended currency keeps its rows with ``avgRate`` «N.A.» (RUB from 2022-03-02; BYN, IRR, KPW, RUB today).
- ``latestRates`` lists the last day's rate of every country's currency: 172 rows, 150 currencies (EUR included).
- For some administered currencies the value is close to the official rate of the day before (NGN, 13/11/2026: 0.04%
  from the CBN rate of 12/11, 0.18% from that of 13/11).

Reference specification for the request shape: the open-source Frankfurter project (MIT) reads the same API.
"""

import asyncio
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateLimitedError, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

#: The only quotation the parser accepts: «foreign currency per 1 EUR». Anything else would store the rate upside down.
_FOR_ONE_EURO_CODE = "C"
_FOR_ONE_EURO = "foreign currency amount for 1 euro"


@register_provider(FXProviderRegistry)
class BDIProvider(FXRateProvider):
    """
    Banca d'Italia FX rate provider.

    Provides daily exchange rates with EUR as base currency (foreign currency per 1 EUR), for about 150 currencies.
    Data source: Banca d'Italia «terze valute» REST API, one time-series request per currency.

    Coverage: discovered from the API at runtime (149 currencies plus EUR on 2026-11-16).
    Update frequency: daily, Italian business days.
    """

    BASE_URL = "https://tassidicambio.bancaditalia.it/terzevalute-wf-web/rest/v1.0"
    #: The first day of the euro series.
    FIRST_DAY = date(1999, 1, 4)
    #: Pause between two requests of one call (D9: an explicit, slow pace; Frankfurter uses 0.3 s too).
    PAUSE_SECONDS = 0.3
    #: Entries of ``latestRates`` that are no currency: the IMF's SDR.
    NOT_CURRENCIES = frozenset({"XDR"})

    # What ``latestRates`` returned on 2026-11-16 (rates «N.A.» and the SDR left out), EUR included. Listed while the
    # first discovery after a restart is slow or fails; the live list replaces it as soon as one arrives.
    FALLBACK_CURRENCIES = tuple(
        (
            "AED AFN ALL AMD AOA ARS AUD AWG AZN BAM BBD BDT BHD BIF BMD BND BOB BRL BSD BTN BWP BZD CAD CDF CHF CLP CNY COP CRC "
            "CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD "
            "ISK JMD JOD JPY KES KGS KHR KMF KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK "
            "MXN MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RWF SAR SBD SCR SDG SEK SGD SHP SLE "
            "SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD UYU UZS VES VND VUV WST XAF XCD XCG XOF "
            "XPF YER ZAR ZMW ZWG"
        ).split()
    )

    @property
    def code(self) -> str:
        return "BDI"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Banca d'Italia"

    @property
    def icon(self) -> str | None:
        # An exception among the FX providers, which give their bank's icon URL (developer decision, 19/11/2026): the
        # bank serves its favicon with «Cross-Origin-Resource-Policy: same-origin», so a browser refuses to show it on
        # any other site. We serve a copy, taken once from
        # https://www.bancaditalia.it/application/themes/bdi2/img/favicon.png, from the frontend's static icons
        # (``frontend/static/icons/fx/bdi.png``, copied into the user guide by ``dev.py mkdocs build``).
        return "/icons/fx/bdi.png"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/bdi/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Banca d'Italia — daily exchange rates of about 150 currencies against EUR, almost every currency in the world in one step to the euro (NGN, KES, GHS, EGP, VND, PKR, DOP, UGX…). Italian business days, history from 1999. Source: Banca d'Italia.",
            "it": "Banca d'Italia — tassi di cambio giornalieri di circa 150 valute contro EUR, quasi ogni valuta del mondo in un passo verso l'euro (NGN, KES, GHS, EGP, VND, PKR, DOP, UGX…). Giorni lavorativi italiani, storia dal 1999. Fonte: Banca d'Italia.",
            "fr": "Banca d'Italia — taux de change quotidiens d'environ 150 devises contre EUR, presque toutes les devises du monde en une étape vers l'euro (NGN, KES, GHS, EGP, VND, PKR, DOP, UGX…). Jours ouvrables italiens, historique depuis 1999. Source : Banca d'Italia.",
            "es": "Banca d'Italia — tipos de cambio diarios de unas 150 monedas contra EUR, casi todas las monedas del mundo en un paso hacia el euro (NGN, KES, GHS, EGP, VND, PKR, DOP, UGX…). Días hábiles italianos, historial desde 1999. Fuente: Banca d'Italia.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "Banca d'Italia's rates are indicative, not a financial benchmark. For the major currencies they are the ECB reference rates; for the others the bank computes them, and for some administered currencies the value can reflect the official rate of the day before.",
            "it": "I tassi della Banca d'Italia sono indicativi, non un benchmark finanziario. Per le valute principali sono i tassi di riferimento BCE; per le altre li calcola la banca, e per alcune valute amministrate il valore può riflettere il tasso ufficiale del giorno prima.",
            "fr": "Les taux de la Banca d'Italia sont indicatifs, pas un indice de référence financier. Pour les principales devises ce sont les taux de référence de la BCE ; pour les autres la banque les calcule, et pour certaines devises administrées la valeur peut refléter le taux officiel de la veille.",
            "es": "Los tipos de la Banca d'Italia son indicativos, no un índice de referencia financiero. Para las monedas principales son los tipos de referencia del BCE; para las demás los calcula el banco, y para algunas monedas administradas el valor puede reflejar el tipo oficial del día anterior.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # A data limit that can mislead (a value of the day before for some currencies), not only a fact: warning
        return "warning"

    @property
    def base_currency(self) -> str:
        return "EUR"

    @property
    def test_currencies(self) -> list[str]:
        return ["EUR", "USD", "GBP", "JPY", "NGN", "KES"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(self.FALLBACK_CURRENCIES)

    async def get_supported_currencies(self) -> list[str]:
        """The currencies of ``latestRates`` with a rate (not «N.A.»), the SDR left out, EUR included."""
        data = await self._get_json("/latestRates", {"lang": "en"}, "the catalogue")
        rows = data.get("latestRates")
        if not isinstance(rows, list):
            raise FXServiceError("Banca d'Italia catalogue has no latestRates list (endpoint changed)")
        currencies = {row.get("isoCode") for row in rows if isinstance(row, dict) and self._rate(row.get("eurRate")) is not None}
        live = {c for c in currencies if isinstance(c, str) and len(c) == 3 and c not in self.NOT_CURRENCIES}
        if not live:
            raise FXServiceError("Banca d'Italia catalogue lists no currency")
        return sorted(live | {self.base_currency})

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch each asked currency's euro series, one request per currency, in series with a pause:
        ``(referenceDate, 'EUR', CUR, CUR per 1 EUR)``.

        A currency whose answer fails, is not JSON, or is quoted in another convention is skipped with one warning
        (XRL-H09); a value «N.A.» or unreadable loses its day only (X-R50). A 429 stops the call.

        Raises:
            ValueError: base_currency is neither None nor EUR
            FXRateLimitedError: the bank refused for too many requests
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"Banca d'Italia provider only supports EUR as base currency, got {base_currency}")

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
            except FXRateLimitedError:
                raise
            except FXServiceError as e:
                logger.warning(f"BDI fetch failed for {currency}, skipping: {e}")
        return results

    async def _fetch_one(self, currency: str, start: date, end: date) -> list[tuple[date, str, str, Decimal]]:
        params = {"startDate": start.isoformat(), "endDate": end.isoformat(), "baseCurrencyIsoCode": currency, "currencyIsoCode": self.base_currency, "lang": "en"}
        data = await self._get_json("/dailyTimeSeries", params, currency)
        rows = data.get("rates")
        if not isinstance(rows, list):
            if (data.get("resultsInfo") or {}).get("totalRecords") == 0:
                return []  # no business day in the range
            raise FXServiceError(f"Banca d'Italia answer for {currency} has no rates list (endpoint changed)")
        self._check_convention(data, rows, currency)

        observations = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            value = self._rate(row.get("avgRate"))
            try:
                day = date.fromisoformat(str(row.get("referenceDate")))
            except ValueError:
                day = None
            if value is None or day is None:
                logger.debug(f"BDI: skipping a day with no rate for {currency}: {row.get('referenceDate')!r} {row.get('avgRate')!r}")
                continue
            observations.append((day, self.base_currency, currency, value))
        return observations

    @staticmethod
    def _check_convention(data: dict, rows: list, currency: str) -> None:
        """Refuse a series that is not «foreign currency per 1 EUR»: stored as such it would be upside down."""
        code = (data.get("resultsInfo") or {}).get("exchangeConventionCode")
        conventions = {str(row.get("exchangeConvention", "")).strip().rstrip(".").lower() for row in rows if isinstance(row, dict) and row.get("exchangeConvention")}
        if (code is not None and code != _FOR_ONE_EURO_CODE) or conventions - {_FOR_ONE_EURO}:
            raise FXServiceError(f"Banca d'Italia quotes {currency} in another convention ({code!r}, {sorted(conventions)}): not «foreign currency per 1 EUR»")

    @staticmethod
    def _rate(text: object) -> Decimal | None:
        """A rate as ``Decimal``, or None for «N.A.», an empty value or anything that is no positive number."""
        try:
            value = Decimal(str(text))
        except InvalidOperation:
            return None
        return value if value.is_finite() and value > 0 else None

    async def _get_json(self, path: str, params: dict[str, str], what: str) -> dict:
        """GET ``BASE_URL + path`` as JSON; an HTTP error, an HTML page or a body that is no JSON object is an
        ``FXServiceError`` naming ``what``."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(f"{self.BASE_URL}{path}", params=params, headers={"Accept": "application/json"})
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            raise FXServiceError(f"Banca d'Italia API error for {what}: {e}") from e
        body = response.text
        try:
            data = json.loads(body)
        except ValueError:
            kind = "an HTML page" if body.lstrip()[:1] == "<" else f"first bytes {body.lstrip()[:40]!r}"
            raise FXServiceError(f"Banca d'Italia answer for {what} is not JSON: {kind}") from None
        if not isinstance(data, dict):
            raise FXServiceError(f"Banca d'Italia answer for {what} is not a JSON object")
        return data
