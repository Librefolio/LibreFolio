"""Contract tests backed by auto-discovered test-only signal plugins."""

from __future__ import annotations

import sys
from datetime import date

import pytest

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.signals import (
    SignalDomain,
    SignalExecutionContext,
    SignalSeriesKind,
)
from backend.app.services.provider_registry import SignalPluginRegistry
from backend.test_scripts.fixtures.signal_plugins.registry import (
    FixtureSignalPluginRegistry,
)
from backend.test_scripts.fixtures.signals import (
    make_signal_event_points,
    make_signal_price_points,
)

EXPECTED_CODES = {
    "FIXTURE_BAND_COMPOSITE",
    "FIXTURE_EVENTS",
    "FIXTURE_FAILING",
    "FIXTURE_LINE",
    "FIXTURE_WARMUP",
}
FIXTURE_NAMESPACE = "backend.test_scripts.fixtures.signal_plugins"


@pytest.fixture(autouse=True)
def reset_fixture_registry():
    FixtureSignalPluginRegistry._plugins = {}
    FixtureSignalPluginRegistry._discovery_done = False
    FixtureSignalPluginRegistry._discovery_errors = ()
    for module_name in tuple(sys.modules):
        if module_name.startswith(f"{FIXTURE_NAMESPACE}.") and module_name != f"{FIXTURE_NAMESPACE}.registry":
            sys.modules.pop(module_name, None)
    yield


@pytest.fixture
def context() -> SignalExecutionContext:
    return SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=date(2026, 1, 1),
            end=date(2026, 1, 6),
        ),
        source_reference="fixture:asset",
    )


def test_fixture_registry_discovers_expected_plugins_only():
    assert set(FixtureSignalPluginRegistry.list_plugin_codes()) == EXPECTED_CODES
    assert FixtureSignalPluginRegistry.get_discovery_errors() == ()
    assert set(SignalPluginRegistry.list_plugin_codes()).isdisjoint(EXPECTED_CODES)


def test_fixture_discovery_is_idempotent():
    first = FixtureSignalPluginRegistry.list_plugin_codes()
    second = FixtureSignalPluginRegistry.list_plugin_codes()
    assert first == second
    assert len(first) == len(set(first))


def test_fixture_catalog_is_sorted_and_json_serializable():
    definitions = FixtureSignalPluginRegistry.list_definitions()
    assert [definition.signal_code for definition in definitions] == sorted(EXPECTED_CODES)
    for definition in definitions:
        assert definition.model_dump_json()
        assert definition.params_schema["additionalProperties"] is False
        assert definition.ai_export_temporal_rules == []


def test_line_fixture_validates_params_warmup_and_output(context):
    plugin_class = FixtureSignalPluginRegistry.get_plugin("fixture_line")
    params = plugin_class.validate_params({"length": 3})
    requirement = plugin_class.warmup_requirement(params, context)
    computation = plugin_class().compute(
        make_signal_price_points(),
        [],
        params,
        context,
    )

    assert requirement.minimum_points == 3
    assert requirement.stabilization_points == 0
    assert [point.value for point in computation.series[0].points[:3]] == [
        None,
        None,
        101.0,
    ]


def test_band_composite_fixture_returns_flat_aligned_series(context):
    plugin_class = FixtureSignalPluginRegistry.get_plugin("FIXTURE_BAND_COMPOSITE")
    params = plugin_class.validate_params({"spread": 2.5})
    computation = plugin_class().compute(
        make_signal_price_points(),
        [],
        params,
        context,
    )

    assert [series.key for series in computation.series] == [
        "envelope",
        "momentum",
        "histogram",
    ]
    assert [series.kind for series in computation.series] == [
        SignalSeriesKind.BAND,
        SignalSeriesKind.LINE,
        SignalSeriesKind.BAR,
    ]
    assert computation.series[0].points[0].model_dump() == {
        "date": date(2026, 1, 1),
        "lower": 97.5,
        "middle": 100.0,
        "upper": 102.5,
    }


def test_warmup_fixture_is_parameter_aware(context):
    plugin_class = FixtureSignalPluginRegistry.get_plugin("FIXTURE_WARMUP")
    params = plugin_class.validate_params(
        {
            "minimum_points": 3,
            "stabilization_points": 7,
        }
    )
    requirement = plugin_class.warmup_requirement(params, context)
    assert requirement.minimum_points == 3
    assert requirement.stabilization_points == 7
    assert requirement.total_points == 10


def test_failing_fixture_surfaces_compute_error(context):
    plugin_class = FixtureSignalPluginRegistry.get_plugin("FIXTURE_FAILING")
    params = plugin_class.validate_params({})
    with pytest.raises(RuntimeError, match="fixture compute failure"):
        plugin_class().compute(
            make_signal_price_points(),
            [],
            params,
            context,
        )


def test_event_fixture_declares_and_consumes_required_events(context):
    plugin_class = FixtureSignalPluginRegistry.get_plugin("FIXTURE_EVENTS")
    requirements = plugin_class.input_requirements
    params = plugin_class.validate_params({})
    computation = plugin_class().compute(
        make_signal_price_points(),
        make_signal_event_points(),
        params,
        context,
    )

    assert requirements.requires_events is True
    assert requirements.event_types == ["DIVIDEND"]
    assert [point.value for point in computation.series[0].points] == [
        0.0,
        2.0,
        2.0,
        2.0,
        3.5,
        3.5,
    ]


def test_fixture_output_keys_and_kinds_match_catalog(context):
    price_points = make_signal_price_points()
    event_points = make_signal_event_points()
    for code in EXPECTED_CODES - {"FIXTURE_FAILING"}:
        plugin_class = FixtureSignalPluginRegistry.get_plugin(code)
        params = plugin_class.validate_params({})
        computation = plugin_class().compute(
            price_points,
            event_points,
            params,
            context,
        )
        expected = [(spec.key, spec.kind) for spec in plugin_class.output_specs]
        actual = [(series.key, series.kind) for series in computation.series]
        assert actual == expected


def test_fixture_registry_uses_test_directory():
    directory = FixtureSignalPluginRegistry._get_plugin_directory()
    assert directory.parts[-4:] == (
        "backend",
        "test_scripts",
        "fixtures",
        "signal_plugins",
    )
    assert directory != SignalPluginRegistry._get_plugin_directory()
