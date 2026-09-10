"""Pure contract tests for per-run test port and data-directory isolation.

Covered here: data-directory resolution and its production guards, lane runtime
configuration, CLI/runner wiring, shared-backend ownership, and the
``exec_unmasked`` spawn wrapper. Every test is PURE — no server, no database, no
network — using ``tmp_path``, in-memory fakes, and (only where a real signal is
the subject) short-lived subprocesses that just print or wait.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import select
import shutil
import socket
import subprocess
import sys
import threading
import urllib.parse
from pathlib import Path
from types import SimpleNamespace

import pytest

import backend.app.config as backend_config
import dev
import scripts.cli_base as cli_base
import scripts.exec_unmasked as exec_unmasked
from backend.test_scripts import test_db_config
from backend.test_scripts import test_server_helper as test_server_helper_module
from scripts.test_runner import _backend_db as test_runner_backend_db
from scripts.test_runner import _cli as test_runner_cli
from scripts.test_runner import _common as test_runner_common
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


class TestDataDirResolution:
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

    @pytest.mark.parametrize("managed_relative", ["sqlite", "sqlite/app.db"])
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
        # values must land there even when they are only defaults.
        shell_probe, hydrated_probe = "LIBREFOLIO_RUNTIME_ISOLATION_SHELL_PROBE", "LIBREFOLIO_RUNTIME_ISOLATION_DOTENV_PROBE"
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
        assert os.environ[shell_probe] == "from-shell"
        assert os.environ.get(hydrated_probe) == ("hydrated-from-dotenv" if source == "dotenv" else None)

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
    prefix = cli_base.pipenv_prefix()
    if prefix and shutil.which(prefix[0]) is None:
        pytest.skip("pipenv is genuinely unavailable in this environment")
    if cli_base._project_dotenv_values().get(port_name) == str(port):
        port += 1
    # The nested Pipenv process still sees the real repository .env; the parent
    # must not hydrate unrelated repository values into this pytest process.
    runtime_env.setattr(cli_base, "_project_dotenv_values", lambda: {})
    configure = cli_base.configure_test_runtime if lane == "test" else cli_base.configure_server_runtime
    configured_port, configured_dir = configure(port=port, data_dir=f"runtime/pipenv-subprocess-{lane}-data")
    probe = f"import os; print(os.environ.get('{port_name}')); print(os.environ.get('{dir_name}')); print(os.environ.get('LIBREFOLIO_TEST_MODE'))"
    result = subprocess.run([*prefix, "python" if prefix else sys.executable, "-c", probe], cwd=cli_base.get_project_root(), env=os.environ.copy(), capture_output=True, text=True, timeout=120)

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

    def capture_exec(_executable, command, env):
        captured.update(command=command, env=dict(env))
        captured["events"].append("spawn")

    monkeypatch.setattr(dev, "HAS_ARGCOMPLETE", False)
    monkeypatch.setattr(dev, "check_port_in_use", lambda _port: captured["events"].append("port-check") or [])
    monkeypatch.setattr(dev, "auto_build_frontend", lambda *_a, **_kw: capture_build("frontend", None))
    monkeypatch.setattr(dev, "auto_build_mkdocs", lambda *_a, **_kw: capture_build("mkdocs", None))
    monkeypatch.setattr(dev, "update_js_cache", lambda *_a, **_kw: capture_build("js-cache", 0))
    monkeypatch.setattr(dev, "run_command_live", capture_run)
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
    @pytest.mark.parametrize(("marked_relative", "managed_root"), [pytest.param("custom-uploads/provider-cache/nested-production-root", "custom-uploads", id="custom-uploads"), pytest.param("broker_reports/uploaded/broker_7/nested-production-root", "broker_reports", id="broker-reports")])
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


class TestSharedTestServerOwnership:
    def test_start_rejects_an_occupied_port_without_spawning_or_signalling(self, monkeypatch):
        # That PID may be another worktree's lane: refuse before doing anything,
        # even though health would answer if start() ever reached the poll loop.
        server = test_runner_server.SharedTestServer()
        patch_spawn(monkeypatch, holders=["918273"], healthy=True)
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
        patch_clock(monkeypatch, test_runner_server, 0.0, 0.0, 0.0, 6.0, 6.0, 12.0, forbid_sleep="the bind-race path must not wait on the real clock")

        assert server.start() is False

        assert len(holder_calls) >= 3
        assert group_signals == [(child_group, test_runner_server.signal.SIGTERM)]
        assert process.wait_timeouts == [test_runner_server.SHUTDOWN_GRACE_PLAIN]
        assert (server.proc, server.process_group_id, ready) == (None, None, [])
        assert any("unowned PID" in message for message in errors), errors
        assert any(str(foreign_pid) in message and "foreign PID" in message for message in errors), errors

    @pytest.mark.parametrize(
        ("poll_results", "group_survives", "clock", "expected_signals"),
        [
            pytest.param([], False, (0.0, 6.0, 6.0, 12.0), ["SIGTERM"], id="group-exits-on-sigterm"),
            pytest.param([23], True, (0.0, 0.0, 6.0, 6.0, 12.0), ["SIGTERM", 0, 0, "SIGKILL"], id="group-ignores-sigterm"),
        ],
    )
    def test_stop_signals_only_its_own_group_and_merely_reports_a_foreign_pid(self, monkeypatch, poll_results, group_survives, clock, expected_signals):
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
        assert (holder_lookups, process.poll_calls, process.wait_timeouts) == ([foreign_pid], 1, [test_runner_server.SHUTDOWN_GRACE_PLAIN])
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


@pytest.mark.parametrize(("ci_env_value", "expected_timeout"), [(None, 120), ("true", 300)], ids=["ci-absent", "ci-present"])
def test_startup_timeout_matches_the_playwright_ci_contract(ci_env_value, expected_timeout):
    # STARTUP_TIMEOUT is computed once at import from os.environ["CI"], so only a
    # freshly loaded module in a controlled environment exercises both branches.
    probe_env = {name: value for name, value in os.environ.items() if name != "CI"}
    if ci_env_value is not None:
        probe_env["CI"] = ci_env_value
    result = subprocess.run([sys.executable, "-c", "from scripts.test_runner import _server as m; print(m.STARTUP_TIMEOUT)"], cwd=test_runner_common.PROJECT_ROOT, env=probe_env, capture_output=True, text=True, timeout=60)

    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert result.stdout.strip() == str(expected_timeout)


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
