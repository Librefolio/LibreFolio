"""The orientation of a stored FX rate: one pair, two ways of reading it.

``fx_rates`` keeps each pair once, its two codes in alphabetical order, with the rate of the first in the second
(``fx/storage.normalize_rate_for_storage``). A conversion from ``source`` to ``destination`` reads that rate as it is
when ``source`` sorts first, and its inverse otherwise. The same rule turns a directed rate into the stored one: the
inversion is its own inverse.
"""

from __future__ import annotations


def oriented_rate[R](rate: R, source: str, destination: str) -> R:
    """The rate from ``source`` to ``destination`` of a pair whose rate is kept in alphabetical order (J-1).

    ``rate`` when ``source`` sorts before ``destination``, its inverse otherwise — in the rate's own number type
    (``Decimal``, the PAC's ``ExactRatio``): ``type(rate)(1) / rate``. Applied to a directed rate it gives the stored one,
    since the inversion is its own inverse. A zero rate has no inverse: the type's division error, never a value.
    """
    if source < destination:
        return rate
    return type(rate)(1) / rate
