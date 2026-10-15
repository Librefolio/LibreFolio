"""Public instance configuration (``GET /system/instance``): what the app reads at startup, before anyone signs in.

The response is ``InstanceConfigResponse`` (``schemas/system.py``). A workstream that owns part of the public
configuration adds one field there, typed with a model of its own schemas, and fills it below with one call to its
service. Everything here is public and the same for whoever asks: nothing private, nothing that depends on a session.
"""

from fastapi import APIRouter

from backend.app.config import get_settings
from backend.app.schemas.system import InstanceConfigResponse

instance_router = APIRouter()


@instance_router.get("/instance", response_model=InstanceConfigResponse)
def get_instance_config() -> InstanceConfigResponse:
    """The public configuration of this instance, read by the app at startup; no session needed."""
    return InstanceConfigResponse(profile=get_settings().LIBREFOLIO_PROFILE)
