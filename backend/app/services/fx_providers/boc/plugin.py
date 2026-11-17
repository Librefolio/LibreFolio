"""
Bank of Canada (BOC) FX rate provider.

This provider fetches the daily average exchange rates of the Bank of Canada from its Valet API. Every series
``FX<CUR>CAD`` is «CAD per 1 unit of the foreign currency»: CAD is the base of the provider.

API documentation: https://www.bankofcanada.ca/valet/docs
Terms: https://www.bankofcanada.ca/terms/ (linked in every Valet answer) — reuse with attribution to the Bank of Canada;
the bank calls these rates indicative, not a benchmark for transactions, and asks not to work around the limits it
imposes on Valet requests. robots.txt (16/11/2026): nothing disallowed under ``/valet/``.

Measured on 16/11/2026:

- ``valet/observations/group/FX_RATES_DAILY/json?start_date=…&end_date=…`` answers every series of the group in one
  JSON: ``observations`` holds one object per Canadian business day, ``{"d": "YYYY-MM-DD", "FX<CUR>CAD": {"v": "…"}}``,
  values as strings. The whole history (2017-01-03 onward, 24 live series) is ~4 MB in ~1.6 s.
- The group starts on 2017-01-03. The noon rates before it are the ``LEGACY_NOON_RATES`` group, another methodology:
  never mixed in (``FIRST_DAY``).
- A weekend range answers 200 with no observation. A request naming one unknown series is HTTP 404 for all the series
  asked, so the provider always asks the group and picks the series it needs. A malformed date is HTTP 400.
- ``…/group/FX_RATES_DAILY/json?recent=1`` gives each series' last observation: 24 live, VND (2019-12-31), RUB and SAR
  (2026-04-30) closed.
- The bank publishes few decimals for small units: IDR 0.000079 (two significant digits), KRW 0.001056.
"""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)


@register_provider(FXProviderRegistry)
class BOCProvider(FXRateProvider):
    """
    Bank of Canada FX rate provider.

    Provides daily average exchange rates with CAD as base currency (CAD per unit of each foreign currency).
    Data source: Bank of Canada Valet API, group ``FX_RATES_DAILY``, one request for every currency.

    Coverage: discovered from the API at runtime (24 currencies plus CAD on 2026-11-16).
    Update frequency: daily, Canadian business days, by 16:30 ET.
    """

    GROUP_URL = "https://www.bankofcanada.ca/valet/observations/group/FX_RATES_DAILY/json"
    #: The first day of the ``FX_RATES_DAILY`` group; earlier noon rates are another series.
    FIRST_DAY = date(2017, 1, 3)
    #: A series whose last value is older than this, counted from the newest value of the catalogue, is closed.
    CLOSED_AFTER = timedelta(days=31)

    # What the catalogue returned on 2026-11-16 (the closed VND, RUB and SAR left out), plus CAD. Listed while the first
    # discovery after a restart is slow or fails; the live list replaces it as soon as one arrives.
    FALLBACK_CURRENCIES = (
        "AUD",
        "BRL",
        "CAD",
        "CHF",
        "CNY",
        "EUR",
        "GBP",
        "HKD",
        "IDR",
        "INR",
        "JPY",
        "KRW",
        "MXN",
        "MYR",
        "NOK",
        "NZD",
        "PEN",
        "PLN",
        "SEK",
        "SGD",
        "THB",
        "TRY",
        "TWD",
        "USD",
        "ZAR",
    )

    @property
    def code(self) -> str:
        return "BOC"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Bank of Canada"

    @property
    def icon(self) -> str | None:
        return "https://www.bankofcanada.ca/wp-content/themes/ews-build-2024/img/favicon/favicon-32x32.png"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/boc/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Bank of Canada — daily average exchange rates of about 24 currencies against CAD, among them PEN, MXN, BRL, INR and TWD. Updated every Canadian business day by 16:30 ET, history from 2017. Source: Bank of Canada.",
            "it": "Bank of Canada — tassi di cambio medi giornalieri di circa 24 valute contro CAD, tra cui PEN, MXN, BRL, INR e TWD. Aggiornamento ogni giorno lavorativo canadese entro le 16:30 ET, storia dal 2017. Fonte: Bank of Canada.",
            "fr": "Banque du Canada — taux de change moyens quotidiens d'environ 24 devises contre CAD, dont PEN, MXN, BRL, INR et TWD. Mise à jour chaque jour ouvrable canadien avant 16h30 HE, historique depuis 2017. Source : Banque du Canada.",
            "es": "Banco de Canadá — tipos de cambio medios diarios de unas 24 monedas contra CAD, entre ellas PEN, MXN, BRL, INR y TWD. Actualizado cada día hábil canadiense antes de las 16:30 ET, historial desde 2017. Fuente: Banco de Canadá.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "Bank of Canada rates are indicative daily averages, one per Canadian business day: none at weekends and on Canadian holidays. IDR and KRW are published with few digits (IDR 0.000079 CAD), so their BOC rates are rounded, by up to about 1% for IDR.",
            "it": "I tassi della Bank of Canada sono medie giornaliere indicative, una per giorno lavorativo canadese: nessuna nei weekend e nelle festività canadesi. IDR e KRW sono pubblicate con poche cifre (IDR 0,000079 CAD), quindi i loro tassi BOC sono arrotondati, fino a circa l'1% per IDR.",
            "fr": "Les taux de la Banque du Canada sont des moyennes quotidiennes indicatives, une par jour ouvrable canadien : aucune le week-end ni les jours fériés canadiens. IDR et KRW sont publiées avec peu de chiffres (IDR 0,000079 CAD) : leurs taux BOC sont arrondis, jusqu'à environ 1 % pour IDR.",
            "es": "Los tipos del Banco de Canadá son medias diarias indicativas, una por día hábil canadiense: ninguna los fines de semana ni en los festivos canadienses. IDR y KRW se publican con pocas cifras (IDR 0,000079 CAD), así que sus tipos BOC están redondeados, hasta un 1 % aproximadamente para IDR.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # A data limit that can mislead (the rounding of IDR and KRW), not only a fact worth knowing: warning (lane 75)
        return "warning"

    @property
    def base_currency(self) -> str:
        return "CAD"

    @property
    def test_currencies(self) -> list[str]:
        return ["CAD", "USD", "EUR", "GBP", "JPY", "MXN"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(self.FALLBACK_CURRENCIES)

    async def get_supported_currencies(self) -> list[str]:
        """
        The live currencies of the group (each series' last observation, ``recent=1``), plus CAD.

        A series whose last value is more than ``CLOSED_AFTER`` older than the newest value of the answer is closed
        (VND, RUB, SAR on 2026-11-16).
        """
        observations = await self._get_observations({"recent": "1"})
        last_day: dict[str, date] = {}
        for observation in observations:
            day = self._day(observation)
            if day is None:
                continue
            for currency in self._currencies(observation):
                last_day[currency] = max(day, last_day.get(currency, day))
        if not last_day:
            raise FXServiceError("Bank of Canada catalogue lists no currency")
        newest = max(last_day.values())
        live = {currency for currency, day in last_day.items() if newest - day <= self.CLOSED_AFTER}
        return sorted(live | {self.base_currency})

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch the rates of every asked currency in one request on the group: ``(day, CUR, 'CAD', CAD per 1 CUR)``.

        Every value keeps the day the bank gives it (D2). A value that is no number loses its day only (X-R50). The call
        is one request for every currency, so an answer that is not the group's JSON is one ``FXServiceError``.

        Raises:
            ValueError: base_currency is neither None nor CAD
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: the request failed, or the answer is not the group's JSON
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"Bank of Canada provider only supports CAD as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = self.FIRST_DAY if start_date == "min" else max(start_date, self.FIRST_DAY)
        wanted = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in wanted}
        if not wanted or request_start > end_date:
            return results

        observations = await self._get_observations({"start_date": request_start.isoformat(), "end_date": end_date.isoformat()})
        for observation in observations:
            day = self._day(observation)
            if day is None:
                continue
            for currency in wanted:
                value = self._value(observation.get(f"FX{currency}CAD"))
                if value is None:
                    if f"FX{currency}CAD" in observation:
                        logger.debug(f"BOC: skipping a value that is no rate for {currency} on {day}: {observation[f'FX{currency}CAD']!r}")
                    continue
                results[currency].append((day, currency, self.base_currency, value))
        return results

    @staticmethod
    def _day(observation: object) -> date | None:
        try:
            return date.fromisoformat(observation["d"])  # type: ignore[index]
        except (TypeError, KeyError, ValueError):
            logger.debug(f"BOC: skipping an observation with no readable day: {observation!r}")
            return None

    @staticmethod
    def _currencies(observation: dict) -> list[str]:
        """The currencies of an observation's ``FX<CUR>CAD`` keys."""
        return [key[2:5] for key in observation if len(key) == 8 and key.startswith("FX") and key.endswith("CAD")]

    @staticmethod
    def _value(cell: object) -> Decimal | None:
        """``{"v": "1.4181"}`` as ``Decimal``, or None when it is missing or no positive number."""
        if not isinstance(cell, dict):
            return None
        try:
            value = Decimal(str(cell.get("v")))
        except InvalidOperation:
            return None
        return value if value.is_finite() and value > 0 else None

    async def _get_observations(self, params: dict[str, str]) -> list[dict]:
        """GET the group with ``params`` and return its ``observations``; anything else is an ``FXServiceError``."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(self.GROUP_URL, params=params)
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            logger.warning(f"Bank of Canada request failed: {e}")
            raise FXServiceError(f"Bank of Canada API error: {e}") from e

        body = response.text
        if body.lstrip()[:1] == "<":
            raise FXServiceError("Bank of Canada answer is an HTML page, not the Valet JSON (endpoint changed or request refused)")
        try:
            data = response.json()
        except ValueError:
            raise FXServiceError(f"Bank of Canada answer is not JSON: first bytes {body.lstrip()[:40]!r}") from None
        observations = data.get("observations") if isinstance(data, dict) else None
        if not isinstance(observations, list):
            raise FXServiceError("Bank of Canada answer has no observations list (endpoint changed)")
        return [observation for observation in observations if isinstance(observation, dict)]
