"""
MF-A5 (workstream MF, lot A5) — the base of a closed position's annualized return covers every unit that left it.

Module under test: ``backend/app/services/financial_math/portfolio/contributions.py``. A position fully sold in the
period annualizes its result on a base over its flight time (``closed_position_annualized``). Until MF-A5 (HEAD
203197f5a) the base was the cost of the units it **sold**; but the row's result also carries what the units it moved to
another broker of the scope did while there (the P22 tract adjustment, ``transfer_tract_adjustments``). J's example:
10 units, cost 1 000, start value 1 100; sell 5 for 625, transfer 5 worth 600 on arrival to a broker of the scope: the
row's P&L is +125 (ΔUGL −100 + realized +125 + tract +100), HEAD's base 500 (25 %), the base now 1 000 (12.5 %).

Coordinator's decision (1) + (2), one shared predicate:

* ``counted_tract(transfer, date_from, end)``: the period's rows split the transfer's result — it departs after
  ``date_from`` (or there is none), arrives on or before ``end``, its value on arrival and its cost moved both known.
  The one condition of ``transfer_tract_adjustments`` (unchanged: guarded against HEAD's own code, written out below
  verbatim but for its name) and of ``transfer_costs_moved_out``;
* ``transfer_costs_moved_out(transfers, date_from, end)``: per **sender** ``(broker_id, asset_id)``, the cost its counted
  tracts moved out and how many;
* ``closed_position_base(cost_sold, sales, moved_out, exits)``: ``cost_sold`` + the moved cost when the position's exits
  of the period are exactly its counted sales plus its counted tracts; None when they are not (a unit left another
  way: outside the scope, still in transit, value or cost unknown, an ADJUSTMENT without a cost) — the general rule
  stands — and None on a base of 0.

Red on HEAD by absence (the three functions do not exist there: AttributeError, raised when each test runs — the module
is imported at module level, it exists on HEAD): ``TestCountedTract``, ``TestTransferCostsMovedOut``,
``TestClosedPositionBase``, ``TestJsExample`` (the composition with ``closed_position_annualized``: 0.1250 on 1 000,
HEAD's base gave 0.2500 on 500). Green on HEAD and after: ``TestTransferTractAdjustmentsUnchanged``.

The window (``holding_window.exits_in``) is tested in ``test_holding_window.py``; the whole chain through
``PortfolioService.get_positions_contribution`` in ``test_financial/test_positions_contribution_engine.py``
(``TestClosedPositionBase``).

Pure: no database, no server, no network.
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

import pytest

import backend.app.services.financial_math.portfolio.contributions as contributions
from backend.app.services.financial_math.portfolio.models import InternalAssetTransfer
from backend.app.services.financial_math.returns import cumulative_to_annualized

ZERO = Decimal("0")

# The period: (FROM, TO]
BEFORE = date(2025, 1, 3)
FROM = date(2025, 1, 15)
AFTER_FROM = date(2025, 1, 16)
MIDDLE = date(2025, 2, 17)
TO = date(2025, 4, 30)
AFTER_TO = date(2025, 5, 1)

# Brokers and assets: ids only
A, B, C = 11, 12, 13
X, Y = 101, 102


def _transfer(departure: date = MIDDLE, arrival: date = MIDDLE, *, sender: int = A, receiver: int = B, asset: int = X, value: str | None = "600", cost: str | None = "500") -> InternalAssetTransfer:
    return InternalAssetTransfer(
        departure=departure,
        arrival=arrival,
        asset_id=asset,
        sender_broker_id=sender,
        receiver_broker_id=receiver,
        value_at_arrival=None if value is None else Decimal(value),
        cost_moved=None if cost is None else Decimal(cost),
    )


# =============================================================================
# HEAD's transfer_tract_adjustments (contributions.py @ 203197f5a), verbatim but for its name
# =============================================================================


def _head_transfer_tract_adjustments(transfers: Iterable[InternalAssetTransfer], date_from: date | None, end: date) -> dict[tuple[int, int], Decimal]:
    adjustments: dict[tuple[int, int], Decimal] = defaultdict(lambda: ZERO)
    for transfer in transfers:
        if date_from is not None and transfer.departure <= date_from:
            continue
        if transfer.arrival > end or transfer.value_at_arrival is None or transfer.cost_moved is None:
            continue
        tract = transfer.value_at_arrival - transfer.cost_moved
        adjustments[(transfer.sender_broker_id, transfer.asset_id)] += tract
        adjustments[(transfer.receiver_broker_id, transfer.asset_id)] -= tract
    return dict(adjustments)


# =============================================================================
# The truth table: four conditions, each one able to exclude a transfer on its own
# =============================================================================


def _truth_case(departs_after_start: bool, arrives_by_end: bool, value_known: bool, cost_known: bool) -> InternalAssetTransfer:
    """A transfer meeting exactly the conditions asked, against the period (FROM, TO]: at their edges, so each one is
    decided by a day — departing on FROM is not after it, arriving on TO is by it."""
    return _transfer(
        departure=AFTER_FROM if departs_after_start else FROM,
        arrival=TO if arrives_by_end else AFTER_TO,
        value=None if not value_known else "600",
        cost=None if not cost_known else "500",
    )


TRUTH_TABLE = list(itertools.product((True, False), repeat=4))
TRUTH_IDS = ["-".join(name if flag else f"not-{name}" for name, flag in zip(("after-start", "by-end", "value", "cost"), row, strict=True)) for row in TRUTH_TABLE]


class TestCountedTract:
    @pytest.mark.parametrize("conditions", TRUTH_TABLE, ids=TRUTH_IDS)
    def test_counted_only_when_every_condition_holds(self, conditions):
        """16 rows: counted exactly when the four conditions hold together."""
        transfer = _truth_case(*conditions)

        assert contributions.counted_tract(transfer, FROM, TO) is all(conditions)

    @pytest.mark.parametrize(
        ("transfer", "counted"),
        [
            # Departing on FROM is the start state's (movements dated ≤ date_from are in the start): not this period's.
            pytest.param(_transfer(departure=FROM, arrival=AFTER_FROM), False, id="departs-on-the-start-day"),
            pytest.param(_transfer(departure=BEFORE, arrival=MIDDLE), False, id="in-transit-at-the-start"),
            pytest.param(_transfer(departure=AFTER_FROM, arrival=AFTER_FROM), True, id="departs-the-day-after-the-start"),
            # Arriving on TO is inside (FROM, TO].
            pytest.param(_transfer(departure=MIDDLE, arrival=TO), True, id="arrives-on-the-end-day"),
            pytest.param(_transfer(departure=MIDDLE, arrival=AFTER_TO), False, id="in-transit-at-the-end"),
            pytest.param(_transfer(departure=TO, arrival=TO), True, id="same-day-on-the-end-day"),
            # A value or a cost of exactly 0 is known: only None excludes.
            pytest.param(_transfer(value="0"), True, id="value-zero-is-known"),
            pytest.param(_transfer(cost="0"), True, id="cost-zero-is-known"),
        ],
    )
    def test_the_edges(self, transfer, counted):
        assert contributions.counted_tract(transfer, FROM, TO) is counted

    @pytest.mark.parametrize(
        ("transfer", "counted"),
        [
            pytest.param(_transfer(departure=BEFORE, arrival=MIDDLE), True, id="any-departure"),
            pytest.param(_transfer(departure=MIDDLE, arrival=AFTER_TO), False, id="still-in-transit"),
            pytest.param(_transfer(value=None), False, id="value-unknown"),
            pytest.param(_transfer(cost=None), False, id="cost-unknown"),
        ],
    )
    def test_without_a_start_only_the_end_and_the_figures_count(self, transfer, counted):
        """``date_from`` None (a period from the beginning): every departure is inside it."""
        assert contributions.counted_tract(transfer, None, TO) is counted

    @pytest.mark.parametrize("conditions", TRUTH_TABLE, ids=TRUTH_IDS)
    def test_it_is_the_one_rule_of_both_functions(self, conditions):
        """The tract adjustments and the moved cost count the same transfers: a transfer is in both or in neither."""
        transfer = _truth_case(*conditions)
        counted = contributions.counted_tract(transfer, FROM, TO)

        assert bool(contributions.transfer_tract_adjustments([transfer], FROM, TO)) is counted
        assert bool(contributions.transfer_costs_moved_out([transfer], FROM, TO)) is counted


# =============================================================================
# transfer_tract_adjustments: the same answer as HEAD's (guard)
# =============================================================================

# name -> (transfers, date_from, end, expected adjustments)
TRACT_CORPUS: dict[str, tuple[list[InternalAssetTransfer], date | None, date, dict[tuple[int, int], Decimal]]] = {
    "empty": ([], FROM, TO, {}),
    # V − C = 100 to the sender, −100 to the receiver.
    "one-counted": ([_transfer()], FROM, TO, {(A, X): Decimal("100"), (B, X): Decimal("-100")}),
    # Each excluded on one condition: nothing.
    "none-counted": ([_transfer(departure=FROM), _transfer(arrival=AFTER_TO), _transfer(value=None), _transfer(cost=None)], FROM, TO, {}),
    # A → B then B → C of the same units: B gets −100 then +50 (650 − 600).
    "a-chain": (
        [_transfer(), _transfer(departure=TO, arrival=TO, sender=B, receiver=C, value="650", cost="600")],
        FROM,
        TO,
        {(A, X): Decimal("100"), (B, X): Decimal("-50"), (C, X): Decimal("-50")},
    ),
    # Two tracts from A of X, one of Y, a loss among them, one excluded.
    "mixed": (
        [_transfer(), _transfer(value="450", cost="500"), _transfer(asset=Y, value="300", cost="200"), _transfer(departure=BEFORE)],
        FROM,
        TO,
        {(A, X): Decimal("50"), (B, X): Decimal("-50"), (A, Y): Decimal("100"), (B, Y): Decimal("-100")},
    ),
    # V = C: a tract of 0 still keys both rows.
    "a-tract-of-zero": ([_transfer(value="500")], FROM, TO, {(A, X): ZERO, (B, X): ZERO}),
    "no-start": ([_transfer(departure=BEFORE), _transfer(arrival=AFTER_TO)], None, TO, {(A, X): Decimal("100"), (B, X): Decimal("-100")}),
}


class TestTransferTractAdjustmentsUnchanged:
    @pytest.mark.parametrize(("transfers", "date_from", "end", "expected"), list(TRACT_CORPUS.values()), ids=list(TRACT_CORPUS))
    def test_the_adjustments_are_heads(self, transfers, date_from, end, expected):
        """The expected adjustments, from HEAD's code and from today's: the shared predicate changed nothing."""
        assert _head_transfer_tract_adjustments(transfers, date_from, end) == expected, "the case is not what HEAD gave: fix the corpus"
        assert contributions.transfer_tract_adjustments(transfers, date_from, end) == expected


# =============================================================================
# transfer_costs_moved_out
# =============================================================================


class TestTransferCostsMovedOut:
    def test_sums_each_sender_with_its_count(self):
        """Two tracts from (A, X), one from (B, X), one from (A, Y): one entry per sender and asset, the costs summed."""
        transfers = [
            _transfer(cost="500"),
            _transfer(departure=TO, arrival=TO, cost="250"),
            _transfer(sender=B, receiver=C, cost="300"),
            _transfer(asset=Y, cost="70"),
        ]

        moved = contributions.transfer_costs_moved_out(transfers, FROM, TO)

        assert moved == {(A, X): (Decimal("750"), 2), (B, X): (Decimal("300"), 1), (A, Y): (Decimal("70"), 1)}

    def test_the_receiver_is_never_a_key(self):
        """The cost moves out of the sender: the receiver's row has nothing of it."""
        assert contributions.transfer_costs_moved_out([_transfer()], FROM, TO) == {(A, X): (Decimal("500"), 1)}

    @pytest.mark.parametrize(
        "excluded",
        [
            pytest.param(_transfer(departure=FROM), id="departs-on-the-start-day"),
            pytest.param(_transfer(departure=BEFORE), id="in-transit-at-the-start"),
            pytest.param(_transfer(arrival=AFTER_TO), id="in-transit-at-the-end"),
            # The cost is known, but the tract is not counted: neither is its cost.
            pytest.param(_transfer(value=None), id="value-unknown"),
            pytest.param(_transfer(cost=None), id="cost-unknown"),
        ],
    )
    def test_an_uncounted_transfer_is_ignored(self, excluded):
        """Alone it leaves no entry; beside a counted one it changes neither the cost nor the count."""
        counted = _transfer(cost="400")

        assert contributions.transfer_costs_moved_out([excluded], FROM, TO) == {}
        assert contributions.transfer_costs_moved_out([counted, excluded], FROM, TO) == {(A, X): (Decimal("400"), 1)}

    def test_a_cost_of_zero_is_counted(self):
        """A known cost of 0 (units received for free) is a counted tract: it adds 0 and counts one."""
        assert contributions.transfer_costs_moved_out([_transfer(cost="0"), _transfer(cost="500")], FROM, TO) == {(A, X): (Decimal("500"), 2)}

    def test_nothing_moved_nothing_out(self):
        assert contributions.transfer_costs_moved_out([], FROM, TO) == {}


# =============================================================================
# closed_position_base
# =============================================================================


class TestClosedPositionBase:
    @pytest.mark.parametrize(
        ("cost_sold", "sales", "moved_out", "exits", "expected"),
        [
            # J's example: 5 sold at a cost of 500, 5 moved at a cost of 500 — two exits, both covered.
            pytest.param("500", 1, ("500", 1), 2, "1000", id="sold-and-moved"),
            pytest.param("700", 2, ("900", 3), 5, "1600", id="several-of-each"),
            # Today's behaviour: no transfer, every exit a sale — the cost sold.
            pytest.param("1000", 2, None, 2, "1000", id="sold-only"),
            pytest.param("1000", 2, ("0", 0), 2, "1000", id="sold-only-explicit-nothing-moved"),
            # Every unit moved to a broker of the scope: the cost moved.
            pytest.param("0", 0, ("1000", 1), 1, "1000", id="moved-only"),
        ],
    )
    def test_every_exit_covered_the_base_is_the_sum(self, cost_sold, sales, moved_out, exits, expected):
        moved = None if moved_out is None else (Decimal(moved_out[0]), moved_out[1])

        assert contributions.closed_position_base(Decimal(cost_sold), sales, moved, exits) == Decimal(expected)

    @pytest.mark.parametrize(
        ("cost_sold", "sales", "moved_out", "exits"),
        [
            # A sale and a transfer outside the scope (or still in transit, or with V or C unknown): 2 exits, 1 covered.
            pytest.param("500", 1, None, 2, id="a-transfer-not-counted"),
            # A sale, a counted tract, and an ADJUSTMENT without a cost: 3 exits, 2 covered.
            pytest.param("500", 1, ("500", 1), 3, id="a-third-exit"),
            # A transfer-only exit whose tract is not counted.
            pytest.param("0", 0, None, 1, id="moved-not-counted"),
            # More disposals than exits in the window: the counts disagree, no base either way.
            pytest.param("500", 2, None, 1, id="fewer-exits-than-disposals"),
        ],
    )
    def test_one_exit_not_covered_no_base(self, cost_sold, sales, moved_out, exits):
        """None: the general rule stands."""
        moved = None if moved_out is None else (Decimal(moved_out[0]), moved_out[1])

        assert contributions.closed_position_base(Decimal(cost_sold), sales, moved, exits) is None

    @pytest.mark.parametrize(
        ("cost_sold", "sales", "moved_out", "exits"),
        [
            # Nothing left in the period (it closed before it).
            pytest.param("0", 0, None, 0, id="no-exit"),
            pytest.param("0", 0, ("0", 0), 0, id="no-exit-explicit"),
            # Covered, but at no cost: a free share sold, a free share moved.
            pytest.param("0", 1, None, 1, id="sold-at-no-cost"),
            pytest.param("0", 0, ("0", 1), 1, id="moved-at-no-cost"),
        ],
    )
    def test_a_base_of_zero_is_no_base(self, cost_sold, sales, moved_out, exits):
        moved = None if moved_out is None else (Decimal(moved_out[0]), moved_out[1])

        assert contributions.closed_position_base(Decimal(cost_sold), sales, moved, exits) is None


# =============================================================================
# The composition, J's example
# =============================================================================


class TestJsExample:
    def test_the_closed_return_is_on_the_cost_of_both_halves(self):
        """P&L 125 on a base of 500 + 500 = 1 000: 0.1250 over FROM → the day the last units left (61 days). HEAD's
        base, the cost sold alone (500): 0.2500."""
        transfers = [_transfer(departure=date(2025, 3, 17), arrival=date(2025, 3, 19), value="600", cost="500")]
        closed = date(2025, 3, 17)
        days = (closed - FROM).days
        expected, head = cumulative_to_annualized(Decimal("0.1250"), days), cumulative_to_annualized(Decimal("0.2500"), days)
        assert days == 61 and expected is not None and head is not None and expected != head, "precondition: two annualizable returns"

        base = contributions.closed_position_base(Decimal("500"), 1, contributions.transfer_costs_moved_out(transfers, FROM, TO).get((A, X)), 2)

        assert base == Decimal("1000")
        assert contributions.closed_position_annualized(Decimal("125"), base, date(2025, 1, 6), closed, FROM) == expected
        assert contributions.closed_position_annualized(Decimal("125"), Decimal("500"), date(2025, 1, 6), closed, FROM) == head, "HEAD's base"
