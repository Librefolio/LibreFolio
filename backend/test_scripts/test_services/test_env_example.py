"""
The ``.env.example`` guard (workstream H, platform, checkpoint CP3).

``.env.example`` is the one list of every option LibreFolio reads: users copy it to their ``.env``, the image ships it as
``/app/.env``, and the admin documentation points to it. A variable the code reads and the file does not list is an
option nobody can find. Six rules:

1. Every environment variable read with a literal name anywhere under ``backend/app/`` has a variable line, except the
   names declared undocumented on purpose in ``UNDOCUMENTED_ON_PURPOSE``, each with its reason.
2. Every field of ``Settings`` (which pydantic-settings reads from the environment and ``.env``) has a variable line,
   except ``DATABASE_URL``: ``get_settings()`` computes it from the data directory, so it has none.
3. Every variable Docker Compose substitutes in ``docker-compose.yml`` and ``docker-compose.prod.yml`` has a variable
   line.
4. ``UNDOCUMENTED_ON_PURPOSE`` is a ratchet: each name is still read somewhere under ``backend/app/`` and still has no
   variable line, or its entry goes.
5. The uncommented lines are exactly the nine of today, in order. The file is copied into the image as ``/app/.env`` and
   by users as their ``.env``, so a new uncommented line would change the behaviour of every install: a new option is
   added commented, with its default.
6. No variable has two variable lines.

A variable line is ``NAME=...`` (uncommented) or ``# NAME=...`` (commented), ``NAME`` matching ``[A-Z_][A-Z0-9_]*``.

What a read is, for rule 1. The sources are parsed with ``ast``, never imported. A read is ``os.environ.get("X")``,
``os.environ["X"]`` where it is loaded, ``"X" in os.environ`` and ``os.getenv("X")``, reached through ``os``, an alias
of it, or the names ``from os import`` binds. A function that reads the variable named by one of its parameters (such
as ``env_secret(name)`` or ``env_secret_origin(name)``) forwards that parameter: a call to it with a literal reads the
literal. A key built as ``parameter + SUFFIX`` (``name + SECRET_FILE_SUFFIX``) appends the suffix, so
``env_secret("X")`` reads both ``X`` and ``X_FILE``; and a function that passes its own parameter on to a forwarder
forwards it too. Writes (``os.environ["X"] = ...``, ``del os.environ["X"]``) are not reads.

Not seen: a name built at run time outside that pattern (an f-string, a loop over ``os.environ``), keyword arguments of
``os.getenv``, a forwarder method called through ``self``, and the variables libraries read for themselves. The rule is
about the options LibreFolio reads itself, and those are written as above.

Pure: the sources, ``.env.example`` and the compose files are read as text, and the only import from the application
is the ``Settings`` class. The guard asserts absences, so presence barriers come first: the detector flags every shape
of a synthetic source and nothing else, the parsers of ``.env.example`` and of the compose files are shown to tell
variables from prose, and the scan of ``backend/app/`` must find variables known to be read.
"""

from __future__ import annotations

import ast
import functools
import re
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest
import yaml

from backend.app.config import Settings
from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "backend" / "app"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
COMPOSE_FILES = ("docker-compose.yml", "docker-compose.prod.yml")

#: (1)(4) Read by the application and kept out of .env.example on purpose, with the reason. A ratchet: an entry whose
#: variable is no longer read, or gets a variable line, fails until it is removed.
UNDOCUMENTED_ON_PURPOSE: dict[str, str] = {
    "FLY_APP_NAME": "set by Fly.io on every machine, read for the idle suspension (config/sleep_wake.py); not an option",
    "FLY_MACHINE_ID": "set by Fly.io on every machine, read for the idle suspension (config/sleep_wake.py); not an option",
    "LIBREFOLIO_DISABLE_DONATION_POPUP": "workstream A keeps the hidden switch out of .env.example and the docs",
    "LIBREFOLIO_DISABLE_WHATS_NEW": "workstream A keeps the hidden switch of the «What's new» modal (C-54) out of .env.example and the admin docs, as the donation popup's (D-A7)",
    "LIBREFOLIO_TEST_LANE_ID": "internal token the test runner sets for the server it owns",
}

#: (5) The uncommented lines of .env.example, in order: the configuration every install starts from.
UNCOMMENTED_LINES = (
    "HOST=0.0.0.0",
    "PORT=6040",
    "LIBREFOLIO_DATA_DIR=./backend/data/prod",
    "TEST_PORT=6041",
    "LIBREFOLIO_TEST_DATA_DIR=./backend/data/test",
    "LOG_LEVEL=INFO",
    "PREVIEW_CACHE_MAX_MB=50",
    "UID=1000",
    "GID=1000",
)

#: Presence barrier: variables backend/app/ is known to read, the _FILE ones only through env_secret. The scan must
#: find them all, and at least one LIBREFOLIO_WEB_LINK_FINDER_* variable.
KNOWN_READS = frozenset(
    {
        "JWT_SECRET",
        "JWT_SECRET_FILE",
        "LIBREFOLIO_INSTANCE_KEY",
        "LIBREFOLIO_INSTANCE_KEY_FILE",
        "LIBREFOLIO_DATA_DIR",
        "LIBREFOLIO_TEST_MODE",
        "LIBREFOLIO_NO_SCHEDULER",
    }
)
LINK_FINDER_PREFIX = "LIBREFOLIO_WEB_LINK_FINDER_"

VARIABLE_LINE = re.compile(r"^(?P<comment>#\s*)?(?P<name>[A-Z_][A-Z0-9_]*)=")
#: ``${NAME``, ``${NAME:-default}``, ``$NAME``; ``$$`` is Compose's escape of a literal ``$``.
COMPOSE_VARIABLE = re.compile(r"(?<!\$)\$\{?(?P<name>[A-Za-z_][A-Za-z0-9_]*)")
#: Forwarders that pass a parameter on to another forwarder: a bound on the chain, which real code never comes near.
MAX_FORWARDING_DEPTH = 10


# =============================================================================
# .env.example and the compose files
# =============================================================================


class VariableLine(NamedTuple):
    number: int
    name: str
    commented: bool


def _variable_lines(text: str) -> list[VariableLine]:
    """The ``NAME=`` and ``# NAME=`` lines of a dotenv text, with their line numbers."""
    return [VariableLine(number, match["name"], match["comment"] is not None) for number, line in enumerate(text.splitlines(), start=1) if (match := VARIABLE_LINE.match(line))]


def _uncommented_lines(text: str) -> list[str]:
    """Every line that is neither blank nor a comment: what a dotenv parser acts on."""
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]


@functools.cache
def _env_example_lines() -> tuple[VariableLine, ...]:
    return tuple(_variable_lines(ENV_EXAMPLE.read_text(encoding="utf-8")))


def _documented() -> set[str]:
    return {line.name for line in _env_example_lines()}


def _strings(node: object) -> Iterator[str]:
    """Every string of a parsed YAML document, keys and values: where Compose may substitute variables."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(key)
            yield from _strings(value)
    elif isinstance(node, list):
        for item in node:
            yield from _strings(item)


def _compose_variables(text: str) -> set[str]:
    """The variables Compose substitutes in a compose file: parsed as YAML, so a ``${NAME}`` in a comment is not one."""
    return {match["name"] for string in _strings(yaml.safe_load(text)) for match in COMPOSE_VARIABLE.finditer(string)}


# =============================================================================
# The detector of environment reads
# =============================================================================


class Forwarder(NamedTuple):
    """A parameter of a function that names the variable the function reads: its position (None if keyword-only) and the suffix appended."""

    position: int | None
    parameter: str
    suffix: str


class Module(NamedTuple):
    path: str
    tree: ast.Module
    parents: dict[ast.AST, ast.AST]
    constants: dict[str, str]


def _module(path: str, source: str) -> Module:
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    constants = {}
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        value = _literal(getattr(node, "value", None))
        constants.update({target.id: value for target in targets if isinstance(target, ast.Name) and value is not None})
    return Module(path, tree, parents, constants)


def _literal(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _environment_members(tree: ast.Module) -> tuple[set[str], dict[str, str]]:
    """The names bound to ``os`` (``import os``, ``import os as alias``, ``import os.path``) and those ``from os import`` binds to ``environ``/``getenv``."""
    modules, members = set(), {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.asname or "os" for alias in node.names if alias.name == "os" or (alias.name.startswith("os.") and alias.asname is None))
        elif isinstance(node, ast.ImportFrom) and node.module == "os" and node.level == 0:
            members.update({alias.asname or alias.name: alias.name for alias in node.names if alias.name in ("environ", "getenv")})
    return modules, members


def _read_keys(tree: ast.Module) -> Iterator[tuple[ast.AST, ast.expr]]:
    """Every environment read of ``tree``, as ``(node, expression of the variable name)``."""
    modules, members = _environment_members(tree)

    def is_member(node: ast.AST, member: str) -> bool:
        if isinstance(node, ast.Attribute):
            return node.attr == member and isinstance(node.value, ast.Name) and node.value.id in modules
        return isinstance(node, ast.Name) and members.get(node.id) == member

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and node.args:
            function = node.func
            if (isinstance(function, ast.Attribute) and function.attr == "get" and is_member(function.value, "environ")) or is_member(function, "getenv"):
                yield node, node.args[0]
        elif isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load) and is_member(node.value, "environ"):
            yield node, node.slice
        elif isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In | ast.NotIn) and is_member(node.comparators[0], "environ"):
            yield node, node.left


def _forwarded(key: ast.expr, node: ast.AST, module: Module) -> tuple[str, Forwarder] | None:
    """``key`` names a parameter of the function around ``node``, maybe plus a suffix: ``(function name, Forwarder)``."""
    function = node
    while function is not None and not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
        function = module.parents.get(function)
    if function is None:
        return None
    parameter, suffix = None, ""
    if isinstance(key, ast.Name):
        parameter = key.id
    elif isinstance(key, ast.BinOp) and isinstance(key.op, ast.Add) and isinstance(key.left, ast.Name):
        parameter = key.left.id
        suffix = _literal(key.right) if not isinstance(key.right, ast.Name) else module.constants.get(key.right.id)
    positional = [argument.arg for argument in (*function.args.posonlyargs, *function.args.args)]
    if suffix is None or parameter not in positional + [argument.arg for argument in function.args.kwonlyargs]:
        return None
    return function.name, Forwarder(positional.index(parameter) if parameter in positional else None, parameter, suffix)


def _resolve(key: ast.expr, node: ast.AST, module: Module, suffix: str, reads: dict[str, set[str]], forwarders: dict[str, set[Forwarder]]) -> bool:
    """Record what reading ``key`` + ``suffix`` at ``node`` means: a literal read, or a new forwarder (then True)."""
    literal = _literal(key)
    if literal is not None:
        reads[literal + suffix].add(f"{module.path}:{node.lineno}")
        return False
    forwarded = _forwarded(key, node, module)
    if forwarded is None:
        return False
    function, forwarder = forwarded
    forwarder = forwarder._replace(suffix=forwarder.suffix + suffix)
    if forwarder in forwarders[function]:
        return False
    forwarders[function].add(forwarder)
    return True


def _argument(call: ast.Call, forwarder: Forwarder) -> ast.expr | None:
    """The argument a call passes for the forwarded parameter, by position or by keyword."""
    positional = call.args[: forwarder.position + 1] if forwarder.position is not None else []
    if forwarder.position is not None and len(positional) > forwarder.position and not any(isinstance(argument, ast.Starred) for argument in positional):
        return positional[forwarder.position]
    return next((keyword.value for keyword in call.keywords if keyword.arg == forwarder.parameter), None)


def _calls_to(tree: ast.Module, functions: dict[str, set[Forwarder]]) -> Iterator[tuple[ast.Call, str]]:
    """The calls of ``tree`` to a forwarder, by its name: ``env_secret(...)`` and ``config.env_secret(...)`` alike."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else None
            if name in functions:
                yield node, name


def environment_reads(sources: dict[str, str]) -> dict[str, set[str]]:
    """Every variable read with a literal name in ``sources`` (path → text), with where: ``{"JWT_SECRET": {"config/platform.py:32"}}``."""
    modules = [_module(path, source) for path, source in sources.items()]
    reads: dict[str, set[str]] = defaultdict(set)
    forwarders: dict[str, set[Forwarder]] = defaultdict(set)
    for module in modules:
        for node, key in _read_keys(module.tree):
            _resolve(key, node, module, "", reads, forwarders)
    for _ in range(MAX_FORWARDING_DEPTH):
        grew = False
        for module in modules:
            for call, name in _calls_to(module.tree, forwarders):
                for forwarder in tuple(forwarders[name]):
                    argument = _argument(call, forwarder)
                    if argument is not None:
                        grew = _resolve(argument, call, module, forwarder.suffix, reads, forwarders) or grew
        if not grew:
            break
    return dict(reads)


@functools.cache
def _application_reads() -> dict[str, set[str]]:
    """The environment reads of every module under ``backend/app/``."""
    return environment_reads({path.relative_to(APP_ROOT).as_posix(): path.read_text(encoding="utf-8") for path in sorted(APP_ROOT.rglob("*.py"))})


# =============================================================================
# Presence barriers: the detector and the parsers see what they look for
# =============================================================================

#: (source, variables read). Every shape of a read, alone in a synthetic module.
_READ_SHAPES = (
    pytest.param('import os\nos.environ.get("A")\n', {"A"}, id="environ-get"),
    pytest.param('import os\nos.environ.get("A", "default")\n', {"A"}, id="environ-get-default"),
    pytest.param('import os\nvalue = os.environ["A"]\n', {"A"}, id="environ-item"),
    pytest.param('import os\npresent = "A" in os.environ\n', {"A"}, id="in-environ"),
    pytest.param('import os\nabsent = "A" not in os.environ\n', {"A"}, id="not-in-environ"),
    pytest.param('import os\nos.getenv("A")\n', {"A"}, id="getenv"),
    pytest.param('import os as system\nsystem.environ.get("A")\nsystem.getenv("B")\n', {"A", "B"}, id="os-alias"),
    pytest.param('import os.path\nos.environ.get("A")\n', {"A"}, id="import-os-path"),
    pytest.param('from os import environ\nenviron.get("A")\nenviron["B"]\n', {"A", "B"}, id="from-os-import-environ"),
    pytest.param('from os import environ as env, getenv as read\nenv.get("A")\nread("B")\n', {"A", "B"}, id="from-os-import-aliases"),
    pytest.param('def load():\n    import os\n\n    return os.environ.get("A")\n', {"A"}, id="inside-a-function"),
    pytest.param('import os\n\n\ndef _env_int(name, default):\n    return int(os.environ.get(name, default))\n\n\nLIMIT = _env_int("A", 5)\n', {"A"}, id="forwarder"),
    pytest.param('import os\n\n\ndef read(prefix, name):\n    return os.environ.get(name)\n\n\nread("not-a-variable", "A")\nread(name="B", prefix="x")\n', {"A", "B"}, id="forwarder-second-parameter-or-keyword"),
    pytest.param('import os\n\n\ndef read(*, name):\n    return os.getenv(name)\n\n\nread(name="A")\n', {"A"}, id="forwarder-keyword-only"),
    pytest.param('import os\n\n\ndef secret(name):\n    return os.environ.get(name + "_FILE")\n\n\nsecret("A")\n', {"A_FILE"}, id="forwarder-literal-suffix"),
    pytest.param('import os\n\nSUFFIX = "_FILE"\n\n\ndef secret(name):\n    return os.environ.get(name) or os.environ.get(name + SUFFIX)\n\n\nsecret("A")\n', {"A", "A_FILE"}, id="forwarder-constant-suffix"),
    pytest.param('import os\n\n\ndef secret(name):\n    return os.environ.get(name)\n\n\ndef token(name):\n    return secret(name + "_TOKEN")\n\n\ntoken("A")\n', {"A_TOKEN"}, id="forwarder-chain"),
)

#: Sources that read no variable with a literal name: writes, run-time names, look-alikes.
_NO_READ_SHAPES = (
    pytest.param('import os\nos.environ["A"] = "1"\n', id="item-assignment"),
    pytest.param('import os\ndel os.environ["A"]\n', id="item-deletion"),
    pytest.param("import os\nos.environ.get(name)\n", id="name-not-a-literal"),
    pytest.param('import os\n\n\ndef read(name):\n    return os.environ.get(PREFIX + name)\n\n\nread("A")\n', id="name-built-at-run-time"),
    pytest.param('import os\n\n\ndef echo(name):\n    return name\n\n\necho("A")\nos.path.join("B")\n', id="function-that-reads-nothing"),
    pytest.param('environ = {}\nenviron.get("A")\n', id="environ-not-from-os"),
    pytest.param('settings = {}\nsettings.get("A")\nvalue = settings["B"]\n', id="another-mapping"),
)


@pytest.mark.parametrize(("source", "expected"), _READ_SHAPES)
def test_the_detector_finds_every_shape_of_a_read(source, expected):
    found = set(environment_reads({"synthetic.py": source}))
    assert found == expected, f"the detector found {sorted(found)} in this source, expected {sorted(expected)}:\n{source}"
    print_success(f"{sorted(found)}")


@pytest.mark.parametrize("source", _NO_READ_SHAPES)
def test_the_detector_finds_no_read_where_there_is_none(source):
    found = environment_reads({"synthetic.py": source})
    assert not found, f"the detector found reads in a source that has none: {found}\n{source}"
    print_success("no read")


def test_the_detector_follows_a_forwarder_across_modules():
    """``env_secret`` is defined in the config package and called from section modules, by name or through the package."""
    found = environment_reads(
        {
            "config/__init__.py": 'import os\n\n\ndef env_secret(name):\n    return os.environ.get(name) or os.environ.get(name + SECRET_FILE_SUFFIX)\n\n\nSECRET_FILE_SUFFIX = "_FILE"\n',
            "config/platform.py": 'from config import env_secret\n\n\ndef jwt():\n    return env_secret("A")\n',
            "elsewhere.py": 'import config\n\nconfig.env_secret("B")\n',
        }
    )
    assert found == {"A": {"config/platform.py:5"}, "A_FILE": {"config/platform.py:5"}, "B": {"elsewhere.py:3"}, "B_FILE": {"elsewhere.py:3"}}, f"a forwarder must be followed into every module that calls it: {found}"
    print_success(f"{sorted(found)}")


def test_the_env_example_parser_tells_variable_lines_from_prose():
    text = "A=1\n# B=2\n#C=\n#   D_E=x   # with a comment\n# Prose mentioning F=1\n  # G=1\nh=1\nexport I=1\n# J =1\n\n#\n"
    assert _variable_lines(text) == [VariableLine(1, "A", False), VariableLine(2, "B", True), VariableLine(3, "C", True), VariableLine(4, "D_E", True)], f"wrong variable lines: {_variable_lines(text)}"
    assert _uncommented_lines(text) == ["A=1", "h=1", "export I=1"], f"wrong uncommented lines: {_uncommented_lines(text)}"
    lines = _env_example_lines()
    assert any(line.commented for line in lines) and any(not line.commented for line in lines), f"{ENV_EXAMPLE} must yield commented and uncommented variable lines: {lines}"
    print_success(f"{ENV_EXAMPLE.name}: {len(lines)} variable lines")


def test_the_compose_parser_finds_substitutions_and_ignores_comments_and_escapes():
    text = "# ${IN_A_COMMENT} $USER\nservices:\n  app:\n    image: ${IMAGE:-app:latest}\n    ports: ['${PORT:-1}:1', '$BARE']\n    command: echo $$ESCAPED ${NESTED:-${INNER}}\n"
    assert _compose_variables(text) == {"IMAGE", "PORT", "BARE", "NESTED", "INNER"}, f"wrong compose variables: {_compose_variables(text)}"
    print_success("substitutions found, comments and $$ escapes ignored")


def test_the_scan_of_the_application_finds_the_variables_known_to_be_read():
    """Presence barrier: rule 1 asserts an absence, so the real scan must first find what is known to be there."""
    print_section(".env.example: the scan of backend/app/")
    reads = _application_reads()
    missing = sorted(KNOWN_READS - set(reads))
    assert not missing, f"the scan of {APP_ROOT} missed variables known to be read: {missing}. Found: {sorted(reads)}"
    link_finder = sorted(name for name in reads if name.startswith(LINK_FINDER_PREFIX))
    assert link_finder, f"the scan of {APP_ROOT} found no {LINK_FINDER_PREFIX}* variable: {sorted(reads)}"
    print_success(f"{len(reads)} variables read under backend/app/, the {len(KNOWN_READS)} known ones and {len(link_finder)} {LINK_FINDER_PREFIX}* among them")


# =============================================================================
# The rules
# =============================================================================


def test_every_variable_the_application_reads_is_in_env_example():
    """(1) A variable the code reads and .env.example does not list is an option nobody can find."""
    documented = _documented()
    undocumented = {name: sorted(where) for name, where in _application_reads().items() if name not in documented and name not in UNDOCUMENTED_ON_PURPOSE}
    assert not undocumented, f"variables read under backend/app/ without a line in {ENV_EXAMPLE.name}: add each, commented and with its default, to the section of its owner:\n" + "\n".join(f"  {name}: read at {', '.join(where)}" for name, where in sorted(undocumented.items()))
    print_success(f"{len(_application_reads())} variables read, all documented or declared undocumented on purpose")


def test_every_setting_is_in_env_example_but_the_computed_database_url():
    """(2) pydantic-settings reads every field of Settings from the environment and .env: each is an option."""
    fields = set(Settings.model_fields) - {"DATABASE_URL"}
    assert {"PORT", "LOG_LEVEL", "SESSION_COOKIE_SECURE"} <= fields, f"Settings lost fields it is known to have: {sorted(fields)}"
    documented = _documented()
    missing = sorted(fields - documented)
    assert not missing, f"fields of Settings without a line in {ENV_EXAMPLE.name}: {missing}. Add each, commented and with its default"
    assert "DATABASE_URL" not in documented, f"{ENV_EXAMPLE.name} has a DATABASE_URL line, but get_settings() computes it from the data directory and ignores any value"
    print_success(f"{len(fields)} settings documented, DATABASE_URL not")


@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_every_variable_of_a_compose_file_is_in_env_example(compose_file):
    """(3) Compose substitutes these from .env: an undocumented one is a knob users cannot see."""
    variables = _compose_variables((REPO_ROOT / compose_file).read_text(encoding="utf-8"))
    assert {"PORT", "LIBREFOLIO_IMAGE"} <= variables, f"{compose_file}: the scan missed PORT or LIBREFOLIO_IMAGE, which it substitutes: {sorted(variables)}"
    missing = sorted(variables - _documented())
    assert not missing, f"{compose_file} substitutes variables without a line in {ENV_EXAMPLE.name}: {missing}"
    print_success(f"{compose_file}: {sorted(variables)} documented")


@pytest.mark.parametrize("name", sorted(UNDOCUMENTED_ON_PURPOSE))
def test_a_variable_undocumented_on_purpose_is_still_read_and_still_undocumented(name):
    """(4) The exceptions are a ratchet: an entry goes as soon as it no longer excuses anything."""
    reason = UNDOCUMENTED_ON_PURPOSE[name]
    assert name in _application_reads(), f"{name} is no longer read under backend/app/: remove it from UNDOCUMENTED_ON_PURPOSE ({reason})"
    lines = [line.number for line in _env_example_lines() if line.name == name]
    assert not lines, f"{name} has a variable line in {ENV_EXAMPLE.name} (line {lines}) although it is declared undocumented on purpose ({reason}): remove the line or the entry"
    print_success(f"{name}: read, undocumented on purpose — {reason}")


def test_the_uncommented_lines_of_env_example_are_unchanged():
    """(5) The file becomes the .env of every install: an uncommented line changes the behaviour of all of them."""
    lines = _uncommented_lines(ENV_EXAMPLE.read_text(encoding="utf-8"))
    assert lines == list(UNCOMMENTED_LINES), (
        f"the uncommented lines of {ENV_EXAMPLE.name} changed. The file is copied into the image as /app/.env and by users as their .env, "
        "so an uncommented line changes the behaviour of every install: add a new option commented, with its default.\n"
        f"expected {list(UNCOMMENTED_LINES)}\nfound    {lines}"
    )
    print_success(f"{len(lines)} uncommented lines, unchanged")


def test_no_variable_has_two_lines_in_env_example():
    """(6) Two lines for one variable: the reader cannot tell which one is meant, and a dotenv parser takes the last."""
    numbers: dict[str, list[int]] = defaultdict(list)
    for line in _env_example_lines():
        numbers[line.name].append(line.number)
    duplicates = {name: lines for name, lines in numbers.items() if len(lines) > 1}
    assert not duplicates, f"variables with more than one line in {ENV_EXAMPLE.name}: {duplicates}"
    print_success(f"{len(numbers)} variables, one line each")
