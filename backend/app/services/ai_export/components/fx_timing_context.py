"""Non-predictive FX conversion-timing evidence component for the AI Export runtime.

Owns exactly one NEW component ID, ``fx.timing_context``, that supplies the
`fx.conversion_timing` analysis with **observed-only** timing evidence so an
analyst can frame a conversion decision *without* the runtime ever forecasting a
rate. Every number here is either the exact resolved current rate/date (reused
verbatim from the already-computed ``fx.current_rate`` / ``fx.conversion_provenance``
sibling components - never recomputed) or a pure function of the genuine,
observed daily rate series loaded through
``backend.app.services.ai_export.components.technical_shared.load_fx_rate_series``
(routed through ``backend.app.services.fx.convert_bulk`` - no invented economics).

Design rules (task ``ai-adequacy-v1-remediate-fx``, goal A):

- **Observed-only.** The observed period minimum/maximum, range position,
  distance-to-extreme ratios, 1M/3M/period returns and realized daily-return
  volatility are all computed from *genuine* observations only (a genuine
  observation is one that is neither backward-filled nor carried forward:
  ``not backward_filled and actual_date == requested_date``). A backward-filled
  carry-forward is never treated as a fresh data point, and no future rate is
  ever consulted (the series never extends past ``snapshot_as_of``).
- **No forecast / no predictive band.** This component deliberately emits no
  projected rate, no volatility-scaled confidence interval and no "expected"
  move: the realized volatility is reported as a plain observed ratio, framed
  as historical dispersion, not a forward band.
- **Flat range is explicit.** When every observed rate is identical
  (``observed_maximum == observed_minimum``), the range position is reported as
  ``None`` with ``range_position_unavailable_reason='flat_observed_range'`` -
  never a fabricated 0.5.
- **Partial source history is explicit.** ``source_history`` carries the
  observed/backfilled counts, calendar coverage and an explicit
  ``is_partial_history`` flag + reason whenever the first genuine observation
  starts after ``period_start`` (or no genuine observation exists at all).
- **Neutral-scenario inputs are honestly missing.** Decision-critical inputs and
  execution refinements are reported separately and together through
  ``missing_user_inputs`` rather than silently defaulted.

This module is intentionally NOT wired into
``backend.app.services.ai_export.components.catalog`` (owned by the parent
integration step): see ``FX_TIMING_CONTEXT_COMPONENTS`` and the coordinator
integration note at the bottom of the file.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum
from statistics import pstdev
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.fx_payloads import FxConversionProvenancePayload, FxCurrentRatePayload
from backend.app.services.ai_export.components.resources import FxRateSeriesResource
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.technical_shared import load_fx_rate_series
from backend.app.services.ai_export.components.types import BuildScope, Domain, PeriodBehavior, normalize_currency_code
from backend.app.services.ai_export.dependencies import BuildContext, BuildContextScopeError

# Trailing calendar windows for the observed short-horizon returns. Kept as plain
# Fixed day counts are named as days in the public payload, never as months.
_RETURN_30D_DAYS = 30
_RETURN_91D_DAYS = 91


class FxNeutralScenarioInput(StrEnum):
    """A user input required to frame a *neutral* conversion scenario.

    None of these are ever available inside the AI Export runtime, so
    ``fx.timing_context`` always reports the full set through
    ``FxTimingContextPayload.missing_user_inputs`` instead of silently
    defaulting any of them - the timing evidence is descriptive, never a
    ready-to-execute recommendation.
    """

    CONVERSION_AMOUNT = "conversion_amount"
    CONVERSION_DIRECTION = "conversion_direction"
    CONVERSION_DEADLINE = "conversion_deadline"
    URGENCY = "urgency"
    EXECUTION_PROVIDER = "execution_provider"
    EXECUTION_SPREAD = "execution_spread"
    TRANSACTION_FEES = "transaction_fees"
    MINIMUM_TRADE_AMOUNT = "minimum_trade_amount"
    SETTLEMENT_CONSTRAINTS = "settlement_constraints"
    ACCEPTABLE_SLIPPAGE = "acceptable_slippage"
    LIQUIDITY_REQUIREMENT = "liquidity_requirement"
    STAGED_EXECUTION_FEASIBILITY = "staged_execution_feasibility"


INDISPENSABLE_SCENARIO_INPUTS: tuple[FxNeutralScenarioInput, ...] = (
    FxNeutralScenarioInput.CONVERSION_AMOUNT,
    FxNeutralScenarioInput.CONVERSION_DIRECTION,
    FxNeutralScenarioInput.CONVERSION_DEADLINE,
)
REFINEMENT_SCENARIO_INPUTS: tuple[FxNeutralScenarioInput, ...] = (
    FxNeutralScenarioInput.URGENCY,
    FxNeutralScenarioInput.EXECUTION_PROVIDER,
    FxNeutralScenarioInput.EXECUTION_SPREAD,
    FxNeutralScenarioInput.TRANSACTION_FEES,
    FxNeutralScenarioInput.MINIMUM_TRADE_AMOUNT,
    FxNeutralScenarioInput.SETTLEMENT_CONSTRAINTS,
    FxNeutralScenarioInput.ACCEPTABLE_SLIPPAGE,
    FxNeutralScenarioInput.LIQUIDITY_REQUIREMENT,
    FxNeutralScenarioInput.STAGED_EXECUTION_FEASIBILITY,
)
ALL_NEUTRAL_SCENARIO_INPUTS = INDISPENSABLE_SCENARIO_INPUTS + REFINEMENT_SCENARIO_INPUTS

# Machine-readable reason the observed range position could not be computed.
REASON_FLAT_RANGE = "flat_observed_range"
REASON_NO_OBSERVED_RATES = "no_observed_rates_in_period"

# Machine-readable reason the observed source history is incomplete.
REASON_HISTORY_STARTS_LATE = "source_history_starts_after_period_start"
REASON_NO_GENUINE_OBSERVATIONS = "no_genuine_observations_in_period"


def _validate_finite_positive_decimal(value: Decimal, *, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be a Decimal")
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{field_name} must be a finite, positive Decimal")
    return value


class FxObservedRangePosition(BaseModel):
    """Where the current rate sits inside the observed period min/max envelope.

    ``range_position_ratio`` is a plain 0..1 *range position* (``(current - min) /
    (max - min)``), deliberately **not** a historical percentile/rank: it says
    only how far between the observed extremes the current rate lies, making no
    distributional claim. It is ``None`` (with ``range_position_unavailable_reason``)
    when the observed range is flat or empty. ``distance_to_min_ratio`` /
    ``distance_to_max_ratio`` are non-negative relative gaps (``current/min - 1``
    and ``max/current - 1``) so a reader sees, in fractional terms, how much
    room there is below the current rate to the observed low and above it to the
    observed high.
    """

    model_config = ConfigDict(extra="forbid")

    observed_minimum: Decimal | None = None
    observed_minimum_date: date | None = None
    observed_maximum: Decimal | None = None
    observed_maximum_date: date | None = None
    range_position_ratio: float | None = Field(default=None, ge=0, le=1)
    range_position_unavailable_reason: str | None = None
    distance_to_min_ratio: float | None = Field(default=None, ge=0)
    distance_to_max_ratio: float | None = Field(default=None, ge=0)

    @field_validator("observed_minimum", "observed_maximum")
    @classmethod
    def _validate_extreme(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return _validate_finite_positive_decimal(value, field_name="observed extreme")

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        has_min = self.observed_minimum is not None
        has_max = self.observed_maximum is not None
        if has_min != has_max:
            raise ValueError("observed_minimum and observed_maximum must both be present or both absent")
        if has_min != (self.observed_minimum_date is not None):
            raise ValueError("observed_minimum requires observed_minimum_date and vice versa")
        if has_max != (self.observed_maximum_date is not None):
            raise ValueError("observed_maximum requires observed_maximum_date and vice versa")
        if has_min:
            if self.observed_maximum < self.observed_minimum:
                raise ValueError("observed_maximum must not be below observed_minimum")
            if self.range_position_ratio is None and self.range_position_unavailable_reason is None:
                raise ValueError("an unavailable range_position requires a range_position_unavailable_reason")
            if self.range_position_ratio is not None and self.range_position_unavailable_reason is not None:
                raise ValueError("a resolved range_position must not carry an unavailable reason")
        else:
            if self.range_position_ratio is not None or self.distance_to_min_ratio is not None or self.distance_to_max_ratio is not None:
                raise ValueError("no observed extremes must leave every derived ratio unset")
            if self.range_position_unavailable_reason is None:
                raise ValueError("an empty observed range requires range_position_unavailable_reason")
        return self


class FxObservedReturns(BaseModel):
    """Trailing observed returns and realized dispersion (never a forecast).

    Every value is ``None`` when insufficient genuine observations exist to
    compute it honestly. ``daily_return_volatility_ratio`` is the population
    standard deviation of consecutive genuine daily returns - a purely
    historical dispersion figure, never scaled into a predictive band.
    """

    model_config = ConfigDict(extra="forbid")

    return_30d_ratio: float | None = None
    return_91d_ratio: float | None = None
    return_period_ratio: float | None = None
    daily_return_volatility_ratio: float | None = Field(default=None, ge=0)


class FxSourceHistoryCoverage(BaseModel):
    """Observed calendar coverage + observed/backfilled counts for the visible period.

    Mirrors the semantics of ``backend.app.services.ai_export.runtime_service.
    _fx_history_coverage`` (same observed/backward-filled split and calendar
    coverage ratio) but as a renderer-neutral component sub-payload. ``complete``
    is ``True`` when the requested period is covered from ``period_start``;
    a backward-filled weekend/holiday start remains covered and does not become a
    false source-history gap. ``is_partial_history`` is the exact inverse.
    """

    model_config = ConfigDict(extra="forbid")

    requested_period_start: date
    requested_period_end: date
    available_start: date | None = None
    requested_calendar_days: int = Field(..., ge=1)
    covered_calendar_days: int = Field(..., ge=0)
    coverage_ratio: float = Field(..., ge=0, le=1)
    observed_observation_count: int = Field(..., ge=0)
    backfilled_observation_count: int = Field(..., ge=0)
    earliest_source_date: date | None = None
    complete: bool
    is_partial_history: bool
    partial_history_reason: str | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.requested_period_end < self.requested_period_start:
            raise ValueError("requested_period_end must not precede requested_period_start")
        if self.complete == self.is_partial_history:
            raise ValueError("complete and is_partial_history must be exact opposites")
        if self.is_partial_history and self.partial_history_reason is None:
            raise ValueError("partial history requires partial_history_reason")
        if not self.is_partial_history and self.partial_history_reason is not None:
            raise ValueError("complete history must not carry a partial_history_reason")
        if self.available_start is not None and self.available_start < self.requested_period_start:
            raise ValueError("available_start must not precede requested_period_start")
        return self


class FxTimingContextPayload(BaseModel):
    """`fx.timing_context`: observed, non-predictive conversion-timing evidence.

    The current rate/date/staleness/backfill/provider are reused verbatim from
    the resolved ``fx.current_rate`` / ``fx.conversion_provenance`` siblings; the
    observed range, returns, volatility and coverage are pure functions of the
    genuine observed rate series. There is deliberately no forecast, target or
    predictive band anywhere in this payload.
    """

    model_config = ConfigDict(extra="forbid")

    base_currency: str
    quote_currency: str
    rate_semantics: str = Field(default="quote_currency_per_base_currency", frozen=True)

    as_of: date
    effective_date: date
    current_rate: Decimal = Field(..., description="Quote units per 1 base unit, as of as_of")
    is_backward_filled: bool
    staleness_days: int = Field(ge=0)
    source: str = Field(min_length=1, description="Authoritative FxRate.source backing the current rate (e.g. 'ECB', 'MANUAL')")

    observed_range: FxObservedRangePosition
    observed_returns: FxObservedReturns
    source_history: FxSourceHistoryCoverage
    indispensable_user_inputs: tuple[FxNeutralScenarioInput, ...]
    refinement_user_inputs: tuple[FxNeutralScenarioInput, ...]
    missing_user_inputs: tuple[FxNeutralScenarioInput, ...]

    @field_validator("base_currency", "quote_currency")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_currency_code(value)

    @field_validator("current_rate")
    @classmethod
    def _validate_rate(cls, value: Decimal) -> Decimal:
        return _validate_finite_positive_decimal(value, field_name="current_rate")

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.base_currency == self.quote_currency:
            raise ValueError("base_currency and quote_currency must differ")
        if self.effective_date > self.as_of:
            raise ValueError("effective_date must not be after as_of")
        if self.staleness_days != (self.as_of - self.effective_date).days:
            raise ValueError("staleness_days must equal (as_of - effective_date).days")
        if self.is_backward_filled != (self.staleness_days > 0):
            raise ValueError("is_backward_filled must match staleness_days > 0")
        if len(set(self.missing_user_inputs)) != len(self.missing_user_inputs):
            raise ValueError("missing_user_inputs must be unique")
        if self.missing_user_inputs != self.indispensable_user_inputs + self.refinement_user_inputs:
            raise ValueError("missing_user_inputs must concatenate indispensable_user_inputs and refinement_user_inputs")
        if self.source_history.requested_period_end != self.as_of:
            raise ValueError("source_history.requested_period_end must equal as_of")
        return self


# =============================================================================
# Builder helpers (observed-only math)
# =============================================================================


def _require_fx_scope(context: BuildContext) -> BuildScope:
    scope = context.scope
    if scope is None:
        raise BuildContextScopeError("fx.timing_context requires a BuildContext constructed with a BuildScope")
    if scope.domain is not Domain.FX:
        raise BuildContextScopeError(f"fx.timing_context requires BuildScope.domain == FX, got {scope.domain!r}")
    return scope


def _genuine_observed_points(series: FxRateSeriesResource, *, start: date, end: date) -> tuple[tuple[date, Decimal], ...]:
    """Genuine (non-backfilled, non-carry-forward) observations within [start, end], chronological."""
    return tuple((observation.requested_date, observation.rate) for observation in series.observations if start <= observation.requested_date <= end and not observation.backward_filled and observation.actual_date == observation.requested_date)


def _value_on_or_before(points: Sequence[tuple[date, Decimal]], target: date) -> tuple[date, Decimal] | None:
    candidates = [point for point in points if point[0] <= target]
    return candidates[-1] if candidates else None


def _trailing_return(points: Sequence[tuple[date, Decimal]], *, as_of: date, days: int) -> float | None:
    """Return from the last observed value on-or-before (as_of - days) to the last observed value.

    ``None`` when no observation reaches back to the trailing anchor (the window
    is not yet covered by observed history) or when the two anchors coincide.
    """
    if not points:
        return None
    anchor_date = as_of - timedelta(days=days)
    start = _value_on_or_before(points, anchor_date)
    end = points[-1]
    if start is None or start[0] >= end[0] or start[1] == 0:
        return None
    return float(end[1] / start[1] - 1)


def _period_return(points: Sequence[tuple[date, Decimal]]) -> float | None:
    if len(points) < 2 or points[0][1] == 0:
        return None
    return float(points[-1][1] / points[0][1] - 1)


def _daily_return_volatility(points: Sequence[tuple[date, Decimal]]) -> float | None:
    returns = [float(current[1] / previous[1] - 1) for previous, current in zip(points, points[1:], strict=False) if previous[1] != 0]
    if len(returns) < 2:
        return None
    return pstdev(returns)


def _build_observed_range(points: Sequence[tuple[date, Decimal]], *, current_rate: Decimal) -> FxObservedRangePosition:
    if not points:
        return FxObservedRangePosition(range_position_unavailable_reason=REASON_NO_OBSERVED_RATES)
    minimum_point = min(points, key=lambda item: (item[1], item[0]))
    maximum_point = max(points, key=lambda item: (item[1], item[0]))
    observed_min = minimum_point[1]
    observed_max = maximum_point[1]
    if observed_max == observed_min:
        return FxObservedRangePosition(
            observed_minimum=observed_min,
            observed_minimum_date=minimum_point[0],
            observed_maximum=observed_max,
            observed_maximum_date=maximum_point[0],
            range_position_ratio=None,
            range_position_unavailable_reason=REASON_FLAT_RANGE,
        )
    # `current_rate` is the resolved as-of rate; on a fully-covered period it is
    # itself a genuine observation, so it lies within [min, max]. Clamp only to
    # absorb the last-bucket backfill edge where the as-of rate is carried from
    # the most recent genuine observation (still within the observed envelope).
    raw_position = float((current_rate - observed_min) / (observed_max - observed_min))
    range_position = min(1.0, max(0.0, raw_position))
    distance_to_min = float(current_rate / observed_min - 1) if observed_min > 0 else None
    distance_to_max = float(observed_max / current_rate - 1) if current_rate > 0 else None
    return FxObservedRangePosition(
        observed_minimum=observed_min,
        observed_minimum_date=minimum_point[0],
        observed_maximum=observed_max,
        observed_maximum_date=maximum_point[0],
        range_position_ratio=range_position,
        distance_to_min_ratio=max(0.0, distance_to_min) if distance_to_min is not None else None,
        distance_to_max_ratio=max(0.0, distance_to_max) if distance_to_max is not None else None,
    )


def _build_source_history(series: FxRateSeriesResource, *, scope: BuildScope) -> FxSourceHistoryCoverage:
    visible = tuple(observation for observation in series.observations if scope.period_start <= observation.requested_date <= scope.period_end)
    requested_days = (scope.period_end - scope.period_start).days + 1
    genuine = tuple(observation for observation in visible if not observation.backward_filled and observation.actual_date == observation.requested_date)
    observed_count = len(genuine)
    backfilled_count = len(visible) - observed_count
    available_start = visible[0].requested_date if visible else None
    covered_days = (scope.period_end - available_start).days + 1 if available_start is not None else 0
    earliest_source_date = min((observation.actual_date for observation in series.observations), default=None)
    complete = available_start == scope.period_start
    if complete:
        reason = None
    elif observed_count == 0:
        reason = REASON_NO_GENUINE_OBSERVATIONS
    else:
        reason = REASON_HISTORY_STARTS_LATE
    return FxSourceHistoryCoverage(
        requested_period_start=scope.period_start,
        requested_period_end=scope.period_end,
        available_start=available_start,
        requested_calendar_days=requested_days,
        covered_calendar_days=covered_days,
        coverage_ratio=covered_days / requested_days,
        observed_observation_count=observed_count,
        backfilled_observation_count=backfilled_count,
        earliest_source_date=earliest_source_date,
        complete=complete,
        is_partial_history=not complete,
        partial_history_reason=reason,
    )


def _current_rate_payload(dependencies: Mapping[str, SectionEnvelope]) -> FxCurrentRatePayload:
    envelope = dependencies["fx.current_rate"]
    return FxCurrentRatePayload.model_validate(envelope.payload)


def _conversion_provenance_payload(dependencies: Mapping[str, SectionEnvelope]) -> FxConversionProvenancePayload:
    envelope = dependencies["fx.conversion_provenance"]
    return FxConversionProvenancePayload.model_validate(envelope.payload)


async def _build_fx_timing_context(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> FxTimingContextPayload:
    scope = _require_fx_scope(context)
    current = _current_rate_payload(dependencies)
    provenance = _conversion_provenance_payload(dependencies)
    series = await load_fx_rate_series(context)
    points = _genuine_observed_points(series, start=scope.period_start, end=scope.period_end)

    observed_range = _build_observed_range(points, current_rate=current.rate)
    observed_returns = FxObservedReturns(
        return_30d_ratio=_trailing_return(points, as_of=scope.snapshot_as_of, days=_RETURN_30D_DAYS),
        return_91d_ratio=_trailing_return(points, as_of=scope.snapshot_as_of, days=_RETURN_91D_DAYS),
        return_period_ratio=_period_return(points),
        daily_return_volatility_ratio=_daily_return_volatility(points),
    )
    source_history = _build_source_history(series, scope=scope)

    return FxTimingContextPayload(
        base_currency=scope.base_currency,
        quote_currency=scope.quote_currency,
        as_of=current.requested_date,
        effective_date=current.effective_date,
        current_rate=current.rate,
        is_backward_filled=current.is_backward_filled,
        staleness_days=current.staleness_days,
        source=provenance.source,
        observed_range=observed_range,
        observed_returns=observed_returns,
        source_history=source_history,
        indispensable_user_inputs=INDISPENSABLE_SCENARIO_INPUTS,
        refinement_user_inputs=REFINEMENT_SCENARIO_INPUTS,
        missing_user_inputs=ALL_NEUTRAL_SCENARIO_INPUTS,
    )


# =============================================================================
# ComponentSpec (NOT wired into the shared catalog - parent integration gate)
# =============================================================================
#
# Coordinator integration note (requirement 7):
# - Component tuple to register: FX_TIMING_CONTEXT_COMPONENTS.
# - Proposed catalog placeholder: _component(Domain.FX, "timing_context",
#   "FX non-predictive conversion-timing evidence",
#   dependencies=("fx.current_rate", "fx.conversion_provenance"),
#   period_behavior=PeriodBehavior.WINDOWED). Metadata below is authoritative.
# - Proposed dataset binding: add "fx.timing_context" to the FX conversion-timing
#   dataset alongside fx.current_rate / fx.conversion_provenance / fx.rate_ohlc.
# - Proposed Analysis binding: attach to the `fx.conversion_timing` analysis so
#   its response contract can cite observed range/returns/coverage + the explicit
#   missing_user_inputs list (no forecast contract fields).

FX_TIMING_CONTEXT_SPEC = ComponentSpec(
    component_id="fx.timing_context",
    version=1,
    domains=frozenset({Domain.FX}),
    output_model=FxTimingContextPayload,
    builder=_build_fx_timing_context,
    dependencies=("fx.current_rate", "fx.conversion_provenance"),
    period_behavior=PeriodBehavior.WINDOWED,
)

FX_TIMING_CONTEXT_COMPONENTS: tuple[ComponentSpec, ...] = (FX_TIMING_CONTEXT_SPEC,)


__all__ = [
    "ALL_NEUTRAL_SCENARIO_INPUTS",
    "FX_TIMING_CONTEXT_COMPONENTS",
    "FX_TIMING_CONTEXT_SPEC",
    "INDISPENSABLE_SCENARIO_INPUTS",
    "REFINEMENT_SCENARIO_INPUTS",
    "REASON_FLAT_RANGE",
    "REASON_HISTORY_STARTS_LATE",
    "REASON_NO_GENUINE_OBSERVATIONS",
    "REASON_NO_OBSERVED_RATES",
    "FxNeutralScenarioInput",
    "FxObservedRangePosition",
    "FxObservedReturns",
    "FxSourceHistoryCoverage",
    "FxTimingContextPayload",
]
