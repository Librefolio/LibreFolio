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

MF-A8 (J's review of MF-A5, the mirror on the receiving side). A row that received units by a counted tract measures
their result from their value on arrival (its tract adjustment, ``−(V − C)``, takes back what they gained before), but
its sales' and moves' costs are their historical cost: the base must add ``V − C`` too. J's example: 5 bought for 500
at A, moved to B worth 600, sold at B for 660: B's realized 160 + tract −100 = P&L 60, on 600 (10 %), not on HEAD's 500
(12 %). Product (HEAD 685d76dab + uncommitted):

* ``transfer_tracts_moved_in(transfers, date_from, end)``: per **receiver** ``(broker_id, asset_id)``, Σ(V − C) of its
  counted tracts — the same ``counted_tract`` rule; negative when the units arrived worth less than they cost;
* ``closed_position_base(..., moved_in=None)``: adds ``moved_in`` to the base, and is None for a base that is not
  **positive** (HEAD: None for 0 only).

Red on HEAD: ``TestTransferTractsMovedIn`` and ``TestMovedInExamples`` (AttributeError: no
``transfer_tracts_moved_in``), ``TestClosedPositionBaseMovedIn`` (TypeError: no ``moved_in`` parameter). Green on HEAD
and after: ``TestClosedPositionBaseWithoutMovedInUnchanged`` (HEAD's function, verbatim, on the MF-A5 corpus) and every
MF-A5 class above, which never pass ``moved_in``.

MF-A9 (the same mirror, for a position still open). A row opened in the period by counted tracts, still holding every
unit they brought, has no start value: ``annualized_period_return`` falls back on its end cost — their historical cost —
while its result counts them from their value on arrival. The A8 chain A → B → C: C holds the 5 units, worth
V₂ = 645 on arrival (C₂ = 500), 650 at the end: P&L 5, on 645 now, on 500 on HEAD (770928213). Product (HEAD +
uncommitted): ``annualized_period_return(..., moved_in=None)`` — with ``moved_in`` the fallback base is
``end_cost + moved_in``, None unless positive; without it HEAD's rule exactly (``end_cost`` ≠ 0, a negative one
included). A usable start value wins either way. The service passes it only to a row with no exit in the period (the
declared limitation, ``test_positions_contribution_engine.py``).

Red on HEAD: ``TestAnnualizedPeriodReturnMovedIn`` (TypeError: no ``moved_in`` parameter). Green on HEAD and after:
``TestAnnualizedPeriodReturnWithoutMovedInUnchanged`` (HEAD's function, verbatim, on its own corpus).

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


# =============================================================================
# MF-A8 — transfer_tracts_moved_in: the receiving half of the tracts
# =============================================================================

UNCOUNTED = [
    pytest.param(_transfer(departure=FROM), id="departs-on-the-start-day"),
    pytest.param(_transfer(departure=BEFORE), id="in-transit-at-the-start"),
    pytest.param(_transfer(arrival=AFTER_TO), id="in-transit-at-the-end"),
    pytest.param(_transfer(value=None), id="value-unknown"),
    pytest.param(_transfer(cost=None), id="cost-unknown"),
]


class TestTransferTractsMovedIn:
    def test_sums_each_receiver(self):
        """Two tracts into (B, X) from two senders, one into (C, X), one into (B, Y): one entry per receiver and asset,
        Σ(V − C)."""
        transfers = [
            _transfer(value="600", cost="500"),  # A → B: +100
            _transfer(departure=TO, arrival=TO, sender=C, receiver=B, value="330", cost="300"),  # C → B: +30
            _transfer(receiver=C, value="450", cost="400"),  # A → C: +50
            _transfer(asset=Y, value="300", cost="200"),  # A → B of Y: +100
        ]

        assert contributions.transfer_tracts_moved_in(transfers, FROM, TO) == {(B, X): Decimal("130"), (C, X): Decimal("50"), (B, Y): Decimal("100")}

    def test_the_sender_is_never_a_key(self):
        """What the units gained before arriving belongs to the receiver's base: the sender's row has nothing of it."""
        assert contributions.transfer_tracts_moved_in([_transfer()], FROM, TO) == {(B, X): Decimal("100")}

    def test_a_chain_gives_each_receiver_its_own_tract(self):
        """A → B (600 − 500), then B → C of the same units (645 − 500): B received +100, C +145 — sending them on
        takes nothing from what B received."""
        transfers = [_transfer(), _transfer(departure=TO, arrival=TO, sender=B, receiver=C, value="645", cost="500")]

        assert contributions.transfer_tracts_moved_in(transfers, FROM, TO) == {(B, X): Decimal("100"), (C, X): Decimal("145")}

    @pytest.mark.parametrize(
        ("value", "cost", "expected"),
        [
            # Arrived worth less than it cost: negative, kept.
            pytest.param("400", "500", "-100", id="arrived-at-a-loss"),
            # V = C: a tract of 0 still keys the receiver.
            pytest.param("500", "500", "0", id="arrived-at-cost"),
            # Received for free (a known cost of 0): the whole value.
            pytest.param("600", "0", "600", id="cost-zero"),
            pytest.param("0", "500", "-500", id="worthless-on-arrival"),
        ],
    )
    def test_the_tract_is_value_minus_cost_whatever_its_sign(self, value, cost, expected):
        assert contributions.transfer_tracts_moved_in([_transfer(value=value, cost=cost)], FROM, TO) == {(B, X): Decimal(expected)}

    def test_a_gain_and_a_loss_into_one_row_net(self):
        """+100 and −50 into (B, X): +50."""
        assert contributions.transfer_tracts_moved_in([_transfer(value="600"), _transfer(value="450")], FROM, TO) == {(B, X): Decimal("50")}

    @pytest.mark.parametrize("excluded", UNCOUNTED)
    def test_an_uncounted_transfer_is_ignored(self, excluded):
        """Alone it leaves no entry; beside a counted one it changes nothing: its units entered the row at their cost."""
        counted = _transfer(value="650", cost="500")

        assert contributions.transfer_tracts_moved_in([excluded], FROM, TO) == {}
        assert contributions.transfer_tracts_moved_in([counted, excluded], FROM, TO) == {(B, X): Decimal("150")}

    def test_without_a_start_every_departure_counts(self):
        """``date_from`` None: the departure before FROM counts, the arrival after TO still does not."""
        assert contributions.transfer_tracts_moved_in([_transfer(departure=BEFORE), _transfer(arrival=AFTER_TO)], None, TO) == {(B, X): Decimal("100")}

    def test_nothing_moved_nothing_in(self):
        assert contributions.transfer_tracts_moved_in([], FROM, TO) == {}

    @pytest.mark.parametrize("conditions", TRUTH_TABLE, ids=TRUTH_IDS)
    def test_it_counts_the_tracts_the_adjustments_count(self, conditions):
        """The one rule (``counted_tract``): a transfer is in the moved-in tracts exactly when it is in the adjustments."""
        transfer = _truth_case(*conditions)

        assert bool(contributions.transfer_tracts_moved_in([transfer], FROM, TO)) is contributions.counted_tract(transfer, FROM, TO)

    @pytest.mark.parametrize(("transfers", "date_from", "end", "expected"), list(TRACT_CORPUS.values()), ids=list(TRACT_CORPUS))
    def test_it_is_what_the_adjustment_takes_back_from_the_receiver(self, transfers, date_from, end, expected):
        """The mirror, on every case of the tract corpus (its adjustments are HEAD's): each row's adjustment is the
        tracts it sent, +(V − C) each, minus exactly what it received by them."""
        sent: dict[tuple[int, int], Decimal] = defaultdict(lambda: ZERO)
        for transfer in transfers:
            if contributions.counted_tract(transfer, date_from, end):
                sent[(transfer.sender_broker_id, transfer.asset_id)] += transfer.value_at_arrival - transfer.cost_moved

        moved_in = contributions.transfer_tracts_moved_in(transfers, date_from, end)

        assert set(moved_in) | set(sent) == set(expected)
        assert {key: sent.get(key, ZERO) - moved_in.get(key, ZERO) for key in expected} == expected


# =============================================================================
# MF-A8 — closed_position_base with what moved in
# =============================================================================


def _head_closed_position_base(cost_sold: Decimal, sales: int, moved_out: tuple[Decimal, int] | None, exits: int) -> Decimal | None:
    """HEAD's closed_position_base (contributions.py @ 685d76dab), verbatim but for its name and the zero's."""
    moved_cost, moved_count = moved_out or (ZERO, 0)
    if exits != sales + moved_count:
        return None
    base = cost_sold + moved_cost
    return base if base else None


# MF-A5's cases, none with anything moved in: name -> (cost_sold, sales, moved_out, exits)
A5_BASE_CORPUS: dict[str, tuple[str, int, tuple[str, int] | None, int]] = {
    "sold-and-moved": ("500", 1, ("500", 1), 2),
    "several-of-each": ("700", 2, ("900", 3), 5),
    "sold-only": ("1000", 2, None, 2),
    "sold-only-explicit-nothing-moved": ("1000", 2, ("0", 0), 2),
    "moved-only": ("0", 0, ("1000", 1), 1),
    "a-transfer-not-counted": ("500", 1, None, 2),
    "a-third-exit": ("500", 1, ("500", 1), 3),
    "moved-not-counted": ("0", 0, None, 1),
    "fewer-exits-than-disposals": ("500", 2, None, 1),
    "no-exit": ("0", 0, None, 0),
    "no-exit-explicit": ("0", 0, ("0", 0), 0),
    "sold-at-no-cost": ("0", 1, None, 1),
    "moved-at-no-cost": ("0", 0, ("0", 1), 1),
}


def _a5_args(cost_sold: str, sales: int, moved_out: tuple[str, int] | None, exits: int) -> tuple[Decimal, int, tuple[Decimal, int] | None, int]:
    return Decimal(cost_sold), sales, None if moved_out is None else (Decimal(moved_out[0]), moved_out[1]), exits


class TestClosedPositionBaseWithoutMovedInUnchanged:
    @pytest.mark.parametrize("case", list(A5_BASE_CORPUS.values()), ids=list(A5_BASE_CORPUS))
    def test_the_base_is_heads(self, case):
        """Guard. Called as MF-A5 calls it, the base is HEAD's on every MF-A5 case: covered or not, zero or not."""
        args = _a5_args(*case)

        assert contributions.closed_position_base(*args) == _head_closed_position_base(*args)


class TestClosedPositionBaseMovedIn:
    @pytest.mark.parametrize(
        ("cost_sold", "sales", "moved_out", "exits", "moved_in", "expected"),
        [
            # J's example: B sold the 5 it received (cost 500), worth 600 on arrival.
            pytest.param("500", 1, None, 1, "100", "600", id="received-then-sold"),
            # Bought for 500, worth 400 on arrival, sold.
            pytest.param("500", 1, None, 1, "-100", "400", id="received-at-a-loss-then-sold"),
            # The middle of a chain A → B → C: nothing sold, moved out at the historical cost C₁ = 500, received
            # V₁ − C₁ = 100: the base is V₁.
            pytest.param("0", 0, ("500", 1), 1, "100", "600", id="passed-through"),
            # 10 held at the start (cost 1000), 5 received (cost 500, worth 650), all 15 sold in two sales.
            pytest.param("1500", 2, None, 2, "150", "1650", id="held-and-received-then-sold"),
            # Received at cost: nothing gained before arriving, the base is the cost.
            pytest.param("500", 1, None, 1, "0", "500", id="received-at-cost"),
        ],
    )
    def test_the_base_adds_what_the_units_gained_before_arriving(self, cost_sold, sales, moved_out, exits, moved_in, expected):
        moved = None if moved_out is None else (Decimal(moved_out[0]), moved_out[1])

        assert contributions.closed_position_base(Decimal(cost_sold), sales, moved, exits, Decimal(moved_in)) == Decimal(expected)

    @pytest.mark.parametrize(
        ("cost_sold", "sales", "moved_out", "exits", "moved_in"),
        [
            # Worthless on arrival (V 0, C 500), sold: 500 − 500.
            pytest.param("500", 1, None, 1, "-500", id="worthless-on-arrival"),
            pytest.param("0", 0, ("500", 1), 1, "-500", id="passed-through-worthless"),
            # Below zero: not a ledger the engine gives (V ≥ 0), the sign's guard.
            pytest.param("100", 1, None, 1, "-300", id="below-zero"),
        ],
    )
    def test_a_base_that_is_not_positive_is_no_base(self, cost_sold, sales, moved_out, exits, moved_in):
        moved = None if moved_out is None else (Decimal(moved_out[0]), moved_out[1])

        assert contributions.closed_position_base(Decimal(cost_sold), sales, moved, exits, Decimal(moved_in)) is None

    @pytest.mark.parametrize(
        ("cost_sold", "sales", "moved_out", "exits", "moved_in"),
        [
            # Received and sold, but a second exit not covered (a transfer outside the scope).
            pytest.param("500", 1, None, 2, "100", id="an-exit-not-covered"),
            # Received, then passed on by a transfer not counted (in transit at the end).
            pytest.param("0", 0, None, 1, "100", id="passed-on-not-counted"),
        ],
    )
    def test_what_moved_in_covers_no_exit(self, cost_sold, sales, moved_out, exits, moved_in):
        """A unit that left another way: None, the general rule stands — whatever moved in."""
        moved = None if moved_out is None else (Decimal(moved_out[0]), moved_out[1])

        assert contributions.closed_position_base(Decimal(cost_sold), sales, moved, exits, Decimal(moved_in)) is None

    @pytest.mark.parametrize("case", list(A5_BASE_CORPUS.values()), ids=list(A5_BASE_CORPUS))
    def test_nothing_moved_in_is_no_moved_in(self, case):
        """None or 0 moved in: the base without it, on every MF-A5 case."""
        args = _a5_args(*case)
        without = contributions.closed_position_base(*args)

        assert contributions.closed_position_base(*args, None) == without
        assert contributions.closed_position_base(*args, ZERO) == without


# =============================================================================
# MF-A8 — the composition, from the transfers themselves
# =============================================================================

MI_DEPARTURE = date(2025, 2, 17)
MI_ARRIVAL = date(2025, 2, 19)  # the units reach B: its row opens
MI_ONWARD = date(2025, 3, 31)  # the last leave B: 40 days later
MI_ONWARD_ARRIVAL = date(2025, 4, 2)


class TestMovedInExamples:
    """B's row closed over MI_ARRIVAL → MI_ONWARD (40 days): its P&L from the tract adjustment and its realized, its base
    from the moved cost and the moved-in tracts, as ``get_positions_contribution`` composes them."""

    @staticmethod
    def _closed_return(pnl: Decimal, base: Decimal) -> Decimal | None:
        return contributions.closed_position_annualized(pnl, base, MI_ARRIVAL, MI_ONWARD, FROM)

    @staticmethod
    def _expected(ratio: str) -> Decimal:
        days = (MI_ONWARD - MI_ARRIVAL).days
        annualized = cumulative_to_annualized(Decimal(ratio), days)
        assert days == 40 and annualized is not None, "precondition: an annualizable window"
        return annualized

    def _b_base(self, transfers: list[InternalAssetTransfer], cost_sold: str, sales: int, exits: int) -> Decimal | None:
        moved_out = contributions.transfer_costs_moved_out(transfers, FROM, TO).get((B, X))
        moved_in = contributions.transfer_tracts_moved_in(transfers, FROM, TO).get((B, X))
        return contributions.closed_position_base(Decimal(cost_sold), sales, moved_out, exits, moved_in)

    @pytest.mark.parametrize(
        ("value", "proceeds", "pnl", "base", "ratio", "head_ratio"),
        [
            # J's example: 5 bought for 500 at A, worth 600 on reaching B, sold there for 660. Realized 160, tract
            # −100: 60 on 600, HEAD on the 500 sold.
            pytest.param("600", "660", "60", "600", "0.1000", "0.1200", id="js-example"),
            # Worth 400 on reaching B, sold for 440. Realized −60, tract +100: 40 on 400, HEAD on 500.
            pytest.param("400", "440", "40", "400", "0.1000", "0.0800", id="arrived-at-a-loss"),
        ],
    )
    def test_received_then_sold(self, value, proceeds, pnl, base, ratio, head_ratio):
        transfers = [_transfer(departure=MI_DEPARTURE, arrival=MI_ARRIVAL, value=value, cost="500")]
        b_pnl = Decimal(proceeds) - Decimal("500") + contributions.transfer_tract_adjustments(transfers, FROM, TO)[(B, X)]
        assert b_pnl == Decimal(pnl), "precondition: B's P&L"

        b_base = self._b_base(transfers, "500", 1, 1)

        assert b_base == Decimal(base)
        assert self._closed_return(b_pnl, b_base) == self._expected(ratio)
        assert self._closed_return(b_pnl, Decimal("500")) == self._expected(head_ratio) != self._expected(ratio), "HEAD's base, the cost sold"

    def test_passed_through_the_base_is_the_value_on_arrival(self):
        """A → B worth V₁ = 600 on arrival, B → C worth V₂ = 645: B's P&L −(V₁ − C₁) + (V₂ − C₁) = V₂ − V₁ = 45, on
        C₁ + (V₁ − C₁) = V₁ = 600: 0.0750. HEAD on the cost moved out, C₁ = 500: 0.0900."""
        transfers = [
            _transfer(departure=MI_DEPARTURE, arrival=MI_ARRIVAL, value="600", cost="500"),
            _transfer(departure=MI_ONWARD, arrival=MI_ONWARD_ARRIVAL, sender=B, receiver=C, value="645", cost="500"),
        ]
        b_pnl = contributions.transfer_tract_adjustments(transfers, FROM, TO)[(B, X)]
        assert b_pnl == Decimal("45"), "precondition: B's P&L, V₂ − V₁"

        b_base = self._b_base(transfers, "0", 0, 1)

        assert b_base == Decimal("600")
        assert self._closed_return(b_pnl, b_base) == self._expected("0.0750")
        assert self._closed_return(b_pnl, Decimal("500")) == self._expected("0.0900") != self._expected("0.0750"), "HEAD's base, the cost moved out"


# =============================================================================
# MF-A9 — annualized_period_return: an open position's fallback base with what moved in
# =============================================================================

# C's window in the A8 chain: from the units reaching it (MI_ONWARD_ARRIVAL) to an end 44 days later. On TO it is 28
# days, too short to annualize (None whatever the base): the service test reads the chain to the same A9_TO.
A9_TO = date(2025, 5, 16)
A9_DAYS = (A9_TO - MI_ONWARD_ARRIVAL).days


def _head_annualized_period_return(period_pnl: Decimal | None, start_value: Decimal | None, end_cost: Decimal | None, *, window_from: date | None, end: date) -> Decimal | None:
    """HEAD's annualized_period_return (contributions.py @ 770928213), verbatim but for its name, its quantum's and its
    helper's module (``period_return_on_start``, unchanged)."""
    ratio = contributions.period_return_on_start(period_pnl, start_value)
    if ratio is None and period_pnl is not None and end_cost is not None and end_cost != 0:
        ratio = (period_pnl / end_cost).quantize(Decimal("0.0001"))
    if ratio is None or window_from is None:
        return None
    return cumulative_to_annualized(ratio, (end - window_from).days)


def _a9_expected(ratio: str) -> Decimal:
    annualized = cumulative_to_annualized(Decimal(ratio), A9_DAYS)
    assert A9_DAYS == 44 and annualized is not None, "precondition: an annualizable window"
    return annualized


def _d(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


# HEAD's corpus: name -> (period_pnl, start_value, end_cost, window_from, end)
A9_CORPUS: dict[str, tuple[str | None, str | None, str | None, date | None, date]] = {
    "on-the-start-value": ("25", "1100", "500", FROM, TO),
    "on-a-negative-start-value": ("25", "-1100", "500", FROM, TO),
    "opened-in-the-period-on-the-end-cost": ("5", "0", "500", MI_ONWARD_ARRIVAL, A9_TO),
    "no-start-value-on-the-end-cost": ("5", None, "500", MI_ONWARD_ARRIVAL, A9_TO),
    "a-negative-end-cost-is-a-base": ("10", "0", "-200", MI_ONWARD_ARRIVAL, A9_TO),
    "an-end-cost-of-zero": ("10", "0", "0", MI_ONWARD_ARRIVAL, A9_TO),
    "end-cost-unknown": ("10", "0", None, MI_ONWARD_ARRIVAL, A9_TO),
    "no-pnl": (None, "0", "500", MI_ONWARD_ARRIVAL, A9_TO),
    "no-window": ("5", "0", "500", None, A9_TO),
    "a-window-too-short": ("5", "0", "500", MI_ONWARD_ARRIVAL, TO),
    "a-total-loss": ("-500", "0", "500", MI_ONWARD_ARRIVAL, A9_TO),
}


def _a9_call(case: tuple[str | None, str | None, str | None, date | None, date], **moved_in: Decimal | None) -> Decimal | None:
    pnl, start, end_cost, window_from, end = case
    return contributions.annualized_period_return(_d(pnl), _d(start), _d(end_cost), window_from=window_from, end=end, **moved_in)


class TestAnnualizedPeriodReturnWithoutMovedInUnchanged:
    @pytest.mark.parametrize("case", list(A9_CORPUS.values()), ids=list(A9_CORPUS))
    def test_the_return_is_heads(self, case):
        """Guard. Called as before MF-A9, the return is HEAD's: on the start value, else on the end cost, else None."""
        pnl, start, end_cost, window_from, end = case

        assert _a9_call(case) == _head_annualized_period_return(_d(pnl), _d(start), _d(end_cost), window_from=window_from, end=end)

    def test_a_negative_end_cost_is_still_a_base(self):
        """Guard. Without ``moved_in`` an end cost other than 0 is the base whatever its sign, as on HEAD: 10 / −200."""
        assert _a9_call(A9_CORPUS["a-negative-end-cost-is-a-base"]) == _a9_expected("-0.0500")


class TestAnnualizedPeriodReturnMovedIn:
    """With ``moved_in`` and no usable start value, the base is the end cost plus what the units gained before arriving;
    None unless positive. Over MI_ONWARD_ARRIVAL → A9_TO, 44 days."""

    @pytest.mark.parametrize("start", [None, "0"], ids=["no-start-value", "a-start-of-zero"])
    @pytest.mark.parametrize(
        ("pnl", "end_cost", "moved_in", "ratio", "head_ratio"),
        [
            # C in the A8 chain: 5 units cost 500, worth 645 on reaching C, 650 at the end: 5 on 645, HEAD on 500.
            pytest.param("5", "500", "145", "0.0078", "0.0100", id="cs-example"),
            # Cost 500, worth 400 on arrival, 450 at the end: 50 on 400, HEAD on 500.
            pytest.param("50", "500", "-100", "0.1250", "0.1000", id="arrived-at-a-loss"),
            # Worth their cost on arrival: nothing gained before, the base is the end cost.
            pytest.param("5", "500", "0", "0.0100", "0.0100", id="received-at-cost"),
        ],
    )
    def test_the_fallback_base_adds_what_the_units_gained_before_arriving(self, start, pnl, end_cost, moved_in, ratio, head_ratio):
        case = (pnl, start, end_cost, MI_ONWARD_ARRIVAL, A9_TO)
        head = _head_annualized_period_return(_d(pnl), _d(start), _d(end_cost), window_from=MI_ONWARD_ARRIVAL, end=A9_TO)
        assert head == _a9_expected(head_ratio), "precondition: HEAD's base, the end cost"

        assert _a9_call(case, moved_in=Decimal(moved_in)) == _a9_expected(ratio)

    @pytest.mark.parametrize(
        ("end_cost", "moved_in"),
        [
            # Worthless on arrival (V 0, C 500): 500 − 500.
            pytest.param("500", "-500", id="worthless-on-arrival"),
            # Below zero: not a ledger the engine gives (V ≥ 0), the sign's guard.
            pytest.param("100", "-300", id="below-zero"),
            # A negative end cost the tract does not lift above zero.
            pytest.param("-200", "100", id="a-negative-end-cost-not-lifted"),
            # With ``moved_in`` the base must be positive: a negative end cost is no base, even received at cost.
            pytest.param("-200", "0", id="a-negative-end-cost-received-at-cost"),
        ],
    )
    def test_a_base_that_is_not_positive_is_no_base(self, end_cost, moved_in):
        case = ("10", "0", end_cost, MI_ONWARD_ARRIVAL, A9_TO)
        assert _a9_call(case) is not None, "precondition: HEAD's rule, the end cost, gives a figure"

        assert _a9_call(case, moved_in=Decimal(moved_in)) is None

    @pytest.mark.parametrize("start", ["1100", "-1100"], ids=["positive", "negative"])
    @pytest.mark.parametrize("moved_in", ["145", "-500", "0"], ids=["a-gain", "a-base-of-zero", "at-cost"])
    def test_a_usable_start_value_ignores_moved_in(self, start, moved_in):
        """The base is the size of the start value: what moved in changes nothing, not even a fallback base of 0."""
        case = ("25", start, "500", FROM, TO)
        on_start = cumulative_to_annualized(Decimal("0.0227"), (TO - FROM).days)
        assert on_start is not None and _a9_call(case) == on_start, "precondition: 25 / 1100 over the period"

        assert _a9_call(case, moved_in=Decimal(moved_in)) == on_start

    @pytest.mark.parametrize(
        "case",
        [
            # The end cost unknown (incomplete): what moved in is no base on its own.
            pytest.param(("5", "0", None, MI_ONWARD_ARRIVAL, A9_TO), id="end-cost-unknown"),
            pytest.param((None, "0", "500", MI_ONWARD_ARRIVAL, A9_TO), id="no-pnl"),
            pytest.param(("5", "0", "500", None, A9_TO), id="no-window"),
            # 28 days.
            pytest.param(("5", "0", "500", MI_ONWARD_ARRIVAL, TO), id="a-window-too-short"),
        ],
    )
    def test_without_a_figure_no_return(self, case):
        assert _a9_call(case, moved_in=Decimal("145")) is None

    @pytest.mark.parametrize("case", list(A9_CORPUS.values()), ids=list(A9_CORPUS))
    def test_nothing_moved_in_is_no_moved_in(self, case):
        """``moved_in=None``: HEAD's rule exactly, on its whole corpus — a negative end cost included."""
        assert _a9_call(case, moved_in=None) == _a9_call(case)

    def test_cs_example_from_the_transfers(self):
        """A → B worth V₁ = 600, B → C worth V₂ = 645 (C₁ = C₂ = 500); C holds the 5, worth 650 at the end. C's P&L:
        (650 − 500) − (V₂ − C₂) = 5; what moved in: V₂ − C₂ = 145; the base 500 + 145 = V₂: 0.0078. HEAD on the end cost
        500: 0.0100."""
        transfers = [
            _transfer(departure=MI_DEPARTURE, arrival=MI_ARRIVAL, value="600", cost="500"),
            _transfer(departure=MI_ONWARD, arrival=MI_ONWARD_ARRIVAL, sender=B, receiver=C, value="645", cost="500"),
        ]
        c_pnl = Decimal("650") - Decimal("500") + contributions.transfer_tract_adjustments(transfers, FROM, A9_TO)[(C, X)]
        assert c_pnl == Decimal("5"), "precondition: C's P&L, from its value on arrival"
        c_moved_in = contributions.transfer_tracts_moved_in(transfers, FROM, A9_TO)[(C, X)]
        assert c_moved_in == Decimal("145"), "precondition: what the units gained before reaching C"

        annualized = contributions.annualized_period_return(c_pnl, ZERO, Decimal("500"), window_from=MI_ONWARD_ARRIVAL, end=A9_TO, moved_in=c_moved_in)

        assert annualized == _a9_expected("0.0078")
        assert _head_annualized_period_return(c_pnl, ZERO, Decimal("500"), window_from=MI_ONWARD_ARRIVAL, end=A9_TO) == _a9_expected("0.0100") != annualized, "HEAD's base, the end cost"
