"""
Banco Central de la República Argentina (BCRA) FX rate provider.

This provider reads the BCRA's «Estadísticas Cambiarias v1.0» REST API (documented: OpenAPI in the bank's API catalogue,
https://www.bcra.gob.ar/BCRAyVos/catalogo-de-APIs-banco-central.asp): one series per currency,
``GET /Cotizaciones/{code}?fechadesde=…&fechahasta=…&limit=1000``. ARS is the base of the provider.

Terms (https://www.bcra.gob.ar/aviso-legal/): reuse «con fines informativos, educativos o académicos», citing «Banco
Central de la República Argentina»; no use «con fines comerciales, publicitarios o de campaña sin autorización
previa». Developer decision Q2 (b), 19/11/2026: the provider stays for a self-hosted instance, with a note on the terms,
and the paid cloud turns it off (``LIBREFOLIO_FX_PROVIDERS_ENABLED``). The description cites the bank. The bank may
change or suspend the API without notice.

Measured on 19/11/2026:

- **USD is the reference rate of Comunicación A 3500** (code ``REF``), from 04/03/2002; its method changed on
  01/01/2026 (weighted averages of actual trades instead of a survey of quotes, Com. A 8359). The API also has a «USD»
  row (``DOLAR E.E.U.U.``, definition not documented), which is not served.
- **The other currencies** are the bank's ``tipoCotizacion``, ARS per unit, which the bank builds on its «USD» row
  times the currency's parity to the dollar (``tipoPase``), not on REF. The «USD» row and REF differ by up to 14.9% in
  2002, 6.4% in 2018, 5.7% in 2023, 4.1% in 2025, under 1% in most other years. To be reviewed with the developer.
- Non-ISO codes: ``REF`` → USD, ``MXP`` → MXN, ``VND`` per 1 000 units. XDR (``DEG``, the IMF's SDR) is served like
  the other currencies (Q7 of lane 75). Not served: XAU and XAG (no ARS value), CNH (not ISO), VEB (three
  redenominations under one code), the legacy ATS, DEM, ESP, ITL.
- Duplicates: a date can carry two records (``count`` counts records, not dates); five REF days have two different
  values (2017-09-06: 17.2183 and 37.6917): such a day is dropped.
- Values have six decimals: small ones are coarse in the early years (COP 0.00106 ARS in 2003).
- ``limit`` is between 10 and 1 000; a window of ``WINDOW_DAYS`` (about three years, ~760 records) fits one page.
- An empty range answers 200 with ``count`` 0. Once, four consecutive windows of REF answered empty and the same
  windows answered their rows a minute later: an empty window between two windows with rows fails that currency.
- Time: ~0.5–1.7 s per window. A series from 2002 is 9 windows, ~10–15 s; three currencies at once take about the
  time of one (8.0 s against 18.4 s sequential for 4 windows each).
"""

import asyncio
import contextvars
import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateLimitedError, FXRateProvider, FXServiceError, raise_if_fx_rate_limited, raise_longest_refusal
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

BASE_URL = "https://api.bcra.gob.ar/estadisticascambiarias/v1.0"
#: The first day of REF (Comunicación A 3500), the series USD is read from.
FIRST_DAY = date(2002, 3, 4)
#: Days asked per request: about three years, ~760 records, under the page limit.
WINDOW_DAYS = 1095
#: Records per page (the API accepts 10 to 1 000).
PAGE_LIMIT = 1000
#: An honest, constant User-Agent, the one BOE sends.
USER_AGENT = "Mozilla/5.0 (compatible; LibreFolio/1.0; +https://github.com/librefolio)"

_ONE = Decimal(1)
#: ISO code → (the BCRA's code, units per quote): USD is the A 3500 reference rate, MXN is «MXP», VND is per 1 000.
CODES: dict[str, tuple[str, Decimal]] = {
    "USD": ("REF", _ONE),
    "MXN": ("MXP", _ONE),
    "VND": ("VND", Decimal(1000)),
    "XDR": ("XDR", _ONE),
    **{code: (code, _ONE) for code in ["AUD", "AWG", "BOB", "BRL", "CAD", "CHF", "CLP", "CNY", "COP", "CZK", "DKK", "EUR", "GBP", "HKD", "ILS", "INR", "JPY", "NIO", "NOK", "NZD", "PEN", "PYG", "RSD", "RUB", "SEK", "SGD", "TRY", "UYU", "ZAR"]},
}

_CURRENCIES = sorted([*CODES, "ARS"])
#: The call's request pacing, shared by its parallel series (each call sets its own).
_PACER: contextvars.ContextVar["_Pacer"] = contextvars.ContextVar("bcra_pacer")


class _SeriesFailed(Exception):
    """One currency's series could not be read: that currency is skipped, the others go on."""


class _NotAsked(Exception):
    """A series queued behind a refusal for too many requests: never asked (the call is refused as a whole)."""


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
class BCRAProvider(FXRateProvider):
    """
    Banco Central de la República Argentina FX rate provider.

    Provides the BCRA's daily exchange rates of 33 currencies with ARS as base currency, ARS per unit; USD is the
    Comunicación A 3500 reference rate. Data source: the documented «Estadísticas Cambiarias v1.0» API.

    Coverage: a fixed code map, 33 currencies plus ARS.
    Update frequency: Argentine business days.
    """

    #: Pause between two request starts of one call (D9).
    PAUSE_SECONDS = 0.3
    #: Series in flight at once (the SARB pattern; three at once take about the time of one).
    MAX_PARALLEL = 3

    @property
    def code(self) -> str:
        return "BCRA"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Banco Central de la República Argentina"

    @property
    def icon(self) -> str | None:
        return "https://www.bcra.gob.ar/wp-content/uploads/cropped-favicon-bcra-192x192.png"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/bcra/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Banco Central de la República Argentina — daily exchange rates of 33 currencies against the Argentine peso (ARS); the US dollar is the official reference rate (Comunicación A 3500). Argentine business days, history from 2002. Source: Banco Central de la República Argentina.",
            "it": "Banco Central de la República Argentina — tassi di cambio giornalieri di 33 valute contro il peso argentino (ARS); il dollaro USA è il tasso di riferimento ufficiale (Comunicación A 3500). Giorni lavorativi argentini, storia dal 2002. Fonte: Banco Central de la República Argentina.",
            "fr": "Banco Central de la República Argentina — taux de change quotidiens de 33 devises contre le peso argentin (ARS) ; le dollar américain est le taux de référence officiel (Comunicación A 3500). Jours ouvrables argentins, historique depuis 2002. Source : Banco Central de la República Argentina.",
            "es": "Banco Central de la República Argentina — tipos de cambio diarios de 33 monedas contra el peso argentino (ARS); el dólar estadounidense es el tipo de cambio de referencia oficial (Comunicación A 3500). Días hábiles argentinos, historial desde 2002. Fuente: Banco Central de la República Argentina.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "The BCRA allows its data for informative, educational or academic use only, citing the bank, and not for commercial use without permission: this provider is meant for your own instance. The US dollar is the reference rate of Comunicación A 3500, whose method changed on 1 January 2026. The other currencies are the bank's own rates, built on another dollar rate of the bank, which can differ from the reference by a few percent in some years (up to 15% in 2002, 6% in 2018). The RUB rate is the one the BCRA publishes, not the Central Bank of Russia's. A day listed twice with two different rates is left out.",
            "it": "La BCRA consente i suoi dati solo per uso informativo, educativo o accademico, citando la banca, e non per uso commerciale senza permesso: questo provider è pensato per la tua istanza. Il dollaro USA è il tasso di riferimento della Comunicación A 3500, il cui metodo è cambiato il 1° gennaio 2026. Le altre valute sono i tassi propri della banca, costruiti su un altro tasso del dollaro della banca, che in alcuni anni può differire dal riferimento di qualche punto percentuale (fino al 15% nel 2002, al 6% nel 2018). Il tasso del RUB è quello che pubblica la BCRA, non quello della Banca centrale russa. Un giorno elencato due volte con due tassi diversi resta fuori.",
            "fr": "La BCRA autorise ses données seulement pour un usage informatif, éducatif ou académique, en citant la banque, et pas pour un usage commercial sans permission : ce fournisseur est prévu pour votre propre instance. Le dollar américain est le taux de référence de la Comunicación A 3500, dont la méthode a changé le 1er janvier 2026. Les autres devises sont les taux propres de la banque, construits sur un autre taux du dollar de la banque, qui peut différer de la référence de quelques pour cent certaines années (jusqu'à 15 % en 2002, 6 % en 2018). Le taux du RUB est celui que publie la BCRA, pas celui de la Banque centrale de Russie. Un jour listé deux fois avec deux taux différents est écarté.",
            "es": "El BCRA permite sus datos solo para uso informativo, educativo o académico, citando al banco, y no para uso comercial sin autorización: este proveedor está pensado para tu propia instancia. El dólar estadounidense es el tipo de cambio de referencia de la Comunicación A 3500, cuyo método cambió el 1 de enero de 2026. Las demás monedas son los tipos propios del banco, construidos sobre otro tipo del dólar del banco, que algunos años puede diferir de la referencia en unos puntos porcentuales (hasta el 15 % en 2002, el 6 % en 2018). El tipo del RUB es el que publica el BCRA, no el del Banco Central de Rusia. Un día que aparece dos veces con dos tipos distintos queda fuera.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # Non-commercial terms, a method change and two dollar rates: limits that can mislead (lane 75)
        return "warning"

    @property
    def base_currency(self) -> str:
        return "ARS"

    @property
    def test_currencies(self) -> list[str]:
        return ["ARS", "USD", "EUR", "BRL", "CLP"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(_CURRENCIES)

    async def get_supported_currencies(self) -> list[str]:
        """The currencies of the code map, plus ARS: no request."""
        return list(_CURRENCIES)

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch each asked currency's series in windows of ``WINDOW_DAYS``, at most ``MAX_PARALLEL`` currencies at once:
        ``(day, CUR, 'ARS', ARS per 1 CUR)``.

        Every value keeps its day (D2). A record of another code, an unreadable day or a value that is not positive is
        skipped (X-R50); a day with two different values is dropped. A currency whose series cannot be read is skipped
        with a warning, the others are returned; when every asked currency fails the call fails.

        Raises:
            ValueError: base_currency is neither None nor ARS
            FXRateLimitedError: the bank refused for too many requests (the whole call)
            FXServiceError: every asked series failed
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"BCRA provider only supports ARS as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        wanted = [currency for currency in asked if currency in CODES]
        if not wanted or request_start > end_date:
            return results

        outcomes = await self._fetch_all(wanted, request_start, end_date)
        raise_longest_refusal(outcomes)  # a currency refused for too many requests: the whole call is refused, as in SARB

        failures: list[str] = []
        for currency, outcome in zip(wanted, outcomes, strict=True):
            if isinstance(outcome, _SeriesFailed):
                logger.warning(f"BCRA fetch failed for {currency}, skipping: {outcome}")
                failures.append(f"{currency}: {outcome}")
            elif isinstance(outcome, BaseException):
                raise outcome
            else:
                results[currency] = self._series(currency, outcome, request_start, end_date)
        if len(failures) == len(wanted):
            raise FXServiceError(f"BCRA API error for every asked series: {'; '.join(failures)}")
        return results

    def _series(self, currency: str, values: list[tuple[date, Decimal]], start: date, end: date) -> list[tuple[date, str, str, Decimal]]:
        """One currency's values in the range, ascending; a day with two different values is dropped."""
        by_day: dict[date, set[Decimal]] = {}
        for day, value in values:
            if start <= day <= end:
                by_day.setdefault(day, set()).add(value)
        conflicting = [day for day, found in by_day.items() if len(found) > 1]
        if conflicting:
            logger.warning(f"BCRA: {len(conflicting)} day(s) with two different values for {currency} dropped")
        return [(day, currency, self.base_currency, next(iter(found))) for day, found in sorted(by_day.items()) if len(found) == 1]

    async def _fetch_all(self, wanted: list[str], start: date, end: date) -> list[object]:
        """Each currency's values or exception, in ``wanted`` order: at most ``MAX_PARALLEL`` series at once; after a
        refusal for too many requests the requests not started yet are never sent."""
        in_flight = asyncio.Semaphore(self.MAX_PARALLEL)
        pacer = _Pacer(self.PAUSE_SECONDS)
        _PACER.set(pacer)

        async def fetch(currency: str) -> list[tuple[date, Decimal]]:
            async with in_flight:
                try:
                    return await self._fetch_one(currency, start, end)
                except FXRateLimitedError:
                    pacer.refused = True
                    raise

        return await asyncio.gather(*(fetch(currency) for currency in wanted), return_exceptions=True)

    async def _fetch_one(self, currency: str, start: date, end: date) -> list[tuple[date, Decimal]]:
        """One currency's ``(day, ARS per 1 unit)`` values over every window, oldest first; ``_SeriesFailed`` when a
        window cannot be read, is cut, or is empty between two windows with values."""
        code, units = CODES[currency]
        pacer = _PACER.get(None) or _Pacer(self.PAUSE_SECONDS)
        windows: list[list[tuple[date, Decimal]]] = []
        async with httpx.AsyncClient(timeout=60.0, headers={"User-Agent": USER_AGENT}) as client:
            window_start = start
            while window_start <= end:
                window_end = min(end, window_start + timedelta(days=WINDOW_DAYS - 1))
                await pacer.wait(currency)
                windows.append(await self._window(client, code, units, window_start, window_end))
                window_start = window_end + timedelta(days=1)
        filled = [index for index, values in enumerate(windows) if values]
        if filled and any(not windows[index] for index in range(filled[0], filled[-1])):
            raise _SeriesFailed("an empty answer inside the series (the API answered no rate for a window between two with rates)")
        return [value for values in windows for value in values]

    async def _window(self, client: httpx.AsyncClient, code: str, units: Decimal, start: date, end: date) -> list[tuple[date, Decimal]]:
        """One window's ``(day, ARS per 1 unit)`` values; ``_SeriesFailed`` when the answer is not the series' JSON."""
        try:
            response = await client.get(f"{BASE_URL}/Cotizaciones/{code}", params={"fechadesde": start.isoformat(), "fechahasta": end.isoformat(), "limit": PAGE_LIMIT})
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            raise _SeriesFailed(f"request failed for {start}..{end}: {_error_messages(e)}") from e

        body = response.text.strip()
        if body[:1] == "<":
            raise _SeriesFailed("the answer is an HTML page, not the series JSON (endpoint changed or request refused)")
        try:
            data = json.loads(body, parse_float=Decimal)
        except ValueError:
            raise _SeriesFailed(f"the answer is not JSON: first bytes {body[:40]!r}") from None
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            raise _SeriesFailed("the answer has no results list (the API changed)")

        records = [(day, record) for day, record in _records(results)]
        count = (data.get("metadata") or {}).get("resultset", {}).get("count") if isinstance(data.get("metadata"), dict) else None
        if isinstance(count, int) and count > len(records):
            raise _SeriesFailed(f"the answer for {start}..{end} was cut at {len(records)} of {count} records")
        values: list[tuple[date, Decimal]] = []
        for day, record in records:
            value = record.get("tipoCotizacion")
            if day is None or record.get("codigoMoneda") != code or not isinstance(value, (Decimal, int)) or value <= 0:
                continue
            values.append((day, Decimal(value) / units))
        return values


def _records(results: list) -> list[tuple[date | None, dict]]:
    """Every detail record with its day (None when the day cannot be read)."""
    records: list[tuple[date | None, dict]] = []
    for entry in results:
        if not isinstance(entry, dict):
            continue
        try:
            day = date.fromisoformat(str(entry.get("fecha")))
        except ValueError:
            day = None
        records.extend((day, record) for record in entry.get("detalle") or [] if isinstance(record, dict))
    return records


def _error_messages(error: httpx.HTTPError) -> str:
    """The API's ``errorMessages`` of an error answer, when it has them; otherwise the error itself."""
    if isinstance(error, httpx.HTTPStatusError):
        try:
            messages = error.response.json().get("errorMessages")
        except (ValueError, AttributeError):
            messages = None
        if messages:
            return f"HTTP {error.response.status_code}: {'; '.join(map(str, messages))}"
    return str(error)
