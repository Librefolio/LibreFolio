"""Strict wire contracts for PAC initial-state analysis, without trade execution."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Union

from pydantic import AfterValidator, ConfigDict, Field, StringConstraints, TypeAdapter

from backend.app.schemas.common import Currency, StrictModel

P1_MAX_ROWS = 32
P1_MAX_CURRENCIES = 4
P1_MAX_ISSUES = 384
P1_MAX_INFO_ISSUES = 80
P1_NUMERIC_POLICY = "pac-initial-state-v1"
P1_RESULT_BYTES = 256 * 1024

_DECIMAL = r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$"
_NONNEGATIVE = r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$"
_POSITIVE = r"^(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)$"
_ISO_DATE = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"


def _unicode_scalar_text(value: str) -> str:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError("Text must contain Unicode scalar values")
    return value


def _quote_basis(value: int) -> int:
    if value not in (1, 100):
        raise ValueError("P1 quote basis must be 1 or 100")
    return value


def _calendar_date(value: str) -> str:
    date.fromisoformat(value)
    return value


def _unique_indices(value: list[int]) -> list[int]:
    if len(value) != len(set(value)):
        raise ValueError("Related row indices must be unique")
    return value


class PacStrictModel(StrictModel):
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
NativeAmount = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=52, pattern=_DECIMAL)]
ReportingAmount = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=80, pattern=_DECIMAL)]
CombinedAmount = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=28, pattern=_DECIMAL)]
RowNumerator = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=96, pattern=_DECIMAL)]
RowDenominator = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=80, pattern=_POSITIVE)]
SquaredNumerator = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=192, pattern=_NONNEGATIVE)]
SquaredDenominator = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=160, pattern=_POSITIVE)]
RatioApproximation = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=36, pattern=_DECIMAL)]
QuoteBasis = Annotated[int, Field(strict=True, json_schema_extra={"enum": [1, 100]}), AfterValidator(_quote_basis)]
RowIndex = Annotated[int, Field(strict=True, ge=0, le=P1_MAX_ROWS - 1)]
GridMode = Literal["whole", "fractional"]


class PacQuoteInput(PacStrictModel):
    raw_price: DraftDecimal | None = Field(None, description="Native-currency price per quote_base_quantity units. A raw draft string, not a parsed float.")
    currency: DraftCurrency | None = Field(None, description="Native ISO 4217 quote currency; this is not the reporting currency.")
    quote_base_quantity: Annotated[int, Field(strict=True)] | None = Field(None, description="Units represented by the raw quote. P1 supports 1 or 100; another positive basis is explicitly unsupported.")
    reference_date: DraftDate | None = Field(None, description="Optional observation date. Missing dates are reported, never replaced by today.")


class PacBuyGridInput(PacStrictModel):
    mode: GridMode | None = Field(None, description="Effective rule supplied by the caller for new purchases only. Existing holdings are never rounded.")
    quantity_step: DraftDecimal | None = Field(None, description="Positive quantity increment; whole mode requires an integer. This is not a monetary quantum.")


class PacAnalyzeRowInput(PacStrictModel):
    row_key: RowKey = Field(description="Stable opaque asset/context identity. The analyzer never parses a broker or joins rows by their names.")
    instrument_key: InstrumentKey = Field(description="Underlying instrument identity across contexts. Targets and tracking remain per row, not per instrument.")
    name: RowName | None = Field(None, description="Display label only; equal labels do not imply equal instruments or rows.")
    initial_quantity: DraftDecimal | None = Field(None, description="Exact opening custody quantity; independent of the new-purchase increment.")
    quote: PacQuoteInput | None = Field(None, description="Explicit native reference quote. No provider or database lookup occurs.")
    target_percent: DraftDecimal | None = Field(None, description="This row's target percentage, 0 to 100. The complete row target vector must total exactly 100.")
    buy_grid: PacBuyGridInput | None = Field(None, description="Caller-supplied effective purchase rule; no Broker configuration is read by this kernel.")


class PacMoneyInput(PacStrictModel):
    currency: DraftCurrency | None = None
    amount: DraftDecimal | None = Field(None, description="Exact native amount. Zero is known zero; null/blank is missing, not zero.")


class PacValuationRateInput(PacStrictModel):
    currency: DraftCurrency | None = None
    rate_to_report: DraftDecimal | None = Field(None, description="Reporting-currency value of one native currency unit. Valuation only: no cash conversion or funding is proposed.")
    reference_date: DraftDate | None = Field(None, description="Optional reference observation date; no wall-clock default.")


class PacAnalyzeInput(PacStrictModel):
    operation: Literal["analyze"]
    report_currency: DraftCurrency | None = Field(None, description="ISO 4217 currency used for reporting values and the current invested-value denominator.")
    as_of_date: DraftDate | None = Field(None, description="Optional scenario reference date; provided observations may not be later. Not inferred from the clock.")
    rows: Annotated[list[PacAnalyzeRowInput], Field(max_length=P1_MAX_ROWS)] = Field(default_factory=list)
    cash_balances: Annotated[list[PacMoneyInput], Field(max_length=P1_MAX_CURRENCIES)] | None = Field(None, description="Closed native existing-cash vector, one entry per currency. Empty means no cash; null means not supplied.")
    contributions: Annotated[list[PacMoneyInput], Field(max_length=P1_MAX_CURRENCIES)] | None = Field(None, description="Closed vector of new contributions, separate from existing cash. Empty means none; null means not supplied.")
    valuation_rates: Annotated[list[PacValuationRateInput], Field(max_length=P1_MAX_CURRENCIES)] = Field(default_factory=list, description="Explicit valuation references. Reporting identity rate is 1; missing foreign rates never default to 1.")


PathField = Literal[
    "report_currency", "as_of_date", "rows", "row_key", "instrument_key", "name", "initial_quantity", "quote", "raw_price", "currency", "quote_base_quantity", "reference_date", "target_percent", "buy_grid", "mode", "quantity_step", "cash_balances", "contributions", "valuation_rates", "amount", "rate_to_report"
]
IssuePath = Annotated[list[Union[PathField, RowIndex]], Field(max_length=4)]
IssueUnit = Literal["quantity", "quote", "rate", "percent", "native_amount"]
FactReason = Literal["input_missing", "input_invalid", "outside_p1_domain", "dependency_unavailable", "zero_initial_invested_value"]
MissingCode = Literal["rows_required", "field_required", "incomplete_decimal", "quote_required", "grid_required", "cash_vector_required", "valuation_rate_required"]
InvalidCode = Literal[
    "invalid_decimal_syntax", "invalid_currency", "invalid_date", "reference_after_asof", "nonpositive_price", "nonpositive_fx_rate", "invalid_quote_basis", "target_percent_out_of_range", "target_total_not_100", "nonpositive_quantity_step", "noninteger_whole_step", "negative_contribution", "duplicate_row_key", "duplicate_currency", "identity_rate_mismatch"
]
UnsupportedCode = Literal["numeric_domain_exceeded", "currency_domain_exceeded", "quote_basis_unsupported", "short_inventory_unsupported", "initial_debt_unsupported"]
InfoCode = Literal["inventory_off_buy_grid", "reference_date_unspecified", "unused_valuation_reference", "identity_rate_redundant"]


class PacIssueParams(PacStrictModel):
    currency: CurrencyCode | None = None
    vector: Literal["cash_balances", "contributions", "valuation_rates"] | None = None
    limit: Annotated[int, Field(strict=True, ge=0, le=512)] | None = None
    allowed_quote_bases: Annotated[list[QuoteBasis], Field(max_length=2)] | None = None
    unit: IssueUnit | None = None


class _IssueBase(PacStrictModel):
    path: IssuePath
    related_row_indices: Annotated[list[RowIndex], Field(max_length=P1_MAX_ROWS, json_schema_extra={"uniqueItems": True}), AfterValidator(_unique_indices)]
    params: PacIssueParams


class PacMissingIssue(_IssueBase):
    kind: Literal["missing"]
    code: MissingCode


class PacInvalidIssue(_IssueBase):
    kind: Literal["invalid"]
    code: InvalidCode


class PacUnsupportedIssue(_IssueBase):
    kind: Literal["unsupported"]
    code: UnsupportedCode


class PacInfoIssue(_IssueBase):
    kind: Literal["info"]
    code: InfoCode


type PacAnalyzeIssue = Annotated[Union[PacMissingIssue, PacInvalidIssue, PacUnsupportedIssue, PacInfoIssue], Field(discriminator="kind")]


class AvailableFact[T](PacStrictModel):
    availability: Literal["available"]
    value: T
    reason_codes: Annotated[list[FactReason], Field(max_length=0)]


class UnavailableFact(PacStrictModel):
    availability: Literal["unavailable"]
    value: None
    reason_codes: Annotated[list[FactReason], Field(min_length=1, max_length=1)]


type Fact[T] = Annotated[Union[AvailableFact[T], UnavailableFact], Field(discriminator="availability")]


class NativeMoney(PacStrictModel):
    currency: CurrencyCode
    amount: NativeAmount


class ReportingMoney(PacStrictModel):
    currency: CurrencyCode
    amount: ReportingAmount


class _RatioBase(PacStrictModel):
    approximation: RatioApproximation
    approximation_decimal_places: Literal[28]
    approximation_exact: bool


class PercentRatio(_RatioBase):
    numerator: RowNumerator
    denominator: RowDenominator
    unit: Literal["percent"]


class GapRatio(_RatioBase):
    numerator: RowNumerator
    denominator: RowDenominator
    unit: Literal["percentage_points"]


class SquaredGapRatio(_RatioBase):
    numerator: SquaredNumerator
    denominator: SquaredDenominator
    unit: Literal["percentage_points_squared"]


class PacAnalyzeRowFacts(PacStrictModel):
    row_index: RowIndex
    row_key: RowKey
    instrument_key: InstrumentKey
    name: RowName | None
    quantity: Fact[CanonicalScalar]
    initial_value_native: Fact[NativeMoney]
    initial_value_reporting: Fact[ReportingMoney]
    current_weight_percent: Fact[PercentRatio]
    target_percent: Fact[CanonicalScalar]
    deviation_pp: Fact[GapRatio]


class CashPoolFacts(PacStrictModel):
    currency: CurrencyCode
    existing_amount: CanonicalScalar
    contribution_amount: CanonicalScalar
    combined_amount: CombinedAmount
    existing_reporting: Fact[ReportingMoney]
    contribution_reporting: Fact[ReportingMoney]
    combined_reporting: Fact[ReportingMoney]


CashPoolList = Annotated[list[CashPoolFacts], Field(max_length=P1_MAX_CURRENCIES)]


class InitialStateTotals(PacStrictModel):
    initial_invested_reporting: Fact[ReportingMoney]
    existing_cash_reporting: Fact[ReportingMoney]
    contributions_reporting: Fact[ReportingMoney]
    cash_plus_contributions_reporting: Fact[ReportingMoney]
    target_total_percent: Fact[CanonicalScalar]
    max_abs_gap_pp: Fact[GapRatio]
    squared_gap_pp2: Fact[SquaredGapRatio]


class NormalizedQuote(PacStrictModel):
    raw_price: CanonicalScalar
    currency: CurrencyCode
    quote_base_quantity: QuoteBasis
    reference_date: ReferenceDate | None


class NormalizedBuyGrid(PacStrictModel):
    mode: GridMode
    quantity_step: CanonicalScalar


class NormalizedInitialRow(PacStrictModel):
    row_key: RowKey
    instrument_key: InstrumentKey
    name: Annotated[RowName, Field(min_length=1)]
    initial_quantity: CanonicalScalar
    quote: NormalizedQuote
    target_percent: CanonicalScalar
    buy_grid: NormalizedBuyGrid


class NormalizedMoney(PacStrictModel):
    currency: CurrencyCode
    amount: CanonicalScalar


class NormalizedValuationRate(PacStrictModel):
    currency: CurrencyCode
    rate_to_report: CanonicalScalar
    reference_date: ReferenceDate | None


class PacNormalizedInitialState(PacStrictModel):
    report_currency: CurrencyCode
    as_of_date: ReferenceDate | None
    rows: Annotated[list[NormalizedInitialRow], Field(min_length=1, max_length=P1_MAX_ROWS)]
    cash_balances: Annotated[list[NormalizedMoney], Field(max_length=P1_MAX_CURRENCIES)]
    contributions: Annotated[list[NormalizedMoney], Field(max_length=P1_MAX_CURRENCIES)]
    valuation_rates: Annotated[list[NormalizedValuationRate], Field(max_length=5)]


class _AnalyzeOutputBase(PacStrictModel):
    operation: Literal["analyze"]
    result_kind: Literal["initial_state_analysis"]
    numeric_policy_id: Literal["pac-initial-state-v1"]
    trade_feasibility: Literal["not_evaluated"] = Field(description="P1 never evaluates or certifies an order proposal.")
    optimization: Literal["not_run"] = Field(description="Initial facts and current row deviations only, not a solver or a no-trade optimum.")
    rows: Annotated[list[PacAnalyzeRowFacts], Field(max_length=P1_MAX_ROWS)]
    cash_pools: Fact[CashPoolList]
    totals: InitialStateTotals


class PacAnalyzeReady(_AnalyzeOutputBase):
    availability: Literal["ready"] = Field(description="Initial state is evaluable. Current targets may be missed, and zero investment has undefined ratios.")
    normalized: PacNormalizedInitialState
    issues: Annotated[list[PacInfoIssue], Field(max_length=P1_MAX_INFO_ISSUES)]


class PacAnalyzeNeedsInput(_AnalyzeOutputBase):
    availability: Literal["needs_input"]
    normalized: None
    issues: Annotated[list[PacAnalyzeIssue], Field(max_length=P1_MAX_ISSUES)]


class PacAnalyzeInvalid(_AnalyzeOutputBase):
    availability: Literal["invalid"]
    normalized: None
    issues: Annotated[list[PacAnalyzeIssue], Field(max_length=P1_MAX_ISSUES)]


class PacAnalyzeUnsupported(_AnalyzeOutputBase):
    availability: Literal["unsupported"]
    normalized: None
    issues: Annotated[list[PacAnalyzeIssue], Field(max_length=P1_MAX_ISSUES)]


type PacAnalyzeOutput = Annotated[Union[PacAnalyzeReady, PacAnalyzeNeedsInput, PacAnalyzeInvalid, PacAnalyzeUnsupported], Field(discriminator="availability")]

PAC_ANALYZE_INPUT_ADAPTER = TypeAdapter(PacAnalyzeInput)
PAC_ANALYZE_OUTPUT_ADAPTER = TypeAdapter(PacAnalyzeOutput)
