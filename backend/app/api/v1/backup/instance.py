"""
Backup of the whole instance (``/backup/instance``): an archive of the data directory, built in the background.

The archive holds the database (a consistent copy), the uploaded files, the broker reports and the risk scenarios, with
a manifest: unpacked into an empty data directory it is the instance again. It holds every user's data, so every route
here is for administrators only. ``POST /backup/instance`` starts a job and answers at once; the client polls the job,
then downloads its archive, which the server keeps for an hour (or until ``DELETE``). One backup runs at a time.

With a password, a secure backup (lot B4, decisions 38 and 39): an ``.lfbk`` envelope that only this password opens,
carrying the instance key when LibreFolio generated it. ``GET /backup/instance/options`` gives the rules the password
must meet. A 422 never repeats the body (``api/no_echo.py``): it may hold the password.

``backup_router`` (``__init__.py``) gives these routes the ``/backup`` prefix and the ``Backup & Export`` tag, before the
hosting panel's routes of ``panel.py`` and the per-series exports of ``exports.py``. The jobs, their views and the
errors, with their stable ``code`` in ``detail``, are shared with ``panel.py`` (``job_views.py``). The five routes
(start, options, job, file, delete) stay allowed on an instance its hosting provider blocked
(``api/v1/instance_block.py``, decision 12).
"""

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse

from backend.app.api.no_echo import NoInputEchoRoute
from backend.app.api.v1.backup import job_views
from backend.app.api.v1.settings import require_admin
from backend.app.db.models import User
from backend.app.schemas.auth import PasswordRuleRead
from backend.app.schemas.backup import InstanceBackupJob, InstanceBackupOptions, InstanceBackupRequest
from backend.app.services.accounts.password_policy import password_rules_public
from backend.app.services.platform.instance_backup.secure import archive_password_problems, archive_password_rules

instance_router = APIRouter(route_class=NoInputEchoRoute)

_PASSWORD_TOO_WEAK = {"description": "The password misses some of the rules of GET /backup/instance/options (code `password_too_weak`, with `rules`): no backup started"}


@instance_router.post("/instance", status_code=status.HTTP_202_ACCEPTED, response_model=InstanceBackupJob, responses={**job_views.START_RESPONSES, 400: _PASSWORD_TOO_WEAK})
def start_instance_backup(body: InstanceBackupRequest | None = Body(default=None), _admin: User = Depends(require_admin)) -> InstanceBackupJob:
    """Start a backup of the whole instance in the background, and return the job to poll. Administrators only.

    With a password, a secure backup: its rules are checked first, and the password goes to the job, never to its state.
    """
    password = body.password.get_secret_value() if body is not None and body.password is not None else None
    if password is not None:
        failed = archive_password_problems(password)
        if failed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "password_too_weak", "message": "The password does not meet the rules of a backup's password", "rules": failed})
    return job_views.start_job("ui", password=password)


@instance_router.get("/instance/options", response_model=InstanceBackupOptions)
def get_instance_backup_options(_admin: User = Depends(require_admin)) -> InstanceBackupOptions:
    """What a secure backup asks of its password: the rules of the accounts, with a longer minimum (P12)."""
    return InstanceBackupOptions(password_rules=[PasswordRuleRead(**rule) for rule in password_rules_public(rules=archive_password_rules())])


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
