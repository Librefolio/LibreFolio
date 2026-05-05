"""
Frontend common: build checks, DB population, test user creation, Playwright runner, test listing.
"""

import inspect
import re
import subprocess
from pathlib import Path

from scripts.cli_base import auto_build_frontend, pipenv_prefix

from ._common import (
    PROJECT_ROOT, Colors,
    print_section, print_info, print_success, print_error, print_warning,
)
from ._backend_db import db_populate


def _ensure_frontend_build() -> bool:
    """Ensure frontend is built and up to date."""
    result = auto_build_frontend(debug=False)
    if result is None or result == 0:
        return True
    else:
        print_error("Frontend build failed!")
        return False


def _ensure_db_populated() -> bool:
    """Ensure test database has been populated with mock data."""
    print_info("Populating test DB with mock data...")
    return db_populate(verbose=False, force=True)


def _ensure_test_users() -> bool:
    """Ensure E2E test users exist in test database."""
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
    """Run Playwright tests with given options."""
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
    if coverage:
        print(f"{Colors.YELLOW}📊 Backend coverage tracking enabled (COVERAGE_BACKEND=1){Colors.NC}")
    print(f"Command:\n└─▶ $ cd frontend && {' '.join(cmd)}")

    try:
        env = None
        if coverage:
            import os
            env = os.environ.copy()
            env['COVERAGE_BACKEND'] = '1'

        result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", text=True, env=env)

        if result.returncode == 0:
            print_success(f"Playwright tests - PASSED")
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

