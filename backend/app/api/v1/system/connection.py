"""Connection security (``GET /system/connection``): how the server sees this request."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from backend.app.api.v1.auth import get_current_user, session_cookie_secure
from backend.app.db.models import User
from backend.app.schemas.system import ConnectionSecurityResponse
from backend.app.utils.runtime.network import classify_ip, client_address

connection_router = APIRouter()


@connection_router.get("/connection", response_model=ConnectionSecurityResponse)
async def get_connection_security(
    request: Request,
    _current_user: Annotated[User, Depends(get_current_user)],
) -> ConnectionSecurityResponse:
    """How the server sees this request, for the connection-security indicator.

    The client address is classified, never returned or logged. The class reads the last
    X-Forwarded-For value when there is one, else the TCP peer: advisory only, since a forged
    header misleads just the sender's own indicator. ``cookie_secure`` is the decision the session
    cookie gets on this very request.
    """
    forwarded_for = ", ".join(request.headers.getlist("x-forwarded-for")) or None
    peer = request.client.host if request.client else None
    return ConnectionSecurityResponse(
        client_class=classify_ip(client_address(forwarded_for, peer)),
        cookie_secure=session_cookie_secure(request),
    )
