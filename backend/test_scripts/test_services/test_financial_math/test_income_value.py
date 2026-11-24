"""Guards ``financial_math/income.py`` (project 79, STK-1): the income of a transaction, cash or in kind.

DIVIDEND and INTEREST earn their signed cash amount in their currency; a REWARD earns ``cost_basis_override × quantity``
in ``cost_basis_currency`` (its value on receipt, no cash), and a REWARD without a value has unknown income (None, never
zero). Pure: transactions are plain namespaces with the attributes the module reads.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.income import (
    CASH_INCOME_TYPES,
    IN_KIND_INCOME_TYPES,
    INCOME_TYPES,
    IncomeValue,
    income_value,
    is_in_kind_income,
    is_income,
)

D = Decimal


def _tx(tx_type, *, amount="0", currency=None, quantity="0", cbo=None, cbo_ccy=None) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        type=tx_type,
        date=date(2026, 3, 1),
        amount=None if amount is None else D(amount),
        currency=currency,
        quantity=None if quantity is None else D(quantity),
        cost_basis_override=None if cbo is None else D(cbo),
        cost_basis_currency=cbo_ccy,
    )


class TestTypeSets:
    def test_income_types(self):
        assert CASH_INCOME_TYPES == {"DIVIDEND", "INTEREST"}
        assert IN_KIND_INCOME_TYPES == {"REWARD"}
        assert INCOME_TYPES == {"DIVIDEND", "INTEREST", "REWARD"}

    @pytest.mark.parametrize("tx_type", [TransactionType.REWARD, "REWARD"])
    def test_reward_is_in_kind_income_as_enum_or_string(self, tx_type):
        tx = _tx(tx_type, quantity="20")
        assert is_income(tx) and is_in_kind_income(tx)

    @pytest.mark.parametrize("tx_type", [TransactionType.DIVIDEND, TransactionType.INTEREST])
    def test_cash_income_is_not_in_kind(self, tx_type):
        tx = _tx(tx_type, amount="10", currency="EUR")
        assert is_income(tx) and not is_in_kind_income(tx)

    @pytest.mark.parametrize("tx_type", [TransactionType.BUY, TransactionType.ADJUSTMENT, TransactionType.FEE])
    def test_other_types_earn_nothing(self, tx_type):
        tx = _tx(tx_type, quantity="20", cbo="0.5", cbo_ccy="EUR")
        assert not is_income(tx) and not is_in_kind_income(tx)


class TestCashIncome:
    def test_dividend_reads_amount_and_currency(self):
        assert income_value(_tx(TransactionType.DIVIDEND, amount="12.34", currency="USD")) == IncomeValue(amount=D("12.34"), currency="USD")

    def test_interest_reads_amount_and_currency(self):
        assert income_value(_tx(TransactionType.INTEREST, amount="3.10", currency="EUR")) == IncomeValue(amount=D("3.10"), currency="EUR")

    def test_negative_legacy_correction_stays_signed(self):
        value = income_value(_tx(TransactionType.INTEREST, amount="-4", currency="EUR"))
        assert value == IncomeValue(amount=D("-4"), currency="EUR")

    def test_default_currency_when_row_has_none(self):
        assert income_value(_tx(TransactionType.DIVIDEND, amount="5", currency=None), default_currency="CHF") == IncomeValue(amount=D("5"), currency="CHF")

    def test_row_currency_wins_over_default(self):
        assert income_value(_tx(TransactionType.DIVIDEND, amount="5", currency="USD"), default_currency="CHF") == IncomeValue(amount=D("5"), currency="USD")

    def test_no_currency_and_no_default_is_unknown(self):
        assert income_value(_tx(TransactionType.DIVIDEND, amount="5", currency=None)) is None

    def test_no_amount_is_unknown(self):
        assert income_value(_tx(TransactionType.DIVIDEND, amount=None, currency="EUR")) is None

    def test_cash_income_ignores_a_cost_basis(self):
        value = income_value(_tx(TransactionType.DIVIDEND, amount="7", currency="EUR", quantity="20", cbo="0.5", cbo_ccy="USD"))
        assert value == IncomeValue(amount=D("7"), currency="EUR")


class TestRewardIncome:
    def test_value_is_override_times_quantity_in_cost_basis_currency(self):
        """20 units at 0.50 EUR each: income 10.00 EUR, whatever the (absent) cash fields say."""
        value = income_value(_tx(TransactionType.REWARD, amount="0", currency=None, quantity="20", cbo="0.50", cbo_ccy="EUR"))
        assert value == IncomeValue(amount=D("10.00"), currency="EUR")

    def test_foreign_cost_basis_currency(self):
        value = income_value(_tx(TransactionType.REWARD, quantity="3", cbo="1.25", cbo_ccy="USD"), default_currency="EUR")
        assert value == IncomeValue(amount=D("3.75"), currency="USD")

    def test_default_currency_when_no_cost_basis_currency(self):
        value = income_value(_tx(TransactionType.REWARD, quantity="20", cbo="0.50", cbo_ccy=None), default_currency="EUR")
        assert value == IncomeValue(amount=D("10.00"), currency="EUR")

    def test_reward_never_reads_its_cash_currency(self):
        """The row's cash ``currency`` is not the reward's: without cost_basis_currency the default is used."""
        value = income_value(_tx(TransactionType.REWARD, currency="USD", quantity="20", cbo="0.50", cbo_ccy=None), default_currency="EUR")
        assert value == IncomeValue(amount=D("10.00"), currency="EUR")

    def test_explicit_zero_is_a_value_not_unknown(self):
        """Q-A: cost_basis_override = 0 is a reward worth nothing, a known income of 0."""
        value = income_value(_tx(TransactionType.REWARD, quantity="20", cbo="0", cbo_ccy="EUR"))
        assert value == IncomeValue(amount=D("0"), currency="EUR")

    def test_without_override_is_unknown_not_zero(self):
        assert income_value(_tx(TransactionType.REWARD, quantity="20", cbo=None, cbo_ccy="EUR"), default_currency="EUR") is None

    def test_without_quantity_is_unknown(self):
        assert income_value(_tx(TransactionType.REWARD, quantity=None, cbo="0.5", cbo_ccy="EUR")) is None

    def test_without_any_currency_is_unknown(self):
        assert income_value(_tx(TransactionType.REWARD, quantity="20", cbo="0.5", cbo_ccy=None)) is None


class TestOtherTypes:
    @pytest.mark.parametrize(
        "tx_type",
        [TransactionType.BUY, TransactionType.SELL, TransactionType.ADJUSTMENT, TransactionType.FEE, TransactionType.TAX, TransactionType.DEPOSIT, TransactionType.WITHDRAWAL, TransactionType.TRANSFER],
    )
    def test_none(self, tx_type):
        tx = _tx(tx_type, amount="-100", currency="EUR", quantity="20", cbo="0.5", cbo_ccy="EUR")
        assert income_value(tx, default_currency="EUR") is None
