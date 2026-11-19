"""
Bank of Israel (BOI) FX rate provider.

This provider reads the Bank of Israel's representative exchange rates from its SDMX REST server
(``edge.boi.gov.il/FusionEdgeServer``, the endpoint the bank's own guide names), dataflow ``BOI.STATISTICS/EXR/1.0``:
one series per currency, ``RER_{CUR}_ILS``, every asked series in one request (keys joined by ``+``), as CSV. ILS is
the base.

Terms (https://www.boi.org.il/en/terms-of-use/, read on 19/11/2026): the site's information is «the exclusive property
of the Bank of Israel», and the user «may not copy, publish, disseminate, transmit or sell» it «without the prior
written consent of the BOI». Developer decision D1 (lane 75), as for SARB and BDI: offered for a self-hosted instance
that stores the rates for its owner; the paid cloud turns it off. The description names the source.

Measured on 19/11/2026:

- ILS per ``10**UNIT_MULT`` units: JPY per 100 (``UNIT_MULT`` 2), LBP per 10 (1), the others per 1. The dataflow also
  holds indices, volatilities and implied series (``RER_USD_ILS_GLBLIMP``…): only ``RER_{CUR}_ILS`` is read.
- The bank publishes the history rescaled to the new shekel, from 1948 (USD 0.000025), daily from 1977. But from 1980
  to September 1985 the non-USD series carry ×1000 values on most Sundays (old shekels not rescaled: AUD 0.0039,
  3.9429, 0.0040 in January 1980), and JOD and LBP ÷10 values on Sundays until December 1985. **History from 1986**
  (``FIRST_DAY``): since then a few isolated days remain (JOD 2.5575 on 1991-03-04 between 2.89 and 2.93; JOD 6.2303 on
  2002-10-07 between 6.83 and 6.84). To be reviewed with the developer (lane 75, L35).
- **LBP is not served**: four decimals per 10 pounds (0.0003, 0.0004, 0.0003 in March 2026) make steps of about 30%.
- EUR from 04/01/1999. No conflicting duplicate. Sunday rows until 2025 are Israeli business days, not errors.
- An empty range (a weekend, a holiday) answers, about half the time each, 200 with an empty body (labelled
  ``text/html``) or 404 with an HTML error page; a range with rates always answers 200 CSV. No rate over more than
  ``EMPTY_SPAN_DAYS`` is an error: the longest gap since 1986 is 7 days (Passover).
- Budget: one request for any range; ``"min"`` (13 series since 1986) is ~9 MB in ~8 s.
"""

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

DATA_URL = "https://edge.boi.gov.il/FusionEdgeServer/sdmx/v2/data/dataflow/BOI.STATISTICS/EXR/1.0"
#: The first day served: the years before carry old-shekel values the bank did not rescale.
FIRST_DAY = date(1986, 1, 1)
#: The longest range that may hold no rate: the longest gap since 1986 is 7 days (Passover).
EMPTY_SPAN_DAYS = 10
#: The site's icon.
ICON_URL = "https://www.boi.org.il/favicon.ico"
#: An honest, constant User-Agent, the one BOE sends.
USER_AGENT = "Mozilla/5.0 (compatible; LibreFolio/1.0; +https://github.com/librefolio)"

#: The currencies served; LBP is in the dataflow and is not (four decimals per 10 pounds).
CURRENCIES = ("AUD", "CAD", "CHF", "DKK", "EGP", "EUR", "GBP", "JOD", "JPY", "NOK", "SEK", "USD", "ZAR")
_CATALOGUE = sorted([*CURRENCIES, "ILS"])
_COLUMNS = ("SERIES_CODE", "TIME_PERIOD", "OBS_VALUE", "UNIT_MULT")


def _series(currency: str) -> str:
    return f"RER_{currency}_ILS"


@register_provider(FXProviderRegistry)
class BOIProvider(FXRateProvider):
    """
    Bank of Israel FX rate provider.

    Provides the Bank of Israel's representative exchange rates of 13 currencies with ILS as base currency, ILS per
    unit. Data source: the bank's SDMX REST server, every asked series in one CSV request.

    Coverage: a fixed list, 13 currencies plus ILS.
    Update frequency: Israeli business days.
    """

    @property
    def code(self) -> str:
        return "BOI"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Bank of Israel"

    @property
    def icon(self) -> str | None:
        return ICON_URL

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/boi/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Bank of Israel — the representative exchange rates of 13 currencies against the Israeli new shekel (ILS), among them the Jordanian dinar and the Egyptian pound. Israeli business days, history from 1986. Source: Bank of Israel.",
            "it": "Bank of Israel — i tassi di cambio rappresentativi di 13 valute contro il nuovo shekel israeliano (ILS), tra cui il dinaro giordano e la sterlina egiziana. Giorni lavorativi israeliani, storia dal 1986. Fonte: Bank of Israel.",
            "fr": "Bank of Israel — les taux de change représentatifs de 13 devises contre le nouveau shekel israélien (ILS), dont le dinar jordanien et la livre égyptienne. Jours ouvrables israéliens, historique depuis 1986. Source : Bank of Israel.",
            "es": "Bank of Israel — los tipos de cambio representativos de 13 monedas contra el nuevo séquel israelí (ILS), entre ellas el dinar jordano y la libra egipcia. Días hábiles israelíes, historial desde 1986. Fuente: Bank of Israel.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "The Bank of Israel does not allow copying or publishing its data without its written consent: this provider is meant for your own instance. The history starts in 1986: the bank's earlier years hold old-shekel values on many days. A few single wrong days can still appear (JOD on 4 March 1991 and 7 October 2002). The Lebanese pound is not served: the bank publishes it with too few decimals to be usable.",
            "it": "La Bank of Israel non consente di copiare o pubblicare i suoi dati senza il suo consenso scritto: questo provider è pensato per la tua istanza. La storia parte dal 1986: gli anni precedenti della banca hanno valori in vecchi shekel in molti giorni. Possono ancora comparire alcuni singoli giorni sbagliati (JOD il 4 marzo 1991 e il 7 ottobre 2002). La lira libanese non è servita: la banca la pubblica con troppo pochi decimali per essere usabile.",
            "fr": "La Bank of Israel n'autorise pas la copie ni la publication de ses données sans son consentement écrit : ce fournisseur est prévu pour votre propre instance. L'historique commence en 1986 : les années précédentes de la banque contiennent des valeurs en anciens shekels sur de nombreux jours. Quelques jours erronés isolés peuvent encore apparaître (JOD le 4 mars 1991 et le 7 octobre 2002). La livre libanaise n'est pas servie : la banque la publie avec trop peu de décimales pour être utilisable.",
            "es": "El Bank of Israel no permite copiar ni publicar sus datos sin su consentimiento escrito: este proveedor está pensado para tu propia instancia. El historial empieza en 1986: los años anteriores del banco contienen valores en séqueles antiguos en muchos días. Aún pueden aparecer algunos días erróneos aislados (JOD el 4 de marzo de 1991 y el 7 de octubre de 2002). La libra libanesa no se ofrece: el banco la publica con muy pocos decimales para ser utilizable.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # Restrictive terms and a history cut to 1986 with residual wrong days: limits that can mislead (lane 75)
        return "warning"

    @property
    def base_currency(self) -> str:
        return "ILS"

    @property
    def test_currencies(self) -> list[str]:
        return ["ILS", "USD", "EUR", "GBP", "JPY"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(_CATALOGUE)

    async def get_supported_currencies(self) -> list[str]:
        """The 13 currencies, plus ILS: no request."""
        return list(_CATALOGUE)

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch every asked series in one request: ``(day, CUR, 'ILS', ILS per 1 CUR)``, ``UNIT_MULT`` divided out.

        Every value keeps its day (D2). A row of another series, with an unreadable day, unit or value, or a value that
        is not positive is skipped (X-R50); a day with two different values for a currency is dropped.

        Raises:
            ValueError: base_currency is neither None nor ILS
            FXRateLimitedError: the bank refused for too many requests
            FXServiceError: the request failed, or the answer is not the series' CSV
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"BOI provider only supports ILS as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        wanted = sorted(set(asked) & set(CURRENCIES))
        if not wanted or request_start > end_date:
            return results

        by_series = {_series(currency): currency for currency in wanted}
        values: dict[tuple[date, str], set[Decimal]] = {}
        for row in await self._fetch_rows("+".join(by_series), request_start, end_date):
            observation = _observation(row, by_series)
            if observation is not None and request_start <= observation[0] <= end_date:
                values.setdefault(observation[:2], set()).add(observation[2])

        conflicting = 0
        for (day, currency), found in sorted(values.items()):
            if len(found) > 1:
                conflicting += 1
                continue
            results[currency].append((day, currency, self.base_currency, next(iter(found))))
        if conflicting:
            logger.warning(f"BOI: {conflicting} day(s) with two different values for one currency dropped")
        return results

    async def _fetch_rows(self, keys: str, start: date, end: date) -> list[dict[str, str]]:
        """The CSV rows of the asked series. No rate at all (a 404 or an empty answer, the server gives either) is an
        empty range when it spans at most ``EMPTY_SPAN_DAYS``; over a longer range it is an error."""
        body = await self._get(keys, start, end)
        rows = _rows(body) if body is not None else []
        if not rows and (end - start).days > EMPTY_SPAN_DAYS:
            raise FXServiceError(f"BOI answered no rate for {start}..{end}, longer than any holiday: the API may have moved")
        return rows

    async def _get(self, keys: str, start: date, end: date) -> str | None:
        """The CSV of the asked series; None for a 404 (the server's answer, half the time, to a range with no rate);
        429 → rate limit, any other failure → FXServiceError."""
        try:
            async with httpx.AsyncClient(timeout=60.0, headers={"User-Agent": USER_AGENT}) as client:
                response = await client.get(f"{DATA_URL}/{keys}", params={"startperiod": start.isoformat(), "endperiod": end.isoformat(), "format": "csv"})
                if response.status_code == 404:
                    return None
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            logger.warning(f"BOI request failed: {e}")
            raise FXServiceError(f"BOI API error: {e}") from e
        return response.text


def _rows(body: str) -> list[dict[str, str]]:
    """The CSV rows; an empty body is an empty range (the server answers one, labelled text/html), HTML is an error."""
    text = body.strip()
    if not text:
        return []
    if text[:1] == "<":
        raise FXServiceError("BOI answer is an HTML page, not the series CSV (request refused, or the API changed)")
    reader = csv.DictReader(io.StringIO(text))
    missing = [column for column in _COLUMNS if column not in (reader.fieldnames or [])]
    if missing:
        raise FXServiceError(f"BOI answer lacks the columns {missing} (the API changed)")
    return list(reader)


def _observation(row: dict[str, str], by_series: dict[str, str]) -> tuple[date, str, Decimal] | None:
    """One row as ``(day, CUR, ILS per 1 CUR)``; None when it is another series or cannot be read."""
    currency = by_series.get((row.get("SERIES_CODE") or "").strip())
    if currency is None:
        return None
    try:
        day = date.fromisoformat((row.get("TIME_PERIOD") or "").strip())
        value = Decimal((row.get("OBS_VALUE") or "").strip())
        power = int((row.get("UNIT_MULT") or "0").strip() or "0")
    except (ValueError, InvalidOperation):
        return None
    if not value.is_finite() or value <= 0:
        return None
    return day, currency, value / (Decimal(10) ** power)
