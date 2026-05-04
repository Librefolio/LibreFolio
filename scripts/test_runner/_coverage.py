"""
Coverage finalization, reporting, and management commands.
"""

import os
import shutil
import subprocess
from pathlib import Path

from scripts.cli_base import pipenv_prefix

from ._common import (
    PROJECT_ROOT, Colors,
    print_header, print_section, print_info, print_success, print_error, print_warning,
)


def _finalize_coverage(is_front: bool, is_all: bool) -> str:
    """Finalize coverage data after test runs."""
    cwd = Path(os.getcwd())
    main_cov = cwd / ".coverage"
    data_dir = cwd / ".coverage_data"
    data_dir.mkdir(exist_ok=True)
    backend_db = data_dir / "backend"
    frontend_db = data_dir / "frontend"
    html_dir = "htmlcov-frontend" if is_front else "htmlcov-backend"

    def _archive_db(db_path: Path, label: str):
        if db_path.exists():
            archive_dir = data_dir / "archive"
            archive_dir.mkdir(exist_ok=True)
            from datetime import datetime as _dt
            ts = _dt.now().strftime("%Y%m%d_%H%M")
            shutil.copy2(str(db_path), str(archive_dir / f"{label}_{ts}"))
            print(f"   {Colors.GREEN}📦 Archived {label} → archive/{label}_{ts}{Colors.NC}")

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
                err_lines = [l for l in r_combine.stderr.strip().splitlines()
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
                [*pipenv_prefix(), "coverage", "html", "-d", "htmlcov-frontend",
                 "--title", "LibreFolio Frontend E2E → Backend Coverage",
                 "--ignore-errors"],
                cwd=os.getcwd(), capture_output=True, text=True
            )
            if r_fe.returncode != 0:
                print_warning(f"coverage html (frontend) failed: {r_fe.stderr.strip()}")
            else:
                print(f"   {Colors.GREEN}📊 Generated htmlcov-frontend/{Colors.NC}")

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
                err_lines = [l for l in r_merge.stderr.strip().splitlines()
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
        print(f"└─▶ $ ./dev.py test coverage show combined")
    else:
        print(f"└─▶ $ ./dev.py test coverage show {'frontend' if is_front else 'backend'}")
        print(f"└─▶ $ ./dev.py test coverage show combined   # merge backend + frontend")
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
        "frontend": "htmlcov-frontend",
        "combined": "htmlcov",
    }
    title_map = {
        "backend": "LibreFolio Backend Test Coverage",
        "frontend": "LibreFolio Frontend E2E → Backend Coverage",
        "combined": "LibreFolio Combined Coverage (Backend + Frontend)",
    }

    html_dir = PROJECT_ROOT / dir_map[target]
    index_file = html_dir / "index.html"

    if target == "combined":
        print(f"{Colors.YELLOW}📊 Combining all coverage data...{Colors.NC}")
        _coverage_combine_internal(html_dir=str(html_dir), title=title_map[target])
    elif not index_file.exists():
        print_error(f"No {target} coverage report found at {html_dir}/")
        print_info(f"Run tests with --coverage first:")
        if target == "backend":
            print_info(f"  ./dev.py test --coverage api all")
        else:
            print_info(f"  ./dev.py test --coverage front-fx all")
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

