"""Unit tests for backend/app/services/fifo_lot_engine.py."""

from datetime import date
from decimal import Decimal

import pytest

from backend.app.services.fifo_lot_engine import (
    EconomicEvent,
    FifoInputTransaction,
    ReferencePriceResolution,
    run_fifo_lot_engine,
)

ASSET_ID = 101


def _d(value: str) -> Decimal:
    return Decimal(value)


def _tx(
    tx_id: int,
    tx_type: str,
    *,
    broker_id: int = 1,
    dt: str = "2025-01-01",
    quantity: str = "0",
    amount: str = "0",
    related_transaction_id: int | None = None,
    target_amount: str | None = None,
    target_currency: str | None = None,
    cost_basis_override: str | None = None,
    cost_basis_currency: str | None = None,
) -> FifoInputTransaction:
    return FifoInputTransaction(
        id=tx_id,
        broker_id=broker_id,
        asset_id=ASSET_ID,
        date=date.fromisoformat(dt),
        type=tx_type,
        quantity=_d(quantity),
        amount=_d(amount),
        currency="EUR",
        related_transaction_id=related_transaction_id,
        target_amount=_d(target_amount) if target_amount is not None else None,
        target_currency=target_currency,
        cost_basis_override=_d(cost_basis_override) if cost_basis_override is not None else None,
        cost_basis_currency=cost_basis_currency,
    )


def _buy(tx_id: int, qty: str, price: str, dt: str = "2025-01-01", broker_id: int = 1, target_amount: str | None = None) -> FifoInputTransaction:
    return _tx(tx_id, "BUY", broker_id=broker_id, dt=dt, quantity=qty, amount=f"-{_d(qty) * _d(price)}", target_amount=target_amount)


def _sell(tx_id: int, qty: str, price: str, dt: str = "2025-01-01", broker_id: int = 1, target_amount: str | None = None) -> FifoInputTransaction:
    return _tx(tx_id, "SELL", broker_id=broker_id, dt=dt, quantity=f"-{qty}", amount=f"{_d(qty) * _d(price)}", target_amount=target_amount)


def _adjustment(tx_id: int, qty: str, dt: str = "2025-01-01", broker_id: int = 1, cost_basis_override: str | None = None, cost_basis_currency: str | None = None) -> FifoInputTransaction:
    return _tx(tx_id, "ADJUSTMENT", broker_id=broker_id, dt=dt, quantity=qty, cost_basis_override=cost_basis_override, cost_basis_currency=cost_basis_currency)


def _transfer_pair(
    out_id: int,
    in_id: int,
    qty: str,
    *,
    out_broker_id: int,
    in_broker_id: int,
    out_date: str,
    in_date: str,
) -> tuple[FifoInputTransaction, FifoInputTransaction]:
    return (
        _tx(out_id, "TRANSFER", broker_id=out_broker_id, dt=out_date, quantity=f"-{qty}", related_transaction_id=in_id),
        _tx(in_id, "TRANSFER", broker_id=in_broker_id, dt=in_date, quantity=qty, related_transaction_id=out_id),
    )


def _run(
    txs: list[FifoInputTransaction],
    *,
    broker_shorting: dict[int, bool] | None = None,
    split_ratios_by_tx_id: dict[int, Decimal] | None = None,
    reference_prices: dict[tuple[int, str], ReferencePriceResolution] | None = None,
    economic_events: list[EconomicEvent] | None = None,
    target_currency: str = "",
):
    def lookup(asset_id: int, opened_at: date) -> ReferencePriceResolution | None:
        if reference_prices is None:
            return None
        return reference_prices.get((asset_id, opened_at.isoformat()))

    return run_fifo_lot_engine(
        txs,
        broker_shorting or {},
        split_ratios_by_tx_id=split_ratios_by_tx_id,
        reference_price_lookup=lookup,
        economic_events=economic_events or (),
        target_currency=target_currency,
    )


def _issue_codes(result) -> list[str]:
    return [issue.code for issue in result.issues]


def _income(
    tx_id: int,
    econ_type: str,
    amount: str,
    *,
    dt: str,
    broker_id: int = 1,
    native_currency: str = "EUR",
    target_amount: str | None = None,
    target_currency: str = "EUR",
) -> EconomicEvent:
    return EconomicEvent(
        transaction_id=tx_id,
        broker_id=broker_id,
        asset_id=ASSET_ID,
        date=date.fromisoformat(dt),
        economic_type=econ_type,
        native_amount=_d(amount),
        native_currency=native_currency,
        target_amount=_d(target_amount if target_amount is not None else amount),
        target_currency=target_currency,
    )


def _lot_income(result, opening_tx_id: int) -> Decimal:
    accumulator = result.economic_accumulators_by_lot.get(opening_tx_id)
    return accumulator.gross_income if accumulator is not None else _d("0")


def _cost(
    tx_id: int,
    econ_type: str,
    amount: str,
    *,
    dt: str,
    broker_id: int = 1,
    native_currency: str = "EUR",
    target_amount: str | None = None,
    target_currency: str = "EUR",
) -> EconomicEvent:
    """Build a FEE/TAX economic event. ``amount`` is the stored (negative) native amount."""
    return EconomicEvent(
        transaction_id=tx_id,
        broker_id=broker_id,
        asset_id=ASSET_ID,
        date=date.fromisoformat(dt),
        economic_type=econ_type,
        native_amount=_d(amount),
        native_currency=native_currency,
        target_amount=_d(target_amount if target_amount is not None else amount),
        target_currency=target_currency,
    )


def _fee(tx_id: int, amount: str, *, dt: str, **kwargs) -> EconomicEvent:
    return _cost(tx_id, "FEE", amount, dt=dt, **kwargs)


def _tax(tx_id: int, amount: str, *, dt: str, **kwargs) -> EconomicEvent:
    return _cost(tx_id, "TAX", amount, dt=dt, **kwargs)


def _lot_fees(result, opening_tx_id: int) -> Decimal:
    accumulator = result.economic_accumulators_by_lot.get(opening_tx_id)
    return accumulator.allocated_fees if accumulator is not None else _d("0")


def _lot_taxes(result, opening_tx_id: int) -> Decimal:
    accumulator = result.economic_accumulators_by_lot.get(opening_tx_id)
    return accumulator.allocated_taxes if accumulator is not None else _d("0")


def _sum_allocated_income(result) -> Decimal:
    return sum((acc.gross_income for acc in result.economic_accumulators_by_lot.values()), _d("0"))


def _sum_allocated_fees(result) -> Decimal:
    return sum((acc.allocated_fees for acc in result.economic_accumulators_by_lot.values()), _d("0"))


def _sum_allocated_taxes(result) -> Decimal:
    return sum((acc.allocated_taxes for acc in result.economic_accumulators_by_lot.values()), _d("0"))


def _group_contexts(result, economic_type: str) -> list[str]:
    contexts: list[str] = []
    for group in result.economic_allocation_groups:
        if group.economic_type == economic_type:
            contexts.extend(op.context for op in group.operation_allocations)
    return contexts


class TestBasicLongShort:
    def test_single_buy_opens_one_long_lot(self):
        result = _run([_buy(1, "10", "100")])

        lot = result.get_lot(1)
        assert lot.direction == "LONG"
        assert lot.open_quantity == _d("10")
        assert lot.opening_unit_price == _d("100")
        assert result.get_lot_states(1) == {"OPEN", "LONG"}
        assert result.active_fragments(lot_id=1)[0].fragment_id == "lot:1/origin:1"

    def test_buy_then_full_sell_closes_lot_with_pnl(self):
        result = _run(
            [
                _buy(1, "10", "100", dt="2025-01-01"),
                _sell(2, "10", "120", dt="2025-01-10"),
            ]
        )

        lot = result.get_lot(1)
        assert lot.open_quantity == _d("0")
        assert lot.realized_pnl == _d("200")
        assert result.get_lot_states(1) == {"CLOSED", "LONG"}
        assert len(result.closures) == 1
        assert result.closures[0].proceeds == _d("1200")

    def test_buy_then_full_sell_at_loss_records_negative_pnl(self):
        # Parity with legacy fifo_utils.test_negative_pnl_on_loss (P1-6 mapping, gap #7):
        # sell below buy price → negative realized P&L on both lot and closure.
        result = _run(
            [
                _buy(1, "10", "100", dt="2025-01-01"),
                _sell(2, "10", "80", dt="2025-06-01"),
            ]
        )

        lot = result.get_lot(1)
        assert lot.open_quantity == _d("0")
        assert lot.realized_pnl == _d("-200")
        assert result.get_lot_states(1) == {"CLOSED", "LONG"}
        assert len(result.closures) == 1
        assert result.closures[0].realized_pnl == _d("-200")
        assert result.closures[0].proceeds == _d("800")

    def test_buy_then_partial_sell_keeps_fragment_identity(self):
        result = _run(
            [
                _buy(1, "10", "100", dt="2025-01-01"),
                _sell(2, "4", "120", dt="2025-01-10"),
            ]
        )

        lot = result.get_lot(1)
        assert lot.open_quantity == _d("6")
        assert lot.realized_pnl == _d("80")
        assert result.get_lot_states(1) == {"PARTIALLY_CLOSED", "LONG"}
        history = [fragment for fragment in result.fragment_intervals if fragment.fragment_id == "lot:1/origin:1"]
        assert len(history) == 2
        assert history[0].quantity == _d("10")
        assert history[0].end_date == date(2025, 1, 10)
        assert history[1].quantity == _d("6")
        assert history[1].end_date is None
        assert result.closures[0].fragment_id == "lot:1/origin:1"

    def test_crossing_zero_sell_closes_long_then_opens_short(self):
        result = _run(
            [
                _buy(1, "5", "100", dt="2025-01-01"),
                _sell(2, "8", "120", dt="2025-01-10"),
            ],
            broker_shorting={1: True},
        )

        long_lot = result.get_lot(1)
        short_lot = result.get_lot(2)
        assert long_lot.open_quantity == _d("0")
        assert long_lot.realized_pnl == _d("100")
        assert short_lot.direction == "SHORT"
        assert short_lot.open_quantity == _d("3")
        assert short_lot.opening_unit_price == _d("120")
        assert result.get_lot_states(2) == {"OPEN", "SHORT"}

    def test_crossing_zero_buy_closes_short_then_opens_long(self):
        result = _run(
            [
                _sell(1, "5", "120", dt="2025-01-01", broker_id=1),
                _buy(2, "8", "100", dt="2025-01-10", broker_id=1),
            ],
            broker_shorting={1: True},
        )

        short_lot = result.get_lot(1)
        long_lot = result.get_lot(2)
        assert short_lot.open_quantity == _d("0")
        assert short_lot.realized_pnl == _d("100")
        assert long_lot.direction == "LONG"
        assert long_lot.open_quantity == _d("3")
        assert long_lot.opening_unit_price == _d("100")

    def test_sell_exceeding_long_without_shorting_emits_issue(self):
        result = _run(
            [
                _buy(1, "5", "100"),
                _sell(2, "8", "120", dt="2025-01-02"),
            ],
            broker_shorting={1: False},
        )

        assert result.get_lot(1).open_quantity == _d("0")
        assert "FIFO_SOURCE_QUANTITY_MISSING" in _issue_codes(result)
        assert len(result.lots) == 1


class TestAdjustmentFlows:
    @pytest.mark.parametrize(
        ("resolution", "expected_code", "expected_return"),
        [
            (ReferencePriceResolution(price=_d("40"), source="exact"), None, _d("0.25")),
            (ReferencePriceResolution(price=_d("40"), source="fallback"), "REFERENCE_PRICE_FALLBACK", _d("0.25")),
            (ReferencePriceResolution(price=None, source="unavailable"), "REFERENCE_PRICE_UNAVAILABLE", None),
        ],
    )
    def test_adjustment_plus_zero_cost_and_reference_policy(self, resolution, expected_code, expected_return):
        result = _run(
            [_adjustment(1, "5", dt="2025-01-01")],
            reference_prices={(ASSET_ID, "2025-01-01"): resolution},
        )

        lot = result.get_lot(1)
        assert lot.open_quantity == _d("5")
        assert lot.opening_unit_price == _d("0")
        assert lot.original_cost == _d("0")
        # relative_return was previously exposed by FifoEngineResult.relative_return_for_lot
        # (removed in Fase 0.4 as non-qbq). Recompute it inline from the reference
        # price the engine resolves onto the lot, so the resolution policy stays tested.
        ref = lot.reference_unit_price
        rel_return = None if ref is None or ref == _d("0") else (_d("50") / ref) - _d("1")
        assert rel_return == expected_return
        assert expected_code in _issue_codes(result) if expected_code else result.issues == []

    def test_adjustment_plus_with_cost_basis_override_opens_priced_lot(self):
        # A broker-snapshot import records the opening position as a positive ADJUSTMENT
        # carrying the per-unit WAC in cost_basis_override. The opened lot must reflect that
        # cost basis (not zero) so total_return is computable and the WAC-chart bubble renders.
        result = _run([_adjustment(1, "5", dt="2025-01-01", cost_basis_override="90", cost_basis_currency="EUR")])

        lot = result.get_lot(1)
        assert lot.open_quantity == _d("5")
        assert lot.opening_unit_price == _d("90")
        assert lot.original_cost == _d("450")

    def test_adjustment_minus_consumes_long_at_zero_proceeds(self):
        result = _run(
            [
                _buy(1, "10", "100"),
                _adjustment(2, "-4", dt="2025-01-03"),
            ]
        )

        lot = result.get_lot(1)
        assert lot.open_quantity == _d("6")
        assert lot.realized_pnl == _d("-400")
        assert result.closures[0].close_reason == "ADJUSTMENT_OUT"
        assert result.closures[0].proceeds == _d("0")

    def test_adjustment_minus_exceeding_long_emits_issue(self):
        result = _run(
            [
                _buy(1, "3", "100"),
                _adjustment(2, "-5", dt="2025-01-03"),
            ]
        )

        assert result.get_lot(1).open_quantity == _d("0")
        assert "FIFO_SOURCE_QUANTITY_MISSING" in _issue_codes(result)

    def test_adjustment_minus_against_short_emits_short_issue(self):
        result = _run(
            [
                _sell(1, "4", "90", dt="2025-01-01"),
                _adjustment(2, "-1", dt="2025-01-02"),
            ],
            broker_shorting={1: True},
        )

        assert result.get_lot(1).open_quantity == _d("4")
        assert "SHORT_ADJUSTMENT_NOT_SUPPORTED" in _issue_codes(result)


class TestTransfers:
    def test_full_transfer_moves_lot_to_destination(self):
        t_out, t_in = _transfer_pair(2, 3, "10", out_broker_id=1, in_broker_id=2, out_date="2025-01-05", in_date="2025-01-10")
        result = _run([_buy(1, "10", "100", dt="2025-01-01"), t_out, t_in])

        active = result.active_fragments(lot_id=1)
        assert len(active) == 1
        assert active[0].fragment_id == "lot:1/transfer:2/to:2"
        assert active[0].broker_id == 2
        transit = [fragment for fragment in result.fragment_intervals if fragment.fragment_id == "lot:1/transfer:2/transit"]
        assert len(transit) == 1
        assert transit[0].start_date == date(2025, 1, 5)
        assert transit[0].end_date == date(2025, 1, 10)

    def test_partial_transfer_keeps_source_remainder(self):
        t_out, t_in = _transfer_pair(2, 3, "4", out_broker_id=1, in_broker_id=2, out_date="2025-01-05", in_date="2025-01-10")
        result = _run([_buy(1, "10", "100", dt="2025-01-01"), t_out, t_in])

        active = result.active_fragments(lot_id=1)
        by_id = {fragment.fragment_id: fragment for fragment in active}
        assert by_id["lot:1/origin:1"].quantity == _d("6")
        assert by_id["lot:1/transfer:2/to:2"].quantity == _d("4")
        assert result.get_lot_states(1) == {"DISTRIBUTED", "LONG", "OPEN"}

    def test_return_transfer_back_to_origin(self):
        first_out, first_in = _transfer_pair(2, 3, "10", out_broker_id=1, in_broker_id=2, out_date="2025-01-05", in_date="2025-01-10")
        second_out, second_in = _transfer_pair(4, 5, "10", out_broker_id=2, in_broker_id=1, out_date="2025-01-12", in_date="2025-01-13")
        result = _run([_buy(1, "10", "100", dt="2025-01-01"), first_out, first_in, second_out, second_in])

        active = result.active_fragments(lot_id=1)
        assert len(active) == 1
        assert active[0].fragment_id == "lot:1/transfer:4/to:1"
        assert active[0].broker_id == 1
        assert active[0].quantity == _d("10")

    def test_chained_transfer_through_three_brokers(self):
        ab_out, ab_in = _transfer_pair(2, 3, "10", out_broker_id=1, in_broker_id=2, out_date="2025-01-05", in_date="2025-01-10")
        bc_out, bc_in = _transfer_pair(4, 5, "10", out_broker_id=2, in_broker_id=3, out_date="2025-01-12", in_date="2025-01-15")
        result = _run([_buy(1, "10", "100", dt="2025-01-01"), ab_out, ab_in, bc_out, bc_in])

        active = result.active_fragments(lot_id=1)
        assert len(active) == 1
        assert active[0].fragment_id == "lot:1/transfer:4/to:3"
        assert active[0].broker_id == 3
        assert active[0].quantity == _d("10")

    def test_transfer_with_reversed_leg_dates_uses_sign_for_direction(self):
        t_out, t_in = _transfer_pair(2, 3, "6", out_broker_id=1, in_broker_id=2, out_date="2025-01-10", in_date="2025-01-05")
        result = _run([_buy(1, "10", "100", dt="2025-01-01"), t_out, t_in])

        active = result.active_fragments(lot_id=1)
        by_id = {fragment.fragment_id: fragment for fragment in active}
        assert by_id["lot:1/origin:1"].quantity == _d("4")
        assert by_id["lot:1/transfer:2/to:2"].quantity == _d("6")
        transit = next(fragment for fragment in result.fragment_intervals if fragment.fragment_id == "lot:1/transfer:2/transit")
        assert transit.start_date == date(2025, 1, 5)
        assert transit.end_date == date(2025, 1, 10)

    def test_short_transfer_emits_unsupported_issue(self):
        t_out, t_in = _transfer_pair(2, 3, "2", out_broker_id=1, in_broker_id=2, out_date="2025-01-05", in_date="2025-01-10")
        result = _run([_sell(1, "5", "100", dt="2025-01-01"), t_out, t_in], broker_shorting={1: True})

        assert "SHORT_TRANSFER_NOT_SUPPORTED" in _issue_codes(result)
        assert result.active_fragments(broker_id=2) == []


class TestSplits:
    def test_forward_split_preserves_cost(self):
        result = _run(
            [_buy(1, "15", "100", dt="2025-01-01"), _adjustment(2, "15", dt="2025-01-10")],
            split_ratios_by_tx_id={2: _d("2")},
        )

        lot = result.get_lot(1)
        active = result.active_fragments(lot_id=1)[0]
        assert active.quantity == _d("30")
        assert active.unit_price == _d("50")
        assert lot.original_cost == _d("1500")
        assert active.quantity * active.unit_price == _d("1500")

    def test_reverse_split_preserves_cost(self):
        result = _run(
            [_buy(1, "30", "50", dt="2025-01-01"), _adjustment(2, "-15", dt="2025-01-10")],
            split_ratios_by_tx_id={2: _d("0.5")},
        )

        lot = result.get_lot(1)
        active = result.active_fragments(lot_id=1)[0]
        assert active.quantity == _d("15")
        assert active.unit_price == _d("100")
        assert lot.original_cost == _d("1500")
        assert active.quantity * active.unit_price == _d("1500")

    def test_split_applies_to_in_transit_fragment(self):
        t_out, t_in = _transfer_pair(2, 3, "10", out_broker_id=1, in_broker_id=2, out_date="2025-01-05", in_date="2025-01-10")
        split_tx = _adjustment(4, "10", dt="2025-01-07", broker_id=2)
        result = _run([_buy(1, "10", "100", dt="2025-01-01"), t_out, t_in, split_tx], split_ratios_by_tx_id={4: _d("2")})

        transit_history = [fragment for fragment in result.fragment_intervals if fragment.fragment_id == "lot:1/transfer:2/transit"]
        assert len(transit_history) == 2
        assert transit_history[0].quantity == _d("10")
        assert transit_history[0].end_date == date(2025, 1, 7)
        assert transit_history[1].quantity == _d("20")
        assert transit_history[1].unit_price == _d("50")
        active = result.active_fragments(lot_id=1)[0]
        assert active.fragment_id == "lot:1/transfer:2/to:2"
        assert active.quantity == _d("20")
        assert active.unit_price == _d("50")

    def test_split_only_transforms_broker_with_linked_transaction(self):
        move_out, move_in = _transfer_pair(3, 4, "5", out_broker_id=1, in_broker_id=2, out_date="2025-01-05", in_date="2025-01-06")
        split_tx = _adjustment(5, "10", dt="2025-01-10", broker_id=2)
        result = _run(
            [
                _buy(1, "10", "100", dt="2025-01-01", broker_id=1),
                _buy(2, "5", "80", dt="2025-01-02", broker_id=1),
                move_out,
                move_in,
                split_tx,
            ],
            split_ratios_by_tx_id={5: _d("2")},
        )

        lot1_fragments = result.active_fragments(lot_id=1)
        lot2_fragment = result.active_fragments(lot_id=2)[0]
        by_id = {fragment.fragment_id: fragment for fragment in lot1_fragments}
        assert by_id["lot:1/origin:1"].quantity == _d("5")
        assert by_id["lot:1/origin:1"].unit_price == _d("100")
        assert by_id["lot:1/transfer:3/to:2"].quantity == _d("10")
        assert by_id["lot:1/transfer:3/to:2"].unit_price == _d("50")
        assert lot2_fragment.broker_id == 1
        assert lot2_fragment.quantity == _d("5")
        assert lot2_fragment.unit_price == _d("80")

    def test_non_dividing_ratio_does_not_raise_on_decimal_rounding(self):
        """Regression: a 3:1 split (ratio doesn't divide evenly) must not crash.

        unit_price / 3 is a non-terminating decimal, truncated at the default
        28-digit Decimal context — recombining quantity*ratio * (unit_price/ratio)
        differs from the original cost by ~1E-25, not a real bug. The cost
        invariant check must tolerate this (see _COST_INVARIANT_TOLERANCE),
        not raise AssertionError on an ordinary, common split ratio.
        """
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01"), _adjustment(2, "20", dt="2025-01-10")],
            split_ratios_by_tx_id={2: _d("3")},
        )

        lot = result.get_lot(1)
        active = result.active_fragments(lot_id=1)[0]
        assert active.quantity == _d("30")
        assert lot.original_cost == _d("1000")
        assert abs(active.quantity * active.unit_price - _d("1000")) < _d("0.01")


class TestValuationAndReconciliation:
    def test_multi_lot_aggregation(self):
        result = _run(
            [
                _buy(1, "10", "100", dt="2025-01-01"),
                _buy(2, "5", "80", dt="2025-01-02"),
                _sell(3, "4", "110", dt="2025-01-03"),
            ]
        )

        # value_for_lot / aggregate_value were removed from the engine in Fase 0.4
        # (they multiplied open_quantity * market_price WITHOUT quote_base_quantity,
        # a latent ×qbq bug for any future consumer). Market valuation is a service
        # concern; here we recompute the same LONG valuation locally from the raw
        # lot fields to keep the multi-lot aggregation invariant covered.
        def _long_val(lot_id: int, market_price: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
            lot = result.get_lot(lot_id)
            open_value = lot.open_quantity * market_price
            proceeds = lot.cumulative_proceeds
            total_value = open_value + proceeds  # every lot in this scenario is LONG
            pnl = total_value - lot.original_cost
            return open_value, proceeds, total_value, lot.original_cost, pnl

        lot1_ov, lot1_pr, lot1_tv, lot1_oc, lot1_pnl = _long_val(1, _d("120"))
        lot2_ov, lot2_pr, lot2_tv, lot2_oc, lot2_pnl = _long_val(2, _d("120"))
        assert lot1_ov == _d("720")
        assert lot1_pr == _d("440")
        assert lot1_tv == _d("1160")
        assert lot1_pnl == _d("160")
        assert lot2_ov == _d("600")
        assert lot2_pnl == _d("200")
        # Aggregate across lots 1 and 2 (previously result.aggregate_value).
        assert lot1_ov + lot2_ov == _d("1320")
        assert lot1_pr + lot2_pr == _d("440")
        assert lot1_tv + lot2_tv == _d("1760")
        assert lot1_oc + lot2_oc == _d("1400")
        assert lot1_pnl + lot2_pnl == _d("360")


class TestAssetIncomeAllocation:
    """Engine economic stage (Fase 1): DIVIDEND/INTEREST allocated to D-1 holdings.

    Eligibility is the open LONG quantity as of ``date - 1`` (D-1 semantics), scoped to the
    paying broker and transfer-aware (in-transit counts for its SOURCE broker). Pools with no
    eligible lot become orphan income and raise ASSET_INCOME_NO_ELIGIBLE_LOTS (DEGRADED).
    """

    def test_dividend_pro_rata_to_open_lots(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "30", "100", dt="2025-01-05")],
            economic_events=[_income(90, "DIVIDEND", "360", dt="2025-01-20")],
            target_currency="EUR",
        )
        assert _lot_income(result, 1) == _d("90")
        assert _lot_income(result, 2) == _d("270")
        assert result.asset_orphan_income == _d("0")
        assert _issue_codes(result) == []

    def test_same_day_buy_lot_excluded_at_d_minus_1(self):
        # The lot opened on the income date is not yet held as of D-1 -> gets nothing.
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "5", "100", dt="2025-01-20")],
            economic_events=[_income(90, "DIVIDEND", "100", dt="2025-01-20")],
            target_currency="EUR",
        )
        assert _lot_income(result, 1) == _d("100")
        assert _lot_income(result, 2) == _d("0")

    def test_same_day_sell_lot_still_eligible_at_d_minus_1(self):
        # A lot sold on the income date was still held as of D-1 -> remains eligible.
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01"), _sell(2, "10", "120", dt="2025-01-20")],
            economic_events=[_income(90, "DIVIDEND", "50", dt="2025-01-20")],
            target_currency="EUR",
        )
        assert _lot_income(result, 1) == _d("50")
        assert result.asset_orphan_income == _d("0")

    def test_income_scoped_to_paying_broker(self):
        # Directa 30 / IBKR 70, dividend paid on Directa -> only the Directa lot is credited.
        result = _run(
            [_buy(1, "30", "100", dt="2025-01-01", broker_id=1), _buy(2, "70", "100", dt="2025-01-01", broker_id=2)],
            economic_events=[_income(90, "DIVIDEND", "100", dt="2025-01-20", broker_id=1)],
            target_currency="EUR",
        )
        assert _lot_income(result, 1) == _d("100")
        assert _lot_income(result, 2) == _d("0")

    def test_no_eligible_lots_becomes_orphan_income(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01"), _sell(2, "10", "120", dt="2025-01-05")],
            economic_events=[_income(90, "DIVIDEND", "50", dt="2025-01-20")],
            target_currency="EUR",
        )
        assert _lot_income(result, 1) == _d("0")
        assert result.asset_orphan_income == _d("50")
        assert "ASSET_INCOME_NO_ELIGIBLE_LOTS" in _issue_codes(result)
        assert result.analysis_status == "DEGRADED"

    def test_income_on_source_broker_during_transit(self):
        t_out, t_in = _transfer_pair(2, 3, "10", out_broker_id=1, in_broker_id=2, out_date="2025-01-05", in_date="2025-01-10")
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01", broker_id=1), t_out, t_in],
            economic_events=[_income(90, "DIVIDEND", "50", dt="2025-01-07", broker_id=1)],
            target_currency="EUR",
        )
        assert _lot_income(result, 1) == _d("50")
        assert result.asset_orphan_income == _d("0")

    def test_income_on_destination_broker_during_transit_is_orphan(self):
        t_out, t_in = _transfer_pair(2, 3, "10", out_broker_id=1, in_broker_id=2, out_date="2025-01-05", in_date="2025-01-10")
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01", broker_id=1), t_out, t_in],
            economic_events=[_income(90, "DIVIDEND", "50", dt="2025-01-07", broker_id=2)],
            target_currency="EUR",
        )
        assert _lot_income(result, 1) == _d("0")
        assert result.asset_orphan_income == _d("50")
        assert "ASSET_INCOME_NO_ELIGIBLE_LOTS" in _issue_codes(result)

    def test_income_on_destination_broker_after_arrival(self):
        t_out, t_in = _transfer_pair(2, 3, "10", out_broker_id=1, in_broker_id=2, out_date="2025-01-05", in_date="2025-01-10")
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01", broker_id=1), t_out, t_in],
            economic_events=[_income(90, "DIVIDEND", "50", dt="2025-01-12", broker_id=2)],
            target_currency="EUR",
        )
        assert _lot_income(result, 1) == _d("50")
        assert result.asset_orphan_income == _d("0")

    def test_multiple_income_same_pool_conserved(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "30", "100", dt="2025-01-05")],
            economic_events=[
                _income(90, "DIVIDEND", "100", dt="2025-01-20"),
                _income(91, "DIVIDEND", "260", dt="2025-01-20"),
            ],
            target_currency="EUR",
        )
        assert _lot_income(result, 1) == _d("90")
        assert _lot_income(result, 2) == _d("270")
        dividend_groups = [group for group in result.economic_allocation_groups if group.economic_type == "DIVIDEND"]
        assert len(dividend_groups) == 1
        assert dividend_groups[0].source_transaction_ids == (90, 91)
        assert dividend_groups[0].target_pool_total == _d("360")

    def test_dividend_and_interest_are_separate_groups_with_shared_eligibility(self):
        result = _run(
            [_buy(1, "40", "100", dt="2025-01-01")],
            economic_events=[
                _income(90, "DIVIDEND", "100", dt="2025-01-20"),
                _income(91, "INTEREST", "40", dt="2025-01-20"),
            ],
            target_currency="EUR",
        )
        assert _lot_income(result, 1) == _d("140")
        types = sorted(group.economic_type for group in result.economic_allocation_groups)
        assert types == ["DIVIDEND", "INTEREST"]

    def test_foreign_currency_income_uses_target_amount(self):
        # Native 120 USD pre-converted by the service to 96 EUR -> engine allocates the target.
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01")],
            economic_events=[_income(90, "DIVIDEND", "120", dt="2025-01-20", native_currency="USD", target_amount="96")],
            target_currency="EUR",
        )
        assert _lot_income(result, 1) == _d("96")
        group = result.economic_allocation_groups[0]
        assert group.native_pool_total == _d("120")
        assert group.target_pool_total == _d("96")


class TestFeeTaxAllocation:
    """Engine economic stage (Fase 4/5): FEE/TAX asset-linked costs allocated to lots.

    Matching order (§4.3): FEE = same-day trades -> previous-day trades -> holdings fallback ->
    orphan; TAX = same-day income -> same-day trades -> previous-day income -> previous-day trades
    -> holdings fallback -> orphan. A trade's cost quota splits between the lots it opened (OPENING)
    and closed (CLOSURE) by q_open/q_close (crossing-safe). Native and target totals are conserved.
    """

    # --- FEE: same-day trades -----------------------------------------------
    def test_fee_same_day_buy_goes_to_opening_lot(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01")],
            economic_events=[_fee(90, "-5", dt="2025-01-01")],
            target_currency="EUR",
        )
        assert _lot_fees(result, 1) == _d("5")
        assert _group_contexts(result, "FEE") == ["OPENING"]
        assert _issue_codes(result) == []

    def test_fee_same_day_sell_goes_to_closure_lot(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01"), _sell(2, "10", "120", dt="2025-01-10")],
            economic_events=[_fee(90, "-5", dt="2025-01-10")],
            target_currency="EUR",
        )
        assert _lot_fees(result, 1) == _d("5")
        assert _group_contexts(result, "FEE") == ["CLOSURE"]

    def test_fee_same_day_mixed_buy_sell_split_by_trade_value(self):
        # 2025-01-10: SELL 5@100 (value 500) closes lot1, BUY 5@100 (value 500) opens lot3.
        # Equal values -> FEE 10 splits 5/5; SELL quota -> CLOSURE(lot1), BUY quota -> OPENING(lot3).
        result = _run(
            [
                _buy(1, "10", "100", dt="2025-01-01"),
                _sell(2, "5", "100", dt="2025-01-10"),
                _buy(3, "5", "100", dt="2025-01-10"),
            ],
            economic_events=[_fee(90, "-10", dt="2025-01-10")],
            target_currency="EUR",
        )
        assert _lot_fees(result, 1) == _d("5")
        assert _lot_fees(result, 3) == _d("5")
        fee_groups = [g for g in result.economic_allocation_groups if g.economic_type == "FEE"]
        assert fee_groups[0].rule == "SAME_DAY_MIXED_TRADES"
        assert sorted(_group_contexts(result, "FEE")) == ["CLOSURE", "OPENING"]

    def test_fee_multi_currency_trades_weighted_by_target_amount(self):
        # Two same-day BUYs in different native currencies; the service resolved target controvalues
        # 800 and 1200 EUR -> FEE 20 splits 8/12 by target weight (reviewer correction #1).
        result = _run(
            [
                _buy(1, "10", "80", dt="2025-01-01", target_amount="-800"),
                _buy(2, "10", "120", dt="2025-01-01", target_amount="-1200"),
            ],
            economic_events=[_fee(90, "-20", dt="2025-01-01")],
            target_currency="EUR",
        )
        assert _lot_fees(result, 1) == _d("8")
        assert _lot_fees(result, 2) == _d("12")

    def test_multiple_fees_same_pool_summed_and_conserved(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01")],
            economic_events=[_fee(90, "-3", dt="2025-01-01"), _fee(91, "-7", dt="2025-01-01")],
            target_currency="EUR",
        )
        assert _lot_fees(result, 1) == _d("10")
        fee_groups = [g for g in result.economic_allocation_groups if g.economic_type == "FEE"]
        assert fee_groups[0].source_transaction_ids == (90, 91)
        assert fee_groups[0].target_pool_total == _d("10")

    # --- FEE: previous-day / fallback / orphan ------------------------------
    def test_fee_previous_day_trade(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01")],
            economic_events=[_fee(90, "-5", dt="2025-01-02")],
            target_currency="EUR",
        )
        assert _lot_fees(result, 1) == _d("5")
        fee_groups = [g for g in result.economic_allocation_groups if g.economic_type == "FEE"]
        assert fee_groups[0].rule == "PREVIOUS_DAY_TRADES"

    def test_fee_holdings_fallback_when_no_recent_trade(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01")],
            economic_events=[_fee(90, "-5", dt="2025-01-10")],
            target_currency="EUR",
        )
        assert _lot_fees(result, 1) == _d("5")
        fee_groups = [g for g in result.economic_allocation_groups if g.economic_type == "FEE"]
        assert fee_groups[0].rule == "OPEN_LOTS_FALLBACK"
        assert _group_contexts(result, "FEE") == ["HOLDING"]

    def test_fee_orphan_when_no_eligible_lot(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01"), _sell(2, "10", "120", dt="2025-01-05")],
            economic_events=[_fee(90, "-5", dt="2025-01-20")],
            target_currency="EUR",
        )
        assert _lot_fees(result, 1) == _d("0")
        assert result.asset_orphan_fees == _d("5")
        assert "ASSET_COST_NO_ELIGIBLE_LOTS" in _issue_codes(result)
        assert result.analysis_status == "DEGRADED"

    # --- FEE: crossing (Fase 5) ---------------------------------------------
    def test_fee_crossing_short_to_long_splits_cost(self):
        # SELL opens SHORT lot1 (10); BUY 15 closes it (q_close=10) and opens LONG lot2 (q_open=5).
        # FEE 30 splits 20 (CLOSURE lot1) / 10 (OPENING lot2) by q_close/q_open.
        result = _run(
            [_sell(1, "10", "100", dt="2025-01-01"), _buy(2, "15", "110", dt="2025-01-05")],
            broker_shorting={1: True},
            economic_events=[_fee(90, "-30", dt="2025-01-05")],
            target_currency="EUR",
        )
        assert _lot_fees(result, 1) == _d("20")
        assert _lot_fees(result, 2) == _d("10")
        assert sorted(_group_contexts(result, "FEE")) == ["CLOSURE", "OPENING"]

    def test_fee_crossing_long_to_short_splits_cost(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01"), _sell(2, "15", "120", dt="2025-01-05")],
            broker_shorting={1: True},
            economic_events=[_fee(90, "-30", dt="2025-01-05")],
            target_currency="EUR",
        )
        assert _lot_fees(result, 1) == _d("20")
        assert _lot_fees(result, 2) == _d("10")

    def test_same_lot_in_opening_and_closure_same_day(self):
        # Lot1 opened and partially sold on the same day -> the FEE pool touches lot1 under both
        # OPENING (from the BUY quota) and CLOSURE (from the SELL quota); total still conserved.
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-10"), _sell(2, "4", "120", dt="2025-01-10")],
            economic_events=[_fee(90, "-10", dt="2025-01-10")],
            target_currency="EUR",
        )
        assert _lot_fees(result, 1) == _d("10")
        assert sorted(_group_contexts(result, "FEE")) == ["CLOSURE", "OPENING"]

    # --- FEE: FX conservation -----------------------------------------------
    def test_fee_foreign_currency_conserves_native_and_target(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01")],
            economic_events=[_fee(90, "-50", dt="2025-01-01", native_currency="USD", target_amount="-40")],
            target_currency="EUR",
        )
        assert _lot_fees(result, 1) == _d("40")
        fee_groups = [g for g in result.economic_allocation_groups if g.economic_type == "FEE"]
        assert fee_groups[0].native_pool_total == _d("50")
        assert fee_groups[0].target_pool_total == _d("40")

    # --- TAX: income-linked -------------------------------------------------
    def test_tax_on_same_day_income_uses_income_eligibility(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01")],
            economic_events=[
                _income(80, "DIVIDEND", "100", dt="2025-01-20"),
                _tax(90, "-15", dt="2025-01-20"),
            ],
            target_currency="EUR",
        )
        assert _lot_income(result, 1) == _d("100")
        assert _lot_taxes(result, 1) == _d("15")
        assert _group_contexts(result, "TAX") == ["INCOME"]
        tax_groups = [g for g in result.economic_allocation_groups if g.economic_type == "TAX"]
        assert tax_groups[0].rule == "SAME_DAY_INCOME"

    def test_tax_on_dividend_and_interest_pool(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01")],
            economic_events=[
                _income(80, "DIVIDEND", "100", dt="2025-01-20"),
                _income(81, "INTEREST", "40", dt="2025-01-20"),
                _tax(90, "-14", dt="2025-01-20"),
            ],
            target_currency="EUR",
        )
        assert _lot_taxes(result, 1) == _d("14")

    def test_tax_previous_day_income(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01")],
            economic_events=[
                _income(80, "DIVIDEND", "100", dt="2025-01-19"),
                _tax(90, "-15", dt="2025-01-20"),
            ],
            target_currency="EUR",
        )
        assert _lot_taxes(result, 1) == _d("15")
        tax_groups = [g for g in result.economic_allocation_groups if g.economic_type == "TAX"]
        assert tax_groups[0].rule == "PREVIOUS_DAY_INCOME"

    def test_tax_orphan_when_taxed_income_is_orphan(self):
        # Dividend after the lot is closed -> income orphan; the same-day TAX follows it -> tax orphan
        # (no fall-through to trades, no mixed allocated/orphan, §4.2).
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01"), _sell(2, "10", "120", dt="2025-01-05")],
            economic_events=[
                _income(80, "DIVIDEND", "50", dt="2025-01-20"),
                _tax(90, "-10", dt="2025-01-20"),
            ],
            target_currency="EUR",
        )
        assert result.asset_orphan_income == _d("50")
        assert result.asset_orphan_taxes == _d("10")
        assert _lot_taxes(result, 1) == _d("0")

    # --- TAX: trade fallback when no income ---------------------------------
    def test_tax_same_day_trade_when_no_income(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01")],
            economic_events=[_tax(90, "-5", dt="2025-01-01")],
            target_currency="EUR",
        )
        assert _lot_taxes(result, 1) == _d("5")
        tax_groups = [g for g in result.economic_allocation_groups if g.economic_type == "TAX"]
        assert tax_groups[0].rule == "SAME_DAY_TRADES"

    def test_tax_previous_day_trade_when_no_income(self):
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01")],
            economic_events=[_tax(90, "-5", dt="2025-01-02")],
            target_currency="EUR",
        )
        assert _lot_taxes(result, 1) == _d("5")
        tax_groups = [g for g in result.economic_allocation_groups if g.economic_type == "TAX"]
        assert tax_groups[0].rule == "PREVIOUS_DAY_TRADES"

    def test_tax_holdings_fallback_and_orphan(self):
        allocated = _run(
            [_buy(1, "10", "100", dt="2025-01-01")],
            economic_events=[_tax(90, "-5", dt="2025-01-10")],
            target_currency="EUR",
        )
        assert _lot_taxes(allocated, 1) == _d("5")
        assert _group_contexts(allocated, "TAX") == ["HOLDING"]

        orphan = _run(
            [_buy(1, "10", "100", dt="2025-01-01"), _sell(2, "10", "120", dt="2025-01-05")],
            economic_events=[_tax(90, "-5", dt="2025-01-20")],
            target_currency="EUR",
        )
        assert orphan.asset_orphan_taxes == _d("5")
        assert "ASSET_COST_NO_ELIGIBLE_LOTS" in _issue_codes(orphan)


class TestAnalysisStatus:
    def test_clean_replay_is_complete(self):
        result = _run([_buy(1, "10", "100", dt="2025-01-01")])
        assert result.issues == []
        assert result.analysis_status == "COMPLETE"

    def test_economic_orphan_is_degraded(self):
        # Isolable economic issue (orphan income) must not invalidate the replay.
        result = _run(
            [_buy(1, "10", "100", dt="2025-01-01"), _sell(2, "10", "120", dt="2025-01-05")],
            economic_events=[_income(90, "DIVIDEND", "50", dt="2025-01-20")],
            target_currency="EUR",
        )
        assert "ASSET_INCOME_NO_ELIGIBLE_LOTS" in _issue_codes(result)
        assert result.analysis_status == "DEGRADED"

    def test_quantitative_issue_is_failed(self):
        # Oversell -> FIFO_SOURCE_QUANTITY_MISSING: a non-isolable quantitative
        # replay failure that must surface as FAILED, not DEGRADED.
        result = _run(
            [_buy(1, "3", "100", dt="2025-01-01"), _sell(2, "8", "120", dt="2025-01-02")],
            broker_shorting={1: False},
        )
        assert "FIFO_SOURCE_QUANTITY_MISSING" in _issue_codes(result)
        assert result.analysis_status == "FAILED"

    def test_quantitative_failure_dominates_economic_issue(self):
        # A quantitative failure alongside an economic one still yields FAILED.
        result = _run(
            [_buy(1, "3", "100", dt="2025-01-01"), _sell(2, "8", "120", dt="2025-01-02")],
            broker_shorting={1: False},
            economic_events=[_income(90, "DIVIDEND", "50", dt="2025-01-20")],
            target_currency="EUR",
        )
        codes = _issue_codes(result)
        assert "FIFO_SOURCE_QUANTITY_MISSING" in codes
        assert result.analysis_status == "FAILED"


class TestEconomicConservation:
    """FIFO half of the Fase 9 reconciliation invariant: for every economic type,
    Σ(allocated to lots) + asset_orphan == absolute (pre-share) target pool total.
    The engine is broker-scoped and share-agnostic, so these absolute totals are the
    ground truth the Portfolio Engine's share-weighted accumulators must reconcile to.
    """

    def test_multi_broker_income_fees_taxes_conserved(self):
        # Directa (b1) 30 / IBKR (b2) 70; income/fee on b1, income/tax on b2 -> all allocate.
        result = _run(
            [
                _buy(1, "30", "100", dt="2025-01-01", broker_id=1),
                _buy(2, "70", "100", dt="2025-01-01", broker_id=2),
            ],
            economic_events=[
                _income(90, "DIVIDEND", "100", dt="2025-01-20", broker_id=1),
                _income(91, "DIVIDEND", "40", dt="2025-01-20", broker_id=2),
                _fee(92, "-8", dt="2025-01-20", broker_id=1),
                _tax(93, "-5", dt="2025-01-20", broker_id=2),
            ],
            target_currency="EUR",
        )
        assert result.asset_orphan_income == _d("0")
        assert result.asset_orphan_fees == _d("0")
        assert result.asset_orphan_taxes == _d("0")
        # Conservation: Σ allocated + orphan == absolute pool total.
        assert _sum_allocated_income(result) + result.asset_orphan_income == _d("140")
        assert _sum_allocated_fees(result) + result.asset_orphan_fees == _d("8")
        assert _sum_allocated_taxes(result) + result.asset_orphan_taxes == _d("5")
        # Broker scope preserved (no cross-broker bleed).
        assert _lot_income(result, 1) == _d("100")
        assert _lot_income(result, 2) == _d("40")
        assert _lot_fees(result, 1) == _d("8")
        assert _lot_taxes(result, 2) == _d("5")

    def test_conservation_holds_with_orphans(self):
        # b1 position fully closed before its dividend+fee -> both orphan; b2 stays open.
        result = _run(
            [
                _buy(1, "10", "100", dt="2025-01-01", broker_id=1),
                _sell(2, "10", "120", dt="2025-01-05", broker_id=1),
                _buy(3, "10", "100", dt="2025-01-01", broker_id=2),
            ],
            economic_events=[
                _income(90, "DIVIDEND", "50", dt="2025-01-20", broker_id=1),
                _income(91, "DIVIDEND", "30", dt="2025-01-20", broker_id=2),
                _fee(92, "-7", dt="2025-01-20", broker_id=1),
            ],
            target_currency="EUR",
        )
        assert result.asset_orphan_income == _d("50")
        assert result.asset_orphan_fees == _d("7")
        assert _lot_income(result, 3) == _d("30")
        # Conservation still holds once orphans are included.
        assert _sum_allocated_income(result) + result.asset_orphan_income == _d("80")
        assert _sum_allocated_fees(result) + result.asset_orphan_fees == _d("7")
        assert _sum_allocated_taxes(result) + result.asset_orphan_taxes == _d("0")
