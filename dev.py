#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""
LibreFolio Development CLI

Unified command-line interface for development tasks.
Supports autocompletion via argcomplete.

Usage:
    ./dev.py <command> [options]
    python dev.py <command> [options]

Autocompletion setup:
    # Add to ~/.bashrc or ~/.zshrc:
    eval "$(register-python-argcomplete dev.py)"
"""

import os
import sys
import re
import math
import shutil
import signal
import secrets
import argparse
import platform
import subprocess
import time
from pathlib import Path

try:
    import argcomplete
    HAS_ARGCOMPLETE = True
except ImportError:
    HAS_ARGCOMPLETE = False

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# Change to project root for consistent paths
os.chdir(PROJECT_ROOT)

from scripts.cli_base import (
    Colors,
    get_server_host,
    get_server_port,
    get_test_server_port,
    get_database_path,
    get_test_database_path,
    run_pipenv,
    run_command_live,
    print_header,
    print_success,
    print_error,
    print_warning,
    check_server_running,
    pipenv_prefix,
)

from scripts.cli_tree_parser import TreeParser, format_help


# =============================================================================
# Backend Commands: Server
# =============================================================================

def check_port_in_use(port: int) -> list:
    """Check if port is in use and return list of (PID, process_name) tuples."""

    processes = []
    try:
        if platform.system() == "Darwin":  # macOS
            # Get PIDs first
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-t"],
                capture_output=True, text=True
            )
            if result.stdout.strip():
                pids = [int(p) for p in result.stdout.strip().split('\n') if p]
                # Get process name for each PID
                for pid in pids:
                    try:
                        ps_result = subprocess.run(
                            ["ps", "-p", str(pid), "-o", "comm="],
                            capture_output=True, text=True
                        )
                        proc_name = ps_result.stdout.strip() or "unknown"
                        processes.append((pid, proc_name))
                    except Exception:
                        processes.append((pid, "unknown"))
        elif platform.system() == "Linux":
            result = subprocess.run(
                ["fuser", f"{port}/tcp"],
                capture_output=True, text=True, stderr=subprocess.DEVNULL
            )
            if result.stdout.strip():
                pids = [int(p) for p in result.stdout.strip().split() if p]
                for pid in pids:
                    try:
                        ps_result = subprocess.run(
                            ["ps", "-p", str(pid), "-o", "comm="],
                            capture_output=True, text=True
                        )
                        proc_name = ps_result.stdout.strip() or "unknown"
                        processes.append((pid, proc_name))
                    except Exception:
                        processes.append((pid, "unknown"))
    except Exception:
        pass
    return processes


def _print_port_help(port: int, processes: list):
    """Print help message for port-in-use errors."""
    print()
    print(f"{Colors.YELLOW}Processes using port {port}:{Colors.NC}")
    pids = []
    for pid, proc_name in processes:
        pids.append(str(pid))
        print(f"  • PID {pid} ({proc_name})")
    print()
    print(f"{Colors.BLUE}To view details:{Colors.NC}")
    print(f"  lsof -i :{port}")
    print()
    print(f"{Colors.BLUE}To kill these processes:{Colors.NC}")
    print(f"  kill -9 {' '.join(pids)}")
    print()
    print(f"{Colors.YELLOW}Tip:{Colors.NC} This often happens when a previous server didn't shut down cleanly.")
    print(f"{Colors.YELLOW}     Use --force to automatically kill blocking processes.{Colors.NC}")


def cmd_server(args):
    """Start the development server."""
    test_mode = getattr(args, 'test', False)
    rebuild = getattr(args, 'rebuild', False)
    debug_mode = getattr(args, 'debug', False)
    force = getattr(args, 'force', False)
    workers = getattr(args, 'workers', 1)
    host_override = getattr(args, 'host', None)
    port_override = getattr(args, 'port', None)
    coverage_mode = getattr(args, 'coverage', False)

    if test_mode:
        port = get_test_server_port()
        db = get_database_path(test_mode=True)
        debug_mode = True
    else:
        port = get_server_port()
        db = get_database_path(test_mode=False)

    # Apply --host / --port overrides (take priority over env vars)
    host = host_override if host_override else get_server_host()
    if port_override:
        port = port_override

    # Check if port is already in use
    processes_using_port = check_port_in_use(port)
    if processes_using_port:
        if force:
            # --force: kill blocking processes and continue
            pids = [pid for pid, _ in processes_using_port]
            print_warning(f"Port {port} is in use — killing {len(pids)} blocking process(es)...")
            for pid, proc_name in processes_using_port:
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"  ✗ Killed PID {pid} ({proc_name})")
                except ProcessLookupError:
                    pass  # already dead
                except PermissionError:
                    print_error(f"  Cannot kill PID {pid} ({proc_name}) — permission denied")
                    return 1
            # Wait briefly for port to be released
            time.sleep(1)
            # Verify port is now free
            still_in_use = check_port_in_use(port)
            if still_in_use:
                print_error(f"Port {port} still in use after killing processes!")
                _print_port_help(port, still_in_use)
                return 1
            print_success(f"Port {port} is now free")
        else:
            print_error(f"Port {port} is already in use!")
            _print_port_help(port, processes_using_port)
            return 1

    # Handle frontend rebuild
    if rebuild:
        print(Colors.info("📦 Forcing frontend rebuild..."))
        # Create a mock args object with debug flag
        class BuildArgs:
            debug = debug_mode
        result = cmd_fe_build(BuildArgs())
        if result != 0:
            print_error("Frontend build failed. Server not started.")
            return result
    else:
        # Auto-build frontend if needed (respects debug mode)
        result = auto_build_frontend(debug=debug_mode)
        if result is not None and result != 0:
            print_error("Frontend build failed. Server not started.")
            return result

    auto_build_mkdocs()
    update_js_cache()

    mode_str = " (TEST MODE)" if test_mode else " (DEBUG MODE)" if debug_mode else ""
    print(Colors.success(f"Starting LibreFolio API server{mode_str}..."))
    print(Colors.warning(f"Database: {db}"))
    print(Colors.warning(f"Host: {host}"))
    print(Colors.warning(f"Port: {port}"))
    if test_mode:
        print()
        print(f"{Colors.RED}{Colors.BOLD}⚠️  TEST MODE - Using test database! ⚠️{Colors.NC}")
        #         ("e2e_test_user", "e2e@test.example.com", "E2eTestPass123!"),
        #         ("e2e_test_admin", "e2eadmin@test.example.com", "E2eAdminPass123!"),
        print(f"{Colors.RED}{Colors.BOLD}Note: defaults user in test db are:{Colors.NC}")
        print(f'{Colors.RED}{Colors.BOLD} - {{"username": "e2e_test_user",  "password": "E2eTestPass123!"}}')
        print(f'{Colors.RED}{Colors.BOLD} - {{"username": "e2e_test_admin", "password": "E2eAdminPass123!"}}')

        print()
    if debug_mode:
        print(Colors.warning("Log Level: DEBUG"))
    print()
    print(f"{Colors.BLUE}{Colors.BOLD}Available endpoints:{Colors.NC}")
    print(f" ├── 🏠 {Colors.YELLOW}Frontend:  http://localhost:{port}/{Colors.NC}")
    print(f" ├── 💻 {Colors.YELLOW}API Redoc: http://localhost:{port}/api/v1/redoc{Colors.NC}")
    print(f" ├── 🚀 {Colors.YELLOW}API Docs:  http://localhost:{port}/api/v1/docs{Colors.NC}")
    print(f" └── 📚 {Colors.YELLOW}User Doc:  http://localhost:{port}/mkdocs/{Colors.NC}")
    print()

    if (PROJECT_ROOT / "frontend" / "build" / "index.html").exists():
        print_success("Frontend build found - UI available at /")
    else:
        print_warning("No frontend build - run './dev.py front build' to enable UI")
    if workers > 1:
        print(f"{Colors.BLUE}Workers: {workers}{Colors.NC}")
    print()

    env = os.environ.copy()
    if test_mode:
        env["LIBREFOLIO_TEST_MODE"] = "1"
    if debug_mode:
        env["LIBREFOLIO_LOG_LEVEL"] = "DEBUG"
    # Generate a shared JWT secret for all workers.
    # On macOS, Python uses 'spawn' (not fork) for multiprocessing, so each
    # uvicorn worker is a fresh process. Without a shared env var, each worker
    # would generate its own random secret → tokens invalid across workers.
    env.setdefault("JWT_SECRET", secrets.token_urlsafe(64))

    if coverage_mode:
        # Use 'coverage run --parallel-mode -m uvicorn' to track backend code
        # coverage during E2E tests. This replaces the old sitecustomize.py
        # approach, which didn't work because Python's system-level
        # sitecustomize.py shadows the project one.
        #
        # NOTE: --reload is NOT used in coverage mode because 'coverage run'
        # tracks only the direct process; reloader child processes would need
        # sitecustomize.py (which doesn't work). Without --reload, there's a
        # single uvicorn process that 'coverage run' tracks directly.
        coveragerc = str(PROJECT_ROOT / ".coveragerc")
        uvicorn_cmd = [
            *pipenv_prefix(), "coverage", "run",
            "--parallel-mode",
            f"--rcfile={coveragerc}",
            "-m", "uvicorn",
            "backend.app.main:app",
            "--host", host,
            "--port", str(port),
        ]
        print(f"{Colors.YELLOW}📊 Coverage tracking enabled via 'coverage run'{Colors.NC}")
        print(f"{Colors.YELLOW}   Config: {coveragerc}{Colors.NC}")
        print(f"{Colors.YELLOW}   Coverage data will be written to .coverage.<pid> on shutdown{Colors.NC}")
        print()
    else:
        uvicorn_cmd = [
            *pipenv_prefix(), "uvicorn",
            "backend.app.main:app",
            "--host", host,
            "--port", str(port),
        ]
        if workers > 1:
            uvicorn_cmd.extend(["--workers", str(workers)])
        else:
            uvicorn_cmd.append("--reload")

    return run_command_live(uvicorn_cmd, env=env)


# =============================================================================
# Backend Commands: Database
# =============================================================================

def cmd_db_check(args):
    """Verify CHECK constraints in database."""
    db_path = args.path or get_database_path()
    print(Colors.success(f"Checking database constraints: {db_path}"))
    return run_pipenv(["python", "backend/test_scripts/verify_db_check_constraints.py", db_path])


def cmd_db_current(args):
    """Show current database migration."""
    db_path = args.path or get_database_path()
    print(Colors.success(f"Current migration for: {db_path}"))

    env = {"DATABASE_URL": f"sqlite:///{PROJECT_ROOT / db_path}"} if db_path else {}
    return run_command_live(
        [*pipenv_prefix(), "alembic", "-c", "backend/alembic.ini", "current"],
        env=env
    )


def cmd_db_migrate(args):
    """Create a new migration."""
    if not check_server_running("creating migrations", strict=True):
        return 1

    db_path = args.path or get_database_path()
    message = args.message

    print(Colors.success(f"Creating migration: {message}"))

    env = {"DATABASE_URL": f"sqlite:///{PROJECT_ROOT / db_path}"} if db_path else {}
    return run_command_live(
        [*pipenv_prefix(), "alembic", "-c", "backend/alembic.ini", "revision", "--autogenerate", "-m", message],
        env=env
    )


def cmd_db_upgrade(args):
    """Apply pending migrations."""
    if not check_server_running("applying migrations", strict=True):
        return 1

    db_path = args.path or get_database_path()
    print(Colors.success(f"Upgrading database: {db_path}"))

    env = {"DATABASE_URL": f"sqlite:///{PROJECT_ROOT / db_path}"} if db_path else {}
    return run_command_live(
        [*pipenv_prefix(), "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        env=env
    )


def cmd_db_downgrade(args):
    """Rollback one migration."""
    if not check_server_running("rolling back migrations", strict=True):
        return 1

    db_path = args.path or get_database_path()
    print(Colors.success(f"Downgrading database: {db_path}"))

    env = {"DATABASE_URL": f"sqlite:///{PROJECT_ROOT / db_path}"} if db_path else {}
    return run_command_live(
        [*pipenv_prefix(), "alembic", "-c", "backend/alembic.ini", "downgrade", "-1"],
        env=env
    )


def cmd_db_create_clean(args):
    """Delete database and recreate with latest migration."""
    if not check_server_running("recreating database", strict=True):
        return 1

    test_mode = getattr(args, 'test', False)
    if test_mode:
        db_path = Path(get_test_database_path())
    else:
        db_path = Path(get_database_path())

    full_path = PROJECT_ROOT / db_path

    # Delete existing database if exists
    if full_path.exists():
        print(Colors.warning(f"Deleting existing database: {db_path}"))
        full_path.unlink()
        print_success("Database deleted")
    else:
        print(Colors.info(f"Database does not exist: {db_path}"))

    # Create fresh database with migrations
    print(Colors.success(f"Creating fresh database: {db_path}"))

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{full_path}"
    if test_mode:
        env["LIBREFOLIO_TEST_MODE"] = "1"

    result = run_command_live(
        [*pipenv_prefix(), "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        env=env
    )

    if result == 0:
        print_success(f"Database created successfully: {db_path}")
    else:
        print_error("Failed to create database")

    return result


# =============================================================================
# Frontend Commands
# =============================================================================

def cmd_fe_dev(args):
    """Start frontend development server."""
    print(Colors.success("Starting frontend development server..."))
    print(Colors.warning("URL: http://localhost:5173"))
    print()
    return run_command_live(["npm", "run", "dev"], cwd=PROJECT_ROOT / "frontend")


def cmd_fe_build(args):
    """Build frontend for production."""
    # First, sync API types to ensure frontend types are aligned with backend
    print(Colors.success("Syncing API types before build..."))
    sync_result = cmd_api_sync(args)
    if sync_result != 0:
        print_error("API sync failed - aborting build")
        return sync_result

    # Generate favicon from logo before build
    generate_favicon()

    if args.debug:
        print(Colors.success("Building frontend in DEBUG mode (no minify, with sourcemaps)..."))
        result = run_command_live(["npm", "run", "build:debug"], cwd=PROJECT_ROOT / "frontend")
    else:
        print(Colors.success("Building frontend for production..."))
        result = run_command_live(["npm", "run", "build"], cwd=PROJECT_ROOT / "frontend")

    if result == 0:
        print_success("Frontend build complete!")
        print(Colors.warning("Output in: frontend/build/"))
    else:
        print_error("Frontend build failed")
    return result


def cmd_fe_check(args):
    """Run svelte-check for type errors."""
    print(Colors.success("Running svelte-check for type errors..."))
    return run_command_live(["npm", "run", "check"], cwd=PROJECT_ROOT / "frontend")


def cmd_fe_preview(args):
    """Preview production build."""
    print(Colors.success("Previewing production build..."))
    print(Colors.warning("URL: http://localhost:4173"))
    print()
    return run_command_live(["npm", "run", "preview"], cwd=PROJECT_ROOT / "frontend")


# =============================================================================
# API Schema Commands
# =============================================================================

def cmd_api_schema(args):
    """Export OpenAPI schema."""
    print(Colors.success("Exporting OpenAPI schema..."))
    return run_pipenv(["python", "scripts/list_api_endpoints.py", "--openapi-file", "frontend/src/lib/api/openapi.json"])


def cmd_api_client(args):
    """Generate TypeScript client from OpenAPI schema."""
    print(Colors.success("Generating TypeScript client..."))
    return run_command_live(
        ["npm", "run", "generate-api"],
        cwd=PROJECT_ROOT / "frontend"
    )


def cmd_api_sync(args):
    """Export schema and generate client."""
    result = cmd_api_schema(args)
    if result != 0:
        return result
    return cmd_api_client(args)



# =============================================================================
# Info Commands
# =============================================================================

def cmd_info_api(args):
    """List all API endpoints."""
    print(Colors.success("Listing all API endpoints..."))
    return run_pipenv(["python", "scripts/list_api_endpoints.py"])


def cmd_info_version(args):
    """Show application version from git tags."""
    from backend.app.utils.version import get_version_info
    version_info = get_version_info()
    print(f"{Colors.CYAN}LibreFolio {version_info['version']}{Colors.NC}")
    if version_info['is_dirty']:
        print(f"  {Colors.YELLOW}(uncommitted changes){Colors.NC}")
    if version_info['is_release']:
        print(f"  {Colors.GREEN}Release version{Colors.NC}")
    else:
        print(f"  Development version")
    return 0


# =============================================================================
# MkDocs Commands
# =============================================================================

def _check_admonition_empty_lines():
    """Warn if any admonition is missing the empty line after !!!/???.

    Without the empty line, Prettier removes the 4-space body indentation,
    breaking the MkDocs admonition rendering.
    """
    docs_dir = PROJECT_ROOT / "mkdocs_src" / "docs"
    adm_re = re.compile(r'^(?:!!!|[?]{3})\s+\w+')
    bad_files = []

    for md_file in sorted(docs_dir.rglob("*.md")):
        lines = md_file.read_text().splitlines()
        for i, line in enumerate(lines):
            if adm_re.match(line):
                if i + 1 < len(lines) and lines[i + 1].strip() != '':
                    if lines[i + 1].startswith('    '):
                        rel = md_file.relative_to(docs_dir)
                        bad_files.append(f"  {rel}:{i + 1}")
                        break  # one warning per file is enough

    if bad_files:
        print(Colors.warning(
            f"⚠️  {len(bad_files)} file(s) have admonitions without empty line after !!!/??? "
            f"(Prettier will break them):"
        ))
        for f in bad_files[:10]:
            print(f)
        if len(bad_files) > 10:
            print(f"  ... and {len(bad_files) - 10} more")
        print(Colors.info(
            "  Fix: add an empty line between the !!! directive and the indented body."
        ))
        print()

def _check_image_paths_in_built_site():
    """Check that all <img src> paths in built HTML resolve to existing files.

    Scans the built site for relative image paths under static/icons/ and
    verifies each one exists on disk.  Prints a visible warning if broken.
    """
    site_dir = PROJECT_ROOT / "mkdocs_src" / "site"
    if not site_dir.exists():
        return

    img_re = re.compile(r'<img[^>]+src="([^"]+)"')
    broken = []

    for html_file in sorted(site_dir.rglob("*.html")):
        html_dir = html_file.parent
        content = html_file.read_text(errors="ignore")
        for match in img_re.finditer(content):
            src = match.group(1)
            # Only check relative paths to static/icons
            if src.startswith(("http://", "https://", "data:", "/")) or "static/icons" not in src:
                continue
            resolved = (html_dir / src).resolve()
            if not resolved.exists():
                rel_html = html_file.relative_to(site_dir)
                broken.append((str(rel_html), src))

    if broken:
        print()
        print(Colors.warning(
            f"⚠️  {len(broken)} broken icon path(s) found in built site:"
        ))
        for html_path, img_src in broken[:20]:
            print(f"  ❌ {html_path}")
            print(f"     → {img_src}")
        if len(broken) > 20:
            print(f"  ... and {len(broken) - 20} more")
        print(Colors.info(
            "  Fix: use Markdown image syntax ![](path) instead of raw <img> for path auto-adjustment."
        ))
        print()
    else:
        print(Colors.success("✅ All static icon paths in built site verified"))


def cmd_mkdocs_build(args):
    """Build MkDocs documentation."""
    print(Colors.success("Building MkDocs site..."))
    _check_admonition_empty_lines()
    copy_docs_assets()
    result = run_pipenv(["mkdocs", "build", "-f", "mkdocs_src/mkdocs.yml"])
    if result == 0:
        _check_image_paths_in_built_site()
    return result


def cmd_mkdocs_serve(args):
    """Serve MkDocs documentation locally."""
    print(Colors.success("Serving MkDocs site (http://127.0.0.1:8002)"))
    copy_docs_assets()
    return run_pipenv(["mkdocs", "serve", "-f", "mkdocs_src/mkdocs.yml", "-a", "127.0.0.1:8002"])


def cmd_mkdocs_clean(args):
    """Remove built site directory."""
    print(Colors.warning("Removing site directory..."))
    site_dir = PROJECT_ROOT / "mkdocs_src" / "site"
    if site_dir.exists():
        shutil.rmtree(site_dir)
    print_success("Site directory removed")
    return 0


def cmd_mkdocs_deploy(args):
    """Deploy MkDocs to GitHub Pages."""
    print(Colors.success("Deploying MkDocs site to GitHub Pages..."))
    copy_docs_assets()
    return run_pipenv(["mkdocs", "gh-deploy", "-f", "mkdocs_src/mkdocs.yml"])


def cmd_mkdocs_gallery(args):
    """Generate gallery screenshots for documentation using Playwright."""

    list_tests = getattr(args, 'list_tests', False)
    filter_text = getattr(args, 'filter', None)
    desktop_only = getattr(args, 'desktop_only', False)
    mobile_only = getattr(args, 'mobile_only', False)
    no_populate = getattr(args, 'no_populate', False)
    test_port = getattr(args, 'test_port', None)

    # --list: show available test names and exit
    if list_tests:
        gallery_spec = PROJECT_ROOT / "frontend" / "e2e" / "gallery.spec.ts"
        if not gallery_spec.exists():
            print_error("gallery.spec.ts not found")
            return 1
        content = gallery_spec.read_text()
        current_describe = ""
        print(f"\n{Colors.CYAN}📸 Available Gallery Tests:{Colors.NC}")
        print(f"  Use {Colors.YELLOW}./dev.py mkdocs gallery -f \"<text>\"{Colors.NC} to filter\n")
        for line in content.splitlines():
            dm = re.search(r"test\.describe\('(.+?)'", line)
            if dm:
                current_describe = dm.group(1)
                print(f"  {Colors.GREEN}▸ {current_describe}{Colors.NC}")
            tm = re.search(r"test\('(.+?)'", line)
            if tm:
                test_name = tm.group(1)
                print(f"    • {test_name}")
        print()
        return 0
    print(Colors.success("Generating gallery screenshots for documentation..."))
    if filter_text:
        print(f"{Colors.YELLOW}Filter: only tests matching '{filter_text}'{Colors.NC}")
    viewports = []
    if not mobile_only:
        viewports.append(('desktop', '📸 Running Desktop Screenshots...'))
    if not desktop_only:
        viewports.append(('mobile', '📱 Running Mobile Screenshots...'))
    print(f"{Colors.BLUE}Viewports: {', '.join(v[0] for v in viewports)}{Colors.NC}")
    print(f"{Colors.BLUE}Screenshots will be saved to mkdocs_src/docs/gallery/{Colors.NC}\n")

    if not no_populate:
        # Populate test database with realistic data (creates fresh DB with --force)
        print(f"\n{Colors.CYAN}🗄️  Populating test database with sample data...{Colors.NC}")
        result = subprocess.run(
            ["python", "dev.py", "test", "db", "populate", "--force", "--clean", "--with-static", "--with-reports"],
            cwd=PROJECT_ROOT
        )
        if result.returncode != 0:
            print_error("Failed to populate test database")
            return 1
        print_success("Test database populated")

        # Ensure ALL test users exist
        print(f"\n{Colors.YELLOW}Ensuring E2E test users exist...{Colors.NC}")
        from scripts.test_runner import _ensure_test_users
        if not _ensure_test_users():
            print_error("Failed to create test users")
            return 1
        print_success("Test users ready")
    else:
        print(f"{Colors.YELLOW}⏭️  Skipping DB population (--no-populate){Colors.NC}")

    failures = []
    # Determine worker count: --workers flag or CPU count
    explicit_workers = getattr(args, 'workers', None)
    cpu_count = os.cpu_count() or 2
    worker_count = explicit_workers if explicit_workers else max(2, cpu_count)
    # Server workers: 1 per 4 browser workers, minimum 1
    server_workers = max(1, math.ceil(worker_count / 4))
    print(f"{Colors.BLUE}Browser workers: {worker_count}  |  Server workers: {server_workers}{Colors.NC}")

    # --- Port conflict check ---
    # Determine which port the test server will use
    effective_port = test_port or os.environ.get('TEST_PORT') or get_test_server_port()
    processes_using_port = check_port_in_use(int(effective_port))
    if processes_using_port:
        print_error(f"Port {effective_port} is already in use!")
        _print_port_help(int(effective_port), processes_using_port)
        print(f"\n{Colors.YELLOW}💡 You can use a different port:{Colors.NC}")
        print(f"   ./dev.py mkdocs gallery --test-port 8099\n")
        return 1

    # --- Headless by default (screenshots are pixel-perfect in headless mode) ---
    use_headed = getattr(args, 'headed', False)
    if use_headed:
        print(f"{Colors.YELLOW}🖥️  Running in headed mode (--headed){Colors.NC}")
    else:
        print(f"{Colors.BLUE}🔇 Running in headless mode (use --headed for visible browser){Colors.NC}")

    # Build a single Playwright command with all requested projects.
    # This shares one webServer process across desktop+mobile, avoiding port conflicts.
    cmd = [
        "npm", "run", "test:e2e", "--",
        "gallery.spec.ts",
        "--workers", str(worker_count),
    ]
    if use_headed:
        cmd.append("--headed")
    for viewport, _label in viewports:
        cmd.extend(["--project", viewport])
    if filter_text:
        cmd.extend(["-g", filter_text])

    viewport_labels = ', '.join(v[0] for v in viewports)
    print(f"\n{Colors.CYAN}📸 Running screenshots for: {viewport_labels}...{Colors.NC}")
    # Pass server worker count + optional port via env so playwright.config.ts can use it
    # Stream output live to terminal (no capture_output) so user sees progress
    gallery_env = os.environ.copy()
    gallery_env["GALLERY_SERVER_WORKERS"] = str(server_workers)
    if test_port:
        gallery_env["TEST_PORT"] = str(test_port)

    run_cmd = cmd

    try:
        result = subprocess.run(run_cmd, cwd=PROJECT_ROOT / "frontend", env=gallery_env)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Gallery interrupted by user (Ctrl+C){Colors.NC}")
        print(f"{Colors.YELLOW}Partial screenshots may have been saved to mkdocs_src/docs/gallery/{Colors.NC}")
        return 1
    if result.returncode != 0:
        failures = [v[0] for v in viewports]
        print_error(f"Gallery generation had failures (see above)")

    if failures:
        print(f"\n{Colors.YELLOW}⚠️  Gallery generation completed with failures in: {', '.join(failures)}{Colors.NC}")
        print(f"{Colors.YELLOW}Some screenshots may be missing or outdated. Run with --filter to retry specific tests.{Colors.NC}")
    else:
        print_success("\n✅ Gallery screenshots generated successfully!")
    print(f"{Colors.GREEN}Output: mkdocs_src/docs/gallery/{Colors.NC}")
    return 1 if failures else 0


def cmd_mkdocs_check_links(args):
    """Validate cross-boundary links: frontend/backend → MkDocs docs.

    Scope 1: Frontend docsPath / /mkdocs/ URLs → docs file existence + anchor check.
    Scope 2: Backend provider docs_url → docs file existence.
    """

    docs_root = PROJECT_ROOT / "mkdocs_src" / "docs"
    frontend_src = PROJECT_ROOT / "frontend" / "src"
    errors = []
    ok_count = 0

    print(Colors.success("🔗 Checking cross-boundary links (frontend/backend → docs)...\n"))

    # ── Scope 1: Frontend → docs ──────────────────────────────────────────
    print(f"{Colors.CYAN}── Scope 1: Frontend → MkDocs ──{Colors.NC}")

    # 1a. Collect docsPath values from .ts and .svelte files
    docs_paths: list[tuple[str, str, int]] = []  # (path, file, line)
    for ext in ("*.ts", "*.svelte"):
        for f in frontend_src.rglob(ext):
            for i, line in enumerate(f.read_text().splitlines(), 1):
                # static docsPath = '...'  or  docsPath: '...'
                m = re.search(r"""docsPath\s*[:=]\s*['"]([^'"]+)['"]""", line)
                if m:
                    docs_paths.append((m.group(1), str(f.relative_to(PROJECT_ROOT)), i))

    # 1b. Collect /mkdocs/ URLs from window.open and href=
    for ext in ("*.ts", "*.svelte"):
        for f in frontend_src.rglob(ext):
            for i, line in enumerate(f.read_text().splitlines(), 1):
                m = re.search(r"""/mkdocs/([^'"`,\s)]+)""", line)
                if m:
                    raw = m.group(1).rstrip("/")
                    # Skip template variables like ${prefix}
                    if "${" in raw:
                        # Extract after the template var — e.g. ${prefix}user/assets → user/assets
                        clean = re.sub(r"\$\{[^}]+\}", "", raw).lstrip("/")
                        if clean:
                            docs_paths.append((clean, str(f.relative_to(PROJECT_ROOT)), i))
                    elif ":path" not in raw:
                        docs_paths.append((raw, str(f.relative_to(PROJECT_ROOT)), i))

    # Deduplicate
    seen = set()
    unique_paths = []
    for path, src_file, line_no in docs_paths:
        key = path
        if key not in seen:
            seen.add(key)
            unique_paths.append((path, src_file, line_no))

    for path, src_file, line_no in sorted(unique_paths, key=lambda x: x[0]):
        # Split anchor
        if "#" in path:
            file_path_str, anchor = path.rsplit("#", 1)
        else:
            file_path_str, anchor = path, None

        # Normalize: path may end with / (directory) → look for index.en.md or file.en.md
        file_path_str = file_path_str.rstrip("/")
        candidates = [
            docs_root / f"{file_path_str}.en.md",
            docs_root / file_path_str / "index.en.md",
            docs_root / f"{file_path_str}.md",
            docs_root / file_path_str / "index.md",
        ]

        found_file = None
        for c in candidates:
            if c.exists():
                found_file = c
                break

        if not found_file:
            errors.append(f"  ❌ {path}\n     → File not found (from {src_file}:{line_no})")
        elif anchor:
            # Check anchor exists in file content (heading slug)
            content = found_file.read_text()
            # Generate slugs from headings + attr_list explicit anchors
            headings = re.findall(r"^#{1,6}\s+(.+?)(?:\s*\{[^}]*\})?\s*$", content, re.MULTILINE)
            attr_anchors = re.findall(r"\{\s*#([a-z0-9_-]+)\s*\}", content)

            slugs = set(attr_anchors)
            for h in headings:
                # Simple slug generation: lowercase, strip emoji, replace spaces/special with -
                slug = re.sub(r"[^\w\s-]", "", h.lower()).strip()
                slug = re.sub(r"[\s_]+", "-", slug).strip("-")
                slugs.add(slug)

            if anchor not in slugs:
                errors.append(f"  ⚠️  {path}\n     → File exists but anchor #{anchor} not found (from {src_file}:{line_no})")
            else:
                ok_count += 1
                print(f"  ✅ {path}")
        else:
            ok_count += 1
            print(f"  ✅ {path}")

    # ── Scope 2: Backend provider docs_url ────────────────────────────────
    print(f"\n{Colors.CYAN}── Scope 2: Backend provider docs_url ──{Colors.NC}")

    providers_dir = PROJECT_ROOT / "backend" / "app" / "services"
    for provider_subdir in ("fx_providers", "asset_source_providers"):
        pdir = providers_dir / provider_subdir
        if not pdir.exists():
            continue
        for f in sorted(pdir.glob("*.py")):
            content = f.read_text()
            for m in re.finditer(r"""['"](/mkdocs/[^'"]+)['"]""", content):
                url = m.group(1)
                raw = url.replace("/mkdocs/", "").rstrip("/")
                if "#" in raw:
                    file_part, anchor = raw.rsplit("#", 1)
                    file_part = file_part.rstrip("/")
                else:
                    file_part, anchor = raw, None

                candidates = [
                    docs_root / f"{file_part}.en.md",
                    docs_root / file_part / "index.en.md",
                    docs_root / f"{file_part}.md",
                    docs_root / file_part / "index.md",
                ]
                found_file = None
                for c in candidates:
                    if c.exists():
                        found_file = c
                        break

                rel_src = str(f.relative_to(PROJECT_ROOT))
                if not found_file:
                    errors.append(f"  ❌ {url}\n     → File not found (from {rel_src})")
                elif anchor:
                    fc = found_file.read_text()
                    headings = re.findall(r"^#{1,6}\s+(.+?)(?:\s*\{[^}]*\})?\s*$", fc, re.MULTILINE)
                    attr_anchors = re.findall(r"\{\s*#([a-z0-9_-]+)\s*\}", fc)
                    slugs = set(attr_anchors)
                    for h in headings:
                        slug = re.sub(r"[^\w\s-]", "", h.lower()).strip()
                        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
                        slugs.add(slug)
                    if anchor not in slugs:
                        errors.append(f"  ⚠️  {url}\n     → File exists but anchor #{anchor} not found (from {rel_src})")
                    else:
                        ok_count += 1
                        print(f"  ✅ {url}")
                else:
                    ok_count += 1
                    print(f"  ✅ {url}")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{Colors.CYAN}── Summary ──{Colors.NC}")
    print(f"  ✅ {ok_count} valid link(s)")
    if errors:
        print(f"  ❌ {len(errors)} broken link(s):\n")
        for e in errors:
            print(e)
        print()
        return 1
    else:
        print_success("All cross-boundary links are valid!")
        return 0


# =============================================================================
# Docker Commands
# =============================================================================

def _get_docker_tag(override: str | None = None) -> str:
    """Get Docker image tag from git version or override.

    Uses the same git-based versioning as `./dev.py info version`:
      - On a tag:       librefolio:v1.2.3
      - After commits:  librefolio:v1.2.3-5-gabcdef
      - Dirty tree:     librefolio:v1.2.3-dirty
      - No tags:        librefolio:v0.0.0-gabcdef
    """
    if override:
        return override

    from backend.app.utils.version import get_git_version
    version = get_git_version()  # e.g. "v0.5.0" or "v0.5.0-3-gabcdef-dirty"
    return f"librefolio:{version}"


def _check_env_file():
    """Check that .env exists; if not, abort with helpful instructions.

    Also warns when terminal environment variables override .env values
    for Docker-relevant variables (PORT, TEST_PORT).
    """
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        print_error("❌ .env file not found!")
        print()
        print(Colors.info("The .env file is required for Docker builds."))
        print(Colors.info("Create it from the example and edit the parameters:"))
        print()
        print(f"    cp {PROJECT_ROOT / '.env.example'} {env_file}")
        print(f"    $EDITOR {env_file}")
        print()
        return False

    # Check for shell env vars that override .env values
    DOCKER_VARS = ("PORT", "TEST_PORT")
    try:
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in DOCKER_VARS:
                shell_value = os.environ.get(key)
                if shell_value is not None and shell_value != value:
                    print_warning(
                        f"⚠ env variable {key} is set in terminal ({shell_value}) "
                        f"but differs from .env ({value})"
                    )
                    print(Colors.info(f"  Terminal value takes priority. To use .env value: unset {key}"))
    except Exception:
        pass  # Non-blocking: if .env parsing fails, just skip the check

    return True


def _docker_ensure_assets_built():
    """Ensure frontend, docs and JS cache are built/up-to-date before Docker image build.

    Uses the same staleness checks as the 'server' command so that
    ``dev.py docker build`` always produces an image with fresh assets.
    """
    from scripts.cli_base import check_frontend_needs_build

    # --- 1. Frontend ----------------------------------------------------------
    if check_frontend_needs_build():
        print_warning("Frontend build missing or outdated — building now...")
        class BuildArgs:
            debug = False
        result = cmd_fe_build(BuildArgs())
        if result != 0:
            print_error("Frontend build failed. Cannot build Docker image.")
            return result
        print_success("Frontend build ready")
    else:
        print(Colors.info("ℹ️  Frontend build is up to date"))

    # --- 2. MkDocs ------------------------------------------------------------
    docs_index = PROJECT_ROOT / "mkdocs_src" / "site" / "index.html"
    docs_dir = PROJECT_ROOT / "mkdocs_src" / "docs"
    needs_mkdocs = False

    if not docs_index.exists():
        needs_mkdocs = True
    else:
        try:
            build_time = docs_index.stat().st_mtime
            for doc_file in docs_dir.rglob("*.md"):
                if doc_file.stat().st_mtime > build_time:
                    needs_mkdocs = True
                    break
        except Exception:
            needs_mkdocs = True

    if needs_mkdocs:
        print_warning("MkDocs build missing or outdated — building now...")
        copy_docs_assets()
        result = run_pipenv(["mkdocs", "build", "-f", "mkdocs_src/mkdocs.yml"])
        if result != 0:
            print_error("MkDocs build failed. Cannot build Docker image.")
            return result
        print_success("MkDocs build ready")
    else:
        print(Colors.info("ℹ️  MkDocs build is up to date"))

    # --- 3. JS library cache --------------------------------------------------
    update_js_cache()

    # --- 4. requirements.txt for Docker (no pipenv needed in image) -----------
    req_file = PROJECT_ROOT / "requirements.txt"
    lock_file = PROJECT_ROOT / "Pipfile.lock"
    needs_req = not req_file.exists()
    if not needs_req:
        # Regenerate if Pipfile.lock is newer than requirements.txt
        try:
            needs_req = lock_file.stat().st_mtime > req_file.stat().st_mtime
        except Exception:
            needs_req = True

    if needs_req:
        print(Colors.info("📦 Generating requirements.txt from Pipfile.lock..."))
        result = subprocess.run(
            ["pipenv", "requirements"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        if result.returncode != 0:
            print_error(f"Failed to generate requirements.txt: {result.stderr}")
            return 1
        req_file.write_text(result.stdout)
        print_success("requirements.txt generated")
    else:
        print(Colors.info("ℹ️  requirements.txt is up to date"))

    return 0


def cmd_docker_build(args):
    """Build the Docker image with git-based versioning."""
    if not _check_env_file():
        return 1
    tag_override = getattr(args, 'tag', None)
    no_cache = getattr(args, 'no_cache', False)

    result = _docker_ensure_assets_built()
    if result != 0:
        return result

    image_tag = _get_docker_tag(tag_override)
    print(Colors.success(f"🐳 Building Docker image: {image_tag}..."))
    docker_cmd = ["docker", "build", "-t", image_tag]
    # Also tag as 'librefolio:latest'
    docker_cmd.extend(["-t", "librefolio:latest"])
    if no_cache:
        docker_cmd.append("--no-cache")
    docker_cmd.append(".")
    result = run_command_live(docker_cmd)
    if result == 0:
        print_success(f"✅ Image built: {image_tag} (also tagged librefolio:latest)")
    return result


def cmd_docker_rebuild(args):
    """Rebuild image, stop running containers, restart with new version."""
    if not _check_env_file():
        return 1
    tag_override = getattr(args, 'tag', None)
    no_cache = getattr(args, 'no_cache', False)

    print(Colors.success("🐳 Rebuild: build new image → stop → start..."))
    print()

    # Step 1: Build new image
    result = _docker_ensure_assets_built()
    if result != 0:
        return result

    image_tag = _get_docker_tag(tag_override)
    print(Colors.info(f"[1/3] Building new image: {image_tag}..."))
    docker_cmd = ["docker", "build", "-t", image_tag, "-t", "librefolio:latest"]
    if no_cache:
        docker_cmd.append("--no-cache")
    docker_cmd.append(".")
    result = run_command_live(docker_cmd)
    if result != 0:
        print_error("Build failed — containers NOT restarted.")
        return result
    print_success(f"Image built: {image_tag}")
    print()

    # Step 2: Stop current containers
    print(Colors.info("[2/3] Stopping current containers..."))
    run_command_live(["docker", "compose", "down"])
    print()

    # Step 3: Start with new image
    print(Colors.info("[3/3] Starting containers with new image..."))
    result = run_command_live(["docker", "compose", "up", "-d"])
    if result == 0:
        print_success(f"✅ Rebuild complete: {image_tag} is now running")
    return result


def cmd_docker_up(args):
    """Start containers with docker compose."""
    detach = not getattr(args, 'no_detach', False)
    print(Colors.success("🐳 Starting LibreFolio containers..."))
    cmd = ["docker", "compose", "up"]
    if detach:
        cmd.append("-d")
    return run_command_live(cmd)


def cmd_docker_down(args):
    """Stop containers."""
    print(Colors.success("🐳 Stopping LibreFolio containers..."))
    return run_command_live(["docker", "compose", "down"])


def cmd_docker_logs(args):
    """Show container logs."""
    follow = getattr(args, 'follow', False)
    cmd = ["docker", "compose", "logs"]
    if follow:
        cmd.append("-f")
    return run_command_live(cmd)


def cmd_docker_status(args):
    """Show container status."""
    return run_command_live(["docker", "compose", "ps"])


def cmd_docker_exec(args):
    """Execute a dev.py command inside the running Docker container.

    Examples:
        ./dev.py docker exec server --test
        ./dev.py docker exec test db populate --force
        ./dev.py docker exec user create admin admin@test.com Pass123!
        ./dev.py docker exec db upgrade
    """
    extra = getattr(args, 'cmd_args', [])
    if not extra:
        print_error("No command specified. Usage: ./dev.py docker exec <command> [args...]")
        print(Colors.info("Examples:"))
        print(f"  ./dev.py docker exec server --test")
        print(f"  ./dev.py docker exec test db populate --force")
        print(f"  ./dev.py docker exec user create admin admin@test.com Pass123!")
        return 1

    cmd = ["docker", "compose", "exec", "librefolio", "python", "dev.py"] + extra
    print(Colors.info(f"🐳 Running in container: dev.py {' '.join(extra)}"))
    return run_command_live(cmd)


# =============================================================================
# Format/Lint Commands
# =============================================================================

def cmd_format(args):
    """Format code with black."""
    print(Colors.success("Formatting code with black..."))
    return run_pipenv(["black", "backend/"])


def cmd_lint(args):
    """Lint code with ruff."""
    print(Colors.success("Linting code with ruff..."))
    return run_pipenv(["ruff", "check", "backend/"])


# =============================================================================
# Shell/Install Commands
# =============================================================================

def cmd_shell(args):
    """Open shell in virtualenv."""
    print(Colors.success("Opening shell in virtualenv..."))
    return run_command_live(["pipenv", "shell"])


def cmd_install(args):
    """Install all dependencies."""
    print_header("Installing LibreFolio Dependencies")
    print()

    print(Colors.info("[1/4] Installing Python backend dependencies..."))
    result = run_command_live(["pipenv", "install", "--dev"])
    if result != 0:
        print_error("Failed to install Python dependencies")
        return result
    print_success("Python dependencies installed")
    print()

    print(Colors.info("[2/4] Installing root project tools..."))
    result = run_command_live(["npm", "install"])
    if result != 0:
        print_error("Failed to install root npm dependencies")
        return result
    print_success("Root project tools installed")
    print()

    print(Colors.info("[3/4] Installing frontend dependencies..."))
    result = run_command_live(["npm", "install"], cwd=PROJECT_ROOT / "frontend")
    if result != 0:
        print_error("Failed to install frontend dependencies")
        return result
    print_success("Frontend dependencies installed")
    print()

    print(Colors.info("[4/4] Installing Playwright browsers..."))
    print(Colors.warning("   (This may take a while, ~500-700MB download)"))
    result = run_command_live(["npx", "playwright", "install"])
    if result != 0:
        print_warning("Playwright browser installation had issues (non-critical)")
    else:
        print_success("Playwright browsers installed")
    print()

    print_header("✅ All dependencies installed!")
    return 0


# =============================================================================
# Helper Functions
# =============================================================================

def auto_build_frontend(debug=False):
    """
    Auto-build frontend if needed.
    Uses shared logic from cli_base with dev.py's build function.
    """
    from scripts.cli_base import check_frontend_needs_build

    if not check_frontend_needs_build():
        print(Colors.info("ℹ️  Frontend build is up to date"))
        return None

    print(Colors.info("📦 Frontend sources changed, rebuilding..."))

    # Create args object for cmd_fe_build
    class BuildArgs:
        pass
    args = BuildArgs()
    args.debug = debug
    return cmd_fe_build(args)



def auto_build_mkdocs():
    """Auto-build mkdocs if needed."""
    site_dir = PROJECT_ROOT / "mkdocs_src" / "site"
    docs_dir = PROJECT_ROOT / "mkdocs_src" / "docs"

    if not site_dir.exists() or not (site_dir / "index.html").exists():
        print(Colors.info("📚 Documentation build missing, building..."))
        copy_docs_assets()
        run_pipenv(["mkdocs", "build", "-f", "mkdocs_src/mkdocs.yml"])
        return

    try:
        build_time = (site_dir / "index.html").stat().st_mtime
        for doc_file in docs_dir.rglob("*.md"):
            if doc_file.stat().st_mtime > build_time:
                print(Colors.info("📚 Documentation changed, rebuilding..."))
                copy_docs_assets()
                run_pipenv(["mkdocs", "build", "-f", "mkdocs_src/mkdocs.yml"])
                return
    except Exception:
        pass


def generate_favicon():
    """Generate a square 48x48 favicon from logo.png (logo is non-square 765x944)."""
    from PIL import Image
    src = PROJECT_ROOT / "frontend" / "static" / "logo.png"
    dst = PROJECT_ROOT / "frontend" / "static" / "favicon.png"
    if not src.exists():
        print_warning("logo.png not found, skipping favicon generation")
        return
    img = Image.open(src)
    w, h = img.size
    size = max(w, h)
    square = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    square.paste(img, ((size - w) // 2, (size - h) // 2))
    square.resize((48, 48), Image.LANCZOS).save(dst)
    print_success(f"favicon.png generated (48×48 from {w}×{h} logo)")


def copy_docs_assets():
    """Copy logo, favicon, and icons to docs."""
    generate_favicon()
    static_dir = PROJECT_ROOT / "mkdocs_src" / "docs" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    src_logo = PROJECT_ROOT / "frontend" / "static" / "logo.png"
    src_favicon = PROJECT_ROOT / "frontend" / "static" / "favicon.png"
    src_icons = PROJECT_ROOT / "frontend" / "static" / "icons"

    if src_logo.exists():
        shutil.copy(src_logo, static_dir / "logo.png")
    if src_favicon.exists():
        shutil.copy(src_favicon, static_dir / "favicon.png")
    
    # Copy icons folder
    if src_icons.exists():
        dest_icons = static_dir / "icons"
        if dest_icons.exists():
            shutil.rmtree(dest_icons)
        shutil.copytree(src_icons, dest_icons)


def update_js_cache():
    """Update JS library cache."""
    result = run_command_live(
        [*pipenv_prefix(), "python", "scripts/update_js_cache.py"],
        cwd=PROJECT_ROOT
    )
    if result == 0:
        print_success("JS libraries cached")
    else:
        print_warning("JS cache update failed (will use CDN fallback)")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = TreeParser(
        description="LibreFolio Development CLI",
        formatter_class=format_help,
        epilog="""
Commands by Category:

  🖥️  Backend
      server              Start development server (--test for test mode)
      db                  Database commands (check, upgrade, create-clean...)

  🎨  Frontend
      front               Frontend commands (dev, build, check, preview)

  🧪  Testing
      test                Run tests (api, db, external, schemas, services...)

  👤  Users
      user                User management (create, list, reset, promote...)

  📚  Documentation
      mkdocs              MkDocs commands (build, serve, clean, deploy)

  📦  Tools
      api                 API schema commands (schema, client, sync)
      i18n                Translation commands (audit)
      cache               Cache management (js)
      info                Information commands (api)
      format              Format code with black
      lint                Lint code with ruff

  🔧  Setup
      shell               Open pipenv shell
      install             Install all dependencies

Examples:
  ./dev.py server              Start development server
  ./dev.py server --test       Start in test mode (test database)
  ./dev.py server --debug      Start with DEBUG logging + debug frontend build
  ./dev.py server --rebuild    Force rebuild frontend before starting
  ./dev.py server -r -d        Rebuild frontend in debug mode + DEBUG logs
  ./dev.py test api auth       Run auth API tests
  ./dev.py db upgrade          Apply migrations
  ./dev.py db create-clean     Delete and recreate database
  ./dev.py front build         Build frontend
  ./dev.py mkdocs serve        Serve documentation locally
  ./dev.py user list           List all users
"""
    )

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    # =========================================================================
    # 🖥️ Backend Commands Group
    # =========================================================================

    # Server (unified with --test flag)
    p = subparsers.add_parser("server", help="🖥️  Start development server")
    p.add_argument("--test", "-t", action="store_true", help="Use test database (port 8001)")
    p.add_argument("--rebuild", "-r", action="store_true", help="Force rebuild frontend before starting")
    p.add_argument("--debug", "-d", action="store_true", help="Debug mode: verbose logging + frontend debug build")
    p.add_argument("--force", "-f", action="store_true", help="Kill blocking processes on port before starting")
    p.add_argument("--workers", "-w", type=int, default=1, help="Number of uvicorn workers (default: 1)")
    p.add_argument("--host", type=str, default=None, help="Bind host (default: HOST env or 0.0.0.0)")
    p.add_argument("--port", "-p", type=int, default=None, help="Bind port (default: PORT env or 8000)")
    p.add_argument("--coverage", action="store_true", help="Enable backend code coverage tracking (writes .coverage.<pid>)")
    p.set_defaults(func=cmd_server)

    # Database
    p = subparsers.add_parser("db", help="🖥️  Database commands")
    db_sub = p.add_subparsers(dest="db_cmd", metavar="action")

    db_p = db_sub.add_parser("check", help="Verify CHECK constraints")
    db_p.add_argument("path", nargs="?", help="Database path (default: app.db)")
    db_p.set_defaults(func=cmd_db_check)

    db_p = db_sub.add_parser("current", help="Show current migration")
    db_p.add_argument("path", nargs="?", help="Database path")
    db_p.set_defaults(func=cmd_db_current)

    db_p = db_sub.add_parser("migrate", help="Create new migration")
    db_p.add_argument("message", help="Migration message")
    db_p.add_argument("path", nargs="?", help="Database path")
    db_p.set_defaults(func=cmd_db_migrate)

    db_p = db_sub.add_parser("upgrade", help="Apply pending migrations")
    db_p.add_argument("path", nargs="?", help="Database path")
    db_p.set_defaults(func=cmd_db_upgrade)

    db_p = db_sub.add_parser("downgrade", help="Rollback one migration")
    db_p.add_argument("path", nargs="?", help="Database path")
    db_p.set_defaults(func=cmd_db_downgrade)

    db_p = db_sub.add_parser("create-clean", help="Delete DB and recreate with latest migration")
    db_p.add_argument("--test", "-t", action="store_true", help="Use test database")
    db_p.set_defaults(func=cmd_db_create_clean)

    # =========================================================================
    # 🎨 Frontend Commands Group
    # =========================================================================

    p = subparsers.add_parser("front", help="🎨 Frontend commands")
    fe_sub = p.add_subparsers(dest="fe_cmd", metavar="action")

    fe_p = fe_sub.add_parser("dev", help="Start dev server with HMR")
    fe_p.set_defaults(func=cmd_fe_dev)

    fe_p = fe_sub.add_parser("build", help="Build for production")
    fe_p.add_argument("--debug", "-d", action="store_true", help="Build in debug mode (no minify, with sourcemaps)")
    fe_p.set_defaults(func=cmd_fe_build)

    fe_p = fe_sub.add_parser("check", help="Type check with svelte-check")
    fe_p.set_defaults(func=cmd_fe_check)

    fe_p = fe_sub.add_parser("preview", help="Preview production build")
    fe_p.set_defaults(func=cmd_fe_preview)

    # =========================================================================
    # 🧪 Testing Commands - Import from test_runner
    # =========================================================================

    from scripts.test_runner import register_subparser as register_test_parser
    register_test_parser(subparsers)

    # =========================================================================
    # 👤 User Commands - Import from user_cli
    # =========================================================================

    from scripts.user_cli import register_subparser as register_user_parser
    register_user_parser(subparsers)

    # =========================================================================
    # 📚 Documentation Commands
    # =========================================================================

    p = subparsers.add_parser("mkdocs", help="📚 MkDocs documentation commands")
    mk_sub = p.add_subparsers(dest="mk_cmd", metavar="action")

    mk_p = mk_sub.add_parser("build", help="Build documentation site")
    mk_p.set_defaults(func=cmd_mkdocs_build)

    mk_p = mk_sub.add_parser("serve", help="Serve documentation locally (port 8002)")
    mk_p.set_defaults(func=cmd_mkdocs_serve)

    mk_p = mk_sub.add_parser("clean", help="Remove built site/ directory")
    mk_p.set_defaults(func=cmd_mkdocs_clean)

    mk_p = mk_sub.add_parser("deploy", help="Deploy to GitHub Pages")
    mk_p.set_defaults(func=cmd_mkdocs_deploy)

    mk_p = mk_sub.add_parser("gallery", help="Generate gallery screenshots with Playwright")
    mk_p.add_argument("--list", "-l", action="store_true", dest="list_tests",
                       help="List available gallery test names (for use with --filter)")
    mk_p.add_argument("--filter", "-f", type=str, default=None,
                       help="Filter: only run tests matching this text (passed as -g to Playwright)")
    mk_p.add_argument("--desktop-only", action="store_true",
                       help="Only generate desktop screenshots")
    mk_p.add_argument("--mobile-only", action="store_true",
                       help="Only generate mobile screenshots")
    mk_p.add_argument("--no-populate", action="store_true",
                       help="Skip DB population (faster for re-runs)")
    mk_p.add_argument("--workers", "-w", type=int, default=None,
                       help="Number of Playwright workers (default: CPU count)")
    mk_p.add_argument("--test-port", type=int, default=None,
                       help="Port for the test server (default: TEST_PORT env or 8001)")
    mk_p.add_argument("--headed", action="store_true",
                       help="Run browser in headed mode (visible window) instead of headless")
    mk_p.set_defaults(func=cmd_mkdocs_gallery)

    mk_p = mk_sub.add_parser("check-links", help="Validate cross-boundary links (frontend/backend → docs)")
    mk_p.set_defaults(func=cmd_mkdocs_check_links)

    # Translate - Import from mkdocs_src/aphra-pipeline/translate_docs.py
    # (not available inside Docker — aphra-pipeline is excluded from image)
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "mkdocs_src" / "aphra-pipeline"))
        from translate_docs import register_subparser as register_translate_parser
        register_translate_parser(mk_sub)

        # Translate-validate - structural validation of translated files
        from validate_translations import register_subparser as register_validate_parser
        register_validate_parser(mk_sub)
    except (ImportError, ModuleNotFoundError):
        pass  # Not available in Docker runtime

    # =========================================================================
    # 📦 Tools Commands Group
    # =========================================================================

    # API
    p = subparsers.add_parser("api", help="📦 API schema commands")
    api_sub = p.add_subparsers(dest="api_cmd", metavar="action")

    api_p = api_sub.add_parser("schema", help="Export OpenAPI schema")
    api_p.set_defaults(func=cmd_api_schema)

    api_p = api_sub.add_parser("client", help="Generate TypeScript client")
    api_p.set_defaults(func=cmd_api_client)

    api_p = api_sub.add_parser("sync", help="Export schema + generate client")
    api_p.set_defaults(func=cmd_api_sync)

    # i18n - Import from frontend/scripts/i18n-audit.py
    # (not available inside Docker — frontend/scripts is excluded from image)
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "frontend" / "scripts"))
        from importlib import import_module
        i18n_module = import_module("i18n-audit")
        i18n_module.register_subparser(subparsers)
    except (ImportError, ModuleNotFoundError):
        pass  # Not available in Docker runtime

    # Cache - Import from scripts/update_js_cache.py
    from scripts.update_js_cache import register_subparser as register_cache_parser
    register_cache_parser(subparsers)

    # Info
    p = subparsers.add_parser("info", help="📦 Information commands")
    info_sub = p.add_subparsers(dest="info_cmd", metavar="action")

    info_p = info_sub.add_parser("api", help="List all API endpoints")
    info_p.set_defaults(func=cmd_info_api)

    info_p = info_sub.add_parser("version", help="Show application version")
    info_p.set_defaults(func=cmd_info_version)

    # Docker
    p = subparsers.add_parser("docker", help="🐳 Docker commands")
    docker_sub = p.add_subparsers(dest="docker_cmd", metavar="action")

    docker_p = docker_sub.add_parser("build", help="Build Docker image (tag from git version)")
    docker_p.add_argument("--tag", "-t", default=None, help="Override image tag (default: librefolio:<git-version>)")
    docker_p.add_argument("--no-cache", action="store_true", help="Build without Docker cache")
    docker_p.set_defaults(func=cmd_docker_build)

    docker_p = docker_sub.add_parser("rebuild", help="Build new image → stop containers → restart with new version")
    docker_p.add_argument("--tag", "-t", default=None, help="Override image tag (default: librefolio:<git-version>)")
    docker_p.add_argument("--no-cache", action="store_true", help="Build without Docker cache")
    docker_p.set_defaults(func=cmd_docker_rebuild)

    docker_p = docker_sub.add_parser("up", help="Start containers (docker compose up)")
    docker_p.add_argument("--no-detach", action="store_true", help="Run in foreground")
    docker_p.set_defaults(func=cmd_docker_up)

    docker_p = docker_sub.add_parser("down", help="Stop containers (docker compose down)")
    docker_p.set_defaults(func=cmd_docker_down)

    docker_p = docker_sub.add_parser("logs", help="Show container logs")
    docker_p.add_argument("-f", "--follow", action="store_true", help="Follow log output")
    docker_p.set_defaults(func=cmd_docker_logs)

    docker_p = docker_sub.add_parser("status", help="Show container status")
    docker_p.set_defaults(func=cmd_docker_status)

    docker_p = docker_sub.add_parser("exec", help="Run a dev.py command inside the container")
    docker_p.add_argument("cmd_args", nargs=argparse.REMAINDER, help="Command and arguments (e.g. server --test)")
    docker_p.set_defaults(func=cmd_docker_exec)

    # Format & Lint
    p = subparsers.add_parser("format", help="📦 Format code with black")
    p.set_defaults(func=cmd_format)

    p = subparsers.add_parser("lint", help="📦 Lint code with ruff")
    p.set_defaults(func=cmd_lint)

    # =========================================================================
    # 🔧 Setup Commands Group
    # =========================================================================

    p = subparsers.add_parser("shell", help="🔧 Open pipenv shell")
    p.set_defaults(func=cmd_shell)

    p = subparsers.add_parser("install", help="🔧 Install all dependencies")
    p.set_defaults(func=cmd_install)

    # =========================================================================
    # Enable autocompletion and parse
    # =========================================================================

    if HAS_ARGCOMPLETE:
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if hasattr(args, 'func'):
        return args.func(args) or 0
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())

