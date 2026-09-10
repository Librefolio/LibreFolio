"""Private Tool registry/catalog tests, without workers or application startup.

Every registry subclass, discovery directory and imported fixture namespace is
owned by one test. Normal application imports are never replaced or bypassed.
The temporary exports below only let real discovered fixture files refer to
their own registry; cleanup removes only those test-owned imports and exports.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Annotated, Literal, Self, TypedDict
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError, computed_field
from pydantic.dataclasses import dataclass as pydantic_dataclass

from backend.app.schemas.tools import ToolDocumentation, ToolOperationPolicy, ToolPlatformPolicy, ToolUIDescriptor
from backend.app.services.provider_registry import AbstractPluginRegistry, register_plugin
from backend.app.services.tools.base import ToolDefinitionError, ToolPlugin
from backend.app.services.tools.catalog import effective_catalog_entries, effective_operation, get_tool_catalog
from backend.app.services.tools.registry import ToolPluginRegistry, build_tool_definition
from backend.app.services.tools.wire import MAX_SAFE_JSON_INTEGER, encode_json


class _StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class _Text(_StrictModel):
    text: str


class _InspectInput(_StrictModel):
    operation: Literal["inspect"]
    payload: _Text
    label: str | None = None


class _RepeatInput(_StrictModel):
    operation: Literal["repeat"]
    text: str


class _ReadyOutput(_StrictModel):
    status: Literal["ready"]
    payload: _Text


class _UnavailableOutput(_StrictModel):
    status: Literal["unavailable"]
    reason: Literal["private_input"]


class _LooseText(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")

    text: str


class _LooseInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="allow")

    operation: Literal["inspect"]
    payload: _Text


class _NestedLooseInput(_StrictModel):
    operation: Literal["inspect"]
    payload: _LooseText


class _NestedLooseOutput(_StrictModel):
    status: Literal["ready"]
    payload: _LooseText


class _TypedPayload(TypedDict):
    text: str


class _NestedTypedDictInput(_StrictModel):
    operation: Literal["inspect"]
    payload: _TypedPayload


@pydantic_dataclass(config=ConfigDict(strict=True, extra="forbid"))
class _DataclassPayload:
    text: str


class _NestedDataclassOutput(_StrictModel):
    status: Literal["ready"]
    payload: _DataclassPayload


class _ComputedOutput(_StrictModel):
    status: Literal["ready"]
    payload: _Text

    @computed_field
    @property
    def summary(self) -> str:
        return f"{self.status}:{self.payload.text}"


class _SerializationAliasOutput(_StrictModel):
    status: Literal["ready"]
    payload: _Text = Field(serialization_alias="wire_payload")


class _ValidationAliasOutput(_StrictModel):
    status: Literal["ready"]
    payload: _Text = Field(validation_alias="wire_payload")


class _RoundTripAliasOutput(_StrictModel):
    status: Literal["ready"]
    payload: _Text = Field(validation_alias="wire_payload", serialization_alias="wire_payload")


class _TupleInput(_StrictModel):
    operation: Literal["inspect"]
    values: tuple[int, str]


class _SetOutput(_StrictModel):
    status: Literal["ready"]
    values: set[str]


class _IntegerBoundsInput(_StrictModel):
    operation: Literal["inspect"]
    unbounded: int
    minimum_only: Annotated[int, Field(ge=-17)]
    maximum_only: Annotated[int, Field(le=23)]
    narrower: Annotated[int, Field(ge=-17, le=23)]


class _NoOperationInput(_StrictModel):
    payload: _Text


class _DefaultOperationInput(_StrictModel):
    operation: Literal["inspect"] = "inspect"
    payload: _Text


class _StringOperationInput(_StrictModel):
    operation: str
    payload: _Text


class _NumericOperationInput(_StrictModel):
    operation: Literal[1]
    payload: _Text


class _RecursiveInput(_StrictModel):
    operation: Literal["inspect"]
    child: Self | None = None


class _PrivatePlugin(ToolPlugin[_InspectInput, _ReadyOutput]):
    """A primitive fixture, never a registered production plugin or PAC oracle."""

    tool_code = "private_probe"
    contract_version = "1.0.0"
    implementation_version = "1.0.0"
    name = "Private registry probe"
    description = "A private typed fixture for Tool publication tests."
    category = "testing"
    icon_key = "code"
    ui = ToolUIDescriptor(kind="custom", component_key="private-registry-probe", ui_contract_version=1)
    documentation = ToolDocumentation(path="user/tools/private-registry-probe/", version="1.0.0")
    operations = (ToolOperationPolicy(operation="inspect"),)
    input_type = _InspectInput
    output_type = _ReadyOutput

    def __init__(self):
        raise AssertionError("Catalog and discovery must not construct the private plugin")

    def compute(self, parameters, context):
        raise AssertionError("Registry tests must not execute a Tool")

    def probe(self):
        raise AssertionError("Catalog and discovery must not probe a Tool")

    def reset(self):
        raise AssertionError("Catalog and discovery must not reset a Tool")


def _register_through_helper(registry: type[ToolPluginRegistry], plugin_class: type) -> None:
    register_plugin(registry)(plugin_class)


@dataclass(frozen=True)
class _DiscoveryFixture:
    registry: type[ToolPluginRegistry]
    directory: Path
    namespace: str
    registry_symbol: str

    def write_module(self, stem: str, body: str) -> str:
        imports = f"from {__name__} import {self.registry_symbol} as Registry\n" f"from {__name__} import _PrivatePlugin, _register_through_helper\n" "from backend.app.services.provider_registry import register_plugin\n"
        (self.directory / f"{stem}.py").write_text(imports + dedent(body), encoding="utf-8")
        return f"{self.namespace}.{stem}"


@pytest.fixture
def discovery_factory(tmp_path, monkeypatch):
    owned_namespaces: set[str] = set()

    def make() -> _DiscoveryFixture:
        suffix = uuid4().hex
        namespace = f"_private_tool_registry_{suffix}"
        directory = tmp_path / namespace
        directory.mkdir()

        class PrivateRegistry(ToolPluginRegistry):
            @classmethod
            def _get_plugin_directory(cls) -> Path:
                return directory

            @classmethod
            def _get_module_namespace(cls) -> str:
                return namespace

        registry_symbol = f"_fixture_registry_{suffix}"
        # These are exports of this test module, not fake application modules.
        monkeypatch.setitem(globals(), registry_symbol, PrivateRegistry)
        owned_namespaces.add(namespace)
        return _DiscoveryFixture(PrivateRegistry, directory, namespace, registry_symbol)

    try:
        yield make
    finally:
        for module_name in tuple(sys.modules):
            if any(module_name.startswith(namespace + ".") for namespace in owned_namespaces):
                sys.modules.pop(module_name, None)


@pytest.fixture
def plugin_factory():
    def make(code: str = "private_probe", **attributes) -> type[_PrivatePlugin]:
        return type("PrivateClaimant", (_PrivatePlugin,), {"__module__": __name__, "tool_code": code, **attributes})

    return make


def _publish(discovery, *plugins):
    for plugin in plugins:
        register_plugin(discovery.registry)(plugin)
    return discovery.registry.get_snapshot()


def test_real_registry_subclass_and_decorator_publish_typed_models(discovery_factory, plugin_factory):
    discovery = discovery_factory()
    plugin = plugin_factory()
    assert issubclass(discovery.registry, AbstractPluginRegistry)
    assert register_plugin(discovery.registry)(plugin) is plugin

    snapshot = discovery.registry.get_snapshot()
    definition = snapshot.definitions[plugin.tool_code]
    assert discovery.registry.get_plugin(plugin.tool_code) is plugin
    assert discovery.registry.get_definition(plugin.tool_code) is definition
    assert definition.plugin_class is plugin
    assert not snapshot.failures
    assert definition.descriptor.ui == plugin.ui
    assert definition.descriptor.documentation == plugin.documentation
    assert {policy.operation for policy in definition.descriptor.operations} == {"inspect"}

    parameters = definition.input_adapter.validate_python({"operation": "inspect", "payload": {"text": " e\u0301 🚀 "}})
    result = definition.output_adapter.validate_python({"status": "ready", "payload": {"text": " e\u0301 🚀 "}})
    assert isinstance(parameters, _InspectInput)
    assert isinstance(result, _ReadyOutput)
    assert parameters.payload.text == result.payload.text == " e\u0301 🚀 "


@pytest.mark.parametrize("direction", ["input", "output"])
@pytest.mark.parametrize(
    ("payload", "error_type"),
    [({"text": "private", "unexpected": True}, "extra_forbidden"), ({"text": 1}, "string_type")],
)
def test_published_adapters_enforce_real_nested_models(direction, payload, error_type, discovery_factory, plugin_factory):
    plugin = plugin_factory()
    definition = _publish(discovery_factory(), plugin).definitions[plugin.tool_code]
    adapter = definition.input_adapter if direction == "input" else definition.output_adapter
    envelope = {"operation": "inspect"} if direction == "input" else {"status": "ready"}

    with pytest.raises(ValidationError) as caught:
        adapter.validate_python({**envelope, "payload": deepcopy(payload)})

    assert any(issue["type"] == error_type and issue["loc"][0] == "payload" for issue in caught.value.errors(include_input=False))


def test_subclasses_do_not_share_claims_or_published_definitions(discovery_factory, plugin_factory):
    first = discovery_factory()
    second = discovery_factory()
    first_plugin = plugin_factory("private_shared_code")
    second_plugin = plugin_factory("private_shared_code")

    first_snapshot = _publish(first, first_plugin)
    second_snapshot = _publish(second, second_plugin)

    assert first_snapshot.definitions["private_shared_code"].plugin_class is first_plugin
    assert second_snapshot.definitions["private_shared_code"].plugin_class is second_plugin
    assert first_snapshot is not second_snapshot
    assert not first_snapshot.failures
    assert not second_snapshot.failures


def test_same_class_object_registration_is_idempotent_before_and_after_publication(discovery_factory, plugin_factory):
    discovery = discovery_factory()
    plugin = plugin_factory()
    register_plugin(discovery.registry)(plugin)
    register_plugin(discovery.registry)(plugin)
    snapshot = discovery.registry.get_snapshot()

    register_plugin(discovery.registry)(plugin)

    assert discovery.registry.get_snapshot() is snapshot
    assert set(snapshot.definitions) == {plugin.tool_code}
    assert snapshot.definitions[plugin.tool_code].plugin_class is plugin
    assert not snapshot.failures


def test_distinct_classes_with_identical_names_are_still_duplicate_claimants(discovery_factory, plugin_factory):
    first = plugin_factory("private_duplicate")
    second = plugin_factory("private_duplicate")
    assert first is not second
    assert (first.__module__, first.__qualname__) == (second.__module__, second.__qualname__)

    snapshot = _publish(discovery_factory(), first, second)

    assert "private_duplicate" not in snapshot.definitions
    failures = [failure for failure in snapshot.failures if failure.tool_code == "private_duplicate"]
    assert len(failures) == 2
    assert {failure.reason for failure in failures} == {"duplicate_code"}


@pytest.mark.parametrize("reverse", [False, True], ids=["valid-first", "rival-first"])
@pytest.mark.parametrize("rival_kind", ["valid", "invalid-descriptor", "invalid-model", "not-a-plugin"])
def test_all_duplicate_claimants_are_quarantined_regardless_of_import_order(reverse, rival_kind, discovery_factory):
    discovery = discovery_factory()
    valid = """
        @register_plugin(Registry)
        class Claimant(_PrivatePlugin):
            tool_code = "private_duplicate"
    """
    rivals = {
        "valid": valid,
        "invalid-descriptor": """
            @register_plugin(Registry)
            class Claimant(_PrivatePlugin):
                tool_code = "private_duplicate"
                contract_version = "not-a-semver"
        """,
        "invalid-model": """
            @register_plugin(Registry)
            class Claimant(_PrivatePlugin):
                tool_code = "private_duplicate"
                input_type = str
        """,
        "not-a-plugin": """
            @register_plugin(Registry)
            class Claimant:
                tool_code = "private_duplicate"
        """,
    }
    first, second = (rivals[rival_kind], valid) if reverse else (valid, rivals[rival_kind])
    discovery.write_module("a_claim", first)
    discovery.write_module("b_claim", second)
    discovery.write_module(
        "z_healthy",
        """
        @register_plugin(Registry)
        class Healthy(_PrivatePlugin):
            tool_code = "private_healthy"
        """,
    )

    snapshot = discovery.registry.get_snapshot()

    assert set(snapshot.definitions) == {"private_healthy"}
    duplicate_failures = [failure for failure in snapshot.failures if failure.tool_code == "private_duplicate"]
    assert len(duplicate_failures) == 2
    assert {failure.reason for failure in duplicate_failures} == {"duplicate_code"}
    assert {failure.filename for failure in duplicate_failures} == {"a_claim.py", "b_claim.py"}
    catalog = get_tool_catalog(ToolPlatformPolicy(), discovery.registry)
    assert {descriptor.tool_code for descriptor in catalog.items} == {"private_healthy"}
    assert [(item.tool_code, item.reason) for item in catalog.unavailable] == [("private_duplicate", "unavailable")]


@pytest.mark.parametrize(
    ("attribute", "bad_type", "reason"),
    [
        ("input_type", int, "invalid_input_model"),
        ("input_type", dict[str, str], "invalid_input_model"),
        ("output_type", str, "invalid_output_model"),
        ("output_type", list[_ReadyOutput], "invalid_schema"),
        ("input_type", _LooseInput, "invalid_input_model"),
        ("input_type", _NestedLooseInput, "invalid_input_model"),
        ("output_type", _NestedLooseOutput, "invalid_output_model"),
    ],
)
def test_invalid_or_open_models_quarantine_only_their_tool(attribute, bad_type, reason, discovery_factory, plugin_factory):
    broken = plugin_factory("private_invalid_model", **{attribute: bad_type})
    healthy = plugin_factory("private_healthy")
    snapshot = _publish(discovery_factory(), broken, healthy)

    assert set(snapshot.definitions) == {healthy.tool_code}
    failures = [failure for failure in snapshot.failures if failure.tool_code == broken.tool_code]
    assert {failure.reason for failure in failures} == {reason}


@pytest.mark.parametrize(
    ("attribute", "bad_type", "reason"),
    [
        pytest.param("input_type", _NestedTypedDictInput, "invalid_input_model", id="nested-typed-dict"),
        pytest.param("output_type", _NestedDataclassOutput, "invalid_output_model", id="nested-pydantic-dataclass"),
    ],
)
def test_nested_non_model_shapes_quarantine_only_their_claim(attribute, bad_type, reason, discovery_factory, plugin_factory):
    broken = plugin_factory("private_nested_shape", **{attribute: bad_type})
    healthy = plugin_factory("private_healthy")

    snapshot = _publish(discovery_factory(), broken, healthy)

    assert set(snapshot.definitions) == {healthy.tool_code}
    assert [(failure.tool_code, failure.reason) for failure in snapshot.failures] == [(broken.tool_code, reason)]


@pytest.mark.parametrize(
    ("output_type", "code"),
    [
        pytest.param(_ComputedOutput, "private_computed_output", id="computed-field"),
        pytest.param(_SerializationAliasOutput, "private_serialization_alias", id="serialization-only-alias"),
        pytest.param(_ValidationAliasOutput, "private_validation_alias", id="validation-only-alias"),
    ],
)
def test_non_roundtrippable_outputs_are_quarantined_without_hiding_healthy_tools(output_type, code, discovery_factory, plugin_factory):
    broken = plugin_factory(code, output_type=output_type)
    healthy = plugin_factory("private_healthy")

    snapshot = _publish(discovery_factory(), broken, healthy)

    assert set(snapshot.definitions) == {healthy.tool_code}
    assert [(failure.tool_code, failure.reason) for failure in snapshot.failures] == [(broken.tool_code, "invalid_output_model")]


def test_matching_validation_and_serialization_alias_is_published_only_when_wire_roundtrip_succeeds(plugin_factory):
    definition = build_tool_definition(plugin_factory("private_roundtrip_alias", output_type=_RoundTripAliasOutput))
    value = _RoundTripAliasOutput.model_validate({"status": "ready", "wire_payload": {"text": "private"}})

    wire_value = definition.output_adapter.dump_python(value, mode="json", by_alias=True, warnings="error")
    payload = encode_json(wire_value)
    validated = definition.output_adapter.validate_json(payload, strict=True)

    assert wire_value == {
        "status": "ready",
        "wire_payload": {"text": "private"},
    }
    assert validated == value
    assert "wire_payload" in definition.descriptor.output_schema["properties"]
    assert "payload" not in definition.descriptor.output_schema["properties"]


def test_frontend_unsupported_tuple_and_set_schemas_are_quarantined_individually(discovery_factory, plugin_factory):
    tuple_claim = plugin_factory("private_tuple_schema", input_type=_TupleInput)
    set_claim = plugin_factory("private_set_schema", output_type=_SetOutput)
    healthy = plugin_factory("private_healthy")

    snapshot = _publish(discovery_factory(), tuple_claim, set_claim, healthy)

    assert set(snapshot.definitions) == {healthy.tool_code}
    assert len(snapshot.failures) == 2
    assert {(failure.tool_code, failure.reason) for failure in snapshot.failures} == {
        (tuple_claim.tool_code, "invalid_schema"),
        (set_claim.tool_code, "invalid_schema"),
    }


def test_published_integer_schema_injects_safe_bounds_without_widening_stricter_fields(plugin_factory):
    definition = build_tool_definition(plugin_factory("private_integer_bounds", input_type=_IntegerBoundsInput))
    properties = definition.descriptor.input_schema["properties"]

    assert {name: (properties[name]["minimum"], properties[name]["maximum"]) for name in ("unbounded", "minimum_only", "maximum_only", "narrower")} == {
        "unbounded": (-MAX_SAFE_JSON_INTEGER, MAX_SAFE_JSON_INTEGER),
        "minimum_only": (-17, MAX_SAFE_JSON_INTEGER),
        "maximum_only": (-MAX_SAFE_JSON_INTEGER, 23),
        "narrower": (-17, 23),
    }


@pytest.mark.parametrize("input_type", [_NoOperationInput, _DefaultOperationInput, _StringOperationInput, _NumericOperationInput])
def test_input_operations_are_required_literal_strings_without_defaults(input_type, plugin_factory):
    plugin = plugin_factory(input_type=input_type)
    with pytest.raises(ToolDefinitionError) as caught:
        build_tool_definition(plugin)
    assert caught.value.reason == "invalid_operation_policy"


@pytest.mark.parametrize("declared", [(), ("repeat",), ("inspect", "repeat"), ("inspect", "inspect")])
def test_policy_operations_must_match_input_without_duplicates(declared, discovery_factory, plugin_factory):
    plugin = plugin_factory("private_mismatched_policy", operations=tuple(ToolOperationPolicy(operation=name) for name in declared))
    healthy = plugin_factory("private_healthy")
    snapshot = _publish(discovery_factory(), plugin, healthy)

    assert set(snapshot.definitions) == {healthy.tool_code}
    failures = [failure for failure in snapshot.failures if failure.tool_code == plugin.tool_code]
    assert failures
    assert all(failure.reason in {"invalid_operation_policy", "invalid_descriptor"} for failure in failures)


def test_input_and_output_discriminated_unions_publish_real_branch_adapters(discovery_factory, plugin_factory):
    input_type = Annotated[_InspectInput | _RepeatInput, Field(discriminator="operation")]
    output_type = Annotated[_ReadyOutput | _UnavailableOutput, Field(discriminator="status")]
    plugin = plugin_factory(
        "private_union",
        input_type=input_type,
        output_type=output_type,
        operations=(ToolOperationPolicy(operation="inspect"), ToolOperationPolicy(operation="repeat")),
    )
    definition = _publish(discovery_factory(), plugin).definitions[plugin.tool_code]

    assert {policy.operation for policy in definition.descriptor.operations} == {"inspect", "repeat"}
    inspect_input = definition.input_adapter.validate_python({"operation": "inspect", "payload": {"text": "private"}})
    repeat_input = definition.input_adapter.validate_python({"operation": "repeat", "text": "private"})
    ready_output = definition.output_adapter.validate_python({"status": "ready", "payload": {"text": "private"}})
    unavailable_output = definition.output_adapter.validate_python({"status": "unavailable", "reason": "private_input"})
    assert isinstance(inspect_input, _InspectInput)
    assert isinstance(repeat_input, _RepeatInput)
    assert isinstance(ready_output, _ReadyOutput)
    assert isinstance(unavailable_output, _UnavailableOutput)
    with pytest.raises(ValidationError):
        definition.input_adapter.validate_python({"text": "private"})
    with pytest.raises(ValidationError):
        definition.output_adapter.validate_python({"status": "other", "reason": "private_input"})


@pytest.mark.parametrize("direction", ["input", "output"])
def test_model_unions_require_an_explicit_discriminator(direction, discovery_factory, plugin_factory):
    attributes = (
        {
            "input_type": _InspectInput | _RepeatInput,
            "operations": (ToolOperationPolicy(operation="inspect"), ToolOperationPolicy(operation="repeat")),
        }
        if direction == "input"
        else {"output_type": _ReadyOutput | _UnavailableOutput}
    )
    plugin = plugin_factory("private_untagged_union", **attributes)
    healthy = plugin_factory("private_healthy")
    snapshot = _publish(discovery_factory(), plugin, healthy)

    assert plugin.tool_code not in snapshot.definitions
    assert snapshot.definitions[healthy.tool_code].plugin_class is healthy
    failures = [failure for failure in snapshot.failures if failure.tool_code == plugin.tool_code]
    assert failures
    assert all(failure.reason in {"invalid_input_model", "invalid_output_model", "invalid_schema"} for failure in failures)


def test_local_recursive_model_references_are_supported(plugin_factory):
    definition = build_tool_definition(plugin_factory(input_type=_RecursiveInput))
    parameters = definition.input_adapter.validate_python({"operation": "inspect", "child": {"operation": "inspect", "child": None}})
    assert isinstance(parameters, _RecursiveInput)
    assert isinstance(parameters.child, _RecursiveInput)
    assert parameters.child.operation == "inspect"
    assert parameters.child.child is None


@pytest.mark.parametrize(
    "schema_extra",
    [
        {"$ref": "#/$defs/private_missing"},
        {"$ref": "https://example.invalid/private.json"},
        {"$id": "https://example.invalid/private.json"},
        {"$dynamicRef": "#"},
        {"$recursiveRef": "#"},
        {"discriminator": {"propertyName": "operation", "mapping": {"inspect": "#/$defs/private_missing"}}},
        {"discriminator": {"propertyName": "operation", "mapping": {"inspect": "https://example.invalid/private.json"}}},
    ],
)
def test_unresolved_or_remote_schema_references_quarantine_real_models(schema_extra, discovery_factory, plugin_factory):
    class InvalidReferenceInput(_InspectInput):
        # A real model with deliberately invalid export metadata, not a hand-written root schema.
        model_config = ConfigDict(strict=True, extra="forbid", json_schema_extra=deepcopy(schema_extra))

    broken = plugin_factory("private_invalid_reference", input_type=InvalidReferenceInput)
    healthy = plugin_factory("private_healthy")
    snapshot = _publish(discovery_factory(), broken, healthy)

    assert set(snapshot.definitions) == {healthy.tool_code}
    failures = [failure for failure in snapshot.failures if failure.tool_code == broken.tool_code]
    assert {failure.reason for failure in failures} == {"invalid_schema"}


def test_unresolved_python_annotations_cannot_publish_a_tool(discovery_factory, plugin_factory):
    class UnresolvedInput(_StrictModel):
        operation: Literal["inspect"]
        payload: "NeverDefinedPrivateModel"  # noqa: F821, UP037 - unresolved on purpose

    broken = plugin_factory("private_unresolved", input_type=UnresolvedInput)
    healthy = plugin_factory("private_healthy")
    snapshot = _publish(discovery_factory(), broken, healthy)

    assert broken.tool_code not in snapshot.definitions
    assert snapshot.definitions[healthy.tool_code].plugin_class is healthy
    failures = [failure for failure in snapshot.failures if failure.tool_code == broken.tool_code]
    assert failures
    assert all(failure.reason in {"invalid_input_model", "invalid_schema"} for failure in failures)


@pytest.mark.parametrize("code", [None, "", "Private_probe", "private-probe", " private_probe", "private_probe "])
def test_invalid_code_claimants_cannot_become_canonical_aliases(code, discovery_factory, plugin_factory):
    healthy = plugin_factory("private_healthy")
    broken = plugin_factory(code)
    snapshot = _publish(discovery_factory(), broken, healthy)

    assert set(snapshot.definitions) == {healthy.tool_code}
    assert {(failure.tool_code, failure.reason) for failure in snapshot.failures} == {(None, "invalid_code")}


@pytest.mark.parametrize("kind", ["not-a-class", "not-a-plugin", "abstract", "required-constructor", "async-compute", "invalid-metadata"])
def test_invalid_plugins_and_constructor_signatures_are_quarantined(kind, discovery_factory, plugin_factory):
    class AbstractClaim(ToolPlugin[_InspectInput, _ReadyOutput]):
        tool_code = "private_invalid"

    def required_constructor(self, required_argument):
        raise AssertionError("A required constructor must be inspected, not invoked")

    async def async_compute(self, parameters, context):
        raise AssertionError("Async Tool definitions must not be invoked")

    claims = {
        "not-a-class": object(),
        "not-a-plugin": type("PrivateUnrelatedClass", (), {"tool_code": "private_invalid"}),
        "abstract": AbstractClaim,
        "required-constructor": plugin_factory("private_invalid", __init__=required_constructor),
        "async-compute": plugin_factory("private_invalid", compute=async_compute),
        "invalid-metadata": plugin_factory("private_invalid", ui=None),
    }
    discovery = discovery_factory()
    healthy = plugin_factory("private_healthy")
    snapshot = _publish(discovery, claims[kind], healthy)

    assert set(snapshot.definitions) == {healthy.tool_code}
    expected_reason = "invalid_descriptor" if kind == "invalid-metadata" else "invalid_plugin"
    assert {failure.reason for failure in snapshot.failures} == {expected_reason}


@pytest.mark.parametrize("lookup", ["PRIVATE_PROBE", " private_probe", "private_probe ", "private-probe", "private"])
def test_lookups_match_codes_exactly(lookup, discovery_factory, plugin_factory):
    discovery = discovery_factory()
    plugin = plugin_factory("private_probe")
    _publish(discovery, plugin)

    assert discovery.registry.get_definition(plugin.tool_code).plugin_class is plugin
    assert discovery.registry.get_plugin(plugin.tool_code) is plugin
    assert discovery.registry.get_definition(lookup) is None
    assert discovery.registry.get_plugin(lookup) is None


@pytest.mark.parametrize("through_helper", [False, True], ids=["decorator", "helper"])
@pytest.mark.parametrize("spoof_module", [False, True], ids=["original-module", "spoofed-module"])
def test_registration_is_rolled_back_when_its_import_caller_fails(through_helper, spoof_module, discovery_factory):
    discovery = discovery_factory()
    registration = "_register_through_helper(Registry, Broken)" if through_helper else "register_plugin(Registry)(Broken)"
    body = "class Broken(_PrivatePlugin):\n" '    tool_code = "private_broken"\n' + ('    __module__ = "backend.app.services.tools.base"\n' if spoof_module else "") + registration + '\nraise RuntimeError("PRIVATE_IMPORT_INPUT_SENTINEL")\n'
    failed_module = discovery.write_module("a_broken", body)
    discovery.write_module(
        "z_healthy",
        """
        @register_plugin(Registry)
        class Healthy(_PrivatePlugin):
            tool_code = "private_healthy"
        """,
    )

    snapshot = discovery.registry.get_snapshot()

    assert failed_module not in sys.modules
    assert set(snapshot.definitions) == {"private_healthy"}
    assert discovery.registry.get_definition("private_broken") is None
    failures = [failure for failure in snapshot.failures if failure.tool_code == "private_broken"]
    assert {(failure.filename, failure.reason) for failure in failures} == {("a_broken.py", "import_failed")}
    public_failures = [failure.model_dump(mode="json") for failure in snapshot.failures]
    public_json = json.dumps(public_failures)
    assert "PRIVATE_IMPORT_INPUT_SENTINEL" not in public_json
    assert str(discovery.directory) not in public_json
    assert "Traceback" not in public_json
    assert all(set(failure) == {"tool_code", "filename", "reason"} for failure in public_failures)
    catalog = get_tool_catalog(ToolPlatformPolicy(), discovery.registry)
    assert {descriptor.tool_code for descriptor in catalog.items} == {"private_healthy"}
    assert ("private_broken", "unavailable") in {(item.tool_code, item.reason) for item in catalog.unavailable}


def test_import_failure_diagnostics_sanitize_an_unsafe_module_filename(discovery_factory):
    discovery = discovery_factory()
    discovery.write_module("private é", 'raise RuntimeError("PRIVATE_RAW_EXCEPTION_SENTINEL")\n')

    snapshot = discovery.registry.get_snapshot()

    assert not snapshot.definitions
    assert [(failure.filename, failure.reason) for failure in snapshot.failures] == [("plugin.py", "import_failed")]
    public_json = json.dumps([failure.model_dump(mode="json") for failure in snapshot.failures])
    assert "PRIVATE_RAW_EXCEPTION_SENTINEL" not in public_json
    assert "private é" not in public_json
    assert str(discovery.directory) not in public_json


def test_snapshot_cannot_publish_during_an_import(discovery_factory):
    discovery = discovery_factory()
    discovery.write_module(
        "private_reentrant",
        """
        @register_plugin(Registry)
        class Pending(_PrivatePlugin):
            tool_code = "private_pending"

        try:
            Registry.get_snapshot()
        except RuntimeError:
            pass
        else:
            raise AssertionError("A partial snapshot was observable during import")
        """,
    )

    snapshot = discovery.registry.get_snapshot()

    assert set(snapshot.definitions) == {"private_pending"}
    assert not snapshot.failures


def test_catalog_and_snapshot_do_not_construct_compute_probe_or_rediscover(discovery_factory, plugin_factory, monkeypatch):
    discovery = discovery_factory()
    plugin = plugin_factory()
    snapshot = _publish(discovery, plugin)

    def forbidden_directory(cls):
        raise AssertionError("Reading a published snapshot must not restart discovery")

    monkeypatch.setattr(discovery.registry, "_get_plugin_directory", classmethod(forbidden_directory))
    first_catalog = get_tool_catalog(ToolPlatformPolicy(), discovery.registry)
    second_catalog = get_tool_catalog(ToolPlatformPolicy(), discovery.registry)

    assert discovery.registry.get_snapshot() is snapshot
    assert discovery.registry.get_definition(plugin.tool_code).plugin_class is plugin
    assert {descriptor.tool_code for descriptor in first_catalog.items} == {plugin.tool_code}
    assert first_catalog == second_catalog
    assert not first_catalog.unavailable


def test_constructor_typeerror_is_not_retried_with_different_arguments(discovery_factory, plugin_factory):
    calls = []

    def constructor(self, **kwargs):
        calls.append(dict(kwargs))
        raise TypeError("PRIVATE_CONSTRUCTOR_SENTINEL")

    discovery = discovery_factory()
    plugin = plugin_factory(__init__=constructor)
    _publish(discovery, plugin)

    with pytest.raises(TypeError, match="PRIVATE_CONSTRUCTOR_SENTINEL"):
        discovery.registry.get_plugin_instance(plugin.tool_code, private_argument="owned")

    assert calls == [{"private_argument": "owned"}]


def test_publication_closes_registration_without_replacing_healthy_definitions(discovery_factory, plugin_factory):
    discovery = discovery_factory()
    healthy = plugin_factory()
    snapshot = _publish(discovery, healthy)

    with pytest.raises(RuntimeError):
        register_plugin(discovery.registry)(plugin_factory("private_late"))
    with pytest.raises(TypeError):
        snapshot.definitions["private_late"] = snapshot.definitions[healthy.tool_code]

    assert discovery.registry.get_snapshot() is snapshot
    assert set(snapshot.definitions) == {healthy.tool_code}


def test_catalog_descriptors_are_independent_deep_copies(discovery_factory, plugin_factory):
    discovery = discovery_factory()
    plugin = plugin_factory()
    snapshot = _publish(discovery, plugin)
    original = deepcopy(snapshot.definitions[plugin.tool_code].descriptor.model_dump())
    first_catalog = get_tool_catalog(ToolPlatformPolicy(), discovery.registry)
    first_descriptor = next(item for item in first_catalog.items if item.tool_code == plugin.tool_code)

    first_descriptor.input_schema["properties"]["payload"]["description"] = "private mutation"
    first_descriptor.output_schema["properties"]["status"]["const"] = "mutated"
    first_descriptor.operations.clear()
    first_catalog.items.clear()

    next_catalog = get_tool_catalog(ToolPlatformPolicy(), discovery.registry)
    next_descriptor = next(item for item in next_catalog.items if item.tool_code == plugin.tool_code)
    assert snapshot.definitions[plugin.tool_code].descriptor.model_dump() == original
    assert next_descriptor.model_dump() == original
    assert {policy.operation for policy in plugin.operations} == {"inspect"}


@pytest.mark.parametrize("reverse", [False, True])
def test_catalog_order_and_fingerprint_are_stable_without_changing_registration_order(reverse, discovery_factory, plugin_factory):
    discovery = discovery_factory()
    first = plugin_factory("private_a")
    second = plugin_factory("private_z")
    plugins = (second, first) if reverse else (first, second)
    snapshot = _publish(discovery, *plugins)
    catalog = get_tool_catalog(ToolPlatformPolicy(), discovery.registry)

    assert [descriptor.tool_code for descriptor in catalog.items] == ["private_a", "private_z"]
    for descriptor in catalog.items:
        assert descriptor.schema_fingerprint == snapshot.definitions[descriptor.tool_code].descriptor.schema_fingerprint
    assert snapshot.definitions[first.tool_code].descriptor.schema_fingerprint == snapshot.definitions[second.tool_code].descriptor.schema_fingerprint


def test_effective_policy_only_lowers_limits_and_reserves_output_time():
    declared = ToolOperationPolicy(
        operation="inspect",
        deterministic=False,
        max_parameter_bytes=262_144,
        max_result_bytes=131_072,
        queue_timeout_ms=9_000,
        job_timeout_ms=3_000,
        soft_timeout_ms=2_900,
    )
    original = declared.model_dump()

    effective = effective_operation(declared, ToolPlatformPolicy())

    assert effective.max_parameter_bytes == 131_072
    assert effective.max_result_bytes == 131_072
    assert effective.queue_timeout_ms == 5_000
    assert effective.job_timeout_ms == 3_000
    assert effective.soft_timeout_ms == 2_000
    assert effective.pure is True
    assert effective.deterministic is False
    assert effective.deduplication == "none"
    assert declared.model_dump() == original


def test_one_invalid_effective_policy_does_not_hide_healthy_tools_or_poison_snapshot(discovery_factory, plugin_factory):
    discovery = discovery_factory()
    tight = plugin_factory(
        "private_tight_deadline",
        operations=(ToolOperationPolicy(operation="inspect", job_timeout_ms=1_000, soft_timeout_ms=900),),
    )
    healthy = plugin_factory("private_healthy")
    snapshot = _publish(discovery, tight, healthy)
    assert not snapshot.failures
    assert set(snapshot.definitions) == {tight.tool_code, healthy.tool_code}

    descriptors, failures = effective_catalog_entries(ToolPlatformPolicy(), discovery.registry)
    assert {descriptor.tool_code for descriptor in descriptors} == {healthy.tool_code}
    assert {(failure.tool_code, failure.reason) for failure in failures} == {(tight.tool_code, "invalid_operation_policy")}
    catalog = get_tool_catalog(ToolPlatformPolicy(), discovery.registry)
    assert {descriptor.tool_code for descriptor in catalog.items} == {healthy.tool_code}
    assert [(item.tool_code, item.reason) for item in catalog.unavailable] == [(tight.tool_code, "unavailable")]

    relaxed_reserve = ToolPlatformPolicy(output_reserve_ms=100)
    next_catalog = get_tool_catalog(relaxed_reserve, discovery.registry)
    assert {descriptor.tool_code for descriptor in next_catalog.items} == {tight.tool_code, healthy.tool_code}
    assert not next_catalog.unavailable
    assert discovery.registry.get_snapshot() is snapshot
    assert not snapshot.failures
