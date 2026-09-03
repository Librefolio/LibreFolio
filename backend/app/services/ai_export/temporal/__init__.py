"""Reusable deterministic temporal engine for the AI Export package.

Builds an immutable, oldest-to-newest :class:`BucketPlan` from a rational
:class:`BucketingPolicy` (see ``policy.py`` for the formula), then provides
generic, Portfolio-agnostic aggregators to bucket observed numeric points,
monetary flow events, multi-output continuous components, and discrete
events. ``warmup.py`` guarantees pre-``start`` calculation data never leaks
into exported output.
"""

from __future__ import annotations

from backend.app.services.ai_export.temporal.aggregators import (
    BandBucketStatistics,
    BandEnvelopeRepresentative,
    ContinuousMultiOutputBucketAggregate,
    DatedValue,
    DiscreteEventBucketAssignment,
    MonetaryFlowBucketAggregate,
    OhlcBucketAggregate,
    ScalarBucketStatistics,
    aggregate_band_statistics,
    aggregate_continuous_multi_output,
    aggregate_monetary_flow,
    aggregate_ohlc,
    aggregate_scalar_statistics,
    aggregate_signal_buckets,
    assign_discrete_events,
    select_band_envelope,
    select_scalar_representative,
)
from backend.app.services.ai_export.temporal.plan import Bucket, BucketPlan
from backend.app.services.ai_export.temporal.points import (
    BandObservedPoint,
    ContinuousMultiOutputPoint,
    DiscreteEvent,
    MonetaryFlowEvent,
    ObservedPoint,
    sort_by_date,
)
from backend.app.services.ai_export.temporal.policy import (
    BucketDetailLevel,
    BucketingPolicy,
)
from backend.app.services.ai_export.temporal.uniform import (
    UniformObservedBucket,
    uniform_observed_buckets,
)
from backend.app.services.ai_export.temporal.warmup import (
    assert_within_requested_period,
    slice_to_requested_period,
    warmup_window_start,
)

__all__ = [
    "BandBucketStatistics",
    "BandEnvelopeRepresentative",
    "BandObservedPoint",
    "Bucket",
    "BucketDetailLevel",
    "BucketPlan",
    "BucketingPolicy",
    "ContinuousMultiOutputBucketAggregate",
    "ContinuousMultiOutputPoint",
    "DatedValue",
    "DiscreteEvent",
    "DiscreteEventBucketAssignment",
    "MonetaryFlowBucketAggregate",
    "MonetaryFlowEvent",
    "ObservedPoint",
    "OhlcBucketAggregate",
    "ScalarBucketStatistics",
    "UniformObservedBucket",
    "aggregate_band_statistics",
    "aggregate_continuous_multi_output",
    "aggregate_monetary_flow",
    "aggregate_ohlc",
    "aggregate_scalar_statistics",
    "aggregate_signal_buckets",
    "assert_within_requested_period",
    "assign_discrete_events",
    "select_band_envelope",
    "select_scalar_representative",
    "slice_to_requested_period",
    "sort_by_date",
    "uniform_observed_buckets",
    "warmup_window_start",
]
