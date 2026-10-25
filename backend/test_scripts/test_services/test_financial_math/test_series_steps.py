"""
MF-P4b small checkpoint (D-P4 cure B, contract ``CONTRATTO-P4b.md`` §1.1, §6, §8 rule 8b): the shared helpers of the
step series. Pure functions, no DB, no server.

Module under test: ``backend/app/services/financial_math/series_steps.py`` (new) —

* a «point» is anything with ``date`` (first day it holds) and ``through`` (last day, inclusive): an object with those
  attributes (dataclass, pydantic model, ``StepRow``) or a Mapping with those keys. A list of points is sorted by
  ``date``, non-overlapping, gaps allowed;
* ``value_at(points, day)``: binary search on ``date``; the point with ``date <= day <= through`` — the point itself,
  never a copy — or ``None`` before the first, after the last, or in a gap;
* ``points_between(points, start, end)``: the points touching ``[start, end]``, clipped to it. An unclipped point is
  returned as is; a clipped one is a copy with only ``date``/``through`` changed (dataclass → ``dataclasses.replace``,
  pydantic → ``model_copy(update=...)``, Mapping → a dict copy). Empty when nothing touches the window (the AI Export's
  empty bucket) or ``start > end``;
* ``steps_from_rows(rows, *, day, values, range_start, range_end, key=None, is_gap=None, ends=None)``: the change-day
  rows of one or more keys become ``StepRow(row, date, through, key)`` steps — identical consecutive rows merged with
  Decimals compared by ``as_tuple()`` (``1.10`` is not ``1.1``), ``through`` the day before the key's next kept row or
  ``ends[key]`` or ``range_end``, gaps opened by ``is_gap`` rows, clipped to ``[range_start, range_end]``.

And in ``backend/app/schemas/common.py``: ``DateSpan`` (``start``/``end``, ``end >= start``) and ``StepSpan``
(``date``/``through``, ``through >= date``), both ``StrictModel``; ``StepSpan`` is the base of every series point.

The new names are looked up inside each test, so the file collects on HEAD ``445386f80`` (where none of them exists)
and every test fails there by naming what is missing.
"""

from __future__ import annotations

import dataclasses
import functools
import importlib
import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from types import MappingProxyType
from typing import Any

import pytest
from pydantic import ValidationError

from backend.app.schemas import common
from backend.app.schemas.common import StrictModel

D = Decimal
D0 = date(2026, 10, 1)


def d(n: int) -> date:
    """Day ``n`` of the fixture calendar (``d(0)`` = 2026-10-01)."""
    return D0 + timedelta(days=n)


# =============================================================================
# Lookups — the new names, resolved at test time so the file collects on HEAD
# =============================================================================

_SERIES_STEPS = "backend.app.services.financial_math.series_steps"


def _series_steps():
    try:
        return importlib.import_module(_SERIES_STEPS)
    except ModuleNotFoundError as exc:
        if exc.name != _SERIES_STEPS:
            raise
        pytest.fail(f"{_SERIES_STEPS} does not exist yet (MF-P4b §6): {exc}")


def _helper(name: str):
    module = _series_steps()
    found = getattr(module, name, None)
    if found is None:
        pytest.fail(f"{_SERIES_STEPS}.{name} is missing (MF-P4b §6)")
    return found


def value_at(points, day):
    return _helper("value_at")(points, day)


def points_between(points, start, end):
    return _helper("points_between")(points, start, end)


def steps_from_rows(rows, **kwargs):
    return _helper("steps_from_rows")(rows, **kwargs)


def _schema(name: str):
    found = getattr(common, name, None)
    if found is None:
        pytest.fail(f"backend.app.schemas.common.{name} is missing (MF-P4b §1.1, §6)")
    return found


@functools.cache
def _nav_point_cls():
    """A series point schema the way the report declares one: ``StepSpan`` plus its own fields."""
    step_span = _schema("StepSpan")

    class NavPoint(step_span):
        nav: Decimal
        label: str = "x"

    return NavPoint


# =============================================================================
# Point kinds — the three a point may be, plus StepRow and a read-only Mapping
# =============================================================================


@dataclass(frozen=True, slots=True)
class DcPoint:
    date: date
    through: date
    nav: Decimal
    label: str = "x"


def _make_dict(start: date, through: date, nav: Decimal):
    return {"date": start, "through": through, "nav": nav, "label": "x"}


def _make_proxy(start: date, through: date, nav: Decimal):
    return MappingProxyType({"date": start, "through": through, "nav": nav, "label": "x"})


def _make_dataclass(start: date, through: date, nav: Decimal):
    return DcPoint(date=start, through=through, nav=nav)


def _make_pydantic(start: date, through: date, nav: Decimal):
    return _nav_point_cls()(date=start, through=through, nav=nav)


def _make_steprow(start: date, through: date, nav: Decimal):
    return _helper("StepRow")(row=("payload", nav), date=start, through=through, key="k")


KINDS = {
    "dict": _make_dict,
    "mapping_proxy": _make_proxy,
    "dataclass": _make_dataclass,
    "pydantic_stepspan_subclass": _make_pydantic,
    "steprow": _make_steprow,
}


def _get(point: Any, field: str):
    return point[field] if isinstance(point, (dict, MappingProxyType)) else getattr(point, field)


def _span(point: Any) -> tuple[date, date]:
    return _get(point, "date"), _get(point, "through")


def _payload(point: Any) -> Any:
    """Every field of a point except ``date``/``through``: what a clip must leave untouched."""
    if isinstance(point, (dict, MappingProxyType)):
        return {k: v for k, v in point.items() if k not in ("date", "through")}
    if dataclasses.is_dataclass(point):
        return {f.name: getattr(point, f.name) for f in dataclasses.fields(point) if f.name not in ("date", "through")}
    return {k: v for k, v in point.model_dump().items() if k not in ("date", "through")}


def _three_points(make):
    """P1 = d2..d4, P2 = d5..d5, gap d6..d7, P3 = d8..d10."""
    return [make(d(2), d(4), D("1.10")), make(d(5), d(5), D("2")), make(d(8), d(10), D("3.000"))]


# =============================================================================
# value_at
# =============================================================================


class TestValueAt:
    @pytest.mark.parametrize("kind", list(KINDS))
    @pytest.mark.parametrize(
        ("day_n", "expected_index"),
        [
            (1, None),  # before the first point
            (2, 0),  # first point, its first day
            (3, 0),  # inside
            (4, 0),  # its last day (through is inclusive)
            (5, 1),  # a single-day point
            (6, None),  # gap
            (7, None),  # gap, last day of it
            (8, 2),  # first day after the gap
            (10, 2),  # last day of the last point
            (11, None),  # after the last point
            (400, None),
            (-400, None),
        ],
    )
    def test_finds_the_point_holding_the_day_or_none(self, kind, day_n, expected_index):
        points = _three_points(KINDS[kind])
        found = value_at(points, d(day_n))
        if expected_index is None:
            assert found is None
        else:
            assert found is points[expected_index], "value_at returns the point itself, never a copy"

    @pytest.mark.parametrize("kind", list(KINDS))
    def test_empty_list_is_none(self, kind):
        assert value_at([], d(3)) is None

    @pytest.mark.parametrize("kind", list(KINDS))
    def test_single_point(self, kind):
        point = KINDS[kind](d(3), d(6), D("7"))
        assert value_at([point], d(2)) is None
        for n in range(3, 7):
            assert value_at([point], d(n)) is point
        assert value_at([point], d(7)) is None

    def test_single_day_points_back_to_back(self):
        points = [_make_dataclass(d(n), d(n), D(n)) for n in range(10)]
        for n in range(10):
            assert value_at(points, d(n)) is points[n]
        assert value_at(points, d(10)) is None
        assert value_at(points, d(-1)) is None

    def test_a_tuple_of_points_is_a_sequence_too(self):
        points = tuple(_three_points(_make_dict))
        assert value_at(points, d(9)) is points[2]

    @pytest.mark.parametrize("seed", range(40))
    def test_agrees_with_a_linear_scan_on_random_lists_with_gaps(self, seed):
        rng = random.Random(seed)
        points, cursor = [], rng.randint(-20, 5)
        for _ in range(rng.randint(0, 25)):
            cursor += rng.randint(0, 3)  # a gap of 0..3 days before the point
            length = rng.randint(0, 6)
            points.append(_make_dict(d(cursor), d(cursor + length), D(rng.randint(0, 9))))
            cursor += length + 1
        for n in range(-25, cursor + 5):
            expected = next((p for p in points if p["date"] <= d(n) <= p["through"]), None)
            assert value_at(points, d(n)) is expected, f"seed {seed}, day {d(n)}"

    def test_binary_search_reads_a_logarithmic_number_of_points(self):
        """§6: «ricerca binaria su ``date``». A series of a 2 000-year step history must not be scanned per lookup."""

        class CountingSequence(Sequence):
            def __init__(self, items):
                self._items = items
                self.reads = 0

            def __len__(self):
                return len(self._items)

            def __getitem__(self, index):
                if isinstance(index, slice):
                    self.reads += len(range(*index.indices(len(self._items))))
                else:
                    self.reads += 1
                return self._items[index]

        n = 100_000
        points = CountingSequence([_make_dataclass(d(2 * i), d(2 * i), D(i)) for i in range(n)])  # every other day a gap
        for probe, expected in ((2 * 77_777, 77_777), (2 * 77_777 + 1, None), (0, 0), (2 * (n - 1), n - 1), (-5, None), (2 * n + 9, None)):
            points.reads = 0
            found = value_at(points, d(probe))
            assert (found is None) if expected is None else (found is points._items[expected])
            assert points.reads <= 100, f"value_at read {points.reads} of {n} points for one day: that is not a binary search"


# =============================================================================
# points_between
# =============================================================================


class TestPointsBetween:
    @pytest.mark.parametrize("kind", list(KINDS))
    def test_window_inside_one_point_is_a_clipped_copy(self, kind):
        points = _three_points(KINDS[kind])
        before = _payload(points[0]), _span(points[0])
        result = points_between(points, d(3), d(3))
        assert isinstance(result, list)
        assert len(result) == 1
        clipped = result[0]
        assert clipped is not points[0]
        assert _span(clipped) == (d(3), d(3))
        assert _payload(clipped) == before[0], "a clip changes only date and through"
        assert (_payload(points[0]), _span(points[0])) == before, "the original point is left untouched"

    @pytest.mark.parametrize("kind", list(KINDS))
    def test_clipped_copy_keeps_its_kind(self, kind):
        points = _three_points(KINDS[kind])
        clipped = points_between(points, d(9), d(9))[0]
        original = points[2]
        if isinstance(original, (dict, MappingProxyType)):
            assert type(clipped) is dict, "a clipped Mapping is a dict copy"
        else:
            assert type(clipped) is type(original), "a clipped dataclass / pydantic model / StepRow keeps its class"
        if kind == "steprow":
            assert clipped.row is original.row and clipped.key == original.key

    @pytest.mark.parametrize("kind", list(KINDS))
    def test_window_across_points_clips_only_the_edges(self, kind):
        points = _three_points(KINDS[kind])
        result = points_between(points, d(3), d(9))
        assert [_span(p) for p in result] == [(d(3), d(4)), (d(5), d(5)), (d(8), d(9))]
        assert result[0] is not points[0]
        assert result[1] is points[1], "an unclipped point is returned as is"
        assert result[2] is not points[2]
        assert [_payload(p) for p in result] == [_payload(p) for p in points]

    @pytest.mark.parametrize("kind", list(KINDS))
    def test_window_on_the_exact_edges_returns_every_point_as_is(self, kind):
        points = _three_points(KINDS[kind])
        result = points_between(points, d(2), d(10))
        assert len(result) == 3
        assert all(got is want for got, want in zip(result, points, strict=True))

    @pytest.mark.parametrize("kind", list(KINDS))
    def test_window_wider_than_the_series_returns_every_point_as_is(self, kind):
        points = _three_points(KINDS[kind])
        result = points_between(points, d(-100), d(100))
        assert len(result) == 3
        assert all(got is want for got, want in zip(result, points, strict=True))

    @pytest.mark.parametrize("kind", list(KINDS))
    @pytest.mark.parametrize(
        ("start_n", "end_n", "spans"),
        [
            (4, 5, [(4, 4), (5, 5)]),  # starts on P1's last day, ends on P2's only day
            (0, 2, [(2, 2)]),  # ends on P1's first day
            (10, 12, [(10, 10)]),  # starts on P3's last day
            (5, 8, [(5, 5), (8, 8)]),  # across the gap, touching P3's first day
            (6, 8, [(8, 8)]),  # starts in the gap
            (4, 7, [(4, 4), (5, 5)]),  # ends in the gap
        ],
    )
    def test_touching_edges_exactly(self, kind, start_n, end_n, spans):
        points = _three_points(KINDS[kind])
        result = points_between(points, d(start_n), d(end_n))
        assert [_span(p) for p in result] == [(d(a), d(b)) for a, b in spans]

    @pytest.mark.parametrize("kind", list(KINDS))
    @pytest.mark.parametrize(
        ("start_n", "end_n"),
        [
            (6, 7),  # the whole gap, nothing else
            (6, 6),
            (0, 1),  # before the first point: the AI Export's empty bucket
            (-400, -1),
            (11, 20),  # after the last point
            (11, 11),
        ],
    )
    def test_window_touching_no_point_is_empty(self, kind, start_n, end_n):
        assert points_between(_three_points(KINDS[kind]), d(start_n), d(end_n)) == []

    @pytest.mark.parametrize("kind", list(KINDS))
    @pytest.mark.parametrize(("start_n", "end_n"), [(5, 3), (10, 2), (3, 2)])
    def test_start_after_end_is_empty(self, kind, start_n, end_n):
        assert points_between(_three_points(KINDS[kind]), d(start_n), d(end_n)) == []

    def test_empty_series_is_empty(self):
        assert points_between([], d(0), d(10)) == []

    def test_pydantic_clip_goes_through_model_copy_and_dumps_the_new_span(self):
        point = _make_pydantic(d(2), d(10), D("10.50"))
        clipped = points_between([point], d(4), d(6))[0]
        dumped = clipped.model_dump(mode="json")
        assert dumped["date"] == d(4).isoformat() and dumped["through"] == d(6).isoformat()
        assert clipped.nav == D("10.50") and clipped.nav.as_tuple() == D("10.50").as_tuple()
        assert point.date == d(2) and point.through == d(10)

    @pytest.mark.parametrize("seed", range(30))
    def test_every_day_of_the_window_reads_the_same_point_as_value_at(self, seed):
        """Clipping never moves a value: each day of [start, end] finds, in the clip, a point equal to the original's."""
        rng = random.Random(seed)
        points, cursor = [], 0
        for _ in range(rng.randint(0, 12)):
            cursor += rng.randint(0, 2)
            length = rng.randint(0, 5)
            points.append(_make_dataclass(d(cursor), d(cursor + length), D(rng.randint(0, 99))))
            cursor += length + 1
        start = d(rng.randint(-3, cursor + 2))
        end = start + timedelta(days=rng.randint(0, 15))
        clipped = points_between(points, start, end)
        for p in clipped:
            assert start <= p.date <= p.through <= end
        n = start
        while n <= end:
            original, sliced = value_at(points, n), value_at(clipped, n)
            assert (original is None) == (sliced is None), f"seed {seed}, day {n}"
            if original is not None:
                assert sliced.nav is original.nav
            n += timedelta(days=1)
        outside = [p for p in points if p.through < start or p.date > end]
        assert len(clipped) == len(points) - len(outside)


# =============================================================================
# steps_from_rows
# =============================================================================


@dataclass(frozen=True, eq=False)
class Row:
    """A change-day row as a caller hands it: identity matters, equality does not."""

    day: date
    value: Any
    key: Any = None
    gap: bool = False


def _steps(rows, *, start=d(0), end=d(20), keyed=False, gaps=False, ends=None):
    kwargs: dict[str, Any] = {"day": lambda r: r.day, "values": lambda r: r.value, "range_start": start, "range_end": end}
    if keyed:
        kwargs["key"] = lambda r: r.key
    if gaps:
        kwargs["is_gap"] = lambda r: r.gap
    if ends is not None:
        kwargs["ends"] = ends
    return steps_from_rows(rows, **kwargs)


def _shape(steps) -> list[tuple]:
    """(row, date, through, key) of each step, rows by identity."""
    return [(s.row, s.date, s.through, s.key) for s in steps]


class TestStepRow:
    def test_is_a_frozen_slotted_dataclass_with_the_contract_fields(self):
        step_row = _helper("StepRow")
        assert dataclasses.is_dataclass(step_row)
        assert [f.name for f in dataclasses.fields(step_row)] == ["row", "date", "through", "key"]
        assert hasattr(step_row, "__slots__")
        instance = step_row(row="r", date=d(1), through=d(2), key=None)
        with pytest.raises(dataclasses.FrozenInstanceError):
            instance.date = d(0)

    def test_is_generic_on_the_row(self):
        step_row = _helper("StepRow")
        assert step_row[Row] is not None


class TestStepsMerge:
    def test_identical_consecutive_rows_are_one_step_keeping_the_first_row(self):
        r1, r3, r5, r8 = Row(d(1), D("1.10")), Row(d(3), D("1.10")), Row(d(5), D("2")), Row(d(8), D("2"))
        assert _shape(_steps([r1, r3, r5, r8], start=d(1), end=d(10))) == [(r1, d(1), d(4), None), (r5, d(5), d(10), None)]

    def test_a_b_a_is_three_steps(self):
        r1, r2, r3 = Row(d(1), D("1")), Row(d(2), D("2")), Row(d(3), D("1"))
        assert _shape(_steps([r1, r2, r3], start=d(1), end=d(5))) == [(r1, d(1), d(1), None), (r2, d(2), d(2), None), (r3, d(3), d(5), None)]

    @pytest.mark.parametrize(
        ("first", "second"),
        [
            (D("1.10"), D("1.1")),
            (D("1.1"), D("1.10")),
            (D("0"), D("-0")),
            (D("10"), D("1E+1")),
            (D("0.0"), D("0")),
            ((D("1.10"), "EUR"), (D("1.1"), "EUR")),
            ([D("1.10"), None], [D("1.1"), None]),
            ({"a": D("1.10")}, {"a": D("1.1")}),
            ({"x": (D("2.0"), None), "y": "EUR"}, {"x": (D("2.00"), None), "y": "EUR"}),
            ((D("1"), {"n": [D("3.5")]}), (D("1"), {"n": [D("3.50")]})),
            ((D("1"), "EUR"), (D("1"), "USD")),
            ((D("1"),), (D("1"), D("1"))),
        ],
        ids=lambda v: repr(v),
    )
    def test_values_differing_by_the_exponent_or_the_content_stay_two_steps(self, first, second):
        """§8 rule 8b: ``1.10`` and ``1.1`` are two steps — compared with ``as_tuple()``, recursively."""
        r1, r2 = Row(d(1), first), Row(d(2), second)
        assert _shape(_steps([r1, r2], start=d(1), end=d(3))) == [(r1, d(1), d(1), None), (r2, d(2), d(3), None)]

    @pytest.mark.parametrize(
        ("first", "second"),
        [
            (D("1.10"), D("1.10")),
            (D("-0"), D("-0")),
            ((D("1.10"), "EUR"), (D("1.10"), "EUR")),
            ([D("2.5"), None], [D("2.5"), None]),
            ({"a": D("1.10"), "b": (D("2"), [D("3.0")])}, {"b": (D("2"), [D("3.0")]), "a": D("1.10")}),
            (None, None),
            ("EUR", "EUR"),
            (7, 7),
        ],
        ids=lambda v: repr(v),
    )
    def test_values_equal_with_the_same_exponent_merge(self, first, second):
        """Equal content, distinct objects (fresh Decimals, a dict in another key order): one step."""
        r1, r2 = Row(d(1), first), Row(d(2), second)
        assert _shape(_steps([r1, r2], start=d(1), end=d(3))) == [(r1, d(1), d(3), None)]


class TestStepsThrough:
    def test_through_is_the_day_before_the_next_row_and_range_end_for_the_last(self):
        r1, r4, r9 = Row(d(1), D("1")), Row(d(4), D("2")), Row(d(9), D("3"))
        assert _shape(_steps([r1, r4, r9], start=d(0), end=d(12))) == [(r1, d(1), d(3), None), (r4, d(4), d(8), None), (r9, d(9), d(12), None)]

    def test_days_before_the_first_row_have_no_step(self):
        r5 = Row(d(5), D("1"))
        assert _shape(_steps([r5], start=d(0), end=d(7))) == [(r5, d(5), d(7), None)]

    def test_rows_may_be_any_iterable(self):
        r1, r3 = Row(d(1), D("1")), Row(d(3), D("2"))
        assert _shape(_steps((r for r in [r1, r3]), start=d(1), end=d(4))) == [(r1, d(1), d(2), None), (r3, d(3), d(4), None)]

    def test_no_rows_no_steps(self):
        assert _steps([], start=d(0), end=d(10)) == []
        assert _steps([], start=d(0), end=d(10), keyed=True, gaps=True, ends={"a": d(3)}) == []


class TestStepsKeys:
    def test_interleaved_keys_each_get_their_own_steps_in_order_of_first_appearance(self):
        b2, a1, b5, a3, a6 = Row(d(2), D("1"), "B"), Row(d(1), D("1"), "A"), Row(d(5), D("2"), "B"), Row(d(3), D("2"), "A"), Row(d(6), D("3"), "A")
        result = _steps([b2, a1, b5, a3, a6], start=d(0), end=d(10), keyed=True)
        assert _shape(result) == [
            (b2, d(2), d(4), "B"),
            (b5, d(5), d(10), "B"),
            (a1, d(1), d(2), "A"),
            (a3, d(3), d(5), "A"),
            (a6, d(6), d(10), "A"),
        ]

    def test_a_key_does_not_merge_with_another_keys_equal_value(self):
        a1, b2, a3 = Row(d(1), D("1"), "A"), Row(d(2), D("1"), "B"), Row(d(3), D("1"), "A")
        assert _shape(_steps([a1, b2, a3], start=d(0), end=d(5), keyed=True)) == [(a1, d(1), d(5), "A"), (b2, d(2), d(5), "B")]

    def test_same_day_on_two_keys_is_allowed(self):
        a, b = Row(d(2), D("1"), "A"), Row(d(2), D("9"), "B")
        assert _shape(_steps([a, b], start=d(0), end=d(3), keyed=True)) == [(a, d(2), d(3), "A"), (b, d(2), d(3), "B")]

    def test_without_key_every_step_has_key_none(self):
        steps = _steps([Row(d(1), D("1"), key="ignored"), Row(d(2), D("2"), key="other")], start=d(0), end=d(3))
        assert [s.key for s in steps] == [None, None]

    def test_any_hashable_key(self):
        k1, k2 = ("broker", 7), ("broker", 8)
        r1, r2 = Row(d(1), D("1"), k1), Row(d(1), D("1"), k2)
        assert [s.key for s in _steps([r1, r2], start=d(0), end=d(2), keyed=True)] == [k1, k2]


class TestStepsEnds:
    def test_a_closed_key_ends_on_its_last_day_and_ignores_later_rows(self):
        a1, a4, a8 = Row(d(1), D("1"), "A"), Row(d(4), D("2"), "A"), Row(d(8), D("3"), "A")
        b2 = Row(d(2), D("5"), "B")
        result = _steps([a1, b2, a4, a8], start=d(0), end=d(10), keyed=True, ends={"A": d(6), "B": d(10)})
        assert _shape(result) == [(a1, d(1), d(3), "A"), (a4, d(4), d(6), "A"), (b2, d(2), d(10), "B")]

    def test_a_key_without_an_end_runs_to_range_end(self):
        a1, b2 = Row(d(1), D("1"), "A"), Row(d(2), D("5"), "B")
        result = _steps([a1, b2], start=d(0), end=d(10), keyed=True, ends={"A": d(3)})
        assert _shape(result) == [(a1, d(1), d(3), "A"), (b2, d(2), d(10), "B")]

    def test_end_on_a_row_day_is_a_single_day_step(self):
        a1, a5 = Row(d(1), D("1"), "A"), Row(d(5), D("2"), "A")
        assert _shape(_steps([a1, a5], keyed=True, ends={"A": d(5)})) == [(a1, d(1), d(4), "A"), (a5, d(5), d(5), "A")]

    def test_end_before_the_first_row_produces_nothing_for_that_key(self):
        a4, b4 = Row(d(4), D("1"), "A"), Row(d(4), D("1"), "B")
        assert _shape(_steps([a4, b4], start=d(0), end=d(10), keyed=True, ends={"A": d(3)})) == [(b4, d(4), d(10), "B")]

    def test_end_after_range_end_is_capped(self):
        a1 = Row(d(1), D("1"), "A")
        assert _shape(_steps([a1], start=d(0), end=d(10), keyed=True, ends={"A": d(30)})) == [(a1, d(1), d(10), "A")]

    def test_end_before_range_start_produces_nothing(self):
        a1 = Row(d(1), D("1"), "A")
        assert _steps([a1], start=d(5), end=d(10), keyed=True, ends={"A": d(4)}) == []

    def test_merged_run_ends_on_the_key_end(self):
        a1, a4 = Row(d(1), D("1"), "A"), Row(d(4), D("1"), "A")
        assert _shape(_steps([a1, a4], start=d(0), end=d(10), keyed=True, ends={"A": d(6)})) == [(a1, d(1), d(6), "A")]


class TestStepsGaps:
    def test_a_gap_ends_the_step_and_the_next_row_opens_a_new_one_even_with_equal_values(self):
        r1, g3, r5 = Row(d(1), D("1")), Row(d(3), None, gap=True), Row(d(5), D("1"))
        assert _shape(_steps([r1, g3, r5], start=d(0), end=d(8), gaps=True)) == [(r1, d(1), d(2), None), (r5, d(5), d(8), None)]

    def test_a_gap_at_the_start(self):
        g1, r3 = Row(d(1), None, gap=True), Row(d(3), D("1"))
        assert _shape(_steps([g1, r3], start=d(0), end=d(8), gaps=True)) == [(r3, d(3), d(8), None)]

    def test_a_gap_at_the_end(self):
        r1, g4 = Row(d(1), D("1")), Row(d(4), None, gap=True)
        assert _shape(_steps([r1, g4], start=d(0), end=d(8), gaps=True)) == [(r1, d(1), d(3), None)]

    def test_two_gaps_in_a_row(self):
        r1, g3, g4, r6 = Row(d(1), D("1")), Row(d(3), None, gap=True), Row(d(4), None, gap=True), Row(d(6), D("2"))
        assert _shape(_steps([r1, g3, g4, r6], start=d(0), end=d(8), gaps=True)) == [(r1, d(1), d(2), None), (r6, d(6), d(8), None)]

    def test_only_gaps(self):
        assert _steps([Row(d(1), None, gap=True), Row(d(4), None, gap=True)], start=d(0), end=d(8), gaps=True) == []

    def test_a_gap_before_range_start_leaves_the_start_uncovered(self):
        r0, g2, r5 = Row(d(0), D("1")), Row(d(2), None, gap=True), Row(d(5), D("2"))
        assert _shape(_steps([r0, g2, r5], start=d(3), end=d(8), gaps=True)) == [(r5, d(5), d(8), None)]

    def test_gaps_are_per_key(self):
        a1, bg2, a3, b4 = Row(d(1), D("1"), "A"), Row(d(2), None, "B", gap=True), Row(d(3), D("1"), "A"), Row(d(4), D("1"), "B")
        result = _steps([a1, bg2, a3, b4], start=d(0), end=d(6), keyed=True, gaps=True)
        assert _shape(result) == [(a1, d(1), d(6), "A"), (b4, d(4), d(6), "B")]

    def test_a_gap_after_the_key_end_changes_nothing(self):
        a1, ag5 = Row(d(1), D("1"), "A"), Row(d(5), None, "A", gap=True)
        assert _shape(_steps([a1, ag5], start=d(0), end=d(8), keyed=True, gaps=True, ends={"A": d(3)})) == [(a1, d(1), d(3), "A")]


class TestStepsClipping:
    def test_the_step_holding_range_start_starts_there_with_its_row(self):
        r0, r5 = Row(d(0), D("1")), Row(d(5), D("2"))
        assert _shape(_steps([r0, r5], start=d(2), end=d(10))) == [(r0, d(2), d(4), None), (r5, d(5), d(10), None)]

    def test_steps_ending_before_range_start_are_dropped(self):
        r0, r2, r6 = Row(d(0), D("1")), Row(d(2), D("2")), Row(d(6), D("3"))
        assert _shape(_steps([r0, r2, r6], start=d(2), end=d(10))) == [(r2, d(2), d(5), None), (r6, d(6), d(10), None)]

    def test_a_run_crossing_range_start_is_one_step_with_its_first_row(self):
        r0, r4 = Row(d(0), D("1.0")), Row(d(4), D("1.0"))
        assert _shape(_steps([r0, r4], start=d(2), end=d(10))) == [(r0, d(2), d(10), None)]

    def test_steps_starting_after_range_end_are_dropped_and_through_is_capped(self):
        r1, r6, r12 = Row(d(1), D("1")), Row(d(6), D("2")), Row(d(12), D("3"))
        assert _shape(_steps([r1, r6, r12], start=d(0), end=d(10))) == [(r1, d(1), d(5), None), (r6, d(6), d(10), None)]

    def test_a_row_on_range_end_is_a_single_day_step(self):
        r1, r10 = Row(d(1), D("1")), Row(d(10), D("2"))
        assert _shape(_steps([r1, r10], start=d(0), end=d(10))) == [(r1, d(1), d(9), None), (r10, d(10), d(10), None)]

    def test_a_single_day_range(self):
        r0, r3, r9 = Row(d(0), D("1")), Row(d(3), D("2")), Row(d(9), D("3"))
        assert _shape(_steps([r0, r3, r9], start=d(5), end=d(5))) == [(r3, d(5), d(5), None)]

    def test_every_row_before_the_range_carries_the_last_one_in(self):
        rows = [Row(d(n), D(n)) for n in range(5)]
        assert _shape(_steps(rows, start=d(10), end=d(12))) == [(rows[-1], d(10), d(12), None)]


class TestStepsRefusals:
    def test_a_repeated_key_day_is_refused(self):
        with pytest.raises(ValueError):
            _steps([Row(d(1), D("1")), Row(d(1), D("2"))], start=d(0), end=d(3))

    def test_a_repeated_key_day_is_refused_even_with_equal_values_and_other_keys_between(self):
        with pytest.raises(ValueError):
            _steps([Row(d(1), D("1"), "A"), Row(d(1), D("1"), "B"), Row(d(1), D("1"), "A")], start=d(0), end=d(3), keyed=True)

    def test_a_repeated_key_day_outside_the_range_is_refused_too(self):
        with pytest.raises(ValueError):
            _steps([Row(d(1), D("1")), Row(d(1), D("1"))], start=d(5), end=d(8))

    def test_range_start_after_range_end_is_refused(self):
        with pytest.raises(ValueError):
            _steps([Row(d(1), D("1"))], start=d(5), end=d(4))

    def test_range_start_after_range_end_is_refused_without_rows(self):
        with pytest.raises(ValueError):
            _steps([], start=d(5), end=d(4))


class TestStepsAreReadableAsPoints:
    def test_value_at_and_points_between_read_the_output(self):
        r1, r4, r9 = Row(d(1), D("1")), Row(d(4), D("2")), Row(d(9), D("3"))
        steps = _steps([r1, r4, r9], start=d(0), end=d(12))
        assert value_at(steps, d(0)) is None
        assert value_at(steps, d(6)).row is r4
        assert value_at(steps, d(12)).row is r9
        window = points_between(steps, d(3), d(4))
        assert [(s.row, s.date, s.through) for s in window] == [(r1, d(3), d(3)), (r4, d(4), d(4))]


# -----------------------------------------------------------------------------
# Property test: expanding the steps to days equals the day-by-day reading of the rows
# -----------------------------------------------------------------------------

_POOL = [
    D("1.10"),
    D("1.1"),
    D("2"),
    D("2.0"),
    (D("1.0"), "EUR"),
    (D("1.00"), "EUR"),
    {"n": D("5")},
    {"n": D("5.0")},
    [D("3"), None],
    "x",
]


def _canon(value: Any) -> Any:
    """The contract's equality as a hashable key: Decimals by ``as_tuple()``, recursively; the rest by value."""
    if isinstance(value, Decimal):
        return ("D", value.as_tuple())
    if isinstance(value, tuple):
        return ("T", tuple(_canon(v) for v in value))
    if isinstance(value, list):
        return ("L", tuple(_canon(v) for v in value))
    if isinstance(value, dict):
        return ("M", tuple(sorted((k, _canon(v)) for k, v in value.items())))
    return ("O", value)


def _random_case(seed: int):
    rng = random.Random(seed)
    single = seed % 4 == 0  # one series, key=None
    keys = [None] if single else rng.sample(["a", "b", "c", "d"], rng.randint(1, 4))
    with_gaps = rng.random() < 0.75
    per_key: dict[Any, list[Row]] = {}
    for k in keys:
        days = sorted(rng.sample(range(-6, 26), rng.randint(0, 9)))
        # fresh Decimal objects each time: equality must come from content, not identity
        per_key[k] = [Row(d(n), _canon_copy(rng.choice(_POOL)), k, gap=with_gaps and rng.random() < 0.2) for n in days]
    ends = None
    if not single and rng.random() < 0.6:
        ends = {k: d(rng.randint(-7, 28)) for k in keys if rng.random() < 0.6}
    start = d(rng.randint(-4, 16))
    end = start + timedelta(days=rng.randint(0, 16))
    # interleave the keys at random, each key's rows staying in day order
    queues = {k: list(rows) for k, rows in per_key.items()}
    rows: list[Row] = []
    while any(queues.values()):
        k = rng.choice([k for k, q in queues.items() if q])
        rows.append(queues[k].pop(0))
    return single, with_gaps, per_key, ends, start, end, rows


def _canon_copy(value: Any) -> Any:
    if isinstance(value, Decimal):
        return Decimal(str(value))
    if isinstance(value, tuple):
        return tuple(_canon_copy(v) for v in value)
    if isinstance(value, list):
        return [_canon_copy(v) for v in value]
    if isinstance(value, dict):
        return {k: _canon_copy(v) for k, v in value.items()}
    return value


def _oracle(rows_of_key: list[Row], end_of_key: date | None, day: date):
    """The value of a key on a day, read row by row: the last row on or before it, unless a gap, closed, or none."""
    if end_of_key is not None and day > end_of_key:
        return None
    last = None
    for row in rows_of_key:
        if row.day <= day:
            last = row
    if last is None or last.gap:
        return None
    return _canon(last.value)


@pytest.mark.parametrize("seed", range(300))
def test_steps_expand_to_the_day_by_day_reading_of_the_rows(seed):
    single, with_gaps, per_key, ends, start, end, rows = _random_case(seed)
    steps = _steps(rows, start=start, end=end, keyed=not single, gaps=with_gaps, ends=ends)
    ends = ends or {}

    covered: dict[tuple[Any, date], Any] = {}
    seen_keys: list[Any] = []
    by_key: dict[Any, list] = {}
    for s in steps:
        assert start <= s.date <= s.through <= end, f"seed {seed}: step {s.date}..{s.through} outside [{start}, {end}]"
        assert s.key in per_key, f"seed {seed}: unknown key {s.key!r}"
        assert not s.row.gap, f"seed {seed}: a gap row produced a step"
        assert s.row.key == s.key or single
        if not seen_keys or seen_keys[-1] != s.key:
            assert s.key not in seen_keys, f"seed {seed}: the steps of key {s.key!r} are not contiguous"
            seen_keys.append(s.key)
        by_key.setdefault(s.key, []).append(s)
        day = s.date
        while day <= s.through:
            assert (s.key, day) not in covered, f"seed {seed}: day {day} of key {s.key!r} covered twice"
            covered[(s.key, day)] = _canon(s.row.value)
            day += timedelta(days=1)

    first_appearance = list(dict.fromkeys(r.key for r in rows))
    assert seen_keys == [k for k in first_appearance if k in seen_keys], f"seed {seed}: keys out of first-appearance order"

    for k, rows_of_key in per_key.items():
        day = start
        while day <= end:
            assert covered.get((k, day)) == _oracle(rows_of_key, ends.get(k), day), f"seed {seed}, key {k!r}, day {day}"
            day += timedelta(days=1)

        kept = [r for r in rows_of_key if ends.get(k) is None or r.day <= ends[k]]
        for prev, nxt in zip(by_key.get(k, []), by_key.get(k, [])[1:], strict=False):
            assert prev.through < nxt.date, f"seed {seed}: steps of key {k!r} out of order or overlapping"
            if prev.through + timedelta(days=1) == nxt.date:
                assert _canon(prev.row.value) != _canon(nxt.row.value), f"seed {seed}: two adjacent equal steps (not maximal) on key {k!r}"
        for s in by_key.get(k, []):
            assert s.row.day == s.date or (s.date == start and s.row.day < start), f"seed {seed}: step row {s.row.day} does not open step {s.date}"
            index = next(i for i, r in enumerate(kept) if r is s.row)
            if index > 0:
                before = kept[index - 1]
                assert before.gap or _canon(before.value) != _canon(s.row.value), f"seed {seed}: step row is not the first row of its run"


# =============================================================================
# Schemas — DateSpan and StepSpan (schemas/common.py)
# =============================================================================


class TestDateSpan:
    def test_valid_and_single_day(self):
        span_cls = _schema("DateSpan")
        span = span_cls(start=d(1), end=d(5))
        assert (span.start, span.end) == (d(1), d(5))
        same = span_cls(start=d(3), end=d(3))
        assert same.start == same.end == d(3)

    def test_end_before_start_is_refused(self):
        with pytest.raises(ValidationError):
            _schema("DateSpan")(start=d(5), end=d(4))

    def test_iso_strings_validate_to_dates_and_dump_back(self):
        span = _schema("DateSpan").model_validate({"start": "2026-10-23", "end": "2026-10-26"})
        assert span.start == date(2026, 10, 23) and span.end == date(2026, 10, 26)
        assert span.model_dump(mode="json") == {"start": "2026-10-23", "end": "2026-10-26"}

    def test_is_strict(self):
        span_cls = _schema("DateSpan")
        assert issubclass(span_cls, StrictModel)
        with pytest.raises(ValidationError):
            span_cls(start=d(1), end=d(2), extra=1)


class TestStepSpan:
    def test_valid_and_single_day(self):
        span_cls = _schema("StepSpan")
        span = span_cls(date=d(1), through=d(5))
        assert (span.date, span.through) == (d(1), d(5))
        assert span_cls(date=d(3), through=d(3)).through == d(3)

    def test_through_before_date_is_refused(self):
        with pytest.raises(ValidationError):
            _schema("StepSpan")(date=d(5), through=d(4))

    def test_is_strict(self):
        span_cls = _schema("StepSpan")
        assert issubclass(span_cls, StrictModel)
        with pytest.raises(ValidationError):
            span_cls(date=d(1), through=d(2), extra=1)

    def test_a_subclass_point_validates_and_dumps_date_and_through_as_iso(self):
        point_cls = _nav_point_cls()
        point = point_cls.model_validate({"date": "2026-10-23", "through": "2026-10-25", "nav": "10450.00"})
        assert point.date == date(2026, 10, 23) and point.through == date(2026, 10, 25)
        dumped = point.model_dump(mode="json")
        assert dumped["date"] == "2026-10-23"
        assert dumped["through"] == "2026-10-25"
        assert set(dumped) == {"date", "through", "nav", "label"}

    def test_a_subclass_keeps_the_through_validator(self):
        with pytest.raises(ValidationError):
            _nav_point_cls()(date=d(5), through=d(4), nav=D("1"))
