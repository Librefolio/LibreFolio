"""Z-29fx: ``POST /fx/currencies/convert`` samples a conversion for a compact chart, as ``POST /assets/prices/query``
does for a price series (Z-29a, Z-29s-a, O1). Reviewers: MF (the semantics), Y (the contract, for the FX half of Y-40).

Why. A card of the FX list draws a few hundred points at most, and asks every day of its range today: years of rates are
thousands of points per card. The asset list stopped doing that with Z-29b; the FX list needs the same contract.

The contract pinned here, the price query's own (``developer/backend/assets/architecture.md``, «Sampled Price Series»):

1. ``FXConversionRequest`` takes ``key``, ``max_points`` (1 … 10 000), ``resolution`` and ``sample_like``: at most one of
   the last three, none of them with ``annotation_requests``; ``key`` and ``sample_like`` match ``SAMPLE_KEY_PATTERN``.
2. A conversion's fill starts on its first day F: the first day of its (cut) range that converts, the range's start when a
   rate precedes it. With ``max_points`` the step is ``choose_resolution(F, end, max_points)``; with ``resolution`` the one
   asked; a ``sample_like`` follower takes the step of the conversion it names, computed on that conversion's own fill
   (on its own fill when the named one has none), from the later of the two first days.
3. A weekly or monthly conversion answers, in ``results``, only the daily results on ``sample_dates(F, end, step)``: each
   the daily result of that date, unchanged. A daily one answers every day, as today (a follower from its later first day).
4. Every result carries ``request_index``, the position of its conversion in the request; ``samples`` holds one entry per
   conversion: its ``resolution`` (``daily`` by default) and, for a weekly or monthly one, ``sample_bounds``: the daily
   result on F (``first``) and on the range's end (``last``).
5. Signals of a weekly or monthly conversion are computed day by day, as today, and each series reduced onto the
   conversion's dates by its output's ``aggregation_profile`` (``sample_signal_series``), the series of one signal then
   aligned (``align_signal_series``, O1): the price query's own function (``services/signals/sampling.py``).
6. ``sample_like`` is checked over the whole request first (``resolve_sample_references``): a fault is a 422
   ``{"code": "sample_reference", "reason", "item", "key", "message"}``.
7. The calendar rolling return is offered in the FX domain too (``ASSET_CALENDAR_ROLLING_RETURN``, the FX half of Y-40): a
   conversion may ask it, and its reduced points keep their provenance (``last_with_range``: the element itself).
8. The day budget counts the days of the fill, as today: a sampled conversion costs what the daily one does.

Isolation: PURE. The handler is called in process, ``convert_bulk`` replaced by a double on no database (the X-R41 tests'
way); the signals run in ``SignalService`` on the points the double gives.

Red before Z-29fx: ``FXConversionRequest`` ignores the four fields, results carry no ``request_index``, the response has
no ``samples``, the conversion answers every day, and ``ASSET_CALENDAR_ROLLING_RETURN`` is refused in the FX domain.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.app.api.v1.fx import currencies as fx_currencies_api
from backend.app.schemas.common import Currency
from backend.app.schemas.fx import FXConversionRequest
from backend.app.schemas.signals import SignalAggregationProfile, SignalCalendarReturnValuePoint, SignalDomain, _validate_series_alignment
from backend.app.services.signals import aggregation as signal_aggregation
from backend.app.services.signals.registry import SignalPluginRegistry

#: The range of the cases: Monday 2026-01-05 to Sunday 2026-03-29, 84 days, 12 ISO weeks, 3 months.
START = date(2026, 1, 5)
END = date(2026, 3, 29)
#: The rate the double gives each pair from its first day: a base, plus a thousandth a day.
EUR_USD = ("EUR", "USD")
GBP_USD = ("GBP", "USD")


def _day(offset: int) -> date:
    return START + timedelta(days=offset)


def _rate(pair: tuple[str, str], day: date) -> Decimal:
    base = Decimal("1.1") if pair == EUR_USD else Decimal("1.3")
    return base + Decimal("0.001") * (day - date(2025, 1, 1)).days


def _convert_bulk(monkeypatch: pytest.MonkeyPatch, first_rate: dict[tuple[str, str], date] | None = None) -> AsyncMock:
    """``convert_bulk`` where the handler reads it: a pair converts from its first rate day (``first_rate``, else always),
    at ``_rate`` of that day, never backward-filled; a day before it has no rate (None, and the error the real one writes)."""
    first_rate = first_rate or {}

    async def _convert(_session, conversions, raise_on_error=True):
        results, errors = [], []
        for index, (amount, to, day) in enumerate(conversions):
            pair = (amount.code, to)
            if amount.code == to:
                results.append((Currency(code=to, amount=amount.amount), day, False))
            elif day < first_rate.get(pair, date.min):
                results.append(None)
                errors.append(f"Conversion {index}: No FX rate found for {amount.code}/{to} on or before {day.isoformat()}. Please sync FX rates first.")
            else:
                results.append((Currency(code=to, amount=amount.amount * _rate(pair, day)), day, False))
        return results, errors

    double = AsyncMock(side_effect=_convert)
    monkeypatch.setattr(fx_currencies_api, "convert_bulk", double)
    return double


def _request(pair: tuple[str, str] = EUR_USD, start: date = START, end: date = END, **fields) -> FXConversionRequest:
    """One conversion as a client posts it: 1 unit of the pair's base over the range, with ``fields``."""
    return FXConversionRequest.model_validate({"from_amount": {"code": pair[0], "amount": "1"}, "to": pair[1], "date_range": {"start": start.isoformat(), "end": end.isoformat()}, **fields})


async def _convert(requests: list[FXConversionRequest]):
    """The handler called in process; an ``HTTPException`` is returned to the test, which reads it."""
    try:
        return await fx_currencies_api.convert_currency_bulk(requests, session=AsyncMock(), _current_user=Mock())
    except HTTPException as exc:
        return exc


def _ok(response):
    assert not isinstance(response, HTTPException), f"answered {response.status_code} {response.detail!r}"
    return response


def _dates_of(response, index: int) -> list[date]:
    return [result.conversion_date for result in response.results if getattr(result, "request_index", None) == index]


def _sample_of(response, index: int):
    samples = {sample.request_index: sample for sample in getattr(response, "samples", [])}
    assert index in samples, f"no samples entry for conversion {index}: {getattr(response, 'samples', 'no samples field')}"
    return samples[index]


def _ref_bucket_ends(first: date, end: date, step: str) -> list[date]:
    """The last day of each ISO week (Monday to Sunday) or calendar month from ``first``'s to ``end``'s, the last cut at
    ``end``: walked here, not read from ``price_sampling``."""
    ends, day = [], first
    while day <= end:
        if step == "weekly":
            bucket_end = day + timedelta(days=6 - day.weekday())
        else:
            bucket_end = (day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        ends.append(min(bucket_end, end))
        day = bucket_end + timedelta(days=1)
    return ends


# =============================================================================
# FXS-01 — the request's four fields
# =============================================================================


def test_fxs01_a_conversion_takes_key_max_points_resolution_and_sample_like():
    """FXS-01: ``key``, ``max_points``, ``resolution`` and ``sample_like`` are read, as the price query's item reads them.

    Red before Z-29fx: the fields are ignored (the model keeps none of them).
    """
    asked = _request(key="pair:EUR-USD", max_points=60)
    follower = _request(GBP_USD, sample_like="pair:EUR-USD")
    stepped = _request(resolution="monthly")

    assert (getattr(asked, "key", None), getattr(asked, "max_points", None)) == ("pair:EUR-USD", 60)
    assert getattr(follower, "sample_like", None) == "pair:EUR-USD"
    assert getattr(stepped, "resolution", None) == "monthly"
    plain = _request()
    assert [getattr(plain, name, "missing") for name in ("key", "max_points", "resolution", "sample_like")] == [None, None, None, None]


#: A signal and a rule on it: accepted alone (the control below), refused with a sampling field.
ANNOTATED = {
    "signals": [{"instance_id": "sma3", "signal_code": "SMA", "params": {"period": 3}}],
    "annotation_requests": [{"kind": "threshold_crossing", "key": "close-crosses-1", "attach_to_instance_id": "sma3", "source": {"kind": "price"}, "threshold": 1.0}],
}


def test_fxs01_control_annotations_are_accepted_without_a_sampling_field():
    """FXS-01 control, green before and after: the annotated request alone is valid, so its refusal below is the field's."""
    assert _request(**ANNOTATED).annotation_requests


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param({"max_points": 60, "resolution": "weekly"}, id="max_points-and-resolution"),
        pytest.param({"max_points": 60, "sample_like": "x"}, id="max_points-and-sample_like"),
        pytest.param({"resolution": "weekly", "sample_like": "x"}, id="resolution-and-sample_like"),
        pytest.param({"max_points": 0}, id="max_points-0"),
        pytest.param({"max_points": 10_001}, id="max_points-over-10000"),
        pytest.param({"resolution": "yearly"}, id="unknown-resolution"),
        pytest.param({"key": "a key"}, id="key-with-a-space"),
        pytest.param({"sample_like": ""}, id="empty-sample_like"),
        pytest.param({"max_points": 60, **ANNOTATED}, id="with-annotation_requests"),
    ],
)
def test_fxs01_refuses_what_the_price_query_refuses(fields):
    """FXS-01: at most one of ``max_points``, ``resolution`` and ``sample_like``; ``max_points`` 1 … 10 000; a step among
    daily, weekly and monthly; a key in ``SAMPLE_KEY_PATTERN``; no sampling field with ``annotation_requests``.

    Red before Z-29fx: the fields are ignored, so nothing is refused.
    """
    with pytest.raises(ValidationError):
        _request(**fields)


# =============================================================================
# FXS-02 … FXS-05 — the step, the points, the bounds
# =============================================================================


@pytest.mark.asyncio
async def test_fxs02_a_conversion_without_the_fields_answers_every_day_and_says_its_index_and_step(monkeypatch):
    """FXS-02: a conversion without the fields answers as today, every day; each result carries ``request_index`` and
    ``samples`` says the step, daily, without bounds.

    Red before Z-29fx: no ``request_index``, no ``samples``.
    """
    _convert_bulk(monkeypatch)

    response = _ok(await _convert([_request(), _request(GBP_USD)]))

    assert _dates_of(response, 0) == [_day(offset) for offset in range(84)]
    assert _dates_of(response, 1) == [_day(offset) for offset in range(84)]
    for index in (0, 1):
        sample = _sample_of(response, index)
        assert (sample.resolution, sample.sample_bounds) == ("daily", None)


@pytest.mark.asyncio
async def test_fxs03_max_points_samples_weekly_the_daily_results_of_each_weeks_last_day(monkeypatch):
    """FXS-03: 84 days over 12 ISO weeks with ``max_points`` 20: weekly. The results are the daily results of the 12
    Sundays, unchanged (amount, rate, date); ``sample_bounds.first`` the result on F, Monday 5 January, and ``last`` the one
    on the end, Sunday 29 March.

    Red before Z-29fx: every day is answered.
    """
    _convert_bulk(monkeypatch)

    response = _ok(await _convert([_request(key="pair:EUR-USD", max_points=20)]))

    expected = _ref_bucket_ends(START, END, "weekly")
    assert len(expected) == 12
    assert _dates_of(response, 0) == expected
    for result in response.results:
        assert result.rate == _rate(EUR_USD, result.conversion_date), result
    sample = _sample_of(response, 0)
    assert sample.resolution == "weekly"
    assert (sample.sample_bounds.first.conversion_date, sample.sample_bounds.first.rate) == (START, _rate(EUR_USD, START))
    assert (sample.sample_bounds.last.conversion_date, sample.sample_bounds.last.rate) == (END, _rate(EUR_USD, END))


@pytest.mark.asyncio
@pytest.mark.parametrize(("max_points", "step"), [(84, "daily"), (83, "weekly"), (12, "weekly"), (11, "monthly")])
async def test_fxs03_the_step_is_the_finest_whose_count_fits(monkeypatch, max_points, step):
    """FXS-03: 84 days, 12 weeks: daily up to 84 points, weekly from 83 to 12, monthly below (the floor).

    Red before Z-29fx: every day is answered, and no step is said.
    """
    _convert_bulk(monkeypatch)

    response = _ok(await _convert([_request(max_points=max_points)]))

    assert _sample_of(response, 0).resolution == step
    expected = [_day(offset) for offset in range(84)] if step == "daily" else _ref_bucket_ends(START, END, step)
    assert _dates_of(response, 0) == expected


@pytest.mark.asyncio
async def test_fxs04_resolution_asks_its_step_whatever_the_length(monkeypatch):
    """FXS-04: ``resolution`` monthly: the 31 January, the 28 February and the end, 29 March, cut.

    Red before Z-29fx: every day is answered.
    """
    _convert_bulk(monkeypatch)

    response = _ok(await _convert([_request(resolution="monthly")]))

    assert _dates_of(response, 0) == [date(2026, 1, 31), date(2026, 2, 28), END]
    assert _sample_of(response, 0).resolution == "monthly"


@pytest.mark.asyncio
async def test_fxs05_the_step_counts_from_the_first_day_that_converts(monkeypatch):
    """FXS-05: the pair's first rate is Monday 2 February: F. From the range's start, 12 weeks would not fit in 9 points
    (monthly); from F, 56 days over 8 weeks do (weekly). The sample starts on F's week, and ``first`` is F's result.

    Red before Z-29fx: every day that converts is answered.
    """
    _convert_bulk(monkeypatch, {EUR_USD: date(2026, 2, 2)})

    response = _ok(await _convert([_request(max_points=9)]))

    sample = _sample_of(response, 0)
    assert sample.resolution == "weekly"
    assert _dates_of(response, 0) == _ref_bucket_ends(date(2026, 2, 2), END, "weekly")
    assert sample.sample_bounds.first.conversion_date == date(2026, 2, 2)


@pytest.mark.asyncio
async def test_fxs05_a_conversion_with_nothing_to_fill_answers_nothing_and_a_daily_step(monkeypatch):
    """FXS-05: a pair with no rate in or before the range: no result, ``samples`` daily without bounds, and the error of
    today.

    Red before Z-29fx: no ``samples``.
    """
    _convert_bulk(monkeypatch, {EUR_USD: date(2027, 1, 1)})

    response = await _convert([_request(max_points=20), _request(GBP_USD)])

    assert not isinstance(response, HTTPException), response
    assert _dates_of(response, 0) == []
    assert (_sample_of(response, 0).resolution, _sample_of(response, 0).sample_bounds) == ("daily", None)
    assert response.errors, "the missing rates are still said"


# =============================================================================
# FXS-06 — sample_like
# =============================================================================


@pytest.mark.asyncio
async def test_fxs06_a_follower_takes_the_step_and_buckets_of_the_conversion_it_names(monkeypatch):
    """FXS-06: EUR→USD, key ``card``, weekly on 20 points; GBP→USD ``sample_like`` it, with rates from Wednesday 14
    January only. The follower is weekly too, from the later first day: the Sundays from 18 January, and its ``first`` is
    its result on 14 January.

    Red before Z-29fx: the follower answers every day.
    """
    _convert_bulk(monkeypatch, {GBP_USD: date(2026, 1, 14)})

    response = _ok(await _convert([_request(key="card", max_points=20), _request(GBP_USD, sample_like="card")]))

    follower = _sample_of(response, 1)
    assert follower.resolution == "weekly"
    assert _dates_of(response, 1) == _ref_bucket_ends(date(2026, 1, 14), END, "weekly")
    assert follower.sample_bounds.first.conversion_date == date(2026, 1, 14)
    assert follower.sample_bounds.last.conversion_date == END


@pytest.mark.asyncio
async def test_fxs06_a_follower_of_a_daily_card_answers_every_day_from_the_later_first_day(monkeypatch):
    """FXS-06: the card is daily (84 days fit in 100 points); the follower, with rates from 14 January, answers every day
    from there, daily, without bounds.

    Red before Z-29fx: no ``samples``.
    """
    _convert_bulk(monkeypatch, {GBP_USD: date(2026, 1, 14)})

    response = _ok(await _convert([_request(key="card", max_points=100), _request(GBP_USD, sample_like="card")]))

    assert _sample_of(response, 1).resolution == "daily"
    assert _dates_of(response, 1)[0] == date(2026, 1, 14)
    assert _dates_of(response, 1)[-1] == END


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("requests", "reason", "item"),
    [
        pytest.param(lambda: [_request(key="card", max_points=20), _request(GBP_USD, sample_like="nope")], "unknown_key", 1, id="unknown_key"),
        pytest.param(lambda: [_request(key="card", max_points=20), _request(GBP_USD, key="card", max_points=20)], "duplicate_key", 1, id="duplicate_key"),
        pytest.param(lambda: [_request(key="a", sample_like="a")], "chained", 0, id="chained-itself"),
        pytest.param(lambda: [_request(key="card", max_points=20), _request(GBP_USD, start=START + timedelta(days=1), sample_like="card")], "range_mismatch", 1, id="range_mismatch"),
    ],
)
async def test_fxs06_a_reference_that_cannot_be_followed_is_a_422(monkeypatch, requests, reason, item):
    """FXS-06: the four faults of the price query, before anything is converted: a 422 ``sample_reference`` naming the
    reason and the item.

    Red before Z-29fx: the fields are ignored, and the request is answered.
    """
    double = _convert_bulk(monkeypatch)

    response = await _convert(requests())

    assert isinstance(response, HTTPException) and response.status_code == 422, response
    assert {key: response.detail.get(key) for key in ("code", "reason", "item")} == {"code": "sample_reference", "reason": reason, "item": item}
    double.assert_not_awaited()


# =============================================================================
# FXS-07 / FXS-08 — the signals, the rolling return
# =============================================================================

SIGNALS = [
    {"instance_id": "ema3", "signal_code": "EMA", "params": {"period": 3}},
    {"instance_id": "bands5", "signal_code": "BOLLINGER", "params": {"period": 5, "multiplier": 2.0}},
    {"instance_id": "return7", "signal_code": "ASSET_CALENDAR_ROLLING_RETURN", "params": {"window_days": 7}},
]


def _profiles(signal_code: str) -> dict[str, SignalAggregationProfile]:
    return {spec.key: spec.aggregation_profile for spec in SignalPluginRegistry.get_plugin(signal_code).output_specs}


def test_fxs08_the_calendar_rolling_return_is_offered_in_the_fx_domain():
    """FXS-08: ``ASSET_CALENDAR_ROLLING_RETURN`` lists the FX domain among its domains (the FX catalog then offers it).

    Red before Z-29fx: asset only.
    """
    plugin = SignalPluginRegistry.get_plugin("ASSET_CALENDAR_ROLLING_RETURN")
    assert SignalDomain.FX in plugin.compatible_domains and SignalDomain.ASSET in plugin.compatible_domains


@pytest.mark.asyncio
async def test_fxs07_the_signals_of_a_sampled_conversion_are_reduced_and_aligned(monkeypatch):
    """FXS-07: EMA (3), Bollinger (5) and the calendar return (7 days) on EUR→USD weekly (20 points). Each series is the
    daily answer's series reduced onto the 12 Sundays by its output's profile (``sample_signal_series``), every point on
    one of them, and the series of a signal are on identical dates (O1). The calendar return keeps its provenance.

    Red before Z-29fx: the rolling return is refused in the FX domain (422), and the other series stay daily.
    """
    _convert_bulk(monkeypatch)

    daily = _ok(await _convert([_request(signals=SIGNALS)]))
    sampled = _ok(await _convert([_request(max_points=20, signals=SIGNALS)]))

    sundays = _ref_bucket_ends(START, END, "weekly")
    (daily_group,) = daily.signal_results
    (sampled_group,) = sampled.signal_results
    daily_by_id = {result.instance_id: result for result in daily_group.signals}
    assert sorted(daily_by_id) == ["bands5", "ema3", "return7"]
    for result in sampled_group.signals:
        assert result.status.value in ("ok", "partial") and result.series, f"{result.instance_id}: {result.status}, {result.error}"
        _validate_series_alignment(result.series)
        profiles = _profiles(result.signal_code)
        reduced_alone = [signal_aggregation.sample_signal_series(series, profiles[series.key], "weekly", sundays) for series in daily_by_id[result.instance_id].series]
        expected = signal_aggregation.align_signal_series(reduced_alone)
        assert [series.model_dump(mode="json") for series in result.series] == [series.model_dump(mode="json") for series in expected], result.instance_id
        for series in result.series:
            assert {point.date for point in series.points} <= set(sundays), f"{result.instance_id}.{series.key}: points off the Sundays"
    (returns,) = [result for result in sampled_group.signals if result.instance_id == "return7"]
    assert {type(point).__name__ for point in returns.series[0].points if point.value is not None} == {SignalCalendarReturnValuePoint.__name__}


# =============================================================================
# FXS-09 — the budget
# =============================================================================


@pytest.mark.asyncio
async def test_fxs09_a_sampled_conversion_costs_the_days_of_its_fill(monkeypatch):
    """FXS-09: the day budget counts the fill's days whatever the step: the conversions handed to ``convert_bulk`` are the
    daily ones, every day of the range, with or without ``max_points``.

    Green before Z-29fx by construction for the daily request; pins the sampled one: the cure reduces in memory.
    """
    double = _convert_bulk(monkeypatch)

    _ok(await _convert([_request(max_points=20)]))

    handed = [day for call in double.await_args_list for _amount, _to, day in call.args[1]]
    assert handed == [_day(offset) for offset in range(84)]
