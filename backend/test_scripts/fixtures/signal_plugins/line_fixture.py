"""Test-only rolling line signal."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

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


class LineFixtureParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length: int = Field(
        3,
        ge=2,
        le=50,
        json_schema_extra={
            "x-i18n-key": "signals.fixture.length",
            "x-control-order": 1,
            "x-step": 1,
        },
    )


@register_plugin(FixtureSignalPluginRegistry)
class LineFixturePlugin(SignalPlugin):
    signal_code = "FIXTURE_LINE"
    implementation_version = "1.0.0"
    category = SignalCategory.TREND
    display_name_key = "signals.fixtureLine.name"
    description_key = "signals.fixtureLine.description"
    icon = "activity"
    params_model = LineFixtureParams
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="average",
            label_key="signals.fixtureLine.average",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.PRICE,
            axis=SignalAxisSpec(key="price", role=SignalAxisRole.PRICE),
        ),
    )
    compatible_domains = (SignalDomain.ASSET, SignalDomain.FX)

    @classmethod
    def warmup_requirement(
        cls,
        params: LineFixtureParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        return SignalWarmupRequirement(
            minimum_points=params.length,
            stabilization_points=0,
            total_points=params.length,
        )

    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: LineFixtureParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        window: list[float] = []
        output: list[SignalValuePoint] = []
        for point in price_points:
            window.append(float(point.close))
            if len(window) > params.length:
                window.pop(0)
            value = sum(window) / params.length if len(window) == params.length else None
            output.append(SignalValuePoint(date=point.date, value=value))
        return SignalComputation(
            series=[
                SignalLineSeries(
                    key="average",
                    label_key="signals.fixtureLine.average",
                    unit=SignalUnit.PRICE,
                    axis=SignalAxisSpec(key="price", role=SignalAxisRole.PRICE),
                    points=output,
                )
            ]
        )
