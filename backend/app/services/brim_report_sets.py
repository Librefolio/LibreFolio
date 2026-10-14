"""Report sets: one import from several exports of the same bank.

The files uploaded together (same ``batch_id``) for one broker and recognised by
the same report-set plugin form a set. This module collects the members,
previews the set (roles, coverage, gaps and the broker history already in
LibreFolio), combines it into the derived combined file, and applies the broker
history to the parse of a combined file.

Design: ``LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/design-phase00BrimReportSets.md``.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Transaction
from backend.app.schemas.brim import (
    BRIMAbsorbed,
    BRIMCheckpoint,
    BRIMCoverage,
    BRIMDerivedRef,
    BRIMFileInfo,
    BRIMFileStatus,
    BRIMNotice,
    BRIMParseOutput,
    BRIMSetCombineResponse,
    BRIMSetMemberInfo,
    BRIMSetMissing,
    BRIMSetPreview,
    BRIMSetRoleStatus,
    BRIMTruthCash,
    BRIMVerification,
)
from backend.app.services import brim_provider
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider, BRIMSetRequiredError
from backend.app.services.provider_registry import BRIMProviderRegistry

logger = structlog.get_logger(__name__)

GAP_FIX_TAG = "gap_fix"


# =============================================================================
# ERRORS
# =============================================================================


class BRIMSetError(Exception):
    """A report-set request that cannot be served; the API maps it to ``status_code``."""

    status_code = 400
    code = "set_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BRIMSetPluginNotFound(BRIMSetError):
    status_code = 404
    code = "plugin_not_found"


class BRIMSetPluginNotASet(BRIMSetError):
    status_code = 400
    code = "plugin_not_a_set"


class BRIMSetMembersNotFound(BRIMSetError):
    status_code = 404
    code = "members_not_found"


class BRIMSetExcludeUnknown(BRIMSetError):
    """A file left out of the set that is not an original of its broker and upload."""

    status_code = 422
    code = "exclude_unknown"


class BRIMSetIncomplete(BRIMSetError):
    status_code = 422
    code = "set_incomplete"

    def __init__(self, message: str, missing_roles: Sequence[str]):
        super().__init__(message)
        self.missing_roles: List[str] = list(missing_roles)


class BRIMSetCombineFailed(BRIMSetError):
    """The plugin could not combine the members; they stay as they are."""

    status_code = 422
    code = "combine_failed"


# =============================================================================
# MEMBERS AND HISTORY
# =============================================================================


def get_set_plugin(plugin_code: str) -> BRIMProvider:
    """The report-set plugin registered under ``plugin_code``."""
    plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
    if plugin is None:
        raise BRIMSetPluginNotFound(f"Unknown import plugin: {plugin_code}")
    if not plugin.is_report_set_plugin:
        raise BRIMSetPluginNotASet(f"{plugin_code} imports single files, not report sets")
    return plugin


def collect_members(*, broker_id: int, plugin_code: str, batch_id: str, exclude_file_ids: Sequence[str] = ()) -> List[BRIMFileInfo]:
    """The original files of one upload batch that the plugin can read, oldest first.

    ``exclude_file_ids`` are the originals the user left out of the set (read alone with
    another plugin, or removed from it). Each must be an original of this broker and upload:
    any other id is refused rather than ignored, so a stale request never passes silently.
    """
    originals = [info for info in brim_provider.list_files(broker_ids=[broker_id]) if info.kind == "original" and info.batch_id == batch_id and info.target_broker_id == broker_id]
    known = {info.file_id for info in originals}
    unknown = sorted({file_id for file_id in exclude_file_ids if file_id not in known})
    if unknown:
        raise BRIMSetExcludeUnknown(f"Not an original of batch {batch_id} for this broker: {', '.join(unknown)}")
    excluded = set(exclude_file_ids)
    members = [info for info in originals if plugin_code in info.compatible_plugins and info.status != BRIMFileStatus.FAILED and info.file_id not in excluded]
    if not members:
        raise BRIMSetMembersNotFound(f"No files of batch {batch_id} can be read by {plugin_code} for this broker")
    members.sort(key=lambda info: (info.uploaded_at, info.filename))
    return members


def _has_tag(tags: Optional[str], tag: str) -> bool:
    return tag in {part.strip() for part in (tags or "").split(",")}


async def _tagged_dates(session: AsyncSession, *, broker_id: int, history_tag: str) -> List[Tuple[date, bool]]:
    """(date, is gap-fix) of every broker transaction carrying ``history_tag`` as an exact tag."""
    stmt = select(Transaction.date, Transaction.tags).where(Transaction.broker_id == broker_id, Transaction.tags.contains(history_tag))
    rows = (await session.execute(stmt)).all()
    return [(tx_date, _has_tag(tags, GAP_FIX_TAG)) for tx_date, tags in rows if _has_tag(tags, history_tag)]


async def history_start(session: AsyncSession, *, broker_id: int, history_tag: str) -> Optional[date]:
    """First day of the broker history LibreFolio already holds for this plugin (design D-S25).

    The oldest transaction tagged with the plugin's history tag; a gap-fix correction
    counts from the day after its date, because it summarises everything up to that day.
    """
    return _first_history_day(await _tagged_dates(session, broker_id=broker_id, history_tag=history_tag))


def _first_history_day(dated: Sequence[Tuple[date, bool]]) -> Optional[date]:
    if not dated:
        return None
    return min(tx_date + timedelta(days=1) if is_gap_fix else tx_date for tx_date, is_gap_fix in dated)


def _gap_fix_days(dated: Sequence[Tuple[date, bool]]) -> List[date]:
    return sorted({tx_date for tx_date, is_gap_fix in dated if is_gap_fix})


async def gap_fix_dates(session: AsyncSession, *, broker_id: int, history_tag: str) -> List[date]:
    """Dates of the gap-fix corrections already imported for this plugin."""
    return _gap_fix_days(await _tagged_dates(session, broker_id=broker_id, history_tag=history_tag))


# =============================================================================
# PREVIEW
# =============================================================================


def _trade_range(coverage: Sequence[BRIMCoverage]) -> Optional[Tuple[date, date]]:
    trade = [item for item in coverage if item.axis == "trade"]
    if not trade:
        return None
    return min(item.start for item in trade), max(item.end for item in trade)


def _notice(code: str, message: str, **context: object) -> BRIMNotice:
    return BRIMNotice(severity="warning", code=code, message=message, context=dict(context) or None)


def build_preview(  # noqa: C901 — one pass per concern (members, roles, coverage, shape), no nesting
    plugin: BRIMProvider,
    members: Sequence[BRIMFileInfo],
    *,
    broker_id: int,
    plugin_code: str,
    batch_id: str,
    history_start: Optional[date],
    gap_fix_dates: Sequence[date],
    history_end: Optional[date] = None,
    history_count: int = 0,
) -> BRIMSetPreview:
    """Describe a set without combining it. Reads the member files through the plugin."""
    warnings: List[BRIMNotice] = []
    member_infos: List[BRIMSetMemberInfo] = []
    paths_by_role: Dict[str, List[Path]] = defaultdict(list)
    ids_by_role: Dict[str, List[str]] = defaultdict(list)
    coverage_by_role: Dict[str, List[BRIMCoverage]] = defaultdict(list)
    fingerprints = set()

    for member in members:
        path = brim_provider.get_file_path(member.file_id)
        role = plugin.detect_role(path) if path is not None else None
        if role is None:
            member_infos.append(BRIMSetMemberInfo(file_id=member.file_id, filename=member.filename))
            warnings.append(_notice("unknown_role", f"{member.filename} is not an export this plugin combines", file_id=member.file_id))
            continue
        summary = plugin.describe_member(path)
        member_infos.append(BRIMSetMemberInfo(file_id=member.file_id, filename=member.filename, role=role, rows=summary.rows, coverage=summary.coverage))
        paths_by_role[role].append(path)
        ids_by_role[role].append(member.file_id)
        coverage_by_role[role].extend(summary.coverage)
        if summary.account_fingerprint:
            fingerprints.add(summary.account_fingerprint)

    role_statuses: List[BRIMSetRoleStatus] = []
    missing: List[BRIMSetMissing] = []
    excess = False
    for role in plugin.report_roles:
        file_ids = ids_by_role.get(role.code, [])
        if not file_ids:
            status = "missing"
        elif len(file_ids) > 1 and not role.multiple:
            status = "excess"
            excess = True
            warnings.append(_notice("excess_files", f"Only one {role.code} export is allowed in a set", role=role.code))
        else:
            status = "present"
        role_statuses.append(BRIMSetRoleStatus(code=role.code, required=role.required, multiple=role.multiple, status=status, file_ids=list(file_ids)))
        if status == "missing" and role.required:
            covered = _trade_range(coverage_by_role.get(role.must_cover, [])) if role.must_cover else None
            start, end = (covered[0] - timedelta(days=1), covered[1]) if covered else (None, None)
            missing.append(BRIMSetMissing(role=role.code, start=start, end=end))

    for role in plugin.report_roles:
        own = coverage_by_role.get(role.code, [])
        covered = _trade_range(coverage_by_role.get(role.must_cover, [])) if role.must_cover else None
        if not own or covered is None:
            continue
        own_start = min(item.start for item in own)
        own_end = max(item.end for item in own)
        if own_start > covered[0] - timedelta(days=1):
            warnings.append(_notice("coverage_starts_late", f"The {role.code} export starts after the {role.must_cover} period", role=role.code, covered_role=role.must_cover, date=own_start.isoformat()))
        if own_end < covered[1]:
            warnings.append(_notice("coverage_ends_early", f"The {role.code} export ends before the {role.must_cover} period", role=role.code, covered_role=role.must_cover, date=own_end.isoformat()))

    mixed_accounts = len(fingerprints) > 1
    if mixed_accounts:
        warnings.append(_notice("mixed_accounts", "The files come from different accounts"))

    required_present = all(ids_by_role.get(role.code) for role in plugin.report_roles if role.required)
    segments = []
    gaps = []
    if required_present:
        shape = plugin.describe_set(dict(paths_by_role))
        segments = list(shape.segments)
        gaps = list(shape.gaps)
        warnings.extend(shape.notices)
        flagged_gap_fix = set()
        for segment in segments:
            segment_end = segment.end or segment.start
            if history_start is not None and segment_end < history_start:
                warnings.append(_notice("before_history_segment", "This period is older than the history already in LibreFolio and will not be imported", start=segment.start.isoformat(), end=segment_end.isoformat()))
            for fix_date in gap_fix_dates:
                if segment.start <= fix_date <= segment_end and fix_date not in flagged_gap_fix:
                    flagged_gap_fix.add(fix_date)
                    warnings.append(_notice("covers_gap_fix", "A gap-fix correction already imported falls inside this period: remove it after the import", date=fix_date.isoformat()))

    return BRIMSetPreview(
        broker_id=broker_id,
        plugin_code=plugin_code,
        batch_id=batch_id,
        members=member_infos,
        roles=role_statuses,
        missing=missing,
        segments=segments,
        gaps=gaps,
        history_start=history_start,
        history_end=history_end,
        history_count=history_count,
        warnings=warnings,
        complete=required_present and not excess and not mixed_accounts,
    )


async def preview_set(session: AsyncSession, *, broker_id: int, plugin_code: str, batch_id: str, exclude_file_ids: Sequence[str] = ()) -> BRIMSetPreview:
    """Preview one report set; reads the member files, writes nothing.

    The broker history comes from one read of the tagged transactions: H0, its last day and its
    size (gap-fix corrections included), shown by the set's timeline, and the gap-fix dates.
    """
    plugin = get_set_plugin(plugin_code)
    members = await asyncio.to_thread(collect_members, broker_id=broker_id, plugin_code=plugin_code, batch_id=batch_id, exclude_file_ids=exclude_file_ids)
    dated = await _tagged_dates(session, broker_id=broker_id, history_tag=plugin.history_tag)
    return await asyncio.to_thread(
        build_preview,
        plugin,
        members,
        broker_id=broker_id,
        plugin_code=plugin_code,
        batch_id=batch_id,
        history_start=_first_history_day(dated),
        gap_fix_dates=_gap_fix_days(dated),
        history_end=max((tx_date for tx_date, _is_gap_fix in dated), default=None),
        history_count=len(dated),
    )


# =============================================================================
# COMBINE
# =============================================================================


def _combined_filename(plugin: BRIMProvider, preview: BRIMSetPreview) -> str:
    """A generated name: never the originals' names, which may carry an account number."""
    if preview.segments:
        start = min(segment.start for segment in preview.segments)
        end = max(segment.end or segment.start for segment in preview.segments)
        return f"{plugin.provider_name} — combined {start.isoformat()}…{end.isoformat()}.csv"
    return f"{plugin.provider_name} — combined.csv"


async def combine_set(session: AsyncSession, *, broker_id: int, plugin_code: str, batch_id: str, user_id: Optional[int], exclude_file_ids: Sequence[str] = ()) -> BRIMSetCombineResponse:
    """Combine a complete set, or reuse the identical combined file built before (design D-S6).

    The members are the preview's, without the files the user left out (``exclude_file_ids``).
    """
    plugin = get_set_plugin(plugin_code)
    preview = await preview_set(session, broker_id=broker_id, plugin_code=plugin_code, batch_id=batch_id, exclude_file_ids=exclude_file_ids)
    if not preview.complete:
        missing_roles = [item.role for item in preview.missing]
        reasons = ", ".join(missing_roles) or ", ".join(notice.code for notice in preview.warnings if notice.code in {"excess_files", "mixed_accounts"})
        raise BRIMSetIncomplete(f"The report set cannot be combined yet: {reasons}", missing_roles)

    recognised = [member for member in preview.members if member.role is not None]
    info, summary, reused = await asyncio.to_thread(
        _combine_under_broker_lock,
        broker_id=broker_id,
        plugin=plugin,
        plugin_code=plugin_code,
        recognised=recognised,
        filename=_combined_filename(plugin, preview),
        user_id=user_id,
    )
    if not reused:
        logger.info("Combined report set", broker_id=broker_id, plugin_code=plugin_code, members=len(recognised), combined_file_id=info.file_id)
    return BRIMSetCombineResponse(combined=info, summary=summary, reused=reused)


def _combine_under_broker_lock(*, broker_id: int, plugin: BRIMProvider, plugin_code: str, recognised: List[BRIMSetMemberInfo], filename: str, user_id: Optional[int]) -> Tuple[BRIMFileInfo, Dict[str, Any], bool]:
    """Reuse, or combine and save, as one step under the broker's metadata lock (F1).

    Two analyses of one set at once (a double click, two tabs) used to build two combined files: the
    second looked for a reusable file before the first had saved its own. Holding the lock from the
    check to the save makes the second find the first's file. It runs in a worker thread: the lock
    is re-entrant within a thread, so taken on the event loop it would let both through.
    """
    member_ids = [member.file_id for member in recognised]
    with brim_provider.broker_metadata_lock(broker_id):
        reusable = brim_provider.find_reusable_combined(broker_id=broker_id, plugin_code=plugin_code, plugin_version=plugin.plugin_version, member_ids=member_ids)
        if reusable is not None:
            return reusable, brim_provider.read_combine_summary(reusable.file_id), True

        paths_by_role: Dict[str, List[Path]] = defaultdict(list)
        for member in recognised:
            path = brim_provider.get_file_path(member.file_id)
            if path is None:
                raise BRIMSetMembersNotFound(f"File {member.filename} is no longer available")
            paths_by_role[member.role].append(path)

        try:
            table = plugin.combine(dict(paths_by_role))
        except (BRIMParseError, ValueError) as exc:
            message = getattr(exc, "message", None) or str(exc)
            raise BRIMSetCombineFailed(f"The report set could not be combined: {message}") from exc
        info = brim_provider.save_combined_file(
            broker_id=broker_id,
            plugin_code=plugin_code,
            plugin_version=plugin.plugin_version,
            members=[BRIMDerivedRef(file_id=member.file_id, role=member.role, filename=member.filename) for member in recognised],
            table=table,
            filename=filename,
            user_id=user_id,
        )
        return info, table.summary, False


# =============================================================================
# PARSE
# =============================================================================


def ensure_parseable(plugin: BRIMProvider, file_info: BRIMFileInfo) -> None:
    """A report-set member is imported through its combined file, never on its own."""
    if plugin.is_report_set_plugin and file_info.kind == "original":
        required = [role.code for role in plugin.report_roles if role.required]
        raise BRIMSetRequiredError(
            f"{file_info.filename} is one export of a report set: upload it together with the other exports and import the set",
            missing_roles=required,
        )


async def apply_history(
    session: AsyncSession,
    *,
    broker_id: int,
    plugin: BRIMProvider,
    output: BRIMParseOutput,
) -> Tuple[List[BRIMCheckpoint], List[BRIMVerification], Optional[date]]:
    """Bring the broker history into the parse of a combined file (design D-S25).

    Returns the checkpoints to keep, the verifications and the history start (H0).
    On the first import H0 is the day after the first checkpoint (or the oldest
    imported row when the plugin imports the rows before it); checkpoints before
    the eve of H0 are dropped, because what precedes the history is already
    represented in LibreFolio. On a later import a checkpoint from H0 on closes a
    gap in a history that already exists: it is a ``gap``, whatever the plugin
    called the first checkpoint of its set (the plugin cannot know H0).
    """
    start = await history_start(session, broker_id=broker_id, history_tag=plugin.history_tag)
    later_import = start is not None
    if start is None:
        if plugin.pre_checkpoint_policy == "import" and output.transactions:
            start = min(tx.date for tx in output.transactions)
        elif output.checkpoints:
            start = min(checkpoint.as_of for checkpoint in output.checkpoints) + timedelta(days=1)
    if start is None:
        return list(output.checkpoints), list(output.verifications), None
    floor = start - timedelta(days=1)
    kept = [checkpoint for checkpoint in output.checkpoints if checkpoint.as_of >= floor]
    if later_import:
        kept = [_without_represented_rows(checkpoint, start) for checkpoint in kept]
        kept = [checkpoint.model_copy(update={"kind": "gap"}) if checkpoint.as_of >= start else checkpoint for checkpoint in kept]
    return kept, list(output.verifications), start


def _without_represented_rows(checkpoint: BRIMCheckpoint, start: date) -> BRIMCheckpoint:
    """On a later import, what precedes H0 is already represented in LibreFolio.

    The earlier opening correction summarises it: the explanation of the gap-fix must
    neither count those rows as missing again nor subtract the opening balance again.
    """
    rows = [row for row in checkpoint.absorbed.rows if row.as_of >= start]
    sums: Dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        sums[row.currency] += row.amount
    absorbed = BRIMAbsorbed(count=len(rows), cash=[BRIMTruthCash(currency=code, amount=amount) for code, amount in sorted(sums.items())], rows=rows, opening_cash=[])
    return checkpoint.model_copy(update={"absorbed": absorbed})
