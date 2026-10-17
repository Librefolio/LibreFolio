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
  consumption, full close and reopen, transfer in and out, an ADJUSTMENT in, an oversell, a dust residual (its window;
  its oldest open lot is MF-A7's, below), quantities of None and 0;
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

MF-A7 gives ``oldest_open_lot_date(moves, dust=QUANTITY_DUST_THRESHOLD)`` the threshold ``closed_position_window``
already has: walking the open lots oldest first, the date is that of the lot at which the accumulated open quantity
first exceeds ``dust``, None when the whole position holds ``dust`` or less — the residual a sale leaves is set aside.
Before it (HEAD 5726486bc) the first open lot counted whatever its quantity; on a split-free stream that is
``_head_oldest_open_lot_date``, and with ``dust=0`` it is the new function. The two corpus cases of a dust residual now
expect None (``DUST_SET_ASIDE_BY_MF_A7`` keeps HEAD's D1), their window unchanged.

- ``TestDustResidualIsNotAnOpenLot`` — red on HEAD: a residual of 0.000001 before a new BUY gives the BUY's date, a
  residual at the threshold itself (0.00001) or below with nothing after it gives None, the threshold applies to the
  accumulated quantity of the oldest lots (0.000006 + 0.000006 open past it on the second lot, 0.000006 + 0.000004 does
  not), a reverse split that shrinks an old lot to dust sets it aside; green on HEAD too: a residual of 0.000011 is an
  open lot, a forward split that lifts a residual of 0.000004 above the threshold keeps its date;
- ``TestTheDustIsAParameterOfTheOldestOpenLot`` — red on HEAD by absence (TypeError, no ``dust``): ``dust=0`` is HEAD's
  rule on every stream above and on the corpus, a larger dust sets more aside, the default is the platform threshold.

MF-A10 gives ``quantity_moves(transactions, split_linked_ids, share=Decimal("1"))`` the owner's share of the broker
(``native_cash.effective_share``): every quantity is scaled by it, as the engine scales its own (``daily_state``:
``tx.quantity * ctxn.share``), so the dust threshold the windows apply is the one the rows apply to the engine's
quantity. Before it (HEAD ab74aafbf) the moves carried the raw quantity: on a broker owned at s < 1 a residual in
(dust, dust / s] was dust for the row and an open lot for the window.

- ``TestQuantityMovesAtTheOwnersShare`` — red on HEAD by absence (TypeError, no ``share``): the share scales every
  quantity and keeps dates, order and split flags; J's case — BUY 10 (2015), SELL 9.999988, BUY 5 (2024): 0.000012
  left, 0.000006 at half — dates from the 2024 BUY at half and from 2015 at the whole broker; BUY 10, SELL 9.999988
  closes on the sale at half and never at the whole broker; the default share is the whole broker on the corpus; a
  split at half still rescales and keeps the dates; a share of 0 moves nothing, as the engine's; ``exits_in`` counts
  the same at any positive share.

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
    # BUY 1, SELL 0.999998: a residual of 0.000002 is a close for the window and, since MF-A7, no open lot — a residual
    # of dust or less is set aside (HEAD: the D1 lot still open, see DUST_SET_ASIDE_BY_MF_A7).
    "dust-residual": ([_tx(D1, 1, "1"), _tx(D2, 2, "-0.999998")], None, (D1, D2)),
    # The tranches of a CROWDFUND redemption: 8 × 0.031102 + 0.751182 against 1 bought, 0.000002 left — set aside too.
    "dust-residual-in-tranches": ([_tx(D1, 1, "1")] + [_tx(D2, 10 + index, "-0.031102") for index in range(8)] + [_tx(D3, 30, "-0.751182")], None, (D1, D3)),
    # Quantities of None and 0 move nothing.
    "none-and-zero-quantities": ([_tx(D1, 1, None), _tx(D2, 2, "0"), _tx(D3, 3, "4")], D3, (D3, None)),
}

# MF-A7: the corpus cases whose oldest open lot date departs from HEAD's, with HEAD's — a residual of dust or less set
# aside. Their window is still HEAD's; their new date is checked by TestDustResidualIsNotAnOpenLot.
DUST_SET_ASIDE_BY_MF_A7: dict[str, date] = {"dust-residual": D1, "dust-residual-in-tranches": D1}
OLDEST_PARITY_CORPUS = {name: case for name, case in SPLIT_FREE_CORPUS.items() if name not in DUST_SET_ASIDE_BY_MF_A7}


class TestParityOnSplitFreeStreams:
    @pytest.mark.parametrize("txns, expected_oldest, expected_window", list(OLDEST_PARITY_CORPUS.values()), ids=list(OLDEST_PARITY_CORPUS))
    def test_oldest_open_lot_date_is_heads(self, txns, expected_oldest, expected_window):
        """The expected date, from HEAD's algorithm and from the new one (the dust residuals aside: MF-A7)."""
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


# =============================================================================
# MF-A7: a dust residual is no open lot
# =============================================================================


def _oldest_with(txns: list[_Tx], dust: Decimal, split_ids: tuple[int, ...] = ()) -> date | None:
    module = _holding_window()
    return module.oldest_open_lot_date(module.quantity_moves(txns, set(split_ids)), dust=dust)


def _tiny_lots(credited: str) -> list[_Tx]:
    """BUY 1 (D1), SELL 0.999994 (D2): 0.000006 left of the D1 lot; an ADJUSTMENT in of ``credited`` (D3, a fractional
    credit) opens a second tiny lot; BUY 5 (D4) a third."""
    return [_tx(D1, 1, "1"), _tx(D2, 2, "-0.999994"), _tx(D3, 3, credited), _tx(D4, 4, "5")]


# Split-free streams whose oldest open lot date MF-A7 moves; HEAD gave D1 for each.
DUST_STREAMS: dict[str, list[_Tx]] = {
    # 0.000001 left of the D1 lot, then BUY 5 (D3).
    "residual-before-a-buy": [_tx(D1, 1, "10"), _tx(D2, 2, "-9.999999"), _tx(D3, 3, "5")],
    "residual-alone": [_tx(D1, 1, "10"), _tx(D2, 2, "-9.999999")],
    # 0.00001 left: the threshold itself.
    "residual-at-the-threshold": [_tx(D1, 1, "10"), _tx(D2, 2, "-9.99999")],
    "tiny-lots-past-the-threshold": _tiny_lots("0.000006"),
    "tiny-lots-at-the-threshold": _tiny_lots("0.000004"),
}


class TestDustResidualIsNotAnOpenLot:
    def test_a_dust_residual_before_a_new_buy_is_set_aside(self):
        """BUY 10 (D1), SELL 9.999999 (D2), BUY 5 (D3): the D1 lot keeps 0.000001, dust; the oldest lot past the threshold
        is the D3 BUY's. HEAD: D1, the residual's."""
        txns = DUST_STREAMS["residual-before-a-buy"]
        assert Decimal("10") - Decimal("9.999999") <= QUANTITY_DUST_THRESHOLD, "precondition: the residual is dust"

        assert _oldest(txns) == D3
        assert _head_oldest_open_lot_date(txns) == D1

    @pytest.mark.parametrize(
        "name, residual",
        [
            pytest.param("residual-alone", "0.000001", id="residual-below-the-threshold"),
            # The boundary: the threshold itself is dust or less, so set aside.
            pytest.param("residual-at-the-threshold", "0.00001", id="residual-at-the-threshold"),
        ],
    )
    def test_a_position_holding_only_dust_has_no_open_lot(self, name, residual):
        """BUY 10 (D1), then a SELL that leaves ``residual`` of the D1 lot (D2): nothing open, as closed_position_window
        reads the same residual as a close on D2. HEAD: the D1 lot."""
        txns = DUST_STREAMS[name]
        assert sum((tx.quantity for tx in txns), Decimal("0")) == Decimal(residual) <= QUANTITY_DUST_THRESHOLD, "precondition: the residual"

        assert _oldest(txns) is None
        assert _window(txns) == (D1, D2)
        assert _head_oldest_open_lot_date(txns) == D1

    @pytest.mark.parametrize("name", list(DUST_SET_ASIDE_BY_MF_A7))
    def test_the_corpus_dust_residuals_are_set_aside(self, name):
        """The corpus's 0.000002 left of the D1 lot, by one SELL or in tranches: nothing open. HEAD: the D1 lot."""
        txns, _expected_oldest, _expected_window = SPLIT_FREE_CORPUS[name]

        assert _oldest(txns) is None
        assert _head_oldest_open_lot_date(txns) == DUST_SET_ASIDE_BY_MF_A7[name]

    @pytest.mark.parametrize("then_buy", [pytest.param(False, id="alone"), pytest.param(True, id="before-a-new-buy")])
    def test_a_residual_just_above_the_threshold_is_an_open_lot(self, then_buy):
        """BUY 10 (D1), SELL 9.999989 (D2): 0.000011 is left, more than dust — the D1 lot is open, alone or before a
        BUY 5 on D3. The same on HEAD."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "-9.999989")] + ([_tx(D3, 3, "5")] if then_buy else [])
        assert Decimal("10") - Decimal("9.999989") > QUANTITY_DUST_THRESHOLD, "precondition: the residual is not dust"

        assert _oldest(txns) == D1
        assert _head_oldest_open_lot_date(txns) == D1

    @pytest.mark.parametrize(
        "name, expected",
        [
            # 0.000006, then 0.000006 + 0.000006 = 0.000012 > 0.00001: past the threshold on the D3 lot.
            pytest.param("tiny-lots-past-the-threshold", D3, id="past-the-threshold-on-the-second-lot"),
            # 0.000006, then 0.000006 + 0.000004 = 0.00001, the threshold itself: past it only on the D4 BUY.
            pytest.param("tiny-lots-at-the-threshold", D4, id="at-the-threshold-after-the-second-lot"),
        ],
    )
    def test_the_threshold_applies_to_the_accumulated_quantity(self, name, expected):
        """Open lots 0.000006 (D1), a credit (D3), 5 (D4), each tiny lot dust: the date is that of the lot at which the
        quantity accumulated from the oldest first exceeds the threshold — D3 when the credit is 0.000006, not the D4
        BUY as if each lot were tested alone. HEAD: D1 in both."""
        txns = DUST_STREAMS[name]
        assert max(Decimal("0.000006"), txns[2].quantity) <= QUANTITY_DUST_THRESHOLD, "precondition: each tiny lot is dust"

        assert _oldest(txns) == expected
        assert _head_oldest_open_lot_date(txns) == D1

    def test_a_forward_split_lifts_a_dust_residual_above_the_threshold(self):
        """BUY 10 (D1), SELL 9.999996 (D2): 0.000004 left, dust. A 10:1 split (ADJUSTMENT +0.000036, D3) rescales it to
        0.00004, more than dust, and keeps its date: the D1 lot is open, alone or before BUY 5 (D4). The same on HEAD."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "-9.999996"), _tx(D3, 3, "0.000036"), _tx(D4, 4, "5")]

        assert _oldest(txns[:3], split_ids=(3,)) == D1
        assert _oldest(txns, split_ids=(3,)) == D1

    def test_the_same_credit_without_the_split_link_is_a_tiny_lot_of_its_own(self):
        """The control of the forward split: without the link the +0.000036 opens a lot of D3, and 0.000004 + 0.000036
        exceeds the threshold there: D3. HEAD: D1, the residual's."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "-9.999996"), _tx(D3, 3, "0.000036"), _tx(D4, 4, "5")]

        assert _oldest(txns) == D3
        assert _head_oldest_open_lot_date(txns) == D1

    def test_a_reverse_split_shrinks_an_old_lot_to_dust(self):
        """BUY 1 (D1), SELL 0.99995 (D2): 0.00005 left, more than dust, so the D1 lot is open; BUY 10 (D3). A 1:10 split
        (ADJUSTMENT −9.000045, D4) rescales both lots by 1.000005 / 10.00005 = 0.1: 0.000005 of D1, now dust, and 1 of
        D3 — the D3 lot. HEAD: D1, the shrunken lot."""
        before_split = [_tx(D1, 1, "1"), _tx(D2, 2, "-0.99995"), _tx(D3, 3, "10")]
        txns = before_split + [_tx(D4, 4, "-9.000045")]
        assert _oldest(before_split) == D1, "precondition: 0.00005 is more than dust"

        assert _oldest(txns, split_ids=(4,)) == D3


class TestTheDustIsAParameterOfTheOldestOpenLot:
    @pytest.mark.parametrize("name", list(DUST_STREAMS))
    def test_no_tolerance_is_heads_rule_on_the_dust_streams(self, name):
        """``dust=0``: the first open lot whatever its quantity, HEAD's D1 on every stream MF-A7 moves."""
        txns = DUST_STREAMS[name]

        assert _oldest_with(txns, Decimal("0")) == _head_oldest_open_lot_date(txns) == D1

    @pytest.mark.parametrize("txns, expected_oldest, expected_window", list(SPLIT_FREE_CORPUS.values()), ids=list(SPLIT_FREE_CORPUS))
    def test_no_tolerance_is_heads_rule_on_the_corpus(self, txns, expected_oldest, expected_window):
        """``dust=0`` on the split-free corpus, its dust residuals included: HEAD's date on every case."""
        assert _oldest_with(txns, Decimal("0")) == _head_oldest_open_lot_date(txns)

    def test_no_tolerance_keeps_a_lot_a_reverse_split_shrank_to_dust(self):
        """The reverse split of TestDustResidualIsNotAnOpenLot with ``dust=0``: the D1 lot, 0.000005 of it, as on HEAD."""
        txns = [_tx(D1, 1, "1"), _tx(D2, 2, "-0.99995"), _tx(D3, 3, "10"), _tx(D4, 4, "-9.000045")]

        assert _oldest_with(txns, Decimal("0"), split_ids=(4,)) == D1

    @pytest.mark.parametrize(
        "dust, expected",
        [
            # 0.005 is left of the D1 lot: more than this dust.
            pytest.param("0.004999", D1, id="below-the-residual"),
            # The residual is this dust: set aside, the D3 BUY.
            pytest.param("0.005", D3, id="at-the-residual"),
            pytest.param("0.01", D3, id="above-the-residual"),
            # 0.005 + 5 = 5.005 open in all: more than this dust on the D3 lot, not more than the next.
            pytest.param("5.004999", D3, id="below-the-whole-position"),
            pytest.param("5.005", None, id="at-the-whole-position"),
        ],
    )
    def test_a_larger_dust_sets_more_aside(self, dust, expected):
        """BUY 10 (D1), SELL 9.995 (D2), BUY 5 (D3): 0.005 left of the D1 lot, an open lot at the platform threshold."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "-9.995"), _tx(D3, 3, "5")]
        assert _oldest(txns) == D1, "precondition: 0.005 is more than the platform's dust"

        assert _oldest_with(txns, Decimal(dust)) == expected

    @pytest.mark.parametrize("name", list(DUST_STREAMS))
    def test_the_default_is_the_platform_threshold(self, name):
        """No ``dust`` given: ``QUANTITY_DUST_THRESHOLD``, 0.00001, the threshold closed_position_window and the rows use."""
        txns = DUST_STREAMS[name]
        assert QUANTITY_DUST_THRESHOLD == Decimal("0.00001")

        assert _oldest(txns) == _oldest_with(txns, QUANTITY_DUST_THRESHOLD)


# =============================================================================
# MF-A10: the quantities at the owner's share of the broker
# =============================================================================

WHOLE = Decimal("1")
HALF = Decimal("0.5")
J_BUY = date(2015, 3, 2)
J_SALE = date(2015, 9, 1)
J_REBUY = date(2024, 4, 2)

# J's case: BUY 10 (2015), SELL 9.999988 (2015) — 0.000012 left of the 2015 lot, 0.000006 at half — then BUY 5 (2024).
J_RESIDUAL_THEN_BUY = [_tx(J_BUY, 1, "10"), _tx(J_SALE, 2, "-9.999988"), _tx(J_REBUY, 3, "5")]
# The same sale with nothing bought after it: closed at dust over the share, not at dust.
J_SOLD_DOWN = J_RESIDUAL_THEN_BUY[:2]


def _at_share(txns: list[_Tx], share: Decimal, split_ids: tuple[int, ...] = ()) -> list:
    return _holding_window().quantity_moves(txns, set(split_ids), share=share)


class TestQuantityMovesAtTheOwnersShare:
    def test_the_share_scales_every_quantity_and_keeps_the_rest(self):
        """At half: each quantity halved — a None as 0 — with the replay order (date, then id, None as 0) and the split
        flags of the whole broker's moves."""
        txns = [_tx(D2, 5, "-3"), _tx(D1, 9, "10"), _tx(D1, None, "4"), _tx(D3, 7, "10"), _tx(D4, 8, None)]

        whole = _holding_window().quantity_moves(txns, {7})
        half = _at_share(txns, HALF, split_ids=(7,))

        assert [(move.date, move.order, move.quantity, move.split) for move in half] == [
            (D1, 0, Decimal("2"), False),
            (D1, 9, Decimal("5"), False),
            (D2, 5, Decimal("-1.5"), False),
            (D3, 7, Decimal("5"), True),
            (D4, 8, Decimal("0"), False),
        ]
        assert [(move.date, move.order, move.split) for move in half] == [(move.date, move.order, move.split) for move in whole]
        assert [move.quantity for move in half] == [move.quantity * HALF for move in whole]

    def test_a_residual_dust_at_the_share_is_set_aside(self):
        """J's case: 0.000012 left of the 2015 lot is more than dust, 0.000006 — the owner's half of it — is not. At half
        the oldest lot past the threshold is the 2024 BUY's, as the row reads the engine's 0.000006 as not held; at the
        whole broker it is still the 2015 lot. HEAD's callers passed the raw quantity: 2015 at any share."""
        raw_residual = Decimal("10") - Decimal("9.999988")
        assert QUANTITY_DUST_THRESHOLD < raw_residual <= QUANTITY_DUST_THRESHOLD / HALF, "precondition: the residual is in (dust, dust / share]"
        module = _holding_window()

        assert module.oldest_open_lot_date(_at_share(J_RESIDUAL_THEN_BUY, HALF)) == J_REBUY, f"HEAD gave {J_BUY}"
        assert module.oldest_open_lot_date(_at_share(J_RESIDUAL_THEN_BUY, WHOLE)) == J_BUY
        assert _oldest(J_RESIDUAL_THEN_BUY) == J_BUY

    def test_a_position_closed_at_dust_over_the_share_closes_on_the_sale(self):
        """BUY 10, SELL 9.999988: at half 5 fall to 0.000006, dust — closed on the sale, nothing open. At the whole broker
        0.000012 stays, more than dust: never closed, the 2015 lot open. HEAD's callers: (J_BUY, None) at any share."""
        module = _holding_window()
        half = _at_share(J_SOLD_DOWN, HALF)

        assert module.closed_position_window(half) == (J_BUY, J_SALE), f"HEAD gave {(J_BUY, None)}"
        assert module.oldest_open_lot_date(half) is None, f"HEAD gave {J_BUY}"
        assert module.closed_position_window(_at_share(J_SOLD_DOWN, WHOLE)) == _window(J_SOLD_DOWN) == (J_BUY, None)
        assert module.oldest_open_lot_date(_at_share(J_SOLD_DOWN, WHOLE)) == J_BUY

    @pytest.mark.parametrize("txns, expected_oldest, expected_window", list(SPLIT_FREE_CORPUS.values()), ids=list(SPLIT_FREE_CORPUS))
    def test_the_default_share_is_the_whole_broker(self, txns, expected_oldest, expected_window):
        """No ``share`` given: the whole broker, the moves HEAD gave — on the corpus, its dates and windows unchanged."""
        module = _holding_window()
        default = module.quantity_moves(txns, set())

        assert module.quantity_moves(txns, set(), share=WHOLE) == default
        assert (module.oldest_open_lot_date(default), module.closed_position_window(default)) == (expected_oldest, expected_window)

    def test_a_forward_split_at_the_share_keeps_the_buy_date(self):
        """TestSplitRescalesTheOpenLots' forward split at half: BUY 5 (D1), split +5 (D2) doubles the D1 lot to 10, SELL
        7.5 (D3) leaves 2.5 of it — D1, as at the whole broker. A split and a full sale still close on the sale."""
        module = _holding_window()

        assert module.oldest_open_lot_date(_at_share([_tx(D1, 1, "10"), _tx(D2, 2, "10"), _tx(D3, 3, "-15")], HALF, split_ids=(2,))) == D1
        assert module.closed_position_window(_at_share([_tx(D1, 1, "10"), _tx(D2, 2, "10"), _tx(D3, 3, "-20")], HALF, split_ids=(2,))) == (D1, D3)

    @pytest.mark.parametrize(
        "sold, expected",
        [
            # 2.495 of the D1 lot of 2.5: 0.005 of it left, more than dust.
            pytest.param("-4.99", D1, id="sell-less-than-the-first-lot"),
            # The whole D1 lot of 2.5: the D2 lot is next.
            pytest.param("-5", D2, id="sell-the-first-lot-exactly"),
            pytest.param("-10", None, id="sell-everything"),
        ],
    )
    def test_a_reverse_split_at_the_share_halves_the_lots_and_keeps_their_dates(self, sold, expected):
        """TestSplitRescalesTheOpenLots' reverse split at half: BUY 5 (D1), BUY 5 (D2), split −5 (D3) → lots of 2.5 and
        2.5, the factor (10 − 5) / 10 the same as at the whole broker; a SELL on D4, at half too, proves it."""
        txns = [_tx(D1, 1, "10"), _tx(D2, 2, "10"), _tx(D3, 3, "-10"), _tx(D4, 4, sold)]

        assert _holding_window().oldest_open_lot_date(_at_share(txns, HALF, split_ids=(3,))) == expected
        assert _oldest(txns, split_ids=(3,)) == expected, "the same lots as at the whole broker"

    def test_a_zero_share_moves_nothing(self):
        """An owner's 0 % share: every quantity 0, so no lot is open, the position never opens nor closes and no unit
        leaves it — as the engine, where a 0 % share moves nothing (``daily_state``: ``tx_qty == 0``)."""
        module = _holding_window()
        txns = J_RESIDUAL_THEN_BUY + [_tx(J_REBUY, 4, "-2")]

        moves = _at_share(txns, Decimal("0"))

        assert [move.quantity for move in moves] == [Decimal("0")] * len(txns)
        assert module.oldest_open_lot_date(moves) is None
        assert module.closed_position_window(moves) == (None, None)
        assert module.exits_in(moves, None, J_REBUY) == 0

    @pytest.mark.parametrize("share", ["1", "0.5", "0.333333", "0.000001"])
    def test_exits_in_counts_the_same_at_any_positive_share(self, share):
        """An exit is an outgoing move whatever its size: TestExitsIn's streams count the same at any positive share."""
        module = _holding_window()
        cases = [
            (TestExitsIn.ONE_EXIT_A_DAY, D2, D4, ()),
            (TestExitsIn.ONE_EXIT_A_DAY, None, D5, ()),
            ([_tx(D1, 1, "10"), _tx(D2, 2, "-3"), _tx(D2, 3, "-3"), _tx(D2, 4, "-4")], D1, D2, ()),
            ([_tx(D1, 1, "20"), _tx(D2, 2, "-5"), _tx(D3, 3, "-10"), _tx(D4, 4, "-5")], D1, D4, (3,)),
        ]

        counts = [module.exits_in(_at_share(txns, Decimal(share), split_ids), date_from, end) for txns, date_from, end, split_ids in cases]

        assert counts == [_exits(txns, date_from, end, split_ids) for txns, date_from, end, split_ids in cases] == [2, 4, 3, 2]
