"""
Central Bank of the Republic of China (Taiwan) (CBC) FX rate provider.

This provider reads the open data of Taiwan's central bank: the interbank closing rate of the New Taiwan dollar against
the US dollar, TWD per 1 USD (source of the rate: Taipei Forex Inc.). TWD is the base of the provider; USD is its only
currency.

Dataset: «銀行間市場新臺幣對美元收盤匯率», https://data.gov.tw/dataset/7232, daily file
``https://cpx.cbc.gov.tw/api/OpenData/FTDOpenData_Day``. Licence: Open Government Data License, version 1
(政府資料開放授權條款-第1版, https://data.gov.tw/license), an open licence with attribution. The description names the
source.

Measured on 19/11/2026:

- One GET with no parameter answers the whole series, oldest first: 4 691 rows from 20080102 to the day itself, ~190 KB
  in ~2 s, ``[{"日期": "20261119", "NTD_USD": "32.942"}, …]`` (``日期`` = date, ``yyyyMMdd``; the value a string). No
  duplicate day, every value numeric. The endpoint has no date filter: the provider keeps the asked days itself.
- The rate of the day is published between 16:00 and 17:00 Taiwan time (UTC+8) on every business day (the note of
  https://www.cbc.gov.tw/tw/lp-645-1.html); it was there on the day itself.
- The CBC's 18-currency table against USD (``BP01D01``) is left out: it arrives about two weeks late, and BDI publishes
  those currencies every day.
- Budget: 1 request for 14 days and 1 for ``"min"``.
"""

from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

DATA_URL = "https://cpx.cbc.gov.tw/api/OpenData/FTDOpenData_Day"
#: The first day of the series.
FIRST_DAY = date(2008, 1, 2)
#: The key of the day in each row («date»).
_DAY_KEY = "日期"
_VALUE_KEY = "NTD_USD"


@register_provider(FXProviderRegistry)
class CBCProvider(FXRateProvider):
    """
    Central Bank of the Republic of China (Taiwan) FX rate provider.

    Provides the interbank closing rate of the US dollar with TWD as base currency (TWD per 1 USD).
    Data source: the CBC open data, one request for the whole series.

    Coverage: USD.
    Update frequency: every Taiwanese business day, between 16:00 and 17:00 Taiwan time.
    """

    @property
    def code(self) -> str:
        return "CBC"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Central Bank of the Republic of China (Taiwan)"

    @property
    def icon(self) -> str | None:
        return "https://cpx.cbc.gov.tw/favicon.ico"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/cbc/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Central Bank of the Republic of China (Taiwan) — the interbank closing rate of the US dollar against the New Taiwan dollar (TWD), the same day, every Taiwanese business day, history from 2008. Source: Central Bank of the Republic of China (Taiwan), Open Government Data License.",
            "it": "Banca centrale della Repubblica di Cina (Taiwan) — il tasso di chiusura interbancario del dollaro USA contro il nuovo dollaro taiwanese (TWD), in giornata, ogni giorno lavorativo di Taiwan, storia dal 2008. Fonte: Central Bank of the Republic of China (Taiwan), Open Government Data License.",
            "fr": "Banque centrale de la République de Chine (Taïwan) — le taux de clôture interbancaire du dollar américain contre le nouveau dollar de Taïwan (TWD), le jour même, chaque jour ouvrable taïwanais, historique depuis 2008. Source : Central Bank of the Republic of China (Taiwan), Open Government Data License.",
            "es": "Banco Central de la República de China (Taiwán) — el tipo de cierre interbancario del dólar estadounidense contra el nuevo dólar taiwanés (TWD), el mismo día, cada día hábil de Taiwán, historial desde 2008. Fuente: Central Bank of the Republic of China (Taiwan), Open Government Data License.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "The CBC publishes the interbank closing rate of the US dollar (source: Taipei Forex Inc.) between 16:00 and 17:00 Taiwan time, one per Taiwanese business day: none at weekends and on Taiwanese holidays. Only USD: the CBC's table of other currencies arrives about two weeks late and is left out.",
            "it": "La CBC pubblica il tasso di chiusura interbancario del dollaro USA (fonte: Taipei Forex Inc.) tra le 16:00 e le 17:00 ora di Taiwan, uno per giorno lavorativo di Taiwan: nessuno nei weekend e nelle festività di Taiwan. Solo USD: la tabella delle altre valute della CBC arriva con circa due settimane di ritardo e resta fuori.",
            "fr": "La CBC publie le taux de clôture interbancaire du dollar américain (source : Taipei Forex Inc.) entre 16h00 et 17h00 heure de Taïwan, un par jour ouvrable taïwanais : aucun le week-end ni les jours fériés taïwanais. Seulement USD : le tableau des autres devises de la CBC arrive avec environ deux semaines de retard et est écarté.",
            "es": "El CBC publica el tipo de cierre interbancario del dólar estadounidense (fuente: Taipei Forex Inc.) entre las 16:00 y las 17:00 hora de Taiwán, uno por día hábil de Taiwán: ninguno los fines de semana ni en los festivos de Taiwán. Solo USD: la tabla de otras monedas del CBC llega con unas dos semanas de retraso y queda fuera.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # Facts worth knowing (which rate, when, USD only), not a data limit that misleads: info (lane 75)
        return "info"

    @property
    def base_currency(self) -> str:
        return "TWD"

    @property
    def test_currencies(self) -> list[str]:
        return ["TWD", "USD"]

    @property
    def fallback_currencies(self) -> list[str]:
        return ["TWD", "USD"]

    async def get_supported_currencies(self) -> list[str]:
        """TWD and USD: one series, no request."""
        return ["TWD", "USD"]

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch the whole series and keep the asked days: ``(day, 'USD', 'TWD', TWD per 1 USD)``.

        Every value keeps its day (D2). A row that is unreadable loses its day only (X-R50); a day listed twice is
        skipped with a warning, never picked at random. Another asked currency answers an empty list.

        Raises:
            ValueError: base_currency is neither None nor TWD
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: the request failed, or the answer is not a JSON list
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"CBC provider only supports TWD as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        if "USD" not in results or request_start > end_date:
            return results

        readable = []
        for row in await self._get_rows():
            day, value = self._day(row), self._value(row)
            if day is not None and value is not None and request_start <= day <= end_date:
                readable.append((day, value))
        repeated = {day for day, count in Counter(day for day, _ in readable).items() if count > 1}
        if repeated:
            logger.warning(f"CBC: {len(repeated)} days listed more than once are skipped: {sorted(repeated)[:5]}")
        results["USD"] = sorted((day, "USD", self.base_currency, value) for day, value in readable if day not in repeated)
        return results

    @staticmethod
    def _day(row: object) -> date | None:
        """``{"日期": "20261119"}`` as a date, or None."""
        try:
            return datetime.strptime(str(row[_DAY_KEY]), "%Y%m%d").date()  # type: ignore[index]
        except (TypeError, KeyError, ValueError):
            logger.debug(f"CBC: skipping a row with no readable day: {row!r}")
            return None

    @staticmethod
    def _value(row: object) -> Decimal | None:
        """``{"NTD_USD": "32.942"}`` as ``Decimal``, or None when missing or no positive number."""
        text = row.get(_VALUE_KEY) if isinstance(row, dict) else None
        if text is None:
            return None
        try:
            value = Decimal(str(text).strip())
        except InvalidOperation:
            return None
        return value if value.is_finite() and value > 0 else None

    async def _get_rows(self) -> list:
        """GET the whole series; anything that is not a JSON list is an ``FXServiceError``."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(DATA_URL, headers={"Accept": "application/json"})
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            logger.warning(f"CBC request failed: {e}")
            raise FXServiceError(f"CBC open data API error: {e}") from e

        body = response.text
        if body.lstrip()[:1] == "<":
            raise FXServiceError("CBC answer is an HTML page, not the open-data JSON (endpoint changed or request refused)")
        try:
            rows = response.json()
        except ValueError:
            raise FXServiceError(f"CBC answer is not JSON: first bytes {body.lstrip()[:40]!r}") from None
        if not isinstance(rows, list):
            raise FXServiceError("CBC answer is not a JSON list (endpoint changed)")
        return rows
