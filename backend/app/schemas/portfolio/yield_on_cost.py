"""Yield on cost: the result of one holding, its status, why it is unavailable and the FX it used."""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from enum import StrEnum
from typing import List, Literal, Optional

from pydantic import Field, field_validator, model_validator

from backend.app.schemas.common import Currency, SafeDecimal, StrictModel


class YieldOnCostStatus(StrEnum):
    """Availability state for a holding's trailing-365-day Yield on Cost."""

    AVAILABLE = "available"
    NO_INCOME = "no_income"
    UNAVAILABLE = "unavailable"


class YieldOnCostUnavailableReason(StrEnum):
    """Why a holding's Yield on Cost cannot be computed."""

    INSUFFICIENT_HISTORY = "insufficient_history"
    INCOME_WITHOUT_ELIGIBLE_QUANTITY = "income_without_eligible_quantity"
    REPLAY_INCONSISTENT = "replay_inconsistent"
    INVALID_SPLIT = "invalid_split"
    MISSING_FX = "missing_fx"
    MISSING_WAC = "missing_wac"
    NON_POSITIVE_WAC = "non_positive_wac"
    NEGATIVE_NET_INCOME = "negative_net_income"


class YieldOnCostFxProvenance(StrictModel):
    """One historical FX observation used by the Yield on Cost calculation."""

    purpose: Literal["income", "wac"]
    requested_date: date_type
    rate_date: date_type
    from_currency: str
    to_currency: str
    days_back: int = Field(..., ge=0)
    stale: bool = Field(False, description="The stored rate row is older than the stale threshold on the requested day: a notice, the value is the same (CP-11a)")

    @field_validator("from_currency", "to_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return Currency.validate_code(value)


class YieldOnCostProvenance(StrictModel):
    """Auditable source and window metadata for one holding's Yield on Cost."""

    source: Literal["transactions"] = "transactions"
    window_start: date_type
    window_end: date_type
    first_pair_transaction_date: Optional[date_type] = None
    gross_income_transaction_count: int = Field(0, ge=0)
    gross_income_per_unit: Optional[Currency] = None
    net_zero: bool = False
    fx: List[YieldOnCostFxProvenance] = Field(default_factory=list)
    issue_date: Optional[date_type] = None
    issue_pair: Optional[str] = None


class YieldOnCostResult(StrictModel):
    """Trailing-365-day gross income per unit divided by residual unit WAC."""

    status: YieldOnCostStatus
    value: Optional[SafeDecimal] = Field(None, description="Yield on Cost as a fraction; 0.04 means 4%.")
    reason: Optional[YieldOnCostUnavailableReason] = None
    provenance: YieldOnCostProvenance

    @model_validator(mode="after")
    def validate_status_contract(self) -> YieldOnCostResult:
        if self.status == YieldOnCostStatus.AVAILABLE:
            self._validate_available()
        elif self.status == YieldOnCostStatus.NO_INCOME:
            self._validate_no_income()
        elif self.status == YieldOnCostStatus.UNAVAILABLE:
            self._validate_unavailable()

        return self

    def _validate_available(self) -> None:
        if self.value is None or self.value < 0 or self.reason is not None:
            raise ValueError("available Yield on Cost requires a non-negative value and forbids reason")
        if self.provenance.gross_income_transaction_count == 0:
            raise ValueError("available Yield on Cost requires at least one income transaction")
        if self.provenance.gross_income_per_unit is None or self.provenance.gross_income_per_unit.amount < 0:
            raise ValueError("available Yield on Cost requires non-negative gross income per unit")

    def _validate_no_income(self) -> None:
        if self.value != Decimal("0") or self.reason is not None:
            raise ValueError("no_income Yield on Cost requires value=0 and forbids reason")
        if self.provenance.gross_income_transaction_count != 0:
            raise ValueError("no_income Yield on Cost cannot contain income transactions")
        if self.provenance.gross_income_per_unit is None or self.provenance.gross_income_per_unit.amount != Decimal("0"):
            raise ValueError("no_income Yield on Cost requires zero gross income per unit")

    def _validate_unavailable(self) -> None:
        if self.value is not None or self.reason is None:
            raise ValueError("unavailable Yield on Cost requires reason and forbids value")

    @model_validator(mode="after")
    def validate_net_zero_contract(self) -> YieldOnCostResult:
        expected = self.status == YieldOnCostStatus.AVAILABLE and self.value == Decimal("0")
        if self.provenance.net_zero != expected:
            raise ValueError("net_zero must identify an available zero with recorded income")
        return self
