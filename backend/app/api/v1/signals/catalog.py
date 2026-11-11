"""Signal catalogs of the two domains that have one: asset prices and FX rates.

The signal definitions are the same registry for both; each catalog lists those compatible with its domain. The URLs stay under their
domain (``GET /assets/prices/signals`` and ``GET /fx/currencies/signals``) and the routes keep their tags (the domain's group and its page): only the code lives
with the other signal routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.schemas.signals.result import SignalCatalogResponse
from backend.app.schemas.signals.vocabulary import SignalDomain
from backend.app.services.signals.registry import SignalPluginRegistry

asset_catalog_router = APIRouter(prefix="/assets/prices", tags=["FA (Financial Assets)", "FA Prices"])
fx_catalog_router = APIRouter(prefix="/fx/currencies", tags=["FX (Forex)", "FX Currencies"])


@asset_catalog_router.get("/signals", response_model=SignalCatalogResponse)
async def list_asset_signal_catalog(
    _current_user: User = Depends(get_current_user),
) -> SignalCatalogResponse:
    """Return static signal definitions compatible with Asset price data."""
    return SignalCatalogResponse(items=[definition for definition in SignalPluginRegistry.list_definitions() if SignalDomain.ASSET in definition.compatible_domains])


@fx_catalog_router.get("/signals", response_model=SignalCatalogResponse)
async def list_fx_signal_catalog(
    _current_user: User = Depends(get_current_user),
) -> SignalCatalogResponse:
    """Return static signal definitions compatible with FX close rates."""
    return SignalCatalogResponse(items=[definition for definition in SignalPluginRegistry.list_definitions() if SignalDomain.FX in definition.compatible_domains])
