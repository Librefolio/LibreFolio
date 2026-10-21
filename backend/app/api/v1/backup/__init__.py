"""Backup and export API (``/backup``): one module per resource, composed here into ``backup_router`` (C2).

``router.py`` includes ``backup_router``. ``instance.py`` owns the backup of the whole instance (``/backup/instance``,
an archive built in the background, for administrators), ``panel.py`` the same jobs for a hosting panel with a token
(``/backup/panel/jobs``), both on ``job_views.py``, ``restore.py`` the check of an archive before a restore
(``/backup/restore``, for administrators), and ``exports.py`` the per-series snapshot exports
(``/backup/asset/{id}/prices``, ``/backup/asset/{id}/events``, ``/backup/fx/{base}/{quote}/rates``).
They share the ``/backup`` prefix of ``backup_router``; the include order is the registration order of the routes. Each
include gives its tag, ``Backup & Export``, but ``panel.py``, whose routes carry the hosting panel's tag alone (lot
H-61): FastAPI adds the tags of a router to the ones of what it includes, never replaces them, so the router itself has
none.
"""

from fastapi import APIRouter

from backend.app.api.v1.backup import exports, instance, panel, restore
from backend.app.services.platform.hosting_panel.access import HOSTING_PANEL_TAG

BACKUP_TAG = "Backup & Export"

backup_router = APIRouter(prefix="/backup")
backup_router.include_router(instance.instance_router, tags=[BACKUP_TAG])
backup_router.include_router(panel.panel_router, tags=[HOSTING_PANEL_TAG])
backup_router.include_router(restore.restore_router, tags=[BACKUP_TAG])
backup_router.include_router(exports.exports_router, tags=[BACKUP_TAG])
