"""J5-1 (#48) — the daily series of a position: its P&L and its base, from the engine's frames of that position.

Module under test (does not exist yet; every case fails by absence until it does):
``backend/app/services/financial_math/portfolio/position_series.py``, ``build_position_series``. A pure function of plain
data, no session, no engine: the frames of each position (the engine's per-position state, one per stretch of days in
which it does not change), the realized sales, the cumulative income and costs, the internal transfers and the cost of
what was bought. Read through ``importlib`` in each case, so only the cases that use it fail and the file collects.

The rules (developer's decision of 18/10 and 23/10, plan 05 «Ondata 5»):

* a position's **P&L on day d** is the Periodo table's ``period_pnl`` of the period from ``date_from`` to d: the change of
  its unrealized result since ``date_from`` (the frame of d against the frame of ``date_from``, plus the tract an internal
  transfer gave it, ``transfer_tract_adjustments``) + the realized gain of its sales in ``(date_from, d]`` + its income -
  its fees and taxes over the same days. So the last point of a series is the table's row;
* its **base** is the size of the value at ``date_from`` + the cost of what is bought after it (+ what an internal
  transfer brings in, at its value on arrival): a sale never lowers it. ``pnl_percent`` is pnl / base, a fraction,
  unrounded; None when the base is 0 or unknown. «Base 100» is ``1 + pnl_percent`` (Q-J5-1, approved 23/10: 10 units at
  100 then 10 at 110, price 120 — pnl 300, base 2 100, 14.3 %);
* the series covers every **calendar day** from ``first_date`` to ``last_date`` and is given as STEPS (D-P4, cure B,
  contract MF-P4b §1.4): a point holds from its ``date`` to its ``through``, both included, and the steps are contiguous
  and maximal. Most cases below read the series the way a day-by-day reader would, through ``expand`` (every step repeated
  over its days), so what they pin is the figures of each calendar day; the last section pins the steps themselves.
  ``last_date`` is ``date_to`` while the position is held, else the day it went to 0 (that day's point has quantity 0,
  value 0, the final pnl); a position never held has no points;
* ``None`` is «not known», never 0: a day with no value (a missing price or rate) has ``market_value`` None and its pnl is
  the sum of the parts that are known, flagged ``complete = False``, as the Periodo row does;
* a request for ``(None, asset)`` is the asset summed over the brokers that held it: the transfers between them cancel
  (their tracts are opposite, their value on arrival is not new capital); a closed leg keeps its final pnl.

Everything is in the report currency, at the owner's share: the engine's frames are already scaled.
"""

from __future__ import annotations

import dataclasses
import importlib
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.services.financial_math.portfolio.models import InternalAssetTransfer, RealizedSale

D = Decimal
JAN = date(2024, 1, 1)


def day(number: int) -> date:
    """January ``number`` of 2024."""
    return JAN + timedelta(days=number - 1)


def _module():
    return importlib.import_module("backend.app.services.financial_math.portfolio.position_series")


@dataclass(frozen=True)
class Frame:
    """What the engine's per-position frame holds for these cases: the stretch ``start``..``end`` (inclusive) it covers and the position's state in it."""

    broker_id: int
    asset_id: int
    start: date
    end: date
    quantity: Decimal
    market_value: Decimal | None
    cost_basis: Decimal
    cost_complete: bool = True
    valuation_source: str = "MARKET_PRICE"

    @property
    def unrealized_pnl(self) -> Decimal | None:
        return self.market_value - self.cost_basis if self.market_value is not None and self.cost_complete else None


def frame(broker: int, asset: int, start: int, end: int, quantity: str, market_value: str | None, cost: str, **kwargs) -> Frame:
    return Frame(broker, asset, day(start), day(end), D(quantity), None if market_value is None else D(market_value), D(cost), **kwargs)


def sale(broker: int, asset: int, on: int, proceeds: str, cost: str, quantity: str = "1") -> RealizedSale:
    return RealizedSale(transaction_id=None, asset_id=asset, broker_id=broker, date=day(on), quantity=D(quantity), proceeds=D(proceeds), cost=D(cost), cost_complete=True)


def build(keys, *, date_from: int | None, date_to: int, frames=(), sales=(), flow_steps=None, transfers=(), acquisitions=None):
    """``build_position_series`` for ``keys`` (``(broker_id | None, asset_id)``), the frames given as a flat list."""
    by_key: dict[tuple[int, int], list[Frame]] = {}
    for item in frames:
        by_key.setdefault((item.broker_id, item.asset_id), []).append(item)
    return _module().build_position_series(
        list(keys),
        date_from=None if date_from is None else day(date_from),
        date_to=day(date_to),
        frames={key: sorted(items, key=lambda item: item.start) for key, items in by_key.items()},
        realized_sales=list(sales),
        flow_steps=flow_steps or {},
        transfers=list(transfers),
        acquisitions=acquisitions or {},
    )


def expand(points) -> list:
    """The daily series a step series stands for: every step repeated over its days, ``date..through``, one point per calendar day."""
    days = []
    for point in points:
        for offset in range((point.through - point.date).days + 1):
            current = point.date + timedelta(days=offset)
            days.append(dataclasses.replace(point, date=current, through=current))
    return days


def points_of(series) -> dict[date, object]:
    """The point of each calendar day of the series (the step that holds it, with ``date`` = ``through`` = that day)."""
    return {point.date: point for point in expand(series.points)}


FIELDS = ("quantity", "market_value", "cost_basis", "pnl", "base", "pnl_percent", "valuation_source", "complete")


def figures(point) -> tuple:
    """The figures of a point, a Decimal as its digits and exponent: ``Decimal('1.10')`` and ``Decimal('1.1')`` differ."""
    return tuple(value.as_tuple() if isinstance(value, Decimal) else value for value in (getattr(point, name) for name in FIELDS))


def starts(series) -> list[date]:
    return [point.date for point in series.points]


# =============================================================================
# A position held from the start to the end
# =============================================================================


class TestAPositionHeldThroughTheWindow:
    """Held on 1 Jan with 10 units worth 1 000 (cost 900, so unrealized 100); on 4 Jan the price lifts it to 1 100."""

    FRAMES = (frame(1, 10, 1, 3, "10", "1000", "900"), frame(1, 10, 4, 5, "10", "1100", "900"))

    def test_the_pnl_is_the_change_of_the_unrealized_result_and_the_base_the_start_value(self):
        [series] = build([(1, 10)], date_from=1, date_to=5, frames=self.FRAMES)

        points = points_of(series)
        assert [(p.date, p.pnl, p.base) for p in expand(series.points)] == [
            (day(1), D("0"), D("1000")),
            (day(2), D("0"), D("1000")),
            (day(3), D("0"), D("1000")),
            (day(4), D("100"), D("1000")),
            (day(5), D("100"), D("1000")),
        ]
        assert (points[day(1)].pnl_percent, points[day(4)].pnl_percent) == (D("0"), D("0.1"))
        assert (series.first_date, series.last_date, series.held_at_start, series.held_at_end, series.closed_on, series.complete) == (day(1), day(5), True, True, None, True)

    def test_every_calendar_day_is_covered_and_constant_while_the_frame_holds(self):
        # Was «one point per calendar day»: that no longer exists (D-P4), the series is steps. What stays is that every day from
        # first_date to last_date has its figures, and that they are the frame's while it holds.
        [series] = build([(1, 10)], date_from=1, date_to=5, frames=self.FRAMES)

        daily = expand(series.points)
        assert [p.date for p in daily] == [day(n) for n in range(1, 6)]
        assert {(p.quantity, p.market_value, p.cost_basis) for p in daily if p.date <= day(3)} == {(D("10"), D("1000"), D("900"))}
        assert {(p.quantity, p.market_value, p.cost_basis) for p in daily if p.date >= day(4)} == {(D("10"), D("1100"), D("900"))}
        # And the steps are the frames' two stretches, the day after the start (the period's second day) changing nothing.
        assert [(p.date, p.through) for p in series.points] == [(day(1), day(3)), (day(4), day(5))]

    def test_a_series_without_a_start_date_begins_with_the_first_frame(self):
        [series] = build([(1, 10)], date_from=None, date_to=5, frames=self.FRAMES[1:])

        assert (series.first_date, series.held_at_start) == (day(4), False)


# =============================================================================
# A position opened in the window, bought in two goes (the developer's example)
# =============================================================================


class TestAPositionBoughtInTwoGoes:
    """10 units at 100 on 3 Jan (cost 1 000); 10 more at 110 on 5 Jan (cost 1 100, price 110); the price goes to 120 on 6 Jan."""

    FRAMES = (
        frame(1, 10, 3, 4, "10", "1000", "1000"),
        frame(1, 10, 5, 5, "20", "2200", "2100"),
        frame(1, 10, 6, 10, "20", "2400", "2100"),
    )
    ACQUISITIONS = {(1, 10): [(day(3), D("1000")), (day(5), D("1100"))]}

    def test_the_base_grows_with_what_is_bought_and_the_percent_is_on_it(self):
        [series] = build([(1, 10)], date_from=1, date_to=10, frames=self.FRAMES, acquisitions=self.ACQUISITIONS)

        points = points_of(series)
        assert (series.first_date, series.held_at_start) == (day(3), False)
        assert (points[day(3)].pnl, points[day(3)].base, points[day(3)].pnl_percent) == (D("0"), D("1000"), D("0"))
        assert (points[day(5)].pnl, points[day(5)].base) == (D("100"), D("2100"))
        assert (points[day(6)].pnl, points[day(6)].base, points[day(6)].pnl_percent) == (D("300"), D("2100"), D("300") / D("2100"))

    def test_no_point_before_the_position_is_held(self):
        [series] = build([(1, 10)], date_from=1, date_to=10, frames=self.FRAMES, acquisitions=self.ACQUISITIONS)

        assert day(1) not in points_of(series) and day(2) not in points_of(series)


# =============================================================================
# Sold in two goes: the base does not fall, the series ends the day it is closed
# =============================================================================


class TestAPositionSoldDown:
    """Held on 1 Jan, 10 units worth 1 200 (cost 1 000); 4 sold on 5 Jan for 520 (cost 400); the 6 left sold on 8 Jan for 840 (cost 600)."""

    FRAMES = (
        frame(1, 10, 1, 4, "10", "1200", "1000"),
        frame(1, 10, 5, 7, "6", "780", "600"),
    )
    SALES = (sale(1, 10, 5, "520", "400", "4"), sale(1, 10, 8, "840", "600", "6"))

    def test_the_realized_gain_enters_when_the_sale_happens_and_the_base_stays(self):
        [series] = build([(1, 10)], date_from=1, date_to=10, frames=self.FRAMES, sales=self.SALES)

        points = points_of(series)
        assert (points[day(4)].pnl, points[day(5)].pnl, points[day(7)].pnl) == (D("0"), D("100"), D("100"))
        assert {p.base for p in expand(series.points)} == {D("1200")}

    def test_the_series_ends_the_day_the_position_goes_to_zero_with_its_final_pnl(self):
        [series] = build([(1, 10)], date_from=1, date_to=10, frames=self.FRAMES, sales=self.SALES)

        last = expand(series.points)[-1]
        assert (series.last_date, series.closed_on, series.held_at_end) == (day(8), day(8), False)
        assert (last.date, last.quantity, last.market_value, last.cost_basis, last.pnl, last.pnl_percent) == (day(8), D("0"), D("0"), D("0"), D("160"), D("160") / D("1200"))

    def test_the_final_pnl_is_the_gain_over_the_window_not_over_the_whole_trade(self):
        # The trade made 1 360 - 1 000 = 360 in all; 200 of it was already in the start value.
        [series] = build([(1, 10)], date_from=1, date_to=10, frames=self.FRAMES, sales=self.SALES)

        assert expand(series.points)[-1].pnl == D("360") - D("200")


# =============================================================================
# Income, fees and taxes
# =============================================================================


class TestIncomeAndCosts:
    """A position that stays at cost 1 000, value 1 000 for ten days. Income and costs are cumulative from the first movement of the ledger."""

    FRAMES = (frame(1, 10, 1, 10, "10", "1000", "1000"),)
    # (date, cumulative income, cumulative fees and taxes)
    STEPS = {(1, 10): [(day(1) - timedelta(days=17), D("5"), D("0")), (day(3), D("15"), D("2")), (day(6), D("25"), D("2"))]}

    def test_only_what_comes_after_the_start_counts(self):
        [series] = build([(1, 10)], date_from=1, date_to=10, frames=self.FRAMES, flow_steps=self.STEPS)

        points = points_of(series)
        assert [points[day(n)].pnl for n in (1, 2, 3, 5, 6, 10)] == [D("0"), D("0"), D("8"), D("8"), D("18"), D("18")]

    def test_a_position_with_no_income_or_costs_is_unaffected(self):
        [series] = build([(1, 10)], date_from=1, date_to=10, frames=self.FRAMES, flow_steps={})

        assert {p.pnl for p in expand(series.points)} == {D("0")}


# =============================================================================
# Split: more units, the same worth
# =============================================================================


def test_a_split_changes_the_quantity_and_not_the_pnl_or_the_base():
    frames = (frame(1, 10, 1, 3, "10", "1000", "800"), frame(1, 10, 4, 6, "20", "1000", "800"))

    [series] = build([(1, 10)], date_from=1, date_to=6, frames=frames)

    points = points_of(series)
    assert (points[day(3)].quantity, points[day(4)].quantity) == (D("10"), D("20"))
    assert {p.pnl for p in expand(series.points)} == {D("0")}
    assert {p.base for p in expand(series.points)} == {D("1000")}


# =============================================================================
# What is not known
# =============================================================================


class TestAValueThatIsNotKnown:
    def test_a_day_without_a_market_value_has_no_value_and_a_pnl_of_the_parts_that_are_known(self):
        # The price is missing on 3 and 4 Jan; a sale on 4 Jan for a gain of 30 is known. The Periodo row adds the parts it has
        # (unrealized change, realized, income, costs) and has no pnl at all when it has none.
        frames = (frame(1, 10, 1, 2, "10", "1000", "900"), frame(1, 10, 3, 4, "10", None, "900"), frame(1, 10, 5, 6, "10", "1050", "900"))

        [series] = build([(1, 10)], date_from=1, date_to=6, frames=frames, sales=[sale(1, 10, 4, "130", "100")])

        points = points_of(series)
        assert (points[day(3)].market_value, points[day(3)].pnl) == (None, None)
        assert (points[day(4)].market_value, points[day(4)].pnl) == (None, D("30"))
        # Back to a known value: the unrealized change is 150 - 100 = 50, plus the 30 realized.
        assert (points[day(5)].market_value, points[day(5)].pnl) == (D("1050"), D("80"))
        assert (points[day(3)].complete, points[day(5)].complete, series.complete) == (False, True, False)

    def test_a_start_value_that_is_not_known_leaves_the_base_and_the_percent_unknown(self):
        frames = (frame(1, 10, 1, 4, "10", None, "900"),)

        [series] = build([(1, 10)], date_from=1, date_to=4, frames=frames)

        assert {(p.base, p.pnl_percent) for p in expand(series.points)} == {(None, None)}

    def test_a_base_of_zero_has_no_percent(self):
        frames = (frame(1, 10, 3, 4, "10", "1000", "1000"),)

        [series] = build([(1, 10)], date_from=1, date_to=4, frames=frames, acquisitions={(1, 10): [(day(3), D("0"))]})

        assert {(p.base, p.pnl_percent) for p in expand(series.points)} == {(D("0"), None)}


# =============================================================================
# A position moved between two brokers of the scope
# =============================================================================


class TestAnInternalTransfer:
    """10 units at broker 1 (cost 1 000, worth 1 100 until 4 Jan); they leave on 4 Jan and arrive at broker 2 on 5 Jan, worth 1 150 (cost moved 1 000);
    at broker 2 they are worth 1 150 on 5 Jan and 1 200 from 6 Jan."""

    FRAMES = (
        frame(1, 10, 1, 4, "10", "1100", "1000"),
        frame(2, 10, 5, 5, "10", "1150", "1000"),
        frame(2, 10, 6, 8, "10", "1200", "1000"),
    )
    TRANSFERS = (InternalAssetTransfer(departure=day(4), arrival=day(5), asset_id=10, sender_broker_id=1, receiver_broker_id=2, value_at_arrival=D("1150"), cost_moved=D("1000")),)

    def test_each_broker_answers_for_its_own_tract(self):
        sender, receiver = build([(1, 10), (2, 10)], date_from=1, date_to=8, frames=self.FRAMES, transfers=self.TRANSFERS)

        # Broker 1 earned 150 on the units (1 150 - 1 000), 100 of it before the window: 50. It closes on the day they arrive.
        assert (sender.last_date, sender.closed_on) == (day(5), day(5))
        assert (points_of(sender)[day(4)].pnl, points_of(sender)[day(5)].pnl) == (D("0"), D("50"))
        # Broker 2 has them from their value on arrival: 0 then, 50 when they gain 50 more.
        assert (receiver.first_date, receiver.held_at_start) == (day(5), False)
        assert (points_of(receiver)[day(5)].pnl, points_of(receiver)[day(6)].pnl) == (D("0"), D("50"))

    def test_the_receivers_base_is_what_arrived_at_its_value_on_arrival(self):
        _, receiver = build([(1, 10), (2, 10)], date_from=1, date_to=8, frames=self.FRAMES, transfers=self.TRANSFERS)

        assert {p.base for p in expand(receiver.points)} == {D("1150")}
        assert points_of(receiver)[day(6)].pnl_percent == D("50") / D("1150")

    def test_the_asset_summed_over_the_brokers_has_no_jump_and_no_double_base(self):
        [asset] = build([(None, 10)], date_from=1, date_to=8, frames=self.FRAMES, transfers=self.TRANSFERS)

        points = points_of(asset)
        assert (asset.first_date, asset.last_date, asset.closed_on) == (day(1), day(8), None)
        # The same asset held at one broker would have gone 1 100 -> 1 150 -> 1 200: pnl 0, 50, 100.
        assert (points[day(4)].pnl, points[day(5)].pnl, points[day(6)].pnl, points[day(8)].pnl) == (D("0"), D("50"), D("100"), D("100"))
        assert {p.base for p in expand(asset.points)} == {D("1100")}
        # A closed leg keeps its final pnl in the sum: broker 1's 50 stays while broker 2's rises from 0 to 50.
        assert points[day(6)].market_value == D("1200")

    def test_units_in_transit_are_the_senders_until_they_arrive(self):
        # They leave on 4 Jan (broker 1's last frame is 3 Jan) and arrive on 6 Jan: the series goes on to the arrival, holding the pnl
        # of the last day held while they are on their way, and the tract settles it on arrival.
        frames = (frame(1, 10, 1, 3, "10", "1100", "1000"), frame(2, 10, 6, 6, "10", "1150", "1000"), frame(2, 10, 7, 8, "10", "1200", "1000"))
        transfers = (InternalAssetTransfer(departure=day(4), arrival=day(6), asset_id=10, sender_broker_id=1, receiver_broker_id=2, value_at_arrival=D("1150"), cost_moved=D("1000")),)

        sender, receiver = build([(1, 10), (2, 10)], date_from=1, date_to=8, frames=frames, transfers=transfers)

        assert (sender.closed_on, sender.last_date, sender.held_at_end) == (day(4), day(6), False)
        points = points_of(sender)
        assert [(points[day(n)].quantity, points[day(n)].pnl) for n in (3, 4, 5)] == [(D("10"), D("0")), (D("0"), D("0")), (D("0"), D("0"))]
        assert points[day(6)].pnl == D("50")
        assert (receiver.first_date, points_of(receiver)[day(6)].pnl) == (day(6), D("0"))

    def test_a_transfer_whose_value_on_arrival_is_unknown_keeps_the_plain_boundary_values(self):
        unknown = (InternalAssetTransfer(departure=day(4), arrival=day(5), asset_id=10, sender_broker_id=1, receiver_broker_id=2, value_at_arrival=None, cost_moved=D("1000")),)

        sender, receiver = build([(1, 10), (2, 10)], date_from=1, date_to=8, frames=self.FRAMES, transfers=unknown)

        # No tract is split: broker 1 loses its whole unrealized (100) on leaving, broker 2 carries 150 and then 200.
        assert (points_of(sender)[day(5)].pnl, points_of(receiver)[day(6)].pnl) == (D("-100"), D("200"))
        # And the units enter the receiver's base at the cost moved, the same plain boundary values its pnl is measured from.
        assert {p.base for p in expand(receiver.points)} == {D("1000")}

    def test_a_transfer_in_transit_at_the_start_enters_the_receivers_base_at_its_cost(self):
        """J5-3 (MF's point 3). Left on 2 Jan, before the window (it starts on 3 Jan), arriving on 5 Jan worth 1 150 (cost moved 1 000): the
        period's rows split no tract (it departs on or before the start), so the receiver's pnl is its plain boundary value, measured from
        the cost, 150 on arrival and 200 from 6 Jan. The base is the same cost, as the table's end cost is: not the value on arrival, which
        would put a part of the gain in the base that the pnl counts."""
        frames = (frame(2, 10, 5, 5, "10", "1150", "1000"), frame(2, 10, 6, 8, "10", "1200", "1000"))
        in_transit = (InternalAssetTransfer(departure=day(2), arrival=day(5), asset_id=10, sender_broker_id=1, receiver_broker_id=2, value_at_arrival=D("1150"), cost_moved=D("1000")),)

        [receiver] = build([(2, 10)], date_from=3, date_to=8, frames=frames, transfers=in_transit)

        points = points_of(receiver)
        assert (points[day(5)].pnl, points[day(6)].pnl) == (D("150"), D("200"))
        assert {p.base for p in expand(receiver.points)} == {D("1000")}
        assert points[day(6)].pnl_percent == D("200") / D("1000")


# =============================================================================
# What is asked for, and what is not
# =============================================================================


class TestTheSelection:
    FRAMES = (frame(1, 10, 1, 4, "10", "1000", "900"), frame(1, 11, 1, 4, "5", "500", "450"), frame(2, 10, 1, 4, "3", "300", "270"))

    def test_only_the_asked_positions_come_back_in_the_order_asked(self):
        series = build([(1, 11), (1, 10)], date_from=1, date_to=4, frames=self.FRAMES)

        assert [s.key for s in series] == [(1, 11), (1, 10)]

    def test_a_position_never_held_comes_back_with_no_points(self):
        [series] = build([(1, 99)], date_from=1, date_to=4, frames=self.FRAMES)

        assert (series.points, series.first_date, series.last_date, series.held_at_start, series.held_at_end, series.closed_on) == ([], None, None, False, False, None)

    def test_an_asset_with_no_broker_sums_the_brokers_that_held_it(self):
        [asset] = build([(None, 10)], date_from=1, date_to=4, frames=self.FRAMES)

        point = points_of(asset)[day(2)]
        assert (point.quantity, point.market_value, point.cost_basis, point.base) == (D("13"), D("1300"), D("1170"), D("1300"))

    def test_a_position_reopened_after_a_close_continues_with_quantity_zero_in_between(self):
        frames = (frame(1, 10, 1, 2, "10", "1000", "1000"), frame(1, 10, 5, 6, "4", "400", "400"))

        [series] = build([(1, 10)], date_from=1, date_to=6, frames=frames, sales=[sale(1, 10, 3, "1000", "1000", "10")])

        points = points_of(series)
        assert (points[day(3)].quantity, points[day(4)].quantity, points[day(5)].quantity) == (D("0"), D("0"), D("4"))
        assert (series.first_date, series.last_date, series.held_at_end, series.closed_on) == (day(1), day(6), True, None)


# =============================================================================
# The Periodo table is the same number
# =============================================================================


def test_every_pnl_of_a_series_is_the_periodo_rows_function_at_that_day(monkeypatch):
    """The row and the series read ONE function, ``contributions.position_period_pnl`` (lifted by MF out of
    ``get_positions_contribution``): the series calls it once for each of its points, with the unrealized results of the start and
    of that day, and what it answers is the point's pnl."""
    module = _module()
    asked: list[dict] = []
    real = module.position_period_pnl

    def spy(**kwargs):
        asked.append(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(module, "position_period_pnl", spy)

    [series] = build([(1, 10)], date_from=1, date_to=5, frames=TestAPositionHeldThroughTheWindow.FRAMES)

    # Was «once for each of its points», one per day. Now it is once for each day the figures can change on (1 Jan the start, 2 Jan
    # the day after it, 4 Jan the second frame, 5 Jan the last day: four lookups, not five), and never for the days between.
    assert len(asked) == 4
    assert {(call["unrealized_start"], call["held_at_start"]) for call in asked} == {(D("100"), True)}
    assert [call["unrealized_end"] for call in asked] == [D("100"), D("100"), D("200"), D("200")]
    assert [point.pnl for point in expand(series.points)] == [D("0"), D("0"), D("0"), D("100"), D("100")]


@pytest.mark.parametrize("name", ["build_position_series"])
def test_the_module_exposes_its_entry_point(name):
    assert callable(getattr(_module(), name))


# =============================================================================
# The series are STEPS (D-P4, cure B; contract MF-P4b §0, §1.1, §1.4, §8)
# =============================================================================
#
# A point holds from ``date`` to ``through``, both included. Everything above reads the steps through ``expand``; what follows
# pins the steps themselves: contiguous from ``first_date`` to ``last_date``, maximal, one starting on every day the figures
# can change, and cheap. The oracle of the figures is never the function itself: it is the way of the old daily series, the
# series of the period ``date_from``..``d`` read at its last day (the Periodo row's definition), or a sum made by hand from the
# expanded singles.

CONST = (frame(1, 10, 1, 10, "10", "1000", "900"),)


def span(first: int, last: int) -> tuple[date, date]:
    return day(first), day(last)


def spans(series) -> list[tuple[date, date]]:
    return [(point.date, point.through) for point in series.points]


#: Units of broker 1 held 1..5 Jan (the frame changes on 3 Jan, so 5 Jan, the last day held, is not the start of a step); they
#: leave on 6 Jan and arrive at broker 2 on 9 Jan: 6, 7 and 8 Jan are in transit.
TRANSIT_FRAMES = (
    frame(1, 10, 1, 2, "10", "1100", "1000"),
    frame(1, 10, 3, 5, "10", "1200", "1000"),
    frame(2, 10, 9, 10, "10", "1250", "1000"),
)
TRANSIT_TRANSFERS = (InternalAssetTransfer(departure=day(6), arrival=day(9), asset_id=10, sender_broker_id=1, receiver_broker_id=2, value_at_arrival=D("1250"), cost_moved=D("1000")),)


def _scenarios() -> dict[str, tuple]:
    """Books whose series are checked by the properties of the steps: ``name -> (the series of the requests, the requests)``."""
    both = [(1, 10), (2, 10), (None, 10)]
    transfer = TestAnInternalTransfer
    held = TestAPositionHeldThroughTheWindow
    goes = TestAPositionBoughtInTwoGoes
    sold = TestAPositionSoldDown
    income = TestIncomeAndCosts
    return {
        "held": build([(1, 10)], date_from=1, date_to=5, frames=held.FRAMES),
        "two goes": build([(1, 10)], date_from=1, date_to=10, frames=goes.FRAMES, acquisitions=goes.ACQUISITIONS),
        "sold down": build([(1, 10)], date_from=1, date_to=10, frames=sold.FRAMES, sales=sold.SALES),
        "income and costs": build([(1, 10)], date_from=1, date_to=10, frames=income.FRAMES, flow_steps=income.STEPS),
        "transfer": build(both, date_from=1, date_to=8, frames=transfer.FRAMES, transfers=transfer.TRANSFERS),
        "transit": build(both, date_from=1, date_to=10, frames=TRANSIT_FRAMES, transfers=TRANSIT_TRANSFERS, flow_steps={(1, 10): [(day(7), D("0"), D("4"))]}),
        "unknown value": build([(1, 10)], date_from=1, date_to=6, frames=(frame(1, 10, 1, 2, "10", "1000", "900"), frame(1, 10, 3, 4, "10", None, "900"), frame(1, 10, 5, 6, "10", "1050", "900")), sales=[sale(1, 10, 4, "130", "100")]),
        "reopened": build([(1, 10)], date_from=1, date_to=6, frames=(frame(1, 10, 1, 2, "10", "1000", "1000"), frame(1, 10, 5, 6, "4", "400", "400")), sales=[sale(1, 10, 3, "1000", "1000", "10")]),
        "no start date": build([(1, 10)], date_from=None, date_to=5, frames=held.FRAMES[1:]),
    }


@pytest.fixture(scope="module")
def scenarios() -> dict[str, tuple]:
    return _scenarios()


def _all_series(scenarios):
    return [(name, series) for name, group in scenarios.items() for series in group if series.points]


class TestTheStepsAreContiguousAndMaximal:
    def test_the_steps_run_from_first_date_to_last_date_without_a_gap_or_an_overlap(self, scenarios):
        checked = _all_series(scenarios)
        assert {name for name, _ in checked} == set(scenarios)  # every book gave at least one series with points
        for name, series in checked:
            points = series.points
            assert points[0].date == series.first_date, name
            assert points[-1].through == series.last_date, name
            for step in points:
                assert step.date <= step.through, (name, step.date, step.through)
            for before, after in zip(points, points[1:], strict=False):
                assert after.date == before.through + timedelta(days=1), (name, before.through, after.date)

    def test_two_consecutive_steps_never_carry_the_same_figures(self, scenarios):
        for name, series in _all_series(scenarios):
            for before, after in zip(series.points, series.points[1:], strict=False):
                assert figures(before) != figures(after), (name, series.key, before.date, after.date)

    def test_two_frames_with_the_same_figures_are_one_step(self):
        frames = (frame(1, 10, 1, 3, "10", "1000", "900"), frame(1, 10, 4, 6, "10", "1000", "900"))

        [series] = build([(1, 10)], date_from=1, date_to=6, frames=frames)

        assert spans(series) == [span(1, 6)]

    def test_figures_that_differ_only_in_the_exponent_are_two_steps(self):
        # 1000.0 == 1000 as numbers, and a Decimal keeps its exponent: the series says «1000.0» from 4 Jan and «1000» before, as the
        # daily series did, so they are not one step. (pnl 100.0 against 100, 0.0 against 0.)
        frames = (frame(1, 10, 1, 3, "10", "1000", "900"), frame(1, 10, 4, 6, "10", "1000.0", "900"))

        [series] = build([(1, 10)], date_from=1, date_to=6, frames=frames)

        assert spans(series) == [span(1, 3), span(4, 6)]
        before, after = series.points
        assert before.market_value == after.market_value and figures(before) != figures(after)
        assert (str(before.market_value), str(after.market_value)) == ("1000", "1000.0")

    def test_the_complete_flag_of_a_series_is_all_of_its_days_complete(self, scenarios):
        flags = {}
        for name, series in _all_series(scenarios):
            expected = all(point.complete for point in expand(series.points))
            assert series.complete is expected, (name, series.key)
            flags[name] = flags.get(name, set()) | {series.complete}
        # Not vacuous: some books are complete and one is not.
        assert flags["unknown value"] == {False}
        assert flags["held"] == {True}

    def test_a_summed_asset_with_one_incomplete_broker_is_incomplete_on_those_days_only(self):
        frames = (frame(1, 10, 1, 4, "10", "1000", "900"), frame(2, 10, 1, 2, "5", "500", "450"), frame(2, 10, 3, 4, "5", None, "450"))

        broker_1, broker_2, asset = build([(1, 10), (2, 10), (None, 10)], date_from=1, date_to=4, frames=frames)

        assert (broker_1.complete, broker_2.complete, asset.complete) == (True, False, False)
        assert [point.complete for point in expand(asset.points)] == [True, True, False, False]


# -----------------------------------------------------------------------------
# A step starts on every day the figures can change on
# -----------------------------------------------------------------------------


class TestAStepStartsOnEveryDayTheFiguresCanChange:
    """Each case is built so that nothing else happens on the day: the frames are the same on both sides of an event (``CONST``), so
    that a frame boundary cannot hide a missing one. A step exists only where the figures differ (maximal), so each case also
    checks that they do."""

    def test_a_frame_starting(self):
        frames = (frame(1, 10, 1, 3, "10", "1000", "900"), frame(1, 10, 4, 6, "10", "1100", "900"))

        [series] = build([(1, 10)], date_from=1, date_to=6, frames=frames)

        assert starts(series) == [day(1), day(4)]
        assert [p.market_value for p in expand(series.points)] == [D("1000")] * 3 + [D("1100")] * 3

    def test_the_day_after_a_frame_ends_with_nothing_starting_there(self):
        # Held 1..3 Jan, no frame on 4 and 5 Jan, the same frame again from 6 Jan: the stretch 4..5 is a step of its own (no units,
        # no value), whose first day is the end of the frame + 1. Without it the position would be held through 5 Jan.
        frames = (frame(1, 10, 1, 3, "10", "1000", "900"), frame(1, 10, 6, 8, "10", "1000", "900"))

        [series] = build([(1, 10)], date_from=1, date_to=8, frames=frames)

        assert starts(series) == [day(1), day(4), day(6)]
        assert [p.quantity for p in expand(series.points)] == [D("10")] * 3 + [D("0")] * 2 + [D("10")] * 3
        assert [(p.market_value, p.cost_basis) for p in expand(series.points) if day(4) <= p.date <= day(5)] == [(D("0"), D("0"))] * 2

    def test_the_day_a_position_closes(self):
        # The last frame ends on 3 Jan and the window goes to 8 Jan: the series ends on 4 Jan, the day it is 0, in a step of its own.
        [series] = build([(1, 10)], date_from=1, date_to=8, frames=(frame(1, 10, 1, 3, "10", "1000", "900"),))

        assert (series.last_date, series.closed_on) == (day(4), day(4))
        assert spans(series) == [span(1, 3), span(4, 4)]
        assert (series.points[-1].quantity, series.points[-1].market_value) == (D("0"), D("0"))

    def test_a_dust_frame_is_a_stretch_of_no_units(self):
        # 0.000001 units are under the dust threshold: the point is 0 in quantity and value, and 4 Jan (the dust frame's start) and
        # 7 Jan (the end of its stretch + 1, the next frame's start) are the boundaries.
        frames = (frame(1, 10, 1, 3, "10", "1000", "900"), frame(1, 10, 4, 6, "0.000001", "0.01", "0.009"), frame(1, 10, 7, 9, "10", "1000", "900"))

        [series] = build([(1, 10)], date_from=1, date_to=9, frames=frames)

        assert starts(series) == [day(1), day(4), day(7)]
        dust_days = [p for p in expand(series.points) if day(4) <= p.date <= day(6)]
        assert [(p.quantity, p.market_value, p.cost_basis, p.valuation_source) for p in dust_days] == [(D("0"), D("0"), D("0"), None)] * 3

    def test_a_sale(self):
        [series] = build([(1, 10)], date_from=1, date_to=10, frames=CONST, sales=[sale(1, 10, 5, "130", "100")])

        assert starts(series) == [day(1), day(5)]
        assert [p.pnl for p in expand(series.points)] == [D("0")] * 4 + [D("30")] * 6
        assert {p.base for p in expand(series.points)} == {D("1000")}

    def test_an_income(self):
        steps = {(1, 10): [(day(4), D("12"), D("0"))]}

        [series] = build([(1, 10)], date_from=1, date_to=10, frames=CONST, flow_steps=steps)

        assert starts(series) == [day(1), day(4)]
        assert [p.pnl for p in expand(series.points)] == [D("0")] * 3 + [D("12")] * 7

    def test_a_cost(self):
        steps = {(1, 10): [(day(6), D("0"), D("5"))]}

        [series] = build([(1, 10)], date_from=1, date_to=10, frames=CONST, flow_steps=steps)

        assert starts(series) == [day(1), day(6)]
        assert [p.pnl for p in expand(series.points)] == [D("0")] * 5 + [D("-5")] * 5

    def test_an_acquisition(self):
        # What is bought raises the base and leaves the pnl: only the base (and with it nothing of the percent, 0 either way) moves.
        [series] = build([(1, 10)], date_from=1, date_to=10, frames=CONST, acquisitions={(1, 10): [(day(5), D("200"))]})

        assert starts(series) == [day(1), day(5)]
        assert [p.base for p in expand(series.points)] == [D("1000")] * 4 + [D("1200")] * 6
        assert {p.pnl for p in expand(series.points)} == {D("0")}

    def test_the_arrival_of_a_transfer(self):
        # Broker 2 holds the same frame all along; 10 units leave broker 1 on 3 Jan and arrive on 5 Jan worth 1 150, cost moved 1 000.
        # The tract (-150) and what the units bring into the base (1 150) enter on 5 Jan; the departure, 3 Jan, is the sender's.
        receiver_frames = (frame(2, 10, 1, 10, "10", "1150", "1000"),)
        arrival = (InternalAssetTransfer(departure=day(3), arrival=day(5), asset_id=10, sender_broker_id=1, receiver_broker_id=2, value_at_arrival=D("1150"), cost_moved=D("1000")),)

        [series] = build([(2, 10)], date_from=1, date_to=10, frames=receiver_frames, transfers=arrival)

        assert starts(series) == [day(1), day(5)]
        assert [(p.pnl, p.base) for p in expand(series.points) if p.date in (day(4), day(5))] == [(D("0"), D("1150")), (D("-150"), D("2300"))]

    def test_the_days_in_transit(self):
        [sender] = build([(1, 10)], date_from=1, date_to=10, frames=TRANSIT_FRAMES, transfers=TRANSIT_TRANSFERS)

        # Held 1..2 and 3..5 Jan; in transit 6..8 Jan (the first day after the last held is a boundary); the arrival, 9 Jan, ends it.
        assert spans(sender) == [span(1, 2), span(3, 5), span(6, 8), span(9, 9)]
        assert (sender.closed_on, sender.last_date) == (day(6), day(9))

    def test_the_period_start_when_held_there(self):
        [series] = build([(1, 10)], date_from=3, date_to=10, frames=CONST)

        assert (series.first_date, spans(series)) == (day(3), [span(3, 10)])

    def test_the_day_after_the_period_start_when_the_position_is_not_held_before(self):
        # Not held on 1 Jan, held from 2 Jan: the series starts the day after the period's start (date_from + 1).
        [series] = build([(1, 10)], date_from=1, date_to=10, frames=(frame(1, 10, 2, 10, "10", "1000", "900"),))

        assert (series.first_date, series.held_at_start, spans(series)) == (day(2), False, [span(2, 10)])


class TestTheDaysInTransit:
    @pytest.mark.parametrize("last_day_value", ["1200", None], ids=["value known", "value unknown"])
    def test_they_are_one_step_with_the_pnl_base_and_percent_of_the_last_day_held(self, last_day_value):
        # The last day held is 5 Jan, in the middle of the step 3..5: it is not the start of a step, so the figures of the days in
        # transit are not those of «the previous point of the list» but of the day 5. (That reading is the same number today — no
        # figure changes between two change days — so replacing it cannot turn this red; what turns it red is any reading that
        # takes the figures of the day itself, or of the first step.) The cost of 7 Jan, a flow day inside the transit, is not theirs.
        frames = (frame(1, 10, 1, 2, "10", "1100", "1000"), frame(1, 10, 3, 5, "10", last_day_value, "1000"), TRANSIT_FRAMES[2])
        steps = {(1, 10): [(day(7), D("0"), D("4"))]}

        [sender] = build([(1, 10)], date_from=1, date_to=10, frames=frames, transfers=TRANSIT_TRANSFERS, flow_steps=steps)

        daily = points_of(sender)
        assert day(5) not in starts(sender)  # not the start of a step: the figures come from the lookup of that day
        last_held = daily[day(5)]
        assert last_held.quantity == D("10")
        if last_day_value is None:
            assert (last_held.pnl, last_held.complete) == (None, False)  # not vacuous: the unknown carries over too
        else:
            assert (last_held.pnl, last_held.base) == (D("100"), D("1100"))
        in_transit = [daily[day(n)] for n in (6, 7, 8)]
        for point in in_transit:
            assert (point.quantity, point.market_value, point.cost_basis, point.valuation_source) == (D("0"), D("0"), D("0"), None)
            assert (point.pnl, point.base, point.pnl_percent, point.complete) == (last_held.pnl, last_held.base, last_held.pnl_percent, last_held.complete)
        assert span(6, 8) in spans(sender)  # one step, the flow day inside it changes nothing
        # The arrival settles it: the tract (1 250 - 1 000) is added to the change since the start and the cost of 7 Jan is counted.
        if last_day_value is not None:
            assert daily[day(9)].pnl == D("-100") + D("250") - D("4")


# -----------------------------------------------------------------------------
# An asset summed over its brokers
# -----------------------------------------------------------------------------


def _summed_oracle(singles, transfers, date_from: int | None, first: date, last: date) -> dict[date, tuple]:
    """The asset's figures of each day, made by hand from the EXPANDED singles: each broker's day (a closed one at its last point,
    zero units and value), their sum, and what the transfers brought into a receiver's base taken out (it is not new capital)."""
    start = None if date_from is None else day(date_from)
    held = [single for single in singles if single.points]
    daily = [points_of(single) for single in held]
    out: dict[date, tuple] = {}
    current = first
    while current <= last:
        quantity, market_value, cost_basis, base = D("0"), D("0"), D("0"), D("0")
        pnls: list[Decimal] = []
        complete, source = True, None
        for single, by_day in zip(held, daily, strict=True):
            if current < single.first_date:
                continue
            point = by_day.get(current)
            closed = point is None
            if closed:
                point = by_day[single.last_date]  # the last point: the position is worth 0, its final pnl and base stay
            reach = min(current, single.last_date)
            brought = D("0")
            for t in transfers:
                if (t.receiver_broker_id, t.asset_id) != single.key or start is None or t.arrival <= start or t.arrival > reach:
                    continue
                counted = t.departure > start and t.value_at_arrival is not None and t.cost_moved is not None
                amount = t.value_at_arrival if counted else t.cost_moved
                if amount is not None:
                    brought += amount
            quantity_here, value_here, cost_here = (D("0"), D("0"), D("0")) if closed else (point.quantity, point.market_value, point.cost_basis)
            quantity += quantity_here
            market_value = None if market_value is None or value_here is None else market_value + value_here
            cost_basis = None if cost_basis is None or cost_here is None else cost_basis + cost_here
            if point.pnl is not None:
                pnls.append(point.pnl)
            base = None if base is None or point.base is None else base + point.base - brought
            complete = complete and point.complete
            source = source or (None if closed else point.valuation_source)
        pnl = sum(pnls, D("0")) if pnls else None
        percent = pnl / base if pnl is not None and base not in (None, D("0")) else None
        out[current] = (
            quantity.as_tuple(),
            market_value if market_value is None else market_value.as_tuple(),
            cost_basis if cost_basis is None else cost_basis.as_tuple(),
            pnl if pnl is None else pnl.as_tuple(),
            base if base is None else base.as_tuple(),
            percent if percent is None else percent.as_tuple(),
            source,
            complete,
        )
        current += timedelta(days=1)
    return out


class TestAnAssetSummedOverItsBrokers:
    #: Broker 1 holds the asset 1..4 Jan and sells it all on 5 Jan; broker 2 holds 5 units from 3 Jan, and its frame of 4..10 Jan is
    #: one long stretch, in the middle of which broker 1 closes.
    CLOSING_FRAMES = (
        frame(1, 10, 1, 2, "10", "1000", "900"),
        frame(1, 10, 3, 4, "10", "1100", "900"),
        frame(2, 10, 3, 3, "5", "500", "450"),
        frame(2, 10, 4, 10, "5", "600", "450"),
    )
    CLOSING_SALES = (sale(1, 10, 5, "1150", "900", "10"),)

    BOOKS = {
        "a broker closes inside a stretch of the other": {"date_to": 10, "frames": CLOSING_FRAMES, "sales": CLOSING_SALES, "transfers": ()},
        "a transfer between them": {"date_to": 8, "frames": TestAnInternalTransfer.FRAMES, "sales": (), "transfers": TestAnInternalTransfer.TRANSFERS},
        "a transfer in transit": {"date_to": 10, "frames": TRANSIT_FRAMES, "sales": (), "transfers": TRANSIT_TRANSFERS},
        "a transfer in transit, then a close": {"date_to": 12, "frames": (*TRANSIT_FRAMES[:2], frame(2, 10, 9, 10, "10", "1250", "1000")), "sales": [sale(2, 10, 11, "1300", "1000", "10")], "transfers": TRANSIT_TRANSFERS},
    }

    @pytest.mark.parametrize("name", list(BOOKS))
    def test_the_sum_equals_the_sum_of_the_expanded_singles_minus_what_the_transfers_brought_in(self, name):
        book = self.BOOKS[name]
        broker_1, broker_2, asset = build([(1, 10), (2, 10), (None, 10)], date_from=1, **book)

        expected = _summed_oracle([broker_1, broker_2], book["transfers"], 1, asset.first_date, asset.last_date)
        actual = {point.date: figures(point) for point in expand(asset.points)}

        assert list(actual) == list(expected)
        assert actual == expected

    @pytest.mark.parametrize("name", list(BOOKS))
    def test_the_steps_are_on_the_union_of_the_brokers_change_days(self, name):
        book = self.BOOKS[name]
        broker_1, broker_2, asset = build([(1, 10), (2, 10), (None, 10)], date_from=1, **book)

        union = {point.date for single in (broker_1, broker_2) for point in single.points} | {asset.first_date, asset.last_date}
        assert set(starts(asset)) <= union
        assert asset.points[0].date == min(single.first_date for single in (broker_1, broker_2) if single.points)

    def test_a_broker_that_closes_in_the_middle_of_a_step_of_the_other_contributes_its_last_step(self):
        book = self.BOOKS["a broker closes inside a stretch of the other"]
        broker_1, broker_2, asset = build([(1, 10), (2, 10), (None, 10)], date_from=1, **book)

        # Broker 2 has one step 4..10 Jan; broker 1 closes on 5 Jan (last_date), inside it.
        assert broker_1.last_date == day(5) and span(4, 10) in spans(broker_2)
        assert day(5) in starts(asset)  # the closing is a boundary of the sum, though broker 2 does not change there
        final = broker_1.points[-1]
        daily = points_of(asset)
        for number in (5, 6, 8, 10):  # from the closing on, broker 1 is its last step: no units, no value, its final pnl and base
            other = points_of(broker_2)[day(number)]
            point = daily[day(number)]
            assert (point.quantity, point.market_value, point.cost_basis) == (other.quantity, other.market_value, other.cost_basis)
            assert point.pnl == final.pnl + other.pnl
            assert point.base == final.base + other.base
        # The days after the closing are one step of the sum: nothing changes there.
        assert span(5, 10) in spans(asset)


# -----------------------------------------------------------------------------
# What the steps cost
# -----------------------------------------------------------------------------


class TestAFirstFrameInTheYearOne:
    """A position whose first frame starts in the year 1 and holds ~739 000 days. A daily series would build a point per day (and ask
    the frames about each one); the steps are the changes: a handful of lookups. The counts are asserted, nothing is timed."""

    @pytest.mark.parametrize("request_key", [(1, 10), (None, 10)], ids=["one broker", "the asset summed"])
    @pytest.mark.parametrize("date_from", [date(1, 1, 1), None], ids=["from year 1", "no start date"])
    def test_it_builds_a_few_steps_and_reads_the_frames_a_few_times(self, monkeypatch, request_key, date_from):
        module = _module()
        reads: list[date] = []
        real = module._PositionReader.on

        def spy(self, on):
            reads.append(on)
            return real(self, on)

        monkeypatch.setattr(module._PositionReader, "on", spy)
        first, last = date(1, 1, 1), date(2024, 1, 5)
        frames = {
            (1, 10): [Frame(1, 10, first, date(2023, 12, 31), D("10"), D("1000"), D("900")), Frame(1, 10, date(2024, 1, 1), last, D("10"), D("1100"), D("900"))],
            (2, 10): [Frame(2, 10, date(1000, 6, 1), last, D("5"), D("500"), D("450"))],
        }

        [series] = module.build_position_series([request_key], date_from=date_from, date_to=last, frames=frames, realized_sales=[], flow_steps={}, transfers=[], acquisitions={})

        assert (last - first).days + 1 > 738_000  # the days a daily series would hold
        assert series.first_date == first and series.last_date == last
        assert 0 < len(series.points) < 50
        assert len(reads) < 2_000
        assert (series.points[0].date, series.points[-1].through) == (first, last)


# -----------------------------------------------------------------------------
# Random books against the period-to-day oracle
# -----------------------------------------------------------------------------


def _random_book(rng: random.Random) -> dict:
    """One position at broker 1 over 14 days: frames held, in gaps or in dust (some without a value or a complete cost), sales,
    cumulative income and costs, purchases, and a transfer to or from another broker."""
    last = 14
    date_from = rng.choice([None, 1, 2, 3, 4])
    low = 0 if date_from is None else date_from
    frames, cursor = [], 1
    while cursor <= last:
        end = min(last, cursor + rng.randint(0, 3))
        kind = rng.choice(["held", "held", "held", "gap", "dust"])
        if kind == "held":
            frames.append(frame(1, 10, cursor, end, rng.choice(["10", "20"]), rng.choice(["900", "1000", "1100", "1200", None]), rng.choice(["900", "1000"]), cost_complete=rng.random() < 0.85))
        elif kind == "dust":
            frames.append(frame(1, 10, cursor, end, "0.000001", "0.01", "0.009"))
        cursor = end + 1
    sales = [sale(1, 10, rng.randint(low + 1, last), rng.choice(["130", "90"]), "100") for _ in range(rng.randint(0, 2))]
    flows, income, costs = [], 0, 0
    for flow_day in sorted(rng.sample(range(0, last + 1), rng.randint(0, 3))):
        income += rng.randint(0, 5)
        costs += rng.randint(0, 3)
        flows.append((day(flow_day), D(income), D(costs)))
    acquisitions = [(day(rng.randint(low + 1, last)), D(rng.choice(["0", "100", "250"]))) for _ in range(rng.randint(0, 2))]
    transfers = []
    if rng.random() < 0.5:
        departure = rng.randint(1, last - 1)
        arrival = rng.randint(departure + 1, last)
        value, cost = rng.choice([("1150", "1000"), (None, "1000"), ("1150", None)])
        sender, receiver = rng.choice([(1, 2), (2, 1)])
        transfers.append(InternalAssetTransfer(departure=day(departure), arrival=day(arrival), asset_id=10, sender_broker_id=sender, receiver_broker_id=receiver, value_at_arrival=None if value is None else D(value), cost_moved=None if cost is None else D(cost)))
    return {"date_from": date_from, "date_to": last, "frames": frames, "sales": sales, "flow_steps": {(1, 10): flows} if flows else None, "transfers": transfers, "acquisitions": {(1, 10): acquisitions} if acquisitions else None}


def test_random_books_steps_equal_the_period_to_day_figures_of_every_day_held():
    """The old way of the series, kept as the oracle: the series of the period ``date_from``..``d`` ends on ``d`` (while the position is
    held there) with the figures of that day. The steps, expanded, give on each held day exactly those, with the Decimals' exponents;
    and they are contiguous and maximal. Seeded: the books are the same on every run."""
    rng = random.Random(20261025)
    compared = 0
    for number in range(300):
        book = _random_book(rng)
        [series] = build([(1, 10)], **book)
        if not series.points:
            continue
        daily = expand(series.points)
        assert [p.date for p in daily] == [series.first_date + timedelta(days=i) for i in range((series.last_date - series.first_date).days + 1)], number
        assert all(figures(a) != figures(b) for a, b in zip(series.points, series.points[1:], strict=False)), number
        assert series.complete is all(p.complete for p in daily), number
        for point in daily:
            if point.quantity <= 0:
                continue  # not held: closed or in transit, a period ending there has another last day
            till = {**book, "date_to": (point.date - JAN).days + 1}
            [period] = build([(1, 10)], **till)
            assert period.last_date == point.date and figures(period.points[-1]) == figures(point), (number, point.date)
            compared += 1
    assert compared > 1_000  # the books are not all empty or closed
