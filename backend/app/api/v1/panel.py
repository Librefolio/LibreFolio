"""The hosting panel's status of the instance (``GET /panel/status``, lot H-61, R1).

Owner: workstream H (platform). A hosting panel that created an instance with ``LIBREFOLIO_ADMIN_EMAIL`` reads here
whether its customer has activated it: the state of the initial administrator's setup (workstream A,
``bootstrap_admin_service.admin_setup_status``) and, while a link works, until when; and, since H-62, the instance's
``mode`` and its ``restore`` (state, reason, waiting, the backup's date and the stage). Nothing else: no email, no
username, no count. The route wants ``LIBREFOLIO_PANEL_STATUS_TOKEN`` (``services/platform/hosting_panel/access.py``):
unset, it answers 404. It answers on a blocked instance (``api/v1/instance_block.py``).
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.backup.restore import _IN_PROGRESS, _state_unreadable
from backend.app.config import get_data_dir
from backend.app.config.platform import awaiting_restore
from backend.app.db.session import get_session_generator
from backend.app.schemas.hosting_panel import PanelRestoreSummary, PanelStatusResponse
from backend.app.services.accounts.bootstrap_admin_service import AdminSetupState, admin_setup_status
from backend.app.services.platform.hosting_panel.access import PanelCaller, PanelScope, panel_access
from backend.app.services.platform.instance_backup import apply as restore_apply
from backend.app.utils.datetime_utils import ensure_utc, utcnow

panel_router = APIRouter()

_RESPONSES: dict[int | str, dict] = {
    401: {
        "description": "No credential, not the status token of this instance, or a ticket that cannot be verified (code `panel_status_unauthorized`); a signed ticket refused has its own code: `panel_ticket_expired`, `panel_ticket_not_yet_valid` (with `Retry-After`), `panel_ticket_wrong_audience`, `panel_ticket_wrong_scope`, `panel_ticket_invalid`, `panel_ticket_replayed`, `panel_ticket_unknown_key`"
    },
    404: {"description": "The status route is off: neither `LIBREFOLIO_PANEL_STATUS_TOKEN` nor `LIBREFOLIO_PANEL_PUBLIC_KEYS`"},
    429: {"description": "Too many refused panel credentials from this address (code `panel_too_many_attempts`, with `Retry-After`)"},
    500: {"description": "The state of the instance's restore cannot be read (code `restore_state_unreadable`): whether a restore waits is not known"},
    503: {"description": "The status token or the ticket settings of this instance cannot be used, or the registry of used tickets cannot be reached (code `panel_status_unavailable`)"},
}


@panel_router.get("/status", response_model=PanelStatusResponse, responses=_RESPONSES)
async def get_panel_status(
    _caller: Annotated[PanelCaller, Depends(panel_access(PanelScope.STATUS))],
    session: Annotated[AsyncSession, Depends(get_session_generator)],
) -> PanelStatusResponse:
    """The state of the initial administrator's setup: none, pending (with the link's expiry), done or expired; the
    instance's mode, and its restore (H-62): its state and why it waits, without who confirmed it."""
    status = await admin_setup_status(session, now=utcnow())
    expires_at = ensure_utc(status.setup_expires_at) if status.state.value == AdminSetupState.PENDING.value else None
    return PanelStatusResponse(admin_setup=status.state.value, setup_expires_at=expires_at, mode="awaiting_restore" if awaiting_restore() else "normal", restore=await _restore_summary())


async def _restore_summary() -> PanelRestoreSummary | None:
    """The restore of the data directory, or None when none was ever recorded; 500 when its state cannot be read (Q7:
    never «none» then, a restore may wait behind it)."""
    try:
        state = await asyncio.to_thread(restore_apply.read_restore, get_data_dir())
    except restore_apply.RestoreStateUnreadableError:
        raise _state_unreadable() from None
    if state is None:
        return None
    return PanelRestoreSummary(state="in_progress" if state.status in _IN_PROGRESS else state.status, reason=state.reason, waiting=state.waiting, backup_created_at=state.backup_created_at, stage_id=state.stage_id)
