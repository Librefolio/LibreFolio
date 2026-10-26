"""MF-P4b (cure B of D-P4), AI Export side: the performance buckets and the average NAV read the portfolio history as STEPS
and answer what they answered when it had one point for every day.

Why. The report's ``history`` becomes one point for each stretch of days on which nothing changed: each point holds from its
``date`` to its ``through``, both included (``CONTRATTO-P4b.md`` §1, §6). Three AI Export components read it day by day:
``build_performance_bucket_rows`` (``payloads/portfolio_broker.py``, called by ``portfolio_financial`` and ``broker_financial``)
and ``broker_cost_efficiency._average_nav``. Their datasets must not move by one digit.

The contract pinned here:

1. **Buckets.** ``build_performance_bucket_rows(steps, buckets, currency_code=…)`` gives, for a history of steps, the rows the
   frozen copy of the day-by-day function below (``day_by_day_bucket_rows``) gives for the same history expanded to one point per
   day. Every field: the first and last value of a bucket, the lowest and highest NAV **and the day each is reached** (the
   first day, on a tie; a step starts reaching its value on ``max(step.date, bucket.start_date)``), the previous close's
   **day** (the last day of the previous bucket that has data, not the first day of its step), the flow, the P&L, the return,
   the index to base 100. The date of a row is a day, never the ``date`` of a step.
2. **Edges.** A history that starts after the period's start or ends before its end, a bucket that touches no day of it (no
   data), a one-step history, an empty one, a NAV that repeats in two steps apart, a TWRR that is ``None`` at first.
3. **Average NAV.** ``_average_nav`` is the arithmetic mean of the NAV of every DAY, weighted by the length of each step
   (``through - date + 1``): the count is days, not steps, and the period runs from the first ``date`` to the last ``through``.
   A mean of the steps' NAVs is a different number, with no error to say so.

Isolation: PURE. No database, no server, no network; the history is built in the test. The steps are a dataclass with the
fields the readers use (the contract's readers work on any point with ``date`` and ``through``).

Red before the cure: the readers count a step as one day.
"""

from __future__ import annotations

import dataclasses
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.schemas.common import Currency
from backend.app.services.ai_export.components import broker_cost_efficiency
from backend.app.services.ai_export.components.payloads.portfolio_broker import PerformanceBucketRow, build_performance_bucket_rows
from backend.app.services.ai_export.temporal.uniform import uniform_calendar_buckets
from backend.app.services.financial_math.returns import price_return

EUR = "EUR"
PERIOD_START = date(2026, 1, 1)
PERIOD_END = date(2026, 10, 25)


@dataclasses.dataclass(frozen=True)
class Step:
    """A point of the history as the contract has it: the values hold from ``date`` to ``through``, both included."""

    date: date
    through: date
    nav_value: Currency
    capital_baseline: Currency
    total_pnl: Currency
    twrr: str | None


def _money(amount: str) -> Currency:
    return Currency(code=EUR, amount=Decimal(amount))


#: (length in days, nav, capital baseline, twrr): the NAV 1100.50 comes back after four steps (a tie apart), the TWRR is None at first
SHAPE = [
    (1, "1000.00", "1000.00", None),
    (3, "1000.00", "1000.00", None),
    (1, "1100.50", "1000.00", "0.100500"),
    (12, "1090.25", "1000.00", "0.090250"),
    (2, "1500.00", "1400.00", "0.090250"),
    (40, "1450.75", "1400.00", "0.036250"),
    (1, "1100.50", "1000.00", "0.100500"),
    (1, "1200.00", "1000.00", "0.200000"),
    (9, "1190.00", "1000.00", "0.190000"),
    (60, "1300.00", "1000.00", "0.300000"),
    (7, "900.10", "1000.00", "-0.099900"),
    (90, "1000.00", "1000.00", "0.000000"),
    (70, "1250.40", "1100.00", "0.250400"),
]


def steps_from(first: date, last: date | None = None) -> list[Step]:
    """The shape above laid from ``first``, cut at ``last`` (inclusive) when it is given."""
    steps: list[Step] = []
    cursor = first
    for length, nav, baseline, twrr in SHAPE:
        end = cursor + timedelta(days=length - 1)
        if last is not None and cursor > last:
            break
        if last is not None and end > last:
            end = last
        steps.append(Step(date=cursor, through=end, nav_value=_money(nav), capital_baseline=_money(baseline), total_pnl=_money(str(Decimal(nav) - Decimal(baseline))), twrr=twrr))
        cursor = end + timedelta(days=1)
    return steps


def expand(steps: list[Step]) -> list[Step]:
    """Every step as one point for each of its days: the history as it was before the cure."""
    return [dataclasses.replace(step, date=day, through=day) for step in steps for day in (step.date + timedelta(days=n) for n in range((step.through - step.date).days + 1))]


def day_by_day_bucket_rows(history, buckets, *, currency_code: str) -> tuple[PerformanceBucketRow, ...]:
    """``build_performance_bucket_rows`` at d96519b86, frozen here: one point for every day. The reference the steps are measured against."""
    ordered_history = tuple(sorted(history, key=lambda point: point.date))
    previous_close = None
    rows: list[PerformanceBucketRow] = []
    first_twrr_observation = next((point for point in ordered_history if point.twrr is not None), None)
    for bucket in buckets:
        bucket_points = tuple(point for point in ordered_history if bucket.start_date <= point.date <= bucket.end_date)
        if not bucket_points:
            rows.append(PerformanceBucketRow(index=bucket.index, start_date=bucket.start_date, end_date=bucket.end_date, has_data=False))
            continue
        first_point = bucket_points[0]
        end_point = bucket_points[-1]
        min_point = min(bucket_points, key=lambda point: point.nav_value.amount)
        max_point = max(bucket_points, key=lambda point: point.nav_value.amount)
        net_external_flow = None
        period_pnl = None
        return_percent = None
        reconciliation_diff = None
        if previous_close is not None:
            net_external_flow = Currency(code=currency_code, amount=(end_point.capital_baseline.amount - previous_close.capital_baseline.amount))
            period_pnl = Currency(code=currency_code, amount=end_point.total_pnl.amount - previous_close.total_pnl.amount)
            reconciliation_diff = Currency(code=currency_code, amount=(end_point.nav_value.amount - previous_close.nav_value.amount - net_external_flow.amount - period_pnl.amount))
            if previous_close.twrr is not None and end_point.twrr is not None:
                return_percent = price_return(Decimal(1) + Decimal(previous_close.twrr), Decimal(1) + Decimal(end_point.twrr))
        rows.append(
            PerformanceBucketRow(
                index=bucket.index,
                start_date=bucket.start_date,
                end_date=bucket.end_date,
                has_data=True,
                start_value=first_point.nav_value,
                end_value=end_point.nav_value,
                min_value=min_point.nav_value,
                max_value=max_point.nav_value,
                min_date=min_point.date,
                max_date=max_point.date,
                variation_start_date=(previous_close.date if previous_close is not None else None),
                variation_start_value=(previous_close.nav_value if previous_close is not None else None),
                net_external_flow=net_external_flow,
                period_pnl=period_pnl,
                return_percent=return_percent,
                normalized_index_base_100=(
                    (Decimal(1) + Decimal(end_point.twrr)) / (Decimal(1) + Decimal(first_twrr_observation.twrr)) * Decimal("100")
                    if first_twrr_observation is not None and first_twrr_observation.twrr is not None and end_point.twrr is not None and Decimal(1) + Decimal(first_twrr_observation.twrr) != 0
                    else None
                ),
                return_from_first_ratio=(price_return(Decimal(1) + Decimal(first_twrr_observation.twrr), Decimal(1) + Decimal(end_point.twrr)) if first_twrr_observation is not None and first_twrr_observation.twrr is not None and end_point.twrr is not None else None),
                reconciliation_diff=reconciliation_diff,
            )
        )
        previous_close = end_point
    return tuple(rows)


def day_by_day_average_nav(history, target_currency: str):
    """``_average_nav``'s history branch at d96519b86, frozen here."""
    values = tuple(point.nav_value.amount for point in history)
    return (Currency(code=target_currency, amount=sum(values, Decimal("0")) / Decimal(len(values))), "arithmetic_mean_of_available_daily_nav", len(values), history[0].date, history[-1].date)


#: name → the history of steps: it covers the period, starts late, ends early, is one step, a few days, or empty
HISTORIES = {
    "covers-the-period": steps_from(PERIOD_START),
    "starts-late": steps_from(PERIOD_START + timedelta(days=23)),
    "ends-early": steps_from(PERIOD_START, PERIOD_START + timedelta(days=150)),
    "starts-late-ends-early": steps_from(PERIOD_START + timedelta(days=40), PERIOD_START + timedelta(days=200)),
    "one-step": [Step(date=PERIOD_START, through=PERIOD_END, nav_value=_money("1000.00"), capital_baseline=_money("1000.00"), total_pnl=_money("0.00"), twrr="0.000000")],
    "one-day": [Step(date=PERIOD_START + timedelta(days=100), through=PERIOD_START + timedelta(days=100), nav_value=_money("1000.00"), capital_baseline=_money("900.00"), total_pnl=_money("100.00"), twrr=None)],
    "empty": [],
}


def _dump(rows) -> list[dict[str, Any]]:
    return [row.model_dump(mode="json") for row in rows]


@pytest.mark.parametrize("bucket_count", [1, 4, 8, 16, 30])
@pytest.mark.parametrize("name", list(HISTORIES))
def test_aps01_the_bucket_rows_of_steps_are_those_of_the_days(name, bucket_count):
    """APS-01: for each history and bucket plan, the rows built from the steps equal, field by field, the rows of the
    day-by-day function on the same history expanded to days — the days of the extremes and of the previous close included.

    Red before the cure: a step counts as one day, on its first day.
    """
    steps = HISTORIES[name]
    buckets = uniform_calendar_buckets(PERIOD_START, PERIOD_END, bucket_count)

    from_steps = build_performance_bucket_rows(steps, buckets, currency_code=EUR)
    from_days = day_by_day_bucket_rows(expand(steps), buckets, currency_code=EUR)

    assert _dump(from_steps) == _dump(from_days), f"{name}, {bucket_count} buckets"


def test_aps02_the_day_of_an_extreme_is_the_day_not_the_start_of_its_step():
    """APS-02: the highest NAV of the shape (1500.00) holds for two days; a bucket that starts inside that step reaches it on
    the bucket's first day, and the previous close is the previous bucket's last DAY. The guard that a step's ``date`` is never
    reported as a day.

    Red before the cure: the row says the step's first day.
    """
    steps = HISTORIES["covers-the-period"]
    high = next(step for step in steps if step.nav_value.amount == Decimal("1500.00"))
    inside = high.date + timedelta(days=1)  # the second day of the two-day step
    buckets = uniform_calendar_buckets(inside, PERIOD_END, 3)

    rows = build_performance_bucket_rows(steps, buckets, currency_code=EUR)

    assert rows[0].max_value == high.nav_value and rows[0].max_date == inside
    assert rows[1].variation_start_date == buckets[0].end_date


def test_aps03_a_tie_between_steps_apart_is_the_earliest_day():
    """APS-03: the lowest NAV (900.00) is reached by the second step and by the fourth, and the highest (1000.00) by the first
    and the third. One bucket holds all four: ``min``/``max`` on the days take the first day each is reached, and so must the
    steps (the second step's ``date`` for the low, the period's first day for the high)."""
    start = PERIOD_START
    steps = [
        Step(date=start + timedelta(days=offset), through=start + timedelta(days=offset + length - 1), nav_value=_money(nav), capital_baseline=_money("800.00"), total_pnl=_money(str(Decimal(nav) - Decimal("800.00"))), twrr="0.100000")
        for offset, length, nav in [(0, 3, "1000.00"), (3, 2, "900.00"), (5, 4, "1000.00"), (9, 5, "900.00")]
    ]
    bucket = uniform_calendar_buckets(start, start + timedelta(days=13), 1)

    (row,) = build_performance_bucket_rows(steps, bucket, currency_code=EUR)
    (reference,) = day_by_day_bucket_rows(expand(steps), bucket, currency_code=EUR)

    assert (row.min_date, row.max_date) == (start + timedelta(days=3), start) == (reference.min_date, reference.max_date)


@pytest.mark.parametrize("name", [name for name in HISTORIES if HISTORIES[name]])
def test_aps04_the_average_nav_is_the_mean_of_the_days_not_of_the_steps(name):
    """APS-04: ``_average_nav`` on a history of steps gives the mean NAV of every day (weighted by the step's length), the
    count in days, and the period from the first ``date`` to the last ``through``.

    Red before the cure: it averages the steps and counts them.
    """
    steps = HISTORIES[name]
    report = SimpleNamespace(history=steps)

    answer = broker_cost_efficiency._average_nav(report, None, target_currency=EUR)
    reference = day_by_day_average_nav(expand(steps), EUR)

    assert answer[0] == reference[0] and answer[0].amount.as_tuple() == reference[0].amount.as_tuple(), f"{name}: {answer[0]} != {reference[0]}"
    assert answer[1:] == reference[1:], name
    assert answer[2] == sum((step.through - step.date).days + 1 for step in steps), "the count is days"


def test_aps05_the_average_nav_adds_the_days_in_order_as_the_day_by_day_mean_does():
    """APS-05: a NAV is a long Decimal (a converted value has 28 or more significant digits) and the context rounds each
    addition, so ``nav * days`` is not the sum of ``days`` additions in the last digits. The probe on the real copies found it:
    the mean of 365 days differed in the 27th digit. The mean of steps adds each NAV once for each of its days, in order, and
    is the day-by-day mean to the digit and the exponent.

    Red before the fix: it multiplied the NAV by the length of its step.
    """
    nav = ["7494.150670142390036005801342", "7500.987654321098765432109876", "7488.111111111111111111111111", "7501.333333333333333333333333"]
    lengths = [97, 130, 61, 77]
    start = date(2026, 1, 1)
    steps = []
    cursor = start
    for amount, length in zip(nav, lengths, strict=True):
        steps.append(Step(date=cursor, through=cursor + timedelta(days=length - 1), nav_value=_money(amount), capital_baseline=_money("1000.00"), total_pnl=_money("0.00"), twrr=None))
        cursor += timedelta(days=length)

    answer = broker_cost_efficiency._average_nav(SimpleNamespace(history=steps), None, target_currency=EUR)
    reference = day_by_day_average_nav(expand(steps), EUR)

    assert answer[0].amount.as_tuple() == reference[0].amount.as_tuple(), f"{answer[0].amount} != {reference[0].amount}"
    assert answer[1:] == reference[1:]
