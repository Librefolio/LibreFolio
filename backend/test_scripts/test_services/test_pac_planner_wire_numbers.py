"""Contract tests for the exact->wire numeric primitive (Step 3, Stage 5a).

``wire_numbers.py`` owns the single conversion every published planner figure
passes through: an exact domain ``ExactRatio`` becomes a wire ``ExactNumber``
(the ``finite_decimal`` branch for a terminating base-10 value, or the exact
``numerator``/``denominator`` branch otherwise). A subtle error here would
silently corrupt every figure downstream rather than failing anywhere
visible, so this suite pins the three properties the module promises:

1. **Canonical spelling is load-bearing, not cosmetic.** Several schema
   validators compare published wire forms for *exact string equality* (the
   accounting identity, the ledger reconciliation, the gap-bound
   cross-checks). ``1/2`` and ``50/100`` must therefore both serialise to
   ``"0.5"``: "equal values serialise identically" is a correctness property,
   and a contributor who "simplifies" the canonicalisation must be caught by
   a failing test rather than by a mis-reconciled ledger in production.
2. **Never lossy; fail closed rather than truncate.** The decimal branch is
   used only when the value genuinely terminates in base 10; a non-terminating
   value falls back to the exact numerator/denominator *losslessly*; and a
   value fitting neither bounded representation raises
   ``WireNumberTooLargeError`` instead of being truncated into range.
3. **The exact_ratio branch carries a deliberately non-authoritative display
   projection.** Its rounding is legitimate precisely because the schema
   labels it ``display_authority="non_authoritative"``; the authoritative
   numerator/denominator stay exact regardless of what the display rounds to.

These are pure in-process tests (``isolation="pure"``): no server, no
database, no clock, no sleeps, no network. Exact domain values compare with
``==``; ground truth is ``fractions.Fraction``, never float. The random
round-trip loop is seeded so it is deterministic, not a clock read.
"""

from __future__ import annotations

import re
from fractions import Fraction
from random import Random

import pytest

from backend.app.schemas.pac_allocator import (
    _PLANNER_FIXED_DECIMAL,
    ExactMoney,
    ExactPrice,
    FiniteDecimal,
    _exact_fraction,
)
from backend.app.schemas.pac_allocator import ExactRatio as WireExactRatio
from backend.app.services.pac_allocator.numeric import ExactRatio as R
from backend.app.services.pac_allocator.numeric import post_half_up
from backend.app.services.pac_allocator.wire_numbers import (
    MAX_DISPLAY_SCALE,
    MAX_FIXED_DECIMAL_CHARS,
    MAX_INTEGER_TEXT_CHARS,
    WireNumberTooLargeError,
    ratio_to_exact_number,
    ratio_to_fixed_decimal,
    ratio_to_money,
    ratio_to_price,
    terminating_decimal_text,
)

# The exact wire pattern for ``PlannerFixedDecimal``. Compiling it here lets a
# test assert that produced text is not merely *equal* to an expectation but
# is a string the frozen wire contract would actually admit.
_FIXED_DECIMAL_RE = re.compile(_PLANNER_FIXED_DECIMAL)

# Seed and iteration count are lifted verbatim from the accepted verification
# harness so the durable suite covers exactly the same random surface. A fixed
# seed is a deterministic input, not a clock read.
_ROUND_TRIP_SEED = 20260918
_ROUND_TRIP_SAMPLES = 6000


def _fraction_of(ratio: R) -> Fraction:
    return Fraction(ratio.numerator, ratio.denominator)


# --------------------------------------------------------------------------
# 1. Round-trip: the wire value is never anything but the exact input
# --------------------------------------------------------------------------


def test_round_trip_wire_value_equals_exact_input_for_random_rationals() -> None:
    """Every projection is value-preserving, whichever branch it takes.

    Property (never lossy): for a large seeded sample of rationals spanning
    both branches, reading the wire number back out with ``_exact_fraction``
    reproduces the exact input. Whenever the ``finite_decimal`` branch is
    taken, its text is additionally a string the wire pattern admits and fits
    the 96-character envelope — so the round-trip is exact *and* publishable.
    """
    rng = Random(_ROUND_TRIP_SEED)
    for _ in range(_ROUND_TRIP_SAMPLES):
        numerator = rng.randint(-(10 ** rng.randint(1, 12)), 10 ** rng.randint(1, 12))
        denominator = rng.randint(1, 10 ** rng.randint(1, 12))
        ratio = R(numerator, denominator)

        wire = ratio_to_exact_number(ratio)

        assert _exact_fraction(wire) == _fraction_of(ratio)
        if isinstance(wire, FiniteDecimal):
            assert _FIXED_DECIMAL_RE.match(wire.value), repr(wire.value)
            assert len(wire.value) <= MAX_FIXED_DECIMAL_CHARS


# --------------------------------------------------------------------------
# 2. Terminating detection matches the 2/5-only rule, exactly
# --------------------------------------------------------------------------


def test_terminating_detection_matches_two_five_only_rule() -> None:
    """A value terminates in base 10 iff its reduced denominator's only prime
    factors are 2 and 5. ``terminating_decimal_text`` must agree with that
    rule for every case, and when it does return text, that text must be the
    exact value — the detection is what protects the "never lossy" promise, so
    it is brute-forced rather than spot-checked.
    """
    for denominator in range(1, 600):
        for numerator in (1, 7, -3, 250):
            ratio = R(numerator, denominator)
            reduced = ratio.denominator
            while reduced % 2 == 0:
                reduced //= 2
            while reduced % 5 == 0:
                reduced //= 5
            expected_terminates = reduced == 1

            text = terminating_decimal_text(ratio)

            assert (text is not None) == expected_terminates, f"{ratio} -> {text}"
            if text is not None:
                assert Fraction(text) == _fraction_of(ratio)


# --------------------------------------------------------------------------
# 3. Canonical spelling — the property schema validators depend on
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [
        (R(0, 1), "0"),
        (R(0, 7), "0"),
        (R(1, 2), "0.5"),
        (R(-1, 2), "-0.5"),
        (R(5, 1), "5"),
        (R(-5, 1), "-5"),
        (R(10, 4), "2.5"),
        (R(1, 8), "0.125"),
        (R(-1, 8), "-0.125"),
        (R(100, 10), "10"),
        (R(3, 1), "3"),
        (R(-250, 100), "-2.5"),
        (R(1, 1000), "0.001"),
    ],
)
def test_terminating_decimal_text_is_canonical(ratio: R, expected: str) -> None:
    """One and only one spelling per value: no trailing fractional zeros, no
    leading zeros, and never ``-0``. This is not tidiness — several schema
    validators reconcile figures by comparing their published *strings*, so a
    second admissible spelling of the same value would break an identity that
    holds numerically. Anyone tempted to change the canonical form is meant to
    land here first.
    """
    text = terminating_decimal_text(ratio)
    assert text == expected
    assert _FIXED_DECIMAL_RE.match(text), repr(text)
    # The canonical guarantees, restated structurally so the intent survives
    # even if the table above is edited: sign only on a nonzero magnitude, no
    # redundant leading zero, no trailing fractional zero.
    assert not text.startswith("-0") or text == "0" or text.startswith("-0.")
    if "." in text:
        assert not text.endswith("0")


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (R(1, 2), R(50, 100)),
        (R(3, 1), R(300, 100)),
        (R(-1, 4), R(-25, 100)),
    ],
)
def test_equal_values_serialise_identically(left: R, right: R) -> None:
    """The load-bearing consequence of canonicalisation: two exact values that
    are equal produce byte-identical wire text. ``ExactRatio`` reduces on
    construction, so ``50/100`` *is* ``1/2`` before it ever reaches the
    projection — this test guards the property a validator relies on when it
    compares two independently-derived figures for string equality.
    """
    assert left == right  # same domain value by construction (reduced form)
    assert terminating_decimal_text(left) == terminating_decimal_text(right)


# --------------------------------------------------------------------------
# 4. Non-terminating falls back to the exact ratio, losslessly
# --------------------------------------------------------------------------


@pytest.mark.parametrize("ratio", [R(1, 3), R(2, 7), R(-5, 11), R(22, 7)])
def test_non_terminating_falls_back_to_exact_ratio(ratio: R) -> None:
    """A value that does not terminate in base 10 cannot use the decimal
    branch, so it takes the exact-ratio branch and carries its numerator and
    denominator verbatim. The fallback is lossless: reading it back reproduces
    the exact input, and the numerator/denominator are the reduced form.
    """
    wire = ratio_to_exact_number(ratio)
    assert isinstance(wire, WireExactRatio)
    assert wire.kind == "exact_ratio"
    assert _exact_fraction(wire) == _fraction_of(ratio)
    assert int(wire.numerator) == ratio.numerator
    assert int(wire.denominator) == ratio.denominator


# --------------------------------------------------------------------------
# 5. The exact_ratio branch's display projection is honest, not authoritative
# --------------------------------------------------------------------------


@pytest.mark.parametrize("ratio", [R(1, 3), R(2, 7), R(-5, 11), R(22, 7), R(355, 113), R(-1, 7)])
def test_exact_ratio_display_projection_is_non_authoritative_and_exact_underneath(ratio: R) -> None:
    """The exact-ratio branch publishes an authoritative numerator/denominator
    *plus* a rounded ``display_decimal`` the schema itself flags as not the
    truth. This test asserts all three halves of that contract:

    * the display is explicitly ``display_authority="non_authoritative"``;
    * ``display_scale`` describes the digits actually emitted;
    * the authoritative value stays exact regardless of what the display
      rounds to.

    The rounding convention is checked to be HALF_UP with ties away from zero,
    matching ``numeric.post_half_up`` rather than a second convention: the
    display is reproduced independently by rounding the exact value to the
    published scale with ``post_half_up``. (These fixtures are small, so the
    projection rounds at ``MAX_DISPLAY_SCALE`` and only trailing zeros — never
    a coarser scale — reduce the emitted digit count.)
    """
    wire = ratio_to_exact_number(ratio)
    assert isinstance(wire, WireExactRatio)
    assert wire.display_authority == "non_authoritative"

    # Authoritative value is exact, whatever the display shows.
    assert _exact_fraction(wire) == _fraction_of(ratio)

    # display_scale is exactly the number of fractional digits emitted.
    fractional_digits = wire.display_decimal.split(".")[1] if "." in wire.display_decimal else ""
    assert wire.display_scale == len(fractional_digits)
    assert _FIXED_DECIMAL_RE.match(wire.display_decimal), repr(wire.display_decimal)

    # The display equals the exact value rounded HALF_UP (ties away from zero)
    # to the published scale — computed independently via post_half_up.
    rounded = post_half_up(ratio, R(1, 10**MAX_DISPLAY_SCALE)).posted
    assert Fraction(wire.display_decimal) == _fraction_of(rounded)
    # Rounded to a real scale, the display never over- or under-states beyond
    # a single quantum of the published scale.
    assert abs(_fraction_of(rounded) - _fraction_of(ratio)) <= Fraction(1, 2 * 10**MAX_DISPLAY_SCALE)


def test_display_scale_never_exceeds_wire_bound() -> None:
    """``display_scale`` rides an ``int`` bounded to ``0..18`` on the wire; the
    projection must never emit more, or pydantic would reject the model with a
    message about an integer bound rather than about a number.
    """
    for ratio in (R(1, 3), R(2, 7), R(-5, 11), R(22, 7), R(1, 6), R(5, 11)):
        wire = ratio_to_exact_number(ratio)
        assert isinstance(wire, WireExactRatio)
        assert 0 <= wire.display_scale <= MAX_DISPLAY_SCALE


# --------------------------------------------------------------------------
# 6. Fail closed rather than truncate — the three (+1) raise paths
# --------------------------------------------------------------------------


def test_fixed_decimal_raises_on_non_terminating_value() -> None:
    """Raise path 1: ``ratio_to_fixed_decimal`` has no exact-ratio escape
    hatch (its callers are ledger fixed-decimal fields), so a value that does
    not terminate must raise rather than invent a rounding. The exact type is
    asserted — a guard that raised a bare ``Exception`` would let a caller that
    only catches ``WireNumberTooLargeError`` crash instead of failing closed.
    """
    with pytest.raises(WireNumberTooLargeError):
        ratio_to_fixed_decimal(R(1, 3))


def test_huge_terminating_value_falls_back_losslessly_but_fixed_decimal_raises() -> None:
    """Raise path 2, and the non-lossy promise at the envelope boundary.

    ``1 / 2**400`` *terminates* in base 10 but its decimal text is far longer
    than the 96-character fixed-decimal envelope. So:

    * ``terminating_decimal_text`` still returns the exact (over-long) text;
    * ``ratio_to_exact_number`` does not truncate it — it falls back to the
      exact-ratio branch, losslessly;
    * ``ratio_to_fixed_decimal`` (which cannot fall back) fails closed.

    Truncating the figure to fit the string bound is the exact silent
    degradation this package exists to refuse.
    """
    huge = R(1, 2**400)

    text = terminating_decimal_text(huge)
    assert text is not None
    assert len(text) > MAX_FIXED_DECIMAL_CHARS

    wire = ratio_to_exact_number(huge)
    assert isinstance(wire, WireExactRatio)
    assert wire.kind == "exact_ratio"
    assert _exact_fraction(wire) == Fraction(1, 2**400)

    with pytest.raises(WireNumberTooLargeError):
        ratio_to_fixed_decimal(huge)


def test_enormous_non_terminating_value_raises_on_integer_text_bound() -> None:
    """Raise path 3: a non-terminating value whose numerator text exceeds the
    192-character integer-text envelope cannot be published exactly at all, so
    ``ratio_to_exact_number`` fails closed rather than emitting a truncated
    numerator.
    """
    enormous = R(10**200 + 1, 3)
    with pytest.raises(WireNumberTooLargeError):
        ratio_to_exact_number(enormous)


def test_display_projection_with_no_representable_form_raises() -> None:
    """Raise path 4 (the display-projection envelope): a non-terminating value
    whose integer part alone overflows the 96-character fixed-decimal window
    has no admissible display at any scale, and ``ratio_to_exact_number``
    raises. The numerator here is 121 digits — within the 192-char integer
    envelope, so it passes that gate and reaches the display projection, which
    is the branch under test.
    """
    no_display = R(10**120, 3)
    assert len(str(no_display.numerator)) <= MAX_INTEGER_TEXT_CHARS
    with pytest.raises(WireNumberTooLargeError):
        ratio_to_exact_number(no_display)


# --------------------------------------------------------------------------
# 7. Money / price projections wrap the primitive without changing its rules
# --------------------------------------------------------------------------


def test_ratio_to_money_carries_currency_and_exact_value() -> None:
    """``ratio_to_money`` is a thin wrapper: the value obeys the same branch
    rules (terminating -> finite_decimal), the currency rides alongside, and
    the amount reads back exactly.
    """
    money = ratio_to_money(R(1, 2), "EUR")
    assert isinstance(money, ExactMoney)
    assert money.currency == "EUR"
    assert isinstance(money.value, FiniteDecimal)
    assert money.value.value == "0.5"
    assert _exact_fraction(money.value) == Fraction(1, 2)


def test_ratio_to_money_uses_exact_ratio_branch_for_non_terminating() -> None:
    """The wrapper does not force termination: a non-terminating amount is
    carried on the exact-ratio branch, losslessly, exactly like the primitive.
    """
    money = ratio_to_money(R(1, 3), "USD")
    assert money.currency == "USD"
    assert isinstance(money.value, WireExactRatio)
    assert _exact_fraction(money.value) == Fraction(1, 3)


def test_ratio_to_price_projects_value_and_quote_base() -> None:
    """``ratio_to_price`` publishes an exact unit price plus a terminating
    ``quote_base_quantity`` fixed-decimal. The price value may be
    non-terminating (it uses the exact union); the quote base must terminate
    because it rides a positive-decimal field.
    """
    price = ratio_to_price(R(3, 2), "USD", R(1))
    assert isinstance(price, ExactPrice)
    assert price.currency == "USD"
    assert price.quantity_unit == "asset_unit"
    assert price.quote_base_quantity == "1"
    assert _exact_fraction(price.value) == Fraction(3, 2)


def test_ratio_to_price_rejects_non_terminating_quote_base() -> None:
    """The quote base has no exact-ratio escape hatch, so a non-terminating
    ``quote_base_quantity`` fails closed rather than being rounded into a
    quote convention it is not.
    """
    with pytest.raises(WireNumberTooLargeError):
        ratio_to_price(R(3, 2), "USD", R(1, 3))


# --------------------------------------------------------------------------
# 8. Public envelope constants and the error contract are part of the wire
# --------------------------------------------------------------------------


def test_public_envelope_constants_are_stable() -> None:
    """These bounds mirror the frozen wire constraints and are imported by
    callers; pin them so a change to the envelope is a deliberate, visible
    edit rather than a silent drift.
    """
    assert MAX_FIXED_DECIMAL_CHARS == 96
    assert MAX_INTEGER_TEXT_CHARS == 192
    assert MAX_DISPLAY_SCALE == 18


def test_wire_number_too_large_error_is_a_value_error() -> None:
    """The fail-closed error is a ``ValueError`` subtype, so existing
    value-validation call sites catch it without a special case — but it is a
    *named* subtype so a caller may distinguish "outgrew the contract" from a
    generic bad value when it wants to.
    """
    assert issubclass(WireNumberTooLargeError, ValueError)
