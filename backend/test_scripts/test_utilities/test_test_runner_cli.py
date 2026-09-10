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
"""

from __future__ import annotations

import pytest

from scripts.test_runner import _backend_utils as backend_utils
from scripts.test_runner import _cli as runner_cli
from scripts.test_runner import _common
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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
