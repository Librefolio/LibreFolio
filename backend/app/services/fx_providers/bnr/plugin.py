"""
National Bank of Romania (BNR) FX rate provider.

This provider reads the BNR's reference rates from its XML files on ``curs.bnr.ro``: the last ten business days
(``nbrfxrates10days.xml``) and one file per year (``files/xml/years/nbrfxrates{YYYY}.xml``). RON is the base.

The host moved in 2026: ``www.bnr.ro/files/xml/...`` now answers 302 to the home page (19/11/2026). The namespace of
the files changes (``https://www.bnr.ro/xsd`` in the recent ones, ``http://www.bnr.ro/xsd`` in older years): the parser
reads local tag names only. Terms: the «Disclaimer & Copyright» page renders its text with a script, so no terms were
found in the page (❔). Developer decision D1 (lane 75): offered for a self-hosted instance that stores the rates for its
owner; the description names the source.

Measured on 19/11/2026:

- Year files from 2005 (2005 already in RON: USD 2.9027 on 03/01/2005); earlier years and future years answer 502.
  ~200–350 KB per year; 5 524 business days from 03/01/2005, no weekend date.
- 40 codes in all: XAU (gold) and XDR (an open question of lane 75) are not served. Legacy currencies are served for
  their history, as ECB does: SKK until 2008, HRK until 2022, BGN until 2025.
- ``multiplier="100"`` for HUF, IDR, ISK, JPY, KRW; a missing value is ``-`` (1 093 cells, mostly BGN, RUB and SKK in
  2007). No conflicting duplicate.
- The RUB rate is the BNR's own (Q3 (b)), not the Central Bank of Russia's.
- Budget: a short sync is one request (the ten-day file); ``"min"`` is one file per year since 2005 (22 files).
"""

import asyncio
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

RECENT_URL = "https://curs.bnr.ro/nbrfxrates10days.xml"
YEAR_URL = "https://curs.bnr.ro/files/xml/years/nbrfxrates{year}.xml"
#: The first year with a file on the host.
FIRST_DAY = date(2005, 1, 1)
#: A range of at most this many days asks the ten-day file first.
RECENT_SPAN_DAYS = 14
#: The site's icon.
ICON_URL = "https://www.bnr.ro/favicon.ico"
#: An honest, constant User-Agent, the one BOE sends.
USER_AGENT = "Mozilla/5.0 (compatible; LibreFolio/1.0; +https://github.com/librefolio)"

#: The currencies served; XAU (gold) and XDR are in the files and are not.
CURRENCIES = ("AED", "AUD", "BGN", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EGP", "EUR", "GBP", "HKD", "HRK", "HUF", "IDR", "ILS", "INR", "ISK", "JPY", "KRW", "MDL", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN", "RSD", "RUB", "SEK", "SGD", "SKK", "THB", "TRY", "UAH", "USD", "ZAR")
_CATALOGUE = sorted([*CURRENCIES, "RON"])


def _local(tag: str) -> str:
    """A tag without its namespace: ``{https://www.bnr.ro/xsd}Cube`` → ``Cube``."""
    return tag.rsplit("}", 1)[-1]


@register_provider(FXProviderRegistry)
class BNRProvider(FXRateProvider):
    """
    National Bank of Romania FX rate provider.

    Provides the BNR's daily reference rates of 38 currencies with RON as base currency, RON per unit.
    Data source: the BNR's XML files (the last ten days, one file per year).

    Coverage: a fixed list, 38 currencies plus RON.
    Update frequency: Romanian business days.
    """

    #: Pause between two requests of one call (D9).
    PAUSE_SECONDS = 0.3

    @property
    def code(self) -> str:
        return "BNR"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "National Bank of Romania"

    @property
    def icon(self) -> str | None:
        return ICON_URL

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/bnr/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "National Bank of Romania — daily reference rates of 38 currencies against the Romanian leu (RON), among them MDL, UAH, RSD, EGP, AED and RUB. Romanian business days, history from 2005. Source: National Bank of Romania.",
            "it": "National Bank of Romania — tassi di riferimento giornalieri di 38 valute contro il leu romeno (RON), tra cui MDL, UAH, RSD, EGP, AED e RUB. Giorni lavorativi rumeni, storia dal 2005. Fonte: National Bank of Romania.",
            "fr": "National Bank of Romania — taux de référence quotidiens de 38 devises contre le leu roumain (RON), dont MDL, UAH, RSD, EGP, AED et RUB. Jours ouvrables roumains, historique depuis 2005. Source : National Bank of Romania.",
            "es": "National Bank of Romania — tipos de referencia diarios de 38 monedas contra el leu rumano (RON), entre ellas MDL, UAH, RSD, EGP, AED y RUB. Días hábiles rumanos, historial desde 2005. Fuente: National Bank of Romania.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "Some currencies start later (AED, BRL, CNY and others in 2009; HKD, IDR, ILS and others in September 2024), and the lev (BGN), the kuna (HRK) and the Slovak koruna (SKK) end when their countries adopted the euro. The RUB rate is the one the National Bank of Romania publishes, not the Central Bank of Russia's.",
            "it": "Alcune valute iniziano più tardi (AED, BRL, CNY e altre nel 2009; HKD, IDR, ILS e altre a settembre 2024), e il lev (BGN), la kuna (HRK) e la corona slovacca (SKK) finiscono quando i loro paesi hanno adottato l'euro. Il tasso del RUB è quello che pubblica la Banca nazionale di Romania, non quello della Banca centrale russa.",
            "fr": "Certaines devises commencent plus tard (AED, BRL, CNY et d'autres en 2009 ; HKD, IDR, ILS et d'autres en septembre 2024), et le lev (BGN), la kuna (HRK) et la couronne slovaque (SKK) s'arrêtent quand leurs pays ont adopté l'euro. Le taux du RUB est celui que publie la Banque nationale de Roumanie, pas celui de la Banque centrale de Russie.",
            "es": "Algunas monedas empiezan más tarde (AED, BRL, CNY y otras en 2009; HKD, IDR, ILS y otras en septiembre de 2024), y el lev (BGN), la kuna (HRK) y la corona eslovaca (SKK) terminan cuando sus países adoptaron el euro. El tipo del RUB es el que publica el Banco Nacional de Rumanía, no el del Banco Central de Rusia.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # Facts worth knowing (later starts, euro adoptions, the BNR's RUB), not a data limit that misleads (lane 75)
        return "info"

    @property
    def base_currency(self) -> str:
        return "RON"

    @property
    def test_currencies(self) -> list[str]:
        return ["RON", "EUR", "USD", "HUF", "MDL"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(_CATALOGUE)

    async def get_supported_currencies(self) -> list[str]:
        """The 38 currencies, plus RON: no request."""
        return list(_CATALOGUE)

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch the asked currencies: the ten-day file for a short range it covers, otherwise one file per year.
        ``(day, CUR, 'RON', RON per 1 CUR)``, the ``multiplier`` divided out.

        Every value keeps its day (D2). A missing value (``-``), a value that is not positive or a day that cannot be
        read is skipped (X-R50); a day with two different values for a currency is dropped.

        Raises:
            ValueError: base_currency is neither None nor RON
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: a request failed, a year file is missing, or an answer is not the BNR's XML
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"BNR provider only supports RON as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        wanted = set(asked) & set(CURRENCIES)
        if not wanted or request_start > end_date:
            return results

        values: dict[tuple[date, str], set[Decimal]] = {}
        for day, rates in await self._fetch_cubes(request_start, end_date):
            if request_start <= day <= end_date:
                for currency, value in rates:
                    if currency in wanted:
                        values.setdefault((day, currency), set()).add(value)

        conflicting = 0
        for (day, currency), found in sorted(values.items()):
            if len(found) > 1:
                conflicting += 1
                continue
            results[currency].append((day, currency, self.base_currency, next(iter(found))))
        if conflicting:
            logger.warning(f"BNR: {conflicting} day(s) with two different values for one currency dropped")
        return results

    async def _fetch_cubes(self, start: date, end: date) -> list[tuple[date, list[tuple[str, Decimal]]]]:
        """The ten-day file when the range is short and the file reaches its start; otherwise the year files, which hold
        every day up to today and replace it."""
        async with httpx.AsyncClient(timeout=60.0, headers={"User-Agent": USER_AGENT}) as client:
            requests = 0
            if (end - start).days <= RECENT_SPAN_DAYS:
                recent = _cubes(await self._get(client, RECENT_URL, "the ten-day file"))
                requests += 1
                if recent and min(day for day, _ in recent) <= start:
                    return recent
            cubes: list[tuple[date, list[tuple[str, Decimal]]]] = []
            for year in range(start.year, end.year + 1):
                if requests:
                    await asyncio.sleep(self.PAUSE_SECONDS)
                cubes.extend(_cubes(await self._get(client, YEAR_URL.format(year=year), f"the {year} file")))
                requests += 1
        return cubes

    async def _get(self, client: httpx.AsyncClient, url: str, what: str) -> bytes:
        """One file; 429 → rate limit, any other failure (a missing year answers 502) → FXServiceError."""
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            logger.warning(f"BNR request failed for {what}: {e}")
            raise FXServiceError(f"BNR API error for {what}: {e}") from e
        return response.content


def _cubes(body: bytes) -> list[tuple[date, list[tuple[str, Decimal]]]]:
    """Every ``Cube`` of a BNR file as ``(day, [(currency, RON per 1 unit)])``; anything else is an error."""
    if body.lstrip()[:1] != b"<":
        raise FXServiceError(f"BNR answer is not XML: first bytes {body[:40]!r}")
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        raise FXServiceError(f"BNR answer is not XML ({e}): the host or the format changed") from e
    if _local(root.tag) != "DataSet":
        raise FXServiceError(f"BNR answer is not the reference rates XML (root {_local(root.tag)!r}): the host or the format changed")
    cubes: list[tuple[date, list[tuple[str, Decimal]]]] = []
    for cube in root.iter():
        if _local(cube.tag) != "Cube":
            continue
        try:
            day = date.fromisoformat(cube.get("date") or "")
        except ValueError:
            continue
        cubes.append((day, [rate for rate in (_rate(element) for element in cube if _local(element.tag) == "Rate") if rate is not None]))
    return cubes


def _rate(element: ET.Element) -> tuple[str, Decimal] | None:
    """One ``Rate`` as ``(currency, RON per 1 unit)``; None for ``-``, an empty text or a value that is not positive."""
    try:
        value = Decimal((element.text or "").strip())
        units = Decimal(element.get("multiplier") or "1")
    except InvalidOperation:
        return None
    if not value.is_finite() or value <= 0 or units <= 0:
        return None
    return str(element.get("currency") or ""), value / units
