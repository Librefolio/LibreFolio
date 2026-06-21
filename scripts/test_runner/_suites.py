"""
Test suites: run_all_tests, run_all_backend_tests, run_all_frontend_tests.
Coverage clean helpers. Category constants.
"""

import inspect
import os
import shutil
import subprocess
from pathlib import Path

from scripts.cli_base import pipenv_prefix

from ._common import (
    _COVERAGE_MODE,
    Colors,
    _run_test_suite,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
)
from ._registry import TEST_REGISTRY

_BACKEND_CATEGORIES = ("external", "db", "services", "utils", "schemas", "api", "e2e")
_FRONTEND_CATEGORIES = ("front-utility", "front-broker", "front-user", "front-fx", "front-asset", "front-transaction", "front-portfolio")

# Mapping of backend test categories to their test directories/files
BACKEND_TEST_PATHS = {
    "external": "backend/test_scripts/test_external/",
    "db": "backend/test_scripts/test_db/",
    "services": "backend/test_scripts/test_services/",
    "utils": "backend/test_scripts/test_utilities/",
    "schemas": "backend/test_scripts/test_schemas/",
    "api": "backend/test_scripts/test_api/",
    "e2e": "backend/test_scripts/test_e2e/",
}


def _clean_coverage_dirs(clean_backend: bool, clean_frontend: bool) -> None:
    """Remove coverage data directories selectively, archiving DBs first."""
    cwd = Path(os.getcwd())
    data_dir = cwd / ".coverage_data"

    def _archive_and_remove(db_path: Path, label: str):
        if db_path.exists():
            archive_dir = data_dir / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            from datetime import datetime as _dt

            ts = _dt.now().strftime("%Y%m%d_%H%M")
            archive_name = f"{label}_{ts}_clean"
            shutil.move(str(db_path), str(archive_dir / archive_name))
            print(f"{Colors.GREEN}📦 Archived .coverage_data/{label} → archive/{archive_name}{Colors.NC}")

    if clean_backend:
        be_dir = cwd / "htmlcov-backend"
        if be_dir.exists():
            shutil.rmtree(be_dir)
            print(f"{Colors.GREEN}🗑️  Removed htmlcov-backend/{Colors.NC}")
        _archive_and_remove(data_dir / "backend", "backend")

    if clean_frontend:
        fe_dir = cwd / "htmlcov-frontend"
        if fe_dir.exists():
            shutil.rmtree(fe_dir)
            print(f"{Colors.GREEN}🗑️  Removed htmlcov-frontend/{Colors.NC}")
        _archive_and_remove(data_dir / "frontend", "frontend")

    if clean_backend or clean_frontend:
        result = subprocess.run([*pipenv_prefix(), "coverage", "erase"], cwd=os.getcwd(), capture_output=True, text=True)


def run_all_tests(verbose: bool = False, providers: list = None, exclude_providers: list = None, resume: bool = False) -> bool:
    """Run all tests (backend + frontend) in optimal order."""
    from ._backend_external import external_all

    all_tests = []

    # Backend categories
    for category in _BACKEND_CATEGORIES:
        if category not in TEST_REGISTRY:
            continue
        all_info = TEST_REGISTRY[category].get("all", {})
        func = all_info.get("func")
        name = all_info.get("name", f"{category.title()} Tests")
        if func:
            func_params = inspect.signature(func).parameters
            if "providers" in func_params:
                all_tests.append((name, lambda f=func, v=verbose, p=providers, ep=exclude_providers: f(verbose=v, providers=p, exclude_providers=ep)))
            elif "coverage" in func_params:
                all_tests.append((name, lambda f=func, v=verbose, c=_COVERAGE_MODE: f(verbose=v, coverage=c)))
            else:
                all_tests.append((name, lambda f=func, v=verbose: f(verbose=v)))

    # Frontend categories
    for category in _FRONTEND_CATEGORIES:
        if category not in TEST_REGISTRY:
            continue
        all_info = TEST_REGISTRY[category].get("all", {})
        func = all_info.get("func")
        name = all_info.get("name", f"{category.title()} Tests")
        if func:
            if "coverage" in inspect.signature(func).parameters:
                all_tests.append((name, lambda f=func, v=verbose, c=_COVERAGE_MODE: f(verbose=v, coverage=c)))
            else:
                all_tests.append((name, lambda f=func, v=verbose: f(verbose=v)))

    return _run_test_suite(
        suite_name="Complete Test Suite",
        tests=all_tests,
        verbose=verbose,
        resume=resume,
        info_msgs=[
            "Running all test categories (backend + frontend)",
            "This may take several minutes...\n",
        ],
        success_msg="\n🎉 ALL TESTS PASSED! 🎉",
    )


def run_all_backend_tests(verbose: bool = False, providers: list = None, exclude_providers: list = None, resume: bool = False) -> bool:
    """Run all backend tests."""
    tests = []
    for category in _BACKEND_CATEGORIES:
        if category not in TEST_REGISTRY:
            continue
        all_info = TEST_REGISTRY[category].get("all", {})
        func = all_info.get("func")
        name = all_info.get("name", f"{category.title()} Tests")
        if func:
            func_params = inspect.signature(func).parameters
            if "providers" in func_params:
                tests.append((name, lambda f=func, v=verbose, p=providers, ep=exclude_providers: f(verbose=v, providers=p, exclude_providers=ep)))
            else:
                tests.append((name, lambda f=func, v=verbose: f(verbose=v)))

    return _run_test_suite(
        suite_name="Backend Test Suite",
        tests=tests,
        verbose=verbose,
        resume=resume,
        info_msgs=[
            "Running all backend test categories",
            "This may take a few minutes...\n",
        ],
        success_msg="\n🎉 ALL BACKEND TESTS PASSED! 🎉",
    )


def run_all_frontend_tests(verbose: bool = False, resume: bool = False) -> bool:
    """Run all frontend tests (front-utility, front-broker, front-user, front-fx, front-asset, front-transaction)."""
    tests = []
    for category in _FRONTEND_CATEGORIES:
        if category not in TEST_REGISTRY:
            continue
        all_info = TEST_REGISTRY[category].get("all", {})
        func = all_info.get("func")
        name = all_info.get("name", f"{category.title()} Tests")
        if func:
            if "coverage" in inspect.signature(func).parameters:
                tests.append((name, lambda f=func, v=verbose, c=_COVERAGE_MODE: f(verbose=v, coverage=c)))
            else:
                tests.append((name, lambda f=func, v=verbose: f(verbose=v)))

    return _run_test_suite(
        suite_name="Frontend Test Suite",
        tests=tests,
        verbose=verbose,
        resume=resume,
        info_msgs=[
            "Running all frontend test categories",
            "This may take a few minutes...\n",
        ],
        success_msg="\n🎉 ALL FRONTEND TESTS PASSED! 🎉",
    )
