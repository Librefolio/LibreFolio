"""
Backup of the whole instance for a hosting panel (``/backup/panel``): the jobs of ``instance.py``, authenticated by a
token instead of a user session.

``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`` (or its ``_FILE``, ``config/backup.py``) turns the routes on. Unset, they answer
404, as a path that does not exist. The token travels only in ``Authorization: Bearer``, never in the URL, where access
logs would keep it, and is compared in constant time; a missing or wrong one answers 401. A token the server cannot use
(a ``_FILE`` it cannot read, a value too short) answers 503 and is logged, never the archive.

The panel sees only the jobs it started (origin ``panel``): any other job id answers 404. Its archives never hold the
instance key, which the panel itself configured. The routes stay allowed on an instance its hosting provider blocked
(``api/v1/instance_block.py``): that is when the provider hands the data back.
"""

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.api.v1.backup import job_views
from backend.app.config import SecretFileError
from backend.app.config.backup import BackupConfigError, backup_download_token
from backend.app.logging_config import get_logger
from backend.app.schemas.backup import InstanceBackupJob

logger = get_logger(__name__)

panel_router = APIRouter()

_bearer = HTTPBearer(auto_error=False, scheme_name="BackupPanelToken", description="LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN, sent as `Authorization: Bearer <token>`")

PANEL_ORIGIN = "panel"

_AUTH_RESPONSES = {
    401: {"description": "No token, or not the token of this instance (code `backup_panel_unauthorized`)"},
    404: {"description": "The panel routes are off (no `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`), or no backup job of the panel has this id"},
    503: {"description": "The token of this instance cannot be used: its file is unreadable or it is too short (code `backup_panel_unavailable`)"},
}


def require_panel_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> None:
    """Let the request through only with the hosting panel's token: 404 when the routes are off, 401 without the token."""
    try:
        expected = backup_download_token()
    except (SecretFileError, BackupConfigError) as exc:
        logger.error("The hosting panel's backup token cannot be used: its routes refuse every request", error=str(exc))
        raise job_views.backup_error(status.HTTP_503_SERVICE_UNAVAILABLE, "backup_panel_unavailable", "The panel token of this instance cannot be used") from None
    if expected is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    presented = credentials.credentials if credentials is not None else ""
    if not hmac.compare_digest(presented.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "backup_panel_unauthorized", "message": "A valid panel token is required"},
            headers={"WWW-Authenticate": "Bearer"},
        )


PanelToken = Annotated[None, Depends(require_panel_token)]


@panel_router.post("/panel/jobs", status_code=status.HTTP_202_ACCEPTED, response_model=InstanceBackupJob, responses={**_AUTH_RESPONSES, **job_views.START_RESPONSES})
def start_panel_backup(_token: PanelToken) -> InstanceBackupJob:
    """Start a backup of the whole instance for the hosting panel, and return the job to poll. Never with the instance key."""
    return job_views.start_job(PANEL_ORIGIN)


@panel_router.get("/panel/jobs/{job_id}", response_model=InstanceBackupJob, responses=_AUTH_RESPONSES)
def get_panel_backup_job(job_id: str, _token: PanelToken) -> InstanceBackupJob:
    """The state of a backup job the panel started: its progress while it runs, its archive or its error once it ends."""
    return job_views.read_job(job_id, origin=PANEL_ORIGIN)


@panel_router.get("/panel/jobs/{job_id}/file", response_class=FileResponse, responses={**job_views.FILE_RESPONSES, **_AUTH_RESPONSES})
def download_panel_backup(job_id: str, _token: PanelToken) -> FileResponse:
    """Download the archive of a finished backup job the panel started. It holds every user's data."""
    return job_views.job_file(job_id, origin=PANEL_ORIGIN)


@panel_router.delete("/panel/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT, responses={**job_views.DELETE_RESPONSES, **_AUTH_RESPONSES})
def delete_panel_backup_job(job_id: str, _token: PanelToken) -> Response:
    """Remove a finished backup job the panel started, and its archive, once the panel has it."""
    return job_views.remove_job(job_id, origin=PANEL_ORIGIN)
