"""Focused HTTP mapping tests for signal request validation failures."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from backend.app.api.v1.assets import query_prices_bulk
from backend.app.api.v1.fx import convert_currency_bulk
from backend.app.schemas.common import Currency
from backend.app.schemas.fx import FXConversionRequest
from backend.app.schemas.signals import SignalRequest
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.signal_service import (
    SignalRequestValidationError,
    SignalService,
)


@pytest.mark.asyncio
async def test_asset_price_query_maps_signal_validation_to_422(monkeypatch):
    monkeypatch.setattr(
        AssetSourceManager,
        "get_prices_bulk",
        AsyncMock(side_effect=SignalRequestValidationError("invalid annotation source")),
    )

    with pytest.raises(HTTPException) as exc:
        await query_prices_bulk([], AsyncMock(), None)

    assert exc.value.status_code == 422
    assert exc.value.detail == "invalid annotation source"


@pytest.mark.asyncio
async def test_fx_conversion_maps_signal_validation_to_422(monkeypatch):
    def fail_prepare_plan(*_args, **_kwargs):
        raise SignalRequestValidationError("band source is not a band")

    monkeypatch.setattr(SignalService, "prepare_plan", fail_prepare_plan)
    request = FXConversionRequest(
        from_amount=Currency(code="EUR", amount=1),
        to="USD",
        date_range={"start": "2026-01-01", "end": "2026-01-02"},
        signals=[
            SignalRequest(
                instance_id="ema",
                signal_code="EMA",
                params={"period": 20},
            )
        ],
    )

    with pytest.raises(HTTPException) as exc:
        await convert_currency_bulk([request], AsyncMock(), None)

    assert exc.value.status_code == 422
    assert exc.value.detail == "band source is not a band"
