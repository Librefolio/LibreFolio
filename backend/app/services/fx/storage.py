"""
FX rate storage: the alphabetical normalization of a pair (``normalize_rate_for_storage``) and the bulk upsert and
delete of stored rates.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, or_
from sqlalchemy import delete as sql_delete
from sqlalchemy import select as sql_select
from sqlalchemy.dialects.sqlite import insert

from backend.app.db.models import FxRate
from backend.app.db.precision import fx_rate_limits_text, storable_fx_rate
from backend.app.logging_config import get_logger
from backend.app.utils.runtime.cache import clear_cache
from backend.app.utils.sql_chunks import chunks

logger = get_logger(__name__)

# ============================================================================
# SERVICE LAYER HELPER FUNCTIONS
# ============================================================================


def normalize_rate_for_storage(base: str, quote: str, rate: Decimal) -> tuple[str, str, Decimal]:
    """
    Normalize FX rate for alphabetical storage in database.

    Database stores rates with: base < quote (alphabetically)
    This function handles the conversion if needed.

    Args:
        base: Base currency (e.g., 'EUR')
        quote: Quote currency (e.g., 'USD')
        rate: Rate value (1 base = rate * quote)

    Returns:
        Tuple of (normalized_base, normalized_quote, normalized_rate)

    Example:
        normalize_rate_for_storage('EUR', 'USD', 1.08)
        → ('EUR', 'USD', 1.08) because EUR < USD

        normalize_rate_for_storage('EUR', 'CHF', 0.95)
        → ('CHF', 'EUR', 1.0526...) because CHF < EUR (inverted)
    """
    if base < quote:
        # Already in correct order
        return base, quote, rate
    else:
        # Invert: swap currencies and invert rate
        return quote, base, Decimal("1") / rate


def normalize_storable_rate(base: str, quote: str, rate: Decimal) -> tuple[str, str, Decimal] | None:
    """``normalize_rate_for_storage`` that never raises (X-R38): the pair in alphabetical order and the rate, inverted when
    base > quote, or None when the rate is not a finite number above 0, or its inverse overflows (``1 / 1E-1000000``) or
    underflows to 0 (``1 / 1E+1000030``, X-R50). Whether ``fx_rates.rate`` can keep the result is ``storable_fx_rate``'s
    answer.
    """
    if not isinstance(rate, Decimal):
        try:
            rate = Decimal(str(rate))
        except ArithmeticError:
            return None
    if not rate.is_finite() or rate <= 0:
        return None
    try:
        normalized = normalize_rate_for_storage(base, quote, rate)
    except ArithmeticError:
        return None
    # The default context does not trap an underflow: the inverse of a huge rate comes back as 0 (X-R50)
    return normalized if normalized[2] > 0 else None


def fx_rate_refusal(base: str, quote: str, rate_date: date) -> str:
    """Why a manual rate is refused (X-R38): the pair, in the order it is stored, its date and ``fx_rates.rate``'s limits."""
    return f"The rate of {min(base, quote)}/{max(base, quote)} on {rate_date.isoformat()} cannot be stored: {fx_rate_limits_text()}"


# ============================================================================
# RATE STORAGE (bulk upsert and delete)
# ============================================================================


async def upsert_rates_bulk(
    session,  # AsyncSession
    rates: list[tuple[date, str, str, Decimal, str]],  # [(date, base, quote, rate, source), ...]
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
        ValueError: If validation fails for any rate, among them a rate ``fx_rates.rate`` cannot keep once normalized
            (X-R38: at most 14 digits before the decimal point, above 0 at 10 decimal places), named with its pair,
            date and the limits; nothing of the call is written
    """

    if not rates:
        return []

    # Validate and normalize all rates first: nothing of the call is written when one is refused
    normalized_rates = []
    for rate_date, base, quote, rate_value, source in rates:
        base = base.upper()
        quote = quote.upper()

        if base == quote:
            raise ValueError(f"Base and quote must be different (got {base} == {quote})")

        if rate_value.is_finite() and rate_value <= 0:
            raise ValueError(f"Rate must be positive (got {rate_value})")

        # Alphabetical ordering, the rate inverted when base > quote; then what fx_rates.rate can keep (X-R38): 1E+400
        # was stored as a REAL inf, its inverse and 1E-11 as values that read back 0, a NaN raised, the inverse of
        # 1E-1000000 overflowed
        normalized = normalize_storable_rate(base, quote, rate_value)
        if normalized is None or storable_fx_rate(normalized[2]) is None:
            raise ValueError(fx_rate_refusal(base, quote, rate_date))
        base, quote, rate_value = normalized

        normalized_rates.append((rate_date, base, quote, rate_value, source))

    # The rates already stored, one OR term per rate: in chunks (MF-SEC9a), since SQLite refuses an OR of a thousand
    conditions = [and_(FxRate.date == rate_date, FxRate.base == base, FxRate.quote == quote) for rate_date, base, quote, _, _ in normalized_rates]
    existing_keys: set[tuple[date, str, str]] = set()
    for chunk in chunks(conditions):
        result = await session.execute(sql_select(FxRate.date, FxRate.base, FxRate.quote).where(or_(*chunk)))
        existing_keys.update((row.date, row.base, row.quote) for row in result.all())

    # OPTIMIZATION: Prepare results tracking (before batch insert)
    results = []
    for rate_date, base, quote, _rate_value, _source in normalized_rates:
        key = (rate_date, base, quote)
        action = "updated" if key in existing_keys else "inserted"
        results.append((True, action))

    # OPTIMIZATION: Single batch INSERT with multiple VALUES
    # Prepare all values for batch insert
    values_list = [
        {
            "date": rate_date,
            "base": base,
            "quote": quote,
            "rate": rate_value,
            "source": source,
            "fetched_at": func.current_timestamp(),
        }
        for rate_date, base, quote, rate_value, source in normalized_rates
    ]

    # One INSERT … ON CONFLICT per chunk, in the same transaction: six bound values a row, under SQLite's limit
    for chunk in chunks(values_list):
        batch_insert = insert(FxRate).values(list(chunk))
        batch_insert = batch_insert.on_conflict_do_update(
            index_elements=["date", "base", "quote"],
            set_={
                "rate": batch_insert.excluded.rate,
                "source": batch_insert.excluded.source,
                "fetched_at": func.current_timestamp(),
            },
        )
        await session.execute(batch_insert)

    # Single commit for all upserts
    await session.commit()

    # Manual rates change valuations exactly like a provider sync — drop the cached
    # portfolio layers so the next report recomputes (same invalidation as sync_pairs_bulk).
    clear_cache("portfolio_layer2")
    clear_cache("portfolio_blob")
    return results


async def delete_rates_bulk(  # noqa: C901 — flat batch delete: normalize, count, chunked delete
    session,  # AsyncSession
    deletions: list[tuple[str, str, date, date | None]],  # [(from_currency, to_currency, start_date, end_date?), ...]
) -> list[tuple[bool, int, int, str | None]]:  # [(success, existing_count, deleted_count, message), ...]
    """
    Delete multiple FX rates in a single batch operation.

    This function efficiently handles bulk deletions by:
    1. Normalizing all currency pairs (alphabetical ordering)
    2. Fetching existing counts in a single batch query (optimization)
    3. Executing deletions in a single batch (optimization)

    Args:
        session: Database session
        deletions: List of (from_currency, to_currency, start_date, end_date?) tuples
                  - from_currency, to_currency: Will be normalized to alphabetical order
                  - start_date: Start date (inclusive)
                  - end_date: End date (inclusive), optional. If None, only start_date is deleted

    Returns:
        List of (success, existing_count, deleted_count, message) tuples
        - success: Always True (errors handled gracefully)
        - existing_count: Number of rates present before deletion
        - deleted_count: Number of rates actually deleted
        - message: Warning/error message if any (e.g., "no rates found")

    Example:
        deletions = [
            ("USD", "EUR", date(2025, 1, 1), None),  # Single day
            ("GBP", "USD", date(2025, 1, 1), date(2025, 1, 5))  # Range
        ]
        results = await delete_rates_bulk(session, deletions)
    """

    if not deletions:
        return []

    # Normalize all deletions (alphabetical ordering)
    normalized_deletions = []
    for from_cur, to_cur, start_date, end_date in deletions:
        from_cur = from_cur.upper()
        to_cur = to_cur.upper()

        # Normalize to alphabetical order (base < quote)
        if from_cur > to_cur:
            base, quote = to_cur, from_cur
        else:
            base, quote = from_cur, to_cur

        normalized_deletions.append((base, quote, start_date, end_date))

    # OPTIMIZATION: Single batch query to fetch ALL matching rates across all deletions
    # Build OR conditions for all deletions
    all_conditions = []
    for base, quote, start_date, end_date in normalized_deletions:
        if end_date:
            # Date range
            condition = and_(
                FxRate.base == base,
                FxRate.quote == quote,
                FxRate.date >= start_date,
                FxRate.date <= end_date,
            )
        else:
            # Single date
            condition = and_(FxRate.base == base, FxRate.quote == quote, FxRate.date == start_date)
        all_conditions.append(condition)

    # The matching rates (id, base, quote, date), in chunks of OR terms (MF-SEC9a): SQLite refuses an OR of a thousand,
    # and the FX page sends one deletion per run of consecutive days
    rates_by_pair: dict[tuple[str, str], dict[date, int]] = {}
    for chunk in chunks(all_conditions):
        result = await session.execute(sql_select(FxRate.id, FxRate.base, FxRate.quote, FxRate.date).where(or_(*chunk)))
        for r in result.all():
            rates_by_pair.setdefault((r.base, r.quote), {})[r.date] = r.id

    # Count existing rates per deletion request, among its own pair's rates only
    existing_counts = {}
    ids_to_delete = set()

    for idx, (base, quote, start_date, end_date) in enumerate(normalized_deletions):
        last = end_date or start_date
        matched = [r_id for r_date, r_id in rates_by_pair.get((base, quote), {}).items() if start_date <= r_date <= last]
        ids_to_delete.update(matched)
        existing_counts[idx] = len(matched)

    # CHUNKED DELETE: Remove all matched IDs in batches to avoid SQLite limits
    # SQLite has SQLITE_MAX_VARIABLE_NUMBER = 999 by default
    # We use chunks of 500 to be safe and improve performance with large datasets
    deleted_count_total = 0
    if ids_to_delete:
        ids_list = list(ids_to_delete)
        batches = 0
        # Process in chunks within same transaction
        for chunk in chunks(ids_list):
            delete_result = await session.execute(sql_delete(FxRate).where(FxRate.id.in_(chunk)))
            deleted_count_total += delete_result.rowcount
            batches += 1

        logger.info(f"Deleted {deleted_count_total} rate(s) in {batches} batch(es)")

    # Build results per deletion request
    results = []
    for idx, (base, quote, start_date, end_date) in enumerate(normalized_deletions):
        existing_count = existing_counts[idx]
        deleted_count = existing_count  # All existing were deleted

        # Prepare result message
        message = None
        if deleted_count == 0:
            if end_date:
                message = f"No rates found for {base}/{quote} from {start_date} to {end_date}"
            else:
                message = f"No rates found for {base}/{quote} on {start_date}"

        results.append((True, existing_count, deleted_count, message))

    # Single commit for all deletions
    await session.commit()

    if deleted_count_total > 0:
        clear_cache("portfolio_layer2")
        clear_cache("portfolio_blob")

    return results
