"""
The «Security» checks of the admin settings (decision of 14/10, point 4): administrators only.

- ``GET /api/v1/security/checks``: every configuration check of ``services/platform/config_audit.py``, evaluated now —
  the ones the startup audit logs, workstreams A and E included —, then the stored plugin secrets the instance key can
  no longer read and the instance key check (is it the key the data was written with). Each with its severity; the tab shows those that are not ``ok``.
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.settings import require_admin
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.schemas.security import SecurityCheckRead, SecurityChecksResponse
from backend.app.services.platform.config_audit import run_config_checks
from backend.app.services.platform.instance_key_check import check_instance_key
from backend.app.services.platform.plugin_secrets_check import check_plugin_secrets

router = APIRouter(prefix="/security", tags=["Security"])


@router.get("/checks", response_model=SecurityChecksResponse, summary="The security checks of the instance (admin)")
async def list_security_checks(admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> SecurityChecksResponse:
    """Every check, evaluated now, with its severity (``ok``, ``info``, ``warning``, ``error``) and the key and the
    parameters of its message; never a secret value. The configuration checks read files (the instance key): off the
    event loop."""
    checks = [*await asyncio.to_thread(run_config_checks), await check_plugin_secrets(session), await check_instance_key(session)]
    return SecurityChecksResponse(items=[SecurityCheckRead(check_id=check.check_id, severity=check.severity, i18n_key=check.i18n_key, detail=dict(check.detail)) for check in checks])
