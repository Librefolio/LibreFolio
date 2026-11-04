"""
The restore of the whole instance by its hosting panel (``/backup/panel/restore``, lot H-62, contract L3 §5).

Owner: workstream H (platform). The panel's coordinator restores an instance whose server is gone onto a new machine
it started in the «awaiting restore» mode (``LIBREFOLIO_AWAIT_RESTORE``, ``config/platform.py``): it uploads the
backup's ``.lfbk`` envelope, still encrypted, sends its password, follows the check on a copy, confirms it and restarts
the server, which applies it at its next start. The work is the administrator's restore (``api/v1/backup/restore.py``,
workstream B): the same upload writer, limit and space checks, the same check on a copy, confirmation and restart; only
the caller changes.

The order of the refusals, on every route:

1. The credential (``services/platform/hosting_panel/access.py``): a signed ticket of scope ``backup:restore`` only —
   no token opens it, so without ``LIBREFOLIO_PANEL_PUBLIC_KEYS`` the routes answer 404 like a path that does not exist.
   FastAPI resolves it before the route reads the body: a ticket that expires while a long upload is still arriving
   does not cut it (R3).
2. A blocked instance: 423 ``instance_blocked``, never a restore (the block lets data leave, never come in).
3. Outside the mode: 409 ``restore_mode_required``. A stolen signing key can at most fill an empty volume, never write
   over the data of an instance that runs.

A caller without a valid ticket learns neither the mode nor the block. The panel sees no personal or portfolio data
(R1): the report of a check is ``PanelRestoreStageReport`` (the administrators counted, the control totals as a verdict)
and the status names who confirmed only as ``confirmed_via``. The panel sees only the checks it started (``origin``). Only an ``.lfbk`` envelope is accepted (D2): a zip or the
coordinator's ``.tar`` is refused on its first bytes, before anything of it is written. Repeating a request never makes two restores: the same confirmation or a
restart already under way answers 202 with the state it finds. The routes never echo the password (``NoInputEchoRoute``).
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status

from backend.app.api.no_echo import NoInputEchoRoute
from backend.app.api.v1.backup.job_views import backup_error
from backend.app.api.v1.backup.restore import (
    _CONFIRM_STATUS,
    _IN_PROGRESS,
    _NOT_PENDING,
    _WRITE_CHUNK,
    _declared_size,
    _folder_unusable,
    _restore_limit,
    _stage_view,
    _state_unreadable,
    _status_view,
    _upload_failure,
    _upload_limit,
)
from backend.app.config import get_data_dir
from backend.app.config.platform import awaiting_restore, instance_blocked
from backend.app.logging_config import get_logger
from backend.app.schemas.backup import RestoreStageRequest, RestoreUpload
from backend.app.schemas.hosting_panel import PanelRestoreStage, PanelRestoreStageReport, PanelRestoreStatus
from backend.app.services.platform.hosting_panel.access import PanelCaller, PanelScope, panel_access
from backend.app.services.platform.instance_backup import apply as restore_apply
from backend.app.services.platform.instance_backup import restart, restore_jobs
from backend.app.services.platform.instance_backup.envelope import MAGIC, EnvelopeError
from backend.app.services.platform.instance_backup.jobs import out_of_space
from backend.app.services.platform.instance_backup.paths import BackupPathError, upload_path
from backend.app.services.platform.instance_backup.staging import StagingBusyError

logger = get_logger(__name__)

panel_restore_router = APIRouter(route_class=NoInputEchoRoute)

#: The origin of the panel's checks, and how its confirmations are recorded (``confirmed_via``): it sees only its own.
PANEL_ORIGIN = "panel"

#: Whether this process already asked for the restart of a confirmed restore: a retried ``restart`` answers its state
#: without a second SIGTERM (the security review's point 6: harmless to uvicorn, but the shutdown it starts is one).
_restart_requested = False


class _NotAnEnvelope(Exception):
    """The body of a panel upload does not start with the envelope's magic: refused before anything of it is written."""


_GATE_RESPONSES: dict[int | str, dict] = {
    401: {
        "description": "No credential, a token (no token opens the restore), or a ticket that cannot be verified (code `backup_restore_unauthorized`); a signed ticket refused has its own code: `panel_ticket_expired`, `panel_ticket_not_yet_valid` (with `Retry-After`), `panel_ticket_wrong_audience`, `panel_ticket_wrong_scope`, `panel_ticket_invalid`, `panel_ticket_replayed`, `panel_ticket_unknown_key`"
    },
    404: {"description": "The restore routes are off: no `LIBREFOLIO_PANEL_PUBLIC_KEYS`"},
    409: {"description": "The instance is not awaiting its restore (code `restore_mode_required`): `LIBREFOLIO_AWAIT_RESTORE` is off"},
    423: {"description": "The instance is blocked by its hosting provider (code `instance_blocked`): no restore"},
    429: {"description": "Too many refused panel credentials from this address (code `panel_too_many_attempts`, with `Retry-After`)"},
    503: {"description": "The panel's ticket settings of this instance cannot be used, or the registry of used tickets cannot be reached (code `backup_restore_unavailable`)"},
}


def _restore_gate(caller: Annotated[PanelCaller, Depends(panel_access(PanelScope.BACKUP_RESTORE))]) -> PanelCaller:
    """After the ticket: never on a blocked instance (423), only in the «awaiting restore» mode (409)."""
    if instance_blocked():
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail={"code": "instance_blocked", "message": "This instance is blocked by its hosting provider"})
    if not awaiting_restore():
        raise backup_error(status.HTTP_409_CONFLICT, "restore_mode_required", "This instance is not awaiting its restore")
    return caller


RestoreCaller = Annotated[PanelCaller, Depends(_restore_gate)]


def _responses(**more: dict) -> dict[int | str, dict]:
    return {**_GATE_RESPONSES, **{int(code.removeprefix("_")): description for code, description in more.items()}}


def _panel_status(state: restore_apply.RestoreState | None) -> PanelRestoreStatus:
    return PanelRestoreStatus.of(_status_view(state))


def _panel_check(stage_id: str) -> restore_jobs.RestoreCheck:
    """A check the panel started; any other (an administrator's, the command line's) is 404 to it, as an unknown id."""
    try:
        check = restore_jobs.read_check(stage_id)
    except restore_jobs.CheckNotFoundError:
        check = None
    if check is None or check.origin != PANEL_ORIGIN:
        raise backup_error(status.HTTP_404_NOT_FOUND, "restore_stage_not_found", "No check has this id")
    return check


def _panel_stage(check: restore_jobs.RestoreCheck) -> PanelRestoreStage:
    stage = _stage_view(check)
    report = PanelRestoreStageReport.of(stage.report) if stage.report is not None else None
    return PanelRestoreStage(**stage.model_dump(exclude={"report"}), report=report)


async def _receive_envelope(request: Request, writer: restore_jobs.UploadWriter) -> restore_jobs.RestoreUploaded:
    """The admin's ``_receive``, after a look at the body's first bytes: one that does not start with ``LFBK`` raises
    ``_NotAnEnvelope`` before a byte is written, and the rest of the body is never read (D2; the security review's
    point 3: a zip in clear never reaches the disk, and the previous upload stays, since the writer never finishes)."""
    stream = request.stream()
    head = bytearray()
    async for piece in stream:
        head += piece
        if len(head) >= len(MAGIC):
            break
    if head and not head.startswith(MAGIC):
        raise _NotAnEnvelope
    if head:
        await asyncio.to_thread(writer.write, bytes(head))
    buffer = bytearray()
    async for piece in stream:
        buffer += piece
        if len(buffer) >= _WRITE_CHUNK:
            await asyncio.to_thread(writer.write, bytes(buffer))
            buffer.clear()
    if buffer:
        await asyncio.to_thread(writer.write, bytes(buffer))
    # The other uploads stay until this one is accepted (SEC-3): a refused body never costs the previous good upload
    return await asyncio.to_thread(lambda: writer.finish(replace_others=False))


def _read_state() -> restore_apply.RestoreState | None:
    try:
        return restore_apply.read_restore(get_data_dir())
    except restore_apply.RestoreStateUnreadableError as exc:
        raise _state_unreadable(exc) from None


@panel_restore_router.put(
    "/panel/restore/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=RestoreUpload,
    responses=_responses(
        _400={"description": "The body is empty (code `backup_upload_empty`), the client left before its end (code `backup_upload_incomplete`), or it does not start as an `.lfbk` envelope: a zip or the `.tar` (code `restore_envelope_required`), refused on its first bytes, nothing written"},
        _413={"description": "The archive is larger than `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` (code `backup_too_large`, with `limit_mb`)"},
        _500={"description": "The restore folder of the data directory is a link or a file (code `restore_folder_unusable`), or the archive could not be written (code `backup_upload_failed`)"},
        _503={"description": "The upload limit of this instance cannot be read (code `backup_upload_unavailable`), or the panel's ticket settings cannot be used, or the registry of used tickets cannot be reached (code `backup_restore_unavailable`)"},
        _507={"description": "Not enough free space for the archive (code `backup_no_space`)"},
    ),
    openapi_extra={"requestBody": {"required": True, "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}},
)
async def upload_panel_restore_archive(request: Request, _caller: RestoreCaller) -> RestoreUpload:
    """Receive the backup's ``.lfbk`` envelope, as the raw request body; check it next with ``POST …/restore/stage``."""
    limit_mb, max_bytes = _upload_limit()
    try:
        writer = await asyncio.to_thread(restore_jobs.UploadWriter, get_data_dir(), max_bytes=max_bytes, declared=_declared_size(request))
    except BackupPathError:
        raise _folder_unusable() from None
    except (restore_jobs.UploadTooLargeError, restore_jobs.UploadNoSpaceError, OSError) as exc:
        raise _upload_failure(exc, limit_mb) from None
    try:
        uploaded = await _receive_envelope(request, writer)
    except _NotAnEnvelope:
        # D2: the coordinator sends the backup.lfbk member only; a zip in clear or the .tar is refused on its first bytes
        await asyncio.to_thread(writer.abort)
        logger.warning("A panel restore upload was not an envelope: refused on its first bytes")
        raise backup_error(status.HTTP_400_BAD_REQUEST, "restore_envelope_required", "Only the backup's .lfbk envelope is accepted") from None
    except BaseException as exc:
        await asyncio.to_thread(writer.abort)
        failure = _upload_failure(exc, limit_mb)
        if failure is exc:
            raise
        raise failure from None
    data_dir = get_data_dir()
    if uploaded.kind != "envelope":
        # The second defence: the finished file is no envelope after all. It goes, and the previous upload stays
        await asyncio.to_thread(upload_path(data_dir, uploaded.upload_id).unlink, missing_ok=True)
        logger.warning("A panel restore upload was not an envelope: refused once finished", upload_id=uploaded.upload_id)
        raise backup_error(status.HTTP_400_BAD_REQUEST, "restore_envelope_required", "Only the backup's .lfbk envelope is accepted")
    # Accepted: only now does it replace the uploads before it
    await asyncio.to_thread(restore_jobs.remove_replaced_uploads, data_dir, keep=uploaded.upload_id)
    return RestoreUpload(upload_id=uploaded.upload_id, size=uploaded.size, kind=uploaded.kind)


@panel_restore_router.post(
    "/panel/restore/stage",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PanelRestoreStage,
    responses=_responses(
        _400={"description": "No password (code `password_required`), a wrong one (code `wrong_password`), or not a whole envelope (code `envelope_damaged`): the upload stays, for another try"},
        _500={"description": "The restore folder of the data directory is a link or a file (code `restore_folder_unusable`), or the check could not start (code `stage_failed`)"},
        _507={"description": "Not enough free space to start the check (code `no_space`)"},
    )
    | {
        404: {"description": "No uploaded archive has this id (code `backup_upload_not_found`); or the restore routes are off"},
        409: {"description": "Another archive is being checked (code `restore_busy`), a secure backup this LibreFolio cannot read (code `envelope_unsupported`), or the instance is not awaiting its restore (code `restore_mode_required`)"},
        503: {"description": "The restore limit cannot be read (code `backup_restore_unavailable`), or the panel's ticket settings cannot be used (same code)"},
    },
)
def start_panel_restore_check(body: RestoreStageRequest, _caller: RestoreCaller) -> PanelRestoreStage:
    """Check the uploaded envelope on a copy, in the background, with its password; return the check to poll. The same
    start again while its check runs answers 202 with that check (the panel retrying), never a second one."""
    running = restore_jobs.running_check(body.upload_id)
    if running is not None and running.origin == PANEL_ORIGIN:
        return _panel_stage(running)
    password = body.password.get_secret_value() if body.password is not None else None
    max_unpacked = _restore_limit()
    try:
        return _panel_stage(restore_jobs.start_check(body.upload_id, password=password, max_unpacked=max_unpacked, origin=PANEL_ORIGIN))
    except restore_jobs.UploadNotFoundError:
        raise backup_error(status.HTTP_404_NOT_FOUND, "backup_upload_not_found", "No uploaded archive has this id") from None
    except StagingBusyError:
        # Two identical starts at once (the security review's point 5): the one that lost the lock answers the winner
        running = restore_jobs.running_check(body.upload_id)
        if running is not None and running.origin == PANEL_ORIGIN:
            return _panel_stage(running)
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
            logger.warning("A panel check of a backup archive could not start: not enough free space")
            raise backup_error(status.HTTP_507_INSUFFICIENT_STORAGE, "no_space", "Not enough free space to check the archive") from None
        logger.error("A panel check of a backup archive could not start", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "stage_failed", "The check could not start: the server's log has the cause") from None


@panel_restore_router.get(
    "/panel/restore/stage/{stage_id}",
    response_model=PanelRestoreStage,
    responses={**_GATE_RESPONSES, 404: {"description": "No check has this id (code `restore_stage_not_found`); or the restore routes are off"}},
)
def get_panel_restore_check(stage_id: str, _caller: RestoreCaller) -> PanelRestoreStage:
    """The state of a check the panel started: its phase and progress while it runs, then the panel's report, or the
    code of its refusal."""
    return _panel_stage(_panel_check(stage_id))


@panel_restore_router.post(
    "/panel/restore/stage/{stage_id}/confirm",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PanelRestoreStatus,
    responses={
        **_GATE_RESPONSES,
        404: {"description": "No check has this id, or its copy is gone (code `restore_stage_not_found`); or the restore routes are off"},
        409: {
            "description": "The check still runs (code `restore_stage_running`), refused the archive (code `restore_not_restorable`), LibreFolio was updated since, or the owner's address changed since the check (code `restore_stage_outdated`), another restore waits (code `restore_already_pending`), or the instance is not awaiting its restore (code `restore_mode_required`). On a managed instance: no `LIBREFOLIO_ADMIN_EMAIL` (code `owner_email_not_set`), or the backup holds two accounts on one address or one name, the owner's address as another account's name, or an administrator still waiting for its setup link while no account holds the owner's address (code `owner_conflict`)"
        },
        410: {"description": "The check expired: check the archive again (code `restore_stage_expired`)"},
        500: {"description": "The confirmation could not be written (code `restore_confirm_failed`), or the state of the restore cannot be read (code `restore_state_unreadable`): nothing confirmed"},
        507: {"description": "Not enough free space to confirm the restore (code `backup_no_space`)"},
    },
)
def confirm_panel_restore_check(stage_id: str, caller: RestoreCaller) -> PanelRestoreStatus:
    """Confirm the restore of a checked copy; the next start applies it. Confirming the same stage again answers 202
    with the same status; no word to type: the ticket is the authority."""
    data_dir = get_data_dir()
    _panel_check(stage_id)
    try:
        # The author is the ticket's key, never a person; the state says it came from the panel
        state = restore_jobs.confirm_check(stage_id, confirmed_by=caller.kid or PANEL_ORIGIN, confirmed_via=PANEL_ORIGIN, data_dir=data_dir)
    except restore_jobs.CheckNotFoundError:
        raise backup_error(status.HTTP_404_NOT_FOUND, "restore_stage_not_found", "No check has this id") from None
    except restore_jobs.CheckRunningError:
        raise backup_error(status.HTTP_409_CONFLICT, "restore_stage_running", "The check still runs") from None
    except restore_apply.RestoreStateUnreadableError as exc:
        raise _state_unreadable(exc) from None
    except restore_apply.RestoreStateError as exc:
        if exc.code == "restore_already_pending":
            current = _read_state()
            if current is not None and current.status == "pending" and current.stage_id == stage_id:
                return _panel_status(current)
        raise backup_error(_CONFIRM_STATUS.get(exc.code, status.HTTP_409_CONFLICT), exc.code, str(exc)) from None
    except BackupPathError:
        raise _folder_unusable() from None
    except OSError as exc:
        if out_of_space(exc):
            logger.warning("A panel restore could not be confirmed: not enough free space")
            raise backup_error(status.HTTP_507_INSUFFICIENT_STORAGE, "backup_no_space", "Not enough free space to confirm the restore") from None
        logger.error("A panel restore could not be confirmed", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "restore_confirm_failed", "The restore could not be confirmed: the server's log has the cause") from None
    logger.warning("Restore confirmed by the hosting panel", stage_id=stage_id, kid=caller.kid, jti=caller.jti)
    return _panel_status(state)


@panel_restore_router.post(
    "/panel/restore/restart",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PanelRestoreStatus,
    responses={
        **_GATE_RESPONSES,
        409: {"description": f"{_NOT_PENDING}, and none under way (code `restore_not_pending`); or the instance is not awaiting its restore (code `restore_mode_required`)"},
        500: {"description": "The restart could not be prepared (code `restore_restart_failed`), or the state of the restore cannot be read (code `restore_state_unreadable`): no restart"},
    },
)
def restart_panel_restore(background_tasks: BackgroundTasks, response: Response, _caller: RestoreCaller) -> PanelRestoreStatus:
    """Stop the server once this answer is sent, so that its next start applies the confirmed restore; the restart
    policy starts it again. A restore already under way or committed answers 202 with its state, and no second stop; so
    does a retry in the process that already asked for the stop."""
    data_dir = get_data_dir()
    try:
        state, _ticket = restore_apply.prepare_restart(data_dir=data_dir)
    except restore_apply.RestoreNotPendingError:
        current = _read_state()
        if current is not None and (current.status in _IN_PROGRESS or current.status == "committed"):
            return _panel_status(current)
        raise backup_error(status.HTTP_409_CONFLICT, "restore_not_pending", _NOT_PENDING) from None
    except restore_apply.RestoreStateUnreadableError as exc:
        raise _state_unreadable(exc) from None
    except BackupPathError:
        raise _folder_unusable() from None
    except OSError as exc:
        logger.error("A panel restart for a restore could not be prepared", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "restore_restart_failed", "The restart could not be prepared: the server's log has the cause") from None
    global _restart_requested
    response.headers["Cache-Control"] = "no-store"
    if _restart_requested:
        # Asked already in this process: the server is stopping, and a second SIGTERM adds nothing
        return _panel_status(state)
    _restart_requested = True
    background_tasks.add_task(lambda: restart.request_restart())
    return _panel_status(state)


@panel_restore_router.get(
    "/panel/restore/status",
    response_model=PanelRestoreStatus,
    responses={**_GATE_RESPONSES, 500: {"description": "The state of the restore cannot be read (code `restore_state_unreadable`)"}},
)
def get_panel_restore_status(_caller: RestoreCaller) -> PanelRestoreStatus:
    """The restore waiting for the next start, the one being applied, or the last one that ended; ``none`` when none."""
    return _panel_status(_read_state())


@panel_restore_router.delete(
    "/panel/restore/pending",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **_GATE_RESPONSES,
        404: {"description": f"{_NOT_PENDING} (code `restore_not_pending`); or the restore routes are off"},
        500: {"description": "The restore could not be dropped (code `restore_cancel_failed`), or its state cannot be read (code `restore_state_unreadable`)"},
    },
)
def cancel_panel_pending_restore(_caller: RestoreCaller) -> Response:
    """Drop the restore waiting for the next start, with its checked copy."""
    try:
        restore_apply.cancel_restore(data_dir=get_data_dir(), drop_copy=True)
    except restore_apply.RestoreNotPendingError:
        raise backup_error(status.HTTP_404_NOT_FOUND, "restore_not_pending", _NOT_PENDING) from None
    except restore_apply.RestoreStateUnreadableError as exc:
        raise _state_unreadable(exc) from None
    except OSError as exc:
        logger.error("A pending restore could not be cancelled by the panel", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise backup_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "restore_cancel_failed", "The restore could not be cancelled: the server's log has the cause") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
