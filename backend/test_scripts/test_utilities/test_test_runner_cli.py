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
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.test_runner import _backend_utils as backend_utils
from scripts.test_runner import _cli as runner_cli
from scripts.test_runner import _common, _frontend_common
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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
