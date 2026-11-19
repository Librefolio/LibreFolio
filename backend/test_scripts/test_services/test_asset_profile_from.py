"""«Use the source's value» in the profile writes of POST/PATCH /assets (project 68, lot B5b; plan §3.5, §3.7).

A profile value ``{"from": "<code>"}`` or ``{"from": "<code>", "seen": <value>}`` (exactly those keys) on
``AssetCRUDService.patch_assets_bulk`` / ``create_assets_bulk`` means «use that enricher's value»:

1. **Resolution.** The value comes from that enricher's read of the asset's binding **after the item** (when the same
   item sets ``enrichers``, the new one): the ``enricher_read`` cache when it holds that voice (the plugin is not
   called), otherwise a read now, which asks for that voice and fills the cache like any read. A cached read of other
   voices only does not answer: the plugin is called.
2. **The row** is written in the source's name: ``source`` the code, ``user_id`` NULL, ``source_date`` the read's; also
   when «now» holds the same value from another source (``force_source``); no row when «now» is already that value from
   that same source. The item's other voices are written by hand as before.
3. **Refused** as the issue ``profileValueInvalid`` on ``profile.<voice>`` (checking phase: nothing of the batch saved;
   the dry run answers the same): a code not among the asset's enrichers (after the item: a code the item removes is
   refused), an enricher not installed, an enricher that gives no value for that voice, does not find the asset or
   fails (an error answer, a raise). Keys other than ``from`` and ``seen`` are not a «from».
4. **``seen``** is compared in stored form: a value read now that differs is saved anyway, with the warning
   ``profileSourceChanged`` (``field`` ``profile.<voice>``, ``params`` ``{voice, seen, now}``, both stored); an equal
   ``seen`` (another spelling, a map in another order) and no ``seen`` give no warning.
5. **Dry run** (``commit=False``, ``POST /assets/validate``): the same issues and warnings, nothing written.
6. **POST** takes ``{"from"}`` with the item's ``enrichers``; a refused one fails that item (asset not created), the
   other items are created.
7. **A batch rolled back while applying** (``patchFailed`` on another item, which only the flush reveals) writes no
   profile row (plan 68, D7a: the case the old double-write suite pinned through
   ``classification_params``).

The synthetic enrichers are classes registered on ``EnricherRegistry`` under ``lab_from_*`` codes (removed with their
claims at teardown), answering from a table identifier → values (filtered to the ``keys`` asked) or an outcome, and
recording every ``read`` call (bindings, keys) under a lock. Every identifier is unique to its test and the process-wide
``enricher_read`` cache is cleared before and after each test.

Every test that asserts a refusal, or the absence of a row, first proves in the same test that a valid ``{"from"}`` on
the same asset commits and writes its row (red until B5b, so no refusal passes on today's catalogue refusal of every
``{"from"}``); a refusal that depends on a read also proves the lab was called.

Every database is a private SQLite file under ``tmp_path`` built with ``SQLModel.metadata.create_all``, opened as
production opens its own (aiosqlite, NullPool, the PRAGMA listener of ``backend.app.db.session``). No server, no
network.

Not pinned: whether a cache miss asks the plugin for exactly that voice or for more (only that the voice is asked or
all are); the ``message`` texts; what POST answers about ``seen`` (``FAAssetCreateResult`` has no warnings); which of
several refusals of one item comes first; a «from» of a voice the enricher's declarations do not list for the type.

Red until B5b: the catalogue refuses every ``{"from"}`` (``profileValueInvalid``), so every test fails on an assertion
(``committed``, a row, a call), never at collection. The code ``profileSourceChanged`` is compared as a string: the
enum member does not exist yet.
"""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import AsyncIterator, Callable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetProfileUpdate, AssetType, User
from backend.app.schemas.assets.assets import FAAssetCreateItem, FAAssetPatchItem, FABulkAssetCreateResponse, FABulkAssetPatchResponse
from backend.app.services.assets.crud import AssetCRUDService
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.app.services.enrichers import bindings
from backend.app.services.enrichers.base import EnricherBinding, EnricherPlugin, EnricherReadItem, EnricherReadStatus, EnricherRecognition, EnricherTerms
from backend.app.services.enrichers.refresh import ReadRequest, read_bindings
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.plugin_settings.fields import release_env_variables
from backend.app.utils.runtime.cache import clear_cache
from backend.test_scripts.test_utils import print_section, print_success

pytestmark = pytest.mark.asyncio

SETTINGS_FAMILY = "enricher"
LAB_PREFIX = "lab_from_"
LAB_CLASS_PREFIX = "LabFromEnricher_"
CACHE_NAME = "enricher_read"
LAB_DATE = date(2026, 10, 31)
PROFILE_VALUE_INVALID = "profileValueInvalid"
PROFILE_SOURCE_CHANGED = "profileSourceChanged"
#: Every voice a lab may yield, declared for ETF.
LAB_VOICES = frozenset({"ter", "description", "geography", "distribution_policy"})
TER = "0.0022"
TER_OTHER = "0.0031"
RAW_GEOGRAPHY = {"USA": "0.6", "JPN": "0.4"}
#: An enricher code that is never installed.
ABSENT_CODE = "zeta_from_absent"

#: The outcomes a lab's table can give instead of values.
NOT_FOUND = "not_found"
ERROR = "error"
RAISE = "raise"


def _ident(tag: str) -> str:
    """An identifier no other test (and no other run within the cache's TTL) uses."""
    return f"LFR{tag}{uuid.uuid4().hex[:10].upper()}"


def _entry(identifier: str) -> dict[str, Any]:
    """A binding as ``asset_enrichers.config`` stores it and as ``enrichers`` sends it."""
    return {"identifier_type": "ISIN", "identifier": identifier}


def _from(code: str, **seen: Any) -> dict[str, Any]:
    """A ``{"from": code}`` value, with ``seen`` when given (``_from(code, seen=…)``)."""
    return {"from": code, **seen}


# =============================================================================
# THE LABS
# =============================================================================


@dataclass
class Lab:
    """A registered synthetic enricher: its code, its answers, every ``read`` call as (identifiers, keys)."""

    code: str
    table: dict[str, Any]
    calls: list[tuple[tuple[str, ...], Optional[frozenset[str]]]] = field(default_factory=list)

    def identifiers_read(self) -> list[str]:
        return [identifier for identifiers, _ in self.calls for identifier in identifiers]


class _LabMethods(EnricherPlugin):
    """The abstract methods but ``read``."""

    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        return EnricherRecognition(found=True, name=f"Lab {binding.identifier}")

    def page_url(self, binding: EnricherBinding) -> str | None:
        return f"https://lab.invalid/{binding.identifier}"

    @property
    def test_cases(self) -> list[dict]:
        return []


def _answer(table: Mapping[str, Any], bindings_read: list[EnricherBinding], keys: Optional[frozenset[str]]) -> Iterator[EnricherReadItem]:
    for index, binding in enumerate(bindings_read):
        spec = table[binding.identifier]
        if spec == RAISE:
            raise RuntimeError(f"lab source down at {binding.identifier}")
        if spec == NOT_FOUND:
            yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
        elif spec == ERROR:
            yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code="LAB_ERROR", error_message="the lab fails on purpose")
        else:
            values = dict(spec) if keys is None else {key: value for key, value in spec.items() if key in keys}
            yield EnricherReadItem(index=index, status=EnricherReadStatus.OK, values=values, source_date=LAB_DATE)


@pytest.fixture(autouse=True)
def _fresh_read_cache() -> Iterator[None]:
    """The read cache is process-wide: empty before and after each test."""
    clear_cache(CACHE_NAME)
    yield
    clear_cache(CACHE_NAME)


@pytest.fixture(autouse=True)
def _no_timezone_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The store's today follows ``scheduler_timezone``; a deployment variable must not move it under the test."""
    monkeypatch.delenv("LIBREFOLIO_DEFAULT_TIMEZONE", raising=False)


@pytest.fixture
def lab() -> Iterator[Callable[..., Lab]]:
    """``lab(name, table)`` registers a synthetic enricher covering ETF and gives back its ``Lab``; removed, with its
    claims, at teardown."""
    labs: list[Lab] = []

    def register(name: str, table: dict[str, Any]) -> Lab:
        code = f"{LAB_PREFIX}{name}"
        handle = Lab(code=code, table=table)
        lock = threading.Lock()

        def read(self, bindings_read, keys=None) -> Iterator[EnricherReadItem]:  # noqa: ARG001 — the contract's signature
            received = None if keys is None else frozenset(keys)
            with lock:
                handle.calls.append((tuple(binding.identifier for binding in bindings_read), received))
            yield from _answer(handle.table, list(bindings_read), received)

        attributes: dict[str, Any] = {
            "code": code,
            "name": f"Lab from {name} (testing)",
            "terms": EnricherTerms.OPEN,
            "accepted_identifier_types": ("ISIN", "LEI", "TICKER"),
            "default_priority": {asset_type: (10 if asset_type == AssetType.ETF else None) for asset_type in AssetType},
            "voices": {AssetType.ETF: LAB_VOICES},
            "read": read,
        }
        labs.append(handle)
        EnricherRegistry.register(type(f"{LAB_CLASS_PREFIX}{name}", (_LabMethods,), attributes))
        assert isinstance(EnricherRegistry.get_plugin_instance(code), EnricherPlugin), f"barrier: {code} is not served after its registration"
        return handle

    yield register
    storage = EnricherRegistry._get_storage()
    for handle in labs:
        stored = storage.get(handle.code)
        if stored is not None and getattr(stored, "__name__", "").startswith(LAB_CLASS_PREFIX):
            storage.pop(handle.code, None)
        release_env_variables(SETTINGS_FAMILY, handle.code)


# =============================================================================
# THE DATABASE
# =============================================================================


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'asset_profile_from.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
            foreign_keys = (await connection.execute(text("PRAGMA foreign_keys"))).scalar()
        assert foreign_keys == 1, "barrier: the app's PRAGMA listener must hold on the private file (foreign keys on)"
        yield engine
    finally:
        await engine.dispose()


async def _user(engine: AsyncEngine) -> int:
    name = f"from_{uuid.uuid4().hex[:8]}"
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=name, email=f"{name}@example.com", hashed_password="$argon2id$seeded-account")
        session.add(user)
        await session.commit()
    return int(user.id)


async def _asset(engine: AsyncEngine, tag: str, config: Optional[Mapping[str, Mapping[str, Any]]] = None) -> int:
    """An ETF, bound to ``config`` (code → binding, in its order) when given."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=f"Lab from {tag} {uuid.uuid4().hex[:8]}", currency="EUR", asset_type=AssetType.ETF)
        session.add(asset)
        await session.commit()
    asset_id = int(asset.id)
    if config:
        async with AsyncSession(engine) as session:
            await bindings.save_config(session, asset_id, {code: dict(binding) for code, binding in config.items()})
            await session.commit()
    return asset_id


async def _config(engine: AsyncEngine, asset_id: int) -> dict[str, Any]:
    async with AsyncSession(engine) as session:
        row = (await bindings.load_enrichers(session, [asset_id])).get(asset_id)
    return {} if row is None else row.config


async def _name(engine: AsyncEngine, asset_id: int) -> str:
    async with AsyncSession(engine) as session:
        return (await session.execute(text("SELECT display_name FROM assets WHERE id = :asset"), {"asset": asset_id})).scalar_one()


async def _asset_id_named(engine: AsyncEngine, name: str) -> Optional[int]:
    async with AsyncSession(engine) as session:
        return (await session.execute(text("SELECT id FROM assets WHERE display_name = :name"), {"name": name})).scalar()


async def _seed(engine: AsyncEngine, asset_id: int, key: str, value: Any, source: str, *, user_id: Optional[int] = None, read_on: Optional[date] = None) -> int:
    """One profile row as the model writes it, without the store, a week back unless ``read_on`` is given."""
    stored = None if value is None else json.dumps(normalize_value(key, value))
    async with AsyncSession(engine, expire_on_commit=False) as session:
        row = AssetProfileUpdate(asset_id=asset_id, key=key, value=stored, source=source, user_id=user_id, read_on=read_on or (date.today() - timedelta(days=7)))
        session.add(row)
        await session.commit()
    return int(row.id)


async def _rows(engine: AsyncEngine, asset_id: int) -> list[dict[str, Any]]:
    """The asset's profile rows by id; ``stored`` the value as the store reads it, ``source_date`` a date or None."""
    query = "SELECT id, key, value, source, user_id, source_date FROM asset_profile_updates WHERE asset_id = :asset ORDER BY id"
    async with AsyncSession(engine) as session:
        rows = [dict(row._mapping) for row in await session.execute(text(query), {"asset": asset_id})]
    for row in rows:
        row["stored"] = None if row["value"] is None else normalize_value(row["key"], json.loads(row["value"]))
        row["source_date"] = None if row["source_date"] is None else date.fromisoformat(str(row["source_date"]))
    return rows


def _new(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    known = {row["id"] for row in before}
    return [row for row in after if row["id"] not in known]


def _by_key(rows: list[dict[str, Any]]) -> dict[str, tuple[Any, str, Optional[int], Optional[date]]]:
    """Rows as voice → (stored value, source, author, source_date); one row per voice expected."""
    summary = {row["key"]: (row["stored"], row["source"], row["user_id"], row["source_date"]) for row in rows}
    assert len(summary) == len(rows), f"one row per voice: {rows}"
    return summary


async def _patch(engine: AsyncEngine, items: list[dict[str, Any]], *, user_id: int, commit: bool = True) -> FABulkAssetPatchResponse:
    patches = [FAAssetPatchItem(**item) for item in items]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await AssetCRUDService.patch_assets_bulk(patches, session, commit=commit, user_id=user_id)


async def _create(engine: AsyncEngine, items: list[dict[str, Any]], *, user_id: int) -> FABulkAssetCreateResponse:
    creates = [FAAssetCreateItem(**item) for item in items]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await AssetCRUDService.create_assets_bulk(creates, session, user_id=user_id)


def _issues(body: FABulkAssetPatchResponse) -> list[tuple[int, int, str, Optional[str]]]:
    return [(issue.asset_id, issue.index, str(issue.code), issue.field) for issue in body.issues]


def _warnings(body: FABulkAssetPatchResponse) -> list[tuple[int, int, str, Optional[str], Optional[dict[str, Any]]]]:
    return [(warning.asset_id, warning.index, str(warning.code), warning.field, warning.params) for warning in body.warnings]


async def _commit_from(engine: AsyncEngine, asset_id: int, code: str, *, user_id: int, voice: str = "ter") -> list[dict[str, Any]]:
    """Barrier: a valid ``{"from": code}`` on ``voice`` commits and writes its row in the source's name. The new rows."""
    before = await _rows(engine, asset_id)
    body = await _patch(engine, [{"asset_id": asset_id, "profile": {voice: _from(code)}}], user_id=user_id)
    assert body.committed is True and body.issues == [], f"barrier: a valid {{'from': {code!r}}} commits: {_issues(body)}"
    new = _new(before, await _rows(engine, asset_id))
    assert [(row["key"], row["source"], row["user_id"]) for row in new] == [(voice, code, None)], f"barrier: the valid «from» writes its row in the source's name: {new}"
    return new


# =============================================================================
# 1. Resolution: the cache, a read now, the cache filled
# =============================================================================


async def test_from_with_the_voice_cached_writes_the_row_in_the_sources_name_without_calling_it(engine, lab) -> None:
    print_section("B5b: {'from'} answered by the read cache")
    user_id = await _user(engine)
    identifier = _ident("HIT")
    a = lab("hit", {identifier: {"ter": TER, "description": "Lab hit"}})
    asset_id = await _asset(engine, "HIT", {a.code: _entry(identifier)})
    primed = [outcome async for outcome in read_bindings([ReadRequest(owner=asset_id, code=a.code, binding=EnricherBinding(identifier_type="ISIN", identifier=identifier))])]
    assert [outcome.status for outcome in primed] == [EnricherReadStatus.OK] and len(a.calls) == 1, f"barrier: the cache holds the lab's read of every voice: {primed} {a.calls}"

    body = await _patch(engine, [{"asset_id": asset_id, "profile": {"ter": _from(a.code), "description": "Written by hand"}}], user_id=user_id)

    assert body.committed is True and body.issues == [] and body.warnings == [], f"a «from» the cache answers is saved: {_issues(body)} {_warnings(body)}"
    assert len(a.calls) == 1, f"the cache answers: the lab is not called again: {a.calls}"
    rows = _by_key(await _rows(engine, asset_id))
    assert rows["ter"] == (TER, a.code, None, LAB_DATE), f"ter in the source's name, no author, the read's source_date: {rows['ter']}"
    assert rows["description"] == ("Written by hand", "user", user_id, None), f"the item's other voice by hand: {rows['description']}"
    print_success("cache hit: no call, the row in the source's name")


async def test_from_with_nothing_cached_reads_the_voice_once(engine, lab) -> None:
    print_section("B5b: {'from'} read now")
    user_id = await _user(engine)
    identifier = _ident("MISS")
    a = lab("miss", {identifier: {"ter": TER, "description": "Lab miss"}})
    asset_id = await _asset(engine, "MISS", {a.code: _entry(identifier)})

    body = await _patch(engine, [{"asset_id": asset_id, "profile": {"ter": _from(a.code)}}], user_id=user_id)

    assert body.committed is True and body.issues == [], f"a «from» read now is saved: {_issues(body)}"
    assert [identifiers for identifiers, _ in a.calls] == [(identifier,)], f"one read of the asset's binding: {a.calls}"
    keys = a.calls[0][1]
    assert keys is None or "ter" in keys, f"the read asks for that voice: {keys}"
    assert _by_key(await _rows(engine, asset_id)) == {"ter": (TER, a.code, None, LAB_DATE)}, "the row in the source's name"


async def test_a_cached_read_of_other_voices_does_not_answer_the_from(engine, lab) -> None:
    user_id = await _user(engine)
    identifier = _ident("PART")
    a = lab("partial", {identifier: {"ter": TER, "description": "Lab partial"}})
    asset_id = await _asset(engine, "PART", {a.code: _entry(identifier)})
    request = ReadRequest(owner=asset_id, code=a.code, binding=EnricherBinding(identifier_type="ISIN", identifier=identifier))
    primed = [outcome async for outcome in read_bindings([request], ["description"])]
    assert [outcome.status for outcome in primed] == [EnricherReadStatus.OK] and len(a.calls) == 1, f"barrier: the cache holds a read of description only: {primed}"

    body = await _patch(engine, [{"asset_id": asset_id, "profile": {"ter": _from(a.code)}}], user_id=user_id)

    assert body.committed is True and body.issues == [], f"saved: {_issues(body)}"
    assert len(a.calls) == 2, f"a read of other voices does not hold ter: the lab is called: {a.calls}"
    assert _by_key(await _rows(engine, asset_id))["ter"] == (TER, a.code, None, LAB_DATE)


async def test_the_resolutions_read_fills_the_cache(engine, lab) -> None:
    user_id = await _user(engine)
    identifier = _ident("FILL")
    a = lab("fill", {identifier: {"ter": TER}})
    asset_id = await _asset(engine, "FILL", {a.code: _entry(identifier)})
    body = await _patch(engine, [{"asset_id": asset_id, "profile": {"ter": _from(a.code)}}], user_id=user_id)
    assert body.committed is True and len(a.calls) == 1, f"barrier: the «from» was read now: {_issues(body)} {a.calls}"

    request = ReadRequest(owner=asset_id, code=a.code, binding=EnricherBinding(identifier_type="ISIN", identifier=identifier))
    again = [outcome async for outcome in read_bindings([request], ["ter"])]

    assert [(outcome.status, outcome.from_cache, dict(outcome.values)) for outcome in again] == [(EnricherReadStatus.OK, True, {"ter": TER})], f"a normal read: it is in the cache: {again}"
    assert len(a.calls) == 1, f"the lab is not called again: {a.calls}"


# =============================================================================
# 2. The row: force over the same value from another source, none over the same source
# =============================================================================


async def test_from_over_the_same_value_from_another_source_writes_the_row(engine, lab) -> None:
    print_section("B5b: {'from'} forces the source's name")
    user_id = await _user(engine)
    identifier = _ident("FORCE")
    a = lab("force", {identifier: {"ter": TER}})
    asset_id = await _asset(engine, "FORCE", {a.code: _entry(identifier)})
    seeded = await _seed(engine, asset_id, "ter", "0.00220", "user", user_id=user_id)
    before = await _rows(engine, asset_id)
    assert [(row["id"], row["stored"], row["source"]) for row in before] == [(seeded, TER, "user")], f"barrier: now is the same value, by hand: {before}"

    body = await _patch(engine, [{"asset_id": asset_id, "profile": {"ter": _from(a.code)}}], user_id=user_id)

    assert body.committed is True and body.issues == [], f"saved: {_issues(body)}"
    new = _new(before, await _rows(engine, asset_id))
    assert _by_key(new) == {"ter": (TER, a.code, None, LAB_DATE)}, f"the same value, a new row in the source's name: {new}"


async def test_from_when_now_is_that_value_from_that_source_writes_no_row(engine, lab) -> None:
    user_id = await _user(engine)
    identifier = _ident("SAME")
    a = lab("same", {identifier: {"ter": TER}})
    asset_id = await _asset(engine, "SAME", {a.code: _entry(identifier)})
    await _seed(engine, asset_id, "ter", TER, a.code)
    before = await _rows(engine, asset_id)

    body = await _patch(engine, [{"asset_id": asset_id, "profile": {"ter": _from(a.code), "description": "Proof the item was written"}}], user_id=user_id)

    assert body.committed is True and body.issues == [], f"saved: {_issues(body)}"
    new = _new(before, await _rows(engine, asset_id))
    assert [(row["key"], row["source"]) for row in new] == [("description", "user")], f"the item was written (description), ter is already that value from that source: no row: {new}"


# =============================================================================
# 3. The binding after the item
# =============================================================================


@pytest.mark.parametrize("bound_before", [pytest.param(True, id="replaced"), pytest.param(False, id="added")])
async def test_from_uses_the_binding_the_same_item_sets(engine, lab, bound_before) -> None:
    print_section("B5b: {'from'} with the item's new binding")
    user_id = await _user(engine)
    old, new = _ident("OLD"), _ident("NEW")
    a = lab("rebind", {old: {"ter": "0.001"}, new: {"ter": "0.003"}})
    asset_id = await _asset(engine, "REBIND", {a.code: _entry(old)} if bound_before else None)

    body = await _patch(engine, [{"asset_id": asset_id, "enrichers": {a.code: _entry(new)}, "profile": {"ter": _from(a.code)}}], user_id=user_id)

    assert body.committed is True and body.issues == [], f"saved: {_issues(body)}"
    assert old not in a.identifiers_read() and new in a.identifiers_read(), f"the binding the item sets is read, never the one it replaces: {a.calls}"
    assert _by_key(await _rows(engine, asset_id)) == {"ter": ("0.003", a.code, None, LAB_DATE)}, "the new binding's value"
    assert await _config(engine, asset_id) == {a.code: _entry(new)}, "the new binding is saved"


async def test_from_a_code_the_same_item_removes_is_refused(engine, lab) -> None:
    user_id = await _user(engine)
    identifier, other = _ident("RM"), _ident("RMO")
    a = lab("removed", {identifier: {"ter": TER}})
    b = lab("removed_other", {other: {"ter": TER_OTHER}})
    asset_id = await _asset(engine, "RM", {a.code: _entry(identifier)})
    await _commit_from(engine, asset_id, a.code, user_id=user_id)
    before = await _rows(engine, asset_id)

    body = await _patch(engine, [{"asset_id": asset_id, "enrichers": {b.code: _entry(other)}, "profile": {"ter": _from(a.code), "description": "Not saved"}}], user_id=user_id)

    assert body.committed is False and _issues(body) == [(asset_id, 0, PROFILE_VALUE_INVALID, "profile.ter")], f"after the item the asset has no binding to {a.code}: {_issues(body)}"
    assert await _rows(engine, asset_id) == before, "nothing of the item written"
    assert await _config(engine, asset_id) == {a.code: _entry(identifier)}, "the bindings unchanged"


# =============================================================================
# 4. Refusals: profileValueInvalid on profile.<voice>, the whole batch refused, the dry run the same
# =============================================================================

#: kind, what the target lab answers for its binding, whether the asset is bound to it, whether it is installed, whether
#: the refusal comes from a read of it
_REFUSALS = [
    pytest.param("not_bound", {"ter": TER}, False, True, False, id="code-not-among-the-enrichers"),
    pytest.param("not_installed", None, True, False, False, id="enricher-not-installed"),
    pytest.param("no_value", {"description": "No ter here"}, True, True, True, id="no-value-for-the-voice"),
    pytest.param("not_found", NOT_FOUND, True, True, True, id="asset-not-found"),
    pytest.param("error", ERROR, True, True, True, id="enricher-fails"),
    pytest.param("raise", RAISE, True, True, True, id="enricher-raises"),
]


@pytest.mark.parametrize(("kind", "answer", "bound", "installed", "read"), _REFUSALS)
async def test_a_from_that_cannot_be_resolved_refuses_the_whole_batch(engine, lab, kind, answer, bound, installed, read) -> None:
    print_section(f"B5b: {{'from'}} refused ({kind})")
    user_id = await _user(engine)
    good_id, target_id = _ident("GOOD"), _ident("TGT")
    good = lab(f"good_{kind}", {good_id: {"ter": TER, "description": "Lab good"}})
    target = lab(f"target_{kind}", {target_id: answer}) if installed else None
    target_code = target.code if target is not None else ABSENT_CODE
    config = {good.code: _entry(good_id), **({target_code: _entry(target_id)} if bound else {})}
    asset_id = await _asset(engine, f"REF_{kind}", config)
    neighbour_id = await _asset(engine, f"NEI_{kind}", {good.code: _entry(good_id)})
    await _commit_from(engine, asset_id, good.code, user_id=user_id)
    neighbour_name = await _name(engine, neighbour_id)
    before = {asset: await _rows(engine, asset) for asset in (asset_id, neighbour_id)}
    items = [
        {"asset_id": neighbour_id, "display_name": f"{neighbour_name} renamed", "profile": {"description": "Not saved either"}},
        {"asset_id": asset_id, "profile": {"ter": _from(target_code), "description": "Not saved"}},
    ]

    for commit in (False, True):
        body = await _patch(engine, items, user_id=user_id, commit=commit)

        assert body.committed is False, f"commit={commit}: refused: {_issues(body)}"
        assert _issues(body) == [(asset_id, 1, PROFILE_VALUE_INVALID, "profile.ter")], f"commit={commit}: one issue on profile.ter of the item: {_issues(body)}"
        assert [result.success for result in body.results] == [False, False], f"commit={commit}: nothing of the batch saved: {body.results}"
        assert {asset: await _rows(engine, asset) for asset in (asset_id, neighbour_id)} == before, f"commit={commit}: no row written"
        assert await _name(engine, neighbour_id) == neighbour_name, f"commit={commit}: the other item not saved"
    if target is not None:
        read_ids = target.identifiers_read()
        assert (target_id in read_ids) if read else (read_ids == []), f"the binding is read only when the refusal depends on the answer: {target.calls}"
    print_success(f"{kind}: refused, nothing saved")


async def test_a_from_with_other_keys_is_not_a_from(engine, lab) -> None:
    user_id = await _user(engine)
    identifier = _ident("KEYS")
    a = lab("keys", {identifier: {"ter": TER}})
    asset_id = await _asset(engine, "KEYS", {a.code: _entry(identifier)})
    await _commit_from(engine, asset_id, a.code, user_id=user_id)
    before = await _rows(engine, asset_id)

    body = await _patch(engine, [{"asset_id": asset_id, "profile": {"ter": {"from": a.code, "seen": TER, "note": "extra"}}}], user_id=user_id)

    assert _issues(body) == [(asset_id, 0, PROFILE_VALUE_INVALID, "profile.ter")] and body.committed is False, f"only from and seen: {_issues(body)}"
    assert await _rows(engine, asset_id) == before, "nothing written"


# =============================================================================
# 5. seen: compared in stored form, a warning when the source changed
# =============================================================================

_SEEN = [
    pytest.param("ter", {"seen": "0.0030"}, True, id="ter-different"),
    pytest.param("ter", {"seen": "0.00220"}, False, id="ter-equal-other-spelling"),
    pytest.param("ter", {}, False, id="ter-no-seen"),
    pytest.param("geography", {"seen": {"JPN": "0.40", "USA": "0.6000"}}, False, id="geography-equal-other-form"),
    pytest.param("geography", {"seen": {"USA": "1"}}, True, id="geography-different"),
]


@pytest.mark.parametrize(("voice", "seen", "changed"), _SEEN)
async def test_seen_is_compared_in_stored_form_and_the_value_read_now_is_saved(engine, lab, voice, seen, changed) -> None:
    print_section(f"B5b: seen ({voice}, changed={changed})")
    user_id = await _user(engine)
    identifier = _ident("SEEN")
    a = lab(f"seen_{voice}_{int(changed)}_{len(seen)}", {identifier: {"ter": TER, "geography": RAW_GEOGRAPHY}})
    asset_id = await _asset(engine, "SEEN", {a.code: _entry(identifier)})
    now = normalize_value(voice, {"ter": TER, "geography": RAW_GEOGRAPHY}[voice])
    expected = [(asset_id, 0, PROFILE_SOURCE_CHANGED, f"profile.{voice}", {"voice": voice, "seen": normalize_value(voice, seen["seen"]), "now": now})] if changed else []

    body = await _patch(engine, [{"asset_id": asset_id, "profile": {voice: _from(a.code, **seen)}}], user_id=user_id)

    assert body.committed is True and body.issues == [], f"a changed source never blocks: {_issues(body)}"
    assert _warnings(body) == expected, f"the warning only when the value read now differs from seen, both in stored form: {_warnings(body)}"
    assert _by_key(await _rows(engine, asset_id)) == {voice: (now, a.code, None, LAB_DATE)}, "the value read now is saved"


async def test_the_dry_run_answers_the_same_warning_and_writes_nothing(engine, lab) -> None:
    user_id = await _user(engine)
    identifier = _ident("DRY")
    a = lab("dry", {identifier: {"ter": TER}})
    asset_id = await _asset(engine, "DRY", {a.code: _entry(identifier)})
    items = [{"asset_id": asset_id, "profile": {"ter": _from(a.code, seen="0.0030")}}]
    expected = [(asset_id, 0, PROFILE_SOURCE_CHANGED, "profile.ter", {"voice": "ter", "seen": "0.003", "now": TER})]

    dry = await _patch(engine, items, user_id=user_id, commit=False)

    assert dry.committed is False and dry.issues == [] and [result.success for result in dry.results] == [True], f"the dry run would save: {_issues(dry)} {dry.results}"
    assert _warnings(dry) == expected, f"the dry run's warning: {_warnings(dry)}"
    assert await _rows(engine, asset_id) == [], "the dry run writes nothing"

    saved = await _patch(engine, items, user_id=user_id)

    assert saved.committed is True and _warnings(saved) == expected, f"the save answers the same: {_issues(saved)} {_warnings(saved)}"
    assert _by_key(await _rows(engine, asset_id)) == {"ter": (TER, a.code, None, LAB_DATE)}, "barrier: the same items do write once committed"


# =============================================================================
# 6. POST /assets
# =============================================================================


async def test_post_takes_a_from_with_the_items_enrichers_and_a_refused_one_fails_its_item(engine, lab) -> None:
    print_section("B5b: {'from'} on POST")
    user_id = await _user(engine)
    good, missing = _ident("PGOOD"), _ident("PNF")
    a = lab("post", {good: {"ter": TER, "description": "Lab post"}, missing: NOT_FOUND})
    tag = uuid.uuid4().hex[:8]
    items = [
        {"display_name": f"Lab from POST ok {tag}", "currency": "EUR", "asset_type": "ETF", "enrichers": {a.code: _entry(good)}, "profile": {"ter": _from(a.code), "description": "By hand"}},
        {"display_name": f"Lab from POST not found {tag}", "currency": "EUR", "asset_type": "ETF", "enrichers": {a.code: _entry(missing)}, "profile": {"ter": _from(a.code)}},
        {"display_name": f"Lab from POST not bound {tag}", "currency": "EUR", "asset_type": "ETF", "profile": {"ter": _from(a.code)}},
    ]

    body = await _create(engine, items, user_id=user_id)

    assert [result.success for result in body.results] == [True, False, False], f"the first created, the two refused «from» fail their item: {body.results}"
    created = body.results[0].asset_id
    assert created is not None and _by_key(await _rows(engine, created)) == {"ter": (TER, a.code, None, LAB_DATE), "description": ("By hand", "user", user_id, None)}, "the «from» in the source's name, the other voice by hand"
    for item in items[1:]:
        assert await _asset_id_named(engine, item["display_name"]) is None, f"a refused item creates no asset: {item['display_name']}"
    assert missing in a.identifiers_read(), f"the not-found binding was read: {a.calls}"


async def test_a_batch_rolled_back_writes_no_profile_row(engine) -> None:
    """Item 0 writes a description by hand; item 1 empties its asset's name, which the checks let through and the flush
    refuses (NOT NULL): ``patchFailed`` on item 1, the batch rolled back, and neither asset gets a profile row. Barrier:
    item 0 alone commits and writes its row."""
    print_section("D7a: a batch rolled back writes no profile row")
    author = await _user(engine)
    sound = await _asset(engine, "rollback-sound")
    other = await _asset(engine, "rollback-other")

    alone = await _patch(engine, [{"asset_id": sound, "profile": {"description": "Written by hand"}}], user_id=author)
    after_alone = await _rows(engine, sound)
    assert alone.committed and [(row["key"], row["source"]) for row in after_alone] == [("description", "user")], f"barrier: item 0 alone writes its row: {after_alone}"

    batch = await _patch(engine, [{"asset_id": sound, "profile": {"description": "Written again"}}, {"asset_id": other, "display_name": "", "profile": {"description": "Never saved"}}], user_id=author)

    assert batch.committed is False and [(issue.asset_id, issue.index, str(issue.code)) for issue in batch.issues] == [(other, 1, "patchFailed")], f"the batch is rolled back on item 1: {batch.issues}"
    assert _new(after_alone, await _rows(engine, sound)) == [], "a rolled-back batch writes no profile row for item 0"
    assert await _rows(engine, other) == [], "nor for item 1"
    print_success("a batch rolled back on patchFailed writes no profile row")
