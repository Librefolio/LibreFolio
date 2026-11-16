"""Reading the profile from the enrichers, and merging it (plan 68, B5; §3.5, §3.7).

**Read.** ``read_bindings`` groups the bindings by enricher and runs the enrichers at once, each in a worker thread
(``plugin.read`` blocks and paces its own calls); the outcomes come out as the plugins yield them. A binding the plugin
never answers (it stopped early, raised, gave an index out of the list) comes out as an ``error``: nothing stays pending.

**Filter.** Every value a plugin gives passes the catalogue before anything else (``catalogue.normalize_value``): a voice
it refuses, an unknown voice, or a ``None`` (a source never empties a voice) is dropped and logged, and the plugin's
other voices go on. Values come out in their stored form.

**Cache** (``enricher_read``, 30 minutes, like «Chiedi al Provider»): the key is the enricher and the whole binding,
parameters included; the entry keeps which voices were read (``None``: all), so a partial read never answers a request
for more. Only ``ok`` and ``not_found`` are kept: an error or a refusal for too many requests never is.

**Merge.** For an asset, voice by voice, the first enricher of its order (the priority of ``config``) whose read gave the
voice wins; an enricher down leaves the voice to the next one. The others' values are kept beside it (``ask``).

**Ask** reads (from the cache when it can) and writes nothing; it works before the asset exists. **Refresh** reads the
assets' bindings, then — the reads all done, never under the write lock — writes each asset in its own transaction: the
merged voices through the store (``source`` the enricher, its ``source_date``) and the ``state`` of each enricher read
(``read_at`` UTC, ``status``, ``error_code``, ``retry_after``, ``voices``). The ``config`` is read again when writing: a
binding the user removed meanwhile writes nothing, and the merge follows the order of now.

This module holds the TTL cache, whose library starts a thread at import: import it lazily from modules in the import
chain of the BRIM parse pool's forkserver preload (``services/assets/crud.py``).

**The source's value** (``source_value``): what one enricher gives for one voice, from the cache or a read of that voice,
for the user's «use the source's value» (``{"from": …}``). **The read after a save** (``refresh_in_background``):
«Aggiorna» after a save that set the enrichers, after the answer, with a session of its own.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
from collections.abc import AsyncIterator, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.app.db.models import Asset, AssetType
from backend.app.db.session import get_async_engine
from backend.app.logging_config import get_logger
from backend.app.services.assets.profile.catalogue import ProfileValueError, normalize_value
from backend.app.services.assets.profile.store import ProfileWrite, profile_today, write_values
from backend.app.services.enrichers.base import RATE_LIMITED, EnricherBinding, EnricherPlugin, EnricherReadItem, EnricherReadStatus
from backend.app.services.enrichers.bindings import load_enrichers, update_state
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.app.utils.runtime.cache import get_ttl_cache

#: How long a read stays in the cache, in seconds (as ``asset_metadata_fetch``).
READ_CACHE_TTL = 1800


@dataclass(frozen=True, slots=True)
class ReadRequest:
    """One binding to read: whose it is (``owner``, an asset id or any key of the caller), which enricher, which binding."""

    owner: Hashable
    code: str
    binding: EnricherBinding


@dataclass(frozen=True, slots=True)
class ReadOutcome:
    """The outcome of one ``ReadRequest``: the values in stored form, filtered by the catalogue."""

    owner: Hashable
    code: str
    binding: EnricherBinding
    status: EnricherReadStatus
    values: Mapping[str, Any] = field(default_factory=dict)
    source_date: date | None = None
    error_code: str | None = None
    error_message: str | None = None
    retry_after: float | None = None
    from_cache: bool = False


@dataclass(frozen=True, slots=True)
class MergedVoice:
    """One voice of an asset after the merge: the winning value and enricher, and what the others gave."""

    value: Any
    source: str
    source_date: date | None
    others: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AskResult:
    """What ``ask_profile`` answers: the merged voices and every enricher's outcome."""

    voices: dict[str, MergedVoice]
    outcomes: list[ReadOutcome]


@dataclass(frozen=True, slots=True)
class AssetRefreshResult:
    """What ``refresh_assets`` did for one asset: the voices written, every enricher's outcome, the reads deferred
    (``RATE_LIMITED``, for the scheduler's second round), or why nothing was read (``error``)."""

    asset_id: int
    written: list[str] = field(default_factory=list)
    outcomes: list[ReadOutcome] = field(default_factory=list)
    deferred: list[ReadOutcome] = field(default_factory=list)
    error: str | None = None


_read_cache = get_ttl_cache("enricher_read", maxsize=2000, ttl=READ_CACHE_TTL)
logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _Cached:
    """A cached read: its outcome (``ok`` or ``not_found``) and the voices asked (``None``: all)."""

    outcome: ReadOutcome
    keys: frozenset[str] | None


def _cache_key(code: str, binding: EnricherBinding) -> tuple[str, str, str, str]:
    params = json.dumps(dict(binding.params), sort_keys=True, default=str)
    return (code, binding.identifier_type, binding.identifier, params)


def _cached(code: str, binding: EnricherBinding, keys: frozenset[str] | None) -> ReadOutcome | None:
    """The cached outcome that answers a read of ``keys``: one read for all voices answers any; one for some answers a
    subset of them only."""
    entry, hit = _read_cache.get(_cache_key(code, binding))
    if not hit or not isinstance(entry, _Cached):
        return None
    if entry.keys is not None and (keys is None or not keys <= entry.keys):
        return None
    return entry.outcome


def _stored_values(code: str, values: Mapping[str, Any]) -> dict[str, Any]:
    """The plugin's values that the catalogue accepts, in stored form; the others dropped and logged."""
    stored: dict[str, Any] = {}
    for key, raw in values.items():
        if raw is None:
            logger.warning("Enricher gave an empty value: dropped, a source never empties a voice", enricher=code, voice=key)
            continue
        try:
            stored[key] = normalize_value(key, raw)
        except ProfileValueError as error:
            logger.warning("Enricher value refused by the profile catalogue: dropped", enricher=code, voice=key, reason=error.reason)
    return stored


def _outcome(request: ReadRequest, item: EnricherReadItem) -> ReadOutcome:
    values = _stored_values(request.code, item.values) if item.status is EnricherReadStatus.OK else {}
    return ReadOutcome(
        owner=request.owner,
        code=request.code,
        binding=request.binding,
        status=item.status,
        values=values,
        source_date=item.source_date,
        error_code=item.error_code,
        error_message=item.error_message,
        retry_after=item.retry_after,
    )


def _unanswered(request: ReadRequest, message: str) -> ReadOutcome:
    return ReadOutcome(owner=request.owner, code=request.code, binding=request.binding, status=EnricherReadStatus.ERROR, error_code="NO_ANSWER", error_message=message)


def _drain(plugin: EnricherPlugin, bindings: list[EnricherBinding], keys: frozenset[str] | None, put: Any) -> None:
    """Run one plugin's ``read`` in this worker thread, handing each item to the loop as it comes, then the end."""
    try:
        for item in plugin.read(bindings, None if keys is None else sorted(keys)):
            put(("item", item))
    except Exception as error:  # noqa: BLE001 — isolation boundary: a plugin that fails leaves its bindings in error
        logger.warning("Enricher read failed", enricher=plugin.code, exc_info=error)
        put(("crash", error))
    finally:
        put(("end", None))


async def _read_plugin(plugin: EnricherPlugin, requests: list[ReadRequest], keys: frozenset[str] | None, out: asyncio.Queue) -> None:
    """One plugin's read: its outcomes onto ``out`` as they come, then one ``error`` for every binding it never answered."""
    loop = asyncio.get_running_loop()
    inbox: asyncio.Queue = asyncio.Queue()
    worker = asyncio.create_task(asyncio.to_thread(_drain, plugin, [request.binding for request in requests], keys, lambda message: loop.call_soon_threadsafe(inbox.put_nowait, message)))
    answered: set[int] = set()
    crashed: str | None = None
    while True:
        kind, payload = await inbox.get()
        if kind == "end":
            break
        if kind == "crash":
            crashed = f"{type(payload).__name__}: {payload}"
            continue
        index = getattr(payload, "index", None)
        if not isinstance(index, int) or not 0 <= index < len(requests) or index in answered:
            logger.warning("Enricher answered an index it was not given, or twice: ignored", enricher=plugin.code, index=index)
            continue
        answered.add(index)
        outcome = _outcome(requests[index], payload)
        if outcome.status in (EnricherReadStatus.OK, EnricherReadStatus.NOT_FOUND):
            _read_cache.set(_cache_key(plugin.code, requests[index].binding), _Cached(outcome=outcome, keys=keys))
        await out.put(outcome)
    await worker
    for index, request in enumerate(requests):
        if index not in answered:
            await out.put(_unanswered(request, crashed or "the enricher gave no answer for this binding"))


async def read_bindings(requests: Sequence[ReadRequest], keys: Iterable[str] | None = None, *, use_cache: bool = True) -> AsyncIterator[ReadOutcome]:
    """Read every binding, the enrichers at once; the outcomes as they come."""
    wanted = None if keys is None else frozenset(keys)
    to_read: dict[str, list[ReadRequest]] = {}
    for request in requests:
        cached = _cached(request.code, request.binding, wanted) if use_cache else None
        if cached is not None:
            yield dataclasses.replace(cached, owner=request.owner, from_cache=True)
            continue
        to_read.setdefault(request.code, []).append(request)
    out: asyncio.Queue = asyncio.Queue()
    pending = 0
    tasks: list[asyncio.Task] = []
    for code, group in to_read.items():
        plugin = EnricherRegistry.get_plugin_instance(code) if EnricherRegistry.get_plugin(code) is not None else None
        if plugin is None:
            for request in group:
                yield _unanswered(request, "no such enricher")
            continue
        pending += len(group)
        tasks.append(asyncio.create_task(_read_plugin(plugin, group, wanted, out)))
    try:
        for _ in range(pending):
            yield await out.get()
    finally:
        for task in tasks:
            task.cancel()


def merge_voices(order: Sequence[str], outcomes: Iterable[ReadOutcome]) -> dict[str, MergedVoice]:
    """Voice by voice, the first enricher of ``order`` whose ``ok`` outcome gave it wins."""
    by_code = {outcome.code: outcome for outcome in outcomes if outcome.status is EnricherReadStatus.OK}
    merged: dict[str, MergedVoice] = {}
    for code in order:
        outcome = by_code.get(code)
        if outcome is None:
            continue
        for key, value in outcome.values.items():
            if key in merged:
                merged[key].others[code] = value  # type: ignore[index] — the dict built just below
            else:
                merged[key] = MergedVoice(value=value, source=code, source_date=outcome.source_date, others={})
    return merged


def _requests(owner: Hashable, config: Mapping[str, Mapping[str, Any]]) -> list[ReadRequest]:
    """The read requests of one asset's bindings."""
    requests = []
    for code, raw in config.items():
        params = {key: value for key, value in raw.items() if key not in ("identifier_type", "identifier")}
        requests.append(ReadRequest(owner=owner, code=code, binding=EnricherBinding(identifier_type=str(raw.get("identifier_type", "")), identifier=str(raw.get("identifier", "")), params=params)))
    return requests


async def ask_profile(asset_type: AssetType, config: Mapping[str, Mapping[str, Any]], keys: Iterable[str] | None = None) -> AskResult:
    """Read ``config`` (code → binding, in its order) for an asset of ``asset_type`` and merge, writing nothing."""
    del asset_type  # the merge follows the asset's order; the type serves the frontend's choice of voices
    wanted = None if keys is None else set(keys)
    outcomes = [outcome async for outcome in read_bindings(_requests(0, config), wanted)]
    voices = merge_voices(list(config), outcomes)
    if wanted is not None:
        # A plugin that reads a whole page may give more than asked: the answer holds the voices asked only
        voices = {key: voice for key, voice in voices.items() if key in wanted}
    return AskResult(voices=voices, outcomes=outcomes)


def _state_entry(outcome: ReadOutcome, read_at: datetime) -> dict[str, Any]:
    return {"read_at": read_at.isoformat(), "status": outcome.status.value, "error_code": outcome.error_code, "retry_after": outcome.retry_after, "voices": len(outcome.values)}


def _already_read(entry: Any, since: datetime) -> bool:
    """Whether a ``state`` entry says the binding was read (ok or not found) at or after ``since``."""
    if not isinstance(entry, Mapping) or entry.get("status") not in ("ok", "not_found"):
        return False
    try:
        read_at = ensure_utc(datetime.fromisoformat(str(entry.get("read_at"))))
    except ValueError:
        return False
    return read_at is not None and read_at >= ensure_utc(since)


async def refresh_assets(session: AsyncSession, asset_ids: Sequence[int], *, keys: Iterable[str] | None = None, now: datetime | None = None, read_since: datetime | None = None) -> list[AssetRefreshResult]:
    """Read and save the profile of those assets, each in its own transaction (committed here).

    ``read_since`` skips the bindings whose ``state`` says they were read (``ok`` or ``not_found``) at or after it: the
    scheduler's second round after a refusal (B6).
    """
    ids = list(dict.fromkeys(asset_ids))
    existing = set((await session.execute(select(Asset.id).where(Asset.id.in_(ids)))).scalars().all()) if ids else set()
    rows = await load_enrichers(session, ids)
    await session.commit()  # nothing held while the enrichers are read
    requests: list[ReadRequest] = []
    for asset_id in ids:
        row = rows.get(asset_id)
        if asset_id not in existing or row is None:
            continue
        for request in _requests(asset_id, row.config):
            if EnricherRegistry.get_plugin(request.code) is None:
                continue  # an enricher not installed (or turned off): its binding stays, the read skips it
            if read_since is not None and _already_read(row.state.get(request.code), read_since):
                continue
            requests.append(request)
    outcomes: dict[int, list[ReadOutcome]] = {}
    async for outcome in read_bindings(requests, keys):
        outcomes.setdefault(outcome.owner, []).append(outcome)
    read_at = now or utcnow()
    results = []
    for asset_id in ids:
        if asset_id not in existing:
            results.append(AssetRefreshResult(asset_id=asset_id, error="asset not found"))
            continue
        results.append(await _save_asset(session, asset_id, outcomes.get(asset_id, []), read_at))
    return results


async def _save_asset(session: AsyncSession, asset_id: int, outcomes: list[ReadOutcome], read_at: datetime) -> AssetRefreshResult:
    """Write one asset's merged voices and its enrichers' state, in one transaction, against its ``config`` of now."""
    try:
        config = (await load_enrichers(session, [asset_id])).get(asset_id)
        order = list(config.config) if config is not None else []
        kept = [outcome for outcome in outcomes if outcome.code in order]
        merged = merge_voices(order, kept)
        writes = [ProfileWrite(key=key, value=voice.value, source=voice.source, source_date=voice.source_date) for key, voice in merged.items()]
        written = await write_values(session, asset_id, writes, today=await profile_today(session, read_at)) if writes else []
        if kept:
            await update_state(session, asset_id, {outcome.code: _state_entry(outcome, read_at) for outcome in kept})
        await session.commit()
    except Exception as error:  # noqa: BLE001 — isolation boundary: one asset that cannot be saved never stops the others
        await session.rollback()
        logger.warning("Profile refresh of an asset failed: nothing saved for it", asset_id=asset_id, exc_info=error)
        return AssetRefreshResult(asset_id=asset_id, outcomes=outcomes, error=type(error).__name__)
    deferred = [outcome for outcome in kept if outcome.error_code == RATE_LIMITED]
    return AssetRefreshResult(asset_id=asset_id, written=[row.key for row in written], outcomes=kept, deferred=deferred)


# =============================================================================
# THE SOURCE'S VALUE, AND THE READ AFTER A SAVE
# =============================================================================


@dataclass(frozen=True, slots=True)
class SourceValue:
    """What an enricher gives now for one voice of one binding: the value in stored form and its ``source_date``."""

    value: Any
    source_date: date | None


async def source_value(code: str, binding: Mapping[str, Any], key: str) -> SourceValue | str:
    """The value ``code`` gives for ``key`` with ``binding`` (the cache when it holds it, else a read of that voice); the
    reason as text when it gives none (not an installed enricher, not found, an error, the voice not given)."""
    if EnricherRegistry.get_plugin(code) is None:
        return f"'{code}' is not an installed enricher"
    request = _requests(0, {code: binding})[0]
    outcomes = [outcome async for outcome in read_bindings([request], {key})]
    outcome = outcomes[-1] if outcomes else None
    if outcome is None or outcome.status is not EnricherReadStatus.OK:
        return f"'{code}' gave no value ({'no answer' if outcome is None else outcome.status.value})"
    if key not in outcome.values:
        return f"'{code}' gives no value for '{key}'"
    return SourceValue(value=outcome.values[key], source_date=outcome.source_date)


async def refresh_in_background(asset_ids: Sequence[int], *, engine: AsyncEngine | None = None) -> None:
    """«Aggiorna» after a save that set the enrichers (plan §3.5), run after the answer with a session of its own. Never
    raises: a failure is logged, and the weekly read or «Aggiorna» reads the asset later (its ``state`` says «never»)."""
    if not asset_ids:
        return
    try:
        async with AsyncSession(engine or get_async_engine(), expire_on_commit=False) as session:
            await refresh_assets(session, asset_ids)
    except Exception as error:  # noqa: BLE001 — a background task has nobody to raise to: log and end
        logger.warning("Profile read after a save failed", asset_ids=list(asset_ids), exc_info=error)
