"""System API (``/system``): one module per resource, composed here into ``router`` (C2).

``router.py`` includes ``router``. The resource modules own their routes: ``info.py`` (``/system/info``),
``diagnostics.py`` (``/system/plugin-diagnostics``), ``container_image.py`` (``/system/container-image-status``),
``connection.py`` (``/system/connection``), ``health.py`` (``/system/health`` and the test runner's
``/system/test-lane-health``), ``instance.py`` (``/system/instance``, the public configuration of the instance),
``ready.py`` (``/system/ready``, the readiness probe), ``wake.py`` (``/system/wake-sync``, the scheduled wake-up,
workstream Z), ``price_refresh.py`` (``/system/price-refresh``, the catch-up of the prices, workstream Z) and
``block.py`` (``/system/block``, the block page, last). They share
the ``/system`` prefix of ``router``; the include order is the registration order of the routes. Each include gives its
tag, ``System``, but ``wake.py``, whose route carries the hosting panel's tag alone (lot H-61): FastAPI adds the tags of
a router to the ones of what it includes, never replaces them, so the router itself has none.
"""

from fastapi import APIRouter

from backend.app.api.v1.system import block, connection, container_image, diagnostics, health, info, instance, price_refresh, ready, wake
from backend.app.services.platform.hosting_panel.access import HOSTING_PANEL_TAG

SYSTEM_TAG = "System"

router = APIRouter(prefix="/system")
for _resource_router in (info.info_router, diagnostics.diagnostics_router, container_image.container_image_router, connection.connection_router, health.health_router, instance.instance_router, ready.ready_router, wake.wake_router, price_refresh.price_refresh_router, block.block_router):
    router.include_router(_resource_router, tags=[HOSTING_PANEL_TAG if _resource_router is wake.wake_router else SYSTEM_TAG])
