"""
Bank of Korea (BOK) FX rate provider.

This provider reads the Bank of Korea's ECOS Open API (https://ecos.bok.or.kr/api/), table ``731Y001`` «Arbitraged
Rates of Major Currencies Against Won»: one series per currency, ``GET /StatisticSearch/{KEY}/json/en/{from_row}/
{to_row}/731Y001/D/{YYYYMMDD}/{YYYYMMDD}/{item}``. KRW is the base. The API needs a free key, which the administrator
asks the bank for and sets in the plugin settings. **The key travels in the URL path**: it is the API's format. So the
plugin never logs a URL or puts one in an error of its own, and the core masks the key in the errors and the log lines
of the call (``utils/runtime/secret_masking.py``).

Measured on 19/11/2026 with the public ``sample`` key (at most 10 rows per request, so no full download):

- 53 items (``StatisticItemList``): 43 current, 8 pre-euro currencies (ended 2001–2002) and two older CNY series; the 43
  current ones are served (``ITEMS``). USD and CNY are the «basic exchange rates»; the others are arbitraged rates, built
  by the bank from them.
- KRW per 1 unit, except JPY, IDR and VND, per 100 (the names say so for JPY only: IDR 7.32 and VND 5.21 KRW on
  18/11/2026). Two decimals: MNT (0.37 KRW) moves in steps of about 3%, ARS (0.86) of about 1%.
- USD from 1964-05-04 (``FIRST_DAY``); most of the others from 1970–1994, 22 of them only from 2015-01-02; CNY from
  2016-01-04 (``0000053``; the older ``0000027`` is not used).
- Errors come with HTTP 200: ``{"RESULT": {"CODE": "INFO-200"}}`` (no data), ``INFO-100`` (the key is refused),
  ``ERROR-602`` (too many calls), other ``ERROR-xxx``.
- Not measured (❔ until a real key, developer decision Q1): the largest page (``PAGE_ROWS`` 10 000 rows is assumed,
  with paging when ``list_total_count`` is larger), the time of a full history, the junk the series may hold.
"""

import asyncio
import contextvars
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXNotConfiguredError, FXProviderStartDate, FXRateLimitedError, FXRateProvider, FXServiceError, raise_if_fx_rate_limited, raise_longest_refusal
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingScope, SettingType

logger = get_logger(__name__)

API_ROOT = "https://ecos.bok.or.kr/api/StatisticSearch"
STAT_CODE = "731Y001"
#: The first day of the USD series.
FIRST_DAY = date(1964, 5, 4)
#: Rows asked per request; more pages are asked when ``list_total_count`` is larger.
PAGE_ROWS = 10000
#: The site's icon.
ICON_URL = "https://ecos.bok.or.kr/favicon.ico"

_ONE = Decimal(1)
_HUNDRED = Decimal(100)
#: ISO code → (the ECOS item, units per quote).
ITEMS: dict[str, tuple[str, Decimal]] = {
    "USD": ("0000001", _ONE),
    "CNY": ("0000053", _ONE),
    "JPY": ("0000002", _HUNDRED),
    "EUR": ("0000003", _ONE),
    "GBP": ("0000012", _ONE),
    "CAD": ("0000013", _ONE),
    "CHF": ("0000014", _ONE),
    "AUD": ("0000017", _ONE),
    "NZD": ("0000026", _ONE),
    "HKD": ("0000015", _ONE),
    "TWD": ("0000031", _ONE),
    "MNT": ("0000032", _ONE),
    "KZT": ("0000033", _ONE),
    "THB": ("0000028", _ONE),
    "SGD": ("0000024", _ONE),
    "IDR": ("0000029", _HUNDRED),
    "MYR": ("0000025", _ONE),
    "PHP": ("0000034", _ONE),
    "VND": ("0000035", _HUNDRED),
    "BND": ("0000036", _ONE),
    "INR": ("0000037", _ONE),
    "PKR": ("0000038", _ONE),
    "BDT": ("0000039", _ONE),
    "MXN": ("0000040", _ONE),
    "BRL": ("0000041", _ONE),
    "ARS": ("0000042", _ONE),
    "SEK": ("0000016", _ONE),
    "DKK": ("0000018", _ONE),
    "NOK": ("0000019", _ONE),
    "RUB": ("0000043", _ONE),
    "HUF": ("0000044", _ONE),
    "PLN": ("0000045", _ONE),
    "CZK": ("0000046", _ONE),
    "SAR": ("0000020", _ONE),
    "QAR": ("0000047", _ONE),
    "ILS": ("0000048", _ONE),
    "JOD": ("0000049", _ONE),
    "KWD": ("0000021", _ONE),
    "BHD": ("0000022", _ONE),
    "AED": ("0000023", _ONE),
    "TRY": ("0000050", _ONE),
    "ZAR": ("0000051", _ONE),
    "EGP": ("0000052", _ONE),
}
_CATALOGUE = sorted([*ITEMS, "KRW"])
#: The call's request pacing, shared by its parallel series (each call sets its own).
_PACER: contextvars.ContextVar["_Pacer"] = contextvars.ContextVar("bok_pacer")


class _SeriesFailed(Exception):
    """One currency's series could not be read: that currency is skipped, the others go on."""


class _NotAsked(Exception):
    """A request queued behind a refusal: never sent (the call fails as a whole)."""


class _KeyRefused(Exception):
    """The bank refused the API key (``INFO-100``): the whole call fails."""


class _Pacer:
    """``PAUSE_SECONDS`` before every request of a call but the first; nothing new starts after a refusal."""

    def __init__(self, pause: float) -> None:
        self.pause = pause
        self.lock = asyncio.Lock()
        self.started = 0
        self.refused = False

    async def wait(self, currency: str) -> None:
        async with self.lock:
            if self.refused:
                raise _NotAsked(currency)
            if self.started:
                await asyncio.sleep(self.pause)
            self.started += 1


@register_provider(FXProviderRegistry)
class BOKProvider(FXRateProvider):
    """
    Bank of Korea FX rate provider.

    Provides the Bank of Korea's daily rates of 43 currencies with KRW as base currency, KRW per unit (USD and CNY the
    basic rates, the others arbitraged). Data source: the ECOS Open API, one series per currency. Needs a key.

    Coverage: a fixed table of 43 currencies plus KRW.
    Update frequency: Korean business days.
    """

    #: Pause between two request starts of one call (D9).
    PAUSE_SECONDS = 0.3
    #: Series in flight at once (the SARB pattern).
    MAX_PARALLEL = 3

    settings_fields = (
        PluginSettingField(
            key="api_key",
            type=SettingType.STRING,
            scope=SettingScope.SYSTEM,
            secret=True,
            required=True,
            label="API key (ECOS)",
            description="The free key of the Bank of Korea ECOS Open API, asked for on the ECOS site.",
            label_key="pluginSettings.fx.BOK.label.api_key",
            description_key="pluginSettings.fx.BOK.description.api_key",
            missing_key="pluginSettings.fx.BOK.missing.api_key",
        ),
    )

    @property
    def code(self) -> str:
        return "BOK"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Bank of Korea"

    @property
    def icon(self) -> str | None:
        return ICON_URL

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/bok/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Bank of Korea — daily rates of 43 currencies against the Korean won (KRW), among them TWD, KZT, MNT, VND, PKR and BDT. Korean business days, history from 1964 for USD. Needs a free API key from the bank. Source: Bank of Korea (ECOS).",
            "it": "Bank of Korea — tassi giornalieri di 43 valute contro il won coreano (KRW), tra cui TWD, KZT, MNT, VND, PKR e BDT. Giorni lavorativi coreani, storia dal 1964 per USD. Serve una chiave API gratuita della banca. Fonte: Bank of Korea (ECOS).",
            "fr": "Bank of Korea — taux quotidiens de 43 devises contre le won coréen (KRW), dont TWD, KZT, MNT, VND, PKR et BDT. Jours ouvrables coréens, historique depuis 1964 pour l'USD. Nécessite une clé API gratuite de la banque. Source : Bank of Korea (ECOS).",
            "es": "Bank of Korea — tipos diarios de 43 monedas contra el won surcoreano (KRW), entre ellas TWD, KZT, MNT, VND, PKR y BDT. Días hábiles coreanos, historial desde 1964 para el USD. Requiere una clave API gratuita del banco. Fuente: Bank of Korea (ECOS).",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "USD and CNY are the Bank of Korea's basic rates; the other currencies are arbitraged rates the bank builds from them. Rates have two decimals, which is coarse for small currencies: MNT (0.37 KRW) moves in steps of about 3%, ARS of about 1%. 22 currencies start only in 2015, CNY in 2016.",
            "it": "USD e CNY sono i tassi base della Bank of Korea; le altre valute sono tassi incrociati che la banca ricava da questi. I tassi hanno due decimali, pochi per le valute piccole: MNT (0,37 KRW) si muove a passi di circa il 3%, ARS di circa l'1%. 22 valute iniziano solo nel 2015, CNY nel 2016.",
            "fr": "USD et CNY sont les taux de base de la Bank of Korea ; les autres devises sont des taux croisés que la banque en déduit. Les taux ont deux décimales, peu pour les petites devises : le MNT (0,37 KRW) varie par pas d'environ 3 %, l'ARS d'environ 1 %. 22 devises ne commencent qu'en 2015, le CNY en 2016.",
            "es": "USD y CNY son los tipos básicos del Bank of Korea; las demás monedas son tipos cruzados que el banco obtiene de ellos. Los tipos tienen dos decimales, pocos para las monedas pequeñas: el MNT (0,37 KRW) se mueve en pasos de alrededor del 3 %, el ARS de alrededor del 1 %. 22 monedas empiezan solo en 2015, el CNY en 2016.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # Two decimals make small currencies coarse (MNT ~3%): a limit that can mislead (lane 75)
        return "warning"

    @property
    def base_currency(self) -> str:
        return "KRW"

    @property
    def test_currencies(self) -> list[str]:
        return ["KRW", "USD", "EUR", "JPY", "CNY"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(_CATALOGUE)

    async def get_supported_currencies(self) -> list[str]:
        """The fixed table, plus KRW: no request and no key."""
        return list(_CATALOGUE)

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch each asked currency's series, at most ``MAX_PARALLEL`` at once: ``(day, CUR, 'KRW', KRW per 1 CUR)``.

        Every value keeps its day (D2). A row with an unreadable day or a value that is not positive is skipped (X-R50);
        a day with two different values is dropped. A currency whose series cannot be read is skipped with a warning;
        when every asked currency fails the call fails.

        Raises:
            ValueError: base_currency is neither None nor KRW
            FXNotConfiguredError: no API key is set
            FXRateLimitedError: the bank refused for too many requests (HTTP 429 or ``ERROR-602``)
            FXServiceError: the key was refused, or every asked series failed
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"BOK provider only supports KRW as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        wanted = [currency for currency in asked if currency in ITEMS]
        if not wanted or request_start > end_date:
            return results

        if not self.settings.secret("api_key"):
            raise FXNotConfiguredError(self.provider_code, ["api_key"])

        outcomes = await self._fetch_all(wanted, request_start, end_date)
        raise_longest_refusal(outcomes)  # a refusal for too many requests: the whole call is refused, as in SARB
        refused = next((outcome for outcome in outcomes if isinstance(outcome, _KeyRefused)), None)
        if refused is not None:
            raise FXServiceError("Bank of Korea refused the API key: check the BOK api_key in the instance's plugin settings") from refused

        failures: list[str] = []
        for currency, outcome in zip(wanted, outcomes, strict=True):
            if isinstance(outcome, _SeriesFailed):
                logger.warning(f"BOK fetch failed for {currency}, skipping: {outcome}")
                failures.append(f"{currency}: {outcome}")
            elif isinstance(outcome, BaseException):
                raise outcome
            else:
                results[currency] = self._series(currency, outcome, request_start, end_date)
        if len(failures) == len(wanted):
            raise FXServiceError(f"Bank of Korea API error for every asked series: {'; '.join(failures)}")
        return results

    def _series(self, currency: str, values: list[tuple[date, Decimal]], start: date, end: date) -> list[tuple[date, str, str, Decimal]]:
        """One currency's values in the range, ascending; a day with two different values is dropped."""
        by_day: dict[date, set[Decimal]] = {}
        for day, value in values:
            if start <= day <= end:
                by_day.setdefault(day, set()).add(value)
        conflicting = [day for day, found in by_day.items() if len(found) > 1]
        if conflicting:
            logger.warning(f"BOK: {len(conflicting)} day(s) with two different values for {currency} dropped")
        return [(day, currency, self.base_currency, next(iter(found))) for day, found in sorted(by_day.items()) if len(found) == 1]

    async def _fetch_all(self, wanted: list[str], start: date, end: date) -> list[object]:
        """Each currency's values or exception, in ``wanted`` order: at most ``MAX_PARALLEL`` series at once; after a
        refusal (too many requests, or the key) the requests not sent yet are never sent."""
        in_flight = asyncio.Semaphore(self.MAX_PARALLEL)
        pacer = _Pacer(self.PAUSE_SECONDS)
        _PACER.set(pacer)

        async def fetch(currency: str) -> list[tuple[date, Decimal]]:
            async with in_flight:
                try:
                    return await self._fetch_one(currency, start, end)
                except (FXRateLimitedError, _KeyRefused):
                    pacer.refused = True
                    raise

        return await asyncio.gather(*(fetch(currency) for currency in wanted), return_exceptions=True)

    async def _fetch_one(self, currency: str, start: date, end: date) -> list[tuple[date, Decimal]]:
        """One currency's ``(day, KRW per 1 unit)`` values, page after page until ``list_total_count``."""
        item, units = ITEMS[currency]
        key = self.settings.secret("api_key") or ""
        pacer = _PACER.get(None) or _Pacer(self.PAUSE_SECONDS)
        values: list[tuple[date, Decimal]] = []
        first_row = 1
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                await pacer.wait(currency)
                rows, total = await self._page(client, key, item, start, end, first_row)
                values.extend(value for value in (_value(row, item, units) for row in rows) if value is not None)
                first_row += PAGE_ROWS
                if not rows or first_row > total:
                    return values

    async def _page(self, client: httpx.AsyncClient, key: str, item: str, start: date, end: date, first_row: int) -> tuple[list, int]:
        """One page: its rows and ``list_total_count``. The URL holds the key: it never goes into a message here."""
        url = f"{API_ROOT}/{key}/json/en/{first_row}/{first_row + PAGE_ROWS - 1}/{STAT_CODE}/D/{start:%Y%m%d}/{end:%Y%m%d}/{item}"
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            raise _SeriesFailed(f"HTTP {e.response.status_code} for item {item}") from e
        except httpx.HTTPError as e:
            raise _SeriesFailed(f"request failed for item {item} ({type(e).__name__})") from e
        body = response.text.strip()
        if body[:1] == "<":
            raise _SeriesFailed(f"item {item}: the answer is an HTML page, not the ECOS JSON")
        try:
            data = json.loads(body)
        except ValueError:
            raise _SeriesFailed(f"item {item}: the answer is not JSON") from None
        return self._rows(data, item)

    def _rows(self, data: object, item: str) -> tuple[list, int]:
        """The rows of a page and its total, or the meaning of a ``RESULT`` code."""
        if isinstance(data, dict) and isinstance(data.get("RESULT"), dict):
            code = str(data["RESULT"].get("CODE"))
            if code == "INFO-200":
                return [], 0
            if code == "INFO-100":
                raise _KeyRefused()
            if code == "ERROR-602":
                raise FXRateLimitedError(f"{self.provider_code}: too many requests ({code})")
            raise _SeriesFailed(f"item {item}: {code} {data['RESULT'].get('MESSAGE')}")
        search = data.get("StatisticSearch") if isinstance(data, dict) else None
        rows = search.get("row") if isinstance(search, dict) else None
        if not isinstance(rows, list):
            raise _SeriesFailed(f"item {item}: the answer has no StatisticSearch rows (the API changed)")
        try:
            total = int(search.get("list_total_count") or 0)
        except (TypeError, ValueError):
            total = 0
        return rows, total


def _value(row: object, item: str, units: Decimal) -> tuple[date, Decimal] | None:
    """One row as ``(day, KRW per 1 unit)``; None for another item, an unreadable day or a value not positive."""
    if not isinstance(row, dict) or str(row.get("ITEM_CODE1")) != item:
        return None
    try:
        day = datetime.strptime(str(row.get("TIME")), "%Y%m%d").date()
        value = Decimal(str(row.get("DATA_VALUE")).strip())
    except (ValueError, InvalidOperation):
        return None
    if not value.is_finite() or value <= 0:
        return None
    return day, value / units
