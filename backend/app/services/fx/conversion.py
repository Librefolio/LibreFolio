"""
FX conversion: the rate of a chained route (``compute_chain_rate``) and the bulk conversion of amounts with
backward-fill (``convert_bulk``).
"""

from bisect import bisect_right
from collections import namedtuple
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, or_
from sqlalchemy import select as sql_select

from backend.app.db.models import FxRate
from backend.app.db.precision import storable_fx_rate, usable_fx_rate_bounds
from backend.app.logging_config import get_logger
from backend.app.schemas.common import Currency
from backend.app.services.fx.base import RateNotFoundError
from backend.app.utils.sql_chunks import OR_TERMS_PER_QUERY

logger = get_logger(__name__)

#: How many pairs one rate query asks for (R13-SEC9-2): SQLite refuses an OR of about a thousand terms («Expression tree
#: is too large»), so a request with more pairs reads them in several queries. The one chunk size of every OR statement,
#: ``utils/sql_chunks.OR_TERMS_PER_QUERY`` (MF-SEC9a), under the name the FX queries know it by.
FX_PAIRS_PER_QUERY = OR_TERMS_PER_QUERY

# ============================================================================
# CHAIN COMPUTATION
# ============================================================================


def _usable_rate(rate: Decimal | None) -> bool:
    """A leg rate a chain may use (X-R38): one ``fx_rates.rate`` can keep (finite, at most 14 digits before the decimal
    point, not 0 at 10 decimal places), above 0."""
    return rate is not None and storable_fx_rate(rate) is not None and rate > 0


def compute_chain_rate(
    steps: list[dict],
    leg_rates: dict[tuple, Decimal],
    target_date: date,
) -> Decimal | None:
    """
    Compute the composite rate for a chain of conversions on a specific date.

    For each step (from_cur, to_cur):
    - Normalize alphabetically: (min, max) for lookup in leg_rates
    - If from_cur < to_cur (direct order): multiply by rate
    - If from_cur > to_cur (inverse order): multiply by 1/rate

    **Strict date matching**: ALL legs must have data for the exact target_date.
    If any leg is missing, returns None and this date is skipped.
    This means chains using providers with sparse data (e.g. SNB monthly)
    will only produce rates on dates where every leg has fresh data.

    A leg ``fx_rates.rate`` could not keep (0, an infinite one, 20 digits before the decimal point, NaN) counts as
    missing (X-R38): never a division by zero, never an infinite or absurd rate.

    Returns: composite rate, or None if any leg is missing or unusable for this date.
    """
    composite = Decimal("1")
    for step in steps:
        fc = step["from"]
        tc = step["to"]
        # Normalize alphabetically for lookup
        norm_base = min(fc, tc)
        norm_quote = max(fc, tc)
        key = (norm_base, norm_quote, target_date)
        rate = leg_rates.get(key)
        if not _usable_rate(rate):
            return None
        if fc < tc:
            # Direct order: multiply by rate
            composite *= rate
        else:
            # Inverse order: multiply by 1/rate
            composite *= Decimal("1") / rate
    return composite


# ============================================================================
# CURRENCY CONVERSION FUNCTIONS
# ============================================================================


# Lightweight (date, rate) record used by convert_bulk's lookup.
_RateRow = namedtuple("_RateRow", ["date", "rate"])


async def convert_bulk(  # noqa: C901 — per-item conversion dispatch with backward-fill search
    session,  # AsyncSession
    conversions: list[tuple[Currency, str, date]],  # [(amount_currency, to_currency, date), ...]
    raise_on_error: bool = True,
) -> tuple[list[tuple[Currency, date, bool] | None], list[str]]:
    """
    Convert multiple Currency amounts in a single batch operation.
    Uses unlimited backward-fill: if rate for exact date is not found,
    uses the most recent rate available (no time limit).

    ⚡ BREAKING CHANGE: Now accepts/returns Currency objects instead of Decimal.

    Rates are stored alphabetically (base < quote): 1 base = rate * quote

    Only usable rates are read (X-R38): a legacy rate ``fx_rates.rate`` cannot keep, written by an older release (an
    infinite one, 0, 20 digits before the decimal point), is a missing rate for its date, backward-filled over like a
    date without a row, or the missing-rate error. Never a division by zero, never an infinite amount.

    Args:
        session: Database session
        conversions: List of (Currency, to_currency, as_of_date) tuples
                     where Currency contains amount + from_currency
        raise_on_error: If True, raise on first error. If False, collect errors and continue

    Returns:
        Tuple of (results, errors) where:
        - results: List of (Currency, rate_date, backward_fill_applied) or None for failed conversions
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

    for idx, (amount_currency, to_currency, as_of_date) in enumerate(conversions):
        # Extract from Currency object
        amount = amount_currency.amount
        from_currency = amount_currency.code

        # Identity conversions don't need DB lookup
        if from_currency == to_currency:
            conversion_metadata.append(
                {
                    "idx": idx,
                    "amount": amount,
                    "from": from_currency,
                    "to": to_currency,
                    "date": as_of_date,
                    "identity": True,
                }
            )
            continue

        # Determine alphabetical ordering
        if from_currency < to_currency:
            base, quote = from_currency, to_currency
            direct = True
        else:
            base, quote = to_currency, from_currency
            direct = False

        conversion_metadata.append(
            {
                "idx": idx,
                "amount": amount,
                "from": from_currency,
                "to": to_currency,
                "date": as_of_date,
                "identity": False,
                "base": base,
                "quote": quote,
                "direct": direct,
            }
        )

        # Group conversions by pair and max date needed
        # We'll fetch the most recent rate for each pair that satisfies all dates
        pair_key = (base, quote)
        if pair_key not in pairs_needed:
            pairs_needed[pair_key] = {"min_date": as_of_date, "max_date": as_of_date, "indices": []}
        else:
            # Track the date window needed for this pair
            if as_of_date > pairs_needed[pair_key]["max_date"]:
                pairs_needed[pair_key]["max_date"] = as_of_date
            if as_of_date < pairs_needed[pair_key]["min_date"]:
                pairs_needed[pair_key]["min_date"] = as_of_date

        pairs_needed[pair_key]["indices"].append(idx)

    # OPTIMIZATION: one query for all needed rates — in chunks of pairs (R13-SEC9-2): SQLite refuses an OR of about a
    # thousand terms («Expression tree is too large», a 500), so each query holds at most FX_PAIRS_PER_QUERY of them
    if pairs_needed:
        # Only the rates a conversion may use, in the anchor too: a legacy unusable rate is skipped like a date without
        # a row (X-R38)
        smallest_rate, first_refused_rate = usable_fx_rate_bounds()
        usable = and_(FxRate.rate >= smallest_rate, FxRate.rate < first_refused_rate)

        conditions = []
        for (base, quote), info in pairs_needed.items():
            # Only the window the conversions can use: from the last rate on/before the
            # earliest requested date (the backward-fill anchor) up to the latest date.
            # Without the lower bound every call loaded the pair's whole history, which
            # made per-day portfolio conversions load millions of rows.
            anchor = sql_select(func.max(FxRate.date)).where(FxRate.base == base, FxRate.quote == quote, FxRate.date <= info["min_date"], usable).scalar_subquery()
            conditions.append(
                and_(
                    FxRate.base == base,
                    FxRate.quote == quote,
                    FxRate.date <= info["max_date"],
                    FxRate.date >= func.coalesce(anchor, info["min_date"]),
                    usable,
                )
            )

        # Build lookup: {(base, quote): ([dates ascending], [rates])} for bisect (plain columns: no ORM object per row)
        rates_lookup = {}
        for start in range(0, len(conditions), FX_PAIRS_PER_QUERY):
            stmt = sql_select(FxRate.base, FxRate.quote, FxRate.date, FxRate.rate).where(or_(*conditions[start : start + FX_PAIRS_PER_QUERY])).order_by(FxRate.base, FxRate.quote, FxRate.date)
            result = await session.execute(stmt)
            for rate_base, rate_quote, rate_date, rate_value in result.all():
                dates, values = rates_lookup.setdefault((rate_base, rate_quote), ([], []))
                dates.append(rate_date)
                values.append(rate_value)
    else:
        rates_lookup = {}

    # Process conversions using cached rates
    results = []
    errors = []

    for meta in conversion_metadata:
        idx = meta["idx"]

        try:
            # Identity conversion - same currency, return as Currency object
            if meta["identity"]:
                result_currency = Currency(code=meta["to"], amount=meta["amount"])
                results.append((result_currency, meta["date"], False))
                continue

            # Find appropriate rate for this conversion
            pair_key = (meta["base"], meta["quote"])
            pair_dates, pair_values = rates_lookup.get(pair_key, ([], []))

            # Find the latest rate <= requested date (backward-fill)
            pos = bisect_right(pair_dates, meta["date"])
            rate_record = _RateRow(pair_dates[pos - 1], pair_values[pos - 1]) if pos else None

            if not rate_record:
                # No rate found at all for this pair
                error_msg = f"No FX rate found for {meta['base']}/{meta['quote']} on or before {meta['date']}. " f"Please sync rates using POST /api/v1/fx/currencies/sync"
                if raise_on_error:
                    raise RateNotFoundError(f"Conversion failed at index {idx}: {error_msg}")
                else:
                    errors.append(f"Conversion {idx}: {error_msg}")
                    results.append(None)
                    continue

            # Track if backward-fill was applied
            backward_fill_applied = rate_record.date < meta["date"]

            # Log if using backward-fill
            if backward_fill_applied:
                days_back = (meta["date"] - rate_record.date).days
                logger.debug(
                    "backward_fill_applied",
                    pair=f"{meta['base']}/{meta['quote']}",
                    rate_date=str(rate_record.date),
                    requested_date=str(meta["date"]),
                    days_back=days_back,
                )

            # Apply conversion
            if meta["direct"]:
                converted_amount = meta["amount"] * rate_record.rate
            else:
                converted_amount = meta["amount"] / rate_record.rate

            # Return Currency object with target currency
            result_currency = Currency(code=meta["to"], amount=converted_amount)
            results.append((result_currency, rate_record.date, backward_fill_applied))

        except RateNotFoundError:
            if raise_on_error:
                raise
            # Already appended error above
        except Exception as e:
            error_msg = f"Conversion {idx} failed: {e!s}"
            if raise_on_error:
                raise RateNotFoundError(error_msg) from e
            else:
                errors.append(error_msg)
                results.append(None)

    return results, errors
