"""Domain-agnostic signal endpoints (preview computation).

The chart-settings modal previews overlay signals on a demo curve. Local
signals (benchmarks, FX-pair, asset-comparison) are computed in the browser,
but backend indicators (SMA, EMA, MACD, RSI, Bollinger, …) are Python plugins
and cannot run client-side. This endpoint computes them on caller-supplied
synthetic points so the preview can render them without a real asset/pair.

No stored/DB data is touched: the points come from the request body.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.signals import (
    SignalCadence,
    SignalExecutionContext,
    SignalPreviewRequest,
    SignalPreviewResponse,
    SignalPricePoint,
)
from backend.app.services.signal_service import (
    SignalRequestValidationError,
    SignalService,
)

signals_router = APIRouter(prefix="/signals", tags=["Signals"])


@signals_router.post("/preview", response_model=SignalPreviewResponse)
async def compute_signal_preview(
    request: SignalPreviewRequest,
    _current_user: User = Depends(get_current_user),
) -> SignalPreviewResponse:
    """Compute overlay signals on caller-supplied synthetic points.

    Returns one `SignalResult` per requested signal. When no signals or no
    points are supplied, an empty result set is returned (nothing to preview).
    """
    if not request.signals or not request.points:
        return SignalPreviewResponse(signals=[])

    price_points = [SignalPricePoint(date=point.date, close=point.value) for point in request.points]
    date_range = DateRangeModel(
        start=request.points[0].date,
        end=request.points[-1].date,
    )
    context = SignalExecutionContext(
        domain=request.domain,
        requested_range=date_range,
        cadence=SignalCadence.DAILY,
        source_reference=f"preview:{request.domain.value}",
    )

    signal_service = SignalService()
    try:
        results = await signal_service.compute(request.signals, price_points, context)
    except SignalRequestValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SignalPreviewResponse(signals=results)
