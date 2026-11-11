"""Signal vocabulary: the enums a signal request, definition and result speak in (domains, categories, units, statuses, reasons, codes)."""

from __future__ import annotations

from enum import StrEnum


class SignalDomain(StrEnum):
    ASSET = "asset"
    FX = "fx"


class SignalCategory(StrEnum):
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    RISK = "risk"


class SignalPriceField(StrEnum):
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"


class SignalVolumeKind(StrEnum):
    """Semantic meaning of a source's `volume` field, when meaningful.

    Kept intentionally minimal: sources declare only whether their volume
    field is unambiguous exchange-traded share volume. Extend with additional
    kinds only when a new source class needs one (e.g. on-chain transfer
    counts); avoid speculative values with no current producer.
    """

    UNKNOWN = "unknown"
    TRADED_SHARES = "traded_shares"


class SignalDataPolicy(StrEnum):
    STRICT_CONTIGUOUS = "strict_contiguous"
    ALLOW_PARTIAL_CONTIGUOUS = "allow_partial_contiguous"


class SignalCadence(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    IRREGULAR = "irregular"


class SignalSeriesKind(StrEnum):
    LINE = "line"
    AREA = "area"
    BAR = "bar"
    BAND = "band"


class SignalAggregationProfile(StrEnum):
    """Plugin-owned temporal reduction semantics shared by chart and AI Export."""

    LAST_WITH_RANGE = "last_with_range"
    FIRST_WITH_RANGE = "first_with_range"
    MIN_WITH_RANGE = "min_with_range"
    MAX_WITH_RANGE = "max_with_range"
    BAND_ENVELOPE = "band_envelope"
    EVENTS_VERBATIM = "events_verbatim"


class SignalTemporalClass(StrEnum):
    VERY_FAST = "very_fast"
    FAST = "fast"
    MEDIUM_FAST = "medium_fast"
    MEDIUM = "medium"
    SLOW = "slow"
    VERY_SLOW = "very_slow"


class SignalBandComponent(StrEnum):
    LOWER = "lower"
    MIDDLE = "middle"
    UPPER = "upper"


class SignalLinePattern(StrEnum):
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"


class SignalColorRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    ACCENT = "accent"


class SignalAxisRole(StrEnum):
    PRICE = "price"
    INDEPENDENT = "independent"
    VOLUME = "volume"


class SignalUnit(StrEnum):
    PRICE = "price"
    PERCENTAGE = "percentage"
    INDEX = "index"
    VOLUME = "volume"
    NONE = "none"


class SignalViewTransform(StrEnum):
    NONE = "none"
    BASE_PERCENTAGE = "base_percentage"


class SignalStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class SignalAvailabilityReason(StrEnum):
    INCOMPATIBLE_DOMAIN = "incompatible_domain"
    MISSING_INPUT_FIELDS = "missing_input_fields"
    MISSING_EVENT_TYPES = "missing_event_types"
    MISSING_PREPARED_SERIES = "missing_prepared_series"
    MISSING_COMPARISON_SERIES = "missing_comparison_series"
    INSUFFICIENT_INPUT_COVERAGE = "insufficient_input_coverage"
    INSUFFICIENT_EVENT_COVERAGE = "insufficient_event_coverage"
    INSUFFICIENT_HISTORY = "insufficient_history"
    UNDEFINED_METRIC = "undefined_metric"
    INCOMPLETE_WARMUP = "incomplete_warmup"
    PARTIAL_INPUT_COVERAGE = "partial_input_coverage"
    PARTIAL_EVENT_COVERAGE = "partial_event_coverage"
    PARTIAL_UNDEFINED_METRIC = "partial_undefined_metric"
    DATA_GAP = "data_gap"
    MISSING_SOURCE_CAPABILITY = "missing_source_capability"


class SignalWarningCode(StrEnum):
    INCOMPLETE_WARMUP = "incomplete_warmup"
    PARTIAL_INPUT_COVERAGE = "partial_input_coverage"
    PARTIAL_EVENT_COVERAGE = "partial_event_coverage"
    DATA_QUALITY = "data_quality"
    UNDEFINED_METRIC_WINDOW = "undefined_metric_window"
    DATA_GAP = "data_gap"
    OUTPUT_TRUNCATED = "output_truncated"
    ANNOTATION_UNAVAILABLE = "annotation_unavailable"


class SignalErrorCode(StrEnum):
    UNKNOWN_SIGNAL = "unknown_signal"
    INVALID_PARAMS = "invalid_params"
    PLANNING_ERROR = "planning_error"
    COMPUTE_ERROR = "compute_error"
    INVALID_OUTPUT = "invalid_output"
    CONTRACT_VIOLATION = "contract_violation"


class SignalAnnotationDirection(StrEnum):
    UP = "up"
    DOWN = "down"


class SignalThresholdDirection(StrEnum):
    UP = "up"
    DOWN = "down"
    BOTH = "both"


class SignalAnnotationSampling(StrEnum):
    RECENT = "recent"
    UNIFORM = "uniform"


class SignalCalendarReturnPointStatus(StrEnum):
    """Why one calendar-return point has a value or is unavailable."""

    AVAILABLE = "available"
    MISSING_REFERENCE = "missing_reference"
    INVALID_CURRENT_PRICE = "invalid_current_price"
    INVALID_REFERENCE_PRICE = "invalid_reference_price"
