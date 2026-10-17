"""
MF-H (workstream MF, lot H) — the holding window of a position, one module in the house.

Module under test: ``backend/app/services/financial_math/holding_window.py``, new. Three functions:

* ``quantity_moves(transactions, split_linked_ids)``: the quantity stream of one (broker, asset) position, one
  ``QuantityMove(date, order, quantity, split)`` per transaction, sorted by (date, id) — an id of None orders as 0 —
  ``quantity`` None read as 0, ``split`` True only for a transaction whose id is in ``split_linked_ids`` (an id of
  None never);
* ``oldest_open_lot_date(moves)``: the opening date of the oldest FIFO lot still open, None when nothing is open;
* ``closed_position_window(moves, dust=QUANTITY_DUST_THRESHOLD)``: ``(first opening, last close)``, the last close
  being the date the running quantity last fell from above ``dust`` to ``dust`` or below.

They replace ``portfolio_service._oldest_open_lot_date`` and ``portfolio_service._closed_position_window`` (HEAD
45ae068cc), written out below as ``_head_oldest_open_lot_date`` and ``_head_closed_position_window``, verbatim but
for their names and type hints. One rule changes: the ADJUSTMENT of a stock split (a transaction linked to a SPLIT asset event)
rescales every open lot by ``(held + q) / held`` and keeps their dates, where HEAD opened a lot dated at the split
(``+q``) or consumed the oldest lots (``−q``). A split never opens nor closes a position in the window. An incoming
TRANSFER or ADJUSTMENT that is not a split still opens a lot dated at its arrival at that broker (D-MF2 (a)).

Green after MF-H, red on HEAD by absence: the module is imported while each test runs (``_holding_window()``),
never at module level, so the file collects on HEAD and every test fails there on ``ModuleNotFoundError``.

- ``TestParityOnSplitFreeStreams`` — on a corpus without splits the new functions give what HEAD's gave: each case
  pins the expected value, checks HEAD's algorithm gives it, then the new one. Same-day ordering by id, partial
  consumption, full close and reopen, transfer in and out, an ADJUSTMENT in, an oversell, a dust residual, quantities
  of None and 0;
- ``TestSplitRescalesTheOpenLots`` — the change: a forward split keeps the date, a reverse split keeps it with lots
  5 / 5, a split with nothing open is ignored, a split then a full sale leaves nothing open; the same +10 without
  the split link is still an acquisition. Each case names HEAD's answer next to the new one;
- ``TestClosedPositionWindowIgnoresASplit`` — a reverse split on a tiny position is no close, a split on nothing is
  no opening, a split then a full sale closes on the sale;
- ``TestQuantityMoves`` — replay order, the split flag, a quantity of None.

MF-A5 adds ``exits_in(moves, date_from, end)``: how many outgoing quantity moves the position had in
``(date_from, end]``, a split's aside — what a closed position's base must cover (``contributions.closed_position_base``).
``TestExitsIn``, red on HEAD by absence (AttributeError): the window's bounds (``date_from`` exclusive, ``end``
inclusive, no ``date_from`` = from the beginning), each outgoing move counted once even on the same day, splits and
incoming or zero moves never counted.

Pure: no database, no server, no network.
"""

from __future__ import annotations

import importlib
from collections import deque
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import ModuleType

import pytest

from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD

HOLDING_WINDOW_MODULE = "backend.app.services.financial_math.holding_window"

D1 = date(2024, 1, 2)
D2 = date(2024, 2, 5)
D3 = date(2024, 3, 4)
D4 = date(2024, 4, 2)
D5 = date(2024, 5, 6)


def _holding_window() -> ModuleType:
    """``financial_math/holding_window.py``, imported when a test runs: until MF-H it does not exist."""
    return importlib.import_module(HOLDING_WINDOW_MODULE)


@dataclass(frozen=True)
class _Tx:
    """What the window reads of a transaction: its date, its id (replay order within a day) and its signed quantity."""

    date: date
    id: int | None
    quantity: Decimal | None


def _tx(day: date, tx_id: int | None, quantity: str | None) -> _Tx:
    return _Tx(date=day, id=tx_id, quantity=None if quantity is None else Decimal(quantity))


# =============================================================================
# HEAD's algorithms (portfolio_service.py @ 45ae068cc), verbatim but for their names and type hints
# =============================================================================


def _head_oldest_open_lot_date(txns: list[_Tx]) -> date | None:
    """``portfolio_service._oldest_open_lot_date`` at HEAD: every positive move opens a lot, a split's too."""
    open_lots: deque[tuple[date, Decimal]] = deque()
    for tx in sorted(txns, key=lambda t: (t.date, t.id or 0)):
        qty = tx.quantity or Decimal("0")
        if qty > 0:
            open_lots.append((tx.date, qty))
        elif qty < 0:
            remaining = -qty
            while remaining > 0 and open_lots:
                lot_date, lot_qty = open_lots[0]
                if lot_qty > remaining:
                    open_lots[0] = (lot_date, lot_qty - remaining)
                    remaining = Decimal("0")
                else:
                    remaining -= lot_qty
                    open_lots.popleft()
    return open_lots[0][0] if open_lots else None


def _head_closed_position_window(txns: list[_Tx]) -> tuple[date | None, date | None]:
    """``portfolio_service._closed_position_window`` at HEAD: a split opens and closes like any other move."""
    open_date: date | None = None
    last_close: date | None = None
    running = Decimal("0")
    for tx in sorted(txns, key=lambda t: (t.date, t.id or 0)):
        qty = tx.quantity or Decimal("0")
        prev = running
        running += qty
        if qty > 0 and open_date is None:
            open_date = tx.date
        if qty < 0 and prev > QUANTITY_DUST_THRESHOLD and running <= QUANTITY_DUST_THRESHOLD:
            last_close = tx.date
    return open_date, last_close


def _oldest(txns: list[_Tx], split_ids: tuple[int, ...] = ()) -> date | None:
    module = _holding_window()
    return module.oldest_open_lot_date(module.quantity_moves(txns, set(split_ids)))


def _window(txns: list[_Tx], split_ids: tuple[int, ...] = ()) -> tuple[date | None, date | None]:
    module = _holding_window()
    return module.closed_position_window(module.quantity_moves(txns, set(split_ids)))


# =============================================================================
# Parity: on a stream without splits nothing changes
# =============================================================================

# name -> (transactions, often given out of order on purpose, expected oldest open lot date, expected window)
SPLIT_FREE_CORPUS: dict[str, tuple[list[_Tx], date | None, tuple[date | None, date | None]]] = {
    "empty": ([], None, (None, None)),
    "one-buy": ([_tx(D1, 1, "10")], D1, (D1, None)),
    # BUY 10, BUY 10, SELL 15: the first lot is gone, 5 left of the second.
    "partial-consumption": ([_tx(D3, 3, "-15"), _tx(D1, 1, "10"), _tx(D2, 2, "10")], D2, (D1, None)),
    # BUY 10, SELL 4, SELL 3: 3 left of the only lot.
    "partial-sales-of-one-lot": ([_tx(D2, 2, "-4"), _tx(D3, 3, "-3"), _tx(D1, 1, "10")], D1, (D1, None)),
    # BUY 10, SELL 10 (closed), BUY 5: the open lot is the reopening; the first opening and the close stay.
    "full-close-and-reopen": ([_tx(D3, 3, "5"), _tx(D2, 2, "-10"), _tx(D1, 1, "10")], D3, (D1, D2)),
    "full-close": ([_tx(D2, 2, "-10"), _tx(D1, 1, "10")], None, (D1, D2)),
    # Same day, ids out of list order: SELL (id 1) replays before BUY (id 2), so it consumes nothing and the BUY stays
    # open. In list order the BUY would be sold and nothing would be open.
    "same-day-sell-before-buy-by-id": ([_tx(D1, 2, "5"), _tx(D1, 1, "-5")], D1, (D1, None)),
    # BUY 5 on D1; on D2 SELL 5 (id 2) then BUY 5 (id 3): closed on D2 and reopened the same day.
    "same-day-close-and-reopen-by-id": ([_tx(D2, 3, "5"), _tx(D2, 2, "-5"), _tx(D1, 1, "5")], D2, (D1, D2)),
    # The other way round on D2: BUY 5 (id 2) then SELL 5 (id 3) — FIFO sells the D1 lot, never closed.
    "same-day-buy-before-sell-by-id": ([_tx(D2, 3, "-5"), _tx(D2, 2, "5"), _tx(D1, 1, "5")], D2, (D1, None)),
    # An id of None orders as 0: the SELL without id replays before the BUY id 1 of the same day.
    "id-none-orders-first": ([_tx(D1, 1, "5"), _tx(D1, None, "-5")], D1, (D1, None)),
    # A transfer in opens a lot dated at its arrival here (D-MF2 (a)); a transfer out consumes the oldest.
    "transfer-in-then-out": ([_tx(D3, 3, "-4"), _tx(D2, 2, "10"), _tx(D1, 1, "3")], D2, (D1, None)),
    "transfer-in-only": ([_tx(D2, 7, "10")], D2, (D2, None)),
    "transfer-out-whole-then-back": ([_tx(D1, 1, "10"), _tx(D2, 2, "-10"), _tx(D4, 4, "10")], D4, (D1, D2)),
    # An ADJUSTMENT in (not a split) opens a lot like a BUY.
    "adjustment-in": ([_tx(D1, 1, "10"), _tx(D2, 2, "5"), _tx(D3, 3, "-12")], D2, (D1, None)),
    # SELL more than held: every lot gone; the running quantity goes below zero, which counts as a close.
    "oversell": ([_tx(D1, 1, "10"), _tx(D2, 2, "-12")], None, (D1, D2)),
    # BUY 1, SELL 0.999998: a residual of 0.000002 is a lot still open, and a close for the window.
    "dust-residual": ([_tx(D1, 1, "1"), _tx(D2, 2, "-0.999998")], D1, (D1, D2)),
    # The tranches of a CROWDFUND redemption: 8 × 0.031102 + 0.751182 against 1 bought, 0.000002 left.
    "dust-residual-in-tranches": ([_tx(D1, 1, "1")] + [_tx(D2, 10 + index, "-0.031102") for index in range(8)] + [_tx(D3, 30, "-0.751182")], D1, (D1, D3)),
    # Quantities of None and 0 move nothing.
    "none-and-zero-quantities": ([_tx(D1, 1, None), _tx(D2, 2, "0"), _tx(D3, 3, "4")], D3, (D3, None)),
}


class TestParityOnSplitFreeStreams:
    @pytest.mark.parametrize("txns, expected_oldest, expected_window", list(SPLIT_FREE_CORPUS.values()), ids=list(SPLIT_FREE_CORPUS))
    def test_oldest_open_lot_date_is_heads(self, txns, expected_oldest, expected_window):
        """The expected date, from HEAD's algorithm and from the new one."""
        assert _head_oldest_open_lot_date(txns) == expected_oldest, "the case is not what HEAD gave: fix the corpus"
        assert _oldest(txns) == expected_oldest

    @pytest.mark.parametrize("txns, expected_oldest, expected_window", list(SPLIT_FREE_CORPUS.values()), ids=list(SPLIT_FREE_CORPUS))
    def test_closed_position_window_is_heads(self, txns, expected_oldest, expected_window):
        """The expected (first opening, last close), from HEAD's algorithm and from the new one."""
        assert _head_closed_position_window(txns) == expected_window, "the case is not what HEAD gave: fix the corpus"
        assert _window(txns) == expected_window

    @pytest.mark.parametrize("txns, expected_oldest, expected_window", list(SPLIT_FREE_CORPUS.values()), ids=list(SPLIT_FREE_CORPUS))
    def test_split_ids_of_other_transactions_change_nothing(self, txns, expected_oldest, expected_window):
        """Split ids that belong to no transaction of the stream leave it a split-free stream."""
        assert (_oldest(txns, split_ids=(998, 999)), _window(txns, split_ids=(998, 999))) == (expected_oldest, expected_window)

    def test_the_dust_is_a_parameter(self):
        """With no dust tolerance the residual of 0.000002 is no close; the default is the platform threshold."""
        module = _holding_window()
        moves = module.quantity_moves([_tx(D1, 1, "1"), _tx(D2, 2, "-0.999998")], set())

        assert module.closed_position_window(moves, dust=Decimal("0")) == (D1, None)
        assert module.closed_position_window(moves) == module.closed_position_window(moves, dust=QUANTITY_DUST_THRESHOLD) == (D1, D2)


# =============================================================================
# The change: a split rescales the open lots and keeps their dates
# =============================================================================


class TestSplitRescalesTheOpenLots:
    def test_a_forward_split_keeps_the_buy_date(self):
        """BUY 10 on D1, split +10 on D2, SELL 15 on D3: the 20 units are one lot of D1, 5 left of it.
        HEAD opened a lot of 10 on D2 and sold the D1 lot first: D2."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "10"), _tx(D3, 3, "-15")]

        assert _oldest(txns, split_ids=(2,)) == D1
        assert _head_oldest_open_lot_date(txns) == D2

    def test_a_reverse_split_keeps_the_buy_date_with_lots_halved(self):
        """BUY 10 on D1, BUY 10 on D2, split −10 on D3: lots of 5 (D1) and 5 (D2), so D1.
        HEAD consumed the D1 lot with the −10: D2."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "10"), _tx(D3, 3, "-10")]

        assert _oldest(txns, split_ids=(3,)) == D1
        assert _head_oldest_open_lot_date(txns) == D2

    @pytest.mark.parametrize(
        "sold, expected",
        [
            # 4.99 of the D1 lot of 5: 0.01 of it left.
            pytest.param("-4.99", D1, id="sell-less-than-the-first-lot"),
            # The whole D1 lot of 5: the D2 lot is next.
            pytest.param("-5", D2, id="sell-the-first-lot-exactly"),
            # 5 + 4.99: 0.01 of the D2 lot left.
            pytest.param("-9.99", D2, id="sell-into-the-second-lot"),
            pytest.param("-10", None, id="sell-everything"),
        ],
    )
    def test_the_reverse_split_lots_are_five_and_five(self, sold, expected):
        """After BUY 10 (D1), BUY 10 (D2), split −10 (D3), a SELL on D4 proves the lots are 5 and 5:
        the factor (20 − 10) / 20 = 0.5 applies to each lot."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "10"), _tx(D3, 3, "-10"), _tx(D4, 4, sold)]

        assert _oldest(txns, split_ids=(3,)) == expected

    def test_the_forward_split_factor_applies_to_every_lot(self):
        """BUY 10 (D1), BUY 30 (D2), split 3:1 +80 on D3: lots of 30 (D1) and 90 (D2). SELL 30 on D4 empties the D1
        lot exactly, SELL 29.99 leaves 0.01 of it."""
        stream = [_tx(D1, 1, "10"), _tx(D2, 2, "30"), _tx(D3, 3, "80")]

        assert _oldest(stream + [_tx(D4, 4, "-30")], split_ids=(3,)) == D2
        assert _oldest(stream + [_tx(D4, 4, "-29.99")], split_ids=(3,)) == D1

    def test_a_split_with_nothing_open_is_ignored(self):
        """A split +10 on D1 with nothing held opens nothing: alone, nothing is open; with a BUY on D2 after it, the
        BUY's lot is the oldest. HEAD opened a lot of 10 on D1."""
        alone = [_tx(D1, 1, "10")]
        then_buy = [_tx(D1, 1, "10"), _tx(D2, 2, "5")]

        assert _oldest(alone, split_ids=(1,)) is None
        assert _oldest(then_buy, split_ids=(1,)) == D2
        assert (_head_oldest_open_lot_date(alone), _head_oldest_open_lot_date(then_buy)) == (D1, D1)

    def test_a_split_after_a_full_close_is_ignored(self):
        """BUY 10, SELL 10, then a split +10 on D3 on nothing: still nothing open (HEAD: a lot of D3)."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "-10"), _tx(D3, 3, "10")]

        assert _oldest(txns, split_ids=(3,)) is None
        assert _head_oldest_open_lot_date(txns) == D3

    def test_a_split_then_a_full_sale_leaves_nothing_open(self):
        """BUY 10 (D1), split +10 (D2), SELL 20 (D3): nothing open, as on HEAD."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "10"), _tx(D3, 3, "-20")]

        assert _oldest(txns, split_ids=(2,)) is None
        assert _head_oldest_open_lot_date(txns) is None

    def test_a_reverse_split_that_takes_everything_leaves_nothing_open(self):
        """BUY 10 (D1), a split −10 (D2): no quantity left after it, so no lot."""
        assert _oldest([_tx(D1, 1, "10"), _tx(D2, 2, "-10")], split_ids=(2,)) is None

    def test_the_same_plus_ten_without_the_split_link_is_an_acquisition(self):
        """The control of the forward split: the same stream with no split id, the +10 of D2 opens a lot of D2 and
        the SELL 15 empties the D1 lot first — D2, as HEAD gave for every +10."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "10"), _tx(D3, 3, "-15")]

        assert _oldest(txns) == D2
        assert _oldest(txns, split_ids=(99,)) == D2


# =============================================================================
# closed_position_window: a split never opens nor closes
# =============================================================================


class TestClosedPositionWindowIgnoresASplit:
    def test_a_reverse_split_on_a_tiny_position_is_no_close(self):
        """BUY 0.00002 (D1), split 1:4 −0.000015 (D2): 0.000005 is left, under the dust threshold, but a split never
        closes — (D1, None). HEAD read it as a close on D2."""
        txns = [_tx(D1, 1, "0.00002"), _tx(D2, 2, "-0.000015")]
        assert Decimal("0.000005") <= QUANTITY_DUST_THRESHOLD < Decimal("0.00002"), "precondition: the split crosses the threshold"

        assert _window(txns, split_ids=(2,)) == (D1, None)
        assert _head_closed_position_window(txns) == (D1, D2)

    def test_a_split_on_nothing_is_no_opening(self):
        """A split +10 on D1 with nothing held, a BUY on D2: the position opens on D2. HEAD opened it on D1."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "5")]

        assert _window(txns, split_ids=(1,))[0] == D2
        assert _head_closed_position_window(txns)[0] == D1

    def test_a_split_then_a_full_sale_closes_on_the_sale(self):
        """BUY 10 (D1), split +10 (D2), SELL 20 (D3): (D1, D3), as on HEAD."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "10"), _tx(D3, 3, "-20")]

        assert _window(txns, split_ids=(2,)) == (D1, D3)
        assert _head_closed_position_window(txns) == (D1, D3)

    def test_a_reverse_split_then_a_full_sale_closes_on_the_sale(self):
        """BUY 10 (D1), split −5 (D2), SELL 5 (D3): (D1, D3). The −5 left 5, above the threshold, so HEAD gave the
        same."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "-5"), _tx(D3, 3, "-5")]

        assert _window(txns, split_ids=(2,)) == (D1, D3)
        assert _head_closed_position_window(txns) == (D1, D3)


# =============================================================================
# quantity_moves
# =============================================================================


class TestQuantityMoves:
    def test_replay_order_is_date_then_id(self):
        """Given out of order: by date, then by id within a day, an id of None as 0."""
        module = _holding_window()
        txns = [_tx(D2, 5, "1"), _tx(D1, 9, "2"), _tx(D1, 3, "3"), _tx(D1, None, "4")]

        moves = module.quantity_moves(txns, set())

        assert [(move.date, move.order, move.quantity) for move in moves] == [(D1, 0, Decimal("4")), (D1, 3, Decimal("3")), (D1, 9, Decimal("2")), (D2, 5, Decimal("1"))]

    def test_the_split_flag_follows_the_ids(self):
        """Only the ids given are splits; a transaction with no id never is, even with None among the ids."""
        module = _holding_window()
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "10"), _tx(D2, None, "3"), _tx(D3, 3, "-15")]

        moves = module.quantity_moves(txns, [2, None])

        assert [(move.order, move.split) for move in moves] == [(1, False), (0, False), (2, True), (3, False)]

    def test_a_quantity_of_none_is_zero(self):
        module = _holding_window()

        (move,) = module.quantity_moves([_tx(D1, 1, None)], set())

        assert move.quantity == Decimal("0") and isinstance(move.quantity, Decimal)
        assert move.split is False

    def test_no_transaction_no_move(self):
        assert _holding_window().quantity_moves([], {1, 2}) == []


# =============================================================================
# exits_in (MF-A5): the outgoing moves of a period
# =============================================================================


def _exits(txns: list[_Tx], date_from: date | None, end: date, split_ids: tuple[int, ...] = ()) -> int:
    module = _holding_window()
    return module.exits_in(module.quantity_moves(txns, set(split_ids)), date_from, end)


class TestExitsIn:
    # BUY 10 on D1, then one SELL of 1 on each of D2, D3, D4, D5.
    ONE_EXIT_A_DAY = [_tx(D1, 1, "10"), _tx(D2, 2, "-1"), _tx(D3, 3, "-1"), _tx(D4, 4, "-1"), _tx(D5, 5, "-1")]

    @pytest.mark.parametrize(
        ("date_from", "end", "expected"),
        [
            # (D2, D4]: the exit on D2 is the start state's, the one on D4 the period's.
            pytest.param(D2, D4, 2, id="from-exclusive-end-inclusive"),
            pytest.param(D1, D5, 4, id="all-four"),
            pytest.param(D3, D3, 0, id="empty-window"),
            pytest.param(D4, D5, 1, id="last-day-only"),
            pytest.param(D5, D5, 0, id="after-the-last-exit"),
            # No date_from: from the beginning.
            pytest.param(None, D3, 2, id="no-start"),
            pytest.param(None, D1, 0, id="no-start-before-any-exit"),
        ],
    )
    def test_the_window_bounds(self, date_from, end, expected):
        assert _exits(self.ONE_EXIT_A_DAY, date_from, end) == expected

    def test_every_outgoing_move_counts_once(self):
        """A SELL, a TRANSFER out and an ADJUSTMENT out on the same day: three exits — the quantity stream cannot tell
        them apart, and each must be covered by the base."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "-3"), _tx(D2, 3, "-3"), _tx(D2, 4, "-4")]

        assert _exits(txns, D1, D2) == 3

    def test_a_split_is_no_exit(self):
        """A reverse split (−10) between two SELLs: two exits. Without the split link the same −10 is a third."""
        txns = [_tx(D1, 1, "20"), _tx(D2, 2, "-5"), _tx(D3, 3, "-10"), _tx(D4, 4, "-5")]

        assert _exits(txns, D1, D4, split_ids=(3,)) == 2
        assert _exits(txns, D1, D4) == 3

    def test_incoming_and_zero_moves_are_no_exit(self):
        """BUYs, a TRANSFER in, a forward split and quantities of 0 or None: no exit."""
        txns = [_tx(D2, 1, "10"), _tx(D3, 2, "5"), _tx(D3, 3, "15"), _tx(D4, 4, "0"), _tx(D4, 5, None)]

        assert _exits(txns, D1, D5, split_ids=(3,)) == 0

    def test_no_move_no_exit(self):
        assert _holding_window().exits_in([], D1, D5) == 0
