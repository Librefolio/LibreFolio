"""Deterministic rational bucket-width policy for the AI Export temporal engine.

D(x) grows the historical bucket width as the offset ``x`` (whole days measured
back from ``snapshot_as_of``) increases, saturating at ``max_bucket_days`` (K):

    f(x; P, M, K) = 1 + (K - 1) * max(x - 7, 0) ** P / (M ** P + max(x - 7, 0) ** P)
    D(x) = max(1, round_half_up(f(x)))

The whole computation is performed in ``Decimal`` so the rounding step is exact
and reproducible regardless of platform float behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

#: Exponent P in the rational decay function.
EXPONENT = 2

#: Half-scale offset M: the offset (beyond the ramp start) at which the decay
#: function reaches the midpoint between 1 and K.
HALF_LIFE_OFFSET = 30

#: Offset (in days) below which D(x) is always exactly 1 (daily granularity for
#: the most recent week of the requested period).
RAMP_START_OFFSET = 7


class BucketDetailLevel(StrEnum):
    """AI Export detail levels, each mapped to a maximum bucket width K."""

    COMPACT = "compact"
    STANDARD = "standard"
    FULL = "full"


#: K (max_bucket_days) per detail level, per the normative Phase 0 policy table.
_MAX_BUCKET_DAYS_BY_DETAIL_LEVEL: dict[BucketDetailLevel, int] = {
    BucketDetailLevel.COMPACT: 30,
    BucketDetailLevel.STANDARD: 14,
    BucketDetailLevel.FULL: 7,
}


@dataclass(frozen=True, slots=True)
class BucketingPolicy:
    """Immutable rational bucket-width policy.

    ``max_bucket_days`` is K in the formula. ``exponent``, ``half_life_offset``
    and ``ramp_start_offset`` default to the normative P=2, M=30, ramp=7 and are
    only exposed for testing convergence/edge behaviour; production code should
    use :meth:`for_detail_level`.
    """

    max_bucket_days: int
    exponent: int = EXPONENT
    half_life_offset: int = HALF_LIFE_OFFSET
    ramp_start_offset: int = RAMP_START_OFFSET

    def __post_init__(self) -> None:
        _require_positive_int(self.max_bucket_days, "max_bucket_days")
        _require_positive_int(self.exponent, "exponent")
        _require_positive_int(self.half_life_offset, "half_life_offset")
        _require_non_negative_int(self.ramp_start_offset, "ramp_start_offset")

    @classmethod
    def for_detail_level(cls, detail_level: BucketDetailLevel) -> BucketingPolicy:
        """Build the normative policy (P=2, M=30, ramp=7) for a given detail level."""

        if not isinstance(detail_level, BucketDetailLevel):
            raise TypeError("detail_level must be a BucketDetailLevel")
        return cls(max_bucket_days=_MAX_BUCKET_DAYS_BY_DETAIL_LEVEL[detail_level])

    def raw_width(self, offset_days: int) -> Decimal:
        """Return f(x) as an exact ``Decimal`` (before rounding/flooring to 1)."""

        _require_non_negative_int(offset_days, "offset_days")
        base = max(offset_days - self.ramp_start_offset, 0)
        if base == 0:
            return Decimal(1)

        base_power = Decimal(base) ** self.exponent
        half_life_power = Decimal(self.half_life_offset) ** self.exponent
        k_minus_one = Decimal(self.max_bucket_days - 1)
        return Decimal(1) + (k_minus_one * base_power) / (half_life_power + base_power)

    def bucket_width(self, offset_days: int) -> int:
        """Return D(x) = max(1, round_half_up(f(x))), always in [1, max_bucket_days]."""

        rounded = self.raw_width(offset_days).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        return max(1, int(rounded))


def _require_positive_int(value: object, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    if value < 1:
        raise ValueError(f"{label} must be >= 1")


def _require_non_negative_int(value: object, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    if value < 0:
        raise ValueError(f"{label} must be >= 0")
