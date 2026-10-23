"""The instance block: on a blocked instance (``LIBREFOLIO_BLOCKED``), every API route answers 423 but a few.

Owner: workstream H (platform). ``refuse_when_blocked`` is a dependency of the ``/api/v1`` router
(``api/v1/router.py``), so it covers every API route (``APIRoute``), today's and tomorrow's: on a blocked instance an
endpoint answers only when it is in ``ALLOWED_WHEN_BLOCKED``. FastAPI does not give router dependencies to a plain
``Route``, a ``WebSocketRoute`` or a ``Mount``, so none of them belongs under ``/api/v1``; a test checks it. The only
exceptions are FastAPI's own documentation routes, ``/api/v1/openapi.json``, ``/api/v1/docs`` and ``/api/v1/redoc``
(``main.py``): they carry the API's schema and no data, and answer as they do for anyone; the test pins them. The list is
short on purpose: signing in and out, a password-reset or invitation link already sent (read it, reset the password
with it: someone who lost the password must still reach the block page, the account deletion or the backup), the block
page, the deletion of one's own account and its preview, the probes, the full backup of an administrator or of the
hosting panel (decision 12: on a blocked instance the data can still be taken away; the panel's routes want its
token, not a session), the outcome of a restore for the page that asked its restart, with that restart's one-time
ticket instead of a session (lot B5c: it starts nothing, and tells that page that the restore waits for the unblock),
and the scheduled wake-up, with its own token (decision D-W3: it runs no job and answers
``blocked``), and the hosting panel's status route, with its own token (lot H-61: the panel asks whether the customer
activated the instance, and a blocked one is still asked). Registration stays out, and so does the initial administrator's setup (decision P16(d)); anything else
goes through the developer first. A test pins the list.

FastAPI hands a dependency the endpoint function of the matched route (``scope["endpoint"]``), not its full path, so
the list holds endpoint functions. The refusal is ``423 Locked`` with the code ``instance_blocked``, and only a
signed-in user gets it: anyone else gets the 401 of ``get_current_user``, so a protected route answers a caller without
a session the same way whether or not the instance is blocked. A public route outside the list (registration, the
initial administrator's setup ``POST /auth/setup``, the email verification ``POST /email/verification/confirm`` and its
new link ``POST /email/verification/resend``, the address probe ``GET /auth/address-probe``, the reference lists of
``utilities``, the AI Export catalogue) answers that 401 only while the instance is blocked: from those, a caller
without a session can tell that it is blocked, and nothing more. The web app keeps the anonymous pages of a link
(``/invite``, ``/setup``, ``/verify-email``) on that 401 instead of sending them to the login
(``frontend/src/lib/api/zodios-client.ts``, lot A7b), so the page can say that the instance is blocked. The address
probe's 401 carries no CORS header, so an administrator's check from another address reads it as not verifiable:
intended (A6a). The web app tells 423 from a permission refusal (403) and shows the block page.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1 import auth, panel
from backend.app.api.v1.backup import instance as backup_instance
from backend.app.api.v1.backup import panel as backup_panel
from backend.app.api.v1.backup import panel_restore as backup_panel_restore
from backend.app.api.v1.backup import restore as backup_restore
from backend.app.api.v1.system import block, health, info, instance, ready, wake
from backend.app.config.platform import awaiting_restore, instance_blocked
from backend.app.db.session import get_session_generator
from backend.app.services.platform.hosting_panel.access import PanelScope, panel_caller
from backend.app.services.platform.restore_guard import restore_interrupted

INSTANCE_BLOCKED_CODE = "instance_blocked"

#: The seven routes of the panel's restore (H-62): their ticket comes first, then their own 423 and 409.
_PANEL_RESTORE_ROUTES = (
    backup_panel_restore.upload_panel_restore_archive,
    backup_panel_restore.start_panel_restore_check,
    backup_panel_restore.get_panel_restore_check,
    backup_panel_restore.confirm_panel_restore_check,
    backup_panel_restore.restart_panel_restore,
    backup_panel_restore.get_panel_restore_status,
    backup_panel_restore.cancel_panel_pending_restore,
)

ALLOWED_WHEN_BLOCKED = frozenset(
    {
        # Signing in and out, and who is signed in
        auth.login,
        auth.logout,
        auth.get_me,
        # A link already sent: reading it, and setting a new password with a reset link (no account is created)
        auth.inspect_link_token,
        auth.reset_password_with_link,
        # The deletion of one's own account, and what it would delete (A6a)
        auth.delete_own_account,
        auth.preview_own_account_deletion,
        # The full backup, for an administrator (decision 12): start, poll, download, delete; and the rules of a secure
        # backup's password (B4)
        backup_instance.start_instance_backup,
        backup_instance.get_instance_backup_options,
        backup_instance.get_instance_backup_job,
        backup_instance.download_instance_backup,
        backup_instance.delete_instance_backup_job,
        # The same, for the hosting panel, with its token instead of a session (B8): the provider hands the data back
        backup_panel.start_panel_backup,
        backup_panel.get_panel_backup_job,
        backup_panel.download_panel_backup,
        backup_panel.delete_panel_backup_job,
        # The outcome of a restore, for the page that asked its restart, with that restart's one-time ticket instead of a
        # session (B5c): it starts nothing, and says that the restore waits for the unblock
        backup_restore.get_restore_outcome,
        # The block page
        block.get_instance_block,
        instance.get_instance_config,
        # Probes and version
        health.health_check,
        health.test_lane_health,
        ready.get_readiness,
        info.get_system_info,
        # The scheduled wake-up, with its token instead of a session: no job runs, it answers "blocked" (Z4, D-W3)
        wake.wake_sync,
        # The hosting panel's status of the instance, with its own token: whether the customer has activated it (H-61, R1)
        panel.get_panel_status,
        # The panel's restore, with its ticket instead of a session (H-62): past the ticket each route answers 423
        # instance_blocked itself, so a caller without a ticket learns nothing of the block
        *_PANEL_RESTORE_ROUTES,
    }
)


async def refuse_when_blocked(request: Request, session: Annotated[AsyncSession, Depends(get_session_generator)]) -> None:
    """Router dependency of ``/api/v1``: on a blocked instance, refuse every endpoint not in ``ALLOWED_WHEN_BLOCKED``.

    The session is the request's own (FastAPI caches the dependency), and it is used only on a blocked instance.
    """
    if not instance_blocked() or request.scope.get("endpoint") in ALLOWED_WHEN_BLOCKED:
        return
    await auth.get_current_user(request, session)
    raise HTTPException(status_code=status.HTTP_423_LOCKED, detail={"code": INSTANCE_BLOCKED_CODE, "message": "This instance is blocked by its hosting provider"})


# =============================================================================
# The «awaiting restore» mode (lot H-62, contract L3 §6)
# =============================================================================

INSTANCE_AWAITING_RESTORE_CODE = "instance_awaiting_restore"

#: What answers while the hosting panel restores the instance: the probes, the version, the public configuration (with
#: its ``mode``), the scheduled wake-up (it runs nothing and says ``awaiting_restore``), and the panel's routes — its
#: status, its backup jobs (a backup there answers 409 ``backup_awaiting_restore``) and its restore. A test pins the list.
ALLOWED_WHEN_AWAITING_RESTORE = frozenset(
    {
        health.health_check,
        health.test_lane_health,
        ready.get_readiness,
        info.get_system_info,
        instance.get_instance_config,
        wake.wake_sync,
        panel.get_panel_status,
        backup_panel.start_panel_backup,
        backup_panel.get_panel_backup_job,
        backup_panel.download_panel_backup,
        backup_panel.delete_panel_backup_job,
        *_PANEL_RESTORE_ROUTES,
    }
)


async def refuse_when_awaiting_restore(request: Request) -> None:
    """Router dependency of ``/api/v1``, right after ``refuse_when_blocked``: while the instance awaits its restore
    (``LIBREFOLIO_AWAIT_RESTORE``), every endpoint not in ``ALLOWED_WHEN_AWAITING_RESTORE`` answers 423
    ``instance_awaiting_restore`` — to anyone, signed in or not (decision Q5): the volume is empty, or holds the data the
    panel is restoring, and nobody may register, set up a first administrator or sign in before the panel ends the mode.
    """
    if awaiting_restore() and request.scope.get("endpoint") not in ALLOWED_WHEN_AWAITING_RESTORE:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail={"code": INSTANCE_AWAITING_RESTORE_CODE, "message": "This instance is waiting for its hosting provider to restore its data"})


# =============================================================================
# A restore stopped half way (lot B-33, the start's part)
# =============================================================================

INSTANCE_RESTORE_INTERRUPTED_CODE = "instance_restore_interrupted"
BACKUP_RESTORE_INTERRUPTED_CODE = "backup_restore_interrupted"

#: What answers while the state of the restore cannot be read: the same as while the instance awaits its restore —
#: the probes, the public configuration (with ``restore_interrupted``), the scheduled wake-up (it runs nothing), and the
#: hosting panel's routes. A test pins it equal to ``ALLOWED_WHEN_AWAITING_RESTORE``.
ALLOWED_WHEN_RESTORE_INTERRUPTED = ALLOWED_WHEN_AWAITING_RESTORE


async def refuse_when_restore_interrupted(request: Request) -> None:
    """Router dependency of ``/api/v1``, third, after the block and the awaiting-restore mode: while this process found
    the state of the restore unreadable at its start (``services/platform/restore_guard.py``), every endpoint not in
    ``ALLOWED_WHEN_RESTORE_INTERRUPTED`` answers 423 ``instance_restore_interrupted`` — to anyone: LibreFolio cannot tell
    which data it holds, and serves none until the administrator chooses with ``./dev.py backup pending --recover previous``.

    The hosting panel's backup start answers 409 ``backup_restore_interrupted`` instead (D7): a backup of data in doubt
    would pass the coordinator's checks and push a good copy out of the seven it keeps. The panel's credential is
    checked first, by hand, so a caller without one gets the same answer as outside the state."""
    if not restore_interrupted():
        return
    endpoint = request.scope.get("endpoint")
    if endpoint is backup_panel.start_panel_backup:
        await panel_caller(request, PanelScope.BACKUP)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": BACKUP_RESTORE_INTERRUPTED_CODE, "message": "A restore of this instance stopped half way: no backup starts until its administrator recovers it"})
    if endpoint not in ALLOWED_WHEN_RESTORE_INTERRUPTED:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail={"code": INSTANCE_RESTORE_INTERRUPTED_CODE, "message": "A restore of this instance stopped half way: it serves no data until its administrator recovers it"})
