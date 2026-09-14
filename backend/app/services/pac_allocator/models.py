"""Immutable numeric state shared by allocation normalization and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

from backend.app.schemas.pac_allocator import AllocationIssue, FactReason, GridMode

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
class ParsedGrid:
    mode: GridMode | None
    step: ParsedValue[Decimal]


@dataclass(frozen=True, slots=True)
class ParsedAsset:
    instrument_key: str
    name: str | None
    grid: ParsedGrid | None


@dataclass(frozen=True, slots=True)
class ParsedQuote:
    price: ParsedValue[Decimal]
    currency: ParsedValue[str]
    basis: ParsedValue[int]
    reference_date: date | None
    date_valid: bool


@dataclass(frozen=True, slots=True)
class ParsedHolding:
    row_key: str
    instrument_key: str
    name: str | None
    quantity: ParsedValue[Decimal]
    quote: ParsedQuote
    grid: ParsedGrid | None


@dataclass(frozen=True, slots=True)
class ParsedTarget:
    instrument_key: str
    percent: ParsedValue[Decimal]


@dataclass(frozen=True, slots=True)
class ParsedMoneyVector:
    entries: tuple[tuple[str, Decimal], ...]
    reason: FactReason | None

    def amount_entries(self) -> tuple[tuple[str, Decimal], ...]:
        return self.entries

    def amounts(self) -> dict[str, Decimal]:
        return dict(self.entries)


@dataclass(frozen=True, slots=True)
class ParsedContributionVector:
    entries: tuple[tuple[str, Decimal, Decimal], ...]
    reason: FactReason | None

    def amount_entries(self) -> tuple[tuple[str, Decimal], ...]:
        return tuple((currency, amount) for currency, amount, _monetary_step in self.entries)

    def amounts(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for currency, amount in self.amount_entries():
            totals[currency] = totals.get(currency, Decimal(0)) + amount
        return totals


@dataclass(frozen=True, slots=True)
class ParsedRate:
    currency: str
    rate: ParsedValue[Decimal]
    reference_date: date | None


@dataclass(frozen=True, slots=True)
class PacAsset:
    instrument_key: str
    name: str
    grid_mode: GridMode | None
    quantity_step: Decimal | None


@dataclass(frozen=True, slots=True)
class Holding:
    row_key: str
    instrument_key: str
    name: str
    quantity: Decimal
    raw_price: Decimal
    currency: str
    quote_base_quantity: int
    reference_date: date | None
    grid_mode: GridMode | None
    quantity_step: Decimal | None


@dataclass(frozen=True, slots=True)
class Target:
    instrument_key: str
    percent: Decimal


@dataclass(frozen=True, slots=True)
class PacScenario:
    report_currency: str
    as_of_date: date | None
    assets: tuple[PacAsset, ...]
    targets: tuple[Target, ...]
    cash_balances: tuple[tuple[str, Decimal], ...]
    contributions: tuple[tuple[str, Decimal, Decimal], ...]
    valuation_rates: tuple[ParsedRate, ...]


@dataclass(frozen=True, slots=True)
class RebalanceScenario:
    report_currency: str
    as_of_date: date | None
    holdings: tuple[Holding, ...]
    targets: tuple[Target, ...]
    cash_balances: tuple[tuple[str, Decimal], ...]
    contributions: tuple[tuple[str, Decimal, Decimal], ...]
    valuation_rates: tuple[ParsedRate, ...]


@dataclass(frozen=True, slots=True)
class PacNormalizationResult:
    report_currency: ParsedValue[str]
    as_of_date: date | None
    assets: tuple[ParsedAsset, ...]
    targets: tuple[ParsedTarget, ...]
    cash: ParsedMoneyVector
    contributions: ParsedContributionVector
    rates: tuple[ParsedRate, ...]
    currencies: tuple[str, ...]
    currency_domain_valid: bool
    asset_identity_valid: bool
    target_identity_valid: bool
    target_total: ParsedValue[Decimal]
    targets_valid: bool
    issues: tuple[AllocationIssue, ...]
    normalized: PacScenario | None

    def rate_map(self) -> dict[str, ParsedValue[Decimal]]:
        return {item.currency: item.rate for item in self.rates}

    def target_map(self) -> dict[str, ParsedValue[Decimal]]:
        return {item.instrument_key: item.percent for item in self.targets}


@dataclass(frozen=True, slots=True)
class RebalanceNormalizationResult:
    report_currency: ParsedValue[str]
    as_of_date: date | None
    holdings: tuple[ParsedHolding, ...]
    targets: tuple[ParsedTarget, ...]
    cash: ParsedMoneyVector
    contributions: ParsedContributionVector
    rates: tuple[ParsedRate, ...]
    currencies: tuple[str, ...]
    currency_domain_valid: bool
    row_identity_valid: bool
    target_identity_valid: bool
    target_total: ParsedValue[Decimal]
    targets_valid: bool
    issues: tuple[AllocationIssue, ...]
    normalized: RebalanceScenario | None

    def rate_map(self) -> dict[str, ParsedValue[Decimal]]:
        return {item.currency: item.rate for item in self.rates}

    def target_map(self) -> dict[str, ParsedValue[Decimal]]:
        return {item.instrument_key: item.percent for item in self.targets}


type NormalizationResult = PacNormalizationResult | RebalanceNormalizationResult


@dataclass(frozen=True, slots=True)
class MoneyEvaluation:
    existing_cash: ParsedValue[Decimal]
    contributions: ParsedValue[Decimal]
    combined_cash: ParsedValue[Decimal]


@dataclass(frozen=True, slots=True)
class PacEvaluation:
    money: MoneyEvaluation
    allocations: tuple[ParsedValue[Decimal], ...]


@dataclass(frozen=True, slots=True)
class HoldingEvaluation:
    native_value: ParsedValue[Decimal]
    reporting_value: ParsedValue[Decimal]


@dataclass(frozen=True, slots=True)
class InstrumentEvaluation:
    instrument_key: str
    current_reporting: ParsedValue[Decimal]
    target_value_reporting: ParsedValue[Decimal]
    value_gap_reporting: ParsedValue[Decimal]
    gap_numerator: Decimal | None


@dataclass(frozen=True, slots=True)
class RebalanceEvaluation:
    holdings: tuple[HoldingEvaluation, ...]
    instruments: tuple[InstrumentEvaluation, ...]
    invested: ParsedValue[Decimal]
    money: MoneyEvaluation
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
