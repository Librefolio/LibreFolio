"""Test-only plugin that raises during compute."""

from __future__ import annotations

from collections.abc import Sequence

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
    SignalOutputSpec,
    SignalPriceField,
    SignalPricePoint,
    SignalSeriesKind,
    SignalUnit,
    SignalWarmupRequirement,
)
from backend.app.services.provider_registry import register_plugin
from backend.app.services.signal_plugins.base import SignalPlugin
from backend.test_scripts.fixtures.signal_plugins.registry import (
    FixtureSignalPluginRegistry,
)


class FailingFixtureParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


@register_plugin(FixtureSignalPluginRegistry)
class FailingFixturePlugin(SignalPlugin):
    signal_code = "FIXTURE_FAILING"
    implementation_version = "1.0.0"
    category = SignalCategory.MOMENTUM
    display_name_key = "signals.fixtureFailing.name"
    description_key = "signals.fixtureFailing.description"
    icon = "triangle-alert"
    params_model = FailingFixtureParams
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="failure",
            label_key="signals.fixtureFailing.failure",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.INDEX,
            axis=SignalAxisSpec(key="failure", role=SignalAxisRole.INDEPENDENT),
        ),
    )
    compatible_domains = (SignalDomain.ASSET, SignalDomain.FX)

    @classmethod
    def warmup_requirement(
        cls,
        params: FailingFixtureParams,
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
        params: FailingFixtureParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        raise RuntimeError("fixture compute failure")
