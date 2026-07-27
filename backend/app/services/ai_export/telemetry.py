"""Deterministic canonical JSON and non-destructive AI Export telemetry."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel

from backend.app.schemas.ai_export import (
    AiExportCanonicalJsonStats,
    AiExportExportStats,
    AiExportTokenEstimate,
    AiExportTokenEstimationMethod,
)

_SERIES_COLLECTION_KEYS = frozenset({"points", "sampled_points", "sampled_prices", "sampled_rates"})


def _normalize_json_value(value: Any, path: str = "$") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"{path} contains a non-finite Decimal")
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _normalize_json_value(value.value, path)
    if isinstance(value, BaseModel):
        return _normalize_json_value(value.model_dump(mode="json", by_alias=True), path)
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string key")
            normalized[key] = _normalize_json_value(item, f"{path}.{key}")
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_json_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
    raise TypeError(f"{path} contains a non-JSON value of type {type(value).__name__}")


def _payload_data(
    payload: BaseModel | Mapping[str, Any],
    *,
    exclude_export_stats: bool,
) -> dict[str, Any]:
    if isinstance(payload, BaseModel):
        exclude = {"export_stats"} if exclude_export_stats else None
        dumped = payload.model_dump(mode="json", by_alias=True, exclude=exclude)
    elif isinstance(payload, Mapping):
        dumped = dict(payload)
        if exclude_export_stats:
            dumped.pop("export_stats", None)
    else:
        raise TypeError("payload must be a Pydantic model or mapping")

    normalized = _normalize_json_value(dumped)
    if not isinstance(normalized, dict):
        raise TypeError("snapshot payload must serialize to a JSON object")
    return normalized


def canonical_json(
    payload: BaseModel | Mapping[str, Any],
    *,
    exclude_export_stats: bool = False,
) -> str:
    """Serialize deterministic compact JSON with model-owned Decimal behavior."""

    data = _payload_data(payload, exclude_export_stats=exclude_export_stats)
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True, slots=True)
class SnapshotContentCounts:
    positions: int = 0
    technical_assets: int = 0
    series_points: int = 0
    events: int = 0


SnapshotCounts = SnapshotContentCounts


def _count_content(value: Any, path: tuple[str, ...], counts: list[int]) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "positions" and isinstance(item, list):
                counts[0] += len(item)
            elif key == "current_position" and isinstance(item, Mapping):
                counts[0] += 1
            elif key == "targets" and isinstance(item, list) and path and path[-1] == "technical":
                counts[1] += len(item)
            elif key in _SERIES_COLLECTION_KEYS and isinstance(item, list):
                counts[2] += len(item)
            elif key == "events" and isinstance(item, list):
                counts[3] += len(item)
            _count_content(item, (*path, key), counts)
    elif isinstance(value, list):
        for item in value:
            _count_content(item, path, counts)


def count_snapshot_contents(payload: BaseModel | Mapping[str, Any]) -> SnapshotContentCounts:
    data = _payload_data(payload, exclude_export_stats=True)
    counts = [0, 0, 0, 0]
    _count_content(data, (), counts)
    return SnapshotContentCounts(
        positions=counts[0],
        technical_assets=counts[1],
        series_points=counts[2],
        events=counts[3],
    )


def estimate_tokens_chars_div_4(serialized_characters: int) -> int:
    if isinstance(serialized_characters, bool) or not isinstance(serialized_characters, int):
        raise TypeError("serialized_characters must be an integer")
    if serialized_characters < 0:
        raise ValueError("serialized_characters must be non-negative")
    return (serialized_characters + 3) // 4


def build_export_stats(payload: BaseModel | Mapping[str, Any]) -> AiExportExportStats:
    """Build stable stats from payload with top-level export_stats excluded."""

    serialized = canonical_json(payload, exclude_export_stats=True)
    counts = count_snapshot_contents(payload)
    serialized_characters = len(serialized)
    return AiExportExportStats(
        canonical_json=AiExportCanonicalJsonStats(
            positions=counts.positions,
            technical_assets=counts.technical_assets,
            series_points=counts.series_points,
            events=counts.events,
            serialized_characters=serialized_characters,
        ),
        token_estimate=AiExportTokenEstimate(
            method=AiExportTokenEstimationMethod.CHARS_DIV_4_V1,
            estimated_tokens=estimate_tokens_chars_div_4(serialized_characters),
        ),
    )
