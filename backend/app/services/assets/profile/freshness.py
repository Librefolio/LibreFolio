"""«Adesso» non aggiornato (plan 68, D1d): how fresh «now» is for the voices that change at every read.

For a voice the catalogue marks ``volatile`` (fund size, market cap, gross and net yield, modified duration, accrued
interest), «now» is **stale** when its last confirmation is more than ``STALE_AFTER_DAYS`` days old (the developer,
18/11/2026: these are slow data; four weekly reads missed).

**The last confirmation is not the row's day.** A read that gives the same value writes no row (the store's «different
from now»), so a row says when the value changed, not when a source last confirmed it. The confirmation lives in the
enrichers' ``state``: ``state[source][CONFIRMED_FIELD][key]``, the moment of the last read of that source that gave the
voice (``services/enrichers/refresh.py``), kept across failed and partial reads (``bindings.update_state``). For «now»
it is the confirmation of the source that wrote the row, read as a day in the scheduler's time zone and never before
the row's own ``read_on``. A value written by hand, a source that never gave the voice, or a state written before D1d:
the row's ``read_on``.

Nothing is written here: no row and no change to the store's rule. The profile read (D1), the risk and AI Export
receive the signal and decide what to do with it. ``holding_now`` says where it belongs on a list of steps: the last
one, when it holds «now».
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, tzinfo
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.logging_config import get_logger
from backend.app.services.assets.profile.catalogue import CATALOGUE
from backend.app.services.assets.profile.store import ProfileRow, ProfileStep, current_rows_of, profile_zone
from backend.app.services.enrichers.bindings import CONFIRMED_FIELD, load_enrichers

#: «Now» of a volatile voice is stale when its last confirmation is more than this many days old.
STALE_AFTER_DAYS = 30

#: The voices that change at every read: the only ones that can be stale.
VOLATILE_VOICES = tuple(key for key, voice in CATALOGUE.items() if voice.volatile)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class VoiceFreshness:
    """How fresh «now» of one voice is: the day it was last confirmed, whether that is more than 30 days ago, and the
    ``read_on`` of the «now» row (a step reaching that day holds «now»)."""

    confirmed_on: date
    stale: bool
    opened_on: date


def _confirmed_day(row: ProfileRow, state: Mapping[str, Any], zone: tzinfo) -> date | None:
    """The day the row's source last gave the voice, from its ``state``; None when it says none."""
    entry = state.get(row.source)
    confirmed = entry.get(CONFIRMED_FIELD) if isinstance(entry, Mapping) else None
    moment = confirmed.get(row.key) if isinstance(confirmed, Mapping) else None
    if moment is None:
        return None
    try:
        return datetime.fromisoformat(str(moment)).astimezone(zone).date()
    except (TypeError, ValueError) as error:
        logger.warning("Unreadable profile confirmation: the row's day counts", asset_id=row.asset_id, voice=row.key, source=row.source, exc_info=error)
        return None


def freshness_of(row: ProfileRow, state: Mapping[str, Any], zone: tzinfo, today: date) -> VoiceFreshness:
    """The freshness of «now» ``row`` given its asset's enrichers ``state``, on ``today``."""
    confirmed = _confirmed_day(row, state, zone)
    confirmed_on = row.read_on if confirmed is None or confirmed < row.read_on else confirmed
    return VoiceFreshness(confirmed_on=confirmed_on, stale=(today - confirmed_on).days > STALE_AFTER_DAYS, opened_on=row.read_on)


async def voice_freshness(session: AsyncSession, asset_ids: Sequence[int], *, today: date, keys: Iterable[str] | None = None) -> dict[int, dict[str, VoiceFreshness]]:
    """For each asset, the freshness of «now» of each volatile voice it holds with a value (of ``keys``, or all); an
    emptied voice, and an asset without one, are left out. Nothing is read when ``keys`` names no volatile voice."""
    wanted = VOLATILE_VOICES if keys is None else tuple(key for key in VOLATILE_VOICES if key in set(keys))
    if not wanted:
        return {}
    rows = await current_rows_of(session, asset_ids, wanted)
    if not rows:
        return {}
    enrichers = await load_enrichers(session, list(rows))
    zone = await profile_zone(session)
    result: dict[int, dict[str, VoiceFreshness]] = {}
    for asset_id, voices in rows.items():
        row_of_asset = enrichers.get(asset_id)
        state = row_of_asset.state if row_of_asset is not None else {}
        # A voice emptied on purpose has no value to be stale
        result[asset_id] = {key: freshness_of(row, state, zone, today) for key, row in voices.items() if row.value is not None}
    return result


def holding_now(known: VoiceFreshness | None, steps: Sequence[ProfileStep]) -> VoiceFreshness | None:
    """The signal for a voice's steps: on its last step when that step reaches the day of the «now» row, so it holds
    «now» whatever day the caller's range ends on (a browser's today may be the scheduler's yesterday); a range that ends
    before «now» was read, or no step, carries none."""
    if known is None or not steps or steps[-1].through < known.opened_on:
        return None
    return known
