"""Canonical JSON and stable token-equivalent utilities for AI Export."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel

__all__ = ["canonical_json", "estimate_tokens_chars_div_4"]


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
        return _normalize_json_value(
            value.model_dump(mode="json", by_alias=True),
            path,
        )
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string key")
            normalized[key] = _normalize_json_value(item, f"{path}.{key}")
        return normalized
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [_normalize_json_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
    raise TypeError(f"{path} contains a non-JSON value of type {type(value).__name__}")


def canonical_json(payload: object) -> str:
    """Serialize deterministic compact UTF-8-friendly JSON."""

    return json.dumps(
        _normalize_json_value(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def estimate_tokens_chars_div_4(serialized_characters: int) -> int:
    if isinstance(serialized_characters, bool) or not isinstance(
        serialized_characters,
        int,
    ):
        raise TypeError("serialized_characters must be an integer")
    if serialized_characters < 0:
        raise ValueError("serialized_characters must be non-negative")
    return (serialized_characters + 3) // 4
