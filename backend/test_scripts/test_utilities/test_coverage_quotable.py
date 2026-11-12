"""The test runner's coverage plumbing, one step at a time (release 1.4, project 71, block 3: «a quotable coverage run»).

The block turns ``dev.py test --quotable all`` into one command that cleans, measures, checks that every expected piece of
coverage exists, and writes pure numbers. It lands in small steps, each pinned here by a class of its own:

1. ``TestOneCoverageTail`` (step 3.1) — the two entries of the runner (``dev.py test …`` through
   ``_dispatch_test_command`` and ``python -m scripts.test_runner`` through ``main``) used to carry the same coverage tail
   twice, and the same fourteen run flags registered twice. Behaviour is unchanged; what is pinned is that there is ONE
   tail, ``_finish_coverage(success) -> int``, and ONE registration of the flags, ``_add_run_flags(parser)``, and that
   ``_prepare_args(args)`` — the single place where a flag standing for other flags will be expanded (step 3.5,
   ``--quotable``) — runs first in both entries.

Pure: no database, no server, no network, no subprocess. The runner's heavy parts are stood in for with ``monkeypatch``; the
source of ``_cli.py`` is read as text (``ast``), never executed beyond its import.
"""

from __future__ import annotations

import argparse
import ast
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.test_runner import _cli, _common

CLI_SOURCE = Path(_cli.__file__).read_text(encoding="utf-8")

#: The run flags both parsers carry: what ``_add_run_flags`` registers, by their destination.
RUN_FLAG_DESTS = (
    "quiet",
    "coverage",
    "cov_clean_backend",
    "cov_clean_backend_e2e",
    "cov_clean_js",
    "workers",
    "fail_fast",
    "no_consolidate",
    "resume",
    "fresh_run",
    "run_status",
    "log_file",
    "log_dir",
    "no_shared_server",
    "assume_scoped",
)


def _bodies_namespace(**overrides: object) -> SimpleNamespace:
    """The arguments of a plain ``dev.py test api all`` as the two bodies read them."""
    values = {"category": "api", "quiet": True, "test_names": None, "coverage": None, "cov_clean_backend": False, "cov_clean_backend_e2e": False, "resume": False, "fresh_run": False, "run_status": False}
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def stood_in_runner(monkeypatch: pytest.MonkeyPatch):
    """What the two bodies call, replaced: runtime configuration, coverage mode, the passes (their verdict is the test's), and
    the two finalizers — which must only ever be reached through the coverage tail."""
    state = SimpleNamespace(result=0, parallel_ok=True, finalized=[])
    monkeypatch.setattr(_cli, "_configure_runtime", lambda args: True)
    monkeypatch.setattr(_cli, "_apply_coverage_mode", lambda *args, **kwargs: True)
    monkeypatch.setattr(_cli, "_run_passes", lambda args, names, verbose: (state.result, state.parallel_ok, True))
    monkeypatch.setattr(_cli, "_finalize_coverage", lambda *args, **kwargs: state.finalized.append("py"))
    monkeypatch.setattr(_cli, "_finalize_js_coverage", lambda *args, **kwargs: state.finalized.append("js"))
    monkeypatch.setattr(_common, "_COVERAGE_MODE", None)
    monkeypatch.setattr(_common, "_COVERAGE_PY", False)
    monkeypatch.setattr(_common, "_COVERAGE_JS", False)
    monkeypatch.setattr(_common, "_COVERAGE_SOURCE", None)
    return state


def _both_entries(args: SimpleNamespace):
    """The two coverage-finishing bodies, called the way their entry points call them."""
    return {
        "dev.py test (_dispatch_test_command_body)": lambda: _cli._dispatch_test_command_body(args),
        "python -m scripts.test_runner (_main_body)": lambda: _cli._main_body(argparse.ArgumentParser(), args),
    }


class TestOneCoverageTail:
    """Step 3.1: the coverage tail and the run flags, once."""

    @pytest.mark.parametrize(("result", "parallel_ok", "expected_success", "expected_rc"), [(0, True, True, 0), (1, True, False, 1), (0, False, False, 1)])
    def test_both_entry_points_finish_through_the_same_function(self, monkeypatch: pytest.MonkeyPatch, stood_in_runner: SimpleNamespace, result: int, parallel_ok: bool, expected_success: bool, expected_rc: int) -> None:
        """CT-01 — both bodies hand ``success`` (the passes' verdict: result 0 and the parallel pass green) to ``_finish_coverage``
        and return what it returns; neither calls a finalizer itself, though the coverage mode is on."""
        calls: list[bool] = []

        def finish(success: bool) -> int:
            calls.append(success)
            return expected_rc

        monkeypatch.setattr(_cli, "_finish_coverage", finish)
        monkeypatch.setattr(_common, "_COVERAGE_MODE", "all")
        monkeypatch.setattr(_common, "_COVERAGE_PY", True)
        monkeypatch.setattr(_common, "_COVERAGE_JS", True)
        stood_in_runner.result, stood_in_runner.parallel_ok = result, parallel_ok

        for entry, run in _both_entries(_bodies_namespace(coverage="all")).items():
            calls.clear()
            returned = run()
            assert calls == [expected_success], f"{entry}: _finish_coverage was called with {calls}, expected [{expected_success}]"
            assert returned == expected_rc, f"{entry}: returned {returned}, expected what _finish_coverage returned ({expected_rc})"
        assert stood_in_runner.finalized == [], "a body ran a finalizer itself instead of leaving it to _finish_coverage"

    @pytest.mark.parametrize("success", [True, False])
    def test_finish_coverage_finalizes_each_language_asked_and_returns_the_exit_code(self, monkeypatch: pytest.MonkeyPatch, stood_in_runner: SimpleNamespace, success: bool) -> None:
        """CT-02 — ``_finish_coverage``: with the coverage mode on, the Python finalizer then the JS one, each only when its language was
        asked, even when the tests failed (the coverage was still tracked); the exit code is 0 for success, 1 otherwise."""
        monkeypatch.setattr(_common, "_COVERAGE_MODE", "all")
        monkeypatch.setattr(_common, "_COVERAGE_PY", True)
        monkeypatch.setattr(_common, "_COVERAGE_JS", True)

        assert _cli._finish_coverage(success) == (0 if success else 1)
        assert stood_in_runner.finalized == ["py", "js"]

        stood_in_runner.finalized.clear()
        monkeypatch.setattr(_common, "_COVERAGE_JS", False)
        _cli._finish_coverage(success)
        assert stood_in_runner.finalized == ["py"], "JS coverage was not asked: no JS finalizer"

    @pytest.mark.parametrize("success", [True, False])
    def test_finish_coverage_without_a_coverage_mode_only_returns_the_exit_code(self, stood_in_runner: SimpleNamespace, success: bool) -> None:
        """CT-03 — no ``--coverage``: no finalizer, no report; the exit code alone."""
        assert _cli._finish_coverage(success) == (0 if success else 1)
        assert stood_in_runner.finalized == []

    def test_the_run_flags_are_registered_once_for_both_parsers(self) -> None:
        """CT-04 — every run flag is registered by ``_add_run_flags`` and nowhere else in ``_cli.py``, and both parsers (the runner's own
        and the ``test`` sub-command of ``dev.py``) read the same flags: the same destinations, the same defaults."""
        tree = ast.parse(CLI_SOURCE)
        registrations: dict[str, list[str]] = {}
        for function in [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]:
            for call in [node for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"]:
                for argument in call.args:
                    if isinstance(argument, ast.Constant) and isinstance(argument.value, str) and argument.value in ("--cov-clean-js", "--fresh-run", "--no-shared-server", "--assume-scoped"):
                        registrations.setdefault(argument.value, []).append(function.name)
        assert registrations == {flag: ["_add_run_flags"] for flag in ("--cov-clean-js", "--fresh-run", "--no-shared-server", "--assume-scoped")}, f"flags registered outside the one function: {registrations}"

        own = _cli.create_parser().parse_args(["all"])
        sub_parsers = argparse.ArgumentParser().add_subparsers()
        _cli.register_subparser(sub_parsers)
        top = sub_parsers._name_parser_map["test"]
        via_dev = top.parse_args(["all"])
        for dest in RUN_FLAG_DESTS:
            assert hasattr(own, dest) and hasattr(via_dev, dest), f"--{dest}: missing in one of the parsers"
            assert getattr(own, dest) == getattr(via_dev, dest), f"--{dest}: the two parsers disagree on its default"

    def test_add_run_flags_registers_the_flags_on_any_parser(self) -> None:
        """CT-05 — ``_add_run_flags(parser)`` on a bare parser gives the fifteen destinations, with the coverage value optional."""
        parser = argparse.ArgumentParser()
        _cli._add_run_flags(parser)

        namespace = parser.parse_args(["--coverage", "js", "--cov-clean-js", "--workers", "3", "--fresh-run"])

        assert [dest for dest in RUN_FLAG_DESTS if not hasattr(namespace, dest)] == []
        assert (namespace.coverage, namespace.cov_clean_js, namespace.workers, namespace.fresh_run) == ("js", True, "3", True)
        assert parser.parse_args(["--cov-clean-frontend"]).cov_clean_backend_e2e is True, "the deprecated alias of --cov-clean-backend-e2e is kept"

    @pytest.mark.parametrize("entry", ["main", "_dispatch_test_command"])
    def test_prepare_args_runs_first_in_both_entries(self, entry: str) -> None:
        """CT-06 — ``main`` and ``_dispatch_test_command`` call ``_prepare_args`` before anything that reads the flags (the refusal of
        test names, the log, the run): it is where ``--quotable`` will be expanded (step 3.5), so it must come first."""
        assert callable(getattr(_cli, "_prepare_args", None)), "_cli._prepare_args does not exist"
        function = next(node for node in ast.parse(CLI_SOURCE).body if isinstance(node, ast.FunctionDef) and node.name == entry)
        calls = [node.func.id for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
        # The first call that is not the output set-up, in source order
        ordered = [name for name in calls if name not in ("normalize_coverage_argv", "create_parser", "getattr")]
        assert "_prepare_args" in ordered, f"{entry} never calls _prepare_args"
        assert ordered.index("_prepare_args") < ordered.index("_refused_test_names"), f"{entry}: _prepare_args must come before the refusal of test names; calls in order: {ordered}"

    def test_prepare_args_changes_nothing_yet(self) -> None:
        """CT-07 — at this step ``_prepare_args`` returns the arguments as they are: the behaviour of the runner is unchanged."""
        args = _bodies_namespace(coverage="js")
        before = dict(vars(args))

        assert _cli._prepare_args(args) is args
        assert vars(args) == before
        assert "args" in inspect.signature(_cli._prepare_args).parameters
