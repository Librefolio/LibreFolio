"""
Norges Bank (NORGES) FX rate provider.

This provider fetches the daily exchange rates of Norges Bank, the central bank of Norway, from its SDMX REST API.
Every series is «NOK per 10**UNIT_MULT units of the foreign currency»: NOK is the base of the provider.

API documentation: https://www.norges-bank.no/en/topics/statistics/open-data/
Query builder: https://app.norges-bank.no/query/index.html#/en/
Licence: Norwegian Licence for Open Government Data (NLOD 2.0), as the national catalogue lists it for the bank's open
data API (https://data.norge.no/en/datasets/23076ce8-b442-407c-817f-0d4ec3cbe744): free reuse, with attribution. The
bank says its rates are «only intended to serve as an indication»
(https://www.norges-bank.no/en/topics/statistics/exchange_rates/). robots.txt (16/11/2026): ``Allow: /`` for every
user agent not named, with ``Content-Signal: use=reference``.

Measured on 16/11/2026:

- ``EXR/B.<c1>+<c2>.NOK.SP?format=csv&startPeriod=…&endPeriod=…`` answers every asked series in one ``;``-separated
  CSV, one row per business day. Never send ``locale``: with ``locale=en`` a value carries a thousands separator
  (CHF ``1,140.68``), with ``locale=no`` a decimal comma.
- A range with no observation (a weekend, a range before a series starts) is HTTP 404 with an SDMX error, code 100
  («No data»). An unknown currency in the key is ignored.
- ``EXR/B..NOK.SP?lastNObservations=1`` lists 41 series: 35 live currencies, the SDR (``XDR``), two indices (``I44``,
  ``TWI``) and three closed currencies (RUB 2022-03-01, HRK 2022-12-30, BGN 2025-12-31). History from 1980-12-10 for
  the oldest series (USD, JPY, XDR…), from 1999-01-04 for EUR, later for others (VND 2021-01-04).

Reference specification for the request shape: the open-source Frankfurter project (MIT) reads the same API.
"""

import csv
import io
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FX_HISTORY_MIN_FALLBACK, FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

#: The columns the parser reads; a CSV without one of them is not the bank's answer.
_COLUMNS = ("BASE_CUR", "QUOTE_CUR", "UNIT_MULT", "TIME_PERIOD", "OBS_VALUE")


@register_provider(FXProviderRegistry)
class NorgesBankProvider(FXRateProvider):
    """
    Norges Bank FX rate provider.

    Provides daily exchange rates with NOK as base currency (NOK per unit of each foreign currency).
    Data source: Norges Bank SDMX REST API, dataflow ``EXR``, business-day series ``B.<CUR>.NOK.SP``.

    Coverage: discovered from the API at runtime (35 currencies plus NOK on 2026-11-13).
    Update frequency: daily, Norwegian business days, around 16:00 CET.
    """

    BASE_URL = "https://data.norges-bank.no/api/data/EXR"
    #: Series of the catalogue that are no currency: two NOK exchange-rate indices and the IMF's SDR.
    NOT_CURRENCIES = frozenset({"I44", "TWI", "XDR"})
    #: A series whose last value is older than this, counted from the newest value of the catalogue, is closed.
    CLOSED_AFTER = timedelta(days=31)

    # What the catalogue returned on 2026-11-13, without indices, SDR and closed series, plus NOK. Listed while the
    # first discovery after a restart is slow or fails; the live list replaces it as soon as one arrives.
    FALLBACK_CURRENCIES = (
        "AUD",
        "BDT",
        "BRL",
        "BYN",
        "CAD",
        "CHF",
        "CNY",
        "CZK",
        "DKK",
        "EUR",
        "GBP",
        "HKD",
        "HUF",
        "IDR",
        "ILS",
        "INR",
        "ISK",
        "JPY",
        "KRW",
        "MMK",
        "MXN",
        "MYR",
        "NOK",
        "NZD",
        "PHP",
        "PKR",
        "PLN",
        "RON",
        "SEK",
        "SGD",
        "THB",
        "TRY",
        "TWD",
        "USD",
        "VND",
        "ZAR",
    )

    @property
    def code(self) -> str:
        return "NORGES"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Norges Bank"

    @property
    def icon(self) -> str | None:
        return "https://www.norges-bank.no/Static/Favicons/favicon-32x32.png"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/norges/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Norges Bank, the central bank of Norway — daily exchange rates of about 35 currencies against NOK, among them BDT, PKR, VND, TWD and MMK. Updated every Norwegian business day around 16:00 CET. Source: Norges Bank, open data under the NLOD 2.0 licence.",
            "it": "Norges Bank, la banca centrale norvegese — tassi di cambio giornalieri di circa 35 valute contro NOK, tra cui BDT, PKR, VND, TWD e MMK. Aggiornamento ogni giorno lavorativo norvegese verso le 16:00 CET. Fonte: Norges Bank, dati aperti con licenza NLOD 2.0.",
            "fr": "Norges Bank, la banque centrale de Norvège — taux de change quotidiens d'environ 35 devises contre NOK, dont BDT, PKR, VND, TWD et MMK. Mise à jour chaque jour ouvrable norvégien vers 16h00 CET. Source : Norges Bank, données ouvertes sous licence NLOD 2.0.",
            "es": "Norges Bank, el banco central de Noruega — tipos de cambio diarios de unas 35 monedas contra NOK, entre ellas BDT, PKR, VND, TWD y MMK. Actualizado cada día hábil noruego alrededor de las 16:00 CET. Fuente: Norges Bank, datos abiertos con licencia NLOD 2.0.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "Norges Bank's rates are mid rates the bank publishes only as an indication. One value per Norwegian business day: none at weekends and on Norwegian holidays.",
            "it": "I tassi di Norges Bank sono tassi medi che la banca pubblica solo come indicazione. Un valore per ogni giorno lavorativo norvegese: nessuno nei weekend e nelle festività norvegesi.",
            "fr": "Les taux de Norges Bank sont des taux moyens que la banque publie à titre indicatif seulement. Une valeur par jour ouvrable norvégien : aucune le week-end ni les jours fériés norvégiens.",
            "es": "Los tipos de Norges Bank son tipos medios que el banco publica solo como indicación. Un valor por cada día hábil noruego: ninguno los fines de semana ni en los festivos noruegos.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        return "info"

    @property
    def base_currency(self) -> str:
        return "NOK"

    @property
    def test_currencies(self) -> list[str]:
        return ["NOK", "USD", "EUR", "GBP", "JPY", "SEK"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(self.FALLBACK_CURRENCIES)

    async def get_supported_currencies(self) -> list[str]:
        """
        The live currencies of the catalogue (last observation of every ``B..NOK.SP`` series), plus NOK.

        Drops the indices and the SDR, and every series whose last value is more than ``CLOSED_AFTER`` older than the
        newest value of the answer (RUB, HRK, BGN on 2026-11-13).
        """
        rows = await self._get_csv("", {"format": "csv", "lastNObservations": "1"})
        last_day: dict[str, date] = {}
        for row in rows:
            currency = row["BASE_CUR"]
            if currency in self.NOT_CURRENCIES or row["QUOTE_CUR"] != self.base_currency:
                continue
            try:
                last_day[currency] = date.fromisoformat(row["TIME_PERIOD"])
            except ValueError:
                continue
        if not last_day:
            raise FXServiceError("Norges Bank catalogue lists no currency")
        newest = max(last_day.values())
        live = {currency for currency, day in last_day.items() if newest - day <= self.CLOSED_AFTER}
        return sorted(live | {self.base_currency})

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch the rates of every asked currency in one request: ``(day, CUR, 'NOK', NOK per 1 CUR)``.

        Every value keeps the day the bank gives it (D2: the core, not the plugin, drops days after the sync's end).
        A value that is no number loses its day only (X-R50). The call is one request for every currency, so an
        answer that is not the CSV is one ``FXServiceError`` for the whole call.

        Raises:
            ValueError: base_currency is neither None nor NOK
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: the request failed, or the answer is not the bank's CSV
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"Norges Bank provider only supports NOK as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FX_HISTORY_MIN_FALLBACK if start_date == "min" else start_date
        wanted = sorted({c for c in currencies if c != self.base_currency})
        if not wanted:
            return {}

        params = {"format": "csv", "startPeriod": request_start.isoformat(), "endPeriod": end_date.isoformat()}
        rows = await self._get_csv("+".join(wanted), params)

        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in wanted}
        for row in rows:
            currency = row["BASE_CUR"]
            if currency not in results or row["QUOTE_CUR"] != self.base_currency:
                continue
            observation = self._parse_row(row)
            if observation is not None:
                results[currency].append(observation)
        return results

    def _parse_row(self, row: dict[str, str]) -> tuple[date, str, str, Decimal] | None:
        """One row as ``(day, CUR, 'NOK', NOK per 1 CUR)``, or None when its day or value is unreadable."""
        try:
            day = date.fromisoformat(row["TIME_PERIOD"])
            value = Decimal(row["OBS_VALUE"]) / (Decimal(10) ** int(row["UNIT_MULT"]))
        except (ValueError, InvalidOperation):
            logger.debug(f"NORGES: skipping an unreadable row for {row.get('BASE_CUR')} on {row.get('TIME_PERIOD')!r}: {row.get('OBS_VALUE')!r}")
            return None
        if not value.is_finite() or value <= 0:
            logger.debug(f"NORGES: skipping a value that is no rate for {row['BASE_CUR']} on {day}: {row['OBS_VALUE']!r}")
            return None
        return day, row["BASE_CUR"], self.base_currency, value

    async def _get_csv(self, currency_key: str, params: dict[str, str]) -> list[dict[str, str]]:
        """GET ``EXR/B.<currency_key>.NOK.SP`` and return its CSV rows; the SDMX «No data» answer is no row."""
        url = f"{self.BASE_URL}/B.{currency_key}.{self.base_currency}.SP"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 404 and 'code="100"' in response.text:
                    return []  # SDMX «No data»: no business day in the range
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            logger.warning(f"Norges Bank request failed: {e}")
            raise FXServiceError(f"Norges Bank API error: {e}") from e
        return self._read_csv(response.text)

    @staticmethod
    def _read_csv(body: str) -> list[dict[str, str]]:
        """The rows of the bank's CSV; anything else (an HTML page, a CSV without the columns read) is an error."""
        head = body.lstrip()[:200].lower()
        if head.startswith("<") or "<html" in head or "<!doctype" in head:
            raise FXServiceError("Norges Bank answer is an HTML page, not the CSV (endpoint changed or request refused)")
        reader = csv.DictReader(io.StringIO(body), delimiter=";")
        missing = [column for column in _COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            first_line = body.split("\n", 1)[0][:60]
            raise FXServiceError(f"Norges Bank answer is not the expected CSV: columns {missing} missing (first line {first_line!r})")
        return list(reader)
