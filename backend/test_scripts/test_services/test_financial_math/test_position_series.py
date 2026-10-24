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
* one point per **calendar day** from ``first_date`` to ``last_date``, constant in the days nothing happens;
  ``last_date`` is ``date_to`` while the position is held, else the day it went to 0 (that day's point has quantity 0,
  value 0, the final pnl); a position never held has no points;
* ``None`` is «not known», never 0: a day with no value (a missing price or rate) has ``market_value`` None and its pnl is
  the sum of the parts that are known, flagged ``complete = False``, as the Periodo row does;
* a request for ``(None, asset)`` is the asset summed over the brokers that held it: the transfers between them cancel
  (their tracts are opposite, their value on arrival is not new capital); a closed leg keeps its final pnl.

Everything is in the report currency, at the owner's share: the engine's frames are already scaled.
"""

from __future__ import annotations

import importlib
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


def points_of(series) -> dict[date, object]:
    return {point.date: point for point in series.points}


# =============================================================================
# A position held from the start to the end
# =============================================================================


class TestAPositionHeldThroughTheWindow:
    """Held on 1 Jan with 10 units worth 1 000 (cost 900, so unrealized 100); on 4 Jan the price lifts it to 1 100."""

    FRAMES = (frame(1, 10, 1, 3, "10", "1000", "900"), frame(1, 10, 4, 5, "10", "1100", "900"))

    def test_the_pnl_is_the_change_of_the_unrealized_result_and_the_base_the_start_value(self):
        [series] = build([(1, 10)], date_from=1, date_to=5, frames=self.FRAMES)

        points = points_of(series)
        assert [(p.date, p.pnl, p.base) for p in series.points] == [
            (day(1), D("0"), D("1000")),
            (day(2), D("0"), D("1000")),
            (day(3), D("0"), D("1000")),
            (day(4), D("100"), D("1000")),
            (day(5), D("100"), D("1000")),
        ]
        assert (points[day(1)].pnl_percent, points[day(4)].pnl_percent) == (D("0"), D("0.1"))
        assert (series.first_date, series.last_date, series.held_at_start, series.held_at_end, series.closed_on, series.complete) == (day(1), day(5), True, True, None, True)

    def test_one_point_per_calendar_day_constant_while_the_frame_holds(self):
        [series] = build([(1, 10)], date_from=1, date_to=5, frames=self.FRAMES)

        assert [p.date for p in series.points] == [day(n) for n in range(1, 6)]
        assert {(p.quantity, p.market_value, p.cost_basis) for p in series.points if p.date <= day(3)} == {(D("10"), D("1000"), D("900"))}
        assert {(p.quantity, p.market_value, p.cost_basis) for p in series.points if p.date >= day(4)} == {(D("10"), D("1100"), D("900"))}

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
        assert {p.base for p in series.points} == {D("1200")}

    def test_the_series_ends_the_day_the_position_goes_to_zero_with_its_final_pnl(self):
        [series] = build([(1, 10)], date_from=1, date_to=10, frames=self.FRAMES, sales=self.SALES)

        last = series.points[-1]
        assert (series.last_date, series.closed_on, series.held_at_end) == (day(8), day(8), False)
        assert (last.date, last.quantity, last.market_value, last.cost_basis, last.pnl, last.pnl_percent) == (day(8), D("0"), D("0"), D("0"), D("160"), D("160") / D("1200"))

    def test_the_final_pnl_is_the_gain_over_the_window_not_over_the_whole_trade(self):
        # The trade made 1 360 - 1 000 = 360 in all; 200 of it was already in the start value.
        [series] = build([(1, 10)], date_from=1, date_to=10, frames=self.FRAMES, sales=self.SALES)

        assert series.points[-1].pnl == D("360") - D("200")


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

        assert {p.pnl for p in series.points} == {D("0")}


# =============================================================================
# Split: more units, the same worth
# =============================================================================


def test_a_split_changes_the_quantity_and_not_the_pnl_or_the_base():
    frames = (frame(1, 10, 1, 3, "10", "1000", "800"), frame(1, 10, 4, 6, "20", "1000", "800"))

    [series] = build([(1, 10)], date_from=1, date_to=6, frames=frames)

    points = points_of(series)
    assert (points[day(3)].quantity, points[day(4)].quantity) == (D("10"), D("20"))
    assert {p.pnl for p in series.points} == {D("0")}
    assert {p.base for p in series.points} == {D("1000")}


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

        assert {(p.base, p.pnl_percent) for p in series.points} == {(None, None)}

    def test_a_base_of_zero_has_no_percent(self):
        frames = (frame(1, 10, 3, 4, "10", "1000", "1000"),)

        [series] = build([(1, 10)], date_from=1, date_to=4, frames=frames, acquisitions={(1, 10): [(day(3), D("0"))]})

        assert {(p.base, p.pnl_percent) for p in series.points} == {(D("0"), None)}


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

        assert {p.base for p in receiver.points} == {D("1150")}
        assert points_of(receiver)[day(6)].pnl_percent == D("50") / D("1150")

    def test_the_asset_summed_over_the_brokers_has_no_jump_and_no_double_base(self):
        [asset] = build([(None, 10)], date_from=1, date_to=8, frames=self.FRAMES, transfers=self.TRANSFERS)

        points = points_of(asset)
        assert (asset.first_date, asset.last_date, asset.closed_on) == (day(1), day(8), None)
        # The same asset held at one broker would have gone 1 100 -> 1 150 -> 1 200: pnl 0, 50, 100.
        assert (points[day(4)].pnl, points[day(5)].pnl, points[day(6)].pnl, points[day(8)].pnl) == (D("0"), D("50"), D("100"), D("100"))
        assert {p.base for p in asset.points} == {D("1100")}
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
        assert {p.base for p in receiver.points} == {D("1000")}

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
        assert {p.base for p in receiver.points} == {D("1000")}
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

    assert len(asked) == len(series.points) == 5
    assert {(call["unrealized_start"], call["held_at_start"]) for call in asked} == {(D("100"), True)}
    assert [call["unrealized_end"] for call in asked] == [D("100"), D("100"), D("100"), D("200"), D("200")]
    assert [point.pnl for point in series.points] == [D("0"), D("0"), D("0"), D("100"), D("100")]


@pytest.mark.parametrize("name", ["build_position_series"])
def test_the_module_exposes_its_entry_point(name):
    assert callable(getattr(_module(), name))
