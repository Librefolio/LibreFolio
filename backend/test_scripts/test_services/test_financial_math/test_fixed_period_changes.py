"""
MF-P2 (workstream MF, lot P2 — D-MF6 b): the fixed-period changes of the Assets and FX tables get a house function.

Module under test: ``backend/app/services/financial_math/returns.py``:

* ``FIXED_PERIODS`` — the table's columns, ``(key, calendar days)`` in display order, 1D included;
* ``fixed_period_dates(as_of, periods=FIXED_PERIODS)`` — the days a table values: ``as_of`` first, then
  ``as_of − days`` for each period, in calendar days;
* ``fixed_period_changes(values, as_of, periods=FIXED_PERIODS)`` → ``tuple[FixedPeriodChange(key, days, change_ratio,
  inverse_change_ratio), ...]``. The anchor is ``values[as_of]``, each reference is ``values[as_of − days]``;
  ``change_ratio = anchor / reference − 1`` and ``inverse_change_ratio = reference / anchor − 1`` (the inverted FX
  quote), both Decimal fractions, never ×100; a missing or None value, a reference ≤ 0 or a negative anchor makes that
  change and its inverse None; an anchor of exactly 0 over a positive reference is −1 without an inverse (see below).
  The carry-forward is the caller's job: the value on a day is the last stored price on or before it (assets, grouped
  SQL) or a rate converted at it (FX, ``convert_bulk``).

The parity oracle is what the frontend computes today, ported below line by line in Decimal:

* Assets: ``frontend/src/lib/utils/assetPriceDerived.ts::computePeriodDelta`` → ``_assets_page_period_delta``;
* FX: the copy in ``frontend/src/routes/(app)/fx/+page.svelte:194-210`` with ``displayFxDelta`` /
  ``displayFxRate`` (``frontend/src/lib/stores/fxStoreRegistry.ts:55-70``) → ``_fx_page_period_delta``.

Both run on the dense series ``POST /assets/prices/query`` returns: one point per calendar day from the range start to
``as_of``, each missing day carrying the last stored value, seeded with the last stored value before the start
(``PriceQueryOperations._build_backward_filled_series``, ported as ``_backward_filled_series``). Each parity test builds
that series from sparse stored points, hands the house function the series' values on ``fixed_period_dates(as_of)``,
and asserts ``change_ratio × 100`` equal, exactly as a Decimal, to what each page computes on the same series.

The stored values come from ``PRICES`` / ``RATES``: distinct numbers 2ⁿ × 10ᵏ. Every quotient of two of them and every
reciprocal terminates within the Decimal context, so the page's ``(last − ref) / ref × 100`` and the house's
``(anchor / ref − 1) × 100`` are the same Decimal: the comparison reads only *which* values each side took. With
arbitrary values the two forms round differently in the last digits — not a difference of rule, and
``test_high_precision_pair_is_exact_decimal`` pins the house's own arithmetic instead. Distinct values also mean a
reference read on the wrong day changes the result.

Red by absence on HEAD (1c37ad0f0): ``returns.py`` there has none of the new names, so the import below fails and the
file errors at collection with ImportError.

X-R59 (rule 10, developer decision N80) adds ``TestRangeChange`` at the end: the whole-range Δ of the Assets cards and
the FX Δ Abs / Δ % — today ``computeDerivedPriceState`` (``assetPriceDerived.ts``) and ``displayFxDelta``
(``fxStoreRegistry.ts``), floats in the browser — get the house function
``range_change(reference, anchor) -> RangeChange(change_abs, change_ratio, inverse_change_abs, inverse_change_ratio)``.
It is looked up on the module when a test calls it, so the rest of this file still collects and runs on HEAD a275ec8af,
where those tests are red with AttributeError.

X's review, point 2 (decision on N80): a price written down to nothing — a defaulted loan, a delisted share — is −100 %,
not «no change». ``range_change(reference, anchor)`` with an anchor of exactly 0 over a positive reference gives
``change_abs = −reference``, ``change_ratio = −1`` and both inverse fields None (the inverted quote has no value); a
reference ≤ 0 and a negative anchor still give all four None. ``fixed_period_changes`` delegates to ``range_change``, so
every period with a positive reference gets −1 and an inverse None. Pinned by ``TestAnchorOfZero``; ``zero-anchor`` left
``UNUSABLE_PAIRS``, and ``test_negative_anchor_or_non_positive_reference_gives_no_change`` (formerly
``test_non_positive_value_gives_no_change_either_way``) keeps only what is still refused. Red on HEAD f252acb4a: None where
−1 is expected (every test of ``TestAnchorOfZero``).

Pure: no database, no server, no network.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.services.financial_math import returns as returns_module
from backend.app.services.financial_math.returns import (
    FIXED_PERIODS,
    FixedPeriodChange,
    fixed_period_changes,
    fixed_period_dates,
    price_return,
)

D = Decimal

FRIDAY = date(2025, 3, 14)
SATURDAY = date(2025, 3, 15)
SUNDAY = date(2025, 3, 16)
MONDAY = date(2025, 3, 17)
GOOD_FRIDAY = date(2025, 4, 18)
EASTER_MONDAY = date(2025, 4, 21)
TUESDAY = date(2026, 6, 30)

LONGEST_PERIOD_DAYS = max(days for _key, days in FIXED_PERIODS)


def _smooth_pool(low: Decimal, high: Decimal, exponents: range) -> tuple[Decimal, ...]:
    """One value 2ⁿ × 10ᵏ in [low, 10 × low) per exponent n: distinct, and every quotient or reciprocal terminates."""
    assert high == low * 10, "one value per exponent needs a one-decade band"
    pool = []
    for exponent in exponents:
        value = Decimal(2) ** exponent
        while value < low:
            value = value.scaleb(1)
        while value >= high:
            value = value.scaleb(-1)
        pool.append(value)
    assert len(set(pool)) == len(pool)
    return tuple(pool)


PRICES = _smooth_pool(D("50"), D("500"), range(-15, 16))
RATES = _smooth_pool(D("0.5"), D("5"), range(-10, 11))


def _days_before(day: date, days: int) -> date:
    return day - timedelta(days=days)


def _weekdays(first: date, last: date, closed: Iterable[date] = ()) -> list[date]:
    """Monday to Friday from ``first`` to ``last``, without the ``closed`` days (holidays)."""
    skipped = set(closed)
    days = []
    day = first
    while day <= last:
        if day.weekday() < 5 and day not in skipped:
            days.append(day)
        day += timedelta(days=1)
    return days


def _priced(days: Iterable[date], pool: Sequence[Decimal] = PRICES) -> dict[date, Decimal]:
    """The stored points of a hand-made series: each day its own value from ``pool``, no two days alike."""
    ordered = sorted(set(days))
    assert len(ordered) <= len(pool), "the pool has fewer distinct values than the series has days"
    return dict(zip(ordered, pool, strict=False))


def _backward_filled_series(stored: Mapping[date, Decimal], start: date, end: date) -> dict[date, Decimal]:
    """Port of ``PriceQueryOperations._build_backward_filled_series`` (``backend/app/services/assets/price_query.py:140``)
    with the seed ``query_prices`` gives it (``:320-397``).

    The price map holds the stored values dated in [start, end]; the seed is the last stored value before ``start``.
    Every day from ``start`` to ``end`` gets the value stored on it, else the last one known; the days before the first
    known value are skipped. Returned in date order, as the endpoint returns it.
    """
    in_range = {day: value for day, value in stored.items() if start <= day <= end}
    before_start = [day for day in stored if day < start]
    last_known = stored[max(before_start)] if before_start else None
    series: dict[date, Decimal] = {}
    day = start
    while day <= end:
        if day in in_range:
            last_known = in_range[day]
            series[day] = last_known
        elif last_known is not None:
            series[day] = last_known
        day += timedelta(days=1)
    return series


def _reference_point(chart_data: Sequence[tuple[str, Decimal]], period_days: int) -> tuple[str, Decimal] | None:
    """The pages' reference: the last point dated on or before (last point's date − N calendar days), ISO strings
    compared as strings, as in the TS.

    The TS builds the target with ``new Date(iso)`` (UTC midnight), ``setDate(getDate() − N)`` (local time) and
    ``toISOString()``: calendar-day arithmetic in a UTC browser, which this port reproduces. In a browser on a
    daylight-saving zone the TS target comes out one day early whenever the last date is in standard time and the
    target in summer time (Europe/Rome: 2026-01-15 − 182 → 2025-07-16 instead of 2025-07-17); the house function has
    no time zone.
    """
    last_date, _last_value = chart_data[-1]
    target = (date.fromisoformat(last_date) - timedelta(days=period_days)).isoformat()
    for point in reversed(chart_data):
        if point[0] <= target:
            return point
    return None


def _assets_page_period_delta(chart_data: Sequence[tuple[str, Decimal]], period_days: int) -> Decimal | None:
    """Port of ``computePeriodDelta`` (``frontend/src/lib/utils/assetPriceDerived.ts:144-164``), in Decimal.

    The last point is the anchor; the reference is ``_reference_point``; ``(last − ref) / ref × 100``, null without a
    reference or when either value is exactly 0 (``=== 0``: a negative value is not nulled here).
    """
    if not chart_data:
        return None
    last_value = chart_data[-1][1]
    if last_value == 0:
        return None
    reference = _reference_point(chart_data, period_days)
    if reference is None or reference[1] == 0:
        return None
    return (last_value - reference[1]) / reference[1] * 100


def _display_fx_rate(rate: Decimal | None, inverted: bool) -> Decimal | None:
    """Port of ``displayFxRate`` (``frontend/src/lib/stores/fxStoreRegistry.ts:55-59``)."""
    if rate is None or rate <= 0:
        return None
    return 1 / rate if inverted else rate


def _fx_page_period_delta(data: Sequence[tuple[str, Decimal]], period_days: int, inverted: bool) -> Decimal | None:
    """Port of the FX page's ``computePeriodDelta`` (``frontend/src/routes/(app)/fx/+page.svelte:194-210``) with
    ``displayFxDelta`` (``fxStoreRegistry.ts:65-70``), in Decimal: the displayed rates (flipped when ``inverted``)
    of the reference and of the last point, ``(last − first) / first × 100``; null with fewer than two points, without
    a reference, or with a rate ≤ 0. Inverted, ``(1/last − 1/ref) / (1/ref)`` is ``ref / last − 1``.
    """
    if len(data) < 2:
        return None
    reference = _reference_point(data, period_days)
    if reference is None:
        return None
    first = _display_fx_rate(reference[1], inverted)
    last = _display_fx_rate(data[-1][1], inverted)
    if first is None or last is None:
        return None
    return (last - first) / first * 100


def _as_percent(ratio: Decimal | None) -> Decimal | None:
    return None if ratio is None else ratio * 100


def _assert_parity(stored: Mapping[date, Decimal], as_of: date, range_start: date | None = None) -> dict[str, FixedPeriodChange]:
    """The house function on the dense series' values at ``fixed_period_dates(as_of)`` against both pages' ports on
    the whole dense series, for every period: exact Decimal equality, None for null.

    ``range_start`` is the start of the range the page loaded (default: the longest period before ``as_of``, so every
    column is shown). Returns the changes by key, for the caller's own assertions.
    """
    start = range_start or _days_before(as_of, LONGEST_PERIOD_DAYS)
    dense = _backward_filled_series(stored, start, as_of)
    values = {day: dense[day] for day in fixed_period_dates(as_of) if day in dense}
    chart_data = [(day.isoformat(), value) for day, value in dense.items()]

    changes = fixed_period_changes(values, as_of)

    assert [(change.key, change.days) for change in changes] == list(FIXED_PERIODS)
    for change in changes:
        assert (change.change_ratio is None) == (change.inverse_change_ratio is None), change
        if change.change_ratio is not None:
            assert isinstance(change.change_ratio, Decimal) and isinstance(change.inverse_change_ratio, Decimal), change
        house = _as_percent(change.change_ratio)
        house_inverted = _as_percent(change.inverse_change_ratio)
        assets_page = _assets_page_period_delta(chart_data, change.days)
        fx_page = _fx_page_period_delta(chart_data, change.days, inverted=False)
        fx_page_inverted = _fx_page_period_delta(chart_data, change.days, inverted=True)
        assert house == assets_page, f"{change.key} on {as_of}: house {house} vs Assets page {assets_page}"
        assert house == fx_page, f"{change.key} on {as_of}: house {house} vs FX page {fx_page}"
        assert house_inverted == fx_page_inverted, f"{change.key} on {as_of}: house inverse {house_inverted} vs FX page inverted {fx_page_inverted}"
    return {change.key: change for change in changes}


def _valued(changes: Mapping[str, FixedPeriodChange]) -> set[str]:
    return {key for key, change in changes.items() if change.change_ratio is not None}


# --- Parity with the frontend rule ----------------------------------------------------------------------------------


def test_parity_weekdays_only_as_of_a_monday() -> None:
    """Weekends never stored: Sunday carries Friday, so the 1D of a Monday reads Friday's price."""
    stored = _priced(_weekdays(date(2025, 2, 10), MONDAY))

    changes = _assert_parity(stored, MONDAY)

    assert _valued(changes) == {"1D", "1W", "1M"}, "3M and longer start before the series"
    assert changes["1D"].change_ratio == stored[MONDAY] / stored[FRIDAY] - 1
    assert changes["1W"].change_ratio == stored[MONDAY] / stored[date(2025, 3, 10)] - 1
    # 1M: the target is Saturday 15 February, valued with Friday 14's price.
    assert changes["1M"].change_ratio == stored[MONDAY] / stored[date(2025, 2, 14)] - 1


def test_parity_stale_anchor_counts_from_as_of() -> None:
    """The last stored price is 10 days before ``as_of``: the anchor carries it, the targets still count from
    ``as_of``. Counting from the stored date would read 10 days earlier, the ``target − 12`` point below."""
    last_stored = _days_before(TUESDAY, 10)
    days = [last_stored]
    for _key, period_days in FIXED_PERIODS:
        target = _days_before(TUESDAY, period_days)
        if target < last_stored:
            days += [_days_before(target, 12), _days_before(target, 1), target + timedelta(days=1)]
    stored = _priced(days)

    changes = _assert_parity(stored, TUESDAY)

    assert _valued(changes) == {key for key, _days in FIXED_PERIODS}
    for key in ("1D", "1W"):
        assert changes[key].change_ratio == 0, f"{key}: both ends carry the same stale price"
    for key, period_days in FIXED_PERIODS[2:]:
        target = _days_before(TUESDAY, period_days)
        assert changes[key].change_ratio == stored[last_stored] / stored[_days_before(target, 1)] - 1, key


def test_parity_reference_exactly_on_the_target_date() -> None:
    """A price stored on the target itself is the reference — not the day before, not the day after."""
    days = {TUESDAY}
    for _key, period_days in FIXED_PERIODS:
        target = _days_before(TUESDAY, period_days)
        days |= {_days_before(target, 1), target, target + timedelta(days=1)}
    stored = _priced(days)

    changes = _assert_parity(stored, TUESDAY)

    for key, period_days in FIXED_PERIODS:
        assert changes[key].change_ratio == stored[TUESDAY] / stored[_days_before(TUESDAY, period_days)] - 1, key


def test_parity_series_younger_than_a_period() -> None:
    """A period that starts before the first stored price has no reference: None, as the page's null."""
    # The first price is stored on the 3M target itself: 3M is valued, 6M is not.
    born_on_3m_target = _priced(_days_before(TUESDAY, 91) + timedelta(days=7 * week) for week in range(14))
    changes = _assert_parity(born_on_3m_target, TUESDAY)
    assert _valued(changes) == {"1D", "1W", "1M", "3M"}
    assert changes["3M"].change_ratio == born_on_3m_target[TUESDAY] / born_on_3m_target[_days_before(TUESDAY, 91)] - 1

    # The first price is stored the day after the 6M target: one day too young.
    born_after_6m_target = _priced(_days_before(TUESDAY, 181) + timedelta(days=7 * week) for week in range(26))
    changes = _assert_parity(born_after_6m_target, TUESDAY)
    assert _valued(changes) == {"1D", "1W", "1M", "3M"}
    assert changes["6M"].change_ratio is None and changes["6M"].inverse_change_ratio is None


def test_parity_with_a_seed_before_the_loaded_range() -> None:
    """A page that loaded 400 days: the series starts with the last price stored before the range, carried.

    The 1Y target falls in that carried stretch. 2Y and longer lie before the range: the page hides those columns
    (``visiblePeriods``), and the series has no value there, so both sides give None.
    """
    range_start = _days_before(TUESDAY, 400)
    stored = _priced(_days_before(TUESDAY, days_back) for days_back in (1000, 500, 200, 20, 3))

    changes = _assert_parity(stored, TUESDAY, range_start=range_start)

    assert _valued(changes) == {"1D", "1W", "1M", "3M", "6M", "1Y"}
    assert changes["1Y"].change_ratio == stored[_days_before(TUESDAY, 3)] / stored[_days_before(TUESDAY, 500)] - 1
    assert changes["6M"].change_ratio == stored[_days_before(TUESDAY, 3)] / stored[_days_before(TUESDAY, 200)] - 1
    assert changes["1W"].change_ratio == stored[_days_before(TUESDAY, 3)] / stored[_days_before(TUESDAY, 20)] - 1
    assert changes["1D"].change_ratio == 0


def test_parity_nothing_stored_up_to_as_of() -> None:
    """Prices stored only after ``as_of``: an empty series, no anchor, every change None on both sides."""
    stored = _priced(TUESDAY + timedelta(days=days_after) for days_after in (1, 2, 5))

    changes = _assert_parity(stored, TUESDAY)

    assert _valued(changes) == set()


def test_parity_fx_rates_both_orientations() -> None:
    """FX rates on weekdays plus one rate stored the day before each long target: the direct change is the FX
    page's delta, the inverse its delta with the pair inverted, ``ref / last − 1``."""
    as_of = date(2025, 3, 19)
    days = _weekdays(date(2025, 3, 5), as_of)
    days += [_days_before(as_of, period_days + 1) for _key, period_days in FIXED_PERIODS if period_days >= 30]
    stored = _priced(days, pool=RATES)

    changes = _assert_parity(stored, as_of)

    def rate_on(day: date) -> Decimal:
        return stored[max(stored_day for stored_day in stored if stored_day <= day)]

    assert _valued(changes) == {key for key, _days in FIXED_PERIODS}
    for key, period_days in FIXED_PERIODS:
        reference = rate_on(_days_before(as_of, period_days))
        assert changes[key].change_ratio == rate_on(as_of) / reference - 1, key
        assert changes[key].inverse_change_ratio == reference / rate_on(as_of) - 1, key


# --- The case X asked to pin: a 1D of exactly 0 over a closed day --------------------------------------------------


def test_one_day_over_a_weekend_is_exactly_zero() -> None:
    """Friday's price carried to Saturday and Sunday: on either, the 1D is exactly 0 both ways — not None, not −0."""
    stored = _priced(_weekdays(date(2025, 2, 10), FRIDAY))

    for as_of in (SATURDAY, SUNDAY):
        changes = _assert_parity(stored, as_of)

        one_day = changes["1D"]
        assert one_day.change_ratio == 0 and one_day.inverse_change_ratio == 0, as_of
        assert not one_day.change_ratio.is_signed() and not one_day.inverse_change_ratio.is_signed(), as_of
        # The week is still a real change: the 1W reads Friday 7 March.
        assert changes["1W"].change_ratio == stored[FRIDAY] / stored[date(2025, 3, 7)] - 1 != 0, as_of

    # The same as the caller hands it: Friday's price on Saturday and Sunday.
    friday_price = stored[FRIDAY]
    (one_day,) = fixed_period_changes({SUNDAY: friday_price, SATURDAY: friday_price}, SUNDAY, (("1D", 1),))
    assert one_day == FixedPeriodChange(key="1D", days=1, change_ratio=D("0"), inverse_change_ratio=D("0"))


def test_one_day_on_a_holiday_is_exactly_zero() -> None:
    """Easter 2025, market closed on Good Friday and Easter Monday: Thursday's price is carried to both, so the 1D of
    each is exactly 0 both ways, while the 1W is a real change."""
    stored = _priced(_weekdays(date(2025, 3, 24), EASTER_MONDAY, closed=(GOOD_FRIDAY, EASTER_MONDAY)))

    for as_of in (GOOD_FRIDAY, EASTER_MONDAY):
        changes = _assert_parity(stored, as_of)

        one_day = changes["1D"]
        assert one_day.change_ratio == 0 and one_day.inverse_change_ratio == 0, as_of
        assert not one_day.change_ratio.is_signed() and not one_day.inverse_change_ratio.is_signed(), as_of
        assert changes["1W"].change_ratio == stored[date(2025, 4, 17)] / stored[_days_before(as_of, 7)] - 1 != 0, as_of


# --- Inverse orientation --------------------------------------------------------------------------------------------


def test_direct_and_inverse_changes_compose_to_one() -> None:
    """On rates whose quotients do not terminate: the inverse is exactly ``reference / anchor − 1`` (not the direct
    change with its sign flipped), and ``(1 + change) × (1 + inverse)`` is 1 within the context's precision."""
    as_of = TUESDAY
    rates = (D("1.0873"), D("1.0912"), D("1.10215"), D("0.98765"), D("1.23456789"), D("0.9999"), D("1.3333"), D("0.7071"), D("1.4142"), D("1.0001"))
    values = dict(zip(fixed_period_dates(as_of), rates, strict=True))

    changes = fixed_period_changes(values, as_of)

    for change in changes:
        reference = values[_days_before(as_of, change.days)]
        assert change.change_ratio == values[as_of] / reference - 1, change.key
        assert change.inverse_change_ratio == reference / values[as_of] - 1, change.key
        assert change.inverse_change_ratio != -change.change_ratio, change.key
        assert abs((1 + change.change_ratio) * (1 + change.inverse_change_ratio) - 1) <= D("1e-25"), change.key


# --- Rules ----------------------------------------------------------------------------------------------------------


def test_fixed_periods_and_their_dates() -> None:
    """The columns in display order, 1D first; their dates are ``as_of`` first, then ``as_of − days`` in calendar
    days — across a leap day, 1Y is 365 days, not the same date a year before."""
    assert FIXED_PERIODS == (("1D", 1), ("1W", 7), ("1M", 30), ("3M", 91), ("6M", 182), ("1Y", 365), ("2Y", 730), ("3Y", 1095), ("5Y", 1825))

    as_of = date(2024, 3, 1)
    expected = (
        as_of,
        date(2024, 2, 29),
        date(2024, 2, 23),
        date(2024, 1, 31),
        date(2023, 12, 1),
        date(2023, 9, 1),
        date(2023, 3, 2),
        date(2022, 3, 2),
        date(2021, 3, 2),
        date(2019, 3, 3),
    )
    assert fixed_period_dates(as_of) == expected
    assert fixed_period_dates(as_of, FIXED_PERIODS) == expected


def test_fixed_period_dates_honour_custom_periods() -> None:
    periods = (("10D", 10), ("2D", 2), ("1D", 1))

    assert fixed_period_dates(TUESDAY, periods) == (TUESDAY, _days_before(TUESDAY, 10), _days_before(TUESDAY, 2), _days_before(TUESDAY, 1))
    assert fixed_period_dates(TUESDAY, ()) == (TUESDAY,)


def test_changes_default_to_fixed_periods() -> None:
    values = _priced(fixed_period_dates(TUESDAY))

    changes = fixed_period_changes(values, TUESDAY)

    assert [(change.key, change.days) for change in changes] == list(FIXED_PERIODS)
    assert changes[0].key == "1D" and changes[0].days == 1
    assert changes == fixed_period_changes(values, TUESDAY, FIXED_PERIODS)
    for change in changes:
        assert change.change_ratio == values[TUESDAY] / values[_days_before(TUESDAY, change.days)] - 1, change.key


def test_changes_honour_custom_periods() -> None:
    """Any (key, days) list, in its own order, with days the default list does not have."""
    periods = (("10D", 10), ("2D", 2), ("1D", 1))
    values = _priced(fixed_period_dates(TUESDAY, periods))

    changes = fixed_period_changes(values, TUESDAY, periods)

    assert [(change.key, change.days) for change in changes] == list(periods)
    for change in changes:
        assert change.change_ratio == values[TUESDAY] / values[_days_before(TUESDAY, change.days)] - 1, change.key
    assert fixed_period_changes(values, TUESDAY, ()) == ()


def test_changes_are_fractions_not_percentages() -> None:
    (change,) = fixed_period_changes({TUESDAY: D("125"), _days_before(TUESDAY, 1): D("100")}, TUESDAY, (("1D", 1),))

    assert change.change_ratio == D("0.25")
    assert change.inverse_change_ratio == D("-0.2")


def test_missing_anchor_gives_no_change() -> None:
    """No value on ``as_of`` — absent or None — leaves every period listed, every change None both ways."""
    references = dict(zip(fixed_period_dates(TUESDAY)[1:], PRICES, strict=False))

    for values in ({}, references, {**references, TUESDAY: None}):
        changes = fixed_period_changes(values, TUESDAY)

        assert [(change.key, change.days) for change in changes] == list(FIXED_PERIODS)
        assert all(change.change_ratio is None and change.inverse_change_ratio is None for change in changes)


def test_missing_reference_gives_none_for_that_period_only() -> None:
    """A reference day absent or None: that period is None both ways, the others are valued."""
    values: dict[date, Decimal | None] = dict(_priced(fixed_period_dates(TUESDAY)))
    del values[_days_before(TUESDAY, 7)]
    values[_days_before(TUESDAY, 91)] = None

    changes = {change.key: change for change in fixed_period_changes(values, TUESDAY)}

    assert _valued(changes) == {key for key, _days in FIXED_PERIODS} - {"1W", "3M"}
    for key in ("1W", "3M"):
        assert changes[key].change_ratio is None and changes[key].inverse_change_ratio is None, key


def test_only_the_values_on_the_fixed_dates_count() -> None:
    """The function does not carry anything forward: a value on any other day — the day before a missing target, a day
    after ``as_of`` — never changes a result nor fills a missing day."""
    fixed_days = set(fixed_period_dates(TUESDAY))
    values: dict[date, Decimal] = dict(_priced(fixed_days))
    del values[_days_before(TUESDAY, 30)]
    baseline = fixed_period_changes(values, TUESDAY)

    noise_day = _days_before(TUESDAY, LONGEST_PERIOD_DAYS + 5)
    with_noise = dict(values)
    while noise_day <= TUESDAY + timedelta(days=5):
        if noise_day not in fixed_days:
            with_noise[noise_day] = D("7.77")
        noise_day += timedelta(days=1)

    assert fixed_period_changes(with_noise, TUESDAY) == baseline
    one_month = next(change for change in baseline if change.key == "1M")
    assert one_month.change_ratio is None and one_month.inverse_change_ratio is None


def test_negative_anchor_or_non_positive_reference_gives_no_change() -> None:
    """A negative anchor nulls every period; a reference ≤ 0 nulls its own. Never a number from such a value.

    This is the FX page's rule (``displayFxRate`` nulls ≤ 0). The Assets page nulls only ``=== 0``: on a negative value
    it shows a number where the house gives None — the parity tests use positive values only. An anchor of exactly 0 is
    no longer refused (N80, X's review point 2): ``TestAnchorOfZero``.
    """
    positive = dict(_priced(fixed_period_dates(TUESDAY)))

    changes = fixed_period_changes({**positive, TUESDAY: D("-12.5")}, TUESDAY)
    assert all(change.change_ratio is None and change.inverse_change_ratio is None for change in changes)

    references = {**positive, _days_before(TUESDAY, 30): D("0"), _days_before(TUESDAY, 365): D("-3")}
    changes = {change.key: change for change in fixed_period_changes(references, TUESDAY)}
    assert _valued(changes) == {key for key, _days in FIXED_PERIODS} - {"1M", "1Y"}
    for key in ("1M", "1Y"):
        assert changes[key].change_ratio is None and changes[key].inverse_change_ratio is None, key


# --- Exact Decimals -------------------------------------------------------------------------------------------------


def test_high_precision_pair_is_exact_decimal() -> None:
    """Two prices with digits to spare: the change is the Decimal quotient, with no float in between."""
    anchor, reference = D("101.3711"), D("99.99993")

    (change,) = fixed_period_changes({TUESDAY: anchor, _days_before(TUESDAY, 1): reference}, TUESDAY, (("1D", 1),))

    assert isinstance(change.change_ratio, Decimal) and isinstance(change.inverse_change_ratio, Decimal)
    assert change.change_ratio == anchor / reference - 1
    assert change.inverse_change_ratio == reference / anchor - 1
    assert change.change_ratio == D("0.013711709598196718737703116")
    assert change.inverse_change_ratio == D("-0.0135262417000506061392250849")
    assert change.change_ratio != Decimal(float(anchor) / float(reference) - 1)


# --- X-R59: the whole-range change (rule 10, decision N80) ----------------------------------------------------------

#: The fields of ``RangeChange``, the brief's contract.
RANGE_CHANGE_FIELDS = {"change_abs", "change_ratio", "inverse_change_abs", "inverse_change_ratio"}

#: Pairs ``(reference, anchor)`` the house refuses to price: a missing value, a reference at or below zero, a negative
#: anchor. An anchor of exactly 0 over a positive reference is priced, −100 % (``ZERO_ANCHOR_REFERENCES``).
UNUSABLE_PAIRS = [
    pytest.param(None, D("100"), id="no-reference"),
    pytest.param(D("100"), None, id="no-anchor"),
    pytest.param(None, None, id="neither"),
    pytest.param(D("0"), D("100"), id="zero-reference"),
    pytest.param(D("0"), D("0"), id="both-zero"),
    pytest.param(D("-5"), D("100"), id="negative-reference"),
    pytest.param(D("100"), D("-5"), id="negative-anchor"),
    pytest.param(D("-5"), D("-4"), id="both-negative"),
    pytest.param(D("-5"), D("0"), id="negative-reference-zero-anchor"),
]

#: Positive references an anchor of 0 is measured against (N80): −1 whatever their size.
ZERO_ANCHOR_REFERENCES = [D("100"), D("3.21"), D("0.000123"), D("99999999.999999999999")]


def _range_change(reference: Decimal | None, anchor: Decimal | None):
    """``returns.range_change(reference, anchor)``, looked up when called: it does not exist on HEAD a275ec8af (an
    AttributeError there), and an import at the top would take the whole file down with it."""
    return returns_module.range_change(reference, anchor)


def _range_change_type() -> type:
    return returns_module.RangeChange


class TestRangeChange:
    """``range_change(reference, anchor)``: the change from the range's first value to its last, in both orientations.

    ``change_abs = anchor − reference``, ``change_ratio = anchor / reference − 1`` (``price_return``),
    ``inverse_change_abs = 1/anchor − 1/reference`` (the pair read the other way round, ``displayFxDelta`` inverted),
    ``inverse_change_ratio = reference / anchor − 1``: Decimal, unrounded, never ×100. Only when both values exist, the
    reference > 0 and the anchor ≥ 0 (an anchor of 0: ``TestAnchorOfZero``); otherwise all four None. RED on HEAD
    a275ec8af: AttributeError, the function does not exist.
    """

    def test_rise(self) -> None:
        result = _range_change(D("100"), D("125"))

        assert result.change_abs == D("25")
        assert result.change_ratio == D("0.25") == price_return(D("100"), D("125"))
        assert result.inverse_change_abs == D("-0.002"), "1/125 − 1/100"
        assert result.inverse_change_ratio == D("-0.2"), "100/125 − 1"

    def test_fall(self) -> None:
        result = _range_change(D("160"), D("125"))

        assert result.change_abs == D("-35")
        assert result.change_ratio == D("-0.21875") == price_return(D("160"), D("125"))
        assert result.inverse_change_abs == D("0.00175"), "1/125 − 1/160: the inverted quote rose"
        assert result.inverse_change_ratio == D("0.28"), "160/125 − 1"

    @pytest.mark.parametrize("value", [D("3.21"), D("100"), D("0.000123")], ids=str)
    def test_equal_values_are_exactly_zero_both_ways(self, value: Decimal) -> None:
        """No move over the range: all four exactly 0 — not None, not −0."""
        result = _range_change(value, value)

        for field in sorted(RANGE_CHANGE_FIELDS):
            change = getattr(result, field)
            assert isinstance(change, Decimal) and change == 0, f"{field}: {change!r}"
            assert not change.is_signed(), f"{field} is −0"

    def test_inverse_fields_are_the_inverted_quote_not_the_sign_flipped(self) -> None:
        """On values whose quotients do not terminate: each field is its own formula; the inverse ratio is not the
        direct one negated, and ``(1 + change) × (1 + inverse)`` is 1 within the context's precision."""
        reference, anchor = D("1.0873"), D("1.0912")

        result = _range_change(reference, anchor)

        assert result.change_abs == anchor - reference == D("0.0039")
        assert result.change_ratio == anchor / reference - 1
        assert result.inverse_change_abs == 1 / anchor - 1 / reference
        assert result.inverse_change_ratio == reference / anchor - 1
        assert result.inverse_change_ratio != -result.change_ratio
        assert result.inverse_change_abs != -result.change_abs
        assert abs((1 + result.change_ratio) * (1 + result.inverse_change_ratio) - 1) <= D("1e-25")

    @pytest.mark.parametrize(("reference", "anchor"), UNUSABLE_PAIRS)
    def test_unusable_values_give_all_none(self, reference: Decimal | None, anchor: Decimal | None) -> None:
        result = _range_change(reference, anchor)

        assert {field: getattr(result, field) for field in RANGE_CHANGE_FIELDS} == dict.fromkeys(RANGE_CHANGE_FIELDS)

    def test_decimal_exactness_no_float_in_between(self) -> None:
        """Reference 3, anchor 3.21: the ratio is exactly 0.07 — a float would give 0.07000000000000006."""
        reference, anchor = D("3"), D("3.21")
        assert Decimal(3.21 / 3 - 1) != D("0.07"), "precondition: the float route is not exact here"

        result = _range_change(reference, anchor)

        assert all(isinstance(getattr(result, field), Decimal) for field in RANGE_CHANGE_FIELDS), result
        assert result.change_abs == D("0.21")
        assert result.change_ratio == D("0.07")
        assert result.inverse_change_ratio == reference / anchor - 1
        assert result.inverse_change_abs == 1 / anchor - 1 / reference
        assert result.inverse_change_ratio != Decimal(3 / 3.21 - 1)

    @pytest.mark.parametrize(
        ("reference", "anchor"),
        [(D("100"), D("125")), (D("160"), D("125")), (D("1.0873"), D("1.0912")), (D("99.99993"), D("101.3711")), (D("3"), D("3")), pytest.param(D("100"), D("0"), id="zero-anchor"), *UNUSABLE_PAIRS],
    )
    def test_ratios_are_the_fixed_periods_ones(self, reference: Decimal | None, anchor: Decimal | None) -> None:
        """One home: the range's ratios are what ``fixed_period_changes`` gives a period with the same two values."""
        (period,) = fixed_period_changes({TUESDAY: anchor, _days_before(TUESDAY, 1): reference}, TUESDAY, (("1D", 1),))

        result = _range_change(reference, anchor)

        assert (result.change_ratio, result.inverse_change_ratio) == (period.change_ratio, period.inverse_change_ratio)

    def test_result_is_a_frozen_dataclass_of_four_fields(self) -> None:
        range_change_type = _range_change_type()
        result = _range_change(D("100"), D("125"))

        assert isinstance(result, range_change_type) and dataclasses.is_dataclass(result)
        assert {field.name for field in dataclasses.fields(range_change_type)} == RANGE_CHANGE_FIELDS
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.change_abs = D("0")


# --- X's review, point 2 (decision on N80): a price written down to nothing -----------------------------------------


class TestAnchorOfZero:
    """An anchor of exactly 0 over a positive reference — a defaulted loan, a delisted share —: −100 %. ``change_abs`` is
    −reference and ``change_ratio`` −1, exact Decimals; the inverse fields are None, the inverted quote having no value.
    ``fixed_period_changes`` gives the same −1 to every period whose reference is positive, the others staying None.

    RED on HEAD f252acb4a, every test: an anchor of 0 was refused there, None where −1 is expected.
    """

    @pytest.mark.parametrize("reference", ZERO_ANCHOR_REFERENCES, ids=str)
    def test_range_change_is_minus_the_reference_and_minus_one(self, reference: Decimal) -> None:
        result = _range_change(reference, D("0"))

        assert (result.change_abs, result.change_ratio) == (-reference, D("-1")), result
        assert isinstance(result.change_abs, Decimal) and isinstance(result.change_ratio, Decimal), result
        assert (result.inverse_change_abs, result.inverse_change_ratio) == (None, None), result

    def test_every_period_with_a_positive_reference_is_minus_one_without_inverse(self) -> None:
        """Anchor 0 on TUESDAY; a positive reference on every period but 1M (none stored), 1Y (0) and 3Y (−3): those
        three None both ways, every other −1 with its inverse None."""
        values: dict[date, Decimal | None] = dict(_priced(fixed_period_dates(TUESDAY)))
        values[TUESDAY] = D("0")
        del values[_days_before(TUESDAY, 30)]
        values[_days_before(TUESDAY, 365)] = D("0")
        values[_days_before(TUESDAY, 1095)] = D("-3")

        changes = fixed_period_changes(values, TUESDAY)

        refused = {"1M", "1Y", "3Y"}
        got = {change.key: (change.change_ratio, change.inverse_change_ratio) for change in changes}
        assert got == {key: (None, None) if key in refused else (D("-1"), None) for key, _days in FIXED_PERIODS}, got

    @pytest.mark.parametrize("reference", ZERO_ANCHOR_REFERENCES, ids=str)
    def test_one_rule_for_the_range_and_the_periods(self, reference: Decimal) -> None:
        """One home: a period with the same two values gives the range's ratios, −1 and None."""
        (period,) = fixed_period_changes({TUESDAY: D("0"), _days_before(TUESDAY, 1): reference}, TUESDAY, (("1D", 1),))

        result = _range_change(reference, D("0"))

        assert (period.change_ratio, period.inverse_change_ratio) == (result.change_ratio, result.inverse_change_ratio) == (D("-1"), None), (period, result)
