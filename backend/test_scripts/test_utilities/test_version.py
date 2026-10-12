"""
Tests for version utilities.

Covers:
- get_version_info: returns dict with version, is_dirty, is_release
- get_git_version: returns git describe string
- the project root get_git_version works from: the repository root in development,
  the app root (/app) in the Docker image, wherever the module sits in the package tree
"""

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

import backend.app.utils.runtime.version as version_utils
from backend.app.utils.runtime.version import get_git_version, get_version_info

# This file is <repo>/backend/test_scripts/test_utilities/test_version.py.
REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def no_version_file(monkeypatch):
    """Force get_git_version past the pre-generated VERSION file so the git-describe
    branch is exercised. A leftover VERSION build artifact (created by
    `./dev.py docker build`) would otherwise short-circuit the function and mask the
    monkeypatched subprocess.run."""
    monkeypatch.setattr(version_utils.Path, "exists", lambda self: False)


@pytest.fixture
def fresh_version_cache():
    """Empty get_git_version's lru_cache before the test, and again after it.

    The second clear is a finalizer, so it runs even when the test fails: a value
    computed under a spy never leaks into the tests that follow."""
    get_git_version.cache_clear()
    yield
    get_git_version.cache_clear()


class TestGetGitVersion:
    def test_returns_string(self):
        version = get_git_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_starts_with_v_or_unknown(self):
        version = get_git_version()
        assert version.startswith("v") or version == "unknown"

    def test_returns_tagged_version_from_git_describe(self, monkeypatch, no_version_file):
        get_git_version.cache_clear()
        monkeypatch.setattr(
            version_utils.subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="v1.2.3\n"),
        )

        version = get_git_version()

        assert version == "v1.2.3"
        get_git_version.cache_clear()

    def test_normalizes_hash_only_output(self, monkeypatch, no_version_file):
        get_git_version.cache_clear()
        monkeypatch.setattr(
            version_utils.subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="abcdef0\n"),
        )

        version = get_git_version()

        assert version == "v0.0.0-gabcdef0"
        get_git_version.cache_clear()

    def test_returns_unknown_when_git_describe_fails(self, monkeypatch, no_version_file):
        get_git_version.cache_clear()
        monkeypatch.setattr(
            version_utils.subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=""),
        )

        version = get_git_version()

        assert version == "unknown"
        get_git_version.cache_clear()

    def test_version_file_takes_precedence_over_git(self, monkeypatch):
        """A present VERSION file (Docker/frozen build) wins over git describe."""
        get_git_version.cache_clear()
        monkeypatch.setattr(version_utils.Path, "exists", lambda self: True)
        monkeypatch.setattr(version_utils.Path, "read_text", lambda self, *args, **kwargs: "v9.9.9\n")
        monkeypatch.setattr(
            version_utils.subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="v0.0.0-should-not-be-used\n"),
        )

        version = get_git_version()

        assert version == "v9.9.9"
        get_git_version.cache_clear()


# What the image-layout test runs in its child interpreter. structlog's default logger
# prints to stdout: its events go to stderr instead, one key=value line each, so that
# stdout carries the version and nothing else.
_IMAGE_PROBE = textwrap.dedent(f"""
    import sys

    import structlog

    structlog.configure(
        processors=[structlog.processors.KeyValueRenderer(key_order=["event"])],
        logger_factory=structlog.PrintLoggerFactory(sys.stderr),
    )

    from {version_utils.__name__} import get_git_version

    print(get_git_version())
    """)


class TestProjectRoot:
    """get_git_version reads VERSION from, and runs `git describe` in, the project root.

    BU1 moved the module from backend/app/utils/ to backend/app/utils/runtime/, one
    directory deeper, and the four `.parent` it counted up from its own file then
    stopped at backend/. Development cannot tell: there is no VERSION file, and
    `git describe` works from a subfolder too. The Docker image can: it has no .git/
    and ships VERSION at its app root (Dockerfile: WORKDIR /app, COPY backend/
    ./backend/, COPY VERSION ./), so a root of /app/backend made it report "unknown".
    """

    def test_git_describe_runs_in_repository_root(self, monkeypatch, no_version_file, fresh_version_cache):
        assert (REPO_ROOT / "dev.py").is_file() and (REPO_ROOT / "backend" / "app").is_dir(), f"{REPO_ROOT} is not the repository root: this test file has moved"
        calls = []

        def spy_run(cmd, *_args, **kwargs):
            calls.append((cmd, kwargs.get("cwd")))
            return SimpleNamespace(returncode=128, stdout="")

        monkeypatch.setattr(version_utils.subprocess, "run", spy_run)

        get_git_version()

        cwds = [cwd for cmd, cwd in calls if list(cmd[:2]) == ["git", "describe"]]
        assert len(cwds) == 1, f"expected one git describe, recorded {calls}"
        assert cwds[0] is not None and Path(cwds[0]).resolve() == REPO_ROOT, f"git describe ran in {cwds[0]}, not in the repository root {REPO_ROOT}"

    def test_image_layout_reads_version_file_without_git(self, tmp_path):
        # The image's /app rebuilt under tmp_path: the module at its package path, VERSION
        # next to backend/, and a PATH holding one empty directory — no git, no .git/.
        app_root = tmp_path / "app"
        *packages, module = version_utils.__name__.split(".")
        package_dir = app_root.joinpath(*packages)
        package_dir.mkdir(parents=True)
        # backend/ has no __init__.py in the repository (a namespace package): nor here.
        for depth in range(2, len(packages) + 1):
            app_root.joinpath(*packages[:depth], "__init__.py").touch()
        shutil.copy(version_utils.__file__, package_dir / f"{module}.py")
        (app_root / "VERSION").write_text("v9.9.9-test\n")
        no_git_bin = tmp_path / "no-git-bin"
        no_git_bin.mkdir()

        result = subprocess.run(
            [sys.executable, "-c", _IMAGE_PROBE],
            cwd=app_root,
            env={"PATH": str(no_git_bin), "PYTHONPATH": str(app_root)},
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )

        assert result.returncode == 0, f"the probe interpreter failed (exit {result.returncode}):\n{result.stderr}"
        assert result.stdout.strip() == "v9.9.9-test", f"with no git, get_git_version() must read {app_root / 'VERSION'} (the app root, next to backend/); it printed {result.stdout.strip()!r}. Its logs: {result.stderr.strip() or '(none)'}"


class TestGetVersionInfo:
    def test_returns_dict_with_keys(self):
        info = get_version_info()
        assert isinstance(info, dict)
        assert "version" in info
        assert "is_dirty" in info
        assert "is_release" in info

    def test_is_dirty_is_bool(self):
        info = get_version_info()
        assert isinstance(info["is_dirty"], bool)

    def test_is_release_is_bool(self):
        info = get_version_info()
        assert isinstance(info["is_release"], bool)

    def test_dirty_snapshot_is_not_release(self, monkeypatch):
        monkeypatch.setattr(version_utils, "get_git_version", lambda: "v1.2.3-5-gabcdef-dirty")

        info = get_version_info()

        assert info == {
            "version": "v1.2.3-5-gabcdef-dirty",
            "is_dirty": True,
            "is_release": False,
        }

    def test_clean_tag_is_release(self, monkeypatch):
        monkeypatch.setattr(version_utils, "get_git_version", lambda: "v1.2.3")

        info = get_version_info()

        assert info == {
            "version": "v1.2.3",
            "is_dirty": False,
            "is_release": True,
        }
