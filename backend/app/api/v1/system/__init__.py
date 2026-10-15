"""System API (``/system``): one module per resource, composed here into ``router`` (C2).

``router.py`` includes ``router``. The resource modules own their routes: ``info.py`` (``/system/info``),
``diagnostics.py`` (``/system/plugin-diagnostics``), ``container_image.py`` (``/system/container-image-status``),
``connection.py`` (``/system/connection``), ``health.py`` (``/system/health`` and the test runner's
``/system/test-lane-health``), ``instance.py`` (``/system/instance``, the public configuration of the instance) and
``ready.py`` (``/system/ready``, the readiness probe). They share the ``/system`` prefix and the ``System`` tag of
``router``; the include order is the registration order of the routes.
"""

from fastapi import APIRouter

from backend.app.api.v1.system import connection, container_image, diagnostics, health, info, instance, ready

router = APIRouter(prefix="/system", tags=["System"])
for _resource_router in (info.info_router, diagnostics.diagnostics_router, container_image.container_image_router, connection.connection_router, health.health_router, instance.instance_router, ready.ready_router):
    router.include_router(_resource_router)
