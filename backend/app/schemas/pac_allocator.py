"""Strict P1 analysis and additive v2 planning contracts for PAC/Rebalancer."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction
from math import gcd
from typing import Annotated, Literal, Union

from pydantic import AfterValidator, ConfigDict, Field, StringConstraints, TypeAdapter, model_validator

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


# =============================================================================
# V2 PLANNER CONTRACTS — additive until the CP5 P1 migration
# =============================================================================

PAC_PLANNER_CONTRACT_VERSION = "2.0.0"
REBALANCER_PLANNER_CONTRACT_VERSION = "2.0.0"

_PLANNER_FIXED_DECIMAL = r"^(?:0(?:\.[0-9]+)?|[1-9][0-9]*(?:\.[0-9]+)?|-(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*))$"
_PLANNER_INTEGER = r"^(?:0|[1-9][0-9]*|-[1-9][0-9]*)$"
_PLANNER_POSITIVE_INTEGER = r"^[1-9][0-9]*$"
_PLANNER_ID = r"^[A-Za-z0-9][A-Za-z0-9._:@/-]*$"
_PLANNER_CODE = r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$"
_PLANNER_MESSAGE_KEY = r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"
_UTC_TIMESTAMP = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
_JS_SAFE_INTEGER = 9_007_199_254_740_991


def _planner_fixed_decimal(value: str) -> str:
    parsed = Decimal(value)
    if not parsed.is_finite():
        raise ValueError("Decimal text must be finite")
    if parsed.is_zero() and value.startswith("-"):
        raise ValueError("Decimal text must not encode negative zero")
    return value


def _planner_nonnegative_decimal(value: str) -> str:
    if Decimal(value) < 0:
        raise ValueError("Decimal text must be nonnegative")
    return value


def _planner_positive_decimal(value: str) -> str:
    if Decimal(value) <= 0:
        raise ValueError("Decimal text must be positive")
    return value


def _planner_positive_whole_decimal(value: str) -> str:
    parsed = Decimal(value)
    if parsed <= 0 or parsed != parsed.to_integral_value():
        raise ValueError("Quantity step must be a positive whole number")
    return value


def _planner_integer_text(value: str) -> str:
    if Decimal(value).is_zero() and value.startswith("-"):
        raise ValueError("Integer text must not encode negative zero")
    return value


def _planner_utc_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("Timestamp must be UTC")
    return value


def _require_unique(values: list[object], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def _collect_currency_codes(value: object) -> set[str]:
    currencies: set[str] = set()

    def visit(node: object) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if key in {"currency", "currency_code", "source_currency", "destination_currency"} and isinstance(child, str):
                    currencies.add(child)
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return currencies


PlannerId = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128, pattern=_PLANNER_ID)]
PlannerRef = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=256, pattern=_PLANNER_ID)]
PlannerCode = Annotated[str, StringConstraints(strict=True, min_length=3, max_length=96, pattern=_PLANNER_CODE)]
PlannerIssueCode = Literal[
    "allocation.asset_inactive_not_buyable",
    "allocation.asset_type_missing",
    "allocation.broker_execution_profile_unsupported",
    "allocation.broker_inactive",
    "allocation.capacity_unsupported",
    "allocation.cash_selection_invalid",
    "allocation.classification_geography_missing",
    "allocation.classification_invalid",
    "allocation.classification_sector_missing",
    "allocation.coefficient_envelope_unsupported",
    "allocation.currency_minor_unit_nonpositive",
    "allocation.currency_mismatch",
    "allocation.currency_spec_missing",
    "allocation.deployment_omitted",
    "allocation.duplicate_id",
    "allocation.dynamic_fee_unsupported",
    "allocation.economic_share_out_of_range",
    "allocation.execution_margin_missing",
    "allocation.execution_margin_rate_out_of_range",
    "allocation.exposure_weight_out_of_range",
    "allocation.fee_floor_exceeds_cap",
    "allocation.fee_rate_out_of_range",
    "allocation.fee_schedule_missing",
    "allocation.fiscal_currency_missing",
    "allocation.funding_cap_negative",
    "allocation.fx_buffer_rate_out_of_range",
    "allocation.fx_cycle_invalid",
    "allocation.fx_multi_hop_unsupported",
    "allocation.fx_quote_missing",
    "allocation.fx_spread_rate_out_of_range",
    "allocation.identity_fx_quote_not_allowed",
    "allocation.identity_valuation_rate_not_allowed",
    "allocation.invalid_quote_basis",
    "allocation.negative_cash_unsupported",
    "allocation.negative_contribution",
    "allocation.negative_fee_amount",
    "allocation.negative_fx_fee",
    "allocation.negative_inventory_unsupported",
    "allocation.no_additional_buy_feasible",
    "allocation.no_positive_order_fundable",
    "allocation.no_selected_funding",
    "allocation.nonpositive_fx_rate",
    "allocation.nonpositive_fx_source_step",
    "allocation.nonpositive_order_amount_step",
    "allocation.nonpositive_price",
    "allocation.nonpositive_quantity_step",
    "allocation.nonpositive_valuation_rate",
    "allocation.order_amount_step_missing",
    "allocation.order_cap_nonpositive",
    "allocation.order_minimum_exceeds_cap",
    "allocation.order_minimum_negative",
    "allocation.planning_quantity_negative",
    "allocation.price_date_missing",
    "allocation.price_missing",
    "allocation.price_order_invalid",
    "allocation.provenance_not_found",
    "allocation.provenance_stale_confirmed",
    "allocation.quote_base_quantity_missing",
    "allocation.reference_not_found",
    "allocation.required_buy_sell_conflict",
    "allocation.required_min_notional_unfunded",
    "allocation.route_priority_negative",
    "allocation.saved_fx_invalid",
    "allocation.saved_fx_missing",
    "allocation.solver_limit_no_incumbent",
    "allocation.stale_age_negative",
    "allocation.stale_observation_not_accepted",
    "allocation.target_total_not_one",
    "allocation.target_weight_missing",
    "allocation.target_weight_out_of_range",
    "allocation.tax_netting_unsupported",
    "allocation.valuation_currency_missing",
    "allocation.wac_fx_missing",
    "allocation.wac_missing",
    "allocation.zero_selected_funding",
    "pac_allocator.initial_holding_forbidden",
    "pac_allocator.sell_forbidden",
    "portfolio_rebalancer.baseline_incumbent_missing",
    "portfolio_rebalancer.carried_loss_negative",
    "portfolio_rebalancer.cost_basis_negative",
    "portfolio_rebalancer.holdings_missing",
    "portfolio_rebalancer.nonpositive_current_portfolio",
    "portfolio_rebalancer.sell_fee_missing",
    "portfolio_rebalancer.sell_inventory_exceeded",
    "portfolio_rebalancer.sell_irreducibility_unresolved",
    "portfolio_rebalancer.sell_to_idle_forbidden",
    "portfolio_rebalancer.tax_rate_missing",
    "portfolio_rebalancer.tax_rate_out_of_range",
    "portfolio_rebalancer.withholding_missing",
]
FundingActionReasonCode = Literal["allocation.fund_declared_orders"]
DeploymentReasonCode = Literal[
    "allocation.deployment_omitted",
    "allocation.no_actions_selected",
    "allocation.no_additional_buy_feasible",
    "allocation.primary_is_deployment",
]
NotProvenReasonCode = Literal[
    "allocation.exact_proof_not_established",
    "portfolio_rebalancer.sell_irreducibility_unresolved",
]
SolverNotRunReasonCode = Literal["allocation.solver_not_required"]
PlannerMessageKey = Annotated[str, StringConstraints(strict=True, min_length=3, max_length=160, pattern=_PLANNER_MESSAGE_KEY)]
PlannerLabel = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128), AfterValidator(_unicode_scalar_text)]
PlannerLongLabel = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=256), AfterValidator(_unicode_scalar_text)]
PlannerTimestamp = Annotated[
    str,
    StringConstraints(strict=True, min_length=20, max_length=27, pattern=_UTC_TIMESTAMP),
    AfterValidator(_planner_utc_timestamp),
]
PlannerFixedDecimal = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=96, pattern=_PLANNER_FIXED_DECIMAL),
    AfterValidator(_planner_fixed_decimal),
]
PlannerNonNegativeDecimal = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=96, pattern=_NONNEGATIVE),
    AfterValidator(_planner_nonnegative_decimal),
]
PlannerPositiveDecimal = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=96, pattern=_POSITIVE),
    AfterValidator(_planner_positive_decimal),
]
PlannerPositiveWholeDecimal = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=96, pattern=_PLANNER_POSITIVE_INTEGER),
    AfterValidator(_planner_positive_whole_decimal),
]
PlannerIntegerText = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=192, pattern=_PLANNER_INTEGER),
    AfterValidator(_planner_integer_text),
]
PlannerPositiveIntegerText = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=192, pattern=_PLANNER_POSITIVE_INTEGER),
]
PlannerSafeInteger = Annotated[int, Field(strict=True, ge=0, le=_JS_SAFE_INTEGER)]
PlannerPositiveInteger = Annotated[int, Field(strict=True, gt=0, le=_JS_SAFE_INTEGER)]
PlannerWireInteger = Annotated[int, Field(strict=True, ge=-_JS_SAFE_INTEGER, le=_JS_SAFE_INTEGER)]
QuantityUnit = Literal["asset_unit"]
OrderSide = Literal["buy", "sell"]


class PlannerSnapshotInput(AllocationStrictModel):
    snapshot_id: PlannerId
    draft_revision: PlannerSafeInteger
    captured_at: PlannerTimestamp


class CurrencySpec(AllocationStrictModel):
    """Backend-derived currency quantum; never silently defaulted by the worker."""

    currency: CurrencyCode
    minor_unit: PlannerFixedDecimal


class ManualProvenance(AllocationStrictModel):
    kind: Literal["manual"]
    provenance_id: PlannerId
    label: PlannerLabel
    entered_at: PlannerTimestamp


class DomainCopyProvenance(AllocationStrictModel):
    kind: Literal["domain_copy"]
    provenance_id: PlannerId
    domain: Literal["portfolio", "market_data", "broker", "fx", "wac"]
    source_ref: PlannerRef
    source_label: PlannerLabel | None
    captured_at: PlannerTimestamp


type PlannerProvenance = Annotated[
    Union[ManualProvenance, DomainCopyProvenance],
    Field(discriminator="kind"),
]


class FreshObservation(AllocationStrictModel):
    kind: Literal["fresh"]


class AcceptedStaleObservation(AllocationStrictModel):
    kind: Literal["stale"]
    age_days: PlannerWireInteger
    accepted: bool


type ObservationFreshness = Annotated[
    Union[FreshObservation, AcceptedStaleObservation],
    Field(discriminator="kind"),
]


class PlannerMoneyInput(AllocationStrictModel):
    amount: PlannerFixedDecimal
    currency: CurrencyCode


class PlannerNonNegativeMoneyInput(AllocationStrictModel):
    amount: PlannerNonNegativeDecimal
    currency: CurrencyCode


class PlannerPositiveMoneyInput(AllocationStrictModel):
    amount: PlannerPositiveDecimal
    currency: CurrencyCode


class PlannerValuationRateInput(AllocationStrictModel):
    """Operational nonidentity valuation fact; assembly filters source identity rows."""

    valuation_rate_id: PlannerId
    source_currency: CurrencyCode
    destination_currency: CurrencyCode = Field(description="Currency units received per one source-currency unit.")
    rate: PlannerFixedDecimal
    reference_date: ReferenceDate
    freshness: ObservationFreshness
    provenance_id: PlannerId


class ManualAssetIdentity(AllocationStrictModel):
    kind: Literal["manual_asset"]
    name: PlannerLabel
    ticker: PlannerLabel | None
    asset_class: PlannerCode


class DomainAssetIdentity(AllocationStrictModel):
    kind: Literal["domain_asset"]
    source_asset_id: PlannerRef
    name: PlannerLabel
    ticker: PlannerLabel | None
    asset_class: PlannerCode


type PlannerAssetIdentity = Annotated[
    Union[ManualAssetIdentity, DomainAssetIdentity],
    Field(discriminator="kind"),
]


class PlannerAssetQuoteInput(AllocationStrictModel):
    amount: PlannerFixedDecimal
    currency: CurrencyCode
    quote_base_quantity: PlannerFixedDecimal
    reference_date: ReferenceDate
    freshness: ObservationFreshness
    provenance_id: PlannerId


class PlannerExposureInput(AllocationStrictModel):
    dimension: Literal["asset_type", "sector", "geography"]
    category_id: PlannerId
    label: PlannerLabel
    weight: PlannerFixedDecimal
    provenance_id: PlannerId


class PlannerAssetInput(AllocationStrictModel):
    asset_id: PlannerId
    identity: PlannerAssetIdentity = Field(description="Nested identity assembled from the authorized flat source Asset row.")
    quote: PlannerAssetQuoteInput | None = Field(description="One complete nested Price fact or explicit absence; never a partial object built from null source fields.")
    exposures: list[PlannerExposureInput] = Field(description="Complete nested Classification facts assembled by the backend; the frontend performs no financial reconstruction.")


class ManualBrokerIdentity(AllocationStrictModel):
    kind: Literal["manual_broker"]
    name: PlannerLabel


class DomainBrokerIdentity(AllocationStrictModel):
    """Minimal persisted Broker facts; executable routes still require normalizer approval."""

    kind: Literal["domain_broker"]
    source_broker_id: PlannerRef
    name: PlannerLabel
    active: bool = Field(description="Persisted activity fact used to reject submitted executable routes to an inactive Broker.")


type PlannerBrokerIdentity = Annotated[
    Union[ManualBrokerIdentity, DomainBrokerIdentity],
    Field(discriminator="kind"),
]


class WholeQuantityCapability(AllocationStrictModel):
    kind: Literal["whole_quantity"]
    capability_id: PlannerId
    currency: CurrencyCode
    fx_mode: Literal["native_currency_required", "conversion_allowed"]
    quantity_unit: QuantityUnit
    quantity_step: PlannerFixedDecimal


class MonetaryAmountCapability(AllocationStrictModel):
    kind: Literal["monetary_amount"]
    capability_id: PlannerId
    currency: CurrencyCode
    fx_mode: Literal["native_currency_required", "conversion_allowed"]
    order_amount_step: PlannerMoneyInput


type BrokerOrderCapability = Annotated[
    Union[WholeQuantityCapability, MonetaryAmountCapability],
    Field(discriminator="kind"),
]


class NoFeeCap(AllocationStrictModel):
    kind: Literal["none"]


class AmountFeeCap(AllocationStrictModel):
    kind: Literal["amount"]
    amount: PlannerMoneyInput


type FeeCap = Annotated[Union[NoFeeCap, AmountFeeCap], Field(discriminator="kind")]


class BrokerFeeScheduleInput(AllocationStrictModel):
    fee_schedule_id: PlannerId
    capability_id: PlannerId
    side: OrderSide
    fixed_fee: PlannerMoneyInput
    rate: PlannerFixedDecimal
    variable_floor: PlannerMoneyInput
    variable_cap: FeeCap


class PlannerBrokerInput(AllocationStrictModel):
    broker_id: PlannerId
    identity: PlannerBrokerIdentity
    provenance_id: PlannerId
    capabilities: list[BrokerOrderCapability]
    fee_schedules: list[BrokerFeeScheduleInput]


class PlannerHoldingInput(AllocationStrictModel):
    holding_id: PlannerId
    asset_id: PlannerId
    broker_id: PlannerId
    custody_quantity: PlannerFixedDecimal = Field(description="Observed custody quantity; never recomputed from economic ownership.")
    economic_share: PlannerFixedDecimal
    planning_quantity: PlannerFixedDecimal = Field(description="Editable planning quantity proposed from source economic_quantity; it never rewrites custody_quantity.")
    quantity_unit: QuantityUnit
    provenance_id: PlannerId


class PlannerExistingCashInput(AllocationStrictModel):
    source_kind: Literal["local_broker_cash", "manual_cash"]
    cash_id: PlannerId
    broker_id: PlannerId
    available: PlannerMoneyInput
    selected: PlannerMoneyInput
    provenance_id: PlannerId


class PlannerContributionInput(AllocationStrictModel):
    contribution_id: PlannerId
    label: PlannerLabel
    amount: PlannerMoneyInput
    provenance_id: PlannerId


class ExistingCashFundingSourceRef(AllocationStrictModel):
    kind: Literal["existing_cash"]
    cash_id: PlannerId


class ContributionFundingSourceRef(AllocationStrictModel):
    kind: Literal["contribution"]
    contribution_id: PlannerId


type PlannerFundingSourceRef = Annotated[
    Union[ExistingCashFundingSourceRef, ContributionFundingSourceRef],
    Field(discriminator="kind"),
]


class PlannerFundingRouteInput(AllocationStrictModel):
    funding_route_id: PlannerId
    source: PlannerFundingSourceRef
    broker_id: PlannerId
    currency: CurrencyCode
    priority: PlannerWireInteger
    transfer_cap: PlannerMoneyInput
    provenance_id: PlannerId


class NoOrderMinimum(AllocationStrictModel):
    kind: Literal["none"]


class WholeQuantityMinimum(AllocationStrictModel):
    kind: Literal["whole_quantity"]
    quantity: PlannerFixedDecimal
    unit: QuantityUnit


class MonetaryAmountMinimum(AllocationStrictModel):
    kind: Literal["monetary_amount"]
    amount: PlannerMoneyInput


type OrderMinimum = Annotated[
    Union[NoOrderMinimum, WholeQuantityMinimum, MonetaryAmountMinimum],
    Field(discriminator="kind"),
]


class QuantityOrderCap(AllocationStrictModel):
    kind: Literal["quantity"]
    quantity: PlannerFixedDecimal
    unit: QuantityUnit


class NotionalOrderCap(AllocationStrictModel):
    kind: Literal["notional"]
    amount: PlannerMoneyInput


type OrderCap = Annotated[
    Union[QuantityOrderCap, NotionalOrderCap],
    Field(discriminator="kind"),
]


class PlannerOrderRouteInput(AllocationStrictModel):
    route_id: PlannerId
    asset_id: PlannerId
    broker_id: PlannerId
    capability_id: PlannerId
    side: OrderSide
    priority: PlannerWireInteger
    minimum_if_active: OrderMinimum
    required_minimum: OrderMinimum
    cap: OrderCap
    execution_margin_rate: PlannerFixedDecimal
    fee_schedule_id: PlannerId
    provenance_id: PlannerId


class PlannerBuyOrderRouteInput(PlannerOrderRouteInput):
    side: Literal["buy"]


class PlannerSellOrderRouteInput(PlannerOrderRouteInput):
    side: Literal["sell"]
    gross_amount_requested: PlannerMoneyInput | None = Field(description="Required for a monetary SELL request; null for quantity-driven SELL routes.")


type RebalancerOrderRouteInput = Annotated[
    Union[PlannerBuyOrderRouteInput, PlannerSellOrderRouteInput],
    Field(discriminator="side"),
]


class PacOrderRouteInput(PlannerBuyOrderRouteInput):
    pass


class PlannerFxQuoteInput(AllocationStrictModel):
    """Operational nonidentity FX fact; assembly filters source identity rows."""

    fx_quote_id: PlannerId
    source_currency: CurrencyCode
    destination_currency: CurrencyCode = Field(description="Currency units received per one source-currency unit.")
    rate: PlannerFixedDecimal
    reference_date: ReferenceDate
    freshness: ObservationFreshness
    provenance_id: PlannerId


class PlannerFxRouteInput(AllocationStrictModel):
    fx_route_id: PlannerId
    broker_id: PlannerId
    fx_quote_id: PlannerId
    source_currency: CurrencyCode
    destination_currency: CurrencyCode = Field(description="Currency units received per one source-currency unit.")
    source_amount_step: PlannerMoneyInput
    spread_rate: PlannerFixedDecimal
    safety_buffer_rate: PlannerFixedDecimal
    fixed_fee: PlannerMoneyInput
    priority: PlannerWireInteger
    provenance_id: PlannerId


class PlannerTargetWeightInput(AllocationStrictModel):
    asset_id: PlannerId
    weight: PlannerFixedDecimal


class PlannerCostBasisInput(AllocationStrictModel):
    holding_id: PlannerId
    average_unit_cost: PlannerMoneyInput
    reference_date: ReferenceDate
    provenance_id: PlannerId


class PlannerAssetTaxInput(AllocationStrictModel):
    asset_id: PlannerId
    tax_rate: PlannerFixedDecimal
    fiscal_currency: CurrencyCode | None = Field(description="Persisted fiscal currency when known; null is explicit and must produce needs_input rather than target-currency substitution.")
    provenance_id: PlannerId


class PlannerBrokerWithholdingInput(AllocationStrictModel):
    broker_id: PlannerId
    withholding_kind: Literal["broker_withheld", "self_reserved"]
    carried_loss: PlannerMoneyInput
    reference_date: ReferenceDate
    provenance_id: PlannerId


class PlannerSellContextInput(AllocationStrictModel):
    """Complete explicit SELL facts; missing fiscal, tax, or withholding facts block assembly."""

    cost_bases: list[PlannerCostBasisInput]
    asset_taxes: list[PlannerAssetTaxInput]
    broker_withholding: list[PlannerBrokerWithholdingInput]


class _PlannerRequestBase(AllocationStrictModel):
    operation: Literal["plan"]
    snapshot: PlannerSnapshotInput
    as_of: ReferenceDate
    valuation_currency: CurrencyCode
    currency_specs: list[CurrencySpec]
    provenance: list[PlannerProvenance] = Field(description="Root provenance records referenced by every copied or manually supplied fact.")
    valuation_rates: list[PlannerValuationRateInput]
    assets: list[PlannerAssetInput]
    brokers: list[PlannerBrokerInput]
    existing_cash: list[PlannerExistingCashInput]
    contributions: list[PlannerContributionInput]
    funding_routes: list[PlannerFundingRouteInput]
    fx_quotes: list[PlannerFxQuoteInput]
    fx_routes: list[PlannerFxRouteInput]
    target_weights: list[PlannerTargetWeightInput]


class PacPlannerRequest(_PlannerRequestBase):
    order_routes: list[PacOrderRouteInput]
    policy: Literal["proportional", "min_fragmentation"]


class _RebalancerPlannerRequestBase(_PlannerRequestBase):
    holdings: list[PlannerHoldingInput]
    order_routes: list[RebalancerOrderRouteInput]


class RebalancerInvestOnlyRequest(_RebalancerPlannerRequestBase):
    policy: Literal["invest_only"]
    order_routes: list[PacOrderRouteInput]


class RebalancerInvestAndSellRequest(_RebalancerPlannerRequestBase):
    policy: Literal["invest_and_sell"]
    sell_context: PlannerSellContextInput

    @model_validator(mode="after")
    def require_sell_route(self) -> RebalancerInvestAndSellRequest:
        if not any(route.side == "sell" for route in self.order_routes):
            raise ValueError("invest_and_sell requires at least one SELL order route")
        return self


type RebalancerPlannerRequest = Annotated[
    Union[RebalancerInvestOnlyRequest, RebalancerInvestAndSellRequest],
    Field(discriminator="policy"),
]


# -----------------------------------------------------------------------------
# V2 exact output scalars, issues, evidence, and authoritative result rows
# -----------------------------------------------------------------------------


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


def _fixed_fraction(value: str) -> Fraction:
    """Convert canonical fixed-point text without applying Decimal context precision."""

    return Fraction(Decimal(value))


def _exact_fraction(value: FiniteDecimal | ExactRatio) -> Fraction:
    if isinstance(value, FiniteDecimal):
        return _fixed_fraction(value.value)
    return Fraction(int(value.numerator), int(value.denominator))


def _money_fraction(value: ExactMoney) -> Fraction:
    return _exact_fraction(value.value)


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
        if _exact_fraction(self.value) <= 0:
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
        if _exact_fraction(self.value) <= 0:
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


def _available_fraction(value: AvailableExactNumber | UnavailableExactNumber) -> Fraction | None:
    if isinstance(value, AvailableExactNumber):
        return _exact_fraction(value.value)
    return None


def _validate_weight_availability(
    values: list[AvailableExactNumber | UnavailableExactNumber],
    total: Fraction,
    zero_reason: str,
    label: str,
) -> None:
    fractions = [_available_fraction(value) for value in values]
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


PlannerIssueSection = Literal[
    "input",
    "assets",
    "brokers",
    "holdings",
    "cash",
    "contributions",
    "funding",
    "routing",
    "fx",
    "targets",
    "policy",
    "proof",
    "liquidity",
    "result",
]
PlannerIssueEntityKind = Literal[
    "scenario",
    "asset",
    "broker",
    "holding",
    "currency",
    "cash",
    "contribution",
    "funding_route",
    "fx_quote",
    "fx_route",
    "order_route",
    "order",
    "solution",
]


class SectionIssuePath(AllocationStrictModel):
    kind: Literal["section"]
    section: PlannerIssueSection


class EntityIssuePath(AllocationStrictModel):
    kind: Literal["entity"]
    section: PlannerIssueSection
    entity_kind: PlannerIssueEntityKind
    entity_id: PlannerId


class FieldIssuePath(AllocationStrictModel):
    kind: Literal["field"]
    section: PlannerIssueSection
    entity_kind: PlannerIssueEntityKind
    entity_id: PlannerId
    field: PlannerCode


type PlannerIssuePath = Annotated[
    Union[SectionIssuePath, EntityIssuePath, FieldIssuePath],
    Field(discriminator="kind"),
]


class TextIssueParam(AllocationStrictModel):
    kind: Literal["text"]
    name: PlannerId
    value: PlannerLongLabel


class IdIssueParam(AllocationStrictModel):
    kind: Literal["id"]
    name: PlannerId
    value: PlannerId


class CountIssueParam(AllocationStrictModel):
    kind: Literal["count"]
    name: PlannerId
    value: PlannerSafeInteger


class DecimalIssueParam(AllocationStrictModel):
    kind: Literal["decimal"]
    name: PlannerId
    value: PlannerFixedDecimal


class CurrencyIssueParam(AllocationStrictModel):
    kind: Literal["currency"]
    name: PlannerId
    value: CurrencyCode


class MoneyIssueParam(AllocationStrictModel):
    kind: Literal["money"]
    name: PlannerId
    value: PlannerMoneyInput


type PlannerIssueParam = Annotated[
    Union[TextIssueParam, IdIssueParam, CountIssueParam, DecimalIssueParam, CurrencyIssueParam, MoneyIssueParam],
    Field(discriminator="kind"),
]


class PlannerIssue(AllocationStrictModel):
    code: PlannerIssueCode
    severity: Literal["info", "warning", "error"]
    kind: Literal["missing", "invalid", "unsupported", "constraint", "proof", "info"]
    path: PlannerIssuePath
    message_key: PlannerMessageKey
    params: list[PlannerIssueParam]

    @model_validator(mode="after")
    def validate_param_names(self) -> PlannerIssue:
        _require_unique([param.name for param in self.params], "Issue parameter names")
        return self


class CountUnit(AllocationStrictModel):
    kind: Literal["count"]


class ValuationMoneyUnit(AllocationStrictModel):
    kind: Literal["valuation_money"]
    currency_code: CurrencyCode


class ValuationMoneySquaredUnit(AllocationStrictModel):
    kind: Literal["valuation_money_squared"]
    currency_code: CurrencyCode


class OrdinalPenaltyUnit(AllocationStrictModel):
    kind: Literal["ordinal_penalty"]


class CanonicalKeyUnit(AllocationStrictModel):
    kind: Literal["canonical_key"]


type NumericObjectiveUnit = Annotated[
    Union[CountUnit, ValuationMoneyUnit, ValuationMoneySquaredUnit, OrdinalPenaltyUnit],
    Field(discriminator="kind"),
]

ObjectiveCode = Literal[
    "fixed_l2",
    "shortfall",
    "turnover",
    "explicit_cost",
    "incremental_cost",
    "split_asset_count",
    "active_order_rows",
    "incremental_order_rows",
    "route_priority",
]
ObjectiveSense = Literal["min", "max"]

_ObjectiveSignDomain = Literal["signed", "nonnegative", "nonnegative_integer"]
# Keep this exhaustive: every future ObjectiveCode must choose its sign domain.
_OBJECTIVE_SIGN_DOMAINS: dict[ObjectiveCode, _ObjectiveSignDomain] = {
    "fixed_l2": "nonnegative",
    "shortfall": "signed",
    "turnover": "nonnegative",
    "explicit_cost": "nonnegative",
    "incremental_cost": "nonnegative",
    "split_asset_count": "nonnegative_integer",
    "active_order_rows": "nonnegative_integer",
    "incremental_order_rows": "nonnegative_integer",
    "route_priority": "nonnegative_integer",
}


def _objective_unit_kind(code: ObjectiveCode) -> str:
    if code == "fixed_l2":
        return "valuation_money_squared"
    if code in {"shortfall", "turnover", "explicit_cost", "incremental_cost"}:
        return "valuation_money"
    if code in {"split_asset_count", "active_order_rows", "incremental_order_rows"}:
        return "count"
    return "ordinal_penalty"


class SolverSettingEvidence(AllocationStrictModel):
    name: PlannerId
    value: PlannerLongLabel


class SolverToleranceEvidence(AllocationStrictModel):
    feasibility: PlannerNonNegativeDecimal
    integrality: PlannerNonNegativeDecimal
    absolute_gap: PlannerNonNegativeDecimal
    relative_gap: PlannerNonNegativeDecimal


class SolverStageEvidence(AllocationStrictModel):
    """Non-authoritative floating solver report; never an exact objective value."""

    kind: Literal["reported_floating"]
    stage: PlannerId
    objective_code: ObjectiveCode
    ordinal: PlannerPositiveInteger
    status: Literal["finished", "unfinished"]
    scope: Literal["global", "incumbent_face"]
    sense: ObjectiveSense
    unit: NumericObjectiveUnit
    primal: PlannerFixedDecimal | None
    dual: PlannerFixedDecimal | None
    absolute_gap: PlannerNonNegativeDecimal | None
    relative_gap: PlannerNonNegativeDecimal | None
    tolerances: SolverToleranceEvidence
    engine: PlannerLabel
    version: PlannerLabel
    settings: list[SolverSettingEvidence]

    @model_validator(mode="after")
    def validate_objective_unit(self) -> SolverStageEvidence:
        if self.unit.kind != _objective_unit_kind(self.objective_code):
            raise ValueError("Solver stage unit does not match objective code")
        observations = (self.primal, self.dual, self.absolute_gap, self.relative_gap)
        if self.status == "finished" and any(value is None for value in observations):
            raise ValueError("Finished solver stage evidence requires finite primal, dual, and gaps")
        if self.primal is not None and self.dual is not None:
            primal = _fixed_fraction(self.primal)
            dual = _fixed_fraction(self.dual)
            if (self.sense == "min" and dual > primal) or (self.sense == "max" and primal > dual):
                raise ValueError("Reported bound ordering must match the objective sense")
            if self.absolute_gap is not None and _fixed_fraction(self.absolute_gap) < abs(primal - dual):
                raise ValueError("Reported absolute gap must bound the primal-dual difference")
        return self


class SolverNotRunEvidence(AllocationStrictModel):
    kind: Literal["not_run"]
    reason: SolverNotRunReasonCode


class ReportedFloatingSolverEvidence(AllocationStrictModel):
    kind: Literal["reported_floating"]
    stages: Annotated[list[SolverStageEvidence], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_stage_order(self) -> ReportedFloatingSolverEvidence:
        ordinals = [stage.ordinal for stage in self.stages]
        codes = [stage.objective_code for stage in self.stages]
        if ordinals != sorted(ordinals) or len(ordinals) != len(set(ordinals)) or len(codes) != len(set(codes)):
            raise ValueError("Solver stages must have unique codes and ascending ordinals")
        statuses = [stage.status for stage in self.stages]
        if statuses != sorted(statuses, key={"finished": 0, "unfinished": 1}.__getitem__):
            raise ValueError("Finished solver stages must precede unfinished stages")
        return self


type PlannerSolverEvidence = Annotated[
    Union[SolverNotRunEvidence, ReportedFloatingSolverEvidence],
    Field(discriminator="kind"),
]


class ExhaustiveOracleWitness(AllocationStrictModel):
    kind: Literal["exhaustive_oracle"]
    enumerated_candidates: PlannerPositiveInteger
    feasible_candidates: PlannerSafeInteger
    objective_codes: list[ObjectiveCode]

    @model_validator(mode="after")
    def validate_candidate_counts(self) -> ExhaustiveOracleWitness:
        if self.feasible_candidates > self.enumerated_candidates:
            raise ValueError("Feasible oracle candidates cannot exceed enumerated candidates")
        if len(self.objective_codes) != len(set(self.objective_codes)):
            raise ValueError("Oracle objective codes must be unique")
        return self


class ScoreLatticeClosureWitness(AllocationStrictModel):
    kind: Literal["score_lattice_closure"]
    objective_codes: Annotated[list[ObjectiveCode], Field(min_length=1)]
    closed_stage_count: PlannerPositiveInteger

    @model_validator(mode="after")
    def validate_closed_stages(self) -> ScoreLatticeClosureWitness:
        if len(self.objective_codes) != len(set(self.objective_codes)):
            raise ValueError("Closed objective codes must be unique")
        if self.closed_stage_count != len(self.objective_codes):
            raise ValueError("Closed stage count must equal the objective-code count")
        return self


class DeterministicConflictWitness(AllocationStrictModel):
    kind: Literal["deterministic_conflict"]
    issue_codes: Annotated[list[PlannerIssueCode], Field(min_length=1)]
    summary_code: PlannerIssueCode

    @model_validator(mode="after")
    def validate_issue_codes(self) -> DeterministicConflictWitness:
        if len(self.issue_codes) != len(set(self.issue_codes)):
            raise ValueError("Conflict issue codes must be unique")
        if self.summary_code not in self.issue_codes:
            raise ValueError("Conflict summary code must reference one listed issue")
        return self


type OptimalityWitness = Annotated[
    Union[ExhaustiveOracleWitness, ScoreLatticeClosureWitness],
    Field(discriminator="kind"),
]
type InfeasibilityWitness = Annotated[
    Union[ExhaustiveOracleWitness, DeterministicConflictWitness],
    Field(discriminator="kind"),
]


class OptimalProvenProof(AllocationStrictModel):
    kind: Literal["optimal_proven"]
    proof_source: Literal["exhaustive_oracle", "score_lattice_closure"]
    witness: OptimalityWitness
    tie_break_closed: Literal[True]

    @model_validator(mode="after")
    def validate_source_matches_witness(self) -> OptimalProvenProof:
        if self.proof_source != self.witness.kind:
            raise ValueError("Proof source must match optimality witness kind")
        if isinstance(self.witness, ExhaustiveOracleWitness):
            if self.witness.feasible_candidates == 0:
                raise ValueError("Optimal oracle proof must include a feasible candidate")
            if not self.witness.objective_codes:
                raise ValueError("Optimal oracle proof must cover an objective")
        return self


class BoundedObjectiveStage(AllocationStrictModel):
    stage: PlannerId
    objective_code: ObjectiveCode
    ordinal: PlannerPositiveInteger
    scope: Literal["global", "incumbent_face"]
    sense: ObjectiveSense
    unit: NumericObjectiveUnit
    primal: PlannerFixedDecimal
    dual: PlannerFixedDecimal
    absolute_gap: PlannerNonNegativeDecimal
    relative_gap: PlannerNonNegativeDecimal

    @model_validator(mode="after")
    def validate_objective_unit(self) -> BoundedObjectiveStage:
        if self.unit.kind != _objective_unit_kind(self.objective_code):
            raise ValueError("Bounded objective unit does not match objective code")
        primal = _fixed_fraction(self.primal)
        dual = _fixed_fraction(self.dual)
        if (self.sense == "min" and dual > primal) or (self.sense == "max" and primal > dual):
            raise ValueError("Bound ordering must match the objective sense")
        if _fixed_fraction(self.absolute_gap) < abs(primal - dual):
            raise ValueError("Absolute gap must bound the primal-dual difference")
        return self


class GapBoundedProof(AllocationStrictModel):
    kind: Literal["gap_bounded"]
    stage_bounds: Annotated[list[BoundedObjectiveStage], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_stage_order(self) -> GapBoundedProof:
        ordinals = [stage.ordinal for stage in self.stage_bounds]
        codes = [stage.objective_code for stage in self.stage_bounds]
        if ordinals != sorted(ordinals) or len(ordinals) != len(set(ordinals)) or len(codes) != len(set(codes)):
            raise ValueError("Gap bounds must have unique objective codes and ascending ordinals")
        return self


class NotProvenProof(AllocationStrictModel):
    kind: Literal["not_proven"]
    reason_code: NotProvenReasonCode


class InfeasibilityProvenProof(AllocationStrictModel):
    kind: Literal["infeasibility_proven"]
    proof_source: Literal["exhaustive_oracle", "deterministic_conflict"]
    witness: InfeasibilityWitness

    @model_validator(mode="after")
    def validate_source_matches_witness(self) -> InfeasibilityProvenProof:
        if self.proof_source != self.witness.kind:
            raise ValueError("Proof source must match infeasibility witness kind")
        if isinstance(self.witness, ExhaustiveOracleWitness) and self.witness.feasible_candidates != 0:
            raise ValueError("Infeasibility oracle proof cannot contain a feasible candidate")
        return self


type ReadyPlanProof = Annotated[
    Union[OptimalProvenProof, GapBoundedProof, NotProvenProof],
    Field(discriminator="kind"),
]


class PlannerCatalogAsset(AllocationStrictModel):
    asset_id: PlannerId
    name: PlannerLabel
    ticker: PlannerLabel | None
    asset_class: PlannerCode


class PlannerCatalogBroker(AllocationStrictModel):
    broker_id: PlannerId
    name: PlannerLabel


class PlannerCatalogs(AllocationStrictModel):
    assets: list[PlannerCatalogAsset]
    brokers: list[PlannerCatalogBroker]
    currencies: list[CurrencySpec]

    @model_validator(mode="after")
    def validate_catalog_ids(self) -> PlannerCatalogs:
        _require_unique([asset.asset_id for asset in self.assets], "Catalog Asset IDs")
        _require_unique([broker.broker_id for broker in self.brokers], "Catalog Broker IDs")
        _require_unique([currency.currency for currency in self.currencies], "Catalog currencies")
        if any(_fixed_fraction(currency.minor_unit) <= 0 for currency in self.currencies):
            raise ValueError("Published currency minor units must be positive")
        return self


class PlannerScenarioCounts(AllocationStrictModel):
    assets: PlannerSafeInteger
    brokers: PlannerSafeInteger
    currencies: PlannerSafeInteger
    holdings: PlannerSafeInteger
    existing_cash: PlannerSafeInteger
    contributions: PlannerSafeInteger
    funding_routes: PlannerSafeInteger
    capabilities: PlannerSafeInteger
    valuation_rates: PlannerSafeInteger
    fx_quotes: PlannerSafeInteger
    fx_routes: PlannerSafeInteger
    order_routes: PlannerSafeInteger
    provenance: PlannerSafeInteger


class PlannerScenarioBasis(AllocationStrictModel):
    as_of: ReferenceDate
    valuation_currency: CurrencyCode
    policy: Literal["proportional", "min_fragmentation", "invest_only", "invest_and_sell"]
    counts: PlannerScenarioCounts
    current_invested: ExactMoney
    selected_funding: ExactMoney
    reachable_funding: ExactMoney
    trapped_funding: ExactMoney
    fixed_reference: ExactMoney


class PacAssetPlanRow(AllocationStrictModel):
    asset_id: PlannerId
    target_weight: ExactNumber
    target_value: ExactMoney
    final_value: ExactMoney
    residual: ExactMoney
    final_weight: ExactNumberAvailability
    buy_mid_value: ExactMoney


class RebalancerAssetPlanRow(AllocationStrictModel):
    asset_id: PlannerId
    before_value: ExactMoney
    target_weight: ExactNumber
    target_value: ExactMoney
    final_value: ExactMoney
    residual: ExactMoney
    before_weight: ExactNumberAvailability
    final_weight: ExactNumberAvailability
    buy_mid_value: ExactMoney
    sell_mid_value: ExactMoney


class PlannerFundingAction(AllocationStrictModel):
    action_id: PlannerId
    sequence: PlannerPositiveInteger
    funding_route_id: PlannerId
    source: PlannerFundingSourceRef
    destination_broker_id: PlannerId
    amount: PlannerPositiveMoneyInput
    reason_code: FundingActionReasonCode
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]


class PlannerFxAction(AllocationStrictModel):
    action_id: PlannerId
    sequence: PlannerPositiveInteger
    fx_route_id: PlannerId
    broker_id: PlannerId
    source_debit: PlannerPositiveMoneyInput
    destination_credit: PlannerPositiveMoneyInput
    spot_rate: ExactFxRate
    effective_rate: ExactFxRate
    spread_loss: ExactMoney
    fee: PlannerNonNegativeMoneyInput
    buffer: PlannerNonNegativeMoneyInput
    reference_date: ReferenceDate
    freshness: ObservationFreshness
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_action_rates_and_costs(self) -> PlannerFxAction:
        if (self.spot_rate.source_currency, self.spot_rate.destination_currency) != (
            self.source_debit.currency,
            self.destination_credit.currency,
        ):
            raise ValueError("FX action rates must follow the posted source-to-destination direction")
        if (self.effective_rate.source_currency, self.effective_rate.destination_currency) != (
            self.source_debit.currency,
            self.destination_credit.currency,
        ):
            raise ValueError("Effective FX rate must follow the posted source-to-destination direction")
        if _exact_fraction(self.effective_rate.value) > _exact_fraction(self.spot_rate.value):
            raise ValueError("Effective FX rate cannot exceed the approved spot rate")
        if self.fee.currency != self.source_debit.currency or self.buffer.currency != self.source_debit.currency:
            raise ValueError("FX action fee and buffer must use the source currency")
        if _exact_fraction(self.spread_loss.value) < 0:
            raise ValueError("FX spread loss cannot be negative")
        if isinstance(self.freshness, AcceptedStaleObservation):
            if self.freshness.age_days < 0:
                raise ValueError("Published stale FX actions require a nonnegative observation age")
            if not self.freshness.accepted:
                raise ValueError("Published stale FX actions require explicit acceptance")
        return self


class WholeQuantityInstruction(AllocationStrictModel):
    kind: Literal["whole_quantity"]
    quantity: PlannerPositiveWholeDecimal
    quantity_step: PlannerPositiveWholeDecimal
    unit: QuantityUnit


class MonetaryAmountInstruction(AllocationStrictModel):
    kind: Literal["monetary_amount"]
    amount: PlannerPositiveMoneyInput
    order_amount_step: PlannerPositiveMoneyInput


type PlannerOrderInstruction = Annotated[
    Union[WholeQuantityInstruction, MonetaryAmountInstruction],
    Field(discriminator="kind"),
]


class ExactEconomicQuantity(AllocationStrictModel):
    kind: Literal["exact"]
    value: ExactNumber
    unit: QuantityUnit

    @model_validator(mode="after")
    def validate_positive_value(self) -> ExactEconomicQuantity:
        if _exact_fraction(self.value) <= 0:
            raise ValueError("Order economic quantity must be positive")
        return self


class EstimatedExactRatioQuantity(AllocationStrictModel):
    kind: Literal["estimated_exact_ratio"]
    value: ExactRatio
    unit: QuantityUnit

    @model_validator(mode="after")
    def validate_positive_value(self) -> EstimatedExactRatioQuantity:
        if _exact_fraction(self.value) <= 0:
            raise ValueError("Estimated order economic quantity must be positive")
        return self


type PlannerEconomicQuantity = Annotated[
    Union[ExactEconomicQuantity, EstimatedExactRatioQuantity],
    Field(discriminator="kind"),
]


class PlannerBuyOrderRow(AllocationStrictModel):
    kind: Literal["buy"]
    order_id: PlannerId
    sequence: PlannerPositiveInteger
    asset_id: PlannerId
    broker_id: PlannerId
    route_id: PlannerId
    instruction: PlannerOrderInstruction
    economic_quantity: PlannerEconomicQuantity
    source_price: ExactPrice
    mid_price: ExactPrice
    charge_price: ExactPrice
    mid_value: ExactMoney
    execution_margin_cost: ExactMoney
    cash_debit: PlannerPositiveMoneyInput
    fee: PlannerNonNegativeMoneyInput
    fx_cost: ExactMoney
    buffer: PlannerNonNegativeMoneyInput
    explanation_keys: list[PlannerMessageKey]
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_order_values(self) -> PlannerBuyOrderRow:
        price_currencies = {self.source_price.currency, self.mid_price.currency, self.charge_price.currency}
        if price_currencies != {self.cash_debit.currency}:
            raise ValueError("BUY prices and cash debit must use one order currency")
        if len({self.source_price.quote_base_quantity, self.mid_price.quote_base_quantity, self.charge_price.quote_base_quantity}) != 1:
            raise ValueError("BUY prices must use one quote base quantity")
        if _exact_fraction(self.charge_price.value) < _exact_fraction(self.mid_price.value):
            raise ValueError("BUY charge price cannot be below mid price")
        if self.fee.currency != self.cash_debit.currency or self.buffer.currency != self.cash_debit.currency:
            raise ValueError("BUY fee and buffer must use the order currency")
        if isinstance(self.instruction, MonetaryAmountInstruction):
            if {self.instruction.amount.currency, self.instruction.order_amount_step.currency} != {self.cash_debit.currency}:
                raise ValueError("Monetary BUY instruction must use the order currency")
        if _exact_fraction(self.mid_value.value) <= 0:
            raise ValueError("BUY mid value must be positive")
        if _exact_fraction(self.execution_margin_cost.value) < 0:
            raise ValueError("BUY execution-margin cost cannot be negative")
        if _exact_fraction(self.fx_cost.value) < 0:
            raise ValueError("BUY FX cost cannot be negative")
        return self


class PlannerSellOrderRow(AllocationStrictModel):
    kind: Literal["sell"]
    order_id: PlannerId
    sequence: PlannerPositiveInteger
    asset_id: PlannerId
    broker_id: PlannerId
    route_id: PlannerId
    instruction: PlannerOrderInstruction
    economic_quantity: PlannerEconomicQuantity
    source_price: ExactPrice
    mid_price: ExactPrice
    sell_price: ExactPrice
    mid_value: ExactMoney
    execution_margin_cost: ExactMoney
    gross_credit: PlannerPositiveMoneyInput
    fee: PlannerNonNegativeMoneyInput
    cost_basis: PlannerNonNegativeMoneyInput
    taxable_gain: PlannerNonNegativeMoneyInput
    tax_reserve: PlannerNonNegativeMoneyInput
    withholding_kind: Literal["broker_withheld", "self_reserved"]
    spendable_credit: PlannerPositiveMoneyInput
    irreducibility_evidence_ref: PlannerId
    explanation_keys: list[PlannerMessageKey]
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_order_value(self) -> PlannerSellOrderRow:
        price_currencies = {self.source_price.currency, self.mid_price.currency, self.sell_price.currency}
        if price_currencies != {self.gross_credit.currency}:
            raise ValueError("SELL prices and gross credit must use one order currency")
        if len({self.source_price.quote_base_quantity, self.mid_price.quote_base_quantity, self.sell_price.quote_base_quantity}) != 1:
            raise ValueError("SELL prices must use one quote base quantity")
        if _exact_fraction(self.sell_price.value) > _exact_fraction(self.mid_price.value):
            raise ValueError("SELL execution price cannot exceed mid price")
        posted_currencies = {self.fee.currency, self.tax_reserve.currency, self.spendable_credit.currency}
        if posted_currencies != {self.gross_credit.currency}:
            raise ValueError("SELL fee, tax reserve, and spendable credit must use the order currency")
        if isinstance(self.instruction, MonetaryAmountInstruction):
            if {self.instruction.amount.currency, self.instruction.order_amount_step.currency} != {self.gross_credit.currency}:
                raise ValueError("Monetary SELL instruction must use the order currency")
        if _fixed_fraction(self.spendable_credit.amount) != _fixed_fraction(self.gross_credit.amount) - _fixed_fraction(self.fee.amount) - _fixed_fraction(self.tax_reserve.amount):
            raise ValueError("SELL spendable credit must equal gross credit less fee and tax reserve")
        if _exact_fraction(self.mid_value.value) <= 0:
            raise ValueError("SELL mid value must be positive")
        if _exact_fraction(self.execution_margin_cost.value) < 0:
            raise ValueError("SELL execution-margin cost cannot be negative")
        return self


type RebalancerOrderRow = Annotated[
    Union[PlannerBuyOrderRow, PlannerSellOrderRow],
    Field(discriminator="kind"),
]


class SellIrreducibilityCheck(AllocationStrictModel):
    kind: Literal["decrement_one_quantum", "zero_row"]
    result: Literal["closed_no_better_candidate"]
    closure_kind: Literal["deterministic_conflict", "exhaustive_oracle"]
    blocking_issue_codes: Annotated[list[PlannerIssueCode], Field(min_length=1)]


class SellIrreducibilityEvidence(AllocationStrictModel):
    evidence_id: PlannerId
    order_id: PlannerId
    checks: Annotated[list[SellIrreducibilityCheck], Field(min_length=2, max_length=2)]

    @model_validator(mode="after")
    def validate_counterfactual_order(self) -> SellIrreducibilityEvidence:
        if [check.kind for check in self.checks] != ["decrement_one_quantum", "zero_row"]:
            raise ValueError("SELL irreducibility requires decrement-one then zero-row counterfactuals")
        return self


class PlannerLedgerRow(AllocationStrictModel):
    broker_id: PlannerId
    currency: CurrencyCode
    initial_selected: PlannerFixedDecimal
    funding_in: PlannerFixedDecimal
    funding_out: PlannerFixedDecimal
    fx_debit: PlannerFixedDecimal
    fx_credit: PlannerFixedDecimal
    buy_debit: PlannerFixedDecimal
    gross_sell_credit: PlannerFixedDecimal
    buy_fees: PlannerFixedDecimal
    sell_fees: PlannerFixedDecimal
    fx_fees: PlannerFixedDecimal
    broker_withheld_tax: PlannerFixedDecimal
    self_reserved_tax: PlannerFixedDecimal
    fx_buffer: PlannerFixedDecimal
    rounding_delta: PlannerFixedDecimal = Field(description="Raw posted-exact rounding delta; credits are negated in the accounting identity.")
    final_spendable: PlannerFixedDecimal
    final_physical: PlannerFixedDecimal

    @model_validator(mode="after")
    def validate_ledger_identity(self) -> PlannerLedgerRow:
        nonnegative_fields = (
            "initial_selected",
            "funding_in",
            "funding_out",
            "fx_debit",
            "fx_credit",
            "buy_debit",
            "gross_sell_credit",
            "buy_fees",
            "sell_fees",
            "fx_fees",
            "broker_withheld_tax",
            "self_reserved_tax",
            "fx_buffer",
            "final_spendable",
            "final_physical",
        )
        if any(_fixed_fraction(getattr(self, name)) < 0 for name in nonnegative_fields):
            raise ValueError("Published ledger amounts cannot be negative")
        expected_spendable = (
            _fixed_fraction(self.initial_selected)
            + _fixed_fraction(self.funding_in)
            + _fixed_fraction(self.fx_credit)
            + _fixed_fraction(self.gross_sell_credit)
            - _fixed_fraction(self.funding_out)
            - _fixed_fraction(self.fx_debit)
            - _fixed_fraction(self.buy_debit)
            - _fixed_fraction(self.buy_fees)
            - _fixed_fraction(self.sell_fees)
            - _fixed_fraction(self.broker_withheld_tax)
            - _fixed_fraction(self.self_reserved_tax)
            - _fixed_fraction(self.fx_fees)
            - _fixed_fraction(self.fx_buffer)
        )
        if expected_spendable != _fixed_fraction(self.final_spendable):
            raise ValueError("Ledger spendable balance does not reconcile its posted debits and credits")
        if _fixed_fraction(self.final_spendable) + _fixed_fraction(self.self_reserved_tax) + _fixed_fraction(self.fx_buffer) != _fixed_fraction(self.final_physical):
            raise ValueError("Ledger spendable balance does not reconcile")
        return self


class PacExposurePlanRow(AllocationStrictModel):
    dimension: Literal["asset_type", "sector", "geography"]
    category_id: PlannerId
    label: PlannerLabel
    target_weight: ExactNumber
    final_weight: ExactNumberAvailability
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_weights(self) -> PacExposurePlanRow:
        target = _exact_fraction(self.target_weight)
        final = _available_fraction(self.final_weight)
        if target < 0 or target > 1 or (final is not None and (final < 0 or final > 1)):
            raise ValueError("Exposure weights must be between zero and one")
        return self


class RebalancerExposurePlanRow(AllocationStrictModel):
    dimension: Literal["asset_type", "sector", "geography"]
    category_id: PlannerId
    label: PlannerLabel
    before_weight: ExactNumberAvailability
    target_weight: ExactNumber
    final_weight: ExactNumberAvailability
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_weights(self) -> RebalancerExposurePlanRow:
        target = _exact_fraction(self.target_weight)
        before = _available_fraction(self.before_weight)
        final = _available_fraction(self.final_weight)
        if target < 0 or target > 1:
            raise ValueError("Target exposure weight must be between zero and one")
        if any(value is not None and (value < 0 or value > 1) for value in (before, final)):
            raise ValueError("Available exposure weights must be between zero and one")
        return self


class PlannerAccountingSummary(AllocationStrictModel):
    current_invested: ExactMoney
    selected_funding: ExactMoney
    reachable_funding: ExactMoney
    trapped_funding: ExactMoney
    fixed_reference: ExactMoney
    final_invested: ExactMoney
    shortfall: ExactMoney
    free_cash: ExactMoney
    physical_reserves: ExactMoney
    economic_losses: ExactMoney
    rounding_delta: ExactMoney = Field(description="Raw posted-exact aggregate rounding delta.")
    rounding_bound: ExactMoney
    identity_delta: ExactMoney


class PlannerCostTotals(AllocationStrictModel):
    buy_fees: ExactMoney
    sell_fees: ExactMoney
    fx_fees: ExactMoney
    fx_spread_loss: ExactMoney
    execution_margin_cost: ExactMoney
    broker_withheld_tax: ExactMoney
    self_reserved_tax: ExactMoney
    fx_buffer: ExactMoney


class ObjectiveStageResult(AllocationStrictModel):
    objective_code: ObjectiveCode
    ordinal: PlannerPositiveInteger
    sense: ObjectiveSense
    unit: NumericObjectiveUnit
    value: ExactNumber

    @model_validator(mode="after")
    def validate_objective_unit_and_value(self) -> ObjectiveStageResult:
        sign_domain = _OBJECTIVE_SIGN_DOMAINS.get(self.objective_code)
        if sign_domain is None:
            raise ValueError("Objective code must declare its sign domain")
        if self.unit.kind != _objective_unit_kind(self.objective_code):
            raise ValueError("Objective unit does not match objective code")
        value = _exact_fraction(self.value)
        if sign_domain == "nonnegative" and value < 0:
            raise ValueError("Objective value must be nonnegative")
        if sign_domain == "nonnegative_integer":
            if value < 0 or value.denominator != 1:
                raise ValueError("Count and ordinal objectives must be nonnegative integers")
        return self


class TieBreakResult(AllocationStrictModel):
    code: Literal["canonical_key"]
    unit: CanonicalKeyUnit
    ordered_keys: list[PlannerId]

    @model_validator(mode="after")
    def validate_keys(self) -> TieBreakResult:
        _require_unique(self.ordered_keys, "Tie-break keys")
        return self


class PlannerObjectiveResults(AllocationStrictModel):
    stages: Annotated[list[ObjectiveStageResult], Field(min_length=1)]
    tie_break: TieBreakResult

    @model_validator(mode="after")
    def validate_stage_order(self) -> PlannerObjectiveResults:
        ordinals = [stage.ordinal for stage in self.stages]
        codes = [stage.objective_code for stage in self.stages]
        if ordinals != sorted(ordinals) or len(ordinals) != len(set(ordinals)) or len(codes) != len(set(codes)):
            raise ValueError("Objective stages must have unique codes and ascending ordinals")
        return self


class PacPlanSolution(AllocationStrictModel):
    solution_id: PlannerId
    solution_kind: Literal["primary"]
    validation: Literal["decimal_verified"]
    asset_rows: list[PacAssetPlanRow]
    funding_actions: list[PlannerFundingAction]
    fx_actions: list[PlannerFxAction]
    order_rows: list[PlannerBuyOrderRow]
    ledger_rows: list[PlannerLedgerRow]
    exposure_rows: list[PacExposurePlanRow]
    accounting: PlannerAccountingSummary
    costs: PlannerCostTotals
    objectives: PlannerObjectiveResults

    @model_validator(mode="after")
    def validate_authoritative_rows(self) -> PacPlanSolution:
        _require_unique([row.asset_id for row in self.asset_rows], "PAC Asset rows")
        actions = [*self.funding_actions, *self.fx_actions, *self.order_rows]
        _require_unique([action.action_id if hasattr(action, "action_id") else action.order_id for action in actions], "PAC action IDs")
        sequences = [action.sequence for action in actions]
        _require_unique(sequences, "PAC action sequences")
        if any([row.sequence for row in rows] != sorted(row.sequence for row in rows) for rows in (self.funding_actions, self.fx_actions, self.order_rows)):
            raise ValueError("PAC action sections must be sequence-ordered")
        _require_unique([(row.broker_id, row.currency) for row in self.ledger_rows], "PAC ledger scopes")
        _require_unique([(row.dimension, row.category_id) for row in self.exposure_rows], "PAC exposure rows")
        return self


class RebalancerPlanSolution(AllocationStrictModel):
    solution_id: PlannerId
    solution_kind: Literal["primary"]
    validation: Literal["decimal_verified"]
    asset_rows: list[RebalancerAssetPlanRow]
    funding_actions: list[PlannerFundingAction]
    fx_actions: list[PlannerFxAction]
    order_rows: list[RebalancerOrderRow]
    sell_irreducibility: list[SellIrreducibilityEvidence]
    ledger_rows: list[PlannerLedgerRow]
    exposure_rows: list[RebalancerExposurePlanRow]
    accounting: PlannerAccountingSummary
    costs: PlannerCostTotals
    objectives: PlannerObjectiveResults

    @model_validator(mode="after")
    def validate_authoritative_rows(self) -> RebalancerPlanSolution:
        _require_unique([row.asset_id for row in self.asset_rows], "Rebalancer Asset rows")
        actions = [*self.funding_actions, *self.fx_actions, *self.order_rows]
        _require_unique(
            [action.action_id if hasattr(action, "action_id") else action.order_id for action in actions],
            "Rebalancer action IDs",
        )
        sequences = [action.sequence for action in actions]
        _require_unique(sequences, "Rebalancer action sequences")
        if any([row.sequence for row in rows] != sorted(row.sequence for row in rows) for rows in (self.funding_actions, self.fx_actions, self.order_rows)):
            raise ValueError("Rebalancer action sections must be sequence-ordered")
        _require_unique([(row.broker_id, row.currency) for row in self.ledger_rows], "Rebalancer ledger scopes")
        _require_unique([(row.dimension, row.category_id) for row in self.exposure_rows], "Rebalancer exposure rows")
        _require_unique([row.evidence_id for row in self.sell_irreducibility], "SELL evidence IDs")
        _require_unique([row.order_id for row in self.sell_irreducibility], "SELL evidence order IDs")
        evidence = {row.evidence_id: row.order_id for row in self.sell_irreducibility}
        sell_orders = {row.order_id: row.irreducibility_evidence_ref for row in self.order_rows if isinstance(row, PlannerSellOrderRow)}
        if set(evidence.values()) != set(sell_orders):
            raise ValueError("SELL orders and irreducibility evidence must be one-to-one")
        if any(evidence.get(evidence_id) != order_id for order_id, evidence_id in sell_orders.items()):
            raise ValueError("SELL orders must reference their own irreducibility evidence")
        return self


def _validate_no_op_common(solution: PacPlanSolution | RebalancerPlanSolution) -> None:
    if any(_money_fraction(getattr(solution.costs, name)) != 0 for name in type(solution.costs).model_fields):
        raise ValueError("No-op solutions cannot publish costs")
    accounting = solution.accounting
    if any(_money_fraction(value) != 0 for value in (accounting.physical_reserves, accounting.economic_losses, accounting.rounding_delta)):
        raise ValueError("No-op solutions cannot publish new reserves, losses, or rounding")
    flow_fields = (
        "funding_in",
        "funding_out",
        "fx_debit",
        "fx_credit",
        "buy_debit",
        "gross_sell_credit",
        "buy_fees",
        "sell_fees",
        "fx_fees",
        "broker_withheld_tax",
        "self_reserved_tax",
        "fx_buffer",
        "rounding_delta",
    )
    for row in solution.ledger_rows:
        if any(_fixed_fraction(getattr(row, name)) != 0 for name in flow_fields):
            raise ValueError("No-op ledger rows cannot contain action-derived postings")
        if _fixed_fraction(row.final_spendable) != _fixed_fraction(row.initial_selected) or _fixed_fraction(row.final_physical) != _fixed_fraction(row.initial_selected):
            raise ValueError("No-op ledger balances must preserve selected initial cash")


def _validate_pac_no_op(solution: PacPlanSolution) -> None:
    if _money_fraction(solution.accounting.final_invested) != 0:
        raise ValueError("No-op PAC final invested value must be zero")
    if any(_money_fraction(row.buy_mid_value) != 0 or _money_fraction(row.final_value) != 0 for row in solution.asset_rows):
        raise ValueError("No-op PAC Asset projections cannot contain BUY value")


def _validate_rebalancer_no_op(solution: RebalancerPlanSolution) -> None:
    if _money_fraction(solution.accounting.final_invested) != _money_fraction(solution.accounting.current_invested):
        raise ValueError("No-op Rebalancer final invested value must equal its current value")
    if any(_money_fraction(row.buy_mid_value) != 0 or _money_fraction(row.sell_mid_value) != 0 or _money_fraction(row.final_value) != _money_fraction(row.before_value) for row in solution.asset_rows):
        raise ValueError("No-op Rebalancer Asset projections must preserve the current portfolio")


class PacNoOpSolution(PacPlanSolution):
    funding_actions: Annotated[list[PlannerFundingAction], Field(max_length=0)]
    fx_actions: Annotated[list[PlannerFxAction], Field(max_length=0)]
    order_rows: Annotated[list[PlannerBuyOrderRow], Field(max_length=0)]

    @model_validator(mode="after")
    def validate_no_op_projection(self) -> PacNoOpSolution:
        _validate_no_op_common(self)
        _validate_pac_no_op(self)
        return self


class RebalancerNoOpSolution(RebalancerPlanSolution):
    funding_actions: Annotated[list[PlannerFundingAction], Field(max_length=0)]
    fx_actions: Annotated[list[PlannerFxAction], Field(max_length=0)]
    order_rows: Annotated[list[RebalancerOrderRow], Field(max_length=0)]
    sell_irreducibility: Annotated[list[SellIrreducibilityEvidence], Field(max_length=0)]

    @model_validator(mode="after")
    def validate_no_op_projection(self) -> RebalancerNoOpSolution:
        _validate_no_op_common(self)
        _validate_rebalancer_no_op(self)
        return self


class PacIncumbentSolution(PacPlanSolution):
    order_rows: Annotated[list[PlannerBuyOrderRow], Field(min_length=1)]


class RebalancerIncumbentSolution(RebalancerPlanSolution):
    order_rows: Annotated[list[RebalancerOrderRow], Field(min_length=1)]


class PacDeploymentSolution(PacPlanSolution):
    solution_kind: Literal["deployment"]


class RebalancerDeploymentSolution(RebalancerPlanSolution):
    solution_kind: Literal["deployment"]


class ObjectiveDelta(AllocationStrictModel):
    objective_code: ObjectiveCode
    ordinal: PlannerPositiveInteger
    sense: ObjectiveSense
    unit: NumericObjectiveUnit
    primary_value: ExactNumber
    deployment_value: ExactNumber
    delta: ExactNumber

    @model_validator(mode="after")
    def validate_objective_unit(self) -> ObjectiveDelta:
        if self.unit.kind != _objective_unit_kind(self.objective_code):
            raise ValueError("Objective delta unit does not match objective code")
        return self


class DeploymentComparison(AllocationStrictModel):
    primary_solution_id: PlannerId
    deployment_solution_id: PlannerId
    changed_order_rows: PlannerSafeInteger
    objective_deltas: list[ObjectiveDelta]

    @model_validator(mode="after")
    def validate_objective_order(self) -> DeploymentComparison:
        ordinals = [delta.ordinal for delta in self.objective_deltas]
        codes = [delta.objective_code for delta in self.objective_deltas]
        if ordinals != sorted(ordinals) or len(ordinals) != len(set(ordinals)) or len(codes) != len(set(codes)):
            raise ValueError("Objective deltas must have unique codes and ascending ordinals")
        return self


class DeploymentUnavailable(AllocationStrictModel):
    kind: Literal["unavailable"]
    reason_code: DeploymentReasonCode


class DeploymentCoincident(AllocationStrictModel):
    kind: Literal["coincident"]
    reason_code: DeploymentReasonCode


class PacDistinctDeployment(AllocationStrictModel):
    kind: Literal["distinct"]
    solution: PacDeploymentSolution
    comparison: DeploymentComparison


class RebalancerDistinctDeployment(AllocationStrictModel):
    kind: Literal["distinct"]
    solution: RebalancerDeploymentSolution
    comparison: DeploymentComparison


def _validate_distinct_deployment(
    primary: PacPlanSolution | RebalancerPlanSolution,
    deployment: PacDistinctDeployment | RebalancerDistinctDeployment,
) -> None:
    comparison = deployment.comparison
    if primary.solution_id == deployment.solution.solution_id:
        raise ValueError("A distinct deployment must use a distinct solution ID")
    if comparison.primary_solution_id != primary.solution_id:
        raise ValueError("Deployment comparison must reference the primary solution")
    if comparison.deployment_solution_id != deployment.solution.solution_id:
        raise ValueError("Deployment comparison must reference the deployment solution")
    primary_orders = {row.order_id: row.model_dump(mode="json") for row in primary.order_rows}
    deployment_orders = {row.order_id: row.model_dump(mode="json") for row in deployment.solution.order_rows}
    changed_order_rows = sum(primary_orders.get(order_id) != deployment_orders.get(order_id) for order_id in primary_orders.keys() | deployment_orders.keys())
    if changed_order_rows == 0 or comparison.changed_order_rows != changed_order_rows:
        raise ValueError("A distinct deployment must report its exact nonzero changed-order-row count")
    primary_stages = primary.objectives.stages
    deployment_stages = deployment.solution.objectives.stages
    deltas = comparison.objective_deltas
    if len(primary_stages) != len(deployment_stages) or len(deltas) != len(primary_stages):
        raise ValueError("Deployment comparison must cover every objective stage")
    for primary_stage, deployment_stage, delta in zip(primary_stages, deployment_stages, deltas, strict=True):
        primary_key = (primary_stage.objective_code, primary_stage.ordinal, primary_stage.sense, primary_stage.unit)
        deployment_key = (deployment_stage.objective_code, deployment_stage.ordinal, deployment_stage.sense, deployment_stage.unit)
        delta_key = (delta.objective_code, delta.ordinal, delta.sense, delta.unit)
        if primary_key != deployment_key or delta_key != primary_key:
            raise ValueError("Deployment objective stages must have identical ordered identities")
        if delta.primary_value != primary_stage.value or delta.deployment_value != deployment_stage.value:
            raise ValueError("Deployment comparison values must match the authoritative solutions")
        if _exact_fraction(delta.delta) != _exact_fraction(delta.deployment_value) - _exact_fraction(delta.primary_value):
            raise ValueError("Deployment objective delta must equal deployment minus primary")


def _validate_accounting_summary(accounting: PlannerAccountingSummary) -> None:
    nonnegative = (
        accounting.current_invested,
        accounting.selected_funding,
        accounting.reachable_funding,
        accounting.trapped_funding,
        accounting.fixed_reference,
        accounting.final_invested,
        accounting.free_cash,
        accounting.physical_reserves,
        accounting.economic_losses,
        accounting.rounding_bound,
    )
    if any(_money_fraction(money) < 0 for money in nonnegative):
        raise ValueError("Nonnegative accounting totals cannot be negative")
    if _money_fraction(accounting.selected_funding) != _money_fraction(accounting.reachable_funding) + _money_fraction(accounting.trapped_funding):
        raise ValueError("Selected funding must equal reachable plus trapped funding")
    if _money_fraction(accounting.fixed_reference) != _money_fraction(accounting.current_invested) + _money_fraction(accounting.reachable_funding):
        raise ValueError("Fixed reference must equal current invested plus reachable funding")
    if abs(_money_fraction(accounting.rounding_delta)) > _money_fraction(accounting.rounding_bound):
        raise ValueError("Rounding delta must remain inside its exact bound")
    if _money_fraction(accounting.shortfall) < -_money_fraction(accounting.rounding_bound):
        raise ValueError("Shortfall cannot exceed the favorable rounding bound")
    decomposition = _money_fraction(accounting.free_cash) + _money_fraction(accounting.physical_reserves) + _money_fraction(accounting.economic_losses) + _money_fraction(accounting.rounding_delta)
    if _money_fraction(accounting.shortfall) != decomposition:
        raise ValueError("Shortfall must equal free cash, physical reserves, economic losses, and rounding")
    if _money_fraction(accounting.identity_delta) != 0:
        raise ValueError("Published accounting identity delta must be zero")


def _validate_asset_row(row: PacAssetPlanRow | RebalancerAssetPlanRow) -> None:
    nonnegative_values = [row.target_value, row.final_value, row.buy_mid_value]
    if isinstance(row, RebalancerAssetPlanRow):
        nonnegative_values.extend([row.before_value, row.sell_mid_value])
    if any(_money_fraction(value) < 0 for value in nonnegative_values):
        raise ValueError("Asset before, target, final, BUY, and SELL values cannot be negative")
    if _money_fraction(row.residual) != _money_fraction(row.final_value) - _money_fraction(row.target_value):
        raise ValueError("Asset residual must equal final minus target value")
    if isinstance(row, RebalancerAssetPlanRow):
        expected_final = _money_fraction(row.before_value) + _money_fraction(row.buy_mid_value) - _money_fraction(row.sell_mid_value)
    else:
        expected_final = _money_fraction(row.buy_mid_value)
    if _money_fraction(row.final_value) != expected_final:
        raise ValueError("Asset final value must reconcile before, BUY, and SELL values")


def _validate_target_weight_identities(
    rows: list[PacAssetPlanRow] | list[RebalancerAssetPlanRow],
    fixed_reference: Fraction,
) -> None:
    weights = [_exact_fraction(row.target_weight) for row in rows]
    if any(weight < 0 or weight > 1 for weight in weights) or sum(weights, Fraction()) != 1:
        raise ValueError("Asset target weights must form a complete unit vector")
    if any(weight * fixed_reference != _money_fraction(row.target_value) for row, weight in zip(rows, weights, strict=True)):
        raise ValueError("Each Asset target weight must match its fixed-reference target value")


def _validate_available_weight_identities(
    weights: list[ExactNumberAvailability],
    values: list[ExactMoney],
    total: Fraction,
    zero_reason: str,
    label: str,
) -> None:
    _validate_weight_availability(weights, total, zero_reason, label)
    if total == 0:
        return
    for weight, value in zip(weights, values, strict=True):
        available = _available_fraction(weight)
        if available is None or available * total != _money_fraction(value):
            raise ValueError(f"Each available Asset {label.lower()} weight must match its value")


def _validate_asset_projection(solution: PacPlanSolution | RebalancerPlanSolution) -> None:
    accounting = solution.accounting
    fixed_reference = _money_fraction(accounting.fixed_reference)
    current_invested = _money_fraction(accounting.current_invested)
    final_invested = _money_fraction(accounting.final_invested)
    if sum((_money_fraction(row.target_value) for row in solution.asset_rows), Fraction()) != fixed_reference:
        raise ValueError("Asset target values must sum to the fixed reference")
    if sum((_money_fraction(row.final_value) for row in solution.asset_rows), Fraction()) != final_invested:
        raise ValueError("Asset final values must sum to final invested value")
    for row in solution.asset_rows:
        _validate_asset_row(row)
    if isinstance(solution, RebalancerPlanSolution):
        if sum((_money_fraction(row.before_value) for row in solution.asset_rows), Fraction()) != current_invested:
            raise ValueError("Rebalancer before values must sum to current invested value")
    elif current_invested != 0:
        raise ValueError("PAC current invested value must be zero")
    if sum((_money_fraction(row.residual) for row in solution.asset_rows), Fraction()) != -_money_fraction(accounting.shortfall):
        raise ValueError("Asset residuals must sum to negative shortfall")
    _validate_target_weight_identities(solution.asset_rows, fixed_reference)
    _validate_available_weight_identities(
        [row.final_weight for row in solution.asset_rows],
        [row.final_value for row in solution.asset_rows],
        final_invested,
        "zero_final_invested",
        "Final",
    )
    if isinstance(solution, RebalancerPlanSolution):
        _validate_available_weight_identities(
            [row.before_weight for row in solution.asset_rows],
            [row.before_value for row in solution.asset_rows],
            current_invested,
            "zero_current_invested",
            "Before",
        )


def _validate_exposure_projection(solution: PacPlanSolution | RebalancerPlanSolution) -> None:
    dimensions: dict[str, list[PacExposurePlanRow | RebalancerExposurePlanRow]] = {}
    for row in solution.exposure_rows:
        dimensions.setdefault(row.dimension, []).append(row)
    for dimension, rows in dimensions.items():
        if sum((_exact_fraction(row.target_weight) for row in rows), Fraction()) != 1:
            raise ValueError(f"{dimension} exposure targets must form a complete unit vector")
        _validate_weight_availability(
            [row.final_weight for row in rows],
            _money_fraction(solution.accounting.final_invested),
            "zero_final_invested",
            f"{dimension} final exposure",
        )
        if isinstance(solution, RebalancerPlanSolution):
            _validate_weight_availability(
                [row.before_weight for row in rows],
                _money_fraction(solution.accounting.current_invested),
                "zero_current_invested",
                f"{dimension} before exposure",
            )


def _validate_solution_financials(
    solution: PacPlanSolution | RebalancerPlanSolution,
    valuation_currency: CurrencyCode,
) -> None:
    valuation_money = [
        *(getattr(solution.accounting, name) for name in type(solution.accounting).model_fields),
        *(getattr(solution.costs, name) for name in type(solution.costs).model_fields),
    ]
    for row in solution.asset_rows:
        fields = ("target_value", "final_value", "residual", "buy_mid_value")
        if isinstance(row, RebalancerAssetPlanRow):
            fields = ("before_value", *fields, "sell_mid_value")
        valuation_money.extend(getattr(row, name) for name in fields)
    valuation_money.extend(row.spread_loss for row in solution.fx_actions)
    valuation_money.extend(row.execution_margin_cost for row in solution.order_rows)
    valuation_money.extend(row.fx_cost for row in solution.order_rows if isinstance(row, PlannerBuyOrderRow))
    if any(money.currency != valuation_currency for money in valuation_money):
        raise ValueError("Asset, accounting, and cost projections must use the valuation currency")
    if any(_exact_fraction(getattr(solution.costs, name).value) < 0 for name in type(solution.costs).model_fields):
        raise ValueError("Cost totals cannot be negative")
    _validate_accounting_summary(solution.accounting)
    if isinstance(solution, RebalancerPlanSolution) and _money_fraction(solution.accounting.final_invested) <= 0:
        raise ValueError("Ready Rebalancer solutions require positive final invested value")
    _validate_asset_projection(solution)
    _validate_exposure_projection(solution)
    if any(stage.unit.kind in {"valuation_money", "valuation_money_squared"} and stage.unit.currency_code != valuation_currency for stage in solution.objectives.stages):
        raise ValueError("Valuation objective units must use the scenario valuation currency")
    if any(stage.objective_code == "shortfall" and _exact_fraction(stage.value) != _money_fraction(solution.accounting.shortfall) for stage in solution.objectives.stages):
        raise ValueError("The shortfall objective must equal the authoritative accounting shortfall")


def _validate_ready_solution(
    catalogs: PlannerCatalogs,
    provenance: list[PlannerProvenance],
    valuation_currency: CurrencyCode,
    solution: PacPlanSolution | RebalancerPlanSolution,
) -> None:
    asset_ids = {row.asset_id for row in catalogs.assets}
    broker_ids = {row.broker_id for row in catalogs.brokers}
    currencies = {row.currency for row in catalogs.currencies}
    provenance_ids = {row.provenance_id for row in provenance}
    if {row.asset_id for row in solution.asset_rows} != asset_ids:
        raise ValueError("Solution must carry exactly one authoritative row per catalog Asset")
    if any(row.broker_id not in broker_ids or row.currency not in currencies for row in solution.ledger_rows):
        raise ValueError("Ledger rows must reference catalog Broker and currency IDs")
    if any(row.destination_broker_id not in broker_ids for row in solution.funding_actions):
        raise ValueError("Funding rows must reference catalog Broker IDs")
    if any(row.broker_id not in broker_ids for row in solution.fx_actions):
        raise ValueError("FX rows must reference catalog Broker IDs")
    if any(row.asset_id not in asset_ids or row.broker_id not in broker_ids for row in solution.order_rows):
        raise ValueError("Order rows must reference catalog Asset and Broker IDs")
    if not _collect_currency_codes(solution.model_dump(mode="python")) <= currencies:
        raise ValueError("Solution rows must reference catalog currencies")
    referenced_provenance = {provenance_id for row in [*solution.funding_actions, *solution.fx_actions, *solution.order_rows, *solution.exposure_rows] for provenance_id in row.provenance_ids}
    if not referenced_provenance <= provenance_ids:
        raise ValueError("Solution rows must reference top-level provenance IDs")
    for row in [*solution.funding_actions, *solution.fx_actions, *solution.order_rows, *solution.exposure_rows]:
        _require_unique(row.provenance_ids, "Result-row provenance IDs")
    _validate_solution_financials(solution, valuation_currency)


def _validate_scenario_basis_financials(
    product: str,
    scenario_basis: PlannerScenarioBasis,
) -> None:
    basis_money = [
        scenario_basis.current_invested,
        scenario_basis.selected_funding,
        scenario_basis.reachable_funding,
        scenario_basis.trapped_funding,
        scenario_basis.fixed_reference,
    ]
    if any(money.currency != scenario_basis.valuation_currency for money in basis_money):
        raise ValueError(f"{product} scenario totals must use the valuation currency")
    if any(_exact_fraction(money.value) < 0 for money in basis_money):
        raise ValueError(f"{product} scenario totals cannot be negative")
    if product == "PAC" and _money_fraction(scenario_basis.current_invested) != 0:
        raise ValueError("PAC scenario current invested value must be zero")
    if product == "Rebalancer" and _money_fraction(scenario_basis.current_invested) <= 0:
        raise ValueError("Ready Rebalancer scenarios require positive current invested value")
    if _exact_fraction(scenario_basis.selected_funding.value) != _exact_fraction(scenario_basis.reachable_funding.value) + _exact_fraction(scenario_basis.trapped_funding.value):
        raise ValueError(f"{product} selected funding must equal reachable plus trapped funding")
    if _exact_fraction(scenario_basis.fixed_reference.value) != _exact_fraction(scenario_basis.current_invested.value) + _exact_fraction(scenario_basis.reachable_funding.value):
        raise ValueError(f"{product} fixed reference must equal current invested plus reachable funding")


def _validate_result_catalogs(
    product: str,
    catalogs: PlannerCatalogs,
    provenance: list[PlannerProvenance],
    scenario_basis: PlannerScenarioBasis,
) -> None:
    _require_unique([row.provenance_id for row in provenance], f"{product} provenance IDs")
    expected_counts = (len(catalogs.assets), len(catalogs.brokers), len(catalogs.currencies), len(provenance))
    actual_counts = (
        scenario_basis.counts.assets,
        scenario_basis.counts.brokers,
        scenario_basis.counts.currencies,
        scenario_basis.counts.provenance,
    )
    if actual_counts != expected_counts:
        raise ValueError(f"{product} catalog and provenance counts must match the result rows")
    if scenario_basis.valuation_currency not in {row.currency for row in catalogs.currencies}:
        raise ValueError(f"{product} valuation currency must appear in the result catalog")
    _validate_scenario_basis_financials(product, scenario_basis)


def _validate_basis_solution(
    scenario_basis: PlannerScenarioBasis,
    solution: PacPlanSolution | RebalancerPlanSolution,
) -> None:
    accounting = solution.accounting
    for field in ("current_invested", "selected_funding", "reachable_funding", "trapped_funding", "fixed_reference"):
        if getattr(scenario_basis, field) != getattr(accounting, field):
            raise ValueError(f"Scenario basis and solution accounting disagree on {field}")


def _validate_optimal_proof_objectives(
    proof: ReadyPlanProof | InfeasibilityProvenProof | None,
    solution: PacPlanSolution | RebalancerPlanSolution | None,
) -> None:
    if not isinstance(proof, OptimalProvenProof):
        return
    if solution is None:
        raise ValueError("optimal_proven requires a published primary solution")
    witness_codes = proof.witness.objective_codes
    published_codes = [stage.objective_code for stage in solution.objectives.stages]
    if witness_codes != published_codes:
        raise ValueError("Optimal proof witness must cover every published objective stage in order")
    if not proof.tie_break_closed:
        raise ValueError("Optimal proof witness must close the published canonical tie-break")


def _validate_not_proven_issue_binding(
    product: str,
    policy: str,
    proof: ReadyPlanProof | InfeasibilityProvenProof | None,
    issues: list[PlannerIssue],
) -> None:
    if not isinstance(proof, NotProvenProof) or proof.reason_code != "portfolio_rebalancer.sell_irreducibility_unresolved":
        return
    if product != "Rebalancer" or policy != "invest_and_sell":
        raise ValueError("SELL irreducibility reason is only valid for invest_and_sell")
    if not any(issue.code == proof.reason_code and issue.kind == "proof" and issue.severity == "warning" for issue in issues):
        raise ValueError("SELL irreducibility reason requires a matching warning proof issue")


def _validate_gap_proof(
    proof: ReadyPlanProof | InfeasibilityProvenProof | None,
    solver_evidence: PlannerSolverEvidence,
    solution: PacPlanSolution | RebalancerPlanSolution | None,
) -> None:
    if not isinstance(proof, GapBoundedProof):
        return
    if not isinstance(solver_evidence, ReportedFloatingSolverEvidence):
        raise ValueError("gap_bounded requires reported_floating solver evidence")
    unfinished = [stage for stage in solver_evidence.stages if stage.status == "unfinished"]
    if [(stage.stage, stage.objective_code, stage.ordinal, stage.scope, stage.sense, stage.unit.model_dump_json()) for stage in proof.stage_bounds] != [(stage.stage, stage.objective_code, stage.ordinal, stage.scope, stage.sense, stage.unit.model_dump_json()) for stage in unfinished]:
        raise ValueError("gap_bounded must cover every unfinished normative solver stage in order")
    if solution is None:
        raise ValueError("gap_bounded requires a published primary solution")
    objectives = {(stage.objective_code, stage.ordinal, stage.sense, stage.unit.model_dump_json()): stage for stage in solution.objectives.stages}
    for solver_stage, bound in zip(unfinished, proof.stage_bounds, strict=True):
        key = (bound.objective_code, bound.ordinal, bound.sense, bound.unit.model_dump_json())
        objective = objectives.get(key)
        if objective is None:
            raise ValueError("Gap-bound stages must match published objective stages, senses, and units")
        solver_values = (solver_stage.primal, solver_stage.dual, solver_stage.absolute_gap, solver_stage.relative_gap)
        if any(value is None for value in solver_values):
            raise ValueError("gap_bounded requires finite floating evidence for every unfinished tier")
        bound_values = (bound.primal, bound.dual, bound.absolute_gap, bound.relative_gap)
        if any(_fixed_fraction(solver_value) != _fixed_fraction(bound_value) for solver_value, bound_value in zip(solver_values, bound_values, strict=True) if solver_value is not None):
            raise ValueError("Gap-bound values must match their reported floating evidence")
        exact_objective = _exact_fraction(objective.value)
        primal = _fixed_fraction(bound.primal)
        dual = _fixed_fraction(bound.dual)
        if (bound.sense == "min" and not dual <= exact_objective <= primal) or (bound.sense == "max" and not primal <= exact_objective <= dual):
            raise ValueError("Exact incumbent objective must lie inside the sense-aware solver bounds")


def _validate_rebalancer_policy_solution(
    policy: str,
    solution: RebalancerPlanSolution,
) -> None:
    if policy != "invest_only":
        return
    if any(isinstance(row, PlannerSellOrderRow) for row in solution.order_rows):
        raise ValueError("invest_only results cannot contain SELL orders")
    if solution.sell_irreducibility:
        raise ValueError("invest_only results cannot contain SELL irreducibility evidence")


def _validate_solver_units(
    solver_evidence: PlannerSolverEvidence,
    valuation_currency: CurrencyCode,
) -> None:
    if not isinstance(solver_evidence, ReportedFloatingSolverEvidence):
        return
    if any(stage.unit.kind in {"valuation_money", "valuation_money_squared"} and stage.unit.currency_code != valuation_currency for stage in solver_evidence.stages):
        raise ValueError("Solver valuation units must use the scenario valuation currency")


def _validate_stop_evidence(
    stop_reason: str,
    solver_evidence: PlannerSolverEvidence,
) -> None:
    if stop_reason != "completed" and not isinstance(solver_evidence, ReportedFloatingSolverEvidence):
        raise ValueError("Solver limit stops require reported_floating stage evidence")
    if isinstance(solver_evidence, ReportedFloatingSolverEvidence):
        unfinished = any(stage.status == "unfinished" for stage in solver_evidence.stages)
        if (stop_reason == "completed") == unfinished:
            raise ValueError("Completed stops require finished stages; limit stops require an unfinished stage")


type PacDeployment = Annotated[
    Union[DeploymentUnavailable, DeploymentCoincident, PacDistinctDeployment],
    Field(discriminator="kind"),
]
type RebalancerDeployment = Annotated[
    Union[DeploymentUnavailable, DeploymentCoincident, RebalancerDistinctDeployment],
    Field(discriminator="kind"),
]


class PlannerResultSnapshot(AllocationStrictModel):
    snapshot_id: PlannerId
    request_fingerprint: PlannerRef = Field(description="External request correlation emitted only after internal view and scenario-fingerprint verification.")


class PacScenarioBasis(PlannerScenarioBasis):
    policy: Literal["proportional", "min_fragmentation"]


class RebalancerScenarioBasis(PlannerScenarioBasis):
    policy: Literal["invest_only", "invest_and_sell"]


class _PlannerFailureResultBase(AllocationStrictModel):
    operation: Literal["plan"]
    snapshot: PlannerResultSnapshot
    issues: Annotated[list[PlannerIssue], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_controlling_issue(self) -> _PlannerFailureResultBase:
        availability = getattr(self, "availability", None)
        if availability not in {"needs_input", "invalid", "unsupported"}:
            raise ValueError("Failure result must declare a failure availability")
        required_kind = "missing" if availability == "needs_input" else availability
        if not any(issue.kind == required_kind and issue.severity == "error" for issue in self.issues):
            raise ValueError("Failure result must include an error issue matching its availability")
        return self


class PacPlannerNeedsInputResult(_PlannerFailureResultBase):
    result_state: Literal["needs_input"]
    availability: Literal["needs_input"]


class PacPlannerInvalidResult(_PlannerFailureResultBase):
    result_state: Literal["invalid"]
    availability: Literal["invalid"]


class PacPlannerUnsupportedResult(_PlannerFailureResultBase):
    result_state: Literal["unsupported"]
    availability: Literal["unsupported"]


class RebalancerPlannerNeedsInputResult(_PlannerFailureResultBase):
    result_state: Literal["needs_input"]
    availability: Literal["needs_input"]


class RebalancerPlannerInvalidResult(_PlannerFailureResultBase):
    result_state: Literal["invalid"]
    availability: Literal["invalid"]


class RebalancerPlannerUnsupportedResult(_PlannerFailureResultBase):
    result_state: Literal["unsupported"]
    availability: Literal["unsupported"]


class _PacReadyResultBase(AllocationStrictModel):
    operation: Literal["plan"]
    availability: Literal["ready"]
    snapshot: PlannerResultSnapshot
    catalogs: PlannerCatalogs
    provenance: Annotated[list[PlannerProvenance], Field(min_length=1)]
    scenario_basis: PacScenarioBasis
    stop_reason: Literal["completed", "time_limit", "node_limit"]
    solver_evidence: PlannerSolverEvidence
    issues: list[PlannerIssue]

    @model_validator(mode="after")
    def validate_gap_evidence(self) -> _PacReadyResultBase:
        if any(issue.severity == "error" for issue in self.issues):
            raise ValueError("Ready results cannot contain error-severity issues")
        _validate_result_catalogs("PAC", self.catalogs, self.provenance, self.scenario_basis)
        proof = getattr(self, "proof", None)
        deployment = getattr(self, "deployment", None)
        solution = getattr(self, "primary_solution", None)
        _validate_stop_evidence(self.stop_reason, self.solver_evidence)
        _validate_solver_units(self.solver_evidence, self.scenario_basis.valuation_currency)
        _validate_not_proven_issue_binding("PAC", self.scenario_basis.policy, proof, self.issues)
        _validate_optimal_proof_objectives(proof, solution)
        _validate_gap_proof(proof, self.solver_evidence, solution)
        if solution is not None:
            _validate_basis_solution(self.scenario_basis, solution)
            _validate_ready_solution(self.catalogs, self.provenance, self.scenario_basis.valuation_currency, solution)
        if isinstance(deployment, PacDistinctDeployment) and solution is not None:
            _validate_basis_solution(self.scenario_basis, deployment.solution)
            _validate_ready_solution(self.catalogs, self.provenance, self.scenario_basis.valuation_currency, deployment.solution)
            _validate_distinct_deployment(solution, deployment)
        return self


class PacPlannerReadyNoOpResult(_PacReadyResultBase):
    result_state: Literal["ready_no_op"]
    outcome: Literal["no_op"]
    proof: ReadyPlanProof
    primary_solution: PacNoOpSolution
    deployment: PacDeployment


class PacPlannerReadyIncumbentResult(_PacReadyResultBase):
    result_state: Literal["ready_incumbent"]
    outcome: Literal["incumbent_found"]
    proof: ReadyPlanProof
    primary_solution: PacIncumbentSolution
    deployment: PacDeployment


class PacPlannerReadyInfeasibleResult(_PacReadyResultBase):
    result_state: Literal["ready_infeasible"]
    outcome: Literal["infeasible_proven"]
    proof: InfeasibilityProvenProof
    stop_reason: Literal["completed"]


class PacPlannerReadyNoIncumbentResult(_PacReadyResultBase):
    result_state: Literal["ready_no_incumbent"]
    outcome: Literal["no_incumbent"]
    proof: NotProvenProof


class _RebalancerReadyResultBase(AllocationStrictModel):
    operation: Literal["plan"]
    availability: Literal["ready"]
    snapshot: PlannerResultSnapshot
    catalogs: PlannerCatalogs
    provenance: Annotated[list[PlannerProvenance], Field(min_length=1)]
    scenario_basis: RebalancerScenarioBasis
    stop_reason: Literal["completed", "time_limit", "node_limit"]
    solver_evidence: PlannerSolverEvidence
    issues: list[PlannerIssue]

    @model_validator(mode="after")
    def validate_gap_evidence(self) -> _RebalancerReadyResultBase:
        if any(issue.severity == "error" for issue in self.issues):
            raise ValueError("Ready results cannot contain error-severity issues")
        _validate_result_catalogs("Rebalancer", self.catalogs, self.provenance, self.scenario_basis)
        proof = getattr(self, "proof", None)
        deployment = getattr(self, "deployment", None)
        solution = getattr(self, "primary_solution", None)
        _validate_stop_evidence(self.stop_reason, self.solver_evidence)
        _validate_solver_units(self.solver_evidence, self.scenario_basis.valuation_currency)
        _validate_not_proven_issue_binding("Rebalancer", self.scenario_basis.policy, proof, self.issues)
        _validate_optimal_proof_objectives(proof, solution)
        _validate_gap_proof(proof, self.solver_evidence, solution)
        if solution is not None:
            _validate_basis_solution(self.scenario_basis, solution)
            _validate_ready_solution(self.catalogs, self.provenance, self.scenario_basis.valuation_currency, solution)
            _validate_rebalancer_policy_solution(self.scenario_basis.policy, solution)
        if isinstance(deployment, RebalancerDistinctDeployment) and solution is not None:
            _validate_basis_solution(self.scenario_basis, deployment.solution)
            _validate_ready_solution(self.catalogs, self.provenance, self.scenario_basis.valuation_currency, deployment.solution)
            _validate_rebalancer_policy_solution(self.scenario_basis.policy, deployment.solution)
            _validate_distinct_deployment(solution, deployment)
        return self


class RebalancerPlannerReadyNoOpResult(_RebalancerReadyResultBase):
    result_state: Literal["ready_no_op"]
    outcome: Literal["no_op"]
    proof: ReadyPlanProof
    primary_solution: RebalancerNoOpSolution
    deployment: RebalancerDeployment


class RebalancerPlannerReadyIncumbentResult(_RebalancerReadyResultBase):
    result_state: Literal["ready_incumbent"]
    outcome: Literal["incumbent_found"]
    proof: ReadyPlanProof
    primary_solution: RebalancerIncumbentSolution
    deployment: RebalancerDeployment


class RebalancerPlannerReadyInfeasibleResult(_RebalancerReadyResultBase):
    result_state: Literal["ready_infeasible"]
    outcome: Literal["infeasible_proven"]
    proof: InfeasibilityProvenProof
    stop_reason: Literal["completed"]


class RebalancerPlannerReadyNoIncumbentResult(_RebalancerReadyResultBase):
    result_state: Literal["ready_no_incumbent"]
    outcome: Literal["no_incumbent"]
    proof: NotProvenProof


type PacPlannerResult = Annotated[
    Union[
        PacPlannerNeedsInputResult,
        PacPlannerInvalidResult,
        PacPlannerUnsupportedResult,
        PacPlannerReadyNoOpResult,
        PacPlannerReadyIncumbentResult,
        PacPlannerReadyInfeasibleResult,
        PacPlannerReadyNoIncumbentResult,
    ],
    Field(discriminator="result_state"),
]
type RebalancerPlannerResult = Annotated[
    Union[
        RebalancerPlannerNeedsInputResult,
        RebalancerPlannerInvalidResult,
        RebalancerPlannerUnsupportedResult,
        RebalancerPlannerReadyNoOpResult,
        RebalancerPlannerReadyIncumbentResult,
        RebalancerPlannerReadyInfeasibleResult,
        RebalancerPlannerReadyNoIncumbentResult,
    ],
    Field(discriminator="result_state"),
]

PAC_PLAN_INPUT_ADAPTER = TypeAdapter(PacPlannerRequest)
PAC_PLAN_OUTPUT_ADAPTER = TypeAdapter(PacPlannerResult)
REBALANCER_PLAN_INPUT_ADAPTER = TypeAdapter(RebalancerPlannerRequest)
REBALANCER_PLAN_OUTPUT_ADAPTER = TypeAdapter(RebalancerPlannerResult)
