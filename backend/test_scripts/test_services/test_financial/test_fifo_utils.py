"""
Unit tests for backend/app/utils/financial/fifo_utils.py.

Pure math tests — no server, no DB, no async.
"""

from datetime import date
from decimal import Decimal

import pytest

from backend.app.utils.financial.fifo_utils import (
    FIFOTransactionInput,
    calculate_fifo_lots,
)


def _buy(id_: int, qty: str, price: str, dt: str) -> FIFOTransactionInput:
    return FIFOTransactionInput(id=id_, type="BUY", quantity=Decimal(qty), price=Decimal(price), date=date.fromisoformat(dt))


def _sell(id_: int, qty: str, price: str, dt: str) -> FIFOTransactionInput:
    return FIFOTransactionInput(id=id_, type="SELL", quantity=Decimal(qty), price=Decimal(price), date=date.fromisoformat(dt))


class TestFIFOLots:
    def test_single_buy_no_sell(self):
        """One buy → 1 open lot, 0 closed."""
        txns = [_buy(1, "100", "50", "2025-01-01")]
        result = calculate_fifo_lots(txns)
        assert len(result.open_lots) == 1
        assert len(result.closed_lots) == 0
        assert result.open_lots[0].remaining_quantity == Decimal("100")
        assert result.open_lots[0].buy_price == Decimal("50")
        assert result.total_realized_pnl == Decimal("0")
        assert result.total_unrealized_quantity == Decimal("100")

    def test_buy_then_full_sell(self):
        """Buy + full sell → 0 open, 1 closed."""
        txns = [
            _buy(1, "100", "50", "2025-01-01"),
            _sell(2, "100", "60", "2025-03-01"),
        ]
        result = calculate_fifo_lots(txns)
        assert len(result.open_lots) == 0
        assert len(result.closed_lots) == 1
        lot = result.closed_lots[0]
        assert lot.buy_transaction_id == 1
        assert lot.sell_transaction_id == 2
        assert lot.quantity == Decimal("100")
        assert lot.realized_pnl == Decimal("1000")  # (60-50) * 100
        assert result.total_realized_pnl == Decimal("1000")
        assert result.total_unrealized_quantity == Decimal("0")

    def test_buy_then_partial_sell(self):
        """Buy 100, sell 30 → 1 open (70 remaining), 1 closed (30 matched)."""
        txns = [
            _buy(1, "100", "50", "2025-01-01"),
            _sell(2, "30", "60", "2025-03-01"),
        ]
        result = calculate_fifo_lots(txns)
        assert len(result.open_lots) == 1
        assert result.open_lots[0].remaining_quantity == Decimal("70")
        assert result.open_lots[0].original_quantity == Decimal("100")
        assert len(result.closed_lots) == 1
        assert result.closed_lots[0].quantity == Decimal("30")
        assert result.closed_lots[0].realized_pnl == Decimal("300")  # (60-50)*30

    def test_two_buys_one_sell_fifo_order(self):
        """Two buys, one sell — FIRST lot consumed first (FIFO)."""
        txns = [
            _buy(1, "50", "100", "2025-01-01"),
            _buy(2, "50", "150", "2025-02-01"),
            _sell(3, "30", "200", "2025-03-01"),
        ]
        result = calculate_fifo_lots(txns)
        assert len(result.closed_lots) == 1
        # First lot (price=100) consumed first
        assert result.closed_lots[0].buy_transaction_id == 1
        assert result.closed_lots[0].buy_price == Decimal("100")
        assert result.closed_lots[0].quantity == Decimal("30")
        # Open lots: lot1 has 20 remaining, lot2 has 50 remaining
        assert len(result.open_lots) == 2
        open_by_id = {lot.buy_transaction_id: lot for lot in result.open_lots}
        assert open_by_id[1].remaining_quantity == Decimal("20")
        assert open_by_id[2].remaining_quantity == Decimal("50")

    def test_sell_spans_multiple_lots(self):
        """
        Sell that exhausts first lot and partially consumes second.

        Lots: [BUY 50 @ 100, BUY 50 @ 150]
        Sell 70 @ 200:
          → consume 50 from lot1 (closed lot: qty=50)
          → consume 20 from lot2 (closed lot: qty=20)
        Open: lot2 with 30 remaining
        """
        txns = [
            _buy(1, "50", "100", "2025-01-01"),
            _buy(2, "50", "150", "2025-02-01"),
            _sell(3, "70", "200", "2025-03-01"),
        ]
        result = calculate_fifo_lots(txns)

        assert len(result.open_lots) == 1
        assert result.open_lots[0].buy_transaction_id == 2
        assert result.open_lots[0].remaining_quantity == Decimal("30")

        assert len(result.closed_lots) == 2
        closed_by_buy = {lot.buy_transaction_id: lot for lot in result.closed_lots}
        assert closed_by_buy[1].quantity == Decimal("50")
        assert closed_by_buy[2].quantity == Decimal("20")

        # P&L: lot1 (200-100)*50=5000, lot2 (200-150)*20=1000 → total=6000
        assert result.total_realized_pnl == Decimal("6000")

    def test_realized_pnl_calculation(self):
        """Verify realized P&L = (sell_price - buy_price) * quantity."""
        txns = [
            _buy(1, "10", "100", "2025-01-01"),
            _sell(2, "10", "130", "2025-06-01"),
        ]
        result = calculate_fifo_lots(txns)
        assert result.closed_lots[0].realized_pnl == Decimal("300")  # (130-100)*10

    def test_negative_pnl_on_loss(self):
        """Sell at lower price → negative realized P&L."""
        txns = [
            _buy(1, "10", "100", "2025-01-01"),
            _sell(2, "10", "80", "2025-06-01"),
        ]
        result = calculate_fifo_lots(txns)
        assert result.closed_lots[0].realized_pnl == Decimal("-200")  # (80-100)*10
        assert result.total_realized_pnl == Decimal("-200")

    def test_oversell_raises_error(self):
        """Selling more than owned → ValueError."""
        txns = [
            _buy(1, "50", "100", "2025-01-01"),
            _sell(2, "60", "120", "2025-03-01"),  # only 50 available
        ]
        with pytest.raises(ValueError, match="exceeds available"):
            calculate_fifo_lots(txns)

    def test_no_transactions(self):
        """Empty input → empty result."""
        result = calculate_fifo_lots([])
        assert result.open_lots == []
        assert result.closed_lots == []
        assert result.total_realized_pnl == Decimal("0")
        assert result.total_unrealized_quantity == Decimal("0")

    def test_non_buy_sell_transactions_ignored(self):
        """Transaction types other than BUY/SELL are silently ignored."""
        txns = [
            FIFOTransactionInput(id=1, type="DIVIDEND", quantity=Decimal("5"), price=Decimal("1"), date=date(2025, 1, 1)),
            _buy(2, "100", "50", "2025-01-15"),
        ]
        result = calculate_fifo_lots(txns)
        assert len(result.open_lots) == 1
        assert result.open_lots[0].buy_transaction_id == 2

    def test_complex_scenario(self):
        """
        5 BUY + 3 SELL — verify FIFO matching across multiple lots.

        Transactions (chronological):
          B1: buy 20 @ 10
          B2: buy 30 @ 12
          S1: sell 25 → consume 20 from B1 + 5 from B2 (B2 has 25 remaining)
          B3: buy 40 @ 15
          S2: sell 30 → consume 25 from B2 + 5 from B3 (B3 has 35 remaining)
          B4: buy 10 @ 18
          S3: sell 10 → consume 10 from B3 (B3 has 25 remaining, B4 untouched)
          B5: buy 15 @ 20

        Final open lots: B3(25), B4(10), B5(15) → total_unrealized = 50
        """
        txns = [
            _buy(1, "20", "10", "2025-01-01"),   # B1
            _buy(2, "30", "12", "2025-01-10"),   # B2
            _sell(3, "25", "15", "2025-02-01"),  # S1: B1(20) + B2(5)
            _buy(4, "40", "15", "2025-03-01"),   # B3
            _sell(5, "30", "18", "2025-04-01"),  # S2: B2(25) + B3(5)
            _buy(6, "10", "18", "2025-05-01"),   # B4
            _sell(7, "10", "20", "2025-06-01"),  # S3: B3(10)
            _buy(8, "15", "20", "2025-07-01"),   # B5
        ]
        result = calculate_fifo_lots(txns)

        assert result.total_unrealized_quantity == Decimal("50")
        open_by_id = {lot.buy_transaction_id: lot for lot in result.open_lots}
        assert open_by_id[4].remaining_quantity == Decimal("25")  # B3 had 40, sold 5+10=15
        assert open_by_id[6].remaining_quantity == Decimal("10")  # B4 untouched
        assert open_by_id[8].remaining_quantity == Decimal("15")  # B5 untouched

        # Total closed lots: S1→2 lots, S2→2 lots, S3→1 lot = 5 closed lots
        assert len(result.closed_lots) == 5
