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

import os
import subprocess
import time


from ._common import Colors, print_error, print_info, print_success
from ._inventory import PROJECT_ROOT

PARTS_DIR = PROJECT_ROOT / ".coverage_data" / "parts"


def _worker_env(index: int, coverage: bool) -> dict:
    """The exclusive resource lot handed to worker ``index``."""
    from backend.test_scripts.test_db_config import TEST_DATABASE_URL

    env = os.environ.copy()
    env["LIBREFOLIO_TEST_MODE"] = "1"
    env["DATABASE_URL"] = TEST_DATABASE_URL
    if coverage:
        # Per-worker data file: this is what replaces the copy-in/copy-out of a
        # single global .coverage, which is the reason two processes could not
        # both collect coverage before.
        PARTS_DIR.mkdir(parents=True, exist_ok=True)
        env["COVERAGE_FILE"] = str(PARTS_DIR / f".coverage.w{index}")
        env["COVERAGE_RUN"] = "1"
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
            header = (
                f"# worker {r['index']} | exit={r['returncode']} | {r['elapsed']:.1f}s\n"
                f"# units ({len(r['paths'])}):\n"
                + "".join(f"#   {p}\n" for p in r["paths"])
                + "\n"
            )
            path.write_text(header + (r["output"] or ""), encoding="utf-8", errors="replace")
        except Exception:
            pass


def run_groups(groups: list, verbose: bool = False, coverage: bool = False, timeout: int = 3600) -> dict:
    """Run each group in its own process; return per-group outcomes.

    Returns ``{"ok": bool, "results": [...], "wall": seconds}`` where each result
    carries the group index, exit code, elapsed time, paths and captured output.
    """
    if not groups:
        return {"ok": True, "results": [], "wall": 0.0}

    started = time.time()
    running = []
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
            env=_worker_env(i, coverage),
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
    """Fold the per-worker data files into the accumulated database.

    Python coverage is a SQLite database and combining is native to it, which is
    what makes per-worker files viable in the first place. The parts are removed
    only once they have been folded in, so a failure here loses nothing.
    """
    from scripts.cli_base import pipenv_prefix

    parts = sorted(PARTS_DIR.glob(".coverage.w*")) if PARTS_DIR.exists() else []
    if not parts:
        return True

    data_dir = PROJECT_ROOT / ".coverage_data"
    data_dir.mkdir(exist_ok=True)
    accumulated = data_dir / source
    main = PROJECT_ROOT / ".coverage"

    import shutil

    if accumulated.exists():
        shutil.copy2(str(accumulated), str(main))

    env = os.environ.copy()
    env.pop("COVERAGE_FILE", None)
    result = subprocess.run(
        [*pipenv_prefix(), "coverage", "combine", "--append", *[str(p) for p in parts]],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        print_error(f"coverage combine failed: {result.stderr.strip()}")
        return False

    if main.exists():
        shutil.copy2(str(main), str(accumulated))
    for p in parts:
        p.unlink(missing_ok=True)
    print_success(f"combined {len(parts)} worker coverage file(s) into .coverage_data/{source}")
    return True
