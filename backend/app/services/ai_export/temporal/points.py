"""Typed immutable observation/event models shared by the temporal aggregators.

These are intentionally generic (numeric points, multi-output points, monetary
flow events, discrete events) and carry no Portfolio-performance-specific
semantics — they are a typed seam for later engine integration, not an engine.
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal
from types import MappingProxyType
from typing import Protocol

from pydantic import JsonValue


class Dated(Protocol):
    """Structural type for observation/event models bucketed by their ``date``."""

    date: Date


def _require_date(value: object, label: str = "date") -> Date:
    if type(value) is not Date:
        raise TypeError(f"{label} must be a datetime.date instance")
    return value


def _require_finite_decimal(value: object, label: str = "value") -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{label} must be a Decimal")
    if not value.is_finite():
        raise ValueError(f"{label} must be finite")
    return value


def _freeze_decimal_mapping(values: Mapping[str, Decimal], label: str = "values") -> Mapping[str, Decimal]:
    if not isinstance(values, Mapping):
        raise TypeError(f"{label} must be a mapping")
    frozen: dict[str, Decimal] = {}
    for key, value in values.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{label} keys must be non-empty strings")
        frozen[key] = _require_finite_decimal(value, f"{label}[{key!r}]")
    if not frozen:
        raise ValueError(f"{label} must not be empty")
    return MappingProxyType(frozen)


def _freeze_json_value(value: object, path: str = "payload") -> JsonValue:
    """Recursively validate ``value`` is JSON-safe and freeze it into an immutable shape.

    Rejects non-finite floats and any non-JSON type (Decimal, sets, arbitrary
    objects, ...). Lists/mappings are frozen into ``tuple``/``MappingProxyType``
    so the resulting payload stays immutable, matching the rest of this
    module's frozen dataclasses.
    """

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item, f"{path}[{index}]") for index, item in enumerate(value))
    if isinstance(value, Mapping):
        frozen: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string key")
            frozen[key] = _freeze_json_value(item, f"{path}.{key}")
        return MappingProxyType(frozen)
    raise ValueError(f"{path} contains a non-JSON-safe value of type {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class ObservedPoint:
    """A single observed numeric point (price/FX/other scalar time series)."""

    date: Date
    value: Decimal

    def __post_init__(self) -> None:
        _require_date(self.date)
        _require_finite_decimal(self.value)


@dataclass(frozen=True, slots=True)
class ContinuousMultiOutputPoint:
    """One observation with several named numeric outputs (e.g. a multi-line signal)."""

    date: Date
    values: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        _require_date(self.date)
        object.__setattr__(self, "values", _freeze_decimal_mapping(self.values))


@dataclass(frozen=True, slots=True)
class MonetaryFlowEvent:
    """A dated monetary amount (deposit/withdrawal/dividend/fee/...)."""

    date: Date
    amount: Decimal

    def __post_init__(self) -> None:
        _require_date(self.date)
        _require_finite_decimal(self.amount)


@dataclass(frozen=True, slots=True)
class DiscreteEvent:
    """A dated discrete event preserved verbatim (never averaged/truncated).

    ``dedup_key`` is caller-supplied and deterministic (e.g. a transaction id):
    when two events share the same key, assignment keeps the first-seen one
    and drops the rest, in input order — it never merges/averages payloads.
    ``payload`` is an opaque, caller-defined JSON-safe value (``pydantic.JsonValue``):
    it is recursively validated and frozen (non-finite floats and any
    non-JSON-safe object, e.g. ``Decimal``, are rejected).
    """

    date: Date
    dedup_key: Hashable
    payload: JsonValue

    def __post_init__(self) -> None:
        _require_date(self.date)
        if self.dedup_key is None:
            raise ValueError("dedup_key must not be None")
        try:
            hash(self.dedup_key)
        except TypeError as exc:
            raise TypeError("dedup_key must be hashable") from exc
        object.__setattr__(self, "payload", _freeze_json_value(self.payload))


def sort_by_date[T: Dated](points: Iterable[T]) -> tuple[T, ...]:
    """Return points sorted by ``date`` ascending (stable, does not mutate input)."""

    return tuple(sorted(points, key=lambda point: point.date))
