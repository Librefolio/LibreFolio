from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator


class CommonConfig:
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": []})


class BackwardFillInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actual_rate_date: date
    days_back: int


class CurrentValueModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: Decimal
    currency: str
    as_of_date: date
    source: Optional[str] = None

    @field_validator("value", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        return Decimal(str(v))


class PricePointModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: date
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Decimal
    volume: Optional[Decimal] = None
    currency: Optional[str] = None
    backward_fill_info: Optional[BackwardFillInfo] = None

    @field_validator("open", "high", "low", "close", "volume", mode="before")
    @classmethod
    def parse_optional_decimal(cls, v):
        if v is None:
            return None
        return Decimal(str(v))


class HistoricalDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prices: List[PricePointModel]
    currency: Optional[str] = None
    source: Optional[str] = None


class AssetProviderAssignmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: int
    provider_code: str
    provider_params: Optional[dict] = None
    last_fetch_at: Optional[str] = None


# Export convenience
__all__ = [
    "BackwardFillInfo",
    "CurrentValueModel",
    "PricePointModel",
    "HistoricalDataModel",
    "AssetProviderAssignmentModel",
]

