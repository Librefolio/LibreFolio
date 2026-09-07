"""Observed-only uniform calendar buckets for compact mini-histories."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from backend.app.services.ai_export.temporal.plan import Bucket
from backend.app.services.ai_export.temporal.points import ObservedPoint, sort_by_date


@dataclass(frozen=True, slots=True)
class UniformObservedBucket:
    """One non-empty uniform calendar bucket with truthful observed statistics."""

    bucket: Bucket
    observation_count: int
    first: ObservedPoint
    minimum: ObservedPoint
    maximum: ObservedPoint
    last: ObservedPoint
    representative: ObservedPoint

    def __post_init__(self) -> None:
        if not isinstance(self.bucket, Bucket):
            raise TypeError("bucket must be a Bucket")
        if isinstance(self.observation_count, bool) or not isinstance(self.observation_count, int):
            raise TypeError("observation_count must be an int")
        if self.observation_count < 1:
            raise ValueError("observation_count must be positive")
        points = (self.first, self.minimum, self.maximum, self.last, self.representative)
        if any(not isinstance(point, ObservedPoint) for point in points):
            raise TypeError("bucket statistics must contain ObservedPoint values")
        if any(not self.bucket.contains(point.date) for point in points):
            raise ValueError("bucket statistic dates must fall inside the bucket")
        if self.first.date > self.last.date:
            raise ValueError("first observation must not follow last observation")
        if self.minimum.value > self.maximum.value:
            raise ValueError("minimum value must not exceed maximum value")


def uniform_observed_buckets(
    points: Iterable[ObservedPoint],
    target_bucket_count: int,
) -> tuple[UniformObservedBucket, ...]:
    """Bucket a scalar series uniformly over its actual observed calendar range.

    Empty buckets are omitted rather than filled or duplicated. The first
    non-empty bucket represents the first observation; later buckets represent
    their last observation, preserving both global endpoints when data exists.
    """

    if isinstance(target_bucket_count, bool) or not isinstance(target_bucket_count, int):
        raise TypeError("target_bucket_count must be an int")
    if target_bucket_count < 1:
        raise ValueError("target_bucket_count must be positive")

    materialized = tuple(points)
    if any(not isinstance(point, ObservedPoint) for point in materialized):
        raise TypeError("points must contain ObservedPoint values")
    observed = sort_by_date(materialized)
    if any(current.date == following.date for current, following in zip(observed, observed[1:], strict=False)):
        raise ValueError("point dates must be unique")
    if not observed:
        return ()

    buckets = uniform_calendar_buckets(observed[0].date, observed[-1].date, target_bucket_count)

    grouped: list[list[ObservedPoint]] = [[] for _ in buckets]
    bucket_index = 0
    for point in observed:
        while point.date > buckets[bucket_index].end_date:
            bucket_index += 1
        grouped[bucket_index].append(point)

    rows: list[UniformObservedBucket] = []
    for bucket, bucket_points in zip(buckets, grouped, strict=True):
        if not bucket_points:
            continue
        minimum = min(bucket_points, key=lambda point: point.value)
        maximum = max(bucket_points, key=lambda point: point.value)
        rows.append(
            UniformObservedBucket(
                bucket=bucket,
                observation_count=len(bucket_points),
                first=bucket_points[0],
                minimum=minimum,
                maximum=maximum,
                last=bucket_points[-1],
                representative=(bucket_points[0] if bucket.index == 0 else bucket_points[-1]),
            )
        )
    return tuple(rows)


def uniform_calendar_buckets(start: date, end: date, target_bucket_count: int) -> tuple[Bucket, ...]:
    """Split an inclusive calendar range into deterministic contiguous buckets."""

    if type(start) is not date or type(end) is not date:
        raise TypeError("start and end must be datetime.date values")
    if start > end:
        raise ValueError("start must not be after end")
    if isinstance(target_bucket_count, bool) or not isinstance(target_bucket_count, int):
        raise TypeError("target_bucket_count must be an int")
    if target_bucket_count < 1:
        raise ValueError("target_bucket_count must be positive")
    span_days = (end - start).days + 1
    planned_count = min(target_bucket_count, span_days)
    return tuple(
        Bucket(
            index=index,
            start_date=start + timedelta(days=(index * span_days) // planned_count),
            end_date=start + timedelta(days=((index + 1) * span_days) // planned_count - 1),
        )
        for index in range(planned_count)
    )


__all__ = ["UniformObservedBucket", "uniform_calendar_buckets", "uniform_observed_buckets"]
