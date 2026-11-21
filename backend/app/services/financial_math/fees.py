"""The broker fee formula: ``fixed + clamp(rate * notional, floor, cap)``, and nothing for a zero notional.

One home for the rule a broker's fee schedule states (A0, project 67: the planner serves two Tools, the PAC and the
Rebalancer, so the formula that the PAC engine alone used to own lives with the common financial math). Generic on the
number type the way ``fx_rates.oriented_rate`` is: the same lines serve ``Decimal``, ``Fraction`` and the PAC's exact
rational, and the result is in the type the caller passed. The layer cannot import the PAC engine, so a refused input
is a plain ``ValueError``.
"""

from __future__ import annotations


def calculate_fee[N](*, notional: N, fixed: N, rate: N, floor: N, cap: N | None) -> N:
    """The fee a broker charges for an order of ``notional`` (cash in the quote currency), before any posting rounding.

    A zero ``notional`` is no order and pays nothing, whatever the schedule says. Otherwise the variable part is
    ``rate * notional`` raised to ``floor`` and lowered to ``cap`` (``cap`` may be ``None``: no cap), and ``fixed`` is
    added on top. Every input must be non-negative and ``floor`` may not exceed ``cap``: a refused input raises
    ``ValueError`` naming it, never a number.
    """
    zero = type(notional)(0)
    for name, value in (("notional", notional), ("fixed", fixed), ("rate", rate), ("floor", floor)):
        if value < zero:
            raise ValueError(f"{name} must be nonnegative")
    if cap is not None:
        if cap < zero:
            raise ValueError("cap must be nonnegative")
        if floor > cap:
            raise ValueError("fee floor must not exceed fee cap")
    if notional == zero:
        return zero

    variable = rate * notional
    if variable < floor:
        variable = floor
    if cap is not None and variable > cap:
        variable = cap
    return fixed + variable
