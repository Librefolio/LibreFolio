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
  the old one. ``dev.py user`` exits 0 even when it prints ``❌``, so the exit codes alone
  would prove nothing;
* **IMG-007**: likewise ``dev.py i18n audit`` names ``frontend/scripts`` and
  ``dev.py mkdocs translate`` names ``mkdocs_src/aphra-pipeline``, both exiting 2;
* **IMG-008**: the ``Dockerfile``'s ``HEALTHCHECK`` probes a literal port, the one the
  final ``CMD`` passes to uvicorn with ``--port``, which is also the port the healthcheck
  of service ``librefolio`` probes in ``docker-compose.yml`` (and in any other
  ``docker-compose*.yml`` giving it one); a failure quotes the lines it read.
  **IMG-008b** runs the same check on synthetic files, to show it can fail.

IMG-002b, IMG-004 and IMG-007 pin decision 1 of the plan's §0.1, IMG-008 its decision 4:
a group whose sources the image lacks stays listed and answers for itself, instead of
crashing or vanishing into argparse's "invalid choice". Their messages are English CLI
output, not UI text, so the fragments above are the contract: "not available in this
installation" (case aside) and the missing directory, nothing more.

"Without a traceback" means none of ``Traceback (most recent call last)``,
``ModuleNotFoundError`` and ``No module named`` in the combined output.

PURE for the runner: the tree, its database and its environment are private to
``tmp_path``; the lane's database and server are never touched, nothing goes over the
network, nothing is written in the repository.
"""

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
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from backend.app.services.auth_service import verify_password
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


def run_python(image: ImageTree, *argv: str) -> Run:
    """``python <argv>`` at the tree's root, as ``docker compose exec`` runs it in ``/app``: stdout and stderr combined, in order."""
    try:
        done = subprocess.run([sys.executable, *argv], cwd=image.app, env=image.env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=CLI_TIMEOUT, check=False)
    except subprocess.TimeoutExpired as exc:
        partial = exc.output.decode("utf-8", "replace") if isinstance(exc.output, bytes) else exc.output or ""
        pytest.fail(f"`python {shlex.join(argv)}` in the image tree did not end within {CLI_TIMEOUT}s and was killed, output so far:\n{partial}")
    return Run(argv, done.returncode, done.stdout)


def run_dev(image: ImageTree, *argv: str) -> Run:
    return run_python(image, "dev.py", *argv)


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
class Schema:
    url: str
    path: Path
    upgrade: Run


@pytest.fixture(scope="module")
def image_db(image: ImageTree) -> Schema:
    """A fresh schema where the tree's own settings put the database, which must be inside the tree's data dir."""
    probe = run_python(image, "-c", SETTINGS_PROBE)
    assert_succeeds(probe)
    lines = probe.output.strip().splitlines()
    url = lines[-1].strip() if lines else ""
    assert url.startswith("sqlite:///"), f"not a SQLite URL: {probe}"
    path = Path(url.removeprefix("sqlite:///")).resolve()
    if not path.is_relative_to(image.root):
        pytest.fail(f"the image tree resolves its database to {path}, outside this module's tmp dir {image.root}: refusing to create a schema there")
    assert path.is_relative_to(image.data_dir), f"the tree resolves its database to {path}, not inside LIBREFOLIO_DATA_DIR={image.data_dir}"
    path.parent.mkdir(parents=True, exist_ok=True)
    upgrade = run_python(image, "-m", "alembic", "-c", "backend/alembic.ini", "-x", f"sqlalchemy.url={url}", "upgrade", "head")
    assert_succeeds(upgrade)
    return Schema(url=url, path=path, upgrade=upgrade)


def stored_password_hash(db_path: Path, username: str) -> str:
    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute("SELECT hashed_password FROM users WHERE username = ?", (username,)).fetchone()
    assert row is not None, f"{username!r} is not in {db_path}"
    return row[0]


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
# IMG-005..IMG-006: the password reset path, on a fresh database
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
        name = f"img_{uuid.uuid4().hex[:12]}"
        email = f"{name}@example.com"

        assert_succeeds(run_dev(image, "user", "create", name, email, OLD_PASSWORD))
        assert_succeeds(run_dev(image, "user", "reset", name, NEW_PASSWORD))
        listed = run_dev(image, "user", "list")
        assert_succeeds(listed)

        assert any(name in line and email in line for line in listed.output.splitlines()), f"user list does not show {name} <{email}>: {listed}"
        stored = stored_password_hash(image_db.path, name)
        assert verify_password(NEW_PASSWORD, stored), f"the stored hash of {name} refuses the new password: user reset exited 0 without resetting it"
        assert not verify_password(OLD_PASSWORD, stored), f"the stored hash of {name} still takes the old password"
        print_success(f"{name}: created, reset and listed; the new password verifies, the old one does not")


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
