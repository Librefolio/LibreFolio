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
    # Every fresh quote moves: a close repeated into Saturday 7 March would be a weekend carry, not a
    # fresh quote (developer's decision of 30/09/2026), and freshness is not what this test is about.
    fresh_after = [converted_point(_day(offset), native_close=str(100 + offset), target_close=str(Decimal(100 + offset) * Decimal("0.9"))) for offset in range(2, 6)]

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


# ---------------------------------------------------------------------------
# Market-closed repeats (developer's decision of 30/09/2026)
#
# Some sources (justETF) store a row for every calendar day: Saturday and Sunday repeat Friday's
# close, an exchange holiday repeats the day before. Such a row — on a weekend or on a market holiday,
# with exactly the close of the row before it — is a carry, not a quote: its date is no candidate for
# the joint calendar, and where another asset puts that date on it anyway, the repeating asset is
# valued at its last genuine quote. A move on a weekend or a holiday is a quote; so is a flat weekday.
# Without a holiday table, weekends still apply.
# ---------------------------------------------------------------------------

REPEAT_FIRST = date(2025, 1, 6)  # a Monday, and the baseline of every preparation below
REPEAT_LAST = date(2025, 1, 26)  # a Sunday, three weeks later
REPEAT_RANGE = DateRangeModel(start=date(2025, 1, 7), end=REPEAT_LAST)


def every_calendar_day(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


DAYS_IN_RANGE = every_calendar_day(REPEAT_RANGE.start, REPEAT_LAST)
WEEKDAYS_IN_RANGE = [day for day in DAYS_IN_RANGE if day.weekday() < 5]


def moving_close(day: date) -> Decimal:
    """A weekday close different from every other day's."""
    return Decimal("100") + Decimal((day - REPEAT_FIRST).days) / Decimal("2")


def seven_day_etf(asset_id: int = 1, *, flat_weekdays: frozenset[date] = frozenset()) -> FAPriceQueryResult:
    """A stored row every calendar day: weekdays move, a weekend or a flat weekday repeats the row before."""
    prices: list[FAPricePoint] = []
    previous: Decimal | None = None
    for day in every_calendar_day(REPEAT_FIRST, REPEAT_LAST):
        repeats = previous is not None and (day.weekday() >= 5 or day in flat_weekdays)
        close = previous if repeats else moving_close(day)
        prices.append(native_point(day, str(close)))
        previous = close
    return FAPriceQueryResult(asset_id=asset_id, prices=prices)


def five_day_series(asset_id: int = 1, *, flat_weekdays: frozenset[date] = frozenset()) -> FAPriceQueryResult:
    """The same quotes stored on weekdays only, served as the price query serves them: weekends backward-filled."""
    prices: list[FAPricePoint] = []
    last_quote: date | None = None
    last_close: Decimal | None = None
    for day in every_calendar_day(REPEAT_FIRST, REPEAT_LAST):
        if day.weekday() < 5:
            last_close = last_close if last_close is not None and day in flat_weekdays else moving_close(day)
            last_quote = day
            prices.append(native_point(day, str(last_close)))
        else:
            prices.append(native_point(day, str(last_close), effective_price_date=last_quote))
    return FAPriceQueryResult(asset_id=asset_id, prices=prices)


def weekend_mover(asset_id: int = 2, *, missing: frozenset[date] = frozenset()) -> FAPriceQueryResult:
    """A crypto-like series: quoted every calendar day, moving on weekends too."""
    return FAPriceQueryResult(
        asset_id=asset_id,
        prices=[native_point(day, str(Decimal("300") + Decimal((day - REPEAT_FIRST).days) * Decimal("0.75"))) for day in every_calendar_day(REPEAT_FIRST, REPEAT_LAST) if day not in missing],
    )


def prepare_repeats(*results: FAPriceQueryResult, market_holidays: frozenset[date] | None = None):
    """Prepare over REPEAT_RANGE; the holiday table is passed only when a test gives one."""
    table = {} if market_holidays is None else {"market_holidays": market_holidays}
    return prepare_asset_series_set(list(results), requested_range=REPEAT_RANGE, target_currency="EUR", **table)


def series_of(prepared, asset_id: int):
    return next(item for item in prepared.series if item.valuations.asset_id == asset_id)


def return_on(prepared, asset_id: int, day: date):
    return next(point for point in series_of(prepared, asset_id).returns.points if point.date == day)


def test_weekend_repeats_of_a_seven_day_source_are_not_observations():
    prepared = prepare_repeats(seven_day_etf())

    assert prepared.baseline_date == REPEAT_FIRST
    assert len(WEEKDAYS_IN_RANGE) == 14
    assert prepared.joint_return_dates == WEEKDAYS_IN_RANGE
    assert prepared.n_observations == 14
    # The trailing weekend repeats Friday 24: the series ends there, and so does its span.
    assert prepared.effective_range == DateRangeModel(start=date(2025, 1, 7), end=date(2025, 1, 24))
    assert prepared.calendar_days == 18
    assert prepared.annualization_factor == pytest.approx(14 * 365 / 18)
    assert prepared.calendar_coverage == pytest.approx(1.0)
    assert prepared.fresh_quote_coverage == pytest.approx(1.0)
    # Monday's return is measured from Friday's quote.
    monday = return_on(prepared, 1, date(2025, 1, 13))
    assert monday.previous_valuation_date == date(2025, 1, 10)
    assert monday.value == pytest.approx(float(moving_close(date(2025, 1, 13)) / moving_close(date(2025, 1, 10)) - 1))


def calendar_projection(prepared) -> dict[str, object]:
    """Everything the analytics read from a prepared set, and nothing incidental."""
    return {
        "baseline": prepared.baseline_date,
        "valuation_dates": prepared.joint_valuation_dates,
        "return_dates": prepared.joint_return_dates,
        "n_observations": prepared.n_observations,
        "calendar_days": prepared.calendar_days,
        "annualization_factor": prepared.annualization_factor,
        "calendar_coverage": prepared.calendar_coverage,
        "fresh_quote_coverage": prepared.fresh_quote_coverage,
        "valuations": {item.valuations.asset_id: [(point.valuation_date, point.effective_price_date, point.is_price_carried_forward, point.target_close) for point in item.valuations.points] for item in prepared.series},
        "returns": {item.returns.asset_id: [(point.date, point.previous_valuation_date, point.value) for point in item.returns.points] for item in prepared.series},
        "carried_forward_price_points": prepared.data_quality.carried_forward_price_points,
        "data_quality_status": prepared.data_quality.data_quality_status,
    }


@pytest.mark.parametrize("beside", [pytest.param((), id="alone"), pytest.param((weekend_mover(),), id="beside-a-series-quoted-every-day")])
def test_a_seven_day_source_prepares_exactly_like_its_weekday_quotes_alone(beside):
    """The cure in one line: storing the weekends as repeats must change nothing at all."""
    seven_days = prepare_repeats(seven_day_etf(), *beside)
    five_days = prepare_repeats(five_day_series(), *beside)

    assert calendar_projection(seven_days) == calendar_projection(five_days)


def test_a_repeat_on_a_market_holiday_is_not_an_observation_but_a_move_is():
    flat_holiday, moving_holiday = date(2025, 1, 15), date(2025, 1, 22)  # two Wednesdays
    etf = seven_day_etf(flat_weekdays=frozenset({flat_holiday}))

    prepared = prepare_repeats(etf, market_holidays=frozenset({flat_holiday, moving_holiday}))

    assert prepared.joint_return_dates == [day for day in WEEKDAYS_IN_RANGE if day != flat_holiday]
    assert moving_holiday in prepared.joint_return_dates
    assert prepared.annualization_factor == pytest.approx(13 * 365 / 18)
    # Thursday's return spans the holiday, from Tuesday's quote.
    thursday = return_on(prepared, 1, date(2025, 1, 16))
    assert thursday.previous_valuation_date == date(2025, 1, 14)
    assert thursday.value == pytest.approx(float(moving_close(date(2025, 1, 16)) / moving_close(date(2025, 1, 14)) - 1))


def test_a_series_that_moves_on_weekends_keeps_every_weekend_observation():
    prepared = prepare_repeats(weekend_mover(asset_id=1))

    assert prepared.joint_return_dates == DAYS_IN_RANGE
    assert prepared.n_observations == 20
    assert prepared.annualization_factor == pytest.approx(365.0)


def test_beside_a_weekend_quote_a_seven_day_source_is_carried_through_the_weekend():
    prepared = prepare_repeats(seven_day_etf(asset_id=1), weekend_mover(asset_id=2))

    # The crypto is quoted every day, so every day stays on the joint calendar...
    assert prepared.joint_return_dates == DAYS_IN_RANGE
    # ...and on a weekend the ETF is valued at Friday's quote, carried.
    etf = {point.valuation_date: point for point in series_of(prepared, 1).valuations.points}
    for day in DAYS_IN_RANGE:
        friday = day - timedelta(days=day.weekday() - 4) if day.weekday() >= 5 else day
        assert (etf[day].is_price_carried_forward, etf[day].effective_price_date) == (day != friday, friday), day
    assert return_on(prepared, 1, date(2025, 1, 11)).value == 0.0
    monday = return_on(prepared, 1, date(2025, 1, 13))
    assert monday.value == pytest.approx(float(moving_close(date(2025, 1, 13)) / moving_close(date(2025, 1, 10)) - 1))
    # A carried point is no fresh quote: 14 of the ETF's 20 points, and all 20 of the crypto's.
    assert prepared.fresh_quote_coverage == pytest.approx(34 / 40)
    # A carry of a day or two is ordinary: it degrades nothing.
    assert prepared.data_quality.carried_forward_price_points == 0
    assert prepared.data_quality.carried_forward_price_asset_ids == []
    assert prepared.data_quality.data_quality_status == DataQualityStatus.OK
    # Each asset lists its own genuine quotes in the requested range.
    assert series_of(prepared, 1).quote_dates == WEEKDAYS_IN_RANGE
    assert series_of(prepared, 2).quote_dates == DAYS_IN_RANGE


def test_a_flat_weekday_is_still_a_quote():
    flat_monday, flat_wednesday = date(2025, 1, 13), date(2025, 1, 15)
    bond = five_day_series(flat_weekdays=frozenset({flat_monday, flat_wednesday}))

    prepared = prepare_repeats(bond)

    assert prepared.joint_return_dates == WEEKDAYS_IN_RANGE
    assert return_on(prepared, 1, flat_monday).value == 0.0
    assert return_on(prepared, 1, flat_wednesday).value == 0.0


def test_quote_dates_are_each_assets_own_quotes_even_on_a_date_the_joint_calendar_drops():
    """What the portfolio TWRR is sampled on: a day a held asset is quoted, joint calendar or not."""
    gap = date(2025, 1, 15)

    prepared = prepare_repeats(seven_day_etf(asset_id=1), weekend_mover(asset_id=2, missing=frozenset({gap})))

    # Presence barrier: the crypto has no row on the 15th, so the joint calendar drops that date...
    assert gap not in prepared.joint_return_dates
    assert prepared.data_quality.incomplete_valuation_dates == [gap]
    # ...yet the ETF was quoted on it, and says so.
    assert series_of(prepared, 1).quote_dates == WEEKDAYS_IN_RANGE
    assert series_of(prepared, 2).quote_dates == [day for day in DAYS_IN_RANGE if day != gap]


def seven_day_usd_etf(asset_id: int = 1) -> FAPriceQueryResult:
    """A USD listing stored every calendar day and served in EUR: its weekend rows repeat Friday's USD
    close, while the rate that converts them moves every day, weekends included."""
    prices: list[FAPricePoint] = []
    previous: Decimal | None = None
    for offset, day in enumerate(every_calendar_day(REPEAT_FIRST, REPEAT_LAST)):
        native = previous if previous is not None and day.weekday() >= 5 else moving_close(day)
        rate = Decimal("0.9") + Decimal(offset) / Decimal("1000")
        prices.append(converted_point(day, native_close=str(native), target_close=str(native * rate)))
        previous = native
    return FAPriceQueryResult(asset_id=asset_id, prices=prices)


def test_a_foreign_listing_repeating_its_native_close_is_a_carry_although_its_converted_close_moves():
    """The rule reads the close as the market set it, in the listing's own currency.

    A moving FX rate turns Friday's repeated USD close into a different EUR amount on Saturday and
    Sunday; no market traded the listing on those days, so they are carries all the same.
    """
    etf = seven_day_usd_etf()
    rows = {point.date: point for point in etf.prices}
    friday, saturday, sunday = date(2025, 1, 10), date(2025, 1, 11), date(2025, 1, 12)
    # Presence barrier: the USD close repeats, the EUR one does not.
    assert rows[saturday].original_close == rows[sunday].original_close == rows[friday].original_close
    assert len({rows[friday].close, rows[saturday].close, rows[sunday].close}) == 3

    prepared = prepare_repeats(etf)

    assert prepared.joint_return_dates == WEEKDAYS_IN_RANGE
    assert series_of(prepared, 1).quote_dates == WEEKDAYS_IN_RANGE
    # Monday's return is measured from Friday's quote.
    assert return_on(prepared, 1, date(2025, 1, 13)).previous_valuation_date == friday
