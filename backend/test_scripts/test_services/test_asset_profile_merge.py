"""What merging two assets and deleting an asset do to the asset profile (project 68, lot A5).

``AssetCRUDService.merge_assets(source_id, target_id, session, dry_run=...)`` folds the source into the target and
deletes the source. Developer round 36 decided what happens to the profile:

1. The target keeps its profile and its enrichers.
2. Every voice the source holds **now with a non-empty value** and the target has **no row of** moves to the target
   whole: all its rows, the NULL ones in its history included, by changing only ``asset_id`` (same row ids, same
   ``read_on``, same order, every other column untouched). ``current_rows`` and ``read_steps`` of the target show it.
3. A voice both hold → the target's rows only; the source's rows are gone.
4. A voice whose source «now» is empty (a NULL last row) → not moved, gone.
5. 🟡 A voice the target holds rows of but whose target «now» is empty (emptied on purpose) → stays the target's,
   still empty; the source's rows are gone (no mixing of histories).
6. Until lot D7 the column follows the profile: for each moved voice of ``description`` / ``geography`` / ``sector``
   the target's ``classification_params`` takes that part from the moved value (``short_description``,
   ``geographic_area: {"distribution": …}``, ``sector_area: {"distribution": …}``); its other parts stay. A shared voice
   (not moved) leaves the target's part as it was, whatever the source's column says.
7. The source's ``asset_enrichers`` row is deleted; the target's is unchanged, and a target without one stays without.
8. ``dry_run=True`` moves and deletes nothing: rows, column and enrichers as before.
9. No orphan: after the merge no ``asset_profile_updates`` / ``asset_enrichers`` row points at the source id.

And ``AssetCRUDService.delete_assets_bulk``: deleting an asset deletes its profile rows and its enrichers row; another
asset's rows stay.

Not pinned: the preview fields of the merge answer, and the target's column in case 5 (the contract says nothing).

Every scene seeds its history through the store's ``write_values`` (one call and one commit per day, fixed past dates),
so the rows look as the app writes them; a ``user`` row carries a real ``user_id`` and a source row a ``source_date``,
so «only ``asset_id`` changed» covers every column. Rows are snapshotted with plain SQL before the merge and compared
by id afterwards; values are compared as the store reads them (``normalize_value``), never by their JSON text. Every
scene that asserts an absence also holds a voice that must move, and asserts that move first: without it an absence
would pass because nothing ran. The service commits, so tests pass integer ids around and re-read through fresh
sessions.

Every database is a private SQLite file under ``tmp_path`` built with ``SQLModel.metadata.create_all``, opened as
production opens its own (aiosqlite, NullPool, the PRAGMA listener of ``backend.app.db.session``: foreign keys on),
disposed at teardown. No server, no lane database.

Red until A5: the merge moves no voice (the source's rows are cascaded away with it) and never touches the target's
column, so every merge test fails on an assertion about the moved voice. The delete tests are guards that already pass
thanks to ``ON DELETE CASCADE``.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Any, Optional

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetEnrichers, AssetType, User
from backend.app.schemas.common import DateRangeModel
from backend.app.services.assets.crud import AssetCRUDService
from backend.app.services.assets.profile import store
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.app.services.assets.profile.store import ProfileWrite
from backend.test_scripts.test_utils import print_section, print_success

pytestmark = pytest.mark.asyncio

USER = "user"
SOURCE = "justetf"
#: Fixed past days of the seeded histories; the range of every steps read.
DAY_1, DAY_2, DAY_3, DAY_4 = date(2026, 3, 2), date(2026, 4, 6), date(2026, 5, 4), date(2026, 6, 1)
THROUGH = date(2026, 6, 30)
#: The parts of classification_params and the voices they map to (plan 68, A4 and migration 006).
PART_OF_VOICE = {"description": "short_description", "geography": "geographic_area", "sector": "sector_area"}

SOURCE_DESCRIPTION = "Vanguard FTSE All-World, as read by the source"
TARGET_DESCRIPTION = "Vanguard FTSE All-World UCITS ETF (the asset kept)"
SOURCE_GEOGRAPHY = {"USA": "0.6", "JPN": "0.25", "GBR": "0.15"}
#: What the source's own column says: differs from its profile, so copying the column is not following the profile.
SOURCE_COLUMN_GEOGRAPHY = {"USA": "0.5", "JPN": "0.5"}
TARGET_GEOGRAPHY = {"USA": "0.7", "DEU": "0.3"}
SOURCE_SECTOR = {"Technology": "0.6", "Financials": "0.4"}
SOURCE_COLUMN_SECTOR = {"Energy": "1"}
TARGET_SECTOR = {"Health Care": "0.55", "Utilities": "0.45"}


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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'asset_profile_merge.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
            foreign_keys = (await connection.execute(text("PRAGMA foreign_keys"))).scalar()
        assert foreign_keys == 1, "barrier: the app's PRAGMA listener must hold on the private file (foreign keys on)"
        yield engine
    finally:
        await engine.dispose()


def _column(*, description: Optional[str] = None, geography: Optional[dict[str, str]] = None, sector: Optional[dict[str, str]] = None) -> Optional[str]:
    """``classification_params`` as the column stores it (only the parts given), or NULL when none is given."""
    params: dict[str, Any] = {}
    if description is not None:
        params["short_description"] = description
    if geography is not None:
        params["geographic_area"] = {"distribution": geography}
    if sector is not None:
        params["sector_area"] = {"distribution": sector}
    return json.dumps(params) if params else None


async def _user(engine: AsyncEngine, name: str = "alice") -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=name, email=f"{name}@example.com", hashed_password="$argon2id$seeded-account")
        session.add(user)
        await session.commit()
    return int(user.id)


async def _asset(engine: AsyncEngine, name: str, classification: Optional[str] = None) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=name, currency="EUR", asset_type=AssetType.ETF, classification_params=classification)
        session.add(asset)
        await session.commit()
    return int(asset.id)


async def _pair(engine: AsyncEngine, *, source_column: Optional[str] = None, target_column: Optional[str] = None) -> tuple[int, int]:
    """The duplicate (source) and the asset kept (target)."""
    return await _asset(engine, "World ETF (duplicate)", source_column), await _asset(engine, "World ETF", target_column)


async def _write(engine: AsyncEngine, asset_id: int, day: date, *writes: ProfileWrite) -> None:
    """One day of the history, through the store as the app writes it, committed."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        written = await store.write_values(session, asset_id, list(writes), today=day)
        await session.commit()
    assert len(written) == len(writes), f"barrier: every seeded value must make a row ({len(written)} of {len(writes)})"


def _by_source(key: str, value: Any, *, source_date: Optional[date] = None) -> ProfileWrite:
    return ProfileWrite(key=key, value=value, source=SOURCE, source_date=source_date)


def _by_hand(key: str, value: Any, user_id: int) -> ProfileWrite:
    return ProfileWrite(key=key, value=value, source=USER, user_id=user_id)


async def _rows(engine: AsyncEngine, *, asset_id: Optional[int] = None, ids: Optional[set[int]] = None) -> dict[int, dict[str, Any]]:
    """Profile rows by id, every column as stored (``value`` the raw JSON text), read with plain SQL."""
    query = "SELECT id, asset_id, key, value, source, user_id, read_on, source_date, created_at FROM asset_profile_updates"
    async with AsyncSession(engine) as session:
        rows = [dict(row._mapping) for row in await session.execute(text(query + " ORDER BY id"))]
    if asset_id is not None:
        rows = [row for row in rows if row["asset_id"] == asset_id]
    if ids is not None:
        rows = [row for row in rows if row["id"] in ids]
    return {int(row["id"]): row for row in rows}


def _of_voice(rows: dict[int, dict[str, Any]], key: str) -> dict[int, dict[str, Any]]:
    return {row_id: row for row_id, row in rows.items() if row["key"] == key}


async def _classification(engine: AsyncEngine, asset_id: int) -> dict[str, Any]:
    """The asset's ``classification_params`` parsed ({} for NULL)."""
    async with AsyncSession(engine) as session:
        value = (await session.execute(text("SELECT classification_params FROM assets WHERE id = :id"), {"id": asset_id})).scalar()
    return json.loads(value) if value else {}


def _part(classification: dict[str, Any], key: str) -> Any:
    """The column's part of a voice in the store's stored form (None when the column has none)."""
    part = classification.get(PART_OF_VOICE[key])
    if part is None:
        return None
    return normalize_value(key, part if key == "description" else part.get("distribution"))


async def _enrichers(engine: AsyncEngine) -> dict[int, tuple[str, str]]:
    """Every ``asset_enrichers`` row: asset id → (config text, state text)."""
    async with AsyncSession(engine) as session:
        rows = (await session.execute(text("SELECT asset_id, config, state FROM asset_enrichers ORDER BY asset_id"))).all()
    return {int(asset_id): (config, state) for asset_id, config, state in rows}


async def _bind_enrichers(engine: AsyncEngine, asset_id: int, config: dict[str, Any], state: dict[str, Any]) -> None:
    async with AsyncSession(engine) as session:
        session.add(AssetEnrichers(asset_id=asset_id, config=json.dumps(config), state=json.dumps(state)))
        await session.commit()


async def _merge(engine: AsyncEngine, source_id: int, target_id: int, *, dry_run: bool = False):
    async with AsyncSession(engine, expire_on_commit=False) as session:
        response = await AssetCRUDService.merge_assets(source_id, target_id, session, dry_run=dry_run)
    assert response.success, f"barrier: the merge itself must succeed: {response}"
    async with AsyncSession(engine) as session:
        source_left = (await session.execute(text("SELECT COUNT(*) FROM assets WHERE id = :id"), {"id": source_id})).scalar()
    assert source_left == (1 if dry_run else 0), f"barrier: the source must be {'kept by the dry run' if dry_run else 'deleted'} ({source_left} rows)"
    return response


async def _current(engine: AsyncEngine, asset_id: int, keys: Optional[list[str]] = None) -> dict[str, store.ProfileRow]:
    async with AsyncSession(engine) as session:
        return await store.current_rows(session, asset_id, keys)


async def _steps(engine: AsyncEngine, asset_id: int, key: str) -> list[store.ProfileStep]:
    async with AsyncSession(engine) as session:
        steps = await store.read_steps(session, [asset_id], DateRangeModel(start=DAY_1, end=THROUGH), [key])
    return steps.get(asset_id, {}).get(key, [])


def _fields(row: store.ProfileRow) -> dict[str, Any]:
    return dataclasses.asdict(row)


def _assert_moved_whole(before: dict[int, dict[str, Any]], after: dict[int, dict[str, Any]], target_id: int, key: str) -> None:
    """The voice's rows of the source, ``before``, are the same rows after the merge with only ``asset_id`` changed."""
    moved = _of_voice(before, key)
    assert moved, f"barrier: the source must hold rows of {key!r} before the merge"
    found = {row_id: row for row_id, row in after.items() if row_id in moved}
    assert set(found) == set(moved), f"{key!r}: every row of the source moves with its id; missing ids {sorted(set(moved) - set(found))}"
    for row_id, row in moved.items():
        expected = {**row, "asset_id": target_id}
        assert found[row_id] == expected, f"{key!r} row {row_id}: only asset_id changes\n before {row}\n after  {found[row_id]}"


# =============================================================================
# 1. A VOICE ONLY THE SOURCE HOLDS MOVES WHOLE
# =============================================================================


async def test_a_voice_only_the_source_holds_moves_whole_with_its_ids_and_dates(engine: AsyncEngine) -> None:
    """The source holds ``ter`` (by a source, a source date, then by hand, two rows on DAY_3) and ``geography`` (a value,
    emptied, a value again: non-empty now, its NULL row moves with it); the target holds neither. Every row of both
    voices is the target's afterwards, ids, ``read_on``, ``source``, ``user_id``, ``source_date``, ``created_at`` and
    value text unchanged, and no row is added; ``current_rows`` and ``read_steps`` of the target show them."""
    print_section("Merge: a voice only the source holds moves whole")
    author = await _user(engine)
    source_id, target_id = await _pair(engine)
    await _write(engine, source_id, DAY_1, _by_source("ter", "0.0022", source_date=date(2026, 2, 27)), _by_source("geography", SOURCE_GEOGRAPHY))
    await _write(engine, source_id, DAY_2, _by_hand("geography", None, author))
    await _write(engine, source_id, DAY_3, _by_hand("ter", "0.0020", author), _by_hand("geography", SOURCE_GEOGRAPHY, author))
    await _write(engine, source_id, DAY_3, _by_source("ter", "0.0019", source_date=date(2026, 4, 30)))
    await _write(engine, target_id, DAY_1, _by_hand("description", TARGET_DESCRIPTION, author))
    before = await _rows(engine, asset_id=source_id)
    target_before = await _rows(engine, asset_id=target_id)
    source_now = await _current(engine, source_id)

    await _merge(engine, source_id, target_id)

    after = await _rows(engine)
    for key in ("ter", "geography"):
        _assert_moved_whole(before, after, target_id, key)
    assert set(await _rows(engine, asset_id=target_id)) == set(target_before) | set(before), "the target holds its own rows and the moved ones, nothing else"

    now = await _current(engine, target_id, ["ter", "geography"])
    for key in ("ter", "geography"):
        assert key in now, f"current_rows of the target must show the moved {key!r}"
        assert _fields(now[key]) == {**_fields(source_now[key]), "asset_id": target_id}, f"{key!r}: now of the target is the source's now"
    ter_steps = await _steps(engine, target_id, "ter")
    assert [(step.date, step.through, step.value, step.source) for step in ter_steps] == [
        (DAY_1, DAY_3 - date.resolution, normalize_value("ter", "0.0022"), SOURCE),
        (DAY_3, THROUGH, normalize_value("ter", "0.0019"), SOURCE),
    ], f"read_steps of the target: the source's ter history, the last row of DAY_3 holding it: {ter_steps}"
    geography_steps = await _steps(engine, target_id, "geography")
    assert [(step.date, step.value) for step in geography_steps] == [
        (DAY_1, normalize_value("geography", SOURCE_GEOGRAPHY)),
        (DAY_2, None),
        (DAY_3, normalize_value("geography", SOURCE_GEOGRAPHY)),
    ], f"read_steps of the target: the geography history with its empty stretch: {geography_steps}"
    print_success("ter and geography moved whole: same ids, same dates, visible on the target")


# =============================================================================
# 2. WHAT DOES NOT MOVE
# =============================================================================


async def test_a_voice_both_hold_keeps_the_targets_rows_only(engine: AsyncEngine) -> None:
    """Both hold ``description`` (the source two rows, the target one): the target's row only, the source's rows gone
    from the whole table. Barrier in the same scene: ``ter``, only the source's, moves."""
    author = await _user(engine)
    source_id, target_id = await _pair(engine)
    await _write(engine, source_id, DAY_1, _by_source("description", SOURCE_DESCRIPTION), _by_source("ter", "0.0022"))
    await _write(engine, source_id, DAY_3, _by_hand("description", SOURCE_DESCRIPTION + " (edited)", author))
    await _write(engine, target_id, DAY_2, _by_hand("description", TARGET_DESCRIPTION, author))
    before = await _rows(engine, asset_id=source_id)
    target_description = _of_voice(await _rows(engine, asset_id=target_id), "description")

    await _merge(engine, source_id, target_id)

    after = await _rows(engine)
    _assert_moved_whole(before, after, target_id, "ter")
    assert _of_voice(await _rows(engine, asset_id=target_id), "description") == target_description, "description: the target's rows, unchanged, and only those"
    gone = set(_of_voice(before, "description"))
    assert not gone & set(after), f"description: the source's rows are gone, not moved: {sorted(gone & set(after))}"
    assert (await _current(engine, target_id, ["description"]))["description"].value == normalize_value("description", TARGET_DESCRIPTION), "description: now is the target's"
    print_success("description: the target's history only")


async def test_a_voice_the_source_left_empty_is_not_moved(engine: AsyncEngine) -> None:
    """The source's ``fund_provider`` is empty now (a value, then a NULL row): not moved, gone. Barrier in the same
    scene: ``ter``, non-empty now, moves."""
    author = await _user(engine)
    source_id, target_id = await _pair(engine)
    await _write(engine, source_id, DAY_1, _by_source("fund_provider", "Vanguard"), _by_source("ter", "0.0022"))
    await _write(engine, source_id, DAY_2, _by_hand("fund_provider", None, author))
    before = await _rows(engine, asset_id=source_id)
    assert (await _current(engine, source_id, ["fund_provider"]))["fund_provider"].value is None, "barrier: fund_provider is empty now on the source"

    await _merge(engine, source_id, target_id)

    after = await _rows(engine)
    _assert_moved_whole(before, after, target_id, "ter")
    assert _of_voice(await _rows(engine, asset_id=target_id), "fund_provider") == {}, "fund_provider: empty now on the source, not moved"
    gone = set(_of_voice(before, "fund_provider"))
    assert not gone & set(after), f"fund_provider: the source's rows are gone: {sorted(gone & set(after))}"
    print_success("fund_provider: empty on the source, gone")


async def test_a_voice_the_target_emptied_on_purpose_stays_empty_and_the_sources_rows_go(engine: AsyncEngine) -> None:
    """🟡 The target held ``sector`` and emptied it (a NULL row now); the source holds a sector now. The target's rows
    stay, its «now» still empty, and the source's rows are gone: two histories are never mixed. Barrier in the same
    scene: ``ter``, only the source's, moves."""
    author = await _user(engine)
    source_id, target_id = await _pair(engine)
    await _write(engine, source_id, DAY_1, _by_source("sector", SOURCE_SECTOR), _by_source("ter", "0.0022"))
    await _write(engine, target_id, DAY_1, _by_source("sector", TARGET_SECTOR))
    await _write(engine, target_id, DAY_2, _by_hand("sector", None, author))
    before = await _rows(engine, asset_id=source_id)
    target_sector = _of_voice(await _rows(engine, asset_id=target_id), "sector")

    await _merge(engine, source_id, target_id)

    after = await _rows(engine)
    _assert_moved_whole(before, after, target_id, "ter")
    assert _of_voice(await _rows(engine, asset_id=target_id), "sector") == target_sector, "sector: the target's rows only, unchanged"
    assert (await _current(engine, target_id, ["sector"]))["sector"].value is None, "sector: the target's now stays empty"
    gone = set(_of_voice(before, "sector"))
    assert not gone & set(after), f"sector: the source's rows are gone: {sorted(gone & set(after))}"
    print_success("sector: emptied on the target, stays empty")


# =============================================================================
# 3. THE COLUMN FOLLOWS THE MOVED VOICES (UNTIL D7)
# =============================================================================


async def test_a_moved_description_fills_a_target_column_that_was_null(engine: AsyncEngine) -> None:
    """The target has no classification at all; the source's description moves: the target's column gets
    ``short_description`` from the moved value (not from the source's column, which says something else) and nothing
    else; a moved ``ter`` touches no part of it."""
    source_id, target_id = await _pair(engine, source_column=_column(description="the source's column, stale"))
    await _write(engine, source_id, DAY_1, _by_source("description", SOURCE_DESCRIPTION), _by_source("ter", "0.0022"))
    before = await _rows(engine, asset_id=source_id)

    await _merge(engine, source_id, target_id)

    _assert_moved_whole(before, await _rows(engine), target_id, "description")
    column = await _classification(engine, target_id)
    assert _part(column, "description") == normalize_value("description", SOURCE_DESCRIPTION), f"short_description from the moved value: {column}"
    assert _part(column, "geography") is None and _part(column, "sector") is None, f"no other part appears: {column}"
    print_success("description moved into a NULL column")


async def test_a_moved_geography_joins_the_targets_other_parts(engine: AsyncEngine) -> None:
    """The target's column and profile hold a description and a sector; the source's geography moves (its own column
    holds another one, and its first row another one still): the column gains ``geographic_area`` from the moved voice's
    value now; its description and sector stay."""
    author = await _user(engine)
    source_id, target_id = await _pair(
        engine,
        source_column=_column(geography=SOURCE_COLUMN_GEOGRAPHY),
        target_column=_column(description=TARGET_DESCRIPTION, sector=TARGET_SECTOR),
    )
    await _write(engine, source_id, DAY_1, _by_source("geography", TARGET_GEOGRAPHY))
    await _write(engine, source_id, DAY_3, _by_source("geography", SOURCE_GEOGRAPHY))
    await _write(engine, target_id, DAY_1, _by_hand("description", TARGET_DESCRIPTION, author), _by_hand("sector", TARGET_SECTOR, author))
    before = await _rows(engine, asset_id=source_id)

    await _merge(engine, source_id, target_id)

    _assert_moved_whole(before, await _rows(engine), target_id, "geography")
    column = await _classification(engine, target_id)
    assert _part(column, "geography") == normalize_value("geography", SOURCE_GEOGRAPHY), f"geographic_area from the moved voice's value now (not its first row, not the source's column): {column}"
    assert _part(column, "description") == normalize_value("description", TARGET_DESCRIPTION), f"the target's description stays: {column}"
    assert _part(column, "sector") == normalize_value("sector", TARGET_SECTOR), f"the target's sector stays: {column}"
    print_success("geography joined the target's description and sector")


async def test_a_moved_sector_enters_the_column_and_a_shared_voice_leaves_the_targets_part(engine: AsyncEngine) -> None:
    """Both hold ``geography`` (not moved: the target's part stays, though the source's column and profile differ); only
    the source holds ``sector`` (moved: ``sector_area`` from the moved value, not from the source's column)."""
    author = await _user(engine)
    source_id, target_id = await _pair(
        engine,
        source_column=_column(geography=SOURCE_COLUMN_GEOGRAPHY, sector=SOURCE_COLUMN_SECTOR),
        target_column=_column(geography=TARGET_GEOGRAPHY),
    )
    await _write(engine, source_id, DAY_1, _by_source("geography", SOURCE_GEOGRAPHY), _by_source("sector", SOURCE_SECTOR))
    await _write(engine, target_id, DAY_2, _by_hand("geography", TARGET_GEOGRAPHY, author))
    before = await _rows(engine, asset_id=source_id)

    await _merge(engine, source_id, target_id)

    _assert_moved_whole(before, await _rows(engine), target_id, "sector")
    column = await _classification(engine, target_id)
    assert _part(column, "sector") == normalize_value("sector", SOURCE_SECTOR), f"sector_area from the moved value: {column}"
    assert _part(column, "geography") == normalize_value("geography", TARGET_GEOGRAPHY), f"geography is shared, not moved: the target's part stays: {column}"
    assert _part(column, "description") is None, f"no description appears: {column}"
    print_success("sector moved into the column, the shared geography left alone")


# =============================================================================
# 4. ENRICHERS, DRY RUN, ORPHANS
# =============================================================================


@pytest.mark.parametrize("target_has_enrichers", [True, False], ids=["target-bound", "target-unbound"])
async def test_the_sources_enrichers_row_goes_and_the_targets_stays_as_it_was(engine: AsyncEngine, target_has_enrichers: bool) -> None:
    """The source's ``asset_enrichers`` row is deleted; the target's is unchanged (config and state text), and a target
    without one stays without (guard: ON DELETE CASCADE does this today). Barrier in the same scene: ``ter`` moves."""
    source_id, target_id = await _pair(engine)
    await _write(engine, source_id, DAY_1, _by_source("ter", "0.0022"))
    await _bind_enrichers(engine, source_id, {"justetf": {"identifier": "IE00BK5BQT80"}}, {"justetf": {"read_at": "2026-05-04", "outcome": "ok"}})
    if target_has_enrichers:
        await _bind_enrichers(engine, target_id, {"yfinance": {"identifier": "VWCE.DE"}, "justetf": {"identifier": "IE00BK5BQT80"}}, {})
    enrichers_before = await _enrichers(engine)
    before = await _rows(engine, asset_id=source_id)

    await _merge(engine, source_id, target_id)

    _assert_moved_whole(before, await _rows(engine), target_id, "ter")
    expected = {target_id: enrichers_before[target_id]} if target_has_enrichers else {}
    assert await _enrichers(engine) == expected, "the source's enrichers row is gone, the target's as it was (or still none)"
    print_success("enrichers: the target's kept, the source's gone")


async def test_a_dry_run_moves_nothing_and_the_real_merge_then_moves(engine: AsyncEngine) -> None:
    """``dry_run=True``: every profile row, both columns and both enrichers rows as before. The same merge for real then
    moves the source-only voices (so the dry run's «nothing» is not a merge that does nothing)."""
    author = await _user(engine)
    source_id, target_id = await _pair(engine, source_column=_column(sector=SOURCE_COLUMN_SECTOR), target_column=_column(description=TARGET_DESCRIPTION))
    await _write(engine, source_id, DAY_1, _by_source("sector", SOURCE_SECTOR), _by_source("ter", "0.0022"), _by_source("description", SOURCE_DESCRIPTION))
    await _write(engine, target_id, DAY_1, _by_hand("description", TARGET_DESCRIPTION, author))
    await _bind_enrichers(engine, source_id, {"justetf": {"identifier": "IE00BK5BQT80"}}, {})
    await _bind_enrichers(engine, target_id, {"yfinance": {"identifier": "VWCE.DE"}}, {})
    rows_before = await _rows(engine)
    columns_before = (await _classification(engine, source_id), await _classification(engine, target_id))
    enrichers_before = await _enrichers(engine)

    await _merge(engine, source_id, target_id, dry_run=True)

    assert await _rows(engine) == rows_before, "dry run: every profile row as before"
    assert (await _classification(engine, source_id), await _classification(engine, target_id)) == columns_before, "dry run: both columns as before"
    assert await _enrichers(engine) == enrichers_before, "dry run: both enrichers rows as before"

    await _merge(engine, source_id, target_id)

    source_rows = {row_id: row for row_id, row in rows_before.items() if row["asset_id"] == source_id}
    after = await _rows(engine)
    for key in ("sector", "ter"):
        _assert_moved_whole(source_rows, after, target_id, key)
    assert _part(await _classification(engine, target_id), "sector") == normalize_value("sector", SOURCE_SECTOR), "the real merge writes the moved sector into the column"
    print_success("dry run: nothing; real run: moved")


async def test_no_profile_or_enrichers_row_points_at_the_source_after_the_merge(engine: AsyncEngine) -> None:
    """After the merge no ``asset_profile_updates`` or ``asset_enrichers`` row points at the source id, whatever the
    voice (moved, shared, empty now). Barrier first: the source had rows of each kind, and ``ter`` moved."""
    author = await _user(engine)
    source_id, target_id = await _pair(engine)
    await _write(engine, source_id, DAY_1, _by_source("ter", "0.0022"), _by_source("description", SOURCE_DESCRIPTION), _by_source("fund_provider", "Vanguard"))
    await _write(engine, source_id, DAY_2, _by_hand("fund_provider", None, author))
    await _write(engine, target_id, DAY_1, _by_hand("description", TARGET_DESCRIPTION, author))
    await _bind_enrichers(engine, source_id, {"justetf": {"identifier": "IE00BK5BQT80"}}, {})
    before = await _rows(engine, asset_id=source_id)
    assert {row["key"] for row in before.values()} == {"ter", "description", "fund_provider"}, "barrier: the source holds the three kinds of voice"
    assert source_id in await _enrichers(engine), "barrier: the source has an enrichers row"

    await _merge(engine, source_id, target_id)

    _assert_moved_whole(before, await _rows(engine), target_id, "ter")
    assert await _rows(engine, asset_id=source_id) == {}, "no profile row points at the source"
    assert source_id not in await _enrichers(engine), "no enrichers row points at the source"
    print_success("no orphan row")


# =============================================================================
# 5. DELETE (GUARD: ON DELETE CASCADE ALREADY DOES IT)
# =============================================================================


async def test_deleting_an_asset_deletes_its_profile_and_enrichers_and_leaves_anothers(engine: AsyncEngine) -> None:
    """``delete_assets_bulk([doomed])``: the doomed asset's profile rows and enrichers row are gone; the other asset's
    are as before. A guard: the foreign keys' ON DELETE CASCADE already does it."""
    print_section("Delete: the profile goes with its asset")
    author = await _user(engine)
    doomed, kept = await _pair(engine)
    await _write(engine, doomed, DAY_1, _by_source("ter", "0.0022"), _by_hand("description", SOURCE_DESCRIPTION, author))
    await _write(engine, kept, DAY_1, _by_source("ter", "0.0007"), _by_hand("sector", TARGET_SECTOR, author))
    await _bind_enrichers(engine, doomed, {"justetf": {"identifier": "IE00BK5BQT80"}}, {})
    await _bind_enrichers(engine, kept, {"yfinance": {"identifier": "VWCE.DE"}}, {"yfinance": {"outcome": "ok"}})
    doomed_rows = await _rows(engine, asset_id=doomed)
    kept_rows = await _rows(engine, asset_id=kept)
    kept_enrichers = (await _enrichers(engine))[kept]
    assert doomed_rows and kept_rows, "barrier: both assets hold profile rows"

    async with AsyncSession(engine, expire_on_commit=False) as session:
        response = await AssetCRUDService.delete_assets_bulk([doomed], session)
    assert [result.success for result in response.results] == [True], f"barrier: the delete succeeds: {response.results}"

    after = await _rows(engine)
    assert not set(doomed_rows) & set(after), "the deleted asset's profile rows are gone"
    assert await _rows(engine, asset_id=kept) == kept_rows, "the other asset's profile rows stay as they were"
    assert await _enrichers(engine) == {kept: kept_enrichers}, "the deleted asset's enrichers row is gone, the other's stays"
    print_success("delete: profile and enrichers go with the asset")
