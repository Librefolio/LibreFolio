"""Unit tests for backend/app/services/fifo_lot_engine.py."""

from datetime import date
from decimal import Decimal

import pytest

from backend.app.services.fifo_lot_engine import (
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
    )


def _buy(tx_id: int, qty: str, price: str, dt: str = "2025-01-01", broker_id: int = 1) -> FifoInputTransaction:
    return _tx(tx_id, "BUY", broker_id=broker_id, dt=dt, quantity=qty, amount=f"-{_d(qty) * _d(price)}")


def _sell(tx_id: int, qty: str, price: str, dt: str = "2025-01-01", broker_id: int = 1) -> FifoInputTransaction:
    return _tx(tx_id, "SELL", broker_id=broker_id, dt=dt, quantity=f"-{qty}", amount=f"{_d(qty) * _d(price)}")


def _adjustment(tx_id: int, qty: str, dt: str = "2025-01-01", broker_id: int = 1) -> FifoInputTransaction:
    return _tx(tx_id, "ADJUSTMENT", broker_id=broker_id, dt=dt, quantity=qty)


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
    )


def _issue_codes(result) -> list[str]:
    return [issue.code for issue in result.issues]


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
        assert result.relative_return_for_lot(1, _d("50")) == expected_return
        assert expected_code in _issue_codes(result) if expected_code else result.issues == []

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

        lot1 = result.value_for_lot(1, _d("120"))
        lot2 = result.value_for_lot(2, _d("120"))
        total = result.aggregate_value([1, 2], _d("120"))
        assert lot1.open_value == _d("720")
        assert lot1.proceeds == _d("440")
        assert lot1.total_value == _d("1160")
        assert lot1.pnl == _d("160")
        assert lot2.open_value == _d("600")
        assert lot2.pnl == _d("200")
        assert total.open_value == lot1.open_value + lot2.open_value
        assert total.proceeds == lot1.proceeds + lot2.proceeds
        assert total.total_value == lot1.total_value + lot2.total_value
        assert total.original_cost == lot1.original_cost + lot2.original_cost
        assert total.pnl == lot1.pnl + lot2.pnl

    def test_signed_fragment_reconciliation_matches_broker_balances(self):
        t_out, t_in = _transfer_pair(3, 4, "2", out_broker_id=1, in_broker_id=2, out_date="2025-01-03", in_date="2025-01-05")
        result = _run(
            [
                _buy(1, "10", "100", dt="2025-01-01", broker_id=1),
                _sell(2, "3", "110", dt="2025-01-02", broker_id=1),
                t_out,
                t_in,
                _adjustment(5, "4", dt="2025-01-06", broker_id=2),
                _sell(6, "1", "120", dt="2025-01-07", broker_id=2),
            ]
        )

        assert result.signed_quantity_by_broker(1) == _d("5")
        assert result.signed_quantity_by_broker(2) == _d("5")
        assert sum(result.signed_quantity_by_broker(broker_id) for broker_id in (1, 2)) == _d("10")
