#!/usr/bin/env python3
"""
CLI Base Utilities for LibreFolio development scripts.

Provides shared utilities for all CLI modules:
- Terminal colors
- Project paths
- Database utilities
- Server check utilities
- Command execution helpers
"""

import contextlib
import hashlib
import os
import re
import secrets
import signal
import socket
import subprocess
import threading
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Optional, Tuple

from scripts.i18n_catalog import generated_catalogs, plugin_i18n_dirs

# =============================================================================
# Terminal Colors
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

    @classmethod
    def success(cls, msg: str) -> str:
        return f"{cls.GREEN}{msg}{cls.NC}"

    @classmethod
    def warning(cls, msg: str) -> str:
        return f"{cls.YELLOW}{msg}{cls.NC}"

    @classmethod
    def error(cls, msg: str) -> str:
        return f"{cls.RED}{msg}{cls.NC}"

    @classmethod
    def info(cls, msg: str) -> str:
        return f"{cls.BLUE}{msg}{cls.NC}"

    @classmethod
    def bold(cls, msg: str) -> str:
        return f"{cls.BOLD}{msg}{cls.NC}"


# =============================================================================
# Project Paths
# =============================================================================

def get_project_root() -> Path:
    """Get the project root directory."""
    # This file is in scripts/, so parent is project root
    return Path(__file__).parent.parent.resolve()


def get_scripts_dir() -> Path:
    """Get the scripts directory."""
    return Path(__file__).parent.resolve()


# =============================================================================
# Port Configuration
# =============================================================================

def get_server_host() -> str:
    """Get server host from environment variable (default: 0.0.0.0)."""
    return os.environ.get("HOST", "0.0.0.0")


def get_server_port() -> int:
    """Get server port from environment variable (default: 6040)."""
    return int(_configured_env_value("PORT") or "6040")


def get_test_server_port() -> int:
    """Get test server port from environment variable (default: 6041)."""
    return int(_configured_env_value("TEST_PORT") or "6041")


# =============================================================================
# Database Configuration
# =============================================================================

# Default data directories (relative to project root)
DEFAULT_PROD_DATA_DIR = "backend/data/prod"
DEFAULT_TEST_DATA_DIR = "backend/data/test"


def _project_dotenv_values() -> dict[str, str]:
    """Read repository .env values without making dotenv a bootstrap dependency."""
    if os.environ.get("PIPENV_DONT_LOAD_ENV", "").lower() in {"1", "true", "yes", "on"}:
        return {}
    configured_path = os.environ.get("PIPENV_DOTENV_LOCATION")
    env_file = Path(configured_path).expanduser() if configured_path else get_project_root() / ".env"
    if not env_file.is_absolute():
        env_file = get_project_root() / env_file
    if not env_file.exists():
        return {}
    try:
        from dotenv import dotenv_values  # noqa: PLC0415 — optional outside the managed environment

        return {
            key: str(value)
            for key, value in dotenv_values(env_file).items()
            if value is not None
        }
    except ImportError:
        pass

    values: dict[str, str] = {}
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.removeprefix("export ").strip()] = value.strip().strip('"').strip("'")
    return values


def _dotenv_value(name: str) -> str | None:
    return _project_dotenv_values().get(name)


def _configured_env_value(name: str) -> str | None:
    """Return shell environment first, then the repository .env value."""
    if name in os.environ:
        return os.environ[name]
    return _dotenv_value(name)


def _load_project_dotenv() -> None:
    """Hydrate the parent once so nested Pipenv commands need not reload .env."""
    for name, value in _project_dotenv_values().items():
        os.environ.setdefault(name, value)


#: What a test lane keeps of the developer's configuration (.env or shell): its port and the production one it must stay
#: away from, the production data directory, the bind address, the log level, the version a release job froze for its
#: gallery, and the server workers of Playwright's webServer. Every LIBREFOLIO_TEST_* name is kept too: the runner's
#: and the tests' own (data directory, mode, lane id, startup timeout…). Every other setting of the instance
#: (secrets, profile, block, mail, accounts, plugins…) takes its default in a lane: configure_test_runtime drops it.
TEST_LANE_KEEPS = frozenset({"PORT", "TEST_PORT", "LIBREFOLIO_DATA_DIR", "HOST", "LOG_LEVEL", "LIBREFOLIO_LOG_LEVEL", "LF_APP_VERSION", "LIBREFOLIO_SERVER_WORKERS"})
TEST_LANE_KEPT_PREFIX = "LIBREFOLIO_TEST_"
#: What a test lane may set of its instance's configuration, with ``--lane-setting NAME=VALUE`` (H-43): the settings a
#: hosting provider's instance runs with, so the suite can see the managed profile, its frame protection and its
#: report-only content security policy for real. Never a secret, a port, a data directory or one of the runner's names.
TEST_LANE_SETTABLE = frozenset({"LIBREFOLIO_PROFILE", "LIBREFOLIO_FRAME_PROTECTION", "LIBREFOLIO_CSP_REPORT_ONLY"})
#: The variable that carries a lane's settings down its process tree — the runner, Playwright, ``dev.py server --test``
#: and uvicorn's workers —, as ``NAME=VALUE`` pairs joined by ``;``. Under the kept prefix, so each nested
#: ``configure_test_runtime()`` finds it and applies it again after its own drop. Set by the runner, never by .env.
TEST_LANE_SETTINGS = "LIBREFOLIO_TEST_LANE_SETTINGS"
# A variable line of .env.example, commented out or not: «NAME=…» or «# NAME=…».
_ENV_EXAMPLE_VARIABLE = re.compile(r"^(?:#\s*)?([A-Z_][A-Z0-9_]*)=")


def kept_in_a_test_lane(name: str) -> bool:
    """Whether a test lane keeps ``name`` from the developer's configuration: ``TEST_LANE_KEEPS`` or ``LIBREFOLIO_TEST_*``."""
    return name in TEST_LANE_KEEPS or name.startswith(TEST_LANE_KEPT_PREFIX)


def parse_lane_settings(items: Iterable[str]) -> dict[str, str]:
    """The lane settings ``items`` give, ``NAME=VALUE`` each, checked (H-43): a name of ``TEST_LANE_SETTABLE``, given
    once, with a value that is not empty and holds no ``;`` nor a line break. ``ValueError`` otherwise, naming the item."""
    allowed = ", ".join(sorted(TEST_LANE_SETTABLE))
    settings: dict[str, str] = {}
    for item in items:
        name, separator, value = item.partition("=")
        name, value = name.strip(), value.strip()
        if not separator or not name or not value:
            raise ValueError(f"Lane setting {item!r} is not NAME=VALUE")
        if name not in TEST_LANE_SETTABLE:
            raise ValueError(f"Lane setting {item!r}: a test lane may set only {allowed}")
        if any(character in value for character in (";", "\n", "\r", "\0")):
            raise ValueError(f"Lane setting {item!r}: its value may hold no ';' and no line break")
        if name in settings:
            raise ValueError(f"Lane setting {name} is given twice")
        settings[name] = value
    return settings


def documented_instance_variables() -> frozenset[str]:
    """Every variable ``.env.example`` documents, commented out or not: the configuration of an instance.

    Empty when the file cannot be read (the Docker image ships it as ``.env``, and runs no test lane).
    """
    try:
        lines = (get_project_root() / ".env.example").read_text(encoding="utf-8").splitlines()
    except OSError:
        return frozenset()
    return frozenset(match.group(1) for line in lines if (match := _ENV_EXAMPLE_VARIABLE.match(line)))


def _test_lane_drops() -> set[str]:
    """The names configure_test_runtime removes, whatever their origin (.env or shell): every documented variable, the
    instance's secrets and every ``LIBREFOLIO_*`` name in the environment, but those ``kept_in_a_test_lane``."""
    from backend.app.config import INSTANCE_TRUST_SECRETS  # noqa: PLC0415 — keep bootstrap-only CLI commands stdlib-only

    names = documented_instance_variables() | set(INSTANCE_TRUST_SECRETS) | {name for name in os.environ if name.startswith("LIBREFOLIO_")}
    return {name for name in names if not kept_in_a_test_lane(name)}


def resolve_data_dir(value: str | os.PathLike[str]) -> Path:
    """Resolve a configured data directory relative to the project root."""
    raw = os.fspath(value).strip()
    if not raw:
        raise ValueError("Data directory cannot be empty")
    if "?" in raw or "#" in raw:
        raise ValueError("Data directory cannot contain '?' or '#'")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = get_project_root() / path
    path = path.resolve()
    if "?" in str(path) or "#" in str(path):
        raise ValueError("Resolved data directory cannot contain '?' or '#'")
    return path


def _validated_port(value: int | str, option: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{option} must be an integer between 1 and 65535")
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{option} must be an integer between 1 and 65535"
        ) from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"{option} must be between 1 and 65535")
    return port


def ensure_test_lane_id() -> str:
    """Return one opaque readiness identity shared by a test process tree."""
    lane_id = os.environ.get("LIBREFOLIO_TEST_LANE_ID")
    if not lane_id:
        lane_id = secrets.token_hex(16)
        os.environ["LIBREFOLIO_TEST_LANE_ID"] = lane_id
    return lane_id


def get_data_dir(test_mode: bool = False) -> Path:
    """
    Get the data directory based on mode.

    Args:
        test_mode: If True, return test data directory

    Returns:
        Path to data directory
    """
    if test_mode:
        configured = _configured_env_value("LIBREFOLIO_TEST_DATA_DIR")
        candidate = resolve_data_dir(configured or DEFAULT_TEST_DATA_DIR)
        from backend.app.config import validate_test_data_dir  # noqa: PLC0415 — keep bootstrap-only CLI commands stdlib-only

        return validate_test_data_dir(
            candidate,
            production_data_dir=get_data_dir(test_mode=False),
        )

    # Check for custom data dir in env (only for prod mode)
    env_data_dir = _configured_env_value("LIBREFOLIO_DATA_DIR")
    if env_data_dir:
        return resolve_data_dir(env_data_dir)

    return resolve_data_dir(DEFAULT_PROD_DATA_DIR)


def configure_test_runtime(
    port: int | str | None = None,
    data_dir: str | os.PathLike[str] | None = None,
    lane_settings: Iterable[str] | None = None,
) -> tuple[int, Path]:
    """Validate and apply one test lane's port and data directory.

    Explicit values are exported for every child process. Omitted values keep
    their effective value while normalizing it for every child process.

    ``lane_settings`` (``--lane-setting``, H-43) are applied after the drop of the
    developer's settings and handed down in ``TEST_LANE_SETTINGS``; without them,
    the settings that variable carries from the parent are applied again. That
    variable is refused when it comes from .env.
    """
    raw_port = port if port is not None else (_configured_env_value("TEST_PORT") or "6041")
    resolved_port = _validated_port(raw_port, "--test-port")
    production_port = _validated_port(
        _configured_env_value("PORT") or "6040",
        "PORT",
    )
    if resolved_port == production_port:
        raise ValueError(
            "Test port must not be the production server port"
        )

    raw_data_dir = data_dir
    if raw_data_dir is None:
        raw_data_dir = _configured_env_value("LIBREFOLIO_TEST_DATA_DIR") or DEFAULT_TEST_DATA_DIR
    resolved_data_dir = resolve_data_dir(raw_data_dir)

    from backend.app.config import validate_test_data_dir  # noqa: PLC0415 — keep bootstrap-only CLI commands stdlib-only

    resolved_data_dir = validate_test_data_dir(
        resolved_data_dir,
        production_data_dir=get_data_dir(test_mode=False),
    )

    # A test lane runs on the instance's defaults: no setting of the developer's .env or shell reaches it, only what
    # kept_in_a_test_lane() keeps, the lane's own settings (H-43) and what the runner sets below. Other keys of .env
    # (not LibreFolio's) stay.
    # Refused whenever the dotenv file holds it, whatever the environment says: `pipenv run` exports .env before dev.py
    # starts, so a line there would look inherited. A runner's children never read .env (PIPENV_DONT_LOAD_ENV, set below).
    if TEST_LANE_SETTINGS in _project_dotenv_values():
        raise ValueError(f"{TEST_LANE_SETTINGS} comes from .env: a test lane's settings come from --lane-setting only")
    inherited_settings = os.environ.get(TEST_LANE_SETTINGS)
    settings = parse_lane_settings(lane_settings if lane_settings is not None else [item for item in (inherited_settings or "").split(";") if item.strip()])
    _load_project_dotenv()
    for name in _test_lane_drops():
        os.environ.pop(name, None)
    if settings:
        os.environ[TEST_LANE_SETTINGS] = ";".join(f"{name}={value}" for name, value in sorted(settings.items()))
    else:
        os.environ.pop(TEST_LANE_SETTINGS, None)
    os.environ.update(settings)
    os.environ["TEST_PORT"] = str(resolved_port)
    os.environ["LIBREFOLIO_TEST_DATA_DIR"] = str(resolved_data_dir)
    ensure_test_lane_id()
    os.environ["LIBREFOLIO_TEST_MODE"] = "1"
    os.environ["PIPENV_DONT_LOAD_ENV"] = "1"

    return resolved_port, resolved_data_dir


def configure_server_runtime(
    port: int | str | None = None,
    data_dir: str | os.PathLike[str] | None = None,
) -> tuple[int, Path]:
    """Normalize and export one production/debug server runtime."""
    raw_port = port if port is not None else (_configured_env_value("PORT") or "6040")
    resolved_port = _validated_port(raw_port, "--port")

    configured_data_dir = data_dir
    if configured_data_dir is None:
        configured_data_dir = _configured_env_value("LIBREFOLIO_DATA_DIR") or DEFAULT_PROD_DATA_DIR
    resolved_data_dir = resolve_data_dir(configured_data_dir)

    _load_project_dotenv()
    os.environ["PORT"] = str(resolved_port)
    os.environ["LIBREFOLIO_DATA_DIR"] = str(resolved_data_dir)
    os.environ.pop("LIBREFOLIO_TEST_LANE_ID", None)
    os.environ["LIBREFOLIO_TEST_MODE"] = "0"
    os.environ["PIPENV_DONT_LOAD_ENV"] = "1"
    return resolved_port, resolved_data_dir


def get_database_path(test_mode: bool = False) -> str:
    """
    Get database path based on mode.

    Args:
        test_mode: If True, return test database path

    Returns:
        Relative path to database file
    """
    data_dir = get_data_dir(test_mode)
    return str(data_dir / "sqlite" / "app.db")


def get_test_database_path() -> str:
    """Get test database path (convenience wrapper)."""
    return get_database_path(test_mode=True)


def get_server_port_for_db(db_path: str) -> int:
    """Pick the port whose server would actually hold a lock on `db_path`.

    SQLite locks are per-file: the PROD server (port 6040) only ever opens the
    PROD db file, and the TEST server (port 6041) only ever opens the TEST db
    file. Resolves both to absolute paths so callers can pass any spelling
    (relative, absolute, from --path or --test) of the target db.
    """
    resolved = (get_project_root() / db_path).resolve()
    test_resolved = (get_project_root() / get_test_database_path()).resolve()
    return get_test_server_port() if resolved == test_resolved else get_server_port()


def path_to_url(db_path: str) -> str:
    """Convert SQLite file path to database URL."""
    if not db_path:
        return ""

    # Convert relative path to absolute if needed
    path = Path(db_path)
    if not path.is_absolute():
        path = get_project_root() / path

    return f"sqlite:///{path}"


# =============================================================================
# Server Utilities
# =============================================================================

def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def check_server_running(action: str = "this operation", strict: bool = True, port: int | None = None) -> bool:
    """
    Check if a server is running on the relevant port for this DB operation.

    Args:
        action: Description of the action being performed
        strict: If True, exit on conflict. If False, warn and ask.
        port: Port to check. Defaults to the PROD server port — pass the TEST
            server port explicitly when the operation targets the test database
            (SQLite locks are per-file, so only the server actually holding that
            file matters, not whichever server happens to be running).

    Returns:
        True if can continue, False if should abort
    """
    port = port if port is not None else get_server_port()

    if not is_port_in_use(port):
        return True

    # Port is in use
    if strict:
        print(Colors.warning(f"⚠️  Important: {action} should be run with the server OFFLINE"))
        print(Colors.warning("   Running while server is active can cause database locks."))
        print()
        print(Colors.error(f"❌ Server is currently running on port {port}"))
        print()
        print(Colors.warning(f"Please stop the server before {action}:"))
        print("  1. Stop the server (Ctrl+C in server terminal)")
        print(f"  2. Or kill the process: {Colors.success(f'lsof -ti:{port} | xargs kill -9')}")
        print()
        return False
    else:
        print(Colors.warning(f"⚠️  Warning: Server is running on port {port}"))
        print(Colors.warning(f"   {action} while server is active may cause issues."))
        print()
        response = input("Continue anyway? (y/N) ").strip().lower()
        return response == 'y'


# =============================================================================
# Command Execution
# =============================================================================

def run_command(cmd: list, cwd: Optional[Path] = None, env: Optional[dict] = None) -> Tuple[int, str, str]:
    """
    Run a command and return (exit_code, stdout, stderr).

    Args:
        cmd: Command as list of strings
        cwd: Working directory
        env: Environment variables to add

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or get_project_root(),
            env=full_env,
            capture_output=True,
            text=True
            )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def run_command_live(cmd: list, cwd: Optional[Path] = None, env: Optional[dict] = None) -> int:
    """
    Run a command with live output (stdout/stderr to terminal).

    Args:
        cmd: Command as list of strings
        cwd: Working directory
        env: Environment variables to add

    Returns:
        Exit code
    """
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or get_project_root(),
            env=full_env
            )
        return result.returncode
    except KeyboardInterrupt:
        print("\n" + Colors.warning("Interrupted"))
        return 130
    except Exception as e:
        print(Colors.error(f"Error: {e}"))
        return 1


def run_server_live(cmd: list, env: Optional[dict] = None, grace_seconds: Optional[float] = None) -> int:
    """
    Run the server with live output, and let it finish its own shutdown when it is asked to stop (Z-10).

    - Ctrl+C: the terminal sends SIGINT to the whole foreground group, so the server already has it. Nothing is
      forwarded (a second SIGINT makes uvicorn force its exit): this waits for the server, up to ``grace_seconds``.
      ``subprocess.run``, as in ``run_command_live``, would kill it 0.25 s later, in the middle of its shutdown.
    - SIGTERM to this process: forwarded to the server, since a process supervisor may signal this process alone,
      then the same wait. A server that also got it from its group gets it twice, and stops once.
    - A second Ctrl+C or SIGTERM, or the grace running out: the server is killed.

    The handlers record the signals instead of raising: an exception raised inside ``Popen.poll()``, between its lock
    and its ``try``, would leave the lock taken, and every later poll would answer that the server still runs.

    Args:
        cmd: Command as list of strings
        env: Environment variables to add
        grace_seconds: How long to wait for the server once it is asked to stop; None for no limit

    Returns:
        The server's exit code; 130 after a Ctrl+C, 143 after a SIGTERM; 1 when it cannot start
    """
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    received: list[str] = []
    replaced = _record_stop_signals(received)
    try:
        try:
            process = subprocess.Popen(cmd, cwd=get_project_root(), env=full_env)
        except Exception as e:
            print(Colors.error(f"Error: {e}"))
            return 1
        return _supervise_server(process, grace_seconds, received, early=len(received))
    finally:
        for signum, handler in replaced.items():
            signal.signal(signum, handler)


def _record_stop_signals(received: list) -> dict:
    """Append ``interrupt`` (Ctrl+C) or ``terminate`` (SIGTERM) to ``received`` when they arrive, instead of their usual effect.

    Only a signal with its usual handler (``default_int_handler``, ``SIG_DFL``) is taken: one the launcher ignores or
    handles stays as it was. Only from the main thread, the one where handlers can be set. Returns the handlers it
    replaced, by signal, for the caller to put back.
    """
    if threading.current_thread() is not threading.main_thread():
        return {}
    replaced = {}
    for signum, kind, usual in ((signal.SIGINT, "interrupt", signal.default_int_handler), (signal.SIGTERM, "terminate", signal.SIG_DFL)):
        if signal.getsignal(signum) is usual:
            replaced[signum] = signal.signal(signum, lambda _signum, _frame, kind=kind: received.append(kind))
    return replaced


def _supervise_server(process: subprocess.Popen, grace_seconds: Optional[float], received: list, early: int) -> int:
    """Wait for the server; after the first stop signal let it finish within the grace, after a second one kill it.

    The first ``early`` signals came while the server was starting: it may have missed them, so they are forwarded.
    """
    handled = 0
    exit_code: Optional[int] = None
    deadline: Optional[float] = None
    while process.poll() is None:
        while handled < len(received):
            kind = received[handled]
            forward = kind == "terminate" or handled < early
            handled += 1
            if exit_code is not None:
                print(Colors.warning("Forced: killing the server"), flush=True)
                process.kill()
                deadline = None
                continue
            exit_code = 130 if kind == "interrupt" else 143
            if forward:
                process.send_signal(signal.SIGINT if kind == "interrupt" else signal.SIGTERM)
            deadline = None if grace_seconds is None else time.monotonic() + grace_seconds
            label, again = ("Interrupted", "Ctrl+C") if kind == "interrupt" else ("SIGTERM", "SIGTERM")
            limit = "no time limit" if grace_seconds is None else f"up to {grace_seconds:g} s"
            print("\n" + Colors.warning(f"{label}: waiting for the server to stop ({limit}; {again} again to force)"), flush=True)
        if deadline is not None and time.monotonic() >= deadline:
            print(Colors.warning(f"The server did not stop within {grace_seconds:g} s: killing it"), flush=True)
            process.kill()
            deadline = None
        time.sleep(0.05)
    if exit_code is None and received:
        exit_code = 130 if received[0] == "interrupt" else 143
    return process.returncode if exit_code is None else exit_code


def _is_docker() -> bool:
    """Detect if running inside a Docker container."""
    return (
        os.path.exists("/.dockerenv")
        or os.environ.get("container") == "docker"
        or (os.path.exists("/proc/1/cgroup") and "docker" in open("/proc/1/cgroup").read())
    )


def pipenv_prefix() -> list:
    """Return ['pipenv', 'run'] on host, [] in Docker (system-wide install)."""
    return [] if _is_docker() else ["pipenv", "run"]


def run_pipenv(args: list, cwd: Optional[Path] = None, env: Optional[dict] = None) -> int:
    """Run a pipenv command with live output.

    In Docker containers (where packages are installed system-wide),
    runs the command directly without pipenv.
    """
    if _is_docker():
        return run_command_live(args, cwd=cwd, env=env)
    return run_command_live(["pipenv", "run"] + args, cwd=cwd, env=env)


# =============================================================================
# Printing Utilities
# =============================================================================

def print_header(title: str):
    """Print a formatted header."""
    width = 60
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def print_success(msg: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✅ {msg}{Colors.NC}")


def print_warning(msg: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.NC}")


def print_error(msg: str):
    """Print an error message."""
    print(f"{Colors.RED}❌ {msg}{Colors.NC}")


def print_info(msg: str):
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.NC}")


# =============================================================================
# Frontend Build Utilities
# =============================================================================

# Files that live under `frontend/src` but are *produced* by the build itself:
# `cmd_fe_build` regenerates them from the backend's OpenAPI schema on every
# run, so they always end up newer than the build output and would make the
# staleness check answer "yes" for ever. That answer used to be merely wasteful
# — a redundant rebuild on every `dev.py server` — but once a coverage run needs
# an *instrumented* build it became destructive: Playwright's webServer rebuilt
# a plain bundle on top of the instrumented one, and the run then reported no JS
# coverage at all while every test passed.
_BUILD_GENERATED_SOURCES = {
    "generated.ts", "openapi.json", "tool-contracts.openapi.json",
    "generated-tools.ts", "tool-contract-map.generated.ts",
}


#: Folders below ``frontend/src`` that only the tests use: Vitest's harnesses (the ``$test`` alias) and module mocks.
_TEST_ONLY_FOLDERS = frozenset({"__tests__", "__mocks__"})


def _counts_for_the_build(path: Path, src_dir: Path) -> bool:
    """Whether a file under ``frontend/src`` or ``frontend/static`` is an input of the build, for ``check_frontend_needs_build()`` (H-24, H-52).

    Not a generated file (``_BUILD_GENERATED_SOURCES``), nothing hidden — a name starting with ``.`` anywhere below
    ``src``: the Finder's ``.DS_Store``, ``.gitignore``, the i18n catalogue's ``.generated`` stamp —, no Vitest file
    (``.test.`` or ``.spec.`` in the name) and nothing in a ``__tests__`` or ``__mocks__`` folder: the build never
    bundles them, no app code imports them. Anything else counts: a build believed fresh by mistake costs more than
    one rebuild too many.
    """
    if path.name in _BUILD_GENERATED_SOURCES or ".test." in path.name or ".spec." in path.name:
        return False
    parts = path.relative_to(src_dir).parts
    return not any(part.startswith(".") for part in parts) and not any(part in _TEST_ONLY_FOLDERS for part in parts[:-1])


#: The folders whose Python files shape the Tool codecs, below the project root (``_tool_contract_sources``).
_TOOL_CONTRACT_FOLDERS = (("backend", "app", "schemas"), ("backend", "app", "services", "tools"), ("backend", "app", "services", "tool_plugins"))

#: Where a successful frontend build records the Tool codegen inputs it was made from, below the project root (H-24).
TOOL_CONTRACT_INPUTS_MARKER = Path("frontend") / "build" / ".tool-contract-inputs"

#: The listing's format, hashed with it: a record written under another rule no longer matches, at the cost of one build.
_TOOL_CONTRACT_LISTING = "tool-contract-inputs/1"


def _tool_contract_sources(project_root: Path) -> list[Path]:
    """The Tool codegen inputs that exist, newly bundled plugins included: their content or their presence shapes the codecs.

    In the three folders, the ``.py`` files, with nothing hidden (a name starting with ``.``) and nothing in a
    ``__pycache__`` (H-24).
    """
    sources = [
        project_root / "dev.py",
        project_root / "scripts" / "list_api_endpoints.py",
        project_root / "scripts" / "export_tool_contracts.py",
        project_root / "frontend" / "scripts" / "generate-tools-client.mjs",
        *sorted((project_root / "frontend" / "scripts").glob("tools-*")),
    ]
    for folder in (project_root.joinpath(*parts) for parts in _TOOL_CONTRACT_FOLDERS):
        sources.extend(source for source in sorted(folder.rglob("*.py")) if not any(part.startswith(".") or part == "__pycache__" for part in source.relative_to(folder).parts))
    return [source for source in sources if source.is_file()]


def _tool_contract_folders(project_root: Path) -> list[Path]:
    """The three folders and their subfolders, ``__pycache__`` aside: a build that recorded no listing reads their mtimes."""
    folders = []
    for folder in (project_root.joinpath(*parts) for parts in _TOOL_CONTRACT_FOLDERS):
        if folder.is_dir():
            folders.append(folder)
            folders.extend(sorted(path for path in folder.rglob("*") if path.is_dir() and "__pycache__" not in path.parts))
    return folders


def tool_contract_fingerprint(project_root: Path) -> str:
    """The Tool codegen inputs' names, hashed: an input added, removed or renamed changes it, a ``.DS_Store`` does not (H-24)."""
    names = sorted(source.relative_to(project_root).as_posix() for source in _tool_contract_sources(project_root))
    return hashlib.sha256("\n".join([_TOOL_CONTRACT_LISTING, *names]).encode()).hexdigest()


def record_tool_contract_inputs(project_root: Path, fingerprint: str) -> None:
    """Record the inputs a successful build made its Tool codecs from (``cmd_fe_build``): bookkeeping, never an error."""
    with contextlib.suppress(OSError):  # without it, the next check reads the folders' mtimes: one rebuild too many at worst
        (project_root / TOOL_CONTRACT_INPUTS_MARKER).write_text(fingerprint, encoding="utf-8")


def _tool_contracts_changed(project_root: Path, build_time: float) -> bool:
    """Whether the Tool codecs may be older than their inputs, for ``check_frontend_needs_build()`` (H-24).

    An input newer than the build has changed. A removed one leaves no date behind: the listing the last successful
    build recorded (``record_tool_contract_inputs``) tells an input added, removed or renamed apart from what only sits
    next to the inputs, a ``.DS_Store``, an editor's hidden file, a ``__pycache__``. A build that recorded none, made
    before the record existed or by ``npm run build`` alone, falls back on the folders' mtimes, which see all of them.
    """
    if any(source.stat().st_mtime > build_time for source in _tool_contract_sources(project_root)):
        return True
    try:
        recorded = (project_root / TOOL_CONTRACT_INPUTS_MARKER).read_text(encoding="utf-8").strip()
    except OSError:
        recorded = ""
    if recorded:
        return recorded != tool_contract_fingerprint(project_root)
    return any(folder.stat().st_mtime > build_time for folder in _tool_contract_folders(project_root))


def check_frontend_needs_build() -> bool:
    """
    Check if frontend needs to be rebuilt.
    Compares modification times of source files vs build output.

    Returns:
        True if build is needed, False otherwise.
    """
    project_root = get_project_root()
    build_dir = project_root / "frontend" / "build"
    src_dir = project_root / "frontend" / "src"

    # If no build exists, definitely need to build
    if not build_dir.exists() or not (build_dir / "index.html").exists():
        return True

    try:
        build_time = (build_dir / "index.html").stat().st_mtime

        # The translation catalogue (src/lib/i18n/<lang>.json) is generated, not tracked: a checkout or a clean that
        # lacks it needs the build that writes it, even when the bundle itself is fresh (E2E fixtures read it).
        if any(not path.exists() for path in generated_catalogs(project_root)):
            return True

        # Check all source files: the ones the bundle can include (_counts_for_the_build). And the static files, which
        # adapter-static copies into the build as they are (sw.js, offline.html, icons, fonts), by the same rule: a hidden
        # one, such as the font cache's .cache_manifest.json rewritten at every check, does not count (H-52)
        for source_dir in (src_dir, project_root / "frontend" / "static"):
            for src_file in source_dir.rglob("*"):
                if src_file.is_file() and _counts_for_the_build(src_file, source_dir) and src_file.stat().st_mtime > build_time:
                    return True

        # Also check config files
        config_files = [
            project_root / "frontend" / "package.json",
            project_root / "frontend" / "vite.config.ts",
            project_root / "frontend" / "svelte.config.js",
            project_root / "frontend" / "tailwind.config.js",
            # Bundled by the changelog modal: CHANGELOG.md inline, each CHANGELOG.<xx>.md as a lazy chunk.
            *sorted(project_root.glob("CHANGELOG*.md")),
            # The translation catalogue is merged from sources under src/ (seen above) and from the plugins' i18n/.
            project_root / "scripts" / "i18n_catalog.py",
            *sorted(path for folder in plugin_i18n_dirs(project_root) for path in folder.glob("*.json")),
        ]
        for f in config_files:
            if f.exists() and f.stat().st_mtime > build_time:
                return True

        # Tool codecs are derived from these inputs, not from the generated files'
        # timestamps. New bundled plugins are discovered without a handwritten list.
        if _tool_contracts_changed(project_root, build_time):
            return True

    except Exception as exc:  # noqa: S110 — staleness probe must never break a build check
        _ = exc

    return False


def auto_build_frontend(debug: bool = False, build_func=None, force: bool = False) -> Optional[int]:
    """
    Auto-build frontend if sources have changed since last build.

    Args:
        debug: Enable debug mode for build
        build_func: Optional function to call for building (for dev.py integration)
                   If None, uses npm run build directly
        force: Rebuild even when the sources are unchanged. Needed when what
               changed is not the source but the *kind* of build wanted — the
               coverage runs need an istanbul-instrumented output, and a normal
               run must not inherit it. Timestamps cannot see that difference.

    Returns:
        None if no build needed
        0 if build succeeded
        Non-zero if build failed
    """
    if not force and not check_frontend_needs_build():
        print_info("Frontend build is up to date")
        return None

    print_info("Frontend build forced (build kind changed)" if force else "Frontend sources changed, rebuilding...")

    if build_func:
        # Use provided build function (from dev.py)
        return build_func(debug=debug)
    else:
        # Direct npm build
        project_root = get_project_root()
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=project_root / "frontend",
            capture_output=False
        )
        return result.returncode
