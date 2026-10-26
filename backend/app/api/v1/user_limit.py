"""The accounts over the plan: while the active accounts outnumber ``LIBREFOLIO_MAX_USERS``, ordinary users do not enter (A5-7).

Owner: workstream A (accounts). ``refuse_when_over_limit`` is a dependency of the ``/api/v1`` router
(``api/v1/router.py``), the fourth, after the instance block, the awaiting-restore mode and the interrupted restore: when
two guards stand, the first answers (a restore that serves no data wins: nobody can choose yet). The state itself is
read from the accounts every time (``services/accounts/user_limit_service.py``): no limit, or a limit that cannot be
read, is never a state.

A signed-in user meets ``423 Locked`` with the code ``user_limit_exceeded`` on every route not in a list, and anyone
without a session gets the 401 of ``get_current_user``, as on an instance that is not over the limit.

- ``ALLOWED_WHEN_OVER_LIMIT`` answers everyone: the list of ``ALLOWED_WHEN_BLOCKED`` (``instance_block.py``) but for the
  five routes of the full backup of an administrator. Copied by reference, so a route added to the block's list for the
  same reason is allowed here too; a test pins the difference.
- ``ALLOWED_WHEN_OVER_LIMIT_ADMIN`` answers an administrator only: the choice of who keeps the access (``GET`` and ``POST``
  ``/users/over-limit``) and the full backup, so the data can be taken away before anybody is deactivated. The restore of
  the app is in neither list: an administrator over the limit chooses first.

The refusal is the page the web app shows (``frontend/src/lib/features/instance``): an administrator gets the choice,
anyone else is told to wait for the administrator.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1 import auth, users
from backend.app.api.v1.backup import instance as backup_instance
from backend.app.api.v1.instance_block import ALLOWED_WHEN_BLOCKED
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.services.accounts import user_limit_service

logger = get_logger(__name__)

USER_LIMIT_EXCEEDED_CODE = "user_limit_exceeded"

#: The full backup of an administrator: start, options, poll, download, delete. Kept for administrators alone.
_ADMIN_BACKUP = frozenset(
    {
        backup_instance.start_instance_backup,
        backup_instance.get_instance_backup_options,
        backup_instance.get_instance_backup_job,
        backup_instance.download_instance_backup,
        backup_instance.delete_instance_backup_job,
    }
)

ALLOWED_WHEN_OVER_LIMIT = frozenset(ALLOWED_WHEN_BLOCKED - _ADMIN_BACKUP)


ALLOWED_WHEN_OVER_LIMIT_ADMIN = frozenset({*_ADMIN_BACKUP, users.list_over_limit, users.resolve_over_limit})

#: Warned once per process and per count, not per request.
_reported: set[tuple[int, int]] = set()


def _report_once(state: user_limit_service.OverLimitState) -> None:
    key = (state.active, state.max_users)
    if key not in _reported:
        _reported.add(key)
        logger.warning("The instance is over its limit of users: ordinary users wait for an administrator to choose who keeps the access", active=state.active, max_users=state.max_users)


async def refuse_when_over_limit(request: Request, session: Annotated[AsyncSession, Depends(get_session_generator)]) -> None:
    """Router dependency of ``/api/v1``, fourth: while the accounts are over the limit, refuse every endpoint not allowed to the caller.

    One ``COUNT`` of the active accounts per request with a limit, none without one. A caller without a session meets
    the 401 of ``get_current_user``, as everywhere.
    """
    endpoint = request.scope.get("endpoint")
    if endpoint in ALLOWED_WHEN_OVER_LIMIT:
        return
    state = await user_limit_service.over_limit_state(session)
    if state is None:
        return
    user = await auth.get_current_user(request, session)
    _report_once(state)
    if user.is_superuser and endpoint in ALLOWED_WHEN_OVER_LIMIT_ADMIN:
        return
    raise HTTPException(status_code=status.HTTP_423_LOCKED, detail={"code": USER_LIMIT_EXCEEDED_CODE, "message": "This instance has more active users than its plan holds: an administrator has to choose who keeps the access"})
