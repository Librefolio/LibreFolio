"""Fail-closed contract tests for `ai_export.temporal.aggregators` value objects.

`test_ai_export_temporal.py` already covers the *happy* aggregation semantics
(OHLC, bands, monetary flows, discrete events, warm-up slicing). This file covers
the other half: the `__post_init__` invariants those aggregates declare, and the
`aggregate_signal_buckets` dispatcher's rejection arms.

Why these are worth pinning rather than "defensive noise": every aggregate here
is the last typed stop before a number reaches an exported AI Export payload. The
invariants exist so that a wrong number is *refused* instead of silently rendered
into a prompt an LLM will then reason about. Each test below names, in one
sentence, the concrete situation that produces the rejected shape - typically a
plugin returning an unexpected series shape, or a future refactor of
`_scalar_statistics_for_bucket` picking the wrong point.

No DB, no server, no network: isolation is PURE.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from backend.app.schemas.signals import SignalAggregationProfile
from backend.app.services.ai_export.temporal import aggregators
from backend.app.services.ai_export.temporal.aggregators import (
    _SCALAR_AGGREGATION_PROFILES,
    BandBucketStatistics,
    BandEnvelopeRepresentative,
    DatedValue,
    ScalarBucketStatistics,
    _assign_by_date,
    aggregate_band_statistics,
    aggregate_scalar_statistics,
    aggregate_signal_buckets,
    assign_discrete_events,
    select_band_envelope,
    select_scalar_representative,
)
from backend.app.services.ai_export.temporal.plan import Bucket, BucketingPolicy, BucketPlan
from backend.app.services.ai_export.temporal.points import BandObservedPoint, DiscreteEvent, ObservedPoint

# ---------------------------------------------------------------------------
# Shared fixtures - one single-bucket plan, deliberately tiny and explicit
# ---------------------------------------------------------------------------

DAY_1 = date(2026, 3, 2)
DAY_2 = date(2026, 3, 3)
DAY_3 = date(2026, 3, 4)
OUTSIDE = date(2026, 3, 9)


def _bucket(index: int = 0, start: date = DAY_1, end: date = DAY_3) -> Bucket:
    return Bucket(index=index, start_date=start, end_date=end)


def _plan(start: date = DAY_1, end: date = DAY_3) -> BucketPlan:
    return BucketPlan(
        start=start,
        end=end,
        policy=BucketingPolicy(max_bucket_days=(end - start).days + 1),
        buckets=(Bucket(index=0, start_date=start, end_date=end),),
    )


def _dv(value: str, day: date = DAY_1) -> DatedValue:
    return DatedValue(value=Decimal(value), observed_date=day)


def _empty_scalar(bucket: Bucket | None = None) -> ScalarBucketStatistics:
    return ScalarBucketStatistics(
        bucket=bucket if bucket is not None else _bucket(),
        observation_count=0,
        first=None,
        minimum=None,
        maximum=None,
        last=None,
    )


def _scalar(
    *,
    bucket: Bucket | None = None,
    count: int = 2,
    first: DatedValue | None = None,
    minimum: DatedValue | None = None,
    maximum: DatedValue | None = None,
    last: DatedValue | None = None,
) -> ScalarBucketStatistics:
    """A valid non-empty scalar aggregate, with every field individually overridable."""
    return ScalarBucketStatistics(
        bucket=bucket if bucket is not None else _bucket(),
        observation_count=count,
        first=first if first is not None else _dv("10", DAY_1),
        minimum=minimum if minimum is not None else _dv("10", DAY_1),
        maximum=maximum if maximum is not None else _dv("20", DAY_2),
        last=last if last is not None else _dv("20", DAY_2),
    )


# ---------------------------------------------------------------------------
# 1. DatedValue - the atom every statistic is made of
# ---------------------------------------------------------------------------


def test_dated_value_accepts_a_finite_decimal_on_a_real_date():
    value = _dv("1.2345", DAY_2)
    assert value.value == Decimal("1.2345")
    assert value.observed_date == DAY_2


def test_dated_value_rejects_a_float_value():
    # Situation: a plugin (or a helper converting one) hands back a float. A float
    # would survive arithmetic but reintroduce binary rounding into an exported
    # financial figure, so the aggregate refuses it at the boundary.
    with pytest.raises(TypeError, match="value must be a Decimal"):
        DatedValue(value=1.5, observed_date=DAY_1)  # type: ignore[arg-type]


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity"])
def test_dated_value_rejects_non_finite_decimals(raw: str):
    # Situation: a division by a zero previous close produced NaN/Inf upstream.
    # Exporting it would render "NaN" into the prompt as if it were an observation.
    with pytest.raises(ValueError, match="value must be finite"):
        DatedValue(value=Decimal(raw), observed_date=DAY_1)


def test_dated_value_rejects_a_datetime_masquerading_as_a_date():
    # Situation: a caller passes `datetime.now()` instead of `.date()`. `datetime`
    # is a `date` subclass, so only an exact type check catches it - and it must,
    # because a datetime silently breaks bucket containment comparisons.
    with pytest.raises(TypeError, match="observed_date must be a datetime.date instance"):
        DatedValue(value=Decimal("1"), observed_date=datetime(2026, 3, 2, 12, 0))


# ---------------------------------------------------------------------------
# 2. ScalarBucketStatistics - the per-bucket scalar contract
# ---------------------------------------------------------------------------


def test_scalar_statistics_rejects_a_non_bucket():
    with pytest.raises(TypeError, match="bucket must be a Bucket"):
        ScalarBucketStatistics(bucket="2026-03-02", observation_count=0, first=None, minimum=None, maximum=None, last=None)  # type: ignore[arg-type]


def test_scalar_statistics_rejects_a_bool_observation_count():
    # Situation: `observation_count=bool(points)` instead of `len(points)`. `bool`
    # is an `int` subclass, so only the explicit bool check catches the typo.
    with pytest.raises(TypeError, match="observation_count must be an int"):
        ScalarBucketStatistics(bucket=_bucket(), observation_count=True, first=None, minimum=None, maximum=None, last=None)


def test_scalar_statistics_rejects_a_negative_observation_count():
    with pytest.raises(ValueError, match="observation_count must be non-negative"):
        ScalarBucketStatistics(bucket=_bucket(), observation_count=-1, first=None, minimum=None, maximum=None, last=None)


def test_empty_scalar_statistics_must_not_carry_values():
    # Situation: a carry-forward/warm-up helper fills an empty bucket with the
    # previous bucket's close. AI Export never synthesizes observations, so an
    # empty bucket carrying a value is a contract breach, not a convenience.
    with pytest.raises(ValueError, match="empty scalar statistics must not contain values"):
        ScalarBucketStatistics(bucket=_bucket(), observation_count=0, first=_dv("10"), minimum=None, maximum=None, last=None)


def test_non_empty_scalar_statistics_require_every_statistic():
    with pytest.raises(ValueError, match="non-empty scalar statistics require first/minimum/maximum/last"):
        ScalarBucketStatistics(bucket=_bucket(), observation_count=1, first=_dv("10"), minimum=_dv("10"), maximum=_dv("10"), last=None)


def test_scalar_statistics_reject_raw_decimals_instead_of_dated_values():
    # Situation: a refactor drops `_dated_value()` and passes the bare Decimal,
    # which would lose the real observation date the prompt is supposed to show.
    with pytest.raises(TypeError, match="scalar statistics must contain DatedValue instances"):
        _scalar(first=Decimal("10"))  # type: ignore[arg-type]


def test_scalar_statistics_reject_an_observed_date_outside_the_bucket():
    # Situation: warm-up data leaks past `slice_to_requested_period` and the
    # minimum of the series is a pre-period point.
    with pytest.raises(ValueError, match="observed_date must fall inside the bucket"):
        _scalar(minimum=_dv("10", OUTSIDE))


def test_scalar_statistics_reject_first_after_last():
    # Situation: the points were not sorted chronologically before aggregation.
    with pytest.raises(ValueError, match="first observed_date must not follow last observed_date"):
        _scalar(first=_dv("10", DAY_3), minimum=_dv("10", DAY_3), last=_dv("20", DAY_1), maximum=_dv("20", DAY_1))


def test_scalar_statistics_reject_inverted_minimum_and_maximum():
    # Situation: min/max got swapped at the call site.
    with pytest.raises(ValueError, match="minimum value must not exceed maximum value"):
        _scalar(minimum=_dv("30", DAY_1), maximum=_dv("20", DAY_2), first=_dv("30", DAY_1), last=_dv("20", DAY_2))


def test_scalar_statistics_reject_a_first_value_outside_the_range():
    with pytest.raises(ValueError, match="first value must fall inside minimum/maximum"):
        _scalar(first=_dv("99", DAY_1), minimum=_dv("10", DAY_1), maximum=_dv("20", DAY_2), last=_dv("20", DAY_2))


def test_scalar_statistics_reject_a_last_value_outside_the_range():
    with pytest.raises(ValueError, match="last value must fall inside minimum/maximum"):
        _scalar(first=_dv("10", DAY_1), minimum=_dv("10", DAY_1), maximum=_dv("20", DAY_2), last=_dv("99", DAY_2))


# ---------------------------------------------------------------------------
# 3. BandBucketStatistics - three independent scalar series, one bucket
# ---------------------------------------------------------------------------


def _band(*, count: int = 2, lower=None, middle=None, upper=None, bucket: Bucket | None = None) -> BandBucketStatistics:
    resolved = bucket if bucket is not None else _bucket()
    return BandBucketStatistics(
        bucket=resolved,
        observation_count=count,
        lower=lower if lower is not None else _scalar(bucket=resolved),
        middle=middle if middle is not None else _scalar(bucket=resolved),
        upper=upper if upper is not None else _scalar(bucket=resolved),
    )


def test_band_statistics_rejects_a_non_bucket():
    with pytest.raises(TypeError, match="bucket must be a Bucket"):
        BandBucketStatistics(bucket=object(), observation_count=0, lower=_empty_scalar(), middle=_empty_scalar(), upper=_empty_scalar())  # type: ignore[arg-type]


def test_band_statistics_rejects_a_bool_observation_count():
    with pytest.raises(TypeError, match="observation_count must be an int"):
        _band(count=True)


def test_band_statistics_rejects_a_negative_observation_count():
    with pytest.raises(ValueError, match="observation_count must be non-negative"):
        _band(count=-1)


def test_band_statistics_reject_a_non_scalar_component():
    # Situation: a band plugin returns a raw list for one of its three lines.
    with pytest.raises(TypeError, match="band components must be ScalarBucketStatistics"):
        _band(middle=[])  # type: ignore[arg-type]


def test_band_statistics_reject_a_component_from_another_bucket():
    # Situation: an off-by-one in the bucket loop pairs bucket N's band with
    # bucket N+1's middle line - the envelope would then mix two periods.
    other = _bucket(index=1, start=OUTSIDE, end=OUTSIDE)
    with pytest.raises(ValueError, match="must reference the same bucket"):
        _band(upper=_empty_scalar(bucket=other))


def test_band_statistics_reject_a_component_count_above_the_band_count():
    # Situation: the band count was taken from the visible points while a
    # component was aggregated over the warm-up-inclusive series.
    with pytest.raises(ValueError, match="cannot exceed band observation_count"):
        _band(count=1, lower=_scalar(count=2))


def test_empty_band_rejects_populated_components_via_the_stricter_per_component_guard():
    # A band that says "no observations" while one of its three lines carries some
    # is still rejected — by the per-component check (`component.observation_count >
    # self.observation_count`), which any populated component trips once the band
    # count is 0. There used to be a second, dedicated check below the loop saying
    # the same thing; it could never fire, and it was removed. This test is what
    # makes that removal safe: it pins the invariant rather than the line that
    # enforced it, so the protection cannot disappear unnoticed.
    with pytest.raises(ValueError, match="cannot exceed band observation_count"):
        BandBucketStatistics(bucket=_bucket(), observation_count=0, lower=_scalar(), middle=_empty_scalar(), upper=_empty_scalar())


def test_non_empty_band_statistics_require_one_observed_component():
    # Situation: every one of the three lines was `None` for the whole bucket
    # while the bucket itself reported observations - a band with no band.
    with pytest.raises(ValueError, match="require at least one observed component"):
        BandBucketStatistics(bucket=_bucket(), observation_count=2, lower=_empty_scalar(), middle=_empty_scalar(), upper=_empty_scalar())


# ---------------------------------------------------------------------------
# 4. BandEnvelopeRepresentative - the synthetic chart envelope
# ---------------------------------------------------------------------------


def test_band_envelope_rejects_a_non_bucket():
    with pytest.raises(TypeError, match="bucket must be a Bucket"):
        BandEnvelopeRepresentative(bucket=None, lower=None, middle=None, upper=None)  # type: ignore[arg-type]


def test_band_envelope_rejects_raw_decimal_components():
    with pytest.raises(TypeError, match="band envelope components must be DatedValue instances"):
        BandEnvelopeRepresentative(bucket=_bucket(), lower=Decimal("1"), middle=None, upper=None)  # type: ignore[arg-type]


def test_band_envelope_rejects_a_component_dated_outside_the_bucket():
    with pytest.raises(ValueError, match="observed dates must fall inside the bucket"):
        BandEnvelopeRepresentative(bucket=_bucket(), lower=_dv("1", OUTSIDE), middle=None, upper=None)


def test_band_envelope_rejects_an_unordered_envelope():
    # Situation: `select_band_envelope` is fed statistics whose "lower" line is
    # actually above its "upper" line (mis-wired output keys in a plugin). A
    # chart band drawn from that is visually and semantically wrong.
    with pytest.raises(ValueError, match="lower <= middle <= upper"):
        BandEnvelopeRepresentative(bucket=_bucket(), lower=_dv("30", DAY_1), middle=_dv("20", DAY_1), upper=_dv("40", DAY_2))


def test_band_envelope_tolerates_partially_present_components():
    # Only the present components are compared, so a band whose middle line has
    # no observation in this bucket still yields a valid envelope.
    envelope = BandEnvelopeRepresentative(bucket=_bucket(), lower=_dv("10", DAY_1), middle=None, upper=_dv("20", DAY_2))
    assert envelope.middle is None
    assert envelope.lower.value < envelope.upper.value


# ---------------------------------------------------------------------------
# 5. Selectors and the profile dispatcher
# ---------------------------------------------------------------------------


def test_select_scalar_representative_rejects_the_wrong_statistics_type():
    with pytest.raises(TypeError, match="statistics must be ScalarBucketStatistics"):
        select_scalar_representative(_band(), SignalAggregationProfile.LAST_WITH_RANGE)


def test_select_scalar_representative_rejects_a_plain_string_profile():
    # Situation: a caller passes the raw catalog string instead of the enum.
    with pytest.raises(TypeError, match="profile must be a SignalAggregationProfile"):
        select_scalar_representative(_scalar(), "last_with_range")  # type: ignore[arg-type]


def test_select_band_envelope_rejects_the_wrong_statistics_type():
    with pytest.raises(TypeError, match="statistics must be BandBucketStatistics"):
        select_band_envelope(_scalar())


def test_select_band_envelope_rejects_a_non_band_profile():
    with pytest.raises(ValueError, match="requires band_envelope profile"):
        select_band_envelope(_band(), SignalAggregationProfile.LAST_WITH_RANGE)


def test_select_band_envelope_returns_min_last_max():
    envelope = select_band_envelope(_band())
    assert (envelope.lower.value, envelope.middle.value, envelope.upper.value) == (Decimal("10"), Decimal("20"), Decimal("20"))


def test_dispatcher_rejects_a_plain_string_profile():
    with pytest.raises(TypeError, match="profile must be a SignalAggregationProfile"):
        aggregate_signal_buckets("last_with_range", (), _plan())  # type: ignore[arg-type]


def test_dispatcher_rejects_events_that_are_not_discrete_events():
    # Situation: an events_verbatim plugin emits observed points instead of
    # annotations - the events section would then contain unlabelled numbers.
    with pytest.raises(TypeError, match="events_verbatim requires DiscreteEvent values"):
        aggregate_signal_buckets(
            SignalAggregationProfile.EVENTS_VERBATIM,
            (ObservedPoint(date=DAY_1, value=Decimal("1")),),
            _plan(),
        )


def test_dispatcher_rejects_a_profile_with_no_aggregation_arm(monkeypatch: pytest.MonkeyPatch):
    # Every current SignalAggregationProfile member has a dispatch arm, so the
    # final `raise` is only reachable in the situation it was written for: a new
    # member is added to the schema and nobody wires an arm for it here. Shrinking
    # the scalar-profile set reproduces exactly that state - an otherwise valid
    # profile that no arm claims - and proves the dispatcher fails loudly instead
    # of quietly returning an empty aggregate for a Signal the user asked for.
    monkeypatch.setattr(
        aggregators,
        "_SCALAR_AGGREGATION_PROFILES",
        frozenset(_SCALAR_AGGREGATION_PROFILES - {SignalAggregationProfile.MIN_WITH_RANGE}),
    )
    with pytest.raises(ValueError, match="unsupported signal aggregation profile: min_with_range"):
        aggregate_signal_buckets(SignalAggregationProfile.MIN_WITH_RANGE, (), _plan())


# ---------------------------------------------------------------------------
# 6. Entry-point type guards on the aggregate_* functions
# ---------------------------------------------------------------------------


def test_aggregate_scalar_statistics_rejects_band_points():
    with pytest.raises(TypeError, match="points must contain ObservedPoint values"):
        aggregate_scalar_statistics(
            (BandObservedPoint(date=DAY_1, lower=Decimal("1"), middle=Decimal("2"), upper=Decimal("3")),),
            _plan(),
        )


def test_aggregate_band_statistics_rejects_scalar_points():
    with pytest.raises(TypeError, match="points must contain BandObservedPoint values"):
        aggregate_band_statistics((ObservedPoint(date=DAY_1, value=Decimal("1")),), _plan())


def test_assign_discrete_events_rejects_observed_points():
    with pytest.raises(TypeError, match="events must contain DiscreteEvent values"):
        assign_discrete_events((ObservedPoint(date=DAY_1, value=Decimal("1")),), _plan())


def test_assign_by_date_rejects_a_plan_with_no_buckets():
    # `BucketPlan.__post_init__` forbids an empty plan, so the only way to reach
    # `_assign_by_date`'s own guard is a stand-in plan object - which is exactly
    # what a future alternative BucketPlan implementation would be.
    class _EmptyPlan:
        buckets: tuple = ()
        start = DAY_1
        end = DAY_3

    with pytest.raises(ValueError, match="plan must contain at least one bucket"):
        _assign_by_date((), _EmptyPlan())  # type: ignore[arg-type]


def test_discrete_events_survive_the_dispatcher_unchanged():
    # Positive counterpart to the rejection tests above: the same dispatcher call
    # that refuses wrong shapes must still preserve a well-formed event verbatim.
    event = DiscreteEvent(date=DAY_2, dedup_key=("e", 1), payload={"k": "v"})
    assigned = aggregate_signal_buckets(SignalAggregationProfile.EVENTS_VERBATIM, (event,), _plan())
    assert len(assigned) == 1
    assert assigned[0].events == (event,)
    assert assigned[0].event_count == 1
