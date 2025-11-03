"""
Bank of England (BOE) FX rate provider.

This provider fetches exchange rates from the Bank of England Statistical Interactive Database.
BOE provides daily rates with GBP as base currency.

API Documentation: https://www.bankofengland.co.uk/boeapps/database/
"""
import logging
from datetime import date
from decimal import Decimal

import httpx

from backend.app.services.fx import FXRateProvider, FXProviderFactory, FXServiceError

logger = logging.getLogger(__name__)


class BOEProvider(FXRateProvider):
    """
    Bank of England FX rate provider.

    Provides daily exchange rates with GBP as base currency.
    Data source: Bank of England Statistical Interactive Database (IADB).

    Coverage: ~15 major currencies (USD, EUR, JPY, CHF, AUD, etc.)
    Update frequency: Daily (weekdays only, UK business days)
    """

    # BOE API configuration
    BASE_URL = "https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp"

    # Series codes for exchange rates
    # Format: XUD{L/H}XXX where L=low, H=high, XXX=currency code
    # We use spot rates (XUDL prefix for most currencies)
    CURRENCY_SERIES = {
        'USD': 'XUDLUSS',  # US Dollar spot
        'EUR': 'XUDLERD',  # Euro spot (vs Sterling)
        'JPY': 'XUDLJYS',  # Japanese Yen spot
        'CHF': 'XUDLSFS',  # Swiss Franc spot
        'CAD': 'XUDLCDS',  # Canadian Dollar spot
        'AUD': 'XUDLADS',  # Australian Dollar spot
        'NZD': 'XUDLNDS',  # New Zealand Dollar spot
        'SEK': 'XUDLSKS',  # Swedish Krona spot
        'NOK': 'XUDLNKS',  # Norwegian Krone spot
        'DKK': 'XUDLDKS',  # Danish Krone spot
        'CNY': 'XUDLBK89', # Chinese Yuan spot
        'HKD': 'XUDLHDS',  # Hong Kong Dollar spot
        'SGD': 'XUDLSGS',  # Singapore Dollar spot
        'ZAR': 'XUDLZRS',  # South African Rand spot
        'INR': 'XUDLBK97', # Indian Rupee spot
    }

    @property
    def code(self) -> str:
        return "BOE"

    @property
    def name(self) -> str:
        return "Bank of England"

    @property
    def base_currency(self) -> str:
        return "GBP"

    @property
    def description(self) -> str:
        return "Official exchange rates from Bank of England"

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
        currencies = ['GBP'] + list(self.CURRENCY_SERIES.keys())
        return sorted(currencies)

    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str]
    ) -> dict[str, list[tuple[date, Decimal]]]:
        """
        Fetch FX rates from BOE API for given date range and currencies.

        BOE provides rates as: 1 GBP = X foreign currency

        Args:
            date_range: (start_date, end_date) inclusive
            currencies: List of currency codes (excluding GBP)

        Returns:
            Dictionary mapping currency -> [(date, rate), ...]

        Raises:
            FXServiceError: If API request fails
        """
        start_date, end_date = date_range
        results = {}

        for currency in currencies:
            # Skip GBP (base currency)
            if currency == "GBP":
                continue

            # Check if we support this currency
            if currency not in self.CURRENCY_SERIES:
                logger.warning(f"Currency {currency} not supported by BOE, skipping")
                results[currency] = []
                continue

            series_code = self.CURRENCY_SERIES[currency]

            # Build BOE API request
            # Format: XML-based API (returning CSV-like data)
            params = {
                'Datefrom': start_date.strftime('%d/%b/%Y'),
                'Dateto': end_date.strftime('%d/%b/%Y'),
                'SeriesCodes': series_code,
                'CSVF': 'TN',  # Time series, no metadata
                'UsingCodes': 'Y',
                'VPD': 'Y',
                'VFD': 'N',
            }

            try:
                # BOE requires a proper User-Agent header
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; LibreFolio/1.0; +https://github.com/librefolio)'
                }

                async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
                    response = await client.get(self.BASE_URL, params=params)
                    response.raise_for_status()

                    # Parse CSV-like response
                    observations = self._parse_response(response.text, currency)
                    results[currency] = observations

            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch FX rates for {currency} from BOE: {e}")
                raise FXServiceError(f"BOE API error for {currency}: {e}") from e
            except Exception as e:
                logger.error(f"Failed to parse BOE response for {currency}: {e}")
                raise FXServiceError(f"Unexpected BOE response format for {currency}: {e}") from e

        return results

    def _parse_response(self, response_text: str, currency: str) -> list[tuple[date, Decimal]]:
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

        lines = response_text.strip().split('\n')

        # Skip header line
        if len(lines) < 2:
            logger.warning(f"BOE response too short for {currency}")
            return []

        for line in lines[1:]:  # Skip header
            if not line.strip():
                continue

            parts = line.split(',')
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
                if not rate_str or rate_str == '':
                    continue

                # BOE gives: 1 GBP = X foreign currency
                # Example: 1 GBP = 1.27 USD
                # Return as (date, base, quote, rate)
                rate = Decimal(rate_str)

                observations.append((rate_date, self.base_currency, currency, rate))

            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping invalid line in BOE response: {line[:50]}... ({e})")
                continue

        logger.info(f"Parsed {len(observations)} rates for {currency} from BOE")
        return observations

    def _parse_boe_date(self, date_str: str) -> date:
        """
        Parse BOE date format.

        Format: "DD Mon YYYY" (e.g., "01 Jan 2025")
        """
        from datetime import datetime
        return datetime.strptime(date_str, '%d %b %Y').date()


# Auto-register provider on module import
FXProviderFactory.register(BOEProvider)

