"""Backup and export API (``/backup``): one module per resource, composed here into ``backup_router`` (C2).

``router.py`` includes ``backup_router``. ``instance.py`` owns the backup of the whole instance (``/backup/instance``,
an archive built in the background, for administrators), ``panel.py`` the same jobs for a hosting panel with a token
(``/backup/panel/jobs``), both on ``job_views.py``, ``restore.py`` the check of an archive before a restore
(``/backup/restore``, for administrators), and ``exports.py`` the per-series snapshot exports
(``/backup/asset/{id}/prices``, ``/backup/asset/{id}/events``, ``/backup/fx/{base}/{quote}/rates``).
They share the ``/backup`` prefix and the ``Backup & Export`` tag of ``backup_router``; the include order is the
registration order of the routes.
"""

from fastapi import APIRouter

from backend.app.api.v1.backup import exports, instance, panel, restore

backup_router = APIRouter(prefix="/backup", tags=["Backup & Export"])
backup_router.include_router(instance.instance_router)
backup_router.include_router(panel.panel_router)
backup_router.include_router(restore.restore_router)
backup_router.include_router(exports.exports_router)
