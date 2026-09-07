"""Test-only plugin with parameter-aware stabilization history."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.signals import (
    SignalAggregationProfile,
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


class WarmupFixtureParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_points: int = Field(2, ge=1, le=100)
    stabilization_points: int = Field(4, ge=0, le=500)


@register_plugin(FixtureSignalPluginRegistry)
class WarmupFixturePlugin(SignalPlugin):
    signal_code = "FIXTURE_WARMUP"
    implementation_version = "1.0.0"
    category = SignalCategory.TREND
    display_name_key = "signals.fixtureWarmup.name"
    description_key = "signals.fixtureWarmup.description"
    semantic_id = "fixture_warmup"
    semantic_description = "Test signal with configurable warm-up history."
    icon = "history"
    params_model = WarmupFixtureParams
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="close",
            label_key="signals.fixtureWarmup.close",
            semantic_id="fixture_warmup.close",
            semantic_description="Test closing-price timeline.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.PRICE,
            axis=SignalAxisSpec(key="price", role=SignalAxisRole.PRICE),
        ),
    )
    compatible_domains = (SignalDomain.ASSET, SignalDomain.FX)

    @classmethod
    def warmup_requirement(
        cls,
        params: WarmupFixtureParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        return SignalWarmupRequirement(
            minimum_points=params.minimum_points,
            stabilization_points=params.stabilization_points,
            total_points=params.minimum_points + params.stabilization_points,
        )

    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: WarmupFixtureParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        return SignalComputation(
            series=[
                SignalLineSeries(
                    key="close",
                    label_key="signals.fixtureWarmup.close",
                    semantic_id="fixture_warmup.close",
                    semantic_description="Test closing-price timeline.",
                    unit=SignalUnit.PRICE,
                    axis=SignalAxisSpec(key="price", role=SignalAxisRole.PRICE),
                    points=[SignalValuePoint(date=point.date, value=float(point.close)) for point in price_points],
                )
            ]
        )
