"""Uniform regression matrix for all production signal plugins."""

from __future__ import annotations

import inspect
import json
import re
from datetime import timedelta

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalAvailabilityReason,
    SignalCadence,
    SignalDataPolicy,
    SignalDomain,
    SignalErrorCode,
    SignalExecutionContext,
    SignalPriceField,
    SignalRequest,
    SignalSeriesKind,
    SignalSourceCapability,
    SignalStatus,
    SignalVolumeKind,
    SignalWarningCode,
)
from backend.app.services.provider_registry import SignalPluginRegistry
from backend.app.services.signal_plugins.base import SignalPlugin
from backend.app.services.signal_service import SignalService
from backend.test_scripts.fixtures.signals.plugin_test_utils import (
    VISIBLE_POINTS,
    execution_context,
    frame_to_points,
    load_signal_frames,
)

LEGACY_CODES = {
    "EMA",
    "SMA",
    "RSI",
    "MACD",
    "BOLLINGER",
    "ROC",
    "STOCH_RSI",
    "KAMA",
    "PPO",
    "ATR",
    "ADX",
    "NATR",
    "AROON",
    "DONCHIAN",
    "CCI",
    "OBV",
    "MFI",
}
RISK_CODES = {
    "RISK_DRAWDOWN",
    "RISK_ROLLING_BETA",
    "RISK_ROLLING_RETURN",
    "RISK_ROLLING_SHARPE",
    "RISK_ROLLING_VOLATILITY",
}
ALL_CODES = LEGACY_CODES | RISK_CODES
CLOSE_ONLY_CODES = {
    "EMA",
    "SMA",
    "RSI",
    "MACD",
    "BOLLINGER",
    "ROC",
    "STOCH_RSI",
    "KAMA",
    "PPO",
}
PARTIAL_CONTIGUOUS_CODES = {
    "ADX",
    "AROON",
    "ATR",
    "CCI",
    "DONCHIAN",
    "MFI",
    "NATR",
    "OBV",
}
SPECIAL_AGGREGATION_PROFILES = {
    "ATR": SignalAggregationProfile.MAX_WITH_RANGE,
    "BOLLINGER": SignalAggregationProfile.BAND_ENVELOPE,
    "DONCHIAN": SignalAggregationProfile.BAND_ENVELOPE,
    "NATR": SignalAggregationProfile.MAX_WITH_RANGE,
    "RISK_DRAWDOWN": SignalAggregationProfile.MIN_WITH_RANGE,
}
EXPECTED_SEMANTIC_IDS = {
    "ADX": (
        "average_directional_index",
        [
            "average_directional_index.strength",
            "average_directional_index.positive_directional_index",
            "average_directional_index.negative_directional_index",
        ],
    ),
    "AROON": (
        "aroon",
        ["aroon.up", "aroon.down", "aroon.oscillator"],
    ),
    "ATR": ("average_true_range", ["average_true_range.value"]),
    "BOLLINGER": ("bollinger_bands", ["bollinger_bands.envelope"]),
    "CCI": (
        "commodity_channel_index",
        ["commodity_channel_index.value"],
    ),
    "DONCHIAN": ("donchian_channels", ["donchian_channels.envelope"]),
    "EMA": (
        "exponential_moving_average",
        ["exponential_moving_average.value"],
    ),
    "KAMA": (
        "kaufman_adaptive_moving_average",
        ["kaufman_adaptive_moving_average.value"],
    ),
    "MACD": (
        "moving_average_convergence_divergence",
        [
            "moving_average_convergence_divergence.line",
            "moving_average_convergence_divergence.signal",
            "moving_average_convergence_divergence.histogram",
        ],
    ),
    "MFI": ("money_flow_index", ["money_flow_index.value"]),
    "NATR": (
        "normalized_average_true_range",
        ["normalized_average_true_range.value"],
    ),
    "OBV": ("on_balance_volume", ["on_balance_volume.value"]),
    "PPO": (
        "percentage_price_oscillator",
        [
            "percentage_price_oscillator.line",
            "percentage_price_oscillator.signal",
            "percentage_price_oscillator.histogram",
        ],
    ),
    "ROC": ("rate_of_change", ["rate_of_change.value"]),
    "RSI": (
        "relative_strength_index",
        ["relative_strength_index.value"],
    ),
    "RISK_DRAWDOWN": (
        "underwater_drawdown",
        ["underwater_drawdown.value"],
    ),
    "RISK_ROLLING_BETA": (
        "rolling_beta",
        ["rolling_beta.value"],
    ),
    "RISK_ROLLING_RETURN": (
        "rolling_compounded_return",
        ["rolling_compounded_return.value"],
    ),
    "RISK_ROLLING_SHARPE": (
        "rolling_sharpe_ratio",
        ["rolling_sharpe_ratio.value"],
    ),
    "RISK_ROLLING_VOLATILITY": (
        "rolling_realized_volatility",
        ["rolling_realized_volatility.value"],
    ),
    "SMA": ("simple_moving_average", ["simple_moving_average.value"]),
    "STOCH_RSI": (
        "stochastic_relative_strength_index",
        [
            "stochastic_relative_strength_index.k",
            "stochastic_relative_strength_index.d",
        ],
    ),
}
DOCS_ROOT = PROJECT_ROOT / "mkdocs_src" / "docs"
# DocsLink opens `/mkdocs/<lang>/<docs_path>` as-is: relative (no leading
# slash), directory-style (trailing slash), as every declared value is.
# Lowercase too: the page-exists check below is case-insensitive on macOS,
# the served site is not.
DOCS_PATH_SHAPE = re.compile(r"(?:[a-z0-9][a-z0-9_-]*/)+")
# Pinned so an edit cannot silently repoint a risk signal's in-app guide.
EXPECTED_RISK_DOCS_PATHS = {
    "RISK_DRAWDOWN": "financial-theory/technical-analysis/risk-metrics/current-drawdown/",
    "RISK_ROLLING_RETURN": "financial-theory/fundamentals/returns/",
    "RISK_ROLLING_VOLATILITY": "financial-theory/technical-analysis/risk-metrics/volatility/",
    "RISK_ROLLING_SHARPE": "financial-theory/technical-analysis/risk-metrics/sharpe-ratio/",
    "RISK_ROLLING_BETA": "financial-theory/technical-analysis/risk-metrics/beta-active-return/",
    "ASSET_CALENDAR_ROLLING_RETURN": "financial-theory/fundamentals/returns/",
}
CALENDAR_CODE = "ASSET_CALENDAR_ROLLING_RETURN"
# Developer's decision of 30/09/2026: technical indicators compute on quote days
# («SMA 200 = 200 sedute»). The calendar return keeps calendar windows by design
# and the prepared risk signals already run on the prepared quote calendar, so
# those six opt out.
QUOTE_DAY_CODES = LEGACY_CODES
CALENDAR_INPUT_CODES = RISK_CODES | {CALENDAR_CODE}
# The seventeen indicators change their numbers (major); the prepared risk
# signals change their input (holidays; minor); the calendar return keeps its
# numbers but now reports a stored weekend or holiday repeat as carried (minor).
EXPECTED_IMPLEMENTATION_VERSIONS = {
    **dict.fromkeys(LEGACY_CODES, "2.0.0"),
    "RISK_DRAWDOWN": "1.2.0",
    "RISK_ROLLING_BETA": "1.1.0",
    "RISK_ROLLING_RETURN": "1.1.0",
    "RISK_ROLLING_SHARPE": "1.1.0",
    "RISK_ROLLING_VOLATILITY": "1.1.0",
    CALENDAR_CODE: "1.4.0",
}
# The unit and tooltip of every param, per plugin: (x-suffix, x-tooltip-key). An
# indicator period counts sessions and says so; the calendar return and the rolling
# risk windows keep days. The shared period tooltip moves to `sessionPeriod`
# (`period` stays for the frontend Sine benchmark, where days are real); the
# EMA, MACD/PPO and StochRSI period tooltips keep their own keys.
SESSION_PERIOD = ("sessions", "chartSettings.tooltips.sessionPeriod")
MACD_PPO_PERIODS = {
    "fastPeriod": ("sessions", "chartSettings.tooltips.fastPeriod"),
    "slowPeriod": ("sessions", "chartSettings.tooltips.slowPeriod"),
    "signalPeriod": ("sessions", "chartSettings.tooltips.signalPeriod"),
}
EXPECTED_PARAM_UNITS = {
    "ADX": {"period": SESSION_PERIOD},
    "AROON": {"period": SESSION_PERIOD},
    "ATR": {"period": SESSION_PERIOD},
    "BOLLINGER": {"period": SESSION_PERIOD, "multiplier": ("σ", "chartSettings.tooltips.multiplier")},
    "CCI": {"period": SESSION_PERIOD},
    "DONCHIAN": {"period": SESSION_PERIOD},
    "EMA": {"period": ("sessions", "chartSettings.tooltips.emaPeriod"), "offset": ("%", "chartSettings.tooltips.offset")},
    "KAMA": {"period": SESSION_PERIOD},
    "MACD": MACD_PPO_PERIODS,
    "MFI": {"period": SESSION_PERIOD, "overbought": (None, "chartSettings.tooltips.overbought"), "oversold": (None, "chartSettings.tooltips.oversold")},
    "NATR": {"period": SESSION_PERIOD},
    "OBV": {},
    "PPO": MACD_PPO_PERIODS,
    "ROC": {"period": SESSION_PERIOD},
    "RSI": {"period": SESSION_PERIOD, "overbought": (None, "chartSettings.tooltips.overbought"), "oversold": (None, "chartSettings.tooltips.oversold")},
    "SMA": {"period": SESSION_PERIOD},
    "STOCH_RSI": {
        "period": ("sessions", "signals.tooltips.stochRsiPeriod"),
        "dPeriod": ("sessions", "signals.tooltips.dPeriod"),
        "overbought": (None, "chartSettings.tooltips.overbought"),
        "oversold": (None, "chartSettings.tooltips.oversold"),
    },
    "RISK_DRAWDOWN": {"full_history": (None, "signals.tooltips.riskFullHistory")},
    "RISK_ROLLING_BETA": {"window": ("days", "signals.tooltips.riskWindow"), "comparison_asset_id": (None, "signals.tooltips.comparisonAsset")},
    "RISK_ROLLING_RETURN": {"window": ("days", "signals.tooltips.riskWindow")},
    "RISK_ROLLING_SHARPE": {"window": ("days", "signals.tooltips.riskWindow"), "risk_free_annual_rate": (None, "signals.tooltips.riskFreeAnnualRate")},
    "RISK_ROLLING_VOLATILITY": {"window": ("days", "signals.tooltips.riskWindow")},
    CALENDAR_CODE: {"window_days": ("days", "signals.tooltips.riskWindow")},
}
I18N_CATALOGS = {language: PROJECT_ROOT / "frontend" / "src" / "lib" / "i18n" / f"{language}.json" for language in ("en", "it", "fr", "es")}
# A word unit is looked up as `signals.units.<suffix>`; a symbol (%, σ) is rendered as
# itself by the parameter control when no such key exists.
WORD_UNIT = re.compile(r"[a-z]+")


@pytest.fixture(scope="module")
def frames():
    return load_signal_frames(
        (
            "flat",
            "trend",
            "volatile",
            "scale_low",
        )
    )


@pytest.fixture(scope="module")
def neutral_points(frames):
    return {name: frame_to_points(frame) for name, frame in frames.items()}


def default_requests() -> list[SignalRequest]:
    return [
        SignalRequest(
            instance_id=code.lower(),
            signal_code=code,
            params={},
        )
        for code in sorted(LEGACY_CODES)
    ]


def test_registry_has_twenty_two_complete_definitions():
    definitions = SignalPluginRegistry.list_definitions()
    assert {definition.signal_code for definition in definitions} == ALL_CODES
    assert len(definitions) == 22

    for definition in definitions:
        assert definition.implementation_version
        assert definition.params_schema["additionalProperties"] is False
        assert definition.output_specs
        assert len({spec.key for spec in definition.output_specs}) == len(definition.output_specs)
        expected_signal_semantic, expected_output_semantics = EXPECTED_SEMANTIC_IDS[definition.signal_code]
        assert definition.semantic_id == expected_signal_semantic
        assert [spec.semantic_id for spec in definition.output_specs] == expected_output_semantics
        semantic_descriptions = [
            definition.semantic_description,
            *[spec.semantic_description for spec in definition.output_specs],
        ]
        assert all(description.strip() for description in semantic_descriptions)
        assert all(re.search(r"(?<![A-Za-z])(?:buy|sell)(?![A-Za-z])", description, re.IGNORECASE) is None for description in semantic_descriptions)
        # Every real, discovered plugin must yield a validated AI description
        # through the catalog by default derivation alone — the registry must
        # never break mid-migration for plugins that don't override
        # describe_for_ai()/describe_events_for_ai().
        assert definition.ai_description is not None
        assert definition.ai_description.signal_code == definition.signal_code
        assert len(definition.ai_description.outputs) == len(definition.output_specs)
        assert isinstance(definition.ai_events, list)
        plugin_class = SignalPluginRegistry.get_plugin(definition.signal_code)
        required_params = set(definition.params_schema.get("required", []))
        if required_params:
            assert required_params.isdisjoint(definition.default_params)
            for key, value in definition.default_params.items():
                assert definition.params_schema["properties"][key]["default"] == value
        else:
            normalized_defaults = plugin_class.validate_params(definition.default_params).model_dump(mode="json", by_alias=True)
            assert normalized_defaults == definition.default_params

    assert len({definition.semantic_id for definition in definitions}) == len(definitions)
    output_semantic_ids = [spec.semantic_id for definition in definitions for spec in definition.output_specs]
    assert len(set(output_semantic_ids)) == len(output_semantic_ids)

    serialized = json.dumps([definition.model_dump(mode="json") for definition in definitions])
    for forbidden in (
        "pandas_ta",
        "talib",
        "lineWidth",
        "lineType",
        '"color"',
    ):
        assert forbidden not in serialized

    # docs_path is what makes a signal's in-app guide button appear, so every
    # *registered* plugin must declare one. Walked through the registry, not
    # list_definitions(), which omits catalog-hidden plugins such as
    # ASSET_CALENDAR_ROLLING_RETURN. Each rule collects every offending code.
    docs_paths = {code: SignalPluginRegistry.get_plugin(code).catalog_definition().docs_path for code in sorted(SignalPluginRegistry.list_plugin_codes())}
    without_docs_path = [code for code, docs_path in docs_paths.items() if not docs_path]
    assert not without_docs_path, f"signals without docs_path: {', '.join(without_docs_path)}"
    misshaped = {code: docs_path for code, docs_path in docs_paths.items() if not DOCS_PATH_SHAPE.fullmatch(docs_path)}
    assert not misshaped, f"docs_path must be relative, lowercase and end with '/': {misshaped}"
    without_page = {code: docs_path for code, docs_path in docs_paths.items() if not (DOCS_ROOT / f"{docs_path.rstrip('/')}.en.md").is_file()}
    assert not without_page, f"docs_path with no .en.md page under {DOCS_ROOT}: {without_page}"
    repointed = [f"{code}: declared {docs_paths.get(code)!r}, pinned {pinned!r}" for code, pinned in EXPECTED_RISK_DOCS_PATHS.items() if docs_paths.get(code) != pinned]
    assert not repointed, f"risk signals off their pinned guide: {'; '.join(repointed)}"


def test_all_plugin_outputs_declare_exact_aggregation_profile_matrix():
    definitions = {definition.signal_code: definition for definition in SignalPluginRegistry.list_definitions()}

    for signal_code in sorted(ALL_CODES):
        expected = SPECIAL_AGGREGATION_PROFILES.get(
            signal_code,
            SignalAggregationProfile.LAST_WITH_RANGE,
        )
        assert {output.aggregation_profile for output in definitions[signal_code].output_specs} == {expected}

    drawdown = definitions["RISK_DRAWDOWN"].output_specs
    assert len(drawdown) == 1
    assert drawdown[0].kind == SignalSeriesKind.AREA
    assert drawdown[0].style.fill_opacity == pytest.approx(0.2)


def test_backend_path_is_sixteen_delegated_plus_native_donchian():
    for code in LEGACY_CODES:
        plugin_class = SignalPluginRegistry.get_plugin(code)
        source = inspect.getsource(plugin_class.compute)
        if code == "DONCHIAN":
            assert "talib=True" not in source
        else:
            assert "talib=True" in source


def test_asset_only_field_rich_plugins_allow_partial_contiguous_input():
    for code in LEGACY_CODES:
        requirements = SignalPluginRegistry.get_plugin(code).input_requirements
        if code in PARTIAL_CONTIGUOUS_CODES:
            assert requirements.data_policy == SignalDataPolicy.ALLOW_PARTIAL_CONTIGUOUS
            assert requirements.minimum_coverage == 0.5
        else:
            assert requirements.data_policy == SignalDataPolicy.STRICT_CONTIGUOUS
            assert requirements.minimum_coverage == 1.0


def test_every_registered_plugin_declares_whether_it_computes_on_quote_days():
    """T9 — True by default; the calendar return and the five prepared risk signals opt out."""
    assert getattr(SignalPlugin, "computes_on_quote_days", None) is True
    registered = set(SignalPluginRegistry.list_plugin_codes())
    assert registered == ALL_CODES | {CALENDAR_CODE}
    declared = {code: getattr(SignalPluginRegistry.get_plugin(code), "computes_on_quote_days", "<not declared>") for code in sorted(registered)}

    assert {code for code, value in declared.items() if value is True} == QUOTE_DAY_CODES, declared
    assert {code for code, value in declared.items() if value is False} == CALENDAR_INPUT_CODES, declared
    # The opt-outs are exactly the prepared-series plugins plus the sparse calendar input.
    opted_out = {code for code, value in declared.items() if value is False}
    prepared = {code for code in registered if SignalPluginRegistry.get_plugin(code).input_requirements.uses_prepared_asset_series}
    assert opted_out == prepared | {CALENDAR_CODE}


def test_implementation_versions_follow_the_quote_day_change():
    """T9 — pinned per plugin, so a bump on one side only cannot stay green."""
    versions = {code: SignalPluginRegistry.get_plugin(code).implementation_version for code in SignalPluginRegistry.list_plugin_codes()}

    assert versions == EXPECTED_IMPLEMENTATION_VERSIONS


def _declared_param_units(signal_code: str) -> dict[str, tuple[str | None, str | None]]:
    """(x-suffix, x-tooltip-key) of every param, read from the schema the catalog serves."""
    properties = SignalPluginRegistry.get_plugin(signal_code).catalog_definition().params_schema.get("properties", {})
    return {key: (schema.get("x-suffix"), schema.get("x-tooltip-key")) for key, schema in properties.items()}


def _translation(catalog: dict, dotted_key: str) -> object:
    node: object = catalog
    for part in dotted_key.split("."):
        node = node.get(part) if isinstance(node, dict) else None
    return node


def test_every_registered_plugin_has_its_param_units_pinned():
    assert set(EXPECTED_PARAM_UNITS) == set(SignalPluginRegistry.list_plugin_codes())


@pytest.mark.parametrize("signal_code", sorted(EXPECTED_PARAM_UNITS))
def test_period_params_declare_sessions_or_days_and_their_tooltip(signal_code):
    """An indicator period is a number of sessions; the calendar return and the rolling risk windows are days."""
    assert _declared_param_units(signal_code) == EXPECTED_PARAM_UNITS[signal_code]


def test_every_param_tooltip_and_word_unit_is_translated_in_the_four_catalogs():
    """The pinned keys and the declared ones alike, so a key renamed in the plugins is checked too."""
    units = [unit for code in EXPECTED_PARAM_UNITS for unit in (*EXPECTED_PARAM_UNITS[code].values(), *_declared_param_units(code).values())]
    keys = {tooltip for _suffix, tooltip in units if tooltip} | {f"signals.units.{suffix}" for suffix, _tooltip in units if suffix and WORD_UNIT.fullmatch(suffix)}
    # Premise: both word units and the moved tooltip are among the keys checked.
    assert {"signals.units.days", "signals.units.sessions", "chartSettings.tooltips.sessionPeriod"} <= keys
    catalogs = {language: json.loads(path.read_text(encoding="utf-8")) for language, path in I18N_CATALOGS.items()}

    untranslated = {language: sorted(key for key in keys if not (isinstance(text := _translation(catalog, key), str) and text.strip())) for language, catalog in catalogs.items()}

    assert untranslated == dict.fromkeys(I18N_CATALOGS, [])


def test_full_plan_aggregates_all_fields_and_max_warmup(neutral_points):
    points = neutral_points["volatile"]
    plan = SignalService().prepare_plan(
        default_requests(),
        execution_context(points),
    )

    assert len(plan.computations) == 17
    assert plan.required_price_fields == frozenset(
        {
            SignalPriceField.HIGH,
            SignalPriceField.LOW,
            SignalPriceField.CLOSE,
            SignalPriceField.VOLUME,
        }
    )
    assert plan.requires_events is False
    assert plan.max_history_points_before_visible == 18 * 14


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dataset_name",
    ["flat", "trend", "volatile", "scale_low"],
)
async def test_all_seventeen_plugins_batch_ok_on_asset(
    dataset_name,
    neutral_points,
):
    points = neutral_points[dataset_name]
    results = await SignalService().compute(
        default_requests(),
        points,
        execution_context(points),
    )

    assert len(results) == 17
    assert all(result.status == SignalStatus.OK for result in results)
    for result in results:
        plugin_class = SignalPluginRegistry.get_plugin(result.signal_code)
        assert [series.key for series in result.series] == [spec.key for spec in plugin_class.output_specs]
        assert [series.kind for series in result.series] == [spec.kind for spec in plugin_class.output_specs]
        assert [series.style for series in result.series] == [spec.style for spec in plugin_class.output_specs]
        assert [series.description_key for series in result.series] == [spec.description_key for spec in plugin_class.output_specs]
        assert [series.semantic_id for series in result.series] == [spec.semantic_id for spec in plugin_class.output_specs]
        assert [series.semantic_description for series in result.series] == [spec.semantic_description for spec in plugin_class.output_specs]
        assert all(len(series.points) == VISIBLE_POINTS for series in result.series)
        assert result.model_dump_json()


@pytest.mark.asyncio
async def test_fx_batch_exposes_only_nine_close_only_plugins(
    neutral_points,
):
    points = neutral_points["volatile"]
    results = await SignalService().compute(
        default_requests(),
        points,
        execution_context(
            points,
            domain=SignalDomain.FX,
        ),
    )
    by_code = {result.signal_code: result for result in results}

    assert {code for code, result in by_code.items() if result.status == SignalStatus.OK} == CLOSE_ONLY_CODES
    for code in LEGACY_CODES - CLOSE_ONLY_CODES:
        assert by_code[code].status == SignalStatus.UNAVAILABLE
        assert by_code[code].availability.reason_code == SignalAvailabilityReason.INCOMPATIBLE_DOMAIN


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(LEGACY_CODES))
async def test_exact_minimum_history_is_partial_not_failed(
    signal_code,
    neutral_points,
):
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    params = plugin_class.validate_params({})
    all_points = neutral_points["volatile"]
    requirement = plugin_class.warmup_requirement(
        params,
        execution_context(all_points),
    )
    points = all_points[: requirement.minimum_points]
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=points[0].date,
            end=points[-1].date,
        ),
        source_reference=f"asset:minimum:{signal_code}",
        source_capability=SignalSourceCapability(
            supports_meaningful_volume=True,
            volume_kind=SignalVolumeKind.TRADED_SHARES,
        ),
    )
    result = (
        await SignalService().compute(
            [
                SignalRequest(
                    instance_id=signal_code,
                    signal_code=signal_code,
                    params={},
                )
            ],
            points,
            context,
        )
    )[0]

    assert result.status == SignalStatus.PARTIAL
    assert result.error is None
    assert any(warning.code == SignalWarningCode.INCOMPLETE_WARMUP for warning in result.warnings)


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(LEGACY_CODES))
async def test_every_required_field_is_dynamically_enforced(
    signal_code,
    neutral_points,
):
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    base_points = neutral_points["volatile"]

    for field in plugin_class.input_requirements.price_fields:
        points = [point.model_copy(update={field.value: None}) for point in base_points]
        result = (
            await SignalService().compute(
                [
                    SignalRequest(
                        instance_id=f"{signal_code}-{field.value}",
                        signal_code=signal_code,
                        params={},
                    )
                ],
                points,
                execution_context(points),
            )
        )[0]

        assert result.status == SignalStatus.UNAVAILABLE
        assert result.availability.reason_code == SignalAvailabilityReason.MISSING_INPUT_FIELDS
        assert field in result.availability.missing_price_fields


@pytest.mark.asyncio
@pytest.mark.parametrize("signal_code", sorted(LEGACY_CODES))
async def test_partial_required_field_never_compacts_dates(
    signal_code,
    neutral_points,
):
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    field = plugin_class.input_requirements.price_fields[0]
    points = neutral_points["volatile"][-1000:].copy()
    points[500] = points[500].model_copy(update={field.value: None})
    result = (
        await SignalService().compute(
            [
                SignalRequest(
                    instance_id=signal_code,
                    signal_code=signal_code,
                    params={},
                )
            ],
            points,
            execution_context(points),
        )
    )[0]

    if signal_code in PARTIAL_CONTIGUOUS_CODES:
        assert result.status == SignalStatus.PARTIAL
        assert result.availability.reason_code == SignalAvailabilityReason.PARTIAL_INPUT_COVERAGE
        gap_date = points[500].date
        assert all(point.date > gap_date for series in result.series for point in series.points)
    else:
        assert result.status == SignalStatus.UNAVAILABLE
        assert result.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_INPUT_COVERAGE
    assert result.availability.input_coverage.internal_gap_count == 1


@pytest.mark.asyncio
async def test_all_plugins_preserve_same_internal_date_gap_without_compaction(
    neutral_points,
):
    points = neutral_points["volatile"][-1000:]
    points = [point for index, point in enumerate(points) if index != 500]
    results = await SignalService().compute(
        default_requests(),
        points,
        SignalExecutionContext(
            domain=SignalDomain.ASSET,
            requested_range=DateRangeModel(
                start=points[0].date,
                end=points[-1].date,
            ),
            source_reference="asset:matrix-gap",
            source_capability=SignalSourceCapability(
                supports_meaningful_volume=True,
                volume_kind=SignalVolumeKind.TRADED_SHARES,
            ),
        ),
    )

    by_code = {result.signal_code: result for result in results}
    assert all(by_code[code].status == SignalStatus.PARTIAL for code in PARTIAL_CONTIGUOUS_CODES)
    assert all(by_code[code].status == SignalStatus.UNAVAILABLE for code in LEGACY_CODES - PARTIAL_CONTIGUOUS_CODES)
    assert all(result.availability.input_coverage.internal_gap_count == 1 for result in results)


@pytest.mark.asyncio
async def test_irregular_range_outside_loaded_data_is_unavailable(
    neutral_points,
):
    points = neutral_points["volatile"][-1000:]
    requested_start = points[-1].date + timedelta(days=10)
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(
            start=requested_start,
            end=requested_start + timedelta(days=10),
        ),
        cadence=SignalCadence.IRREGULAR,
        source_reference="asset:irregular-outside",
    )
    results = await SignalService().compute(
        default_requests(),
        points,
        context,
    )

    assert all(result.status == SignalStatus.UNAVAILABLE for result in results)
    assert all(result.error is None for result in results)


@pytest.mark.asyncio
async def test_invalid_instance_does_not_erase_valid_matrix(
    neutral_points,
):
    points = neutral_points["volatile"]
    requests = [
        SignalRequest(
            instance_id="invalid-ema",
            signal_code="EMA",
            params={"period": 1},
        ),
        *default_requests(),
    ]
    results = await SignalService().compute(
        requests,
        points,
        execution_context(points),
    )

    assert results[0].status == SignalStatus.FAILED
    assert results[0].error.code == SignalErrorCode.INVALID_PARAMS
    assert all(result.status == SignalStatus.OK for result in results[1:])


def test_all_warmup_contracts_are_internally_consistent(
    neutral_points,
):
    points = neutral_points["volatile"]
    context = execution_context(points)
    for code in LEGACY_CODES:
        plugin_class = SignalPluginRegistry.get_plugin(code)
        requirement = plugin_class.warmup_requirement(
            plugin_class.validate_params({}),
            context,
        )
        assert requirement.total_points == requirement.minimum_points + requirement.stabilization_points
        assert requirement.normalized_tolerance == 1e-6
