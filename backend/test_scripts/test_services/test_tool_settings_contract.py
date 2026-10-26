"""The contract of a field in a Tool plugin (CP12, X5-4b): how one is declared, what the registry does with it, what the plugin sees.

The Tool family joins ``asset``, ``fx`` and ``brim`` in the plugin settings. This module is the worked example of the Tool
guide made executable (the rounding Tool of ``_tool_settings_fixtures``: a personal ``select`` and an instance ``integer``). It pins:

1. **The rules of the family** (``FAMILY_RULES["tool"]``): a call is made on behalf of a user, so a personal field reaches it; a
   Tool calls no external source, so a field may not be secret.
2. **``ToolPlugin`` inherits ``PluginSettingsMixin``**; a plugin that declares no field is called exactly as today (nothing bound).
3. **The registry validates the declaration when it builds the definition** (the Tool registry publishes its own snapshot, so
   the base class' registration checks do not run): an invalid declaration quarantines every service of that plugin with the
   new reason ``invalid_settings``, the siblings are untouched; the environment variables derive from the family ``tool`` and
   the **tool code**, one set of values per service; a ``test_only`` Tool is not part of the snapshot outside test mode.
4. **The default of a field is the behaviour before the field existed**, in the worker and on an instance nobody configured.
5. **The worker binds the values the job carries** right after it creates the plugin; ``ToolWorkerJob`` pickles with them.
6. **The executor refuses a Tool that is not configured** (a required field without a value) with ``service_unavailable``,
   without starting a worker for it.
7. **The compute route** resolves the values of the batch for the caller and hands them to the executor.

Pure: no database, no server, no process. The worker's ``_execute`` is run in this process (the spawned child is exercised by
``test_tool_settings_lifecycle.py``); the executor is given a batch whose every item stops before a worker would start. The
values are built the way the core builds them (``build_bound_settings``) from the rows the database would hold.
"""

from __future__ import annotations

import asyncio
import pickle
import time
import typing
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from backend.app.api.v1 import tools as tools_api
from backend.app.schemas.tools import ToolComputeBatchRequest, ToolDiscoveryReason, ToolPlatformPolicy
from backend.app.services.plugin_settings import resolver
from backend.app.services.plugin_settings.contract import BoundSettings, PluginSettingsMixin
from backend.app.services.plugin_settings.fields import FAMILY_RULES, FamilyRules, PluginSettingField, SettingScope, SettingsDeclarationError, SettingType, claimed_env_variables, env_name, env_variables, validate_declaration
from backend.app.services.plugin_settings.resolver import build_bound_settings, default_settings_fingerprint
from backend.app.services.tools import executor as executor_module
from backend.app.services.tools import worker as worker_module
from backend.app.services.tools.base import ToolDefinitionError, ToolPlugin
from backend.app.services.tools.catalog import effective_catalog_entries, get_tool_catalog
from backend.app.services.tools.executor import ToolExecutor
from backend.app.services.tools.registry import ToolPluginRegistry, build_tool_definition
from backend.app.services.tools.worker import ToolWorkerJob
from backend.test_scripts.test_services import _tool_settings_fixtures as fx

COLLIDE_A, COLLIDE_B = "settings_col", "settings_col_x"
SECRET_CODE, KEYS_CODE = "settings_secret", "settings_badkey"


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch):
    """Test mode (the registries serve what the suites register), no ambient variable of the fixture Tools, no claim left."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    for code in (fx.ROUNDING_CODE, fx.PAIR_A_CODE, fx.PAIR_B_CODE, fx.REQUIRED_CODE, COLLIDE_A, COLLIDE_B):
        for declared in (*fx.ROUNDING_FIELDS, fx.REGION):
            for name in {*env_variables("tool", code, declared), env_name("tool", code, declared.key)}:
                monkeypatch.delenv(name, raising=False)
                monkeypatch.delenv(name + "_FILE", raising=False)
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])
    yield
    fx.release_fixture_claims(COLLIDE_A, COLLIDE_B, SECRET_CODE, KEYS_CODE)


def _secret_field() -> PluginSettingField:
    return PluginSettingField(key="token", type=SettingType.STRING, scope=SettingScope.SYSTEM, secret=True, label="Token (testing)")


def _failure_reasons(snapshot) -> dict[str | None, str]:
    return {failure.tool_code: failure.reason for failure in snapshot.failures}


def _run_in_process(registry, tool_code: str, parameters: dict | None = None, **job_changes) -> dict:
    """The worker's ``_execute`` for one job, in this process: the frame the worker would send."""
    job = fx.job_for(registry, tool_code, parameters, **job_changes)
    return worker_module._execute(job, fx.NeverCancelled(), registry)


# =============================================================================
# 1. THE RULES OF THE FAMILY
# =============================================================================


def test_the_tool_family_delivers_personal_fields_and_forbids_secrets():
    """A call is made on behalf of a user, a Tool calls no external source: ``FamilyRules(user_scope=True, secrets=False)``."""
    assert FAMILY_RULES.get("tool") == FamilyRules(user_scope=True, secrets=False)


def test_a_personal_and_an_instance_field_are_a_valid_tool_declaration():
    """The worked example's two fields pass the checks of the ``tool`` family."""
    validate_declaration(fx.ROUNDING_FIELDS, family="tool")
    validate_declaration((fx.REGION,), family="tool")


def test_a_secret_field_is_refused_for_a_tool():
    """A Tool has nothing to keep secret: the refusal is the family's («cannot be secret»), not «unknown family»."""
    with pytest.raises(SettingsDeclarationError, match="secret"):
        validate_declaration((_secret_field(),), family="tool")
    with pytest.raises(SettingsDeclarationError, match="secret"):
        validate_declaration((PluginSettingField(key="mine", type=SettingType.STRING, scope=SettingScope.USER, secret=True, label="Mine"),), family="tool")


def test_the_other_rules_of_a_declaration_apply_to_a_tool_too():
    """The key, the tuple and the «a personal field cannot be required» rules are the common ones (guards of the family reading)."""
    with pytest.raises(SettingsDeclarationError):
        validate_declaration((PluginSettingField(key="Bad-Key", type=SettingType.STRING, scope=SettingScope.SYSTEM, label="Bad"),), family="tool")
    with pytest.raises(SettingsDeclarationError):
        validate_declaration([fx.ROUNDING], family="tool")  # type: ignore[arg-type]
    with pytest.raises(SettingsDeclarationError, match="required"):
        validate_declaration((PluginSettingField(key="mine", type=SettingType.STRING, scope=SettingScope.USER, required=True, label="Mine"),), family="tool")


def test_the_tool_registry_names_its_family():
    assert ToolPluginRegistry.settings_family() == "tool"
    assert fx.SettingsToolRegistry.settings_family() == "tool"


# =============================================================================
# 2. THE PLUGIN BASE
# =============================================================================


def test_a_tool_plugin_inherits_the_settings_mixin():
    """``settings_fields`` (empty), ``test_only`` (false), ``settings`` and ``bind_settings`` come from the mixin."""
    assert issubclass(ToolPlugin, PluginSettingsMixin)
    assert ToolPlugin.settings_fields == () and ToolPlugin.test_only is False


def test_a_tool_that_declares_no_field_sees_nothing_bound():
    """Exactly as today: no value, no secret, nothing missing, an empty fingerprint; and the core binds nothing on it."""
    plugin = fx.PlainToolPlugin()

    assert (plugin.settings.plain_values(), plugin.settings.secret_values(), plugin.settings.missing, plugin.settings.fingerprint) == ({}, frozenset(), (), "")
    frame = _run_in_process(fx.SettingsToolRegistry, fx.PLAIN_CODE)
    assert frame["status"] == "success" and frame["result"] == {"pong": True, "bound": False}


def test_the_values_bound_on_an_instance_are_the_ones_the_plugin_reads():
    plugin = fx.RoundingToolPlugin()
    plugin.bind_settings(fx.bound_rounding(rounding="half_up", max_points=700))

    assert (plugin.settings.get("rounding"), plugin.settings.get("max_points")) == ("half_up", 700)


# =============================================================================
# 3. THE REGISTRY: THE DECLARATION, THE QUARANTINE, THE TOOL CODE, test_only
# =============================================================================


def test_quarantine_has_a_reason_for_an_invalid_declaration():
    """The new discovery reason is part of the contract (``ToolDiscoveryReason``)."""
    assert "invalid_settings" in typing.get_args(ToolDiscoveryReason)


@pytest.mark.parametrize(
    ("code", "fields"),
    [
        pytest.param(SECRET_CODE, (_secret_field(),), id="a-secret-field"),
        pytest.param(KEYS_CODE, (PluginSettingField(key="Bad-Key", type=SettingType.STRING, scope=SettingScope.SYSTEM, label="Bad"),), id="a-bad-key"),
        pytest.param("settings_notuple", [fx.ROUNDING], id="not-a-tuple"),
        pytest.param("settings_userreq", (PluginSettingField(key="mine", type=SettingType.STRING, scope=SettingScope.USER, required=True, label="Mine"),), id="a-required-personal-field"),
    ],
)
def test_building_a_definition_validates_the_settings_declaration(code: str, fields: object):
    """The Tool registry bypasses the base class' registration checks, so the definition builder is where an invalid
    declaration stops, with the discovery reason ``invalid_settings``."""
    plugin = fx.invalid_plugin(code, fields)

    with pytest.raises(ToolDefinitionError) as caught:
        build_tool_definition(plugin, plugin.services[0])

    assert caught.value.reason == "invalid_settings"


def test_a_valid_declaration_builds_its_definition():
    definition = build_tool_definition(fx.RoundingToolPlugin, fx.RoundingToolPlugin.services[0])
    assert definition.descriptor.tool_code == fx.ROUNDING_CODE


@pytest.mark.parametrize("fields", [pytest.param((_secret_field(),), id="a-secret-field"), pytest.param((PluginSettingField(key="Bad-Key", type=SettingType.STRING, scope=SettingScope.SYSTEM, label="Bad"),), id="a-bad-key")])
def test_a_plugin_with_an_invalid_declaration_is_quarantined_and_its_sibling_is_untouched(fields: tuple):
    """The invalid plugin's service is out of the snapshot with ``invalid_settings``; the valid plugin registered beside it
    is published whole."""
    registry = fx.private_registry(fx.RoundingToolPlugin, fx.invalid_plugin(SECRET_CODE, fields))

    snapshot = registry.get_snapshot()

    assert SECRET_CODE not in snapshot.definitions
    assert _failure_reasons(snapshot).get(SECRET_CODE) == "invalid_settings"
    assert fx.ROUNDING_CODE in snapshot.definitions and fx.ROUNDING_CODE not in _failure_reasons(snapshot), "the sibling plugin is untouched"
    assert snapshot.definitions[fx.ROUNDING_CODE].plugin_class is fx.RoundingToolPlugin


def test_every_service_of_a_plugin_with_an_invalid_declaration_is_quarantined():
    """The declaration belongs to the plugin: its two services are out together, a plugin beside it stays."""
    pair = type("InvalidPair", (fx.PairToolPlugin,), {"__module__": fx.__name__, "settings_fields": (_secret_field(),)})
    registry = fx.private_registry(pair, fx.RoundingToolPlugin)

    snapshot = registry.get_snapshot()

    assert {fx.PAIR_A_CODE, fx.PAIR_B_CODE}.isdisjoint(snapshot.definitions)
    assert _failure_reasons(snapshot).get(fx.PAIR_A_CODE) == _failure_reasons(snapshot).get(fx.PAIR_B_CODE) == "invalid_settings"
    assert fx.ROUNDING_CODE in snapshot.definitions


@pytest.mark.asyncio
async def test_a_quarantined_tool_is_unavailable_in_the_catalogue_and_for_the_executor():
    """Shown as unavailable (diagnostics list the failure, the catalogue the code), and a compute naming it is
    ``tool_unavailable``, not ``unknown_tool``."""
    registry = fx.private_registry(fx.RoundingToolPlugin, fx.invalid_plugin(SECRET_CODE, (_secret_field(),)))
    descriptors, failures = effective_catalog_entries(ToolPlatformPolicy(), registry)
    catalog = get_tool_catalog(ToolPlatformPolicy(), registry)

    assert [d.tool_code for d in descriptors] == [fx.ROUNDING_CODE]
    assert (SECRET_CODE, "invalid_settings") in {(f.tool_code, f.reason) for f in failures}
    assert SECRET_CODE in {entry.tool_code for entry in catalog.unavailable}

    executor = ToolExecutor(ToolPlatformPolicy(), registry)
    ghost = fx.item_for(fx.SettingsToolRegistry, fx.ROUNDING_CODE, correlation="ghost").model_copy(update={"tool_code": SECRET_CODE})
    (result,) = (await executor.compute(ToolComputeBatchRequest(request_id="r1", items=[ghost]), principal_key="p1")).results
    assert result.status == "error" and result.error.code == "tool_unavailable"


def test_the_variables_of_a_tool_derive_from_the_family_and_the_tool_code():
    """``LIBREFOLIO_PLUGIN_TOOL_<TOOL_CODE>_<FIELD>``: a personal field has none, an instance field one."""
    assert env_variables("tool", fx.ROUNDING_CODE, fx.MAX_POINTS) == ("LIBREFOLIO_PLUGIN_TOOL_SETTINGS_ROUNDING_MAX_POINTS",)
    assert env_variables("tool", fx.ROUNDING_CODE, fx.ROUNDING) == ()
    assert env_variables("tool", fx.PAIR_A_CODE, fx.MAX_POINTS) != env_variables("tool", fx.PAIR_B_CODE, fx.MAX_POINTS)


def test_each_service_of_a_plugin_has_its_own_values(monkeypatch: pytest.MonkeyPatch):
    """The variable of one tool code does not reach the sibling service of the same plugin, nor another plugin's."""
    monkeypatch.setenv(env_name("tool", fx.PAIR_A_CODE, "max_points"), "700")

    a = build_bound_settings("tool", fx.PAIR_A_CODE, fx.ROUNDING_FIELDS, {}, {}, user_id=1)
    b = build_bound_settings("tool", fx.PAIR_B_CODE, fx.ROUNDING_FIELDS, {}, {}, user_id=1)
    other = build_bound_settings("tool", fx.ROUNDING_CODE, fx.ROUNDING_FIELDS, {}, {}, user_id=1)

    assert (a.get("max_points"), b.get("max_points"), other.get("max_points")) == (700, 500, 500)
    assert a.fingerprint != b.fingerprint


def test_the_registry_claims_the_variables_of_each_tool_code():
    """Each variable is claimed for ``("tool", tool_code)``: a service of a bundle claims its own, not its sibling's."""
    fx.private_registry(fx.PairToolPlugin, fx.RoundingToolPlugin).get_snapshot()
    claims = claimed_env_variables()

    for code in (fx.PAIR_A_CODE, fx.PAIR_B_CODE, fx.ROUNDING_CODE):
        assert claims.get(env_name("tool", code, "max_points")) == ("tool", code), code


def test_two_services_never_share_a_variable():
    """``settings_col`` + ``x_y`` and ``settings_col_x`` + ``y`` derive the same name: the two plugins never both publish
    (the one that cannot claim is quarantined with ``invalid_settings``), whichever order they register in."""
    one = fx.invalid_plugin(COLLIDE_A, (PluginSettingField(key="x_y", type=SettingType.INTEGER, scope=SettingScope.SYSTEM, label="XY", default=1),))
    two = fx.invalid_plugin(COLLIDE_B, (PluginSettingField(key="y", type=SettingType.INTEGER, scope=SettingScope.SYSTEM, label="Y", default=1),))
    assert env_name("tool", COLLIDE_A, "x_y") == env_name("tool", COLLIDE_B, "y"), "barrier: the names collide"

    snapshot = fx.private_registry(one, two).get_snapshot()

    published = {COLLIDE_A, COLLIDE_B} & set(snapshot.definitions)
    assert len(published) <= 1, f"both published: {sorted(published)} would read one variable"
    assert {code: reason for code, reason in _failure_reasons(snapshot).items() if code in (COLLIDE_A, COLLIDE_B)} == dict.fromkeys({COLLIDE_A, COLLIDE_B} - published, "invalid_settings")


def test_a_test_only_tool_is_not_part_of_the_snapshot_outside_test_mode(monkeypatch: pytest.MonkeyPatch):
    """Not listed, not served, and not a failure either (X-R44): the lists, the lookups, the snapshot and the catalogue."""
    monkeypatch.delenv("LIBREFOLIO_TEST_MODE", raising=False)
    registry = fx.private_registry(fx.RoundingToolPlugin, fx.OnlyForTestsToolPlugin)

    snapshot = registry.get_snapshot()
    descriptors, failures = effective_catalog_entries(ToolPlatformPolicy(), registry)

    assert fx.ROUNDING_CODE in snapshot.definitions, "barrier: the registry serves the other Tool"
    assert fx.TESTONLY_CODE not in snapshot.definitions
    assert fx.TESTONLY_CODE not in {d.tool_code for d in descriptors} | {f.tool_code for f in failures} | {f.tool_code for f in snapshot.failures}
    assert registry.get_definition(fx.TESTONLY_CODE) is None
    assert registry.get_plugin(fx.TESTONLY_CODE) is None and registry.get_plugin_instance(fx.TESTONLY_CODE) is None
    assert fx.TESTONLY_CODE not in registry.list_plugin_codes()


def test_a_test_only_tool_is_served_in_test_mode():
    registry = fx.private_registry(fx.RoundingToolPlugin, fx.OnlyForTestsToolPlugin)

    snapshot = registry.get_snapshot()

    assert {fx.ROUNDING_CODE, fx.TESTONLY_CODE} <= set(snapshot.definitions)
    assert registry.get_plugin(fx.TESTONLY_CODE) is fx.OnlyForTestsToolPlugin
    assert fx.TESTONLY_CODE in registry.list_plugin_codes()
    assert isinstance(registry.get_plugin_instance(fx.TESTONLY_CODE), fx.OnlyForTestsToolPlugin)


# =============================================================================
# 4. THE DEFAULT IS THE OLD BEHAVIOUR
# =============================================================================


def test_an_instance_nobody_configured_reads_the_defaults_and_keeps_the_old_output():
    """Half of 5 is a tie: rounded to the even neighbour, 2, as the Tool always did."""
    plugin = fx.RoundingToolPlugin()

    assert (plugin.settings.get("rounding"), plugin.settings.get("max_points")) == ("half_even", 500)
    frame = _run_in_process(fx.SettingsToolRegistry, fx.ROUNDING_CODE)
    assert frame["status"] == "success"
    assert frame["result"] == {"tool_code": fx.ROUNDING_CODE, "rounded": 2, "rounding": "half_even", "max_points": 500}


def test_a_user_who_chose_nothing_gets_the_defaults_through_the_core():
    bound = fx.bound_rounding()

    assert (bound.get("rounding"), bound.get("max_points"), bound.missing) == ("half_even", 500, ())
    assert bound.fingerprint == default_settings_fingerprint(fx.ROUNDING_FIELDS)


# =============================================================================
# 5. THE WORKER BINDS WHAT THE JOB CARRIES
# =============================================================================


def test_the_job_carries_settings_and_they_default_to_none():
    """``ToolWorkerJob.settings`` is a field with a default: a job built without it is the job of today."""
    assert fx.job_for(fx.SettingsToolRegistry, fx.ROUNDING_CODE).settings is None
    bound = fx.bound_rounding(rounding="half_up", max_points=700)
    assert fx.job_for(fx.SettingsToolRegistry, fx.ROUNDING_CODE, settings=bound).settings is bound


def test_the_plugin_sees_the_values_the_job_carries():
    """The same tie, the other rule: 3. The instance's integer reaches the plugin too."""
    bound = fx.bound_rounding(rounding="half_up", max_points=700)

    frame = _run_in_process(fx.SettingsToolRegistry, fx.ROUNDING_CODE, settings=bound)

    assert frame["status"] == "success"
    assert frame["result"] == {"tool_code": fx.ROUNDING_CODE, "rounded": 3, "rounding": "half_up", "max_points": 700}


def test_the_plugin_sees_the_defaults_when_the_job_carries_none():
    frame = _run_in_process(fx.SettingsToolRegistry, fx.ROUNDING_CODE)

    assert frame["result"] == {"tool_code": fx.ROUNDING_CODE, "rounded": 2, "rounding": "half_even", "max_points": 500}


def test_a_plugin_is_bound_before_it_computes_and_not_in_its_constructor(monkeypatch: pytest.MonkeyPatch):
    """«Right after ``plugin = definition.plugin_class()``»: the values are on the instance when ``compute`` runs."""
    seen: list[BoundSettings | None] = []
    original = fx.RoundingToolPlugin.compute

    def spy(self, tool_code, parameters, context):
        seen.append(self._lf_bound_settings)
        return original(self, tool_code, parameters, context)

    monkeypatch.setattr(fx.RoundingToolPlugin, "compute", spy)
    bound = fx.bound_rounding(rounding="half_up")

    _run_in_process(fx.SettingsToolRegistry, fx.ROUNDING_CODE, settings=bound)

    assert seen == [bound]


def test_each_service_of_a_bundle_gets_the_values_of_its_own_job():
    """One plugin, two services, two jobs: the values follow the job, not the class."""
    up = fx.bound_rounding(fx.PAIR_A_CODE, rounding="half_up")

    a = _run_in_process(fx.SettingsToolRegistry, fx.PAIR_A_CODE, settings=up)
    b = _run_in_process(fx.SettingsToolRegistry, fx.PAIR_B_CODE)

    assert (a["result"]["tool_code"], a["result"]["rounded"]) == (fx.PAIR_A_CODE, 3)
    assert (b["result"]["tool_code"], b["result"]["rounded"]) == (fx.PAIR_B_CODE, 2)


def test_a_job_with_settings_pickles_to_the_spawn_child():
    """The job crosses the spawn boundary pickled, like BRIM's: values and fingerprint arrive, the ``repr`` shows no secret."""
    bound = fx.bound_rounding(rounding="half_up", max_points=700)
    job = fx.job_for(fx.SettingsToolRegistry, fx.ROUNDING_CODE, settings=bound)

    again = pickle.loads(pickle.dumps(job))

    assert isinstance(again, ToolWorkerJob) and again.execution_id == job.execution_id
    assert isinstance(again.settings, BoundSettings)
    assert (again.settings.plain_values(), again.settings.missing, again.settings.fingerprint) == (bound.plain_values(), bound.missing, bound.fingerprint)
    assert (again.settings.get("rounding"), again.settings.get("max_points")) == ("half_up", 700)


# =============================================================================
# 6. A TOOL THAT IS NOT CONFIGURED IS REFUSED BEFORE A WORKER STARTS
# =============================================================================


@pytest.mark.asyncio
async def test_a_tool_with_a_required_field_without_a_value_is_unavailable_and_starts_no_worker(monkeypatch: pytest.MonkeyPatch):
    """``service_unavailable``, not retryable, no execution id: the plugin never ran, and no process was started."""
    started: list[object] = []
    monkeypatch.setattr(executor_module, "_run_owned_job", lambda *args, **kwargs: started.append(args) or pytest.fail("a worker was started"))
    unconfigured = BoundSettings.unbound((fx.REGION,))
    assert unconfigured.missing == ("region",), "barrier: the required field has no value"
    executor = ToolExecutor(ToolPlatformPolicy(), fx.SettingsToolRegistry)
    batch = ToolComputeBatchRequest(request_id="r1", items=[fx.item_for(fx.SettingsToolRegistry, fx.REQUIRED_CODE, correlation="needs-region")])

    response = await executor.compute(batch, principal_key="p1", settings={fx.REQUIRED_CODE: unconfigured})

    (result,) = response.results
    assert (result.correlation_id, result.status, result.error.code, result.error.retryable) == ("needs-region", "error", "service_unavailable", False)
    assert result.execution_id is None and started == []
    assert executor.snapshot().pending == 0, "the admission credit of the refused item is returned"


@pytest.mark.asyncio
async def test_compute_without_settings_is_the_compute_of_today():
    """``settings`` is optional: a batch whose only item is unknown fails exactly as before, with or without the argument."""
    executor = ToolExecutor(ToolPlatformPolicy(), fx.SettingsToolRegistry)
    ghost = fx.item_for(fx.SettingsToolRegistry, fx.ROUNDING_CODE, correlation="ghost").model_copy(update={"tool_code": "settings_nowhere"})
    batch = ToolComputeBatchRequest(request_id="r1", items=[ghost])

    plain = await executor.compute(batch, principal_key="p1")
    with_none = await executor.compute(batch, principal_key="p2", settings=None)
    with_empty = await executor.compute(batch, principal_key="p3", settings={})

    for response in (plain, with_none, with_empty):
        assert [(r.status, r.error.code) for r in response.results] == [("error", "unknown_tool")]


# =============================================================================
# 7. THE COMPUTE ROUTE RESOLVES THE VALUES OF THE CALLER
# =============================================================================


@pytest.mark.asyncio
async def test_the_compute_route_resolves_the_batch_settings_for_the_caller_and_hands_them_to_the_executor(monkeypatch: pytest.MonkeyPatch):
    """``compute_tools`` calls ``bound_settings_for_batch(batch, user_id=current_user.id)`` and passes the mapping it gets as
    ``settings=`` to ``get_tool_executor().compute``. (Assumes the route imports the function by name, as it does
    ``get_tool_executor``.)"""
    resolved = {fx.ROUNDING_CODE: fx.bound_rounding(rounding="half_up", user_id=42)}
    answer = SimpleNamespace(name="the-response")
    asked: list[tuple] = []
    computed: list[dict] = []

    async def resolve(batch, **kwargs):
        asked.append((batch, kwargs))
        return resolved

    class StubExecutor:
        policy = ToolPlatformPolicy()

        def batch_request_timeout_ms(self, batch) -> int:
            return 20_000

        async def compute(self, batch, **kwargs):
            computed.append({"batch": batch, **kwargs})
            return answer

    monkeypatch.setattr(tools_api, "bound_settings_for_batch", resolve)
    monkeypatch.setattr(tools_api, "get_tool_executor", lambda: StubExecutor())
    batch = ToolComputeBatchRequest(request_id="r1", items=[fx.item_for(fx.SettingsToolRegistry, fx.ROUNDING_CODE)])

    async def never_disconnects():
        await asyncio.Event().wait()

    async with asyncio.timeout(60) as timeout:
        scope = {"type": "http", "method": "POST", "path": "/api/v1/tools/compute", "headers": [], "query_string": b""}
        request = tools_api._ToolRequest(scope, never_disconnects, policy=StubExecutor.policy, started=time.monotonic(), timeout=timeout)
        assert isinstance(request, Request)
        response = await tools_api.compute_tools(batch, request, SimpleNamespace(id=42))

    assert response is answer
    assert asked == [(batch, {"user_id": 42})]
    assert len(computed) == 1 and computed[0]["settings"] is resolved and computed[0]["principal_key"] == "42"
