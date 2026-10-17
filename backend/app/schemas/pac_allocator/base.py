"""Strict base model and constrained scalars of the PAC/Rebalancer planner contracts: ids, codes, labels, decimals, integers, timestamps, currency and money inputs, issue and reason codes."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field, StringConstraints

from backend.app.schemas.common import Currency, StrictModel

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


class AllocationStrictModel(StrictModel):
    # Input defaults let a caller omit neutral values; the serialization schema still lists
    # every field as required, because results are dumped in full.
    model_config = ConfigDict(strict=True, frozen=True, revalidate_instances="always", json_schema_serialization_defaults_required=True)


CurrencyCode = Annotated[str, StringConstraints(strict=True, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"), AfterValidator(Currency.validate_code)]
ReferenceDate = Annotated[str, StringConstraints(strict=True, min_length=10, max_length=10, pattern=_ISO_DATE), AfterValidator(_calendar_date)]


_PLANNER_FIXED_DECIMAL = r"^(?:0(?:\.[0-9]+)?|[1-9][0-9]*(?:\.[0-9]+)?|-(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*))$"
_PLANNER_INTEGER = r"^(?:0|[1-9][0-9]*|-[1-9][0-9]*)$"
_PLANNER_POSITIVE_INTEGER = r"^[1-9][0-9]*$"
_PLANNER_ID = r"^[A-Za-z0-9][A-Za-z0-9._:@/-]*$"
_PLANNER_CODE = r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$"
_PLANNER_MESSAGE_KEY = r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"
_UTC_TIMESTAMP = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
_JS_SAFE_INTEGER = 9_007_199_254_740_991
PLANNER_FX_PAIR = r"^[A-Z]{3}/[A-Z]{3}$"


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


def planner_canonical_fx_pair(value: str) -> str:
    first, _, second = value.partition("/")
    if first >= second:
        raise ValueError("Canonical FX pair must name two distinct currencies in ascending alphabetical order")
    return value


def require_unique(values: list[object], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def collect_currency_codes(value: object) -> set[str]:
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
    "allocation.currency_mismatch",
    "allocation.deployment_omitted",
    "allocation.duplicate_id",
    "allocation.dynamic_fee_unsupported",
    "allocation.economic_share_out_of_range",
    "allocation.execution_margin_missing",
    "allocation.execution_margin_rate_out_of_range",
    "allocation.exposure_total_exceeds_one",
    "allocation.exposure_weight_out_of_range",
    "allocation.fee_floor_exceeds_cap",
    "allocation.fee_rate_out_of_range",
    "allocation.fee_schedule_missing",
    "allocation.fiscal_currency_missing",
    "allocation.funding_cap_negative",
    "allocation.fx_rate_inconsistent",
    "allocation.fx_rate_missing",
    "allocation.fx_spread_rate_out_of_range",
    "allocation.identity_fx_rate_not_allowed",
    "allocation.invalid_quote_basis",
    "allocation.negative_cash_unsupported",
    "allocation.negative_contribution",
    "allocation.negative_fee_amount",
    "allocation.negative_inventory_unsupported",
    "allocation.no_additional_buy_feasible",
    "allocation.no_positive_order_fundable",
    "allocation.no_selected_funding",
    "allocation.nonpositive_fx_rate",
    "allocation.nonpositive_order_amount_step",
    "allocation.nonpositive_price",
    "allocation.nonpositive_quantity_step",
    "allocation.order_amount_step_missing",
    "allocation.order_cap_nonpositive",
    "allocation.order_minimum_exceeds_cap",
    "allocation.order_minimum_negative",
    "allocation.planning_quantity_negative",
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
    "allocation.solver_limit_no_incumbent",
    "allocation.target_total_not_one",
    "allocation.target_weight_missing",
    "allocation.target_weight_out_of_range",
    "allocation.tax_netting_unsupported",
    "allocation.valuation_currency_missing",
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
PlannerWholeQuantityStep = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=96, pattern=_PLANNER_INTEGER),
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
PlannerConversionMode = Literal["manual", "automatic"]


class PlannerMoneyInput(AllocationStrictModel):
    amount: PlannerFixedDecimal
    currency: CurrencyCode


class PlannerNonNegativeMoneyInput(AllocationStrictModel):
    amount: PlannerNonNegativeDecimal
    currency: CurrencyCode


class PlannerPositiveMoneyInput(AllocationStrictModel):
    amount: PlannerPositiveDecimal
    currency: CurrencyCode
