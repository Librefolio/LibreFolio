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
(``read_at`` UTC, ``status``, ``error_code``, ``retry_after``, ``voices``, and ``confirmed``: voice → the moment of
the last read that gave it, kept across failed and partial reads, D1d). The ``config`` is read again when writing: a
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
from backend.app.services.enrichers.bindings import CONFIRMED_FIELD, load_enrichers, update_state
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.enrichers.usable import NOT_CONFIGURED, configured_enricher, usable_codes
from backend.app.services.platform import call_counter
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
    #: The day of a voice that has one of its own; a voice not in it takes ``source_date``.
    source_dates: Mapping[str, date] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    retry_after: float | None = None
    from_cache: bool = False

    def date_of(self, key: str) -> date | None:
        """The source date of voice ``key``: its own, else the read's."""
        return self.source_dates.get(key, self.source_date)


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
    (``RATE_LIMITED``, for the scheduler's second round), or why nothing was read (``error``). ``enrichers_read`` counts
    the enrichers this round read for it (a cached read included): zero when every one bound is turned off, not
    installed or not configured (E6c2, PROF 19/11: «Aggiorna» says so; the weekly job still skips them silently)."""

    asset_id: int
    written: list[str] = field(default_factory=list)
    outcomes: list[ReadOutcome] = field(default_factory=list)
    deferred: list[ReadOutcome] = field(default_factory=list)
    error: str | None = None
    enrichers_read: int = 0


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
        source_dates={key: day for key, day in item.source_dates.items() if key in values},
        error_code=item.error_code,
        error_message=item.error_message,
        retry_after=item.retry_after,
    )


def _unanswered(request: ReadRequest, message: str) -> ReadOutcome:
    return ReadOutcome(owner=request.owner, code=request.code, binding=request.binding, status=EnricherReadStatus.ERROR, error_code="NO_ANSWER", error_message=message)


def _not_configured(request: ReadRequest, missing: Sequence[str]) -> ReadOutcome:
    return ReadOutcome(
        owner=request.owner,
        code=request.code,
        binding=request.binding,
        status=EnricherReadStatus.ERROR,
        error_code=NOT_CONFIGURED,
        error_message=f"not configured: {', '.join(missing)} missing",
    )


def _split_cached(requests: list[ReadRequest], keys: frozenset[str] | None, use_cache: bool) -> tuple[list[ReadOutcome], list[ReadRequest]]:
    """The outcomes the read cache answers, and the requests left to read."""
    served: list[ReadOutcome] = []
    to_read: list[ReadRequest] = []
    for request in requests:
        cached = _cached(request.code, request.binding, keys) if use_cache else None
        if cached is not None:
            served.append(dataclasses.replace(cached, owner=request.owner, from_cache=True))
        else:
            to_read.append(request)
    return served, to_read


def _limit_refused(request: ReadRequest, full: call_counter.CallLimitReached) -> ReadOutcome:
    """A binding not read because the plugin's call limit is full: a refusal for too many requests, never cached."""
    return ReadOutcome(
        owner=request.owner,
        code=request.code,
        binding=request.binding,
        status=EnricherReadStatus.ERROR,
        error_code=RATE_LIMITED,
        error_message=f"Enricher {request.code} reached its {full.window} call limit ({full.limit})",
        retry_after=full.retry_after,
    )


async def _within_call_limit(plugin: EnricherPlugin, requests: list[ReadRequest]) -> tuple[list[ReadRequest], list[ReadOutcome]]:
    """The bindings a plugin that calls out may read now, and the refusals of the others (project 76, K1).

    One call counted per binding, in request order, before the read, on the plugin's row or on its credit-sharing
    group's (``call_counter.call_owner``). A full window refuses that binding and every following one; a counter that
    fails (None) lets them go. A plugin that calls nothing out is never counted.
    """
    if not getattr(plugin, "calls_external_service", False):
        return requests, []
    family, owner, limits = call_counter.call_owner(plugin, "enricher")
    for index in range(len(requests)):
        try:
            await call_counter.count_and_check(family, owner, limits)
        except call_counter.CallLimitReached as full:
            refused = requests[index:]
            logger.warning("Enricher read refused: instance call limit reached", enricher=plugin.code, owner=f"{family}/{owner}", window=full.window, limit=full.limit, refused=len(refused), retry_after_s=round(full.retry_after, 1))
            return requests[:index], [_limit_refused(item, full) for item in refused]
    return requests, []


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
    """Read every binding, the enrichers at once; the outcomes as they come.

    An enricher the registry does not serve (not installed, turned off) answers «no answer», and one with a required
    setting left empty «not configured», before the read cache: a value read before the switch is not served after it.
    A plugin that calls an external service has each binding it reads counted first, and a full call limit refuses
    the rest (``_within_call_limit``); a cached binding is never counted.
    """
    wanted = None if keys is None else frozenset(keys)
    by_code: dict[str, list[ReadRequest]] = {}
    for request in requests:
        by_code.setdefault(request.code, []).append(request)
    out: asyncio.Queue = asyncio.Queue()
    pending = 0
    tasks: list[asyncio.Task] = []
    for code, group in by_code.items():
        plugin, missing = await configured_enricher(code)
        if plugin is None or missing:
            for request in group:
                yield _unanswered(request, "no such enricher") if plugin is None else _not_configured(request, missing)
            continue
        served, to_read = _split_cached(group, wanted, use_cache)
        to_read, refused = await _within_call_limit(plugin, to_read)
        for outcome in (*served, *refused):
            yield outcome
        if to_read:
            pending += len(to_read)
            tasks.append(asyncio.create_task(_read_plugin(plugin, to_read, wanted, out)))
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
                merged[key] = MergedVoice(value=value, source=code, source_date=outcome.date_of(key), others={})
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
    """The ``state`` of one read; ``confirmed`` the voices it gave, at ``read_at``. A voice held for the second round is
    confirmed too: the source gave it, and the retry never reads that source again (D1d)."""
    given = sorted(outcome.values) if outcome.status is EnricherReadStatus.OK else []
    return {
        "read_at": read_at.isoformat(),
        "status": outcome.status.value,
        "error_code": outcome.error_code,
        "retry_after": outcome.retry_after,
        "voices": len(outcome.values),
        CONFIRMED_FIELD: dict.fromkeys(given, read_at.isoformat()),
    }


def _already_read(entry: Any, since: datetime) -> bool:
    """Whether a ``state`` entry says the binding was read (ok or not found) at or after ``since``."""
    if not isinstance(entry, Mapping) or entry.get("status") not in ("ok", "not_found"):
        return False
    try:
        read_at = ensure_utc(datetime.fromisoformat(str(entry.get("read_at"))))
    except ValueError:
        return False
    return read_at is not None and read_at >= ensure_utc(since)


async def _usable_bound(rows: Mapping[int, Any]) -> set[str]:
    """The bound enrichers that can be used now; the others are named in ONE log line for the whole run (not one per
    asset): their bindings stay, the reads skip them."""
    bound = {code for row in rows.values() for code in row.config}
    usable = await usable_codes(bound)
    if skipped := sorted(bound - usable):
        logger.info("Profile read skips enrichers not active or not configured", enrichers=skipped)
    return usable


async def refresh_assets(
    session: AsyncSession,
    asset_ids: Sequence[int],
    *,
    keys: Iterable[str] | None = None,
    now: datetime | None = None,
    read_since: datetime | None = None,
    hold_deferred: bool = False,
) -> list[AssetRefreshResult]:
    """Read and save the profile of those assets, each in its own transaction (committed here).

    ``read_since`` skips the bindings whose ``state`` says they were read (``ok`` or ``not_found``) at or after it: the
    scheduler's second round after a refusal (B6); their values still join the merge, from the read cache.
    ``hold_deferred`` (the scheduler's first round, consultant 16/11): where an enricher refused for too many requests,
    the voices it declares for the asset's type whose winner comes after it in the asset's order are not written yet.
    """
    ids = list(dict.fromkeys(asset_ids))
    asset_types = dict((await session.execute(select(Asset.id, Asset.asset_type).where(Asset.id.in_(ids)))).all()) if ids else {}
    rows = await load_enrichers(session, ids)
    await session.commit()  # nothing held while the enrichers are read
    wanted = None if keys is None else frozenset(keys)
    requests: list[ReadRequest] = []
    carried: dict[int, list[ReadOutcome]] = {}
    usable = await _usable_bound(rows)
    for asset_id in ids:
        row = rows.get(asset_id)
        if asset_id not in asset_types or row is None:
            continue
        for request in _requests(asset_id, row.config):
            if request.code not in usable:
                continue  # not installed, turned off, or not configured: its binding and state stay, the read skips it
            if read_since is not None and _already_read(row.state.get(request.code), read_since):
                # Read in this round already: not read again, its values join the merge from the cache
                if (cached := _cached(request.code, request.binding, wanted)) is not None:
                    carried.setdefault(asset_id, []).append(dataclasses.replace(cached, owner=asset_id, from_cache=True))
                continue
            requests.append(request)
    outcomes: dict[int, list[ReadOutcome]] = {}
    async for outcome in read_bindings(requests, wanted):
        outcomes.setdefault(outcome.owner, []).append(outcome)
    read_at = now or utcnow()
    results = []
    for asset_id in ids:
        if asset_id not in asset_types:
            results.append(AssetRefreshResult(asset_id=asset_id, error="asset not found"))
            continue
        hold_for = AssetType(asset_types[asset_id]) if hold_deferred else None
        results.append(await _save_asset(session, asset_id, outcomes.get(asset_id, []), carried.get(asset_id, []), read_at, hold_for))
    return results


def _held_voices(order: Sequence[str], merged: Mapping[str, MergedVoice], deferred: Sequence[str], asset_type: AssetType) -> set[str]:
    """The voices to hold for the second round: those a refused enricher declares for ``asset_type`` whose winner comes
    after it in ``order``."""
    held: set[str] = set()
    for code in deferred:
        plugin = EnricherRegistry.get_plugin(code)
        declared = plugin.voices.get(asset_type, frozenset()) if plugin is not None else frozenset()
        rank = order.index(code)
        held.update(key for key, voice in merged.items() if key in declared and order.index(voice.source) > rank)
    return held


async def _save_asset(session: AsyncSession, asset_id: int, outcomes: list[ReadOutcome], carried: list[ReadOutcome], read_at: datetime, hold_for: AssetType | None) -> AssetRefreshResult:
    """Write one asset's merged voices and its enrichers' state, in one transaction, against its ``config`` of now.

    ``carried`` are the cached reads of the bindings this round skipped: they join the merge, their ``state`` stays.
    ``hold_for`` (the asset's type) holds the voices of a refused enricher for the second round.
    """
    try:
        config = (await load_enrichers(session, [asset_id])).get(asset_id)
        order = list(config.config) if config is not None else []
        kept = [outcome for outcome in outcomes if outcome.code in order]
        merged = merge_voices(order, kept + [outcome for outcome in carried if outcome.code in order])
        deferred_codes = [outcome.code for outcome in kept if outcome.error_code == RATE_LIMITED]
        held = _held_voices(order, merged, deferred_codes, hold_for) if hold_for is not None and deferred_codes else set()
        writes = [ProfileWrite(key=key, value=voice.value, source=voice.source, source_date=voice.source_date) for key, voice in merged.items() if key not in held]
        written = await write_values(session, asset_id, writes, today=await profile_today(session, read_at)) if writes else []
        if kept:
            await update_state(session, asset_id, {outcome.code: _state_entry(outcome, read_at) for outcome in kept})
        await session.commit()
    except Exception as error:  # noqa: BLE001 — isolation boundary: one asset that cannot be saved never stops the others
        await session.rollback()
        logger.warning("Profile refresh of an asset failed: nothing saved for it", asset_id=asset_id, exc_info=error)
        return AssetRefreshResult(asset_id=asset_id, outcomes=outcomes, error=type(error).__name__, enrichers_read=len({outcome.code for outcome in outcomes}))
    deferred = [outcome for outcome in kept if outcome.error_code == RATE_LIMITED]
    read = {outcome.code for outcome in kept} | {outcome.code for outcome in carried if outcome.code in order}
    return AssetRefreshResult(asset_id=asset_id, written=[row.key for row in written], outcomes=kept, deferred=deferred, enrichers_read=len(read))


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
    return SourceValue(value=outcome.values[key], source_date=outcome.date_of(key))


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
