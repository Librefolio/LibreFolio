"""Asset API (``/assets``): one module per resource, composed here into ``asset_router`` (C2).

``router.py`` includes ``asset_router``. The resource modules own their routes: ``crud.py`` (create, read, patch,
delete and merge), ``market_data.py`` (market-data summary and wipe), ``prices.py`` (``/assets/prices``),
``providers.py`` (``/assets/provider``) and ``events.py`` (``/assets/events``). Each is included with the ``/assets``
prefix and the ``FA (Financial Assets)`` tag; the include order is the registration order of the routes.
"""

from fastapi import APIRouter

from backend.app.api.v1.assets import crud, events, market_data, prices, providers

asset_router = APIRouter()
for _resource_router in (crud.crud_router, market_data.market_data_router, prices.price_router, providers.provider_router, events.event_router):
    asset_router.include_router(_resource_router, prefix="/assets", tags=["FA (Financial Assets)"])
