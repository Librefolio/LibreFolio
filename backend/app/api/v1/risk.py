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


@router.get(
    "/catalog",
    response_model=RiskCatalogResponse,
    summary="List risk analytics",
)
async def get_risk_catalog(
    _current_user: User = Depends(get_current_user),
) -> RiskCatalogResponse:
    return RiskCatalogResponse(items=RiskService.catalog())


@router.post(
    "/query",
    response_model=RiskQueryResponse,
    summary="Execute a bulk risk query",
    responses={
        403: {"description": "Requested broker scope is not accessible."},
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
