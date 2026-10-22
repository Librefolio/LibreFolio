"""What the routes of the instance backup share: a job as the API shows it, and the errors with their stable codes.

``instance.py`` (administrators, with a session) and ``panel.py`` (a hosting panel, with a token) run the same jobs of
``services/platform/instance_backup/jobs.py``; only the caller differs. A caller limited to one ``origin`` sees only the
jobs started with it: any other job id answers as one that does not exist.
"""

from fastapi import HTTPException, Response, status
from fastapi.responses import FileResponse

from backend.app.logging_config import get_logger
from backend.app.schemas.backup import InstanceBackupJob
from backend.app.services.platform.instance_backup import jobs
from backend.app.services.platform.instance_backup.envelope import FILE_SUFFIX
from backend.app.services.platform.instance_backup.manifest import BackupOrigin
from backend.app.services.platform.instance_backup.paths import BackupPathError
from backend.app.services.platform.instance_backup.sealed import FILE_SUFFIX as SEALED_SUFFIX

logger = get_logger(__name__)

NOT_FOUND = {"description": "No backup job has this id, or its archive is gone (code `backup_job_not_found`)"}
START_RESPONSES = {
    409: {"description": "Another backup is running (code `backup_busy`). The detail adds `job_id` and `origin` of the running backup when the caller can read it: the Backup tab always, the hosting panel for a backup of its own (B-8)"},
    500: {"description": "The backup could not start: the backups folder of the data directory is a link or a file (code `backup_folder_unusable`), or it cannot be written (code `backup_failed`)"},
    507: {"description": "Not enough free space to start the backup (code `backup_no_space`)"},
}
FILE_RESPONSES = {
    200: {"content": {"application/zip": {}, "application/octet-stream": {}, "application/x-tar": {}}, "description": "The backup archive: a .zip, the .lfbk envelope of a secure backup, or the .tar of a hosting panel's sealed one"},
    404: NOT_FOUND,
    409: {"description": "The job has not produced an archive: still running, or failed (code `backup_job_not_ready`)"},
}
DELETE_RESPONSES = {404: NOT_FOUND, 409: {"description": "The job is still running (code `backup_job_running`)"}}


def backup_error(status_code: int, code: str, message: str) -> HTTPException:
    """An error whose ``detail`` carries a stable ``code`` and an English ``message``, never a path or a system error."""
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def job_view(job: jobs.BackupJob) -> InstanceBackupJob:
    """The job as the API shows it: the archive's SHA-256 once done (L3), never the list of the files left out."""
    return InstanceBackupJob(
        job_id=job.job_id,
        status=job.status,
        phase=job.phase,
        done_bytes=job.done_bytes,
        total_bytes=job.total_bytes,
        created_at=job.created_at,
        finished_at=job.finished_at,
        file_name=job.file_name,
        file_size=job.file_size,
        file_sha256=job.file_sha256 if job.status == "done" else None,
        warnings=list(job.warnings),
        error_code=job.error_code,
        encrypted=job.encrypted,
        instance_key_included=job.instance_key_included,
        sealed=job.sealed,
        sealed_recipients=list(job.sealed_recipients),
    )


def start_job(origin: BackupOrigin, password: str | None = None, recipients: tuple[str, ...] | None = None) -> InstanceBackupJob:
    """Start a backup in the background; its first state. 409 while another runs, 507 on a full disk, 500 when it cannot
    start.

    ``password``: a secure backup (the Backup tab only; the hosting panel's backups never take one). ``recipients``: a
    sealed backup (the hosting panel's, L3).
    """
    try:
        job = jobs.start_backup(origin=origin, password=password, recipients=recipients) if recipients else jobs.start_backup(origin=origin, password=password)
    except jobs.BackupBusyError as exc:
        refusal = backup_error(status.HTTP_409_CONFLICT, "backup_busy", "Another backup is running")
        running = exc.running
        # B-8: the running backup, to a caller that can read it, so the Backup tab follows one whose start answer was lost:
        # the tab reads every job, the hosting panel only its own.
        if running is not None and (origin == "ui" or running.origin == origin):
            refusal.detail = {**refusal.detail, "job_id": running.job_id, "origin": running.origin}
        raise refusal from None
    except BackupPathError:
        logger.error("Instance backup could not start: the backups folder of the data directory is not a plain folder", origin=origin)
        raise backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "backup_folder_unusable", "The backups folder of the data directory is not a plain folder") from None
    except OSError as exc:
        if jobs.out_of_space(exc):
            logger.warning("Instance backup could not start: not enough free space", origin=origin)
            raise backup_error(status.HTTP_507_INSUFFICIENT_STORAGE, "backup_no_space", "Not enough free space to start the backup") from None
        logger.error("Instance backup could not start", origin=origin, error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "backup_failed", "The backup could not start") from None
    return job_view(job)


def _not_found(message: str = "No such backup job") -> HTTPException:
    return backup_error(status.HTTP_404_NOT_FOUND, "backup_job_not_found", message)


def _job(job_id: str, origin: BackupOrigin | None) -> jobs.BackupJob:
    """The job ``job_id``, when ``origin`` is None or the job's own: otherwise, and when there is none, 404."""
    try:
        job = jobs.get_job(job_id)
    except jobs.BackupJobNotFoundError:
        raise _not_found() from None
    if origin is not None and job.origin != origin:
        raise _not_found()
    return job


def read_job(job_id: str, *, origin: BackupOrigin | None = None) -> InstanceBackupJob:
    """The state of a job; 404 when there is none (or not of ``origin``)."""
    return job_view(_job(job_id, origin))


def job_file(job_id: str, *, origin: BackupOrigin | None = None) -> FileResponse:
    """The archive of a finished job, never cached; 404 when there is none (or not of ``origin``), 409 before its end."""
    if origin is not None:
        _job(job_id, origin)
    try:
        path, name = jobs.job_archive(job_id)
    except jobs.BackupJobNotFoundError:
        raise _not_found("No such backup archive") from None
    except jobs.BackupJobStateError:
        raise backup_error(status.HTTP_409_CONFLICT, "backup_job_not_ready", "The backup has no archive yet") from None
    # A secure backup's envelope is not a zip: a browser or a mail filter must not take it for one. A sealed one is a tar.
    media_type = "application/x-tar" if name.endswith(SEALED_SUFFIX) else "application/octet-stream" if name.endswith(FILE_SUFFIX) else "application/zip"
    return FileResponse(path, media_type=media_type, filename=name, headers={"Cache-Control": "no-store"})


def remove_job(job_id: str, *, origin: BackupOrigin | None = None) -> Response:
    """Delete a finished job and its archive; 404 when there is none (or not of ``origin``), 409 while it runs."""
    if origin is not None:
        _job(job_id, origin)
    try:
        jobs.delete_job(job_id)
    except jobs.BackupJobNotFoundError:
        raise _not_found() from None
    except jobs.BackupJobStateError:
        raise backup_error(status.HTTP_409_CONFLICT, "backup_job_running", "The backup is still running") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
