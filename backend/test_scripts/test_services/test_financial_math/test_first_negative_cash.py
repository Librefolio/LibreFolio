"""
Unit tests for ``first_negative_cash``: the first day a broker's cash ends below zero.

Module under test: ``backend/app/services/financial_math/native_cash.py`` — ``first_negative_cash`` and the
value object it returns, ``NegativeCash``.

What the function owes its caller, in one line: given one broker's cash movements (any order), the balances
before them and the extra days to check, it returns the first visited day on which a currency's balance ENDS
below zero — with that balance and the day's negative movements of that currency — or None.

The caller it is written for is the balance validator,
``backend/app/services/transactions/balances.py::_validate_broker_balances``: the opening is its
``_get_balances_before_date``, the check day its ``from_date``, the order of currencies on a red day its dict
iteration. Where the validator's current behaviour and this contract differ, the test follows the contract and
says so in its docstring.

R13-SEC7-3: only the days with a movement and the check days are visited, never every calendar day. A
movement of the year 1 and one of 9999-12-31 must cost a handful of steps; it is measured as the number of
traced lines executed inside ``native_cash.py`` (deterministic, not a clock).

Pure: no database, no server, no network, nothing to convert. The new names are read as attributes of the
module inside each test (``native_cash.first_negative_cash``), never imported at module level: until the
function exists each test fails on its own with an AttributeError, while every other file of this directory
still collects and runs.
"""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.services.financial_math import native_cash
from backend.app.services.financial_math.native_cash import CashMovement, cash_movement_from_transaction

BROKER = 7

_next_id = iter(range(1, 1_000_000))


def mv(day: date, amount: str, currency: str = "EUR", *, share: str = "1", broker_id: int = BROKER, tx_type: str = "WITHDRAWAL") -> CashMovement:
    """One cash movement of the test broker; every call a distinct id, so identity and order are observable."""
    return CashMovement(
        movement_id=next(_next_id),
        transaction_type=tx_type,
        date=day,
        broker_id=broker_id,
        asset_id=None,
        currency=currency,
        amount=Decimal(amount),
        share=Decimal(share),
    )


def d(day: int, month: int = 3, year: int = 2026) -> date:
    return date(year, month, day)


def first_negative(movements, **kwargs):
    return native_cash.first_negative_cash(movements, **kwargs)


def assert_same_movements(actual, expected) -> None:
    """The reducers are the caller's own objects, in order — not equal copies."""
    assert isinstance(actual, tuple)
    assert len(actual) == len(expected), f"{actual!r} != {expected!r}"
    for got, want in zip(actual, expected, strict=True):
        assert got is want, f"{got!r} is not {want!r}"


# ---------------------------------------------------------------------------
# 1. The spec example and the shape of the answer
# ---------------------------------------------------------------------------


def test_spec_example_reports_end_of_day_balance_and_every_reducer_of_the_day():
    """Opening {EUR: 100}; 05/03 −60, 05/03 −50, 06/03 +30 → 05/03, EUR, −10, (the −60, the −50)."""
    m60 = mv(d(5), "-60")
    m50 = mv(d(5), "-50")
    p30 = mv(d(6), "30")

    result = first_negative([m60, m50, p30], opening={"EUR": Decimal("100")})

    assert isinstance(result, native_cash.NegativeCash)
    assert result.day == d(5)
    assert result.currency == "EUR"
    assert result.balance == Decimal("-10")
    assert_same_movements(result.reducers, (m60, m50))


def test_negative_cash_is_frozen():
    m = mv(d(1), "-1")
    result = first_negative([m])
    assert result is not None
    with pytest.raises(FrozenInstanceError):
        result.balance = Decimal("0")  # type: ignore[misc]


def test_none_when_no_balance_ends_below_zero():
    movements = [mv(d(1), "100"), mv(d(2), "-40"), mv(d(3), "-60"), mv(d(4), "5", "USD")]
    assert first_negative(movements) is None


def test_exactly_zero_is_not_negative():
    assert first_negative([mv(d(1), "-50")], opening={"EUR": Decimal("50")}) is None
    assert first_negative([mv(d(1), "50"), mv(d(2), "-50")]) is None


def test_empty_movements_and_no_opening_is_none():
    assert first_negative([]) is None


# ---------------------------------------------------------------------------
# 2. One broker only
# ---------------------------------------------------------------------------


def test_movements_of_two_brokers_raise_value_error_even_when_every_amount_is_positive():
    movements = [mv(d(1), "10", broker_id=1), mv(d(2), "10", broker_id=2)]
    with pytest.raises(ValueError):
        first_negative(movements)


def test_movements_of_two_brokers_raise_value_error_before_any_red_is_reported():
    """A red on the first broker's day must not hide that the input mixes two brokers."""
    movements = [mv(d(1), "-10", broker_id=1), mv(d(9), "10", broker_id=2)]
    with pytest.raises(ValueError):
        first_negative(movements)


# ---------------------------------------------------------------------------
# 3. Order: sorted by date, same day stable, end of day only
# ---------------------------------------------------------------------------


def test_unsorted_input_is_walked_by_date_and_same_day_movements_keep_their_input_order():
    """Given newest first: the 01/03 red is found, not the 10/03 one; its reducers keep the order they came in."""
    late = mv(d(10), "-500")
    b = mv(d(1), "-20")
    a = mv(d(1), "-30")
    deposit = mv(d(1), "40")

    result = first_negative([late, b, deposit, a])

    assert result is not None
    assert result.day == d(1)
    assert result.balance == Decimal("-10")
    assert_same_movements(result.reducers, (b, a))


def test_balance_is_checked_at_end_of_day_no_intermediate_red():
    """From 40: −60 then +30 on the same day dips to −20 in between, ends at 10 → no red."""
    movements = [mv(d(3), "-60"), mv(d(3), "30")]
    assert first_negative(movements, opening={"EUR": Decimal("40")}) is None


def test_first_negative_day_wins_over_a_later_deeper_one_and_a_later_recovery_does_not_matter():
    first = mv(d(2), "-15")
    movements = [mv(d(1), "10"), first, mv(d(3), "-100"), mv(d(4), "1000")]

    result = first_negative(movements)

    assert result is not None
    assert (result.day, result.balance) == (d(2), Decimal("-5"))
    assert_same_movements(result.reducers, (first,))


# ---------------------------------------------------------------------------
# 4. Amounts: share, zero, reducers of one currency only
# ---------------------------------------------------------------------------


def test_share_scales_the_amount_minus_60_at_half_counts_minus_30():
    half = mv(d(1), "-60", share="0.5")

    result = first_negative([half], opening={"EUR": Decimal("20")})
    assert result is not None
    assert result.balance == Decimal("-10")
    assert_same_movements(result.reducers, (half,))

    assert first_negative([half], opening={"EUR": Decimal("40")}) is None


def test_zero_amount_changes_nothing_and_is_never_a_reducer():
    zero = mv(d(1), "0")
    red = mv(d(1), "-1")

    assert first_negative([zero]) is None
    assert first_negative([zero], opening={"EUR": Decimal("0")}) is None

    result = first_negative([zero, red])
    assert result is not None
    assert result.balance == Decimal("-1")
    assert_same_movements(result.reducers, (red,))


def test_reducers_are_only_the_negative_movements_of_that_currency_on_that_day():
    earlier_eur = mv(d(1), "-1")
    usd_out = mv(d(2), "-3", "USD")
    eur_in = mv(d(2), "1")
    eur_out = mv(d(2), "-10")
    eur_zero = mv(d(2), "0")

    result = first_negative([earlier_eur, usd_out, eur_in, eur_out, eur_zero], opening={"EUR": Decimal("5"), "USD": Decimal("100")})

    assert result is not None
    assert (result.day, result.currency, result.balance) == (d(2), "EUR", Decimal("-5"))
    assert_same_movements(result.reducers, (eur_out,))


def test_currencies_are_independent_balances():
    """A USD deposit does not cover a EUR withdrawal."""
    eur_out = mv(d(1), "-10")
    result = first_negative([mv(d(1), "1000", "USD"), eur_out])

    assert result is not None
    assert (result.currency, result.balance) == ("EUR", Decimal("-10"))


# ---------------------------------------------------------------------------
# 5. Several negative currencies on one day: insertion order
# ---------------------------------------------------------------------------


def test_several_red_currencies_on_one_day_opening_order_wins():
    """Opening {USD, EUR}; on the red day EUR moves first → USD reported, as the validator's dict iteration."""
    movements = [mv(d(1), "-20", "EUR"), mv(d(1), "-20", "USD")]

    result = first_negative(movements, opening={"USD": Decimal("10"), "EUR": Decimal("10")})

    assert result is not None
    assert (result.currency, result.balance) == ("USD", Decimal("-10"))


def test_several_red_currencies_on_one_day_first_appearance_in_the_walk_wins_not_the_order_on_the_red_day():
    """USD appears on 01/03, EUR on 02/03; on 03/03 EUR goes red first in the day → USD still reported."""
    movements = [
        mv(d(1), "5", "USD"),
        mv(d(2), "5", "EUR"),
        mv(d(3), "-10", "EUR"),
        mv(d(3), "-10", "USD"),
    ]

    result = first_negative(movements)

    assert result is not None
    assert (result.day, result.currency, result.balance) == (d(3), "USD", Decimal("-5"))


def test_several_red_currencies_unsorted_input_first_appearance_is_by_walk_not_by_input_position():
    """The input lists the 02/03 EUR row before the 01/03 USD row: the walk meets USD first."""
    movements = [
        mv(d(2), "5", "EUR"),
        mv(d(3), "-10", "EUR"),
        mv(d(3), "-10", "USD"),
        mv(d(1), "5", "USD"),
    ]

    result = first_negative(movements)

    assert result is not None
    assert result.currency == "USD"


def test_zero_amount_does_not_establish_a_currencys_place_in_the_order():
    """Validator parity: ``if tx.amount != 0`` keeps a zero row out of the balances dict, so it gives its currency no
    earlier place. USD's only earlier row is 0; on 03/03 EUR moves first → EUR reported."""
    movements = [
        mv(d(1), "0", "USD"),
        mv(d(3), "-10", "EUR"),
        mv(d(3), "-10", "USD"),
    ]

    result = first_negative(movements)

    assert result is not None
    assert result.currency == "EUR"


# ---------------------------------------------------------------------------
# 6. Opening balances and check days
# ---------------------------------------------------------------------------


def test_negative_opening_currency_without_movements_is_reported_on_the_first_visited_day_with_no_reducers():
    movements = [mv(d(3), "10", "USD"), mv(d(5), "10", "USD")]

    result = first_negative(movements, opening={"EUR": Decimal("-5")})

    assert result is not None
    assert (result.day, result.currency, result.balance) == (d(3), "EUR", Decimal("-5"))
    assert result.reducers == ()


def test_negative_opening_on_a_check_day_earlier_than_every_movement():
    """The validator's from_date: the balances before it may already be negative → reported on from_date."""
    movements = [mv(d(10), "100", "USD")]

    result = first_negative(movements, opening={"EUR": Decimal("-5")}, check_days=(d(1),))

    assert result is not None
    assert (result.day, result.currency, result.balance) == (d(1), "EUR", Decimal("-5"))
    assert result.reducers == ()


def test_negative_opening_cured_on_the_first_visited_day_is_not_a_red():
    """End of day: the opening is −5 but a +10 lands on the check day itself → ends at +5."""
    movements = [mv(d(1), "10")]
    assert first_negative(movements, opening={"EUR": Decimal("-5")}, check_days=(d(1),)) is None


def test_check_day_between_movements_adds_no_false_red():
    movements = [mv(d(1), "10"), mv(d(5), "-10")]
    assert first_negative(movements, check_days=(d(3), d(4))) is None


def test_check_day_equal_to_a_movement_day_is_visited_once_with_that_days_reducers():
    red = mv(d(2), "-3")
    result = first_negative([mv(d(1), "1"), red], check_days=(d(2), d(2)))

    assert result is not None
    assert result.day == d(2)
    assert_same_movements(result.reducers, (red,))


def test_negative_opening_with_nothing_to_visit_is_none():
    """No movement, no check day: no day is visited, so nothing is reported."""
    assert first_negative([], opening={"EUR": Decimal("-5")}) is None


def test_negative_opening_with_only_a_check_day_is_reported():
    """Contract over validator: ``_validate_broker_balances`` returns early (``if not txs: return``) when no row is on
    or after from_date, so today it never checks a negative opening; the function visits the check day anyway."""
    result = first_negative([], opening={"EUR": Decimal("-5")}, check_days=(d(4),))

    assert result is not None
    assert (result.day, result.currency, result.balance) == (d(4), "EUR", Decimal("-5"))
    assert result.reducers == ()


def test_opening_mapping_is_not_mutated():
    opening = {"EUR": Decimal("100")}
    first_negative([mv(d(1), "-60"), mv(d(1), "-50"), mv(d(2), "5", "USD")], opening=opening)
    assert opening == {"EUR": Decimal("100")}


def test_movements_and_check_days_may_be_single_pass_iterables():
    m60 = mv(d(5), "-60")
    m50 = mv(d(5), "-50")

    result = first_negative(
        (m for m in [mv(d(6), "30"), m60, m50]),
        opening={"EUR": Decimal("100")},
        check_days=(day for day in [d(1)]),
    )

    assert result is not None
    assert (result.day, result.balance) == (d(5), Decimal("-10"))
    assert_same_movements(result.reducers, (m60, m50))


# ---------------------------------------------------------------------------
# 7. R13-SEC7-3: only the visited days, never the calendar
# ---------------------------------------------------------------------------

_LINE_BUDGET = 5_000


def _lines_executed_in_native_cash(call) -> tuple[object, int]:
    """Run ``call`` and count the traced lines executed inside native_cash.py — a day-by-day walk from the year 1 to
    9999-12-31 runs millions; a walk over the visited days a few dozen. The previous tracer (coverage) is restored."""
    target = native_cash.__file__
    count = 0

    def local(frame, event, arg):
        nonlocal count
        if event == "line":
            count += 1
        return local

    def global_(frame, event, arg):
        if frame.f_code.co_filename == target:
            return local
        return None

    previous = sys.gettrace()
    sys.settrace(global_)
    try:
        result = call()
    finally:
        sys.settrace(previous)
    return result, count


def test_extreme_dates_are_walked_by_visited_days_not_by_calendar():
    first = mv(date(1, 1, 1), "10")
    last = mv(date(9999, 12, 31), "-25")

    result, lines = _lines_executed_in_native_cash(lambda: first_negative([last, first]))

    assert result is not None
    assert (result.day, result.balance) == (date(9999, 12, 31), Decimal("-15"))
    assert_same_movements(result.reducers, (last,))
    assert lines < _LINE_BUDGET, f"{lines} lines executed in native_cash.py: the walk steps through the calendar"


def test_extreme_check_day_with_extreme_movement_is_walked_by_visited_days():
    result, lines = _lines_executed_in_native_cash(
        lambda: first_negative([mv(date(9999, 12, 31), "1")], opening={"EUR": Decimal("0")}, check_days=(date(1, 1, 1),)),
    )

    assert result is None
    assert lines < _LINE_BUDGET, f"{lines} lines executed in native_cash.py: the walk steps through the calendar"


# ---------------------------------------------------------------------------
# 8. Built from transactions
# ---------------------------------------------------------------------------


def test_movements_built_by_cash_movement_from_transaction():
    """The validator's path: transaction rows → cash_movement_from_transaction → first_negative_cash."""
    rows = [
        SimpleNamespace(id=11, type="DEPOSIT", date=d(1), broker_id=BROKER, asset_id=None, currency="EUR", amount=Decimal("50")),
        SimpleNamespace(id=12, type="BUY", date=d(2), broker_id=BROKER, asset_id=3, currency="EUR", amount=Decimal("-80")),
        SimpleNamespace(id=13, type="FEE", date=d(2), broker_id=BROKER, asset_id=3, currency="EUR", amount=Decimal("-1.5")),
    ]
    movements = [cash_movement_from_transaction(row) for row in rows]
    assert all(m is not None for m in movements)

    result = first_negative(movements)

    assert result is not None
    assert (result.day, result.currency, result.balance) == (d(2), "EUR", Decimal("-31.5"))
    assert [m.movement_id for m in result.reducers] == [12, 13]
