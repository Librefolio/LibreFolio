"""
Checking a backup archive before a restore (``/backup/restore``), for administrators only.

The archive arrives as the raw body of ``PUT /backup/restore/upload``, read in pieces and written to disk as it comes:
never held in memory, never past the limit the hosting provider set (``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB``, decision 43:
413) or the free space (507). ``POST /backup/restore/stage`` then checks it in the background on a copy — unpacked,
brought to this LibreFolio's schema, checked — and the client polls ``GET /backup/restore/stage/{stage_id}`` until the
report of what a restore would do, or the code of the refusal. ``DELETE`` drops a check and its copy. One check runs at
a time. The restore itself, from a checked copy, is lot B3.

None of these routes is allowed on an instance its hosting provider blocked (``api/v1/instance_block.py``): the block
lets the data leave (the backup routes), never come in.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from starlette.requests import ClientDisconnect

from backend.app.api.v1.backup.job_views import backup_error
from backend.app.api.v1.settings import require_admin
from backend.app.config import get_data_dir
from backend.app.config.backup import BackupConfigError, backup_max_upload_mb
from backend.app.db.models import User
from backend.app.logging_config import get_logger
from backend.app.schemas.backup import RestoreMigration, RestoreStage, RestoreStageReport, RestoreStageRequest, RestoreTableRows, RestoreUpload
from backend.app.services.platform.instance_backup import restore_jobs
from backend.app.services.platform.instance_backup.paths import BackupPathError
from backend.app.services.platform.instance_backup.staging import StagingBusyError, StagingReport, read_report

logger = get_logger(__name__)

restore_router = APIRouter()

#: Pieces of the body are gathered up to this size before each write, so a large archive is not one thread hop per
#: network read.
_WRITE_CHUNK = 1024 * 1024
_MEGABYTE = 1024 * 1024

_FOLDER_UNUSABLE = {"description": "The restore folder of the data directory is a link or a file (code `restore_folder_unusable`)"}
_UPLOAD_FAILED = {"description": "The restore folder of the data directory is a link or a file (code `restore_folder_unusable`), or the archive could not be written (code `backup_upload_failed`)"}
_STAGE_NOT_FOUND = {"description": "No check has this id (code `restore_stage_not_found`)"}


def _folder_unusable() -> HTTPException:
    return backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "restore_folder_unusable", "The restore folder of the data directory is not a plain folder")


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
    return RestoreUpload(upload_id=uploaded.upload_id, size=uploaded.size)


def _upload_limit() -> tuple[int, int | None]:
    """The limit in megabytes (0: none), and in bytes (``None``: none). 503 when it cannot be read."""
    try:
        limit_mb = backup_max_upload_mb()
    except BackupConfigError as exc:
        logger.error("The upload limit of a restore cannot be read", error=str(exc))
        raise backup_error(status.HTTP_503_SERVICE_UNAVAILABLE, "backup_upload_unavailable", "The upload limit of this instance cannot be read") from None
    return limit_mb, (limit_mb * _MEGABYTE if limit_mb else None)


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
        administrators=report.administrators,
        warnings=report.warnings,
        blockers=report.blockers,
        restorable=report.restorable,
        expires_at=report.expires_at,
    )


def _stage_view(check: restore_jobs.RestoreCheck) -> RestoreStage:
    report = None
    if check.status == "done":
        try:
            report = _report_view(read_report(get_data_dir(), check.stage_id))
        except FileNotFoundError:
            logger.warning("A finished restore check has no readable report", stage_id=check.stage_id)
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
        404: {"description": "No uploaded archive has this id: never received, replaced, or already checked (code `backup_upload_not_found`)"},
        409: {"description": "Another archive is being checked (code `restore_busy`)"},
        500: _FOLDER_UNUSABLE,
    },
)
def start_restore_check(body: RestoreStageRequest, _admin: User = Depends(require_admin)) -> RestoreStage:
    """Check an uploaded archive on a copy, in the background, and return the check to poll. The instance is not touched."""
    try:
        return _stage_view(restore_jobs.start_check(body.upload_id))
    except restore_jobs.UploadNotFoundError:
        raise backup_error(status.HTTP_404_NOT_FOUND, "backup_upload_not_found", "No uploaded archive has this id") from None
    except StagingBusyError:
        raise backup_error(status.HTTP_409_CONFLICT, "restore_busy", "Another archive is being checked") from None
    except BackupPathError:
        raise _folder_unusable() from None


@restore_router.get("/restore/stage/{stage_id}", response_model=RestoreStage, responses={404: _STAGE_NOT_FOUND})
def get_restore_check(stage_id: str, _admin: User = Depends(require_admin)) -> RestoreStage:
    """The state of a check: its phase and progress while it runs, then its report, or the code of its refusal."""
    try:
        return _stage_view(restore_jobs.read_check(stage_id))
    except restore_jobs.CheckNotFoundError:
        raise backup_error(status.HTTP_404_NOT_FOUND, "restore_stage_not_found", "No check has this id") from None


@restore_router.delete(
    "/restore/stage/{stage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: _STAGE_NOT_FOUND, 409: {"description": "The check still runs (code `restore_stage_running`)"}},
)
def delete_restore_check(stage_id: str, _admin: User = Depends(require_admin)) -> Response:
    """Drop an ended check and its copy: the archive is not restored."""
    try:
        restore_jobs.remove_check(stage_id)
    except restore_jobs.CheckNotFoundError:
        raise backup_error(status.HTTP_404_NOT_FOUND, "restore_stage_not_found", "No check has this id") from None
    except restore_jobs.CheckRunningError:
        raise backup_error(status.HTTP_409_CONFLICT, "restore_stage_running", "The check still runs") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
