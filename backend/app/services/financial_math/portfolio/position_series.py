"""The daily series of a position: its P&L and its base, one point per calendar day (J5-1, #48).

The chart of the Dashboard's positions draws one line per chosen position. A line is the position's result since the
period's start, day by day: the Performance table's ``period_pnl`` of the period from ``date_from`` to each day, so the
last point of a series is the table's row. This module is the pure side: it takes the engine's frames of each position
(the state of a position over a stretch of days in which it does not change), the realized sales, the income and costs
steps, the internal transfers and the cost of what was bought, and returns the series. It reads no database and builds
no daily state: each figure of a day is a lookup in the stretches (a bisection), never a replay of the days before it.

**Volume (D-P4).** A series is one point per calendar day and per requested position, so its size is the days of the window
times the positions asked: a typo'd first year would ask for ~740 000 points per series. The API keeps the daily point; the
Dashboard asks for a window its chart can draw (sampled on the long ones, as the cards of Z-29 do). Nothing here limits it.

The rules, which the developer decided on 18/10 and 23/10 (plan 05, «Ondata 5»):

* **pnl** on day ``d`` = the change of the position's unrealized result since ``date_from`` (its frame of ``d`` against its
  frame of ``date_from``, plus the tract an internal transfer gave it: ``contributions.transfer_tract_adjustments``) + the
  realized gain of its sales in ``(date_from, d]`` + its income - its fees and taxes over the same days;
* **base** = the size of the value at ``date_from`` + the cost of what is bought after it + what an internal transfer
  brings in: at its value on arrival when the period splits its tract (``contributions.counted_tract``, the units' pnl is then
  measured from that value), else at the cost moved, which is where the plain boundary values measure their pnl from; as the
  Performance row's base does (``contributions.annualized_period_return``). A sale never lowers it. ``pnl_percent`` = pnl / base, a fraction, unrounded; None
  when the base is 0 or unknown;
* one point per **calendar day** from ``first_date`` to ``last_date``; ``last_date`` is ``date_to`` while the position is
  held, else the day it went to 0 (that day's point has quantity 0, value 0 and the final pnl);
* ``None`` is «not known», never 0. A day without a market value has a pnl of the parts that are known, flagged
  ``complete = False``, as the Performance row does;
* a request for ``(None, asset)`` is the asset summed over the brokers that held it. The tracts of an internal transfer
  cancel in the sum and what it brings in is not new capital; a closed leg keeps its final pnl and base.

Everything is in the report currency at the owner's share: the engine's frames are already scaled. The module imports
nothing outside ``financial_math`` and the data-quality thresholds.

A position is *held* when its quantity is above ``QUANTITY_DUST_THRESHOLD``. Below it a day's point is 0 in quantity and value,
while the engine's day totals still count the dust: the sum of the series' ``market_value`` equals the report's on every day
whose positions are held, and only there.
"""

from __future__ import annotations

import bisect
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal

from backend.app.services.financial_math.average_cost import AverageCost, CostMovementKind
from backend.app.services.financial_math.portfolio.contributions import counted_tract, position_period_pnl, transfer_tract
from backend.app.services.financial_math.portfolio.models import InternalAssetTransfer, PositionFrame, RealizedSale
from backend.app.services.financial_math.returns import realized_gain
from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD

_ZERO = Decimal("0")

#: ``(broker_id, asset_id)``: a position at one broker.
PositionKey = tuple[int, int]
#: What is asked for: ``(broker_id, asset_id)``, or ``(None, asset_id)`` for the asset summed over its brokers.
PositionRequest = tuple[int | None, int]


@dataclass(frozen=True, slots=True)
class SeriesPoint:
    """One day of a position's series."""

    date: date_type
    quantity: Decimal
    market_value: Decimal | None
    cost_basis: Decimal | None
    pnl: Decimal | None
    base: Decimal | None
    pnl_percent: Decimal | None
    valuation_source: str | None
    complete: bool


@dataclass(frozen=True, slots=True)
class PositionSeriesData:
    """The series of one request: its points, and where the position starts and ends inside the window."""

    key: PositionRequest
    first_date: date_type | None
    last_date: date_type | None
    held_at_start: bool
    held_at_end: bool
    closed_on: date_type | None
    points: list[SeriesPoint]
    complete: bool


@dataclass(frozen=True, slots=True)
class _Steps:
    """A cumulative amount that changes on given days, read by day: sums over ``(date_from, d]`` are two lookups."""

    days: tuple[date_type, ...]
    cumulative: tuple[Decimal, ...]

    def up_to(self, day: date_type) -> Decimal:
        index = bisect.bisect_right(self.days, day) - 1
        return self.cumulative[index] if index >= 0 else _ZERO

    def moved_in(self, date_from: date_type | None, day: date_type) -> bool:
        """Whether a step falls in ``(date_from, day]``."""
        low = 0 if date_from is None else bisect.bisect_right(self.days, date_from)
        return bisect.bisect_right(self.days, day) > low


def _steps_of(items: Sequence[tuple[date_type, Decimal]]) -> _Steps:
    ordered = sorted(items, key=lambda item: item[0])
    total = _ZERO
    days: list[date_type] = []
    cumulative: list[Decimal] = []
    for day, amount in ordered:
        total += amount
        if days and days[-1] == day:
            cumulative[-1] = total
        else:
            days.append(day)
            cumulative.append(total)
    return _Steps(tuple(days), tuple(cumulative))


@dataclass(frozen=True, slots=True)
class _Cumulative:
    """A running total given at the days it changes, as stored: ``(day, total up to and including it)``."""

    days: tuple[date_type, ...]
    totals: tuple[Decimal, ...]

    def at(self, day: date_type | None) -> Decimal:
        if day is None:
            return _ZERO
        index = bisect.bisect_right(self.days, day) - 1
        return self.totals[index] if index >= 0 else _ZERO


def _held(frame: PositionFrame | None) -> bool:
    return frame is not None and frame.quantity > QUANTITY_DUST_THRESHOLD


class _PositionReader:
    """One position's frames, read by day."""

    def __init__(self, frames: Sequence[PositionFrame]) -> None:
        self.frames = list(frames)
        self._starts = [frame.start for frame in self.frames]

    def on(self, day: date_type) -> PositionFrame | None:
        index = bisect.bisect_right(self._starts, day) - 1
        if index < 0:
            return None
        frame = self.frames[index]
        return frame if day <= frame.end else None


def _single(  # noqa: C901 — one pass over the days of a position: boundaries, the parts of its pnl, its base, the days in transit
    key: PositionKey,
    *,
    date_from: date_type | None,
    date_to: date_type,
    reader: _PositionReader,
    sales: Sequence[RealizedSale],
    flow_steps: Sequence[tuple[date_type, Decimal, Decimal]],
    transfers: Sequence[InternalAssetTransfer],
    acquisitions: Sequence[tuple[date_type, Decimal]],
) -> tuple[PositionSeriesData, dict[date_type, _Parts]]:
    """The series of one position at one broker, and its base's parts by day (what the asset-level sum needs)."""
    start_frame = reader.on(date_from) if date_from is not None else None
    held_at_start = _held(start_frame)
    held_frames = [frame for frame in reader.frames if frame.quantity > QUANTITY_DUST_THRESHOLD and frame.start <= date_to]
    lower = date_from
    first_date: date_type | None = None
    if held_at_start:
        first_date = date_from
    else:
        for frame in held_frames:
            candidate = frame.start if lower is None else max(frame.start, lower + timedelta(days=1))
            if candidate <= min(frame.end, date_to):
                first_date = candidate
                break
    if first_date is None:
        return PositionSeriesData(key, None, None, False, False, None, [], True), {}
    held_at_end = _held(reader.on(date_to))
    last_held = max(min(frame.end, date_to) for frame in held_frames)
    last_date = date_to if held_at_end else last_held + timedelta(days=1)
    closed_on = None if held_at_end else last_date
    # Units sent to another broker of the scope are the sender's until they arrive (P22): the series goes on to the arrival, where
    # the tract settles their result, and holds the pnl of the last day held while they are on their way.
    transit_end: date_type | None = None
    if not held_at_end:
        arrivals = [t.arrival for t in transfers if t.sender_broker_id == key[0] and t.asset_id == key[1] and last_date <= t.arrival <= date_to and counted_tract(t, date_from, t.arrival)]
        transit_end = max(arrivals, default=None)
        if transit_end is not None:
            last_date = max(last_date, transit_end)

    start_value = (start_frame.market_value if held_at_start else _ZERO) if date_from is not None else _ZERO
    ug_start = start_frame.unrealized_pnl if held_at_start else None

    # ``sales`` are the period's (``period.period_realized_sales``): dated in (date_from, date_to], proceeds and cost known.
    gains = [(sale.date, realized_gain(sale.proceeds, sale.cost)) for sale in sales]
    realized = _steps_of([(day, gain) for day, gain in gains if gain is not None])
    sale_days = sorted({day for day, _ in gains})
    income = _Cumulative(tuple(step[0] for step in flow_steps), tuple(step[1] for step in flow_steps))
    costs = _Cumulative(tuple(step[0] for step in flow_steps), tuple(step[2] for step in flow_steps))
    flow_days = tuple(step[0] for step in flow_steps)
    bought = _steps_of(list(acquisitions))
    tract_adjustments = _steps_of([(t.arrival, transfer_tract(t, key[0])) for t in transfers if _takes_part(t, key) and counted_tract(t, date_from, t.arrival)])
    brought_in = _steps_of([(t.arrival, base) for t in transfers if t.receiver_broker_id == key[0] and t.asset_id == key[1] and (date_from is None or t.arrival > date_from) and (base := _arrival_base(t, date_from)) is not None])
    start_unknown_base = held_at_start and start_value is None

    points: list[SeriesPoint] = []
    parts: dict[date_type, _Parts] = {}
    day = first_date
    while day <= last_date:
        frame = reader.on(day)
        held = _held(frame)
        if not held and transit_end is not None and last_held < day < transit_end and points:
            # In transit: the units are on their way, their result is settled on arrival. The point keeps the last held day's pnl.
            before = points[-1]
            points.append(SeriesPoint(day, _ZERO, _ZERO, _ZERO, before.pnl, before.base, before.pnl_percent, None, before.complete))
            parts[day] = _Parts(brought_in=brought_in.up_to(day))
            day += timedelta(days=1)
            continue
        ug_day = frame.unrealized_pnl if held else None
        adjustment = tract_adjustments.up_to(day) if tract_adjustments.moved_in(date_from, day) else None
        realized_sum = realized.up_to(day) if sale_days and sale_days[0] <= day else None
        income_sum: Decimal | None = None
        fees_sum: Decimal | None = None
        if flow_days and bisect.bisect_right(flow_days, day) > (0 if date_from is None else bisect.bisect_right(flow_days, date_from)):
            income_sum = income.at(day) - income.at(date_from)
            fees_sum = costs.at(day) - costs.at(date_from)
        # The Performance row's formula, the one home of it (contributions.position_period_pnl), at this day.
        pnl = position_period_pnl(
            held_at_start=held_at_start,
            held_at_end=held,
            unrealized_start=ug_start,
            unrealized_end=ug_day,
            transfer_adjustment=adjustment,
            realized=realized_sum,
            income=income_sum,
            fees=fees_sum,
        ).period_pnl
        unknown_boundary = (held_at_start and ug_start is None) or (held and ug_day is None)
        base: Decimal | None
        if start_unknown_base:
            base = None
        else:
            base = abs(start_value or _ZERO) + bought.up_to(day) + brought_in.up_to(day)
        percent = pnl / base if pnl is not None and base is not None and base != 0 else None
        points.append(
            SeriesPoint(
                date=day,
                quantity=frame.quantity if held else _ZERO,
                market_value=frame.market_value if held else _ZERO,
                cost_basis=(frame.cost_basis if frame.cost_complete else None) if held else _ZERO,
                pnl=pnl,
                base=base,
                pnl_percent=percent,
                valuation_source=frame.valuation_source if held else None,
                complete=not unknown_boundary,
            )
        )
        parts[day] = _Parts(brought_in=brought_in.up_to(day))
        day += timedelta(days=1)
    data = PositionSeriesData(key, first_date, last_date, held_at_start, held_at_end, closed_on, points, all(point.complete for point in points))
    return data, parts


@dataclass(frozen=True, slots=True)
class _Parts:
    """What of a base an internal transfer brought in: the asset-level sum takes it out, it is not new capital."""

    brought_in: Decimal


def _takes_part(transfer: InternalAssetTransfer, key: PositionKey) -> bool:
    """Whether ``key`` is the sender or the receiver of ``transfer``."""
    return transfer.asset_id == key[1] and key[0] in (transfer.sender_broker_id, transfer.receiver_broker_id)


def _arrival_base(transfer: InternalAssetTransfer, date_from: date_type | None) -> Decimal | None:
    """What a transfer brings into the receiver's base on arrival, by the rule the Performance row's base follows.

    When the period splits its tract (``counted_tract``) the units' pnl is measured from their value on arrival, so they enter
    the base at that value (``closed_position_base``'s ``moved_in``: the cost plus ``V - C``). Otherwise — in transit at the
    start, or the value unknown — the plain boundary values measure it from the cost, and so they enter at the cost moved. None
    when that is not known either: the cost basis lacks it too, and the pnl with it.
    """
    if counted_tract(transfer, date_from, transfer.arrival):
        return transfer.value_at_arrival
    return transfer.cost_moved


def acquisitions_from_average_costs(average_costs: Mapping[tuple[int, int], AverageCost], transfers: Sequence[InternalAssetTransfer]) -> dict[PositionKey, list[tuple[date_type, Decimal]]]:
    """What was bought, per ``(broker_id, asset_id)``: ``(day, cost in the report currency)`` for each acquisition step of the average cost.

    The arrival of an internal transfer is not a purchase here: it enters the receiver's base at its value on arrival
    (``build_position_series`` reads the transfers), so a TRANSFER step on a day an internal transfer arrives at that broker
    is left out. A split is not an acquisition (its step is a rescale). The costs are the engine's: at the owner's share, each
    converted at its own date, the known part.
    """
    arrivals = {(transfer.receiver_broker_id, transfer.asset_id, transfer.arrival) for transfer in transfers}
    bought: dict[PositionKey, list[tuple[date_type, Decimal]]] = {}
    for (asset_id, broker_id), average_cost in average_costs.items():
        for step in average_cost.steps:
            movement = step.movement
            if movement.kind is not CostMovementKind.ACQUISITION or step.cost_report_change == _ZERO:
                continue
            if movement.transaction_type == "TRANSFER" and (broker_id, asset_id, movement.date) in arrivals:
                continue
            bought.setdefault((broker_id, asset_id), []).append((movement.date, step.cost_report_change))
    return bought


def build_position_series(
    requests: Sequence[PositionRequest],
    *,
    date_from: date_type | None,
    date_to: date_type,
    frames: Mapping[PositionKey, Sequence[PositionFrame]],
    realized_sales: Sequence[RealizedSale],
    flow_steps: Mapping[PositionKey, Sequence[tuple[date_type, Decimal, Decimal]]],
    transfers: Sequence[InternalAssetTransfer],
    acquisitions: Mapping[PositionKey, Sequence[tuple[date_type, Decimal]]],
) -> list[PositionSeriesData]:
    """The series of each requested position, in the order asked.

    ``frames`` hold each position's frames in ascending order (``end`` inclusive). ``realized_sales`` are the period's sales,
    already selected by ``period.period_realized_sales`` (dated in ``(date_from, date_to]``, proceeds and cost known).
    ``flow_steps`` give a position's income and costs as running totals, ``(day, income so far, fees and taxes so far)``, as
    ``NativeCash.position_flow_steps(date_from, date_to)`` returns them: counted from ``date_from`` (excluded), so they start at
    0 after it. What the totals hold up to ``date_from`` is subtracted anyway, so steps that begin earlier are read right. ``acquisitions`` are what was bought, ``(day, cost)``, never an
    internal transfer's arrival (the transfers bring theirs in at their value on arrival).
    """
    out: list[PositionSeriesData] = []
    for request in requests:
        broker_id, asset_id = request
        keys = [(broker, asset_id) for broker in sorted({b for b, a in frames if a == asset_id})] if broker_id is None else [(broker_id, asset_id)]
        singles = []
        for key in keys:
            singles.append(
                _single(
                    key,
                    date_from=date_from,
                    date_to=date_to,
                    reader=_PositionReader(frames.get(key, ())),
                    sales=[sale for sale in realized_sales if (sale.broker_id, sale.asset_id) == key],
                    flow_steps=list(flow_steps.get(key, ())),
                    transfers=[t for t in transfers if t.asset_id == asset_id],
                    acquisitions=list(acquisitions.get(key, ())),
                )
            )
        out.append(singles[0][0] if broker_id is not None else _sum_over_brokers(request, [data for data, _ in singles], [parts for _, parts in singles]))
    return out


def _sum_over_brokers(request: PositionRequest, singles: list[PositionSeriesData], parts: list[dict[date_type, _Parts]]) -> PositionSeriesData:
    """An asset summed over the brokers that held it: each broker's point on each day, a closed one at its last."""
    held = [data for data in singles if data.points]
    if not held:
        return PositionSeriesData(request, None, None, False, False, None, [], True)
    first_date = min(data.first_date for data in held)
    last_date = max(data.last_date for data in held)
    at_end = any(data.held_at_end for data in held)
    by_day = [{point.date: point for point in data.points} for data in held]
    brought = [part for data, part in zip(singles, parts, strict=True) if data.points]
    points: list[SeriesPoint] = []
    day = first_date
    while day <= last_date:
        quantity = _ZERO
        market_value: Decimal | None = _ZERO
        cost_basis: Decimal | None = _ZERO
        pnls: list[Decimal] = []
        pnl_known = False
        base: Decimal | None = _ZERO
        complete = True
        source: str | None = None
        for data, index, part in zip(held, by_day, brought, strict=True):
            point = index.get(day)
            if point is None:
                if day < data.first_date:
                    continue
                point = data.points[-1]  # closed: the final pnl and base stay in the sum, the position is worth 0
                market_value_here, cost_here, quantity_here, source_here = _ZERO, _ZERO, _ZERO, None
                brought_in = part[data.last_date].brought_in
            else:
                market_value_here, cost_here, quantity_here, source_here = point.market_value, point.cost_basis, point.quantity, point.valuation_source
                brought_in = part[day].brought_in
            quantity += quantity_here
            market_value = None if market_value is None or market_value_here is None else market_value + market_value_here
            cost_basis = None if cost_basis is None or cost_here is None else cost_basis + cost_here
            if point.pnl is not None:
                pnls.append(point.pnl)
                pnl_known = True
            base = None if base is None or point.base is None else base + point.base - brought_in
            complete = complete and point.complete
            source = source or source_here
        pnl = sum(pnls, _ZERO) if pnl_known else None
        points.append(SeriesPoint(day, quantity, market_value, cost_basis, pnl, base, pnl / base if pnl is not None and base not in (None, _ZERO) else None, source, complete))
        day += timedelta(days=1)
    closed_on = None if at_end else max(data.closed_on for data in held if data.closed_on is not None)
    return PositionSeriesData(request, first_date, last_date, any(data.held_at_start for data in held), at_end, closed_on, points, all(point.complete for point in points))
