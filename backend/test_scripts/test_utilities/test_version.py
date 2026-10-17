"""
Tests for version utilities.

Covers:
- get_version_info: returns dict with version, is_dirty, is_release
- get_git_version: ``LF_APP_VERSION``, stripped, comes first when set and not blank, and git then never runs. Unset or
  blank, the R2 order: in a checkout, with ``.git`` in the project root (a folder, a file as in a worktree or a
  submodule, or a link), ``git describe`` decides, even over a VERSION file with another value. When git cannot answer
  (non-zero exit, no output, git missing or too slow) the VERSION file counts, else "unknown". Without ``.git`` git
  never runs, so the tags of a parent repository are never reported. A blank or unreadable VERSION counts as absent.
  Hash-only output is normalised to v0.0.0-g<hash>, and the answer is computed once.
- the project root get_git_version works from: the repository root in development,
  the app root (/app) in the Docker image, wherever the module sits in the package tree

The R2 tests build the project root in tmp_path (``_project_root`` patched), unset ``LF_APP_VERSION`` and replace
``subprocess.run`` with a recorder. One of them runs the real git, in a throwaway repository of its own.
"""

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

import backend.app.config.platform as platform_config
import backend.app.utils.runtime.version as version_utils
from backend.app.utils.runtime.version import get_git_version, get_version_info

# This file is <repo>/backend/test_scripts/test_utilities/test_version.py.
REPO_ROOT = Path(__file__).resolve().parents[3]


#: The command get_git_version runs in a checkout.
GIT_DESCRIBE = ["git", "describe", "--tags", "--always", "--dirty"]
#: The version a build is frozen at: when set and not blank, get_git_version reports it, stripped, before anything else.
FROZEN_VERSION_VARIABLE = "LF_APP_VERSION"

needs_symlinks = pytest.mark.skipif(os.name == "nt", reason="creating a symbolic link needs a privilege on Windows")


@pytest.fixture
def fresh_version_cache():
    """Empty get_git_version's lru_cache before the test, and again after it.

    The second clear is a finalizer, so it runs even when the test fails: a value
    computed under a spy never leaks into the tests that follow."""
    get_git_version.cache_clear()
    yield
    get_git_version.cache_clear()


@pytest.fixture
def project(tmp_path, monkeypatch, fresh_version_cache) -> Path:
    """An empty project root of this test's own: get_git_version looks for ``.git`` and VERSION there, and runs git there.

    ``LF_APP_VERSION`` is unset, as on an install: set, it would come before both (TestFrozenVersionComesFirst).
    """
    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.delenv(FROZEN_VERSION_VARIABLE, raising=False)
    monkeypatch.setattr(version_utils, "_project_root", lambda: root)
    return root


def _completed(returncode: int, stdout: str) -> SimpleNamespace:
    """What ``subprocess.run(..., capture_output=True, text=True)`` returns, as far as get_git_version reads it."""
    return SimpleNamespace(returncode=returncode, stdout=stdout)


class GitRecorder:
    """Stands in for ``subprocess.run``: records each command with its cwd, then answers ``outcome``, raised when an exception."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], object]] = []
        # Until a test says otherwise, git answers as in a repository without commits.
        self.outcome: object = _completed(128, "")

    def __call__(self, cmd, *_args, **kwargs):
        self.calls.append((list(cmd), kwargs.get("cwd")))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


@pytest.fixture
def git(monkeypatch) -> GitRecorder:
    """Every ``subprocess.run`` of the test, recorded and answered by a GitRecorder."""
    recorder = GitRecorder()
    monkeypatch.setattr(version_utils.subprocess, "run", recorder)
    return recorder


def _mark_checkout(root: Path, kind: str) -> None:
    """Put ``.git`` in ``root``: a folder, a file as git writes in a worktree or a submodule, or a link to nowhere."""
    marker = root / ".git"
    if kind == "folder":
        marker.mkdir()
    elif kind == "file":
        marker.write_text("gitdir: ../elsewhere/.git/worktrees/project\n")
    elif kind == "dangling-link":
        marker.symlink_to(root / "no-such-gitdir")
    else:
        raise ValueError(f"unknown kind of .git: {kind!r}")
    assert os.path.lexists(marker), f"Setup: {marker} was not created"


def _git(cwd: Path, *args: str) -> str:
    """Run the real git in ``cwd`` with no user or system configuration and a fixed identity; its stdout, stripped."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="LibreFolio Test",
        GIT_AUTHOR_EMAIL="test@example.com",
        GIT_COMMITTER_NAME="LibreFolio Test",
        GIT_COMMITTER_EMAIL="test@example.com",
    )
    result = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, f"Setup: git {' '.join(args)} failed in {cwd} (exit {result.returncode}): {result.stderr.strip()}"
    return result.stdout.strip()


#: Every way ``git describe`` can fail to answer, as a factory: each test gets an outcome of its own.
GIT_FAILURES = [
    pytest.param(lambda: _completed(128, ""), id="non-zero-exit"),
    pytest.param(lambda: _completed(128, "v6.6.6\n"), id="non-zero-exit-with-output"),
    pytest.param(lambda: _completed(0, ""), id="empty-output"),
    pytest.param(lambda: _completed(0, " \n"), id="blank-output"),
    pytest.param(lambda: FileNotFoundError(2, "No such file or directory", "git"), id="git-not-installed"),
    pytest.param(lambda: subprocess.TimeoutExpired(GIT_DESCRIBE, 5), id="timeout"),
    pytest.param(lambda: PermissionError(13, "Permission denied", "git"), id="git-not-executable"),
]


class TestGetGitVersion:
    def test_returns_string(self):
        version = get_git_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_starts_with_v_or_unknown(self):
        version = get_git_version()
        assert version.startswith("v") or version == "unknown"


class TestFrozenVersionComesFirst:
    """``LF_APP_VERSION`` set and not blank: reported stripped, before ``.git`` and VERSION, and git never runs. Unset or blank: ignored."""

    @staticmethod
    def _checkout_whose_git_describe_answers(project: Path, git: GitRecorder) -> None:
        """``.git``, a VERSION file, and a git describe that answers: without the variable, git describe decides (v1.2.3)."""
        _mark_checkout(project, "folder")
        (project / "VERSION").write_text("v9.9.9\n")
        git.outcome = _completed(0, "v1.2.3\n")

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param("v5.0.0-frozen", "v5.0.0-frozen", id="as-set"),
            pytest.param("  v5.0.0-frozen \n", "v5.0.0-frozen", id="stripped"),
        ],
    )
    def test_it_wins_over_git_describe_and_the_version_file(self, project, git, monkeypatch, value, expected):
        self._checkout_whose_git_describe_answers(project, git)
        monkeypatch.setenv(FROZEN_VERSION_VARIABLE, value)

        frozen = get_git_version()
        calls_while_frozen = list(git.calls)
        # Control, same project without the variable: git describe answers and wins over VERSION.
        monkeypatch.delenv(FROZEN_VERSION_VARIABLE)
        get_git_version.cache_clear()
        described = get_git_version()

        assert (described, git.calls) == ("v1.2.3", [(GIT_DESCRIBE, project)]), f"Barrier: without {FROZEN_VERSION_VARIABLE} this project reports git describe: {described!r}, {git.calls}"
        assert calls_while_frozen == [], f"with {FROZEN_VERSION_VARIABLE} set git must not run: recorded {calls_while_frozen}"
        assert frozen == expected, f"{FROZEN_VERSION_VARIABLE}={value!r} must win over git describe (v1.2.3) and VERSION (v9.9.9): got {frozen!r}"

    @pytest.mark.parametrize("checkout", [True, False], ids=["dot-git-git-describe-decides", "no-dot-git-version-file-decides"])
    @pytest.mark.parametrize("value", [None, "", "   ", " \t\n"], ids=["unset", "empty", "spaces", "any-whitespace"])
    def test_unset_or_blank_it_is_ignored(self, project, git, monkeypatch, value, checkout):
        """The R2 order applies as without the variable: git describe in a checkout, VERSION without one."""
        if checkout:
            _mark_checkout(project, "folder")
        (project / "VERSION").write_text("v9.9.9\n")
        git.outcome = _completed(0, "v1.2.3\n")
        if value is not None:
            monkeypatch.setenv(FROZEN_VERSION_VARIABLE, value)

        version = get_git_version()

        expected_calls, expected = ([(GIT_DESCRIBE, project)], "v1.2.3") if checkout else ([], "v9.9.9")
        assert git.calls == expected_calls, f"{FROZEN_VERSION_VARIABLE}={value!r} is ignored: expected git calls {expected_calls}, recorded {git.calls}"
        assert version == expected, f"{FROZEN_VERSION_VARIABLE}={value!r} is ignored, so the R2 order decides: expected {expected!r}, got {version!r}"


class TestCheckoutAsksGitDescribe:
    """With ``.git`` in the project root, of any kind, ``git describe`` run there decides; when it cannot answer, VERSION, else "unknown"."""

    @pytest.mark.parametrize("kind", ["folder", "file", pytest.param("dangling-link", marks=needs_symlinks)])
    def test_dot_git_of_any_kind_makes_git_describe_decide(self, project, git, kind):
        _mark_checkout(project, kind)
        git.outcome = _completed(0, "v1.2.3\n")

        version = get_git_version()

        assert git.calls == [(GIT_DESCRIBE, project)], f"with .git as a {kind}, expected one git describe in {project}, recorded {git.calls}"
        assert version == "v1.2.3", f"with .git as a {kind}, git describe must decide: got {version!r}"

    def test_git_describe_wins_over_a_version_file(self, project, git):
        """A VERSION file left over by an earlier build cannot hide a newer commit."""
        _mark_checkout(project, "folder")
        (project / "VERSION").write_text("v9.9.9\n")
        git.outcome = _completed(0, "v1.2.3-4-gabcdef0-dirty\n")

        version = get_git_version()

        assert version == "v1.2.3-4-gabcdef0-dirty", f"in a checkout git describe wins over VERSION (v9.9.9): got {version!r}"

    @pytest.mark.parametrize(
        ("stdout", "expected"),
        [
            pytest.param("abcdef0\n", "v0.0.0-gabcdef0", id="hash-only"),
            pytest.param("abcdef0-dirty\n", "v0.0.0-gabcdef0-dirty", id="hash-only-dirty"),
            pytest.param("v1.2.3\n", "v1.2.3", id="tag"),
            pytest.param("V2.0.0\n", "V2.0.0", id="tag-capital-v"),
            pytest.param("  v1.2.3-5-gabcdef0  \n", "v1.2.3-5-gabcdef0", id="tag-with-commits-stripped"),
        ],
    )
    def test_the_answer_of_git_describe_is_normalised(self, project, git, stdout, expected):
        """Hash-only output (no tag) becomes v0.0.0-g<hash>; output starting with v or V is kept, stripped."""
        _mark_checkout(project, "folder")
        git.outcome = _completed(0, stdout)

        version = get_git_version()

        assert version == expected, f"git describe answering {stdout!r} must give {expected!r}, got {version!r}"

    def test_the_version_is_computed_once(self, project, git):
        _mark_checkout(project, "folder")
        git.outcome = _completed(0, "v1.2.3\n")

        versions = (get_git_version(), get_git_version())

        assert versions == ("v1.2.3", "v1.2.3")
        assert len(git.calls) == 1, f"get_git_version is cached: expected one git describe for two calls, recorded {git.calls}"

    @pytest.mark.parametrize("failure", GIT_FAILURES)
    def test_when_git_cannot_answer_the_version_file_counts(self, project, git, failure):
        _mark_checkout(project, "folder")
        (project / "VERSION").write_text("v9.9.9-frozen\n")
        git.outcome = failure()

        version = get_git_version()

        assert git.calls == [(GIT_DESCRIBE, project)], f"Barrier: git describe must be asked first, recorded {git.calls}"
        assert version == "v9.9.9-frozen", f"git describe could not answer ({git.outcome!r}): the VERSION file must count, got {version!r}"

    @pytest.mark.parametrize("failure", GIT_FAILURES)
    def test_when_git_cannot_answer_and_there_is_no_version_file_it_is_unknown(self, project, git, failure):
        _mark_checkout(project, "folder")
        git.outcome = failure()

        version = get_git_version()

        assert git.calls == [(GIT_DESCRIBE, project)], f"Barrier: git describe must be asked first, recorded {git.calls}"
        assert version == "unknown", f"git describe could not answer ({git.outcome!r}) and there is no VERSION file: got {version!r}"


class TestWithoutCheckoutTheVersionFileDecides:
    """Without ``.git`` in the project root git never runs: the VERSION file, stripped, else "unknown"."""

    def test_the_version_file_decides_and_git_never_runs(self, project, git):
        (project / "VERSION").write_text("v3.1.4\n")
        git.outcome = _completed(0, "v0.0.0-not-to-be-asked\n")

        version = get_git_version()

        assert git.calls == [], f"without .git in {project} git must not run: recorded {git.calls}"
        assert version == "v3.1.4"

    def test_without_a_version_file_it_is_unknown_and_git_never_runs(self, project, git):
        git.outcome = _completed(0, "v0.0.0-not-to-be-asked\n")

        version = get_git_version()

        assert git.calls == [], f"without .git in {project} git must not run: recorded {git.calls}"
        assert version == "unknown"

    def test_the_version_file_is_stripped(self, project, git):
        (project / "VERSION").write_text("\n  v2.0.0-rc1  \n\n")

        assert get_git_version() == "v2.0.0-rc1"

    def test_the_tags_of_a_parent_repository_are_never_reported(self, tmp_path, monkeypatch, fresh_version_cache):
        """The project folder, without ``.git``, sits inside a tagged repository: "unknown", never the tag of that repository.

        The real git, in a throwaway repository with no user or system configuration.
        """
        parent = tmp_path / "parent"
        project = parent / "project"
        project.mkdir(parents=True)
        _git(parent, "init", "--quiet")
        _git(parent, "commit", "--allow-empty", "--quiet", "-m", "parent commit")
        _git(parent, "tag", "v7.7.7-parent")
        # Presence barrier: asked from the project folder, git describe answers the tag of the parent repository.
        assert _git(project, *GIT_DESCRIBE[1:]) == "v7.7.7-parent", "Setup: git describe in the project folder must see the parent repository"
        monkeypatch.delenv(FROZEN_VERSION_VARIABLE, raising=False)
        monkeypatch.setattr(version_utils, "_project_root", lambda: project)

        version = get_git_version()

        assert version == "unknown", f"{project} has no .git and no VERSION: the tag of the repository around it must not be reported, got {version!r}"


class TestBlankOrUnreadableVersionFile:
    """A VERSION file that is blank or cannot be read counts as absent, with or without a checkout."""

    @pytest.mark.parametrize("checkout", [False, True], ids=["no-dot-git", "dot-git-and-git-failing"])
    def test_a_blank_version_file_counts_as_absent(self, project, git, checkout):
        if checkout:
            _mark_checkout(project, "folder")
        (project / "VERSION").write_text(" \n\t\n")

        version = get_git_version()

        assert len(git.calls) == (1 if checkout else 0), f"git describe runs only with .git: recorded {git.calls}"
        assert version == "unknown", f"a blank VERSION file counts as absent: got {version!r}"

    @pytest.mark.parametrize("checkout", [False, True], ids=["no-dot-git", "dot-git-and-git-failing"])
    def test_an_unreadable_version_file_counts_as_absent(self, project, git, checkout):
        """VERSION is a folder: reading it fails, and the answer is "unknown", not an error."""
        if checkout:
            _mark_checkout(project, "folder")
        (project / "VERSION").mkdir()

        version = get_git_version()

        assert len(git.calls) == (1 if checkout else 0), f"git describe runs only with .git: recorded {git.calls}"
        assert version == "unknown", f"a VERSION that cannot be read counts as absent: got {version!r}"


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

    def test_git_describe_runs_in_repository_root(self, monkeypatch, fresh_version_cache):
        assert (REPO_ROOT / "dev.py").is_file() and (REPO_ROOT / "backend" / "app").is_dir(), f"{REPO_ROOT} is not the repository root: this test file has moved"
        assert os.path.lexists(REPO_ROOT / ".git"), f"Precondition: {REPO_ROOT} must be a checkout (.git as a folder or a file): git describe runs only there"
        monkeypatch.delenv(FROZEN_VERSION_VARIABLE, raising=False)
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
        # get_git_version asks the config package for LF_APP_VERSION first: the image has the package
        # (COPY backend/ ./backend/), so this tree has it too. The child's environment below does not set it.
        config_package = platform_config.__name__.rpartition(".")[0]
        shutil.copytree(Path(platform_config.__file__).parent, app_root.joinpath(*config_package.split(".")), ignore=shutil.ignore_patterns("__pycache__"))
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
