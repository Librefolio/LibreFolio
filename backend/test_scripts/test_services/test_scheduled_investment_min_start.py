"""
The Scheduled Investment history from ``"min"`` — MF-SI1 (LibreFolio 1.3.0, workstream MF).

``AssetHistoryStartDate`` is ``date | "min"``, and ``"min"`` means "from the earliest available point"
(``services/assets/base.py``). ``services/assets/refresh.py`` asks for ``"min"`` when an asset has no stored price yet,
so the first sync of every new Scheduled Investment asset goes through it.

Before: ``get_history_value`` resolved ``"min"`` into ``effective_start`` (the schedule's first value date), then still
compared the literal ``start_date`` with dates — in the initial-value anchor (``start_date < min(cached)``) and in the
three event filters (``start_date <= e.date <= end_date``). ``"min" < date`` is a ``TypeError``, wrapped in
``AssetSourceError(CALCULATION_ERROR)``. With an empty schedule only the manual-event filter compares it, so an empty
schedule without manual events did not raise.

Now ``"min"`` is the earliest of the schedule's first value date (``min(cached)``) and its manual events' dates, else
``end_date``: ``min([*cached, *event dates], default=end_date)``. A refresh reads ``"min"`` once, on the first sync, so a
manual event dated before the schedule would never be read again. The history from ``"min"`` is the history asked from
that date, price by price and event by event:
    - events only after the schedule start: the history from ``schedule[0].start_date``, with no initial-value anchor;
      auto INTEREST, late INTEREST / MATURITY_SETTLEMENT and manual events dated on or after it;
    - a manual event before the schedule start: the history from that event's date, so the initial-value anchor on that
      date, as an explicit early start gives it;
    - an empty schedule (``validate_params({})`` builds one; an explicit ``schedule: []`` is the other way to have no
      values): the history from the earliest manual event, else from ``end_date``;
    - an explicit date behaves as before.

Sections:
    A. ``"min"`` on a schedule (Red): MONTHLY coupons with a manual PRICE_ADJUSTMENT; COMPOUND late interest with
       generate_interest and an end after maturity; manual events before the schedule start. Each equals the explicit
       call at ``min(first start, earliest event)``, field by field.
    B. ``"min"`` on an empty schedule: with manual events (Red: the manual-event filter compares the literal), without
       (Guard: nothing compares it, before or after the fix: an empty history).
    C. Explicit start (Guard: green before and after): before the schedule start, the initial-value anchor at that date
       and the schedule's history after it; inside the schedule, the prices and events from that date on.

Every test deletes the ``_CACHE`` entry of its schedule before (cold) and after (no leftovers).

Pure: no database, no server, no network.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import pytest

from backend.app.db.models import IdentifierType
from backend.app.schemas.assets.events import FAAssetEventPoint
from backend.app.schemas.assets.scheduled_investment import (
    DayCountConvention,
    FAInterestRatePeriod,
    FALateInterestConfig,
    FAScheduledInvestmentSchedule,
    InterestType,
    MaturationFrequency,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import FAHistoricalData, FAPricePoint
from backend.app.services.asset_source_providers.scheduled_investment.plugin import (
    _CACHE,
    ScheduledInvestmentProvider,
    _cache_key,
)
from backend.app.services.assets.base import AssetSourceError

IDENTIFIER = "mf-si1"


# ============================================================================
# Helpers
# ============================================================================


@contextmanager
def _own_cache_entry(provider_params: dict) -> Iterator[None]:
    """The ``_CACHE`` entry of the schedule the provider validates from ``provider_params``: absent when the block
    starts, deleted when it ends."""
    key = _cache_key(ScheduledInvestmentProvider().validate_params(provider_params))
    _CACHE.delete(key)
    try:
        yield
    finally:
        _CACHE.delete(key)


async def _history(provider_params: dict, start: date | str, end: date) -> FAHistoricalData:
    """The provider's history from ``start`` to ``end``; an ``AssetSourceError`` fails the test with its code."""
    try:
        return await ScheduledInvestmentProvider().get_history_value(IDENTIFIER, IdentifierType.OTHER, provider_params, start, end)
    except AssetSourceError as exc:
        pytest.fail(f"get_history_value(start_date={start!r}, end_date={end}) raised AssetSourceError({exc.error_code}): {exc.message}")


def _assert_same_points(kind: str, actual: list, expected: list) -> None:
    """``actual`` equals ``expected`` point by point, in order, every field compared."""
    got = [point.model_dump() for point in actual]
    want = [point.model_dump() for point in expected]
    mismatch = next((index for index, (g, w) in enumerate(zip(got, want, strict=False)) if g != w), None)
    assert mismatch is None, f"{kind}[{mismatch}]: {got[mismatch]} != expected {want[mismatch]}"
    assert len(got) == len(want), f"{kind}: {len(got)} points, expected {len(want)}; first unmatched: {(got if len(got) > len(want) else want)[min(len(got), len(want))]}"


def _assert_same_history(actual: FAHistoricalData, expected: FAHistoricalData) -> None:
    """Same currency and source, same price points, same events."""
    assert (actual.currency, actual.source) == (expected.currency, expected.source)
    _assert_same_points("prices", actual.prices, expected.prices)
    _assert_same_points("events", actual.events, expected.events)


def _eur(amount: str) -> Currency:
    return Currency(code="EUR", amount=Decimal(amount))


def _earliest_point(schedule: FAScheduledInvestmentSchedule) -> date:
    """What ``"min"`` means for a schedule with periods: its first start or its earliest manual event, the earlier."""
    return min([schedule.schedule[0].start_date, *(event.date for event in schedule.asset_events)])


def _monthly_coupon_schedule() -> FAScheduledInvestmentSchedule:
    """Two MONTHLY periods paying coupons (auto INTEREST at each maturation date), no late interest (so a
    MATURITY_SETTLEMENT on 2024-12-31), a manual PRICE_ADJUSTMENT inside the first period."""
    return FAScheduledInvestmentSchedule(
        initial_value=_eur("10000"),
        interest_type=InterestType.SIMPLE,
        day_count=DayCountConvention.ACT_365,
        schedule=[
            FAInterestRatePeriod(start_date=date(2024, 1, 15), end_date=date(2024, 7, 14), annual_rate=Decimal("0.05"), maturation_frequency=MaturationFrequency.MONTHLY, generate_interest=True),
            FAInterestRatePeriod(start_date=date(2024, 7, 15), end_date=date(2024, 12, 31), annual_rate=Decimal("0.04"), maturation_frequency=MaturationFrequency.MONTHLY, generate_interest=True),
        ],
        asset_events=[FAAssetEventPoint(date=date(2024, 3, 20), type="PRICE_ADJUSTMENT", value=_eur("150"), notes="Manual revaluation")],
    )


MONTHLY_END = date(2025, 2, 28)  # after maturity: the settlement value is the anchor at end_date

LATE_MATURITY = date(2023, 10, 31)


def _late_compound_schedule() -> FAScheduledInvestmentSchedule:
    """A COMPOUND QUARTERLY period paying coupons, then COMPOUND late interest with generate_interest (late INTEREST at
    each MONTHLY late date, a late MATURITY_SETTLEMENT at the last one); a manual PRICE_ADJUSTMENT inside the period and
    a manual INTEREST after maturity."""
    return FAScheduledInvestmentSchedule(
        initial_value=_eur("5000"),
        interest_type=InterestType.COMPOUND,
        day_count=DayCountConvention.ACT_360,
        schedule=[
            FAInterestRatePeriod(start_date=date(2023, 2, 1), end_date=LATE_MATURITY, annual_rate=Decimal("0.06"), maturation_frequency=MaturationFrequency.QUARTERLY, generate_interest=True),
        ],
        late_interest=FALateInterestConfig(annual_rate=Decimal("0.12"), grace_period_days=30, interest_type=InterestType.COMPOUND, maturation_frequency=MaturationFrequency.MONTHLY, generate_interest=True),
        asset_events=[
            FAAssetEventPoint(date=date(2023, 5, 10), type="PRICE_ADJUSTMENT", value=_eur("75")),
            FAAssetEventPoint(date=date(2023, 12, 15), type="INTEREST", value=_eur("40"), notes="Manual late payment"),
        ],
    )


LATE_END = date(2024, 3, 31)


# ============================================================================
# A. "min" on a schedule: the history from its earliest point
# ============================================================================


@pytest.mark.asyncio
async def test_min_on_monthly_coupon_schedule_equals_first_start_history():
    """Red before MF-SI1: ``"min"`` raised CALCULATION_ERROR (``"min" < date`` in the anchor). Now it is the history
    from ``min(first start, earliest event)`` — here the first start, the manual event being inside the schedule: same
    prices, no anchor before it, same coupons, PRICE_ADJUSTMENT and settlement."""
    schedule = _monthly_coupon_schedule()
    params = schedule.model_dump(mode="json")
    first_start = schedule.schedule[0].start_date
    with _own_cache_entry(params):
        expected = await _history(params, _earliest_point(schedule), MONTHLY_END)
        actual = await _history(params, "min", MONTHLY_END)

    # The reference is not vacuous: it starts on the first start and carries every kind of event under test.
    assert expected.prices[0].date == first_start
    assert {"INTEREST", "PRICE_ADJUSTMENT", "MATURITY_SETTLEMENT"} <= {event.type for event in expected.events}
    _assert_same_history(actual, expected)


@pytest.mark.asyncio
async def test_min_with_late_compound_interest_equals_first_start_history():
    """Red before MF-SI1, as above. With late interest and ``end_date`` after maturity, ``"min"`` also keeps the late
    prices, the late INTEREST events and the late MATURITY_SETTLEMENT, and the manual event dated after maturity."""
    schedule = _late_compound_schedule()
    params = schedule.model_dump(mode="json")
    first_start = schedule.schedule[0].start_date
    with _own_cache_entry(params):
        expected = await _history(params, _earliest_point(schedule), LATE_END)
        actual = await _history(params, "min", LATE_END)

    assert expected.prices[0].date == first_start
    assert any(point.date > LATE_MATURITY for point in expected.prices)
    assert {"INTEREST", "MATURITY_SETTLEMENT"} <= {event.type for event in expected.events if event.date > LATE_MATURITY}
    expected_events = [event.model_dump() for event in expected.events]
    assert all(event.model_dump() in expected_events for event in schedule.asset_events)
    _assert_same_history(actual, expected)


_EVENTS_BEFORE_START = {
    "one-event": [FAAssetEventPoint(date=date(2023, 11, 20), type="INTEREST", value=_eur("35"), notes="Paid before the schedule")],
    # Out of date order: the earliest is the second, so "the first listed" is not "the earliest".
    "two-events-out-of-order": [
        FAAssetEventPoint(date=date(2023, 12, 28), type="PRICE_ADJUSTMENT", value=_eur("12")),
        FAAssetEventPoint(date=date(2023, 10, 5), type="INTEREST", value=_eur("20")),
    ],
}


@pytest.mark.asyncio
@pytest.mark.parametrize("early_events", list(_EVENTS_BEFORE_START.values()), ids=list(_EVENTS_BEFORE_START))
async def test_min_reaches_back_to_a_manual_event_before_the_schedule(early_events):
    """Red before MF-SI1 (CALCULATION_ERROR), and red on a ``"min"`` that stops at the schedule's first value (the
    earlier events are dropped, no anchor). Now ``"min"`` is the earliest manual event's date: every manual event in
    the result, the initial-value anchor on that date, and the history the explicit call from that date gives."""
    base = _monthly_coupon_schedule()
    schedule = base.model_copy(update={"asset_events": [*early_events, *base.asset_events]})
    params = schedule.model_dump(mode="json")
    earliest = min(event.date for event in early_events)
    assert earliest < schedule.schedule[0].start_date
    with _own_cache_entry(params):
        actual = await _history(params, "min", MONTHLY_END)
        expected = await _history(params, earliest, MONTHLY_END)

    actual_events = [event.model_dump() for event in actual.events]
    missing = [event.model_dump() for event in schedule.asset_events if event.model_dump() not in actual_events]
    assert not missing, f"manual events missing from the history from 'min': {missing}"
    anchor = FAPricePoint(date=earliest, close=schedule.initial_value.amount, currency=schedule.initial_value.code)
    assert actual.prices, "no price point at all"
    _assert_same_points("prices[:1]", actual.prices[:1], [anchor])
    _assert_same_history(actual, expected)


# ============================================================================
# B. "min" on an empty schedule: from the earliest manual event, else end_date
# ============================================================================

EMPTY_END = date(2024, 12, 31)

_EMPTY_SCHEDULE_EVENTS = {
    "one-event": [FAAssetEventPoint(date=date(2024, 6, 3), type="INTEREST", value=_eur("120"), notes="Manual payout")],
    # Out of date order: the earliest is the second, so "the first listed" is not "the earliest".
    "two-events-out-of-order": [
        FAAssetEventPoint(date=date(2024, 9, 1), type="PRICE_ADJUSTMENT", value=_eur("30")),
        FAAssetEventPoint(date=date(2024, 4, 2), type="INTEREST", value=_eur("55")),
    ],
}


@pytest.mark.asyncio
@pytest.mark.parametrize("events", list(_EMPTY_SCHEDULE_EVENTS.values()), ids=list(_EMPTY_SCHEDULE_EVENTS))
async def test_min_on_empty_schedule_starts_at_earliest_manual_event(events):
    """Red before MF-SI1: the manual-event filter compared ``"min"`` with the event's date. Now ``"min"`` is the earliest
    manual event's date: no exception, every manual event in the result, and the history the explicit call from that
    date gives."""
    params = FAScheduledInvestmentSchedule(initial_value=_eur("10000"), schedule=[], asset_events=events).model_dump(mode="json")
    earliest = min(event.date for event in events)
    with _own_cache_entry(params):
        actual = await _history(params, "min", EMPTY_END)
        expected = await _history(params, earliest, EMPTY_END)

    actual_events = [event.model_dump() for event in actual.events]
    missing = [event.model_dump() for event in events if event.model_dump() not in actual_events]
    assert not missing, f"manual events missing from the history from 'min': {missing}"
    _assert_same_history(actual, expected)


_NO_VALUES_PARAMS = {
    # validate_params({}) builds the probe's default: EUR 10000, no period.
    "probe-default": {},
    "explicit-empty-schedule": {"initial_value": {"code": "USD", "amount": "2500"}, "schedule": []},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("params", list(_NO_VALUES_PARAMS.values()), ids=list(_NO_VALUES_PARAMS))
async def test_min_on_empty_schedule_without_events_is_empty(params):
    """Guard (green before MF-SI1 too: nothing compared ``"min"`` when there is neither a value nor an event). ``"min"``
    is ``end_date``: no exception, no price, no event — the history the explicit call from ``end_date`` gives."""
    currency = ScheduledInvestmentProvider().validate_params(params).initial_value.code
    with _own_cache_entry(params):
        actual = await _history(params, "min", EMPTY_END)
        expected = await _history(params, EMPTY_END, EMPTY_END)

    assert actual.prices == []
    assert actual.events == []
    assert actual.currency == currency
    _assert_same_history(actual, expected)


# ============================================================================
# C. Explicit start: unchanged
# ============================================================================


@pytest.mark.asyncio
async def test_explicit_start_before_schedule_inserts_initial_value_anchor():
    """Guard (green before and after MF-SI1). A start before the schedule's first start emits the initial value on that
    start date, then exactly the history from the first start."""
    schedule = _monthly_coupon_schedule()
    params = schedule.model_dump(mode="json")
    first_start = schedule.schedule[0].start_date
    early_start = date(2023, 12, 1)
    with _own_cache_entry(params):
        actual = await _history(params, early_start, MONTHLY_END)
        from_first_start = await _history(params, first_start, MONTHLY_END)

    anchor = FAPricePoint(date=early_start, close=schedule.initial_value.amount, currency=schedule.initial_value.code)
    assert actual.prices, "no price point at all"
    _assert_same_points("prices[:1]", actual.prices[:1], [anchor])
    _assert_same_points("prices[1:]", actual.prices[1:], from_first_start.prices)
    _assert_same_points("events", actual.events, from_first_start.events)


@pytest.mark.asyncio
async def test_explicit_start_inside_schedule_keeps_prices_and_events_from_it():
    """Guard (green before and after MF-SI1). A start inside the schedule emits no anchor: the prices and the events of
    the history from the first start that are dated on or after it."""
    schedule = _monthly_coupon_schedule()
    params = schedule.model_dump(mode="json")
    mid_start = date(2024, 5, 1)
    with _own_cache_entry(params):
        actual = await _history(params, mid_start, MONTHLY_END)
        full = await _history(params, schedule.schedule[0].start_date, MONTHLY_END)

    # The cut drops something on both sides, the PRICE_ADJUSTMENT of 2024-03-20 among the events.
    assert any(point.date < mid_start for point in full.prices)
    assert any(event.date < mid_start for event in full.events)
    _assert_same_points("prices", actual.prices, [point for point in full.prices if point.date >= mid_start])
    _assert_same_points("events", actual.events, [event for event in full.events if event.date >= mid_start])
