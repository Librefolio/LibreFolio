"""
Checking a backup archive before a restore (``/backup/restore``), for administrators only.

The archive arrives as the raw body of ``PUT /backup/restore/upload``, read in pieces and written to disk as it comes:
never held in memory, never past the limit the hosting provider set (``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB``, decision 43:
413) or the free space (507). ``POST /backup/restore/stage`` then checks it in the background on a copy — unpacked,
brought to this LibreFolio's schema, checked — and the client polls ``GET /backup/restore/stage/{stage_id}`` until the
report of what a restore would do, or the code of the refusal. ``DELETE`` drops a check and its copy. One check runs at
a time. A secure backup (an ``.lfbk`` envelope, lot B4) comes with its password, checked at once: a missing or wrong
one is refused (400) and keeps the upload, for another try. A 422 never repeats the body (``api/no_echo.py``).

The restore (lot B3, ``services/platform/instance_backup/apply.py``): ``POST /backup/restore/stage/{stage_id}/confirm``
confirms the restore of a checked copy, which changes nothing yet: the next start of the server applies it, before any
step reads the data, and ends every session. ``POST /backup/restore/restart`` stops the server for that start, once its
answer is sent; whatever supervises the server starts it again. Its answer carries a one-time ticket (lot B5c): with
it in the ``X-Restore-Ticket`` header, ``GET /backup/restore/outcome`` tells the page what became of the restore,
without a session (a restore ends every session, and without ``JWT_SECRET`` every start does). ``GET /backup/restore/status`` follows the restore: waiting,
then committed, or rolled back when its first start did not complete. ``DELETE /backup/restore/pending`` drops it before
that start, with its checked copy (B-17).

None of these routes is allowed on an instance its hosting provider blocked (``api/v1/instance_block.py``): the block
lets the data leave (the backup routes), never come in. The outcome, read with its ticket, is: it starts nothing, and
it tells the page that the restore waits for the unblock.
"""

import asyncio
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, Response, status
from starlette.requests import ClientDisconnect

from backend.app.api.no_echo import NoInputEchoRoute
from backend.app.api.v1.backup.job_views import backup_error
from backend.app.api.v1.settings import require_admin
from backend.app.config import ProfileDefaultError, get_data_dir
from backend.app.config.backup import BackupConfigError, backup_max_restore_mb, backup_max_upload_mb
from backend.app.db.models import User
from backend.app.logging_config import get_logger
from backend.app.schemas.backup import (
    RestoreConfirmRequest,
    RestoreMigration,
    RestoreOutcome,
    RestoreOwnerCandidate,
    RestoreOwnerChoice,
    RestoreRestartAccepted,
    RestoreSecretCounts,
    RestoreStage,
    RestoreStageReport,
    RestoreStageRequest,
    RestoreStatus,
    RestoreTableRows,
    RestoreTotalsDifference,
    RestoreUpload,
)
from backend.app.services.platform.instance_backup import outcome, restart, restore_jobs
from backend.app.services.platform.instance_backup.apply import RestoreNotPendingError, RestoreState, RestoreStateError, RestoreStateUnreadableError, cancel_restore, prepare_restart, read_restore
from backend.app.services.platform.instance_backup.envelope import EnvelopeError
from backend.app.services.platform.instance_backup.jobs import out_of_space
from backend.app.services.platform.instance_backup.paths import BackupPathError
from backend.app.services.platform.instance_backup.staging import StagingBusyError, StagingReport, read_report

logger = get_logger(__name__)

restore_router = APIRouter(route_class=NoInputEchoRoute)

#: Pieces of the body are gathered up to this size before each write, so a large archive is not one thread hop per
#: network read.
_WRITE_CHUNK = 1024 * 1024
_MEGABYTE = 1024 * 1024

_FOLDER_UNUSABLE = {"description": "The restore folder of the data directory is a link or a file (code `restore_folder_unusable`)"}
_UPLOAD_FAILED = {"description": "The restore folder of the data directory is a link or a file (code `restore_folder_unusable`), or the archive could not be written (code `backup_upload_failed`)"}
_STAGE_NOT_STARTED = {"description": "The restore folder of the data directory is a link or a file (code `restore_folder_unusable`), or the check could not start: its folders or its state could not be written (code `stage_failed`)"}
_STAGE_NOT_FOUND = {"description": "No check has this id (code `restore_stage_not_found`)"}
_CONFIRM_FAILED = {"description": "The restore folder of the data directory is a link or a file (code `restore_folder_unusable`), the confirmation could not be written (code `restore_confirm_failed`), or the state of the restore cannot be read (code `restore_state_unreadable`): nothing confirmed"}
_CANCEL_FAILED = {"description": "The restore could not be dropped (code `restore_cancel_failed`): it still waits for the next start; or the state of the restore cannot be read (code `restore_state_unreadable`): nothing dropped"}
_OUTCOME_NOT_FOUND = {"description": "No restore outcome for this ticket: none, malformed, unknown, expired, replaced or removed, or of another restore, all alike (code `restore_outcome_not_found`)"}
_RESTART_NOT_PREPARED = {
    "description": "The restore folder of the data directory is a link or a file (code `restore_folder_unusable`), the ticket of the outcome could not be written (code `restore_restart_failed`), or the state of the restore cannot be read (code `restore_state_unreadable`): no restart"
}
_STATE_UNREADABLE = {
    "description": "The state of the restore cannot be read (code `restore_state_unreadable`, with `reason`: `io`, its owner or permissions or a disk error; `not_a_file`, a link or a folder in its place; `invalid`, no state this LibreFolio reads); whether a restore waits is not known: `dev.py backup pending` on the server says what to do"
}


def _folder_unusable() -> HTTPException:
    return backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "restore_folder_unusable", "The restore folder of the data directory is not a plain folder")


def _state_unreadable(exc: RestoreStateUnreadableError | None = None) -> HTTPException:
    """A state of the restore that cannot be used (logged by the reader): never taken for none (B-32). ``reason`` in the
    detail (B-33): the page tells it from a server down, and says what to do."""
    refusal = backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "restore_state_unreadable", "The state of the restore cannot be read: the server's log has the cause")
    if exc is not None:
        refusal.detail = {**refusal.detail, "reason": exc.reason}
    return refusal


def _declared_size(request: Request) -> int | None:
    raw = request.headers.get("content-length", "")
    return int(raw) if raw.isascii() and raw.isdigit() else None


@restore_router.put(
    "/restore/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=RestoreUpload,
    responses={
        400: {"description": "The body is empty (code `backup_upload_empty`), or the client left before its end (code `backup_upload_incomplete`)"},
        413: {"description": "The archive is larger than the limit the hosting provider set (code `backup_too_large`, with `limit_mb`)"},
        500: _UPLOAD_FAILED,
        503: {"description": "The limit of this instance cannot be read (code `backup_upload_unavailable`)"},
        507: {"description": "Not enough free space for the archive (code `backup_no_space`)"},
    },
    openapi_extra={"requestBody": {"required": True, "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}},
)
async def upload_restore_archive(request: Request, _admin: User = Depends(require_admin)) -> RestoreUpload:
    """Receive a backup archive for a restore, as the raw request body. Check it next with ``POST /backup/restore/stage``."""
    limit_mb, max_bytes = _upload_limit()
    try:
        writer = await asyncio.to_thread(restore_jobs.UploadWriter, get_data_dir(), max_bytes=max_bytes, declared=_declared_size(request))
    except BackupPathError:
        raise _folder_unusable() from None
    except (restore_jobs.UploadTooLargeError, restore_jobs.UploadNoSpaceError, OSError) as exc:
        raise _upload_failure(exc, limit_mb) from None
    try:
        uploaded = await _receive(request, writer)
    except BaseException as exc:
        await asyncio.to_thread(writer.abort)
        failure = _upload_failure(exc, limit_mb)
        if failure is exc:
            raise
        raise failure from None
    return RestoreUpload(upload_id=uploaded.upload_id, size=uploaded.size, kind=uploaded.kind)


def _upload_limit() -> tuple[int, int | None]:
    """The limit in megabytes (0: none), and in bytes (``None``: none). 503 when it cannot be read."""
    try:
        limit_mb = backup_max_upload_mb()
    except (BackupConfigError, ProfileDefaultError) as exc:
        logger.error("The upload limit of a restore cannot be read", error=str(exc))
        raise backup_error(status.HTTP_503_SERVICE_UNAVAILABLE, "backup_upload_unavailable", "The upload limit of this instance cannot be read") from None
    return limit_mb, (limit_mb * _MEGABYTE if limit_mb else None)


def _restore_limit() -> int | None:
    """The most an archive may unpack to in a check, in bytes (``None``: none; B-35). 503 when it cannot be read."""
    try:
        limit_mb = backup_max_restore_mb()
    except (BackupConfigError, ProfileDefaultError) as exc:
        logger.error("The restore limit cannot be read", error=str(exc))
        raise backup_error(status.HTTP_503_SERVICE_UNAVAILABLE, "backup_restore_unavailable", "The restore limit of this instance cannot be read") from None
    return limit_mb * _MEGABYTE if limit_mb else None


async def _receive(request: Request, writer: restore_jobs.UploadWriter) -> restore_jobs.RestoreUploaded:
    """Write the body as it comes, gathered in pieces of ``_WRITE_CHUNK``, each write in a worker thread."""
    buffer = bytearray()
    async for piece in request.stream():
        buffer += piece
        if len(buffer) >= _WRITE_CHUNK:
            await asyncio.to_thread(writer.write, bytes(buffer))
            buffer.clear()
    if buffer:
        await asyncio.to_thread(writer.write, bytes(buffer))
    return await asyncio.to_thread(writer.finish)


def _upload_failure(exc: BaseException, limit_mb: int) -> BaseException:
    """The answer an upload failure gets; any other failure is returned as it is, to be raised again."""
    if isinstance(exc, restore_jobs.UploadTooLargeError):
        return HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail={"code": "backup_too_large", "message": f"The archive is larger than {limit_mb} MB", "limit_mb": limit_mb})
    if isinstance(exc, restore_jobs.UploadNoSpaceError):
        return backup_error(status.HTTP_507_INSUFFICIENT_STORAGE, "backup_no_space", "Not enough free space for the archive")
    if isinstance(exc, restore_jobs.UploadEmptyError):
        return backup_error(status.HTTP_400_BAD_REQUEST, "backup_upload_empty", "The request carried no archive")
    if isinstance(exc, ClientDisconnect):
        return backup_error(status.HTTP_400_BAD_REQUEST, "backup_upload_incomplete", "The upload ended before the archive did")
    if isinstance(exc, OSError):
        logger.error("A backup archive for a restore could not be written", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        return backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "backup_upload_failed", "The archive could not be written")
    return exc


def _report_view(report: StagingReport) -> RestoreStageReport:
    return RestoreStageReport(
        backup_created_at=report.backup.created_at,
        backup_app_version=report.backup.app_version,
        backup_origin=report.backup.origin,
        backup_revision=report.backup.alembic_revision,
        app_version=report.app_version,
        head_revision=report.head_revision,
        action=report.action,
        migrations=[RestoreMigration(revision=migration.revision, message=migration.message) for migration in report.migrations],
        post_migration_fixes=report.post_migration_fixes,
        tables={name: RestoreTableRows(before=rows.before, after=rows.after) for name, rows in report.tables.items()},
        foreign_key_violations_before=report.foreign_key_violations_before,
        foreign_key_violations_after=report.foreign_key_violations_after,
        files=report.files,
        files_size=report.files_size,
        database_size=report.database_size,
        instance_key_included=report.instance_key_included,
        encrypted=report.encrypted,
        secrets_rekeyed=report.secrets_rekeyed,
        secrets_unreadable=RestoreSecretCounts(system=report.secrets_unreadable.system, user=report.secrets_unreadable.user),
        administrators=report.administrators,
        warnings=report.warnings,
        control_totals=report.control_totals,
        control_totals_differences=[RestoreTotalsDifference(**line.model_dump()) for line in report.control_totals_differences],
        control_totals_differences_count=report.control_totals_differences_count,
        blockers=report.blockers,
        restorable=report.restorable,
        expires_at=report.expires_at,
        owner_choice=_owner_choice_view(report),
    )


def _owner_choice_view(report: StagingReport) -> RestoreOwnerChoice | None:
    """B5-1: the accounts of the backup the owner may choose, with their addresses, on a managed instance only; the
    administrators' route alone shows it (never the hosting panel, never a log)."""
    from backend.app.services.accounts.user_service import same_email  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.apply import owner_choices  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.owner import configured_owner_email, owner_choice_required  # noqa: PLC0415

    if not owner_choice_required():
        return None
    owner_email = configured_owner_email()
    if owner_email is None:
        return None
    _allowed, forced = owner_choices(report.owner_candidates, owner_email)
    # Every candidate of the report, so the owner sees the backup's administrators; when one holds the owner's address
    # it is the only choice (forced_user_id), and the confirmation refuses any other (apply.confirm_restore).
    candidates = [
        RestoreOwnerCandidate(
            user_id=candidate.user_id,
            username=candidate.username,
            email=candidate.email,
            owner_email=candidate.email is not None and same_email(candidate.email, owner_email),
            administrator=candidate.is_superuser and candidate.is_active,
            is_superuser=candidate.is_superuser,
            is_active=candidate.is_active,
        )
        for candidate in report.owner_candidates
    ]
    return RestoreOwnerChoice(required=True, owner_email=owner_email, forced_user_id=forced, candidates=candidates)


def _stage_view(check: restore_jobs.RestoreCheck, *, reader: str | None = None) -> RestoreStage:
    """A check as the API shows it. ``reader``: the username of the administrator who reads it; when the backup has no
    such administrator, its report ends with ``confirming_account_not_in_backup`` (L3), for that reader only."""
    report = None
    if check.status == "done":
        try:
            report = _report_view(read_report(get_data_dir(), check.stage_id))
        except FileNotFoundError:
            logger.warning("A finished restore check has no readable report", stage_id=check.stage_id)
    if report is not None and reader is not None and reader not in report.administrators:
        report = report.model_copy(update={"warnings": [*report.warnings, "confirming_account_not_in_backup"]})
    return RestoreStage(
        stage_id=check.stage_id,
        status=check.status,
        phase=check.phase,
        done_bytes=check.done_bytes,
        total_bytes=check.total_bytes,
        created_at=check.created_at,
        finished_at=check.finished_at,
        error_code=check.error_code,
        report=report,
    )


@restore_router.post(
    "/restore/stage",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RestoreStage,
    responses={
        400: {"description": "A secure backup without its password (code `password_required`), with a wrong one (code `wrong_password`), or not a whole envelope (code `envelope_damaged`): the upload stays, for another try"},
        404: {"description": "No uploaded archive has this id: never received, replaced, or already checked (code `backup_upload_not_found`)"},
        409: {"description": "Another archive is being checked (code `restore_busy`), or a secure backup this LibreFolio cannot read: update it first (code `envelope_unsupported`)"},
        500: _STAGE_NOT_STARTED,
        503: {"description": "The restore limit of this instance cannot be read (code `backup_restore_unavailable`): no check started, the upload kept"},
        507: {"description": "Not enough free space to start the check (code `no_space`, the code of a check that runs out of space)"},
    },
)
def start_restore_check(body: RestoreStageRequest, _admin: User = Depends(require_admin)) -> RestoreStage:
    """Check an uploaded archive on a copy, in the background, and return the check to poll. The instance is not touched.

    A secure backup's password is checked first, in this request; it is never kept, logged or sent back. A full disk
    before the check starts answers 507 ``no_space``; any other failure to write its folders or its state, 500
    ``stage_failed``, the cause in the log (B-30). A restore limit that cannot be read answers 503
    ``backup_restore_unavailable`` and starts nothing (B-35).
    """
    password = body.password.get_secret_value() if body.password is not None else None
    max_unpacked = _restore_limit()
    try:
        return _stage_view(restore_jobs.start_check(body.upload_id, password=password, max_unpacked=max_unpacked))
    except restore_jobs.UploadNotFoundError:
        raise backup_error(status.HTTP_404_NOT_FOUND, "backup_upload_not_found", "No uploaded archive has this id") from None
    except StagingBusyError:
        raise backup_error(status.HTTP_409_CONFLICT, "restore_busy", "Another archive is being checked") from None
    except restore_jobs.PasswordRequiredError:
        raise backup_error(status.HTTP_400_BAD_REQUEST, "password_required", "The backup is protected by a password") from None
    except EnvelopeError as exc:
        code = status.HTTP_409_CONFLICT if exc.code == "envelope_unsupported" else status.HTTP_400_BAD_REQUEST
        raise backup_error(code, exc.code, str(exc)) from None
    except BackupPathError:
        raise _folder_unusable() from None
    except OSError as exc:
        if out_of_space(exc):
            logger.warning("A check of a backup archive could not start: not enough free space")
            raise backup_error(status.HTTP_507_INSUFFICIENT_STORAGE, "no_space", "Not enough free space to check the archive") from None
        logger.error("A check of a backup archive could not start", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "stage_failed", "The check could not start: the server's log has the cause") from None


@restore_router.get("/restore/stage/{stage_id}", response_model=RestoreStage, responses={404: _STAGE_NOT_FOUND})
def get_restore_check(stage_id: str, admin: User = Depends(require_admin)) -> RestoreStage:
    """The state of a check: its phase and progress while it runs, then its report, or the code of its refusal. The
    report warns the administrator who reads it when the backup does not hold their account (L3)."""
    try:
        return _stage_view(restore_jobs.read_check(stage_id), reader=admin.username)
    except restore_jobs.CheckNotFoundError:
        raise backup_error(status.HTTP_404_NOT_FOUND, "restore_stage_not_found", "No check has this id") from None


@restore_router.delete(
    "/restore/stage/{stage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: _STAGE_NOT_FOUND, 409: {"description": "The check still runs (code `restore_stage_running`), or a restore waits to apply its copy (code `restore_pending`)"}},
)
def delete_restore_check(stage_id: str, _admin: User = Depends(require_admin)) -> Response:
    """Drop an ended check and its copy: the archive is not restored."""
    try:
        restore_jobs.remove_check(stage_id)
    except restore_jobs.CheckNotFoundError:
        raise backup_error(status.HTTP_404_NOT_FOUND, "restore_stage_not_found", "No check has this id") from None
    except restore_jobs.CheckRunningError:
        raise backup_error(status.HTTP_409_CONFLICT, "restore_stage_running", "The check still runs") from None
    except restore_jobs.CheckPendingError:
        raise backup_error(status.HTTP_409_CONFLICT, "restore_pending", "A restore waits to apply this copy: cancel it first") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# The restore: confirmed, applied at the next start (lot B3)
# =============================================================================

#: The answer of each refusal of a confirmation; any other ``RestoreStateError`` is a conflict.
_CONFIRM_STATUS = {"restore_stage_not_found": status.HTTP_404_NOT_FOUND, "restore_stage_expired": status.HTTP_410_GONE, "owner_choice_not_applicable": status.HTTP_400_BAD_REQUEST}
_NOT_PENDING = "No restore waits for the next start"
_IN_PROGRESS = frozenset({"applying", "applied", "rolling_back"})


def _readable_limit_mb() -> int | None:
    """The upload limit in megabytes (0: none), or ``None`` when it cannot be read (logged, as the upload logs it)."""
    try:
        return backup_max_upload_mb()
    except (BackupConfigError, ProfileDefaultError) as exc:
        logger.error("The upload limit of a restore cannot be read", error=str(exc))
        return None


def _status_view(state: RestoreState | None) -> RestoreStatus:
    limit = _readable_limit_mb()
    if state is None:
        return RestoreStatus(state="none", upload_limit_mb=limit)
    return RestoreStatus(
        state="in_progress" if state.status in _IN_PROGRESS else state.status,
        stage_id=state.stage_id,
        confirmed_at=state.confirmed_at,
        confirmed_by=state.confirmed_by,
        confirmed_via=state.confirmed_via,
        backup_created_at=state.backup_created_at,
        backup_app_version=state.backup_app_version,
        action=state.action,
        finished_at=state.finished_at,
        reason=state.reason,
        waiting=state.waiting,
        upload_limit_mb=limit,
    )


@restore_router.post(
    "/restore/stage/{stage_id}/confirm",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RestoreStatus,
    responses={
        400: {"description": "An owner's account named on an instance that is not managed (code `owner_choice_not_applicable`): nothing confirmed"},
        404: {"description": "No check has this id, or its copy is gone (code `restore_stage_not_found`)"},
        409: {
            "description": "The check still runs (code `restore_stage_running`); it refused the archive, or found what forbids a restore (code `restore_not_restorable`); LibreFolio was updated since the check (code `restore_stage_outdated`); or another restore waits (code `restore_already_pending`). On a managed instance (B5-1): no owner's account named (code `owner_choice_required`), one the report does not offer (code `owner_choice_invalid`), no `LIBREFOLIO_ADMIN_EMAIL` (code `owner_email_not_set`), the owner's address changed since the check (code `restore_stage_outdated`), or the backup holds two accounts on one address or one name, the owner's address as another account's name, or an administrator still waiting for its setup link while no account holds the owner's address (code `owner_conflict`)"
        },
        410: {"description": "The check expired: check the archive again (code `restore_stage_expired`)"},
        500: _CONFIRM_FAILED,
        507: {"description": "Not enough free space to confirm the restore (code `backup_no_space`): nothing confirmed"},
    },
)
def confirm_restore_check(stage_id: str, body: RestoreConfirmRequest | None = None, admin: User = Depends(require_admin)) -> RestoreStatus:
    """Confirm the restore of a checked archive. Nothing changes yet: the next start of the server applies it, and ends
    every session; ``POST /backup/restore/restart`` stops the server for that start. A full disk answers 507
    ``backup_no_space``, any other failure to write the confirmation 500 ``restore_confirm_failed``: either way nothing
    is confirmed, since the state is written last and atomically (B-31). A state that cannot be read answers 500
    ``restore_state_unreadable``: a restore that may be half applied is never written over (B-32)."""
    try:
        owner_user_id = body.owner_user_id if body is not None else None
        return _status_view(restore_jobs.confirm_check(stage_id, confirmed_by=admin.username, owner_user_id=owner_user_id, data_dir=get_data_dir()))
    except restore_jobs.CheckNotFoundError:
        raise backup_error(status.HTTP_404_NOT_FOUND, "restore_stage_not_found", "No check has this id") from None
    except restore_jobs.CheckRunningError:
        raise backup_error(status.HTTP_409_CONFLICT, "restore_stage_running", "The check still runs") from None
    except RestoreStateUnreadableError as exc:
        raise _state_unreadable(exc) from None
    except RestoreStateError as exc:
        raise backup_error(_CONFIRM_STATUS.get(exc.code, status.HTTP_409_CONFLICT), exc.code, str(exc)) from None
    except BackupPathError:
        raise _folder_unusable() from None
    except OSError as exc:
        if out_of_space(exc):
            logger.warning("A restore could not be confirmed: not enough free space")
            raise backup_error(status.HTTP_507_INSUFFICIENT_STORAGE, "backup_no_space", "Not enough free space to confirm the restore") from None
        logger.error("A restore could not be confirmed", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "restore_confirm_failed", "The restore could not be confirmed: the server's log has the cause") from None


@restore_router.get("/restore/status", response_model=RestoreStatus, responses={500: _STATE_UNREADABLE})
def get_restore_status(_admin: User = Depends(require_admin)) -> RestoreStatus:
    """The restore waiting for the next start, the one being applied, or the last one that ended; ``none`` when there was
    none. A state the file system does not let be read answers 500 ``restore_state_unreadable``, never ``none``: a
    restore may wait behind it (B-32)."""
    try:
        return _status_view(read_restore(get_data_dir()))
    except RestoreStateUnreadableError as exc:
        raise _state_unreadable(exc) from None


@restore_router.delete("/restore/pending", status_code=status.HTTP_204_NO_CONTENT, responses={404: {"description": f"{_NOT_PENDING} (code `restore_not_pending`)"}, 500: _CANCEL_FAILED})
def cancel_pending_restore(_admin: User = Depends(require_admin)) -> Response:
    """Drop the restore waiting for the next start, with its checked copy, as ``backup pending --cancel`` does: the data
    stays as it is. A failure before the restore is dropped answers 500 ``restore_cancel_failed`` and leaves it waiting;
    a copy that cannot be removed afterwards is only logged (B-31). A state that cannot be read answers 500
    ``restore_state_unreadable``, nothing dropped (B-32)."""
    try:
        cancel_restore(data_dir=get_data_dir(), drop_copy=True)
    except RestoreNotPendingError:
        raise backup_error(status.HTTP_404_NOT_FOUND, "restore_not_pending", _NOT_PENDING) from None
    except RestoreStateUnreadableError as exc:
        raise _state_unreadable(exc) from None
    except OSError as exc:
        logger.error("A pending restore could not be cancelled", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "restore_cancel_failed", "The restore could not be cancelled: the server's log has the cause") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@restore_router.post(
    "/restore/restart",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RestoreRestartAccepted,
    responses={409: {"description": f"{_NOT_PENDING} (code `restore_not_pending`)"}, 500: _RESTART_NOT_PREPARED},
)
def restart_for_restore(background_tasks: BackgroundTasks, response: Response, _admin: User = Depends(require_admin)) -> RestoreRestartAccepted:
    """Stop the server once this answer is sent, so that its next start applies the restore waiting. Whatever supervises
    the server (Docker, systemd, a hosting provider) starts it again; without one it stays stopped until someone does.

    The answer carries a one-time ticket, valid one hour: ``GET /backup/restore/outcome`` with it tells what became of the
    restore, without a session. A new restart request replaces it."""
    data_dir = get_data_dir()
    try:
        state, ticket = prepare_restart(data_dir=data_dir)
    except RestoreNotPendingError:
        raise backup_error(status.HTTP_409_CONFLICT, "restore_not_pending", _NOT_PENDING) from None
    except RestoreStateUnreadableError as exc:
        raise _state_unreadable(exc) from None
    except BackupPathError:
        raise _folder_unusable() from None
    except OSError as exc:
        logger.error("The ticket of the restore's outcome could not be written: no restart", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "restore_restart_failed", "The restart could not be prepared: the server's log has the cause") from None
    background_tasks.add_task(_restart)
    response.headers["Cache-Control"] = "no-store"
    return RestoreRestartAccepted(**_status_view(state).model_dump(), outcome_ticket=ticket)


@restore_router.get("/restore/outcome", response_model=RestoreOutcome, responses={404: _OUTCOME_NOT_FOUND})
def get_restore_outcome(response: Response, x_restore_ticket: str | None = Header(default=None, alias="X-Restore-Ticket")) -> RestoreOutcome:
    """What became of a restore, for the page that asked its restart: no session (a restore ends every session, and
    without ``JWT_SECRET`` every start does), the one-time ticket of the restart in the ``X-Restore-Ticket`` header
    instead, never in the URL. The same 404 for every ticket that does not give it. The outcome can be read again until
    the ticket expires, a final one included (decision N53). The ticket comes first: the state of the restore is read
    only for the ticket of a restart not expired, so no other caller makes LibreFolio read it, nor log that it cannot
    (B-41)."""
    data_dir = get_data_dir()
    found = outcome.read_outcome(x_restore_ticket, lambda: _state_for_outcome(data_dir), data_dir=data_dir)
    if found is None:
        raise backup_error(status.HTTP_404_NOT_FOUND, "restore_outcome_not_found", "No restore outcome for this ticket")
    response.headers["Cache-Control"] = "no-store"
    return found


def _state_for_outcome(data_dir: Path) -> RestoreState | None:
    """The state of the restore, for the holder of the ticket of its restart: one the file system does not let be read
    is none there, logged by the reader, so the holder learns no more than with any other ticket (B-32)."""
    try:
        return read_restore(data_dir)
    except RestoreStateUnreadableError:
        return None


def _restart() -> None:
    restart.request_restart()
