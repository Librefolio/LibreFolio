"""
European Central Bank (ECB) FX rate provider.

This provider fetches exchange rates from the ECB Data Portal API.
ECB provides daily rates with EUR as base currency.

API Documentation: https://data.ecb.europa.eu/help/api/overview
"""
import logging
from datetime import date
from decimal import Decimal

import httpx

from backend.app.services.fx import FXRateProvider, FXServiceError
from backend.app.services.provider_registry import register_provider, FXProviderRegistry

logger = logging.getLogger(__name__)


@register_provider(FXProviderRegistry)
class ECBProvider(FXRateProvider):
    """
    European Central Bank FX rate provider.

    Provides daily exchange rates with EUR as base currency.
    Data source: ECB Data Portal (Statistical Data Warehouse).

    Coverage: 45+ currencies including major currencies (USD, GBP, JPY, CHF, etc.)
    Update frequency: Daily (weekdays only, ECB business days)
    """

    # ECB API configuration
    BASE_URL = "https://data-api.ecb.europa.eu/service/data"
    DATASET = "EXR"  # Exchange Rates
    FREQUENCY = "D"  # Daily
    REFERENCE_AREA = "EUR"  # Base currency
    SERIES = "SP00"  # Series variation (spot rate)

    @property
    def code(self) -> str:
        return "ECB"
    
    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "European Central Bank"

    @property
    def base_currency(self) -> str:
        return "EUR"

    @property
    def test_currencies(self) -> list[str]:
        """
        Common currencies that ECB should always provide.
        These are used for automated testing.
        """
        return [
            "USD",  # US Dollar
            "GBP",  # British Pound
            "CHF",  # Swiss Franc
            "JPY",  # Japanese Yen
            "CAD",  # Canadian Dollar
            "AUD",  # Australian Dollar
            "EUR",  # Euro (base currency)
            ]

    async def get_supported_currencies(self) -> list[str]:
        """
        Fetch the list of available currencies from ECB API.

        Returns:
            List of ISO 4217 currency codes supported by ECB

        Raises:
            FXServiceError: If API request fails
        """
        # ECB API endpoint for all available currency pairs against EUR
        url = f"{self.BASE_URL}/{self.DATASET}/{self.FREQUENCY}..{self.REFERENCE_AREA}.{self.SERIES}.A"
        params = {
            "format": "jsondata",
            "detail": "dataonly",
            "lastNObservations": 1  # We only need structure, not all data
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                # Parse structure to get currency codes
                currencies = set()
                eur_found = False

                if "structure" in data:
                    dimensions = data["structure"].get("dimensions", {}).get("series", [])
                    for dim in dimensions:
                        dim_id = dim.get("id")
                        values = dim.get("values", [])

                        match dim_id:
                            case "CURRENCY":
                                # Get quote currencies (USD, GBP, etc.)
                                currencies = {v["id"] for v in values if v.get("id")}

                            case "CURRENCY_DENOM":
                                # Check for EUR in base currency dimension
                                for v in values:
                                    if v.get("id") == "EUR":
                                        eur_found = True
                                        currencies.add("EUR")
                                        break

                # Verify EUR is present
                if not eur_found:
                    logger.error("EUR not found in ECB API response, API may be malformed")
                    raise FXServiceError("EUR not found in ECB API - base currency missing")

                return sorted(list(currencies))

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch available currencies from ECB: {e}")
            raise FXServiceError(f"ECB API error: {e}") from e
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse ECB response: {e}")
            raise FXServiceError(f"Invalid ECB response format: {e}") from e

    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str],
        base_currency: str | None = None
        ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch FX rates from ECB API for given date range and currencies.

        ECB API returns rates as: 1 EUR = X currency

        Args:
            date_range: (start_date, end_date) inclusive
            currencies: List of currency codes (excluding EUR)
            base_currency: Must be None or "EUR" (ECB only supports EUR as base)

        Returns:
            Dictionary mapping currency -> [(date, base, quote, rate), ...]

        Raises:
            ValueError: If base_currency is not None and not "EUR"
            FXServiceError: If API request fails
        """
        # Validate base_currency for single-base provider
        if base_currency is not None and base_currency != "EUR":
            raise ValueError(
                f"ECB provider only supports EUR as base currency, got {base_currency}"
                )

        start_date, end_date = date_range
        results = {}

        for currency in currencies:
            # Skip EUR (base currency)
            if currency == "EUR":
                continue

            # Fetch from ECB API: D.{CURRENCY}.EUR.SP00.A
            # Returns: 1 EUR = X {CURRENCY}
            url = f"{self.BASE_URL}/{self.DATASET}/{self.FREQUENCY}.{currency}.{self.REFERENCE_AREA}.{self.SERIES}.A"
            params = {
                "format": "jsondata",
                "startPeriod": start_date.isoformat(),
                "endPeriod": end_date.isoformat()
                }

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()

                    # ECB returns empty body when no data available (weekends/holidays)
                    # This is NOT an error - it's ECB's way of saying "no rates for this period"
                    # Happens when:
                    # - Requesting weekend dates (Saturday/Sunday)
                    # - Requesting EU holidays
                    # - Requesting future dates
                    if not response.text:
                        logger.info(
                            f"No FX rates available for {currency} ({start_date} to {end_date}). "
                            f"This is normal for weekends/holidays when ECB doesn't publish rates."
                            )
                        results[currency] = []
                        continue

                    # Parse JSON response from ECB API
                    data = response.json()

                    # Extract observations from ECB's nested JSON structure
                    observations = []

                    # Check if dataSets exist (ECB returns empty dataSets on weekends/holidays)
                    if "dataSets" in data and len(data["dataSets"]) > 0:
                        series = data["dataSets"][0].get("series", {})

                        if series:
                            # ECB returns series as a dictionary with keys like "0:0:0:0"
                            # We just need the first (and usually only) series
                            first_series = next(iter(series.values()))
                            obs_data = first_series.get("observations", {})

                            # Get time period dimension to map observation indices to dates
                            # ECB structure: dimensions.observation contains TIME_PERIOD values
                            dimensions = data["structure"]["dimensions"]["observation"]
                            time_periods = next(d["values"] for d in dimensions if d["id"] == "TIME_PERIOD")

                            # Iterate through observations
                            # Format: {"0": [1.0850], "1": [1.0860], ...}
                            # Index maps to time_periods array
                            for obs_idx, obs_value in obs_data.items():
                                idx = int(obs_idx)
                                rate_date_str = time_periods[idx]["id"]  # Format: "2025-01-01"

                                # ECB gives: 1 EUR = X foreign currency
                                # obs_value is array, first element is the rate
                                # Return as (date, base, quote, rate)
                                ecb_rate = Decimal(str(obs_value[0]))
                                rate_date = date.fromisoformat(rate_date_str)

                                observations.append((rate_date, self.base_currency, currency, ecb_rate))

                    results[currency] = observations

            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch FX rates for {currency}: {e}")
                raise FXServiceError(f"ECB API error for {currency}: {e}") from e
            except (KeyError, IndexError, ValueError) as e:
                logger.error(f"Failed to parse ECB response for {currency}: {e}")
                raise FXServiceError(f"Unexpected ECB response format for {currency}: {e}") from e

        return results

