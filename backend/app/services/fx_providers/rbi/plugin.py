"""
Reserve Bank of India (RBI) FX rate provider.

This provider reads the reference rates of the Indian rupee from the RBI's «Reference Rate Archive» page
(https://www.rbi.org.in/Scripts/ReferenceRateArchive.aspx), an ASP.NET form: a GET of the page, then one POST per
window with the dates and the hidden fields the page gives every visitor (``__VIEWSTATE``, ``__EVENTVALIDATION``…), as
a browser sends them (developer decision Q4 (a), 19/11/2026). The result is an HTML table read with CSS selectors. INR
is the base of the provider.

Since 10/07/2018 the reference rate is computed by FBIL (Financial Benchmarks India Pvt Ltd); the archive shows it
(equal to FBIL's own values on 11 and 12/11/2026). Before, the RBI computed it.

Terms: FBIL «does not authorize commercial use of the data available in its website without written permission»; the
RBI's site is «All Rights Reserved». Developer decision Q2 (b), 19/11/2026: the provider stays for a self-hosted
instance, with a note on the terms, and the paid cloud turns it off (``LIBREFOLIO_FX_PROVIDERS_ENABLED``). The RUB
column is the RBI's own (Q3 (b)), not the Central Bank of Russia's.

Measured on 19/11/2026:

- The table: ``Date``, then one column per currency whose header gives the unit: ``USD (INR / 1 USD)``,
  ``JPY (INR / 100 JPY)``, ``IDR (INR / 10000 IDR)``. The unit is read from the header. Newest first.
- History from 25/08/1998 (USD, GBP, JPY; EUR from 04/01/1999, written 0.0000 before; AED and IDR from 22/01/2026, RUB
  from 15/09/2026, empty cells before). **The archive has a hole**: nothing from 10/07 to 23/07/2018 and from
  25/07/2018 to 11/04/2022 (FBIL's rates of those years are not in it).
- Junk: one row dated Sunday 11/10/1998 copies 10/11/1998 (day and month swapped); Sunday rows are skipped (D2). One
  Saturday (23/09/2000) looks like a real rate and is kept.
- Time: one year in one POST takes ~1.7 s, ten years ~78 s: the call asks windows of at most ``WINDOW_DAYS``.
- Budget: a 14-day sync is 1 GET + 1 POST; ``"min"`` is 1 GET + 29 POSTs, ~75 s with the pause.
- An empty range answers the page with the form and without the result table.
"""

import asyncio
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx
from bs4 import BeautifulSoup

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

PAGE_URL = "https://www.rbi.org.in/Scripts/ReferenceRateArchive.aspx"
#: The first day of the archive.
FIRST_DAY = date(1998, 8, 25)
#: Days asked per POST: one year answers in ~2 s, ten years in ~78 s.
WINDOW_DAYS = 365
#: An honest, constant User-Agent, the one BOE sends.
USER_AGENT = "Mozilla/5.0 (compatible; LibreFolio/1.0; +https://github.com/librefolio)"

#: CSS selectors: the hidden fields of the form, its date field, the header cells of the result table.
HIDDEN_SELECTOR = "input[type=hidden][name]"
FORM_SELECTOR = "#txtFromDate"
TABLE_SELECTOR = "table.tablebg"
HEADER_CELL_SELECTOR = "td.tableheader"
#: A currency column's header: ``USD (INR / 1 USD)``.
HEADER_PATTERN = re.compile(r"^([A-Z]{3}) \(INR / (\d+) ([A-Z]{3})\)$")

_CURRENCIES = ["AED", "EUR", "GBP", "IDR", "JPY", "RUB", "USD"]


@register_provider(FXProviderRegistry)
class RBIProvider(FXRateProvider):
    """
    Reserve Bank of India FX rate provider.

    Provides the reference rate (FBIL since 2018) of 7 currencies with INR as base currency, INR per unit.
    Data source: the RBI's Reference Rate Archive, an ASP.NET form read as HTML.

    Coverage: USD, GBP, EUR, JPY, AED, IDR, RUB.
    Update frequency: Mumbai business days.
    """

    #: Pause between two POSTs of one call (D9).
    PAUSE_SECONDS = 1.0

    @property
    def code(self) -> str:
        return "RBI"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Reserve Bank of India"

    @property
    def icon(self) -> str | None:
        return "https://www.rbi.org.in/favicon.ico"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/rbi/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Reserve Bank of India — the reference rate of the Indian rupee (INR) for USD, GBP, EUR, JPY, AED, IDR and RUB, computed by FBIL since 2018. Mumbai business days, history from 1998 with a gap from July 2018 to April 2022. Source: Reserve Bank of India (FBIL reference rate).",
            "it": "Reserve Bank of India — il tasso di riferimento della rupia indiana (INR) per USD, GBP, EUR, JPY, AED, IDR e RUB, calcolato da FBIL dal 2018. Giorni lavorativi di Mumbai, storia dal 1998 con un vuoto da luglio 2018 ad aprile 2022. Fonte: Reserve Bank of India (tasso di riferimento FBIL).",
            "fr": "Reserve Bank of India — le taux de référence de la roupie indienne (INR) pour USD, GBP, EUR, JPY, AED, IDR et RUB, calculé par FBIL depuis 2018. Jours ouvrables de Mumbai, historique depuis 1998 avec un trou de juillet 2018 à avril 2022. Source : Reserve Bank of India (taux de référence FBIL).",
            "es": "Reserve Bank of India — el tipo de referencia de la rupia india (INR) para USD, GBP, EUR, JPY, AED, IDR y RUB, calculado por FBIL desde 2018. Días hábiles de Bombay, historial desde 1998 con un hueco de julio de 2018 a abril de 2022. Fuente: Reserve Bank of India (tipo de referencia FBIL).",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "The RBI's rates are read from a web page form, which can change without notice. FBIL, which computes the reference rate since 2018, does not allow commercial use of its data without written permission: this provider is meant for your own instance. The RBI's archive has no rates from 25 July 2018 to 11 April 2022, nor from 10 to 23 July 2018. AED and IDR start in January 2026 and RUB in September 2026; the RUB rate is the one the RBI publishes, not the Central Bank of Russia's.",
            "it": "I tassi della RBI si leggono da un modulo di una pagina web, che può cambiare senza preavviso. FBIL, che calcola il tasso di riferimento dal 2018, non consente l'uso commerciale dei suoi dati senza un permesso scritto: questo provider è pensato per la tua istanza. L'archivio della RBI non ha tassi dal 25 luglio 2018 all'11 aprile 2022, né dal 10 al 23 luglio 2018. AED e IDR iniziano a gennaio 2026 e RUB a settembre 2026; il tasso del RUB è quello che pubblica la RBI, non quello della Banca centrale russa.",
            "fr": "Les taux de la RBI sont lus depuis un formulaire d'une page web, qui peut changer sans préavis. FBIL, qui calcule le taux de référence depuis 2018, n'autorise pas l'usage commercial de ses données sans permission écrite : ce fournisseur est prévu pour votre propre instance. L'archive de la RBI n'a pas de taux du 25 juillet 2018 au 11 avril 2022, ni du 10 au 23 juillet 2018. AED et IDR commencent en janvier 2026 et RUB en septembre 2026 ; le taux du RUB est celui que publie la RBI, pas celui de la Banque centrale de Russie.",
            "es": "Los tipos de la RBI se leen de un formulario de una página web, que puede cambiar sin aviso. FBIL, que calcula el tipo de referencia desde 2018, no permite el uso comercial de sus datos sin permiso escrito: este proveedor está pensado para tu propia instancia. El archivo de la RBI no tiene tipos del 25 de julio de 2018 al 11 de abril de 2022, ni del 10 al 23 de julio de 2018. AED e IDR empiezan en enero de 2026 y RUB en septiembre de 2026; el tipo del RUB es el que publica la RBI, no el del Banco Central de Rusia.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # A web form, restrictive terms and a four-year hole: limits that can mislead, warning (lane 75)
        return "warning"

    @property
    def base_currency(self) -> str:
        return "INR"

    @property
    def test_currencies(self) -> list[str]:
        return ["INR", "USD", "EUR", "GBP", "JPY"]

    @property
    def fallback_currencies(self) -> list[str]:
        return sorted([*_CURRENCIES, "INR"])

    async def get_supported_currencies(self) -> list[str]:
        """The archive's 7 currencies, plus INR: no request."""
        return sorted([*_CURRENCIES, "INR"])

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch the asked currencies from the archive, one POST per window of at most ``WINDOW_DAYS`` days:
        ``(day, CUR, 'INR', INR per 1 CUR)``, the unit read from the column's header.

        Every value keeps its day (D2). A cell that is empty, zero or not a number loses only that currency of the row; a
        row with an unreadable day, or dated Sunday, is skipped (X-R50); a day where a currency has two different values
        is dropped for that currency. A window that fails fails the call.

        Raises:
            ValueError: base_currency is neither None nor INR
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: a request failed, or a page is not the archive's form or table
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"RBI provider only supports INR as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        wanted = set(asked) & set(_CURRENCIES)
        if not wanted or request_start > end_date:
            return results

        values: dict[tuple[date, str], set[Decimal]] = {}
        for day, currency, value in await self._fetch_windows(request_start, end_date):
            if currency in wanted and request_start <= day <= end_date:
                values.setdefault((day, currency), set()).add(value)

        conflicting = 0
        for (day, currency), found in sorted(values.items()):
            if len(found) > 1:
                conflicting += 1
                continue
            results[currency].append((day, currency, self.base_currency, next(iter(found))))
        if conflicting:
            logger.warning(f"RBI: {conflicting} day(s) with two different values for one currency dropped")
        return results

    async def _fetch_windows(self, request_start: date, end_date: date) -> list[tuple[date, str, Decimal]]:
        """The GET, then one POST per window in one session, each POST sending the hidden fields of the last answer."""
        observations: list[tuple[date, str, Decimal]] = []
        async with httpx.AsyncClient(timeout=120.0, headers={"User-Agent": USER_AGENT}) as client:
            page = _parse_form(await self._request(client, "GET", None), "page")
            hidden = {field["name"]: field.get("value", "") for field in page.select(HIDDEN_SELECTOR)}
            if "__VIEWSTATE" not in hidden:
                raise FXServiceError("RBI archive page has no __VIEWSTATE field (the page changed)")
            window_start = request_start
            while window_start <= end_date:
                window_end = min(end_date, window_start + timedelta(days=WINDOW_DAYS - 1))
                if window_start > request_start:
                    await asyncio.sleep(self.PAUSE_SECONDS)
                form = {**hidden, "chkAll": "on", "txtFromDate": f"{window_start:%d/%m/%Y}", "txtToDate": f"{window_end:%d/%m/%Y}", "btnSubmit": " GO "}
                answer = _parse_form(await self._request(client, "POST", form), f"answer for {window_start}..{window_end}")
                observations.extend(_table_observations(answer))
                hidden = {field["name"]: field.get("value", "") for field in answer.select(HIDDEN_SELECTOR)} or hidden
                window_start = window_end + timedelta(days=1)
        return observations

    async def _request(self, client: httpx.AsyncClient, method: str, form: dict[str, str] | None) -> str:
        """One GET or POST of the archive page; 429 → rate limit, any other failure → FXServiceError."""
        try:
            response = await client.request(method, PAGE_URL, data=form)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            logger.warning(f"RBI {method} failed: {e}")
            raise FXServiceError(f"RBI API error ({method}): {e}") from e
        return response.text


def _parse_form(html: str, what: str) -> BeautifulSoup:
    """The page, when it holds the archive's form; otherwise the page changed or the request was refused."""
    soup = BeautifulSoup(html, "html.parser")
    if soup.select_one(FORM_SELECTOR) is None:
        raise FXServiceError(f"RBI {what} is not the reference rate archive form (the page changed, or the request was refused)")
    return soup


def _table_observations(page: BeautifulSoup) -> list[tuple[date, str, Decimal]]:
    """The result table's values as ``(day, CUR, INR per 1 CUR)``; none when the page has no result table (an empty range)."""
    table = next((t for t in page.select(TABLE_SELECTOR) if t.select_one("tr") is not None and t.select_one("tr").select(HEADER_CELL_SELECTOR)), None)
    if table is None:
        return []
    rows = table.select("tr")
    columns = _columns([cell.get_text(" ", strip=True) for cell in rows[0].select("td")])
    observations: list[tuple[date, str, Decimal]] = []
    for row in rows[1:]:
        cells = [cell.get_text(strip=True) for cell in row.select("td")]
        try:
            day = datetime.strptime(cells[0], "%d/%m/%Y").date()
        except (IndexError, ValueError):
            continue
        if day.weekday() == 6:
            continue  # the bank does not publish on Sundays: the one Sunday row copies another day (D2)
        for index, (currency, unit) in columns.items():
            value = _positive(cells[index] if index < len(cells) else "")
            if value is not None:
                observations.append((day, currency, value / unit))
    return observations


def _columns(header: list[str]) -> dict[int, tuple[str, Decimal]]:
    """Column index → (currency, unit) from the header; a header of another shape is an error."""
    if not header or header[0] != "Date":
        raise FXServiceError(f"RBI result table does not start with a Date column: {header[:2]}")
    columns: dict[int, tuple[str, Decimal]] = {}
    for index, text in enumerate(header[1:], start=1):
        match = HEADER_PATTERN.match(text)
        if match is None or match.group(1) != match.group(3):
            raise FXServiceError(f"RBI result table has an unknown column {text!r} (the page changed)")
        columns[index] = (match.group(1), Decimal(match.group(2)))
    missing = set(_CURRENCIES) - {currency for currency, _ in columns.values()}
    if missing:
        raise FXServiceError(f"RBI result table lacks the columns {sorted(missing)} (the page changed)")
    return columns


def _positive(text: str) -> Decimal | None:
    """A cell's value when it is a positive number; None for an empty cell, 0.0000 or text."""
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return value if value.is_finite() and value > 0 else None
