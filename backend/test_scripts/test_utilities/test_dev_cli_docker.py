"""The Docker lot of the platform workstream (H, checkpoint CP7a): the image, the compose files and ``dev.py``'s docker commands.

Five items of plan ``01_platform`` change the image and the commands around it. A Docker run proves them together;
what needs no Docker is pinned here, statically or with stand-ins. The series continues ``test_dev_cli_image.py``
(IMG-001 to IMG-012).

* **P-4** (D11): a time zone saved under an old name (``Asia/Calcutta``, ``US/Eastern``) made the scheduler fall back
  to UTC in the image. ``zoneinfo`` reads the system's IANA database, the lock has no PyPI ``tzdata``, and Debian keeps
  the old names in ``tzdata-legacy``. **IMG-013**: the final image installs ``tzdata`` and ``tzdata-legacy`` with apt;
* **C-37**: the image has no test mode, yet it exposed 6041 and ``docker-compose.yml`` published
  ``${TEST_PORT:-6041}:6041``. **IMG-014**: ``EXPOSE`` names the port the final ``CMD`` binds, 6040, and no other;
  **IMG-015**: service ``librefolio`` publishes that container port and no other, in every ``docker-compose*.yml``
  (other services of a file run other images, with ports of their own);
* **N-8**: ``env_file`` brings the host's ``PORT``, the host side of the mapping, into the container, where the server
  listens on 6040 whatever it says and ``dev.py`` commands read it. **IMG-016**: both compose files pin ``PORT``,
  ``HOST`` and ``LIBREFOLIO_DATA_DIR`` in ``environment`` to what the image binds and keeps: the ``CMD``'s ``--port``
  and ``--host``, and its ``ENV``'s data directory, where a volume of the service must be mounted;
* **32-3** (D8): ``./dev.py docker exec`` ran its command as root, so the files it created in the data volume belonged
  to root. The container now runs
  ``sh -c 'exec gosu "${LIBREFOLIO_UID:-1000}:${LIBREFOLIO_GID:-1000}" python dev.py "$@"' sh`` followed by the
  arguments: the image's numeric ids, with the defaults of ``entrypoint.sh`` for an image that sets neither.
  **IMG-017**: that exact command line, once, and its exit status is the command's; **IMG-017b**: arguments a shell
  would split, expand or run come after the ``sh`` that becomes ``$0``, one element each, in order, and the script is
  the same whatever they are; **IMG-017c**: no command, exit 1 and nothing run; **IMG-017d**: what follows the service
  name, run by a local POSIX ``sh`` with stand-ins for ``gosu`` and ``python``, hands every argument to
  ``python dev.py`` verbatim and switches to the ids of the environment, or, when it sets neither, to ``1000:1000``,
  the ids ``entrypoint.sh`` falls back to; **IMG-018**: those ids are set by an ``ENV`` of the final image, the
  fallback being for an image older than that ``ENV``;
* **M-25**: the image's frontend bundle, its ``VERSION`` file and its tag could name three versions. The version is
  now frozen once, at step 0 of ``_docker_ensure_assets_built``, after removing the previous ``VERSION`` and clearing
  ``get_git_version``'s cache, before any step can write a tracked file (``-dirty``). **IMG-019**:
  ``_docker_frontend_stale_reason`` gives each reason in its order (the sources changed; not a production build; no
  recorded version, so not made by ``docker build``; built for another version) and None when the bundle fits;
  **IMG-020**: ``_docker_ensure_frontend_built`` sets ``LF_APP_VERSION`` to the version during the build only, gives
  back the value before it (or its absence) whether the build succeeds, fails or raises, and records
  ``.build-version`` only after a build that succeeded; **IMG-020b**: a bundle that fits is not rebuilt;
  **IMG-021**: the version step 0 froze reaches the frontend build and ``VERSION``, though every fresh
  ``get_git_version`` answer after the first step is ``-dirty``; **IMG-022**: ``_get_docker_tag`` returns the
  override when given, else ``librefolio:`` and the stripped ``VERSION``, and asks git afresh only when that file is
  missing or blank; **IMG-023**: ``cmd_docker_build``, end to end with stand-ins, tags the image with the version of
  ``VERSION`` and of the bundle (``-light`` appended for the light variant), not git's later ``-dirty``;
  **IMG-024**: ``_check_env_file`` warns when the shell's ``PORT`` differs from ``.env``'s, and no longer about
  ``TEST_PORT``.

Every static check has a ``b`` test that runs it on synthetic files, the state before CP7a included, to show it can
fail: **IMG-013b**, **IMG-014b**, **IMG-015b**, **IMG-016b**, **IMG-018b**.

The static checks read the repository's ``Dockerfile`` and ``docker-compose*.yml`` as Docker and Compose do, with the
parser of ``test_dev_cli_image.py`` (comment lines dropped, continuation lines joined); the stages the final one builds
on (``FROM <stage>``) count too, since their packages, ``EXPOSE`` and ``ENV`` reach the final image. A failure quotes
what it read.

``dev.py`` is loaded in this process under a private name, its import-time ``sys.path`` entries and change of
directory undone, and its functions run with stand-ins for whatever they would launch: ``run_command_live`` for
``docker``; ``update_js_cache``, ``cmd_fe_build``, ``copy_docs_assets``, ``run_pipenv`` and the ``subprocess`` of the
requirements step for the asset build; ``get_git_version`` for git. ``PROJECT_ROOT``, which the docker functions read
when they run, points to a project in ``tmp_path``: ``VERSION``, ``requirements.txt`` and ``.env`` live there. The two
markers of ``frontend/build/`` are module constants computed from the real root at import, so they are moved to
``tmp_path`` separately. While the asset build runs, ``PATH`` names an empty directory: a stand-in that missed its
target would fail to find its command rather than run it. IMG-017d's hostile arguments only ``touch`` a file in the
directory of the run, which must stay absent: nothing destructive is ever handed to a shell.

PURE for the runner: no database, no server, no network, no Docker, nothing written in the repository. The Dockerfile,
the compose files and ``entrypoint.sh`` are only read, everything written lives in ``tmp_path``, the processes started
are a POSIX ``sh`` and this interpreter, and every monkeypatch ends with its test.

Left to a Docker run: ``zoneinfo`` in the image resolves ``Asia/Calcutta`` and ``US/Eastern``; ``docker compose up``
publishes 6040 only and the healthcheck passes; ``./dev.py docker exec user list`` runs as
``LIBREFOLIO_UID:LIBREFOLIO_GID`` and a file it creates in the data volume belongs to those ids; ``dev.py`` in the
container reads ``PORT=6040`` while the host's ``.env`` says otherwise; ``./dev.py docker build`` gives the tag, the
sidebar and ``/system/info`` one version.
"""

import importlib.util
import json
import os
import posixpath
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import yaml

from backend.app.utils.runtime import version as version_module
from backend.test_scripts.test_utilities.test_dev_cli_image import COMPOSE_SERVICE, Instruction, command_tokens, dockerfile_instructions, last
from backend.test_scripts.test_utils import print_section, print_success
from scripts import cli_base

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
#: The compose files that define service librefolio in full: docker-compose.yml builds the image, docker-compose.prod.yml
#: runs the published one. Any other docker-compose*.yml is read as an override, which may leave things out.
COMPOSE_FILES = ("docker-compose.yml", "docker-compose.prod.yml")
COMPOSE_GLOB = "docker-compose*.yml"
OVERRIDE_FILE = "docker-compose.override.yml"

#: dev.py loaded in this process under a private name, so the ``dev`` other tests import is not replaced.
DEVPY_MODULE = "_test_dev_cli_docker_devpy"
#: Generous for a local sh and this interpreter; a hang still ends, with what it printed.
RUN_TIMEOUT = 60


# ---------------------------------------------------------------------------
# The Dockerfile: stages, the final image, its CMD and ENV
# ---------------------------------------------------------------------------


@dataclass
class Stage:
    """One build stage: what its ``FROM`` names, its ``AS`` name, and its instructions after the ``FROM``."""

    base: str
    name: str | None
    instructions: list[Instruction] = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.name or f"FROM {self.base}"


def dockerfile_stages(text: str) -> list[Stage]:
    """The stages in order; what comes before the first ``FROM`` (global ``ARG``s) belongs to none."""
    stages: list[Stage] = []
    for instruction in dockerfile_instructions(text):
        if instruction.keyword == "FROM":
            words = [word for word in shlex.split(instruction.arguments) if not word.startswith("--")]
            stages.append(Stage(words[0], words[2] if len(words) > 2 and words[1].upper() == "AS" else None))
        elif stages:
            stages[-1].instructions.append(instruction)
    assert stages, "the Dockerfile has no FROM"
    return stages


def final_image(text: str) -> list[Instruction]:
    """The instructions that shape the final image: those of the stages it builds on (``FROM <stage>``), oldest first, then its own."""
    stages = dockerfile_stages(text)
    chain: list[Stage] = []
    index: int | None = len(stages) - 1
    while index is not None:
        stage = stages[index]
        if "$" in stage.base:
            raise AssertionError(f"the final image builds on {stage.base!r}, chosen by a build argument: this test does not follow it")
        chain.insert(0, stage)
        index = next((earlier for earlier in range(index - 1, -1, -1) if (stages[earlier].name or "").lower() == stage.base.lower()), None)
    return [instruction for stage in chain for instruction in stage.instructions]


def cmd_option(instructions: list[Instruction], option: str) -> str | None:
    """The value the final ``CMD`` gives ``option``, written ``--port 6040`` or ``--port=6040``; None without one."""
    cmd = last(instructions, "CMD")
    words = command_tokens(cmd.arguments) if cmd else []
    for i, word in enumerate(words):
        if word == option and i + 1 < len(words):
            return words[i + 1]
        if word.startswith(f"{option}="):
            return word.partition("=")[2]
    return None


def env_assignments(instruction: Instruction) -> dict[str, str]:
    """What one ``ENV`` sets: ``NAME=value`` pairs, or the legacy ``ENV NAME value`` (one variable, the rest of the line)."""
    words = shlex.split(instruction.arguments)
    if words and "=" not in words[0]:
        name, _, value = instruction.arguments.strip().partition(" ")
        return {name: value.strip()}
    pairs = [word.partition("=") for word in words]
    if not all(sep for _, sep, _ in pairs):
        raise AssertionError(f"{instruction}: ENV syntax this test does not reproduce")
    return {name: value for name, _, value in pairs}


def image_environment(instructions: list[Instruction]) -> dict[str, str]:
    """The variables the ``ENV`` instructions of the final image set, a later one overriding an earlier one."""
    environment: dict[str, str] = {}
    for instruction in instructions:
        if instruction.keyword == "ENV":
            environment.update(env_assignments(instruction))
    return environment


SYNTHETIC_CMD = 'CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "6040"]'
SLIM = "python:3.13-slim"


def synthetic_dockerfile(final: str, builder: str = "", final_base: str = SLIM) -> str:
    """Two stages: ``builder`` with ``builder`` in it, then the final one, on ``final_base``, with ``final`` and the CMD every check reads (uvicorn on 0.0.0.0:6040)."""
    return "\n".join([f"FROM {SLIM} AS builder", builder, f"FROM {final_base}", "WORKDIR /app", final, SYNTHETIC_CMD, ""])


# ---------------------------------------------------------------------------
# P-4: apt in the final image
# ---------------------------------------------------------------------------

#: P-4 (D11): the IANA database zoneinfo reads from the system, and the package where Debian keeps its old names.
TIME_ZONE_PACKAGES = ("tzdata", "tzdata-legacy")
#: apt-get options whose value is the next word.
APT_VALUE_OPTIONS = frozenset({"-o", "-c", "-t", "--option", "--config-file", "--target-release", "--default-release"})
#: A word made of operators only (``&&``, ``||``, ``;``, ``|``, ``&``, parentheses): the commands around it are separate.
COMMAND_SEPARATOR = re.compile(r"[;&|()]+")
#: A redirection operator: the word after it is a file, not an argument.
REDIRECTION = re.compile(r"[<>]+")
#: ``NAME=value`` before a command: an assignment, not the command.
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*", re.DOTALL)


def shell_commands(script: str) -> list[list[str]]:
    """The simple commands of a shell command line, as words: split at the operators, redirections and leading assignments dropped."""
    lexer = shlex.shlex(script, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    commands: list[list[str]] = [[]]
    words = iter(lexer)
    for word in words:
        if COMMAND_SEPARATOR.fullmatch(word):
            commands.append([])
        elif REDIRECTION.fullmatch(word):
            next(words, None)
        elif commands[-1] or not ASSIGNMENT.fullmatch(word):
            commands[-1].append(word)
    return [command for command in commands if command]


def run_commands(instruction: Instruction) -> list[list[str]]:
    """The simple commands a ``RUN`` runs: its exec form (a JSON list, no shell) as one, its shell form split; ``--mount``-style flags dropped."""
    arguments = instruction.arguments
    while arguments.startswith("--"):
        arguments = arguments.partition(" ")[2].lstrip()
    if "<<" in arguments:
        raise AssertionError(f"{instruction}: a heredoc, which this test does not reproduce")
    try:
        words = json.loads(arguments)
    except ValueError:
        words = None
    return [[str(word) for word in words]] if isinstance(words, list) else shell_commands(arguments)


def apt_installs(command: list[str]) -> list[str]:
    """What ``apt-get install`` or ``apt install`` installs in one simple command, ``=version``, ``:arch`` and ``/release`` dropped; nothing for another command."""
    if not command or posixpath.basename(command[0]) not in ("apt-get", "apt"):
        return []
    operands: list[str] = []
    words = iter(command[1:])
    for word in words:
        if word in APT_VALUE_OPTIONS:
            next(words, None)
        elif not word.startswith("-"):
            operands.append(word)
    return [re.split(r"[=:/]", operand, maxsplit=1)[0] for operand in operands[1:]] if operands[:1] == ["install"] else []


def installed_packages(instructions: list[Instruction]) -> set[str]:
    return {package for instruction in instructions if instruction.keyword == "RUN" for command in run_commands(instruction) for package in apt_installs(command)}


def time_zone_violations(dockerfile_text: str) -> list[str]:
    """What keeps the final image from having the system's time zone database, old names included (P-4)."""
    installed = installed_packages(final_image(dockerfile_text))
    violations = []
    for package in TIME_ZONE_PACKAGES:
        if package not in installed:
            elsewhere = [stage.label for stage in dockerfile_stages(dockerfile_text)[:-1] if package in installed_packages(stage.instructions)]
            note = f"; stage {', '.join(elsewhere)} installs it, and the final image does not build on it" if elsewhere else ""
            violations.append(f"the final image installs no {package} with apt (it installs: {', '.join(sorted(installed)) or 'nothing'}){note}")
    return violations


def final_lines(dockerfile_text: str, *keywords: str) -> str:
    """The final image's instructions of these kinds, as found, for a failure message."""
    return "\n".join(f"  {instruction}" for instruction in final_image(dockerfile_text) if instruction.keyword in keywords)


APT_RUN = "RUN apt-get update && apt-get install -y --no-install-recommends \\\n    gosu sqlite3 tzdata tzdata-legacy \\\n    && rm -rf /var/lib/apt/lists/*"
TIME_ZONE_CASES = [
    pytest.param(APT_RUN, "", SLIM, True, id="both-in-the-final-stage"),
    pytest.param("RUN apt-get -y -o Dpkg::Use-Pty=0 install --no-install-recommends tzdata=2025b-4 tzdata-legacy=2025b-4", "", SLIM, True, id="options-first-versions-pinned"),
    pytest.param("", "RUN apt-get install -y tzdata tzdata-legacy", "builder", True, id="from-the-stage-it-builds-on"),
    pytest.param("RUN apt-get update && apt-get install -y --no-install-recommends gosu sqlite3 && rm -rf /var/lib/apt/lists/*", "", SLIM, False, id="neither-as-before-p4"),
    pytest.param("RUN apt-get install -y gosu tzdata", "", SLIM, False, id="no-tzdata-legacy"),
    pytest.param("RUN apt-get install -y gosu tzdata-legacy", "", SLIM, False, id="no-tzdata"),
    pytest.param("RUN apt-get install -y gosu tzdata", "RUN apt-get install -y tzdata-legacy", SLIM, False, id="tzdata-legacy-in-another-stage"),
    pytest.param("RUN apt-get install -y \\\n    # tzdata-legacy \\\n    gosu tzdata", "", SLIM, False, id="tzdata-legacy-commented-out"),
    pytest.param("RUN echo tzdata-legacy && apt-get install -y gosu tzdata", "", SLIM, False, id="tzdata-legacy-only-echoed"),
]


# ---------------------------------------------------------------------------
# C-37: the ports
# ---------------------------------------------------------------------------


def is_port(word: object, port: str) -> bool:
    """Whether an ``EXPOSE`` word or a container port is ``port`` over TCP: ``6040`` or ``6040/tcp``."""
    number, _, protocol = str(word).partition("/")
    return number == port and protocol.lower() in ("", "tcp")


def literal_cmd_port(instructions: list[Instruction]) -> tuple[str, list[str]]:
    """The final CMD's --port, and the violation when it is not a literal number."""
    port = cmd_option(instructions, "--port")
    return (port, []) if port and port.isdigit() else ("", [f"the final CMD passes no literal --port to uvicorn (found {port!r})"])


def expose_violations(dockerfile_text: str) -> list[str]:
    """Where the final image's ``EXPOSE`` differs from the one port its ``CMD`` binds (C-37)."""
    instructions = final_image(dockerfile_text)
    port, broken = literal_cmd_port(instructions)
    if broken:
        return broken
    exposed = [(word, instruction) for instruction in instructions if instruction.keyword == "EXPOSE" for word in shlex.split(instruction.arguments)]
    violations = [f"{instruction} exposes {word}: the CMD binds --port {port} only, and the image has no test mode" for word, instruction in exposed if not is_port(word, port)]
    if not any(is_port(word, port) for word, _ in exposed):
        violations.append(f"the final image does not EXPOSE {port}, the port its CMD binds")
    return violations


#: One part of a short-syntax ``ports`` entry: a ``${…}`` substitution, which may hold colons, or a run of anything but colons.
PORT_PART = re.compile(r"(?:\$\{[^}]*\}|[^:])+")


def container_port(entry: object) -> str:
    """The container side of a ``ports`` entry, protocol included: ``target`` in the long syntax, the last colon-separated part of the short one."""
    if isinstance(entry, dict):
        protocol = entry.get("protocol")
        return f"{entry.get('target')}/{protocol}" if protocol else str(entry.get("target"))
    parts = PORT_PART.findall(str(entry))
    return parts[-1] if parts else ""


def compose_service(text: str) -> dict | None:
    """Service ``librefolio`` of a compose file, or None."""
    services = (yaml.safe_load(text) or {}).get("services") or {}
    service = services.get(COMPOSE_SERVICE)
    return service if isinstance(service, dict) else None


def service_port_violations(where: str, service: dict, port: str, complete: bool) -> list[str]:
    published = [(container_port(entry), entry) for entry in service.get("ports") or []]
    violations = [f"{where} publishes container port {target!r} ({entry!r}): the server listens on {port} only" for target, entry in published if not is_port(target, port)]
    violations += [f"{where} exposes {entry!r}: the server listens on {port} only" for entry in service.get("expose") or [] if not is_port(entry, port)]
    if complete and not any(is_port(target, port) for target, _ in published):
        violations.append(f"{where} publishes no container port {port}: the server could not be reached from the host")
    return violations


def port_violations(dockerfile_text: str, composes: dict[str, str]) -> list[str]:
    """Where service ``librefolio`` publishes or exposes a container port other than the one the final ``CMD`` binds, or a complete compose file does not publish it (C-37)."""
    port, broken = literal_cmd_port(final_image(dockerfile_text))
    if broken:
        return broken
    violations = []
    for file, text in composes.items():
        service = compose_service(text)
        if service is not None:
            violations += service_port_violations(f"{file}, service {COMPOSE_SERVICE},", service, port, complete=file in COMPOSE_FILES)
        elif file in COMPOSE_FILES:
            violations.append(f"{file} has no service {COMPOSE_SERVICE}")
    return violations


EXPOSE_CASES = [
    pytest.param("EXPOSE 6040", "", SLIM, True, id="the-cmd-port"),
    pytest.param("EXPOSE 6040/tcp", "", SLIM, True, id="with-its-protocol"),
    pytest.param("EXPOSE 6040", "EXPOSE 6041", SLIM, True, id="another-stage-does-not-count"),
    pytest.param("EXPOSE 6040 6041", "", SLIM, False, id="the-test-port-too-as-before-c37"),
    pytest.param("EXPOSE 6040\nEXPOSE 6041", "", SLIM, False, id="a-second-expose"),
    pytest.param("EXPOSE 6040", "EXPOSE 6041", "builder", False, id="from-the-stage-it-builds-on"),
    pytest.param("EXPOSE 6040/udp", "", SLIM, False, id="udp"),
    pytest.param("EXPOSE ${PORT}", "", SLIM, False, id="a-variable"),
    pytest.param("", "", SLIM, False, id="nothing-exposed"),
]

PUBLISHED = ["${PORT:-6040}:6040"]
PORT_CASES = [
    pytest.param(COMPOSE_FILES[0], {"ports": PUBLISHED}, {}, True, id="host-side-variable"),
    pytest.param(COMPOSE_FILES[0], {"ports": ["127.0.0.1:6040:6040/tcp"]}, {}, True, id="host-ip-and-protocol"),
    pytest.param(COMPOSE_FILES[0], {"ports": [6040]}, {}, True, id="container-port-only"),
    pytest.param(COMPOSE_FILES[0], {"ports": [{"target": 6040, "published": "8080"}]}, {}, True, id="long-syntax"),
    pytest.param(COMPOSE_FILES[0], {"ports": PUBLISHED}, {"sidecar": {"ports": ["9090:9090"]}}, True, id="another-service-another-image"),
    pytest.param(OVERRIDE_FILE, {"environment": ["LOG_LEVEL=DEBUG"]}, {}, True, id="override-publishing-nothing"),
    pytest.param(COMPOSE_FILES[0], {"ports": [*PUBLISHED, "${TEST_PORT:-6041}:6041"]}, {}, False, id="the-test-port-too-as-before-c37"),
    pytest.param(COMPOSE_FILES[0], {"ports": ["${PORT:-6040}:${PORT:-6040}"]}, {}, False, id="container-side-variable"),
    pytest.param(COMPOSE_FILES[0], {"ports": ["6040-6041:6040-6041"]}, {}, False, id="a-range"),
    pytest.param(COMPOSE_FILES[0], {"ports": ["6040:6040/udp"]}, {}, False, id="udp"),
    pytest.param(COMPOSE_FILES[0], {"ports": [{"target": 6041, "published": "6041"}]}, {}, False, id="long-syntax-another-port"),
    pytest.param(COMPOSE_FILES[0], {"ports": PUBLISHED, "expose": ["6041"]}, {}, False, id="exposes-another-port"),
    pytest.param(COMPOSE_FILES[0], {"image": "librefolio:latest"}, {}, False, id="publishes-nothing"),
    pytest.param(OVERRIDE_FILE, {"ports": ["6041:6041"]}, {}, False, id="override-publishing-another-port"),
    pytest.param(COMPOSE_FILES[0], None, {"sidecar": {"ports": ["6040:6040"]}}, False, id="no-librefolio-service"),
]


def synthetic_compose(service: dict | None, others: dict) -> str:
    """A compose file with service librefolio as given (none for None) and the ``others`` beside it."""
    return yaml.safe_dump({"services": {**({COMPOSE_SERVICE: service} if service is not None else {}), **others}}, sort_keys=False)


def repository_composes() -> dict[str, str]:
    composes = {path.name: path.read_text(encoding="utf-8") for path in sorted(PROJECT_ROOT.glob(COMPOSE_GLOB))}
    assert set(COMPOSE_FILES) <= set(composes), f"premise: {', '.join(COMPOSE_FILES)} are in the repository root; found {sorted(composes)}"
    return composes


def compose_lines(composes: dict[str, str], *keys: str) -> str:
    """What service librefolio of each file says under ``keys``, as found, for a failure message."""
    return "\n".join(f"  {file}, {key}: {json.dumps(service.get(key))}" for file, text in composes.items() if (service := compose_service(text)) is not None for key in keys)


# ---------------------------------------------------------------------------
# N-8: what compose pins in environment
# ---------------------------------------------------------------------------

#: Why compose pins each variable for service librefolio (N-8, and the comments of the compose files).
PIN_REASONS = {
    "PORT": "the server listens on the CMD's --port whatever PORT says, and dev.py commands in the container read PORT",
    "HOST": "the CMD binds this address, and a HOST=127.0.0.1 left in .env for local development must not reach the container",
    "LIBREFOLIO_DATA_DIR": "the image's ENV keeps the data there, where the data volume is mounted",
}


def pinned_environment(dockerfile_text: str) -> dict[str, str | None]:
    """What compose must pin for the image, read from it: the ``CMD``'s ``--port`` and ``--host``, the ``ENV``'s data directory."""
    instructions = final_image(dockerfile_text)
    return {"PORT": cmd_option(instructions, "--port"), "HOST": cmd_option(instructions, "--host"), "LIBREFOLIO_DATA_DIR": image_environment(instructions).get("LIBREFOLIO_DATA_DIR")}


def service_environment(service: dict) -> dict[str, str | None]:
    """The ``environment`` of a service, list or mapping syntax; a name without a value (``- PORT``, ``PORT:``) is None: Compose takes it from the shell."""
    environment = service.get("environment") or {}
    if isinstance(environment, dict):
        return {str(name): None if value is None else str(value) for name, value in environment.items()}
    entries = [str(entry).partition("=") for entry in environment]
    return {name: value if sep else None for name, sep, value in entries}


def volume_target(entry: object) -> str:
    """Where a ``volumes`` entry is mounted in the container: ``target`` in the long syntax, the ``TARGET`` of ``SOURCE:TARGET[:MODE]`` or a lone path in the short one."""
    if isinstance(entry, dict):
        return posixpath.normpath(str(entry.get("target")))
    parts = str(entry).split(":")
    return posixpath.normpath(parts[1] if len(parts) > 1 else parts[0])


def service_environment_violations(where: str, service: dict, pinned: dict[str, str], complete: bool) -> list[str]:
    environment = service_environment(service)
    violations = []
    for name, value in pinned.items():
        if name not in environment:
            violations += [f"{where} leaves {name} to env_file and the shell; the image needs {name}={value}: {PIN_REASONS[name]}"] if complete else []
        elif environment[name] != value:
            found = "no value, taken from the shell" if environment[name] is None else repr(environment[name])
            violations.append(f"{where} sets {name} to {found}; the image needs {name}={value}: {PIN_REASONS[name]}")
    targets = [volume_target(entry) for entry in service.get("volumes") or []]
    if complete and pinned["LIBREFOLIO_DATA_DIR"] not in targets:
        violations.append(f"{where} mounts no volume at LIBREFOLIO_DATA_DIR={pinned['LIBREFOLIO_DATA_DIR']} (mounted: {targets or 'nothing'}): the data would stay inside the container")
    return violations


def environment_violations(dockerfile_text: str, composes: dict[str, str]) -> list[str]:
    """Where service ``librefolio`` leaves ``PORT``, ``HOST`` or ``LIBREFOLIO_DATA_DIR`` to ``env_file``, sets one to another value, or mounts nothing at the data directory (N-8)."""
    pinned = pinned_environment(dockerfile_text)
    unreadable = [f"the final image gives {name} no literal value to pin (found {value!r})" for name, value in pinned.items() if not value or "$" in value]
    if unreadable:
        return unreadable
    violations = []
    for file, text in composes.items():
        service = compose_service(text)
        if service is not None:
            violations += service_environment_violations(f"{file}, service {COMPOSE_SERVICE},", service, pinned, complete=file in COMPOSE_FILES)
        elif file in COMPOSE_FILES:
            violations.append(f"{file} has no service {COMPOSE_SERVICE}")
    return violations


DATA_DIR = "/app/backend/data/prod-docker"
DATA_VOLUME = f"./LibreFolio-data:{DATA_DIR}"
PINNED_ENVIRONMENT = (f"LIBREFOLIO_DATA_DIR={DATA_DIR}", "HOST=0.0.0.0", "PORT=6040")
ENVIRONMENT_DOCKERFILE = synthetic_dockerfile("ENV HOST=0.0.0.0 \\\n    PORT=6040 \\\n    LIBREFOLIO_DATA_DIR=" + DATA_DIR)


def environment_with(name: str, entry: str | None) -> list[str]:
    """PINNED_ENVIRONMENT with the entry of ``name`` replaced by ``entry``, or removed for None."""
    kept = [item for item in PINNED_ENVIRONMENT if not item.startswith(f"{name}=")]
    return kept if entry is None else [*kept, entry]


ENVIRONMENT_CASES = [
    pytest.param(COMPOSE_FILES[0], {"environment": list(PINNED_ENVIRONMENT), "volumes": [DATA_VOLUME]}, True, id="pinned"),
    pytest.param(COMPOSE_FILES[0], {"environment": {"LIBREFOLIO_DATA_DIR": DATA_DIR, "HOST": "0.0.0.0", "PORT": 6040}, "volumes": [DATA_VOLUME]}, True, id="mapping-syntax"),
    pytest.param(COMPOSE_FILES[0], {"environment": list(PINNED_ENVIRONMENT), "volumes": [{"type": "bind", "source": "./LibreFolio-data", "target": DATA_DIR}]}, True, id="long-volume-syntax"),
    pytest.param(OVERRIDE_FILE, {"environment": ["LOG_LEVEL=DEBUG"]}, True, id="override-setting-none-of-them"),
    pytest.param(COMPOSE_FILES[0], {"environment": environment_with("PORT", None), "volumes": [DATA_VOLUME]}, False, id="port-left-to-env-file-as-before-n8"),
    pytest.param(COMPOSE_FILES[0], {"environment": environment_with("PORT", "PORT"), "volumes": [DATA_VOLUME]}, False, id="port-from-the-shell"),
    pytest.param(COMPOSE_FILES[0], {"environment": environment_with("PORT", "PORT=${PORT:-6040}"), "volumes": [DATA_VOLUME]}, False, id="port-is-the-host-side"),
    pytest.param(COMPOSE_FILES[0], {"environment": environment_with("HOST", "HOST=127.0.0.1"), "volumes": [DATA_VOLUME]}, False, id="host-loopback"),
    pytest.param(COMPOSE_FILES[0], {"environment": environment_with("HOST", None), "volumes": [DATA_VOLUME]}, False, id="host-left-to-env-file"),
    pytest.param(COMPOSE_FILES[0], {"environment": environment_with("LIBREFOLIO_DATA_DIR", "LIBREFOLIO_DATA_DIR=/data"), "volumes": [DATA_VOLUME]}, False, id="data-dir-elsewhere"),
    pytest.param(COMPOSE_FILES[0], {"environment": list(PINNED_ENVIRONMENT), "volumes": ["./LibreFolio-data:/srv/data"]}, False, id="data-dir-not-mounted"),
    pytest.param(OVERRIDE_FILE, {"environment": ["PORT=8080"]}, False, id="override-setting-another-port"),
]


# ---------------------------------------------------------------------------
# dev.py, loaded in this process
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def devpy() -> Iterator[ModuleType]:
    """The repository's ``dev.py`` as a module, loaded under a private name with its import-time side effects undone.

    Its module-level code inserts two ``sys.path`` entries and changes directory to the project root: both are
    restored as soon as it has loaded, before any test runs.
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


@dataclass
class FakeRunner:
    """``run_command_live``'s stand-in: records each command line and returns ``returncode``, running nothing."""

    returncode: int = 0
    launches: list[tuple[str, ...]] = field(default_factory=list)

    def __call__(self, cmd, cwd=None, env=None) -> int:
        self.launches.append(tuple(cmd))
        return self.returncode


def read_text(path: Path) -> str | None:
    """The file's content, or None when it does not exist."""
    return path.read_text(encoding="utf-8") if path.exists() else None


# ---------------------------------------------------------------------------
# 32-3: docker exec
# ---------------------------------------------------------------------------

#: 32-3 (D8): the script the container's sh runs: gosu drops to the image's numeric ids, falling back to those of
#: entrypoint.sh, and the arguments arrive as "$@".
EXEC_SCRIPT = 'exec gosu "${LIBREFOLIO_UID:-1000}:${LIBREFOLIO_GID:-1000}" python dev.py "$@"'
#: ``docker compose exec`` in service librefolio, the sh that runs the script, and "sh" as its $0; the arguments follow.
EXEC_PREFIX = ("docker", "compose", "exec", COMPOSE_SERVICE, "sh", "-c", EXEC_SCRIPT, "sh")
#: Created by any hostile argument a shell ran instead of passing it on.
CANARY = "INJECTED"
#: Arguments a shell would split, expand, glob or run if they were pasted into the script. What they would run only
#: creates CANARY in the directory of the run.
HOSTILE_ARGUMENTS = ("user", "create", f"a b; touch {CANARY}", f"$(touch {CANARY})", f"`touch {CANARY}`", f"x' ; touch {CANARY}; echo '", f'x" ; touch {CANARY}; echo "', "it's", "*", "", "$LIBREFOLIO_UID", "line\nbreak", "--role", "admin")
#: The ids the local run gives the container's environment.
STAND_IN_UID, STAND_IN_GID = "4321", "8765"
#: The ids entrypoint.sh drops to in an image that sets neither LIBREFOLIO_UID nor LIBREFOLIO_GID (one older than that
#: ENV): docker exec must fall back to the same, or the server and the command would own the volume's files apart.
DEFAULT_IDS = "1000:1000"
ENTRYPOINT = PROJECT_ROOT / "entrypoint.sh"
#: An id variable of the image with the value sh uses when it is unset or empty: ``${LIBREFOLIO_UID:-1000}``.
ID_FALLBACK = re.compile(r"\$\{(LIBREFOLIO_UID|LIBREFOLIO_GID):-([^}]*)\}")
#: The container's environment in the local run, and the user:group gosu must get from it.
EXEC_ENVIRONMENTS = [
    pytest.param({"LIBREFOLIO_UID": STAND_IN_UID, "LIBREFOLIO_GID": STAND_IN_GID}, f"{STAND_IN_UID}:{STAND_IN_GID}", id="ids-of-the-environment"),
    pytest.param({}, DEFAULT_IDS, id="neither-set-entrypoint-defaults"),
]

GOSU_STAND_IN = """\
#!/bin/sh
# gosu's stand-in: records the user:group it is given, then runs the rest as gosu does, without switching.
printf '%s' "$1" > "$GOSU_RECORD"
shift
exec "$@"
"""

PYTHON_STAND_IN = """\
#!/bin/sh
# python's stand-in: records its arguments as one JSON list, through the interpreter running this test.
exec "$REAL_PYTHON" -c 'import json, os, sys; open(os.environ["ARGV_RECORD"], "w", encoding="utf-8").write(json.dumps(sys.argv[1:]))' "$@"
"""


def docker_exec(devpy: ModuleType, monkeypatch: pytest.MonkeyPatch, arguments, returncode: int = 0) -> tuple[int, FakeRunner]:
    """``./dev.py docker exec <arguments>``, with ``run_command_live`` stood in for: its result, and what it would have run."""
    runner = FakeRunner(returncode)
    monkeypatch.setattr(devpy, "run_command_live", runner)
    return devpy.cmd_docker_exec(SimpleNamespace(cmd_args=list(arguments))), runner


def in_container(argv: tuple[str, ...]) -> list[str]:
    """What ``docker compose exec`` runs in the container: everything after the service name."""
    return list(argv[argv.index(COMPOSE_SERVICE) + 1 :])


def gosu_target(script: str) -> str:
    """The user spec the script hands gosu: the word after ``gosu``, quotes removed."""
    words = shlex.split(script)
    return words[words.index("gosu") + 1] if "gosu" in words[:-1] else ""


def fallback_ids(script: str) -> str | None:
    """The user:group a shell script falls back to when neither LIBREFOLIO_UID nor LIBREFOLIO_GID is set, read from its ``${…:-default}`` outside comments; None unless it has both."""
    code = "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("#"))
    defaults = dict(ID_FALLBACK.findall(code))
    return f"{defaults['LIBREFOLIO_UID']}:{defaults['LIBREFOLIO_GID']}" if {"LIBREFOLIO_UID", "LIBREFOLIO_GID"} <= defaults.keys() else None


def exec_id_violations(script: str, dockerfile_text: str) -> list[str]:
    """Where the ids the script switches to are not set, non-empty, by an ``ENV`` of the final image."""
    target = gosu_target(script)
    names = re.findall(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)", target)
    if not names:
        return [f"the script switches to {target!r} with gosu, not to ids read from the image's environment: {script!r}"]
    environment = image_environment(final_image(dockerfile_text))
    return [f"the script hands gosu ${name} ({target}), which {'no ENV of the final image sets' if name not in environment else 'the final image sets empty'}: docker exec would not run as the ids the image was built with" for name in names if not environment.get(name, "").strip()]


EXEC_ID_ENV = "ARG UID=1000\nARG GID=1000\nENV LIBREFOLIO_UID=${UID} \\\n    LIBREFOLIO_GID=${GID}"
EXEC_ID_CASES = [
    pytest.param(EXEC_SCRIPT, EXEC_ID_ENV, "", SLIM, True, id="set-from-the-build-arguments"),
    pytest.param(EXEC_SCRIPT, "", "ENV LIBREFOLIO_UID=1000 LIBREFOLIO_GID=1000", "builder", True, id="from-the-stage-it-builds-on"),
    pytest.param(EXEC_SCRIPT, "ENV LIBREFOLIO_UID 1000\nENV LIBREFOLIO_GID 1000", "", SLIM, True, id="legacy-env-form"),
    pytest.param(EXEC_SCRIPT, "", "", SLIM, False, id="not-set"),
    pytest.param(EXEC_SCRIPT, "", "ENV LIBREFOLIO_UID=1000 LIBREFOLIO_GID=1000", SLIM, False, id="set-in-another-stage"),
    pytest.param(EXEC_SCRIPT, "ENV LIBREFOLIO_UID=1000", "", SLIM, False, id="no-gid"),
    pytest.param(EXEC_SCRIPT, 'ENV LIBREFOLIO_UID=1000 LIBREFOLIO_GID=""', "", SLIM, False, id="empty-gid"),
    pytest.param('exec gosu 1000:1000 python dev.py "$@"', EXEC_ID_ENV, "", SLIM, False, id="ids-written-in-the-script"),
]


# ---------------------------------------------------------------------------
# M-25: one version for the bundle, VERSION and the tag
# ---------------------------------------------------------------------------

APP_VERSION = "LF_APP_VERSION"
#: The version step 0 freezes, and what git describe answers once a step has written a tracked file.
FROZEN = "v1.3.0-4-gabc1234"
DRIFTED = f"{FROZEN}-dirty"
#: What an earlier call of the same process left in get_git_version's cache: step 0 clears it.
STALE_CACHE = "v1.2.9-stale-cache"
#: The VERSION, or the recorded bundle version, of a previous image build.
PREVIOUS_BUILD = "v1.2.0"
#: A value LF_APP_VERSION holds before the call, as the release workflow sets it: it must come back afterwards.
OUTER_APP_VERSION = "v1.2.5-outer"

#: _docker_frontend_stale_reason's answers, in the order it checks them.
SOURCES_CHANGED = "missing or outdated"
NOT_PRODUCTION = "not a production build"
NO_RECORDED_VERSION = "made without a recorded version (not by docker build)"


def built_for(recorded: str) -> str:
    return f"built for {recorded}, not {FROZEN}"


STALE_CASES = [
    pytest.param(True, "0", FROZEN, SOURCES_CHANGED, id="sources-changed"),
    pytest.param(True, "1", None, SOURCES_CHANGED, id="sources-changed-comes-first"),
    pytest.param(False, "1", FROZEN, NOT_PRODUCTION, id="debug-build"),
    pytest.param(False, None, FROZEN, NOT_PRODUCTION, id="mode-unknown"),
    pytest.param(False, "1", PREVIOUS_BUILD, NOT_PRODUCTION, id="debug-comes-before-the-version"),
    pytest.param(False, "0", None, NO_RECORDED_VERSION, id="no-recorded-version"),
    pytest.param(False, "0", "  \n", NO_RECORDED_VERSION, id="blank-recorded-version"),
    pytest.param(False, "0", PREVIOUS_BUILD, built_for(PREVIOUS_BUILD), id="previous-version"),
    pytest.param(False, "0", DRIFTED, built_for(DRIFTED), id="dirty-version"),
    pytest.param(False, "0", FROZEN, None, id="fits"),
    pytest.param(False, "0\n", f"{FROZEN}\n", None, id="fits-with-newlines"),
]


@dataclass(frozen=True)
class Markers:
    """The bookkeeping files of ``frontend/build/``, moved to tmp_path: the build mode (``.build-debug``) and the version a ``docker build`` recorded (``.build-version``)."""

    mode: Path
    version: Path

    def write(self, mode: str | None, version: str | None) -> None:
        """Give each marker this content, or remove it for None."""
        for path, content in ((self.mode, mode), (self.version, version)):
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(content, encoding="utf-8")


@pytest.fixture
def markers(devpy: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Markers:
    """The markers, moved: dev.py computes their paths from the real root at import, so moving PROJECT_ROOT would not move them."""
    build = tmp_path / "frontend-build"
    build.mkdir()
    moved = Markers(mode=build / ".build-debug", version=build / ".build-version")
    monkeypatch.setattr(devpy, "FRONTEND_BUILD_MODE_MARKER", moved.mode)
    monkeypatch.setattr(devpy, "FRONTEND_BUILD_VERSION_MARKER", moved.version)
    return moved


def given_app_version(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """LF_APP_VERSION before the call: ``value``, or unset. setenv comes first so that the process's own value is back at teardown, whatever the code under test left."""
    monkeypatch.setenv(APP_VERSION, value or "unset-below")
    if value is None:
        monkeypatch.delenv(APP_VERSION)


class BuildCrash(RuntimeError):
    """What the stand-in frontend build raises: a build that crashed or was interrupted."""


@dataclass(frozen=True)
class BuildCall:
    """What the stand-in frontend build saw when it was called."""

    app_version: str | None
    debug: object
    recorded_version: str | None


class FakeFrontendBuild:
    """``cmd_fe_build``'s stand-in: records LF_APP_VERSION, the mode it is asked for and ``.build-version`` as it finds them, then returns ``outcome`` or raises it."""

    def __init__(self, outcome: int | BaseException, version_marker: Path):
        self.outcome, self.version_marker = outcome, version_marker
        self.calls: list[BuildCall] = []

    def __call__(self, args) -> int:
        self.calls.append(BuildCall(os.environ.get(APP_VERSION), getattr(args, "debug", None), read_text(self.version_marker)))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


@dataclass(frozen=True)
class Answer:
    """A fresh answer of the stand-in ``get_git_version``, and the moment it was given."""

    value: str
    version_file_existed: bool
    cache_cleared: bool


class DriftingGitVersion:
    """``get_git_version`` for a run whose steps write to the tree.

    Cached like the real one (``lru_cache``): it repeats its answer until ``cache_clear``. A fresh answer is FROZEN while
    the tree is clean and DRIFTED once a step has written to it (``dirty``), as ``git describe --dirty`` would say. The
    cache starts with STALE_CACHE, what an earlier call of the process could have left. Every fresh answer is recorded
    with whether VERSION existed then and whether the cache had been cleared.
    """

    def __init__(self, version_file: Path):
        self.version_file = version_file
        self.cached: str | None = STALE_CACHE
        self.dirty = False
        self.cleared = False
        self.answers: list[Answer] = []

    def cache_clear(self) -> None:
        self.cached = None
        self.cleared = True

    def __call__(self) -> str:
        if self.cached is None:
            self.cached = DRIFTED if self.dirty else FROZEN
            self.answers.append(Answer(self.cached, self.version_file.exists(), self.cleared))
        return self.cached

    def fresh(self) -> str:
        """What git would answer now: the premise that a late read would have been caught."""
        self.cache_clear()
        return self()


@dataclass(frozen=True)
class StepCall:
    """One heavy step of the asset build, as its stand-in saw it."""

    name: str
    app_version: str | None
    tree_dirty: bool
    detail: object = None


class AssetSteps:
    """Stand-ins for the heavy steps of ``_docker_ensure_assets_built``.

    Each records itself, LF_APP_VERSION and whether the tree was already dirty, then writes to the tree as the real
    steps may (git says ``-dirty`` from then on), and succeeds.
    """

    def __init__(self, git: DriftingGitVersion, root: Path):
        self.git, self.root = git, root
        self.calls: list[StepCall] = []

    def _ran(self, name: str, detail: object = None) -> None:
        self.calls.append(StepCall(name, os.environ.get(APP_VERSION), self.git.dirty, detail))
        self.git.dirty = True

    def update_js_cache(self, strict: bool = False, required_for: str | None = None) -> int:
        self._ran("update_js_cache", {"strict": strict, "required_for": required_for})
        return 0

    def cmd_fe_build(self, args) -> int:
        self._ran("cmd_fe_build", {"debug": getattr(args, "debug", None)})
        return 0

    def copy_docs_assets(self) -> None:
        self._ran("copy_docs_assets")

    def run_pipenv(self, args: list, cwd=None, env=None) -> int:
        self._ran("run_pipenv", list(args))
        return 0

    def subprocess_run(self, cmd, **kwargs) -> subprocess.CompletedProcess:
        self._ran("pipenv requirements", list(cmd))
        if list(cmd) != ["pipenv", "requirements"] or Path(kwargs.get("cwd", "")) != self.root:
            raise AssertionError(f"a subprocess the stand-ins do not expect: {cmd} {kwargs}")
        return subprocess.CompletedProcess(cmd, 0, stdout="# requirements.txt stand-in\n", stderr="")


@dataclass(frozen=True)
class FakeProject:
    root: Path
    git: DriftingGitVersion
    steps: AssetSteps

    @property
    def version_file(self) -> Path:
        return self.root / "VERSION"

    def builds(self) -> list[StepCall]:
        return [call for call in self.steps.calls if call.name == "cmd_fe_build"]

    def other_steps(self) -> list[StepCall]:
        return [call for call in self.steps.calls if call.name != "cmd_fe_build"]


@pytest.fixture
def project(devpy: ModuleType, markers: Markers, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeProject:
    """A project in tmp_path for the docker build functions, git and every heavy step stood in for; VERSION holds a previous build's version."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "VERSION").write_text(PREVIOUS_BUILD, encoding="utf-8")
    git = DriftingGitVersion(root / "VERSION")
    steps = AssetSteps(git, root)
    monkeypatch.setattr(devpy, "PROJECT_ROOT", root)
    monkeypatch.setattr(version_module, "get_git_version", git)
    for name in ("update_js_cache", "cmd_fe_build", "copy_docs_assets", "run_pipenv"):
        monkeypatch.setattr(devpy, name, getattr(steps, name))
    monkeypatch.setattr(devpy, "subprocess", SimpleNamespace(run=steps.subprocess_run))
    # A stand-in that missed its target finds no command to run, rather than building, downloading or writing.
    monkeypatch.setenv("PATH", str(tmp_path / "no-commands"))
    return FakeProject(root, git, steps)


ASSET_CASES = [
    pytest.param(True, FROZEN, True, id="sources-changed"),
    pytest.param(False, PREVIOUS_BUILD, True, id="bundle-of-the-previous-version"),
    pytest.param(False, FROZEN, False, id="bundle-of-this-version"),
]

TAG_CASES = [
    pytest.param(FROZEN, f"librefolio:{FROZEN}", id="version-file"),
    pytest.param(f"  {FROZEN}\n", f"librefolio:{FROZEN}", id="version-file-with-whitespace"),
    pytest.param(None, f"librefolio:{DRIFTED}", id="no-version-file"),
    pytest.param("", f"librefolio:{DRIFTED}", id="empty-version-file"),
    pytest.param(" \n", f"librefolio:{DRIFTED}", id="blank-version-file"),
]

CUSTOM_TAG = "registry.example/librefolio:custom"
BUILD_CASES = [
    pytest.param({}, [f"librefolio:{FROZEN}", "librefolio:latest"], id="full"),
    pytest.param({"light": True}, [f"librefolio:{FROZEN}-light", "librefolio:latest-light"], id="light"),
    pytest.param({"tag": CUSTOM_TAG}, [CUSTOM_TAG, "librefolio:latest"], id="tag-override"),
]


def image_tags(argv: tuple[str, ...]) -> list[str]:
    """The ``-t`` values of a ``docker build`` command line."""
    return [argv[i + 1] for i, word in enumerate(argv[:-1]) if word == "-t"]


# ===========================================================================
# IMG-013: P-4, the time zone database
# ===========================================================================


class TestTimeZoneDatabase:
    def test_the_final_image_installs_it(self):
        """IMG-013: the final image installs tzdata and tzdata-legacy with apt, so zoneinfo resolves the old names too."""
        print_section("IMG-013: tzdata and tzdata-legacy in the final image")
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")

        violations = time_zone_violations(dockerfile)

        assert not violations, "\n".join(violations) + f"\nRUN instructions of the final image:\n{final_lines(dockerfile, 'RUN')}"
        print_success(f"apt installs {' and '.join(TIME_ZONE_PACKAGES)} in the final image")

    @pytest.mark.parametrize(("final", "builder", "final_base", "passes"), TIME_ZONE_CASES)
    def test_the_check_can_fail(self, final, builder, final_base, passes):
        """IMG-013b: the same check on synthetic Dockerfiles: only what reaches the final image counts, read as Docker reads it."""
        print_section("IMG-013b: the time zone check on a synthetic Dockerfile")
        dockerfile = synthetic_dockerfile(final, builder, final_base)

        violations = time_zone_violations(dockerfile)

        assert (not violations) is passes, f"expected {'no violation' if passes else 'a violation'}, got: {violations}\n{dockerfile}"
        print_success(f"violations: {violations or 'none'}")


# ===========================================================================
# IMG-014..IMG-015: C-37, one port
# ===========================================================================


class TestExposedPort:
    def test_only_the_cmd_port(self):
        """IMG-014: the final image's EXPOSE names the port its CMD binds, 6040, and no other: the image has no test mode."""
        print_section("IMG-014: EXPOSE names the CMD's port only")
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")

        violations = expose_violations(dockerfile)

        assert not violations, "\n".join(violations) + f"\nas found:\n{final_lines(dockerfile, 'EXPOSE', 'CMD')}"
        print_success(f"EXPOSE {cmd_option(final_image(dockerfile), '--port')} only")

    @pytest.mark.parametrize(("final", "builder", "final_base", "passes"), EXPOSE_CASES)
    def test_the_check_can_fail(self, final, builder, final_base, passes):
        """IMG-014b: the same check on synthetic Dockerfiles, the state before C-37 included."""
        print_section("IMG-014b: the EXPOSE check on a synthetic Dockerfile")
        dockerfile = synthetic_dockerfile(final, builder, final_base)

        violations = expose_violations(dockerfile)

        assert (not violations) is passes, f"expected {'no violation' if passes else 'a violation'}, got: {violations}\n{dockerfile}"
        print_success(f"violations: {violations or 'none'}")


class TestPublishedPort:
    def test_only_the_cmd_port(self):
        """IMG-015: in every docker-compose*.yml, service librefolio publishes the CMD's port and no other container port."""
        print_section("IMG-015: compose publishes the CMD's port only")
        composes = repository_composes()

        violations = port_violations(DOCKERFILE.read_text(encoding="utf-8"), composes)

        assert not violations, "\n".join(violations) + f"\nas found:\n{compose_lines(composes, 'ports', 'expose')}"
        print_success(f"{', '.join(composes)}: container port 6040 only")

    @pytest.mark.parametrize(("file", "service", "others", "passes"), PORT_CASES)
    def test_the_check_can_fail(self, file, service, others, passes):
        """IMG-015b: the same check on synthetic compose files, the state before C-37 included; an override need not publish."""
        print_section(f"IMG-015b: the ports check on a synthetic {file}")
        compose = synthetic_compose(service, others)

        violations = port_violations(synthetic_dockerfile("EXPOSE 6040"), {file: compose})

        assert (not violations) is passes, f"expected {'no violation' if passes else 'a violation'}, got: {violations}\n{compose}"
        print_success(f"violations: {violations or 'none'}")


# ===========================================================================
# IMG-016: N-8, the environment compose pins
# ===========================================================================


class TestPinnedEnvironment:
    def test_both_compose_files_pin_it(self):
        """IMG-016: both compose files pin PORT, HOST and LIBREFOLIO_DATA_DIR to the CMD's --port and --host and the image's data directory, mounted as a volume."""
        print_section("IMG-016: PORT, HOST and LIBREFOLIO_DATA_DIR pinned in compose")
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        composes = repository_composes()

        violations = environment_violations(dockerfile, composes)

        assert not violations, "\n".join(violations) + f"\nas found:\n{compose_lines(composes, 'environment', 'volumes')}"
        print_success(f"{', '.join(composes)}: {pinned_environment(dockerfile)}")

    @pytest.mark.parametrize(("file", "service", "passes"), ENVIRONMENT_CASES)
    def test_the_check_can_fail(self, file, service, passes):
        """IMG-016b: the same check on synthetic compose files, the state before N-8 included; an override may leave them out, not change them."""
        print_section(f"IMG-016b: the environment check on a synthetic {file}")
        compose = synthetic_compose(service, {})

        violations = environment_violations(ENVIRONMENT_DOCKERFILE, {file: compose})

        assert (not violations) is passes, f"expected {'no violation' if passes else 'a violation'}, got: {violations}\n{compose}"
        print_success(f"violations: {violations or 'none'}")


# ===========================================================================
# IMG-017..IMG-018: 32-3, docker exec as the image's numeric ids
# ===========================================================================


class TestDockerExec:
    def test_runs_dev_py_through_gosu(self, devpy, monkeypatch):
        """IMG-017: docker exec user list runs, once, sh -c with the gosu script in service librefolio, "sh" as $0 and the arguments after it; its exit status is the command's."""
        print_section("IMG-017: ./dev.py docker exec user list")

        result, runner = docker_exec(devpy, monkeypatch, ["user", "list"], returncode=7)

        assert runner.launches == [(*EXEC_PREFIX, "user", "list")], f"expected one command line, {(*EXEC_PREFIX, 'user', 'list')}; got {runner.launches}"
        assert result == 7, f"docker exec must return the exit status of the command it ran (7), got {result}"
        print_success(shlex.join(runner.launches[0]))

    def test_arguments_never_reach_the_script(self, devpy, monkeypatch):
        """IMG-017b: arguments a shell would split, expand or run follow the "sh" of $0, one element each and in order; the script is the same whatever they are."""
        print_section("IMG-017b: hostile arguments of docker exec")

        _, plain = docker_exec(devpy, monkeypatch, ["user", "list"])
        _, hostile = docker_exec(devpy, monkeypatch, HOSTILE_ARGUMENTS)

        argv = hostile.launches[0] if hostile.launches else ()
        assert argv[: len(EXEC_PREFIX)] == EXEC_PREFIX, f"expected the command line to start with {EXEC_PREFIX}, got {argv}"
        assert argv[len(EXEC_PREFIX) :] == HOSTILE_ARGUMENTS, f"each argument must follow the sh of $0 as one element, in order: {argv[len(EXEC_PREFIX):]}"
        assert in_container(argv)[:3] == in_container(plain.launches[0])[:3], "the sh -c script must not depend on the arguments"
        print_success(f"{len(HOSTILE_ARGUMENTS)} arguments after the sh of $0, the script unchanged")

    @pytest.mark.parametrize("args", [SimpleNamespace(cmd_args=[]), SimpleNamespace()], ids=["empty", "absent"])
    def test_no_command_runs_nothing(self, devpy, monkeypatch, args):
        """IMG-017c: docker exec without a command exits 1 and runs nothing."""
        print_section("IMG-017c: ./dev.py docker exec without a command")
        runner = FakeRunner()
        monkeypatch.setattr(devpy, "run_command_live", runner)

        result = devpy.cmd_docker_exec(args)

        assert result == 1, f"expected exit 1 without a command, got {result}"
        assert runner.launches == [], f"nothing may run without a command, yet: {runner.launches}"
        print_success("exit 1, nothing run")

    @pytest.mark.parametrize(("ids", "expected_ids"), EXEC_ENVIRONMENTS)
    def test_the_container_hands_every_argument_to_dev_py(self, devpy, monkeypatch, tmp_path, ids, expected_ids):
        """IMG-017d: what follows the service name, run by a local sh with stand-ins for gosu and python, passes every argument verbatim to python dev.py, as the ids of the environment or, when it sets neither, entrypoint.sh's 1000:1000."""
        print_section(f"IMG-017d: the container's command under a local sh, gosu and python stood in for, ids {ids or 'unset'}")
        _, runner = docker_exec(devpy, monkeypatch, HOSTILE_ARGUMENTS)
        command = in_container(runner.launches[0])
        stand_ins, app, records = tmp_path / "bin", tmp_path / "app", tmp_path / "records"
        for directory in (stand_ins, app, records):
            directory.mkdir()
        for name, script in (("gosu", GOSU_STAND_IN), ("python", PYTHON_STAND_IN)):
            (stand_ins / name).write_text(script, encoding="utf-8")
            (stand_ins / name).chmod(0o755)
        (app / "dev.py").write_text("# an unquoted * would expand to this name\n", encoding="utf-8")
        # Built from nothing: without ids, the variables are absent, not inherited from this process.
        env = {
            "PATH": os.pathsep.join([str(stand_ins), os.defpath]),
            "REAL_PYTHON": sys.executable,
            "GOSU_RECORD": str(records / "gosu"),
            "ARGV_RECORD": str(records / "argv"),
            **ids,
        }
        assert shutil.which("sh", path=env["PATH"]) and shutil.which("touch", path=env["PATH"]), f"premise: sh runs the command, and touch is there for an argument a shell would run, on PATH={env['PATH']}"

        done = subprocess.run(command, cwd=app, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=RUN_TIMEOUT, check=False)

        assert done.returncode == 0, f"`{shlex.join(command)}` exited {done.returncode}:\n{done.stdout}{done.stderr}"
        source = "LIBREFOLIO_UID:LIBREFOLIO_GID of the environment" if ids else "the fallback, the environment setting neither variable"
        assert read_text(records / "gosu") == expected_ids, f"gosu must get {expected_ids}, {source}; got {read_text(records / 'gosu')!r}"
        received = json.loads(read_text(records / "argv") or "null")
        assert received == ["dev.py", *HOSTILE_ARGUMENTS], f"python must get dev.py and every argument verbatim, got {received}"
        assert not (app / CANARY).exists(), f"an argument was run by the shell: {app / CANARY} exists"
        if not ids:
            entrypoint_ids = fallback_ids(ENTRYPOINT.read_text(encoding="utf-8"))
            assert entrypoint_ids == expected_ids, f"entrypoint.sh falls back to {entrypoint_ids!r}, docker exec to {expected_ids}: in an image that sets neither variable, the server and docker exec would run as different ids"
        print_success(f"gosu {expected_ids}, python dev.py and {len(HOSTILE_ARGUMENTS)} arguments verbatim, nothing run")


class TestExecIds:
    def test_the_image_sets_them(self, devpy, monkeypatch):
        """IMG-018: the ids the docker exec script hands gosu are set, non-empty, by an ENV of the final image: its fallback is for an image older than that ENV."""
        print_section("IMG-018: LIBREFOLIO_UID and LIBREFOLIO_GID in the image")
        _, runner = docker_exec(devpy, monkeypatch, ["user", "list"])
        script = in_container(runner.launches[0])[2]
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")

        violations = exec_id_violations(script, dockerfile)

        assert not violations, "\n".join(violations) + f"\nENV instructions of the final image:\n{final_lines(dockerfile, 'ENV')}"
        print_success(f"gosu {gosu_target(script)}: set by the final image")

    @pytest.mark.parametrize(("script", "final", "builder", "final_base", "passes"), EXEC_ID_CASES)
    def test_the_check_can_fail(self, script, final, builder, final_base, passes):
        """IMG-018b: the same check on synthetic Dockerfiles and scripts."""
        print_section("IMG-018b: the exec ids check on a synthetic Dockerfile")
        dockerfile = synthetic_dockerfile(final, builder, final_base)

        violations = exec_id_violations(script, dockerfile)

        assert (not violations) is passes, f"expected {'no violation' if passes else 'a violation'}, got: {violations}\n{script}\n{dockerfile}"
        print_success(f"violations: {violations or 'none'}")


# ===========================================================================
# IMG-019..IMG-024: M-25, one version for the bundle, VERSION and the tag
# ===========================================================================


class TestFrontendStaleReason:
    @pytest.mark.parametrize(("sources_changed", "mode", "recorded", "expected"), STALE_CASES)
    def test_reason(self, devpy, markers, sources_changed, mode, recorded, expected):
        """IMG-019: the sources changed, then a build not known to be production, then no recorded version, then another one; None when the bundle fits."""
        print_section(f"IMG-019: stale reason, sources changed {sources_changed}, .build-debug {mode!r}, .build-version {recorded!r}")
        markers.write(mode=mode, version=recorded)

        reason = devpy._docker_frontend_stale_reason(FROZEN, lambda: sources_changed)

        assert reason == expected, f"image version {FROZEN}, sources changed {sources_changed}, .build-debug {mode!r}, .build-version {recorded!r}: expected {expected!r}, got {reason!r}"
        print_success(f"{reason!r}")


class TestFrontendBuild:
    @pytest.mark.parametrize("previous", [None, OUTER_APP_VERSION], ids=["unset-before", "set-before"])
    def test_a_build_that_succeeds_records_the_version(self, devpy, markers, monkeypatch, previous):
        """IMG-020: the build runs in production mode with LF_APP_VERSION set to the version, which is then given back; .build-version records it afterwards."""
        print_section(f"IMG-020: a frontend build that succeeds, LF_APP_VERSION {previous!r} before")
        markers.write(mode="0", version=None)
        given_app_version(monkeypatch, previous)
        build = FakeFrontendBuild(0, markers.version)
        monkeypatch.setattr(devpy, "cmd_fe_build", build)

        result = devpy._docker_ensure_frontend_built(FROZEN, lambda: True)

        assert build.calls == [BuildCall(app_version=FROZEN, debug=False, recorded_version=None)], f"one production build, with LF_APP_VERSION={FROZEN} and nothing recorded yet: {build.calls}"
        assert os.environ.get(APP_VERSION) == previous, f"LF_APP_VERSION must be {previous!r} again after the build, is {os.environ.get(APP_VERSION)!r}"
        assert result == 0 and read_text(markers.version) == FROZEN, f"result {result}, .build-version {read_text(markers.version)!r}: expected 0 and {FROZEN}"
        print_success(f"built with {FROZEN}, recorded, LF_APP_VERSION back to {previous!r}")

    @pytest.mark.parametrize("previous", [None, OUTER_APP_VERSION], ids=["unset-before", "set-before"])
    def test_a_build_that_fails_records_nothing(self, devpy, markers, monkeypatch, previous):
        """IMG-020: a build that fails: its exit status comes back, LF_APP_VERSION is given back, and no version is recorded."""
        print_section(f"IMG-020: a frontend build that fails, LF_APP_VERSION {previous!r} before")
        markers.write(mode="0", version=None)
        given_app_version(monkeypatch, previous)
        build = FakeFrontendBuild(3, markers.version)
        monkeypatch.setattr(devpy, "cmd_fe_build", build)

        result = devpy._docker_ensure_frontend_built(FROZEN, lambda: True)

        assert [call.app_version for call in build.calls] == [FROZEN], f"the build must run once with LF_APP_VERSION={FROZEN}: {build.calls}"
        assert result == 3, f"the build's exit status (3) must come back, got {result}"
        assert os.environ.get(APP_VERSION) == previous, f"LF_APP_VERSION must be {previous!r} again after a failed build, is {os.environ.get(APP_VERSION)!r}"
        assert read_text(markers.version) is None, f"a failed build must record no version: .build-version says {read_text(markers.version)!r}"
        print_success(f"exit 3, nothing recorded, LF_APP_VERSION back to {previous!r}")

    @pytest.mark.parametrize("previous", [None, OUTER_APP_VERSION], ids=["unset-before", "set-before"])
    def test_a_build_that_raises_records_nothing(self, devpy, markers, monkeypatch, previous):
        """IMG-020: a build that raises: the exception goes through, LF_APP_VERSION is given back, and no version is recorded."""
        print_section(f"IMG-020: a frontend build that raises, LF_APP_VERSION {previous!r} before")
        markers.write(mode="0", version=None)
        given_app_version(monkeypatch, previous)
        build = FakeFrontendBuild(BuildCrash("the stand-in build crashed"), markers.version)
        monkeypatch.setattr(devpy, "cmd_fe_build", build)

        with pytest.raises(BuildCrash):
            devpy._docker_ensure_frontend_built(FROZEN, lambda: True)

        assert [call.app_version for call in build.calls] == [FROZEN], f"the build must run once with LF_APP_VERSION={FROZEN}: {build.calls}"
        assert os.environ.get(APP_VERSION) == previous, f"LF_APP_VERSION must be {previous!r} again after a crashed build, is {os.environ.get(APP_VERSION)!r}"
        assert read_text(markers.version) is None, f"a crashed build must record no version: .build-version says {read_text(markers.version)!r}"
        print_success(f"raised, nothing recorded, LF_APP_VERSION back to {previous!r}")

    @pytest.mark.parametrize("previous", [None, OUTER_APP_VERSION], ids=["unset-before", "set-before"])
    def test_a_bundle_that_fits_is_kept(self, devpy, markers, monkeypatch, previous):
        """IMG-020b: a production bundle recorded with this version is not rebuilt, and LF_APP_VERSION and the markers stay as they are."""
        print_section(f"IMG-020b: a frontend bundle that fits, LF_APP_VERSION {previous!r} before")
        markers.write(mode="0", version=FROZEN)
        given_app_version(monkeypatch, previous)
        build = FakeFrontendBuild(0, markers.version)
        monkeypatch.setattr(devpy, "cmd_fe_build", build)

        result = devpy._docker_ensure_frontend_built(FROZEN, lambda: False)

        assert result == 0 and build.calls == [], f"a bundle that fits must not be rebuilt: result {result}, builds {build.calls}"
        assert os.environ.get(APP_VERSION) == previous and read_text(markers.version) == FROZEN, f"nothing may change: LF_APP_VERSION {os.environ.get(APP_VERSION)!r}, .build-version {read_text(markers.version)!r}"
        print_success("kept, nothing changed")


class TestFrozenVersion:
    @pytest.mark.parametrize(("sources_changed", "recorded", "rebuilds"), ASSET_CASES)
    def test_one_version_for_the_bundle_and_version(self, devpy, project, markers, monkeypatch, sources_changed, recorded, rebuilds):
        """IMG-021: the version step 0 freezes (VERSION removed, the cache cleared) reaches the frontend build and VERSION, though git answers -dirty after the first step."""
        print_section(f"IMG-021: _docker_ensure_assets_built, sources changed {sources_changed}, bundle recorded as {recorded}")
        markers.write(mode="0", version=recorded)
        monkeypatch.setattr(cli_base, "check_frontend_needs_build", lambda: sources_changed)
        given_app_version(monkeypatch, None)

        result = devpy._docker_ensure_assets_built()

        assert result == 0, f"the asset build failed with {result}: {project.steps.calls}"
        assert project.git.answers == [Answer(FROZEN, version_file_existed=False, cache_cleared=True)], f"step 0 must ask git once, afresh, after removing the previous VERSION and clearing the cache: {project.git.answers}"
        assert [(call.app_version, call.detail) for call in project.builds()] == ([(FROZEN, {"debug": False})] if rebuilds else []), f"expected {'one production build with LF_APP_VERSION=' + FROZEN if rebuilds else 'no build'}: {project.builds()}"
        assert {call.app_version for call in project.other_steps()} == {None}, f"LF_APP_VERSION must be set during the frontend build only: {project.other_steps()}"
        assert read_text(project.version_file) == FROZEN, f"VERSION must hold the frozen {FROZEN}, holds {read_text(project.version_file)!r}"
        assert read_text(markers.version) == FROZEN, f".build-version must record {FROZEN}, records {read_text(markers.version)!r}"
        assert os.environ.get(APP_VERSION) is None, f"LF_APP_VERSION must be unset again, is {os.environ.get(APP_VERSION)!r}"
        assert all(call.tree_dirty for call in project.builds()) and project.git.fresh() == DRIFTED, "premise: the tree was dirty before the build and before VERSION, so a late read of git would have said -dirty"
        print_success(f"bundle {'rebuilt' if rebuilds else 'kept'}, VERSION and .build-version {FROZEN}; git now says {DRIFTED}")


class TestDockerTag:
    def test_the_override_wins(self, devpy, project):
        """IMG-022: a tag given on the command line is the tag: VERSION is not read and git not asked."""
        print_section("IMG-022: _get_docker_tag with an override")
        project.version_file.write_text(FROZEN, encoding="utf-8")

        tag = devpy._get_docker_tag(CUSTOM_TAG)

        assert tag == CUSTOM_TAG and project.git.answers == [], f"expected {CUSTOM_TAG} and no git answer, got {tag!r} and {project.git.answers}"
        print_success(tag)

    @pytest.mark.parametrize(("content", "expected"), TAG_CASES)
    def test_the_tag_follows_version(self, devpy, project, content, expected):
        """IMG-022: the tag is librefolio: and the stripped VERSION while it says something; a fresh git answer only when VERSION is missing or blank."""
        print_section(f"IMG-022: _get_docker_tag, VERSION {content!r}, git saying {DRIFTED}")
        project.git.dirty = True  # a build step wrote to the tree: a fresh read says -dirty
        if content is None:
            project.version_file.unlink()
        else:
            project.version_file.write_text(content, encoding="utf-8")

        tag = devpy._get_docker_tag(None)

        asked = [answer.value for answer in project.git.answers]
        assert tag == expected, f"VERSION {content!r}, git saying {DRIFTED}: expected {expected}, got {tag!r}"
        assert asked == ([] if (content or "").strip() else [DRIFTED]), f"git must be asked afresh exactly when VERSION is missing or blank: {project.git.answers}"
        print_success(tag)


class TestDockerBuild:
    @pytest.mark.parametrize(("options", "tags"), BUILD_CASES)
    def test_the_image_carries_one_version(self, devpy, project, markers, monkeypatch, options, tags):
        """IMG-023: docker build tags the image with the version of VERSION and of the bundle (-light for the light variant), not git's later -dirty; a --tag override stays."""
        print_section(f"IMG-023: ./dev.py docker build {options or ''}")
        (project.root / ".env").write_text("PORT=6040\n", encoding="utf-8")
        markers.write(mode="0", version=PREVIOUS_BUILD)
        monkeypatch.setattr(cli_base, "check_frontend_needs_build", lambda: False)
        given_app_version(monkeypatch, None)
        runner = FakeRunner()
        monkeypatch.setattr(devpy, "run_command_live", runner)

        result = devpy.cmd_docker_build(SimpleNamespace(**{"tag": None, "no_cache": False, "light": False, **options}))

        assert result == 0 and len(runner.launches) == 1, f"expected one docker build and exit 0: result {result}, launches {runner.launches}"
        assert image_tags(runner.launches[0]) == tags, f"expected the tags {tags}, got {image_tags(runner.launches[0])} in {runner.launches[0]}"
        assert read_text(project.version_file) == FROZEN and [call.app_version for call in project.builds()] == [FROZEN], f"VERSION {read_text(project.version_file)!r} and the bundle {project.builds()} must carry {FROZEN}"
        assert len(project.git.answers) == 1 and project.git.fresh() == DRIFTED, f"premise: git was asked once, at step 0, and says {DRIFTED} by now: {project.git.answers}"
        print_success(f"tags {', '.join(tags)}; VERSION and bundle {FROZEN}")


class TestEnvFileCheck:
    def test_only_port_is_compared(self, devpy, monkeypatch, tmp_path, capsys):
        """IMG-024: a shell PORT that differs from .env's is reported; TEST_PORT is no longer a Docker variable, so it is not."""
        print_section("IMG-024: _check_env_file, PORT and TEST_PORT both differing")
        root = tmp_path / "project"
        root.mkdir()
        (root / ".env").write_text("PORT=6040\nTEST_PORT=6041\n", encoding="utf-8")
        monkeypatch.setattr(devpy, "PROJECT_ROOT", root)
        monkeypatch.setenv("PORT", "8080")
        monkeypatch.setenv("TEST_PORT", "9191")
        capsys.readouterr()  # the section header above names TEST_PORT: only what _check_env_file prints counts

        result = devpy._check_env_file()

        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert result is True, f"a .env that exists passes, got {result!r}:\n{output}"
        assert any("PORT" in line and "8080" in line and "6040" in line for line in output.splitlines()), f"expected a warning naming PORT, 8080 and 6040:\n{output}"
        assert not any(word in output for word in ("TEST_PORT", "9191", "6041")), f"TEST_PORT must not be compared any more:\n{output}"
        print_success("PORT reported, TEST_PORT not")
