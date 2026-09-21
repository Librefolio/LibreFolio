"""Exact-rational to wire-number projection for the PAC/Rebalancer planner (Step 3, Stage 5a).

Every published number in a planner result starts life as an ``ExactRatio``
in the domain and has to become a wire ``ExactNumber`` — either the
``finite_decimal`` branch (a terminating base-10 value) or the
``exact_ratio`` branch (numerator/denominator text). This module owns that
one conversion and nothing else, because it is the single primitive the whole
report projection rests on: a subtle error here would silently corrupt every
figure downstream rather than failing anywhere visible.

Three rules it enforces:

1. **Never lossy.** A ratio becomes ``finite_decimal`` only when it genuinely
   terminates in base 10 — i.e. once the fraction is in lowest terms, its
   denominator's only prime factors are 2 and 5. Everything else keeps its
   exact numerator/denominator. No rounding, no "close enough", no float ever
   touches the value.
2. **Canonical.** The decimal branch emits one and only one spelling per
   value: no trailing fractional zeros, no ``-0``, no leading zeros. Two
   equal values therefore always serialize identically, which matters because
   several schema validators compare published figures for exact equality
   (the accounting identity, the ledger reconciliation, the gap-bound
   cross-checks).
3. **Fail closed on the wire envelope.** The wire caps
   ``PlannerFixedDecimal`` at 96 characters and the integer texts at 192. A
   value that fits neither representation is a genuine contract violation, so
   it raises ``WireNumberTooLargeError`` rather than being truncated or
   silently rounded into range. Truncating a financial figure to satisfy a
   string bound is exactly the class of silent degradation this package keeps
   removing.
"""

from __future__ import annotations

from backend.app.schemas.pac_allocator import ExactMoney, ExactNumber, ExactPrice, FiniteDecimal
from backend.app.schemas.pac_allocator import ExactRatio as WireExactRatio
from backend.app.services.pac_allocator.numeric import ExactRatio

__all__ = [
    "MAX_DISPLAY_SCALE",
    "MAX_FIXED_DECIMAL_CHARS",
    "MAX_INTEGER_TEXT_CHARS",
    "WireNumberTooLargeError",
    "ratio_to_exact_number",
    "ratio_to_fixed_decimal",
    "ratio_to_money",
    "ratio_to_price",
    "terminating_decimal_text",
]

# Mirrors the wire constraints (`PlannerFixedDecimal` max_length=96,
# `PlannerIntegerText`/`PlannerPositiveIntegerText` max_length=192). Restated
# here so the conversion can refuse *before* building a model that Pydantic
# would reject with a message about string length rather than about money.
MAX_FIXED_DECIMAL_CHARS = 96
MAX_INTEGER_TEXT_CHARS = 192

# `ExactRatio.display_scale` is bounded to 0..18 on the wire.
MAX_DISPLAY_SCALE = 18


class WireNumberTooLargeError(ValueError):
    """Raised when an exact value fits neither wire representation.

    Deliberately not recoverable by rounding: a figure too large to publish
    exactly is a scenario that has outgrown the contract, and the caller must
    learn that rather than receive a quietly altered number.
    """


def terminating_decimal_text(value: ExactRatio) -> str | None:
    """Return ``value`` as canonical decimal text, or ``None`` if it does not
    terminate in base 10.

    ``ExactRatio`` normalizes to lowest terms on construction, so the
    terminating test is simply whether the denominator reduces to 1 after
    removing all factors of 2 and 5. The digits are then produced by exact
    integer arithmetic — ``numerator * 10**places // denominator`` is exact
    precisely because that denominator divides ``10**places`` — so no float
    or Decimal context is involved at any point.
    """
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        return None

    places = max(twos, fives)
    scaled = value.numerator * 10**places // value.denominator
    negative = scaled < 0
    digits = str(abs(scaled)).rjust(places + 1, "0")
    if places:
        integer_part, fractional_part = digits[: len(digits) - places], digits[len(digits) - places :]
        # Both the strip and the empty-fraction fallback below are
        # DELIBERATELY UNREACHABLE for a canonical ``ExactRatio``, and are
        # kept as defence rather than removed. The argument, written out so a
        # future reader can re-derive it instead of trusting the word:
        #
        #   ``ExactRatio`` normalizes on construction, so ``gcd(n, d) == 1``
        #   and, past the terminating test above, ``d == 2**a * 5**b`` with
        #   ``places == max(a, b)``. Hence
        #       scaled = n * 10**places / d = n * 2**(places-a) * 5**(places-b)
        #   and exactly one of those two exponents is zero. The surviving
        #   factor is a power of 2 or a power of 5 — never both — so it
        #   contributes no factor 10, and ``n`` is coprime to ``d`` and
        #   therefore to 10. So ``scaled`` is never divisible by 10: the
        #   fractional part cannot end in a zero, and cannot be all zeros.
        #
        # If ``ExactRatio`` ever stops normalizing on construction, this
        # branch becomes live and this comment is the notice that the
        # invariant underneath it moved. Do not "simplify" it away on the
        # strength of a coverage report: covering it would require
        # constructing a non-normalised ratio, i.e. asserting behaviour for an
        # input the type forbids.
        fractional_part = fractional_part.rstrip("0")
        text = f"{integer_part}.{fractional_part}" if fractional_part else integer_part
    else:
        text = digits
    # `negative` can only be true when the magnitude is nonzero — by the same
    # argument, ``scaled = n * (positive integer)``, so its sign is exactly the
    # sign of ``n`` — which is why this never produces the "-0" the wire
    # pattern forbids.
    return f"-{text}" if negative else text


def ratio_to_fixed_decimal(value: ExactRatio) -> str:
    """Return canonical fixed-decimal text for a value that must terminate.

    Used for ``PlannerFixedDecimal`` fields — the ledger rows — where the wire
    has no exact-ratio escape hatch. Every ledger figure is a posted amount,
    i.e. an integer multiple of a currency quantum, so termination is
    guaranteed in practice; if it ever is not, that is a real defect and this
    raises instead of inventing a rounding.
    """
    text = terminating_decimal_text(value)
    if text is None:
        raise WireNumberTooLargeError(f"{value.numerator}/{value.denominator} does not terminate in base 10 and cannot be published as fixed-decimal text")
    if len(text) > MAX_FIXED_DECIMAL_CHARS:
        raise WireNumberTooLargeError(f"fixed-decimal text of {len(text)} characters exceeds the wire limit of {MAX_FIXED_DECIMAL_CHARS}")
    return text


def _display_projection(value: ExactRatio) -> tuple[str, int]:
    """Build the wire's ``display_decimal``/``display_scale`` pair.

    The ``exact_ratio`` branch publishes the authoritative numerator and
    denominator *plus* a rounded decimal that the schema itself marks
    ``display_authority="non_authoritative"``. That is the contract being
    honest about its own rounding: consumers get something readable without
    anyone pretending it is the value. This helper is therefore the one place
    in the module where rounding is legitimate — precisely because the result
    is explicitly labelled as not the truth.

    Rounding is HALF_UP with ties away from zero, matching
    ``numeric.post_half_up`` rather than inventing a second convention, and is
    done in pure integer arithmetic so no Decimal context or float is
    involved. The scale is reduced until the text fits the wire envelope, and
    ``display_scale`` always describes the digits actually emitted.
    """
    for scale in range(MAX_DISPLAY_SCALE, -1, -1):
        scaled_numerator = abs(value.numerator) * 10**scale
        whole, remainder = divmod(scaled_numerator, value.denominator)
        if 2 * remainder >= value.denominator:
            whole += 1
        digits = str(whole).rjust(scale + 1, "0")
        if scale:
            integer_part, fractional_part = digits[: len(digits) - scale], digits[len(digits) - scale :]
            fractional_part = fractional_part.rstrip("0")
            text = f"{integer_part}.{fractional_part}" if fractional_part else integer_part
            emitted_scale = len(fractional_part)
        else:
            text = digits
            emitted_scale = 0
        # `whole == 0` means the magnitude rounded away entirely, so the sign
        # must be dropped: the wire pattern forbids "-0".
        if whole != 0 and value.numerator < 0:
            text = f"-{text}"
        if len(text) <= MAX_FIXED_DECIMAL_CHARS:
            return text, emitted_scale
    raise WireNumberTooLargeError(f"exact value {value.numerator}/{value.denominator} has no display projection within the wire's {MAX_FIXED_DECIMAL_CHARS}-character limit")


def ratio_to_exact_number(value: ExactRatio) -> ExactNumber:
    """Project one exact rational onto the wire ``ExactNumber`` union.

    Prefers ``finite_decimal`` when the value terminates *and* fits the
    envelope, because it is far more readable for consumers; falls back to the
    exact numerator/denominator otherwise. Both branches carry the exact value
    losslessly — the choice is presentational, never numerical. The fallback
    additionally carries a rounded, explicitly non-authoritative display
    projection (see ``_display_projection``).
    """
    text = terminating_decimal_text(value)
    if text is not None and len(text) <= MAX_FIXED_DECIMAL_CHARS:
        return FiniteDecimal(kind="finite_decimal", value=text)

    numerator_text = str(value.numerator)
    denominator_text = str(value.denominator)
    if len(numerator_text) > MAX_INTEGER_TEXT_CHARS or len(denominator_text) > MAX_INTEGER_TEXT_CHARS:
        raise WireNumberTooLargeError(f"exact value {numerator_text[:32]}.../{denominator_text[:32]}... exceeds the wire integer-text limit of {MAX_INTEGER_TEXT_CHARS} characters and cannot be published without loss")
    display_decimal, display_scale = _display_projection(value)
    return WireExactRatio(
        kind="exact_ratio",
        numerator=numerator_text,
        denominator=denominator_text,
        display_decimal=display_decimal,
        display_scale=display_scale,
        display_authority="non_authoritative",
    )


def ratio_to_money(value: ExactRatio, currency: str) -> ExactMoney:
    """Project an exact amount plus its currency onto wire ``ExactMoney``."""
    return ExactMoney(value=ratio_to_exact_number(value), currency=currency)


def ratio_to_price(value: ExactRatio, currency: str, quote_base_quantity: ExactRatio) -> ExactPrice:
    """Project an exact unit price onto wire ``ExactPrice``.

    ``quote_base_quantity`` rides a ``PlannerPositiveDecimal`` field rather
    than the exact union, so it must terminate; it is a quote convention (1,
    100, 1000) rather than a computed quantity, so that is not a practical
    constraint — but it is enforced rather than assumed.
    """
    return ExactPrice(
        value=ratio_to_exact_number(value),
        currency=currency,
        quote_base_quantity=ratio_to_fixed_decimal(quote_base_quantity),
        quantity_unit="asset_unit",
    )
