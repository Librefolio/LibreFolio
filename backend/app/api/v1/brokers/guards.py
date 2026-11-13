"""Access guards shared by the broker routes: who may reach a report file, who may edit a broker."""

import asyncio
import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import User, UserRole
from backend.app.schemas.brim import (
    BRIMFileInfo,
)
from backend.app.services.brim import storage
from backend.app.services.brokers.broker_service import BrokerService


async def get_brim_file_with_access(
    file_id: str,
    current_user: User,
    session: AsyncSession,
    *,
    min_role: Optional[UserRole] = None,
    denied_detail: str = "Access denied",
) -> BRIMFileInfo:
    """Load a BRIM file and check that the current user may reach it (decision 36 of release 1.3).

    A file of a broker needs a role on that broker (``min_role`` when given); a file with no broker, uploaded by an
    older version, only its uploader. An administrator reaches every file; anyone else gets 403. An id that is not the
    UUID an upload gives is a 404 before any lookup (W-B4).
    """
    if not is_brim_file_id(file_id):
        raise HTTPException(status_code=404, detail="File not found")
    # Off the event loop: reading a sidecar may detect the file's plugins again (item 8), which reads the file.
    file_info = await asyncio.to_thread(storage.get_file_info, file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    if not current_user.is_superuser:
        if file_info.target_broker_id is not None:
            broker_service = BrokerService(session)
            role = await broker_service._check_user_access(file_info.target_broker_id, current_user.id, min_role=min_role)
            if role is None:
                raise HTTPException(status_code=403, detail=denied_detail)
        elif file_info.uploaded_by_user_id != current_user.id:
            raise HTTPException(status_code=403, detail=denied_detail)

    return file_info


def is_brim_file_id(file_id: str) -> bool:
    """Whether ``file_id`` is a file id as an upload writes it: a UUID in its canonical lower-case form (W-B4).

    Upper-case is refused too: on a case-insensitive disk it would still find the file.
    """
    try:
        return str(uuid.UUID(file_id)) == file_id
    except ValueError:
        return False


async def require_broker_editor(broker_id: int, current_user: User, session: AsyncSession) -> None:
    """EDITOR or OWNER access on the broker, as for uploads and parses."""
    if current_user.is_superuser:
        return
    role = await BrokerService(session)._check_user_access(broker_id, current_user.id, min_role=UserRole.EDITOR)
    if role is None:
        raise HTTPException(status_code=403, detail="EDITOR or OWNER access required on this broker")
