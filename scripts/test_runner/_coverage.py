"""
Coverage finalization, reporting, and management commands.
"""

import contextlib
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import webbrowser
from pathlib import Path
from typing import NamedTuple

from scripts.cli_base import pipenv_prefix

from . import _common
from ._archive import archive_path
from ._common import (
    PROJECT_ROOT,
    Colors,
    print_error,
    print_info,
    print_section,
    print_success,
    print_warning,
)

JS_COVERAGE_DIR = "coverage-js"


class CoverageLedger:
    """What a run tells the coverage to expect (project 71, block 3): the record the end of the run is checked against.

    Every Vitest group the runner launches under JS coverage is told to write into its own directory
    (``coverage-js/unit/<label>-<n>``, relative to ``frontend/``, through ``LF_VITEST_COVERAGE_DIR``), and the directory is noted
    here the moment the group is launched. The runner used to leave the directory to Vitest (a dated name the runner never
    saw), so a group that wrote nothing could not be told from a group that never ran.

    The other launchers note what they leave too (step 3.3): a pytest run under Python coverage the database of its source
    (``.coverage_data/backend`` or ``frontend``), a Playwright run or the shared server under Python coverage the E2E server's
    (``.coverage_data/frontend``), a Playwright run under JS coverage its worker files. Only what was launched is expected:
    a run that skipped everything (``--resume``) expects nothing.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self, categories: list[str] | None = None, quotable: bool = False) -> None:
        """Forget everything: a run starts from an empty ledger (``_apply_coverage_mode``), naming the categories it runs and
        whether it is a ``--quotable`` one; ``start_state`` is the commit and the state of the tree at its start (``None`` until
        a quotable run records it)."""
        self.categories: list[str] = list(categories or [])
        self.quotable = quotable
        self.start_state: tuple[str | None, bool | None] | None = None
        self.units: list[str] = []
        self.python: set[str] = set()
        self.e2e_js = 0
        self.backend_server = False
        self._counts: dict[str, int] = {}

    def expect_unit(self, label: str) -> str:
        """Note a Vitest group launched under the name ``label`` and return the directory it must write: ``coverage-js/unit/<label>-<n>``, ``n`` counting per label from 1."""
        self._counts[label] = self._counts.get(label, 0) + 1
        directory = f"{JS_COVERAGE_DIR}/unit/{label}-{self._counts[label]}"
        self.units.append(directory)
        return directory

    def expect_python(self, database: str) -> None:
        """Note a launch whose Python coverage ends in ``.coverage_data/<database>`` (``backend`` or ``frontend``)."""
        self.python.add(database)

    def expect_backend_server(self) -> None:
        """Note the shared backend started under Python coverage by a backend category (``api``, ``e2e``): its parts are folded into
        ``.coverage_data/backend`` by that run's finalizer, so the run expects them folded."""
        self.backend_server = True

    def expect_e2e_js(self) -> None:
        """Note a Playwright run under JS coverage: its workers write ``coverage-js/e2e-raw/worker-*.json``."""
        self.e2e_js += 1


#: The ledger of this process's run: one run per process.
LEDGER = CoverageLedger()


def vitest_env(label: str, env: dict | None = None) -> dict | None:
    """The environment of a Vitest launch: under JS coverage, ``env`` (or a copy of the runner's own) with
    ``LF_VITEST_COVERAGE_DIR`` set to the directory the ledger now expects under ``label``; otherwise ``env`` unchanged
    (``None`` keeps ``subprocess.run`` inheriting the runner's). Every launch of Vitest goes through here, the consolidated
    groups and the actions that call it themselves alike, so no directory is written that the ledger has not seen."""
    if not _common._COVERAGE_JS:
        return env
    env = dict(os.environ if env is None else env)
    env["LF_VITEST_COVERAGE_DIR"] = LEDGER.expect_unit(label)
    return env


# coverage.py's final name for a parallel data file: the last step of its write() appends `.H<hash>h`.
_FINISHED_PART = re.compile(r"\.H\w{10}h$")


def _js_dir() -> Path:
    return PROJECT_ROOT / "frontend" / JS_COVERAGE_DIR


def _coverage_parts(directory: Path) -> list:
    """The parallel coverage data files in ``directory``: ``.coverage.*``, as coverage.py collects them."""
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob(".coverage.*") if p.is_file() and not p.name.endswith("-journal"))


def _holds_no_data(part: Path) -> bool:
    """True for a finished coverage database that measured no file: there is nothing in it to combine.

    coverage.py's SIGTERM handler is not re-entrant: a SIGTERM that lands while a process is
    already saving starts a nested save, which closes the first one's connection mid-transaction,
    renames the file to its final ``.H<hash>h`` name and kills the process. What is left is the
    schema without a row — the writer's data was lost inside the writer, where no combine can
    reach it. Only a finished name is judged: a transient one may still be filling up. The file
    is opened read-only, so a part that vanishes meanwhile is never re-created.
    """
    if not _FINISHED_PART.search(part.name):
        return False
    return _measured_files(part) == 0


def _measured_files(database: Path) -> int | None:
    """How many files a coverage database measured (rows of its ``file`` table), or ``None`` when it cannot be read. Opened
    read-only, so a database that vanishes meanwhile is never re-created."""
    try:
        con = sqlite3.connect(f"{database.absolute().as_uri()}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        return con.execute("select count(*) from file").fetchone()[0]
    except sqlite3.Error:
        return None
    finally:
        con.close()


def _drop_empty_parts(parts: list) -> list:
    """Remove the finished parts that hold no data, name them, and return the others."""
    empty = [p for p in parts if _holds_no_data(p)]
    if not empty:
        return parts
    for part in empty:
        part.unlink(missing_ok=True)
    print_warning(f"   {len(empty)} empty coverage part(s) removed — their writer was stopped while saving, its data never reached the file: {', '.join(p.name for p in empty)}")
    return [p for p in parts if p not in empty]


def clean_coverage_parts(parts_dir: Path) -> int:
    """Remove the worker coverage left in ``parts_dir`` by earlier runs: loose ``.coverage*`` files and ``run-*`` directories.

    A clean backend measure must not inherit the parts of a run whose combine failed.
    The junit reports beside them are not coverage data, and the parallel pass rewrites them.
    """
    if not parts_dir.is_dir():
        return 0
    removed = 0
    for entry in sorted(parts_dir.iterdir()):
        if entry.is_dir() and entry.name.startswith("run-"):
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
        elif entry.is_file() and entry.name.startswith(".coverage"):
            entry.unlink(missing_ok=True)
            removed += 1
    if removed:
        print(f"{Colors.GREEN}🗑️  Removed {removed} leftover worker coverage item(s) — loose parts and run-* directories — from .coverage_data/parts/{Colors.NC}")
    return removed


def combine_coverage_dir(directory: Path, *, cwd: Path, append: bool, keep: bool = False, max_rounds: int = 3) -> tuple:
    """Fold every parallel data file in ``directory`` into ``cwd/.coverage``.

    coverage.py is given the *directory*, never a list of names. A list is a
    snapshot, and a process still saving when it is taken — the multiprocessing
    resource tracker outlives its pytest worker by a few milliseconds — renames
    its file to ``….X<rand>x.H<hash>h`` before ``coverage combine`` starts. One
    vanished name makes coverage.py refuse the whole combine: that is how the
    07/10 run lost two parallel passes. Given the directory, coverage lists it in
    its own process and skips an entry that vanishes.

    A file can also land after coverage's own listing. What a round leaves is new,
    so it gets another round, up to ``max_rounds``; with ``keep`` nothing is
    consumed and one round is all there is.

    A finished part that holds no data (see ``_holds_no_data``) is removed and
    named before each round and once more at the end: it has nothing to fold in,
    so it never fails the combine. With ``keep`` nothing is removed.

    Returns ``(ok, leftovers, detail)``: the parts no round could fold in, and
    coverage.py's own words when its last round failed.
    """
    env = os.environ.copy()
    env.pop("COVERAGE_FILE", None)
    detail = ""
    seen: set = set()
    for _ in range(1 if keep else max_rounds):
        before = _coverage_parts(directory) if keep else _drop_empty_parts(_coverage_parts(directory))
        if not before:
            break
        late = [p.name for p in before if p.name not in seen]
        if seen and late:
            print_info(f"   {len(late)} part(s) landed after the previous round, combining them too: {', '.join(late)}")
        seen.update(p.name for p in before)
        cmd = [*pipenv_prefix(), "coverage", "combine", *(["--append"] if append else []), *(["--keep"] if keep else []), str(directory)]
        result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, env=env)
        output = f"{result.stdout}\n{result.stderr}"
        # coverage.py prints its refusals on stdout, not stderr.
        failed = result.returncode != 0 and "No data to combine" not in output
        detail = " ".join(line.strip() for line in output.splitlines() if line.strip() and "Loading .env" not in line) if failed else ""
        # What this round folded in is in `.coverage` now: the next round adds to it.
        append = True
        if _coverage_parts(directory) == before:
            break  # nothing folded in, nothing new: another round would only repeat this one
    if keep:
        return not detail, [], detail
    leftovers = _drop_empty_parts(_coverage_parts(directory))
    return not leftovers and not detail, leftovers, detail


def _clean_js_coverage_dirs() -> None:
    """Wipe JS coverage data before a run.

    Unlike Python coverage — which accumulates in ``.coverage_data`` across
    invocations by design — JS data is rebuilt from scratch every time: the raw
    V8 output is tied to a specific build, so mixing runs across a rebuild would
    mean remapping bytes onto sources that have since moved.

    The retry is not defensive padding. ``shutil.rmtree`` lists a directory,
    empties what it saw, then ``rmdir``s it — and on macOS the Finder drops a
    fresh ``.DS_Store`` into any folder it is looking at, including one being
    deleted. The window is milliseconds wide and the result was an unhandled
    ``OSError: Directory not empty`` that killed the whole test command before a
    single test ran.

    Failing to clean must still be loud: stale V8 offsets remapped onto a rebuilt
    bundle produce a report that is wrong without being broken.
    """
    js_dir = _js_dir()
    if not js_dir.exists():
        return
    for attempt in (1, 2, 3):
        try:
            shutil.rmtree(js_dir)
            print(f"{Colors.GREEN}🗑️  Removed frontend/{JS_COVERAGE_DIR}/{Colors.NC}")
            return
        except OSError as exc:
            if attempt == 3:
                raise RuntimeError(f"Could not remove frontend/{JS_COVERAGE_DIR}/ ({exc}). JS coverage " "cannot be reused across a rebuild, so the run is stopped rather " "than left to report stale data. Remove the directory by hand and retry.") from exc
            time.sleep(0.2)


def _run_frontend_cmd(cmd: list, label: str) -> bool:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT / "frontend"),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except FileNotFoundError:
        print_warning(f"{cmd[0]} not found: skipping JS coverage report")
        return False
    except subprocess.TimeoutExpired:
        print_warning(f"JS coverage ({label}) timed out")
        return False

    if result.returncode != 0:
        print_warning(f"JS coverage ({label}) failed: {(result.stderr or result.stdout).strip()[-500:]}")
        return False
    return True


def _finalize_js_coverage() -> None:
    """Merge JS/Svelte coverage from vitest and Playwright into one report.

    Mirrors what ``_finalize_coverage`` does for Python, with
    ``istanbul-lib-coverage`` playing the part of ``coverage combine`` and the
    per-process JSON files the part of the ``.coverage.*`` files.

    Two sources feed in, in the same format:

    - **unit** — vitest's istanbul provider writes a ``coverage-final.json`` at
      the end of every process, and the runner launches vitest once per
      category, each into its own ``unit/<tag>`` directory.
    - **e2e** — each Playwright worker sums its tests' ``window.__coverage__``
      and writes one JSON per worker into ``e2e-raw/``
      (``worker-<parallelIndex>-<pid>.json``, ``e2e/fixtures/js-coverage-sink.ts``).

    That both levels are istanbul is what makes the merge mean anything: while
    the E2E level was V8, the two counted different things and the combined
    percentage was an average of two questions. It also puts the branches of
    every ``{#if}`` in the denominator — V8 reports an empty branch map for a
    Svelte template, so the whole conditional surface of the UI was invisible.
    """
    js_dir = _js_dir()
    if not js_dir.exists():
        print_warning("No JS coverage data collected")
        return

    print_section("JS/Svelte Coverage")

    def report(out: str, name: str, inputs: list[str]) -> bool:
        return _run_frontend_cmd(["node", "scripts/js-coverage-report.js", f"{JS_COVERAGE_DIR}/{out}", name, *inputs], out)

    sources = []

    # --- unit: one istanbul JSON per vitest process ---
    unit_root = js_dir / "unit"
    unit_jsons = sorted(unit_root.glob("*/coverage-final.json")) if unit_root.is_dir() else []
    if unit_jsons and report("unit-combined", "unit", [f"{JS_COVERAGE_DIR}/unit"]):
        print(f"   {Colors.GREEN}📊 Generated frontend/{JS_COVERAGE_DIR}/unit-combined/ ({len(unit_jsons)} run){Colors.NC}")
        sources.append(f"{JS_COVERAGE_DIR}/unit-combined/coverage-final.json")

    # --- e2e: one istanbul JSON per Playwright worker, each the sum of its tests ---
    e2e_raw = js_dir / "e2e-raw"
    e2e_jsons = sorted(e2e_raw.glob("*.json")) if e2e_raw.is_dir() else []
    if e2e_jsons and report("e2e", "e2e", [f"{JS_COVERAGE_DIR}/e2e-raw"]):
        print(f"   {Colors.GREEN}📊 Generated frontend/{JS_COVERAGE_DIR}/e2e/ ({len(e2e_jsons)} worker file(s)){Colors.NC}")
        sources.append(f"{JS_COVERAGE_DIR}/e2e/coverage-final.json")

    if not sources:
        print_warning("No JS coverage data to report")
        return

    # The combined report is built from the two *reports*, not from the raw data
    # again: each level has already been remapped onto source coordinates and
    # re-keyed, which is precisely what makes them addable. Re-reading the raw
    # data here would repeat several minutes of sourcemap work for no gain.
    if len(sources) == 2:
        if report("combined", "unit + E2E", sources):
            print(f"   {Colors.GREEN}📊 Generated frontend/{JS_COVERAGE_DIR}/combined/{Colors.NC}")
            print_info("   Open with: ./dev.py test coverage show js")
            print_info("   Find the gaps: ./dev.py test coverage-report --lang js --summary")
    else:
        only = "unit-combined" if "unit" in sources[0] else "e2e"
        print_info(f"   Single source only — see frontend/{JS_COVERAGE_DIR}/{only}/index.html")
        print_info("   Find the gaps: ./dev.py test coverage-report --lang js --summary")


class PythonFinalized(NamedTuple):
    """What ``_finalize_coverage`` did with the E2E server's data in this run: how many parts it found in the project root, and
    whether it saved the combined data into ``.coverage_data/frontend``; for one backend category, whether it folded them into
    the pytest data it saved in ``.coverage_data/backend`` (``backend_folded``). The databases accumulate across runs, so
    their rows alone do not say that this run's server wrote anything."""

    server_parts: int
    frontend_saved: bool
    backend_folded: bool = False


def _finalize_coverage(is_front: bool, is_all: bool) -> PythonFinalized:  # noqa: C901 — TODO(P2-refactor): mode matrix × combine/html pipeline, nested error handling
    """Finalize coverage data after test runs; return what was done with the E2E server's data (``PythonFinalized``)."""
    cwd = Path(os.getcwd())
    main_cov = cwd / ".coverage"
    data_dir = cwd / ".coverage_data"
    data_dir.mkdir(exist_ok=True)
    backend_db = data_dir / "backend"
    frontend_db = data_dir / "frontend"
    html_dir = "htmlcov-backend-e2e" if is_front else "htmlcov-backend"

    def _archive_db(db_path: Path, label: str):
        archive_path(db_path, target_dir=data_dir, label=label)

    server_parts, frontend_saved, backend_folded = 0, False, False

    if is_front or is_all:
        if main_cov.exists():
            if is_all and not backend_db.exists():
                shutil.copy2(str(main_cov), str(backend_db))
            main_cov.unlink()

        pid_files = _coverage_parts(cwd)
        server_parts = len(pid_files)

        print(f"{Colors.YELLOW}📊 Combining coverage data from server subprocess(es)...{Colors.NC}")
        if pid_files:
            print(f"   Found {len(pid_files)} coverage data file(s): " f"{', '.join(f.name for f in pid_files[:5])}" f"{'...' if len(pid_files) > 5 else ''}")
            combined, leftovers, detail = combine_coverage_dir(cwd, cwd=cwd, append=False)
            if not combined:
                if detail:
                    print_warning(f"   coverage combine: {detail}")
                if leftovers:
                    print_warning(f"   {len(leftovers)} data file(s) not combined: {', '.join(f.name for f in leftovers)}")

            if main_cov.exists():
                _archive_db(frontend_db, "frontend")
                shutil.copy2(str(main_cov), str(frontend_db))
                frontend_saved = True
                print(f"   {Colors.GREEN}💾 Saved frontend coverage → .coverage_data/frontend{Colors.NC}")
        else:
            print_warning("   No .coverage.* files found! Server may not have written coverage data.")
            print(f"   {Colors.YELLOW}Hint: check that './dev.py server --coverage' starts the server " f"with 'coverage run'{Colors.NC}")

    if is_all:
        if backend_db.exists():
            shutil.copy2(str(backend_db), str(main_cov))
            subprocess.run([*pipenv_prefix(), "coverage", "html", "-d", "htmlcov-backend", "--title", "LibreFolio Backend Coverage", "--ignore-errors"], cwd=os.getcwd(), capture_output=True, text=True)
            print(f"   {Colors.GREEN}📊 Generated htmlcov-backend/{Colors.NC}")

        if frontend_db.exists():
            shutil.copy2(str(frontend_db), str(main_cov))
            r_fe = subprocess.run([*pipenv_prefix(), "coverage", "html", "-d", "htmlcov-backend-e2e", "--title", "LibreFolio Frontend E2E → Backend Coverage", "--ignore-errors"], cwd=os.getcwd(), capture_output=True, text=True)
            if r_fe.returncode != 0:
                print_warning(f"coverage html (frontend) failed: {r_fe.stderr.strip()}")
            else:
                print(f"   {Colors.GREEN}📊 Generated htmlcov-backend-e2e/{Colors.NC}")

        combine_srcs = [str(f) for f in (backend_db, frontend_db) if f.exists()]
        if combine_srcs:
            if main_cov.exists():
                main_cov.unlink()
            print(f"{Colors.YELLOW}📊 Merging backend + frontend for combined report...{Colors.NC}")
            r_merge = subprocess.run([*pipenv_prefix(), "coverage", "combine", "--keep"] + combine_srcs, cwd=os.getcwd(), capture_output=True, text=True)
            if r_merge.returncode != 0:
                # Come sopra: coverage.py parla su stdout quando il combine rifiuta.
                err_lines = [l for l in (r_merge.stdout + "\n" + r_merge.stderr).strip().splitlines() if "Loading .env" not in l and l.strip()]
                if err_lines:
                    print_warning(f"   coverage combine: {' '.join(err_lines)}")

        r = subprocess.run([*pipenv_prefix(), "coverage", "html", "-d", "htmlcov", "--title", "LibreFolio Combined Coverage", "--ignore-errors"], cwd=os.getcwd(), capture_output=True, text=True)
        if r.returncode != 0:
            print_warning(f"coverage html failed: {r.stderr.strip()}")
    elif is_front:
        r = subprocess.run([*pipenv_prefix(), "coverage", "html", "-d", html_dir, "--title", "LibreFolio Frontend E2E → Backend Coverage", "--ignore-errors"], cwd=os.getcwd(), capture_output=True, text=True)
        if r.returncode != 0:
            print_warning(f"coverage html failed: {r.stderr.strip()}")
    else:
        # One backend category. The shared backend of `api` and `e2e` writes its parts into the working directory; they are
        # folded into the pytest data (`.coverage`, appended to) before it is saved, so this run's database holds them. They
        # used to wait there for the next run's pytest-cov, one run late and into whichever database that run saved.
        parts = _coverage_parts(cwd)
        server_parts = len(parts)
        if parts:
            print(f"{Colors.YELLOW}📊 Folding {len(parts)} shared-backend part(s) into the backend coverage...{Colors.NC}")
            folded, leftovers, detail = combine_coverage_dir(cwd, cwd=cwd, append=True)
            backend_folded = folded
            if detail:
                print_warning(f"   coverage combine: {detail}")
            if leftovers:
                print_warning(f"   {len(leftovers)} data file(s) not combined: {', '.join(f.name for f in leftovers)}")
        if main_cov.exists():
            _archive_db(backend_db, "backend")
            shutil.copy2(str(main_cov), str(backend_db))
            print(f"   {Colors.GREEN}💾 Saved backend coverage → .coverage_data/backend{Colors.NC}")

    subprocess.run([*pipenv_prefix(), "coverage", "report", "--skip-covered", "--ignore-errors"], cwd=os.getcwd(), capture_output=False, text=True)
    print_info("   ↑ coverage.py's TOTAL counts lines + branches together: not a number to quote. The pure numbers, lines and branches apart, close the run.")

    print()
    print(f"{Colors.GREEN}📊 Detailed reports:{Colors.NC}")
    print(f"   HTML: {Colors.BLUE}{html_dir}/index.html{Colors.NC}")
    print(f"   Data: {Colors.BLUE}.coverage{Colors.NC}")
    if backend_db.exists():
        print(f"   Backend DB: {Colors.BLUE}.coverage_data/backend{Colors.NC}")
    if frontend_db.exists():
        print(f"   Frontend DB: {Colors.BLUE}.coverage_data/frontend{Colors.NC}")
    print()
    print(f"{Colors.YELLOW}💡 View HTML report:{Colors.NC}")
    if is_all:
        print("└─▶ $ ./dev.py test coverage show combined")
    else:
        print(f"└─▶ $ ./dev.py test coverage show {'frontend' if is_front else 'backend'}")
        print("└─▶ $ ./dev.py test coverage show combined   # merge backend + frontend")
    print()

    return PythonFinalized(server_parts, frontend_saved, backend_folded)


class PieceRow(NamedTuple):
    """One row of the completeness table: a piece of coverage the run launched, where it must be, and what is there."""

    piece: str
    where: str
    expected: str
    found: str
    ok: bool


def _istanbul_files(path: Path) -> int | None:
    """How many files an istanbul JSON measured (a ``coverage-final.json``, a Playwright worker file), or ``None`` when it is
    missing or cannot be read whole — a file cut short is not JSON."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return len(data) if isinstance(data, dict) else None


def _named(paths: list, limit: int = 3) -> str:
    names = [p.name for p in paths[:limit]]
    return ", ".join(names) + ("…" if len(paths) > limit else "")


def check_coverage_pieces(ledger: CoverageLedger, mode: str, finalized: PythonFinalized | None = None) -> list[PieceRow]:  # noqa: C901 — flat list of independent piece checks
    """Compare what the run launched under coverage (``ledger``) with what the finalizers left on disk: one row per expected piece.

    - every ``.coverage_data/<database>`` a launch noted holds at least one measured file (the ``file`` table, read-only);
    - where the finalizer combines the server's parts (``mode`` ``frontend`` or ``all``), no ``.coverage.*`` is left in the
      project root: a part left there is data no report holds;
    - every Vitest directory of the ledger holds a ``coverage-final.json`` with at least one file;
    - after a Playwright run under JS coverage, at least one worker file, every one readable whole, and no ``*.tmp`` left;
    - the JS reports of what ran: ``unit-combined`` for Vitest, ``e2e`` for Playwright, ``combined`` for both.

    Only what was launched is a row: a JS run of Vitest alone expects no worker file, a backend run no E2E data. ``mode`` is the
    finalizer's: ``backend`` (one backend category), ``frontend`` (a front-* category or all-frontend) or ``all``. ``finalized``
    is what the Python finalizer did: the E2E database accumulates across runs, so where it combines the server's parts, the
    check also wants this run's parts saved into it (the JS data needs no such row: a JS run wipes it before it starts).
    """
    root = PROJECT_ROOT
    js = root / "frontend" / JS_COVERAGE_DIR
    rows: list[PieceRow] = []

    for database in sorted(ledger.python):
        path = root / ".coverage_data" / database
        files = _measured_files(path) if path.is_file() else None
        found = "missing" if not path.is_file() else ("unreadable" if files is None else f"{files} file(s)")
        rows.append(PieceRow("Python data", f".coverage_data/{database}", "≥1 measured file", found, bool(files)))

    if "frontend" in ledger.python and mode in ("frontend", "all") and finalized is not None:
        found = f"{finalized.server_parts} part(s), " + ("saved" if finalized.frontend_saved else "nothing saved")
        rows.append(PieceRow("E2E server data, this run", ".coverage.* → .coverage_data/frontend", "parts found and saved", found, finalized.frontend_saved))

    if ledger.backend_server and mode == "backend" and finalized is not None:
        found = f"{finalized.server_parts} part(s), " + ("folded" if finalized.backend_folded else "none folded")
        rows.append(PieceRow("backend server data, this run", ".coverage.* → .coverage_data/backend", "parts found and folded", found, finalized.backend_folded))

    if (ledger.python and mode in ("frontend", "all")) or (ledger.backend_server and mode == "backend"):
        left = _coverage_parts(root)
        found = f"{len(left)} left" + (f": {_named(left)}" if left else "")
        rows.append(PieceRow("server parts", ".coverage.* (project root)", "none left after the combine", found, not left))

    for directory in ledger.units:
        path = root / "frontend" / directory / "coverage-final.json"
        files = _istanbul_files(path)
        found = "missing" if not path.exists() else ("unreadable" if files is None else f"{files} file(s)")
        rows.append(PieceRow("Vitest unit", f"frontend/{directory}", "coverage-final.json, ≥1 file", found, bool(files)))

    if ledger.e2e_js:
        raw = js / "e2e-raw"
        workers = sorted(raw.glob("worker-*.json")) if raw.is_dir() else []
        torn = [w for w in workers if _istanbul_files(w) is None]
        found = f"{len(workers) - len(torn)} readable" + (f", torn: {_named(torn)}" if torn else "")
        rows.append(PieceRow("E2E worker files", f"frontend/{JS_COVERAGE_DIR}/e2e-raw/worker-*.json", "≥1, all readable", found, len(workers) > len(torn) and not torn))
        unfinished = sorted(raw.glob("*.tmp")) if raw.is_dir() else []
        found = f"{len(unfinished)}" + (f": {_named(unfinished)}" if unfinished else "")
        rows.append(PieceRow("E2E unfinished writes", f"frontend/{JS_COVERAGE_DIR}/e2e-raw/*.tmp", "none", found, not unfinished))

    reports = (["unit-combined"] if ledger.units else []) + (["e2e"] if ledger.e2e_js else []) + (["combined"] if ledger.units and ledger.e2e_js else [])
    for name in reports:
        path = js / name / "coverage-final.json"
        files = _istanbul_files(path)
        found = "missing" if not path.exists() else ("unreadable" if files is None else f"{files} file(s)")
        rows.append(PieceRow("JS report", f"frontend/{JS_COVERAGE_DIR}/{name}", "coverage-final.json, ≥1 file", found, bool(files)))

    return rows


def report_coverage_pieces(ledger: CoverageLedger, mode: str, finalized: PythonFinalized | None = None) -> list[PieceRow]:
    """Print the completeness table «piece · where · expected · found» and return its rows: the run is whole when every row is
    ok. A red row makes the run red whatever its tests said: numbers measured with a piece missing are not the run's measure.
    Nothing launched under coverage, nothing to print."""
    rows = check_coverage_pieces(ledger, mode, finalized)
    if not rows:
        return rows
    # The mark is an emoji, two columns wide on a terminal and one character long: it stays out of the width arithmetic.
    header = ("piece", "where", "expected", "found")
    cells = [(row.piece, row.where, row.expected, row.found) for row in rows]
    widths = [max(len(line[i]) for line in (header, *cells)) for i in range(len(header))]
    print_section("Coverage pieces")
    for mark, line in (("  ", header), *zip(("✅" if row.ok else "❌" for row in rows), cells, strict=True)):
        print(f"   {mark}  " + "  ".join(cell.ljust(width) for cell, width in zip(line, widths, strict=True)).rstrip())
    missing = [row for row in rows if not row.ok]
    if missing:
        print_error(f"Coverage incomplete: {len(missing)} of {len(rows)} piece(s) missing or empty — the run is red; its numbers are not the whole measure")
        return rows
    print_success(f"Coverage complete: {len(rows)} piece(s), all there")
    return rows


# ---------------------------------------------------------------------------
# Pure numbers (step 3.4): lines and branches apart, never coverage.py's mixed TOTAL
# ---------------------------------------------------------------------------

#: ``financial_math`` reported on its own (one home of every financial calculation): the folder and its subfolders. coverage.py's
#: ``*`` crosses ``/`` in an include pattern, so ``fifo/``, ``lots/`` and ``portfolio/`` are in.
FINANCIAL_MATH_INCLUDE = "*/backend/app/services/financial_math/*"
SUMMARY_SCHEMA = "lf-coverage-summary/1"
#: The frontend levels of the summary and the report directory each one is read from.
_JS_LEVELS = {"unit": "unit-combined", "e2e": "e2e", "combined": "combined"}


def _measure(covered: int, total: int) -> dict:
    """Covered / total with the percentage computed here, to two decimals; ``None`` when there is nothing to count (no branch is
    neither 0 % nor 100 %)."""
    return {"covered": covered, "total": total, "pct": round(100 * covered / total, 2) if total else None}


def backend_totals(database: Path, include: str | None = None) -> dict | None:
    """Lines and branches of one coverage database, apart: ``totals`` of a JSON report (``covered_lines`` / ``num_statements``,
    ``covered_branches`` / ``num_branches``), never its ``percent_covered``, which mixes the two as coverage.py's TOTAL does.
    ``include`` restricts it to a folder (``FINANCIAL_MATH_INCLUDE``). The report reads the repository's ``.coveragerc`` (its
    exclusions), as ``coverage json`` run from the project root would. ``None`` for a missing database, one without a measured
    file, or an ``include`` that matches nothing: never a zero that would read as «measured, nothing covered»."""
    if not database.is_file() or not _measured_files(database):
        return None
    import coverage  # noqa: PLC0415 — the runner's own interpreter has it; only coverage runs need it

    rc_file = PROJECT_ROOT / ".coveragerc"
    reader = coverage.Coverage(data_file=str(database), config_file=str(rc_file) if rc_file.is_file() else False)
    with tempfile.TemporaryDirectory(prefix="lf_cov_json_") as scratch:
        out = Path(scratch) / "report.json"
        try:
            reader.load()
            with contextlib.redirect_stdout(io.StringIO()):
                reader.json_report(outfile=str(out), include=include, ignore_errors=True)
        except coverage.exceptions.NoDataError:
            return None
        except coverage.exceptions.CoverageException as exc:
            print_warning(f"   coverage json on {database.name} failed: {exc}")
            return None
        report = json.loads(out.read_text(encoding="utf-8"))
    totals = report["totals"]
    return {"files": len(report["files"]), "lines": _measure(totals["covered_lines"], totals["num_statements"]), "branches": _measure(totals.get("covered_branches", 0), totals.get("num_branches", 0))}


def _union_totals(databases: list[Path]) -> tuple[dict | None, dict | None]:
    """The totals of the union of ``databases`` (pytest and E2E server): the whole, and ``financial_math`` alone. Built in a
    scratch database, so neither source is touched."""
    present = [db for db in databases if db.is_file() and _measured_files(db)]
    if not present:
        return None, None
    from coverage import CoverageData  # noqa: PLC0415 — see backend_totals
    from coverage.exceptions import DataError  # noqa: PLC0415

    with tempfile.TemporaryDirectory(prefix="lf_cov_union_") as scratch:
        union_path = Path(scratch) / "union"
        union = CoverageData(basename=str(union_path))
        try:
            for database in present:
                part = CoverageData(basename=str(database))
                part.read()
                union.update(part)
            union.write()
        except DataError as exc:
            print_warning(f"   the backend databases cannot be combined: {exc}")
            return None, None
        return backend_totals(union_path), backend_totals(union_path, include=FINANCIAL_MATH_INCLUDE)


def frontend_totals() -> dict:
    """The three frontend levels (``unit``, ``e2e``, ``combined``) from the ``summary.json`` ``js-coverage-report.js`` writes
    beside each report: lines and branches covered / total (the percentage computed here), the files read and skipped. A level
    without its summary is ``None``."""
    levels: dict = {}
    for level, directory in _JS_LEVELS.items():
        path = PROJECT_ROOT / "frontend" / JS_COVERAGE_DIR / directory / "summary.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            levels[level] = {"files": data["files"], "lines": _measure(data["lines"]["covered"], data["lines"]["total"]), "branches": _measure(data["branches"]["covered"], data["branches"]["total"])}
        except (OSError, ValueError, KeyError, TypeError):
            levels[level] = None
    return levels


def _git_state() -> tuple[str | None, bool | None]:
    """The commit the run measured and whether the tree had changes (``git status --porcelain``); ``None`` when git cannot say."""
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None, None
    sha = head.stdout.strip() if head.returncode == 0 else None
    dirty = bool(status.stdout.strip()) if status.returncode == 0 else None
    return sha or None, dirty


def _cell(measure: dict | None) -> str:
    if not measure:
        return "—"
    pct = "  n/a  " if measure["pct"] is None else f"{measure['pct']:6.2f} %"
    return f"{pct}  ({measure['covered']}/{measure['total']})"


def _files_cell(value: dict | None) -> str:
    """A backend base counts its measured files; a frontend level the JSON files its report read and skipped."""
    if not value:
        return "—"
    files = value["files"]
    return str(files) if isinstance(files, int) else f"{files['read']} read, {files['skipped']} skipped"


def forget_summary() -> None:
    """Delete ``.coverage_data/coverage-summary.json``: a quotable run starts without the summary of an earlier one."""
    (PROJECT_ROOT / ".coverage_data" / "coverage-summary.json").unlink(missing_ok=True)


def summarize(ledger: CoverageLedger, rows: list[PieceRow], *, success: bool) -> dict:
    """Write ``.coverage_data/coverage-summary.json`` (schema ``lf-coverage-summary/1``) and print its numbers.

    The backend bases are what this run measured (the ledger): ``pytest`` (``.coverage_data/backend``), ``server`` (the E2E
    server, ``.coverage_data/frontend``), their union ``combined``, and ``financial_math``, the union restricted to its folder.
    The frontend levels come from the JS reports. Every number is lines and branches apart (``backend_totals``). ``quotable`` is
    true only for a ``--quotable all`` run (step 3.5) whose tests passed, whose pieces are all there and whose tree was clean
    when it began (``ledger.start_state``, read before the run's own writes); ``reasons`` says what kept it from it, one per
    condition, the commit moving during the run included. The numbers are a note, not a gate (D6): nothing here turns a run red.
    """
    sha, dirty = ledger.start_state or _git_state()
    missing = [row for row in rows if not row.ok]
    reasons = []
    if not ledger.quotable:
        reasons.append("not a --quotable all run")
    if not success:
        reasons.append("tests red")
    if missing:
        reasons.append(f"{len(missing)} coverage piece(s) missing")
    if dirty is None or sha is None:
        reasons.append("git state unknown")
    elif dirty:
        reasons.append("working tree dirty at the start")
    elif ledger.start_state and _git_state()[0] != sha:
        reasons.append("the commit moved during the run")

    data_dir = PROJECT_ROOT / ".coverage_data"
    measured = [data_dir / name for name in ("backend", "frontend") if name in ledger.python]
    combined, financial_math = _union_totals(measured)
    summary = {
        "schema": SUMMARY_SCHEMA,
        "quotable": not reasons,
        "reasons": reasons,
        "sha": sha,
        "dirty": dirty,
        "workers": getattr(_common, "_E2E_WORKERS", 1),
        "argv": sys.argv[1:],
        "categories": ledger.categories,
        "backend": {
            "pytest": backend_totals(data_dir / "backend") if "backend" in ledger.python else None,
            "server": backend_totals(data_dir / "frontend") if "frontend" in ledger.python else None,
            "combined": combined,
            "financial_math": financial_math,
        },
        "frontend": frontend_totals(),
        "pieces": [row._asdict() for row in rows],
    }
    data_dir.mkdir(exist_ok=True)
    (data_dir / "coverage-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    table = [(f"backend {name}", value) for name, value in summary["backend"].items()] + [(f"frontend {name}", value) for name, value in summary["frontend"].items()]
    cells = [(label, _cell(value and value["lines"]), _cell(value and value["branches"]), _files_cell(value)) for label, value in table]
    header = ("base", "lines", "branches", "files")
    widths = [max(len(line[i]) for line in (header, *cells)) for i in range(len(header))]
    print_section("Coverage numbers — lines and branches apart (a note, not a gate)")
    for line in (header, *cells):
        print("   " + "  ".join(cell.ljust(width) for cell, width in zip(line, widths, strict=True)).rstrip())
    verdict = "quotable" if summary["quotable"] else f"not quotable: {'; '.join(reasons)}"
    print_info(f"   Summary → .coverage_data/coverage-summary.json ({verdict})")
    return summary


def _handle_coverage_command(args) -> int:
    """Handle ./dev.py test coverage show [backend|frontend|combined]."""
    action = getattr(args, "cov_action", None)
    if not action:
        print_error("Usage: ./dev.py test coverage show [backend|frontend|combined]")
        return 1

    if action == "show":
        target = getattr(args, "target", "combined")
        return _coverage_show(target)
    elif action == "combine":
        return _coverage_combine()
    else:
        print_error(f"Unknown coverage action: {action}")
        return 1


def _coverage_show(target: str) -> int:
    """Open coverage HTML report for the given target."""
    dir_map = {
        "backend": "htmlcov-backend",
        "frontend": "htmlcov-backend-e2e",
        "combined": "htmlcov",
        "js": "frontend/coverage-js/combined",
        "js-unit": "frontend/coverage-js/unit-combined",
        "js-e2e": "frontend/coverage-js/e2e",
    }
    title_map = {
        "backend": "LibreFolio Backend Test Coverage",
        "frontend": "LibreFolio Frontend E2E → Backend Coverage",
        "combined": "LibreFolio Combined Coverage (Backend + Frontend)",
    }

    html_dir = PROJECT_ROOT / dir_map[target]
    index_file = html_dir / "index.html"

    if target.startswith("js"):
        if not index_file.exists():
            print_error(f"No {target} coverage report found at {html_dir}/")
            print_info("Run tests with JS coverage first:")
            print_info("  ./dev.py test --coverage js front-asset all")
            return 1
    elif target == "combined":
        print(f"{Colors.YELLOW}📊 Combining all coverage data...{Colors.NC}")
        _coverage_combine_internal(html_dir=str(html_dir), title=title_map[target])
    elif not index_file.exists():
        print_error(f"No {target} coverage report found at {html_dir}/")
        print_info("Run tests with --coverage first:")
        if target == "backend":
            print_info("  ./dev.py test --coverage api all")
        else:
            print_info("  ./dev.py test --coverage front-fx all")
        return 1

    if index_file.exists():
        print_success(f"Opening {target} coverage report: {html_dir}/index.html")
        # `open` exists on macOS only: the standard library picks the platform's opener (xdg-open on Linux, the
        # default browser on Windows), and a machine with no browser just leaves the path printed above.
        if not webbrowser.open(index_file.resolve().as_uri()):
            print_info(f"No browser to open it here: {index_file}")
        return 0
    else:
        print_error(f"Failed to generate {target} coverage report")
        return 1


def _coverage_combine() -> int:
    """Combine all .coverage.* files and generate combined HTML report."""
    return _coverage_combine_internal(html_dir="htmlcov", title="LibreFolio Combined Coverage (Backend + Frontend)")


def _combine_keeping(cwd: Path, snapshots: list) -> None:
    """``coverage combine --keep`` into ``cwd/.coverage``: the saved snapshots by name, otherwise the parallel parts as a directory.

    The snapshots are two stable files that nothing rewrites. Parallel parts may still be renamed by
    their writer, so they go through ``combine_coverage_dir`` like every other combine of parallel data.
    """
    if snapshots:
        result = subprocess.run([*pipenv_prefix(), "coverage", "combine", "--keep", *snapshots], cwd=str(cwd), capture_output=True, text=True)
        if result.returncode != 0 and "No data to combine" not in result.stderr:
            print_warning(f"coverage combine: {result.stderr.strip()}")
        return
    combined, _, detail = combine_coverage_dir(cwd, cwd=cwd, append=False, keep=True)
    if not combined and detail:
        print_warning(f"coverage combine: {detail}")


def _coverage_combine_internal(html_dir: str = "htmlcov", title: str = "LibreFolio Coverage") -> int:
    """Internal: combine coverage data and generate HTML report."""
    cwd = Path(os.getcwd())
    backend_cov = cwd / ".coverage.backend"
    frontend_cov = cwd / ".coverage.frontend"

    combine_files = []
    snapshots = backend_cov.exists() or frontend_cov.exists()
    if snapshots:
        if backend_cov.exists():
            combine_files.append(str(backend_cov))
        if frontend_cov.exists():
            combine_files.append(str(frontend_cov))
        print(f"   Using saved snapshots: {', '.join(f.name for f in [backend_cov, frontend_cov] if f.exists())}")
    else:
        combine_files = [str(f) for f in _coverage_parts(cwd)]
        if combine_files:
            print(f"   Using {len(combine_files)} parallel data file(s)")

    if not combine_files:
        main_cov = cwd / ".coverage"
        if not main_cov.exists():
            print_warning("No coverage data found to combine")
            return 1
    else:
        main_cov = cwd / ".coverage"
        if main_cov.exists():
            main_cov.unlink()

        _combine_keeping(cwd, combine_files if snapshots else [])

    result = subprocess.run([*pipenv_prefix(), "coverage", "html", "-d", html_dir, "--title", title], cwd=os.getcwd(), capture_output=True, text=True)
    if result.returncode == 0:
        print_success(f"Coverage report generated: {html_dir}/index.html")
    else:
        print_error(f"Failed to generate report: {result.stderr.strip()}")
        return 1

    subprocess.run([*pipenv_prefix(), "coverage", "report", "--skip-covered"], cwd=os.getcwd(), capture_output=False, text=True)
    return 0
