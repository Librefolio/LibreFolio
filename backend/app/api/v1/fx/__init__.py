"""FX API (``/fx``): one module per resource, composed here into ``fx_router`` (C2).

``router.py`` includes ``fx_router``. ``providers.py`` owns ``/fx/providers`` (provider catalog, conversion routes) and
``currencies.py`` owns ``/fx/currencies`` (sync, manual rates, signal catalog, conversion); the include order is the
registration order of the routes.
"""

from fastapi import APIRouter

from backend.app.api.v1.fx import currencies, providers

fx_router = APIRouter(prefix="/fx", tags=["FX (Forex)"])
fx_router.include_router(providers.router_providers)
fx_router.include_router(currencies.router_currencies)
