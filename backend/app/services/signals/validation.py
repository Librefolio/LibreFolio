"""Checks on what a signal plugin returns: the output errors, sanitization and normalization, the output contract,
the availability rewrites and the details of a failure."""

from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ValidationError

from backend.app.schemas.signals import (
    SignalAvailability,
    SignalAvailabilityReason,
    SignalComputation,
    SignalPricePoint,
)
from backend.app.services.signals.base import SignalPlugin


class SignalOutputValidationError(ValueError):
    """Raised when plugin output violates canonical LibreFolio contracts."""


class SignalNonFiniteOutputError(SignalOutputValidationError):
    """Raised when plugin output contains positive or negative infinity."""


class SignalOutputContractError(SignalOutputValidationError):
    """Raised when canonical output disagrees with plugin metadata."""


def exception_details(
    exc: Exception,
    *,
    phase: str,
) -> dict[str, Any]:
    details: dict[str, Any] = {
        "phase": phase,
        "exception_type": type(exc).__name__,
        "exception": str(exc),
    }
    if isinstance(exc, ValidationError):
        details["validation_errors"] = json.loads(exc.json(include_url=False))
    return details


def normalize_computation(
    raw_computation: Any,
) -> SignalComputation:
    if isinstance(raw_computation, BaseModel):
        raw_computation = raw_computation.model_dump(mode="python")
    sanitized = sanitize_output(raw_computation)
    return SignalComputation.model_validate(sanitized)


def visible_history_unavailable(
    availability: SignalAvailability,
) -> SignalAvailability:
    data = availability.model_dump(mode="python")
    data.update(
        {
            "can_compute": False,
            "partial_coverage_used": False,
            "reason_code": SignalAvailabilityReason.INSUFFICIENT_HISTORY,
        }
    )
    return SignalAvailability.model_validate(data)


def unavailable_availability(
    availability: SignalAvailability,
    reason: SignalAvailabilityReason,
) -> SignalAvailability:
    data = availability.model_dump(mode="python")
    data.update(
        {
            "can_compute": False,
            "partial_coverage_used": False,
            "reason_code": reason,
        }
    )
    return SignalAvailability.model_validate(data)


def partial_metric_availability(
    availability: SignalAvailability,
) -> SignalAvailability:
    data = availability.model_dump(mode="python")
    data.update(
        {
            "can_compute": True,
            "partial_coverage_used": False,
            "reason_code": (SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC),
        }
    )
    return SignalAvailability.model_validate(data)


def sanitize_output(
    value: Any,
    path: str = "output",
) -> Any:
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            raise SignalNonFiniteOutputError(f"{path} contains infinity")
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            if value.is_nan():
                return None
            raise SignalNonFiniteOutputError(f"{path} contains infinity")
        return value
    if isinstance(value, dict):
        return {key: sanitize_output(item, f"{path}.{key}") for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_output(item, f"{path}[{index}]") for index, item in enumerate(value)]
    return value


def validate_plugin_output(
    plugin_class: type[SignalPlugin],
    computation: SignalComputation,
    selected_points: list[SignalPricePoint],
) -> None:
    expected_specs = plugin_class.output_specs
    if len(computation.series) != len(expected_specs):
        raise SignalOutputContractError("plugin output count does not match output_specs")
    for series, spec in zip(
        computation.series,
        expected_specs,
        strict=True,
    ):
        if (
            series.key != spec.key
            or series.kind != spec.kind
            or series.label_key != spec.label_key
            or series.description_key != spec.description_key
            or series.semantic_id != spec.semantic_id
            or series.semantic_description != spec.semantic_description
            or series.unit != spec.unit
            or series.axis != spec.axis
            or series.view_transform != spec.view_transform
            or series.style != spec.style
        ):
            raise SignalOutputContractError(f"plugin output metadata does not match spec '{spec.key}'")

    if selected_points and plugin_class.input_requirements.price_fields:
        expected_dates = [point.date for point in selected_points]
        expected_date_set = set(expected_dates)
        for series in computation.series:
            actual_dates = [point.date for point in series.points]
            if plugin_class.allows_sparse_output_dates:
                if actual_dates != sorted(set(actual_dates)) or any(date not in expected_date_set for date in actual_dates):
                    raise SignalOutputContractError(f"series '{series.key}' sparse dates must be a sorted unique input subset")
            elif actual_dates != expected_dates:
                raise SignalOutputContractError(f"series '{series.key}' dates/cardinality do not match input")
