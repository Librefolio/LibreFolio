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

def get_server_port() -> int:
    """Get server port from environment variable (default: 8000)."""
    return int(os.environ.get("PORT", "8000"))


def get_test_server_port() -> int:
    """Get test server port from environment variable (default: 8001)."""
    return int(os.environ.get("TEST_PORT", "8001"))


# =============================================================================
# Database Configuration
# =============================================================================

# Default data directories (relative to project root)
DEFAULT_PROD_DATA_DIR = "backend/data/prod"
DEFAULT_TEST_DATA_DIR = "backend/data/test"


def get_data_dir(test_mode: bool = False) -> Path:
    """
    Get the data directory based on mode.

    Args:
        test_mode: If True, return test data directory

    Returns:
        Path to data directory
    """
    if test_mode:
        return get_project_root() / DEFAULT_TEST_DATA_DIR

    # Check for custom data dir in env (only for prod mode)
    env_data_dir = os.environ.get("LIBREFOLIO_DATA_DIR")
    if env_data_dir:
        path = Path(env_data_dir)
        if not path.is_absolute():
            path = get_project_root() / path
        return path

    return get_project_root() / DEFAULT_PROD_DATA_DIR


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


def check_server_running(action: str = "this operation", strict: bool = True) -> bool:
    """
    Check if server is running on configured port.

    Args:
        action: Description of the action being performed
        strict: If True, exit on conflict. If False, warn and ask.

    Returns:
        True if can continue, False if should abort
    """
    port = get_server_port()

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
        print(f"  1. Stop the server (Ctrl+C in server terminal)")
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


def run_pipenv(args: list, cwd: Optional[Path] = None) -> int:
    """Run a pipenv command with live output."""
    return run_command_live(["pipenv", "run"] + args, cwd=cwd)


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
            if src_file.is_file() and src_file.stat().st_mtime > build_time:
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

    except Exception:
        pass

    return False


def auto_build_frontend(debug: bool = False, build_func=None) -> Optional[int]:
    """
    Auto-build frontend if sources have changed since last build.

    Args:
        debug: Enable debug mode for build
        build_func: Optional function to call for building (for dev.py integration)
                   If None, uses npm run build directly

    Returns:
        None if no build needed
        0 if build succeeded
        Non-zero if build failed
    """
    if not check_frontend_needs_build():
        print_info("Frontend build is up to date")
        return None

    print_info("Frontend sources changed, rebuilding...")

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

