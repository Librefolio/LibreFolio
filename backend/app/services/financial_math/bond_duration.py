"""A bond's price sensitivity to its yield: the first-order price change from its modified duration.

For a parallel move Δy of the yield, the price moves by about −D_mod × Δy, D_mod the modified duration in years (the
figure Borsa Italiana publishes as «duration modificata», which the asset profile keeps as ``modified_duration``). A
first-order estimate: it ignores convexity (the curve bends, so a large move is overstated on the way up and
understated on the way down) and the coupons received meanwhile. The rising-rates scenario of an asset's «What if…?»
reads it (RN-25), for a rise and for a fall alike.
"""

from __future__ import annotations

import math


def duration_price_change(modified_duration: float, yield_change: float) -> float:
    """The relative price change −D_mod × Δy, both as plain numbers: 1.8 years and 0.01 (one point) give −0.018.

    A negative or non-finite duration, or a non-finite yield change, is refused: the figure would be a number nobody
    measured.
    """
    if not math.isfinite(modified_duration) or modified_duration < 0:
        raise ValueError("modified duration must be a finite, non-negative number of years")
    if not math.isfinite(yield_change):
        raise ValueError("yield change must be a finite number")
    change = -modified_duration * yield_change
    # -0.0 reads as a loss that is not there.
    return 0.0 if change == 0 else change
