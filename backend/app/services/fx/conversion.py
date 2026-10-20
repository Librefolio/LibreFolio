"""
FX conversion: the rate of a chained route (``compute_chain_rate``), the bulk conversion of amounts with
backward-fill (``convert_bulk``), and one unit's rate as steps over the days asked (``unit_rate_steps``, P3).
"""

from bisect import bisect_right
from collections import namedtuple
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, or_
from sqlalchemy import select as sql_select

from backend.app.db.models import FxRate
from backend.app.db.precision import storable_fx_rate, usable_fx_rate_bounds
from backend.app.logging_config import get_logger
from backend.app.schemas.common import Currency
from backend.app.services.financial_math.fx_rates import oriented_rate
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
        # The stored rate read from fc to tc: as it is in alphabetical order, inverted otherwise
        composite *= oriented_rate(rate, fc, tc)
    return composite


# ============================================================================
# CURRENCY CONVERSION FUNCTIONS
# ============================================================================


# Lightweight (date, rate) record used by convert_bulk's lookup.
_RateRow = namedtuple("_RateRow", ["date", "rate"])

#: One unit of a currency: what ``unit_rate_steps`` converts, as the portfolio engine and the native cash ask
#: ``convert_bulk`` for it (P3).
_ONE = Decimal("1")


def _converted(amount: Decimal, rate: Decimal, direct: bool) -> Decimal:
    """``amount`` at a stored rate: multiplied when it is in the pair's base (``direct``), divided otherwise. The one
    arithmetic of ``convert_bulk`` and ``unit_rate_steps`` (P3, MF n1), so that a step is ``convert_bulk``'s amount to the
    digit and the exponent."""
    return amount * rate if direct else amount / rate


async def _usable_rates(session, spans: Mapping[tuple[str, str], tuple[date, date]]) -> dict[tuple[str, str], tuple[list[date], list[Decimal]]]:
    """The rows of each stored pair ``(base, quote)`` that its span ``(first, last)`` can use, as ascending dates and their
    rates: from the backward-fill anchor — the last usable rate on or before ``first``, however old — up to ``last``.

    The one read of ``convert_bulk`` and ``unit_rate_steps`` (P3, MF n2):
    - only usable rates (X-R38), in the anchor as in the window: a legacy unusable row is skipped like a date without one;
    - only the window the dates can use: without the lower bound every call loaded the pair's whole history, and
      per-day portfolio conversions loaded millions of rows;
    - at most ``FX_PAIRS_PER_QUERY`` pairs per query (R13-SEC9-2): SQLite refuses an OR of about a thousand terms
      («Expression tree is too large», a 500);
    - plain columns, no ORM object per row.
    """
    if not spans:
        return {}
    smallest_rate, first_refused_rate = usable_fx_rate_bounds()
    usable = and_(FxRate.rate >= smallest_rate, FxRate.rate < first_refused_rate)
    conditions = []
    for (base, quote), (first, last) in spans.items():
        anchor = sql_select(func.max(FxRate.date)).where(FxRate.base == base, FxRate.quote == quote, FxRate.date <= first, usable).scalar_subquery()
        conditions.append(and_(FxRate.base == base, FxRate.quote == quote, FxRate.date <= last, FxRate.date >= func.coalesce(anchor, first), usable))
    rates: dict[tuple[str, str], tuple[list[date], list[Decimal]]] = {}
    for start in range(0, len(conditions), FX_PAIRS_PER_QUERY):
        stmt = sql_select(FxRate.base, FxRate.quote, FxRate.date, FxRate.rate).where(or_(*conditions[start : start + FX_PAIRS_PER_QUERY])).order_by(FxRate.base, FxRate.quote, FxRate.date)
        for rate_base, rate_quote, rate_date, rate_value in (await session.execute(stmt)).all():
            dates, values = rates.setdefault((rate_base, rate_quote), ([], []))
            dates.append(rate_date)
            values.append(rate_value)
    return rates


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

    # One read for every pair, from each pair's backward-fill anchor to its latest date, usable rates only (X-R38)
    rates_lookup = await _usable_rates(session, {pair: (info["min_date"], info["max_date"]) for pair, info in pairs_needed.items()})

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
            converted_amount = _converted(meta["amount"], rate_record.rate, meta["direct"])

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


# ============================================================================
# UNIT RATES AS STEPS (P3)
# ============================================================================


@dataclass(frozen=True, slots=True)
class UnitRateSteps:
    """What one unit of ``source`` is worth in ``destination``, as steps (P3): from ``days[i]`` on, ``values[i]``, read
    from the stored row of ``rate_days[i]``.

    Built by ``unit_rate_steps`` on the windows asked: on every day of them ``at`` is ``convert_bulk``'s amount for one
    unit, to the digit and the exponent, and ``rate_day_at`` its rate date; both None before the pair's first usable
    rate. A day outside the windows reads the last step on or before it: which days a value is asked for is the
    caller's to keep.
    """

    source: str
    destination: str
    days: tuple[date, ...]
    values: tuple[Decimal, ...]
    rate_days: tuple[date, ...]

    def _step(self, day: date) -> int:
        return bisect_right(self.days, day) - 1

    def at(self, day: date) -> Decimal | None:
        """One unit of ``source`` in ``destination`` on ``day``; None before the first step."""
        index = self._step(day)
        return self.values[index] if index >= 0 else None

    def rate_day_at(self, day: date) -> date | None:
        """The date of the stored row ``at(day)`` comes from; None before the first step."""
        index = self._step(day)
        return self.rate_days[index] if index >= 0 else None


async def unit_rate_steps(session, requests: Mapping[tuple[str, str], Sequence[tuple[date, date]]]) -> dict[tuple[str, str], UnitRateSteps]:
    """One unit of each ``source`` in its ``destination``, as steps on the windows asked (P3): the portfolio engine and the
    native cash need a rate for every day of long ranges, and a rate changes only on the days a row is stored.

    ``requests`` maps ``(source, destination)``, two currency codes as stored, to its windows ``(first_day, last_day)``,
    both days included; the windows of a pair may touch, overlap or lie apart. The steps of a pair are:
    - the first day of each window, with the rate of the backward-fill anchor, the last usable row on or before it (no
      step when the pair has no usable row by then);
    - every day inside a window with a usable row of the pair: two rows with the same rate are two steps.
    So on every day of the windows ``at(day)`` and ``rate_day_at(day)`` are what ``convert_bulk`` gives for
    ``Currency(code=source, amount=Decimal("1"))`` on that day: the same rows, filter and chunks (``_usable_rates``) and
    the same arithmetic (``_converted``). Rows between two windows are no steps.

    Every pair asked has its entry, empty when it has no usable rate in its windows. Raises ``ValueError`` for a pair of
    one currency (``convert_bulk`` answers it with no rate at all, on the day itself, which a step cannot say) and for a
    window whose last day comes before its first.
    """
    planned: list[tuple[tuple[str, str], tuple[str, str], bool, list[tuple[date, date]]]] = []
    spans: dict[tuple[str, str], tuple[date, date]] = {}
    for (source, destination), asked in requests.items():
        if source == destination:
            raise ValueError(f"unit_rate_steps: {source}/{destination} is one currency, not a pair")
        windows = sorted(asked)
        for first, last in windows:
            if last < first:
                raise ValueError(f"unit_rate_steps: the window {first} – {last} of {source}/{destination} ends before it starts")
        stored = (min(source, destination), max(source, destination))
        if windows:
            first, last = windows[0][0], max(window_last for _first, window_last in windows)
            if stored in spans:
                first, last = min(first, spans[stored][0]), max(last, spans[stored][1])
            spans[stored] = (first, last)
        planned.append(((source, destination), stored, source < destination, windows))

    rates = await _usable_rates(session, spans)
    steps: dict[tuple[str, str], UnitRateSteps] = {}
    for (source, destination), stored, direct, windows in planned:
        dates, values = rates.get(stored, ([], []))
        rows_by_day = _step_rows(dates, windows)
        days = tuple(sorted(rows_by_day))
        steps[(source, destination)] = UnitRateSteps(
            source=source,
            destination=destination,
            days=days,
            values=tuple(_converted(_ONE, values[rows_by_day[day]], direct) for day in days),
            rate_days=tuple(dates[rows_by_day[day]] for day in days),
        )
    return steps


def _step_rows(dates: list[date], windows: list[tuple[date, date]]) -> dict[date, int]:
    """By step day, the index in ``dates`` (a pair's ascending usable rows) of the row the step reads: each window's first
    day with its anchor, the last row on or before it, when there is one; and each row inside a window, by its own date."""
    rows_by_day: dict[date, int] = {}
    for first, last in windows:
        anchor = bisect_right(dates, first) - 1
        if anchor >= 0:
            rows_by_day[first] = anchor
        for index in range(anchor + 1, bisect_right(dates, last)):
            rows_by_day[dates[index]] = index
    return rows_by_day
