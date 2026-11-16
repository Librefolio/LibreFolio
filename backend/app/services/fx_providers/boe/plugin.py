"""
Bank of England (BOE) FX rate provider.

This provider fetches exchange rates from the Bank of England Statistical Interactive Database.
BOE provides daily rates with GBP as base currency.

API Documentation: https://www.bankofengland.co.uk/boeapps/database/
Licence: the Bank of England Database is published under the UK Open Government Licence
(https://www.bankofengland.co.uk/legal, «Bank of England Database»): free reuse, with attribution.

Path used: ``/boeapps/database/_iadb-fromshowcolumns.asp`` with ``csv.x=yes``, one series per request. Measured on
16/11/2026: the old ``/boeapps/database/fromshowcolumns.asp`` URL, and this one without ``csv.x``, answer the HTML page
«Data Series» instead of the CSV; this path answers ``application/csv``. The site's robots.txt lists
``Disallow: /boeapps/database/_iadb-FromShowColumns.asp`` (since 2024 at least). The developer's decision (lane 75,
16/11/2026): robots.txt addresses search-engine crawlers, not a user's own fetch of an OGL dataset, so the provider
uses this path. No anti-bot measure is involved or evaded: plain requests, an honest User-Agent. The path is not
documented and can change again: ``_check_csv`` refuses any answer that is not the CSV of the series asked.
"""

import asyncio
from datetime import date, datetime
from decimal import Decimal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FX_HISTORY_MIN_FALLBACK, FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited, raise_longest_refusal
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)


@register_provider(FXProviderRegistry)
class BOEProvider(FXRateProvider):
    """
    Bank of England FX rate provider.

    Provides daily exchange rates with GBP as base currency.
    Data source: Bank of England Statistical Interactive Database (IADB).

    Coverage: ~15 major currencies (USD, EUR, JPY, CHF, AUD, etc.)
    Update frequency: Daily (weekdays only, UK business days)
    """

    # BOE API configuration: the CSV download of the Interactive Database (needs ``csv.x=yes``)
    BASE_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
    #: The earliest ``Datefrom`` the database accepts: an earlier one is refused (302 to ``ErrorPage.asp?ei=905``)
    FIRST_DAY = date(1963, 1, 1)

    # Series codes for exchange rates: daily spot rates, every one «<currency> into Sterling» (CUR per 1 GBP).
    # A code ending in D (e.g. XUDLERD, «Euro into US $») is against the dollar: never one of these.
    CURRENCY_SERIES = {
        "USD": "XUDLUSS",  # US Dollar spot
        "EUR": "XUDLERS",  # Euro spot (into Sterling)
        "JPY": "XUDLJYS",  # Japanese Yen spot
        "CHF": "XUDLSFS",  # Swiss Franc spot
        "CAD": "XUDLCDS",  # Canadian Dollar spot
        "AUD": "XUDLADS",  # Australian Dollar spot
        "NZD": "XUDLNDS",  # New Zealand Dollar spot
        "SEK": "XUDLSKS",  # Swedish Krona spot
        "NOK": "XUDLNKS",  # Norwegian Krone spot
        "DKK": "XUDLDKS",  # Danish Krone spot
        "CNY": "XUDLBK89",  # Chinese Yuan spot
        "HKD": "XUDLHDS",  # Hong Kong Dollar spot
        "SGD": "XUDLSGS",  # Singapore Dollar spot
        "ZAR": "XUDLZRS",  # South African Rand spot
        "INR": "XUDLBK97",  # Indian Rupee spot
    }

    @property
    def code(self) -> str:
        return "BOE"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Bank of England"

    @property
    def icon(self) -> str | None:
        return "https://www.bankofengland.co.uk/favicon.svg?ver=2c06d"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/boe/"

    @property
    def base_currency(self) -> str:
        return "GBP"

    @property
    def description(self) -> str:
        return "Official exchange rates from Bank of England"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Bank of England — daily spot exchange rates against GBP. LibreFolio's provider covers 15 currencies. Updated each business day. One data point per day.",
            "it": "Bank of England — tassi di cambio spot giornalieri contro GBP. Il provider di LibreFolio copre 15 valute. Aggiornamento ogni giorno lavorativo. Un dato al giorno.",
            "fr": "Banque d'Angleterre — taux de change spot quotidiens contre GBP. Le fournisseur de LibreFolio couvre 15 devises. Mise à jour chaque jour ouvrable. Un point par jour.",
            "es": "Banco de Inglaterra — tipos de cambio spot diarios contra GBP. El proveedor de LibreFolio cubre 15 monedas. Actualizado cada día hábil. Un dato por día.",
        }

    @property
    def test_currencies(self) -> list[str]:
        """
        Common currencies that BOE should always provide.
        These are used for automated testing.
        """
        return [
            "GBP",  # British Pound (base currency)
            "USD",  # US Dollar
            "EUR",  # Euro
            "JPY",  # Japanese Yen
            "CHF",  # Swiss Franc
            "AUD",  # Australian Dollar
        ]

    async def get_supported_currencies(self) -> list[str]:
        """
        Get list of supported currencies.

        BOE has a fixed list of currencies, so we return the static list.

        Returns:
            List of ISO 4217 currency codes supported by BOE
        """
        # Include GBP as base currency + all quote currencies
        currencies = ["GBP"] + list(self.CURRENCY_SERIES.keys())
        return sorted(currencies)

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch FX rates from BOE API for given date range and currencies.

        BOE provides rates as: 1 GBP = X foreign currency

        Args:
            date_range: (start_date, end_date) inclusive
            currencies: List of currency codes (excluding GBP)
            base_currency: Must be None or "GBP" (BOE only supports GBP as base)

        Returns:
            Dictionary mapping currency -> [(date, base, quote, rate), ...]

        Raises:
            ValueError: If base_currency is not None and not "GBP"
            FXServiceError: If API request fails
        """
        # Validate base_currency for single-base provider
        if base_currency is not None and base_currency != "GBP":
            raise ValueError(f"BOE provider only supports GBP as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FX_HISTORY_MIN_FALLBACK if start_date == "min" else start_date
        request_start = max(request_start, self.FIRST_DAY)  # the database refuses an earlier Datefrom
        # Every currency asked gets a list, empty when nothing arrives
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {c: [] for c in currencies if c != "GBP"}

        # Filter valid currencies; none when the whole range is before the database's first day
        valid_currencies = [c for c in currencies if c != "GBP" and c in self.CURRENCY_SERIES and request_start <= end_date]
        skipped = [c for c in currencies if c != "GBP" and c not in self.CURRENCY_SERIES]
        for c in skipped:
            logger.warning(f"Currency {c} not supported by BOE, skipping")

        if not valid_currencies:
            return results

        async def _fetch_one(currency: str) -> tuple[str, list[tuple[date, str, str, Decimal]]]:
            """Fetch rates for a single currency — isolated for parallel execution."""
            series_code = self.CURRENCY_SERIES[currency]

            params = {
                "csv.x": "yes",
                "Datefrom": request_start.strftime("%d/%b/%Y"),
                "Dateto": end_date.strftime("%d/%b/%Y"),
                "SeriesCodes": series_code,
                "CSVF": "TN",
                "UsingCodes": "Y",
                "VPD": "Y",
                "VFD": "N",
            }

            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; LibreFolio/1.0; +https://github.com/librefolio)",
                    "Accept": "text/csv, text/plain, */*;q=0.1",
                }

                async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
                    response = await client.get(self.BASE_URL, params=params)
                    response.raise_for_status()

                    body = response.text
                    self._check_csv(body, series_code, currency)  # never parse an answer that is not this series' CSV
                    observations = self._parse_response(body, currency)
                    return currency, observations

            except FXServiceError:  # already says what went wrong; logged once where the currency is skipped
                raise
            except httpx.HTTPError as e:
                raise_if_fx_rate_limited(e, self.provider_code)
                logger.exception(f"Failed to fetch FX rates for {currency} from BOE: {e}")
                raise FXServiceError(f"BOE API error for {currency}: {e}") from e
            except Exception as e:
                logger.exception(f"Failed to parse BOE response for {currency}: {e}")
                raise FXServiceError(f"Unexpected BOE response format for {currency}: {e}") from e

        # Launch all HTTP calls in parallel (return_exceptions to avoid cascade failure)
        tasks = [_fetch_one(c) for c in valid_currencies]
        fetched = await asyncio.gather(*tasks, return_exceptions=True)
        raise_longest_refusal(fetched)  # a currency refused for too many requests: the whole call is refused, the core pauses

        for i, result in enumerate(fetched):
            if isinstance(result, BaseException):
                currency = valid_currencies[i]
                logger.warning(f"BOE fetch failed for {currency}, skipping: {result}")
                results[currency] = []
            else:
                currency, observations = result
                results[currency] = observations

        return results

    @staticmethod
    def _check_csv(body: str, series_code: str, currency: str) -> None:
        """Refuse an answer that is not the CSV of ``series_code``: its first line must be ``DATE,<series_code>``.

        An HTML page (a changed endpoint, the Bank's error page), an empty answer or the CSV of another series raises
        ``FXServiceError`` naming the currency, the series and what arrived; nothing of it is parsed or stored.

        Raises:
            FXServiceError: the answer is not the CSV of ``series_code``
        """
        first_line = body.lstrip().split("\n", 1)[0].strip()
        if first_line.upper() == f"DATE,{series_code}":
            return
        head = body.lstrip()[:200].lower()
        what = "an HTML page" if "<html" in head or "<!doctype" in head or "<head" in head or "<body" in head else f"first line {first_line[:60]!r}"
        raise FXServiceError(f"BOE answer for {currency} is not the CSV of series {series_code}: {what} (endpoint changed or request refused)")

    def _parse_response(self, response_text: str, currency: str) -> list[tuple[date, Decimal]]:  # pragma: no cover
        """
        Parse BOE CSV-like response.

        Format (approximate):
        DATE,XUDLXXX
        01 Jan 2025,1.2500
        02 Jan 2025,1.2510

        Args:
            response_text: Raw text from BOE API
            currency: Currency code being parsed

        Returns:
            List of (date, base, quote, rate) tuples
        """
        observations = []

        lines = response_text.strip().split("\n")

        # Skip header line
        if len(lines) < 2:
            logger.warning(f"BOE response too short for {currency}")
            return []

        for line in lines[1:]:  # Skip header
            if not line.strip():
                continue

            parts = line.split(",")
            if len(parts) < 2:
                continue

            try:
                # Parse date (format: DD Mon YYYY, e.g., "01 Jan 2025")
                date_str = parts[0].strip()
                rate_date = self._parse_boe_date(date_str)

                # Parse rate value from CSV
                rate_str = parts[1].strip()

                # Skip empty values (no data available for this date)
                # BOE may not publish rates on weekends, holidays, or UK bank holidays
                if not rate_str or rate_str == "":
                    continue

                # BOE gives: 1 GBP = X foreign currency
                # Example: 1 GBP = 1.27 USD
                # Return as (date, base, quote, rate)
                rate = Decimal(rate_str)

                observations.append((rate_date, self.base_currency, currency, rate))

            except (ValueError, IndexError, ArithmeticError) as e:  # ArithmeticError: a value that is no number, the line only (X-R50)
                logger.debug(f"Skipping invalid line in BOE response: {line[:50]}... ({e})")
                continue

        logger.debug(f"Parsed {len(observations)} rates for {currency} from BOE")
        return observations

    def _parse_boe_date(self, date_str: str) -> date:  # pragma: no cover
        """
        Parse BOE date format.

        Format: "DD Mon YYYY" (e.g., "01 Jan 2025")
        """
        return datetime.strptime(date_str, "%d %b %Y").date()
