"""Guards the in-kind income channel of ``financial_math/native_cash.py`` (project 79, STK-1).

A REWARD moves no cash but earns income: ``in_kind_income_movement`` turns it into a flow-only movement, which
``compute_native_cash`` converts in the same ``convert_bulk`` call as the cash, asking no unit rate for it. It counts in
``flows``, ``position_flow_steps``, ``sums_by_date`` and ``missing_conversions``, and never in ``balances``, ``value_at``,
``exchange_results``, ``foreign_cash_broker_ids`` or ``rate_change_days``. Pure: the FX service is replaced on the module
by the doubles of ``test_native_cash.py``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math import native_cash
from backend.app.services.financial_math.native_cash import (
    CashMovement,
    MissingCashConversion,
    NativeCash,
    cash_movement_from_transaction,
    compute_native_cash,
    in_kind_income_movement,
)
from backend.test_scripts.test_services.test_financial_math.test_native_cash import ForbiddenFx, install_fx

D = Decimal
D1 = date(2026, 3, 1)
D2 = date(2026, 3, 2)
D3 = date(2026, 3, 3)
D4 = date(2026, 3, 4)
D5 = date(2026, 3, 5)

A = 10  # broker with cash
B = 20  # broker with only a reward
X = 100  # asset


def _reward(*, tx_id=7, day=D2, broker_id=A, asset_id=X, quantity="20", cbo="0.50", cbo_ccy="EUR") -> SimpleNamespace:
    """A REWARD as stored: units in, amount 0 and no cash currency, the per-unit value in cost_basis_*."""
    return SimpleNamespace(
        id=tx_id,
        type=TransactionType.REWARD,
        date=day,
        broker_id=broker_id,
        asset_id=asset_id,
        quantity=D(quantity),
        amount=D("0"),
        currency=None,
        cost_basis_override=None if cbo is None else D(cbo),
        cost_basis_currency=cbo_ccy,
    )


def _cash(day, currency, amount, *, broker_id=A, tx_type="DEPOSIT", asset_id=None, movement_id=1, share="1") -> CashMovement:
    return CashMovement(movement_id=movement_id, transaction_type=tx_type, date=day, broker_id=broker_id, asset_id=asset_id, currency=currency, amount=D(amount), share=D(share))


def _only_in_kind(*movements: CashMovement, converted=None) -> NativeCash:
    """A NativeCash holding no cash at all, only income in kind (converted to its own amount by default)."""
    return NativeCash(
        report_currency="EUR",
        movements=(),
        converted=(),
        unit_rates={},
        in_kind=movements,
        in_kind_converted=tuple(movement.amount for movement in movements) if converted is None else converted,
    )


@pytest.fixture
def no_unit_rates(monkeypatch) -> ForbiddenFx:
    """``unit_rate_steps`` must not be asked: income in kind holds no balance."""
    probe = ForbiddenFx()
    monkeypatch.setattr(native_cash, "unit_rate_steps", probe)
    return probe


# =============================================================================
# 1. in_kind_income_movement
# =============================================================================


class TestInKindIncomeMovement:
    def test_reward_with_value(self):
        movement = in_kind_income_movement(_reward())
        assert movement == CashMovement(movement_id=7, transaction_type="REWARD", date=D2, broker_id=A, asset_id=X, currency="EUR", amount=D("10.00"), share=D("1"))

    def test_share_is_kept_on_the_movement(self):
        movement = in_kind_income_movement(_reward(), share=D("0.4"))
        assert movement is not None
        assert (movement.amount, movement.share, movement.native) == (D("10.00"), D("0.4"), D("4.000"))

    def test_foreign_cost_basis_currency(self):
        movement = in_kind_income_movement(_reward(cbo="1.25", cbo_ccy="USD", quantity="4"))
        assert movement is not None
        assert (movement.currency, movement.amount) == ("USD", D("5.00"))

    def test_reward_of_explicit_zero_value_is_a_zero_movement(self):
        """Q-A: an explicit 0 is a value: a movement of 0, which counts nothing and needs no rate."""
        movement = in_kind_income_movement(_reward(cbo="0", cbo_ccy="USD"))
        assert movement is not None
        assert (movement.amount, movement.currency) == (D("0"), "USD")
        cash = _only_in_kind(movement, converted=(D("0"),))
        assert cash.missing_conversions(None, D5) == []
        assert cash.sums_by_date(None, D5) == {}

    def test_reward_without_value_is_none(self):
        assert in_kind_income_movement(_reward(cbo=None)) is None

    @pytest.mark.parametrize("tx_type", [TransactionType.DIVIDEND, TransactionType.BUY, TransactionType.ADJUSTMENT])
    def test_other_types_are_none(self, tx_type):
        tx = _reward()
        tx.type = tx_type
        tx.currency = "EUR"
        assert in_kind_income_movement(tx) is None

    def test_reward_has_no_cash_movement(self):
        """A REWARD (amount 0, no currency) is never a cash movement."""
        assert cash_movement_from_transaction(_reward()) is None


# =============================================================================
# 2. NativeCash: counted in the flows, never in the cash
# =============================================================================


class TestNativeCashFlows:
    def test_flows_count_the_reward_as_income_of_its_position(self):
        cash = _only_in_kind(in_kind_income_movement(_reward()))
        flows = cash.flows(None, D5)
        assert flows.signed_by_type == {"REWARD": D("10.00")}
        assert flows.absolute_by_type == {"REWARD": D("10.00")}
        assert flows.income_by_position == {(A, X): D("10.00")}
        assert flows.unallocated_income == {}
        assert flows.costs_by_position == {}

    def test_flows_window_is_half_open(self):
        cash = _only_in_kind(in_kind_income_movement(_reward(day=D2)))
        assert cash.flows(D2, D5).signed_by_type == {}
        assert cash.flows(D1, D2).signed_by_type == {"REWARD": D("10.00")}

    def test_share_scales_the_flows(self):
        cash = _only_in_kind(in_kind_income_movement(_reward(), share=D("0.4")))
        flows = cash.flows(None, D5)
        assert flows.signed_by_type == {"REWARD": D("4.0000")}
        assert flows.income_by_position == {(A, X): D("4.0000")}
        assert cash.position_flow_steps(None, D5) == {(A, X): [(D2, D("4.0000"), D("0"))]}
        assert cash.sums_by_date(None, D5) == {D2: {"REWARD": D("4.0000")}}

    def test_position_flow_steps_merge_cash_and_in_kind_income(self):
        """A DIVIDEND of 3 on D1 and a REWARD of 10 on D2 on the same position: running income 3, then 13."""
        dividend = _cash(D1, "EUR", "3", tx_type="DIVIDEND", asset_id=X, movement_id=5)
        cash = NativeCash(report_currency="EUR", movements=(dividend,), converted=(D("3"),), unit_rates={}, in_kind=(in_kind_income_movement(_reward(day=D2)),), in_kind_converted=(D("10.00"),))
        assert cash.position_flow_steps(None, D5) == {(A, X): [(D1, D("3"), D("0")), (D2, D("13.00"), D("0"))]}
        assert cash.sums_by_date(None, D5, {"DIVIDEND", "REWARD"}) == {D1: {"DIVIDEND": D("3")}, D2: {"REWARD": D("10.00")}}
        assert cash.sums_by_date(None, D5, {"DIVIDEND"}) == {D1: {"DIVIDEND": D("3")}}

    def test_no_balance_and_no_value_for_a_broker_with_only_income_in_kind(self):
        cash = _only_in_kind(in_kind_income_movement(_reward(broker_id=B)))
        assert cash.balances() == {}
        assert cash.balances(D5) == {}
        assert cash.value_at(D5) == {}
        assert cash.foreign_cash_broker_ids == frozenset()
        assert cash.exchange_results(None, D5) == {}
        assert cash.rate_change_days(None, D5) == ()

    def test_foreign_reward_is_not_foreign_cash(self):
        """A USD REWARD converted at 0.9 counts 9 EUR of income, and still no foreign cash, balance or rate day."""
        movement = in_kind_income_movement(_reward(broker_id=B, cbo_ccy="USD"))
        cash = _only_in_kind(movement, converted=(D("9.00"),))
        assert cash.flows(None, D5).income_by_position == {(B, X): D("9.00")}
        assert cash.foreign_cash_broker_ids == frozenset()
        assert cash.balances() == {}
        assert cash.value_at(D5) == {}
        assert cash.rate_change_days(None, D5) == ()
        assert cash.missing_conversions(None, D5) == []

    def test_missing_conversion_is_reported_and_left_out_of_the_flows(self):
        movement = in_kind_income_movement(_reward(cbo_ccy="USD"))
        cash = _only_in_kind(movement, converted=(None,))
        assert cash.flows(None, D5).signed_by_type == {}
        assert cash.position_flow_steps(None, D5) == {}
        assert cash.sums_by_date(None, D5) == {}
        assert cash.missing_conversions(None, D5) == [MissingCashConversion(pair="USD/EUR", dates=(D2,))]
        assert cash.missing_conversions(None, D5, {"DIVIDEND"}) == []

    def test_lengths_must_match(self):
        with pytest.raises(ValueError, match="income in kind"):
            NativeCash(report_currency="EUR", movements=(), converted=(), unit_rates={}, in_kind=(in_kind_income_movement(_reward()),), in_kind_converted=())


# =============================================================================
# 3. compute_native_cash: one convert_bulk call, no unit rate for income in kind
# =============================================================================


class TestComputeNativeCash:
    @pytest.mark.asyncio
    async def test_report_currency_reward_asks_nothing(self, monkeypatch):
        probe = ForbiddenFx()
        monkeypatch.setattr(native_cash, "convert_bulk", probe)
        monkeypatch.setattr(native_cash, "unit_rate_steps", probe)
        reward = in_kind_income_movement(_reward())
        result = await compute_native_cash(None, [], report_currency="EUR", in_kind_income=[reward])
        assert probe.calls == []
        assert result.in_kind == (reward,)
        assert result.in_kind_converted == (D("10.00"),)
        assert result.flows(None, D5).signed_by_type == {"REWARD": D("10.00")}

    @pytest.mark.asyncio
    async def test_foreign_reward_with_a_rate(self, monkeypatch, no_unit_rates):
        fx = install_fx(monkeypatch, {("USD", "EUR"): {D1: "0.9"}})
        monkeypatch.setattr(native_cash, "unit_rate_steps", no_unit_rates)
        reward = in_kind_income_movement(_reward(broker_id=B, cbo_ccy="USD"))
        result = await compute_native_cash(None, [], report_currency="EUR", rates_until=D5, in_kind_income=[reward])
        assert len(fx.calls) == 1
        assert fx.requests == {("USD", D("10.00"), "EUR", D2)}
        assert no_unit_rates.calls == []
        assert result.in_kind_converted == (D("9.000"),)
        assert result.flows(None, D5).income_by_position == {(B, X): D("9.000")}
        assert result.missing_conversions(None, D5) == []
        assert result.balances() == {}
        assert result.value_at(D5) == {}
        assert result.foreign_cash_broker_ids == frozenset()
        assert result.rate_change_days(None, D5) == ()

    @pytest.mark.asyncio
    async def test_foreign_reward_without_a_rate(self, monkeypatch, no_unit_rates):
        install_fx(monkeypatch, {})
        monkeypatch.setattr(native_cash, "unit_rate_steps", no_unit_rates)
        reward = in_kind_income_movement(_reward(cbo_ccy="USD"))
        result = await compute_native_cash(None, [], report_currency="EUR", rates_until=D5, in_kind_income=[reward])
        assert result.in_kind_converted == (None,)
        assert result.flows(None, D5).signed_by_type == {}
        assert result.missing_conversions(None, D5) == [MissingCashConversion(pair="USD/EUR", dates=(D2,))]
        assert no_unit_rates.calls == []

    @pytest.mark.asyncio
    async def test_cash_and_in_kind_in_one_call_and_the_cash_unaffected(self, monkeypatch):
        """USD deposit 100 on D3 (rate 0.9, then 1.0 from D4) and a USD REWARD of 10 on D1 at the same broker.

        One ``convert_bulk`` call carries both; the unit-rate window starts at the deposit, not at the reward; and every
        cash reading equals the one of the same cash without the reward: exchange result 100 × 1.0 − 90 = 10 (with the
        reward booked as cash it would read 1).
        """
        rates = {("USD", "EUR"): {D1: "0.9", D4: "1.0"}}
        deposit = _cash(D3, "USD", "100")
        reward = in_kind_income_movement(_reward(day=D1, broker_id=A, cbo_ccy="USD"))

        fx = install_fx(monkeypatch, rates)
        with_reward = await compute_native_cash(None, [deposit], report_currency="EUR", rates_until=D5, in_kind_income=[reward])
        assert len(fx.calls) == 1
        assert [(amount.code, amount.amount, day) for amount, _to, day in fx.calls[0]] == [("USD", D("100"), D3), ("USD", D("10.00"), D1)]
        assert fx.steps.calls == [{("USD", "EUR"): [(D3, D5)]}]

        install_fx(monkeypatch, rates)
        without = await compute_native_cash(None, [deposit], report_currency="EUR", rates_until=D5)

        assert with_reward.converted == without.converted == (D("90.0"),)
        assert with_reward.in_kind_converted == (D("9.000"),)
        assert with_reward.balances() == without.balances() == {A: {"USD": D("100")}}
        for day in (D1, D2, D3, D4, D5):
            assert with_reward.value_at(day) == without.value_at(day), day
        assert with_reward.exchange_results(None, D5) == without.exchange_results(None, D5) == {A: D("10.0")}
        assert with_reward.foreign_cash_broker_ids == without.foreign_cash_broker_ids == frozenset({A})
        assert with_reward.rate_change_days(None, D5) == without.rate_change_days(None, D5)

        assert with_reward.flows(None, D5).signed_by_type == {"DEPOSIT": D("90.0"), "REWARD": D("9.000")}
        assert with_reward.flows(None, D5).income_by_position == {(A, X): D("9.000")}
        assert without.flows(None, D5).income_by_position == {}
