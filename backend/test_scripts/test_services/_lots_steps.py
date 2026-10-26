"""Read the lots analysis' histories as days again (J5-5, MF-P4b contract §1.3, §8).

Since J5-5 the seven histories of ``get_lots_analysis`` (``value_history``, ``return_history``, ``price_history``,
``market_price_history``, ``broker_wac_history``, ``cumulative_wac_history``, ``performance_history``) are STEPS: a row
holds from its ``date`` to its ``through``, both included, and two consecutive rows of one key with the same figures are
one row. The contract's rule 1 is that repeating each row over ``date``..``through`` gives, field for field, the one-row-
per-day answer the histories gave before. A test that is about the figures of a day (not about how the days are grouped)
reads the answer through this module: ``daily_points`` on the schema objects, ``expand_steps`` on ``model_dump`` dicts.
A test that is about the grouping itself asserts the steps and says so.

This is the one home of those helpers in the test tree: ``test_lots_change_days_parity.py`` (the step checker and its
oracle ``compress_days``) and every suite that reads a history by day import them from here; none keeps a copy.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any


def daily_points[P](points: Sequence[P] | None) -> list[P]:
    """The one-row-per-day answer a list of step points stands for: each point (a schema object with ``date`` and
    ``through``) repeated on every day from ``date`` to ``through``, as a copy dated that day with ``through`` the same
    day. The order of the points is kept (their keys in order of first appearance, their days ascending); ``None`` is
    an empty list. Every other field is untouched, down to the exponent of its Decimals."""
    days: list[P] = []
    for point in points or []:
        first, last = point.date, point.through  # type: ignore[attr-defined]
        assert first <= last, f"through {last} before date {first}: {point!r}"
        for offset in range((last - first).days + 1):
            day = first + timedelta(days=offset)
            days.append(point if day == first == last else point.model_copy(update={"date": day, "through": day}))  # type: ignore[attr-defined]
    return days


def expand_steps(section_rows: Sequence[Mapping], key_name: str | None) -> list[dict]:
    """The daily rows a step section stands for: every row repeated on each day from ``date`` to ``through`` (both
    included), ``through`` dropped, the other fields untouched. Ordered by ``key_name`` (``None``: one line) then by day,
    so two answers compare whatever the interleaving of their keys. A row without ``through`` is a daily row: it fails
    here, naming it. The rows are ``model_dump(mode="json")`` dicts."""
    days: list[dict] = []
    for row in section_rows:
        assert "through" in row, f"row has no `through` (the series is still one row per day): {dict(row)}"
        first, last = date.fromisoformat(row["date"]), date.fromisoformat(row["through"])
        assert first <= last, f"through before date: {dict(row)}"
        body = {name: value for name, value in row.items() if name != "through"}
        days.extend({**body, "date": (first + timedelta(days=offset)).isoformat()} for offset in range((last - first).days + 1))
    return sorted(days, key=lambda day_row: (-1 if key_name is None else day_row[key_name], day_row["date"]))


def rows_by_key(rows: Sequence[Mapping], key_name: str | None) -> dict[object, list[Mapping]]:
    """The rows of each key, each key's rows in the order they come."""
    groups: dict[object, list[Mapping]] = {}
    for row in rows:
        groups.setdefault(None if key_name is None else row[key_name], []).append(row)
    return groups


def step_values(row: Mapping) -> dict:
    """A step's values: everything but the span (``date``, ``through``); the key stays, equal within a key."""
    return {name: value for name, value in row.items() if name not in ("date", "through")}


def order_by_key(rows: Sequence[Mapping], key_name: str | None) -> list[Mapping]:
    """The rows by key then first day: the order two answers are compared in."""
    return sorted(rows, key=lambda row: (-1 if key_name is None else row[key_name], row["date"]))


def compress_days(daily_rows: Sequence[Mapping], key_name: str | None) -> list[dict]:
    """The MAXIMAL steps of a daily section: the rows of a key, a day apart, with identical values (JSON text, so ``1.10``
    and ``1.1`` differ) are one step; a missing day opens a new one. The oracle of the canonical form, written here and
    nowhere in the product: ``steps == compress_days(expand_steps(steps))`` for any canonical list."""
    steps: list[dict] = []
    open_step: dict[object, dict] = {}
    for row in order_by_key(daily_rows, key_name):
        key = None if key_name is None else row[key_name]
        current = open_step.get(key)
        if current is not None and date.fromisoformat(current["through"]) + timedelta(days=1) == date.fromisoformat(row["date"]) and step_values(current) == step_values(row):
            current["through"] = row["date"]
        else:
            open_step[key] = {**row, "through": row["date"]}
            steps.append(open_step[key])
    return steps


def as_daily_rows(rows: Sequence[Mapping], key_name: str | None) -> list[Mapping[str, Any]]:
    """The daily rows of a section, whichever form it comes in: expanded when it holds steps, as it is when it holds days."""
    return expand_steps(rows, key_name) if rows and "through" in rows[0] else order_by_key(rows, key_name)


def gap_days(item) -> list[date]:
    """The days a ``WACMissingPairInfo`` stands for: its movement ``dates`` and every day of its ``ranges`` (the valuation days with
    no rate, D-P4), ascending. For a test about WHICH days lack a rate, not about how they are grouped."""
    days = set(item.dates)
    for span in item.ranges:
        days.update(span.start + timedelta(days=offset) for offset in range((span.end - span.start).days + 1))
    return sorted(days)


def fold_gap_ranges(dump: dict) -> dict:
    """``dump`` (a ``model_dump(mode="json")`` of a lots analysis) with each missing pair's ``ranges`` folded into its ``dates``:
    the same days, grouped the old way, so an answer with ranges compares with one that lists every day."""
    for pair in (dump.get("data_quality") or {}).get("missing_fx_pairs", []):
        days = set(pair.get("dates", []))
        for span in pair.pop("ranges", []):
            first, last = date.fromisoformat(span["start"]), date.fromisoformat(span["end"])
            days.update((first + timedelta(days=offset)).isoformat() for offset in range((last - first).days + 1))
        pair["dates"] = sorted(days)
    return dump
