"""
Test Suite: the settings of a BRIM plugin reach the parse, and a changed setting makes the parse stale (CP12, W5-8)

The wiring of the contract of «A field in a BRIM plugin» (``backend/brim/architecture.md``) for the first real field,
``date_order`` of ``broker_generic_csv``. The rule itself, ``settings_changed_since``, is pinned by
``test_brim_field_contract.py``; this module pins the code that feeds it.

1. **The value reaches the subprocess** (D). ``brim_parse_pool.parse_file_offloaded(..., bound=<BoundSettings>)`` hands the given
   values to the worker of the REAL process pool (the thread fallback is the control): a parse with ``month_first`` gives the
   month-first dates. Without ``bound`` the values are resolved as before, in the parent, for ``user_id`` (a user with nothing
   stored reads day first, one who chose ``month_first`` reads month first). With ``bound`` the database is not read at all, and
   ``bound=None`` means «no settings»: the defaults.
2. **The fingerprint is stored with the parse** (E1). ``save_parse_result(..., settings_fingerprint=fp)`` writes
   ``parsed_settings_fingerprint`` in the metadata sidecar, ``None`` removes it, ``BRIMFileInfo`` carries it, and the API never
   shows it (``exclude=True``).
3. **A file is stale when the user's values moved** (E2). ``brim_file_settings.apply_settings_staleness(files, user_id)``: a PARSED
   file of a plugin that declares fields is stale when ``settings_changed_since(saved, current)`` says so, with ``current`` the
   values of the user who looks; a parse drawn before the field existed (no fingerprint) is compared with the defaults; a plugin
   without fields, a file not PARSED and another user's value change nothing; a flag already true stays true; the values are
   read once per plugin.

The bound values are built the way the core builds them (``build_bound_settings``) from a field copied from the contract, and the
user's rows live in a private SQLite file reached through a private engine put in the place of ``runtime.get_async_engine``.
The plugin's own declaration is pinned by ``test_external/test_brim_date_order.py``.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import PluginUserSetting, User
from backend.app.schemas.brim import BRIMFileInfo, BRIMParseOutput
from backend.app.services.brim import brim_parse_pool, brim_provider
from backend.app.services.brim.brim_provider import BRIMFileStatus
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.plugin_settings import resolver, runtime
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType
from backend.app.services.plugin_settings.resolver import StoredValue, build_bound_settings, default_settings_fingerprint

CODE = "broker_generic_csv"
BROKER_ID = 5
KEY = "LibreFolio-brim-file-settings-test-key-0123456789"

DATE_ORDER = PluginSettingField(
    key="date_order",
    type=SettingType.SELECT,
    scope=SettingScope.USER,
    label="Order of day and month",
    default="day_first",
    options=(SettingOption("day_first", "Day first"), SettingOption("month_first", "Month first")),
)

HEADER = "date,type,quantity,amount,currency,asset,description\n"
#: One ambiguous date and one that cannot be read two ways, found again by their description.
AMBIGUOUS_CSV = HEADER + "03/01/2025,BUY,5,-500.00,EUR,MSFT,ambiguous\n25/12/2025,BUY,2,-200.00,EUR,AAPL,unambiguous\n"
MINIMAL_CSV = b"date,type,quantity,amount,currency,asset\n2025-01-01,DEPOSIT,0,100,EUR,\n"


# =============================================================================
# HELPERS
# =============================================================================


def _stored(value: str) -> StoredValue:
    return StoredValue(value_json=json.dumps(value), secret_ciphertext=None, key_id=None, updated_at=datetime.now(UTC))


def _bound(order: str | None) -> BoundSettings:
    """What the core binds for a user who saved ``order`` (None: nothing saved)."""
    rows = {"date_order": _stored(order)} if order is not None else {}
    return build_bound_settings("brim", CODE, (DATE_ORDER,), {}, rows, user_id=7)


def _dates(output: BRIMParseOutput) -> dict[str, date]:
    """The date of each transaction of a parse by the description the test wrote."""
    return {tx.description: tx.date for tx in output.transactions}


DAY_FIRST_DATES = {"ambiguous": date(2025, 1, 3), "unambiguous": date(2025, 12, 25)}
MONTH_FIRST_DATES = {"ambiguous": date(2025, 3, 1), "unambiguous": date(2025, 12, 25)}


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """A test instance key, the once-per-process logs of the resolver empty. The data directory is NOT redirected: the worker of
    the pool resolves the upload area from the environment it was born with, which must be the parent's."""
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY)
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])


@pytest.fixture
def isolated_brim_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """BRIM storage redirected to a directory of this test (the metadata sidecars are read and written in this process only)."""
    reports = tmp_path / "broker_reports"
    reports.mkdir()
    monkeypatch.setattr(brim_provider, "get_broker_reports_dir", lambda: reports)
    return reports


@pytest.fixture
def reset_pool() -> Iterator[None]:
    """Each test starts from a pristine pool and leaves no worker behind (as ``test_brim_parse_pool.py``)."""
    brim_parse_pool.shutdown_pool()
    brim_parse_pool._pool_disabled = False
    yield
    brim_parse_pool.shutdown_pool()
    brim_parse_pool._pool_disabled = False


@pytest.fixture
def uploaded_ambiguous(reset_pool: None) -> Iterator[str]:
    """A real upload (the lane's upload area, which the pool's worker resolves too) of a CSV with an ambiguous date; deleted after."""
    info = brim_provider.save_uploaded_file(AMBIGUOUS_CSV.encode(), f"date-order-{uuid.uuid4().hex[:8]}.csv", user_id=1, broker_id=BROKER_ID)
    yield info.file_id
    brim_provider.delete_file(info.file_id)


@pytest_asyncio.fixture
async def private_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole ORM schema; disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'settings.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def reads(private_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """The settings rows are read through the private engine; the list counts the reads."""
    seen: list[int] = []

    def engine() -> AsyncEngine:
        seen.append(1)
        return private_engine

    monkeypatch.setattr(runtime, "get_async_engine", engine)
    return seen


@pytest_asyncio.fixture
async def users(private_engine: AsyncEngine) -> dict[str, int]:
    """Two users of the private database: alice and bob."""
    async with AsyncSession(private_engine, expire_on_commit=False) as session:
        alice = User(username="alice", email="alice@example.test", hashed_password="$argon2id$test")
        bob = User(username="bob", email="bob@example.test", hashed_password="$argon2id$test")
        session.add_all([alice, bob])
        await session.commit()
        return {"alice": alice.id, "bob": bob.id}


async def _choose(engine: AsyncEngine, user_id: int, value: str | None, code: str = CODE) -> None:
    """The user's own ``date_order``: ``value`` saved (replacing any), or the saved value deleted when ``None``."""
    async with AsyncSession(engine) as session:
        await session.execute(delete(PluginUserSetting).where(PluginUserSetting.user_id == user_id, PluginUserSetting.plugin_code == code))
        if value is not None:
            session.add(PluginUserSetting(user_id=user_id, family="brim", plugin_code=code, field_key="date_order", value_json=json.dumps(value)))
        await session.commit()


# =============================================================================
# D. THE VALUE REACHES THE SUBPROCESS
# =============================================================================


def _the_pool_carried_it(pool: bool) -> None:
    assert (brim_parse_pool._pool is not None) is pool, "barrier: the real process pool carried the parse (or the thread fallback did, as asked)"


@pytest.mark.asyncio
@pytest.mark.parametrize("pool", [pytest.param(True, id="process-pool"), pytest.param(False, id="thread-fallback")])
async def test_a_bound_month_first_reaches_the_parse_in_the_worker(pool: bool, uploaded_ambiguous: str, monkeypatch: pytest.MonkeyPatch):
    """D: ``bound`` is delivered to the worker as the settings of the plugin: the dates are read month first."""
    monkeypatch.setattr(brim_parse_pool, "_pool_disabled", not pool)

    output = await brim_parse_pool.parse_file_offloaded(uploaded_ambiguous, CODE, BROKER_ID, bound=_bound("month_first"))

    _the_pool_carried_it(pool)
    assert _dates(output) == MONTH_FIRST_DATES


@pytest.mark.asyncio
async def test_a_bound_day_first_is_read_day_first(uploaded_ambiguous: str):
    output = await brim_parse_pool.parse_file_offloaded(uploaded_ambiguous, CODE, BROKER_ID, bound=_bound("day_first"))

    _the_pool_carried_it(True)
    assert _dates(output) == DAY_FIRST_DATES


@pytest.mark.asyncio
async def test_bound_none_means_no_settings_and_the_defaults(uploaded_ambiguous: str, reads: list[int]):
    """D: ``bound=None`` is «no settings»: the plugin sees the defaults (day first) and nothing is resolved from the database."""
    output = await brim_parse_pool.parse_file_offloaded(uploaded_ambiguous, CODE, BROKER_ID, user_id=1, bound=None)

    _the_pool_carried_it(True)
    assert _dates(output) == DAY_FIRST_DATES
    assert reads == [], "bound was given (None included): the parent resolved nothing"


@pytest.mark.asyncio
async def test_a_given_bound_wins_over_what_the_user_saved_and_reads_nothing(uploaded_ambiguous: str, users: dict[str, int], private_engine: AsyncEngine, reads: list[int]):
    """D: alice saved day first, the caller hands month first: the caller's values are the parse's, and the database is not read."""
    await _choose(private_engine, users["alice"], "day_first")

    output = await brim_parse_pool.parse_file_offloaded(uploaded_ambiguous, CODE, BROKER_ID, user_id=users["alice"], bound=_bound("month_first"))

    assert _dates(output) == MONTH_FIRST_DATES
    assert reads == []


@pytest.mark.asyncio
async def test_without_bound_a_user_with_nothing_stored_reads_day_first(uploaded_ambiguous: str, users: dict[str, int], reads: list[int]):
    """D: not passing ``bound`` resolves it as before, in the parent: nothing stored is the default, day first."""
    output = await brim_parse_pool.parse_file_offloaded(uploaded_ambiguous, CODE, BROKER_ID, user_id=users["alice"])

    _the_pool_carried_it(True)
    assert _dates(output) == DAY_FIRST_DATES


@pytest.mark.asyncio
async def test_without_bound_the_value_the_user_saved_is_resolved_and_reaches_the_worker(uploaded_ambiguous: str, users: dict[str, int], private_engine: AsyncEngine, reads: list[int]):
    """D, the whole way: the row of alice -> ``bound_settings_for`` in the parent -> the worker -> month-first dates; bob, who saved
    nothing, reads the same file day first."""
    await _choose(private_engine, users["alice"], "month_first")

    alices = await brim_parse_pool.parse_file_offloaded(uploaded_ambiguous, CODE, BROKER_ID, user_id=users["alice"])
    bobs = await brim_parse_pool.parse_file_offloaded(uploaded_ambiguous, CODE, BROKER_ID, user_id=users["bob"])

    _the_pool_carried_it(True)
    assert _dates(alices) == MONTH_FIRST_DATES
    assert _dates(bobs) == DAY_FIRST_DATES
    assert len(reads) >= 2, "the rows were read from the database, in the parent"


# =============================================================================
# E1. THE FINGERPRINT IS STORED WITH THE PARSE
# =============================================================================


def _sidecar(file_id: str) -> dict[str, Any]:
    meta_path = brim_provider._find_metadata_path(file_id)
    assert meta_path is not None, "barrier: the file has a metadata sidecar"
    return json.loads(meta_path.read_text())


def _upload(content: bytes = MINIMAL_CSV) -> str:
    return brim_provider.save_uploaded_file(content=content, original_filename="settings.csv", user_id=1).file_id


def _record(file_id: str, plugin_code: str = CODE, **extra: Any) -> bool:
    return brim_provider.save_parse_result(file_id, {"transactions": [], "warnings": []}, plugin_code=plugin_code, **extra)


def test_save_parse_result_stores_the_fingerprint_in_the_sidecar(isolated_brim_dir: Path):
    file_id = _upload()
    fingerprint = _bound("month_first").fingerprint

    assert _record(file_id, settings_fingerprint=fingerprint) is True

    sidecar = _sidecar(file_id)
    assert sidecar["parsed_settings_fingerprint"] == fingerprint
    assert sidecar["parsed_plugin_code"] == CODE and sidecar["last_parse_result"] == {"transactions": [], "warnings": []}, "the rest is saved as before"


def test_save_parse_result_without_a_fingerprint_removes_the_one_saved_before(isolated_brim_dir: Path):
    """A re-parse that carries no fingerprint (a plugin without fields) must not leave the previous parse's record behind."""
    file_id = _upload()
    _record(file_id, settings_fingerprint=_bound("month_first").fingerprint)
    assert "parsed_settings_fingerprint" in _sidecar(file_id), "barrier: it was saved"

    _record(file_id)
    assert "parsed_settings_fingerprint" not in _sidecar(file_id)

    _record(file_id, settings_fingerprint=_bound("day_first").fingerprint)
    _record(file_id, settings_fingerprint=None)
    assert "parsed_settings_fingerprint" not in _sidecar(file_id)
    assert brim_provider.get_file_info(file_id).parsed_settings_fingerprint is None


def test_the_file_info_carries_the_fingerprint_and_the_api_never_shows_it(isolated_brim_dir: Path):
    file_id = _upload()
    fingerprint = _bound("month_first").fingerprint
    _record(file_id, settings_fingerprint=fingerprint)

    from_info = brim_provider.get_file_info(file_id)
    from_listing = next(f for f in brim_provider.list_files() if f.file_id == file_id)

    assert from_info.parsed_settings_fingerprint == fingerprint
    assert from_listing.parsed_settings_fingerprint == fingerprint
    for info in (from_info, from_listing):
        assert "parsed_settings_fingerprint" not in info.model_dump()
        assert "parsed_settings_fingerprint" not in info.model_dump(mode="json")
        assert "parsed_settings_fingerprint" not in info.model_dump_json()
        assert fingerprint not in info.model_dump_json()
    assert BRIMFileInfo.model_fields["parsed_settings_fingerprint"].exclude is True


def test_a_file_never_recorded_has_no_fingerprint(isolated_brim_dir: Path):
    file_id = _upload()

    assert brim_provider.get_file_info(file_id).parsed_settings_fingerprint is None


# =============================================================================
# E2. apply_settings_staleness
# =============================================================================


def _parsed_file(*, plugin_code: str = CODE, fingerprint: str | None = None, parsed: bool = True) -> str:
    """An uploaded file, moved to PARSED when ``parsed``, whose parse was recorded for ``plugin_code`` over ``fingerprint``."""
    file_id = _upload()
    if parsed:
        brim_provider._move_file(file_id, BRIMFileStatus.PARSED)
    if fingerprint is None:
        _record(file_id, plugin_code)
    else:
        _record(file_id, plugin_code, settings_fingerprint=fingerprint)
    return file_id


def _staleness_rule():
    """``apply_settings_staleness``, imported when a test needs it: the module is new in W5-8, and a top-level import would fail the
    collection of the whole file (the tests of the pool and of the sidecar included) instead of the tests that need it."""
    from backend.app.services.brim.brim_file_settings import apply_settings_staleness  # noqa: PLC0415

    return apply_settings_staleness


async def _apply(file_ids: list[str], user_id: int | None) -> list[BRIMFileInfo]:
    """``apply_settings_staleness`` over fresh infos of the files (a module that does not exist yet fails the test here)."""
    files = [brim_provider.get_file_info(file_id) for file_id in file_ids]
    assert all(info is not None and info.parse_is_stale is False for info in files), "barrier: nothing is stale before the rule is applied"
    await _staleness_rule()(files, user_id)
    return files


async def _stale(file_id: str, user_id: int | None) -> bool:
    (info,) = await _apply([file_id], user_id)
    return info.parse_is_stale


@pytest.mark.asyncio
async def test_a_file_parsed_with_the_defaults_is_not_stale_while_the_values_are_unchanged(isolated_brim_dir: Path, users: dict[str, int], reads: list[int]):
    """E (i): the fingerprint saved is that of the defaults and the user has chosen nothing."""
    file_id = _parsed_file(fingerprint=_bound(None).fingerprint)

    assert await _stale(file_id, users["alice"]) is False
    assert len(reads) >= 1, "barrier: the user's values were really resolved, so «not stale» was decided, not skipped"


@pytest.mark.asyncio
async def test_a_change_of_the_users_value_makes_the_file_stale_and_a_new_parse_makes_it_current(isolated_brim_dir: Path, users: dict[str, int], private_engine: AsyncEngine, reads: list[int]):
    """E (ii): month first chosen after the parse -> stale; parsed again over month first -> current; chosen back -> stale again."""
    file_id = _parsed_file(fingerprint=_bound(None).fingerprint)
    assert await _stale(file_id, users["alice"]) is False

    await _choose(private_engine, users["alice"], "month_first")
    assert await _stale(file_id, users["alice"]) is True

    _record(file_id, settings_fingerprint=_bound("month_first").fingerprint)
    assert await _stale(file_id, users["alice"]) is False

    await _choose(private_engine, users["alice"], None)
    assert await _stale(file_id, users["alice"]) is True, "the values moved back to the default: the record says month first"


@pytest.mark.asyncio
async def test_a_file_parsed_before_the_field_existed_is_compared_with_the_defaults(isolated_brim_dir: Path, users: dict[str, int], private_engine: AsyncEngine, reads: list[int]):
    """E (iii): no fingerprint saved -> not stale at the defaults, stale once the user picked month first."""
    file_id = _parsed_file(fingerprint=None)
    assert "parsed_settings_fingerprint" not in _sidecar(file_id), "barrier: nothing was recorded"

    assert await _stale(file_id, users["alice"]) is False

    await _choose(private_engine, users["alice"], "month_first")
    assert await _stale(file_id, users["alice"]) is True
    assert default_settings_fingerprint((DATE_ORDER,)) == _bound(None).fingerprint, "the baseline is the fingerprint of the defaults"


@pytest.mark.asyncio
async def test_a_plugin_without_fields_is_never_stale_for_its_settings(isolated_brim_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """E (iv): schwab declares no field: whatever fingerprint a file carries, it is not stale, and the database is not reached."""

    def no_database() -> AsyncEngine:
        raise AssertionError("the settings database was reached: schwab declares no field")

    monkeypatch.setattr(runtime, "get_async_engine", no_database)
    plugin_class = BRIMProviderRegistry.get_plugin("broker_schwab")
    assert plugin_class is not None and not plugin_class.settings_fields, "barrier: schwab declares no field"
    file_id = _parsed_file(plugin_code="broker_schwab", fingerprint="0" * 32)

    assert await _stale(file_id, 4242) is False


@pytest.mark.asyncio
async def test_another_users_value_does_not_make_my_file_stale(isolated_brim_dir: Path, users: dict[str, int], private_engine: AsyncEngine, reads: list[int]):
    """E (v): bob chose month first; the file was parsed over the defaults. For alice it is current; for bob, who is looking
    with month first, it is stale (the control that makes the first answer mean something)."""
    file_id = _parsed_file(fingerprint=_bound(None).fingerprint)
    await _choose(private_engine, users["bob"], "month_first")

    assert await _stale(file_id, users["alice"]) is False
    assert await _stale(file_id, users["bob"]) is True


@pytest.mark.asyncio
async def test_no_user_means_the_instance_values_and_the_defaults(isolated_brim_dir: Path, users: dict[str, int], private_engine: AsyncEngine, reads: list[int]):
    """A call for nobody sees no personal value: alice's choice does not make the file stale."""
    file_id = _parsed_file(fingerprint=_bound(None).fingerprint)
    await _choose(private_engine, users["alice"], "month_first")

    assert await _stale(file_id, None) is False


@pytest.mark.asyncio
async def test_a_file_that_is_not_parsed_is_left_alone(isolated_brim_dir: Path, users: dict[str, int], private_engine: AsyncEngine, reads: list[int]):
    """Only a PARSED file has a parse to be stale: an uploaded one keeps its flag, whatever the user chose."""
    file_id = _parsed_file(fingerprint=_bound(None).fingerprint, parsed=False)
    await _choose(private_engine, users["alice"], "month_first")
    info = brim_provider.get_file_info(file_id)
    assert info.status == BRIMFileStatus.UPLOADED and info.parsed_plugin_code == CODE, "barrier: not PARSED, yet it records a parse"

    assert await _stale(file_id, users["alice"]) is False


@pytest.mark.asyncio
async def test_a_flag_already_true_stays_true(isolated_brim_dir: Path, users: dict[str, int], reads: list[int], monkeypatch: pytest.MonkeyPatch):
    """The rule adds to the plugin-version staleness (``or``), it never clears it: the values are unchanged, the plugin is newer."""
    file_id = _parsed_file(fingerprint=_bound(None).fingerprint)
    plugin_class = type(BRIMProviderRegistry.get_provider_instance(CODE))
    monkeypatch.setattr(plugin_class, "plugin_version", "9.9.9-stale-test")
    assert brim_provider.get_file_info(file_id).parse_is_stale is True, "barrier: stale by version"

    files = [brim_provider.get_file_info(file_id)]
    await _staleness_rule()(files, users["alice"])

    assert files[0].parse_is_stale is True


@pytest.mark.asyncio
async def test_the_values_are_read_once_per_plugin_for_many_files(isolated_brim_dir: Path, users: dict[str, int], private_engine: AsyncEngine, reads: list[int]):
    """Cached inside the call: three files of one plugin are one read of the user's values, each judged by its own fingerprint."""
    await _choose(private_engine, users["alice"], "month_first")
    current = _parsed_file(fingerprint=_bound("month_first").fingerprint)
    old_a = _parsed_file(fingerprint=_bound(None).fingerprint)
    old_b = _parsed_file(fingerprint=None)
    reads.clear()

    files = await _apply([current, old_a, old_b], users["alice"])

    assert [info.parse_is_stale for info in files] == [False, True, True]
    assert len(reads) == 1, f"the user's values were read {len(reads)} times for one plugin"
