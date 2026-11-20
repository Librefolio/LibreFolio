"""
Czech National Bank (CNB) FX rate provider.

This provider reads the central bank exchange rate fixing of the Czech National Bank from its plain-text files: every
value is «CZK per ``Amount`` units» of a foreign currency. CZK is the base of the provider.

Page: https://www.cnb.cz/en/financial-markets/foreign-exchange-market/central-bank-exchange-rate-fixing/central-bank-exchange-rate-fixing/
Terms: https://www.cnb.cz/en/privacy-statement-and-disclaimer/disclaimer-copyright/index.html — «You may store,
distribute and reproduce all our Internet information»; «The CNB must always be stated as the source of the
information (Source: the CNB)». robots.txt (19/11/2026): nothing disallowed under these files.

Measured on 19/11/2026:

- ``year.txt?year=YYYY``: one file per year, from 1991. A header ``Date|1 AUD|100 HUF|1000 IDR|…`` (amount, space,
  code), then one row per fixing day, ``dd.mm.yyyy|v1|v2|…``, values with a dot. A year can hold several blocks with
  different columns (1993 has three headers: currencies entered and left). The current year's file ends with today's
  fixing, so no daily file is needed for the last day.
- ``year=1990`` (any year without a file) answers **the current year's file**, not an error: a row is kept only when
  its year is the asked one.
- ``daily.txt`` without a date is the last fixing: ``19 Nov 2026 #222``, a header ``Country|Currency|Amount|Code|Rate``,
  one row per currency (30 on 19/11/2026, XDR among them; BGN left at the end of 2025). The catalogue reads it.
- The fixing is declared every working day at around 2.30 p.m. (Prague) and is valid for that day and the following
  non-working days: the files list the fixing days only, and so does the provider (D2).
- Up to 1000 units with three decimals: IDR 1.218 CZK per 1000, so a step of about 0.08%.
- The «other currencies» (124, monthly) are left out: BDI publishes them daily.
- Budget: one request per year of the range, with ``PAUSE_SECONDS`` between two (D9): a 14-day sync is 1 request
  (2 across New Year), ``"min"`` 36 requests (~25 s).
"""

import asyncio
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

_FIXING_PAGE = "https://www.cnb.cz/en/financial-markets/foreign-exchange-market/central-bank-exchange-rate-fixing/central-bank-exchange-rate-fixing/"
#: The header of the rows of ``daily.txt``.
_DAILY_HEADER = "Country|Currency|Amount|Code|Rate"


@register_provider(FXProviderRegistry)
class CNBProvider(FXRateProvider):
    """
    Czech National Bank FX rate provider.

    Provides the central bank exchange rate fixing with CZK as base currency (CZK per unit of each foreign currency).
    Data source: the CNB yearly text files, one request per year of the range.

    Coverage: discovered from the last fixing at runtime (30 currencies plus CZK on 2026-11-19).
    Update frequency: every Czech working day, at around 2.30 p.m. Prague time.
    """

    YEAR_URL = f"{_FIXING_PAGE}year.txt"
    DAILY_URL = f"{_FIXING_PAGE}daily.txt"
    #: The first year with a file.
    FIRST_DAY = date(1991, 1, 1)
    #: Pause between two requests of one call (D9: an explicit, slow pace).
    PAUSE_SECONDS = 0.3

    # What the last fixing listed on 2026-11-19, plus CZK. Listed while the first discovery after a restart is slow or
    # fails; the live list replaces it as soon as one arrives.
    FALLBACK_CURRENCIES = (
        "AUD",
        "BRL",
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
        "MXN",
        "MYR",
        "NOK",
        "NZD",
        "PHP",
        "PLN",
        "RON",
        "SEK",
        "SGD",
        "THB",
        "TRY",
        "USD",
        "XDR",
        "ZAR",
    )

    @property
    def code(self) -> str:
        return "CNB"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Czech National Bank"

    @property
    def icon(self) -> str | None:
        return "https://www.cnb.cz/export/system/modules/org.opencms.apollo/resources/img/favicon_120.png"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/cnb/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Czech National Bank — the daily central bank fixing of about 30 currencies against CZK, among them HUF, PLN, RON, ILS and the SDR (XDR). Updated every Czech working day at around 2.30 p.m., history from 1991. Source: the CNB.",
            "it": "Banca nazionale ceca — il fixing giornaliero della banca centrale di circa 30 valute contro CZK, tra cui HUF, PLN, RON, ILS e il DSP (XDR). Aggiornamento ogni giorno lavorativo ceco verso le 14:30, storia dal 1991. Fonte: la CNB.",
            "fr": "Banque nationale tchèque — le fixing quotidien de la banque centrale d'environ 30 devises contre CZK, dont HUF, PLN, RON, ILS et le DTS (XDR). Mise à jour chaque jour ouvrable tchèque vers 14h30, historique depuis 1991. Source : la CNB.",
            "es": "Banco Nacional Checo — el fixing diario del banco central de unas 30 monedas contra CZK, entre ellas HUF, PLN, RON, ILS y el DEG (XDR). Actualizado cada día hábil checo hacia las 14:30, historial desde 1991. Fuente: el CNB.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "The CNB fixing is declared on Czech working days at around 2.30 p.m. and is valid until the next one: only fixing days are listed. Some currencies are quoted per 100 or 1000 units with three decimals (IDR 1.218 CZK per 1000), so their rates move in steps of up to about 0.1%. Before 8 February 1993 the rates are those of the Czechoslovak koruna, which the Czech koruna replaced at par.",
            "it": "Il fixing della CNB è dichiarato nei giorni lavorativi cechi verso le 14:30 e vale fino al successivo: compaiono solo i giorni di fixing. Alcune valute sono quotate per 100 o 1000 unità con tre decimali (IDR 1,218 CZK per 1000), quindi i loro tassi si muovono a passi fino a circa lo 0,1%. Prima dell'8 febbraio 1993 i tassi sono quelli della corona cecoslovacca, sostituita alla pari dalla corona ceca.",
            "fr": "Le fixing de la CNB est déclaré les jours ouvrables tchèques vers 14h30 et vaut jusqu'au suivant : seuls les jours de fixing figurent. Certaines devises sont cotées pour 100 ou 1000 unités avec trois décimales (IDR 1,218 CZK pour 1000) : leurs taux varient par pas allant jusqu'à environ 0,1 %. Avant le 8 février 1993, les taux sont ceux de la couronne tchécoslovaque, remplacée au pair par la couronne tchèque.",
            "es": "El fixing del CNB se declara los días hábiles checos hacia las 14:30 y vale hasta el siguiente: solo figuran los días de fixing. Algunas monedas cotizan por 100 o 1000 unidades con tres decimales (IDR 1,218 CZK por 1000), así que sus tipos se mueven en pasos de hasta un 0,1 % aproximadamente. Antes del 8 de febrero de 1993 los tipos son los de la corona checoslovaca, que la corona checa sustituyó a la par.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # Facts worth knowing (fixing days, units, the 1993 koruna at par), not a data limit that misleads: info
        return "info"

    @property
    def base_currency(self) -> str:
        return "CZK"

    @property
    def test_currencies(self) -> list[str]:
        return ["CZK", "USD", "EUR", "GBP", "JPY", "HUF"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(self.FALLBACK_CURRENCIES)

    async def get_supported_currencies(self) -> list[str]:
        """The codes of the last fixing (``daily.txt``), plus CZK."""
        text = await self._get_text(self.DAILY_URL, None, "the last fixing")
        lines = [line.strip() for line in text.splitlines()]
        if len(lines) < 2 or lines[1] != _DAILY_HEADER:
            raise FXServiceError("CNB daily fixing has no «Country|Currency|Amount|Code|Rate» header (format changed)")
        codes = {cells[3] for cells in (line.split("|") for line in lines[2:] if line) if len(cells) == 5 and len(cells[3]) == 3 and cells[3].isalpha()}
        if not codes:
            raise FXServiceError("CNB daily fixing lists no currency")
        return sorted(codes | {self.base_currency})

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch the asked currencies from one yearly file per year of the range: ``(day, CUR, 'CZK', CZK per 1 CUR)``.

        Every value keeps its fixing day (D2). A cell that is no positive number loses that currency's day only
        (X-R50). The years make one dataset: a year that fails fails the call, never a history with a silent hole.

        Raises:
            ValueError: base_currency is neither None nor CZK
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: a request failed, or an answer is not a yearly file
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"CNB provider only supports CZK as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = self.FIRST_DAY if start_date == "min" else max(start_date, self.FIRST_DAY)
        wanted = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in wanted}
        if not wanted or request_start > end_date:
            return results

        for index, year in enumerate(range(request_start.year, end_date.year + 1)):
            if index:
                await asyncio.sleep(self.PAUSE_SECONDS)
            text = await self._get_text(self.YEAR_URL, {"year": str(year)}, f"year {year}")
            for day, currency, value in self._read_year(text, year):
                if currency in results and request_start <= day <= end_date:
                    results[currency].append((day, currency, self.base_currency, value))
        return results

    @staticmethod
    def _read_year(text: str, year: int) -> list[tuple[date, str, Decimal]]:
        """The ``(day, CUR, CZK per 1 CUR)`` of a yearly file, block by block; rows of another year are skipped."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines or not lines[0].startswith("Date|"):
            first = lines[0][:40] if lines else ""
            raise FXServiceError(f"CNB answer for year {year} is not a yearly file: first line {first!r} (format changed)")
        observations: list[tuple[date, str, Decimal]] = []
        columns: list[tuple[str, Decimal] | None] = []
        other_year = 0
        for line in lines:
            cells = line.split("|")
            if cells[0] == "Date":
                columns = [CNBProvider._column(cell) for cell in cells[1:]]
                continue
            try:
                day = datetime.strptime(cells[0], "%d.%m.%Y").date()
            except ValueError:
                logger.debug(f"CNB: skipping a line with no readable day in year {year}: {line[:60]!r}")
                continue
            if day.year != year:
                other_year += 1
                continue
            for column, cell in zip(columns, cells[1:], strict=False):
                if column is None:
                    continue
                currency, amount = column
                value = CNBProvider._value(cell)
                if value is not None:
                    observations.append((day, currency, value / amount))
        if other_year:
            logger.warning(f"CNB: the file asked for {year} holds {other_year} rows of another year (no file for {year}?): skipped")
        return observations

    @staticmethod
    def _column(cell: str) -> tuple[str, Decimal] | None:
        """``"100 HUF"`` as ``("HUF", 100)``, or None for a column that is not «amount code»."""
        parts = cell.strip().split(" ")
        if len(parts) != 2 or not parts[0].isdigit() or int(parts[0]) <= 0 or len(parts[1]) != 3 or not parts[1].isalpha():
            logger.debug(f"CNB: ignoring a column that is not «amount code»: {cell!r}")
            return None
        return parts[1], Decimal(parts[0])

    @staticmethod
    def _value(cell: str) -> Decimal | None:
        """A cell as ``Decimal``, or None when it is empty or no positive number."""
        try:
            value = Decimal(cell.strip())
        except InvalidOperation:
            return None
        return value if value.is_finite() and value > 0 else None

    async def _get_text(self, url: str, params: dict[str, str] | None, what: str) -> str:
        """GET a CNB text file; an HTTP or network failure is an ``FXServiceError`` (a 429 an ``FXRateLimitedError``)."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            logger.warning(f"CNB request failed for {what}: {e}")
            raise FXServiceError(f"CNB API error for {what}: {e}") from e
        return response.text
