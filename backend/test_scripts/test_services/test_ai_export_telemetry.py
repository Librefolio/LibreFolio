"""Focused tests for AI Export canonical serialization and telemetry."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from backend.app.schemas.ai_export import AiExportSampledPoint, AiExportTokenEstimationMethod
from backend.app.services.ai_export.telemetry import (
    SnapshotContentCounts,
    build_export_stats,
    canonical_json,
    count_snapshot_contents,
    estimate_tokens_chars_div_4,
)


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


def test_pydantic_json_serialization_preserves_fixed_point_decimal_behavior():
    point = AiExportSampledPoint(date=date(2026, 7, 26), value=Decimal("1E+5"))

    assert canonical_json(point) == '{"date":"2026-07-26","value":"100000"}'


@pytest.mark.parametrize("value", (float("nan"), float("inf"), Decimal("NaN"), Decimal("Infinity")))
def test_canonical_json_rejects_non_finite_numbers(value):
    with pytest.raises(ValueError, match="non-finite"):
        canonical_json({"value": value})


@pytest.mark.parametrize(
    ("payload", "expected"),
    (
        (
            {
                "domain": "portfolio",
                "facts": {"positions": [{}, {}]},
                "technical": {
                    "targets": [
                        {"signals": [{"components": [{"sampled_points": [{}, {}]}]}]},
                        {"signals": [{"components": [{"sampled_points": [{}]}]}]},
                    ]
                },
                "events": [{}, {}],
            },
            SnapshotContentCounts(positions=2, technical_assets=2, series_points=3, events=2),
        ),
        (
            {
                "domain": "asset",
                "facts": {
                    "current_position": {},
                    "market": {"sampled_prices": [{}, {}]},
                    "normalized_return": {"points": [{}, {}]},
                },
                "technical": {"targets": [{"signals": [{"components": [{"sampled_points": [{}]}]}]}]},
                "events": [{}],
            },
            SnapshotContentCounts(positions=1, technical_assets=1, series_points=5, events=1),
        ),
        (
            {
                "domain": "fx",
                "facts": {"sampled_rates": [{}, {}]},
                "technical": {"targets": [{"signals": [{"components": [{"sampled_points": [{}, {}]}]}]}]},
                "events": [],
            },
            SnapshotContentCounts(positions=0, technical_assets=1, series_points=4, events=0),
        ),
        (
            {
                "domain": "broker",
                "facts": {"positions": [{}]},
                "technical": {"targets": [{"signals": [{"components": [{"latest": {"date": "2026-07-26", "value": "1"}}]}]}]},
                "nested": {"events": [{}]},
            },
            SnapshotContentCounts(positions=1, technical_assets=1, series_points=0, events=1),
        ),
    ),
)
def test_recursive_counts_cover_representative_four_domain_payloads(payload, expected):
    assert count_snapshot_contents(payload) == expected


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


def test_build_export_stats_uses_canonical_character_count_and_typed_method():
    payload = {
        "domain": "portfolio",
        "facts": {"positions": [{}]},
        "technical": {"targets": [{"signals": [{"components": [{"sampled_points": [{}, {}]}]}]}]},
        "events": [{}],
        "label": "Portafoglio €",
    }

    stats = build_export_stats(payload)
    expected_characters = len(canonical_json(payload, exclude_export_stats=True))

    assert stats.canonical_json.positions == 1
    assert stats.canonical_json.technical_assets == 1
    assert stats.canonical_json.series_points == 2
    assert stats.canonical_json.events == 1
    assert stats.canonical_json.serialized_characters == expected_characters
    assert stats.token_estimate.method == AiExportTokenEstimationMethod.CHARS_DIV_4_V1
    assert stats.token_estimate.estimated_tokens == (expected_characters + 3) // 4


def test_export_stats_are_explicitly_excluded_from_self_measurement():
    base = {
        "domain": "asset",
        "facts": {"current_position": {}},
        "events": [],
    }
    first = {**base, "export_stats": {"canonical_json": {"serialized_characters": 1}}}
    second = {**base, "export_stats": {"canonical_json": {"serialized_characters": 999999}, "events": [{}, {}]}}

    assert build_export_stats(first) == build_export_stats(second)
    assert canonical_json(first, exclude_export_stats=True) == canonical_json(base)
    assert '"export_stats"' in canonical_json(first)


def test_export_stats_exclusion_also_prevents_nested_counter_instability():
    payload = {
        "domain": "broker",
        "facts": {"positions": [{}]},
        "export_stats": {
            "positions": [{}, {}, {}],
            "technical": {"targets": [{}, {}]},
            "events": [{}, {}],
        },
    }

    stats = build_export_stats(payload)

    assert stats.canonical_json.positions == 1
    assert stats.canonical_json.technical_assets == 0
    assert stats.canonical_json.events == 0
