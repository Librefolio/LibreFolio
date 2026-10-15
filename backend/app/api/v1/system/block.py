"""The block page (``GET /system/block``): whether the hosting provider blocked this instance, its deletion date, and,
for an administrator, where the subscription is managed.

Signed-in users only, and allowed on a blocked instance (``api/v1/instance_block.py``). A workstream that owns part of
the block page adds one field to ``InstanceBlockResponse`` and fills it here with one call to its service.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.v1.auth import get_current_user
from backend.app.config.platform import instance_blocked, instance_deletion_date
from backend.app.db.models import User
from backend.app.schemas.system import InstanceBlockResponse
from backend.app.services.accounts.registration_service import billing_link

block_router = APIRouter()


@block_router.get("/block", response_model=InstanceBlockResponse)
async def get_instance_block(current_user: Annotated[User, Depends(get_current_user)]) -> InstanceBlockResponse:
    """Whether this instance is blocked by its hosting provider, the day it will be deleted when given, and, for an
    administrator only, where the subscription is managed (``LIBREFOLIO_BILLING_URL``, A5) and that a full backup can
    still be downloaded (decision 12)."""
    return InstanceBlockResponse(
        blocked=instance_blocked(),
        deletion_date=instance_deletion_date(),
        billing_url=billing_link() if current_user.is_superuser else None,
        backup_available=current_user.is_superuser,
    )
