"""
Application configuration module.
Loads environment variables and provides application-wide settings.

Data Directory Structure:
    backend/data/
    ├── prod/                    # Production data
    │   ├── sqlite/app.db
    │   ├── custom-uploads/
    │   ├── broker_reports/{uploaded,parsed,failed}/
    │   ├── logs/
    │   └── secrets/instance.key # generated on first use (services/platform/instance_key.py)
    └── test/                    # Test data (isolated)
        ├── sqlite/app.db
        ├── custom-uploads/
        ├── broker_reports/{uploaded,parsed,failed}/
        └── logs/

Environment Variables (see .env):
    LIBREFOLIO_DATA_DIR: Override production data directory (default: ./backend/data/prod)
    LIBREFOLIO_TEST_DATA_DIR: Override test data directory (default: ./backend/data/test)
    LIBREFOLIO_TEST_MODE: When "1", use the test data directory; for a test lane only (H-46: outside one, an error of the
        configuration checks, and the managed profile does not start)
    PORT: Production server port (default: 6040)
    TEST_PORT: Test server port (default: 6041)
    LOG_LEVEL: Logging level (default: INFO)
    PREVIEW_CACHE_MAX_MB: Image preview cache size in MB (default: 50)
    SESSION_COOKIE_SECURE: Secure attribute of the session cookie: auto | always | never (default: auto)
    RISK_SIMULATION_WORKERS: Spawned simulation workers (default: 1)
    RISK_OPTIMIZATION_WORKERS: Spawned optimization workers (default: 1)
    RISK_SIMULATION_IDLE_TIMEOUT_SECONDS: Simulation worker idle reap (default: 600; managed: 60)
    RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS: Optimization worker idle reap (default: 600; managed: 60)
    LIBREFOLIO_PROFILE: Instance profile: selfhosted | managed (default: selfhosted); a profile's defaults: PROFILE_DEFAULTS
        for Settings fields, ENVIRONMENT_PROFILE_DEFAULTS (profile_default()) for the variables of the section modules
    LIBREFOLIO_FRAME_PROTECTION: X-Frame-Options and frame-ancestors on every response, plus object-src, base-uri and
        form-action on documents: HTML, XHTML, SVG, XML (default: off; managed: on)
    LIBREFOLIO_CSP_REPORT_ONLY: Report-only Content-Security-Policy on the web app's pages (default: off; managed: on)
    LIBREFOLIO_CLIENT_IP_HEADER: The header a trusted reverse proxy passes the visitor's address in, such as Fly-Client-IP
        (default: unset, the connection's address; no profile sets it)

Secrets (JWT_SECRET, LIBREFOLIO_INSTANCE_KEY, ...) also accept NAME_FILE, the path of a file holding the value: see
env_secret(). Addresses (LIBREFOLIO_PUBLIC_URL, LIBREFOLIO_BILLING_URL, ...) follow one rule: see env_url(). Every
variable the code reads is listed in .env.example.
"""

import os
import re
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlsplit

from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings

from backend.app.utils.runtime.version import get_git_version

# =============================================================================
# Constants (not configurable via .env — change here if needed)
# =============================================================================
PROJECT_NAME: str = "LibreFolio"
API_V1_PREFIX: str = "/api/v1"

# Project root: four directories up from backend/app/config/__init__.py
PROJECT_ROOT = Path(__file__).parents[3]

# Default data directories (relative to project root)
DEFAULT_PROD_DATA_DIR = PROJECT_ROOT / "backend" / "data" / "prod"
DEFAULT_TEST_DATA_DIR = PROJECT_ROOT / "backend" / "data" / "test"
PRODUCTION_DATA_MARKER = ".librefolio-production-data"
TEST_LANE_HEADER = "X-LibreFolio-Test-Lane"

#: What a profile changes (decision D5, F27): ``Settings`` gives every listed field the environment and ``.env`` leave
#: unset the active profile's value. A value the operator sets always wins, even one equal to the code default. A
#: self-hosted install keeps every code default.
PROFILE_DEFAULTS: dict[str, dict[str, object]] = {
    "selfhosted": {},
    "managed": {
        # A hosting provider runs many instances: idle risk workers give their memory back after a minute (F27)
        "RISK_SIMULATION_IDLE_TIMEOUT_SECONDS": 60.0,
        "RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS": 60.0,
        "LIBREFOLIO_FRAME_PROTECTION": True,
        "LIBREFOLIO_CSP_REPORT_ONLY": True,
    },
}

#: The same for the variables a section module of this package reads from the environment, outside ``Settings`` (H-17):
#: while such a variable is unset, ``profile_default(name, fallback)`` gives the active profile's value. ``selfhosted``
#: lists none, so a self-hosted install keeps every code fallback. Every other profile lists every variable a reader
#: asks for, even at the fallback's value: one it does not list raises ``ProfileDefaultError`` (H-37), never the
#: self-hosted fallback, which for a limit may mean none.
ENVIRONMENT_PROFILE_DEFAULTS: dict[str, dict[str, object]] = {
    "selfhosted": {},
    "managed": {
        # The largest archive a restore accepts, in megabytes (decision 43; workstream B, config/backup.py)
        "LIBREFOLIO_BACKUP_MAX_UPLOAD_MB": 500,
    },
}

#: The name of an HTTP header (RFC 9110 ``token``), for ``LIBREFOLIO_CLIENT_IP_HEADER``.
_HEADER_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")
#: Headers holding a list of addresses, whose first value the client chooses: never ``LIBREFOLIO_CLIENT_IP_HEADER``.
_LIST_HEADERS = frozenset({"x-forwarded-for", "forwarded"})

#: The secrets that make an instance trust a session or decrypt its data, in every form. A test runtime never inherits
#: them (``configure_test_runtime`` in ``scripts/cli_base.py``): a test lane signs and derives with secrets of its own.
INSTANCE_TRUST_SECRETS = ("JWT_SECRET", "JWT_SECRET_FILE", "LIBREFOLIO_INSTANCE_KEY", "LIBREFOLIO_INSTANCE_KEY_FILE")


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
# Secrets: NAME, or the file named by NAME_FILE
# =============================================================================

SECRET_FILE_SUFFIX = "_FILE"
SECRET_FILE_MAX_BYTES = 64 * 1024


class SecretFileError(RuntimeError):
    """A secret file cannot give its secret: missing, unreadable, empty or blank, not UTF-8 text or larger than 64 KiB."""


def env_secret(name: str) -> str | None:
    """The secret ``name``, from the process environment only, never from ``.env``: ``NAME``, or else ``NAME_FILE``.

    - ``NAME``, when not blank, is the secret as written, spaces included. It wins over ``NAME_FILE``: the configuration
      audit warns when both are set.
    - Otherwise ``NAME_FILE``, when not blank, is the path of a file holding the secret, as Docker and Kubernetes mount
      their secrets. The secret is the file's text without a leading UTF-8 byte order mark and without its trailing
      line breaks. A relative path starts from the project folder.
    - Otherwise there is no secret: ``None``. An empty or blank value counts as unset: a stray space is never used as
      a key.

    A ``NAME_FILE`` that cannot give its secret raises ``SecretFileError``, which names the variable and the path,
    never the content.
    """
    value = os.environ.get(name, "")
    if value.strip():
        return value
    file_name = os.environ.get(name + SECRET_FILE_SUFFIX, "")
    if not file_name.strip():
        return None
    return read_secret_file(_secret_file_path(file_name), name + SECRET_FILE_SUFFIX)


def env_secret_origin(name: str) -> str | None:
    """Where ``env_secret(name)`` takes the secret from, for messages: ``NAME``, ``NAME_FILE (<path>)``, or ``None``."""
    if os.environ.get(name, "").strip():
        return name
    file_name = os.environ.get(name + SECRET_FILE_SUFFIX, "")
    if file_name.strip():
        return f"{name}{SECRET_FILE_SUFFIX} ({_secret_file_path(file_name)})"
    return None


def env_url(name: str) -> str | None:
    """The http(s) address in the variable ``name``, from the process environment only, never from ``.env``.

    - An empty or blank value counts as unset: ``None``.
    - Otherwise the value, stripped, must be an ``http://`` or ``https://`` address (the scheme in any case) with a host
      name, no user info (no ``@`` in its authority: a user name or a password would be published with the address,
      X-R35), and no space, tab or line break inside. One trailing slash is removed, so a path can be appended to it;
      nothing else changes, the case included. An ``@`` in the path, the query or the fragment is no user info.
    - Any other value raises ``ValueError``, which names the variable and quotes the value, unless the value holds an
      ``@``: it may carry a user name or a password, and the caller logs the error. The caller decides what an invalid
      address costs.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        return None
    try:
        parts = urlsplit(value)
        # urlsplit drops tabs and line breaks before parsing: the whitespace check reads the raw value.
        valid = not any(character.isspace() for character in value) and value.lower().startswith(("http://", "https://")) and bool(parts.hostname) and "@" not in parts.netloc
    except ValueError:  # a malformed address, such as an unclosed IPv6 bracket
        valid = False
    if not valid:
        if "@" in value:
            raise ValueError(f"{name} (its value is not shown: it holds an @, which may carry a user name or a password): expected an http:// or https:// address with a host name and no user name or password")
        raise ValueError(f"{name}={value!r}: expected an http:// or https:// address with a host name")
    return value[:-1] if value.endswith("/") else value


def _secret_file_path(file_name: str) -> Path:
    path = Path(file_name).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_secret_file(path: Path, label: str) -> str:
    """The secret held by ``path``, without a leading UTF-8 byte order mark and its trailing line breaks.

    ``label`` names the source in the errors. A file that holds nothing but spaces and line breaks is an error, like an
    empty one.
    """
    try:
        with path.open("rb") as handle:
            raw = handle.read(SECRET_FILE_MAX_BYTES + 1)
    except FileNotFoundError:
        raise SecretFileError(f"{label}: {path} does not exist") from None
    except OSError as exc:
        raise SecretFileError(f"{label}: {path} cannot be read ({exc.strerror or type(exc).__name__})") from None
    if len(raw) > SECRET_FILE_MAX_BYTES:
        raise SecretFileError(f"{label}: {path} is larger than {SECRET_FILE_MAX_BYTES} bytes, too large for a secret")
    try:
        secret = raw.decode("utf-8-sig").rstrip("\r\n")
    except UnicodeDecodeError:
        raise SecretFileError(f"{label}: {path} is not UTF-8 text") from None
    if not secret.strip():
        raise SecretFileError(f"{label}: {path} is empty or blank")
    return secret


def secrets_set_twice() -> list[str]:
    """The secrets set both as ``NAME`` and as ``NAME_FILE``, neither blank, sorted: ``NAME`` wins and the file is ignored.

    A secret of LibreFolio is ``JWT_SECRET`` or a ``LIBREFOLIO_*`` variable: a new secret takes that prefix, so it is
    covered here without a list to keep up to date.
    """
    names = []
    for variable, value in os.environ.items():
        if not value.strip() or not variable.endswith(SECRET_FILE_SUFFIX):
            continue
        name = variable.removesuffix(SECRET_FILE_SUFFIX)
        if (name == "JWT_SECRET" or name.startswith("LIBREFOLIO_")) and os.environ.get(name, "").strip():
            names.append(name)
    return sorted(names)


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

    # Image Preview Cache
    PREVIEW_CACHE_MAX_MB: int = 50

    # Session cookie Secure attribute: "auto" (on HTTPS, seen directly or as the first
    # X-Forwarded-Proto value of a reverse proxy), "always", or "never" (the only way off over HTTPS)
    SESSION_COOKIE_SECURE: Literal["auto", "always", "never"] = "auto"

    @field_validator("SESSION_COOKIE_SECURE", mode="before")
    @classmethod
    def _cookie_secure_mode(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    # Instance profile: "selfhosted" (an install run by its owner) or "managed" (an instance a hosting provider runs for
    # its customers), reported by GET /system/instance. Its defaults: PROFILE_DEFAULTS
    LIBREFOLIO_PROFILE: Literal["selfhosted", "managed"] = "selfhosted"

    @field_validator("LIBREFOLIO_PROFILE", mode="before")
    @classmethod
    def _instance_profile(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    # Frame protection (D5): X-Frame-Options: SAMEORIGIN and Content-Security-Policy: frame-ancestors 'self' on every
    # response, and on documents (HTML, XHTML, SVG, XML) object-src 'none', base-uri 'self' and form-action 'self' too
    # (H-42, H-45). Off by default: a self-hosted install may be embedded by its owner's dashboards (Home Assistant
    # panels)
    LIBREFOLIO_FRAME_PROTECTION: bool = False
    # Report-only Content-Security-Policy on the web app's pages (D5): violations show in the browser console, nothing
    # is blocked. Off by default
    LIBREFOLIO_CSP_REPORT_ONLY: bool = False
    # The API's documentation, /api/v1/docs, /api/v1/redoc and /api/v1/openapi.json (H-55 R5): off by default in every
    # profile, Docker included, so an instance publishes no map of its API; `dev.py server --debug` turns it on, and test
    # mode always has it (api_docs_enabled()). The managed profile keeps the code default: no PROFILE_DEFAULTS entry
    LIBREFOLIO_API_DOCS: bool = False

    # The header in which a trusted reverse proxy passes the visitor's address (P17), such as Fly.io's Fly-Client-IP:
    # services/platform/client_address.py. Empty by default: the connection's address. No profile sets it
    LIBREFOLIO_CLIENT_IP_HEADER: str = ""

    @field_validator("LIBREFOLIO_CLIENT_IP_HEADER", mode="after")
    @classmethod
    def _client_ip_header(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return ""
        if not _HEADER_TOKEN.fullmatch(value):
            raise ValueError(f"LIBREFOLIO_CLIENT_IP_HEADER={value!r}: expected the name of one HTTP header, such as Fly-Client-IP")
        if value.lower() in _LIST_HEADERS:
            raise ValueError(f"LIBREFOLIO_CLIENT_IP_HEADER={value!r}: a list of addresses whose first value the client chooses; for X-Forwarded-For set FORWARDED_ALLOW_IPS, which uvicorn reads")
        return value

    # Native quantitative engines
    RISK_SIMULATION_WORKERS: int = Field(1, ge=1, le=8)
    RISK_OPTIMIZATION_WORKERS: int = Field(1, ge=1, le=8)
    RISK_SIMULATION_QUEUE_CAPACITY: int = Field(2, ge=0, le=64)
    RISK_OPTIMIZATION_QUEUE_CAPACITY: int = Field(2, ge=0, le=64)
    RISK_SIMULATION_TIMEOUT_SECONDS: float = Field(120.0, gt=0)
    RISK_OPTIMIZATION_TIMEOUT_SECONDS: float = Field(60.0, gt=0)
    RISK_SIMULATION_IDLE_TIMEOUT_SECONDS: float = Field(600.0, ge=0)
    RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS: float = Field(600.0, ge=0)

    @model_validator(mode="after")
    def _apply_profile_defaults(self) -> "Settings":
        """Give every field the profile changes, and that neither the environment nor ``.env`` set, the profile's value."""
        for name, value in PROFILE_DEFAULTS.get(self.LIBREFOLIO_PROFILE, {}).items():
            if name not in self.model_fields_set:
                # Not an assignment, which would count the field as set by the operator and skip its validation; the
                # table's values are checked against the fields' types by services profile-defaults
                object.__setattr__(self, name, value)
        return self

    model_config = ConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        case_sensitive=True,
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore env vars not defined as fields (e.g. LIBREFOLIO_DATA_DIR)
    )

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        """In test mode the instance's ``.env`` is not read: a test lane sees only what its runner exported.

        ``scripts/cli_base.configure_test_runtime`` drops the instance's settings from the lane's environment; without
        this, ``Settings`` would read them back from ``.env`` (its ``env_file``).
        """
        if is_test_mode():
            return init_settings, env_settings, file_secret_settings
        return init_settings, env_settings, dotenv_settings, file_secret_settings


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
    return same_filesystem and (is_case_insensitive(left_parent) or is_case_insensitive(right_parent)) and str(left).casefold() == str(right).casefold()


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
        case_insensitive = left_parent.stat().st_dev == right_parent.stat().st_dev and (
            _same_filesystem_location(
                left_parent,
                left_parent.with_name(left_parent.name.swapcase()),
            )
            or _same_filesystem_location(
                right_parent,
                right_parent.with_name(right_parent.name.swapcase()),
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
    # Path.exists() re-raises EACCES: a folder that cannot be traversed is refused with a message, never let through
    try:
        marked = any((ancestor / PRODUCTION_DATA_MARKER).exists() for ancestor in (candidate, *candidate.parents))
    except OSError as exc:
        raise ValueError(f"Cannot verify the test data directory: {exc.strerror or type(exc).__name__}") from exc
    if marked:
        raise ValueError("Test data directory is inside a marked production data directory")

    for relative in (
        Path("sqlite"),
        Path("custom-uploads"),
        Path("broker_reports"),
        Path("logs"),
        Path("scenario_catalog"),
        Path("secrets"),
    ):
        managed_root = candidate / relative
        if not managed_root.is_dir():
            continue
        try:
            marker = next(managed_root.rglob(PRODUCTION_DATA_MARKER), None)
        except OSError as exc:
            raise ValueError(f"Cannot verify test data subtree: {relative}") from exc
        if marker is not None:
            raise ValueError(f"Test data subtree contains a marked production root: {relative}")

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
        # The scheduler's lock across worker processes (workstream Z, Z-11: run_lock.LOCK_FILE_NAME)
        Path(".scheduler.lock"),
        Path("scenario_catalog"),
        Path("secrets"),
        Path("secrets/instance.key"),
        # Instance backup (workstream B): the archives, and the restore's copies and its pending marker (lots B2, B3).
        Path("backups"),
        Path(".restore"),
        # The registry of the hosting panel's used tickets (workstream H, H-61 L2: ticket_registry.REGISTRY_FILE)
        Path("panel_tickets.sqlite3"),
        # The caches the app keeps on the volume: the PDF viewer's CJK fonts (workstream H, H-55: pdf_fonts.cache_dir)
        Path("cache"),
    )
    for relative in managed_paths:
        test_target = (candidate / relative).resolve()
        if not test_target.is_relative_to(candidate):
            raise ValueError(f"Test data path escapes its configured root: {relative}")
        try:
            aliased = any(_same_filesystem_location(test_target, (prod / relative).resolve()) for prod in production_dirs)
        except OSError as exc:
            raise ValueError(f"Cannot verify test data path: {relative} ({exc.strerror or type(exc).__name__})") from exc
        if aliased:
            raise ValueError(f"Test data path aliases production data: {relative}")
    return candidate


def get_test_data_dir() -> Path:
    """Get the test data directory, including an explicit lane override."""
    return validate_test_data_dir(os.environ.get("LIBREFOLIO_TEST_DATA_DIR") or DEFAULT_TEST_DATA_DIR)


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


def api_docs_enabled() -> bool:
    """Whether the API's documentation is served (H-55 R5): ``LIBREFOLIO_API_DOCS`` (``dev.py server --debug`` sets it), or
    test mode, whose lanes read ``/api/v1/openapi.json`` in their tests. Read at each call; ``main.py`` reads it once, when
    the app is built."""
    return is_test_mode() or get_settings().LIBREFOLIO_API_DOCS


class ProfileDefaultError(TypeError):
    """An entry of ``ENVIRONMENT_PROFILE_DEFAULTS`` its reader cannot use: not of the type of the reader's own default
    (H-27), or missing from a profile other than ``selfhosted`` (H-37).

    The table is code, so such an entry is a bug: the reader stops on it rather than use it or fall back. Read as it is,
    a ``None`` upload limit would mean no limit at all, and so would the self-hosted fallback ``0`` of a managed profile
    that lost its entry.
    """


def profile_default[T](name: str, fallback: T) -> T:
    """What the active profile gives ``name``, a variable a section module reads from the environment, else ``fallback``.

    ``ENVIRONMENT_PROFILE_DEFAULTS`` holds the profile's values; ``fallback`` is the code's own default, the one a
    self-hosted install gets. The section module asks only while its variable is unset, and keeps its own rules for a
    blank or an invalid value. The profile is read at each call, normalised by ``Settings``. Every profile but
    ``selfhosted`` must list ``name``: a name it does not list raises ``ProfileDefaultError`` rather than give the
    self-hosted ``fallback`` (H-37, fail closed). A profile's value is of the exact type of ``fallback`` (``500`` for
    ``0``; never ``None``, ``"500"``, ``500.0`` nor ``True``): any other raises ``ProfileDefaultError`` too.
    """
    profile = get_settings().LIBREFOLIO_PROFILE
    values = ENVIRONMENT_PROFILE_DEFAULTS.get(profile, {})
    if name not in values:
        if profile == "selfhosted":
            return fallback
        raise ProfileDefaultError(f"{name}: the {profile} profile gives it no value; every profile but selfhosted must give one to each variable a reader asks for, rather than leave it the self-hosted default: ENVIRONMENT_PROFILE_DEFAULTS is missing it")
    value = values[name]
    if type(value) is not type(fallback):
        raise ProfileDefaultError(f"{name}: the {profile} profile gives {value!r}, a {type(value).__name__}, where its reader expects a {type(fallback).__name__} like its own default {fallback!r}: ENVIRONMENT_PROFILE_DEFAULTS is wrong")
    return cast(T, value)


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
