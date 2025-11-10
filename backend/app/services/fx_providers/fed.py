"""
Federal Reserve (FED) FX rate provider.

This provider fetches exchange rates from FRED (Federal Reserve Economic Data).
FED provides daily rates with USD as base currency.

API Documentation: https://fred.stlouisfed.org/docs/api/fred/
Data Source: H.10 Foreign Exchange Rates via FRED
Note: No API key required for basic usage
"""
import logging
from datetime import date
from decimal import Decimal

import httpx

from backend.app.services.fx import FXRateProvider, FXServiceError
from backend.app.services.provider_registry import register_provider, FXProviderRegistry

logger = logging.getLogger(__name__)


@register_provider(FXProviderRegistry)
class FEDProvider(FXRateProvider):
    """
    Federal Reserve FX rate provider via FRED API.

    Provides daily exchange rates with USD as base currency.
    Data source: FRED (Federal Reserve Economic Data) - H.10 Release.

    Coverage: ~15 major currencies (EUR, GBP, JPY, CAD, CHF, AUD, etc.)
    Update frequency: Daily (weekdays only, US business days)

    Note: FRED provides rates as "USD per foreign currency" (e.g., USD per EUR)
    We need to invert these to get "foreign currency per USD"
    """

    # FRED CSV Download (no API key needed - uses public data download)
    BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

    # FRED Series IDs for FX rates
    # Format: DEXXX where XX = country code
    # These rates are quoted as: USD per 1 foreign currency
    # Example: DEXUSEU = USD per 1 EUR
    CURRENCY_SERIES = {
        'EUR': 'DEXUSEU',  # Euro (USD per EUR)
        'GBP': 'DEXUSUK',  # British Pound (USD per GBP)
        'JPY': 'DEXJPUS',  # Japanese Yen (USD per JPY)
        'CAD': 'DEXCAUS',  # Canadian Dollar (USD per CAD)
        'CHF': 'DEXSZUS',  # Swiss Franc (USD per CHF)
        'AUD': 'DEXUSAL',  # Australian Dollar (USD per AUD)
        'SEK': 'DEXSDUS',  # Swedish Krona (USD per SEK)
        'DKK': 'DEXDNUS',  # Danish Krone (USD per DKK)
        'NOK': 'DEXNOUS',  # Norwegian Krone (USD per NOK)
        'CNY': 'DEXCHUS',  # Chinese Yuan (USD per CNY)
        'INR': 'DEXINUS',  # Indian Rupee (USD per INR)
        'BRL': 'DEXBZUS',  # Brazilian Real (USD per BRL)
        'MXN': 'DEXMXUS',  # Mexican Peso (USD per MXN)
        'ZAR': 'DEXSFUS',  # South African Rand (USD per ZAR)
        'SGD': 'DEXSIUS',  # Singapore Dollar (USD per SGD)
        'HKD': 'DEXHKUS',  # Hong Kong Dollar (USD per HKD)
        'KRW': 'DEXKOUS',  # South Korean Won (USD per KRW)
        'TWD': 'DEXTAUS',  # Taiwan Dollar (USD per TWD)
        'NZD': 'DEXUSNZ',  # New Zealand Dollar (USD per NZD)
        'THB': 'DEXTHUS',  # Thai Baht (USD per THB)
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
    def base_currency(self) -> str:
        return "USD"

    @property
    def description(self) -> str:
        return "Official exchange rates from Federal Reserve (H.10 Release)"

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
        currencies = ['USD'] + list(self.CURRENCY_SERIES.keys())
        return sorted(currencies)

    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str],
        base_currency: str | None = None
        ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch FX rates from FRED API for given date range and currencies.

        FRED provides rates as: USD per 1 foreign currency
        We need to invert to get: foreign currency per 1 USD

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
            raise ValueError(
                f"FED provider only supports USD as base currency, got {base_currency}"
                )

        start_date, end_date = date_range
        results = {}

        for currency in currencies:
            # Skip USD (base currency)
            if currency == "USD":
                continue

            # Check if we support this currency
            if currency not in self.CURRENCY_SERIES:
                logger.warning(f"Currency {currency} not supported by FED, skipping")
                results[currency] = []
                continue

            series_id = self.CURRENCY_SERIES[currency]

            # Build FRED CSV download request (no API key needed)
            # Uses public fredgraph.csv endpoint
            params = {
                'id': series_id,
                'cosd': start_date.isoformat(),
                'coed': end_date.isoformat(),
                }

            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    response = await client.get(self.BASE_URL, params=params)
                    response.raise_for_status()

                    # Parse CSV with date range filter
                    observations = self._parse_csv(response.text, currency, start_date, end_date)
                    results[currency] = observations

            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch FX rates for {currency} from FED/FRED: {e}")
                raise FXServiceError(f"FED/FRED API error for {currency}: {e}") from e
            except Exception as e:
                logger.error(f"Failed to parse FED/FRED response for {currency}: {e}")
                raise FXServiceError(f"Unexpected FED/FRED response format for {currency}: {e}") from e

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

        lines = csv_text.strip().split('\n')

        # Skip header
        if len(lines) < 2:
            logger.warning(f"FRED CSV response too short for {currency}")
            return []

        for line in lines[1:]:  # Skip header
            if not line.strip():
                continue

            parts = line.split(',')
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
                if value_str in ['.', '', 'ND']:
                    continue

                # FRED gives: USD per 1 foreign currency (ALL currencies per 1 unit)
                # Example: DEXUSEU = 1.0850 means 1 EUR = 1.0850 USD
                # Example: DEXJPUS = 0.0067 means 1 JPY = 0.0067 USD (NOT per 100!)
                # Return as provided: (date, quote_currency, base_currency, rate)
                # Note: FRED quotes backwards (foreign/USD not USD/foreign)
                fred_rate = Decimal(value_str)

                # Skip zero rates to avoid division by zero
                # Zero rates are invalid and should never occur in real data
                # This is a safety check to prevent crashes on malformed API responses
                if fred_rate == 0:
                    logger.warning(f"Skipping zero rate for {currency} on {rate_date}")
                    continue

                # FRED quotes as: 1 foreign_currency = fred_rate USD
                # Return tuple: (date, base=foreign, quote=USD, rate)
                # Example: 1 EUR = 1.08 USD → (date, 'EUR', 'USD', 1.08)
                observations.append((rate_date, currency, self.base_currency, fred_rate))


            except (ValueError, IndexError, ZeroDivisionError) as e:
                logger.debug(f"Skipping invalid line in FRED CSV: {line[:50]}... ({e})")
                continue

        logger.info(f"Parsed {len(observations)} rates for {currency} from FRED")
        return observations
