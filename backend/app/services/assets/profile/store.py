"""The store of the asset profile (plan 68, §3.1, §3.4, §3.7): write a voice only when it changes, read it as steps.

Every value enters through ``catalogue.normalize_value`` and is stored as its JSON text in ``asset_profile_updates``.

- **Order.** The rows of one voice are ordered by (``read_on``, ``id``). «Now» is the last of them; the steps are built
  in that order, so a card and a chart never disagree. A new row takes as ``read_on`` the later of today (in the
  scheduler's time zone) and the ``read_on`` of the voice's row now: a new row is always the last one, also on the day
  the scheduler's time zone moves the date back.
- **Different from now.** A value is written only when its stored form differs from the voice's value now, whoever
  wrote either («chiunque l'abbia scritto»): the source alone never makes a row. One exception, ``force_source`` (the
  user's «use the source's value», ``{"from": …}``): the row is written in the source's name with the same value too,
  unless now is already that value from that source.
- **Steps.** A read asks one or more assets, some voices (all when none), and a ``DateRangeModel`` or a
  ``MinStartDateRangeModel``; it gets, per asset and voice, the steps that hold in the range, one per stretch (never one
  per day): ``date`` … ``through``, the value and its source. Two neighbouring rows with the same value **and** the same
  source make one step. Several rows on one day: the last one holds that day. ``start: "min"`` is the first ``read_on``
  of the asset among the voices asked; nothing stored, or a first day after ``end``, answers nothing. ``carry_back``
  stretches each voice's first step back to ``start`` (the portfolio engine and the risk ask it, plan I18: «for a date
  we do not have, the oldest we have»), and a voice whose first row comes after ``end`` answers one step over the whole
  range with its first value; without it the steps begin where the history begins. A voice with no rows has nothing to
  carry.
- **Empty on purpose.** ``None`` is a value: stored as NULL, read as a step whose value is ``None``.
- **Forget.** Rows are deleted to forget a change; «now» and the steps then follow from the rows left.
- **Merge.** A voice only the source asset holds moves to the target whole, its rows keeping their ids (``move_voices``).
- **Changes.** The changes of an asset, newest first, each with the value before it; the panel leaves out the source
  rows of the volatile voices but those written by hand and the first source row that replaces one.

Writes run under SQLite's write lock (``db.session.begin_writes``): compare and insert are in one write transaction,
so two equal reads arriving together make one row (plan §3.7). The lock holds until the caller commits: between
``write_values`` and the commit nothing waits on the network. What the caller read before ``write_values`` is not
what it compares with: «now» is read again under the lock.

«The same value» is one rule for writing and for steps: the stored form of ``catalogue.normalize_value`` read back from
the row, so a row whose JSON text was written another way (key order, ``"0.6"`` for ``"0.6000"``) is still the same
value. Every reader gets the value in that stored form too. A voice the catalogue does not list is refused
(``catalogue.ProfileValueError``) when written and when asked.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AssetProfileUpdate
from backend.app.db.session import begin_writes
from backend.app.schemas.common import DateRangeModel, MinStartDateRangeModel
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts.global_settings_service import get_setting_value
from backend.app.services.assets.profile.catalogue import CATALOGUE, get_voice, normalize_value
from backend.app.services.financial_math.series_steps import steps_from_rows
from backend.app.utils.datetime_utils import ensure_utc, utcnow, zoneinfo_or_utc

#: Rows of «Ultime variazioni» per page.
CHANGES_PAGE_SIZE = 20
#: The source of a value written by hand.
USER_SOURCE = "user"
#: The source of a value copied from ``classification_params`` by migration 006.
LEGACY_SOURCE = "legacy"


class ProfileStoreError(Exception):
    """A request the store refuses as a whole: nothing was written or deleted."""


class ProfileUpdatesNotFound(ProfileStoreError):
    """Some of the rows asked to be forgotten are not rows of that asset. ``update_ids`` lists them."""

    def __init__(self, asset_id: int, update_ids: Sequence[int]):
        super().__init__(f"asset {asset_id}: no profile rows {sorted(update_ids)}")
        self.asset_id = asset_id
        self.update_ids = tuple(sorted(update_ids))


class ProfileUpdatesNewer(ProfileStoreError):
    """Some of the rows asked to be forgotten were written after ``as_of``: the page that asked had not seen them."""

    def __init__(self, asset_id: int, update_ids: Sequence[int]):
        super().__init__(f"asset {asset_id}: profile rows {sorted(update_ids)} are newer than the page that asked")
        self.asset_id = asset_id
        self.update_ids = tuple(sorted(update_ids))


@dataclass(frozen=True, slots=True)
class ProfileWrite:
    """One value to write: a voice, its raw value (``None``: empty on purpose), who gives it.

    ``source`` is an enricher's code, ``user`` or ``legacy``; ``user_id`` the author of a ``user`` row. ``force_source``
    writes the row in the source's name even with the value now (the user's «use the source's value»).
    """

    key: str
    value: Any
    source: str
    user_id: int | None = None
    source_date: date | None = None
    force_source: bool = False


@dataclass(frozen=True, slots=True)
class ProfileRow:
    """A stored row, its value decoded from JSON (``None``: empty on purpose)."""

    id: int
    asset_id: int
    key: str
    value: Any
    source: str
    user_id: int | None
    read_on: date
    source_date: date | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProfileStep:
    """One step of a voice: from ``date`` to ``through`` (both included) the value is ``value``, given by ``source``.

    ``update_id`` is the row the step starts with.
    """

    date: date
    through: date
    value: Any
    source: str
    update_id: int


@dataclass(frozen=True, slots=True)
class ProfileChange:
    """A row of «Ultime variazioni»: the row, and the voice's value before it (``has_previous`` False for its first)."""

    row: ProfileRow
    previous: Any
    has_previous: bool


@dataclass(frozen=True, slots=True)
class ProfileChangesPage:
    """One page of changes, newest first, and how many there are in all."""

    items: list[ProfileChange]
    total: int


# =============================================================================
# THE SAME VALUE
# =============================================================================


def _dumps(stored: Any) -> str:
    """The JSON text of a stored form: compact, keys in the order the stored form has them (maps already sorted)."""
    return json.dumps(stored, ensure_ascii=False, separators=(",", ":"))


def _same_value_text(key: str, text: str | None) -> str | None:
    """The one «same value» rule (writes and steps): the row's text, read back through the catalogue's stored form.

    A row written another way (key order, ``"0.6"`` for ``"0.6000"``) gives the text the catalogue would write. A text
    the catalogue no longer accepts (a rule tightened later) stays as it is: it is still compared, never refused here.
    """
    if text is None:
        return None
    try:
        return _dumps(normalize_value(key, json.loads(text)))
    except (ValueError, TypeError):
        # Parsing probe: a value the catalogue refuses today is compared by its own text, not lost
        return text


def _value(record: AssetProfileUpdate) -> Any:
    """The row's value in its stored form (``_same_value_text``), whatever the way its text was written; None for a value
    left empty on purpose."""
    text = _same_value_text(record.key, record.value)
    return None if text is None else json.loads(text)


def _row(record: AssetProfileUpdate) -> ProfileRow:
    return ProfileRow(
        id=record.id,
        asset_id=record.asset_id,
        key=record.key,
        value=_value(record),
        source=record.source,
        user_id=record.user_id,
        read_on=record.read_on,
        source_date=record.source_date,
        created_at=record.created_at,
    )


def _checked_keys(keys: Iterable[str] | None) -> list[str] | None:
    """The voices asked, each one checked against the catalogue; None for all."""
    if keys is None:
        return None
    checked = list(dict.fromkeys(keys))
    for key in checked:
        get_voice(key)
    return checked


_ORDER = (AssetProfileUpdate.asset_id, AssetProfileUpdate.key, AssetProfileUpdate.read_on, AssetProfileUpdate.id)


# =============================================================================
# TODAY AND NOW
# =============================================================================


async def profile_today(session: AsyncSession, now: datetime | None = None) -> date:
    """Today in the scheduler's time zone (``scheduler_timezone``; UTC when it is not set or not valid)."""
    name = await get_setting_value(session, SETTINGS_REGISTRY.global_.SCHEDULER_TIMEZONE.key)
    return (now or utcnow()).astimezone(zoneinfo_or_utc(name)).date()


async def _rows_of(session: AsyncSession, asset_ids: Sequence[int], keys: Sequence[str] | None, *, until: date | None = None) -> list[AssetProfileUpdate]:
    statement = select(AssetProfileUpdate).where(AssetProfileUpdate.asset_id.in_(asset_ids))
    if keys is not None:
        statement = statement.where(AssetProfileUpdate.key.in_(keys))
    if until is not None:
        statement = statement.where(AssetProfileUpdate.read_on <= until)
    return list((await session.execute(statement.order_by(*_ORDER))).scalars().all())


def _last_by_key(records: Iterable[AssetProfileUpdate]) -> dict[str, AssetProfileUpdate]:
    """The last record of each voice; ``records`` are in (``read_on``, ``id``) order within a voice."""
    last: dict[str, AssetProfileUpdate] = {}
    for record in records:
        last[record.key] = record
    return last


async def current_rows(session: AsyncSession, asset_id: int, keys: Iterable[str] | None = None) -> dict[str, ProfileRow]:
    """«Now» of each voice of ``asset_id`` (of ``keys``, or all): its last row in (``read_on``, ``id``) order."""
    records = await _rows_of(session, [asset_id], _checked_keys(keys))
    return {key: _row(record) for key, record in _last_by_key(records).items()}


# =============================================================================
# WRITE
# =============================================================================


async def write_values(session: AsyncSession, asset_id: int, writes: Sequence[ProfileWrite], *, today: date) -> list[ProfileRow]:
    """Write each value that differs from now (or a ``force_source`` one); the rows written, in order. Not committed.

    Every value is checked first (``catalogue.ProfileValueError``): one refused value writes nothing.
    """
    prepared = [(write, normalize_value(write.key, write.value)) for write in writes]
    if not prepared:
        return []
    await begin_writes(session, AssetProfileUpdate)
    keys = list(dict.fromkeys(write.key for write, _ in prepared))
    now = _last_by_key(await _rows_of(session, [asset_id], keys))
    # «now» per voice as (same-value text, source, read_on): updated by each write of this call, so a second write of
    # the same voice compares with the first
    state: dict[str, tuple[str | None, str, date]] = {key: (_same_value_text(key, record.value), record.source, record.read_on) for key, record in now.items()}
    written: list[AssetProfileUpdate] = []
    for write, stored in prepared:
        text = None if stored is None else _dumps(stored)
        current = state.get(write.key)
        if current is None:
            if text is None:
                continue  # emptying a voice that holds nothing changes nothing
        else:
            current_text, current_source, _ = current
            same_value = current_text == text
            if same_value and not write.force_source:
                continue
            if same_value and current_source == write.source:
                continue  # «use the source's value» when now is already that value from that source
        read_on = today if current is None else max(today, current[2])
        record = AssetProfileUpdate(
            asset_id=asset_id,
            key=write.key,
            value=text,
            source=write.source,
            user_id=write.user_id,
            read_on=read_on,
            source_date=write.source_date,
        )
        session.add(record)
        written.append(record)
        state[write.key] = (text, write.source, read_on)
    await session.flush()
    return [_row(record) for record in written]


# =============================================================================
# READ AS STEPS
# =============================================================================


async def _first_days(session: AsyncSession, asset_ids: Sequence[int], keys: Sequence[str] | None) -> dict[int, date]:
    """The first ``read_on`` of each asset among ``keys`` (all voices when None): what ``start: "min"`` stands for."""
    statement = select(AssetProfileUpdate.asset_id, func.min(AssetProfileUpdate.read_on)).where(AssetProfileUpdate.asset_id.in_(asset_ids))
    if keys is not None:
        statement = statement.where(AssetProfileUpdate.key.in_(keys))
    rows = (await session.execute(statement.group_by(AssetProfileUpdate.asset_id))).all()
    return {asset_id: first for asset_id, first in rows if first is not None}


def _last_of_each_day(records: Sequence[AssetProfileUpdate]) -> list[AssetProfileUpdate]:
    """One record per voice and day, the last in (``read_on``, ``id``) order: several rows on one day are normal (plan
    §3.7), and ``series_steps.steps_from_rows`` takes one row per day."""
    kept: dict[tuple[str, date], AssetProfileUpdate] = {}
    for record in records:
        kept[(record.key, record.read_on)] = record
    return list(kept.values())


async def read_steps(
    session: AsyncSession,
    asset_ids: Sequence[int],
    date_range: DateRangeModel | MinStartDateRangeModel,
    keys: Iterable[str] | None = None,
    *,
    carry_back: bool = False,
) -> dict[int, dict[str, list[ProfileStep]]]:
    """The steps of each asset and voice in ``date_range``; an asset or a voice with no step in it is left out."""
    checked = _checked_keys(keys)
    asset_ids = list(dict.fromkeys(asset_ids))
    if not asset_ids:
        return {}
    end = date_range.end if date_range.end is not None else date_range.start
    if isinstance(date_range, MinStartDateRangeModel):
        starts = await _first_days(session, asset_ids, checked)
    else:
        starts = dict.fromkeys(asset_ids, date_range.start)
    # carry_back reads past ``end`` too: a voice whose history begins after the range still lends its first value to it
    records = await _rows_of(session, list(starts), checked, until=None if carry_back else end)
    by_asset: dict[int, list[AssetProfileUpdate]] = {}
    for record in records:
        by_asset.setdefault(record.asset_id, []).append(record)
    result: dict[int, dict[str, list[ProfileStep]]] = {}
    for asset_id, asset_records in by_asset.items():
        if starts[asset_id] <= end and (voices := _asset_steps(asset_records, starts[asset_id], end, carry_back=carry_back)):
            result[asset_id] = voices
    return result


def _asset_steps(records: Sequence[AssetProfileUpdate], start: date, end: date, *, carry_back: bool) -> dict[str, list[ProfileStep]]:
    """The steps of one asset's voices from ``start`` to ``end``; ``records`` in (``read_on``, ``id``) order per voice,
    past ``end`` too when ``carry_back``."""
    steps = steps_from_rows(
        _last_of_each_day([record for record in records if record.read_on <= end]),
        day=lambda record: record.read_on,
        values=lambda record: (_same_value_text(record.key, record.value), record.source),
        key=lambda record: record.key,
        range_start=start,
        range_end=end,
    )
    voices: dict[str, list[ProfileStep]] = {}
    for step in steps:
        voices.setdefault(step.row.key, []).append(_step(step.row, step.date, step.through))
    if carry_back:
        for voice_steps in voices.values():
            if voice_steps[0].date > start:
                voice_steps[0] = dataclasses.replace(voice_steps[0], date=start)
        # A voice whose first row comes after the range: its first value holds the whole range (plan I18, «for a date we
        # do not have, the oldest we have»)
        for record in records:
            if record.key not in voices:
                voices[record.key] = [_step(record, start, end)]
    return voices


def _step(record: AssetProfileUpdate, first: date, through: date) -> ProfileStep:
    return ProfileStep(date=first, through=through, value=_value(record), source=record.source, update_id=record.id)


# =============================================================================
# FORGET
# =============================================================================


async def forget_updates(session: AsyncSession, asset_id: int, update_ids: Sequence[int], *, as_of: datetime | None = None) -> int:
    """Delete those rows of ``asset_id``; how many. Not committed.

    All or nothing: an id that is not a row of that asset raises ``ProfileUpdatesNotFound``, a row created after
    ``as_of`` raises ``ProfileUpdatesNewer``, and nothing is deleted.
    """
    wanted = set(update_ids)
    if not wanted:
        return 0
    await begin_writes(session, AssetProfileUpdate)
    statement = select(AssetProfileUpdate.id, AssetProfileUpdate.created_at).where(AssetProfileUpdate.asset_id == asset_id, AssetProfileUpdate.id.in_(wanted))
    found = dict((await session.execute(statement)).all())
    missing = wanted - set(found)
    if missing:
        raise ProfileUpdatesNotFound(asset_id, sorted(missing))
    if as_of is not None:
        newer = [update_id for update_id, created_at in found.items() if ensure_utc(created_at) > ensure_utc(as_of)]
        if newer:
            raise ProfileUpdatesNewer(asset_id, newer)
    result = await session.execute(delete(AssetProfileUpdate).where(AssetProfileUpdate.asset_id == asset_id, AssetProfileUpdate.id.in_(wanted)).execution_options(synchronize_session=False))
    return result.rowcount


# =============================================================================
# CHANGES
# =============================================================================


async def recent_changes(session: AsyncSession, asset_id: int, *, key: str | None = None, page: int = 0, page_size: int = CHANGES_PAGE_SIZE) -> ProfileChangesPage:
    """The changes of ``asset_id``, newest first in (``read_on``, ``id``) order, one page.

    Without ``key``, the panel: every voice, but for a volatile voice only the rows written by hand and the first source
    row after one. With ``key``, the history of that voice: all its rows.
    """
    records = await _rows_of(session, [asset_id], None if key is None else _checked_keys([key]))
    changes: list[ProfileChange] = []
    previous: dict[str, AssetProfileUpdate] = {}
    for record in records:
        before = previous.get(record.key)
        previous[record.key] = record
        if key is None and not _shown_in_panel(record, before):
            continue
        changes.append(ProfileChange(row=_row(record), previous=_row(before).value if before is not None else None, has_previous=before is not None))
    # Newest first, across voices: (read_on, id) descending
    changes.sort(key=lambda change: (change.row.read_on, change.row.id), reverse=True)
    first = page * page_size
    return ProfileChangesPage(items=changes[first : first + page_size], total=len(changes))


def _shown_in_panel(record: AssetProfileUpdate, before: AssetProfileUpdate | None) -> bool:
    """Whether the panel shows a row: every row of a voice that keeps still; for a volatile voice, only the rows written
    by hand and the source row that replaces one (plan §3.7, «Ultime variazioni»)."""
    voice = CATALOGUE.get(record.key)
    if voice is None or not voice.volatile:
        return True
    return record.source == USER_SOURCE or (before is not None and before.source == USER_SOURCE)


# =============================================================================
# MERGE
# =============================================================================


async def move_voices(session: AsyncSession, source_id: int, target_id: int) -> dict[str, Any]:
    """Merge of two assets (plan 68, A5): move to ``target_id`` each voice ``source_id`` holds now with a value and the
    target has no row of; the voices moved and their value now. Not committed.

    A voice moves whole, by changing only ``asset_id``: its rows keep their ids and days, so its order is unchanged and
    two histories of one voice never mix. A voice the target has rows of — even emptied on purpose — stays the target's.
    The rest of the source's profile goes with the source (``CASCADE``).
    """
    source_now = await current_rows(session, source_id)
    target_keys = set((await session.execute(select(AssetProfileUpdate.key).where(AssetProfileUpdate.asset_id == target_id).distinct())).scalars().all())
    moved = {key: row.value for key, row in source_now.items() if row.value is not None and key not in target_keys}
    if moved:
        statement = update(AssetProfileUpdate).where(AssetProfileUpdate.asset_id == source_id, AssetProfileUpdate.key.in_(list(moved)))
        await session.execute(statement.values(asset_id=target_id).execution_options(synchronize_session=False))
    return moved
