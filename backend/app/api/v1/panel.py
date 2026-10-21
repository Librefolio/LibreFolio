"""The hosting panel's status of the instance (``GET /panel/status``, lot H-61, R1).

Owner: workstream H (platform). A hosting panel that created an instance with ``LIBREFOLIO_ADMIN_EMAIL`` reads here
whether its customer has activated it: the state of the initial administrator's setup (workstream A,
``bootstrap_admin_service.admin_setup_status``) and, while a link works, until when. Nothing else: no email, no
username, no count. The route wants ``LIBREFOLIO_PANEL_STATUS_TOKEN`` (``services/platform/hosting_panel/access.py``):
unset, it answers 404. It answers on a blocked instance (``api/v1/instance_block.py``).
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session_generator
from backend.app.schemas.hosting_panel import PanelStatusResponse
from backend.app.services.accounts.bootstrap_admin_service import AdminSetupState, admin_setup_status
from backend.app.services.platform.hosting_panel.access import PanelCaller, PanelScope, panel_access
from backend.app.utils.datetime_utils import ensure_utc, utcnow

panel_router = APIRouter()

_RESPONSES: dict[int | str, dict] = {
    401: {"description": "No token, or not the status token of this instance (code `panel_status_unauthorized`)"},
    404: {"description": "The status route is off: no `LIBREFOLIO_PANEL_STATUS_TOKEN`"},
    429: {"description": "Too many refused panel credentials from this address (code `panel_too_many_attempts`, with `Retry-After`)"},
    503: {"description": "The status token of this instance cannot be used (code `panel_status_unavailable`)"},
}


@panel_router.get("/status", response_model=PanelStatusResponse, responses=_RESPONSES)
async def get_panel_status(
    _caller: Annotated[PanelCaller, Depends(panel_access(PanelScope.STATUS))],
    session: Annotated[AsyncSession, Depends(get_session_generator)],
) -> PanelStatusResponse:
    """The state of the initial administrator's setup: none, pending (with the link's expiry), done or expired."""
    status = await admin_setup_status(session, now=utcnow())
    expires_at = ensure_utc(status.setup_expires_at) if status.state.value == AdminSetupState.PENDING.value else None
    return PanelStatusResponse(admin_setup=status.state.value, setup_expires_at=expires_at)
