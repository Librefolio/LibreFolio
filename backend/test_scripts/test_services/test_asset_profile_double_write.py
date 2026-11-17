"""The double write of ``classification_params`` into the asset profile (project 68, lot A4), until lot D7.

``classification_params`` sent to ``POST /assets`` or ``PATCH /assets`` is also written into the profile, in the same
transaction, through the profile store (``services/assets/profile/store.py``): ``source='user'``, ``user_id`` the
authenticated user, ``read_on`` the store's rule (``store.profile_today``, never before the voice's «now»). The services
take the author as a keyword: ``AssetCRUDService.create_assets_bulk(assets, session, user_id=None)`` and
``AssetCRUDService.patch_assets_bulk(patches, session, commit=True, user_id=None)``; the routes pass the current user's
id (the API half: ``test_api/test_assets_patch_fields.py``). The parts become voices as in migration 006:
``short_description`` → ``description``, ``geographic_area.distribution`` → ``geography``, ``sector_area.distribution`` →
``sector``.

Pinned here:

1. POST with a full classification → three ``user`` rows by that author, each value the stored form of the part sent,
   ``read_on`` today in ``scheduler_timezone``; an asset of the same batch without classification → no row.
2. PATCH of ``sector_area`` alone → one new ``sector`` row; description and geography get none, even when the profile
   holds another geography than the column.
3. ``sector_area: null`` → a NULL ``sector`` row. ``classification_params: null`` → NULL rows for the voices that hold a
   value in the profile; a voice with nothing stored gets no row.
4. The value the voice holds now (another spelling of it) → no row: the store's «different from now».
5. A new row is never dated before the voice's «now» (``max(today, now)``).
6. ``commit=False`` (``POST /assets/validate``) and a batch rolled back (another item fails while applying:
   ``patchFailed``) → no profile row.
7. A PATCH that does not touch ``classification_params`` → no profile row.
8. A ``short_description`` of only spaces (``FAClassificationParams`` takes it, the catalogue refuses it) is an empty
   description: POST creates the asset with its other voices and no ``description`` row; PATCH is saved and writes a
   NULL ``description`` row over a description; its dry run answers success and writes nothing. Never ``patchFailed``.

Not pinned: what a call with ``user_id=None`` writes (the contract does not say), and a POST batch whose commit fails
(no way to provoke it on a private file without patching the session).

Every database is a private SQLite file under ``tmp_path`` built with ``SQLModel.metadata.create_all``, opened as
production opens its own (aiosqlite, NullPool, the PRAGMA listener of ``backend.app.db.session``), disposed at teardown.
Scenes are seeded through the models; profile rows are read back with plain SQL, and a value is compared as the store
reads it (``normalize_value(key, json.loads(value))``), never by its JSON text. Every test that asserts an absence
proves first, in the same test, that the double write runs (a row it expects is there). No server, no lane database.

Red until A4: the services take no ``user_id``: every test fails with ``TypeError`` at its first call, never at
collection.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetProfileUpdate, AssetType, GlobalSetting, User
from backend.app.schemas.assets.assets import FAAssetCreateItem, FAAssetPatchCode, FAAssetPatchItem, FABulkAssetCreateResponse, FABulkAssetPatchResponse
from backend.app.schemas.assets.metadata import FAClassificationParams
from backend.app.services.assets.crud import AssetCRUDService
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.test_scripts.test_utils import print_section, print_success

pytestmark = pytest.mark.asyncio

USER = "user"
#: A realistic classification as the edit modal sends it.
DESCRIPTION = "iShares Core MSCI World: large and mid caps of 23 developed markets."
GEOGRAPHY = {"USA": "0.7", "JPN": "0.2", "GBR": "0.1"}
SECTOR = {"Technology": "0.6", "Financials": "0.4"}
#: Another geography, as an enricher read it: the profile differs from the column for that voice.
GEOGRAPHY_READ_ELSEWHERE = {"USA": "0.65", "JPN": "0.25", "GBR": "0.1"}
#: Two other sectors the user picks.
SECTOR_EDITED = {"Energy": "0.55", "Utilities": "0.45"}
SECTOR_EDITED_AGAIN = {"Health Care": "1"}
#: The voices of the profile and the part of classification_params each comes from.
PART_OF_VOICE = {"description": "short_description", "geography": "geographic_area", "sector": "sector_area"}
#: Two zones 26 hours apart: at any hour at least one has another date than UTC.
FAR_EAST, FAR_WEST = "Pacific/Kiritimati", "Etc/GMT+12"


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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'asset_profile_double_write.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
            foreign_keys = (await connection.execute(text("PRAGMA foreign_keys"))).scalar()
        assert foreign_keys == 1, "barrier: the app's PRAGMA listener must hold on the private file (foreign keys on)"
        yield engine
    finally:
        await engine.dispose()


def _classification(*, description: Optional[str] = None, geography: Optional[dict[str, str]] = None, sector: Optional[dict[str, str]] = None) -> FAClassificationParams:
    """A classification with only the parts given set (``model_fields_set``): a PATCH sends those and nothing else."""
    fields: dict[str, Any] = {}
    if description is not None:
        fields["short_description"] = description
    if geography is not None:
        fields["geographic_area"] = {"distribution": geography}
    if sector is not None:
        fields["sector_area"] = {"distribution": sector}
    return FAClassificationParams(**fields)


FULL_CLASSIFICATION = _classification(description=DESCRIPTION, geography=GEOGRAPHY, sector=SECTOR)


async def _user(engine: AsyncEngine, name: str = "alice") -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=name, email=f"{name}@example.com", hashed_password="$argon2id$seeded-account")
        session.add(user)
        await session.commit()
    return int(user.id)


async def _asset(engine: AsyncEngine, name: str, classification: Optional[str] = None) -> int:
    """An asset as 1.3 stored it: ``classification_params`` the given text (``model_dump_json``), or NULL."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=name, currency="EUR", asset_type=AssetType.ETF, classification_params=classification)
        session.add(asset)
        await session.commit()
    return int(asset.id)


async def _seed(engine: AsyncEngine, asset_id: int, key: str, value: Any, source: str, read_on: date, *, user_id: Optional[int] = None) -> int:
    """One profile row as the model writes it, without the store: ``value`` in its stored form (None: NULL)."""
    stored = None if value is None else json.dumps(normalize_value(key, value))
    async with AsyncSession(engine, expire_on_commit=False) as session:
        row = AssetProfileUpdate(asset_id=asset_id, key=key, value=stored, source=source, user_id=user_id, read_on=read_on)
        session.add(row)
        await session.commit()
    return int(row.id)


async def _save_zone(engine: AsyncEngine, zone: str) -> None:
    """``scheduler_timezone`` as an administrator saves it."""
    admin = await _user(engine, "admin")
    async with AsyncSession(engine) as session:
        session.add(GlobalSetting(key="scheduler_timezone", value=zone, value_type="str", updated_by_user_id=admin))
        await session.commit()


async def _rows(engine: AsyncEngine, asset_id: int) -> list[dict[str, Any]]:
    """The asset's profile rows by id, read with plain SQL; ``read_on`` as a date, ``stored`` the value as the store reads it."""
    query = "SELECT id, key, value, source, user_id, read_on, source_date FROM asset_profile_updates WHERE asset_id = :asset ORDER BY id"
    async with AsyncSession(engine) as session:
        rows = [dict(row._mapping) for row in await session.execute(text(query), {"asset": asset_id})]
    for row in rows:
        row["read_on"] = date.fromisoformat(str(row["read_on"]))
        row["stored"] = None if row["value"] is None else normalize_value(row["key"], json.loads(row["value"]))
    return rows


def _new(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    known = {row["id"] for row in before}
    return [row for row in after if row["id"] not in known]


def _summary(rows: list[dict[str, Any]]) -> list[tuple[str, Any, str, Optional[int]]]:
    """Rows as (voice, value as the store reads it, source, author), by voice."""
    return sorted(((row["key"], row["stored"], row["source"], row["user_id"]) for row in rows), key=lambda item: item[0])


async def _create(engine: AsyncEngine, items: list[FAAssetCreateItem], *, user_id: int) -> FABulkAssetCreateResponse:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await AssetCRUDService.create_assets_bulk(items, session, user_id=user_id)


async def _patch(engine: AsyncEngine, patches: list[FAAssetPatchItem], *, user_id: int, commit: bool = True) -> FABulkAssetPatchResponse:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await AssetCRUDService.patch_assets_bulk(patches, session, commit=commit, user_id=user_id)


def _today_in(zone: str) -> date:
    return datetime.now(ZoneInfo(zone)).date()


def _utc_today() -> date:
    return datetime.now(UTC).date()


def _zone_off_utc() -> str:
    """A zone whose date differs from UTC's right now: a ``read_on`` in UTC cannot pass for it."""
    return FAR_EAST if _today_in(FAR_EAST) != _utc_today() else FAR_WEST


async def _full_asset(engine: AsyncEngine, name: str) -> int:
    """An asset whose column holds the full classification, as ``create_assets_bulk`` stores it."""
    return await _asset(engine, name, FULL_CLASSIFICATION.model_dump_json(exclude_none=True))


# =============================================================================
# 1. POST /assets
# =============================================================================


async def test_post_with_a_classification_writes_three_user_rows_by_the_author_and_none_without(engine: AsyncEngine) -> None:
    """One batch, two assets: the one with description, geography and sector gets three ``user`` rows by the author,
    each value the stored form of the part sent, ``source_date`` NULL, ``read_on`` today in ``scheduler_timezone``; the
    one without classification gets none."""
    print_section("POST /assets: the classification also enters the profile")
    zone = _zone_off_utc()
    await _save_zone(engine, zone)
    author = await _user(engine)
    first = _today_in(zone)

    response = await _create(
        engine,
        [
            FAAssetCreateItem(display_name="Classified ETF", currency="EUR", asset_type=AssetType.ETF, classification_params=FULL_CLASSIFICATION),
            FAAssetCreateItem(display_name="Plain ETF", currency="EUR", asset_type=AssetType.ETF),
        ],
        user_id=author,
    )
    days = {first, _today_in(zone)}

    assert [result.success for result in response.results] == [True, True], f"both assets must be created: {response.results}"
    classified, plain = (result.asset_id for result in response.results)
    rows = await _rows(engine, classified)
    expected = [
        ("description", normalize_value("description", DESCRIPTION), USER, author),
        ("geography", normalize_value("geography", GEOGRAPHY), USER, author),
        ("sector", normalize_value("sector", SECTOR), USER, author),
    ]
    assert _summary(rows) == expected, f"three user rows by the author, the parts sent: {_summary(rows)}"
    assert all(row["source_date"] is None for row in rows), f"a value written by hand has no source date: {rows}"
    assert {row["read_on"] for row in rows} <= days, f"read_on is today in {zone} {sorted(days)}, not UTC's {_utc_today()}: {[row['read_on'] for row in rows]}"
    assert await _rows(engine, plain) == [], "an asset created without classification gets no profile row"
    print_success("three user rows; none for the plain asset")


# =============================================================================
# 2. PATCH /assets: what the patch touches
# =============================================================================


async def test_patch_of_the_sector_alone_writes_one_sector_row_and_leaves_the_other_voices(engine: AsyncEngine) -> None:
    """The column holds the full classification, the profile a description and a sector equal to it and a geography an
    enricher read differently. A PATCH of ``sector_area`` alone: one new ``sector`` row by the author; no row for
    description or geography — the merged column is not the profile's business."""
    author = await _user(engine)
    asset = await _full_asset(engine, "Sector-only ETF")
    day = _utc_today() - timedelta(days=3)
    await _seed(engine, asset, "description", DESCRIPTION, "legacy", day)
    await _seed(engine, asset, "geography", GEOGRAPHY_READ_ELSEWHERE, "justetf", day)
    await _seed(engine, asset, "sector", SECTOR, "legacy", day)
    before = await _rows(engine, asset)

    response = await _patch(engine, [FAAssetPatchItem(asset_id=asset, classification_params=_classification(sector=SECTOR_EDITED))], user_id=author)

    assert response.committed, f"the patch must be saved: {response.issues}"
    new = _new(before, await _rows(engine, asset))
    assert _summary(new) == [("sector", normalize_value("sector", SECTOR_EDITED), USER, author)], f"one new sector row by the author, nothing else: {_summary(new)}"


async def test_patch_of_a_null_sector_writes_a_null_sector_row(engine: AsyncEngine) -> None:
    """``{"sector_area": null}`` removes the sector from the column, and empties it on purpose in the profile: one NULL
    ``sector`` row by the author."""
    author = await _user(engine)
    asset = await _full_asset(engine, "Null-sector ETF")
    await _seed(engine, asset, "sector", SECTOR, "legacy", _utc_today() - timedelta(days=3))
    before = await _rows(engine, asset)

    response = await _patch(engine, [FAAssetPatchItem(asset_id=asset, classification_params=FAClassificationParams(sector_area=None))], user_id=author)

    assert response.committed, f"the patch must be saved: {response.issues}"
    new = _new(before, await _rows(engine, asset))
    assert [(row["key"], row["value"], row["source"], row["user_id"]) for row in new] == [("sector", None, USER, author)], f"one NULL sector row by the author: {new}"


async def test_patch_of_a_null_classification_writes_null_rows_for_the_voices_with_a_value(engine: AsyncEngine) -> None:
    """``classification_params: null`` clears the column; in the profile it empties the voices that hold a value — here
    description and geography — and writes nothing for the sector, which holds nothing (the store's rule)."""
    author = await _user(engine)
    asset = await _full_asset(engine, "Cleared ETF")
    day = _utc_today() - timedelta(days=3)
    await _seed(engine, asset, "description", DESCRIPTION, "legacy", day)
    await _seed(engine, asset, "geography", GEOGRAPHY, "legacy", day)
    before = await _rows(engine, asset)

    response = await _patch(engine, [FAAssetPatchItem(asset_id=asset, classification_params=None)], user_id=author)

    assert response.committed, f"the patch must be saved: {response.issues}"
    new = _new(before, await _rows(engine, asset))
    found = sorted((row["key"], row["value"], row["source"], row["user_id"]) for row in new)
    assert found == [("description", None, USER, author), ("geography", None, USER, author)], f"NULL rows for the two voices with a value, none for the sector: {found}"


async def test_patch_with_the_value_the_voice_holds_writes_no_row(engine: AsyncEngine) -> None:
    """A first PATCH of the sector writes one row (the double write runs); the same sector again — spelled another way —
    writes nothing: «different from now», whoever wrote now."""
    author = await _user(engine)
    asset = await _full_asset(engine, "Same-value ETF")
    await _seed(engine, asset, "sector", SECTOR, "legacy", _utc_today() - timedelta(days=3))
    before = await _rows(engine, asset)

    first = await _patch(engine, [FAAssetPatchItem(asset_id=asset, classification_params=_classification(sector=SECTOR_EDITED))], user_id=author)
    after_first = await _rows(engine, asset)
    assert first.committed and len(_new(before, after_first)) == 1, f"barrier: the first patch writes one sector row: {_new(before, after_first)}"

    again = await _patch(engine, [FAAssetPatchItem(asset_id=asset, classification_params=_classification(sector={"Utilities": "0.450", "Energy": "0.550"}))], user_id=author)

    assert again.committed, f"the patch must be saved: {again.issues}"
    assert _new(after_first, await _rows(engine, asset)) == [], "the value the sector holds now, spelled another way, writes no row"


async def test_a_patched_row_is_never_dated_before_the_voice_now(engine: AsyncEngine) -> None:
    """The sector's «now» is dated after today (a reading of a later day): the new row takes that day, not today
    (``max(today, now)``), so it is the last one."""
    author = await _user(engine)
    asset = await _full_asset(engine, "Future-dated ETF")
    later = _utc_today() + timedelta(days=30)
    await _seed(engine, asset, "sector", SECTOR, "justetf", later)
    before = await _rows(engine, asset)

    response = await _patch(engine, [FAAssetPatchItem(asset_id=asset, classification_params=_classification(sector=SECTOR_EDITED))], user_id=author)

    assert response.committed, f"the patch must be saved: {response.issues}"
    new = _new(before, await _rows(engine, asset))
    assert [(row["key"], row["read_on"]) for row in new] == [("sector", later)], f"the new sector row is dated {later}, the day of now: {new}"


# =============================================================================
# 3. NOTHING SAVED, NOTHING WRITTEN
# =============================================================================


async def test_the_dry_run_writes_no_profile_row(engine: AsyncEngine) -> None:
    """``commit=False`` (``POST /assets/validate``) answers what would be saved and rolls back: the profile gets no row.
    Barrier: a saved PATCH of the same asset writes one."""
    author = await _user(engine)
    asset = await _full_asset(engine, "Dry-run ETF")
    before = await _rows(engine, asset)
    saved = await _patch(engine, [FAAssetPatchItem(asset_id=asset, classification_params=_classification(sector=SECTOR_EDITED))], user_id=author)
    after_saved = await _rows(engine, asset)
    assert saved.committed and len(_new(before, after_saved)) == 1, f"barrier: a saved patch writes one sector row: {_new(before, after_saved)}"

    dry = await _patch(engine, [FAAssetPatchItem(asset_id=asset, classification_params=_classification(sector=SECTOR_EDITED_AGAIN))], user_id=author, commit=False)

    assert dry.committed is False and dry.success_count == 1, f"the dry run answers success without saving: {dry}"
    assert _new(after_saved, await _rows(engine, asset)) == [], "the dry run must write no profile row"


async def test_a_batch_rolled_back_writes_no_profile_row(engine: AsyncEngine) -> None:
    """Two items: the first patches a sound asset's sector, the second an asset whose stored geography no longer sums to 1,
    so merging it fails while applying (``patchFailed``) and the whole batch is rolled back: neither asset gets a
    profile row. Barrier: the first item alone writes one."""
    author = await _user(engine)
    sound = await _full_asset(engine, "Sound ETF")
    broken = await _asset(engine, "Broken-geography ETF", '{"geographic_area":{"distribution":{"USA":"0.5"}}}')
    before = await _rows(engine, sound)
    alone = await _patch(engine, [FAAssetPatchItem(asset_id=sound, classification_params=_classification(sector=SECTOR_EDITED))], user_id=author)
    after_alone = await _rows(engine, sound)
    assert alone.committed and len(_new(before, after_alone)) == 1, f"barrier: the sound item alone writes one sector row: {_new(before, after_alone)}"

    batch = await _patch(
        engine,
        [
            FAAssetPatchItem(asset_id=sound, classification_params=_classification(sector=SECTOR_EDITED_AGAIN)),
            FAAssetPatchItem(asset_id=broken, classification_params=_classification(sector=SECTOR_EDITED_AGAIN)),
        ],
        user_id=author,
    )

    assert batch.committed is False and [(issue.asset_id, issue.code) for issue in batch.issues] == [(broken, FAAssetPatchCode.PATCH_FAILED)], f"the batch must be rolled back on the broken asset: {batch.issues}"
    assert _new(after_alone, await _rows(engine, sound)) == [], "a rolled-back batch writes no profile row for the sound asset"
    assert await _rows(engine, broken) == [], "nor for the broken one"


async def test_a_patch_that_does_not_touch_the_classification_writes_no_row(engine: AsyncEngine) -> None:
    """One batch: a rename of one asset, a sector of another. The renamed asset gets no profile row; the other one
    does (the double write runs in that very call)."""
    author = await _user(engine)
    renamed = await _full_asset(engine, "Renamed ETF")
    classified = await _full_asset(engine, "Reclassified ETF")

    response = await _patch(
        engine,
        [
            FAAssetPatchItem(asset_id=renamed, display_name="Renamed ETF (2026)"),
            FAAssetPatchItem(asset_id=classified, classification_params=_classification(sector=SECTOR_EDITED)),
        ],
        user_id=author,
    )

    assert response.committed, f"the batch must be saved: {response.issues}"
    assert _summary(await _rows(engine, classified)) == [("sector", normalize_value("sector", SECTOR_EDITED), USER, author)], "barrier: the reclassified asset gets its sector row"
    assert await _rows(engine, renamed) == [], "a patch that does not touch classification_params writes no profile row"


# =============================================================================
# 4. A DESCRIPTION OF ONLY SPACES IS AN EMPTY DESCRIPTION
# =============================================================================

#: What a user leaves in the description field after deleting its text: ``FAClassificationParams`` takes it and the
#: column stores it, but the catalogue refuses a text of only spaces (an empty text is written as null).
BLANK = "   "


async def test_post_with_a_blank_description_creates_the_asset_with_its_sector_and_no_description_row(engine: AsyncEngine) -> None:
    """``{short_description: "   ", sector_area: …}``: the asset is created; the profile gets its ``sector`` row by the
    author and no ``description`` row — a blank text is no description, and it must not make the item fail."""
    author = await _user(engine)

    response = await _create(engine, [FAAssetCreateItem(display_name="Blank-description ETF", currency="EUR", asset_type=AssetType.ETF, classification_params=_classification(description=BLANK, sector=SECTOR))], user_id=author)

    assert [result.success for result in response.results] == [True], f"the asset must be created: {response.results}"
    rows = await _rows(engine, response.results[0].asset_id)
    assert _summary(rows) == [("sector", normalize_value("sector", SECTOR), USER, author)], f"the sector row by the author and no description row: {_summary(rows)}"


async def test_patch_with_a_blank_description_empties_the_description_voice(engine: AsyncEngine) -> None:
    """The profile holds a description; a PATCH sending ``short_description: "   "`` is saved (no ``patchFailed``) and
    writes a NULL ``description`` row by the author: spaces only count as empty."""
    author = await _user(engine)
    asset = await _full_asset(engine, "Blanked ETF")
    await _seed(engine, asset, "description", DESCRIPTION, "legacy", _utc_today() - timedelta(days=3))
    before = await _rows(engine, asset)

    response = await _patch(engine, [FAAssetPatchItem(asset_id=asset, classification_params=_classification(description=BLANK))], user_id=author)

    assert response.committed is True and response.issues == [], f"the batch must be saved, not refused: committed={response.committed}, issues {[(issue.asset_id, issue.code) for issue in response.issues]}"
    new = _new(before, await _rows(engine, asset))
    assert [(row["key"], row["value"], row["source"], row["user_id"]) for row in new] == [("description", None, USER, author)], f"one NULL description row by the author: {new}"


async def test_the_dry_run_of_a_blank_description_succeeds_and_writes_nothing(engine: AsyncEngine) -> None:
    """The same PATCH with ``commit=False``: answered as saveable (no issue, the item a success) and nothing written.
    Barrier, after it: the same PATCH saved writes the NULL description row, so the dry run's silence is its own."""
    author = await _user(engine)
    asset = await _full_asset(engine, "Blank dry-run ETF")
    await _seed(engine, asset, "description", DESCRIPTION, "legacy", _utc_today() - timedelta(days=3))
    before = await _rows(engine, asset)
    patch = [FAAssetPatchItem(asset_id=asset, classification_params=_classification(description=BLANK))]

    dry = await _patch(engine, patch, user_id=author, commit=False)

    assert dry.committed is False and dry.issues == [] and dry.success_count == 1, f"the dry run must answer success: success_count={dry.success_count}, issues {[(issue.asset_id, issue.code) for issue in dry.issues]}"
    assert _new(before, await _rows(engine, asset)) == [], "the dry run must write no profile row"
    saved = await _patch(engine, patch, user_id=author)
    new = _new(before, await _rows(engine, asset))
    assert saved.committed is True and [(row["key"], row["value"]) for row in new] == [("description", None)], f"barrier: the saved patch writes the NULL description row: {new}"
