from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from backend.app.schemas.common import BackwardFillInfo


class CurrentValueModel(BaseModel):
    value: Decimal = Field(..., description="Numeric price or value")
    currency: str
    as_of_date: date
    source: Optional[str] = None

    # Pydantic v2 style config
    model_config = {
        "from_attributes": True,
        "json_encoders": {Decimal: lambda v: format(v, 'f')},
    }


class PricePointModel(BaseModel):
    date: date
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Decimal
    volume: Optional[Decimal] = None
    currency: Optional[str] = None
    backfill_info: Optional[BackwardFillInfo] = None

    # Pydantic v2 style config
    model_config = {
        "from_attributes": True,
        "json_encoders": {Decimal: lambda v: format(v, 'f')},
    }

    @field_validator("open", "high", "low", "close", "volume", mode="before")
    def coerce_decimal(cls, v):
        if v is None:
            return v
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))


class HistoricalDataModel(BaseModel):
    prices: List[PricePointModel]
    currency: Optional[str] = None
    source: Optional[str] = None

    model_config = {"from_attributes": True}

    # keep JSON encoders consistent if serialized directly
    model_config.update({"json_encoders": {Decimal: lambda v: format(v, 'f')}})
