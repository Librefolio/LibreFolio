"""
Coverage finalization, reporting, and management commands.
"""

import os
import shutil
import subprocess
import time
from pathlib import Path

from scripts.cli_base import pipenv_prefix

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


def _js_dir() -> Path:
    return PROJECT_ROOT / "frontend" / JS_COVERAGE_DIR


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
                raise RuntimeError(
                    f"Could not remove frontend/{JS_COVERAGE_DIR}/ ({exc}). JS coverage "
                    "cannot be reused across a rebuild, so the run is stopped rather "
                    "than left to report stale data. Remove the directory by hand and retry."
                ) from exc
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
    - **e2e** — the Playwright fixture drops one JSON per test into
      ``e2e-raw/``, read straight out of ``window.__coverage__``.

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

    # --- e2e: one istanbul JSON per test ---
    e2e_raw = js_dir / "e2e-raw"
    e2e_jsons = sorted(e2e_raw.glob("*.json")) if e2e_raw.is_dir() else []
    if e2e_jsons and report("e2e", "e2e", [f"{JS_COVERAGE_DIR}/e2e-raw"]):
        print(f"   {Colors.GREEN}📊 Generated frontend/{JS_COVERAGE_DIR}/e2e/ ({len(e2e_jsons)} test){Colors.NC}")
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


def _finalize_coverage(is_front: bool, is_all: bool) -> str:  # noqa: C901 — TODO(P2-refactor): mode matrix × combine/html pipeline, nested error handling
    """Finalize coverage data after test runs."""
    cwd = Path(os.getcwd())
    main_cov = cwd / ".coverage"
    data_dir = cwd / ".coverage_data"
    data_dir.mkdir(exist_ok=True)
    backend_db = data_dir / "backend"
    frontend_db = data_dir / "frontend"
    html_dir = "htmlcov-backend-e2e" if is_front else "htmlcov-backend"

    def _archive_db(db_path: Path, label: str):
        archive_path(db_path, target_dir=data_dir, label=label)

    if is_front or is_all:
        if main_cov.exists():
            if is_all and not backend_db.exists():
                shutil.copy2(str(main_cov), str(backend_db))
            main_cov.unlink()

        SAVED_NAMES = frozenset({".coveragerc"})
        pid_files = [f for f in cwd.glob(".coverage.*") if f.name not in SAVED_NAMES]

        print(f"{Colors.YELLOW}📊 Combining coverage data from server subprocess(es)...{Colors.NC}")
        if pid_files:
            print(f"   Found {len(pid_files)} coverage data file(s): "
                  f"{', '.join(f.name for f in pid_files[:5])}"
                  f"{'...' if len(pid_files) > 5 else ''}")
            r_combine = subprocess.run(
                [*pipenv_prefix(), "coverage", "combine"] + [str(f) for f in pid_files],
                cwd=os.getcwd(), capture_output=True, text=True
            )
            if r_combine.returncode != 0:
                err_lines = [l for l in (r_combine.stdout + "\n" + r_combine.stderr).strip().splitlines()
                             if "Loading .env" not in l and l.strip()]
                if err_lines:
                    print_warning(f"   coverage combine: {' '.join(err_lines)}")

            if main_cov.exists():
                _archive_db(frontend_db, "frontend")
                shutil.copy2(str(main_cov), str(frontend_db))
                print(f"   {Colors.GREEN}💾 Saved frontend coverage → .coverage_data/frontend{Colors.NC}")
        else:
            print_warning("   No .coverage.* files found! Server may not have written coverage data.")
            print(f"   {Colors.YELLOW}Hint: check that './dev.py server --coverage' starts the server "
                  f"with 'coverage run'{Colors.NC}")

    if is_all:
        if backend_db.exists():
            shutil.copy2(str(backend_db), str(main_cov))
            subprocess.run(
                [*pipenv_prefix(), "coverage", "html", "-d", "htmlcov-backend",
                 "--title", "LibreFolio Backend Coverage", "--ignore-errors"],
                cwd=os.getcwd(), capture_output=True, text=True
            )
            print(f"   {Colors.GREEN}📊 Generated htmlcov-backend/{Colors.NC}")

        if frontend_db.exists():
            shutil.copy2(str(frontend_db), str(main_cov))
            r_fe = subprocess.run(
                [*pipenv_prefix(), "coverage", "html", "-d", "htmlcov-backend-e2e",
                 "--title", "LibreFolio Frontend E2E → Backend Coverage",
                 "--ignore-errors"],
                cwd=os.getcwd(), capture_output=True, text=True
            )
            if r_fe.returncode != 0:
                print_warning(f"coverage html (frontend) failed: {r_fe.stderr.strip()}")
            else:
                print(f"   {Colors.GREEN}📊 Generated htmlcov-backend-e2e/{Colors.NC}")

        combine_srcs = [str(f) for f in (backend_db, frontend_db) if f.exists()]
        if combine_srcs:
            if main_cov.exists():
                main_cov.unlink()
            print(f"{Colors.YELLOW}📊 Merging backend + frontend for combined report...{Colors.NC}")
            r_merge = subprocess.run(
                [*pipenv_prefix(), "coverage", "combine", "--keep"] + combine_srcs,
                cwd=os.getcwd(), capture_output=True, text=True
            )
            if r_merge.returncode != 0:
                # Come sopra: coverage.py parla su stdout quando il combine rifiuta.
                err_lines = [l for l in (r_merge.stdout + "\n" + r_merge.stderr).strip().splitlines()
                             if "Loading .env" not in l and l.strip()]
                if err_lines:
                    print_warning(f"   coverage combine: {' '.join(err_lines)}")

        r = subprocess.run(
            [*pipenv_prefix(), "coverage", "html", "-d", "htmlcov",
             "--title", "LibreFolio Combined Coverage", "--ignore-errors"],
            cwd=os.getcwd(), capture_output=True, text=True
        )
        if r.returncode != 0:
            print_warning(f"coverage html failed: {r.stderr.strip()}")
    elif is_front:
        r = subprocess.run(
            [*pipenv_prefix(), "coverage", "html", "-d", html_dir,
             "--title", "LibreFolio Frontend E2E → Backend Coverage",
             "--ignore-errors"],
            cwd=os.getcwd(), capture_output=True, text=True
        )
        if r.returncode != 0:
            print_warning(f"coverage html failed: {r.stderr.strip()}")
    else:
        if main_cov.exists():
            _archive_db(backend_db, "backend")
            shutil.copy2(str(main_cov), str(backend_db))
            print(f"   {Colors.GREEN}💾 Saved backend coverage → .coverage_data/backend{Colors.NC}")

    subprocess.run(
        [*pipenv_prefix(), "coverage", "report", "--skip-covered", "--ignore-errors"],
        cwd=os.getcwd(), capture_output=False, text=True
    )

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

    return html_dir


def _handle_coverage_command(args) -> int:
    """Handle ./dev.py test coverage show [backend|frontend|combined]."""
    action = getattr(args, 'cov_action', None)
    if not action:
        print_error("Usage: ./dev.py test coverage show [backend|frontend|combined]")
        return 1

    if action == "show":
        target = getattr(args, 'target', 'combined')
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
        subprocess.run(["open", str(index_file)])
        return 0
    else:
        print_error(f"Failed to generate {target} coverage report")
        return 1


def _coverage_combine() -> int:
    """Combine all .coverage.* files and generate combined HTML report."""
    return _coverage_combine_internal(
        html_dir="htmlcov",
        title="LibreFolio Combined Coverage (Backend + Frontend)"
    )


def _coverage_combine_internal(html_dir: str = "htmlcov", title: str = "LibreFolio Coverage") -> int:
    """Internal: combine coverage data and generate HTML report."""
    cwd = Path(os.getcwd())
    backend_cov = cwd / ".coverage.backend"
    frontend_cov = cwd / ".coverage.frontend"

    combine_files = []
    if backend_cov.exists() or frontend_cov.exists():
        if backend_cov.exists():
            combine_files.append(str(backend_cov))
        if frontend_cov.exists():
            combine_files.append(str(frontend_cov))
        print(f"   Using saved snapshots: {', '.join(f.name for f in [backend_cov, frontend_cov] if f.exists())}")
    else:
        combine_files = [str(f) for f in cwd.glob(".coverage.*") if f.name != ".coveragerc"]
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

        result = subprocess.run(
            [*pipenv_prefix(), "coverage", "combine", "--keep"] + combine_files,
            cwd=os.getcwd(), capture_output=True, text=True
        )
        if result.returncode != 0 and "No data to combine" not in result.stderr:
            print_warning(f"coverage combine: {result.stderr.strip()}")

    result = subprocess.run(
        [*pipenv_prefix(), "coverage", "html", "-d", html_dir, "--title", title],
        cwd=os.getcwd(), capture_output=True, text=True
    )
    if result.returncode == 0:
        print_success(f"Coverage report generated: {html_dir}/index.html")
    else:
        print_error(f"Failed to generate report: {result.stderr.strip()}")
        return 1

    subprocess.run(
        [*pipenv_prefix(), "coverage", "report", "--skip-covered"],
        cwd=os.getcwd(), capture_output=False, text=True
    )
    return 0

