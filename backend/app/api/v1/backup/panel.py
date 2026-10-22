"""
Backup of the whole instance for a hosting panel (``/backup/panel``): the jobs of ``instance.py``, authenticated by a
token instead of a user session.

``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`` (or its ``_FILE``, ``config/backup.py``) turns the routes on: they are the
``backup`` scope of the hosting panel, behind its shared access (``services/platform/hosting_panel/access.py``, lot
H-61). Unset, they answer 404, as a path that does not exist. The token travels only in ``Authorization: Bearer``,
never in the URL, where access logs would keep it, and is compared in constant time; a missing or wrong one answers 401,
too many refused ones from an address 429. A token the server cannot use (a ``_FILE`` it cannot read, a value too short)
answers 503 and is logged, never the archive. The routes carry the OpenAPI tag of the hosting panel
(``api/v1/backup/__init__.py``).

The panel sees only the jobs it started (origin ``panel``): any other job id answers 404. Its archives never hold the
instance key, which the panel itself configured. With ``LIBREFOLIO_BACKUP_RECIPIENTS`` set, every backup it starts is
sealed for those recipients (L3, ``instance_backup/sealed.py``): a ``.tar`` whose password only their private keys
open. A value that cannot be used, or none on a managed instance, answers 503 ``backup_panel_unavailable``: the panel
never gets a clear zip instead. The routes stay allowed on an instance its hosting provider blocked
(``api/v1/instance_block.py``): that is when the provider hands the data back.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import FileResponse

from backend.app.api.v1.backup import job_views
from backend.app.config.backup import RECIPIENTS_VARIABLE, BackupConfigError, backup_recipients, backup_requires_recipients
from backend.app.logging_config import get_logger
from backend.app.schemas.backup import InstanceBackupJob
from backend.app.services.platform.hosting_panel.access import PanelCaller, PanelScope, panel_access

logger = get_logger(__name__)

panel_router = APIRouter()

PANEL_ORIGIN = "panel"

_AUTH_RESPONSES = {
    401: {"description": "No token, or not the token of this instance (code `backup_panel_unauthorized`)"},
    404: {"description": "The panel routes are off (no `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`), or no backup job of the panel has this id"},
    429: {"description": "Too many refused panel credentials from this address (code `panel_too_many_attempts`, with `Retry-After`)"},
    503: {"description": "The token of this instance cannot be used: its file is unreadable or it is too short (code `backup_panel_unavailable`)"},
}
# The start's 409 says both refusals: another backup runs (the shared one), or the instance awaits a restore (L3).
_START_AWAITING_RESTORE = {409: {"description": job_views.START_RESPONSES[409]["description"] + "; or the instance awaits a restore from its hosting panel (`LIBREFOLIO_AWAIT_RESTORE`): a backup of its empty data never starts (code `backup_awaiting_restore`)"}}
_START_UNAVAILABLE = {503: {"description": "The panel's credential cannot be used, or the backup cannot be sealed: `LIBREFOLIO_BACKUP_RECIPIENTS` cannot be used, or is not set on a managed instance (code `backup_panel_unavailable`): no backup starts"}}


PanelToken = Annotated[PanelCaller, Depends(panel_access(PanelScope.BACKUP))]


@panel_router.post("/panel/jobs", status_code=status.HTTP_202_ACCEPTED, response_model=InstanceBackupJob, responses={**_AUTH_RESPONSES, **job_views.START_RESPONSES, **_START_UNAVAILABLE, **_START_AWAITING_RESTORE})
def start_panel_backup(_token: PanelToken) -> InstanceBackupJob:
    """Start a backup of the whole instance for the hosting panel, and return the job to poll. Never with the instance key;
    sealed for ``LIBREFOLIO_BACKUP_RECIPIENTS`` when it is set (L3). Never on an instance that awaits a restore."""
    if _awaiting_restore():
        raise job_views.backup_error(status.HTTP_409_CONFLICT, "backup_awaiting_restore", "The instance awaits a restore: a backup of its empty data never starts")
    recipients = _recipients()
    if recipients is None:
        return job_views.start_job(PANEL_ORIGIN)
    return job_views.start_job(PANEL_ORIGIN, recipients=recipients)


def _awaiting_restore() -> bool:
    """Whether the instance awaits a restore from its hosting panel (``LIBREFOLIO_AWAIT_RESTORE``, contract L3 §6), read
    at each request by workstream H's ``config.platform.await_restore`` (H-62); before it lands, never."""
    from backend.app.config import platform  # noqa: PLC0415 — the reader is looked up at each request

    reader = getattr(platform, "await_restore", None)
    return bool(reader is not None and reader())


def _recipients() -> tuple[str, ...] | None:
    """The recipients the panel's backup is sealed for; ``None`` for a clear zip, allowed on a self-hosted instance only.
    503 ``backup_panel_unavailable`` when the value cannot be used or a managed instance has none, logged once, naming
    the variable and the rule, never the value."""
    try:
        recipients = backup_recipients()
    except BackupConfigError as exc:
        logger.error("Hosting panel backup refused: the recipients cannot be used", variable=RECIPIENTS_VARIABLE, code=exc.code)
        raise job_views.backup_error(status.HTTP_503_SERVICE_UNAVAILABLE, "backup_panel_unavailable", "The backups of the hosting panel cannot be sealed: the configuration of the instance is unusable") from None
    if recipients is None and backup_requires_recipients():
        logger.error("Hosting panel backup refused: a managed instance has no recipients to seal it for", variable=RECIPIENTS_VARIABLE)
        raise job_views.backup_error(status.HTTP_503_SERVICE_UNAVAILABLE, "backup_panel_unavailable", "The backups of the hosting panel cannot be sealed: the configuration of the instance is unusable")
    return recipients


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
