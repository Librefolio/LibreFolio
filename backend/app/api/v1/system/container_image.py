"""Container image status (``GET /system/container-image-status``): whether a release image can be pulled from GHCR."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.schemas.system import ContainerImageStatusResponse
from backend.app.services.platform.container_registry import probe_container_image

container_image_router = APIRouter()


@container_image_router.get("/container-image-status", response_model=ContainerImageStatusResponse)
async def get_container_image_status(
    tag: Annotated[str, Query(pattern=r"^\d+\.\d+\.\d+$", description="Normalized stable image tag, without a leading v")],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> ContainerImageStatusResponse:
    """Check whether a stable LibreFolio image tag is pullable from GHCR."""
    return await probe_container_image(tag)
