"""The test runner's coverage plumbing, one step at a time (release 1.4, project 71, block 3: «a quotable coverage run»).

The block turns ``dev.py test --quotable all`` into one command that cleans, measures, checks that every expected piece of
coverage exists, and writes pure numbers. It lands in small steps, each pinned here by a class of its own:

1. ``TestOneCoverageTail`` (step 3.1) — the two entries of the runner (``dev.py test …`` through
   ``_dispatch_test_command`` and ``python -m scripts.test_runner`` through ``main``) used to carry the same coverage tail
   twice, and the same fourteen run flags registered twice. Behaviour is unchanged; what is pinned is that there is ONE
   tail, ``_finish_coverage(success) -> int``, and ONE registration of the flags, ``_add_run_flags(parser)``, and that
   ``_prepare_args(args)`` — the single place where a flag standing for other flags will be expanded (step 3.5,
   ``--quotable``) — runs first in both entries.

2. ``TestUnitDirectories`` (step 3.2) — every Vitest run the consolidated pass makes under JS coverage writes into a directory the
   runner names (``coverage-js/unit/<category>-<n>``, the environment variable ``LF_VITEST_COVERAGE_DIR``) and records in the
   run's ledger (``_coverage.CoverageLedger``); and ``vitest.config.ts`` writes the coverage of a red run too
   (``reportOnFailure``), so a failing test no longer hides a whole group's coverage.

3. ``TestCompleteness`` (step 3.3) — the ledger notes everything the run launches under coverage (the Vitest groups and the
   actions that launch Vitest themselves, through ``vitest_env``; pytest; Playwright; the E2E server), and at the end
   ``check_coverage_pieces(ledger, mode)`` compares it with what is on disk. A missing or empty piece is a red row of the table
   «piece · where · expected · found», and the run exits 1 whatever its tests said: a run that lost data cannot report numbers.

4. ``TestPureNumbers`` (step 3.4) — the numbers a run reports are lines and branches apart, each covered / total with the
   percentage the runner computes, never coverage.py's TOTAL (which mixes the two) nor its ``percent_covered``: for the backend
   from ``totals`` of a JSON report of each database (pytest, E2E server, their union, and ``financial_math`` alone), for the
   frontend from the ``summary.json`` that ``js-coverage-report.js`` writes beside each report. ``summarize()`` writes them all to
   ``.coverage_data/coverage-summary.json`` (schema ``lf-coverage-summary/1``) and prints them.

5. ``TestQuotable`` (step 3.5) — ``--quotable`` stands for ``--fresh-run --coverage all`` and the three ``--cov-clean-*``, expanded
   by ``_prepare_args`` before the campaign opens; it needs ``all`` written and refuses everything that would make the run
   partial (``--resume``, test names, ``--fail-fast``, the provider filters, another category, a coverage other than ``all``, a
   listing, a status) with exit 2 before anything starts. The summary it writes says ``quotable`` only for a green run, with
   every piece, from a tree that was clean when it began.

Pure: no database, no server, no network, no subprocess. The runner's heavy parts are stood in for with ``monkeypatch``; the
source of ``_cli.py`` is read as text (``ast``), never executed beyond its import. The coverage data of step 3.4 is real: a few
lines of Python under ``tmp_path``, measured in process by coverage.py itself.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import inspect
import json
import os
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import coverage
import pytest

from scripts.test_runner import _cli, _common, _consolidate, _coverage, _frontend_common, _frontend_fx, _inventory, _server

CLI_SOURCE = Path(_cli.__file__).read_text(encoding="utf-8")
VITEST_CONFIG = Path(_common.PROJECT_ROOT, "frontend", "vitest.config.ts")
JS_REPORT_SCRIPT = Path(_common.PROJECT_ROOT, "frontend", "scripts", "js-coverage-report.js")

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
    "quotable",
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
    monkeypatch.setattr(_coverage, "LEDGER", _coverage.CoverageLedger())
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
        test names, the log, the run): it is where ``--quotable`` is expanded (step 3.5), so it must come first."""
        assert callable(getattr(_cli, "_prepare_args", None)), "_cli._prepare_args does not exist"
        function = next(node for node in ast.parse(CLI_SOURCE).body if isinstance(node, ast.FunctionDef) and node.name == entry)
        calls = [node.func.id for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
        # The first call that is not the output set-up, in source order
        ordered = [name for name in calls if name not in ("normalize_coverage_argv", "create_parser", "getattr")]
        assert "_prepare_args" in ordered, f"{entry} never calls _prepare_args"
        assert ordered.index("_prepare_args") < ordered.index("_refused_test_names"), f"{entry}: _prepare_args must come before the refusal of test names; calls in order: {ordered}"

    def test_prepare_args_changes_nothing_yet(self) -> None:
        """CT-07 — without ``--quotable`` ``_prepare_args`` returns the arguments as they are: no flag stands for others."""
        args = _bodies_namespace(coverage="js")
        before = dict(vars(args))

        assert _cli._prepare_args(args) is args
        assert vars(args) == before
        assert "args" in inspect.signature(_cli._prepare_args).parameters


class TestUnitDirectories:
    """Step 3.2: each Vitest group has its own directory, named by the runner and written in the ledger."""

    @pytest.fixture
    def vitest_calls(self, monkeypatch: pytest.MonkeyPatch):
        """``subprocess.run`` of the consolidated pass, replaced by a recorder of its command and environment; a ledger of its own;
        the JS coverage on; the reports read back as empty."""
        calls: list[SimpleNamespace] = []

        def fake_run(cmd, **kwargs):
            calls.append(SimpleNamespace(cmd=cmd, env=kwargs.get("env"), cwd=kwargs.get("cwd")))
            return SimpleNamespace(returncode=0)

        ledger = _coverage.CoverageLedger()
        monkeypatch.setattr(_consolidate.subprocess, "run", fake_run)
        monkeypatch.setattr(_consolidate, "_vitest_results", lambda report, known: {})
        monkeypatch.setattr(_coverage, "LEDGER", ledger)
        monkeypatch.setattr(_common, "_COVERAGE_JS", True)
        monkeypatch.delenv("LF_VITEST_COVERAGE_DIR", raising=False)
        return SimpleNamespace(calls=calls, ledger=ledger)

    def test_each_vitest_group_gets_its_directory_in_the_ledger(self, vitest_calls: SimpleNamespace) -> None:
        """UD-01 — under JS coverage, every ``run_vitest_group`` runs vitest with ``LF_VITEST_COVERAGE_DIR`` set to
        ``coverage-js/unit/<category>-<n>`` (n counting per category: ``front-fx-1``, ``front-fx-2``, ``front-user-1``) and the ledger
        expects exactly those directories, in order; the variable is the child's alone, never the runner's own environment."""
        _consolidate.run_vitest_group(["a.test.ts"], True, category="front-fx")
        _consolidate.run_vitest_group(["b.test.ts"], True, category="front-user")
        _consolidate.run_vitest_group(["c.test.ts"], True, category="front-fx")

        directories = [call.env["LF_VITEST_COVERAGE_DIR"] for call in vitest_calls.calls]
        assert directories == ["coverage-js/unit/front-fx-1", "coverage-js/unit/front-user-1", "coverage-js/unit/front-fx-2"]
        assert vitest_calls.ledger.units == directories, "the ledger expects exactly the directories the runs were told to write"
        assert "LF_VITEST_COVERAGE_DIR" not in _consolidate.os.environ

    def test_without_js_coverage_nothing_is_named_and_nothing_is_expected(self, monkeypatch: pytest.MonkeyPatch, vitest_calls: SimpleNamespace) -> None:
        """UD-02 — no ``--coverage``, or ``--coverage py``: no variable in the child, nothing in the ledger."""
        _consolidate.run_vitest_group(["a.test.ts"], False, category="front-fx")
        monkeypatch.setattr(_common, "_COVERAGE_JS", False)
        _consolidate.run_vitest_group(["b.test.ts"], True, category="front-fx")

        assert all("LF_VITEST_COVERAGE_DIR" not in (call.env or {}) for call in vitest_calls.calls)
        assert vitest_calls.ledger.units == []

    def test_a_group_without_a_category_still_has_a_directory(self, vitest_calls: SimpleNamespace) -> None:
        """UD-03 — ``category=None`` (a direct call): the label is ``vitest``."""
        _consolidate.run_vitest_group(["a.test.ts"], True)

        assert vitest_calls.calls[0].env["LF_VITEST_COVERAGE_DIR"] == "coverage-js/unit/vitest-1"

    def test_the_ledger_counts_per_label_and_returns_what_it_expects(self) -> None:
        """UD-04 — ``CoverageLedger.expect_unit(label)`` returns the directory, relative to ``frontend/``, and keeps the list."""
        ledger = _coverage.CoverageLedger()

        first, second, other = ledger.expect_unit("front-fx"), ledger.expect_unit("front-fx"), ledger.expect_unit("front-user")

        assert (first, second, other) == ("coverage-js/unit/front-fx-1", "coverage-js/unit/front-fx-2", "coverage-js/unit/front-user-1")
        assert ledger.units == [first, second, other]

    def test_vitest_config_reports_on_failure(self) -> None:
        """UD-05 — contract on the text of ``frontend/vitest.config.ts``: ``reportOnFailure: true`` (without it Vitest 4 writes no
        coverage for a run with a red test) and the directory read from ``LF_VITEST_COVERAGE_DIR``, the dated one only as the default
        for a run no one named."""
        text = VITEST_CONFIG.read_text(encoding="utf-8")

        assert "reportOnFailure: true" in text
        assert "process.env.LF_VITEST_COVERAGE_DIR" in text
        assert "reportsDirectory: process.env.LF_VITEST_COVERAGE_DIR ?? `coverage-js/unit/${Date.now()" in text, "the variable first, and the dated directory as the default for a direct run, as it was"


def _coverage_database(path: Path, measured_files: int) -> Path:
    """A coverage.py data file as the check reads it: the ``file`` table, with ``measured_files`` rows (0 = the schema of a writer
    stopped while saving, nothing measured)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.execute("create table file (id integer primary key, path text, unique (path))")
        con.executemany("insert into file (path) values (?)", [(f"/src/module_{i}.py",) for i in range(measured_files)])
        con.commit()
    finally:
        con.close()
    return path


def _istanbul_json(path: Path, text: str = '{"/src/a.ts": {"path": "/src/a.ts", "s": {"0": 1}}}') -> Path:
    """An istanbul ``coverage-final.json`` (or a Playwright worker file): one measured file by default, or the text given."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestCompleteness:
    """Step 3.3: the run checks, at its end, that every piece of coverage it launched is there; a missing piece turns it red."""

    @pytest.fixture
    def run_root(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """A project root of the test's own (the check reads ``.coverage_data/`` and ``frontend/coverage-js/`` under it, and the
        Python data of ``run_command`` lands in the working directory, so the test works there too) and a ledger of its own."""
        ledger = _coverage.CoverageLedger()
        monkeypatch.setattr(_coverage, "LEDGER", ledger)
        monkeypatch.setattr(_coverage, "PROJECT_ROOT", tmp_path)
        monkeypatch.chdir(tmp_path)
        return SimpleNamespace(root=tmp_path, js=tmp_path / "frontend" / "coverage-js", ledger=ledger)

    def test_a_missing_unit_directory_turns_the_run_red_with_a_table(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, stood_in_runner: SimpleNamespace, run_root: SimpleNamespace) -> None:
        """CC-01 — a Vitest group the ledger expects left no ``coverage-final.json``: ``_finish_coverage`` prints the table «piece ·
        where · expected · found», names the directory as missing, and returns 1 although every test passed. The same run with the
        directory and its report present returns 0."""
        monkeypatch.setattr(_common, "_COVERAGE_MODE", "js")
        monkeypatch.setattr(_common, "_COVERAGE_JS", True)
        monkeypatch.setattr(_common, "_COVERAGE_SOURCE", "frontend")
        run_root.ledger.expect_unit("front-fx")

        assert _cli._finish_coverage(True) == 1, "a run with a piece missing is red, whatever the tests said"
        out = capsys.readouterr().out
        for column in ("piece", "where", "expected", "found"):
            assert column in out, f"the table has no «{column}» column"
        assert "coverage-js/unit/front-fx-1" in out and "missing" in out

        _istanbul_json(run_root.js / "unit" / "front-fx-1" / "coverage-final.json")
        _istanbul_json(run_root.js / "unit-combined" / "coverage-final.json")
        assert _cli._finish_coverage(True) == 0, "every expected piece is there: the run keeps the tests' verdict"
        assert _cli._finish_coverage(False) == 1

    def test_an_empty_server_database_is_a_red_row(self, run_root: SimpleNamespace) -> None:
        """CC-02 — the E2E server's data (``.coverage_data/frontend``) exists but measured no file — the shape a writer stopped
        while saving leaves: a red row. With one measured file the row is green. The database is read, never written."""
        run_root.ledger.expect_python("frontend")
        database = _coverage_database(run_root.root / ".coverage_data" / "frontend", 0)

        rows = _coverage.check_coverage_pieces(run_root.ledger, "frontend")
        red = [row for row in rows if not row.ok]
        assert [row.where for row in red] == [".coverage_data/frontend"]
        assert "0" in red[0].found

        database.unlink()
        _coverage_database(database, 1)
        assert all(row.ok for row in _coverage.check_coverage_pieces(run_root.ledger, "frontend"))

    def test_a_part_left_uncombined_is_a_red_row(self, run_root: SimpleNamespace) -> None:
        """CC-03 — where the finalizer combines the server's parts (a frontend or a whole run), a ``.coverage.*`` still in the
        project root is data no report holds: a red row naming how many are left."""
        run_root.ledger.expect_python("frontend")
        _coverage_database(run_root.root / ".coverage_data" / "frontend", 3)
        _coverage_database(run_root.root / ".coverage.host.4242.XabcdeX.Habcdefghijh", 2)

        for mode in ("frontend", "all"):
            red = [row for row in _coverage.check_coverage_pieces(run_root.ledger, mode) if not row.ok]
            assert len(red) == 1 and ".coverage.*" in red[0].where and "1" in red[0].found, f"mode {mode}: {red}"

    def test_a_torn_worker_file_is_a_red_row(self, run_root: SimpleNamespace) -> None:
        """CC-04 — a Playwright run under JS coverage: the worker files must all be readable JSON (one cut short is a red row) and no
        ``*.tmp`` may be left (a sink that never renamed its file is a red row). One readable file and nothing else is green."""
        run_root.ledger.expect_e2e_js()
        _istanbul_json(run_root.js / "e2e-raw" / "worker-0-101.json")
        _istanbul_json(run_root.js / "e2e" / "coverage-final.json")
        assert all(row.ok for row in _coverage.check_coverage_pieces(run_root.ledger, "frontend"))

        _istanbul_json(run_root.js / "e2e-raw" / "worker-1-102.json", '{"/src/b.ts": {"pa')
        _istanbul_json(run_root.js / "e2e-raw" / "worker-2-103.json.tmp", "{}")
        red = [row for row in _coverage.check_coverage_pieces(run_root.ledger, "frontend") if not row.ok]
        assert len(red) == 2, red
        assert any("worker-1-102.json" in row.found for row in red), "the torn file is named"
        assert any("tmp" in row.where for row in red), "the unfinished file is its own row"

    def test_a_direct_vitest_call_is_in_the_ledger(self, monkeypatch: pytest.MonkeyPatch, run_root: SimpleNamespace) -> None:
        """CC-05 — an action that launches Vitest itself (``front-fx fx-unit``, not the consolidated pass) under JS coverage: its
        child gets ``LF_VITEST_COVERAGE_DIR=coverage-js/unit/front-fx-1`` and the ledger expects that directory. Without JS
        coverage, nothing is named and nothing expected."""
        envs: list = []
        monkeypatch.setattr(_frontend_fx.subprocess, "run", lambda cmd, **kwargs: envs.append(kwargs.get("env")) or SimpleNamespace(returncode=0))
        monkeypatch.delenv("LF_VITEST_COVERAGE_DIR", raising=False)

        monkeypatch.setattr(_common, "_COVERAGE_JS", True)
        assert _frontend_fx.front_fx_unit()
        assert envs[-1]["LF_VITEST_COVERAGE_DIR"] == "coverage-js/unit/front-fx-1"
        assert run_root.ledger.units == ["coverage-js/unit/front-fx-1"]
        assert "LF_VITEST_COVERAGE_DIR" not in os.environ, "the variable is the child's alone"

        monkeypatch.setattr(_common, "_COVERAGE_JS", False)
        assert _frontend_fx.front_fx_unit()
        assert "LF_VITEST_COVERAGE_DIR" not in (envs[-1] or {})
        assert run_root.ledger.units == ["coverage-js/unit/front-fx-1"]

    def test_every_vitest_launch_of_the_runner_names_its_directory(self) -> None:
        """CC-06 — gate on the runner's source: every function that launches Vitest (a command list with ``"vitest"`` and a
        ``subprocess.run``, ``Popen`` or ``run_command`` call) hands it the environment of ``vitest_env``; a launch that does not
        writes a directory the ledger never sees, and the check could not tell it missing."""
        launchers = {"subprocess.run", "subprocess.Popen", "run_command", "_common.run_command"}
        unnamed = []
        for module in sorted(Path(_cli.__file__).parent.glob("*.py")):
            source = module.read_text(encoding="utf-8")
            for node in ast.walk(ast.parse(source)):
                if not isinstance(node, ast.FunctionDef):
                    continue
                launches = {ast.unparse(call.func) for call in ast.walk(node) if isinstance(call, ast.Call)}
                lists_vitest = any(isinstance(item, ast.List) and any(isinstance(e, ast.Constant) and e.value == "vitest" for e in item.elts) for item in ast.walk(node))
                if lists_vitest and launches & launchers and not any(name.endswith("vitest_env") for name in launches):
                    unnamed.append(f"{module.name}:{node.lineno} {node.name}")
        assert unnamed == [], f"Vitest launched without vitest_env: {unnamed}"

    def test_a_backend_only_run_expects_only_the_pytest_data(self, monkeypatch: pytest.MonkeyPatch, run_root: SimpleNamespace) -> None:
        """CC-07 — ``--coverage py <backend category>``: a pytest command through ``run_command`` notes ``.coverage_data/backend``,
        nothing else; the check then has one row, green when the database holds data — the server parts a backend run leaves in the
        project root are not its pieces (its finalizer does not combine them)."""
        monkeypatch.setattr(_common, "_COVERAGE_PY", True)
        monkeypatch.setattr(_common, "_COVERAGE_JS", False)
        monkeypatch.setattr(_common, "_COVERAGE_SOURCE", "backend")
        monkeypatch.setattr(_common.subprocess, "run", lambda cmd, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""))

        assert _common.run_command(["pipenv", "run", "pytest", "backend/test_scripts/test_utilities/test_coverage_quotable.py"], "stood-in pytest")
        assert run_root.ledger.python == {"backend"}
        assert run_root.ledger.units == [] and run_root.ledger.e2e_js == 0

        _coverage_database(run_root.root / ".coverage_data" / "backend", 5)
        _coverage_database(run_root.root / ".coverage.host.4242.XabcdeX.Habcdefghijh", 2)
        rows = _coverage.check_coverage_pieces(run_root.ledger, "backend")
        assert [(row.where, row.ok) for row in rows] == [(".coverage_data/backend", True)]

    def test_playwright_and_the_server_under_coverage_are_in_the_ledger(self, monkeypatch: pytest.MonkeyPatch, run_root: SimpleNamespace) -> None:
        """CC-08 — a Playwright run under JS coverage expects worker files (both launchers: the consolidated group and a single
        action); under Python coverage, Playwright and the shared server expect the E2E server's data, ``.coverage_data/frontend``.
        A backend category's shared server notes nothing: its parts are not combined by its run (open question of step 3.3)."""
        monkeypatch.setattr(_common, "_COVERAGE_PY", True)
        monkeypatch.setattr(_common, "_COVERAGE_JS", True)
        monkeypatch.setattr(_common, "_COVERAGE_SOURCE", "frontend")
        monkeypatch.setattr(_consolidate.subprocess, "run", lambda cmd, **kwargs: SimpleNamespace(returncode=0))
        monkeypatch.setattr(_consolidate, "_playwright_results", lambda report: {})

        _consolidate.run_playwright_group(["e2e/a.spec.ts"], True, category="front-fx")
        _frontend_common._run_playwright_body("e2e/b.spec.ts", coverage=True)
        assert run_root.ledger.e2e_js == 2
        assert run_root.ledger.python == {"frontend"}

        class StoodInServer:
            def __init__(self, **kwargs: object) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc: object) -> None:
                return None

        monkeypatch.setattr(_server, "SharedTestServer", StoodInServer)
        monkeypatch.setattr(_cli, "_requires_shared_backend", lambda args: True)
        for source, expected in (("backend", set()), ("frontend", {"frontend"})):
            monkeypatch.setattr(_common, "_COVERAGE_SOURCE", source)
            run_root.ledger.reset()
            with _cli.shared_backend_for("api", SimpleNamespace(workers="1")):
                pass
            assert run_root.ledger.python == expected, f"source {source}"

    def test_a_run_starts_from_an_empty_ledger(self, monkeypatch: pytest.MonkeyPatch, run_root: SimpleNamespace) -> None:
        """CC-09 — ``_apply_coverage_mode``, the first coverage step of both entries, empties the ledger, with or without
        ``--coverage``: nothing a previous run of the same process noted is expected again."""
        for name in ("_COVERAGE_MODE", "_RESUME_MODE", "_COVERAGE_SOURCE", "_COVERAGE_PY", "_COVERAGE_JS", "_FAIL_FAST"):
            monkeypatch.setattr(_common, name, getattr(_common, name))
        run_root.ledger.expect_unit("front-fx")
        run_root.ledger.expect_python("backend")
        run_root.ledger.expect_e2e_js()

        assert _cli._apply_coverage_mode(SimpleNamespace(category="api", fail_fast=False), None, False, False, False)
        assert (run_root.ledger.units, run_root.ledger.python, run_root.ledger.e2e_js) == ([], set(), 0)
        assert run_root.ledger.expect_unit("front-fx") == "coverage-js/unit/front-fx-1", "the count per label starts again"

    def test_collecting_the_launches_expects_nothing(self, monkeypatch: pytest.MonkeyPatch, run_root: SimpleNamespace) -> None:
        """CC-10 — the consolidated pass collects what each action would launch by calling it with the launchers stood in
        (``_inventory.collect_launches``); under JS coverage that dry run must not note a Vitest directory nobody will write."""
        monkeypatch.setattr(_common, "_COVERAGE_JS", True)
        launches, _errors = _inventory.collect_launches()

        assert any(engine == "vitest" for units in launches.values() for engine, _path, _project in units), "the dry run reached the Vitest actions"
        assert run_root.ledger.units == [], "a dry run noted directories in the ledger"

    def test_stale_e2e_data_without_a_part_this_run_is_a_red_row(self, monkeypatch: pytest.MonkeyPatch, run_root: SimpleNamespace) -> None:
        """CC-11 — ``.coverage_data/frontend`` accumulates across runs, so rows in it do not prove that this run's server wrote
        anything. The finalizer says what it did (``PythonFinalized``): with no part in the project root it saves nothing, and the
        check turns that into a red row although the old database still has rows. A finalizer that found and saved parts is green."""
        monkeypatch.setattr(_coverage.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""))
        run_root.ledger.expect_python("frontend")
        _coverage_database(run_root.root / ".coverage_data" / "frontend", 7)

        finalized = _coverage._finalize_coverage(is_front=True, is_all=False)

        assert finalized == _coverage.PythonFinalized(server_parts=0, frontend_saved=False)
        red = [row for row in _coverage.check_coverage_pieces(run_root.ledger, "frontend", finalized) if not row.ok]
        assert len(red) == 1 and "this run" in red[0].piece, red
        assert all(row.ok for row in _coverage.check_coverage_pieces(run_root.ledger, "frontend", _coverage.PythonFinalized(server_parts=2, frontend_saved=True)))


#: One ``if`` never taken the other way: every line runs, one branch of two. Lines 100 %, branches 50 %, coverage.py's TOTAL
#: (lines + branches together) 6 / 7 = 85.71 %, a number that is neither.
_ONE_IF = "def decide(flag):\n    result = 0\n    if flag:\n        result = 1\n    return result\n"


def _measured_database(root: Path, database: Path, sources: dict[str, str]) -> Path:
    """Real coverage data: write each ``{relative path: source}`` under ``root``, import it and call its function with ``True``
    while coverage.py measures lines and branches into ``database``. In process, nested inside any coverage that is already
    running (coverage.py pauses the outer collector and resumes it on stop)."""
    for relative, source in sources.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(source, encoding="utf-8")
    database.parent.mkdir(parents=True, exist_ok=True)
    measuring = coverage.Coverage(data_file=str(database), branch=True, config_file=False, include=[f"{root}/*"])
    measuring.start()
    try:
        for relative in sources:
            spec = importlib.util.spec_from_file_location(Path(relative).stem, root / relative)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.decide(True)
    finally:
        measuring.stop()
        measuring.save()
    return database


def _js_summary(path: Path, lines: tuple[int, int], branches: tuple[int, int], read: int = 3, skipped: int = 0) -> Path:
    """The ``summary.json`` ``js-coverage-report.js`` writes beside a report: covered / total per measure, files read and skipped."""
    measure = lambda covered, total: {"covered": covered, "total": total}  # noqa: E731
    body = {"lines": measure(*lines), "branches": measure(*branches), "statements": measure(*lines), "functions": measure(1, 1), "files": {"read": read, "skipped": skipped}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


@pytest.fixture
def summary_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """A project root of the test's own, a ledger of its own, and the git state stood in (a clean tree at a known commit)."""
    ledger = _coverage.CoverageLedger()
    monkeypatch.setattr(_coverage, "LEDGER", ledger)
    monkeypatch.setattr(_coverage, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(_coverage, "_git_state", lambda: ("0123abc", False))
    monkeypatch.chdir(tmp_path)
    return SimpleNamespace(root=tmp_path, data=tmp_path / ".coverage_data", js=tmp_path / "frontend" / "coverage-js", ledger=ledger)


class TestPureNumbers:
    """Step 3.4: lines and branches apart, covered / total, the percentage computed by the runner; one summary file."""

    @pytest.fixture
    def run_root(self, summary_root: SimpleNamespace):
        return summary_root

    def test_backend_lines_and_branches_come_from_totals_never_percent_covered(self, run_root: SimpleNamespace) -> None:
        """PN-01 — real data, one ``if`` taken one way: lines 5 / 5 = 100 %, branches 1 / 2 = 50 %. coverage.py's mixed TOTAL
        (85.71 %) appears nowhere: each percentage is the runner's own, covered / total."""
        database = _measured_database(run_root.root, run_root.data / "backend", {"pkg/one_if.py": _ONE_IF})

        totals = _coverage.backend_totals(database)

        assert totals["files"] == 1
        assert totals["lines"] == {"covered": 5, "total": 5, "pct": 100.0}
        assert totals["branches"] == {"covered": 1, "total": 2, "pct": 50.0}
        assert 85.71 not in {round(measure["pct"], 2) for measure in (totals["lines"], totals["branches"])}

    def test_financial_math_include_takes_nested_files(self, run_root: SimpleNamespace) -> None:
        """PN-02 — ``financial_math`` is the combined data restricted to ``backend/app/services/financial_math/``, subfolders
        (``fifo/``, ``lots/``, ``portfolio/``) included; a file outside the folder is not counted."""
        sources = {"backend/app/services/financial_math/fifo/lots.py": _ONE_IF, "backend/app/services/other/elsewhere.py": _ONE_IF}
        database = _measured_database(run_root.root, run_root.data / "backend", sources)

        whole = _coverage.backend_totals(database)
        folder = _coverage.backend_totals(database, include=_coverage.FINANCIAL_MATH_INCLUDE)

        assert whole["files"] == 2
        assert folder["files"] == 1, "the nested file of financial_math, and only it"
        assert folder["lines"] == {"covered": 5, "total": 5, "pct": 100.0}

    def test_an_empty_or_missing_database_has_no_totals(self, run_root: SimpleNamespace) -> None:
        """PN-03 — no database, or one with no measured file: ``None``, never a zero that would read as «measured, nothing covered»."""
        assert _coverage.backend_totals(run_root.data / "backend") is None
        assert _coverage.backend_totals(_coverage_database(run_root.data / "frontend", 0)) is None

    def test_the_js_summary_json_is_read_for_three_levels(self, run_root: SimpleNamespace) -> None:
        """PN-04 — ``unit`` (``unit-combined/``), ``e2e`` and ``combined``: lines and branches covered / total, the percentage
        computed here, the files read and skipped carried over; a level without its ``summary.json`` is ``None``."""
        _js_summary(run_root.js / "unit-combined" / "summary.json", (30, 40), (3, 8), read=4)
        _js_summary(run_root.js / "e2e" / "summary.json", (10, 40), (0, 0), read=2, skipped=1)

        levels = _coverage.frontend_totals()

        assert levels["unit"] == {"files": {"read": 4, "skipped": 0}, "lines": {"covered": 30, "total": 40, "pct": 75.0}, "branches": {"covered": 3, "total": 8, "pct": 37.5}}
        assert levels["e2e"]["branches"] == {"covered": 0, "total": 0, "pct": None}, "no branch measured: no percentage, not 0 % nor 100 %"
        assert levels["e2e"]["files"] == {"read": 2, "skipped": 1}
        assert levels["combined"] is None

    def test_the_js_report_script_writes_its_summary_and_counts_the_files_it_skips(self) -> None:
        """PN-05 — contract on the text of ``frontend/scripts/js-coverage-report.js``: it writes ``summary.json`` beside
        ``coverage-final.json`` and counts the files it could not read, which it used to skip in silence."""
        text = JS_REPORT_SCRIPT.read_text(encoding="utf-8")

        assert "'summary.json'" in text
        assert "skipped += 1" in text
        assert "covered" in text and "total" in text

    def test_summarize_writes_the_summary_file_and_prints_the_numbers(self, capsys: pytest.CaptureFixture, run_root: SimpleNamespace) -> None:
        """PN-06 — ``summarize()`` writes ``.coverage_data/coverage-summary.json``, schema ``lf-coverage-summary/1``: the run
        (``sha``, ``dirty``, ``workers``, ``argv``, ``categories``), the verdict (``quotable`` with its ``reasons``), the backend
        bases (pytest, E2E server, their union, ``financial_math``) and the three frontend levels, and the piece table. A base the
        run did not measure is ``None``. The same numbers are printed."""
        _measured_database(run_root.root, run_root.data / "backend", {"backend/app/services/financial_math/top.py": _ONE_IF})
        _measured_database(run_root.root, run_root.data / "frontend", {"backend/app/api/route.py": _ONE_IF})
        _js_summary(run_root.js / "unit-combined" / "summary.json", (30, 40), (3, 8))
        run_root.ledger.reset(categories=["all"])
        run_root.ledger.expect_python("backend")
        run_root.ledger.expect_python("frontend")
        rows = [_coverage.PieceRow("Python data", ".coverage_data/backend", "≥1 measured file", "1 file(s)", True)]

        summary = _coverage.summarize(run_root.ledger, rows, success=True)

        written = json.loads((run_root.data / "coverage-summary.json").read_text(encoding="utf-8"))
        assert written == summary
        assert written["schema"] == "lf-coverage-summary/1"
        assert (written["sha"], written["dirty"], written["categories"]) == ("0123abc", False, ["all"])
        assert {"workers", "argv", "quotable", "reasons", "pieces"} <= written.keys()
        assert written["quotable"] is False and written["reasons"], "only a --quotable all run can be quoted (step 3.5)"
        backend = written["backend"]
        assert backend["pytest"]["lines"]["total"] == 5 and backend["server"]["lines"]["total"] == 5
        assert backend["combined"]["files"] == 2 and backend["combined"]["lines"] == {"covered": 10, "total": 10, "pct": 100.0}
        assert backend["financial_math"]["files"] == 1
        assert written["frontend"]["unit"]["lines"]["pct"] == 75.0 and written["frontend"]["e2e"] is None
        assert written["pieces"] == [{"piece": "Python data", "where": ".coverage_data/backend", "expected": "≥1 measured file", "found": "1 file(s)", "ok": True}]
        out = capsys.readouterr().out
        assert "75.00" in out and "37.50" in out, "the frontend unit numbers are printed"

    def test_the_reasons_name_what_keeps_a_run_from_being_quoted(self, monkeypatch: pytest.MonkeyPatch, run_root: SimpleNamespace) -> None:
        """PN-07 — red tests, a missing piece, a dirty tree each add their reason; a backend-only run has no frontend and its
        server base is ``None``."""
        run_root.ledger.expect_python("backend")
        _measured_database(run_root.root, run_root.data / "backend", {"pkg/one_if.py": _ONE_IF})
        missing = _coverage.PieceRow("Vitest unit", "frontend/coverage-js/unit/front-fx-1", "coverage-final.json, ≥1 file", "missing", False)

        clean = _coverage.summarize(run_root.ledger, [], success=True)
        monkeypatch.setattr(_coverage, "_git_state", lambda: ("0123abc", True))
        dirty = _coverage.summarize(run_root.ledger, [missing], success=False)

        assert len(dirty["reasons"]) == len(clean["reasons"]) + 3, dirty["reasons"]
        assert dirty["backend"]["server"] is None and dirty["frontend"] == {"unit": None, "e2e": None, "combined": None}

    def test_every_coverage_run_ends_with_its_summary(self, monkeypatch: pytest.MonkeyPatch, stood_in_runner: SimpleNamespace, run_root: SimpleNamespace) -> None:
        """PN-08 — ``_finish_coverage`` writes the summary after the piece table, in every coverage run; without ``--coverage``,
        nothing."""
        _cli._finish_coverage(True)
        assert not (run_root.data / "coverage-summary.json").exists()

        monkeypatch.setattr(_common, "_COVERAGE_MODE", "js")
        monkeypatch.setattr(_common, "_COVERAGE_JS", True)
        _cli._finish_coverage(True)
        assert json.loads((run_root.data / "coverage-summary.json").read_text(encoding="utf-8"))["schema"] == "lf-coverage-summary/1"

    def test_the_mixed_total_of_coverage_report_is_labelled(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, run_root: SimpleNamespace) -> None:
        """PN-09 — outside a quotable run ``coverage report`` still prints its TOTAL, followed by a line saying it mixes lines and
        branches, so nobody quotes it."""
        monkeypatch.setattr(_coverage.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""))

        _coverage._finalize_coverage(is_front=False, is_all=False)

        assert "lines + branches" in capsys.readouterr().out


class TestQuotable:
    """Step 3.5: ``--quotable``, what it stands for, what it refuses, and when its summary says «quotable»."""

    @pytest.fixture
    def run_root(self, summary_root: SimpleNamespace):
        return summary_root

    @pytest.fixture
    def entries(self, monkeypatch: pytest.MonkeyPatch):
        """The two entries of the runner with everything after the expansion stood in: the campaign (``_timed_run``) records the
        arguments it is opened with, the log and the snapshot do nothing. ``run(argv)`` returns ``(exit code, arguments or None)``."""
        seen: list = []
        monkeypatch.setattr(_cli, "_timed_run", lambda args, body: seen.append(args) or 0)
        monkeypatch.setattr(_cli, "_activate_log_dir", lambda args: None)
        monkeypatch.setattr(_cli, "_snapshot_log_dir_db", lambda: None)
        monkeypatch.setattr(_common, "line_buffer_output", lambda: None)

        def own(argv: list):
            seen.clear()
            monkeypatch.setattr(sys, "argv", ["scripts.test_runner", *argv])
            return _cli.main(), (seen[0] if seen else None)

        def via_dev(argv: list):
            seen.clear()
            sub_parsers = argparse.ArgumentParser().add_subparsers()
            _cli.register_subparser(sub_parsers)
            args = sub_parsers._name_parser_map["test"].parse_args(_cli.normalize_coverage_argv(argv))
            return _cli._dispatch_test_command(args), (seen[0] if seen else None)

        return {"python -m scripts.test_runner": own, "dev.py test": via_dev}

    def test_quotable_expands_before_the_campaign_opens(self, entries: dict) -> None:
        """QU-01 — ``--quotable all`` reaches the campaign (``_timed_run``) of both entries already standing for
        ``--fresh-run --coverage all --cov-clean-backend --cov-clean-backend-e2e --cov-clean-js``: ``_timed_run`` reads
        ``fresh_run`` before the body runs, so the expansion cannot wait for the body."""
        for entry, run in entries.items():
            rc, args = run(["--quotable", "all"])
            assert rc == 0 and args is not None, f"{entry}: the run did not start"
            assert (args.fresh_run, args.coverage, args.cov_clean_backend, args.cov_clean_backend_e2e, args.cov_clean_js) == (True, "all", True, True, True), entry
            assert args.quotable is True and args.category == "all", entry

    def test_without_quotable_nothing_is_expanded(self, entries: dict) -> None:
        """QU-02 — the same command line without ``--quotable``: a plain run, none of the flags set."""
        for entry, run in entries.items():
            _rc, args = run(["all"])
            assert (args.fresh_run, args.coverage, args.cov_clean_backend, args.cov_clean_js) == (False, None, False, False), entry

    @pytest.mark.parametrize(
        ("argv", "named"),
        [
            (["--quotable", "--resume", "all"], "--resume"),
            (["--quotable", "--fail-fast", "all"], "--fail-fast"),
            (["--quotable", "--coverage", "py", "all"], "--coverage"),
            (["--quotable", "--coverage", "js", "all"], "--coverage"),
            (["--quotable", "--run-status", "all"], "--run-status"),
            (["--quotable", "all", "--providers", "yfinance"], "--providers"),
            (["--quotable", "all", "--exclude-providers", "yfinance"], "--exclude-providers"),
            (["--quotable", "api", "all"], "all"),
            (["--quotable", "front-fx", "all"], "all"),
            (["--quotable", "all-backend"], "all"),
            (["--quotable"], "all"),
        ],
    )
    def test_quotable_refuses_what_would_make_the_run_partial(self, entries: dict, capsys: pytest.CaptureFixture, argv: list, named: str) -> None:
        """QU-03 — a command line that cannot be a whole run is refused by both entries with exit 2, before the campaign opens,
        and the message names what is wrong."""
        for entry, run in entries.items():
            rc, args = run(argv)
            out = capsys.readouterr().out
            assert (rc, args) == (2, None), f"{entry} {argv}: exit {rc}, campaign opened: {args is not None}"
            assert "--quotable" in out and named in out, f"{entry} {argv}: the refusal does not name {named}: {out!r}"

    def test_quotable_refuses_test_names(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
        """QU-04 — test names (the ``-k`` filter after the action) make a run partial: refused. Through the function the two
        entries call, since ``all`` takes no names at the parser."""
        args = SimpleNamespace(quotable=True, category="all", action=None, test_names=["test_one"], resume=False, fail_fast=False, coverage=None, list_tests=False, run_status=False, providers=None, exclude_providers=None)

        refusal = _cli._refused_quotable(args)

        assert refusal and "test names" in refusal and "--quotable" in refusal
        args.test_names = None
        assert _cli._refused_quotable(args) is None, "a whole `--quotable all` is not refused"
        args.list_tests = True
        assert "--list" in (_cli._refused_quotable(args) or ""), "the parser gives `all` no --list, but a caller that sets it is refused"
        args.list_tests = False
        args.quotable = False
        args.resume = True
        assert _cli._refused_quotable(args) is None, "without --quotable nothing is refused here"

    def test_the_run_starts_clean_and_remembers_the_tree(self, monkeypatch: pytest.MonkeyPatch, run_root: SimpleNamespace) -> None:
        """QU-05 — ``_apply_coverage_mode`` of a quotable run deletes the previous summary, notes in the ledger that the run is
        quotable-minded, and records the commit and the state of the tree as they are at the start (the run's own writes must not
        decide it)."""
        for name in ("_COVERAGE_MODE", "_RESUME_MODE", "_COVERAGE_SOURCE", "_COVERAGE_PY", "_COVERAGE_JS", "_FAIL_FAST"):
            monkeypatch.setattr(_common, name, getattr(_common, name))
        monkeypatch.setattr(_cli, "_clean_coverage_dirs", lambda *args: None)
        monkeypatch.setattr(_cli, "_clean_js_coverage_dirs", lambda: None)
        monkeypatch.setattr(_cli, "_coverage_capabilities", lambda category: {"py", "js"})
        run_root.data.mkdir(parents=True)
        (run_root.data / "coverage-summary.json").write_text("{}", encoding="utf-8")

        assert _cli._apply_coverage_mode(SimpleNamespace(category="all", fail_fast=False, quotable=True), "all", False, True, True)

        assert not (run_root.data / "coverage-summary.json").exists(), "the summary of the previous run is gone"
        assert run_root.ledger.quotable is True
        assert run_root.ledger.start_state == ("0123abc", False)

    def test_a_red_or_incomplete_run_writes_quotable_false_with_reasons(self, run_root: SimpleNamespace) -> None:
        """QU-06 — ``quotable`` is true only when the run asked for it, the tests passed and every piece is there; each failing
        condition adds its own reason. A whole run from a clean tree says ``quotable: true`` with no reason."""
        run_root.ledger.reset(categories=["all"], quotable=True)
        run_root.ledger.start_state = ("0123abc", False)
        missing = _coverage.PieceRow("Vitest unit", "frontend/coverage-js/unit/front-fx-1", "coverage-final.json, ≥1 file", "missing", False)

        whole = _coverage.summarize(run_root.ledger, [], success=True)
        red = _coverage.summarize(run_root.ledger, [], success=False)
        incomplete = _coverage.summarize(run_root.ledger, [missing], success=True)

        assert (whole["quotable"], whole["reasons"]) == (True, [])
        assert red["quotable"] is False and any("red" in reason for reason in red["reasons"])
        assert incomplete["quotable"] is False and any("piece" in reason for reason in incomplete["reasons"])
        assert json.loads((run_root.data / "coverage-summary.json").read_text(encoding="utf-8"))["quotable"] is False, "the file holds the last summary written"

    def test_a_dirty_tree_is_not_quotable(self, monkeypatch: pytest.MonkeyPatch, run_root: SimpleNamespace) -> None:
        """QU-07 — a tree with changes when the run began, one whose state git cannot tell, or a commit that moved during the run
        is not quotable; changes the run itself made to the tree after its start do not count (the state is read at the start)."""
        run_root.ledger.reset(categories=["all"], quotable=True)

        run_root.ledger.start_state = ("0123abc", True)
        assert any("dirty" in reason for reason in _coverage.summarize(run_root.ledger, [], success=True)["reasons"])

        run_root.ledger.start_state = (None, None)
        assert any("unknown" in reason for reason in _coverage.summarize(run_root.ledger, [], success=True)["reasons"])

        run_root.ledger.start_state = ("0123abc", False)
        monkeypatch.setattr(_coverage, "_git_state", lambda: ("0123abc", True))
        assert _coverage.summarize(run_root.ledger, [], success=True)["quotable"] is True, "dirty at the end, clean at the start"

        monkeypatch.setattr(_coverage, "_git_state", lambda: ("fedcba9", False))
        moved = _coverage.summarize(run_root.ledger, [], success=True)
        assert moved["quotable"] is False and any("moved" in reason for reason in moved["reasons"])
