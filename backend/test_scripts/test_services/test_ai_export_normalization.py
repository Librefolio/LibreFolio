"""Focused tests for pure AI Export normalization and valuation helpers."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from backend.app.schemas.ai_export import (
    AiExportAssetTask,
    AiExportDetailLevel,
    AiExportDomain,
    AiExportNormalizedReturnBaseSource,
    AiExportValuationReferenceSource,
)
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.services.ai_export.models import SamplingSpec
from backend.app.services.ai_export.normalization import (
    ObservedSourcePoint,
    bollinger_percent_b,
    bounded_position_pct,
    build_last_buy_valuation_reference,
    build_last_seed_valuation_reference,
    build_normalized_return,
    relative_distance_pct,
)
from backend.app.services.ai_export.resolver import resolve_profile
from backend.app.services.ai_export.sampling import NumericPoint, round_asset_price, round_decimal_places, sample_numeric_points

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "ai_export" / "legacy_semantics"


def _sampling(detail_level: AiExportDetailLevel) -> SamplingSpec:
    return resolve_profile(AiExportDomain.ASSET, AiExportAssetTask.ASSET_SNAPSHOT, detail_level).detail_overlay.sampling


def _point(point_date: str | date, source_value: int | str | Decimal) -> ObservedSourcePoint:
    parsed_date = date.fromisoformat(point_date) if isinstance(point_date, str) else point_date
    return ObservedSourcePoint(date=parsed_date, source_value=source_value if isinstance(source_value, Decimal) else Decimal(str(source_value)))


def _fixture_points(raw_points: list[dict[str, object]]) -> tuple[ObservedSourcePoint, ...]:
    return tuple(_point(str(item["date"]), Decimal(str(item["value"]))) for item in raw_points)


def _build(
    points: tuple[ObservedSourcePoint | NumericPoint, ...],
    start: str | date,
    end: str | date,
    *,
    detail_level: AiExportDetailLevel = AiExportDetailLevel.STANDARD,
    source_currency: str | None = None,
    source_rounding=round_asset_price,
):
    range_start = date.fromisoformat(start) if isinstance(start, str) else start
    range_end = date.fromisoformat(end) if isinstance(end, str) else end
    return build_normalized_return(
        points,
        DateRangeModel(start=range_start, end=range_end),
        _sampling(detail_level),
        source_currency=source_currency,
        source_rounding=source_rounding,
    )


def test_legacy_normalized_return_fixture_uses_approved_exact_gap_and_young_semantics():
    fixture = json.loads((FIXTURE_DIR / "normalized_return.v1.json").read_text())
    cases = {case["id"]: case for case in fixture["cases"]}

    exact_case = cases["exact_window_start_base_before_sampling"]
    exact = _build(_fixture_points(exact_case["prices"]), exact_case["window_start"], exact_case["end_date"])
    assert exact is not None
    exact_approved = exact_case["approved_semantics_expected"]
    assert exact.base_source == AiExportNormalizedReturnBaseSource.OBSERVED_MARKET_PRICE
    assert exact.base_date.isoformat() == exact_approved["first_series_point"]["date"]
    assert exact.points[0].source_value == Decimal(str(exact_approved["first_series_point"]["close"]))
    assert exact.points[0].return_from_base_pct == 0
    assert exact.points[-1].date.isoformat() == exact_approved["sampled_last_date"]
    assert exact.window_complete is True

    gap_case = cases["gap_around_start_uses_previous_observation"]
    gap = _build(_fixture_points(gap_case["prices"]), gap_case["window_start"], gap_case["end_date"])
    assert gap is not None
    gap_approved = gap_case["approved_semantics_expected"]
    assert gap.base_source == AiExportNormalizedReturnBaseSource.FIRST_OBSERVED_MARKET_PRICE_IN_WINDOW
    assert gap.base_date.isoformat() == gap_approved["normalized_return_base_date"]
    assert gap.base_value == Decimal(str(gap_approved["normalized_return_base_price"]))
    assert gap.points[0].return_from_base_pct == Decimal(str(gap_approved["first_series_return_from_base_pct"]))
    assert gap.window_complete is True

    young_case = cases["young_asset_incomplete_window"]
    young = _build(_fixture_points(young_case["prices"]), young_case["window_start"], young_case["end_date"])
    assert young is not None
    expected = young_case["expected"]
    assert young.base_date.isoformat() == expected["metadata"]["normalized_return_base_date"]
    assert young.base_source == AiExportNormalizedReturnBaseSource.FIRST_OBSERVED_MARKET_PRICE_IN_WINDOW
    assert young.window_complete is False
    assert [(point.date.isoformat(), point.source_value, point.return_from_base_pct) for point in young.points] == [(item["date"], Decimal(str(item["close"])), Decimal(str(item["return_from_base_pct"])).quantize(Decimal("0.01"))) for item in expected["sampled_series"]]


def test_legacy_sampling_fixture_preserves_approved_base_last_and_observed_dates_only():
    fixture = json.loads((FIXTURE_DIR / "sampling.v1.json").read_text())
    case = fixture["cases"][0]
    points = _fixture_points(case["input"])

    result = _build(points, case["options"]["windowStart"], points[-1].date)

    assert result is not None
    approved = case["approved_semantics_expected"]
    sampled_dates = [point.date.isoformat() for point in result.points]
    assert sampled_dates[0] == approved["expected_first_date"]
    assert sampled_dates[-1] == approved["expected_last_date"]
    assert result.points[0].source_value == Decimal(str(approved["normalization_base"]["value"]))
    assert result.points[0].return_from_base_pct == Decimal(str(approved["normalization_base"]["return_from_base_pct"]))
    assert set(sampled_dates).isdisjoint(case["must_remain_absent"])


def test_weekend_gap_history_marks_complete_but_never_becomes_pre_window_base():
    points = (
        _point("2026-07-03", "98"),
        _point("2026-07-06", "100"),
        _point("2026-07-10", "110"),
    )

    result = _build(points, "2026-07-04", "2026-07-10")

    assert result is not None
    assert result.requested_range == DateRangeModel(start=date(2026, 7, 4), end=date(2026, 7, 10))
    assert result.base_date == date(2026, 7, 6)
    assert result.base_value == Decimal("100")
    assert result.points[0].return_from_base_pct == Decimal("0.00")
    assert result.points[-1].return_from_base_pct == Decimal("10.00")
    assert result.window_complete is True
    assert date(2026, 7, 3) not in {point.date for point in result.points}


def test_no_in_window_observation_returns_none_even_with_surrounding_history():
    points = (_point("2026-06-30", "100"), _point("2026-08-01", "110"))

    assert _build(points, "2026-07-01", "2026-07-31") is None


def test_short_standard_history_keeps_every_observed_point():
    points = (_point("2026-07-01", "100"), _point("2026-07-03", "101"), _point("2026-07-08", "102"))

    result = _build(points, points[0].date, points[-1].date)

    assert result is not None
    assert [point.date for point in result.points] == [point.date for point in points]


def test_standard_and_full_use_c4_sampling_while_retaining_base_and_last():
    weekly = tuple(_point(date(2026, 1, 2) + timedelta(weeks=index), index + 1) for index in range(12))
    recent_start = weekly[-1].date + timedelta(days=3)
    recent = tuple(_point(recent_start + timedelta(days=index), 100 + index) for index in range(7))
    points = (*weekly, *recent)

    standard = _build(points, points[0].date, points[-1].date, detail_level=AiExportDetailLevel.STANDARD)
    full = _build(points, points[0].date, points[-1].date, detail_level=AiExportDetailLevel.FULL)

    assert standard is not None
    assert full is not None
    numeric = tuple(NumericPoint(date=point.date, value=point.source_value) for point in points)
    assert [point.date for point in standard.points] == [point.date for point in sample_numeric_points(numeric, _sampling(AiExportDetailLevel.STANDARD))]
    assert [point.date for point in full.points] == [point.date for point in sample_numeric_points(numeric, _sampling(AiExportDetailLevel.FULL))]
    assert len(standard.points) == 16
    assert len(full.points) == len(points)
    assert standard.points[0].date == full.points[0].date == points[0].date
    assert standard.points[-1].date == full.points[-1].date == points[-1].date


def test_raw_return_uses_unrounded_source_values_then_rounds_fixed_point_output():
    points = (_point("2026-07-01", "1.49"), _point("2026-07-02", "2.49"))

    result = _build(points, points[0].date, points[-1].date, source_rounding=lambda value: round_decimal_places(value, 0))

    assert result is not None
    assert result.base_value == Decimal("1")
    assert result.points[-1].source_value == Decimal("2")
    assert result.points[-1].return_from_base_pct == Decimal("67.11")

    fixed = _build((_point("2026-07-01", "1E+5"), _point("2026-07-02", "1.2345E+5")), "2026-07-01", "2026-07-02")
    assert fixed is not None
    payload = fixed.model_dump(mode="json")
    assert payload["base_value"] == "100000"
    assert payload["points"][1]["source_value"] == "123450"
    assert payload["points"][1]["return_from_base_pct"] == "23.45"


def test_source_rounding_runs_only_after_sampling_on_selected_points():
    points = tuple(_point(date(2026, 1, 1) + timedelta(days=index), Decimal(index + 1)) for index in range(40))
    rounded_values: list[Decimal] = []

    def record_rounding(value: Decimal) -> Decimal:
        rounded_values.append(value)
        return value

    result = _build(points, points[0].date, points[-1].date, source_rounding=record_rounding)

    assert result is not None
    expected_dates = [point.date for point in sample_numeric_points(tuple(NumericPoint(date=point.date, value=point.source_value) for point in points), _sampling(AiExportDetailLevel.STANDARD))]
    expected_values = [point.source_value for point in points if point.date in set(expected_dates)]
    assert rounded_values == expected_values
    assert len(rounded_values) < len(points)


def test_negative_returns_source_currency_and_quote_like_values_are_preserved():
    result = _build(
        (_point("2026-07-01", "98.75"), _point("2026-07-02", "101.25"), _point("2026-07-03", "75")),
        "2026-07-01",
        "2026-07-03",
        source_currency=" usd ",
    )

    assert result is not None
    assert result.source_currency == "USD"
    assert result.points[0].source_value == Decimal("98.75")
    assert result.points[1].source_value == Decimal("101.25")
    assert result.points[1].return_from_base_pct == Decimal("2.53")
    assert result.points[-1].return_from_base_pct == Decimal("-24.05")


def test_observed_source_point_is_immutable_positive_finite_and_numeric_point_compatible():
    point = _point("2026-07-01", "100")
    with pytest.raises(AttributeError):
        point.source_value = Decimal("101")  # type: ignore[misc]

    with pytest.raises(TypeError, match="Decimal"):
        ObservedSourcePoint(date=date(2026, 7, 1), source_value=100)  # type: ignore[arg-type]
    for invalid in (Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(ValueError):
            ObservedSourcePoint(date=date(2026, 7, 1), source_value=invalid)

    numeric_points = (
        NumericPoint(date=date(2026, 7, 1), value=Decimal("100")),
        NumericPoint(date=date(2026, 7, 2), value=Decimal("110")),
    )
    result = _build(numeric_points, numeric_points[0].date, numeric_points[-1].date)
    assert result is not None
    assert result.points[-1].return_from_base_pct == Decimal("10.00")

    with pytest.raises(ValueError, match="positive"):
        _build((NumericPoint(date=date(2026, 7, 1), value=Decimal("0")),), "2026-07-01", "2026-07-01")


def test_last_buy_valuation_reference_has_fixed_semantics_and_no_artificial_series():
    reference = build_last_buy_valuation_reference(date(2026, 7, 10), Decimal("102.375"), " chf ")

    assert reference.source == AiExportValuationReferenceSource.LAST_VISIBLE_BUY_UNIT_PRICE
    assert reference.unit_price.code == "CHF"
    assert reference.unit_price.amount == Decimal("102.375")
    assert reference.semantics == "valuation_fallback_not_observed_market_return"
    assert reference.model_dump(mode="json") == {
        "date": "2026-07-10",
        "source": "last_visible_buy_unit_price",
        "unit_price": {"code": "CHF", "amount": "102.375"},
        "effective_unit_price": None,
        "split_adjusted": False,
        "semantics": "valuation_fallback_not_observed_market_return",
    }
    with pytest.raises(ValueError, match="Invalid currency"):
        build_last_buy_valuation_reference(date(2026, 7, 10), Decimal("102.375"), "ZZZ")


def test_last_seed_valuation_reference_has_cost_semantics_and_no_artificial_series():
    reference = build_last_seed_valuation_reference(date(2026, 6, 30), Decimal("98.125"), " usd ")

    assert reference.source == AiExportValuationReferenceSource.LAST_SEED_COST
    assert reference.unit_price.code == "USD"
    assert reference.unit_price.amount == Decimal("98.125")
    assert reference.semantics == "estimated_at_cost_not_observed_market_return"
    assert reference.model_dump(mode="json") == {
        "date": "2026-06-30",
        "source": "last_seed_cost",
        "unit_price": {"code": "USD", "amount": "98.125"},
        "effective_unit_price": None,
        "split_adjusted": False,
        "semantics": "estimated_at_cost_not_observed_market_return",
    }
    with pytest.raises(ValueError, match="Invalid currency"):
        build_last_seed_valuation_reference(date(2026, 6, 30), Decimal("98.125"), "ZZZ")


@pytest.mark.parametrize("unit_price", (Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")))
def test_last_buy_valuation_reference_rejects_non_positive_or_non_finite_price(unit_price):
    with pytest.raises(ValueError):
        build_last_buy_valuation_reference(date(2026, 7, 10), unit_price, "EUR")


@pytest.mark.parametrize("unit_price", (Decimal("-1"), Decimal("NaN"), Decimal("Infinity")))
def test_last_seed_valuation_reference_rejects_negative_or_non_finite_price(unit_price):
    with pytest.raises(ValueError):
        build_last_seed_valuation_reference(date(2026, 7, 10), unit_price, "EUR")


def test_zero_seed_and_split_adjusted_effective_price_are_explicit():
    zero = build_last_seed_valuation_reference(date(2026, 6, 30), Decimal("0"), "EUR")
    adjusted = build_last_seed_valuation_reference(
        date(2026, 6, 30),
        Decimal("100"),
        "USD",
        effective_unit_price=Decimal("50"),
        effective_currency="EUR",
        split_adjusted=True,
    )

    assert zero.unit_price.amount == Decimal("0")
    assert adjusted.unit_price == Currency(code="USD", amount=Decimal("100"))
    assert adjusted.effective_unit_price == Currency(code="EUR", amount=Decimal("50"))
    assert adjusted.split_adjusted is True


def test_split_adjusted_reference_requires_effective_price():
    with pytest.raises(ValueError, match="effective_unit_price"):
        build_last_buy_valuation_reference(date(2026, 7, 10), Decimal("100"), "EUR", split_adjusted=True)


def test_relative_and_bounded_metric_formulas_are_decimal_and_not_clamped():
    assert relative_distance_pct(Decimal("110"), Decimal("100")) == Decimal("10")
    assert relative_distance_pct(Decimal("90"), Decimal("100")) == Decimal("-10")
    assert bounded_position_pct(Decimal("75"), Decimal("50"), Decimal("100")) == Decimal("50")
    assert bounded_position_pct(Decimal("120"), Decimal("50"), Decimal("100")) == Decimal("140")
    assert bollinger_percent_b(Decimal("75"), Decimal("50"), Decimal("100")) == Decimal("50")


def test_metric_helpers_return_none_for_zero_or_invalid_denominators():
    assert relative_distance_pct(Decimal("1"), Decimal("0")) is None
    assert relative_distance_pct(Decimal("1"), Decimal("-0")) is None
    assert bounded_position_pct(Decimal("1"), Decimal("1"), Decimal("1")) is None
    assert bounded_position_pct(Decimal("1"), Decimal("2"), Decimal("1")) is None
    assert bollinger_percent_b(Decimal("1"), Decimal("1"), Decimal("1")) is None
    assert bollinger_percent_b(Decimal("1"), Decimal("2"), Decimal("1")) is None


@pytest.mark.parametrize("invalid", (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")))
def test_metric_helpers_reject_non_finite_inputs(invalid):
    with pytest.raises(ValueError, match="finite"):
        relative_distance_pct(invalid, Decimal("1"))
    with pytest.raises(ValueError, match="finite"):
        relative_distance_pct(Decimal("1"), invalid)
    with pytest.raises(ValueError, match="finite"):
        bounded_position_pct(invalid, Decimal("0"), Decimal("1"))
    with pytest.raises(ValueError, match="finite"):
        bounded_position_pct(Decimal("1"), invalid, Decimal("2"))
    with pytest.raises(ValueError, match="finite"):
        bollinger_percent_b(Decimal("1"), Decimal("0"), invalid)
