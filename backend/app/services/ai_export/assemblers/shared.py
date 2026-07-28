"""Shared construction helpers for AI Export domain assemblers."""

from __future__ import annotations

import calendar
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from types import MappingProxyType

from pydantic import BaseModel

from backend.app.schemas.ai_export import (
    AiExportCanonicalJsonStats,
    AiExportCurrencySemantics,
    AiExportExportStats,
    AiExportMethodology,
    AiExportMetricSemantic,
    AiExportSemantics,
    AiExportSignalSemantic,
    AiExportSnapshotMeta,
    AiExportTokenEstimate,
    AiExportTokenEstimationMethod,
)
from backend.app.schemas.common import DateRangeModel
from backend.app.services.ai_export.models import ResolvedProfile
from backend.app.services.ai_export.service import AiExportPreparedRequest
from backend.app.services.ai_export.telemetry import build_export_stats

Clock = Callable[[], datetime]


class AiExportAssemblerError(RuntimeError):
    """Base typed assembler failure with stable machine-readable context."""

    error_code = "assembler_error"

    def __init__(self, message: str, *, context: Mapping[str, object] | None = None) -> None:
        self.context = MappingProxyType(dict(context or {}))
        super().__init__(message)


class AiExportEntityNotFoundError(AiExportAssemblerError):
    """Requested entity is absent or unavailable in the authenticated scope."""

    error_code = "entity_not_found"

    def __init__(
        self,
        entity_type: str,
        entity_id: int | str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        details = {"entity_type": entity_type, "entity_id": entity_id, **dict(context or {})}
        super().__init__(f"{entity_type} {entity_id} was not found", context=details)


class AiExportTaskNotApplicableError(AiExportAssemblerError):
    """Requested task has no truthful result for the selected entity/scope."""

    error_code = "task_not_applicable"

    def __init__(
        self,
        applicability_code: str,
        reason_code: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        self.applicability_code = applicability_code
        self.reason_code = reason_code
        details = {
            "applicability_code": applicability_code,
            "reason_code": reason_code,
            **dict(context or {}),
        }
        super().__init__(
            f"AI Export task is not applicable: {reason_code}",
            context=details,
        )


class AiExportSourceFailureError(AiExportAssemblerError):
    """A required internal source failed or returned unusable data."""

    error_code = "source_failure"

    def __init__(
        self,
        source_code: str,
        operation: str,
        *,
        retryable: bool = False,
        context: Mapping[str, object] | None = None,
    ) -> None:
        self.source_code = source_code
        self.operation = operation
        self.retryable = retryable
        details = {
            "source_code": source_code,
            "operation": operation,
            "retryable": retryable,
            **dict(context or {}),
        }
        super().__init__(
            f"AI Export source failed: {source_code}.{operation}",
            context=details,
        )


@dataclass(frozen=True, slots=True)
class AiExportResolvedRanges:
    """Inclusive selected, technical, and calculation ranges."""

    snapshot_as_of: date
    selected_range: DateRangeModel
    technical_window: DateRangeModel
    calculation_range: DateRangeModel
    calculation_warmup_start: date


def utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def subtract_calendar_months(value: date, months: int) -> date:
    """Subtract whole calendar months, clamping to the destination month."""

    if isinstance(months, bool) or not isinstance(months, int):
        raise TypeError("months must be an integer")
    if months < 0:
        raise ValueError("months must be non-negative")
    month_index = value.year * 12 + value.month - 1 - months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def resolve_selected_range(prepared: AiExportPreparedRequest) -> tuple[DateRangeModel, date]:
    request_range = prepared.request.date_range
    resolved_end = request_range.end or request_range.start
    selected = DateRangeModel(start=request_range.start, end=resolved_end)
    return selected, resolved_end


def default_technical_window(snapshot_as_of: date) -> DateRangeModel:
    return DateRangeModel(
        start=subtract_calendar_months(snapshot_as_of, 3),
        end=snapshot_as_of,
    )


def resolve_ranges(
    prepared: AiExportPreparedRequest,
    *,
    calculation_range: DateRangeModel | None = None,
    calculation_warmup_start: date | None = None,
) -> AiExportResolvedRanges:
    selected, snapshot_as_of = resolve_selected_range(prepared)
    requested_technical = prepared.request.technical_window
    technical = (
        DateRangeModel(
            start=requested_technical.start,
            end=requested_technical.end or requested_technical.start,
        )
        if requested_technical is not None
        else default_technical_window(snapshot_as_of)
    )
    calculation = calculation_range or technical
    warmup_start = calculation_warmup_start or calculation.start
    return AiExportResolvedRanges(
        snapshot_as_of=snapshot_as_of,
        selected_range=selected,
        technical_window=technical,
        calculation_range=calculation,
        calculation_warmup_start=warmup_start,
    )


def build_snapshot_meta(
    prepared: AiExportPreparedRequest,
    ranges: AiExportResolvedRanges,
    *,
    clock: Clock = utc_now,
) -> AiExportSnapshotMeta:
    profile = prepared.resolved_profile
    return AiExportSnapshotMeta(
        schema_version=profile.schema_version,
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        frontend_response_contract_id=profile.frontend_response_contract_id,
        frontend_response_contract_version=profile.frontend_response_contract_version,
        generated_at=_utc_datetime(clock()),
        snapshot_as_of=ranges.snapshot_as_of,
        selected_range=ranges.selected_range,
        technical_window=ranges.technical_window,
        calculation_range=ranges.calculation_range,
        calculation_warmup_start=ranges.calculation_warmup_start,
        target_currency=prepared.request.target_currency,
    )


def build_methodology(
    *,
    uses_weighted_average_cost: bool = False,
    uses_runtime_fifo: bool = False,
    uses_portfolio_cash_decomposition: bool = False,
) -> AiExportMethodology:
    return AiExportMethodology(
        position_cost_basis_method=("weighted_average_cost" if uses_weighted_average_cost else None),
        position_cost_basis_is_not_market_price=(True if uses_weighted_average_cost else None),
        lot_matching_method="runtime_fifo" if uses_runtime_fifo else None,
        cash_decomposition_source=("portfolio_engine" if uses_portfolio_cash_decomposition else None),
    )


def build_semantics(
    *,
    metric_semantics: Sequence[AiExportMetricSemantic] = (),
    signal_semantics: Sequence[AiExportSignalSemantic] = (),
    trading_currency: str | None,
    valuation_currency: str,
    underlying_currency_exposure_available: bool = False,
) -> AiExportSemantics:
    metrics = sorted(metric_semantics, key=lambda item: item.metric_code)
    signals = sorted(signal_semantics, key=lambda item: item.semantic_id)
    return AiExportSemantics(
        metric_semantics=metrics,
        signal_semantics=signals,
        currency_semantics=AiExportCurrencySemantics(
            trading_currency=trading_currency,
            valuation_currency=valuation_currency,
            underlying_currency_exposure_available=(underlying_currency_exposure_available),
        ),
    )


def neutral_export_stats() -> AiExportExportStats:
    return AiExportExportStats(
        canonical_json=AiExportCanonicalJsonStats(serialized_characters=0),
        token_estimate=AiExportTokenEstimate(
            method=AiExportTokenEstimationMethod.CHARS_DIV_4_V1,
            estimated_tokens=0,
        ),
    )


def finalize_response[SnapshotResponseT: BaseModel](
    response: SnapshotResponseT,
) -> SnapshotResponseT:
    """Replace neutral typed stats with deterministic final telemetry."""

    return response.model_copy(
        update={"export_stats": build_export_stats(response)},
        deep=True,
    )


def profile_allows(profile: ResolvedProfile, section: str) -> bool:
    return section in profile.required_sections or section in profile.optional_sections


def profile_requires(profile: ResolvedProfile, section: str) -> bool:
    return section in profile.required_sections


__all__ = [
    "AiExportAssemblerError",
    "AiExportEntityNotFoundError",
    "AiExportResolvedRanges",
    "AiExportSourceFailureError",
    "AiExportTaskNotApplicableError",
    "Clock",
    "build_methodology",
    "build_semantics",
    "build_snapshot_meta",
    "default_technical_window",
    "finalize_response",
    "neutral_export_stats",
    "profile_allows",
    "profile_requires",
    "resolve_ranges",
    "resolve_selected_range",
    "subtract_calendar_months",
    "utc_now",
]
