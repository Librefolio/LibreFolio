"""Build-only OpenAPI contracts derived from the registry's real Pydantic roots."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterator
from copy import deepcopy
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, JsonValue, TypeAdapter

from backend.app.schemas.tools import (
    ToolCatalogResponse,
    ToolComputeBatchRequest,
    ToolComputeBatchResponse,
    ToolDiagnosticsResponse,
)
from backend.app.services.tools.registry import ToolPluginRegistry, ToolRegistrySnapshot
from backend.app.services.tools.schema import (
    declared_operations,
    generate_tool_schema,
    resolve_schema_reference,
    schema_fingerprint,
    walk_schema,
)

TOOL_MANIFEST_KEY = "x-librefolio-tools"
TOOL_COMPONENT_SOURCE_KEY = "x-librefolio-tool-source"
SchemaMode = Literal["validation", "serialization"]

_SCHEMA_MAPS = ("properties", "patternProperties", "dependentSchemas")
_SCHEMA_ARRAYS = ("allOf", "anyOf", "oneOf", "prefixItems")
_SCHEMA_SINGLE = (
    "items",
    "additionalProperties",
    "unevaluatedProperties",
    "contains",
    "propertyNames",
    "not",
    "if",
    "then",
    "else",
)
_FORBIDDEN_REFERENCE_KEYS = frozenset(("$id", "$anchor", "$dynamicAnchor", "$dynamicRef", "$recursiveRef", "$recursiveAnchor"))
_ANNOTATION_KEYS = frozenset(("title", "description", "default", "examples", "deprecated", "readOnly", "writeOnly"))


class ToolSchemaExportError(ValueError):
    """A declared healthy contract cannot be exported without losing meaning."""


@dataclass(frozen=True, slots=True)
class _TransportRoot:
    role: str
    model: type[BaseModel]
    mode: SchemaMode
    component_name: str


@dataclass(frozen=True, slots=True)
class _Discriminator:
    property_name: str
    mapping: dict[str, JsonValue]
    branches: list[JsonValue]


_TRANSPORT_ROOTS = (
    _TransportRoot("catalog", ToolCatalogResponse, "serialization", "ToolTransportCatalog"),
    _TransportRoot("computeRequest", ToolComputeBatchRequest, "validation", "ToolTransportComputeRequest"),
    _TransportRoot("computeResponse", ToolComputeBatchResponse, "serialization", "ToolTransportComputeResponse"),
    _TransportRoot("diagnostics", ToolDiagnosticsResponse, "serialization", "ToolTransportDiagnostics"),
)


def _component_reference(name: str) -> str:
    return f"#/components/schemas/{name}"


def _local_target(document: dict[str, JsonValue], reference: object, schema_nodes: set[int]) -> dict[str, JsonValue]:
    if not isinstance(reference, str) or not (reference == "#" or reference.startswith("#/")):
        raise ToolSchemaExportError(f"Only local JSON Pointer references are supported: {reference!r}")
    # Percent-encoded fragments and malformed pointer escapes must not acquire aliases.
    if "%" in reference:
        raise ToolSchemaExportError(f"Encoded reference fragments are unsupported: {reference!r}")
    for token in reference[2:].split("/"):
        remainder = token.replace("~1", "").replace("~0", "")
        if "~" in remainder:
            raise ToolSchemaExportError(f"Invalid JSON Pointer escape: {reference!r}")
    try:
        target = resolve_schema_reference(document, reference)
    except ValueError as exc:
        raise ToolSchemaExportError(f"Unresolved schema reference: {reference!r}") from exc
    if id(target) not in schema_nodes:
        raise ToolSchemaExportError(f"A reference targets data rather than a schema: {reference!r}")
    return target


def _dereference(document: dict[str, JsonValue], node: dict[str, JsonValue], schema_nodes: set[int]) -> dict[str, JsonValue]:
    visited: set[str] = set()
    while "$ref" in node:
        reference = node["$ref"]
        if not isinstance(reference, str) or reference in visited:
            raise ToolSchemaExportError("A discriminator option has a cyclic or invalid alias")
        if set(node).difference(_ANNOTATION_KEYS | {"$ref"}):
            raise ToolSchemaExportError("Discriminator aliases with validation siblings are unsupported")
        visited.add(reference)
        node = _local_target(document, reference, schema_nodes)
    return node


def _discriminator_definition(node: dict[str, JsonValue]) -> _Discriminator | None:
    discriminator = node.get("discriminator")
    if discriminator is None:
        return None
    if not isinstance(discriminator, dict):
        raise ToolSchemaExportError("A discriminator must be an object")
    property_name = discriminator.get("propertyName")
    mapping = discriminator.get("mapping")
    branches = node.get("oneOf")
    if not isinstance(property_name, str) or not property_name or not isinstance(mapping, dict) or not mapping or not isinstance(branches, list) or not branches:
        raise ToolSchemaExportError("A discriminated union needs oneOf, propertyName and a local mapping")
    return _Discriminator(property_name, mapping, branches)


def _discriminator_literals(
    document: dict[str, JsonValue],
    option: dict[str, JsonValue],
    property_name: str,
    schema_nodes: set[int],
) -> list[str]:
    properties = option.get("properties")
    required = option.get("required")
    if option.get("type") != "object" or option.get("additionalProperties") is not False or not isinstance(properties, dict) or not isinstance(required, list) or property_name not in required:
        raise ToolSchemaExportError("Discriminator options must be strict objects with a required tag")
    field = properties.get(property_name)
    if not isinstance(field, dict) or "default" in field:
        raise ToolSchemaExportError("Required discriminator fields cannot have defaults")
    field = _dereference(document, field, schema_nodes)
    if "default" in field:
        raise ToolSchemaExportError("Required discriminator fields cannot have defaults")
    literals = [field["const"]] if "const" in field else field.get("enum")
    if not isinstance(literals, list) or not literals or any(not isinstance(value, str) for value in literals):
        raise ToolSchemaExportError("Discriminator tags must be nonempty string literal sets")
    return [value for value in literals if isinstance(value, str)]


def _validate_discriminator_mapping(
    document: dict[str, JsonValue],
    option: dict[str, JsonValue],
    mapping: dict[str, JsonValue],
    literals: list[str],
    values: set[str],
    schema_nodes: set[int],
) -> None:
    for value in literals:
        if value in values:
            raise ToolSchemaExportError(f"Duplicate discriminator tag: {value!r}")
        values.add(value)
        if value not in mapping:
            raise ToolSchemaExportError(f"Missing discriminator mapping: {value!r}")
        mapped = _local_target(document, mapping[value], schema_nodes)
        if _dereference(document, mapped, schema_nodes) is not option:
            raise ToolSchemaExportError(f"Discriminator mapping points to the wrong option: {value!r}")


def _validate_discriminator(document: dict[str, JsonValue], node: dict[str, JsonValue], schema_nodes: set[int]) -> None:
    discriminator = _discriminator_definition(node)
    if discriminator is None:
        return
    targets: set[int] = set()
    values: set[str] = set()
    for branch in discriminator.branches:
        if not isinstance(branch, dict):
            raise ToolSchemaExportError("Discriminator options must be schemas")
        option = _dereference(document, branch, schema_nodes)
        targets.add(id(option))
        literals = _discriminator_literals(document, option, discriminator.property_name, schema_nodes)
        _validate_discriminator_mapping(document, option, discriminator.mapping, literals, values, schema_nodes)
    if set(discriminator.mapping) != values:
        raise ToolSchemaExportError("Discriminator mapping and option literals differ")
    if len(targets) != len(discriminator.branches):
        raise ToolSchemaExportError("A discriminated union repeats an option")


def _validate_schema_collections(node: dict[str, JsonValue]) -> None:
    for keyword in _SCHEMA_MAPS:
        if keyword not in node:
            continue
        children = node[keyword]
        if not isinstance(children, dict) or any(not isinstance(child, dict) for child in children.values()):
            raise ToolSchemaExportError(f"{keyword} must contain schema objects")
    for keyword in _SCHEMA_ARRAYS:
        if keyword not in node:
            continue
        children = node[keyword]
        if not isinstance(children, list) or not children or any(not isinstance(child, dict) for child in children):
            raise ToolSchemaExportError(f"{keyword} must contain a nonempty array of schemas")


def _validate_required_fields(node: dict[str, JsonValue]) -> None:
    required = node.get("required")
    if required is None:
        return
    properties = node.get("properties")
    if not isinstance(required, list) or any(not isinstance(value, str) for value in required) or len(required) != len(set(required)) or not isinstance(properties, dict) or any(value not in properties for value in required):
        raise ToolSchemaExportError("Required fields must name distinct declared properties")


def _validate_shape(node: dict[str, JsonValue]) -> None:
    if _FORBIDDEN_REFERENCE_KEYS.intersection(node):
        raise ToolSchemaExportError("Dynamic, anchored and externally scoped references are unsupported")
    _validate_schema_collections(node)
    for keyword in _SCHEMA_SINGLE:
        if keyword in node and not isinstance(node[keyword], (dict, bool)):
            raise ToolSchemaExportError(f"Unsupported {keyword} schema shape")
    _validate_required_fields(node)


def _schema_map_pairs(source: dict[str, JsonValue], target: dict[str, JsonValue]) -> Iterator[tuple[dict[str, JsonValue], dict[str, JsonValue]]]:
    for keyword in _SCHEMA_MAPS:
        source_children = source.get(keyword)
        target_children = target.get(keyword)
        if isinstance(source_children, dict) and isinstance(target_children, dict):
            for key in sorted(source_children):
                source_child = source_children[key]
                target_child = target_children[key]
                if isinstance(source_child, dict) and isinstance(target_child, dict):
                    yield source_child, target_child


def _schema_array_pairs(source: dict[str, JsonValue], target: dict[str, JsonValue]) -> Iterator[tuple[dict[str, JsonValue], dict[str, JsonValue]]]:
    for keyword in _SCHEMA_ARRAYS:
        source_children = source.get(keyword)
        target_children = target.get(keyword)
        if isinstance(source_children, list) and isinstance(target_children, list):
            for source_child, target_child in zip(source_children, target_children, strict=True):
                if isinstance(source_child, dict) and isinstance(target_child, dict):
                    yield source_child, target_child


def _schema_single_pairs(source: dict[str, JsonValue], target: dict[str, JsonValue]) -> Iterator[tuple[dict[str, JsonValue], dict[str, JsonValue]]]:
    for keyword in _SCHEMA_SINGLE:
        source_child = source.get(keyword)
        target_child = target.get(keyword)
        if isinstance(source_child, dict) and isinstance(target_child, dict):
            yield source_child, target_child


def _rewrite_schema_node(
    source: dict[str, JsonValue],
    target: dict[str, JsonValue],
    rewrite_reference: Callable[[object], str],
) -> None:
    for keyword in ("$defs", "definitions", "$schema"):
        target.pop(keyword, None)
    if "$ref" in source:
        target["$ref"] = rewrite_reference(source["$ref"])
    discriminator = source.get("discriminator")
    if isinstance(discriminator, dict):
        mapping = discriminator.get("mapping")
        if not isinstance(mapping, dict):
            raise ToolSchemaExportError("Discriminator mapping must be an object")
        target["discriminator"] = {
            **deepcopy(discriminator),
            "mapping": {value: rewrite_reference(local_ref) for value, local_ref in sorted(mapping.items())},
        }


def _rewrite_component(
    document: dict[str, JsonValue],
    original: dict[str, JsonValue],
    schema_nodes: set[int],
    rewrite_reference: Callable[[object], str],
) -> dict[str, JsonValue]:
    transformed = deepcopy(original)
    pending = deque([(original, transformed)])
    while pending:
        source, target = pending.popleft()
        _validate_shape(source)
        _validate_discriminator(document, source, schema_nodes)
        _rewrite_schema_node(source, target, rewrite_reference)
        # Definitions are scheduled by references, not copied as nested schema maps.
        pending.extend(_schema_map_pairs(source, target))
        pending.extend(_schema_array_pairs(source, target))
        pending.extend(_schema_single_pairs(source, target))
    return transformed


def _add_schema_bundle(
    components: dict[str, JsonValue],
    document: dict[str, JsonValue],
    *,
    namespace: str,
    mode: SchemaMode,
) -> str:
    """Lift only reachable schema nodes; reference cycles never recurse through targets."""
    schema_nodes = {id(node) for node in walk_schema(document)}
    pending = deque(["#"])
    names = {"#": namespace}
    visited: set[str] = set()

    def rewrite_reference(reference: object) -> str:
        _local_target(document, reference, schema_nodes)
        if not isinstance(reference, str):
            raise ToolSchemaExportError("References must be strings")
        if reference not in names:
            # Hex-encoded complete pointers are injective, including Unicode model names.
            names[reference] = f"{namespace}Ref{reference[2:].encode('utf-8').hex()}"
            pending.append(reference)
        return _component_reference(names[reference])

    while pending:
        reference = pending.popleft()
        if reference in visited:
            continue
        visited.add(reference)
        name = names[reference]
        if name in components:
            raise ToolSchemaExportError(f"Component namespace collision: {name}")
        original = _local_target(document, reference, schema_nodes)
        transformed = _rewrite_component(document, original, schema_nodes, rewrite_reference)
        transformed[TOOL_COMPONENT_SOURCE_KEY] = {
            "mode": mode,
            "localRef": reference,
            "root": _component_reference(namespace),
        }
        components[name] = transformed
    return _component_reference(namespace)


def build_tool_contracts_document(snapshot: ToolRegistrySnapshot) -> dict[str, JsonValue]:
    """Pure export from a captured registry snapshot; no discovery, computation or file I/O.

    Quarantined plugins are already excluded from snapshot.definitions, just as in
    the runtime catalog. With no healthy definitions, only transport roots are exported.
    Fingerprints are checked against the unadapted runtime validation/serialization pair.
    """
    components: dict[str, JsonValue] = {}
    tools: list[JsonValue] = []
    identities: set[tuple[str, str]] = set()
    for code, definition in sorted(snapshot.definitions.items()):
        descriptor = definition.descriptor
        identity = (descriptor.tool_code, descriptor.contract_version)
        if code != descriptor.tool_code or identity in identities:
            raise ToolSchemaExportError(f"Duplicate or inconsistent Tool identity: {identity!r}")
        identities.add(identity)
        input_schema = generate_tool_schema(definition.input_adapter, "validation")
        output_schema = generate_tool_schema(definition.output_adapter, "serialization")
        operations = declared_operations(input_schema)
        fingerprint = schema_fingerprint(input_schema, output_schema, operations)
        if descriptor.input_schema != input_schema or descriptor.output_schema != output_schema or descriptor.schema_fingerprint != fingerprint or {policy.operation for policy in descriptor.operations} != operations:
            raise ToolSchemaExportError(f"Registry descriptor and Pydantic roots disagree: {identity!r}")
        namespace = f"ToolC{descriptor.tool_code.encode('utf-8').hex()}" f"V{descriptor.contract_version.encode('utf-8').hex()}"
        input_reference = _add_schema_bundle(components, input_schema, namespace=f"{namespace}Input", mode="validation")
        output_reference = _add_schema_bundle(components, output_schema, namespace=f"{namespace}Output", mode="serialization")
        tools.append(
            {
                "toolCode": descriptor.tool_code,
                "contractVersion": descriptor.contract_version,
                "schemaFingerprint": fingerprint,
                "componentKey": descriptor.ui.component_key,
                "uiContractVersion": descriptor.ui.ui_contract_version,
                "input": input_reference,
                "output": output_reference,
                "operations": sorted(operations),
            }
        )
    transport: dict[str, JsonValue] = {}
    for root in _TRANSPORT_ROOTS:
        document = generate_tool_schema(TypeAdapter(root.model), root.mode)
        reference = _add_schema_bundle(components, document, namespace=root.component_name, mode=root.mode)
        transport[root.role] = {
            "model": root.model.__name__,
            "schema": reference,
            "mode": root.mode,
        }
    return {
        "openapi": "3.1.0",
        "info": {"title": "LibreFolio bundled Tool contracts", "version": "1"},
        "paths": {},
        "components": {"schemas": dict(sorted(components.items()))},
        TOOL_MANIFEST_KEY: {
            "manifestVersion": 1,
            "tools": tools,
            "transport": transport,
        },
    }


def export_tool_contracts_document(*, registry_class: type[ToolPluginRegistry] = ToolPluginRegistry) -> dict[str, JsonValue]:
    """Discover schema-only bundled plugins, then export; never instantiate a Tool."""
    return build_tool_contracts_document(registry_class.get_snapshot())
