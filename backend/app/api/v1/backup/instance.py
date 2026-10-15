"""
Backup of the whole instance (``/backup/instance``): an archive of the data directory, built in the background.

The archive holds the database (a consistent copy), the uploaded files, the broker reports and the risk scenarios, with
a manifest: unpacked into an empty data directory it is the instance again. It holds every user's data, so every route
here is for administrators only. ``POST /backup/instance`` starts a job and answers at once; the client polls the job,
then downloads its archive, which the server keeps for an hour (or until ``DELETE``). One backup runs at a time.

``backup_router`` (``__init__.py``) gives these routes the ``/backup`` prefix and the ``Backup & Export`` tag, before the
per-series exports of ``exports.py``. Errors carry a stable ``code`` in ``detail``.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse

from backend.app.api.v1.settings import require_admin
from backend.app.db.models import User
from backend.app.logging_config import get_logger
from backend.app.schemas.backup import InstanceBackupJob
from backend.app.services.platform.instance_backup import jobs
from backend.app.services.platform.instance_backup.paths import BackupPathError

logger = get_logger(__name__)

instance_router = APIRouter()

_NOT_FOUND = {"description": "No backup job has this id, or its archive is gone (code `backup_job_not_found`)"}


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _job_response(job: jobs.BackupJob) -> InstanceBackupJob:
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
        warnings=list(job.warnings),
        error_code=job.error_code,
    )


@instance_router.post(
    "/instance",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=InstanceBackupJob,
    responses={
        409: {"description": "Another backup is running (code `backup_busy`)"},
        500: {"description": "The backup could not start: the backups folder of the data directory is a link or a file (code `backup_folder_unusable`), or it cannot be written (code `backup_failed`)"},
    },
)
def start_instance_backup(_admin: User = Depends(require_admin)) -> InstanceBackupJob:
    """Start a backup of the whole instance in the background, and return the job to poll. Administrators only."""
    try:
        job = jobs.start_backup(origin="ui")
    except jobs.BackupBusyError:
        raise _error(status.HTTP_409_CONFLICT, "backup_busy", "Another backup is running") from None
    except BackupPathError:
        logger.error("Instance backup could not start: the backups folder of the data directory is not a plain folder")
        raise _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "backup_folder_unusable", "The backups folder of the data directory is not a plain folder") from None
    except OSError as exc:
        logger.error("Instance backup could not start", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "backup_failed", "The backup could not start") from None
    return _job_response(job)


@instance_router.get("/instance/jobs/{job_id}", response_model=InstanceBackupJob, responses={404: _NOT_FOUND})
def get_instance_backup_job(job_id: str, _admin: User = Depends(require_admin)) -> InstanceBackupJob:
    """The state of a backup job: its phase and progress while it runs, its archive or its error once it ends."""
    try:
        return _job_response(jobs.get_job(job_id))
    except jobs.BackupJobNotFoundError:
        raise _error(status.HTTP_404_NOT_FOUND, "backup_job_not_found", "No such backup job") from None


@instance_router.get(
    "/instance/jobs/{job_id}/file",
    response_class=FileResponse,
    responses={
        200: {"content": {"application/zip": {}}, "description": "The backup archive"},
        404: _NOT_FOUND,
        409: {"description": "The job has not produced an archive: still running, or failed (code `backup_job_not_ready`)"},
    },
)
def download_instance_backup(job_id: str, _admin: User = Depends(require_admin)) -> FileResponse:
    """Download the archive of a finished backup job. It holds every user's data: keep it private."""
    try:
        path, name = jobs.job_archive(job_id)
    except jobs.BackupJobNotFoundError:
        raise _error(status.HTTP_404_NOT_FOUND, "backup_job_not_found", "No such backup archive") from None
    except jobs.BackupJobStateError:
        raise _error(status.HTTP_409_CONFLICT, "backup_job_not_ready", "The backup has no archive yet") from None
    return FileResponse(path, media_type="application/zip", filename=name, headers={"Cache-Control": "no-store"})


@instance_router.delete(
    "/instance/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: _NOT_FOUND, 409: {"description": "The job is still running (code `backup_job_running`)"}},
)
def delete_instance_backup_job(job_id: str, _admin: User = Depends(require_admin)) -> Response:
    """Remove a finished backup job and its archive from the server before the hour it would keep them."""
    try:
        jobs.delete_job(job_id)
    except jobs.BackupJobNotFoundError:
        raise _error(status.HTTP_404_NOT_FOUND, "backup_job_not_found", "No such backup job") from None
    except jobs.BackupJobStateError:
        raise _error(status.HTTP_409_CONFLICT, "backup_job_running", "The backup is still running") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
