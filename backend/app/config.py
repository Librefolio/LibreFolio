"""
Application configuration module.
Loads environment variables and provides application-wide settings.

Data Directory Structure:
    backend/data/
    ├── prod/                    # Production data
    │   ├── sqlite/app.db
    │   ├── custom-uploads/
    │   ├── broker_reports/{uploaded,parsed,failed}/
    │   └── logs/
    └── test/                    # Test data (isolated)
        ├── sqlite/app.db
        ├── custom-uploads/
        ├── broker_reports/{uploaded,parsed,failed}/
        └── logs/

Environment Variables (see .env):
    LIBREFOLIO_DATA_DIR: Override production data directory (default: ./backend/data/prod)
    LIBREFOLIO_TEST_DATA_DIR: Override test data directory (default: ./backend/data/test)
    LIBREFOLIO_TEST_MODE: When "1", use the test data directory
    PORT: Production server port (default: 6040)
    TEST_PORT: Test server port (default: 6041)
    LOG_LEVEL: Logging level (default: INFO)
    PORTFOLIO_BASE_CURRENCY: Base currency ISO 4217 (default: EUR)
    PREVIEW_CACHE_MAX_MB: Image preview cache size in MB (default: 50)
    RISK_SIMULATION_WORKERS: Spawned simulation workers (default: 1)
    RISK_OPTIMIZATION_WORKERS: Spawned optimization workers (default: 1)
    RISK_SIMULATION_IDLE_TIMEOUT_SECONDS: Simulation worker idle reap (default: 600)
    RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS: Optimization worker idle reap (default: 600)
"""

import os
from pathlib import Path

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

# =============================================================================
# Constants (not configurable via .env — change here if needed)
# =============================================================================
PROJECT_NAME: str = "LibreFolio"
API_V1_PREFIX: str = "/api/v1"

# Get project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Default data directories (relative to project root)
DEFAULT_PROD_DATA_DIR = PROJECT_ROOT / "backend" / "data" / "prod"
DEFAULT_TEST_DATA_DIR = PROJECT_ROOT / "backend" / "data" / "test"
PRODUCTION_DATA_MARKER = ".librefolio-production-data"
TEST_LANE_HEADER = "X-LibreFolio-Test-Lane"


# =============================================================================
# Test mode management
# =============================================================================


def set_test_mode(enabled: bool = True):
    """
    Enable/disable test mode globally.
    When enabled, data directory switches to backend/data/test/.
    """
    os.environ["LIBREFOLIO_TEST_MODE"] = "1" if enabled else "0"
    _reset_engine_singletons()


def _reset_engine_singletons():
    """Reset engine singletons to allow recreation with new settings."""
    from backend.app.db import session as session_module  # noqa: PLC0415 — lazy import / avoid circular

    session_module.sync_engine = None
    session_module.async_engine = None


def is_test_mode() -> bool:
    """
    Check if test mode is enabled.
    Checks env var directly to support dynamic switching.
    """
    return os.environ.get("LIBREFOLIO_TEST_MODE", "").lower() in ("1", "true", "yes")


# =============================================================================
# Settings model (loaded from .env)
# =============================================================================


class Settings(BaseSettings):
    """
    Application settings loaded from .env file.
    Environment variables take precedence over .env values.

    NOTE: DATABASE_URL is computed dynamically by get_settings(),
    it is NOT read from .env.
    """

    # Database URL — computed dynamically, do NOT set in .env
    DATABASE_URL: str = ""

    # Server
    PORT: int = 6040
    TEST_PORT: int = 6041

    # Logging
    LOG_LEVEL: str = "INFO"

    # Portfolio
    PORTFOLIO_BASE_CURRENCY: str = "EUR"

    # Image Preview Cache
    PREVIEW_CACHE_MAX_MB: int = 50

    # Native quantitative engines
    RISK_SIMULATION_WORKERS: int = Field(1, ge=1, le=8)
    RISK_OPTIMIZATION_WORKERS: int = Field(1, ge=1, le=8)
    RISK_SIMULATION_QUEUE_CAPACITY: int = Field(2, ge=0, le=64)
    RISK_OPTIMIZATION_QUEUE_CAPACITY: int = Field(2, ge=0, le=64)
    RISK_SIMULATION_TIMEOUT_SECONDS: float = Field(120.0, gt=0)
    RISK_OPTIMIZATION_TIMEOUT_SECONDS: float = Field(60.0, gt=0)
    RISK_SIMULATION_IDLE_TIMEOUT_SECONDS: float = Field(600.0, ge=0)
    RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS: float = Field(600.0, ge=0)

    model_config = ConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        case_sensitive=True,
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore env vars not defined as fields (e.g. LIBREFOLIO_DATA_DIR)
    )


# =============================================================================
# Data directory resolution
# =============================================================================


def _resolve_data_dir(path: str | os.PathLike[str]) -> Path:
    raw = os.fspath(path).strip()
    if not raw:
        raise ValueError("Data directory cannot be empty")
    if "?" in raw or "#" in raw:
        raise ValueError("Data directory cannot contain '?' or '#'")
    resolved = Path(raw).expanduser()
    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved
    resolved = resolved.resolve()
    if "?" in str(resolved) or "#" in str(resolved):
        raise ValueError("Resolved data directory cannot contain '?' or '#'")
    return resolved


def _same_filesystem_location(left: Path, right: Path) -> bool:
    try:
        return left.samefile(right)
    except OSError:
        if left == right:
            return True

    def nearest_existing(path: Path) -> Path:
        current = path
        while not current.exists() and current != current.parent:
            current = current.parent
        return current

    def is_case_insensitive(path: Path) -> bool:
        current = nearest_existing(path)
        while current != current.parent:
            swapped = current.with_name(current.name.swapcase())
            if swapped != current:
                try:
                    return swapped.samefile(current)
                except OSError:
                    pass
            current = current.parent
        return False

    left_parent = nearest_existing(left)
    right_parent = nearest_existing(right)
    try:
        same_filesystem = left_parent.stat().st_dev == right_parent.stat().st_dev
    except OSError:
        same_filesystem = False
    return (
        same_filesystem
        and (is_case_insensitive(left_parent) or is_case_insensitive(right_parent))
        and str(left).casefold() == str(right).casefold()
    )


def _paths_overlap(left: Path, right: Path) -> bool:
    """Return whether either root contains the other on the active filesystem."""
    if _same_filesystem_location(left, right):
        return True

    left_parent = left
    while not left_parent.exists() and left_parent != left_parent.parent:
        left_parent = left_parent.parent
    right_parent = right
    while not right_parent.exists() and right_parent != right_parent.parent:
        right_parent = right_parent.parent
    try:
        case_insensitive = (
            left_parent.stat().st_dev == right_parent.stat().st_dev
            and (
                _same_filesystem_location(
                    left_parent,
                    left_parent.with_name(left_parent.name.swapcase()),
                )
                or _same_filesystem_location(
                    right_parent,
                    right_parent.with_name(right_parent.name.swapcase()),
                )
            )
        )
    except (OSError, ValueError):
        case_insensitive = False

    left_parts = left.parts
    right_parts = right.parts
    if case_insensitive:
        left_parts = tuple(part.casefold() for part in left_parts)
        right_parts = tuple(part.casefold() for part in right_parts)
    shortest = min(len(left_parts), len(right_parts))
    return left_parts[:shortest] == right_parts[:shortest]


def validate_test_data_dir(  # noqa: C901 — ordered safety boundary: identity, markers, managed paths
    data_dir: str | os.PathLike[str],
    *,
    production_data_dir: str | os.PathLike[str] | None = None,
) -> Path:
    """Reject a test root that aliases canonical or configured production data."""
    candidate = _resolve_data_dir(data_dir)
    configured_prod = production_data_dir
    if configured_prod is None:
        configured_prod = os.environ.get("LIBREFOLIO_DATA_DIR")

    production_dirs = [DEFAULT_PROD_DATA_DIR.resolve()]
    if configured_prod:
        production_dirs.append(_resolve_data_dir(configured_prod))
    if any(_paths_overlap(candidate, prod) for prod in production_dirs):
        raise ValueError("Test data directory must not overlap the production data directory")
    if any((ancestor / PRODUCTION_DATA_MARKER).exists() for ancestor in (candidate, *candidate.parents)):
        raise ValueError("Test data directory is inside a marked production data directory")

    for relative in (
        Path("sqlite"),
        Path("custom-uploads"),
        Path("broker_reports"),
        Path("logs"),
        Path("scenario_catalog"),
    ):
        managed_root = candidate / relative
        if not managed_root.is_dir():
            continue
        try:
            marker = next(managed_root.rglob(PRODUCTION_DATA_MARKER), None)
        except OSError as exc:
            raise ValueError(
                f"Cannot verify test data subtree: {relative}"
            ) from exc
        if marker is not None:
            raise ValueError(
                f"Test data subtree contains a marked production root: {relative}"
            )

    managed_paths = (
        Path("sqlite"),
        Path("sqlite/app.db"),
        Path("custom-uploads"),
        Path("broker_reports"),
        Path("broker_reports/uploaded"),
        Path("broker_reports/parsed"),
        Path("broker_reports/failed"),
        Path("logs"),
        Path("scheduler_state.json"),
        Path("scenario_catalog"),
    )
    for relative in managed_paths:
        test_target = (candidate / relative).resolve()
        if not test_target.is_relative_to(candidate):
            raise ValueError(
                f"Test data path escapes its configured root: {relative}"
            )
        if any(
            _same_filesystem_location(test_target, (prod / relative).resolve())
            for prod in production_dirs
        ):
            raise ValueError(
                f"Test data path aliases production data: {relative}"
            )
    return candidate


def get_test_data_dir() -> Path:
    """Get the test data directory, including an explicit lane override."""
    return validate_test_data_dir(
        os.environ.get("LIBREFOLIO_TEST_DATA_DIR") or DEFAULT_TEST_DATA_DIR
    )


def get_data_dir() -> Path:
    """
    Get the current data directory based on environment and test mode.

    Priority:
    1. Test mode + LIBREFOLIO_TEST_DATA_DIR → custom test path
    2. Test mode → backend/data/test/
    3. LIBREFOLIO_DATA_DIR env var → custom production path
    4. Default → backend/data/prod/
    """
    if is_test_mode():
        return get_test_data_dir()

    env_data_dir = os.environ.get("LIBREFOLIO_DATA_DIR")
    if env_data_dir:
        return _resolve_data_dir(env_data_dir)

    return DEFAULT_PROD_DATA_DIR


def get_database_url() -> str:
    """Get the SQLite database URL based on current data directory."""
    db_path = get_data_dir() / "sqlite" / "app.db"
    return f"sqlite:///{db_path}"


def get_version() -> str:
    """
    Get application version from git tags.
    Same logic as ./dev.py info version and frontend APP_VERSION.
    """
    from backend.app.utils.version import get_git_version  # noqa: PLC0415 — lazy import / avoid circular

    return get_git_version()


def get_settings() -> Settings:
    """
    Get settings instance with computed fields.

    DATABASE_URL is computed dynamically based on test mode and data directory.
    LOG_LEVEL can be overridden by LIBREFOLIO_LOG_LEVEL env var.
    """
    settings = Settings()
    settings.DATABASE_URL = get_database_url()

    log_level_override = os.environ.get("LIBREFOLIO_LOG_LEVEL")
    if log_level_override:
        settings.LOG_LEVEL = log_level_override.upper()

    return settings


def ensure_data_dirs() -> None:
    """
    Ensure all data directories exist.
    Called at application startup.
    """
    data_dir = get_data_dir()
    for subdir in [
        "sqlite",
        "custom-uploads",
        "broker_reports/uploaded",
        "broker_reports/parsed",
        "broker_reports/failed",
        "logs",
    ]:
        (data_dir / subdir).mkdir(parents=True, exist_ok=True)
    if not is_test_mode():
        (data_dir / PRODUCTION_DATA_MARKER).write_text(
            "LibreFolio production data root\n",
            encoding="utf-8",
        )
