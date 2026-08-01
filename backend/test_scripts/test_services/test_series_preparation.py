"""Mathematical tests for canonical converted-price and return preparation."""

from datetime import date
from decimal import Decimal

import pytest

from backend.app.db.models import PriceHistory
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio import (
    DataQualityExclusionReason,
    DataQualityStatus,
)
from backend.app.schemas.prices import (
    AssetBackwardFillInfo,
    FAPricePoint,
    FAPriceQueryResult,
)
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.series_preparation import (
    observed_annualization,
    prepare_asset_series_set,
)


def converted_point(
    point_date: date,
    *,
    native_close: str,
    target_close: str,
    effective_price_date: date | None = None,
    fx_rate_date: date | None = None,
    source: str = "fixture",
) -> FAPricePoint:
    effective = effective_price_date or point_date
    fx_date = fx_rate_date or point_date
    needs_info = effective != point_date or fx_date != point_date
    return FAPricePoint(
        date=point_date,
        close=Decimal(target_close),
        currency="EUR",
        original_close=Decimal(native_close),
        original_currency="USD",
        source_plugin_key=source,
        backward_fill_info=(
            AssetBackwardFillInfo(
                actual_rate_date=effective,
                days_back=(point_date - effective).days,
                fx_rate_date=fx_date,
                fx_days_back=(point_date - fx_date).days,
            )
            if needs_info
            else None
        ),
    )


def native_point(
    point_date: date,
    close: str,
    *,
    effective_price_date: date | None = None,
    source: str = "fixture",
) -> FAPricePoint:
    effective = effective_price_date or point_date
    return FAPricePoint(
        date=point_date,
        close=Decimal(close),
        currency="EUR",
        source_plugin_key=source,
        backward_fill_info=(
            AssetBackwardFillInfo(
                actual_rate_date=effective,
                days_back=(point_date - effective).days,
            )
            if effective != point_date
            else None
        ),
    )


def fixture_results(*, include_failed_fx: bool = False) -> list[FAPriceQueryResult]:
    day_0 = date(2026, 1, 2)
    day_1 = date(2026, 1, 3)
    day_2 = date(2026, 1, 4)
    day_3 = date(2026, 1, 5)
    day_4 = date(2026, 1, 6)

    equity_day_2 = (
        FAPricePoint(
            date=day_2,
            close=Decimal("100"),
            currency="USD",
            source_plugin_key="equity",
        )
        if include_failed_fx
        else converted_point(
            day_2,
            native_close="100",
            target_close="91",
            effective_price_date=day_0,
            fx_rate_date=day_1,
            source="equity",
        )
    )
    equity = FAPriceQueryResult(
        asset_id=1,
        prices=[
            converted_point(day_0, native_close="100", target_close="90", source="equity"),
            converted_point(
                day_1,
                native_close="100",
                target_close="91",
                effective_price_date=day_0,
                source="equity",
            ),
            equity_day_2,
            converted_point(
                day_3,
                native_close="102",
                target_close="93.84",
                fx_rate_date=day_2,
                source="equity",
            ),
            converted_point(
                day_4,
                native_close="102",
                target_close="93.84",
                effective_price_date=day_3,
                fx_rate_date=day_3,
                source="equity",
            ),
        ],
        errors=["USD/EUR unavailable on 2026-01-04"] if include_failed_fx else [],
    )
    crypto = FAPriceQueryResult(
        asset_id=2,
        prices=[
            native_point(day_0, "200", source="crypto"),
            native_point(day_1, "210", source="crypto"),
            native_point(day_2, "220", source="crypto"),
            native_point(day_3, "230", source="crypto"),
            native_point(day_4, "230", effective_price_date=day_3, source="crypto"),
        ],
    )
    return [equity, crypto]


def test_joint_calendar_converts_before_returns_and_tracks_carry():
    prepared = prepare_asset_series_set(
        fixture_results(),
        requested_range=DateRangeModel(
            start=date(2026, 1, 3),
            end=date(2026, 1, 6),
        ),
        target_currency="EUR",
    )

    assert prepared.joint_valuation_dates == [
        date(2026, 1, 2),
        date(2026, 1, 3),
        date(2026, 1, 4),
        date(2026, 1, 5),
    ]
    assert prepared.joint_return_dates == [
        date(2026, 1, 3),
        date(2026, 1, 4),
        date(2026, 1, 5),
    ]
    assert prepared.n_observations == 3
    assert prepared.calendar_days == 3
    assert prepared.annualization_factor == pytest.approx(365.0)
    assert prepared.calendar_coverage == pytest.approx(1.0)
    assert prepared.fresh_quote_coverage == pytest.approx(4 / 6)
    assert prepared.data_quality.data_quality_status == DataQualityStatus.CARRIED_FORWARD
    assert prepared.data_quality.carried_forward_price_points == 2
    assert prepared.data_quality.carried_forward_fx_points == 2
    assert prepared.data_quality.carried_forward_price_asset_ids == [1]
    assert prepared.data_quality.carried_forward_fx_pairs == ["USD/EUR"]

    equity = prepared.series[0]
    assert equity.valuations.points[0].price_source == "equity"
    assert equity.returns.points[0].value == pytest.approx(float(Decimal("91") / Decimal("90") - Decimal("1")))
    assert equity.returns.points[0].value != 0.0
    assert equity.returns.points[1].value == 0.0
    assert equity.valuations.points[-1].is_price_carried_forward is False
    assert equity.valuations.points[-1].is_fx_carried_forward is True


def test_missing_fx_date_is_excluded_without_filling_returns():
    prepared = prepare_asset_series_set(
        fixture_results(include_failed_fx=True),
        requested_range=DateRangeModel(
            start=date(2026, 1, 3),
            end=date(2026, 1, 5),
        ),
        target_currency="EUR",
    )

    assert prepared.joint_return_dates == [
        date(2026, 1, 3),
        date(2026, 1, 5),
    ]
    assert prepared.data_quality.incomplete_valuation_dates == [date(2026, 1, 4)]
    assert prepared.data_quality.unresolved_fx_pairs == ["USD/EUR"]
    assert prepared.data_quality.data_quality_status == DataQualityStatus.PARTIAL
    assert prepared.calendar_coverage == pytest.approx(2 / 3)
    assert prepared.series[0].returns.points[-1].previous_valuation_date == date(2026, 1, 3)


def test_unusable_asset_is_explicitly_excluded_and_does_not_change_calendar():
    results = [
        *fixture_results(),
        FAPriceQueryResult(asset_id=3),
    ]
    prepared = prepare_asset_series_set(
        results,
        requested_range=DateRangeModel(
            start=date(2026, 1, 3),
            end=date(2026, 1, 5),
        ),
        target_currency="EUR",
    )

    assert [item.valuations.asset_id for item in prepared.series] == [1, 2]
    assert prepared.data_quality.data_quality_status == DataQualityStatus.PARTIAL
    assert prepared.data_quality.unusable_assets[0].asset_id == 3
    assert prepared.data_quality.unusable_assets[0].reason == DataQualityExclusionReason.MISSING_PRICE


def test_short_history_uses_effective_baseline_without_marking_partial():
    results = [
        FAPriceQueryResult(
            asset_id=1,
            prices=[
                native_point(date(2026, 1, 3), "100"),
                native_point(date(2026, 1, 4), "101"),
                native_point(date(2026, 1, 5), "102"),
            ],
        ),
        FAPriceQueryResult(
            asset_id=2,
            prices=[
                native_point(date(2026, 1, 3), "200"),
                native_point(date(2026, 1, 4), "202"),
                native_point(date(2026, 1, 5), "204"),
            ],
        ),
    ]
    prepared = prepare_asset_series_set(
        results,
        requested_range=DateRangeModel(
            start=date(2026, 1, 3),
            end=date(2026, 1, 5),
        ),
        target_currency="EUR",
    )

    assert prepared.baseline_date == date(2026, 1, 3)
    assert prepared.joint_return_dates == [
        date(2026, 1, 4),
        date(2026, 1, 5),
    ]
    assert prepared.data_quality.data_quality_status == DataQualityStatus.OK
    assert "baseline_inside_requested_range" in prepared.warnings
    assert "short_history:1" in prepared.warnings
    assert "short_history:2" in prepared.warnings


def test_fx_fingerprint_is_order_independent_and_content_sensitive():
    request_range = DateRangeModel(
        start=date(2026, 1, 3),
        end=date(2026, 1, 5),
    )
    original = fixture_results()
    first = prepare_asset_series_set(
        original,
        requested_range=request_range,
        target_currency="EUR",
    )
    reordered = prepare_asset_series_set(
        list(reversed(original)),
        requested_range=request_range,
        target_currency="EUR",
    )
    changed_results = fixture_results()
    changed_results[0].prices[1] = changed_results[0].prices[1].model_copy(update={"close": Decimal("92")})
    changed = prepare_asset_series_set(
        changed_results,
        requested_range=request_range,
        target_currency="EUR",
    )

    assert first.fx_fingerprint == reordered.fx_fingerprint
    assert first.fx_fingerprint != changed.fx_fingerprint


def test_observed_annualization_guards_empty_and_invalid_spans():
    assert observed_annualization(0, None, None) == (0, None)
    assert observed_annualization(
        64,
        date(2026, 1, 1),
        date(2026, 4, 1),
    ) == pytest.approx((90, 64 * 365 / 90))
    with pytest.raises(ValueError, match="cannot be negative"):
        observed_annualization(-1, None, None)
    with pytest.raises(ValueError, match="must follow"):
        observed_annualization(
            1,
            date(2026, 1, 1),
            date(2026, 1, 1),
        )


def test_asset_source_preserves_price_source_through_backward_fill():
    first_date = date(2026, 1, 1)
    history = PriceHistory(
        asset_id=1,
        date=first_date,
        close=Decimal("100"),
        currency="EUR",
        source_plugin_key="manual_fixture",
    )
    points = AssetSourceManager._build_backward_filled_series(
        {first_date: history},
        first_date,
        date(2026, 1, 2),
    )

    assert [point.source_plugin_key for point in points] == [
        "manual_fixture",
        "manual_fixture",
    ]
