"""Weights and concentration: a part's share of a total, the slices of an allocation, and how concentrated a set of
weights is.

Every share LibreFolio shows — a holding's weight on the net worth or on the invested value, an allocation slice, the
weights the risk analytics and the AI Export read — is a part divided by its total, and only these functions divide.
A share needs a positive total: on a total at or below zero (a net worth wiped out or negative) there is no
meaningful share, so the answer is None — never a percentage of an arbitrary divisor.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")
_ONE_POSITION_POINTS = Decimal("10000")


def share_of(part: Decimal, total: Decimal) -> Decimal | None:
    """``part / total``, unrounded; None when the total is zero or negative."""
    if total <= 0:
        return None
    return part / total


def percent_of(part: Decimal, total: Decimal) -> Decimal | None:
    """:func:`share_of` as a percentage (× 100), unrounded; None when the total is zero or negative."""
    share = share_of(part, total)
    return share * _HUNDRED if share is not None else None


def slice_percents[K](amounts: Mapping[K, Decimal]) -> dict[K, Decimal | None]:
    """The slices of an allocation as percentages of their sum, unrounded, in the mapping's order.

    An allocation keeps signed slices — cash below zero is a slice below zero, and the others then add up to more than
    100 (see ``AllocationItem.value``) — so this divides by the signed sum. A sum at or below zero gives no share
    (MF-C2): every slice is None, its amount stays the caller's — never a percentage of an arbitrary divisor, as
    :func:`share_of`. An empty allocation has no slices.
    """
    total = sum(amounts.values(), _ZERO)
    if total <= 0:
        return dict.fromkeys(amounts)
    return {name: amount / total * _HUNDRED for name, amount in amounts.items()}


def gross_weights(values: Mapping[int, Decimal]) -> dict[int, Decimal]:
    """Each value's share of the gross total ``Σ |value|`` (short positions weigh by their size); {} on a zero total."""
    total = sum((abs(value) for value in values.values()), _ZERO)
    if total <= 0:
        return {}
    return {key: abs(value) / total for key, value in values.items()}


def concentration(weights_percent: Iterable[Decimal]) -> tuple[Decimal | None, Decimal | None]:
    """The largest absolute weight and the Herfindahl–Hirschman index (Σ w², in points: 10 000 = one position), over
    every weight given — never a top-N subset. (None, None) without weights."""
    weights = list(weights_percent)
    if not weights:
        return None, None
    return max(abs(weight) for weight in weights), sum((weight * weight for weight in weights), _ZERO)


def effective_number_of_positions[K](weights: Mapping[K, Decimal]) -> Decimal | None:
    """N_eff, the equivalent count of equal positions: ``10 000 ÷`` the Herfindahl index of :func:`concentration`, in
    points, over the weights given **renormalized on their own sum** (RN-15, developer's Q8 a, 16/11/2026).

    The unit is positions: ``0.5, 0.3, 0.15, 0.05`` gives 2.74 — the set behaves like about two and three-quarter
    equal positions. The weights are re-taken over the part they measure, so what is not among them — cash, a position
    without a price — is not in the denominator, and N_eff never exceeds the number of weights given. Weights are a
    long holding's share (value or weight, any scale): a negative one is refused. None without a weight of value.
    """
    if any(weight < 0 for weight in weights.values()):
        raise ValueError("effective number of positions takes non-negative weights")
    slices = slice_percents(weights)
    if not slices or any(percent is None for percent in slices.values()):
        return None
    _, herfindahl_points = concentration(percent for percent in slices.values() if percent is not None)
    if herfindahl_points is None or herfindahl_points <= 0:
        return None
    return _ONE_POSITION_POINTS / herfindahl_points
