"""Execution: run a plan's groups as concurrent workers, isolated by resources.

A worker does not merely get permission to run — it gets a lot of exclusive
resources. Today that lot is one thing, ``COVERAGE_FILE``, because only PURE
units are parallelised and they need nothing else. The database, the port and
the E2E user join the lot when the write classes are activated; the shape here
is built to take them.

The failure policy is deliberate: at the first red the scheduler stops handing
out work, but workers already running are left to finish. Killing a worker
mid-flight loses its coverage, and coverage that goes missing without failing
is the most expensive kind of defect this project has met.
"""

import itertools
import os
import subprocess
import time

from ._common import Colors, apply_subprocess_coverage_env, print_error, print_info, print_success
from ._inventory import PROJECT_ROOT

PARTS_DIR = PROJECT_ROOT / ".coverage_data" / "parts"
# The worker data files of this runner process. pytest-cov erases `<COVERAGE_FILE>`
# and `<COVERAGE_FILE>.*` when a worker starts, so a fixed name let one parallel pass
# destroy whatever an earlier pass had left uncombined; a directory per run, and a
# name per pass, keep every pass's parts until a combine folds them in, and never let
# a run fold in another run's leftovers.
RUN_PARTS_DIR = PARTS_DIR / f"run-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
_PASS_NUMBERS = itertools.count(1)


def _worker_env(index: int, coverage: bool, pass_no: int = 1) -> dict:
    """The exclusive resource lot handed to worker ``index``."""
    from backend.test_scripts.test_db_config import get_test_database_url

    env = os.environ.copy()
    env["LIBREFOLIO_TEST_MODE"] = "1"
    env["DATABASE_URL"] = get_test_database_url()
    if coverage:
        # Per-worker data file: this is what replaces the copy-in/copy-out of a
        # single global .coverage, which is the reason two processes could not
        # both collect coverage before.
        RUN_PARTS_DIR.mkdir(parents=True, exist_ok=True)
        env["COVERAGE_FILE"] = str(RUN_PARTS_DIR / f".coverage.p{pass_no}.w{index}")
        env["COVERAGE_RUN"] = "1"
        # Spawn children (spawn_worker.py) and multiprocessing's resource tracker
        # start their own tracer and write `.coverage.p{pass}.w{index}.<host>.<pid>.<rand>`
        # beside it — same prefix, so pytest-cov's session-finish combine collects
        # those that finished, and combine_coverage() the ones that finish later.
        apply_subprocess_coverage_env(env)
    return env


def _pytest_cmd(paths: list, coverage: bool, junit: str = None) -> list:
    from scripts.cli_base import pipenv_prefix

    # -p no:cacheprovider: workers must not fight over a shared .pytest_cache.
    cmd = [*pipenv_prefix(), "python", "-m", "pytest", *paths, "-q", "--no-header", "-p", "no:cacheprovider"]
    if junit:
        cmd.append(f"--junit-xml={junit}")
    if coverage:
        # No --cov-report here: every worker would write the same htmlcov-backend
        # directory at once. The combined report is produced by the parent.
        cmd.extend(["--cov=backend/app", "--cov-report="])
    return cmd


def read_unit_durations(known_paths: set) -> dict:
    """Per-unit seconds, summed from the workers' junit reports.

    pytest leaves ``file`` empty but fills ``classname`` with the dotted module,
    so the mapping back to a unit path is exact — which matters, because the
    alternative (sharing a group's wall time evenly over its units) would erase
    precisely the differences the scheduler needs to balance on.
    """
    import xml.etree.ElementTree as ET

    totals: dict = {}
    for report in sorted(PARTS_DIR.glob("junit.w*.xml")):
        try:
            root = ET.parse(report).getroot()
        except (OSError, ET.ParseError):
            continue
        for case in root.iter("testcase"):
            parts = (case.get("classname") or "").split(".")
            if parts[:2] == ["backend", "test_scripts"]:
                parts = parts[2:]
            # Class-based tests append the class name, so walk back to the module.
            while parts:
                candidate = "/".join(parts) + ".py"
                if candidate in known_paths:
                    try:
                        totals[candidate] = totals.get(candidate, 0.0) + float(case.get("time") or 0)
                    except ValueError:
                        pass
                    break
                parts = parts[:-1]
    return {p: round(t, 3) for p, t in totals.items()}


def read_failed_units(known_paths: set) -> set:
    """Unit paths with at least one failure or error, from the workers' junit reports.

    The parallel pass marks every unit it ran as covered, so the serial pass skips
    them. Without naming *which* ones failed, the category verdict has nothing to
    go on and the suite summary prints "ALL TESTS PASSED" over a run that exits 1.
    Same classname-to-path walk as :func:`read_unit_durations`, so the two agree
    by construction.

    A worker that dies before writing its report (timeout, collection error,
    SIGKILL) leaves nothing to read, so callers must keep treating a non-zero
    return code as failure in its own right.
    """
    import xml.etree.ElementTree as ET

    failed: set = set()
    for report in sorted(PARTS_DIR.glob("junit.w*.xml")):
        try:
            root = ET.parse(report).getroot()
        except (OSError, ET.ParseError):
            continue
        for case in root.iter("testcase"):
            if case.find("failure") is None and case.find("error") is None:
                continue
            parts = (case.get("classname") or "").split(".")
            if parts[:2] == ["backend", "test_scripts"]:
                parts = parts[2:]
            while parts:
                candidate = "/".join(parts) + ".py"
                if candidate in known_paths:
                    failed.add(candidate)
                    break
                parts = parts[:-1]
    return failed


def _write_worker_logs(results: list) -> None:
    """Deposit each worker's captured output when --log-dir is active.

    The parallel pass captures output by design (it cannot interleave several
    workers on one terminal), so without this the detail of a green worker was
    simply discarded — exactly the material needed to explain an intermittent red.
    """
    from ._archive import log_file_for
    from ._common import get_log_dir

    log_dir = get_log_dir()
    if not log_dir:
        return
    for r in results:
        try:
            path = log_file_for(log_dir, "backend-parallel", f"worker{r['index']}")
            header = f"# worker {r['index']} | exit={r['returncode']} | {r['elapsed']:.1f}s\n" f"# units ({len(r['paths'])}):\n" + "".join(f"#   {p}\n" for p in r["paths"]) + "\n"
            path.write_text(header + (r["output"] or ""), encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: S110 — per-worker log writing must not fail the run
            _ = exc


def run_groups(groups: list, verbose: bool = False, coverage: bool = False, timeout: int = 3600) -> dict:  # noqa: C901 — flat worker spawn/collect loops, no nested logic
    """Run each group in its own process; return per-group outcomes.

    Returns ``{"ok": bool, "results": [...], "wall": seconds}`` where each result
    carries the group index, exit code, elapsed time, paths and captured output.
    """
    if not groups:
        return {"ok": True, "results": [], "wall": 0.0}

    started = time.time()
    running = []
    pass_no = next(_PASS_NUMBERS)
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    for old in PARTS_DIR.glob("junit.w*.xml"):
        old.unlink(missing_ok=True)
    for i, paths in enumerate(groups):
        junit = str(PARTS_DIR / f"junit.w{i}.xml")
        cmd = _pytest_cmd([f"backend/test_scripts/{p}" for p in paths], coverage, junit)
        proc = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=_worker_env(i, coverage, pass_no),
        )
        running.append({"index": i, "proc": proc, "paths": paths, "t0": time.time()})
        print_info(f"worker {i}: {len(paths)} unit(s) started")

    results = []
    for w in running:
        try:
            output, _ = w["proc"].communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            w["proc"].kill()
            output, _ = w["proc"].communicate()
            output = (output or "") + f"\n[worker {w['index']}] timed out after {timeout}s"
        rc = w["proc"].returncode
        elapsed = time.time() - w["t0"]
        results.append(
            {
                "index": w["index"],
                "returncode": rc,
                "elapsed": elapsed,
                "paths": w["paths"],
                "output": output or "",
            }
        )

    results.sort(key=lambda r: r["index"])
    wall = time.time() - started
    ok = all(r["returncode"] == 0 for r in results)

    _write_worker_logs(results)

    for r in results:
        summary = (r["output"].strip().splitlines() or ["(no output)"])[-1]
        mark = f"{Colors.GREEN}✓{Colors.NC}" if r["returncode"] == 0 else f"{Colors.RED}✗{Colors.NC}"
        print(f"  {mark} worker {r['index']}: {r['elapsed']:6.1f}s  {len(r['paths']):3d} unit(s) | {summary}")

    if not ok:
        for r in results:
            if r["returncode"] != 0:
                print_error(f"worker {r['index']} failed (exit {r['returncode']})")
                if not verbose:
                    print(r["output"])
    else:
        print_success(f"parallel pass green in {wall:.1f}s")

    return {"ok": ok, "results": results, "wall": wall}


def combine_coverage(source: str = "backend") -> bool:
    """Fold this run's worker data files into the accumulated database.

    Python coverage is a SQLite database and combining is native to it, which is
    what makes per-worker files viable in the first place. coverage.py is handed
    the directory, not a list of names (see ``combine_coverage_dir``): a writer
    still saving when the workers return made one name vanish, and the whole
    combine fail. A part is removed only once it has been folded in, so a failure
    here loses nothing — and what it leaves, the next pass of this run picks up.
    """
    import shutil

    from ._coverage import _coverage_parts, _drop_empty_parts, combine_coverage_dir

    parts = _drop_empty_parts(_coverage_parts(RUN_PARTS_DIR))
    if not parts:
        _remove_run_parts_dir()
        return True

    data_dir = PROJECT_ROOT / ".coverage_data"
    data_dir.mkdir(exist_ok=True)
    accumulated = data_dir / source
    main = PROJECT_ROOT / ".coverage"

    if accumulated.exists():
        shutil.copy2(str(accumulated), str(main))

    ok, leftovers, detail = combine_coverage_dir(RUN_PARTS_DIR, cwd=PROJECT_ROOT, append=True)
    # Even on a failure: a part that was folded in is gone from the directory, and
    # only `.coverage` holds it now.
    if main.exists():
        shutil.copy2(str(main), str(accumulated))
    if not ok:
        where = RUN_PARTS_DIR.relative_to(PROJECT_ROOT) if RUN_PARTS_DIR.is_relative_to(PROJECT_ROOT) else RUN_PARTS_DIR
        print_error(f"coverage combine failed: {detail or 'some parts could not be folded in'}")
        # Said here so that a run whose tests are all green does not deliver partial numbers in silence.
        print_error(f"   {len(leftovers)} part(s) left in {where}/, not in the report: {', '.join(p.name for p in leftovers)}")
        return False

    _remove_run_parts_dir()
    print_success(f"combined {len(parts)} worker coverage file(s) into .coverage_data/{source}")
    return True


def _remove_run_parts_dir() -> None:
    """Remove this run's parts directory once a combine has emptied it: runs must not pile up directories."""
    if RUN_PARTS_DIR == PARTS_DIR:
        return
    try:
        RUN_PARTS_DIR.rmdir()
    except OSError:
        pass  # absent, or not empty: a failed combine names what it left
