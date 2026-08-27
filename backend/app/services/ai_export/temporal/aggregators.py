"""Generic, Portfolio-agnostic bucket aggregators for the temporal engine.

These operate purely on the typed observation/event models in
:mod:`backend.app.services.ai_export.temporal.points` and a
:class:`~backend.app.services.ai_export.temporal.plan.BucketPlan`. They
provide a typed seam for later integration (e.g. Portfolio performance) and
intentionally contain no Portfolio-performance-specific math.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType

from backend.app.schemas.signals import SignalAggregationProfile
from backend.app.services.ai_export.temporal.plan import Bucket, BucketPlan
from backend.app.services.ai_export.temporal.points import (
    BandObservedPoint,
    ContinuousMultiOutputPoint,
    Dated,
    DiscreteEvent,
    MonetaryFlowEvent,
    ObservedPoint,
    sort_by_date,
)

_SCALAR_AGGREGATION_PROFILES = frozenset(
    {
        SignalAggregationProfile.LAST_WITH_RANGE,
        SignalAggregationProfile.FIRST_WITH_RANGE,
        SignalAggregationProfile.MIN_WITH_RANGE,
        SignalAggregationProfile.MAX_WITH_RANGE,
    }
)


def _assign_by_date[T: Dated](items: Sequence[T], plan: BucketPlan) -> tuple[tuple[T, ...], ...]:
    """Assign date-bearing items into the plan's buckets (oldest-to-newest).

    Every item must fall within exactly one bucket's inclusive date range;
    buckets are contiguous and non-overlapping by construction, so this is a
    single linear pass over items pre-sorted by date.
    """

    buckets = plan.buckets
    if not buckets:
        raise ValueError("plan must contain at least one bucket")

    grouped: list[list[T]] = [[] for _ in buckets]
    bucket_index = 0
    for item in sort_by_date(items):
        while bucket_index < len(buckets) - 1 and item.date > buckets[bucket_index].end_date:
            bucket_index += 1
        if not buckets[bucket_index].contains(item.date):
            raise ValueError(f"observation date {item.date} falls outside the plan's requested period [{plan.start}, {plan.end}]")
        grouped[bucket_index].append(item)
    return tuple(tuple(bucket_items) for bucket_items in grouped)


@dataclass(frozen=True, slots=True)
class OhlcBucketAggregate:
    """OHLC-like aggregate for a single bucket of a scalar numeric series."""

    bucket: Bucket
    first: Decimal | None
    minimum: Decimal | None
    maximum: Decimal | None
    last: Decimal | None
    observation_count: int


@dataclass(frozen=True, slots=True)
class DatedValue:
    """One finite value paired with the real date on which it was observed."""

    value: Decimal
    observed_date: date

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError("value must be a Decimal")
        if not self.value.is_finite():
            raise ValueError("value must be finite")
        if type(self.observed_date) is not date:
            raise TypeError("observed_date must be a datetime.date instance")


@dataclass(frozen=True, slots=True)
class ScalarBucketStatistics:
    """Complete dated statistics for one scalar series inside one bucket."""

    bucket: Bucket
    observation_count: int
    first: DatedValue | None
    minimum: DatedValue | None
    maximum: DatedValue | None
    last: DatedValue | None

    def __post_init__(self) -> None:
        if not isinstance(self.bucket, Bucket):
            raise TypeError("bucket must be a Bucket")
        if not isinstance(self.observation_count, int) or isinstance(self.observation_count, bool):
            raise TypeError("observation_count must be an int")
        if self.observation_count < 0:
            raise ValueError("observation_count must be non-negative")
        statistics = (self.first, self.minimum, self.maximum, self.last)
        if self.observation_count == 0:
            if any(statistic is not None for statistic in statistics):
                raise ValueError("empty scalar statistics must not contain values")
            return
        if any(statistic is None for statistic in statistics):
            raise ValueError("non-empty scalar statistics require first/minimum/maximum/last")
        for statistic in statistics:
            if not isinstance(statistic, DatedValue):
                raise TypeError("scalar statistics must contain DatedValue instances")
            if not self.bucket.contains(statistic.observed_date):
                raise ValueError("statistic observed_date must fall inside the bucket")
        if self.first.observed_date > self.last.observed_date:
            raise ValueError("first observed_date must not follow last observed_date")
        if self.minimum.value > self.maximum.value:
            raise ValueError("minimum value must not exceed maximum value")
        if not self.minimum.value <= self.first.value <= self.maximum.value:
            raise ValueError("first value must fall inside minimum/maximum")
        if not self.minimum.value <= self.last.value <= self.maximum.value:
            raise ValueError("last value must fall inside minimum/maximum")


@dataclass(frozen=True, slots=True)
class BandBucketStatistics:
    """Independent dated statistics for lower/middle/upper band components."""

    bucket: Bucket
    observation_count: int
    lower: ScalarBucketStatistics
    middle: ScalarBucketStatistics
    upper: ScalarBucketStatistics

    def __post_init__(self) -> None:
        if not isinstance(self.bucket, Bucket):
            raise TypeError("bucket must be a Bucket")
        if not isinstance(self.observation_count, int) or isinstance(self.observation_count, bool):
            raise TypeError("observation_count must be an int")
        if self.observation_count < 0:
            raise ValueError("observation_count must be non-negative")
        for component in (self.lower, self.middle, self.upper):
            if not isinstance(component, ScalarBucketStatistics):
                raise TypeError("band components must be ScalarBucketStatistics")
            if component.bucket != self.bucket:
                raise ValueError("band component statistics must reference the same bucket")
            if component.observation_count > self.observation_count:
                raise ValueError("band component count cannot exceed band observation_count")
        component_counts = (
            self.lower.observation_count,
            self.middle.observation_count,
            self.upper.observation_count,
        )
        if self.observation_count > 0 and not any(component_counts):
            raise ValueError("non-empty band statistics require at least one observed component")


@dataclass(frozen=True, slots=True)
class BandEnvelopeRepresentative:
    """Synthetic chart envelope selected from independent band statistics."""

    bucket: Bucket
    lower: DatedValue | None
    middle: DatedValue | None
    upper: DatedValue | None

    def __post_init__(self) -> None:
        if not isinstance(self.bucket, Bucket):
            raise TypeError("bucket must be a Bucket")
        present = [component for component in (self.lower, self.middle, self.upper) if component is not None]
        if any(not isinstance(component, DatedValue) for component in present):
            raise TypeError("band envelope components must be DatedValue instances")
        if any(not self.bucket.contains(component.observed_date) for component in present):
            raise ValueError("band envelope observed dates must fall inside the bucket")
        if any(current.value > following.value for current, following in zip(present, present[1:], strict=False)):
            raise ValueError("band envelope must satisfy lower <= middle <= upper")


def _dated_value(point: ObservedPoint) -> DatedValue:
    return DatedValue(value=point.value, observed_date=point.date)


def _scalar_statistics_for_bucket(
    bucket: Bucket,
    points: Sequence[ObservedPoint],
) -> ScalarBucketStatistics:
    if not points:
        return ScalarBucketStatistics(
            bucket=bucket,
            observation_count=0,
            first=None,
            minimum=None,
            maximum=None,
            last=None,
        )
    minimum_value = min(point.value for point in points)
    maximum_value = max(point.value for point in points)
    minimum_point = next(point for point in points if point.value == minimum_value)
    maximum_point = next(point for point in points if point.value == maximum_value)
    return ScalarBucketStatistics(
        bucket=bucket,
        observation_count=len(points),
        first=_dated_value(points[0]),
        minimum=_dated_value(minimum_point),
        maximum=_dated_value(maximum_point),
        last=_dated_value(points[-1]),
    )


def aggregate_scalar_statistics(
    points: Iterable[ObservedPoint],
    plan: BucketPlan,
) -> tuple[ScalarBucketStatistics, ...]:
    """Aggregate scalar observations with real dates and chronological tie-breaking."""

    materialized = tuple(points)
    if any(not isinstance(point, ObservedPoint) for point in materialized):
        raise TypeError("points must contain ObservedPoint values")
    grouped = _assign_by_date(materialized, plan)
    return tuple(_scalar_statistics_for_bucket(bucket, bucket_points) for bucket, bucket_points in zip(plan.buckets, grouped, strict=True))


def aggregate_ohlc(points: Iterable[ObservedPoint], plan: BucketPlan) -> tuple[OhlcBucketAggregate, ...]:
    """Aggregate a scalar numeric series (price/FX/...) into OHLC-like buckets.

    Empty buckets are explicit: they carry ``observation_count == 0`` and
    ``None`` for every numeric field (no synthetic carry-forward here — that
    is the responsibility of a warm-up/carry-forward helper if needed).
    """

    statistics = aggregate_scalar_statistics(points, plan)
    return tuple(
        OhlcBucketAggregate(
            bucket=item.bucket,
            first=item.first.value if item.first is not None else None,
            minimum=item.minimum.value if item.minimum is not None else None,
            maximum=item.maximum.value if item.maximum is not None else None,
            last=item.last.value if item.last is not None else None,
            observation_count=item.observation_count,
        )
        for item in statistics
    )


def aggregate_band_statistics(
    points: Iterable[BandObservedPoint],
    plan: BucketPlan,
) -> tuple[BandBucketStatistics, ...]:
    """Aggregate band components independently so their observed dates remain truthful."""

    materialized = tuple(points)
    if any(not isinstance(point, BandObservedPoint) for point in materialized):
        raise TypeError("points must contain BandObservedPoint values")
    grouped = _assign_by_date(materialized, plan)
    results: list[BandBucketStatistics] = []
    for bucket, bucket_points in zip(plan.buckets, grouped, strict=True):
        components = {component: tuple(ObservedPoint(date=point.date, value=value) for point in bucket_points if (value := getattr(point, component)) is not None) for component in ("lower", "middle", "upper")}
        results.append(
            BandBucketStatistics(
                bucket=bucket,
                observation_count=len(bucket_points),
                lower=_scalar_statistics_for_bucket(bucket, components["lower"]),
                middle=_scalar_statistics_for_bucket(bucket, components["middle"]),
                upper=_scalar_statistics_for_bucket(bucket, components["upper"]),
            )
        )
    return tuple(results)


def select_scalar_representative(
    statistics: ScalarBucketStatistics,
    profile: SignalAggregationProfile,
) -> DatedValue | None:
    """Select the chart representative declared by a scalar aggregation profile."""

    if not isinstance(statistics, ScalarBucketStatistics):
        raise TypeError("statistics must be ScalarBucketStatistics")
    if not isinstance(profile, SignalAggregationProfile):
        raise TypeError("profile must be a SignalAggregationProfile")
    selectors = {
        SignalAggregationProfile.FIRST_WITH_RANGE: statistics.first,
        SignalAggregationProfile.MIN_WITH_RANGE: statistics.minimum,
        SignalAggregationProfile.MAX_WITH_RANGE: statistics.maximum,
        SignalAggregationProfile.LAST_WITH_RANGE: statistics.last,
    }
    if profile not in selectors:
        raise ValueError(f"{profile.value} is not a scalar aggregation profile")
    return selectors[profile]


def select_band_envelope(
    statistics: BandBucketStatistics,
    profile: SignalAggregationProfile = SignalAggregationProfile.BAND_ENVELOPE,
) -> BandEnvelopeRepresentative:
    """Select lower=min, middle=last, upper=max for the chart band envelope."""

    if not isinstance(statistics, BandBucketStatistics):
        raise TypeError("statistics must be BandBucketStatistics")
    if profile != SignalAggregationProfile.BAND_ENVELOPE:
        raise ValueError("band envelope selection requires band_envelope profile")
    return BandEnvelopeRepresentative(
        bucket=statistics.bucket,
        lower=statistics.lower.minimum,
        middle=statistics.middle.last,
        upper=statistics.upper.maximum,
    )


@dataclass(frozen=True, slots=True)
class MonetaryFlowBucketAggregate:
    """Monetary-flow aggregate (deposits/withdrawals/dividends/fees/...)."""

    bucket: Bucket
    total: Decimal
    event_count: int


def aggregate_monetary_flow(events: Iterable[MonetaryFlowEvent], plan: BucketPlan) -> tuple[MonetaryFlowBucketAggregate, ...]:
    """Sum monetary flow amounts per bucket.

    Empty buckets are explicit: ``event_count == 0`` and ``total == Decimal(0)``
    — flows use a zero total (not ``None``) since "no flow" is a meaningful
    additive identity for this aggregate.
    """

    grouped = _assign_by_date(tuple(events), plan)
    results: list[MonetaryFlowBucketAggregate] = []
    for bucket, bucket_events in zip(plan.buckets, grouped, strict=True):
        total = sum((event.amount for event in bucket_events), Decimal(0))
        results.append(MonetaryFlowBucketAggregate(bucket=bucket, total=total, event_count=len(bucket_events)))
    return tuple(results)


@dataclass(frozen=True, slots=True)
class ContinuousMultiOutputBucketAggregate:
    """OHLC-like aggregate generalised to several named numeric outputs at once."""

    bucket: Bucket
    first: Mapping[str, Decimal] | None
    minimum: Mapping[str, Decimal] | None
    maximum: Mapping[str, Decimal] | None
    last: Mapping[str, Decimal] | None
    observation_count: int


def aggregate_continuous_multi_output(points: Iterable[ContinuousMultiOutputPoint], plan: BucketPlan) -> tuple[ContinuousMultiOutputBucketAggregate, ...]:
    """Aggregate a multi-output continuous component (e.g. a multi-line signal).

    Every point within a bucket must expose the same set of output keys; empty
    buckets are explicit (``observation_count == 0``, all mapping fields
    ``None``).
    """

    grouped = _assign_by_date(tuple(points), plan)
    results: list[ContinuousMultiOutputBucketAggregate] = []
    for bucket, bucket_points in zip(plan.buckets, grouped, strict=True):
        if not bucket_points:
            results.append(ContinuousMultiOutputBucketAggregate(bucket=bucket, first=None, minimum=None, maximum=None, last=None, observation_count=0))
            continue

        output_keys = frozenset(bucket_points[0].values.keys())
        for point in bucket_points:
            if frozenset(point.values.keys()) != output_keys:
                raise ValueError("all points within a bucket must share the same output keys")

        minimum = {key: min(point.values[key] for point in bucket_points) for key in output_keys}
        maximum = {key: max(point.values[key] for point in bucket_points) for key in output_keys}
        results.append(
            ContinuousMultiOutputBucketAggregate(
                bucket=bucket,
                first=MappingProxyType(dict(bucket_points[0].values)),
                minimum=MappingProxyType(minimum),
                maximum=MappingProxyType(maximum),
                last=MappingProxyType(dict(bucket_points[-1].values)),
                observation_count=len(bucket_points),
            )
        )
    return tuple(results)


@dataclass(frozen=True, slots=True)
class DiscreteEventBucketAssignment:
    """Every (deduplicated) discrete event assigned to its bucket, verbatim."""

    bucket: Bucket
    events: tuple[DiscreteEvent, ...]
    event_count: int


def assign_discrete_events(events: Iterable[DiscreteEvent], plan: BucketPlan) -> tuple[DiscreteEventBucketAssignment, ...]:
    """Deduplicate by caller-supplied ``dedup_key`` (first-seen wins) then bucket.

    Every surviving event is preserved exactly as given — no averaging,
    truncation, or synthesis. Empty buckets are explicit (``event_count == 0``,
    ``events == ()``).
    """

    deduplicated: dict[Hashable, DiscreteEvent] = {}
    for event in events:
        if not isinstance(event, DiscreteEvent):
            raise TypeError("events must contain DiscreteEvent values")
        deduplicated.setdefault(event.dedup_key, event)

    grouped = _assign_by_date(tuple(deduplicated.values()), plan)
    return tuple(DiscreteEventBucketAssignment(bucket=bucket, events=bucket_events, event_count=len(bucket_events)) for bucket, bucket_events in zip(plan.buckets, grouped, strict=True))


SignalBucketAggregate = ScalarBucketStatistics | BandBucketStatistics | DiscreteEventBucketAssignment


def aggregate_signal_buckets(
    profile: SignalAggregationProfile,
    items: Iterable[ObservedPoint | BandObservedPoint | DiscreteEvent],
    plan: BucketPlan,
) -> tuple[SignalBucketAggregate, ...]:
    """Dispatch one plugin-declared enum profile without custom aggregation hooks."""

    if not isinstance(profile, SignalAggregationProfile):
        raise TypeError("profile must be a SignalAggregationProfile")
    materialized = tuple(items)
    if profile in _SCALAR_AGGREGATION_PROFILES:
        if any(not isinstance(item, ObservedPoint) for item in materialized):
            raise TypeError("scalar profiles require ObservedPoint values")
        return aggregate_scalar_statistics(materialized, plan)
    if profile == SignalAggregationProfile.BAND_ENVELOPE:
        if any(not isinstance(item, BandObservedPoint) for item in materialized):
            raise TypeError("band_envelope requires BandObservedPoint values")
        return aggregate_band_statistics(materialized, plan)
    if profile == SignalAggregationProfile.EVENTS_VERBATIM:
        if any(not isinstance(item, DiscreteEvent) for item in materialized):
            raise TypeError("events_verbatim requires DiscreteEvent values")
        return assign_discrete_events(materialized, plan)
    raise ValueError(f"unsupported signal aggregation profile: {profile.value}")
