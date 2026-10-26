"""Transactional Tool specialization of the shared plugin registry."""

from __future__ import annotations

import inspect
import re
import sys
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar

from pydantic import TypeAdapter, ValidationError

from backend.app.logging_config import get_logger
from backend.app.schemas.tools import ToolDescriptor, ToolDiscoveryFailure, ToolDiscoveryReason
from backend.app.services.plugin_settings.fields import SettingsDeclarationError, claim_env_variables, validate_declaration
from backend.app.services.provider_registry import PLUGIN_MODULE_NAME, AbstractPluginRegistry
from backend.app.services.tools.base import ToolDefinitionError, ToolPlugin, ToolService
from backend.app.services.tools.schema import declared_operations, generate_tool_schema, require_roundtrip_output, schema_fingerprint
from backend.app.services.tools.wire import encode_json

logger = get_logger(__name__)
_CODE_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,63}")
_MODULE_STEM_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,128}")
_MAX_SERVICES_PER_PLUGIN = 16


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    plugin_class: type[ToolPlugin]
    service: ToolService
    input_adapter: TypeAdapter
    output_adapter: TypeAdapter
    descriptor: ToolDescriptor


@dataclass(frozen=True, slots=True)
class ToolRegistrySnapshot:
    definitions: Mapping[str, ToolDefinition]
    failures: tuple[ToolDiscoveryFailure, ...]


def _claim_code(service: object) -> str | None:
    if not isinstance(service, ToolService):
        return None
    value = service.tool_code
    return value if isinstance(value, str) and _CODE_PATTERN.fullmatch(value) else None


def _claimed_services(plugin_class: object) -> tuple[object, ...]:
    if not isinstance(plugin_class, type):
        return (None,)
    value = inspect.getattr_static(plugin_class, "services", None)
    if not isinstance(value, tuple) or not 1 <= len(value) <= _MAX_SERVICES_PER_PLUGIN:
        return (None,)
    return value


def _safe_filename(module_name: str, namespace: str) -> str:
    """The plugin's file within its family folder: ``<name>/plugin.py`` for a folder, ``<stem>.py`` for a module."""
    relative = module_name[len(namespace) + 1 :] if module_name.startswith(namespace + ".") else module_name.rsplit(".", 1)[-1]
    folder, _, leaf = relative.rpartition(".")
    if leaf == PLUGIN_MODULE_NAME and folder and "." not in folder and _MODULE_STEM_PATTERN.fullmatch(folder):
        return f"{folder}/{PLUGIN_MODULE_NAME}.py"
    stem = relative.rsplit(".", 1)[-1]
    return f"{stem}.py" if _MODULE_STEM_PATTERN.fullmatch(stem) else "plugin.py"


def _registration_module(namespace: str) -> str:
    frame = inspect.currentframe()
    caller_module: str | None = None
    try:
        while frame is not None:
            module_name = frame.f_globals.get("__name__")
            if isinstance(module_name, str) and module_name not in (__name__, AbstractPluginRegistry.__module__):
                if caller_module is None:
                    caller_module = module_name
                if frame.f_code.co_name == "<module>" and module_name.startswith(namespace + "."):
                    return module_name
            frame = frame.f_back
    finally:
        del frame
    if caller_module is not None:
        return caller_module
    raise RuntimeError("Tool registration has no identifiable source module")


def _validate_plugin_class(plugin_class: object) -> type[ToolPlugin]:
    if not isinstance(plugin_class, type) or not issubclass(plugin_class, ToolPlugin) or inspect.isabstract(plugin_class):
        raise ToolDefinitionError("invalid_plugin")
    if inspect.iscoroutinefunction(plugin_class.compute):
        raise ToolDefinitionError("invalid_plugin")
    try:
        inspect.signature(plugin_class).bind()
    except TypeError as exc:
        raise ToolDefinitionError("invalid_plugin") from exc
    return plugin_class


def build_tool_definition(plugin_class: type[ToolPlugin], service: ToolService) -> ToolDefinition:
    plugin_class = _validate_plugin_class(plugin_class)
    if not isinstance(service, ToolService):
        raise ToolDefinitionError("invalid_descriptor")
    if _claim_code(service) is None:
        raise ToolDefinitionError("invalid_code")
    try:
        input_adapter = service.input_adapter()
        input_schema = generate_tool_schema(input_adapter, "validation")
        output_adapter = service.output_adapter()
        require_roundtrip_output(output_adapter)
        output_schema = generate_tool_schema(output_adapter, "serialization")
    except ToolDefinitionError:
        raise
    except Exception as exc:
        # One malformed bundled service must not hide sibling services.
        raise ToolDefinitionError("invalid_schema") from exc
    fields = getattr(plugin_class, "settings_fields", ())
    if fields:
        # This registry builds its own definitions, so the checks of the shared ``register`` (the declaration and the claim of the
        # environment variables) are made here, per tool code: an invalid declaration quarantines that service only.
        try:
            validate_declaration(fields, family="tool")
            claim_env_variables("tool", service.tool_code, fields)
        except SettingsDeclarationError as exc:
            raise ToolDefinitionError("invalid_settings") from exc
    operations = declared_operations(input_schema)
    if not service.operations or {policy.operation for policy in service.operations} != operations:
        raise ToolDefinitionError("invalid_operation_policy")
    try:
        descriptor = ToolDescriptor(
            tool_code=service.tool_code,
            contract_version=plugin_class.contract_version,
            implementation_version=plugin_class.implementation_version,
            schema_fingerprint=schema_fingerprint(input_schema, output_schema, operations),
            name=service.name,
            description=service.description,
            name_i18n_key=service.name_i18n_key,
            description_i18n_key=service.description_i18n_key,
            category=service.category,
            icon_key=service.icon_key,
            ui=service.ui,
            documentation=service.documentation,
            input_schema=input_schema,
            output_schema=output_schema,
            operations=[policy.model_copy(deep=True) for policy in service.operations],
        )
        encode_json(descriptor.model_dump(mode="json"), max_depth=64)
    except (AttributeError, TypeError, ValueError, ValidationError) as exc:
        raise ToolDefinitionError("invalid_descriptor") from exc
    return ToolDefinition(plugin_class, service, input_adapter, output_adapter, descriptor)


def _resolve_claim(
    claim: object,
    service: object,
    module_name: str,
    failed_modules: set[str],
    collisions: set[str],
    namespace: str,
) -> ToolDefinition | ToolDiscoveryFailure:
    code = _claim_code(service)
    reason: ToolDiscoveryReason
    if code in collisions:
        reason = "duplicate_code"
    elif module_name in failed_modules:
        reason = "import_failed"
    elif not isinstance(claim, type) or not issubclass(claim, ToolPlugin):
        reason = "invalid_plugin"
    elif service is None:
        reason = "invalid_plugin"
    elif code is None:
        reason = "invalid_code"
    else:
        try:
            return build_tool_definition(claim, service)
        except ToolDefinitionError as exc:
            reason = exc.reason
        except Exception:
            reason = "invalid_descriptor"
    return ToolDiscoveryFailure(tool_code=code, filename=_safe_filename(module_name, namespace), reason=reason)


class ToolPluginRegistry(AbstractPluginRegistry):
    _claims: ClassVar[dict[str, list[object]]] = {}
    _lock: ClassVar[threading.RLock] = threading.RLock()
    _snapshot: ClassVar[ToolRegistrySnapshot | None] = None
    _discovering: ClassVar[bool] = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._claims = {}
        cls._lock = threading.RLock()
        cls._snapshot = None
        cls._discovering = False

    @classmethod
    def _get_plugin_folder(cls) -> str:
        return "tool_plugins"

    @classmethod
    def _get_plugin_code_attr(cls) -> str:
        return "services"

    @classmethod
    def settings_family(cls) -> str | None:
        return "tool"

    @classmethod
    def register(cls, plugin_class: type) -> None:
        with cls._lock:
            if cls._snapshot is not None:
                if any(claim is plugin_class for claims in cls._claims.values() for claim in claims):
                    return
                raise RuntimeError("Tool registration is closed after discovery")
            if any(claim is plugin_class for claims in cls._claims.values() for claim in claims):
                return
            module_name = _registration_module(cls._get_module_namespace())
            cls._claims.setdefault(module_name, []).append(plugin_class)

    @classmethod
    def auto_discover(cls) -> None:
        with cls._lock:
            if cls._snapshot is not None:
                return
            if cls._discovering:
                raise RuntimeError("Tool discovery cannot observe partial registration")
            cls._discovering = True
            try:
                super().auto_discover()
                cls._publish_snapshot()
            finally:
                cls._discovering = False

    @classmethod
    def _publish_snapshot(cls) -> None:
        failed_modules = {failure.module_name for failure in cls._discovery_errors}
        module_namespace = cls._get_module_namespace()
        namespace = module_namespace + "."
        failed_modules.update(module_name for module_name in cls._claims if module_name.startswith(namespace) and module_name not in sys.modules)
        failures = [ToolDiscoveryFailure(tool_code=None, filename=_safe_filename(module_name, module_namespace), reason="import_failed") for module_name in sorted(failed_modules)]
        expanded: list[tuple[str, object, object]] = []
        by_code: dict[str, list[tuple[object, object]]] = {}
        for module_name, claims in sorted(cls._claims.items()):
            for claim in claims:
                for service in _claimed_services(claim):
                    expanded.append((module_name, claim, service))
                    code = _claim_code(service)
                    if code is not None:
                        by_code.setdefault(code, []).append((claim, service))
        collisions = {code for code, claims in by_code.items() if len(claims) > 1}
        definitions: dict[str, ToolDefinition] = {}
        for module_name, claim, service in expanded:
            entry = _resolve_claim(claim, service, module_name, failed_modules, collisions, module_namespace)
            if isinstance(entry, ToolDefinition):
                if cls._withheld(entry.plugin_class):
                    # X-R44: a plugin that exists for the tests is not served outside test mode (the snapshot is built once).
                    continue
                definitions[entry.descriptor.tool_code] = entry
            else:
                failures.append(entry)
                logger.warning("Tool service quarantined", tool_code=entry.tool_code, filename=entry.filename, reason=entry.reason)
        ordered = dict(sorted(definitions.items()))
        cls._snapshot = ToolRegistrySnapshot(MappingProxyType(ordered), tuple(failures))
        setattr(cls, cls._get_storage_attribute(), {code: definition.plugin_class for code, definition in ordered.items()})

    @classmethod
    def get_snapshot(cls) -> ToolRegistrySnapshot:
        cls.auto_discover()
        with cls._lock:
            if cls._snapshot is None:
                raise RuntimeError("Tool discovery did not publish a snapshot")
            return cls._snapshot

    @classmethod
    def get_definition(cls, code: str) -> ToolDefinition | None:
        return cls.get_snapshot().definitions.get(code)

    @classmethod
    def get_plugin_instance(cls, code: str, **kwargs):
        definition = cls.get_definition(code)
        if definition is None:
            return None
        return definition.plugin_class(**kwargs)
