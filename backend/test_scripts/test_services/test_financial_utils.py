"""
Unit tests for backend/app/utils/financial/wac_utils.py.

Pure math tests — no server, no DB, no async.
Tests compute_wac_from_txlist() and determine_target_currency().
"""

from datetime import date
from decimal import Decimal

from backend.app.utils.financial.wac_utils import (
    WACInputTX,
    compute_wac_from_txlist,
    determine_target_currency,
)
from backend.test_scripts.test_utils import print_section, print_success


def _tx(
    *,
    tx_id=None,
    type="BUY",
    dt="2026-01-05",
    quantity="10",
    unit_cost=None,
    currency="EUR",
    is_pending=False,
    is_split=False,
) -> WACInputTX:
    """Shorthand to build a WACInputTX."""
    return WACInputTX(
        tx_id=tx_id,
        type=type,
        date=date.fromisoformat(dt) if isinstance(dt, str) else dt,
        quantity=Decimal(quantity),
        unit_cost_converted=Decimal(unit_cost) if unit_cost is not None else None,
        original_currency=currency,
        is_pending=is_pending,
        is_split_linked=is_split,
    )


class TestComputeWacFromTxlist:
    """Tests for compute_wac_from_txlist (FU-1 to FU-8)."""

    # ------------------------------------------------------------------ FU-1
    def test_fu1_empty_list(self):
        """Empty list → WAC=0, qty=0."""
        print_section("FU-1 — Empty list")
        result = compute_wac_from_txlist([], "EUR")
        assert result.wac_amount == Decimal("0")
        assert result.pool_qty == Decimal("0")
        assert result.qualifying == []
        print_success("FU-1: Empty list → WAC=0, qty=0 ✓")

    # ------------------------------------------------------------------ FU-2
    def test_fu2_single_buy(self):
        """Single BUY → WAC = unit price."""
        print_section("FU-2 — Single BUY")
        txs = [_tx(tx_id=1, quantity="10", unit_cost="100")]
        result = compute_wac_from_txlist(txs, "EUR")
        assert result.wac_amount == Decimal("100")
        assert result.pool_qty == Decimal("10")
        assert len(result.qualifying) == 1
        assert result.qualifying[0].effect == "add"
        print_success("FU-2: Single BUY → WAC = 100 ✓")

    # ------------------------------------------------------------------ FU-3
    def test_fu3_buy_then_sell(self):
        """BUY + SELL → WAC unchanged, qty reduced."""
        print_section("FU-3 — BUY + SELL")
        txs = [
            _tx(tx_id=1, type="BUY", dt="2026-01-05", quantity="10", unit_cost="100"),
            _tx(tx_id=2, type="SELL", dt="2026-01-10", quantity="-3"),
        ]
        result = compute_wac_from_txlist(txs, "EUR")
        assert result.wac_amount == Decimal("100")
        assert result.pool_qty == Decimal("7")
        # First is 'add', second is 'reduce'
        assert result.qualifying[0].effect == "add"
        assert result.qualifying[1].effect == "reduce"
        print_success("FU-3: BUY + SELL → WAC unchanged, qty reduced ✓")

    # ------------------------------------------------------------------ FU-4
    def test_fu4_two_buys_weighted_average(self):
        """BUY 10@100 + BUY 5@200 → WAC = 2000/15 ≈ 133.33."""
        print_section("FU-4 — Two BUYs weighted average")
        txs = [
            _tx(tx_id=1, type="BUY", dt="2026-01-05", quantity="10", unit_cost="100"),
            _tx(tx_id=2, type="BUY", dt="2026-01-10", quantity="5", unit_cost="200"),
        ]
        result = compute_wac_from_txlist(txs, "EUR")
        expected = Decimal("2000") / Decimal("15")
        assert abs(result.wac_amount - expected) < Decimal("0.000001")
        assert result.pool_qty == Decimal("15")
        print_success("FU-4: Two BUYs → WAC ≈ 133.33 ✓")

    # ------------------------------------------------------------------ FU-5
    def test_fu5_same_date_buy_sell_additions_first(self):
        """Same-date BUY+SELL → additions processed first (no transient negative)."""
        print_section("FU-5 — Same-date additions first")
        txs = [
            # SELL before BUY in list order, but same date → BUY processed first
            _tx(tx_id=2, type="SELL", dt="2026-01-05", quantity="-3"),
            _tx(tx_id=1, type="BUY", dt="2026-01-05", quantity="10", unit_cost="100"),
        ]
        result = compute_wac_from_txlist(txs, "EUR")
        # BUY first: pool=10@100, then SELL 3 → pool=7@100
        assert result.wac_amount == Decimal("100")
        assert result.pool_qty == Decimal("7")
        print_success("FU-5: Same-date BUY+SELL → additions first ✓")

    # ------------------------------------------------------------------ FU-6
    def test_fu6_clamp_negative_to_zero(self):
        """Qty going negative (rounding) → clamped to (0, 0)."""
        print_section("FU-6 — Clamp negative to zero")
        txs = [
            _tx(tx_id=1, type="BUY", dt="2026-01-05", quantity="5", unit_cost="100"),
            _tx(tx_id=2, type="SELL", dt="2026-01-10", quantity="-10"),  # more than available
        ]
        result = compute_wac_from_txlist(txs, "EUR")
        assert result.wac_amount == Decimal("0")
        assert result.pool_qty == Decimal("0")
        print_success("FU-6: Negative qty clamped to 0 ✓")

    # ------------------------------------------------------------------ FU-7
    def test_fu7_transfer_in_with_override(self):
        """TRANSFER_IN with cost_basis_override → contributes to WAC."""
        print_section("FU-7 — TRANSFER_IN with override")
        txs = [
            _tx(tx_id=1, type="TRANSFER", dt="2026-01-05", quantity="10", unit_cost="50"),
        ]
        result = compute_wac_from_txlist(txs, "EUR")
        assert result.wac_amount == Decimal("50")
        assert result.pool_qty == Decimal("10")
        assert result.qualifying[0].effect == "add"
        print_success("FU-7: TRANSFER_IN with override → WAC = 50 ✓")

    # ------------------------------------------------------------------ FU-8
    def test_fu8_transfer_in_without_override(self):
        """TRANSFER_IN without cost_basis_override → add_zero_cost."""
        print_section("FU-8 — TRANSFER_IN without override")
        txs = [
            _tx(tx_id=1, type="BUY", dt="2026-01-03", quantity="10", unit_cost="100"),
            _tx(tx_id=2, type="TRANSFER", dt="2026-01-05", quantity="5", unit_cost=None),
        ]
        result = compute_wac_from_txlist(txs, "EUR")
        # BUY: pool=10@100. TRANSFER with zero cost: pool=15, WAC = (100*10 + 0*5)/15 = 66.67
        expected = Decimal("1000") / Decimal("15")
        assert abs(result.wac_amount - expected) < Decimal("0.000001")
        assert result.pool_qty == Decimal("15")
        # Second qualifying entry should be add_zero_cost
        assert result.qualifying[1].effect == "add_zero_cost"
        print_success("FU-8: TRANSFER_IN without override → add_zero_cost ✓")

    # ------------------------------------------------------------------ FU-11
    def test_fu11_pool_reset_after_full_sell(self):
        """BUY 10@100, SELL 10, BUY 5@300 → WAC resets to 300."""
        print_section("FU-11 — Pool reset after full sell")
        txs = [
            _tx(tx_id=1, type="BUY", dt="2026-01-05", quantity="10", unit_cost="100"),
            _tx(tx_id=2, type="SELL", dt="2026-01-10", quantity="-10"),
            _tx(tx_id=3, type="BUY", dt="2026-01-15", quantity="5", unit_cost="300"),
        ]
        result = compute_wac_from_txlist(txs, "EUR")
        assert result.wac_amount == Decimal("300")
        assert result.pool_qty == Decimal("5")
        print_success("FU-11: Pool reset → WAC = 300 ✓")

    # ------------------------------------------------------------------ FU-12
    def test_fu12_multiple_reductions_wac_stable(self):
        """Multiple SELLs do not change WAC, only reduce qty."""
        print_section("FU-12 — Multiple reductions WAC stable")
        txs = [
            _tx(tx_id=1, type="BUY", dt="2026-01-05", quantity="20", unit_cost="50"),
            _tx(tx_id=2, type="SELL", dt="2026-01-10", quantity="-5"),
            _tx(tx_id=3, type="SELL", dt="2026-01-12", quantity="-5"),
            _tx(tx_id=4, type="SELL", dt="2026-01-14", quantity="-5"),
        ]
        result = compute_wac_from_txlist(txs, "EUR")
        assert result.wac_amount == Decimal("50")
        assert result.pool_qty == Decimal("5")
        print_success("FU-12: Multiple reductions → WAC stable at 50 ✓")

    # ------------------------------------------------------------------ FU-13
    def test_fu13_forward_split_preserves_total_cost(self):
        """15@100 (cost 1500) + SPLIT-linked ADJUSTMENT +15 → 30@50 (cost 1500).

        Regression test for the WAC split-doubling bug (fifo-engine reports 1-6):
        the "auto" WAC fallback used to add the increment at the *current* WAC
        (100), doubling total cost to 3000 instead of preserving it at 1500.
        """
        print_section("FU-13 — Forward split preserves total cost")
        txs = [
            _tx(tx_id=1, type="BUY", dt="2026-01-05", quantity="15", unit_cost="100"),
            _tx(tx_id=2, type="ADJUSTMENT", dt="2026-02-01", quantity="15", is_split=True),
        ]
        result = compute_wac_from_txlist(txs, "EUR")
        assert result.pool_qty == Decimal("30")
        assert result.wac_amount == Decimal("50")
        assert result.wac_amount * result.pool_qty == Decimal("1500")
        assert result.qualifying[1].effect == "split_rescale"
        print_success("FU-13: 15@100 -[split 2:1]-> 30@50, cost 1500 preserved ✓")

    # ------------------------------------------------------------------ FU-14
    def test_fu14_reverse_split_preserves_total_cost(self):
        """30@50 (cost 1500) + SPLIT-linked ADJUSTMENT -15 → 15@100 (cost 1500).

        Regression test: a plain reduction (SELL semantics) would keep WAC at 50
        and drop total cost to 750 — a reverse split must preserve total cost by
        rescaling WAC upward instead.
        """
        print_section("FU-14 — Reverse split preserves total cost")
        txs = [
            _tx(tx_id=1, type="BUY", dt="2026-01-05", quantity="30", unit_cost="50"),
            _tx(tx_id=2, type="ADJUSTMENT", dt="2026-02-01", quantity="-15", is_split=True),
        ]
        result = compute_wac_from_txlist(txs, "EUR")
        assert result.pool_qty == Decimal("15")
        assert result.wac_amount == Decimal("100")
        assert result.wac_amount * result.pool_qty == Decimal("1500")
        assert result.qualifying[1].effect == "split_rescale"
        print_success("FU-14: 30@50 -[reverse split 1:2]-> 15@100, cost 1500 preserved ✓")

    # ------------------------------------------------------------------ FU-15
    def test_fu15_split_ignores_cost_basis_override(self):
        """SPLIT-linked ADJUSTMENT with a stray unit_cost_converted is still ignored.

        Even if a stale/manual cost_basis_override is present, is_split_linked
        must bypass it entirely — a split never carries economic cost.
        """
        print_section("FU-15 — Split ignores stray unit_cost_converted")
        txs = [
            _tx(tx_id=1, type="BUY", dt="2026-01-05", quantity="15", unit_cost="100"),
            _tx(tx_id=2, type="ADJUSTMENT", dt="2026-02-01", quantity="15", unit_cost="999", is_split=True),
        ]
        result = compute_wac_from_txlist(txs, "EUR")
        assert result.pool_qty == Decimal("30")
        assert result.wac_amount == Decimal("50")
        print_success("FU-15: Split rescale ignores stray unit_cost_converted (999) ✓")

    # ------------------------------------------------------------------ FU-16
    def test_fu16_split_then_sell_uses_post_split_wac(self):
        """15@100 -> split 2:1 -> 30@50 -> SELL 10 → WAC stays 50, qty 20."""
        print_section("FU-16 — Split then SELL uses post-split WAC")
        txs = [
            _tx(tx_id=1, type="BUY", dt="2026-01-05", quantity="15", unit_cost="100"),
            _tx(tx_id=2, type="ADJUSTMENT", dt="2026-02-01", quantity="15", is_split=True),
            _tx(tx_id=3, type="SELL", dt="2026-02-10", quantity="-10"),
        ]
        result = compute_wac_from_txlist(txs, "EUR")
        assert result.pool_qty == Decimal("20")
        assert result.wac_amount == Decimal("50")
        print_success("FU-16: Post-split SELL uses rescaled WAC (50) ✓")


class TestDetermineTargetCurrency:
    """Tests for determine_target_currency (FU-9 to FU-10).

    Current rule: currency of the most recent acquisition (by date).
    Fallback: asset_currency when no acquisitions exist.
    """

    # ------------------------------------------------------------------ FU-9
    def test_fu9_most_recent_wins(self):
        """Most recent acquisition currency wins."""
        print_section("FU-9 — Most recent currency wins")
        txs = [
            _tx(tx_id=1, quantity="10", currency="USD", dt="2025-01-01"),
            _tx(tx_id=2, quantity="10", currency="USD", dt="2025-02-01"),
            _tx(tx_id=3, quantity="10", currency="EUR", dt="2025-03-01"),
        ]
        result = determine_target_currency(txs, "USD")
        assert result == "EUR", f"Expected EUR (most recent), got {result}"
        print_success("FU-9: Most recent (EUR) wins ✓")

    # ------------------------------------------------------------------ FU-10
    def test_fu10_fallback_asset_currency(self):
        """No acquisitions → asset_currency fallback."""
        print_section("FU-10 — No acquisitions → asset_currency")
        txs = [
            _tx(tx_id=1, quantity="-5", currency="USD", dt="2025-01-01"),
        ]
        result = determine_target_currency(txs, "EUR")
        assert result == "EUR", f"Expected EUR (asset_currency fallback), got {result}"
        print_success("FU-10: No acquisitions → asset_currency (EUR) ✓")
