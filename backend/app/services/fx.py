"""
FX (Foreign Exchange) service.
Handles currency conversion and FX rate fetching from ECB (European Central Bank).
"""
import logging
from datetime import date
from decimal import Decimal

import httpx
from sqlmodel import Session, select

from backend.app.db.models import FxRate

logger = logging.getLogger(__name__)

# ECB API endpoints
# For detailed explanation of these parameters, see: docs/fx-implementation.md (ECB API Parameters section)
ECB_BASE_URL = "https://data-api.ecb.europa.eu/service/data"
ECB_DATASET = "EXR"  # Exchange Rates
ECB_FREQUENCY = "D"  # Daily
ECB_REFERENCE_AREA = "EUR"  # Base currency
ECB_SERIES = "SP00"  # Series variation (spot rate)


class FXServiceError(Exception):
    """Base exception for FX service errors."""
    pass


class RateNotFoundError(FXServiceError):
    """Raised when no FX rate is found for a given currency and date."""
    pass


async def get_available_currencies() -> list[str]:
    """
    Fetch the list of available currencies from ECB.

    Returns:
        List of ISO 4217 currency codes supported by ECB

    Raises:
        FXServiceError: If API request fails
    """
    # ECB API endpoint for all available currency pairs against EUR
    url = f"{ECB_BASE_URL}/{ECB_DATASET}/{ECB_FREQUENCY}..{ECB_REFERENCE_AREA}.{ECB_SERIES}.A"
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
                logger.error("EUR not found in ECB API response (CURRENCY_DENOM dimension), API may be malformed or changed")
                raise FXServiceError("EUR not found in ECB API - base currency missing")

            return sorted(list(currencies))

    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch available currencies from ECB: {e}")
        raise FXServiceError(f"ECB API error: {e}") from e
    except (KeyError, ValueError) as e:
        logger.error(f"Failed to parse ECB response: {e}")
        raise FXServiceError(f"Invalid ECB response format: {e}") from e


async def ensure_rates(
    session: Session,
    date_range: tuple[date, date],
    currencies: list[str]
) -> int:
    """
    Ensure FX rates exist in the database for the given date range and currencies.
    Fetches missing rates from ECB API and persists them.

    ECB provides rates as: 1 EUR = X currency
    We store them alphabetically ordered (base < quote).

    Args:
        session: Database session
        date_range: Tuple of (start_date, end_date) inclusive
        currencies: List of currency codes to sync (e.g., ["USD", "GBP"])

    Returns:
        Number of new rates inserted

    Raises:
        FXServiceError: If API request fails
    """
    start_date, end_date = date_range
    inserted_count = 0

    for currency in currencies:
        # Skip EUR as it's the reference currency
        if currency == "EUR":
            continue

        # Determine alphabetical ordering for storage
        # ECB gives us: 1 EUR = X currency
        if "EUR" < currency:
            # Store as EUR/currency (e.g., EUR/USD)
            base, quote = "EUR", currency
            needs_inversion = False
        else:
            # Store as currency/EUR (e.g., CHF/EUR) - invert the rate
            base, quote = currency, "EUR"
            needs_inversion = True

        # Query existing rates for this pair in the date range
        existing_stmt = select(FxRate).where(
            FxRate.base == base,
            FxRate.quote == quote,
            FxRate.date >= start_date,
            FxRate.date <= end_date
        )
        existing_rates = session.exec(existing_stmt).all()
        existing_dates = {rate.date for rate in existing_rates}

        # Fetch from ECB API: D.{CURRENCY}.EUR.SP00.A
        # Returns: 1 EUR = X {CURRENCY}
        url = f"{ECB_BASE_URL}/{ECB_DATASET}/{ECB_FREQUENCY}.{currency}.{ECB_REFERENCE_AREA}.{ECB_SERIES}.A"
        params = {
            "format": "jsondata",
            "startPeriod": start_date.isoformat(),
            "endPeriod": end_date.isoformat()
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                # Parse observations
                observations = []
                if "dataSets" in data and len(data["dataSets"]) > 0:
                    series = data["dataSets"][0].get("series", {})
                    if series:
                        # Get first (and should be only) series
                        first_series = next(iter(series.values()))
                        obs_data = first_series.get("observations", {})

                        # Get time period dimension
                        dimensions = data["structure"]["dimensions"]["observation"]
                        time_periods = next(d["values"] for d in dimensions if d["id"] == "TIME_PERIOD")

                        for obs_idx, obs_value in obs_data.items():
                            idx = int(obs_idx)
                            rate_date_str = time_periods[idx]["id"]
                            # ECB gives: 1 EUR = rate_value CURRENCY
                            ecb_rate = Decimal(str(obs_value[0]))

                            # Convert to our storage format (alphabetical base < quote)
                            stored_rate = ecb_rate if not needs_inversion else (Decimal("1") / ecb_rate)

                            observations.append((date.fromisoformat(rate_date_str), stored_rate))

                # Insert missing rates
                for rate_date, rate_value in observations:
                    if rate_date not in existing_dates:
                        fx_rate = FxRate(
                            base=base,
                            quote=quote,
                            date=rate_date,
                            rate=rate_value,
                            source="ECB"
                        )
                        session.add(fx_rate)
                        inserted_count += 1
                        logger.debug(f"Inserted FX rate: {base}/{quote} = {rate_value} on {rate_date}")

                session.commit()
                logger.info(f"Synced {currency}: {len(observations)} rates fetched, {inserted_count} new rates inserted")

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch FX rates for {currency}: {e}")
            raise FXServiceError(f"ECB API error for {currency}: {e}") from e
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Failed to parse ECB response for {currency}: {e}")
            raise FXServiceError(f"Invalid ECB response for {currency}: {e}") from e

    return inserted_count


def convert(
    session: Session,
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    as_of_date: date
) -> Decimal:
    """
    Convert an amount from one currency to another using FX rates.
    Uses forward-fill logic: if rate for exact date is not found, uses the most recent rate before that date.

    Rates are stored alphabetically (base < quote): 1 base = rate * quote

    Args:
        session: Database session
        amount: Amount to convert
        from_currency: Source currency code (ISO 4217)
        to_currency: Target currency code (ISO 4217)
        as_of_date: Date for which to use the FX rate

    Returns:
        Converted amount

    Raises:
        RateNotFoundError: If no rate is found (even with forward-fill)
    """
    # Identity conversion
    if from_currency == to_currency:
        return amount

    # Determine alphabetical ordering
    if from_currency < to_currency:
        # We need from/to, and it's stored as from/to
        base, quote = from_currency, to_currency
        direct = True
    else:
        # We need from/to, but it's stored as to/from
        base, quote = to_currency, from_currency
        direct = False

    # Query for rate with forward-fill
    stmt = select(FxRate).where(
        FxRate.base == base,
        FxRate.quote == quote,
        FxRate.date <= as_of_date
    ).order_by(FxRate.date.desc()).limit(1)

    rate_record = session.exec(stmt).first()
    if not rate_record:
        raise RateNotFoundError(
            f"No FX rate found for {base}/{quote} on or before {as_of_date}"
        )

    # Log if using forward-fill
    if rate_record.date < as_of_date:
        logger.warning(
            f"Using forward-fill: rate for {base}/{quote} from {rate_record.date} "
            f"(requested: {as_of_date})"
        )

    # Apply conversion
    # Stored: 1 base = rate * quote
    if direct:
        # from=base, to=quote: amount_from * rate = amount_to
        return amount * rate_record.rate
    else:
        # from=quote, to=base: amount_from / rate = amount_to
        return amount / rate_record.rate

