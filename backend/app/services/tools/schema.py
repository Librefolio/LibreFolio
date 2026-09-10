"""Publishable Tool schema profile derived exclusively from Pydantic models."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from typing import Literal

from pydantic import BaseModel, JsonValue, TypeAdapter

from backend.app.services.tools.base import ToolDefinitionError
from backend.app.services.tools.wire import encode_json

_SCHEMA_DOCUMENT = TypeAdapter(dict[str, JsonValue])
_SCHEMA_MAPS = ("$defs", "definitions", "properties", "patternProperties", "dependentSchemas")
_SCHEMA_ARRAYS = ("allOf", "anyOf", "oneOf", "prefixItems")
_SCHEMA_SINGLE = ("items", "additionalProperties", "unevaluatedProperties", "contains", "propertyNames", "not", "if", "then", "else")


def walk_schema(schema: dict[str, JsonValue]) -> Iterator[dict[str, JsonValue]]:
    pending = [schema]
    while pending:
        node = pending.pop()
        yield node
        for keyword in _SCHEMA_MAPS:
            children = node.get(keyword)
            if isinstance(children, dict):
                pending.extend(child for child in children.values() if isinstance(child, dict))
        for keyword in _SCHEMA_ARRAYS:
            children = node.get(keyword)
            if isinstance(children, list):
                pending.extend(child for child in children if isinstance(child, dict))
        for keyword in _SCHEMA_SINGLE:
            child = node.get(keyword)
            if isinstance(child, dict):
                pending.append(child)


def resolve_schema_reference(document: dict[str, JsonValue], reference: str) -> dict[str, JsonValue]:
    if reference == "#":
        return document
    if not reference.startswith("#/"):
        raise ToolDefinitionError("invalid_schema")
    node: JsonValue = document
    for escaped_token in reference[2:].split("/"):
        token = escaped_token.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or token not in node:
            raise ToolDefinitionError("invalid_schema")
        node = node[token]
    if not isinstance(node, dict):
        raise ToolDefinitionError("invalid_schema")
    return node


def root_models(document: dict[str, JsonValue]) -> Iterator[dict[str, JsonValue]]:
    pending = [document]
    visited: set[int] = set()
    while pending:
        node = pending.pop()
        if id(node) in visited:
            raise ToolDefinitionError("invalid_schema")
        visited.add(id(node))
        reference = node.get("$ref")
        if isinstance(reference, str):
            pending.append(resolve_schema_reference(document, reference))
            continue
        branches = node.get("oneOf", node.get("anyOf"))
        if isinstance(branches, list):
            discriminator = node.get("discriminator")
            if not isinstance(discriminator, dict) or not isinstance(discriminator.get("propertyName"), str) or not discriminator["propertyName"]:
                raise ToolDefinitionError("invalid_schema")
            if not branches or any(not isinstance(branch, dict) for branch in branches):
                raise ToolDefinitionError("invalid_schema")
            pending.extend(branch for branch in branches if isinstance(branch, dict))
            continue
        if node.get("type") != "object" or node.get("additionalProperties") is not False:
            raise ToolDefinitionError("invalid_schema")
        yield node


def _require_strict_models(adapter: TypeAdapter, mode: Literal["validation", "serialization"]) -> None:
    pending: list[object] = [adapter.core_schema]
    visited: set[int] = set()
    found_model = False
    while pending:
        node = pending.pop()
        if isinstance(node, (dict, list)):
            if id(node) in visited:
                continue
            visited.add(id(node))
        if isinstance(node, dict):
            if node.get("type") == "model":
                model_class = node.get("cls")
                config = node.get("config", {})
                if not isinstance(model_class, type) or not issubclass(model_class, BaseModel) or not isinstance(config, dict) or config.get("extra_fields_behavior") != "forbid":
                    raise ToolDefinitionError("invalid_input_model" if mode == "validation" else "invalid_output_model")
                found_model = True
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    if not found_model:
        raise ToolDefinitionError("invalid_input_model" if mode == "validation" else "invalid_output_model")


def generate_tool_schema(adapter: TypeAdapter, mode: Literal["validation", "serialization"]) -> dict[str, JsonValue]:
    _require_strict_models(adapter, mode)
    schema = _SCHEMA_DOCUMENT.validate_python(adapter.json_schema(mode=mode), strict=True)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    encode_json(schema, max_depth=64)
    for node in walk_schema(schema):
        if "$dynamicRef" in node or "$recursiveRef" in node or "$id" in node:
            raise ToolDefinitionError("invalid_schema")
        reference = node.get("$ref")
        if reference is not None:
            if not isinstance(reference, str):
                raise ToolDefinitionError("invalid_schema")
            resolve_schema_reference(schema, reference)
        discriminator = node.get("discriminator")
        if isinstance(discriminator, dict):
            mapping = discriminator.get("mapping", {})
            if not isinstance(mapping, dict):
                raise ToolDefinitionError("invalid_schema")
            for target in mapping.values():
                if not isinstance(target, str):
                    raise ToolDefinitionError("invalid_schema")
                resolve_schema_reference(schema, target)
    list(root_models(schema))
    return schema


def declared_operations(schema: dict[str, JsonValue]) -> frozenset[str]:
    operations: set[str] = set()
    for model in root_models(schema):
        required = model.get("required")
        properties = model.get("properties")
        if not isinstance(required, list) or "operation" not in required or not isinstance(properties, dict):
            raise ToolDefinitionError("invalid_operation_policy")
        operation = properties.get("operation")
        if not isinstance(operation, dict):
            raise ToolDefinitionError("invalid_operation_policy")
        reference = operation.get("$ref")
        if isinstance(reference, str):
            operation = resolve_schema_reference(schema, reference)
        if "default" in operation:
            raise ToolDefinitionError("invalid_operation_policy")
        values = [operation["const"]] if "const" in operation else operation.get("enum")
        if not isinstance(values, list) or not values or any(not isinstance(value, str) for value in values):
            raise ToolDefinitionError("invalid_operation_policy")
        operations.update(value for value in values if isinstance(value, str))
    return frozenset(operations)


def schema_fingerprint(input_schema: dict[str, JsonValue], output_schema: dict[str, JsonValue], operations: frozenset[str]) -> str:
    document = {"input_schema": input_schema, "output_schema": output_schema, "operations": sorted(operations)}
    return hashlib.sha256(encode_json(document, max_depth=64)).hexdigest()
