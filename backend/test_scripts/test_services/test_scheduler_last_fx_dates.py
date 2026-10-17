"""X-R45 — the history sync's last saved FX dates skip a stored rate no read may use (lot Z-5's lookup, on the lane DB).

The defect, on HEAD 16e837153. ``jobs._last_fx_dates`` answers, for each pair it is asked about, ``max(date)`` over every
stored row, and the history sync starts the day after it (``_history_sync_start``, lot Z-5). A 1.2 install could store
rates no read may use — 0 (a manual ``1E-11`` truncated to 10 decimals), an infinite REAL (``1E+400``), 1E+14 and above:
outside X-R38's ``usable_fx_rate_bounds()``, 1E-10 <= rate < 1E+14. Such a row, as a pair's latest, counts as covered:
the sync never asks for that day again, so the provider's rate never overwrites it.

The cure's contract (X-R45), pinned here with the real function on a real session against the lane database:
``_last_fx_dates`` reads only the rates ``usable_fx_rate_clause()`` (``db/precision.py``) keeps.

1. A usable rate on D1 and an unusable one on D2 > D1 (0, inf, 1E+14): both orders of the pair's slug answer D1, and the
   history sync, its horizon a week, starts the day after D1 — before D2, which is fetched again.
2. A pair whose only stored rate is unusable answers nothing, as a pair with no rate.

Red on HEAD 16e837153: ``test_xr45_last_fx_dates_skips_an_unusable_latest_rate`` and
``test_xr45_last_fx_dates_answers_nothing_for_a_pair_whose_only_rate_is_unusable`` (0, inf and 1E+14 each): D2 is
answered. Green before and after (guard): ``test_xr45_guard_last_fx_dates_answers_the_latest_usable_rate`` (an ordinary
rate, and the two bounds 1E-10 and 99999999999999, on D2: D2).

A file of its own: ``test_scheduler_jobs.py`` replaces ``_last_fx_dates`` with a fake for the job cases and meets the live
database only to read (its unit is READ), while these cases write rows.

Ownership. The pair XQD/XQE — codes shaped like ISO 4217, unassigned, written by no other test — is this file's. Each
test checks, not assumes, that no rate of it is committed, plants its rows with raw SQL in its own session — past the
model, as an older release could leave them — and never commits: the session rolls them back. No other connection sees
them; a concurrent writer waits for the rollback at most the length of one test (busy_timeout 30 s). The days count back
from today, as the history sync does, so that the start it computes can be compared with them.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.app.db.models import FxRate
from backend.app.db.session import get_async_engine
from backend.app.services.platform.scheduler import jobs
from backend.test_scripts.test_utils import print_section, print_success

#: This file's pair, as ``fx_rates`` keeps it (base < quote). Not XQB/XQC: ``test_scheduler_jobs.py`` asks about that
#: pair as one no rate is ever stored for.
XR45_BASE, XR45_QUOTE = "XQD", "XQE"
#: Both orders of the slug: ``fx_rates`` keeps the pair in alphabetical order, and each slug is answered as it was asked.
XR45_SLUGS = (f"{XR45_BASE}-{XR45_QUOTE}", f"{XR45_QUOTE}-{XR45_BASE}")
#: The history sync's horizon in these cases: D1 and D2 lie behind it, so the sync reaches back to the last saved date.
HORIZON_DAYS = 7
D1_DAYS_AGO, D2_DAYS_AGO = 60, 40
D1_RATE = 1.5
#: Rates a 1.2 install could store and no read may use (X-R38: usable is 1E-10 <= rate < 1E+14), as SQLite binds them.
XR45_UNUSABLE = [
    pytest.param(0.0, id="0"),  # a manual 1E-11, truncated to the column's 10 decimals
    pytest.param(float("inf"), id="inf"),  # 1E+400, written as an SQLite REAL
    pytest.param(1e14, id="1E+14"),  # the first rate refused
]
#: Rates a read may use, the two bounds among them.
XR45_USABLE = [
    pytest.param(2.0, id="ordinary-2"),
    pytest.param(1e-10, id="smallest-1E-10"),
    pytest.param(99999999999999.0, id="largest-99999999999999"),
]


def _days() -> tuple[date, date, date]:
    """(today, D1, D2), D1 before D2, both behind the horizon."""
    today = date.today()
    return today, today - timedelta(days=D1_DAYS_AGO), today - timedelta(days=D2_DAYS_AGO)


async def _check_the_pair_is_free(session: AsyncSession) -> None:
    """Precondition, checked not assumed: no committed XQD/XQE rate, whatever its date — ``_last_fx_dates`` reads them all."""
    leftover = (await session.execute(select(FxRate.date).where(FxRate.base == XR45_BASE, FxRate.quote == XR45_QUOTE))).scalars().all()
    if leftover:
        pytest.fail(f"Precondition failed: X-R45 needs {XR45_BASE}/{XR45_QUOTE} without rates, found {', '.join(str(day) for day in sorted(leftover))}")


async def _plant(session: AsyncSession, rates: dict[date, float]) -> None:
    """XQD/XQE rates written with raw SQL in ``session``, past the model, and not committed.

    Barrier: raw SQL reads back, in the same session, the very rates planted — an inf stays inf, a 0 stays 0.
    """
    for day, rate in rates.items():
        await session.execute(
            text("INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES (:day, :base, :quote, :rate, 'X-R45', CURRENT_TIMESTAMP)"),
            {"day": day.isoformat(), "base": XR45_BASE, "quote": XR45_QUOTE, "rate": rate},
        )
    stored = (await session.execute(text("SELECT date, rate FROM fx_rates WHERE base = :base AND quote = :quote"), {"base": XR45_BASE, "quote": XR45_QUOTE})).all()
    found = {date.fromisoformat(day): rate for day, rate in stored}
    assert found == rates, f"the fixture itself is wrong: raw SQL reads back {found}, not the rates planted, {rates}"


async def _last_fx_dates_over(rates: dict[date, float]) -> dict[str, date]:
    """The real ``jobs._last_fx_dates`` for both slugs of the pair, on a session of the lane database holding ``rates`` for
    it, uncommitted; the session rolls them back whatever happens."""
    async with AsyncSession(get_async_engine()) as session:
        await _check_the_pair_is_free(session)
        try:
            await _plant(session, rates)
            return await jobs._last_fx_dates(session, list(XR45_SLUGS))
        finally:
            await session.rollback()


@pytest.mark.asyncio
@pytest.mark.parametrize("unusable", XR45_UNUSABLE)
async def test_xr45_last_fx_dates_skips_an_unusable_latest_rate(unusable):
    """Red on HEAD 16e837153: ``max(date)`` over every row answers D2, whose rate no read may use. The history sync then
    starts the day after D2 and never asks for D2 again: the provider's rate never replaces the legacy one.

    Contract (X-R45): both slugs answer D1, the latest usable rate's date; the sync, its horizon a week, starts the day
    after D1 — before D2, which is fetched again.
    """
    today, d1, d2 = _days()
    story = f"{XR45_BASE}/{XR45_QUOTE} {D1_RATE} on {d1} and a legacy {unusable!r} on {d2}"
    print_section(f"X-R45: the last saved FX date, {story}")

    last = await _last_fx_dates_over({d1: D1_RATE, d2: unusable})

    assert last == dict.fromkeys(XR45_SLUGS, d1), f"{story}: _last_fx_dates answers {last}, expected {d1} for both slugs — the latest usable rate's date (X-R45)"
    start = jobs._history_sync_start(today, HORIZON_DAYS, last[XR45_SLUGS[0]])
    assert start == d1 + timedelta(days=1), f"{story}: the history sync starts on {start}, expected the day after {d1}"
    assert start <= d2, f"{story}: the history sync starts on {start}, after {d2}: the legacy rate is never fetched again"
    print_success(f"{story}: {d1}, the sync starting on {start}")


@pytest.mark.asyncio
@pytest.mark.parametrize("unusable", XR45_UNUSABLE)
async def test_xr45_last_fx_dates_answers_nothing_for_a_pair_whose_only_rate_is_unusable(unusable):
    """Red on HEAD 16e837153: D2 is answered, its rate no read may use.

    Contract (X-R45): nothing for either slug, as for a pair with no rate; the sync keeps its horizon (lot Z-5: without a
    saved value, fetching a whole history stays a manual sync).
    """
    _today, _d1, d2 = _days()
    story = f"{XR45_BASE}/{XR45_QUOTE} whose only rate is a legacy {unusable!r} on {d2}"
    print_section(f"X-R45: the last saved FX date, {story}")

    last = await _last_fx_dates_over({d2: unusable})

    assert last == {}, f"{story}: _last_fx_dates answers {last}, expected nothing — no usable rate is saved (X-R45)"
    print_success(f"{story}: nothing")


@pytest.mark.asyncio
@pytest.mark.parametrize("usable", XR45_USABLE)
async def test_xr45_guard_last_fx_dates_answers_the_latest_usable_rate(usable):
    """Guard: green before and after. 1.5 on D1 and a usable rate on D2 — an ordinary 2, and the two bounds 1E-10 and
    99999999999999: both slugs answer D2, the latest, and the sync starts the day after it — the clause skips nothing a
    read may use."""
    today, d1, d2 = _days()
    story = f"{XR45_BASE}/{XR45_QUOTE} {D1_RATE} on {d1} and {usable!r} on {d2}"
    print_section(f"X-R45 guard: the last saved FX date, {story}")

    last = await _last_fx_dates_over({d1: D1_RATE, d2: usable})

    assert last == dict.fromkeys(XR45_SLUGS, d2), f"{story}: _last_fx_dates answers {last}, expected {d2} for both slugs"
    start = jobs._history_sync_start(today, HORIZON_DAYS, last[XR45_SLUGS[0]])
    assert start == d2 + timedelta(days=1), f"{story}: the history sync starts on {start}, expected the day after {d2}"
    print_success(f"{story}: {d2}")
