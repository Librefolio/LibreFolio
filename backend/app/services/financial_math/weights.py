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
_ONE = Decimal("1")
_HUNDRED = Decimal("100")


def share_of(part: Decimal, total: Decimal) -> Decimal | None:
    """``part / total``, unrounded; None when the total is zero or negative."""
    if total <= 0:
        return None
    return part / total


def percent_of(part: Decimal, total: Decimal) -> Decimal | None:
    """:func:`share_of` as a percentage (× 100), unrounded; None when the total is zero or negative."""
    share = share_of(part, total)
    return share * _HUNDRED if share is not None else None


def slice_percents(amounts: Mapping[str, Decimal]) -> dict[str, Decimal]:
    """The slices of an allocation as percentages of their sum, unrounded, in the mapping's order.

    An allocation keeps signed slices — cash below zero is a slice below zero, and the others then add up to more than
    100 (see ``AllocationItem.value``) — so this divides by the signed sum, and an empty or all-zero allocation is all
    zeros rather than unavailable. A sum that cancels out still divides by one and a negative sum flips every sign:
    the allocation charts' rule as it was, kept on purpose (MF-C2 is the follow-up decision).
    """
    total = sum(amounts.values(), _ZERO) or _ONE
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
