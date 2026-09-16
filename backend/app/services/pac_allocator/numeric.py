"""Exact PAC arithmetic primitives plus legacy P1 Decimal helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, DivisionByZero, Inexact, InvalidOperation, Overflow
from functools import total_ordering
from math import gcd
from typing import Self

P1_DECIMAL_PRECISION = 256
RATIO_DECIMAL_PLACES = 28
ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


class ExactArithmeticError(ArithmeticError):
    """Base error for exact PAC arithmetic."""


class InvalidExactRatioError(ExactArithmeticError):
    """Raised when an exact ratio cannot be constructed from supplied values."""


class ExactDivisionByZeroError(ExactArithmeticError):
    """Raised when exact arithmetic would divide by zero."""


class NonFiniteDecimalError(ExactArithmeticError):
    """Raised when a Decimal-to-ratio conversion receives NaN or infinity."""


class NonTerminatingDecimalError(ExactArithmeticError):
    """Raised when an exact ratio has no finite base-10 representation."""


class InvalidQuantumError(ExactArithmeticError):
    """Raised when a rounding quantum is not strictly positive."""


class InvalidEconomicInputError(ExactArithmeticError):
    """Raised when a pure financial formula receives an invalid value."""


@total_ordering
@dataclass(frozen=True, slots=True, eq=False)
class ExactRatio:
    """Canonical exact rational backed only by Python integers."""

    numerator: int
    denominator: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.numerator, bool) or not isinstance(self.numerator, int):
            raise InvalidExactRatioError("ExactRatio numerator must be an integer")
        if isinstance(self.denominator, bool) or not isinstance(self.denominator, int):
            raise InvalidExactRatioError("ExactRatio denominator must be an integer")
        if self.denominator == 0:
            raise ExactDivisionByZeroError("ExactRatio denominator must be nonzero")

        numerator = self.numerator
        denominator = self.denominator
        if numerator == 0:
            denominator = 1
        else:
            if denominator < 0:
                numerator = -numerator
                denominator = -denominator
            divisor = gcd(abs(numerator), denominator)
            numerator //= divisor
            denominator //= divisor

        object.__setattr__(self, "numerator", numerator)
        object.__setattr__(self, "denominator", denominator)

    @classmethod
    def from_decimal(cls, value: Decimal) -> Self:
        """Convert a finite Decimal losslessly without using float."""
        if not isinstance(value, Decimal):
            raise InvalidExactRatioError("ExactRatio.from_decimal requires Decimal")
        if not value.is_finite():
            raise NonFiniteDecimalError("ExactRatio requires a finite Decimal")
        numerator, denominator = value.as_integer_ratio()
        return cls(numerator, denominator)

    @staticmethod
    def _coerce(value: object) -> ExactRatio:
        if isinstance(value, ExactRatio):
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return ExactRatio(value)
        raise InvalidExactRatioError(f"ExactRatio operation requires ExactRatio or int, got {type(value).__name__}")

    def __hash__(self) -> int:
        if self.denominator == 1:
            return hash(self.numerator)
        return hash((self.numerator, self.denominator))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ExactRatio):
            return self.numerator == other.numerator and self.denominator == other.denominator
        if isinstance(other, int) and not isinstance(other, bool):
            return self.denominator == 1 and self.numerator == other
        return False

    def __lt__(self, other: object) -> bool:
        ratio = self._coerce(other)
        return self.numerator * ratio.denominator < ratio.numerator * self.denominator

    def __neg__(self) -> ExactRatio:
        return ExactRatio(-self.numerator, self.denominator)

    def __abs__(self) -> ExactRatio:
        return ExactRatio(abs(self.numerator), self.denominator)

    def __bool__(self) -> bool:
        return self.numerator != 0

    def __add__(self, other: object) -> ExactRatio:
        ratio = self._coerce(other)
        return ExactRatio(
            self.numerator * ratio.denominator + ratio.numerator * self.denominator,
            self.denominator * ratio.denominator,
        )

    def __radd__(self, other: object) -> ExactRatio:
        return self + other

    def __sub__(self, other: object) -> ExactRatio:
        return self + -self._coerce(other)

    def __rsub__(self, other: object) -> ExactRatio:
        return self._coerce(other) - self

    def __mul__(self, other: object) -> ExactRatio:
        ratio = self._coerce(other)
        return ExactRatio(
            self.numerator * ratio.numerator,
            self.denominator * ratio.denominator,
        )

    def __rmul__(self, other: object) -> ExactRatio:
        return self * other

    def __truediv__(self, other: object) -> ExactRatio:
        ratio = self._coerce(other)
        if ratio.numerator == 0:
            raise ExactDivisionByZeroError("Cannot divide ExactRatio by zero")
        return ExactRatio(
            self.numerator * ratio.denominator,
            self.denominator * ratio.numerator,
        )

    def __rtruediv__(self, other: object) -> ExactRatio:
        if self.numerator == 0:
            raise ExactDivisionByZeroError("Cannot divide by zero ExactRatio")
        return self._coerce(other) / self

    def square(self) -> ExactRatio:
        return ExactRatio(
            self.numerator * self.numerator,
            self.denominator * self.denominator,
        )

    def as_integer_ratio(self) -> tuple[int, int]:
        return self.numerator, self.denominator

    def to_decimal_exact(self) -> Decimal:
        """Project to Decimal only when the base-10 expansion terminates."""
        denominator = self.denominator
        powers_of_two = 0
        powers_of_five = 0
        while denominator % 2 == 0:
            denominator //= 2
            powers_of_two += 1
        while denominator % 5 == 0:
            denominator //= 5
            powers_of_five += 1
        if denominator != 1:
            raise NonTerminatingDecimalError(f"ExactRatio {self} has no finite Decimal representation")

        decimal_places = max(powers_of_two, powers_of_five)
        scaled_numerator = self.numerator * 2 ** (decimal_places - powers_of_two) * 5 ** (decimal_places - powers_of_five)
        if decimal_places == 0:
            return Decimal(scaled_numerator)

        sign = "-" if scaled_numerator < 0 else ""
        digits = str(abs(scaled_numerator)).rjust(decimal_places + 1, "0")
        return Decimal(f"{sign}{digits[:-decimal_places]}.{digits[-decimal_places:]}")

    def __str__(self) -> str:
        if self.denominator == 1:
            return str(self.numerator)
        return f"{self.numerator}/{self.denominator}"


@dataclass(frozen=True, slots=True)
class PostedAmount:
    """Exact value and its one-time posting on an explicit quantum.

    ``rounding_delta`` is the raw ``posted - exact`` difference. The future
    ledger must use that sign for debit families and negate it for credit
    families when composing ``A_round``. Posting direction remains outside
    this pre-G3 numeric primitive.
    """

    exact: ExactRatio
    posted: ExactRatio
    quantum: ExactRatio
    units: int
    rounding_delta: ExactRatio  # posted - exact


_EXACT_ZERO = ExactRatio(0)
_EXACT_ONE = ExactRatio(1)


def _require_ratio(name: str, value: ExactRatio) -> None:
    if not isinstance(value, ExactRatio):
        raise InvalidEconomicInputError(f"{name} must be an ExactRatio, got {type(value).__name__}")


def _require_nonnegative(name: str, value: ExactRatio) -> None:
    _require_ratio(name, value)
    if value < _EXACT_ZERO:
        raise InvalidEconomicInputError(f"{name} must be nonnegative")


def _require_positive_quantum(quantum: ExactRatio) -> None:
    if not isinstance(quantum, ExactRatio) or quantum <= _EXACT_ZERO:
        raise InvalidQuantumError("Posting quantum must be a positive ExactRatio")


def post_half_up(value: ExactRatio, quantum: ExactRatio) -> PostedAmount:
    """Round a signed exact value to nearest quantum, with ties away from zero."""
    _require_ratio("value", value)
    _require_positive_quantum(quantum)

    scaled_numerator = abs(value.numerator) * quantum.denominator
    scaled_denominator = value.denominator * quantum.numerator
    whole_units, remainder = divmod(scaled_numerator, scaled_denominator)
    if 2 * remainder >= scaled_denominator:
        whole_units += 1
    units = -whole_units if value.numerator < 0 else whole_units
    posted = quantum * units
    return PostedAmount(
        exact=value,
        posted=posted,
        quantum=quantum,
        units=units,
        rounding_delta=posted - value,
    )


def ceil_to_quantum_units(value: ExactRatio, quantum: ExactRatio) -> int:
    """Return the mathematical ceiling of value / positive quantum."""
    _require_ratio("value", value)
    _require_positive_quantum(quantum)
    scaled_numerator = value.numerator * quantum.denominator
    scaled_denominator = value.denominator * quantum.numerator
    return -((-scaled_numerator) // scaled_denominator)


def calculate_fee(
    *,
    notional: ExactRatio,
    fixed: ExactRatio,
    rate: ExactRatio,
    floor: ExactRatio,
    cap: ExactRatio | None,
) -> ExactRatio:
    """Return the exact pre-posting fee for a caller-supplied fee schedule."""
    _require_nonnegative("notional", notional)
    _require_nonnegative("fixed", fixed)
    _require_nonnegative("rate", rate)
    _require_nonnegative("floor", floor)
    if cap is not None:
        _require_nonnegative("cap", cap)
        if floor > cap:
            raise InvalidEconomicInputError("fee floor must not exceed fee cap")
    if notional == _EXACT_ZERO:
        return _EXACT_ZERO

    variable = rate * notional
    if variable < floor:
        variable = floor
    if cap is not None and variable > cap:
        variable = cap
    return fixed + variable


def calculate_effective_fx_rate(
    *,
    approved_rate: ExactRatio,
    spread: ExactRatio,
) -> ExactRatio:
    """Return target-currency units per source-currency unit after spread."""
    _require_ratio("approved_rate", approved_rate)
    _require_nonnegative("spread", spread)
    if approved_rate <= _EXACT_ZERO:
        raise InvalidEconomicInputError("approved_rate must be positive")
    if spread >= _EXACT_ONE:
        raise InvalidEconomicInputError("spread must be less than one")
    return approved_rate * (_EXACT_ONE - spread)


def calculate_fx_credit(
    *,
    source_debit: ExactRatio,
    approved_rate: ExactRatio,
    spread: ExactRatio,
) -> ExactRatio:
    """Return exact target-currency credit before quantum posting.

    ``source_debit`` is in source-currency units and ``approved_rate`` is
    target-currency units per one source-currency unit.
    """
    _require_nonnegative("source_debit", source_debit)
    effective_rate = calculate_effective_fx_rate(
        approved_rate=approved_rate,
        spread=spread,
    )
    return source_debit * effective_rate


def calculate_taxable_gain(
    *,
    gross_sell_proceeds: ExactRatio,
    sell_fee: ExactRatio,
    sold_quantity: ExactRatio,
    unit_cost: ExactRatio,
) -> ExactRatio:
    """Return max(gross proceeds - fee - sold cost basis, 0)."""
    _require_nonnegative("gross_sell_proceeds", gross_sell_proceeds)
    _require_nonnegative("sell_fee", sell_fee)
    _require_nonnegative("sold_quantity", sold_quantity)
    _require_nonnegative("unit_cost", unit_cost)
    gain = gross_sell_proceeds - sell_fee - sold_quantity * unit_cost
    return gain if gain > _EXACT_ZERO else _EXACT_ZERO


def calculate_tax_reserve(
    *,
    gross_sell_proceeds: ExactRatio,
    sell_fee: ExactRatio,
    sold_quantity: ExactRatio,
    unit_cost: ExactRatio,
    tax_rate: ExactRatio,
) -> ExactRatio:
    """Return exact SELL tax reserve before caller-selected quantum posting."""
    _require_nonnegative("tax_rate", tax_rate)
    if tax_rate > _EXACT_ONE:
        raise InvalidEconomicInputError("tax_rate must not exceed one")
    taxable_gain = calculate_taxable_gain(
        gross_sell_proceeds=gross_sell_proceeds,
        sell_fee=sell_fee,
        sold_quantity=sold_quantity,
        unit_cost=unit_cost,
    )
    return taxable_gain * tax_rate


def decimal_context() -> Context:
    return Context(prec=P1_DECIMAL_PRECISION, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999, traps=[DivisionByZero, Inexact, InvalidOperation, Overflow])


def decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise ArithmeticError("Non-finite value in PAC analysis")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("0", "-0") else text


def exact_holding_value(
    quantity: Decimal,
    raw_price: Decimal,
    quote_base_quantity: int,
) -> Decimal:
    """Preserve exact products before applying the integer quote basis."""
    return quantity * raw_price / Decimal(quote_base_quantity)


def ratio_approximation(numerator: Decimal, denominator: Decimal) -> tuple[str, bool]:
    if denominator <= 0:
        raise ArithmeticError("PAC ratio denominator must be positive")
    n_value, n_scale = numerator.as_integer_ratio()
    d_value, d_scale = denominator.as_integer_ratio()
    divisor = n_scale * d_value
    scaled, remainder = divmod(abs(n_value) * d_scale * 10**RATIO_DECIMAL_PLACES, divisor)
    digits = str(scaled).rjust(RATIO_DECIMAL_PLACES + 1, "0")
    whole, fraction = digits[:-RATIO_DECIMAL_PLACES], digits[-RATIO_DECIMAL_PLACES:].rstrip("0")
    text = f"{whole}.{fraction}" if fraction else whole
    if n_value < 0 and scaled != 0:
        text = f"-{text}"
    return text, remainder == 0
