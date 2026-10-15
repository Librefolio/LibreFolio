"""Backup and export API (``/backup``): one module per resource, composed here into ``backup_router`` (C2).

``router.py`` includes ``backup_router``. ``instance.py`` owns the full-instance export and restore
(``/backup/export``, ``/backup/restore``, ``/backup/formats``, ``/backup/status``) and ``exports.py`` the per-series
snapshot exports (``/backup/asset/{id}/prices``, ``/backup/asset/{id}/events``, ``/backup/fx/{base}/{quote}/rates``).
They share the ``/backup`` prefix and the ``Backup & Export`` tag of ``backup_router``; the include order is the
registration order of the routes.
"""

from fastapi import APIRouter

from backend.app.api.v1.backup import exports, instance

backup_router = APIRouter(prefix="/backup", tags=["Backup & Export"])
backup_router.include_router(instance.instance_router)
backup_router.include_router(exports.exports_router)
