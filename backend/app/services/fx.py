"""
FX (Foreign Exchange) service.
Handles currency conversion and FX rate fetching from ECB (European Central Bank).
"""
import logging
from datetime import date
from decimal import Decimal

import httpx
from sqlmodel import select

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
    session,  # AsyncSession
    date_range: tuple[date, date],
    currencies: list[str]
    ) -> int:
    """
    Synchronize FX rates from ECB API to the database.

    This function fetches rates from ECB and UPSERTS them into the database:
    - If a rate doesn't exist → INSERT new rate
    - If a rate already exists → UPDATE with fresh data from ECB

    This ensures that:
    - All rates are present (no gaps)
    - All rates are up-to-date (corrections from ECB are applied)
    - Manual data is replaced with authoritative ECB data when they are finally available

    ECB provides rates as: 1 EUR = X currency
    We store them alphabetically ordered (base < quote).

    Args:
        session: Database session
        date_range: Tuple of (start_date, end_date) inclusive
        currencies: List of currency codes to sync (e.g., ["USD", "GBP"])

    Returns:
        Number of rates with changes (new inserts + updates with value changes, excludes refreshes with no change)

    Raises:
        FXServiceError: If API request fails
    """
    start_date, end_date = date_range
    inserted_count = 0
    total_changed_count = 0  # Total changes across all currencies (new + updated with value change)

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
        result = await session.execute(existing_stmt)
        existing_rates = result.scalars().all()
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

                # ECB returns empty body (Content-Length: 0) when no data available
                # This is normal for weekends/holidays - not an error
                if not response.text:
                    logger.info(
                        f"No FX rates available for {currency} ({start_date} to {end_date}). "
                        f"This is normal for weekends/holidays when ECB doesn't publish rates."
                    )
                    continue  # Skip this currency, move to next one

                # Parse JSON (at this point we know body is not empty)
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

                # OPTIMIZATION: Batch UPSERT all observations for this currency
                from sqlalchemy.dialects.sqlite import insert
                from sqlalchemy import func

                changed_count = 0  # Count only actual changes (new inserts + updates with value change)
                refreshed_count = 0  # Count updates with no value change

                # Track changes before batch insert (for logging)
                for rate_date, rate_value in observations:
                    old_rate = None
                    if rate_date in existing_dates:
                        existing_rate = next(r for r in existing_rates if r.date == rate_date)
                        old_rate = existing_rate.rate


                    # Track changes for logging
                    if old_rate is not None:
                        # This was an UPDATE
                        if old_rate != rate_value:
                            changed_count += 1  # Count as change
                            logger.info(f"Updated FX rate: {base}/{quote} on {rate_date}: {old_rate} → {rate_value}")
                        else:
                            refreshed_count += 1  # Count as refresh (no change)
                            logger.debug(f"Refreshed FX rate: {base}/{quote} on {rate_date} (unchanged: {rate_value})")
                    else:
                        # This was an INSERT
                        inserted_count += 1
                        changed_count += 1  # Count as change
                        logger.debug(f"Inserted FX rate: {base}/{quote} = {rate_value} on {rate_date}")

                # OPTIMIZATION: Single batch INSERT for all observations of this currency
                if observations:
                    values_list = [
                        {
                            'date': rate_date,
                            'base': base,
                            'quote': quote,
                            'rate': rate_value,
                            'source': 'ECB',
                            'fetched_at': func.current_timestamp()
                        }
                        for rate_date, rate_value in observations
                    ]

                    # Single batch INSERT statement
                    batch_stmt = insert(FxRate).values(values_list)

                    # On conflict: update all fields
                    batch_stmt = batch_stmt.on_conflict_do_update(
                        index_elements=['date', 'base', 'quote'],
                        set_={
                            'rate': batch_stmt.excluded.rate,
                            'source': batch_stmt.excluded.source,
                            'fetched_at': func.current_timestamp()
                        }
                    )

                    # Execute single batch statement (replaces N individual executes)
                    await session.execute(batch_stmt)

                await session.commit()

                # Add to total changed count
                total_changed_count += changed_count

                # Log summary with details
                updated_with_change = changed_count - inserted_count  # Updates that had value changes

                if inserted_count > 0 and updated_with_change > 0:
                    logger.info(f"Synced {currency}: {len(observations)} fetched, {inserted_count} new + {updated_with_change} changed ({refreshed_count} unchanged)")
                elif updated_with_change > 0:
                    logger.info(f"Synced {currency}: {len(observations)} fetched, {updated_with_change} changed ({refreshed_count} unchanged)")
                elif inserted_count > 0:
                    logger.info(f"Synced {currency}: {len(observations)} fetched, {inserted_count} new ({refreshed_count} unchanged)")
                else:
                    logger.info(f"Synced {currency}: {len(observations)} fetched, all unchanged")

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch FX rates for {currency}: {e}")
            raise FXServiceError(f"ECB API error for {currency}: {e}") from e
        except ValueError as e:
            # This catches json.JSONDecodeError (which is a subclass of ValueError)
            # Should not happen now that we check for empty body, but kept as safety net
            logger.error(f"Failed to parse ECB JSON response for {currency}: {e}")
            logger.error(f"Response body preview: {response.text[:500] if 'response' in locals() else 'N/A'}")
            raise FXServiceError(f"Invalid JSON response from ECB for {currency}: {e}") from e
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse ECB response structure for {currency}: {e}")
            raise FXServiceError(f"Unexpected ECB response format for {currency}: {e}") from e

    return total_changed_count


async def convert(
    session,  # AsyncSession
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    as_of_date: date,
    return_rate_info: bool = False
    ) -> Decimal | tuple[Decimal, date, bool]:
    """
    Convert a single amount from one currency to another.
    This is a convenience wrapper around convert_bulk() for single conversions.

    Args:
        session: Database session
        amount: Amount to convert
        from_currency: Source currency code (ISO 4217)
        to_currency: Target currency code (ISO 4217)
        as_of_date: Date for which to use the FX rate
        return_rate_info: If True, return (amount, rate_date, backward_fill_applied)

    Returns:
        If return_rate_info=False: Converted amount
        If return_rate_info=True: Tuple of (converted_amount, rate_date, backward_fill_applied)

    Raises:
        RateNotFoundError: If no rate is found at all for this currency pair
    """
    # Call bulk version with single item (raise_on_error=True for backward compatibility)
    results, errors = await convert_bulk(
        session,
        [(amount, from_currency, to_currency, as_of_date)],
        raise_on_error=True
    )

    converted_amount, rate_date, backward_fill_applied = results[0]

    if return_rate_info:
        return converted_amount, rate_date, backward_fill_applied
    return converted_amount


async def convert_bulk(
    session,  # AsyncSession
    conversions: list[tuple[Decimal, str, str, date]],  # [(amount, from, to, date), ...]
    raise_on_error: bool = True
    ) -> tuple[list[tuple[Decimal, date, bool] | None], list[str]]:
    """
    Convert multiple amounts in a single batch operation.
    Uses unlimited backward-fill: if rate for exact date is not found,
    uses the most recent rate available (no time limit).

    Rates are stored alphabetically (base < quote): 1 base = rate * quote

    Args:
        session: Database session
        conversions: List of (amount, from_currency, to_currency, as_of_date) tuples
        raise_on_error: If True, raise on first error. If False, collect errors and continue

    Returns:
        Tuple of (results, errors) where:
        - results: List of (converted_amount, rate_date, backward_fill_applied) or None for failed conversions
        - errors: List of error messages for failed conversions

        If raise_on_error=True, raises on first error (legacy behavior)

    Raises:
        RateNotFoundError: If any conversion fails and raise_on_error=True
    """
    if not conversions:
        return ([], [])

    # OPTIMIZATION: Collect all unique currency pairs needed
    pairs_needed = {}  # {(base, quote, max_date): [indices_needing_this_pair]}
    conversion_metadata = []  # Store metadata for each conversion

    for idx, (amount, from_currency, to_currency, as_of_date) in enumerate(conversions):
        # Identity conversions don't need DB lookup
        if from_currency == to_currency:
            conversion_metadata.append({
                'idx': idx,
                'amount': amount,
                'from': from_currency,
                'to': to_currency,
                'date': as_of_date,
                'identity': True
            })
            continue

        # Determine alphabetical ordering
        if from_currency < to_currency:
            base, quote = from_currency, to_currency
            direct = True
        else:
            base, quote = to_currency, from_currency
            direct = False

        conversion_metadata.append({
            'idx': idx,
            'amount': amount,
            'from': from_currency,
            'to': to_currency,
            'date': as_of_date,
            'identity': False,
            'base': base,
            'quote': quote,
            'direct': direct
        })

        # Group conversions by pair and max date needed
        # We'll fetch the most recent rate for each pair that satisfies all dates
        pair_key = (base, quote)
        if pair_key not in pairs_needed:
            pairs_needed[pair_key] = {'max_date': as_of_date, 'indices': []}
        else:
            # Track the maximum date needed for this pair
            if as_of_date > pairs_needed[pair_key]['max_date']:
                pairs_needed[pair_key]['max_date'] = as_of_date

        pairs_needed[pair_key]['indices'].append(idx)

    # OPTIMIZATION: Single batch query for all needed rates
    # Build OR clauses for all pairs
    if pairs_needed:
        from sqlalchemy import or_, and_

        conditions = []
        for (base, quote), info in pairs_needed.items():
            # For each pair, get all rates up to the max date needed
            conditions.append(
                and_(
                    FxRate.base == base,
                    FxRate.quote == quote,
                    FxRate.date <= info['max_date']
                )
            )

        # Single query fetching all rates needed
        stmt = select(FxRate).where(or_(*conditions)).order_by(
            FxRate.base, FxRate.quote, FxRate.date.desc()
        )

        result = await session.execute(stmt)
        all_rates = result.scalars().all()

        # Build lookup dictionary: {(base, quote): [rates_sorted_desc_by_date]}
        rates_lookup = {}
        for rate in all_rates:
            pair_key = (rate.base, rate.quote)
            if pair_key not in rates_lookup:
                rates_lookup[pair_key] = []
            rates_lookup[pair_key].append(rate)
    else:
        rates_lookup = {}

    # Process conversions using cached rates
    results = []
    errors = []

    for meta in conversion_metadata:
        idx = meta['idx']

        try:
            # Identity conversion
            if meta['identity']:
                results.append((meta['amount'], meta['date'], False))
                continue

            # Find appropriate rate for this conversion
            pair_key = (meta['base'], meta['quote'])
            pair_rates = rates_lookup.get(pair_key, [])

            # Find first rate <= requested date (backward-fill)
            rate_record = None
            for rate in pair_rates:
                if rate.date <= meta['date']:
                    rate_record = rate
                    break

            if not rate_record:
                # No rate found at all for this pair
                error_msg = (
                    f"No FX rate found for {meta['base']}/{meta['quote']} on or before {meta['date']}. "
                    f"Please sync rates using POST /api/v1/fx/sync"
                )
                if raise_on_error:
                    raise RateNotFoundError(f"Conversion failed at index {idx}: {error_msg}")
                else:
                    errors.append(f"Conversion {idx}: {error_msg}")
                    results.append(None)
                    continue

            # Track if backward-fill was applied
            backward_fill_applied = rate_record.date < meta['date']

            # Log if using backward-fill
            if backward_fill_applied:
                days_back = (meta['date'] - rate_record.date).days
                logger.info(
                    f"Using backward-fill: rate for {meta['base']}/{meta['quote']} from {rate_record.date} "
                    f"({days_back} days back, requested: {meta['date']})"
                )

            # Apply conversion
            if meta['direct']:
                converted = meta['amount'] * rate_record.rate
            else:
                converted = meta['amount'] / rate_record.rate

            results.append((converted, rate_record.date, backward_fill_applied))

        except RateNotFoundError:
            if raise_on_error:
                raise
            # Already appended error above
        except Exception as e:
            error_msg = f"Conversion {idx} failed: {str(e)}"
            if raise_on_error:
                raise RateNotFoundError(error_msg) from e
            else:
                errors.append(error_msg)
                results.append(None)

    return (results, errors)


async def upsert_rates_bulk(
    session,  # AsyncSession
    rates: list[tuple[date, str, str, Decimal, str]]  # [(date, base, quote, rate, source), ...]
    ) -> list[tuple[bool, str]]:  # [(success, action), ...]
    """
    Insert or update multiple FX rates in a single batch operation.

    Args:
        session: Database session
        rates: List of (date, base, quote, rate, source) tuples

    Returns:
        List of (success, action) tuples where action is 'inserted' or 'updated'
        Results are in the same order as input rates

    Raises:
        ValueError: If validation fails for any rate
    """
    from sqlalchemy.dialects.sqlite import insert
    from sqlalchemy import func, select as sql_select, or_, and_

    if not rates:
        return []

    # Validate and normalize all rates first
    normalized_rates = []
    for rate_date, base, quote, rate_value, source in rates:
        base = base.upper()
        quote = quote.upper()

        if base == quote:
            raise ValueError(f"Base and quote must be different (got {base} == {quote})")

        if rate_value <= 0:
            raise ValueError(f"Rate must be positive (got {rate_value})")

        # Ensure alphabetical ordering
        if base > quote:
            base, quote = quote, base
            rate_value = Decimal("1") / rate_value

        normalized_rates.append((rate_date, base, quote, rate_value, source))

    # OPTIMIZATION: Single batch query to check all existing rates
    conditions = []
    for rate_date, base, quote, _, _ in normalized_rates:
        conditions.append(
            and_(
                FxRate.date == rate_date,
                FxRate.base == base,
                FxRate.quote == quote
            )
        )

    # Fetch all existing rates in one query
    stmt = sql_select(FxRate).where(or_(*conditions))
    result = await session.execute(stmt)
    existing_rates = result.scalars().all()

    # Build lookup set for existing rates
    existing_keys = {
        (rate.date, rate.base, rate.quote)
        for rate in existing_rates
    }

    # OPTIMIZATION: Prepare results tracking (before batch insert)
    results = []
    for rate_date, base, quote, rate_value, source in normalized_rates:
        key = (rate_date, base, quote)
        action = "updated" if key in existing_keys else "inserted"
        results.append((True, action))

    # OPTIMIZATION: Single batch INSERT with multiple VALUES
    # Prepare all values for batch insert
    values_list = [
        {
            'date': rate_date,
            'base': base,
            'quote': quote,
            'rate': rate_value,
            'source': source,
            'fetched_at': func.current_timestamp()
        }
        for rate_date, base, quote, rate_value, source in normalized_rates
    ]

    # Single batch INSERT statement (all rates at once)
    batch_insert = insert(FxRate).values(values_list)

    # On conflict: update all fields for each row
    batch_insert = batch_insert.on_conflict_do_update(
        index_elements=['date', 'base', 'quote'],
        set_={
            'rate': batch_insert.excluded.rate,
            'source': batch_insert.excluded.source,
            'fetched_at': func.current_timestamp()
        }
    )

    # Execute single batch statement (replaces N individual executes)
    await session.execute(batch_insert)

    # Single commit for all upserts
    await session.commit()
    return results


