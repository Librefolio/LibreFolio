"""Mathematical tests for canonical converted-price and return preparation."""

from datetime import date, timedelta
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
from backend.app.services.data_quality_thresholds import STALE_PRICE_THRESHOLD_DAYS
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

    # Every carry is still tracked point by point: the equity price is one and two days old on
    # the second and third date, its rate one day old on the last two...
    equity_points = prepared.series[0].valuations.points
    assert [point.is_price_carried_forward for point in equity_points] == [False, True, True, False]
    assert [point.effective_price_date for point in equity_points] == [date(2026, 1, 2), date(2026, 1, 2), date(2026, 1, 2), date(2026, 1, 5)]
    assert [point.is_fx_carried_forward for point in equity_points] == [False, False, True, True]
    # ...but none is older than the staleness threshold, so none degrades the report: a carry of a
    # day or two is a weekend or a holiday (developer's decision of 24/09/2026).
    assert prepared.data_quality.data_quality_status == DataQualityStatus.OK
    assert prepared.data_quality.carried_forward_price_points == 0
    assert prepared.data_quality.carried_forward_fx_points == 0
    assert prepared.data_quality.carried_forward_price_asset_ids == []
    assert prepared.data_quality.carried_forward_fx_pairs == []

    equity = prepared.series[0]
    assert equity.valuations.points[0].price_source == "equity"
    assert equity.returns.points[0].value == pytest.approx(float(Decimal("91") / Decimal("90") - Decimal("1")))
    assert equity.returns.points[0].value != 0.0
    assert equity.returns.points[1].value == 0.0
    assert equity.valuations.points[-1].is_price_carried_forward is False
    assert equity.valuations.points[-1].is_fx_carried_forward is True


# A carried price or rate degrades the report only once it is older than the staleness
# threshold, and the baseline never does (developer's decision of 24/09/2026). Asset 1 carries;
# asset 2 is quoted fresh every day, which is what puts each date on the joint calendar.

CARRY_BASELINE = date(2026, 3, 2)


def _day(offset: int) -> date:
    return CARRY_BASELINE + timedelta(days=offset)


def _prepare_with_reference(carried: FAPriceQueryResult, days: int):
    reference = FAPriceQueryResult(
        asset_id=2,
        prices=[native_point(_day(offset), str(200 + offset)) for offset in range(days + 1)],
    )
    return prepare_asset_series_set(
        [carried, reference],
        requested_range=DateRangeModel(start=_day(1), end=_day(days)),
        target_currency="EUR",
    )


def _price_carried_for(days: int) -> FAPriceQueryResult:
    """Quoted on the baseline, then that price is carried forward for `days` days."""
    return FAPriceQueryResult(
        asset_id=1,
        prices=[
            native_point(CARRY_BASELINE, "100"),
            *(native_point(_day(offset), "100", effective_price_date=CARRY_BASELINE) for offset in range(1, days + 1)),
        ],
    )


def _fx_carried_for(days: int) -> FAPriceQueryResult:
    """Quoted fresh every day in USD, converted with the baseline's rate for `days` days."""
    return FAPriceQueryResult(
        asset_id=1,
        prices=[
            converted_point(CARRY_BASELINE, native_close="100", target_close="90"),
            *(
                converted_point(
                    _day(offset),
                    native_close=str(100 + offset),
                    target_close=str(Decimal(100 + offset) * Decimal("0.9")),
                    fx_rate_date=CARRY_BASELINE,
                )
                for offset in range(1, days + 1)
            ),
        ],
    )


CARRY_BOUNDARIES = [
    pytest.param(STALE_PRICE_THRESHOLD_DAYS, 0, id="exactly-the-threshold-is-ordinary"),
    pytest.param(STALE_PRICE_THRESHOLD_DAYS + 1, 1, id="one-day-past-it-the-last-point-is-stale"),
    pytest.param(STALE_PRICE_THRESHOLD_DAYS + 2, 2, id="each-point-past-it-counts"),
]


@pytest.mark.parametrize(("carry_days", "expected_points"), CARRY_BOUNDARIES)
def test_carried_price_degrades_only_beyond_the_stale_threshold(carry_days, expected_points):
    prepared = _prepare_with_reference(_price_carried_for(carry_days), carry_days)

    # The calendar does not depend on the verdict: every day is a joint date.
    assert prepared.baseline_date == CARRY_BASELINE
    assert prepared.n_observations == carry_days
    points = prepared.series[0].valuations.points
    assert [(point.valuation_date - point.effective_price_date).days for point in points] == list(range(carry_days + 1))

    data_quality = prepared.data_quality
    assert data_quality.carried_forward_price_points == expected_points
    assert data_quality.carried_forward_price_asset_ids == ([1] if expected_points else [])
    assert data_quality.carried_forward_fx_points == 0
    assert data_quality.data_quality_status == (DataQualityStatus.CARRIED_FORWARD if expected_points else DataQualityStatus.OK)
    # Freshness is a separate question: a carried price is never a fresh quote, however young.
    assert prepared.fresh_quote_coverage == pytest.approx(carry_days / (2 * carry_days))


@pytest.mark.parametrize(("carry_days", "expected_points"), CARRY_BOUNDARIES)
def test_carried_fx_rate_degrades_only_beyond_the_stale_threshold(carry_days, expected_points):
    prepared = _prepare_with_reference(_fx_carried_for(carry_days), carry_days)

    points = prepared.series[0].valuations.points
    assert [(point.valuation_date - point.fx_rate_date).days for point in points] == list(range(carry_days + 1))
    assert not any(point.is_price_carried_forward for point in points)

    data_quality = prepared.data_quality
    assert data_quality.carried_forward_fx_points == expected_points
    assert data_quality.carried_forward_fx_pairs == (["USD/EUR"] if expected_points else [])
    assert data_quality.carried_forward_price_points == 0
    assert data_quality.data_quality_status == (DataQualityStatus.CARRIED_FORWARD if expected_points else DataQualityStatus.OK)
    # Every price is a fresh quote, so the age of the rate leaves freshness alone.
    assert prepared.fresh_quote_coverage == pytest.approx(1.0)


def test_a_carried_baseline_never_degrades_even_when_older_than_the_threshold():
    stale_since = CARRY_BASELINE - timedelta(days=30)
    fresh_after = [converted_point(_day(offset), native_close="100", target_close="90") for offset in range(2, 6)]

    def stale(offset: int) -> FAPricePoint:
        return converted_point(_day(offset), native_close="100", target_close="90", effective_price_date=stale_since, fx_rate_date=stale_since)

    # Quoted a month before the baseline, and again from the first date after it.
    resumes_after_baseline = FAPriceQueryResult(
        asset_id=1,
        prices=[stale(0), converted_point(_day(1), native_close="100", target_close="90"), *fresh_after],
    )
    prepared = _prepare_with_reference(resumes_after_baseline, 5)

    baseline = prepared.series[0].valuations.points[0]
    assert prepared.baseline_date == CARRY_BASELINE == baseline.valuation_date
    # The provenance still says how old the reference is...
    assert baseline.is_price_carried_forward is True
    assert baseline.effective_price_date == stale_since
    assert baseline.is_fx_carried_forward is True
    assert baseline.fx_rate_date == stale_since
    # ...but the baseline is a reference, not an observation: it never counts.
    assert prepared.data_quality.carried_forward_price_points == 0
    assert prepared.data_quality.carried_forward_fx_points == 0
    assert prepared.data_quality.data_quality_status == DataQualityStatus.OK
    assert prepared.fresh_quote_coverage == pytest.approx(1.0)

    # Control: quotes resume one date later, so the same stale price and rate are also the first
    # observation — and that one counts.
    resumes_one_date_later = FAPriceQueryResult(asset_id=1, prices=[stale(0), stale(1), *fresh_after])
    control = _prepare_with_reference(resumes_one_date_later, 5)

    assert control.baseline_date == CARRY_BASELINE
    assert control.data_quality.carried_forward_price_points == 1
    assert control.data_quality.carried_forward_fx_points == 1
    assert control.data_quality.carried_forward_price_asset_ids == [1]
    assert control.data_quality.carried_forward_fx_pairs == ["USD/EUR"]
    assert control.data_quality.data_quality_status == DataQualityStatus.CARRIED_FORWARD
    assert control.fresh_quote_coverage == pytest.approx(9 / 10)


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
