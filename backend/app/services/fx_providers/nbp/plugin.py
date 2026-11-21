"""
Narodowy Bank Polski (NBP) FX rate provider.

This provider reads the NBP's average exchange rates from its documented REST API (https://api.nbp.pl/en.html):
``GET /api/exchangerates/tables/{A|B}/{from}/{to}/?format=json``, at most 93 days per request. Table **A** is daily (31
currencies served), table **B** is weekly (116 more currencies, the rarer ones): developer decision D3 accepts a weekly
source with a note. PLN is the base. The ``mid`` rate is used.

Terms: the API documentation reads only «All rights reserved»; the instructions page on nbp.pl is behind an anti-bot
wall. Developer decision D1 (lane 75): offered for a self-hosted instance that stores the rates for its owner; the
description names the source.

Measured on 19/11/2026:

- Both tables from 02/01/2002. Table B is weekly (mostly Wednesday; every two weeks in 2002). Many table-A currencies
  were in table B before moving to A (PHP, CNY, BRL… on 2008-01-02, INR, ILS on 2011-07-27, CLP on 2011-08-31): for an
  A currency the provider also reads table B up to ``B_HISTORY_UNTIL``, so their history is weekly before the move.
- XDR (the IMF's SDR) is in table A and is served (Q7 of lane 75).
- No conflicting duplicate; A and B never disagree on a day both publish.
- Scale changes under one code in table B: VES was redenominated (÷10⁶) on 01/10/2021 and the NBP switched on
  13/10/2021: older values are multiplied by 10⁶, as BCB does. SYP changed scale on 07/01/2026 (about 1:100, factor
  not certain): it is served from that day. LRD and IQD (2004) and IRR (2026) jump when the NBP moved from an official
  parity to a market rate: they stay as published.
- A range with no table answers 404 «Brak danych» (no data).
- Budget: a 14-day sync is one request per table; ``"min"`` is 98 requests per table (table B only to 2011 when no B
  currency is asked), the two tables at once, ~40 s.
"""

import asyncio
import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

TABLES_URL = "https://api.nbp.pl/api/exchangerates/tables"
FIRST_DAY = date(2002, 1, 2)
#: Days per request: the API's limit.
WINDOW_DAYS = 93
#: The site's icon.
ICON_URL = "https://nbp.pl/favicon.ico"
#: An honest, constant User-Agent, the one BOE sends.
USER_AGENT = "Mozilla/5.0 (compatible; LibreFolio/1.0; +https://github.com/librefolio)"

#: Table A, daily (the IMF's SDR, XDR, included).
A_CURRENCIES = tuple("AUD BRL CAD CHF CLP CNY CZK DKK EUR GBP HKD HUF IDR ILS INR ISK JPY KRW MXN MYR NOK NZD PHP RON SEK SGD THB TRY UAH USD XDR ZAR".split())
#: Table B, weekly.
B_CURRENCIES = tuple(
    "AED AFN ALL AMD AOA ARS AWG AZN BAM BBD BDT BHD BIF BND BOB BSD BWP BYN BZD CDF COP CRC CUP CVE DJF DOP DZD EGP ERN ETB FJD GEL GHS GIP GMD GNF GTQ GYD HNL HTG "
    "IQD IRR JMD JOD KES KGS KHR KMF KWD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MZN NAD NGN NIO NPR OMR PAB PEN PGK PKR PYG QAR RSD "
    "RUB RWF SAR SBD SCR SDG SLE SOS SRD SSP STN SVC SYP SZL TJS TMT TND TOP TTD TWD TZS UGX UYU UZS VES VND VUV WST XAF XCD XCG XOF XPF YER ZMW ZWG".split()
)
#: Table-A currencies have table-B rows until this day (the last move from B to A, CLP in August 2011).
B_HISTORY_UNTIL = date(2011, 8, 31)
#: A currency served only from a day on: its scale changed under the same code by an uncertain factor.
SERIES_FROM = {"SYP": date(2026, 1, 7)}
#: VES before this day is in old bolívares (÷10⁶ on 01/10/2021, published by the NBP from 13/10/2021).
VES_NEW_FROM = date(2021, 10, 13)
VES_FACTOR = Decimal(10**6)
_CATALOGUE = sorted([*A_CURRENCIES, *B_CURRENCIES, "PLN"])


@register_provider(FXProviderRegistry)
class NBPProvider(FXRateProvider):
    """
    Narodowy Bank Polski FX rate provider.

    Provides the NBP's average exchange rates of 148 currencies with PLN as base currency, PLN per unit: 32 daily
    (table A) and 116 weekly (table B). Data source: the documented NBP API, 93 days per request.

    Coverage: a fixed list, 148 currencies plus PLN.
    Update frequency: Polish business days (table A), weekly (table B).
    """

    #: Pause between two requests of one table (D9).
    PAUSE_SECONDS = 0.3

    @property
    def code(self) -> str:
        return "NBP"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Narodowy Bank Polski"

    @property
    def icon(self) -> str | None:
        return ICON_URL

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/nbp/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Narodowy Bank Polski — average exchange rates of 148 currencies against the Polish złoty (PLN): 32 daily, and 116 weekly, among them most currencies of Africa, Asia and Latin America. History from 2002. Source: Narodowy Bank Polski.",
            "it": "Narodowy Bank Polski — tassi di cambio medi di 148 valute contro lo złoty polacco (PLN): 32 giornalieri e 116 settimanali, tra cui la maggior parte delle valute di Africa, Asia e America latina. Storia dal 2002. Fonte: Narodowy Bank Polski.",
            "fr": "Narodowy Bank Polski — taux de change moyens de 148 devises contre le złoty polonais (PLN) : 32 quotidiens et 116 hebdomadaires, dont la plupart des devises d'Afrique, d'Asie et d'Amérique latine. Historique depuis 2002. Source : Narodowy Bank Polski.",
            "es": "Narodowy Bank Polski — tipos de cambio medios de 148 monedas contra el esloti polaco (PLN): 32 diarios y 116 semanales, entre ellos la mayoría de las monedas de África, Asia y América Latina. Historial desde 2002. Fuente: Narodowy Bank Polski.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "116 of the NBP's currencies are published once a week (usually on Wednesday), not every day: between two publications the last rate is the only one. Some currencies that are daily today were weekly before 2008 or 2011. A few rates jump when the NBP moved from an official parity to a market rate (the Liberian dollar and the Iraqi dinar in 2004, the Iranian rial in 2026). The Syrian pound starts in January 2026, when its scale changed. The RUB rate is the one the NBP publishes, not the Central Bank of Russia's.",
            "it": "116 valute della NBP sono pubblicate una volta alla settimana (di solito il mercoledì), non ogni giorno: fra due pubblicazioni c'è solo l'ultimo tasso. Alcune valute oggi giornaliere erano settimanali prima del 2008 o del 2011. Alcuni tassi saltano quando la NBP è passata da una parità ufficiale a un tasso di mercato (il dollaro liberiano e il dinaro iracheno nel 2004, il rial iraniano nel 2026). La lira siriana parte da gennaio 2026, quando è cambiata la sua scala. Il tasso del RUB è quello che pubblica la NBP, non quello della Banca centrale russa.",
            "fr": "116 devises de la NBP sont publiées une fois par semaine (en général le mercredi), pas chaque jour : entre deux publications, seul le dernier taux existe. Certaines devises quotidiennes aujourd'hui étaient hebdomadaires avant 2008 ou 2011. Quelques taux sautent quand la NBP est passée d'une parité officielle à un taux de marché (le dollar libérien et le dinar irakien en 2004, le rial iranien en 2026). La livre syrienne commence en janvier 2026, quand son échelle a changé. Le taux du RUB est celui que publie la NBP, pas celui de la Banque centrale de Russie.",
            "es": "116 monedas del NBP se publican una vez por semana (normalmente el miércoles), no cada día: entre dos publicaciones solo existe el último tipo. Algunas monedas hoy diarias eran semanales antes de 2008 o 2011. Algunos tipos saltan cuando el NBP pasó de una paridad oficial a un tipo de mercado (el dólar liberiano y el dinar iraquí en 2004, el rial iraní en 2026). La libra siria empieza en enero de 2026, cuando cambió su escala. El tipo del RUB es el que publica el NBP, no el del Banco Central de Rusia.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # Weekly rates for 116 currencies (D3) and parity jumps: limits that can mislead (lane 75)
        return "warning"

    @property
    def base_currency(self) -> str:
        return "PLN"

    @property
    def test_currencies(self) -> list[str]:
        return ["PLN", "EUR", "USD", "CHF", "KES"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(_CATALOGUE)

    async def get_supported_currencies(self) -> list[str]:
        """The 148 currencies of tables A and B, plus PLN: no request."""
        return list(_CATALOGUE)

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch the asked currencies from tables A and/or B, 93 days per request, the two tables at once:
        ``(day, CUR, 'PLN', PLN per 1 CUR)``, the day being the table's ``effectiveDate``.

        Every value keeps its day (D2). A rate that is not a positive number, or a day that cannot be read, is skipped
        (X-R50); a day where a currency has two different values is dropped. A failure in either table fails the call.

        Raises:
            ValueError: base_currency is neither None nor PLN
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: a request failed, or an answer is not the NBP's JSON
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"NBP provider only supports PLN as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        wanted = set(asked) & set(_CATALOGUE)
        if not wanted or request_start > end_date:
            return results

        answers = await asyncio.gather(*(self._table(table, request_start, last) for table, last in _tables(wanted, request_start, end_date)))

        values: dict[tuple[date, str], set[Decimal]] = {}
        for day, currency, value in (observation for answer in answers for observation in answer):
            if currency in wanted and request_start <= day <= end_date and day >= SERIES_FROM.get(currency, FIRST_DAY):
                values.setdefault((day, currency), set()).add(value)

        conflicting = 0
        for (day, currency), found in sorted(values.items()):
            if len(found) > 1:
                conflicting += 1
                continue
            results[currency].append((day, currency, self.base_currency, next(iter(found))))
        if conflicting:
            logger.warning(f"NBP: {conflicting} day(s) with two different values for one currency dropped")
        return results

    async def _table(self, table: str, start: date, end: date) -> list[tuple[date, str, Decimal]]:
        """Every ``(day, CUR, mid)`` of one table over the range, one request per 93-day window, oldest first."""
        observations: list[tuple[date, str, Decimal]] = []
        async with httpx.AsyncClient(timeout=60.0, headers={"User-Agent": USER_AGENT}) as client:
            window_start = start
            while window_start <= end:
                window_end = min(end, window_start + timedelta(days=WINDOW_DAYS - 1))
                if window_start > start:
                    await asyncio.sleep(self.PAUSE_SECONDS)
                observations.extend(_observations(await self._get(client, table, window_start, window_end)))
                window_start = window_end + timedelta(days=1)
        return observations

    async def _get(self, client: httpx.AsyncClient, table: str, start: date, end: date) -> list:
        """One window of one table; ``[]`` for the API's «no data» 404; anything else that is not a list is an error."""
        try:
            response = await client.get(f"{TABLES_URL}/{table}/{start.isoformat()}/{end.isoformat()}/", params={"format": "json"})
            if response.status_code == 404 and "Brak danych" in response.text:
                return []
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            detail = e.response.text.strip()[:120] if isinstance(e, httpx.HTTPStatusError) else str(e)
            logger.warning(f"NBP request failed for table {table} {start}..{end}: {detail}")
            raise FXServiceError(f"NBP API error for table {table} {start}..{end}: {detail}") from e
        body = response.text.strip()
        if body[:1] == "<":
            raise FXServiceError(f"NBP answer for table {table} is an HTML page, not the API's JSON")
        try:
            data = json.loads(body, parse_float=Decimal)
        except ValueError:
            raise FXServiceError(f"NBP answer for table {table} is not JSON: first bytes {body[:40]!r}") from None
        if not isinstance(data, list):
            raise FXServiceError(f"NBP answer for table {table} is not a list of tables (the API changed)")
        return data


def _tables(wanted: set[str], start: date, end: date) -> list[tuple[str, date]]:
    """The tables to read, each with its last day: A for the A currencies; B for the B currencies, or only up to
    ``B_HISTORY_UNTIL`` for the weekly history of the A currencies."""
    tables: list[tuple[str, date]] = []
    if wanted & set(A_CURRENCIES):
        tables.append(("A", end))
    if wanted & set(B_CURRENCIES):
        tables.append(("B", end))
    elif start <= B_HISTORY_UNTIL:
        tables.append(("B", min(end, B_HISTORY_UNTIL)))
    return tables


def _observations(tables: list) -> list[tuple[date, str, Decimal]]:
    """Every rate of the tables as ``(effectiveDate, code, mid)``; VES before ``VES_NEW_FROM`` in new bolívares."""
    observations: list[tuple[date, str, Decimal]] = []
    for table in tables:
        if not isinstance(table, dict):
            continue
        try:
            day = date.fromisoformat(str(table.get("effectiveDate")))
        except ValueError:
            continue
        for rate in table.get("rates") or []:
            value = _positive(rate.get("mid")) if isinstance(rate, dict) else None
            if value is None:
                continue
            code = str(rate.get("code"))
            if code == "VES" and day < VES_NEW_FROM:
                value = value * VES_FACTOR
            observations.append((day, code, value))
    return observations


def _positive(raw: object) -> Decimal | None:
    """A rate as a positive Decimal; None for anything else."""
    try:
        value = Decimal(str(raw))
    except InvalidOperation:
        return None
    return value if value.is_finite() and value > 0 else None
