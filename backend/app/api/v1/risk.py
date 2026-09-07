"""Catalog and bulk query endpoints for risk analytics."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.schemas.risk import (
    RiskCatalogResponse,
    RiskQueryRequest,
    RiskQueryResponse,
)
from backend.app.schemas.risk_scenarios import RiskScenarioCatalogResponse
from backend.app.services.risk.scenario_catalog import (
    get_loaded_risk_scenario_catalog,
)
from backend.app.services.risk.service import (
    RiskScopeAccessError,
    RiskScopeNotFoundError,
    RiskService,
)

router = APIRouter(prefix="/risk", tags=["Risk Analysis"])


def get_risk_service(
    session: AsyncSession = Depends(get_session_generator),
) -> RiskService:
    return RiskService(session)


def get_risk_scenario_catalog() -> RiskScenarioCatalogResponse:
    try:
        return get_loaded_risk_scenario_catalog()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.get(
    "/catalog",
    response_model=RiskCatalogResponse,
    summary="List risk analytics",
)
async def get_risk_catalog(
    _current_user: User = Depends(get_current_user),
) -> RiskCatalogResponse:
    return RiskCatalogResponse(items=RiskService.catalog())


@router.get(
    "/scenario-catalog",
    response_model=RiskScenarioCatalogResponse,
    summary="List typed risk scenarios",
)
async def get_scenario_catalog(
    _current_user: User = Depends(get_current_user),
    catalog: RiskScenarioCatalogResponse = Depends(get_risk_scenario_catalog),
) -> RiskScenarioCatalogResponse:
    return catalog


@router.post(
    "/query",
    response_model=RiskQueryResponse,
    summary="Execute a bulk risk query",
    responses={
        403: {"description": "Requested portfolio broker subset is not fully accessible."},
        404: {"description": "Requested risk scope does not exist."},
    },
)
async def query_risk(
    body: RiskQueryRequest,
    service: RiskService = Depends(get_risk_service),
    current_user: User = Depends(get_current_user),
) -> RiskQueryResponse:
    try:
        return await service.execute(
            user_id=current_user.id,
            request=body,
        )
    except RiskScopeAccessError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc
    except RiskScopeNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
