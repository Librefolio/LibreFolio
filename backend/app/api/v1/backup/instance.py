"""
Backup of the whole instance (``/backup/instance``): an archive of the data directory, built in the background.

The archive holds the database (a consistent copy), the uploaded files, the broker reports and the risk scenarios, with
a manifest: unpacked into an empty data directory it is the instance again. It holds every user's data, so every route
here is for administrators only. ``POST /backup/instance`` starts a job and answers at once; the client polls the job,
then downloads its archive, which the server keeps for an hour (or until ``DELETE``). One backup runs at a time.

``backup_router`` (``__init__.py``) gives these routes the ``/backup`` prefix and the ``Backup & Export`` tag, before the
hosting panel's routes of ``panel.py`` and the per-series exports of ``exports.py``. The jobs, their views and the
errors, with their stable ``code`` in ``detail``, are shared with ``panel.py`` (``job_views.py``). The four routes stay
allowed on an instance its hosting provider blocked (``api/v1/instance_block.py``, decision 12).
"""

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import FileResponse

from backend.app.api.v1.backup import job_views
from backend.app.api.v1.settings import require_admin
from backend.app.db.models import User
from backend.app.schemas.backup import InstanceBackupJob

instance_router = APIRouter()


@instance_router.post("/instance", status_code=status.HTTP_202_ACCEPTED, response_model=InstanceBackupJob, responses=job_views.START_RESPONSES)
def start_instance_backup(_admin: User = Depends(require_admin)) -> InstanceBackupJob:
    """Start a backup of the whole instance in the background, and return the job to poll. Administrators only."""
    return job_views.start_job("ui")


@instance_router.get("/instance/jobs/{job_id}", response_model=InstanceBackupJob, responses={404: job_views.NOT_FOUND})
def get_instance_backup_job(job_id: str, _admin: User = Depends(require_admin)) -> InstanceBackupJob:
    """The state of a backup job: its phase and progress while it runs, its archive or its error once it ends."""
    return job_views.read_job(job_id)


@instance_router.get("/instance/jobs/{job_id}/file", response_class=FileResponse, responses=job_views.FILE_RESPONSES)
def download_instance_backup(job_id: str, _admin: User = Depends(require_admin)) -> FileResponse:
    """Download the archive of a finished backup job. It holds every user's data: keep it private."""
    return job_views.job_file(job_id)


@instance_router.delete("/instance/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT, responses=job_views.DELETE_RESPONSES)
def delete_instance_backup_job(job_id: str, _admin: User = Depends(require_admin)) -> Response:
    """Remove a finished backup job and its archive from the server before the hour it would keep them."""
    return job_views.remove_job(job_id)
