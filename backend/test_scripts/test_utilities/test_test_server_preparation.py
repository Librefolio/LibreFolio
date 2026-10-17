"""The test server's builds run before its startup timeout, a tree without node_modules stops before npx (C-94), and a failed start shows the backend's own output (H-12).

``dev.py server --test`` builds what it serves before it binds: the frontend in debug (``auto_build_frontend``, or
``cmd_fe_build`` under ``--rebuild``), the MkDocs site, the JS cache. ``SharedTestServer.start()`` launched it with its
output on DEVNULL and started ``STARTUP_TIMEOUT`` right after the ``Popen``, so a rebuild after a merge (minutes)
counted against the startup timeout, invisibly; the gallery's Playwright ``webServer`` had the same problem. And
without ``frontend/node_modules`` the frontend build went on to ``npx svelte-check`` and to ``npm run generate-api``,
which calls ``npx openapi-zod-client``: npx then fetches from the registry instead of running the locked version.
The backend's own output stayed on DEVNULL once the builds had moved out: a start that failed said only ``Shared
backend exited during startup (code N)`` or ``Shared backend did not answer within Ns``, and nobody could tell why
(H-12).

The contracts held here:

* ``dev.py server --build-only`` runs the server's pre-bind steps, in today's order and mode, and returns their verdict
  without checking the port, running a command or exec'ing uvicorn; the runner's prerequisites command is such a run;
* ``cmd_fe_build`` and ``cmd_api_client`` first check ``frontend/node_modules/.bin`` for the tools they call, and stop
  with exit 1, naming what is missing and ``npm ci``, before any npm or npx call;
* ``SharedTestServer.start()`` checks the port, then runs ``dev.py server --test --build-only`` in the foreground, its
  output visible, with the runner's own environment (not the coverage wiring the server gets), and only then spawns
  the backend and starts ``STARTUP_TIMEOUT``: a build never counts against it, a failed build spawns nothing, an
  occupied port builds nothing;
* the build step's output comes out in order on a pipe too (CI, a ``tee``'d log), where Python block-buffers it: the
  runner flushes its stdout, then its stderr, after its info line and before the build starts, and runs the build as
  ``python -u dev.py …``, so dev.py's own messages come out among the npm, vite and mkdocs output they introduce;
* ``mkdocs gallery`` runs the same build step after its database step and its port check, before Playwright, with
  the environment Playwright gets (``LF_APP_VERSION`` included: the bundle bakes the version in); ``--list`` builds
  nothing;
* without ``--workers``, ``mkdocs gallery`` runs ``default_gallery_workers()`` browser workers, 60 % of the
  ``os.cpu_count()`` read at each call (two CPUs when it cannot tell), rounded, at least one, and sizes its server from
  them; an explicit ``--workers`` wins;
* outside ``--verbose``, ``SharedTestServer.start()`` gives the backend a log file as its stdout, its stderr merged in
  (a file, never a pipe): its ``log_path``, else ``shared_backend_log_path()``, ``shared-backend.log`` in the run's
  log folder, read at ``start()``. An instance's first start on that path empties the file (a previous run's, an
  earlier instance's) and creates its folder; a later start of the same instance on it, as when ``db create`` restarts
  the backend mid-run (``database_file_owned_exclusively()``), appends. The runner's own handle is closed right after
  the spawn, the path named in the info line before it. Without a run log folder (``_common.get_log_dir()`` None, as
  in this pytest process) the backend's output stays on DEVNULL, and under ``--verbose`` on the terminal: no file is
  written and ``log_path`` is None;
* a start that fails, by an exit during its startup or by ``STARTUP_TIMEOUT``, prints after its error line and before
  ``stop()`` the log's path and the last 30 lines this start wrote (fewer when it wrote fewer, ``(no output)`` when it
  wrote none, whatever earlier starts wrote), read by ``log_tail()`` from the file's size at the open and from at most
  its last 64 KiB, a line cut by that limit left out, bytes that are not UTF-8 replaced; without a log, under
  ``--verbose`` and after a start that succeeds, no tail comes out;
* ``cmd_fe_build`` takes the fingerprint of the Tool codegen inputs' listing (``tool_contract_fingerprint``, imported
  with ``record_tool_contract_inputs`` from ``scripts.cli_base``, whose ``check_frontend_needs_build()`` computes the
  one it compares) after its node_modules and JS cache checks, right before ``cmd_api_sync`` generates the codecs from
  those inputs, and records it only once the npm build answered 0: after a missing tool, a failed step or a failed
  build nothing is recorded (H-24r).

PURE — no server, no database, no network. Every seam (the build steps, ``subprocess``, ``os.execvpe``, signals,
lsof, health, the clock, the CPU count, the build step's ``sys`` streams) is faked, the ``node_modules/.bin`` layouts
and the backend's logs live under ``tmp_path`` (the run log folder set through monkeypatch only, never the real
``.testLog``), and an autouse fixture forbids every real process: one that started would build the frontend. One case,
in a class of its own, is the exception: it lets one real child start, through the real ``scripts/exec_unmasked.py`` —
a one-line Python that writes to its stderr and exits, never the backend — and signals no process group but its own.
"""

from __future__ import annotations

import inspect
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import dev
import scripts.cli_base as cli_base
from scripts.test_runner import _common as test_runner_common
from scripts.test_runner import _server as test_runner_server

# ── Shared fixtures, fakes and probes ──────────────────────────────────────

#: What the frontend build calls (``vite`` through npm, ``npx svelte-check``, ``npx openapi-zod-client`` through
#: ``generate-api``) and what the API client generator needs. Literals: dev.py's own tuples are asserted against them.
BUILD_TOOLS = ("openapi-zod-client", "svelte-check", "vite")
API_CLIENT_TOOLS = ("openapi-zod-client",)
#: A failing build's exit code, distinctive enough that an error naming it cannot match by accident.
FAILED_BUILD_CODE = 77
#: The test lane a runner exports to ``dev.py server --test --build-only``. Never bound: every port seam is faked.
LANE_PORT = "6139"
#: The lane variables ``dev.py server`` writes into ``os.environ`` (``configure_*_runtime``) before it builds.
RUNTIME_ENV_NAMES = ("LIBREFOLIO_TEST_MODE", "LIBREFOLIO_DATA_DIR", "LIBREFOLIO_TEST_DATA_DIR", "LIBREFOLIO_TEST_LANE_ID", "PORT", "TEST_PORT", "PIPENV_DONT_LOAD_ENV", "PIPENV_DOTENV_LOCATION")


def forbid(monkeypatch, target, name: str, reason: str, *, raising: bool = True) -> None:
    """Make an attribute fail the test if the code under test ever reaches it.

    ``raising=False`` also forbids a name the code does not define yet: a guard that holds before and after it exists.
    """

    def fail(*_args, **_kwargs):
        pytest.fail(reason)

    monkeypatch.setattr(target, name, fail, raising=raising)


@pytest.fixture(autouse=True)
def no_real_process(monkeypatch):
    """No test here may start a real process or signal one: a process that started would build the frontend or bind.

    A test that asserts on one of these seams replaces the forbidding stub with its own fake.
    """
    for name in ("run", "Popen"):
        forbid(monkeypatch, subprocess, name, f"a real subprocess.{name} was reached")
    for name in ("execvpe", "kill", "killpg"):
        forbid(monkeypatch, os, name, f"a real os.{name} was reached")


@pytest.fixture
def runtime_env(monkeypatch, tmp_path):
    """The lane a runner exports, under ``tmp_path``, and no lane variable of the caller's; every env change undone.

    ``dev.py server`` writes its lane into ``os.environ`` before it builds: the snapshot puts the caller's
    environment back, whatever the code under test did to it.
    """
    snapshot = dict(os.environ)
    for name in RUNTIME_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("TEST_PORT", LANE_PORT)
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "test-lane-data"))
    monkeypatch.setenv("LIBREFOLIO_DATA_DIR", str(tmp_path / "production-data"))
    yield monkeypatch
    os.environ.clear()
    os.environ.update(snapshot)


def record_errors(monkeypatch, module) -> list[str]:
    """Capture what ``module.print_error`` reports instead of printing it."""
    errors: list[str] = []
    monkeypatch.setattr(module, "print_error", errors.append)
    return errors


# ── Contract 1 — `dev.py server --build-only`: the pre-bind builds, and nothing after them ──


def run_dev(monkeypatch, *argv: str) -> int:
    """``dev.py <argv>`` in this process, through the real parser; argparse refusing it fails the test, not pytest."""
    monkeypatch.setattr(dev, "HAS_ARGCOMPLETE", False)
    monkeypatch.setattr(sys, "argv", ["dev.py", *argv])
    try:
        return dev.main()
    except SystemExit as exc:
        pytest.fail(f"dev.py {' '.join(argv)} raised SystemExit({exc.code!r}) instead of returning: argparse refuses an unknown flag this way")


def capture_pre_bind_steps(monkeypatch, *, forced_rebuild: bool = False, frontend_result=None) -> dict:
    """Replace what ``dev.py server`` does before it binds with an ordered recording; binding or spawning fails the test.

    ``steps`` holds each step with the ``LIBREFOLIO_TEST_MODE`` it ran under. The frontend goes through
    ``auto_build_frontend(debug=…)``, or through ``cmd_fe_build(BuildArgs)`` under ``--rebuild``: the other is forbidden.
    """
    captured: dict = {"steps": [], "frontend_debug": [], "js_cache_calls": []}

    def step(name: str, result):
        captured["steps"].append((name, os.environ.get("LIBREFOLIO_TEST_MODE")))
        return result

    def auto_build_frontend(*args, **kwargs):
        captured["frontend_debug"].append(kwargs.get("debug", args[0] if args else False))
        return step("frontend", frontend_result)

    def cmd_fe_build(build_args):
        captured["frontend_debug"].append(build_args.debug)
        return step("frontend", frontend_result)

    def update_js_cache(*args, **kwargs):
        captured["js_cache_calls"].append((args, kwargs))
        return step("js-cache", 0)

    used, unused = ("cmd_fe_build", "auto_build_frontend") if forced_rebuild else ("auto_build_frontend", "cmd_fe_build")
    monkeypatch.setattr(dev, used, cmd_fe_build if forced_rebuild else auto_build_frontend)
    forbid(monkeypatch, dev, unused, f"the frontend must be built through {used} here, never {unused}")
    monkeypatch.setattr(dev, "auto_build_mkdocs", lambda *_args, **_kwargs: step("mkdocs", None))
    monkeypatch.setattr(dev, "update_js_cache", update_js_cache)
    for name in ("check_port_in_use", "run_command_live"):
        forbid(monkeypatch, dev, name, f"--build-only reached {name}: it must stop before the port check and never start the server")
    # Z-10 moves the server launch to run_server_live, which dev.py does not define before it: raising=False.
    forbid(monkeypatch, dev, "run_server_live", "--build-only reached run_server_live: it must stop before the port check and never start the server", raising=False)
    forbid(monkeypatch, dev.os, "execvpe", "--build-only exec'd the server: it must stop before uvicorn")
    return captured


class TestBuildOnlyServer:
    """``dev.py server --build-only``: exactly what the server builds before binding, then the exit code, nothing more."""

    @pytest.mark.parametrize(
        ("flags", "frontend_result", "expected_debug", "expected_mode"),
        [
            pytest.param(("--test",), None, True, "1", id="test-lane-frontend-up-to-date"),
            pytest.param(("--test",), 0, True, "1", id="test-lane-frontend-rebuilt"),
            pytest.param(("--test", "--rebuild"), 0, True, "1", id="test-lane-forced-rebuild"),
            pytest.param((), None, False, "0", id="production-server"),
        ],
    )
    def test_build_only_runs_the_pre_bind_builds_in_order_and_never_binds(self, runtime_env, flags, frontend_result, expected_debug, expected_mode):
        # The same steps as before a real bind, in the same order and mode: a test server started after this finds
        # its bundle up to date (debug, which --test forces) and binds at once, inside STARTUP_TIMEOUT.
        captured = capture_pre_bind_steps(runtime_env, forced_rebuild="--rebuild" in flags, frontend_result=frontend_result)

        assert run_dev(runtime_env, "server", *flags, "--build-only") == 0

        assert captured["steps"] == [("frontend", expected_mode), ("mkdocs", expected_mode), ("js-cache", expected_mode)]
        assert captured["frontend_debug"] == [expected_debug]
        # As before a bind: not strict, so a resource missing from the cache falls back to the CDN, never fails.
        assert captured["js_cache_calls"] == [((), {})]

    @pytest.mark.parametrize("flags", [pytest.param(("--test",), id="stale-frontend-build-fails"), pytest.param(("--test", "--rebuild"), id="forced-rebuild-fails")])
    def test_a_failed_frontend_build_ends_build_only_with_its_exit_code(self, runtime_env, flags):
        # As before a bind today: no docs and no JS cache are built for a server that will not start.
        captured = capture_pre_bind_steps(runtime_env, forced_rebuild="--rebuild" in flags, frontend_result=FAILED_BUILD_CODE)
        for name in ("auto_build_mkdocs", "update_js_cache"):
            forbid(runtime_env, dev, name, f"{name} ran after a failed frontend build")

        assert run_dev(runtime_env, "server", *flags, "--build-only") == FAILED_BUILD_CODE

        assert captured["steps"] == [("frontend", "1")]

    @pytest.mark.parametrize(
        ("argv", "expected"),
        [
            pytest.param(("server", "--test", "--build-only"), True, id="test-mode"),
            pytest.param(("server", "--build-only"), True, id="production-mode"),
            pytest.param(("server", "--test"), False, id="test-mode-default"),
            pytest.param(("server",), False, id="production-mode-default"),
        ],
    )
    def test_the_server_parser_has_build_only_off_by_default(self, monkeypatch, argv, expected):
        parsed: list = []
        monkeypatch.setattr(dev, "cmd_server", lambda args: parsed.append(args) or 0)

        assert run_dev(monkeypatch, *argv) == 0

        (args,) = parsed
        assert vars(args).get("build_only", "<no build_only>") is expected

    def test_the_runner_prerequisites_command_is_a_build_only_test_server_run(self, runtime_env):
        # The two halves of C-94 must agree: the argv the runner launches is one dev.py takes as a test-mode build.
        command = test_runner_server.prerequisites_command()
        captured = capture_pre_bind_steps(runtime_env)

        assert run_dev(runtime_env, *command[command.index("dev.py") + 1 :]) == 0

        assert captured["steps"] == [("frontend", "1"), ("mkdocs", "1"), ("js-cache", "1")]
        assert captured["frontend_debug"] == [True]


# ── Contract 2 — `frontend/node_modules/.bin` is checked before any npm or npx call ──
#
# Without it, a tree with no node_modules reached `npx svelte-check` (cmd_fe_build) and `npm run generate-api`
# (cmd_api_client), whose `npx openapi-zod-client` then fetched from the registry instead of the locked version.

#: What ``cmd_fe_build`` does after its check, in its order: none of it may run while a tool is missing.
FE_BUILD_STEPS = ((dev, "update_js_cache"), (dev, "cmd_api_sync"), (dev, "run_command_live"), (dev.i18n_catalog, "build"), (dev, "generate_favicon"), (dev, "stamp_service_worker"))


def frontend_node_bin(monkeypatch, root: Path, *tools: str, installed: bool = True, layout: str = "npm-symlinks") -> Path:
    """Point ``dev.FRONTEND_NODE_BIN`` at a ``node_modules/.bin`` under ``root`` holding exactly ``tools``.

    ``installed=False`` leaves ``node_modules`` absent, as in a fresh worktree. ``layout`` is npm's on POSIX (a symlink
    into each tool's package) or, as ``"shim-files"``, npm's on Windows (a plain file per tool).
    """
    node_bin = root / "node_modules" / ".bin"
    if installed:
        node_bin.mkdir(parents=True)
    for tool in tools:
        if layout == "npm-symlinks":
            target = root / "node_modules" / tool / "bin" / "cli.js"
            target.parent.mkdir(parents=True)
            target.write_text("#!/usr/bin/env node\n", encoding="utf-8")
            (node_bin / tool).symlink_to(target)
        else:
            (node_bin / tool).write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(dev, "FRONTEND_NODE_BIN", node_bin)
    return node_bin


def forbid_steps(monkeypatch, steps, reason: str) -> None:
    """``forbid`` each ``(target, name)`` of ``steps``, the step's name appended to ``reason``."""
    for target, name in steps:
        forbid(monkeypatch, target, name, f"{reason}: {name} ran")


def assert_reports_missing_tools(errors: list[str], output: str, missing) -> None:
    """The error names every missing tool; the error or the hints after it say ``npm ci``."""
    reported = "\n".join(errors)
    assert all(tool in reported for tool in missing), f"the error does not name every missing tool {missing}: {errors}"
    assert "npm ci" in f"{reported}\n{output}", f"no `npm ci` in the error or the hints: {errors} / {output!r}"


class TestFrontendToolsCheck:
    """The tools a command calls are checked in ``frontend/node_modules/.bin`` first: missing, it stops with exit 1."""

    def test_the_checked_tools_are_the_ones_the_build_and_the_api_client_call(self):
        assert dev.FRONTEND_NODE_BIN == dev.PROJECT_ROOT / "frontend" / "node_modules" / ".bin"
        assert dev.FRONTEND_BUILD_BINARIES == BUILD_TOOLS
        assert dev.API_CLIENT_BINARIES == API_CLIENT_TOOLS

    @pytest.mark.parametrize(
        ("installed_tools", "installed", "layout", "asked", "expected"),
        [
            pytest.param((), False, "npm-symlinks", BUILD_TOOLS, list(BUILD_TOOLS), id="fresh-worktree"),
            pytest.param((), True, "npm-symlinks", BUILD_TOOLS, list(BUILD_TOOLS), id="empty-bin"),
            pytest.param(("vite",), True, "npm-symlinks", BUILD_TOOLS, ["openapi-zod-client", "svelte-check"], id="partial-npm-symlinks"),
            pytest.param(("vite",), True, "shim-files", BUILD_TOOLS, ["openapi-zod-client", "svelte-check"], id="partial-shim-files"),
            pytest.param(("vite",), True, "npm-symlinks", BUILD_TOOLS[::-1], ["svelte-check", "openapi-zod-client"], id="asked-order-kept"),
            pytest.param(BUILD_TOOLS, True, "npm-symlinks", BUILD_TOOLS, [], id="complete"),
        ],
    )
    def test_missing_frontend_binaries_lists_the_absent_tools_in_the_order_asked(self, monkeypatch, tmp_path, installed_tools, installed, layout, asked, expected):
        frontend_node_bin(monkeypatch, tmp_path, *installed_tools, installed=installed, layout=layout)

        assert list(dev.missing_frontend_binaries(asked)) == expected

    def test_require_frontend_dependencies_is_silent_when_every_tool_is_there(self, monkeypatch, tmp_path, capsys):
        frontend_node_bin(monkeypatch, tmp_path, *BUILD_TOOLS)
        errors = record_errors(monkeypatch, dev)

        assert dev.require_frontend_dependencies(BUILD_TOOLS, purpose="the frontend build") == 0

        assert (errors, tuple(capsys.readouterr())) == ([], ("", ""))

    def test_require_frontend_dependencies_names_what_is_missing_and_npm_ci(self, monkeypatch, tmp_path, capsys):
        frontend_node_bin(monkeypatch, tmp_path, "vite")
        errors = record_errors(monkeypatch, dev)

        assert dev.require_frontend_dependencies(BUILD_TOOLS, purpose="the frontend build") == 1

        assert_reports_missing_tools(errors, capsys.readouterr().out, ("openapi-zod-client", "svelte-check"))

    @pytest.mark.parametrize(
        ("installed_tools", "installed", "missing"),
        [
            pytest.param((), False, BUILD_TOOLS, id="fresh-worktree"),
            pytest.param((), True, BUILD_TOOLS, id="empty-bin"),
            pytest.param(("vite",), True, ("openapi-zod-client", "svelte-check"), id="partial"),
        ],
    )
    def test_fe_build_stops_before_any_step_when_a_tool_is_missing(self, monkeypatch, tmp_path, capsys, installed_tools, installed, missing):
        frontend_node_bin(monkeypatch, tmp_path, *installed_tools, installed=installed)
        forbid_steps(monkeypatch, FE_BUILD_STEPS, "cmd_fe_build went past a failed node_modules check")
        errors = record_errors(monkeypatch, dev)

        assert dev.cmd_fe_build(SimpleNamespace(debug=True)) == 1

        assert_reports_missing_tools(errors, capsys.readouterr().out, missing)

    def test_fe_build_goes_on_to_its_first_step_when_every_tool_is_there(self, monkeypatch, tmp_path):
        # The positive control: an installed tree passes the check and the JS cache step comes next. Its failure
        # (exit 9) ends the build there, so nothing is built for real.
        frontend_node_bin(monkeypatch, tmp_path, *BUILD_TOOLS)
        monkeypatch.setattr(dev, "update_js_cache", lambda *_args, **_kwargs: 9)
        forbid_steps(monkeypatch, FE_BUILD_STEPS[1:], "cmd_fe_build went past a failed JS cache step")

        assert dev.cmd_fe_build(SimpleNamespace(debug=True)) == 9

    @pytest.mark.parametrize("tools_only", [False, True], ids=["generate-api", "generate-tools"])
    @pytest.mark.parametrize(
        ("installed_tools", "installed"),
        [
            pytest.param((), False, id="fresh-worktree"),
            pytest.param((), True, id="empty-bin"),
            pytest.param(("svelte-check", "vite"), True, id="build-tools-without-the-generator"),
        ],
    )
    def test_api_client_stops_before_npm_when_its_generator_is_missing(self, monkeypatch, tmp_path, capsys, tools_only, installed_tools, installed):
        # generate-api runs `npx openapi-zod-client`; generate-tools imports it as a library.
        frontend_node_bin(monkeypatch, tmp_path, *installed_tools, installed=installed)
        forbid(monkeypatch, dev, "run_command_live", "cmd_api_client ran npm without openapi-zod-client installed")
        errors = record_errors(monkeypatch, dev)

        assert dev.cmd_api_client(SimpleNamespace(tools_only=tools_only)) == 1

        assert_reports_missing_tools(errors, capsys.readouterr().out, API_CLIENT_TOOLS)

    @pytest.mark.parametrize(("tools_only", "script"), [(False, "generate-api"), (True, "generate-tools")], ids=["generate-api", "generate-tools"])
    def test_api_client_runs_its_npm_script_once_its_generator_is_installed(self, monkeypatch, tmp_path, tools_only, script):
        # Only openapi-zod-client is installed: the API client needs nothing else, and runs exactly as before.
        frontend_node_bin(monkeypatch, tmp_path, *API_CLIENT_TOOLS)
        calls: list = []
        monkeypatch.setattr(dev, "run_command_live", lambda *args, **kwargs: calls.append((args, kwargs)) or 0)

        assert dev.cmd_api_client(SimpleNamespace(tools_only=tools_only)) == 0

        assert calls == [((["npm", "run", script],), {"cwd": dev.PROJECT_ROOT / "frontend"})]


# ── Contract 3 — SharedTestServer.start(): port check, build step, then the spawn and its deadline ──

SERVER_PID, SERVER_GROUP = 48001, 48000


class FakeClock:
    """``_server``'s ``time``: still unless a fake moves ``now``; any sleep fails the test."""

    def __init__(self):
        self.now = 0.0

    def time(self) -> float:
        return self.now

    monotonic = perf_counter = time

    def sleep(self, _seconds):
        pytest.fail("this path must not wait on the clock")


class FakeServerProcess:
    """The ``Popen`` of a backend that stays up: ``poll()`` always answers None."""

    pid, returncode = SERVER_PID, None

    def poll(self):
        return None


def patch_start(monkeypatch, *, holders=(), build=None, spawn=None, clock=None) -> None:
    """Wire ``SharedTestServer.start()`` to fakes: lsof, the build step, ``Popen``, the PGID, health, the clock.

    ``build=None`` keeps the real build step, whose ``subprocess.run`` stays forbidden unless the test fakes it;
    ``spawn=None`` forbids the spawn. Health answers yes at the first poll.
    """
    monkeypatch.setattr(test_runner_server, "port_holders", holders if callable(holders) else (lambda port=None: list(holders)))
    if build is not None:
        monkeypatch.setattr(test_runner_server, "build_server_prerequisites", build)
    if spawn is None:
        forbid(monkeypatch, test_runner_server.subprocess, "Popen", "the backend was spawned on a path that must spawn nothing")
    else:
        monkeypatch.setattr(test_runner_server.subprocess, "Popen", spawn)
    monkeypatch.setattr(test_runner_server.os, "getpgid", lambda _pid: SERVER_GROUP)
    monkeypatch.setattr(test_runner_server, "is_healthy", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(test_runner_server, "time", clock or FakeClock())


class TestSharedServerBuildsBeforeItsDeadline:
    """``SharedTestServer.start()``: the port check, then the build step, then the spawn and ``STARTUP_TIMEOUT``."""

    def test_start_checks_the_port_then_builds_then_spawns(self, monkeypatch):
        # Port first: refusing a held lane after minutes of building would waste them. Spawn last: no backend may
        # serve a bundle the build step did not finish.
        server, events = test_runner_server.SharedTestServer(), []
        patch_start(
            monkeypatch,
            holders=lambda port=None: events.append("port-check") or [],
            build=lambda *_args, **_kwargs: events.append("build") or True,
            spawn=lambda *_args, **_kwargs: events.append("spawn") or FakeServerProcess(),
        )
        forbid(monkeypatch, server, "stop", "a start that is healthy at its first poll must not be stopped")

        assert server.start() is True

        assert events[:3] == ["port-check", "build", "spawn"]
        assert events.count("build") == 1
        assert (server.process_group_id, server.started_here) == (SERVER_GROUP, True)

    def test_the_build_step_does_not_count_against_the_startup_timeout(self, monkeypatch):
        # A build longer than STARTUP_TIMEOUT itself, then a backend that answers at once: only a deadline started
        # after the build lets this start succeed.
        server, clock, build_started_at = test_runner_server.SharedTestServer(), FakeClock(), []

        def slow_build(*_args, **_kwargs):
            build_started_at.append(clock.now)
            clock.now += test_runner_server.STARTUP_TIMEOUT + 100
            return True

        patch_start(monkeypatch, build=slow_build, spawn=lambda *_args, **_kwargs: FakeServerProcess(), clock=clock)
        forbid(monkeypatch, server, "stop", "the start timed out: its deadline counted the build step")

        assert server.start() is True

        assert build_started_at == [0.0]

    def test_a_build_step_that_fails_spawns_nothing(self, monkeypatch):
        server = test_runner_server.SharedTestServer()
        patch_start(monkeypatch, build=lambda *_args, **_kwargs: False)

        assert server.start() is False

        assert (server.proc, server.process_group_id, server.started_here) == (None, None, False)

    def test_a_build_command_that_exits_non_zero_spawns_nothing_and_names_its_code(self, monkeypatch):
        # The real build step, down to its subprocess.run of `dev.py server --test --build-only`.
        server, runs = test_runner_server.SharedTestServer(), []
        patch_start(monkeypatch)
        monkeypatch.setattr(test_runner_server.subprocess, "run", lambda command, *_args, **_kwargs: runs.append(command) or subprocess.CompletedProcess(command, FAILED_BUILD_CODE))
        errors = record_errors(monkeypatch, test_runner_server)

        assert server.start() is False

        assert runs == [test_runner_server.prerequisites_command()]
        assert (server.proc, server.process_group_id, server.started_here) == (None, None, False)
        assert any(re.search(rf"\b{FAILED_BUILD_CODE}\b", message) for message in errors), errors

    def test_an_occupied_port_is_refused_before_anything_is_built(self, monkeypatch):
        server = test_runner_server.SharedTestServer()
        patch_start(monkeypatch, holders=["918273"])
        forbid(monkeypatch, test_runner_server, "build_server_prerequisites", "the build step ran while the port was held by another lane")
        errors = record_errors(monkeypatch, test_runner_server)

        assert server.start() is False

        assert (server.proc, server.started_here) == (None, False)
        assert any("918273" in message for message in errors), errors

    def test_the_build_step_gets_the_runner_env_and_only_the_server_the_coverage_wiring(self, monkeypatch):
        # Under --coverage the backend measures itself, the build must not: it comes out the same either way, and
        # configure_test_runtime imports backend.app.config, which .coveragerc measures.
        for name in ("COVERAGE_PROCESS_START", "PYTHONPATH"):
            monkeypatch.delenv(name, raising=False)
        server, build_envs, spawn_envs = test_runner_server.SharedTestServer(coverage=True), [], []

        def build(*args, **kwargs):
            given = kwargs.get("env", args[0] if args else None)
            build_envs.append(dict(os.environ if given is None else given))
            return True

        patch_start(monkeypatch, build=build, spawn=lambda *_args, **kwargs: spawn_envs.append(kwargs["env"]) or FakeServerProcess())

        assert server.start() is True

        (build_env,) = build_envs
        assert "COVERAGE_PROCESS_START" not in build_env
        assert str(test_runner_common.COVERAGE_SITECUSTOMIZE_DIR) not in build_env.get("PYTHONPATH", "")
        (spawn_env,) = spawn_envs
        assert spawn_env["COVERAGE_PROCESS_START"] == str(test_runner_common.PROJECT_ROOT / ".coveragerc")


# ── Contract 4 — build_server_prerequisites(): the build-only server, in the foreground, its output in order ──
#
# On a pipe (CI, a tee'd gallery log, the runner's own logs) Python block-buffers stdout. In one log the runner's info
# line came out 262 s late, after the whole build; inside the build, dev.py's own messages ("Frontend sources changed,
# rebuilding…", "Frontend build complete!") came out at its exit, after the npm, vite and mkdocs output they introduce.
# A terminal, line-buffered, showed the right order: only the logs were scrambled.


class FlushRecordingStream:
    """``_server``'s ``sys.stdout`` or ``sys.stderr``: each ``flush()`` recorded as ``<name>.flush``, then done for real.

    Everything else goes to the real stream, looked up at each call: whatever pytest's capture put there gets it.
    """

    def __init__(self, name: str, events: list[str]):
        self._name, self._events = name, events

    def flush(self):
        self._events.append(f"{self._name}.flush")
        getattr(sys, self._name).flush()

    def __getattr__(self, attribute: str):
        return getattr(getattr(sys, self._name), attribute)


class SysRecordingFlushes:
    """``_server``'s ``sys``: the real module, ``executable`` included, but for its two streams, which record their flushes."""

    def __init__(self, events: list[str]):
        self.stdout = FlushRecordingStream("stdout", events)
        self.stderr = FlushRecordingStream("stderr", events)

    def __getattr__(self, name: str):
        return getattr(sys, name)


def record_build_runs(monkeypatch, *, returncode: int) -> tuple[list[str], list[tuple]]:
    """Fake ``_server``'s ``subprocess.run`` (answering ``returncode``), ``print_info``, ``sys`` and clock; order the calls.

    ``events`` gets ``info``, ``stdout.flush``, ``stderr.flush`` and ``run``, as they happen.
    """
    events: list[str] = []
    runs: list[tuple] = []

    def fake_run(*args, **kwargs):
        events.append("run")
        runs.append((args, kwargs))
        return subprocess.CompletedProcess(args[0] if args else kwargs.get("args"), returncode)

    monkeypatch.setattr(test_runner_server.subprocess, "run", fake_run)
    monkeypatch.setattr(test_runner_server, "print_info", lambda _message: events.append("info"))
    monkeypatch.setattr(test_runner_server, "sys", SysRecordingFlushes(events))
    monkeypatch.setattr(test_runner_server, "time", FakeClock())
    return events, runs


class TestBuildServerPrerequisites:
    """``build_server_prerequisites()``: ``python -u dev.py server --test --build-only``, its output on the terminal in order, its verdict."""

    def test_the_command_is_a_test_mode_build_only_server(self):
        command = test_runner_server.prerequisites_command()

        # -u: dev.py unbuffered, so on a pipe its own messages come out among its subprocesses' output, not at its exit.
        assert command == [sys.executable, "-u", "dev.py", "server", "--test", "--build-only"]
        # An interpreter option goes before the script: after it, -u would be one of dev.py's own arguments.
        assert "-u" in command[: command.index("dev.py")], command
        # From the cwd the step runs in, the dev.py this module imports.
        assert (Path(test_runner_server.PROJECT_ROOT) / command[command.index("dev.py")]).resolve() == Path(dev.__file__).resolve()

    @pytest.mark.parametrize("call_kwargs", [{}, {"env": {"LF_APP_VERSION": "explicit-env"}}], ids=["inherited-env", "explicit-env"])
    def test_it_runs_the_command_in_the_foreground_with_its_output_visible(self, monkeypatch, call_kwargs):
        # Inherited stdout/stderr, never DEVNULL: a build lasts minutes and must be seen. check=False: a failed build
        # is a verdict, not an exception.
        events, runs = record_build_runs(monkeypatch, returncode=0)
        errors = record_errors(monkeypatch, test_runner_server)

        assert test_runner_server.build_server_prerequisites(**call_kwargs) is True

        ((args, kwargs),) = runs
        assert args == (test_runner_server.prerequisites_command(),)
        assert Path(kwargs.get("cwd", "<no cwd>")).resolve() == Path(test_runner_server.PROJECT_ROOT).resolve()
        assert kwargs.get("env") == call_kwargs.get("env")
        assert kwargs.get("check", False) is False
        assert not kwargs.get("shell", False)
        assert not {"capture_output", "stdout", "stderr"} & kwargs.keys(), f"the build's output must reach the terminal: {kwargs}"
        assert "info" in events[: events.index("run")], events
        assert errors == []

    @pytest.mark.parametrize("call_kwargs", [{}, {"env": {"LF_APP_VERSION": "explicit-env"}}], ids=["inherited-env", "explicit-env"])
    def test_it_flushes_its_output_after_its_info_line_and_before_the_build_starts(self, monkeypatch, call_kwargs):
        # The build writes to this process's stdout and stderr. On a pipe, a line still in this process's buffer comes
        # out after the whole build: both streams are flushed once the info line is written and before the build
        # starts. Flushed before the line, the line stays in the buffer; flushed after the run, it comes out too late.
        events, _runs = record_build_runs(monkeypatch, returncode=0)

        assert test_runner_server.build_server_prerequisites(**call_kwargs) is True

        assert "run" in events, f"the build never started: {events}"
        # What the step did last before the build started: the info line, then a flush of each stream, nothing between.
        assert events[: events.index("run") + 1][-4:] == ["info", "stdout.flush", "stderr.flush", "run"], events

    def test_a_build_that_exits_non_zero_is_false_and_its_exit_code_is_named(self, monkeypatch):
        _events, runs = record_build_runs(monkeypatch, returncode=FAILED_BUILD_CODE)
        errors = record_errors(monkeypatch, test_runner_server)

        assert test_runner_server.build_server_prerequisites() is False

        assert len(runs) == 1
        assert any(re.search(rf"\b{FAILED_BUILD_CODE}\b", message) for message in errors), errors


# ── Contract 5 — `mkdocs gallery`: the same build step, before Playwright, with Playwright's environment ──
#
# Playwright's webServer starts `dev.py server --test` itself, so its builds fell inside STARTUP_TIMEOUT_S. The
# gallery now builds first, after its database step and its port check. The colour coordinator's condition: the
# step gets the environment Playwright gets, LF_APP_VERSION included, because the bundle bakes the version in.


def gallery_args(**overrides) -> SimpleNamespace:
    """``mkdocs gallery`` arguments: desktop only, one browser worker, the lane DB reused, a test port of its own."""
    values = {"list_tests": False, "filter": None, "desktop_only": True, "mobile_only": False, "no_populate": True, "test_port": 6199, "force": False, "workers": 1, "headed": False, "ui": False}
    return SimpleNamespace(**{**values, **overrides})


class FakePlaywright:
    """The gallery's ``npm run test:e2e`` process: no output, exit 0."""

    def __init__(self):
        self.stdout, self.returncode = iter([]), 0

    def wait(self):
        return self.returncode


class TestGalleryBuildsBeforePlaywright:
    """``mkdocs gallery``: the build step runs between its port check and Playwright, with Playwright's environment."""

    def test_the_build_step_runs_before_playwright_with_the_environment_playwright_gets(self, runtime_env):
        runtime_env.setenv("LF_APP_VERSION", "x-c94")
        events, seen = [], {}

        def build(*args, **kwargs):
            events.append("build")
            seen["build_env"] = dict(kwargs.get("env", args[0] if args else None) or {})
            return True

        def playwright(command, *_args, **kwargs):
            events.append("playwright")
            seen.update(command=command, cwd=kwargs.get("cwd"), playwright_env=dict(kwargs.get("env") or {}))
            return FakePlaywright()

        runtime_env.setattr(dev, "_reuse_gallery_test_db", lambda: events.append("lane-db") or True)
        runtime_env.setattr(dev, "check_port_in_use", lambda _port: events.append("port-check") or [])
        runtime_env.setattr(test_runner_server, "build_server_prerequisites", build)
        runtime_env.setattr(dev.subprocess, "Popen", playwright)

        assert dev.cmd_mkdocs_gallery(gallery_args()) == 0

        assert events == ["lane-db", "port-check", "build", "playwright"]
        assert (seen["build_env"].get("LF_APP_VERSION"), seen["build_env"].get("TEST_PORT")) == ("x-c94", "6199")
        assert seen["build_env"] == seen["playwright_env"]
        assert seen["command"][:5] == ["npm", "run", "test:e2e", "--", "gallery.spec.ts"]
        assert seen["cwd"] == dev.PROJECT_ROOT / "frontend"

    def test_a_failed_build_step_ends_the_gallery_before_playwright(self, runtime_env):
        events: list[str] = []
        runtime_env.setattr(dev, "_reuse_gallery_test_db", lambda: True)
        runtime_env.setattr(dev, "check_port_in_use", lambda _port: [])
        runtime_env.setattr(test_runner_server, "build_server_prerequisites", lambda *_args, **_kwargs: events.append("build") or False)
        forbid(runtime_env, dev.subprocess, "Popen", "Playwright started after a failed build step")
        errors = record_errors(runtime_env, dev)

        assert dev.cmd_mkdocs_gallery(gallery_args()) == 1

        assert events == ["build"]
        assert errors, "the gallery stopped without saying why"

    def test_list_only_lists_and_builds_nothing(self, runtime_env):
        # A guard, green before C-94 as after: --list returns before the database step, the port check and the
        # build step. raising=False: the build step does not exist before C-94.
        forbid(runtime_env, test_runner_server, "build_server_prerequisites", "--list ran the build step", raising=False)
        for name in ("_reuse_gallery_test_db", "check_port_in_use"):
            forbid(runtime_env, dev, name, f"--list reached {name}")

        assert dev.cmd_mkdocs_gallery(gallery_args(list_tests=True)) == 0


# ── Contract 6 — `mkdocs gallery` without --workers: 60 % of the CPUs as browsers, the server sized from them ──
#
# The default was max(2, os.cpu_count()) browsers, and one server worker per four of them: 10 browsers and 3 server
# workers on a 10-CPU Mac, where one run reached load 65 and 8 reds in 10 minutes came from saturation alone. With 6
# browsers, two 30-minute runs were green at load 11–16: the colour coordinator asked for 60 % of the CPUs.

#: CPUs → the gallery's default browser workers, round(0.6 × CPUs) and at least one. Literals: dev.py's function is
#: asserted against them. 0.6 × a whole number never ends in .5, so no row depends on how round() breaks a tie.
DEFAULT_GALLERY_WORKERS_BY_CPUS = ((1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (8, 5), (10, 6), (16, 10))


def report_cpus(monkeypatch, cpus: int | None) -> None:
    """Make ``os.cpu_count()`` answer ``cpus``, whatever this machine has; None is a platform that cannot tell."""
    monkeypatch.setattr(dev.os, "cpu_count", lambda: cpus)


def launch_gallery(monkeypatch, args) -> tuple[list[str], dict]:
    """``cmd_mkdocs_gallery(args)`` through contract 5's fakes; the argv and the env of the one Playwright it launched."""
    launched: list[tuple[list[str], dict]] = []

    def playwright(command, *_args, **kwargs):
        launched.append((list(command), dict(kwargs.get("env") or {})))
        return FakePlaywright()

    monkeypatch.setattr(dev, "_reuse_gallery_test_db", lambda: True)
    monkeypatch.setattr(dev, "check_port_in_use", lambda _port: [])
    monkeypatch.setattr(test_runner_server, "build_server_prerequisites", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(dev.subprocess, "Popen", playwright)

    assert dev.cmd_mkdocs_gallery(args) == 0

    (launch,) = launched
    return launch


def playwright_workers(command: list[str]) -> str | None:
    """The value after ``--workers`` in a Playwright argv, which carries the flag at most once; None without it."""
    assert command.count("--workers") <= 1, f"--workers given more than once: {command}"
    return command[command.index("--workers") + 1] if "--workers" in command else None


class TestGalleryDefaultBrowserWorkers:
    """``mkdocs gallery`` without ``--workers``: 60 % of the CPUs as browser workers, at least one; its server follows."""

    @pytest.mark.parametrize(("cpus", "expected"), DEFAULT_GALLERY_WORKERS_BY_CPUS, ids=[f"{cpus}-cpus" for cpus, _ in DEFAULT_GALLERY_WORKERS_BY_CPUS])
    def test_the_default_is_sixty_percent_of_the_cpus_rounded_and_at_least_one(self, cpus, expected):
        assert dev.default_gallery_workers(cpus) == expected

    def test_the_share_is_sixty_percent_of_the_cpus(self):
        # The share by name, the knob a later tuning turns: moving it is a decision a test sees, not a side effect.
        assert dev.GALLERY_BROWSER_WORKERS_PER_CPU == 0.6

    def test_without_a_count_it_reads_the_cpu_count_at_each_call(self, monkeypatch):
        # Two answers in one process: a count read once (a default argument, a module constant) gives the same twice,
        # and on a 10-CPU machine the first answer alone could not tell. None is a platform that cannot tell: the
        # fallback of two CPUs gives one browser.
        report_cpus(monkeypatch, 10)
        on_ten_cpus = dev.default_gallery_workers()
        report_cpus(monkeypatch, None)
        on_unknown_cpus = dev.default_gallery_workers()

        assert (on_ten_cpus, on_unknown_cpus) == (6, 1)

    @pytest.mark.parametrize(("cpus", "browsers", "servers"), [pytest.param(10, "6", "2", id="10-cpus"), pytest.param(16, "10", "3", id="16-cpus")])
    def test_the_gallery_without_workers_runs_the_default_and_sizes_its_server_from_it(self, runtime_env, cpus, browsers, servers):
        # Before C-94, 10 CPUs gave 10 browsers and 3 server workers. Two machines, so a fixed count cannot pass: the
        # default follows the CPUs of the machine the gallery runs on.
        report_cpus(runtime_env, cpus)

        command, env = launch_gallery(runtime_env, gallery_args(workers=None))

        assert (playwright_workers(command), env.get("GALLERY_SERVER_WORKERS")) == (browsers, servers)

    @pytest.mark.parametrize(("workers", "servers"), [pytest.param(3, "1", id="below-the-default"), pytest.param(12, "3", id="above-the-default")])
    def test_an_explicit_workers_wins_over_the_default(self, runtime_env, workers, servers):
        # A guard, green before C-94 as after: the default (6 on these 10 CPUs) is neither a floor nor a cap on an
        # explicit count, and the server is sized from the count given.
        report_cpus(runtime_env, 10)

        command, env = launch_gallery(runtime_env, gallery_args(workers=workers))

        assert (playwright_workers(command), env.get("GALLERY_SERVER_WORKERS")) == (str(workers), servers)

    @pytest.mark.parametrize(("argv", "expected"), [pytest.param((), None, id="no-flag"), pytest.param(("--workers", "3"), 3, id="explicit")])
    def test_the_gallery_parser_leaves_workers_unset_without_the_flag(self, monkeypatch, argv, expected):
        # A guard, green before C-94 as after, and the precondition of the gallery tests above: gallery_args(workers=None)
        # is the command line without the flag only while the parser's default is None. Any other default would leave
        # default_gallery_workers unreachable from the command line, however right it is.
        parsed: list = []
        monkeypatch.setattr(dev, "cmd_mkdocs_gallery", lambda args: parsed.append(args) or 0)

        assert run_dev(monkeypatch, "mkdocs", "gallery", *argv) == 0

        (args,) = parsed
        assert vars(args).get("workers", "<no workers>") == expected


# ── Contract 7 — the backend's output goes to a log file, whose tail a failed start prints (H-12) ──
#
# start() gave the backend DEVNULL for its stdout and stderr: a backend that exited during its startup left "Shared
# backend exited during startup (code N)", one that hung "Shared backend did not answer within Ns", and nothing said
# why. Outside --verbose its output now goes to a file: log_path when given, else shared-backend.log in the run's log
# folder (--log-dir, .testLog by default, which the runner prepares before it starts the backend), read at start().
# A failed start prints the file's last lines. Without a run log folder the spawn stays on DEVNULL: this pytest process
# has none (_common._LOG_DIR is None), and a fallback to <root>/.testLog would let every fake start() of these files
# truncate the live server's log in the middle of an all-backend run.
#
# A restart of the same instance (db create stops the shared backend and starts it again, mid-run) appends instead of
# emptying the file, and its failure prints only what it wrote itself: from the file's size when it opened it.
#
# Before H-12, SharedTestServer.__init__ has no log_path and _server neither shared_backend_log_path nor log_tail: all
# are looked up at call time, so the contracts above still run and every case below fails on one of these barriers.

#: The log's name in the run's log folder.
SHARED_BACKEND_LOG_NAME = "shared-backend.log"
#: What an empty log prints instead of lines: the contract's example, and the one literal of the tail pinned here.
EMPTY_LOG_MARKER = "(no output)"
#: The most of the log a failed start may read to find its last lines.
TAIL_READ_LIMIT = 64 * 1024
#: How the backend that dies during its startup exits, and today's error line for it, which the tail follows.
EXIT_CODE_DURING_STARTUP = 3
EXITED_LINE = f"Shared backend exited during startup (code {EXIT_CODE_DURING_STARTUP})"
#: Bytes no UTF-8 decoder accepts: a lone continuation byte, two bytes UTF-8 never uses, a sequence cut short.
NOT_UTF8 = b"\x80\xfe\xff\xc3"
#: 41 lines: one of bytes that are not UTF-8, then ``line 1`` … ``line 40``, ``line 33`` ending in such bytes too. The
#: last 30 are ``line 11`` … ``line 40``; ``line 10`` is the 31st from the end.
FORTY_LINES_AMID_BAD_BYTES = NOT_UTF8 + b"\n" + b"".join(f"line {number}".encode() + (b" " + NOT_UTF8 if number == 33 else b"") + b"\n" for number in range(1, 41))
#: An ANSI colour sequence: the runner colours its lines, the assertions read their text.
ANSI_SEQUENCE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def backend_output(*numbers: int) -> bytes:
    """What a backend printed: ``line N`` for each of ``numbers``, one per line."""
    return b"".join(f"line {number}\n".encode() for number in numbers)


def numbered_lines(text: str, word: str = "line") -> list[int]:
    """The ``N`` of each ``<word> N`` in ``text``, in order: which of the backend's numbered lines came out."""
    return [int(number) for number in re.findall(rf"\b{re.escape(word)} (\d+)\b", text)]


def plain(text: str) -> str:
    """``text`` without its ANSI colour sequences."""
    return ANSI_SEQUENCE.sub("", text)


def excerpt(text: str, size: int = 1500) -> str:
    """``text`` for a failure message: only its two ends when it is long (one case prints a line of 64 KiB)."""
    return text if len(text) <= 2 * size else f"{text[:size]} […] {text[-size:]}"


def shared_backend_log_path():
    """``_server.shared_backend_log_path()``, looked up at call time: before H-12 it does not exist."""
    function = getattr(test_runner_server, "shared_backend_log_path", None)
    assert callable(function), "H-12: shared_backend_log_path is missing"
    return function()


def log_tail(path: Path, **kwargs) -> list[str]:
    """``_server.log_tail(path, **kwargs)``, looked up at call time, its lines without their newline: before H-12 it does not exist."""
    function = getattr(test_runner_server, "log_tail", None)
    assert callable(function), "H-12: log_tail is missing"
    return [line.rstrip("\n") for line in function(path, **kwargs)]


def logging_server(**kwargs) -> test_runner_server.SharedTestServer:
    """``SharedTestServer(**kwargs)``, whose ``__init__`` takes H-12's ``log_path``: before H-12 it takes none."""
    assert "log_path" in inspect.signature(test_runner_server.SharedTestServer.__init__).parameters, "H-12: SharedTestServer has no log_path"
    return test_runner_server.SharedTestServer(**kwargs)


def exposed_log_path(server):
    """``server.log_path``, which ``start()`` sets in every mode: the file it wrote, None when it wrote none."""
    assert hasattr(server, "log_path"), "H-12: SharedTestServer exposes no log_path after start()"
    return server.log_path


@pytest.fixture
def run_log_dir(monkeypatch):
    """``_common``'s run log folder, what ``--log-dir`` prepared: None to begin with, set by the test, put back after.

    Only through monkeypatch, never ``set_log_dir()``: whatever the test does, the next one finds the folder this
    process had (None in this pytest process). A case that needs one sets a folder under ``tmp_path``.
    """
    monkeypatch.setattr(test_runner_common, "_LOG_DIR", None)

    def set_run_log_dir(path: Path | None) -> None:
        monkeypatch.setattr(test_runner_common, "_LOG_DIR", path)

    return set_run_log_dir


class LogWritingSpawn:
    """A fake ``Popen`` that writes ``output`` through the ``stdout`` it is given, then returns ``process``.

    Through the descriptor, as the backend does: the bytes land in the file whatever the runner's handle buffers, after
    whatever the runner left in it. ``calls`` holds each call's keywords; ``open_and_writable``, the runner's handle as
    the spawn received it.
    """

    def __init__(self, process, output: bytes = b""):
        self.process, self.output = process, output
        self.calls: list[dict] = []
        self.open_and_writable: list[bool] = []

    def __call__(self, *_args, **kwargs):
        self.calls.append(kwargs)
        stdout = kwargs.get("stdout")
        if hasattr(stdout, "fileno"):
            self.open_and_writable.append(not stdout.closed and stdout.writable())
        if self.output:
            assert hasattr(stdout, "fileno"), f"H-12: the backend's stdout is {stdout!r}, not the log file"
            assert os.write(stdout.fileno(), self.output) == len(self.output), "the fake backend's output was cut short"
        return self.process

    @property
    def stdout(self):
        """The ``stdout`` of the one spawn."""
        (kwargs,) = self.calls
        return kwargs.get("stdout")


class ExitedServerProcess:
    """The ``Popen`` of a backend that died during its startup: ``poll()`` answers its exit code at once."""

    pid, returncode = SERVER_PID, EXIT_CODE_DURING_STARTUP

    def poll(self):
        return self.returncode


class HandleWatchingProcess(FakeServerProcess):
    """A backend that stays up and notes, at each ``poll()``, whether the runner's handle on its log is closed by then."""

    def __init__(self):
        self.spawn: LogWritingSpawn | None = None
        self.handle_closed_at_poll: list = []

    def poll(self):
        self.handle_closed_at_poll.append(getattr(self.spawn.stdout, "closed", None))
        return None


class AdvancingClock(FakeClock):
    """A ``FakeClock`` whose ``sleep`` moves ``now`` instead of waiting: a startup deadline passes in no real time."""

    def sleep(self, seconds):
        self.now += seconds


def patch_logging_start(monkeypatch, spawn, *, healthy: bool = True, holders=(), clock=None) -> None:
    """``patch_start`` with a build step that succeeds and ``spawn`` as the backend; ``healthy=False``: it never answers."""
    patch_start(monkeypatch, holders=holders, build=lambda *_args, **_kwargs: True, spawn=spawn, clock=clock)
    if not healthy:
        monkeypatch.setattr(test_runner_server, "is_healthy", lambda *_args, **_kwargs: False)


def record_output_at_stop(monkeypatch, server, capsys) -> list[str]:
    """Replace ``server.stop`` with a recorder of what the runner had printed (stdout, then stderr) when it called it.

    One entry per call, colours removed. Whatever the runner prints after ``stop()`` stays in ``capsys``.
    """
    printed: list[str] = []

    def stop():
        out, err = capsys.readouterr()
        printed.append(plain(out + err))

    monkeypatch.setattr(server, "stop", stop)
    return printed


def printed_before_the_only_stop(printed_at_stop: list[str]) -> str:
    """What the runner had printed when it called ``stop()``, which a failed start calls once."""
    assert len(printed_at_stop) == 1, f"stop() ran {len(printed_at_stop)} times: a failed start stops its backend once"
    return printed_at_stop[0]


def assert_tail_printed(printed: str, failure_line: str, log_path: Path, expected: list[int], *, word: str = "line") -> None:
    """``failure_line`` in ``printed``, then a line naming ``log_path``, then exactly the backend lines ``expected``.

    Where a case checks that the tail comes before ``stop()``, ``printed`` is what came out before ``stop()`` ran.
    """
    assert failure_line in printed, f"today's error line {failure_line!r} did not come out: {excerpt(printed)!r}"
    named_at = printed.find(str(log_path), printed.index(failure_line))
    assert named_at >= 0, f"H-12: no line naming {log_path} after {failure_line!r}: {excerpt(printed)!r}"
    assert numbered_lines(printed[:named_at], word) == [], f"backend lines came out before the line naming the log: {excerpt(printed)!r}"
    assert numbered_lines(printed[named_at:], word) == expected, f"H-12: the tail brought back the backend's lines {numbered_lines(printed[named_at:], word)}, not {expected}"


@pytest.mark.usefixtures("run_log_dir")
class TestSharedBackendLog:
    """Outside ``--verbose``, the backend's stdout and stderr go to one log file, emptied by an instance's first ``start()``."""

    def test_the_backend_gets_the_log_file_as_stdout_and_its_stderr_merged_into_it(self, monkeypatch, tmp_path):
        # A file, never a pipe: a backend that writes a lot never blocks on a reader that has stopped reading.
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        server = logging_server(log_path=log_path)
        spawn = LogWritingSpawn(FakeServerProcess(), backend_output(1, 2))
        patch_logging_start(monkeypatch, spawn)
        forbid(monkeypatch, server, "stop", "a start that is healthy at its first poll must not be stopped")

        assert server.start() is True

        (kwargs,) = spawn.calls
        stdout = kwargs.get("stdout")
        assert isinstance(getattr(stdout, "name", None), (str, os.PathLike)), f"H-12: the backend's stdout is {stdout!r}, not a file"
        assert Path(stdout.name) == log_path
        assert spawn.open_and_writable == [True], "the runner's handle on the log was not open for writing when the backend got it"
        assert kwargs.get("stderr") == subprocess.STDOUT
        assert log_path.read_bytes() == backend_output(1, 2)
        assert exposed_log_path(server) == log_path

    def test_a_previous_log_is_emptied_before_the_backend_writes(self, monkeypatch, tmp_path):
        # An instance's first start writes the file afresh: a run's log holds that run's backend, never what a previous
        # run left (an earlier instance's leftovers: TestSharedBackendLogRestart).
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        log_path.write_bytes(b"a line of the previous run\n" * 100)
        server = logging_server(log_path=log_path)
        patch_logging_start(monkeypatch, LogWritingSpawn(FakeServerProcess(), backend_output(1)))
        forbid(monkeypatch, server, "stop", "a start that is healthy at its first poll must not be stopped")

        assert server.start() is True

        assert log_path.read_bytes() == backend_output(1)

    def test_a_missing_log_folder_is_created(self, monkeypatch, tmp_path):
        log_path = tmp_path / "not" / "there" / "yet" / SHARED_BACKEND_LOG_NAME
        server = logging_server(log_path=log_path)
        patch_logging_start(monkeypatch, LogWritingSpawn(FakeServerProcess(), backend_output(1)))
        forbid(monkeypatch, server, "stop", "a start that is healthy at its first poll must not be stopped")

        assert server.start() is True

        assert log_path.read_bytes() == backend_output(1)

    def test_the_runner_closes_its_handle_on_the_log_right_after_the_spawn(self, monkeypatch, tmp_path):
        # The backend keeps its own descriptor. Closed only by stop(), the runner's would stay open for the backend's
        # whole life; closed when start() returns, it would still be open while start() waits for the first answer.
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        server = logging_server(log_path=log_path)
        process = HandleWatchingProcess()
        spawn = process.spawn = LogWritingSpawn(process)
        patch_logging_start(monkeypatch, spawn)
        forbid(monkeypatch, server, "stop", "a start that is healthy at its first poll must not be stopped")

        assert server.start() is True

        assert spawn.open_and_writable == [True], "the runner's handle on the log was not open for writing when the backend got it"
        assert process.handle_closed_at_poll and all(closed is True for closed in process.handle_closed_at_poll), f"H-12: the runner's handle on the log was not closed when start() polled the backend: {process.handle_closed_at_poll}"

    def test_the_info_line_before_the_spawn_names_the_log(self, monkeypatch, tmp_path):
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        server = logging_server(log_path=log_path)
        events: list[tuple[str, str]] = []
        spawn = LogWritingSpawn(FakeServerProcess())
        patch_logging_start(monkeypatch, lambda *args, **kwargs: events.append(("spawn", "")) or spawn(*args, **kwargs))
        monkeypatch.setattr(test_runner_server, "print_info", lambda message: events.append(("info", plain(message))))
        forbid(monkeypatch, server, "stop", "a start that is healthy at its first poll must not be stopped")

        assert server.start() is True

        before_spawn = events[: events.index(("spawn", ""))]
        assert any(kind == "info" and str(log_path) in message for kind, message in before_spawn), f"H-12: no info line names {log_path} before the spawn: {events}"

    def test_without_a_log_path_the_log_is_shared_backend_log_in_the_run_log_dir_read_at_start(self, monkeypatch, tmp_path, run_log_dir):
        # The runner prepares --log-dir before it starts the backend: the live server's log lands beside the units'
        # logs. The folder is read by start(), not when the server is built: it is set here once the server exists.
        server = logging_server()
        run_log_dir(tmp_path / "run-logs")
        expected = tmp_path / "run-logs" / SHARED_BACKEND_LOG_NAME
        spawn = LogWritingSpawn(FakeServerProcess(), backend_output(1))
        patch_logging_start(monkeypatch, spawn)
        forbid(monkeypatch, server, "stop", "a start that is healthy at its first poll must not be stopped")

        assert shared_backend_log_path() == expected
        assert server.start() is True

        assert Path(getattr(spawn.stdout, "name", "<not a file>")) == expected
        assert expected.read_bytes() == backend_output(1)
        assert exposed_log_path(server) == expected

    def test_without_a_run_log_dir_the_output_stays_on_devnull_and_no_tail_comes_out(self, monkeypatch, tmp_path, capsys):
        # This pytest process has no run log folder, like every utilities run: a fallback to <root>/.testLog would
        # truncate the live server's log under all-backend. PROJECT_ROOT and the working directory point under
        # tmp_path, so a fallback through either would write where this test looks, never into the real tree.
        server = logging_server()
        project_root, cwd = tmp_path / "project", tmp_path / "cwd"
        for folder in (project_root, cwd):
            folder.mkdir()
        for module in (test_runner_server, test_runner_common):
            monkeypatch.setattr(module, "PROJECT_ROOT", project_root)
        monkeypatch.chdir(cwd)
        spawn = LogWritingSpawn(ExitedServerProcess())
        patch_logging_start(monkeypatch, spawn)
        printed_at_stop = record_output_at_stop(monkeypatch, server, capsys)

        assert shared_backend_log_path() is None
        assert server.start() is False

        (kwargs,) = spawn.calls
        assert (kwargs.get("stdout"), kwargs.get("stderr")) == (subprocess.DEVNULL, subprocess.DEVNULL)
        assert [path for path in tmp_path.rglob("*") if path.is_file()] == []
        assert exposed_log_path(server) is None
        lines = [line for line in printed_before_the_only_stop(printed_at_stop).splitlines() if line.strip()]
        assert lines and EXITED_LINE in lines[-1], f"H-12: something came out after today's error line with no log to show: {lines}"
        assert not any(SHARED_BACKEND_LOG_NAME in line for line in lines), f"H-12: a log was named with no run log folder: {lines}"
        assert plain("".join(capsys.readouterr())) == ""

    def test_verbose_leaves_the_output_on_the_terminal_and_writes_no_log(self, monkeypatch, tmp_path, run_log_dir):
        # As before H-12: --verbose shows the backend's output as it happens, a log_path and a run log folder given alike.
        run_log_dir(tmp_path / "run-logs")
        server = logging_server(verbose=True, log_path=tmp_path / "given" / SHARED_BACKEND_LOG_NAME)
        spawn = LogWritingSpawn(FakeServerProcess())
        patch_logging_start(monkeypatch, spawn)
        forbid(monkeypatch, server, "stop", "a start that is healthy at its first poll must not be stopped")

        assert server.start() is True

        (kwargs,) = spawn.calls
        assert (kwargs.get("stdout"), kwargs.get("stderr")) == (None, None)
        assert [path for path in tmp_path.rglob("*") if path.is_file()] == []
        assert exposed_log_path(server) is None


@pytest.mark.usefixtures("run_log_dir")
class TestSharedBackendLogTail:
    """A start that fails prints, after its error line and before ``stop()``, the log's path and its last 30 lines."""

    def test_an_exit_during_startup_prints_the_log_path_then_its_last_30_lines(self, monkeypatch, tmp_path, capsys):
        # FORTY_LINES_AMID_BAD_BYTES: the last 30 are line 11 … line 40, line 10 is the 31st. Its bytes that are not
        # UTF-8 cost a replacement character, never an exception: the line before line 1 trips a strict decoder of the
        # whole read, the end of line 33 one that decodes only the last lines.
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        server = logging_server(log_path=log_path)
        patch_logging_start(monkeypatch, LogWritingSpawn(ExitedServerProcess(), FORTY_LINES_AMID_BAD_BYTES))
        printed_at_stop = record_output_at_stop(monkeypatch, server, capsys)

        assert server.start() is False

        assert_tail_printed(printed_before_the_only_stop(printed_at_stop), EXITED_LINE, log_path, list(range(11, 41)))

    def test_a_startup_timeout_prints_the_log_path_then_its_last_30_lines(self, monkeypatch, tmp_path, capsys):
        # A backend that neither answers nor exits: the deadline passes on the fake clock, which each sleep moves on.
        monkeypatch.setattr(test_runner_server, "STARTUP_TIMEOUT", 1)
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        server = logging_server(log_path=log_path)
        patch_logging_start(monkeypatch, LogWritingSpawn(FakeServerProcess(), backend_output(*range(1, 36))), healthy=False, clock=AdvancingClock())
        printed_at_stop = record_output_at_stop(monkeypatch, server, capsys)

        assert server.start() is False

        assert_tail_printed(printed_before_the_only_stop(printed_at_stop), "Shared backend did not answer within 1s", log_path, list(range(6, 36)))

    def test_a_log_shorter_than_the_tail_comes_out_whole(self, monkeypatch, tmp_path, capsys):
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        server = logging_server(log_path=log_path)
        patch_logging_start(monkeypatch, LogWritingSpawn(ExitedServerProcess(), backend_output(1, 2, 3)))
        printed_at_stop = record_output_at_stop(monkeypatch, server, capsys)

        assert server.start() is False

        assert_tail_printed(printed_before_the_only_stop(printed_at_stop), EXITED_LINE, log_path, [1, 2, 3])

    def test_an_empty_log_prints_the_marker_instead_of_lines(self, monkeypatch, tmp_path, capsys):
        # A backend that died before printing anything: the marker says so, where an empty tail would say nothing.
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        server = logging_server(log_path=log_path)
        patch_logging_start(monkeypatch, LogWritingSpawn(ExitedServerProcess()))
        printed_at_stop = record_output_at_stop(monkeypatch, server, capsys)

        assert server.start() is False

        printed = printed_before_the_only_stop(printed_at_stop)
        assert_tail_printed(printed, EXITED_LINE, log_path, [])
        named_at = printed.index(str(log_path), printed.index(EXITED_LINE))
        assert EMPTY_LOG_MARKER in printed[named_at:], f"H-12: no {EMPTY_LOG_MARKER!r} after the line naming the empty log: {printed!r}"
        assert log_path.read_bytes() == b""

    def test_the_tail_reads_no_more_than_the_last_64_kib_of_the_log(self, monkeypatch, tmp_path, capsys):
        # line 1 … line 10, a line of 64 KiB, line 11 … line 20: 21 lines, all of them in the last 30 of a whole read.
        # From the last 64 KiB the long line comes cut, and is left out, and line 1 … line 10 are out of reach: a
        # runner that prints them read further back, as it would through a log that grew for the whole STARTUP_TIMEOUT.
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        output = backend_output(*range(1, 11)) + b"x" * TAIL_READ_LIMIT + b"\n" + backend_output(*range(11, 21))
        server = logging_server(log_path=log_path)
        patch_logging_start(monkeypatch, LogWritingSpawn(ExitedServerProcess(), output))
        printed_at_stop = record_output_at_stop(monkeypatch, server, capsys)

        assert server.start() is False

        assert_tail_printed(printed_before_the_only_stop(printed_at_stop), EXITED_LINE, log_path, list(range(11, 21)))

    def test_verbose_prints_no_tail_when_the_start_fails(self, monkeypatch, tmp_path, capsys, run_log_dir):
        # The backend's output is already on the terminal. A previous run's log sits at both paths a wrong runner could
        # read: it stays as it was, and none of it comes out.
        run_log_dir(tmp_path / "run-logs")
        previous_logs = (tmp_path / "given" / SHARED_BACKEND_LOG_NAME, tmp_path / "run-logs" / SHARED_BACKEND_LOG_NAME)
        for path in previous_logs:
            path.parent.mkdir()
            path.write_bytes(backend_output(1, 2, 3))
        server = logging_server(verbose=True, log_path=previous_logs[0])
        patch_logging_start(monkeypatch, LogWritingSpawn(ExitedServerProcess()))
        printed_at_stop = record_output_at_stop(monkeypatch, server, capsys)

        assert server.start() is False

        printed = printed_before_the_only_stop(printed_at_stop) + plain("".join(capsys.readouterr()))
        assert EXITED_LINE in printed
        assert (numbered_lines(printed), SHARED_BACKEND_LOG_NAME in printed, EMPTY_LOG_MARKER in printed) == ([], False, False), printed
        assert [path.read_bytes() for path in previous_logs] == [backend_output(1, 2, 3)] * 2
        assert exposed_log_path(server) is None

    def test_a_successful_start_prints_no_tail(self, monkeypatch, tmp_path, capsys):
        # The backend printed its startup lines and answered from a port it owns: today's lines come out, the path in
        # the info line, and nothing of the log.
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        server = logging_server(log_path=log_path)
        spawn = LogWritingSpawn(FakeServerProcess(), backend_output(1, 2, 3))
        patch_logging_start(monkeypatch, spawn, holders=lambda port=None: [str(SERVER_PID)] if spawn.calls else [])
        forbid(monkeypatch, server, "stop", "a start that is healthy at its first poll must not be stopped")

        assert server.start() is True

        printed = plain("".join(capsys.readouterr()))
        assert f"Shared backend ready on port {server.port}" in printed
        assert (numbered_lines(printed), printed.count(str(log_path)) <= 1, EMPTY_LOG_MARKER in printed) == ([], True, False), printed


class StoppableServerProcess(FakeServerProcess):
    """A backend that answers and stays up until the real ``stop()`` waits for it after its SIGTERM: ``wait()`` ends it."""

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.returncode = -int(test_runner_server.signal.SIGTERM)
        return self.returncode


def killpg_ending_the_fake_group(group, sig) -> None:
    """``os.killpg`` for the real ``stop()``: the fake backend's group takes the SIGTERM, then is gone at the next look."""
    assert group == SERVER_GROUP, f"a signal for process group {group}, which is not the fake backend's"
    if sig == 0:
        raise ProcessLookupError(group)


def patch_restarts(monkeypatch) -> None:
    """Fake what ``start()`` and the real ``stop()`` reach, for a server started more than once; each start brings its backend.

    ``stop()``'s SIGTERM reaches a fake that signals nothing, after which the group is gone; its wait ends the
    ``StoppableServerProcess``; the port is free. Nothing sleeps: ``patch_start``'s clock fails any sleep.
    """
    patch_start(monkeypatch, build=lambda *_args, **_kwargs: True)
    monkeypatch.setattr(test_runner_server.os, "killpg", killpg_ending_the_fake_group)


def spawning(monkeypatch, process, output: bytes = b"") -> LogWritingSpawn:
    """Make the next ``start()``'s backend ``process``, which writes ``output`` through the ``stdout`` it is given."""
    spawn = LogWritingSpawn(process, output)
    monkeypatch.setattr(test_runner_server.subprocess, "Popen", spawn)
    return spawn


def first_start_then_stop(monkeypatch, server, capsys, output: bytes) -> None:
    """A start of ``server`` whose backend writes ``output`` and answers, then the real ``stop()``; what they print is dropped."""
    spawning(monkeypatch, StoppableServerProcess(), output)
    assert server.start() is True
    server.stop()
    assert (server.proc, server.process_group_id, server.started_here) == (None, None, False), "the real stop() did not run to its end"
    capsys.readouterr()


@pytest.mark.usefixtures("run_log_dir")
class TestSharedBackendLogRestart:
    """A restart of the same server appends to its log, and its failure shows only the lines the restart wrote.

    ``database_file_owned_exclusively()`` (``db create``) stops the shared backend and starts the same instance again in
    the middle of a run: emptied by that start, the log would lose the first server's output. The real ``stop()`` runs
    between the starts, as there; only its signals and its wait are faked.
    """

    def test_a_restart_appends_and_its_failure_prints_only_its_own_lines(self, monkeypatch, tmp_path, capsys):
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        server = logging_server(log_path=log_path)
        patch_restarts(monkeypatch)
        first_start_then_stop(monkeypatch, server, capsys, b"first start\n")
        spawning(monkeypatch, ExitedServerProcess(), b"second 1\nsecond 2\nsecond 3\n")

        assert server.start() is False

        assert log_path.read_bytes() == b"first start\nsecond 1\nsecond 2\nsecond 3\n", "H-12: the restart did not append to the first start's log"
        printed = plain("".join(capsys.readouterr()))
        assert_tail_printed(printed, EXITED_LINE, log_path, [1, 2, 3], word="second")
        assert "first start" not in printed, f"H-12: the restart's tail brought back the first start's line: {printed!r}"

    def test_a_restart_that_wrote_nothing_prints_the_marker_not_the_earlier_lines(self, monkeypatch, tmp_path, capsys):
        # The file is not empty, the restart's share of it is: the marker, read from the size at the restart's open.
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        server = logging_server(log_path=log_path)
        patch_restarts(monkeypatch)
        first_start_then_stop(monkeypatch, server, capsys, b"first start\n")
        spawning(monkeypatch, ExitedServerProcess())

        assert server.start() is False

        assert log_path.read_bytes() == b"first start\n", "H-12: the restart did not keep the first start's log"
        printed = plain("".join(capsys.readouterr()))
        assert_tail_printed(printed, EXITED_LINE, log_path, [])
        named_at = printed.index(str(log_path), printed.index(EXITED_LINE))
        assert EMPTY_LOG_MARKER in printed[named_at:], f"H-12: no {EMPTY_LOG_MARKER!r} for a restart that wrote nothing: {printed!r}"
        assert "first start" not in printed, f"H-12: the restart's tail brought back the first start's line: {printed!r}"

    def test_a_new_server_empties_the_log_an_earlier_server_left(self, monkeypatch, tmp_path, capsys):
        # Appending is a restart's: another instance, as the next invocation's, starts the log afresh. A record of the
        # logs already opened kept beyond the instance (on the class, in the module) would append here.
        log_path = tmp_path / SHARED_BACKEND_LOG_NAME
        earlier, later = logging_server(log_path=log_path), logging_server(log_path=log_path)
        patch_restarts(monkeypatch)
        first_start_then_stop(monkeypatch, earlier, capsys, b"earlier server\n")
        spawning(monkeypatch, StoppableServerProcess(), b"later server\n")

        assert later.start() is True

        assert log_path.read_bytes() == b"later server\n"


class TestLogTail:
    """``log_tail()``: the last lines written after an offset, read from at most the file's last bytes, whole lines only."""

    def test_whole_lines_after_the_offset_from_at_most_the_last_max_bytes(self, tmp_path):
        # 76 bytes: old 1 and old 2 (12 bytes), an earlier start's, before the offset; then line 1 … line 9, 7 bytes each
        # but line 8, which ends in a byte that is not UTF-8. The last 33 bytes begin inside line 5, at "e 5": that piece
        # is left out. Read from the offset, nothing is cut: line 1 comes whole.
        earlier = b"old 1\nold 2\n"
        path = tmp_path / SHARED_BACKEND_LOG_NAME
        path.write_bytes(earlier + backend_output(*range(1, 8)) + b"line 8\xff\n" + backend_output(9))
        offset, size = len(earlier), path.stat().st_size
        this_start = [f"line {number}" for number in range(1, 8)] + ["line 8\ufffd", "line 9"]

        assert log_tail(path, offset=offset, lines=30, max_bytes=33) == this_start[5:]
        assert log_tail(path, offset=offset, lines=3, max_bytes=1000) == this_start[-3:]
        assert log_tail(path, offset=offset, lines=30, max_bytes=1000) == this_start
        assert log_tail(path, offset=0, lines=30, max_bytes=1000) == ["old 1", "old 2", *this_start]
        assert log_tail(path, offset=size, lines=30, max_bytes=1000) == []


# ── Contract 7, end to end — a real child's stderr reaches the log through the real spawn ──

#: The real child of the case below: what it writes to its stderr, how it exits, and the command that does both.
CHILD_FAILURE = "boom: the configuration cannot be read"
CHILD_EXIT_CODE = 3
CHILD_COMMAND = (sys.executable, "-c", f"import sys; print({CHILD_FAILURE!r}, file=sys.stderr); sys.exit({CHILD_EXIT_CODE})")
#: A bound, not a wait: the child is gone in well under a second; one that hung would fail the case in a minute, not five.
REAL_CHILD_STARTUP_BOUND = 60
#: The real ``Popen`` and ``os.killpg``, taken at import, before ``no_real_process`` forbids them: only the guards below call them.
REAL_POPEN, REAL_KILLPG = subprocess.Popen, os.killpg


def allow_one_real_child(monkeypatch, argv: list[str]) -> list:
    """Let ``_server`` start ``argv`` for real, once, and signal only that child's process group; nothing else may start.

    ``start_new_session=True`` makes the child the leader of a new group whose id is its PID, and ``os.getpgid`` is
    pinned to that answer. The real call gives the same while the child lives, but a one-line child can be gone before
    the runner's next line, and macOS does not report a zombie's group: a ``ProcessLookupError`` that would be this
    test's race (the real backend takes seconds to start), not the contract's.
    """
    children: list = []

    def popen(command, *args, **kwargs):
        assert list(command) == argv, f"only this test's own child may start for real, not {command}"
        assert not children, "this test's child was started twice"
        children.append(REAL_POPEN(command, *args, **kwargs))
        return children[-1]

    def killpg(group, sig):
        assert children and group == children[0].pid, f"a signal for process group {group}, which is not this test's child"
        REAL_KILLPG(group, sig)

    monkeypatch.setattr(test_runner_server.subprocess, "Popen", popen)
    monkeypatch.setattr(test_runner_server.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(test_runner_server.os, "killpg", killpg)
    return children


@pytest.mark.usefixtures("run_log_dir")
class TestSharedBackendLogWithARealChild:
    """The one case of this file with a real process: the child's stderr reaches the log through the real spawn.

    Outside this file's every-seam-faked rule, on purpose and alone. The child is a one-line Python started through the
    real ``scripts/exec_unmasked.py``, never the backend and never a build: ``_command()`` is replaced and the ``Popen``
    guard refuses any other argv. Still ``pure`` for the catalogue: no server, no database, no network, no port; the log
    lives under ``tmp_path``; the real ``stop()`` signals no group but the child's. Only the build step, lsof and health
    are faked, and the PGID lookup (see ``allow_one_real_child``).
    """

    def test_a_real_child_s_stderr_reaches_the_log_and_comes_back_in_the_tail(self, monkeypatch, tmp_path, capsys):
        log_path = tmp_path / "logs" / SHARED_BACKEND_LOG_NAME
        server = logging_server(log_path=log_path)
        monkeypatch.setattr(server, "_command", lambda: list(CHILD_COMMAND))
        monkeypatch.setattr(test_runner_server, "build_server_prerequisites", lambda *_args, **_kwargs: True)
        monkeypatch.setattr(test_runner_server, "port_holders", lambda port=None: [])
        monkeypatch.setattr(test_runner_server, "is_healthy", lambda *_args, **_kwargs: False)
        monkeypatch.setattr(test_runner_server, "STARTUP_TIMEOUT", REAL_CHILD_STARTUP_BOUND)
        children = allow_one_real_child(monkeypatch, [sys.executable, str(test_runner_server.UNMASKED_EXEC), *CHILD_COMMAND])

        assert server.start() is False

        (child,) = children
        assert child.returncode == CHILD_EXIT_CODE
        assert (server.proc, server.process_group_id, server.started_here) == (None, None, False), "the real stop() did not run"
        assert CHILD_FAILURE in log_path.read_text(encoding="utf-8", errors="replace"), "the child's stderr did not reach the log"
        printed = plain("".join(capsys.readouterr()))
        failure_line = f"Shared backend exited during startup (code {CHILD_EXIT_CODE})"
        assert failure_line in printed, printed
        named_at = printed.find(str(log_path), printed.index(failure_line))
        assert named_at >= 0, f"H-12: no line naming {log_path} after {failure_line!r}: {printed!r}"
        assert CHILD_FAILURE in printed[named_at:], f"H-12: the tail does not bring back the child's stderr: {printed!r}"


# ── Contract 8 — `cmd_fe_build` records the listing of the Tool codegen inputs it built from (H-24r) ──
#
# `check_frontend_needs_build()` compares the Tool codegen inputs' listing with the one the last successful build
# recorded in `frontend/build/.tool-contract-inputs` (`scripts/cli_base.py`): a folder's mtime cannot tell a `.DS_Store`
# the Finder dropped from a `.py` that was removed. The build takes the listing's fingerprint right before `cmd_api_sync`
# generates the codecs from those inputs — a file added while the build runs is not in it, so the next check still finds
# the build stale — and records it only once the npm build answered 0: after a missing tool, a failed step or a failed
# build nothing is recorded. Every step is stubbed, and the two names are replaced only after a barrier proves dev.py
# imports them: nothing here ever runs a real step, nor writes into the real `frontend/build/`.

#: What the stub fingerprint answers: recognisable wherever it travels.
TOOL_INPUTS_SENTINEL = "sentinel-fingerprint-of-the-tool-codegen-inputs"
#: The two names dev.py imports from ``scripts.cli_base`` to record the listing.
TOOL_CONTRACT_RECORDING = ("tool_contract_fingerprint", "record_tool_contract_inputs")
#: The npm build ``cmd_fe_build`` runs, by its ``debug`` flag; svelte-check runs before it, its result ignored.
NPM_BUILD_COMMANDS = {True: ["npm", "run", "build:debug"], False: ["npm", "run", "build"]}


def require_tool_contract_recording() -> None:
    """The barrier: a dev.py without the two names fails the test here, before anything is replaced or run."""
    for name in TOOL_CONTRACT_RECORDING:
        if not hasattr(dev, name):
            pytest.fail(f"H-24r: dev.py does not import {name}")


def stub_fe_build_steps(monkeypatch, *, failing: str | None = None) -> SimpleNamespace:
    """Replace every step of ``cmd_fe_build`` with a recording stub, after the barrier; the step named ``failing`` returns 1.

    ``events`` holds each step's name in the order it ran (svelte-check as ``"svelte-check"``, the npm build as
    ``"npm build"``), ``fingerprinted`` the root of each fingerprint taken, ``recorded`` the arguments of each record.
    Any other command fails the test, and so does a call that reached cli_base's own two functions around dev.py's
    imports.
    """
    require_tool_contract_recording()
    calls = SimpleNamespace(events=[], fingerprinted=[], recorded=[])

    def step(name: str, result=0):
        def run(*_args, **_kwargs):
            calls.events.append(name)
            return 1 if name == failing else result

        return run

    def tool_contract_fingerprint(project_root):
        calls.events.append("tool_contract_fingerprint")
        calls.fingerprinted.append(project_root)
        return TOOL_INPUTS_SENTINEL

    def record_tool_contract_inputs(project_root, fingerprint):
        calls.events.append("record_tool_contract_inputs")
        calls.recorded.append((project_root, fingerprint))

    def run_command_live(command, *_args, **_kwargs):
        if list(command[:2]) == ["npx", "svelte-check"]:
            return step("svelte-check")()
        if list(command) in NPM_BUILD_COMMANDS.values():
            return step("npm build")()
        pytest.fail(f"cmd_fe_build ran a command this test does not expect: {command}")

    for name in TOOL_CONTRACT_RECORDING:
        forbid(monkeypatch, cli_base, name, f"cmd_fe_build reached cli_base.{name} around dev.py's import of it", raising=False)
    for name in ("require_frontend_dependencies", "update_js_cache", "cmd_api_sync", "generate_favicon", "stamp_service_worker", "_write_frontend_build_mode_marker"):
        monkeypatch.setattr(dev, name, step(name))
    monkeypatch.setattr(dev.i18n_catalog, "build", step("i18n_catalog.build"))
    monkeypatch.setattr(dev, "run_command_live", run_command_live)
    monkeypatch.setattr(dev, "tool_contract_fingerprint", tool_contract_fingerprint)
    monkeypatch.setattr(dev, "record_tool_contract_inputs", record_tool_contract_inputs)
    return calls


class TestFrontendBuildRecordsTheToolContractInputs:
    """``cmd_fe_build`` fingerprints the Tool codegen inputs before the API sync, and records it after a successful build only."""

    def test_dev_records_with_the_functions_the_staleness_check_compares_with(self):
        # One fingerprint on both sides: the check computes the current listing's with cli_base's function, so a function
        # of dev.py's own could record a value the check never matches, and every build would look stale.
        require_tool_contract_recording()

        for name in TOOL_CONTRACT_RECORDING:
            assert getattr(dev, name) is getattr(cli_base, name, None), f"H-24r: dev.{name} is not scripts.cli_base.{name}"

    @pytest.mark.parametrize("debug", [True, False], ids=["debug-build", "production-build"])
    def test_the_fingerprint_is_taken_before_the_api_sync_and_recorded_after_the_build(self, monkeypatch, debug):
        calls = stub_fe_build_steps(monkeypatch)

        assert dev.cmd_fe_build(SimpleNamespace(debug=debug)) == 0

        # Once, after the checks that may stop the build, right before cmd_api_sync generates the codecs.
        assert calls.events[:4] == ["require_frontend_dependencies", "update_js_cache", "tool_contract_fingerprint", "cmd_api_sync"]
        assert calls.fingerprinted == [dev.PROJECT_ROOT]
        # Once, that very fingerprint, after the npm build answered 0.
        assert calls.recorded == [(dev.PROJECT_ROOT, TOOL_INPUTS_SENTINEL)]
        assert calls.events.index("record_tool_contract_inputs") > calls.events.index("npm build")

    @pytest.mark.parametrize("failing", ["update_js_cache", "cmd_api_sync", "i18n_catalog.build", "npm build"])
    def test_a_failed_step_or_build_records_nothing(self, monkeypatch, failing):
        calls = stub_fe_build_steps(monkeypatch, failing=failing)
        record_errors(monkeypatch, dev)

        assert dev.cmd_fe_build(SimpleNamespace(debug=True)) == 1

        assert failing in calls.events, f"premise: {failing} ran, and failed"
        assert calls.recorded == [], f"H-24r: the listing was recorded though {failing} failed: only a successful build may record it"

    def test_a_missing_frontend_tool_takes_no_fingerprint_and_records_nothing(self, monkeypatch, tmp_path):
        # The real node_modules check, on a tree without node_modules: the build stops before every step, the
        # fingerprint and the record included.
        require_tool_contract_recording()
        frontend_node_bin(monkeypatch, tmp_path, installed=False)
        recording_steps = [(dev, name) for name in (*TOOL_CONTRACT_RECORDING, "_write_frontend_build_mode_marker")]
        forbid_steps(monkeypatch, (*FE_BUILD_STEPS, *recording_steps), "cmd_fe_build went past a failed node_modules check")
        record_errors(monkeypatch, dev)

        assert dev.cmd_fe_build(SimpleNamespace(debug=True)) == 1
