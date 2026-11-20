"""
Banco Central de Reserva del Perú (BCRP) FX rate provider.

This provider reads one series of BCRPData, the statistics API of Peru's central bank: the interbank exchange rate of
the US dollar, sell side, «S/ por US$» (PEN per 1 USD). PEN is the base of the provider; USD is its only currency.

API documentation: https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/api
Terms: https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/condiciones-de-uso — the content «puede reproducirse
total o parcialmente, sin autorización expresa, siempre y cuando se cite la fuente». The description names the source.

Measured on 19/11/2026:

- ``…/api/PD04638PD/json/{yyyy-MM-dd}/{yyyy-MM-dd}`` answers JSON (sent as ``text/html``):
  ``{"config": {…, "series": [{"name": "Tipo de cambio - TC Interbancario (S/ por US$) - Venta"}]},
  "periods": [{"name": "10.Nov.26", "values": ["3.41621428571429"]}, …]}``, oldest first. The day is ``dd.Mmm.yy``
  with Spanish month abbreviations (``Ene`` … ``Set`` … ``Dic``); the value a string with many decimals (the day's
  average of the interbank sells), or ``"n.d."``.
- ``"n.d."``: Peruvian holidays (356 days since 1997) and the last days not published yet (17–19/11 on 19/11: one to
  three days late). Those days are skipped, never stored as zero; a later sync finds them.
- The series has values from 02.Ene.97 (``FIRST_DAY``); asked from 1990 it answers ``n.d.`` before.
- One request for the whole history: ~470 KB in ~4.4 s. Budget: 1 request for 14 days and 1 for ``"min"``.
- An unknown series answers an Incapsula (Imperva) HTML page with a challenge script: the site is behind a WAF. The
  provider never works around it: an HTML answer is an ``FXServiceError``.
- The BCRP's EUR series (``PD04648PD``) is left out: between 05 and 12/11/2026 it moved from 3.83 to 4.04 while USD
  × EUR/USD stayed at 3.77–3.79 (research, lane 75), a retail rate rather than a reference one.
"""

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

API_URL = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
#: «Tipo de cambio - TC Interbancario (S/ por US$) - Venta»: PEN per 1 USD.
USD_SERIES = "PD04638PD"
#: The first day with a value.
FIRST_DAY = date(1997, 1, 2)
#: The Spanish month abbreviations of the day names (``Set`` for September; ``Sep`` accepted too).
_MONTHS = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8, "Set": 9, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}
#: «No data»: a holiday or a day not published yet.
_NO_DATA = "n.d."


@register_provider(FXProviderRegistry)
class BCRPProvider(FXRateProvider):
    """
    Banco Central de Reserva del Perú FX rate provider.

    Provides the interbank exchange rate of the US dollar, sell side, with PEN as base currency (PEN per 1 USD).
    Data source: BCRPData, one request for the whole range.

    Coverage: USD.
    Update frequency: Peruvian business days, published with one to three days of delay.
    """

    @property
    def code(self) -> str:
        return "BCRP"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Banco Central de Reserva del Perú"

    @property
    def icon(self) -> str | None:
        return "https://estadisticas.bcrp.gob.pe/favicon.ico"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/bcrp/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Banco Central de Reserva del Perú — the interbank exchange rate of the US dollar against the Peruvian sol (PEN), sell side, every Peruvian business day, history from 1997. Source: BCRP (BCRPData).",
            "it": "Banco Central de Reserva del Perú — il tasso di cambio interbancario del dollaro USA contro il sol peruviano (PEN), lato vendita, ogni giorno lavorativo peruviano, storia dal 1997. Fonte: BCRP (BCRPData).",
            "fr": "Banco Central de Reserva del Perú — le taux de change interbancaire du dollar américain contre le sol péruvien (PEN), côté vente, chaque jour ouvrable péruvien, historique depuis 1997. Source : BCRP (BCRPData).",
            "es": "Banco Central de Reserva del Perú — el tipo de cambio interbancario del dólar estadounidense contra el sol peruano (PEN), venta, cada día hábil peruano, historial desde 1997. Fuente: BCRP (BCRPData).",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "BCRP publishes the interbank sell rate of the US dollar, the average of the day's interbank sells, one to three days late: the last days arrive at a later update. No rate on Peruvian holidays. Only USD: the bank's euro rate is not a reference rate and is left out.",
            "it": "Il BCRP pubblica il tasso interbancario di vendita del dollaro USA, la media delle vendite interbancarie del giorno, con uno-tre giorni di ritardo: gli ultimi giorni arrivano a un aggiornamento successivo. Nessun tasso nei festivi peruviani. Solo USD: il tasso dell'euro della banca non è un tasso di riferimento e resta fuori.",
            "fr": "La BCRP publie le taux interbancaire de vente du dollar américain, la moyenne des ventes interbancaires du jour, avec un à trois jours de retard : les derniers jours arrivent lors d'une mise à jour suivante. Aucun taux les jours fériés péruviens. Seulement USD : le taux de l'euro de la banque n'est pas un taux de référence et est écarté.",
            "es": "El BCRP publica el tipo interbancario de venta del dólar estadounidense, el promedio de las ventas interbancarias del día, con uno a tres días de retraso: los últimos días llegan en una actualización posterior. Sin tipo en los feriados peruanos. Solo USD: el tipo del euro del banco no es un tipo de referencia y queda fuera.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # Facts worth knowing (which rate, the delay, USD only), not a data limit that misleads: info (lane 75)
        return "info"

    @property
    def base_currency(self) -> str:
        return "PEN"

    @property
    def test_currencies(self) -> list[str]:
        return ["PEN", "USD"]

    @property
    def fallback_currencies(self) -> list[str]:
        return ["PEN", "USD"]

    async def get_supported_currencies(self) -> list[str]:
        """PEN and USD: one series, no request."""
        return ["PEN", "USD"]

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch the USD series in one request: ``(day, 'USD', 'PEN', PEN per 1 USD)``.

        Every value keeps its day (D2). «n.d.», or a value that is no positive number, loses its day only (X-R50).
        Another asked currency answers an empty list.

        Raises:
            ValueError: base_currency is neither None nor PEN
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: the request failed, or the answer is not the series JSON (an HTML page included)
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"BCRP provider only supports PEN as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        if "USD" not in results or request_start > end_date:
            return results

        observations = []
        for period in await self._get_periods(request_start, end_date):
            day, value = self._day(period), self._value(period)
            if day is None or value is None or not request_start <= day <= end_date:
                continue
            observations.append((day, "USD", self.base_currency, value))
        observations.sort(key=lambda observation: observation[0])
        results["USD"] = observations
        return results

    @staticmethod
    def _day(period: object) -> date | None:
        """``{"name": "02.Ene.97"}`` as a date (90–99 → the 1990s), or None."""
        try:
            day, month, year = str(period["name"]).split(".")  # type: ignore[index]
            short_year = int(year)
            if len(year) != 2:
                raise ValueError(year)
            return date(1900 + short_year if short_year >= 90 else 2000 + short_year, _MONTHS[month], int(day))
        except (TypeError, KeyError, ValueError):
            logger.debug(f"BCRP: skipping a period with no readable day: {period!r}")
            return None

    @staticmethod
    def _value(period: object) -> Decimal | None:
        """The period's first value as ``Decimal``; None for «n.d.» or anything that is no positive number."""
        values = period.get("values") if isinstance(period, dict) else None
        if not isinstance(values, list) or not values or not isinstance(values[0], str) or values[0].strip() == _NO_DATA:
            return None
        try:
            value = Decimal(values[0].strip())
        except InvalidOperation:
            return None
        return value if value.is_finite() and value > 0 else None

    async def _get_periods(self, start: date, end: date) -> list:
        """GET the USD series for the range and return its ``periods``; anything else is an ``FXServiceError``."""
        url = f"{API_URL}/{USD_SERIES}/json/{start.isoformat()}/{end.isoformat()}"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, headers={"Accept": "application/json"})
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            logger.warning(f"BCRP request failed: {e}")
            raise FXServiceError(f"BCRP API error: {e}") from e

        body = response.text
        if body.lstrip()[:1] == "<":
            raise FXServiceError("BCRP answer is an HTML page, not the BCRPData JSON (request blocked by the site's firewall, or endpoint changed)")
        try:
            data = json.loads(body)
        except ValueError:
            raise FXServiceError(f"BCRP answer is not JSON: first bytes {body.lstrip()[:40]!r}") from None
        periods = data.get("periods") if isinstance(data, dict) else None
        if not isinstance(periods, list):
            raise FXServiceError("BCRP answer has no periods list (endpoint changed)")
        return periods
