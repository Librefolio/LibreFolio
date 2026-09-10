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

import os
import secrets
import socket
import subprocess
from pathlib import Path
from typing import Optional, Tuple

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
) -> tuple[int, Path]:
    """Validate and apply one test lane's port and data directory.

    Explicit values are exported for every child process. Omitted values keep
    their effective value while normalizing it for every child process.
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

    _load_project_dotenv()
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
_BUILD_GENERATED_SOURCES = {"generated.ts", "openapi.json"}


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

        # Check all source files
        for src_file in src_dir.rglob("*"):
            if src_file.is_file() and src_file.name not in _BUILD_GENERATED_SOURCES and src_file.stat().st_mtime > build_time:
                return True

        # Also check config files
        config_files = [
            project_root / "frontend" / "package.json",
            project_root / "frontend" / "vite.config.ts",
            project_root / "frontend" / "svelte.config.js",
            project_root / "frontend" / "tailwind.config.js",
        ]
        for f in config_files:
            if f.exists() and f.stat().st_mtime > build_time:
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
