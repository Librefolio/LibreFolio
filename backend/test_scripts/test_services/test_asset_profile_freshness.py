"""«Adesso» non aggiornato (project 68, lot D1d): ``services/assets/profile/freshness.py``.

The developer's decision (18/11/2026): for the voices the catalogue marks «changes at every read» (``volatile``: fund
size, market cap, gross and net yield, modified duration, accrued interest), «now» is **stale** when its last
confirmation is more than ``STALE_AFTER_DAYS`` (30) days old. Pinned here:

1. **The last confirmation** of a voice's «now» row is, for the source that wrote it, the day that source last gave the
   voice (``asset_enrichers.state[source]["confirmed"][key]``, a UTC ISO moment, read as a day in the scheduler's time
   zone); never before the row's own ``read_on``. A value written by hand, a source that never gave the voice, or a
   state written before D1d (no ``confirmed``): the row's ``read_on`` (``opened_on``).
2. **Stale** is strictly more than 30 days: 31 → stale, 30 and 29 → not.
3. Only the volatile voices answer: a TER read a year ago is never stale, and is absent.
4. ``holding_now``: the signal belongs to the voice's last step when it reaches the day of the «now» row (whatever day
   the range ends on); a range that ends before «now» was read, or no step, carries none. ``keys`` limits the read.

Every database is a private SQLite file under ``tmp_path`` built with ``create_all``; every day is passed in.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetProfileUpdate, AssetType, GlobalSetting, User
from backend.app.services.assets.profile import freshness
from backend.app.services.assets.profile.catalogue import CATALOGUE, normalize_value
from backend.app.services.assets.profile.store import ProfileStep
from backend.app.services.enrichers import bindings

pytestmark = pytest.mark.asyncio

TODAY = date(2026, 11, 18)
SOURCE = "borsa_italiana"
OTHER = "justetf"


@pytest.fixture(autouse=True)
def _no_timezone_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """``LIBREFOLIO_DEFAULT_TIMEZONE`` stands behind ``scheduler_timezone`` until an administrator saves it: never here."""
    monkeypatch.delenv("LIBREFOLIO_DEFAULT_TIMEZONE", raising=False)


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'asset_profile_freshness.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


async def _asset(engine: AsyncEngine, name: str = "BTP 2030") -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=name, currency="EUR", asset_type=AssetType.BOND)
        session.add(asset)
        await session.commit()
    return int(asset.id)


async def _row(engine: AsyncEngine, asset_id: int, key: str, value: Any, source: str, read_on: date) -> None:
    async with AsyncSession(engine) as session:
        session.add(AssetProfileUpdate(asset_id=asset_id, key=key, value=json.dumps(normalize_value(key, value)), source=source, read_on=read_on))
        await session.commit()


def _moment(day: date) -> str:
    return datetime.combine(day, time(9, 30), tzinfo=UTC).isoformat()


async def _state(engine: AsyncEngine, asset_id: int, entries: Mapping[str, Mapping[str, Any]]) -> None:
    async with AsyncSession(engine) as session:
        await bindings.update_state(session, asset_id, entries)
        await session.commit()


def _entry(confirmed: Mapping[str, date] | None, read_at: date = TODAY) -> dict[str, Any]:
    entry: dict[str, Any] = {"read_at": _moment(read_at), "status": "ok", "error_code": None, "retry_after": None, "voices": len(confirmed or {})}
    if confirmed is not None:
        entry["confirmed"] = {key: _moment(day) for key, day in confirmed.items()}
    return entry


async def _freshness(engine: AsyncEngine, asset_id: int, today: date = TODAY) -> dict[str, freshness.VoiceFreshness]:
    async with AsyncSession(engine) as session:
        return (await freshness.voice_freshness(session, [asset_id], today=today)).get(asset_id, {})


def test_the_threshold_is_thirty_days() -> None:
    assert freshness.STALE_AFTER_DAYS == 30


@pytest.mark.parametrize(("days", "stale"), [(31, True), (30, False), (29, False)], ids=["31-stale", "30-not", "29-not"])
async def test_a_source_confirmation_older_than_thirty_days_is_stale(engine: AsyncEngine, days: int, stale: bool) -> None:
    """The row opened two months ago; its source last gave the voice ``days`` ago: that is the confirmation."""
    asset_id = await _asset(engine)
    await _row(engine, asset_id, "modified_duration", "1.8", SOURCE, TODAY - timedelta(days=60))
    await _state(engine, asset_id, {SOURCE: _entry({"modified_duration": TODAY - timedelta(days=days)})})

    result = await _freshness(engine, asset_id)

    assert result["modified_duration"] == freshness.VoiceFreshness(confirmed_on=TODAY - timedelta(days=days), stale=stale, opened_on=TODAY - timedelta(days=60)), result


async def test_a_source_that_did_not_give_the_voice_counts_from_the_row(engine: AsyncEngine) -> None:
    """The source answers every week, but without the duration: the duration's confirmation is its row's day."""
    asset_id = await _asset(engine)
    await _row(engine, asset_id, "modified_duration", "1.8", SOURCE, TODAY - timedelta(days=31))
    await _state(engine, asset_id, {SOURCE: _entry({"yield_gross": TODAY - timedelta(days=2)})})

    result = await _freshness(engine, asset_id)

    assert result["modified_duration"] == freshness.VoiceFreshness(confirmed_on=TODAY - timedelta(days=31), stale=True, opened_on=TODAY - timedelta(days=31)), result


async def test_another_source_confirming_the_voice_is_not_the_rows_confirmation(engine: AsyncEngine) -> None:
    asset_id = await _asset(engine)
    await _row(engine, asset_id, "yield_gross", "0.0361", SOURCE, TODAY - timedelta(days=45))
    await _state(engine, asset_id, {OTHER: _entry({"yield_gross": TODAY - timedelta(days=1)})})

    result = await _freshness(engine, asset_id)

    assert result["yield_gross"] == freshness.VoiceFreshness(confirmed_on=TODAY - timedelta(days=45), stale=True, opened_on=TODAY - timedelta(days=45)), result


async def test_a_value_written_by_hand_thirty_one_days_ago_is_stale(engine: AsyncEngine) -> None:
    asset_id = await _asset(engine)
    await _row(engine, asset_id, "fund_size", {"amount": "1000000", "currency": "EUR"}, "user", TODAY - timedelta(days=31))
    await _state(engine, asset_id, {SOURCE: _entry({"fund_size": TODAY})})

    result = await _freshness(engine, asset_id)

    assert result["fund_size"] == freshness.VoiceFreshness(confirmed_on=TODAY - timedelta(days=31), stale=True, opened_on=TODAY - timedelta(days=31)), "by hand: only the row's day counts"


async def test_a_state_written_before_the_confirmations_counts_from_the_row(engine: AsyncEngine) -> None:
    asset_id = await _asset(engine)
    await _row(engine, asset_id, "accrued_interest", "1.25", SOURCE, TODAY - timedelta(days=40))
    await _state(engine, asset_id, {SOURCE: _entry(None)})

    result = await _freshness(engine, asset_id)

    assert result["accrued_interest"] == freshness.VoiceFreshness(confirmed_on=TODAY - timedelta(days=40), stale=True, opened_on=TODAY - timedelta(days=40)), result


async def test_a_confirmation_is_never_before_the_rows_own_day(engine: AsyncEngine) -> None:
    """A row written today by the source over a confirmation of two months ago: confirmed today."""
    asset_id = await _asset(engine)
    await _row(engine, asset_id, "market_cap", {"amount": "5000000", "currency": "EUR"}, SOURCE, TODAY)
    await _state(engine, asset_id, {SOURCE: _entry({"market_cap": TODAY - timedelta(days=60)})})

    result = await _freshness(engine, asset_id)

    assert result["market_cap"] == freshness.VoiceFreshness(confirmed_on=TODAY, stale=False, opened_on=TODAY), result


async def test_the_now_row_is_the_last_one(engine: AsyncEngine) -> None:
    """Two rows of the voice: the confirmation is the later one's."""
    asset_id = await _asset(engine)
    await _row(engine, asset_id, "yield_net", "0.031", SOURCE, TODAY - timedelta(days=90))
    await _row(engine, asset_id, "yield_net", "0.029", "user", TODAY - timedelta(days=10))

    result = await _freshness(engine, asset_id)

    assert result["yield_net"] == freshness.VoiceFreshness(confirmed_on=TODAY - timedelta(days=10), stale=False, opened_on=TODAY - timedelta(days=10)), result


async def test_a_voice_that_keeps_still_is_never_stale(engine: AsyncEngine) -> None:
    """A TER read a year ago, and countries: not volatile, never in the answer."""
    assert not CATALOGUE["ter"].volatile and not CATALOGUE["geography"].volatile, "barrier: TER and countries keep still"
    asset_id = await _asset(engine)
    await _row(engine, asset_id, "ter", "0.0022", SOURCE, TODAY - timedelta(days=365))
    await _row(engine, asset_id, "geography", {"ITA": "1"}, SOURCE, TODAY - timedelta(days=365))

    assert await _freshness(engine, asset_id) == {}, "only the volatile voices answer"


async def test_an_asset_without_rows_answers_nothing(engine: AsyncEngine) -> None:
    asset_id = await _asset(engine)
    async with AsyncSession(engine) as session:
        assert await freshness.voice_freshness(session, [asset_id], today=TODAY) == {}


async def test_the_confirmation_is_a_day_in_the_scheduler_time_zone(engine: AsyncEngine) -> None:
    """Confirmed at 23:30 UTC on 17/10: in Rome it is already 18/10, 30 days before 17/11, not «more than 30» (read as
    the UTC day it would be 31)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        admin = User(username="admin", email="admin@example.com", hashed_password="$argon2id$seeded-account")
        session.add(admin)
        await session.commit()
        session.add(GlobalSetting(key="scheduler_timezone", value="Europe/Rome", value_type="str", updated_by_user_id=admin.id))
        await session.commit()
    asset_id = await _asset(engine)
    await _row(engine, asset_id, "modified_duration", "1.8", SOURCE, date(2026, 9, 1))
    entry = _entry({})
    entry["confirmed"] = {"modified_duration": datetime(2026, 10, 17, 23, 30, tzinfo=UTC).isoformat()}
    await _state(engine, asset_id, {SOURCE: entry})

    result = await _freshness(engine, asset_id, today=date(2026, 11, 17))

    assert result["modified_duration"] == freshness.VoiceFreshness(confirmed_on=date(2026, 10, 18), stale=False, opened_on=date(2026, 9, 1)), result


def _step(start: date, through: date) -> ProfileStep:
    return ProfileStep(date=start, through=through, value="1.8", source=SOURCE, update_id=1, opened_on=start)


def test_the_signal_is_on_the_last_step_only_when_it_holds_now() -> None:
    """«Now» was read on 01/10. A range ending on any day from then on holds it (a browser's today may be the
    scheduler's yesterday); one that ends before carries no signal."""
    known = freshness.VoiceFreshness(confirmed_on=TODAY - timedelta(days=40), stale=True, opened_on=date(2026, 10, 1))
    steps = [_step(date(2026, 9, 1), date(2026, 9, 30)), _step(date(2026, 10, 1), TODAY - timedelta(days=1))]

    assert freshness.holding_now(known, steps) == known, "the last step holds now, though it ends yesterday"
    assert freshness.holding_now(known, [*steps[:1], _step(date(2026, 10, 1), date(2026, 10, 1))]) == known, "the day now was read"
    assert freshness.holding_now(known, steps[:1]) is None, "a range that ends before now was read carries none"
    assert freshness.holding_now(known, []) is None, "no step, no signal"
    assert freshness.holding_now(None, steps) is None, "a voice with no freshness carries none"


async def test_only_the_volatile_voices_asked_are_read(engine: AsyncEngine) -> None:
    asset_id = await _asset(engine)
    await _row(engine, asset_id, "modified_duration", "1.8", SOURCE, TODAY - timedelta(days=40))
    await _row(engine, asset_id, "yield_gross", "0.0361", SOURCE, TODAY - timedelta(days=40))
    async with AsyncSession(engine) as session:
        duration_only = (await freshness.voice_freshness(session, [asset_id], today=TODAY, keys=["modified_duration", "ter"])).get(asset_id, {})
        none_volatile = await freshness.voice_freshness(session, [asset_id], today=TODAY, keys=["ter", "geography"])

    assert set(duration_only) == {"modified_duration"}, duration_only
    assert none_volatile == {}, "no volatile voice asked: nothing"


async def test_a_voice_emptied_on_purpose_has_no_now_to_be_stale(engine: AsyncEngine) -> None:
    """The duration emptied by hand 40 days ago (a NULL row over a value): no answer for it."""
    asset_id = await _asset(engine)
    await _row(engine, asset_id, "modified_duration", "1.8", SOURCE, TODAY - timedelta(days=90))
    async with AsyncSession(engine) as session:
        session.add(AssetProfileUpdate(asset_id=asset_id, key="modified_duration", value=None, source="user", read_on=TODAY - timedelta(days=40)))
        await session.commit()

    assert await _freshness(engine, asset_id) == {}, "an emptied voice is never stale"
