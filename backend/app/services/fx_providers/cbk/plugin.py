"""
Central Bank of Kenya (CBK) FX rate provider.

This provider reads the exchange rates of the Central Bank of Kenya from the two WordPress «wpDataTables» tables of its
rate pages, through ``admin-ajax.php`` and the server-side DataTables protocol (a POST with the table's form fields, as
the page sends it; no nonce needed on 19/11/2026). KES is the base of the provider.

Pages: https://www.centralbank.go.ke/forex/ and https://www.centralbank.go.ke/rates/forex-exchange-rates/.
The endpoint is not documented (decision D10 c of lane 75): the note says so, and an answer of another shape fails the
call with a clear error instead of storing anything. The form fields are those any visitor's browser sends (developer
decision Q4 (a), 19/11/2026); nothing is worked around. Terms: no terms of use found (``/disclaimer/`` and
``/terms-of-use/`` answer 404; ❔). Developer decision D1 (lane 75): the provider is offered for a self-hosted instance that
stores the rates for its owner; nothing downloaded from the bank is committed. The description names the source.

Measured on 19/11/2026:

- Table ``193``, «trade weighted average indicative rates», from 05/01/2024: 3 columns (date, name, rate), 15 078 rows,
  21 names; the whole table in one request is ~600 KB in ~5 s. The server honours a lower bound on the date column
  (``columns[0][search][value]=dd/mm/yyyy|``: from 10/11/2026, 168 rows) and ignores an upper bound: the end is cut here.
- Table ``32``, the earlier «indicative rates» up to 04/01/2024: 5 columns (date, name, mean, buy, sell; the mean is
  used), 97 606 rows, ~5.8 MB in ~10 s, names with variants (``JPY(100)``, ``KES/USHS``, ``HONGKONG $``…), 21 junk rows
  dated 01/01/1970; daily from 02/11/2004. Three more days are junk: 12/09/2003 and 12/09/2004 (a Sunday) carry
  values of 2012 under scrambled names, 12/04/2015 (a Sunday) copies December 2015. ``FIRST_DAY`` cuts the first ones
  and the old table's Saturday and Sunday rows are skipped (D2: a value that cannot sit under its own day is dropped).
  The current table has no weekend rows and keeps any it may get.
- **The method changed in January 2024**: since then a weighted average of the registered interbank spot trades
  (the CBK's forex page); before, the average of the main dealers' buying and selling rates at the opening. The series
  has a break there; the note says so.
- Directions: KES per 1 unit for most names, KES per 100 yen (``JPY (100)``), and **units per 1 KES** for the four East
  African currencies (``KES / USHS``, ``KES / TSHS``, ``KES / RWF``, ``KES / BIF``).
- Duplicates: table 193 has 21 duplicate day-and-name keys, all identical; table 32 has 250, 79 of them with two
  different values. Such a day is dropped for that currency, never picked (X-R50, as CBN).
- Precision: four decimals until 2025, two in 2026 (INR 1.39 KES: steps of ~0.7%).
- Budget: a 14-day sync is 1 request (table 193 from the start of the range); ``"min"`` is 2 requests (~20 s).
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

AJAX_URL = "https://www.centralbank.go.ke/wp-admin/admin-ajax.php"
#: The current table (weighted average of the interbank spot trades), from CURRENT_FIRST_DAY.
CURRENT_TABLE = "193"
CURRENT_FIRST_DAY = date(2024, 1, 5)
#: The earlier table (the dealers' mean, buy and sell), up to the day before CURRENT_FIRST_DAY.
OLD_TABLE = "32"
#: The first day kept, the start of the daily series: the old table holds junk rows before it (01/01/1970, 2003, 2004).
FIRST_DAY = date(2004, 11, 2)
#: Rows asked per request: every row from the lower bound in one answer.
PAGE_LENGTH = 100000
#: The columns of each table: date, name, rate (current); date, name, mean, buy, sell (old).
_COLUMNS = {CURRENT_TABLE: 3, OLD_TABLE: 5}
#: An honest, constant User-Agent, the one BOE sends.
USER_AGENT = "Mozilla/5.0 (compatible; LibreFolio/1.0; +https://github.com/librefolio)"

#: The bank's names (stripped) → (ISO code, kind): ``per_unit`` KES per 1 unit, ``per_100`` KES per 100 units,
#: ``inverse`` units per 1 KES. Any other name is discarded.
CURRENCY_NAMES: dict[str, tuple[str, str]] = {
    "US DOLLAR": ("USD", "per_unit"),
    "STG POUND": ("GBP", "per_unit"),
    "EURO": ("EUR", "per_unit"),
    "SA RAND": ("ZAR", "per_unit"),
    "AE DIRHAM": ("AED", "per_unit"),
    "CAN $": ("CAD", "per_unit"),
    "S FRANC": ("CHF", "per_unit"),
    "SW KRONER": ("SEK", "per_unit"),
    "NOR KRONER": ("NOK", "per_unit"),
    "DAN KRONER": ("DKK", "per_unit"),
    "IND RUPEE": ("INR", "per_unit"),
    "HONGKONG DOLLAR": ("HKD", "per_unit"),
    "HONGKONG $": ("HKD", "per_unit"),
    "SINGAPORE DOLLAR": ("SGD", "per_unit"),
    "SINGAPORE $": ("SGD", "per_unit"),
    "SAUDI RIYAL": ("SAR", "per_unit"),
    "CHINESE YUAN": ("CNY", "per_unit"),
    "AUSTRALIAN $": ("AUD", "per_unit"),
    "JPY (100)": ("JPY", "per_100"),
    "JPY(100)": ("JPY", "per_100"),
    "KES / USHS": ("UGX", "inverse"),
    "KES/USHS": ("UGX", "inverse"),
    "KES / TSHS": ("TZS", "inverse"),
    "KES/TSHS": ("TZS", "inverse"),
    "KES / RWF": ("RWF", "inverse"),
    "KES/RWF": ("RWF", "inverse"),
    "KES / BIF": ("BIF", "inverse"),
    "KES/BIF": ("BIF", "inverse"),
}

_CURRENCIES = sorted({iso for iso, _ in CURRENCY_NAMES.values()} | {"KES"})
_HUNDRED = Decimal(100)


@register_provider(FXProviderRegistry)
class CBKProvider(FXRateProvider):
    """
    Central Bank of Kenya FX rate provider.

    Provides the CBK's daily exchange rates of 21 currencies with KES as base currency, in each name's own direction.
    Data source: the two wpDataTables tables of the CBK's rate pages (undocumented), one request per table.

    Coverage: a fixed name map, 21 currencies plus KES.
    Update frequency: Kenyan business days.
    """

    #: Pause between the two tables of one call (D9).
    PAUSE_SECONDS = 0.3

    @property
    def code(self) -> str:
        return "CBK"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Central Bank of Kenya"

    @property
    def icon(self) -> str | None:
        return "https://www.centralbank.go.ke/wp-content/uploads/2016/09/NewLogoCBK-150x150.png"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/cbk/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Central Bank of Kenya — daily exchange rates of 21 currencies against the Kenyan shilling (KES), among them the Ugandan and Tanzanian shillings and the Rwandan and Burundian francs. Kenyan business days, history from 2004. Source: Central Bank of Kenya.",
            "it": "Central Bank of Kenya — tassi di cambio giornalieri di 21 valute contro lo scellino keniota (KES), tra cui gli scellini ugandese e tanzaniano e i franchi ruandese e burundese. Giorni lavorativi kenioti, storia dal 2004. Fonte: Central Bank of Kenya.",
            "fr": "Central Bank of Kenya — taux de change quotidiens de 21 devises contre le shilling kényan (KES), dont les shillings ougandais et tanzanien et les francs rwandais et burundais. Jours ouvrables kényans, historique depuis 2004. Source : Central Bank of Kenya.",
            "es": "Central Bank of Kenya — tipos de cambio diarios de 21 monedas contra el chelín keniano (KES), entre ellas los chelines ugandés y tanzano y los francos ruandés y burundés. Días hábiles kenianos, historial desde 2004. Fuente: Central Bank of Kenya.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "The CBK's rates come from an undocumented source behind its website, which can change without notice. The method changed in January 2024: since then a weighted average of the interbank spot trades, before that the average of the main dealers' rates, so the series has a break there. Since 2026 the bank publishes two decimals (INR 1.39 KES: steps of about 0.7%). A day listed twice with two different rates is left out.",
            "it": "I tassi della CBK vengono da una fonte non documentata dietro il suo sito, che può cambiare senza preavviso. Il metodo è cambiato a gennaio 2024: da allora una media ponderata delle operazioni a pronti interbancarie, prima la media dei tassi dei principali operatori, quindi la serie ha un salto lì. Dal 2026 la banca pubblica due decimali (INR 1,39 KES: passi di circa lo 0,7%). Un giorno elencato due volte con due tassi diversi resta fuori.",
            "fr": "Les taux de la CBK viennent d'une source non documentée derrière son site, qui peut changer sans préavis. La méthode a changé en janvier 2024 : depuis, une moyenne pondérée des opérations au comptant interbancaires, avant, la moyenne des taux des principaux opérateurs ; la série a donc une rupture à cet endroit. Depuis 2026 la banque publie deux décimales (INR 1,39 KES : pas d'environ 0,7 %). Un jour listé deux fois avec deux taux différents est écarté.",
            "es": "Los tipos de la CBK vienen de una fuente no documentada detrás de su sitio, que puede cambiar sin aviso. El método cambió en enero de 2024: desde entonces una media ponderada de las operaciones de contado interbancarias, antes la media de los tipos de los principales operadores, así que la serie tiene una ruptura ahí. Desde 2026 el banco publica dos decimales (INR 1,39 KES: pasos de alrededor del 0,7 %). Un día que aparece dos veces con dos tipos distintos queda fuera.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # An undocumented source, a method break and two decimals: a data limit that can mislead, warning (lane 75)
        return "warning"

    @property
    def base_currency(self) -> str:
        return "KES"

    @property
    def test_currencies(self) -> list[str]:
        return ["KES", "USD", "EUR", "GBP", "UGX"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(_CURRENCIES)

    async def get_supported_currencies(self) -> list[str]:
        """The currencies of the name map, plus KES: no request."""
        return list(_CURRENCIES)

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch the asked currencies from the table(s) of the range: the old one up to 2024-01-04, the current one from
        2024-01-05, old first. ``(day, CUR, 'KES', KES per 1 CUR)``, or ``(day, 'KES', CUR, CUR per 1 KES)`` for the
        East African names.

        Every value keeps its day (D2). A row with an unknown name, an unreadable day or no positive value is skipped
        (X-R50); a day where a currency has two different values is dropped for that currency. The tables make one
        dataset: a table that fails fails the call.

        Raises:
            ValueError: base_currency is neither None nor KES
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: a request failed, or an answer is not a wpDataTables JSON
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"CBK provider only supports KES as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        wanted = set(asked) & {iso for iso, _ in CURRENCY_NAMES.values()}
        if not wanted or request_start > end_date:
            return results

        values = await self._collect(request_start, end_date, wanted)
        conflicting = 0
        for (day, currency), found in sorted(values.items()):
            if len(found) > 1:
                conflicting += 1
                continue
            base, quote, value = next(iter(found))
            results[currency].append((day, base, quote, value))
        if conflicting:
            logger.warning(f"CBK: {conflicting} day(s) with two different values for one currency dropped")
        return results

    async def _collect(self, request_start: date, end_date: date, wanted: set[str]) -> dict[tuple[date, str], set[tuple[str, str, Decimal]]]:
        """Every distinct value of each (day, currency) in the range, each table only over its own period, old first."""
        plan: list[tuple[str, date, date, date]] = []  # (table, first day asked, first day owned, last day owned)
        if request_start < CURRENT_FIRST_DAY:
            plan.append((OLD_TABLE, request_start, FIRST_DAY, date.fromordinal(CURRENT_FIRST_DAY.toordinal() - 1)))
        if end_date >= CURRENT_FIRST_DAY:
            plan.append((CURRENT_TABLE, max(request_start, CURRENT_FIRST_DAY), CURRENT_FIRST_DAY, date.max))

        values: dict[tuple[date, str], set[tuple[str, str, Decimal]]] = {}
        for index, (table, ask_from, owned_from, owned_to) in enumerate(plan):
            if index:
                await asyncio.sleep(self.PAUSE_SECONDS)
            for row in await self._get_table(table, ask_from):
                observation = self._observation(row)
                if observation is None:
                    continue
                day, currency, base, quote, value = observation
                if table == OLD_TABLE and day.weekday() >= 5:
                    continue  # the old table's weekend rows are copies of other days (D2)
                if currency in wanted and max(owned_from, request_start) <= day <= min(owned_to, end_date):
                    values.setdefault((day, currency), set()).add((base, quote, value))
        return values

    def _observation(self, row: object) -> tuple[date, str, str, str, Decimal] | None:
        """One table row as ``(day, CUR, base, quote, value)`` in the name's direction; None when it cannot be read."""
        if not isinstance(row, list) or len(row) < 3:
            return None
        mapped = CURRENCY_NAMES.get(str(row[1]).strip())
        if mapped is None:
            return None
        try:
            day = datetime.strptime(str(row[0]).strip(), "%d/%m/%Y").date()
            value = Decimal(str(row[2]).strip())
        except (ValueError, InvalidOperation):
            return None
        if not value.is_finite() or value <= 0:
            return None
        currency, kind = mapped
        if kind == "inverse":
            return day, currency, self.base_currency, currency, value
        if kind == "per_100":
            value = value / _HUNDRED
        return day, currency, currency, self.base_currency, value

    async def _get_table(self, table: str, ask_from: date) -> list:
        """The rows of ``table`` from ``ask_from`` (the server's lower bound), newest first; anything else is an error."""
        form = {"draw": "1", "start": "0", "length": str(PAGE_LENGTH), "order[0][column]": "0", "order[0][dir]": "desc"}
        for column in range(_COLUMNS[table]):
            form[f"columns[{column}][data]"] = str(column)
            form[f"columns[{column}][searchable]"] = "true"
            form[f"columns[{column}][orderable]"] = "true"
            form[f"columns[{column}][search][value]"] = ""
        form["columns[0][search][value]"] = f"{ask_from:%d/%m/%Y}|"
        try:
            async with httpx.AsyncClient(timeout=60.0, headers={"User-Agent": USER_AGENT}) as client:
                response = await client.post(AJAX_URL, params={"action": "get_wdtable", "table_id": table}, data=form)
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            logger.warning(f"CBK request failed for table {table}: {e}")
            raise FXServiceError(f"CBK API error for table {table}: {e}") from e

        body = response.text.strip()
        if not body:
            raise FXServiceError(f"CBK answer for table {table} is empty (the table may now ask for a form token, or the endpoint changed)")
        if body[:1] == "<":
            raise FXServiceError(f"CBK answer for table {table} is an HTML page, not the table's JSON (undocumented endpoint changed, or request refused)")
        try:
            data = json.loads(body)
        except ValueError:
            raise FXServiceError(f"CBK answer for table {table} is not JSON: first bytes {body[:40]!r}") from None
        rows = data.get("data") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise FXServiceError(f"CBK answer for table {table} has no data list (undocumented endpoint changed)")
        filtered = _as_int(data.get("recordsFiltered"))
        if filtered is not None and filtered > len(rows):
            # Rows come newest first: a cut answer would lose the oldest days silently
            raise FXServiceError(f"CBK answer for table {table} was cut at {len(rows)} of {filtered} rows (PAGE_LENGTH too small)")
        return rows


def _as_int(value: object) -> int | None:
    """``recordsFiltered`` as an integer (the bank sends a string); None when absent or not a number."""
    try:
        return int(str(value))
    except ValueError:
        return None
