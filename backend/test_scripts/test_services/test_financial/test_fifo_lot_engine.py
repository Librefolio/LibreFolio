"""Unit tests for backend/app/services/financial_math/fifo/engine.py."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.services.financial_math.fifo import models as fifo_models
from backend.app.services.financial_math.fifo.eligibility import eligible_income_quantity
from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.fifo.models import (
    EconomicAllocationGroup,
    EconomicEvent,
    EconomicLotAllocation,
    FifoInputTransaction,
    FragmentInterval,
    LotMatchingMethod,
    ReferencePriceResolution,
    TargetOperationAllocation,
)
from backend.app.services.financial_math.lots.conversions import FxRateResolver
from backend.app.services.financial_math.lots.economic_events import extract_cost_outputs, map_economic_groups, withheld_economics
from backend.app.services.financial_math.lots.histories import _prefix_value_on_date, build_value_history, group_closures, group_fragments

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
    currency: str | None = "EUR",
) -> FifoInputTransaction:
    return FifoInputTransaction(
        id=tx_id,
        broker_id=broker_id,
        asset_id=ASSET_ID,
        date=date.fromisoformat(dt),
        type=tx_type,
        quantity=_d(quantity),
        amount=_d(amount),
        currency=currency,
        related_transaction_id=related_transaction_id,
        target_amount=_d(target_amount) if target_amount is not None else None,
        target_currency=target_currency,
        cost_basis_override=_d(cost_basis_override) if cost_basis_override is not None else None,
        cost_basis_currency=cost_basis_currency,
    )


def _buy(tx_id: int, qty: str, price: str, dt: str = "2025-01-01", broker_id: int = 1, target_amount: str | None = None, currency: str | None = "EUR") -> FifoInputTransaction:
    return _tx(tx_id, "BUY", broker_id=broker_id, dt=dt, quantity=qty, amount=f"-{_d(qty) * _d(price)}", target_amount=target_amount, currency=currency)


def _sell(tx_id: int, qty: str, price: str, dt: str = "2025-01-01", broker_id: int = 1, target_amount: str | None = None, currency: str | None = "EUR") -> FifoInputTransaction:
    return _tx(tx_id, "SELL", broker_id=broker_id, dt=dt, quantity=f"-{qty}", amount=f"{_d(qty) * _d(price)}", target_amount=target_amount, currency=currency)


def _adjustment(tx_id: int, qty: str, dt: str = "2025-01-01", broker_id: int = 1, cost_basis_override: str | None = None, cost_basis_currency: str | None = None, currency: str | None = "EUR") -> FifoInputTransaction:
    return _tx(tx_id, "ADJUSTMENT", broker_id=broker_id, dt=dt, quantity=qty, cost_basis_override=cost_basis_override, cost_basis_currency=cost_basis_currency, currency=currency)


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
    split_event_ids_by_tx_id: dict[int, int] | None = None,
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
        split_event_ids_by_tx_id=split_event_ids_by_tx_id,
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


class TestEligibleIncomeQuantity:
    """Public D-1 eligibility seam shared by FIFO allocation and Yield on Cost."""

    def test_cutoff_excludes_same_day_buy_and_includes_same_day_sell(self):
        income_date = date(2025, 1, 10)
        fragments = [
            FragmentInterval(
                fragment_id="sold-on-income-day",
                lot_id=1,
                direction="LONG",
                custody_type="BROKER",
                quantity=_d("10"),
                unit_price=_d("100"),
                start_date=date(2025, 1, 1),
                end_date=income_date,
                broker_id=1,
            ),
            FragmentInterval(
                fragment_id="bought-on-income-day",
                lot_id=2,
                direction="LONG",
                custody_type="BROKER",
                quantity=_d("7"),
                unit_price=_d("100"),
                start_date=income_date,
                broker_id=1,
            ),
            FragmentInterval(
                fragment_id="short-is-never-eligible",
                lot_id=3,
                direction="SHORT",
                custody_type="BROKER",
                quantity=_d("99"),
                unit_price=_d("100"),
                start_date=date(2025, 1, 1),
                broker_id=1,
            ),
        ]

        assert eligible_income_quantity(
            fragments,
            broker_id=1,
            cutoff=income_date - timedelta(days=1),
        ) == _d("10")

    def test_in_transit_quantity_belongs_to_source_until_arrival(self):
        fragments = [
            FragmentInterval(
                fragment_id="in-transit",
                lot_id=1,
                direction="LONG",
                custody_type="IN_TRANSIT",
                quantity=_d("4"),
                unit_price=_d("100"),
                start_date=date(2025, 1, 5),
                end_date=date(2025, 1, 10),
                source_broker_id=1,
                destination_broker_id=2,
            ),
            FragmentInterval(
                fragment_id="arrived",
                lot_id=1,
                direction="LONG",
                custody_type="BROKER",
                quantity=_d("4"),
                unit_price=_d("100"),
                start_date=date(2025, 1, 10),
                broker_id=2,
                source_broker_id=1,
                destination_broker_id=2,
            ),
        ]

        transit_cutoff = date(2025, 1, 7)
        assert eligible_income_quantity(fragments, broker_id=1, cutoff=transit_cutoff) == _d("4")
        assert eligible_income_quantity(fragments, broker_id=2, cutoff=transit_cutoff) == _d("0")

        arrival_cutoff = date(2025, 1, 10)
        assert eligible_income_quantity(fragments, broker_id=1, cutoff=arrival_cutoff) == _d("0")
        assert eligible_income_quantity(fragments, broker_id=2, cutoff=arrival_cutoff) == _d("4")


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

    def test_global_split_linked_on_both_transfer_brokers_applies_once_per_in_transit_fragment(self):
        """Two broker adjustments represent one global event, not two 2:1 splits."""
        t_out, t_in = _transfer_pair(
            2,
            3,
            "10",
            out_broker_id=1,
            in_broker_id=2,
            out_date="2025-01-05",
            in_date="2025-01-10",
        )
        source_split_tx = _adjustment(
            4,
            "10",
            dt="2025-01-07",
            broker_id=1,
        )
        destination_split_tx = _adjustment(
            5,
            "10",
            dt="2025-01-07",
            broker_id=2,
        )
        global_split_event_id = 7001

        result = _run(
            [
                _buy(1, "10", "100", dt="2025-01-01", broker_id=1),
                t_out,
                t_in,
                source_split_tx,
                destination_split_tx,
            ],
            split_ratios_by_tx_id={4: _d("2"), 5: _d("2")},
            split_event_ids_by_tx_id={
                4: global_split_event_id,
                5: global_split_event_id,
            },
        )

        split_events = [event for event in result.classified_events if event.kind == "SPLIT"]
        assert {event.transaction_id for event in split_events} == {4, 5}
        assert {event.asset_event_id for event in split_events} == {global_split_event_id}

        transit_history = [fragment for fragment in result.fragment_intervals if fragment.fragment_id == "lot:1/transfer:2/transit"]
        assert [fragment.quantity for fragment in transit_history] == [
            _d("10"),
            _d("20"),
        ]

        active = result.active_fragments(lot_id=1)
        assert len(active) == 1
        assert active[0].fragment_id == "lot:1/transfer:2/to:2"
        assert active[0].quantity == _d("20")
        assert active[0].unit_price == _d("50")
        assert result.get_lot(1).original_cost == _d("1000")

    def test_split_snapshot_keeps_large_scope_and_small_custody_candidates_separate(self):
        """Passive metadata stays pre-event; generic FIFO does not judge row coherence."""
        in_transit_quantity = _d("900000000000")
        total_quantity = in_transit_quantity + _d("1")
        t_out, t_in = _transfer_pair(
            2,
            3,
            str(in_transit_quantity),
            out_broker_id=1,
            in_broker_id=2,
            out_date="2025-01-05",
            in_date="2025-01-10",
        )
        split_tx = _adjustment(
            4,
            "2",
            dt="2025-01-07",
            broker_id=1,
        )

        result = _run(
            [
                _buy(
                    1,
                    str(total_quantity),
                    "1",
                    dt="2025-01-01",
                    broker_id=1,
                ),
                t_out,
                t_in,
                split_tx,
            ],
            split_ratios_by_tx_id={4: _d("2")},
            split_event_ids_by_tx_id={4: 7002},
        )

        snapshot = result.split_quantities_by_transaction_id[4]
        assert snapshot.scoped_quantity == total_quantity
        assert snapshot.broker_custody_quantity == _d("1")
        assert result.analysis_status == "COMPLETE"

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


#: date.min (0001-01-01) and the day after it, as the ``dt`` strings of the builders above.
DATE_MIN = date.min.isoformat()
DAY_AFTER_DATE_MIN = (date.min + timedelta(days=1)).isoformat()


def _economic_group(result, economic_type: str):
    """The one allocation group of ``economic_type`` (each case below builds exactly one pool of that type)."""
    groups = [group for group in result.economic_allocation_groups if group.economic_type == economic_type]
    assert len(groups) == 1, groups
    return groups[0]


class TestEconomicsOnDateMin:
    """MF-SEC8-2b — income, FEE and TAX pools on date.min (0001-01-01: stored by an older version or a hand edit).

    Every D-1 rule looks at the day before the pool, and date.min has none: nothing was held then, so a D-1 rule finds
    nothing — the income pool is orphan, and a FEE/TAX pool is orphan unless a same-day rule applies. The same-day
    rules keep working. On HEAD b44bdd333 the engine subtracts a day from date.min (the income cutoff, the cost pools'
    ``previous_day`` computed before any rule): OverflowError. Each case runs on date.min and, as its guard, on an
    ordinary day with the same shape, where today's allocation is the expected one.
    """

    @pytest.mark.parametrize("day", [pytest.param(DATE_MIN, id="date_min"), pytest.param("2025-01-20", id="ordinary_day")])
    def test_dividend_with_only_a_same_day_lot_is_orphan_income(self, day):
        """Red on HEAD b44bdd333 for ``date_min`` (OverflowError). The lot opened on the dividend's day was not held
        the day before: orphan income, as for ``ordinary_day`` today."""
        result = _run([_buy(1, "10", "100", dt=day)], economic_events=[_income(90, "DIVIDEND", "50", dt=day)], target_currency="EUR")

        assert _lot_income(result, 1) == _d("0")
        assert result.asset_orphan_income == _d("50")
        assert "ASSET_INCOME_NO_ELIGIBLE_LOTS" in _issue_codes(result)
        group = _economic_group(result, "DIVIDEND")
        assert (group.rule, group.source_transaction_ids, group.operation_allocations, group.target_orphan) == ("ASSET_INCOME_HOLDINGS", (90,), (), _d("50"))

    @pytest.mark.parametrize("economic_type", ["FEE", "TAX"])
    @pytest.mark.parametrize("day", [pytest.param(DATE_MIN, id="date_min"), pytest.param("2025-01-01", id="ordinary_day")])
    def test_cost_with_a_same_day_buy_goes_to_its_opening_lot(self, day, economic_type):
        """Red on HEAD b44bdd333 for ``date_min`` (OverflowError, raised before any rule). A same-day BUY and no income:
        SAME_DAY_TRADES, the whole pool on the lot the BUY opened — the rule an ordinary day applies today."""
        result = _run([_buy(1, "10", "100", dt=day)], economic_events=[_cost(90, economic_type, "-5", dt=day)], target_currency="EUR")

        accumulator = result.economic_accumulators_by_lot[1]
        assert (accumulator.allocated_fees, accumulator.allocated_taxes) == ((_d("5"), _d("0")) if economic_type == "FEE" else (_d("0"), _d("5")))
        assert _economic_group(result, economic_type).rule == "SAME_DAY_TRADES"
        assert _group_contexts(result, economic_type) == ["OPENING"]
        assert (result.asset_orphan_fees, result.asset_orphan_taxes) == (_d("0"), _d("0"))
        assert _issue_codes(result) == []

    @pytest.mark.parametrize("economic_type", ["FEE", "TAX"])
    @pytest.mark.parametrize(
        ("day", "buy_day"),
        [pytest.param(DATE_MIN, DAY_AFTER_DATE_MIN, id="date_min"), pytest.param("2025-01-20", "2025-01-21", id="ordinary_day")],
    )
    def test_cost_without_a_same_day_match_is_orphan(self, day, buy_day, economic_type):
        """Red on HEAD b44bdd333 for ``date_min`` (OverflowError). No income, no trade on the pool's day, and the lot is
        opened the day after: the previous-day rules and the D-1 holdings find nothing, so the pool is orphan under
        OPEN_LOTS_FALLBACK, the last level tried — as for ``ordinary_day`` today."""
        result = _run([_buy(1, "10", "100", dt=buy_day)], economic_events=[_cost(90, economic_type, "-5", dt=day)], target_currency="EUR")

        assert (result.asset_orphan_fees, result.asset_orphan_taxes) == ((_d("5"), _d("0")) if economic_type == "FEE" else (_d("0"), _d("5")))
        assert (_lot_fees(result, 1), _lot_taxes(result, 1)) == (_d("0"), _d("0"))
        assert "ASSET_COST_NO_ELIGIBLE_LOTS" in _issue_codes(result)
        group = _economic_group(result, economic_type)
        assert (group.rule, group.operation_allocations, group.target_orphan) == ("OPEN_LOTS_FALLBACK", (), _d("5"))

    @pytest.mark.parametrize("day", [pytest.param(DATE_MIN, id="date_min"), pytest.param("2025-01-20", id="ordinary_day")])
    def test_tax_on_a_same_day_orphan_income_is_orphan(self, day):
        """Red on HEAD b44bdd333 for ``date_min`` (OverflowError). TAX follows the same-day income it taxes, held as of
        D-1: there is none, so the dividend is orphan and so is the TAX, under SAME_DAY_INCOME — no fall-through to the
        same-day BUY, as for ``ordinary_day`` today."""
        result = _run(
            [_buy(1, "10", "100", dt=day)],
            economic_events=[_income(80, "DIVIDEND", "50", dt=day), _tax(90, "-10", dt=day)],
            target_currency="EUR",
        )

        assert (result.asset_orphan_income, result.asset_orphan_taxes) == (_d("50"), _d("10"))
        assert (_lot_income(result, 1), _lot_taxes(result, 1)) == (_d("0"), _d("0"))
        assert {"ASSET_INCOME_NO_ELIGIBLE_LOTS", "ASSET_COST_NO_ELIGIBLE_LOTS"} <= set(_issue_codes(result))
        group = _economic_group(result, "TAX")
        assert (group.rule, group.operation_allocations, group.target_orphan) == ("SAME_DAY_INCOME", (), _d("10"))

    @pytest.mark.parametrize(
        ("income_day", "tax_day"),
        [pytest.param(DATE_MIN, DAY_AFTER_DATE_MIN, id="income_on_date_min"), pytest.param("2025-01-19", "2025-01-20", id="ordinary_days")],
    )
    def test_tax_the_day_after_an_orphan_income_is_orphan(self, income_day, tax_day):
        """Red on HEAD b44bdd333 for ``income_on_date_min`` (OverflowError), although the TAX is dated 0001-01-02:
        PREVIOUS_DAY_INCOME reads the holdings of the day before the income, the day before date.min. The dividend's
        only lot opened on its day, so it is orphan, and the TAX that follows it is orphan under PREVIOUS_DAY_INCOME
        — as for ``ordinary_days`` today."""
        result = _run(
            [_buy(1, "10", "100", dt=income_day)],
            economic_events=[_income(80, "DIVIDEND", "50", dt=income_day), _tax(90, "-10", dt=tax_day)],
            target_currency="EUR",
        )

        assert (result.asset_orphan_income, result.asset_orphan_taxes) == (_d("50"), _d("10"))
        assert _lot_taxes(result, 1) == _d("0")
        group = _economic_group(result, "TAX")
        assert (group.rule, group.operation_allocations, group.target_orphan) == ("PREVIOUS_DAY_INCOME", (), _d("10"))

    def test_the_day_after_date_min_sees_the_lots_held_on_date_min(self):
        """Guard (green on HEAD b44bdd333 and after): date.min is a day like any other for the day after it. A lot
        bought on date.min is held as of D-1 for a dividend on 0001-01-02, and a FEE on 0001-01-02 with no trade that
        day goes to the date.min BUY under PREVIOUS_DAY_TRADES."""
        result = _run(
            [_buy(1, "10", "100", dt=DATE_MIN)],
            economic_events=[_income(80, "DIVIDEND", "50", dt=DAY_AFTER_DATE_MIN), _fee(90, "-5", dt=DAY_AFTER_DATE_MIN)],
            target_currency="EUR",
        )

        assert (_lot_income(result, 1), _lot_fees(result, 1)) == (_d("50"), _d("5"))
        assert (result.asset_orphan_income, result.asset_orphan_fees) == (_d("0"), _d("0"))
        assert _economic_group(result, "FEE").rule == "PREVIOUS_DAY_TRADES"
        assert _issue_codes(result) == []


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


# --------------------------------------------------------------------------- #
# CP-7a — developer's decision 26 (D-J1, option B): the currency of a closure
# --------------------------------------------------------------------------- #


class TestCloseCurrency:
    """Every closure carries the currency of its closing price, ``close_currency``; across two currencies there is no native realized P&L.

    Workstream J, CP-7a. A SELL or a BUY closes in its row's currency; an ADJUSTMENT-in closing a short in the currency of its
    cost (``cost_basis_currency``, else the row's) when it has one, else in the row's. A closure whose currency differs from
    its lot's — None counting as the engine's target currency, as the lots FX resolver reads it — is mixed: the engine has no
    rates, so its native ``realized_pnl`` is None, and a LONG lot's ``realized_pnl`` and ``cumulative_proceeds`` are None from
    then on; ``proceeds`` stay, native in the closure's currency. The lots analysis converts each leg at its own date
    (test_lots_analysis_pure.py, CP-7a section). Before CP-7a a closure had no currency and the engine subtracted any two
    prices. Values are asserted before ``close_currency``, so a test whose values changed fails on them; GUARD marks values
    CP-7a leaves as they were.
    """

    @pytest.mark.parametrize(
        "currency",
        [
            pytest.param("EUR", id="GUARD-values-in-the-report-currency"),
            pytest.param("USD", id="GUARD-values-of-a-foreign-lot-sold-in-its-own-currency"),
        ],
    )
    def test_a_sell_closes_in_its_own_currency_and_keeps_its_native_realized_pnl(self, currency):
        """10 bought at 100 and 4 sold at 120, both in ``currency``, report EUR: close_currency is the SELL's, realized 80 and proceeds 480 native.

        One currency, nothing mixed: the values are GUARDs. Before CP-7a: the same values, and no close_currency (AttributeError).
        """
        result = _run([_buy(1, "10", "100", currency=currency), _sell(2, "4", "120", dt="2025-01-10", currency=currency)], target_currency="EUR")
        closure = next(closure for closure in result.closures if closure.transaction_id == 2)
        lot = result.get_lot(1)

        assert (closure.realized_pnl, closure.proceeds, lot.realized_pnl, lot.cumulative_proceeds) == (_d("80"), _d("480"), _d("80"), _d("480"))
        assert closure.close_currency == currency

    def test_a_lot_bought_in_eur_and_sold_in_usd_has_no_native_realized_pnl(self):
        """1 bought at 100 EUR at broker 1, moved to broker 2, sold there at 110 USD, report EUR: the closure is in USD and mixed.

        Its proceeds stay 110, native USD; its realized P&L and the lot's realized P&L and cumulative proceeds are None: 110 USD
        less 100 EUR has no meaning without rates. Before CP-7a: realized 10 on the closure and on the lot, cumulative proceeds 110.
        """
        t_out, t_in = _transfer_pair(2, 3, "1", out_broker_id=1, in_broker_id=2, out_date="2025-03-03", in_date="2025-03-03")
        result = _run([_buy(1, "1", "100", dt="2025-01-02", currency="EUR"), t_out, t_in, _sell(4, "1", "110", dt="2025-06-02", broker_id=2, currency="USD")], target_currency="EUR")
        closure = next(closure for closure in result.closures if closure.transaction_id == 4)
        lot = result.get_lot(1)

        observed = {"closure": (closure.quantity, closure.realized_pnl, closure.proceeds), "lot": (lot.open_quantity, lot.realized_pnl, lot.cumulative_proceeds)}
        assert observed == {"closure": (_d("1"), None, _d("110")), "lot": (_d("0"), None, None)}
        assert closure.close_currency == "USD"

    def test_after_a_mixed_closure_the_lots_native_sums_stay_unknown(self):
        """10 bought at 100 EUR; 4 sold at 110 USD (mixed), then 6 at 120 EUR: the lot's realized P&L and proceeds stay None.

        The EUR sale keeps its own native realized P&L, 6 × 20 = 120. The engine never asks which currencies a broker trades in,
        so both sales are at broker 1. Before CP-7a: realized 4 × 10 + 120 = 160 and proceeds 440 + 720 = 1160, USD and EUR added.
        """
        result = _run([_buy(1, "10", "100", currency="EUR"), _sell(2, "4", "110", dt="2025-02-03", currency="USD"), _sell(3, "6", "120", dt="2025-03-03", currency="EUR")], target_currency="EUR")
        realized_by_closure = {(closure.lot_id, closure.transaction_id): closure.realized_pnl for closure in result.closures}
        lot = result.get_lot(1)

        assert (realized_by_closure, lot.realized_pnl, lot.cumulative_proceeds) == ({(1, 2): None, (1, 3): _d("120")}, None, None)

    @pytest.mark.parametrize(
        ("buy_currency", "expected_realized"),
        [
            pytest.param("USD", _d("100"), id="GUARD-values-bought-back-in-the-shorts-currency"),
            pytest.param("EUR", None, id="bought-back-in-another-currency-is-mixed"),
        ],
    )
    def test_a_buy_closing_a_short_carries_the_buys_currency(self, buy_currency, expected_realized):
        """5 sold short at 120 USD, report EUR, bought back at 100 in ``buy_currency``: the closure is in the BUY's currency.

        In USD the short realizes 5 × (120 − 100) = 100, native; in EUR the closure is mixed, None. Either way the short's
        cumulative proceeds stay its opening sale's, 600. Before CP-7a: 100 in both cases (USD less EUR), and no close_currency.
        """
        result = _run([_sell(1, "5", "120", currency="USD"), _buy(2, "5", "100", dt="2025-01-10", currency=buy_currency)], broker_shorting={1: True}, target_currency="EUR")
        closure = next(closure for closure in result.closures if closure.transaction_id == 2)
        lot = result.get_lot(1)

        assert (closure.close_reason, closure.realized_pnl, lot.cumulative_proceeds) == ("BUY", expected_realized, _d("600"))
        assert closure.close_currency == buy_currency

    @pytest.mark.parametrize(
        ("override", "override_currency", "row_currency", "expected_currency", "expected_close_price", "expected_realized"),
        [
            pytest.param("100", "USD", "EUR", "USD", _d("100"), _d("100"), id="a-cost-in-USD-on-a-row-in-EUR-closes-in-USD"),
            pytest.param("100", "GBP", "USD", "GBP", _d("100"), None, id="a-cost-in-GBP-is-mixed-against-the-USD-short"),
            pytest.param(None, None, "EUR", "EUR", _d("0"), None, id="without-a-cost-in-the-rows-currency"),
        ],
    )
    def test_an_adjustment_in_closing_a_short_carries_its_costs_currency(self, override, override_currency, row_currency, expected_currency, expected_close_price, expected_realized):
        """5 sold short at 120 USD, report EUR, then an ADJUSTMENT +5: (close price, native realized, close_currency) of its closure.

        With a cost the closure is in the cost's currency — cost_basis_currency, never the row's — at the cost: in USD, the
        short's, 5 × (120 − 100) = 100; in GBP it is mixed, None. Without a cost it closes at 0 in the row's currency, EUR here:
        mixed, None. Before CP-7a: no close_currency, and the realized P&L read 100, 100 and 600 (5 × 120 against a price of 0).
        """
        adjustment = _adjustment(2, "5", dt="2025-01-10", cost_basis_override=override, cost_basis_currency=override_currency, currency=row_currency)
        result = _run([_sell(1, "5", "120", currency="USD"), adjustment], broker_shorting={1: True}, target_currency="EUR")
        closure = next(closure for closure in result.closures if closure.transaction_id == 2)

        assert (closure.close_reason, closure.close_unit_price, closure.realized_pnl) == ("BUY", expected_close_price, expected_realized)
        assert closure.close_currency == expected_currency


# --------------------------------------------------------------------------- #
# Project 66, M1 — a charge linked to a trade goes on that trade's lots
# --------------------------------------------------------------------------- #
#
# A FEE/TAX whose ``parent_transaction_id`` names a BUY/SELL the engine replayed, at the charge's own broker, leaves the
# day's pool before pooling: one ``LINKED_TRADE`` group per charge, dated on the charge, split by
# ``_split_trade_cost`` between the lots its parent opened (OPENING) and closed (CLOSURE). A charge whose parent is a
# BUY/SELL of its broker dated after ``replay_until`` waits, orphan (M1b, below); a charge whose parent is an income of
# the engine goes on the lots that earned it (M2, LINKED_INCOME, below). Every other charge — no parent, a parent the
# engine never saw and knows no facts of, a parent that opened and closed nothing, a parent that is neither a trade nor
# an income, or a parent of another broker — keeps today's ladder and its numbers. Within a type the linked groups come
# first, by (charge date, charge id), then the pools.


def _linked_cost(
    tx_id: int,
    econ_type: str,
    amount: str,
    *,
    dt: str,
    parent: int,
    broker_id: int = 1,
    native_currency: str = "EUR",
    target_amount: str | None = None,
    target_currency: str = "EUR",
    parent_facts=None,
) -> EconomicEvent:
    """A FEE/TAX event linked to ``parent`` (project 66). ``amount`` is the stored (negative) native amount.

    ``parent_facts`` (M1b) are the parent's facts the service reads (``_parent_facts``); omitted, the event has none.
    """
    facts = {"parent": parent_facts} if parent_facts is not None else {}
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
        parent_transaction_id=parent,
        **facts,
    )


def _parent_facts(day: str, tx_type: str = "BUY", broker_id: int = 1):
    """The facts of a charge's parent as the service reads them (project 66, M1b: ``LinkedParent``).

    Resolved on the module when called, so the file still collects while ``LinkedParent`` does not exist and only the
    tests that need it are red.
    """
    return fifo_models.LinkedParent(date=date.fromisoformat(day), type=tx_type, broker_id=broker_id)


def _linked_fee(tx_id: int, amount: str, *, dt: str, parent: int, **kwargs) -> EconomicEvent:
    return _linked_cost(tx_id, "FEE", amount, dt=dt, parent=parent, **kwargs)


def _linked_tax(tx_id: int, amount: str, *, dt: str, parent: int, **kwargs) -> EconomicEvent:
    return _linked_cost(tx_id, "TAX", amount, dt=dt, parent=parent, **kwargs)


def _run_linked(
    txs: list[FifoInputTransaction],
    events: list[EconomicEvent],
    *,
    replay_until: str | None = None,
    matching_method: LotMatchingMethod = LotMatchingMethod.FIFO,
    broker_shorting: dict[int, bool] | None = None,
):
    """The engine in EUR, with the replay end and the matching method ``_run`` does not pass."""
    return run_fifo_lot_engine(
        txs,
        broker_shorting or {},
        economic_events=events,
        target_currency="EUR",
        replay_until=date.fromisoformat(replay_until) if replay_until is not None else None,
        matching_method=matching_method,
    )


def _group_of(result, source_id: int) -> EconomicAllocationGroup:
    """The one allocation group whose sources hold the charge ``source_id``."""
    groups = [group for group in result.economic_allocation_groups if source_id in group.source_transaction_ids]
    assert len(groups) == 1, f"charge {source_id} must be in exactly one group: {groups}"
    return groups[0]


def _group_index(groups, source_id: int) -> int:
    """Index of the group holding ``source_id`` in the engine's list (what ``withheld_economics`` returns indexes into)."""
    indexes = [index for index, group in enumerate(groups) if source_id in group.source_transaction_ids]
    assert len(indexes) == 1, f"charge {source_id} must be in exactly one group: {indexes}"
    return indexes[0]


def _operations(group: EconomicAllocationGroup) -> list[tuple[str, int | None, tuple[int, ...]]]:
    """(context, operation transaction, lot ids) of each operation of a group."""
    return [(op.context, op.operation_transaction_id, tuple(allocation.lot_id for allocation in op.lot_allocations)) for op in group.operation_allocations]


def _cents(value: Decimal) -> Decimal:
    """The figure to the cent: the running remainder of a pool split may leave sub-cent digits (§7.3 of the M1 contract)."""
    return value.quantize(Decimal("0.01"))


class TestLinkedChargeOnItsTrade:
    """The three trade cases of analysis §3.5: each linked charge lands on the lots of its own trade."""

    def test_two_buys_of_one_day_keep_each_their_own_linked_fee(self):
        # Morning BUY 1 000 € with its FEE 2 €, afternoon BUY 9 000 € with its FEE 19 €. Today the 21 € pool splits by
        # controvalue: 2.10 / 18.90.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-03-03"), _buy(2, "90", "100", dt="2025-03-03")],
            [_linked_fee(90, "-2", dt="2025-03-03", parent=1), _linked_fee(91, "-19", dt="2025-03-03", parent=2)],
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2)) == (_d("2"), _d("19"))
        for charge, parent in ((90, 1), (91, 2)):
            group = _group_of(result, charge)
            assert (group.rule, group.source_transaction_ids, group.date) == ("LINKED_TRADE", (charge,), date(2025, 3, 3))
            assert _operations(group) == [("OPENING", parent, (parent,))]
        assert _issue_codes(result) == []

    def test_a_fee_linked_to_the_sell_of_a_mixed_day_goes_to_the_closure_only(self):
        # Same day: BUY 1 000 opens lot 2, SELL 1 000 closes lot 1. FEE 5 € linked to the SELL: 5 on the closure, 0 on the
        # new lot. Today the mixed pool gives 2.50 / 2.50.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-02-03"), _sell(3, "10", "100", dt="2025-02-03")],
            [_linked_fee(90, "-5", dt="2025-02-03", parent=3)],
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2)) == (_d("5"), _d("0"))
        group = _group_of(result, 90)
        assert group.rule == "LINKED_TRADE"
        assert _operations(group) == [("CLOSURE", 3, (1,))]

    def test_a_tax_linked_to_a_sell_three_days_earlier_goes_to_the_lots_it_closed(self):
        # SELL 3 closes lot 1 on 3 Feb, lot 2 stays open. TAX 6 € on 6 Feb linked to the SELL. Today: no trade that day or
        # the day before, so OPEN_LOTS_FALLBACK puts it on the open lot 2.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-02"), _sell(3, "10", "120", dt="2025-02-03")],
            [_linked_tax(90, "-6", dt="2025-02-06", parent=3)],
        )

        assert (_lot_taxes(result, 1), _lot_taxes(result, 2)) == (_d("6"), _d("0"))
        group = _group_of(result, 90)
        assert (group.rule, group.date) == ("LINKED_TRADE", date(2025, 2, 6))
        assert _operations(group) == [("CLOSURE", 3, (1,))]

    def test_a_tax_linked_to_a_sell_that_left_nothing_open_is_allocated_not_orphan(self):
        # Same shape with no lot left open: today the TAX is orphan (ASSET_COST_NO_ELIGIBLE_LOTS, DEGRADED). Linked, it is
        # a cost of the closed lot and the analysis is COMPLETE (§7.6 of the M1 contract).
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _sell(3, "10", "120", dt="2025-02-03")],
            [_linked_tax(90, "-6", dt="2025-02-06", parent=3)],
        )

        assert _lot_taxes(result, 1) == _d("6")
        assert result.asset_orphan_taxes == _d("0")
        assert "ASSET_COST_NO_ELIGIBLE_LOTS" not in _issue_codes(result)
        assert result.analysis_status == "COMPLETE"


class TestLinkedChargeBesideAPool:
    def test_the_unlinked_rest_of_the_day_still_splits_over_every_trade(self):
        # BUY A 1 000 with its FEE 2 €, BUY B 9 000, an unlinked FEE 19 € the same day. The 19 € pool splits over both
        # trades as today (1.90 / 17.10, §6.6): A = 2 + 1.90, B = 17.10.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-03-03"), _buy(2, "90", "100", dt="2025-03-03")],
            [_linked_fee(90, "-2", dt="2025-03-03", parent=1), _fee(91, "-19", dt="2025-03-03")],
        )

        assert (_cents(_lot_fees(result, 1)), _cents(_lot_fees(result, 2))) == (_d("3.90"), _d("17.10"))
        assert _group_of(result, 90).rule == "LINKED_TRADE"
        pool = _group_of(result, 91)
        assert (pool.rule, pool.source_transaction_ids, pool.target_pool_total) == ("SAME_DAY_TRADES", (91,), _d("19"))
        assert sorted(_operations(pool)) == [("OPENING", 1, (1,)), ("OPENING", 2, (2,))]


class TestLinkedChargeConservation:
    """Σ allocated + orphan == Σ |events| for each type, in native and in target (§1.5, §7.9 of the M1 contract)."""

    def test_linked_unlinked_waiting_unseen_and_orphan_charges_conserve_both_totals(self):
        # BUY 4 lies after replay_until (M1b, retargeted): the charges linked to it (93, 96) wait, orphan, each in its own
        # empty LINKED_TRADE group; before M1b they went back to their day's pool (93 with 94, 96 with 98). FEE 99 is
        # linked to a row the engine never saw and knows no facts of: it still joins its day's pool, with 94. Every charge
        # is dated on or before replay_until and on no day touching BUY 4, so no ladder pool reaches the unreplayed trade.
        txs = [
            _buy(1, "10", "100", dt="2025-01-01"),
            _buy(2, "20", "100", dt="2025-01-10"),
            _sell(3, "5", "120", dt="2025-01-10"),
            _buy(4, "10", "100", dt="2025-03-01"),
        ]
        events = [
            _linked_fee(90, "-3", dt="2025-01-10", parent=2),
            _fee(91, "-4", dt="2025-01-10"),
            _linked_fee(92, "-10", dt="2025-01-10", parent=3, native_currency="USD", target_amount="-9"),
            _linked_fee(93, "-2", dt="2025-01-20", parent=4),
            _fee(94, "-1", dt="2025-01-20"),
            _fee(97, "-5", dt="2025-01-20", broker_id=2),
            _linked_tax(95, "-6", dt="2025-01-13", parent=3),
            _linked_tax(96, "-7", dt="2025-01-25", parent=4),
            _tax(98, "-1.5", dt="2025-01-25"),
            _linked_fee(99, "-1.25", dt="2025-01-20", parent=777),
        ]
        result = _run_linked(txs, events, replay_until="2025-02-01")

        # Each charge is in exactly one group; the linked ones alone in theirs.
        for event in events:
            _group_of(result, event.transaction_id)
        assert [(group.source_transaction_ids, group.rule) for group in result.economic_allocation_groups if group.rule == "LINKED_TRADE"] == [
            ((90,), "LINKED_TRADE"),
            ((92,), "LINKED_TRADE"),
            ((93,), "LINKED_TRADE"),
            ((95,), "LINKED_TRADE"),
            ((96,), "LINKED_TRADE"),
        ]
        for waiting in (93, 96):
            group = _group_of(result, waiting)
            assert (group.operation_allocations, group.native_orphan, group.target_orphan) == ((), group.native_pool_total, group.target_pool_total)
        assert (_group_of(result, 94).source_transaction_ids, _group_of(result, 94).rule) == ((94, 99), "OPEN_LOTS_FALLBACK")
        assert (_group_of(result, 98).source_transaction_ids, _group_of(result, 98).rule) == ((98,), "OPEN_LOTS_FALLBACK")
        assert sorted(issue.transaction_id for issue in _after_range_issues(result)) == [93, 96]
        # FEE 97 of broker 2 (no lot there) and the waiting FEE 93; the waiting TAX 96.
        assert (result.asset_orphan_fees, result.asset_orphan_taxes) == (_d("7"), _d("7"))

        for economic_type, accumulated, orphan in (("FEE", _sum_allocated_fees(result), result.asset_orphan_fees), ("TAX", _sum_allocated_taxes(result), result.asset_orphan_taxes)):
            typed = [event for event in events if event.economic_type == economic_type]
            groups = [group for group in result.economic_allocation_groups if group.economic_type == economic_type]
            target_total = sum((abs(event.target_amount) for event in typed), _d("0"))
            native_total = sum((abs(event.native_amount) for event in typed), _d("0"))
            native_allocated = sum((allocation.native_amount for group in groups for op in group.operation_allocations for allocation in op.lot_allocations), _d("0"))
            native_orphan = sum((group.native_orphan for group in groups), _d("0"))
            assert accumulated + orphan == target_total, economic_type
            assert native_allocated + native_orphan == native_total, economic_type


class TestLinkedChargeCurrency:
    def test_a_usd_charge_on_a_eur_trade_uses_its_resolved_target_amount(self):
        # FEE 10 USD, resolved by the service to 9 EUR, linked to BUY 2. No FX in the engine: 9 EUR on lot 2, 10 USD native.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-01")],
            [_linked_fee(90, "-10", dt="2025-01-01", parent=2, native_currency="USD", target_amount="-9")],
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2)) == (_d("0"), _d("9"))
        group = _group_of(result, 90)
        assert (group.rule, group.native_currency, group.target_currency) == ("LINKED_TRADE", "USD", "EUR")
        assert (group.native_pool_total, group.target_pool_total) == (_d("10"), _d("9"))
        [operation] = group.operation_allocations
        assert [(allocation.lot_id, allocation.native_amount, allocation.target_amount) for allocation in operation.lot_allocations] == [(2, _d("10"), _d("9"))]


class TestLinkedChargeDate:
    """The date of a linked charge is never judged: it goes on its parent's lots, and its group carries its own date."""

    def test_a_charge_dated_after_its_parent(self):
        # Today: OPEN_LOTS_FALLBACK splits 4 € over lots 1 and 2 (2 / 2).
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-20")],
            [_linked_fee(90, "-4", dt="2025-01-25", parent=1)],
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2)) == (_d("4"), _d("0"))
        group = _group_of(result, 90)
        assert (group.rule, group.date) == ("LINKED_TRADE", date(2025, 1, 25))
        assert _operations(group) == [("OPENING", 1, (1,))]

    def test_a_charge_dated_before_its_buy(self):
        # Today: OPEN_LOTS_FALLBACK on 17 Jan reaches lot 1 only.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-20")],
            [_linked_fee(90, "-4", dt="2025-01-18", parent=2)],
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2)) == (_d("0"), _d("4"))
        group = _group_of(result, 90)
        assert (group.rule, group.date) == ("LINKED_TRADE", date(2025, 1, 18))
        assert _operations(group) == [("OPENING", 2, (2,))]

    def test_a_charge_dated_before_its_sell(self):
        # SELL 3 on 20 Jan closes lot 1 (FIFO). Today: OPEN_LOTS_FALLBACK on 17 Jan splits 4 € over lots 1 and 2.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-05"), _sell(3, "10", "120", dt="2025-01-20")],
            [_linked_fee(90, "-4", dt="2025-01-18", parent=3)],
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2)) == (_d("4"), _d("0"))
        group = _group_of(result, 90)
        assert (group.rule, group.date) == ("LINKED_TRADE", date(2025, 1, 18))
        assert _operations(group) == [("CLOSURE", 3, (1,))]


class TestLinkedChargeFallbacks:
    """A charge whose parent is not a trade the engine replayed — and not a trade of its broker after the end (M1b, which
    waits: ``TestLinkedChargeWaitingForItsParent``), nor an income of its broker (M2: ``TestLinkedChargeOnItsIncome``)
    — keeps today's ladder: same rule, same numbers."""

    # The consultant's example (§8 of the M1 contract): lot A bought in January and still open; FEE 5 € of 10 Mar linked
    # to a BUY of 12 Mar (lot B).
    _LOT_A = _buy(1, "10", "100", dt="2025-01-15")
    _LOT_B = _buy(2, "10", "100", dt="2025-03-12")
    _FEE = ("-5", "2025-03-10")

    # M1b retarget: the old case «b-parent-after-replay-until» (BUY 2 among the transactions, after the end) waits now:
    # TestLinkedChargeWaitingForItsParent.test_the_consultants_example_waits_until_the_analysis_reaches_the_buy.
    @pytest.mark.parametrize(
        "replay_until",
        [
            pytest.param(None, id="a-parent-absent-from-transactions"),
            pytest.param("2025-03-11", id="a-parent-absent-from-transactions-with-an-end"),
        ],
    )
    def test_linked_charge_parent_absent_with_no_facts_goes_back_to_the_ladder(self, replay_until):
        amount, day = self._FEE
        result = _run_linked([self._LOT_A], [_linked_fee(90, amount, dt=day, parent=2)], replay_until=replay_until)

        assert _lot_fees(result, 1) == _d("5")
        group = _group_of(result, 90)
        assert (group.rule, group.date) == ("OPEN_LOTS_FALLBACK", date(2025, 3, 10))
        assert _operations(group) == [("HOLDING", None, (1,))]
        assert _after_range_issues(result) == []

    @pytest.mark.parametrize("replay_until", [pytest.param("2025-03-12", id="on-the-parents-day"), pytest.param("2025-06-30", id="later"), pytest.param(None, id="no-end")])
    def test_linked_charge_parent_seen_by_engine_goes_to_its_lot(self, replay_until):
        amount, day = self._FEE
        result = _run_linked([self._LOT_A, self._LOT_B], [_linked_fee(90, amount, dt=day, parent=2)], replay_until=replay_until)

        assert (_lot_fees(result, 1), _lot_fees(result, 2)) == (_d("0"), _d("5"))
        group = _group_of(result, 90)
        assert (group.rule, group.date) == ("LINKED_TRADE", date(2025, 3, 10))
        assert _operations(group) == [("OPENING", 2, (2,))]

    # M1b retarget: test_without_lot_a_a_charge_whose_parent_is_unseen_is_orphan (BUY 2 among the transactions, after the
    # end: OPEN_LOTS_FALLBACK, ASSET_COST_NO_ELIGIBLE_LOTS) waits now — TestLinkedChargeWaitingForItsParent.
    # test_without_lot_a_the_charge_waits_instead_of_taking_the_ladders_orphan.

    def test_a_charge_back_on_the_ladder_joins_its_own_days_pool(self):
        # Never a second group with the same pool key (§7.2): the charge whose parent the engine never saw (and knows no
        # facts of) and an unlinked FEE of the same broker, day and currency make one pool. M1b retarget: before, the
        # parent was BUY 2 after the end, which now waits; the rule stays on the case that keeps the ladder.
        amount, day = self._FEE
        result = _run_linked([self._LOT_A], [_linked_fee(90, amount, dt=day, parent=2), _fee(91, "-1", dt=day)], replay_until="2025-03-11")

        group = _group_of(result, 90)
        assert (group.source_transaction_ids, group.rule, group.target_pool_total) == ((90, 91), "OPEN_LOTS_FALLBACK", _d("6"))
        assert _lot_fees(result, 1) == _d("6")

    def test_a_parent_that_opened_and_closed_nothing_goes_back_to_the_ladder(self):
        # SELL 3 at broker 2, which holds nothing and cannot short: the replay rejects it (FIFO_SOURCE_QUANTITY_MISSING),
        # so it closed nothing and opened nothing (``_split_trade_cost`` is []). The FEE, dated away from the SELL's day
        # and the day after, takes the ladder of broker 2: no lot, orphan.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-15"), _sell(3, "5", "120", dt="2025-03-12", broker_id=2)],
            [_linked_fee(90, "-5", dt="2025-03-20", parent=3, broker_id=2)],
            broker_shorting={1: False, 2: False},
        )

        assert "FIFO_SOURCE_QUANTITY_MISSING" in _issue_codes(result), "precondition: the SELL is rejected"
        group = _group_of(result, 90)
        assert (group.rule, group.operation_allocations, group.target_orphan) == ("OPEN_LOTS_FALLBACK", (), _d("5"))
        assert result.asset_orphan_fees == _d("5")

    # M2 retarget: test_a_tax_linked_to_a_dividend_stays_on_the_ladder_until_m2 (SAME_DAY_INCOME, 3 / 3) goes on the
    # dividend's lots now, rule LINKED_INCOME, same 3 / 3 —
    # TestLinkedChargeOnItsIncome.test_a_tax_linked_to_a_same_day_dividend_goes_on_its_lots.

    def test_a_charge_linked_to_a_row_that_is_not_a_trade_stays_on_the_ladder(self):
        # ADJUSTMENT 1 opens lot 1 with a cost but is not a trade; BUY 2 the same day opens lot 2. The FEE linked to the
        # adjustment takes today's SAME_DAY_TRADES: all of it to lot 2.
        result = _run_linked(
            [_adjustment(1, "10", dt="2025-01-10", cost_basis_override="100", cost_basis_currency="EUR"), _buy(2, "10", "100", dt="2025-01-10")],
            [_linked_fee(90, "-4", dt="2025-01-10", parent=1)],
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2)) == (_d("0"), _d("4"))
        assert _group_of(result, 90).rule == "SAME_DAY_TRADES"

    def test_a_charge_linked_to_a_trade_of_another_broker_stays_on_the_ladder(self):
        # Defence (§7.2): the parent's broker was changed after the link. The FEE of broker 2 takes broker 2's ladder.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-10", broker_id=1), _buy(2, "10", "100", dt="2025-01-10", broker_id=2)],
            [_linked_fee(90, "-4", dt="2025-01-10", parent=1, broker_id=2)],
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2)) == (_d("0"), _d("4"))
        assert _group_of(result, 90).rule == "SAME_DAY_TRADES"


# --------------------------------------------------------------------------- #
# Project 66, M1b — a charge linked to a trade after the end of the analysis waits, orphan
# --------------------------------------------------------------------------- #
#
# Developer's decision of 20 Nov 2026 (M1b contract §1, §7): a FEE/TAX linked to a BUY or SELL of its own broker dated
# after ``replay_until`` no longer takes the ladder. It leaves its pool, goes on no lot, and waits as an orphan in its own
# ``LINKED_TRADE`` group (no operation, dated on the charge), with one ``ASSET_COST_LINKED_PARENT_AFTER_RANGE`` issue,
# until the analysis reaches the parent's date. The engine reads the parent from its own transactions, or — when the
# parent is not among them, as in the service, which loads trades up to the end — from ``event.parent``.

_AFTER_RANGE = "ASSET_COST_LINKED_PARENT_AFTER_RANGE"


def _after_range_issues(result) -> list:
    return [issue for issue in result.issues if issue.code == _AFTER_RANGE]


def _assert_waiting(
    result,
    charge_id: int,
    *,
    economic_type: str,
    amount: str,
    day: str,
    parent_id: int,
    parent_day: str,
    native: str | None = None,
    native_currency: str = "EUR",
    broker_id: int = 1,
    rule: str = "LINKED_TRADE",
) -> None:
    """The charge waits for its parent: alone in an empty group of its parent's rule (``LINKED_TRADE`` for a trade,
    ``LINKED_INCOME`` for an income, M2 §1.3), all of it orphan, with its one issue."""
    group = _group_of(result, charge_id)
    target_total, native_total = _d(amount), _d(native if native is not None else amount)
    assert (group.economic_type, group.rule, group.source_transaction_ids, group.operation_allocations) == (economic_type, rule, (charge_id,), ())
    assert (group.date, group.broker_id, group.native_currency, group.target_currency) == (date.fromisoformat(day), broker_id, native_currency, "EUR")
    assert (group.native_pool_total, group.target_pool_total, group.native_orphan, group.target_orphan) == (native_total, target_total, native_total, target_total)
    issues = [issue for issue in _after_range_issues(result) if issue.transaction_id == charge_id]
    assert len(issues) == 1, f"charge {charge_id} must have exactly one {_AFTER_RANGE} issue: {result.issues}"
    assert issues[0].broker_id == broker_id
    assert issues[0].params == {
        "economic_type": economic_type,
        "as_of_date": day,
        "target_amount": target_total,
        "target_currency": "EUR",
        "parent_transaction_id": parent_id,
        "parent_date": parent_day,
    }


def _assert_no_parent_in_any_issue(result, parent_day: str) -> None:
    """No issue names the parent: no M1b code, no ``parent_*`` param, no param holding the parent's date."""
    assert _after_range_issues(result) == []
    for issue in result.issues:
        assert not {"parent_transaction_id", "parent_date"} & set(issue.params), issue
        assert parent_day not in issue.params.values(), issue


class TestLinkedChargeWaitingForItsParent:
    """A charge linked to a BUY/SELL of its broker dated after ``replay_until`` is orphan until the analysis reaches it."""

    # The consultant's example (M1b contract §2): lot A bought in January and still open; FEE 5 € of 10 Mar linked to a
    # BUY of 12 Mar (lot B).
    _LOT_A = _buy(1, "10", "100", dt="2025-01-15")
    _LOT_B = _buy(2, "10", "100", dt="2025-03-12")

    def test_the_consultants_example_waits_until_the_analysis_reaches_the_buy(self):
        # To 11 Mar: the BUY is among the engine's transactions but after the end. Before M1b the FEE took
        # OPEN_LOTS_FALLBACK and landed on lot A; now it waits, orphan, and A carries nothing.
        events = [_linked_fee(90, "-5", dt="2025-03-10", parent=2)]
        waiting = _run_linked([self._LOT_A, self._LOT_B], events, replay_until="2025-03-11")

        assert (_lot_fees(waiting, 1), _lot_fees(waiting, 2)) == (_d("0"), _d("0"))
        assert waiting.asset_orphan_fees == _d("5")
        _assert_waiting(waiting, 90, economic_type="FEE", amount="5", day="2025-03-10", parent_id=2, parent_day="2025-03-12")
        assert "ASSET_COST_NO_ELIGIBLE_LOTS" not in _issue_codes(waiting)
        assert waiting.analysis_status == "DEGRADED"

        # To 12 Mar: the BUY is replayed, the FEE is on lot B, as in M1, and nothing waits.
        reached = _run_linked([self._LOT_A, self._LOT_B], events, replay_until="2025-03-12")

        assert (_lot_fees(reached, 1), _lot_fees(reached, 2)) == (_d("0"), _d("5"))
        group = _group_of(reached, 90)
        assert (group.rule, group.date) == ("LINKED_TRADE", date(2025, 3, 10))
        assert _operations(group) == [("OPENING", 2, (2,))]
        assert (reached.asset_orphan_fees, _after_range_issues(reached)) == (_d("0"), [])

    def test_a_parent_known_only_by_its_facts_leaves_its_charge_waiting(self):
        # The service's shape: the BUY of 12 Mar is not among the engine's transactions (loaded up to the end); the event
        # carries its facts. Same outcome as the parent the engine holds.
        result = _run_linked(
            [self._LOT_A],
            [_linked_fee(90, "-5", dt="2025-03-10", parent=2, parent_facts=_parent_facts("2025-03-12"))],
            replay_until="2025-03-11",
        )

        assert _lot_fees(result, 1) == _d("0")
        assert result.asset_orphan_fees == _d("5")
        _assert_waiting(result, 90, economic_type="FEE", amount="5", day="2025-03-10", parent_id=2, parent_day="2025-03-12")
        assert "ASSET_COST_NO_ELIGIBLE_LOTS" not in _issue_codes(result)

    def test_without_lot_a_the_charge_waits_instead_of_taking_the_ladders_orphan(self):
        # Retargeted from M1 (test_without_lot_a_a_charge_whose_parent_is_unseen_is_orphan): it was orphan through the
        # ladder (OPEN_LOTS_FALLBACK, ASSET_COST_NO_ELIGIBLE_LOTS); now it is orphan because it waits, with its own code.
        result = _run_linked([self._LOT_B], [_linked_fee(90, "-5", dt="2025-03-10", parent=2)], replay_until="2025-03-11")

        assert result.asset_orphan_fees == _d("5")
        _assert_waiting(result, 90, economic_type="FEE", amount="5", day="2025-03-10", parent_id=2, parent_day="2025-03-12")
        assert "ASSET_COST_NO_ELIGIBLE_LOTS" not in _issue_codes(result)

    @pytest.mark.parametrize("parent_in_the_engine", [pytest.param(True, id="parent-among-the-transactions"), pytest.param(False, id="parent-known-by-its-facts")])
    def test_a_tax_linked_to_a_sell_after_the_end_waits_and_skips_same_day_income(self, parent_in_the_engine):
        # Lots 1 and 2 open; a dividend and a TAX on 10 Feb; the TAX is linked to SELL 3 of 12 Feb — among the engine's
        # transactions, or (the service's shape) known by its facts only. Before M1b the TAX followed the income
        # (SAME_DAY_INCOME, 3 / 3 over the D-1 holdings); now it waits. The dividend is untouched.
        lots = [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-05")]
        facts = None if parent_in_the_engine else _parent_facts("2025-02-12", tx_type="SELL")
        result = _run_linked(
            [*lots, _sell(3, "10", "120", dt="2025-02-12")] if parent_in_the_engine else lots,
            [_income(80, "DIVIDEND", "50", dt="2025-02-10"), _linked_tax(90, "-6", dt="2025-02-10", parent=3, parent_facts=facts)],
            replay_until="2025-02-11",
        )

        assert (_lot_income(result, 1), _lot_income(result, 2)) == (_d("25"), _d("25"))
        assert (_lot_taxes(result, 1), _lot_taxes(result, 2)) == (_d("0"), _d("0"))
        assert (result.asset_orphan_taxes, result.asset_orphan_fees) == (_d("6"), _d("0"))
        _assert_waiting(result, 90, economic_type="TAX", amount="6", day="2025-02-10", parent_id=3, parent_day="2025-02-12")

    @pytest.mark.parametrize("parent_in_the_engine", [pytest.param(True, id="parent-among-the-transactions"), pytest.param(False, id="parent-known-by-its-facts")])
    def test_a_waiting_charge_leaves_the_unlinked_charge_of_its_pool_as_it_was(self, parent_in_the_engine):
        # Mixed day (M1b contract §7.5): on 10 Mar a waiting FEE 90 and an unlinked FEE 91 share broker, date, native and
        # target currency — one pool key — beside BUY 3 of that day. FEE 91 must get the numbers it gets without FEE 90.
        # Before M1b they made one SAME_DAY_TRADES pool of 6 €.
        txs = [self._LOT_A, _buy(3, "5", "100", dt="2025-03-10"), *([self._LOT_B] if parent_in_the_engine else [])]
        facts = None if parent_in_the_engine else _parent_facts("2025-03-12")
        alone = _run_linked(txs, [_fee(91, "-1", dt="2025-03-10")], replay_until="2025-03-11")
        reference = _group_of(alone, 91)
        assert (reference.rule, reference.source_transaction_ids, _operations(reference)) == ("SAME_DAY_TRADES", (91,), [("OPENING", 3, (3,))]), "precondition: FEE 91 alone"
        events = [_linked_fee(90, "-5", dt="2025-03-10", parent=2, parent_facts=facts), _fee(91, "-1", dt="2025-03-10")]
        mixed = _run_linked(txs, events, replay_until="2025-03-11")

        unlinked = _group_of(mixed, 91)
        assert (unlinked.rule, unlinked.source_transaction_ids, unlinked.native_pool_total, unlinked.target_pool_total) == ("SAME_DAY_TRADES", (91,), _d("1"), _d("1"))
        assert unlinked.operation_allocations == reference.operation_allocations
        assert {lot: _lot_fees(mixed, lot) for lot in (1, 2, 3)} == {lot: _lot_fees(alone, lot) for lot in (1, 2, 3)}
        _assert_waiting(mixed, 90, economic_type="FEE", amount="5", day="2025-03-10", parent_id=2, parent_day="2025-03-12")

        # Conservation: allocated + orphan == Σ |events|, native and target.
        groups = [group for group in mixed.economic_allocation_groups if group.economic_type == "FEE"]
        native_allocated = sum((allocation.native_amount for group in groups for op in group.operation_allocations for allocation in op.lot_allocations), _d("0"))
        native_orphan = sum((group.native_orphan for group in groups), _d("0"))
        assert _sum_allocated_fees(mixed) + mixed.asset_orphan_fees == _d("6")
        assert native_allocated + native_orphan == _d("6")
        assert mixed.asset_orphan_fees == _d("5")

    def test_two_waiting_charges_of_one_pool_key_keep_each_their_group_and_issue(self):
        # Two FEEs of 10 Mar, same pool key, both linked to the BUY of 12 Mar: two groups and two issues, never one pool.
        result = _run_linked(
            [self._LOT_A, self._LOT_B],
            [_linked_fee(90, "-5", dt="2025-03-10", parent=2), _linked_fee(91, "-2", dt="2025-03-10", parent=2)],
            replay_until="2025-03-11",
        )

        _assert_waiting(result, 90, economic_type="FEE", amount="5", day="2025-03-10", parent_id=2, parent_day="2025-03-12")
        _assert_waiting(result, 91, economic_type="FEE", amount="2", day="2025-03-10", parent_id=2, parent_day="2025-03-12")
        assert result.asset_orphan_fees == _d("7")
        assert _lot_fees(result, 1) == _d("0")

    def test_a_waiting_group_sorts_with_the_other_linked_groups_by_date_and_id(self):
        # FEE 90 waits (3 Mar, BUY 2 of 12 Mar); FEE 92 (5 Mar) is on BUY 3, FEE 95 (8 Mar) on BUY 1; FEE 96 is unlinked.
        # The LINKED_TRADE groups by (charge date, id) — the waiting one first — then the pool.
        result = _run_linked(
            [self._LOT_A, _buy(3, "5", "100", dt="2025-03-01"), self._LOT_B],
            [
                _linked_fee(95, "-1", dt="2025-03-08", parent=1),
                _fee(96, "-1", dt="2025-03-08"),
                _linked_fee(92, "-1", dt="2025-03-05", parent=3),
                _linked_fee(90, "-5", dt="2025-03-03", parent=2),
            ],
            replay_until="2025-03-11",
        )

        layout = [(group.rule, group.source_transaction_ids) for group in result.economic_allocation_groups if group.economic_type == "FEE"]
        assert layout == [("LINKED_TRADE", (90,)), ("LINKED_TRADE", (92,)), ("LINKED_TRADE", (95,)), ("OPEN_LOTS_FALLBACK", (96,))]
        assert _group_of(result, 90).operation_allocations == ()

    @pytest.mark.parametrize(("method", "closed_lot", "open_lot"), [pytest.param(LotMatchingMethod.FIFO, 1, 2, id="FIFO"), pytest.param(LotMatchingMethod.LIFO, 2, 1, id="LIFO")])
    def test_a_fee_linked_to_a_sell_after_the_end_waits_in_both_methods(self, method, closed_lot, open_lot):
        # Lots 1 and 2 open; SELL 3 of 12 Feb closes lot 1 in FIFO, lot 2 in LIFO; FEE of 10 Feb linked to it. To 11 Feb
        # it waits in both methods (before M1b: OPEN_LOTS_FALLBACK, 2.50 / 2.50); to 12 Feb it is on the lot each closed.
        txs = [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-05"), _sell(3, "10", "120", dt="2025-02-12")]
        events = [_linked_fee(90, "-5", dt="2025-02-10", parent=3)]

        reached = _run_linked(txs, events, replay_until="2025-02-12", matching_method=method)
        assert (_lot_fees(reached, closed_lot), _lot_fees(reached, open_lot)) == (_d("5"), _d("0"))
        assert _operations(_group_of(reached, 90)) == [("CLOSURE", 3, (closed_lot,))]
        assert _after_range_issues(reached) == []

        waiting = _run_linked(txs, events, replay_until="2025-02-11", matching_method=method)
        assert (_lot_fees(waiting, 1), _lot_fees(waiting, 2)) == (_d("0"), _d("0"))
        _assert_waiting(waiting, 90, economic_type="FEE", amount="5", day="2025-02-10", parent_id=3, parent_day="2025-02-12")


class TestLinkedChargeAfterTheEndStaysOnTheLadder:
    """The cases M1b leaves on the ladder (M1b contract §1.7, §7.8, §8.3): same rule, same numbers as in M1, no new issue.
    The income parent after the end, on the ladder until M2, waits now (``TestLinkedChargeWaitingForItsIncome``)."""

    _LOT_A = _buy(1, "10", "100", dt="2025-01-15")

    # M2 retarget: test_an_income_parent_after_the_end_stays_on_the_ladder_until_m2[DIVIDEND|INTEREST] (OPEN_LOTS_FALLBACK
    # on lot A) waits now, in an empty LINKED_INCOME group with the M1b code —
    # TestLinkedChargeWaitingForItsIncome.test_a_charge_linked_to_an_income_after_the_end_waits[income-known-by-its-facts-*].

    @pytest.mark.parametrize("parent_in_the_engine", [pytest.param(True, id="parent-among-the-transactions"), pytest.param(False, id="parent-known-by-its-facts")])
    def test_a_parent_of_another_broker_after_the_end_stays_on_the_ladder_and_is_never_named(self, parent_in_the_engine):
        # Defence of rule 5 (M1b contract §8.3): the BUY of 12 Mar was moved to broker 2 after the link. The FEE of broker
        # 1 takes broker 1's ladder (lot A), and no issue carries the parent's id or date.
        parent = _buy(2, "10", "100", dt="2025-03-12", broker_id=2)
        facts = None if parent_in_the_engine else _parent_facts("2025-03-12", broker_id=2)
        result = _run_linked(
            [self._LOT_A, parent] if parent_in_the_engine else [self._LOT_A],
            [_linked_fee(90, "-5", dt="2025-03-10", parent=2, parent_facts=facts)],
            replay_until="2025-03-11",
        )

        assert _lot_fees(result, 1) == _d("5")
        assert _group_of(result, 90).rule == "OPEN_LOTS_FALLBACK"
        _assert_no_parent_in_any_issue(result, "2025-03-12")

    def test_a_linked_charge_orphaned_by_the_ladder_keeps_the_ladders_code(self):
        # Parent absent from the engine and no facts; the FEE is at broker 2, which holds no lot: the ladder leaves it
        # orphan with ASSET_COST_NO_ELIGIBLE_LOTS, as in M1 — never the M1b code, which is only for a parent after the end.
        result = _run_linked([self._LOT_A], [_linked_fee(90, "-5", dt="2025-03-10", parent=2, broker_id=2)], replay_until="2025-03-11")

        group = _group_of(result, 90)
        assert (group.rule, group.operation_allocations, group.target_orphan) == ("OPEN_LOTS_FALLBACK", (), _d("5"))
        assert result.asset_orphan_fees == _d("5")
        assert "ASSET_COST_NO_ELIGIBLE_LOTS" in _issue_codes(result)
        assert _after_range_issues(result) == []

    def test_without_an_end_a_parent_absent_from_the_engine_stays_on_the_ladder(self):
        # A direct caller of the engine with no replay_until: nothing is "after the end", the ladder as in M1.
        result = _run_linked([self._LOT_A], [_linked_fee(90, "-5", dt="2025-03-10", parent=2, parent_facts=_parent_facts("2025-03-12"))])

        assert _lot_fees(result, 1) == _d("5")
        assert _group_of(result, 90).rule == "OPEN_LOTS_FALLBACK"
        assert _after_range_issues(result) == []

    def test_a_parent_dated_on_the_end_is_not_after_it(self):
        # Facts dated on replay_until, parent absent from the engine: not after the end (strictly later only), the ladder.
        result = _run_linked(
            [self._LOT_A],
            [_linked_fee(90, "-5", dt="2025-03-10", parent=2, parent_facts=_parent_facts("2025-03-11"))],
            replay_until="2025-03-11",
        )

        assert _lot_fees(result, 1) == _d("5")
        assert _group_of(result, 90).rule == "OPEN_LOTS_FALLBACK"
        assert _after_range_issues(result) == []

    def test_the_engines_own_parent_wins_over_the_facts(self):
        # The engine holds BUY 2 of 12 Mar, replayed (end 12 Mar); the facts claim a later date. The engine's row decides:
        # the FEE is on lot B.
        result = _run_linked(
            [self._LOT_A, _buy(2, "10", "100", dt="2025-03-12")],
            [_linked_fee(90, "-5", dt="2025-03-10", parent=2, parent_facts=_parent_facts("2025-04-01"))],
            replay_until="2025-03-12",
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2)) == (_d("0"), _d("5"))
        assert _operations(_group_of(result, 90)) == [("OPENING", 2, (2,))]
        assert _after_range_issues(result) == []


# --------------------------------------------------------------------------- #
# Project 66, M2 — a charge linked to an income goes on the lots that earned it
# --------------------------------------------------------------------------- #
#
# Decision D12 = A (M2 contract §1, §7, §8): a FEE/TAX whose ``parent_transaction_id`` names a DIVIDEND/INTEREST event of
# the engine — at the charge's broker, not after ``replay_until`` — leaves its pool and goes, alone, onto the lots that
# earned that income: the LONG holdings of the parent's broker on the day before the parent's date, by quantity, as the
# income's own ASSET_INCOME_HOLDINGS group and a SAME_DAY_INCOME TAX. Its own group, rule "LINKED_INCOME", dated on the
# charge, holds one INCOME operation whose ``operation_transaction_id`` is the parent. When no lot earned the income, the
# charge is orphan with it: an empty LINKED_INCOME group and one ASSET_COST_LINKED_INCOME_NO_ELIGIBLE_LOTS issue (§8). An
# income parent after the end waits, as in M1b, in an empty LINKED_INCOME group. An income parent at another broker, a
# parent with no facts, and a parent whose facts are not an income keep the ladder, and no issue names the parent. An
# income known only by its facts (a zero amount, with no event in the engine) follows them since M2b (see below).
# The rule and the code are strings here: the file collects before the engine knows them.

_LINKED_INCOME = "LINKED_INCOME"
_INCOME_ORPHAN = "ASSET_COST_LINKED_INCOME_NO_ELIGIBLE_LOTS"


def _lot_shares(group: EconomicAllocationGroup) -> list[tuple[int, Decimal]]:
    """(lot id, weight) of every lot allocation of a group, in the engine's order."""
    return [(allocation.lot_id, allocation.weight) for op in group.operation_allocations for allocation in op.lot_allocations]


def _assert_on_its_income(result, charge_id: int, income_id: int, *, economic_type: str, amount: str, day: str, native: str | None = None) -> None:
    """The charge is alone in its LINKED_INCOME group, dated on itself, with one INCOME operation naming its income, on the
    lots and weights of that income's own ASSET_INCOME_HOLDINGS group in the same result (§7.2), all of it allocated."""
    group = _group_of(result, charge_id)
    income = _group_of(result, income_id)
    target_total, native_total = _d(amount), _d(native if native is not None else amount)
    assert (income.rule, bool(income.operation_allocations)) == ("ASSET_INCOME_HOLDINGS", True), f"precondition: the income was allocated: {income}"
    assert (group.economic_type, group.rule, group.source_transaction_ids, group.date) == (economic_type, _LINKED_INCOME, (charge_id,), date.fromisoformat(day))
    assert [(op.context, op.operation_transaction_id) for op in group.operation_allocations] == [("INCOME", income_id)]
    assert _lot_shares(group) == _lot_shares(income)
    assert (group.native_pool_total, group.target_pool_total, group.native_orphan, group.target_orphan) == (native_total, target_total, _d("0"), _d("0"))
    allocations = [allocation for op in group.operation_allocations for allocation in op.lot_allocations]
    assert sum((allocation.target_amount for allocation in allocations), _d("0")) == target_total
    assert sum((allocation.native_amount for allocation in allocations), _d("0")) == native_total


def _assert_orphan_with_its_income(
    result,
    charge_id: int,
    *,
    economic_type: str,
    amount: str,
    day: str,
    parent_id: int,
    parent_day: str,
    native: str | None = None,
    native_currency: str = "EUR",
) -> None:
    """The charge is orphan with the income no lot earned (D12): alone in an empty LINKED_INCOME group, with its one
    ASSET_COST_LINKED_INCOME_NO_ELIGIBLE_LOTS issue — dated on the charge, naming the parent (§8) — and never the ladder's code."""
    group = _group_of(result, charge_id)
    target_total, native_total = _d(amount), _d(native if native is not None else amount)
    assert (group.economic_type, group.rule, group.source_transaction_ids, group.operation_allocations) == (economic_type, _LINKED_INCOME, (charge_id,), ())
    assert (group.date, group.broker_id, group.native_currency, group.target_currency) == (date.fromisoformat(day), 1, native_currency, "EUR")
    assert (group.native_pool_total, group.target_pool_total, group.native_orphan, group.target_orphan) == (native_total, target_total, native_total, target_total)
    issues = [issue for issue in result.issues if issue.code == _INCOME_ORPHAN and issue.transaction_id == charge_id]
    assert len(issues) == 1, f"charge {charge_id} must have exactly one {_INCOME_ORPHAN} issue: {result.issues}"
    assert issues[0].broker_id == 1
    assert issues[0].params == {
        "economic_type": economic_type,
        "as_of_date": day,
        "target_amount": target_total,
        "target_currency": "EUR",
        "parent_transaction_id": parent_id,
        "parent_date": parent_day,
    }
    assert [issue for issue in result.issues if issue.transaction_id == charge_id and issue.code != _INCOME_ORPHAN] == []


def _assert_conserved(result, events: list[EconomicEvent], economic_type: str) -> None:
    """Σ allocated + orphan == Σ |events| of one type, in target (accumulators and groups) and in native (groups)."""
    typed = [event for event in events if event.economic_type == economic_type]
    groups = [group for group in result.economic_allocation_groups if group.economic_type == economic_type]
    accumulated, orphan = (_sum_allocated_fees(result), result.asset_orphan_fees) if economic_type == "FEE" else (_sum_allocated_taxes(result), result.asset_orphan_taxes)
    target_total = sum((abs(event.target_amount) for event in typed), _d("0"))
    native_total = sum((abs(event.native_amount) for event in typed), _d("0"))
    allocations = [allocation for group in groups for op in group.operation_allocations for allocation in op.lot_allocations]
    assert accumulated + orphan == target_total, economic_type
    assert sum((allocation.target_amount for allocation in allocations), _d("0")) + sum((group.target_orphan for group in groups), _d("0")) == target_total, economic_type
    assert sum((allocation.native_amount for allocation in allocations), _d("0")) + sum((group.native_orphan for group in groups), _d("0")) == native_total, economic_type


def _assert_parent_never_named(result) -> None:
    """No issue names a linked charge's parent: no M1b or M2 code, no ``parent_*`` param (rule 5's defence)."""
    assert [issue for issue in result.issues if issue.code in (_AFTER_RANGE, _INCOME_ORPHAN)] == []
    for issue in result.issues:
        assert not {"parent_transaction_id", "parent_date"} & set(issue.params), issue


class TestLinkedChargeOnItsIncome:
    """The worked example of M2 contract §7.7 and its variations: the charge follows the income it was paid on."""

    # Lot A (10 units) and lot B (30) are held on 9 Mar; the income is of 10 Mar; BUY C opens lot C on 10 Mar.
    _LOT_A = _buy(1, "10", "100", dt="2025-01-15")
    _LOT_B = _buy(2, "30", "100", dt="2025-02-03")
    _LOT_C = _buy(3, "5", "100", dt="2025-03-10")

    @pytest.mark.parametrize("income_type", ["DIVIDEND", "INTEREST"])
    def test_the_worked_example_shares_the_fee_like_the_income(self, income_type):
        # Income of 50 € → 12.50 / 37.50 / 0. FEE of 1 € linked to it: before M2 all of it on lot C (SAME_DAY_TRADES); now
        # 0.25 / 0.75 / 0, the income's shares.
        result = _run_linked([self._LOT_A, self._LOT_B, self._LOT_C], [_income(80, income_type, "50", dt="2025-03-10"), _linked_fee(90, "-1", dt="2025-03-10", parent=80)])

        assert (_lot_income(result, 1), _lot_income(result, 2), _lot_income(result, 3)) == (_d("12.5"), _d("37.5"), _d("0"))
        assert (_lot_fees(result, 1), _lot_fees(result, 2), _lot_fees(result, 3)) == (_d("0.25"), _d("0.75"), _d("0"))
        _assert_on_its_income(result, 90, 80, economic_type="FEE", amount="1", day="2025-03-10")
        assert (result.asset_orphan_fees, result.issues, result.analysis_status) == (_d("0"), [], "COMPLETE")

    @pytest.mark.parametrize(
        ("economic_type", "charge_day"),
        [
            pytest.param("FEE", "2025-03-14", id="fee-four-days-later-before-m2-open-lots-fallback"),
            pytest.param("TAX", "2025-03-11", id="tax-the-day-after-before-m2-previous-day-income"),
            pytest.param("TAX", "2025-03-14", id="tax-four-days-later-before-m2-open-lots-fallback"),
        ],
    )
    def test_a_charge_dated_days_after_its_dividend_uses_the_dividends_day_before(self, economic_type, charge_day):
        # BUY 4 opens lot 4 (20 units) on 12 Mar, after the dividend; the charge of 4 € is dated later. Before M2: four days
        # later, OPEN_LOTS_FALLBACK on the holdings of 13 Mar, A / B / 4 = 10 / 30 / 20; a TAX of the day after,
        # PREVIOUS_DAY_INCOME (same numbers, another rule). Now always the dividend's 9 Mar: 1 / 3 / 0, rule LINKED_INCOME.
        result = _run_linked(
            [self._LOT_A, self._LOT_B, _buy(4, "20", "100", dt="2025-03-12")],
            [_income(80, "DIVIDEND", "50", dt="2025-03-10"), _linked_cost(90, economic_type, "-4", dt=charge_day, parent=80)],
        )

        lot_cost = _lot_fees if economic_type == "FEE" else _lot_taxes
        assert (lot_cost(result, 1), lot_cost(result, 2), lot_cost(result, 4)) == (_d("1"), _d("3"), _d("0"))
        _assert_on_its_income(result, 90, 80, economic_type=economic_type, amount="4", day=charge_day)

    def test_a_negative_dividend_still_shares_its_fee_by_quantity(self):
        # A correction of −50 € takes 12.50 / 37.50 off lots A and B (MF-F1). The FEE of 1 € linked to it still splits by
        # quantity, as a cost: 0.25 / 0.75, never signed by its income. Before M2: SAME_DAY_TRADES on lot C.
        result = _run_linked([self._LOT_A, self._LOT_B, self._LOT_C], [_income(80, "DIVIDEND", "-50", dt="2025-03-10"), _linked_fee(90, "-1", dt="2025-03-10", parent=80)])

        assert (_lot_income(result, 1), _lot_income(result, 2)) == (_d("-12.5"), _d("-37.5"))
        assert (_lot_fees(result, 1), _lot_fees(result, 2), _lot_fees(result, 3)) == (_d("0.25"), _d("0.75"), _d("0"))
        _assert_on_its_income(result, 90, 80, economic_type="FEE", amount="1", day="2025-03-10")

    def test_a_tax_linked_to_a_same_day_dividend_goes_on_its_lots(self):
        # Retargeted from M1 (test_a_tax_linked_to_a_dividend_stays_on_the_ladder_until_m2): lots 1 and 2 (10 units each)
        # earned the dividend; its TAX of 6 € was SAME_DAY_INCOME, 3 / 3. Now LINKED_INCOME: the same 3 / 3, its own group.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-05")],
            [_income(80, "DIVIDEND", "50", dt="2025-02-10"), _linked_tax(90, "-6", dt="2025-02-10", parent=80)],
        )

        assert (_lot_taxes(result, 1), _lot_taxes(result, 2)) == (_d("3"), _d("3"))
        _assert_on_its_income(result, 90, 80, economic_type="TAX", amount="6", day="2025-02-10")

    def test_a_same_day_tax_linked_to_its_dividend_has_the_numbers_of_same_day_income(self):
        # Lots of 10 and 20 units: a third does not terminate. Reference run: the TAX unlinked and the only TAX
        # (SAME_DAY_INCOME). Linked, it is LINKED_INCOME with the same lot allocations to the last digit (§7.2).
        txs = [_buy(1, "10", "100", dt="2025-01-15"), _buy(2, "20", "100", dt="2025-02-03")]
        income = _income(80, "DIVIDEND", "50", dt="2025-03-10")
        alone = _run_linked(txs, [income, _tax(90, "-1", dt="2025-03-10")])
        reference = _group_of(alone, 90)
        assert reference.rule == "SAME_DAY_INCOME", "precondition: the TAX alone follows the income"

        linked = _run_linked(txs, [income, _linked_tax(90, "-1", dt="2025-03-10", parent=80)])

        _assert_on_its_income(linked, 90, 80, economic_type="TAX", amount="1", day="2025-03-10")
        [reference_operation] = reference.operation_allocations
        [operation] = _group_of(linked, 90).operation_allocations
        assert operation.lot_allocations == reference_operation.lot_allocations
        assert {lot: _lot_taxes(linked, lot) for lot in (1, 2)} == {lot: _lot_taxes(alone, lot) for lot in (1, 2)}

    @pytest.mark.parametrize(
        ("method", "expected"),
        [pytest.param(LotMatchingMethod.FIFO, {1: "1", 2: "2", 4: "0"}, id="FIFO"), pytest.param(LotMatchingMethod.LIFO, {1: "2", 2: "1", 4: "0"}, id="LIFO")],
    )
    def test_the_lots_that_earned_the_income_follow_the_matching_method(self, method, expected):
        # Lots 1 and 2 (10 units each); SELL 3 of 5 units on 1 Feb leaves 5 + 10 in FIFO, 10 + 5 in LIFO. Dividend of 30 €
        # on 10 Mar, BUY 4 on 12 Mar, FEE of 3 € of 13 Mar linked to the dividend. Before M2: PREVIOUS_DAY_TRADES puts it on
        # lot 4. Now the lots each method left holding on 9 Mar.
        txs = [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-05"), _sell(3, "5", "120", dt="2025-02-01"), _buy(4, "10", "100", dt="2025-03-12")]
        result = _run_linked(txs, [_income(80, "DIVIDEND", "30", dt="2025-03-10"), _linked_fee(90, "-3", dt="2025-03-13", parent=80)], matching_method=method)

        assert {lot: _lot_fees(result, lot) for lot in (1, 2, 4)} == {lot: _d(value) for lot, value in expected.items()}
        _assert_on_its_income(result, 90, 80, economic_type="FEE", amount="3", day="2025-03-13")

    def test_an_unlinked_fee_of_the_same_pool_key_keeps_the_numbers_it_has_alone(self):
        # Mixed day: the worked example plus an unlinked FEE of 2 € with the same broker, day and currencies. Alone it is
        # SAME_DAY_TRADES on lot C; it must keep exactly that. Before M2 the two made one pool of 3 € on lot C.
        txs = [self._LOT_A, self._LOT_B, self._LOT_C]
        income = _income(80, "DIVIDEND", "50", dt="2025-03-10")
        alone = _run_linked(txs, [income, _fee(91, "-2", dt="2025-03-10")])
        reference = _group_of(alone, 91)
        assert (reference.rule, reference.source_transaction_ids, _operations(reference)) == ("SAME_DAY_TRADES", (91,), [("OPENING", 3, (3,))]), "precondition: FEE 91 alone"

        events = [income, _linked_fee(90, "-1", dt="2025-03-10", parent=80), _fee(91, "-2", dt="2025-03-10")]
        mixed = _run_linked(txs, events)

        unlinked = _group_of(mixed, 91)
        assert (unlinked.rule, unlinked.source_transaction_ids, unlinked.native_pool_total, unlinked.target_pool_total) == ("SAME_DAY_TRADES", (91,), _d("2"), _d("2"))
        assert unlinked.operation_allocations == reference.operation_allocations
        _assert_on_its_income(mixed, 90, 80, economic_type="FEE", amount="1", day="2025-03-10")
        assert {lot: _lot_fees(mixed, lot) for lot in (1, 2, 3)} == {1: _d("0.25"), 2: _d("0.75"), 3: _d("2")}
        _assert_conserved(mixed, events, "FEE")
        assert mixed.asset_orphan_fees == _d("0")

    @pytest.mark.parametrize(
        "replay_until",
        [pytest.param(None, id="no-end"), pytest.param("2025-03-10", id="income-dated-on-the-end"), pytest.param("2025-06-30", id="later-end")],
    )
    def test_an_income_of_the_engine_not_after_the_end_is_followed(self, replay_until):
        # §7.2 twins: with no end, with the income dated on the end (not after it), or with a later end, an income among the
        # engine's events is the charge's parent. The facts the service reads say the same day.
        facts = _parent_facts("2025-03-10", tx_type="DIVIDEND")
        result = _run_linked(
            [self._LOT_A, self._LOT_B, self._LOT_C],
            [_income(80, "DIVIDEND", "50", dt="2025-03-10"), _linked_fee(90, "-1", dt="2025-03-10", parent=80, parent_facts=facts)],
            replay_until=replay_until,
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2), _lot_fees(result, 3)) == (_d("0.25"), _d("0.75"), _d("0"))
        _assert_on_its_income(result, 90, 80, economic_type="FEE", amount="1", day="2025-03-10")
        assert _after_range_issues(result) == []

    def test_the_engines_income_event_wins_over_the_facts(self):
        # §7.2 twin of M1b's: the engine holds the dividend of 10 Mar (end 11 Mar); the facts claim 1 Apr, after the end.
        # The engine's event decides: on the dividend's lots, no wait.
        result = _run_linked(
            [self._LOT_A, self._LOT_B, self._LOT_C],
            [_income(80, "DIVIDEND", "50", dt="2025-03-10"), _linked_fee(90, "-1", dt="2025-03-10", parent=80, parent_facts=_parent_facts("2025-04-01", tx_type="DIVIDEND"))],
            replay_until="2025-03-11",
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2), _lot_fees(result, 3)) == (_d("0.25"), _d("0.75"), _d("0"))
        _assert_on_its_income(result, 90, 80, economic_type="FEE", amount="1", day="2025-03-10")
        assert _after_range_issues(result) == []


class TestLinkedChargeOrphanWithItsIncome:
    """D12: when no lot earned the income, the charge linked to it is orphan with it (M2 contract §1.2, §8)."""

    # The only lot is opened on the income's day: nothing is held on 9 Mar, so the dividend is orphan.
    _LOT_C = _buy(3, "5", "100", dt="2025-03-10")

    @pytest.mark.parametrize(
        "fee_day",
        [
            pytest.param("2025-03-10", id="same-day-before-m2-same-day-trades"),
            pytest.param("2025-03-13", id="days-later-before-m2-open-lots-fallback"),
        ],
    )
    def test_a_fee_linked_to_an_orphan_dividend_is_orphan_with_it(self, fee_day):
        # Before M2 the FEE found lot C through the ladder (the BUY of its day, or the holdings of 12 Mar). Now it is orphan
        # with the dividend: its issue is dated on the FEE and names the dividend's day (§8).
        events = [_income(80, "DIVIDEND", "50", dt="2025-03-10"), _linked_fee(90, "-1", dt=fee_day, parent=80)]
        result = _run_linked([self._LOT_C], events)

        assert (result.asset_orphan_income, "ASSET_INCOME_NO_ELIGIBLE_LOTS" in _issue_codes(result)) == (_d("50"), True), "precondition: the dividend is orphan"
        assert (_lot_fees(result, 3), result.asset_orphan_fees) == (_d("0"), _d("1"))
        _assert_orphan_with_its_income(result, 90, economic_type="FEE", amount="1", day=fee_day, parent_id=80, parent_day="2025-03-10")
        assert "ASSET_COST_NO_ELIGIBLE_LOTS" not in _issue_codes(result)
        _assert_conserved(result, events, "FEE")
        assert result.analysis_status == "DEGRADED"

    def test_a_same_day_tax_linked_to_an_orphan_dividend_takes_the_linked_code(self):
        # Before M2: SAME_DAY_INCOME, orphan with ASSET_COST_NO_ELIGIBLE_LOTS. §8: linked, it takes the linked code; the
        # ladder's code stays for the charges without a link.
        events = [_income(80, "DIVIDEND", "50", dt="2025-03-10"), _linked_tax(90, "-6", dt="2025-03-10", parent=80)]
        result = _run_linked([self._LOT_C], events)

        assert (_lot_taxes(result, 3), result.asset_orphan_taxes) == (_d("0"), _d("6"))
        _assert_orphan_with_its_income(result, 90, economic_type="TAX", amount="6", day="2025-03-10", parent_id=80, parent_day="2025-03-10")
        assert "ASSET_COST_NO_ELIGIBLE_LOTS" not in _issue_codes(result)
        _assert_conserved(result, events, "TAX")

    def test_an_unlinked_tax_of_the_same_day_keeps_the_ladders_code(self):
        # Mixed day: beside the linked TAX 90, an unlinked TAX 91 of the same pool key follows the orphan income as it does
        # alone (SAME_DAY_INCOME, ASSET_COST_NO_ELIGIBLE_LOTS, 2 €), and never takes the linked code.
        income = _income(80, "DIVIDEND", "50", dt="2025-03-10")
        alone = _run_linked([self._LOT_C], [income, _tax(91, "-2", dt="2025-03-10")])
        reference = _group_of(alone, 91)
        assert (reference.rule, reference.operation_allocations, reference.target_orphan) == ("SAME_DAY_INCOME", (), _d("2")), "precondition: TAX 91 alone"

        events = [income, _linked_tax(90, "-6", dt="2025-03-10", parent=80), _tax(91, "-2", dt="2025-03-10")]
        result = _run_linked([self._LOT_C], events)

        unlinked = _group_of(result, 91)
        assert (unlinked.rule, unlinked.source_transaction_ids, unlinked.operation_allocations, unlinked.target_orphan) == ("SAME_DAY_INCOME", (91,), (), _d("2"))
        assert [issue.params for issue in result.issues if issue.code == "ASSET_COST_NO_ELIGIBLE_LOTS"] == [issue.params for issue in alone.issues if issue.code == "ASSET_COST_NO_ELIGIBLE_LOTS"]
        _assert_orphan_with_its_income(result, 90, economic_type="TAX", amount="6", day="2025-03-10", parent_id=80, parent_day="2025-03-10")
        assert result.asset_orphan_taxes == _d("8")
        _assert_conserved(result, events, "TAX")

    def test_an_income_on_date_min_leaves_its_charge_orphan_without_overflow(self):
        # MF-SEC8-2b: an income on date.min has no day before, so no lot earned it; its linked FEE is orphan with it,
        # never an OverflowError. Before M2: SAME_DAY_TRADES on the lot bought that day.
        events = [_income(80, "DIVIDEND", "50", dt="0001-01-01"), _linked_fee(90, "-1", dt="0001-01-01", parent=80)]
        result = _run_linked([_buy(3, "5", "100", dt="0001-01-01")], events)

        assert result.asset_orphan_fees == _d("1")
        _assert_orphan_with_its_income(result, 90, economic_type="FEE", amount="1", day="0001-01-01", parent_id=80, parent_day="0001-01-01")


class TestLinkedChargeWaitingForItsIncome:
    """An income parent after ``replay_until`` waits, as a trade does in M1b: an empty LINKED_INCOME group (§1.3)."""

    _LOT_A = _buy(1, "10", "100", dt="2025-01-15")

    @pytest.mark.parametrize("income_type", ["DIVIDEND", "INTEREST"])
    @pytest.mark.parametrize("parent_in_the_engine", [pytest.param(True, id="income-among-the-engines-events"), pytest.param(False, id="income-known-by-its-facts")])
    def test_a_charge_linked_to_an_income_after_the_end_waits(self, income_type, parent_in_the_engine):
        # Retargeted from M1b (test_an_income_parent_after_the_end_stays_on_the_ladder_until_m2, the facts variant): a TAX of
        # 10 Mar linked to an income of 12 Mar; the analysis ends on 11 Mar. Before M2: OPEN_LOTS_FALLBACK put the TAX on
        # lot A. Now it waits, orphan, with the M1b code. The income is among the engine's events (a direct caller), or —
        # the service's shape, which loads income up to the end — known by its facts only.
        facts = None if parent_in_the_engine else _parent_facts("2025-03-12", tx_type=income_type)
        income = [_income(80, income_type, "50", dt="2025-03-12")] if parent_in_the_engine else []
        result = _run_linked([self._LOT_A], [*income, _linked_tax(90, "-6", dt="2025-03-10", parent=80, parent_facts=facts)], replay_until="2025-03-11")

        assert (_lot_taxes(result, 1), result.asset_orphan_taxes) == (_d("0"), _d("6"))
        _assert_waiting(result, 90, economic_type="TAX", amount="6", day="2025-03-10", parent_id=80, parent_day="2025-03-12", rule=_LINKED_INCOME)
        assert {"ASSET_COST_NO_ELIGIBLE_LOTS", _INCOME_ORPHAN} & set(_issue_codes(result)) == set()

    @pytest.mark.parametrize(("method", "lot"), [pytest.param(LotMatchingMethod.FIFO, 2, id="FIFO"), pytest.param(LotMatchingMethod.LIFO, 1, id="LIFO")])
    def test_a_fee_linked_to_an_income_after_the_end_waits_in_both_methods(self, method, lot):
        # Lots 1 and 2 open, SELL 3 of 10 Feb closes one of them (FIFO lot 1, LIFO lot 2); the FEE of 1 Mar is linked to a
        # dividend of 20 Mar the service knows by its facts; the analysis ends on 15 Mar. Before M2: OPEN_LOTS_FALLBACK on
        # the lot each method left open. Now it waits in both methods.
        txs = [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-05"), _sell(3, "10", "120", dt="2025-02-10")]
        events = [_linked_fee(90, "-5", dt="2025-03-01", parent=80, parent_facts=_parent_facts("2025-03-20", tx_type="DIVIDEND"))]
        result = _run_linked(txs, events, replay_until="2025-03-15", matching_method=method)

        assert (_lot_fees(result, lot), result.asset_orphan_fees) == (_d("0"), _d("5"))
        _assert_waiting(result, 90, economic_type="FEE", amount="5", day="2025-03-01", parent_id=80, parent_day="2025-03-20", rule=_LINKED_INCOME)


class TestLinkedChargeOnAnIncomeStaysOnTheLadder:
    """The cases M2 leaves on the ladder (§1.4): same rule and numbers as before M2, and no issue names the parent."""

    _LOT_A = _buy(1, "10", "100", dt="2025-01-15")
    _LOT_C = _buy(3, "5", "100", dt="2025-03-10")

    @pytest.mark.parametrize(
        ("lots_at_broker_2", "replay_until", "income_in_the_engine"),
        [
            pytest.param(True, None, True, id="income-earned-at-broker-2"),
            pytest.param(False, None, True, id="income-orphan-at-broker-2"),
            pytest.param(False, "2025-03-11", False, id="income-after-the-end-at-broker-2"),
        ],
    )
    def test_an_income_of_another_broker_is_never_followed_nor_named(self, lots_at_broker_2, replay_until, income_in_the_engine):
        # Defence of rule 5: the dividend 80 sits at broker 2 (its broker edited after the link); the FEE of broker 1 names
        # it. Earned, orphan, or after the end (known by its facts), the FEE takes broker 1's ladder: SAME_DAY_TRADES on
        # lot C, as before M2, and no issue carries the parent.
        txs = [self._LOT_A, self._LOT_C, *([_buy(5, "10", "100", dt="2025-01-15", broker_id=2)] if lots_at_broker_2 else [])]
        income = [_income(80, "DIVIDEND", "50", dt="2025-03-10", broker_id=2)] if income_in_the_engine else []
        facts = _parent_facts("2025-03-10" if income_in_the_engine else "2025-03-12", tx_type="DIVIDEND", broker_id=2)
        result = _run_linked(txs, [*income, _linked_fee(90, "-1", dt="2025-03-10", parent=80, parent_facts=facts)], replay_until=replay_until)

        assert (_lot_fees(result, 1), _lot_fees(result, 3)) == (_d("0"), _d("1"))
        group = _group_of(result, 90)
        assert (group.rule, _operations(group)) == ("SAME_DAY_TRADES", [("OPENING", 3, (3,))])
        _assert_parent_never_named(result)

    @pytest.mark.parametrize("replay_until", [pytest.param(None, id="no-end"), pytest.param("2025-03-11", id="with-an-end")])
    def test_a_parent_absent_with_no_facts_keeps_the_ladder_beside_a_dividend(self, replay_until):
        # A TAX linked to row 81, which the engine never saw and knows no facts of, on the day of dividend 80: it follows
        # that income through the ladder (SAME_DAY_INCOME), as before M2 — never LINKED_INCOME by guess.
        result = _run_linked(
            [self._LOT_A, self._LOT_C],
            [_income(80, "DIVIDEND", "50", dt="2025-03-10"), _linked_tax(90, "-6", dt="2025-03-10", parent=81)],
            replay_until=replay_until,
        )

        assert (_lot_taxes(result, 1), _lot_taxes(result, 3)) == (_d("6"), _d("0"))
        assert _group_of(result, 90).rule == "SAME_DAY_INCOME"
        _assert_parent_never_named(result)

    # M2b retarget: test_an_income_known_only_by_its_facts_and_not_after_the_end_keeps_the_ladder[income-dated-on-the-end|
    # income-before-the-end] and test_without_an_end_an_income_known_only_by_its_facts_keeps_the_ladder (SAME_DAY_TRADES on
    # lot C) go on the lots held the day before the income now —
    # TestLinkedChargeOnAZeroIncome.test_an_income_known_only_by_its_facts_and_not_after_the_end_goes_on_its_day_befores_lots
    # and TestLinkedChargeOnAZeroIncome.test_without_an_end_an_income_known_only_by_its_facts_goes_on_its_day_befores_lots.


class TestLinkedIncomeConservationAndAudit:
    # Lot A (10) and B (30) earn the dividend of 10 Mar; lot C opens that day. The INTEREST of 15 Jan is orphan (lot A
    # is bought that day). The end is 31 Mar.
    _TXS = [_buy(1, "10", "100", dt="2025-01-15"), _buy(2, "30", "100", dt="2025-02-03"), _buy(3, "5", "100", dt="2025-03-10")]

    def test_on_its_income_orphan_with_it_waiting_and_unlinked_conserve_both_totals(self):
        events = [
            _income(80, "DIVIDEND", "50", dt="2025-03-10"),
            _income(81, "INTEREST", "7", dt="2025-01-15"),
            _linked_fee(90, "-1", dt="2025-03-10", parent=80),
            _fee(91, "-2", dt="2025-03-10"),
            _linked_fee(92, "-10", dt="2025-03-12", parent=80, native_currency="USD", target_amount="-9"),
            _linked_fee(93, "-3", dt="2025-01-20", parent=81),
            _linked_tax(94, "-6", dt="2025-03-10", parent=80),
            _linked_tax(95, "-4", dt="2025-03-20", parent=82, parent_facts=_parent_facts("2025-04-02", tx_type="INTEREST")),
            _tax(96, "-1.5", dt="2025-03-20"),
        ]
        result = _run_linked(self._TXS, events, replay_until="2025-03-31")

        for event in events:
            _group_of(result, event.transaction_id)
        _assert_on_its_income(result, 90, 80, economic_type="FEE", amount="1", day="2025-03-10")
        _assert_on_its_income(result, 92, 80, economic_type="FEE", amount="9", day="2025-03-12", native="10")
        _assert_on_its_income(result, 94, 80, economic_type="TAX", amount="6", day="2025-03-10")
        _assert_orphan_with_its_income(result, 93, economic_type="FEE", amount="3", day="2025-01-20", parent_id=81, parent_day="2025-01-15")
        _assert_waiting(result, 95, economic_type="TAX", amount="4", day="2025-03-20", parent_id=82, parent_day="2025-04-02", rule=_LINKED_INCOME)
        assert (_group_of(result, 91).rule, _group_of(result, 96).rule) == ("SAME_DAY_TRADES", "OPEN_LOTS_FALLBACK")
        # 0.25 + 2.25 on A, 0.75 + 6.75 on B, the unlinked 2 on C.
        assert {lot: _lot_fees(result, lot) for lot in (1, 2, 3)} == {1: _d("2.5"), 2: _d("7.5"), 3: _d("2")}
        assert (result.asset_orphan_income, result.asset_orphan_fees, result.asset_orphan_taxes) == (_d("7"), _d("3"), _d("4"))
        _assert_conserved(result, events, "FEE")
        _assert_conserved(result, events, "TAX")

    def test_the_linked_groups_sort_by_charge_date_and_id_before_the_pools(self):
        # FEE 92 (8 Mar, dated before its dividend: rule 4, never judged) and 93 (10 Mar) on dividend 80; FEE 91 (10 Mar) on
        # BUY C; FEE 95 unlinked. One list of linked groups by (charge date, id), whatever their rule, then the pool.
        result = _run_linked(
            self._TXS,
            [
                _income(80, "DIVIDEND", "50", dt="2025-03-10"),
                _fee(95, "-1", dt="2025-03-10"),
                _linked_fee(93, "-1", dt="2025-03-10", parent=80),
                _linked_fee(91, "-1", dt="2025-03-10", parent=3),
                _linked_fee(92, "-1", dt="2025-03-08", parent=80),
            ],
        )

        layout = [(group.rule, group.source_transaction_ids) for group in result.economic_allocation_groups if group.economic_type == "FEE"]
        assert layout == [(_LINKED_INCOME, (92,)), ("LINKED_TRADE", (91,)), (_LINKED_INCOME, (93,)), ("SAME_DAY_TRADES", (95,))]
        _assert_on_its_income(result, 92, 80, economic_type="FEE", amount="1", day="2025-03-08")

    def test_the_linked_income_group_validates_through_the_api_schema(self):
        result = _run_linked(self._TXS, [_income(80, "DIVIDEND", "50", dt="2025-03-10"), _linked_fee(90, "-1", dt="2025-03-10", parent=80)])

        [mapped] = [group for group in map_economic_groups(result.economic_allocation_groups) if group.economic_type == "FEE"]
        assert (mapped.rule, mapped.source_transaction_ids) == (_LINKED_INCOME, [90])
        assert [(op.context, op.operation_transaction_id, [allocation.lot_id for allocation in op.lot_allocations]) for op in mapped.operation_allocations] == [("INCOME", 80, [1, 2])]

    def test_a_linked_income_rule_is_a_rule_of_the_api(self):
        # Independent of the engine: the API's AllocationRuleLiteral must accept the rule M2 adds (§1.5).
        group = EconomicAllocationGroup(
            economic_type="FEE",
            asset_id=ASSET_ID,
            broker_id=1,
            date=date(2025, 3, 10),
            native_currency="EUR",
            target_currency="EUR",
            rule=_LINKED_INCOME,
            source_transaction_ids=(90,),
            native_pool_total=_d("1"),
            target_pool_total=_d("1"),
            operation_allocations=(
                TargetOperationAllocation(
                    context="INCOME",
                    operation_transaction_id=80,
                    weight=_d("1"),
                    lot_allocations=(EconomicLotAllocation(lot_id=1, weight=_d("1"), native_amount=_d("1"), target_amount=_d("1")),),
                ),
            ),
        )

        [mapped] = map_economic_groups([group])
        assert (mapped.rule, mapped.source_transaction_ids) == (_LINKED_INCOME, [90])

    def test_a_missing_rate_degrades_the_charges_own_group_not_through_its_income(self):
        # §1.6: the weights of a LINKED_INCOME group are quantities, so the income's missing rate degrades no linked charge;
        # the charge's own missing rate degrades its group, on the lots of the income.
        result = _run_linked(self._TXS, [_income(80, "DIVIDEND", "50", dt="2025-03-10"), _linked_fee(90, "-1", dt="2025-03-10", parent=80)])
        groups = result.economic_allocation_groups
        fee_index, income_index = _group_index(groups, 90), _group_index(groups, 80)
        assert groups[fee_index].rule == _LINKED_INCOME, "precondition: the FEE is on its income"

        income_without_rate = withheld_economics(groups, unconvertible_event_ids={80}, unconvertible_trade_ids={80}, trade_currency_by_id={80: "USD"})
        assert (fee_index in income_without_rate.amount_degraded, fee_index in income_without_rate.split_degraded, income_index in income_without_rate.amount_degraded) == (False, False, True)
        assert income_without_rate.fees_from == {}

        fee_without_rate = withheld_economics(groups, unconvertible_event_ids={90}, unconvertible_trade_ids=set(), trade_currency_by_id={})
        assert (fee_without_rate.amount_degraded, fee_without_rate.fees_from) == (frozenset({fee_index}), {1: date(2025, 3, 10), 2: date(2025, 3, 10)})


# --------------------------------------------------------------------------- #
# Project 66, M2b — a charge linked to an income the engine holds no event of
# --------------------------------------------------------------------------- #
#
# Decision (b) of the consultant: the service's income loader drops a zero-amount DIVIDEND/INTEREST, so the engine holds
# no income event for it, while the API accepts one (rule 11 skips zero) and the parents' read still hands the engine its
# facts (``event.parent``). When the parent is not among the engine's income events but its facts say DIVIDEND or
# INTEREST, of the charge's broker, not after ``replay_until``, the charge goes on
# ``_holding_operations(parent broker, day_before(parent date), …, "INCOME", operation_transaction_id=parent id)``: the
# same calculation as M2, rule LINKED_INCOME. No lot on that day → orphan with the M2 code, its parent id and date read
# from the facts. The engine's income event still wins over the facts; a zero income after the end still waits (M1b); an
# unlinked charge on the zero income's day keeps today's path; another broker, or no facts, keeps the ladder.
# In a pure test «a zero-amount income» is: no income EconomicEvent for it, and the charge's ``parent`` facts.


def _zero_income_facts(day: str, income_type: str = "DIVIDEND", broker_id: int = 1):
    """The facts the service reads of a zero-amount income: the engine holds no event of it."""
    return _parent_facts(day, tx_type=income_type, broker_id=broker_id)


def _assert_on_its_zero_income(result, reference, charge_id: int, parent_id: int, *, economic_type: str, amount: str, day: str, native: str | None = None) -> None:
    """The charge is alone in its LINKED_INCOME group, dated on itself, with one INCOME operation naming its parent, all of
    it allocated, on exactly the lot allocations of ``reference``: the same charge linked to a real income event of the
    parent's day (the M2 calculation, §7.2)."""
    group = _group_of(result, charge_id)
    target_total, native_total = _d(amount), _d(native if native is not None else amount)
    expected = _group_of(reference, charge_id)
    assert expected.rule == _LINKED_INCOME, f"precondition: in the reference the charge follows its income event: {expected}"
    assert (group.economic_type, group.rule, group.source_transaction_ids, group.date) == (economic_type, _LINKED_INCOME, (charge_id,), date.fromisoformat(day)), group
    assert [(op.context, op.operation_transaction_id) for op in group.operation_allocations] == [("INCOME", parent_id)], group
    assert (group.native_pool_total, group.target_pool_total, group.native_orphan, group.target_orphan) == (native_total, target_total, _d("0"), _d("0"))
    [operation] = group.operation_allocations
    [expected_operation] = expected.operation_allocations
    assert operation.lot_allocations == expected_operation.lot_allocations


def _income_twin(txs, events: list[EconomicEvent], *, parent_id: int, income_type: str, day: str, **kwargs):
    """The reference run: the same transactions and charges, plus a real income event of 50 € for the parent on ``day``."""
    return _run_linked(txs, [_income(parent_id, income_type, "50", dt=day), *events], **kwargs)


class TestLinkedChargeOnAZeroIncome:
    """M2b: a charge linked to an income the engine holds no event of (a zero amount) goes on the lots held the day
    before that income, by quantity — not on the ladder of its own day."""

    # Lots 1 and 2 (10 units each); SELL 3 of 5 units on 1 Feb leaves 5 + 10 in FIFO, 10 + 5 in LIFO. The zero income is
    # of 10 Mar; BUY 4 opens lot 4 (lot C) that same day.
    _HELD = [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-05"), _sell(3, "5", "120", dt="2025-02-01"), _buy(4, "10", "100", dt="2025-03-10")]

    @pytest.mark.parametrize("income_type", ["DIVIDEND", "INTEREST"])
    @pytest.mark.parametrize(
        ("method", "expected"),
        [pytest.param(LotMatchingMethod.FIFO, {1: "1", 2: "2", 4: "0"}, id="FIFO"), pytest.param(LotMatchingMethod.LIFO, {1: "2", 2: "1", 4: "0"}, id="LIFO")],
    )
    def test_a_fee_linked_to_a_zero_income_goes_on_the_lots_held_the_day_before(self, method, expected, income_type):
        # FEE of 3 € of 10 Mar linked to the zero income 80. Today: SAME_DAY_TRADES puts all of it on lot 4, bought that
        # day. M2b: the lots each method left holding on 9 Mar, by quantity, rule LINKED_INCOME, never on lot 4.
        events = [_linked_fee(90, "-3", dt="2025-03-10", parent=80, parent_facts=_zero_income_facts("2025-03-10", income_type))]
        result = _run_linked(self._HELD, events, replay_until="2025-03-31", matching_method=method)

        ladder = _group_of(_run_linked(self._HELD, [_fee(90, "-3", dt="2025-03-10")], replay_until="2025-03-31", matching_method=method), 90)
        assert (ladder.rule, _operations(ladder)) == ("SAME_DAY_TRADES", [("OPENING", 4, (4,))]), "precondition: the ladder of the FEE's day is lot 4"
        group = _group_of(result, 90)
        assert {lot: _lot_fees(result, lot) for lot in (1, 2, 4)} == {lot: _d(value) for lot, value in expected.items()}
        assert 4 not in [lot for lot, _weight in _lot_shares(group)], group
        assert (group.rule, group.operation_allocations) != (ladder.rule, ladder.operation_allocations)
        twin = _income_twin(self._HELD, events, parent_id=80, income_type=income_type, day="2025-03-10", replay_until="2025-03-31", matching_method=method)
        _assert_on_its_zero_income(result, twin, 90, 80, economic_type="FEE", amount="3", day="2025-03-10")
        assert (result.asset_orphan_fees, result.asset_orphan_income, result.issues) == (_d("0"), _d("0"), [])

    def test_a_tax_linked_to_a_zero_interest_uses_the_interests_day_before(self):
        # Lots A (10) and B (30); zero INTEREST 80 of 10 Mar; BUY 4 opens lot 4 (20 units) on 12 Mar; TAX of 4 € of 13 Mar
        # linked to the interest. Today: no income event, so PREVIOUS_DAY_TRADES puts all of it on lot 4. M2b: the
        # interest's 9 Mar, 1 / 3 / 0.
        txs = [_buy(1, "10", "100", dt="2025-01-15"), _buy(2, "30", "100", dt="2025-02-03"), _buy(4, "20", "100", dt="2025-03-12")]
        events = [_linked_tax(90, "-4", dt="2025-03-13", parent=80, parent_facts=_zero_income_facts("2025-03-10", "INTEREST"))]
        result = _run_linked(txs, events, replay_until="2025-03-31")

        assert (_lot_taxes(result, 1), _lot_taxes(result, 2), _lot_taxes(result, 4)) == (_d("1"), _d("3"), _d("0"))
        twin = _income_twin(txs, events, parent_id=80, income_type="INTEREST", day="2025-03-10", replay_until="2025-03-31")
        _assert_on_its_zero_income(result, twin, 90, 80, economic_type="TAX", amount="4", day="2025-03-13")
        assert (result.asset_orphan_taxes, result.issues) == (_d("0"), [])

    @pytest.mark.parametrize(
        ("economic_type", "charge_day"),
        [
            pytest.param("FEE", "2025-03-13", id="fee-days-later-today-open-lots-fallback"),
            pytest.param("TAX", "2025-03-10", id="tax-same-day-today-same-day-trades"),
        ],
    )
    def test_a_charge_linked_to_a_zero_income_no_lot_earned_is_orphan_with_it(self, economic_type, charge_day):
        # The only lot is opened on the zero income's day: nothing is held on 9 Mar. Today the charge finds lot C through
        # the ladder. M2b: orphan with its income, the M2 code, dated on the charge, parent id and date from the facts.
        events = [_linked_cost(90, economic_type, "-1", dt=charge_day, parent=80, parent_facts=_zero_income_facts("2025-03-10"))]
        result = _run_linked([_buy(3, "5", "100", dt="2025-03-10")], events, replay_until="2025-03-31")

        lot_cost, orphan = (_lot_fees, result.asset_orphan_fees) if economic_type == "FEE" else (_lot_taxes, result.asset_orphan_taxes)
        assert (lot_cost(result, 3), orphan) == (_d("0"), _d("1"))
        _assert_orphan_with_its_income(result, 90, economic_type=economic_type, amount="1", day=charge_day, parent_id=80, parent_day="2025-03-10")
        codes = _issue_codes(result)
        assert {"ASSET_COST_NO_ELIGIBLE_LOTS", "ASSET_INCOME_NO_ELIGIBLE_LOTS", _AFTER_RANGE} & set(codes) == set(), codes
        assert result.asset_orphan_income == _d("0")
        _assert_conserved(result, events, economic_type)
        assert result.analysis_status == "DEGRADED"

    @pytest.mark.parametrize(
        ("facts_day", "expected"),
        [pytest.param("2025-03-11", ("2", "1"), id="income-dated-on-the-end"), pytest.param("2025-03-05", ("3", "0"), id="income-before-the-end")],
    )
    def test_an_income_known_only_by_its_facts_and_not_after_the_end_goes_on_its_day_befores_lots(self, facts_day, expected):
        # M2b flip of TestLinkedChargeOnAnIncomeStaysOnTheLadder.test_an_income_known_only_by_its_facts_and_not_after_the_end_
        # keeps_the_ladder (SAME_DAY_TRADES on lot C). The facts say DIVIDEND, on or before the end, and the engine holds no
        # such event (the service's zero amount). The FEE (3 € here, 1 € before, so the thirds stay exact) goes on the lots
        # held the day before the facts' date: on 10 Mar lot A (10) and lot C (5) → 2 / 1; on 4 Mar lot A alone → 3 / 0.
        lots = [_buy(1, "10", "100", dt="2025-01-15"), _buy(3, "5", "100", dt="2025-03-10")]
        events = [_linked_fee(90, "-3", dt="2025-03-10", parent=80, parent_facts=_parent_facts(facts_day, tx_type="DIVIDEND"))]
        result = _run_linked(lots, events, replay_until="2025-03-11")

        assert (_lot_fees(result, 1), _lot_fees(result, 3)) == (_d(expected[0]), _d(expected[1]))
        twin = _income_twin(lots, events, parent_id=80, income_type="DIVIDEND", day=facts_day, replay_until="2025-03-11")
        _assert_on_its_zero_income(result, twin, 90, 80, economic_type="FEE", amount="3", day="2025-03-10")
        assert _after_range_issues(result) == []

    def test_without_an_end_an_income_known_only_by_its_facts_goes_on_its_day_befores_lots(self):
        # M2b flip of TestLinkedChargeOnAnIncomeStaysOnTheLadder.test_without_an_end_an_income_known_only_by_its_facts_keeps_
        # the_ladder (SAME_DAY_TRADES on lot C). No replay_until (a direct caller): nothing is after the end, and the facts
        # of 12 Mar say DIVIDEND; the FEE of 10 Mar (3 € here, 1 € before) goes on the lots held on 11 Mar: lot A (10) and
        # lot C (5), 2 / 1.
        lots = [_buy(1, "10", "100", dt="2025-01-15"), _buy(3, "5", "100", dt="2025-03-10")]
        events = [_linked_fee(90, "-3", dt="2025-03-10", parent=80, parent_facts=_parent_facts("2025-03-12", tx_type="DIVIDEND"))]
        result = _run_linked(lots, events)

        assert (_lot_fees(result, 1), _lot_fees(result, 3)) == (_d("2"), _d("1"))
        twin = _income_twin(lots, events, parent_id=80, income_type="DIVIDEND", day="2025-03-12")
        _assert_on_its_zero_income(result, twin, 90, 80, economic_type="FEE", amount="3", day="2025-03-10")
        assert _after_range_issues(result) == []

    def test_zero_income_charges_conserve_both_totals_beside_the_others(self):
        # Lots A (10, 15 Jan), B (30, 3 Feb), C (5, 10 Mar); end 31 Mar. Dividend 80 has an event; 82 (10 Mar) and 83 (15
        # Jan, nothing held on 14 Jan) are zero incomes known by their facts; 84 is an interest after the end.
        txs = [_buy(1, "10", "100", dt="2025-01-15"), _buy(2, "30", "100", dt="2025-02-03"), _buy(3, "5", "100", dt="2025-03-10")]
        zero_dividend, zero_interest = _zero_income_facts("2025-03-10"), _zero_income_facts("2025-01-15", "INTEREST")
        events = [
            _income(80, "DIVIDEND", "50", dt="2025-03-10"),
            _linked_fee(90, "-1", dt="2025-03-10", parent=80),
            _linked_fee(91, "-2", dt="2025-03-10", parent=82, parent_facts=zero_dividend),
            _linked_tax(92, "-6", dt="2025-03-12", parent=83, parent_facts=zero_interest),
            _linked_fee(93, "-10", dt="2025-03-12", parent=82, parent_facts=zero_dividend, native_currency="USD", target_amount="-9"),
            _fee(94, "-2", dt="2025-03-10"),
            _tax(95, "-1.5", dt="2025-03-20"),
            _linked_tax(96, "-4", dt="2025-03-20", parent=84, parent_facts=_zero_income_facts("2025-04-02", "INTEREST")),
        ]
        result = _run_linked(txs, events, replay_until="2025-03-31")

        for event in events:
            _group_of(result, event.transaction_id)
        twin = _income_twin(txs, [event for event in events if event.transaction_id in (91, 93)], parent_id=82, income_type="DIVIDEND", day="2025-03-10", replay_until="2025-03-31")
        _assert_on_its_income(result, 90, 80, economic_type="FEE", amount="1", day="2025-03-10")
        _assert_on_its_zero_income(result, twin, 91, 82, economic_type="FEE", amount="2", day="2025-03-10")
        _assert_on_its_zero_income(result, twin, 93, 82, economic_type="FEE", amount="9", day="2025-03-12", native="10")
        _assert_orphan_with_its_income(result, 92, economic_type="TAX", amount="6", day="2025-03-12", parent_id=83, parent_day="2025-01-15")
        _assert_waiting(result, 96, economic_type="TAX", amount="4", day="2025-03-20", parent_id=84, parent_day="2025-04-02", rule=_LINKED_INCOME)
        unlinked = _group_of(result, 94)
        assert (unlinked.rule, unlinked.source_transaction_ids, _operations(unlinked)) == ("SAME_DAY_TRADES", (94,), [("OPENING", 3, (3,))])
        assert _group_of(result, 95).rule == "OPEN_LOTS_FALLBACK"
        # A: 0.25 + 0.5 + 2.25; B: 0.75 + 1.5 + 6.75; C: the unlinked 2.
        assert {lot: _lot_fees(result, lot) for lot in (1, 2, 3)} == {1: _d("3"), 2: _d("9"), 3: _d("2")}
        assert (result.asset_orphan_fees, result.asset_orphan_taxes) == (_d("0"), _d("10"))
        _assert_conserved(result, events, "FEE")
        _assert_conserved(result, events, "TAX")


class TestLinkedChargeOnAZeroIncomeKeepsItsGuards:
    """The cases M2b must not move (green before and after): the engine's income event decides over the facts, another
    broker's income and a parent that is not an income keep the ladder, a zero income after the end waits, an unlinked
    charge on a zero income's day keeps today's path."""

    _LOT_A = _buy(1, "10", "100", dt="2025-01-15")
    _LOT_B = _buy(2, "30", "100", dt="2025-02-03")
    _LOT_C = _buy(3, "5", "100", dt="2025-03-10")

    @pytest.mark.parametrize("facts_day", [pytest.param("2025-03-12", id="facts-later-lot-c-held-on-their-day-before"), pytest.param("2025-02-01", id="facts-earlier-lot-a-alone")])
    def test_the_engines_income_event_wins_over_facts_of_another_day(self, facts_day):
        # The engine holds dividend 80 of 10 Mar; the facts claim another day, not after the end, whose day before holds
        # another set of lots. The event decides: the dividend's 9 Mar, 0.25 / 0.75 / 0.
        result = _run_linked(
            [self._LOT_A, self._LOT_B, self._LOT_C],
            [_income(80, "DIVIDEND", "50", dt="2025-03-10"), _linked_fee(90, "-1", dt="2025-03-10", parent=80, parent_facts=_parent_facts(facts_day, tx_type="DIVIDEND"))],
            replay_until="2025-03-31",
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2), _lot_fees(result, 3)) == (_d("0.25"), _d("0.75"), _d("0"))
        _assert_on_its_income(result, 90, 80, economic_type="FEE", amount="1", day="2025-03-10")
        assert _after_range_issues(result) == []

    @pytest.mark.parametrize("replay_until", [pytest.param(None, id="no-end"), pytest.param("2025-03-31", id="with-an-end")])
    def test_a_zero_income_of_another_broker_keeps_the_ladder_and_is_never_named(self, replay_until):
        # The zero dividend 80 is at broker 2, which holds lot 5 on 9 Mar; the FEE of broker 1 names it. Rule 5: broker 1's
        # ladder, SAME_DAY_TRADES on lot C; lot 5 gets nothing, and no issue carries the parent.
        txs = [self._LOT_A, self._LOT_C, _buy(5, "10", "100", dt="2025-01-15", broker_id=2)]
        events = [_linked_fee(90, "-1", dt="2025-03-10", parent=80, parent_facts=_zero_income_facts("2025-03-10", broker_id=2))]
        result = _run_linked(txs, events, replay_until=replay_until)

        assert (_lot_fees(result, 1), _lot_fees(result, 3), _lot_fees(result, 5)) == (_d("0"), _d("1"), _d("0"))
        group = _group_of(result, 90)
        assert (group.rule, _operations(group)) == ("SAME_DAY_TRADES", [("OPENING", 3, (3,))])
        _assert_parent_never_named(result)

    @pytest.mark.parametrize("parent_type", ["BUY", "SELL", "ADJUSTMENT", "DEPOSIT"])
    def test_facts_that_are_not_an_income_keep_the_ladder(self, parent_type):
        # Parent 80 absent from the engine, its facts of 10 Mar not an income: never this branch. Read as an income it would
        # go on 9 Mar's lot A; the ladder puts it on lot C, bought on the FEE's day.
        result = _run_linked(
            [self._LOT_A, self._LOT_C],
            [_linked_fee(90, "-1", dt="2025-03-10", parent=80, parent_facts=_parent_facts("2025-03-10", tx_type=parent_type))],
            replay_until="2025-03-31",
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 3)) == (_d("0"), _d("1"))
        group = _group_of(result, 90)
        assert (group.rule, _operations(group)) == ("SAME_DAY_TRADES", [("OPENING", 3, (3,))])
        _assert_parent_never_named(result)

    @pytest.mark.parametrize("income_type", ["DIVIDEND", "INTEREST"])
    def test_a_zero_income_after_the_end_still_waits(self, income_type):
        # M1b before M2b: the zero income of 12 Mar lies after the end (11 Mar), though lot A is held on its day before. The
        # FEE of 10 Mar waits, orphan, in an empty LINKED_INCOME group with the after-range code — never on lot A.
        result = _run_linked(
            [self._LOT_A],
            [_linked_fee(90, "-5", dt="2025-03-10", parent=80, parent_facts=_zero_income_facts("2025-03-12", income_type))],
            replay_until="2025-03-11",
        )

        assert (_lot_fees(result, 1), result.asset_orphan_fees) == (_d("0"), _d("5"))
        _assert_waiting(result, 90, economic_type="FEE", amount="5", day="2025-03-10", parent_id=80, parent_day="2025-03-12", rule=_LINKED_INCOME)
        assert _INCOME_ORPHAN not in _issue_codes(result)

    def test_an_unlinked_tax_on_a_zero_incomes_day_keeps_todays_path(self):
        # A FEE linked to the zero dividend of 10 Mar hands the engine its facts; the unlinked TAX of that day must not see
        # the zero income (it has no event): it keeps the numbers it has alone, SAME_DAY_TRADES on lot C.
        txs = [self._LOT_A, self._LOT_C]
        alone = _run_linked(txs, [_tax(91, "-2", dt="2025-03-10")], replay_until="2025-03-31")
        reference = _group_of(alone, 91)
        assert (reference.rule, _operations(reference)) == ("SAME_DAY_TRADES", [("OPENING", 3, (3,))]), "precondition: TAX 91 alone"

        events = [_linked_fee(90, "-1", dt="2025-03-10", parent=80, parent_facts=_zero_income_facts("2025-03-10")), _tax(91, "-2", dt="2025-03-10")]
        result = _run_linked(txs, events, replay_until="2025-03-31")

        unlinked = _group_of(result, 91)
        assert (unlinked.rule, unlinked.source_transaction_ids, unlinked.operation_allocations) == (reference.rule, (91,), reference.operation_allocations)
        assert (_lot_taxes(result, 1), _lot_taxes(result, 3), result.asset_orphan_taxes) == (_d("0"), _d("2"), _d("0"))


class TestLinkedChargeQuantitySplit:
    """A linked charge splits over its parent's lots by quantity, as ``_split_trade_cost`` does for one trade."""

    def test_a_sell_closing_two_lots_unevenly_splits_its_fee_by_closed_quantity(self):
        # SELL 3 closes 10 of lot 1 and 15 of lot 2 (FIFO). FEE 5 € five days later, linked: 2 / 3. Today OPEN_LOTS_FALLBACK
        # puts all of it on lot 2, the only lot still open.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "30", "100", dt="2025-01-05"), _sell(3, "25", "120", dt="2025-02-10")],
            [_linked_fee(90, "-5", dt="2025-02-15", parent=3)],
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2)) == (_d("2"), _d("3"))
        group = _group_of(result, 90)
        assert group.rule == "LINKED_TRADE"
        [operation] = group.operation_allocations
        assert (operation.context, operation.operation_transaction_id, operation.weight) == ("CLOSURE", 3, _d("1"))
        assert [(allocation.lot_id, allocation.weight, allocation.target_amount) for allocation in operation.lot_allocations] == [(1, _d("0.4"), _d("2")), (2, _d("0.6"), _d("3"))]

    def test_a_crossing_parent_splits_its_fee_between_opening_and_closure(self):
        # Short lot 1 (SELL 10); BUY 2 of 15 covers it (q_close 10) and opens long lot 2 (q_open 5). FEE 30 € on 20 Jan
        # linked to the BUY: 20 to the closure, 10 to the opening; each operation weighs its share of the charge. Today
        # OPEN_LOTS_FALLBACK puts all 30 on lot 2, the only LONG lot.
        result = _run_linked(
            [_sell(1, "10", "100", dt="2025-01-01"), _buy(2, "15", "110", dt="2025-01-05")],
            [_linked_fee(90, "-30", dt="2025-01-20", parent=2)],
            broker_shorting={1: True},
        )

        assert (_lot_fees(result, 1), _lot_fees(result, 2)) == (_d("20"), _d("10"))
        group = _group_of(result, 90)
        assert group.rule == "LINKED_TRADE"
        assert _operations(group) == [("OPENING", 2, (2,)), ("CLOSURE", 2, (1,))]
        assert [(op.context, _cents(op.weight * group.target_pool_total)) for op in group.operation_allocations] == [("OPENING", _d("10.00")), ("CLOSURE", _d("20.00"))]
        assert sum((op.weight for op in group.operation_allocations), _d("0")) == _d("1")


class TestLinkedChargeRules:
    def test_a_tax_linked_to_a_sell_skips_same_day_income(self):
        # SELL 3 closes lot 1 on the day of a dividend. Today the TAX follows the income (SAME_DAY_INCOME, 3 / 3 over the
        # D-1 holdings); linked, it is a cost of the SELL's closure.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-05"), _sell(3, "10", "120", dt="2025-02-10")],
            [_income(80, "DIVIDEND", "50", dt="2025-02-10"), _linked_tax(90, "-6", dt="2025-02-10", parent=3)],
        )

        assert (_lot_taxes(result, 1), _lot_taxes(result, 2)) == (_d("6"), _d("0"))
        group = _group_of(result, 90)
        assert group.rule == "LINKED_TRADE"
        assert _operations(group) == [("CLOSURE", 3, (1,))]

    @pytest.mark.parametrize(("method", "closed_lot", "open_lot"), [pytest.param(LotMatchingMethod.FIFO, 1, 2, id="FIFO"), pytest.param(LotMatchingMethod.LIFO, 2, 1, id="LIFO")])
    def test_a_fee_linked_to_a_sell_goes_to_the_lots_the_method_closed(self, method, closed_lot, open_lot):
        # SELL 3 closes lot 1 in FIFO, lot 2 in LIFO. The FEE is dated five days later: today OPEN_LOTS_FALLBACK puts it on
        # the lot left open, the other one.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-05"), _sell(3, "10", "120", dt="2025-02-10")],
            [_linked_fee(90, "-5", dt="2025-02-15", parent=3)],
            matching_method=method,
        )

        assert (_lot_fees(result, closed_lot), _lot_fees(result, open_lot)) == (_d("5"), _d("0"))
        group = _group_of(result, 90)
        assert group.rule == "LINKED_TRADE"
        assert _operations(group) == [("CLOSURE", 3, (closed_lot,))]


class TestLinkedChargeAudit:
    def _result(self):
        # Lot 1 on 1 Jan; on 10 Jan BUY 2 opens lot 2 and SELL 3 closes 5 of lot 1. FEE 91 (BUY 2) and 93 (BUY 1) on 10 Jan,
        # FEE 92 (SELL 3) on 12 Jan, FEE 90 unlinked on 10 Jan, a dividend and a TAX linked to SELL 3.
        return _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-10"), _sell(3, "5", "120", dt="2025-01-10")],
            [
                _income(80, "DIVIDEND", "20", dt="2025-01-20"),
                _fee(90, "-1", dt="2025-01-10"),
                _linked_fee(93, "-3", dt="2025-01-10", parent=1),
                _linked_fee(92, "-2", dt="2025-01-12", parent=3),
                _linked_fee(91, "-4", dt="2025-01-10", parent=2),
                _linked_tax(94, "-6", dt="2025-01-20", parent=3),
            ],
        )

    def test_one_linked_group_per_charge_before_the_pools_of_its_type(self):
        result = self._result()
        layout = [(group.economic_type, group.rule, group.source_transaction_ids) for group in result.economic_allocation_groups]

        assert layout == [
            ("DIVIDEND", "ASSET_INCOME_HOLDINGS", (80,)),
            ("FEE", "LINKED_TRADE", (91,)),
            ("FEE", "LINKED_TRADE", (93,)),
            ("FEE", "LINKED_TRADE", (92,)),
            ("FEE", "SAME_DAY_MIXED_TRADES", (90,)),
            ("TAX", "LINKED_TRADE", (94,)),
        ]
        assert _operations(_group_of(result, 91)) == [("OPENING", 2, (2,))]
        assert _operations(_group_of(result, 93)) == [("OPENING", 1, (1,))]
        assert _operations(_group_of(result, 92)) == [("CLOSURE", 3, (1,))]
        for charge in (91, 92, 93, 94):
            group = _group_of(result, charge)
            assert (group.native_orphan, group.target_orphan) == (_d("0"), _d("0"))
            assert sum((allocation.target_amount for op in group.operation_allocations for allocation in op.lot_allocations), _d("0")) == group.target_pool_total

    def test_the_linked_groups_validate_through_the_api_schema(self):
        mapped = map_economic_groups(self._result().economic_allocation_groups)

        assert [group.rule for group in mapped if group.economic_type == "FEE"] == ["LINKED_TRADE", "LINKED_TRADE", "LINKED_TRADE", "SAME_DAY_MIXED_TRADES"]

    def test_a_linked_trade_rule_is_a_rule_of_the_api(self):
        # Independent of the engine: the API's AllocationRuleLiteral must accept the rule M1 adds.
        group = EconomicAllocationGroup(
            economic_type="FEE",
            asset_id=ASSET_ID,
            broker_id=1,
            date=date(2025, 1, 10),
            native_currency="EUR",
            target_currency="EUR",
            rule="LINKED_TRADE",
            source_transaction_ids=(90,),
            native_pool_total=_d("4"),
            target_pool_total=_d("4"),
            operation_allocations=(
                TargetOperationAllocation(
                    context="OPENING",
                    operation_transaction_id=2,
                    weight=_d("1"),
                    lot_allocations=(EconomicLotAllocation(lot_id=2, weight=_d("1"), native_amount=_d("4"), target_amount=_d("4")),),
                ),
            ),
        )

        [mapped] = map_economic_groups([group])
        assert (mapped.rule, mapped.source_transaction_ids) == ("LINKED_TRADE", [90])


class TestLinkedChargeWithheld:
    """A missing rate degrades only what it touches (§6.8, §7.6 of the M1 contract)."""

    @pytest.mark.parametrize("sibling_linked", [pytest.param(True, id="sibling-linked-to-lot-2"), pytest.param(False, id="sibling-unlinked")])
    def test_a_charge_without_a_rate_degrades_its_own_group_only(self, sibling_linked):
        # FEE 90 (linked to BUY 1) has no rate; FEE 91 is linked to BUY 2 or unlinked. Today both share one pool, and the
        # missing rate leaves the fees of lots 1 and 2 unknown.
        sibling = _linked_fee(91, "-3", dt="2025-01-10", parent=2) if sibling_linked else _fee(91, "-3", dt="2025-01-10")
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-10"), _buy(2, "10", "100", dt="2025-01-10")],
            [_linked_fee(90, "-2", dt="2025-01-10", parent=1), sibling],
        )
        groups = result.economic_allocation_groups

        withheld = withheld_economics(groups, unconvertible_event_ids={90}, unconvertible_trade_ids=set(), trade_currency_by_id={1: "EUR", 2: "EUR"})

        assert withheld.amount_degraded == frozenset({_group_index(groups, 90)})
        assert _group_index(groups, 91) not in withheld.amount_degraded
        assert withheld.fees_from == {1: date(2025, 1, 10)}
        assert withheld.split_degraded == frozenset()

    def test_a_parent_trade_without_a_rate_does_not_degrade_the_split(self):
        # BUY 1 in EUR and BUY 2 in USD (no rate) the same day; FEE 90 linked to BUY 2. Today the pool weighs both trades in
        # two currencies, one without a rate: split-degraded. A LINKED_TRADE group weighs one trade by quantity.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-10"), _buy(2, "10", "100", dt="2025-01-10", currency="USD", target_amount="-1000")],
            [_linked_fee(90, "-2", dt="2025-01-10", parent=2)],
        )
        groups = result.economic_allocation_groups

        withheld = withheld_economics(groups, unconvertible_event_ids=set(), unconvertible_trade_ids={2}, trade_currency_by_id={1: "EUR", 2: "USD"})

        assert _group_of(result, 90).rule == "LINKED_TRADE"
        assert withheld.split_degraded == frozenset()
        assert withheld.fees_from == {}
        assert _lot_fees(result, 2) == _d("2")


def _orphan_linked_charge(case: str, economic_type: str):
    """An orphan linked group of charge 90 (``economic_type``, 4 €), with its precondition asserted.

    - ``waiting-for-its-trade`` (M1b): lot A open; the charge of 10 Mar is linked to BUY 2 of 12 Mar; the end is 11 Mar.
    - ``waiting-for-its-income`` (M2 §1.3): lot A open; the charge of 10 Mar is linked to a dividend of 12 Mar, known by
      its facts; the end is 11 Mar.
    - ``orphan-with-its-income`` (M2, D12): lot C opened on 10 Mar earns nothing of the dividend of that day; the charge
      of 10 Mar is linked to it.
    """

    def charge(*, parent: int, **kwargs) -> EconomicEvent:
        return _linked_cost(90, economic_type, "-4", dt="2025-03-10", parent=parent, **kwargs)

    lot_a = _buy(1, "10", "100", dt="2025-01-15")
    if case == "waiting-for-its-trade":
        result = _run_linked([lot_a, _buy(2, "10", "100", dt="2025-03-12")], [charge(parent=2)], replay_until="2025-03-11")
        _assert_waiting(result, 90, economic_type=economic_type, amount="4", day="2025-03-10", parent_id=2, parent_day="2025-03-12")
    elif case == "waiting-for-its-income":
        result = _run_linked([lot_a], [charge(parent=80, parent_facts=_parent_facts("2025-03-12", tx_type="DIVIDEND"))], replay_until="2025-03-11")
        _assert_waiting(result, 90, economic_type=economic_type, amount="4", day="2025-03-10", parent_id=80, parent_day="2025-03-12", rule=_LINKED_INCOME)
    else:
        result = _run_linked([_buy(3, "5", "100", dt="2025-03-10")], [_income(80, "DIVIDEND", "50", dt="2025-03-10"), charge(parent=80)])
        _assert_orphan_with_its_income(result, 90, economic_type=economic_type, amount="4", day="2025-03-10", parent_id=80, parent_day="2025-03-10")
    return result


class TestOrphanLinkedChargeWithheld:
    """Project 66, M3 (GUARD): a linked group with no lot — waiting for its parent, or orphan with its income — whose
    charge has no rate leaves the asset's orphan total of its kind unknown (``orphan_unknown``), and no lot's figures:
    the group reaches no lot. The control: with every rate known nothing is withheld."""

    _ORPHAN_CASES = ["waiting-for-its-trade", "waiting-for-its-income", "orphan-with-its-income"]

    @pytest.mark.parametrize("case", _ORPHAN_CASES)
    @pytest.mark.parametrize(("economic_type", "kind"), [pytest.param("FEE", "fees", id="fee"), pytest.param("TAX", "taxes", id="tax")])
    def test_an_orphan_linked_charge_without_a_rate_leaves_its_kinds_orphan_total_unknown(self, case, economic_type, kind):
        result = _orphan_linked_charge(case, economic_type)
        groups = result.economic_allocation_groups

        withheld = withheld_economics(groups, unconvertible_event_ids={90}, unconvertible_trade_ids=set(), trade_currency_by_id={1: "EUR", 2: "EUR", 3: "EUR"})

        assert withheld.orphan_unknown == frozenset({kind})
        assert withheld.amount_degraded == frozenset({_group_index(groups, 90)})
        assert withheld.split_degraded == frozenset()
        assert (withheld.income_from, withheld.fees_from, withheld.taxes_from) == ({}, {}, {})

    @pytest.mark.parametrize("case", _ORPHAN_CASES)
    @pytest.mark.parametrize("economic_type", ["FEE", "TAX"])
    def test_control_an_orphan_linked_charge_with_its_rate_withholds_nothing(self, case, economic_type):
        groups = _orphan_linked_charge(case, economic_type).economic_allocation_groups

        withheld = withheld_economics(groups, unconvertible_event_ids=set(), unconvertible_trade_ids=set(), trade_currency_by_id={1: "EUR", 2: "EUR", 3: "EUR"})

        assert (withheld.orphan_unknown, withheld.amount_degraded, withheld.split_degraded) == (frozenset(), frozenset(), frozenset())


class TestTwoChargesLinkedToOneTrade:
    def test_two_charges_of_one_buy_make_two_groups_by_date_and_conserve(self):
        # Guard (MF review of M1): FEE 2 € on the BUY's day and FEE 3 € the day after, both linked to BUY 1. One
        # LINKED_TRADE group each, by date; 5 on the BUY's lot; native and target conserved.
        events = [_linked_fee(91, "-3", dt="2025-01-11", parent=1), _linked_fee(90, "-2", dt="2025-01-10", parent=1)]
        result = _run_linked([_buy(1, "10", "100", dt="2025-01-10")], events)

        fee_groups = [group for group in result.economic_allocation_groups if group.economic_type == "FEE"]
        assert [(group.rule, group.source_transaction_ids, group.date) for group in fee_groups] == [
            ("LINKED_TRADE", (90,), date(2025, 1, 10)),
            ("LINKED_TRADE", (91,), date(2025, 1, 11)),
        ]
        assert all(_operations(group) == [("OPENING", 1, (1,))] for group in fee_groups)
        assert _lot_fees(result, 1) == _d("5")
        native_allocated = sum((allocation.native_amount for group in fee_groups for op in group.operation_allocations for allocation in op.lot_allocations), _d("0"))
        native_orphan = sum((group.native_orphan for group in fee_groups), _d("0"))
        assert _sum_allocated_fees(result) + result.asset_orphan_fees == sum((abs(event.target_amount) for event in events), _d("0"))
        assert native_allocated + native_orphan == sum((abs(event.native_amount) for event in events), _d("0"))


class TestLinkedChargeDailySeries:
    """Guards (MF review of M1): the per-day cumulative FEE/TAX maps that feed the lots' net history
    (``extract_cost_outputs``), read on the engine's output with linked charges."""

    def test_a_mixed_pool_day_adds_the_linked_and_the_pooled_shares(self):
        # The 3.90 / 17.10 case: on its day lot A sums its linked 2 and its pooled 1.90, never one replacing the other.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-03-03"), _buy(2, "90", "100", dt="2025-03-03")],
            [_linked_fee(90, "-2", dt="2025-03-03", parent=1), _fee(91, "-19", dt="2025-03-03")],
        )
        fees_by_lot, _taxes_by_lot, fees_prefix_by_lot, _taxes_prefix_by_lot = extract_cost_outputs(result)
        day = date(2025, 3, 3)

        assert {lot_id: {d: _cents(v) for d, v in prefix.items()} for lot_id, prefix in fees_prefix_by_lot.items()} == {1: {day: _d("3.90")}, 2: {day: _d("17.10")}}
        assert {lot_id: _cents(value) for lot_id, value in fees_by_lot.items()} == {1: _d("3.90"), 2: _d("17.10")}

    def test_two_charges_of_one_buy_step_on_their_own_days(self):
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-10")],
            [_linked_fee(90, "-2", dt="2025-01-10", parent=1), _linked_fee(91, "-3", dt="2025-01-11", parent=1)],
        )
        fees_by_lot, _taxes_by_lot, fees_prefix_by_lot, _taxes_prefix_by_lot = extract_cost_outputs(result)

        assert fees_prefix_by_lot == {1: {date(2025, 1, 10): _d("2"), date(2025, 1, 11): _d("5")}}
        assert fees_by_lot == {1: _d("5")}

    def test_a_charge_dated_before_its_buy_is_in_the_lots_first_history_row(self):
        # FEE 4 € on 18 Jan linked to BUY 2 of 20 Jan. The prefix is keyed on the charge's date with the whole charge; the
        # value history starts on the opening day (no row before it) and that first row already carries the 4 €.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-20")],
            [_linked_fee(90, "-4", dt="2025-01-18", parent=2)],
        )
        fees_by_lot, taxes_by_lot, fees_prefix_by_lot, taxes_prefix_by_lot = extract_cost_outputs(result)
        assert fees_prefix_by_lot == {2: {date(2025, 1, 18): _d("4")}}
        assert _prefix_value_on_date(fees_prefix_by_lot[2], date(2025, 1, 20)) == _d("4")

        history_dates = [date(2025, 1, 15) + timedelta(days=offset) for offset in range(11)]
        points = build_value_history(
            selected_ids=[2],
            lots_by_id={lot.lot_id: lot for lot in result.lots},
            fragments_by_lot=group_fragments(result.fragment_intervals),
            closures_by_lot=group_closures(result.closures),
            market_prices={day: _d("100") for day in history_dates},
            history_dates=history_dates,
            fx_resolver=FxRateResolver("EUR"),
            income_prefix_by_lot={},
            fees_prefix_by_lot=fees_prefix_by_lot,
            taxes_prefix_by_lot=taxes_prefix_by_lot,
            at_cost_until=None,
            quote_base_quantity=1,
        )

        assert points, "the lot opened inside the window has a value history"
        first = min(points, key=lambda point: point.date)
        assert (first.date, first.allocated_fees) == (date(2025, 1, 20), _d("4"))
        assert all(point.date >= date(2025, 1, 20) for point in points)
        assert fees_by_lot == {2: _d("4")} and taxes_by_lot == {}

    def test_a_tax_after_the_closure_steps_the_closed_lot_on_its_own_date(self):
        # SELL 3 closes lot 1 on 3 Feb; the linked TAX of 6 Feb is a step on lot 1 from that day, nothing before.
        result = _run_linked(
            [_buy(1, "10", "100", dt="2025-01-01"), _buy(2, "10", "100", dt="2025-01-02"), _sell(3, "10", "120", dt="2025-02-03")],
            [_linked_tax(90, "-6", dt="2025-02-06", parent=3)],
        )
        _fees_by_lot, taxes_by_lot, _fees_prefix_by_lot, taxes_prefix_by_lot = extract_cost_outputs(result)

        assert taxes_prefix_by_lot == {1: {date(2025, 2, 6): _d("6")}}
        assert (_prefix_value_on_date(taxes_prefix_by_lot[1], date(2025, 2, 5)), _prefix_value_on_date(taxes_prefix_by_lot[1], date(2025, 2, 6))) == (_d("0"), _d("6"))
        assert taxes_by_lot == {1: _d("6")}
