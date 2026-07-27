"""Test-only band plus flat composite output."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.signals import (
    SignalAxisRole,
    SignalAxisSpec,
    SignalBandPoint,
    SignalBandSeries,
    SignalBarSeries,
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


class BandCompositeFixtureParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spread: float = Field(2.0, gt=0, le=100)


@register_plugin(FixtureSignalPluginRegistry)
class BandCompositeFixturePlugin(SignalPlugin):
    signal_code = "FIXTURE_BAND_COMPOSITE"
    implementation_version = "1.0.0"
    category = SignalCategory.VOLATILITY
    display_name_key = "signals.fixtureBandComposite.name"
    description_key = "signals.fixtureBandComposite.description"
    semantic_id = "fixture_band_composite"
    semantic_description = "Test composite containing band, line, and bar outputs."
    icon = "chart-no-axes-combined"
    params_model = BandCompositeFixtureParams
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="envelope",
            label_key="signals.fixtureBandComposite.envelope",
            semantic_id="fixture_band_composite.envelope",
            semantic_description="Test lower, middle, and upper envelope.",
            kind=SignalSeriesKind.BAND,
            unit=SignalUnit.PRICE,
            axis=SignalAxisSpec(key="price", role=SignalAxisRole.PRICE),
        ),
        SignalOutputSpec(
            key="momentum",
            label_key="signals.fixtureBandComposite.momentum",
            semantic_id="fixture_band_composite.momentum",
            semantic_description="Test close-price displacement from the first point.",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.INDEX,
            axis=SignalAxisSpec(key="fixture-composite", role=SignalAxisRole.INDEPENDENT),
        ),
        SignalOutputSpec(
            key="histogram",
            label_key="signals.fixtureBandComposite.histogram",
            semantic_id="fixture_band_composite.histogram",
            semantic_description="Negated test close-price displacement.",
            kind=SignalSeriesKind.BAR,
            unit=SignalUnit.INDEX,
            axis=SignalAxisSpec(key="fixture-composite", role=SignalAxisRole.INDEPENDENT),
        ),
    )
    compatible_domains = (SignalDomain.ASSET, SignalDomain.FX)

    @classmethod
    def warmup_requirement(
        cls,
        params: BandCompositeFixtureParams,
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
        params: BandCompositeFixtureParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        first_close = float(price_points[0].close)
        band_points: list[SignalBandPoint] = []
        momentum_points: list[SignalValuePoint] = []
        histogram_points: list[SignalValuePoint] = []
        for point in price_points:
            close = float(point.close)
            momentum = close - first_close
            band_points.append(
                SignalBandPoint(
                    date=point.date,
                    lower=close - params.spread,
                    middle=close,
                    upper=close + params.spread,
                )
            )
            momentum_points.append(SignalValuePoint(date=point.date, value=momentum))
            histogram_points.append(SignalValuePoint(date=point.date, value=-momentum))
        composite_axis = SignalAxisSpec(
            key="fixture-composite",
            role=SignalAxisRole.INDEPENDENT,
        )
        return SignalComputation(
            series=[
                SignalBandSeries(
                    key="envelope",
                    label_key="signals.fixtureBandComposite.envelope",
                    semantic_id="fixture_band_composite.envelope",
                    semantic_description="Test lower, middle, and upper envelope.",
                    unit=SignalUnit.PRICE,
                    axis=SignalAxisSpec(key="price", role=SignalAxisRole.PRICE),
                    points=band_points,
                ),
                SignalLineSeries(
                    key="momentum",
                    label_key="signals.fixtureBandComposite.momentum",
                    semantic_id="fixture_band_composite.momentum",
                    semantic_description="Test close-price displacement from the first point.",
                    unit=SignalUnit.INDEX,
                    axis=composite_axis,
                    points=momentum_points,
                ),
                SignalBarSeries(
                    key="histogram",
                    label_key="signals.fixtureBandComposite.histogram",
                    semantic_id="fixture_band_composite.histogram",
                    semantic_description="Negated test close-price displacement.",
                    unit=SignalUnit.INDEX,
                    axis=composite_axis,
                    points=histogram_points,
                ),
            ]
        )
