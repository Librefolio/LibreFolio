"""``dev.py`` lists the Designer Lab among the server's endpoints only when the frontend build carries it (L, R2).

The request: when ``./dev.py server`` starts, show the Designer Lab's address beside the API pages, but only when the
Lab was compiled in, which in practice means a debug build. ``frontend/scripts/designer-lab/vite-plugin.mjs``
(``designerLabEnabled``) compiles it into debug builds and ``vite dev`` unless ``LF_DESIGNER_LAB=0``, and into any build
with ``LF_DESIGNER_LAB=1``. The build mode file ``frontend/build/.build-debug`` therefore cannot tell: a debug build made
with ``LF_DESIGNER_LAB=0`` has no Lab, a production build made with ``LF_DESIGNER_LAB=1`` has one. The Lab's marker can:
every Lab runtime module holds ``LAB_MARKER`` (``'lf-designer-lab'``), and the plugin fails a build without the Lab when
any file it emits holds it.

The contracts held here:

* ``_frontend_build_has_designer_lab(build_dir)`` is True when a ``*.js`` file under ``build_dir/_app/immutable/``, at
  any depth, holds ``DESIGNER_LAB_MARKER``, also inside a longer string (``'lf-designer-lab/v1'``); False without a
  build, without ``_app/``, when no such script holds it, and when the listing fails; a script it cannot read is skipped
  and the scan goes on. Only those scripts count: source maps, CSS, HTML, SvelteKit's ``_app/env.js`` and the files
  copied from ``static/`` (``sw.js``, ``offline.html``) are not guarded by the plugin. By default it reads
  ``frontend/build/``, the folder the server serves.
* ``DESIGNER_LAB_MARKER`` is the ``LAB_MARKER`` the Vite plugin exports.
* ``cmd_server`` prints `` ├── 🎨 Designer Lab: http://localhost:<port>/designer-lab`` right after the Frontend line of
  «Available endpoints» when the build it is about to serve (after its auto-build) carries the Lab, and no such line
  otherwise; the other endpoint lines stay as they were; a build it cannot read never stops the start; ``--build-only``
  prints no endpoint list and never asks.
* ``cmd_fe_dev`` (``./dev.py front dev``, Vite on 5173) prints ``🎨 Designer Lab: http://localhost:5173/designer-lab``
  right after its URL unless ``LF_DESIGNER_LAB`` is exactly ``"0"``, the only value that turns the Lab off under
  ``vite dev`` in ``designerLabEnabled``; then it launches ``npm run dev`` and returns its result.

The server cases run ``cmd_server`` in this process on a fake project under ``tmp_path``, the real helper bound to a
fake build with ``functools.partial`` (its default ``build_dir`` is bound when ``dev.py`` is imported). What surrounds the
banner is stood in for: the runtime configuration (it writes ``os.environ``), the database path, the data directory, the
host, the builds, the port check and the uvicorn launch (``run_server_live``, formerly ``run_command_live``), whose
recorder shows the start reached it. Read errors are injected by patching ``pathlib.Path.rglob`` or
``pathlib.Path.read_bytes`` for one path only: a ``chmod 000`` would not stop a root user, as on a CI container.

PURE: no DB, no server, no network, nothing written outside ``tmp_path``. An autouse fixture forbids every real process,
exec and signal, and ``os.environ`` is compared before and after each ``cmd_server`` call. The only repository file read
is ``frontend/scripts/designer-lab/vite-plugin.mjs``: the real ``frontend/build/`` is neither read nor written.
"""

import argparse
import errno
import functools
import inspect
import json
import os
import pathlib
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

import dev

PROJECT_ROOT = Path(__file__).resolve().parents[3]
#: The Vite plugin that compiles the Lab in or out, and fails a build without the Lab when an emitted file holds LAB_MARKER.
VITE_PLUGIN = PROJECT_ROOT / "frontend" / "scripts" / "designer-lab" / "vite-plugin.mjs"
#: ``export const LAB_MARKER = '…';`` in the Vite plugin, whatever the quotes and the spacing.
LAB_MARKER_EXPORT = re.compile(r"""^\s*export\s+const\s+LAB_MARKER\s*=\s*(['"`])(?P<marker>.*?)\1\s*;?\s*$""", re.MULTILINE)

#: The real helper, listing and read, taken at import, before any test patches them.
REAL_HELPER = dev._frontend_build_has_designer_lab
REAL_RGLOB = pathlib.Path.rglob
REAL_READ_BYTES = pathlib.Path.read_bytes

#: What the fake builds write: the marker dev.py looks for (the parity test pins it to the Vite plugin's LAB_MARKER), and
#: the name of dev.py's build mode file, "1" after a debug build and "0" after a production one.
MARKER = dev.DESIGNER_LAB_MARKER.decode()
MODE_FILE = dev.FRONTEND_BUILD_MODE_MARKER.name

#: A script without any trace of the Lab.
PLAIN_JS = "export const answer = 42;\n"
#: A Lab module holding the bare marker (the id of the Lab's style element).
BARE_LAB_JS = f"const STYLE_ID = '{MARKER}';\nexport {{ STYLE_ID }};\n"
#: A Lab module holding the marker only inside a longer string, as the Lab's storage keys write it.
STORAGE_KEY_LAB_JS = f"const STORAGE_KEY = '{MARKER}/v1';\nexport {{ STORAGE_KEY }};\n"

#: A production build (``./dev.py front build``): the mode file at 0, scripts under _app/immutable/ without the marker, a
#: CSS asset, SvelteKit's _app/env.js and version.json, the pages, and the files copied from static/.
RELEASE_BUILD = {
    MODE_FILE: "0",
    "index.html": "<!doctype html><title>LibreFolio</title>\n",
    "200.html": "<!doctype html><title>LibreFolio</title>\n",
    "sw.js": "self.addEventListener('fetch', () => {});\n",
    "offline.html": "<!doctype html><title>LibreFolio offline</title>\n",
    "_app/env.js": "export const env = {};\n",
    "_app/version.json": '{"version": "1"}\n',
    "_app/immutable/entry/start.B1a2c3d4.js": PLAIN_JS,
    "_app/immutable/chunks/C5e6f7g8.js": PLAIN_JS,
    "_app/immutable/nodes/0.D9h0i1j2.js": PLAIN_JS,
    "_app/immutable/assets/0.E3k4l5m6.css": "body { margin: 0; }\n",
}
#: A debug build made with ``LF_DESIGNER_LAB=0``: the mode file at 1, source maps beside the scripts, no script with the
#: marker.
DEBUG_BUILD_WITHOUT_LAB = {
    **RELEASE_BUILD,
    MODE_FILE: "1",
    "_app/immutable/entry/start.B1a2c3d4.js.map": json.dumps({"version": 3, "sourcesContent": [PLAIN_JS]}),
    "_app/immutable/chunks/C5e6f7g8.js.map": json.dumps({"version": 3, "sourcesContent": [PLAIN_JS]}),
    "_app/immutable/nodes/0.D9h0i1j2.js.map": json.dumps({"version": 3, "sourcesContent": [PLAIN_JS]}),
}
#: Where the Lab's module lands in a build that carries it.
LAB_CHUNK = "_app/immutable/chunks/F7n8o9p0.js"
#: A debug build with the Lab (``./dev.py front build --debug``): the mode file at 1, the Lab's chunk and its source map.
DEBUG_BUILD_WITH_LAB = {
    **DEBUG_BUILD_WITHOUT_LAB,
    LAB_CHUNK: STORAGE_KEY_LAB_JS,
    f"{LAB_CHUNK}.map": json.dumps({"version": 3, "sourcesContent": [STORAGE_KEY_LAB_JS]}),
}
#: A production build made with ``LF_DESIGNER_LAB=1``: the mode file at 0, yet the Lab's chunk.
PRODUCTION_BUILD_WITH_LAB = {**RELEASE_BUILD, LAB_CHUNK: STORAGE_KEY_LAB_JS}

#: ANSI colour codes, stripped from what the commands print.
ANSI = re.compile(r"\x1b\[[0-9;]*m")
#: Any mention of the Lab, however written.
LAB_MENTION = re.compile(r"designer[ -]lab", re.IGNORECASE)

#: The port of the server cases. Never bound (the port check and the launch are stood in for), and neither 6040 nor 6041,
#: so a URL carrying it comes from this run.
PORT = 6999
#: The line cmd_server adds for the Lab.
SERVER_LAB_LINE = f"🎨 Designer Lab: http://localhost:{PORT}/designer-lab"
#: The endpoint lines cmd_server printed before the Lab line existed, in their order, each found by label and URL whatever
#: the padding after the colon.
OTHER_ENDPOINTS = {
    "Frontend": f"http://localhost:{PORT}/",
    "API Redoc": f"http://localhost:{PORT}/api/v1/redoc",
    "API Docs": f"http://localhost:{PORT}/api/v1/docs",
    "User Doc": f"http://localhost:{PORT}/mkdocs/",
}
#: The database path the stood-in configuration gives. Only printed.
FAKE_DATABASE = "fake-lane/sqlite/app.db"

#: What cmd_fe_dev prints: Vite's URL, and the Lab line that follows it.
FRONT_DEV_URL_LINE = "URL: http://localhost:5173"
FRONT_DEV_LAB_LINE = "🎨 Designer Lab: http://localhost:5173/designer-lab"


# ---------------------------------------------------------------------------
# Fakes, stand-ins and probes
# ---------------------------------------------------------------------------


def write_build(build: Path, files: dict[str, str]) -> Path:
    """Write ``files`` (path relative to the build: text) under ``build``, and return ``build``."""
    for relative, text in files.items():
        path = build / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return build


def fake_build(tmp_path: Path, files: dict[str, str]) -> Path:
    """``frontend/build`` of a fake project rooted at ``tmp_path``, holding ``files``."""
    return write_build(tmp_path / "frontend" / "build", files)


def recorded_build_mode(monkeypatch, build: Path) -> bool | None:
    """What dev.py's own reader of the build mode file says about ``build``: True debug, False production, None unknown."""
    monkeypatch.setattr(dev, "FRONTEND_BUILD_MODE_MARKER", build / MODE_FILE)
    return dev._read_frontend_build_mode_marker()


def forbid(monkeypatch, target, name: str) -> None:
    """Make ``target.name`` fail the test if the code under test ever reaches it."""

    def refuse(*_args, **_kwargs):
        pytest.fail(f"{target.__name__}.{name} was reached: nothing may start, build, exec or be signalled here")

    monkeypatch.setattr(target, name, refuse)


@pytest.fixture(autouse=True)
def no_real_process(monkeypatch):
    """No test here may start, exec or signal a real process: uvicorn, ``npm run dev`` or a kill would escape the test."""
    for name in ("run", "Popen"):
        forbid(monkeypatch, subprocess, name)
    for name in ("execvpe", "kill", "killpg"):
        forbid(monkeypatch, os, name)


class _LaunchResult:
    """What the stood-in launchers (``run_server_live``, ``run_command_live``) return: a caller returning it reached its launch and handed the result back."""

    def __repr__(self) -> str:
        return "<the stood-in launch's result>"


LAUNCH_RESULT = _LaunchResult()


@dataclass
class Launch:
    """One launch (``run_server_live`` or ``run_command_live``): the command that would have started, and where. Its ``env`` is never printed."""

    cmd: list[str]
    cwd: Path | None
    env: dict[str, str] | None


def record_launches(monkeypatch, steps: list[str] | None = None) -> list[Launch]:
    """Stand in for ``dev.run_server_live`` and ``dev.run_command_live``: record each call (and a ``launch`` step), start nothing, return ``LAUNCH_RESULT``.

    The server launches through ``run_server_live`` (Z-10; formerly ``run_command_live``), which takes no ``cwd``: it
    always starts the server in the project root, recorded as None. ``front dev`` launches through ``run_command_live``.
    ``run_server_live`` is set with ``raising=False``, so the stand-in holds before and after dev.py defines it.
    """
    launches: list[Launch] = []

    def run_command_live(cmd, cwd=None, env=None):
        launches.append(Launch(cmd=list(cmd), cwd=cwd, env=env))
        if steps is not None:
            steps.append("launch")
        return LAUNCH_RESULT

    def run_server_live(cmd, env=None, grace_seconds=None):
        launches.append(Launch(cmd=list(cmd), cwd=None, env=env))
        if steps is not None:
            steps.append("launch")
        return LAUNCH_RESULT

    monkeypatch.setattr(dev, "run_command_live", run_command_live)
    monkeypatch.setattr(dev, "run_server_live", run_server_live, raising=False)
    return launches


def yield_then_raise(paths: list[Path], error: OSError):
    """A listing that yields ``paths`` and then fails with ``error``, as a folder that turns unreadable mid-walk."""
    yield from paths
    raise error


def fail_listing(monkeypatch, listed: Path, *, after: list[Path] | None = None) -> list[Path]:
    """Make ``listed.rglob(...)`` raise ``OSError`` (EIO): at the call, or, given ``after``, once those paths are yielded.

    Every other listing is real. Returns the failed listings, so a test can prove its error was reached.
    """
    failed: list[Path] = []

    def rglob(self, pattern, *args, **kwargs):
        if self != listed:
            return REAL_RGLOB(self, pattern, *args, **kwargs)
        failed.append(self)
        error = OSError(errno.EIO, os.strerror(errno.EIO), str(self))
        if after is None:
            raise error
        return yield_then_raise(after, error)

    monkeypatch.setattr(pathlib.Path, "rglob", rglob)
    return failed


def refuse_reading(monkeypatch, refused: Path) -> list[Path]:
    """Make ``refused.read_bytes()`` raise ``PermissionError`` (EACCES), as a file without read permission does.

    Every other read is real. Returns the refused reads, so a test can prove its error was reached.
    """
    attempts: list[Path] = []

    def read_bytes(self):
        if self != refused:
            return REAL_READ_BYTES(self)
        attempts.append(self)
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(self))

    monkeypatch.setattr(pathlib.Path, "read_bytes", read_bytes)
    return attempts


@dataclass
class ServerStart:
    """One ``cmd_server`` call on the fake project.

    Its result, its output (ANSI codes stripped), the stood-in steps it went through in order, and what it would have
    launched.
    """

    returned: object
    lines: list[str]
    steps: list[str]
    launches: list[Launch]


def start_server(monkeypatch, capsys, tmp_path: Path, lab_check: Callable[[], bool], *, frontend_build: Callable[[bool], object] | None = None, **options) -> ServerStart:
    """Run ``dev.cmd_server`` on a fake project rooted at ``tmp_path``, ``lab_check`` answering for the Designer Lab.

    The arguments are a ``Namespace`` with ``port=PORT`` and ``options``. Stood in for, each recording a step: the
    frontend auto-build (``frontend_build(debug)`` runs in its place when given; ``cmd_fe_build``, reached only under
    ``--rebuild``, fails the test), the documentation build, the JS cache, the port check (nothing holds the port), the
    Lab check (it calls ``lab_check``) and the launch (``run_server_live``, formerly ``run_command_live``). The runtime
    configuration, which writes ``os.environ``, the database path, the data directory and the host are fixed, and
    ``dev.PROJECT_ROOT`` is ``tmp_path``, so the «Frontend build found» check reads the fake project too. Fails the test
    when the call changed ``os.environ``.
    """
    steps: list[str] = []
    launches = record_launches(monkeypatch, steps)

    def recorded(name: str, result=None):
        def step(*_args, **_kwargs):
            steps.append(name)
            return result

        return step

    def configure_runtime(port=None, data_dir=None):
        return port, tmp_path / "data"

    def auto_build_frontend(debug=False):
        steps.append("frontend-build")
        return None if frontend_build is None else frontend_build(debug)

    def frontend_build_has_designer_lab(*args, **kwargs):
        steps.append("lab-check")
        return lab_check(*args, **kwargs)

    monkeypatch.setattr(dev, "PROJECT_ROOT", tmp_path)
    for name in ("configure_server_runtime", "configure_test_runtime"):
        monkeypatch.setattr(dev, name, configure_runtime)
    monkeypatch.setattr(dev, "get_database_path", lambda test_mode=False: FAKE_DATABASE)
    monkeypatch.setattr(dev, "get_data_dir", lambda test_mode=False: tmp_path / "data")
    monkeypatch.setattr(dev, "get_server_host", lambda: "127.0.0.1")
    monkeypatch.setattr(dev, "auto_build_frontend", auto_build_frontend)
    forbid(monkeypatch, dev, "cmd_fe_build")
    monkeypatch.setattr(dev, "auto_build_mkdocs", recorded("docs-build"))
    monkeypatch.setattr(dev, "update_js_cache", recorded("js-cache"))
    monkeypatch.setattr(dev, "check_port_in_use", recorded("port-check", []))
    monkeypatch.setattr(dev, "_frontend_build_has_designer_lab", frontend_build_has_designer_lab)

    capsys.readouterr()
    environ_before = dict(os.environ)
    returned = dev.cmd_server(argparse.Namespace(port=PORT, **options))
    printed = capsys.readouterr().out
    changed = sorted(key for key in environ_before.keys() | os.environ.keys() if environ_before.get(key) != os.environ.get(key))
    assert not changed, f"cmd_server changed os.environ, which none of its stand-ins writes (names only): {changed}"
    return ServerStart(returned=returned, lines=ANSI.sub("", printed).splitlines(), steps=steps, launches=launches)


def only_line(lines: list[str], pattern: re.Pattern[str], what: str) -> int:
    """The index of the one line matching ``pattern``; fails naming ``what`` when there is none, or several."""
    hits = [index for index, line in enumerate(lines) if pattern.search(line)]
    assert len(hits) == 1, f"expected exactly one {what} line, found {len(hits)} in:\n" + "\n".join(lines)
    return hits[0]


def assert_endpoints(start: ServerStart, *, lab_listed: bool) -> None:
    """«Available endpoints:», Frontend, the Lab line when ``lab_listed``, API Redoc, API Docs, User Doc.

    One per line, in this order, nothing between them; the Lab mentioned nowhere else; the helper asked exactly once,
    after the frontend build, so about the build the server is going to serve.
    """
    lines = start.lines
    shown = "\n".join(lines)
    header = only_line(lines, re.compile(r"^Available endpoints:\s*$"), "«Available endpoints:»")
    endpoints = {label: only_line(lines, re.compile(rf"{re.escape(label)}:\s+{re.escape(url)}\s*$"), f"{label} ({url})") for label, url in OTHER_ENDPOINTS.items()}
    mentions = [index for index, line in enumerate(lines) if LAB_MENTION.search(line)]
    if lab_listed:
        assert len(mentions) == 1 and SERVER_LAB_LINE in lines[mentions[0]], f"the build carries the Lab: cmd_server must print one line with {SERVER_LAB_LINE!r} and mention the Lab nowhere else; it printed:\n{shown}"
        order = [header, endpoints["Frontend"], mentions[0], endpoints["API Redoc"], endpoints["API Docs"], endpoints["User Doc"]]
    else:
        assert not mentions, f"the build does not carry the Lab: cmd_server must not mention it; it printed:\n{shown}"
        order = [header, *endpoints.values()]
    listed = "Frontend, Designer Lab, API Redoc" if lab_listed else "Frontend, API Redoc"
    assert order == list(range(header, header + len(order))), f"«Available endpoints:» must be followed by {listed}, API Docs and User Doc, one per line in this order; it printed:\n{shown}"
    asked = start.steps.count("lab-check") == 1 and "frontend-build" in start.steps and start.steps.index("lab-check") > start.steps.index("frontend-build")
    assert asked, f"cmd_server must ask about the Lab once, after the frontend build it is going to serve: steps {start.steps}"


def assert_launched(start: ServerStart) -> None:
    """The start went on to the uvicorn launch, on PORT and as its last step, and cmd_server returned the launch's result."""
    commands = [launch.cmd for launch in start.launches]
    assert len(commands) == 1 and "backend.app.main:app" in commands[0], f"cmd_server must reach the uvicorn launch exactly once: {commands}"
    command = commands[0]
    assert "--port" in command and command[command.index("--port") + 1] == str(PORT), f"uvicorn must be launched on {PORT}, the port the endpoints name: {command}"
    assert start.steps[-1] == "launch", f"the launch must be cmd_server's last step: {start.steps}"
    assert start.returned is LAUNCH_RESULT, f"cmd_server must return the launch's result, not {start.returned!r}"


def immutable_scripts(build: Path) -> list[Path]:
    """The scripts the helper reads: ``*.js`` under ``_app/immutable/``, at any depth."""
    return sorted((build / "_app" / "immutable").rglob("*.js"))


# ---------------------------------------------------------------------------
# The helper on fake builds
# ---------------------------------------------------------------------------


def test_helper_without_a_build_folder_finds_no_lab(tmp_path):
    """No ``frontend/build`` at all: False, and no error."""
    build = tmp_path / "frontend" / "build"

    assert REAL_HELPER(build) is False


def test_helper_on_a_build_without_app_folder_finds_no_lab(tmp_path):
    """A build holding ``index.html`` but no ``_app/``: nothing to read, False."""
    build = fake_build(tmp_path, {"index.html": RELEASE_BUILD["index.html"]})

    assert REAL_HELPER(build) is False


def test_helper_on_scripts_without_the_marker_finds_no_lab(tmp_path):
    """Scripts in ``_app/immutable/chunks/``, ``nodes/`` and ``entry/``, none holding the marker: False."""
    build = fake_build(tmp_path, RELEASE_BUILD)
    assert len(immutable_scripts(build)) == 3, "premise: the helper has three scripts to read"

    assert REAL_HELPER(build) is False


def test_helper_finds_the_marker_in_a_chunk(tmp_path):
    """The bare marker in ``_app/immutable/chunks/<name>.js``, among scripts without it: True."""
    build = fake_build(tmp_path, {**RELEASE_BUILD, LAB_CHUNK: BARE_LAB_JS})

    assert REAL_HELPER(build) is True


@pytest.mark.parametrize(
    "script",
    [
        "_app/immutable/nodes/3.G1h2i3j4.js",
        "_app/immutable/entry/app.H5k6l7m8.js",
        "_app/immutable/workers/nested/deeper/w.J9n0p1q2.js",
        "_app/immutable/K3r4s5t6.js",
    ],
    ids=["nodes", "entry", "nested-folders", "immutable-root"],
)
def test_helper_finds_the_marker_in_a_script_at_any_depth(tmp_path, script):
    """The marker in one script only, wherever it sits under ``_app/immutable/`` (``nodes/3.<hash>.js`` included): True."""
    build = fake_build(tmp_path, {**RELEASE_BUILD, script: BARE_LAB_JS})

    assert REAL_HELPER(build) is True, f"the marker in {script} must count"


#: Files of a build that hold the marker and must not count: not a script of _app/immutable/, so not guarded by the plugin.
OUTSIDE_THE_SCRIPTS = {
    "source-map": "_app/immutable/chunks/C5e6f7g8.js.map",
    "css-asset": "_app/immutable/assets/0.E3k4l5m6.css",
    "index-html": "index.html",
    "root-sw-js": "sw.js",
    "static-offline-html": "offline.html",
    "sveltekit-env-js": "_app/env.js",
}


@pytest.mark.parametrize("place", list(OUTSIDE_THE_SCRIPTS.values()), ids=list(OUTSIDE_THE_SCRIPTS))
def test_helper_ignores_the_marker_outside_the_scripts_of_app_immutable(tmp_path, place):
    """The marker only in a source map, a CSS asset, ``index.html``, the root ``sw.js``, ``offline.html`` or ``_app/env.js``: False.

    The control then puts the same text in a chunk: True. So the build is read, and only the place decided.
    """
    build = fake_build(tmp_path, {**RELEASE_BUILD, place: STORAGE_KEY_LAB_JS})

    assert REAL_HELPER(build) is False, f"the marker in {place} must not count: only the scripts of _app/immutable/ do"

    write_build(build, {"_app/immutable/chunks/Z9y8x7w6.js": STORAGE_KEY_LAB_JS})
    assert REAL_HELPER(build) is True, "control: the same text in a chunk of this build must count"


def test_helper_finds_the_marker_inside_a_longer_string(tmp_path):
    """The marker only as the start of a longer string (``'lf-designer-lab/v1'``, as the Lab's storage keys write it): True."""
    assert f"'{MARKER}'" not in STORAGE_KEY_LAB_JS and f"'{MARKER}/v1'" in STORAGE_KEY_LAB_JS, "premise: the script holds the marker only inside a longer string"
    build = fake_build(tmp_path, {**RELEASE_BUILD, LAB_CHUNK: STORAGE_KEY_LAB_JS})

    assert REAL_HELPER(build) is True


def test_helper_reads_by_default_the_build_the_server_serves():
    """Called without arguments, as cmd_server calls it, the helper reads ``frontend/build/`` of this checkout."""
    default = inspect.signature(REAL_HELPER).parameters["build_dir"].default

    assert default == PROJECT_ROOT / "frontend" / "build", f"the helper's default build_dir must be {PROJECT_ROOT / 'frontend' / 'build'}, the folder the server serves: {default}"


# ---------------------------------------------------------------------------
# The marker is the Vite plugin's
# ---------------------------------------------------------------------------


def test_marker_is_the_lab_marker_the_vite_plugin_exports():
    """``DESIGNER_LAB_MARKER`` is the bytes of ``LAB_MARKER``, exported by the Vite plugin that guards a build without the Lab."""
    source = VITE_PLUGIN.read_text(encoding="utf-8")
    exports = [match.group("marker") for match in LAB_MARKER_EXPORT.finditer(source)]
    if len(exports) != 1:
        pytest.fail(f"{VITE_PLUGIN.relative_to(PROJECT_ROOT)} must export LAB_MARKER exactly once as a string literal (export const LAB_MARKER = '…';); found {len(exports)} such exports. Compare it with dev.py's DESIGNER_LAB_MARKER by hand, then update this test.")

    assert isinstance(dev.DESIGNER_LAB_MARKER, bytes), f"DESIGNER_LAB_MARKER must be bytes, the helper searches the bytes of each script: {dev.DESIGNER_LAB_MARKER!r}"
    assert dev.DESIGNER_LAB_MARKER.decode() == exports[0], f"dev.py's DESIGNER_LAB_MARKER {dev.DESIGNER_LAB_MARKER!r} must equal LAB_MARKER {exports[0]!r} of {VITE_PLUGIN.relative_to(PROJECT_ROOT)}"


# ---------------------------------------------------------------------------
# cmd_server's banner on fake builds (cases 1 to 4, and the mirror of case 4)
# ---------------------------------------------------------------------------


def test_server_banner_without_any_build_has_no_lab_line(monkeypatch, capsys, tmp_path):
    """Case 1, no build: no ``frontend/build`` at all, so no Designer Lab line; the start goes on to the launch."""
    build = tmp_path / "frontend" / "build"
    assert recorded_build_mode(monkeypatch, build) is None, "premise: dev.py reads this project as never built"

    start = start_server(monkeypatch, capsys, tmp_path, functools.partial(REAL_HELPER, build))

    assert_endpoints(start, lab_listed=False)
    assert_launched(start)


def test_server_banner_of_a_release_build_has_no_lab_line(monkeypatch, capsys, tmp_path):
    """Case 2, release build: scripts under ``_app/immutable/`` without the marker, ``.build-debug`` at 0: no Designer Lab line."""
    build = fake_build(tmp_path, RELEASE_BUILD)
    assert recorded_build_mode(monkeypatch, build) is False, "premise: dev.py reads this build as a production build"
    assert immutable_scripts(build), "premise: the build has scripts for the helper to read"

    start = start_server(monkeypatch, capsys, tmp_path, functools.partial(REAL_HELPER, build))

    assert_endpoints(start, lab_listed=False)
    assert_launched(start)


def test_server_banner_of_a_debug_build_with_the_lab_lists_it_on_the_server_port(monkeypatch, capsys, tmp_path):
    """Case 3, debug build with the Lab: a chunk with the marker, ``.build-debug`` at 1.

    One line `` ├── 🎨 Designer Lab: http://localhost:6999/designer-lab``, the port the server is launched on, right after
    the Frontend line and right before API Redoc.
    """
    build = fake_build(tmp_path, DEBUG_BUILD_WITH_LAB)
    assert recorded_build_mode(monkeypatch, build) is True, "premise: dev.py reads this build as a debug build"

    start = start_server(monkeypatch, capsys, tmp_path, functools.partial(REAL_HELPER, build))

    assert_endpoints(start, lab_listed=True)
    assert_launched(start)


def test_server_banner_of_a_debug_build_made_with_lf_designer_lab_0_has_no_lab_line(monkeypatch, capsys, tmp_path):
    """Case 4, debug build made with ``LF_DESIGNER_LAB=0``: ``.build-debug`` at 1 but no script with the marker, no line.

    The mode file is not enough: then the same debug build with the Lab's chunk added gets the line, the mode file unchanged.
    """
    build = fake_build(tmp_path, DEBUG_BUILD_WITHOUT_LAB)
    assert recorded_build_mode(monkeypatch, build) is True, "premise: dev.py reads this build as a debug build"
    assert immutable_scripts(build), "premise: the build has scripts for the helper to read"

    without_lab = start_server(monkeypatch, capsys, tmp_path, functools.partial(REAL_HELPER, build))

    assert_endpoints(without_lab, lab_listed=False)
    assert_launched(without_lab)

    write_build(build, {LAB_CHUNK: STORAGE_KEY_LAB_JS})
    with_lab = start_server(monkeypatch, capsys, tmp_path, functools.partial(REAL_HELPER, build))

    assert recorded_build_mode(monkeypatch, build) is True, "control: the mode file still says debug"
    assert_endpoints(with_lab, lab_listed=True)
    assert_launched(with_lab)


def test_server_banner_of_a_production_build_made_with_lf_designer_lab_1_lists_the_lab(monkeypatch, capsys, tmp_path):
    """The mirror of case 4: a production build made with ``LF_DESIGNER_LAB=1``, ``.build-debug`` at 0, carries the Lab.

    The line is printed: the marker decides, not the mode file.
    """
    build = fake_build(tmp_path, PRODUCTION_BUILD_WITH_LAB)
    assert recorded_build_mode(monkeypatch, build) is False, "premise: dev.py reads this build as a production build"

    start = start_server(monkeypatch, capsys, tmp_path, functools.partial(REAL_HELPER, build))

    assert_endpoints(start, lab_listed=True)
    assert_launched(start)


@pytest.mark.parametrize(
    ("debug", "before", "after", "lab_listed"),
    [(True, RELEASE_BUILD, DEBUG_BUILD_WITH_LAB, True), (False, DEBUG_BUILD_WITH_LAB, RELEASE_BUILD, False)],
    ids=["rebuilt-in-debug-with-the-lab", "rebuilt-in-production-without-it"],
)
def test_server_banner_reads_the_build_the_auto_build_left(monkeypatch, capsys, tmp_path, debug, before, after, lab_listed):
    """The banner speaks of the build the server serves, as the frontend auto-build left it.

    ``./dev.py server --debug`` right after a production build rebuilds in debug, with the Lab, and ``./dev.py server``
    after a debug build rebuilds in production, without it: the build found before the auto-build says the opposite.
    """
    build = fake_build(tmp_path, before)
    assert REAL_HELPER(build) is (not lab_listed), "premise: before the auto-build, the build says the opposite"
    rebuilds: list[bool] = []

    def rebuild(debug_asked: bool) -> int:
        rebuilds.append(debug_asked)
        shutil.rmtree(build)
        write_build(build, after)
        return 0

    start = start_server(monkeypatch, capsys, tmp_path, functools.partial(REAL_HELPER, build), frontend_build=rebuild, debug=debug)

    assert rebuilds == [debug], f"the stood-in auto-build must run once, in the mode asked for (debug={debug}): {rebuilds}"
    assert_endpoints(start, lab_listed=lab_listed)
    assert_launched(start)


# ---------------------------------------------------------------------------
# --build-only (case 5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("test_mode", [False, True], ids=["server", "test-server"])
def test_build_only_prints_no_endpoints_and_never_asks_about_the_lab(monkeypatch, capsys, tmp_path, test_mode):
    """Case 5, ``--build-only`` (``server --build-only``, and the test runner's ``server --test --build-only``).

    cmd_server runs its builds and returns 0, prints neither «Available endpoints» nor a Lab line, launches nothing, and
    never calls the helper. The recorder answers True: had cmd_server asked and printed, the Lab line would show.
    """
    asked: list[tuple] = []

    def lab_check(*args, **kwargs):
        asked.append((args, kwargs))
        return True

    start = start_server(monkeypatch, capsys, tmp_path, lab_check, build_only=True, test=test_mode)

    assert start.returned == 0, f"--build-only must return 0 once its builds succeed, not {start.returned!r}"
    assert "frontend-build" in start.steps, f"premise: cmd_server ran its builds before returning: steps {start.steps}"
    assert asked == [], f"--build-only must never ask about the Lab: the helper was called {len(asked)} time(s)"
    printed = [line for line in start.lines if "Available endpoints" in line or LAB_MENTION.search(line)]
    assert printed == [], f"--build-only must print neither the endpoints nor the Lab: {printed}"
    assert start.launches == [], f"--build-only must launch nothing: {[launch.cmd for launch in start.launches]}"


# ---------------------------------------------------------------------------
# Read errors (case 6)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("when", ["at-the-call", "while-iterating"])
def test_helper_reads_a_failing_listing_as_no_lab(monkeypatch, tmp_path, when):
    """Case 6a: listing ``_app/immutable/`` raises ``OSError``, at the call or after yielding a script: False, no error.

    The build carries the Lab (checked first), so the False comes from the failed listing.
    """
    build = fake_build(tmp_path, DEBUG_BUILD_WITH_LAB)
    assert REAL_HELPER(build) is True, "premise: read normally, this build carries the Lab"
    after = [build / "_app/immutable/chunks/C5e6f7g8.js"] if when == "while-iterating" else None
    failed = fail_listing(monkeypatch, build / "_app" / "immutable", after=after)

    assert REAL_HELPER(build) is False, "a listing that fails must read as no Lab"
    assert failed, "the failing listing was never reached: the helper no longer lists _app/immutable/ with rglob"


def test_helper_skips_an_unreadable_script_so_alone_it_reads_as_no_lab(monkeypatch, tmp_path):
    """Case 6b: reading the only script with the marker raises ``PermissionError``: that script is skipped, False, no error."""
    build = fake_build(tmp_path, DEBUG_BUILD_WITH_LAB)
    assert REAL_HELPER(build) is True, "premise: read normally, this build carries the Lab"
    refused = refuse_reading(monkeypatch, build / LAB_CHUNK)

    assert REAL_HELPER(build) is False, f"{LAB_CHUNK} cannot be read and no other script holds the marker"
    assert refused, f"reading {LAB_CHUNK} was never attempted"


def test_helper_skips_an_unreadable_script_and_goes_on_to_another_with_the_marker(monkeypatch, tmp_path):
    """Case 6b: the refused script is skipped and the scan goes on: another script with the marker still counts, True.

    The refused chunk sorts before the other script (``chunks/`` before ``nodes/``) and the helper reads in sorted order
    up to its first hit, so it meets the refusal first: the test checks it did.
    """
    other = "_app/immutable/nodes/3.G1h2i3j4.js"
    build = fake_build(tmp_path, {**DEBUG_BUILD_WITH_LAB, other: BARE_LAB_JS})
    assert immutable_scripts(build).index(build / LAB_CHUNK) < immutable_scripts(build).index(build / other), "premise: the refused chunk sorts first"
    refused = refuse_reading(monkeypatch, build / LAB_CHUNK)

    assert REAL_HELPER(build) is True, f"{other} holds the marker: the scan must go on past the unreadable {LAB_CHUNK}"
    assert refused, f"reading {LAB_CHUNK} was never attempted, so the scan never had to go past it"


@pytest.mark.parametrize("fault", ["listing-fails", "lab-script-unreadable"])
def test_server_starts_despite_a_build_it_cannot_read(monkeypatch, capsys, tmp_path, fault):
    """Case 6c: through cmd_server, a failing listing or the Lab's chunk unreadable: no Lab line, and the server still starts.

    cmd_server reaches the uvicorn launch and returns its result. The build carries the Lab when it can be read (checked
    first), so the missing line comes from the error, and the error from the injected fault (checked after).
    """
    build = fake_build(tmp_path, DEBUG_BUILD_WITH_LAB)
    assert REAL_HELPER(build) is True, "premise: read normally, this build carries the Lab"
    if fault == "listing-fails":
        injected = fail_listing(monkeypatch, build / "_app" / "immutable")
    else:
        injected = refuse_reading(monkeypatch, build / LAB_CHUNK)

    start = start_server(monkeypatch, capsys, tmp_path, functools.partial(REAL_HELPER, build))

    assert injected, f"the injected fault ({fault}) was never reached"
    assert_endpoints(start, lab_listed=False)
    assert_launched(start)


# ---------------------------------------------------------------------------
# cmd_fe_dev
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("value", "lab_listed"), [(None, True), ("1", True), ("false", True), ("", True), ("0", False)], ids=["unset", "1", "false", "empty", "0"])
def test_front_dev_lists_the_lab_unless_lf_designer_lab_is_0(monkeypatch, capsys, value, lab_listed):
    """``./dev.py front dev``: the Lab line right after the URL unless ``LF_DESIGNER_LAB`` is exactly ``"0"``; then ``npm run dev``.

    ``designerLabEnabled`` turns the Lab off under ``vite dev`` only for ``'0'``: unset, ``'1'``, ``'false'`` and an empty
    value all keep it. The URL line is printed in every case, the launch goes through ``run_command_live`` in
    ``frontend/``, and its result is returned.
    """
    if value is None:
        monkeypatch.delenv("LF_DESIGNER_LAB", raising=False)
    else:
        monkeypatch.setenv("LF_DESIGNER_LAB", value)
    launches = record_launches(monkeypatch)
    capsys.readouterr()

    returned = dev.cmd_fe_dev(argparse.Namespace())

    lines = ANSI.sub("", capsys.readouterr().out).splitlines()
    shown = "\n".join(lines)
    url = [index for index, line in enumerate(lines) if line.strip() == FRONT_DEV_URL_LINE]
    mentions = [index for index, line in enumerate(lines) if LAB_MENTION.search(line)]
    assert len(url) == 1, f"front dev must print {FRONT_DEV_URL_LINE!r} once; it printed:\n{shown}"
    if lab_listed:
        assert mentions == [url[0] + 1] and lines[mentions[0]].strip() == FRONT_DEV_LAB_LINE, f"LF_DESIGNER_LAB={value!r}: front dev must print {FRONT_DEV_LAB_LINE!r} right after its URL, and mention the Lab nowhere else; it printed:\n{shown}"
    else:
        assert mentions == [], f"LF_DESIGNER_LAB={value!r}: front dev must not mention the Lab; it printed:\n{shown}"
    assert [launch.cmd for launch in launches] == [["npm", "run", "dev"]], f"front dev must launch npm run dev once: {[launch.cmd for launch in launches]}"
    assert launches[0].cwd == dev.PROJECT_ROOT / "frontend", f"npm run dev must run in frontend/: {launches[0].cwd}"
    assert returned is LAUNCH_RESULT, f"front dev must return the launch's result, not {returned!r}"
