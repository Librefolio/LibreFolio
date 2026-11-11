"""Prepared asset series: valuation and return points and series, the sets the analytics read, and the risk-free reference."""

from __future__ import annotations

import math
from datetime import date
from typing import List, Optional

from pydantic import Field, FiniteFloat, field_validator, model_validator

from backend.app.schemas.common import Currency, DateRangeModel, SafeDecimal, StrictModel
from backend.app.schemas.portfolio.data_quality import DataQualityReport
from backend.app.schemas.risk.vocabulary import RiskReturnBasis
from backend.app.services.financial_math.returns import observations_per_year  # MF-D3: a pure house function, no service


class RiskFreeReference(StrictModel):
    """Deterministic risk-free reference used only by eligible metrics."""

    annual_rate: FiniteFloat = Field(0.0, gt=-1)
    source: str = Field("config", min_length=1)
    currency: str

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return Currency.validate_code(value)


class AssetValuationPoint(StrictModel):
    """One target-currency valuation with price and FX provenance."""

    valuation_date: date
    effective_price_date: date
    is_price_carried_forward: bool
    native_close: SafeDecimal = Field(..., gt=0)
    native_currency: str
    fx_rate: Optional[SafeDecimal] = Field(None, gt=0)
    fx_rate_date: Optional[date] = None
    is_fx_carried_forward: bool = False
    target_close: SafeDecimal = Field(..., gt=0)
    target_currency: str
    price_source: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    @field_validator("native_currency", "target_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return Currency.validate_code(value)

    @model_validator(mode="after")
    def validate_provenance(self) -> AssetValuationPoint:
        if self.effective_price_date > self.valuation_date:
            raise ValueError("effective_price_date cannot follow valuation_date")
        if self.is_price_carried_forward != (self.effective_price_date < self.valuation_date):
            raise ValueError("is_price_carried_forward must match effective_price_date")
        if self.native_currency != self.target_currency and (self.fx_rate is None or self.fx_rate_date is None):
            raise ValueError("converted valuations require fx_rate and fx_rate_date")
        if self.is_fx_carried_forward:
            if self.fx_rate_date is None or self.fx_rate_date >= self.valuation_date:
                raise ValueError("carried FX requires an earlier fx_rate_date")
        return self


class AssetReturnPoint(StrictModel):
    """Simple return derived from two converted valuation points."""

    date: date
    previous_valuation_date: date
    value: FiniteFloat = Field(..., gt=-1)

    @model_validator(mode="after")
    def validate_dates(self) -> AssetReturnPoint:
        if self.previous_valuation_date >= self.date:
            raise ValueError("previous_valuation_date must precede date")
        return self


class AssetValuationSeries(StrictModel):
    """Converted valuation series for one asset on the joint calendar."""

    asset_id: int
    target_currency: str
    points: List[AssetValuationPoint] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @field_validator("target_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return Currency.validate_code(value)

    @model_validator(mode="after")
    def validate_points(self) -> AssetValuationSeries:
        dates = [point.valuation_date for point in self.points]
        if dates != sorted(set(dates)):
            raise ValueError("valuation points must have unique ascending dates")
        if any(point.target_currency != self.target_currency for point in self.points):
            raise ValueError("valuation point target currency must match its series")
        return self


class AssetReturnSeries(StrictModel):
    """Price-only simple-return series for one asset."""

    asset_id: int
    target_currency: str
    return_basis: RiskReturnBasis = RiskReturnBasis.PRICE_ONLY
    points: List[AssetReturnPoint] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @field_validator("target_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return Currency.validate_code(value)

    @model_validator(mode="after")
    def validate_points(self) -> AssetReturnSeries:
        dates = [point.date for point in self.points]
        if dates != sorted(set(dates)):
            raise ValueError("return points must have unique ascending dates")
        return self


class PreparedAssetSeries(StrictModel):
    """Canonical valuation and return series for one asset."""

    valuations: AssetValuationSeries
    returns: AssetReturnSeries
    # The asset's own quote dates inside the requested range, whether or not the joint calendar kept
    # them: a stored carry (a weekend or market-holiday row repeating the close before it) is not one.
    quote_dates: List[date] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_alignment(self) -> PreparedAssetSeries:
        if self.valuations.asset_id != self.returns.asset_id:
            raise ValueError("valuation and return series asset_id must match")
        if self.valuations.target_currency != self.returns.target_currency:
            raise ValueError("valuation and return series currency must match")
        valuation_dates = [point.valuation_date for point in self.valuations.points]
        return_dates = [point.date for point in self.returns.points]
        expected_return_dates = valuation_dates[1:]
        if return_dates != expected_return_dates:
            raise ValueError("returns must be derived from consecutive valuation points")
        for previous, current, return_point in zip(
            valuation_dates[:-1],
            valuation_dates[1:],
            self.returns.points,
            strict=True,
        ):
            if return_point.previous_valuation_date != previous or return_point.date != current:
                raise ValueError("return provenance must match valuation dates")
        return self


class PreparedAssetSeriesSet(StrictModel):
    """Canonical common-calendar series ready for risk analytics."""

    requested_range: DateRangeModel
    baseline_date: Optional[date] = None
    effective_range: Optional[DateRangeModel] = None
    target_currency: str
    series: List[PreparedAssetSeries] = Field(default_factory=list)
    joint_valuation_dates: List[date] = Field(default_factory=list)
    joint_return_dates: List[date] = Field(default_factory=list)
    n_observations: int = Field(0, ge=0)
    calendar_days: int = Field(0, ge=0)
    annualization_factor: Optional[FiniteFloat] = Field(None, gt=0)
    calendar_coverage: FiniteFloat = Field(0.0, ge=0, le=1)
    fresh_quote_coverage: FiniteFloat = Field(0.0, ge=0, le=1)
    data_quality: DataQualityReport = Field(default_factory=DataQualityReport)
    fx_fingerprint: str = Field(..., pattern="^[0-9a-f]{64}$")
    warnings: List[str] = Field(default_factory=list)

    @field_validator("target_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return Currency.validate_code(value)

    @model_validator(mode="after")
    def validate_alignment(self) -> PreparedAssetSeriesSet:  # noqa: C901 — flat invariant raises, no nested logic
        asset_ids = [item.valuations.asset_id for item in self.series]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("prepared asset series must have unique asset IDs")
        if self.joint_valuation_dates != sorted(set(self.joint_valuation_dates)):
            raise ValueError("joint valuation dates must be unique and ascending")
        if self.joint_return_dates != sorted(set(self.joint_return_dates)):
            raise ValueError("joint return dates must be unique and ascending")
        if self.joint_return_dates != self.joint_valuation_dates[1:]:
            raise ValueError("joint return dates must exclude only the valuation baseline")
        if self.n_observations != len(self.joint_return_dates):
            raise ValueError("n_observations must match joint return dates")
        if any([point.valuation_date for point in item.valuations.points] != self.joint_valuation_dates or [point.date for point in item.returns.points] != self.joint_return_dates or item.valuations.target_currency != self.target_currency for item in self.series):
            raise ValueError("every asset series must use the same joint calendar and target currency")
        if self.n_observations == 0:
            if self.calendar_days != 0 or self.annualization_factor is not None or self.effective_range is not None:
                raise ValueError("empty prepared series cannot expose annualization metadata")
            return self
        if self.baseline_date is None or self.effective_range is None:
            raise ValueError("non-empty prepared series requires baseline and effective range")
        if self.effective_range.start != self.joint_return_dates[0] or self.effective_range.end != self.joint_return_dates[-1]:
            raise ValueError("effective_range must match joint return dates")
        expected_days = (self.joint_return_dates[-1] - self.baseline_date).days
        if self.calendar_days != expected_days or self.calendar_days <= 0:
            raise ValueError("calendar_days must span baseline to final return")
        expected_factor = observations_per_year(self.n_observations, self.calendar_days)
        if self.annualization_factor is None or not math.isclose(self.annualization_factor, expected_factor, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("annualization_factor must equal n_observations * 365 / calendar_days")
        return self
