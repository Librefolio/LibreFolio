"""Contract tests for the test-runner CLI plumbing itself.

The runner has no notion of "a test unit" other than the command an action
builds and hands to :func:`_common.run_command`. These tests pin three
properties of that plumbing directly — not through ``TEST_REGISTRY`` metadata,
which only describes intent, not behaviour:

1. ``utils_coverage_js_adapter`` turns ``test_names`` into pytest ``-k``
   semantics (``"a or b"``) in the *actual* command it launches.
2. ``run_test_from_registry`` forwards that same selector end to end for a
   standard backend action.
3. ``scripts/coverage_js.py`` still compiles and still defines the functions
   the adapter action depends on — checked by ``compile()`` on the source
   text, never by importing the module or invoking a subprocess/.pyc.

A fourth test pins the missing-path preflight in ``_common.run_command``: it
monkeypatches ``subprocess.run`` to fail loudly if invoked, then proves a
pytest command built from a path that does not exist on disk is rejected
before any process is spawned. It is constructed so it fails without that
preflight — the monkeypatch turns any fallthrough into ``subprocess.run``
into an immediate, loud test failure — and it now proves the preflight is in
place and working. Keep the assertion exactly this strict so a regression
that removes the preflight is caught immediately.

The frontend-listing regressions also pin sequence-valued registry metadata:
only existing ``.spec.ts`` entries are parsed, while frontend unit-test paths
are ignored without crashing the listing command.

The junit attribution regressions pin how the consolidated backend pass reads its
report back into per-unit verdicts (``_consolidate_backend._junit_results``):
a directory unit owns a case only on a ``/`` boundary, the deepest directory
containing a case wins whatever the order of the units, and a file unit keeps
its own cases. Pure: a hand-written junit report in ``tmp_path``.

The H-21 regressions pin how a single action seeds its category first. A single
action (``dev.py test … api brim``) runs against the lane's database as it is:
after a run that recreated it empty (``services``, ``db create``), every unit
signing in as ``e2e_test_admin``/``e2e_test_user`` failed with 401. A category may
declare ``setup_needed`` next to its ``setup`` (``_common.make_category``): a
no-argument callable returning why the setup must run before one action, or None.
``_common.ensure_category_setup`` asks it only while the setup has not run in this
invocation, prints one ``print_info`` line naming the category and the reason, then
runs the setup through ``run_category_setup``; a check that raises seeds anyway and
says it could not check. ``_cli.run_test_from_registry`` calls it before a single
action — never for ``all``, never for ``--list`` — and refuses the action when the
setup fails. The ``api`` category declares ``_backend_api._api_fixture_users_missing``:
it opens the lane's SQLite file read-only and names the ``API_FIXTURE_USERS`` it
lacks (no file, no ``users`` table and a file that is not a database are reasons
too), and it never writes. Pure: throwaway categories through
``monkeypatch.setitem``, a private ``_SETUP_DONE``, SQLite files built with the
stdlib under ``tmp_path``; ``populate_mock_data.py`` is parsed as source text,
never imported.

The H-23 regressions pin how one action run on its own keeps the lane's database.
``dev.py test … services client-address``, a ``pure`` unit that opens no database,
still ran the ``services`` category's exclusive setup (``_services_setup`` →
``db_create``), which recreates that database empty: two workstreams lost their
fixture users that way. ``_inventory.declared_isolation(category, action)`` is the
one definition of the class the catalogue declares for an action, read from
``TEST_REGISTRY`` when asked: ``write-global`` when the entry has an
``exclusive_because`` (it wins over a declared ``isolation``), else the entry's
``isolation``, else the category's ``default_isolation``, else None, which is also
the answer for an unknown category or action. ``build_inventory`` classifies every
unit through it: ``classify(engine, path, declared_isolation(category, action))``.
``_cli._run_exclusive_setups`` leaves a category's exclusive setup unrun for one
action other than ``all`` that the catalogue declares ``pure``, and says so on one
``print_info`` line naming the category and the action. The whole category, ``all``,
an action declared anything else and an action with no declared class at all
(``classify()``'s static ``pure`` does not count) still run it, once, through
``run_category_setup``; a failing setup still aborts with today's error, and a
category without an exclusive setup gets neither a setup nor a line. Pure:
throwaway categories through ``monkeypatch.setitem``, a private ``_SETUP_DONE``,
``collect_launches`` stubbed; on the real ``services`` entry ``run_category_setup``
only records, and ``_services_setup``, ``db_create`` and ``subprocess.run`` fail the
test if reached.
"""

from __future__ import annotations

import ast
import contextlib
import re
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.test_runner import _backend_api as backend_api
from scripts.test_runner import _backend_db as backend_db
from scripts.test_runner import _backend_services as backend_services
from scripts.test_runner import _backend_utils as backend_utils
from scripts.test_runner import _cli as runner_cli
from scripts.test_runner import _common, _frontend_common, _inventory
from scripts.test_runner._consolidate_backend import _junit_results
from scripts.test_runner._registry import TEST_REGISTRY

PROJECT_ROOT = _common.PROJECT_ROOT
ADAPTER_TEST_PATH = "backend/test_scripts/test_utilities/test_coverage_js_adapter.py"
SELF_TEST_PATH = "backend/test_scripts/test_utilities/test_test_runner_cli.py"


@pytest.fixture
def capture_run_command(monkeypatch):
    """Replace ``_backend_utils.run_command`` with a recorder.

    This is the module's *launch point*: every ``utils_*`` action calls the
    name bound into its own module namespace by the ``from ._common import
    run_command`` at the top of ``_backend_utils.py``. Patching that name
    (not ``_common.run_command``) is what actually intercepts the call —
    patching the origin module would leave the already-bound reference alone.
    """
    calls: list[list[str]] = []

    def fake_run_command(cmd, description, verbose=False, timeout=600):
        calls.append(cmd)
        return True

    monkeypatch.setattr(backend_utils, "run_command", fake_run_command)
    return calls


class TestCoverageJsAdapterActionBuildsDashK:
    """Direct behavior of the concrete action — not registry metadata."""

    def test_two_test_names_join_with_or_after_the_dash_k_flag(self, capture_run_command):
        ok = backend_utils.utils_coverage_js_adapter(test_names=["test_a", "test_b"])
        assert ok is True
        assert len(capture_run_command) == 1
        cmd = capture_run_command[0]
        assert "-k" in cmd
        assert cmd[cmd.index("-k") + 1] == "test_a or test_b"

    def test_three_test_names_preserve_order_in_the_or_expression(self, capture_run_command):
        backend_utils.utils_coverage_js_adapter(test_names=["alpha", "beta", "gamma"])
        cmd = capture_run_command[0]
        assert cmd[cmd.index("-k") + 1] == "alpha or beta or gamma"

    def test_a_single_test_name_still_uses_the_dash_k_flag(self, capture_run_command):
        backend_utils.utils_coverage_js_adapter(test_names=["only_this_one"])
        cmd = capture_run_command[0]
        assert cmd[cmd.index("-k") + 1] == "only_this_one"

    def test_no_test_names_omits_the_dash_k_flag_entirely(self, capture_run_command):
        backend_utils.utils_coverage_js_adapter()
        cmd = capture_run_command[0]
        assert "-k" not in cmd

    def test_an_empty_test_names_list_also_omits_the_dash_k_flag(self, capture_run_command):
        """``test_names=[]`` is falsy, same as ``None`` — an empty filter must
        not turn into ``-k ""``, which would match nothing."""
        backend_utils.utils_coverage_js_adapter(test_names=[])
        cmd = capture_run_command[0]
        assert "-k" not in cmd

    def test_the_action_always_targets_its_own_test_file(self, capture_run_command):
        backend_utils.utils_coverage_js_adapter()
        cmd = capture_run_command[0]
        assert ADAPTER_TEST_PATH in cmd

    def test_the_action_reports_the_launch_as_successful_when_run_command_does(self, capture_run_command):
        ok = backend_utils.utils_coverage_js_adapter()
        assert ok is True


class TestRunTestFromRegistryForwardsSelectors:
    """The CLI dispatch layer: does it actually pass ``test_names`` through to
    the action's own command, or only through to itself?"""

    def test_registry_dispatch_forwards_test_names_into_the_same_dash_k(self, capture_run_command):
        ok = runner_cli.run_test_from_registry(category="utils", action="coverage-js-adapter", test_names=["forwarded_name"])
        assert ok is True
        cmd = capture_run_command[0]
        assert cmd[cmd.index("-k") + 1] == "forwarded_name"

    def test_registry_dispatch_without_test_names_runs_the_bare_file(self, capture_run_command):
        runner_cli.run_test_from_registry(category="utils", action="coverage-js-adapter")
        cmd = capture_run_command[0]
        assert "-k" not in cmd
        assert ADAPTER_TEST_PATH in cmd

    def test_registry_dispatch_rejects_an_unknown_action_without_touching_run_command(self, capture_run_command):
        ok = runner_cli.run_test_from_registry(category="utils", action="does-not-exist")
        assert ok is False
        assert capture_run_command == []


class TestRunPassesListTests:
    def test_list_tests_dispatches_without_touching_execution_helpers(self, monkeypatch):
        dispatch_result = object()
        dispatch_calls = []
        args = SimpleNamespace(category="utils", list_tests=True)
        test_names = ["selected-test"]

        def fail_if_touched(*_args, **_kwargs):
            pytest.fail("list-tests dispatch touched an execution-only helper")

        def fake_dispatch(category, names, verbose, dispatch_args):
            dispatch_calls.append((category, names, verbose, dispatch_args))
            return dispatch_result

        for helper_name in ("_run_exclusive_setups", "shared_backend_for", "_apply_parallel"):
            monkeypatch.setattr(runner_cli, helper_name, fail_if_touched)
        monkeypatch.setattr(runner_cli, "dispatch_to_category", fake_dispatch)

        result = runner_cli._run_passes(args, test_names, verbose=False)

        assert dispatch_calls == [("utils", test_names, False, args)]
        assert result == (dispatch_result, True, True)


class TestCoverageJsCompilesWithoutImportOrSubprocess:
    """Proves the source is sound and still shaped as the adapter expects it —
    via ``compile()`` on the source text only. No ``import scripts.coverage_js``
    (which would execute and cache module state other tests could observe), no
    subprocess, no ``.pyc``."""

    @staticmethod
    def _top_level_function_names(source: str) -> set[str]:
        code = compile(source, "scripts/coverage_js.py", "exec")
        names: set[str] = set()
        for const in code.co_consts:
            if hasattr(const, "co_name"):
                names.add(const.co_name)
        return names

    def test_the_source_compiles_without_a_syntax_error(self):
        source = (PROJECT_ROOT / "scripts" / "coverage_js.py").read_text(encoding="utf-8")
        # compile() itself raises SyntaxError on failure; reaching this line is the proof.
        compile(source, "scripts/coverage_js.py", "exec")

    def test_the_functions_the_adapter_depends_on_are_still_defined(self):
        source = (PROJECT_ROOT / "scripts" / "coverage_js.py").read_text(encoding="utf-8")
        names = self._top_level_function_names(source)
        for expected in ("is_istanbul", "istanbul_to_analysis", "_statements_in_range", "_branches_in_range"):
            assert expected in names, f"{expected} missing: the adapter action would be pointing at a file that no longer matches its own test suite"

    def test_the_running_action_links_to_the_test_file_that_imports_the_module(self, capture_run_command):
        """The compile check proves the source is sound in isolation; this
        proves the live action is wired to the test file that actually
        imports it, closing the loop without importing anything ourselves."""
        backend_utils.utils_coverage_js_adapter()
        cmd = capture_run_command[0]
        assert any(ADAPTER_TEST_PATH in part for part in cmd)
        adapter_test_source = (PROJECT_ROOT / ADAPTER_TEST_PATH).read_text(encoding="utf-8")
        assert "from scripts.coverage_js import" in adapter_test_source


class TestSelfRegistrationInTheCatalogue:
    """This file's own action entry: registered, pure, pointed at itself."""

    def test_test_runner_cli_action_is_registered_under_utils(self):
        assert "test-runner-cli" in TEST_REGISTRY["utils"]

    def test_test_runner_cli_action_declares_pure_isolation(self):
        entry = TEST_REGISTRY["utils"]["test-runner-cli"]
        assert entry["isolation"] == "pure"

    def test_test_runner_cli_action_has_a_concrete_name_and_description(self):
        entry = TEST_REGISTRY["utils"]["test-runner-cli"]
        assert entry["name"].strip()
        assert entry["desc"].strip()

    def test_test_runner_cli_action_targets_this_file(self, capture_run_command):
        entry = TEST_REGISTRY["utils"]["test-runner-cli"]
        entry["func"]()
        cmd = capture_run_command[0]
        assert SELF_TEST_PATH in cmd

    def test_test_runner_cli_action_is_included_in_utils_all(self):
        assert TEST_REGISTRY["utils"]["test-runner-cli"].get("in_all", True) is True


class TestListFrontTestsWithSequenceMetadata:
    """Sequence-valued ``tests`` metadata may mix E2E specs and unit files."""

    def test_mixed_tests_tuple_lists_spec_and_ignores_unit_path(self, tmp_path, monkeypatch, capsys):
        category = "front-list-tuple-regression"
        unit_path = "src/lib/registry-tuple.test.ts"
        spec_path = "utility/registry-tuple.spec.ts"
        full_spec_path = tmp_path / "frontend" / "e2e" / spec_path
        full_spec_path.parent.mkdir(parents=True)
        full_spec_path.write_text(
            """
test.describe("Tuple metadata", () => {
  test("lists the spec from tuple metadata", async () => {});
});
""",
            encoding="utf-8",
        )
        monkeypatch.setitem(
            TEST_REGISTRY,
            category,
            {"mixed-tests": {"tests": (unit_path, spec_path)}},
        )
        monkeypatch.setattr(_frontend_common, "PROJECT_ROOT", tmp_path)

        result = _frontend_common._list_front_tests(category)
        captured = capsys.readouterr()
        output = captured.out + captured.err

        assert result is True
        assert spec_path in output
        assert "lists the spec from tuple metadata" in output
        assert unit_path not in output

    def test_unit_only_tests_tuple_reports_no_specs_without_crashing(self, tmp_path, monkeypatch, capsys):
        category = "front-list-unit-only-tuple-regression"
        unit_path = "src/lib/registry-unit-only.test.ts"
        monkeypatch.setitem(
            TEST_REGISTRY,
            category,
            {"unit-tests": {"tests": (unit_path,)}},
        )
        monkeypatch.setattr(_frontend_common, "PROJECT_ROOT", tmp_path)

        result = _frontend_common._list_front_tests(category)
        captured = capsys.readouterr()
        output = captured.out + captured.err

        assert result is True
        assert f"No spec files found for category '{category}'" in output
        assert unit_path not in output


class TestMissingPathRegression:
    """Pins the missing-path preflight in ``_common.run_command``.

    This test is constructed to fail without that preflight: it monkeypatches
    ``subprocess.run`` to fail loudly the instant it is invoked, so a pytest
    command built from a path that does not exist on disk would previously
    have shelled straight into ``subprocess.run`` and tripped the guard. With
    the preflight in place it now proves the path is rejected before any
    process is spawned. Do not weaken this assertion or catch the failure to
    make it pass artificially — the preflight itself lives in ``_common.py``,
    not here.
    """

    def test_a_missing_backend_test_path_is_rejected_before_subprocess_ever_runs(self, monkeypatch):
        missing_path = "backend/test_scripts/test_utilities/test_does_not_exist_for_hardening_probe.py"
        assert not (PROJECT_ROOT / missing_path).exists(), "the regression needs a path that is genuinely absent"
        cmd = _common._build_pytest_cmd(missing_path)

        def fail_if_invoked(*_args, **_kwargs):
            pytest.fail("run_command shelled out to subprocess.run for a pytest path that does not exist on disk; _common.py needs a missing-path preflight that returns False before ever invoking subprocess.run")

        monkeypatch.setattr(_common.subprocess, "run", fail_if_invoked)
        result = _common.run_command(cmd, "missing path regression probe")
        assert result is False, "a nonexistent test path must fail loudly, not silently report success"


# Units are paths relative to backend/test_scripts/: a file unit ends in ``.py``, a directory unit in ``/``.
FINANCIAL_DIR = "test_services/test_financial/"  # roi-fifo-utils
FINANCIAL_MATH_DIR = "test_services/test_financial_math/"  # financial-math
SERVICES_DIR = "test_services/"
OTHER_FILE = "test_services/test_financial/test_other.py"

CASE_IN_FINANCIAL_MATH = "backend.test_scripts.test_services.test_financial_math.test_average_cost.TestX"
CASE_IN_FINANCIAL = "backend.test_scripts.test_services.test_financial.test_other.TestY"
CASE_ELSEWHERE_IN_FINANCIAL = "backend.test_scripts.test_services.test_financial.test_sibling.TestW"
CASE_DIRECTLY_IN_SERVICES = "backend.test_scripts.test_services.test_misc.TestZ"


def _unit_orders(*units: str) -> list:
    """``units`` in the order run_backend_consolidated hands them over (sorted), and reversed."""
    return [pytest.param(sorted(units), id="runner-order"), pytest.param(sorted(units, reverse=True), id="reversed")]


def _junit_report(tmp_path: Path, cases: list[tuple[str, bool]]) -> Path:
    """A minimal pytest junit report: one ``<testcase>`` per ``(classname, passed)``; a red one carries ``<failure/>``."""
    rows = []
    for index, (classname, passed) in enumerate(cases):
        body = "" if passed else '<failure message="red on purpose">AssertionError</failure>'
        rows.append(f'<testcase classname="{classname}" name="test_{index}" time="0.001">{body}</testcase>')
    report = tmp_path / "report.xml"
    report.write_text(
        f'<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest" tests="{len(cases)}">{"".join(rows)}</testsuite></testsuites>',
        encoding="utf-8",
    )
    return report


class TestJunitAttributionToDirectoryUnits:
    """``_junit_results`` gives every junit case to the unit that owns it.

    The consolidated backend pass reads its single junit report back into one verdict per
    unit. A directory unit owns the modules below it — below it on a ``/`` boundary, not
    every path that merely starts with the same characters — and when several directory
    units contain a case, the deepest one owns it. A file unit found by the exact walk keeps
    its own cases. None of this may depend on the order the units arrive in: the runner hands
    them over sorted, and ``/`` sorts before ``_``, so ``test_financial/`` comes before
    ``test_financial_math/`` — and, matched by bare prefix, swallowed its cases: financial-math
    got no verdict and was reported as "produced no test case" with its 39 tests green.
    """

    @pytest.mark.parametrize("known", _unit_orders(FINANCIAL_DIR, FINANCIAL_MATH_DIR))
    def test_sibling_directory_units_sharing_a_prefix_each_get_their_own_cases(self, tmp_path, known):
        report = _junit_report(tmp_path, [(CASE_IN_FINANCIAL_MATH, True), (CASE_IN_FINANCIAL, True)])

        assert _junit_results(report, known) == {FINANCIAL_MATH_DIR: True, FINANCIAL_DIR: True}

    @pytest.mark.parametrize("known", _unit_orders(FINANCIAL_DIR, FINANCIAL_MATH_DIR))
    @pytest.mark.parametrize(
        ("red_case", "expected"),
        [
            pytest.param(CASE_IN_FINANCIAL_MATH, {FINANCIAL_MATH_DIR: False, FINANCIAL_DIR: True}, id="red-in-financial-math"),
            pytest.param(CASE_IN_FINANCIAL, {FINANCIAL_MATH_DIR: True, FINANCIAL_DIR: False}, id="red-in-financial"),
        ],
    )
    def test_a_red_case_turns_only_its_own_directory_unit_red(self, tmp_path, known, red_case, expected):
        report = _junit_report(tmp_path, [(case, case != red_case) for case in (CASE_IN_FINANCIAL_MATH, CASE_IN_FINANCIAL)])

        assert _junit_results(report, known) == expected

    @pytest.mark.parametrize("known", _unit_orders(SERVICES_DIR, FINANCIAL_DIR))
    @pytest.mark.parametrize(
        ("classname", "owner"),
        [
            pytest.param(CASE_IN_FINANCIAL, FINANCIAL_DIR, id="case-in-the-nested-directory"),
            pytest.param(CASE_DIRECTLY_IN_SERVICES, SERVICES_DIR, id="case-directly-in-the-outer-directory"),
        ],
    )
    def test_the_deepest_directory_unit_containing_a_case_owns_it(self, tmp_path, known, classname, owner):
        report = _junit_report(tmp_path, [(classname, True)])

        assert _junit_results(report, known) == {owner: True}

    @pytest.mark.parametrize("known", _unit_orders(FINANCIAL_DIR, OTHER_FILE))
    @pytest.mark.parametrize(
        ("red_case", "expected"),
        [
            pytest.param(CASE_IN_FINANCIAL, {OTHER_FILE: False, FINANCIAL_DIR: True}, id="red-in-the-file-unit"),
            pytest.param(CASE_ELSEWHERE_IN_FINANCIAL, {OTHER_FILE: True, FINANCIAL_DIR: False}, id="red-elsewhere-in-the-directory"),
        ],
    )
    def test_a_file_unit_keeps_its_own_cases_inside_a_directory_unit(self, tmp_path, known, red_case, expected):
        """Guard: the exact walk finds the file unit first; the directory gets only what the file does not own."""
        report = _junit_report(tmp_path, [(case, case != red_case) for case in (CASE_IN_FINANCIAL, CASE_ELSEWHERE_IN_FINANCIAL)])

        assert _junit_results(report, known) == expected


# ── H-21: a single action seeds its category first, when the category says it must ──────────────────────────────────
# Every name the contract adds is looked up at call time: a missing one fails its cases on a named "H-21:" barrier and
# leaves the cases above alone.

#: The accounts the api units sign in as: contract point 4, ``_backend_api.API_FIXTURE_USERS``.
FIXTURE_USERS = ("e2e_test_admin", "e2e_test_user")
#: What SQLite leaves next to a database it writes to; a rollback-journal database that is only read leaves none.
SQLITE_SIDECARS = ("-journal", "-wal", "-shm")
POPULATE_MOCK_DATA = PROJECT_ROOT / "backend" / "test_scripts" / "test_db" / "populate_mock_data.py"


class _SetupNeededProbeError(RuntimeError):
    """What a fake ``setup_needed`` raises: its type name must reach the line ``ensure_category_setup`` prints."""


class _FakeCategory:
    """A throwaway category whose setup, ``setup_needed`` and actions only record, in order, that they ran.

    Built with the real ``make_category``/``add_test`` and injected with ``monkeypatch.setitem(TEST_REGISTRY, …)``.
    ``setup_needed`` is set on ``_meta`` by hand, where contract point 1 stores it, so the dispatch cases reach
    ``run_test_from_registry`` even while ``make_category`` does not take the keyword (that is the make_category
    cases' barrier, not theirs).
    """

    name = "h21-fake-category"

    def __init__(self, *, reason: str | None = None, setup_result: bool = True, raises: Exception | None = None) -> None:
        self.reason = reason
        self.setup_result = setup_result
        self.raises = raises
        self.events: list[str] = []
        self.one_calls: list[list[str] | None] = []

    def setup(self) -> bool:
        self.events.append("setup")
        return self.setup_result

    def setup_needed(self) -> str | None:
        self.events.append("setup_needed")
        if self.raises is not None:
            raise self.raises
        return self.reason

    def run_one(self, verbose: bool = False, test_names: list[str] | None = None) -> bool:
        self.events.append("one")
        self.one_calls.append(test_names)
        return True

    def run_all(self, verbose: bool = False) -> bool:
        # What every real ``*_test`` does first: the category's own ``all`` runs its setup itself.
        _common.run_category_setup(self.name)
        self.events.append("all")
        return True

    def register(self, monkeypatch, *, with_setup: bool = True, with_setup_needed: bool = True) -> _FakeCategory:
        category = _common.make_category("H-21 fake category", "A category of this test only", setup=self.setup if with_setup else None)
        if with_setup_needed:
            category["_meta"]["setup_needed"] = self.setup_needed
        _common.add_test(category, "one", self.run_one, name="One action", desc="A single action of the fake category")
        _common.add_test(category, "all", self.run_all, test_names=False, name="All", desc="The fake category's own all")
        monkeypatch.setitem(TEST_REGISTRY, self.name, category)
        return self


@pytest.fixture
def fresh_setup_done(monkeypatch):
    """A private ``_common._SETUP_DONE``: no setup recorded by this run, or by a neighbouring case, leaks in or out."""
    monkeypatch.setattr(_common, "_SETUP_DONE", set())


@pytest.fixture
def runner_lines(monkeypatch):
    """Record the ``print_info`` / ``print_error`` lines of ``_common`` and ``_cli`` instead of printing them.

    ``ensure_category_setup`` prints through the names bound in ``_common``; ``_cli`` holds its own bindings of the
    same functions (``from ._common import print_error, print_info``), so both modules are patched.
    """
    lines = SimpleNamespace(info=[], error=[])

    def record_info(message, *_args, **_kwargs):
        lines.info.append(str(message))

    def record_error(message, *_args, **_kwargs):
        lines.error.append(str(message))

    for module in (_common, runner_cli):
        monkeypatch.setattr(module, "print_info", record_info)
        monkeypatch.setattr(module, "print_error", record_error)
    return lines


def _make_category_with_setup_needed(**kwargs) -> dict:
    """``_common.make_category`` called with ``setup_needed``, or the H-21 barrier while it does not take it."""
    kwargs.setdefault("setup_needed", None)
    try:
        return _common.make_category("H-21 probe", "A category of this test only", **kwargs)
    except TypeError as exc:
        if "setup_needed" not in str(exc):
            raise
        pytest.fail(f"H-21: make_category has no setup_needed ({exc})")


def _ensure_category_setup():
    """``_common.ensure_category_setup``, looked up at call time, or the H-21 barrier while it is missing."""
    ensure = getattr(_common, "ensure_category_setup", None)
    if ensure is None:
        pytest.fail("H-21: ensure_category_setup is missing")
    return ensure


def _assert_consulted(fake: _FakeCategory) -> None:
    """The dispatch barrier: a single action of ``fake`` must have asked its ``setup_needed`` first."""
    assert "setup_needed" in fake.events, f"H-21: run_test_from_registry ran a single action of {fake.name!r} without asking its setup_needed first (ran: {fake.events})"


def _users_check_reading(monkeypatch, db_path: Path):
    """``_backend_api._api_fixture_users_missing`` with ``get_test_db_path`` pointed at ``db_path``, or the H-21 barrier."""
    check = getattr(backend_api, "_api_fixture_users_missing", None)
    if check is None:
        pytest.fail("H-21: _api_fixture_users_missing is missing")
    if not hasattr(backend_api, "get_test_db_path"):
        pytest.fail("H-21: _backend_api has no module-level get_test_db_path, so the check cannot be pointed at a database of the test")
    monkeypatch.setattr(backend_api, "get_test_db_path", lambda: db_path)
    return check


def _api_fixture_users() -> tuple:
    """``_backend_api.API_FIXTURE_USERS``, looked up at call time, or the H-21 barrier while it is missing."""
    users = getattr(backend_api, "API_FIXTURE_USERS", None)
    if users is None:
        pytest.fail("H-21: API_FIXTURE_USERS is missing")
    return users


def _sidecars(db_path: Path) -> list[str]:
    """The SQLite sidecar files present next to ``db_path``."""
    return [db_path.name + suffix for suffix in SQLITE_SIDECARS if db_path.with_name(db_path.name + suffix).exists()]


def _write_lane_db(db_path: Path, usernames: tuple[str, ...] | None) -> None:
    """A rollback-journal SQLite file whose ``users`` table holds ``usernames`` — or with no ``users`` table when None.

    The real table (``User`` in ``backend/app/db/models.py``) has more columns; the check needs ``username`` only.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        journal_mode = conn.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
        with conn:
            if usernames is None:
                conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
            else:
                conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL UNIQUE)")
                conn.executemany("INSERT INTO users (username) VALUES (?)", [(name,) for name in usernames])
    assert journal_mode == "delete", f"precondition: the database of the test must use a rollback journal, got {journal_mode!r}"
    assert _sidecars(db_path) == [], f"precondition: nothing next to the database before the check, found {_sidecars(db_path)}"


def _assert_is_reason_naming(reason, db_path: Path) -> None:
    """A reason is a non-empty text that names the database it read."""
    assert isinstance(reason, str) and reason.strip(), f"the api category must seed here, so the check must say why (got {reason!r})"
    assert str(db_path) in reason, f"the reason must name the database it read ({db_path}): {reason!r}"


def _named_users(reason: str, db_path: Path) -> set[str]:
    """The fixture usernames ``reason`` names as whole words (``e2e_test_user2`` is not ``e2e_test_user``), outside the path it names."""
    words = reason.replace(str(db_path), "")
    return {name for name in FIXTURE_USERS if re.search(rf"\b{re.escape(name)}\b", words)}


def _assigned_value(node: ast.AST, name: str) -> ast.expr | None:
    """The value ``node`` assigns to ``name``, when ``node`` is that assignment."""
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
        return node.value
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
        return node.value
    return None


def _seeded_usernames() -> set[str]:
    """The usernames ``test_user_defs`` seeds in populate_mock_data.py, read from its source text: never imported."""
    tree = ast.parse(POPULATE_MOCK_DATA.read_text(encoding="utf-8"), filename=str(POPULATE_MOCK_DATA))
    values = [_assigned_value(node, "test_user_defs") for node in ast.walk(tree)]
    definitions = [value for value in values if value is not None]
    if not definitions:
        pytest.fail(f"{POPULATE_MOCK_DATA.name} no longer assigns test_user_defs: the seeded users cannot be read from it")
    return {row[0] for definition in definitions for row in ast.literal_eval(definition)}


@pytest.mark.usefixtures("fresh_setup_done")
class TestMakeCategoryStoresSetupNeeded:
    """Contract point 1: ``setup_needed`` lives in ``_meta`` next to ``setup``, stored like ``setup_exclusive``."""

    def test_setup_needed_is_stored_next_to_setup(self):
        def setup():
            return True

        def setup_needed():
            return None

        meta = _make_category_with_setup_needed(setup=setup, setup_needed=setup_needed)["_meta"]

        assert meta["setup"] is setup
        assert meta["setup_needed"] is setup_needed
        assert meta["setup_exclusive"] is False

    def test_a_setup_without_setup_needed_declares_none(self):
        """``services`` and the other categories with a setup keep today's behaviour: there is nothing to ask."""

        def setup():
            return True

        meta = _make_category_with_setup_needed(setup=setup)["_meta"]

        assert meta["setup"] is setup
        assert meta.get("setup_needed") is None

    def test_setup_needed_without_a_setup_is_not_stored(self):
        """A reason to run a setup the category does not have would mean nothing: like ``setup_exclusive``, it needs one."""

        def setup_needed():
            return "a reason with no setup to run"

        meta = _make_category_with_setup_needed(setup_needed=setup_needed)["_meta"]

        assert "setup" not in meta
        assert meta.get("setup_needed") is None


@pytest.mark.usefixtures("fresh_setup_done")
class TestEnsureCategorySetup:
    """Contract point 2: ``_common.ensure_category_setup`` runs the setup before one action only when the category says why."""

    def test_a_reason_prints_one_line_and_runs_the_setup_once(self, monkeypatch, runner_lines, capsys):
        ensure = _ensure_category_setup()
        fake = _FakeCategory(reason="the fixture users are absent").register(monkeypatch)

        assert ensure(fake.name) is True
        assert fake.events == ["setup_needed", "setup"]
        assert len(runner_lines.info) == 1, f"one visible line, got {runner_lines.info}"
        assert fake.name in runner_lines.info[0]
        assert fake.reason in runner_lines.info[0]
        assert fake.name in _common._SETUP_DONE, "run_category_setup records the category: once per invocation"

        assert ensure(fake.name) is True
        assert fake.events == ["setup_needed", "setup"], "a second call in the same invocation asks nothing and runs nothing"
        assert len(runner_lines.info) == 1
        captured = capsys.readouterr()
        assert captured.out + captured.err == "", "the one line goes through print_info: nothing else is printed"

    def test_a_failed_setup_comes_back_as_false(self, monkeypatch, runner_lines):
        ensure = _ensure_category_setup()
        fake = _FakeCategory(reason="the fixture users are absent", setup_result=False).register(monkeypatch)

        assert ensure(fake.name) is False
        assert fake.events == ["setup_needed", "setup"]
        assert fake.name in _common._SETUP_DONE

    @pytest.mark.parametrize("reason", [None, ""], ids=["none", "empty"])
    def test_no_reason_runs_nothing_and_prints_nothing(self, monkeypatch, runner_lines, capsys, reason):
        ensure = _ensure_category_setup()
        fake = _FakeCategory(reason=reason).register(monkeypatch)

        assert ensure(fake.name) is True
        assert fake.events == ["setup_needed"]
        assert runner_lines.info == []
        assert fake.name not in _common._SETUP_DONE, "_SETUP_DONE means the setup ran: recording one that did not would make the category's own all skip it later in this invocation"
        captured = capsys.readouterr()
        assert captured.out + captured.err == ""

    def test_a_check_that_raises_seeds_anyway_and_says_it_could_not_check(self, monkeypatch, runner_lines, capsys):
        ensure = _ensure_category_setup()
        fake = _FakeCategory(raises=_SetupNeededProbeError("the probe broke")).register(monkeypatch)

        assert ensure(fake.name) is True
        assert fake.events == ["setup_needed", "setup"], "a check that cannot answer must not skip the setup"
        assert len(runner_lines.info) == 1, f"one visible line, got {runner_lines.info}"
        line = runner_lines.info[0]
        assert fake.name in line
        assert "could not check" in line.lower()
        assert _SetupNeededProbeError.__name__ in line
        assert fake.name in _common._SETUP_DONE
        captured = capsys.readouterr()
        assert captured.out + captured.err == ""

    @pytest.mark.parametrize(
        ("with_setup", "with_setup_needed"),
        [
            pytest.param(True, False, id="setup-without-setup-needed"),
            pytest.param(False, True, id="setup-needed-without-setup"),
        ],
    )
    def test_a_category_without_both_halves_calls_nothing(self, monkeypatch, runner_lines, capsys, with_setup, with_setup_needed):
        ensure = _ensure_category_setup()
        fake = _FakeCategory(reason="would seed, if anyone asked").register(monkeypatch, with_setup=with_setup, with_setup_needed=with_setup_needed)

        assert ensure(fake.name) is True
        assert fake.events == []
        assert runner_lines.info == []
        assert fake.name not in _common._SETUP_DONE
        captured = capsys.readouterr()
        assert captured.out + captured.err == ""

    def test_a_setup_that_already_ran_is_not_checked_again(self, monkeypatch, runner_lines):
        ensure = _ensure_category_setup()
        fake = _FakeCategory(reason="would seed, if anyone asked").register(monkeypatch)
        assert _common.run_category_setup(fake.name) is True
        assert fake.events == ["setup"], "precondition: the setup ran, through the runner's once-per-invocation door"

        assert ensure(fake.name) is True
        assert fake.events == ["setup"], "the setup already ran in this invocation: setup_needed must not even be asked"
        assert runner_lines.info == []

        # Presence barrier: with no setup recorded, the same category IS asked, so the negative above has teeth.
        monkeypatch.setattr(_common, "_SETUP_DONE", set())
        assert ensure(fake.name) is True
        assert fake.events == ["setup", "setup_needed", "setup"]


@pytest.mark.usefixtures("fresh_setup_done")
class TestRunTestFromRegistrySeedsBeforeASingleAction:
    """Contract point 3: a single action asks its category first and seeds when told to; ``all`` and ``--list`` never ask."""

    def test_a_single_action_runs_after_the_check_and_the_setup(self, monkeypatch, runner_lines):
        fake = _FakeCategory(reason="the fixture users are absent").register(monkeypatch)

        result = runner_cli.run_test_from_registry(category=fake.name, action="one", test_names=["only_this"])

        _assert_consulted(fake)
        assert fake.events == ["setup_needed", "setup", "one"]
        assert result is True
        assert fake.one_calls == [["only_this"]], "seeding first must not swallow the -k selector"
        assert any(fake.name in line and fake.reason in line for line in runner_lines.info), f"the user is told why: {runner_lines.info}"

    def test_a_failed_setup_stops_the_action_and_names_the_category(self, monkeypatch, runner_lines):
        fake = _FakeCategory(reason="the fixture users are absent", setup_result=False).register(monkeypatch)

        result = runner_cli.run_test_from_registry(category=fake.name, action="one")

        _assert_consulted(fake)
        assert fake.events == ["setup_needed", "setup"], "the action must not run against a category whose setup failed"
        assert result is False
        assert any(fake.name in line for line in runner_lines.error), f"an error line must name the category: {runner_lines.error}"

    def test_all_never_asks_setup_needed(self, monkeypatch, runner_lines):
        fake = _FakeCategory(reason=None).register(monkeypatch)
        runner_cli.run_test_from_registry(category=fake.name, action="one")
        _assert_consulted(fake)  # presence barrier: a single action of this very category does ask
        fake.events.clear()

        assert runner_cli.run_test_from_registry(category=fake.name, action="all") is True
        assert fake.events == ["setup", "all"], "all seeds through its own *_test, without asking setup_needed first"

    def test_a_listing_never_asks_setup_needed(self, monkeypatch, runner_lines):
        fake = _FakeCategory(reason=None).register(monkeypatch)
        runner_cli.run_test_from_registry(category=fake.name, action="one")
        _assert_consulted(fake)  # presence barrier: a single action of this very category does ask
        fake.events.clear()
        listed = []

        def record_listing(category, action=None):
            listed.append((category, action))
            return True

        monkeypatch.setitem(runner_cli.BACKEND_TEST_PATHS, fake.name, "backend/test_scripts/test_utilities/")
        monkeypatch.setattr(runner_cli, "_list_pytest_tests", record_listing)

        assert runner_cli.run_test_from_registry(category=fake.name, action="one", list_tests=True) is True
        assert listed == [(fake.name, "one")], "presence barrier: the listing itself ran"
        assert fake.events == [], "a listing never seeds: nothing asked, nothing set up, nothing run"

    def test_the_check_is_looked_up_on_common_at_call_time(self, monkeypatch, runner_lines):
        """``_common.ensure_category_setup`` as it is when the action runs, not a copy bound into ``_cli`` at import."""
        fake = _FakeCategory(reason="never asked: the replacement answers first").register(monkeypatch)
        asked = []

        def refuse(category):
            asked.append(category)
            return False

        monkeypatch.setattr(_common, "ensure_category_setup", refuse, raising=False)

        result = runner_cli.run_test_from_registry(category=fake.name, action="one")

        assert asked == [fake.name], f"H-21: run_test_from_registry did not ask _common.ensure_category_setup at call time (asked: {asked})"
        assert result is False
        assert fake.events == [], "a refused setup leaves the action unrun"


@pytest.mark.usefixtures("fresh_setup_done")
class TestApiFixtureUsersMissing:
    """Contract point 4: why the api category must seed before one action, read from the lane's SQLite file without writing it."""

    def test_no_database_file_is_a_reason_and_creates_nothing(self, tmp_path, monkeypatch):
        db_path = tmp_path / "lane" / "sqlite" / "app.db"
        check = _users_check_reading(monkeypatch, db_path)

        reason = check()

        _assert_is_reason_naming(reason, db_path)
        assert not db_path.exists(), "the check created the database it was only meant to read"
        assert list(tmp_path.iterdir()) == [], "the check wrote under the lane's data directory"

    @pytest.mark.parametrize(
        ("present", "missing"),
        [
            pytest.param(None, FIXTURE_USERS, id="no-users-table"),
            pytest.param((), FIXTURE_USERS, id="empty-users-table"),
            pytest.param(("e2e_test_user2", "e2e_user_alice"), FIXTURE_USERS, id="other-seeded-users-only"),
            pytest.param(("e2e_test_admin",), ("e2e_test_user",), id="only-the-admin"),
            pytest.param(("e2e_test_user",), ("e2e_test_admin",), id="only-the-user"),
        ],
    )
    def test_a_reason_names_the_database_and_exactly_the_missing_users(self, tmp_path, monkeypatch, present, missing):
        db_path = tmp_path / "sqlite" / "app.db"
        check = _users_check_reading(monkeypatch, db_path)
        _write_lane_db(db_path, present)

        reason = check()

        _assert_is_reason_naming(reason, db_path)
        assert _named_users(reason, db_path) == set(missing), f"the reason must name exactly the missing users {missing}: {reason!r}"

    def test_both_users_present_is_no_reason(self, tmp_path, monkeypatch):
        db_path = tmp_path / "sqlite" / "app.db"
        check = _users_check_reading(monkeypatch, db_path)
        _write_lane_db(db_path, ("e2e_test_user2", *FIXTURE_USERS, "e2e_user_alice"))

        assert check() is None

    def test_a_file_that_is_not_a_database_is_a_reason_naming_it(self, tmp_path, monkeypatch):
        db_path = tmp_path / "sqlite" / "app.db"
        check = _users_check_reading(monkeypatch, db_path)
        db_path.parent.mkdir(parents=True)
        db_path.write_bytes(b"not a SQLite database, only some bytes where one should be\n" * 64)
        before = db_path.read_bytes()

        reason = check()

        _assert_is_reason_naming(reason, db_path)
        assert db_path.read_bytes() == before, "the check rewrote a file it could not read"
        assert _sidecars(db_path) == []

    @pytest.mark.parametrize(
        "present",
        [
            pytest.param(FIXTURE_USERS, id="both-present"),
            pytest.param(("e2e_test_admin",), id="one-missing"),
            pytest.param(None, id="no-users-table"),
        ],
    )
    def test_the_check_never_writes_the_database(self, tmp_path, monkeypatch, present):
        db_path = tmp_path / "sqlite" / "app.db"
        check = _users_check_reading(monkeypatch, db_path)
        _write_lane_db(db_path, present)
        before_bytes = db_path.read_bytes()
        before_mtime = db_path.stat().st_mtime_ns

        check()

        assert db_path.read_bytes() == before_bytes, "the check changed the database's bytes"
        assert db_path.stat().st_mtime_ns == before_mtime, "the check touched the database's mtime"
        assert _sidecars(db_path) == [], "a sidecar appeared next to a rollback-journal database: the check wrote to it"


@pytest.mark.usefixtures("fresh_setup_done")
class TestApiFixtureUsersAreSeededByPopulate:
    """Contract point 4: ``API_FIXTURE_USERS`` are the accounts the api units sign in as, and ``db populate`` seeds them."""

    def test_the_fixture_users_are_the_two_accounts_the_units_sign_in_as(self):
        assert tuple(_api_fixture_users()) == FIXTURE_USERS

    def test_every_fixture_user_is_seeded_by_populate_mock_data(self):
        users = _api_fixture_users()
        seeded = _seeded_usernames()

        unseeded = [name for name in users if name not in seeded]
        assert unseeded == [], f"test_user_defs in {POPULATE_MOCK_DATA.name} no longer seeds {unseeded}: the api setup could never satisfy its own check"


@pytest.mark.usefixtures("fresh_setup_done")
class TestApiCategoryDeclaresSetupNeeded:
    """Contract point 5: the api category reseeds through ``_api_setup``, before one action only when ``_api_fixture_users_missing`` says why."""

    def test_the_api_category_asks_for_its_fixture_users_before_a_single_action(self):
        meta = TEST_REGISTRY["api"]["_meta"]

        assert meta.get("setup_needed") is not None, "H-21: the api category declares no setup_needed"
        assert meta["setup_needed"] is getattr(backend_api, "_api_fixture_users_missing", None)
        assert meta["setup"] is backend_api._api_setup


# ── H-23: one pure action run on its own leaves the lane's database as it is ──────────────────────────────────────────
# ``_inventory.declared_isolation`` is looked up at call time: while it is missing, the cases that ask it fail on the
# named "H-23: declared_isolation is missing" barrier and leave the cases above alone. Every ``_run_exclusive_setups``
# case on a fake category either is, or first proves (a presence barrier), that one pure action of a category with an
# exclusive setup leaves that setup unrun: today's code, which runs the setup before any action, fails each of them on
# the "H-23: the exclusive setup ran for a single pure action" barrier, and a case that then sees the setup run has teeth.

PURE = _inventory.PURE
READ = _inventory.READ
WRITE_SCOPED = _inventory.WRITE_SCOPED
WRITE_GLOBAL = _inventory.WRITE_GLOBAL

#: Every fake category of the H-23 cases starts with it: ``setup_door`` opens the real setup door for those only.
H23_PREFIX = "h23-"
H23_CATEGORY = "h23-fake-category"
#: The fake category's actions, one per way the catalogue declares a class.
H23_OWN_PURE = "h23-own-pure"
H23_OWN_READ = "h23-own-read"
H23_OWN_WRITE_SCOPED = "h23-own-write-scoped"
H23_OWN_WRITE_GLOBAL = "h23-own-write-global"
H23_EXCLUSIVE_OVER_PURE = "h23-exclusive-over-pure"
H23_UNDECLARED = "h23-undeclared"
#: The actions declaring a class of their own other than pure, with that class.
H23_OWN_NOT_PURE = {H23_OWN_READ: READ, H23_OWN_WRITE_SCOPED: WRITE_SCOPED, H23_OWN_WRITE_GLOBAL: WRITE_GLOBAL}
H23_EXCLUSIVE_REASON = "truncates a table every unit of this fake category reads (a reason of this test only)"
#: A pytest unit no file stands at: the static classifier answers write-global for it without reading anything.
H23_MISSING_PYTEST_UNIT = "test_utilities/test_h23_no_such_unit.py"
#: A vitest unit: the static classifier answers pure for any vitest unit without reading it.
H23_VITEST_UNIT = "src/lib/h23-no-such-unit.test.ts"
#: ``args`` without an ``action`` attribute at all, as an invocation naming only a category may build them.
NO_ACTION_ATTRIBUTE = object()
#: The real catalogue (``_backend_services.populate_registry``): ``client-address`` declares ``pure``; ``asset-source``
#: declares nothing of its own and takes the ``services`` default, ``write-scoped``.
SERVICES_PURE_ACTION = "client-address"
SERVICES_DEFAULT_ACTION = "asset-source"


class _H23FakeCategory:
    """A throwaway category whose setup only records that it ran, with one action per way of declaring a class.

    Built with the real ``make_category``/``add_test`` and injected with ``monkeypatch.setitem(TEST_REGISTRY, …)``. Its
    actions fail the test if anything runs one: the class of an action is read from the catalogue, never found by
    running the action.
    """

    def __init__(self, name: str = H23_CATEGORY, *, default_isolation: str | None = None, with_setup: bool = True, setup_exclusive: bool = True, setup_result: bool = True) -> None:
        self.name = name
        self.default_isolation = default_isolation
        self.with_setup = with_setup
        self.setup_exclusive = setup_exclusive
        self.setup_result = setup_result
        self.events: list[str] = []

    def setup(self) -> bool:
        self.events.append("setup")
        return self.setup_result

    def _refusing(self, action: str):
        """The function registered for ``action``: it fails the test if anything runs it."""

        def run(*_args, **_kwargs):
            pytest.fail(f"{self.name} {action}: an action of the fake category ran; the class of an action is read from the catalogue, not found by running it")

        return run

    def register(self, monkeypatch) -> _H23FakeCategory:
        setup = self.setup if self.with_setup else None
        category = _common.make_category("H-23 fake category", "A category of this test only", setup=setup, setup_exclusive=self.setup_exclusive, default_isolation=self.default_isolation)
        declarations = {
            H23_OWN_PURE: {"isolation": PURE},
            **{action: {"isolation": isolation} for action, isolation in H23_OWN_NOT_PURE.items()},
            H23_EXCLUSIVE_OVER_PURE: {"isolation": PURE, "exclusive_because": H23_EXCLUSIVE_REASON},
            H23_UNDECLARED: {},
        }
        for action, declaration in declarations.items():
            _common.add_test(category, action, self._refusing(action), name=f"H-23 {action}", desc="An action of the fake category", **declaration)
        _common.add_test(category, "all", self._refusing("all"), test_names=False, name="All", desc="The fake category's own all")
        monkeypatch.setitem(TEST_REGISTRY, self.name, category)
        return self


@pytest.fixture
def setup_door(monkeypatch):
    """``_common.run_category_setup`` behind a recorder that still opens the real door, for the H-23 fake categories only.

    Each category asked for is recorded; the real once-per-invocation ``run_category_setup`` then runs the fake's
    recording setup. A real category is refused before its setup could run.
    """
    real_door = _common.run_category_setup
    door = SimpleNamespace(calls=[])

    def recording_door(category):
        door.calls.append(category)
        if not category.startswith(H23_PREFIX):
            pytest.fail(f"run_category_setup was asked for {category!r}, a real category: these cases open only the setups of their own fake categories")
        return real_door(category)

    monkeypatch.setattr(_common, "run_category_setup", recording_door)
    return door


@pytest.fixture
def services_setup_unreachable(monkeypatch):
    """On the real ``services`` entry: ``run_category_setup`` only records the categories it is asked for.

    The real setup behind it, ``_services_setup`` → ``db_create``, deletes the lane's database and rebuilds it from the
    migrations. It is replaced wherever it is bound — the registry's ``_meta``, both runner modules, ``subprocess.run`` —
    so a case that reached it fails here, loudly, instead of emptying the database the lane runs on.
    """
    calls: list[str] = []

    def record_only(category):
        calls.append(category)
        return True

    def fail_if_reached(*_args, **_kwargs):
        pytest.fail("the real services setup was reached past the run_category_setup recorder: _services_setup → db_create would have emptied the lane's test database")

    monkeypatch.setattr(_common, "run_category_setup", record_only)
    monkeypatch.setitem(TEST_REGISTRY["services"]["_meta"], "setup", fail_if_reached)
    monkeypatch.setattr(backend_services, "_services_setup", fail_if_reached)
    monkeypatch.setattr(backend_services, "db_create", fail_if_reached)
    monkeypatch.setattr(backend_db, "db_create", fail_if_reached)
    monkeypatch.setattr(_common.subprocess, "run", fail_if_reached)
    return calls


def _declared_isolation():
    """``_inventory.declared_isolation``, looked up at call time, or the H-23 barrier while it is missing."""
    declared = getattr(_inventory, "declared_isolation", None)
    if declared is None:
        pytest.fail("H-23: declared_isolation is missing")
    return declared


def _args_for(category: str, action) -> SimpleNamespace:
    """The ``args`` of an invocation naming ``category`` and ``action``; no ``action`` attribute for ``NO_ACTION_ATTRIBUTE``."""
    if action is NO_ACTION_ATTRIBUTE:
        return SimpleNamespace(category=category)
    return SimpleNamespace(category=category, action=action)


def _assert_setup_not_run(category: str, action: str, door_calls: list, setup_events=()) -> None:
    """The H-23 barrier: one pure action of ``category`` run on its own leaves the category's exclusive setup unrun."""
    assert not door_calls and not setup_events, f"H-23: the exclusive setup ran for a single pure action ({category} {action}: run_category_setup was asked for {door_calls}, the setup itself ran {len(setup_events)} time(s))"


def _assert_skip_line(lines, category: str, action: str) -> None:
    """Exactly one ``print_info`` line, naming the category and the action whose setup was left unrun, and no error line."""
    assert len(lines.info) == 1, f"one visible line, got {lines.info}"
    assert category in lines.info[0], f"the line must name the category {category!r}: {lines.info[0]!r}"
    assert action in lines.info[0], f"the line must name the action {action!r}: {lines.info[0]!r}"
    assert lines.error == [], f"leaving the setup unrun is not an error: {lines.error}"


def _assert_pure_single_action_skipped(monkeypatch, fake: _H23FakeCategory, door, lines) -> None:
    """Presence barrier: one pure action of ``fake`` leaves its exclusive setup unrun, so the case that follows has teeth.

    The recorders and ``_SETUP_DONE`` are emptied afterwards: the case starts as if nothing had run.
    """
    result = runner_cli._run_exclusive_setups(_args_for(fake.name, H23_OWN_PURE))

    _assert_setup_not_run(fake.name, H23_OWN_PURE, door.calls, fake.events)
    assert result is True
    door.calls.clear()
    fake.events.clear()
    lines.info.clear()
    lines.error.clear()
    monkeypatch.setattr(_common, "_SETUP_DONE", set())


def _assert_setup_ran_once(fake: _H23FakeCategory, door, lines) -> None:
    """The exclusive setup ran once, through ``run_category_setup``, and no line says the database was left as it is."""
    assert door.calls == [fake.name], f"the setup must run once, through _common.run_category_setup (asked for: {door.calls})"
    assert fake.events == ["setup"], f"the fake's setup must run exactly once (ran: {fake.events})"
    assert lines.info == [], f"the setup ran: no line may say the lane's database was left as it is ({lines.info})"


def _stub_launches(monkeypatch, launches: dict) -> None:
    """``_inventory.collect_launches`` answering ``launches`` in its own shape, ``{(category, action): [(engine, path, project), …]}``, and no error."""

    def collect(only_all: bool = False):
        return launches, {}

    monkeypatch.setattr(_inventory, "collect_launches", collect)


class TestDeclaredIsolation:
    """Contract point 1: ``_inventory.declared_isolation`` answers the class the catalogue declares for one action."""

    def test_an_exclusive_because_wins_over_a_declared_pure(self, monkeypatch):
        declared = _declared_isolation()
        fake = _H23FakeCategory(default_isolation=PURE).register(monkeypatch)
        entry = TEST_REGISTRY[fake.name][H23_EXCLUSIVE_OVER_PURE]
        assert entry["isolation"] == PURE and entry["exclusive_because"] == H23_EXCLUSIVE_REASON, f"precondition: the entry declares both ({entry})"

        assert declared(fake.name, H23_EXCLUSIVE_OVER_PURE) == WRITE_GLOBAL

    @pytest.mark.parametrize(
        ("default", "action", "expected"),
        [
            pytest.param(WRITE_SCOPED, H23_OWN_PURE, PURE, id="pure-over-a-write-scoped-default"),
            pytest.param(PURE, H23_OWN_READ, READ, id="read-over-a-pure-default"),
            pytest.param(PURE, H23_OWN_WRITE_SCOPED, WRITE_SCOPED, id="write-scoped-over-a-pure-default"),
            pytest.param(PURE, H23_OWN_WRITE_GLOBAL, WRITE_GLOBAL, id="write-global-over-a-pure-default"),
            pytest.param(None, H23_OWN_PURE, PURE, id="pure-without-a-default"),
        ],
    )
    def test_an_own_isolation_is_declared_whatever_the_category_default(self, monkeypatch, default, action, expected):
        declared = _declared_isolation()
        fake = _H23FakeCategory(default_isolation=default).register(monkeypatch)

        assert declared(fake.name, action) == expected

    @pytest.mark.parametrize("default", [PURE, READ, WRITE_SCOPED, WRITE_GLOBAL])
    def test_an_action_without_its_own_isolation_takes_the_category_default(self, monkeypatch, default):
        declared = _declared_isolation()
        fake = _H23FakeCategory(default_isolation=default).register(monkeypatch)

        assert declared(fake.name, H23_UNDECLARED) == default

    def test_no_own_isolation_and_no_category_default_is_none(self, monkeypatch):
        declared = _declared_isolation()
        fake = _H23FakeCategory(default_isolation=None).register(monkeypatch)
        assert "default_isolation" not in TEST_REGISTRY[fake.name]["_meta"], "precondition: the fake category declares no default"

        assert declared(fake.name, H23_UNDECLARED) is None

    def test_an_unknown_category_is_none(self):
        declared = _declared_isolation()
        category = "h23-no-such-category"
        assert category not in TEST_REGISTRY, "precondition: the category must be genuinely absent"

        assert declared(category, H23_OWN_PURE) is None

    @pytest.mark.parametrize("default", [None, WRITE_SCOPED], ids=["no-default", "write-scoped-default"])
    def test_an_unknown_action_is_none_whatever_the_category_default(self, monkeypatch, default):
        declared = _declared_isolation()
        fake = _H23FakeCategory(default_isolation=default).register(monkeypatch)
        action = "h23-no-such-action"
        assert action not in TEST_REGISTRY[fake.name], "precondition: the action must be genuinely absent"

        assert declared(fake.name, action) is None

    def test_the_catalogue_is_read_when_asked(self, monkeypatch):
        declared = _declared_isolation()
        fake = _H23FakeCategory(default_isolation=PURE).register(monkeypatch)
        assert declared(fake.name, H23_UNDECLARED) == PURE

        _H23FakeCategory(fake.name, default_isolation=WRITE_SCOPED).register(monkeypatch)

        assert declared(fake.name, H23_UNDECLARED) == WRITE_SCOPED, "declared_isolation answered from a copy: it must read TEST_REGISTRY when asked"


class TestBuildInventoryClassifiesThroughDeclaredIsolation:
    """Contract point 2: a unit's class is ``classify(engine, path, declared_isolation(category, action))``, one definition.

    ``collect_launches`` is replaced by each case's launches, in its own shape, so no action is invoked: every fake action
    launches one ``(engine, path, project)`` the static classifier judges without reading a file.
    """

    @pytest.mark.parametrize(
        ("default", "action", "engine", "path", "expected"),
        [
            pytest.param(WRITE_SCOPED, H23_OWN_READ, "pytest", H23_MISSING_PYTEST_UNIT, READ, id="own-isolation"),
            pytest.param(WRITE_SCOPED, H23_UNDECLARED, "pytest", H23_MISSING_PYTEST_UNIT, WRITE_SCOPED, id="category-default"),
            pytest.param(PURE, H23_EXCLUSIVE_OVER_PURE, "vitest", H23_VITEST_UNIT, WRITE_GLOBAL, id="exclusive-because"),
            pytest.param(None, H23_UNDECLARED, "pytest", H23_MISSING_PYTEST_UNIT, WRITE_GLOBAL, id="undeclared-pytest-static"),
            pytest.param(None, H23_UNDECLARED, "vitest", H23_VITEST_UNIT, PURE, id="undeclared-vitest-static"),
        ],
    )
    def test_a_unit_takes_the_class_classify_gives_its_declared_isolation(self, monkeypatch, default, action, engine, path, expected):
        declared = _declared_isolation()
        assert not (_inventory.PROJECT_ROOT / "backend" / "test_scripts" / H23_MISSING_PYTEST_UNIT).exists(), "precondition: the static classifier must find no file there"
        fake = _H23FakeCategory(default_isolation=default).register(monkeypatch)
        _stub_launches(monkeypatch, {(fake.name, action): [(engine, path, "")]})

        units, _errors = _inventory.build_inventory()

        assert [(unit.category, unit.action, unit.engine, unit.path) for unit in units] == [(fake.name, action, engine, path)]
        assert units[0].isolation == _inventory.classify(engine, path, declared(fake.name, action))
        assert units[0].isolation == expected
        assert units[0].exclusive_because == TEST_REGISTRY[fake.name][action].get("exclusive_because", "")

    def test_every_unit_takes_the_class_declared_isolation_answers(self, monkeypatch):
        """One definition, looked up when ``build_inventory`` runs: a stand-in ``declared_isolation`` decides every unit's class."""
        real_declared = _declared_isolation()
        fake = _H23FakeCategory(default_isolation=WRITE_SCOPED).register(monkeypatch)
        launches = {
            (fake.name, H23_OWN_READ): [("pytest", H23_MISSING_PYTEST_UNIT, "")],
            (fake.name, H23_EXCLUSIVE_OVER_PURE): [("vitest", H23_VITEST_UNIT, "")],
            (fake.name, H23_UNDECLARED): [("pytest", H23_MISSING_PYTEST_UNIT, ""), ("vitest", H23_VITEST_UNIT, "")],
        }
        assert PURE not in {real_declared(*key) for key in launches}, "precondition: the catalogue declares none of these actions pure"
        _stub_launches(monkeypatch, launches)
        asked = []

        def stand_in(category, action):
            asked.append((category, action))
            return PURE

        monkeypatch.setattr(_inventory, "declared_isolation", stand_in)

        units, _errors = _inventory.build_inventory()

        assert set(launches) <= set(asked), f"H-23: build_inventory did not ask declared_isolation for every action it launches (asked: {asked})"
        assert {(unit.action, unit.engine, unit.path): unit.isolation for unit in units} == {(action, engine, path): PURE for (_category, action), items in launches.items() for engine, path, _project in items}
        assert [unit.exclusive_because for unit in units if unit.action == H23_EXCLUSIVE_OVER_PURE] == [H23_EXCLUSIVE_REASON], "a unit's exclusive_because is still its entry's"


@pytest.mark.usefixtures("fresh_setup_done")
class TestRunExclusiveSetupsSparesASinglePureAction:
    """Contract point 3: one action run on its own that the catalogue declares pure leaves its category's exclusive setup unrun.

    Everything else runs it as today, once, through ``run_category_setup``: the whole category, ``all``, an action
    declared anything else, an action with no declared class. The fake categories default to ``pure`` wherever that
    sharpens a case: an implementation that read the default before the action's own class, or asked about ``all``,
    would leave the setup unrun there.
    """

    def test_a_single_pure_action_leaves_the_setup_unrun_and_says_so_once(self, monkeypatch, runner_lines, setup_door, capsys):
        """The action's own pure wins over the category's write-scoped default."""
        fake = _H23FakeCategory(default_isolation=WRITE_SCOPED).register(monkeypatch)

        result = runner_cli._run_exclusive_setups(_args_for(fake.name, H23_OWN_PURE))

        _assert_setup_not_run(fake.name, H23_OWN_PURE, setup_door.calls, fake.events)
        assert result is True
        _assert_skip_line(runner_lines, fake.name, H23_OWN_PURE)
        assert fake.name not in _common._SETUP_DONE, "_SETUP_DONE means the setup ran: recording one that did not would make the category's own all skip it later in this invocation"
        captured = capsys.readouterr()
        assert captured.out + captured.err == "", "the one line goes through print_info: nothing else is printed"

    def test_an_action_without_its_own_isolation_in_a_pure_category_leaves_it_unrun_too(self, monkeypatch, runner_lines, setup_door):
        fake = _H23FakeCategory(default_isolation=PURE).register(monkeypatch)

        result = runner_cli._run_exclusive_setups(_args_for(fake.name, H23_UNDECLARED))

        _assert_setup_not_run(fake.name, H23_UNDECLARED, setup_door.calls, fake.events)
        assert result is True
        _assert_skip_line(runner_lines, fake.name, H23_UNDECLARED)

    @pytest.mark.parametrize("action", list(H23_OWN_NOT_PURE))
    def test_a_single_action_declared_anything_but_pure_runs_the_setup_once(self, monkeypatch, runner_lines, setup_door, action):
        """The category's pure default must not win over the action's own class."""
        fake = _H23FakeCategory(default_isolation=PURE).register(monkeypatch)
        _assert_pure_single_action_skipped(monkeypatch, fake, setup_door, runner_lines)

        result = runner_cli._run_exclusive_setups(_args_for(fake.name, action))

        _assert_setup_ran_once(fake, setup_door, runner_lines)
        assert result is True

    def test_an_exclusive_because_over_a_declared_pure_runs_the_setup_once(self, monkeypatch, runner_lines, setup_door):
        fake = _H23FakeCategory(default_isolation=PURE).register(monkeypatch)
        _assert_pure_single_action_skipped(monkeypatch, fake, setup_door, runner_lines)

        result = runner_cli._run_exclusive_setups(_args_for(fake.name, H23_EXCLUSIVE_OVER_PURE))

        _assert_setup_ran_once(fake, setup_door, runner_lines)
        assert result is True

    def test_an_action_with_no_declared_class_runs_the_setup_once(self, monkeypatch, runner_lines, setup_door):
        """Conservative: no own isolation and no category default is not pure, whatever ``classify()`` would find statically."""
        fake = _H23FakeCategory(default_isolation=None).register(monkeypatch)
        _assert_pure_single_action_skipped(monkeypatch, fake, setup_door, runner_lines)

        result = runner_cli._run_exclusive_setups(_args_for(fake.name, H23_UNDECLARED))

        _assert_setup_ran_once(fake, setup_door, runner_lines)
        assert result is True

    @pytest.mark.parametrize("action", ["all", None, NO_ACTION_ATTRIBUTE], ids=["all", "none", "missing"])
    def test_the_whole_category_runs_the_setup_once(self, monkeypatch, runner_lines, setup_door, action):
        """``all`` is not one action run on its own, though the catalogue gives this category's ``all`` entry the pure default."""
        fake = _H23FakeCategory(default_isolation=PURE).register(monkeypatch)
        _assert_pure_single_action_skipped(monkeypatch, fake, setup_door, runner_lines)

        result = runner_cli._run_exclusive_setups(_args_for(fake.name, action))

        _assert_setup_ran_once(fake, setup_door, runner_lines)
        assert result is True

    def test_a_failing_setup_still_aborts_with_todays_error(self, monkeypatch, runner_lines, setup_door):
        fake = _H23FakeCategory(default_isolation=PURE, setup_result=False).register(monkeypatch)
        _assert_pure_single_action_skipped(monkeypatch, fake, setup_door, runner_lines)

        result = runner_cli._run_exclusive_setups(_args_for(fake.name, H23_OWN_WRITE_SCOPED))

        _assert_setup_ran_once(fake, setup_door, runner_lines)
        assert result is False
        assert len(runner_lines.error) == 1, f"one error line, got {runner_lines.error}"
        assert fake.name in runner_lines.error[0]
        assert "setup failed before the shared backend" in runner_lines.error[0]

    @pytest.mark.parametrize(
        ("with_setup", "setup_exclusive"),
        [
            pytest.param(True, False, id="setup-not-exclusive"),
            pytest.param(False, True, id="no-setup"),
        ],
    )
    def test_a_category_without_an_exclusive_setup_gets_no_setup_and_no_line(self, monkeypatch, runner_lines, setup_door, capsys, with_setup, setup_exclusive):
        witness = _H23FakeCategory("h23-exclusive-witness", default_isolation=PURE).register(monkeypatch)
        _assert_pure_single_action_skipped(monkeypatch, witness, setup_door, runner_lines)
        fake = _H23FakeCategory("h23-no-exclusive-setup", default_isolation=PURE, with_setup=with_setup, setup_exclusive=setup_exclusive).register(monkeypatch)
        assert not _common.setup_is_exclusive(fake.name), "precondition: the category has no exclusive setup"

        result = runner_cli._run_exclusive_setups(_args_for(fake.name, H23_OWN_PURE))

        assert result is True
        assert setup_door.calls == []
        assert fake.events == []
        assert runner_lines.info == [], f"no exclusive setup was left unrun: there is nothing to say ({runner_lines.info})"
        assert runner_lines.error == []
        captured = capsys.readouterr()
        assert captured.out + captured.err == ""


@pytest.mark.usefixtures("fresh_setup_done")
class TestServicesClientAddressKeepsTheLaneDatabase:
    """Contract point 3 on the real catalogue: ``services client-address`` no longer empties the lane's database first."""

    def test_the_catalogue_declares_client_address_pure(self):
        entry = TEST_REGISTRY["services"][SERVICES_PURE_ACTION]
        assert entry.get("isolation") == PURE and not entry.get("exclusive_because"), f"precondition: {SERVICES_PURE_ACTION} is declared pure in _backend_services.py ({entry.get('isolation')!r})"

        assert _declared_isolation()("services", SERVICES_PURE_ACTION) == PURE

    def test_client_address_on_its_own_leaves_the_services_setup_unrun(self, runner_lines, services_setup_unreachable, capsys):
        assert _common.setup_is_exclusive("services"), "precondition: services recreates the lane's database in an exclusive setup"

        result = runner_cli._run_exclusive_setups(_args_for("services", SERVICES_PURE_ACTION))

        _assert_setup_not_run("services", SERVICES_PURE_ACTION, services_setup_unreachable)
        assert result is True
        _assert_skip_line(runner_lines, "services", SERVICES_PURE_ACTION)
        captured = capsys.readouterr()
        assert captured.out + captured.err == ""

    def test_an_action_on_the_write_scoped_default_still_runs_the_setup_once(self, runner_lines, services_setup_unreachable):
        meta = TEST_REGISTRY["services"]["_meta"]
        entry = TEST_REGISTRY["services"][SERVICES_DEFAULT_ACTION]
        assert meta.get("default_isolation") == WRITE_SCOPED, "precondition: services declares write-scoped as its default"
        assert "isolation" not in entry and not entry.get("exclusive_because"), f"precondition: {SERVICES_DEFAULT_ACTION} declares nothing of its own; pick another services action on the default"
        assert _declared_isolation()("services", SERVICES_DEFAULT_ACTION) == WRITE_SCOPED

        result = runner_cli._run_exclusive_setups(_args_for("services", SERVICES_DEFAULT_ACTION))

        assert services_setup_unreachable == ["services"], f"the setup must run once, through _common.run_category_setup (asked for: {services_setup_unreachable})"
        assert result is True
        assert runner_lines.info == [], f"the setup ran: no line may say the lane's database was left as it is ({runner_lines.info})"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
