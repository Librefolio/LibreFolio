"""Exact numbers on the wire: finite decimals, reduced ratios, money, prices, FX rates and their availability, with the conversions to exact fractions the validators use."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from math import gcd
from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from backend.app.schemas.pac_allocator.base import AllocationStrictModel, CurrencyCode, PlannerFixedDecimal, PlannerIntegerText, PlannerPositiveDecimal, PlannerPositiveIntegerText, QuantityUnit


class FiniteDecimal(AllocationStrictModel):
    """Exact branch used only for a terminating base-10 value inside the bounded wire envelope."""

    kind: Literal["finite_decimal"]
    value: PlannerFixedDecimal


class ExactRatio(AllocationStrictModel):
    """Reduced exact branch used when the value has no bounded terminating representation."""

    kind: Literal["exact_ratio"]
    numerator: PlannerIntegerText
    denominator: PlannerPositiveIntegerText
    display_decimal: PlannerFixedDecimal = Field(description="Backend-authored display projection; never authoritative.")
    display_scale: Annotated[int, Field(strict=True, ge=0, le=18)]
    display_authority: Literal["non_authoritative"]

    @model_validator(mode="after")
    def validate_canonical_ratio(self) -> ExactRatio:
        if gcd(abs(int(self.numerator)), int(self.denominator)) != 1:
            raise ValueError("Exact ratio must be reduced to canonical terms")
        return self


type ExactNumber = Annotated[Union[FiniteDecimal, ExactRatio], Field(discriminator="kind")]


def fixed_fraction(value: str) -> Fraction:
    """Convert canonical fixed-point text without applying Decimal context precision."""

    return Fraction(Decimal(value))


def exact_fraction(value: FiniteDecimal | ExactRatio) -> Fraction:
    if isinstance(value, FiniteDecimal):
        return fixed_fraction(value.value)
    return Fraction(int(value.numerator), int(value.denominator))


def money_fraction(value: ExactMoney) -> Fraction:
    return exact_fraction(value.value)


class ExactMoney(AllocationStrictModel):
    value: ExactNumber
    currency: CurrencyCode


class ExactPrice(AllocationStrictModel):
    value: ExactNumber
    currency: CurrencyCode
    quote_base_quantity: PlannerPositiveDecimal
    quantity_unit: QuantityUnit

    @model_validator(mode="after")
    def validate_positive_value(self) -> ExactPrice:
        if exact_fraction(self.value) <= 0:
            raise ValueError("Exact price must be positive")
        return self


class ExactFxRate(AllocationStrictModel):
    source_currency: CurrencyCode
    destination_currency: CurrencyCode = Field(description="Currency units received per one source-currency unit.")
    value: ExactNumber

    @model_validator(mode="after")
    def validate_rate(self) -> ExactFxRate:
        if self.source_currency == self.destination_currency:
            raise ValueError("Published FX action rates must be non-identity")
        if exact_fraction(self.value) <= 0:
            raise ValueError("Exact FX rate must be positive")
        return self


class AvailableExactNumber(AllocationStrictModel):
    kind: Literal["available"]
    value: ExactNumber


class UnavailableExactNumber(AllocationStrictModel):
    kind: Literal["unavailable"]
    reason: Literal["zero_current_invested", "zero_final_invested", "not_applicable", "dependency_unavailable"]


type ExactNumberAvailability = Annotated[
    Union[AvailableExactNumber, UnavailableExactNumber],
    Field(discriminator="kind"),
]


def available_fraction(value: AvailableExactNumber | UnavailableExactNumber) -> Fraction | None:
    if isinstance(value, AvailableExactNumber):
        return exact_fraction(value.value)
    return None


def validate_weight_availability(
    values: list[AvailableExactNumber | UnavailableExactNumber],
    total: Fraction,
    zero_reason: str,
    label: str,
) -> None:
    fractions = [available_fraction(value) for value in values]
    if total == 0:
        if any(value is not None for value in fractions):
            raise ValueError(f"{label} weights must be unavailable at zero invested value")
        if any(value.reason != zero_reason for value in values if isinstance(value, UnavailableExactNumber)):
            raise ValueError(f"{label} weights must use the explicit zero-invested reason")
        return
    if any(value is None or value < 0 or value > 1 for value in fractions):
        raise ValueError(f"{label} weights must all be available unit-interval values")
    if sum((value for value in fractions if value is not None), Fraction()) != 1:
        raise ValueError(f"{label} weights must form a complete unit vector")
