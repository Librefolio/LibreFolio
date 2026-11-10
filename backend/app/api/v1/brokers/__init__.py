"""Broker API (``/brokers``): one module per resource, composed here into ``broker_router`` (W3).

``router.py`` includes ``broker_router``. The resource modules own their routes: ``crud.py`` (create, list, read,
update, delete), ``access.py`` (who may reach a broker) and, under ``/brokers/import``, the BRIM
(Broker Report Import Manager) routes: ``files.py`` (upload, list, preview, delete, download, plugin check),
``parse.py`` (parse a file), ``sets.py`` (report sets and gap fix) and ``lookup.py`` (duplicates, plugins, asset
candidates). ``guards.py`` holds the access checks they share. The include order is the registration order of the
routes: it keeps the OpenAPI document, and so the generated client, as it was.

**BRIM flow:**
1. Upload file → POST /import/upload (status: UPLOADED)
2. Parse file → POST /import/files/{id}/parse (status: PARSED or FAILED)
3. Client resolves fake asset IDs to real asset IDs
4. Import transactions → POST /transactions (standard endpoint)
"""

from fastapi import APIRouter

from backend.app.api.v1.brokers import access, crud, files, lookup, parse, sets

# The resource routers of ``/brokers`` carry the prefix themselves (their list routes have an empty path, which a
# router included without a prefix refuses); the BRIM routers hang under ``/brokers/import``.
broker_router = APIRouter(tags=["BR (Broker)"])

brim_router = APIRouter(prefix="/import", tags=["BR Import"])

for _router in (files.file_router, parse.parse_router, sets.set_router, lookup.lookup_router):
    brim_router.include_router(_router)

for _router in (crud.crud_router, access.access_router):
    broker_router.include_router(_router)
broker_router.include_router(brim_router, prefix="/brokers")

__all__ = ["brim_router", "broker_router"]
