"""Structural catalog guards must survive optimization, without touching stored data.

Each witness owns a fresh interpreter and mutates only its in-memory definitions.
The loader inserts a mutation before, and a continuation marker after, one real
guard. It never replaces the application's predicate, exception, or module body.
No component builder, database fixture, server, or prompt probe is requested here.

The repository's parent conftest has a session-autouse registration-settings
fixture. That runner-level behavior is separate from these fixture-free children;
use the coordinator's approved collection boundary for a strictly DB-free run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_PREFIX = "backend.app.services.ai_export."
_RESULT_PREFIX = "STRUCTURAL_GUARD_RESULT:"
_MODES = (pytest.param(0, id="normal"), pytest.param(1, id="optimized"))


@dataclass(frozen=True)
class _GuardSite:
    identifier: str
    module: str
    subject: str
    error: str
    family: str = "length"
    expected_size: int | None = None
    anchor: str | None = None
    scope: str | None = None


# A01-A17 are the approved inventory, not source line numbers. Length is itself
# the contract under test; these are immutable definitions, never shared DB rows.
_IMPORT_LENGTH_SITES = (
    _GuardSite("A01-foundation", "components.catalog", "ALL_FOUNDATION_COMPONENTS", "components.registry.ComponentRegistryError", expected_size=67),
    _GuardSite("A02-real", "components.catalog", "ALL_REAL_COMPONENTS", "components.registry.ComponentRegistryError", expected_size=67),
    _GuardSite("A03-integrated", "components.catalog", "ALL_COMPONENTS", "components.registry.ComponentRegistryError", expected_size=67),
    _GuardSite("A04-asset-fx-fragment", "components.asset_fx_registry", "ASSET_FX_COMPONENTS", "components.asset_fx_registry.AssetFxRegistryError", expected_size=26),
    _GuardSite("A05-asset-ids", "components.asset_fx_registry", "ASSET_REAL_COMPONENT_IDS", "components.asset_fx_registry.AssetFxRegistryError", expected_size=14),
    _GuardSite("A06-fx-ids", "components.asset_fx_registry", "FX_REAL_COMPONENT_IDS", "components.asset_fx_registry.AssetFxRegistryError", expected_size=12),
    _GuardSite("A08-portfolio-broker-fragment", "components.portfolio_broker_registry", "PORTFOLIO_BROKER_COMPONENTS", "components.portfolio_broker_registry.PortfolioBrokerRegistryError", expected_size=41),
    _GuardSite("A09-portfolio-ids", "components.portfolio_broker_registry", "PORTFOLIO_REAL_COMPONENT_IDS", "components.portfolio_broker_registry.PortfolioBrokerRegistryError", expected_size=21),
    _GuardSite("A10-broker-ids", "components.portfolio_broker_registry", "BROKER_REAL_COMPONENT_IDS", "components.portfolio_broker_registry.PortfolioBrokerRegistryError", expected_size=20),
    _GuardSite("A11-public-datasets", "datasets.catalog", "PUBLIC_DATASETS", "datasets.spec.DatasetRegistryError", expected_size=8),
    _GuardSite("A13-public-analyses", "analyses.catalog", "PUBLIC_ANALYSES", "analyses.spec.AnalysisRegistryError", expected_size=11),
)
_BUILD_SITE = _GuardSite("A12-all-datasets", "datasets.catalog", "specs", "datasets.spec.DatasetRegistryError", expected_size=40, scope="build_dataset_registry")
_UNION_SITE = _GuardSite(
    "A07-asset-fx-union",
    "components.asset_fx_registry",
    "(ASSET_REAL_COMPONENT_IDS, FX_REAL_COMPONENT_IDS)",
    "components.asset_fx_registry.AssetFxRegistryError",
    family="union",
    anchor="len(set(ASSET_REAL_COMPONENT_IDS) | set(FX_REAL_COMPONENT_IDS))",
)
_POLICY_OUTER_SITE = _GuardSite(
    "A14-policy-details",
    "temporal.policy",
    "_INDICATOR_POLICY_PARAMETERS",
    "temporal.policy.IndicatorPolicyError",
    family="policy-outer",
    anchor="set(_INDICATOR_POLICY_PARAMETERS)",
)
_POLICY_ROW_SITE = _GuardSite(
    "A15-policy-rows",
    "temporal.policy",
    "_INDICATOR_POLICY_PARAMETERS",
    "temporal.policy.IndicatorPolicyError",
    family="policy-row",
    anchor="_INDICATOR_POLICY_PARAMETERS.values()",
)
_MAPPING_KEYS_SITE = _GuardSite(
    "A16-detail-sources",
    "dependencies",
    "_DETAIL_LEVEL_TO_BUCKET_DETAIL_LEVEL",
    "dependencies.DetailLevelMappingError",
    family="mapping-keys",
    anchor="set(_DETAIL_LEVEL_TO_BUCKET_DETAIL_LEVEL)",
)
_MAPPING_VALUES_SITE = _GuardSite(
    "A17-detail-destinations",
    "dependencies",
    "_DETAIL_LEVEL_TO_BUCKET_DETAIL_LEVEL",
    "dependencies.DetailLevelMappingError",
    family="mapping-values",
    anchor="set(_DETAIL_LEVEL_TO_BUCKET_DETAIL_LEVEL.values())",
)
_IMPORT_FAULTS = (
    *((site, fault) for site in _IMPORT_LENGTH_SITES for fault in ("missing", "extra")),
    *((_UNION_SITE, fault) for fault in ("cross-domain", "within-asset", "within-fx")),
    *((_POLICY_OUTER_SITE, fault) for fault in ("missing", "extra")),
    *((_POLICY_ROW_SITE, f"{fault}:{row}") for row in ("compact", "standard", "full") for fault in ("missing", "extra")),
    *((_MAPPING_KEYS_SITE, fault) for fault in ("missing", "extra")),
    *((_MAPPING_VALUES_SITE, fault) for fault in ("duplicate", "unexpected")),
)

# Deliberately plain Python: no pytest import, assertion rewriting, or correctness
# checks using assert. The target source, including any regressed assert, is
# compiled at the *actual* child's optimization level, not at the parent's level.
_CHILD_PROGRAM = r"""
import ast
import importlib
import importlib.abc
import importlib.machinery
import json
import sys

PREFIX = "backend.app.services.ai_export."
RESULT_PREFIX = "STRUCTURAL_GUARD_RESULT:"
request = json.loads(sys.argv[1])


def require(condition, message):
    if not condition:
        raise SystemExit(message)


require(sys.flags.optimize == request["optimize"], "wrong child optimization level")
require(sys.dont_write_bytecode, "child must disable bytecode writes")
require("pytest" not in sys.modules, "child must not import pytest")
require(not any(name.startswith(PREFIX) for name in sys.modules), "AI Export was not fresh")
catalog_io_guard_active = True


def forbid_external_io(event, args):
    # Audit before any application import: a catalog import/build may declare
    # models, but must never open SQLite or connect/bind a network socket.
    if catalog_io_guard_active and event in {"sqlite3.connect", "socket.connect", "socket.bind", "socket.getaddrinfo"}:
        raise SystemExit("catalog-only child attempted forbidden I/O: " + event)


sys.addaudithook(forbid_external_io)
state = {
    "loads": 0,
    "anchors": 0,
    "injections": 0,
    "continuations": 0,
    "constructor_calls": 0,
    "import_completed": False,
    "phase": "import",
}


def mutate_length(value, fault):
    require(isinstance(value, tuple), "length witness expects an assembled tuple")
    require(len(value) == site["expected_size"], "length witness did not start healthy")
    # Position is immaterial here: removing/duplicating any owned definition
    # changes cardinality. No application object or persistent row is modified.
    first, *rest = value
    result = tuple(rest) if fault == "missing" else (*value, first)
    delta = -1 if fault == "missing" else 1
    require(len(result) == len(value) + delta, "length mutation missed its target")
    return result


def mutate_union(value, fault):
    asset, fx = value
    require((len(asset), len(fx)) == (14, 12), "union witness needs healthy tuple lengths")
    require(len(set(asset) | set(fx)) == 26, "union witness did not start unique")
    asset_first, *asset_rest = asset
    fx_first, *_ = fx
    variants = {
        "cross-domain": ((fx_first, *asset_rest), fx),
        "within-asset": ((*asset[:-1], asset_first), fx),
        "within-fx": (asset, (*fx[:-1], fx_first)),
    }
    result = variants[fault]
    changed_asset, changed_fx = result
    require((len(changed_asset), len(changed_fx)) == (len(asset), len(fx)), "union mutation changed a length")
    require(len(set(changed_asset) | set(changed_fx)) == 25, "union mutation must remove exactly one unique ID")
    if fault != "cross-domain":
        require(not set(changed_asset) & set(changed_fx), "within-domain fault must remain disjoint")
    return result


def mutate_keys(value, fault):
    result = dict(value)
    key = next(iter(result))
    if fault == "missing":
        del result[key]
    else:
        require("__structural_extra__" not in result, "extra-key sentinel already exists")
        result["__structural_extra__"] = result[key]
    require(set(result) != set(value), "key mutation missed its target")
    return result


def mutate_policy_row(value, fault):
    change, row_name = fault.split(":")
    result = {key: dict(row) for key, row in value.items()}
    matches = [key for key in result if key.value == row_name]
    require(len(matches) == 1, "policy row witness is missing or ambiguous")
    (row_key,) = matches
    result[row_key] = mutate_keys(result[row_key], change)
    require(set(result) == set(value), "inner-row fault must preserve outer keys")
    require(all(result[key] == value[key] for key in value if key != row_key), "inner-row fault changed a neighbour")
    return result


def mutate_mapping_values(value, fault):
    result = dict(value)
    first, second, *_ = result
    require(len(set(value.values())) == len(value), "mapping witness did not start bijective")
    result[first] = result[second] if fault == "duplicate" else "__structural_unexpected__"
    require(set(result) == set(value), "destination fault changed source coverage")
    require(set(result.values()) != set(value.values()), "destination mutation missed its target")
    return result


def mutate(value):
    require(state["injections"] == 0, "mutation ran more than once")
    expected_phase = "build" if site["scope"] else "import"
    require(state["phase"] == expected_phase, "guard ran in the wrong phase")
    mutators = {
        "length": mutate_length,
        "union": mutate_union,
        "policy-outer": mutate_keys,
        "policy-row": mutate_policy_row,
        "mapping-keys": mutate_keys,
        "mapping-values": mutate_mapping_values,
    }
    result = mutators[site["family"]](value, request["fault"])
    state["injections"] += 1
    return result


def continuation():
    state["continuations"] += 1
    raise SystemExit("real guard allowed execution to continue after a structural fault")


def constructor_trap(*args, **kwargs):
    state["constructor_calls"] += 1
    raise SystemExit("DatasetRegistry constructor reached before rejecting invalid specs")


def guard_matches(statement, anchor):
    if isinstance(statement, ast.Assert):
        condition = statement.test
    elif isinstance(statement, ast.If):
        if not any(isinstance(node, ast.Raise) for child in statement.body for node in ast.walk(child)):
            return False
        condition = statement.test
    else:
        return False
    return any(ast.dump(node) == anchor for node in ast.walk(condition))


def instrument(tree):
    body = tree.body
    if site["scope"]:
        functions = [node for node in body if isinstance(node, ast.FunctionDef) and node.name == site["scope"]]
        require(len(functions) == 1, "builder scope is missing or ambiguous")
        (function,) = functions
        body = function.body
    anchor_source = site["anchor"] or ("len(" + site["subject"] + ")")
    anchor = ast.dump(ast.parse(anchor_source, mode="eval").body)
    matches = [(index, node) for index, node in enumerate(body) if guard_matches(node, anchor)]
    require(len(matches) == 1, "guard anchor is missing or ambiguous: " + site["identifier"])
    (match,) = matches
    index, guard = match
    state["anchors"] += 1
    original_guard = ast.dump(guard, include_attributes=True)
    before = ast.parse(site["subject"] + " = __lf_structural_mutate__(" + site["subject"] + ")").body
    after = ast.parse("__lf_structural_continue__()").body
    for inserted in (*before, *after):
        ast.copy_location(inserted, guard)
    # Insert only siblings. Earlier integration/length guards still run first;
    # the application predicate and raise are retained verbatim as AST nodes.
    body[index:index + 1] = [*before, guard, *after]
    require(ast.dump(guard, include_attributes=True) == original_guard, "instrumentation changed the guard")
    return ast.fix_missing_locations(tree)


class GuardLoader(importlib.abc.Loader):
    def __init__(self, original, fullname, origin):
        self.original = original
        self.fullname = fullname
        self.origin = origin

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        state["loads"] += 1
        source = self.original.get_source(self.fullname)
        require(isinstance(source, str), "target loader did not supply real source")
        tree = instrument(ast.parse(source, filename=self.origin))
        code = compile(tree, self.origin, "exec", dont_inherit=True, optimize=sys.flags.optimize)
        module.__dict__["__lf_structural_mutate__"] = mutate
        module.__dict__["__lf_structural_continue__"] = continuation
        exec(code, module.__dict__)


class GuardFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname != PREFIX + site["module"]:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        require(spec is not None and spec.loader is not None, "actual target module not found")
        require(spec.origin is not None, "actual target source has no origin")
        spec.loader = GuardLoader(spec.loader, fullname, spec.origin)
        return spec


def run_fault():
    sys.meta_path.insert(0, GuardFinder())
    caught = None
    try:
        # dependencies imports component submodules whose existing barrel in
        # turn imports dependencies.BuildContext. Enter through that barrel's
        # normal catalog path, rather than inventing a dependencies-first
        # startup contract. The finder is already armed for the real target.
        entry = "components.catalog" if site["module"] == "dependencies" else site["module"]
        module = importlib.import_module(PREFIX + entry)
        state["import_completed"] = True
        if site["scope"]:
            require(state["injections"] == 0, "builder fault ran during import")
            require(state["continuations"] == 0, "builder guard ran during import")
            state["phase"] = "build"
            # Installed only after a successful import, so an import-time error
            # cannot masquerade as A12 and registry duplicate validation cannot
            # masquerade as the length guard either.
            module.DatasetRegistry = constructor_trap
            module.build_dataset_registry()
    except BaseException as exc:
        caught = exc
    require(caught is not None, "corrupted definition was accepted")
    actual = type(caught).__module__ + "." + type(caught).__qualname__
    require(actual == PREFIX + site["error"], "wrong exception: " + actual + ": " + str(caught))
    require(isinstance(caught, ValueError), "structural error must remain a ValueError")
    require(state["loads"] == 1 and state["anchors"] == 1, "target must be loaded/anchored exactly once")
    require(state["injections"] == 1, "the expected fault was never injected")
    require(state["continuations"] == 0, "execution continued past the guard")
    require(state["constructor_calls"] == 0, "builder delegated structural rejection to the constructor")
    require(state["import_completed"] == bool(site["scope"]), "wrong import-versus-build failure timing")
    return {"exception": actual, **state}


def require_registry_counts(components, datasets, analyses):
    counts = (len(components), len(datasets), len(analyses))
    require(counts == (67, 40, 11), "healthy registry counts changed: " + repr(counts))


def run_healthy():
    fragment_name = request["fragment"]
    fragment = importlib.import_module(PREFIX + "components." + fragment_name + "_registry")
    # Preserve TestImportCycleSafety's existing contract: the components barrel
    # eagerly imports its catalog, but dataset/analysis catalogs remain lazy.
    require(PREFIX + "components.catalog" in sys.modules, "existing eager components catalog import disappeared")
    require(PREFIX + "datasets.catalog" not in sys.modules, "fragment eagerly imported dataset catalog")
    require(PREFIX + "analyses.catalog" not in sys.modules, "fragment eagerly imported analysis catalog")
    components = getattr(fragment, "build_" + fragment_name + "_component_registry")()
    datasets = getattr(fragment, "build_" + fragment_name + "_dataset_registry")(components)
    analyses = getattr(fragment, "build_" + fragment_name + "_analysis_registry")(datasets)
    require_registry_counts(components, datasets, analyses)
    catalog = importlib.import_module(PREFIX + "components.catalog")
    dataset_catalog = importlib.import_module(PREFIX + "datasets.catalog")
    analysis_catalog = importlib.import_module(PREFIX + "analyses.catalog")
    integrated = catalog.build_component_registry()
    all_datasets = dataset_catalog.build_dataset_registry(integrated)
    all_analyses = analysis_catalog.build_analysis_registry(all_datasets)
    require_registry_counts(integrated, all_datasets, all_analyses)
    require(integrated.canonical_order == tuple(spec.component_id for spec in catalog.ALL_FOUNDATION_COMPONENTS), "healthy canonical component order changed")
    require(len(dataset_catalog.PUBLIC_DATASETS) == 8, "healthy public dataset count changed")
    # Import both policy and mapping explicitly even if a future fragment no
    # longer imports them, so a blanket optimization ban cannot evade controls.
    importlib.import_module(PREFIX + "temporal.policy")
    importlib.import_module(PREFIX + "dependencies")
    return {"fragment": fragment_name, "counts": [67, 40, 11]}


try:
    if request["kind"] == "healthy":
        result = run_healthy()
    else:
        site = request["site"]
        result = run_fault()
finally:
    # Protect application imports/builds, not a centralized runner's optional
    # coverage tracer saving its own SQLite coverage file during interpreter exit.
    catalog_io_guard_active = False
require("pytest" not in sys.modules, "child imported pytest during the witness")
print(RESULT_PREFIX + json.dumps({"optimize": sys.flags.optimize, **result}, sort_keys=True))
"""


def _run_child(request: dict, optimize: int) -> dict:
    env = os.environ.copy()
    env.pop("PYTHONOPTIMIZE", None)
    command = [sys.executable, "-B"]
    if optimize:
        command.append("-O")
    command.extend(("-c", _CHILD_PROGRAM, json.dumps({**request, "optimize": optimize})))
    completed = subprocess.run(command, cwd=_ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert completed.returncode == 0, f"child witness failed ({request!r}, optimize={optimize}):\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    reports = [line.removeprefix(_RESULT_PREFIX) for line in completed.stdout.splitlines() if line.startswith(_RESULT_PREFIX)]
    assert len(reports) == 1, f"child did not emit exactly one completion report:\n{completed.stdout}"
    (report,) = reports
    result = json.loads(report)
    assert result["optimize"] == optimize
    return result


@pytest.mark.parametrize("optimize", _MODES)
class TestStructuralImportGuards:
    @pytest.mark.parametrize("site,fault", [pytest.param(site, fault, id=f"{site.identifier}-{fault}") for site, fault in _IMPORT_FAULTS])
    def test_import_guard_rejects_corrupted_definition(self, site: _GuardSite, fault: str, optimize: int):
        result = _run_child({"kind": "fault", "site": asdict(site), "fault": fault}, optimize)
        assert result["exception"] == _PREFIX + site.error
        assert result["phase"] == "import"
        assert result["import_completed"] is False
        assert result["injections"] == 1
        assert result["continuations"] == 0


@pytest.mark.parametrize("optimize", _MODES)
class TestDatasetRegistryBuildGuard:
    @pytest.mark.parametrize("fault", ("missing", "extra"))
    def test_build_guard_rejects_local_specs_before_constructor(self, fault: str, optimize: int):
        result = _run_child({"kind": "fault", "site": asdict(_BUILD_SITE), "fault": fault}, optimize)
        assert result["exception"] == _PREFIX + _BUILD_SITE.error
        assert result["import_completed"] is True
        assert result["phase"] == "build"
        assert result["injections"] == 1
        assert result["continuations"] == 0
        assert result["constructor_calls"] == 0


@pytest.mark.parametrize("optimize", _MODES)
class TestFreshImportCompatibility:
    @pytest.mark.parametrize("fragment", ("portfolio_broker", "asset_fx"))
    def test_healthy_fragment_and_integrated_registries(self, fragment: str, optimize: int):
        result = _run_child({"kind": "healthy", "fragment": fragment}, optimize)
        assert result["fragment"] == fragment
        assert result["counts"] == [67, 40, 11]
