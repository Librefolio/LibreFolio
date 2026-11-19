"""The store of the asset profile (project 68, lot A3): write a voice only when it changes, read it as steps.

The contract is the docstring of ``backend/app/services/assets/profile/store.py``. Pinned here:

1. ``profile_today(session, now)``: today in ``scheduler_timezone`` (a saved global setting), UTC when it is not set or
   not a valid zone; ``now`` falls on another date in UTC than in the zone.
2. ``current_rows``: «now» of each voice is its last row in (``read_on``, ``id``) order, also when ids and days run in
   different orders; ``keys`` narrows it; another asset's rows never count.
3. ``write_values`` writes a row only when the stored form (``catalogue.normalize_value``) differs from now, whoever wrote
   either — the source alone never makes a row; a map with its keys in another order or another rounding, or a row whose
   JSON text was written another way, is the same value. ``force_source`` writes the source's row with the same value,
   unless now is already that value from that source. ``None`` is a NULL row when the voice has a value, nothing when
   it has none. Writes of one call apply in order. One refused value (or an unknown voice) raises ``ProfileValueError``
   and writes nothing. ``read_on`` is today, or now's ``read_on`` when today is before it. A ``user`` row keeps its
   ``user_id``, a source row has none; ``source_date`` is stored, and a reading that changes only ``source_date`` makes
   no row (plan §3.7). Two connections writing the same new value together make one row (the write lock,
   ``db.session.begin_writes``, is taken before the comparison), and the lock is held until the caller commits: a second
   connection that will not wait (``busy_timeout=0``) gets «database is locked» meanwhile, whether the first wrote a row
   or found its value already there, and after the commit writes nothing.
4. ``read_steps``: one step per stretch, ``date`` … ``through``, from the first row (or from ``start`` with
   ``carry_back``, per voice); ``start: "min"`` resolved per asset among the voices asked; nothing for an asset without
   rows or a first row after ``end``. With ``carry_back`` (plan I18, developer round 9: «for a date we do not have, the
   oldest we have») a voice whose first row comes after ``end`` answers ONE step ``start`` … ``end`` holding that first
   row's value and source (``update_id`` that row); a voice with no row at all, and an asset with none, stay left out:
   nothing to carry. One day with ``DateRangeModel(start=d)``; several rows on one day: the last holds;
   neighbours with the same value and the same source are one step; ``keys=None`` is every voice, an unknown key is
   refused. The steps work with ``financial_math.series_steps`` (``value_at``, ``points_between``).
5. ``forget_updates``: «now» and the steps follow from the rows left (neighbours merge again when value and source
   match); all or nothing: ``ProfileUpdatesNotFound`` for an id that is not the asset's, ``ProfileUpdatesNewer`` for a
   row created after ``as_of``; the count.
6. ``recent_changes``: newest first in (``read_on``, ``id``) order, 20 a page, ``total``; each with the voice's value
   before it computed on the whole history (``has_previous`` False for the first row); the panel (``key=None``) leaves
   out the source rows of a volatile voice but those written by hand and the first source row after one; ``key=…`` is
   the whole history of that voice. ``total`` counts what that view lists (the panel's rows, or the voice's).
7. A row whose JSON text was written another way (``'{"USA": "0.6", "JPN": "0.4"}'``, ``'"0.00220"'``) is read back in
   its stored form, exactly ``normalize_value(key, value)``: in ``current_rows``, in the steps, and in the rows and the
   previous values of ``recent_changes``.

Every database is a private SQLite file under ``tmp_path`` built with ``SQLModel.metadata.create_all``, opened as
production opens its own (aiosqlite, NullPool, the PRAGMA listener of ``backend.app.db.session``: WAL, busy_timeout,
foreign keys), every engine disposed at teardown. Scenes are seeded through the ``AssetProfileUpdate`` model, whose
``value`` is plain text: a non-canonical JSON text goes in verbatim. Stored values are compared decoded (``json.loads``)
or through ``normalize_value``, never as the JSON text the store writes. No server, no lane database, no clock: every
day is passed as ``today`` or seeded, every moment as ``now``/``as_of``.

Red until A3: every function of the store raises ``NotImplementedError``; each test fails on it, never at collection.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.util import await_only

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetProfileUpdate, AssetType, GlobalSetting, User
from backend.app.schemas.common import DateRangeModel, MinStartDateRangeModel
from backend.app.services.assets.profile import store
from backend.app.services.assets.profile.catalogue import ProfileValueError, normalize_value
from backend.app.services.assets.profile.store import ProfileStep, ProfileUpdatesNewer, ProfileUpdatesNotFound, ProfileWrite
from backend.app.services.financial_math.series_steps import points_between, value_at

pytestmark = pytest.mark.asyncio

D = date.fromisoformat

#: Realistic readings: a TER of 0.22 % and 0.19 % (justETF), 0.20 % written by hand; the stored forms.
TER_022, TER_020, TER_019 = "0.0022", "0.002", "0.0019"
#: The same countries read twice, with keys in another order and another rounding: one stored form.
GEO_FINE = {"USA": "0.60331", "JPN": "0.39669"}
GEO_ROUNDED = {"JPN": "0.3967", "USA": "0.6033"}
#: A JSON text written another way than the store writes it: key order and digits differ from the stored form.
GEO_LOOSE_TEXT = '{"USA": "0.6", "JPN": "0.4"}'
GEO_LOOSE = {"USA": "0.6", "JPN": "0.4"}
DESCRIPTION = "The fund tracks the MSCI World index: large and mid caps of 23 developed markets."
FUND_SIZE = {"amount": "1250000000", "currency": "EUR"}

#: Far above any id a private database of a few rows reaches.
NEVER_WRITTEN_ID = 987_654_321
#: The seed helper's default: store ``value`` in its stored form (``raw_text`` given: that text, verbatim).
_FROM_VALUE = object()
#: The first word of a statement that writes: the barrier of the concurrency case fires on the first of them.
WRITE_STATEMENTS = frozenset({"INSERT", "UPDATE", "DELETE", "REPLACE", "BEGIN", "SAVEPOINT"})


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def _no_timezone_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """``LIBREFOLIO_DEFAULT_TIMEZONE`` stands behind ``scheduler_timezone`` until an administrator saves it: never here."""
    monkeypatch.delenv("LIBREFOLIO_DEFAULT_TIMEZONE", raising=False)


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own, disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'asset_profile_store.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
            pragmas = [(await connection.execute(text(f"PRAGMA {name}"))).scalar() for name in ("journal_mode", "foreign_keys", "busy_timeout")]
        assert pragmas == ["wal", 1, 30000], f"barrier: the app's pragmas (db/session.py) must hold on the private file: {pragmas}"
        yield engine
    finally:
        await engine.dispose()


async def _asset(engine: AsyncEngine, name: str = "iShares Core MSCI World") -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=name, currency="EUR", asset_type=AssetType.ETF)
        session.add(asset)
        await session.commit()
    return int(asset.id)


async def _user(engine: AsyncEngine, name: str = "alice") -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=name, email=f"{name}@example.com", hashed_password="$argon2id$seeded-account")
        session.add(user)
        await session.commit()
    return int(user.id)


async def _seed(
    engine: AsyncEngine,
    asset_id: int,
    key: str,
    value: Any,
    source: str,
    read_on: date,
    *,
    raw_text: Any = _FROM_VALUE,
    user_id: int | None = None,
    created_at: datetime | None = None,
    source_date: date | None = None,
) -> int:
    """One row written as the model writes it, without the store: ``value`` in its stored form, or ``raw_text`` verbatim."""
    stored = (None if value is None else json.dumps(normalize_value(key, value))) if raw_text is _FROM_VALUE else raw_text
    fields: dict[str, Any] = {"asset_id": asset_id, "key": key, "value": stored, "source": source, "user_id": user_id, "read_on": read_on, "source_date": source_date}
    if created_at is not None:
        fields["created_at"] = created_at
    async with AsyncSession(engine, expire_on_commit=False) as session:
        row = AssetProfileUpdate(**fields)
        session.add(row)
        await session.commit()
    return int(row.id)


async def _db_rows(engine: AsyncEngine, asset_id: int, key: str | None = None) -> list[dict[str, Any]]:
    """The asset's rows as stored, by id, read with plain SQL; ``value`` decoded, ``is_null`` true when the column is NULL."""
    query = "SELECT id, key, value, value IS NULL AS is_null, source, user_id, read_on, source_date FROM asset_profile_updates WHERE asset_id = :asset"
    parameters: dict[str, Any] = {"asset": asset_id}
    if key is not None:
        query += " AND key = :key"
        parameters["key"] = key
    async with AsyncSession(engine) as session:
        result = await session.execute(text(query + " ORDER BY id"), parameters)
        rows = [dict(row._mapping) for row in result]
    for row in rows:
        row["value"] = None if row["value"] is None else json.loads(row["value"])
        row["is_null"] = bool(row["is_null"])
    return rows


async def _write(engine: AsyncEngine, asset_id: int, *writes: ProfileWrite, today: date) -> list[store.ProfileRow]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        rows = await store.write_values(session, asset_id, list(writes), today=today)
        await session.commit()
    return rows


async def _now(engine: AsyncEngine, asset_id: int, keys: Iterable[str] | None = None) -> dict[str, store.ProfileRow]:
    async with AsyncSession(engine) as session:
        return await store.current_rows(session, asset_id, keys)


async def _steps(
    engine: AsyncEngine,
    asset_ids: Sequence[int],
    date_range: DateRangeModel | MinStartDateRangeModel,
    keys: Iterable[str] | None = None,
    *,
    carry_back: bool = False,
) -> dict[int, dict[str, list[ProfileStep]]]:
    async with AsyncSession(engine) as session:
        return await store.read_steps(session, asset_ids, date_range, keys, carry_back=carry_back)


async def _forget(engine: AsyncEngine, asset_id: int, update_ids: Sequence[int], *, as_of: datetime | None = None) -> int:
    async with AsyncSession(engine) as session:
        count = await store.forget_updates(session, asset_id, update_ids, as_of=as_of)
        await session.commit()
    return count


async def _changes(engine: AsyncEngine, asset_id: int, **arguments: Any) -> store.ProfileChangesPage:
    async with AsyncSession(engine) as session:
        return await store.recent_changes(session, asset_id, **arguments)


def _span(start: str, end: str | None = None) -> DateRangeModel:
    return DateRangeModel(start=D(start), end=None if end is None else D(end))


def _from_min(end: str) -> MinStartDateRangeModel:
    return MinStartDateRangeModel(start="min", end=D(end))


def _shape(steps: Sequence[ProfileStep]) -> list[tuple[date, date, Any, str]]:
    """Steps as (date, through, value, source): the comparison every reading case makes."""
    return [(step.date, step.through, step.value, step.source) for step in steps]


def _plan_example_rows() -> list[tuple[str, Any, str, date]]:
    """The plan's example: TER 0.22 % read by justETF on 12/11, 0.19 % on 03/12."""
    return [("ter", "0.0022", "justetf", D("2026-11-12")), ("ter", "0.0019", "justetf", D("2026-12-03"))]


async def _seed_all(engine: AsyncEngine, asset_id: int, rows: Iterable[tuple[str, Any, str, date]]) -> list[int]:
    return [await _seed(engine, asset_id, key, value, source, read_on) for key, value, source, read_on in rows]


# =============================================================================
# 1. TODAY IN THE SCHEDULER'S TIME ZONE
# =============================================================================


@pytest.mark.parametrize(
    ("zone", "now", "expected"),
    [
        pytest.param(None, datetime(2026, 11, 15, 23, 30, tzinfo=UTC), D("2026-11-15"), id="not-set-is-utc"),
        pytest.param("Pacific/Auckland", datetime(2026, 11, 15, 23, 30, tzinfo=UTC), D("2026-11-16"), id="auckland-is-already-tomorrow"),
        pytest.param("America/Los_Angeles", datetime(2026, 11, 16, 3, 0, tzinfo=UTC), D("2026-11-15"), id="los-angeles-is-still-yesterday"),
        pytest.param("Not/AZone", datetime(2026, 11, 15, 23, 30, tzinfo=UTC), D("2026-11-15"), id="not-a-zone-is-utc"),
    ],
)
async def test_profile_today_is_the_date_in_the_scheduler_timezone(engine: AsyncEngine, zone: str | None, now: datetime, expected: date) -> None:
    """``profile_today`` is ``now``'s date in ``scheduler_timezone`` as an administrator saved it; UTC when not set or not valid."""
    if zone is not None:
        admin = await _user(engine, "admin")
        async with AsyncSession(engine) as session:
            session.add(GlobalSetting(key="scheduler_timezone", value=zone, value_type="str", updated_by_user_id=admin))
            await session.commit()
    async with AsyncSession(engine) as session:
        today = await store.profile_today(session, now)
    assert today == expected, f"{now.isoformat()} in {zone or 'UTC (not set)'} is {expected}, the store said {today}"


# =============================================================================
# 2. NOW
# =============================================================================


async def test_current_rows_is_the_last_row_of_each_voice_of_the_asset(engine: AsyncEngine) -> None:
    """«Now» per voice is its last row in (read_on, id) order; ``keys`` narrows it; another asset's rows never count."""
    asset, other = await _asset(engine), await _asset(engine, "Vanguard FTSE All-World")
    _first, ter_now = await _seed_all(engine, asset, _plan_example_rows())
    geo = await _seed(engine, asset, "geography", GEO_FINE, "justetf", D("2026-11-20"))
    text_row = await _seed(engine, asset, "description", DESCRIPTION, "justetf", D("2026-11-12"))
    await _seed(engine, other, "ter", "0.0007", "justetf", D("2026-12-10"))

    now = await _now(engine, asset)
    assert {key: row.id for key, row in now.items()} == {"ter": ter_now, "geography": geo, "description": text_row}
    assert (now["ter"].value, now["ter"].source, now["ter"].read_on, now["ter"].asset_id) == (TER_019, "justetf", D("2026-12-03"), asset)
    assert normalize_value("geography", now["geography"].value) == normalize_value("geography", GEO_FINE)
    assert set(await _now(engine, asset, ["ter"])) == {"ter"}, "keys narrows the voices"
    assert await _now(engine, await _asset(engine, "No rows yet")) == {}, "an asset without rows has no voice now"


# =============================================================================
# 3. WRITING
# =============================================================================


@pytest.mark.parametrize(
    ("source", "value", "writes_a_row"),
    [
        pytest.param("justetf", "0.0022", False, id="same-value-same-source"),
        pytest.param("justetf", "0.00220", False, id="same-value-another-spelling"),
        pytest.param("yfinance", "0.0022", False, id="same-value-another-source"),
        pytest.param("user", "0.0022", False, id="same-value-by-hand"),
        pytest.param("justetf", "0.0019", True, id="a-different-value"),
    ],
)
async def test_a_row_is_written_only_when_the_value_differs_from_now(engine: AsyncEngine, source: str, value: str, writes_a_row: bool) -> None:
    """Different from now, whoever wrote either: the source alone never makes a row."""
    asset = await _asset(engine)
    seeded = await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-10"))
    user_id = await _user(engine) if source == "user" else None

    written = await _write(engine, asset, ProfileWrite(key="ter", value=value, source=source, user_id=user_id), today=D("2026-11-12"))

    rows = await _db_rows(engine, asset)
    if writes_a_row:
        assert [(row.key, row.value, row.source) for row in written] == [("ter", normalize_value("ter", value), source)]
        assert [row["id"] for row in rows] == [seeded, written[0].id]
        assert (rows[1]["value"], rows[1]["source"]) == (normalize_value("ter", value), source)
    else:
        assert written == [], f"{value!r} from {source} is now's value: no row, got {written}"
        assert [row["id"] for row in rows] == [seeded]


async def test_a_value_by_hand_then_a_source_reading_makes_two_rows(engine: AsyncEngine) -> None:
    """The user writes 0.20 %, then justETF reads 0.22 %: two rows, and now is justETF's."""
    asset, alice = await _asset(engine), await _user(engine)
    await _write(engine, asset, ProfileWrite(key="ter", value="0.0020", source="user", user_id=alice), today=D("2026-11-10"))
    await _write(engine, asset, ProfileWrite(key="ter", value="0.0022", source="justetf"), today=D("2026-11-12"))

    assert [(row["value"], row["source"], row["user_id"]) for row in await _db_rows(engine, asset)] == [(TER_020, "user", alice), (TER_022, "justetf", None)]
    now = (await _now(engine, asset))["ter"]
    assert (now.value, now.source) == (TER_022, "justetf")


@pytest.mark.parametrize("source", ["justetf", "yfinance"])
async def test_a_map_with_keys_in_another_order_or_rounding_is_the_same_value(engine: AsyncEngine, source: str) -> None:
    """{"USA":"0.60331","JPN":"0.39669"} then {"JPN":"0.3967","USA":"0.6033"}: one stored form, one row."""
    asset = await _asset(engine)
    first = await _write(engine, asset, ProfileWrite(key="geography", value=GEO_FINE, source="justetf"), today=D("2026-11-10"))
    again = await _write(engine, asset, ProfileWrite(key="geography", value=GEO_ROUNDED, source=source), today=D("2026-11-12"))

    assert len(first) == 1 and again == [], f"the same countries must not make a second row: {again}"
    assert [row["id"] for row in await _db_rows(engine, asset)] == [first[0].id]


async def test_a_row_with_json_written_another_way_is_the_same_value_for_writes_and_steps(engine: AsyncEngine) -> None:
    """A row holding non-canonical JSON text (order and digits differ): writing the same value makes no row, and the
    steps make one stretch across it and a later canonical row of the same value and source — one «same value» rule."""
    asset = await _asset(engine)
    loose = await _seed(engine, asset, "geography", None, "justetf", D("2026-11-01"), raw_text=GEO_LOOSE_TEXT)

    written = await _write(engine, asset, ProfileWrite(key="geography", value=GEO_LOOSE, source="justetf"), today=D("2026-11-10"))
    assert written == [], f"{GEO_LOOSE_TEXT} is now's value whatever its text: no row, got {written}"

    canonical = await _seed(engine, asset, "geography", GEO_LOOSE, "justetf", D("2026-11-20"))
    steps = (await _steps(engine, [asset], _span("2026-11-01", "2026-11-30")))[asset]["geography"]
    assert [(step.date, step.through, step.source, step.update_id) for step in steps] == [(D("2026-11-01"), D("2026-11-30"), "justetf", loose)], f"rows {loose} and {canonical} hold the same value from the same source: one step"
    assert normalize_value("geography", steps[0].value) == normalize_value("geography", GEO_LOOSE)


async def test_force_source_writes_the_same_value_in_the_sources_name(engine: AsyncEngine) -> None:
    """«Use the source's value»: now is 0.20 % by hand, justETF says 0.20 % too → one row in justETF's name, a new step."""
    asset, alice = await _asset(engine), await _user(engine)
    by_hand = await _seed(engine, asset, "ter", "0.0020", "user", D("2026-11-01"), user_id=alice)

    written = await _write(engine, asset, ProfileWrite(key="ter", value="0.0020", source="justetf", force_source=True), today=D("2026-11-10"))

    assert [(row.value, row.source, row.user_id, row.read_on) for row in written] == [(TER_020, "justetf", None, D("2026-11-10"))]
    assert (await _now(engine, asset))["ter"].id == written[0].id
    steps = (await _steps(engine, [asset], _span("2026-11-01", "2026-11-20")))[asset]["ter"]
    assert _shape(steps) == [(D("2026-11-01"), D("2026-11-09"), TER_020, "user"), (D("2026-11-10"), D("2026-11-20"), TER_020, "justetf")]
    assert [step.update_id for step in steps] == [by_hand, written[0].id]


async def test_force_source_writes_nothing_when_now_is_already_that_value_from_that_source(engine: AsyncEngine) -> None:
    asset = await _asset(engine)
    seeded = await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-01"))

    written = await _write(engine, asset, ProfileWrite(key="ter", value="0.0022", source="justetf", force_source=True), today=D("2026-11-10"))

    assert written == []
    assert [row["id"] for row in await _db_rows(engine, asset)] == [seeded]


async def test_none_on_a_voice_with_a_value_is_a_null_row_read_as_an_empty_step(engine: AsyncEngine) -> None:
    """«Lascia vuoto»: the user empties the TER on purpose → a NULL row, a step whose value is None."""
    asset, alice = await _asset(engine), await _user(engine)
    await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-01"))

    written = await _write(engine, asset, ProfileWrite(key="ter", value=None, source="user", user_id=alice), today=D("2026-11-10"))

    assert [(row.value, row.source, row.user_id) for row in written] == [(None, "user", alice)]
    stored = (await _db_rows(engine, asset))[-1]
    assert stored["id"] == written[0].id and stored["is_null"], f"an empty value is stored as NULL, not as JSON text: {stored}"
    now = (await _now(engine, asset))["ter"]
    assert (now.id, now.value) == (written[0].id, None)
    steps = (await _steps(engine, [asset], _span("2026-11-01", "2026-11-20")))[asset]["ter"]
    assert _shape(steps) == [(D("2026-11-01"), D("2026-11-09"), TER_022, "justetf"), (D("2026-11-10"), D("2026-11-20"), None, "user")]


async def test_none_on_a_voice_without_rows_writes_nothing(engine: AsyncEngine) -> None:
    asset, alice = await _asset(engine), await _user(engine)

    written = await _write(engine, asset, ProfileWrite(key="description", value=None, source="user", user_id=alice), today=D("2026-11-10"))

    assert written == [] and await _db_rows(engine, asset) == []
    assert await _steps(engine, [asset], _span("2026-11-01", "2026-11-20")) == {}


@pytest.mark.parametrize(
    ("writes", "expected"),
    [
        pytest.param([("0.0022", "justetf"), ("0.0022", "yfinance")], [(TER_022, "justetf")], id="the-second-equals-the-first"),
        pytest.param([("0.0022", "justetf"), ("0.0019", "justetf")], [(TER_022, "justetf"), (TER_019, "justetf")], id="the-second-differs-from-the-first"),
        pytest.param([("0.0022", "justetf"), ("0.0019", "justetf"), ("0.00190", "yfinance")], [(TER_022, "justetf"), (TER_019, "justetf")], id="the-third-equals-the-second"),
    ],
)
async def test_writes_of_one_call_apply_in_order(engine: AsyncEngine, writes: list[tuple[str, str]], expected: list[tuple[str, str]]) -> None:
    """Two (or more) writes of the same voice in one call: each compares with the one before it."""
    asset = await _asset(engine)

    written = await _write(engine, asset, *(ProfileWrite(key="ter", value=value, source=source) for value, source in writes), today=D("2026-11-10"))

    assert [(row.value, row.source) for row in written] == expected
    assert [row["id"] for row in await _db_rows(engine, asset)] == [row.id for row in written]
    assert (await _now(engine, asset))["ter"].id == written[-1].id, "the last row written is now"


@pytest.mark.parametrize(
    ("writes", "refused_key"),
    [
        pytest.param([ProfileWrite(key="ter", value="0.0019", source="justetf"), ProfileWrite(key="ter", value="-0.001", source="justetf")], "ter", id="a-negative-ter"),
        pytest.param([ProfileWrite(key="geography", value=GEO_FINE, source="justetf"), ProfileWrite(key="ter", value=0.0019, source="justetf")], "ter", id="a-float"),
        pytest.param([ProfileWrite(key="ter", value="0.0019", source="justetf"), ProfileWrite(key="not_a_voice", value="x", source="justetf")], "not_a_voice", id="an-unknown-voice"),
    ],
)
async def test_one_refused_value_writes_nothing(engine: AsyncEngine, writes: list[ProfileWrite], refused_key: str) -> None:
    """Every value is checked first: ``ProfileValueError`` naming the voice, and nothing written — even after a commit."""
    asset = await _asset(engine)
    async with AsyncSession(engine) as session:
        with pytest.raises(ProfileValueError) as refused:
            await store.write_values(session, asset, writes, today=D("2026-11-10"))
        await session.commit()

    assert refused.value.key == refused_key
    assert await _db_rows(engine, asset) == [], "one refused value writes nothing, the valid ones before it included"


async def test_a_write_dated_before_now_takes_nows_read_on_and_becomes_now(engine: AsyncEngine) -> None:
    """The scheduler's time zone moved back a day: ``today`` (09/11) is before now's ``read_on`` (10/11) → the new row
    takes 10/11, and is now (the last in (read_on, id) order), and holds that day."""
    asset = await _asset(engine)
    await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-10"))

    written = await _write(engine, asset, ProfileWrite(key="ter", value="0.0019", source="justetf"), today=D("2026-11-09"))

    assert [row.read_on for row in written] == [D("2026-11-10")]
    assert (await _now(engine, asset))["ter"].id == written[0].id
    steps = (await _steps(engine, [asset], _span("2026-11-10", "2026-11-12")))[asset]["ter"]
    assert _shape(steps) == [(D("2026-11-10"), D("2026-11-12"), TER_019, "justetf")]


async def test_a_normal_write_takes_today_whatever_the_other_voices(engine: AsyncEngine) -> None:
    """``read_on`` is today; another voice read on a later day does not move it."""
    asset = await _asset(engine)
    await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-10"))
    await _seed(engine, asset, "geography", GEO_FINE, "justetf", D("2026-11-20"))

    written = await _write(engine, asset, ProfileWrite(key="ter", value="0.0019", source="justetf"), today=D("2026-11-12"))

    assert [row.read_on for row in written] == [D("2026-11-12")]


async def test_user_rows_keep_their_author_source_rows_have_none_and_source_date_is_stored(engine: AsyncEngine) -> None:
    asset, alice = await _asset(engine), await _user(engine)

    written = await _write(
        engine,
        asset,
        ProfileWrite(key="ter", value="0.0020", source="user", user_id=alice),
        ProfileWrite(key="fund_size", value=FUND_SIZE, source="justetf", source_date=D("2026-09-30")),
        today=D("2026-11-12"),
    )

    assert [(row.key, row.source, row.user_id, row.source_date, row.read_on) for row in written] == [
        ("ter", "user", alice, None, D("2026-11-12")),
        ("fund_size", "justetf", None, D("2026-09-30"), D("2026-11-12")),
    ]
    stored = await _db_rows(engine, asset)
    assert [(row["key"], row["user_id"], row["source_date"]) for row in stored] == [("ter", alice, None), ("fund_size", None, "2026-09-30")]
    assert stored[1]["value"] == normalize_value("fund_size", FUND_SIZE)


async def test_two_connections_writing_the_same_new_value_together_make_one_row(engine: AsyncEngine) -> None:
    """Two equal readings arrive together (plan §3.7): the second connection's write runs, and right before its first
    write statement — a barrier, no sleep — the first connection writes the same new value and commits. The store takes
    the write lock before comparing, so the second sees the first's row and writes nothing: exactly one row.

    A store that compares and then inserts has already read «no row» when the rival commits, and writes a second one.
    """
    asset = await _asset(engine)
    reading = ProfileWrite(key="ter", value="0.0022", source="justetf")
    rival_rows: list[store.ProfileRow] = []
    fired: list[str] = []

    async def rival() -> None:
        async with AsyncSession(first, expire_on_commit=False) as session:
            rival_rows.extend(await store.write_values(session, asset, [reading], today=D("2026-11-12")))
            await session.commit()

    def before_cursor_execute(_connection: Any, _cursor: Any, statement: str, _parameters: Any, _context: Any, _executemany: bool) -> None:
        words = statement.split(None, 1)
        if fired or not words or words[0].upper() not in WRITE_STATEMENTS:
            return
        fired.append(statement)
        await_only(rival())

    first = create_async_engine(engine.url, poolclass=NullPool)
    second = create_async_engine(engine.url, poolclass=NullPool)
    event.listen(second.sync_engine, "before_cursor_execute", before_cursor_execute)
    try:
        async with AsyncSession(second, expire_on_commit=False) as session:
            written = await store.write_values(session, asset, [reading], today=D("2026-11-12"))
            await session.commit()
    finally:
        event.remove(second.sync_engine, "before_cursor_execute", before_cursor_execute)
        await first.dispose()
        await second.dispose()

    assert fired, "barrier: the second connection must issue a write statement, the rival running right before it"
    assert len(rival_rows) == 1, f"barrier: the rival writes the new value: {rival_rows}"
    assert written == [], f"the second connection must find the rival's row under the lock and write nothing: {written}"
    assert [row["id"] for row in await _db_rows(engine, asset)] == [rival_rows[0].id]


@pytest.mark.parametrize("first_writes_a_row", [True, False], ids=["the-first-writes-a-row", "the-first-finds-its-value"])
async def test_the_write_lock_is_held_until_the_caller_commits(engine: AsyncEngine, first_writes_a_row: bool) -> None:
    """The first connection's ``write_values`` returns without committing: the lock it took (``begin_writes``) is still
    held, so a second connection that will not wait (``busy_timeout=0``) gets «database is locked» writing the same voice,
    whether the first wrote a row or found its value already there. Once the first commits, the second writes nothing.
    A second connection that is NOT refused means ``write_values`` takes no lock."""
    asset = await _asset(engine)
    if not first_writes_a_row:
        await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-10"))
    reading = ProfileWrite(key="ter", value="0.0022", source="justetf")

    def no_wait(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=0")
        cursor.close()

    impatient = create_async_engine(engine.url, poolclass=NullPool)
    event.listen(impatient.sync_engine, "connect", no_wait)
    try:
        async with impatient.connect() as connection:
            timeout = (await connection.execute(text("PRAGMA busy_timeout"))).scalar()
        assert timeout == 0, f"barrier: the second connection must not wait for the lock: busy_timeout {timeout}"

        async with AsyncSession(engine, expire_on_commit=False) as first:
            held = await store.write_values(first, asset, [reading], today=D("2026-11-12"))
            assert len(held) == (1 if first_writes_a_row else 0), f"barrier: the first connection's write: {held}"
            async with AsyncSession(impatient) as second:
                with pytest.raises(OperationalError) as refused:
                    await store.write_values(second, asset, [reading], today=D("2026-11-12"))
            assert "database is locked" in str(refused.value), f"the second connection must meet the first's write lock: {refused.value}"
            await first.commit()

        async with AsyncSession(impatient) as second:
            after = await store.write_values(second, asset, [reading], today=D("2026-11-12"))
            await second.commit()
    finally:
        await impatient.dispose()

    assert after == [], f"after the first commits, the same value is now's: no row, got {after}"
    assert len(await _db_rows(engine, asset)) == 1


@pytest.mark.parametrize("source", ["justetf", "yfinance"])
async def test_a_reading_that_changes_only_source_date_makes_no_row(engine: AsyncEngine, source: str) -> None:
    """Plan §3.7: «cambia solo source_date → nessuna riga». The TER read again with data at 31/10 instead of 30/09."""
    asset = await _asset(engine)
    first = await _write(engine, asset, ProfileWrite(key="ter", value="0.0022", source="justetf", source_date=D("2026-09-30")), today=D("2026-10-05"))

    again = await _write(engine, asset, ProfileWrite(key="ter", value="0.0022", source=source, source_date=D("2026-10-31")), today=D("2026-11-05"))

    assert again == [], f"only source_date changed: no row, got {again}"
    stored = await _db_rows(engine, asset)
    assert [(row["id"], row["source_date"]) for row in stored] == [(first[0].id, "2026-09-30")]


# =============================================================================
# 4. READING STEPS
# =============================================================================


async def test_the_plans_example_gives_two_steps(engine: AsyncEngine) -> None:
    """0.22 % on 12/11 and 0.19 % on 03/12 (justETF), from min to 20/12: 12/11–02/12 and 03/12–20/12."""
    asset = await _asset(engine)
    first, second = await _seed_all(engine, asset, _plan_example_rows())

    steps = await _steps(engine, [asset], _from_min("2026-12-20"))

    assert set(steps) == {asset} and set(steps[asset]) == {"ter"}
    assert _shape(steps[asset]["ter"]) == [(D("2026-11-12"), D("2026-12-02"), TER_022, "justetf"), (D("2026-12-03"), D("2026-12-20"), TER_019, "justetf")]
    assert [step.update_id for step in steps[asset]["ter"]] == [first, second]


@pytest.mark.parametrize(
    ("date_range", "keys", "carry_back", "first_days"),
    [
        pytest.param(_span("2026-10-01", "2026-12-20"), None, False, {"ter": D("2026-11-12"), "geography": D("2026-11-20")}, id="from-each-voices-first-row"),
        pytest.param(_span("2026-10-01", "2026-12-20"), None, True, {"ter": D("2026-10-01"), "geography": D("2026-10-01")}, id="carried-back-to-start"),
        pytest.param(_from_min("2026-12-20"), None, True, {"ter": D("2026-11-12"), "geography": D("2026-11-12")}, id="min-carried-back-to-the-assets-first-day"),
        pytest.param(_from_min("2026-12-20"), ["geography"], True, {"geography": D("2026-11-20")}, id="min-among-the-voices-asked"),
        pytest.param(_from_min("2026-12-20"), None, False, {"ter": D("2026-11-12"), "geography": D("2026-11-20")}, id="min-without-carry-back"),
    ],
)
async def test_steps_start_at_each_voices_first_row_or_at_start_with_carry_back(engine: AsyncEngine, date_range: DateRangeModel | MinStartDateRangeModel, keys: list[str] | None, carry_back: bool, first_days: dict[str, date]) -> None:
    """A range starting before the first row: the steps start at the first row; ``carry_back`` stretches each voice's
    first step back to ``start`` (``min``: the asset's first ``read_on`` among the voices asked), voice by voice."""
    asset = await _asset(engine)
    await _seed_all(engine, asset, _plan_example_rows())
    await _seed(engine, asset, "geography", GEO_FINE, "justetf", D("2026-11-20"))

    steps = (await _steps(engine, [asset], date_range, keys, carry_back=carry_back))[asset]

    assert {key: voice[0].date for key, voice in steps.items()} == first_days
    assert {key: voice[-1].through for key, voice in steps.items()} == dict.fromkeys(first_days, D("2026-12-20"))
    if "ter" in steps:
        assert [(step.date, step.value) for step in steps["ter"][1:]] == [(D("2026-12-03"), TER_019)]


@pytest.mark.parametrize("carry_back", [False, True])
async def test_nothing_stored_or_a_first_row_after_end_answers_nothing(engine: AsyncEngine, carry_back: bool) -> None:
    """``min`` on an asset without rows, a range ending before the first row, ``min`` resolved after ``end``: nothing,
    and the asset is left out of the answer."""
    asset, empty = await _asset(engine), await _asset(engine, "No rows yet")
    await _seed_all(engine, asset, _plan_example_rows())

    assert await _steps(engine, [empty], _from_min("2026-12-20"), carry_back=carry_back) == {}, "min on an asset without rows: nothing"
    # Without carry_back only: with it, the first row is carried back over the range (the test after this one).
    assert await _steps(engine, [asset], _span("2026-10-01", "2026-10-31")) == {}, "the first row after end: nothing"
    assert await _steps(engine, [asset], _from_min("2026-10-31"), carry_back=carry_back) == {}, "min resolved after end: nothing"
    both = await _steps(engine, [asset, empty], _from_min("2026-12-20"), carry_back=carry_back)
    assert set(both) == {asset}, "an asset with no step is left out of the answer"


async def test_carry_back_gives_a_range_before_the_first_row_the_oldest_value(engine: AsyncEngine) -> None:
    """Plan I18 (developer round 9, «for a date we do not have, the oldest we have»): with ``carry_back``, a range
    01/10–31/10 before the first rows (TER 12/11, countries 20/11) answers ONE step 01/10–31/10 per voice, holding its
    first row's value and source, ``update_id`` that row. A voice with no row at all (``description``) and an asset with
    no rows stay left out: nothing to carry. Without ``carry_back`` the same range answers nothing."""
    asset, empty = await _asset(engine), await _asset(engine, "No rows yet")
    ter_first, _ = await _seed_all(engine, asset, _plan_example_rows())
    geo_first = await _seed(engine, asset, "geography", GEO_FINE, "justetf", D("2026-11-20"))
    october = _span("2026-10-01", "2026-10-31")

    steps = await _steps(engine, [asset, empty], october, carry_back=True)

    assert set(steps) == {asset}, "the asset with rows carries its first rows back; the one with none has nothing to carry: left out"
    assert set(steps[asset]) == {"ter", "geography"}, "a voice with no rows (description) has nothing to carry: left out"
    assert _shape(steps[asset]["ter"]) == [(D("2026-10-01"), D("2026-10-31"), TER_022, "justetf")]
    assert normalize_value("geography", steps[asset]["geography"][0].value) == normalize_value("geography", GEO_FINE)
    assert [(step.date, step.through, step.update_id) for step in steps[asset]["geography"]] == [(D("2026-10-01"), D("2026-10-31"), geo_first)]
    assert steps[asset]["ter"][0].update_id == ter_first, "the step is the first row's"

    asked = await _steps(engine, [asset], october, ["ter", "description"], carry_back=True)
    assert set(asked[asset]) == {"ter"}, "a voice asked with no rows stays left out"
    assert await _steps(engine, [asset, empty], october) == {}, "without carry_back: nothing"


async def test_carry_back_fills_a_voice_whose_first_row_is_after_the_range(engine: AsyncEngine) -> None:
    """A range 12/11–15/11: the TER has a row in it, the countries start on 20/11. Without ``carry_back`` the countries are
    left out; with it they answer one step 12/11–15/11 holding their first row."""
    asset = await _asset(engine)
    await _seed_all(engine, asset, _plan_example_rows())
    geo_first = await _seed(engine, asset, "geography", GEO_FINE, "justetf", D("2026-11-20"))

    steps = (await _steps(engine, [asset], _span("2026-11-12", "2026-11-15"), carry_back=True))[asset]

    assert _shape(steps["ter"]) == [(D("2026-11-12"), D("2026-11-15"), TER_022, "justetf")]
    assert [(step.date, step.through, step.source, step.update_id) for step in steps["geography"]] == [(D("2026-11-12"), D("2026-11-15"), "justetf", geo_first)]


async def test_a_voice_with_no_step_in_the_range_is_left_out(engine: AsyncEngine) -> None:
    asset = await _asset(engine)
    await _seed_all(engine, asset, _plan_example_rows())
    await _seed(engine, asset, "geography", GEO_FINE, "justetf", D("2026-11-20"))

    steps = await _steps(engine, [asset], _span("2026-11-12", "2026-11-15"))

    assert set(steps[asset]) == {"ter"}


@pytest.mark.parametrize("carry_back", [False, True])
async def test_min_is_resolved_per_asset(engine: AsyncEngine, carry_back: bool) -> None:
    early, late = await _asset(engine), await _asset(engine, "Vanguard FTSE All-World")
    await _seed(engine, early, "ter", TER_022, "justetf", D("2026-11-12"))
    await _seed(engine, late, "ter", "0.0019", "justetf", D("2026-11-25"))

    steps = await _steps(engine, [early, late], _from_min("2026-12-20"), carry_back=carry_back)

    assert _shape(steps[early]["ter"]) == [(D("2026-11-12"), D("2026-12-20"), TER_022, "justetf")]
    assert _shape(steps[late]["ter"]) == [(D("2026-11-25"), D("2026-12-20"), TER_019, "justetf")]


@pytest.mark.parametrize(
    ("day", "carry_back", "expected"),
    [
        pytest.param("2026-11-25", False, [(D("2026-11-25"), D("2026-11-25"), TER_022, "justetf")], id="inside-the-first-step"),
        pytest.param("2026-12-03", False, [(D("2026-12-03"), D("2026-12-03"), TER_019, "justetf")], id="on-a-change"),
        pytest.param("2026-11-01", False, None, id="before-the-first-row"),
        pytest.param("2026-11-01", True, [(D("2026-11-01"), D("2026-11-01"), TER_022, "justetf")], id="before-the-first-row-carried-back"),
    ],
)
async def test_a_range_without_end_is_one_day(engine: AsyncEngine, day: str, carry_back: bool, expected: list[tuple[date, date, Any, str]] | None) -> None:
    """``DateRangeModel(start=d)``: one point, ``date == through == d``."""
    asset = await _asset(engine)
    await _seed_all(engine, asset, _plan_example_rows())

    steps = await _steps(engine, [asset], _span(day), carry_back=carry_back)

    if expected is None:
        assert steps == {}
    else:
        assert _shape(steps[asset]["ter"]) == expected


async def test_several_rows_on_one_day_the_last_holds_it(engine: AsyncEngine) -> None:
    asset = await _asset(engine)
    await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-12"))
    last = await _seed(engine, asset, "ter", TER_019, "justetf", D("2026-11-12"))

    steps = (await _steps(engine, [asset], _span("2026-11-10", "2026-11-20")))[asset]["ter"]

    assert _shape(steps) == [(D("2026-11-12"), D("2026-11-20"), TER_019, "justetf")] and steps[0].update_id == last
    assert (await _now(engine, asset))["ter"].id == last


async def test_now_and_the_last_step_agree_when_ids_and_days_run_in_different_orders(engine: AsyncEngine) -> None:
    """A row with a higher id and an older ``read_on``: the order is (read_on, id), for now and for the steps alike."""
    asset = await _asset(engine)
    later_day = await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-20"))
    higher_id = await _seed(engine, asset, "ter", TER_019, "justetf", D("2026-11-12"))
    assert higher_id > later_day, "barrier: the row of the older day has the higher id"

    steps = (await _steps(engine, [asset], _span("2026-11-01", "2026-11-30")))[asset]["ter"]
    now = (await _now(engine, asset))["ter"]

    assert _shape(steps) == [(D("2026-11-12"), D("2026-11-19"), TER_019, "justetf"), (D("2026-11-20"), D("2026-11-30"), TER_022, "justetf")]
    assert now.id == later_day == steps[-1].update_id, f"now ({now.id}) and the last step ({steps[-1].update_id}) must be the row last in (read_on, id): {later_day}"


@pytest.mark.parametrize(
    ("second_source", "expected"),
    [
        pytest.param("justetf", [(D("2026-11-01"), D("2026-11-30"), TER_022, "justetf")], id="same-value-same-source-one-step"),
        pytest.param("yfinance", [(D("2026-11-01"), D("2026-11-09"), TER_022, "justetf"), (D("2026-11-10"), D("2026-11-30"), TER_022, "yfinance")], id="same-value-another-source-two-steps"),
    ],
)
async def test_neighbouring_rows_merge_only_with_the_same_value_and_source(engine: AsyncEngine, second_source: str, expected: list[tuple[date, date, Any, str]]) -> None:
    asset = await _asset(engine)
    first = await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-01"))
    await _seed(engine, asset, "ter", TER_022, second_source, D("2026-11-10"))

    steps = (await _steps(engine, [asset], _span("2026-11-01", "2026-11-30")))[asset]["ter"]

    assert _shape(steps) == expected
    assert steps[0].update_id == first, "a step starts with its first row"


async def test_keys_none_reads_every_voice_and_an_unknown_key_is_refused(engine: AsyncEngine) -> None:
    asset = await _asset(engine)
    await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-12"))
    await _seed(engine, asset, "geography", GEO_FINE, "justetf", D("2026-11-12"))
    await _seed(engine, asset, "description", DESCRIPTION, "justetf", D("2026-11-12"))

    steps = await _steps(engine, [asset], _span("2026-11-12", "2026-11-20"))
    assert set(steps[asset]) == {"ter", "geography", "description"}
    assert steps[asset]["description"][0].value == DESCRIPTION

    with pytest.raises(ProfileValueError) as refused:
        await _steps(engine, [asset], _span("2026-11-12", "2026-11-20"), ["ter", "not_a_voice"])
    assert refused.value.key == "not_a_voice"


async def test_the_steps_work_with_series_steps(engine: AsyncEngine) -> None:
    """``value_at`` and ``points_between`` (``financial_math/series_steps.py``) read the steps as they come."""
    asset = await _asset(engine)
    await _seed_all(engine, asset, _plan_example_rows())
    steps = (await _steps(engine, [asset], _from_min("2026-12-20")))[asset]["ter"]

    assert value_at(steps, D("2026-11-20")) is steps[0]
    assert value_at(steps, D("2026-12-03")) is steps[1]
    assert value_at(steps, D("2026-11-11")) is None and value_at(steps, D("2026-12-21")) is None
    window = points_between(steps, D("2026-11-30"), D("2026-12-05"))
    assert all(isinstance(step, ProfileStep) for step in window)
    assert _shape(window) == [(D("2026-11-30"), D("2026-12-02"), TER_022, "justetf"), (D("2026-12-03"), D("2026-12-05"), TER_019, "justetf")]


# =============================================================================
# 4b. A ROW WRITTEN ANOTHER WAY IS READ IN ITS STORED FORM
# =============================================================================


@pytest.mark.parametrize(
    ("key", "raw_text", "other"),
    [
        pytest.param("geography", GEO_LOOSE_TEXT, GEO_FINE, id="a-map-in-another-order-and-digits"),
        pytest.param("ter", '"0.00220"', "0.0019", id="a-percentage-with-a-trailing-zero"),
    ],
)
async def test_a_row_written_another_way_is_read_in_its_stored_form(engine: AsyncEngine, key: str, raw_text: str, other: Any) -> None:
    """Rows with non-canonical JSON text (20/10 and 01/11) around a canonical one (25/10): ``current_rows``, the steps and
    ``recent_changes`` (rows and previous values) give exactly ``normalize_value(key, value)``, never the text as written."""
    asset = await _asset(engine)
    stored = normalize_value(key, json.loads(raw_text))
    other_stored = normalize_value(key, other)
    assert stored != json.loads(raw_text), "barrier: the text must differ from the stored form"
    oldest = await _seed(engine, asset, key, None, "justetf", D("2026-10-20"), raw_text=raw_text)
    middle = await _seed(engine, asset, key, other, "justetf", D("2026-10-25"))
    newest = await _seed(engine, asset, key, None, "justetf", D("2026-11-01"), raw_text=raw_text)

    now = (await _now(engine, asset))[key]
    steps = (await _steps(engine, [asset], _span("2026-10-20", "2026-11-10")))[asset][key]
    changes = await _changes(engine, asset, key=key)

    # One comparison of the three readers, so a red shows every one that returns the text as written
    read = {
        "current_rows": (now.id, now.value),
        "read_steps": [(step.update_id, step.value) for step in steps],
        "recent_changes": [(change.row.id, change.row.value, change.previous, change.has_previous) for change in changes.items],
    }
    assert read == {
        "current_rows": (newest, stored),
        "read_steps": [(oldest, stored), (middle, other_stored), (newest, stored)],
        "recent_changes": [(newest, stored, other_stored, True), (middle, other_stored, stored, True), (oldest, stored, None, False)],
    }, f"every reader must give the stored form {stored!r}, never the text as written ({raw_text}): {read}"


# =============================================================================
# 5. FORGETTING
# =============================================================================


async def test_forgetting_the_last_row_brings_now_back_to_the_row_before(engine: AsyncEngine) -> None:
    asset = await _asset(engine)
    first = await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-01"))
    last = await _seed(engine, asset, "ter", TER_019, "justetf", D("2026-11-10"))

    assert await _forget(engine, asset, [last]) == 1

    assert (await _now(engine, asset))["ter"].id == first
    steps = (await _steps(engine, [asset], _span("2026-11-01", "2026-11-20")))[asset]["ter"]
    assert _shape(steps) == [(D("2026-11-01"), D("2026-11-20"), TER_022, "justetf")]


@pytest.mark.parametrize(
    ("third_source", "expected"),
    [
        pytest.param("justetf", [(D("2026-11-01"), D("2026-11-20"), TER_022, "justetf")], id="same-source-the-neighbours-merge"),
        pytest.param("yfinance", [(D("2026-11-01"), D("2026-11-09"), TER_022, "justetf"), (D("2026-11-10"), D("2026-11-20"), TER_022, "yfinance")], id="another-source-two-steps"),
    ],
)
async def test_forgetting_a_row_in_the_middle_recomputes_the_steps(engine: AsyncEngine, third_source: str, expected: list[tuple[date, date, Any, str]]) -> None:
    """justETF 0.22 → user 0.20 → {justETF | yfinance} 0.22: forget the user's row → one step, or two when the sources differ."""
    asset, alice = await _asset(engine), await _user(engine)
    await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-01"))
    by_hand = await _seed(engine, asset, "ter", "0.0020", "user", D("2026-11-05"), user_id=alice)
    third = await _seed(engine, asset, "ter", TER_022, third_source, D("2026-11-10"))

    assert await _forget(engine, asset, [by_hand]) == 1

    steps = (await _steps(engine, [asset], _span("2026-11-01", "2026-11-20")))[asset]["ter"]
    assert _shape(steps) == expected
    now = (await _now(engine, asset))["ter"]
    assert (now.id, now.source) == (third, third_source)


async def test_forgetting_returns_the_count_and_every_row_of_a_voice_can_go(engine: AsyncEngine) -> None:
    asset = await _asset(engine)
    rows = await _seed_all(engine, asset, _plan_example_rows())
    kept = await _seed(engine, asset, "description", DESCRIPTION, "justetf", D("2026-11-12"))

    assert await _forget(engine, asset, rows) == 2

    assert set(await _now(engine, asset)) == {"description"}
    assert [row["id"] for row in await _db_rows(engine, asset)] == [kept]


@pytest.mark.parametrize("stranger", ["another-assets-row", "never-written"])
async def test_forgetting_an_id_that_is_not_the_assets_deletes_nothing(engine: AsyncEngine, stranger: str) -> None:
    asset, other = await _asset(engine), await _asset(engine, "Vanguard FTSE All-World")
    own = await _seed_all(engine, asset, _plan_example_rows())
    others = await _seed(engine, other, "ter", "0.0007", "justetf", D("2026-11-12"))
    foreign = others if stranger == "another-assets-row" else NEVER_WRITTEN_ID

    async with AsyncSession(engine) as session:
        with pytest.raises(ProfileUpdatesNotFound) as refused:
            await store.forget_updates(session, asset, [*own, foreign])
        await session.commit()

    assert (refused.value.asset_id, refused.value.update_ids) == (asset, (foreign,))
    assert [row["id"] for row in await _db_rows(engine, asset)] == own, "all or nothing: the asset's rows stay"
    assert [row["id"] for row in await _db_rows(engine, other)] == [others]


async def test_forgetting_a_row_newer_than_the_page_deletes_nothing(engine: AsyncEngine) -> None:
    """The page that asked was built at ``as_of``: a row created after it was never seen, so nothing is deleted."""
    asset = await _asset(engine)
    seen = await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-01"), created_at=datetime(2026, 11, 1, 10, 0, tzinfo=UTC))
    unseen = await _seed(engine, asset, "ter", TER_019, "justetf", D("2026-11-10"), created_at=datetime(2026, 11, 10, 10, 0, tzinfo=UTC))
    as_of = datetime(2026, 11, 5, 0, 0, tzinfo=UTC)

    async with AsyncSession(engine) as session:
        with pytest.raises(ProfileUpdatesNewer) as refused:
            await store.forget_updates(session, asset, [seen, unseen], as_of=as_of)
        await session.commit()

    assert (refused.value.asset_id, refused.value.update_ids) == (asset, (unseen,))
    assert [row["id"] for row in await _db_rows(engine, asset)] == [seen, unseen]
    assert await _forget(engine, asset, [seen], as_of=as_of) == 1, "a row the page had seen is forgotten"


# =============================================================================
# 6. RECENT CHANGES
# =============================================================================


def _expected_changes(rows: list[dict[str, Any]]) -> list[tuple[int, Any, bool]]:
    """(id, previous, has_previous) of every row, newest first in (read_on, id) order, previous on the voice's history."""
    previous: dict[int, tuple[Any, bool]] = {}
    by_key: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_key.setdefault(row["key"], []).append(row)
    for voice in by_key.values():
        voice.sort(key=lambda row: (row["read_on"], row["id"]))
        for index, row in enumerate(voice):
            previous[row["id"]] = (voice[index - 1]["value"], True) if index else (None, False)
    newest_first = sorted(rows, key=lambda row: (row["read_on"], row["id"]), reverse=True)
    return [(row["id"], *previous[row["id"]]) for row in newest_first]


def _listed(page: store.ProfileChangesPage) -> list[tuple[int, Any, bool]]:
    return [(change.row.id, change.previous, change.has_previous) for change in page.items]


async def test_changes_are_newest_first_twenty_a_page_with_the_value_before(engine: AsyncEngine) -> None:
    """25 changes of two non-volatile voices, ids and days in different orders: pages of 20 newest first in (read_on, id)
    order, ``total`` 25, each with the voice's value before it; another asset's rows never listed."""
    asset, other = await _asset(engine), await _asset(engine, "Vanguard FTSE All-World")
    for day in range(1, 16):
        await _seed(engine, asset, "ter", TER_022 if day % 2 else TER_019, "justetf", date(2026, 11, day))
    for day in range(10, 0, -1):  # the later day first: ids run against the days
        await _seed(engine, asset, "description", f"{DESCRIPTION} Revision {day}.", "justetf", date(2026, 11, day))
    await _seed(engine, other, "ter", "0.0007", "justetf", D("2026-11-30"))
    expected = _expected_changes(await _db_rows(engine, asset))
    assert len(expected) == 25

    first, second = await _changes(engine, asset), await _changes(engine, asset, page=1)

    assert (first.total, second.total) == (25, 25)
    assert _listed(first) == expected[:20] and _listed(second) == expected[20:]
    assert store.CHANGES_PAGE_SIZE == 20
    small = [await _changes(engine, asset, page=page, page_size=10) for page in range(3)]
    assert [len(page.items) for page in small] == [10, 10, 5] and [entry for page in small for entry in _listed(page)] == expected


async def test_the_panel_leaves_out_the_source_rows_of_a_volatile_voice(engine: AsyncEngine) -> None:
    """``yield_gross`` (volatile): justETF 3.1 %, 3.2 %, by hand 3.0 %, justETF 3.3 %, 3.4 % — the panel shows the hand row
    and the first source row after it, every row of the non-volatile TER; the previous value comes from the whole
    history (3.2 %, hidden). ``key=…`` lists every row of the voice."""
    asset, alice = await _asset(engine), await _user(engine)
    ter_first = await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-01"))
    hidden_first = await _seed(engine, asset, "yield_gross", "0.031", "justetf", D("2026-11-01"))
    hidden_second = await _seed(engine, asset, "yield_gross", "0.032", "justetf", D("2026-11-02"))
    by_hand = await _seed(engine, asset, "yield_gross", "0.030", "user", D("2026-11-03"), user_id=alice)
    after_hand = await _seed(engine, asset, "yield_gross", "0.033", "justetf", D("2026-11-04"))
    hidden_third = await _seed(engine, asset, "yield_gross", "0.034", "justetf", D("2026-11-05"))
    ter_second = await _seed(engine, asset, "ter", TER_019, "justetf", D("2026-11-06"))

    panel = await _changes(engine, asset)
    assert _listed(panel) == [(ter_second, TER_022, True), (after_hand, "0.03", True), (by_hand, "0.032", True), (ter_first, None, False)]
    assert panel.total == 4, "total counts the rows the panel lists"

    history = await _changes(engine, asset, key="yield_gross")
    assert _listed(history) == [(hidden_third, "0.033", True), (after_hand, "0.03", True), (by_hand, "0.032", True), (hidden_second, "0.031", True), (hidden_first, None, False)]
    assert history.total == 5
    assert [change.row.id for change in (await _changes(engine, asset, key="ter")).items] == [ter_second, ter_first]


async def test_each_change_carries_the_row_before_it(engine: AsyncEngine) -> None:
    """Plan 68, E6a: «Cosa è cambiato» says who wrote the value before and when («Tornato a 0,14 %: il 2 novembre Anna
    l'aveva corretto a mano…», «Ora sono i dati del 30 settembre (prima, del 31 agosto)»), so each change carries the
    voice's row before it — its source, author, day and source date — from the whole history, hidden rows included;
    the voice's first row has none."""
    asset, alice = await _asset(engine), await _user(engine)
    first = await _seed(engine, asset, "geography", {"USA": "1"}, "justetf", D("2026-09-01"), source_date=D("2026-08-31"))
    second = await _seed(engine, asset, "geography", {"USA": "0.6", "JPN": "0.4"}, "justetf", D("2026-10-01"), source_date=D("2026-09-30"))
    by_hand = await _seed(engine, asset, "ter", TER_019, "user", D("2026-11-02"), user_id=alice)
    back = await _seed(engine, asset, "ter", TER_022, "justetf", D("2026-11-08"))

    page = await _changes(engine, asset)
    before = {change.row.id: change.before for change in page.items}

    assert before[first] is None, "the voice's first row has no row before it"
    assert (before[second].id, before[second].source, before[second].source_date) == (first, "justetf", D("2026-08-31"))
    assert (before[back].id, before[back].source, before[back].user_id, before[back].read_on) == (by_hand, "user", alice, D("2026-11-02"))
    assert before[by_hand] is None, "the TER's first row"
