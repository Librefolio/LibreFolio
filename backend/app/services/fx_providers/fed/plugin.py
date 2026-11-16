"""
Federal Reserve (FED) FX rate provider.

This provider fetches exchange rates from FRED (Federal Reserve Economic Data).
FED provides daily rates with USD as base currency, released once a week (H.10).

API Documentation: https://fred.stlouisfed.org/docs/api/fred/
Data Source: H.10 Foreign Exchange Rates via FRED
Note: No API key required for basic usage
"""

import asyncio
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal, NamedTuple

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FX_HISTORY_MIN_FALLBACK, FXProviderStartDate, FXRateProvider, FXServiceError, raise_if_fx_rate_limited, raise_longest_refusal
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)


class FredQuote(Enum):
    """How a FRED H.10 series is quoted. FRED's series title says it: «U.S. Dollars to One Euro» or «Japanese Yen to One
    U.S. Dollar»."""

    #: ``DEXUS..`` series: 1 foreign unit = value USD (e.g. ``DEXUSEU`` 1.08: 1 EUR = 1.08 USD)
    USD_PER_UNIT = "usd_per_unit"
    #: ``DEX..US`` series: 1 USD = value foreign units (e.g. ``DEXJPUS`` 158.2: 1 USD = 158.2 JPY)
    UNITS_PER_USD = "units_per_usd"


class FredSeries(NamedTuple):
    """One FRED series: its id, how it is quoted, and the first day it is in the currency's present unit."""

    series_id: str
    quote: FredQuote
    #: The first day served; earlier lines are in an older unit of the currency (a redenomination). None: the whole series
    first_day: date | None = None


_USD_PER_UNIT = FredQuote.USD_PER_UNIT
_UNITS_PER_USD = FredQuote.UNITS_PER_USD


@register_provider(FXProviderRegistry)
class FEDProvider(FXRateProvider):
    """
    Federal Reserve FX rate provider via FRED API.

    Provides daily exchange rates with USD as base currency.
    Data source: FRED (Federal Reserve Economic Data) - H.10 Release.

    Coverage: 23 currencies (EUR, GBP, JPY, CAD, CHF, AUD, etc.)
    Update frequency: one value per US business day, released once a week (H.10 comes out on Mondays)

    Note: FRED quotes each series in one of two directions (``FredQuote``); every series declares its own, and the
    rate is returned as published, «1 base = rate quote»: the service normalizes the pair.
    """

    # FRED CSV Download (no API key needed - uses public data download)
    BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

    # FRED Series IDs for FX rates, each with its direction (FRED's series title):
    # DEXUS.. = U.S. Dollars to One <currency>; DEX..US = <currency> to One U.S. Dollar.
    CURRENCY_SERIES: dict[str, FredSeries] = {
        "EUR": FredSeries("DEXUSEU", _USD_PER_UNIT),  # Euro: USD per 1 EUR
        "GBP": FredSeries("DEXUSUK", _USD_PER_UNIT),  # British Pound: USD per 1 GBP
        "AUD": FredSeries("DEXUSAL", _USD_PER_UNIT),  # Australian Dollar: USD per 1 AUD
        "NZD": FredSeries("DEXUSNZ", _USD_PER_UNIT),  # New Zealand Dollar: USD per 1 NZD
        "JPY": FredSeries("DEXJPUS", _UNITS_PER_USD),  # Japanese Yen: JPY per 1 USD
        "CAD": FredSeries("DEXCAUS", _UNITS_PER_USD),  # Canadian Dollar: CAD per 1 USD
        "CHF": FredSeries("DEXSZUS", _UNITS_PER_USD),  # Swiss Franc: CHF per 1 USD
        "SEK": FredSeries("DEXSDUS", _UNITS_PER_USD),  # Swedish Krona: SEK per 1 USD
        "DKK": FredSeries("DEXDNUS", _UNITS_PER_USD),  # Danish Krone: DKK per 1 USD
        "NOK": FredSeries("DEXNOUS", _UNITS_PER_USD),  # Norwegian Krone: NOK per 1 USD
        "CNY": FredSeries("DEXCHUS", _UNITS_PER_USD),  # Chinese Yuan: CNY per 1 USD
        "INR": FredSeries("DEXINUS", _UNITS_PER_USD),  # Indian Rupee: INR per 1 USD
        "BRL": FredSeries("DEXBZUS", _UNITS_PER_USD),  # Brazilian Real: BRL per 1 USD
        "MXN": FredSeries("DEXMXUS", _UNITS_PER_USD),  # Mexican Peso: MXN per 1 USD
        "ZAR": FredSeries("DEXSFUS", _UNITS_PER_USD),  # South African Rand: ZAR per 1 USD
        "SGD": FredSeries("DEXSIUS", _UNITS_PER_USD),  # Singapore Dollar: SGD per 1 USD
        "HKD": FredSeries("DEXHKUS", _UNITS_PER_USD),  # Hong Kong Dollar: HKD per 1 USD
        "KRW": FredSeries("DEXKOUS", _UNITS_PER_USD),  # South Korean Won: KRW per 1 USD
        "TWD": FredSeries("DEXTAUS", _UNITS_PER_USD),  # Taiwan Dollar: TWD per 1 USD
        "THB": FredSeries("DEXTHUS", _UNITS_PER_USD),  # Thai Baht: THB per 1 USD
        "MYR": FredSeries("DEXMAUS", _UNITS_PER_USD),  # Malaysian Ringgit: MYR per 1 USD
        "LKR": FredSeries("DEXSLUS", _UNITS_PER_USD),  # Sri Lankan Rupee: LKR per 1 USD
        # Venezuelan Bolívar: VES per 1 USD. DEXVZUS joins three units: VEF until 17/08/2018, the 2018 bolívar until
        # 01/10/2021, today's (10^6 of the 2018 one) since 04/10/2021. Only today's unit is VES.
        "VES": FredSeries("DEXVZUS", _UNITS_PER_USD, first_day=date(2021, 10, 4)),
    }

    @property
    def code(self) -> str:
        return "FED"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Federal Reserve Bank"

    @property
    def icon(self) -> str | None:
        return "https://fred.stlouisfed.org/favicon.ico"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/fed/"

    @property
    def base_currency(self) -> str:
        return "USD"

    @property
    def description(self) -> str:
        return "Official exchange rates from Federal Reserve (H.10 Release)"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Federal Reserve Bank (FRED) — daily exchange rates from the H.10 Statistical Release for 23 currencies against USD. Published once a week. One data point per US business day.",
            "it": "Federal Reserve Bank (FRED) — tassi di cambio giornalieri dal bollettino statistico H.10 per 23 valute contro USD. Pubblicati una volta alla settimana. Un dato per giorno lavorativo USA.",
            "fr": "Federal Reserve Bank (FRED) — taux de change quotidiens du bulletin statistique H.10 pour 23 devises contre USD. Publiés une fois par semaine. Un point par jour ouvrable américain.",
            "es": "Federal Reserve Bank (FRED) — tipos de cambio diarios del boletín estadístico H.10 para 23 monedas contra USD. Publicados una vez por semana. Un dato por día hábil de EE. UU.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        # A fact worth knowing, not a data fault: shown at «info» level (warning_level)
        return {
            "en": "FED rates are daily: one value per US business day. The Federal Reserve publishes them once a week, on Mondays, with the days of the previous week, so the latest FED rate can be up to about 10 days old.",
            "it": "I tassi FED sono giornalieri: un valore per ogni giorno lavorativo statunitense. La Federal Reserve li pubblica una volta alla settimana, il lunedì, con i giorni della settimana precedente: l'ultimo tasso FED può quindi avere fino a circa 10 giorni.",
            "fr": "Les taux FED sont quotidiens : une valeur par jour ouvrable américain. La Réserve fédérale les publie une fois par semaine, le lundi, avec les jours de la semaine précédente : le dernier taux FED peut donc dater d'environ 10 jours.",
            "es": "Los tipos FED son diarios: un valor por cada día hábil de EE. UU. La Reserva Federal los publica una vez por semana, los lunes, con los días de la semana anterior: el último tipo FED puede tener hasta unos 10 días.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        return "info"

    @property
    def test_currencies(self) -> list[str]:
        """
        Common currencies that FED should always provide.
        These are used for automated testing.
        """
        return [
            "USD",  # US Dollar (base currency)
            "EUR",  # Euro
            "GBP",  # British Pound
            "JPY",  # Japanese Yen
            "CAD",  # Canadian Dollar
            "CHF",  # Swiss Franc
            "AUD",  # Australian Dollar
        ]

    @property
    def multi_unit_currencies(self) -> set[str]:
        """
        FRED quotes ALL currencies per 1 unit, including JPY.
        No multi-unit adjustments needed.
        """
        return set()  # Empty - FRED quotes all per 1 unit

    async def get_supported_currencies(self) -> list[str]:
        """
        Get list of supported currencies.

        FED H.10 has a fixed list of currencies, so we return the static list.

        Returns:
            List of ISO 4217 currency codes supported by FED
        """
        # Include USD as base currency + all quote currencies
        currencies = ["USD"] + list(self.CURRENCY_SERIES.keys())
        return sorted(currencies)

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch FX rates from FRED API for given date range and currencies.

        Each series is returned as FRED quotes it (``FredSeries.quote``): «1 CUR = v USD» as (d, CUR, 'USD', v),
        «1 USD = v CUR» as (d, 'USD', CUR, v). A series with a ``first_day`` is asked from that day on.

        Args:
            date_range: (start_date, end_date) inclusive
            currencies: List of currency codes (excluding USD)
            base_currency: Must be None or "USD" (FED only supports USD as base)

        Returns:
            Dictionary mapping currency -> [(date, base, quote, rate), ...]

        Raises:
            ValueError: If base_currency is not None and not "USD"
            FXServiceError: If API request fails
        """
        # Validate base_currency for single-base provider
        if base_currency is not None and base_currency != "USD":
            raise ValueError(f"FED provider only supports USD as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FX_HISTORY_MIN_FALLBACK if start_date == "min" else start_date
        results = {}

        # Filter valid currencies
        valid_currencies = [c for c in currencies if c != "USD" and c in self.CURRENCY_SERIES]
        skipped = [c for c in currencies if c != "USD" and c not in self.CURRENCY_SERIES]
        for c in skipped:
            logger.warning(f"Currency {c} not supported by FED, skipping")
            results[c] = []

        if not valid_currencies:
            return results

        async def _fetch_one(currency: str) -> tuple[str, list[tuple[date, str, str, Decimal]]]:
            """Fetch rates for a single currency — isolated for parallel execution."""
            series = self.CURRENCY_SERIES[currency]
            series_start = max(request_start, series.first_day) if series.first_day else request_start
            if series_start > end_date:  # the whole range is before the currency's present unit: nothing to ask
                return currency, []

            params = {
                "id": series.series_id,
                "cosd": series_start.isoformat(),
                "coed": end_date.isoformat(),
            }

            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    response = await client.get(self.BASE_URL, params=params)
                    response.raise_for_status()

                    observations = self._parse_csv(response.text, currency, series_start, end_date)
                    return currency, observations

            except httpx.HTTPError as e:
                raise_if_fx_rate_limited(e, self.provider_code)
                logger.exception(f"Failed to fetch FX rates for {currency} from FED/FRED: {e}")
                raise FXServiceError(f"FED/FRED API error for {currency}: {e}") from e
            except Exception as e:
                logger.exception(f"Failed to parse FED/FRED response for {currency}: {e}")
                raise FXServiceError(f"Unexpected FED/FRED response format for {currency}: {e}") from e

        # Launch all HTTP calls in parallel (return_exceptions to avoid cascade failure)
        tasks = [_fetch_one(c) for c in valid_currencies]
        fetched = await asyncio.gather(*tasks, return_exceptions=True)
        raise_longest_refusal(fetched)  # a currency refused for too many requests: the whole call is refused, the core pauses

        for i, result in enumerate(fetched):
            if isinstance(result, BaseException):
                currency = valid_currencies[i]
                logger.warning(f"FED fetch failed for {currency}, skipping: {result}")
                results[currency] = []
            else:
                currency, observations = result
                results[currency] = observations

        return results

    def _parse_csv(self, csv_text: str, currency: str, start_date: date, end_date: date) -> list[tuple[date, str, str, Decimal]]:
        """
        Parse FRED CSV response.

        CSV Format:
        DATE,DEXUSEU
        2024-01-01,1.0850
        2024-01-02,1.0860
        ...

        Args:
            csv_text: Raw CSV text from FRED
            currency: Currency code being parsed
            start_date: Start date for filtering
            end_date: End date for filtering

        Returns:
            List of (date, base, quote, rate) tuples
        """
        observations = []
        # Returned as published, «1 base = rate quote»; the service normalizes the pair
        # DEXUSEU 1.08: 1 EUR = 1.08 USD → (date, 'EUR', 'USD', 1.08); DEXJPUS 158.2: 1 USD = 158.2 JPY → (date, 'USD', 'JPY', 158.2)
        usd_per_unit = self.CURRENCY_SERIES[currency].quote is FredQuote.USD_PER_UNIT
        base, quote = (currency, self.base_currency) if usd_per_unit else (self.base_currency, currency)

        lines = csv_text.strip().split("\n")

        # Skip header
        if len(lines) < 2:
            logger.warning(f"FRED CSV response too short for {currency}")
            return []

        for line in lines[1:]:  # Skip header
            if not line.strip():
                continue

            parts = line.split(",")
            if len(parts) < 2:
                continue

            try:
                # Parse date (format: YYYY-MM-DD)
                date_str = parts[0].strip()
                rate_date = date.fromisoformat(date_str)

                # Filter: only include dates within requested range
                # FRED sometimes returns more data than requested
                if rate_date < start_date or rate_date > end_date:
                    continue

                # Parse value from CSV
                value_str = parts[1].strip()

                # Skip missing data indicators from FRED
                # "." = No data available for this date
                # "" = Empty value (same as no data)
                # "ND" = Not Determined (explicit no-data marker)
                # These occur on weekends, holidays, or when markets are closed
                if value_str in [".", "", "ND"]:
                    continue

                # FRED quotes every currency per 1 unit (JPY included, never per 100), in the series' own direction
                fred_rate = Decimal(value_str)

                # A zero rate is invalid and never occurs in real data: a safety check on a malformed answer
                if fred_rate == 0:
                    logger.warning(f"Skipping zero rate for {currency} on {rate_date}")
                    continue

                observations.append((rate_date, base, quote, fred_rate))

            except (ValueError, IndexError, ArithmeticError) as e:  # ArithmeticError: a value that is no number, the line only (X-R50)
                logger.debug(f"Skipping invalid line in FRED CSV: {line[:50]}... ({e})")
                continue

        logger.debug(f"Parsed {len(observations)} rates for {currency} from FRED")
        return observations
