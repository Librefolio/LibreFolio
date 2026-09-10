"""Immutable numeric state shared by normalization and initial evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

from backend.app.schemas.pac_allocator import FactReason, GridMode, PacAnalyzeIssue

Checkpoint = Callable[[], None]


@dataclass(frozen=True, slots=True)
class ParsedValue[T]:
    value: T | None
    reason: FactReason | None = None

    @property
    def available(self) -> bool:
        return self.reason is None and self.value is not None

    def require(self) -> T:
        if not self.available or self.value is None:
            raise RuntimeError("Required normalized value is unavailable")
        return self.value


@dataclass(frozen=True, slots=True)
class ParsedQuote:
    price: ParsedValue[Decimal]
    currency: ParsedValue[str]
    basis: ParsedValue[int]
    reference_date: date | None
    date_valid: bool


@dataclass(frozen=True, slots=True)
class ParsedGrid:
    mode: GridMode | None
    step: ParsedValue[Decimal]


@dataclass(frozen=True, slots=True)
class ParsedRow:
    row_key: str
    instrument_key: str
    name: str | None
    quantity: ParsedValue[Decimal]
    quote: ParsedQuote
    target: ParsedValue[Decimal]
    grid: ParsedGrid


@dataclass(frozen=True, slots=True)
class ParsedMoneyVector:
    entries: tuple[tuple[str, Decimal], ...]
    reason: FactReason | None

    def amounts(self) -> dict[str, Decimal]:
        return dict(self.entries)


@dataclass(frozen=True, slots=True)
class ParsedRate:
    currency: str
    rate: ParsedValue[Decimal]
    reference_date: date | None


@dataclass(frozen=True, slots=True)
class InitialRow:
    row_key: str
    instrument_key: str
    name: str
    quantity: Decimal
    raw_price: Decimal
    currency: str
    quote_base_quantity: int
    reference_date: date | None
    target_percent: Decimal
    grid_mode: GridMode
    quantity_step: Decimal


@dataclass(frozen=True, slots=True)
class InitialState:
    report_currency: str
    as_of_date: date | None
    rows: tuple[InitialRow, ...]
    cash_balances: tuple[tuple[str, Decimal], ...]
    contributions: tuple[tuple[str, Decimal], ...]
    valuation_rates: tuple[ParsedRate, ...]


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    report_currency: ParsedValue[str]
    as_of_date: date | None
    rows: tuple[ParsedRow, ...]
    cash: ParsedMoneyVector
    contributions: ParsedMoneyVector
    rates: tuple[ParsedRate, ...]
    currencies: tuple[str, ...]
    currency_domain_valid: bool
    row_identity_valid: bool
    target_total: ParsedValue[Decimal]
    targets_valid: bool
    issues: tuple[PacAnalyzeIssue, ...]
    normalized: InitialState | None

    def rate_map(self) -> dict[str, ParsedValue[Decimal]]:
        return {item.currency: item.rate for item in self.rates}


@dataclass(frozen=True, slots=True)
class InitialRowEvaluation:
    native_value: ParsedValue[Decimal]
    reporting_value: ParsedValue[Decimal]


@dataclass(frozen=True, slots=True)
class InitialEvaluation:
    rows: tuple[InitialRowEvaluation, ...]
    invested: ParsedValue[Decimal]
    existing_cash: ParsedValue[Decimal]
    contributions: ParsedValue[Decimal]
    combined_cash: ParsedValue[Decimal]
    gap_numerators: tuple[Decimal, ...] | None
    max_gap_numerator: Decimal | None
    squared_gap_numerator: Decimal | None


def check_budget(checkpoint: Checkpoint | None) -> None:
    if checkpoint is not None:
        checkpoint()


def unavailable_reason(values: list[ParsedValue] | tuple[ParsedValue, ...]) -> FactReason | None:
    reasons = {item.reason for item in values if not item.available}
    for reason in ("input_invalid", "outside_p1_domain", "input_missing", "dependency_unavailable"):
        if reason in reasons:
            return reason
    return "dependency_unavailable" if reasons else None
