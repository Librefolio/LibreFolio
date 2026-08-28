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

from . import _common
from ._common import (
    Colors,
    _run_test_suite,
    print_warning,
)
from ._registry import TEST_REGISTRY

_BACKEND_CATEGORIES = ("external", "db", "services", "utils", "schemas", "api", "e2e")
_FRONTEND_CATEGORIES = ("front-utility", "front-broker", "front-user", "front-fx", "front-asset", "front-transaction", "front-portfolio", "front-ai-export")

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


def _archive_incompatible_coverage_dbs() -> None:
    """Archivia i DB di coverage salvati la cui modalità di misura non è più quella corrente.

    ``coverage combine`` **rifiuta** di fondere dati ad archi (branch) con dati a
    sole righe. Il guaio non è il rifiuto: è che ``_finalize_coverage`` tratta il
    fallimento del combine come un semplice warning e poi genera comunque l'HTML
    da qualunque metà sia sopravvissuta. Cambiare ``branch`` in ``.coveragerc``
    con i vecchi DB sul disco produrrebbe quindi un report **sbagliato in
    silenzio** — il modo più caro di sbagliarsi.

    Qui il disallineamento si scopre prima che i test scrivano, diventa una riga
    a schermo, e il dato vecchio resta recuperabile in ``.coverage_data/00_archive``.
    """
    data_dir = Path(os.getcwd()) / ".coverage_data"
    if not data_dir.exists():
        return

    try:
        from coverage import Coverage, CoverageData
    except ImportError:
        return

    from ._archive import archive_path

    wants_arcs = bool(Coverage().config.branch)
    mode = "branch" if wants_arcs else "statement"

    # Il `.coverage` di root va incluso: non è uno scarto, è il **bersaglio** del
    # `coverage combine --append` della passata parallela, e sopravvive alle run
    # backend-only. Lasciarlo fuori significava veder fallire il combine e
    # buttare via la coverage di tutta la passata senza capire perché.
    candidates = [(data_dir / "backend", "backend"), (data_dir / "frontend", "frontend"), (Path(os.getcwd()) / ".coverage", "root")]

    for db_path, label in candidates:
        if not db_path.exists():
            continue
        try:
            data = CoverageData(basename=str(db_path))
            data.read()
            compatible = data.has_arcs() == wants_arcs
            reason = f"raccolto in modalità {'branch' if data.has_arcs() else 'statement'}"
        except Exception as exc:
            # Illeggibile è comunque inutilizzabile: si archivia dicendo perché,
            # invece di lasciarlo far fallire il combine più avanti.
            compatible, reason = False, f"illeggibile ({exc.__class__.__name__})"
        if compatible:
            continue
        print_warning(f"   Coverage {label}: {reason}, incompatibile con la modalità {mode} attuale")
        archive_path(db_path, target_dir=data_dir, label=f"{label}_mode_change", move=True)


def _clean_coverage_dirs(clean_backend: bool, clean_frontend: bool) -> None:
    """Remove coverage data directories selectively, archiving DBs first."""
    cwd = Path(os.getcwd())
    data_dir = cwd / ".coverage_data"

    def _archive_and_remove(db_path: Path, label: str):
        if db_path.exists():
            from ._archive import archive_path

            archive_path(db_path, target_dir=data_dir, label=f"{label}_clean", move=True)

    if clean_backend:
        be_dir = cwd / "htmlcov-backend"
        if be_dir.exists():
            shutil.rmtree(be_dir)
            print(f"{Colors.GREEN}🗑️  Removed htmlcov-backend/{Colors.NC}")
        _archive_and_remove(data_dir / "backend", "backend")

    if clean_frontend:
        fe_dir = cwd / "htmlcov-backend-e2e"
        if fe_dir.exists():
            shutil.rmtree(fe_dir)
            print(f"{Colors.GREEN}🗑️  Removed htmlcov-backend-e2e/{Colors.NC}")
        _archive_and_remove(data_dir / "frontend", "frontend")

    if clean_backend or clean_frontend:
        result = subprocess.run([*pipenv_prefix(), "coverage", "erase"], cwd=os.getcwd(), capture_output=True, text=True)

    # Dopo le pulizie esplicite: quello che è sopravvissuto deve essere della
    # stessa modalità di misura di adesso, altrimenti il merge finale mente.
    _archive_incompatible_coverage_dbs()


def run_all_tests(verbose: bool = False, providers: list = None, exclude_providers: list = None, resume: bool = False) -> bool:
    """Run all tests (backend + frontend) in optimal order."""
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
                all_tests.append((name, lambda f=func, v=verbose: f(verbose=v, coverage=_common._COVERAGE_MODE)))
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
                all_tests.append((name, lambda f=func, v=verbose: f(verbose=v, coverage=_common._COVERAGE_MODE)))
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
    """Run all frontend categories, including portfolio and AI Export cutover tests."""
    tests = []
    for category in _FRONTEND_CATEGORIES:
        if category not in TEST_REGISTRY:
            continue
        all_info = TEST_REGISTRY[category].get("all", {})
        func = all_info.get("func")
        name = all_info.get("name", f"{category.title()} Tests")
        if func:
            if "coverage" in inspect.signature(func).parameters:
                tests.append((name, lambda f=func, v=verbose: f(verbose=v, coverage=_common._COVERAGE_MODE)))
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
