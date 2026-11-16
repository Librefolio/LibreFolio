"""Enricher endpoints (``/assets/enrichers``, plan 68 B3): the installed enrichers and what they declare.

The bindings of an asset are written with the asset (``POST`` and ``PATCH /assets``, field ``enrichers``) and read with
it (``GET /assets``, field ``enrichers``): one door to write, as for the profile (plan §3.5).
"""

from fastapi import APIRouter, Depends

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.schemas.assets.enrichers import FAEnrichersCatalogue
from backend.app.services.enrichers.bindings import enrichers_catalogue

enricher_router = APIRouter()


@enricher_router.get("/enrichers", response_model=FAEnrichersCatalogue, tags=["FA Enrichers"])
def list_enrichers(_current_user: User = Depends(get_current_user)) -> FAEnrichersCatalogue:
    """The installed enrichers with what each declares, and per asset type their default order (degree, then code)."""
    return enrichers_catalogue()
