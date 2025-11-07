from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session
from backend.app.schemas.assets import (
    AssetProviderAssignmentModel,
    PricePointModel,
)
from backend.app.services.asset_source import AssetSourceManager

router = APIRouter(prefix="/assets", tags=["Assets"])


class RefreshItem(BaseModel):
    asset_id: int
    start_date: date
    end_date: date
    force: Optional[bool] = Field(False)


class BulkRefreshRequest(BaseModel):
    requests: List[RefreshItem]


@router.post("/price/refresh/bulk")
async def refresh_prices_bulk(request: BulkRefreshRequest, session: AsyncSession = Depends(get_session)):
    try:
        # Convert tagged objects to plain dicts for service
        payload = [r.model_dump() for r in request.requests]
        results = await AssetSourceManager.bulk_refresh_prices(payload, session)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{asset_id}/price/refresh")
async def refresh_prices_single(asset_id: int, start_date: date, end_date: date, session: AsyncSession = Depends(get_session)):
    try:
        result = await AssetSourceManager.refresh_price(asset_id, start_date, end_date, session)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
