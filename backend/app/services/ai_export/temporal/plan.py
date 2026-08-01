"""Deterministic, immutable bucket plan built from a :class:`BucketingPolicy`.

The plan is constructed once per (start, end, policy) triple and can be reused
across every component/target that needs to bucket observations for the same
requested period — the bucket boundaries themselves never depend on the data
being aggregated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta

from backend.app.services.ai_export.temporal.policy import BucketingPolicy


@dataclass(frozen=True, slots=True)
class Bucket:
    """One inclusive calendar-day range, oldest-to-newest ordered within a plan."""

    index: int
    start_date: Date
    end_date: Date

    def __post_init__(self) -> None:
        if type(self.start_date) is not Date or type(self.end_date) is not Date:
            raise TypeError("start_date and end_date must be datetime.date instances")
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        if isinstance(self.index, bool) or not isinstance(self.index, int) or self.index < 0:
            raise ValueError("index must be a non-negative integer")

    @property
    def day_count(self) -> int:
        """Inclusive number of calendar days covered by this bucket."""

        return (self.end_date - self.start_date).days + 1

    def contains(self, day: Date) -> bool:
        if type(day) is not Date:
            raise TypeError("day must be a datetime.date instance")
        return self.start_date <= day <= self.end_date


@dataclass(frozen=True, slots=True)
class BucketPlan:
    """Immutable, reusable oldest-to-newest sequence of non-overlapping buckets."""

    start: Date
    end: Date
    policy: BucketingPolicy
    buckets: tuple[Bucket, ...]

    def __post_init__(self) -> None:
        """Validate invariants for *any* construction path, not just :meth:`build`.

        ``BucketPlan`` is a public dataclass, so direct construction must be
        rejected unless it represents a valid plan: correctly typed/ordered
        dates, a real policy, a non-empty tuple of ``Bucket`` with sequential
        0-based indexes, contiguous non-overlapping buckets, and full inclusive
        coverage of ``[start, end]`` with the first/last bucket anchored
        exactly at ``start``/``end``.
        """

        if type(self.start) is not Date or type(self.end) is not Date:
            raise TypeError("start and end must be datetime.date instances")
        if self.start > self.end:
            raise ValueError("start must not be after end")
        if not isinstance(self.policy, BucketingPolicy):
            raise TypeError("policy must be a BucketingPolicy")
        if not isinstance(self.buckets, tuple) or not all(isinstance(bucket, Bucket) for bucket in self.buckets):
            raise TypeError("buckets must be a tuple of Bucket instances")
        if not self.buckets:
            raise ValueError("buckets must not be empty")

        if tuple(bucket.index for bucket in self.buckets) != tuple(range(len(self.buckets))):
            raise ValueError("bucket indexes must be sequential starting at 0")
        if self.buckets[0].start_date != self.start:
            raise ValueError("first (oldest) bucket must start exactly at the plan's start")
        if self.buckets[-1].end_date != self.end:
            raise ValueError("last (newest) bucket must end exactly at the plan's end")

        for previous, current in zip(self.buckets, self.buckets[1:], strict=False):
            if current.start_date != previous.end_date + timedelta(days=1):
                raise ValueError("buckets must be contiguous with no gap or overlap")

        covered_days = sum(bucket.day_count for bucket in self.buckets)
        if covered_days != (self.end - self.start).days + 1:
            raise ValueError("buckets must fully cover the inclusive requested period exactly once")

    @property
    def requested_day_count(self) -> int:
        """Inclusive requested period length T = (end - start).days + 1."""

        return (self.end - self.start).days + 1

    @classmethod
    def build(cls, start: Date, end: Date, policy: BucketingPolicy) -> BucketPlan:
        """Iteratively build boundaries from offset x0=0 up to T, oldest-to-newest.

        Buckets are grown outward from ``end`` (``snapshot_as_of``) using
        half-open offset ranges ``[x_n, x_n+1)`` measured in whole days back
        from ``end``; each offset range is mapped to a non-overlapping
        inclusive calendar-date range. The final (oldest) bucket is truncated
        so it always starts exactly at ``start`` — no null intervals and the
        loop always terminates because ``bucket_width`` is always >= 1.
        """

        if type(start) is not Date or type(end) is not Date:
            raise TypeError("start and end must be datetime.date instances")
        if start > end:
            raise ValueError("start must not be after end")
        if not isinstance(policy, BucketingPolicy):
            raise TypeError("policy must be a BucketingPolicy")

        total_days = (end - start).days + 1

        offsets = [0]
        offset = 0
        while offset < total_days:
            offset = min(offset + policy.bucket_width(offset), total_days)
            offsets.append(offset)

        newest_first: list[Bucket] = []
        for offset_start, offset_end in zip(offsets, offsets[1:], strict=False):
            bucket_end_date = end - timedelta(days=offset_start)
            bucket_start_date = end - timedelta(days=offset_end - 1)
            newest_first.append(Bucket(index=0, start_date=bucket_start_date, end_date=bucket_end_date))

        oldest_first = tuple(Bucket(index=new_index, start_date=bucket.start_date, end_date=bucket.end_date) for new_index, bucket in enumerate(reversed(newest_first)))
        return cls(start=start, end=end, policy=policy, buckets=oldest_first)
