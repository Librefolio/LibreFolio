"""Signal API: ``/signals/preview`` and the signal catalogs of the asset and FX domains (CP5).

``router.py`` includes ``signals_router`` (``/signals``) and the two catalog routers, which keep their URLs under ``/assets/prices`` and
``/fx/currencies``. The package re-exports nothing besides these routers.
"""

from fastapi import APIRouter

from backend.app.api.v1.signals import catalog, preview

signals_router = APIRouter(prefix="/signals", tags=["Signals"])
signals_router.include_router(preview.preview_router)

asset_catalog_router = catalog.asset_catalog_router
fx_catalog_router = catalog.fx_catalog_router

__all__ = ["asset_catalog_router", "fx_catalog_router", "signals_router"]
