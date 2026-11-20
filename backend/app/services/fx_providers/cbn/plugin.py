"""
Central Bank of Nigeria (CBN) FX rate provider.

This provider reads the exchange rates the Central Bank of Nigeria publishes on its site, through the JSON endpoints its
page «Exchange Rates by Currency» (https://www.cbn.gov.ng/rates/ExchRateByCurrency.html) reads. The **central** rate is
used, NGN per 1 unit of each currency. NGN is the base of the provider.

The endpoints are **not documented** (decision D10 c of lane 75): the note says so, and an answer of another shape fails
the call with a clear error instead of storing anything. Terms: no terms of use or disclaimer page found (❔, searched on
16 and 19/11/2026); decision D1 (lane 75): the provider is offered for a self-hosted instance that stores the rates for
its owner, nothing downloaded from the bank is committed. The description names the source.

Measured on 19/11/2026 (the site is behind Cloudflare; GET only):

- ``/api/GetAllExchangeRates``: the whole history in one answer, 62 696 rows from 2001-12-10, ~8 MB in ~4 s, newest
  first: ``{"id": 65444, "currency": "US DOLLAR", "ratedate": "2026-11-13", "buyingrate": "1352.9741",
  "centralrate": "1353.4741", "sellingrate": "1353.9741"}``. No date filter was found.
- ``/api/GetAllExchangeRatesGRAPH``: the same rows for about the last month (240 rows, 23/10–18/11, ~32 KB). A range of
  at most ``RECENT_SPAN_DAYS`` days asks it first, and the whole history only when it does not reach back to the start:
  a daily sync downloads 32 KB, not 8 MB.
- **Dirty names**: trailing spaces and tabs (``"EURO\\t"``, ``"YEN "``), variants (POUND/POUNDS STERLING, DANISH
  KRONA/KRONER, JAPANESE YEN) and noise (WAUA — the African Development Bank's unit of account —, NAIRA, POESO). The IMF's SDR is served as XDR
  (Q7 of lane 75).
  ``CURRENCY_NAMES`` maps the known names; every other row is discarded, and counted in the log.
- **Conflicting duplicates**: 97 day-and-currency keys appear twice, 64 of them with two different central rates (JPY
  2017-10-09: 2.7072 and 46.0795). Such a day is dropped for that currency, never picked (X-R50); an exact repeat is kept
  once.
- CFA is the West African CFA franc (XOF; 2.2796 NGN on 13/11/2026). UAE DIRHAM starts on 2026-01-22.
- Budget: 1 request (32 KB) for a 14-day sync; 1 request (8 MB) for ``"min"``.
"""

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

ALL_URL = "https://www.cbn.gov.ng/api/GetAllExchangeRates"
RECENT_URL = "https://www.cbn.gov.ng/api/GetAllExchangeRatesGRAPH"
#: A range of at most this many days asks the recent feed first.
RECENT_SPAN_DAYS = 20
#: The first day of the history.
FIRST_DAY = date(2001, 12, 10)
#: The bank's currency names (stripped) → ISO code. Any other name is discarded.
CURRENCY_NAMES: dict[str, str] = {
    "US DOLLAR": "USD",
    "POUNDS STERLING": "GBP",
    "POUND STERLING": "GBP",
    "EURO": "EUR",
    "YEN": "JPY",
    "JAPANESE YEN": "JPY",
    "CFA": "XOF",
    "RIYAL": "SAR",
    "SWISS FRANC": "CHF",
    "YUAN/RENMINBI": "CNY",
    "DANISH KRONA": "DKK",
    "DANISH KRONER": "DKK",
    "SOUTH AFRICAN RAND": "ZAR",
    "UAE DIRHAM": "AED",
    "SDR": "XDR",
}

_CURRENCIES = sorted({*CURRENCY_NAMES.values(), "NGN"})


@register_provider(FXProviderRegistry)
class CBNProvider(FXRateProvider):
    """
    Central Bank of Nigeria FX rate provider.

    Provides the central exchange rate of 12 currencies with NGN as base currency (NGN per 1 unit).
    Data source: the undocumented JSON endpoints of the CBN's rate page.

    Coverage: a fixed name map, 12 currencies plus NGN.
    Update frequency: Nigerian business days.
    """

    @property
    def code(self) -> str:
        return "CBN"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Central Bank of Nigeria"

    @property
    def icon(self) -> str | None:
        return "https://www.cbn.gov.ng/favicon.ico"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/cbn/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Central Bank of Nigeria — the central exchange rate of 12 currencies against the naira (NGN), among them USD, GBP, EUR, the West African CFA franc (XOF), SAR and AED. Nigerian business days, history from 2001. Source: Central Bank of Nigeria.",
            "it": "Central Bank of Nigeria — il tasso di cambio centrale di 12 valute contro la naira (NGN), tra cui USD, GBP, EUR, il franco CFA dell'Africa occidentale (XOF), SAR e AED. Giorni lavorativi nigeriani, storia dal 2001. Fonte: Central Bank of Nigeria.",
            "fr": "Central Bank of Nigeria — le taux de change central de 12 devises contre le naira (NGN), dont USD, GBP, EUR, le franc CFA d'Afrique de l'Ouest (XOF), SAR et AED. Jours ouvrables nigérians, historique depuis 2001. Source : Central Bank of Nigeria.",
            "es": "Central Bank of Nigeria — el tipo de cambio central de 12 monedas contra la naira (NGN), entre ellas USD, GBP, EUR, el franco CFA de África Occidental (XOF), SAR y AED. Días hábiles nigerianos, historial desde 2001. Fuente: Central Bank of Nigeria.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "The CBN's rates come from an undocumented source behind its website, which can change without notice. The data are uneven: on some days a currency is listed twice with two different rates, and LibreFolio leaves such a day out instead of guessing. The central rate is used (between the bank's buying and selling rates).",
            "it": "I tassi della CBN vengono da una fonte non documentata dietro il suo sito, che può cambiare senza preavviso. I dati sono irregolari: in alcuni giorni una valuta compare due volte con due tassi diversi, e LibreFolio lascia fuori quel giorno invece di indovinare. Si usa il tasso centrale (fra i tassi di acquisto e di vendita della banca).",
            "fr": "Les taux de la CBN viennent d'une source non documentée derrière son site, qui peut changer sans préavis. Les données sont inégales : certains jours une devise figure deux fois avec deux taux différents, et LibreFolio écarte ce jour au lieu de deviner. Le taux central est utilisé (entre les taux d'achat et de vente de la banque).",
            "es": "Los tipos de la CBN vienen de una fuente no documentada detrás de su sitio, que puede cambiar sin aviso. Los datos son irregulares: algunos días una moneda aparece dos veces con dos tipos distintos, y LibreFolio deja fuera ese día en lugar de adivinar. Se usa el tipo central (entre los tipos de compra y de venta del banco).",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # An undocumented source with conflicting rows: a data limit that can mislead, warning (lane 75)
        return "warning"

    @property
    def base_currency(self) -> str:
        return "NGN"

    @property
    def test_currencies(self) -> list[str]:
        return ["NGN", "USD", "EUR", "GBP"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(_CURRENCIES)

    async def get_supported_currencies(self) -> list[str]:
        """The currencies of the name map, plus NGN: no request (the 8 MB history is no catalogue)."""
        return list(_CURRENCIES)

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch the central rates: ``(day, CUR, 'NGN', NGN per 1 CUR)``, from the recent feed when it covers a short
        range, else from the whole history.

        Every value keeps its day (D2). A row with an unknown name, an unreadable day or no positive central rate is
        skipped (X-R50); a day where a currency has two different central rates is dropped for that currency.

        Raises:
            ValueError: base_currency is neither None nor NGN
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: a request failed, or an answer is not a JSON list
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"CBN provider only supports NGN as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        wanted = set(asked) & set(CURRENCY_NAMES.values())
        if not wanted or request_start > end_date:
            return results

        rows = await self._rows_for(request_start, end_date)
        by_key: dict[tuple[date, str], set[Decimal]] = defaultdict(set)
        unknown: Counter[str] = Counter()
        for row in rows:
            name = str(row.get("currency", "")).strip() if isinstance(row, dict) else ""
            currency = CURRENCY_NAMES.get(name)
            if currency is None:
                unknown[name] += 1
                continue
            day, value = self._day(row), self._value(row)
            if day is None or value is None or currency not in wanted or not request_start <= day <= end_date:
                continue
            by_key[(day, currency)].add(value)
        if unknown:
            logger.debug(f"CBN: rows with a name outside the map discarded: {dict(unknown)}")

        conflicting = 0
        for (day, currency), values in sorted(by_key.items()):
            if len(values) > 1:
                conflicting += 1
                continue
            results[currency].append((day, currency, self.base_currency, next(iter(values))))
        if conflicting:
            logger.warning(f"CBN: {conflicting} day(s) with two different central rates for one currency dropped")
        return results

    async def _rows_for(self, start: date, end: date) -> list:
        """The recent feed when the range is short and the feed reaches back to ``start``; else the whole history."""
        if (end - start).days <= RECENT_SPAN_DAYS:
            recent = await self._get_rows(RECENT_URL, "the recent rates")
            days = [day for day in (self._day(row) for row in recent) if day is not None]
            if days and min(days) <= start:
                return recent
        return await self._get_rows(ALL_URL, "the whole history")

    @staticmethod
    def _day(row: object) -> date | None:
        """``{"ratedate": "2026-11-13"}`` as a date, or None."""
        try:
            return date.fromisoformat(str(row["ratedate"]).strip()[:10])  # type: ignore[index]
        except (TypeError, KeyError, ValueError):
            return None

    @staticmethod
    def _value(row: object) -> Decimal | None:
        """The central rate as ``Decimal``, or None when it is no positive number."""
        text = row.get("centralrate") if isinstance(row, dict) else None
        if text is None:
            return None
        try:
            value = Decimal(str(text).strip())
        except InvalidOperation:
            return None
        return value if value.is_finite() and value > 0 else None

    async def _get_rows(self, url: str, what: str) -> list:
        """GET one endpoint; anything that is not a JSON list is an ``FXServiceError``."""
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.get(url, headers={"Accept": "application/json"})
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            logger.warning(f"CBN request failed for {what}: {e}")
            raise FXServiceError(f"CBN API error for {what}: {e}") from e

        body = response.text
        if body.lstrip()[:1] == "<":
            raise FXServiceError(f"CBN answer for {what} is an HTML page, not the rates JSON (undocumented endpoint changed, or request refused)")
        try:
            rows = response.json()
        except ValueError:
            raise FXServiceError(f"CBN answer for {what} is not JSON: first bytes {body.lstrip()[:40]!r}") from None
        if not isinstance(rows, list):
            raise FXServiceError(f"CBN answer for {what} is not a JSON list (undocumented endpoint changed)")
        return rows
