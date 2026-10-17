"""Library-agnostic orchestration for technical signal plugins: `SignalService` plans a batch (`planning.py`) and
runs it in one worker thread (`execution.py`)."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any, Optional

from backend.app.schemas.signals import (
    SignalAnnotationRequest,
    SignalEventPoint,
    SignalExecutionContext,
    SignalPricePoint,
    SignalRequest,
    SignalResult,
    SignalSourceCapability,
)
from backend.app.services.signals.annotations import SignalAnnotationService
from backend.app.services.signals.execution import SignalPreparedSeriesBundle, execute_signal_plan
from backend.app.services.signals.planning import SignalExecutionPlan, prepare_signal_plan
from backend.app.services.signals.registry import SignalPluginRegistry


class SignalService:
    """Resolve, plan and execute signal plugins as one sequential worker batch."""

    def __init__(
        self,
        registry: type[SignalPluginRegistry] = SignalPluginRegistry,
        annotation_service: Optional[SignalAnnotationService] = None,
    ) -> None:
        self.registry = registry
        self.annotation_service = annotation_service or SignalAnnotationService()

    def prepare_plan(
        self,
        requests: Sequence[SignalRequest | dict[str, Any]],
        context: SignalExecutionContext,
        annotation_requests: Sequence[SignalAnnotationRequest | dict[str, Any]] = (),
    ) -> SignalExecutionPlan:
        return prepare_signal_plan(self.registry, requests, context, annotation_requests)

    async def execute(
        self,
        plan: SignalExecutionPlan,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint] = (),
        *,
        events_loaded: bool = False,
        prepared_series_bundle: Optional[SignalPreparedSeriesBundle] = None,
        source_capability: Optional[SignalSourceCapability] = None,
    ) -> list[SignalResult]:
        """Execute the entire signal batch in one worker thread."""
        return await asyncio.to_thread(
            execute_signal_plan,
            self.annotation_service,
            plan,
            tuple(price_points),
            tuple(event_points),
            events_loaded,
            prepared_series_bundle,
            source_capability,
        )

    async def compute(
        self,
        requests: Sequence[SignalRequest | dict[str, Any]],
        price_points: Sequence[SignalPricePoint],
        context: SignalExecutionContext,
        event_points: Sequence[SignalEventPoint] = (),
        *,
        events_loaded: bool = False,
        annotation_requests: Sequence[SignalAnnotationRequest | dict[str, Any]] = (),
        prepared_series_bundle: Optional[SignalPreparedSeriesBundle] = None,
        source_capability: Optional[SignalSourceCapability] = None,
    ) -> list[SignalResult]:
        plan = self.prepare_plan(
            requests,
            context,
            annotation_requests,
        )
        return await self.execute(
            plan,
            price_points,
            event_points,
            events_loaded=events_loaded,
            prepared_series_bundle=prepared_series_bundle,
            source_capability=source_capability,
        )


__all__ = ["SignalService"]
