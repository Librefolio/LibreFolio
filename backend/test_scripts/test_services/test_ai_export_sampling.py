"""Focused tests for AI Export sampling, precision, and omission utilities."""

from __future__ import annotations

import copy
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from backend.app.schemas.ai_export import AiExportAssetTask, AiExportDetailLevel, AiExportDomain
from backend.app.services.ai_export.models import SamplingSpec
from backend.app.services.ai_export.resolver import resolve_profile
from backend.app.services.ai_export.sampling import (
    NumericPoint,
    omit_empty_technical,
    round_asset_price,
    round_compact_volume,
    round_fx_rate,
    round_money,
    round_oscillator,
    round_percentage,
    sample_and_round_numeric_points,
    sample_numeric_points,
    validate_numeric_points,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "ai_export" / "legacy_semantics"


def _sampling(detail_level: AiExportDetailLevel):
    return resolve_profile(AiExportDomain.ASSET, AiExportAssetTask.ASSET_SNAPSHOT, detail_level).detail_overlay.sampling


def _point(point_date: str | date, value: int | str | Decimal) -> NumericPoint:
    parsed_date = date.fromisoformat(point_date) if isinstance(point_date, str) else point_date
    return NumericPoint(date=parsed_date, value=value if isinstance(value, Decimal) else Decimal(str(value)))


def _fixture_points(raw_points: list[dict[str, object]]) -> tuple[NumericPoint, ...]:
    return tuple(_point(str(item["date"]), Decimal(str(item["value"]))) for item in raw_points)


def test_sampling_fixture_uses_approved_first_point_and_never_synthesizes_dates():
    fixture = json.loads((FIXTURE_DIR / "sampling.v1.json").read_text())
    case = fixture["cases"][0]

    sampled = sample_numeric_points(_fixture_points(case["input"]), _sampling(AiExportDetailLevel.STANDARD))
    sampled_dates = [point.date.isoformat() for point in sampled]
    approved = case["approved_semantics_expected"]

    assert sampled_dates[0] == approved["expected_first_date"]
    assert sampled_dates[-1] == approved["expected_last_date"]
    assert sampled[0].value == Decimal(str(approved["normalization_base"]["value"]))
    assert sampled_dates[0] != case["expected_first_date"]
    assert set(sampled_dates).isdisjoint(case["must_remain_absent"])


def test_normalized_return_fixture_uses_first_observation_on_or_after_window_start():
    fixture = json.loads((FIXTURE_DIR / "normalized_return.v1.json").read_text())
    discrepancy_cases = {case["id"]: case for case in fixture["cases"] if case["classification"] == "known-legacy-discrepancy"}
    assert set(discrepancy_cases) == {"exact_window_start_base_before_sampling", "gap_around_start_uses_previous_observation"}

    for case in discrepancy_cases.values():
        window_start = date.fromisoformat(case["window_start"])
        window_end = date.fromisoformat(case["end_date"])
        observed_in_window = tuple(point for point in _fixture_points(case["prices"]) if window_start <= point.date <= window_end)
        sampled = sample_numeric_points(observed_in_window, _sampling(AiExportDetailLevel.STANDARD))
        approved = case["approved_semantics_expected"]

        if case["id"] == "exact_window_start_base_before_sampling":
            expected_first = approved["first_series_point"]
            assert sampled[0] == _point(expected_first["date"], expected_first["close"])
            assert sampled[-1].date.isoformat() == approved["sampled_last_date"]
        else:
            assert sampled[0] == _point(approved["normalized_return_base_date"], approved["normalized_return_base_price"])
            assert round_percentage((sampled[0].value / sampled[0].value - 1) * 100) == Decimal(str(approved["first_series_return_from_base_pct"])).quantize(Decimal("0.01"))


def test_young_asset_fixture_keeps_observed_base_and_short_history():
    fixture = json.loads((FIXTURE_DIR / "normalized_return.v1.json").read_text())
    case = next(item for item in fixture["cases"] if item["id"] == "young_asset_incomplete_window")

    sampled = sample_numeric_points(_fixture_points(case["prices"]), _sampling(AiExportDetailLevel.STANDARD))

    assert sampled == _fixture_points([{"date": item["date"], "value": item["close"]} for item in case["expected"]["sampled_series"]])
    assert sampled[0].date.isoformat() == case["expected"]["metadata"]["normalized_return_base_date"]


def test_weekend_and_gap_dates_remain_absent():
    points = (
        _point("2026-07-03", 100),
        _point("2026-07-06", 101),
        _point("2026-07-10", 102),
    )

    sampled = sample_numeric_points(points, _sampling(AiExportDetailLevel.STANDARD))

    assert sampled == points
    assert {point.date.isoformat() for point in sampled}.isdisjoint({"2026-07-04", "2026-07-05", "2026-07-07"})


@pytest.mark.parametrize(
    "points",
    (
        (_point("2026-07-26", 1),),
        tuple(_point(date(2026, 7, 20) + timedelta(days=index), index) for index in range(5)),
    ),
)
def test_single_and_short_series_preserve_every_observation(points):
    assert sample_numeric_points(points, _sampling(AiExportDetailLevel.STANDARD)) == points


def test_compact_and_empty_series_return_empty():
    points = (_point("2026-07-25", 1), _point("2026-07-26", 2))

    assert sample_numeric_points(points, _sampling(AiExportDetailLevel.COMPACT)) == ()
    assert sample_numeric_points((), _sampling(AiExportDetailLevel.STANDARD)) == ()


def test_standard_caps_weekly_points_but_full_keeps_full_window():
    weekly = tuple(_point(date(2026, 1, 2) + timedelta(weeks=index), index + 1) for index in range(12))
    recent_start = weekly[-1].date + timedelta(days=3)
    recent = tuple(_point(recent_start + timedelta(days=index), 100 + index) for index in range(7))
    points = (*weekly, *recent)

    standard = sample_numeric_points(points, _sampling(AiExportDetailLevel.STANDARD))
    full = sample_numeric_points(points, _sampling(AiExportDetailLevel.FULL))

    assert standard[0] == weekly[0]
    assert standard[-1] == recent[-1]
    assert len(standard) == 16
    assert tuple(point.date for point in standard[1:9]) == tuple(point.date for point in weekly[-8:])
    assert full == points


def test_weekly_sampling_does_not_emit_partial_split_week_point():
    dates = (
        date(2026, 7, 1),
        date(2026, 7, 2),
        date(2026, 7, 3),
        date(2026, 7, 6),
        date(2026, 7, 7),
        date(2026, 7, 8),
        date(2026, 7, 9),
        date(2026, 7, 10),
        date(2026, 7, 13),
        date(2026, 7, 14),
        date(2026, 7, 15),
        date(2026, 7, 16),
        date(2026, 7, 17),
        date(2026, 7, 20),
        date(2026, 7, 21),
        date(2026, 7, 22),
    )
    points = tuple(NumericPoint(date=point_date, value=Decimal(index)) for index, point_date in enumerate(dates))

    sampled = sample_numeric_points(points, _sampling(AiExportDetailLevel.FULL))
    sampled_dates = {point.date for point in sampled}

    assert date(2026, 7, 13) not in sampled_dates
    assert date(2026, 7, 17) in sampled_dates


def test_sampling_spec_without_weekly_mode_keeps_only_first_recent_and_last():
    points = tuple(_point(date(2026, 1, 2) + timedelta(weeks=index), index) for index in range(5))
    sampling = SamplingSpec(
        include_latest=True,
        include_aggregates=True,
        include_series=True,
        recent_daily_points=2,
        preceding_weekly_points=None,
        weekly_across_technical_window=False,
    )

    assert sample_numeric_points(points, sampling) == (points[0], points[-2], points[-1])


def test_duplicate_and_non_increasing_dates_are_rejected():
    duplicate = (_point("2026-07-25", 1), _point("2026-07-25", 2))
    descending = (_point("2026-07-26", 1), _point("2026-07-25", 2))

    with pytest.raises(ValueError, match="strictly increasing"):
        validate_numeric_points(duplicate)
    with pytest.raises(ValueError, match="strictly increasing"):
        sample_numeric_points(descending, _sampling(AiExportDetailLevel.STANDARD))


@pytest.mark.parametrize("value", (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")))
def test_numeric_point_rejects_non_finite_values(value):
    with pytest.raises(ValueError, match="finite"):
        NumericPoint(date=date(2026, 7, 26), value=value)


def test_numeric_point_is_strictly_decimal_and_immutable():
    with pytest.raises(TypeError, match="Decimal"):
        NumericPoint(date=date(2026, 7, 26), value=1)  # type: ignore[arg-type]

    point = _point("2026-07-26", 1)
    with pytest.raises(AttributeError):
        point.value = Decimal("2")  # type: ignore[misc]


def test_decimal_rounding_rules_cover_ties_negatives_and_currency_minor_units():
    assert round_money(Decimal("1.005")) == Decimal("1.01")
    assert round_money(Decimal("-1.005")) == Decimal("-1.01")
    assert round_money(Decimal("2.5"), minor_units=0) == Decimal("3")
    assert round_money(Decimal("-2.5"), minor_units=0) == Decimal("-3")
    assert round_fx_rate(Decimal("1.2345675")) == Decimal("1.234568")
    assert round_percentage(Decimal("-1.235")) == Decimal("-1.24")
    assert round_oscillator(Decimal("70.005")) == Decimal("70.01")


def test_asset_price_keeps_native_precision_up_to_four_places():
    native = Decimal("123.40")

    assert round_asset_price(native) is native
    assert round_asset_price(native).as_tuple().exponent == -2
    assert round_asset_price(Decimal("123.45678")) == Decimal("123.4568")


def test_volume_rounding_uses_three_significant_digits_for_large_small_and_negative_values():
    assert round_compact_volume(Decimal("12345")) == Decimal("1.23E+4")
    assert round_compact_volume(Decimal("-98765")) == Decimal("-9.88E+4")
    assert round_compact_volume(Decimal("1.23456E+100")) == Decimal("1.23E+100")
    assert round_compact_volume(Decimal("1.23456E-100")) == Decimal("1.23E-100")
    assert round_compact_volume(Decimal("0")) == Decimal("0")


def test_money_rounding_handles_very_large_and_small_decimals_without_float_conversion():
    rounded_large = round_money(Decimal("1.2345E+40"))

    assert rounded_large == Decimal("1.2345E+40")
    assert rounded_large.as_tuple().exponent == -2
    assert round_money(Decimal("1E-40")) == Decimal("0.00")


def test_rounding_rejects_non_finite_values():
    with pytest.raises(ValueError, match="finite"):
        round_money(Decimal("NaN"))
    with pytest.raises(ValueError, match="finite"):
        round_compact_volume(Decimal("Infinity"))


def test_sample_and_round_preserves_sampling_selection_before_precision():
    points = tuple(_point(date(2026, 7, 1) + timedelta(days=index), f"{index + 1}.005") for index in range(10))

    sampled = sample_and_round_numeric_points(points, _sampling(AiExportDetailLevel.STANDARD), round_money)

    assert sampled[0] == _point("2026-07-01", "1.01")
    assert sampled[-1] == _point("2026-07-10", "10.01")
    assert [point.date for point in sampled] == [point.date for point in sample_numeric_points(points, _sampling(AiExportDetailLevel.STANDARD))]


def test_omission_prunes_empty_branches_but_keeps_partial_data_and_owner():
    entity = {
        "asset_id": 7,
        "name": "Partial Asset",
        "technical": {
            "targets": [
                {
                    "target": {"kind": "asset", "asset_id": 7},
                    "signals": [
                        {
                            "instance_id": "rsi_14",
                            "status": "partial",
                            "components": [
                                {"component_code": "rsi", "latest": None, "sampled_points": [{"date": "2026-07-26", "value": "55"}]},
                                {"component_code": "empty", "latest": None, "sampled_points": []},
                            ],
                        },
                        {"instance_id": "empty_signal", "components": []},
                    ],
                },
                {"target": {"kind": "asset", "asset_id": 8}, "signals": []},
            ]
        },
    }
    original = copy.deepcopy(entity)

    pruned = omit_empty_technical(entity)

    assert pruned["asset_id"] == 7
    assert pruned["name"] == "Partial Asset"
    assert len(pruned["technical"]["targets"]) == 1
    signal = pruned["technical"]["targets"][0]["signals"][0]
    assert signal["status"] == "partial"
    assert [component["component_code"] for component in signal["components"]] == ["rsi"]
    assert entity == original


def test_omission_removes_empty_technical_collection_without_dropping_domain_entity():
    entity = {
        "base_currency": "EUR",
        "facts": {"nav": "100"},
        "technical": {"targets": [{"target": {"kind": "portfolio"}, "signals": [{"components": []}]}]},
    }

    assert omit_empty_technical(entity) == {"base_currency": "EUR", "facts": {"nav": "100"}}
