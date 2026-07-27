"""Test-only signal requiring both close prices and dividend events."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.signals import (
    SignalAxisRole,
    SignalAxisSpec,
    SignalCategory,
    SignalComputation,
    SignalDomain,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputRequirements,
    SignalLineSeries,
    SignalOutputSpec,
    SignalPriceField,
    SignalPricePoint,
    SignalSeriesKind,
    SignalUnit,
    SignalValuePoint,
    SignalWarmupRequirement,
)
from backend.app.services.provider_registry import register_plugin
from backend.app.services.signal_plugins.base import SignalPlugin
from backend.test_scripts.fixtures.signal_plugins.registry import (
    FixtureSignalPluginRegistry,
)


class EventsFixtureParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


@register_plugin(FixtureSignalPluginRegistry)
class EventsFixturePlugin(SignalPlugin):
    signal_code = "FIXTURE_EVENTS"
    implementation_version = "1.0.0"
    category = SignalCategory.VOLUME
    display_name_key = "signals.fixtureEvents.name"
    description_key = "signals.fixtureEvents.description"
    semantic_id = "fixture_cumulative_events"
    semantic_description = "Test cumulative event values over time."
    icon = "calendar-range"
    params_model = EventsFixtureParams
    input_requirements = SignalInputRequirements(
        price_fields=[SignalPriceField.CLOSE],
        requires_events=True,
        event_types=["DIVIDEND"],
    )
    output_specs = (
        SignalOutputSpec(
            key="cumulative-events",
            label_key="signals.fixtureEvents.cumulative",
            semantic_id="fixture_cumulative_events.value",
            semantic_description="Test cumulative value of matching events.",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.INDEX,
            axis=SignalAxisSpec(key="events", role=SignalAxisRole.INDEPENDENT),
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)

    @classmethod
    def warmup_requirement(
        cls,
        params: EventsFixtureParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        return SignalWarmupRequirement(
            minimum_points=1,
            stabilization_points=0,
            total_points=1,
        )

    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: EventsFixtureParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        values_by_date: dict = {}
        for event in event_points:
            if event.type == "DIVIDEND":
                values_by_date[event.date] = values_by_date.get(
                    event.date,
                    Decimal("0"),
                ) + (event.value or Decimal("0"))
        cumulative = Decimal("0")
        output: list[SignalValuePoint] = []
        for point in price_points:
            cumulative += values_by_date.get(point.date, Decimal("0"))
            output.append(
                SignalValuePoint(
                    date=point.date,
                    value=float(cumulative),
                )
            )
        return SignalComputation(
            series=[
                SignalLineSeries(
                    key="cumulative-events",
                    label_key="signals.fixtureEvents.cumulative",
                    semantic_id="fixture_cumulative_events.value",
                    semantic_description="Test cumulative value of matching events.",
                    unit=SignalUnit.INDEX,
                    axis=SignalAxisSpec(
                        key="events",
                        role=SignalAxisRole.INDEPENDENT,
                    ),
                    points=output,
                )
            ]
        )
