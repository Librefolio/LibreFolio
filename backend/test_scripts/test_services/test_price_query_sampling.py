"""Z-29a (decision N90, contract revised on 19/10): an item of ``POST /assets/prices/query`` may ask its price series
sampled for a compact chart — at the step its own fill fits, at the step it asks, or at the step and on the buckets of
another item of the same request.

Why. On «All» the asset list asks every asset's whole daily history, from the 2000-01-01 sentinel: about 9 787 days each,
so 300 assets are about 2.9 million points and 930 MB of JSON, a batch of 800 000 days about 1.45 GB — an out-of-memory
on a small managed instance. A card draws about 300 points: its compact ``LineChart`` keeps the last point of each ISO
week or calendar month once the daily points pass 1.3 per pixel of its plot (``chooseStaticResolution``;
``timeSeriesAggregation.ts``, ``mapDateToBucket`` and ``aggregateLineSeries``). Z-29a lets the backend send that sample,
and the series a comparison on the card needs on the same buckets, reading each asset once. The contract pinned here
(N90, revised on 19/10: Q-Z29-1's bounds, the developer's «one read per asset», ``sample_like`` by key):

1. ``FAPriceQueryItem`` gains four optional fields, None by default. ``key``: 1 to 64 characters of ``[A-Za-z0-9_.:-]``,
   a pattern the JSON schema carries. ``max_points``: an integer from 1 to 10 000. ``resolution``: a
   ``SampleResolution``, the step asked. ``sample_like``: the ``key`` of another item of the request, the same pattern.
   At most one of ``max_points``, ``resolution`` and ``sample_like``: a model validator's ``ValueError`` whose message
   names the three. With any of them, non-empty ``annotation_requests`` or ``include_events=True`` are refused, a
   ``ValueError`` naming that field and the one refused; ``signals`` (since lot Z-29s-a, point 15: refused before it),
   ``target_currency`` and ``include_price`` stay allowed.
2. ``FAPriceQueryResult`` gains ``resolution: SampleResolution = "daily"``, always present, the step of its ``prices``;
   and ``sample_bounds: Optional[FAPriceSampleBounds] = None``, present if and only if that step is weekly or monthly.
   ``FAPriceSampleBounds`` is a strict model of two required ``FAPricePoint``, ``first`` and ``last``. In the JSON schema
   both are optional properties, as ``prices`` and ``events``. ``FAPricePoint`` as it is.
3. ``backend/app/services/assets/price_sampling.py``, pure: ``SampleResolution``, ``Literal["daily", "weekly",
   "monthly"]``; ``bucket_of(day, resolution)``, the first and last day of the day's bucket (the day; its ISO week,
   Monday to Sunday; its calendar month); ``fill_counts(first, end)``, the days, ISO weeks and calendar months a daily
   fill from ``first`` to ``end`` (both included) touches; ``choose_resolution(first, end, max_points)``: daily if the
   days fit in ``max_points``, else weekly if the weeks do, else monthly — the floor, which may pass it;
   ``sample_dates(first, end, resolution)``: daily, every day; weekly or monthly, the last day of each bucket from
   ``first``'s to ``end``'s, the last one cut at ``end`` — ``first`` only when it closes its bucket or is ``end``. And
   the refusal of a wrong reference: ``SampleReferenceError``, an ``Exception`` with ``index`` (the position of the item
   at fault), ``key`` (that item's own ``key``, or None) and ``reason`` (``unknown_key``, ``duplicate_key``,
   ``chained``, ``range_mismatch``); ``sample_reference_detail(error)``, ``{"code": "sample_reference", "reason",
   "item": index, "key", "message"}``; ``resolve_sample_references(items)``, by the position of each item with a
   ``sample_like`` the position of the item it names, or ``SampleReferenceError`` at the first item at fault (point 8).
4. The fill's first day F, per item, once X-R55 has cut the end at ``latest_range_end()``: the range's start when a row
   of the asset precedes it (the seed), else the asset's first row in the range; neither: nothing to fill — no point,
   ``resolution`` daily, no bounds, whatever the item asks.
5. The step: with ``max_points``, ``choose_resolution(F, end, max_points)`` on the asset's own fill; with
   ``resolution``, the one asked, whatever the counts; with neither, daily. Daily: the answer is exactly the one without
   the fields, no bounds.
6. Weekly or monthly: ``prices`` are the points of ``sample_dates(F, end, step)``, each equal, as JSON, to the point the
   daily answer (the same item without the fields) has on that date — the last stored row on or before it, the seed
   included, ``backward_fill_info`` as the fill gives it; ``sample_bounds.first`` is the daily answer's point on F,
   ``sample_bounds.last`` its point on the cut end, which is also the last of ``prices``.
7. ``sample_like`` K names C, the item of the request whose ``key`` is K. The item T takes C's step, the one C's answer
   says (daily included: then no bounds); T starts on F_T' = max(F_C, F_T), F_T its own fill's first day; its prices are
   ``sample_dates(F_T', end, step)`` on its own daily fill — C's bucket dates, from F_T''s bucket on — and
   ``sample_bounds.first`` its daily point on F_T'. A C with nothing to fill lends its ``max_points`` or its
   ``resolution`` (daily with neither) and T is sampled by itself. C answers as it does alone; its
   ``include_price=False`` (the settings dialog sends the card so) does not change T's answer.
8. The references are the request's, checked before any read: ``get_prices_bulk`` raises ``SampleReferenceError`` for a
   ``sample_like`` that names no item's key (``unknown_key``), a key two items carry (``duplicate_key``, the second), a
   ``sample_like`` naming an item that has one itself, itself included (``chained``), or an item with another
   ``date_range`` (``range_mismatch``: compared before the ceiling cut, an absent ``end`` read as the start,
   ``DateRangeModel``'s single day); ``index`` is the item's position in the request as sent, items after the ceiling
   included. The route answers 422 with ``detail == sample_reference_detail(error)``.
9. ``target_currency``: each sampled point and bound equals the daily answer's converted point on its date (the
   conversion runs per point). ``include_price=False``: no point, as today — with a sampling field, a placeholder
   (point 14).
10. The day budget, ``MAX_BULK_ITEM_DAYS`` (read by name in ``price_query``, lowered here through that module as
    ``test_bulk_limits.py`` does): a weekly or monthly item counts its points plus its two bounds, a daily one its fill
    days, as today; a placeholder nothing (point 14). The budget is checked before the bucket rows are read: a request
    refused for its sampled points has read, through the ORM, at most 2 ``PriceHistory`` rows of an asset it only
    samples.
11. What a sample costs. A request of weekly and monthly items never builds the daily fill
    (``PriceQueryOperations._build_backward_filled_series``) and reads at most (buckets + 2) rows of an asset sampled
    on a card. One read per asset: an asset a daily item of the request reads whole, on the same range, serves its
    sampled items from those rows, and no bucket statement names it; the assets read only sampled are read by one bucket
    statement per (range, step), all of that group in it. Rows are counted by a ``load`` listener on ``PriceHistory``,
    statements by a ``before_cursor_execute`` listener on the engine, both registered and removed here. A bucket
    statement names ``price_history`` and groups or partitions by two terms or more, the asset and the bucket
    (``_is_bucket_statement``); it reads an asset when the asset's id is one of its parameters (``_names_asset``) — the
    assets of ``world`` carry ids no date, format or bound of a price statement can be.
12. The request's order is kept with daily, sampled, asked, following and after-the-ceiling items mixed (X-R55: empty in
    its place), an asset asked daily and sampled, one sampled twice.
13. ``frontend/src/lib/components/charts/__tests__/compactDensityCases.json``, the case table generated with the chart's
    own float rule (``{"threshold", "cases": [{note, first, end, plot_width_px, days, weeks, max_points, resolution}]}``),
    ties the backend's rule to the chart's: for every case ``fill_counts`` gives its days and weeks and
    ``choose_resolution`` its step. Lot Z-29b adds the Vitest side over the same file.
14. A placeholder (lot Z-29a-f, X's review of Z-29a v3): an item with ``max_points``, ``resolution`` or ``sample_like``
    and ``include_price=False`` — the comparison dialog (Z-29d) sends the card so, only to give its step to its target.
    Its plan stays (``_plan_samples``: the seed and the first row in the range, one probe each), and nothing more of its
    asset is read on its account, whatever its step — weekly, monthly, or daily when its fill's days fit in
    ``max_points`` or ``resolution`` asks it: no bucket statement names it, and the day-by-day read of
    ``get_prices_bulk`` — its one ``SELECT … FROM price_history WHERE price_history.asset_id IN (…)``,
    ``_is_daily_load`` — does not list it; alone, that read does not run. It counts nothing against the day budget. Its
    answer: its plan's step in ``resolution`` (daily for a daily one), no point, no bounds, no error. A target follows
    it from the later first day as it follows a card sent with prices (point 7), counting its own points and bounds
    only. The description of ``FAPriceQueryResult.sample_bounds`` says None «without prices» too. An item with
    ``include_price=False`` and no sampling field is read and counted as before: nothing new is pinned about it.
15. Signals on a sample (lot Z-29s-a, contract of 20/10 on 5bbadda95; the developer's Q-Z29-2 of 19/10): an item with
    ``signals`` and ``max_points``, ``resolution`` or ``sample_like`` is valid. It is read, computed and counted day by
    day exactly as the same item without the sampling field — its fill with the signals' warm-up, its day budget the
    fill's days —: never a bucket read, never a placeholder, even with ``include_price=False`` (its signals need the
    rows). Its plan (points 5 and 7, unchanged) gives the step and the dates. Weekly or monthly: ``prices``,
    ``sample_bounds`` and ``resolution`` are those of the same item without signals; each series of each signal result
    is ``aggregation.sample_signal_series(the daily series, its output's aggregation_profile, the step, the plan's
    dates)`` — each point on one of those dates, the point the profile picks in its bucket (the last, the earliest
    smallest, a band's envelope), a gap marker aside —, the result otherwise the daily one's. ``include_price=False``:
    no point, no bounds, the step said, the signals reduced. Daily: the answer without the sampling field. A follower
    (``sample_like``) is reduced on its own plan's dates, from the later first day: its signal points before that day's
    bucket are dropped. The descriptions say it: ``max_points`` no longer «not with signals», ``FAPriceQueryResult``'s
    ``signals`` and ``resolution`` name the ``aggregation_profile``. Real plugins run on the private file: EMA, BOLLINGER
    (a band), MACD (its histogram a bar), RISK_DRAWDOWN (an area, min_with_range) and ASSET_CALENDAR_ROLLING_RETURN (its
    points with a provenance), mostly on WAVE (``signal_world``), an asset of this block whose closes go up and down.

The expectations are computed apart from the module under test: a day-by-day walk (``_ref_*``) for the buckets, the
counts, the step and the sampled dates; the daily answer of the same item, without the fields, for the points.

Isolation: PURE — no lane database, no server, no network. The price queries run on a private SQLite file under
``tmp_path`` built by ``create_all`` (``world``), the X-R55 ceiling frozen in ``price_query`` (``frozen_ceiling``); the
rates of the conversion case are rows of that file, read by the real ``convert_bulk``; the route is called as a function
on a session of that file, as ``test_bulk_limits.py`` calls it. The signals of point 15 compute in-process, the market
holiday table replaced in ``price_query`` by an empty one (no row of the file is a weekend or holiday repeat).

Red before Z-29a (HEAD 14247474e), each for the reason its docstring gives ("Red before Z-29a"): PQS-M01…M08 and PQS-T02
(``price_sampling`` does not exist); PQS-S01…S04 and S07…S13 (``key``, ``max_points``, ``resolution`` and
``sample_like`` are refused as extra fields and absent from the JSON schema); PQS-S05 and S06 (``FAPriceQueryResult``
has no ``resolution`` nor ``sample_bounds``, and there is no ``FAPriceSampleBounds``); PQS-Q01…Q23 (an item with one of
the four fields cannot be built: an extra field). Green then, written green: PQS-T01 (the case table is the chart's own
rule: it pins the table, not the code). Red before the cure that reads an absent ``end`` as the start, written red:
PQS-M08's first two cases, one day with its ``end`` and without it (compared as sent: ``range_mismatch``); its control
is green then, by construction.

Red before Z-29a-f (on Z-29a v3), each for the reason its docstring gives ("Red before Z-29a-f"): PQS-Q24 and Q25 (a
placeholder's asset is named by a bucket statement or listed by the day-by-day read, more than 2 of its rows loaded);
PQS-Q26, Q27 and Q28 (its points and bounds, or its fill days, are counted: refused under 0 alone, under the exact count
of the items beside it); PQS-S14 (the description of ``sample_bounds`` says None for a daily series only). Green then
and after, kept: PQS-Q08 and PQS-Q18's last case, the answers of a placeholder and of the target it leads.

Red before Z-29s-a (HEAD 5bbadda95), each for the reason its docstring gives ("Red before Z-29s-a"): PQS-SG09
(``validate_sampling`` refuses signals with a sampling field); PQS-SG01…SG08 (an item with signals and a sampling field
cannot be built, the same refusal — met after the premises, which hold on the daily answers of today); PQS-SG10 (the
descriptions still say «not with signals» and do not name the ``aggregation_profile``). PQS-S03, updated by Z-29s-a (its
signals case is gone: signals are taken, PQS-SG09), is green then and after: annotations and events stay refused.
"""

from __future__ import annotations

import collections
import contextlib
import dataclasses
import importlib
import json
import math
import re
import typing
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import pytest_asyncio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import event, insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1.assets import prices as price_routes
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetType, FxRate, PriceHistory
from backend.app.schemas import prices as price_schemas
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.prices import FAPricePoint, FAPriceQueryItem, FAPriceQueryResult
from backend.app.schemas.signals import SignalAggregationProfile, SignalBandSeries, SignalBarSeries, SignalCalendarReturnValuePoint, SignalResult, _validate_series_alignment
from backend.app.services.assets import price_query
from backend.app.services.assets.price_query import PriceQueryOperations
from backend.app.services.signals import aggregation as signal_aggregation
from backend.app.services.signals.registry import SignalPluginRegistry
from backend.app.utils.date_range_limits import BulkTooManyDaysError
from backend.app.utils.datetime_utils import utcnow

SAMPLING_MODULE = "backend.app.services.assets.price_sampling"
#: The case table shared with the chart, read from the repository (N90, point 13).
CASE_TABLE = Path(__file__).resolve().parents[3] / "frontend/src/lib/components/charts/__tests__/compactDensityCases.json"
CHART_DENSITY_THRESHOLD = 1.3  # LineChart.svelte's COMPACT_DENSITY_THRESHOLD, written here and not read from the table

#: The contract's names and bounds (N90, revised 19/10), written here and not read from the code under test.
MAX_POINTS_BOUNDS = (1, 10_000)
SAMPLE_RESOLUTIONS = ("daily", "weekly", "monthly")
SAMPLE_FIELDS = ("max_points", "resolution", "sample_like")  # at most one of them per item
REFERENCE_DETAIL_KEYS = {"code", "reason", "item", "key", "message"}
#: Strings a ``key`` or a ``sample_like`` takes (1 to 64 of A-Z a-z 0-9 _ . : -) and refuses.
KEYS_ACCEPTED = ("a", "asset:42", "Az09_.:-", "k" * 64)
KEYS_REFUSED = ("", "k" * 65, "asset 42", "àsset", "asset/42", "€")
#: A value of each sampling field, valid alone.
SAMPLING_VALUES = {"max_points": 377, "resolution": "weekly", "sample_like": "card"}

FROZEN_TODAY = date(2026, 10, 16)  # a Friday: the last stored row of every history
CEILING = FROZEN_TODAY + timedelta(days=1)  # latest_range_end(), frozen: Saturday 2026-10-17, the case table's end
ALL_START = date(2000, 1, 1)  # the asset list's «All»: the 2000-01-01 sentinel, a Saturday
FAR_END = date(2099, 12, 31)  # an end past the ceiling: X-R55 cuts it to CEILING
CARD = 377  # the most points a 290 px compact plot takes, 1.3 a pixel (the case table's first cases)
WIDE = 1534  # the same for a 1 180.25 px plot: «All» fits weekly there
FETCHED_AT = utcnow()

OLD_GAP_MONTH = (date(2010, 3, 1), date(2010, 3, 31))  # a whole calendar month without a row
OLD_GAP_WEEK = (date(2015, 6, 8), date(2015, 6, 14))  # a whole ISO week without a row
YOUNG_GAP_WEEK = (date(2023, 1, 2), date(2023, 1, 8))
FX_FIRST = date(2014, 12, 1)
FX_GAP_MONTH = (date(2022, 8, 1), date(2022, 8, 31))  # no EUR/USD rate for a month

#: The assets of ``world`` with a history: weekday closes from the first day to FROZEN_TODAY, less the gaps; the base of
#: their closes. OLD has rows before «All» (its fill is seeded), YOUNG starts on Monday 2020-03-02, RECENT on Monday
#: 2026-01-05; EMPTY has none.
_HISTORIES = {
    "old": (date(1999, 12, 1), (OLD_GAP_MONTH, OLD_GAP_WEEK), 100),
    "young": (date(2020, 3, 2), (YOUNG_GAP_WEEK,), 200),
    "recent": (date(2026, 1, 5), (), 300),
}
#: Their ids, chosen: a statement names an asset when its id is one of the statement's parameters (point 11), and no
#: date, format, step or bound of a price statement is one of these.
_ASSET_IDS = {"old": 9101, "young": 9202, "recent": 9303, "empty": 9404}

SMA3 = {"instance_id": "sma3", "signal_code": "SMA", "params": {"period": 3}}
CLOSE_CROSSES_100 = {"kind": "threshold_crossing", "key": "close-crosses-100", "attach_to_instance_id": "sma3", "source": {"kind": "price"}, "threshold": 100.0}


# =============================================================================
# THE REFERENCE: THE CALENDAR, WALKED ONE DAY AT A TIME
# =============================================================================


def _days(first: date, last: date) -> list[date]:
    """Every day from ``first`` to ``last``, both included."""
    return [first + timedelta(days=n) for n in range((last - first).days + 1)]


def _ref_bucket(day: date, step: str) -> tuple[date, date]:
    """The bucket of ``day``: the day itself; Monday to Sunday of its ISO week; the first to the last day of its month."""
    if step == "weekly":
        monday = day - timedelta(days=day.isoweekday() - 1)
        return monday, monday + timedelta(days=6)
    if step == "monthly":
        first = day.replace(day=1)
        return first, (first + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    return day, day


def _ref_counts(first: date, end: date) -> tuple[int, int, int]:
    """The days, ISO weeks and calendar months of the daily fill from ``first`` to ``end``, counted day by day."""
    days = _days(first, end)
    return len(days), len({_ref_bucket(day, "weekly") for day in days}), len({_ref_bucket(day, "monthly") for day in days})


def _step_for(counts: tuple[int, int, int], max_points: int) -> str:
    """The step of the contract for a fill of these counts: the finest whose count fits in ``max_points``, monthly when
    none does."""
    days, weeks, _months = counts
    if days <= max_points:
        return "daily"
    return "weekly" if weeks <= max_points else "monthly"


def _ref_step(first: date, end: date, max_points: int) -> str:
    """The step of the contract for the fill from ``first`` to ``end``."""
    return _step_for(_ref_counts(first, end), max_points)


def _ref_sample_dates(first: date, end: date, step: str) -> list[date]:
    """The sampled dates, walking the fill: every day that ends its bucket (the next day lies in another) or ends the
    fill — ``first`` among them only when it closes its bucket or is ``end``. Daily: every day."""
    days = _days(first, end)
    if step == "daily":
        return days
    return [day for day in days if day == end or _ref_bucket(day, step) != _ref_bucket(day + timedelta(days=1), step)]


def _ref_buckets(first: date, end: date, step: str) -> int:
    """How many weeks or months the fill from ``first`` to ``end`` touches."""
    _days_count, weeks, months = _ref_counts(first, end)
    return weeks if step == "weekly" else months


def _sampling() -> ModuleType:
    """``price_sampling``, imported at the call: while it is missing, the test asking it fails saying so, and the other
    tests of the file still run."""
    try:
        return importlib.import_module(SAMPLING_MODULE)
    except ModuleNotFoundError as missing:
        if missing.name != SAMPLING_MODULE:
            raise
    pytest.fail(f"{SAMPLING_MODULE} does not exist: Z-29a's pure module (SampleResolution, bucket_of, fill_counts, choose_resolution, sample_dates, SampleReferenceError, sample_reference_detail)")


def _bounds_model() -> type:
    """``FAPriceSampleBounds``, read from the schema module at the call: while it is missing, the test asking it fails
    saying so."""
    model = getattr(price_schemas, "FAPriceSampleBounds", None)
    if model is None:
        pytest.fail("backend.app.schemas.prices has no FAPriceSampleBounds: Z-29a's bounds of a weekly or monthly answer (first, last)")
    return model


# =============================================================================
# PQS-M — THE PURE MODULE
# =============================================================================


def test_pqs_m01_sample_resolution_names_the_three_steps():
    """PQS-M01: ``SampleResolution`` is the ``Literal`` of the three steps, daily, weekly and monthly.

    Red before Z-29a: ``price_sampling`` does not exist.
    """
    resolution = _sampling().SampleResolution
    resolution = getattr(resolution, "__value__", resolution)  # a ``type`` alias holds its Literal there
    assert typing.get_origin(resolution) is typing.Literal, f"SampleResolution is {resolution!r}, not a Literal"
    assert set(typing.get_args(resolution)) == set(SAMPLE_RESOLUTIONS)


_BUCKET_CASES = [
    pytest.param(date(2026, 10, 18), "weekly", (date(2026, 10, 12), date(2026, 10, 18)), id="weekly-a-sunday-is-in-its-monday-week"),
    pytest.param(date(2026, 10, 12), "weekly", (date(2026, 10, 12), date(2026, 10, 18)), id="weekly-a-monday-starts-its-own"),
    pytest.param(date(2026, 10, 14), "weekly", (date(2026, 10, 12), date(2026, 10, 18)), id="weekly-a-wednesday"),
    pytest.param(date(2021, 1, 1), "weekly", (date(2020, 12, 28), date(2021, 1, 3)), id="weekly-across-new-year"),
    pytest.param(ALL_START, "weekly", (date(1999, 12, 27), date(2000, 1, 2)), id="weekly-the-all-sentinel-a-saturday"),
    pytest.param(date(2024, 2, 10), "monthly", (date(2024, 2, 1), date(2024, 2, 29)), id="monthly-february-of-a-leap-year"),
    pytest.param(date(2023, 2, 28), "monthly", (date(2023, 2, 1), date(2023, 2, 28)), id="monthly-february-of-a-common-year"),
    pytest.param(date(2000, 2, 29), "monthly", (date(2000, 2, 1), date(2000, 2, 29)), id="monthly-february-2000-a-leap-century"),
    pytest.param(date(1900, 2, 15), "monthly", (date(1900, 2, 1), date(1900, 2, 28)), id="monthly-february-1900-a-common-century"),
    pytest.param(date(2025, 12, 1), "monthly", (date(2025, 12, 1), date(2025, 12, 31)), id="monthly-december-from-its-first-day"),
    pytest.param(date(2025, 12, 31), "monthly", (date(2025, 12, 1), date(2025, 12, 31)), id="monthly-december-from-its-last-day"),
    pytest.param(date(2024, 2, 29), "daily", (date(2024, 2, 29), date(2024, 2, 29)), id="daily-the-day-itself"),
]


@pytest.mark.parametrize(("day", "resolution", "expected"), _BUCKET_CASES)
def test_pqs_m02_bucket_of(day, resolution, expected):
    """PQS-M02: ``bucket_of`` gives the first and last day of the bucket: the day itself; Monday to Sunday of its ISO
    week (a Sunday belongs to the Monday six days before, a Monday starts its own, a week may straddle two years); the
    1st to the last day of its month (February of a leap year, 2000 a leap century, 1900 not; December).

    Red before Z-29a: ``price_sampling`` does not exist.
    """
    assert tuple(_sampling().bucket_of(day, resolution)) == expected


_COUNT_CASES = [
    pytest.param(date(2026, 10, 12), date(2026, 10, 18), (7, 1, 1), id="monday-to-sunday-one-iso-week"),
    pytest.param(date(2026, 10, 18), date(2026, 10, 19), (2, 2, 1), id="sunday-to-monday-two-iso-weeks"),
    pytest.param(date(2024, 2, 29), date(2024, 2, 29), (1, 1, 1), id="first-is-end"),
    pytest.param(date(2025, 12, 31), date(2026, 1, 1), (2, 1, 2), id="one-iso-week-two-months"),
    pytest.param(date(2024, 1, 31), date(2024, 3, 1), (31, 5, 3), id="across-a-leap-february"),
    pytest.param(ALL_START, CEILING, (9787, 1399, 322), id="all-to-the-case-table-end"),
]


@pytest.mark.parametrize(("first", "end", "expected"), _COUNT_CASES)
def test_pqs_m03_fill_counts(first, end, expected):
    """PQS-M03: ``fill_counts(first, end)`` is the days, the ISO weeks and the calendar months a daily fill from
    ``first`` to ``end``, both included, touches — «All» to Saturday 2026-10-17: 9 787 days, 1 399 weeks, 322 months.

    Red before Z-29a: ``price_sampling`` does not exist.
    """
    assert tuple(_sampling().fill_counts(first, end)) == expected


_STEP_CASES = [
    pytest.param(date(2026, 10, 12), date(2026, 10, 18), 7, "daily", id="seven-days-in-seven-points"),
    pytest.param(date(2026, 10, 12), date(2026, 10, 18), 6, "weekly", id="one-point-short-weekly"),
    pytest.param(date(2026, 10, 12), date(2026, 10, 18), 1, "weekly", id="one-week-in-one-point"),
    pytest.param(date(2026, 10, 18), date(2026, 10, 19), 1, "monthly", id="two-weeks-in-one-point-monthly"),
    pytest.param(ALL_START, CEILING, 100, "monthly", id="the-floor-322-months-in-100-points"),
    pytest.param(date(2024, 2, 29), date(2024, 2, 29), 1, "daily", id="first-is-end"),
]


@pytest.mark.parametrize(("first", "end", "max_points", "expected"), _STEP_CASES)
def test_pqs_m04_choose_resolution(first, end, max_points, expected):
    """PQS-M04: ``choose_resolution`` is daily when the days fit in ``max_points`` (equal included), else weekly when the
    weeks do, else monthly — the floor, even when the months do not fit either.

    Red before Z-29a: ``price_sampling`` does not exist.
    """
    assert _sampling().choose_resolution(first, end, max_points) == expected


_SAMPLE_CASES = [
    pytest.param(date(2024, 2, 27), date(2024, 3, 2), "daily", [date(2024, 2, 27), date(2024, 2, 28), date(2024, 2, 29), date(2024, 3, 1), date(2024, 3, 2)], id="daily-every-day"),
    pytest.param(date(2026, 9, 30), CEILING, "weekly", [date(2026, 10, 4), date(2026, 10, 11), CEILING], id="weekly-from-a-wednesday-its-sunday-first-the-last-week-cut"),
    pytest.param(date(2026, 10, 4), CEILING, "weekly", [date(2026, 10, 4), date(2026, 10, 11), CEILING], id="weekly-a-sunday-first-closes-its-week"),
    pytest.param(date(2026, 10, 5), date(2026, 10, 18), "weekly", [date(2026, 10, 11), date(2026, 10, 18)], id="weekly-monday-to-sunday-the-monday-left-out"),
    pytest.param(date(2020, 12, 30), date(2021, 1, 12), "weekly", [date(2021, 1, 3), date(2021, 1, 10), date(2021, 1, 12)], id="weekly-across-new-year"),
    pytest.param(date(2026, 10, 13), date(2026, 10, 15), "weekly", [date(2026, 10, 15)], id="weekly-within-one-week-the-end-alone"),
    pytest.param(CEILING, CEILING, "weekly", [CEILING], id="weekly-first-is-end"),
    pytest.param(date(2026, 10, 18), date(2026, 10, 18), "weekly", [date(2026, 10, 18)], id="weekly-first-is-end-a-sunday"),
    pytest.param(date(2023, 12, 15), date(2024, 3, 10), "monthly", [date(2023, 12, 31), date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 10)], id="monthly-december-and-a-leap-february"),
    pytest.param(date(2024, 2, 29), date(2024, 4, 30), "monthly", [date(2024, 2, 29), date(2024, 3, 31), date(2024, 4, 30)], id="monthly-first-closes-its-month"),
    pytest.param(date(2023, 1, 31), date(2023, 3, 1), "monthly", [date(2023, 1, 31), date(2023, 2, 28), date(2023, 3, 1)], id="monthly-a-common-february"),
    pytest.param(date(2025, 3, 1), date(2025, 5, 15), "monthly", [date(2025, 3, 31), date(2025, 4, 30), date(2025, 5, 15)], id="monthly-from-a-first-of-month-left-out"),
    pytest.param(date(2025, 2, 3), date(2025, 2, 20), "monthly", [date(2025, 2, 20)], id="monthly-within-one-month-the-end-alone"),
    pytest.param(date(2024, 12, 31), date(2024, 12, 31), "monthly", [date(2024, 12, 31)], id="monthly-first-is-end"),
]


@pytest.mark.parametrize(("first", "end", "resolution", "expected"), _SAMPLE_CASES)
def test_pqs_m05_sample_dates(first, end, resolution, expected):
    """PQS-M05: ``sample_dates`` — daily, every day; weekly or monthly, the last day of each bucket from ``first``'s to
    ``end``'s, the last one cut at ``end``: ``first`` is a sampled date only when it closes its bucket (a Sunday, a
    month's last day) or is ``end``. A fill within one bucket is its end alone; from a Monday or a 1st, the first date is
    that bucket's last day.

    Red before Z-29a: ``price_sampling`` does not exist. Red too against the v2 draft (19/10), which put ``first`` in
    front of every sample.
    """
    assert list(_sampling().sample_dates(first, end, resolution)) == expected


#: Two windows of fifteen first days — every weekday twice, January's end, a leap February, a December and the ISO week
#: that straddles 2025 and 2026 — each with every end up to nine weeks on.
_SWEEP_FIRSTS = [*_days(date(2024, 1, 25), date(2024, 2, 8)), *_days(date(2025, 12, 24), date(2026, 1, 7))]
_SWEEP_SPAN = 62
_SWEEP_MAX_POINTS = (1, 2, 5, 9, 10, 31, 63)


def _sweep_mismatches(sampling: ModuleType, first: date) -> list[str]:
    """What the module says differently from the reference for one first day, every end of the sweep."""
    found = []
    for end in _days(first, first + timedelta(days=_SWEEP_SPAN)):
        counts = _ref_counts(first, end)
        if tuple(sampling.fill_counts(first, end)) != counts:
            found.append(f"fill_counts({first}, {end}) = {tuple(sampling.fill_counts(first, end))}, not {counts}")
        for step in SAMPLE_RESOLUTIONS:
            if list(sampling.sample_dates(first, end, step)) != _ref_sample_dates(first, end, step):
                found.append(f"sample_dates({first}, {end}, {step!r}) = {list(sampling.sample_dates(first, end, step))}")
        found.extend(f"choose_resolution({first}, {end}, {cap}) = {sampling.choose_resolution(first, end, cap)!r}" for cap in _SWEEP_MAX_POINTS if sampling.choose_resolution(first, end, cap) != _step_for(counts, cap))
    return found


def test_pqs_m06_the_module_is_the_day_walk():
    """PQS-M06: over 30 first days and every end up to 62 days on (1 890 fills), ``fill_counts``, ``sample_dates`` for
    the three steps and ``choose_resolution`` for seven caps agree with the reference, which walks the calendar one day
    at a time and knows nothing of the module's arithmetic.

    Red before Z-29a: ``price_sampling`` does not exist.
    """
    sampling = _sampling()
    mismatches = [found for first in _SWEEP_FIRSTS for found in _sweep_mismatches(sampling, first)]
    assert not mismatches, f"{len(mismatches)} disagreements with the day walk, the first: {mismatches[:3]}"


def test_pqs_m07_the_module_names_a_wrong_reference():
    """PQS-M07: the module holds the request's refusal of a wrong ``sample_like`` reference: ``SampleReferenceError``,
    an ``Exception``, and ``sample_reference_detail``, the function the route builds its 422 ``detail`` with. What they
    carry is pinned on the errors ``get_prices_bulk`` raises (PQS-Q20) and on the route's answer (PQS-Q21), not on an
    error built here: the constructor is the implementation's.

    Red before Z-29a: ``price_sampling`` does not exist.
    """
    sampling = _sampling()
    error_type = getattr(sampling, "SampleReferenceError", None)
    assert isinstance(error_type, type) and issubclass(error_type, Exception), f"SampleReferenceError is {error_type!r}, not an exception class"
    assert callable(getattr(sampling, "sample_reference_detail", None)), f"{SAMPLING_MODULE} has no sample_reference_detail"


#: One day — any: the function compares ranges, it reads no row — as ``DateRangeModel``'s keyword arguments: with its
#: ``end``, without it (left out, as a request leaves it out: the single day), and to the next day.
_ONE_DAY = date(2026, 10, 14)
_WITH_END = {"start": _ONE_DAY, "end": _ONE_DAY}
_WITHOUT_END = {"start": _ONE_DAY}
_TO_THE_NEXT_DAY = {"start": _ONE_DAY, "end": _ONE_DAY + timedelta(days=1)}
#: A card's range and its target's, and what ``resolve_sample_references`` makes of the two: the target's position
#: mapped to the card's, or the refusal as (index, key, reason).
_ABSENT_END_CASES = [
    pytest.param(_WITH_END, _WITHOUT_END, {1: 0}, id="the-target-without-end"),
    pytest.param(_WITHOUT_END, _WITH_END, {1: 0}, id="the-card-without-end"),
    pytest.param(_WITHOUT_END, _TO_THE_NEXT_DAY, (1, None, "range_mismatch"), id="control-the-target-to-the-next-day-refused"),
]


@pytest.mark.parametrize(("card_range", "target_range", "expected"), _ABSENT_END_CASES)
def test_pqs_m08_an_absent_end_is_the_start(card_range, target_range, expected):
    """PQS-M08: ``resolve_sample_references`` reads an absent ``date_range.end`` as the start — ``DateRangeModel``'s
    single day, the range ``get_prices_bulk`` plans an item on, ``(start, end or start)``. A card on one day with its
    ``end`` and a target on that day without it, or the reverse, cover the same range: the target's position maps to
    the card's, ``{1: 0}``. The control: a card on one day without its ``end`` and a target from that day to the next
    cover two ranges, ``range_mismatch`` on the target (index 1, no key of its own). Real ``FAPriceQueryItem`` objects
    on assets 1 and 2 (the function reads ``key``, ``sample_like`` and ``date_range`` only), an absent ``end`` left out
    as a request leaves it out; the premise: the model keeps it None. No row and no ceiling: ``get_prices_bulk`` checks
    the references before X-R55 cuts the ranges (point 8).

    Red before Z-29a: ``price_sampling`` does not exist. Red before the cure, the first two cases
    (``range_mismatch``): an absent end is compared as sent. The control is green then, by construction: its two
    ranges differ however an absent end is read.
    """
    sampling = _sampling()
    resolve = getattr(sampling, "resolve_sample_references", None)
    assert callable(resolve), f"{SAMPLING_MODULE} has no resolve_sample_references"
    card = FAPriceQueryItem(asset_id=1, date_range=DateRangeModel(**card_range), key="card", max_points=CARD)
    target = FAPriceQueryItem(asset_id=2, date_range=DateRangeModel(**target_range), sample_like="card")
    assert (card.date_range.end, target.date_range.end) == (card_range.get("end"), target_range.get("end")), f"premise: an end is kept as given, an absent one None; the items hold {card.date_range!r} and {target.date_range!r}"
    try:
        said = resolve([card, target])
    except sampling.SampleReferenceError as refusal:
        said = (refusal.index, refusal.key, refusal.reason)
    assert said == expected, f"card {card_range}, target {target_range}: resolve_sample_references gives {said!r}, not {expected!r} (a mapping: the target follows the card; a tuple: refused, as (index, key, reason))"


# =============================================================================
# PQS-T — THE CASE TABLE SHARED WITH THE CHART
# =============================================================================


def _case_table() -> dict:
    assert CASE_TABLE.is_file(), f"the case table shared with the chart is missing: {CASE_TABLE}"
    return json.loads(CASE_TABLE.read_text(encoding="utf-8"))


def _most_points(width: float, threshold: float) -> int:
    """The most points a plot ``width`` pixels wide takes under the chart's rule: max{c : c / width <= threshold}, in
    doubles, as the chart computes its density."""
    count = math.floor(threshold * width) + 2
    while count > 0 and count / width > threshold:
        count -= 1
    return count


def _chart_step(days: int, weeks: int, width: float, threshold: float) -> str:
    """``chooseStaticResolution``: daily while the daily points are at most ``threshold`` a pixel, else weekly while the
    weekly ones are, else monthly; ``computeDensity`` is 0 for a plot without width."""

    def density(count: int) -> float:
        return 0.0 if width <= 0 else count / width

    if density(days) <= threshold:
        return "daily"
    return "weekly" if density(weeks) <= threshold else "monthly"


def _case_dates(case: dict) -> tuple[date, date]:
    return date.fromisoformat(case["first"]), date.fromisoformat(case["end"])


def test_pqs_t01_the_case_table_is_the_charts_rule():
    """PQS-T01: every case of the shared table is the chart's own rule, in doubles: its days and weeks are those of the
    fill from ``first`` to ``end`` (the day walk), its ``max_points`` the most points its plot width takes at 1.3 a
    pixel, its step the one ``chooseStaticResolution`` draws for those counts on that width.

    It pins the table, not the backend: a case edited by hand fails here, before it fails the backend for a rule it
    never had. Green before Z-29a, written green: the table comes with the change.
    """
    table = _case_table()
    assert table["threshold"] == CHART_DENSITY_THRESHOLD, table["threshold"]
    cases = table["cases"]
    assert cases, "the table has no case"
    assert len({case["note"] for case in cases}) == len(cases), "two cases share a note"
    wrong = []
    for case in cases:
        first, end = _case_dates(case)
        width = case["plot_width_px"]
        seen = (_ref_counts(first, end)[:2], _most_points(width, CHART_DENSITY_THRESHOLD), _chart_step(case["days"], case["weeks"], width, CHART_DENSITY_THRESHOLD))
        if seen != ((case["days"], case["weeks"]), case["max_points"], case["resolution"]):
            wrong.append(f"{case['note']}: the chart's rule gives {seen}")
    assert not wrong, wrong


def test_pqs_t02_the_backend_rule_reproduces_the_case_table():
    """PQS-T02: for every case of the shared table, ``fill_counts(first, end)`` gives its days and weeks and
    ``choose_resolution(first, end, max_points)`` its step: the chart's density rule and the backend's cap agree on every
    edge the table holds — days or weeks equal to ``max_points`` and one more, a fill from a Sunday and from a Monday, a
    fractional width, the floor.

    Red before Z-29a: ``price_sampling`` does not exist.
    """
    sampling = _sampling()
    wrong = []
    for case in _case_table()["cases"]:
        first, end = _case_dates(case)
        counts = tuple(sampling.fill_counts(first, end))[:2]
        step = sampling.choose_resolution(first, end, case["max_points"])
        if (counts, step) != ((case["days"], case["weeks"]), case["resolution"]):
            wrong.append(f"{case['note']}: fill_counts {counts}, choose_resolution {step!r}; the table: {(case['days'], case['weeks'])}, {case['resolution']!r}")
    assert not wrong, wrong


# =============================================================================
# PQS-S — THE REQUEST FIELDS AND THE ANSWER'S
# =============================================================================


def _payload(**extra: Any) -> dict:
    return {"asset_id": 1, "date_range": {"start": ALL_START.isoformat(), "end": CEILING.isoformat()}, **extra}


def _refused(payload: dict) -> list[dict]:
    """The errors ``FAPriceQueryItem`` refuses ``payload`` with; when it accepts it, the test fails saying so."""
    try:
        FAPriceQueryItem.model_validate(payload)
    except ValidationError as refusal:
        return refusal.errors()
    pytest.fail(f"accepted: {payload}")


@pytest.mark.parametrize("max_points", [MAX_POINTS_BOUNDS[0], CARD, MAX_POINTS_BOUNDS[1]])
def test_pqs_s01_max_points_from_1_to_10000(max_points):
    """PQS-S01: ``max_points`` is an optional field, None by default; 1, 377 and 10 000 are accepted, with
    ``target_currency`` and with ``include_price=False`` too.

    Red before Z-29a: the field does not exist, and the item refuses it as an extra one.
    """
    assert "max_points" in FAPriceQueryItem.model_fields, f"FAPriceQueryItem has no max_points: {sorted(FAPriceQueryItem.model_fields)}"
    assert FAPriceQueryItem.model_validate(_payload()).max_points is None
    assert FAPriceQueryItem.model_validate(_payload(max_points=max_points)).max_points == max_points
    item = FAPriceQueryItem.model_validate(_payload(max_points=max_points, target_currency="USD", include_price=False))
    assert (item.max_points, item.target_currency, item.include_price) == (max_points, "USD", False)


@pytest.mark.parametrize(
    ("value", "error_types"),
    [
        pytest.param(0, {"greater_than_equal"}, id="zero"),
        pytest.param(-1, {"greater_than_equal"}, id="negative"),
        pytest.param(10_001, {"less_than_equal"}, id="past-10000"),
        pytest.param(1.5, {"int_from_float", "int_type"}, id="not-an-integer"),
    ],
)
def test_pqs_s02_max_points_outside_the_bounds_refused(value, error_types):
    """PQS-S02: 0, -1, 10 001 and 1.5 are refused on the field itself: at least 1, at most 10 000, an integer.

    Red before Z-29a: refused too, but as an extra field (``extra_forbidden``), whatever the value.
    """
    errors = _refused(_payload(max_points=value))
    assert [(error["type"] in error_types, error["loc"]) for error in errors] == [(True, ("max_points",))], errors


@pytest.mark.parametrize("field", SAMPLE_FIELDS)
@pytest.mark.parametrize(
    ("extra", "refused"),
    [
        pytest.param({"signals": [SMA3], "annotation_requests": [CLOSE_CROSSES_100]}, "annotation_requests", id="signals-and-annotations"),
        pytest.param({"include_events": True}, "include_events", id="include-events"),
    ],
)
def test_pqs_s03_a_sampled_item_refuses_annotations_and_events(field, extra, refused):
    """PQS-S03: with ``max_points``, ``resolution`` or ``sample_like``, signals with annotations, or
    ``include_events=True``, are refused: a value error whose message names the sampling field and the field refused —
    annotations and events need every day. Signals alone are taken since lot Z-29s-a (point 15, PQS-SG09): the backend
    reduces them on the sample. The same item without the sampling field is valid (the control: the refusal is the
    combination's).

    Red before Z-29a: refused, but for the sampling field itself, an extra one. Updated by Z-29s-a, which removed its
    signals case (signals alone, refused until then): green before Z-29s-a and after.
    """
    assert FAPriceQueryItem.model_validate(_payload(**extra)) is not None
    errors = _refused(_payload(**{field: SAMPLING_VALUES[field]}, **extra))
    assert not [error for error in errors if error["type"] == "extra_forbidden"], f"{field} refused as an unknown field: {errors}"
    assert any(error["type"] == "value_error" and field in error["msg"] and refused in error["msg"] for error in errors), errors


def _integer_branch(field_schema: dict) -> dict:
    """The integer schema of an optional integer field: the field itself, or its ``anyOf`` branch of type integer."""
    branches = [branch for branch in field_schema.get("anyOf", [field_schema]) if branch.get("type") == "integer"]
    assert len(branches) == 1, f"not one integer schema: {field_schema}"
    return branches[0]


def test_pqs_s04_json_schema_bounds_max_points():
    """PQS-S04: ``model_json_schema()`` shows ``max_points`` as an optional integer, null allowed, not required, with
    minimum 1 and maximum 10000 — what the OpenAPI document and the generated client read.

    Red before Z-29a: the schema has no ``max_points``.
    """
    schema = FAPriceQueryItem.model_json_schema()
    field_schema = schema["properties"].get("max_points")
    assert field_schema is not None, f"no max_points in the schema: {sorted(schema['properties'])}"
    integer = _integer_branch(field_schema)
    assert (integer.get("minimum"), integer.get("maximum")) == MAX_POINTS_BOUNDS, field_schema
    assert any(branch.get("type") == "null" for branch in field_schema.get("anyOf", [])), f"max_points is not nullable: {field_schema}"
    assert field_schema.get("default") is None, field_schema
    assert "max_points" not in schema.get("required", []), schema.get("required")


def _literal_values(node: dict, definitions: dict) -> list:
    """The values a ``Literal`` property admits, however the JSON schema writes them: ``enum`` or ``const`` on the
    property, ``anyOf``/``oneOf`` of those, or a ``$ref`` (alone, or the one member of an ``allOf``) to a definition that
    holds them — a ``type`` alias is written so. ``definitions``: the schema's ``$defs``."""
    if "$ref" in node:
        name = node["$ref"].rsplit("/", 1)[-1]
        assert name in definitions, f"{node['$ref']} is not a definition of the schema: {sorted(definitions)}"
        return _literal_values(definitions[name], definitions)
    if "enum" in node:
        return list(node["enum"])
    if "const" in node:
        return [node["const"]]
    if len(node.get("allOf", [])) == 1:
        return _literal_values(node["allOf"][0], definitions)
    branches = node.get("anyOf") or node.get("oneOf")
    assert branches, f"no literal values in {node}"
    return [value for branch in branches for value in _literal_values(branch, definitions)]


def _nullable_literal(field_schema: dict, definitions: dict) -> tuple[bool, list]:
    """Whether an optional ``Literal`` property admits null, and the values it admits besides: its ``anyOf`` branches
    split into ``{"type": "null"}`` and the others, read as ``_literal_values`` reads them."""
    branches = field_schema.get("anyOf", [field_schema])
    values = [value for branch in branches if branch.get("type") != "null" for value in _literal_values(branch, definitions)]
    return any(branch.get("type") == "null" for branch in branches), values


def _ref_name(node: dict) -> str | None:
    """The definition a property refers to: its ``$ref``, alone or the one member of an ``allOf``; None without one."""
    if "$ref" in node:
        return node["$ref"].rsplit("/", 1)[-1]
    members = node.get("allOf", [])
    return _ref_name(members[0]) if len(members) == 1 else None


def test_pqs_s05_the_answer_says_its_resolution():
    """PQS-S05: the answer gains two fields and only those: ``FAPriceQueryResult`` has the five fields it had at HEAD
    14247474e plus ``resolution`` and ``sample_bounds`` (PQS-S06). ``resolution`` is ``"daily"`` when not given, typed
    with ``price_sampling``'s ``SampleResolution`` — the very object, which the schema imports. Its JSON schema, in both
    modes (an answer's is the serialization one), shows ``resolution`` optional, not required, as ``prices`` and
    ``events``: its values exactly the three steps, its default ``"daily"`` — an ``enum`` on the property, or behind a
    ``$ref`` for a ``type`` alias. ``FAPricePoint`` keeps its fields: a sampled series and its bounds are the same points.
    A later lot that adds a field updates these lists on purpose.

    Red before Z-29a: ``FAPriceQueryResult`` has no ``resolution``.
    """
    result_fields = set(FAPriceQueryResult.model_fields)
    assert result_fields == {"asset_id", "prices", "events", "errors", "signals", "resolution", "sample_bounds"}, sorted(result_fields)
    assert FAPriceQueryResult(asset_id=1).resolution == "daily"
    for mode in ("validation", "serialization"):
        schema = FAPriceQueryResult.model_json_schema(mode=mode)
        field_schema = schema["properties"]["resolution"]
        assert sorted(_literal_values(field_schema, schema.get("$defs", {}))) == sorted(SAMPLE_RESOLUTIONS), f"{mode}: {field_schema}"
        assert field_schema.get("default") == "daily", f"{mode}: {field_schema}"
        assert "resolution" not in schema.get("required", []), f"{mode}: required {schema.get('required')}"
    annotation = FAPriceQueryResult.model_fields["resolution"].annotation
    assert annotation is _sampling().SampleResolution, f"resolution is typed {annotation!r}, not {SAMPLING_MODULE}.SampleResolution"
    point_fields = {"date", "open", "high", "low", "close", "volume", "currency", "source_plugin_key", "backward_fill_info"}
    point_fields |= {"original_currency", "original_close", "original_open", "original_high", "original_low"}
    assert set(FAPricePoint.model_fields) == point_fields


def test_pqs_s06_the_answer_bounds_a_weekly_or_monthly_sample():
    """PQS-S06: ``FAPriceQueryResult.sample_bounds``, None when not given, holds a ``FAPriceSampleBounds``: a strict model
    (an unknown field refused, ``additionalProperties`` false in its schema) of exactly two ``FAPricePoint``, ``first``
    and ``last``, both required. In the answer's JSON schema, both modes, ``sample_bounds`` is optional and not
    required, null allowed, its other branch a reference to ``FAPriceSampleBounds``, whose ``first`` and ``last`` refer
    to ``FAPricePoint`` and are required — what the OpenAPI document and the generated client read.

    Red before Z-29a: ``FAPriceQueryResult`` has no ``sample_bounds``, and there is no ``FAPriceSampleBounds``.
    """
    assert "sample_bounds" in FAPriceQueryResult.model_fields, f"FAPriceQueryResult has no sample_bounds: {sorted(FAPriceQueryResult.model_fields)}"
    assert FAPriceQueryResult(asset_id=1).sample_bounds is None
    bounds_model = _bounds_model()
    fields = {name: (field.annotation, field.is_required()) for name, field in bounds_model.model_fields.items()}
    assert fields == {"first": (FAPricePoint, True), "last": (FAPricePoint, True)}, fields
    point = FAPricePoint(date=FROZEN_TODAY, close=Decimal("1.5"), currency="EUR")
    assert bounds_model(first=point, last=point).last == point
    with pytest.raises(ValidationError):
        bounds_model.model_validate({"first": point.model_dump(), "last": point.model_dump(), "middle": point.model_dump()})
    for mode in ("validation", "serialization"):
        schema = FAPriceQueryResult.model_json_schema(mode=mode)
        field_schema = schema["properties"]["sample_bounds"]
        branches = field_schema.get("anyOf", [field_schema])
        assert [_ref_name(branch) for branch in branches if _ref_name(branch)] == ["FAPriceSampleBounds"], f"{mode}: {field_schema}"
        assert any(branch.get("type") == "null" for branch in branches), f"{mode}: sample_bounds is not nullable: {field_schema}"
        assert field_schema.get("default") is None and "sample_bounds" not in schema.get("required", []), f"{mode}: {field_schema}, required {schema.get('required')}"
        bounds = schema["$defs"]["FAPriceSampleBounds"]
        assert (sorted(bounds.get("required", [])), bounds.get("additionalProperties")) == (["first", "last"], False), f"{mode}: {bounds}"
        assert {name: _ref_name(node) for name, node in bounds["properties"].items()} == {"first": "FAPricePoint", "last": "FAPricePoint"}, f"{mode}: {bounds}"


def _key_error_types(value: str) -> set[str]:
    """The error types a length or a pattern constraint may refuse ``value`` with: a length one when the length is out of
    bounds, the pattern one in any case."""
    if not value:
        return {"string_too_short", "string_pattern_mismatch"}
    if len(value) > 64:
        return {"string_too_long", "string_pattern_mismatch"}
    return {"string_pattern_mismatch"}


@pytest.mark.parametrize("field", ["key", "sample_like"])
@pytest.mark.parametrize("value", KEYS_ACCEPTED, ids=["one-letter", "asset-colon-id", "every-class", "64-characters"])
def test_pqs_s07_key_and_sample_like_take_the_key_alphabet(field, value):
    """PQS-S07: ``key`` and ``sample_like`` are optional, None by default, and take 1 to 64 characters of ``A-Z a-z 0-9
    _ . : -``: one letter, ``asset:42`` (the asset list's key), one of each class, 64 characters — on an item alone (the
    reference is the request's, PQS-Q20), with ``target_currency`` and ``include_price=False`` too.

    Red before Z-29a: the field does not exist, and the item refuses it as an extra one.
    """
    assert field in FAPriceQueryItem.model_fields, f"FAPriceQueryItem has no {field}: {sorted(FAPriceQueryItem.model_fields)}"
    assert getattr(FAPriceQueryItem.model_validate(_payload()), field) is None
    assert getattr(FAPriceQueryItem.model_validate(_payload(**{field: value})), field) == value
    item = FAPriceQueryItem.model_validate(_payload(**{field: value}, target_currency="USD", include_price=False))
    assert (getattr(item, field), item.target_currency, item.include_price) == (value, "USD", False)


@pytest.mark.parametrize("field", ["key", "sample_like"])
@pytest.mark.parametrize("value", KEYS_REFUSED, ids=["empty", "65-characters", "a-space", "a-letter-outside-ascii", "a-slash", "a-symbol"])
def test_pqs_s08_key_and_sample_like_refuse_other_strings(field, value):
    """PQS-S08: an empty string, 65 characters, a space, a letter outside ASCII, a slash or a symbol are refused on the
    field itself, by its length or by its pattern.

    Red before Z-29a: refused too, but as an extra field (``extra_forbidden``), whatever the value.
    """
    errors = _refused(_payload(**{field: value}))
    assert [(error["type"] in _key_error_types(value), error["loc"]) for error in errors] == [(True, (field,))], errors


def _string_branch(field_schema: dict) -> dict:
    """The string schema of an optional string field: the field itself, or its ``anyOf`` branch of type string."""
    branches = [branch for branch in field_schema.get("anyOf", [field_schema]) if branch.get("type") == "string"]
    assert len(branches) == 1, f"not one string schema: {field_schema}"
    return branches[0]


def _schema_admits(string_schema: dict, value: str) -> bool:
    """Whether a client that follows the JSON schema sends ``value``: its ``minLength`` and ``maxLength``, and its
    ``pattern``, searched as JSON Schema does (not anchored unless the pattern anchors itself)."""
    if not string_schema.get("minLength", 0) <= len(value) <= string_schema.get("maxLength", len(value)):
        return False
    pattern = string_schema.get("pattern")
    return pattern is None or re.search(pattern, value) is not None


@pytest.mark.parametrize("field", ["key", "sample_like"])
def test_pqs_s09_json_schema_constrains_key_and_sample_like(field):
    """PQS-S09: ``model_json_schema()`` shows ``key`` and ``sample_like`` as optional strings, null allowed, not required,
    with a ``pattern``; read with their ``minLength`` and ``maxLength`` they admit every string PQS-S07 takes and none
    PQS-S08 refuses — the generated client refuses what the backend does, before sending it.

    Red before Z-29a: the schema has neither field.
    """
    schema = FAPriceQueryItem.model_json_schema()
    field_schema = schema["properties"].get(field)
    assert field_schema is not None, f"no {field} in the schema: {sorted(schema['properties'])}"
    string = _string_branch(field_schema)
    assert "pattern" in string, f"{field}: no pattern in the schema: {string}"
    wrong = [value for value in KEYS_ACCEPTED if not _schema_admits(string, value)] + [value for value in KEYS_REFUSED if _schema_admits(string, value)]
    assert not wrong, f"{field}: the schema {string} admits or refuses these against the contract: {wrong}"
    assert any(branch.get("type") == "null" for branch in field_schema.get("anyOf", [])), f"{field} is not nullable: {field_schema}"
    assert field_schema.get("default") is None and field not in schema.get("required", []), f"{field_schema}, required {schema.get('required')}"


@pytest.mark.parametrize("value", SAMPLE_RESOLUTIONS)
def test_pqs_s10_resolution_asks_one_of_the_three_steps(value):
    """PQS-S10: the item's ``resolution`` is optional, None by default, and takes daily, weekly or monthly, with
    ``target_currency`` and ``include_price=False`` too; its annotation is ``Optional[SampleResolution]``, the pure
    module's type.

    Red before Z-29a: the field does not exist, and the item refuses it as an extra one.
    """
    assert "resolution" in FAPriceQueryItem.model_fields, f"FAPriceQueryItem has no resolution: {sorted(FAPriceQueryItem.model_fields)}"
    assert FAPriceQueryItem.model_validate(_payload()).resolution is None
    item = FAPriceQueryItem.model_validate(_payload(resolution=value, target_currency="USD", include_price=False))
    assert (item.resolution, item.target_currency, item.include_price) == (value, "USD", False)
    annotation = FAPriceQueryItem.model_fields["resolution"].annotation
    assert set(typing.get_args(annotation)) == {_sampling().SampleResolution, type(None)}, f"resolution is typed {annotation!r}, not Optional[SampleResolution]"


@pytest.mark.parametrize("value", ["yearly", "Weekly", ""], ids=["yearly", "capitalised", "empty"])
def test_pqs_s11_resolution_outside_the_three_steps_refused(value):
    """PQS-S11: a step that is not daily, weekly or monthly — yearly, a capital letter, an empty string — is refused on
    the field itself.

    Red before Z-29a: refused too, but as an extra field (``extra_forbidden``), whatever the value.
    """
    errors = _refused(_payload(resolution=value))
    assert [(error["type"], error["loc"]) for error in errors] == [("literal_error", ("resolution",))], errors


def test_pqs_s12_json_schema_lists_the_item_resolution():
    """PQS-S12: ``model_json_schema()`` shows the item's ``resolution`` optional, null allowed, not required, its other
    values exactly the three steps.

    Red before Z-29a: the schema has no ``resolution``.
    """
    schema = FAPriceQueryItem.model_json_schema()
    field_schema = schema["properties"].get("resolution")
    assert field_schema is not None, f"no resolution in the schema: {sorted(schema['properties'])}"
    nullable, values = _nullable_literal(field_schema, schema.get("$defs", {}))
    assert (nullable, sorted(values)) == (True, sorted(SAMPLE_RESOLUTIONS)), field_schema
    assert field_schema.get("default") is None and "resolution" not in schema.get("required", []), f"{field_schema}, required {schema.get('required')}"


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param(("max_points", "resolution"), id="max-points-and-resolution"),
        pytest.param(("max_points", "sample_like"), id="max-points-and-sample-like"),
        pytest.param(("resolution", "sample_like"), id="resolution-and-sample-like"),
        pytest.param(SAMPLE_FIELDS, id="all-three"),
    ],
)
def test_pqs_s13_at_most_one_way_to_sample(fields):
    """PQS-S13: an item says its step one way at most: two of ``max_points``, ``resolution`` and ``sample_like``, or the
    three, are refused by a value error whose message names the three. Each alone is valid (the control).

    Red before Z-29a: refused, but for the fields themselves, extra ones.
    """
    for field in fields:
        assert FAPriceQueryItem.model_validate(_payload(**{field: SAMPLING_VALUES[field]})) is not None
    errors = _refused(_payload(**{field: SAMPLING_VALUES[field] for field in fields}))
    assert not [error for error in errors if error["type"] == "extra_forbidden"], f"refused as unknown fields: {errors}"
    assert any(error["type"] == "value_error" and all(field in error["msg"] for field in SAMPLE_FIELDS) for error in errors), errors


def test_pqs_s14_sample_bounds_is_none_without_prices_too():
    """PQS-S14: the description of ``FAPriceQueryResult.sample_bounds`` says it is None «without prices» too, not only
    for a daily series — a placeholder (point 14: ``include_price=False`` with ``max_points``, ``resolution`` or
    ``sample_like``) says weekly or monthly in ``resolution`` and carries no bounds. On the field, and in the JSON schema
    in both modes, what the OpenAPI document and the generated client read. The words are checked, not the sentence.

    Red before Z-29a-f: the description says None «for a daily one» only.
    """
    description = FAPriceQueryResult.model_fields["sample_bounds"].description or ""
    assert "without prices" in description.lower(), f"the field's description: {description!r}"
    for mode in ("validation", "serialization"):
        field_schema = FAPriceQueryResult.model_json_schema(mode=mode)["properties"]["sample_bounds"]
        assert "without prices" in field_schema.get("description", "").lower(), f"{mode}: {field_schema}"


# =============================================================================
# PQS-Q — get_prices_bulk ON A PRIVATE DATABASE
# =============================================================================


@dataclasses.dataclass(frozen=True)
class _World:
    """The private database, its assets (``_HISTORIES`` and EMPTY, on ``_ASSET_IDS``) and the days each one has a row on."""

    engine: AsyncEngine
    old: int
    young: int
    recent: int
    empty: int
    stored: dict[int, frozenset[date]]

    def named(self) -> dict[str, int]:
        """The assets by name."""
        return {"old": self.old, "young": self.young, "recent": self.recent, "empty": self.empty}


def _weekdays(first: date, gaps: tuple[tuple[date, date], ...]) -> list[date]:
    """Monday to Friday from ``first`` to ``FROZEN_TODAY``, less the days inside ``gaps``."""
    return [day for day in _days(first, FROZEN_TODAY) if day.weekday() < 5 and not any(start <= day <= end for start, end in gaps)]


def _price_row(asset_id: int, day: date, n: int, base: int) -> dict:
    """The ``n``-th row of an asset: a close of its own (``base`` + n / 100), open, high and low around it, a volume."""
    close = Decimal(base) + Decimal(n) / 100
    return {"asset_id": asset_id, "date": day, "open": close - 1, "high": close + 2, "low": close - 2, "close": close, "volume": Decimal(1000 + n), "currency": "EUR", "source_plugin_key": "MANUAL", "fetched_at": FETCHED_AT}


@pytest_asyncio.fixture
async def world(tmp_path: Path) -> AsyncIterator[_World]:
    """A private SQLite file under tmp_path with the whole ORM schema and four assets in EUR, on the ids of
    ``_ASSET_IDS``: OLD, YOUNG and RECENT with their weekday closes (``_HISTORIES``), EMPTY without a row. Disposed at the
    end."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'price_query_sampling.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        stored: dict[int, frozenset[date]] = {asset_id: frozenset() for asset_id in _ASSET_IDS.values()}
        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add_all([Asset(id=asset_id, display_name=f"Z-29a {name} {uuid.uuid4().hex[:8]}", currency="EUR", asset_type=AssetType.STOCK) for name, asset_id in _ASSET_IDS.items()])
            await session.flush()
            rows: list[dict] = []
            for name, (first, gaps, base) in _HISTORIES.items():
                days = _weekdays(first, gaps)
                stored[_ASSET_IDS[name]] = frozenset(days)
                rows.extend(_price_row(_ASSET_IDS[name], day, n, base) for n, day in enumerate(days))
            await session.execute(insert(PriceHistory), rows)
            await session.commit()
        yield _World(engine=engine, stored=stored, **_ASSET_IDS)
    finally:
        await engine.dispose()


async def _seed_eur_usd(engine: AsyncEngine) -> None:
    """EUR/USD on every weekday from ``FX_FIRST`` to ``FROZEN_TODAY``, none in August 2022, a different rate each day."""
    days = _weekdays(FX_FIRST, (FX_GAP_MONTH,))
    rows = [{"date": day, "base": "EUR", "quote": "USD", "rate": Decimal("1.05") + Decimal(n % 97) / 1000, "source": "ECB", "fetched_at": FETCHED_AT} for n, day in enumerate(days)]
    async with AsyncSession(engine) as session:
        await session.execute(insert(FxRate), rows)
        await session.commit()


@pytest.fixture
def frozen_ceiling(monkeypatch: pytest.MonkeyPatch) -> date:
    """``latest_range_end()`` answers ``CEILING`` where X-R55 reads it (``price_query``), whatever the day the suite runs."""
    monkeypatch.setattr(price_query, "latest_range_end", lambda: CEILING)
    return CEILING


async def _query(engine: AsyncEngine, *items: FAPriceQueryItem) -> list[FAPriceQueryResult]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await PriceQueryOperations.get_prices_bulk(list(items), session)


def _item(asset_id: int, start: date, end: date = FAR_END, **extra: Any) -> FAPriceQueryItem:
    return FAPriceQueryItem(asset_id=asset_id, date_range=DateRangeModel(start=start, end=end), **extra)


def _daily(item: FAPriceQueryItem) -> FAPriceQueryItem:
    """The same item without ``key`` and the sampling fields: the daily answer a sample is compared with."""
    return FAPriceQueryItem.model_validate(item.model_dump(exclude={"key", *SAMPLE_FIELDS}))


def _fill_first_day(stored: frozenset[date], start: date, end: date) -> date | None:
    """F: the range's start when a row precedes it, else the first row in the range; None with neither."""
    if any(day < start for day in stored):
        return start
    return min((day for day in stored if start <= day <= end), default=None)


@dataclasses.dataclass(frozen=True)
class _Expected:
    """What the contract gives an item on ``world``: its step; the day its sample starts on (``first``: F, or a
    following item's later start; None with nothing to fill), the day ``sample_bounds.first`` is on; the cut end, the day
    ``sample_bounds.last`` is on; and the dates of its ``prices``."""

    step: str
    first: date | None
    end: date | None
    dates: list[date]


def _plan(world: _World, asset_id: int, start: date, end: date | None, *, max_points: int | None = None, resolution: str | None = None) -> _Expected:
    """The contract for an asset on a range: the end cut at the ceiling; F; the step asked (``resolution``), chosen on F
    … end (``max_points``), or daily; the sampled dates. Nothing to fill: daily, no date."""
    cut = min(end or start, CEILING)
    first = _fill_first_day(world.stored[asset_id], start, cut) if start <= cut else None
    if first is None:
        return _Expected("daily", None, None, [])
    step = resolution or (_ref_step(first, cut, max_points) if max_points is not None else "daily")
    return _Expected(step, first, cut, _ref_sample_dates(first, cut, step))


def _expected(world: _World, item: FAPriceQueryItem) -> _Expected:
    """The contract for an item without ``sample_like``."""
    return _plan(world, item.asset_id, item.date_range.start, item.date_range.end, max_points=item.max_points, resolution=item.resolution)


def _expected_like(world: _World, target: FAPriceQueryItem, card: FAPriceQueryItem) -> _Expected:
    """The contract for ``target``, whose ``sample_like`` names ``card``: the card's step, from the later of the card's F
    and the target's own, on the target's fill; a card with nothing to fill lends its ``max_points`` or its
    ``resolution`` (daily with neither), and the target is sampled by itself."""
    start, end = target.date_range.start, target.date_range.end
    card_plan = _expected(world, card)
    if card_plan.first is None:
        return _plan(world, target.asset_id, start, end, max_points=card.max_points, resolution=card.resolution)
    own = _plan(world, target.asset_id, start, end)
    if own.first is None:
        return own
    first = max(card_plan.first, own.first)
    return _Expected(card_plan.step, first, own.end, _ref_sample_dates(first, own.end, card_plan.step))


def _expected_all(world: _World, items: list[FAPriceQueryItem]) -> list[_Expected]:
    """The contract for each item of one request, a ``sample_like`` read against the item that carries that key."""
    keyed = {item.key: item for item in items if item.key is not None}
    return [_expected(world, item) if item.sample_like is None else _expected_like(world, item, keyed[item.sample_like]) for item in items]


def _dates(result: FAPriceQueryResult) -> list[date]:
    return [point.date for point in result.prices]


def _first_difference(got: list[date], expected: list[date]) -> str:
    at = next((n for n, (left, right) in enumerate(zip(got, expected, strict=False)) if left != right), min(len(got), len(expected)))
    return f"{len(got):,} dates for {len(expected):,} expected; from position {at}: {got[at : at + 3]} instead of {expected[at : at + 3]}"


def _assert_bounds(sampled: FAPriceQueryResult, daily_points: dict[date, dict], expected: _Expected) -> None:
    """Weekly or monthly, ``sample_bounds`` are the daily answer's points on ``expected.first`` and on the cut end, the
    last one also the last of ``prices``; daily, there are none."""
    bounds = sampled.sample_bounds
    if expected.step == "daily":
        assert bounds is None, f"a daily answer with sample_bounds: {bounds}"
        return
    assert bounds is not None, f"a {expected.step} answer without sample_bounds"
    first, last = bounds.first.model_dump(mode="json"), bounds.last.model_dump(mode="json")
    assert first == daily_points.get(expected.first), f"sample_bounds.first is {first}, not the daily point on {expected.first}: {daily_points.get(expected.first)}"
    assert last == daily_points.get(expected.end), f"sample_bounds.last is {last}, not the daily point on {expected.end}: {daily_points.get(expected.end)}"
    assert last == sampled.prices[-1].model_dump(mode="json"), f"sample_bounds.last {last} is not the last point {sampled.prices[-1]}"


def _assert_sample_of_daily(sampled: FAPriceQueryResult, daily: FAPriceQueryResult, expected: _Expected) -> None:
    """``sampled`` says it is at ``expected.step`` and carries exactly ``expected.dates``, each point the daily answer's
    on that date, compared as JSON, every field written as the wire writes it; its bounds as ``_assert_bounds`` says.
    ``daily``, the same item without the sampling fields, says daily, without bounds."""
    assert sampled.asset_id == daily.asset_id
    assert (daily.resolution, daily.sample_bounds) == ("daily", None), f"the daily answer says {daily.resolution!r}, bounds {daily.sample_bounds}"
    assert sampled.resolution == expected.step, f"the sample says {sampled.resolution!r} for {expected.step!r}"
    assert _dates(sampled) == expected.dates, _first_difference(_dates(sampled), expected.dates)
    daily_points = {point.date: point.model_dump(mode="json") for point in daily.prices}
    sampled_points = [(point.date, point.model_dump(mode="json")) for point in sampled.prices]
    differing = [(day, got, daily_points.get(day)) for day, got in sampled_points if got != daily_points.get(day)]
    assert not differing, f"{len(differing)} of {len(expected.dates)} sampled points differ from the daily answer's on their date; the first (date, sampled, daily): {differing[0]}"
    assert (sampled.events, sampled.errors, sampled.signals) == ([], daily.errors, []), (sampled.events, sampled.errors, sampled.signals)
    _assert_bounds(sampled, daily_points, expected)


def _point(result: FAPriceQueryResult, day: date) -> FAPricePoint:
    found = [point for point in result.prices if point.date == day]
    assert len(found) == 1, f"{len(found)} points on {day} in the answer for asset {result.asset_id}"
    return found[0]


def _filled_from(point: FAPricePoint) -> tuple[date, int] | None:
    """The point's backward fill, (the stored row's day, days back); None when stored on its own day."""
    fill = point.backward_fill_info
    return None if fill is None else (fill.actual_rate_date, fill.days_back)


def _row_day(point: FAPricePoint) -> date:
    """The day of the stored row behind a native point: its own, or the one it is filled from."""
    fill = point.backward_fill_info
    return point.date if fill is None else fill.actual_rate_date


def _same(left: FAPriceQueryResult, right: FAPriceQueryResult) -> bool:
    """Two answers equal as the wire writes them."""
    return left.model_dump(mode="json") == right.model_dump(mode="json")


async def _refused_for_days(make_call: Callable[[], Awaitable[list[FAPriceQueryResult]]]) -> BulkTooManyDaysError:
    """The ``BulkTooManyDaysError`` the price query raises; when it raises none, the test fails saying what it answered."""
    try:
        results = await make_call()
    except BulkTooManyDaysError as refusal:
        return refusal
    pytest.fail(f"no BulkTooManyDaysError: {len(results)} items answered, {sum(len(result.prices) for result in results):,} points")


async def _refused_for_reference(make_call: Callable[[], Awaitable[list[FAPriceQueryResult]]]) -> Exception:
    """The ``SampleReferenceError`` the price query raises; when it raises none, the test fails saying what it answered."""
    error_type = getattr(_sampling(), "SampleReferenceError", None)
    if not (isinstance(error_type, type) and issubclass(error_type, Exception)):
        pytest.fail(f"{SAMPLING_MODULE} has no SampleReferenceError exception class: {error_type!r}")
    try:
        results = await make_call()
    except error_type as refusal:
        return refusal
    pytest.fail(f"no SampleReferenceError: {len(results)} items answered, resolutions {[getattr(result, 'resolution', None) for result in results]}")


async def _route_refusal(make_call: Callable[[], Awaitable[Any]]) -> HTTPException:
    """The ``HTTPException`` the route raises; when it raises none, the test fails saying what it answered."""
    try:
        answer = await make_call()
    except HTTPException as refused:
        return refused
    pytest.fail(f"no refusal: the route answered {len(answer.items)} items")


class _DailyFillBuilt(Exception):
    """``_build_backward_filled_series`` was called while the test forbids it."""


def _forbid_the_daily_fill(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """Replaces ``PriceQueryOperations._build_backward_filled_series`` with one that records its call and raises."""
    calls: list[tuple] = []

    def refuse(*args: Any, **kwargs: Any) -> list:
        calls.append((args[1:3], kwargs))
        raise _DailyFillBuilt(f"the daily fill was built, arguments {args[1:3]}")

    monkeypatch.setattr(PriceQueryOperations, "_build_backward_filled_series", staticmethod(refuse))
    return calls


@contextlib.contextmanager
def _counting_loads() -> Iterator[collections.Counter]:
    """The ``PriceHistory`` rows the ORM builds meanwhile, by asset: a ``load`` listener registered here, removed on exit."""
    loads: collections.Counter = collections.Counter()

    def on_load(target: PriceHistory, _context: Any) -> None:
        loads[target.asset_id] += 1

    event.listen(PriceHistory, "load", on_load)
    try:
        yield loads
    finally:
        event.remove(PriceHistory, "load", on_load)


@dataclasses.dataclass(frozen=True)
class _Statement:
    """One statement the engine sent to SQLite: its text, and its parameters flattened."""

    sql: str
    values: tuple


@contextlib.contextmanager
def _recording_statements(engine: AsyncEngine) -> Iterator[list[_Statement]]:
    """Every statement the engine sends meanwhile, in order: a ``before_cursor_execute`` listener on its sync engine,
    registered here, removed on exit."""
    seen: list[_Statement] = []

    def on_execute(_connection: Any, _cursor: Any, statement: str, parameters: Any, _context: Any, executemany: bool) -> None:
        rows = parameters if executemany else [parameters]
        seen.append(_Statement(statement, tuple(value for row in rows for value in (row.values() if isinstance(row, dict) else row or ()))))

    event.listen(engine.sync_engine, "before_cursor_execute", on_execute)
    try:
        yield seen
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", on_execute)


_PRICE_TABLE = re.compile(r"\bprice_history\b", re.IGNORECASE)
_GROUPING = re.compile(r"\b(?:GROUP|PARTITION)\s+BY\b", re.IGNORECASE)
_CLAUSE_TOKENS = re.compile(r"[(),]|\b(?:HAVING|ORDER\s+BY|LIMIT|UNION|EXCEPT|INTERSECT|WINDOW)\b", re.IGNORECASE)


def _grouping_width(tail: str) -> int:
    """How many terms the GROUP BY or PARTITION BY clause that ``tail`` starts with has: its commas at its own
    parenthesis depth, up to the parenthesis that closes the query around it or the clause that follows it."""
    depth, width = 0, 1
    for token in (found.group(0) for found in _CLAUSE_TOKENS.finditer(tail)):
        if token == "(":
            depth += 1
        elif token == ")" and depth:
            depth -= 1
        elif token == "," and not depth:
            width += 1
        elif not depth:
            return width
    return width


def _is_bucket_statement(statement: _Statement) -> bool:
    """A statement that picks ``price_history`` rows per asset and per bucket: it names the table and groups or
    partitions by two terms or more, the asset and the bucket (the v2 draft's ``_bucket_last_rows``: ``GROUP BY
    price_history.asset_id, strftime(…)``; a window's ``PARTITION BY asset_id, bucket`` as well). The daily read, the seed
    and the edge probes — ``ORDER BY … LIMIT 1``, or a ``GROUP BY`` of the asset alone — are not."""
    sql = statement.sql
    return _PRICE_TABLE.search(sql) is not None and any(_grouping_width(sql[found.end() :]) >= 2 for found in _GROUPING.finditer(sql))


def _names_asset(statement: _Statement, asset_id: int) -> bool:
    """Whether the statement reads the asset: its id is one of the parameters, or a literal of the text."""
    return asset_id in statement.values or re.search(rf"(?<![\w.]){asset_id}(?![\w.])", statement.sql) is not None


def _bucket_groups(statements: list[_Statement], world: _World) -> list[frozenset[str]]:
    """For each bucket statement, in order, the names of the world's assets it reads."""
    return [frozenset(name for name, asset_id in world.named().items() if _names_asset(statement, asset_id)) for statement in statements if _is_bucket_statement(statement)]


def _said(statements: list[_Statement]) -> str:
    """The statements, one line each and shortened, with their parameters: what a failure message shows of them."""
    return " | ".join(f"{' '.join(statement.sql.split())[:200]} {statement.values[:8]}" for statement in statements) or "(none)"


# ── points 4, 5 and 6: the step, per asset, on its own fill; the bounds ────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("asset", "start", "max_points", "days"),
    [
        pytest.param("young", date(2025, 10, 6), CARD, 377, id="days-equal-to-max-points"),
        pytest.param("recent", ALL_START, CARD, 286, id="a-short-history-on-a-card"),
        pytest.param("old", ALL_START, MAX_POINTS_BOUNDS[1], 9787, id="all-within-10000-points"),
    ],
)
async def test_pqs_q01_daily_chosen_is_the_answer_without_max_points(world, frozen_ceiling, asset, start, max_points, days):
    """PQS-Q01: an item whose fill's days fit in ``max_points`` is answered exactly as without it, the same points in the
    same order, no bounds, and says ``resolution`` daily, as the answer without it does: YOUNG from Monday 2025-10-06,
    seeded, to the ceiling — 377 days for 377 points; RECENT on «All», its 286 days from its first row; OLD on «All»,
    9 787 days within 10 000.

    Red before Z-29a: an item with ``max_points`` cannot be built, an extra field.
    """
    item = _item(getattr(world, asset), start, max_points=max_points)
    assert _expected(world, item).step == "daily", "premise"
    (sampled,) = await _query(world.engine, item)
    (daily,) = await _query(world.engine, _daily(item))
    assert len(daily.prices) == days, f"the daily answer has {len(daily.prices)} points"
    assert (sampled.resolution, daily.resolution, sampled.sample_bounds) == ("daily", "daily", None)
    assert _same(sampled, daily)


@pytest.mark.asyncio
async def test_pqs_q02_one_day_more_is_weekly_from_a_sunday(world, frozen_ceiling):
    """PQS-Q02: one day more than PQS-Q01's first case — YOUNG from Sunday 2025-10-05, 378 days for 377 points — is
    weekly, and says so in ``resolution``: 55 points, every Sunday from the first, which closes its ISO week, then the
    ceiling, each the daily answer's point on its date; the first filled from the Friday before the range, 2 days back.
    F closes its bucket, so ``sample_bounds.first`` is the first point itself; ``last`` is the point on the ceiling.

    Red before Z-29a: an item with ``max_points`` cannot be built, an extra field.
    """
    item = _item(world.young, date(2025, 10, 5), max_points=CARD)
    expected = _expected(world, item)
    assert (expected.step, len(expected.dates), expected.dates[:2]) == ("weekly", 55, [date(2025, 10, 5), date(2025, 10, 12)]), "premise"
    (sampled,) = await _query(world.engine, item)
    (daily,) = await _query(world.engine, _daily(item))
    _assert_sample_of_daily(sampled, daily, expected)
    assert _filled_from(_point(sampled, date(2025, 10, 5))) == (date(2025, 10, 3), 2)
    assert sampled.sample_bounds.first.model_dump(mode="json") == sampled.prices[0].model_dump(mode="json")


@pytest.mark.asyncio
async def test_pqs_q03_all_on_a_card_each_asset_its_own_step(world, frozen_ceiling):
    """PQS-Q03: «All» on a card (2000-01-01 to past the ceiling, 377 points), four assets in one request: OLD, rows since
    before 2000, monthly — 322 points, every month end from 2000-01-31 and the ceiling, F (2000-01-01, a Saturday) only
    in ``sample_bounds.first``, filled from the seed (1999-12-31); YOUNG, rows since Monday 2020-03-02, weekly — 346
    points, every Sunday from 2020-03-08 and the ceiling, its first row in ``sample_bounds.first``, stored that day;
    RECENT, 286 days, daily, as without max_points; EMPTY, no point. Each answer's ``resolution`` is its step — monthly,
    weekly, daily — and daily for EMPTY, which has nothing to sample, without bounds. Every sampled point and bound is the
    daily answer's on its date: March 2010 — a month without a row — from 2010-02-26, YOUNG's week without a row from
    2022-12-30, both last points, on the ceiling, from 2026-10-16.

    Red before Z-29a: an item with ``max_points`` cannot be built, an extra field.
    """
    items = [_item(world.old, ALL_START, max_points=CARD), _item(world.young, ALL_START, max_points=CARD), _item(world.recent, ALL_START, max_points=CARD), _item(world.empty, ALL_START, max_points=CARD)]
    expected = [_expected(world, item) for item in items]
    assert [(plan.step, plan.first, len(plan.dates)) for plan in expected] == [("monthly", ALL_START, 322), ("weekly", date(2020, 3, 2), 346), ("daily", date(2026, 1, 5), 286), ("daily", None, 0)], "premise"
    old, young, recent, empty = await _query(world.engine, *items)
    daily = await _query(world.engine, *(_daily(item) for item in items))
    _assert_sample_of_daily(old, daily[0], expected[0])
    _assert_sample_of_daily(young, daily[1], expected[1])
    assert (recent.resolution, recent.sample_bounds) == ("daily", None)
    assert _same(recent, daily[2])
    assert (empty.asset_id, empty.prices, empty.errors, empty.resolution, empty.sample_bounds, daily[3].prices) == (world.empty, [], [], "daily", None, [])
    assert (old.prices[0].date, old.sample_bounds.first.date, _filled_from(old.sample_bounds.first)) == (date(2000, 1, 31), ALL_START, (date(1999, 12, 31), 1))
    assert _filled_from(_point(old, date(2010, 3, 31))) == (date(2010, 2, 26), 33)
    assert _filled_from(_point(old, CEILING)) == (FROZEN_TODAY, 1)
    assert (young.prices[0].date, young.sample_bounds.first.date, _filled_from(young.sample_bounds.first)) == (date(2020, 3, 8), date(2020, 3, 2), None)
    assert _filled_from(_point(young, date(2023, 1, 8))) == (date(2022, 12, 30), 9)
    assert _filled_from(_point(young, CEILING)) == (FROZEN_TODAY, 1)


@pytest.mark.asyncio
async def test_pqs_q04_the_step_is_chosen_after_the_ceiling_cut(world, frozen_ceiling):
    """PQS-Q04: OLD on «All» to 2099-12-31 in 1 534 points (one wide column). Cut at the ceiling, the fill's 1 399 weeks
    fit: weekly, as the answer's ``resolution`` says, 1 399 points from Sunday 2000-01-02 to the ceiling, each the daily
    answer's — the week without a row (2015-06-08 … 2015-06-14) filled from Friday 2015-06-05 — and the bounds on
    2000-01-01 and on the ceiling. Uncut, the 5 219 weeks to 2099 would not fit, and the step would be monthly: the step
    is chosen on the cut range.

    Red before Z-29a: an item with ``max_points`` cannot be built, an extra field.
    """
    item = _item(world.old, ALL_START, FAR_END, max_points=WIDE)
    assert _ref_step(ALL_START, FAR_END, WIDE) == "monthly", "premise: uncut, the step would be monthly"
    expected = _expected(world, item)
    assert (expected.step, len(expected.dates), expected.dates[0], expected.dates[-1]) == ("weekly", 1399, date(2000, 1, 2), CEILING), "premise"
    (sampled,) = await _query(world.engine, item)
    (daily,) = await _query(world.engine, _daily(item))
    _assert_sample_of_daily(sampled, daily, expected)
    assert _filled_from(_point(sampled, date(2015, 6, 14))) == (date(2015, 6, 5), 9)


@pytest.mark.asyncio
async def test_pqs_q05_seeded_fill_from_a_month_end_monthly_past_max_points(world, frozen_ceiling):
    """PQS-Q05: OLD from Saturday 2015-01-31 in 100 points: a row precedes the range, so F is the range's start; neither
    the 4 278 days nor the 612 weeks fit, and monthly is the floor — 142 points, past 100, ``resolution`` monthly. The
    first point, 2015-01-31, closes its month, so it is a point and ``sample_bounds.first`` both, filled from Friday
    2015-01-30; each point is the daily answer's.

    Red before Z-29a: an item with ``max_points`` cannot be built, an extra field.
    """
    item = _item(world.old, date(2015, 1, 31), max_points=100)
    expected = _expected(world, item)
    assert (expected.step, len(expected.dates), expected.dates[:2]) == ("monthly", 142, [date(2015, 1, 31), date(2015, 2, 28)]), "premise"
    (sampled,) = await _query(world.engine, item)
    (daily,) = await _query(world.engine, _daily(item))
    _assert_sample_of_daily(sampled, daily, expected)
    assert _filled_from(_point(sampled, date(2015, 1, 31))) == (date(2015, 1, 30), 1)
    assert sampled.sample_bounds.first.model_dump(mode="json") == sampled.prices[0].model_dump(mode="json")


@pytest.mark.asyncio
@pytest.mark.parametrize("fields", [pytest.param({"max_points": CARD}, id="on-a-card"), pytest.param({"resolution": "weekly"}, id="weekly-asked"), pytest.param({"resolution": "monthly"}, id="monthly-asked")])
@pytest.mark.parametrize(
    ("asset", "end"),
    [
        pytest.param("empty", FAR_END, id="no-row-at-all"),
        pytest.param("young", date(2019, 12, 31), id="no-row-before-nor-in-the-range"),
    ],
)
async def test_pqs_q06_nothing_to_fill_from_no_point(world, frozen_ceiling, asset, end, fields):
    """PQS-Q06: with no row before the range and none in it — EMPTY on «All», YOUNG on 2000 … 2019 — an item on a card,
    or asking weekly or monthly, has no point, no bounds and says ``resolution`` daily, exactly as the same item without
    the field: there is no point for a bound to be.

    Red before Z-29a: an item with ``max_points`` or ``resolution`` cannot be built, an extra field.
    """
    item = _item(getattr(world, asset), ALL_START, end, **fields)
    (sampled,) = await _query(world.engine, item)
    (daily,) = await _query(world.engine, _daily(item))
    assert daily.prices == [], "premise"
    assert (sampled.resolution, sampled.sample_bounds) == ("daily", None)
    assert _same(sampled, daily)


# ── point 9: the conversion and include_price ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pqs_q07_target_currency_converts_each_sampled_point(world, frozen_ceiling):
    """PQS-Q07: in USD, with EUR/USD rates on weekdays and none in August 2022: YOUNG from 2020 on a card (weekly) and
    OLD from 2015-01-31 in 100 points (monthly) are, point by point and bound by bound, the daily answer's converted
    points on their dates, and say ``resolution`` weekly and monthly where the daily answers say daily. The conversion
    ran per point: Sunday 2020-03-08, YOUNG's first point, carries Friday's close and Friday's rate (2 days back each),
    and 2022-08-31, stored that day, the rate of 2022-07-29, 33 days back.

    Red before Z-29a: an item with ``max_points`` cannot be built, an extra field.
    """
    await _seed_eur_usd(world.engine)
    items = [_item(world.young, date(2020, 1, 1), max_points=CARD, target_currency="USD"), _item(world.old, date(2015, 1, 31), max_points=100, target_currency="USD")]
    expected = [_expected(world, item) for item in items]
    assert [plan.step for plan in expected] == ["weekly", "monthly"], "premise"
    sampled = await _query(world.engine, *items)
    daily = await _query(world.engine, *(_daily(item) for item in items))
    for answer in daily:
        assert answer.prices and {(point.currency, point.original_currency) for point in answer.prices} == {("USD", "EUR")}, "premise: every daily point converted"
    for answer, reference, plan in zip(sampled, daily, expected, strict=True):
        _assert_sample_of_daily(answer, reference, plan)
    young, old = sampled
    sunday = _point(young, date(2020, 3, 8)).backward_fill_info
    assert (sunday.actual_rate_date, sunday.days_back, sunday.fx_rate_date, sunday.fx_days_back) == (date(2020, 3, 6), 2, date(2020, 3, 6), 2)
    august = _point(old, date(2022, 8, 31)).backward_fill_info
    assert (august.actual_rate_date, august.days_back, august.fx_rate_date, august.fx_days_back) == (date(2022, 8, 31), 0, date(2022, 7, 29), 33)


@pytest.mark.asyncio
async def test_pqs_q08_include_price_false_no_point(world, frozen_ceiling):
    """PQS-Q08: a sampled item with ``include_price=False`` has no point and no error, as without ``max_points``.

    Red before Z-29a: an item with ``max_points`` cannot be built, an extra field.
    """
    (result,) = await _query(world.engine, _item(world.young, ALL_START, max_points=CARD, include_price=False))
    assert (result.asset_id, result.prices, result.errors) == (world.young, [], [])


# ── point 10: the day budget ──────────────────────────────────────────────────────────────────────────────────────


def _two_sampled_items(world: _World, how: str) -> list[FAPriceQueryItem]:
    """OLD and YOUNG on «All», only sampled: each on a card (monthly and weekly), each asking that step, or YOUNG
    following OLD's card (both monthly, YOUNG from its first row)."""
    if how == "resolution":
        return [_item(world.old, ALL_START, resolution="monthly"), _item(world.young, ALL_START, resolution="weekly")]
    if how == "sample-like":
        return [_item(world.old, ALL_START, key="card", max_points=CARD), _item(world.young, ALL_START, sample_like="card")]
    return [_item(world.old, ALL_START, max_points=CARD), _item(world.young, ALL_START, max_points=CARD)]


@pytest.mark.asyncio
@pytest.mark.parametrize(("how", "points"), [pytest.param("max-points", 672, id="on-a-card"), pytest.param("resolution", 672, id="the-steps-asked"), pytest.param("sample-like", 406, id="young-following-olds-card")])
async def test_pqs_q09_the_budget_counts_the_sampled_points_and_their_bounds(world, frozen_ceiling, monkeypatch, how, points):
    """PQS-Q09: OLD and YOUNG on «All», only sampled; their daily fills span 9 787 + 2 421 = 12 208 days. On a card, or
    asking those steps: 322 monthly and 346 weekly points, each item 2 bounds more — 324 + 348 = 672; YOUNG following
    OLD's card, monthly from its first row: 324 + (80 + 2) = 406. Under that budget the request is answered with the
    samples; under one less, ``BulkTooManyDaysError`` with ``item_days`` that count — the points and the bounds, not the
    fill days.

    Red before Z-29a: an item with ``max_points``, ``resolution`` or ``sample_like`` cannot be built, an extra field.
    """
    items = _two_sampled_items(world, how)
    expected = _expected_all(world, items)
    fill_days = sum(_ref_counts(_expected(world, _daily(item)).first, CEILING)[0] for item in items)
    assert (sum(len(plan.dates) + 2 for plan in expected), fill_days) == (points, 12_208), "premise"
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", points)
    answered = await _query(world.engine, *items)
    assert [_dates(result) for result in answered] == [plan.dates for plan in expected]
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", points - 1)
    refusal = await _refused_for_days(lambda: _query(world.engine, *items))
    assert (refusal.item_days, refusal.max_item_days) == (points, points - 1)


@pytest.mark.asyncio
@pytest.mark.parametrize("daily_fields", [pytest.param({}, id="no-sampling-field"), pytest.param({"max_points": CARD}, id="max-points-whose-days-fit"), pytest.param({"resolution": "daily"}, id="daily-asked")])
async def test_pqs_q10_a_mixed_request_counts_fill_days_and_points(world, frozen_ceiling, monkeypatch, daily_fields):
    """PQS-Q10: YOUNG from 2026-01-01, seeded, daily — without a sampling field, with 377 points that its 290 days fit,
    or asking daily — beside OLD on «All» on a card, monthly, 322 points and 2 bounds: the request counts 290 + 324 =
    614. Answered under a budget of 614; under 613, ``BulkTooManyDaysError`` with ``item_days`` 614.

    Red before Z-29a: an item with ``max_points`` or ``resolution`` cannot be built, an extra field.
    """
    daily_item = _item(world.young, date(2026, 1, 1), **daily_fields)
    sampled_item = _item(world.old, ALL_START, max_points=CARD)
    daily_dates = _days(date(2026, 1, 1), CEILING)
    sampled_plan = _expected(world, sampled_item)
    total = len(daily_dates) + len(sampled_plan.dates) + 2
    assert (_expected(world, daily_item).step, len(daily_dates), total) == ("daily", 290, 614), "premise"
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", total)
    answered = await _query(world.engine, daily_item, sampled_item)
    assert [_dates(result) for result in answered] == [daily_dates, sampled_plan.dates]
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", total - 1)
    refusal = await _refused_for_days(lambda: _query(world.engine, daily_item, sampled_item))
    assert (refusal.item_days, refusal.max_item_days) == (total, total - 1)


@pytest.mark.asyncio
async def test_pqs_q14_a_request_refused_for_its_sampled_points_reads_no_bucket_row(world, frozen_ceiling, monkeypatch):
    """PQS-Q14: the budget is checked before the bucket rows are read. PQS-Q09's request on a card — OLD and YOUNG on
    «All», 322 + 346 sampled points and 2 bounds each, 672, both assets only sampled — under a budget of 671 raises
    ``BulkTooManyDaysError`` with ``item_days`` 672 having loaded through the ORM at most 2 ``PriceHistory`` rows of each
    asset: at most the seed and the first row in the range (OLD: 1999-12-31 and 2000-01-03; YOUNG: 2020-03-02 alone), not
    the hundreds behind the points, one per month or week. The ``load`` listener counts the rows by asset. Its presence
    barrier: under a budget of 672 the same request is answered with its samples and the listener sees more than 2 rows
    of each asset loaded — the rows are read where it looks, so «at most 2» under the refusal is a read that did not
    happen, not one it cannot see.

    Red before Z-29a: an item with ``max_points`` cannot be built, an extra field. Red too against a draft that reads the
    bucket rows before it checks the budget: refused with the same ``item_days``, it has already loaded them.
    """
    items = [_item(world.old, ALL_START, max_points=CARD), _item(world.young, ALL_START, max_points=CARD)]
    expected = [_expected(world, item) for item in items]
    points = sum(len(plan.dates) + 2 for plan in expected)
    assert points == 672, "premise"
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", points)
    with _counting_loads() as answered_loads:
        answered = await _query(world.engine, *items)
    assert [_dates(result) for result in answered] == [plan.dates for plan in expected]
    seen = {item.asset_id: answered_loads[item.asset_id] for item in items}
    assert all(count > 2 for count in seen.values()), f"answered under a budget of {points}, the listener saw {seen} price rows loaded (asset id: rows), not more than 2 of each asset: the rows are not read through the ORM, and the bound under the refusal would prove nothing"
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", points - 1)
    with _counting_loads() as refused_loads:
        refusal = await _refused_for_days(lambda: _query(world.engine, *items))
    assert (refusal.item_days, refusal.max_item_days) == (points, points - 1)
    assert all(count <= 2 for count in refused_loads.values()), f"refused for its {points} points and bounds, the request had loaded {dict(refused_loads)} price rows (asset id: rows), more than the seed and the first row in the range of an asset: bucket rows read before the budget check"


# ── point 11: what a sample costs ─────────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pqs_q11_sampled_items_never_build_the_daily_fill(world, frozen_ceiling, monkeypatch):
    """PQS-Q11: a request of weekly and monthly items only, all on «All» — OLD on a card (monthly, keyed ``card``) and in
    1 534 points (weekly), YOUNG on a card (weekly), RECENT asking weekly, YOUNG following OLD's card (monthly) — is
    answered with its samples, each saying its step in ``resolution``, while
    ``PriceQueryOperations._build_backward_filled_series`` raises: no daily fill is built for them.

    Red before Z-29a: an item with ``max_points``, ``resolution`` or ``sample_like`` cannot be built, an extra field.
    """
    items = [
        _item(world.old, ALL_START, key="card", max_points=CARD),
        _item(world.young, ALL_START, max_points=CARD),
        _item(world.old, ALL_START, max_points=WIDE),
        _item(world.recent, ALL_START, resolution="weekly"),
        _item(world.young, ALL_START, sample_like="card"),
    ]
    expected = _expected_all(world, items)
    assert [plan.step for plan in expected] == ["monthly", "weekly", "weekly", "weekly", "monthly"], "premise"
    calls = _forbid_the_daily_fill(monkeypatch)
    try:
        results = await _query(world.engine, *items)
    except _DailyFillBuilt as built:
        pytest.fail(f"a weekly or monthly item built the daily fill: {built}")
    assert calls == []
    assert [_dates(result) for result in results] == [plan.dates for plan in expected]
    assert [result.resolution for result in results] == [plan.step for plan in expected]


@pytest.mark.asyncio
async def test_pqs_q12_sampled_items_read_at_most_buckets_plus_two_rows(world, frozen_ceiling):
    """PQS-Q12: OLD (monthly, 322 months) and YOUNG (weekly, 346 weeks) on «All» on a card read through the ORM at most
    324 and 348 price rows: one per bucket, plus the seed and the first row in the range — not their 6 985 and 1 725
    rows. The ``load`` listener counts the rows by asset. Its presence barrier: it saw at least the stored rows behind
    the sampled points (321 and 345: a month or a week without a row shares its row with the bucket before), so a bound
    met because the rows were read some other way cannot pass for one met.

    Red before Z-29a: an item with ``max_points`` cannot be built, an extra field.
    """
    items = [_item(world.old, ALL_START, max_points=CARD), _item(world.young, ALL_START, max_points=CARD)]
    expected = [_expected(world, item) for item in items]
    with _counting_loads() as loads:
        results = await _query(world.engine, *items)
    read = dict(loads)
    for item, result, plan in zip(items, results, expected, strict=True):
        assert _dates(result) == plan.dates, _first_difference(_dates(result), plan.dates)
        bound = _ref_buckets(plan.first, CEILING, plan.step) + 2
        behind = len({_row_day(point) for point in result.prices})
        loaded = read.get(item.asset_id, 0)
        assert loaded >= behind, f"asset {item.asset_id}: the listener saw {loaded} rows loaded, fewer than the {behind} behind the points — not read through the ORM, the bound proves nothing"
        assert loaded <= bound, f"asset {item.asset_id} ({plan.step}): {loaded:,} price rows read, more than {bound} (buckets + 2)"


# ── point 12: the order of the request ────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pqs_q13_the_request_order_is_kept(world, frozen_ceiling):
    """PQS-Q13: seven items in one request — YOUNG daily on «All»; OLD on a card (monthly, keyed ``card``); OLD after the
    ceiling; YOUNG on a card (weekly), the first item's asset sampled; OLD in 1 534 points (weekly), the second's sampled
    again; RECENT asking monthly; YOUNG following OLD's card (monthly) — answer in that order, each saying its step in
    ``resolution``: the item after the ceiling empty in its place (its asset id, no point, no event, no error, no bound,
    daily), each other one as when asked alone — the follower as beside its card alone.

    Red before Z-29a: an item with ``max_points``, ``resolution``, ``key`` or ``sample_like`` cannot be built, an extra
    field.
    """
    items = [
        _item(world.young, ALL_START),
        _item(world.old, ALL_START, key="card", max_points=CARD),
        _item(world.old, CEILING + timedelta(days=1), date(2026, 12, 31), max_points=CARD),
        _item(world.young, ALL_START, max_points=CARD),
        _item(world.old, ALL_START, max_points=WIDE),
        _item(world.recent, ALL_START, resolution="monthly"),
        _item(world.young, ALL_START, sample_like="card"),
    ]
    expected = _expected_all(world, items)
    assert [plan.step for plan in expected] == ["daily", "monthly", "daily", "weekly", "weekly", "monthly", "monthly"], "premise"
    results = await _query(world.engine, *items)
    assert [result.asset_id for result in results] == [item.asset_id for item in items]
    assert [result.resolution for result in results] == [plan.step for plan in expected]
    after = results[2]
    assert (after.prices, after.events, after.errors, after.signals, after.sample_bounds) == ([], [], [], [], None)
    assert [_dates(result) for result in results] == [plan.dates for plan in expected]
    assert _dates(results[0]) == _days(date(2020, 3, 2), CEILING)
    for index in (0, 1, 3, 4, 5):
        (alone,) = await _query(world.engine, items[index])
        assert _same(results[index], alone), f"position {index} differs from the item asked alone"
    _card, paired = await _query(world.engine, items[1], items[6])
    assert _same(results[6], paired), "position 6 differs from the follower asked beside its card alone"


# ── points 5 and 6: the step asked, the first day as a bound ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("asset", "start", "step", "count", "opens_with_first"),
    [
        pytest.param("young", date(2025, 10, 8), "weekly", 54, False, id="weekly-from-a-wednesday"),
        pytest.param("young", date(2025, 10, 5), "weekly", 55, True, id="weekly-from-a-sunday"),
        pytest.param("old", date(2015, 1, 15), "monthly", 142, False, id="monthly-from-mid-january"),
        pytest.param("old", date(2015, 1, 31), "monthly", 142, True, id="monthly-from-a-month-end"),
    ],
)
async def test_pqs_q15_the_first_day_is_a_bound_and_a_point_only_when_it_closes_its_bucket(world, frozen_ceiling, asset, start, step, count, opens_with_first):
    """PQS-Q15: the series a sample carries is the one the compact chart draws, the last point of each bucket: F, the
    fill's first day, is always ``sample_bounds.first`` and is a point only when it closes its bucket. YOUNG asking weekly
    from Wednesday 2025-10-08 (54 points, from Sunday 2025-10-12) and from Sunday 2025-10-05 (55, F the first); OLD asking
    monthly from Thursday 2015-01-15 (142, from 2015-01-31) and from Saturday 2015-01-31 (142, F the first). Each seeded,
    each to the ceiling, which is ``sample_bounds.last`` and the last point; every point and bound the daily answer's.

    Red before Z-29a: an item with ``resolution`` cannot be built, an extra field.
    """
    item = _item(getattr(world, asset), start, resolution=step)
    expected = _expected(world, item)
    assert (expected.step, expected.first, len(expected.dates), expected.dates[0] == start) == (step, start, count, opens_with_first), "premise"
    (sampled,) = await _query(world.engine, item)
    (daily,) = await _query(world.engine, _daily(item))
    _assert_sample_of_daily(sampled, daily, expected)
    assert (sampled.sample_bounds.first.date, sampled.prices[0].date == start, sampled.sample_bounds.last.date) == (start, opens_with_first, CEILING)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("asset", "start", "end", "step", "count", "card_step"),
    [
        pytest.param("young", date(2026, 7, 1), date(2026, 9, 30), "weekly", 14, "daily", id="weekly-on-three-months"),
        pytest.param("young", date(2026, 7, 1), date(2026, 9, 30), "monthly", 3, "daily", id="monthly-on-three-months"),
        pytest.param("old", ALL_START, FAR_END, "weekly", 1399, "monthly", id="weekly-on-all-past-a-card"),
    ],
)
async def test_pqs_q16_resolution_is_the_step_whatever_the_counts(world, frozen_ceiling, asset, start, end, step, count, card_step):
    """PQS-Q16: an item asking a step gets it, whatever its fill's counts: YOUNG on Wednesday 2026-07-01 … Wednesday
    2026-09-30, 92 days a card would draw daily, asking weekly (14 points: every Sunday from 2026-07-05, then the end) or
    monthly (3: the three month ends); OLD on «All», which a card would draw monthly, asking weekly (1 399 points, more
    than a card's 377). ``resolution`` says the step asked, the bounds are the daily points on F and on the end, every
    point the daily answer's.

    Red before Z-29a: an item with ``resolution`` cannot be built, an extra field.
    """
    item = _item(getattr(world, asset), start, end, resolution=step)
    expected = _expected(world, item)
    assert (expected.step, len(expected.dates), _ref_step(expected.first, expected.end, CARD)) == (step, count, card_step), "premise: on a card the step would be another"
    (sampled,) = await _query(world.engine, item)
    (daily,) = await _query(world.engine, _daily(item))
    _assert_sample_of_daily(sampled, daily, expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("asset", "start", "days"),
    [
        pytest.param("young", date(2026, 7, 1), 109, id="a-seeded-range"),
        pytest.param("old", ALL_START, 9787, id="all"),
    ],
)
async def test_pqs_q17_resolution_daily_is_the_daily_answer(world, frozen_ceiling, asset, start, days):
    """PQS-Q17: an item asking daily is answered exactly as without the field — the same points in the same order,
    ``resolution`` daily, no bounds: YOUNG from 2026-07-01 to the ceiling (109 days), OLD on «All» (9 787).

    Red before Z-29a: an item with ``resolution`` cannot be built, an extra field.
    """
    item = _item(getattr(world, asset), start, resolution="daily")
    (asked,) = await _query(world.engine, item)
    (daily,) = await _query(world.engine, _daily(item))
    assert len(daily.prices) == days, f"premise: the daily answer has {len(daily.prices)} points"
    assert (asked.resolution, asked.sample_bounds) == ("daily", None)
    assert _same(asked, daily)


# ── point 7: an item that follows another's buckets ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("card_asset", "card_fields", "target_asset", "step", "first", "count"),
    [
        pytest.param("old", {"max_points": CARD}, "young", "monthly", date(2020, 3, 2), 80, id="a-later-target-on-a-monthly-card"),
        pytest.param("young", {"max_points": CARD}, "old", "weekly", date(2020, 3, 2), 346, id="an-older-target-from-the-cards-first-day"),
        pytest.param("young", {"resolution": "monthly"}, "old", "monthly", date(2020, 3, 2), 80, id="a-card-asking-its-step"),
        pytest.param("recent", {"max_points": CARD}, "old", "daily", date(2026, 1, 5), 286, id="a-daily-card-a-daily-target-from-its-first-day"),
        pytest.param("recent", {}, "old", "daily", date(2026, 1, 5), 286, id="a-card-without-a-sampling-field"),
        pytest.param("empty", {"max_points": CARD}, "young", "weekly", date(2020, 3, 2), 346, id="a-card-with-nothing-lends-its-max-points"),
        pytest.param("empty", {"resolution": "monthly"}, "young", "monthly", date(2020, 3, 2), 80, id="a-card-with-nothing-lends-its-resolution"),
        pytest.param("empty", {}, "young", "daily", date(2020, 3, 2), 2421, id="a-card-with-nothing-nor-a-step-daily"),
        pytest.param("old", {"max_points": CARD, "include_price": False}, "young", "monthly", date(2020, 3, 2), 80, id="a-card-without-its-prices"),
    ],
)
async def test_pqs_q18_sample_like_puts_the_target_on_the_cards_buckets(world, frozen_ceiling, card_asset, card_fields, target_asset, step, first, count):
    """PQS-Q18: a card (``key`` ``card``) and a target (``sample_like`` ``card``) in one request, both on «All». The
    target takes the card's step — the one the card's answer says — from the later of the card's F and its own first
    day, on its own daily fill: YOUNG on OLD's card monthly from its first row 2020-03-02 (80 points; alone on a card it
    would be weekly); OLD on YOUNG's card weekly from YOUNG's F, 2020-03-02 (346; alone, monthly from 2000); OLD on a
    YOUNG card asking monthly, monthly from 2020-03-02; OLD on RECENT's card, daily by count or by default, daily from
    RECENT's first row 2026-01-05 (286 days, no bounds). A card with nothing to fill (EMPTY) lends its ``max_points``
    (YOUNG weekly, 346), its ``resolution`` (monthly, 80) or nothing (daily, YOUNG's whole 2 421 days), and the target is
    sampled by itself. A card sent with ``include_price=False``, as the settings dialog sends it, leads its target all
    the same. Every point and bound is the target's daily answer's; the card answers as it does alone.

    Red before Z-29a: an item with ``key`` or ``sample_like`` cannot be built, an extra field.
    """
    card = _item(getattr(world, card_asset), ALL_START, key="card", **card_fields)
    target = _item(getattr(world, target_asset), ALL_START, sample_like="card")
    expected = _expected_like(world, target, card)
    assert (expected.step, expected.first, len(expected.dates)) == (step, first, count), "premise"
    card_answer, target_answer = await _query(world.engine, card, target)
    (target_daily,) = await _query(world.engine, _daily(target))
    (card_alone,) = await _query(world.engine, card)
    _assert_sample_of_daily(target_answer, target_daily, expected)
    assert _same(card_answer, card_alone), "the card answers otherwise beside its target than alone"


@pytest.mark.asyncio
async def test_pqs_q19_several_cards_and_targets_on_one_asset(world, frozen_ceiling):
    """PQS-Q19: two cards on OLD — ``c1`` on a card (monthly), ``c2`` in 1 534 points (weekly) — and four targets, YOUNG
    and RECENT following each: monthly and weekly from YOUNG's first row 2020-03-02 (80 and 346 points), from RECENT's
    2026-01-05 (10 and 41). One request answers each in its place and with its step: each card as alone, each target as
    beside its card alone.

    Red before Z-29a: an item with ``key`` or ``sample_like`` cannot be built, an extra field.
    """
    cards = [_item(world.old, ALL_START, key="c1", max_points=CARD), _item(world.old, ALL_START, key="c2", max_points=WIDE)]
    targets = [_item(asset_id, ALL_START, sample_like=key) for asset_id in (world.young, world.recent) for key in ("c1", "c2")]
    items = [*cards, *targets]
    expected = _expected_all(world, items)
    young_first, recent_first = date(2020, 3, 2), date(2026, 1, 5)
    steps = [("monthly", ALL_START, 322), ("weekly", ALL_START, 1399), ("monthly", young_first, 80), ("weekly", young_first, 346), ("monthly", recent_first, 10), ("weekly", recent_first, 41)]
    assert [(plan.step, plan.first, len(plan.dates)) for plan in expected] == steps, "premise"
    results = await _query(world.engine, *items)
    assert [(result.asset_id, result.resolution) for result in results] == [(item.asset_id, plan.step) for item, plan in zip(items, expected, strict=True)]
    assert [_dates(result) for result in results] == [plan.dates for plan in expected]
    for index, card in enumerate(cards):
        (alone,) = await _query(world.engine, card)
        assert _same(results[index], alone), f"card {card.key} differs from the card asked alone"
    for index, target in enumerate(targets, start=len(cards)):
        owner = next(card for card in cards if card.key == target.sample_like)
        _owner, paired = await _query(world.engine, owner, target)
        assert _same(results[index], paired), f"position {index} differs from the target asked beside its card alone"


# ── point 8: the references, the request's ────────────────────────────────────────────────────────────────────────

#: Requests with one wrong reference — each item (asset, start, fields) on «All» unless said — and the refusal they
#: earn: (index, key, reason).
_REFERENCE_CASES = [
    pytest.param((("old", ALL_START, {"key": "card", "max_points": CARD}), ("young", ALL_START, {"sample_like": "nope"})), (1, None, "unknown_key"), id="unknown-key"),
    pytest.param((("young", ALL_START, {"sample_like": "card"}),), (0, None, "unknown_key"), id="unknown-key-no-item-has-a-key"),
    pytest.param((("old", ALL_START, {"key": "card", "max_points": CARD}), ("young", ALL_START, {"key": "target", "sample_like": "nope"})), (1, "target", "unknown_key"), id="unknown-key-the-wrong-item-keyed"),
    pytest.param((("old", ALL_START, {"key": "card", "max_points": CARD}), ("recent", ALL_START, {"key": "card", "resolution": "weekly"}), ("young", ALL_START, {"sample_like": "card"})), (1, "card", "duplicate_key"), id="duplicate-key-the-second"),
    pytest.param((("old", ALL_START, {"key": "a", "max_points": CARD}), ("young", ALL_START, {"key": "b", "sample_like": "a"}), ("recent", ALL_START, {"sample_like": "b"})), (2, None, "chained"), id="chained"),
    pytest.param((("old", ALL_START, {"key": "self", "sample_like": "self"}),), (0, "self", "chained"), id="chained-to-itself"),
    pytest.param((("old", ALL_START, {"key": "card", "max_points": CARD}), ("young", date(2020, 1, 1), {"sample_like": "card"})), (1, None, "range_mismatch"), id="range-mismatch"),
    pytest.param((("old", CEILING + timedelta(days=1), {}), ("old", ALL_START, {"key": "card", "max_points": CARD}), ("young", ALL_START, {"sample_like": "nope"})), (2, None, "unknown_key"), id="unknown-key-behind-an-item-after-the-ceiling"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("spec", "refusal"), _REFERENCE_CASES)
async def test_pqs_q20_a_wrong_reference_is_refused_before_any_read(world, frozen_ceiling, spec, refusal):
    """PQS-Q20: ``get_prices_bulk`` raises ``SampleReferenceError`` before any statement for a request with a wrong
    reference, its ``index``, ``key`` and ``reason`` those of the item at fault: a ``sample_like`` naming no item's key
    (``unknown_key``; the item's own ``key`` as ``key``, None when it has none); a key two items carry
    (``duplicate_key``, the second); a ``sample_like`` naming an item that has one itself (``chained``: two levels, or
    itself); a ``sample_like`` naming an item with another ``date_range`` (``range_mismatch``). The references are the
    request's: an item after the ceiling, which X-R55 answers empty, keeps its place, and ``index`` is the position in
    the request as sent. ``sample_reference_detail(error)`` is ``{"code": "sample_reference", "reason", "item", "key",
    "message"}``, the message a sentence. Statements are seen by a ``before_cursor_execute`` listener; its presence
    barrier: the same listener sees the statements of a valid card and target on the same database.

    Red before Z-29a: an item with ``key`` or ``sample_like`` cannot be built, an extra field.
    """
    items = [_item(getattr(world, name), start, **fields) for name, start, fields in spec]
    valid = [_item(world.old, ALL_START, key="card", max_points=CARD), _item(world.young, ALL_START, sample_like="card")]
    with _recording_statements(world.engine) as valid_said:
        await _query(world.engine, *valid)
    assert valid_said, "barrier: the listener saw no statement of a valid request, and «no statement» under the refusal would prove nothing"
    with _recording_statements(world.engine) as refused_said:
        error = await _refused_for_reference(lambda: _query(world.engine, *items))
    assert not refused_said, f"refused after {len(refused_said)} statements: {_said(refused_said)}"
    index, key, reason = refusal
    assert (error.index, error.key, error.reason) == refusal, f"refused with index {error.index!r}, key {error.key!r}, reason {error.reason!r}"
    detail = _sampling().sample_reference_detail(error)
    assert isinstance(detail, dict) and set(detail) == REFERENCE_DETAIL_KEYS, detail
    assert {name: detail[name] for name in ("code", "reason", "item", "key")} == {"code": "sample_reference", "reason": reason, "item": index, "key": key}, detail
    assert isinstance(detail["message"], str) and detail["message"].strip(), detail


@pytest.mark.asyncio
async def test_pqs_q21_the_route_answers_422_sample_reference(world, frozen_ceiling):
    """PQS-Q21: ``POST /assets/prices/query``'s handler, called as a function on a session of the private database,
    turns the error into a 422 whose ``detail`` is ``sample_reference_detail`` of the error ``get_prices_bulk`` raises
    for the same request — ``sample_reference``, ``unknown_key``, item 1 — not a 500.

    Red before Z-29a: an item with ``key`` or ``sample_like`` cannot be built, an extra field.
    """
    items = [_item(world.old, ALL_START, key="card", max_points=CARD), _item(world.young, ALL_START, sample_like="nope")]
    error = await _refused_for_reference(lambda: _query(world.engine, *items))
    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        refused = await _route_refusal(lambda: price_routes.query_prices_bulk(requests=items, session=session, _current_user=None))
    assert refused.status_code == 422, f"{refused.status_code}: {refused.detail!r}"
    assert refused.detail == _sampling().sample_reference_detail(error), refused.detail
    assert (refused.detail["code"], refused.detail["reason"], refused.detail["item"]) == ("sample_reference", "unknown_key", 1)


# ── point 11: one read per asset ──────────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fields", "step"),
    [
        pytest.param({"max_points": CARD}, "weekly", id="on-a-card"),
        pytest.param({"resolution": "monthly"}, "monthly", id="asking-monthly"),
        pytest.param({"sample_like": "card"}, "monthly", id="following-olds-card"),
    ],
)
async def test_pqs_q22_an_asset_read_whole_serves_its_samples(world, frozen_ceiling, fields, step):
    """PQS-Q22: YOUNG daily on «All», beside YOUNG sampled on the same range — on a card (weekly), asking monthly, or
    following OLD's card (monthly) — and OLD on a card (monthly, keyed ``card``): YOUNG's whole daily read serves its
    sample, and no bucket statement reads YOUNG; YOUNG's sample is the one it gets without the daily item, and OLD's
    answer too. Statements are seen by a ``before_cursor_execute`` listener (``_is_bucket_statement``,
    ``_names_asset``). Its presence barriers: without the daily item a bucket statement reads YOUNG; with it, one reads
    OLD, sampled only — the listener sees bucket statements and the assets in them.

    Red before Z-29a: an item with ``max_points``, ``resolution``, ``key`` or ``sample_like`` cannot be built, an extra
    field.
    """
    card = _item(world.old, ALL_START, key="card", max_points=CARD)
    sampled = _item(world.young, ALL_START, **fields)
    expected = _expected_all(world, [card, sampled])
    assert [plan.step for plan in expected] == ["monthly", step], "premise"
    with _recording_statements(world.engine) as apart_said:
        apart = await _query(world.engine, card, sampled)
    with _recording_statements(world.engine) as together_said:
        together = await _query(world.engine, _item(world.young, ALL_START), card, sampled)
    apart_groups, together_groups = _bucket_groups(apart_said, world), _bucket_groups(together_said, world)
    assert any("young" in group for group in apart_groups), f"barrier: sampled without a daily item, YOUNG is read by no bucket statement the matcher sees (bucket statements: {apart_groups}); the statements: {_said(apart_said)}"
    assert any("old" in group for group in together_groups), f"barrier: OLD, sampled only, is read by no bucket statement the matcher sees (bucket statements: {together_groups}); the statements: {_said(together_said)}"
    assert not [group for group in together_groups if "young" in group], f"YOUNG, read whole by a daily item, is read again by a bucket statement: {together_groups}; the statements: {_said(together_said)}"
    assert (together[2].resolution, _dates(together[2])) == (step, expected[1].dates)
    assert _same(together[2], apart[1]), "YOUNG's sample differs once its daily read serves it"
    assert _same(together[1], apart[0]), "OLD's sample differs beside YOUNG's daily item"
    assert _dates(together[0]) == _days(date(2020, 3, 2), CEILING)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("spec", "groups"),
    [
        pytest.param((("old", {"resolution": "monthly"}), ("young", {"resolution": "monthly"}), ("recent", {"resolution": "monthly"})), [{"old", "young", "recent"}], id="three-assets-one-step"),
        pytest.param((("old", {"max_points": CARD}), ("young", {"max_points": CARD})), [{"old"}, {"young"}], id="two-steps"),
        pytest.param((("old", {"key": "card", "max_points": CARD}), ("young", {"sample_like": "card"})), [{"old", "young"}], id="a-card-and-its-target-one-step"),
    ],
)
async def test_pqs_q23_one_bucket_statement_per_range_and_step(world, frozen_ceiling, spec, groups):
    """PQS-Q23: the assets a request reads only sampled are read by one bucket statement per (range, step), every asset
    of that group in it: OLD, YOUNG and RECENT asking monthly on «All», one statement reading the three; OLD and YOUNG
    on a card (monthly and weekly), two, one each; a card on OLD and YOUNG following it (both monthly), one reading both.
    Each request is answered with its samples. Statements are seen by a ``before_cursor_execute`` listener
    (``_is_bucket_statement``, ``_names_asset``); the exact groups are the presence barrier — no bucket statement seen
    fails them as surely as one too many.

    Red before Z-29a: an item with ``max_points``, ``resolution``, ``key`` or ``sample_like`` cannot be built, an extra
    field.
    """
    items = [_item(getattr(world, name), ALL_START, **fields) for name, fields in spec]
    expected = _expected_all(world, items)
    with _recording_statements(world.engine) as said:
        results = await _query(world.engine, *items)
    assert [_dates(result) for result in results] == [plan.dates for plan in expected]
    found = sorted(sorted(group) for group in _bucket_groups(said, world))
    assert found == sorted(sorted(group) for group in groups), f"bucket statements reading {found}, not {sorted(sorted(group) for group in groups)}; the statements: {_said(said)}"


# ── point 14: a placeholder, sampled without its prices (Z-29a-f) ─────────────────────────────────────────────────

_DAILY_LOAD = re.compile(r"\bFROM\s+price_history\b.*?\bprice_history\.asset_id\s+IN\s*\(", re.IGNORECASE | re.DOTALL)
_LIMIT = re.compile(r"\bLIMIT\b", re.IGNORECASE)


def _is_daily_load(statement: _Statement) -> bool:
    """The day-by-day read of ``get_prices_bulk``: the statement that selects the ``price_history`` rows of the assets it
    lists, ``price_history.asset_id IN (…)``, every row of the range — not grouped per bucket (``_is_bucket_statement``)
    and not cut to one row by a ``LIMIT``, as the seed and the plan's probes are (they name one asset,
    ``price_history.asset_id = …``, or rows by their id)."""
    sql = statement.sql
    return _DAILY_LOAD.search(sql) is not None and _LIMIT.search(sql) is None and not _is_bucket_statement(statement)


def _reads_naming(statements: list[_Statement], asset_id: int) -> list[str]:
    """The reads of an asset's price rows past a plan's probes, in order: ``bucket`` for each bucket statement that names
    it, ``daily`` for each day-by-day read that lists it."""
    reads = [statement for statement in statements if _is_bucket_statement(statement) or _is_daily_load(statement)]
    return ["bucket" if _is_bucket_statement(statement) else "daily" for statement in reads if _names_asset(statement, asset_id)]


def _read_kind(step: str) -> str:
    """How an item at this step is read when it carries its prices: daily, by the day-by-day read; weekly or monthly, its
    asset only sampled, by a bucket statement."""
    return "daily" if step == "daily" else "bucket"


def _priced(item: FAPriceQueryItem) -> FAPriceQueryItem:
    """The same item sent with its prices: a placeholder's counterpart, read and counted as Z-29a reads and counts it."""
    return FAPriceQueryItem.model_validate({**item.model_dump(), "include_price": True})


def _counted(plan: _Expected) -> int:
    """What an item of this plan counts against the day budget when it carries its prices (point 10): weekly or monthly,
    its points and its two bounds; daily, its fill days."""
    return len(plan.dates) + (0 if plan.step == "daily" else 2)


def _assert_placeholder(result: FAPriceQueryResult, asset_id: int, step: str) -> None:
    """A placeholder's answer: its asset, its plan's step in ``resolution``, no point, no bounds, no error, event or
    signal."""
    said = (result.asset_id, result.resolution, len(result.prices), result.sample_bounds, result.errors, result.events, result.signals)
    expected = (asset_id, step, 0, None, [], [], [])
    assert said == expected, f"the placeholder answers (asset, resolution, points, bounds, errors, events, signals) {said}, not {expected}"


async def _answered_within_budget(make_call: Callable[[], Awaitable[list[FAPriceQueryResult]]]) -> list[FAPriceQueryResult]:
    """The answer of a call the day budget must let through; refused, the test fails saying what was counted."""
    try:
        return await make_call()
    except BulkTooManyDaysError as refusal:
        pytest.fail(f"refused for its days: item_days {refusal.item_days:,} over a budget of {refusal.max_item_days:,}")


#: A placeholder alone on «All», of each kind, the step of its plan and its count of dates: YOUNG on a card, weekly (346
#: points); OLD on a card, monthly (322); RECENT asking weekly (41); YOUNG asking monthly (80); daily, RECENT on a card
#: (its 286 days within 377 points) and YOUNG asking it (2 421 days).
_LONE_PLACEHOLDERS = [
    pytest.param("young", {"max_points": CARD}, "weekly", 346, id="weekly-on-a-card"),
    pytest.param("old", {"max_points": CARD}, "monthly", 322, id="monthly-on-a-card"),
    pytest.param("recent", {"resolution": "weekly"}, "weekly", 41, id="weekly-asked"),
    pytest.param("young", {"resolution": "monthly"}, "monthly", 80, id="monthly-asked"),
    pytest.param("recent", {"max_points": CARD}, "daily", 286, id="daily-its-days-within-max-points"),
    pytest.param("young", {"resolution": "daily"}, "daily", 2421, id="daily-asked"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("asset", "fields", "step", "points"), _LONE_PLACEHOLDERS)
async def test_pqs_q24_a_placeholder_alone_reads_no_price_row_past_its_plan(world, frozen_ceiling, asset, fields, step, points):
    """PQS-Q24: a placeholder alone on «All» reads no price row past its plan, whatever its step: YOUNG on a card
    (weekly, 346 points), OLD on a card (monthly, 322), RECENT asking weekly (41), YOUNG asking monthly (80); daily,
    RECENT on a card (its 286 days within 377 points) and YOUNG asking daily (2 421 days). It answers its plan's step in
    ``resolution``, no point, no bounds, no error; no bucket statement runs, nor the day-by-day read
    (``_is_daily_load``); the ORM loads at most 2 price rows, the seed and the first row in the range ``_plan_samples``
    probes. Statements are seen by a ``before_cursor_execute`` listener, rows by a ``load`` listener. Their presence
    barrier: the same item with its prices answers its points, a bucket statement (weekly, monthly) or the day-by-day
    read (daily) names its asset, and more than 2 of its rows are loaded — the reads are made where the listeners look.

    Red before Z-29a-f: the placeholder is read as the same item with its prices is, by a bucket statement or by the
    day-by-day read, more than 2 of its rows loaded. Its answer is green then, by construction (the last pass of
    ``get_prices_bulk`` drops the points and the bounds of an item without its prices): asserted first, so the red is
    the reads'.
    """
    placeholder = _item(getattr(world, asset), ALL_START, include_price=False, **fields)
    plan = _expected(world, placeholder)
    assert (plan.step, len(plan.dates)) == (step, points), "premise"
    with _recording_statements(world.engine) as priced_said, _counting_loads() as priced_loads:
        (priced,) = await _query(world.engine, _priced(placeholder))
    assert (priced.resolution, _dates(priced)) == (step, plan.dates), f"premise: with its prices the item says {priced.resolution!r}; {_first_difference(_dates(priced), plan.dates)}"
    assert _read_kind(step) in _reads_naming(priced_said, placeholder.asset_id), f"barrier: with its prices, the item is read by no {_read_kind(step)} statement the matchers see; the statements: {_said(priced_said)}"
    assert priced_loads[placeholder.asset_id] > 2, f"barrier: with its prices, the listener saw {priced_loads[placeholder.asset_id]} of its rows loaded, not more than 2: the bound below would prove nothing"
    with _recording_statements(world.engine) as said, _counting_loads() as loads:
        (result,) = await _query(world.engine, placeholder)
    _assert_placeholder(result, placeholder.asset_id, step)
    reads = [statement for statement in said if _is_bucket_statement(statement) or _is_daily_load(statement)]
    assert not reads, f"a placeholder alone ran {len(reads)} bucket statement(s) or day-by-day read(s): {_said(reads)}"
    assert sum(loads.values()) <= 2, f"a placeholder alone loaded {dict(loads)} price rows (asset id: rows), more than the seed and the first row in the range its plan probes"


#: A placeholder on «All» beside a daily item and a card (``key`` card, on a card) that carry their prices, each on an
#: asset of its own: the placeholder's asset, its fields and the step of its plan; the daily item's asset; the card's
#: (OLD's monthly, YOUNG's weekly).
_PLACEHOLDERS_AMONG = [
    pytest.param("young", {"max_points": CARD}, "weekly", "recent", "old", id="weekly-on-a-card"),
    pytest.param("recent", {"resolution": "monthly"}, "monthly", "young", "old", id="monthly-asked-the-cards-step"),
    pytest.param("recent", {"sample_like": "card"}, "monthly", "young", "old", id="monthly-following-the-card"),
    pytest.param("recent", {"max_points": CARD}, "daily", "young", "old", id="daily-its-days-within-max-points"),
    pytest.param("old", {"resolution": "daily"}, "daily", "recent", "young", id="daily-asked"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("asset", "fields", "step", "daily_asset", "card_asset"), _PLACEHOLDERS_AMONG)
async def test_pqs_q25_beside_items_with_prices_no_statement_reads_the_placeholder(world, frozen_ceiling, asset, fields, step, daily_asset, card_asset):
    """PQS-Q25: beside a daily item and a card that carry their prices, each on an asset of its own, a placeholder is read
    by no statement past its plan: the card's bucket statement — even when the placeholder asks the card's step on the
    same range, or follows the card — and the day-by-day read that lists the daily item's asset leave the placeholder's
    asset out, and the ORM loads at most 2 of its rows. On «All»: YOUNG on a card (weekly) beside RECENT daily and OLD's
    card (monthly); RECENT asking monthly, following OLD's card (monthly from its own first row, 2026-01-05) or on a
    card (daily, its 286 days within 377 points), each beside YOUNG daily and OLD's card; OLD asking daily beside RECENT
    daily and YOUNG's card (weekly). The placeholder answers its plan's step, no point, no bounds, no error; the two
    others answer as they do without it. Presence barriers: in the same request the day-by-day read lists the daily
    item's asset and a bucket statement names the card's; with its prices, the placeholder's asset is read too (a bucket
    statement; the day-by-day read when daily) and more than 2 of its rows are loaded.

    Red before Z-29a-f: the placeholder's asset is named by a bucket statement — the card's own when they share a range
    and a step — or listed by the day-by-day read, more than 2 of its rows loaded. The answers are green then.
    """
    daily_item = _item(getattr(world, daily_asset), ALL_START)
    card = _item(getattr(world, card_asset), ALL_START, key="card", max_points=CARD)
    placeholder = _item(getattr(world, asset), ALL_START, include_price=False, **fields)
    expected = _expected_all(world, [daily_item, card, placeholder])
    assert ([_read_kind(plan.step) for plan in expected], expected[2].step, bool(expected[2].dates)) == (["daily", "bucket", _read_kind(step)], step, True), "premise"
    with _recording_statements(world.engine) as priced_said, _counting_loads() as priced_loads:
        await _query(world.engine, daily_item, card, _priced(placeholder))
    assert _read_kind(step) in _reads_naming(priced_said, placeholder.asset_id), f"barrier: with its prices, the {step} item is read by no {_read_kind(step)} statement the matchers see; the statements: {_said(priced_said)}"
    assert priced_loads[placeholder.asset_id] > 2, f"barrier: with its prices, the listener saw {priced_loads[placeholder.asset_id]} of its rows loaded, not more than 2: the bound below would prove nothing"
    with _recording_statements(world.engine) as said, _counting_loads() as loads:
        results = await _query(world.engine, daily_item, card, placeholder)
    others = ("daily" in _reads_naming(said, daily_item.asset_id), "bucket" in _reads_naming(said, card.asset_id))
    assert others == (True, True), f"barrier: (the daily item's asset listed by the day-by-day read, the card's named by a bucket statement) is {others}; the statements: {_said(said)}"
    assert _reads_naming(said, placeholder.asset_id) == [], f"the placeholder's asset is read: {_reads_naming(said, placeholder.asset_id)}; the statements: {_said(said)}"
    assert loads[placeholder.asset_id] <= 2, f"{loads[placeholder.asset_id]} of the placeholder's price rows loaded, more than the seed and the first row in the range its plan probes"
    _assert_placeholder(results[2], placeholder.asset_id, step)
    alone = await _query(world.engine, daily_item, card)
    assert [_same(result, other) for result, other in zip(results[:2], alone, strict=True)] == [True, True], "the daily item or the card answers otherwise beside the placeholder"


@pytest.mark.asyncio
@pytest.mark.parametrize(("asset", "fields", "step", "points"), _LONE_PLACEHOLDERS)
async def test_pqs_q26_a_placeholder_alone_passes_a_budget_of_zero(world, frozen_ceiling, monkeypatch, asset, fields, step, points):
    """PQS-Q26: a placeholder counts nothing against the day budget: alone, each placeholder of PQS-Q24 is answered under
    a budget of 0 (``MAX_BULK_ITEM_DAYS`` lowered through ``price_query``, which refuses a count above it) — its plan's
    step in ``resolution``, no point, no bounds, no error. The barrier: under the same 0, the same item with its prices
    is refused with ``item_days`` its points and its two bounds (weekly, monthly) or its fill days (daily) — the budget
    is applied where it is lowered, and the item counts there when it carries its prices.

    Red before Z-29a-f: refused under 0 — the placeholder counts as with its prices: 348, 324, 43, 82, 286 and 2 421.
    """
    placeholder = _item(getattr(world, asset), ALL_START, include_price=False, **fields)
    plan = _expected(world, placeholder)
    assert (plan.step, len(plan.dates)) == (step, points), "premise"
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", 0)
    refusal = await _refused_for_days(lambda: _query(world.engine, _priced(placeholder)))
    assert (refusal.item_days, refusal.max_item_days) == (_counted(plan), 0), f"barrier: with its prices the item is refused with item_days {refusal.item_days}, not {_counted(plan)}"
    (result,) = await _answered_within_budget(lambda: _query(world.engine, placeholder))
    _assert_placeholder(result, placeholder.asset_id, step)


#: A placeholder on RECENT, on «All», and the step of its plan: weekly chosen (in 100 points: its 41 weeks fit, its 286
#: days do not), monthly asked, monthly following OLD's card (from RECENT's first row), daily within a card's 377
#: points, daily asked.
_PLACEHOLDERS_ON_RECENT = [
    pytest.param({"max_points": 100}, "weekly", id="weekly-chosen"),
    pytest.param({"resolution": "monthly"}, "monthly", id="monthly-asked"),
    pytest.param({"sample_like": "card"}, "monthly", id="monthly-following-the-card"),
    pytest.param({"max_points": CARD}, "daily", id="daily-its-days-within-max-points"),
    pytest.param({"resolution": "daily"}, "daily", id="daily-asked"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("fields", "step"), _PLACEHOLDERS_ON_RECENT)
async def test_pqs_q27_beside_items_that_fit_a_placeholder_counts_nothing(world, frozen_ceiling, monkeypatch, fields, step):
    """PQS-Q27: beside items that fit, a placeholder adds nothing to the count. PQS-Q10's request — YOUNG daily from
    2026-01-01, seeded (290 days), and OLD on «All» on a card (monthly, 322 points and 2 bounds; keyed ``card``), 614 —
    with a placeholder on RECENT on «All»: weekly chosen (in 100 points: its 41 weeks fit, its 286 days do not), monthly
    asked, monthly following OLD's card, daily within 377 points, daily asked. Under a budget of 614, the others' exact
    total, the request is answered: the two others as without the placeholder, the placeholder with its plan's step, no
    point, no bounds, no error. Under 613, ``BulkTooManyDaysError`` with ``item_days`` 614 — the others' count to the
    unit, the placeholder's nothing; that refusal is also the barrier: the budget is applied where it is lowered.

    Red before Z-29a-f: refused under 614 — the placeholder counts too: 43, 12, 12, 286 and 286 more.
    """
    others = [_item(world.young, date(2026, 1, 1)), _item(world.old, ALL_START, key="card", max_points=CARD)]
    placeholder = _item(world.recent, ALL_START, include_price=False, **fields)
    items = [*others, placeholder]
    expected = _expected_all(world, items)
    total = sum(_counted(plan) for plan in expected[:2])
    assert ([plan.step for plan in expected], total, bool(expected[2].dates)) == (["daily", "monthly", step], 614, True), "premise"
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", total)
    answered = await _answered_within_budget(lambda: _query(world.engine, *items))
    alone = await _query(world.engine, *others)
    assert [_dates(result) for result in answered[:2]] == [plan.dates for plan in expected[:2]]
    assert [_same(result, other) for result, other in zip(answered[:2], alone, strict=True)] == [True, True], "the daily item or the card answers otherwise beside the placeholder"
    _assert_placeholder(answered[2], world.recent, step)
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", total - 1)
    refusal = await _refused_for_days(lambda: _query(world.engine, *items))
    assert (refusal.item_days, refusal.max_item_days) == (total, total - 1), f"refused with item_days {refusal.item_days}: the placeholder counted {refusal.item_days - total}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("card_asset", "target_asset", "step", "first", "points", "counted"),
    [
        pytest.param("old", "young", "monthly", date(2020, 3, 2), 80, 82, id="a-monthly-card"),
        pytest.param("recent", "old", "daily", date(2026, 1, 5), 286, 286, id="a-daily-card"),
    ],
)
async def test_pqs_q28_a_placeholder_card_leads_its_target_on_the_targets_own_budget(world, frozen_ceiling, monkeypatch, card_asset, target_asset, step, first, points, counted):
    """PQS-Q28: the comparison dialog's request (Z-29d): a card sent as a placeholder (``key`` card, on a card,
    ``include_price=False``) and its target (``sample_like`` card, with its prices), both on «All». The target follows
    the card's step from the later first day exactly as beside the card sent with prices (PQS-Q18's last case), every
    point and bound its own daily answer's: YOUNG on OLD's card, monthly from its own first row 2020-03-02 (80 points);
    OLD on RECENT's card, daily from RECENT's first row 2026-01-05 (286 days). The request passes a budget of the
    target's own count — its points and its two bounds, 82; its fill days, 286 — and is refused under one less with
    ``item_days`` that count: the card adds nothing. The card answers its plan's step (monthly, daily), no point, no
    bounds, no error; no bucket statement names its asset, the day-by-day read does not list it, the ORM loads at most 2
    of its rows. Presence barriers: the target is read in the same request (a bucket statement; the day-by-day read);
    with its prices, the card's asset is read too.

    Red before Z-29a-f: refused under the target's own count — the card counts too, 324 (its monthly points and bounds)
    or 286 (its fill days). The answers, under the default budget, are green then (PQS-Q18).
    """
    card = _item(getattr(world, card_asset), ALL_START, key="card", max_points=CARD, include_price=False)
    target = _item(getattr(world, target_asset), ALL_START, sample_like="card")
    expected = _expected_like(world, target, card)
    assert (_expected(world, card).step, expected.step, expected.first, len(expected.dates), _counted(expected)) == (step, step, first, points, counted), "premise"
    with _recording_statements(world.engine) as priced_said:
        _card_priced, led = await _query(world.engine, _priced(card), target)
    (target_daily,) = await _query(world.engine, _daily(target))
    assert _read_kind(step) in _reads_naming(priced_said, card.asset_id), f"barrier: with its prices, the card is read by no {_read_kind(step)} statement the matchers see; the statements: {_said(priced_said)}"
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", counted)
    with _recording_statements(world.engine) as said, _counting_loads() as loads:
        card_answer, target_answer = await _answered_within_budget(lambda: _query(world.engine, card, target))
    _assert_placeholder(card_answer, card.asset_id, step)
    _assert_sample_of_daily(target_answer, target_daily, expected)
    assert _same(target_answer, led), "the target differs from its answer beside the card sent with prices"
    assert _read_kind(step) in _reads_naming(said, target.asset_id), f"barrier: the target is read by no {_read_kind(step)} statement the matchers see; the statements: {_said(said)}"
    assert _reads_naming(said, card.asset_id) == [], f"the placeholder card's asset is read: {_reads_naming(said, card.asset_id)}; the statements: {_said(said)}"
    assert loads[card.asset_id] <= 2, f"{loads[card.asset_id]} of the placeholder card's price rows loaded, more than the seed and the first row in the range its plan probes"
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", counted - 1)
    refusal = await _refused_for_days(lambda: _query(world.engine, card, target))
    assert (refusal.item_days, refusal.max_item_days) == (counted, counted - 1), f"refused with item_days {refusal.item_days}: the card counted {refusal.item_days - counted}"


# ── point 15: signals on a sample (Z-29s-a) ───────────────────────────────────────────────────────────────────────

#: WAVE, an asset of this block alone (``signal_world``): a close on every weekday from Monday 2025-01-06 to FROZEN_TODAY,
#: going up and down (100 + 7n mod 11, plus n / 100), so that a drawdown has troughs and a week's lowest or highest point
#: is rarely its first or last. Its id, as the world's, is no date, format or bound of a price statement.
WAVE_ID = 9505
WAVE_FIRST = date(2025, 1, 6)
#: WAVE's range in most cases: from Sunday 2026-03-01, rows before it (the fill seeded), to the ceiling — 231 days, 34
#: ISO weeks (the first closed by that Sunday), 8 months.
WAVE_START = date(2026, 3, 1)
#: The signals asked, real plugins: a line (EMA), a band (BOLLINGER), two lines and a bar (MACD, its histogram the bar),
#: an area reduced by its minimum (RISK_DRAWDOWN, on the full history), a line whose points carry a provenance
#: (ASSET_CALENDAR_ROLLING_RETURN).
SG_EMA = {"instance_id": "ema5", "signal_code": "EMA", "params": {"period": 5}}
SG_BANDS = {"instance_id": "bands5", "signal_code": "BOLLINGER", "params": {"period": 5, "multiplier": 2.0}}
SG_MACD = {"instance_id": "macd363", "signal_code": "MACD", "params": {"fast_period": 3, "slow_period": 6, "signal_period": 3}}
#: An ADX whose two directional lines are valued from the fourth session, in the first week, and whose ADX from the
#: seventh, in the second (PQS-SG06, O1).
SG_ADX = {"instance_id": "adx3", "signal_code": "ADX", "params": {"period": 3}}
SG_DRAWDOWN = {"instance_id": "drawdown", "signal_code": "RISK_DRAWDOWN", "params": {"full_history": True}}
SG_RETURN = {"instance_id": "return7", "signal_code": "ASSET_CALENDAR_ROLLING_RETURN", "params": {"window_days": 7}}
SG_ALL = [SG_EMA, SG_BANDS, SG_MACD, SG_DRAWDOWN, SG_RETURN]
#: Each output's aggregation_profile, by (signal code, series key), as the plugins declare it: written here and checked
#: against their output_specs (``_assert_profiles``), not read from the code under test.
SG_PROFILES = {
    ("EMA", "ema"): "last_with_range",
    ("BOLLINGER", "bands"): "band_envelope",
    ("MACD", "macd"): "last_with_range",
    ("MACD", "signal"): "last_with_range",
    ("MACD", "histogram"): "last_with_range",
    ("ADX", "adx"): "last_with_range",
    ("ADX", "plus_di"): "last_with_range",
    ("ADX", "minus_di"): "last_with_range",
    ("RISK_DRAWDOWN", "drawdown"): "min_with_range",
    ("ASSET_CALENDAR_ROLLING_RETURN", "calendar_return"): "last_with_range",
}


def _wave_row(day: date, n: int) -> dict:
    """WAVE's ``n``-th row: ``_price_row``'s, its close going up and down, open, high and low around it."""
    close = Decimal(100 + (7 * n) % 11) + Decimal(n) / 100
    return {**_price_row(WAVE_ID, day, n, 100), "open": close - 1, "high": close + 2, "low": close - 2, "close": close}


@pytest_asyncio.fixture
async def signal_world(world: _World, monkeypatch: pytest.MonkeyPatch) -> _World:
    """``world`` with WAVE (``WAVE_ID``, its weekday closes from ``WAVE_FIRST``, its days in ``stored``), and the market
    holiday table empty where the price query reads it: no row of the file is a weekend or holiday repeat, so the table
    changes nothing, and no QuantLib build process is spawned (``test_range_ceiling.py`` and ``test_bulk_limits.py`` do
    the same)."""
    days = _weekdays(WAVE_FIRST, ())
    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        session.add(Asset(id=WAVE_ID, display_name=f"Z-29s wave {uuid.uuid4().hex[:8]}", currency="EUR", asset_type=AssetType.STOCK))
        await session.flush()
        await session.execute(insert(PriceHistory), [_wave_row(day, n) for n, day in enumerate(days)])
        await session.commit()
    world.stored[WAVE_ID] = frozenset(days)

    async def _no_market_holidays() -> frozenset[date]:
        return frozenset()

    monkeypatch.setattr(price_query, "ensure_market_holidays", _no_market_holidays)
    return world


def _asset_of(world: _World, name: str) -> int:
    """An asset by name: one of the world's, or WAVE."""
    return WAVE_ID if name == "wave" else getattr(world, name)


def _signal_item(asset_id: int, start: date, end: date = FAR_END, **extra: Any) -> FAPriceQueryItem:
    """``_item`` for an item with signals and a sampling field: while ``validate_sampling`` refuses the pair (before
    Z-29s-a), the test fails saying so, not on the ``ValidationError``."""
    try:
        return _item(asset_id, start, end, **extra)
    except ValidationError as refusal:
        asked = [name for name in SAMPLE_FIELDS if extra.get(name) is not None]
        pytest.fail(f"Z-29s-a: FAPriceQueryItem refuses signals with {' and '.join(asked)}: {[error['msg'] for error in refusal.errors()]}")


def _signal_sampler() -> Callable[..., Any]:
    """``aggregation.sample_signal_series``, read at the call: while it is missing, the test asking it fails saying so."""
    sample = getattr(signal_aggregation, "sample_signal_series", None)
    if sample is None:
        pytest.fail("Z-29s-a: backend.app.services.signals.aggregation.sample_signal_series is missing — sample_signal_series(series, profile, resolution, render_dates)")
    return sample


def _without_clock(dumped: Any) -> Any:
    """A dump without its ``computed_at``: a risk signal's ``risk_metadata`` says when it was computed, so two
    computations of the same series differ there, and only there."""
    if isinstance(dumped, dict):
        return {key: _without_clock(value) for key, value in dumped.items() if key != "computed_at"}
    if isinstance(dumped, list):
        return [_without_clock(value) for value in dumped]
    return dumped


def _same_but_the_clock(left: FAPriceQueryResult, right: FAPriceQueryResult) -> bool:
    """Two answers equal as the wire writes them, ``computed_at`` aside."""
    return _without_clock(left.model_dump(mode="json")) == _without_clock(right.model_dump(mode="json"))


def _bounds_json(result: FAPriceQueryResult) -> dict | None:
    return None if result.sample_bounds is None else result.sample_bounds.model_dump(mode="json")


def _signals_by_id(answer: FAPriceQueryResult) -> dict[str, SignalResult]:
    return {result.instance_id: result for result in answer.signals}


def _inner_gap(series: Any) -> bool:
    """Whether a scalar series holds a point without value between two with one: a gap the reduction would mark."""
    valued = [point.value is not None for point in series.points]
    if True not in valued:
        return False
    first, last = valued.index(True), len(valued) - 1 - valued[::-1].index(True)
    return not all(valued[first : last + 1])


def _assert_computed(answer: FAPriceQueryResult, requests: list[dict]) -> None:
    """Premise: the daily answer computed every signal asked — ok or partial, with series —, no line or area of it with
    an inner gap: each is one run, which ``_ref_reduction`` walks."""
    results = _signals_by_id(answer)
    assert sorted(results) == sorted(request["instance_id"] for request in requests), f"premise: the daily answer's signals are {sorted(results)}"
    failed = {instance: (result.status.value, result.error, result.availability.reason_code if result.availability else None) for instance, result in results.items() if result.status.value not in ("ok", "partial") or not result.series}
    assert not failed, f"premise: signals not computed on the daily answer: {failed}"
    gaps = [f"{instance}.{series.key}" for instance, result in results.items() for series in result.series if series.kind in ("line", "area") and _inner_gap(series)]
    assert not gaps, f"premise: lines or areas with an inner gap on the daily answer: {gaps}"


def _assert_profiles() -> None:
    """Premise: each output's aggregation_profile is the one ``SG_PROFILES`` writes — the plugins' own declarations."""
    codes = sorted({code for code, _key in SG_PROFILES})
    declared = {(code, spec.key): spec.aggregation_profile.value for code in codes for spec in SignalPluginRegistry.get_plugin(code).output_specs}
    assert declared == SG_PROFILES, f"premise: the plugins declare {declared}"


def _ref_reduction(series: Any, profile: str, step: str, render_dates: list[date]) -> list[dict]:
    """What point 15 gives a daily series without an inner gap on these render dates, walked here: per render date, in
    order, the point the profile picks among the series' points of that date's bucket — a scalar's points with a value
    (the first, the last, the earliest smallest or largest), a band's complete points (the lowest lower, the last
    middle, the highest upper) — re-dated at the render date, as the wire writes it (a calendar-return point with its
    provenance); a bucket without such a point gives none, a point of a bucket without a render date none."""
    band = isinstance(series, SignalBandSeries)
    by_bucket: dict[tuple[date, date], list] = collections.defaultdict(list)
    for point in sorted(series.points, key=lambda point: point.date):
        if (None not in (point.lower, point.middle, point.upper)) if band else point.value is not None:
            by_bucket[_ref_bucket(point.date, step)].append(point)
    reduced = []
    for day in render_dates:
        points = by_bucket.get(_ref_bucket(day, step))
        if not points:
            continue
        if band:
            reduced.append({"date": day.isoformat(), "lower": min(point.lower for point in points), "middle": points[-1].middle, "upper": max(point.upper for point in points)})
            continue
        picks = {"first_with_range": points[0], "last_with_range": points[-1], "min_with_range": min(points, key=lambda point: point.value), "max_with_range": max(points, key=lambda point: point.value)}
        reduced.append(picks[profile].model_copy(update={"date": day}).model_dump(mode="json"))
    return reduced


def _first_mismatch(got: list[dict], expected: list[dict]) -> str:
    at = next((n for n, (left, right) in enumerate(zip(got, expected, strict=False)) if left != right), min(len(got), len(expected)))
    return f"{len(got)} points for {len(expected)}; from position {at}: {got[at : at + 2]} instead of {expected[at : at + 2]}"


def _ref_empty(day: date, band: bool) -> dict:
    """The point a series has, without a value, on a date only another series of its signal reduced to (O1)."""
    return {"date": day.isoformat(), "lower": None, "middle": None, "upper": None} if band else {"date": day.isoformat(), "value": None}


def _assert_signals_reduced(sampled: FAPriceQueryResult, daily: FAPriceQueryResult, step: str, render_dates: list[date]) -> None:
    """Each signal result of ``sampled`` is the daily answer's but for its series (``computed_at`` aside), and each of its
    series is reduced: walked apart (``_ref_reduction``), the point its output's profile picks in each bucket re-dated at
    the bucket's render date, then on the dates of all the signal's series (O1: the union of the dates the reductions
    leave, a point without a value where a series has none, so that ``SignalResult`` accepts them), every point on one
    of ``render_dates``; and, but for those points without a value, it is ``sample_signal_series`` of the daily series
    with that profile, ``step`` and ``render_dates``."""
    daily_results = _signals_by_id(daily)
    assert sorted(_signals_by_id(sampled)) == sorted(daily_results), f"the signals {sorted(_signals_by_id(sampled))} for {sorted(daily_results)}"
    for result in sampled.signals:
        reference = daily_results[result.instance_id]
        assert _without_clock(result.model_dump(mode="json", exclude={"series"})) == _without_clock(reference.model_dump(mode="json", exclude={"series"})), f"{result.instance_id}: the result differs from the daily one beyond its series"
        assert [(series.kind, series.key) for series in result.series] == [(series.kind, series.key) for series in reference.series], result.instance_id
        walked = {series.key: _ref_reduction(daily_series, SG_PROFILES[(result.signal_code, series.key)], step, render_dates) for series, daily_series in zip(result.series, reference.series, strict=True)}
        union = sorted({point["date"] for points in walked.values() for point in points})
        _validate_series_alignment(result.series)
        for series, daily_series in zip(result.series, reference.series, strict=True):
            profile = SG_PROFILES[(result.signal_code, series.key)]
            label = f"{result.instance_id}.{series.key} ({profile}, {step})"
            own = {point["date"]: point for point in walked[series.key]}
            expected = [own.get(day) or _ref_empty(date.fromisoformat(day), series.kind == "band") for day in union]
            assert walked[series.key], f"premise: {label} has no point in the plan's buckets"
            got = [point.model_dump(mode="json") for point in series.points]
            assert got == expected, f"{label}: {_first_mismatch(got, expected)}"
            assert {point.date for point in series.points} <= set(render_dates), f"{label}: points off the plan's dates"
            reduced = _signal_sampler()(daily_series, SignalAggregationProfile(profile), step, list(render_dates)).model_dump(mode="json")
            assert [point for point in got if point["date"] in own] == reduced["points"], f"{label}: not sample_signal_series of the daily series"
            assert series.model_dump(mode="json", exclude={"points"}) == {key: value for key, value in reduced.items() if key != "points"}, f"{label}: a field other than the points changed"


#: Items with signals on a sample, each asset on its range, how it asks its step, the step and its count of dates: WAVE
#: on a card's 60 points (its 34 weeks fit, its 231 days do not) and asking monthly (8 months); OLD on «All» on a card,
#: monthly (322 months), its March 2010 and a week of 2015 without a quote.
_SG_SAMPLES = [
    pytest.param("wave", WAVE_START, {"max_points": 60}, "weekly", 34, id="wave-weekly-on-a-card"),
    pytest.param("wave", WAVE_START, {"resolution": "monthly"}, "monthly", 8, id="wave-monthly-asked"),
    pytest.param("old", ALL_START, {"max_points": CARD}, "monthly", 322, id="old-all-monthly-on-a-card"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("asset", "start", "fields", "step", "count"), _SG_SAMPLES)
async def test_pqs_sg01_signals_leave_the_samples_prices_bounds_and_step(signal_world, frozen_ceiling, asset, start, fields, step, count):
    """PQS-SG01: an item with ``max_points`` or ``resolution`` and five real signals (EMA, BOLLINGER, MACD, RISK_DRAWDOWN,
    ASSET_CALENDAR_ROLLING_RETURN) says the step and carries the prices and the bounds of the same item without signals,
    as the wire writes them: the plan's dates, no event, no error — and its signals, the five asked. WAVE weekly on a
    card and monthly asked; OLD on «All» monthly on a card.

    Red before Z-29s-a: an item with signals and a sampling field cannot be built (``validate_sampling``).
    """
    asset_id = _asset_of(signal_world, asset)
    plain = _item(asset_id, start, **fields)
    expected = _expected(signal_world, plain)
    assert (expected.step, len(expected.dates)) == (step, count), "premise"
    (plain_answer,) = await _query(signal_world.engine, plain)
    assert (plain_answer.resolution, _dates(plain_answer), plain_answer.sample_bounds is not None) == (step, expected.dates, True), "premise: the sample without signals"
    (sampled,) = await _query(signal_world.engine, _signal_item(asset_id, start, signals=SG_ALL, **fields))
    assert (sampled.resolution, _dates(sampled)) == (step, expected.dates), f"{sampled.resolution!r}; {_first_difference(_dates(sampled), expected.dates)}"
    differing = [(left.date, left.model_dump(mode="json"), right.model_dump(mode="json")) for left, right in zip(sampled.prices, plain_answer.prices, strict=True) if left.model_dump(mode="json") != right.model_dump(mode="json")]
    assert not differing, f"{len(differing)} points differ from the sample without signals; the first (date, with, without): {differing[0]}"
    assert _bounds_json(sampled) == _bounds_json(plain_answer), f"sample_bounds {_bounds_json(sampled)}, without signals {_bounds_json(plain_answer)}"
    assert (sampled.events, sampled.errors, sorted(_signals_by_id(sampled))) == ([], [], sorted(request["instance_id"] for request in SG_ALL))


@pytest.mark.asyncio
@pytest.mark.parametrize(("asset", "start", "fields", "step", "count"), _SG_SAMPLES)
async def test_pqs_sg02_each_series_is_reduced_by_its_outputs_profile(signal_world, frozen_ceiling, asset, start, fields, step, count):
    """PQS-SG02: on the cases of PQS-SG01, each series of each signal result is the daily series — the same item without
    the sampling field — reduced on the plan's dates by its output's ``aggregation_profile``: walked here, the point the
    profile picks in each bucket (the EMA's, the MACD's lines' and histogram's and the rolling return's last, the
    drawdown's earliest lowest, the bands' envelope) re-dated at its render date, a bucket without a point of the series
    giving none (OLD's March 2010, without a quote: no EMA point on 2010-03-31); and ``sample_signal_series`` of the daily
    series with that profile, the step and the plan's dates. Each result is otherwise the daily one's. The premises: the
    plugins declare the profiles written here, and the daily answer computes the five, without an inner gap.

    Red before Z-29s-a: an item with signals and a sampling field cannot be built (``validate_sampling``).
    """
    asset_id = _asset_of(signal_world, asset)
    expected = _expected(signal_world, _item(asset_id, start, **fields))
    assert (expected.step, len(expected.dates)) == (step, count), "premise"
    _assert_profiles()
    (daily,) = await _query(signal_world.engine, _item(asset_id, start, signals=SG_ALL))
    _assert_computed(daily, SG_ALL)
    (sampled,) = await _query(signal_world.engine, _signal_item(asset_id, start, signals=SG_ALL, **fields))
    assert (sampled.resolution, _dates(sampled)) == (step, expected.dates), f"{sampled.resolution!r}; {_first_difference(_dates(sampled), expected.dates)}"
    _assert_signals_reduced(sampled, daily, step, expected.dates)


@pytest.mark.asyncio
async def test_pqs_sg03_the_macd_histogram_is_reduced_as_a_bar(signal_world, frozen_ceiling):
    """PQS-SG03: RECENT from its first row, Monday 2026-01-05, in 100 points (weekly: its 41 weeks fit) with MACD (3, 6,
    3): no row precedes the range, so the warm-up is incomplete (a partial result) and the daily histogram — a bar —
    opens on points without value, the whole first week. Reduced, the histogram is still a ``SignalBarSeries``, holds no
    point without value (a bar has no gap marker, and its warm-up is dropped), and starts on the render date of the week
    of its first value; with the MACD's two lines, each series the daily one reduced by its profile (PQS-SG02's checks).
    The range starts on the first row: from «All», the strict coverage of the visible range would leave MACD unavailable.

    Red before Z-29s-a: an item with signals and a sampling field cannot be built (``validate_sampling``).
    """
    start, fields = _HISTORIES["recent"][0], {"max_points": 100}
    expected = _expected(signal_world, _item(signal_world.recent, start, **fields))
    assert (expected.step, expected.first, len(expected.dates)) == ("weekly", start, 41), "premise"
    (daily,) = await _query(signal_world.engine, _item(signal_world.recent, start, signals=[SG_MACD]))
    _assert_computed(daily, [SG_MACD])
    (macd,) = daily.signals
    histogram = next(series for series in macd.series if series.key == "histogram")
    first_value = next(point.date for point in histogram.points if point.value is not None)
    leading = [point.date for point in histogram.points if point.value is None]
    assert isinstance(histogram, SignalBarSeries) and leading and max(leading) < first_value, f"premise: the daily histogram is a bar opening on points without value, {type(histogram).__name__}, {leading}"
    assert _ref_bucket(first_value, "weekly") != _ref_bucket(expected.dates[0], "weekly"), f"premise: the first week holds no value of the histogram (the first on {first_value})"
    (sampled,) = await _query(signal_world.engine, _signal_item(signal_world.recent, start, signals=[SG_MACD], **fields))
    (reduced_macd,) = sampled.signals
    reduced = next(series for series in reduced_macd.series if series.key == "histogram")
    assert isinstance(reduced, SignalBarSeries), type(reduced).__name__
    assert [point.date for point in reduced.points if point.value is None] == [], "a bar holds points without value: gap markers, or its warm-up kept"
    first_render = next(day for day in expected.dates if _ref_bucket(day, "weekly") == _ref_bucket(first_value, "weekly"))
    assert reduced.points[0].date == first_render, f"the histogram starts on {reduced.points[0].date}, not on {first_render}, the render date of its first value's week"
    _assert_signals_reduced(sampled, daily, "weekly", expected.dates)


@pytest.mark.asyncio
async def test_pqs_sg04_a_rolling_return_representative_keeps_its_provenance(signal_world, frozen_ceiling):
    """PQS-SG04: the calendar rolling return (7 days, ``last_with_range``) on WAVE weekly on a card: its daily points are
    calendar-return points, one a day, those of a weekend carrying Friday's price (``current_price_days_back`` above
    0). Reduced, each point is still a ``SignalCalendarReturnValuePoint`` and is, value and provenance, the daily point
    it stands for — the last of its week — re-dated at the week's render date; a Sunday's stands for a carried day.

    Red before Z-29s-a: an item with signals and a sampling field cannot be built (``validate_sampling``).
    """
    fields = {"max_points": 60}
    expected = _expected(signal_world, _item(WAVE_ID, WAVE_START, **fields))
    assert (expected.step, len(expected.dates)) == ("weekly", 34), "premise"
    (daily,) = await _query(signal_world.engine, _item(WAVE_ID, WAVE_START, signals=[SG_RETURN]))
    _assert_computed(daily, [SG_RETURN])
    ((daily_series,),) = [result.series for result in daily.signals]
    kinds = {type(point).__name__ for point in daily_series.points}
    carried = [point.date for point in daily_series.points if isinstance(point, SignalCalendarReturnValuePoint) and point.provenance.current_price_days_back > 0]
    assert (kinds, bool(carried)) == ({"SignalCalendarReturnValuePoint"}, True), f"premise: the daily points are {kinds}, carried days {carried[:3]}"
    (sampled,) = await _query(signal_world.engine, _signal_item(WAVE_ID, WAVE_START, signals=[SG_RETURN], **fields))
    ((series,),) = [result.series for result in sampled.signals]
    assert {type(point).__name__ for point in series.points} == {"SignalCalendarReturnValuePoint"}, f"the reduced points are {sorted({type(point).__name__ for point in series.points})}: the provenance is lost"
    got = [point.model_dump(mode="json") for point in series.points]
    expected_points = _ref_reduction(daily_series, "last_with_range", "weekly", expected.dates)
    assert got == expected_points, _first_mismatch(got, expected_points)
    assert any(point.provenance.current_price_days_back > 0 for point in series.points), "barrier: no representative stands for a carried day"
    _assert_signals_reduced(sampled, daily, "weekly", expected.dates)


@pytest.mark.asyncio
async def test_pqs_sg05_without_prices_the_signals_are_reduced_on_rows_read_day_by_day(signal_world, frozen_ceiling):
    """PQS-SG05: WAVE weekly on a card with ``include_price=False`` and the five signals is no placeholder: it answers
    weekly, no point, no bounds, no error, its signals the daily ones reduced on the plan's dates (PQS-SG02's checks);
    and its rows are read day by day — the day-by-day read lists WAVE, no bucket statement names it, the ORM loads more
    of its rows than the plan's points and bounds. The contrast, the same item without signals: a placeholder (point
    14), which reads nothing past its plan.

    Red before Z-29s-a: an item with signals and a sampling field cannot be built (``validate_sampling``).
    """
    fields = {"max_points": 60, "include_price": False}
    placeholder = _item(WAVE_ID, WAVE_START, **fields)
    expected = _expected(signal_world, placeholder)
    assert (expected.step, len(expected.dates)) == ("weekly", 34), "premise"
    with _recording_statements(signal_world.engine) as placeholder_said:
        (alone,) = await _query(signal_world.engine, placeholder)
    _assert_placeholder(alone, WAVE_ID, "weekly")
    assert _reads_naming(placeholder_said, WAVE_ID) == [], f"premise: the placeholder is read: {_said(placeholder_said)}"
    (daily,) = await _query(signal_world.engine, _item(WAVE_ID, WAVE_START, include_price=False, signals=SG_ALL))
    _assert_computed(daily, SG_ALL)
    item = _signal_item(WAVE_ID, WAVE_START, signals=SG_ALL, **fields)
    with _recording_statements(signal_world.engine) as said, _counting_loads() as loads:
        (sampled,) = await _query(signal_world.engine, item)
    said_answer = (sampled.resolution, sampled.prices, sampled.sample_bounds, sampled.errors, sampled.events)
    assert said_answer == ("weekly", [], None, [], []), f"(resolution, prices, bounds, errors, events) {said_answer}"
    _assert_signals_reduced(sampled, daily, "weekly", expected.dates)
    reads = _reads_naming(said, WAVE_ID)
    assert "daily" in reads and "bucket" not in reads, f"WAVE's reads {reads}: not day by day; the statements: {_said(said)}"
    assert loads[WAVE_ID] > len(expected.dates) + 2, f"{loads[WAVE_ID]} of WAVE's rows loaded: no more than a sample's"


@pytest.mark.asyncio
async def test_pqs_sg06_the_budget_counts_the_fill_days_of_an_item_with_signals(signal_world, frozen_ceiling, monkeypatch):
    """PQS-SG06: an item with signals and a sampling field counts against the day budget as the same item without the
    sampling field — its fill's days, warm-up included (the drawdown loads the full history: WAVE's 650 days) —, not its
    points and bounds. Under a budget of WAVE's weekly points and bounds (36), between those and the fill's days, the
    item without signals is answered and the item with them is refused, ``item_days`` the fill's days, the count of the
    item with signals without the sampling field (read under a budget of 0, its own refusal).

    Red before Z-29s-a: an item with signals and a sampling field cannot be built (``validate_sampling``).
    """
    fields = {"max_points": 60}
    plain = _item(WAVE_ID, WAVE_START, **fields)
    expected = _expected(signal_world, plain)
    points = len(expected.dates) + 2
    assert (expected.step, points) == ("weekly", 36), "premise"
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", 0)
    fill_days = (await _refused_for_days(lambda: _query(signal_world.engine, _item(WAVE_ID, WAVE_START, signals=SG_ALL)))).item_days
    assert fill_days > points, f"premise: the daily item with signals counts {fill_days}, not more than the sample's {points}"
    monkeypatch.setattr(price_query, "MAX_BULK_ITEM_DAYS", points)
    (answered,) = await _answered_within_budget(lambda: _query(signal_world.engine, plain))
    assert _dates(answered) == expected.dates
    item = _signal_item(WAVE_ID, WAVE_START, signals=SG_ALL, **fields)
    refusal = await _refused_for_days(lambda: _query(signal_world.engine, item))
    assert (refusal.item_days, refusal.max_item_days) == (fill_days, points), f"refused with item_days {refusal.item_days}, not the fill's {fill_days}"


@pytest.mark.asyncio
@pytest.mark.parametrize("fields", [pytest.param({"max_points": CARD}, id="its-days-within-max-points"), pytest.param({"resolution": "daily"}, id="daily-asked")])
async def test_pqs_sg07_a_daily_step_with_signals_is_the_answer_without_the_field(signal_world, frozen_ceiling, fields):
    """PQS-SG07: WAVE from Tuesday 2026-09-01 to the ceiling, 47 days, with the five signals and 377 points — which its
    days fit — or asking daily: the plan is daily, and the answer is the one without the sampling field, as the wire
    writes it (``computed_at`` aside): every day, ``resolution`` daily, no bounds, the daily series.

    Red before Z-29s-a: an item with signals and a sampling field cannot be built (``validate_sampling``).
    """
    start = date(2026, 9, 1)
    expected = _expected(signal_world, _item(WAVE_ID, start, **fields))
    assert (expected.step, len(expected.dates)) == ("daily", 47), "premise"
    (daily,) = await _query(signal_world.engine, _item(WAVE_ID, start, signals=SG_ALL))
    _assert_computed(daily, SG_ALL)
    (asked,) = await _query(signal_world.engine, _signal_item(WAVE_ID, start, signals=SG_ALL, **fields))
    assert (asked.resolution, asked.sample_bounds) == ("daily", None)
    assert _same_but_the_clock(asked, daily), "a daily step with signals answers otherwise than without the sampling field"


@pytest.mark.asyncio
async def test_pqs_sg08_a_follower_is_reduced_on_its_plan_from_the_later_first_day(signal_world, frozen_ceiling):
    """PQS-SG08: a card on RECENT (``key`` card, 100 points) and WAVE following it with the five signals, both from
    Monday 2025-01-06, WAVE's first row, to the ceiling. The card's fill starts on its first row, 2026-01-05: weekly (41
    weeks). WAVE's own fill starts on 2025-01-06: its plan is the card's step from the later first day, 2026-01-05 (41
    weeks). It carries the prices and the bounds of the follower without signals, and each series is its daily series —
    WAVE on the same range without ``sample_like``, every series with points of 2025 — reduced on its plan's dates: the
    points before the plan's first week dropped (PQS-SG02's checks). The card answers as beside the follower without
    signals. The range starts on WAVE's first row: from «All», the strict coverage of the visible range would leave its
    indicators unavailable.

    Red before Z-29s-a: an item with signals and a sampling field cannot be built (``validate_sampling``).
    """
    card = _item(signal_world.recent, WAVE_FIRST, key="card", max_points=100)
    plain_target = _item(WAVE_ID, WAVE_FIRST, sample_like="card")
    expected = _expected_like(signal_world, plain_target, card)
    assert (expected.step, expected.first, len(expected.dates)) == ("weekly", _HISTORIES["recent"][0], 41), "premise"
    (daily,) = await _query(signal_world.engine, _item(WAVE_ID, WAVE_FIRST, signals=SG_ALL))
    _assert_computed(daily, SG_ALL)
    late = [f"{result.instance_id}.{series.key}" for result in daily.signals for series in result.series if min(point.date for point in series.points) >= expected.first]
    assert not late, f"premise: every daily series has points before {expected.first}, which the reduction drops; not {late}"
    card_beside_plain, plain_answer = await _query(signal_world.engine, card, plain_target)
    card_answer, target_answer = await _query(signal_world.engine, card, _signal_item(WAVE_ID, WAVE_FIRST, sample_like="card", signals=SG_ALL))
    assert (target_answer.resolution, _dates(target_answer)) == ("weekly", expected.dates), f"{target_answer.resolution!r}; {_first_difference(_dates(target_answer), expected.dates)}"
    assert [point.model_dump(mode="json") for point in target_answer.prices] == [point.model_dump(mode="json") for point in plain_answer.prices]
    assert _bounds_json(target_answer) == _bounds_json(plain_answer) and target_answer.sample_bounds.first.date == expected.first
    _assert_signals_reduced(target_answer, daily, "weekly", expected.dates)
    assert _same(card_answer, card_beside_plain), "the card answers otherwise beside a follower with signals"


@pytest.mark.parametrize("field", SAMPLE_FIELDS)
def test_pqs_sg09_signals_are_taken_with_each_sampling_field(field):
    """PQS-SG09: ``max_points``, ``resolution`` or ``sample_like`` with the five signals is a valid item, alone and with
    ``include_price=False`` and ``target_currency``: the item keeps the field and the signals, no annotation, no events.

    Red before Z-29s-a: refused by ``validate_sampling`` («samples the price series alone: not with signals, …»).
    """
    for extra in ({}, {"include_price": False, "target_currency": "USD"}):
        try:
            item = FAPriceQueryItem.model_validate(_payload(**{field: SAMPLING_VALUES[field]}, signals=SG_ALL, **extra))
        except ValidationError as refusal:
            pytest.fail(f"Z-29s-a: signals with {field} ({extra}) refused: {[error['msg'] for error in refusal.errors()]}")
        kept = (getattr(item, field), [signal.instance_id for signal in item.signals], item.annotation_requests, item.include_events, item.include_price)
        assert kept == (SAMPLING_VALUES[field], [request["instance_id"] for request in SG_ALL], [], False, not extra), kept


def test_pqs_sg10_the_descriptions_say_the_signals_are_reduced():
    """PQS-SG10: the descriptions say what Z-29s-a does: ``FAPriceQueryItem.max_points`` no longer says «not with
    signals»; ``FAPriceQueryResult.signals`` and ``resolution`` name the ``aggregation_profile`` a weekly or monthly
    result's series are reduced by — on the fields, and in the JSON schema in both modes, what the OpenAPI document and
    the generated client read. The words are checked, not the sentence.

    Red before Z-29s-a: ``max_points`` says «not with signals, annotation_requests or include_events», and neither
    ``signals`` nor ``resolution`` names the profile.
    """
    said = {"max_points": FAPriceQueryItem.model_fields["max_points"].description or ""}
    said |= {f"result.{name}": FAPriceQueryResult.model_fields[name].description or "" for name in ("signals", "resolution")}
    for mode in ("validation", "serialization"):
        said[f"{mode} max_points"] = FAPriceQueryItem.model_json_schema(mode=mode)["properties"]["max_points"].get("description", "")
        properties = FAPriceQueryResult.model_json_schema(mode=mode)["properties"]
        said |= {f"{mode} result.{name}": properties[name].get("description", "") for name in ("signals", "resolution")}
    wrong = {where: text for where, text in said.items() if where.endswith("max_points") and "not with signals" in text.lower()}
    wrong |= {where: text for where, text in said.items() if not where.endswith("max_points") and "aggregation_profile" not in text}
    assert not wrong, wrong


@pytest.mark.asyncio
async def test_pqs_sg11_the_series_of_a_signal_with_different_warm_ups_are_on_the_same_dates(signal_world, frozen_ceiling):
    """PQS-SG11 (O1): RECENT from its first row, Monday 2026-01-05, in 100 points (weekly: its 41 weeks fit) with ADX (3):
    the directional lines are valued from the fourth session, in the first week, the ADX from the seventh, in the second.
    Reduced, each series is its daily one reduced alone (PQS-SG02's checks), and the three are on the same dates, as
    ``SignalResult`` wants them: the ADX has a point without a value on the render date of the first week, where only the
    directional lines have a value; none after its first value.

    Red before the O1 cure: the ADX has no point on the first week, so the three series are on different dates.
    """
    start, fields = _HISTORIES["recent"][0], {"max_points": 100}
    expected = _expected(signal_world, _item(signal_world.recent, start, **fields))
    assert (expected.step, expected.first, len(expected.dates)) == ("weekly", start, 41), "premise"
    _assert_profiles()
    (daily,) = await _query(signal_world.engine, _item(signal_world.recent, start, signals=[SG_ADX]))
    _assert_computed(daily, [SG_ADX])
    (adx,) = daily.signals
    firsts = {series.key: next(point.date for point in series.points if point.value is not None) for series in adx.series}
    weeks = {key: _ref_bucket(day, "weekly") for key, day in firsts.items()}
    assert weeks["plus_di"] == weeks["minus_di"] == _ref_bucket(expected.dates[0], "weekly") != weeks["adx"], f"premise: the daily series are first valued on {firsts}"
    (sampled,) = await _query(signal_world.engine, _signal_item(signal_world.recent, start, signals=[SG_ADX], **fields))
    (reduced,) = sampled.signals
    by_key = {series.key: series for series in reduced.series}
    dates = {key: [point.date for point in series.points] for key, series in by_key.items()}
    assert dates["adx"] == dates["plus_di"] == dates["minus_di"], f"the series are on different dates: {({key: days[:3] for key, days in dates.items()})}"
    assert [(point.date, point.value) for point in by_key["adx"].points[:1]] == [(expected.dates[0], None)], "the ADX has no point without a value on the first week"
    assert [point.date for point in by_key["adx"].points if point.value is None] == [expected.dates[0]], "the ADX has points without a value besides the first week's"
    _assert_signals_reduced(sampled, daily, "weekly", expected.dates)
