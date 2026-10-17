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

The H-43 regressions pin how an action that runs only when named stays out of the
consolidated frontend pass. ``in_all=False`` is read by the serial ``all`` alone
(``_get_category_tests_for_all``, ``nothing_left_to_run``):
``_consolidate.group_frontend_units`` groups whatever ``_inventory.collect_launches``
reports, and that dry run invokes every action but ``all``, whatever its ``in_all``.
That is right for the AI Export and Designer Lab per-spec actions, ``in_all=False``
because an alias runs their specs in one invocation: they stay claimants, each with a
verdict and a ``--resume`` entry of its own. It is wrong for ``front-utility
cloud-smoke``, which refuses any lane but a managed one: on a managed lane it passes
that check during the dry run, so ``front-utility all`` would run the cloud smoke, and
``all-frontend`` seven specs of other categories twice. ``_common.add_test(...,
named_only=True)`` stores ``named_only: True`` and ``in_all`` False (without it, or
with ``named_only=False``: no ``named_only`` key, ``in_all`` as given), and
``group_frontend_units`` leaves a ``named_only`` action out, whatever it launches.
Pure: throwaway category dicts; a fake frontend category through
``monkeypatch.setitem``, ``collect_launches`` stubbed; and on the real catalogue the
real dry run, which launches nothing, behind a recorder, in a lane exporting what
``--lane-setting LIBREFOLIO_PROFILE=managed`` exports (the profile, and the lane
settings that carry it through the ``configure_test_runtime()`` the dry run's ``db``
actions run in this process) or neither, the whole environment put back afterwards.

The H-25 regressions pin which invocations the parallel pre-pass serves. With
``--workers`` above 1, ``_cli._run_parallel_prepass`` handed the whole category to
``_parallel_for_scope`` whatever the action and the test names:
``--workers 2 services client-address`` ran every parallel-safe ``services`` unit,
behind the category's setup (``db create``, which empties the lane's database), and
``--workers 4 services all -k foo`` ran them all, ignoring ``-k``.
``_cli._parallel_prepass_applies(args)`` is the consolidated pre-passes' rule
(``_backend_consolidation_scope``) for the parallel one: False when ``test_names`` is
non-empty, else True for an ``action`` that is None, absent or ``all``, else False;
``test_names`` absent (the ``all`` / ``all-backend`` parsers declare none), None or
``[]`` all mean no test names. ``_run_parallel_prepass`` asks it, looked up on ``_cli``
when it runs, and on False returns ``(True, set())`` calling nothing; otherwise it is
unchanged: one ``_parallel_for_scope(args, category, workers, verbose)`` for a backend
registry category, its verdict passed back; none for a frontend category or
``all-frontend``; one per ``CONSOLIDATABLE`` category, in order, for ``all`` /
``all-backend``. Through ``_apply_parallel`` with ``--workers 2``, one action or a
``-k`` filter reaches neither the parallel pass nor a setup, and leaves the serial pass
nothing to skip. Pure: ``_parallel_for_scope`` and both consolidated pre-passes are
recorders; ``run_category_setup``, ``plan``, ``run_groups`` and ``subprocess.run``
fail the test if reached.

The H-26 regressions pin how test names given to an action registered without them
are refused. Every registry category's parser takes positional ``test_names``, and
``run_test_from_registry`` hands them only to an action registered ``test_names=True``;
the others dropped them and ran whole: ``services all test_foo`` ran every ``services``
unit, ``external all yfinance`` every provider, ``db populate --force --clean extra``
repopulated the lane in silence. ``_cli._refused_test_names(args)`` is the rule, pure:
None without test names (``test_names`` absent, None or ``[]``), for a category or an
action ``TEST_REGISTRY`` does not hold (the suites and ``check-orphans`` declare
neither attribute; argparse answers for those) and for an action whose entry takes
names; otherwise the refusal, which names the category and every name given, then says
"name the action" for ``all``, or names the action and says "takes no test names".
``dev.py test``'s ``_dispatch_test_command`` and the standalone ``main()`` ask it first,
``--list`` included, before ``tee_output``, ``_activate_log_dir``, ``_timed_run`` and
``_snapshot_log_dir_db``: a refusal goes through ``print_error`` and the entry returns
2, which ``dev.py`` and ``python -m scripts.test_runner`` exit with. Pure: the
arguments come from the real parsers; every seam an entry reaches before or instead of
a run, ``subprocess.run`` and ``Popen`` included, fails the test if reached; ``dev`` is
imported by its one case only, with the working directory and ``sys.path`` put back.

The H-30 regressions pin that a body that raises still leaves the lane's database
snapshotted next to the logs. With ``--log-file``, the standalone ``main()`` called
``_snapshot_log_dir_db()`` after ``_timed_run``, outside any ``finally``: a body that
raised skipped it, and the run that crashed, the one whose database is evidence, left
none. ``_dispatch_test_command`` (``dev.py test``) has the ``finally`` in both branches.
Both entries, with ``--log-file`` or without, call ``_snapshot_log_dir_db`` once, after
the body, inside the log's tee when there is one, and let the body's exception through.
Pure: H-26's ``entry_steps`` (every seam closed, the entry's steps recorded), a
``tee_output`` that only records, and a body answering 0 or raising ``H30BodyCrash``.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib
import os
import re
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.test_runner import _backend_api as backend_api
from scripts.test_runner import _backend_db as backend_db
from scripts.test_runner import _backend_services as backend_services
from scripts.test_runner import _backend_utils as backend_utils
from scripts.test_runner import _cli as runner_cli
from scripts.test_runner import _common, _consolidate, _executor, _frontend_common, _frontend_utility, _inventory, _scheduler
from scripts.test_runner._consolidate_backend import CONSOLIDATABLE, _junit_results
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


# ── H-43: an action that runs only when named stays out of the consolidated frontend pass ─────────────────────────────
# ``add_test`` is called with ``named_only`` through ``_registered``: while it does not take the keyword, those cases
# fail on the named "H-43: add_test takes no named_only" barrier, and the cases that leave it out are guards, green
# before and after. The fake category's named-only entry is written by hand, as the cure's ``add_test`` stores it, so
# its cases reach ``group_frontend_units`` today: three of them fail there, on what the named-only action claims, and
# the in_all=False one is a guard, green before and after. On the real catalogue the managed lane fails today on the
# cloud smoke's specs in front-utility's group; the self-hosted lane is a control, green before and after: there the
# cloud smoke refuses during the dry run, before it launches anything. That dry run reconfigures the lane in this
# process (its ``db`` actions run ``configure_test_runtime()``, which drops the instance's settings, the profile
# included): the managed lane exports what ``--lane-setting`` does, the profile and the lane settings carrying it, and
# ``lane_environ`` puts the whole environment back.

#: A keyword left out of the ``add_test`` call, which then stores the keyword's default.
H43_NOT_GIVEN = object()
#: ``in_all`` left out of the call, or given either way.
H43_IN_ALL_GIVEN = [pytest.param(H43_NOT_GIVEN, id="in-all-not-given"), pytest.param(True, id="in-all-true"), pytest.param(False, id="in-all-false")]
#: A frontend category of these tests only: ``group_frontend_units`` keeps the categories whose name starts with ``front``.
H43_CATEGORY = "front-h43-fake-category"
#: Its three actions: one every ``all`` runs (front-utility auth, front-ai-export cutover); one registered
#: ``in_all=False`` because another action runs its spec in one invocation (front-ai-export panel, whose spec cutover
#: runs); one registered ``named_only`` (front-utility cloud-smoke).
H43_IN_ALL = "h43-in-all"
H43_NOT_IN_ALL = "h43-not-in-all"
H43_NAMED_ONLY = "h43-named-only"
#: What they launch, each unit named after the actions that launch it. In front-utility the cloud smoke shares
#: auth.spec.ts with auth, and launches portfolio/dashboard.spec.ts alone.
H43_SPEC_IN_ALL_AND_NOT_IN_ALL = "h43/in-all-and-not-in-all.spec.ts"
H43_SPEC_IN_ALL_AND_NAMED_ONLY = "h43/in-all-and-named-only.spec.ts"
H43_SPEC_NAMED_ONLY_ALONE = "h43/named-only-alone.spec.ts"
H43_VITEST_NAMED_ONLY_ALONE = "src/lib/h43-named-only-alone.test.ts"
#: What ``collect_launches`` answers for the fake category, in its own shape: the named-only action's launches are
#: reported, as the real dry run reports the cloud smoke's on a managed lane.
H43_LAUNCHES = {
    (H43_CATEGORY, H43_IN_ALL): [("playwright", H43_SPEC_IN_ALL_AND_NAMED_ONLY, "desktop"), ("playwright", H43_SPEC_IN_ALL_AND_NOT_IN_ALL, "desktop")],
    (H43_CATEGORY, H43_NOT_IN_ALL): [("playwright", H43_SPEC_IN_ALL_AND_NOT_IN_ALL, "desktop")],
    (H43_CATEGORY, H43_NAMED_ONLY): [("playwright", H43_SPEC_IN_ALL_AND_NAMED_ONLY, "desktop"), ("playwright", H43_SPEC_NAMED_ONLY_ALONE, "desktop"), ("vitest", H43_VITEST_NAMED_ONLY_ALONE, "")],
}
#: The scopes ``group_frontend_units`` is asked for the fake category: the category's own ``all``, and ``all-frontend``.
H43_FAKE_SCOPES = [pytest.param(H43_CATEGORY, id="category-all"), pytest.param(None, id="all-frontend")]
#: The cloud smoke's category and action, as the catalogue and ``collect_launches`` key them.
H43_UTILITY = "front-utility"
H43_CLOUD_SMOKE = "cloud-smoke"
#: The scopes ``group_frontend_units`` is asked on the real catalogue: ``front-utility all``, and ``all-frontend``.
H43_REAL_SCOPES = [pytest.param(H43_UTILITY, id="front-utility-all"), pytest.param(None, id="all-frontend")]
#: What ``--lane-setting LIBREFOLIO_PROFILE=managed`` exports to every process of a lane: the profile, and the variable
#: carrying the lane's settings (``cli_base.TEST_LANE_SETTINGS``, spelled here, pinned by ``utils runtime-isolation``),
#: which every nested ``configure_test_runtime()`` applies again after dropping the instance's settings. The dry run runs
#: one before it reaches front-utility (its ``db`` actions ask ``get_test_db_path()``): the profile alone would be gone
#: by the time the cloud smoke checks it. A self-hosted lane exports neither.
H43_MANAGED_LANE = {"LIBREFOLIO_PROFILE": "managed", "LIBREFOLIO_TEST_LANE_SETTINGS": "LIBREFOLIO_PROFILE=managed"}


@pytest.fixture
def lane_environ(monkeypatch):
    """``monkeypatch``, and the whole environment put back after the test, whatever the real dry run changed in it.

    The dry run reconfigures the lane in this process: its ``db`` actions ask ``get_test_db_path()``, which runs
    ``configure_test_runtime()`` (the instance's settings dropped, the lane's own applied again, port, data directory and
    test mode exported). Inside a lane that changes nothing; run anywhere else it would, and no later test may inherit it.
    """
    snapshot = dict(os.environ)
    yield monkeypatch
    os.environ.clear()
    os.environ.update(snapshot)


def _never_run(action: str):
    """The function registered for ``action``: it fails the test if anything runs it."""

    def run(*_args, **_kwargs):
        pytest.fail(f"{action}: an action of the H-43 tests ran; add_test only stores it, and group_frontend_units reads what it launches from the stubbed collect_launches")

    return run


def _given(**keywords) -> dict:
    """``keywords`` but those left out of the call (``H43_NOT_GIVEN``)."""
    return {name: value for name, value in keywords.items() if value is not H43_NOT_GIVEN}


def _shown(**keywords) -> str:
    """The keywords given, as the call reads them (``named_only=True, in_all=False``), or ``no keyword``."""
    return ", ".join(f"{name}={value!r}" for name, value in _given(**keywords).items()) or "no keyword"


def _registered(action: str, **keywords) -> dict:
    """The entry ``_common.add_test`` stores for ``action`` in a throwaway category dict, given ``keywords``.

    The H-43 barrier while ``add_test`` takes no ``named_only``; a ``TypeError`` about anything else goes through.
    """
    category: dict = {}
    try:
        _common.add_test(category, action, _never_run(action), name=f"H-43 {action}", desc="An action of this test only", **_given(**keywords))
    except TypeError as exc:
        if "named_only" not in str(exc):
            raise
        pytest.fail(f"H-43: add_test takes no named_only ({exc}): an action cannot say it runs only when named, and the consolidated pass has nothing to read")
    return category[action]


def _register_h43_category(monkeypatch) -> None:
    """The fake category, built with the real ``make_category``/``add_test`` and injected with ``monkeypatch.setitem``.

    The named-only action is registered ``in_all=False`` and given ``named_only: True`` by hand: the entry the cure's
    ``add_test(..., named_only=True)`` stores. These cases reach ``group_frontend_units`` even while ``add_test`` does
    not take the keyword (that is ``TestAddTestStoresNamedOnly``'s barrier, not theirs).
    """
    category = _common.make_category("H-43 fake category", "A frontend category of this test only")
    _common.add_test(category, H43_IN_ALL, _never_run(H43_IN_ALL), name="H-43 in every all", desc="Run by every all, as front-utility auth or front-ai-export cutover")
    _common.add_test(category, H43_NOT_IN_ALL, _never_run(H43_NOT_IN_ALL), name="H-43 run by another action", desc="Its spec run by another action in one invocation, as front-ai-export panel", in_all=False)
    _common.add_test(category, H43_NAMED_ONLY, _never_run(H43_NAMED_ONLY), name="H-43 named only", desc="Run only when named, as front-utility cloud-smoke", in_all=False)
    category[H43_NAMED_ONLY]["named_only"] = True
    monkeypatch.setitem(TEST_REGISTRY, H43_CATEGORY, category)


def _claims(group: dict) -> dict[tuple[str, str, str], list[str]]:
    """One category's consolidated group, flat: ``{(kind, project, path): sorted claimants}``, project '' for vitest."""
    claims = {("playwright", project, path): sorted(actions) for project, specs in group["playwright"].items() for path, actions in specs.items()}
    claims.update({("vitest", "", path): sorted(actions) for path, actions in group["vitest"].items()})
    return claims


def _h43_claims(monkeypatch, scope: str | None) -> dict[tuple[str, str, str], list[str]]:
    """The fake category's group, flat, from ``group_frontend_units(scope)`` with ``collect_launches`` answering ``H43_LAUNCHES``."""
    _register_h43_category(monkeypatch)
    _stub_launches(monkeypatch, H43_LAUNCHES)

    groups = _consolidate.group_frontend_units(scope)

    assert set(groups) == {H43_CATEGORY}, f"precondition: group_frontend_units must group the stubbed launches, the fake category's alone (groups: {sorted(groups)})"
    return _claims(groups[H43_CATEGORY])


def _record_real_launches(monkeypatch) -> SimpleNamespace:
    """``_inventory.collect_launches`` behind a recorder that runs the real dry run and keeps what it answered.

    The real one invokes every action of the catalogue but ``all`` with every launch point replaced by a collector, the
    side-effecting actions neutralised and any deletion refused (``_inventory._collecting``): it launches nothing, as on
    every run of the consolidated passes and the scheduler. ``group_frontend_units`` imports it from ``_inventory`` when
    it runs, so the recorder is what it calls.
    """
    real_collect = _inventory.collect_launches
    seen = SimpleNamespace(calls=0, launches={}, errors={})

    def record(only_all: bool = False):
        seen.calls += 1
        seen.launches, seen.errors = real_collect(only_all=only_all)
        return seen.launches, seen.errors

    monkeypatch.setattr(_inventory, "collect_launches", record)
    return seen


def _front_groups_on_lane(lane_environ, lane: dict[str, str], scope: str | None) -> tuple[dict, SimpleNamespace]:
    """``group_frontend_units(scope)`` on the real catalogue, in a lane exporting ``lane`` alone of ``H43_MANAGED_LANE``'s names, and what its dry run answered."""
    for name in H43_MANAGED_LANE:
        lane_environ.delenv(name, raising=False)
    for name, value in lane.items():
        lane_environ.setenv(name, value)
    seen = _record_real_launches(lane_environ)

    groups = _consolidate.group_frontend_units(scope)

    assert seen.calls == 1, f"precondition: group_frontend_units must read the launches from _inventory.collect_launches when it runs, once (read {seen.calls} time(s))"
    assert seen.errors == {}, f"precondition: the dry run reported errors, and group_frontend_units answers {{}} on any, where every negative below would hold: {seen.errors}"
    assert H43_UTILITY in groups, f"precondition: front-utility's consolidated group must exist, or the negatives below prove nothing (groups: {sorted(groups)})"
    return groups, seen


def _launched_specs(launches: dict, keep) -> dict[str, list[str]]:
    """``{spec: ["category action", …]}``: the Playwright specs the ``(category, action)`` pairs ``keep`` accepts launch, in the groups' form (``_norm_spec``)."""
    specs: dict[str, set[str]] = {}
    for (category, action), units in launches.items():
        if not keep(category, action):
            continue
        for engine, path, _project in units:
            if engine == "playwright":
                specs.setdefault(_consolidate._norm_spec(path), set()).add(f"{category} {action}")
    return {spec: sorted(owners) for spec, owners in specs.items()}


def _cloud_smoke_specs() -> set[str]:
    """``_frontend_utility.CLOUD_SMOKE_SPECS`` in the groups' form (``_norm_spec``)."""
    return {_consolidate._norm_spec(spec) for spec in _frontend_utility.CLOUD_SMOKE_SPECS}


def _foreign_smoke_specs(seen) -> dict[str, list[str]]:
    """The cloud smoke's specs no other front-utility action launches, each with the actions of other categories that do.

    Computed, not listed: ``CLOUD_SMOKE_SPECS`` less what front-utility's other actions launch in the dry run ``seen``
    recorded, so a spec added to the smoke is covered as well.
    """
    utility = _launched_specs(seen.launches, lambda category, action: category == H43_UTILITY and action != H43_CLOUD_SMOKE)
    elsewhere = _launched_specs(seen.launches, lambda category, _action: category != H43_UTILITY)
    foreign = {spec: elsewhere.get(spec, []) for spec in sorted(_cloud_smoke_specs() - set(utility))}
    assert foreign, f"precondition: front-utility's other actions launch every spec of CLOUD_SMOKE_SPECS, so no spec of another category is at stake here ({sorted(_cloud_smoke_specs())})"
    return foreign


def _assert_nothing_of_the_cloud_smoke_in(groups: dict, foreign: dict[str, list[str]], lane: str, scope: str | None) -> None:
    """front-utility's consolidated group holds none of the ``foreign`` specs, and none of its units is claimed by the cloud smoke."""
    suite = "all-frontend" if scope is None else f"{scope} all"
    claims = _claims(groups[H43_UTILITY])
    paths = {path for _kind, _project, path in claims}
    held = {spec: owners for spec, owners in foreign.items() if spec in paths}
    assert held == {}, f"H-43: on a {lane} lane, {suite} would run in front-utility's consolidated invocation specs only the cloud smoke launches there, which these actions of their own categories run already: {held}"
    claimed = sorted(unit for unit, actions in claims.items() if H43_CLOUD_SMOKE in actions)
    assert claimed == [], f"H-43: on a {lane} lane, {suite} would run front-utility cloud-smoke, which claims {claimed} in the consolidated group: it runs only when named (named_only)"


class TestAddTestStoresNamedOnly:
    """``add_test(..., named_only=True)``: the entry says so, ``named_only: True``, and is in no ``all``, ``in_all`` False.

    Without it, or with ``named_only=False``, the entry has no ``named_only`` key, as ``prereq``, ``tests``, ``note`` and
    ``isolation`` have none when not given, and its ``in_all`` is the one given, True by default.
    """

    @pytest.mark.parametrize("in_all", H43_IN_ALL_GIVEN)
    def test_named_only_is_stored_and_leaves_the_action_out_of_every_all(self, in_all):
        entry = _registered(H43_NAMED_ONLY, named_only=True, in_all=in_all)

        shown = _shown(named_only=True, in_all=in_all)
        assert entry.get("named_only") is True, f"H-43: add_test with {shown} stored named_only={entry.get('named_only')!r}: the consolidated pass reads it to leave out an action that runs only when named"
        assert entry["in_all"] is False, f"H-43: add_test with {shown} stored in_all={entry['in_all']!r}: an action that runs only when named is in no all, whatever in_all it is given, and the serial all reads in_all"

    @pytest.mark.parametrize("named_only", [pytest.param(H43_NOT_GIVEN, id="named-only-not-given"), pytest.param(False, id="named-only-false")])
    @pytest.mark.parametrize("in_all", H43_IN_ALL_GIVEN)
    def test_without_named_only_there_is_no_key_and_in_all_is_the_one_given(self, named_only, in_all):
        """Left out, green before and after; ``named_only=False``, on the barrier until ``add_test`` takes the keyword."""
        entry = _registered(H43_IN_ALL, named_only=named_only, in_all=in_all)

        shown = _shown(named_only=named_only, in_all=in_all)
        expected = True if in_all is H43_NOT_GIVEN else in_all
        assert "named_only" not in entry, f"H-43: add_test with {shown} stored named_only={entry['named_only']!r}: the key is stored only when named_only is set"
        assert entry["in_all"] is expected, f"H-43: add_test with {shown} stored in_all={entry['in_all']!r}, not {expected}: without named_only, in_all is the one given, True by default"


@pytest.mark.parametrize("scope", H43_FAKE_SCOPES)
class TestGroupFrontendUnitsLeavesANamedOnlyActionOut:
    """``group_frontend_units`` groups what the dry run reports of every action but one registered ``named_only``.

    ``collect_launches`` reports the named-only action's launches (``H43_LAUNCHES``), as the real dry run reports the
    cloud smoke's on a managed lane. The action must claim nothing, a unit only it launches must stay out of the group,
    and a spec another action launches too must stay in, claimed by that action alone. An ``in_all=False`` action is no
    named-only one: it stays a claimant, as the AI Export and Designer Lab per-spec actions must, to keep a verdict and a
    ``--resume`` entry of their own. Each case runs for the category's ``all`` and for ``all-frontend``.
    """

    def test_a_named_only_action_claims_nothing(self, monkeypatch, scope):
        claims = _h43_claims(monkeypatch, scope)

        claimed = sorted(unit for unit, actions in claims.items() if H43_NAMED_ONLY in actions)
        assert claimed == [], f"H-43: {H43_NAMED_ONLY}, registered named_only, claims {claimed} in the consolidated group: the pass would run it and give it a verdict, though only a command line naming it may run it"

    def test_a_unit_only_a_named_only_action_launches_is_left_out(self, monkeypatch, scope):
        claims = _h43_claims(monkeypatch, scope)

        held = sorted({H43_SPEC_NAMED_ONLY_ALONE, H43_VITEST_NAMED_ONLY_ALONE} & {path for _kind, _project, path in claims})
        assert held == [], f"H-43: the consolidated group holds {held}, which only {H43_NAMED_ONLY}, registered named_only, launches: the category's all and all-frontend would run them"

    def test_a_spec_shared_with_a_named_only_action_stays_claimed_by_the_other_action_alone(self, monkeypatch, scope):
        claims = _h43_claims(monkeypatch, scope)

        claimants = claims.get(("playwright", "desktop", H43_SPEC_IN_ALL_AND_NAMED_ONLY))
        assert claimants == [H43_IN_ALL], f"H-43: {H43_SPEC_IN_ALL_AND_NAMED_ONLY} must stay in the group, claimed by {H43_IN_ALL} alone, as front-utility's auth.spec.ts by auth alone (claimed by: {claimants})"

    def test_an_in_all_false_action_stays_a_claimant(self, monkeypatch, scope):
        """Guard, green before and after: ``in_all=False`` is not ``named_only``."""
        claims = _h43_claims(monkeypatch, scope)

        claimants = claims.get(("playwright", "desktop", H43_SPEC_IN_ALL_AND_NOT_IN_ALL))
        expected = sorted([H43_IN_ALL, H43_NOT_IN_ALL])
        assert claimants == expected, f"{H43_NOT_IN_ALL}, registered in_all=False, must stay a claimant of {H43_SPEC_IN_ALL_AND_NOT_IN_ALL} beside {H43_IN_ALL}, as front-ai-export panel beside cutover (claimed by: {claimants})"


@pytest.mark.parametrize("scope", H43_REAL_SCOPES)
class TestTheCloudSmokeStaysOutOfTheConsolidatedPass:
    """On the real catalogue and the real dry run, front-utility's consolidated group holds nothing of the cloud smoke.

    The lane's variables (``H43_MANAGED_LANE``) are set or removed through ``lane_environ``, which puts the whole
    environment back. The specs at stake are those of ``CLOUD_SMOKE_SPECS`` front-utility's other actions do not
    launch, computed from the same dry run: seven on today's catalogue, the dashboard's and the brokers' among them,
    which their own categories run. Each case runs for ``front-utility all`` and for ``all-frontend``.
    """

    def test_on_a_managed_lane_the_cloud_smoke_is_not_consolidated(self, lane_environ, scope):
        groups, seen = _front_groups_on_lane(lane_environ, H43_MANAGED_LANE, scope)
        smoke = _launched_specs(seen.launches, lambda category, action: (category, action) == (H43_UTILITY, H43_CLOUD_SMOKE))
        assert set(smoke) == _cloud_smoke_specs(), f"precondition: on a managed lane the cloud smoke passes its profile check during the dry run and reports every spec of CLOUD_SMOKE_SPECS, or the negatives below hold for the wrong reason (reported: {sorted(smoke)})"

        _assert_nothing_of_the_cloud_smoke_in(groups, _foreign_smoke_specs(seen), "managed", scope)

    def test_on_a_self_hosted_lane_the_cloud_smoke_is_not_consolidated_either(self, lane_environ, scope):
        """Control, green before and after: there the cloud smoke refuses during the dry run, before it launches anything."""
        groups, seen = _front_groups_on_lane(lane_environ, {}, scope)

        _assert_nothing_of_the_cloud_smoke_in(groups, _foreign_smoke_specs(seen), "self-hosted", scope)


# ── H-25: the parallel pre-pass serves a whole category or a whole suite, as the consolidated pre-passes do ────────────
# ``_cli._parallel_prepass_applies`` is looked up at call time: while it is missing, its own cases fail on the named
# "H-25: _parallel_prepass_applies is missing" barrier and leave the cases above alone. ``_parallel_for_scope`` is a
# recorder in every case, and what a real pass reaches behind it (the category's setup, the plan, the workers, a
# subprocess) fails the test if reached. Every case expecting no parallel pass first proves, on the same recorder, that
# the whole category or suite does run one (a presence barrier). Today's code runs it whatever the action and the test
# names: each case naming one action or test names fails on the "H-25: the parallel pre-pass ran for …" barrier, and the
# case whose stand-in rule says yes fails on the rule never being asked.

#: ``test_names`` absent from ``args``, as the ``all`` / ``all-backend`` parsers build them: they declare no test names.
NO_TEST_NAMES_ATTRIBUTE = object()
#: What the recorded ``_parallel_for_scope`` reports covered for each scope it is asked for: ``(scope, H25_COVERED_ACTION)``.
H25_COVERED_ACTION = "h25-covered-action"
#: The workers handed to ``_run_parallel_prepass`` directly: not 2, so a count fixed in the code would show.
H25_WORKERS = 3
#: ``--workers 2`` as argparse hands it to ``_apply_parallel``: a string, which ``_scheduler.resolve_workers`` reads as 2.
H25_APPLY_WORKERS = "2"
#: Positional test names after the action: the runner turns them into a pytest ``-k`` filter.
H25_TEST_NAMES = ("foo",)
#: An existing ``utils`` action: this file's own, pinned by ``TestSelfRegistrationInTheCatalogue``.
H25_UTILS_ACTION = "test-runner-cli"
#: A frontend registry category, which the parallel pre-pass never serves.
H25_FRONTEND_CATEGORY = "front-utility"
#: A whole registry category, or a whole suite, as ``(category, action)``: the suites' parsers declare no ``action``.
H25_WHOLE = [
    pytest.param("services", "all", id="action-all"),
    pytest.param("services", None, id="action-none"),
    pytest.param("all-backend", NO_ACTION_ATTRIBUTE, id="action-missing"),
]
#: No test names: the attribute absent, None, or the empty list a registry category's parser gives without names.
H25_NO_TEST_NAMES = [
    pytest.param(NO_TEST_NAMES_ATTRIBUTE, id="names-missing"),
    pytest.param(None, id="names-none"),
    pytest.param([], id="names-empty"),
]


def _parallel_prepass_applies():
    """``_cli._parallel_prepass_applies``, looked up at call time, or the H-25 barrier while it is missing."""
    applies = getattr(runner_cli, "_parallel_prepass_applies", None)
    if applies is None:
        pytest.fail("H-25: _parallel_prepass_applies is missing")
    return applies


def _prepass_args(category: str, action=NO_ACTION_ATTRIBUTE, test_names=NO_TEST_NAMES_ATTRIBUTE, **extra) -> SimpleNamespace:
    """The ``args`` of ``dev.py test [--workers N] <category> [<action> [<test name>…]]``; a sentinel leaves its attribute absent.

    A registry category's parser always sets ``action`` and ``test_names`` (``[]`` without names); the ``all`` /
    ``all-backend`` parsers set neither. ``test_names`` is copied: no two cases share a list.
    """
    fields = {"category": category, **extra}
    if action is not NO_ACTION_ATTRIBUTE:
        fields["action"] = action
    if test_names is not NO_TEST_NAMES_ATTRIBUTE:
        fields["test_names"] = None if test_names is None else list(test_names)
    return SimpleNamespace(**fields)


def _whole(category: str) -> SimpleNamespace:
    """The ``args`` of the whole ``category`` (``<category> all``, no test names), or of the whole suite it names."""
    if category in TEST_REGISTRY:
        return _prepass_args(category, "all", [])
    return _prepass_args(category)


def _invocation(args) -> str:
    """``args`` as the command line reads, for a barrier message: ``services client-address``, ``all-backend -k foo``."""
    words = [f"--workers {args.workers}"] if hasattr(args, "workers") else []
    words.append(args.category)
    action = getattr(args, "action", None)
    if action:
        words.append(action)
    names = getattr(args, "test_names", None)
    if names:
        words += ["-k", " or ".join(names)]
    return " ".join(words)


def _scopes(recorder) -> list:
    """The scopes the recorded ``_parallel_for_scope`` was asked for, in order."""
    return [scope for _args, scope, _workers, _verbose in recorder.calls]


def _unreachable(what: str):
    """A stand-in for ``what`` that fails the test the moment anything calls it."""

    def fail_if_reached(*call_args, **_kwargs):
        pytest.fail(f"{what} was reached past the _parallel_for_scope recorder (called with {call_args}): a real parallel pass ran its setup, its plan or its workers against the lane; for services the setup is db create, which empties the lane's database")

    return fail_if_reached


@pytest.fixture
def parallel_pass(monkeypatch):
    """``_cli._parallel_for_scope`` behind a recorder; what a real parallel pass reaches behind it fails the test if reached.

    ``_run_parallel_prepass`` looks ``_parallel_for_scope`` up among ``_cli``'s globals when it runs, so the recorder is
    what it calls. Each call is recorded as ``(args, scope, workers, verbose)`` and answered
    ``(parallel_pass.ok, {(scope, H25_COVERED_ACTION)})``. A real pass runs the category's setup through
    ``_common.run_category_setup``, plans through ``_scheduler.plan`` and spawns its workers through
    ``_executor.run_groups``: all three, and ``subprocess.run``, are replaced where the runner looks them up.
    """
    recorder = SimpleNamespace(calls=[], ok=True)

    def record(args, scope, workers, verbose):
        recorder.calls.append((args, scope, workers, verbose))
        return recorder.ok, {(scope, H25_COVERED_ACTION)}

    monkeypatch.setattr(runner_cli, "_parallel_for_scope", record)
    monkeypatch.setattr(_common, "run_category_setup", _unreachable("_common.run_category_setup"))
    monkeypatch.setattr(_scheduler, "plan", _unreachable("_scheduler.plan"))
    monkeypatch.setattr(_executor, "run_groups", _unreachable("_executor.run_groups"))
    monkeypatch.setattr(_common.subprocess, "run", _unreachable("subprocess.run"))
    return recorder


@pytest.fixture
def consolidation_passes(monkeypatch):
    """Both consolidated pre-passes behind recorders answering ``(True, set())``, and the runner's process-wide sets kept.

    ``_apply_parallel`` runs them after the parallel pre-pass: the backend one would launch a whole category's pytest, the
    frontend one Playwright. The backend one is recorded with what it was told to skip. ``_apply_parallel`` also writes
    ``_common._E2E_WORKERS`` and ``_common._SKIP_ACTIONS``: monkeypatch puts them back.
    """
    passes = SimpleNamespace(backend=[], frontend=[])

    def backend(args, verbose, skip):
        passes.backend.append(set(skip))
        return True, set()

    def frontend(args, verbose):
        passes.frontend.append(args)
        return True, set()

    monkeypatch.setattr(runner_cli, "_run_backend_consolidation_prepass", backend)
    monkeypatch.setattr(runner_cli, "_run_consolidation_prepass", frontend)
    monkeypatch.setattr(_common, "_E2E_WORKERS", _common._E2E_WORKERS)
    monkeypatch.setattr(_common, "_SKIP_ACTIONS", set())
    monkeypatch.setattr(_common, "_FAILED_ACTIONS", set())
    return passes


def _assert_the_whole_runs_a_parallel_pass(category: str, recorder) -> None:
    """Presence barrier: the whole ``category``, or the whole suite, reaches the recorder, so a case expecting no pass has teeth.

    The recorder is emptied afterwards: the case starts as if nothing had run.
    """
    whole = _whole(category)

    runner_cli._run_parallel_prepass(whole, H25_WORKERS, False)

    assert recorder.calls, f"precondition: the parallel pre-pass for {_invocation(whole)} must reach the _parallel_for_scope recorder, or a case expecting none proves nothing"
    recorder.calls.clear()


def _assert_no_parallel_pass(args, recorder, result) -> None:
    """The H-25 barrier: one action, or test names, and the pre-pass runs nothing and covers nothing."""
    assert recorder.calls == [], f"H-25: the parallel pre-pass ran for {_invocation(args)} (scopes: {_scopes(recorder)}); it serves a whole category or a whole suite only, as the consolidated pre-passes do"
    assert result == (True, set()), f"no parallel pass ran for {_invocation(args)}: nothing failed and nothing is covered (got {result!r})"


def _assert_apply_parallel_runs_one_pass_for_the_whole_category(monkeypatch, recorder, passes) -> None:
    """``--workers 2 services all`` through ``_apply_parallel``: one pass for ``services``, whose coverage both later passes skip.

    Also the presence barrier of the cases expecting no pass: the recorders and ``_SKIP_ACTIONS`` are emptied afterwards.
    """
    args = _prepass_args("services", "all", [], workers=H25_APPLY_WORKERS)
    covered = {("services", H25_COVERED_ACTION)}

    result = runner_cli._apply_parallel(args, False)

    assert recorder.calls == [(args, "services", 2, False)], f"one parallel pass for services, with the 2 workers --workers 2 asks for (calls: {recorder.calls})"
    assert result == (True, True)
    assert passes.backend == [covered], f"the consolidated backend pre-pass skips what the parallel pass covered (asked with: {passes.backend})"
    assert _common._SKIP_ACTIONS == covered, f"and so does the serial pass (skips: {_common._SKIP_ACTIONS})"
    recorder.calls.clear()
    passes.backend.clear()
    passes.frontend.clear()
    monkeypatch.setattr(_common, "_SKIP_ACTIONS", set())


class TestParallelPrepassApplies:
    """Contract point 1: ``_cli._parallel_prepass_applies(args)``, the consolidated pre-passes' rule for the parallel one.

    A whole category or a whole suite applies: ``action`` None, absent or ``all``, and no test names (``test_names``
    absent, None or ``[]``). One named action does not; any test name does not, whatever the action.
    """

    @pytest.mark.parametrize("test_names", H25_NO_TEST_NAMES)
    @pytest.mark.parametrize(("category", "action"), H25_WHOLE)
    def test_the_whole_category_or_suite_without_test_names_applies(self, category, action, test_names):
        applies = _parallel_prepass_applies()

        assert applies(_prepass_args(category, action, test_names)) is True

    @pytest.mark.parametrize("test_names", H25_NO_TEST_NAMES)
    def test_one_named_action_does_not_apply(self, test_names):
        applies = _parallel_prepass_applies()

        assert applies(_prepass_args("services", SERVICES_PURE_ACTION, test_names)) is False

    @pytest.mark.parametrize(("category", "action"), [*H25_WHOLE, pytest.param("services", SERVICES_PURE_ACTION, id="named-action")])
    def test_test_names_never_apply(self, category, action):
        applies = _parallel_prepass_applies()

        assert applies(_prepass_args(category, action, H25_TEST_NAMES)) is False


@pytest.mark.usefixtures("fresh_setup_done")
class TestRunParallelPrepassRunsNothingForOneActionOrTestNames:
    """Contract point 2: when the rule says no, ``_run_parallel_prepass`` returns ``(True, set())`` and calls nothing.

    No ``_parallel_for_scope``, so no plan of the whole category, no setup (``services``: ``db create``) and no worker.
    """

    @pytest.mark.parametrize(
        ("category", "action"),
        [
            pytest.param("services", SERVICES_PURE_ACTION, id="services-pure-action"),
            pytest.param("services", SERVICES_DEFAULT_ACTION, id="services-write-scoped-action"),
            pytest.param("utils", H25_UTILS_ACTION, id="utils-action"),
        ],
    )
    def test_one_action_runs_no_parallel_pass(self, parallel_pass, category, action):
        """Whatever the class the catalogue declares for the action: the rule reads the invocation, not the catalogue."""
        assert action in TEST_REGISTRY[category], f"precondition: {category} {action} is an action of the catalogue"
        _assert_the_whole_runs_a_parallel_pass(category, parallel_pass)
        args = _prepass_args(category, action, [])

        result = runner_cli._run_parallel_prepass(args, H25_WORKERS, False)

        _assert_no_parallel_pass(args, parallel_pass, result)

    @pytest.mark.parametrize(
        ("category", "action"),
        [
            pytest.param("services", "all", id="services-all"),
            pytest.param("all-backend", NO_ACTION_ATTRIBUTE, id="all-backend"),
            pytest.param("all", NO_ACTION_ATTRIBUTE, id="all"),
        ],
    )
    def test_test_names_run_no_parallel_pass_even_for_the_whole(self, parallel_pass, category, action):
        """The parallel pass knows nothing of ``-k``: it would run every parallel-safe unit of the scope instead."""
        _assert_the_whole_runs_a_parallel_pass(category, parallel_pass)
        args = _prepass_args(category, action, H25_TEST_NAMES)

        result = runner_cli._run_parallel_prepass(args, H25_WORKERS, False)

        _assert_no_parallel_pass(args, parallel_pass, result)

    def test_the_rule_is_asked_when_the_prepass_runs_and_a_no_stops_even_the_whole_category(self, monkeypatch, parallel_pass):
        """One rule, looked up on ``_cli`` when the pre-pass runs: a stand-in answering False stops ``services all`` too."""
        _assert_the_whole_runs_a_parallel_pass("services", parallel_pass)
        args = _whole("services")
        asked = []

        def say_no(prepass_args):
            asked.append(prepass_args)
            return False

        monkeypatch.setattr(runner_cli, "_parallel_prepass_applies", say_no, raising=False)

        result = runner_cli._run_parallel_prepass(args, H25_WORKERS, False)

        assert parallel_pass.calls == [], f"H-25: the parallel pre-pass ran for {_invocation(args)} although _cli._parallel_prepass_applies, looked up when it runs, answers False (asked: {asked}; scopes: {_scopes(parallel_pass)})"
        assert asked == [args], f"the rule is asked once, with the invocation's args (asked: {asked})"
        assert result == (True, set())

    def test_a_yes_from_the_rule_leaves_the_prepass_as_it_was_for_one_action(self, monkeypatch, parallel_pass):
        """Nothing but the rule decides: a stand-in answering True for one action gets today's pass, unchanged."""
        args = _prepass_args("services", SERVICES_PURE_ACTION, [])
        asked = []

        def say_yes(prepass_args):
            asked.append(prepass_args)
            return True

        monkeypatch.setattr(runner_cli, "_parallel_prepass_applies", say_yes, raising=False)

        result = runner_cli._run_parallel_prepass(args, H25_WORKERS, False)

        assert asked == [args], f"H-25: the parallel pre-pass for {_invocation(args)} did not ask _cli._parallel_prepass_applies when it ran (asked: {asked})"
        assert parallel_pass.calls == [(args, "services", H25_WORKERS, False)], f"the rule said yes: today's one pass for the category (calls: {parallel_pass.calls})"
        assert result == (True, {("services", H25_COVERED_ACTION)})


@pytest.mark.usefixtures("fresh_setup_done")
class TestRunParallelPrepassStillServesTheWholeCategoryOrSuite:
    """Contract point 2, unchanged: the whole category or suite gets the parallel pass it gets today (green before and after)."""

    @pytest.mark.parametrize("ok", [True, False], ids=["green-pass", "red-pass"])
    @pytest.mark.parametrize(
        ("action", "test_names"),
        [
            pytest.param("all", [], id="action-all"),
            pytest.param(None, None, id="action-none"),
        ],
    )
    def test_a_whole_backend_category_runs_one_pass_and_gets_its_verdict_back(self, parallel_pass, action, test_names, ok):
        parallel_pass.ok = ok
        args = _prepass_args("services", action, test_names)

        result = runner_cli._run_parallel_prepass(args, H25_WORKERS, True)

        assert parallel_pass.calls == [(args, "services", H25_WORKERS, True)], f"one pass, for the category, with the workers and the verbosity given (calls: {parallel_pass.calls})"
        assert result == (ok, {("services", H25_COVERED_ACTION)}), f"the pass's own verdict and coverage come back as they are (got {result!r})"

    @pytest.mark.parametrize("suite", ["all-backend", "all"])
    def test_a_whole_suite_runs_one_pass_per_consolidatable_category_in_order(self, parallel_pass, suite):
        assert suite not in TEST_REGISTRY, f"precondition: {suite} is a suite, not a registry category"
        args = _whole(suite)

        result = runner_cli._run_parallel_prepass(args, H25_WORKERS, False)

        assert parallel_pass.calls == [(args, category, H25_WORKERS, False) for category in CONSOLIDATABLE], f"one pass per CONSOLIDATABLE category, in the suite's order (scopes: {_scopes(parallel_pass)})"
        assert result == (True, {(category, H25_COVERED_ACTION) for category in CONSOLIDATABLE})

    @pytest.mark.parametrize(
        ("category", "in_registry"),
        [
            pytest.param(H25_FRONTEND_CATEGORY, True, id="frontend-category"),
            pytest.param("all-frontend", False, id="all-frontend"),
        ],
    )
    def test_a_frontend_scope_runs_no_pass(self, parallel_pass, category, in_registry):
        """A frontend category or ``all-frontend``, whole: the rule lets it through, and the pre-pass serves neither, as today."""
        assert (category in TEST_REGISTRY) is in_registry, f"precondition: {category} is {'a' if in_registry else 'no'} registry category"
        _assert_the_whole_runs_a_parallel_pass("services", parallel_pass)
        args = _whole(category)

        result = runner_cli._run_parallel_prepass(args, H25_WORKERS, False)

        assert parallel_pass.calls == [], f"the parallel pre-pass never serves {_invocation(args)} (scopes: {_scopes(parallel_pass)})"
        assert result == (True, set())


@pytest.mark.usefixtures("fresh_setup_done")
class TestApplyParallelLeavesOneActionToTheSerialPass:
    """Through ``_apply_parallel`` with ``--workers 2``: one action or test names reach no parallel pass and no setup.

    ``--workers`` is a string there, which ``_scheduler.resolve_workers`` reads as 2. ``parallel_pass`` fails the case if
    ``run_category_setup`` is reached; ``consolidation_passes`` keeps both consolidated pre-passes from running anything.
    """

    def test_the_whole_category_runs_one_parallel_pass(self, monkeypatch, parallel_pass, consolidation_passes):
        """Guard, green today and after: ``--workers 2 services all`` keeps its parallel pass."""
        _assert_apply_parallel_runs_one_pass_for_the_whole_category(monkeypatch, parallel_pass, consolidation_passes)

    @pytest.mark.parametrize(
        ("action", "test_names"),
        [
            pytest.param(SERVICES_PURE_ACTION, [], id="one-action"),
            pytest.param("all", H25_TEST_NAMES, id="test-names"),
        ],
    )
    def test_one_action_or_test_names_reach_no_parallel_pass_and_no_setup(self, monkeypatch, parallel_pass, consolidation_passes, action, test_names):
        _assert_apply_parallel_runs_one_pass_for_the_whole_category(monkeypatch, parallel_pass, consolidation_passes)
        args = _prepass_args("services", action, test_names, workers=H25_APPLY_WORKERS)

        result = runner_cli._apply_parallel(args, False)

        assert parallel_pass.calls == [], f"H-25: the parallel pre-pass ran for {_invocation(args)} through _apply_parallel (scopes: {_scopes(parallel_pass)}): behind it, a real pass runs the category's setup and every parallel-safe unit of the category"
        assert result == (True, True), f"nothing failed: the serial pass goes on (got {result!r})"
        assert consolidation_passes.backend == [set()], f"the consolidated backend pre-pass is still asked, with nothing to skip (asked with: {consolidation_passes.backend})"
        assert _common._SKIP_ACTIONS == set(), f"nothing was covered: the serial pass has nothing to skip (skips: {_common._SKIP_ACTIONS})"


# ── H-26: test names given to an action that takes none are refused, before anything runs ─────────────────────────────
# ``_cli._refused_test_names`` is looked up at call time: while it is missing, its own cases fail on the named
# "H-26: _refused_test_names is missing" barrier and leave the cases above alone. A case driving an entry
# (``_dispatch_test_command`` for ``dev.py test``, the standalone ``main()``, ``dev.main()``) first closes every seam
# the entry reaches before, or instead of, the body of a run (``refusal_seams``). Today's code hands the names on to the
# whole category: each refused invocation fails on the first seam it reaches ("H-26: _cli._activate_log_dir ran for
# test names …"), before a log is archived, a campaign recorded or a category run. An invocation the rule lets through
# reaches the entry's body, a recorder answering 0 (``entry_steps``): those cases are green before and after.

#: Two test names, so that "every name given" has more than one to find.
H26_NAMES = ("h26_name_a", "h26_name_b")
#: What the refusal of an ``all`` says: test names belong to one of the category's actions.
H26_NAME_THE_ACTION = "name the action"
#: What the refusal of any other action registered without test names says.
H26_TAKES_NO_NAMES = "takes no test names"
#: Every action of the live catalogue as ``(category, action)``, read once, when this module is collected.
H26_CATALOGUE = [pytest.param(category, action, id=f"{category}-{action}") for category, actions in TEST_REGISTRY.items() for action in actions if action != "_meta"]
#: A Vitest unit registered without test names (``_frontend_portfolio.populate_registry``).
H26_VITEST = ("front-portfolio", "risk-unit")
#: The sub-commands of ``dev.py test`` that are no registry category: their parsers declare neither ``action`` nor ``test_names``.
H26_NOT_CATEGORIES = ["all", "all-backend", "all-frontend", "check-orphans", "coverage", "coverage-report"]
#: A category of these tests only, injected with ``monkeypatch.setitem``, and its one action other than ``all``.
H26_FAKE_CATEGORY = "h26-fake-category"
H26_FAKE_ACTION = "h26-one"
#: Test names given to an action registered without them, as ``(words after "dev.py test", category, action, names)``.
#: The parsers read a name after a flag (``--list``, ``--clean``) as a test name all the same.
H26_REFUSED = [
    pytest.param(("services", "all", *H26_NAMES), "services", "all", H26_NAMES, id="services-all"),
    pytest.param(("services", "all", "--list", "h26_name"), "services", "all", ("h26_name",), id="services-all-list"),
    pytest.param(("db", "populate", "--force", "--clean", "h26_name"), "db", "populate", ("h26_name",), id="db-populate"),
    pytest.param(("external", "all", "yfinance"), "external", "all", ("yfinance",), id="external-all-provider-code"),
    pytest.param((*H26_VITEST, "h26_name"), *H26_VITEST, ("h26_name",), id="vitest-unit"),
]
#: Invocations the rule lets through, as ``(words, category, action, names, other attributes the parser sets)``: names
#: to an action that takes them, ``all`` without names, and provider codes, which ``--exclude-providers`` takes.
H26_LET_THROUGH = [
    pytest.param(("services", SERVICES_PURE_ACTION, "test_x"), "services", SERVICES_PURE_ACTION, ("test_x",), {}, id="names-to-an-action-taking-them"),
    pytest.param(("services", "all"), "services", "all", (), {}, id="all-without-names"),
    pytest.param(("external", "all", "--exclude-providers", "yfinance", "broker_coinbase"), "external", "all", (), {"exclude_providers": ["yfinance", "broker_coinbase"]}, id="exclude-providers-takes-the-codes"),
]
#: The seams either entry reaches before, or instead of, the body of a run, as ``(module, name)``, each looked up there
#: when called. ``_common.subprocess`` is the ``subprocess`` module itself: behind every seam, no process may start.
H26_SEAMS = (
    (_common, "tee_output"),
    (runner_cli, "_activate_log_dir"),
    (runner_cli, "_timed_run"),
    (runner_cli, "_snapshot_log_dir_db"),
    (runner_cli, "_dispatch_test_command_body"),
    (runner_cli, "_main_body"),
    (runner_cli, "_configure_runtime"),
    (runner_cli, "run_test_from_registry"),
    (runner_cli, "dispatch_to_category"),
    (_common.subprocess, "run"),
    (_common.subprocess, "Popen"),
)
#: Why a seam fails a refused invocation that reaches it.
H26_REFUSAL_FIRST = "ran for test names the action does not take: the refusal must come first, before any side effect (the real seams tee the log, archive .testLog, record the campaign and run the whole category)"
#: Why a seam fails an invocation the rule lets through that reaches it.
H26_PAST_THE_STEPS = "was reached by an invocation the rule lets through: only the entry's recorded steps and its recorded body may run here"


def _refused_test_names():
    """``_cli._refused_test_names``, looked up at call time, or the H-26 barrier while it is missing."""
    refused = getattr(runner_cli, "_refused_test_names", None)
    if refused is None:
        pytest.fail("H-26: _refused_test_names is missing")
    return refused


def _takes_test_names(category: str, action: str) -> bool:
    """Whether the catalogue's entry for ``category action`` takes test names, read as ``run_test_from_registry`` reads it."""
    return bool(TEST_REGISTRY[category][action].get("test_names", False))


def _by_value(args) -> dict:
    """``args``' attributes by value: a list is copied, so a change made to it in place shows too."""
    return {key: list(value) if isinstance(value, list) else value for key, value in vars(args).items()}


def _assert_refusal(text, category: str, action: str, names, where: str) -> None:
    """``text`` refuses ``names`` for ``category action``: substrings only, never the sentence.

    Always the category and every name given; for ``all`` "name the action", for any other action the action itself and
    "takes no test names".
    """
    shown = " ".join([category, action, *names])
    assert isinstance(text, str) and text.strip(), f"H-26: {category} {action} takes no test names, so {shown} must be refused: {where} carries no refusal (got {text!r})"
    expected = [category, *names, H26_NAME_THE_ACTION] if action == "all" else [category, action, *names, H26_TAKES_NO_NAMES]
    missing = [part for part in expected if part not in text]
    assert not missing, f"H-26: the refusal of {shown} in {where} must carry {missing} (got {text!r})"


def _assert_no_refusal(text: str) -> None:
    """Nothing in ``text`` reads as a refusal: neither of its phrases."""
    assert H26_TAKES_NO_NAMES not in text and H26_NAME_THE_ACTION not in text, f"an invocation the rule lets through is not refused (printed: {text!r})"


def _dev_test_args(*words: str) -> argparse.Namespace:
    """``dev.py test <words…>`` read by the real ``test`` parser, built and normalised as ``dev.py`` does: nothing runs."""
    parser = argparse.ArgumentParser(prog="dev.py")
    runner_cli.register_subparser(parser.add_subparsers(dest="command"))
    return parser.parse_args(runner_cli.normalize_coverage_argv(["test", *words], only_command="test"))


def _runner_args(*words: str) -> argparse.Namespace:
    """``python -m scripts.test_runner <words…>`` read by the real ``create_parser()``, as ``main()`` reads it: nothing runs."""
    return runner_cli.create_parser().parse_args(runner_cli.normalize_coverage_argv(list(words)))


def _assert_parsed(args, category: str, action: str, names, extra=None) -> None:
    """Precondition: the parser read ``category action`` with exactly ``names`` as test names, and ``extra``'s attributes."""
    parsed = (args.category, getattr(args, "action", None), getattr(args, "test_names", None))
    assert parsed == (category, action, list(names)), f"precondition: the parser must read {category} {action} with the test names {list(names)} (got {parsed})"
    for attribute, value in (extra or {}).items():
        assert getattr(args, attribute, None) == value, f"precondition: the parser must set {attribute}={value!r} (got {getattr(args, attribute, None)!r})"


def _h26_unreachable(what: str, why: str = H26_REFUSAL_FIRST):
    """A stand-in for ``what`` that fails the test, saying ``why``, the moment anything calls it."""

    def fail_if_reached(*call_args, **_kwargs):
        pytest.fail(f"H-26: {what} {why} (called with {call_args!r})")

    return fail_if_reached


def _close_seams(monkeypatch, why: str) -> None:
    """Every ``H26_SEAMS`` seam replaced, where it is looked up, by a stand-in failing the test ``why`` when reached."""
    for module, name in H26_SEAMS:
        monkeypatch.setattr(module, name, _h26_unreachable(f"{module.__name__.rpartition('.')[2]}.{name}", why))


def _steps_of(body: str) -> list[str]:
    """What an entry does for an invocation the rule lets through, in today's order, ``body`` being its own body."""
    return ["_activate_log_dir", "_timed_run", body, "_snapshot_log_dir_db"]


def _run_runner_main(monkeypatch, *words: str):
    """``python -m scripts.test_runner <words…>`` through the real ``main()``, which builds its parser and reads ``sys.argv``."""
    monkeypatch.setattr(sys, "argv", ["scripts.test_runner", *words])
    monkeypatch.delenv("_ARGCOMPLETE", raising=False)  # without it, main()'s argcomplete.autocomplete(parser) returns at once
    return runner_cli.main()


def _register_fake_category(monkeypatch, *, takes_names: bool) -> None:
    """``H26_FAKE_CATEGORY``, with ``all`` and ``H26_FAKE_ACTION`` both registered ``test_names=takes_names``.

    Built with the real ``make_category``/``add_test`` and injected with ``monkeypatch.setitem``; its actions fail the
    test if anything runs one: the rule reads the catalogue, it never runs an action.
    """
    category = _common.make_category("H-26 fake category", "A category of this test only")
    for action in ("all", H26_FAKE_ACTION):
        run = _h26_unreachable(f"{H26_FAKE_CATEGORY} {action}", "ran: the rule reads the catalogue, it never runs an action")
        _common.add_test(category, action, run, test_names=takes_names, name=f"H-26 {action}", desc="An action of the fake category")
    monkeypatch.setitem(TEST_REGISTRY, H26_FAKE_CATEGORY, category)


@pytest.fixture
def refusal_seams(monkeypatch):
    """Every seam either entry reaches before, or instead of, the body of a run, failing the test the moment it is called.

    ``tee_output`` writes ``--log-file``; ``_activate_log_dir`` archives the previous ``.testLog`` (``--log-dir`` defaults
    to it, so on every invocation); ``_timed_run`` writes the campaign record; ``_snapshot_log_dir_db`` copies the lane's
    database next to the logs; the two bodies, the lane, the registry and the category dispatch run the tests, and
    ``subprocess`` would spawn them. A refused invocation reaches none of them: today's code reaches the first one and
    fails there, never on a real run.
    """
    _close_seams(monkeypatch, H26_REFUSAL_FIRST)


@pytest.fixture
def entry_steps(monkeypatch):
    """For an invocation the rule lets through: the entry's own steps record, in order, and its body answers 0.

    ``_activate_log_dir`` and ``_snapshot_log_dir_db`` only record; ``_timed_run`` records and calls the body it is
    given; each body (``_dispatch_test_command_body(args)``, ``_main_body(parser, args)``) records itself and its
    ``args`` and answers 0. Every other seam fails the test if reached: the body is a recorder, nothing behind it runs.
    """
    _close_seams(monkeypatch, H26_PAST_THE_STEPS)
    steps = SimpleNamespace(events=[], bodies=[])

    def activate_log_dir(args):
        steps.events.append("_activate_log_dir")

    def timed_run(args, body):
        steps.events.append("_timed_run")
        return body()

    def snapshot_log_dir_db():
        steps.events.append("_snapshot_log_dir_db")

    def dispatch_test_command_body(args):
        steps.events.append("_dispatch_test_command_body")
        steps.bodies.append(args)
        return 0

    def main_body(parser, args):
        steps.events.append("_main_body")
        steps.bodies.append(args)
        return 0

    recorders = {
        "_activate_log_dir": activate_log_dir,
        "_timed_run": timed_run,
        "_snapshot_log_dir_db": snapshot_log_dir_db,
        "_dispatch_test_command_body": dispatch_test_command_body,
        "_main_body": main_body,
    }
    for name, recorder in recorders.items():
        monkeypatch.setattr(runner_cli, name, recorder)
    return steps


@pytest.fixture
def dev_module(monkeypatch):
    """``dev.py`` imported as a module, as ``test_runtime_isolation.py`` drives it, with what importing it changes put back.

    Importing ``dev`` moves the working directory to the project root and prepends to ``sys.path``, and its ``main()``
    prepends again on every call (``mkdocs_src/aphra-pipeline``, ``frontend/scripts``): ``monkeypatch.chdir`` and a copy
    of ``sys.path`` put both back after the case. Before ``args.func(args)``, ``main()`` only imports the modules that
    register its sub-parsers, registers them (reading files, writing none) and parses ``sys.argv``. ``HAS_ARGCOMPLETE``
    is off, as in ``test_runtime_isolation.py``.
    """
    monkeypatch.chdir(Path.cwd())
    monkeypatch.setattr(sys, "path", [*sys.path])
    dev = importlib.import_module("dev")
    monkeypatch.setattr(dev, "HAS_ARGCOMPLETE", False)
    return dev


class TestRefusedTestNames:
    """Contract point 1: ``_cli._refused_test_names(args)``, pure: the refusal, or None.

    None without test names (``test_names`` absent, None or ``[]``), for a category or an action ``TEST_REGISTRY`` does
    not hold (argparse answers for those), and for an action whose entry takes test names. For any test name given to an
    action registered without them, the refusal: it names the category and every name, then says "name the action" for
    ``all``, or names the action and says "takes no test names" for any other.
    """

    @pytest.mark.parametrize(("category", "action"), H26_CATALOGUE)
    def test_test_names_are_refused_exactly_where_the_catalogue_takes_none(self, capsys, category, action):
        refused = _refused_test_names()
        args = _prepass_args(category, action, H26_NAMES)
        before = _by_value(args)

        message = refused(args)

        if _takes_test_names(category, action):
            assert message is None, f"H-26: {category} {action} takes test names: {list(H26_NAMES)} must reach it, not be refused (got {message!r})"
        else:
            _assert_refusal(message, category, action, H26_NAMES, "the rule's answer")
        assert _by_value(args) == before, f"the rule is pure: it reads the arguments and changes none of them (before: {before}, after: {_by_value(args)})"
        captured = capsys.readouterr()
        assert captured.out + captured.err == "", "the rule is pure: the entries print the refusal, the rule prints nothing"

    def test_the_catalogue_holds_actions_on_both_sides_of_the_rule(self):
        """Precondition of the case above, green before and after: no count, named actions on each side of the rule.

        ``all`` and other actions registered without test names, so both refusals are exercised, and an action taking
        them, so test names that must go through are exercised too.
        """
        for category, action in [("services", "all"), ("db", "populate"), H26_VITEST]:
            assert action in TEST_REGISTRY.get(category, {}), f"precondition: {category} {action} is an action of the catalogue"
            assert not _takes_test_names(category, action), f"precondition: {category} {action} is registered without test names; anchor the rule on another action that is"
        assert _takes_test_names("services", SERVICES_PURE_ACTION), f"precondition: services {SERVICES_PURE_ACTION} takes test names; anchor the rule on another action that does"

    @pytest.mark.parametrize("test_names", H25_NO_TEST_NAMES)
    @pytest.mark.parametrize(
        ("category", "action"),
        [
            pytest.param("services", "all", id="services-all"),
            pytest.param("db", "populate", id="db-populate"),
            pytest.param(*H26_VITEST, id="vitest-unit"),
            pytest.param("services", SERVICES_PURE_ACTION, id="action-taking-names"),
        ],
    )
    def test_without_test_names_nothing_is_refused(self, category, action, test_names):
        refused = _refused_test_names()

        assert refused(_prepass_args(category, action, test_names)) is None

    @pytest.mark.parametrize("command", H26_NOT_CATEGORIES)
    def test_a_sub_command_declaring_neither_attribute_is_never_refused(self, command):
        """``all``, ``all-backend``, ``all-frontend``, ``check-orphans`` and the coverage commands take no positional names: argparse refuses extras there."""
        refused = _refused_test_names()
        assert command not in TEST_REGISTRY, f"precondition: {command} is a sub-command of dev.py test, not a registry category"

        assert refused(_prepass_args(command)) is None

    @pytest.mark.parametrize(
        ("category", "action"),
        [
            pytest.param("h26-no-such-category", "all", id="unknown-category"),
            pytest.param("services", "h26-no-such-action", id="unknown-action"),
            pytest.param("services", None, id="action-none"),
            pytest.param("all-backend", NO_ACTION_ATTRIBUTE, id="suite-without-an-action"),
        ],
    )
    def test_test_names_outside_the_catalogue_are_not_the_rules_to_refuse(self, category, action):
        """The rule judges the catalogue's actions only: a category or an action it does not hold is argparse's to answer."""
        refused = _refused_test_names()
        assert category not in TEST_REGISTRY or action not in TEST_REGISTRY[category], f"precondition: {category} {action} must be outside the catalogue"

        assert refused(_prepass_args(category, action, H26_NAMES)) is None

    def test_the_catalogue_is_read_when_asked(self, monkeypatch):
        """One definition, read from ``TEST_REGISTRY`` when the rule is asked: a category registered after import counts too."""
        refused = _refused_test_names()
        _register_fake_category(monkeypatch, takes_names=False)

        for action in ("all", H26_FAKE_ACTION):
            _assert_refusal(refused(_prepass_args(H26_FAKE_CATEGORY, action, H26_NAMES)), H26_FAKE_CATEGORY, action, H26_NAMES, "the rule's answer")

        _register_fake_category(monkeypatch, takes_names=True)

        for action in ("all", H26_FAKE_ACTION):
            message = refused(_prepass_args(H26_FAKE_CATEGORY, action, H26_NAMES))
            assert message is None, f"{H26_FAKE_CATEGORY} {action} now takes test names: the rule answered from a copy of the catalogue, it must read TEST_REGISTRY when asked (got {message!r})"


class TestDispatchTestCommandRefusesBeforeAnySideEffect:
    """Contract point 2, ``dev.py test``: ``_dispatch_test_command`` asks the rule first and returns 2 on a refusal.

    The arguments come from the real ``test`` parser, built and normalised as ``dev.py`` does. ``refusal_seams`` fails a
    refused case on the first seam it reaches: today's code reaches ``_activate_log_dir`` (``tee_output`` with
    ``--log-file``) and fails there, before anything runs. An invocation the rule lets through runs today's steps, in
    today's order, up to its body.
    """

    @pytest.mark.usefixtures("refusal_seams")
    @pytest.mark.parametrize(("words", "category", "action", "names"), H26_REFUSED)
    def test_test_names_the_action_takes_none_of_are_refused_with_exit_code_2(self, capsys, words, category, action, names):
        args = _dev_test_args(*words)
        _assert_parsed(args, category, action, names)

        rc = runner_cli._dispatch_test_command(args)

        assert rc == 2, f"H-26: dev.py test {' '.join(words)} must be refused with exit code 2 (got {rc!r})"
        _assert_refusal(capsys.readouterr().out, category, action, names, "stdout")

    @pytest.mark.usefixtures("refusal_seams")
    def test_a_refusal_writes_neither_the_log_file_nor_the_log_dir(self, tmp_path, capsys):
        log_file, log_dir = tmp_path / "run.log", tmp_path / "logs"
        args = _dev_test_args("--log-file", str(log_file), "--log-dir", str(log_dir), "services", "all", *H26_NAMES)
        _assert_parsed(args, "services", "all", H26_NAMES, {"log_file": str(log_file), "log_dir": str(log_dir)})

        rc = runner_cli._dispatch_test_command(args)

        assert rc == 2, f"H-26: a refusal with --log-file and --log-dir must still exit 2 (got {rc!r})"
        _assert_refusal(capsys.readouterr().out, "services", "all", H26_NAMES, "stdout")
        assert not log_file.exists() and not log_dir.exists(), f"a refused invocation writes no log (found under {tmp_path}: {sorted(path.name for path in tmp_path.iterdir())})"

    @pytest.mark.parametrize(("words", "category", "action", "names", "extra"), H26_LET_THROUGH)
    def test_an_invocation_the_rule_lets_through_reaches_the_body(self, capsys, entry_steps, words, category, action, names, extra):
        """Guard, green before and after: names to an action taking them, ``all`` without names, provider codes after a flag."""
        args = _dev_test_args(*words)
        _assert_parsed(args, category, action, names, extra)

        rc = runner_cli._dispatch_test_command(args)

        assert rc == 0, f"the body answered 0, and so must dev.py test {' '.join(words)} (got {rc!r})"
        assert entry_steps.events == _steps_of("_dispatch_test_command_body"), f"dev.py test {' '.join(words)} runs today's steps, in today's order (ran: {entry_steps.events})"
        assert len(entry_steps.bodies) == 1 and entry_steps.bodies[0] is args, f"the body runs once, with the args the entry was given (bodies: {entry_steps.bodies})"
        _assert_no_refusal(capsys.readouterr().out)


class TestMainRefusesBeforeAnySideEffect:
    """Contract point 2, ``python -m scripts.test_runner``: ``main()`` asks the rule right after parsing and returns 2.

    Its own parser puts the categories at the top level, so the words are those after ``dev.py test``; ``__main__`` exits
    with what ``main()`` returns. The cases mirror ``TestDispatchTestCommandRefusesBeforeAnySideEffect``'s, with
    ``_main_body`` as the body.
    """

    @pytest.mark.usefixtures("refusal_seams")
    @pytest.mark.parametrize(("words", "category", "action", "names"), H26_REFUSED)
    def test_test_names_the_action_takes_none_of_are_refused_with_exit_code_2(self, monkeypatch, capsys, words, category, action, names):
        _assert_parsed(_runner_args(*words), category, action, names)

        rc = _run_runner_main(monkeypatch, *words)

        assert rc == 2, f"H-26: python -m scripts.test_runner {' '.join(words)} must be refused with exit code 2 (got {rc!r})"
        _assert_refusal(capsys.readouterr().out, category, action, names, "stdout")

    @pytest.mark.usefixtures("refusal_seams")
    def test_a_refusal_writes_neither_the_log_file_nor_the_log_dir(self, monkeypatch, tmp_path, capsys):
        log_file, log_dir = tmp_path / "run.log", tmp_path / "logs"
        words = ("--log-file", str(log_file), "--log-dir", str(log_dir), "services", "all", "--list", "h26_name")
        _assert_parsed(_runner_args(*words), "services", "all", ("h26_name",), {"log_file": str(log_file), "log_dir": str(log_dir), "list_tests": True})

        rc = _run_runner_main(monkeypatch, *words)

        assert rc == 2, f"H-26: a refusal with --log-file, --log-dir and --list must still exit 2 (got {rc!r})"
        _assert_refusal(capsys.readouterr().out, "services", "all", ("h26_name",), "stdout")
        assert not log_file.exists() and not log_dir.exists(), f"a refused invocation writes no log (found under {tmp_path}: {sorted(path.name for path in tmp_path.iterdir())})"

    @pytest.mark.parametrize(("words", "category", "action", "names", "extra"), H26_LET_THROUGH)
    def test_an_invocation_the_rule_lets_through_reaches_the_body(self, monkeypatch, capsys, entry_steps, words, category, action, names, extra):
        """Guard, green before and after: names to an action taking them, ``all`` without names, provider codes after a flag."""
        rc = _run_runner_main(monkeypatch, *words)

        assert rc == 0, f"the body answered 0, and so must python -m scripts.test_runner {' '.join(words)} (got {rc!r})"
        assert entry_steps.events == _steps_of("_main_body"), f"python -m scripts.test_runner {' '.join(words)} runs today's steps, in today's order (ran: {entry_steps.events})"
        assert len(entry_steps.bodies) == 1, f"the body runs once (bodies: {entry_steps.bodies})"
        _assert_parsed(entry_steps.bodies[0], category, action, names, extra)
        _assert_no_refusal(capsys.readouterr().out)


class TestDevPyExitsWithTheRefusal:
    """Contract point 2, end to end: ``dev.py``'s ``main()`` returns ``args.func(args) or 0``, and ``sys.exit`` exits with it.

    ``args.func`` is the real ``_dispatch_test_command``, bound when ``main()`` registers the ``test`` parser; every seam
    behind it is closed by ``refusal_seams``.
    """

    @pytest.mark.usefixtures("refusal_seams")
    def test_dev_py_test_services_all_with_test_names_returns_2(self, monkeypatch, capsys, dev_module):
        monkeypatch.setattr(sys, "argv", ["dev.py", "test", "services", "all", *H26_NAMES])

        rc = dev_module.main()

        assert rc == 2, f"H-26: dev.py test services all {' '.join(H26_NAMES)} must exit 2: dev.py's main() returns what the test entry returns (got {rc!r})"
        _assert_refusal(capsys.readouterr().out, "services", "all", H26_NAMES, "stdout")


# ── H-30: with --log-file too, a body that raises still leaves the lane's database next to the logs ───────────────────
# ``main()`` (``python -m scripts.test_runner``) took the snapshot of the lane's database (``_snapshot_log_dir_db``)
# in a ``finally`` only without ``--log-file``: with it, the call came after ``_timed_run``, so a body that raised
# skipped it, and the run that crashed, the one whose database is evidence, left none. ``_dispatch_test_command``
# (``dev.py test``) has the ``finally`` in both branches. Every case drives a real entry with H-26's ``entry_steps``
# (every seam closed, the entry's steps recorded), ``tee_output`` recorded instead of teeing, and a body that answers
# 0 or raises ``H30BodyCrash``. Today's code fails one case, the body raising through ``main()`` with ``--log-file``
# ("H-30: … the lane's database must still be snapshotted …"); the others are guards, green before and after.

#: The action every case runs: this file's own, given no test names, so the H-26 rule lets it through to the body.
H30_ACTION = ("utils", H25_UTILS_ACTION)
#: What the recorded ``tee_output`` adds to the steps: entering the block it wraps, and exiting it, raising or not.
H30_TEE_ENTERED = "tee_output entered"
H30_TEE_EXITED = "tee_output exited"
#: Both entries, as ``(the function the words go through, its body, the command it serves)``.
H30_ENTRIES = [
    pytest.param("main", "_main_body", "python -m scripts.test_runner", id="main"),
    pytest.param("_dispatch_test_command", "_dispatch_test_command_body", "dev.py test", id="dev-py-test"),
]


class H30BodyCrash(RuntimeError):
    """What a crashing body raises: a class of its own, so that ``pytest.raises`` catches this crash and no other."""


def _h30_args(entry: str, *words: str) -> argparse.Namespace:
    """``words`` read by ``entry``'s parser, nothing run: ``create_parser()`` for ``main``, ``dev.py``'s ``test`` parser otherwise."""
    return _runner_args(*words) if entry == "main" else _dev_test_args(*words)


def _h30_run(monkeypatch, entry: str, *words: str):
    """``words`` through the real ``entry``: ``main()`` reads them from ``sys.argv``, ``_dispatch_test_command`` gets them parsed."""
    if entry == "main":
        return _run_runner_main(monkeypatch, *words)
    return runner_cli._dispatch_test_command(_dev_test_args(*words))


def _teed(steps: list[str]) -> list[str]:
    """``steps`` as an entry runs them with ``--log-file``: inside the log's tee, entered first and exited last."""
    return [H30_TEE_ENTERED, *steps, H30_TEE_EXITED]


def _crash_the_body(monkeypatch, steps, body: str) -> None:
    """``body`` replaced, where the entry looks it up, by a stand-in that records itself in ``steps.events`` and raises."""

    def crash(*_call_args):
        steps.events.append(body)
        raise H30BodyCrash(f"H-30: {body} crashed, as a category that raises would")

    monkeypatch.setattr(runner_cli, body, crash)


@pytest.fixture
def teed_entry_steps(monkeypatch, entry_steps):
    """``entry_steps``, with ``_common.tee_output`` recorded in the same ``events``: entered, then exited.

    The stand-in tees nothing and writes no file. Like the real one, it exits whether the block returns or raises, and
    it lets the exception through. Both entries look it up on ``_common`` when ``--log-file`` is given; without it, it is
    never entered.
    """

    @contextlib.contextmanager
    def tee_output(log_path):
        entry_steps.events.append(H30_TEE_ENTERED)
        try:
            yield log_path
        finally:
            entry_steps.events.append(H30_TEE_EXITED)

    monkeypatch.setattr(_common, "tee_output", tee_output)
    return entry_steps


@pytest.mark.parametrize(("entry", "body", "command"), H30_ENTRIES)
class TestTheLaneDatabaseIsSnapshottedWhateverTheBodyDoes:
    """Contract: an entry snapshots the lane's database once, after its body, whether the body answers or raises.

    With ``--log-file`` it does so inside the log's tee, as ``_dispatch_test_command`` does, so the snapshot's line lands
    in the log; the body's exception goes through the entry unchanged. Every case runs through both entries: ``main()``,
    the H-30 defect, and ``_dispatch_test_command``, which has the ``finally`` in both branches already.
    """

    def test_with_a_log_file_a_body_that_raises_still_leaves_the_database_snapshotted(self, monkeypatch, tmp_path, teed_entry_steps, entry, body, command):
        log_file = tmp_path / "run.log"
        words = ("--log-file", str(log_file), *H30_ACTION)
        _assert_parsed(_h30_args(entry, *words), *H30_ACTION, (), {"log_file": str(log_file)})
        _crash_the_body(monkeypatch, teed_entry_steps, body)

        with pytest.raises(H30BodyCrash):
            _h30_run(monkeypatch, entry, *words)

        events = teed_entry_steps.events
        shown = f"{command} {' '.join(words)}"
        assert events.count("_snapshot_log_dir_db") == 1, f"H-30: {shown}: the body raised, and the lane's database must still be snapshotted next to the logs, once: the run that crashed is the one whose database is evidence (ran: {events})"
        assert events == _teed(_steps_of(body)), f"H-30: {shown}: the snapshot comes after the body and before the log's tee exits, the other steps in today's order (ran: {events})"

    def test_with_a_log_file_a_body_answering_0_runs_todays_steps(self, monkeypatch, tmp_path, teed_entry_steps, entry, body, command):
        """Guard, green before and after: the body answers 0, and the snapshot follows it, once, inside the log's tee."""
        log_file = tmp_path / "run.log"
        words = ("--log-file", str(log_file), *H30_ACTION)
        _assert_parsed(_h30_args(entry, *words), *H30_ACTION, (), {"log_file": str(log_file)})

        rc = _h30_run(monkeypatch, entry, *words)

        assert rc == 0, f"the body answered 0, and so must {command} {' '.join(words)} (got {rc!r})"
        assert teed_entry_steps.events == _teed(_steps_of(body)), f"{command} {' '.join(words)} runs today's steps, in today's order, inside the log's tee (ran: {teed_entry_steps.events})"

    def test_without_a_log_file_a_body_that_raises_still_leaves_the_database_snapshotted(self, monkeypatch, teed_entry_steps, entry, body, command):
        """Guard, green before and after: without ``--log-file``, both entries already snapshot in a ``finally``."""
        _assert_parsed(_h30_args(entry, *H30_ACTION), *H30_ACTION, (), {"log_file": None})
        _crash_the_body(monkeypatch, teed_entry_steps, body)

        with pytest.raises(H30BodyCrash):
            _h30_run(monkeypatch, entry, *H30_ACTION)

        assert teed_entry_steps.events == _steps_of(body), f"{command} {' '.join(H30_ACTION)}: the body raised, and the lane's database is still snapshotted, once, after the body, with no log tee entered (ran: {teed_entry_steps.events})"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
