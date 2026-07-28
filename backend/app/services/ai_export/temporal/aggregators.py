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
from decimal import Decimal
from types import MappingProxyType

from backend.app.services.ai_export.temporal.plan import Bucket, BucketPlan
from backend.app.services.ai_export.temporal.points import (
    ContinuousMultiOutputPoint,
    Dated,
    DiscreteEvent,
    MonetaryFlowEvent,
    ObservedPoint,
    sort_by_date,
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


def aggregate_ohlc(points: Iterable[ObservedPoint], plan: BucketPlan) -> tuple[OhlcBucketAggregate, ...]:
    """Aggregate a scalar numeric series (price/FX/...) into OHLC-like buckets.

    Empty buckets are explicit: they carry ``observation_count == 0`` and
    ``None`` for every numeric field (no synthetic carry-forward here — that
    is the responsibility of a warm-up/carry-forward helper if needed).
    """

    grouped = _assign_by_date(tuple(points), plan)
    results: list[OhlcBucketAggregate] = []
    for bucket, bucket_points in zip(plan.buckets, grouped, strict=True):
        if not bucket_points:
            results.append(OhlcBucketAggregate(bucket=bucket, first=None, minimum=None, maximum=None, last=None, observation_count=0))
            continue
        values = tuple(point.value for point in bucket_points)
        results.append(
            OhlcBucketAggregate(
                bucket=bucket,
                first=bucket_points[0].value,
                minimum=min(values),
                maximum=max(values),
                last=bucket_points[-1].value,
                observation_count=len(bucket_points),
            )
        )
    return tuple(results)


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
