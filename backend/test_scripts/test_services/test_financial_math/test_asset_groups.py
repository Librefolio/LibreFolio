"""
Project 74 (L1) — an asset held at several brokers, seen as one row (Dashboard › Positions, «Globale»).

Module under test: ``backend/app/services/financial_math/portfolio/asset_groups.py``. The developer's rule (16/11/2026):
the group is **the sum of its brokers, never a recomputation as if they were one broker**. Amounts add up; every derived
figure comes from the sums (a ratio of sums, never an average of ratios); a sum with an unknown part is unknown.

Pure tests — no DB, no server. Red before L1 by absence: the module does not exist (ImportError at collection).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio.yield_on_cost import YieldOnCostProvenance, YieldOnCostResult, YieldOnCostStatus, YieldOnCostUnavailableReason
from backend.app.services.financial_math.portfolio.asset_groups import (
    ContributionFacts,
    HoldingFacts,
    group_contributions,
    group_holdings,
    group_yield_on_cost,
    merge_by_kind,
)

D = Decimal
END = date(2026, 11, 16)


def holding(broker_id: int, **overrides) -> HoldingFacts:
    values = {
        "broker_id": broker_id,
        "quantity": D("10"),
        "market_value": D("1000"),
        "cost_basis": D("900"),
        "gain_loss": D("100"),
        "wac_per_unit": D("90"),
        "current_price": D("100"),
        "valuation_source": "MARKET_PRICE",
        "change_1d": D("10"),
        "previous_value": D("990"),
        "income": D("0"),
        "costs": D("0"),
        "first_transaction": date(2025, 1, 1),
        "oldest_open_lot": date(2025, 1, 1),
        "missing_fx_pair": None,
    }
    values.update(overrides)
    return HoldingFacts(**values)


def contribution(broker_id: int, **overrides) -> ContributionFacts:
    values = {
        "broker_id": broker_id,
        "held_at_start": True,
        "held_at_end": True,
        "start_value": D("1000"),
        "end_value": D("1100"),
        "end_cost": D("900"),
        "unrealized_delta": D("100"),
        "realized": None,
        "income": None,
        "fees": None,
        "period_pnl": D("100"),
        "cost_sold": D("0"),
        "sales": 0,
        "exits": 0,
        "moved_out_count": 0,
        "is_fully_sold": False,
        "opened": date(2025, 1, 1),
        "closed": None,
        "oldest_open_lot": date(2025, 1, 1),
        "closed_by": None,
        "closed_to_broker_id": None,
    }
    values.update(overrides)
    return ContributionFacts(**values)


# ─────────────────────────────────────────────────────────────── Portfolio


class TestGroupHoldings:
    def test_brief_example_ratio_of_sums_not_average(self):
        # A +10 % on 1 000, B −10 % on 9 000 → (100 − 900) / 10 000 = −8 %, never the 0 % of the average.
        a = holding(1, market_value=D("1100"), cost_basis=D("1000"), gain_loss=D("100"))
        b = holding(2, market_value=D("8100"), cost_basis=D("9000"), gain_loss=D("-900"))
        group = group_holdings([a, b], valuation_date=END)
        assert group.gain_loss == D("-800")
        assert group.gain_loss_ratio == D("-0.08")
        assert group.market_value == D("9200")
        assert group.cost_basis == D("10000")
        assert group.broker_ids == [1, 2]

    def test_lane_apple_ib_and_coinbase(self):
        # The lane's real rows (scope IB + Coinbase): +293,75 and +42,71 → +336,46 on 1 123,71 = 29,94 %, not 43,4 %.
        ib = holding(1, quantity=D("5.25"), market_value=D("1344.89"), cost_basis=D("1051.14"), gain_loss=D("293.75"), wac_per_unit=D("200.22"))
        cb = holding(5, quantity=D("0.45"), market_value=D("115.28"), cost_basis=D("72.57"), gain_loss=D("42.71"), wac_per_unit=D("161.26"))
        group = group_holdings([ib, cb], valuation_date=END)
        assert group.gain_loss == D("336.46")
        assert round(group.gain_loss_ratio * 100, 2) == D("29.94")
        assert group.quantity == D("5.70")

    def test_average_price_is_total_cost_over_total_quantity_in_the_rows_units(self):
        # PMC = Σ(PMC × qty) / Σ qty: (200 × 1 + 100 × 3) / 4 = 125 — also with quote_base_quantity ≠ 1 (BTP), the rows' unit.
        group = group_holdings([holding(1, quantity=D("1"), wac_per_unit=D("200")), holding(2, quantity=D("3"), wac_per_unit=D("100"))], valuation_date=END)
        assert group.wac_per_unit == D("125")

    def test_average_price_unknown_when_a_broker_has_none(self):
        group = group_holdings([holding(1), holding(2, wac_per_unit=None)], valuation_date=END)
        assert group.wac_per_unit is None

    def test_day_change_percent_from_the_sums(self):
        # Δ1: +10 on 990 and −30 on 2 030 → −20 on 3 020 = −0,66 %.
        group = group_holdings([holding(1, change_1d=D("10"), previous_value=D("990")), holding(2, change_1d=D("-30"), previous_value=D("2030"))], valuation_date=END)
        assert group.change_1d == D("-20")
        assert group.change_1d_percent == D("-0.66")

    def test_a_sum_with_an_unknown_part_is_unknown(self):
        group = group_holdings([holding(1), holding(2, market_value=None, gain_loss=None, change_1d=None)], valuation_date=END)
        assert group.market_value is None
        assert group.gain_loss is None
        assert group.gain_loss_ratio is None
        assert group.change_1d is None
        assert group.change_1d_percent is None

    def test_cost_incomplete_at_one_broker_leaves_ratio_and_annualized_unknown(self):
        group = group_holdings([holding(1), holding(2, cost_basis=None)], valuation_date=END)
        assert group.cost_basis is None
        assert group.gain_loss_ratio is None
        assert group.annualized_return is None

    def test_price_shown_only_when_the_brokers_agree(self):
        same = group_holdings([holding(1), holding(2)], valuation_date=END)
        assert same.current_price == D("100")
        assert same.valuation_source == "MARKET_PRICE"
        differ = group_holdings([holding(1), holding(2, current_price=D("98"), valuation_source="LAST_TRADE_PRICE")], valuation_date=END)
        assert differ.current_price is None
        # the less reliable source of the two, so the row's warning shows
        assert differ.valuation_source == "LAST_TRADE_PRICE"

    def test_annualized_net_return_on_the_summed_cost_from_the_first_transaction(self):
        # (Σ P&L + Σ income − Σ costs) / Σ cost = (200 + 30 − 10) / 2 000 = 11 %, over 365 days → 11 %.
        a = holding(1, gain_loss=D("100"), cost_basis=D("1000"), income=D("30"), costs=D("10"), first_transaction=date(2025, 11, 16))
        b = holding(2, gain_loss=D("100"), cost_basis=D("1000"), first_transaction=date(2026, 5, 1))
        group = group_holdings([a, b], valuation_date=END)
        assert group.annualized_return == pytest.approx(D("0.11"), abs=D("0.0001"))
        assert group.first_transaction == date(2025, 11, 16)

    def test_oldest_open_lot_is_the_oldest_of_the_brokers(self):
        group = group_holdings([holding(1, oldest_open_lot=date(2026, 3, 1)), holding(2, oldest_open_lot=date(2025, 6, 1)), holding(3, oldest_open_lot=None)], valuation_date=END)
        assert group.oldest_open_lot == date(2025, 6, 1)

    def test_one_broker_group_equals_its_row(self):
        row = holding(1)
        group = group_holdings([row], valuation_date=END)
        assert (group.quantity, group.market_value, group.gain_loss, group.wac_per_unit, group.current_price) == (row.quantity, row.market_value, row.gain_loss, row.wac_per_unit, row.current_price)


# ─────────────────────────────────────────────────────────────── Yield on cost (Q1: the sum)


def _yoc(status: YieldOnCostStatus, value: str | None = None, per_unit: str | None = None, count: int = 0, reason=None) -> YieldOnCostResult:
    provenance = YieldOnCostProvenance(
        window_start=date(2025, 11, 17),
        window_end=END,
        gross_income_transaction_count=count,
        gross_income_per_unit=Currency(code="EUR", amount=D(per_unit)) if per_unit is not None else None,
        net_zero=status == YieldOnCostStatus.AVAILABLE and value is not None and D(value) == 0,
    )
    return YieldOnCostResult(status=status, value=D(value) if value is not None else None, reason=reason, provenance=provenance)


class TestGroupYieldOnCost:
    def test_income_of_the_brokers_over_the_total_cost(self):
        # A: 2 €/unit on 10 units at 100 (2 %); B: 0,5 €/unit on 30 units at 50 (1 %) → (20 + 15) / (1 000 + 1 500) = 1,4 %.
        a = _yoc(YieldOnCostStatus.AVAILABLE, "0.02", "2", 2)
        b = _yoc(YieldOnCostStatus.AVAILABLE, "0.01", "0.5", 1)
        group = group_yield_on_cost([(a, D("10"), D("100")), (b, D("30"), D("50"))])
        assert group.status == YieldOnCostStatus.AVAILABLE
        assert group.value == D("0.014")
        assert group.provenance.gross_income_transaction_count == 3
        assert group.provenance.gross_income_per_unit.amount == D("0.875")  # 35 € over 40 units

    def test_a_broker_without_income_counts_its_cost(self):
        a = _yoc(YieldOnCostStatus.AVAILABLE, "0.02", "2", 1)
        b = _yoc(YieldOnCostStatus.NO_INCOME, "0", "0")
        group = group_yield_on_cost([(a, D("10"), D("100")), (b, D("10"), D("100"))])
        assert group.status == YieldOnCostStatus.AVAILABLE
        assert group.value == D("0.01")

    def test_no_income_anywhere_is_no_income(self):
        group = group_yield_on_cost([(_yoc(YieldOnCostStatus.NO_INCOME, "0", "0"), D("1"), D("10")), (_yoc(YieldOnCostStatus.NO_INCOME, "0", "0"), D("1"), D("10"))])
        assert group.status == YieldOnCostStatus.NO_INCOME
        assert group.value == D("0")

    def test_one_broker_unavailable_makes_the_group_unavailable(self):
        missing = _yoc(YieldOnCostStatus.UNAVAILABLE, reason=YieldOnCostUnavailableReason.MISSING_FX)
        group = group_yield_on_cost([(_yoc(YieldOnCostStatus.AVAILABLE, "0.02", "2", 1), D("10"), D("100")), (missing, D("1"), D("10"))])
        assert group.status == YieldOnCostStatus.UNAVAILABLE
        assert group.reason == YieldOnCostUnavailableReason.MISSING_FX
        assert group.value is None


# ─────────────────────────────────────────────────────────────── Period


class TestGroupContributions:
    def test_sums_and_return_on_the_summed_start_value(self):
        # A +10 % on 1 000, B −10 % on 9 000 → −800 on 10 000 = −8 %.
        a = contribution(1, start_value=D("1000"), period_pnl=D("100"), unrealized_delta=D("100"))
        b = contribution(2, start_value=D("9000"), period_pnl=D("-900"), unrealized_delta=D("-900"))
        group = group_contributions([a, b], date_from=date(2026, 1, 1), end=END)
        assert group.period_pnl == D("-800")
        assert group.period_pnl_percent == D("-0.0800")
        assert group.unrealized_delta_percent == D("-0.0800")
        assert group.start_value == D("10000")

    def test_brief_example_realized_is_the_sum_of_the_brokers(self):
        # Buy 10 @100 on A and 10 @200 on B, sell 5 on B @250: B's realized is 5 × (250 − 200) = +250. A single FIFO
        # over the two would say 5 × (250 − 100) = +750, a fake gain. The group takes the brokers' own figures.
        a = contribution(1, held_at_start=False, start_value=D("0"), end_value=D("2500"), end_cost=D("1000"), unrealized_delta=D("1500"), period_pnl=D("1500"))
        b = contribution(2, held_at_start=False, start_value=D("0"), end_value=D("1250"), end_cost=D("1000"), unrealized_delta=D("250"), realized=D("250"), period_pnl=D("500"), cost_sold=D("1000"), sales=1, exits=1)
        group = group_contributions([a, b], date_from=date(2026, 1, 1), end=END)
        assert group.realized == D("250")
        assert group.period_pnl == D("2000")
        assert group.end_cost == D("2000")

    def test_an_internal_transfer_between_the_brokers_nets_out(self):
        # A → B inside the period: A's row gains the tract V − C (+50), B's loses it; the group sees only the asset's own move.
        a = contribution(1, end_value=D("0"), held_at_end=False, unrealized_delta=D("50"), period_pnl=D("50"), is_fully_sold=True, exits=1, moved_out_count=1, closed=date(2026, 6, 1), closed_by="TRANSFER", closed_to_broker_id=2)
        b = contribution(2, held_at_start=False, start_value=D("0"), end_value=D("1100"), unrealized_delta=D("50"), period_pnl=D("50"))
        group = group_contributions([a, b], date_from=date(2026, 1, 1), end=END)
        assert group.period_pnl == D("100")
        assert group.is_fully_sold is False
        assert group.closed_by is None

    def test_closed_only_when_every_broker_is_closed(self):
        a = contribution(1, held_at_end=False, end_value=D("0"), is_fully_sold=True, realized=D("100"), period_pnl=D("100"), cost_sold=D("1000"), sales=1, exits=1, opened=date(2025, 1, 1), closed=date(2026, 3, 1), closed_by="SELL")
        b = contribution(2, held_at_end=False, end_value=D("0"), is_fully_sold=True, realized=D("100"), period_pnl=D("100"), cost_sold=D("1000"), sales=1, exits=1, opened=date(2025, 6, 1), closed=date(2026, 9, 1), closed_by="ADJUSTMENT")
        group = group_contributions([a, b], date_from=date(2026, 1, 1), end=END)
        assert group.is_fully_sold is True
        # the group closed when its last broker did
        assert group.closed_by == "ADJUSTMENT"
        # +200 on the 2 000 that left, over 01/01 → 01/09 (243 days): (1.1)^(365/243) − 1
        assert group.annualized_return == pytest.approx(D("0.1540"), abs=D("0.0005"))

    def test_closed_base_leaves_out_the_moves_between_the_brokers(self):
        # A moves all to B (counted tract), B sells all: the units left the group once, sold at B's cost.
        a = contribution(1, held_at_end=False, end_value=D("0"), is_fully_sold=True, period_pnl=D("50"), unrealized_delta=D("50"), exits=1, moved_out_count=1, opened=date(2025, 1, 1), closed=date(2026, 4, 1), closed_by="TRANSFER", closed_to_broker_id=2)
        b = contribution(2, held_at_start=False, start_value=D("0"), held_at_end=False, end_value=D("0"), is_fully_sold=True, realized=D("150"), unrealized_delta=D("-50"), period_pnl=D("100"), cost_sold=D("1000"), sales=1, exits=1, opened=date(2026, 4, 1), closed=date(2026, 9, 1), closed_by="SELL")
        group = group_contributions([a, b], date_from=date(2026, 1, 1), end=END)
        assert group.is_fully_sold is True
        assert group.closed_by == "SELL"
        assert group.annualized_return is not None  # base 1 000 (B's cost sold), 150 / 1 000 over 243 days

    def test_a_unit_that_left_another_way_falls_back_to_the_general_rule_as_a_row(self):
        # Two exits, one sale: no closed base (MF-A5) → the row's general rule, on the start value over the period:
        # −100 / 1 000 over 01/01 → 16/11 (319 days) = 0.9^(365/319) − 1
        a = contribution(1, held_at_end=False, end_value=D("0"), is_fully_sold=True, period_pnl=D("-100"), exits=2, sales=1, cost_sold=D("500"), opened=date(2025, 1, 1), closed=date(2026, 9, 1), closed_by="ADJUSTMENT")
        group = group_contributions([a], date_from=date(2026, 1, 1), end=END)
        assert group.annualized_return == pytest.approx(D("-0.1136"), abs=D("0.0005"))

    def test_closed_too_short_to_annualize_is_unknown(self):
        a = contribution(1, held_at_end=False, end_value=D("0"), is_fully_sold=True, realized=D("10"), period_pnl=D("10"), cost_sold=D("100"), sales=1, exits=1, opened=date(2026, 10, 1), closed=date(2026, 10, 10), closed_by="SELL")
        group = group_contributions([a], date_from=date(2026, 1, 1), end=END)
        assert group.annualized_return is None

    def test_open_group_annualized_on_start_value_from_the_oldest_lot(self):
        a = contribution(1, start_value=D("1000"), period_pnl=D("50"), oldest_open_lot=date(2024, 1, 1))
        b = contribution(2, start_value=D("1000"), period_pnl=D("50"), oldest_open_lot=date(2026, 2, 1))
        group = group_contributions([a, b], date_from=date(2025, 11, 16), end=END)
        # 100 / 2 000 = 5 % over the period's 365 days (the oldest lot is older than the period's start) → 5 %
        assert group.annualized_return == pytest.approx(D("0.05"), abs=D("0.0001"))

    def test_none_parts_of_an_activity_stay_none_when_nobody_has_them(self):
        group = group_contributions([contribution(1), contribution(2)], date_from=date(2026, 1, 1), end=END)
        assert group.realized is None and group.income is None and group.fees is None

    def test_an_unknown_pnl_makes_the_group_unknown(self):
        group = group_contributions([contribution(1), contribution(2, period_pnl=None, unrealized_delta=None)], date_from=date(2026, 1, 1), end=END)
        assert group.period_pnl is None
        assert group.period_pnl_percent is None


# ─────────────────────────────────────────────────────────────── Other effects (Q2: summed by kind)


class TestMergeByKind:
    def test_same_kind_summed_with_its_brokers_in_first_seen_order(self):
        rows = [("unalloc_costs", 1, D("-1.34")), ("fx_on_cash", 1, D("-36.31")), ("fx_on_cash", 5, D("-53.43")), ("residual", None, D("1406.91"))]
        merged = merge_by_kind(rows)
        assert merged == [("unalloc_costs", [1], D("-1.34")), ("fx_on_cash", [1, 5], D("-89.74")), ("residual", [], D("1406.91"))]
