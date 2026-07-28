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
    ContinuousMultiOutputBucketAggregate,
    DiscreteEventBucketAssignment,
    MonetaryFlowBucketAggregate,
    OhlcBucketAggregate,
    aggregate_continuous_multi_output,
    aggregate_monetary_flow,
    aggregate_ohlc,
    assign_discrete_events,
)
from backend.app.services.ai_export.temporal.plan import Bucket, BucketPlan
from backend.app.services.ai_export.temporal.points import (
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
from backend.app.services.ai_export.temporal.warmup import (
    assert_within_requested_period,
    slice_to_requested_period,
    warmup_window_start,
)

__all__ = [
    "Bucket",
    "BucketPlan",
    "BucketDetailLevel",
    "BucketingPolicy",
    "ObservedPoint",
    "ContinuousMultiOutputPoint",
    "MonetaryFlowEvent",
    "DiscreteEvent",
    "sort_by_date",
    "OhlcBucketAggregate",
    "MonetaryFlowBucketAggregate",
    "ContinuousMultiOutputBucketAggregate",
    "DiscreteEventBucketAssignment",
    "aggregate_ohlc",
    "aggregate_monetary_flow",
    "aggregate_continuous_multi_output",
    "assign_discrete_events",
    "warmup_window_start",
    "slice_to_requested_period",
    "assert_within_requested_period",
]
