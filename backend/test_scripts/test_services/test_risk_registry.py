"""Tests for the pure RiskAnalytic contract and strict registry."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.risk import (
    RiskKpiOutput,
    RiskMode,
    RiskOutputKind,
    RiskScopeKind,
)
from backend.app.services.provider_registry import (
    DuplicatePluginCodeError,
    RiskAnalyticRegistry,
    register_plugin,
)
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
)


class DemoParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_free_annual_rate: float = Field(0, gt=-1)


class DemoRiskAnalytic(RiskAnalytic):
    analytic_code = "demo_risk"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.demo.name"
    description_i18n_key = "risk.demo.description"
    output_kind = RiskOutputKind.KPI
    supported_scopes = (RiskScopeKind.PORTFOLIO,)
    supported_modes = (RiskMode.HISTORICAL,)
    params_model = DemoParams
    min_observations = 2

    def compute(self, params, context):
        return RiskComputation(
            output=RiskKpiOutput(
                volatility=0.1,
                max_drawdown=0.2,
                max_drawdown_duration_days=3,
            ),
            method="demo",
        )


class InlineRiskRegistry(RiskAnalyticRegistry):
    @classmethod
    def _get_plugin_folder(cls) -> str:
        return "inline_risk_registry_unused"


@pytest.fixture(autouse=True)
def reset_inline_registry():
    InlineRiskRegistry._plugins = {}
    InlineRiskRegistry._discovery_done = False
    InlineRiskRegistry._discovery_errors = ()


def test_register_risk_analytic_and_publish_catalog():
    @register_plugin(InlineRiskRegistry)
    class DecoratedRisk(DemoRiskAnalytic):
        analytic_code = "decorated_risk"

    assert InlineRiskRegistry.get_plugin(" DECORATED_RISK ") is DecoratedRisk
    definition = InlineRiskRegistry.list_definitions()[0]
    assert definition.analytic_code == "decorated_risk"
    assert definition.output_kind == RiskOutputKind.KPI
    assert definition.supported_scopes == [RiskScopeKind.PORTFOLIO]
    assert definition.parameters_schema["properties"]["risk_free_annual_rate"]["default"] == 0


def test_risk_analytic_validates_params_and_definition():
    params = DemoRiskAnalytic.validate_params({"risk_free_annual_rate": 0.02})
    assert params.risk_free_annual_rate == 0.02
    with pytest.raises(ValueError):
        DemoRiskAnalytic.validate_params({"unknown": True})

    class LowercaseRequired(DemoRiskAnalytic):
        analytic_code = "NOT_CANONICAL"

    with pytest.raises(ValueError, match="canonical lowercase"):
        InlineRiskRegistry.register(LowercaseRequired)


def test_registry_rejects_duplicate_non_risk_and_unsafe_params():
    class FirstRisk(DemoRiskAnalytic):
        analytic_code = "duplicate_risk"

    class SecondRisk(DemoRiskAnalytic):
        analytic_code = "duplicate_risk"

    InlineRiskRegistry.register(FirstRisk)
    with pytest.raises(DuplicatePluginCodeError, match="duplicate_risk"):
        InlineRiskRegistry.register(SecondRisk)

    class NotRisk:
        analytic_code = "not_risk"

    with pytest.raises(TypeError, match="extend RiskAnalytic"):
        InlineRiskRegistry.register(NotRisk)

    class UnsafeParams(BaseModel):
        value: int = 1

    class UnsafeRisk(DemoRiskAnalytic):
        analytic_code = "unsafe_risk"
        params_model = UnsafeParams

    with pytest.raises(ValueError, match="extra='forbid'"):
        InlineRiskRegistry.register(UnsafeRisk)


def test_registry_rejects_abstract_and_stateful_analytics():
    with pytest.raises(TypeError, match="concrete"):
        InlineRiskRegistry.register(RiskAnalytic)

    class StatefulRisk(DemoRiskAnalytic):
        analytic_code = "stateful_risk"

        def __init__(self, dependency):
            self.dependency = dependency

    with pytest.raises(TypeError, match="without arguments"):
        InlineRiskRegistry.register(StatefulRisk)
