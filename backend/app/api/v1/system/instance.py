"""Public instance configuration (``GET /system/instance``): what the app reads at startup, before anyone signs in.

The response is ``InstanceConfigResponse`` (``schemas/system.py``). A workstream that owns part of the public
configuration adds one field there, typed with a model of its own schemas, and fills it below with one call to its
service. Everything here is public and the same for whoever asks: nothing private, nothing that depends on a session.
"""

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.config.platform import awaiting_restore
from backend.app.db.session import get_session_generator
from backend.app.logging_config import client_log_level
from backend.app.schemas.auth import AccountsInstanceConfig
from backend.app.schemas.system import InstanceConfigResponse, LegalInstanceConfig
from backend.app.services.accounts.password_policy import password_rules_public
from backend.app.services.accounts.registration_service import effective_registration_mode, first_account_open
from backend.app.services.email.links import email_instance_config
from backend.app.services.platform.instance_links import privacy_link, support_link, terms_link

instance_router = APIRouter()


@instance_router.get("/instance", response_model=InstanceConfigResponse)
async def get_instance_config(session: AsyncSession = Depends(get_session_generator)) -> InstanceConfigResponse:
    """The public configuration of this instance, read by the app at startup; no session needed."""
    registration = await effective_registration_mode(session)
    return InstanceConfigResponse(
        profile=get_settings().LIBREFOLIO_PROFILE,
        # H-62: while the hosting panel restores the instance, the app shows its waiting page
        mode="awaiting_restore" if awaiting_restore() else "normal",
        accounts=AccountsInstanceConfig(registration_mode=registration.mode, registration_locked=registration.locked, first_account_open=await first_account_open(session), password_rules=password_rules_public()),
        # The email configuration may come from a password file: read off the event loop.
        email=await asyncio.to_thread(email_instance_config),
        support_url=support_link(),
        legal=LegalInstanceConfig(terms_url=terms_link(), privacy_url=privacy_link()),
        client_log_level=client_log_level(get_settings().LOG_LEVEL),
    )
