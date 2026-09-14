"""Strict P1 contracts for PAC allocation and portfolio rebalancing analysis."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Union

from pydantic import AfterValidator, ConfigDict, Field, StringConstraints, TypeAdapter

from backend.app.schemas.common import Currency, StrictModel

P1_MAX_ROWS = 32
P1_MAX_CURRENCIES = 4
P1_MAX_ISSUES = 512
P1_MAX_INFO_ISSUES = 80
P1_MAX_NATIVE_AMOUNT_CHARS = 52
P1_RESULT_BYTES = 256 * 1024

_DECIMAL = r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$"
_NONNEGATIVE = r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$"
_POSITIVE = r"^(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)$"
_ISO_DATE = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"


def _unicode_scalar_text(value: str) -> str:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError("Text must contain Unicode scalar values")
    return value


def _calendar_date(value: str) -> str:
    date.fromisoformat(value)
    return value


def _unique_indices(value: list[int]) -> list[int]:
    if len(value) != len(set(value)):
        raise ValueError("Related indices must be unique")
    return value


class AllocationStrictModel(StrictModel):
    model_config = ConfigDict(strict=True, frozen=True, revalidate_instances="always")


RowKey = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=256, pattern=r"^[!-~]+$")]
InstrumentKey = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128, pattern=r"^[!-~]+$")]
RowName = Annotated[str, StringConstraints(strict=True, max_length=128), AfterValidator(_unicode_scalar_text)]
DraftDecimal = Annotated[str, StringConstraints(strict=True, max_length=64), AfterValidator(_unicode_scalar_text)]
DraftCurrency = Annotated[str, StringConstraints(strict=True, max_length=8), AfterValidator(_unicode_scalar_text)]
DraftDate = Annotated[str, StringConstraints(strict=True, max_length=10), AfterValidator(_unicode_scalar_text)]
CurrencyCode = Annotated[str, StringConstraints(strict=True, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"), AfterValidator(Currency.validate_code)]
ReferenceDate = Annotated[str, StringConstraints(strict=True, min_length=10, max_length=10, pattern=_ISO_DATE), AfterValidator(_calendar_date)]
CanonicalScalar = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=26, pattern=_DECIMAL)]
NativeAmount = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=P1_MAX_NATIVE_AMOUNT_CHARS, pattern=_DECIMAL)]
ReportingAmount = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=80, pattern=_DECIMAL)]
CombinedAmount = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=28, pattern=_DECIMAL)]
RatioNumerator = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=96, pattern=_DECIMAL)]
RatioDenominator = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=80, pattern=_POSITIVE)]
SquaredNumerator = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=192, pattern=_NONNEGATIVE)]
SquaredDenominator = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=160, pattern=_POSITIVE)]
RatioApproximation = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=36, pattern=_DECIMAL)]
QuoteBaseQuantity = Annotated[int, Field(strict=True, gt=0)]
SourceIndex = Annotated[int, Field(strict=True, ge=0, le=P1_MAX_ROWS - 1)]
GridMode = Literal["whole", "fractional"]


class AllocationBuyGridInput(AllocationStrictModel):
    mode: GridMode | None = Field(None, description="Rule for future purchases only. Current inventory is never rounded.")
    quantity_step: DraftDecimal | None = Field(None, description="Positive quantity increment; whole mode requires an integer. It is not a monetary step.")


class PacAssetInput(AllocationStrictModel):
    instrument_key: InstrumentKey = Field(description="Canonical instrument identity. Equal display names never merge different instruments.")
    name: RowName | None = Field(None, description="Display label only; it has no identity semantics.")
    buy_grid: AllocationBuyGridInput | None = Field(None, description="Optional future-purchase constraint. P1 allocation does not quantize its monetary result.")


class RebalanceQuoteInput(AllocationStrictModel):
    raw_price: DraftDecimal | None = Field(None, description="Native-currency price per quote_base_quantity units. A raw draft string, never a float.")
    currency: DraftCurrency | None = Field(None, description="Native ISO 4217 quote currency, not the reporting currency.")
    quote_base_quantity: Annotated[int, Field(strict=True)] | None = Field(None, description="Positive integer units represented by the raw quote.")
    reference_date: DraftDate | None = Field(None, description="Optional observation date. Missing dates are reported, never replaced by today.")


class RebalanceHoldingInput(AllocationStrictModel):
    row_key: RowKey = Field(description="Stable opaque custody identity. Broker names are never parsed.")
    instrument_key: InstrumentKey = Field(description="Canonical instrument identity used to aggregate custody contexts.")
    name: RowName | None = Field(None, description="Display label only; equal labels do not imply equal instruments.")
    quantity: DraftDecimal | None = Field(None, description="Exact current custody quantity. Existing inventory is never rounded.")
    quote: RebalanceQuoteInput | None = Field(None, description="Explicit native reference quote. No provider or database lookup occurs.")
    buy_grid: AllocationBuyGridInput | None = Field(None, description="Optional future-purchase constraint. P1 rebalancing analysis does not create orders.")


class AllocationTargetInput(AllocationStrictModel):
    instrument_key: InstrumentKey
    target_percent: DraftDecimal | None = Field(None, description="Exact target percentage from 0 to 100. The complete canonical vector must total exactly 100.")


class AllocationMoneyInput(AllocationStrictModel):
    currency: DraftCurrency | None = None
    amount: DraftDecimal | None = Field(None, description="Exact native amount. Zero is known zero; null or blank is missing, not zero.")


class AllocationContributionInput(AllocationStrictModel):
    currency: DraftCurrency | None = None
    amount: DraftDecimal | None = Field(None, description="Exact native contribution, separate from existing cash.")
    monetary_step: DraftDecimal | None = Field(None, description="Exact positive monetary increment. The contribution must be an exact multiple.")


class AllocationValuationRateInput(AllocationStrictModel):
    currency: DraftCurrency | None = None
    rate_to_report: DraftDecimal | None = Field(None, description="Reporting-currency value of one native unit. Valuation only; it never represents an FX transfer.")
    reference_date: DraftDate | None = Field(None, description="Optional reference observation date; no wall-clock default.")


class _AllocationAnalyzeInput(AllocationStrictModel):
    operation: Literal["analyze"]
    report_currency: DraftCurrency | None = Field(None, description="ISO 4217 reporting currency.")
    as_of_date: DraftDate | None = Field(None, description="Optional scenario date; observations may not be later. Never inferred from the clock.")
    targets: Annotated[list[AllocationTargetInput], Field(max_length=P1_MAX_ROWS)] = Field(default_factory=list)
    cash_balances: Annotated[list[AllocationMoneyInput], Field(max_length=P1_MAX_CURRENCIES)] | None = Field(
        None,
        description="Closed native existing-cash vector, one entry per currency. Empty means intentionally none; null means not supplied.",
    )
    contributions: Annotated[list[AllocationContributionInput], Field(max_length=P1_MAX_ROWS)] | None = Field(
        None,
        description="Closed native contribution vector, separate from existing cash. Empty means intentionally none; null means not supplied.",
    )
    valuation_rates: Annotated[list[AllocationValuationRateInput], Field(max_length=P1_MAX_CURRENCIES)] = Field(
        default_factory=list,
        description="Explicit valuation references. Reporting identity is 1; missing foreign rates never default to 1.",
    )


class PacAnalyzeInput(_AllocationAnalyzeInput):
    assets: Annotated[list[PacAssetInput], Field(max_length=P1_MAX_ROWS)] = Field(
        default_factory=list,
        description="Canonical instruments receiving the investable budget. Prices and holdings are not required by this P1 calculation.",
    )


class RebalanceAnalyzeInput(_AllocationAnalyzeInput):
    holdings: Annotated[list[RebalanceHoldingInput], Field(max_length=P1_MAX_ROWS)] = Field(
        default_factory=list,
        description="Current custody contexts. Contexts sharing instrument_key are aggregated before target comparison.",
    )


PathField = Literal[
    "report_currency",
    "as_of_date",
    "assets",
    "holdings",
    "targets",
    "row_key",
    "instrument_key",
    "name",
    "quantity",
    "quote",
    "raw_price",
    "currency",
    "quote_base_quantity",
    "reference_date",
    "buy_grid",
    "mode",
    "quantity_step",
    "target_percent",
    "cash_balances",
    "contributions",
    "valuation_rates",
    "amount",
    "monetary_step",
    "rate_to_report",
]
IssuePath = Annotated[list[Union[PathField, SourceIndex]], Field(max_length=4)]
IssueUnit = Literal["quantity", "quote", "rate", "percent", "native_amount"]
FactReason = Literal["input_missing", "input_invalid", "outside_p1_domain", "dependency_unavailable", "zero_invested_value"]
MissingCode = Literal[
    "assets_required",
    "holdings_required",
    "targets_required",
    "target_required",
    "field_required",
    "incomplete_decimal",
    "quote_required",
    "cash_vector_required",
    "valuation_rate_required",
]
InvalidCode = Literal[
    "invalid_decimal_syntax",
    "invalid_currency",
    "invalid_date",
    "reference_after_asof",
    "nonpositive_price",
    "nonpositive_fx_rate",
    "invalid_quote_basis",
    "target_percent_out_of_range",
    "target_total_not_100",
    "nonpositive_quantity_step",
    "noninteger_whole_step",
    "negative_contribution",
    "nonpositive_monetary_step",
    "contribution_not_multiple_of_monetary_step",
    "duplicate_row_key",
    "duplicate_instrument",
    "duplicate_target_instrument",
    "target_instrument_not_selected",
    "identity_rate_mismatch",
    "duplicate_currency",
]
UnsupportedCode = Literal["numeric_domain_exceeded", "currency_domain_exceeded", "short_inventory_unsupported", "initial_debt_unsupported"]
InfoCode = Literal["inventory_off_buy_grid", "reference_date_unspecified", "unused_valuation_reference", "identity_rate_redundant"]


class AllocationIssueParams(AllocationStrictModel):
    currency: CurrencyCode | None = None
    vector: Literal["cash_balances", "contributions", "valuation_rates"] | None = None
    instrument_key: InstrumentKey | None = None
    limit: Annotated[int, Field(strict=True, ge=0, le=512)] | None = None
    unit: IssueUnit | None = None


class _IssueBase(AllocationStrictModel):
    path: IssuePath
    related_indices: Annotated[list[SourceIndex], Field(max_length=P1_MAX_ROWS), AfterValidator(_unique_indices)]
    params: AllocationIssueParams


class AllocationMissingIssue(_IssueBase):
    kind: Literal["missing"]
    code: MissingCode


class AllocationInvalidIssue(_IssueBase):
    kind: Literal["invalid"]
    code: InvalidCode


class AllocationUnsupportedIssue(_IssueBase):
    kind: Literal["unsupported"]
    code: UnsupportedCode


class AllocationInfoIssue(_IssueBase):
    kind: Literal["info"]
    code: InfoCode


type AllocationIssue = Annotated[
    Union[AllocationMissingIssue, AllocationInvalidIssue, AllocationUnsupportedIssue, AllocationInfoIssue],
    Field(discriminator="kind"),
]


class AvailableFact[T](AllocationStrictModel):
    availability: Literal["available"]
    value: T
    reason_codes: Annotated[list[FactReason], Field(max_length=0)]


class UnavailableFact(AllocationStrictModel):
    availability: Literal["unavailable"]
    value: None
    reason_codes: Annotated[list[FactReason], Field(min_length=1, max_length=1)]


type Fact[T] = Annotated[Union[AvailableFact[T], UnavailableFact], Field(discriminator="availability")]


class NativeMoney(AllocationStrictModel):
    currency: CurrencyCode
    amount: NativeAmount


class ReportingMoney(AllocationStrictModel):
    currency: CurrencyCode
    amount: ReportingAmount


class _RatioBase(AllocationStrictModel):
    approximation: RatioApproximation
    approximation_decimal_places: Literal[28]
    approximation_exact: bool


class PercentRatio(_RatioBase):
    numerator: RatioNumerator
    denominator: RatioDenominator
    unit: Literal["percent"]


class GapRatio(_RatioBase):
    numerator: RatioNumerator
    denominator: RatioDenominator
    unit: Literal["percentage_points"]


class SquaredGapRatio(_RatioBase):
    numerator: SquaredNumerator
    denominator: SquaredDenominator
    unit: Literal["percentage_points_squared"]


class CashPoolFacts(AllocationStrictModel):
    currency: CurrencyCode
    existing_amount: CanonicalScalar
    contribution_amount: CanonicalScalar
    combined_amount: CombinedAmount
    existing_reporting: Fact[ReportingMoney]
    contribution_reporting: Fact[ReportingMoney]
    combined_reporting: Fact[ReportingMoney]


CashPoolList = Annotated[list[CashPoolFacts], Field(max_length=P1_MAX_CURRENCIES)]


class PacAllocationFacts(AllocationStrictModel):
    target_index: SourceIndex
    instrument_key: InstrumentKey
    name: RowName | None
    target_percent: Fact[CanonicalScalar]
    ideal_allocation_reporting: Fact[ReportingMoney] = Field(description="Theoretical share of reporting-currency budget. Not an order amount or native-cash feasibility claim.")


class RebalanceHoldingFacts(AllocationStrictModel):
    holding_index: SourceIndex
    row_key: RowKey
    instrument_key: InstrumentKey
    name: RowName | None
    quantity: Fact[CanonicalScalar]
    current_value_native: Fact[NativeMoney]
    current_value_reporting: Fact[ReportingMoney]


class RebalanceInstrumentFacts(AllocationStrictModel):
    target_index: SourceIndex
    instrument_key: InstrumentKey
    name: RowName | None
    custody_context_count: Annotated[int, Field(strict=True, ge=0, le=P1_MAX_ROWS)]
    current_value_reporting: Fact[ReportingMoney]
    current_weight_percent: Fact[PercentRatio]
    target_percent: Fact[CanonicalScalar]
    target_value_reporting: Fact[ReportingMoney]
    value_gap_to_target_reporting: Fact[ReportingMoney] = Field(description="Signed target value minus current value. It is not a buy or sell instruction.")
    gap_to_target_pp: Fact[GapRatio]


class PacTotals(AllocationStrictModel):
    existing_cash_reporting: Fact[ReportingMoney]
    contributions_reporting: Fact[ReportingMoney]
    investable_budget_reporting: Fact[ReportingMoney]
    target_total_percent: Fact[CanonicalScalar]


class RebalanceTotals(AllocationStrictModel):
    current_invested_reporting: Fact[ReportingMoney]
    existing_cash_reporting: Fact[ReportingMoney]
    contributions_reporting: Fact[ReportingMoney]
    cash_plus_contributions_reporting: Fact[ReportingMoney]
    target_total_percent: Fact[CanonicalScalar]
    max_abs_gap_pp: Fact[GapRatio]
    squared_gap_pp2: Fact[SquaredGapRatio]


class NormalizedBuyGrid(AllocationStrictModel):
    mode: GridMode
    quantity_step: CanonicalScalar


class NormalizedPacAsset(AllocationStrictModel):
    instrument_key: InstrumentKey
    name: Annotated[RowName, Field(min_length=1)]
    buy_grid: NormalizedBuyGrid | None


class NormalizedHolding(AllocationStrictModel):
    row_key: RowKey
    instrument_key: InstrumentKey
    name: Annotated[RowName, Field(min_length=1)]
    quantity: CanonicalScalar
    raw_price: CanonicalScalar
    currency: CurrencyCode
    quote_base_quantity: QuoteBaseQuantity
    reference_date: ReferenceDate | None
    buy_grid: NormalizedBuyGrid | None


class NormalizedTarget(AllocationStrictModel):
    instrument_key: InstrumentKey
    target_percent: CanonicalScalar


class NormalizedMoney(AllocationStrictModel):
    currency: CurrencyCode
    amount: CanonicalScalar


class NormalizedContribution(AllocationStrictModel):
    currency: CurrencyCode
    amount: CanonicalScalar
    monetary_step: CanonicalScalar


class NormalizedValuationRate(AllocationStrictModel):
    currency: CurrencyCode
    rate_to_report: CanonicalScalar
    reference_date: ReferenceDate | None


class _NormalizedScenario(AllocationStrictModel):
    report_currency: CurrencyCode
    as_of_date: ReferenceDate | None
    targets: Annotated[list[NormalizedTarget], Field(min_length=1, max_length=P1_MAX_ROWS)]
    cash_balances: Annotated[list[NormalizedMoney], Field(max_length=P1_MAX_CURRENCIES)]
    contributions: Annotated[list[NormalizedContribution], Field(max_length=P1_MAX_ROWS)]
    valuation_rates: Annotated[list[NormalizedValuationRate], Field(max_length=P1_MAX_CURRENCIES + 1)]


class PacNormalizedScenario(_NormalizedScenario):
    assets: Annotated[list[NormalizedPacAsset], Field(min_length=1, max_length=P1_MAX_ROWS)]


class RebalanceNormalizedScenario(_NormalizedScenario):
    holdings: Annotated[list[NormalizedHolding], Field(min_length=1, max_length=P1_MAX_ROWS)]


class _PacOutputBase(AllocationStrictModel):
    operation: Literal["analyze"]
    result_kind: Literal["pac_budget_analysis"]
    numeric_policy_id: Literal["pac-budget-allocation-v1"]
    allocations: Annotated[list[PacAllocationFacts], Field(max_length=P1_MAX_ROWS)]
    cash_pools: Fact[CashPoolList]
    totals: PacTotals


class PacAnalyzeReady(_PacOutputBase):
    availability: Literal["ready"]
    normalized: PacNormalizedScenario
    issues: Annotated[list[AllocationInfoIssue], Field(max_length=P1_MAX_INFO_ISSUES)]


class PacAnalyzeNeedsInput(_PacOutputBase):
    availability: Literal["needs_input"]
    normalized: None
    issues: Annotated[list[AllocationIssue], Field(max_length=P1_MAX_ISSUES)]


class PacAnalyzeInvalid(_PacOutputBase):
    availability: Literal["invalid"]
    normalized: None
    issues: Annotated[list[AllocationIssue], Field(max_length=P1_MAX_ISSUES)]


class PacAnalyzeUnsupported(_PacOutputBase):
    availability: Literal["unsupported"]
    normalized: None
    issues: Annotated[list[AllocationIssue], Field(max_length=P1_MAX_ISSUES)]


type PacAnalyzeOutput = Annotated[
    Union[PacAnalyzeReady, PacAnalyzeNeedsInput, PacAnalyzeInvalid, PacAnalyzeUnsupported],
    Field(discriminator="availability"),
]


class _RebalanceOutputBase(AllocationStrictModel):
    operation: Literal["analyze"]
    result_kind: Literal["portfolio_rebalancing_analysis"]
    numeric_policy_id: Literal["portfolio-rebalancing-v1"]
    holdings: Annotated[list[RebalanceHoldingFacts], Field(max_length=P1_MAX_ROWS)]
    instruments: Annotated[list[RebalanceInstrumentFacts], Field(max_length=P1_MAX_ROWS)]
    cash_pools: Fact[CashPoolList]
    totals: RebalanceTotals


class RebalanceAnalyzeReady(_RebalanceOutputBase):
    availability: Literal["ready"]
    normalized: RebalanceNormalizedScenario
    issues: Annotated[list[AllocationInfoIssue], Field(max_length=P1_MAX_INFO_ISSUES)]


class RebalanceAnalyzeNeedsInput(_RebalanceOutputBase):
    availability: Literal["needs_input"]
    normalized: None
    issues: Annotated[list[AllocationIssue], Field(max_length=P1_MAX_ISSUES)]


class RebalanceAnalyzeInvalid(_RebalanceOutputBase):
    availability: Literal["invalid"]
    normalized: None
    issues: Annotated[list[AllocationIssue], Field(max_length=P1_MAX_ISSUES)]


class RebalanceAnalyzeUnsupported(_RebalanceOutputBase):
    availability: Literal["unsupported"]
    normalized: None
    issues: Annotated[list[AllocationIssue], Field(max_length=P1_MAX_ISSUES)]


type RebalanceAnalyzeOutput = Annotated[
    Union[RebalanceAnalyzeReady, RebalanceAnalyzeNeedsInput, RebalanceAnalyzeInvalid, RebalanceAnalyzeUnsupported],
    Field(discriminator="availability"),
]

PAC_ANALYZE_INPUT_ADAPTER = TypeAdapter(PacAnalyzeInput)
PAC_ANALYZE_OUTPUT_ADAPTER = TypeAdapter(PacAnalyzeOutput)
REBALANCE_ANALYZE_INPUT_ADAPTER = TypeAdapter(RebalanceAnalyzeInput)
REBALANCE_ANALYZE_OUTPUT_ADAPTER = TypeAdapter(RebalanceAnalyzeOutput)
