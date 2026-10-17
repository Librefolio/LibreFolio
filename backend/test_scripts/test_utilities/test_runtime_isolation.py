"""Pure contract tests for per-run test port and data-directory isolation.

Covered here: data-directory resolution and its production guards, lane runtime
configuration (including the instance configuration a lane drops, the few
settings ``--lane-setting`` lets a lane set all the same (H-43), and
``Settings`` reading no dotenv file in test mode), CLI/runner wiring (the
managed lane's cloud smoke kept out of every ``all`` included, H-43),
shared-backend ownership, the ``exec_unmasked`` spawn wrapper,
``mkdocs gallery --no-populate`` reusing a lane's test database, and the
frontend build's staleness probe (``check_frontend_needs_build``): what it
counts as an input, and the listing of the Tool codegen inputs a successful
build records, which it compares instead of the folders' mtimes (H-24r).
Among the production guards, a managed path of a test root (the scheduler's
state and lock files included, Z-24) is refused when a symlink sends it out of
the root or a hard link makes it the production file itself.
Every test is PURE — no server, no database, no network — using ``tmp_path``,
in-memory fakes, and (only where a real signal is the subject) short-lived
subprocesses that just print or wait.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import inspect
import json
import os
import re
import select
import shutil
import socket
import subprocess
import sys
import threading
import urllib.parse
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import backend.app.config as backend_config
import dev
import scripts.cli_base as cli_base
import scripts.exec_unmasked as exec_unmasked
import scripts.list_api_endpoints as endpoint_listing
import scripts.test_runner as test_runner_package
from backend.app.config import platform as config_platform
from backend.test_scripts import test_db_config
from backend.test_scripts import test_server_helper as test_server_helper_module
from scripts.test_runner import _backend_db as test_runner_backend_db
from scripts.test_runner import _cli as test_runner_cli
from scripts.test_runner import _common as test_runner_common
from scripts.test_runner import _registry as test_runner_registry
from scripts.test_runner import _server as test_runner_server

# ── Shared fixtures, fakes and probes ──────────────────────────────────────

OVERLAP_ERROR = "^Test data directory must not overlap the production data directory$"
MARKED_ERROR = "^Test data directory is inside a marked production data directory$"
RAW_METACHAR_ERROR = r"^Data directory cannot contain '\?' or '#'$"
RESOLVED_METACHAR_ERROR = r"^Resolved data directory cannot contain '\?' or '#'$"
RUNTIME_ENV_NAMES = ("LIBREFOLIO_TEST_MODE", "LIBREFOLIO_DATA_DIR", "LIBREFOLIO_TEST_DATA_DIR", "LIBREFOLIO_TEST_LANE_ID", "PORT", "TEST_PORT", "PIPENV_DONT_LOAD_ENV", "PIPENV_DOTENV_LOCATION")


@pytest.fixture
def runtime_env(monkeypatch):
    """Start with no runtime override and restore every mutation after the test."""
    snapshot = dict(os.environ)
    for name in RUNTIME_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    yield monkeypatch
    os.environ.clear()
    os.environ.update(snapshot)


def runtime_state() -> dict[str, str | None]:
    """The runtime variables a rejected operation must leave exactly as they were."""
    return {name: os.environ.get(name) for name in RUNTIME_ENV_NAMES}


def tree_snapshot(root: Path) -> dict[Path, bytes | None]:
    """Every path under ``root`` with its bytes — proof nothing was written."""
    return {path.relative_to(root): path.read_bytes() if path.is_file() else None for path in root.rglob("*")}


def forbid(monkeypatch, target, name: str, reason: str) -> None:
    """Make an attribute fail the test if the code under test ever reaches it."""

    def fail(*_args, **_kwargs):
        pytest.fail(reason)

    monkeypatch.setattr(target, name, fail)


def record_mkdir(monkeypatch) -> list[Path]:
    """Capture every ``Path.mkdir`` instead of performing it."""
    calls: list[Path] = []
    monkeypatch.setattr(Path, "mkdir", lambda self, *args, **kwargs: calls.append(self))
    return calls


def patch_clock(monkeypatch, module, *times: float, forbid_sleep: str | None = "this path must not wait on the real clock") -> None:
    """Freeze a module's ``time`` seam; by default any sleep fails the test."""
    values = iter(times or (0.0,))
    fallback = times[-1] if times else 0.0

    def fake_sleep(_seconds):
        if forbid_sleep is not None:
            pytest.fail(forbid_sleep)

    monkeypatch.setattr(module, "time", SimpleNamespace(time=lambda: next(values, fallback), sleep=fake_sleep))


class FakeProc:
    """``Popen`` stand-in: scripted ``poll()``, recorded waits and direct signals."""

    def __init__(self, pid: int, poll_results: list[int | None] | None = None, *, records_signals: bool = False):
        self.pid, self.returncode, self.poll_calls = pid, None, 0
        self.poll_results = iter(poll_results or [])
        self.wait_timeouts: list[float] = []
        self.signals: list[int] = []
        self._records_signals = records_signals

    def poll(self):
        self.poll_calls += 1
        result = next(self.poll_results, self.returncode)
        self.returncode = self.returncode if result is None else result
        return result

    def wait(self, timeout):
        self.wait_timeouts.append(timeout)
        return 0

    def send_signal(self, sig):
        assert self._records_signals, "the process-group signal must not fall back to the child process"
        self.signals.append(sig)


class FakeHealthResponse:
    """urllib-style readiness response usable as a context manager."""

    def __init__(self, status: int, headers: dict[str, str]):
        self.status = self.status_code = status
        self.headers = headers

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def lane_headers(lane_id: str | None) -> dict[str, str]:
    return {} if lane_id is None else {backend_config.TEST_LANE_HEADER: lane_id}


def httpx_lane_probe(lane_id: str | None, *, calls: list | None = None, on_call=None):
    """An ``httpx.get`` stand-in answering the helper's authenticated probe."""

    def fake_get(url, *, timeout, follow_redirects=False):
        if calls is not None:
            calls.append((url, timeout, follow_redirects))
        if on_call is not None:
            on_call()
        return SimpleNamespace(status_code=200, headers=lane_headers(lane_id))

    return fake_get


def patch_spawn(monkeypatch, *, process=None, holders=(), pgid=None, healthy=None) -> None:
    """Wire ``SharedTestServer.start()``'s external seams to in-memory fakes."""
    monkeypatch.setattr(test_runner_server, "port_holders", holders if callable(holders) else (lambda port=None: list(holders)))
    # The build step before the spawn (C-94) is otherwise a real `dev.py server --build-only`: it always succeeds here.
    monkeypatch.setattr(test_runner_server, "build_server_prerequisites", lambda *_args, **_kwargs: True, raising=False)
    if process is not None:
        monkeypatch.setattr(test_runner_server.subprocess, "Popen", lambda *_args, **_kwargs: process)
    if pgid is not None:
        monkeypatch.setattr(test_runner_server.os, "getpgid", pgid if callable(pgid) else (lambda _pid: pgid))
    if healthy is not None:
        monkeypatch.setattr(test_runner_server, "is_healthy", healthy if callable(healthy) else (lambda *_args, **_kwargs: healthy))


def record_stop(monkeypatch, server) -> list[tuple]:
    """Capture the ownership state visible to ``stop()`` without running it."""
    calls: list[tuple] = []
    monkeypatch.setattr(server, "stop", lambda: calls.append((server.proc, server.process_group_id, server.started_here)))
    return calls


def patch_manager_seams(monkeypatch, *, available: bool, holders, process_info: str | None = None, health=None) -> None:
    """Point ``_TestingServerManager`` at fake port-ownership and health seams."""
    module = test_server_helper_module
    monkeypatch.setattr(module, "shared_server_mode", lambda: False)
    monkeypatch.setattr(module, "check_port_available", lambda port: (available, process_info))
    monkeypatch.setattr(module, "port_holder_pids", lambda port: holders)
    if health is not None:
        monkeypatch.setattr(module.httpx, "get", health)


def patch_fake_server_thread(monkeypatch, *, alive: bool) -> list:
    """Replace Thread with a deterministic stand-in that never runs its target."""
    created: list = []

    class FakeThread:
        def __init__(self, *, target, daemon, name):
            self.target, self.daemon, self.name, self.started, self.alive = target, daemon, name, False, alive
            created.append(self)

        def start(self):
            self.started = True

        def is_alive(self):
            return self.alive

    monkeypatch.setattr(test_server_helper_module, "threading", SimpleNamespace(Thread=FakeThread))
    return created


def run_python_in_a_pipenv_child(code: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    """Run ``python -c code`` with ``env`` as the runner starts its children, through ``pipenv run``, never letting pipenv create an environment.

    In Docker, where ``pipenv_prefix()`` is empty because packages are installed system-wide, the child is this
    interpreter. Elsewhere ``pipenv run`` creates an empty virtualenv when the one it resolves does not exist, as in a
    worktree run without ``PIPENV_CUSTOM_VENV_NAME``. So pipenv is first asked, with the child's own environment, for
    ``pipenv --venv``, which prints the location or fails and never creates anything: unless it names the environment
    this interpreter runs in, the test is skipped and no ``pipenv run`` starts.
    """
    prefix = cli_base.pipenv_prefix()
    if prefix:
        if shutil.which(prefix[0]) is None:
            pytest.skip("pipenv is genuinely unavailable in this environment")
        venv = subprocess.run([prefix[0], "--venv"], cwd=cli_base.get_project_root(), env=env, capture_output=True, text=True, timeout=120)
        lines = venv.stdout.strip().splitlines()
        if venv.returncode != 0 or not lines or Path(lines[-1]).resolve() != Path(sys.prefix).resolve():
            pytest.skip(f"`pipenv run` here would not run this interpreter's environment ({sys.prefix}) and could create one: set PIPENV_CUSTOM_VENV_NAME")
    return subprocess.run([*prefix, "python" if prefix else sys.executable, "-c", code], cwd=cli_base.get_project_root(), env=env, capture_output=True, text=True, timeout=120)


def test_endpoint_listing_uses_lazy_openapi_operations_instead_of_route_markers(monkeypatch, capsys):
    class LazyOpenAPIApp:
        def __init__(self):
            self.openapi_calls = 0

        @property
        def routes(self):
            raise AssertionError("Endpoint listing must not inspect pre-OpenAPI route markers")

        def openapi(self):
            self.openapi_calls += 1
            return {
                "paths": {
                    "/api/v1/tools/catalog": {
                        "get": {"tags": ["Tools"], "summary": "List Tools"},
                        "parameters": [{"name": "ignored-path-parameter"}],
                    },
                    "/api/v1/tools/compute": {
                        "post": {"tags": ["Tools"], "description": "Run Tools\nMore detail"},
                    },
                    "/api/v1/tools/diagnostics": {
                        "get": {"tags": ["Tools"], "summary": "Inspect Tools"},
                    },
                    "/health": {
                        "head": {"description": "Health probe"},
                        "x-private": {"tags": ["Ignored"]},
                    },
                }
            }

    app = LazyOpenAPIApp()
    fake_main = ModuleType("backend.app.main")
    fake_main.app = app
    monkeypatch.setitem(sys.modules, "backend.app.main", fake_main)

    endpoint_listing.list_endpoints()

    output = capsys.readouterr().out
    assert app.openapi_calls == 1
    assert "[TOOLS]" in output
    assert "GET        /api/v1/tools/catalog" in output
    assert "POST       /api/v1/tools/compute" in output
    assert "GET        /api/v1/tools/diagnostics" in output
    assert output.count("/api/v1/tools/") == 3
    assert "[DEFAULT]" in output
    assert "HEAD       /health" in output
    assert "ignored-path-parameter" not in output
    assert "X-PRIVATE" not in output
    assert "Total endpoints: 4" in output


# ── Contracts 1 and 9 — data directories, production guards, markers ───────


def resolve_test_data_dir(runtime_env, resolver: str) -> Path:
    """Resolve the effective test data directory through one of the two resolvers."""
    if resolver == "backend":
        runtime_env.setenv("LIBREFOLIO_TEST_MODE", "1")
        return backend_config.get_data_dir()
    return cli_base.get_data_dir(test_mode=True)


def resolver_defaults(resolver: str) -> tuple[Path, Path]:
    """(project root, default test data dir), spelled the way that resolver spells them."""
    if resolver == "backend":
        return backend_config.PROJECT_ROOT, backend_config.DEFAULT_TEST_DATA_DIR
    root = cli_base.get_project_root()
    return root, root / cli_base.DEFAULT_TEST_DATA_DIR


def call_test_dir_entry_point(entry: str) -> None:
    """Call one resolving/destructive entry point for the configured test root."""
    if entry == "backend-get-data-dir":
        backend_config.get_data_dir()
    elif entry == "db-get-test-data-dir":
        test_db_config.get_test_data_dir()
    elif entry == "db-setup-test-database":
        test_db_config.setup_test_database()
    else:
        raise AssertionError(f"unknown entry point: {entry}")


def case_variant_alias() -> tuple[Path, Path]:
    """A case-swapped spelling of PROJECT_ROOT naming the very same directory.

    Case rewriting is identity on a case-insensitive volume (default macOS and
    Windows), so a guard comparing resolved paths as strings misses the alias.
    On a case-sensitive filesystem the spellings really are distinct paths, and
    the test skips instead of asserting something untrue there.
    """
    production_dir = backend_config.PROJECT_ROOT
    candidate = production_dir.with_name(production_dir.name.swapcase())
    try:
        alias = os.path.samefile(candidate, production_dir)
    except OSError:
        alias = False
    if not alias:
        pytest.skip("filesystem treats case variants as distinct paths")
    return production_dir, candidate


#: Mode 000 is how these tests make a folder untraversable: it denies nothing to root, and Windows has no POSIX mode.
needs_permission_denial = pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0, reason="mode 000 denies nothing to root, and Windows has no POSIX directory permissions")


@contextlib.contextmanager
def untraversable(folder: Path) -> Iterator[Path]:
    """``folder`` at mode 000 for the block: nothing in it can be listed, nor even looked up.

    Mode 0o700 comes back in a ``finally``, so ``tmp_path`` stays removable whatever the block raises. Where the mode
    still lets this user search the folder, there is no scenario to check, and the test is skipped rather than green.
    """
    folder.chmod(0o000)
    try:
        if os.access(folder, os.X_OK):
            pytest.skip("mode 000 does not deny this user the folder here: there is no untraversable folder to check")
        yield folder
    finally:
        folder.chmod(0o700)


def validation_refusal(test_root: Path, production_root: Path) -> ValueError:
    """The ``ValueError`` that ``validate_test_data_dir`` refuses ``test_root`` with: a raw ``OSError`` or a pass fails the test, saying which."""
    try:
        backend_config.validate_test_data_dir(test_root, production_data_dir=production_root)
    except ValueError as refusal:
        return refusal
    except OSError as raw:
        pytest.fail(f"validate_test_data_dir let a raw {type(raw).__name__} escape instead of refusing with a ValueError: {raw}")
    pytest.fail(f"validate_test_data_dir accepted {test_root}, which it could not verify: the guard must fail closed")


class TestDataDirResolution:
    #: The scheduler's lock across processes (Z-11), in the data directory beside ``scheduler_state.json``: spelled here,
    #: never read from its module, and pinned to ``run_lock.LOCK_FILE_NAME`` by a barrier test of this class (Z-24).
    SCHEDULER_LOCK = ".scheduler.lock"

    @pytest.mark.parametrize("resolver", ["backend", "cli"])
    @pytest.mark.parametrize("override", ["/isolated/lane-test-data", "runtime/lane-test-data", None], ids=["absolute", "relative", "default"])
    def test_test_data_dir_resolves_and_ignores_the_production_override(self, runtime_env, resolver, override):
        runtime_env.setenv("LIBREFOLIO_DATA_DIR", "/configured/production-data")
        if override is not None:
            runtime_env.setenv("LIBREFOLIO_TEST_DATA_DIR", override)
        project_root, default_test_dir = resolver_defaults(resolver)
        expected = default_test_dir if override is None else (Path(override) if Path(override).is_absolute() else project_root / override)

        assert resolve_test_data_dir(runtime_env, resolver) == expected

    @pytest.mark.parametrize("marker", ["?", "#"])
    @pytest.mark.parametrize("resolver", ["backend-production", "backend-test", "cli"])
    def test_rejects_url_metacharacters_in_the_raw_override(self, runtime_env, resolver, marker):
        raw = f"runtime/lane-data{marker}lane"
        if resolver == "backend-test":
            runtime_env.setenv("LIBREFOLIO_TEST_MODE", "1")
            runtime_env.setenv("LIBREFOLIO_TEST_DATA_DIR", raw)
        elif resolver == "backend-production":
            runtime_env.setenv("LIBREFOLIO_TEST_MODE", "0")
            runtime_env.setenv("LIBREFOLIO_DATA_DIR", raw)

        with pytest.raises(ValueError, match=RAW_METACHAR_ERROR):
            cli_base.resolve_data_dir(raw) if resolver == "cli" else backend_config.get_data_dir()

    @pytest.mark.parametrize("marker", ["?", "#"])
    @pytest.mark.parametrize("resolver", ["backend", "cli"])
    def test_rejects_a_metacharacter_reached_only_through_a_symlink(self, tmp_path, resolver, marker):
        # A delimiter-free path can still *resolve* into a target whose canonical
        # spelling carries '?' or '#'; the raw-string check alone would miss it.
        target = tmp_path / f"synthetic-target{marker}lane"
        target.mkdir()
        link = tmp_path / "delimiter-free-link"
        link.symlink_to(target, target_is_directory=True)
        assert marker not in str(link)

        with pytest.raises(ValueError, match=RESOLVED_METACHAR_ERROR):
            cli_base.resolve_data_dir(link) if resolver == "cli" else backend_config._resolve_data_dir(link)

    @pytest.mark.parametrize("production_source", ["canonical", "configured"])
    @pytest.mark.parametrize("direction", ["production-ancestor", "production-child"])
    def test_rejects_overlap_in_either_ancestor_direction(self, runtime_env, tmp_path, production_source, direction):
        production_dir = backend_config.DEFAULT_PROD_DATA_DIR if production_source == "canonical" else tmp_path / "production"
        candidate = production_dir / "test-lane" if direction == "production-ancestor" else production_dir.parent
        kwargs = {} if production_source == "canonical" else {"production_data_dir": production_dir}

        with pytest.raises(ValueError, match=OVERLAP_ERROR):
            backend_config.validate_test_data_dir(candidate, **kwargs)

    def test_siblings_sharing_only_a_parent_are_not_rejected(self, runtime_env):
        production_dir = backend_config.PROJECT_ROOT / "runtime" / "sibling-production-data"
        candidate = backend_config.PROJECT_ROOT / "runtime" / "sibling-test-data"

        assert backend_config.validate_test_data_dir(candidate, production_data_dir=production_dir) == candidate

    def test_test_default_is_rejected_when_production_is_configured_onto_it(self, runtime_env):
        runtime_env.setenv("LIBREFOLIO_TEST_MODE", "1")
        runtime_env.setenv("LIBREFOLIO_DATA_DIR", str(backend_config.DEFAULT_TEST_DATA_DIR))

        with pytest.raises(ValueError, match=OVERLAP_ERROR):
            backend_config.get_data_dir()

    @pytest.mark.parametrize("entry", ["backend-get-data-dir", "db-get-test-data-dir", "db-setup-test-database"])
    @pytest.mark.parametrize("alias", ["canonical", "configured", "case-variant"])
    def test_a_production_alias_is_rejected_by_every_entry_point_before_mutation(self, runtime_env, monkeypatch, entry, alias):
        # configure_test_runtime() is the guard `dev.py test` goes through, but
        # test_db_config is importable — and destructive — by anything at all.
        if alias == "canonical":
            candidate = backend_config.DEFAULT_PROD_DATA_DIR
        elif alias == "configured":
            runtime_env.setenv("LIBREFOLIO_DATA_DIR", "runtime/configured-production-data")
            candidate = backend_config.PROJECT_ROOT / "runtime/configured-production-data"
        else:
            production_dir, candidate = case_variant_alias()
            runtime_env.setenv("LIBREFOLIO_DATA_DIR", str(production_dir))
        runtime_env.setenv("LIBREFOLIO_TEST_DATA_DIR", str(candidate))
        if entry == "backend-get-data-dir":
            runtime_env.setenv("LIBREFOLIO_TEST_MODE", "1")
        mkdir_calls, before = record_mkdir(monkeypatch), runtime_state()
        with pytest.raises(ValueError):
            call_test_dir_entry_point(entry)

        assert (mkdir_calls, runtime_state()) == ([], before)

    def test_fresh_nonexistent_case_variant_is_rejected_without_creating_anything(self, runtime_env):
        case_variant_alias()  # decides applicability on this filesystem
        pairs = ((backend_config.PROJECT_ROOT / f".runtime-isolation-prod-{n}", backend_config.PROJECT_ROOT / f".RUNTIME-ISOLATION-PROD-{n}") for n in range(1000))
        production_dir, candidate = next((pair for pair in pairs if not pair[0].exists() and not pair[1].exists()), (None, None))
        assert production_dir is not None, "could not find a fresh case-variant path pair"
        runtime_env.setenv("LIBREFOLIO_TEST_MODE", "1")
        runtime_env.setenv("LIBREFOLIO_DATA_DIR", str(production_dir))
        runtime_env.setenv("LIBREFOLIO_TEST_DATA_DIR", str(candidate))
        with pytest.raises(ValueError, match=OVERLAP_ERROR):
            backend_config.get_data_dir()

        assert not production_dir.exists() and not candidate.exists()

    @pytest.mark.parametrize("managed_relative", ["sqlite", "sqlite/app.db", "secrets", "secrets/instance.key", "backups", ".restore", "scheduler_state.json", SCHEDULER_LOCK])
    def test_managed_symlink_escaping_into_another_root_is_rejected_before_mutation(self, runtime_env, tmp_path, managed_relative):
        # Both roots are synthetic: the only thing under test is whether the guard
        # resolves symlinks instead of comparing unresolved path strings.
        production_root, test_root, relative = tmp_path / "synthetic-production-data", tmp_path / "synthetic-test-data", Path(managed_relative)
        production_target = production_root / relative
        production_target.parent.mkdir(parents=True, exist_ok=True)
        production_target.write_bytes(b"") if relative.suffix else production_target.mkdir(parents=True, exist_ok=True)
        candidate_link = test_root / relative
        candidate_link.parent.mkdir(parents=True, exist_ok=True)
        candidate_link.symlink_to(production_target, target_is_directory=production_target.is_dir())
        runtime_env.setenv("LIBREFOLIO_DATA_DIR", str(production_root))
        runtime_env.setenv("PORT", "6198")
        before = runtime_state()
        with pytest.raises(ValueError, match=f"^{re.escape(f'Test data path escapes its configured root: {relative}')}$"):
            cli_base.configure_test_runtime(port=6199, data_dir=str(test_root))

        assert runtime_state() == before

    @pytest.mark.parametrize("managed_file", ["sqlite/app.db", "secrets/instance.key", "scheduler_state.json", SCHEDULER_LOCK])
    def test_a_managed_file_hardlinked_to_production_is_rejected_before_mutation(self, runtime_env, tmp_path, managed_file):
        # A hard link resolves to itself, so it never escapes its root: only the identity check (samefile) sees that the
        # test file is the production one. Both roots are synthetic, and the folders above the file are distinct real
        # folders in each, so the file is the one aliased path and the refusal must name it.
        production_root, test_root, relative = tmp_path / "synthetic-production-data", tmp_path / "synthetic-test-data", Path(managed_file)
        production_file, test_file = production_root / relative, test_root / relative
        production_file.parent.mkdir(parents=True, exist_ok=True)
        production_file.write_bytes(b"")
        test_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(production_file, test_file)
        except OSError as refused:
            pytest.skip(f"this filesystem refuses hard links ({refused}): there is no aliased file to refuse")
        runtime_env.setenv("LIBREFOLIO_DATA_DIR", str(production_root))
        runtime_env.setenv("PORT", "6198")
        before = runtime_state()
        with pytest.raises(ValueError, match=f"^{re.escape(f'Test data path aliases production data: {relative}')}$"):
            cli_base.configure_test_runtime(port=6199, data_dir=str(test_root))

        assert runtime_state() == before

    def test_the_scheduler_lock_named_here_is_the_one_the_scheduler_takes(self):
        # The cases above and the guard's managed paths spell Z-11's lock file: were its constant to move, they would
        # guard a file nobody locks, and leave the real lock unguarded. The constant is read from the module's source
        # text, never imported: the import runs the scheduler package's __init__, which loads its loop and the DB models,
        # over a thousand modules, into this pure unit.
        relative = Path("backend/app/services/platform/scheduler/run_lock.py")
        module = ast.parse((backend_config.PROJECT_ROOT / relative).read_text(encoding="utf-8"), filename=str(relative))
        values = [
            statement.value
            for statement in module.body
            if (isinstance(statement, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "LOCK_FILE_NAME" for target in statement.targets))
            or (isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name) and statement.target.id == "LOCK_FILE_NAME" and statement.value is not None)
        ]
        if not values:
            pytest.fail(f"{relative} has no top-level assignment of LOCK_FILE_NAME, plain or annotated: there is no name of the scheduler's lock file to compare")
        name = values[-1]  # run top to bottom, the module keeps the last one
        if not (isinstance(name, ast.Constant) and isinstance(name.value, str)):
            pytest.fail(f"{relative} assigns LOCK_FILE_NAME = {ast.unparse(name)}, not a string literal: the barrier reads the source and never runs it")

        assert name.value == self.SCHEDULER_LOCK, f"{relative} now names the scheduler's lock {name.value!r}: the guard's managed paths and the cases of this class must name it instead of {self.SCHEDULER_LOCK!r}"

    @needs_permission_denial
    @pytest.mark.parametrize("managed_file", ["sqlite/app.db", "secrets/instance.key"], ids=["sqlite", "secrets"])
    def test_an_untraversable_managed_folder_is_refused_with_a_value_error(self, runtime_env, tmp_path, managed_file):
        # H-4: the subtree scan skips a folder it cannot list, so the managed path inside it is the first one the guard
        # cannot look up. Both roots are synthetic, the canonical production root included.
        production_root, test_root, relative = tmp_path / "synthetic-production-data", tmp_path / "synthetic-test-data", Path(managed_file)
        production_root.mkdir()
        (test_root / relative.parent).mkdir(parents=True)
        (test_root / relative).write_bytes(b"")
        runtime_env.setattr(backend_config, "DEFAULT_PROD_DATA_DIR", production_root)
        with untraversable(test_root / relative.parent):
            refusal = validation_refusal(test_root, production_root)

        assert str(refusal).startswith(f"Cannot verify test data path: {relative}"), f"the refusal must name the managed path it could not check: {refusal}"
        assert isinstance(refusal.__cause__, PermissionError), f"the refusal must be chained from the OSError it turns into a ValueError, not from {refusal.__cause__!r}"

    @needs_permission_denial
    def test_an_untraversable_test_root_is_refused_with_a_value_error(self, runtime_env, tmp_path):
        # H-4, the production-marker check: a root nobody can search could hold a marker nobody can see.
        production_root, test_root = tmp_path / "synthetic-production-data", tmp_path / "synthetic-test-data"
        production_root.mkdir()
        test_root.mkdir()
        runtime_env.setattr(backend_config, "DEFAULT_PROD_DATA_DIR", production_root)
        with untraversable(test_root):
            refusal = validation_refusal(test_root, production_root)

        assert str(refusal).startswith("Cannot verify the test data directory"), f"the refusal must say the directory itself could not be checked: {refusal}"
        assert isinstance(refusal.__cause__, PermissionError), f"the refusal must be chained from the OSError it turns into a ValueError, not from {refusal.__cause__!r}"

    @pytest.mark.parametrize(("test_mode", "expected_marker"), [(False, True), (True, False)], ids=["production", "test"])
    def test_ensure_data_dirs_marks_only_a_synthetic_production_root(self, runtime_env, tmp_path, test_mode, expected_marker):
        production_root, test_root = tmp_path / "synthetic-production-data", tmp_path / "synthetic-test-data"
        runtime_env.setattr(backend_config, "DEFAULT_PROD_DATA_DIR", production_root)
        runtime_env.setattr(backend_config, "DEFAULT_TEST_DATA_DIR", test_root)
        runtime_env.setenv("LIBREFOLIO_TEST_MODE", "1" if test_mode else "0")
        runtime_env.setenv("LIBREFOLIO_DATA_DIR", str(production_root))
        runtime_env.setenv("LIBREFOLIO_TEST_DATA_DIR", str(test_root))
        backend_config.ensure_data_dirs()

        production_marker = production_root / backend_config.PRODUCTION_DATA_MARKER
        assert production_marker.exists() is expected_marker
        assert not (test_root / backend_config.PRODUCTION_DATA_MARKER).exists()
        if expected_marker:
            assert production_marker.read_text(encoding="utf-8") == "LibreFolio production data root\n"

    def test_test_db_config_derivatives_follow_override_changes(self, runtime_env):
        for override in (Path("/isolated/db-config-first"), Path("/isolated/db-config-second")):
            # Same process, same already-imported module — only the env var moves.
            runtime_env.setenv("LIBREFOLIO_TEST_DATA_DIR", str(override))

            assert test_db_config.get_test_data_dir() == override
            assert test_db_config.get_test_db_path() == override / "sqlite" / "app.db"
            assert test_db_config.get_test_database_url() == f"sqlite:///{override / 'sqlite' / 'app.db'}"


# ── Contract 2 — lane runtime configuration: ports, dotenv, exports, lane id ──


class TestConfigureTestRuntime:
    @pytest.mark.parametrize("port", [1, 6123, 65535])
    def test_explicit_valid_port_is_written_and_returned(self, runtime_env, port):
        runtime_env.setenv("LIBREFOLIO_TEST_MODE", "0")
        configured_port, _ = cli_base.configure_test_runtime(port=port)

        assert configured_port == port
        assert os.environ["TEST_PORT"] == str(port)
        assert os.environ["LIBREFOLIO_TEST_MODE"] == "1"

    @pytest.mark.parametrize("port", [0, 65536])
    def test_invalid_port_boundaries_are_rejected_without_mutation(self, runtime_env, port):
        before = runtime_state()
        with pytest.raises(ValueError):
            cli_base.configure_test_runtime(port=port)

        assert runtime_state() == before

    @pytest.mark.parametrize("seam", ["shell", "dotenv"])
    def test_test_port_equal_to_the_configured_production_port_is_rejected(self, runtime_env, seam):
        # The production port is the *effective configured* one, never the
        # hardcoded 6040 — and through the dotenv seam it must be the same
        # effective value get_server_port() would read, not merely os.environ.
        port = 6099 if seam == "shell" else 6098
        if seam == "shell":
            runtime_env.setenv("PORT", str(port))
        else:
            runtime_env.setattr(cli_base, "_project_dotenv_values", lambda: {"PORT": str(port)})
        before = runtime_state()
        with pytest.raises(ValueError, match="^Test port must not be the production server port$"):
            cli_base.configure_test_runtime(port=port, data_dir="runtime/production-port-guard-test-data")

        assert runtime_state() == before

    @pytest.mark.parametrize("data_dir", ["/isolated/configured-test-data", "runtime/configured-test-data"], ids=["absolute", "relative"])
    def test_explicit_data_dir_is_resolved_written_and_returned(self, runtime_env, data_dir):
        configured_port, configured_dir = cli_base.configure_test_runtime(data_dir=data_dir)

        expected = Path(data_dir) if Path(data_dir).is_absolute() else cli_base.get_project_root() / data_dir
        assert (configured_port, configured_dir) == (cli_base.get_test_server_port(), expected)
        assert os.environ["LIBREFOLIO_TEST_DATA_DIR"] == str(expected)

    @pytest.mark.parametrize("alias", ["canonical-relative", "canonical-absolute", "configured", "tilde-configured"])
    def test_production_data_dir_is_rejected_before_mutation(self, runtime_env, alias):
        if alias.startswith("canonical"):
            production_dir = cli_base.get_project_root() / cli_base.DEFAULT_PROD_DATA_DIR
            candidate = cli_base.DEFAULT_PROD_DATA_DIR if alias.endswith("relative") else str(production_dir)
        elif alias == "configured":
            runtime_env.setenv("LIBREFOLIO_DATA_DIR", "runtime/configured-production-data")
            candidate = str(cli_base.get_project_root() / "runtime/configured-production-data")
        else:
            # A tilde spelling must still alias the expanded production path.
            probe = "librefolio-runtime-isolation-tilde-probe/prod-alias"
            runtime_env.setenv("LIBREFOLIO_DATA_DIR", f"~/{probe}")
            candidate = str(Path.home() / probe)
        before = runtime_state()
        with pytest.raises(ValueError):
            cli_base.configure_test_runtime(data_dir=candidate)

        assert runtime_state() == before

    @pytest.mark.parametrize("marker_location", ["candidate", "ancestor"])
    def test_marked_synthetic_production_root_is_rejected_before_mutation(self, runtime_env, tmp_path, marker_location):
        marked_root = tmp_path / "synthetic-marked-production-data"
        candidate = marked_root if marker_location == "candidate" else marked_root / "test-lane"
        marked_root.mkdir()
        marker, marker_content = marked_root / backend_config.PRODUCTION_DATA_MARKER, "synthetic production marker\n"
        marker.write_text(marker_content, encoding="utf-8")
        candidate_existed = candidate.exists()
        runtime_env.setattr(backend_config, "DEFAULT_PROD_DATA_DIR", tmp_path / "synthetic-canonical-production-data")
        runtime_env.setenv("LIBREFOLIO_DATA_DIR", str(tmp_path / "separate-synthetic-production-data"))
        before = runtime_state()
        with pytest.raises(ValueError, match=MARKED_ERROR):
            cli_base.configure_test_runtime(port=6199, data_dir=candidate)

        assert runtime_state() == before
        assert candidate.exists() is candidate_existed
        assert marker.read_text(encoding="utf-8") == marker_content

    @pytest.mark.parametrize("source", ["shell", "defaults", "dotenv"])
    def test_no_args_normalizes_and_exports_the_effective_lane(self, runtime_env, source):
        # A lane with no explicit --test-port/--data-dir still forks children that
        # inherit os.environ, not this function's return value: the effective
        # values must land there even when they are only defaults. The probes are
        # not LIBREFOLIO_* names, which a lane drops unless it keeps them.
        shell_probe, hydrated_probe = "RUNTIME_ISOLATION_SHELL_PROBE", "RUNTIME_ISOLATION_DOTENV_PROBE"
        dotenv_values: dict[str, str] = {}
        if source == "shell":
            runtime_env.setenv("TEST_PORT", "06124")
            runtime_env.setenv("LIBREFOLIO_TEST_DATA_DIR", "runtime/existing-test-data")
            expected_port, relative = 6124, "runtime/existing-test-data"
        elif source == "dotenv":
            dotenv_values = {"TEST_PORT": "06129", "LIBREFOLIO_TEST_DATA_DIR": "runtime/dotenv-test-data", shell_probe: "from-dotenv", hydrated_probe: "hydrated-from-dotenv"}
            expected_port, relative = 6129, "runtime/dotenv-test-data"
        else:
            expected_port, relative = cli_base.get_test_server_port(), cli_base.DEFAULT_TEST_DATA_DIR
        runtime_env.setenv(shell_probe, "from-shell")
        runtime_env.delenv(hydrated_probe, raising=False)
        runtime_env.setattr(cli_base, "_project_dotenv_values", lambda: dict(dotenv_values))
        configured = cli_base.configure_test_runtime()

        expected_dir = cli_base.get_project_root() / relative
        assert configured == (expected_port, expected_dir)
        assert os.environ["TEST_PORT"] == str(expected_port)
        assert os.environ["LIBREFOLIO_TEST_DATA_DIR"] == str(expected_dir)
        assert os.environ["LIBREFOLIO_TEST_MODE"] == "1"
        # Hydration fills only what the shell left unset; it never overwrites it.
        hydrated = os.environ.get(hydrated_probe)
        assert os.environ[shell_probe] == "from-shell"
        assert hydrated == ("hydrated-from-dotenv" if source == "dotenv" else None)

    def test_explicit_lane_args_win_over_dotenv_values(self, runtime_env):
        runtime_env.setattr(cli_base, "_project_dotenv_values", lambda: {"TEST_PORT": "6041", "LIBREFOLIO_TEST_DATA_DIR": "runtime/dotenv-test-data"})
        configured = cli_base.configure_test_runtime(port=6134, data_dir="runtime/explicit-lane-test-data")

        expected_dir = cli_base.get_project_root() / "runtime/explicit-lane-test-data"
        assert configured == (6134, expected_dir)
        assert os.environ["TEST_PORT"] == "6134"
        assert os.environ["LIBREFOLIO_TEST_DATA_DIR"] == str(expected_dir)

    def test_exports_the_pipenv_dotenv_guard_and_one_stable_lane_id(self, runtime_env):
        cli_base.configure_test_runtime(port=6132, data_dir="runtime/stable-lane-id-test-data")
        lane_id = os.environ["LIBREFOLIO_TEST_LANE_ID"]
        assert os.environ["PIPENV_DONT_LOAD_ENV"] == "1"
        assert lane_id
        cli_base.configure_test_runtime(port=6132, data_dir="runtime/stable-lane-id-test-data")

        assert os.environ["LIBREFOLIO_TEST_LANE_ID"] == lane_id


class TestTestLaneSecrets:
    """A test lane signs sessions and derives keys with secrets of its own, never with the instance's.

    ``configure_test_runtime`` removes every name of ``INSTANCE_TRUST_SECRETS`` from the environment the lane exports,
    whether the shell or the dotenv file provided it, and a rejected lane changes nothing, those names included. The
    dotenv file is a synthetic one in ``tmp_path``, named by ``PIPENV_DOTENV_LOCATION``; a probe variable in it proves
    the file was loaded, so the absence of the secrets after loading it means something.
    """

    #: Not a LIBREFOLIO_* name, which a lane drops unless it keeps it: hydrated from the dotenv file and left there.
    DOTENV_PROBE = "RUNTIME_ISOLATION_LANE_SECRETS_PROBE"
    LANE_PORT = 6197

    @staticmethod
    def instance_values() -> dict[str, str]:
        return {name: f"instance-value-of-{name}" for name in backend_config.INSTANCE_TRUST_SECRETS}

    @staticmethod
    def exported() -> dict[str, str | None]:
        return {name: os.environ.get(name) for name in backend_config.INSTANCE_TRUST_SECRETS}

    def use_dotenv(self, runtime_env, tmp_path: Path, values: dict[str, str]) -> None:
        """Point the dotenv loader at a synthetic file holding ``values`` and the probe, and nothing else."""
        dotenv_file = tmp_path / "lane-secrets.env"
        dotenv_file.write_text("".join(f"{name}={value}\n" for name, value in {self.DOTENV_PROBE: "hydrated-from-dotenv", **values}.items()), encoding="utf-8")
        runtime_env.setenv("PIPENV_DOTENV_LOCATION", str(dotenv_file))
        runtime_env.delenv(self.DOTENV_PROBE, raising=False)

    def test_the_session_signing_key_is_a_trust_secret(self):
        assert "JWT_SECRET" in backend_config.INSTANCE_TRUST_SECRETS, f"JWT_SECRET must be among the secrets a test lane never inherits: {backend_config.INSTANCE_TRUST_SECRETS}"

    @pytest.mark.parametrize("source", ["shell", "dotenv"])
    def test_a_configured_lane_inherits_none_of_the_instance_secrets(self, runtime_env, tmp_path, source):
        values = self.instance_values()
        if source == "shell":
            for name, value in values.items():
                runtime_env.setenv(name, value)
            self.use_dotenv(runtime_env, tmp_path, {})
        else:
            for name in values:
                runtime_env.delenv(name, raising=False)
            self.use_dotenv(runtime_env, tmp_path, values)

        configured = cli_base.configure_test_runtime(port=self.LANE_PORT, data_dir=tmp_path / "lane-data")

        probe = os.environ.get(self.DOTENV_PROBE)
        assert configured == (self.LANE_PORT, (tmp_path / "lane-data").resolve())
        assert probe == "hydrated-from-dotenv", "the synthetic dotenv file was not loaded, so the absence below would prove nothing"
        inherited = sorted(name for name, value in self.exported().items() if value is not None)
        assert not inherited, f"the test lane kept secrets of the instance from the {source}: {inherited}"
        assert os.environ["PIPENV_DONT_LOAD_ENV"] == "1", "a nested pipenv run must not load the dotenv file again, or the removed secrets come back"

    @pytest.mark.parametrize("lane", [pytest.param({"port": 0}, id="invalid-port"), pytest.param({"port": LANE_PORT, "data_dir": cli_base.DEFAULT_PROD_DATA_DIR}, id="production-data-dir")])
    def test_a_rejected_lane_leaves_the_instance_secrets_untouched(self, runtime_env, tmp_path, lane):
        for name, value in self.instance_values().items():
            runtime_env.setenv(name, value)
        self.use_dotenv(runtime_env, tmp_path, {})
        before = runtime_state(), self.exported()

        with pytest.raises(ValueError):
            cli_base.configure_test_runtime(**lane)

        assert (runtime_state(), self.exported()) == before


# ── Contract 2b — a test lane runs on the instance's defaults ──────────────

#: Read by the tests below on their own, not through ``cli_base``: a variable ``.env.example`` comes to document is
#: covered here with no list to update.
ENV_EXAMPLE = backend_config.PROJECT_ROOT / ".env.example"


def env_example_variables() -> frozenset[str]:
    """Every variable ``.env.example`` documents, commented out or not, read independently of ``cli_base``.

    A variable line, once a leading ``#`` and the blanks after it are set aside, is ``NAME=...`` with ``NAME`` an
    upper-case ASCII identifier: prose such as ``# For manual builds: UID=$(id -u) ...`` is not one.
    """
    names = set()
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        text = line[1:].lstrip() if line.startswith("#") else line
        name, equals, _ = text.partition("=")
        if equals and name.isascii() and name.isidentifier() and name == name.upper():
            names.add(name)
    return frozenset(names)


def environment_changes(before: dict[str, str]) -> dict[str, tuple[str | None, str | None]]:
    """The variables whose value differs from ``before``, as ``(before, now)``: a failure shows those, not the environment."""
    now = dict(os.environ)
    return {name: (before.get(name), now.get(name)) for name in sorted(before.keys() | now.keys()) if before.get(name) != now.get(name)}


class TestTestLaneRunsOnTheInstanceDefaults:
    """Of the developer's configuration, dotenv file or shell, a test lane keeps what ``kept_in_a_test_lane`` keeps.

    ``configure_test_runtime`` hydrates the dotenv file without overwriting the shell, then removes every variable
    ``.env.example`` documents, the instance's secrets and every ``LIBREFOLIO_*`` name, whichever of the two provided
    them, but ``TEST_LANE_KEEPS`` and the ``LIBREFOLIO_TEST_*`` names: of those the lane's own value wins, then the
    shell's, then the dotenv file's. A variable of another program (a proxy, ``PYTHONPATH``) is not the instance's
    configuration and stays, hydrated from the dotenv file when the shell lacks it. The documented variables come from
    ``env_example_variables()``, so a new one is covered as soon as ``.env.example`` lists it.

    The dotenv file is a synthetic one in ``tmp_path``, named by ``PIPENV_DOTENV_LOCATION``. Where an absence is asserted
    it also holds names the lane keeps: finding them hydrated proves the file was read. A value set in the shell stands
    for an export of the developer as much as for the copy of the dotenv file that ``pipenv run`` puts in the
    environment of the command it starts.
    """

    LANE_PORT = 6185
    #: ``PORT`` and ``TEST_PORT`` of the instance, by origin: valid ports, none of them the lane's.
    PORTS = {"instance": ("6186", "6187"), "dotenv": ("6188", "6189"), "shell": ("6190", "6191")}
    #: ``LIBREFOLIO_TEST_*`` names the runner and the tests read, kept by their prefix: the lane's data directory and
    #: mode (which the lane then sets), its readiness token, the startup timeout of its servers, the shared-server flag.
    KEPT_BY_PREFIX = ("LIBREFOLIO_TEST_DATA_DIR", "LIBREFOLIO_TEST_MODE", "LIBREFOLIO_TEST_LANE_ID", "LIBREFOLIO_TEST_STARTUP_TIMEOUT", "LIBREFOLIO_TEST_SHARED_SERVER")
    #: A LibreFolio variable ``.env.example`` does not document (yet).
    UNDOCUMENTED = "LIBREFOLIO_NOT_YET_DOCUMENTED_SMTP_PASSWORD"
    #: Variables of other programs: the first in the developer's dotenv file only, the second in both, exported as well.
    OTHER_PROGRAMS = ("HTTP_PROXY", "HTTPS_PROXY")

    @pytest.fixture
    def lane(self, runtime_env, tmp_path) -> SimpleNamespace:
        """The lane the runner configures, in an environment holding no ``LIBREFOLIO_*`` name and none of the names set here."""
        names = env_example_variables() | cli_base.TEST_LANE_KEEPS | set(backend_config.INSTANCE_TRUST_SECRETS) | {*self.KEPT_BY_PREFIX, self.UNDOCUMENTED, *self.OTHER_PROGRAMS}
        for name in names | {name for name in os.environ if name.startswith("LIBREFOLIO_")}:
            runtime_env.delenv(name, raising=False)
        return SimpleNamespace(port=self.LANE_PORT, data_dir=tmp_path / "lane-data", env=runtime_env, tmp_path=tmp_path)

    def values(self, lane, origin: str, names) -> dict[str, str]:
        """A value of ``origin`` for each name: a sentinel, but a valid port or directory for the keeps the runner reads."""
        port, test_port = self.PORTS[origin]
        valid = {"PORT": port, "TEST_PORT": test_port, "LIBREFOLIO_DATA_DIR": str(lane.tmp_path / f"{origin}-production-data"), "LIBREFOLIO_TEST_DATA_DIR": str(lane.tmp_path / f"{origin}-test-data")}
        return {name: valid.get(name, f"{origin}-value-of-{name}") for name in sorted(names)}

    @staticmethod
    def configure_instance(lane, *, dotenv: dict[str, str], shell: dict[str, str]) -> None:
        """Write ``dotenv`` to the synthetic dotenv file and export ``shell``."""
        dotenv_file = lane.tmp_path / "instance.env"
        dotenv_file.write_text("".join(f"{name}={value}\n" for name, value in dotenv.items()), encoding="utf-8")
        lane.env.setenv("PIPENV_DOTENV_LOCATION", str(dotenv_file))
        for name, value in shell.items():
            lane.env.setenv(name, value)

    @staticmethod
    def lane_exports(lane) -> dict[str, str]:
        """What ``configure_test_runtime`` itself sets, among the names these tests look at."""
        return {"TEST_PORT": str(lane.port), "LIBREFOLIO_TEST_DATA_DIR": str(lane.data_dir.resolve()), "LIBREFOLIO_TEST_MODE": "1"}

    @staticmethod
    def present(names) -> dict[str, str]:
        """The names the environment holds, with their values."""
        return {name: os.environ[name] for name in sorted(names) if name in os.environ}

    @staticmethod
    def pipenv_child(env: dict[str, str], names) -> dict[str, str | None]:
        """What a ``pipenv run python -c`` child started with ``env`` holds of ``names``: the probe only prints them."""
        probe = f"import json, os; print(json.dumps({{name: os.environ.get(name) for name in {sorted(names)!r}}}))"
        result = run_python_in_a_pipenv_child(probe, env)
        lines = result.stdout.strip().splitlines()
        assert result.returncode == 0 and lines, f"the pipenv run child failed: exit {result.returncode}, stderr={result.stderr[-2000:]!r}"
        return json.loads(lines[-1])

    def test_the_documented_variables_are_those_env_example_holds(self):
        documented = env_example_variables()
        from_cli = cli_base.documented_instance_variables()

        # Presence barriers: both kinds of variable line are read
        assert {"HOST", "PORT", "LOG_LEVEL", "PREVIEW_CACHE_MAX_MB"} <= documented, f"uncommented variable lines were not read: {sorted(documented)}"
        assert {"JWT_SECRET", "LIBREFOLIO_PROFILE", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_TEST_MODE"} <= documented, f"commented variable lines were not read: {sorted(documented)}"
        assert from_cli == documented, f"documented_instance_variables() and .env.example disagree: only in the first {sorted(from_cli - documented)}, only in the file {sorted(documented - from_cli)}"

    @pytest.mark.parametrize("origin", [pytest.param("dotenv", id="dotenv-file-and-shell"), pytest.param("shell", id="shell-only")])
    def test_no_documented_variable_reaches_the_lane_but_the_kept_ones(self, lane, origin):
        documented = env_example_variables()
        instance = self.values(lane, "instance", documented)
        kept = {name: value for name, value in instance.items() if cli_base.kept_in_a_test_lane(name)}
        dropped = {name: value for name, value in instance.items() if not cli_base.kept_in_a_test_lane(name)}
        if origin == "dotenv":
            # Every one in the developer's dotenv file, and every second one of those to drop exported as well
            self.configure_instance(lane, dotenv=instance, shell={name: dropped[name] for name in sorted(dropped)[::2]})
        else:
            # Those to drop exported only: the dotenv file holds the kept ones alone
            self.configure_instance(lane, dotenv=kept, shell=dropped)

        configured = cli_base.configure_test_runtime(port=lane.port, data_dir=lane.data_dir)

        exports = self.lane_exports(lane)
        reached_kept, reached_dropped = self.present(kept), self.present(dropped)
        assert configured == (lane.port, lane.data_dir.resolve())
        assert reached_kept == {name: exports.get(name, value) for name, value in kept.items()}, "the kept variables come from the dotenv file, the lane's own values over it: without them the absences below prove nothing"
        assert not reached_dropped, f"documented variables of the instance reached the lane from the {origin}: {sorted(reached_dropped)}"

    @pytest.mark.parametrize("origin", [pytest.param("dotenv", id="dotenv-file-only"), pytest.param("both", id="dotenv-file-and-shell"), pytest.param("shell", id="shell-only")])
    def test_an_undocumented_librefolio_variable_is_dropped_wherever_it_comes_from(self, lane, origin):
        assert self.UNDOCUMENTED not in env_example_variables() and not cli_base.kept_in_a_test_lane(self.UNDOCUMENTED), "the probe must be a LibreFolio name neither documented nor kept"
        kept = self.values(lane, "instance", cli_base.TEST_LANE_KEEPS)
        undocumented = self.values(lane, "instance", {self.UNDOCUMENTED})
        self.configure_instance(lane, dotenv={**kept, **(undocumented if origin != "shell" else {})}, shell=undocumented if origin != "dotenv" else {})

        cli_base.configure_test_runtime(port=lane.port, data_dir=lane.data_dir)

        hydrated_names = cli_base.TEST_LANE_KEEPS - self.lane_exports(lane).keys()
        hydrated, left = self.present(hydrated_names), self.present({self.UNDOCUMENTED})
        assert hydrated == {name: kept[name] for name in hydrated_names}, "the dotenv file was not hydrated, so the absence below would prove nothing"
        assert not left, f"{self.UNDOCUMENTED} must be dropped from the {origin}: every LIBREFOLIO_* name is, but those kept_in_a_test_lane keeps"

    def test_a_variable_of_another_program_stays_hydrated_from_the_dotenv_file(self, lane):
        """A proxy or ``PYTHONPATH`` in the developer's dotenv file or shell is not the instance's configuration: it stays."""
        dotenv_only, exported = self.OTHER_PROGRAMS
        dotenv = self.values(lane, "dotenv", self.OTHER_PROGRAMS)
        shell = self.values(lane, "shell", {exported})
        for name in self.OTHER_PROGRAMS:
            assert not name.startswith("LIBREFOLIO_") and name not in env_example_variables() | set(backend_config.INSTANCE_TRUST_SECRETS), f"{name} must be neither LibreFolio's nor documented nor a secret"
        self.configure_instance(lane, dotenv=dotenv, shell=shell)

        cli_base.configure_test_runtime(port=lane.port, data_dir=lane.data_dir)

        left = self.present(self.OTHER_PROGRAMS)
        assert left == {dotenv_only: dotenv[dotenv_only], exported: shell[exported]}, "a variable of another program stays: hydrated from the dotenv file when the shell lacks it, the shell's value over the file's"

    @pytest.mark.parametrize("origin", ["dotenv", "shell"])
    def test_the_version_a_release_job_froze_reaches_the_lane(self, lane, origin):
        """``LF_APP_VERSION`` is kept, so that the release gallery reports the version its job froze.

        ``.github/workflows/release.yml`` freezes ``LF_APP_VERSION`` from ``VERSION`` for every later step of its job, the
        gallery included: ``dev.py mkdocs gallery`` starts Playwright, whose webServer, ``dev.py server --test``, is a
        test lane, and its debug frontend build reads the variable too. Dropped there, the gallery's screenshots would
        show ``git describe``'s answer instead, ``-dirty`` after the steps of the job that write tracked files.
        """
        frozen = {"LF_APP_VERSION": "1.2.3-frozen-by-the-release-job"}
        self.configure_instance(lane, dotenv=frozen if origin == "dotenv" else {}, shell=frozen if origin == "shell" else {})

        cli_base.configure_test_runtime(port=lane.port, data_dir=lane.data_dir)

        assert config_platform.frozen_app_version() == frozen["LF_APP_VERSION"], f"the lane lost LF_APP_VERSION from the {origin}: the backend would report git describe's answer"

    @pytest.mark.parametrize("exported", [pytest.param(False, id="dotenv-file-only"), pytest.param(True, id="shell-and-dotenv-file")])
    def test_the_kept_variables_are_kept_the_shell_over_the_dotenv_file_and_the_lane_over_both(self, lane, exported):
        names = cli_base.TEST_LANE_KEEPS | set(self.KEPT_BY_PREFIX)
        assert all(cli_base.kept_in_a_test_lane(name) for name in names), f"kept_in_a_test_lane must keep {sorted(name for name in names if not cli_base.kept_in_a_test_lane(name))}"
        dotenv = self.values(lane, "dotenv", names)
        shell = self.values(lane, "shell", names) if exported else {}
        self.configure_instance(lane, dotenv=dotenv, shell=shell)

        configured = cli_base.configure_test_runtime(port=lane.port, data_dir=lane.data_dir)

        winner, exports = shell or dotenv, self.lane_exports(lane)
        kept = self.present(names)
        assert configured == (lane.port, lane.data_dir.resolve())
        assert kept == {name: exports.get(name, winner[name]) for name in sorted(names)}, "each kept variable holds the lane's value when it has one, else the shell's, else the dotenv file's"

    @pytest.mark.parametrize("nested", [pytest.param("inherited", id="no-args-as-the-shared-server"), pytest.param("explicit", id="the-same-lane-again")])
    def test_a_nested_call_keeps_the_lane_id_and_drops_nothing_more(self, lane, nested):
        # The runner: the developer's dotenv file, loaded by pipenv into its environment as well. Once the lane is
        # configured it adds what its children inherit: the lane's database and the flag of its shared server.
        instance = self.values(lane, "instance", env_example_variables() | cli_base.TEST_LANE_KEEPS | {self.UNDOCUMENTED, *self.OTHER_PROGRAMS})
        self.configure_instance(lane, dotenv=instance, shell=instance)
        cli_base.configure_test_runtime(port=lane.port, data_dir=lane.data_dir)
        lane.env.setenv("DATABASE_URL", f"sqlite:///{lane.data_dir.resolve() / 'sqlite' / 'app.db'}")
        lane.env.setenv(test_runner_server.SHARED_SERVER_ENV, "1")
        inherited = dict(os.environ)
        guard, lane_id = inherited.get("PIPENV_DONT_LOAD_ENV"), inherited.get("LIBREFOLIO_TEST_LANE_ID")

        # The child: `dev.py server --test` of the shared server passes no lane argument, a direct entry point may
        configured = cli_base.configure_test_runtime(**({} if nested == "inherited" else {"port": lane.port, "data_dir": lane.data_dir}))

        nested_lane_id, changes = os.environ.get("LIBREFOLIO_TEST_LANE_ID"), environment_changes(inherited)
        assert (guard, bool(lane_id)) == ("1", True), "the first call hides the dotenv file from the pipenv runs it starts and gives the lane an id"
        assert configured == (lane.port, lane.data_dir.resolve())
        assert nested_lane_id == lane_id, "a nested call keeps the lane's id: the shared server proves its readiness with it"
        assert not changes, f"a nested call changed the lane's environment: {changes}"

    def test_a_pipenv_run_child_of_the_lane_gets_no_dropped_setting_back(self, lane):
        """The runner starts its pytest children with ``pipenv run``, which would load the dotenv file again, overriding.

        pipenv loads the file ``PIPENV_DOTENV_LOCATION`` names (else the project's ``.env``) into the command it runs,
        with ``override=True``, unless ``PIPENV_DONT_LOAD_ENV`` is set. ``configure_test_runtime`` sets it, so what the
        lane dropped stays dropped in its children and what it kept reaches them. The control runs the same child
        without the guard and gets the dropped settings back: the guard is what keeps them out.

        As in ``test_configured_runtime_survives_a_nested_pipenv_run``, the child only prints, and starts through
        ``run_python_in_a_pipenv_child``, which never lets pipenv create an environment.
        """
        if not cli_base.pipenv_prefix():
            pytest.skip("no pipenv in the Docker image: no `pipenv run` child loads a dotenv file there")
        dropped = {"LIBREFOLIO_PROFILE": "managed", self.UNDOCUMENTED: "instance-value-of-the-smtp-password"}
        kept = {"LF_APP_VERSION": "1.2.3-frozen-by-the-release-job"}
        assert not any(map(cli_base.kept_in_a_test_lane, dropped)) and all(map(cli_base.kept_in_a_test_lane, kept)), "the probes must be two settings the lane drops and one it keeps"
        self.configure_instance(lane, dotenv={**dropped, **kept}, shell={})
        cli_base.configure_test_runtime(port=lane.port, data_dir=lane.data_dir)
        guarded = dict(os.environ)
        unguarded = {name: value for name, value in guarded.items() if name != "PIPENV_DONT_LOAD_ENV"}

        child = self.pipenv_child(guarded, [*dropped, *kept])
        control = self.pipenv_child(unguarded, [*dropped, *kept])

        in_process = self.present([*dropped, *kept])
        assert (guarded.get("PIPENV_DONT_LOAD_ENV"), in_process) == ("1", kept), "the lane must set the guard, drop the two settings and keep LF_APP_VERSION in this process"
        assert control == {**dropped, **kept}, "without PIPENV_DONT_LOAD_ENV, pipenv must load the dotenv file into the child again: otherwise the absences below prove nothing"
        assert child == {**dict.fromkeys(dropped), **kept}, "a pipenv run child of the lane got dropped settings back from the dotenv file, or lost LF_APP_VERSION"

    @pytest.mark.parametrize(
        ("rejected", "error"),
        [
            pytest.param("invalid-port", "^--test-port must be between 1 and 65535$", id="invalid-port"),
            pytest.param("production-port", "^Test port must not be the production server port$", id="production-port"),
            pytest.param("production-data-dir", OVERLAP_ERROR, id="production-data-dir"),
        ],
    )
    def test_a_rejected_lane_changes_nothing(self, lane, rejected, error):
        # Everything in the dotenv file, and what the lane would drop exported as well: a drop made before the rejection
        # would show as a removal, a hydration of the kept ones as an addition.
        instance = self.values(lane, "instance", env_example_variables() | cli_base.TEST_LANE_KEEPS | {self.UNDOCUMENTED})
        self.configure_instance(lane, dotenv=instance, shell={name: value for name, value in instance.items() if not cli_base.kept_in_a_test_lane(name)})
        lane_args = {
            "invalid-port": {"port": 0, "data_dir": lane.data_dir},
            "production-port": {"port": int(instance["PORT"]), "data_dir": lane.data_dir},
            "production-data-dir": {"port": lane.port, "data_dir": instance["LIBREFOLIO_DATA_DIR"]},
        }[rejected]
        before = dict(os.environ)

        with pytest.raises(ValueError, match=error):
            cli_base.configure_test_runtime(**lane_args)

        changes = environment_changes(before)
        assert not changes, f"a rejected lane changed the environment: {changes}"


class TestSettingsReadNoDotenvFileInTestMode:
    """In test mode ``Settings`` reads no dotenv file, not even one it is given; outside test mode it reads it as before.

    A lane's settings are the defaults and what its runner exported. The dotenv file is a synthetic one in ``tmp_path``
    whose values differ from the defaults: reading it outside test mode first proves it would be read. Every field of
    ``Settings`` is cleared from the environment beforehand, and the fixtures restore the environment afterwards.
    """

    FILE_VALUES = {"LIBREFOLIO_PROFILE": "managed", "PREVIEW_CACHE_MAX_MB": 7}

    @pytest.fixture
    def instance_dotenv(self, runtime_env, tmp_path) -> Path:
        for name in backend_config.Settings.model_fields:
            runtime_env.delenv(name, raising=False)
        dotenv_file = tmp_path / "instance.env"
        dotenv_file.write_text("".join(f"{name}={value}\n" for name, value in self.FILE_VALUES.items()), encoding="utf-8")
        return dotenv_file

    def read(self, settings: backend_config.Settings) -> dict[str, object]:
        return {name: getattr(settings, name) for name in self.FILE_VALUES}

    def defaults(self) -> dict[str, object]:
        return {name: backend_config.Settings.model_fields[name].default for name in self.FILE_VALUES}

    @pytest.mark.parametrize("given", [pytest.param("argument", id="env-file-argument"), pytest.param("model-config", id="model-config-env-file")])
    def test_the_dotenv_file_is_read_outside_test_mode_only(self, runtime_env, instance_dotenv, given):
        if given == "model-config":
            # Where get_settings() finds it: Settings() without argument reads model_config["env_file"]
            runtime_env.setitem(backend_config.Settings.model_config, "env_file", str(instance_dotenv))

        def settings_in(test_mode: str) -> dict[str, object]:
            runtime_env.setenv("LIBREFOLIO_TEST_MODE", test_mode)
            return self.read(backend_config.Settings(_env_file=instance_dotenv) if given == "argument" else backend_config.Settings())

        outside, inside = settings_in("0"), settings_in("1")

        assert self.FILE_VALUES != self.defaults(), "the file must set values other than the defaults, or reading it could not be told apart"
        assert outside == self.FILE_VALUES, "outside test mode the dotenv file is read: without it, its absence in test mode would prove nothing"
        assert inside == self.defaults(), "in test mode the dotenv file must not be read"

    def test_in_test_mode_the_environment_is_still_read(self, runtime_env, instance_dotenv):
        exported = {"LIBREFOLIO_PROFILE": "managed", "PREVIEW_CACHE_MAX_MB": 9}
        runtime_env.setenv("LIBREFOLIO_TEST_MODE", "1")
        for name, value in exported.items():
            runtime_env.setenv(name, str(value))

        assert self.read(backend_config.Settings(_env_file=instance_dotenv)) == exported, "a lane still reads what its runner exported"


class TestConfigureServerRuntime:
    @pytest.mark.parametrize("source", ["shell", "explicit"], ids=["shell-over-dotenv", "explicit-over-dotenv"])
    def test_winning_values_are_normalized_and_exported(self, runtime_env, source):
        runtime_env.setattr(cli_base, "_project_dotenv_values", lambda: {"PORT": "9999", "LIBREFOLIO_DATA_DIR": "runtime/dotenv-production-data"})
        raw_dir = "runtime/../runtime/lane-production-data"
        if source == "shell":
            runtime_env.setenv("LIBREFOLIO_TEST_MODE", "1")
            runtime_env.setenv("PORT", "06222")
            runtime_env.setenv("LIBREFOLIO_DATA_DIR", raw_dir)
            expected_port, configured = 6222, cli_base.configure_server_runtime(port=None, data_dir=None)
        else:
            expected_port, configured = 6223, cli_base.configure_server_runtime(port="06223", data_dir=raw_dir)

        expected_dir = (cli_base.get_project_root() / "runtime/lane-production-data").resolve()
        assert configured == (expected_port, expected_dir)
        assert os.environ["PORT"] == str(expected_port)
        assert os.environ["LIBREFOLIO_DATA_DIR"] == str(expected_dir)
        assert os.environ["LIBREFOLIO_TEST_MODE"] == "0"
        assert os.environ["PIPENV_DONT_LOAD_ENV"] == "1"


class TestProjectDotenvValues:
    """``_project_dotenv_values()`` itself, isolated from the repository's .env."""

    def test_reads_from_the_configured_pipenv_dotenv_location(self, runtime_env, tmp_path):
        alternate = tmp_path / "alternate.env"
        alternate.write_text("LIBREFOLIO_RUNTIME_ISOLATION_DOTENV_LOCATION_PROBE=alternate-dotenv-value\n", encoding="utf-8")
        runtime_env.setenv("PIPENV_DOTENV_LOCATION", str(alternate))

        assert cli_base._project_dotenv_values()["LIBREFOLIO_RUNTIME_ISOLATION_DOTENV_LOCATION_PROBE"] == "alternate-dotenv-value"

    @pytest.mark.parametrize("guard_value", ["1", "true", "TRUE", "yes", "on", "ON"])
    def test_dont_load_guard_skips_even_a_configured_dotenv_location(self, runtime_env, tmp_path, guard_value):
        guarded = tmp_path / "guarded.env"
        guarded.write_text("LIBREFOLIO_RUNTIME_ISOLATION_DONT_LOAD_PROBE=should-never-be-read\n", encoding="utf-8")
        runtime_env.setenv("PIPENV_DOTENV_LOCATION", str(guarded))
        runtime_env.setenv("PIPENV_DONT_LOAD_ENV", guard_value)

        assert cli_base._project_dotenv_values() == {}


@pytest.mark.parametrize(("lane", "port_name", "dir_name", "expected_mode", "port"), [pytest.param("test", "TEST_PORT", "LIBREFOLIO_TEST_DATA_DIR", "1", 6135, id="test-lane"), pytest.param("production", "PORT", "LIBREFOLIO_DATA_DIR", "0", 6226, id="production-lane")])
def test_configured_runtime_survives_a_nested_pipenv_run(runtime_env, lane, port_name, dir_name, expected_mode, port):
    """The probe only prints inherited values: no server, no database, no files."""
    if cli_base._project_dotenv_values().get(port_name) == str(port):
        port += 1
    # The nested Pipenv process still sees the real repository .env; the parent
    # must not hydrate unrelated repository values into this pytest process.
    runtime_env.setattr(cli_base, "_project_dotenv_values", lambda: {})
    configure = cli_base.configure_test_runtime if lane == "test" else cli_base.configure_server_runtime
    configured_port, configured_dir = configure(port=port, data_dir=f"runtime/pipenv-subprocess-{lane}-data")
    probe = f"import os; print(os.environ.get('{port_name}')); print(os.environ.get('{dir_name}')); print(os.environ.get('LIBREFOLIO_TEST_MODE'))"
    result = run_python_in_a_pipenv_child(probe, os.environ.copy())

    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert result.stdout.strip().splitlines()[-3:] == [str(configured_port), str(configured_dir), expected_mode]


# ── Contracts 3 and 4 — parsers, child environments, dispatch, database ────


def build_dev_test_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dev.py")
    test_runner_cli.register_subparser(parser.add_subparsers(dest="command"))
    return parser


LANE_ARGV = ["--test-port", "6125", "--data-dir", "runtime/parser-test-data", "utils", "runtime-isolation"]


@pytest.mark.parametrize(
    ("parser_factory", "argv", "expected"),
    [
        pytest.param(build_dev_test_parser, ["test", *LANE_ARGV], (6125, "runtime/parser-test-data"), id="dev-test"),
        pytest.param(test_runner_cli.create_parser, LANE_ARGV, (6125, "runtime/parser-test-data"), id="runner"),
        pytest.param(build_dev_test_parser, ["test", "utils", "runtime-isolation"], (None, None), id="dev-test-defaults"),
    ],
)
def test_test_parsers_expose_lane_overrides_and_none_defaults(parser_factory, argv, expected):
    args = parser_factory().parse_args(argv)

    assert (args.test_port, args.data_dir) == expected
    assert (args.category, args.action) == ("utils", "runtime-isolation")


@pytest.mark.parametrize(
    ("category", "action", "list_tests", "expected"),
    [
        pytest.param("api", "system", False, True, id="api"),
        pytest.param("e2e", "search-to-prices", False, True, id="e2e"),
        pytest.param("all-frontend", None, False, True, id="all-frontend"),
        pytest.param("front-asset", "all", False, True, id="frontend-all"),
        pytest.param("front-asset", "asset-list", False, True, id="playwright-spec"),
        pytest.param("front-utility", "core-unit", False, False, id="vitest-test"),
        pytest.param("api", "system", True, False, id="list-api"),
        pytest.param("front-asset", "asset-list", True, False, id="list-playwright"),
    ],
)
def test_requires_shared_backend_matrix(category, action, list_tests, expected):
    assert test_runner_cli._requires_shared_backend(SimpleNamespace(category=category, action=action, list_tests=list_tests)) is expected


def capture_server_child(monkeypatch) -> dict:
    """Replace every side effect of ``dev.py server`` with an ordered recording."""
    captured: dict = {"build_modes": [], "events": []}

    def capture_build(name, result):
        captured["build_modes"].append((name, os.environ.get("LIBREFOLIO_TEST_MODE")))
        captured["events"].append(name)
        return result

    def capture_run(command, *_args, **kwargs):
        captured.update(command=command, env=dict(kwargs["env"]))
        captured["events"].append("spawn")
        return 0

    def capture_server_launch(command, env=None, grace_seconds=None):
        captured.update(command=command, env=dict(env or {}), grace_seconds=grace_seconds)
        captured["events"].append("spawn")
        return 0

    def capture_exec(_executable, command, env):
        captured.update(command=command, env=dict(env))
        captured["events"].append("spawn")

    monkeypatch.setattr(dev, "HAS_ARGCOMPLETE", False)
    monkeypatch.setattr(dev, "check_port_in_use", lambda _port: captured["events"].append("port-check") or [])
    monkeypatch.setattr(dev, "auto_build_frontend", lambda *_a, **_kw: capture_build("frontend", None))
    monkeypatch.setattr(dev, "auto_build_mkdocs", lambda *_a, **_kw: capture_build("mkdocs", None))
    monkeypatch.setattr(dev, "update_js_cache", lambda *_a, **_kw: capture_build("js-cache", 0))
    monkeypatch.setattr(dev, "run_command_live", capture_run)
    # Z-10 moves the server launch to run_server_live, which dev.py does not define before it (raising=False): without
    # this stand-in, dev.main() would start a real uvicorn on the test's port and hang.
    monkeypatch.setattr(dev, "run_server_live", capture_server_launch, raising=False)
    monkeypatch.setattr(dev.os, "execvpe", capture_exec)
    return captured


@pytest.mark.parametrize("lane", ["test", "production"])
def test_server_child_env_carries_the_configured_lane(runtime_env, lane):
    captured = capture_server_child(runtime_env)
    if lane == "test":
        data_dir = "runtime/server-test-data"
        runtime_env.setattr(sys, "argv", ["dev.py", "server", "--test", "--data-dir", data_dir, "--port", "6126"])
    else:
        data_dir = str(cli_base.get_project_root() / "runtime/server-production-data")
        runtime_env.setattr(sys, "argv", ["dev.py", "server", "--data-dir", data_dir, "--port", "6127"])
    assert dev.main() == 0

    # configure_*_runtime() writes to os.environ before cmd_server() snapshots it
    # into the child env: the child must inherit the same normalized lane.
    mode, env = ("1" if lane == "test" else "0"), captured["env"]
    assert captured["build_modes"] == [("frontend", mode), ("mkdocs", mode), ("js-cache", mode)]
    assert (env["LIBREFOLIO_TEST_MODE"], env["PIPENV_DONT_LOAD_ENV"]) == (mode, "1")
    if lane == "test":
        assert (env["TEST_PORT"], env["LIBREFOLIO_TEST_DATA_DIR"]) == ("6126", str(cli_base.get_project_root() / data_dir))
        assert captured["command"][captured["command"].index("--port") + 1] == "6126"
    else:
        assert (env["PORT"], env["LIBREFOLIO_DATA_DIR"]) == ("6127", data_dir)
        assert "LIBREFOLIO_TEST_DATA_DIR" not in env
    # The port is checked after every build step and immediately before the spawn.
    events = captured["events"]
    port_check_index = events.index("port-check")
    assert all(events.index(stage) < port_check_index for stage in ("frontend", "mkdocs", "js-cache"))
    assert events[port_check_index : port_check_index + 2] == ["port-check", "spawn"]


def test_runner_applies_overrides_before_shared_server_and_test_dispatch(runtime_env):
    args = build_dev_test_parser().parse_args(["test", "--test-port", "6128", "--data-dir", "runtime/runner-test-data", "api", "system"])
    observed = []

    def snapshot(stage):
        observed.append((stage, os.environ.get("TEST_PORT"), os.environ.get("LIBREFOLIO_TEST_DATA_DIR"), os.environ.get("LIBREFOLIO_TEST_MODE")))

    class CapturingSharedServer:
        def __init__(self, **_kwargs):
            snapshot("shared-server")

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    runtime_env.setattr(test_runner_server, "SharedTestServer", CapturingSharedServer)
    runtime_env.setattr(test_runner_cli, "_apply_coverage_mode", lambda *_a, **_kw: snapshot("coverage-build") or True)
    runtime_env.setattr(test_runner_cli, "_run_exclusive_setups", lambda _args: snapshot("exclusive-setups") or True)
    runtime_env.setattr(test_runner_cli, "_apply_parallel", lambda _args, _verbose: (snapshot("parallel-tests"), (True, True))[1])
    runtime_env.setattr(test_runner_cli, "dispatch_to_category", lambda *_a: snapshot("test-dispatch") or 0)
    for name in ("_COVERAGE_MODE", "_COVERAGE_PY"):
        runtime_env.setattr(test_runner_cli._common, name, False)
    for name in ("_SKIP_ACTIONS", "_FAILED_ACTIONS"):
        runtime_env.setattr(test_runner_cli._common, name, set())

    assert test_runner_cli._dispatch_test_command_body(args) == 0

    expected_dir = str(cli_base.get_project_root() / "runtime/runner-test-data")
    assert observed == [(stage, "6128", expected_dir, "1") for stage in ("coverage-build", "exclusive-setups", "shared-server", "parallel-tests", "test-dispatch")]


def test_run_command_forwards_the_dynamic_database_url_to_the_child_env(runtime_env):
    override = Path("/isolated/run-command-test-data")
    runtime_env.setenv("LIBREFOLIO_TEST_DATA_DIR", str(override))
    runtime_env.setattr(test_runner_common, "_COVERAGE_PY", False)
    runtime_env.setattr(test_runner_common, "_LOG_DIR", None)
    captured = {}

    def fake_subprocess_run(cmd, *, cwd, capture_output, text, env, timeout):
        captured["env"] = env
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    runtime_env.setattr(test_runner_common.subprocess, "run", fake_subprocess_run)
    # The lane database URL is injected only for a backend test command.
    cmd = ["python", "-m", "pytest", "backend/test_scripts/test_utilities/test_runtime_isolation.py", "-v"]

    assert test_runner_common.run_command(cmd, "runtime isolation") is True
    assert captured["env"]["DATABASE_URL"] == f"sqlite:///{override / 'sqlite' / 'app.db'}"
    assert captured["env"]["LIBREFOLIO_TEST_MODE"] == "1"


def test_db_create_clean_rejects_a_production_test_dir_before_any_mutation(runtime_env, monkeypatch):
    runtime_env.setenv("LIBREFOLIO_DATA_DIR", "runtime/configured-production-data")
    runtime_env.setenv("LIBREFOLIO_TEST_DATA_DIR", str(backend_config.PROJECT_ROOT / "runtime/configured-production-data"))
    for target, name in ((Path, "unlink"), (dev, "check_server_running"), (dev, "run_command_live")):
        forbid(monkeypatch, target, name, "destructive db create-clean work ran before path validation")

    with pytest.raises(ValueError, match=OVERLAP_ERROR):
        dev.cmd_db_create_clean(argparse.Namespace(test=True))


class TestRunnerDbCreateSafety:
    @pytest.mark.parametrize(
        ("marked_relative", "managed_root"),
        [
            pytest.param("custom-uploads/provider-cache/nested-production-root", "custom-uploads", id="custom-uploads"),
            pytest.param("broker_reports/uploaded/broker_7/nested-production-root", "broker_reports", id="broker-reports"),
            pytest.param("secrets/nested-production-root", "secrets", id="secrets"),
        ],
    )
    def test_nested_production_marker_is_rejected_before_destructive_mutation(self, runtime_env, monkeypatch, tmp_path, marked_relative, managed_root):
        production_root, test_root = tmp_path / "synthetic-production-data", tmp_path / "synthetic-test-data"
        production_root.mkdir()
        marked_root = test_root / marked_relative
        marked_root.mkdir(parents=True)
        (marked_root / backend_config.PRODUCTION_DATA_MARKER).write_text("synthetic nested production marker\n", encoding="utf-8")
        runtime_env.setattr(backend_config, "DEFAULT_PROD_DATA_DIR", production_root)
        runtime_env.setenv("LIBREFOLIO_DATA_DIR", str(production_root))
        runtime_env.setenv("LIBREFOLIO_TEST_DATA_DIR", str(test_root))
        runtime_env.setenv("PORT", "6198")
        before, tree_before = runtime_state(), tree_snapshot(tmp_path)
        mkdir_calls = record_mkdir(monkeypatch)
        for target, name in ((Path, "unlink"), (test_runner_backend_db, "get_test_db_path"), (test_runner_backend_db, "_reset_test_file_store"), (test_runner_backend_db, "run_command"), (cli_base, "check_server_running")):
            forbid(monkeypatch, target, name, "destructive database work ran before nested marker validation")
        with pytest.raises(ValueError, match=rf"^Test data subtree contains a marked production root: {re.escape(managed_root)}$"):
            test_runner_backend_db._db_create_body()

        assert mkdir_calls == []
        assert (runtime_state(), tree_snapshot(tmp_path)) == (before, tree_before)

    def test_db_upgrade_path_with_spaces_and_colon_remains_one_argv_element(self, runtime_env, monkeypatch, tmp_path):
        data_dir_name = "synthetic test data: isolated lane" if os.name != "nt" else "synthetic test data isolated lane"
        test_db_path = tmp_path / data_dir_name / "sqlite" / "app.db"
        test_db_path.parent.mkdir(parents=True)
        test_db_path.write_bytes(b"synthetic database sentinel\n")
        for relative in ("custom-uploads/keep.txt", "broker_reports/keep.txt"):
            sentinel = tmp_path / data_dir_name / relative
            sentinel.parent.mkdir(parents=True, exist_ok=True)
            sentinel.write_text("preserve me\n", encoding="utf-8")
        assert " " in data_dir_name
        tree_before, environment_before = tree_snapshot(tmp_path), dict(os.environ)
        calls: dict = {"setup": [], "server_checks": [], "unlinked": [], "reset": []}

        def capture_run(command, description, *, verbose):
            calls["run"] = (command, description, verbose)
            return False

        monkeypatch.setattr(test_runner_backend_db, "setup_test_database", lambda: (calls["setup"].append(True), test_db_path)[1])
        monkeypatch.setattr(test_runner_backend_db, "get_test_db_path", lambda: test_db_path)
        monkeypatch.setattr(test_runner_backend_db, "_reset_test_file_store", lambda: calls["reset"].append(True))
        monkeypatch.setattr(test_runner_backend_db, "run_command", capture_run)
        monkeypatch.setattr(cli_base, "get_test_server_port", lambda: 6199)
        monkeypatch.setattr(cli_base, "check_server_running", lambda action, *, port: calls["server_checks"].append((action, port)) or True)
        monkeypatch.setattr(Path, "unlink", lambda path, *_a, **_kw: calls["unlinked"].append(path))

        assert test_runner_backend_db._db_create_body(verbose=True) is False

        assert calls["run"] == ([sys.executable, "dev.py", "db", "upgrade", str(test_db_path)], "Create database via Alembic migrations", True)
        assert (calls["setup"], calls["reset"], calls["unlinked"]) == ([True], [True], [test_db_path])
        assert calls["server_checks"] == [("creating a clean test database", 6199)]
        assert dict(os.environ) == environment_before
        assert tree_snapshot(tmp_path) == tree_before


# ── Contract 5 — lane-authenticated readiness probes (runner and helper).
# The handler's own token/header semantics live in test_api/test_system_api.py.


class TestLaneHealthProbes:
    def test_runner_health_url_encodes_the_current_lane_id(self, runtime_env):
        lane_id = "lane/id+with space&token"
        runtime_env.setenv("LIBREFOLIO_TEST_LANE_ID", lane_id)
        url = test_runner_server.health_url(port=6125)

        assert url == "http://localhost:6125/api/v1/system/test-lane-health?token=lane%2Fid%2Bwith+space%26token"
        assert urllib.parse.parse_qs(urllib.parse.urlsplit(url).query) == {"token": [lane_id]}

    @pytest.mark.parametrize(
        ("status", "returned_lane", "expected"),
        [pytest.param(200, None, False, id="missing-header"), pytest.param(200, "wrong-lane", False, id="wrong-header"), pytest.param(200, "runner-lane", True, id="exact-header"), pytest.param(503, "runner-lane", False, id="wrong-status")],
    )
    def test_runner_readiness_requires_status_and_exact_lane_header(self, runtime_env, status, returned_lane, expected):
        runtime_env.setenv("LIBREFOLIO_TEST_LANE_ID", "runner-lane")
        opener_handlers, open_calls = [], []

        class FakeOpener:
            def open(self, url, *, timeout):
                open_calls.append((url, timeout))
                return FakeHealthResponse(status, lane_headers(returned_lane))

        runtime_env.setattr(test_runner_server.urllib.request, "build_opener", lambda *handlers: (opener_handlers.append(handlers), FakeOpener())[1])

        assert test_runner_server.is_healthy(port=6125, timeout=3.0) is expected
        assert open_calls == [(test_runner_server.health_url(6125), 3.0)]
        # Exactly one handler, and it refuses redirects: a 3xx must never send
        # the probe to some other lane's backend.
        (redirect_handler,) = opener_handlers[0]
        assert isinstance(redirect_handler, test_runner_server.urllib.request.HTTPRedirectHandler)
        assert redirect_handler.redirect_request(None, None, 302, "Found", {}, "http://localhost:6125/redirected") is None

    def test_helper_creates_and_exports_a_lane_id(self, runtime_env):
        manager = test_server_helper_module._TestingServerManager()

        assert manager.lane_id
        assert os.environ["LIBREFOLIO_TEST_LANE_ID"] == manager.lane_id

    @pytest.mark.parametrize(("returned_lane", "expected"), [pytest.param("exact", True, id="exact-header"), pytest.param(None, False, id="missing-header"), pytest.param("wrong-lane", False, id="wrong-header")])
    def test_helper_readiness_requires_an_exact_lane_header(self, runtime_env, returned_lane, expected):
        lane_id = "helper/lane+with space&token"
        runtime_env.setenv("LIBREFOLIO_TEST_LANE_ID", lane_id)
        requested: list[tuple] = []
        runtime_env.setattr(test_server_helper_module.httpx, "get", httpx_lane_probe(lane_id if returned_lane == "exact" else returned_lane, calls=requested))
        manager = test_server_helper_module._TestingServerManager()

        assert manager.lane_id == lane_id
        assert manager.health_url == f"{test_server_helper_module.TEST_API_BASE_URL}/system/test-lane-health?token=helper%2Flane%2Bwith+space%26token"
        assert manager.is_server_running() is expected
        assert requested == [(manager.health_url, 2.0, False)]


# ── Contract 6 — SharedTestServer: ownership, races, teardown, signal order ──


class _PublicationHookServer(test_runner_server.SharedTestServer):
    """A server whose ``started_here`` publication also runs a test-supplied hook.

    The only way to observe *when* ownership becomes durably visible, relative to
    masking and ``Popen``/``getpgid``, without touching the production class.
    """

    def __init__(self, on_publish):
        self._on_publish = on_publish
        super().__init__()

    @property
    def started_here(self):
        return self.__dict__.get("_started_here", False)

    @started_here.setter
    def started_here(self, value):
        if value:
            self._on_publish()
        self.__dict__["_started_here"] = value


#: ``stop()``'s grace outside coverage. The scripted clocks of the real ``stop()`` derive from it, never from its value:
#: the reading meant to end each of its two waits lies one second past that wait's deadline — the first starts at 0 and
#: ends at ``PLAIN_GRACE_S + 1``, the second starts there and ends at ``2 * PLAIN_GRACE_S + 2`` —, so a longer grace
#: cannot leave a wait running on the clock's last reading (with the fake sleep, a busy loop).
PLAIN_GRACE_S = test_runner_server.SHUTDOWN_GRACE_PLAIN
#: How long ``stop()`` reaps the launcher after a SIGKILL: ``self.proc.wait(timeout=5)``, a literal of ``_server.py`` that
#: does not follow the grace. The two were both 5 s until the grace became 10 s.
SIGKILL_REAP_TIMEOUT_S = 5


class TestSharedTestServerOwnership:
    def test_start_rejects_an_occupied_port_without_spawning_or_signalling(self, monkeypatch):
        # That PID may be another worktree's lane: refuse before doing anything,
        # even though health would answer if start() ever reached the poll loop.
        server = test_runner_server.SharedTestServer()
        patch_spawn(monkeypatch, holders=["918273"], healthy=True)
        forbid(monkeypatch, test_runner_server, "build_server_prerequisites", "the build step must not run while the port is already held")
        forbid(monkeypatch, test_runner_server.subprocess, "Popen", "subprocess.Popen must not run while the port is already held")
        for name in ("kill", "killpg"):
            forbid(monkeypatch, test_runner_server.os, name, "no signal may be sent by a fail-closed start()")
        errors: list[str] = []
        monkeypatch.setattr(test_runner_server, "print_error", errors.append)
        assert server.start() is False

        assert (server.proc, server.started_here) == (None, False)
        assert any(str(server.port) in message and "918273" in message for message in errors), errors

    @pytest.mark.parametrize(
        ("poll_results", "healthy", "clock", "poll_calls"),
        [
            pytest.param([17], None, (0.0,), 1, id="launcher-exit-during-startup"),
            pytest.param([None, 19], True, (0.0,), 2, id="launcher-exit-at-readiness"),
            pytest.param([], None, (0.0, test_runner_server.STARTUP_TIMEOUT + 1.0), 0, id="startup-timeout"),
        ],
    )
    def test_a_failed_startup_always_routes_through_stop_without_sleeping(self, monkeypatch, poll_results, healthy, clock, poll_calls):
        server = test_runner_server.SharedTestServer()
        process = FakeProc(40001, poll_results)
        patch_spawn(monkeypatch, process=process, holders=lambda port=None: [] if server.proc is None else ["40001"], pgid=40000, healthy=healthy)
        stop_calls = record_stop(monkeypatch, server)
        ready: list[str] = []
        monkeypatch.setattr(test_runner_server, "print_success", ready.append)
        patch_clock(monkeypatch, test_runner_server, *clock, forbid_sleep="a failed startup must not wait on the real clock")
        assert server.start() is False

        assert (process.poll_calls, stop_calls, ready) == (poll_calls, [(process, 40000, True)], [])

    def test_start_rejects_a_foreign_listener_that_wins_the_bind_race(self, monkeypatch):
        server = test_runner_server.SharedTestServer()
        child_pid, child_group, foreign_pid, foreign_group = 41001, 41000, 51001, 51000
        process = FakeProc(child_pid)
        holder_calls, group_signals, errors, ready = [], [], [], []

        def fake_port_holders(port=None):
            # Free at the preflight, then a stranger owns the socket.
            holder_calls.append(port)
            return [] if len(holder_calls) == 1 else [str(foreign_pid)]

        patch_spawn(monkeypatch, process=process, holders=fake_port_holders, pgid=lambda pid: child_group if pid == child_pid else foreign_group, healthy=True)
        monkeypatch.setattr(test_runner_server.os, "killpg", lambda group, sig: group_signals.append((group, sig)))
        monkeypatch.setattr(server, "_process_group_alive", lambda: False)
        monkeypatch.setattr(test_runner_server, "print_error", errors.append)
        monkeypatch.setattr(test_runner_server, "print_success", ready.append)
        patch_clock(monkeypatch, test_runner_server, 0.0, 0.0, 0.0, PLAIN_GRACE_S + 1.0, PLAIN_GRACE_S + 1.0, 2 * PLAIN_GRACE_S + 2.0, forbid_sleep="the bind-race path must not wait on the real clock")

        assert server.start() is False

        assert len(holder_calls) >= 3
        assert group_signals == [(child_group, test_runner_server.signal.SIGTERM)]
        assert process.wait_timeouts == [test_runner_server.SHUTDOWN_GRACE_PLAIN]
        assert (server.proc, server.process_group_id, ready) == (None, None, [])
        assert any("unowned PID" in message for message in errors), errors
        assert any(str(foreign_pid) in message and "foreign PID" in message for message in errors), errors

    @pytest.mark.parametrize(
        ("poll_results", "group_survives", "clock", "expected_signals", "expected_waits"),
        [
            # The launcher still runs after SIGTERM: stop() waits for it for the grace.
            pytest.param([], False, (0.0, PLAIN_GRACE_S + 1.0, PLAIN_GRACE_S + 1.0, 2 * PLAIN_GRACE_S + 2.0), ["SIGTERM"], [PLAIN_GRACE_S], id="group-exits-on-sigterm"),
            # The launcher has exited (23) and its group has not: no grace wait on the launcher, only its reap after the
            # SIGKILL. The 0.0 inside the first deadline makes one liveness probe and one sleep before it ends.
            pytest.param([23], True, (0.0, 0.0, PLAIN_GRACE_S + 1.0, PLAIN_GRACE_S + 1.0, 2 * PLAIN_GRACE_S + 2.0), ["SIGTERM", 0, 0, "SIGKILL"], [SIGKILL_REAP_TIMEOUT_S], id="group-ignores-sigterm"),
        ],
    )
    def test_stop_signals_only_its_own_group_and_merely_reports_a_foreign_pid(self, monkeypatch, poll_results, group_survives, clock, expected_signals, expected_waits):
        # Diagnostics are LISTEN-only: a different PID on the port is another
        # lane, never cleanup — so it may be named, never signalled.
        server = test_runner_server.SharedTestServer()
        child_group, foreign_pid, foreign_group = 43000, 53001, 53000
        process = FakeProc(43001, poll_results)
        server.proc, server.process_group_id, server.started_here = process, child_group, True
        group_signals, holder_lookups, errors = [], [], []
        monkeypatch.setattr(test_runner_server.os, "killpg", lambda group, sig: group_signals.append((group, sig)))
        monkeypatch.setattr(test_runner_server.os, "getpgid", lambda pid: holder_lookups.append(pid) or foreign_group)
        forbid(monkeypatch, test_runner_server.os, "kill", "stop() must never signal a PID discovered from LISTEN diagnostics")
        monkeypatch.setattr(test_runner_server, "port_holders", lambda port=None: [str(foreign_pid)])
        monkeypatch.setattr(test_runner_server, "print_error", errors.append)
        if not group_survives:
            monkeypatch.setattr(server, "_process_group_alive", lambda: False)
        patch_clock(monkeypatch, test_runner_server, *clock, forbid_sleep=None if group_survives else "a group that is already gone must not be waited on")
        server.stop()

        signals = {"SIGTERM": test_runner_server.signal.SIGTERM, "SIGKILL": test_runner_server.signal.SIGKILL}
        assert group_signals == [(child_group, signals.get(sig, sig)) for sig in expected_signals]
        assert (holder_lookups, process.poll_calls, process.wait_timeouts) == ([foreign_pid], 1, expected_waits)
        assert any(str(foreign_pid) in message and "foreign PID" in message for message in errors), errors
        assert (server.proc, server.process_group_id, server.started_here) == (None, None, False)

    @pytest.mark.parametrize("published", ["proc-only", "group-only"])
    def test_stop_signals_and_clears_partial_publication_state(self, monkeypatch, published):
        # stop()'s only escape hatch is "no proc AND no group", deliberately
        # weaker than started_here, so a crash mid-spawn is still cleaned up.
        server = test_runner_server.SharedTestServer()
        process = FakeProc(46001, records_signals=True) if published == "proc-only" else None
        server.proc, server.process_group_id, server.started_here = process, (None if published == "proc-only" else 46100), False
        group_signals: list[tuple] = []
        monkeypatch.setattr(test_runner_server.os, "killpg", lambda group, sig: group_signals.append((group, sig)))
        if published == "group-only":
            forbid(monkeypatch, test_runner_server.os, "kill", "with no proc, stop() must signal the group, not a direct PID")
        monkeypatch.setattr(server, "_process_group_alive", lambda: False)
        monkeypatch.setattr(test_runner_server, "port_holders", lambda port=None: [])
        patch_clock(monkeypatch, test_runner_server, forbid_sleep="no residual grace-period wait is expected")
        server.stop()

        if published == "proc-only":
            assert (process.signals, process.wait_timeouts, group_signals) == ([test_runner_server.signal.SIGTERM], [test_runner_server.SHUTDOWN_GRACE_PLAIN], [])
        else:
            assert group_signals == [(46100, test_runner_server.signal.SIGTERM)]
        assert (server.proc, server.process_group_id, server.started_here) == (None, None, False)

    @pytest.mark.parametrize("interruption", [KeyboardInterrupt(), SystemExit(3)], ids=["keyboard-interrupt", "system-exit"])
    def test_interruption_during_polling_invokes_stop_and_reraises_it(self, monkeypatch, interruption):
        # start() wraps the whole post-Popen wait in `except BaseException`, so
        # Ctrl-C and sys.exit() tear the half-started process down instead of
        # orphaning it the way a bare `except Exception` would.
        server = test_runner_server.SharedTestServer()
        process = FakeProc(44001)

        def raise_interruption(*_args, **_kwargs):
            raise interruption

        patch_spawn(monkeypatch, process=process, holders=[], pgid=44000, healthy=raise_interruption)
        stop_calls = record_stop(monkeypatch, server)
        patch_clock(monkeypatch, test_runner_server, forbid_sleep="the interruption must fire before any sleep")

        with pytest.raises(type(interruption)) as excinfo:
            server.start()

        # Identity, not merely type: a bare `raise` re-raises the exact object.
        assert excinfo.value is interruption
        assert stop_calls == [(process, 44000, True)]

    @pytest.mark.parametrize("stage", ["pgid-capture", "ownership-publication"])
    def test_a_crash_before_ownership_is_published_still_routes_through_stop(self, monkeypatch, stage):
        # start() wraps the spawn as well as the poll loop, so a crash while
        # capturing the PGID — or in the instant before started_here is published
        # — still reaches stop() even though ownership was never recorded.
        process = FakeProc(45101)
        capture_stage = stage == "pgid-capture"
        failure = OSError("no such process group") if capture_stage else RuntimeError("crash after PGID capture")

        def raise_failure(*_args, **_kwargs):
            raise failure

        server = test_runner_server.SharedTestServer() if capture_stage else _PublicationHookServer(raise_failure)
        expected_group = None if capture_stage else 45200
        monkeypatch.setattr(test_runner_server.signal, "pthread_sigmask", lambda _how, _mask: frozenset())
        patch_spawn(monkeypatch, process=process, holders=[], pgid=raise_failure if capture_stage else 45200)
        stop_calls = record_stop(monkeypatch, server)

        with pytest.raises(type(failure)) as excinfo:
            server.start()

        assert excinfo.value is failure
        assert stop_calls == [(process, expected_group, False)]
        assert (server.proc, server.process_group_id, server.started_here) == (process, expected_group, False)


class _LifecycleProbe:
    """Records `__enter__`/`__exit__` ordering around _ACTIVE and the handlers."""

    def __init__(self, monkeypatch, server, *, handlers_installed: bool):
        self.calls: list = []
        self.handlers_installed = handlers_installed
        real_set_active = test_runner_server._set_active

        def install():
            assert test_runner_server._ACTIVE is server and self.handlers_installed is False
            self.handlers_installed = True
            self.calls.append("install_teardown")

        def remove():
            assert test_runner_server._ACTIVE is None and self.handlers_installed is True
            self.handlers_installed = False
            self.calls.append("remove_teardown")

        def stop():
            assert test_runner_server._ACTIVE is server and self.handlers_installed is True
            self.calls.append("stop")

        monkeypatch.setattr(test_runner_server, "_set_active", lambda value: (self.calls.append(("set_active", value)), real_set_active(value))[0])
        monkeypatch.setattr(test_runner_server, "_install_last_resort_teardown", install)
        monkeypatch.setattr(test_runner_server, "_remove_last_resort_teardown", remove)
        monkeypatch.setattr(server, "stop", stop)


class TestSharedTestServerContextManager:
    @pytest.mark.parametrize("outcome", ["success", "returns-false", "raises-keyboard-interrupt"])
    def test_enter_publishes_ownership_before_start_and_tears_it_down_on_failure(self, monkeypatch, outcome):
        server = test_runner_server.SharedTestServer()
        interrupt = KeyboardInterrupt()
        monkeypatch.setattr(test_runner_server, "_ACTIVE", None)
        monkeypatch.delenv(test_runner_server.SHARED_SERVER_ENV, raising=False)
        probe = _LifecycleProbe(monkeypatch, server, handlers_installed=False)

        def fake_start():
            assert test_runner_server._ACTIVE is server and probe.handlers_installed is True
            probe.calls.append("start")
            if outcome == "raises-keyboard-interrupt":
                raise interrupt
            return outcome == "success"

        monkeypatch.setattr(server, "start", fake_start)
        expected_calls = [("set_active", server), "install_teardown", "start"]

        if outcome == "success":
            assert server.__enter__() is server
            assert test_runner_server._ACTIVE is server
            assert os.environ[test_runner_server.SHARED_SERVER_ENV] == "1"
        else:
            with pytest.raises(KeyboardInterrupt if outcome == "raises-keyboard-interrupt" else RuntimeError) as excinfo:
                server.__enter__()
            if outcome == "raises-keyboard-interrupt":
                assert excinfo.value is interrupt
            else:
                assert "shared test backend failed to start" in str(excinfo.value)
            # Teardown happens only after start() ran and failed — never before.
            expected_calls += ["stop", ("set_active", None), "remove_teardown"]
            assert (test_runner_server._ACTIVE, probe.handlers_installed) == (None, False)
            assert test_runner_server.SHARED_SERVER_ENV not in os.environ
        assert probe.calls == expected_calls

    def test_exit_keeps_active_and_handlers_installed_until_stop_completes(self, monkeypatch):
        server = test_runner_server.SharedTestServer()
        monkeypatch.setattr(test_runner_server, "_ACTIVE", server)
        monkeypatch.setenv(test_runner_server.SHARED_SERVER_ENV, "1")
        probe = _LifecycleProbe(monkeypatch, server, handlers_installed=True)
        assert server.__exit__(None, None, None) is False

        assert probe.calls == ["stop", ("set_active", None), "remove_teardown"]
        assert (test_runner_server._ACTIVE, probe.handlers_installed) == (None, False)
        assert test_runner_server.SHARED_SERVER_ENV not in os.environ


class TestSharedTestServerSpawnSignals:
    """Signals arriving while the detached child is adopted must wait for it."""

    @pytest.mark.parametrize("second_signal", [False, True], ids=["single-signal", "first-signal-wins"])
    def test_a_signal_during_publication_is_deferred_without_teardown_or_reraise(self, monkeypatch, second_signal):
        first_signal = test_runner_server.signal.SIGTERM
        monkeypatch.setattr(test_runner_server, "_spawn_publication_active", True)
        monkeypatch.setattr(test_runner_server, "_deferred_spawn_signal", None)
        forbid(monkeypatch, test_runner_server, "_teardown_active", "teardown must not run while ownership publication is active")
        reraise = SimpleNamespace(getpid=lambda: pytest.fail("a deferred signal must not be re-raised"), kill=lambda *_a: pytest.fail("a deferred signal must not be re-raised"))
        monkeypatch.setattr(test_runner_server, "os", reraise)
        test_runner_server._signal_teardown(first_signal, None)
        if second_signal:
            test_runner_server._signal_teardown(test_runner_server.signal.SIGINT, None)

        assert test_runner_server._spawn_publication_active is True
        assert test_runner_server._deferred_spawn_signal == first_signal

    def test_a_deferred_signal_replays_only_once_ownership_is_visible(self, monkeypatch):
        signal_module = test_runner_server.signal
        deferred_signal, previous_handler, process_marker = signal_module.SIGTERM, object(), object()
        server = test_runner_server.SharedTestServer()
        events: list = []

        def record_stop_call():
            assert test_runner_server._spawn_publication_active is False
            assert test_runner_server._deferred_spawn_signal is None
            assert (server.proc, server.process_group_id, server.started_here) == (process_marker, 47000, True)
            events.append("stop")

        def record_handler_restore(signum, handler):
            assert events == ["stop"]
            events.append(("restore", signum, handler))

        def record_reraise(pid, signum):
            assert events == ["stop", ("restore", deferred_signal, previous_handler)]
            events.append(("kill", pid, signum))

        monkeypatch.setattr(test_runner_server, "_ACTIVE", server)
        monkeypatch.setattr(test_runner_server, "_spawn_publication_active", False)
        monkeypatch.setattr(test_runner_server, "_deferred_spawn_signal", None)
        monkeypatch.setattr(test_runner_server, "_previous_handlers", {deferred_signal: previous_handler})
        monkeypatch.setattr(server, "stop", record_stop_call)
        monkeypatch.setattr(test_runner_server, "signal", SimpleNamespace(SIG_DFL=signal_module.SIG_DFL, signal=record_handler_restore))
        monkeypatch.setattr(test_runner_server, "os", SimpleNamespace(getpid=lambda: 47001, kill=record_reraise))

        with test_runner_server._publish_spawn_ownership():
            assert test_runner_server._spawn_publication_active is True
            test_runner_server._signal_teardown(deferred_signal, None)
            assert test_runner_server._deferred_spawn_signal == deferred_signal
            server.proc, server.process_group_id, server.started_here = process_marker, 47000, True
            assert events == []

        assert events == ["stop", ("restore", deferred_signal, previous_handler), ("kill", 47001, deferred_signal)]
        assert test_runner_server._spawn_publication_active is False
        assert test_runner_server._deferred_spawn_signal is None

    def test_publication_globals_reset_when_the_body_raises(self, monkeypatch):
        publication_failure = RuntimeError("publication failed")
        monkeypatch.setattr(test_runner_server, "_spawn_publication_active", False)
        monkeypatch.setattr(test_runner_server, "_deferred_spawn_signal", None)
        with pytest.raises(RuntimeError) as excinfo, test_runner_server._publish_spawn_ownership():
            assert test_runner_server._spawn_publication_active is True
            test_runner_server._deferred_spawn_signal = test_runner_server.signal.SIGTERM
            raise publication_failure

        assert excinfo.value is publication_failure
        assert test_runner_server._spawn_publication_active is False
        assert test_runner_server._deferred_spawn_signal is None

    def test_teardown_handlers_are_registered_and_restored(self, monkeypatch):
        teardown_signals = test_runner_server._TEARDOWN_SIGNALS
        previous_by_signal = {signum: object() for signum in teardown_signals}
        signal_calls: list[tuple] = []
        sigint = test_runner_server.signal.SIGINT
        assert sigint in teardown_signals
        monkeypatch.setattr(test_runner_server, "_previous_handlers", {})
        monkeypatch.setattr(test_runner_server, "_atexit_registered", True)
        monkeypatch.setattr(test_runner_server, "signal", SimpleNamespace(signal=lambda signum, handler: signal_calls.append((signum, handler)) or previous_by_signal[signum]))
        test_runner_server._install_last_resort_teardown()

        install_calls = [(signum, test_runner_server._signal_teardown) for signum in teardown_signals]
        assert signal_calls == install_calls
        assert test_runner_server._previous_handlers[sigint] is previous_by_signal[sigint]

        test_runner_server._remove_last_resort_teardown()

        assert signal_calls == install_calls + [(signum, previous_by_signal[signum]) for signum in teardown_signals]
        assert test_runner_server._previous_handlers == {}


def test_runner_port_holders_queries_listening_pids_only(monkeypatch):
    calls: list[tuple] = []

    def fake_run(command, *, capture_output, text, timeout):
        calls.append((command, capture_output, text, timeout))
        return SimpleNamespace(stdout="41001\n41002\n")

    monkeypatch.setattr(test_runner_server.subprocess, "run", fake_run)

    assert test_runner_server.port_holders(6125) == ["41001", "41002"]
    assert calls == [(["lsof", "-nP", "-iTCP:6125", "-sTCP:LISTEN", "-t"], True, True, 10)]


# The runner's STARTUP_TIMEOUT (its wait for the shared backend) and Playwright's
# webServer.timeout (its wait for the backend it starts itself) wait for the same
# `dev.py server --test`, so they are one contract: 300 s whether CI is set or not,
# and LIBREFOLIO_TEST_STARTUP_TIMEOUT (whole seconds) overrides both. They drifted
# once already: Playwright kept `CI ? 300 : 120` after the runner moved to 300
# everywhere. Playwright's half is checked as text, so no node_modules is needed.
STARTUP_TIMEOUT_ENV = "LIBREFOLIO_TEST_STARTUP_TIMEOUT"
DOCUMENTED_STARTUP_TIMEOUT_S = 300
PLAYWRIGHT_CONFIG = test_runner_common.PROJECT_ROOT / "frontend" / "playwright.config.ts"


def runner_startup_timeout(*, ci: str | None, override: str | None) -> int:
    """``_server.STARTUP_TIMEOUT`` as a fresh interpreter computes it with exactly this CI and override.

    The value is fixed at import from the environment, so neither the module this
    process already imported nor an override a developer exported can stand in for it.
    """
    probe_env = {name: value for name, value in os.environ.items() if name not in ("CI", STARTUP_TIMEOUT_ENV)}
    probe_env.update({name: value for name, value in (("CI", ci), (STARTUP_TIMEOUT_ENV, override)) if value is not None})
    result = subprocess.run([sys.executable, "-c", "from scripts.test_runner import _server as m; print(repr(m.STARTUP_TIMEOUT))"], cwd=test_runner_common.PROJECT_ROOT, env=probe_env, capture_output=True, text=True, timeout=60)

    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    printed = result.stdout.strip()
    assert printed.isdigit(), f"STARTUP_TIMEOUT is {printed}, not a whole number of seconds"
    return int(printed)


def webserver_own_timeouts(code: str) -> list[str]:
    """Each ``timeout:`` expression declared on Playwright's ``webServer`` object itself.

    Brace depth inside ``webServer: {…}`` separates its own property from the
    ``timeout`` of the ``gracefulShutdown: {…}`` nested in it.
    """
    opening = re.search(r"\bwebServer\s*:\s*\{", code)
    if opening is None:
        return []
    depth, end = 0, len(code)
    for index in range(opening.end() - 1, len(code)):
        depth += {"{": 1, "}": -1}.get(code[index], 0)
        if depth == 0:
            end = index
            break
    body = code[opening.end() : end]
    return [match[1].strip() for match in re.finditer(r"\btimeout\s*:\s*([^,\n}]+)", body) if body.count("{", 0, match.start()) == body.count("}", 0, match.start())]


def playwright_startup_timeout_drift(config_text: str, runner_default_s: int) -> list[str]:
    """Every way playwright.config.ts's webServer wait departs from the runner's ([] = none).

    Pure on text, so a control can feed it a drifted config. It anchors on the chain
    ``const RAW = process.env.<env> ?? '<N>'`` → ``const S = Number(RAW)`` →
    ``webServer.timeout: S * 1000``, whatever RAW and S are called.
    """
    code = re.sub(r"^[ \t]*//.*$", "", config_text, flags=re.M)  # full-line comments may quote the old expression
    reads = len(re.findall(rf"process\.env\.{STARTUP_TIMEOUT_ENV}\b", code))
    raw = re.search(rf"^[ \t]*const\s+(\w+)\s*=\s*process\.env\.{STARTUP_TIMEOUT_ENV}\s*\?\?\s*'(\d+)'\s*;?[ \t]*$", code, re.M)
    raw_name = raw[1] if raw else "STARTUP_TIMEOUT_RAW"
    seconds = re.search(rf"^[ \t]*const\s+(\w+)\s*=\s*Number\(\s*{raw_name}\s*\)\s*;?[ \t]*$", code, re.M)
    seconds_name = seconds[1] if seconds else "STARTUP_TIMEOUT_S"
    timeouts = webserver_own_timeouts(code)
    checks = [
        (reads == 1, f"process.env.{STARTUP_TIMEOUT_ENV} is read {reads} times: its default and its override must come from one declaration"),
        (raw is not None, f"no `const … = process.env.{STARTUP_TIMEOUT_ENV} ?? '<seconds>';` declaration"),
        (raw is None or int(raw[2]) == runner_default_s, f"Playwright defaults to {raw[2] if raw else '?'} s, the runner's STARTUP_TIMEOUT to {runner_default_s} s"),
        (seconds is not None, f"no `const … = Number({raw_name});`: the webServer wait is not derived from the override"),
        (len(timeouts) == 1, f"webServer declares {len(timeouts)} timeout properties of its own, not 1"),
        (not any(re.search(r"\bprocess\.env\.CI\b", timeout) for timeout in timeouts), f"webServer timeout branches on process.env.CI again: {timeouts}"),
        (any(re.fullmatch(rf"{seconds_name}\s*\*\s*1000", timeout) for timeout in timeouts), f"webServer timeout is {timeouts}, not `{seconds_name} * 1000`"),
    ]
    return [reason for holds, reason in checks if not holds]


@pytest.mark.parametrize(("ci", "override", "expected_s"), [(None, None, DOCUMENTED_STARTUP_TIMEOUT_S), ("true", None, DOCUMENTED_STARTUP_TIMEOUT_S), (None, "45", 45), ("true", "45", 45)], ids=["default-ci-absent", "default-ci-present", "override-ci-absent", "override-ci-present"])
def test_startup_timeout_ignores_ci_and_honours_the_override(ci, override, expected_s):
    assert runner_startup_timeout(ci=ci, override=override) == expected_s


def test_playwright_webserver_waits_exactly_as_long_as_the_runner():
    # Playwright's default is compared with the runner's own, read from a fresh
    # import, not with a second literal 300: moving either side alone fails here.
    runner_default_s = runner_startup_timeout(ci=None, override=None)

    assert runner_default_s == DOCUMENTED_STARTUP_TIMEOUT_S
    assert playwright_startup_timeout_drift(PLAYWRIGHT_CONFIG.read_text(encoding="utf-8"), runner_default_s) == []


@pytest.mark.parametrize(
    ("edit", "runner_default_s", "expected_reason"),
    [
        pytest.param(("timeout: STARTUP_TIMEOUT_S * 1000,", "timeout: process.env.CI ? 300 * 1000 : 120 * 1000,"), DOCUMENTED_STARTUP_TIMEOUT_S, "branches on process.env.CI", id="old-ci-ternary"),
        pytest.param(("?? '300'", "?? '120'"), DOCUMENTED_STARTUP_TIMEOUT_S, "Playwright defaults to 120 s", id="playwright-default-120"),
        pytest.param(None, 120, "the runner's STARTUP_TIMEOUT to 120 s", id="runner-default-moved"),
        pytest.param(("Number(STARTUP_TIMEOUT_RAW)", "120"), DOCUMENTED_STARTUP_TIMEOUT_S, "not derived from the override", id="override-ignored"),
        pytest.param(("timeout: STARTUP_TIMEOUT_S * 1000,", f"timeout: Number(process.env.{STARTUP_TIMEOUT_ENV} || 120) * 1000,"), DOCUMENTED_STARTUP_TIMEOUT_S, "is read 2 times", id="override-read-twice"),
        pytest.param(("timeout: STARTUP_TIMEOUT_S * 1000,", ""), DOCUMENTED_STARTUP_TIMEOUT_S, "declares 0 timeout properties", id="webserver-timeout-dropped"),
    ],
)
def test_playwright_wait_check_rejects_a_drifted_config(edit, runner_default_s, expected_reason):
    # The control for the check above: the real config, drifted the way it could
    # drift, must be rejected — otherwise an empty drift list would prove nothing.
    config_text = PLAYWRIGHT_CONFIG.read_text(encoding="utf-8")
    if edit is not None:
        anchor, replacement = edit
        assert config_text.count(anchor) == 1, f"control anchor {anchor!r} is not in playwright.config.ts exactly once: re-anchor this control"
        config_text = config_text.replace(anchor, replacement)

    drift = playwright_startup_timeout_drift(config_text, runner_default_s)

    assert any(expected_reason in reason for reason in drift), f"{expected_reason!r} not reported, drift={drift}"


# ── Contract 7 — the exec_unmasked spawn wrapper (and the masking around it) ──


class TestExecUnmaskedWrapper:
    def test_a_successful_start_masks_signals_around_an_authenticated_unmasked_launch(self, monkeypatch):
        # One successful start(), three contracts: the child is launched through
        # exec_unmasked (never a preexec_fn); SIGINT/SIGTERM/SIGHUP stay blocked
        # from before Popen until after ownership is published, so no signal can
        # land while proc exists but nothing owns it; and with lsof unavailable
        # (port_holders answers "nothing listening") the lane-authenticated
        # health check is what proves the listener is ours.
        lane_id = "runner-lsof-unavailable-lane"
        monkeypatch.setenv("LIBREFOLIO_TEST_LANE_ID", lane_id)
        order: list[str] = []
        server = _PublicationHookServer(lambda: order.append("started_here=True"))
        process = FakeProc(45011, [None, None])
        previous_mask, sigmask_calls, popen_commands, popen_kwargs = object(), [], [], {}
        lsof_calls, health_calls, ready = [], [], []

        def fake_pthread_sigmask(how, mask):
            blocking = how == test_runner_server.signal.SIG_BLOCK
            assert blocking or how == test_runner_server.signal.SIG_SETMASK
            sigmask_calls.append(("block", frozenset(mask)) if blocking else ("restore", mask))
            order.append("block" if blocking else "restore")
            return previous_mask if blocking else frozenset()

        def fake_popen(command, **kwargs):
            order.append("popen")
            popen_commands.append(command)
            popen_kwargs.update(kwargs)
            return process

        def unavailable_lsof(command, *, capture_output, text, timeout):
            lsof_calls.append((command, capture_output, text, timeout))
            raise FileNotFoundError("lsof unavailable")

        class AuthenticatedOpener:
            def open(self, url, *, timeout):
                health_calls.append((url, timeout))
                return FakeHealthResponse(200, lane_headers(lane_id))

        monkeypatch.setattr(test_runner_server.signal, "pthread_sigmask", fake_pthread_sigmask)
        monkeypatch.setattr(test_runner_server.subprocess, "Popen", fake_popen)
        monkeypatch.setattr(test_runner_server.subprocess, "run", unavailable_lsof)
        # The build step before the spawn (C-94) would otherwise reach this lsof stand-in: it always succeeds here.
        monkeypatch.setattr(test_runner_server, "build_server_prerequisites", lambda *_args, **_kwargs: True, raising=False)
        monkeypatch.setattr(test_runner_server.os, "getpgid", lambda _pid: (order.append("getpgid"), 45010)[1])
        monkeypatch.setattr(test_runner_server.urllib.request, "build_opener", lambda *_handlers: AuthenticatedOpener())
        monkeypatch.setattr(test_runner_server, "print_success", ready.append)
        forbid(monkeypatch, server, "stop", "a healthy authenticated lane must not be stopped")
        patch_clock(monkeypatch, test_runner_server, forbid_sleep="a successful first poll must not sleep")

        assert server.start() is True

        wrapper = str(test_runner_common.PROJECT_ROOT / "scripts" / "exec_unmasked.py")
        assert popen_commands == [[sys.executable, wrapper, sys.executable, "dev.py", "server", "--test", "--no-reload", "--no-scheduler", "--workers", "1"]]
        assert "preexec_fn" not in popen_kwargs
        assert (popen_kwargs["shell"], popen_kwargs["start_new_session"]) == (False, True)
        # Masking brackets the whole publication, and the restore hands back the
        # exact mask SIG_BLOCK returned, so pre-existing blocks are not dropped.
        assert order == ["block", "popen", "getpgid", "started_here=True", "restore"]
        assert sigmask_calls == [("block", frozenset({test_runner_server.signal.SIGINT, test_runner_server.signal.SIGTERM, test_runner_server.signal.SIGHUP})), ("restore", previous_mask)]
        expected_lsof = (["lsof", "-nP", f"-iTCP:{server.port}", "-sTCP:LISTEN", "-t"], True, True, 10)
        assert lsof_calls == [expected_lsof, expected_lsof]
        assert health_calls == [(test_runner_server.health_url(server.port), 2.0)]
        assert (process.poll_calls, server.process_group_id, server.started_here) == (2, 45010, True)
        assert ready == [f"Shared backend ready on port {server.port}"]

    def test_main_unblocks_the_spawn_signals_and_forwards_the_exact_exec_contract(self, monkeypatch):
        target_argv = [sys.executable, "-c", "raise SystemExit(0)", "argument with spaces"]
        sigmask_calls, exec_calls = [], []
        monkeypatch.setattr(exec_unmasked.sys, "argv", [str(test_runner_common.PROJECT_ROOT / "scripts" / "exec_unmasked.py"), *target_argv])
        monkeypatch.setattr(exec_unmasked.signal, "pthread_sigmask", lambda how, mask: sigmask_calls.append((how, frozenset(mask))) or frozenset(), raising=False)
        monkeypatch.setattr(exec_unmasked.os, "execvpe", lambda executable, argv, environment: exec_calls.append((executable, argv, environment)))
        assert exec_unmasked.main() == 127

        assert sigmask_calls == [(exec_unmasked.signal.SIG_UNBLOCK, frozenset({exec_unmasked.signal.SIGINT, exec_unmasked.signal.SIGTERM, exec_unmasked.signal.SIGHUP}))]
        assert exec_calls == [(target_argv[0], target_argv, exec_unmasked.os.environ)]
        assert exec_calls[0][2] is exec_unmasked.os.environ

    @pytest.mark.skipif(not hasattr(test_runner_server.signal, "pthread_sigmask") or not hasattr(test_runner_server.os, "killpg"), reason="POSIX pthread_sigmask and process groups are required")
    def test_real_wrapper_child_exits_on_group_sigterm_from_a_threaded_masked_parent(self, tmp_path):
        # The one real-signal regression: a live thread in the parent must not
        # keep the wrapper's child from inheriting an unmasked SIGTERM.
        signal_module = test_runner_server.signal
        spawn_signals = {signal_module.SIGINT, signal_module.SIGTERM, signal_module.SIGHUP}
        child_program = "import signal\nsignal.signal(signal.SIGTERM, signal.SIG_DFL)\nprint('ready', flush=True)\nwhile True:\n    signal.pause()\n"
        worker_ready, release_worker = threading.Event(), threading.Event()
        worker = threading.Thread(target=lambda: (worker_ready.set(), release_worker.wait()), name="exec-unmasked-regression-worker")
        process, child_group, stdout, stderr, returncode, cleanup_used_sigkill = None, None, "", "", None, False
        worker.start()
        try:
            assert worker_ready.wait(5.0), "worker did not become ready before the deadline"
            assert worker.is_alive()
            previous_mask = signal_module.pthread_sigmask(signal_module.SIG_BLOCK, spawn_signals)
            try:
                assert spawn_signals <= signal_module.pthread_sigmask(signal_module.SIG_BLOCK, set())
                wrapper = str(test_runner_common.PROJECT_ROOT / "scripts" / "exec_unmasked.py")
                process = subprocess.Popen([sys.executable, wrapper, sys.executable, "-u", "-c", child_program], cwd=tmp_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            finally:
                signal_module.pthread_sigmask(signal_module.SIG_SETMASK, previous_mask)

            assert process.stdout is not None
            readable, _, _ = select.select([process.stdout], [], [], 5.0)
            assert readable, "child did not publish readiness before the deadline"
            assert process.stdout.readline() == "ready\n"
            child_group = os.getpgid(process.pid)
            assert child_group == process.pid

            os.killpg(child_group, signal_module.SIGTERM)
            try:
                stdout, stderr = process.communicate(timeout=5.0)
            except subprocess.TimeoutExpired:
                pytest.fail("child did not exit promptly after process-group SIGTERM")
            returncode = process.returncode
        finally:
            release_worker.set()
            worker.join(timeout=5.0)
            if process is not None:
                if process.poll() is None:
                    cleanup_group = child_group or process.pid
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(cleanup_group, signal_module.SIGTERM)
                    try:
                        process.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        cleanup_used_sigkill = True
                        with contextlib.suppress(ProcessLookupError):
                            os.killpg(cleanup_group, signal_module.SIGKILL)
                        process.wait(timeout=5.0)
                for stream in (process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()

        assert worker.is_alive() is False
        assert returncode == -signal_module.SIGTERM, f"stdout={stdout!r} stderr={stderr!r} returncode={returncode!r}"
        assert cleanup_used_sigkill is False


# ── Contract 8 — _TestingServerManager: port ownership must fail closed ────


def test_check_port_available_sets_reuseaddr_before_the_fallback_bind(monkeypatch):
    calls: list[tuple] = []

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def setsockopt(self, level, option, value):
            calls.append(("setsockopt", level, option, value))

        def bind(self, address):
            calls.append(("bind", address))

    def unavailable_lsof(*_args, **_kwargs):
        raise FileNotFoundError("lsof unavailable")

    def fake_socket(family, socket_type):
        assert (family, socket_type) == (socket.AF_INET, socket.SOCK_STREAM)
        return FakeSocket()

    monkeypatch.setattr(subprocess, "run", unavailable_lsof)
    monkeypatch.setattr(socket, "socket", fake_socket)

    assert test_server_helper_module.check_port_available(6125) == (True, None)
    assert calls == [("setsockopt", socket.SOL_SOCKET, socket.SO_REUSEADDR, 1), ("bind", (test_server_helper_module.TEST_SERVER_HOST, 6125))]


class TestTestingServerManagerFailsClosed:
    """A listener is reused only when this very process demonstrably owns it.

    ``port_holder_pids`` returning ``None`` means lsof could not establish
    ownership at all; the lane-authenticated health check is then the only
    acceptable substitute, since only our own in-process server can answer that
    private token. Any concrete foreign PID set fails closed even when healthy.
    """

    @pytest.mark.parametrize(
        ("holder_kind", "lane_kind", "expected", "diagnostic"),
        [
            pytest.param("self", "exact", True, "Reusing test server already listening", id="same-process-healthy"),
            pytest.param("self-and-foreign", "exact", False, "Refusing to reuse or terminate", id="foreign-holder"),
            pytest.param("unverifiable", "exact", True, "Reusing test server already listening", id="lsof-less-authenticated"),
            pytest.param("unverifiable", "wrong", False, "Could not verify ownership of occupied port", id="lsof-less-unauthenticated"),
        ],
    )
    def test_occupied_port_is_reused_only_when_ownership_is_proven(self, monkeypatch, capsys, holder_kind, lane_kind, expected, diagnostic):
        lane_id, foreign_pid = "helper-occupied-port-lane", os.getpid() + 1
        monkeypatch.setenv("LIBREFOLIO_TEST_LANE_ID", lane_id)
        holders = {"self": {os.getpid()}, "self-and-foreign": {os.getpid(), foreign_pid}, "unverifiable": None}[holder_kind]
        patch_manager_seams(monkeypatch, available=False, holders=holders, process_info="occupied", health=httpx_lane_probe(lane_id if lane_kind == "exact" else f"{lane_id}-wrong"))
        forbid(monkeypatch, test_server_helper_module.threading, "Thread", "an owned or authenticated listener must be reused, never restarted on a new thread")
        forbid(monkeypatch, test_server_helper_module.os, "kill", "os.kill must never be called for a listener this process did not start")
        manager = test_server_helper_module._TestingServerManager()
        assert manager.start_server() is expected

        assert manager.server_thread is None
        output = capsys.readouterr().out
        assert diagnostic in output
        assert holder_kind != "self-and-foreign" or str(foreign_pid) in output

    @pytest.mark.parametrize(
        ("holder_kind", "thread_dies", "expected", "diagnostic"),
        [
            pytest.param("foreign", False, False, "Refusing to reuse or terminate", id="foreign-wins-bind-race"),
            pytest.param("self", True, False, "thread exited", id="own-thread-died"),
            pytest.param("unverifiable", False, True, "", id="lsof-less-live-thread"),
            pytest.param("unverifiable", True, False, "thread exited", id="lsof-less-dead-thread"),
        ],
    )
    def test_post_launch_readiness_requires_a_live_thread_and_an_owned_port(self, monkeypatch, capsys, holder_kind, thread_dies, expected, diagnostic):
        # The free-port preflight and uvicorn's bind are not atomic, so health is
        # necessary but never proof of ownership.
        lane_id, foreign_pid = "helper-post-launch-lane", os.getpid() + 1
        monkeypatch.setenv("LIBREFOLIO_TEST_LANE_ID", lane_id)
        holders = {"self": {os.getpid()}, "foreign": {foreign_pid}, "unverifiable": None}[holder_kind]
        manager = test_server_helper_module._TestingServerManager()
        manager.server_started.set()
        created_threads = patch_fake_server_thread(monkeypatch, alive=True)
        health_calls: list[tuple] = []

        def kill_thread_on_probe():
            if thread_dies:
                created_threads[0].alive = False

        patch_manager_seams(monkeypatch, available=True, holders=holders, health=httpx_lane_probe(lane_id, calls=health_calls, on_call=kill_thread_on_probe))
        patch_clock(monkeypatch, test_server_helper_module, forbid_sleep="the post-launch decision must not sleep")

        assert manager.start_server() is expected

        assert len(created_threads) == 1 and created_threads[0].started is True
        assert len(health_calls) == 1
        assert manager.attached_to_shared is False
        output = capsys.readouterr().out
        assert diagnostic in output
        assert holder_kind != "foreign" or str(foreign_pid) in output


# ── `mkdocs gallery --no-populate` — reuse the lane DB, stand global-setup down ──
#
# "Skip DB population" used to skip it without telling Playwright, so its
# global-setup ran its own `populate_mock_data --force --with-reports` at every
# run: another dataset, without the static resources, written under a backend
# that was already serving. Now `--no-populate` verifies the lane's existing
# database and ensures its E2E users *before* Playwright starts, both branches
# hand over with LF_SETUP_DONE, and a missing database is an error — never a
# populate after all.

GLOBAL_SETUP = test_runner_common.PROJECT_ROOT / "frontend" / "e2e" / "global-setup.ts"
GALLERY_ARGV = ["dev.py", "mkdocs", "gallery", "--desktop-only", "--workers", "2", "--test-port", "6196"]


def global_setup_stand_down_value() -> str:
    """The ``LF_SETUP_DONE`` value Playwright's global-setup stands down on, read from global-setup.ts.

    The command is held to the literal the other side compares against, not to a
    second copy of ``"1"``: moving either side alone fails the check.
    """
    values = set(re.findall(r"process\.env\.LF_SETUP_DONE\s*===\s*['\"]([^'\"]*)['\"]", GLOBAL_SETUP.read_text(encoding="utf-8")))
    assert len(values) == 1, f"global-setup.ts compares LF_SETUP_DONE against {sorted(values)}, not exactly one value: re-anchor this check"
    return values.pop()


def seed_lane_db(db_path: Path) -> None:
    """An earlier run's database, as far as an existence check can tell: bytes, never opened as SQLite."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(b"synthetic database left by an earlier gallery run\n")


@pytest.fixture
def gallery_lane(runtime_env, tmp_path):
    """A synthetic lane under ``tmp_path``, with every way out of the process closed.

    The lane passes ``validate_test_data_dir``'s production-alias checks honestly: no
    guard is patched. ``_ensure_test_users`` becomes a recorder answering
    ``lane.ensure_users``, and any ``subprocess.run``/``Popen`` fails the test, so
    nothing here can populate a database, create a user or start Playwright for real;
    a test re-opens only the seam it asserts on. LF_SETUP_DONE starts absent, so
    finding it in Playwright's environment proves the command set it.
    """
    root = tmp_path / "synthetic-test-data"
    lane = SimpleNamespace(root=root, db=root.resolve() / "sqlite" / "app.db", ensure_users=True, events=[])
    runtime_env.setenv("LIBREFOLIO_TEST_DATA_DIR", str(root))
    runtime_env.delenv("LF_SETUP_DONE", raising=False)
    runtime_env.setattr(test_runner_package, "_ensure_test_users", lambda: (lane.events.append("ensure-users"), lane.ensure_users)[1])
    for name in ("run", "Popen"):
        forbid(runtime_env, subprocess, name, f"subprocess.{name} reached: a gallery contract test must never populate, create users or start Playwright for real")
    return lane


def run_gallery(runtime_env, lane, *flags: str) -> tuple[int, dict]:
    """``./dev.py mkdocs gallery <flags>`` through the real parser; the Playwright launch is recorded, not run."""
    launch: dict = {}

    def fake_popen(command, **kwargs):
        lane.events.append("playwright")
        launch.update(command=command, env=dict(kwargs["env"]))
        return SimpleNamespace(stdout=iter(()), wait=lambda: 0, returncode=0)

    runtime_env.setattr(dev, "HAS_ARGCOMPLETE", False)
    runtime_env.setattr(dev, "check_port_in_use", lambda _port: [])
    # The gallery's build step before Playwright (C-94) is otherwise a real `dev.py server --build-only`: it always succeeds here.
    runtime_env.setattr(test_runner_server, "build_server_prerequisites", lambda *_args, **_kwargs: True, raising=False)
    runtime_env.setattr(subprocess, "Popen", fake_popen)
    runtime_env.setattr(sys, "argv", [*GALLERY_ARGV, *flags])
    return dev.main(), launch


class TestGalleryReusesTheLaneDb:
    """``dev._reuse_gallery_test_db()``: global-setup may stand down only once the lane DB and its users exist."""

    @pytest.mark.parametrize("layout", ["no-lane-root", "sqlite-dir-only"])
    def test_a_missing_lane_db_is_refused_without_creating_it_or_any_user(self, gallery_lane, tmp_path, capsys, layout):
        # The check must not materialise what it looks for: an empty app.db left
        # behind would be "reused" by the next --no-populate run.
        if layout == "sqlite-dir-only":
            gallery_lane.db.parent.mkdir(parents=True)
        tree_before = tree_snapshot(tmp_path)

        assert dev._reuse_gallery_test_db() is False

        output = capsys.readouterr().out
        assert str(gallery_lane.db) in output
        assert "run once without --no-populate" in output
        assert gallery_lane.events == []
        assert tree_snapshot(tmp_path) == tree_before

    def test_an_existing_lane_db_is_reused_untouched_once_its_users_are_ensured(self, gallery_lane, tmp_path, capsys):
        seed_lane_db(gallery_lane.db)
        tree_before = tree_snapshot(tmp_path)

        assert dev._reuse_gallery_test_db() is True

        assert gallery_lane.events == ["ensure-users"]
        # The lane override decides which database is reused, not the default test root.
        assert f"reusing {gallery_lane.db}" in capsys.readouterr().out
        # Reused as it is: neither recreated nor rewritten by the check itself.
        assert tree_snapshot(tmp_path) == tree_before

    def test_users_that_cannot_be_ensured_refuse_the_reuse(self, gallery_lane, capsys):
        seed_lane_db(gallery_lane.db)
        gallery_lane.ensure_users = False

        assert dev._reuse_gallery_test_db() is False

        output = capsys.readouterr().out
        assert gallery_lane.events == ["ensure-users"]
        assert "Failed to create test users" in output
        assert "reusing" not in output

    @pytest.mark.parametrize(("production", "reason"), [pytest.param("configured", OVERLAP_ERROR, id="configured-production"), pytest.param("marked", MARKED_ERROR, id="marked-production")])
    def test_a_lane_the_resolver_rejects_is_refused_before_any_user_is_created(self, gallery_lane, runtime_env, tmp_path, capsys, production, reason):
        # A database really is there: only the resolver's ValueError stands between
        # it and _ensure_test_users writing E2E users into production data.
        production_root = tmp_path / "synthetic-production-data"
        lane_root = production_root / "test-lane"
        seed_lane_db(lane_root / "sqlite" / "app.db")
        if production == "configured":
            runtime_env.setenv("LIBREFOLIO_DATA_DIR", str(production_root))
        else:
            (production_root / backend_config.PRODUCTION_DATA_MARKER).write_text("synthetic production marker\n", encoding="utf-8")
        runtime_env.setenv("LIBREFOLIO_TEST_DATA_DIR", str(lane_root))
        with pytest.raises(ValueError, match=reason) as rejected:  # the precondition, verified: this resolver refuses this lane
            backend_config.get_test_data_dir()
        tree_before = tree_snapshot(tmp_path)

        assert dev._reuse_gallery_test_db() is False

        assert gallery_lane.events == []
        assert str(rejected.value) in capsys.readouterr().out
        assert tree_snapshot(tmp_path) == tree_before


class TestGalleryHandsTheSetupToPlaywright:
    """``mkdocs gallery``: Playwright starts only after the DB and its users are ready, and is told so."""

    @pytest.mark.parametrize("no_populate", [False, True], ids=["populate", "no-populate"])
    def test_playwright_starts_last_and_is_told_to_skip_its_own_setup(self, gallery_lane, runtime_env, no_populate):
        # Both branches prepare the DB and its users before Playwright, so both must
        # hand over. Under --no-populate subprocess.run stays forbidden: the command
        # populates nothing, and LF_SETUP_DONE stops global-setup doing it instead.
        if no_populate:
            seed_lane_db(gallery_lane.db)
        else:
            runtime_env.setattr(subprocess, "run", lambda command, **_kwargs: (gallery_lane.events.append("populate"), subprocess.CompletedProcess(command, 0))[1])
        exit_code, launch = run_gallery(runtime_env, gallery_lane, *(("--no-populate",) if no_populate else ()))

        assert exit_code == 0
        assert gallery_lane.events == (["ensure-users", "playwright"] if no_populate else ["populate", "ensure-users", "playwright"])
        assert "gallery.spec.ts" in launch["command"]
        assert launch["env"]["LF_SETUP_DONE"] == global_setup_stand_down_value()
        # The database the command verified is the one Playwright's backend will serve.
        assert launch["env"]["LIBREFOLIO_TEST_DATA_DIR"] == str(gallery_lane.root)

    @pytest.mark.parametrize("cause", ["missing-db", "users-not-ensured"])
    def test_a_refused_reuse_exits_1_before_playwright_and_never_falls_back_to_populate(self, gallery_lane, runtime_env, cause):
        if cause == "users-not-ensured":
            seed_lane_db(gallery_lane.db)
            gallery_lane.ensure_users = False
        exit_code, launch = run_gallery(runtime_env, gallery_lane, "--no-populate")

        assert exit_code == 1
        # No Playwright launch was recorded, and subprocess.run is still forbidden:
        # a refused reuse never turns into a populate after all.
        assert launch == {}
        assert gallery_lane.events == ([] if cause == "missing-db" else ["ensure-users"])


# ── Frontend build staleness — the root CHANGELOG files are inputs of the build (lot CL) ──
#
# `cli_base.check_frontend_needs_build()` says whether `frontend/build` must be
# rebuilt by comparing the mtime of `build/index.html` with what the build reads:
# `frontend/src`, the frontend config files and the Tool codegen inputs. The
# frontend also bundles the root CHANGELOG files — `CHANGELOG.md` inline through
# vite's `?raw`, each `CHANGELOG.<lang>.md` as a lazy chunk — so a changelog
# edited after the last build must make the build stale as well: otherwise the
# app keeps serving the old text, and an E2E that reads the file
# (`layout/changelog-locale.spec.ts`) disagrees with the bundle it runs against.
#
# Not all of `frontend/src` is an input of the bundle, though (H-24). A file
# there is left out of the comparison when, read relative to `src`:
#   - a part of its path starts with `.`: the Finder's `.DS_Store`, an
#     AppleDouble `._App.svelte`, a `.gitignore`, the translation catalogue's
#     stamp `lib/i18n/.generated`, anything inside a hidden folder;
#   - its name contains `.test.` or `.spec.`: a Vitest file;
#   - one of its folders is named exactly `__tests__` or `__mocks__`: Vitest's
#     harnesses, fixtures and module mocks, which no app code imports.
# None of them reaches the bundle, so one newer than the build must not force a
# rebuild of minutes — as a `.DS_Store` the Finder dropped into `src` once did.
# Everything else still counts, the near-misses included (`latest.ts`,
# `testing/helpers.ts`, `lib/tests/x.ts`, `lib/__tests__.ts`), and a folder
# above `src`, in the checkout's own path, hides nothing.
#
# The project root is a tree under `tmp_path` and every mtime is set with
# `os.utime`: no clock, no sleep, no repository file touched.

#: The build's mtime, and the instants an hour either side of it where every other input is placed.
BUILD_MTIME = 1_800_000_000
OLDER_MTIME = BUILD_MTIME - 3600
NEWER_MTIME = BUILD_MTIME + 3600


def make_frontend_project(monkeypatch, root: Path) -> dict[str, Path]:
    """A built frontend under the project root ``root``, every input an hour older than the build.

    Inputs: one ``frontend/src`` file, ``frontend/package.json`` and the root
    markdown files a test may move forward — the two changelogs and a README that
    is not one. The Tool codegen inputs are absent here, verified rather than
    assumed: they could otherwise answer either way for the guards below.
    ``cli_base.get_project_root`` answers ``root`` for the rest of the test.
    """
    files = {
        "index.html": root / "frontend" / "build" / "index.html",
        "source": root / "frontend" / "src" / "app.html",
        "package.json": root / "frontend" / "package.json",
        "CHANGELOG.md": root / "CHANGELOG.md",
        "CHANGELOG.it.md": root / "CHANGELOG.it.md",
        "README.md": root / "README.md",
    }
    for path in files.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic build input\n", encoding="utf-8")
        os.utime(path, (OLDER_MTIME, OLDER_MTIME))
    os.utime(files["index.html"], (BUILD_MTIME, BUILD_MTIME))
    monkeypatch.setattr(cli_base, "get_project_root", lambda: root)
    assert [path for path in cli_base._tool_contract_sources(root) if path.exists()] == [], "a Tool codegen input exists under the fake root"
    return files


@pytest.fixture
def frontend_project(monkeypatch, tmp_path) -> dict[str, Path]:
    """``make_frontend_project`` with ``tmp_path`` itself as the project root."""
    return make_frontend_project(monkeypatch, tmp_path)


# The translation catalogue is an input of the build too (workstream U, step U-2): `src/lib/i18n/<lang>.json` is
# generated from its sources — `src/lib/i18n/base/`, the subsystem folders, the plugins' `i18n/` — by
# `scripts/i18n_catalog.py`, and is not tracked. So a checkout without the generated files needs the build that writes
# them even when the bundle is fresh, and a source or the generator newer than the build makes it stale.
CATALOGUE_LANGUAGES = ("en", "it", "fr", "es")


@pytest.fixture
def frontend_catalogue(frontend_project, tmp_path) -> dict[str, Path]:
    """``frontend_project`` with a translation catalogue, every file of it an hour older than the build.

    Its sources (``frontend/src/lib/i18n/base/<lang>.json`` and one plugin fragment,
    ``backend/app/services/brim_providers/broker_x/i18n/en.json`` beside its ``plugin.py``), the
    generator ``scripts/i18n_catalog.py`` and the four catalogues it generates,
    ``frontend/src/lib/i18n/<lang>.json``. That the probe sees the four is verified, not assumed.
    """
    i18n = tmp_path / "frontend" / "src" / "lib" / "i18n"
    plugin = tmp_path / "backend" / "app" / "services" / "brim_providers" / "broker_x"
    files = {
        **{f"base/{language}.json": i18n / "base" / f"{language}.json" for language in CATALOGUE_LANGUAGES},
        **{f"generated/{language}.json": i18n / f"{language}.json" for language in CATALOGUE_LANGUAGES},
        "plugin.py": plugin / "plugin.py",
        "fragment": plugin / "i18n" / "en.json",
        "generator": tmp_path / "scripts" / "i18n_catalog.py",
    }
    for path in files.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n" if path.suffix == ".json" else "# synthetic build input\n", encoding="utf-8")
        os.utime(path, (OLDER_MTIME, OLDER_MTIME))
    assert cli_base.generated_catalogs(tmp_path) == [i18n / f"{language}.json" for language in CATALOGUE_LANGUAGES], "premise: the probe sees the four generated catalogues"
    assert [path for path in cli_base._tool_contract_sources(tmp_path) if path.exists()] == [], "a Tool codegen input exists under the fake root"
    return {**frontend_project, **files}


# The files under `frontend/src` the H-24 rule leaves out, by their path relative to `src`, each with what it is.
NOT_BUNDLED_SOURCES = {
    ".DS_Store": "the Finder's folder metadata",
    "lib/components/.DS_Store": "the Finder's folder metadata, in a subfolder",
    "lib/components/._App.svelte": "an AppleDouble file, the metadata macOS keeps beside App.svelte on a volume without extended attributes",
    "lib/api/.gitignore": "a hidden file",
    "lib/i18n/.generated": "the translation catalogue's stamp",
    "lib/.cache/x.ts": "a file inside a hidden folder",
    "lib/.cache/vite/x.ts": "a file deeper inside a hidden folder",
    "x.test.ts": "a Vitest file",
    "lib/components/x.dom.test.ts": "a Vitest file",
    "lib/utils/x.spec.ts": "a Vitest file",
    "routes/x/page.test.ts": "a Vitest file",
    "__tests__/component.ts": "a Vitest harness",
    "lib/charts/__tests__/fixtures/series.json": "a Vitest fixture",
    "__mocks__/$app/navigation.ts": "a Vitest module mock",
}

# The files under `frontend/src` it must keep counting: ordinary inputs, then the near-misses of each of its clauses — a
# name or a folder that merely contains "test", "spec" or "__tests__".
BUNDLED_SOURCES = {
    "lib/utils/format.ts": "a module",
    "lib/components/App.svelte": "a component",
    "lib/data/currencies.json": "a JSON module",  # not under lib/i18n/base/, where a JSON would make a catalogue due and answer True for that reason
    "lib/i18n/assets/prefixes.txt": "a subsystem's key prefixes, read by the catalogue generator",
    "latest.ts": "'test' in the name, not '.test.'",
    "contest.svelte": "'test' in the name, not '.test.'",
    "lib/utils/x.testing.ts": "'.test' in the name, not '.test.'",
    "inspect.ts": "'spec' in the name, not '.spec.'",
    "spectrum.ts": "'spec' in the name, not '.spec.'",
    "testing/helpers.ts": "'test' in a folder's name",
    "lib/tests/x.ts": "a folder named tests, not __tests__",
    "lib/my__tests__/x.ts": "a folder whose name merely contains __tests__",
    "lib/__tests__.ts": "a file, not a folder, named like __tests__",
}


def add_newer_source(project: dict[str, Path], relative: str) -> None:
    """Write ``frontend/src/<relative>`` into a ``make_frontend_project`` tree, an hour newer than its build."""
    path = project["source"].parent / relative  # the project's one source is frontend/src/app.html
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetic source\n", encoding="utf-8")
    os.utime(path, (NEWER_MTIME, NEWER_MTIME))


class TestFrontendBuildStaleness:
    """``cli_base.check_frontend_needs_build()``: the build is stale once any input it bundles is newer than it."""

    def test_every_input_older_than_the_build_leaves_it_up_to_date(self, frontend_project):
        assert cli_base.check_frontend_needs_build() is False

    def test_a_frontend_source_newer_than_the_build_needs_a_rebuild(self, frontend_project):
        # The positive control of the guards: the fake root is the one being read,
        # and a newer input does make the answer True.
        os.utime(frontend_project["source"], (NEWER_MTIME, NEWER_MTIME))

        assert cli_base.check_frontend_needs_build() is True

    @pytest.mark.parametrize("changelog", ["CHANGELOG.md", "CHANGELOG.it.md"], ids=["inline-english", "lazy-translation"])
    def test_a_root_changelog_newer_than_the_build_needs_a_rebuild(self, frontend_project, changelog):
        os.utime(frontend_project[changelog], (NEWER_MTIME, NEWER_MTIME))

        assert cli_base.check_frontend_needs_build() is True, f"{changelog} is bundled by the frontend: editing it after the build must make the build stale"

    def test_a_newer_root_file_that_is_not_a_changelog_leaves_it_up_to_date(self, frontend_project):
        os.utime(frontend_project["README.md"], (NEWER_MTIME, NEWER_MTIME))

        assert cli_base.check_frontend_needs_build() is False

    def test_without_catalogue_sources_the_other_inputs_still_decide(self, frontend_project, tmp_path):
        # No frontend/src/lib/i18n/base/en.json: no catalogue to generate, so none can be missing, and the probe answers
        # on its other inputs. It once raised there, and its blanket except turned every answer into False.
        assert cli_base.generated_catalogs(tmp_path) == []
        assert cli_base.check_frontend_needs_build() is False

        os.utime(frontend_project["source"], (NEWER_MTIME, NEWER_MTIME))

        assert cli_base.check_frontend_needs_build() is True

    def test_a_catalogue_older_than_the_build_leaves_it_up_to_date(self, frontend_catalogue):
        assert cli_base.check_frontend_needs_build() is False

    @pytest.mark.parametrize("language", CATALOGUE_LANGUAGES)
    def test_a_missing_generated_catalogue_needs_a_rebuild_though_the_bundle_is_fresh(self, frontend_catalogue, language):
        frontend_catalogue[f"generated/{language}.json"].unlink()

        assert cli_base.check_frontend_needs_build() is True, f"src/lib/i18n/{language}.json is generated, not tracked: a checkout without it needs the build that writes it"

    @pytest.mark.parametrize("newer", ["base/it.json", "fragment", "generator"], ids=["a-base-source", "a-plugin-fragment", "the-generator"])
    def test_a_catalogue_input_newer_than_the_build_needs_a_rebuild(self, frontend_catalogue, newer):
        os.utime(frontend_catalogue[newer], (NEWER_MTIME, NEWER_MTIME))

        assert cli_base.check_frontend_needs_build() is True

    @pytest.mark.parametrize("relative", list(NOT_BUNDLED_SOURCES))
    def test_a_newer_file_that_is_not_an_input_of_the_bundle_leaves_it_up_to_date(self, frontend_project, relative):
        add_newer_source(frontend_project, relative)

        assert cli_base.check_frontend_needs_build() is False, f"H-24: frontend/src/{relative} ({NOT_BUNDLED_SOURCES[relative]}) is not an input of the bundle: newer than the build, it must not force a rebuild"

    @pytest.mark.parametrize("relative", list(BUNDLED_SOURCES))
    def test_a_newer_input_of_the_bundle_needs_a_rebuild(self, frontend_project, relative):
        # Green before H-24 and after it: these keep the cure from leaving out more than it should.
        add_newer_source(frontend_project, relative)

        assert cli_base.check_frontend_needs_build() is True, f"frontend/src/{relative} ({BUNDLED_SOURCES[relative]}) is an input of the bundle: newer than the build, it must make the build stale"

    @pytest.mark.parametrize("left_out", [".DS_Store", "x.test.ts", "__tests__/component.ts"], ids=["a-hidden-file", "a-vitest-file", "a-tests-folder"])
    def test_a_file_left_out_is_skipped_and_the_scan_goes_on(self, frontend_project, left_out):
        # The left-out file sits at most one folder down in `src`, the bundled one two: `rglob` yields the first before
        # the second, so a rule that ended the scan at a left-out file, instead of skipping it, would answer False here.
        add_newer_source(frontend_project, left_out)
        add_newer_source(frontend_project, "lib/utils/format.ts")

        assert cli_base.check_frontend_needs_build() is True, f"frontend/src/lib/utils/format.ts is newer than the build: leaving frontend/src/{left_out} out must not end the scan"

    @pytest.mark.parametrize("folder", [".hidden-root", "__tests__"], ids=["a-hidden-folder", "a-tests-folder"])
    def test_a_folder_above_src_hides_none_of_its_sources(self, monkeypatch, tmp_path, folder):
        # The rule reads each path relative to `src`: a checkout may live under a hidden folder, or one named
        # `__tests__` — here the project root itself is that folder — and its sources must still count.
        project = make_frontend_project(monkeypatch, tmp_path / folder)
        assert cli_base.check_frontend_needs_build() is False

        os.utime(project["source"], (NEWER_MTIME, NEWER_MTIME))

        assert cli_base.check_frontend_needs_build() is True, f"frontend/src/app.html is an input of the bundle: {folder}, a folder above src, must not hide it"


# ── Frontend build staleness — the Tool codegen inputs, their listing recorded at build time (H-24 residual) ──
#
# The Tool codecs a build generates (`cmd_api_sync`) derive from Python sources — `backend/app/schemas`, the Tool
# services, the bundled Tool plugins — and from a few fixed scripts. The probe compared their mtimes with the build's,
# and the three folders' own mtimes as well, so that a `.py` removed after the build made it stale. But a folder's mtime
# also moves when the Finder drops a `.DS_Store` in it or Python creates a `__pycache__`, and no filter on mtimes can
# tell those from a removed file: each cost a rebuild of minutes. So a successful build records the inputs' listing — a
# fingerprint of their paths relative to the project root, taken before the API sync — in
# `frontend/build/.tool-contract-inputs`, and the probe reads it:
#   - an input newer than the build makes it stale, as before;
#   - with a listing recorded, the build is stale exactly when the listing changed: a `.py` added, removed, renamed or
#     moved in with an old mtime, a new plugin folder, whatever the mtimes say. A `.DS_Store`, a `__pycache__`, a
#     hidden `.py` (`.c.py`, Emacs' lock `.#c.py`, one inside a hidden folder) are not inputs and change nothing;
#   - without one (a build made before the cure, a record that failed, an empty marker) the folders' mtimes decide, as
#     before: a `.DS_Store` then still costs one rebuild, and that build records the listing.
#
# "After the build" is NEWER_MTIME, given with `os.utime` to the new file and to every folder its creation moved;
# "arrived with an old mtime" (moved in, renamed, a folder reset after a removal) is OLDER_MTIME, so that only the
# listing can tell. The clock is never read. The names the cure adds to `cli_base` are looked up when a test runs: until
# they exist, the tests that need them fail on "H-24r: cli_base.<name> is missing", never at collection.

#: The Tool codegen inputs ``make_tool_contract_project`` writes, by key, relative to the project root: a ``.py`` in each
#: of the three folders (the plugin's in its own subfolder) and one of the fixed files.
TOOL_CONTRACT_INPUTS = {
    "schemas/a.py": "backend/app/schemas/a.py",
    "services/tools/b.py": "backend/app/services/tools/b.py",
    "tool_plugins/demo/c.py": "backend/app/services/tool_plugins/demo/c.py",
    "generate-tools-client.mjs": "frontend/scripts/generate-tools-client.mjs",
}

#: The folders of that tree a ``.py`` input can live in, by key: the three the probe watches and the plugin's subfolder.
TOOL_CONTRACT_FOLDERS = {
    "schemas": "backend/app/schemas",
    "services/tools": "backend/app/services/tools",
    "tool_plugins": "backend/app/services/tool_plugins",
    "tool_plugins/demo": "backend/app/services/tool_plugins/demo",
}

#: Files beside the inputs that are not inputs, by their path relative to the folder they appear in, each with what it is.
NOT_TOOL_CONTRACT_INPUTS = {
    ".DS_Store": "the Finder's folder metadata",
    "__pycache__/c.cpython-313.pyc": "Python's bytecode cache",
    ".c.py": "a hidden .py",
    ".#c.py": "Emacs' lock file, here a regular file",
    ".cache/c.py": "a .py inside a hidden folder",
    "static/icon.png": "a plugin's asset, not Python",
}


def tool_contract_name(name: str):
    """``cli_base.<name>``, looked up when the test runs: a name the cure has not added yet fails the test, not its collection."""
    if not hasattr(cli_base, name):
        pytest.fail(f"H-24r: cli_base.{name} is missing")
    return getattr(cli_base, name)


def set_mtime(mtime: float, *paths: Path) -> None:
    """Give each of ``paths`` ``mtime`` as its access and modification time."""
    for path in paths:
        os.utime(path, (mtime, mtime))


def add_tool_file(folder: Path, relative: str, mtime: float) -> Path:
    """Write the file ``folder/<relative>``, then give ``mtime`` to it and to every folder its creation moved, ``folder`` included."""
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"synthetic\n")
    set_mtime(mtime, path, *(parent for parent in path.parents if parent.is_relative_to(folder)))
    return path


def remove_tool_file(path: Path, folder_mtime: float) -> None:
    """Remove ``path``, then give its folder, whose mtime the removal moved, ``folder_mtime``."""
    path.unlink()
    set_mtime(folder_mtime, path.parent)


def rename_tool_file(path: Path, name: str) -> Path:
    """Rename ``path`` to ``name`` in its folder: the file keeps its mtime, the folder's is reset an hour before the build."""
    renamed = path.with_name(name)
    os.rename(path, renamed)
    set_mtime(OLDER_MTIME, path.parent)
    return renamed


#: Changes to the inputs' listing that no mtime shows: every file and folder involved ends an hour older than the build.
LISTING_CHANGES = {
    "an-input-added": lambda project: add_tool_file(project.folders["services/tools"], "added.py", OLDER_MTIME),
    "an-input-removed": lambda project: remove_tool_file(project.inputs["schemas/a.py"], OLDER_MTIME),
    "an-input-renamed": lambda project: rename_tool_file(project.inputs["tool_plugins/demo/c.py"], "d.py"),
}


def make_tool_contract_project(monkeypatch, root: Path) -> SimpleNamespace:
    """``make_frontend_project`` plus the Tool codegen inputs ``TOOL_CONTRACT_INPUTS``, all an hour older than the build.

    So are the folders of ``TOOL_CONTRACT_FOLDERS``: writing the files moved their mtimes to now, so they are set last.
    That the probe lists every input written here is verified, not assumed. Returns the project's ``root``, and its
    ``inputs`` and ``folders`` by key.
    """
    make_frontend_project(monkeypatch, root)
    inputs = {key: root / relative for key, relative in TOOL_CONTRACT_INPUTS.items()}
    folders = {key: root / relative for key, relative in TOOL_CONTRACT_FOLDERS.items()}
    for path in inputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# synthetic Tool codegen input\n", encoding="utf-8")
    set_mtime(OLDER_MTIME, *inputs.values(), *folders.values())
    assert set(inputs.values()) <= set(cli_base._tool_contract_sources(root)), "premise: the probe lists every Tool codegen input written here"
    return SimpleNamespace(root=root, inputs=inputs, folders=folders)


@pytest.fixture
def tool_contract_project(monkeypatch, tmp_path) -> SimpleNamespace:
    """``make_tool_contract_project`` with ``tmp_path`` itself as the project root."""
    return make_tool_contract_project(monkeypatch, tmp_path)


def record_tool_contract_listing(root: Path) -> None:
    """Record the inputs' listing under ``root`` as a successful build does, through the cure's own two functions.

    ``frontend/build/`` exists, so the record lands, and with nothing changed yet the build is up to date: both are
    verified. The marker's exact content is pinned once, in ``TestToolContractListing``.
    """
    fingerprint = tool_contract_name("tool_contract_fingerprint")(root)
    tool_contract_name("record_tool_contract_inputs")(root, fingerprint)
    marker = root / tool_contract_name("TOOL_CONTRACT_INPUTS_MARKER")
    assert marker.is_file() and marker.read_text(encoding="utf-8").strip(), f"premise: the listing was recorded in {marker}"
    assert cli_base.check_frontend_needs_build() is False, "premise: right after the record, with nothing changed, the build is up to date"


def write_tool_contract_marker(root: Path, content: str) -> None:
    """Overwrite the recorded listing with ``content``: a listing another build recorded, or an empty one."""
    (root / tool_contract_name("TOOL_CONTRACT_INPUTS_MARKER")).write_text(content, encoding="utf-8")


def assert_no_listing_recorded(root: Path) -> None:
    """The old rule's premise, verified without the cure's names: the build folder holds its ``index.html`` alone."""
    assert sorted(path.name for path in (root / "frontend" / "build").iterdir()) == ["index.html"], "premise: no listing is recorded"


class TestToolContractListing:
    """What a build records: the Tool codegen inputs, the fingerprint of their listing, and the marker it goes to."""

    @pytest.mark.parametrize("checkout", ["checkout", ".hidden-checkout"], ids=["a-plain-folder", "a-hidden-folder"])
    def test_the_inputs_are_the_files_that_exist_never_a_folder_nor_a_file_that_is_not_one(self, monkeypatch, tmp_path, checkout):
        # The fixed files the tree holds (the generator alone: dev.py and the others are absent, so left out, not listed
        # missing) and the `.py` files of the three folders, nothing hidden and no `__pycache__` below the folder; a
        # hidden folder above it, here the checkout's own, hides nothing.
        project = make_tool_contract_project(monkeypatch, tmp_path / checkout)
        for relative in NOT_TOOL_CONTRACT_INPUTS:
            add_tool_file(project.folders["tool_plugins/demo"], relative, OLDER_MTIME)

        listed = sorted(path.relative_to(project.root).as_posix() for path in cli_base._tool_contract_sources(project.root))

        assert listed == sorted(TOOL_CONTRACT_INPUTS.values()), "H-24r: the Tool codegen inputs are the files that exist, without a folder or a file that is not an input"

    def test_without_a_record_the_folders_watched_are_the_three_and_their_subfolders_but_pycache(self, tool_contract_project):
        folders_of = tool_contract_name("_tool_contract_folders")
        root = tool_contract_project.root
        for folder in tool_contract_project.folders.values():
            add_tool_file(folder, "__pycache__/c.cpython-313.pyc", OLDER_MTIME)

        watched = sorted(path.relative_to(root).as_posix() for path in folders_of(root))

        assert watched == sorted(TOOL_CONTRACT_FOLDERS.values())

    def test_the_same_inputs_give_the_same_fingerprint(self, tool_contract_project):
        fingerprint = tool_contract_name("tool_contract_fingerprint")

        assert fingerprint(tool_contract_project.root) == fingerprint(tool_contract_project.root)

    def test_the_fingerprint_reads_the_inputs_relative_to_the_project_root(self, monkeypatch, tmp_path):
        # The same inputs in two checkouts: one listing, so one fingerprint, wherever the checkout lives.
        fingerprint = tool_contract_name("tool_contract_fingerprint")
        first = make_tool_contract_project(monkeypatch, tmp_path / "first")
        second = make_tool_contract_project(monkeypatch, tmp_path / "second")

        assert fingerprint(first.root) == fingerprint(second.root)

    def test_touching_the_inputs_keeps_the_fingerprint(self, tool_contract_project):
        # Names, no mtimes: an input newer than the build is the mtime check's business, not the listing's.
        fingerprint = tool_contract_name("tool_contract_fingerprint")
        before = fingerprint(tool_contract_project.root)

        set_mtime(NEWER_MTIME, *tool_contract_project.inputs.values())

        assert fingerprint(tool_contract_project.root) == before

    @pytest.mark.parametrize("change", list(LISTING_CHANGES))
    def test_an_input_added_removed_or_renamed_changes_the_fingerprint(self, tool_contract_project, change):
        fingerprint = tool_contract_name("tool_contract_fingerprint")
        before = fingerprint(tool_contract_project.root)

        LISTING_CHANGES[change](tool_contract_project)

        assert fingerprint(tool_contract_project.root) != before

    @pytest.mark.parametrize("relative", list(NOT_TOOL_CONTRACT_INPUTS))
    def test_a_file_that_is_not_an_input_keeps_the_fingerprint(self, tool_contract_project, relative):
        fingerprint = tool_contract_name("tool_contract_fingerprint")
        before = fingerprint(tool_contract_project.root)

        add_tool_file(tool_contract_project.folders["tool_plugins/demo"], relative, NEWER_MTIME)

        assert fingerprint(tool_contract_project.root) == before, f"H-24r: tool_plugins/demo/{relative} ({NOT_TOOL_CONTRACT_INPUTS[relative]}) is not a Tool codegen input"

    def test_the_fingerprint_is_a_sha256_hex_digest_that_names_no_input(self, tool_contract_project):
        value = tool_contract_name("tool_contract_fingerprint")(tool_contract_project.root)

        assert isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), f"not a lowercase sha256 hex digest: {value!r}"
        names = sorted({part for relative in TOOL_CONTRACT_INPUTS.values() for part in Path(relative).parts})
        assert [name for name in names if name in value] == [], "the fingerprint carries the listing itself, not its digest"

    def test_the_marker_is_a_hidden_file_of_the_build(self):
        # Every build empties frontend/build/, so a listing there never outlives the build it describes; and a hidden
        # file of the build is never served (H-28).
        marker = tool_contract_name("TOOL_CONTRACT_INPUTS_MARKER")

        assert Path(marker) == Path("frontend") / "build" / ".tool-contract-inputs"

    def test_record_writes_exactly_the_fingerprint_into_the_marker(self, tool_contract_project):
        fingerprint, record = tool_contract_name("tool_contract_fingerprint"), tool_contract_name("record_tool_contract_inputs")
        marker = tool_contract_project.root / tool_contract_name("TOOL_CONTRACT_INPUTS_MARKER")
        value = fingerprint(tool_contract_project.root)

        record(tool_contract_project.root, value)

        assert marker.read_text(encoding="utf-8") == value

    def test_record_without_a_build_folder_raises_nothing_and_writes_nothing(self, tool_contract_project):
        # Bookkeeping, like the build-mode marker: a record that fails costs one rebuild later (the old rule decides),
        # never the build that made it.
        fingerprint, record = tool_contract_name("tool_contract_fingerprint"), tool_contract_name("record_tool_contract_inputs")
        root = tool_contract_project.root
        shutil.rmtree(root / "frontend" / "build")
        value = fingerprint(root)
        before = tree_snapshot(root)

        record(root, value)

        assert tree_snapshot(root) == before


class TestToolContractInputsRecorded:
    """``check_frontend_needs_build()`` once a build recorded the listing: the listing decides, never a folder's mtime."""

    def test_nothing_changed_since_the_recorded_build_leaves_it_up_to_date(self, tool_contract_project):
        record_tool_contract_listing(tool_contract_project.root)

        assert cli_base.check_frontend_needs_build() is False

    @pytest.mark.parametrize("folder", list(TOOL_CONTRACT_FOLDERS))
    def test_a_ds_store_the_finder_drops_after_the_build_leaves_it_up_to_date(self, tool_contract_project, folder):
        record_tool_contract_listing(tool_contract_project.root)

        add_tool_file(tool_contract_project.folders[folder], ".DS_Store", NEWER_MTIME)

        assert cli_base.check_frontend_needs_build() is False, f"H-24r: a .DS_Store moved the mtime of {folder} past the build, but no input changed"

    @pytest.mark.parametrize("folder", list(TOOL_CONTRACT_FOLDERS))
    def test_a_pycache_python_creates_after_the_build_leaves_it_up_to_date(self, tool_contract_project, folder):
        record_tool_contract_listing(tool_contract_project.root)

        add_tool_file(tool_contract_project.folders[folder], "__pycache__/c.cpython-313.pyc", NEWER_MTIME)

        assert cli_base.check_frontend_needs_build() is False, f"H-24r: a __pycache__ moved the mtime of {folder} past the build, but no input changed"

    @pytest.mark.parametrize("relative", [".c.py", ".#c.py", ".cache/c.py"], ids=["a-hidden-py", "an-emacs-lock", "a-py-in-a-hidden-folder"])
    def test_a_hidden_py_written_after_the_build_leaves_it_up_to_date(self, tool_contract_project, relative):
        record_tool_contract_listing(tool_contract_project.root)

        add_tool_file(tool_contract_project.folders["tool_plugins/demo"], relative, NEWER_MTIME)

        assert cli_base.check_frontend_needs_build() is False, f"H-24r: tool_plugins/demo/{relative} ({NOT_TOOL_CONTRACT_INPUTS[relative]}) is not a Tool codegen input"

    @pytest.mark.parametrize("noise", [".DS_Store", "__pycache__/c.cpython-313.pyc", ".c.py"], ids=["a-ds-store", "a-pycache", "a-hidden-py"])
    def test_a_real_change_beside_the_noise_still_needs_a_rebuild(self, tool_contract_project, noise):
        # The probe turns any exception into "up to date", so the cases above would pass as well if the noise made it
        # raise. Here the noise stays, and an input goes that only the listing can see.
        record_tool_contract_listing(tool_contract_project.root)
        add_tool_file(tool_contract_project.folders["tool_plugins/demo"], noise, NEWER_MTIME)

        remove_tool_file(tool_contract_project.inputs["services/tools/b.py"], OLDER_MTIME)

        assert cli_base.check_frontend_needs_build() is True

    @pytest.mark.parametrize("removed", list(TOOL_CONTRACT_INPUTS))
    def test_an_input_removed_needs_a_rebuild_though_no_mtime_moved(self, tool_contract_project, removed):
        record_tool_contract_listing(tool_contract_project.root)

        remove_tool_file(tool_contract_project.inputs[removed], OLDER_MTIME)

        assert cli_base.check_frontend_needs_build() is True, f"H-24r: {TOOL_CONTRACT_INPUTS[removed]} is gone: the codecs the build generated from it are stale"

    def test_an_input_renamed_with_its_old_mtime_needs_a_rebuild(self, tool_contract_project):
        record_tool_contract_listing(tool_contract_project.root)

        rename_tool_file(tool_contract_project.inputs["tool_plugins/demo/c.py"], "d.py")

        assert cli_base.check_frontend_needs_build() is True

    @pytest.mark.parametrize("folder", list(TOOL_CONTRACT_FOLDERS))
    def test_a_py_moved_in_with_an_old_mtime_needs_a_rebuild(self, tool_contract_project, folder):
        record_tool_contract_listing(tool_contract_project.root)

        add_tool_file(tool_contract_project.folders[folder], "moved_in.py", OLDER_MTIME)

        assert cli_base.check_frontend_needs_build() is True, f"H-24r: a .py arrived in {folder} with an old mtime: only the listing can tell"

    def test_a_new_plugin_folder_with_old_mtimes_needs_a_rebuild(self, tool_contract_project):
        record_tool_contract_listing(tool_contract_project.root)

        add_tool_file(tool_contract_project.folders["tool_plugins"], "new_plugin/plugin.py", OLDER_MTIME)

        assert cli_base.check_frontend_needs_build() is True

    @pytest.mark.parametrize("newer", list(TOOL_CONTRACT_INPUTS))
    def test_an_input_newer_than_the_build_needs_a_rebuild(self, tool_contract_project, newer):
        record_tool_contract_listing(tool_contract_project.root)

        set_mtime(NEWER_MTIME, tool_contract_project.inputs[newer])

        assert cli_base.check_frontend_needs_build() is True

    def test_a_listing_recorded_by_another_build_needs_a_rebuild(self, tool_contract_project):
        record_tool_contract_listing(tool_contract_project.root)

        write_tool_contract_marker(tool_contract_project.root, "0" * 64)

        assert cli_base.check_frontend_needs_build() is True

    @pytest.mark.parametrize(("ds_store", "expected"), [(False, False), (True, True)], ids=["nothing-changed", "a-ds-store-after-the-build"])
    def test_an_empty_marker_is_no_record_and_the_folders_decide(self, tool_contract_project, ds_store, expected):
        # Not a listing that differs, which would make every build stale, nor one that matches, which would hide a
        # removed .py: no record at all, and the old rule.
        record_tool_contract_listing(tool_contract_project.root)
        write_tool_contract_marker(tool_contract_project.root, "")
        if ds_store:
            add_tool_file(tool_contract_project.folders["tool_plugins/demo"], ".DS_Store", NEWER_MTIME)

        assert cli_base.check_frontend_needs_build() is expected

    def test_a_hidden_folder_above_the_checkout_hides_no_input(self, monkeypatch, tmp_path):
        project = make_tool_contract_project(monkeypatch, tmp_path / ".hidden-checkout")
        record_tool_contract_listing(project.root)

        remove_tool_file(project.inputs["schemas/a.py"], OLDER_MTIME)

        assert cli_base.check_frontend_needs_build() is True, "H-24r: an input is read relative to its folder: a hidden folder above the checkout must not hide it"


class TestToolContractInputsWithoutARecord:
    """No listing recorded, as after a build made before the cure: the folders' mtimes decide, the rule the record replaces.

    Green before the cure and after it: these need none of its names, and keep its fallback what the probe did until now.
    """

    def test_nothing_changed_leaves_it_up_to_date(self, tool_contract_project):
        assert_no_listing_recorded(tool_contract_project.root)

        assert cli_base.check_frontend_needs_build() is False

    @pytest.mark.parametrize("folder", list(TOOL_CONTRACT_FOLDERS))
    def test_a_ds_store_after_the_build_still_needs_a_rebuild(self, tool_contract_project, folder):
        # The price the record removes: without one, a folder's mtime cannot tell a .DS_Store from a removed .py.
        assert_no_listing_recorded(tool_contract_project.root)
        assert cli_base.check_frontend_needs_build() is False, "premise: up to date before the change"

        add_tool_file(tool_contract_project.folders[folder], ".DS_Store", NEWER_MTIME)

        assert cli_base.check_frontend_needs_build() is True

    def test_an_input_removed_after_the_build_needs_a_rebuild(self, tool_contract_project):
        assert_no_listing_recorded(tool_contract_project.root)
        assert cli_base.check_frontend_needs_build() is False, "premise: up to date before the change"

        remove_tool_file(tool_contract_project.inputs["tool_plugins/demo/c.py"], NEWER_MTIME)

        assert cli_base.check_frontend_needs_build() is True

    def test_an_input_newer_than_the_build_still_needs_a_rebuild(self, tool_contract_project):
        assert_no_listing_recorded(tool_contract_project.root)
        assert cli_base.check_frontend_needs_build() is False, "premise: up to date before the change"

        set_mtime(NEWER_MTIME, tool_contract_project.inputs["tool_plugins/demo/c.py"])

        assert cli_base.check_frontend_needs_build() is True


# ── Test lane settings — what a lane may set: --lane-setting (H-43) ────────
#
# A test lane runs on the instance's defaults (Contract 2b): configure_test_runtime drops every LibreFolio setting of the
# developer's dotenv file and shell, LIBREFOLIO_PROFILE included, in the runner and again in `dev.py server --test`, the
# shared backend. So no lane could run as a managed instance, and no E2E saw the headers the managed profile turns on.
# H-43 lets a lane ask for those settings, and for nothing else:
#   - `--lane-setting NAME=VALUE`, repeatable, on both test entry points and on `dev.py server --test` (an error without
#     `--test`), for the names of TEST_LANE_SETTABLE alone: the profile, the frame protection, the report-only CSP;
#   - configure_test_runtime(..., lane_settings=[...]) writes them to LIBREFOLIO_TEST_LANE_SETTINGS, NAME=VALUE sorted by
#     name and joined by ';' (none given removes it), which every process of the lane inherits through the kept
#     LIBREFOLIO_TEST_ prefix; given no list, it reads the inherited variable. Either way it sets each pair after the
#     drop, so that a nested call, the shared server's, sets them again;
#   - a bad setting, given or inherited, refuses the whole lane, and a refused lane changes nothing;
#   - a lane setting comes from the command line, never from a dotenv file: the variable found there is refused, or a
#     forgotten line would turn every lane managed, silently — alone, and exported as well, as `pipenv run` exports it:
#     it loads the file into the command it starts (override=True) unless PIPENV_DONT_LOAD_ENV is set, and there the
#     variable looks inherited from a runner. Every child of the runner has the guard and reads no dotenv file, so it
#     sets what its runner handed down whatever the file holds;
#   - the runner prints the lane's settings, and Playwright hands the variable to its own webServer;
#   - `front-utility cloud-smoke`, which refuses any lane but a managed one, runs when asked for by name, never in an `all`.
# Without a lane setting nothing changes: a developer's LIBREFOLIO_PROFILE=managed is dropped, as before.
#
# The dotenv file is a synthetic one in tmp_path, named by PIPENV_DOTENV_LOCATION, holding a probe that proves it was
# read: the repository's .env is never read. `dev.py server` runs in this process through capture_server_child, which
# records the builds and the launch instead of running them. The names the cure adds are looked up when a test runs:
# until they exist, the tests that need them fail on "H-43: …", never at collection.

#: The variable a lane's settings travel in, to every process of the lane: spelled here, pinned to
#: ``cli_base.TEST_LANE_SETTINGS`` by a test below.
LANE_SETTINGS_ENV = "LIBREFOLIO_TEST_LANE_SETTINGS"
#: The only names a lane may set: the managed profile and the two protections it turns on. Pinned to
#: ``cli_base.TEST_LANE_SETTABLE`` by a test below.
LANE_SETTABLE = frozenset({"LIBREFOLIO_PROFILE", "LIBREFOLIO_FRAME_PROTECTION", "LIBREFOLIO_CSP_REPORT_ONLY"})
#: A developer's own managed configuration of those names, in the shell or the dotenv file.
DEVELOPER_MANAGED = {"LIBREFOLIO_PROFILE": "managed", "LIBREFOLIO_FRAME_PROTECTION": "true", "LIBREFOLIO_CSP_REPORT_ONLY": "true"}
#: A developer's configuration of those names with values no lane below asks for, so that a lane's value and a
#: developer's can be told apart.
DEVELOPER_SELFHOSTED = {"LIBREFOLIO_PROFILE": "selfhosted", "LIBREFOLIO_FRAME_PROTECTION": "true", "LIBREFOLIO_CSP_REPORT_ONLY": "true"}
LANE_SETTINGS_PORT = 6175
#: Not a LIBREFOLIO_* name, which a lane drops: hydrated from the dotenv file and left there, proof the file was read.
LANE_SETTINGS_PROBE = "RUNTIME_ISOLATION_LANE_SETTINGS_PROBE"


def lane_values(names) -> dict[str, str]:
    """Those of ``names`` the environment holds, with their values."""
    return {name: os.environ[name] for name in sorted(names) if name in os.environ}


def lane_settings_name(name: str):
    """``cli_base.<name>``, looked up when the test runs: a name the cure has not added yet fails the test, not its collection."""
    value = getattr(cli_base, name, None)
    if value is None:
        pytest.fail(f"H-43: cli_base.{name} is missing")
    return value


def configure_lane(**lane):
    """``cli_base.configure_test_runtime(**lane)``: a ``lane_settings`` it does not take yet fails the test, saying so, instead of a TypeError."""
    if "lane_settings" in lane and "lane_settings" not in inspect.signature(cli_base.configure_test_runtime).parameters:
        pytest.fail("H-43: configure_test_runtime takes no lane_settings: a --lane-setting has nowhere to go, and a lane can set nothing")
    return cli_base.configure_test_runtime(**lane)


def lane_refusal(what: str, **lane) -> ValueError:
    """The ``ValueError`` ``configure_test_runtime(**lane)`` refuses ``what`` with: a lane it configures all the same fails the test."""
    try:
        configure_lane(**lane)
    except ValueError as refusal:
        return refusal
    pytest.fail(f"H-43: configure_test_runtime accepted {what} and configured the lane")


def parse_refusal(items) -> ValueError:
    """The ``ValueError`` ``parse_lane_settings(items)`` refuses them with: items it parses fail the test, saying into what."""
    parse = lane_settings_name("parse_lane_settings")
    try:
        parsed = parse(items)
    except ValueError as refusal:
        return refusal
    pytest.fail(f"H-43: parse_lane_settings accepted {items!r} as {parsed!r}")


def write_instance(lane, *, dotenv: dict[str, str], shell: dict[str, str]) -> None:
    """Write ``dotenv`` and the probe to the lane's synthetic dotenv file, and export ``shell``."""
    lane.dotenv = {LANE_SETTINGS_PROBE: "hydrated-from-dotenv", **dotenv}
    lane.dotenv_file.write_text("".join(f"{name}={value}\n" for name, value in lane.dotenv.items()), encoding="utf-8")
    lane.env.setenv("PIPENV_DOTENV_LOCATION", str(lane.dotenv_file))
    for name, value in shell.items():
        lane.env.setenv(name, value)


@pytest.fixture
def settings_lane(runtime_env, tmp_path) -> SimpleNamespace:
    """The lane the runner configures, in an environment holding no LibreFolio setting, and a dotenv file holding the probe alone.

    Every documented variable, kept name, instance secret and ``LIBREFOLIO_*`` name leaves the environment, the variable
    of the lane settings and the names a lane may set included: what a test finds there, it put there. The dotenv file
    is ``tmp_path/instance.env``, named by ``PIPENV_DOTENV_LOCATION``, until a test rewrites it with ``write_instance``:
    the repository's own ``.env`` is never read. ``runtime_env`` restores the environment afterwards.
    """
    names = env_example_variables() | cli_base.TEST_LANE_KEEPS | set(backend_config.INSTANCE_TRUST_SECRETS) | LANE_SETTABLE | {LANE_SETTINGS_ENV, LANE_SETTINGS_PROBE}
    for name in names | {name for name in os.environ if name.startswith("LIBREFOLIO_")}:
        runtime_env.delenv(name, raising=False)
    lane = SimpleNamespace(port=LANE_SETTINGS_PORT, data_dir=tmp_path / "lane-data", env=runtime_env, dotenv_file=tmp_path / "instance.env", dotenv={})
    write_instance(lane, dotenv={}, shell={})
    return lane


class TestTestLaneSettings:
    """``configure_test_runtime(..., lane_settings=...)``: a lane sets what it is given, after the drop, and nothing else."""

    #: ``--lane-setting`` values a lane is refused for, by what makes them bad: a good one beside a bad one goes with it.
    REFUSED_LANE_SETTINGS = {
        "a-production-data-dir": ["LIBREFOLIO_DATA_DIR=/tmp/elsewhere"],
        "an-instance-secret": ["JWT_SECRET=chosen-by-the-lane"],
        "the-test-mode": ["LIBREFOLIO_TEST_MODE=0"],
        "no-equals-sign": ["LIBREFOLIO_PROFILE"],
        "an-empty-value": ["LIBREFOLIO_PROFILE="],
        "a-semicolon-in-the-value": ["LIBREFOLIO_PROFILE=managed;LIBREFOLIO_DATA_DIR=/tmp/elsewhere"],
        "a-name-given-twice": ["LIBREFOLIO_PROFILE=managed", "LIBREFOLIO_PROFILE=selfhosted"],
        "a-good-one-beside-a-bad-one": ["LIBREFOLIO_PROFILE=managed", "LIBREFOLIO_DATA_DIR=/tmp/elsewhere"],
    }

    @staticmethod
    def instance_a_refusal_must_leave(lane, shell: dict[str, str] | None = None) -> dict[str, str]:
        """Export the developer's settings, which a drop would remove, beside the dotenv probe, which a hydration would add; return the environment."""
        write_instance(lane, dotenv={}, shell={**DEVELOPER_SELFHOSTED, **(shell or {})})
        return dict(os.environ)

    def test_the_names_a_lane_may_set_and_the_variable_they_travel_in(self):
        settable, variable = lane_settings_name("TEST_LANE_SETTABLE"), lane_settings_name("TEST_LANE_SETTINGS")

        assert isinstance(settable, frozenset) and settable == LANE_SETTABLE, f"H-43: a lane may set {sorted(LANE_SETTABLE)} and nothing else, not {settable!r}"
        assert variable == LANE_SETTINGS_ENV
        assert cli_base.kept_in_a_test_lane(variable), f"{variable} must be kept in a lane, by its LIBREFOLIO_TEST_ prefix: every process of the lane reads it"
        assert not any(map(cli_base.kept_in_a_test_lane, settable)), "a name a lane may set is not one it keeps: the developer's own value of it must still be dropped"

    @pytest.mark.parametrize(
        ("lane_settings", "variable", "settings"),
        [
            pytest.param(["LIBREFOLIO_PROFILE=managed"], "LIBREFOLIO_PROFILE=managed", {"LIBREFOLIO_PROFILE": "managed"}, id="the-managed-profile"),
            pytest.param([" \tLIBREFOLIO_PROFILE =  managed "], "LIBREFOLIO_PROFILE=managed", {"LIBREFOLIO_PROFILE": "managed"}, id="name-and-value-stripped"),
            pytest.param(["LIBREFOLIO_PROFILE=managed", "LIBREFOLIO_CSP_REPORT_ONLY=false"], "LIBREFOLIO_CSP_REPORT_ONLY=false;LIBREFOLIO_PROFILE=managed", {"LIBREFOLIO_CSP_REPORT_ONLY": "false", "LIBREFOLIO_PROFILE": "managed"}, id="two-sorted-by-name"),
            pytest.param(
                ["LIBREFOLIO_PROFILE=managed", "LIBREFOLIO_FRAME_PROTECTION=false", "LIBREFOLIO_CSP_REPORT_ONLY=false"],
                "LIBREFOLIO_CSP_REPORT_ONLY=false;LIBREFOLIO_FRAME_PROTECTION=false;LIBREFOLIO_PROFILE=managed",
                {"LIBREFOLIO_CSP_REPORT_ONLY": "false", "LIBREFOLIO_FRAME_PROTECTION": "false", "LIBREFOLIO_PROFILE": "managed"},
                id="the-three",
            ),
        ],
    )
    def test_a_lane_sets_exactly_the_settings_it_is_given(self, settings_lane, lane_settings, variable, settings):
        # The developer configured the three names otherwise: none of those values may reach the lane, set or not
        write_instance(settings_lane, dotenv=DEVELOPER_SELFHOSTED, shell=DEVELOPER_SELFHOSTED)

        configured = configure_lane(port=settings_lane.port, data_dir=settings_lane.data_dir, lane_settings=lane_settings)

        assert configured == (settings_lane.port, settings_lane.data_dir.resolve()), "the lane settings change nothing of what configure_test_runtime returns"
        assert os.environ.get(LANE_SETTINGS_ENV) == variable, f"H-43: the lane's settings travel to its children in {LANE_SETTINGS_ENV}, NAME=VALUE sorted by name and joined by ';'"
        assert lane_values(LANE_SETTABLE) == settings, "H-43: the lane must hold exactly the settings it was given, set after the drop: none of the developer's own"

    def test_a_nested_call_sets_them_again_after_its_drop_and_changes_nothing(self, settings_lane):
        # The runner, given two --lane-setting: what it configures, its children inherit
        configure_lane(port=settings_lane.port, data_dir=settings_lane.data_dir, lane_settings=["LIBREFOLIO_PROFILE=managed", "LIBREFOLIO_CSP_REPORT_ONLY=false"])
        inherited, settings = dict(os.environ), {"LIBREFOLIO_CSP_REPORT_ONLY": "false", "LIBREFOLIO_PROFILE": "managed"}
        assert lane_values(LANE_SETTABLE) == settings, "premise: the runner's lane holds its two settings"

        # The child: `dev.py server --test` of the shared server passes no lane argument and no lane setting, and its drop
        # removes every LIBREFOLIO_* name but the kept ones: the two settings with them
        configured = cli_base.configure_test_runtime()

        changes = environment_changes(inherited)
        assert lane_values(LANE_SETTABLE) == settings, "H-43: the nested call dropped the lane's settings and set nothing back: the shared server would run on the instance's defaults"
        assert configured == (settings_lane.port, settings_lane.data_dir.resolve())
        assert not changes, f"a nested call changed the lane's environment: {changes}"

    @pytest.mark.parametrize(
        ("lane_settings", "variable", "settings"),
        [
            pytest.param([], None, {}, id="none-given"),
            pytest.param(["LIBREFOLIO_CSP_REPORT_ONLY=false"], "LIBREFOLIO_CSP_REPORT_ONLY=false", {"LIBREFOLIO_CSP_REPORT_ONLY": "false"}, id="others-given"),
        ],
    )
    def test_given_lane_settings_replace_the_inherited_ones(self, settings_lane, lane_settings, variable, settings):
        # The environment a runner configured with the managed profile hands to its children
        write_instance(settings_lane, dotenv={}, shell={LANE_SETTINGS_ENV: "LIBREFOLIO_PROFILE=managed", "LIBREFOLIO_PROFILE": "managed"})

        configure_lane(port=settings_lane.port, data_dir=settings_lane.data_dir, lane_settings=lane_settings)

        assert os.environ.get(LANE_SETTINGS_ENV) == variable, f"H-43: lane settings given, even none, replace the inherited ones in {LANE_SETTINGS_ENV}: none given removes it"
        assert lane_values(LANE_SETTABLE) == settings, "H-43: the lane must hold exactly the settings it was given, none of those it inherited"

    @pytest.mark.parametrize("inherited", ["LIBREFOLIO_PROFILE=managed", ";LIBREFOLIO_PROFILE=managed;;"], ids=["from-the-runner", "empty-items-ignored"])
    def test_lane_settings_inherited_from_the_runner_are_set(self, settings_lane, inherited):
        # As the runner hands them to a child: the variable exported, beside the developer's own values of the three names
        write_instance(settings_lane, dotenv={}, shell={**DEVELOPER_SELFHOSTED, LANE_SETTINGS_ENV: inherited})

        configured = cli_base.configure_test_runtime(port=settings_lane.port, data_dir=settings_lane.data_dir)

        assert configured == (settings_lane.port, settings_lane.data_dir.resolve())
        assert LANE_SETTINGS_ENV in os.environ, f"{LANE_SETTINGS_ENV} stays in the lane, for its own children"
        assert lane_values(LANE_SETTABLE) == {"LIBREFOLIO_PROFILE": "managed"}, "H-43: the lane must hold the settings it inherited from its runner, and only those: the drop removed them and nothing set them back"

    def test_a_child_of_the_runner_reads_no_dotenv_file_and_sets_the_inherited_settings(self, settings_lane):
        """A child of the runner reads no dotenv file: what the file holds, the variable included, is neither applied nor refused.

        Every child of the runner holds ``PIPENV_DONT_LOAD_ENV=1``: ``configure_test_runtime`` exports it, and Playwright's
        webServer env sets it as well. The child sets the settings its runner handed down, as the runner set them.
        """
        # The runner's lane as a child inherits it, the guard included, beside the developer's own values of the three
        # names; the dotenv file holds another value of the variable, which must reach neither the lane nor a refusal
        write_instance(settings_lane, dotenv={LANE_SETTINGS_ENV: "LIBREFOLIO_CSP_REPORT_ONLY=false"}, shell={**DEVELOPER_SELFHOSTED, LANE_SETTINGS_ENV: "LIBREFOLIO_PROFILE=managed", "PIPENV_DONT_LOAD_ENV": "1"})

        configured = cli_base.configure_test_runtime(port=settings_lane.port, data_dir=settings_lane.data_dir)

        assert configured == (settings_lane.port, settings_lane.data_dir.resolve())
        assert LANE_SETTINGS_PROBE not in os.environ, "PIPENV_DONT_LOAD_ENV hides the dotenv file from a child of the runner, yet the probe it holds was hydrated: the file was read"
        assert os.environ.get(LANE_SETTINGS_ENV) == "LIBREFOLIO_PROFILE=managed", f"H-43: a child of the runner hands on in {LANE_SETTINGS_ENV} what its runner handed down, never the dotenv file's value"
        assert lane_values(LANE_SETTABLE) == {"LIBREFOLIO_PROFILE": "managed"}, "H-43: a child of the runner must hold the settings its runner handed down, and only those: neither the developer's own nor the dotenv file's"

    @pytest.mark.parametrize("origin", ["shell", "dotenv", "both"])
    def test_without_a_lane_setting_the_developers_managed_profile_is_still_dropped(self, settings_lane, origin):
        """Green before H-43 and after it: a lane's settings come from the lane, never from the developer's configuration."""
        write_instance(settings_lane, dotenv=DEVELOPER_MANAGED if origin != "shell" else {}, shell=DEVELOPER_MANAGED if origin != "dotenv" else {})

        configured = cli_base.configure_test_runtime(port=settings_lane.port, data_dir=settings_lane.data_dir)

        reached = lane_values(LANE_SETTABLE | {LANE_SETTINGS_ENV})
        assert configured == (settings_lane.port, settings_lane.data_dir.resolve())
        assert os.environ.get(LANE_SETTINGS_PROBE) == "hydrated-from-dotenv", "the synthetic dotenv file was not loaded, so the absence below would prove nothing"
        assert not reached, f"the developer's managed configuration reached a lane given no lane setting, from the {origin}: {reached}"

    @pytest.mark.parametrize("lane_settings", list(REFUSED_LANE_SETTINGS.values()), ids=list(REFUSED_LANE_SETTINGS))
    def test_a_bad_lane_setting_refuses_the_lane_and_changes_nothing(self, settings_lane, lane_settings):
        before = self.instance_a_refusal_must_leave(settings_lane)

        lane_refusal(f"--lane-setting {lane_settings!r}", port=settings_lane.port, data_dir=settings_lane.data_dir, lane_settings=lane_settings)

        changes = environment_changes(before)
        assert not changes, f"a lane refused for its settings changed the environment: {changes}"

    @pytest.mark.parametrize(
        "inherited",
        ["LIBREFOLIO_DATA_DIR=/tmp/elsewhere", "LIBREFOLIO_PROFILE", "LIBREFOLIO_PROFILE=managed;LIBREFOLIO_PROFILE=selfhosted", "LIBREFOLIO_PROFILE=managed;JWT_SECRET=chosen-by-the-lane"],
        ids=["a-production-data-dir", "no-equals-sign", "a-name-given-twice", "a-good-one-beside-a-bad-one"],
    )
    def test_a_bad_inherited_lane_setting_refuses_the_lane_and_changes_nothing(self, settings_lane, inherited):
        before = self.instance_a_refusal_must_leave(settings_lane, shell={LANE_SETTINGS_ENV: inherited})

        lane_refusal(f"{LANE_SETTINGS_ENV}={inherited!r} inherited from its runner", port=settings_lane.port, data_dir=settings_lane.data_dir)

        changes = environment_changes(before)
        assert not changes, f"a lane refused for its inherited settings changed the environment: {changes}"

    @pytest.mark.parametrize("lane_settings", [None, ["LIBREFOLIO_PROFILE=managed"]], ids=["no-lane-setting", "a-lane-setting-as-well"])
    def test_lane_settings_from_the_dotenv_file_are_refused(self, settings_lane, lane_settings):
        # A line forgotten in the developer's dotenv file would turn every lane managed, silently
        write_instance(settings_lane, dotenv={LANE_SETTINGS_ENV: "LIBREFOLIO_PROFILE=managed"}, shell=DEVELOPER_SELFHOSTED)
        before = dict(os.environ)
        assert LANE_SETTINGS_ENV not in before, "premise: the variable is in the dotenv file alone"
        lane = {"port": settings_lane.port, "data_dir": settings_lane.data_dir} | ({} if lane_settings is None else {"lane_settings": lane_settings})

        refusal = lane_refusal(f"{LANE_SETTINGS_ENV} from the dotenv file", **lane)

        # The hydration that finds the variable may stay; nothing else may happen: no drop, no export, no setting
        hydration = {name: (None, value) for name, value in settings_lane.dotenv.items()}
        beyond = {name: change for name, change in environment_changes(before).items() if hydration.get(name) != change}
        assert "--lane-setting" in str(refusal) and ".env" in str(refusal), f"the refusal must say that lane settings come from --lane-setting only, never from .env: {refusal}"
        assert not beyond, f"a lane refused for the lane settings of its dotenv file changed more than the hydration that found them: {beyond}"

    @pytest.mark.parametrize("lane_settings", [None, ["LIBREFOLIO_PROFILE=managed"]], ids=["no-lane-setting", "a-lane-setting-as-well"])
    def test_lane_settings_pipenv_loaded_from_the_dotenv_file_are_refused(self, settings_lane, lane_settings):
        """``pipenv run`` loads the dotenv file into the command it starts, ``override=True``, unless ``PIPENV_DONT_LOAD_ENV`` is set.

        So the variable a line of the developer's dotenv file holds reaches ``dev.py`` exported, as if a runner had handed
        it down: refused all the same, first, before any hydration, drop or export — the environment stays as it was.
        """
        # What `pipenv run` exports from the file, beside the developer's own values of the three names, which a drop would
        # remove. The probe stays in the file alone, so that a hydration would show as its arrival
        loaded = {LANE_SETTINGS_ENV: "LIBREFOLIO_PROFILE=managed"}
        write_instance(settings_lane, dotenv=loaded, shell={**DEVELOPER_SELFHOSTED, **loaded})
        before = dict(os.environ)
        assert "PIPENV_DONT_LOAD_ENV" not in before, "premise: no guard, as in a command `pipenv run` starts from the developer's shell"
        lane = {"port": settings_lane.port, "data_dir": settings_lane.data_dir} | ({} if lane_settings is None else {"lane_settings": lane_settings})

        refusal = lane_refusal(f"{LANE_SETTINGS_ENV} that pipenv loaded from the dotenv file", **lane)

        changes = environment_changes(before)
        assert "--lane-setting" in str(refusal) and ".env" in str(refusal), f"the refusal must say that lane settings come from --lane-setting only, never from .env: {refusal}"
        assert not changes, f"a lane refused for the lane settings pipenv loaded from its dotenv file changed the environment: {changes}"


class TestParseLaneSettings:
    """``cli_base.parse_lane_settings``: ``NAME=VALUE`` items, name and value stripped, for the names of ``TEST_LANE_SETTABLE`` alone."""

    #: Items refused one by one, by what makes them bad.
    REFUSED_ITEMS = {
        "no-equals-sign": "LIBREFOLIO_PROFILE",
        "an-empty-name": "=managed",
        "a-blank-name": "   =managed",
        "an-empty-value": "LIBREFOLIO_PROFILE=",
        "a-blank-value": "LIBREFOLIO_PROFILE=   ",
        "a-production-data-dir": "LIBREFOLIO_DATA_DIR=/tmp/elsewhere",
        "an-instance-secret": "JWT_SECRET=chosen-by-the-lane",
        "a-port": "TEST_PORT=6041",
        "the-test-mode": "LIBREFOLIO_TEST_MODE=0",
        "the-variable-of-the-lane-settings": "LIBREFOLIO_TEST_LANE_SETTINGS=LIBREFOLIO_PROFILE=managed",
        "a-name-in-lower-case": "librefolio_profile=managed",
        "a-semicolon-in-the-value": "LIBREFOLIO_PROFILE=managed;LIBREFOLIO_DATA_DIR=/tmp/elsewhere",
        "a-newline-in-the-value": "LIBREFOLIO_PROFILE=managed\nLIBREFOLIO_DATA_DIR=/tmp/elsewhere",
        "a-carriage-return-in-the-value": "LIBREFOLIO_PROFILE=man\raged",
        "a-nul-in-the-value": "LIBREFOLIO_PROFILE=man\0aged",
    }

    @pytest.mark.parametrize(
        ("items", "expected"),
        [
            pytest.param(["LIBREFOLIO_PROFILE=managed"], {"LIBREFOLIO_PROFILE": "managed"}, id="one"),
            pytest.param([" \tLIBREFOLIO_PROFILE =  managed "], {"LIBREFOLIO_PROFILE": "managed"}, id="name-and-value-stripped"),
            pytest.param(
                ("LIBREFOLIO_PROFILE=managed", "LIBREFOLIO_FRAME_PROTECTION=true", "LIBREFOLIO_CSP_REPORT_ONLY=false"),
                {"LIBREFOLIO_PROFILE": "managed", "LIBREFOLIO_FRAME_PROTECTION": "true", "LIBREFOLIO_CSP_REPORT_ONLY": "false"},
                id="the-three-from-a-tuple",
            ),
            pytest.param([], {}, id="none"),
        ],
    )
    def test_reads_name_value_items(self, items, expected):
        assert lane_settings_name("parse_lane_settings")(items) == expected

    @pytest.mark.parametrize("item", list(REFUSED_ITEMS.values()), ids=list(REFUSED_ITEMS))
    def test_refuses_a_bad_item(self, item):
        parse_refusal([item])

    @pytest.mark.parametrize("items", [["LIBREFOLIO_PROFILE=managed", "LIBREFOLIO_PROFILE=selfhosted"], ["LIBREFOLIO_PROFILE=managed", " LIBREFOLIO_PROFILE = managed"]], ids=["two-values", "the-same-one-once-stripped"])
    def test_refuses_a_name_given_twice(self, items):
        parse_refusal(items)

    def test_a_name_it_refuses_is_named_beside_the_allowed_ones(self):
        message = str(parse_refusal(["LIBREFOLIO_DATA_DIR=/tmp/elsewhere"]))

        missing = sorted(name for name in LANE_SETTABLE if name not in message)
        assert "LIBREFOLIO_DATA_DIR" in message, f"the refusal must name the item it refuses: {message!r}"
        assert not missing, f"the refusal must list the names a lane may set: {missing} missing from {message!r}"


#: Two lane settings on the command line, in the order they were typed.
LANE_SETTING_ARGV = ["--lane-setting", "LIBREFOLIO_PROFILE=managed", "--lane-setting", "LIBREFOLIO_CSP_REPORT_ONLY=false"]


def runtime_args_parser() -> argparse.ArgumentParser:
    """A fresh parser holding the lane options alone, as ``_add_runtime_args`` adds them to both test entry points."""
    parser = argparse.ArgumentParser(prog="lane")
    test_runner_cli._add_runtime_args(parser)
    return parser


def run_dev_server(lane, *flags: str) -> tuple[int, dict]:
    """``./dev.py server <flags>`` through the real parser: its exit code, and what it built and launched, recorded, never run."""
    captured = capture_server_child(lane.env)
    lane.env.setattr(sys, "argv", ["dev.py", "server", *flags])
    try:
        exit_code = dev.main()
    except SystemExit as exited:  # argparse refusing an option it does not know
        exit_code = exited.code
    return exit_code, captured


def argparse_note(exit_code) -> str:
    """What exit code 2 of ``dev.main()`` means in the messages below."""
    return " — exit 2 is argparse refusing an option, as when `dev.py server` has no --lane-setting" if exit_code == 2 else ""


class TestLaneSettingsOnTheCommandLine:
    """``--lane-setting``: on both test entry points, applied and printed by the runner, and on ``dev.py server --test`` alone."""

    @staticmethod
    def lane_args(lane, lane_settings) -> SimpleNamespace:
        """The arguments of the runner's lane, as both parsers produce them."""
        return SimpleNamespace(test_port=lane.port, data_dir=str(lane.data_dir), lane_settings=lane_settings)

    @staticmethod
    def printed_lane_settings(output: str) -> list[str]:
        """Each line of ``output`` that reports the lane settings, from ``Test lane settings:`` on, without its colours."""
        lines = (re.sub(r"\x1b\[[0-9;]*m", "", line).rstrip() for line in output.splitlines())
        return [line[line.index("Test lane settings:") :] for line in lines if "Test lane settings:" in line]

    @pytest.mark.parametrize(
        ("parser_factory", "before", "after"),
        [
            pytest.param(runtime_args_parser, [], [], id="runtime-args"),
            pytest.param(build_dev_test_parser, ["test"], ["utils", "runtime-isolation"], id="dev-test"),
            pytest.param(test_runner_cli.create_parser, [], ["utils", "runtime-isolation"], id="runner"),
        ],
    )
    def test_the_option_repeats_and_defaults_to_none(self, parser_factory, before, after):
        parser = parser_factory()
        try:
            given = parser.parse_args([*before, *LANE_SETTING_ARGV, *after])
        except SystemExit as exited:
            pytest.fail(f"H-43: this entry point has no --lane-setting: argparse exited {exited.code} on {LANE_SETTING_ARGV}")
        omitted = parser.parse_args([*before, *after])

        assert given.lane_settings == ["LIBREFOLIO_PROFILE=managed", "LIBREFOLIO_CSP_REPORT_ONLY=false"], "every --lane-setting is kept, in the order given"
        assert getattr(omitted, "lane_settings", "missing") is None, "without --lane-setting, lane_settings is None: the lane inherits its runner's"

    @pytest.mark.parametrize(
        ("lane_settings", "inherited", "value", "settings"),
        [
            pytest.param(["LIBREFOLIO_PROFILE=managed", "LIBREFOLIO_CSP_REPORT_ONLY=false"], None, "LIBREFOLIO_CSP_REPORT_ONLY=false;LIBREFOLIO_PROFILE=managed", {"LIBREFOLIO_CSP_REPORT_ONLY": "false", "LIBREFOLIO_PROFILE": "managed"}, id="given"),
            pytest.param(None, "LIBREFOLIO_PROFILE=managed", "LIBREFOLIO_PROFILE=managed", {"LIBREFOLIO_PROFILE": "managed"}, id="inherited"),
            pytest.param(None, None, None, {}, id="none"),
        ],
    )
    def test_the_runner_applies_and_prints_the_lane_settings(self, settings_lane, capsys, lane_settings, inherited, value, settings):
        write_instance(settings_lane, dotenv={}, shell={} if inherited is None else {LANE_SETTINGS_ENV: inherited})

        configured = test_runner_cli._configure_runtime(self.lane_args(settings_lane, lane_settings))

        printed, expected = self.printed_lane_settings(capsys.readouterr().out), [] if value is None else [f"Test lane settings: {value}"]
        assert configured is True
        assert printed == expected, f"H-43: the runner must print the lane's settings in one info line, {expected or 'none without any'}: it printed {printed or 'none'}"
        assert lane_values(LANE_SETTABLE) == settings, "H-43: _configure_runtime must hand --lane-setting to configure_test_runtime"

    @pytest.mark.parametrize(
        ("lane_settings", "dotenv", "shell", "named"),
        [
            pytest.param(["LIBREFOLIO_DATA_DIR=/tmp/elsewhere"], {}, {}, "LIBREFOLIO_DATA_DIR", id="a-name-outside-the-list"),
            pytest.param(None, {LANE_SETTINGS_ENV: "LIBREFOLIO_PROFILE=managed"}, {}, "--lane-setting", id="the-variable-in-the-dotenv-file"),
            # `pipenv run` exports what the file holds, unless PIPENV_DONT_LOAD_ENV is set: the variable looks inherited
            pytest.param(None, {LANE_SETTINGS_ENV: "LIBREFOLIO_PROFILE=managed"}, {LANE_SETTINGS_ENV: "LIBREFOLIO_PROFILE=managed"}, "--lane-setting", id="the-variable-pipenv-loaded-from-the-dotenv-file"),
        ],
    )
    def test_the_runner_refuses_a_bad_lane_setting_with_its_error(self, settings_lane, capsys, lane_settings, dotenv, shell, named):
        write_instance(settings_lane, dotenv=dotenv, shell=shell)

        configured = test_runner_cli._configure_runtime(self.lane_args(settings_lane, lane_settings))

        output = capsys.readouterr().out
        assert configured is False, f"H-43: the runner goes on with a bad lane setting ({lane_settings or dotenv}{', exported as well' if shell else ''}): _configure_runtime returned {configured}"
        assert named in output, f"the runner must print the refusal, naming {named!r}: {output!r}"
        assert (self.printed_lane_settings(output), lane_values(LANE_SETTABLE)) == ([], {}), "a refused lane prints no lane setting and sets none"

    def test_dev_server_refuses_a_lane_setting_without_test(self, settings_lane, capsys):
        flags = ["--lane-setting", "LIBREFOLIO_PROFILE=managed", "--port", str(LANE_SETTINGS_PORT + 1), "--data-dir", str(settings_lane.data_dir.parent / "synthetic-production-data")]

        exit_code, captured = run_dev_server(settings_lane, *flags)

        output = capsys.readouterr()
        assert exit_code == 1, f"H-43: `dev.py server {' '.join(flags)}` without --test exited {exit_code}, not 1 with an error{argparse_note(exit_code)}"
        assert "--lane-setting" in output.out + output.err, f"the error must name --lane-setting: {output!r}"
        assert (captured["events"], "env" in captured) == ([], False), "a server refused for its options builds nothing and starts nothing"
        assert lane_values(LANE_SETTABLE) == {}, "a server refused for its lane settings sets none of them"

    @pytest.mark.parametrize("source", ["command-line", "inherited"], ids=["given-on-the-command-line", "inherited-from-the-runner"])
    def test_dev_server_test_starts_with_the_lane_settings(self, settings_lane, source):
        flags = ["--test", "--port", str(settings_lane.port), "--data-dir", str(settings_lane.data_dir)]
        if source == "command-line":
            flags += ["--lane-setting", "LIBREFOLIO_PROFILE=managed"]
        else:
            # As the runner's shared server and Playwright's webServer start it: the runner's lane exported, no lane argument
            write_instance(settings_lane, dotenv={}, shell={LANE_SETTINGS_ENV: "LIBREFOLIO_PROFILE=managed", "LIBREFOLIO_PROFILE": "managed"})

        exit_code, captured = run_dev_server(settings_lane, *flags)

        child = captured.get("env", {})
        assert exit_code == 0, f"H-43: `dev.py server {' '.join(flags)}` exited {exit_code}{argparse_note(exit_code)}"
        assert (child.get("LIBREFOLIO_PROFILE"), child.get(LANE_SETTINGS_ENV)) == ("managed", "LIBREFOLIO_PROFILE=managed"), "H-43: the server must start with the lane's settings, and hand them on to its own children"


# Playwright's webServer, `./dev.py server --test`, configures a lane of its own: whether its `env` merges into or replaces
# the environment of `playwright test` was left unverified (H-43 analysis), so the config hands the variable over
# explicitly. Checked as text, as the startup timeout is above: no node_modules needed.


def braced_body(code: str, opening: re.Match | None) -> str | None:
    """The text between the brace ``opening`` ends on and the brace that closes it (``None`` without an opening)."""
    if opening is None:
        return None
    depth = 0
    for index in range(opening.end() - 1, len(code)):
        depth += {"{": 1, "}": -1}.get(code[index], 0)
        if depth == 0:
            return code[opening.end() : index]
    return code[opening.end() :]


def playwright_lane_settings_gaps(config_text: str) -> list[str]:
    """Every way ``playwright.config.ts`` fails to hand ``LIBREFOLIO_TEST_LANE_SETTINGS`` to its webServer ([] = none).

    Pure on text, so a control can feed it a config of its own. The webServer's env must be ``WEB_SERVER_ENV``, and that
    object must be given the variable, read from ``process.env``: as a key of its object literal, or by an assignment
    ``WEB_SERVER_ENV.<name> = …`` (or ``['<name>']``), as the config already gives it the coverage variables. Full-line
    comments are not code.
    """
    code = re.sub(r"^[ \t]*//.*$", "", config_text, flags=re.M)
    name = re.escape(LANE_SETTINGS_ENV)
    web_server = braced_body(code, re.search(r"\bwebServer\s*:\s*\{", code)) or ""
    given_env = [match for match in re.finditer(r"\benv\s*:\s*WEB_SERVER_ENV\b", web_server) if web_server.count("{", 0, match.start()) == web_server.count("}", 0, match.start())]
    literal = braced_body(code, re.search(r"\bconst\s+WEB_SERVER_ENV\b[^=]*=\s*\{", code)) or ""
    keyed = re.search(rf"(?<![.\w'\"]){name}\s*(?::|,|$)|['\"]{name}['\"]\s*:", literal)
    assigned = re.search(rf"\bWEB_SERVER_ENV\s*(?:\.\s*{name}\b|\[\s*['\"]{name}['\"]\s*\])\s*=(?!=)", code)
    read = re.search(rf"\bprocess\.env\s*(?:\.\s*{name}\b|\[\s*['\"]{name}['\"]\s*\])", code)
    checks = [
        (bool(given_env), "webServer is not given WEB_SERVER_ENV as its env: nothing that object carries reaches `dev.py server --test`"),
        (bool(keyed or assigned), f"WEB_SERVER_ENV is not given {LANE_SETTINGS_ENV}: neither a key of its object literal nor an assignment WEB_SERVER_ENV.{LANE_SETTINGS_ENV} = …"),
        (bool(read), f"process.env.{LANE_SETTINGS_ENV} is never read: the lane settings the runner exported never reach the webServer"),
    ]
    return [reason for holds, reason in checks if not holds]


def synthetic_playwright_config(*, in_literal: str = "", after_literal: str = "", web_server_env: str = "WEB_SERVER_ENV") -> str:
    """A ``playwright.config.ts`` cut down to what ``playwright_lane_settings_gaps`` reads, its webServer given ``web_server_env``."""
    return (
        "const WEB_SERVER_ENV: Record<string, string> = {\n"
        "    TEST_PORT,\n"
        "    PIPENV_DONT_LOAD_ENV: '1',\n"
        f"{in_literal}"
        "};\n"
        f"{after_literal}"
        "export default defineConfig({\n"
        "    webServer: {\n"
        "        command: `cd .. && exec ./dev.py server --test --workers ${SERVER_WORKERS}`,\n"
        f"        env: {web_server_env},\n"
        "        gracefulShutdown: {signal: 'SIGTERM', timeout: 10000},\n"
        "    },\n"
        "});\n"
    )


#: The handover the contract asks for, the way the config already gives WEB_SERVER_ENV the coverage variables.
ASSIGNED_LANE_SETTINGS = "if (process.env.LIBREFOLIO_TEST_LANE_SETTINGS) {\n    WEB_SERVER_ENV.LIBREFOLIO_TEST_LANE_SETTINGS = process.env.LIBREFOLIO_TEST_LANE_SETTINGS;\n}\n"
#: The shapes of the handover the check accepts, as parts of ``synthetic_playwright_config``.
LANE_SETTINGS_HANDOVERS = {
    "an-assignment": {"after_literal": ASSIGNED_LANE_SETTINGS},
    "a-bracket-assignment": {"after_literal": "const laneSettings = process.env['LIBREFOLIO_TEST_LANE_SETTINGS'];\nif (laneSettings) WEB_SERVER_ENV['LIBREFOLIO_TEST_LANE_SETTINGS'] = laneSettings;\n"},
    "a-key-of-the-literal": {"in_literal": "    ...(process.env.LIBREFOLIO_TEST_LANE_SETTINGS ? {LIBREFOLIO_TEST_LANE_SETTINGS: process.env.LIBREFOLIO_TEST_LANE_SETTINGS} : {}),\n"},
}
#: Configs the check rejects, each with the reason it must give.
LANE_SETTINGS_NON_HANDOVERS = {
    "only-in-a-comment": ({"after_literal": "// WEB_SERVER_ENV.LIBREFOLIO_TEST_LANE_SETTINGS = process.env.LIBREFOLIO_TEST_LANE_SETTINGS;\n"}, "WEB_SERVER_ENV is not given"),
    "read-and-kept": ({"after_literal": "const laneSettings = process.env.LIBREFOLIO_TEST_LANE_SETTINGS;\n"}, "WEB_SERVER_ENV is not given"),
    "given-to-another-object": ({"after_literal": ASSIGNED_LANE_SETTINGS, "web_server_env": "{TEST_PORT}"}, "webServer is not given WEB_SERVER_ENV"),
}


def test_playwright_hands_the_lane_settings_to_its_web_server():
    gaps = playwright_lane_settings_gaps(PLAYWRIGHT_CONFIG.read_text(encoding="utf-8"))

    assert gaps == [], f"H-43: playwright.config.ts does not hand {LANE_SETTINGS_ENV} to its webServer, `dev.py server --test`: {gaps}"


@pytest.mark.parametrize("parts", list(LANE_SETTINGS_HANDOVERS.values()), ids=list(LANE_SETTINGS_HANDOVERS))
def test_the_lane_settings_check_accepts_a_handover(parts):
    # The control of the check above, green before H-43 and after it: each shape the cure may take passes it.
    assert playwright_lane_settings_gaps(synthetic_playwright_config(**parts)) == []


@pytest.mark.parametrize(("parts", "reason"), list(LANE_SETTINGS_NON_HANDOVERS.values()), ids=list(LANE_SETTINGS_NON_HANDOVERS))
def test_the_lane_settings_check_rejects_a_config_without_one(parts, reason):
    # The other control: a config that only seems to hand the variable over is rejected, for the reason that applies.
    gaps = playwright_lane_settings_gaps(synthetic_playwright_config(**parts))

    assert any(reason in gap for gap in gaps), f"{reason!r} not reported, gaps={gaps}"


# The cloud smoke runs on a managed lane and refuses any other: `front_cloud_smoke` returns False, printing why, unless
# LIBREFOLIO_PROFILE is `managed`, and a lane is self-hosted unless it is started with --lane-setting
# LIBREFOLIO_PROFILE=managed. Run by an `all` — `front-utility all`, `all-frontend`, `all` — it would turn the category
# red on the default lane: it runs when asked for by name only. The collector's own spec runs on any lane, and stays in
# every `all`. `in_all=False` is not enough: the serial `all` reads it, but the consolidated pre-pass that runs first
# (`_consolidate.group_frontend_units`) groups whatever the dry run of `_inventory.collect_launches` reports, whatever
# `in_all` says — the AI Export and Designer Lab per-spec actions rely on it — and on a managed lane the cloud smoke
# passes its check in that dry run: `front-utility all` would run it, `all-frontend` seven specs of other categories
# twice. So it is registered `named_only`, which both passes read. Read from the registry, as they read it (`in_all`,
# True when not given; `named_only`, False when not given); `utils test-runner-cli` pins what `add_test` stores and
# what the consolidated pass does with it.

#: The two front-utility actions of H-43: whether their category's `all` — and so `all-frontend` and `all` — runs them, and why.
H43_ACTIONS_IN_ALL = {
    "cloud-smoke": (False, "it refuses any lane but a managed one, and a lane is self-hosted unless given --lane-setting LIBREFOLIO_PROFILE=managed: in `all` it turns front-utility all, all-frontend and all red on the default lane. Register it with named_only=True"),
    "csp-collector": (True, "it runs on any lane, and stays in front-utility all, all-frontend and all"),
}
#: The same two: whether they run only when named on the command line, which the consolidated pre-pass reads too, and why.
H43_ACTIONS_NAMED_ONLY = {
    "cloud-smoke": (True, "in_all=False keeps it out of the serial `all` alone: the consolidated pre-pass groups whatever the dry run reports, and on a managed lane front-utility all would run it, all-frontend seven specs of other categories twice. Register it with named_only=True"),
    "csp-collector": (False, "it runs on any lane, so every `all` runs it, consolidated or serial, with a verdict of its own"),
}


@pytest.mark.parametrize(("action", "in_all", "why"), [(action, *rule) for action, rule in H43_ACTIONS_IN_ALL.items()], ids=list(H43_ACTIONS_IN_ALL))
def test_the_cloud_smoke_is_left_out_of_every_all_and_the_collector_spec_is_not(action, in_all, why):
    entry = test_runner_registry.TEST_REGISTRY["front-utility"].get(action)

    assert entry is not None, f"H-43: front-utility {action} is not registered: `dev.py test front-utility {action}` cannot run it"
    assert entry.get("in_all", True) is in_all, f"H-43: front-utility {action} is registered with in_all={entry.get('in_all', True)}, not {in_all}: {why}"


@pytest.mark.parametrize(("action", "named_only", "why"), [(action, *rule) for action, rule in H43_ACTIONS_NAMED_ONLY.items()], ids=list(H43_ACTIONS_NAMED_ONLY))
def test_the_cloud_smoke_runs_only_when_named_and_the_collector_spec_does_not(action, named_only, why):
    entry = test_runner_registry.TEST_REGISTRY["front-utility"].get(action)

    assert entry is not None, f"H-43: front-utility {action} is not registered: `dev.py test front-utility {action}` cannot run it"
    assert entry.get("named_only", False) is named_only, f"H-43: front-utility {action} is registered with named_only={entry.get('named_only', False)}, not {named_only}: {why}"
