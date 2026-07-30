"""Focused tests for the AI Export temporal engine (bucket policy/plan/aggregators/warm-up).

Covers: bucket-width formula edge cases (x<=7, monotonicity, [1,K] bounds,
convergence), plan construction (no null/overlapping buckets, full coverage,
final boundary at requested start, normative bucket counts, sub-week and very
long periods, determinism), aggregator semantics (OHLC, monetary sums,
multi-output continuous components, discrete event preservation/dedup, and
explicit empty buckets), and warm-up slicing (pre-start data never emitted).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from backend.app.schemas.signals import SignalAggregationProfile
from backend.app.services.ai_export.temporal import (
    BandBucketStatistics,
    BandObservedPoint,
    Bucket,
    BucketDetailLevel,
    BucketingPolicy,
    BucketPlan,
    ContinuousMultiOutputPoint,
    DiscreteEvent,
    MonetaryFlowEvent,
    ObservedPoint,
    ScalarBucketStatistics,
    aggregate_band_statistics,
    aggregate_continuous_multi_output,
    aggregate_monetary_flow,
    aggregate_ohlc,
    aggregate_scalar_statistics,
    aggregate_signal_buckets,
    assert_within_requested_period,
    assign_discrete_events,
    select_band_envelope,
    select_scalar_representative,
    slice_to_requested_period,
    warmup_window_start,
)

SNAPSHOT = date(2026, 1, 1)
AGGREGATION_FIXTURE = json.loads((Path(__file__).parents[1] / "fixtures" / "signals" / "aggregation_profiles.v1.json").read_text())


def _start(days_back: int) -> date:
    return SNAPSHOT - timedelta(days=days_back - 1)


def _policy(detail_level: BucketDetailLevel) -> BucketingPolicy:
    return BucketingPolicy.for_detail_level(detail_level)


def _plan(total_days: int, detail_level: BucketDetailLevel) -> BucketPlan:
    return BucketPlan.build(start=_start(total_days), end=SNAPSHOT, policy=_policy(detail_level))


# ---------------------------------------------------------------------------
# 1. BucketingPolicy: D(x) formula behaviour
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("detail_level", [BucketDetailLevel.COMPACT, BucketDetailLevel.STANDARD, BucketDetailLevel.FULL])
def test_bucket_width_is_one_for_offsets_within_first_week(detail_level: BucketDetailLevel):
    policy = _policy(detail_level)
    for x in range(0, 8):
        assert policy.bucket_width(x) == 1


@pytest.mark.parametrize("detail_level", [BucketDetailLevel.COMPACT, BucketDetailLevel.STANDARD, BucketDetailLevel.FULL])
def test_bucket_width_is_monotonically_non_decreasing(detail_level: BucketDetailLevel):
    policy = _policy(detail_level)
    widths = [policy.bucket_width(x) for x in range(0, 1000)]
    assert all(current <= following for current, following in zip(widths, widths[1:], strict=False))


@pytest.mark.parametrize("detail_level", [BucketDetailLevel.COMPACT, BucketDetailLevel.STANDARD, BucketDetailLevel.FULL])
def test_bucket_width_is_always_within_one_and_k(detail_level: BucketDetailLevel):
    policy = _policy(detail_level)
    k = policy.max_bucket_days
    for x in range(0, 2000):
        assert 1 <= policy.bucket_width(x) <= k


@pytest.mark.parametrize(
    "detail_level,k",
    [(BucketDetailLevel.COMPACT, 30), (BucketDetailLevel.STANDARD, 14), (BucketDetailLevel.FULL, 7)],
)
def test_bucket_width_converges_to_k_for_large_offsets(detail_level: BucketDetailLevel, k: int):
    policy = _policy(detail_level)
    assert policy.bucket_width(100_000) == k


def test_full_detail_level_stays_daily_for_at_least_first_14_days():
    policy = _policy(BucketDetailLevel.FULL)
    x = 0
    days_covered = 0
    while days_covered < 14:
        width = policy.bucket_width(x)
        assert width == 1
        days_covered += width
        x += width


def test_bucketing_policy_rejects_invalid_construction():
    with pytest.raises(ValueError):
        BucketingPolicy(max_bucket_days=0)
    with pytest.raises(TypeError):
        BucketingPolicy(max_bucket_days="30")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        BucketingPolicy.for_detail_level("compact")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. BucketPlan: construction invariants and normative counts
# ---------------------------------------------------------------------------


def _assert_boundaries(plan: BucketPlan, requested_start: date, snapshot_as_of: date) -> None:
    """Binding acceptance assertion: oldest.start==requested_start, newest.end==snapshot_as_of."""

    assert plan.buckets[0].start_date == requested_start, "oldest bucket must start exactly at requested_start"
    assert plan.buckets[-1].end_date == snapshot_as_of, "newest bucket must end exactly at snapshot_as_of"


@pytest.mark.parametrize(
    "T,expected_count",
    [(90, 20), (180, 23), (365, 29)],
)
def test_compact_normative_bucket_counts(T: int, expected_count: int):
    requested_start = _start(T)
    plan = BucketPlan.build(start=requested_start, end=SNAPSHOT, policy=_policy(BucketDetailLevel.COMPACT))
    assert len(plan.buckets) == expected_count
    _assert_boundaries(plan, requested_start, SNAPSHOT)


@pytest.mark.parametrize(
    "T,expected_count",
    [(90, 26), (180, 33), (365, 46)],
)
def test_standard_normative_bucket_counts(T: int, expected_count: int):
    requested_start = _start(T)
    plan = BucketPlan.build(start=requested_start, end=SNAPSHOT, policy=_policy(BucketDetailLevel.STANDARD))
    assert len(plan.buckets) == expected_count
    _assert_boundaries(plan, requested_start, SNAPSHOT)


@pytest.mark.parametrize(
    "T,expected_count",
    [(90, 35), (180, 49), (365, 75)],
)
def test_full_normative_bucket_counts(T: int, expected_count: int):
    requested_start = _start(T)
    plan = BucketPlan.build(start=requested_start, end=SNAPSHOT, policy=_policy(BucketDetailLevel.FULL))
    assert len(plan.buckets) == expected_count
    _assert_boundaries(plan, requested_start, SNAPSHOT)


@pytest.mark.parametrize("detail_level", [BucketDetailLevel.COMPACT, BucketDetailLevel.STANDARD, BucketDetailLevel.FULL])
@pytest.mark.parametrize("total_days", [1, 2, 5, 7, 8, 90, 180, 365, 1500, 7300])
def test_plan_has_no_null_overlapping_or_gapped_buckets_and_full_coverage(detail_level: BucketDetailLevel, total_days: int):
    plan = _plan(total_days, detail_level)
    assert plan.buckets, "plan must always contain at least one bucket"

    for bucket in plan.buckets:
        assert bucket.day_count >= 1, "no null intervals allowed"

    for previous, current in zip(plan.buckets, plan.buckets[1:], strict=False):
        assert current.start_date == previous.end_date + timedelta(days=1), "buckets must be contiguous, no gap/overlap"

    assert plan.buckets[0].start_date == plan.start, "final (oldest) bucket must start exactly at requested start"
    assert plan.buckets[-1].end_date == plan.end, "newest bucket must end exactly at snapshot_as_of"

    total_covered_days = sum(bucket.day_count for bucket in plan.buckets)
    assert total_covered_days == total_days, "buckets must cover the full inclusive requested period exactly once"


@pytest.mark.parametrize("detail_level", [BucketDetailLevel.COMPACT, BucketDetailLevel.STANDARD, BucketDetailLevel.FULL])
@pytest.mark.parametrize("total_days", [1, 3, 7])
def test_short_periods_under_a_week_are_fully_daily(detail_level: BucketDetailLevel, total_days: int):
    plan = _plan(total_days, detail_level)
    assert len(plan.buckets) == total_days
    assert all(bucket.day_count == 1 for bucket in plan.buckets)


def test_very_long_custom_period_terminates_and_covers_fully():
    total_days = 20 * 365 + 5  # 20-year custom period
    plan = _plan(total_days, BucketDetailLevel.COMPACT)
    assert plan.buckets[0].start_date == plan.start
    assert plan.buckets[-1].end_date == plan.end
    assert sum(bucket.day_count for bucket in plan.buckets) == total_days


def test_plan_output_is_oldest_to_newest_with_sequential_indices():
    plan = _plan(365, BucketDetailLevel.COMPACT)
    assert [bucket.index for bucket in plan.buckets] == list(range(len(plan.buckets)))
    dates = [bucket.start_date for bucket in plan.buckets]
    assert dates == sorted(dates)


def test_plan_construction_is_deterministic_across_repeated_builds():
    policy = _policy(BucketDetailLevel.STANDARD)
    start, end = _start(365), SNAPSHOT
    first = BucketPlan.build(start=start, end=end, policy=policy)
    second = BucketPlan.build(start=start, end=end, policy=policy)
    assert first.buckets == second.buckets


def test_inclusive_requested_day_count_definition():
    plan = _plan(90, BucketDetailLevel.COMPACT)
    assert plan.requested_day_count == 90
    assert (plan.end - plan.start).days + 1 == 90


def test_bucket_plan_reusable_across_multiple_components():
    plan = _plan(180, BucketDetailLevel.STANDARD)
    prices = tuple(ObservedPoint(date=plan.start + timedelta(days=i), value=Decimal(100 + i)) for i in range(180))
    flows = tuple(MonetaryFlowEvent(date=plan.start + timedelta(days=i), amount=Decimal("10")) for i in range(0, 180, 30))

    ohlc = aggregate_ohlc(prices, plan)
    flow = aggregate_monetary_flow(flows, plan)

    assert len(ohlc) == len(plan.buckets) == len(flow)
    assert sum(item.observation_count for item in ohlc) == 180


def test_plan_rejects_invalid_construction_inputs():
    with pytest.raises(ValueError):
        BucketPlan.build(start=SNAPSHOT, end=SNAPSHOT - timedelta(days=1), policy=_policy(BucketDetailLevel.COMPACT))
    with pytest.raises(TypeError):
        BucketPlan.build(start="2026-01-01", end=SNAPSHOT, policy=_policy(BucketDetailLevel.COMPACT))  # type: ignore[arg-type]


def test_bucket_plan_direct_construction_enforces_full_invariants():
    """BucketPlan is a public dataclass: directly constructed instances must be
    rejected unless every invariant that ``build`` guarantees actually holds."""

    policy = _policy(BucketDetailLevel.COMPACT)
    start, end = date(2026, 1, 1), date(2026, 1, 10)  # 10-day period

    valid_plan = BucketPlan.build(start=start, end=end, policy=policy)
    assert valid_plan.buckets  # sanity: build() itself must satisfy __post_init__

    # Invalid start/end types or ordering.
    with pytest.raises(TypeError):
        BucketPlan(start="2026-01-01", end=end, policy=policy, buckets=valid_plan.buckets)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        BucketPlan(start=end, end=start, policy=policy, buckets=valid_plan.buckets)

    # Invalid policy.
    with pytest.raises(TypeError):
        BucketPlan(start=start, end=end, policy="not-a-policy", buckets=valid_plan.buckets)  # type: ignore[arg-type]

    # Empty / wrong-type buckets.
    with pytest.raises(ValueError):
        BucketPlan(start=start, end=end, policy=policy, buckets=())
    with pytest.raises(TypeError):
        BucketPlan(start=start, end=end, policy=policy, buckets=("not-a-bucket",))  # type: ignore[arg-type]

    # Non-sequential indexes.
    reindexed = tuple(Bucket(index=bucket.index * 2, start_date=bucket.start_date, end_date=bucket.end_date) for bucket in valid_plan.buckets)
    with pytest.raises(ValueError):
        BucketPlan(start=start, end=end, policy=policy, buckets=reindexed)

    # Oldest bucket does not start exactly at the plan's start.
    wrong_first = (Bucket(index=0, start_date=start + timedelta(days=1), end_date=start + timedelta(days=1)), *valid_plan.buckets[1:])
    with pytest.raises(ValueError):
        BucketPlan(start=start, end=end, policy=policy, buckets=wrong_first)

    # Newest bucket does not end exactly at the plan's end (deliberately extends past plan.end).
    wrong_last = (
        *valid_plan.buckets[:-1],
        Bucket(index=len(valid_plan.buckets) - 1, start_date=valid_plan.buckets[-1].start_date, end_date=end + timedelta(days=1)),
    )
    with pytest.raises(ValueError):
        BucketPlan(start=start, end=end, policy=policy, buckets=wrong_last)


def test_bucket_plan_direct_construction_rejects_gaps_and_overlaps():
    """Shift one boundary of a >=2-day-wide bucket to create a gap/overlap.

    A bucket with day_count >= 2 is required so shifting one edge by a single
    day never violates that individual Bucket's own start<=end invariant —
    the failure being tested here is the plan-level contiguity check, not
    Bucket's own ordering check.
    """

    policy = _policy(BucketDetailLevel.COMPACT)
    start, end = _start(180), SNAPSHOT  # wide policy ramp-up guarantees multi-day buckets
    plan = BucketPlan.build(start=start, end=end, policy=policy)

    widenable_index = next(index for index, bucket in enumerate(plan.buckets) if 0 < index < len(plan.buckets) - 1 and bucket.day_count >= 2)
    widened = plan.buckets[widenable_index]

    gapped = list(plan.buckets)
    gapped[widenable_index] = Bucket(index=widened.index, start_date=widened.start_date, end_date=widened.end_date - timedelta(days=1))
    with pytest.raises(ValueError):
        BucketPlan(start=start, end=end, policy=policy, buckets=tuple(gapped))

    overlapped = list(plan.buckets)
    overlapped[widenable_index] = Bucket(index=widened.index, start_date=widened.start_date - timedelta(days=1), end_date=widened.end_date)
    with pytest.raises(ValueError):
        BucketPlan(start=start, end=end, policy=policy, buckets=tuple(overlapped))


def test_bucket_rejects_inverted_date_range():
    with pytest.raises(ValueError):
        Bucket(index=0, start_date=date(2026, 1, 2), end_date=date(2026, 1, 1))


# ---------------------------------------------------------------------------
# 3. Aggregators
# ---------------------------------------------------------------------------


def _small_plan() -> BucketPlan:
    # 10-day full-detail plan -> every bucket is exactly 1 day wide (x<=7 covers most, and
    # x=8,9 still round to 1 for K=7), giving deterministic 1:1 bucket-to-day mapping for tests.
    return _plan(10, BucketDetailLevel.FULL)


def _fixture_plan(payload: dict[str, str]) -> BucketPlan:
    start = date.fromisoformat(payload["start"])
    end = date.fromisoformat(payload["end"])
    return BucketPlan(
        start=start,
        end=end,
        policy=BucketingPolicy(max_bucket_days=(end - start).days + 1),
        buckets=(Bucket(index=0, start_date=start, end_date=end),),
    )


def _dated_value_payload(value) -> dict[str, str] | None:
    if value is None:
        return None
    return {
        "value": format(value.value, "f"),
        "date": value.observed_date.isoformat(),
    }


def _scalar_statistics_payload(statistics: ScalarBucketStatistics) -> dict[str, object]:
    return {
        "observation_count": statistics.observation_count,
        "first": _dated_value_payload(statistics.first),
        "min": _dated_value_payload(statistics.minimum),
        "max": _dated_value_payload(statistics.maximum),
        "last": _dated_value_payload(statistics.last),
    }


def test_shared_fixture_scalar_stats_profiles_empty_single_and_ties():
    for case in AGGREGATION_FIXTURE["scalar_cases"]:
        plan = _fixture_plan(case["bucket"])
        points = tuple(
            ObservedPoint(
                date=date.fromisoformat(point["date"]),
                value=Decimal(point["value"]),
            )
            for point in case["points"]
        )
        expected = case["expected"]
        expected_statistics = {key: value for key, value in expected.items() if key != "representatives"}

        direct = aggregate_scalar_statistics(points, plan)
        assert len(direct) == 1
        assert _scalar_statistics_payload(direct[0]) == expected_statistics

        for profile_value, expected_representative in expected["representatives"].items():
            profile = SignalAggregationProfile(profile_value)
            dispatched = aggregate_signal_buckets(profile, points, plan)
            assert dispatched == direct
            assert _dated_value_payload(select_scalar_representative(direct[0], profile)) == expected_representative


def test_shared_fixture_band_stats_preserve_independent_dates_and_valid_envelope():
    case = AGGREGATION_FIXTURE["band_case"]
    plan = _fixture_plan(case["bucket"])
    points = tuple(
        BandObservedPoint(
            date=date.fromisoformat(point["date"]),
            lower=Decimal(point["lower"]),
            middle=Decimal(point["middle"]),
            upper=Decimal(point["upper"]),
        )
        for point in case["points"]
    )

    direct = aggregate_band_statistics(points, plan)
    dispatched = aggregate_signal_buckets(
        SignalAggregationProfile.BAND_ENVELOPE,
        points,
        plan,
    )

    assert dispatched == direct
    assert len(direct) == 1
    statistics = direct[0]
    assert isinstance(statistics, BandBucketStatistics)
    expected = case["expected"]
    assert statistics.observation_count == expected["observation_count"]
    for component in ("lower", "middle", "upper"):
        assert _scalar_statistics_payload(getattr(statistics, component)) == expected[component]

    envelope = select_band_envelope(statistics)
    assert {component: _dated_value_payload(getattr(envelope, component)) for component in ("lower", "middle", "upper")} == expected["envelope"]
    assert envelope.lower.value <= envelope.middle.value <= envelope.upper.value


def test_shared_fixture_events_verbatim_preserves_and_deduplicates():
    case = AGGREGATION_FIXTURE["events_case"]
    plan = _fixture_plan(case["bucket"])
    events = tuple(
        DiscreteEvent(
            date=date.fromisoformat(event["date"]),
            dedup_key=event["dedup_key"],
            payload=event["payload"],
        )
        for event in case["events"]
    )

    result = aggregate_signal_buckets(
        SignalAggregationProfile.EVENTS_VERBATIM,
        events,
        plan,
    )

    assert len(result) == 1
    assert [
        {
            "date": event.date.isoformat(),
            "dedup_key": event.dedup_key,
            "payload": dict(event.payload),
        }
        for event in result[0].events
    ] == case["expected"]


def test_signal_profile_dispatcher_rejects_wrong_input_shapes_and_warmup_leakage():
    plan = _fixture_plan({"start": "2026-01-01", "end": "2026-01-03"})
    scalar = ObservedPoint(date=plan.start, value=Decimal("1"))
    band = BandObservedPoint(
        date=plan.start,
        lower=Decimal("1"),
        middle=Decimal("2"),
        upper=Decimal("3"),
    )

    with pytest.raises(TypeError, match="BandObservedPoint"):
        aggregate_signal_buckets(
            SignalAggregationProfile.BAND_ENVELOPE,
            (scalar,),
            plan,
        )
    with pytest.raises(TypeError, match="ObservedPoint"):
        aggregate_signal_buckets(
            SignalAggregationProfile.LAST_WITH_RANGE,
            (band,),
            plan,
        )
    with pytest.raises(ValueError, match="not a scalar"):
        select_scalar_representative(
            aggregate_scalar_statistics((scalar,), plan)[0],
            SignalAggregationProfile.EVENTS_VERBATIM,
        )
    with pytest.raises(ValueError, match="outside"):
        aggregate_signal_buckets(
            SignalAggregationProfile.MIN_WITH_RANGE,
            (
                ObservedPoint(
                    date=plan.start - timedelta(days=1),
                    value=Decimal("1"),
                ),
            ),
            plan,
        )


def test_band_observation_rejects_missing_or_inverted_components():
    with pytest.raises(ValueError, match="at least one"):
        BandObservedPoint(date=date(2026, 1, 1))
    with pytest.raises(ValueError, match="lower <= middle <= upper"):
        BandObservedPoint(
            date=date(2026, 1, 1),
            lower=Decimal("3"),
            middle=Decimal("2"),
            upper=Decimal("4"),
        )


def test_ohlc_first_min_max_last_and_observation_count():
    plan = _small_plan()
    day0 = plan.start
    points = (
        ObservedPoint(date=day0, value=Decimal("10")),
        ObservedPoint(date=day0 + timedelta(days=1), value=Decimal("15")),
        ObservedPoint(date=day0 + timedelta(days=1), value=Decimal("5")),
        ObservedPoint(date=day0 + timedelta(days=1), value=Decimal("12")),
    )
    result = aggregate_ohlc(points, plan)
    bucket_for_day1 = result[1]
    assert bucket_for_day1.first == Decimal("15")
    assert bucket_for_day1.minimum == Decimal("5")
    assert bucket_for_day1.maximum == Decimal("15")
    assert bucket_for_day1.last == Decimal("12")
    assert bucket_for_day1.observation_count == 3


def test_ohlc_handles_weekends_missing_observations_as_explicit_empty_buckets():
    plan = _small_plan()
    day0 = plan.start
    # Only provide observations for even offsets, simulating missing weekend data.
    points = tuple(ObservedPoint(date=day0 + timedelta(days=i), value=Decimal(i)) for i in range(0, 10, 2))
    result = aggregate_ohlc(points, plan)
    for index, bucket_result in enumerate(result):
        if index % 2 == 0:
            assert bucket_result.observation_count == 1
            assert bucket_result.first is not None
        else:
            assert bucket_result.observation_count == 0
            assert bucket_result.first is None
            assert bucket_result.minimum is None
            assert bucket_result.maximum is None
            assert bucket_result.last is None


def test_monetary_flow_totals_and_explicit_zero_empty_buckets():
    plan = _small_plan()
    day0 = plan.start
    events = (
        MonetaryFlowEvent(date=day0, amount=Decimal("100.50")),
        MonetaryFlowEvent(date=day0, amount=Decimal("-20.00")),
    )
    result = aggregate_monetary_flow(events, plan)
    assert result[0].total == Decimal("80.50")
    assert result[0].event_count == 2
    for empty_bucket in result[1:]:
        assert empty_bucket.total == Decimal(0)
        assert empty_bucket.event_count == 0


def test_multi_output_continuous_component_aggregation():
    plan = _small_plan()
    day0 = plan.start
    points = (
        ContinuousMultiOutputPoint(date=day0, values={"macd": Decimal("1.0"), "signal": Decimal("0.5")}),
        ContinuousMultiOutputPoint(date=day0 + timedelta(days=1), values={"macd": Decimal("2.0"), "signal": Decimal("0.2")}),
        ContinuousMultiOutputPoint(date=day0 + timedelta(days=1), values={"macd": Decimal("-1.0"), "signal": Decimal("0.9")}),
    )
    result = aggregate_continuous_multi_output(points, plan)
    bucket0, bucket1 = result[0], result[1]

    assert bucket0.first == {"macd": Decimal("1.0"), "signal": Decimal("0.5")}
    assert bucket0.observation_count == 1

    assert bucket1.first == {"macd": Decimal("2.0"), "signal": Decimal("0.2")}
    assert bucket1.last == {"macd": Decimal("-1.0"), "signal": Decimal("0.9")}
    assert bucket1.minimum == {"macd": Decimal("-1.0"), "signal": Decimal("0.2")}
    assert bucket1.maximum == {"macd": Decimal("2.0"), "signal": Decimal("0.9")}
    assert bucket1.observation_count == 2

    for empty_bucket in result[2:]:
        assert empty_bucket.observation_count == 0
        assert empty_bucket.first is None


def test_multi_output_rejects_inconsistent_output_keys_within_a_bucket():
    plan = _small_plan()
    day0 = plan.start
    points = (
        ContinuousMultiOutputPoint(date=day0, values={"macd": Decimal("1.0")}),
        ContinuousMultiOutputPoint(date=day0, values={"macd": Decimal("2.0"), "signal": Decimal("0.1")}),
    )
    with pytest.raises(ValueError):
        aggregate_continuous_multi_output(points, plan)


def test_discrete_events_preserve_every_event_and_dedup_by_caller_supplied_key():
    plan = _small_plan()
    day0 = plan.start
    events = (
        DiscreteEvent(date=day0, dedup_key="tx-1", payload={"amount": 10}),
        DiscreteEvent(date=day0, dedup_key="tx-1", payload={"amount": 999}),  # duplicate, must be dropped, not averaged
        DiscreteEvent(date=day0, dedup_key="tx-2", payload={"amount": 20}),
    )
    result = assign_discrete_events(events, plan)
    bucket0 = result[0]
    assert bucket0.event_count == 2
    payloads_by_key = {event.dedup_key: event.payload for event in bucket0.events}
    assert payloads_by_key == {"tx-1": {"amount": 10}, "tx-2": {"amount": 20}}

    for empty_bucket in result[1:]:
        assert empty_bucket.event_count == 0
        assert empty_bucket.events == ()


def test_discrete_event_requires_hashable_dedup_key():
    with pytest.raises(TypeError):
        DiscreteEvent(date=date(2026, 1, 1), dedup_key=["not", "hashable"], payload=None)


def test_discrete_event_payload_accepts_and_freezes_nested_json_safe_values():
    event = DiscreteEvent(
        date=date(2026, 1, 1),
        dedup_key="tx-1",
        payload={
            "amount": 10,
            "tags": ["a", "b"],
            "nested": {"flag": True, "note": None, "rate": 1.5},
        },
    )
    assert event.payload["amount"] == 10
    assert event.payload["tags"] == ("a", "b")  # lists are frozen into tuples
    assert event.payload["nested"]["flag"] is True
    assert event.payload["nested"]["note"] is None
    assert event.payload["nested"]["rate"] == 1.5
    # frozen mappings/tuples must not be plain mutable list/dict instances.
    assert not isinstance(event.payload, dict)
    assert not isinstance(event.payload["tags"], list)


@pytest.mark.parametrize(
    "invalid_payload",
    [
        Decimal("1.5"),  # Decimal is not JSON-safe
        float("nan"),
        float("inf"),
        {"value": float("nan")},  # non-finite nested inside a mapping
        ["ok", float("inf")],  # non-finite nested inside a list
        {"value": Decimal("1")},  # non-JSON-safe nested inside a mapping
        {1: "non-string key"},
        object(),
        {"nested": {2: "non-string key"}},
    ],
)
def test_discrete_event_payload_rejects_non_json_safe_values(invalid_payload: object):
    with pytest.raises(ValueError):
        DiscreteEvent(date=date(2026, 1, 1), dedup_key="tx-1", payload=invalid_payload)


def test_discrete_event_payload_none_and_scalars_round_trip():
    for payload in (None, "text", True, 42, 3.14, ()):
        event = DiscreteEvent(date=date(2026, 1, 1), dedup_key="tx-1", payload=payload)
        assert event.payload == payload


def test_aggregators_reject_observations_outside_plan_coverage():
    plan = _small_plan()
    out_of_range = ObservedPoint(date=plan.start - timedelta(days=1), value=Decimal("1"))
    with pytest.raises(ValueError):
        aggregate_ohlc((out_of_range,), plan)


def test_observed_point_rejects_non_finite_and_non_decimal_values():
    with pytest.raises(TypeError):
        ObservedPoint(date=date(2026, 1, 1), value=1.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ObservedPoint(date=date(2026, 1, 1), value=Decimal("NaN"))
    with pytest.raises(ValueError):
        ObservedPoint(date=date(2026, 1, 1), value=Decimal("Infinity"))


# ---------------------------------------------------------------------------
# 4. Warm-up helpers
# ---------------------------------------------------------------------------


def test_warmup_window_start_subtracts_lookback_days():
    start = date(2026, 3, 1)
    assert warmup_window_start(start, 26) == date(2026, 2, 3)
    assert warmup_window_start(start, 0) == start
    with pytest.raises(ValueError):
        warmup_window_start(start, -1)


def test_warmup_window_start_clamps_at_date_min_instead_of_underflowing():
    start = date(1, 1, 5)
    assert warmup_window_start(start, 10) == date.min
    assert warmup_window_start(date.min, 1) == date.min
    assert warmup_window_start(start, 4) == date(1, 1, 1)  # exact boundary, no clamping needed
    assert warmup_window_start(start, 3) == date(1, 1, 2)


def test_slice_to_requested_period_excludes_pre_start_and_post_end_calculation_data():
    start = date(2026, 3, 1)
    end = date(2026, 3, 2)
    points = (
        ObservedPoint(date=start - timedelta(days=2), value=Decimal("1")),  # warm-up only, pre-start
        ObservedPoint(date=start - timedelta(days=1), value=Decimal("2")),  # warm-up only, pre-start
        ObservedPoint(date=start, value=Decimal("3")),
        ObservedPoint(date=end, value=Decimal("4")),
        ObservedPoint(date=end + timedelta(days=1), value=Decimal("5")),  # post-end over-fetch leakage
        ObservedPoint(date=end + timedelta(days=5), value=Decimal("6")),  # post-end over-fetch leakage
    )
    sliced = slice_to_requested_period(points, start, end)
    assert [point.date for point in sliced] == [start, end]


def test_slice_to_requested_period_rejects_invalid_range():
    start = date(2026, 3, 2)
    end = date(2026, 3, 1)  # end before start
    with pytest.raises(ValueError):
        slice_to_requested_period((), start, end)
    with pytest.raises(TypeError):
        slice_to_requested_period((), "2026-03-01", date(2026, 3, 2))  # type: ignore[arg-type]


def test_assert_within_requested_period_raises_for_pre_start_leakage():
    start = date(2026, 3, 1)
    end = date(2026, 3, 10)
    points = (ObservedPoint(date=start - timedelta(days=1), value=Decimal("1")),)
    with pytest.raises(ValueError):
        assert_within_requested_period(points, start, end)

    sliced = slice_to_requested_period(points, start, end)
    assert_within_requested_period(sliced, start, end)  # does not raise once sliced (empty here)


def test_assert_within_requested_period_raises_for_post_end_leakage():
    start = date(2026, 3, 1)
    end = date(2026, 3, 10)
    points = (ObservedPoint(date=end + timedelta(days=1), value=Decimal("1")),)
    with pytest.raises(ValueError):
        assert_within_requested_period(points, start, end)

    sliced = slice_to_requested_period(points, start, end)
    assert_within_requested_period(sliced, start, end)  # does not raise once sliced (empty here)


def test_assert_within_requested_period_rejects_invalid_range():
    with pytest.raises(ValueError):
        assert_within_requested_period((), date(2026, 3, 2), date(2026, 3, 1))
