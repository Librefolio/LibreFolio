"""
Red tests for MF5-5 «one home for the unit price of a trade».

The same formula, the unit price on the market quote axis behind a trade, was written twice:

* ``price_marks.build_asset_price_series``: a BUY/SELL observation's price is ``|amount| / |quantity| × scale``
  (scale = ``quote_base_quantity`` when > 0, else 1), in the caller's decimal context;
* ``trade_amount.unit_price_from_amount`` (#47): ``amount × base / quantity`` at 80 digits, rounded half-even.

Contract under test (module ``backend/app/services/financial_math/trade_amount.py``):

* ``unit_price_on_quote_axis(quantity, amount, quote_base_quantity)`` =
  ``amount / quantity × Decimal(normalize_quote_base_quantity(quote_base_quantity))``, division first, in the
  CALLER's context, unrounded; signs follow the inputs; a zero quantity raises;
* ``price_marks`` imports it and takes every TRADE observation's ``unit_price`` from
  ``unit_price_on_quote_axis(abs(quantity), abs(amount), quote_base_quantity)``, bit for bit what it computes today;
* ``unit_price_from_amount`` rounds ``unit_price_on_quote_axis(...)`` inside its 80-digit half-even context.

The helper is reached as a module attribute, never imported at module level: on HEAD it does not exist, and the
parity tests (a green guard on today's ``price_marks`` numbers) must still be collected and pass.

Why the order matters: with a decimal base (1, 100, 1000) multiplying first or dividing first gives the same 28 digits,
the base only shifts the exponent. With another base it does not: ``1 × 3 / 3`` is ``1`` while ``1 / 3 × 3`` is
``0.9999999999999999999999999999`` at 28 digits. ``price_marks`` divides first today, so the one home divides first.
"""

from __future__ import annotations

import inspect
from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP, Decimal, InvalidOperation, getcontext, localcontext
from types import SimpleNamespace

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math import price_marks, trade_amount
from backend.app.services.financial_math.price_marks import ObservationKind
from backend.app.services.financial_math.valuation import normalize_quote_base_quantity

D = Decimal
_HELPER = "unit_price_on_quote_axis"


def _helper():
    """The one home, read off its module; a clear failure while it does not exist."""
    helper = getattr(trade_amount, _HELPER, None)
    if helper is None:
        pytest.fail(f"trade_amount.{_HELPER} does not exist: the unit price of a trade has no single home yet")
    return helper


def _expected(quantity: Decimal, amount: Decimal, base: int | None) -> Decimal:
    """The contract's formula, computed here in the ambient context: division first, then × base."""
    return amount / quantity * Decimal(normalize_quote_base_quantity(base))


def _same(actual: Decimal, expected: Decimal) -> None:
    """Bit for bit: same value AND same representation (sign, digits, exponent)."""
    assert isinstance(actual, Decimal)
    assert actual.as_tuple() == expected.as_tuple(), f"{actual!r} != {expected!r}"


# --------------------------------------------------------------------------------------------------------------------
# The pure function
# --------------------------------------------------------------------------------------------------------------------


class TestUnitPriceOnQuoteAxis:
    @pytest.mark.parametrize(
        ("quantity", "amount", "base", "value"),
        [
            ("12", "1000.8", 1, "83.4"),
            ("12", "1000.8", None, "83.4"),
            ("12", "1000.8", 0, "83.4"),
            ("12", "1000.8", -1, "83.4"),
            ("10000", "9850", 100, "98.5"),  # a bond quoted on base 100
            ("8", "1", 1000, "125"),
            ("0.5", "1.5", 1, "3"),  # fractional quantity
            ("2.5", "1", 100, "40"),
        ],
    )
    def test_values_on_every_base(self, quantity, amount, base, value):
        result = _helper()(D(quantity), D(amount), base)
        assert result == D(value)
        _same(result, _expected(D(quantity), D(amount), base))

    @pytest.mark.parametrize(
        ("quantity", "amount", "base", "value"),
        [
            ("-3", "300", 100, "-10000"),  # a SELL as stored: negative quantity, positive amount
            ("3", "-300", None, "-100"),  # a BUY as stored: positive quantity, negative amount
            ("-2", "-5", 1, "2.5"),
        ],
    )
    def test_signs_follow_the_inputs(self, quantity, amount, base, value):
        result = _helper()(D(quantity), D(amount), base)
        assert result == D(value)
        _same(result, _expected(D(quantity), D(amount), base))

    @pytest.mark.parametrize(
        ("quantity", "amount", "base"),
        [("3", "1", 1), ("7", "1000.01", 100), ("0.7", "1234.567891", 1000), ("12.34567", "98.5", 3), ("1.3", "2", 25)],
    )
    def test_non_terminating_quotient_in_the_default_context(self, quantity, amount, base):
        assert getcontext().prec == 28
        _same(_helper()(D(quantity), D(amount), base), _expected(D(quantity), D(amount), base))

    @pytest.mark.parametrize(
        ("quantity", "amount", "base"),
        [("3", "1", 1), ("7", "1000.01", 100), ("3", "1", 3), ("1.3", "2", 25)],
    )
    def test_non_terminating_quotient_in_an_80_digit_context(self, quantity, amount, base):
        with localcontext() as context:
            context.prec = 80
            context.rounding = ROUND_HALF_EVEN
            result = _helper()(D(quantity), D(amount), base)
            _same(result, _expected(D(quantity), D(amount), base))
        assert len(result.as_tuple().digits) == 80, "unrounded: the caller's 80 digits, not a fixed scale"

    def test_it_is_not_rounded_to_a_scale(self):
        """1 / 3 at 28 digits keeps all 28: no quantize to the 12 decimals of a price column."""
        result = _helper()(D("3"), D("1"), 1)
        assert result == D("0.3333333333333333333333333333")

    @pytest.mark.parametrize(("rounding", "value"), [(ROUND_UP, "0.66667"), (ROUND_DOWN, "0.66666")])
    def test_it_runs_in_the_callers_context(self, rounding, value):
        """Precision AND rounding mode are the caller's: the helper opens no context of its own."""
        with localcontext() as context:
            context.prec = 5
            context.rounding = rounding
            _same(_helper()(D("3"), D("2"), 1), D(value))

    @pytest.mark.parametrize(("quantity", "amount"), [("0", "5"), ("0", "0"), ("0.000", "-12")])
    def test_a_zero_quantity_raises(self, quantity, amount):
        with pytest.raises((ZeroDivisionError, InvalidOperation)):
            _helper()(D(quantity), D(amount), 100)


class TestOrderMattersAt28Digits:
    """Division first, then × base: with a non-decimal base the two orders part in the last digit."""

    @pytest.mark.parametrize(
        ("quantity", "amount", "base", "divide_first", "multiply_first"),
        [
            ("3", "1", 3, "0.9999999999999999999999999999", "1"),
            ("7", "1", 3, "0.4285714285714285714285714287", "0.4285714285714285714285714286"),
            ("1.3", "2", 3, "4.615384615384615384615384614", "4.615384615384615384615384615"),
            ("3.7", "1000.01", 3, "810.8189189189189189189189190", "810.8189189189189189189189189"),
        ],
    )
    def test_the_helper_divides_first(self, quantity, amount, base, divide_first, multiply_first):
        q, a, b = D(quantity), D(amount), D(base)
        assert getcontext().prec == 28
        # The numbers really are order-sensitive (a guard on the test's own premise).
        assert a / q * b == D(divide_first)
        assert a * b / q == D(multiply_first)
        assert D(divide_first) != D(multiply_first)
        _same(_helper()(q, a, base), D(divide_first))


# --------------------------------------------------------------------------------------------------------------------
# price_marks: the TRADE observations (parity is a green guard, the call is the single home)
# --------------------------------------------------------------------------------------------------------------------

_DAY = date(2026, 3, 2)


def _tx(tx_id: int, tx_type: TransactionType, quantity: str | None, amount: str | None, *, day: date = _DAY, currency: str = "EUR") -> SimpleNamespace:
    """The fields ``build_asset_price_series`` reads off a Transaction row, nothing else."""
    return SimpleNamespace(id=tx_id, type=tx_type, date=day, quantity=None if quantity is None else D(quantity), amount=None if amount is None else D(amount), currency=currency)


#: (id, type, quantity, amount): one row per shape the contract names.
_TRADES = [
    (1, TransactionType.BUY, "10", "-1200"),
    (2, TransactionType.BUY, "0.37", "-45.678"),  # fractional quantity
    (3, TransactionType.BUY, "3", "-100"),  # non-terminating quotient
    (4, TransactionType.SELL, "-7", "1000.01"),  # SELL: negative quantity, positive amount
    (5, TransactionType.BUY, "1.3", "-2"),  # BUY: negative amount; order-sensitive on base 3
    (6, TransactionType.SELL, "-3.7", "1000.01"),
]


def _trade_observations(monkeypatch, transactions, quote_base_quantity, *, split_linked: set[int] | None = None):
    """Every TRADE observation ``build_asset_price_series`` hands to the series, before same-day averaging."""
    captured: list = []
    real_series = price_marks.AssetPriceSeries

    def capturing_series(observations):
        captured.extend(observations)
        return real_series(observations)

    monkeypatch.setattr(price_marks, "AssetPriceSeries", capturing_series)
    price_marks.build_asset_price_series(
        price_rows=[],
        transactions=transactions,
        split_linked_tx_ids=split_linked or set(),
        asset_currency="EUR",
        quote_base_quantity=quote_base_quantity,
    )
    return [obs for obs in captured if obs.kind is ObservationKind.TRADE]


class TestPriceMarksParity:
    """Green on HEAD and after: the TRADE price stays ``|amount| / |quantity| × scale``, bit for bit."""

    @pytest.mark.parametrize("quote_base_quantity", [1, 3, 25, 100, 1000, None, 0, -5])
    def test_every_trade_observation_is_abs_amount_over_abs_quantity_times_scale(self, monkeypatch, quote_base_quantity):
        rows = [_tx(tx_id, tx_type, qty, amt, day=date(2026, 3, tx_id)) for tx_id, tx_type, qty, amt in _TRADES]
        observations = _trade_observations(monkeypatch, rows, quote_base_quantity)
        assert len(observations) == len(rows)
        scale = D(quote_base_quantity if quote_base_quantity and quote_base_quantity > 0 else 1)
        by_day = {obs.date: obs for obs in observations}
        for row in rows:
            expected = abs(row.amount) / abs(row.quantity) * scale
            _same(by_day[row.date].unit_price, expected)

    def test_the_order_sensitive_row_divides_first(self, monkeypatch):
        """2 paid for 1.3 units quoted on base 3: today's price_marks gives the divide-first digits."""
        (obs,) = _trade_observations(monkeypatch, [_tx(5, TransactionType.BUY, "1.3", "-2")], 3)
        _same(obs.unit_price, D("4.615384615384615384615384614"))


def _spy_on(monkeypatch, module):
    """Replace ``module.unit_price_on_quote_axis`` with a spy around the real helper; on HEAD there is nothing to replace."""
    real = getattr(trade_amount, _HELPER)  # AttributeError on HEAD: the single home does not exist
    signature = inspect.signature(real)
    calls: list[dict] = []

    def spy(*args, **kwargs):
        bound = signature.bind(*args, **kwargs).arguments  # positional or keyword, the same three values
        context = getcontext()
        result = real(*args, **kwargs)
        calls.append({"args": tuple(bound.values())[:3], "prec": context.prec, "rounding": context.rounding, "result": result})
        return result

    monkeypatch.setattr(module, _HELPER, spy, raising=True)
    return calls


def _call_args(call: dict) -> tuple:
    """``(quantity, amount, quote_base_quantity)`` as the spy received them."""
    return call["args"]


class TestPriceMarksUsesTheSingleHome:
    def test_price_marks_imports_the_helper(self):
        assert getattr(price_marks, _HELPER, None) is getattr(trade_amount, _HELPER, object()), "price_marks must import trade_amount.unit_price_on_quote_axis"

    @pytest.mark.parametrize("quote_base_quantity", [100, 3, 1])
    def test_each_trade_price_comes_from_the_helper(self, monkeypatch, quote_base_quantity):
        calls = _spy_on(monkeypatch, price_marks)
        rows = [
            _tx(1, TransactionType.BUY, "0.37", "-45.678", day=date(2026, 3, 2)),
            _tx(2, TransactionType.SELL, "-7", "1000.01", day=date(2026, 3, 3)),
            _tx(3, TransactionType.ADJUSTMENT, "5", "-10", day=date(2026, 3, 4)),  # never a price
            _tx(4, TransactionType.BUY, "2", "-20", day=date(2026, 3, 5)),  # split-linked: skipped
        ]
        observations = _trade_observations(monkeypatch, rows, quote_base_quantity, split_linked={4})

        assert [_call_args(call) for call in calls] == [
            (D("0.37"), D("45.678"), quote_base_quantity),
            (D("7"), D("1000.01"), quote_base_quantity),
        ]
        # What the helper returned is what the observation carries, untouched.
        assert [obs.unit_price for obs in sorted(observations, key=lambda obs: obs.date)] == [call["result"] for call in calls]


class TestUnitPriceFromAmountUsesTheSingleHome:
    @pytest.mark.parametrize(("quantity", "amount", "base", "scale"), [("3", "100", 100, 12), ("0.37", "45.678", None, 12), ("-7", "1000.01", 3, 6)])
    def test_it_rounds_the_helpers_result_in_its_80_digit_context(self, monkeypatch, quantity, amount, base, scale):
        calls = _spy_on(monkeypatch, trade_amount)
        result = trade_amount.unit_price_from_amount(D(quantity), D(amount), base, scale=scale)

        assert len(calls) == 1
        (call,) = calls
        got_quantity, got_amount, got_base = _call_args(call)
        assert (got_quantity, got_amount) == (D(quantity), D(amount))
        assert normalize_quote_base_quantity(got_base) == normalize_quote_base_quantity(base)
        assert (call["prec"], call["rounding"]) == (80, ROUND_HALF_EVEN), "the helper runs inside the 80-digit half-even context"
        _same(result, call["result"].quantize(D(1).scaleb(-scale), rounding=ROUND_HALF_EVEN))
