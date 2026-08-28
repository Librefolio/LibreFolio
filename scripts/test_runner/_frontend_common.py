"""
Frontend common: build checks, DB population, test user creation, Playwright runner, test listing.
"""

import inspect
import os
import re
import subprocess
from pathlib import Path

from scripts.cli_base import auto_build_frontend, pipenv_prefix

from . import _common
from ._archive import log_file_for
from ._backend_db import db_populate
from ._common import (
    PROJECT_ROOT,
    Colors,
    print_error,
    print_info,
    print_success,
    print_warning,
)

# Setup already performed in the current scope. A scope is one run of one
# category: `reset_setup_scope()` opens it, and the first `_ensure_*` call
# inside it does the real work while the rest find it warm.
#
# This is what lets an `all` action be derived from the registry instead of
# hand-written. Without it, calling the registered actions would repopulate the
# database and recreate the eight users once per action; with it, the cost is
# paid exactly once per category — which is what the hand-written lists did.
_SETUP_DONE: set[str] = set()


def reset_setup_scope() -> None:
    """Open a new setup scope, so the next ``_ensure_*`` call works for real."""
    _SETUP_DONE.clear()
    os.environ.pop("LF_SETUP_DONE", None)


def _ensure_frontend_build() -> bool:
    """Ensure frontend is built and up to date.

    Reuses dev.py's canonical build (``cmd_fe_build``) as the build function, so a
    rebuild also syncs the API types first (export openapi.json → generate the
    Zodios client ``generated.ts``). Both files are gitignored, so on a fresh
    checkout (e.g. CI) a plain ``npm run build`` fails with
    ``Could not resolve "./generated" from src/lib/api/index.ts``. Routing the
    build through ``cmd_fe_build`` — the same path ``dev.py server --force`` uses —
    regenerates them first. ``auto_build_frontend`` still only rebuilds when the
    sources actually changed.
    """
    from types import SimpleNamespace

    from dev import cmd_fe_build

    if "build" in _SETUP_DONE:
        return True

    result = auto_build_frontend(
        debug=False,
        build_func=lambda debug=False: cmd_fe_build(SimpleNamespace(debug=debug)),
    )
    if result is None or result == 0:
        _SETUP_DONE.add("build")
        return True
    else:
        print_error("Frontend build failed!")
        return False


def _ensure_db_populated() -> bool:
    """Ensure test database has been populated with mock data.

    ``with_reports=True`` matters: Playwright's ``globalSetup`` has always used
    it, and the broker import-history specs need those sample BRIM files to have
    anything to show. Without it here, the Python populate would be a *subset* of
    the JS one, and telling `globalSetup` to stand down (``LF_SETUP_DONE``) would
    quietly remove data those specs depend on.
    """
    if "db" in _SETUP_DONE:
        return True

    print_info("Populating test DB with mock data...")
    if not db_populate(verbose=False, force=True, with_reports=True):
        return False

    _SETUP_DONE.add("db")
    # Repopulating drops the E2E users, so they must be recreated after it.
    _SETUP_DONE.discard("users")
    os.environ.pop("LF_SETUP_DONE", None)
    return True


def _ensure_test_users() -> bool:
    """Ensure E2E test users exist in test database."""
    if "users" in _SETUP_DONE:
        return True

    print_info("Ensuring E2E test users exist...")

    users = [
        ("e2e_test_user", "e2e@test.example.com", "E2eTestPass123!"),
        ("e2e_test_admin", "e2eadmin@test.example.com", "E2eAdminPass123!"),
        ("e2e_test_user2", "e2e2@test.example.com", "E2eTestPass456!"),
        ("e2e_user_alice", "alice@test.example.com", "AlicePass123!"),
        ("e2e_user_bob", "bob@test.example.com", "BobPass123!"),
        ("e2e_user_carol", "carol@test.example.com", "CarolPass123!"),
        ("e2e_user_dave", "dave@test.example.com", "DavePass123!"),
        ("e2e_user_eve", "eve@test.example.com", "EvePass123!"),
    ]

    for username, email, password in users:
        result = subprocess.run(
            ["python", "scripts/user_cli.py", "--test-db", "create-superuser",
             username, email, password],
            capture_output=True,
            text=True
        )
        if result.returncode != 0 and "already exists" not in result.stderr.lower():
            print_error(f"Failed to create user {username}: {result.stderr}")
            return False

    # Promote admin
    subprocess.run(
        ["python", "scripts/user_cli.py", "--test-db", "promote", "e2e_test_admin"],
        capture_output=True
    )

    _SETUP_DONE.add("users")
    # Both halves of what globalSetup would redo are now in place, so it can skip
    # them. It still initialises the global settings over the API — nothing on the
    # Python side does that, and `populate --force` wipes them.
    if "db" in _SETUP_DONE:
        os.environ["LF_SETUP_DONE"] = "1"
    print_success("Test users ready")
    return True


def _run_playwright(
    spec_file: str | list[str] | None = None,
    ui: bool = False,
    headed: bool = False,
    debug: bool = False,
    project: str = "desktop",
    test_names: list = None,
    coverage: bool = False,
) -> bool:
    """
    Run Playwright tests with given options.

    When ``--log-dir`` is active the whole run is teed to its own file, exactly
    like ``run_command`` does for the Python side. Playwright is invoked through
    ``subprocess.run`` rather than ``run_command``, so without this the E2E
    output — the part a CI artifact is actually needed for — was the only thing
    the log dir did not capture.
    """
    log_dir = _common.get_log_dir()
    if log_dir is None:
        return _run_playwright_body(spec_file, ui, headed, debug, project, test_names, coverage)

    spec_files = spec_file if isinstance(spec_file, list) else ([spec_file] if spec_file else [])
    unit = _playwright_log_unit(spec_files, test_names)
    try:
        log_path = log_file_for(log_dir, _common.get_log_category(), unit)
    except Exception:
        return _run_playwright_body(spec_file, ui, headed, debug, project, test_names, coverage)

    with _common.tee_output(log_path):
        return _run_playwright_body(spec_file, ui, headed, debug, project, test_names, coverage)


def _playwright_log_unit(spec_files: list[str], test_names: list | None) -> str:
    """
    Name the log after what was run: the spec file's stem, or the count when a
    single invocation carries several specs. Falls back to the grep pattern so a
    filtered run is still identifiable.
    """
    stems = [Path(sf).name.replace(".spec.ts", "") for sf in spec_files]
    if len(stems) == 1:
        base = stems[0]
    elif stems:
        base = f"e2e-{len(stems)}-specs"
    elif test_names:
        base = "-".join(test_names)[:60]
    else:
        base = "e2e"
    return base


def _run_playwright_body(
    spec_file: str | list[str] | None = None,
    ui: bool = False,
    headed: bool = False,
    debug: bool = False,
    project: str = "desktop",
    test_names: list = None,
    coverage: bool = False,
) -> bool:
    cmd = ["npm", "run"]

    if ui:
        cmd.append("test:e2e:ui")
    elif debug:
        cmd.append("test:e2e:debug")
    elif headed:
        cmd.append("test:e2e:headed")
    else:
        cmd.append("test:e2e")

    extra_args = []
    # Accept a single spec file string or a list of spec files
    spec_files = spec_file if isinstance(spec_file, list) else ([spec_file] if spec_file else [])
    for sf in spec_files:
        extra_args.append(sf)
    if project and not ui:
        extra_args.extend(["--project", project])

    if test_names:
        pattern = "|".join(test_names)
        extra_args.extend(["--grep", pattern])

    if extra_args:
        cmd.extend(["--"] + extra_args)

    spec_label = ', '.join(spec_files) if spec_files else 'all tests'
    print(f"\n{Colors.BLUE}Running: Playwright {spec_label}{Colors.NC}")
    if test_names:
        print(f"{Colors.YELLOW}Filter: {' | '.join(test_names)}{Colors.NC}")

    # `coverage` stays a plain on/off switch for the ~77 callers; *which*
    # languages to collect is decided centrally in _cli.py.
    cov_py = bool(coverage) and _common._COVERAGE_PY
    cov_js = bool(coverage) and _common._COVERAGE_JS
    if cov_py:
        print(f"{Colors.YELLOW}📊 Backend coverage tracking enabled (COVERAGE_BACKEND=1){Colors.NC}")
    if cov_js:
        print(f"{Colors.YELLOW}📊 JS/Svelte coverage tracking enabled (COVERAGE_JS=1){Colors.NC}")
    print(f"Command:\n└─▶ $ cd frontend && {' '.join(cmd)}")

    try:
        env = None
        # `--workers` decided by the runner, not read from the shell.
        if getattr(_common, "_E2E_WORKERS", 1) > 1 and "E2E_WORKERS" not in os.environ:
            env = _common.apply_e2e_workers(os.environ.copy())
        if cov_py or cov_js:
            if env is None:
                env = os.environ.copy()
            if cov_py:
                env['COVERAGE_BACKEND'] = '1'
            if cov_js:
                env['COVERAGE_JS'] = '1'
            else:
                env.pop('COVERAGE_JS', None)

        result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", text=True, env=env)

        if result.returncode == 0:
            print_success("Playwright tests - PASSED")
            return True
        else:
            print_error(f"Playwright tests - FAILED (exit code: {result.returncode})")
            return False

    except Exception as e:
        print_error(f"Playwright error: {e}")
        return False


def _list_front_tests(category: str, action: str = None) -> bool:
    """
    List available test names from spec files for a front-* category.
    Parses .spec.ts files looking for test.describe() and test() calls.
    """
    from ._registry import TEST_REGISTRY

    spec_map = {}
    if category in TEST_REGISTRY:
        for act, info in TEST_REGISTRY[category].items():
            if act == "_meta" or act == "all":
                continue
            tests_file = info.get("tests", "")
            if tests_file.endswith(".spec.ts"):
                spec_map[act] = tests_file

    if action and action != "all":
        if action in spec_map:
            spec_map = {action: spec_map[action]}
        else:
            print_error(f"No spec file found for action '{action}'")
            return True

    if not spec_map:
        print_warning(f"No spec files found for category '{category}'")
        return True

    e2e_dir = PROJECT_ROOT / "frontend" / "e2e"
    print(f"\n{Colors.CYAN}🧪 Available Tests ({category}{' / ' + action if action and action != 'all' else ''}):{Colors.NC}")
    print(f"  Use {Colors.YELLOW}./dev.py test {category} <action> \"<test name>\"{Colors.NC} to run a specific test\n")

    for act, spec_file in spec_map.items():
        full_path = e2e_dir / spec_file
        if not full_path.exists():
            print(f"  {Colors.RED}✘ {spec_file} (file not found){Colors.NC}")
            continue

        print(f"  {Colors.GREEN}📄 {spec_file}{Colors.NC}")
        try:
            content = full_path.read_text(encoding="utf-8")
        except Exception:
            print(f"    {Colors.RED}(could not read file){Colors.NC}")
            continue

        # Parse test.describe() and test() calls
        describe_re = re.compile(r"test\.describe\(\s*['\"](.+?)['\"]", re.MULTILINE)
        test_re = re.compile(r"^\s+test\(\s*['\"](.+?)['\"]", re.MULTILINE)

        current_describe = None
        test_count = 0
        for line in content.splitlines():
            desc_match = describe_re.search(line)
            if desc_match:
                current_describe = desc_match.group(1)
                print(f"    {Colors.YELLOW}📁 {current_describe}{Colors.NC}")
                continue

            test_match = test_re.search(line)
            if test_match:
                test_name = test_match.group(1)
                prefix = "      " if current_describe else "    "
                print(f"{prefix}{Colors.BLUE}• {test_name}{Colors.NC}")
                test_count += 1

        if test_count == 0:
            print(f"    {Colors.YELLOW}(no tests found){Colors.NC}")
        print()

    return True


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


def _list_pytest_tests(category: str, action: str = None) -> bool:
    """List available pytest test names for a backend category."""
    from ._registry import TEST_REGISTRY

    test_path = None

    if action and action != "all" and category in TEST_REGISTRY:
        info = TEST_REGISTRY[category].get(action, {})
        func = info.get("func")
        if func:
            try:
                source = inspect.getsource(func)
                match = re.search(r'_build_pytest_cmd\(["\']([^"\']+)["\']', source)
                if match:
                    test_path = match.group(1)
                else:
                    match = re.search(r'pytest.*?["\']([^"\']*test_scripts[^"\']+\.py)["\']', source)
                    if match:
                        test_path = match.group(1)
            except (TypeError, OSError):
                pass

    if not test_path:
        test_path = BACKEND_TEST_PATHS.get(category)

    if not test_path:
        print_error(f"No test path found for category '{category}' action '{action}'")
        return True

    full_path = PROJECT_ROOT / test_path
    if not full_path.exists():
        print_error(f"Test path not found: {test_path}")
        return True

    print(f"\n{Colors.CYAN}🧪 Available Tests ({category}{' / ' + action if action and action != 'all' else ''}):{Colors.NC}")
    print(f"  Use {Colors.YELLOW}./dev.py test {category} <action> \"<test name>\"{Colors.NC} to run a specific test\n")

    try:
        cmd = [*pipenv_prefix(), "python", "-m", "pytest", str(test_path), "--collect-only", "-q"]
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout.strip()
        if not output:
            print(f"  {Colors.YELLOW}(no tests collected){Colors.NC}")
            if result.stderr:
                err_lines = [l for l in result.stderr.strip().splitlines() if 'ERROR' in l or 'error' in l.lower()]
                for l in err_lines[:5]:
                    print(f"  {Colors.RED}{l}{Colors.NC}")
            print()
            return True

        current_file = ""
        current_class = ""
        test_count = 0

        for line in output.splitlines():
            if '::' not in line or line.startswith('='):
                continue

            parts = line.strip().split('::')
            file_path = parts[0] if len(parts) >= 1 else ""

            if file_path != current_file:
                current_file = file_path
                current_class = ""
                short_name = Path(file_path).name if file_path else file_path
                print(f"  {Colors.GREEN}📄 {short_name}{Colors.NC}")

            if len(parts) >= 3:
                class_name = parts[1]
                test_name = parts[2]
                if class_name != current_class:
                    current_class = class_name
                    print(f"    {Colors.YELLOW}📁 {class_name}{Colors.NC}")
                print(f"      {Colors.BLUE}• {test_name}{Colors.NC}")
                test_count += 1
            elif len(parts) == 2:
                test_name = parts[1]
                current_class = ""
                print(f"    {Colors.BLUE}• {test_name}{Colors.NC}")
                test_count += 1

        if test_count == 0:
            print(f"    {Colors.YELLOW}(no tests found){Colors.NC}")
        print()

    except subprocess.TimeoutExpired:
        print_warning("Test collection timed out (30s)")
    except Exception as e:
        print_error(f"Error listing tests: {e}")

    print()
    return True

