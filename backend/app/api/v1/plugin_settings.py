"""Plugin settings endpoints: the fields the plugins declare, their state for the caller, and their values.

- ``GET /api/v1/settings/plugins``: every plugin that declares settings, with its fields as the caller sees them. A
  secret's value never comes back, only whether it is set and readable.
- ``PATCH /api/v1/settings/plugins/bulk``: write or clear fields, all or nothing. System fields need an administrator;
  user fields are the caller's own.

The rules live in ``services/plugin_settings/service.py``.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.no_echo import NoInputEchoRoute
from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.schemas.plugin_settings import (
    PluginSettingFamily,
    PluginSettingsBulkWrite,
    PluginSettingsCatalogResponse,
    PluginSettingsWriteResponse,
)
from backend.app.services.plugin_settings.service import (
    PluginSettingsConflict,
    PluginSettingsKeyUnavailable,
    PluginSettingsRefused,
    read_catalogue,
    write_settings,
)

# A 422 never repeats the body: a malformed write may hold a secret (``api/no_echo.py``).
router = APIRouter(prefix="/settings/plugins", tags=["Plugin settings"], route_class=NoInputEchoRoute)


@router.get("", response_model=PluginSettingsCatalogResponse)
async def get_plugin_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session_generator)],
    family: Annotated[PluginSettingFamily | None, Query(description="Only the plugins of this family")] = None,
    plugin_code: Annotated[str | None, Query(max_length=64, description="Only this plugin (a test-only plugin is listed only when named here)")] = None,
) -> PluginSettingsCatalogResponse:
    """The plugins that declare settings and the state of each field for the caller.

    A system field shows its value to everyone when it is plain, and only whether it is set when it is secret; a user
    field shows the caller's own value. In the managed profile a field an environment variable sets is not listed.
    """
    return await read_catalogue(session, current_user, family=family.value if family else None, plugin_code=plugin_code)


@router.patch(
    "/bulk",
    response_model=PluginSettingsWriteResponse,
    responses={
        status.HTTP_409_CONFLICT: {"description": "Another write changed the same fields at the same time: nothing was written"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "At least one item is refused: nothing was written; `detail.results` lists every item"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "A secret cannot be encrypted: the instance key cannot be used"},
    },
)
async def update_plugin_settings(
    body: PluginSettingsBulkWrite,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session_generator)],
) -> PluginSettingsWriteResponse:
    """Write or clear plugin settings, all or nothing.

    Each item names a field and gives exactly one of ``value`` (a plain field), ``secret_value`` (a secret field,
    never returned) and ``clear``. A refused item refuses the whole write: the 422 lists every item with its
    ``error_code`` (``UNKNOWN_FIELD``, ``FORBIDDEN_SCOPE``, ``LOCKED_BY_ENV``, ``INVALID_VALUE``), and no message
    contains a value.
    """
    try:
        return await write_settings(session, current_user, body.items)
    except PluginSettingsRefused as refused:
        detail = {
            "message": str(refused),
            "results": [result.model_dump(mode="json") for result in refused.results],
            "success_count": 0,
        }
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail) from None
    except PluginSettingsKeyUnavailable as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from None
    except PluginSettingsConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None
