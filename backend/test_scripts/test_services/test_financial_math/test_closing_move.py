"""MF-CB — ``holding_window.closing_move(moves, dust=QUANTITY_DUST_THRESHOLD) -> QuantityMove | None``: the move of a
position's last close.

The last close is the one ``closed_position_window`` dates: the move after which the running quantity fell from above
``dust`` to ``dust`` or below for the last time. A split's ADJUSTMENT never closes (it rescales, as in
``closed_position_window``). Several moves on the closing day: the later in replay order (date, then ``order``, the
transaction id). None when the position never closed (never fell to the dust, or never opened); a position closed and
reopened keeps that close, as ``closed_position_window`` keeps its date. The row's ``closed_by`` reads it only on a fully
sold row (``AssetPeriodContribution.closed_by``, ``test_services/test_financial/test_closed_by.py``).

Each case also checks that the returned move's date is the last close ``closed_position_window`` gives on the same
stream (green on HEAD), so the two never disagree.

Red on HEAD 898bc9d15 by absence: the module is imported at collection, ``closing_move`` is read while each test runs
(``AttributeError: module ... has no attribute 'closing_move'``).

Pure: no DB, no server, no network. Runs in ``./dev.py test services financial-math``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import backend.app.services.financial_math.holding_window as holding_window
from backend.app.services.financial_math.holding_window import QuantityMove, closed_position_window
from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD

D1 = date(2024, 1, 10)
D2 = date(2024, 2, 10)
D3 = date(2024, 3, 10)
D4 = date(2024, 4, 10)


def _move(day: date, order: int, quantity: str, split: bool = False) -> QuantityMove:
    return QuantityMove(date=day, order=order, quantity=Decimal(quantity), split=split)


def _closing(moves: list[QuantityMove], **kwargs) -> QuantityMove | None:
    found = holding_window.closing_move(moves, **kwargs)
    _opened, last_close = closed_position_window(moves, **kwargs)
    assert (found.date if found is not None else None) == last_close, f"closing_move {found} disagrees with closed_position_window's last close {last_close}"
    return found


class TestTheLastClose:
    def test_a_sale_to_zero_is_the_close(self):
        sale = _move(D2, 2, "-10")
        assert _closing([_move(D1, 1, "10"), sale]) == sale

    def test_two_partial_sales_the_second_closes(self):
        second = _move(D3, 3, "-4")
        assert _closing([_move(D1, 1, "10"), _move(D2, 2, "-6"), second]) == second

    def test_a_sale_to_a_dust_residual_closes(self):
        sale = _move(D2, 2, "-9.99999")  # leaves 0.00001, the threshold itself
        assert Decimal("10") - Decimal("9.99999") == QUANTITY_DUST_THRESHOLD
        assert _closing([_move(D1, 1, "10"), sale]) == sale

    def test_a_residual_just_above_the_dust_is_still_open(self):
        assert _closing([_move(D1, 1, "10"), _move(D2, 2, "-9.99998")]) is None

    def test_the_residual_sold_later_is_not_the_close(self):
        """The rule as ``closed_position_window`` states it: the close is the sale that fell to dust; a later move of the
        residual does not fall from above the dust, so it closes nothing."""
        sale = _move(D2, 2, "-9.999995")
        assert _closing([_move(D1, 1, "10"), sale, _move(D3, 3, "-0.000005")]) == sale

    def test_reopened_and_closed_again_the_later_close(self):
        later = _move(D4, 4, "-5")
        assert _closing([_move(D1, 1, "10"), _move(D2, 2, "-10"), _move(D3, 3, "5"), later]) == later

    def test_reopened_and_still_open_keeps_the_earlier_close(self):
        """As ``closed_position_window`` dates it: a position closed and reopened keeps its last close. The row reads
        ``closing_move`` only when it is fully sold, so an open row never shows it."""
        sale = _move(D2, 2, "-10")
        assert _closing([_move(D1, 1, "10"), sale, _move(D3, 3, "5")]) == sale

    def test_an_oversell_closes(self):
        oversell = _move(D2, 2, "-12")
        assert _closing([_move(D1, 1, "10"), oversell]) == oversell

    def test_the_dust_is_a_parameter(self):
        sale = _move(D2, 2, "-9.9")  # leaves 0.1
        moves = [_move(D1, 1, "10"), sale]
        assert _closing(moves) is None
        assert _closing(moves, dust=Decimal("0.1")) == sale


class TestNeverClosed:
    def test_still_open(self):
        assert _closing([_move(D1, 1, "10"), _move(D2, 2, "-4")]) is None

    def test_never_opened(self):
        assert _closing([]) is None

    def test_only_zero_moves(self):
        assert _closing([_move(D1, 1, "0"), _move(D2, 2, "0")]) is None


class TestASplitNeverCloses:
    def test_a_reverse_split_then_a_sale_the_sale_closes(self):
        sale = _move(D3, 3, "-1")
        assert _closing([_move(D1, 1, "10"), _move(D2, 2, "-9", split=True), sale]) == sale

    def test_a_reverse_split_to_dust_is_no_close(self):
        """10 units, a reverse split that leaves 0.000005: the quantity falls under the dust, but a split never closes."""
        assert _closing([_move(D1, 1, "10"), _move(D2, 2, "-9.999995", split=True)]) is None

    def test_a_reverse_split_to_zero_is_no_close(self):
        assert _closing([_move(D1, 1, "10"), _move(D2, 2, "-10", split=True)]) is None

    def test_the_same_move_without_the_split_flag_closes(self):
        adjustment = _move(D2, 2, "-10")
        assert _closing([_move(D1, 1, "10"), adjustment]) == adjustment


class TestSameDay:
    def test_two_exits_on_the_closing_day_the_later_by_order(self):
        later = _move(D2, 7, "-4")
        moves = [_move(D1, 1, "10"), _move(D2, 5, "-6"), later]
        assert _closing(moves) == later

    def test_the_order_decides_not_the_list_position(self):
        """``moves`` in replay order, as ``quantity_moves`` gives them: the move with the higher id closes."""
        moves = holding_window.quantity_moves(
            [_Tx(D1, 1, "10"), _Tx(D2, 9, "-4"), _Tx(D2, 5, "-6")],
            split_linked_ids=(),
        )
        found = _closing(moves)
        assert found is not None and found.order == 9

    def test_close_and_reopen_on_the_same_day_keeps_that_close(self):
        sale = _move(D2, 2, "-10")
        assert _closing([_move(D1, 1, "10"), sale, _move(D2, 3, "10")]) == sale

    def test_close_reopen_and_close_on_the_same_day_the_last(self):
        last = _move(D2, 4, "-10")
        assert _closing([_move(D1, 1, "10"), _move(D2, 2, "-10"), _move(D2, 3, "10"), last]) == last


class TestShare:
    def test_a_share_scales_the_dust(self):
        """At a 30 % share a residual of 0.00003 is 0.000009 of the owner's: dust, so the sale that leaves it closes."""
        moves = holding_window.quantity_moves([_Tx(D1, 1, "10"), _Tx(D2, 2, "-9.99997")], split_linked_ids=(), share=Decimal("0.3"))
        found = _closing(moves)
        assert found is not None and found.order == 2

    def test_a_zero_share_never_opens(self):
        """An owner at 0 %: every move is 0, the position never opens, so it never closes."""
        moves = holding_window.quantity_moves([_Tx(D1, 1, "10"), _Tx(D2, 2, "-10")], split_linked_ids=(), share=Decimal("0"))
        assert _closing(moves) is None


class _Tx:
    """The three attributes ``quantity_moves`` reads."""

    def __init__(self, day: date, tx_id: int, quantity: str) -> None:
        self.date = day
        self.id = tx_id
        self.quantity = Decimal(quantity)
