"""Signal preview: the request and the response of the indicator preview."""

from __future__ import annotations

from datetime import date
from typing import List

from pydantic import Field, model_validator

from backend.app.schemas.signals.base import SignalDecimal, SignalModel, _ensure_strictly_increasing
from backend.app.schemas.signals.result import SignalRequest, SignalResult
from backend.app.schemas.signals.vocabulary import SignalDomain


class SignalPreviewPoint(SignalModel):
    """A single synthetic data point (date + close value) for a signal preview."""

    date: date
    value: SignalDecimal


class SignalPreviewRequest(SignalModel):
    """Compute one or more signals on caller-supplied synthetic points.

    Used by the chart-settings preview (global mode) to render backend
    indicators on a demo curve, since backend indicators cannot run in the
    browser. No stored/DB data is involved.
    """

    domain: SignalDomain
    points: List[SignalPreviewPoint] = Field(default_factory=list, max_length=2000)
    signals: List[SignalRequest] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def validate_points(self) -> SignalPreviewRequest:
        _ensure_strictly_increasing([point.date for point in self.points], "preview point")
        return self


class SignalPreviewResponse(SignalModel):
    signals: List[SignalResult] = Field(default_factory=list)
