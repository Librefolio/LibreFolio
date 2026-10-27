"""Tool plugins of the tests that declare settings (CP12, X5-4b), and the helpers to run them.

No product Tool declares a setting yet, and none may be added for the tests: the plugins here live in the tests only. They
are **never** a folder under ``backend/app/services/tool_plugins/``.

Two kinds of registry, both private and both unable to discover the product plugins:

* ``SettingsToolRegistry``: static, importable, holding the valid plugins below. It is the registry a spawned worker can
  re-create (the child imports this module when it unpickles the class), so the real-spawn tests use it. Never mutate it.
* ``private_registry(*plugins)``: a new registry subclass per call, for the tests that need another set of plugins (an invalid
  declaration, a ``test_only`` plugin, two plugins whose variables collide) or another mode. Its snapshot is built when the
  test first asks for it, so the test sets ``LIBREFOLIO_TEST_MODE`` first.

The worked example is a rounding Tool: ``halves`` is twice a value (5 is 2.5), the personal field ``rounding`` chooses how a
tie is rounded, and the default (``half_even``) is what the Tool did before the field existed. The instance field
``max_points`` is an integer the plugin only reports. The plugin reads both through ``self.settings`` inside ``compute``, never
in ``__init__``, and echoes what it saw: the worker is another process, so the result is the only way a test sees the values.
"""

from __future__ import annotations

import time
from dataclasses import replace
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.tools import ToolComputeItem, ToolDocumentation, ToolOperationPolicy, ToolUIDescriptor
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType, release_env_variables
from backend.app.services.plugin_settings.resolver import StoredValue, build_bound_settings
from backend.app.services.provider_registry import register_plugin
from backend.app.services.tools.base import ToolExecutionContext, ToolPlugin, ToolService
from backend.app.services.tools.registry import ToolPluginRegistry
from backend.app.services.tools.wire import encode_json
from backend.app.services.tools.worker import ToolWorkerJob

ROUNDING_CODE = "settings_rounding"
PAIR_A_CODE = "settings_pair_a"
PAIR_B_CODE = "settings_pair_b"
REQUIRED_CODE = "settings_required"
PLAIN_CODE = "settings_plain"
TESTONLY_CODE = "settings_testonly"

#: The service names the catalogue shows (``ToolService.name``).
NAMES = {
    ROUNDING_CODE: "Rounding fixture",
    PAIR_A_CODE: "Pair fixture A",
    PAIR_B_CODE: "Pair fixture B",
    REQUIRED_CODE: "Required-setting fixture",
    PLAIN_CODE: "Plain fixture",
    TESTONLY_CODE: "Test-only fixture",
}

#: A personal select; its default is what the Tool did before the field existed.
ROUNDING = PluginSettingField(
    key="rounding",
    type=SettingType.SELECT,
    scope=SettingScope.USER,
    label="Rounding of a tie (testing)",
    description="How 2.5 is rounded: to the even neighbour (2) or away from zero (3).",
    default="half_even",
    options=(SettingOption("half_even", "Half even"), SettingOption("half_up", "Half up")),
)
#: An instance-wide integer with bounds and a default.
MAX_POINTS = PluginSettingField(key="max_points", type=SettingType.INTEGER, scope=SettingScope.SYSTEM, label="Largest series (testing)", default=500, minimum=10, maximum=10_000)
#: An instance-wide select the Tool cannot work without, and with no default.
REGION = PluginSettingField(key="region", type=SettingType.SELECT, scope=SettingScope.SYSTEM, label="Region (testing)", required=True, options=(SettingOption("eu", "Europe"), SettingOption("us", "United States")))

ROUNDING_FIELDS = (ROUNDING, MAX_POINTS)
DEFAULTS = {"rounding": "half_even", "max_points": 500}


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class RoundInput(_Strict):
    operation: Literal["round"]
    halves: int


class RoundOutput(_Strict):
    tool_code: str
    rounded: int
    rounding: str
    max_points: int


class PingInput(_Strict):
    operation: Literal["ping"]


class RegionOutput(_Strict):
    region: str


class PlainOutput(_Strict):
    pong: bool
    bound: bool


def make_service(code: str, input_type: type[BaseModel], output_type: type[BaseModel], operation: str) -> ToolService:
    """One public service, complete, with the policies of the defaults."""
    return ToolService(
        tool_code=code,
        name=NAMES.get(code, f"Settings fixture {code}"),
        description="A Tool of the tests that declares settings.",
        category="testing",
        icon_key="code",
        ui=ToolUIDescriptor(kind="custom", component_key="settings-fixture-" + code.replace("_", "-"), version="1.0.0"),
        documentation=ToolDocumentation(path="user/tools/settings-fixture/", version="1.0.0"),
        operations=(ToolOperationPolicy(operation=operation),),
        input_type=input_type,
        output_type=output_type,
    )


def round_service(code: str) -> ToolService:
    return make_service(code, RoundInput, RoundOutput, "round")


class RoundingToolPlugin(ToolPlugin):
    """The worked example: rounds ``halves / 2`` with the tie rule its user chose, and reports the values it saw."""

    contract_version = "1.0.0"
    implementation_version = "1.0.0"
    settings_fields = ROUNDING_FIELDS
    services = (round_service(ROUNDING_CODE),)

    def compute(self, tool_code: str, parameters: BaseModel, context: ToolExecutionContext) -> BaseModel:
        assert isinstance(parameters, RoundInput)
        rounding = self.settings.get("rounding")
        mode = ROUND_HALF_UP if rounding == "half_up" else ROUND_HALF_EVEN
        rounded = int((Decimal(parameters.halves) / 2).quantize(Decimal(1), rounding=mode))
        return RoundOutput(tool_code=tool_code, rounded=rounded, rounding=str(rounding), max_points=int(self.settings.get("max_points")))


class PairToolPlugin(RoundingToolPlugin):
    """One plugin that bundles two services: each has its own set of values, keyed by its tool code."""

    services = (round_service(PAIR_A_CODE), round_service(PAIR_B_CODE))


class RequiredToolPlugin(ToolPlugin):
    """Cannot work without its ``region``: the core refuses a call before a worker starts when it has no value."""

    contract_version = "1.0.0"
    implementation_version = "1.0.0"
    settings_fields = (REGION,)
    services = (make_service(REQUIRED_CODE, PingInput, RegionOutput, "ping"),)

    def compute(self, tool_code: str, parameters: BaseModel, context: ToolExecutionContext) -> BaseModel:
        return RegionOutput(region=str(self.settings.get("region")))


class PlainToolPlugin(ToolPlugin):
    """Declares no field: behaves as every Tool does today. ``bound`` tells whether the core bound anything on it."""

    contract_version = "1.0.0"
    implementation_version = "1.0.0"
    services = (make_service(PLAIN_CODE, PingInput, PlainOutput, "ping"),)

    def compute(self, tool_code: str, parameters: BaseModel, context: ToolExecutionContext) -> BaseModel:
        return PlainOutput(pong=True, bound=self._lf_bound_settings is not None)


class OnlyForTestsToolPlugin(RoundingToolPlugin):
    """A Tool that exists for the tests: served only in test mode."""

    test_only = True
    services = (round_service(TESTONLY_CODE),)


def invalid_plugin(code: str, fields: object) -> type[RoundingToolPlugin]:
    """A plugin whose declaration the ``tool`` family refuses (``fields`` is whatever the test wants to declare)."""
    return type("Invalid_" + code, (RoundingToolPlugin,), {"__module__": __name__, "settings_fields": fields, "services": (round_service(code),)})


class UnusedDirectoryRegistry(ToolPluginRegistry):
    """A registry that cannot discover the product plugins (it never creates or scans the directory)."""

    @classmethod
    def _get_plugin_directory(cls) -> Path:
        return Path(__file__).with_name("_tool_settings_fixture_plugins_unused")

    @classmethod
    def _get_module_namespace(cls) -> str:
        return f"{__package__}._tool_settings_fixture_plugins_unused"


class SettingsToolRegistry(UnusedDirectoryRegistry):
    """The static registry a spawned worker re-creates: the valid plugins above, published on import. Never mutate it."""


for _plugin in (RoundingToolPlugin, PairToolPlugin, RequiredToolPlugin, PlainToolPlugin):
    register_plugin(SettingsToolRegistry)(_plugin)
SettingsToolRegistry.get_snapshot()


def private_registry(*plugins: type[ToolPlugin]) -> type[UnusedDirectoryRegistry]:
    """A new registry holding ``plugins``; its snapshot is built at the first ``get_snapshot``, in the mode then set."""

    class PrivateToolSettingsRegistry(UnusedDirectoryRegistry):
        pass

    for plugin in plugins:
        PrivateToolSettingsRegistry.register(plugin)
    return PrivateToolSettingsRegistry


def release_fixture_claims(*extra_codes: str) -> None:
    """Drop the environment-variable claims the fixture codes may have made in the ``tool`` family."""
    for code in (ROUNDING_CODE, PAIR_A_CODE, PAIR_B_CODE, REQUIRED_CODE, PLAIN_CODE, TESTONLY_CODE, *extra_codes):
        release_env_variables("tool", code)


# =============================================================================
# Values and items
# =============================================================================


def stored(value: object) -> StoredValue:
    """The content of a plain row, as the database would hold it."""
    import json  # noqa: PLC0415 — only here

    return StoredValue(value_json=json.dumps(value), secret_ciphertext=None, key_id=None, updated_at=datetime.now(UTC))


def bound_rounding(code: str = ROUNDING_CODE, *, rounding: str | None = None, max_points: int | None = None, user_id: int | None = 7) -> BoundSettings:
    """What the core binds for a call of ``code`` made for ``user_id`` who chose ``rounding``, with the instance's ``max_points``."""
    system_rows = {"max_points": stored(max_points)} if max_points is not None else {}
    user_rows = {"rounding": stored(rounding)} if rounding is not None else {}
    return build_bound_settings("tool", code, ROUNDING_FIELDS, system_rows, user_rows, user_id=user_id)


def item_for(registry: type[ToolPluginRegistry], tool_code: str, parameters: dict | None = None, correlation: str | None = None) -> ToolComputeItem:
    """A compute item carrying the versions the registry published for ``tool_code``."""
    descriptor = registry.get_definition(tool_code).descriptor
    operation = descriptor.operations[0].operation
    return ToolComputeItem(
        correlation_id=correlation or uuid4().hex,
        tool_code=tool_code,
        contract_version=descriptor.contract_version,
        implementation_version=descriptor.implementation_version,
        schema_fingerprint=descriptor.schema_fingerprint,
        parameters=parameters if parameters is not None else ({"operation": operation, "halves": 5} if operation == "round" else {"operation": operation}),
    )


def job_for(registry: type[ToolPluginRegistry], tool_code: str, parameters: dict | None = None, **changes) -> ToolWorkerJob:
    """A worker job for ``tool_code``; ``changes`` (``settings=…``) are fields of ``ToolWorkerJob``."""
    item = item_for(registry, tool_code, parameters)
    now = time.monotonic()
    job = ToolWorkerJob(
        execution_id=uuid4().hex,
        tool_code=tool_code,
        contract_version=item.contract_version,
        implementation_version=item.implementation_version,
        schema_fingerprint=item.schema_fingerprint,
        parameters=encode_json(item.parameters),
        soft_deadline=now + 50,
        hard_deadline=now + 60,
        max_parameter_bytes=131_072,
        max_result_bytes=262_144,
        max_json_depth=32,
    )
    return replace(job, **changes) if changes else job


class NeverCancelled:
    """A cancellation signal that never fires, for the in-process runs of the worker's ``_execute``."""

    @staticmethod
    def is_set() -> bool:
        return False
