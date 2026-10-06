"""The Dockerfile's frontend guard, ``scripts/docker/check_frontend_build.sh`` (M, R2 P0 release images).

The release images copy ``frontend/build/``, and the docs gallery runs before them:
its Playwright webServer is ``./dev.py server --test``, which rebuilds that directory
in debug mode (no minification, sourcemaps, ~2.7x the size). That build reached the
published images. The Dockerfile now copies the build into a ``frontend`` stage, runs
this script on it with ``sh``, and only the final stage's ``COPY --from=frontend``
takes it further. The script must therefore refuse, with exit status 1:

* a build without ``index.html``, or without ``200.html`` (the SPA fallback);
* ``.build-debug`` saying ``1`` once whitespace is stripped (``./dev.py front build``
  writes ``0`` or ``1``; a trailing newline must not turn debug into production);
* a ``.coverage-instrumented`` marker (the JS-coverage E2E build);
* any ``*.map`` file anywhere in the tree, naming the first one it finds;

and accept everything else with exit status 0, warning on stderr when
``.build-debug`` is missing: the mode is then unknown, but nothing else is wrong.

Its messages are English-only build-log lines, not UI strings, so stable fragments
of them are part of the contract and are asserted as such.

PURE: every build tree lives in ``tmp_path`` and the script runs under ``sh``, as in
the Docker stage. No DB, no server, no network, no repository writes.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = PROJECT_ROOT / "scripts" / "docker" / "check_frontend_build.sh"

OK_LINE = "Frontend build OK: production."
REFUSED = "is not a production frontend build"
REBUILD_HINT = "Rebuild it with './dev.py front build'"
CHUNK = Path("_app") / "immutable" / "chunks" / "app.Bx7d2Q.js"

# A plain name, and one that only survives if the script quotes every expansion.
DIR_NAMES = ["build", "front end build"]


def make_build(build_dir: Path, *, debug_marker: str | None = "0") -> Path:
    """A minimal production-shaped build: both HTML entry points and one hashed chunk."""
    (build_dir / CHUNK).parent.mkdir(parents=True)
    (build_dir / "index.html").write_text("<!doctype html><title>LibreFolio</title>\n")
    (build_dir / "200.html").write_text("<!doctype html><title>LibreFolio</title>\n")
    (build_dir / CHUNK).write_text("export const answer = 42;\n")
    if debug_marker is not None:
        (build_dir / ".build-debug").write_text(debug_marker)
    return build_dir


def run_guard(*args: str) -> subprocess.CompletedProcess:
    """Run the guard exactly as the Docker stage does: ``sh <script> <dir>``."""
    sh = shutil.which("sh")
    assert sh is not None, "no POSIX sh on PATH: the Docker stage runs the guard with sh"
    return subprocess.run([sh, str(SCRIPT), *args], capture_output=True, text=True, timeout=60, check=False)


def assert_accepted(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 0, f"exit {result.returncode}, stderr: {result.stderr!r}"
    assert OK_LINE in result.stdout, f"stdout: {result.stdout!r}"


def assert_refused(result: subprocess.CompletedProcess, reason: str) -> None:
    """Exit 1, the reason and the rebuild hint on stderr, and no OK line anywhere."""
    assert result.returncode == 1, f"exit {result.returncode}, stdout: {result.stdout!r}, stderr: {result.stderr!r}"
    assert REFUSED in result.stderr, f"stderr: {result.stderr!r}"
    assert reason in result.stderr, f"expected {reason!r} in stderr: {result.stderr!r}"
    assert REBUILD_HINT in result.stderr, f"stderr: {result.stderr!r}"
    assert OK_LINE not in result.stdout


class TestProductionBuildIsAccepted:
    @pytest.mark.parametrize("dir_name", DIR_NAMES)
    @pytest.mark.parametrize("marker", ["0", "0\n"])
    def test_production_build_passes_without_a_warning(self, tmp_path, dir_name, marker):
        result = run_guard(str(make_build(tmp_path / dir_name, debug_marker=marker)))

        assert_accepted(result)
        assert result.stderr == "", "a build that says it is production must pass silently"

    def test_missing_marker_passes_with_a_warning(self, tmp_path):
        """Unknown mode but no sourcemaps: accepted, and the doubt is said out loud."""
        result = run_guard(str(make_build(tmp_path / "build", debug_marker=None)))

        assert_accepted(result)
        assert "WARNING" in result.stderr
        assert ".build-debug is missing" in result.stderr


class TestNonProductionBuildIsRefused:
    @pytest.mark.parametrize("marker", ["1", "1\n", " 1\r\n"])
    def test_debug_marker_is_refused(self, tmp_path, marker):
        result = run_guard(str(make_build(tmp_path / "build", debug_marker=marker)))

        assert_refused(result, "debug build")

    @pytest.mark.parametrize("dir_name", DIR_NAMES)
    def test_stray_sourcemap_is_refused_and_named(self, tmp_path, dir_name):
        """The marker can lie (a build copied over a production one): the maps cannot."""
        build_dir = make_build(tmp_path / dir_name)
        stray = CHUNK.with_name(CHUNK.name + ".map")
        (build_dir / stray).write_text('{"version": 3}\n')

        result = run_guard(str(build_dir))

        assert_refused(result, "sourcemaps")
        assert stray.as_posix() in result.stderr, f"the refused file must be named relative to the build: {result.stderr!r}"

    def test_coverage_instrumented_build_is_refused(self, tmp_path):
        build_dir = make_build(tmp_path / "build")
        (build_dir / ".coverage-instrumented").write_text("")

        result = run_guard(str(build_dir))

        assert_refused(result, "instrumented for coverage")

    @pytest.mark.parametrize("entry_point", ["index.html", "200.html"])
    def test_missing_entry_point_is_refused(self, tmp_path, entry_point):
        build_dir = make_build(tmp_path / "build")
        (build_dir / entry_point).unlink()

        result = run_guard(str(build_dir))

        assert_refused(result, entry_point)
        assert "is missing" in result.stderr

    def test_missing_argument_is_a_usage_error(self):
        result = run_guard()

        assert result.returncode != 0
        assert "usage: check_frontend_build.sh <frontend-build-dir>" in result.stderr
        assert OK_LINE not in result.stdout
