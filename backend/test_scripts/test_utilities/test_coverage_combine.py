"""Red-first contract: coverage parts are combined as a directory, never as a list of names.

The defect
----------
``_executor.combine_coverage()`` lists ``PARTS_DIR.glob(".coverage.w*")`` the moment the
parallel workers return, then — about a second later, once ``pipenv run`` has started —
hands every file it saw to ``coverage combine --append`` **by name**. coverage.py 7.16
refuses an explicit path that is no longer a file (``coverage/data.py``,
``combinable_files``: ``NoDataError("Couldn't combine from non-existent path …")``) and the
WHOLE combine fails: not one part is folded in.

The names that vanish are coverage's own transient parallel names,
``<base>.<host>.pid<N>.X<rand>x``, which the end of ``CoverageData.write()`` renames to
``….X<rand>x.H<hash>h`` (``coverage/sqldata.py``). In the field the late writer is the
``multiprocessing`` resource tracker started by the spawn context of
``risk/quant/spawn_worker.py``: the ``COVERAGE_PROCESS_START`` wiring measures it as well,
and it exits about 10 ms after the pytest worker that started it — inside the runner's
window. ``_coverage._finalize_coverage()`` repeats the explicit-name pattern on the shared
backend's ``.coverage.*`` files in the working directory.

Evidence
--------
Full coverage run of 07/10 (``d07412899``, 2 workers): the parallel passes of 111 and of 54
units both ended in ``coverage combine failed: Couldn't combine from non-existent path
'….pid10917.Xm9GZYYx'`` / ``'….pid24531.X0pJBznx'``, while the parts directory still held
``….pid24531.X0pJBznx.HNQIp837rWOh`` — the missing path plus coverage's completion suffix.
The next pass's ``erase()`` then deleted those parts, so both passes' data was lost; the run
still ended green, with the backend at 36.8 %. Replayed on lane 6159: the tracker's
transient name appears 11 ms after its worker returns and is renamed at 34 ms, with the same
``HNQIp837rWOh``.

The host that hit it is called «MacBook Pro di Emanuele (2)». Spaces and parentheses are
harmless — coverage escapes its glob and the runner passes argv without a shell — but every
name below carries them, so the contract is proven on them too.

With the fix in place, the real ``services all --coverage --workers 2`` pass of 08/10 left one
part no round could fold in: ``….pid17336.XWmqACex.HuitnSoGmx4h``, a SQLite file with every
coverage.py table and zero rows — not even ``coverage_schema``'s version — which coverage
refuses as «isn't a coverage data file». Its writer lost the data inside itself: coverage's
SIGTERM handler is not re-entrant, so a SIGTERM during the atexit save started a nested save
that closed the outer connection mid-transaction, gave the file its final ``.H<hash>h`` name
and killed the process.

The contract
------------
1. A part that coverage renames while the combine is starting is still combined.
2. A part that lands after coverage's own listing is combined in a later round, and nothing
   is left behind in the parts directory.
3. The shared backend's parts in the working directory follow the same rule, and
   ``.coveragerc`` is never taken for a part.
4. A failed combine turns the parallel pass red: lost coverage is a verdict, not a log line.
5. A run's parts live in their own directory under ``parts/``. A successful combine leaves no
   run directory behind; a failed one keeps it, with the part it could not combine, and names
   both — so run directories never pile up, and what is kept is kept on purpose.
6. ``--cov-clean-backend`` cleans ``parts/`` of coverage data — loose parts and run
   directories alike — and leaves the junit reports alone.
7. A leftover with coverage's final name (``.H`` + 10 word characters + ``h``) whose database
   holds coverage's schema and an empty ``file`` table has nothing to combine: it is removed,
   named with a warning, and the combine does not fail. Every other part no round could fold
   in stays red, kept and named; a part with a transient name is never judged empty, since it
   may still be filling up.

How it is reproduced
--------------------
Deterministically, never with a sleep: ``subprocess.run`` is wrapped so that the first
``coverage combine`` it launches is preceded, or followed, by exactly what the late writer
does. The parts are real coverage.py databases with one distinct fake source each, so the
combined database names every part that was folded in. ``coverage`` runs as
``sys.executable -m coverage`` inside ``tmp_path``, with every ``COVERAGE_*`` variable that
would make it measure itself removed: a ``--coverage`` run of this file never writes into the
directory under test, nor into the repository. Code that works from ``os.getcwd()``
(``_finalize_coverage``, ``_clean_coverage_dirs``) runs with the working directory moved into
``tmp_path`` as well.
"""

from __future__ import annotations

import contextlib
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from coverage import CoverageData
from coverage.sqldata import SCHEMA

from scripts import cli_base
from scripts.test_runner import _cli, _common, _coverage, _executor, _scheduler, _suites
from scripts.test_runner._inventory import PURE

HOST = "MacBook Pro di Emanuele (2)"  # the machine that hit the race: spaces and parentheses, no dots

# A worker pass's parts, as the run of 07/10 left them in .coverage_data/parts/.
W0 = ".coverage.w0"
W1 = ".coverage.w1"
W1_SPAWN_CHILD = f".coverage.w1.{HOST}.pid24532.XxpJi2Cx.H4iMCLM7Cjwh"  # finished: the double suffix
W1_TRACKER = f".coverage.w1.{HOST}.pid24531.X0pJBznx"  # transient: still being written...
W1_TRACKER_DONE = f"{W1_TRACKER}.HNQIp837rWOh"  # ...until coverage's write() renames it
W0_LATE = f".coverage.w0.{HOST}.pid24533.XlAte00x.HlAtePart00h"  # finished after coverage's own listing

# The shared backend's parts, in the working directory.
SERVER = f".coverage.{HOST}.pid111.Xaaaaaax.Hbbbbbbbbbbh"
SERVER_TRACKER = f".coverage.{HOST}.pid222.Xccccccx"
SERVER_TRACKER_DONE = f"{SERVER_TRACKER}.Hddddddddddh"

# The fix's layout: one directory per run under parts/, the pass in each part's name.
RUN_DIR = "run-20261008-110000-4242"
P1_W0 = ".coverage.p1.w0"
P1_W1 = ".coverage.p1.w1"
P1_W1_SPAWN_CHILD = f".coverage.p1.w1.{HOST}.pid24532.XxpJi2Cx.H4iMCLM7Cjwh"
P1_W0_UNREADABLE = f".coverage.p1.w0.{HOST}.pid9.Xabcdefx.Hzzzzzzzzzzh"  # named like a finished part...
NOT_A_DATABASE = b"not a coverage database: no SQLite header here, only text long enough for SQLite to read and refuse\n" * 2  # ...holding none
LEFTOVER_RUN_DIR = "run-20261007-130500-123"  # left behind by an earlier run
CURRENT_RUN_DIR = "run-20261008-112600-777"  # this run's: not created yet when the clean-up runs

# Coverage's schema and not one row: what the 08/10 services pass left. A final name means nothing
# will ever write to the file again; a transient one (coverage's own shape: X + 6 characters + x)
# means it may still be filling up.
P1_W0_EMPTY = f".coverage.p1.w0.{HOST}.pid17336.XWmqACex.HuitnSoGmx4h"
P1_W0_EMPTY_TRANSIENT = f".coverage.p1.w0.{HOST}.pid17337.XtRaNs1x"
SERVER_EMPTY = f".coverage.{HOST}.pid333.Xeeeeeex.Hffffffffffh"

# One distinct fake source per part: the combined database then names every part folded in.
SOURCE = {
    W0: "/fake/w0.py",
    W1: "/fake/w1.py",
    W1_SPAWN_CHILD: "/fake/w1_spawn_child.py",
    W1_TRACKER: "/fake/w1_resource_tracker.py",
    W0_LATE: "/fake/w0_late.py",
    SERVER: "/fake/server.py",
    SERVER_TRACKER: "/fake/server_resource_tracker.py",
    P1_W0: "/fake/p1_w0.py",
    P1_W1: "/fake/p1_w1.py",
    P1_W1_SPAWN_CHILD: "/fake/p1_w1_spawn_child.py",
}

NON_EXISTENT = "Couldn't combine from non-existent path"

# Every binding through which the runner's coverage code reaches pipenv, the project root or the
# parts directory: the ones held today, plus the ones a fix could hoist to module level (hence
# raising=False below), so that no case can ever reach the repository's own .coverage_data.
_PREFIX_HOLDERS = (cli_base, _common, _coverage, _executor, _suites)
_ROOT_HOLDERS = (_common, _coverage, _executor, _suites)
_PARTS_HOLDERS = (_executor, _suites)


def _write_part(directory: Path, name: str) -> Path:
    """A real coverage.py data file (arcs, as with ``branch = true``) measuring ``SOURCE[name]``."""
    path = directory / name
    data = CoverageData(str(path))
    data.add_arcs({SOURCE[name]: {(-1, 1), (1, 2), (2, -1)}})
    data.write()
    return path


def _write_empty_part(directory: Path, name: str) -> Path:
    """coverage.py's schema and not one row, ``coverage_schema``'s version included: coverage refuses it
    («isn't a coverage data file») exactly as it refused the real leftover."""
    path = directory / name
    with contextlib.closing(sqlite3.connect(path)) as con:
        con.executescript(SCHEMA)
    return path


def _measured(db: Path) -> set[str]:
    """The sources a coverage database measures; empty when it was never written."""
    if not db.is_file():
        return set()
    data = CoverageData(str(db))
    data.read()
    return data.measured_files()


def _parts_left(directory: Path, pattern: str) -> list[str]:
    return sorted(p.name for p in directory.glob(pattern))


def _this_interpreter() -> list:
    """``pipenv_prefix()`` for this process: the venv's own coverage, without pipenv's second of start-up."""
    return [sys.executable, "-m"]


def _point_parts_at(monkeypatch, parts: Path, run_parts: Path) -> None:
    """``PARTS_DIR`` and the fix's per-run ``RUN_PARTS_DIR``, on every module that may hold them."""
    for module in _PARTS_HOLDERS:
        monkeypatch.setattr(module, "PARTS_DIR", parts, raising=False)
        monkeypatch.setattr(module, "RUN_PARTS_DIR", run_parts, raising=False)


class _AroundFirstCombine:
    """``subprocess.run``, with a hook just before and/or just after the FIRST ``coverage combine``.

    ``before`` runs once the runner has listed its parts and before coverage starts: the window
    in which the resource tracker renames its file. ``after`` runs once coverage has listed and
    combined: a writer finishing too late for that round. Both runner modules call
    ``subprocess.run`` through ``import subprocess``, so replacing the attribute on the module
    reaches them wherever the combine is launched from.
    """

    def __init__(self, before=None, after=None) -> None:
        self._real_run = subprocess.run
        self._before = before
        self._after = after
        self.combines: list[list[str]] = []

    def __call__(self, *args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", ())
        argv = [str(token) for token in cmd] if isinstance(cmd, (list, tuple)) else str(cmd).split()
        is_combine = "combine" in argv
        first = is_combine and not self.combines
        if is_combine:
            self.combines.append(argv)
        if first and self._before is not None:
            self._before()
        result = self._real_run(*args, **kwargs)
        if first and self._after is not None:
            self._after()
        return result


def _hook_first_combine(monkeypatch, before=None, after=None) -> _AroundFirstCombine:
    hook = _AroundFirstCombine(before=before, after=after)
    monkeypatch.setattr(subprocess, "run", hook)
    return hook


@pytest.fixture
def coverage_sandbox(tmp_path, monkeypatch) -> Path:
    """``tmp_path`` as the project root, with the real ``coverage`` run by this interpreter.

    - every ``pipenv_prefix`` binding of the runner's coverage code → ``[sys.executable, "-m"]``:
      no pipenv, no second of start-up, the venv's own coverage (``_executor`` imports it inside
      ``combine_coverage()`` and ``_suites`` at module level, for ``coverage erase``);
    - every ``PROJECT_ROOT`` binding → ``tmp_path``: whichever one the code reads, it can never
      write into the repository;
    - no ``COVERAGE_*`` variable that would make a ``coverage`` subprocess measure itself
      (``COVERAGE_PROCESS_START`` / ``COVERAGE_PROCESS_CONFIG`` start a tracer through the
      venv's ``a1_coverage.pth``), write or erase elsewhere (``COVERAGE_FILE``: under
      ``--coverage`` it names this very worker's data file) or read the repository's
      configuration (``COVERAGE_RCFILE``, exported by coverage's own multiprocessing support).
    """
    for var in ("COVERAGE_FILE", "COVERAGE_PROCESS_START", "COVERAGE_PROCESS_CONFIG", "COVERAGE_RCFILE"):
        monkeypatch.delenv(var, raising=False)
    for module in _PREFIX_HOLDERS:
        monkeypatch.setattr(module, "pipenv_prefix", _this_interpreter, raising=False)
    for module in _ROOT_HOLDERS:
        monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path, raising=False)
    return tmp_path


@pytest.fixture
def parts_dir(coverage_sandbox, monkeypatch) -> Path:
    """The pass's parts directory, ``<root>/.coverage_data/parts`` like the real one.

    The fix moves the worker parts to a per-run subdirectory, ``RUN_PARTS_DIR``; pointing it at
    the same directory lets the same case run before and after the fix. The run-directory and
    clean-up cases point it at a real subdirectory instead.
    """
    parts = coverage_sandbox / ".coverage_data" / "parts"
    parts.mkdir(parents=True)
    _point_parts_at(monkeypatch, parts, parts)
    return parts


class TestWorkerPartsCombine:
    """``_executor.combine_coverage()``: a parallel pass's parts, folded into ``.coverage_data/backend``."""

    def test_a_part_renamed_while_coverage_starts_is_still_combined(self, coverage_sandbox, parts_dir, monkeypatch, capsys):
        """The race of 07/10, replayed: the resource tracker finishes its ``write()`` between the
        runner's listing and coverage's start, so a name the runner listed no longer exists.

        Red today: ``combine_coverage()`` returns False on «Couldn't combine from non-existent
        path», and not one of the four parts reaches the accumulated database.
        """
        for name in (W0, W1, W1_SPAWN_CHILD, W1_TRACKER):
            _write_part(parts_dir, name)
        hook = _hook_first_combine(monkeypatch, before=lambda: (parts_dir / W1_TRACKER).rename(parts_dir / W1_TRACKER_DONE))

        ok = _executor.combine_coverage("backend")
        out = capsys.readouterr().out

        assert hook.combines, "no `coverage combine` was launched: the race was never replayed"
        assert ok is True, f"combine_coverage() failed on a part that coverage itself renamed:\n{out}"
        assert _measured(coverage_sandbox / ".coverage_data" / "backend") == {SOURCE[name] for name in (W0, W1, W1_SPAWN_CHILD, W1_TRACKER)}
        assert _parts_left(parts_dir, ".coverage*") == []
        assert NON_EXISTENT not in out

    def test_a_part_landing_after_coverages_own_listing_is_combined_in_a_later_round(self, coverage_sandbox, parts_dir, monkeypatch, capsys):
        """A writer that finishes after ``coverage combine`` has listed the directory.

        No transient part here, on purpose: today's combine must succeed for the late arrival to
        be the only defect in view. Red today: ``combine_coverage()`` even returns True, while
        the late part stays in the parts directory and its source never reaches the database.
        """
        for name in (W0, W1, W1_SPAWN_CHILD):
            _write_part(parts_dir, name)
        hook = _hook_first_combine(monkeypatch, after=lambda: _write_part(parts_dir, W0_LATE))

        ok = _executor.combine_coverage("backend")
        out = capsys.readouterr().out
        measured = _measured(coverage_sandbox / ".coverage_data" / "backend")
        left = _parts_left(parts_dir, ".coverage*")

        assert hook.combines, "no `coverage combine` was launched: the late part was never written"
        assert SOURCE[W0_LATE] in measured, f"the part that landed after coverage's listing was not combined; left in parts/: {left}\n{out}"
        assert measured == {SOURCE[name] for name in (W0, W1, W1_SPAWN_CHILD, W0_LATE)}
        assert left == []
        assert ok is True, out


class TestSharedBackendPartsCombine:
    """``_coverage._finalize_coverage()``: the shared backend's parts, in the working directory."""

    def test_server_parts_in_the_cwd_are_all_combined_and_coveragerc_is_kept(self, coverage_sandbox, monkeypatch, capsys):
        """Frontend mode: the server's own part, plus its tracker renaming itself as the combine starts.

        ``coverage html`` and ``coverage report`` run too, through the same interpreter, on fake
        sources and with ``--ignore-errors``: nothing is asserted about them.

        Red today: the explicit list fails on the renamed name, so no ``.coverage`` is produced
        and ``.coverage_data/frontend`` is never written.
        """
        monkeypatch.chdir(coverage_sandbox)
        coveragerc = coverage_sandbox / ".coveragerc"
        coveragerc.write_text("[run]\nbranch = true\n", encoding="utf-8")
        for name in (SERVER, SERVER_TRACKER):
            _write_part(coverage_sandbox, name)
        hook = _hook_first_combine(monkeypatch, before=lambda: (coverage_sandbox / SERVER_TRACKER).rename(coverage_sandbox / SERVER_TRACKER_DONE))

        _coverage._finalize_coverage(is_front=True, is_all=False)
        out = capsys.readouterr().out

        assert hook.combines, "no `coverage combine` was launched: the race was never replayed"
        assert _measured(coverage_sandbox / ".coverage_data" / "frontend") == {SOURCE[SERVER], SOURCE[SERVER_TRACKER]}, f"the shared backend's parts did not reach .coverage_data/frontend:\n{out}"
        assert _parts_left(coverage_sandbox, ".coverage.*") == []
        assert coveragerc.is_file(), ".coveragerc was taken for a coverage part"
        assert NON_EXISTENT not in out


def _parallel_pass(monkeypatch, combined: bool) -> tuple:
    """Run ``_cli._parallel_for_scope`` with every ingredient of its verdict green but the combine.

    Returns ``(ok, combine_calls)``. ``_parallel_for_scope`` imports its collaborators inside its
    body (``from ._executor import …`` / ``from ._scheduler import …``), so replacing the module
    attributes is what it sees. A 1-tuple of classes skips the category setup: no DB, no server.
    """
    combine_calls: list = []

    def fake_combine(*args, **kwargs):
        combine_calls.append(args)
        return combined

    def fake_plan(*args, **kwargs):
        return {"errors": [], "groups": [["a"], ["b"]], "parallel_paths": ["a", "b"], "covered_actions": {"x"}, "by_action": {}}

    monkeypatch.setattr(_cli, "_parallel_classes", lambda *a, **k: (PURE,))
    monkeypatch.setattr(_scheduler, "plan", fake_plan)
    monkeypatch.setattr(_scheduler, "load_durations", lambda *a, **k: {})
    monkeypatch.setattr(_scheduler, "save_durations", lambda *a, **k: None)
    monkeypatch.setattr(_executor, "run_groups", lambda *a, **k: {"ok": True, "results": [], "wall": 0.0})
    monkeypatch.setattr(_executor, "combine_coverage", fake_combine)
    monkeypatch.setattr(_executor, "read_unit_durations", lambda *a, **k: {})
    monkeypatch.setattr(_executor, "read_failed_units", lambda *a, **k: set())
    monkeypatch.setattr(_common, "_COVERAGE_PY", True)
    monkeypatch.setattr(_common, "_COVERAGE_SOURCE", None)
    # Process-wide verdict state: whatever the pass records there must not outlive the test.
    monkeypatch.setattr(_common, "_FAILED_ACTIONS", set())

    ok, _ = _cli._parallel_for_scope(SimpleNamespace(assume_scoped=False), "services", 2, False)
    return ok, combine_calls


class TestParallelPassVerdict:
    """``_cli._parallel_for_scope()``: the combine's outcome is part of the parallel pass's verdict."""

    def test_a_failed_combine_turns_the_parallel_pass_red(self, monkeypatch):
        """The workers passed, nothing failed — only the combine did.

        Red today: ``_parallel_for_scope`` ignores what ``combine_coverage()`` returns and reports
        ok=True over a pass whose coverage was lost, so the run ends green on partial numbers.
        """
        ok, combine_calls = _parallel_pass(monkeypatch, combined=False)

        assert combine_calls, "combine_coverage() was never called: the verdict did not go through it"
        assert ok is False, "combine_coverage() failed, yet the parallel pass reported ok=True"

    def test_a_good_combine_leaves_the_parallel_pass_green(self, monkeypatch):
        """Control: the same pass with a combine that succeeds stays green (today and after the fix)."""
        ok, combine_calls = _parallel_pass(monkeypatch, combined=True)

        assert combine_calls, "combine_coverage() was never called: the verdict did not go through it"
        assert ok is True


class TestRunDirectories:
    """``_executor.combine_coverage()`` with the parts in ``parts/run-*``: no run directory piles up."""

    def test_a_successful_combine_leaves_no_run_directory_behind(self, coverage_sandbox, parts_dir, monkeypatch, capsys):
        """Coverage deletes the parts it combined; the runner removes the run directory they leave empty.

        Red today: ``combine_coverage()`` lists ``PARTS_DIR`` itself, finds no ``.coverage.w*`` there
        and returns True early — the run directory keeps its three parts, and none of them reaches
        the accumulated database.
        """
        run_dir = parts_dir / RUN_DIR
        run_dir.mkdir()
        for name in (P1_W0, P1_W1, P1_W1_SPAWN_CHILD):
            _write_part(run_dir, name)
        _point_parts_at(monkeypatch, parts_dir, run_dir)

        ok = _executor.combine_coverage("backend")
        captured = capsys.readouterr()

        assert ok is True, captured.out + captured.err
        assert not run_dir.exists(), f"{RUN_DIR}/ survived a successful combine, holding: {_parts_left(run_dir, '*')}"
        assert _measured(coverage_sandbox / ".coverage_data" / "backend") == {SOURCE[name] for name in (P1_W0, P1_W1, P1_W1_SPAWN_CHILD)}

    def test_a_part_coverage_cannot_read_keeps_its_run_directory_and_is_named(self, coverage_sandbox, parts_dir, monkeypatch, capsys):
        """A file named like a finished part, holding no database, beside two readable parts.

        coverage warns about it, keeps it and — because the others combined — exits 0: the verdict has
        to come from what is left in the run directory, not from coverage's exit code. Nothing is
        asserted about the readable parts: folding them in or keeping them are both honest.

        Red today: ``combine_coverage()`` never looks inside the run directory, prints nothing and
        returns True.
        """
        run_dir = parts_dir / RUN_DIR
        run_dir.mkdir()
        for name in (P1_W0, P1_W1):
            _write_part(run_dir, name)
        unreadable = run_dir / P1_W0_UNREADABLE
        unreadable.write_bytes(NOT_A_DATABASE)
        _point_parts_at(monkeypatch, parts_dir, run_dir)

        ok = _executor.combine_coverage("backend")
        captured = capsys.readouterr()
        printed = captured.out + captured.err

        assert ok is False, f"combine_coverage() reported success with a part it could not read in {RUN_DIR}/:\n{printed}"
        assert unreadable.is_file(), f"the unreadable part must stay in {RUN_DIR}/, where the failure says it is"
        assert RUN_DIR in printed, f"the failure does not name the run directory:\n{printed}"
        assert P1_W0_UNREADABLE in printed, f"the failure does not name the part it could not combine:\n{printed}"


class TestCleanBackendCoverage:
    """``--cov-clean-backend`` (``_suites._clean_coverage_dirs``): ``parts/`` holds coverage data too."""

    def test_clean_backend_empties_parts_of_coverage_data_and_keeps_the_junit_reports(self, coverage_sandbox, parts_dir, monkeypatch):
        """The leftovers of 07/10 — loose worker parts at the top of ``parts/`` — and the run directory
        of an earlier run. ``junit.w0.xml`` is not coverage data, and the parallel pass rewrites it
        anyway: it stays.

        Hermetic: the function works from ``os.getcwd()``, now ``tmp_path``; its ``coverage erase``
        runs there through this interpreter, and ``_archive_incompatible_coverage_dbs`` finds none of
        its candidates (``.coverage_data/backend``, ``.coverage_data/frontend``, ``.coverage``) there.

        Red today: ``_clean_coverage_dirs`` archives ``.coverage_data/backend`` and erases
        ``.coverage``, but never looks into ``parts/``.
        """
        monkeypatch.chdir(coverage_sandbox)
        for name in (W0, W1, W1_SPAWN_CHILD):
            _write_part(parts_dir, name)
        _write_part(parts_dir, W1_TRACKER).rename(parts_dir / W1_TRACKER_DONE)
        junit = parts_dir / "junit.w0.xml"
        junit.write_text('<testsuites><testsuite name="pytest" tests="0"/></testsuites>\n', encoding="utf-8")
        earlier_run = parts_dir / LEFTOVER_RUN_DIR
        earlier_run.mkdir()
        _write_part(earlier_run, P1_W0)
        # The clean-up runs at start-up, before this run has created its own directory.
        _point_parts_at(monkeypatch, parts_dir, parts_dir / CURRENT_RUN_DIR)

        _suites._clean_coverage_dirs(clean_backend=True, clean_frontend=False)

        assert _parts_left(parts_dir, ".coverage*") == [], "--cov-clean-backend left loose coverage parts at the top of parts/"
        assert _parts_left(parts_dir, "run-*") == [], "--cov-clean-backend left a run directory in parts/"
        assert junit.is_file(), "junit.w0.xml is not coverage data: --cov-clean-backend must leave it"


class TestEmptyFinishedParts:
    """A finished part holding coverage's schema and no data has nothing to combine: removed, named, not a failure."""

    def test_an_empty_finished_part_is_removed_named_and_does_not_fail_the_combine(self, coverage_sandbox, parts_dir, monkeypatch, capsys):
        """The leftover of the 08/10 ``services`` pass, beside two good parts in the run directory.

        Red today: coverage refuses it («isn't a coverage data file»), so ``combine_coverage()`` counts
        it among the parts it could not fold in, returns False and keeps the run directory.
        """
        run_dir = parts_dir / RUN_DIR
        run_dir.mkdir()
        for name in (P1_W0, P1_W1):
            _write_part(run_dir, name)
        _write_empty_part(run_dir, P1_W0_EMPTY)
        _point_parts_at(monkeypatch, parts_dir, run_dir)

        ok = _executor.combine_coverage("backend")
        captured = capsys.readouterr()
        printed = captured.out + captured.err

        assert ok is True, f"an empty finished part failed the combine:\n{printed}"
        assert not run_dir.exists(), f"{RUN_DIR}/ survived the combine, holding: {_parts_left(run_dir, '*')}"
        assert _measured(coverage_sandbox / ".coverage_data" / "backend") == {SOURCE[P1_W0], SOURCE[P1_W1]}
        assert P1_W0_EMPTY in printed, f"the removed part must be named:\n{printed}"

    def test_an_empty_part_with_a_transient_name_is_never_judged_empty(self, coverage_sandbox, parts_dir, monkeypatch, capsys):
        """Guard, green today and after: the same empty database without coverage's final ``.H<hash>h``
        may still be filling up. It is never deleted: it stays, and the combine is red and names it,
        like any other part no round could fold in.
        """
        run_dir = parts_dir / RUN_DIR
        run_dir.mkdir()
        for name in (P1_W0, P1_W1):
            _write_part(run_dir, name)
        transient = _write_empty_part(run_dir, P1_W0_EMPTY_TRANSIENT)
        _point_parts_at(monkeypatch, parts_dir, run_dir)

        ok = _executor.combine_coverage("backend")
        captured = capsys.readouterr()
        printed = captured.out + captured.err

        assert ok is False, f"a part that may still be filling up was judged empty:\n{printed}"
        assert transient.is_file(), "a part with a transient name was deleted"
        assert P1_W0_EMPTY_TRANSIENT in printed, f"the part left behind must be named:\n{printed}"

    def test_an_empty_finished_part_of_the_shared_backend_is_removed_and_named(self, coverage_sandbox, monkeypatch, capsys):
        """The same rule on the shared backend's parts in the working directory (frontend mode); no race hook.

        Red today: the empty part stays in the working directory — ``_finalize_coverage`` only warns that
        it was not combined.
        """
        monkeypatch.chdir(coverage_sandbox)
        coveragerc = coverage_sandbox / ".coveragerc"
        coveragerc.write_text("[run]\nbranch = true\n", encoding="utf-8")
        _write_part(coverage_sandbox, SERVER)
        _write_empty_part(coverage_sandbox, SERVER_EMPTY)

        _coverage._finalize_coverage(is_front=True, is_all=False)
        captured = capsys.readouterr()
        printed = captured.out + captured.err

        assert _measured(coverage_sandbox / ".coverage_data" / "frontend") == {SOURCE[SERVER]}, printed
        assert _parts_left(coverage_sandbox, ".coverage.*") == [], f"a part was left in the working directory:\n{printed}"
        assert coveragerc.is_file(), ".coveragerc was taken for a coverage part"
        assert SERVER_EMPTY in printed, f"the removed part must be named:\n{printed}"
