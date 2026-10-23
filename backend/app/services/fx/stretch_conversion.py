"""Many conversions of a long range, converted once for each stretch of days on which the rate row is the same (X-Q3).

``convert_bulk`` converts every item it is handed, though an amount converted under the same stored rate row is the same
amount: a rate changes only on the days a row is stored (``fx.conversion.unit_rate_steps``, P3). ``convert_by_stretch``
answers a list the way ``convert_bulk`` does — the same results, to the digit, the same ``(amount, rate date, backward fill)``
for each item and the same errors — but asks ``convert_bulk`` one conversion for each distinct (amount, currencies, rate row),
on the first day it meets it, and copies the answer to the other days of the stretch with their own backward-fill flag.

What stays per item, as in ``convert_bulk``:
- an identity (a currency to itself): the amount, dated as asked, no backward fill;
- a day with no usable rate on or before it: its own error, numbered by its position in ``conversions``;
- the backward-fill flag: ``rate date < day``.

The seams are ``convert`` and ``steps``, the two reads, so a test can stand in for them.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import date as date_type

from backend.app.schemas.common import Currency
from backend.app.services.fx.conversion import convert_bulk, unit_rate_steps

_INDEX = re.compile(r"^Conversion \d+")

Conversions = list[tuple[Currency, str, date_type]]
Results = list[tuple[Currency, date_type, bool] | None]


def rate_not_found_error(index: int, source: str, destination: str, day: date_type) -> str:
    """The error ``convert_bulk`` writes for the ``index``-th conversion of a batch that has no rate on or before ``day``.

    Kept equal to ``convert_bulk``'s text (pinned by the parity tests, on a pair with no rate): a series with no rate does
    not ask ``convert_bulk`` a failure it already knows.
    """
    base, quote = (source, destination) if source < destination else (destination, source)
    return f"Conversion {index}: No FX rate found for {base}/{quote} on or before {day}. Please sync rates using POST /api/v1/fx/currencies/sync"


async def convert_by_stretch(  # noqa: C901 — one pass over the items: identity, no rate, or the stretch it belongs to; then the answers
    session,
    conversions: Conversions,
    *,
    convert: Callable[..., Awaitable[tuple[Results, list[str]]]] = convert_bulk,
    steps: Callable[..., Awaitable[dict]] = unit_rate_steps,
) -> tuple[Results, list[str]]:
    """``convert_bulk(session, conversions, raise_on_error=False)`` with one conversion for each stretch (see the module)."""
    if not conversions:
        return [], []

    days_by_pair: dict[tuple[str, str], list[date_type]] = {}
    for amount, destination, day in conversions:
        if amount.code != destination:
            days_by_pair.setdefault((amount.code, destination), []).append(day)
    pair_steps = await steps(session, {pair: [(min(days), max(days))] for pair, days in days_by_pair.items()}) if days_by_pair else {}

    results: Results = [None] * len(conversions)
    errors: list[tuple[int, str]] = []  # (item, message): answered in the order of the items, as ``convert_bulk`` does
    # Two amounts are one amount only if they print the same: Decimal("1.0") and Decimal("1") convert to different exponents.
    asked: dict[tuple[str, str, str, date_type], int] = {}  # (amount, source, destination, rate day) -> position in ``asked_items``
    asked_items: Conversions = []
    pending: list[tuple[int, int, date_type]] = []  # (item, asked position, rate day)
    for index, (amount, destination, day) in enumerate(conversions):
        if amount.code == destination:
            results[index] = (Currency(code=destination, amount=amount.amount), day, False)
            continue
        rate_day = pair_steps[(amount.code, destination)].rate_day_at(day)
        if rate_day is None:
            errors.append((index, rate_not_found_error(index, amount.code, destination, day)))
            continue
        key = (str(amount.amount), amount.code, destination, rate_day)
        if key not in asked:
            asked[key] = len(asked_items)
            asked_items.append((amount, destination, day))
        pending.append((index, asked[key], rate_day))

    answers: Results = []
    failures: dict[int, str] = {}  # asked position -> what ``convert`` said, without its number
    if asked_items:
        answers, convert_errors = await convert(session, asked_items, raise_on_error=False)
        for message in convert_errors:
            match = _INDEX.match(message)
            failures[int(match.group(0).split()[1]) if match else -1] = message[match.end() :] if match else message
    for index, position, rate_day in pending:
        answer = answers[position]
        if answer is None:
            # ``convert`` failed the whole stretch: each of its days fails, numbered by its own item; a failure it did not
            # explain still leaves an error, never a silent None
            reason = failures.get(position, " failed: no answer for the stretch")
            errors.append((index, f"Conversion {index}{reason}"))
            continue
        converted, _rate_date, _applied = answer
        results[index] = (Currency(code=converted.code, amount=converted.amount), rate_day, rate_day < conversions[index][2])
    if -1 in failures:  # an error that carries no number: kept as it came
        errors.append((len(conversions), failures[-1]))
    return results, [message for _index, message in sorted(errors, key=lambda item: item[0])]
