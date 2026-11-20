"""
TRM (Colombia) FX rate provider.

This provider reads the TRM, «Tasa de Cambio Representativa del Mercado», Colombia's official exchange rate of the US
dollar: COP per 1 USD. The Superintendencia Financiera de Colombia (SFC) computes and certifies it with the Banco de la
República's methodology, from the spot trades of the previous banking day. COP is the base of the provider; USD is its
only currency.

Source: the open-data portal datos.gov.co, Socrata dataset ``32sa-8pi3`` «Tasa de Cambio Representativa del Mercado -
TRM» (https://www.datos.gov.co/Econom-a-y-Finanzas/Tasa-de-Cambio-Representativa-del-Mercado-TRM/32sa-8pi3).
Licence: Creative Commons Attribution-ShareAlike 4.0 International (the dataset's metadata), attribution to the
«Superintendencia Financiera de Colombia». LibreFolio stores the values for the instance's owner and redistributes no
dataset; the description names the source.

Measured on 19/11/2026:

- ``GET …/resource/32sa-8pi3.json`` with ``$where``, ``$order`` and ``$limit=50000`` answers the whole dataset in one
  request: 8 389 rows from 1991-12-02, ~1 MB, ~3.9 s. Fields: ``valor`` (a number as text), ``unidad`` (always COP),
  ``vigenciadesde`` and ``vigenciahasta`` (floating timestamps).
- **A row is valid over an interval**: 1 947 rows span several days (a weekend and the holidays around it take the TRM
  computed on the banking day before). No gap and no overlap between rows. Decision D2 (lane 75): the provider returns
  one value for **every day** of the interval, because the SFC says the TRM is valid on those days.
- The TRM valid tomorrow is published today: a day after the asked end is never returned (and the core discards future
  days anyway).
- No app token: requests go to Socrata's shared pool, whose limits are not documented. Budget: 1 request for 14 days and
  1 for ``"min"`` (``$offset`` pages beyond 50 000 rows, which the dataset will not reach for a century).
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

DATASET_URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"
#: The first day of the dataset.
FIRST_DAY = date(1991, 12, 2)
#: Rows per request; a full page asks the next one with ``$offset``.
PAGE_SIZE = 50000


@register_provider(FXProviderRegistry)
class TRMProvider(FXRateProvider):
    """
    TRM (Colombia) FX rate provider.

    Provides Colombia's official exchange rate of the US dollar, certified by the Superintendencia Financiera de
    Colombia, with COP as base currency (COP per 1 USD), on every day it is valid. Data source: datos.gov.co.

    Coverage: USD.
    Update frequency: every Colombian banking day, the day before the TRM is valid.
    """

    @property
    def code(self) -> str:
        return "TRM"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "TRM Colombia (Superintendencia Financiera)"

    @property
    def icon(self) -> str | None:
        return "https://www.superfinanciera.gov.co/info/superfinancierav8/web/portal/img/favicon.png"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/trm/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "TRM — Colombia's official exchange rate of the US dollar against the Colombian peso (COP), certified by the Superintendencia Financiera de Colombia, for every day, history from 1991. Source: Superintendencia Financiera de Colombia (datos.gov.co, CC BY-SA 4.0).",
            "it": "TRM — il tasso di cambio ufficiale della Colombia per il dollaro USA contro il peso colombiano (COP), certificato dalla Superintendencia Financiera de Colombia, per ogni giorno, storia dal 1991. Fonte: Superintendencia Financiera de Colombia (datos.gov.co, CC BY-SA 4.0).",
            "fr": "TRM — le taux de change officiel de la Colombie pour le dollar américain contre le peso colombien (COP), certifié par la Superintendencia Financiera de Colombia, pour chaque jour, historique depuis 1991. Source : Superintendencia Financiera de Colombia (datos.gov.co, CC BY-SA 4.0).",
            "es": "TRM — la Tasa de Cambio Representativa del Mercado del dólar estadounidense contra el peso colombiano (COP), certificada por la Superintendencia Financiera de Colombia, para cada día, historial desde 1991. Fuente: Superintendencia Financiera de Colombia (datos.gov.co, CC BY-SA 4.0).",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "The TRM valid on a day is computed from the spot trades of the previous Colombian banking day and published the day before. Weekends and holidays carry the TRM the Superintendencia declares valid for them, so every day has a value, and that value is one already known on the last banking day. Only USD.",
            "it": "La TRM valida in un giorno è calcolata sulle operazioni a pronti del giorno bancario colombiano precedente e pubblicata il giorno prima. Weekend e festivi hanno la TRM che la Superintendencia dichiara valida per loro, quindi ogni giorno ha un valore, ed è un valore già noto l'ultimo giorno bancario. Solo USD.",
            "fr": "La TRM valable un jour est calculée sur les opérations au comptant du jour bancaire colombien précédent et publiée la veille. Les week-ends et jours fériés ont la TRM que la Superintendencia déclare valable pour eux : chaque jour a une valeur, déjà connue le dernier jour bancaire. Seulement USD.",
            "es": "La TRM vigente en un día se calcula con las operaciones de contado del día bancario colombiano anterior y se publica el día antes. Los fines de semana y festivos tienen la TRM que la Superintendencia declara vigente para ellos, así que cada día tiene un valor, ya conocido el último día bancario. Solo USD.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # Facts worth knowing (D-1 computation, values on non-banking days), not a data limit that misleads: info
        return "info"

    @property
    def base_currency(self) -> str:
        return "COP"

    @property
    def test_currencies(self) -> list[str]:
        return ["COP", "USD"]

    @property
    def fallback_currencies(self) -> list[str]:
        return ["COP", "USD"]

    async def get_supported_currencies(self) -> list[str]:
        """COP and USD: one dataset, no request."""
        return ["COP", "USD"]

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch the TRM rows that overlap the range: ``(day, 'USD', 'COP', COP per 1 USD)`` for every day of each row's
        validity inside the range (D2).

        A row that is unreadable is skipped (X-R50). A day two rows both claim is dropped with a warning, never picked
        at random. Another asked currency answers an empty list.

        Raises:
            ValueError: base_currency is neither None nor COP
            FXRateLimitedError: the portal refused for too many requests
            FXServiceError: the request failed, or the answer is not a JSON list
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"TRM provider only supports COP as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        if "USD" not in results or request_start > end_date:
            return results

        by_day: dict[date, list[Decimal]] = defaultdict(list)
        for row in await self._get_rows(request_start, end_date):
            interval = self._interval(row)
            value = self._value(row)
            if interval is None or value is None:
                continue
            first, last = max(interval[0], request_start), min(interval[1], end_date)
            day = first
            while day <= last:
                by_day[day].append(value)
                day += timedelta(days=1)

        observations = []
        for day in sorted(by_day):
            values = by_day[day]
            if len(values) > 1:
                logger.warning(f"TRM: {len(values)} rows are valid on {day}: the day is skipped")
                continue
            observations.append((day, "USD", self.base_currency, values[0]))
        results["USD"] = observations
        return results

    @staticmethod
    def _interval(row: object) -> tuple[date, date] | None:
        """``vigenciadesde`` … ``vigenciahasta`` as two dates, or None when unreadable or reversed."""
        try:
            first = datetime.fromisoformat(str(row["vigenciadesde"])).date()  # type: ignore[index]
            last = datetime.fromisoformat(str(row["vigenciahasta"])).date()  # type: ignore[index]
        except (TypeError, KeyError, ValueError):
            logger.debug(f"TRM: skipping a row with no readable validity: {row!r}")
            return None
        return (first, last) if first <= last else None

    @staticmethod
    def _value(row: object) -> Decimal | None:
        """``{"valor": "3316.7", "unidad": "COP"}`` as ``Decimal``; None for another unit or no positive number."""
        if not isinstance(row, dict) or row.get("unidad") != "COP":
            return None
        try:
            value = Decimal(str(row.get("valor")).strip())
        except InvalidOperation:
            return None
        return value if value.is_finite() and value > 0 else None

    async def _get_rows(self, start: date, end: date) -> list:
        """Every row whose validity overlaps [start, end], page after page; anything else is an ``FXServiceError``."""
        rows: list = []
        offset = 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                params = {
                    "$where": f"vigenciahasta >= '{start.isoformat()}T00:00:00' AND vigenciadesde <= '{end.isoformat()}T00:00:00'",
                    "$order": "vigenciadesde",
                    "$limit": str(PAGE_SIZE),
                    "$offset": str(offset),
                }
                page = await self._get_page(client, params)
                rows.extend(page)
                if len(page) < PAGE_SIZE:
                    return rows
                offset += PAGE_SIZE

    async def _get_page(self, client: httpx.AsyncClient, params: dict[str, str]) -> list:
        try:
            response = await client.get(DATASET_URL, params=params, headers={"Accept": "application/json"})
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            logger.warning(f"TRM request failed: {e}")
            raise FXServiceError(f"TRM (datos.gov.co) API error: {e}") from e

        body = response.text
        if body.lstrip()[:1] == "<":
            raise FXServiceError("TRM answer is an HTML page, not the dataset's JSON (endpoint changed or request refused)")
        try:
            page = response.json()
        except ValueError:
            raise FXServiceError(f"TRM answer is not JSON: first bytes {body.lstrip()[:40]!r}") from None
        if not isinstance(page, list):
            raise FXServiceError(f"TRM answer is not a JSON list (dataset changed, or the portal's error): {body.lstrip()[:80]!r}")
        return page
