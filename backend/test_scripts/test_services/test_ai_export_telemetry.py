"""Tests for live AI Export canonical JSON and token estimation utilities."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

import pytest
from pydantic import BaseModel

from backend.app.schemas.common import SafeDecimal
from backend.app.services.ai_export.telemetry import (
    canonical_json,
    estimate_tokens_chars_div_4,
)


class _Code(StrEnum):
    VALUE = "value"


class _Payload(BaseModel):
    day: date
    amount: SafeDecimal
    code: _Code


def test_canonical_json_is_deterministic_across_mapping_insertion_order():
    first = {
        "z": 1,
        "a": {
            "text": "café €",
            "amount": Decimal("1E-7"),
        },
    }
    second = {
        "a": {
            "amount": Decimal("0.0000001"),
            "text": "café €",
        },
        "z": 1,
    }

    serialized = canonical_json(first)

    assert serialized == canonical_json(second)
    assert serialized == '{"a":{"amount":"0.0000001","text":"café €"},"z":1}'
    assert "\\u" not in serialized


def test_canonical_json_normalizes_models_dates_decimals_and_enums():
    payload = _Payload(
        day=date(2026, 7, 26),
        amount=Decimal("1E+5"),
        code=_Code.VALUE,
    )

    assert canonical_json(payload) == '{"amount":"100000","code":"value","day":"2026-07-26"}'


@pytest.mark.parametrize(
    "value",
    (
        float("nan"),
        float("inf"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ),
)
def test_canonical_json_rejects_non_finite_numbers(value):
    with pytest.raises(ValueError, match="non-finite"):
        canonical_json({"value": value})


def test_canonical_json_rejects_non_string_keys_and_unknown_objects():
    with pytest.raises(ValueError, match="non-string key"):
        canonical_json({1: "value"})
    with pytest.raises(TypeError, match="non-JSON value"):
        canonical_json({"value": object()})


@pytest.mark.parametrize(
    ("characters", "tokens"),
    (
        (0, 0),
        (1, 1),
        (4, 1),
        (5, 2),
        (17, 5),
    ),
)
def test_chars_div_4_token_estimate_uses_ceiling(characters, tokens):
    assert estimate_tokens_chars_div_4(characters) == tokens


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (True, TypeError),
        (-1, ValueError),
        (1.5, TypeError),
        ("4", TypeError),
    ),
)
def test_token_estimate_rejects_invalid_counts(value, expected):
    with pytest.raises(expected):
        estimate_tokens_chars_div_4(value)
