"""
Swiss National Bank (SNB) FX rate provider.

This provider fetches exchange rates from the SNB Data Portal.
SNB provides daily rates with CHF as base currency.

API Documentation: https://data.snb.ch/en/topics/uvo#!/doc/explanations
"""
import logging
from datetime import date
from decimal import Decimal

import httpx

from backend.app.services.fx import FXRateProvider, FXProviderFactory, FXServiceError

logger = logging.getLogger(__name__)


class SNBProvider(FXRateProvider):
    """
    Swiss National Bank FX rate provider.

    Provides daily exchange rates with CHF as base currency.
    Data source: SNB Data Portal.

    Coverage: ~10 major currencies (USD, EUR, GBP, JPY, etc.)
    Update frequency: Daily (weekdays only, Swiss business days)
    """

    # SNB API configuration
    BASE_URL = "https://data.snb.ch/api/cube"
    DATASET = "devkum"  # Daily exchange rates

    # Currency mapping to SNB codes
    # SNB uses special codes in their API
    CURRENCY_CODES = {
        'USD': 'USD',  # US Dollar
        'EUR': 'EUR',  # Euro
        'GBP': 'GBP',  # British Pound
        'JPY': 'JPY',  # Japanese Yen (100 units)
        'CAD': 'CAD',  # Canadian Dollar
        'AUD': 'AUD',  # Australian Dollar
        'SEK': 'SEK',  # Swedish Krona (100 units)
        'NOK': 'NOK',  # Norwegian Krone (100 units)
        'DKK': 'DKK',  # Danish Krone (100 units)
        'CNY': 'CNY',  # Chinese Yuan
    }

    @property
    def code(self) -> str:
        return "SNB"

    @property
    def name(self) -> str:
        return "Swiss National Bank"

    @property
    def base_currency(self) -> str:
        return "CHF"

    @property
    def description(self) -> str:
        return "Official exchange rates from Swiss National Bank"

    @property
    def test_currencies(self) -> list[str]:
        """
        Common currencies that SNB should always provide.
        These are used for automated testing.
        """
        return [
            "CHF",  # Swiss Franc (base currency)
            "USD",  # US Dollar
            "EUR",  # Euro
            "GBP",  # British Pound
            "JPY",  # Japanese Yen
        ]

    @property
    def multi_unit_currencies(self) -> set[str]:
        """
        SNB quotes these currencies per 100 units instead of per 1 unit.

        These currencies have small unit values, so SNB quotes them per 100
        to make rates more readable (e.g., 100 JPY = 1.5 CHF instead of 1 JPY = 0.015 CHF).
        """
        return {'JPY', 'SEK', 'NOK', 'DKK'}

    async def get_supported_currencies(self) -> list[str]:
        """
        Get list of supported currencies.

        SNB has a fixed list of currencies, so we return the static list.

        Returns:
            List of ISO 4217 currency codes supported by SNB
        """
        # Include CHF as base currency + all quote currencies
        currencies = ['CHF'] + list(self.CURRENCY_CODES.keys())
        return sorted(currencies)

    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str]
    ) -> dict[str, list[tuple[date, Decimal]]]:
        """
        Fetch FX rates from SNB API for given date range and currencies.

        SNB provides rates as: X CHF = 1 foreign currency (or 100 for some currencies)
        We need to invert to get: 1 CHF = X foreign currency

        Args:
            date_range: (start_date, end_date) inclusive
            currencies: List of currency codes (excluding CHF)

        Returns:
            Dictionary mapping currency -> [(date, rate), ...]

        Raises:
            FXServiceError: If API request fails
        """
        start_date, end_date = date_range
        results = {}

        for currency in currencies:
            # Skip CHF (base currency)
            if currency == "CHF":
                continue

            # Check if we support this currency
            if currency not in self.CURRENCY_CODES:
                logger.warning(f"Currency {currency} not supported by SNB, skipping")
                results[currency] = []
                continue

            snb_code = self.CURRENCY_CODES[currency]

            # Build SNB API request
            # Format: REST API returning CSV
            # URL pattern: /api/cube/{dataset}/data/csv/en
            # Series format for exchange rates: {FREQ}.{UNIT}.{CURRENCY}
            url = f"{self.BASE_URL}/{self.DATASET}/data/csv/en"
            params = {
                'from': start_date.isoformat(),
                'to': end_date.isoformat(),
                # Series: D (daily), M (monthly average), currency code
                # We want: D.M.{currency} = daily, monthly average for currency
                # Example: D.M.USD for USD/CHF exchange rate
            }

            # Add series parameter - SNB uses dimension:value format
            # The series structure is: D (daily) . M (monthly avg) . {currency}
            params['series'] = f'D.M.{snb_code}'

            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()

                    # Parse CSV response
                    observations = self._parse_csv(response.text, currency)
                    results[currency] = observations

            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch FX rates for {currency} from SNB: {e}")
                raise FXServiceError(f"SNB API error for {currency}: {e}") from e
            except Exception as e:
                logger.error(f"Failed to parse SNB response for {currency}: {e}")
                raise FXServiceError(f"Unexpected SNB response format for {currency}: {e}") from e

        return results

    def _parse_csv(self, csv_text: str, currency: str) -> list[tuple[date, Decimal]]:
        """
        Parse SNB CSV response.

        CSV Format:
        Date,Value
        2025-01-01,1.0850
        2025-01-02,1.0860

        Note: SNB gives rates as X CHF = 1 foreign currency (or 100 for some)
        We need to invert and adjust for multi-unit currencies.

        Args:
            csv_text: Raw CSV text from SNB
            currency: Currency code being parsed

        Returns:
            List of (date, rate) tuples
        """
        observations = []

        lines = csv_text.strip().split('\n')

        # Skip header
        if len(lines) < 2:
            logger.warning(f"SNB response too short for {currency}")
            return []

        is_multi_unit = currency in self.multi_unit_currencies

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

                # Parse rate value from CSV
                rate_str = parts[1].strip()

                # Skip empty values (no data available for this date)
                # This can happen on weekends, holidays, or during API maintenance
                if not rate_str or rate_str == '':
                    continue

                # SNB gives: X CHF = 1 foreign currency (or 100 for multi-unit)
                # Example: 0.9 CHF = 1 USD
                # Example: 1.5 CHF = 100 JPY
                # 
                # We adjust multi-unit to per-1-unit, then return raw rate
                snb_rate = Decimal(rate_str)

                # Skip zero rates to avoid division by zero
                # Zero rates are invalid and should never occur in real data
                # This is a safety check to prevent crashes on malformed API responses
                if snb_rate == 0:
                    logger.warning(f"Skipping zero rate for {currency} on {rate_date}")
                    continue

                # Adjust multi-unit currencies to per-1-unit basis
                # Multi-unit currencies (JPY, SEK, NOK, DKK) are quoted per 100 units
                if is_multi_unit:
                    # SNB quotes per 100 units, so: snb_rate CHF = 100 JPY
                    # Adjust to: (snb_rate/100) CHF = 1 JPY
                    # Example: 1.5 CHF = 100 JPY → 0.015 CHF = 1 JPY
                    rate_per_unit = snb_rate / Decimal("100")
                else:
                    # SNB quotes per 1 unit already
                    # Example: 0.9 CHF = 1 USD
                    rate_per_unit = snb_rate

                # Return: (date, base=foreign, quote=CHF, rate)
                # Example: 1 USD = 0.9 CHF → (date, 'USD', 'CHF', 0.9)
                observations.append((rate_date, currency, self.base_currency, rate_per_unit))

            except (ValueError, IndexError, ZeroDivisionError) as e:
                logger.debug(f"Skipping invalid line in SNB CSV: {line[:50]}... ({e})")
                continue

        logger.info(f"Parsed {len(observations)} rates for {currency} from SNB")
        return observations


# Auto-register provider on module import
FXProviderFactory.register(SNBProvider)

