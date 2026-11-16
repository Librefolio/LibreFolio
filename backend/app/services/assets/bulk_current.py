"""Current values read in bulk: one provider call for many assets (project 76, plan §3.1).

A provider that declares ``supports_bulk_current`` (``base.py``) prices every asset of a GROUP with one call per chunk of
``bulk_current_max_items``, instead of one call per asset. A group is one provider, one set of its settings
(``core.settings_cache_part``) and one pause scope (``core.cooldown_scope_for``): what a single call can serve. The core
groups; the plugin only answers the items it is given.

- **Aligned expiry.** When a group must be read, the call covers every ACTIVE asset assigned to the provider, plus the
  assets asked for (a detail page may ask for an inactive one). Every answer goes to the per-asset current-value cache
  (``core._asset_current_cache``), so the readers that ask other sets of assets — the scheduler, the asset list, a
  detail page, the dashboard — find them there, and the whole group expires at the same time: one call per group per
  expiry, not one per set of assets.
- **The group stamp.** A per-asset entry alone cannot say «read, and nothing came»: an omitted identifier, a quote the
  price columns cannot keep or an answer of its own error leave no entry, and that asset would make the whole group read
  again at every request. So a read leaves a stamp per group, ``(expiry, members)``: within it, a member without a cached
  quote is served from the database without a call; an asset outside the members (an assignment newer than the read)
  reads the whole group again. A read that ends in another failure leaves a short stamp; a refusal for too many requests
  leaves none: the provider's pause decides when to call again (``provider_cooldown.py``).
- **Single-flight.** One ``asyncio.Lock`` per group, per event loop: the scheduler and a page that find the same group
  expired make one call; the second finds the stamp the first left. Only the read and the cache fill run under the lock;
  the database fallback and today's row stay with the caller.
- **Only what was asked is written.** The assets read but not asked for go to the cache only, never to today's row of
  ``price_history``: the scheduler asks for every active asset within its interval, and writes them then.

Per process, by design (plan §3.3): stamps, locks and the cache live in each uvicorn worker. The Docker image runs one
worker, and the scheduler runs in one process at a time; with N workers only the reads the pages drive multiply.

The session is used before the reads only (the active assignments of the providers to read): the reads run in parallel,
and one ``AsyncSession`` never serves concurrent tasks (MF-SEC9c).
"""

from __future__ import annotations

import asyncio
import time
import weakref
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetProviderAssignment
from backend.app.schemas.prices import FACurrentValue, FACurrentValueRequest
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.price_store import storable_current_value, unstorable_quote_reason

logger = structlog.get_logger(__name__)

#: The timeout of one bulk call, longer than a single asset's: one request answers up to ``bulk_current_max_items``.
BULK_CURRENT_TIMEOUT = 30.0

#: How long a group read stays fresh: the life of the per-asset current-value cache.
GROUP_STAMP_SECONDS = 120.0

#: How long a group read that failed (not refused) stays fresh at most: a broken source is not called at every request,
#: and the prices it cannot give are not hidden for long.
SHORT_STAMP_SECONDS = 120.0

#: The monotonic clock of the stamps; the tests move it.
_clock: Callable[[], float] = time.monotonic

#: The key of a group: provider code, settings fingerprint, pause scope.
GroupKey = tuple[str, str, Optional[str]]


@dataclass(frozen=True)
class _Stamp:
    """The last read of a group: when it expires, the cache keys it covered, and the reasons of the quotes it refused
    for the price columns (X-R51), so that a refresh within the stamp still reports them."""

    expires_at: float
    members: frozenset[tuple]
    notes: Mapping[tuple, str] = field(default_factory=dict)


@dataclass(frozen=True)
class _Entry:
    """One asset to price in a group: its id (the first one, when assets share a cache key), its provider inputs and its
    cache key."""

    asset_id: int
    identifier: str
    identifier_type: object  # the IdentifierType the plugin receives
    provider_params: dict
    cache_key: tuple


@dataclass(frozen=True)
class BulkQuote:
    """What a bulk read gives one asked asset: its quote from the cache, as the price columns keep it (None: the caller
    falls back to the database), the refusal for too many requests of its group, and, when this read refused its
    quote for the price columns, the reason a refresh reports (X-R51)."""

    quote: Optional[FACurrentValue]
    refusal: Optional[AssetRateLimitedError] = None
    note: Optional[str] = None


_stamps: dict[GroupKey, _Stamp] = {}
_locks: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[GroupKey, asyncio.Lock]] = weakref.WeakKeyDictionary()


def reset_group_state() -> None:
    """Forget every group stamp and lock (the tests)."""
    _stamps.clear()
    _locks.clear()


def _group_lock(group_key: GroupKey) -> asyncio.Lock:
    """The lock of a group in the running event loop: an ``asyncio.Lock`` belongs to one loop."""
    return _locks.setdefault(asyncio.get_running_loop(), {}).setdefault(group_key, asyncio.Lock())


def _stamp(group_key: GroupKey, members: frozenset[tuple], seconds: float, since: float, notes: Mapping[tuple, str]) -> None:
    """Record a read of the group, from ``since`` (the clock before its first call: the stamp never outlives the
    entries the read cached, which start later), and drop the stamps that have expired."""
    now = _clock()
    for key in [key for key, stamp in _stamps.items() if stamp.expires_at <= now]:
        del _stamps[key]
    _stamps[group_key] = _Stamp(expires_at=since + seconds, members=members, notes=dict(notes))


def _stamped_note(group_key: GroupKey, cache_key: tuple) -> str | None:
    """The X-R51 reason a fresh stamp of the group keeps for ``cache_key``: an earlier read refused its quote for the
    price columns, and a refresh within the stamp reports it as the per-asset path would."""
    stamp = _stamps.get(group_key)
    if stamp is None or _clock() >= stamp.expires_at:
        return None
    return stamp.notes.get(cache_key)


def forget_member(cache_key: tuple) -> None:
    """Forget the stamps that cover ``cache_key``: its cached quote was dropped (``core.drop_asset_cache_entries``: a
    parametric assignment or the asset's currency changed), so the next request for it reads its group again instead
    of serving the database until the stamp expires."""
    for key in [key for key, stamp in _stamps.items() if cache_key in stamp.members]:
        del _stamps[key]


def _needs_read(group_key: GroupKey, wanted: Sequence[tuple]) -> bool:
    """Whether a group must be read for the cache keys ``wanted``: one has no cached quote and is not covered by a fresh
    stamp (an asset the last read left without a quote is served from the database until the stamp expires)."""
    stamp = _stamps.get(group_key)
    fresh = stamp is not None and _clock() < stamp.expires_at
    for cache_key in wanted:
        if core._asset_current_cache.get(cache_key)[1]:
            continue
        if not (fresh and cache_key in stamp.members):
            return True
    return False


def supports_bulk(provider: AssetSourceProvider | None) -> bool:
    """Whether the core reads ``provider``'s current values in bulk. Read with a default: a test double that is no plugin
    declares nothing."""
    return provider is not None and getattr(provider, "supports_bulk_current", False) is True


def _entry(provider: AssetSourceProvider, assignment: AssetProviderAssignment) -> tuple[GroupKey, _Entry]:
    """The group and the entry of one assignment, keyed as every other reader of the cache keys it (``asset_cache_key``)."""
    params = core._parse_provider_params(assignment.provider_params)
    identifier_type = AssetSourceProvider.map_input_type_to_identifier_type(assignment.identifier_type)
    settings_part = core.settings_cache_part(provider)
    cache_key = core.asset_cache_key(assignment.provider_code, assignment.identifier, assignment.identifier_type, params, settings_part)
    scope = core.cooldown_scope_for(provider, assignment.identifier, identifier_type, params)
    entry = _Entry(asset_id=assignment.asset_id, identifier=assignment.identifier or "", identifier_type=identifier_type, provider_params=params, cache_key=cache_key)
    return (assignment.provider_code, settings_part, scope), entry


async def _active_assignments(session: AsyncSession, provider_codes: Sequence[str]) -> list[AssetProviderAssignment]:
    """The assignments of the active assets to ``provider_codes``: one statement."""
    statement = select(AssetProviderAssignment).join(Asset, Asset.id == AssetProviderAssignment.asset_id).where(Asset.active == True, AssetProviderAssignment.provider_code.in_(sorted(set(provider_codes))))  # noqa: E712 — SQLAlchemy expression
    return list((await session.execute(statement)).scalars().all())


async def _read_group(group_key: GroupKey, provider: AssetSourceProvider, entries: list[_Entry], wanted: list[tuple], semaphore: asyncio.Semaphore) -> tuple[AssetRateLimitedError | None, dict[tuple, str]]:
    """Read one group, under its lock, unless another reader did meanwhile; the refusal for too many requests met, if
    any, and the reasons of the quotes this read refused for the price columns, by cache key. Every answer that the
    price columns can keep goes to the per-asset cache."""
    code, _settings_part, scope = group_key
    async with _group_lock(group_key):
        if not _needs_read(group_key, wanted):
            return None, {}  # another reader read it while this one waited
        members = frozenset(entry.cache_key for entry in entries)
        since = _clock()
        most = provider.bulk_current_max_items
        notes: dict[tuple, str] = {}
        try:
            for start in range(0, len(entries), most):
                chunk = entries[start : start + most]
                items = [FACurrentValueRequest(key=str(index), identifier=entry.identifier, identifier_type=entry.identifier_type, provider_params=entry.provider_params) for index, entry in enumerate(chunk)]
                async with semaphore:
                    answer = await core.call_provider(provider, lambda items=items: provider.get_current_values_bulk(items), timeout=BULK_CURRENT_TIMEOUT, scope=scope)
                notes.update(_cache_answers(code, chunk, answer))
        except AssetRateLimitedError as refused:
            # Paused, or refused now: no stamp, the provider's pause decides when to call again (decision 34)
            logger.debug("Bulk current-value read refused", provider=code, retry_after=refused.retry_after)
            return refused, notes
        except Exception as error:  # noqa: BLE001 — isolation boundary: a failed read falls back to the stored prices
            # The last stored prices are served, and a short stamp keeps a broken source from being called at every
            # request. The error leaves call_provider with the provider's secrets masked. A provider left without a
            # required setting is a known state, not a failure to trace (it says so at every call until configured).
            if isinstance(error, AssetSourceError) and error.error_code == "NOT_CONFIGURED":
                logger.info("Bulk current-value read skipped: provider not configured", provider=code)
            else:
                logger.warning("Bulk current-value read failed: last stored prices served", provider=code, error_code=getattr(error, "error_code", None), error=type(error).__name__, exc_info=error)
            _stamp(group_key, members, min(GROUP_STAMP_SECONDS, SHORT_STAMP_SECONDS), since, notes)
            return None, notes
        _stamp(group_key, members, GROUP_STAMP_SECONDS, since, notes)
        return None, notes


def _cache_answers(provider_code: str, chunk: list[_Entry], answer: object) -> dict[tuple, str]:
    """Cache the answers of one call, as the per-asset path caches a quote: only one the price columns can keep; the
    reasons of the ones they refuse, by cache key (X-R51). A key the core did not ask for is ignored; an asset's own
    error is logged by its code only (its text may come from the source)."""
    notes: dict[tuple, str] = {}
    if not isinstance(answer, dict):
        logger.warning("Bulk current-value answer is not a dict: ignored", provider=provider_code, answer_type=type(answer).__name__)
        return notes
    for index, entry in enumerate(chunk):
        value = answer.get(str(index))
        if isinstance(value, FACurrentValue):
            quote = storable_current_value(value, entry.asset_id, provider_code)
            if quote is not None:
                core._asset_current_cache.set(entry.cache_key, quote)
            else:
                notes[entry.cache_key] = unstorable_quote_reason(value.value)
        elif isinstance(value, AssetSourceError):
            logger.debug("Bulk current value refused for one asset", provider=provider_code, asset_id=entry.asset_id, error_code=value.error_code)
    return notes


@dataclass
class BulkPlan:
    """The requested assets whose provider reads in bulk, grouped, with the groups to read: built with the session
    (``prepare_bulk``), read without it (``read``)."""

    asked: dict[int, tuple[GroupKey, _Entry]]
    providers: dict[str, AssetSourceProvider | None]
    wanted: dict[GroupKey, list[tuple]]
    entries: dict[GroupKey, dict[tuple, _Entry]]

    async def read(self, semaphore: asyncio.Semaphore) -> dict[int, BulkQuote]:
        """Read the groups that need it, in parallel, and answer every asked asset (``BulkQuote``). Never touches a
        session."""
        to_read = list(self.entries)
        outcomes = await asyncio.gather(*(_read_group(group_key, self.providers[group_key[0]], list(self.entries[group_key].values()), self.wanted[group_key], semaphore) for group_key in to_read))
        refusals = {group_key: refusal for group_key, (refusal, _notes) in zip(to_read, outcomes, strict=True)}
        notes = {cache_key: note for _refusal, group_notes in outcomes for cache_key, note in group_notes.items()}
        quotes: dict[int, BulkQuote] = {}
        for asset_id, (group_key, entry) in self.asked.items():
            cached, found = core._asset_current_cache.get(entry.cache_key)
            quote = storable_current_value(cached, asset_id, group_key[0]) if found else None
            if quote is not None:
                quotes[asset_id] = BulkQuote(quote=quote)
            else:
                quotes[asset_id] = BulkQuote(quote=None, refusal=refusals.get(group_key), note=notes.get(entry.cache_key) or _stamped_note(group_key, entry.cache_key))
        return quotes


async def prepare_bulk(session: AsyncSession, requested: Sequence[tuple[int, AssetProviderAssignment]]) -> BulkPlan:
    """Group the requested assets whose provider reads in bulk, and find what each group to read covers.

    ``requested`` holds each asset once, with its assignment. An asset whose provider does not read in bulk, or is
    unknown, is left out of ``asked``: the per-asset path serves it. The groups to read take every active asset of
    their provider too (aligned expiry): one statement, here, before the reads, which never touch the session
    (MF-SEC9c).
    """
    providers: dict[str, AssetSourceProvider | None] = {}
    for _asset_id, assignment in requested:
        if assignment.provider_code not in providers:
            providers[assignment.provider_code] = await core.configured_provider(assignment.provider_code)
    asked = {asset_id: _entry(providers[assignment.provider_code], assignment) for asset_id, assignment in requested if supports_bulk(providers[assignment.provider_code])}
    wanted: dict[GroupKey, list[tuple]] = {}
    for group_key, entry in asked.values():
        wanted.setdefault(group_key, []).append(entry.cache_key)
    entries: dict[GroupKey, dict[tuple, _Entry]] = {group_key: {} for group_key, keys in wanted.items() if _needs_read(group_key, keys)}
    if entries:
        for assignment in await _active_assignments(session, [group_key[0] for group_key in entries]):
            group_key, entry = _entry(providers[assignment.provider_code], assignment)
            if group_key in entries:
                entries[group_key].setdefault(entry.cache_key, entry)
        for group_key, entry in asked.values():
            if group_key in entries:
                entries[group_key].setdefault(entry.cache_key, entry)
    return BulkPlan(asked=asked, providers=providers, wanted=wanted, entries=entries)
