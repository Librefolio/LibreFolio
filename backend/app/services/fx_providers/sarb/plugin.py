"""
South African Reserve Bank (SARB) FX rate provider.

This provider reads the daily exchange rates of the South African Reserve Bank, one JSON series per currency, from the
service API behind the bank's web pages. ZAR is the base of the provider; the direction is the series', mixed: three
«Rand per X» series (USD, GBP, EUR) and 22 «X per Rand».

Series list: ``https://custom.resbank.co.za/SarbWebApi/WebIndicators/HistoricalExchangeRatesDaily/``, the list behind
the bank's «Selected Historical Rates» page
(https://www.resbank.co.za/en/home/what-we-do/statistics/key-statistics/selected-historical-rates). The API's own help
page (``/SarbWebApi/Help``) answered 404 on 16/11 and on 19/11/2026: the codes below come from that list.
Terms: https://www.resbank.co.za/en/home/quick-links/disclaimer — the material «may not be copied, reproduced, adapted,
published or distributed in any form whatsoever without the prior written consent» of the bank. Developer decision D1
(lane 75, 16/11/2026): the provider is offered for a self-hosted instance that stores the rates for its owner; nothing
downloaded from the bank is committed (tests use synthetic answers only). The description names the source. robots.txt
of ``www.resbank.co.za`` disallows only ``/content/dam/``; ``custom.resbank.co.za`` has none (404).

Measured on 19/11/2026:

- ``…/Shared/GetTimeseriesObservations/{CODE}/{yyyy-MM-dd}/{yyyy-MM-dd}`` answers a JSON list, newest first:
  ``{"Period": "2026-11-19T00:00:00", "Timeseries": "Rand per US Dollar", "Value": 17.2532, "FormatNumber": "0.0000",
  …}``. An unknown code, or a range without data (a weekend), answers 200 with ``[]``.
- The rate is the «weighted average of the banks' daily rates at approximately 10:30 am», one per South African
  business day, the value of the day published that morning.
- Four decimals: CHF 0.0488 per rand is rounded by up to ~0.1%, CAD 0.0830 and AUD 0.0865 by ~0.06%.
- RUB (``EXCB110D``, «Russia: Rouble per Rand»): served since the developer's answer to Q3 (19/11/2026, lane 75): the
  rouble published by a bank other than the Central Bank of Russia (CBR, suspended by D4) is a route like the others,
  with a neutral note saying where it comes from.
- Budget: one request per currency with ``PAUSE_SECONDS`` between two (D9). A series from 1970 is ~4 MB in ~7 s, from
  2000 ~3.3 s, from 2010 ~1.5 s: with 25 currencies a history from 1970 would take ~3 minutes, over the 120 s the core
  gives a leg. ``FIRST_DAY`` is 2010-01-01: ``"min"`` for 24 of them took 68.9 s (25 with RUB: ~72 s, estimated), 14 days for two currencies 2.0 s
  (19/11/2026); a route usually asks one to three currencies. The ECB and BDI hold the older ZAR history.
"""

import asyncio
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

SERIES_URL = "https://custom.resbank.co.za/SarbWebApi/WebIndicators/Shared/GetTimeseriesObservations"
#: Each currency's series and its direction: True for «Rand per X» (ZAR per 1 X), False for «X per Rand».
SERIES: dict[str, tuple[str, bool]] = {
    "USD": ("EXCX135D", True),
    "GBP": ("EXCZ001D", True),
    "EUR": ("EXCZ002D", True),
    "AUD": ("EXCB080D", False),
    "BWP": ("EXCB051D", False),
    "BRL": ("EXCB036D", False),
    "CAD": ("EXCB031D", False),
    "CNY": ("EXCB121D", False),
    "DKK": ("EXCB003D", False),
    "HKD": ("EXCB122D", False),
    "INR": ("EXCB123D", False),
    "ILS": ("EXCB094D", False),
    "JPY": ("EXCB120D", False),
    "KES": ("EXCB059D", False),
    "MWK": ("EXCB063D", False),
    "MZN": ("EXCB065D", False),
    "NZD": ("EXCB081D", False),
    "NOK": ("EXCB013D", False),
    "KRW": ("EXCB118D", False),
    "SEK": ("EXCB015D", False),
    "CHF": ("EXCB016D", False),
    "TWD": ("EXCB126D", False),
    "THB": ("EXCB115D", False),
    "ZMW": ("EXCB071D", False),
    "RUB": ("EXCB110D", False),
}

_CURRENCIES = sorted([*SERIES, "ZAR"])


class _SeriesFailed(Exception):
    """One currency's series could not be read: that currency is skipped, the others go on."""


@register_provider(FXProviderRegistry)
class SARBProvider(FXRateProvider):
    """
    South African Reserve Bank FX rate provider.

    Provides the daily weighted average of the banks' rates at about 10:30 SAST with ZAR as base currency, in the
    direction of each series («Rand per X» or «X per Rand»). Data source: the SARB web indicators API, one request per
    currency.

    Coverage: a fixed table of 25 currencies plus ZAR.
    Update frequency: every South African business day, after about 10:30 SAST.
    """

    #: The first day asked: a later start than the series' own, so that 25 currencies fit the core's 120 s.
    FIRST_DAY = date(2010, 1, 1)
    #: Pause between two requests of one call (D9: an explicit, slow pace).
    PAUSE_SECONDS = 0.3

    @property
    def code(self) -> str:
        return "SARB"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "South African Reserve Bank"

    @property
    def icon(self) -> str | None:
        return "https://www.resbank.co.za/favicon.ico"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/sarb/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "South African Reserve Bank — daily exchange rates of 25 currencies against ZAR, among them BWP, KES, MWK, MZN and ZMW of southern and eastern Africa. Updated every South African business day after 10:30 SAST, history from 2010. Source: South African Reserve Bank.",
            "it": "South African Reserve Bank — tassi di cambio giornalieri di 25 valute contro ZAR, tra cui BWP, KES, MWK, MZN e ZMW dell'Africa australe e orientale. Aggiornamento ogni giorno lavorativo sudafricano dopo le 10:30 SAST, storia dal 2010. Fonte: South African Reserve Bank.",
            "fr": "South African Reserve Bank — taux de change quotidiens de 25 devises contre ZAR, dont BWP, KES, MWK, MZN et ZMW d'Afrique australe et orientale. Mise à jour chaque jour ouvrable sud-africain après 10h30 SAST, historique depuis 2010. Source : South African Reserve Bank.",
            "es": "South African Reserve Bank — tipos de cambio diarios de 25 monedas contra ZAR, entre ellas BWP, KES, MWK, MZN y ZMW del sur y el este de África. Actualizado cada día hábil sudafricano después de las 10:30 SAST, historial desde 2010. Fuente: South African Reserve Bank.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "SARB rates are the weighted average of the banks' rates at about 10:30 South African time, one per South African business day. Except USD, GBP and EUR, the bank publishes units of the currency per rand with four decimals, so small values are rounded: CHF (0.0488 per rand) by up to about 0.1%, CAD and AUD by about 0.06%. History from 2010. The RUB rate is the one the SARB publishes (roubles per rand), not the Central Bank of Russia's.",
            "it": "I tassi della SARB sono la media ponderata dei tassi delle banche verso le 10:30 ora sudafricana, uno per giorno lavorativo sudafricano. Tranne USD, GBP ed EUR, la banca pubblica le unità di valuta per un rand con quattro decimali, quindi i valori piccoli sono arrotondati: CHF (0,0488 per rand) fino a circa lo 0,1%, CAD e AUD di circa lo 0,06%. Storia dal 2010. Il tasso del RUB è quello pubblicato dalla SARB (rubli per rand), non quello della Banca centrale russa.",
            "fr": "Les taux de la SARB sont la moyenne pondérée des taux des banques vers 10h30 heure sud-africaine, un par jour ouvrable sud-africain. Sauf pour USD, GBP et EUR, la banque publie les unités de devise par rand avec quatre décimales : les petites valeurs sont arrondies, le CHF (0,0488 par rand) jusqu'à environ 0,1 %, le CAD et l'AUD d'environ 0,06 %. Historique depuis 2010. Le taux du RUB est celui que publie la SARB (roubles par rand), pas celui de la Banque centrale de Russie.",
            "es": "Los tipos de la SARB son la media ponderada de los tipos de los bancos hacia las 10:30 hora sudafricana, uno por día hábil sudafricano. Salvo USD, GBP y EUR, el banco publica las unidades de moneda por rand con cuatro decimales, así que los valores pequeños están redondeados: el CHF (0,0488 por rand) hasta un 0,1 % aproximadamente, el CAD y el AUD alrededor de un 0,06 %. Historial desde 2010. El tipo del RUB es el que publica la SARB (rublos por rand), no el del Banco Central de Rusia.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # A data limit that can mislead (the rounding of the «X per Rand» series), as BOC's: warning (lane 75)
        return "warning"

    @property
    def base_currency(self) -> str:
        return "ZAR"

    @property
    def test_currencies(self) -> list[str]:
        return ["ZAR", "USD", "EUR", "GBP", "JPY", "BWP"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(_CURRENCIES)

    async def get_supported_currencies(self) -> list[str]:
        """The fixed table, plus ZAR: no request (the direction of each series is fixed in the table anyway)."""
        return list(_CURRENCIES)

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch each asked currency's series, one request per currency, in series with a pause. A «Rand per X» series
        gives ``(day, CUR, 'ZAR', ZAR per 1 CUR)``, a «X per Rand» one ``(day, 'ZAR', CUR, CUR per 1 ZAR)``.

        Every value keeps its day (D2). A row that is no positive number loses its day only (X-R50). A currency whose
        series fails is skipped with a warning (XRL-H09); a call where every series failed is an ``FXServiceError``.

        Raises:
            ValueError: base_currency is neither None nor ZAR
            FXRateLimitedError: the bank refused for too many requests (no further currency is asked)
            FXServiceError: every asked series failed
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"SARB provider only supports ZAR as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = self.FIRST_DAY if start_date == "min" else max(start_date, self.FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        wanted = [currency for currency in asked if currency in SERIES]
        if not wanted or request_start > end_date:
            return results

        failures: list[str] = []
        for index, currency in enumerate(wanted):
            if index:
                await asyncio.sleep(self.PAUSE_SECONDS)
            try:
                results[currency] = await self._fetch_one(currency, request_start, end_date)
            except _SeriesFailed as failed:
                logger.warning(f"SARB fetch failed for {currency}, skipping: {failed}")
                failures.append(f"{currency}: {failed}")
        if len(failures) == len(wanted):
            raise FXServiceError(f"SARB API error for every asked series: {'; '.join(failures)}")
        return results

    async def _fetch_one(self, currency: str, start: date, end: date) -> list[tuple[date, str, str, Decimal]]:
        """One currency's rows, oldest first; ``_SeriesFailed`` when its answer is not the series' JSON list."""
        series_code, rand_per_unit = SERIES[currency]
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(f"{SERIES_URL}/{series_code}/{start.isoformat()}/{end.isoformat()}", headers={"Accept": "application/json"})
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            raise _SeriesFailed(f"request failed: {e}") from e

        body = response.text
        if body.lstrip()[:1] == "<":
            raise _SeriesFailed("the answer is an HTML page, not the series JSON (endpoint changed or request refused)")
        try:
            rows = json.loads(body, parse_float=Decimal)
        except ValueError:
            raise _SeriesFailed(f"the answer is not JSON: first bytes {body.lstrip()[:40]!r}") from None
        if not isinstance(rows, list):
            raise _SeriesFailed("the answer is not a JSON list (endpoint changed)")

        observations: list[tuple[date, str, str, Decimal]] = []
        for row in rows:
            day, value = self._day(row), self._value(row)
            if day is None or value is None or not start <= day <= end:
                continue
            observations.append((day, currency, self.base_currency, value) if rand_per_unit else (day, self.base_currency, currency, value))
        observations.sort(key=lambda observation: observation[0])
        return observations

    @staticmethod
    def _day(row: object) -> date | None:
        """``{"Period": "2026-11-19T00:00:00"}`` as a date, or None."""
        try:
            return datetime.fromisoformat(row["Period"]).date()  # type: ignore[index]
        except (TypeError, KeyError, ValueError):
            logger.debug(f"SARB: skipping a row with no readable day: {row!r}")
            return None

    @staticmethod
    def _value(row: object) -> Decimal | None:
        """``{"Value": 17.2532}`` (read as ``Decimal``) as a positive ``Decimal``, or None."""
        value = row.get("Value") if isinstance(row, dict) else None
        if isinstance(value, bool) or not isinstance(value, Decimal | int):
            return None
        try:
            number = Decimal(value)
        except InvalidOperation:
            return None
        return number if number.is_finite() and number > 0 else None
