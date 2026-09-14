"""Strict wire-contract tests for the PAC and portfolio-rebalancer P1 services.

The witnesses are owned, deterministic inputs.  Financial behaviour is asserted in
the service suite; this module protects the two public codecs, their generated
schemas, and the bounded Tool export.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from backend.app.schemas.pac_allocator import (
    P1_MAX_ROWS,
    P1_RESULT_BYTES,
    PAC_ANALYZE_INPUT_ADAPTER,
    PAC_ANALYZE_OUTPUT_ADAPTER,
    REBALANCE_ANALYZE_INPUT_ADAPTER,
    REBALANCE_ANALYZE_OUTPUT_ADAPTER,
    CanonicalScalar,
    CombinedAmount,
    NativeAmount,
    PacAnalyzeInput,
    PacAnalyzeOutput,
    RatioApproximation,
    RatioDenominator,
    RatioNumerator,
    RebalanceAnalyzeInput,
    RebalanceAnalyzeOutput,
    ReportingAmount,
    SquaredDenominator,
    SquaredNumerator,
)
from backend.app.services.pac_allocator import (
    analyze_pac_budget,
    analyze_rebalancing,
)
from backend.app.services.tool_plugins.pac_allocator import PacAllocatorTool
from backend.app.services.tools.registry import (
    ToolRegistrySnapshot,
    build_tool_definition,
)
from backend.app.services.tools.schema import (
    declared_operations,
    generate_tool_schema,
    schema_fingerprint,
    walk_schema,
)
from backend.app.services.tools.schema_export import (
    TOOL_MANIFEST_KEY,
    build_tool_contracts_document,
)

Path = tuple[str | int, ...]

EXPECTED_TOOL_CODES = frozenset(
    {
        "pac_allocator",
        "portfolio_rebalancer",
    }
)
EXPECTED_COMPONENTS = {
    "pac_allocator": "pac-allocator",
    "portfolio_rebalancer": "portfolio-rebalancer",
}


def _encode(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _at(value: Any, path: Path) -> Any:
    for token in path:
        value = value[token]
    return value


def _set(value: Any, path: Path, replacement: Any) -> None:
    _at(value, path[:-1])[path[-1]] = replacement


def _objects(value: Any, path: Path = ()):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from _objects(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _objects(child, (*path, index))


def _roundtrip(adapter: TypeAdapter, payload: Any) -> Any:
    model = adapter.validate_json(_encode(payload), strict=True)
    emitted = adapter.dump_json(model)
    assert adapter.validate_json(emitted, strict=True) == model
    assert json.loads(emitted) == adapter.dump_python(model, mode="json")
    return model


def _reject(adapter: TypeAdapter, payload: Any) -> None:
    with pytest.raises(ValidationError):
        adapter.validate_json(_encode(payload), strict=True)


def _asset(
    instrument_key: str = "asset-alpha",
    *,
    name: str = "Alpha",
    buy_grid: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "instrument_key": instrument_key,
        "name": name,
        "buy_grid": buy_grid,
    }


def _target(
    instrument_key: str = "asset-alpha",
    target_percent: str | None = "100",
) -> dict[str, object]:
    return {
        "instrument_key": instrument_key,
        "target_percent": target_percent,
    }


def _holding(
    row_key: str = "broker-a::asset-alpha",
    instrument_key: str = "asset-alpha",
    *,
    name: str = "Alpha",
    quantity: str | None = "2",
    price: str | None = "25",
    currency: str | None = "EUR",
    quote_base_quantity: int | None = 1,
    buy_grid: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "row_key": row_key,
        "instrument_key": instrument_key,
        "name": name,
        "quantity": quantity,
        "quote": {
            "raw_price": price,
            "currency": currency,
            "quote_base_quantity": quote_base_quantity,
            "reference_date": "2026-09-14",
        },
        "buy_grid": buy_grid,
    }


def _pac_payload() -> dict[str, object]:
    return {
        "operation": "analyze",
        "report_currency": "EUR",
        "as_of_date": "2026-09-14",
        "assets": [_asset()],
        "targets": [_target()],
        "cash_balances": [{"currency": "EUR", "amount": "10.25"}],
        "contributions": [
            {
                "currency": "EUR",
                "amount": "5",
                "monetary_step": "0.01",
            }
        ],
        "valuation_rates": [],
    }


def _rebalance_payload() -> dict[str, object]:
    return {
        "operation": "analyze",
        "report_currency": "EUR",
        "as_of_date": "2026-09-14",
        "holdings": [_holding()],
        "targets": [_target()],
        "cash_balances": [],
        "contributions": [],
        "valuation_rates": [],
    }


CONTRACTS = (
    pytest.param(
        "pac",
        PAC_ANALYZE_INPUT_ADAPTER,
        PAC_ANALYZE_OUTPUT_ADAPTER,
        PacAnalyzeInput,
        PacAnalyzeOutput,
        _pac_payload,
        analyze_pac_budget,
        id="pac",
    ),
    pytest.param(
        "rebalancer",
        REBALANCE_ANALYZE_INPUT_ADAPTER,
        REBALANCE_ANALYZE_OUTPUT_ADAPTER,
        RebalanceAnalyzeInput,
        RebalanceAnalyzeOutput,
        _rebalance_payload,
        analyze_rebalancing,
        id="rebalancer",
    ),
)


@pytest.mark.parametrize(
    (
        "service",
        "input_adapter",
        "output_adapter",
        "input_type",
        "output_type",
        "payload_factory",
        "analyze",
    ),
    CONTRACTS,
)
def test_public_adapters_are_strict_real_codecs(
    service,
    input_adapter,
    output_adapter,
    input_type,
    output_type,
    payload_factory,
    analyze,
):
    assert isinstance(input_adapter, TypeAdapter)
    assert isinstance(output_adapter, TypeAdapter)
    request = _roundtrip(input_adapter, payload_factory())
    assert isinstance(request, input_type)
    result = analyze(request)
    assert output_adapter.validate_python(result, strict=True) == result
    assert TypeAdapter(output_type).json_schema(mode="serialization") == (output_adapter.json_schema(mode="serialization"))


@pytest.mark.parametrize(
    "input_adapter",
    [PAC_ANALYZE_INPUT_ADAPTER, REBALANCE_ANALYZE_INPUT_ADAPTER],
    ids=["pac", "rebalancer"],
)
@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "analyze",
        True,
        1,
        {},
        {"operation": None},
        {"operation": "solve"},
        {"operation": "ANALYZE"},
        {"operation": True},
        {"operation": 1},
    ],
)
def test_root_and_required_operation_are_strict(input_adapter, payload):
    _reject(input_adapter, payload)


def test_service_roots_have_exact_distinct_fields_and_defaults():
    pac = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, {"operation": "analyze"})
    assert pac.model_dump(mode="json") == {
        "operation": "analyze",
        "report_currency": None,
        "as_of_date": None,
        "targets": [],
        "cash_balances": None,
        "contributions": None,
        "valuation_rates": [],
        "assets": [],
    }
    rebalancer = _roundtrip(
        REBALANCE_ANALYZE_INPUT_ADAPTER,
        {"operation": "analyze"},
    )
    assert rebalancer.model_dump(mode="json") == {
        "operation": "analyze",
        "report_currency": None,
        "as_of_date": None,
        "targets": [],
        "cash_balances": None,
        "contributions": None,
        "valuation_rates": [],
        "holdings": [],
    }
    assert set(PacAnalyzeInput.model_fields) - set(RebalanceAnalyzeInput.model_fields) == {"assets"}
    assert set(RebalanceAnalyzeInput.model_fields) - set(PacAnalyzeInput.model_fields) == {"holdings"}


@pytest.mark.parametrize(
    ("adapter", "payload_factory"),
    [
        pytest.param(PAC_ANALYZE_INPUT_ADAPTER, _pac_payload, id="pac"),
        pytest.param(
            REBALANCE_ANALYZE_INPUT_ADAPTER,
            _rebalance_payload,
            id="rebalancer",
        ),
    ],
)
def test_contribution_rows_are_independently_bounded_at_32(
    adapter,
    payload_factory,
):
    assert P1_MAX_ROWS == 32
    payload = payload_factory()
    repeated = [
        {
            "currency": "EUR",
            "amount": str(index + 1),
            "monetary_step": "1",
        }
        for index in range(P1_MAX_ROWS)
    ]
    payload["contributions"] = repeated

    request = _roundtrip(adapter, payload)

    assert request.model_dump(mode="json")["contributions"] == repeated

    overflow = deepcopy(payload)
    overflow["contributions"] = [
        *repeated,
        {
            "currency": "EUR",
            "amount": str(P1_MAX_ROWS + 1),
            "monetary_step": "1",
        },
    ]
    _reject(adapter, overflow)


@pytest.mark.parametrize(
    ("adapter", "payload_factory"),
    [
        pytest.param(PAC_ANALYZE_INPUT_ADAPTER, _pac_payload, id="pac"),
        pytest.param(
            REBALANCE_ANALYZE_INPUT_ADAPTER,
            _rebalance_payload,
            id="rebalancer",
        ),
    ],
)
def test_every_input_object_is_closed(adapter, payload_factory):
    payload = payload_factory()
    paths = [path for path, _obj in _objects(payload)]
    assert paths
    for path in paths:
        mutated = deepcopy(payload)
        _at(mutated, path)["unknown_contract_field"] = "rejected"
        _reject(adapter, mutated)


@pytest.mark.parametrize(
    ("adapter", "payload_factory", "path", "field"),
    [
        (
            PAC_ANALYZE_INPUT_ADAPTER,
            _pac_payload,
            (),
            "rows",
        ),
        (
            PAC_ANALYZE_INPUT_ADAPTER,
            _pac_payload,
            ("assets", 0),
            "row_key",
        ),
        (
            PAC_ANALYZE_INPUT_ADAPTER,
            _pac_payload,
            ("assets", 0),
            "quantity",
        ),
        (
            PAC_ANALYZE_INPUT_ADAPTER,
            _pac_payload,
            ("assets", 0),
            "quote",
        ),
        (
            PAC_ANALYZE_INPUT_ADAPTER,
            _pac_payload,
            ("assets", 0),
            "target_percent",
        ),
        (
            REBALANCE_ANALYZE_INPUT_ADAPTER,
            _rebalance_payload,
            (),
            "rows",
        ),
        (
            REBALANCE_ANALYZE_INPUT_ADAPTER,
            _rebalance_payload,
            ("holdings", 0),
            "initial_quantity",
        ),
        (
            REBALANCE_ANALYZE_INPUT_ADAPTER,
            _rebalance_payload,
            ("holdings", 0),
            "target_percent",
        ),
    ],
    ids=[
        "pac-old-rows",
        "pac-row-key",
        "pac-quantity",
        "pac-quote",
        "pac-target-on-asset",
        "rebalancer-old-rows",
        "rebalancer-old-quantity",
        "rebalancer-target-on-holding",
    ],
)
def test_old_compound_row_contract_is_rejected(
    adapter,
    payload_factory,
    path,
    field,
):
    payload = payload_factory()
    _at(payload, path)[field] = None
    _reject(adapter, payload)


@pytest.mark.parametrize(
    "field",
    [
        "orders",
        "quantities",
        "solver",
        "fees",
        "execution_fx",
        "broker_id",
        "user_id",
        "draft_revision",
    ],
)
@pytest.mark.parametrize(
    ("adapter", "payload_factory"),
    [
        pytest.param(PAC_ANALYZE_INPUT_ADAPTER, _pac_payload, id="pac"),
        pytest.param(
            REBALANCE_ANALYZE_INPUT_ADAPTER,
            _rebalance_payload,
            id="rebalancer",
        ),
    ],
)
def test_platform_and_solver_fields_are_not_financial_parameters(
    field,
    adapter,
    payload_factory,
):
    payload = payload_factory()
    payload[field] = None
    _reject(adapter, payload)


FINANCIAL_PATHS = {
    "pac": (
        ("targets", 0, "target_percent"),
        ("cash_balances", 0, "amount"),
        ("contributions", 0, "amount"),
        ("contributions", 0, "monetary_step"),
    ),
    "rebalancer": (
        ("holdings", 0, "quantity"),
        ("holdings", 0, "quote", "raw_price"),
        ("targets", 0, "target_percent"),
    ),
}


@pytest.mark.parametrize(
    ("adapter", "payload_factory", "paths"),
    [
        pytest.param(
            PAC_ANALYZE_INPUT_ADAPTER,
            _pac_payload,
            FINANCIAL_PATHS["pac"],
            id="pac",
        ),
        pytest.param(
            REBALANCE_ANALYZE_INPUT_ADAPTER,
            _rebalance_payload,
            FINANCIAL_PATHS["rebalancer"],
            id="rebalancer",
        ),
    ],
)
@pytest.mark.parametrize("bad", [True, False, 0, 1, -2, 1.25, [], {}])
def test_financial_inputs_never_coerce_json_numbers_or_booleans(
    adapter,
    payload_factory,
    paths,
    bad,
):
    for path in paths:
        payload = payload_factory()
        _set(payload, path, bad)
        _reject(adapter, payload)


@pytest.mark.parametrize("bad", [True, False, 1.0, "1", [], {}])
def test_quote_base_quantity_is_a_strict_json_integer(bad):
    payload = _rebalance_payload()
    _set(payload, ("holdings", 0, "quote", "quote_base_quantity"), bad)
    _reject(REBALANCE_ANALYZE_INPUT_ADAPTER, payload)


@pytest.mark.parametrize(
    "basis",
    [
        None,
        -1,
        0,
        1,
        3,
        100,
        999_999_999_999,
        1_000_000_000_000,
        10**18,
    ],
)
def test_quote_base_quantity_draft_allows_domain_classification(basis):
    payload = _rebalance_payload()
    _set(payload, ("holdings", 0, "quote", "quote_base_quantity"), basis)
    parsed = _roundtrip(REBALANCE_ANALYZE_INPUT_ADAPTER, payload)
    assert parsed.holdings[0].quote is not None
    assert parsed.holdings[0].quote.quote_base_quantity == basis


def test_normalized_quote_base_output_is_strict_positive_without_repeating_normalizer_cap():
    output_schema = REBALANCE_ANALYZE_OUTPUT_ADAPTER.json_schema(
        mode="serialization",
    )
    normalized_holding = output_schema["$defs"]["NormalizedHolding"]
    quote_schema = normalized_holding["properties"]["quote_base_quantity"]
    assert quote_schema["type"] == "integer"
    assert quote_schema["exclusiveMinimum"] == 0
    assert "maximum" not in quote_schema

    payload = _rebalance_payload()
    _set(payload, ("holdings", 0, "quantity"), "999999999999")
    _set(payload, ("holdings", 0, "quote", "raw_price"), "1")
    _set(
        payload,
        ("holdings", 0, "quote", "quote_base_quantity"),
        999_999_999_999,
    )
    request = _roundtrip(REBALANCE_ANALYZE_INPUT_ADAPTER, payload)
    result = analyze_rebalancing(request)
    wire = REBALANCE_ANALYZE_OUTPUT_ADAPTER.dump_python(result, mode="json")
    assert wire["availability"] == "ready"
    assert (
        _at(
            wire,
            ("normalized", "holdings", 0, "quote_base_quantity"),
        )
        == 999_999_999_999
    )
    _roundtrip(REBALANCE_ANALYZE_OUTPUT_ADAPTER, wire)

    above_input_domain = deepcopy(wire)
    _set(
        above_input_domain,
        ("normalized", "holdings", 0, "quote_base_quantity"),
        1_000_000_000_000,
    )
    parsed = _roundtrip(
        REBALANCE_ANALYZE_OUTPUT_ADAPTER,
        above_input_domain,
    )
    assert parsed.normalized.holdings[0].quote_base_quantity == 1_000_000_000_000

    for invalid in (0, -1, True, 1.0, "1"):
        malformed = deepcopy(wire)
        _set(
            malformed,
            ("normalized", "holdings", 0, "quote_base_quantity"),
            invalid,
        )
        _reject(REBALANCE_ANALYZE_OUTPUT_ADAPTER, malformed)


def test_pac_asset_needs_no_price_holding_or_grid_fields():
    payload = _pac_payload()
    payload["assets"] = [
        {
            "instrument_key": "asset-alpha",
            "name": "Alpha",
        }
    ]
    parsed = _roundtrip(PAC_ANALYZE_INPUT_ADAPTER, payload)
    assert parsed.assets[0].model_dump(mode="json") == {
        "instrument_key": "asset-alpha",
        "name": "Alpha",
        "buy_grid": None,
    }


@pytest.mark.parametrize(
    ("adapter", "payload_factory", "analyze", "output_adapter", "mutate"),
    [
        pytest.param(
            PAC_ANALYZE_INPUT_ADAPTER,
            _pac_payload,
            analyze_pac_budget,
            PAC_ANALYZE_OUTPUT_ADAPTER,
            lambda payload: payload["cash_balances"][0].update(amount="NaN"),
            id="pac-invalid",
        ),
        pytest.param(
            REBALANCE_ANALYZE_INPUT_ADAPTER,
            _rebalance_payload,
            analyze_rebalancing,
            REBALANCE_ANALYZE_OUTPUT_ADAPTER,
            lambda payload: payload["holdings"][0]["quote"].update(raw_price="Infinity"),
            id="rebalancer-invalid",
        ),
    ],
)
def test_nonfinite_draft_strings_become_typed_domain_invalid_results(
    adapter,
    payload_factory,
    analyze,
    output_adapter,
    mutate,
):
    payload = payload_factory()
    mutate(payload)
    request = _roundtrip(adapter, payload)
    result = analyze(request)
    wire = output_adapter.dump_python(result, mode="json")
    assert wire["availability"] == "invalid"
    assert wire["normalized"] is None
    assert any(issue["kind"] == "invalid" and issue["code"] == "invalid_decimal_syntax" for issue in wire["issues"])
    assert "NaN" not in _encode(wire).decode()
    assert "Infinity" not in _encode(wire).decode()


@pytest.fixture(scope="module")
def output_witnesses() -> dict[str, dict[str, dict[str, object]]]:
    witnesses: dict[str, dict[str, dict[str, object]]] = {
        "pac": {},
        "rebalancer": {},
    }
    cases = (
        (
            "pac",
            PAC_ANALYZE_INPUT_ADAPTER,
            PAC_ANALYZE_OUTPUT_ADAPTER,
            _pac_payload,
            analyze_pac_budget,
            ("cash_balances", 0, "amount"),
        ),
        (
            "rebalancer",
            REBALANCE_ANALYZE_INPUT_ADAPTER,
            REBALANCE_ANALYZE_OUTPUT_ADAPTER,
            _rebalance_payload,
            analyze_rebalancing,
            ("holdings", 0, "quantity"),
        ),
    )
    for (
        service,
        input_adapter,
        output_adapter,
        payload_factory,
        analyze,
        state_path,
    ) in cases:
        for state, value in (
            ("ready", "1"),
            ("needs_input", None),
            ("invalid", "NaN"),
            ("unsupported", "-1"),
        ):
            payload = payload_factory()
            _set(payload, state_path, value)
            request = input_adapter.validate_python(payload, strict=True)
            result = analyze(request)
            wire = output_adapter.dump_python(result, mode="json")
            assert wire["availability"] == state
            assert (wire["normalized"] is not None) is (state == "ready")
            witnesses[service][state] = wire
    return witnesses


@pytest.mark.parametrize(
    ("service", "output_adapter", "root_fields"),
    [
        (
            "pac",
            PAC_ANALYZE_OUTPUT_ADAPTER,
            {
                "operation",
                "result_kind",
                "numeric_policy_id",
                "allocations",
                "cash_pools",
                "totals",
                "availability",
                "normalized",
                "issues",
            },
        ),
        (
            "rebalancer",
            REBALANCE_ANALYZE_OUTPUT_ADAPTER,
            {
                "operation",
                "result_kind",
                "numeric_policy_id",
                "holdings",
                "instruments",
                "cash_pools",
                "totals",
                "availability",
                "normalized",
                "issues",
            },
        ),
    ],
)
@pytest.mark.parametrize("state", ["ready", "needs_input", "invalid", "unsupported"])
def test_output_states_are_closed_explicit_and_conditionally_normalized(
    service,
    output_adapter,
    root_fields,
    state,
    output_witnesses,
):
    wire = deepcopy(output_witnesses[service][state])
    assert set(wire) == root_fields
    assert wire["operation"] == "analyze"
    assert (wire["normalized"] is not None) is (state == "ready")
    _roundtrip(output_adapter, wire)

    extra = deepcopy(wire)
    extra["unknown_output"] = None
    _reject(output_adapter, extra)
    for field in root_fields:
        missing = deepcopy(wire)
        del missing[field]
        _reject(output_adapter, missing)


@pytest.mark.parametrize(
    ("service", "output_adapter"),
    [
        pytest.param("pac", PAC_ANALYZE_OUTPUT_ADAPTER, id="pac"),
        pytest.param(
            "rebalancer",
            REBALANCE_ANALYZE_OUTPUT_ADAPTER,
            id="rebalancer",
        ),
    ],
)
def test_normalized_output_preserves_32_contribution_addends(
    service,
    output_adapter,
    output_witnesses,
):
    assert P1_MAX_ROWS == 32
    addends = [
        {
            "currency": "EUR",
            "amount": str(index + 1),
            "monetary_step": "1",
        }
        for index in range(P1_MAX_ROWS)
    ]
    wire = deepcopy(output_witnesses[service]["ready"])
    _set(wire, ("normalized", "contributions"), addends)

    model = _roundtrip(output_adapter, wire)

    emitted = output_adapter.dump_python(model, mode="json")
    assert _at(emitted, ("normalized", "contributions")) == addends

    overflow = deepcopy(wire)
    _set(
        overflow,
        ("normalized", "contributions"),
        [
            *addends,
            {
                "currency": "EUR",
                "amount": str(P1_MAX_ROWS + 1),
                "monetary_step": "1",
            },
        ],
    )
    _reject(output_adapter, overflow)


def test_output_shapes_make_p1_non_goals_unrepresentable(output_witnesses):
    pac = output_witnesses["pac"]["ready"]
    rebalancer = output_witnesses["rebalancer"]["ready"]
    assert pac["result_kind"] == "pac_budget_analysis"
    assert pac["numeric_policy_id"] == "pac-budget-allocation-v1"
    assert rebalancer["result_kind"] == "portfolio_rebalancing_analysis"
    assert rebalancer["numeric_policy_id"] == "portfolio-rebalancing-v1"
    assert set(pac["allocations"][0]) == {
        "target_index",
        "instrument_key",
        "name",
        "target_percent",
        "ideal_allocation_reporting",
    }
    assert set(rebalancer["holdings"][0]) == {
        "holding_index",
        "row_key",
        "instrument_key",
        "name",
        "quantity",
        "current_value_native",
        "current_value_reporting",
    }
    prohibited = {
        "order",
        "orders",
        "trade",
        "trades",
        "proposal",
        "proposals",
        "solver",
        "optimality",
        "optimization",
        "feasibility",
        "trade_feasibility",
        "execution_fx",
    }
    for wire in (pac, rebalancer):
        assert not prohibited.intersection(key for _path, obj in _objects(wire) for key in obj)


def test_fact_shapes_and_decimal_output_are_strict(output_witnesses):
    wire = deepcopy(output_witnesses["pac"]["ready"])
    fact = wire["totals"]["investable_budget_reporting"]
    assert fact["availability"] == "available"
    assert fact["reason_codes"] == []
    assert type(fact["value"]["amount"]) is str

    for bad in (True, 1, 1.25, "NaN", "Infinity", "-Infinity"):
        mutated = deepcopy(wire)
        mutated["totals"]["investable_budget_reporting"]["value"]["amount"] = bad
        _reject(PAC_ANALYZE_OUTPUT_ADAPTER, mutated)

    for field in ("availability", "value", "reason_codes"):
        mutated = deepcopy(wire)
        del mutated["totals"]["investable_budget_reporting"][field]
        _reject(PAC_ANALYZE_OUTPUT_ADAPTER, mutated)

    unavailable = deepcopy(wire)
    unavailable["totals"]["investable_budget_reporting"] = {
        "availability": "unavailable",
        "value": None,
        "reason_codes": ["input_missing"],
    }
    _roundtrip(PAC_ANALYZE_OUTPUT_ADAPTER, unavailable)
    unavailable["totals"]["investable_budget_reporting"]["reason_codes"] = []
    _reject(PAC_ANALYZE_OUTPUT_ADAPTER, unavailable)


@pytest.mark.parametrize(
    ("wire_type", "maximum", "too_long"),
    [
        (
            CanonicalScalar,
            "-999999999999.123456789012",
            "-9999999999999.123456789012",
        ),
        (NativeAmount, "9" * 52, "9" * 53),
        (ReportingAmount, "9" * 80, "9" * 81),
        (CombinedAmount, "-9999999999999.123456789012", "9" * 29),
        (RatioNumerator, "9" * 96, "9" * 97),
        (RatioDenominator, "9" * 80, "9" * 81),
        (SquaredNumerator, "9" * 192, "9" * 193),
        (SquaredDenominator, "9" * 160, "9" * 161),
        (RatioApproximation, "-0." + "1" * 33, "-0." + "1" * 34),
    ],
)
def test_decimal_wire_aliases_have_hard_width_and_string_bounds(
    wire_type,
    maximum,
    too_long,
):
    adapter = TypeAdapter(wire_type)
    assert adapter.validate_python(maximum, strict=True) == maximum
    for bad in (too_long, True, 1, 1.5, "NaN", "Infinity"):
        with pytest.raises(ValidationError):
            adapter.validate_python(bad, strict=True)


@pytest.mark.parametrize(
    ("input_type", "root_field"),
    [
        (PacAnalyzeInput, "assets"),
        (RebalanceAnalyzeInput, "holdings"),
    ],
)
def test_exported_input_requires_operation_and_closes_every_object(
    input_type,
    root_field,
):
    schema = generate_tool_schema(TypeAdapter(input_type), "validation")
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert "operation" in schema["required"]
    assert "default" not in schema["properties"]["operation"]
    assert root_field in schema["properties"]
    for node in walk_schema(schema):
        if node.get("type") == "object" and "properties" in node:
            assert node.get("additionalProperties") is False


def _maximum_payloads() -> tuple[dict[str, object], dict[str, object]]:
    names = "🚀" * 128
    targets = [_target(f"instrument-{index}", "3" if index < P1_MAX_ROWS - 1 else "7") for index in range(P1_MAX_ROWS)]
    pac = {
        "operation": "analyze",
        "report_currency": "EUR",
        "as_of_date": "2026-09-14",
        "assets": [
            _asset(
                f"instrument-{index}",
                name=names,
                buy_grid={"mode": "fractional", "quantity_step": "0.000000000001"},
            )
            for index in range(P1_MAX_ROWS)
        ],
        "targets": targets,
        "cash_balances": [{"currency": "EUR", "amount": "999999999999.123456789012"}],
        "contributions": [],
        "valuation_rates": [],
    }
    rebalancer = {
        "operation": "analyze",
        "report_currency": "EUR",
        "as_of_date": "2026-09-14",
        "holdings": [
            _holding(
                f"custody-{index}",
                f"instrument-{index}",
                name=names,
                quantity="999999999999.123456789012",
                price="999999999999.123456789012",
                quote_base_quantity=10**18,
                buy_grid={"mode": "fractional", "quantity_step": "0.000000000001"},
            )
            for index in range(P1_MAX_ROWS)
        ],
        "targets": targets,
        "cash_balances": [],
        "contributions": [],
        "valuation_rates": [],
    }
    return pac, rebalancer


def test_real_maximum_rows_and_tool_schemas_fit_platform_limits():
    pac_payload, rebalance_payload = _maximum_payloads()
    definitions = {}
    maximum_inputs = {
        "pac_allocator": pac_payload,
        "portfolio_rebalancer": rebalance_payload,
    }
    analyzers = {
        "pac_allocator": analyze_pac_budget,
        "portfolio_rebalancer": analyze_rebalancing,
    }
    for service in PacAllocatorTool.services:
        definition = build_tool_definition(PacAllocatorTool, service)
        descriptor = definition.descriptor
        definitions[service.tool_code] = definition
        assert descriptor.contract_version == "1.0.0"
        assert descriptor.implementation_version == "1.0.0"
        assert re.fullmatch(r"[a-f0-9]{64}", descriptor.schema_fingerprint)
        assert descriptor.schema_fingerprint == schema_fingerprint(
            descriptor.input_schema,
            descriptor.output_schema,
            declared_operations(descriptor.input_schema),
        )
        (operation,) = descriptor.operations
        assert len(_encode(descriptor.input_schema)) < operation.max_parameter_bytes
        assert len(_encode(descriptor.output_schema)) < operation.max_result_bytes

        payload = maximum_inputs[service.tool_code]
        assert len(_encode(payload)) < operation.max_parameter_bytes
        request = definition.input_adapter.validate_python(payload, strict=True)
        result = analyzers[service.tool_code](request)
        emitted = definition.output_adapter.dump_json(result)
        assert len(emitted) <= P1_RESULT_BYTES
        assert len(emitted) < operation.max_result_bytes
        assert definition.output_adapter.validate_json(emitted, strict=True) == result

    export = build_tool_contracts_document(ToolRegistrySnapshot(definitions=definitions, failures=()))
    assert export["info"]["version"] == "2"
    manifest = export[TOOL_MANIFEST_KEY]
    assert manifest["manifestVersion"] == 2
    tools = {item["toolCode"]: item for item in manifest["tools"]}
    assert set(tools) == EXPECTED_TOOL_CODES
    for code in EXPECTED_TOOL_CODES:
        assert tools[code]["contractVersion"] == "1.0.0"
        assert tools[code]["schemaFingerprint"] == definitions[code].descriptor.schema_fingerprint
        assert tools[code]["componentKey"] == EXPECTED_COMPONENTS[code]
        assert tools[code]["uiVersion"] == "1.0.0"
        assert tools[code]["operations"] == ["analyze"]
        assert tools[code]["input"].startswith("#/components/schemas/")
        assert tools[code]["output"].startswith("#/components/schemas/")
