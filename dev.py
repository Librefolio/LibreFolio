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

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time
from html import unescape
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit

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

import scripts.docs_links as docs_links
import scripts.i18n_catalog as i18n_catalog
from scripts.cli_base import (
    Colors,
    check_server_running,
    configure_server_runtime,
    configure_test_runtime,
    get_data_dir,
    get_database_path,
    get_server_host,
    get_server_port,
    get_server_port_for_db,
    get_test_database_path,
    get_test_server_port,
    pipenv_prefix,
    print_error,
    print_header,
    print_success,
    print_warning,
    record_tool_contract_inputs,
    run_command,
    run_command_live,
    run_pipenv,
    run_server_live,
    tool_contract_fingerprint,
)
from scripts.cli_tree_parser import TreeParser, format_help

# =============================================================================
# Backend Commands: Server
# =============================================================================

def check_port_in_use(port: int) -> list:
    """The processes listening on ``port``, as (PID, process_name) tuples; empty when nothing listens.

    Only a listener counts, as in the test runner's ``port_holders`` (``scripts/test_runner/_server.py``): a client
    connected to the port, or the accepted connection of a server that closed its listener, keeps nobody from binding
    it (H-12). ``lsof`` answers that wherever it exists. On Linux without ``lsof``, ``fuser`` is the fallback, and it
    also names a process that only holds an accepted connection on the port.
    """
    pids = []
    try:
        if shutil.which("lsof"):
            result = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], capture_output=True, text=True)
            pids = [int(p) for p in result.stdout.split() if p.isdigit()]
        elif platform.system() == "Linux":
            # fuser prints the PIDs on stdout and the "port/tcp:" label on stderr. `capture_output`
            # cannot be combined with `stderr=`: Python raises ValueError before running anything.
            result = subprocess.run(["fuser", f"{port}/tcp"], stdout=subprocess.PIPE, text=True, stderr=subprocess.DEVNULL)
            pids = [int(p) for p in result.stdout.split() if p.isdigit()]
    except Exception:
        pass
    processes = []
    for pid in dict.fromkeys(pids):
        try:
            ps_result = subprocess.run(["ps", "-p", str(pid), "-o", "comm="], capture_output=True, text=True)
            processes.append((pid, ps_result.stdout.strip() or "unknown"))
        except Exception:
            processes.append((pid, "unknown"))
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
    print(f"  lsof -nP -iTCP:{port} -sTCP:LISTEN")
    print()
    print(f"{Colors.BLUE}To kill these processes:{Colors.NC}")
    print(f"  kill -9 {' '.join(pids)}")
    print()
    print(f"{Colors.YELLOW}Tip:{Colors.NC} This often happens when a previous server didn't shut down cleanly.")
    print(f"{Colors.YELLOW}     Use --force to automatically kill blocking processes.{Colors.NC}")


def _resolve_server_workers(value) -> int:
    """Resolve server worker CLI value to an integer."""
    if isinstance(value, str) and value.strip().lower() == "auto":
        cpu_count = os.cpu_count() or 1
        return max(1, 2 * (cpu_count - 1))
    try:
        workers = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("--workers must be a positive integer, 0, or auto") from exc
    if workers == 0:
        cpu_count = os.cpu_count() or 1
        return max(1, 2 * (cpu_count - 1))
    if workers < 0:
        raise ValueError("--workers must be a positive integer, 0, or auto")
    return workers


def _ensure_shared_jwt_secret(env: dict) -> None:
    """Give every uvicorn worker the same JWT secret: a fresh one when ``env`` has none.

    An empty or blank value counts as none: ``JWT_SECRET=`` in .env reaches the environment as ''
    through pipenv, and each worker would then make its own secret (auth_service), logging users
    out whenever a request lands on another worker.

    With ``JWT_SECRET_FILE`` set, every worker reads the secret from that file: nothing is generated.
    A blank ``JWT_SECRET`` beside it is left alone, because the server ignores a blank secret
    (``env_secret``) and the file wins.
    """
    if env.get("JWT_SECRET", "").strip() or env.get("JWT_SECRET_FILE", "").strip():
        return
    env["JWT_SECRET"] = secrets.token_urlsafe(64)


#: What ``dev.py server`` waits beyond the server's shutdown budget, for the process to exit (Z-10).
SERVER_STOP_MARGIN_SECONDS = 2


def _server_stop_grace(env: dict) -> Optional[float]:
    """How long ``dev.py server`` waits for the server once Ctrl+C or a SIGTERM asked it to stop (Z-10).

    The server's shutdown budget, ``LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`` in the environment it starts with (the
    default when the value cannot be used: the server logs that itself), plus ``SERVER_STOP_MARGIN_SECONDS``. None
    with no limit (budget 0): then only a second Ctrl+C or SIGTERM stops the wait.
    """
    from backend.app.config.sleep_wake import DEFAULT_SHUTDOWN_TIMEOUT_SECONDS, SleepWakeConfigError, shutdown_timeout_seconds  # noqa: PLC0415 — CLI-only import

    try:
        budget = shutdown_timeout_seconds(env)
    except SleepWakeConfigError:
        budget = DEFAULT_SHUTDOWN_TIMEOUT_SECONDS
    return None if budget == 0 else float(budget + SERVER_STOP_MARGIN_SECONDS)


def cmd_server(args):
    """Start the development server; with --build-only, only build what it serves and exit."""
    test_mode = getattr(args, 'test', False)
    rebuild = getattr(args, 'rebuild', False)
    build_only = getattr(args, 'build_only', False)
    debug_mode = getattr(args, 'debug', False)
    force = getattr(args, 'force', False)
    try:
        workers = _resolve_server_workers(getattr(args, 'workers', 1))
    except ValueError as exc:
        print_error(str(exc))
        return 1
    host_override = getattr(args, 'host', None)
    port_override = getattr(args, 'port', None)
    data_dir_override = getattr(args, 'data_dir', None)
    coverage_mode = getattr(args, 'coverage', False)
    no_scheduler = getattr(args, 'no_scheduler', False)
    no_reload = getattr(args, 'no_reload', False)

    lane_settings = getattr(args, 'lane_settings', None)
    if lane_settings and not test_mode:
        print_error("--lane-setting works only with --test: it sets the instance of a test lane")
        return 1

    if test_mode:
        try:
            port, _ = configure_test_runtime(
                port=port_override,
                data_dir=data_dir_override,
                lane_settings=lane_settings,
            )
        except ValueError as exc:
            print_error(str(exc))
            return 1
        db = get_database_path(test_mode=True)
        debug_mode = True
    else:
        try:
            port, _ = configure_server_runtime(
                port=port_override,
                data_dir=data_dir_override,
            )
        except ValueError as exc:
            print_error(str(exc))
            return 1
        db = get_database_path(test_mode=False)

    # Apply --host / --port overrides (take priority over env vars)
    host = host_override if host_override else get_server_host()
    if port_override is not None:
        port = port_override

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

    # The test runner and the gallery run this first, in the foreground, so that these builds
    # (minutes after a merge) never count against the startup timeout of the server they start next.
    if build_only:
        print_success("Server prerequisites ready (--build-only): frontend, documentation and JS cache; server not started")
        return 0

    # Check immediately before binding. Builds can take minutes, so checking
    # before them left a large race in which another worktree could claim the
    # supposedly free lane.
    processes_using_port = check_port_in_use(port)
    if processes_using_port:
        if force:
            pids = [pid for pid, _ in processes_using_port]
            print_warning(f"Port {port} is in use — killing {len(pids)} blocking process(es)...")
            for pid, proc_name in processes_using_port:
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"  ✗ Killed PID {pid} ({proc_name})")
                except ProcessLookupError:
                    pass
                except PermissionError:
                    print_error(f"  Cannot kill PID {pid} ({proc_name}) — permission denied")
                    return 1
            time.sleep(1)
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
    if no_scheduler:
        print(Colors.warning("⏸️  Scheduler: DISABLED (--no-scheduler)"))
    print()
    print(f"{Colors.BLUE}{Colors.BOLD}Available endpoints:{Colors.NC}")
    print(f" ├── 🏠 {Colors.YELLOW}Frontend:  http://localhost:{port}/{Colors.NC}")
    if _frontend_build_has_designer_lab():
        print(f" ├── 🎨 {Colors.YELLOW}Designer Lab: http://localhost:{port}/designer-lab{Colors.NC}")
    # The API's documentation exists only with --debug or in test mode (H-55 R5): no link to a page that answers 404
    if debug_mode or test_mode:
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
        # Frontend E2E tests (Playwright) log in repeatedly against shared test users —
        # never let the donation popup signal fire and interfere with test assertions.
        env["LIBREFOLIO_DISABLE_DONATION_POPUP"] = "1"
        # Nor the «What's new» modal (C-54): the lanes' accounts predate it, and a modal on every first load would stop the suites.
        env["LIBREFOLIO_DISABLE_WHATS_NEW"] = "1"
        # The suites sign in wrongly on purpose, from one address: the limit on failed sign-ins (F15) would refuse their
        # later attempts. Off on every lane (configure_test_runtime has dropped any LIBREFOLIO_* of .env and the shell);
        # its own tests turn it on in-process.
        env["LIBREFOLIO_LOGIN_LIMIT"] = "off"
        # MF-SI2: the E2E suites pick search results as one user, two provider probes a pick: the per-user probe limit
        # would refuse them in a parallel run. Off on every lane; its own tests build limiters in-process.
        env["LIBREFOLIO_PROBE_RATE_LIMIT"] = "0"
    else:
        env["LIBREFOLIO_TEST_MODE"] = "0"
    if debug_mode:
        env["LIBREFOLIO_LOG_LEVEL"] = "DEBUG"
        # The API's documentation, off on every other instance (H-55 R5)
        env["LIBREFOLIO_API_DOCS"] = "1"
    if no_scheduler:
        env["LIBREFOLIO_NO_SCHEDULER"] = "1"
    # Generate a shared JWT secret for all workers.
    # On macOS, Python uses 'spawn' (not fork) for multiprocessing, so each
    # uvicorn worker is a fresh process. Without a shared env var, each worker
    # would generate its own random secret → tokens invalid across workers.
    _ensure_shared_jwt_secret(env)
    # Shutdown budget (decision 35): uvicorn drains the requests in flight for 3/8 of
    # LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS, unless UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN is set by hand.
    from backend.app.config.sleep_wake import uvicorn_drain_env  # noqa: PLC0415 — CLI-only import

    env.update(uvicorn_drain_env(env))

    # uvicorn closes idle keep-alive connections after 5 s by default. A test
    # client that reuses a socket the server has just closed gets ECONNRESET on
    # a POST, which is not retried — it surfaces as a lone, unreproducible red.
    # Parallel E2E workers make it likelier: each context sits idle between
    # steps while the others work. 65 s is the usual browser/proxy figure and
    # outlives any gap inside a test.
    keepalive_args = ["--timeout-keep-alive", "65"] if test_mode else []

    if coverage_mode:
        # Use 'coverage run --parallel-mode -m uvicorn' to track backend code
        # coverage during E2E tests.
        #
        # NOTE: --reload is NOT used in coverage mode because 'coverage run'
        # tracks only the direct process; reloader child processes bypass it.
        #
        # CRITICAL — SIGTERM propagation chain (3 levels of exec):
        #
        #   When Playwright finishes E2E tests, it sends SIGTERM to the webServer
        #   process. For 'coverage run' to write .coverage.<pid> files, SIGTERM
        #   must reach it directly. The process chain uses exec at every level:
        #
        #   1. playwright.config.ts: 'exec ./dev.py ...' → /bin/sh replaces itself
        #   2. dev.py (here): os.execvpe(pipenv, ...) → dev.py replaces itself
        #   3. pipenv run: os.execvpe(coverage, ...) → pipenv replaces itself
        #
        #   Result: single PID from Playwright → coverage run -m uvicorn.
        #   SIGTERM arrives directly, .coveragerc sigterm=true handles it,
        #   .coverage.<pid> file is written on graceful shutdown.
        #
        #   Without exec at ANY level, subprocess.run() creates a child process,
        #   SIGTERM only reaches the parent, the child becomes an orphan, and
        #   no coverage data is ever written.
        #
        #   MULTIPLE WORKERS: uvicorn --workers spawns child processes, and
        #   'coverage run' tracks only the process it starts — the same reason
        #   --reload is excluded above. Left alone, asking for N workers under
        #   coverage would measure the supervisor (which executes no app code)
        #   and silently discard everything the workers did.
        #
        #   .coveragerc declares 'concurrency = thread,gevent' for the common
        #   single-process case; adding 'multiprocessing' there would change the
        #   pytest runs too, so it is passed on the command line instead, only
        #   when it is actually needed. Measured with 2 workers: supervisor 0
        #   lines, each worker 224 — i.e. the children are fully tracked.
        coveragerc = str(PROJECT_ROOT / ".coveragerc")
        uvicorn_cmd = [
            *pipenv_prefix(), "coverage", "run",
            "--parallel-mode",
            f"--rcfile={coveragerc}",
            ]
        if workers > 1:
            uvicorn_cmd.extend(["--concurrency", "multiprocessing,thread,gevent"])
        uvicorn_cmd.extend([
            "-m", "uvicorn",
            "backend.app.main:app",
            "--host", host,
            "--port", str(port),
            ])
        if workers > 1:
            uvicorn_cmd.extend(["--workers", str(workers)])
        uvicorn_cmd.extend(keepalive_args)
        print(f"{Colors.YELLOW}📊 Coverage tracking enabled via 'coverage run'{Colors.NC}")
        print(f"{Colors.YELLOW}   Config: {coveragerc}{Colors.NC}")
        print(f"{Colors.YELLOW}   Coverage data will be written to .coverage.<pid> on shutdown{Colors.NC}")
        print()

        # Replace this process with coverage run (execvpe never returns)
        full_env = os.environ.copy()
        full_env.update(env)
        sys.stdout.flush()
        sys.stderr.flush()
        os.execvpe(uvicorn_cmd[0], uvicorn_cmd, full_env)
    else:
        uvicorn_cmd = [
            *pipenv_prefix(), "python", "-c",
            "import logging; logging.getLogger('watchfiles').setLevel(logging.WARNING); "
            "import uvicorn.main; uvicorn.main.main()",
            "backend.app.main:app",
            "--host", host,
            "--port", str(port),
            ]
        if workers > 1:
            uvicorn_cmd.extend(["--workers", str(workers)])
        else:
            # --reload is only safe/useful when 'watchfiles' is installed. Without
            # it uvicorn falls back to StatReload, which IGNORES --reload-exclude
            # (uvicorn logs a warning to that effect) and polls the *entire* tree —
            # including files the app writes at runtime (test DB, logs, mkdocs
            # site/). On CI (watchfiles not in Pipfile.lock) this produced an
            # endless reload loop: the server kept shutting down/restarting, so the
            # Playwright webServer never became ready → gallery/E2E 120s timeout.
            # An ephemeral test server needs no reload anyway, so only enable it
            # when watchfiles is present; otherwise run a plain, stable server.
            import importlib.util
            if no_reload:
                pass  # caller wants a single, plainly-killable process
            elif importlib.util.find_spec("watchfiles") is not None:
                uvicorn_cmd.append("--reload")
                # Exclude the git directory and the configured data directory
                uvicorn_cmd.extend([
                    "--reload-exclude", "**/.git/**",
                ])
                try:
                    data_dir_path = get_data_dir(test_mode=test_mode).resolve()
                    try:
                        rel_data_dir = data_dir_path.relative_to(PROJECT_ROOT)
                    except ValueError:
                        rel_data_dir = data_dir_path
                    uvicorn_cmd.extend([
                        "--reload-exclude", f"**/{rel_data_dir}/**",
                    ])
                except Exception:
                    pass
                # Always exclude the default backend/data folder recursively as well
                uvicorn_cmd.extend([
                    "--reload-exclude", "**/backend/data/**",
                ])
            else:
                print(f"{Colors.YELLOW}⚠️  watchfiles not installed → running WITHOUT --reload "
                      f"(StatReload ignores --reload-exclude and can reload-loop).{Colors.NC}")

        uvicorn_cmd.extend(keepalive_args)
        # Ctrl+C and SIGTERM let the server finish its shutdown within its budget (Z-10).
        return run_server_live(uvicorn_cmd, env=env, grace_seconds=_server_stop_grace(env))


# =============================================================================
# Backend Commands: Database
# =============================================================================

def _named_db_file(args) -> tuple[Optional[Path], bool]:
    """The database file named on the command line, absolute: ``(None, True)`` when none was named.

    A relative path starts at the project root, like ``--data-dir`` (``dev.py`` runs from there).
    Returns ``(None, False)`` after printing why the path cannot be used.
    """
    raw = getattr(args, "path", None)
    if not raw:
        return None, True
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path = path.resolve()
    # '%' breaks Alembic's config interpolation; '?' and '#' would end the path part of the SQLite URL.
    if any(char in str(path) for char in "%?#"):
        print_error(f"Database path cannot contain '%', '?' or '#': {path}")
        return None, False
    if path.is_dir():
        print_error(f"Database path is a directory: {path}")
        return None, False
    return path, True


def _existing_db_file(args) -> tuple[Optional[Path], bool]:
    """``_named_db_file``, refusing a file that does not exist: only ``db upgrade`` creates one."""
    db_file, ok = _named_db_file(args)
    if ok and db_file is not None and not db_file.is_file():
        print_error(f"Database not found: {db_file}")
        return None, False
    return db_file, ok


def _alembic(db_file: Optional[Path], *alembic_args: str) -> list:
    """``alembic`` on ``db_file`` when one was named, otherwise on the configured database.

    The file reaches ``backend/alembic/env.py`` as ``-x sqlalchemy.url``. An environment variable
    cannot do it: ``get_settings()`` computes ``DATABASE_URL`` from the data directory and overwrites it.
    """
    cmd = [*pipenv_prefix(), "alembic", "-c", "backend/alembic.ini"]
    if db_file is not None:
        cmd += ["-x", f"sqlalchemy.url=sqlite:///{db_file}"]
    return [*cmd, *alembic_args]


def cmd_db_check(args):
    """Verify CHECK constraints in database."""
    db_file, ok = _existing_db_file(args)
    if not ok:
        return 1
    print(Colors.success(f"Checking database constraints: {db_file or get_database_path()}"))
    env = {"ALEMBIC_DATABASE_URL": f"sqlite:///{db_file}"} if db_file else None
    return run_pipenv(["python", "-m", "backend.alembic.check_constraints_hook"], env=env)


def cmd_db_currencies(args):
    """List the stored currency codes that are not ISO 4217 codes (E-19a): read-only, exit 1 when it lists some."""
    db_file, ok = _existing_db_file(args)
    if not ok:
        return 1
    print(Colors.success(f"Checking stored currency codes: {db_file or get_database_path()}"))
    command = ["python", "-m", "backend.app.services.platform.stored_currencies"]
    if db_file is not None:
        command += ["--db-file", str(db_file)]
    return run_pipenv(command)


def cmd_db_current(args):
    """Show current database migration."""
    db_file, ok = _existing_db_file(args)
    if not ok:
        return 1
    print(Colors.success(f"Current migration for: {db_file or get_database_path()}"))
    return run_command_live(_alembic(db_file, "current"))


def cmd_db_migrate(args):
    """Create a new migration."""
    db_file, ok = _existing_db_file(args)
    if not ok:
        return 1
    db_path = str(db_file or get_database_path())
    if not check_server_running("creating migrations", strict=True, port=get_server_port_for_db(db_path)):
        return 1

    message = args.message

    print(Colors.success(f"Creating migration: {message}"))
    return run_command_live(_alembic(db_file, "revision", "--autogenerate", "-m", message))


def cmd_db_upgrade(args):
    """Apply pending migrations; a named database file that does not exist yet is created."""
    db_file, ok = _named_db_file(args)
    if not ok:
        return 1
    db_path = str(db_file or get_database_path())
    if not check_server_running("applying migrations", strict=True, port=get_server_port_for_db(db_path)):
        return 1

    print(Colors.success(f"Upgrading database: {db_path}"))
    if db_file is not None:
        db_file.parent.mkdir(parents=True, exist_ok=True)
    return run_command_live(_alembic(db_file, "upgrade", "head"))


def cmd_db_downgrade(args):
    """Rollback one migration."""
    db_file, ok = _existing_db_file(args)
    if not ok:
        return 1
    db_path = str(db_file or get_database_path())
    if not check_server_running("rolling back migrations", strict=True, port=get_server_port_for_db(db_path)):
        return 1

    print(Colors.success(f"Downgrading database: {db_path}"))
    return run_command_live(_alembic(db_file, "downgrade", "-1"))


def cmd_db_create_clean(args):
    """Delete database and recreate with latest migration."""
    test_mode = getattr(args, 'test', False)
    if test_mode:
        db_path = Path(get_test_database_path())
    else:
        db_path = Path(get_database_path())

    if not check_server_running("recreating database", strict=True, port=get_server_port_for_db(str(db_path))):
        return 1

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
    # `vite dev` carries the Designer Lab unless LF_DESIGNER_LAB=0 (designerLabEnabled in vite-plugin.mjs).
    if os.environ.get("LF_DESIGNER_LAB") != "0":
        print(Colors.warning("🎨 Designer Lab: http://localhost:5173/designer-lab"))
    print()
    return run_command_live(["npm", "run", "dev"], cwd=PROJECT_ROOT / "frontend")


#: Where `npm ci` (in frontend/, from the lock) installs the frontend's command-line tools.
FRONTEND_NODE_BIN = PROJECT_ROOT / "frontend" / "node_modules" / ".bin"
#: What a frontend build calls: the API client generator (`generate-api`), `svelte-check`, and `vite` (`npm run build`).
FRONTEND_BUILD_BINARIES = ("openapi-zod-client", "svelte-check", "vite")
#: The API client and the Tool codecs need only their generator: `generate-api` runs it, `generate-tools` imports it.
API_CLIENT_BINARIES = ("openapi-zod-client",)


def missing_frontend_binaries(names) -> list[str]:
    """The tools of ``names`` that ``frontend/node_modules/.bin`` does not hold, in the order asked."""
    return [name for name in names if not (FRONTEND_NODE_BIN / name).exists()]


def require_frontend_dependencies(names, *, purpose: str) -> int:
    """0 when the frontend tools ``names`` are installed; otherwise say what is missing and return 1.

    Checked before any npm or npx call. Without ``frontend/node_modules``, ``npx`` does not fail: it fetches
    whatever version the registry serves (or one cached earlier) instead of the one the lock pins.
    """
    missing = missing_frontend_binaries(names)
    if not missing:
        return 0
    print_error(f"Cannot run {purpose}: the frontend dependencies are not installed (missing from frontend/node_modules/.bin: {', '.join(missing)})")
    print("   Install them from the lock file, then retry:  cd frontend && npm ci")
    print("   dev.py never falls back to npx: without node_modules it would run unpinned versions from the registry.")
    return 1


def cmd_fe_build(args):
    """Build frontend for production."""
    # Before anything that runs npm or npx: the API client generation and svelte-check below go through npx.
    deps_result = require_frontend_dependencies(FRONTEND_BUILD_BINARIES, purpose="the frontend build")
    if deps_result != 0:
        return deps_result

    # Ensure fonts/JS libs exist before SvelteKit prerender (validates app.html refs)
    # Only resources the frontend ships can stop this build: MathJax lives in
    # mkdocs_src/ and is never referenced from frontend/, so letting it abort
    # here blocked every fresh worktree over an asset the bundle does not carry.
    cache_result = update_js_cache(strict=True, required_for="frontend")
    if cache_result != 0:
        print_error("Resource cache incomplete - aborting frontend build")
        return cache_result

    # The Tool codegen inputs as `api sync` reads them: recorded below only when the build succeeds (H-24)
    tool_inputs = tool_contract_fingerprint(PROJECT_ROOT)

    # Sync API types to ensure frontend types are aligned with backend
    print(Colors.success("Syncing API types before build..."))
    sync_result = cmd_api_sync(args)
    if sync_result != 0:
        print_error("API sync failed - aborting build")
        return sync_result

    # The translation catalogue the app loads (src/lib/i18n/<lang>.json) is generated from its sources;
    # svelte-check below reads it before npm's own prebuild hook would run.
    if i18n_catalog.build(quiet=True) != 0:
        print_error("Translation catalogue could not be generated - aborting build")
        return 1

    # Generate favicon from logo before build
    generate_favicon()
    # sw.js names the offline page it caches by its hash: a build ships the stamp of the offline.html it copies (H-52)
    stamp_service_worker()

    # DIAGNOSTICS FOR GITHUB ACTIONS
    print(Colors.info("[DEBUG] Running svelte-check..."))
    run_command_live(["npx", "svelte-check", "--tsconfig", "./tsconfig.json"], cwd=PROJECT_ROOT / "frontend")
    print(Colors.info("[DEBUG] END OF DIAGNOSTICS"))

    if args.debug:
        print(Colors.success("Building frontend in DEBUG mode (no minify, with sourcemaps)..."))
        result = run_command_live(["npm", "run", "build:debug"], cwd=PROJECT_ROOT / "frontend")
    else:
        print(Colors.success("Building frontend for production..."))
        result = run_command_live(["npm", "run", "build"], cwd=PROJECT_ROOT / "frontend")

    if result == 0:
        # Record which mode this build was made in, so auto_build_frontend() can detect a
        # debug/production mismatch later (e.g. `./dev.py server --debug` after a plain
        # build) even when the build isn't otherwise stale. Not tracked by git (frontend/build
        # is gitignored).
        _write_frontend_build_mode_marker(debug=args.debug)
        record_tool_contract_inputs(PROJECT_ROOT, tool_inputs)
        print_success("Frontend build complete!")
        print(Colors.warning("Output in: frontend/build/"))
    else:
        print_error("Frontend build failed")
    return result


def cmd_fe_check(args):
    """Run svelte-check for type errors."""
    print(Colors.success("Running svelte-check for type errors..."))
    return run_command_live(["npm", "run", "check"], cwd=PROJECT_ROOT / "frontend")


def cmd_fe_format(args):
    """Format frontend code with Prettier."""
    if getattr(args, "check", False):
        print(Colors.success("Checking frontend formatting with Prettier..."))
        return run_command_live(["npm", "run", "format:check"], cwd=PROJECT_ROOT / "frontend")
    else:
        print(Colors.success("Formatting frontend code with Prettier..."))
        return run_command_live(["npm", "run", "format"], cwd=PROJECT_ROOT / "frontend")


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
    """Export API and build-only Tool schemas."""
    print(Colors.success("Exporting OpenAPI contracts..."))
    command = ["python", "scripts/list_api_endpoints.py"]
    if not getattr(args, "tools_only", False):
        command.extend(["--openapi-file", "frontend/src/lib/api/openapi.json"])
    command.extend(["--tool-contracts-file", "frontend/src/lib/api/tool-contracts.openapi.json"])
    return run_pipenv(command)


def cmd_api_client(args):
    """Generate the API client and exact Tool codecs from exported schemas."""
    deps_result = require_frontend_dependencies(API_CLIENT_BINARIES, purpose="the TypeScript contracts generation")
    if deps_result != 0:
        return deps_result
    print(Colors.success("Generating TypeScript contracts..."))
    script = "generate-tools" if getattr(args, "tools_only", False) else "generate-api"
    return run_command_live(
        ["npm", "run", script],
        cwd=PROJECT_ROOT / "frontend"
        )


def cmd_api_sync(args):
    """Export schemas and generate API/Tool clients, stopping on any failure."""
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
    from backend.app.utils.runtime.version import get_version_info
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
    Skips content inside fenced code blocks (``` or ~~~).
    """
    docs_dir = PROJECT_ROOT / "mkdocs_src" / "docs"
    adm_re = re.compile(r'^(?:!!!|[?]{3})\s+\w+')
    fence_re = re.compile(r'^(`{3,}|~{3,})')
    bad_files = []

    for md_file in sorted(docs_dir.rglob("*.md")):
        lines = md_file.read_text().splitlines()
        in_fence = False
        for i, line in enumerate(lines):
            # Track fenced code blocks
            if fence_re.match(line.strip()):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
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


_ASSET_TAG = re.compile(r"<(img|source|video|audio|a)\b([^>]*)>", re.IGNORECASE)
_ASSET_ATTR = re.compile(r"""(?<![\w-])(src|srcset|poster|href)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
_FILE_NAME = re.compile(r"\.[A-Za-z0-9]{1,5}$")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _relative_asset_urls(page_html: str):
    """Yield (tag, attribute, url) for each relative URL of a file in a built page.

    `<img>`/`<source>` `src`/`srcset`, `<video>` `src`/`poster`, `<audio>` `src`, and `<a href>` to a file that is not
    a page. External, root-absolute, fragment-only and `data:` URLs are left out, and so are HTML comments.
    """
    for tag_m in _ASSET_TAG.finditer(_HTML_COMMENT.sub("", page_html)):
        tag = tag_m.group(1).lower()
        for attr_m in _ASSET_ATTR.finditer(tag_m.group(2)):
            attr = attr_m.group(1).lower()
            if (attr == "href") != (tag == "a"):
                continue
            value = unescape(attr_m.group(2) if attr_m.group(2) is not None else attr_m.group(3))
            urls = [c.split()[0] for c in value.split(",") if c.strip()] if attr == "srcset" else [value]
            for url in urls:
                parts = urlsplit(url)
                if parts.scheme or parts.netloc or url.startswith(("/", "#")) or not parts.path:
                    continue
                if tag == "a" and (not _FILE_NAME.search(parts.path) or parts.path.lower().endswith((".html", ".htm"))):
                    continue
                yield tag, attr, url


def _check_asset_paths_in_built_site(site_dir: Path | None = None) -> list[tuple[str, str, str, str]]:
    """Check that every relative URL of a file in the built site resolves to a file.

    Each URL is resolved from its page's folder as a browser does (query and fragment dropped, percent-decoded); a
    folder URL needs an index.html, and nothing may resolve outside the site. MkDocs rewrites Markdown images and
    links, not raw HTML: a translated page is built one folder deeper (site/<lang>/...) and the language folders hold
    no files, so a raw-HTML path copied from the English breaks there. Returns the broken URLs as
    (page, tag, attribute, url) after printing them, or the count verified.
    """
    site_dir = (site_dir or PROJECT_ROOT / "mkdocs_src" / "site").resolve()
    if not site_dir.is_dir():
        return []

    broken = []
    checked = 0
    for html_file in sorted(site_dir.rglob("*.html")):
        page_html = html_file.read_text(encoding="utf-8", errors="ignore")
        for tag, attr, url in _relative_asset_urls(page_html):
            checked += 1
            target = (html_file.parent / unquote(urlsplit(url).path)).resolve()
            inside = target == site_dir or site_dir in target.parents
            if not inside or not (target.is_file() or (target / "index.html").is_file()):
                broken.append((html_file.relative_to(site_dir).as_posix(), tag, attr, url))

    if broken:
        print()
        print(Colors.error(f"❌ {len(broken)} broken asset URL(s) in the built site:"))
        for page, tag, attr, url in broken[:20]:
            print(f"  ❌ {page}")
            print(f"     <{tag} {attr}> → {url}")
        if len(broken) > 20:
            print(f"  ... and {len(broken) - 20} more")
        print(Colors.info("  Fix: a translated page is built one folder deeper (site/<lang>/...): a raw-HTML path copied from the" " English needs one more '../' (translate-validate reports such copies as html-asset-depth)."))
        print()
    else:
        print(Colors.success(f"✅ All {checked} relative asset URL(s) in the built site resolve"))
    return broken


def cmd_mkdocs_build(args):
    """Build MkDocs documentation."""
    print(Colors.success("Building MkDocs site..."))
    _check_admonition_empty_lines()
    copy_docs_assets()
    # --strict turns a nav entry pointing at a missing file from a silent warning
    # into a failure. Measured before enabling: the tree builds strict-clean with
    # zero warnings, so this adds a gate without importing pre-existing debt.
    result = run_pipenv(["mkdocs", "build", "--strict", "-f", "mkdocs_src/mkdocs.yml"])
    if result == 0 and _check_asset_paths_in_built_site():
        return 1
    return result


def cmd_mkdocs_serve(args):
    """Serve MkDocs documentation locally."""
    print(Colors.success("Serving MkDocs site (http://127.0.0.1:6042)"))
    copy_docs_assets()
    return run_pipenv(["mkdocs", "serve", "-f", "mkdocs_src/mkdocs.yml", "-a", "127.0.0.1:6042"])


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
    return run_pipenv(["mkdocs", "gh-deploy", "--force", "-f", "mkdocs_src/mkdocs.yml"])


def cmd_mkdocs_normalize_dashboard_fixture(args):
    """Rescale the gallery dashboard fixture to a 50K net worth (privacy normalization)."""
    from scripts.normalize_dashboard_fixture import normalize_file  # noqa: PLC0415 — CLI-only import

    return normalize_file(Path(args.path), getattr(args, "dry_run", False))


def _reuse_gallery_test_db() -> bool:
    """`mkdocs gallery --no-populate`: reuse the test database of an earlier run, as it is.

    Playwright's global-setup may only be told to stand down (``LF_SETUP_DONE``) once the database
    and the E2E users are really there; told nothing, it runs its own ``populate --force`` — a
    different dataset, without the static resources — under the freshly started backend.
    """
    from backend.app.config import get_test_data_dir  # noqa: PLC0415 — CLI-only import

    try:
        test_db = get_test_data_dir() / "sqlite" / "app.db"
    except ValueError as exc:
        print_error(f"Invalid test data directory: {exc}")
        return False
    if not test_db.is_file():
        print_error(f"--no-populate reuses an existing test database, and there is none at {test_db}: run once without --no-populate")
        return False
    from scripts.test_runner import _ensure_test_users  # noqa: PLC0415 — CLI-only import

    if not _ensure_test_users():
        print_error("Failed to create test users")
        return False
    print(f"{Colors.YELLOW}⏭️  Skipping DB population (--no-populate): reusing {test_db}{Colors.NC}")
    return True


#: Share of the CPUs the gallery gives to browser workers when --workers is not given. One per CPU saturated a
#: 10-CPU Mac (load 65, 8 reds in 10 minutes, requests stuck 10-20 s); 6 ran two 30-minute galleries green at load 11-16.
GALLERY_BROWSER_WORKERS_PER_CPU = 0.6


def default_gallery_workers(cpu_count: Optional[int] = None) -> int:
    """Browser workers of `mkdocs gallery` without --workers: 60% of the CPUs, at least one.

    ``None`` reads the CPU count when called, so a test (or a container) that changes it is seen.
    """
    cpus = cpu_count if cpu_count is not None else (os.cpu_count() or 2)
    return max(1, round(GALLERY_BROWSER_WORKERS_PER_CPU * cpus))


def cmd_mkdocs_gallery(args):
    """Generate gallery screenshots for documentation using Playwright."""

    list_tests = getattr(args, 'list_tests', False)
    filter_text = getattr(args, 'filter', None)
    desktop_only = getattr(args, 'desktop_only', False)
    mobile_only = getattr(args, 'mobile_only', False)
    no_populate = getattr(args, 'no_populate', False)
    test_port = getattr(args, 'test_port', None)
    force = getattr(args, 'force', False)

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
            ["python", "dev.py", "test", "-q", "db", "populate", "--force", "--clean", "--with-static", "--with-reports"],
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
    elif not _reuse_gallery_test_db():
        return 1

    failures = []
    # Determine worker count: --workers flag, or 60% of the CPUs (default_gallery_workers)
    explicit_workers = getattr(args, 'workers', None)
    worker_count = explicit_workers if explicit_workers else default_gallery_workers()
    # Server workers: browser workers here spend most of their time rendering,
    # so one server per four of them (vs one per two for API/E2E).
    from scripts.test_runner._server import CLIENTS_PER_SERVER_WORKER_GALLERY, build_server_prerequisites, server_workers_for
    server_workers = server_workers_for(worker_count, CLIENTS_PER_SERVER_WORKER_GALLERY)
    print(f"{Colors.BLUE}Browser workers: {worker_count}  |  Server workers: {server_workers}{Colors.NC}")

    # --- Port conflict check ---
    # Determine which port the test server will use
    effective_port = test_port or os.environ.get('TEST_PORT') or get_test_server_port()
    processes_using_port = check_port_in_use(int(effective_port))
    if processes_using_port:
        if force:
            # --force: kill blocking processes and continue
            pids = [pid for pid, _ in processes_using_port]
            print_warning(f"Port {effective_port} is in use — killing {len(pids)} blocking process(es)...")
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
            still_in_use = check_port_in_use(int(effective_port))
            if still_in_use:
                print_error(f"Port {effective_port} still in use after killing processes!")
                _print_port_help(int(effective_port), still_in_use)
                return 1
            print_success(f"Port {effective_port} is now free")
        else:
            print_error(f"Port {effective_port} is already in use!")
            _print_port_help(int(effective_port), processes_using_port)
            print(f"\n{Colors.YELLOW}💡 Use --force to kill zombie processes, or use a different port:{Colors.NC}")
            print(f"   ./dev.py mkdocs gallery --force")
            print(f"   ./dev.py mkdocs gallery --test-port 8099\n")
            return 1

    # --- Headless by default (screenshots are pixel-perfect in headless mode) ---
    use_headed = getattr(args, 'headed', False)
    use_ui = getattr(args, 'ui', False)
    if use_ui:
        print(f"{Colors.YELLOW}🖥️  Running in Playwright UI mode (--ui){Colors.NC}")
    elif use_headed:
        print(f"{Colors.YELLOW}🖥️  Running in headed mode (--headed){Colors.NC}")
    else:
        print(f"{Colors.BLUE}🔇 Running in headless mode (use --headed for visible browser, --ui for interactive){Colors.NC}")

    # Build a single Playwright command with all requested projects.
    # This shares one webServer process across desktop+mobile, avoiding port conflicts.
    cmd = [
        "npm", "run", "test:e2e", "--",
        "gallery.spec.ts",
        "--workers", str(worker_count),
        ]
    if use_ui:
        cmd.append("--ui")
    elif use_headed:
        cmd.append("--headed")
    for viewport, _label in viewports:
        cmd.extend(["--project", viewport])
    if filter_text:
        cmd.extend(["-g", filter_text])

    viewport_labels = ', '.join(v[0] for v in viewports)
    # Pass server worker count + optional port via env so playwright.config.ts can use it
    # Stream output live to terminal (no capture_output) so user sees progress
    gallery_env = os.environ.copy()
    gallery_env["GALLERY_SERVER_WORKERS"] = str(server_workers)
    # Always disable the scheduler during gallery runs — prevents live data updates
    # from changing charts/numbers between screenshots.
    gallery_env["LIBREFOLIO_NO_SCHEDULER"] = "1"
    # Both branches above leave a prepared DB with its E2E users (populated now, or
    # reused with --no-populate) — tell Playwright's global-setup to stand down.
    # Without this flag it re-runs `populate --force` under the freshly started
    # backend, wiping and rewriting the DB while the first browser workers are
    # already logging in (the first ~17 tests raced exactly that on 04/09).
    # Note: global-setup step 3 (initGlobalSettings via API) still runs —
    # the flag only stands down the DB populate + user creation.
    gallery_env["LF_SETUP_DONE"] = "1"
    if test_port:
        gallery_env["TEST_PORT"] = str(test_port)

    # Playwright's webServer starts `dev.py server --test` and waits STARTUP_TIMEOUT_S for it, and that
    # server builds a stale frontend (debug) and MkDocs before it binds. Built here first, in the
    # foreground, they no longer count against that wait. Same environment as the webServer's:
    # LF_APP_VERSION included, which the build bakes into the sidebar of every screenshot.
    if not build_server_prerequisites(env=gallery_env):
        print_error("The test server's builds failed: gallery not started")
        return 1

    print(f"\n{Colors.CYAN}📸 Running screenshots for: {viewport_labels}...{Colors.NC}")
    run_cmd = cmd

    try:
        # Use Popen to stream output live AND capture it for failure parsing
        proc = subprocess.Popen(
            run_cmd, cwd=PROJECT_ROOT / "frontend", env=gallery_env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
        output_lines = []
        for line in proc.stdout:
            print(line, end='')
            output_lines.append(line)
        proc.wait()
        returncode = proc.returncode
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Gallery interrupted by user (Ctrl+C){Colors.NC}")
        print(f"{Colors.YELLOW}Partial screenshots may have been saved to mkdocs_src/docs/gallery/{Colors.NC}")
        return 1

    # Parse failed test names from Playwright output
    # Playwright prints lines like:
    #   [desktop] › e2e/gallery.spec.ts:330:9 › Gallery Screenshots › Files › test name ───────
    failed_tests = []  # list of (viewport, test_name) tuples
    if returncode != 0:
        failures = [v[0] for v in viewports]
        in_failures_block = False
        for line in output_lines:
            stripped = line.strip()
            # Detect the failures summary block (e.g. "  1 failed")
            if re.match(r'^\d+ failed$', stripped):
                in_failures_block = True
                continue
            if in_failures_block:
                # Lines like: [desktop] › e2e/gallery.spec.ts:330:9 › Gallery Screenshots › Files › test name ───
                m = re.match(r'\[([\w]+)\]\s+›\s+\S+\s+›\s+Gallery Screenshots\s+›\s+(.+)', stripped)
                if m:
                    viewport = m.group(1).strip()   # 'desktop' or 'mobile'
                    test_name = m.group(2).strip()   # 'FX › Chart settings modal ───────'
                    failed_tests.append((viewport, test_name))
                elif stripped and not stripped.startswith('['):
                    # End of failures block (e.g. "X passed", empty line, etc.)
                    in_failures_block = False
        print_error(f"Gallery generation had failures (see above)")

    if failures:
        print(f"\n{Colors.YELLOW}⚠️  Gallery generation completed with failures in: {', '.join(failures)}{Colors.NC}")
        if failed_tests:
            print(f"\n{Colors.YELLOW}Failed tests:{Colors.NC}")
            for _vp, t in failed_tests:
                print(f"  ✗ {t}")
            print(f"\n{Colors.CYAN}💡 Retry failed tests with:{Colors.NC}")

            # Group by test name to detect which viewports failed
            from collections import defaultdict
            by_test: dict[str, list[str]] = defaultdict(list)
            for vp, t in failed_tests:
                # Strip trailing ─── decoration for the filter text
                clean_name = re.sub(r'\s*─+\s*$', '', t).strip()
                by_test[clean_name].append(vp)

            for test_name, vps in by_test.items():
                has_desktop = 'desktop' in vps
                has_mobile = 'mobile' in vps
                if has_desktop:
                    print(f"   ./dev.py mkdocs gallery --no-populate --desktop-only -f \"{test_name}\"")
                if has_mobile:
                    print(f"   ./dev.py mkdocs gallery --no-populate --mobile-only -f \"{test_name}\"")
                if has_desktop and has_mobile:
                    print(f"   ./dev.py mkdocs gallery --no-populate -f \"{test_name}\"  # both viewports")
            print()
        else:
            print(f"{Colors.YELLOW}Some screenshots may be missing or outdated. Run with --filter to retry specific tests.{Colors.NC}")
    else:
        print_success("\n✅ Gallery screenshots generated successfully!")
    print(f"{Colors.GREEN}Output: mkdocs_src/docs/gallery/{Colors.NC}")
    return 1 if failures else 0


# Declared perimeter of the explicit-anchor convention, measured 18 Sep 2026.
#
# Across the 22 risk-metrics pages there are 180 headings: 22 H1 page titles and
# 158 at H2 or deeper. All 158 carry an explicit ``{: #slug }`` so the anchor
# survives translation. The 22 H1s are excluded BY DESIGN, not by omission: a link
# to a page is written ``.../slug/`` with no fragment and already lands at the top,
# so ``.../value-at-risk/#value-at-risk`` would be a token with no future in which
# it is needed.
#
# ⚠️ Cite this as "158 of 158 H2+, 22 H1 excluded by design, 180 total" — never as a
# bare ratio. A full-coverage number with no stated perimeter reads as a finished
# job and switches off the next inspection, which is how an earlier count of this
# same convention reported 130/130 while silently measuring a subset. The figure
# "136 of 158" is wrong in the other direction and shows why the perimeter has to
# travel with the number: 158 is already the H1-excluded count, so subtracting the
# 22 again removes them twice.
def _mkdocs_page_anchors(md_file) -> frozenset[str]:
    """The anchor ids of a MkDocs page, as ``mkdocs build`` records them: the ids of its own render.

    The shared function of ``mkdocs_src/aphra-pipeline/page_anchors.py`` (translate-validate uses it too). It
    needs MkDocs, so it is imported here, when a link is checked: dev.py itself runs where MkDocs is absent.
    """
    from page_anchors import file_anchors  # noqa: PLC0415 — needs MkDocs: imported when a link is checked

    return file_anchors(md_file)


# Anchors already shipped broken in translated pages, recorded 18 Sep 2026.
#
# Each entry is a link that resolves in English and lands on the wrong place — or
# nowhere — in the listed languages, because the translated heading produced a
# different slug. They are listed here instead of failing the gate because the fix
# requires editing .it/.fr/.es bodies, which the English-only documentation rule
# forbids: the debt is cleared by the translation pipeline, not by this campaign.
#
# ⚠️ THIS LIST MUST ONLY EVER SHRINK. A new broken anchor is a regression and must
# turn the gate red; silencing it by adding a line here defeats the check entirely.
#
# Emptied 10 Oct 2026 (1.2 translation round): the three recorded anchors now exist in
# it/fr/es as shared explicit ids, so every link resolves in all four languages.
MKDOCS_ANCHOR_EXCEPTIONS: dict[str, tuple[str, ...]] = {}


def _mkdocs_check_anchor(en_file, anchor: str, path: str, origin: str, docs_root):
    """Validate an anchor in English *and* in every language that has a translation.

    A page without a translation is safe: mkdocs-static-i18n falls back to the English
    body, anchors included. A page *with* a translation serves the translated headings,
    so an anchor added to the English file alone is dead there — silently, because the
    English source still contains it.

    Returns ``None`` when the anchor resolves everywhere, the string ``"KNOWN"`` for a
    recorded exception, or an error message.
    """
    if anchor not in _mkdocs_page_anchors(en_file):
        return f"  ⚠️  {path}\n     → File exists but anchor #{anchor} not found (from {origin})"

    stem = en_file.name[: -len(".en.md")] if en_file.name.endswith(".en.md") else en_file.stem
    broken = []
    for lang in ("it", "fr", "es"):
        translated = en_file.parent / f"{stem}.{lang}.md"
        if translated.exists() and anchor not in _mkdocs_page_anchors(translated):
            broken.append(lang)

    if not broken:
        return None

    file_part = path.split("#", 1)[0].strip("/")
    allowed = MKDOCS_ANCHOR_EXCEPTIONS.get(f"{file_part}#{anchor}")
    if allowed is not None and set(broken) <= set(allowed):
        print(f"  🟡 {path}  (known: dead in {', '.join(broken)} — awaiting translation)")
        return "KNOWN"

    return (
        f"  ❌ {path}\n"
        f"     → Anchor #{anchor} resolves in English but is missing in: {', '.join(broken)}\n"
        f"       (from {origin}) — the translated heading produces a different slug"
    )


def cmd_mkdocs_check_links(args):
    """Validate cross-boundary links: frontend/backend → MkDocs docs.

    Scope 1: frontend docsPath / /mkdocs/ URLs / <DocsLink> props, including the
    ones whose value comes from a local constant or map — those used to be
    skipped, although their values are perfectly static.
    Scope 2: every backend ``*_providers`` / ``*_plugins`` package, by glob.

    Discovery lives in ``scripts/docs_links.py`` so it can be imported and
    interrogated by a test; this function owns presentation and the exit code.
    """

    docs_root = PROJECT_ROOT / "mkdocs_src" / "docs"
    frontend_src = PROJECT_ROOT / "frontend" / "src"
    try:
        # A link's anchor is checked against the page's own MkDocs render (page_anchors.py): the docs toolchain.
        import mkdocs  # noqa: F401, PLC0415 — the docs toolchain: dev.py runs without it
        import page_anchors  # noqa: F401, PLC0415 — mkdocs_src/aphra-pipeline, imported by this command only
    except ImportError as exc:
        print_error(f"check-links needs MkDocs and mkdocs_src/aphra-pipeline/page_anchors.py: {exc}")
        return 1
    errors = []
    ok_count = 0
    known_count = 0
    speculative_misses = []

    def _rel(origin: str) -> str:
        """Render an origin relative to the project root, keeping any ``:line`` suffix."""
        return str(origin).replace(f"{PROJECT_ROOT}/", "")

    print(Colors.success("🔗 Checking cross-boundary links (frontend/backend → docs)...\n"))

    # ── Scope 1: Frontend → docs ──────────────────────────────────────────
    print(f"{Colors.CYAN}── Scope 1: Frontend → MkDocs ──{Colors.NC}")

    discovery = docs_links.collect_frontend(frontend_src)

    for link in docs_links.deduplicate(discovery.links):
        origin = _rel(link.origin)
        file_path_str, _, anchor = link.path.partition("#")
        found_file = docs_links.find_page(docs_root, link.path)

        if not found_file:
            # A speculative path came from dropping an unknown interpolation, so
            # its absence proves nothing about the link — only about the guess.
            if not link.confident:
                speculative_misses.append(link)
                continue
            errors.append(f"  ❌ {link.path}\n     → File not found (from {origin})")
        elif anchor:
            failure = _mkdocs_check_anchor(found_file, anchor, link.path, origin, docs_root)
            if failure == "KNOWN":
                known_count += 1
            elif failure:
                errors.append(failure)
            else:
                ok_count += 1
                print(f"  ✅ {link.path}")
        else:
            ok_count += 1
            print(f"  ✅ {link.path}")

    # ── Scope 2: Backend-declared docs paths ──────────────────────────────
    # Every *_providers / *_plugins package, by glob. The two directories this
    # scope used to name by hand left signal_plugins and tool_plugins — nineteen
    # pages — unchecked, because a hand-written list only covers what someone
    # remembered to add.
    print(f"\n{Colors.CYAN}── Scope 2: Backend service plugins ──{Colors.NC}")

    backend_found = docs_links.collect_backend(PROJECT_ROOT / "backend" / "app" / "services")
    for link in docs_links.deduplicate(backend_found.links):
        origin = _rel(link.origin)
        _, _, anchor = link.path.partition("#")
        found_file = docs_links.find_page(docs_root, link.path)
        if not found_file:
            # A speculative path came from dropping an unknown interpolation, so
            # its absence proves nothing about the link — only about the guess.
            if not link.confident:
                speculative_misses.append(link)
                continue
            errors.append(f"  ❌ {link.path}\n     → File not found (from {origin})")
        elif anchor:
            failure = _mkdocs_check_anchor(found_file, anchor, link.path, origin, docs_root)
            if failure == "KNOWN":
                known_count += 1
            elif failure:
                errors.append(failure)
            else:
                ok_count += 1
                print(f"  ✅ {link.path}")
        else:
            ok_count += 1
            print(f"  ✅ {link.path}")

    # ── Declared unverifiable ─────────────────────────────────────────────
    # A value that genuinely depends on runtime state is not an error, but it is
    # not a pass either. It used to disappear from the output entirely, and an
    # empty error list read as "everything is fine".
    unverified = docs_links.deduplicate(
        discovery.unverified + backend_found.unverified + speculative_misses
    )
    if unverified:
        print(f"\n{Colors.CYAN}── Not verifiable ({len(unverified)}) ──{Colors.NC}")
        for link in unverified:
            print(f"  🔵 {link.path}  (from {_rel(link.origin)}) — resolved at runtime")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{Colors.CYAN}── Summary ──{Colors.NC}")
    print(f"  ✅ {ok_count} valid link(s)")
    if known_count:
        print(f"  🟡 {known_count} known-broken anchor(s) awaiting translation "
              f"(see MKDOCS_ANCHOR_EXCEPTIONS — this list must only shrink)")
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
# Graph / DevWiki Commands (graphify knowledge graph)
# =============================================================================

WIKI_DIR = PROJECT_ROOT / "LibreFolio_devWiki"
CORPUS_DIR = WIKI_DIR / "corpus"
GRAPH_JSON = WIKI_DIR / "graphify-out" / "graph.json"
GRAPH_REPORT = WIKI_DIR / "graphify-out" / "GRAPH_REPORT.md"


def _graphify_cmd(args_list: list, cwd: Path = WIKI_DIR, env: dict | None = None) -> int:
    """Run graphify via pipenv with live output from LibreFolio_devWiki/."""
    return run_pipenv(["python", "-m", "graphify"] + args_list, cwd=cwd, env=env)


def cmd_graph_build(args):
    """Full knowledge-graph build: extract + cluster + report.

    When graph.json already exists (default): code-only incremental update, no LLM needed.
    With --full: full semantic re-extraction (requires an LLM API key in env, or use the
    graphify skill through your AI assistant for semantic extraction of new doc files).
    """
    full = getattr(args, "full", False)

    if not CORPUS_DIR.exists():
        print_error(f"Corpus directory not found: {CORPUS_DIR}")
        print_error("Run from project root and ensure LibreFolio_devWiki/corpus/ exists.")
        return 1

    if GRAPH_JSON.exists() and not full:
        print_warning("graph.json exists — running incremental update (use --full for complete rebuild).")
        return _graphify_cmd(["update", "corpus/"])

    print(Colors.success("🔬 Building knowledge graph (full extract, no-viz)..."))
    print_warning("Semantic extraction uses cache for known files. New .md files need an LLM API key")
    print_warning("or run '/graphify corpus/' through your AI assistant for semantic extraction.")
    backend_args = []
    if getattr(args, "backend", None):
        backend_args = ["--backend", args.backend]
    return _graphify_cmd([
        "extract", "corpus/",
        *backend_args,
        "--no-viz",
        "--no-cluster",  # cluster separately; cluster-only is faster on 8k+ nodes
        "--out", ".",     # write to LibreFolio_devWiki/graphify-out/ (corpus/graphify-out symlinks here)
    ])


def cmd_graph_cluster(args):
    """Rerun clustering on existing graph.json and regenerate GRAPH_REPORT.md."""
    if not GRAPH_JSON.exists():
        print_error("No graph.json found. Run: ./dev.py graph build")
        return 1
    print(Colors.success("🔬 Reclustering graph..."))
    return _graphify_cmd(["cluster-only", "corpus/", "--no-viz"])


def cmd_graph_viz(args):
    """Generate graph.html from existing graph.json (raises node limit to 15000)."""
    if not GRAPH_JSON.exists():
        print_error("No graph.json found. Run: ./dev.py graph build first.")
        return 1
    print(Colors.success("🌐 Generating graph.html (node limit raised to 15000)..."))
    rc = _graphify_cmd(
        ["cluster-only", "corpus/"],
        env={"GRAPHIFY_VIZ_NODE_LIMIT": "15000"},
    )
    if rc == 0:
        print(Colors.success(f"✅ graph.html → {WIKI_DIR / 'graphify-out' / 'graph.html'}"))
    return rc


def cmd_graph_update(args):
    """Incremental code-only update: re-extract changed .py/.ts/.svelte (no LLM)."""
    if not GRAPH_JSON.exists():
        print_error("No graph.json found. Run: ./dev.py graph build first.")
        return 1
    print(Colors.success("🔄 Updating graph (code-only, no LLM)..."))
    return _graphify_cmd(["update", "corpus/"])


def cmd_graph_query(args):
    """BFS/DFS query on the knowledge graph."""
    if not GRAPH_JSON.exists():
        print_error("No graph.json found. Run: ./dev.py graph build first.")
        return 1
    question = " ".join(args.question)
    mode_flag = ["--dfs"] if getattr(args, "dfs", False) else []
    budget = ["--budget", str(args.budget)] if getattr(args, "budget", None) else []
    print(Colors.success(f"🔍 Querying: {question}"))
    return _graphify_cmd(["query", question] + mode_flag + budget)


def cmd_graph_path(args):
    """Shortest path between two concepts in the graph."""
    if not GRAPH_JSON.exists():
        print_error("No graph.json found. Run: ./dev.py graph build first.")
        return 1
    return _graphify_cmd(["path", args.node_a, args.node_b])


def cmd_graph_report(args):
    """Print GRAPH_REPORT.md summary to stdout."""
    if not GRAPH_REPORT.exists():
        print_error("No GRAPH_REPORT.md found. Run: ./dev.py graph build first.")
        return 1
    print(GRAPH_REPORT.read_text())
    return 0


# =============================================================================
# Docker Commands
# =============================================================================

def _get_docker_tag(override: str | None = None) -> str:
    """Get Docker image tag: the version the image reports, or the override.

    The same git-based versioning as `./dev.py info version`:
      - On a tag:       librefolio:v1.2.3
      - After commits:  librefolio:v1.2.3-5-gabcdef
      - Dirty tree:     librefolio:v1.2.3-dirty
      - No tags:        librefolio:v0.0.0-gabcdef

    Called after _docker_ensure_assets_built(), which froze the version before any build step and wrote it to
    VERSION: the tag reads that file, so the tag, VERSION and the frontend bundle name one version even when a build
    step wrote a tracked file meanwhile. Without the file, the version is computed afresh.
    """
    if override:
        return override

    version_file = PROJECT_ROOT / "VERSION"
    try:
        frozen = version_file.read_text().strip()
    except OSError:
        frozen = ""
    if frozen:
        return f"librefolio:{frozen}"

    from backend.app.utils.runtime.version import get_git_version

    get_git_version.cache_clear()
    return f"librefolio:{get_git_version()}"


def _check_env_file():
    """Check that .env exists; if not, abort with helpful instructions.

    Also warns when terminal environment variables override .env values
    for the Docker-relevant variable PORT (the host side of the port mapping).
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
    DOCKER_VARS = ("PORT",)
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


def _docker_frontend_stale_reason(version: str, check_frontend_needs_build) -> Optional[str]:
    """Why the frontend bundle cannot go into an image of ``version`` as it is, or None when it can.

    The image needs a production bundle of this version: the sources changed, the last build was a debug one (or
    of unknown mode), or it carries another version, e.g. after a commit that touched no frontend file.
    """
    if check_frontend_needs_build():
        return "missing or outdated"
    if _read_frontend_build_mode_marker() is not False:
        return "not a production build"
    recorded = _read_frontend_build_version()
    if recorded is None:
        return "made without a recorded version (not by docker build)"
    if recorded != version:
        return f"built for {recorded}, not {version}"
    return None


def _docker_ensure_frontend_built(version: str, check_frontend_needs_build) -> int:
    """Rebuild the frontend in production mode with ``LF_APP_VERSION=version`` unless the bundle already fits."""
    stale_reason = _docker_frontend_stale_reason(version, check_frontend_needs_build)
    if stale_reason is None:
        print(Colors.info(f"ℹ️  Frontend build is up to date ({version})"))
        return 0
    print_warning(f"Frontend build {stale_reason} — building now...")

    class BuildArgs:
        debug = False

    previous = os.environ.get("LF_APP_VERSION")
    os.environ["LF_APP_VERSION"] = version
    try:
        result = cmd_fe_build(BuildArgs())
    finally:
        if previous is None:
            os.environ.pop("LF_APP_VERSION", None)
        else:
            os.environ["LF_APP_VERSION"] = previous
    if result != 0:
        print_error("Frontend build failed. Cannot build Docker image.")
        return result
    _write_frontend_build_version(version)
    print_success(f"Frontend build ready ({version})")
    return 0


def _docker_ensure_assets_built():
    """Ensure frontend, docs, JS cache, requirements.txt and VERSION are ready before Docker build.

    Uses the same staleness checks as the 'server' command so that
    ``dev.py docker build`` always produces an image with fresh assets. The
    version is frozen once, first: the frontend bundle (as ``LF_APP_VERSION``)
    and the VERSION file carry the same one.
    """
    from backend.app.utils.runtime.version import get_git_version
    from scripts.cli_base import check_frontend_needs_build

    # --- 0. The image's version, frozen once ----------------------------------
    # Before any step can write a tracked file and make `git describe` say
    # "-dirty". get_git_version() reads VERSION only where there is no .git/ or
    # `git describe` fails: remove the file of a previous build first, so such a
    # checkout gets "unknown" instead of the old value.
    version_file = PROJECT_ROOT / "VERSION"
    version_file.unlink(missing_ok=True)
    get_git_version.cache_clear()
    version = get_git_version()

    # --- 1. JS library cache (fonts must exist before SvelteKit prerender) ----
    # No narrowing here on purpose: the image copies mkdocs_src/site/ next to
    # the frontend bundle, so it ships *both* consumers and every missing
    # resource is still fatal.
    cache_result = update_js_cache(strict=True)
    if cache_result != 0:
        print_error("Resource cache incomplete. Cannot build Docker image.")
        return cache_result

    # --- 2. Frontend ----------------------------------------------------------
    result = _docker_ensure_frontend_built(version, check_frontend_needs_build)
    if result != 0:
        return result

    # --- 3. MkDocs ------------------------------------------------------------
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
        result = subprocess.run(["pipenv", "requirements"], capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            print_error(f"Failed to generate requirements.txt: {result.stderr}")
            return 1
        req_file.write_text(result.stdout)
        print_success("requirements.txt generated")
    else:
        print(Colors.info("ℹ️  requirements.txt is up to date"))

    # --- 5. VERSION file for Docker (no .git/ in the runtime image) -----------
    # The image has no .git/, so get_git_version()'s `git describe` can't run at
    # container runtime: the version frozen at step 0 goes into a plain file
    # that gets COPYed into the image.
    version_file.write_text(version)
    print_success(f"VERSION file generated ({version})")

    return 0


def _docker_build_cmd(image_tag: str, no_cache: bool, light: bool) -> list:
    """Assemble the `docker build` command for the full or light variant.

    The light variant (build-arg DOCS_VARIANT=light) ships without the
    documentation images and is tagged with a `-light` suffix.
    """
    alias_tag = "librefolio:latest-light" if light else "librefolio:latest"
    docker_cmd = ["docker", "build", "-t", image_tag, "-t", alias_tag]
    # Pass host UID/GID so container user matches host user
    docker_cmd.extend(["--build-arg", f"UID={os.getuid()}", "--build-arg", f"GID={os.getgid()}"])
    if light:
        docker_cmd.extend(["--build-arg", "DOCS_VARIANT=light"])
    if no_cache:
        docker_cmd.append("--no-cache")
    docker_cmd.append(".")
    return docker_cmd


def cmd_docker_build(args):
    """Build the Docker image with git-based versioning."""
    if not _check_env_file():
        return 1
    tag_override = getattr(args, 'tag', None)
    no_cache = getattr(args, 'no_cache', False)
    light = getattr(args, 'light', False)

    result = _docker_ensure_assets_built()
    if result != 0:
        return result

    image_tag = _get_docker_tag(tag_override)
    if light and not tag_override:
        image_tag += "-light"
    variant = "light (no documentation images)" if light else "full"
    print(Colors.success(f"🐳 Building Docker image: {image_tag} [{variant}]..."))
    docker_cmd = _docker_build_cmd(image_tag, no_cache, light)
    result = run_command_live(docker_cmd)
    if result == 0:
        alias_tag = "librefolio:latest-light" if light else "librefolio:latest"
        print_success(f"✅ Image built: {image_tag} (also tagged {alias_tag})")
        if light:
            print(Colors.info("ℹ️  Light variant: documentation images load from the online"))
            print(Colors.info("   docs site — viewing them requires an internet connection."))
    return result


def cmd_docker_rebuild(args):
    """Rebuild image, stop running containers, restart with new version."""
    if not _check_env_file():
        return 1
    tag_override = getattr(args, 'tag', None)
    no_cache = getattr(args, 'no_cache', False)
    light = getattr(args, 'light', False)

    print(Colors.success("🐳 Rebuild: build new image → stop → start..."))
    print()

    # Step 1: Build new image
    result = _docker_ensure_assets_built()
    if result != 0:
        return result

    image_tag = _get_docker_tag(tag_override)
    if light and not tag_override:
        image_tag += "-light"
    print(Colors.info(f"[1/3] Building new image: {image_tag}..."))
    docker_cmd = _docker_build_cmd(image_tag, no_cache, light)
    result = run_command_live(docker_cmd)
    if result != 0:
        print_error("Build failed — containers NOT restarted.")
        return result
    print_success(f"Image built: {image_tag}")
    if light:
        # docker-compose.yml runs ${LIBREFOLIO_IMAGE:-librefolio:latest}
        print(Colors.info("ℹ️  Light variant built. To run it, set LIBREFOLIO_IMAGE=librefolio:latest-light in .env"))
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


def cmd_docker_restart(args):
    """Restart containers (down + up -d)."""
    print(Colors.success("🐳 Restarting LibreFolio containers..."))
    print(Colors.info("[1/2] Stopping containers..."))
    result = run_command_live(["docker", "compose", "down"])
    if result != 0:
        return result
    print()
    print(Colors.info("[2/2] Starting containers..."))
    result = run_command_live(["docker", "compose", "up", "-d"])
    if result == 0:
        print_success("✅ Containers restarted successfully")
    return result


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

    The image ships the application, not the development tree: `user`, `db` and
    `info` work; `test` answers "not available", and `server --test` cannot
    rebuild the frontend there. `db upgrade` refuses while the server runs, and
    the server applies the migrations itself at every start.

    Examples:
        ./dev.py docker exec user list
        ./dev.py docker exec user create admin admin@test.com Pass123!
        ./dev.py docker exec db current
    """
    extra = getattr(args, 'cmd_args', [])
    if not extra:
        print_error("No command specified. Usage: ./dev.py docker exec <command> [args...]")
        print(Colors.info("Examples:"))
        print(f"  ./dev.py docker exec user list")
        print(f"  ./dev.py docker exec user create admin admin@test.com Pass123!")
        print(f"  ./dev.py docker exec db current")
        return 1

    # As the server: gosu drops to the numeric ids the entrypoint uses (LIBREFOLIO_UID/GID, set in the image, with the
    # entrypoint's defaults), so a file a command creates in the data volume belongs to them, not to root. sh hands the
    # arguments on as "$@".
    cmd = ["docker", "compose", "exec", "librefolio", "sh", "-c", 'exec gosu "${LIBREFOLIO_UID:-1000}:${LIBREFOLIO_GID:-1000}" python dev.py "$@"', "sh", *extra]
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
    if getattr(args, "dead_code", False):
        return cmd_dead_code(args)
    cmd = ["ruff", "check", "backend/"]
    if getattr(args, "fix", False):
        cmd.append("--fix")
        if getattr(args, "unsafe", False):
            cmd.append("--unsafe-fixes")
    if getattr(args, "statistics", False):
        cmd.append("--statistics")
    print(Colors.success(f"Linting code with ruff {'(--fix) ' if getattr(args, 'fix', False) else ''}..."))
    return run_pipenv(cmd)


# Vulture categories worth acting on. Everything else ("variable", "attribute",
# "import") is dominated by Pydantic model fields and Enum members, which are
# consumed by value rather than by name and therefore always look unused.
DEAD_CODE_SIGNAL_TYPES = ("function", "method", "class", "property")

_VULTURE_LINE_RE = re.compile(r"^(?P<loc>.+?): unused (?P<kind>[a-z ]+) '(?P<name>[^']+)'")


def _parse_vulture(output: str):
    """Turn raw vulture output into (line, kind) pairs."""
    parsed = []
    for line in output.splitlines():
        m = _VULTURE_LINE_RE.match(line)
        if m:
            parsed.append((line, m.group("kind")))
    return parsed


def _run_vulture(paths, exclude):
    """Run vulture and return its raw stdout (exit code 3 == findings, not an error)."""
    cmd = ["vulture", *paths]
    if exclude:
        cmd += ["--exclude", ",".join(exclude)]
    code, out, err = run_command(pipenv_prefix() + cmd, cwd=PROJECT_ROOT)
    if code not in (0, 3):
        print_error(f"vulture failed (exit {code})")
        if err:
            print(err.strip())
        return None
    return out


def cmd_dead_code(args):
    """Find dead code: vulture on the backend, knip on the frontend."""
    print_header("Dead Code Analysis")
    print()

    show_all = getattr(args, "all", False)
    exclude = list(getattr(args, "exclude", None) or [])
    scope = getattr(args, "scope", "both")
    failed = False

    if scope in ("both", "backend"):
        print(Colors.info("[backend] Scanning backend/app with vulture..."))
        # Production consumers are not limited to backend/app: the ./dev.py CLI
        # (scripts/user_cli.py & co.) imports services directly. Scanning app in
        # isolation would flag every CLI-only service function as dead.
        prod_paths = ["backend/app", "scripts", "dev.py"]
        app_out = _run_vulture(prod_paths, exclude)
        if app_out is None:
            return 1

        findings = [(line, kind) for line, kind in _parse_vulture(app_out) if line.startswith("backend/app")]
        raw_total = len(findings)
        if not show_all:
            findings = [f for f in findings if f[1] in DEAD_CODE_SIGNAL_TYPES]

        # Differential pass: symbols that disappear from the report once the test
        # suite is in scope are referenced *only* by tests — i.e. code kept alive
        # artificially by its own tests.
        test_only = set()
        with_tests_out = _run_vulture([*prod_paths, "backend/test_scripts"], exclude)
        if with_tests_out is not None:
            still_dead = {line for line, _ in _parse_vulture(with_tests_out) if line.startswith("backend/app")}
            test_only = {line for line, _ in findings if line not in still_dead}

        truly_dead = [line for line, _ in findings if line not in test_only]

        print()
        if truly_dead:
            print(Colors.warning(f"  Unreferenced ({len(truly_dead)}):"))
            for line in truly_dead:
                print(f"    {line}")
        else:
            print_success("  No unreferenced symbols")

        print()
        if test_only:
            print(Colors.warning(f"  Referenced only by tests ({len(test_only)}):"))
            for line in sorted(test_only):
                print(f"    {line}")
        else:
            print_success("  No test-only symbols")

        if not show_all:
            hidden = raw_total - len(findings)
            if hidden:
                print()
                print(Colors.info(f"  {hidden} low-signal findings hidden (variables, attributes) — use --all to show"))
        failed = failed or bool(truly_dead) or bool(test_only)
        print()

    if scope in ("both", "frontend"):
        print(Colors.info("[frontend] Scanning with knip..."))
        frontend_dir = PROJECT_ROOT / "frontend"
        if not (frontend_dir / "node_modules" / "knip").exists():
            print_warning("  knip not installed — run './dev.py install' or 'npm install' in frontend/")
        else:
            failed = _run_knip_on_generated_catalogue(frontend_dir, exclude) or failed

    return 1 if failed else 0


# knip issue buckets, in report order, with the label shown to the user.
_KNIP_BUCKETS = [
    ("files", "Unused files"),
    ("exports", "Unused exports"),
    ("types", "Unused exported types"),
    ("enumMembers", "Unused enum members"),
    ("duplicates", "Duplicate exports"),
    ("dependencies", "Unused dependencies"),
    ("devDependencies", "Unused devDependencies"),
    ("unlisted", "Unlisted dependencies"),
    ("unresolved", "Unresolved imports"),
]


def _extract_json(text):
    """Pull the JSON blob out of noisy stdout (dotenv banners, svelte.config debug lines)."""
    import json

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('{"'):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                continue
    return None


def _run_knip_on_generated_catalogue(frontend_dir, exclude):
    """knip resolves the imports of the generated src/lib/i18n/<lang>.json: write them first, or it reports false findings."""
    if i18n_catalog.build(quiet=True) != 0:
        print_error("  translation catalogue could not be generated - knip skipped")
        return True
    return _run_knip(frontend_dir, exclude)


def _run_knip(frontend_dir, exclude):
    """Run knip via its JSON reporter so results can be path-filtered. Returns True on findings."""
    import fnmatch

    code, out, err = run_command(["npx", "knip", "--no-progress", "--reporter", "json"], cwd=frontend_dir)
    payload = _extract_json(out)
    if payload is None:
        print_error("  could not parse knip output")
        if err:
            print(err.strip()[:2000])
        return True
    issues = payload.get("issues", [])

    def skipped(path):
        return any(fnmatch.fnmatch(path, pat) for pat in exclude)

    buckets = {key: [] for key, _ in _KNIP_BUCKETS}
    hidden = 0
    for issue in issues:
        path = issue.get("file", "")
        for key, _ in _KNIP_BUCKETS:
            for item in issue.get(key) or []:
                name = item.get("name", "") if isinstance(item, dict) else str(item)
                # Dependency findings are reported against package.json, so the
                # exclude globs must be matched on the owning file instead.
                if skipped(path):
                    hidden += 1
                    continue
                buckets[key].append(f"{name}  ({path})" if key not in ("files",) else name)

    total = sum(len(v) for v in buckets.values())
    print()
    if total == 0:
        print_success("  No dead code found")
    for key, label in _KNIP_BUCKETS:
        items = buckets[key]
        if not items:
            continue
        print(Colors.warning(f"  {label} ({len(items)}):"))
        for item in sorted(items):
            print(f"    {item}")
        print()
    if hidden:
        print(Colors.info(f"  {hidden} findings hidden by --exclude"))
    return total > 0


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
    # `npm ci`, like the frontend below: it installs the lockfile as committed and never rewrites it.
    result = run_command_live(["npm", "ci"])
    if result != 0:
        print_error("Failed to install root npm dependencies")
        return result
    print_success("Root project tools installed")
    print()

    print(Colors.info("[3/4] Installing frontend dependencies..."))
    result = run_command_live(["npm", "ci"], cwd=PROJECT_ROOT / "frontend")
    if result != 0:
        print_error("Failed to install frontend dependencies")
        return result
    print_success("Frontend dependencies installed")
    print(Colors.info("[DEBUG] Git status after install:"))
    run_command_live(["git", "status", "--short"])
    print()

    print(Colors.info("[4/4] Installing Playwright browsers..."))
    print(Colors.warning("   (This will download Chromium, ~150MB)"))
    result = run_command_live(["npx", "playwright", "install", "chromium"], cwd=PROJECT_ROOT / "frontend")
    if result != 0:
        print_warning("Playwright browser installation had issues (non-critical)")
    else:
        print_success("Playwright browsers installed")
    print()

    print_header("✅ All dependencies installed!")
    
    # DIAGNOSTICS FOR GITHUB ACTIONS
    print()
    print(Colors.info("[DEBUG] Backend Package versions:"))
    run_command_live(["pipenv", "run", "pip", "list"])
    print(Colors.info("[DEBUG] Frontend Package versions:"))
    run_command_live(["npm", "ls", "svelte", "@sveltejs/kit", "@sveltejs/vite-plugin-svelte", "vite", "typescript", "esbuild"], cwd=PROJECT_ROOT / "frontend")
    
    return 0


# =============================================================================
# Helper Functions
# =============================================================================

FRONTEND_BUILD_MODE_MARKER = PROJECT_ROOT / "frontend" / "build" / ".build-debug"


def _write_frontend_build_mode_marker(debug: bool) -> None:
    """Record whether the last frontend build was made in debug mode (see auto_build_frontend)."""
    try:
        FRONTEND_BUILD_MODE_MARKER.write_text("1" if debug else "0")
    except OSError:
        pass  # non-critical bookkeeping — worst case, next run rebuilds unnecessarily


def _read_frontend_build_mode_marker() -> Optional[bool]:
    """Return whether the last build was a debug build, or None if unknown (e.g. never built)."""
    try:
        return FRONTEND_BUILD_MODE_MARKER.read_text().strip() == "1"
    except OSError:
        return None


#: The version the last frontend build for a Docker image carries (_docker_ensure_assets_built). Every build empties
#: frontend/build/, so the file exists only when the last build was made for an image.
FRONTEND_BUILD_VERSION_MARKER = PROJECT_ROOT / "frontend" / "build" / ".build-version"


def _write_frontend_build_version(version: str) -> None:
    """Record the version the frontend bundle was built with (LF_APP_VERSION), for the next image build."""
    try:
        FRONTEND_BUILD_VERSION_MARKER.write_text(version)
    except OSError:
        pass  # non-critical bookkeeping — worst case, the next image build rebuilds the frontend


def _read_frontend_build_version() -> Optional[str]:
    """Return the version the last image-bound frontend build carries, or None if unknown."""
    try:
        return FRONTEND_BUILD_VERSION_MARKER.read_text().strip() or None
    except OSError:
        return None


#: A string every Designer Lab runtime module contains: LAB_MARKER of frontend/scripts/designer-lab/vite-plugin.mjs.
DESIGNER_LAB_MARKER = b"lf-designer-lab"


def _frontend_build_has_designer_lab(build_dir: Path = PROJECT_ROOT / "frontend" / "build") -> bool:
    """Whether the frontend build carries the Designer Lab (/designer-lab): one of its scripts holds the Lab's marker.

    The debug-mode marker cannot tell, since a debug build made with LF_DESIGNER_LAB=0 has no Lab. The marker can: when
    the Lab is off, the Vite plugin fails the build if any emitted file contains it. Reads the scripts of
    _app/immutable/ up to the first hit: a few milliseconds on a debug build, a few tens when it reads them all.
    """
    try:
        scripts = sorted((build_dir / "_app" / "immutable").rglob("*.js"))
    except OSError:
        return False
    for script in scripts:
        try:
            if DESIGNER_LAB_MARKER in script.read_bytes():
                return True
        except OSError:
            continue
    return False


def auto_build_frontend(debug=False):
    """
    Auto-build frontend if needed.
    Uses shared logic from cli_base with dev.py's build function.

    Rebuilds when EITHER:
    - sources changed since the last build (check_frontend_needs_build), OR
    - the last build's debug-mode doesn't match what's being requested now
      (e.g. `./dev.py server --debug` after a plain `./dev.py front build` — the bundle would
      otherwise silently keep serving the old mode even though nothing is "stale").
    """
    from scripts.cli_base import check_frontend_needs_build

    last_debug = _read_frontend_build_mode_marker()
    mode_mismatch = last_debug != debug

    if not check_frontend_needs_build() and not mode_mismatch:
        print(Colors.info("ℹ️  Frontend build is up to date"))
        return None

    if mode_mismatch:
        last_label = "unknown" if last_debug is None else ("debug" if last_debug else "production")
        new_label = "debug" if debug else "production"
        print(Colors.info(f"📦 Frontend was last built in {last_label} mode, rebuilding in {new_label} mode..."))
    else:
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


#: Where dev.py records the source of each generated icon set and the recipe that drew it. The icons are
#: regenerated only when either changes: Pillow does not write the same PNG bytes on every platform, so
#: regenerating unchanged icons on another machine rewrote tracked files — on the release runner, enough for
#: `git describe --dirty` to mark the app's version. Delete an entry (or the file) to force a regeneration.
GENERATED_ICONS_RECORD = PROJECT_ROOT / "frontend" / "generated-icons.json"
#: Bump when generate_favicon() changes what it draws.
FAVICON_RECIPE = 1
#: Bump when generate_pwa_icons() changes what it draws.
PWA_ICONS_RECIPE = 1


def _icon_set_record(source: Path, recipe: int) -> dict:
    """What GENERATED_ICONS_RECORD holds for an icon set drawn from ``source`` by ``recipe``."""
    return {"recipe": recipe, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "source": source.relative_to(PROJECT_ROOT).as_posix()}


def _read_generated_icons_record() -> dict:
    try:
        record = json.loads(GENERATED_ICONS_RECORD.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return record if isinstance(record, dict) else {}


def _icon_set_up_to_date(key: str, source: Path, recipe: int, outputs: list[Path]) -> bool:
    """Every output exists, and the record names this source's bytes and this recipe."""
    return all(path.exists() for path in outputs) and _read_generated_icons_record().get(key) == _icon_set_record(source, recipe)


def _record_icon_set(key: str, source: Path, recipe: int) -> None:
    record = _read_generated_icons_record()
    record["_about"] = "Written by dev.py (generate_favicon, generate_pwa_icons): each icon set is regenerated only when its source's sha256 or its recipe changes."
    record[key] = _icon_set_record(source, recipe)
    GENERATED_ICONS_RECORD.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def generate_favicon():
    """Generate a square 48x48 favicon from logo.png (logo is non-square 765x944).

    Only when logo.png or FAVICON_RECIPE changed since the last generation (GENERATED_ICONS_RECORD).
    """
    src = PROJECT_ROOT / "frontend" / "static" / "logo.png"
    dst = PROJECT_ROOT / "frontend" / "static" / "favicon.png"
    if not src.exists():
        print_warning("logo.png not found, skipping favicon generation")
        return
    if _icon_set_up_to_date("favicon", src, FAVICON_RECIPE, [dst]):
        print(Colors.info("ℹ️  favicon.png is up to date (logo.png unchanged)"))
        return
    from PIL import Image

    img = Image.open(src)
    w, h = img.size
    size = max(w, h)
    square = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    square.paste(img, ((size - w) // 2, (size - h) // 2))
    square.resize((48, 48), Image.LANCZOS).save(dst)
    _record_icon_set("favicon", src, FAVICON_RECIPE)
    print_success(f"favicon.png generated (48×48 from {w}×{h} logo)")


def generate_pwa_icons():
    """Generate the PWA icons from logo_square.png.

    - icon-{192,512}.png (manifest "any"): the logo on white with ~12 % padding per side;
    - icon-maskable-{192,512}.png (manifest "maskable"): the logo on the splash beige (the
      manifest background_color), fitted so every logo pixel stays within 0.37 × size of the
      centre — the maskable safe zone is a circle of 0.40 × size;
    - apple-touch-icon.png (180×180): as "any", for iOS.

    Every icon is flattened to opaque RGB: Android's splash and iOS paint transparent pixels
    black. The logo is resized premultiplied (RGBa), so its transparent black pixels do not
    bleed a dark fringe into the edge, and composited with alpha_composite, which keeps the
    canvas opaque (paste with a mask blends the alpha channel too).

    Only when logo_square.png or PWA_ICONS_RECIPE changed since the last generation
    (GENERATED_ICONS_RECORD).
    """
    src = PROJECT_ROOT / "frontend" / "static" / "logo_square.png"
    icons_dir = PROJECT_ROOT / "frontend" / "static" / "icons"
    if not src.exists():
        print_warning("logo_square.png not found, skipping PWA icon generation")
        return
    outputs = [icons_dir / f"icon-{size}.png" for size in (192, 512)] + [icons_dir / f"icon-maskable-{size}.png" for size in (192, 512)] + [icons_dir / "apple-touch-icon.png"]
    if _icon_set_up_to_date("pwa-icons", src, PWA_ICONS_RECIPE, outputs):
        print(Colors.info("ℹ️  PWA icons are up to date (logo_square.png unchanged)"))
        return
    from PIL import Image

    icons_dir.mkdir(parents=True, exist_ok=True)
    logo = Image.open(src).convert("RGBA")
    w, h = logo.size
    white, beige = (255, 255, 255), (245, 244, 239)
    any_logo_ratio = 1 / 1.24
    maskable_reach = 0.37

    # Farthest logo pixel from the centre, as a fraction of the logo side.
    alpha = logo.getchannel("A").load()
    cx, cy = (w - 1) / 2, (h - 1) / 2
    logo_reach = max((((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for y in range(h) for x in range(w) if alpha[x, y]), default=0.0) / w or 0.5

    def compose(size, background, logo_side):
        resized = logo.convert("RGBa").resize((logo_side, logo_side), Image.LANCZOS).convert("RGBA")
        layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        offset = (size - logo_side) // 2
        layer.paste(resized, (offset, offset))
        canvas = Image.new("RGBA", (size, size), background + (255,))
        return Image.alpha_composite(canvas, layer).convert("RGB")

    for target_size in (192, 512):
        compose(target_size, white, round(target_size * any_logo_ratio)).save(icons_dir / f"icon-{target_size}.png", optimize=True)
        maskable_side = int(target_size * maskable_reach / logo_reach)
        compose(target_size, beige, maskable_side).save(icons_dir / f"icon-maskable-{target_size}.png", optimize=True)
    compose(180, white, round(180 * any_logo_ratio)).save(icons_dir / "apple-touch-icon.png", optimize=True)
    _record_icon_set("pwa-icons", src, PWA_ICONS_RECIPE)
    print_success(f"PWA icons generated (any 192/512, maskable 192/512, apple-touch 180 from {w}×{h} logo_square)")


def stamp_service_worker():
    """Stamp sw.js with a content hash of offline.html to auto-trigger SW updates."""
    sw_path = PROJECT_ROOT / "frontend" / "static" / "sw.js"
    offline_path = PROJECT_ROOT / "frontend" / "static" / "offline.html"
    if not sw_path.exists() or not offline_path.exists():
        return
    offline_hash = hashlib.md5(offline_path.read_bytes()).hexdigest()[:8]
    sw_content = sw_path.read_text()
    # Remove any existing hash comment
    lines = [l for l in sw_content.splitlines() if not l.startswith('// build:')]
    # Prepend hash comment (any byte change in sw.js triggers browser SW update)
    lines.insert(1, f'// build: {offline_hash}')
    stamped = '\n'.join(lines) + '\n'
    # Written only when it changes: the frontend build watches static/ (H-52), and a rewrite at every docs build
    # would leave sw.js newer than the build, for a needless rebuild at the next start
    if stamped != sw_content:
        sw_path.write_text(stamped)


def copy_docs_assets():
    """Copy logo, favicon, and icons to docs."""
    generate_favicon()
    generate_pwa_icons()
    stamp_service_worker()
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


def update_js_cache(strict: bool = False, required_for: str | None = None):
    """Update JS library cache.

    I1 (02/09): the script exits non-zero when a resource is missing AND has no
    usable cached copy. With ``strict=True`` (build paths) that failure is
    returned to the caller so a broken build stops instead of shipping; the
    dev-server path stays non-blocking (offline development with a warm cache
    must keep working).

    ``required_for`` narrows the failure to the resources the calling build
    actually ships. A frontend build has no reason to abort over MathJax, which
    only the documentation serves — and on a fresh worktree that abort happens
    before any test can start.
    """
    command = [*pipenv_prefix(), "python", "scripts/update_js_cache.py"]
    if required_for:
        command += ["--required-for", required_for]
    result = run_command_live(command, cwd=PROJECT_ROOT)
    if result == 0:
        print_success("JS libraries cached")
        return 0
    if strict:
        print_error("JS cache update failed — a required resource is missing and not cached")
        return result
    print_warning("JS cache update failed (will use CDN fallback)")
    return 0


# =============================================================================
# Command groups that need part of the development tree
# =============================================================================
# The Docker image ships the application, not the development tree: no
# backend/test_scripts, no frontend sources, no docs sources. A group is
# registered (and its modules imported) only when what it needs is there;
# otherwise it stays listed and says so. Checked before importing, never by
# catching ImportError: in a full checkout a broken import must stay loud.


def _has(*relative_paths: str) -> bool:
    """True when every path a command group needs is part of this installation."""
    return all((PROJECT_ROOT / path).exists() for path in relative_paths)


def _add_unavailable(subparsers, name: str, help_text: str, missing: str) -> None:
    """List a command this installation cannot run; running it says what is missing and exits 2."""
    # No option prefix: every word after the command, --help or --coverage too, lands in `rest`,
    # so any invocation gets the explanation instead of argparse's "unrecognized arguments".
    p = subparsers.add_parser(name, help=f"{help_text} — not available in this installation", add_help=False, prefix_chars="\x00")
    p.add_argument("rest", nargs=argparse.REMAINDER, metavar="...", help=argparse.SUPPRESS)

    def _explain(_args):
        print_error(f"'{name}' is not available in this installation: {missing} is not part of it (the Docker image ships the application, not the development tree).")
        return 2

    p.set_defaults(func=_explain)


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
      front               Frontend commands (dev, build, check, format, preview)

  🧪  Testing
      test                Run tests (api, db, external, schemas, services...)

  👤  Users
      user                User management (create, list, reset, promote...)

  💾  Backup
      backup              Instance backup (create, inspect, restore, pending)

  📚  Documentation
      mkdocs              MkDocs commands (build, serve, clean, deploy)

  📦  Tools
      api                 API schema commands (schema, client, sync)
      i18n                Translation commands (audit)
      cache               Cache management (js)
      info                Information commands (api)
      format              Format backend code with black
      lint                Lint backend code with ruff

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
    p.add_argument("--test", "-t", action="store_true", help="Use test database (port 6041)")
    p.add_argument("--rebuild", "-r", action="store_true", help="Force rebuild frontend before starting")
    p.add_argument("--build-only", action="store_true", dest="build_only",
                   help="Only build what the server serves (frontend, docs, JS cache), then exit without starting it")
    p.add_argument("--debug", "-d", action="store_true", help="Debug mode: verbose logging + frontend debug build")
    p.add_argument("--force", "-f", action="store_true", help="Kill blocking processes on port before starting")
    p.add_argument("--workers", "-w", metavar="N|auto", default=1, help="Number of uvicorn workers, or 'auto' for 2 × (CPU-1) (default: 1)")
    p.add_argument("--host", type=str, default=None, help="Bind host (default: HOST env or 0.0.0.0)")
    p.add_argument("--port", "-p", type=int, default=None, help="Bind port (default: PORT env or 6040)")
    p.add_argument("--data-dir", metavar="PATH", default=None,
                   help="Data root for this server (test mode uses LIBREFOLIO_TEST_DATA_DIR)")
    p.add_argument("--coverage", action="store_true", help="Enable backend code coverage tracking (writes .coverage.<pid>)")
    p.add_argument("--no-scheduler", action="store_true", dest="no_scheduler",
                   help="Disable the market data scheduler (no background sync jobs)")
    p.add_argument("--no-reload", action="store_true", dest="no_reload",
                   help="Never enable uvicorn --reload (the reloader adds a supervisor process that outlives SIGTERM)")
    p.add_argument("--lane-setting", dest="lane_settings", action="append", metavar="NAME=VALUE", default=None,
                   help="With --test: a setting of the lane's instance, repeatable (H-43): LIBREFOLIO_PROFILE, LIBREFOLIO_FRAME_PROTECTION or LIBREFOLIO_CSP_REPORT_ONLY")
    p.set_defaults(func=cmd_server)

    # Database
    p = subparsers.add_parser("db", help="🖥️  Database commands")
    db_sub = p.add_subparsers(dest="db_cmd", metavar="action")

    db_p = db_sub.add_parser("check", help="Verify CHECK constraints")
    db_p.add_argument("path", nargs="?", help="Database file (default: the configured one; a relative path starts at the project root)")
    db_p.set_defaults(func=cmd_db_check)

    db_p = db_sub.add_parser("currencies", help="List stored currency codes that are not ISO 4217 codes")
    db_p.add_argument("path", nargs="?", help="Database file (default: the configured one; a relative path starts at the project root)")
    db_p.set_defaults(func=cmd_db_currencies)

    db_p = db_sub.add_parser("current", help="Show current migration")
    db_p.add_argument("path", nargs="?", help="Database file (default: the configured one; a relative path starts at the project root)")
    db_p.set_defaults(func=cmd_db_current)

    db_p = db_sub.add_parser("migrate", help="Create new migration")
    db_p.add_argument("message", help="Migration message")
    db_p.add_argument("path", nargs="?", help="Database file (default: the configured one; a relative path starts at the project root)")
    db_p.set_defaults(func=cmd_db_migrate)

    db_p = db_sub.add_parser("upgrade", help="Apply pending migrations")
    db_p.add_argument("path", nargs="?", help="Database file (default: the configured one; a relative path starts at the project root); created when missing")
    db_p.set_defaults(func=cmd_db_upgrade)

    db_p = db_sub.add_parser("downgrade", help="Rollback one migration")
    db_p.add_argument("path", nargs="?", help="Database file (default: the configured one; a relative path starts at the project root)")
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

    fe_p = fe_sub.add_parser("format", help="Format code with Prettier")
    fe_p.add_argument("--check", action="store_true", help="Check only (no write)")
    fe_p.set_defaults(func=cmd_fe_format)

    fe_p = fe_sub.add_parser("preview", help="Preview production build")
    fe_p.set_defaults(func=cmd_fe_preview)

    # =========================================================================
    # 🧪 Testing Commands - Import from test_runner
    # =========================================================================

    has_test_runner = _has("backend/test_scripts")
    if has_test_runner:
        from scripts.test_runner import register_subparser as register_test_parser
        register_test_parser(subparsers)
    else:
        _add_unavailable(subparsers, "test", "🧪 Run tests", "backend/test_scripts")

    # =========================================================================
    # 👤 User Commands - Import from user_cli
    # =========================================================================

    from scripts.user_cli import register_subparser as register_user_parser
    register_user_parser(subparsers)

    # =========================================================================
    # 💾 Backup Commands - Import from backup_cli
    # =========================================================================

    from scripts.backup_cli import register_subparser as register_backup_parser
    register_backup_parser(subparsers)

    # =========================================================================
    # 📚 Documentation Commands
    # =========================================================================

    p = subparsers.add_parser("mkdocs", help="📚 MkDocs documentation commands")
    mk_sub = p.add_subparsers(dest="mk_cmd", metavar="action")

    mk_p = mk_sub.add_parser("build", help="Build documentation site")
    mk_p.set_defaults(func=cmd_mkdocs_build)

    mk_p = mk_sub.add_parser("serve", help="Serve documentation locally (port 6042)")
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
                      help="Reuse the existing test database as it is (faster re-runs; needs one earlier full run)")
    mk_p.add_argument("--workers", "-w", type=int, default=None,
                      help="Number of Playwright workers (default: 60%% of the CPU count, at least 1)")
    mk_p.add_argument("--test-port", type=int, default=None,
                      help="Port for the test server (default: TEST_PORT env or 6041)")
    mk_p.add_argument("--headed", action="store_true",
                      help="Run browser in headed mode (visible window) instead of headless")
    mk_p.add_argument("--ui", action="store_true",
                      help="Open Playwright UI mode (interactive test runner with time-travel debugger)")
    mk_p.add_argument("--force", action="store_true",
                      help="Kill zombie processes blocking the test port instead of failing")
    mk_p.set_defaults(func=cmd_mkdocs_gallery)

    mk_p = mk_sub.add_parser("normalize-dashboard-fixture", help="Rescale the gallery dashboard snapshot to a 50K net worth (anonymization)")
    mk_p.add_argument("path", nargs="?", default="frontend/e2e/dashboard-report.json",
                      help="Fixture path (default: the gallery dashboard snapshot)")
    mk_p.add_argument("--dry-run", action="store_true",
                      help="Report what would change without writing")
    mk_p.set_defaults(func=cmd_mkdocs_normalize_dashboard_fixture)

    mk_p = mk_sub.add_parser("check-links", help="Validate cross-boundary links (frontend/backend → docs)")
    mk_p.set_defaults(func=cmd_mkdocs_check_links)

    # Translate - Import from mkdocs_src/aphra-pipeline/translate_docs.py
    # (not part of the Docker image: aphra-pipeline is excluded from it)
    if _has("mkdocs_src/aphra-pipeline"):
        sys.path.insert(0, str(PROJECT_ROOT / "mkdocs_src" / "aphra-pipeline"))
        from translate_docs import register_subparser as register_translate_parser
        register_translate_parser(mk_sub)

        # Translate-validate - structural validation of translated files
        from validate_translations import register_subparser as register_validate_parser
        register_validate_parser(mk_sub)
    else:
        _add_unavailable(mk_sub, "translate", "Translate the documentation (Aphra pipeline)", "mkdocs_src/aphra-pipeline")
        _add_unavailable(mk_sub, "translate-validate", "Validate the translated documentation", "mkdocs_src/aphra-pipeline")

    # =========================================================================
    # 📦 Tools Commands Group
    # =========================================================================

    # API
    p = subparsers.add_parser("api", help="📦 API schema commands")
    api_sub = p.add_subparsers(dest="api_cmd", metavar="action")

    api_p = api_sub.add_parser("schema", help="Export OpenAPI schema")
    api_p.add_argument("--tools-only", action="store_true", help="Export only Tool schemas without importing the API application")
    api_p.set_defaults(func=cmd_api_schema)

    api_p = api_sub.add_parser("client", help="Generate TypeScript client")
    api_p.add_argument("--tools-only", action="store_true", help="Generate only Tool codecs from their exported schema")
    api_p.set_defaults(func=cmd_api_client)

    api_p = api_sub.add_parser("sync", help="Export schema + generate client")
    api_p.add_argument("--tools-only", action="store_true", help="Sync only Tool contracts without importing the API application")
    api_p.set_defaults(func=cmd_api_sync)

    # i18n - Import from frontend/scripts/i18n-audit.py
    # (not part of the Docker image: frontend/scripts is excluded from it)
    if _has("frontend/scripts/i18n-audit.py"):
        sys.path.insert(0, str(PROJECT_ROOT / "frontend" / "scripts"))
        from importlib import import_module
        i18n_module = import_module("i18n-audit")
        i18n_module.register_subparser(subparsers)
    else:
        _add_unavailable(subparsers, "i18n", "📦 Translation commands", "frontend/scripts")

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
    docker_p.add_argument("--light", action="store_true", help="Light variant: no documentation images (tagged *-light); doc images load from the online docs site")
    docker_p.set_defaults(func=cmd_docker_build)

    docker_p = docker_sub.add_parser("rebuild", help="Build new image → stop containers → restart with new version")
    docker_p.add_argument("--tag", "-t", default=None, help="Override image tag (default: librefolio:<git-version>)")
    docker_p.add_argument("--no-cache", action="store_true", help="Build without Docker cache")
    docker_p.add_argument("--light", action="store_true", help="Light variant: no documentation images (tagged *-light); doc images load from the online docs site")
    docker_p.set_defaults(func=cmd_docker_rebuild)

    docker_p = docker_sub.add_parser("up", help="Start containers (docker compose up)")
    docker_p.add_argument("--no-detach", action="store_true", help="Run in foreground")
    docker_p.set_defaults(func=cmd_docker_up)

    docker_p = docker_sub.add_parser("down", help="Stop containers (docker compose down)")
    docker_p.set_defaults(func=cmd_docker_down)

    docker_p = docker_sub.add_parser("restart", help="Restart containers (down + up -d)")
    docker_p.set_defaults(func=cmd_docker_restart)

    docker_p = docker_sub.add_parser("logs", help="Show container logs")
    docker_p.add_argument("-f", "--follow", action="store_true", help="Follow log output")
    docker_p.set_defaults(func=cmd_docker_logs)

    docker_p = docker_sub.add_parser("status", help="Show container status")
    docker_p.set_defaults(func=cmd_docker_status)

    docker_p = docker_sub.add_parser("exec", help="Run a dev.py command inside the container")
    docker_p.add_argument("cmd_args", nargs=argparse.REMAINDER, help="Command and arguments (e.g. user list)")
    docker_p.set_defaults(func=cmd_docker_exec)

    # Format & Lint
    p = subparsers.add_parser("format", help="📦 Format code with black")
    p.set_defaults(func=cmd_format)

    p = subparsers.add_parser("lint", help="📦 Lint code with ruff")
    p.add_argument("--fix", action="store_true", help="Auto-fix safe issues")
    p.add_argument("--unsafe", action="store_true", help="Include unsafe fixes (use with --fix)")
    p.add_argument("--statistics", action="store_true", help="Show error statistics")
    p.add_argument("--dead-code", action="store_true", help="Find dead code (vulture + knip) instead of linting")
    p.add_argument("--all", action="store_true", help="With --dead-code: include low-signal findings (variables, attributes)")
    p.add_argument("--scope", choices=["both", "backend", "frontend"], default="both", help="With --dead-code: which side to scan (default: both)")
    p.add_argument("--exclude", action="append", metavar="GLOB", help="With --dead-code: extra path globs to skip (repeatable)")
    p.set_defaults(func=cmd_lint)

    # =========================================================================
    # 🔧 Setup Commands Group
    # =========================================================================

    p = subparsers.add_parser("shell", help="🔧 Open pipenv shell")
    p.set_defaults(func=cmd_shell)

    p = subparsers.add_parser("install", help="🔧 Install all dependencies")
    p.set_defaults(func=cmd_install)

    # =========================================================================
    # 🔬 Graph / DevWiki Commands (graphify knowledge graph)
    # =========================================================================

    p = subparsers.add_parser("graph", help="🔬 DevWiki knowledge graph (graphify)")
    graph_sub = p.add_subparsers(dest="graph_cmd", metavar="action")

    gp = graph_sub.add_parser("build", help="Full extraction (--full) or incremental code update")
    gp.add_argument("--backend", default=None,
                    choices=["claude", "openai", "kimi", "deepseek", "ollama", "gemini"],
                    help="LLM backend for semantic extraction of new docs (optional; uses env var auto-detect if not set)")
    gp.add_argument("--full", action="store_true",
                    help="Force full rebuild even if graph.json already exists")
    gp.set_defaults(func=cmd_graph_build)

    gp = graph_sub.add_parser("cluster", help="Rerun clustering on existing graph.json")
    gp.set_defaults(func=cmd_graph_cluster)

    gp = graph_sub.add_parser("viz", help="Generate graph.html (raises node limit to 15000)")
    gp.set_defaults(func=cmd_graph_viz)

    gp = graph_sub.add_parser("update", help="Code-only incremental update (no LLM, fast)")
    gp.set_defaults(func=cmd_graph_update)

    gp = graph_sub.add_parser("query", help='BFS query: ./dev.py graph query "how does auth work"')
    gp.add_argument("question", nargs="+", help="Question to ask the graph")
    gp.add_argument("--dfs", action="store_true", help="Use DFS instead of BFS")
    gp.add_argument("--budget", type=int, default=None, help="Token budget for answer (default: 2000)")
    gp.set_defaults(func=cmd_graph_query)

    gp = graph_sub.add_parser("path", help='Shortest path: ./dev.py graph path "Currency" "Transaction"')
    gp.add_argument("node_a", help="Start concept")
    gp.add_argument("node_b", help="End concept")
    gp.set_defaults(func=cmd_graph_path)

    gp = graph_sub.add_parser("report", help="Print GRAPH_REPORT.md to stdout")
    gp.set_defaults(func=cmd_graph_report)

    def _graph_help(a):
        p.print_help()
        return 0
    p.set_defaults(func=_graph_help)

    # =========================================================================
    # Enable autocompletion and parse
    # =========================================================================

    if HAS_ARGCOMPLETE:
        argcomplete.autocomplete(parser)

    argv = sys.argv[1:]
    if has_test_runner:
        from scripts.test_runner._cli import normalize_coverage_argv
        argv = normalize_coverage_argv(argv, only_command="test")

    args = parser.parse_args(argv)

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
