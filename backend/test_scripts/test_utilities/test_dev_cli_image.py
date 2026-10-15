"""``dev.py`` inside the Docker image, which does not ship the tests (L, R2 P0, plan 35_devCliImage).

``.dockerignore`` drops ``backend/test_scripts/`` (``f32e460ca``, in 1.1.0). ``dev.py``,
though, registers the test runner while it builds its parser (``scripts.test_runner`` →
``_cli`` → ``_common.py``, which imports ``backend.test_scripts.test_db_config`` and
``test_utils``), and imports ``normalize_coverage_argv`` from ``scripts.test_runner._cli``
before ``parse_args``. In the image every ``python dev.py …`` therefore dies with
``ModuleNotFoundError: No module named 'backend.test_scripts'`` before reading its
arguments: ``--help``, user management (the password reset the login page sends the
administrator to), ``db`` and ``user init-settings`` are all unusable. Found by Q.

The module rebuilds the image's ``/app`` in ``tmp_path`` and runs that tree's ``dev.py``.
The tree is derived, not listed: the ``COPY`` lines of the ``Dockerfile``'s final stage
that take files from the build context, filtered by ``.dockerignore`` as Docker reads it.
Files are copied, not linked, because modules find the project from ``__file__``. The two
files ``./dev.py docker build`` generates (``VERSION``, ``requirements.txt``) get
placeholders; the outputs of other stages are left out: the interpreter running this test
stands in for the Python packages, and no command started here reads the frontend build
or the docs site. Each command runs in a subprocess with ``sys.executable``, ``cwd`` at the
tree's root and a container's environment rather than the runner's: only ``PATH`` is
inherited, ``HOME`` and ``TMPDIR`` are private, and ``LIBREFOLIO_DATA_DIR`` is
``backend/data/prod-docker`` inside the tree, where the ``Dockerfile`` and compose put it.

The contract:

* **IMG-001**, the premise: the tree has no ``backend/test_scripts``, nor the
  ``frontend/scripts`` and ``mkdocs_src/aphra-pipeline`` the other optional groups need;
  **IMG-001b**: nothing on the tree's import path supplies ``backend.test_scripts``
  either (a ``PYTHONPATH``, a ``.pth``, an editable install), or this module would prove
  nothing;
* **IMG-002**: ``dev.py --help`` exits 0 with argparse's usage and lists ``user`` and
  ``db`` among the commands it registered (its epilog names both in prose too, which does
  not count); **IMG-002b**: it lists ``test`` and ``i18n`` too, each entry saying "not
  available in this installation";
* **IMG-003**: ``dev.py user --help`` and ``dev.py db --help`` exit 0;
* **IMG-004**: ``dev.py test``, ``dev.py test api auth`` and ``dev.py test --help`` answer
  that the group is "not available in this installation", name ``backend/test_scripts``
  and exit 2;
* **IMG-005**: ``alembic upgrade head`` builds a fresh schema in the tree, at the path the
  tree's own settings resolve, which must lie inside its ``LIBREFOLIO_DATA_DIR``: checked
  before anything is created;
* **IMG-006**: the password reset path: ``user create``, ``user reset`` and ``user list``
  exit 0, the list shows the user, and the stored hash takes the new password and refuses
  the old one, which no exit code can prove;
* **IMG-006b**: a ``user`` command that fails exits 1: ``user reset`` of a user who does
  not exist prints ``❌`` and exits 1. It exited 0 whatever happened;
* **IMG-007**: likewise ``dev.py i18n audit`` names ``frontend/scripts`` and
  ``dev.py mkdocs translate`` names ``mkdocs_src/aphra-pipeline``, both exiting 2;
* **IMG-008**: the ``Dockerfile``'s ``HEALTHCHECK`` probes a literal port, the one the
  final ``CMD`` passes to uvicorn with ``--port``, which is also the port the healthcheck
  of service ``librefolio`` probes in ``docker-compose.yml`` (and in any other
  ``docker-compose*.yml`` giving it one); a failure quotes the lines it read.
  **IMG-008b** runs the same check on synthetic files, to show it can fail;
* **IMG-009**: on a database of its own, where the user it creates is checked to be the
  only active administrator, ``user demote`` and ``user deactivate`` refuse: exit 1, the
  "last active administrator" named, and ``user list`` still showing it 👑 and ✅. They
  used to succeed and leave the instance with nobody to administer it.
  **IMG-009b**, the other side of the guard: with other active administrators left, both
  commands succeed and exit 0;
* **IMG-010**: ``_ensure_shared_jwt_secret``, through which ``dev.py server`` gives every
  uvicorn worker the same JWT secret, run on plain dicts from the repository's ``dev.py``,
  no server started: a missing secret gets a fresh one (**IMG-010**), and so does an empty
  or blank one (**IMG-010b**), which used to survive (a ``JWT_SECRET=`` left in ``.env``,
  then each worker made its own secret and users were logged out at random); a set one is
  kept and nothing else changes (**IMG-010c**); every start gets a secret of its own
  (**IMG-010d**). With ``JWT_SECRET_FILE`` set, every worker reads the secret from that
  file: nothing is generated and the env is left as it is (**IMG-010e**), a blank
  ``JWT_SECRET`` beside it included, which the server ignores as unset (**IMG-010f**); an
  empty or blank ``JWT_SECRET_FILE`` names no file, so a fresh secret again (**IMG-010g**).
  The process environment is only read, to show it is left alone.
* **IMG-011**: ``user create`` gives the account the role it is asked for. With no ``--role``
  it still creates an active administrator, as it always did (**IMG-011**); ``--role admin``
  does the same (**IMG-011b**); ``--role user`` creates an active account that is not an
  administrator, even as the only account of an empty database, and ``user list`` shows it
  without 👑 (**IMG-011c**); any other role is refused by argparse itself — exit 2, "invalid
  choice" for ``--role`` — and nobody is created (**IMG-011d**);
* **IMG-012**: the internal commands behind it, run as the test runner and
  ``e2e/global-setup.ts`` run them, ``python scripts/user_cli.py <command> …``:
  ``create-user`` creates an active account that is not an administrator, even as the only
  account of an empty database, prints ``✅`` and exits 0 (**IMG-012**); with a password that
  breaks the rules, or a username already taken, it prints ``❌``, exits 1 and creates or
  changes nobody (**IMG-012b**); ``create-superuser``, which still creates the E2E
  administrators, keeps creating an active administrator (**IMG-012c**).
* **IMG-013**: ``dev.py --help`` lists ``backup`` among the commands it registered (its
  epilog names it in prose too, which does not count); **IMG-013b**: ``dev.py backup
  --help`` exits 0 with the usage of the group;
* **IMG-014**: on the image's database, ``backup create`` exits 0 and writes exactly one
  ``librefolio-backup-*.zip`` into ``backups/`` of the image's data directory, where
  ``docker compose exec librefolio python dev.py backup create`` leaves it, with no job
  folder left in ``backups/.jobs/``; the archive holds that database (a user this test
  created there, and its Alembic revision in the manifest), which no exit code can prove;
  ``backup inspect`` of the archive exits 0. **IMG-014b**: ``backup inspect`` of a file
  that does not exist prints ``❌`` and exits 1.

IMG-002b, IMG-004 and IMG-007 pin decision 1 of plan 35_devCliImage §0.1, IMG-008 its
decision 4: a group whose sources the image lacks stays listed and answers for itself,
instead of crashing or vanishing into argparse's "invalid choice". IMG-006b, IMG-009 and
IMG-010 pin the decisions of plan 34_accountAndIdReuse step 2 §0.1. IMG-011 and IMG-012 pin
backlog 38, item L12 (plan A3 of workstream A): ``user create`` mapped to ``create-superuser``
and so did the runner's ``_ensure_test_users`` and ``e2e/global-setup.ts`` for every E2E
user, so on an empty database the users meant to be ordinary were administrators; a
populated database hid it, because ``populate_mock_data.py`` creates them first with the
right role. IMG-013 and IMG-014 pin lot B1 of workstream B (plan 07_backupDocker §3.10): the
``backup`` group works in the image, as ``docker compose exec`` runs it. The messages are
English CLI output, not UI text, so the fragments above are the contract: "not available in
this installation", "last active administrator" and "invalid choice" (case aside), the
missing directory, the option argparse names, ``❌`` and ``✅``, nothing more. Roles are read
from the database itself: no exit code tells an administrator from an ordinary user.

"Without a traceback" means none of ``Traceback (most recent call last)``,
``ModuleNotFoundError`` and ``No module named`` in the combined output.

PURE for the runner: the tree, its databases, its backups and its environment are private to
``tmp_path``; the lane's database and server are never touched, nothing goes over the
network, nothing is written in the repository. IMG-010 loads the repository's ``dev.py``
into this process under a private name, and undoes the ``sys.path`` entries and the change
of directory its module-level code makes as soon as it has loaded.
"""

import importlib.util
import json
import os
import posixpath
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import uuid
import zipfile
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from backend.app.services.accounts.auth_service import verify_password
from backend.test_scripts.test_utils import print_info, print_section, print_success
from scripts.user_cli import validate_password

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
DOCKERIGNORE = PROJECT_ROOT / ".dockerignore"

#: Generous: these commands import the application, and a loaded parallel run is slow.
#: A hang still ends, and what it printed so far is reported.
CLI_TIMEOUT = 120

#: Where the Dockerfile's ENV and compose put LIBREFOLIO_DATA_DIR (/app/backend/data/prod-docker).
IMAGE_DATA_DIR = Path("backend") / "data" / "prod-docker"

#: Written by ``./dev.py docker build`` right before ``docker build``, never committed.
GENERATED = {
    "requirements.txt": "# placeholder: ./dev.py docker build generates it from Pipfile.lock\n",
    "VERSION": "v0.0.0-dev-cli-image\n",
}

#: What the final stage takes from other stages, and why the tree does without it.
STAGE_OUTPUTS = {
    "pybuilder": "the Python packages: the interpreter running this test stands in for them",
    "frontend": "the checked frontend build: static files that no command started here reads",
    "docs": "the documentation site: static files that no command started here reads",
}

COPY_FLAGS = ("--from=", "--chown=", "--chmod=", "--link")

#: Not in the image: the test runner's sources, and those of the other optional groups.
ABSENT_FROM_IMAGE = ("backend/test_scripts", "frontend/scripts", "mkdocs_src/aphra-pipeline")

CRASH_MARKERS = ("Traceback (most recent call last)", "ModuleNotFoundError", "No module named")

IMPORT_PROBE = "import importlib.util, backend; print(importlib.util.find_spec('backend.test_scripts')); print(list(backend.__path__))"
SETTINGS_PROBE = "from backend.app.config import get_settings; print(get_settings().DATABASE_URL)"

#: Both must satisfy scripts/user_cli.py::validate_password, which IMG-006 checks first.
OLD_PASSWORD = "Image#Old-2024"
NEW_PASSWORD = "Image#New-2025"

#: Decision 1 of the plan's §0.1 (the coordinator, 2026-10-08): a group whose sources the
#: image lacks stays listed, answers that it is not available, names what is missing, and
#: exits 2, whatever follows it on the command line.
NOT_AVAILABLE = "not available in this installation"
LISTED_AS_UNAVAILABLE = ["test", "i18n"]
TEST_GROUP_INVOCATIONS = [("test",), ("test", "api", "auth"), ("test", "--help")]
OTHER_UNAVAILABLE_GROUPS = [
    pytest.param(("i18n", "audit"), "frontend/scripts", id="i18n audit"),
    pytest.param(("mkdocs", "translate"), "mkdocs_src/aphra-pipeline", id="mkdocs translate"),
]

#: Decision 4: the compose file and service whose healthcheck the image's must agree with.
COMPOSE_FILE = "docker-compose.yml"
COMPOSE_SERVICE = "librefolio"
LOCAL_URL_PORT = re.compile(r"https?://(?:localhost|127\.0\.0\.1|\[::1\]):([^/\s'\"]+)")

#: Plan 34_accountAndIdReuse step 2 §0.1 (the developer, 2026-10-09): a failed ``user``
#: command exits 1, and the service refuses to demote or deactivate the last active
#: administrator with a message naming it.
FAILED = "❌"
LAST_ACTIVE_ADMIN = "last active administrator"
GUARDED_COMMANDS = ["demote", "deactivate"]

#: Backlog 38, item L12 (plan A3): ``user create … [--role {admin,user}]``, ``admin`` by
#: default as before, and the internal ``create-user`` for an ordinary account. An account
#: as the database holds it, ``account()`` below.
ADMIN_ACCOUNT = {"is_superuser": True, "is_active": True}
ORDINARY_ACCOUNT = {"is_superuser": False, "is_active": True}
SUCCEEDED = "✅"
INVALID_CHOICE = "invalid choice"
#: The internal CLI, as the runner and ``e2e/global-setup.ts`` run it, from the project root.
USER_CLI = "scripts/user_cli.py"
#: Breaks scripts/user_cli.py::validate_password: no uppercase letter, no digit, no special character.
WEAK_PASSWORD = "weakpassword"

#: ``dev.py`` loaded in this process, for its JWT secret helper; private, so the ``dev``
#: other tests import is not replaced.
DEVPY_MODULE = "_test_dev_cli_image_devpy"
#: Characters; ``secrets.token_urlsafe(64)``, what dev.py hands out, is 86 of them.
MIN_SECRET_LENGTH = 32

#: Lot B1 of workstream B (plan 07_backupDocker §3.10): ``dev.py backup``, as ``docker compose
#: exec librefolio python dev.py backup …`` runs it in the image. Without ``--output`` an
#: archive goes into ``backups/`` of the data directory; while it is built, the backup keeps
#: its state and work files in a job folder of ``backups/.jobs/``, which the command removes
#: once the archive is in place.
BACKUPS = "backups"
BACKUP_JOBS = ".jobs"
BACKUP_ARCHIVES = "librefolio-backup-*.zip"
#: An archive's database entry, and its manifest.
ARCHIVED_DATABASE = "sqlite/app.db"
ARCHIVE_MANIFEST = "manifest.json"


# ---------------------------------------------------------------------------
# The Dockerfile and .dockerignore, as Docker reads them
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Instruction:
    """One Dockerfile instruction, its continuation lines joined, with the lines it spans."""

    first: int
    last: int
    text: str

    @property
    def keyword(self) -> str:
        return self.text.split(maxsplit=1)[0].upper()

    @property
    def arguments(self) -> str:
        parts = self.text.split(maxsplit=1)
        return parts[1] if len(parts) > 1 else ""

    def __str__(self) -> str:
        lines = f"line {self.first}" if self.first == self.last else f"lines {self.first}-{self.last}"
        return f"Dockerfile {lines}: {self.text}"


def dockerfile_instructions(text: str) -> list[Instruction]:
    """The instructions in order: comments and blank lines dropped, inside a continuation too, as Docker does."""
    instructions: list[Instruction] = []
    pending, first = "", 0
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        first = first or number
        if line.endswith("\\"):
            pending += line[:-1].rstrip() + " "
        else:
            instructions.append(Instruction(first, number, pending + line))
            pending, first = "", 0
    return instructions


def final_stage(text: str) -> list[Instruction]:
    """The instructions after the last ``FROM``."""
    instructions = dockerfile_instructions(text)
    starts = [i for i, instruction in enumerate(instructions) if instruction.keyword == "FROM"]
    assert starts, "the Dockerfile has no FROM"
    return instructions[starts[-1] + 1 :]


def last(stage: list[Instruction], keyword: str) -> Instruction | None:
    found = [instruction for instruction in stage if instruction.keyword == keyword]
    return found[-1] if found else None


@dataclass(frozen=True)
class Copy:
    """One ``COPY`` of the final stage, its destination made absolute against the ``WORKDIR`` of the moment."""

    sources: tuple[str, ...]
    dest: str
    into_dir: bool
    stage: str | None


def parse_copy(args: str, workdir: str) -> Copy:
    tokens = shlex.split(args)
    flags = [token for token in tokens if token.startswith("--")]
    paths = [token for token in tokens if not token.startswith("--")]
    unsupported = [flag for flag in flags if not flag.startswith(COPY_FLAGS)] + [path for path in paths if re.search(r"[][*?$]", path)]
    if unsupported or len(paths) < 2:
        raise AssertionError(f"COPY {args}: syntax this test does not reproduce ({unsupported or 'no destination'})")
    *sources, dest = paths
    stage = next((flag.partition("=")[2] for flag in flags if flag.startswith("--from=")), None)
    return Copy(tuple(sources), posixpath.normpath(posixpath.join(workdir, dest)), dest.endswith("/") or len(sources) > 1, stage)


def image_copies(text: str) -> tuple[str, list[Copy]]:
    """The final stage's last ``WORKDIR``, where its ``CMD`` and ``docker compose exec`` run, and its ``COPY`` instructions."""
    workdir = "/"
    copies: list[Copy] = []
    for instruction in final_stage(text):
        if instruction.keyword == "WORKDIR":
            workdir = posixpath.normpath(posixpath.join(workdir, instruction.arguments))
        elif instruction.keyword == "COPY":
            copies.append(parse_copy(instruction.arguments, workdir))
        elif instruction.keyword == "ADD":
            raise AssertionError(f"the final stage uses ADD, which this test does not reproduce: {instruction}")
    return workdir, copies


def glob_regex(pattern: str) -> re.Pattern[str]:
    """Docker's glob: ``*`` and ``?`` stay within one path segment, ``**`` spans any number of them."""
    regex, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            i += 2
            if pattern.startswith("/", i):
                i += 1
            regex += ".*" if i == len(pattern) else "(?:.*/)?"
        elif pattern[i] in "*?":
            regex += "[^/]*" if pattern[i] == "*" else "[^/]"
            i += 1
        else:
            regex += re.escape(pattern[i])
            i += 1
    return re.compile(regex)


class DockerIgnore:
    """``.dockerignore``: the last matching line wins, ``!`` re-includes, and a line that matches a directory matches everything below it."""

    def __init__(self, text: str):
        self.rules: list[tuple[re.Pattern[str], bool]] = []
        self.reincludes_below_top_level = False
        for raw in text.splitlines():
            line = raw.strip()
            if line and not line.startswith("#"):
                self._add(line)

    def _add(self, line: str) -> None:
        negated = line.startswith("!")
        pattern = posixpath.normpath(line.removeprefix("!").strip()).lstrip("/")
        if "[" in pattern or "\\" in pattern:
            raise AssertionError(f".dockerignore line {line!r} uses syntax this test does not reproduce")
        self.rules.append((glob_regex(pattern), negated))
        # Without "/" or "**" a pattern matches a top-level name only, which a directory
        # shares with everything below it: such a "!" cannot re-include a path inside an
        # excluded directory, and leaves pruning safe.
        self.reincludes_below_top_level |= negated and ("/" in pattern or "**" in pattern)

    def excludes(self, path: str) -> bool:
        parts = path.split("/")
        candidates = ["/".join(parts[: depth + 1]) for depth in range(len(parts))]
        excluded = False
        for regex, negated in self.rules:
            if any(regex.fullmatch(candidate) for candidate in candidates):
                excluded = not negated
        return excluded

    def prunes(self, directory: str) -> bool:
        """Whether nothing below ``directory`` can reach the image, so the walk need not enter it."""
        return self.excludes(directory) and not self.reincludes_below_top_level


# ---------------------------------------------------------------------------
# The image tree
# ---------------------------------------------------------------------------


def copy_file(origin: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(origin, destination, follow_symlinks=False)
    except FileNotFoundError:
        # Deleted between the walk and the copy, as the runner does with
        # scripts/test_runner/.run_cache.json: an image built a moment later would not
        # have it either.
        return


def copy_context_dir(name: str, target: Path, ignore: DockerIgnore) -> None:
    """The contents of the context directory ``name`` into ``target``, minus what ``.dockerignore`` drops."""
    top = PROJECT_ROOT / name
    for dirpath, dirnames, filenames in os.walk(top):
        here = Path(dirpath)
        context = here.relative_to(PROJECT_ROOT).as_posix()
        dirnames[:] = [dirname for dirname in dirnames if not ignore.prunes(f"{context}/{dirname}")]
        if not ignore.excludes(context):
            (target / here.relative_to(top)).mkdir(parents=True, exist_ok=True)
        for filename in filenames:
            if not ignore.excludes(f"{context}/{filename}"):
                copy_file(here / filename, target / here.relative_to(top) / filename)


def place(source: str, target: Path, into_dir: bool, ignore: DockerIgnore) -> None:
    """One context source of a ``COPY``, laid out as Docker does: a directory's contents into ``target``, a file into it or onto it."""
    name = source.rstrip("/")
    if name in GENERATED:
        destination = target / name if into_dir else target
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(GENERATED[name], encoding="utf-8")
        return
    origin = PROJECT_ROOT / name
    if not origin.exists() or ignore.excludes(name):
        raise AssertionError(f"COPY {source}: not in the build context (missing, or excluded by .dockerignore), so the image build would fail")
    if origin.is_dir():
        copy_context_dir(name, target, ignore)
    else:
        copy_file(origin, target / origin.name if into_dir else target)


def build_image_tree(app: Path) -> list[str]:
    """Rebuild in ``app`` what the final stage copies into its ``WORKDIR`` from the build context; return what was left out, and why."""
    ignore = DockerIgnore(DOCKERIGNORE.read_text(encoding="utf-8"))
    workdir, copies = image_copies(DOCKERFILE.read_text(encoding="utf-8"))
    app.mkdir(parents=True)
    left_out = []
    for copy in copies:
        if copy.stage is not None:
            if copy.stage not in STAGE_OUTPUTS:
                raise AssertionError(f"the final stage copies {copy.dest} from stage {copy.stage!r}, which this test neither rebuilds nor knows to be irrelevant: reproduce it, or add it to STAGE_OUTPUTS with the reason")
            left_out.append(f"{copy.dest}, {STAGE_OUTPUTS[copy.stage]}")
            continue
        relative = posixpath.relpath(copy.dest, workdir)
        if relative.split("/")[0] == "..":
            left_out.append(f"{copy.dest}, outside {workdir} where dev.py runs")
            continue
        for source in copy.sources:
            place(source, app / relative, copy.into_dir, ignore)
    return left_out


def image_env(root: Path, data_dir: Path) -> dict[str, str]:
    """A container's environment, not the runner's: only ``PATH`` (and Windows' ``SYSTEMROOT``) is inherited.

    The runner exports lane and test-mode variables (``LIBREFOLIO_TEST_MODE``,
    ``LIBREFOLIO_TEST_DATA_DIR``, ``TEST_PORT``), coverage hooks (``COVERAGE_PROCESS_START``,
    which a ``.pth`` of the venv honours) and a ``PYTHONPATH``, and ``pipenv run`` may load
    a ``.env``: any of them could point the tree at the lane's database, or put the
    repository's ``backend`` on its import path and hide the defect. ``HOME`` and
    ``TMPDIR`` are private, so whatever the tree runs writes under ``tmp_path``.
    """
    home, tmp = root / "home", root / "tmp"
    home.mkdir(exist_ok=True)
    tmp.mkdir(exist_ok=True)
    env = {name: os.environ[name] for name in ("PATH", "SYSTEMROOT") if name in os.environ}
    env.update(HOME=str(home), TMPDIR=str(tmp), LIBREFOLIO_DATA_DIR=str(data_dir), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    return env


@dataclass(frozen=True)
class ImageTree:
    root: Path  # this module's tmp dir: everything it writes is below it
    app: Path  # the image's WORKDIR, rebuilt
    data_dir: Path  # LIBREFOLIO_DATA_DIR, inside the tree as in the image
    env: dict[str, str]
    left_out: tuple[str, ...]


@pytest.fixture(scope="module")
def image(tmp_path_factory: pytest.TempPathFactory) -> Iterator[ImageTree]:
    root = tmp_path_factory.mktemp("dev_cli_image")
    app = root / "app"
    left_out = build_image_tree(app)
    assert (app / "dev.py").is_file(), "the image tree has no dev.py: does the Dockerfile still copy it into its WORKDIR?"
    data_dir = app / IMAGE_DATA_DIR
    yield ImageTree(root=root, app=app, data_dir=data_dir, env=image_env(root, data_dir), left_out=tuple(left_out))
    # ~35 MB of copies; every failure message already carries the output it is about.
    shutil.rmtree(app, ignore_errors=True)


# ---------------------------------------------------------------------------
# Running the tree
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Run:
    argv: tuple[str, ...]
    returncode: int
    output: str

    def __str__(self) -> str:
        return f"`python {shlex.join(self.argv)}` in the image tree exited {self.returncode}, output:\n{self.output}"


def run_python(image: ImageTree, *argv: str, env: dict[str, str] | None = None) -> Run:
    """``python <argv>`` at the tree's root, as ``docker compose exec`` runs it in ``/app``: stdout and stderr combined, in order."""
    try:
        done = subprocess.run([sys.executable, *argv], cwd=image.app, env=image.env if env is None else env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=CLI_TIMEOUT, check=False)
    except subprocess.TimeoutExpired as exc:
        partial = exc.output.decode("utf-8", "replace") if isinstance(exc.output, bytes) else exc.output or ""
        pytest.fail(f"`python {shlex.join(argv)}` in the image tree did not end within {CLI_TIMEOUT}s and was killed, output so far:\n{partial}")
    return Run(argv, done.returncode, done.stdout)


def run_dev(image: ImageTree, *argv: str, env: dict[str, str] | None = None) -> Run:
    return run_python(image, "dev.py", *argv, env=env)


def assert_no_crash(run: Run) -> None:
    found = [marker for marker in CRASH_MARKERS if marker in run.output]
    assert not found, f"crashed ({', '.join(found)}): {run}"


def assert_succeeds(run: Run) -> None:
    assert_no_crash(run)
    assert run.returncode == 0, f"expected exit 0: {run}"


def assert_not_available(run: Run, missing: str) -> None:
    """Decision 1: the group answers for itself, neither crashing nor falling back on argparse's "invalid choice"."""
    assert_no_crash(run)
    assert "invalid choice" not in run.output, f"argparse rejected the group instead of the group answering: {run}"
    assert run.returncode == 2, f"expected exit 2: {run}"
    assert NOT_AVAILABLE in run.output.lower(), f"expected {NOT_AVAILABLE!r}: {run}"
    assert missing in run.output, f"expected the message to name what the image lacks, {missing}: {run}"


def indentation(line: str) -> int:
    return len(line) - len(line.lstrip())


def command_entries(help_text: str) -> dict[str, str]:
    """The commands argparse lists under ``positional arguments:``, each with its help text unwrapped.

    The section holds the ``command`` placeholder, its choices one indentation level
    deeper, and the wrapped tails of their help texts deeper still. Only those choices are
    the parser's own: the epilog names commands in prose too, and a wrapped tail that
    happens to start with ``user`` is not a command.
    """
    _, heading, rest = help_text.partition("positional arguments:")
    lines = [line for line in rest.split("\n\n", 1)[0].splitlines() if line.strip()] if heading else []
    levels = sorted({indentation(line) for line in lines})
    if len(levels) < 2:
        return {}
    entries: dict[str, list[str]] = {}
    for line in lines:
        depth = indentation(line)
        if depth == levels[1]:
            name, *words = line.split()
            entries[name] = words
        elif depth > levels[1] and entries:
            entries[next(reversed(entries))] += line.split()
    return {name: " ".join(words) for name, words in entries.items()}


@pytest.fixture(scope="module")
def top_help(image: ImageTree) -> Run:
    """``dev.py --help`` in the tree, run once for the tests that read it."""
    return run_dev(image, "--help")


@dataclass(frozen=True)
class Database:
    """A database where the tree's own settings put it for a ``LIBREFOLIO_DATA_DIR``, with its schema."""

    path: Path
    env: dict[str, str]  # the tree's environment, pointed at this database
    upgrade: Run


def create_database(image: ImageTree, data_dir: Path) -> Database:
    """Ask the tree where ``data_dir`` puts its database, refuse anything outside this module's tmp dir, then build the schema there with alembic."""
    env = {**image.env, "LIBREFOLIO_DATA_DIR": str(data_dir)}
    probe = run_python(image, "-c", SETTINGS_PROBE, env=env)
    assert_succeeds(probe)
    lines = probe.output.strip().splitlines()
    url = lines[-1].strip() if lines else ""
    assert url.startswith("sqlite:///"), f"not a SQLite URL: {probe}"
    path = Path(url.removeprefix("sqlite:///")).resolve()
    if not path.is_relative_to(image.root):
        pytest.fail(f"the image tree resolves its database to {path}, outside this module's tmp dir {image.root}: refusing to create a schema there")
    assert path.is_relative_to(data_dir), f"the tree resolves its database to {path}, not inside LIBREFOLIO_DATA_DIR={data_dir}"
    path.parent.mkdir(parents=True, exist_ok=True)
    upgrade = run_python(image, "-m", "alembic", "-c", "backend/alembic.ini", "-x", f"sqlalchemy.url={url}", "upgrade", "head", env=env)
    assert_succeeds(upgrade)
    return Database(path=path, env=env, upgrade=upgrade)


@pytest.fixture(scope="module")
def image_db(image: ImageTree) -> Database:
    """The database where the image keeps it (``LIBREFOLIO_DATA_DIR`` as the Dockerfile and compose set it), shared by the password-reset tests."""
    return create_database(image, image.data_dir)


@pytest.fixture
def fresh_db(image: ImageTree) -> Iterator[Database]:
    """A database of its own, for a test that must know every user in it."""
    data_dir = image.root / "databases" / uuid.uuid4().hex[:12]
    yield create_database(image, data_dir)
    shutil.rmtree(data_dir, ignore_errors=True)


def unique_username() -> str:
    return f"img_{uuid.uuid4().hex[:12]}"


def stored_password_hash(db_path: Path, username: str) -> str:
    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute("SELECT hashed_password FROM users WHERE username = ?", (username,)).fetchone()
    assert row is not None, f"{username!r} is not in {db_path}"
    return row[0]


def active_admins(db_path: Path) -> list[str]:
    """The usernames of the active administrators, oldest first, read from the database itself."""
    with closing(sqlite3.connect(db_path)) as conn:
        return [name for (name,) in conn.execute("SELECT username FROM users WHERE is_superuser AND is_active ORDER BY id")]


def account(db_path: Path, username: str) -> dict[str, bool] | None:
    """``is_superuser`` and ``is_active`` of ``username``, read from the database itself; None when it is not there."""
    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute("SELECT is_superuser, is_active FROM users WHERE username = ?", (username,)).fetchone()
    return None if row is None else {"is_superuser": bool(row[0]), "is_active": bool(row[1])}


def usernames(db_path: Path) -> list[str]:
    """Every username in the database, oldest first."""
    with closing(sqlite3.connect(db_path)) as conn:
        return [name for (name,) in conn.execute("SELECT username FROM users ORDER BY id")]


def user_row(listed: Run, username: str) -> str:
    """The line of ``user list`` whose username column is ``username``."""
    rows = [line for line in listed.output.splitlines() if username in line.split()]
    assert len(rows) == 1, f"user list must show {username} exactly once: {listed}"
    return rows[0]


def job_folders(backups: Path) -> set[Path]:
    """The folders in ``backups/.jobs/``: a backup's job folder while it is built, none once its command has ended."""
    jobs = backups / BACKUP_JOBS
    return {path for path in jobs.iterdir() if path.is_dir()} if jobs.is_dir() else set()


def alembic_revision(db_path: Path) -> str | None:
    """The revision ``alembic_version`` records, read from the database itself; None unless it records exactly one."""
    with closing(sqlite3.connect(db_path)) as conn:
        rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    return rows[0][0] if len(rows) == 1 else None


@pytest.fixture(scope="module")
def devpy() -> Iterator[ModuleType]:
    """The repository's ``dev.py`` as a module, loaded under a private name with its import-time side effects undone.

    Its module-level code inserts two ``sys.path`` entries and changes directory to the
    project root: both are restored as soon as it has loaded, before any test runs.
    """
    cwd, path = Path.cwd(), list(sys.path)
    spec = importlib.util.spec_from_file_location(DEVPY_MODULE, PROJECT_ROOT / "dev.py")
    assert spec is not None and spec.loader is not None, f"cannot load {PROJECT_ROOT / 'dev.py'} as a module"
    module = importlib.util.module_from_spec(spec)
    sys.modules[DEVPY_MODULE] = module
    try:
        try:
            spec.loader.exec_module(module)
        finally:
            os.chdir(cwd)
            sys.path[:] = path
        yield module
    finally:
        sys.modules.pop(DEVPY_MODULE, None)


def ensure_secret(devpy: ModuleType, env: dict[str, str]) -> dict[str, str]:
    """Run the helper on ``env`` and return it, checking that the process environment was left alone."""
    before = dict(os.environ)
    devpy._ensure_shared_jwt_secret(env)
    assert dict(os.environ) == before, "_ensure_shared_jwt_secret changed os.environ: it must write into the env it is given"
    return env


def assert_usable_secret(secret: object, context: str = "") -> None:
    assert isinstance(secret, str) and len(secret.strip()) >= MIN_SECRET_LENGTH, f"not a usable JWT secret: {secret!r}{context}"


# ---------------------------------------------------------------------------
# The HEALTHCHECK
# ---------------------------------------------------------------------------


def command_tokens(arguments: str) -> list[str]:
    """A ``CMD``'s words: a JSON list in exec form, shell words otherwise (which is also how Docker reads a malformed list)."""
    try:
        tokens = json.loads(arguments)
    except ValueError:
        return shlex.split(arguments)
    return [str(token) for token in tokens] if isinstance(tokens, list) else shlex.split(arguments)


def cmd_port(stage: list[Instruction]) -> str | None:
    """The ``--port`` the final ``CMD`` passes to uvicorn."""
    cmd = last(stage, "CMD")
    tokens = command_tokens(cmd.arguments) if cmd else []
    for i, token in enumerate(tokens):
        if token == "--port" and i + 1 < len(tokens):
            return tokens[i + 1]
        if token.startswith("--port="):
            return token.partition("=")[2]
    return None


def compose_healthcheck(text: str) -> str | None:
    """The healthcheck test of service ``librefolio``, on one line, or None."""
    services = (yaml.safe_load(text) or {}).get("services") or {}
    test = ((services.get(COMPOSE_SERVICE) or {}).get("healthcheck") or {}).get("test")
    if not test:
        return None
    return json.dumps(test) if isinstance(test, list) else str(test)


def port_mismatches(where: str, found: str, port: str) -> list[str]:
    """What is wrong with the localhost ports a healthcheck probes, against the port the CMD binds."""
    probed = LOCAL_URL_PORT.findall(found)
    if not probed:
        return [f"{where} probes no localhost URL with an explicit port"]
    return [f"{where} probes localhost:{other}, {'another port' if other.isdigit() else 'not a literal number'}, while the CMD binds --port {port}" for other in probed if other != port]


def compose_violations(port: str, composes: dict[str, str]) -> list[str]:
    violations = [] if compose_healthcheck(composes.get(COMPOSE_FILE, "")) else [f"{COMPOSE_FILE} gives service {COMPOSE_SERVICE} no healthcheck to agree with"]
    for file, text in composes.items():
        found = compose_healthcheck(text)
        if found is not None:
            violations += port_mismatches(f"the healthcheck of {COMPOSE_SERVICE} in {file}", found, port)
    return violations


def healthcheck_violations(dockerfile_text: str, composes: dict[str, str]) -> list[str]:
    """Where the image's ``HEALTHCHECK``, or a compose healthcheck of ``librefolio``, disagrees with the literal port the final ``CMD`` binds."""
    stage = final_stage(dockerfile_text)
    port = cmd_port(stage)
    if port is None or not port.isdigit():
        return [f"the final CMD passes no literal --port to uvicorn (found {port!r})"]
    check = last(stage, "HEALTHCHECK")
    violations = port_mismatches("the Dockerfile HEALTHCHECK", check.arguments, port) if check else ["the final stage has no HEALTHCHECK"]
    return violations + compose_violations(port, composes)


def healthcheck_sources(dockerfile_text: str, composes: dict[str, str]) -> list[str]:
    """The lines the check reads, as found: they go into its failure message."""
    stage = final_stage(dockerfile_text)
    found = [str(instruction) for instruction in (last(stage, "HEALTHCHECK"), last(stage, "CMD")) if instruction is not None]
    return found + [f"{file}, service {COMPOSE_SERVICE}, healthcheck test: {test}" for file, text in composes.items() if (test := compose_healthcheck(text)) is not None]


SYNTHETIC_DOCKERFILE = """\
FROM python:3.13-slim AS builder
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9999/')"
FROM python:3.13-slim
WORKDIR /app
HEALTHCHECK --interval=30s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{probe}/api/v1/system/health')" || exit 1
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "6040"]
"""

SYNTHETIC_COMPOSE = """\
services:
  librefolio:
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:{probe}/api/v1/system/health')"]
"""

SYNTHETIC_COMPOSE_WITHOUT_HEALTHCHECK = """\
services:
  librefolio:
    image: librefolio:latest
"""


# ---------------------------------------------------------------------------
# IMG-001: the premise
# ---------------------------------------------------------------------------


class TestImageTree:
    @pytest.mark.parametrize("path", ABSENT_FROM_IMAGE, ids=["test_scripts", "frontend_scripts", "aphra_pipeline"])
    def test_lacks_what_the_image_lacks(self, image, path):
        """IMG-001: the tree is the image's /app: what .dockerignore drops, or the Dockerfile never copies, is not there."""
        print_section(f"IMG-001: no {path} in the image tree")

        assert not (image.app / path).exists(), f"{path} is in the image tree: the image ships it now (see .dockerignore and the Dockerfile's COPY lines), and this module's premise no longer holds"

        print_success(f"{path} is absent, as in the image")

    def test_test_scripts_cannot_be_imported(self, image):
        """IMG-001b: nothing on the tree's import path supplies backend.test_scripts."""
        print_section("IMG-001b: backend.test_scripts cannot be imported in the image tree")
        print_info("Left out of the tree: " + "; ".join(image.left_out))

        probe = run_python(image, "-c", IMPORT_PROBE)

        assert_succeeds(probe)
        spec, _, search_path = probe.output.strip().partition("\n")
        assert spec == "None", f"backend.test_scripts is importable in the image tree ({spec}), backend.__path__ = {search_path}: something outside the tree would hide the defect"
        print_success(f"not importable, backend.__path__ = {search_path}")


# ---------------------------------------------------------------------------
# IMG-002..IMG-004: help, and the test runner the image does not have
# ---------------------------------------------------------------------------


class TestHelp:
    def test_top_level_help_lists_user_and_db(self, top_help):
        """IMG-002: dev.py --help exits 0 with argparse's usage, and lists user and db among the commands it registered."""
        print_section("IMG-002: dev.py --help in the image")

        assert_succeeds(top_help)
        assert re.search(r"^usage: dev\.py\b", top_help.output, re.M), f"no argparse usage line: {top_help}"
        listed = command_entries(top_help.output)
        assert {"user", "db"} <= listed.keys(), f"user and db must be among the registered commands, listed: {sorted(listed)}; {top_help}"
        print_success(f"exit 0, commands: {', '.join(sorted(listed))}")

    @pytest.mark.parametrize("group", LISTED_AS_UNAVAILABLE)
    def test_top_level_help_lists_unavailable_group(self, top_help, group):
        """IMG-002b: dev.py --help still lists the group, and its entry says it is not available in this installation."""
        print_section(f"IMG-002b: dev.py --help lists {group} as not available")

        assert_succeeds(top_help)
        listed = command_entries(top_help.output)

        assert group in listed, f"{group} is not among the registered commands, listed: {sorted(listed)}; {top_help}"
        assert NOT_AVAILABLE in listed[group].lower(), f"the entry of {group} does not say {NOT_AVAILABLE!r}: {listed[group]!r}; {top_help}"
        print_success(f"{group}: {listed[group]}")

    @pytest.mark.parametrize("group", ["user", "db"])
    def test_group_help(self, image, group):
        """IMG-003: dev.py user --help and dev.py db --help exit 0."""
        print_section(f"IMG-003: dev.py {group} --help in the image")

        run = run_dev(image, group, "--help")

        assert_succeeds(run)
        assert re.search(rf"^usage: dev\.py {group}\b", run.output, re.M), f"not the help of the {group} group: {run}"
        print_success(f"dev.py {group} --help: exit 0")


class TestTestRunnerIsAbsent:
    @pytest.mark.parametrize("argv", TEST_GROUP_INVOCATIONS, ids=[" ".join(argv) for argv in TEST_GROUP_INVOCATIONS])
    def test_says_not_available(self, image, argv):
        """IMG-004: without backend/test_scripts, dev.py test answers that it is not available, names it, and exits 2, whatever follows."""
        command = " ".join(argv)
        print_section(f"IMG-004: dev.py {command} in the image")

        run = run_dev(image, *argv)

        assert_not_available(run, "backend/test_scripts")
        print_success(f"dev.py {command}: not available, backend/test_scripts named, exit 2")


# ---------------------------------------------------------------------------
# IMG-005..IMG-006b: the password reset path, on a fresh database, and a failed command
# ---------------------------------------------------------------------------


class TestPasswordReset:
    def test_schema_is_built_in_the_tree(self, image_db):
        """IMG-005: alembic builds a fresh schema in the tree, where its settings resolve the database inside LIBREFOLIO_DATA_DIR."""
        print_section("IMG-005: a fresh schema in the image tree")

        with closing(sqlite3.connect(image_db.path)) as conn:
            tables = {name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}

        assert "users" in tables, f"no users table in {image_db.path} after {image_db.upgrade}"
        print_success(f"schema at {image_db.path}")

    def test_create_reset_and_list(self, image, image_db):
        """IMG-006: user create, reset and list exit 0, the list shows the user, and the stored hash takes the new password, not the old one."""
        print_section("IMG-006: user create / reset / list in the image")
        for password in (OLD_PASSWORD, NEW_PASSWORD):
            valid, errors = validate_password(password)
            assert valid, f"test bug: {password!r} breaks the CLI's password rules: {errors}"
        name = unique_username()
        email = f"{name}@example.com"

        assert_succeeds(run_dev(image, "user", "create", name, email, OLD_PASSWORD, env=image_db.env))
        assert_succeeds(run_dev(image, "user", "reset", name, NEW_PASSWORD, env=image_db.env))
        listed = run_dev(image, "user", "list", env=image_db.env)
        assert_succeeds(listed)

        assert any(name in line and email in line for line in listed.output.splitlines()), f"user list does not show {name} <{email}>: {listed}"
        stored = stored_password_hash(image_db.path, name)
        assert verify_password(NEW_PASSWORD, stored), f"the stored hash of {name} refuses the new password: user reset exited 0 without resetting it"
        assert not verify_password(OLD_PASSWORD, stored), f"the stored hash of {name} still takes the old password"
        print_success(f"{name}: created, reset and listed; the new password verifies, the old one does not")

    def test_failed_command_exits_1(self, image, image_db):
        """IMG-006b: user reset of a user who does not exist reports it with ❌ and exits 1, not 0."""
        print_section("IMG-006b: user reset of an unknown user in the image")
        name = unique_username()

        run = run_dev(image, "user", "reset", name, NEW_PASSWORD, env=image_db.env)

        assert_no_crash(run)
        assert FAILED in run.output, f"expected the failure to be reported with {FAILED}: {run}"
        assert run.returncode == 1, f"a failed user command must exit 1: {run}"
        print_success(f"user reset {name}: {FAILED}, exit 1")


# ---------------------------------------------------------------------------
# IMG-007: the other groups the image cannot run say so too
# ---------------------------------------------------------------------------


class TestUnavailableGroups:
    @pytest.mark.parametrize(("argv", "missing"), OTHER_UNAVAILABLE_GROUPS)
    def test_says_not_available(self, image, argv, missing):
        """IMG-007: the group answers that it is not available in this installation, names what the image lacks, and exits 2."""
        command = " ".join(argv)
        print_section(f"IMG-007: dev.py {command} in the image")

        run = run_dev(image, *argv)

        assert_not_available(run, missing)
        print_success(f"dev.py {command}: not available, {missing} named, exit 2")


# ---------------------------------------------------------------------------
# IMG-008: the HEALTHCHECK probes the port the CMD binds
# ---------------------------------------------------------------------------


class TestHealthcheck:
    def test_probes_the_port_the_cmd_binds(self):
        """IMG-008: the Dockerfile's HEALTHCHECK probes a literal port, the CMD's --port, which compose's healthcheck probes too."""
        print_section("IMG-008: the image's HEALTHCHECK probes the CMD's port")
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        composes = {path.name: path.read_text(encoding="utf-8") for path in sorted(PROJECT_ROOT.glob("docker-compose*.yml"))}

        violations = healthcheck_violations(dockerfile, composes)

        found = "\n".join(f"  {line}" for line in healthcheck_sources(dockerfile, composes))
        assert not violations, "\n".join(violations) + f"\nas found:\n{found}"
        print_success(f"the HEALTHCHECK, the CMD and {', '.join(composes)} agree on --port {cmd_port(final_stage(dockerfile))}")

    @pytest.mark.parametrize(
        ("image_probe", "compose_probe", "passes"),
        [("6040", "6040", True), ("${PORT}", "6040", False), ("6041", "6040", False), ("6040", "6041", False), ("6040", None, False)],
        ids=["agreed", "image-probes-a-variable", "image-probes-another-port", "compose-probes-another-port", "compose-has-no-healthcheck"],
    )
    def test_the_check_can_fail(self, image_probe, compose_probe, passes):
        """IMG-008b: the same check on synthetic files: only the final stage counts, and any disagreement is reported."""
        print_section(f"IMG-008b: HEALTHCHECK on {image_probe}, compose on {compose_probe}")
        dockerfile = SYNTHETIC_DOCKERFILE.replace("{probe}", image_probe)
        compose = SYNTHETIC_COMPOSE.replace("{probe}", compose_probe) if compose_probe else SYNTHETIC_COMPOSE_WITHOUT_HEALTHCHECK

        violations = healthcheck_violations(dockerfile, {COMPOSE_FILE: compose})

        assert (not violations) is passes, f"expected {'no violation' if passes else 'a violation'}, got: {violations}"
        print_success(f"violations: {violations or 'none'}")


# ---------------------------------------------------------------------------
# IMG-009: the last active administrator stays, through the CLI
# ---------------------------------------------------------------------------


class TestLastActiveAdministrator:
    @pytest.mark.parametrize("command", GUARDED_COMMANDS)
    def test_refuses_to_remove_the_last_active_admin(self, image, fresh_db, command):
        """IMG-009: user demote / deactivate of the only active administrator exit 1 naming the last active administrator, and change nothing."""
        print_section(f"IMG-009: user {command} of the last active administrator, in the image")
        name = unique_username()
        assert_succeeds(run_dev(image, "user", "create", name, f"{name}@example.com", OLD_PASSWORD, env=fresh_db.env))
        assert active_admins(fresh_db.path) == [name], f"premise: {name} must be the only active administrator of its fresh database"

        run = run_dev(image, "user", command, name, env=fresh_db.env)
        listed = run_dev(image, "user", "list", env=fresh_db.env)

        assert_no_crash(run)
        assert_succeeds(listed)
        row = user_row(listed, name)
        assert run.returncode == 1, f"user {command} of the last active administrator must fail with exit 1: {run}\nuser list afterwards: {row}"
        assert LAST_ACTIVE_ADMIN in run.output.lower(), f"expected {LAST_ACTIVE_ADMIN!r}: {run}"
        assert "👑" in row and "✅" in row, f"{name} must still be an active administrator (👑, ✅) after the refused {command}: {row}"
        assert active_admins(fresh_db.path) == [name], f"the refused {command} changed the database"
        print_success(f"user {command} {name}: refused, exit 1, still 👑 and ✅")

    def test_lets_an_admin_go_while_another_stays(self, image, fresh_db):
        """IMG-009b: with other active administrators left, user demote and user deactivate succeed and exit 0."""
        print_section("IMG-009b: user demote / deactivate with other active administrators, in the image")
        names = [unique_username() for _ in range(3)]
        for name in names:
            assert_succeeds(run_dev(image, "user", "create", name, f"{name}@example.com", OLD_PASSWORD, env=fresh_db.env))
        assert active_admins(fresh_db.path) == names, "premise: the three users must be the active administrators of their fresh database"
        demoted, deactivated, remaining = names

        assert_succeeds(run_dev(image, "user", "demote", demoted, env=fresh_db.env))
        assert_succeeds(run_dev(image, "user", "deactivate", deactivated, env=fresh_db.env))
        listed = run_dev(image, "user", "list", env=fresh_db.env)

        assert_succeeds(listed)
        assert "👑" not in user_row(listed, demoted), f"{demoted} must no longer be an administrator: {listed}"
        assert "👑" in user_row(listed, deactivated) and "❌" in user_row(listed, deactivated), f"{deactivated} must be an inactive administrator (👑, ❌): {listed}"
        assert active_admins(fresh_db.path) == [remaining], f"only {remaining} must be left as an active administrator"
        print_success(f"{demoted} demoted, {deactivated} deactivated, {remaining} still an active administrator")


# ---------------------------------------------------------------------------
# IMG-010: one JWT secret for every uvicorn worker, even when .env leaves it empty
# ---------------------------------------------------------------------------


class TestSharedJwtSecret:
    """``cmd_server`` copies the environment for its workers and hands it to ``_ensure_shared_jwt_secret``.

    ``pipenv run`` loads ``.env`` into that environment, so ``JWT_SECRET=`` arrives as
    ``''``. ``setdefault`` kept it, ``auth_service`` (``os.environ.get("JWT_SECRET") or
    token_urlsafe(64)``) then gave each worker a secret of its own, and with several
    workers a token signed by one was refused by the next: users logged out at random.
    A value made of spaces is no better: it is truthy, so the workers would share it and
    sign every token with a blank key.
    """

    def test_missing_secret_gets_a_fresh_one(self, devpy):
        """IMG-010: no JWT_SECRET in the env: the helper writes a fresh one, long enough to sign tokens, and nothing else."""
        print_section("IMG-010: dev.py server, JWT_SECRET missing")

        env = ensure_secret(devpy, {})

        assert set(env) == {"JWT_SECRET"}, f"the helper must add JWT_SECRET and nothing else: {sorted(env)}"
        assert_usable_secret(env["JWT_SECRET"])
        print_success(f"a fresh secret of {len(env['JWT_SECRET'])} characters")

    @pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "spaces"])
    def test_blank_secret_counts_as_missing(self, devpy, blank):
        """IMG-010b: an empty or whitespace-only JWT_SECRET, as a bare `JWT_SECRET=` in .env gives, is replaced by a fresh secret."""
        print_section(f"IMG-010b: dev.py server, JWT_SECRET={blank!r}")

        env = ensure_secret(devpy, {"JWT_SECRET": blank})

        assert_usable_secret(env["JWT_SECRET"], f", kept from JWT_SECRET={blank!r}: a blank value must count as missing")
        print_success(f"{blank!r} replaced by a fresh secret of {len(env['JWT_SECRET'])} characters")

    def test_set_secret_is_kept(self, devpy):
        """IMG-010c: a non-blank JWT_SECRET is kept as is, and nothing else in the env changes."""
        print_section("IMG-010c: dev.py server, JWT_SECRET set")
        given = {"JWT_SECRET": "keep-me", "PORT": "6040"}

        env = ensure_secret(devpy, dict(given))

        assert env == given, f"a set JWT_SECRET must be kept and the rest left alone: {env}"
        print_success("kept")

    def test_every_start_gets_its_own_secret(self, devpy):
        """IMG-010d: two starts without a secret get two different ones: the fresh secret is made at each start, not once."""
        print_section("IMG-010d: dev.py server, a fresh secret at every start")

        first, second = ensure_secret(devpy, {}), ensure_secret(devpy, {})

        assert first["JWT_SECRET"] != second["JWT_SECRET"], "two starts got the same secret"
        print_success("two starts, two secrets")

    def test_secret_file_is_left_to_the_workers(self, devpy):
        """IMG-010e: JWT_SECRET_FILE set and no JWT_SECRET: every worker reads the file, so nothing is generated and the env is left as is."""
        print_section("IMG-010e: dev.py server, JWT_SECRET_FILE set")
        given = {"JWT_SECRET_FILE": "/run/secrets/jwt", "PORT": "6040"}

        env = ensure_secret(devpy, dict(given))

        assert env == given, f"with JWT_SECRET_FILE set the helper must not add a JWT_SECRET nor change anything: {env}"
        print_success("nothing generated, the file left to the workers")

    @pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "spaces"])
    def test_blank_secret_beside_a_secret_file_is_left_alone(self, devpy, blank):
        """IMG-010f: a blank JWT_SECRET beside JWT_SECRET_FILE: the server ignores it as unset and reads the file, so the env is left exactly as it is."""
        print_section(f"IMG-010f: dev.py server, JWT_SECRET={blank!r} and JWT_SECRET_FILE set")
        given = {"JWT_SECRET": blank, "JWT_SECRET_FILE": "/run/secrets/jwt", "PORT": "6040"}

        env = ensure_secret(devpy, dict(given))

        assert env == given, f"with JWT_SECRET_FILE set the helper must generate nothing and remove nothing, JWT_SECRET={blank!r} included: {env}"
        print_success(f"JWT_SECRET={blank!r} and JWT_SECRET_FILE left as they are")

    @pytest.mark.parametrize("blank", ["", "  "], ids=["empty", "spaces"])
    def test_blank_secret_file_variable_counts_as_missing(self, devpy, blank):
        """IMG-010g: an empty or blank JWT_SECRET_FILE names no file: a fresh secret, as without it, and the variable is left as it is."""
        print_section(f"IMG-010g: dev.py server, JWT_SECRET_FILE={blank!r}")

        env = ensure_secret(devpy, {"JWT_SECRET_FILE": blank})

        assert set(env) == {"JWT_SECRET", "JWT_SECRET_FILE"} and env["JWT_SECRET_FILE"] == blank, f"the helper must add JWT_SECRET and change nothing else: {env}"
        assert_usable_secret(env["JWT_SECRET"], f", with JWT_SECRET_FILE={blank!r}: a blank file variable must count as missing")
        print_success(f"a fresh secret of {len(env['JWT_SECRET'])} characters")


# ---------------------------------------------------------------------------
# IMG-011..IMG-012: the role of an account created from the command line (L12)
# ---------------------------------------------------------------------------


class TestAccountRole:
    """``dev.py user create`` made every account an administrator (backlog 38, item L12; plan A3).

    The command maps to ``user_cli.py create-superuser``, and so did the runner's
    ``_ensure_test_users`` and ``e2e/global-setup.ts`` for every E2E user: on an empty
    database the users meant to be ordinary were administrators, so a test of what an
    ordinary user may not do could pass for the wrong reason. The approved change:
    ``user create <username> <email> <password> [--role {admin,user}]``, ``admin`` by default
    as before, and an internal ``create-user`` for an ordinary account, which the runner and
    the global setup will use for the ordinary E2E users.

    The ordinary account is created as the only account of a fresh database: that is the
    case L12 is about. Every other case uses the module's database and a username of its own.
    """

    def test_create_without_a_role_makes_an_administrator(self, image, image_db):
        """IMG-011: user create with no --role still creates an active administrator: admin stays the default."""
        print_section("IMG-011: user create with no --role, in the image")
        name = unique_username()

        run = run_dev(image, "user", "create", name, f"{name}@example.com", OLD_PASSWORD, env=image_db.env)

        assert_succeeds(run)
        assert account(image_db.path, name) == ADMIN_ACCOUNT, f"with no --role, user create must still make an active administrator, as it always did: {account(image_db.path, name)}; {run}"
        print_success(f"{name}: an active administrator")

    def test_create_with_role_admin_makes_an_administrator(self, image, image_db):
        """IMG-011b: user create --role admin creates an active administrator."""
        print_section("IMG-011b: user create --role admin, in the image")
        name = unique_username()

        run = run_dev(image, "user", "create", name, f"{name}@example.com", OLD_PASSWORD, "--role", "admin", env=image_db.env)

        assert_succeeds(run)
        assert account(image_db.path, name) == ADMIN_ACCOUNT, f"--role admin must make an active administrator: {account(image_db.path, name)}; {run}"
        print_success(f"{name}: an active administrator")

    def test_create_with_role_user_makes_an_ordinary_account(self, image, fresh_db):
        """IMG-011c: user create --role user creates an active account that is not an administrator, even alone in an empty database, and user list shows it without 👑."""
        print_section("IMG-011c: user create --role user on an empty database, in the image")
        name = unique_username()
        assert usernames(fresh_db.path) == [], "premise: the fresh database has no account yet"

        run = run_dev(image, "user", "create", name, f"{name}@example.com", OLD_PASSWORD, "--role", "user", env=fresh_db.env)

        assert_succeeds(run)
        assert usernames(fresh_db.path) == [name], f"premise: {name} is the only account of its database"
        assert account(fresh_db.path, name) == ORDINARY_ACCOUNT, f"--role user must make an active account that is not an administrator, even the first one: {account(fresh_db.path, name)}; {run}"
        listed = run_dev(image, "user", "list", env=fresh_db.env)
        assert_succeeds(listed)
        row = user_row(listed, name)
        assert "👑" not in row and "✅" in row, f"user list must show {name} active (✅) and without 👑: {row}"
        print_success(f"{name}: an active ordinary account, alone in its database")

    def test_create_with_an_unknown_role_is_refused(self, image, image_db):
        """IMG-011d: user create --role owner is refused by argparse, as an invalid choice for --role: exit 2, and nobody is created."""
        print_section("IMG-011d: user create --role owner, in the image")
        name = unique_username()

        run = run_dev(image, "user", "create", name, f"{name}@example.com", OLD_PASSWORD, "--role", "owner", env=image_db.env)

        assert_no_crash(run)
        assert run.returncode == 2, f"an unknown role is an argparse error, exit 2: {run}"
        assert INVALID_CHOICE in run.output.lower() and "--role" in run.output, f"argparse must refuse the value of --role ({INVALID_CHOICE!r} for --role), not an option it does not know: {run}"
        assert account(image_db.path, name) is None, f"a refused role must create nobody, yet {name} is in the database: {account(image_db.path, name)}"
        print_success(f"--role owner: {INVALID_CHOICE}, exit 2, {name} not created")

    def test_internal_create_user_makes_an_ordinary_account(self, image, fresh_db):
        """IMG-012: user_cli.py create-user creates an active account that is not an administrator, even alone in an empty database, prints ✅ and exits 0."""
        print_section("IMG-012: user_cli.py create-user on an empty database, in the image")
        name = unique_username()
        assert usernames(fresh_db.path) == [], "premise: the fresh database has no account yet"

        run = run_python(image, USER_CLI, "create-user", name, f"{name}@example.com", OLD_PASSWORD, env=fresh_db.env)

        assert_succeeds(run)
        assert SUCCEEDED in run.output, f"expected the creation to be reported with {SUCCEEDED}: {run}"
        assert usernames(fresh_db.path) == [name], f"premise: {name} is the only account of its database"
        assert account(fresh_db.path, name) == ORDINARY_ACCOUNT, f"create-user must make an active account that is not an administrator, even the first one: {account(fresh_db.path, name)}; {run}"
        print_success(f"{name}: an active ordinary account, {SUCCEEDED}, exit 0")

    def test_internal_create_user_refuses_a_password_that_breaks_the_rules(self, image, image_db):
        """IMG-012b: user_cli.py create-user with a password that breaks the rules prints ❌, exits 1 and creates nobody."""
        print_section("IMG-012b: user_cli.py create-user with a weak password, in the image")
        valid, _ = validate_password(WEAK_PASSWORD)
        assert not valid, f"test bug: {WEAK_PASSWORD!r} satisfies the CLI's password rules"
        name = unique_username()

        run = run_python(image, USER_CLI, "create-user", name, f"{name}@example.com", WEAK_PASSWORD, env=image_db.env)

        assert_no_crash(run)
        assert FAILED in run.output, f"expected the refusal to be reported with {FAILED}: {run}"
        assert run.returncode == 1, f"a failed create-user must exit 1: {run}"
        assert account(image_db.path, name) is None, f"a refused password must create nobody, yet {name} is in the database"
        print_success(f"{name}: {FAILED}, exit 1, not created")

    def test_internal_create_user_refuses_a_username_already_taken(self, image, image_db):
        """IMG-012b: user_cli.py create-user of a username already taken prints ❌, exits 1, and the existing account keeps its role."""
        print_section("IMG-012b: user_cli.py create-user of a username already taken, in the image")
        name = unique_username()
        assert_succeeds(run_dev(image, "user", "create", name, f"{name}@example.com", OLD_PASSWORD, env=image_db.env))
        assert account(image_db.path, name) == ADMIN_ACCOUNT, f"premise: {name} exists as an active administrator"

        run = run_python(image, USER_CLI, "create-user", name, f"other-{name}@example.com", OLD_PASSWORD, env=image_db.env)

        assert_no_crash(run)
        assert FAILED in run.output, f"expected the refusal to be reported with {FAILED}: {run}"
        assert run.returncode == 1, f"a failed create-user must exit 1: {run}"
        assert account(image_db.path, name) == ADMIN_ACCOUNT, f"create-user must never change an existing account: {account(image_db.path, name)}"
        print_success(f"{name}: {FAILED}, exit 1, still an active administrator")

    def test_internal_create_superuser_still_makes_an_administrator(self, image, image_db):
        """IMG-012c: user_cli.py create-superuser, which still creates the E2E administrators, creates an active administrator, prints ✅ and exits 0."""
        print_section("IMG-012c: user_cli.py create-superuser, in the image")
        name = unique_username()

        run = run_python(image, USER_CLI, "create-superuser", name, f"{name}@example.com", OLD_PASSWORD, env=image_db.env)

        assert_succeeds(run)
        assert SUCCEEDED in run.output, f"expected the creation to be reported with {SUCCEEDED}: {run}"
        assert account(image_db.path, name) == ADMIN_ACCOUNT, f"create-superuser must make an active administrator: {account(image_db.path, name)}; {run}"
        print_success(f"{name}: an active administrator, {SUCCEEDED}, exit 0")


# ---------------------------------------------------------------------------
# IMG-013..IMG-014: the instance backup, from the image's command line (B1)
# ---------------------------------------------------------------------------


class TestBackup:
    """``dev.py backup`` in the image (lot B1 of workstream B, plan 07_backupDocker §3.10).

    What an administrator runs on a Docker install, ``docker compose exec librefolio python
    dev.py backup create``: the archive goes where the image keeps its data, and ``inspect``
    checks an archive against its manifest.
    """

    def test_top_level_help_lists_backup(self, top_help):
        """IMG-013: dev.py --help lists backup among the commands it registered."""
        print_section("IMG-013: dev.py --help lists backup, in the image")

        assert_succeeds(top_help)
        listed = command_entries(top_help.output)

        assert "backup" in listed, f"backup must be among the registered commands, listed: {sorted(listed)}; {top_help}"
        print_success(f"backup: {listed['backup']}")

    def test_group_help(self, image):
        """IMG-013b: dev.py backup --help exits 0 with the usage of the backup group."""
        print_section("IMG-013b: dev.py backup --help in the image")

        run = run_dev(image, "backup", "--help")

        assert_succeeds(run)
        assert re.search(r"^usage: dev\.py backup\b", run.output, re.M), f"not the help of the backup group: {run}"
        print_success("dev.py backup --help: exit 0")

    def test_create_then_inspect(self, image, image_db, tmp_path):
        """IMG-014: backup create on the image's database exits 0, writes exactly one archive into backups/ of its data directory, leaves no job folder, and the archive holds that database; backup inspect of it exits 0."""
        print_section("IMG-014: backup create, then backup inspect, on the image's database")
        backups = image.data_dir / BACKUPS
        archives_before, folders_before = set(backups.glob(BACKUP_ARCHIVES)), job_folders(backups)
        name = unique_username()
        assert_succeeds(run_dev(image, "user", "create", name, f"{name}@example.com", OLD_PASSWORD, env=image_db.env))

        created = run_dev(image, "backup", "create", env=image_db.env)

        assert_succeeds(created)
        written = set(backups.glob(BACKUP_ARCHIVES)) - archives_before
        assert len(written) == 1, f"backup create must write exactly one {BACKUP_ARCHIVES} into {backups}, it wrote {sorted(path.name for path in written)}: {created}"
        (archive,) = written
        left = job_folders(backups) - folders_before
        assert not left, f"backup create must remove its job folder from {backups / BACKUP_JOBS}, left: {sorted(path.name for path in left)}; {created}"
        archived_db = tmp_path / "archived-app.db"
        with zipfile.ZipFile(archive) as zf:
            manifest = json.loads(zf.read(ARCHIVE_MANIFEST))
            with zf.open(ARCHIVED_DATABASE) as source, archived_db.open("wb") as target:
                shutil.copyfileobj(source, target)
        assert name in usernames(archived_db), f"the archive must hold the image's database, with the user {name} this test created there: {archive}"
        assert manifest["alembic_revision"] == alembic_revision(image_db.path), f"the manifest must give the revision of the image's database, {alembic_revision(image_db.path)!r}: {manifest['alembic_revision']!r}"

        inspected = run_dev(image, "backup", "inspect", str(archive), env=image_db.env)

        assert_succeeds(inspected)
        print_success(f"{archive.name}: in {BACKUPS}/, no job folder left, {name} inside, inspect exit 0")

    def test_inspect_of_a_missing_file_exits_1(self, image):
        """IMG-014b: backup inspect of a file that does not exist reports it with ❌ and exits 1."""
        print_section("IMG-014b: backup inspect of a missing file, in the image")
        missing = image.root / f"{unique_username()}.zip"
        assert not missing.exists(), f"premise: {missing} must not exist"

        run = run_dev(image, "backup", "inspect", str(missing))

        assert_no_crash(run)
        assert FAILED in run.output, f"expected the missing file to be reported with {FAILED}: {run}"
        assert run.returncode == 1, f"backup inspect of a missing file must exit 1: {run}"
        print_success(f"backup inspect {missing.name}: {FAILED}, exit 1")
