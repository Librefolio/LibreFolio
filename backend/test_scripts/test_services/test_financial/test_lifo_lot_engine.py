"""Project 69, lot L1 — the lot engine replays a book in FIFO or in LIFO (``LotMatchingMethod``).

Pure: ``run_fifo_lot_engine`` on hand-written rows, and ``read_transfers_at_scope_boundary`` for the view of one broker.
No DB, no server, no FX.

THE RULES (plan ``Release_2/Phase_2/69_lotsLifo/plan-phase02LotsLifo.prompt.md``, approved 11/11/2026):

1. The engine takes the method of its replay, ``matching_method``; without one it replays in FIFO, as before.
2. In LIFO every outflow of a broker takes the most recent lot first: opening date, then lot id, both descending. The
   one queue serves sales, outgoing adjustments, short covers and transfer departures (D2). The queue stays per broker
   (D3).
3. Within one day the inflows (BUY, ADJUSTMENT-in) come before the outflows (SELL, ADJUSTMENT-out), in both methods
   (D4, D4b): a sale recorded before the purchase of its day no longer fails a broker without shorting, and on a broker
   with shorting a same-day short becomes a long lot with the same realized gain.
4. A lot is dated at its opening with the data the calculator has (D10): with every broker in scope a transferred lot
   keeps its purchase date and the arrival broker's queue orders it by that date; seen from one broker only it is born
   at its arrival.
5. The lots are the same in both methods (id, opening, quantity, cost); only which lot closes, and when, changes. A
   position closed in full realizes the same total in both.

Before L1 (HEAD ``927d66f23``): ``LotMatchingMethod`` does not exist — ImportError at collection.
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.fifo.models import EconomicEvent, FifoEngineResult, FifoInputTransaction, LotMatchingMethod, ReferencePriceResolution, fails_the_replay
from backend.app.services.financial_math.lots.scope_boundary import TransferPartner, read_transfers_at_scope_boundary
from backend.app.services.financial_math.price_marks import build_asset_price_series

D = Decimal
ASSET_ID = 6901
BROKER_A = 1
BROKER_B = 2
FIFO = LotMatchingMethod.FIFO
LIFO = LotMatchingMethod.LIFO


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _tx(tx_id: int, tx_type: str, quantity: str, *, on: str, broker_id: int = BROKER_A, amount: str = "0", cost: str | None = None, related: int | None = None) -> FifoInputTransaction:
    return FifoInputTransaction(
        id=tx_id,
        broker_id=broker_id,
        asset_id=ASSET_ID,
        date=date.fromisoformat(on),
        type=tx_type,
        quantity=D(quantity),
        amount=D(amount),
        currency="EUR",
        cost_basis_override=None if cost is None else D(cost),
        cost_basis_currency=None if cost is None else "EUR",
        related_transaction_id=related,
    )


def _buy(tx_id: int, qty: str, price: str, *, on: str, broker_id: int = BROKER_A) -> FifoInputTransaction:
    return _tx(tx_id, "BUY", qty, on=on, broker_id=broker_id, amount=f"-{D(qty) * D(price)}")


def _sell(tx_id: int, qty: str, price: str, *, on: str, broker_id: int = BROKER_A) -> FifoInputTransaction:
    return _tx(tx_id, "SELL", f"-{qty}", on=on, broker_id=broker_id, amount=f"{D(qty) * D(price)}")


def _adjustment(tx_id: int, qty: str, *, on: str, broker_id: int = BROKER_A, cost: str | None = None) -> FifoInputTransaction:
    return _tx(tx_id, "ADJUSTMENT", qty, on=on, broker_id=broker_id, cost=cost)


def _transfer(out_id: int, in_id: int, qty: str, *, out_on: str, in_on: str, out_broker: int, in_broker: int) -> list[FifoInputTransaction]:
    return [
        _tx(out_id, "TRANSFER", f"-{qty}", on=out_on, broker_id=out_broker, related=in_id),
        _tx(in_id, "TRANSFER", qty, on=in_on, broker_id=in_broker, related=out_id),
    ]


def _economic(tx_id: int, economic_type: str, amount: str, *, on: str, broker_id: int = BROKER_A) -> EconomicEvent:
    return EconomicEvent(
        transaction_id=tx_id,
        broker_id=broker_id,
        asset_id=ASSET_ID,
        date=date.fromisoformat(on),
        economic_type=economic_type,
        native_amount=D(amount),
        native_currency="EUR",
        target_amount=D(amount),
        target_currency="EUR",
    )


def _run(rows: list, method: LotMatchingMethod, *, shorting: dict[int, bool] | None = None, split_ratios: dict[int, Decimal] | None = None, economic_events: list[EconomicEvent] | None = None) -> FifoEngineResult:
    return run_fifo_lot_engine(
        rows,
        shorting or {},
        split_ratios_by_tx_id=split_ratios,
        # An incoming adjustment asks the market price of its day for its relative return; one is always there, so that
        # the only issues left are the replay's own.
        reference_price_lookup=lambda _asset_id, _day: ReferencePriceResolution(price=D("100"), source="exact"),
        economic_events=economic_events or (),
        target_currency="EUR",
        matching_method=method,
    )


def _closed(result: FifoEngineResult) -> dict[int, tuple[Decimal, Decimal | None]]:
    """Quantity closed and realized P&L of each lot that closed, by lot id."""
    closed: dict[int, tuple[Decimal, Decimal | None]] = {}
    for closure in result.closures:
        quantity, realized = closed.get(closure.lot_id, (D("0"), D("0")))
        closed[closure.lot_id] = (quantity + closure.quantity, None if realized is None or closure.realized_pnl is None else realized + closure.realized_pnl)
    return closed


def _open(result: FifoEngineResult) -> dict[int, Decimal]:
    return {lot.lot_id: lot.open_quantity for lot in result.lots}


def _identity(result: FifoEngineResult) -> list[tuple]:
    """What makes a lot the same lot in both methods: its id, opening, direction, quantity and cost."""
    return [(lot.lot_id, lot.opening_transaction_id, lot.opening_broker_id, lot.opening_date, lot.direction, lot.original_quantity, lot.original_cost, lot.currency) for lot in result.lots]


def _total_realized(result: FifoEngineResult) -> Decimal:
    return sum((lot.realized_pnl for lot in result.lots if lot.realized_pnl is not None), D("0"))


# --------------------------------------------------------------------------- #
# Rule 1 — the method of the replay, FIFO by default
# --------------------------------------------------------------------------- #


def test_the_engine_replays_in_fifo_without_a_method():
    """Rule 1: every caller of today passes no method and gets the FIFO replay, field by field."""
    rows = [_buy(1, "10", "100", on="2025-01-10"), _buy(2, "10", "120", on="2025-02-10"), _sell(3, "15", "130", on="2025-03-10")]

    default = run_fifo_lot_engine(rows, {}, target_currency="EUR")
    fifo = _run(rows, FIFO)

    assert (default.lots, default.closures, default.fragment_intervals, default.issues) == (fifo.lots, fifo.closures, fifo.fragment_intervals, fifo.issues)
    assert _closed(default) == {1: (D("10"), D("300")), 2: (D("5"), D("50"))}


def test_the_method_is_a_string_enum_of_fifo_and_lifo():
    """The values a request will carry (L3): exactly FIFO and LIFO."""
    assert [method.value for method in LotMatchingMethod] == ["FIFO", "LIFO"]
    assert LotMatchingMethod("LIFO") is LIFO


# --------------------------------------------------------------------------- #
# Rule 2 — LIFO takes the most recent lot first
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("method", "expected_closed", "expected_open"),
    [
        (FIFO, {1: (D("10"), D("300"))}, {1: D("0"), 2: D("10")}),
        (LIFO, {2: (D("10"), D("100"))}, {1: D("10"), 2: D("0")}),
    ],
    ids=["fifo-closes-january", "lifo-closes-february"],
)
def test_a_sale_closes_the_oldest_lot_in_fifo_and_the_most_recent_in_lifo(method, expected_closed, expected_open):
    """10 at 100 in January, 10 at 120 in February, sell 10 at 130 in March: FIFO realizes +300, LIFO +100."""
    rows = [_buy(1, "10", "100", on="2025-01-10"), _buy(2, "10", "120", on="2025-02-10"), _sell(3, "10", "130", on="2025-03-10")]

    result = _run(rows, method)

    assert (_closed(result), _open(result), result.issues) == (expected_closed, expected_open, [])


@pytest.mark.parametrize(
    ("method", "expected_closed", "expected_open"),
    [
        (FIFO, {1: (D("10"), D("300")), 2: (D("5"), D("100"))}, {1: D("0"), 2: D("5"), 3: D("10")}),
        (LIFO, {3: (D("10"), D("100")), 2: (D("5"), D("100"))}, {1: D("10"), 2: D("5"), 3: D("0")}),
    ],
    ids=["fifo", "lifo"],
)
def test_a_partial_sale_over_several_lots_walks_the_queue_from_its_end(method, expected_closed, expected_open):
    """Three lots (100, 110, 120), sell 15 at 130: LIFO closes the March lot whole and half of February's."""
    rows = [
        _buy(1, "10", "100", on="2025-01-10"),
        _buy(2, "10", "110", on="2025-02-10"),
        _buy(3, "10", "120", on="2025-03-10"),
        _sell(4, "15", "130", on="2025-04-10"),
    ]

    result = _run(rows, method)

    assert (_closed(result), _open(result), result.issues) == (expected_closed, expected_open, [])


@pytest.mark.parametrize(("method", "closed_lot"), [(FIFO, 1), (LIFO, 2)], ids=["fifo-lower-id", "lifo-higher-id"])
def test_two_lots_of_the_same_day_are_ordered_by_id(method, closed_lot):
    """Same opening date: the lot id breaks the tie, ascending in FIFO, descending in LIFO."""
    rows = [_buy(1, "10", "100", on="2025-01-10"), _buy(2, "10", "110", on="2025-01-10"), _sell(3, "10", "130", on="2025-02-10")]

    result = _run(rows, method)

    assert list(_closed(result)) == [closed_lot]


@pytest.mark.parametrize(
    ("method", "travelling_lot", "left_on_a"),
    [(FIFO, 1, {1: D("5"), 2: D("10")}), (LIFO, 2, {1: D("10"), 2: D("5")})],
    ids=["fifo-sends-january", "lifo-sends-february"],
)
def test_a_transfer_sends_the_lot_the_method_takes_and_the_lot_keeps_its_identity(method, travelling_lot, left_on_a):
    """D2: a departure takes from the queue like a sale. The lot that arrives on B keeps its id, purchase date and cost."""
    rows = [
        _buy(1, "10", "100", on="2025-01-10"),
        _buy(2, "10", "120", on="2025-02-10"),
        *_transfer(3, 4, "5", out_on="2025-03-10", in_on="2025-03-10", out_broker=BROKER_A, in_broker=BROKER_B),
    ]

    result = _run(rows, method)

    on_b = result.active_fragments(broker_id=BROKER_B)
    assert [(fragment.lot_id, fragment.quantity, fragment.unit_price) for fragment in on_b] == [(travelling_lot, D("5"), D("100") if travelling_lot == 1 else D("120"))]
    lot = result.get_lot(travelling_lot)
    assert (lot.opening_date, lot.opening_broker_id, lot.original_quantity, lot.original_cost) == (date(2025, travelling_lot, 10), BROKER_A, D("10"), D("1000") if travelling_lot == 1 else D("1200"))
    assert {fragment.lot_id: fragment.quantity for fragment in result.active_fragments(broker_id=BROKER_A)} == left_on_a
    assert result.issues == []


@pytest.mark.parametrize(
    ("method", "expected_closed"),
    [(FIFO, {1: (D("10"), D("200"))}), (LIFO, {2: (D("10"), D("100"))})],
    ids=["fifo", "lifo"],
)
def test_a_split_keeps_each_lots_cost_and_the_method_picks_the_lot_after_it(method, expected_closed):
    """A 2:1 split rescales both lots (20 at 50, 20 at 60) without changing their cost; a sale of 10 at 70 then closes
    January in FIFO (+200) and February in LIFO (+100)."""
    rows = [
        _buy(1, "10", "100", on="2025-01-10"),
        _buy(2, "10", "120", on="2025-02-10"),
        _adjustment(3, "20", on="2025-03-10"),
        _sell(4, "10", "70", on="2025-04-10"),
    ]

    result = _run(rows, method, split_ratios={3: D("2")})

    assert {lot.lot_id: (lot.original_cost, lot.original_quantity) for lot in result.lots} == {1: (D("1000"), D("20")), 2: (D("1200"), D("20"))}
    assert (_closed(result), result.issues) == (expected_closed, [])


@pytest.mark.parametrize(
    ("method", "expected_closed"),
    [(FIFO, {1: (D("10"), D("-100"))}), (LIFO, {2: (D("10"), D("100"))})],
    ids=["fifo-covers-january", "lifo-covers-february"],
)
def test_a_buy_covers_the_short_the_method_takes(method, expected_closed):
    """D2: two shorts (at 100 and at 120), a buy of 10 at 110 covers January in FIFO (−100) and February in LIFO (+100)."""
    rows = [_sell(1, "10", "100", on="2025-01-10"), _sell(2, "10", "120", on="2025-02-10"), _buy(3, "10", "110", on="2025-03-10")]

    result = _run(rows, method, shorting={BROKER_A: True})

    assert (_closed(result), result.issues) == (expected_closed, [])
    assert {lot.lot_id for lot in result.lots if lot.direction == "SHORT"} == {1, 2}


@pytest.mark.parametrize(
    ("method", "expected_closed"),
    [(FIFO, {1: (D("5"), D("-500"))}), (LIFO, {2: (D("5"), D("-600"))})],
    ids=["fifo", "lifo"],
)
def test_an_outgoing_adjustment_takes_the_lot_the_method_takes(method, expected_closed):
    """D2: an ADJUSTMENT of −5 leaves at no value (N78-1): it realizes the cost of the lot it takes as a loss."""
    rows = [_buy(1, "10", "100", on="2025-01-10"), _buy(2, "10", "120", on="2025-02-10"), _adjustment(3, "-5", on="2025-03-10")]

    result = _run(rows, method)

    assert (_closed(result), result.issues) == (expected_closed, [])


# --------------------------------------------------------------------------- #
# Rule 3 — within one day, inflows before outflows (D4, D4b)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("method", [FIFO, LIFO], ids=["fifo", "lifo"])
def test_a_sale_recorded_before_the_buy_of_its_day_does_not_fail_a_broker_without_shorting(method):
    """D4: SELL 5 (id 1) and BUY 10 (id 2) on the same day. The buy opens its lot first; the sale closes half of it."""
    rows = [_sell(1, "5", "110", on="2025-03-10"), _buy(2, "10", "100", on="2025-03-10")]

    result = _run(rows, method)

    assert (result.analysis_status, result.issues) == ("COMPLETE", [])
    assert (_closed(result), _open(result)) == ({2: (D("5"), D("50"))}, {2: D("5")})


@pytest.mark.parametrize(
    ("method", "expected_closed"),
    [(FIFO, {1: (D("10"), D("200")), 3: (D("5"), D("50"))}), (LIFO, {3: (D("10"), D("100")), 1: (D("5"), D("100"))})],
    ids=["fifo", "lifo"],
)
def test_a_same_day_buy_joins_the_queue_before_the_sale_of_its_day(method, expected_closed):
    """D4: 10 held since January; on one day SELL 15 (id 2) and BUY 10 (id 3). The buy comes first, so the sale has 20
    to take from: FIFO closes January and half of the day's lot, LIFO the day's lot and half of January."""
    rows = [_buy(1, "10", "90", on="2025-01-10"), _sell(2, "15", "110", on="2025-03-10"), _buy(3, "10", "100", on="2025-03-10")]

    result = _run(rows, method)

    assert (_closed(result), result.issues) == (expected_closed, [])


@pytest.mark.parametrize("method", [FIFO, LIFO], ids=["fifo", "lifo"])
def test_an_outgoing_adjustment_recorded_before_the_incoming_one_of_its_day_does_not_fail(method):
    """D4: ADJUSTMENT −5 (id 1) and ADJUSTMENT +5 at cost 100 (id 2) on the same day: the incoming one comes first."""
    rows = [_adjustment(1, "-5", on="2025-03-10"), _adjustment(2, "5", on="2025-03-10", cost="100")]

    result = _run(rows, method)

    assert result.issues == []
    assert _closed(result) == {2: (D("5"), D("-500"))}


@pytest.mark.parametrize("method", [FIFO, LIFO], ids=["fifo", "lifo"])
def test_a_same_day_short_on_a_broker_with_shorting_becomes_a_long_lot_with_the_same_realized(method):
    """D4b: SELL 10 at 110 (id 1) and BUY 10 at 100 (id 2) on one day. The buy opens a LONG lot (id 2) and the sale
    closes it: +100, the gain the short at 110 covered at 100 gave before L1. No SHORT lot is left."""
    rows = [_sell(1, "10", "110", on="2025-03-10"), _buy(2, "10", "100", on="2025-03-10")]

    result = _run(rows, method, shorting={BROKER_A: True})

    assert [(lot.lot_id, lot.direction, lot.open_quantity) for lot in result.lots] == [(2, "LONG", D("0"))]
    assert (_closed(result), _total_realized(result), result.issues) == ({2: (D("10"), D("100"))}, D("100"), [])


# --------------------------------------------------------------------------- #
# Rule 4 — D10: a lot is dated at its opening with the data the calculator has
# --------------------------------------------------------------------------- #


def _row(tx_id: int, tx_type: TransactionType, quantity: str, *, on: str, broker_id: int, amount: str = "0", cost: str | None = None, related: int | None = None) -> SimpleNamespace:
    """An ORM-free stand-in of a ``Transaction`` row, as the lots analysis reads one."""
    return SimpleNamespace(
        id=tx_id,
        broker_id=broker_id,
        asset_id=ASSET_ID,
        date=date.fromisoformat(on),
        type=tx_type,
        quantity=D(quantity),
        amount=D(amount),
        currency="EUR",
        cost_basis_override=None if cost is None else D(cost),
        cost_basis_currency=None if cost is None else "EUR",
        related_transaction_id=related,
    )


# January: buy 10 at 100 on A. February: buy 10 at 120 on B. April: move the 10 from A to B (the receiving leg carries
# A's Auto cost, 100). June: sell 5 at 130 on B.
_D10_BOOK = (
    _row(1, TransactionType.BUY, "10", on="2025-01-10", broker_id=BROKER_A, amount="-1000"),
    _row(2, TransactionType.BUY, "10", on="2025-02-10", broker_id=BROKER_B, amount="-1200"),
    _row(3, TransactionType.TRANSFER, "-10", on="2025-04-10", broker_id=BROKER_A, related=4),
    _row(4, TransactionType.TRANSFER, "10", on="2025-04-10", broker_id=BROKER_B, cost="100", related=3),
    _row(5, TransactionType.SELL, "-5", on="2025-06-10", broker_id=BROKER_B, amount="650"),
)


@pytest.mark.parametrize(
    ("method", "expected_closed"),
    [(FIFO, {1: (D("5"), D("150"))}), (LIFO, {2: (D("5"), D("50"))})],
    ids=["fifo-closes-january", "lifo-closes-february"],
)
def test_d10_with_every_broker_the_transferred_lot_keeps_its_purchase_date_in_the_arrival_queue(method, expected_closed):
    """D10, both brokers in scope: the January lot arrives on B in April but sits in B's queue as January. FIFO closes
    it (+150), LIFO closes February (+50)."""
    result = _run(list(_D10_BOOK), method)

    assert result.get_lot(1).opening_date == date(2025, 1, 10)
    assert (_closed(result), result.issues) == (expected_closed, [])


@pytest.mark.parametrize(
    ("method", "expected_closed"),
    [(FIFO, {2: (D("5"), D("50"))}), (LIFO, {4: (D("5"), D("150"))})],
    ids=["fifo-closes-february", "lifo-closes-the-arrival"],
)
def test_d10_seen_from_b_only_the_arrival_is_a_lot_born_on_its_day(method, expected_closed):
    """D10, B alone: the arrival reads as an ADJUSTMENT-in on its day at its own cost (J-10), lot 4 of April at 100.
    FIFO closes February (+50), LIFO closes the arrival (+150). The difference with the view of every broker is
    accepted (decision of 11/11)."""
    rows_on_b = [row for row in _D10_BOOK if row.broker_id == BROKER_B]
    reading = read_transfers_at_scope_boundary(
        rows_on_b,
        partners={3: TransferPartner(id=3, broker_id=BROKER_A, asset_id=ASSET_ID, type="TRANSFER", quantity=D("-10"), related_transaction_id=4)},
        scope_broker_ids={BROKER_B},
        price_series=build_asset_price_series(price_rows=[], transactions=[], split_linked_tx_ids=set(), asset_currency="EUR", quote_base_quantity=1),
        quote_base_quantity=1,
    )

    result = _run(reading.transactions, method)

    assert (result.get_lot(4).opening_date, result.get_lot(4).opening_unit_price) == (date(2025, 4, 10), D("100"))
    assert (_closed(result), result.issues) == (expected_closed, [])


# --------------------------------------------------------------------------- #
# Income and costs follow the lots each method closes
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("method", "sold_lot", "kept_lot"), [(FIFO, 1, 2), (LIFO, 2, 1)], ids=["fifo", "lifo"])
def test_income_and_costs_land_on_the_lots_the_method_closes_and_keeps(method, sold_lot, kept_lot):
    """A dividend of 20 while both lots are held goes 10 and 10 in both methods. The fee of the sale goes to the lot the
    sale closes; a dividend after the sale goes to the lot still open."""
    rows = [_buy(1, "10", "100", on="2025-01-10"), _buy(2, "10", "120", on="2025-02-10"), _sell(3, "10", "130", on="2025-04-10")]
    events = [
        _economic(90, "DIVIDEND", "20", on="2025-03-10"),
        _economic(91, "FEE", "-5", on="2025-04-10"),
        _economic(92, "DIVIDEND", "10", on="2025-05-10"),
    ]

    result = _run(rows, method, economic_events=events)

    accumulators = result.economic_accumulators_by_lot
    assert {lot_id: (acc.gross_income, acc.allocated_fees) for lot_id, acc in accumulators.items()} == {
        sold_lot: (D("10"), D("5")),
        kept_lot: (D("20"), D("0")),
    }
    assert (result.asset_orphan_income, result.asset_orphan_fees, result.issues) == (D("0"), D("0"), [])


# --------------------------------------------------------------------------- #
# Rule 5 — the same lots, the same total at a closed position
# --------------------------------------------------------------------------- #


def _mixed_book() -> list[FifoInputTransaction]:
    """Two brokers, A without shorting and B with: buys, a transfer in transit, a short opened and covered, and a
    same-day sale recorded before the incoming adjustment that feeds it. Everything is closed at the end.

    Long costs 1000 + 550 + 420 + 600 = 2570, long proceeds 840 + 1500 + 780 = 3120: +550; the short of 3 at 125
    covered at 115: +30. Total +580 whatever the method.
    """
    return [
        _buy(1, "10", "100", on="2025-01-05"),
        _buy(2, "5", "110", on="2025-02-05"),
        *_transfer(3, 4, "8", out_on="2025-03-05", in_on="2025-03-07", out_broker=BROKER_A, in_broker=BROKER_B),
        _buy(5, "4", "105", on="2025-03-20", broker_id=BROKER_B),
        _sell(6, "7", "120", on="2025-04-05"),
        _sell(7, "15", "125", on="2025-05-05", broker_id=BROKER_B),
        _buy(8, "3", "115", on="2025-06-05", broker_id=BROKER_B),
        _sell(11, "6", "130", on="2025-07-05"),
        _adjustment(12, "6", on="2025-07-05", cost="100"),
    ]


def test_both_methods_open_the_same_lots():
    """D12: the lots are the same in both methods, so a selection of lots survives a change of method."""
    fifo = _run(_mixed_book(), FIFO, shorting={BROKER_B: True})
    lifo = _run(_mixed_book(), LIFO, shorting={BROKER_B: True})

    assert _identity(fifo) == _identity(lifo)
    assert [lot_id for lot_id, *_ in _identity(fifo)] == [1, 2, 5, 7, 12]
    assert (fifo.issues, lifo.issues) == ([], [])


def test_a_position_closed_in_full_realizes_the_same_total_in_both_methods():
    """Per lot the methods differ; at a position closed in full the total realized is the same, +580."""
    fifo = _run(_mixed_book(), FIFO, shorting={BROKER_B: True})
    lifo = _run(_mixed_book(), LIFO, shorting={BROKER_B: True})

    assert _closed(fifo) != _closed(lifo)
    assert _total_realized(fifo) == _total_realized(lifo) == D("580")
    assert all(quantity == D("0") for quantity in _open(fifo).values()) and all(quantity == D("0") for quantity in _open(lifo).values())


# --------------------------------------------------------------------------- #
# L3a — what the lots analysis shares between the two methods
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("rows", "shorting", "code"),
    [
        pytest.param([_buy(1, "10", "100", on="2025-01-01"), _buy(2, "5", "110", on="2025-02-01"), _sell(3, "20", "120", on="2025-03-01")], {}, "FIFO_SOURCE_QUANTITY_MISSING", id="oversell"),
        pytest.param([_buy(1, "10", "100", on="2025-01-01"), _sell(2, "15", "90", on="2025-02-01"), _adjustment(3, "-1", on="2025-03-01")], {BROKER_A: True}, "SHORT_ADJUSTMENT_NOT_SUPPORTED", id="adjustment-out-on-a-short"),
        pytest.param(
            [_buy(1, "10", "100", on="2025-01-01"), _sell(2, "15", "90", on="2025-02-01"), *_transfer(3, 4, "2", out_on="2025-03-01", in_on="2025-03-02", out_broker=BROKER_A, in_broker=BROKER_B)],
            {BROKER_A: True},
            "SHORT_TRANSFER_NOT_SUPPORTED",
            id="transfer-out-of-a-short",
        ),
        pytest.param([_buy(1, "10", "100", on="2025-01-01"), _buy(2, "5", "110", on="2025-02-01"), _tx(3, "TRANSFER", "-4", on="2025-03-01", related=99)], {}, "TRANSFER_PAIR_MISSING", id="transfer-without-its-pair"),
    ],
)
def test_a_failed_replay_fails_in_both_methods_with_the_same_codes(rows, shorting, code):
    """The four codes that fail a replay (``fails_the_replay``) read the quantity of a broker, which does not depend on
    which lot an outflow closes: a book that fails in one method fails in the other, with the same failing issues. The
    analysis still keeps a status per method (opinion on L3, (b)); this pins why the two never differ today."""
    fifo, lifo = _run(rows, FIFO, shorting=shorting), _run(rows, LIFO, shorting=shorting)
    failing = [[(issue.code, issue.transaction_id) for issue in result.issues if fails_the_replay(issue.code)] for result in (fifo, lifo)]
    assert code in {failed_code for failed_code, _tx_id in failing[0]}, f"precondition: the book fails with {code}: {failing[0]}"
    assert (fifo.analysis_status, lifo.analysis_status) == ("FAILED", "FAILED")
    assert failing[0] == failing[1]
