"""
Bank of Ghana (BOG) FX rate provider.

This provider reads the interbank exchange rates of the Bank of Ghana from the WordPress «wpDataTables» table 40 of its
«Historical Interbank FX Rates» page (https://www.bog.gov.gh/treasury-and-the-markets/historical-interbank-fx-rates/),
through ``admin-ajax.php`` and the DataTables server-side protocol. The table asks for the nonce the page gives every
visitor (``wdtNonceFrontendServerSide_40``): the provider reads the page, then sends the nonce with the form, as a
browser does (developer decision Q4 (a), 19/11/2026); without it the server answers an empty body. GHS is the base.

The endpoint is not documented (decision D10 c of lane 75). Terms: the bank's disclaimer gives the information «for
general reference purposes only», with no clause against reproduction; «© Bank of Ghana. All rights reserved.».
Developer decision D1: offered for a self-hosted instance that stores the rates for its owner. The description names
the source.

Measured on 19/11/2026:

- 146 034 rows from 02/01/1996, 19 pairs, the whole table in one request ~10 MB in ~12 s. The server honours both
  bounds of the date filter (``columns[0][search][value]=dd Mon yyyy|dd Mon yyyy``) and a filter on the pair.
- Columns: date (``19 Nov 2026``), currency name, pair code, buying, selling, mid. The **mid** («market reference rate»,
  the weighted median of the USD/GHS spot trades up to 15:30) is used. Values can carry thousands separators.
- Directions from the pair code: ``USDGHS`` is GHS per 1 USD; ``GHSXOF`` is XOF per 1 GHS.
- **History from 2020** (``FIRST_DAY``): before, the table holds old cedis up to 27/06/2007 (the redenomination,
  10 000:1) and, until 2019, 110 one-day values of another currency or another scale in the 17 pairs served (16 ten-fold or more) (USD 9 539.94 on
  19/06/2012 between 1.88 and 1.89). From 2020 one such day is left (CNY 2.3951 on 28/02/2025, between 2.13 and 2.13).
  To be reviewed with the developer (lane 75, L33).
- Dropped pairs: ``WAUGHS`` (the ECOWAS unit of account) and ``GHSMRO`` (always USDGHS × 357.5, a parity of 2017,
  while the market says about 400 MRO per USD; MRO is no longer an ISO code).
- The leone: ``GHSSLL`` is in old leones until 10/09/2026 and in new leones (SLE) from 11/09/2026; old leones are
  served as SLE ÷ 1 000, as BCB does.
- JPY has four decimals (0.0736 GHS: steps of about 0.14%).
- Budget: one GET (~240 KB, ~4 s) and one POST for any range; ``"min"`` is ~2.3 MB.
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

PAGE_URL = "https://www.bog.gov.gh/treasury-and-the-markets/historical-interbank-fx-rates/"
AJAX_URL = "https://www.bog.gov.gh/wp-admin/admin-ajax.php"
TABLE_ID = "40"
#: The hidden input of the page that holds the table's nonce.
NONCE_FIELD = f"wdtNonceFrontendServerSide_{TABLE_ID}"
#: The first day served: the years before carry old cedis and frequent one-day values of another currency.
FIRST_DAY = date(2020, 1, 1)
#: Rows asked per request: every row of the range in one answer.
PAGE_LENGTH = 100000
#: The first day of the new leone in the table; before, ``GHSSLL`` is in old leones.
SLE_FROM = date(2026, 9, 11)
SLL_PER_SLE = Decimal(1000)
#: The site's own icon (its favicon link).
ICON_URL = "https://www.bog.gov.gh/wp-content/uploads/2020/08/logo-150x150.png"
#: An honest, constant User-Agent, the one BOE sends.
USER_AGENT = "Mozilla/5.0 (compatible; LibreFolio/1.0; +https://github.com/librefolio)"

#: The table's pair codes → (ISO code, kind): ``per_unit`` GHS per 1 unit, ``inverse`` units per 1 GHS.
PAIRS: dict[str, tuple[str, str]] = {
    "AUDGHS": ("AUD", "per_unit"),
    "CADGHS": ("CAD", "per_unit"),
    "CHFGHS": ("CHF", "per_unit"),
    "CNYGHS": ("CNY", "per_unit"),
    "DKKGHS": ("DKK", "per_unit"),
    "EURGHS": ("EUR", "per_unit"),
    "GBPGHS": ("GBP", "per_unit"),
    "JPYGHS": ("JPY", "per_unit"),
    "NOKGHS": ("NOK", "per_unit"),
    "NZDGHS": ("NZD", "per_unit"),
    "SEKGHS": ("SEK", "per_unit"),
    "USDGHS": ("USD", "per_unit"),
    "ZARGHS": ("ZAR", "per_unit"),
    "GHSGMD": ("GMD", "inverse"),
    "GHSNGN": ("NGN", "inverse"),
    "GHSXOF": ("XOF", "inverse"),
    "GHSSLL": ("SLE", "inverse"),
}

#: English month abbreviations of the table's dates, independent of the process locale.
_MONTHS = {name: number for number, name in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}
_MONTH_NAMES = {number: name for name, number in _MONTHS.items()}
_CURRENCIES = sorted({iso for iso, _ in PAIRS.values()} | {"GHS"})


def _format_day(day: date) -> str:
    return f"{day.day:02d} {_MONTH_NAMES[day.month]} {day.year}"


def _parse_day(text: str) -> date | None:
    """``19 Nov 2026`` → date; None when it cannot be read (a parsing probe: the None is the answer)."""
    parts = text.strip().split()
    if len(parts) != 3 or parts[1] not in _MONTHS:
        return None
    try:
        return date(int(parts[2]), _MONTHS[parts[1]], int(parts[0]))
    except ValueError:
        return None


@register_provider(FXProviderRegistry)
class BOGProvider(FXRateProvider):
    """
    Bank of Ghana FX rate provider.

    Provides the Bank of Ghana's daily interbank mid rates of 17 currencies with GHS as base currency, in each pair's
    own direction. Data source: the wpDataTables table of the bank's historical rates page (undocumented).

    Coverage: a fixed pair map, 17 currencies plus GHS.
    Update frequency: Ghanaian business days.
    """

    @property
    def code(self) -> str:
        return "BOG"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Bank of Ghana"

    @property
    def icon(self) -> str | None:
        return ICON_URL

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/bog/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Bank of Ghana — daily interbank mid rates of 17 currencies against the Ghanaian cedi (GHS), among them the naira, the West African CFA franc, the dalasi and the leone. Ghanaian business days, history from 2020. Source: Bank of Ghana.",
            "it": "Bank of Ghana — tassi medi interbancari giornalieri di 17 valute contro il cedi ghanese (GHS), tra cui la naira, il franco CFA dell'Africa occidentale, il dalasi e il leone. Giorni lavorativi del Ghana, storia dal 2020. Fonte: Bank of Ghana.",
            "fr": "Bank of Ghana — taux moyens interbancaires quotidiens de 17 devises contre le cedi ghanéen (GHS), dont le naira, le franc CFA d'Afrique de l'Ouest, le dalasi et le leone. Jours ouvrables ghanéens, historique depuis 2020. Source : Bank of Ghana.",
            "es": "Bank of Ghana — tipos medios interbancarios diarios de 17 monedas contra el cedi ghanés (GHS), entre ellas el naira, el franco CFA de África occidental, el dalasi y el leone. Días hábiles de Ghana, historial desde 2020. Fuente: Bank of Ghana.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "The Bank of Ghana's rates come from an undocumented source behind its website, which can change without notice. The history starts in 2020: the earlier years of the bank's table hold old cedis and many days with the value of another currency. A single wrong day can still appear (CNY on 28 February 2025). The yen has four decimals (steps of about 0.14%). Until 10 September 2026 the bank quotes the leone in old leones, converted here to new leones (SLE). A day listed twice with two different rates is left out.",
            "it": "I tassi della Bank of Ghana vengono da una fonte non documentata dietro il suo sito, che può cambiare senza preavviso. La storia parte dal 2020: gli anni precedenti della tabella della banca contengono vecchi cedi e molti giorni con il valore di un'altra valuta. Può ancora comparire un singolo giorno sbagliato (CNY il 28 febbraio 2025). Lo yen ha quattro decimali (passi di circa lo 0,14%). Fino al 10 settembre 2026 la banca quota il leone in vecchi leoni, convertiti qui in nuovi leoni (SLE). Un giorno elencato due volte con due tassi diversi resta fuori.",
            "fr": "Les taux de la Bank of Ghana viennent d'une source non documentée derrière son site, qui peut changer sans préavis. L'historique commence en 2020 : les années précédentes du tableau de la banque contiennent d'anciens cedis et de nombreux jours avec la valeur d'une autre devise. Un jour erroné isolé peut encore apparaître (CNY le 28 février 2025). Le yen a quatre décimales (pas d'environ 0,14 %). Jusqu'au 10 septembre 2026 la banque cote le leone en anciens leones, convertis ici en nouveaux leones (SLE). Un jour listé deux fois avec deux taux différents est écarté.",
            "es": "Los tipos del Bank of Ghana vienen de una fuente no documentada detrás de su sitio, que puede cambiar sin aviso. El historial empieza en 2020: los años anteriores de la tabla del banco contienen cedis antiguos y muchos días con el valor de otra moneda. Aún puede aparecer un único día erróneo (CNY el 28 de febrero de 2025). El yen tiene cuatro decimales (pasos de alrededor del 0,14 %). Hasta el 10 de septiembre de 2026 el banco cotiza el leone en leones antiguos, convertidos aquí en leones nuevos (SLE). Un día que aparece dos veces con dos tipos distintos queda fuera.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # An undocumented source, a short clean history and residual wrong days: limits that can mislead (lane 75)
        return "warning"

    @property
    def base_currency(self) -> str:
        return "GHS"

    @property
    def test_currencies(self) -> list[str]:
        return ["GHS", "USD", "EUR", "GBP", "NGN"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(_CURRENCIES)

    async def get_supported_currencies(self) -> list[str]:
        """The currencies of the pair map, plus GHS: no request."""
        return list(_CURRENCIES)

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch the asked currencies from table 40: the page for the nonce, then one POST for the whole range.
        ``(day, CUR, 'GHS', GHS per 1 CUR)``, or ``(day, 'GHS', CUR, CUR per 1 GHS)`` for the ``GHSXXX`` pairs.

        Every value keeps its day (D2). A row with an unknown pair, an unreadable day or no positive mid is skipped
        (X-R50); a day where a currency has two different mids is dropped for that currency.

        Raises:
            ValueError: base_currency is neither None nor GHS
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: a request failed, the page has no nonce, or the answer is not the table's JSON
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"BOG provider only supports GHS as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        wanted = set(asked) & {iso for iso, _ in PAIRS.values()}
        if not wanted or request_start > end_date:
            return results

        values: dict[tuple[date, str], set[tuple[str, str, Decimal]]] = {}
        for row in await self._get_rows(request_start, end_date):
            observation = _observation(row)
            if observation is None:
                continue
            day, currency, base, quote, value = observation
            if currency in wanted and request_start <= day <= end_date:
                values.setdefault((day, currency), set()).add((base, quote, value))

        conflicting = 0
        for (day, currency), found in sorted(values.items()):
            if len(found) > 1:
                conflicting += 1
                continue
            base, quote, value = next(iter(found))
            results[currency].append((day, base, quote, value))
        if conflicting:
            logger.warning(f"BOG: {conflicting} day(s) with two different values for one currency dropped")
        return results

    async def _get_rows(self, request_start: date, end_date: date) -> list:
        """The page's nonce, then the table's rows of the range, in one session."""
        async with httpx.AsyncClient(timeout=120.0, headers={"User-Agent": USER_AGENT}) as client:
            page = await self._send(client, "GET", PAGE_URL)
            nonce = _nonce(page)
            form = {"draw": "1", "start": "0", "length": str(PAGE_LENGTH), "order[0][column]": "0", "order[0][dir]": "desc", "wdtNonce": nonce}
            for column in range(6):
                form[f"columns[{column}][data]"] = str(column)
                form[f"columns[{column}][searchable]"] = "true"
                form[f"columns[{column}][orderable]"] = "true"
                form[f"columns[{column}][search][value]"] = ""
            form["columns[0][search][value]"] = f"{_format_day(request_start)}|{_format_day(end_date)}"
            body = await self._send(client, "POST", AJAX_URL, params={"action": "get_wdtable", "table_id": TABLE_ID}, data=form)
        return _rows(body)

    async def _send(self, client: httpx.AsyncClient, method: str, url: str, **kwargs) -> str:
        """One request; 429 → rate limit, any other failure → FXServiceError."""
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            logger.warning(f"BOG {method} failed: {e}")
            raise FXServiceError(f"BOG API error ({method}): {e}") from e
        return response.text


def _nonce(page: str) -> str:
    """The table's nonce from the page's hidden input; a page without it is an error."""
    marker = f'name="{NONCE_FIELD}"'
    index = page.find(marker)
    if index < 0:
        raise FXServiceError(f"BOG page has no {NONCE_FIELD} (the page changed, or the request was refused)")
    tag = page[page.rfind("<", 0, index) : page.find(">", index)]
    value_at = tag.find('value="')
    if value_at < 0:
        raise FXServiceError(f"BOG page's {NONCE_FIELD} has no value (the page changed)")
    return tag[value_at + 7 : tag.find('"', value_at + 7)]


def _rows(body: str) -> list:
    """The ``data`` list of the table's answer; anything else is an error, a cut answer too."""
    text = body.strip()
    if not text:
        raise FXServiceError("BOG answer is empty (the nonce may have been refused, or the endpoint changed)")
    if text[:1] == "<":
        raise FXServiceError("BOG answer is an HTML page, not the table's JSON (undocumented endpoint changed, or request refused)")
    try:
        data = json.loads(text)
    except ValueError:
        raise FXServiceError(f"BOG answer is not JSON: first bytes {text[:40]!r}") from None
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise FXServiceError("BOG answer has no data list (undocumented endpoint changed)")
    try:
        filtered = int(str(data.get("recordsFiltered")))
    except ValueError:
        filtered = None
    if filtered is not None and filtered > len(rows):
        # Rows come newest first: a cut answer would lose the oldest days silently
        raise FXServiceError(f"BOG answer was cut at {len(rows)} of {filtered} rows (PAGE_LENGTH too small)")
    return rows


def _observation(row: object) -> tuple[date, str, str, str, Decimal] | None:
    """One row as ``(day, CUR, base, quote, mid)`` in the pair's direction; None when it cannot be read."""
    if not isinstance(row, list) or len(row) < 6:
        return None
    mapped = PAIRS.get(str(row[2]).strip())
    day = _parse_day(str(row[0]))
    if mapped is None or day is None:
        return None
    try:
        value = Decimal(str(row[5]).replace(",", "").strip())
    except InvalidOperation:
        return None
    if not value.is_finite() or value <= 0:
        return None
    currency, kind = mapped
    if kind == "per_unit":
        return day, currency, currency, "GHS", value
    if currency == "SLE" and day < SLE_FROM:
        value = value / SLL_PER_SLE
    return day, currency, "GHS", currency, value
