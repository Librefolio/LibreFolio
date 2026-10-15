"""
Guard of the configuration package (workstream H, platform, checkpoint CP2a).

Package under guard: ``backend/app/config/`` — the base (constants, data directories, test mode, ``Settings``) in
``__init__.py``, and one section module per owner (``platform.py``, ``accounts.py``, ...) holding that owner's variables.

The project rule, in one line: every environment variable of the application is read inside ``backend/app/config/``; a
module elsewhere calls an accessor of the package instead of reading ``os.environ``. Four checks:

(a) The detector. A source READS the environment wherever it evaluates ``os.environ`` (or ``os.environb``) for anything
    but an item assignment or deletion — a subscript, ``.get``, ``.copy``, ``.items``, ``.keys``, ``.values``, ``in``,
    ``dict(...)``, iteration, unpacking, passing the mapping on, aliasing it; wherever it calls or references
    ``os.getenv`` (or ``os.getenvb``); and wherever it imports one of them from ``os`` (``from os import environ``,
    ``from os import getenv``, ``from os import *``), every use of the imported name counting as well. ``os`` is any
    name an import binds to the module: ``import os``, ``import os as alias``, ``import os.path``. The only WRITES are
    ``os.environ["X"] = "1"`` and ``del os.environ["X"]``: they read nothing and the rule allows them anywhere
    (``services/risk/quant/spawn_worker.py`` pins the native thread pools that way). An augmented assignment,
    ``setdefault`` or ``pop`` reads the item before writing it, so it counts as a read.
(b) The guard. No module under ``backend/app/`` outside ``config/`` reads the environment, except the files declared in
    ``ENVIRONMENT_READ_EXCEPTIONS``: keyed by basename, so an entry survives its module moving between packages, with
    the reason as value. The exceptions are a ratchet: an entry whose file no longer reads, or no longer exists, fails
    until it is removed.
(c) The accessors that replaced the reads keep the exact semantics of the call sites they replaced, quirks included:
    any non-empty ``LIBREFOLIO_NO_SCHEDULER`` disables the scheduler, ``0`` and ``false`` too; an empty ``JWT_SECRET``
    is no secret, a whitespace-only one is returned as is.
(d) ``PROJECT_ROOT``, now computed from one directory deeper, is still the repository root.

What the detector does not see: a read made on the module's behalf (``os.path.expanduser``, a library honouring
``HTTPS_PROXY``) and ``os`` reached dynamically (``importlib``, ``sys.modules``). The rule is about the variables the
application reads itself, and those are written ``os.environ`` and ``os.getenv``.

Pure: the sources are parsed with ``ast``, never imported, and the accessors run against variables set through
``monkeypatch`` — no database, no server, no network, no file written. The guard asserts an absence, so the detector
first proves it sees a presence: it flags every read shape of a synthetic source and nothing allowed, and the scan must
reach known modules, find the writes of ``spawn_worker.py`` without calling them reads, and find the reads of the config
package itself (an empty parametrization would be skipped, never red).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import NamedTuple

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.config.accounts import donation_popup_disabled
from backend.app.config.platform import configured_jwt_secret, owning_test_lane_id, scheduler_disabled
from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "backend" / "app"
CONFIG_ROOT = APP_ROOT / "config"

# (a) The members of ``os`` that expose the environment: the mappings (str and bytes) and their getters.
ENVIRONMENT_MAPPINGS = frozenset({"environ", "environb"})
ENVIRONMENT_GETTERS = frozenset({"getenv", "getenvb"})
ENVIRONMENT_MEMBERS = ENVIRONMENT_MAPPINGS | ENVIRONMENT_GETTERS

# (b) Files still allowed to read the environment, by basename (robust to the module moving between packages), with the
# reason. Each entry is a debt: the ratchet fails as soon as its file stops reading, so the entry leaves with the move
# that pays it.
ENVIRONMENT_READ_EXCEPTIONS: dict[str, str] = {
    "web_link_finder.py": "LIBREFOLIO_WEB_LINK_FINDER_*: workstream H moves these reads into backend/app/config/ after the module moves to services/assets/ (plan 01_platform, CP3)",
}

# Presence barrier: modules the scan must reach, relative to backend/app/. The writer sets environment variables for
# its spawned children and reads none.
KNOWN_MODULES = ("main.py", "api/v1/system.py", "services/risk/quant/spawn_worker.py")
ENVIRONMENT_WRITER = "services/risk/quant/spawn_worker.py"

# One parametrized case per file, so a failure names the file.
SCANNED_MODULES = sorted(path.relative_to(APP_ROOT).as_posix() for path in APP_ROOT.rglob("*.py") if CONFIG_ROOT not in path.parents)
CONFIG_MODULES = sorted(path.relative_to(APP_ROOT).as_posix() for path in CONFIG_ROOT.rglob("*.py"))


# =============================================================================
# Detector
# =============================================================================


class EnvironmentAccesses(NamedTuple):
    """Where a source touches the process environment: sorted ``(line, source line)`` pairs."""

    reads: list[tuple[int, str]]
    writes: list[tuple[int, str]]


def _names_bound_to_os(tree: ast.Module) -> set[str]:
    """Every name an ``import`` binds to the ``os`` module: ``import os``, ``import os as alias``, ``import os.path`` (it binds ``os``)."""
    return {alias.asname or "os" for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names if alias.name == "os" or (alias.name.startswith("os.") and alias.asname is None)}


def _environment_imports(tree: ast.Module) -> list[ast.ImportFrom]:
    """The ``from os import ...`` statements that bind an environment member, a star import included: each one is a read."""
    return [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "os" and any(alias.name == "*" or alias.name in ENVIRONMENT_MEMBERS for alias in node.names)]


def _names_bound_to_environment(tree: ast.Module) -> dict[str, str]:
    """Every name a ``from os import`` binds to an environment member, mapped to the member: ``from os import environ as env`` → ``{"env": "environ"}``."""
    names: dict[str, str] = {}
    for node in _environment_imports(tree):
        for alias in node.names:
            if alias.name == "*":
                names.update({member: member for member in ENVIRONMENT_MEMBERS})
            elif alias.name in ENVIRONMENT_MEMBERS:
                names[alias.asname or alias.name] = alias.name
    return names


def _environment_member(node: ast.AST, modules: set[str], names: dict[str, str]) -> str | None:
    """The environment member of ``os`` that ``node`` evaluates, if any: ``os.environ`` → ``"environ"``; ``getenv`` bound by ``from os import getenv`` → ``"getenv"``."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in modules and node.attr in ENVIRONMENT_MEMBERS:
        return node.attr
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        return names.get(node.id)
    return None


def _is_item_write(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    """``node`` is the mapping of an item assignment or deletion — ``os.environ["X"] = "1"``, ``del os.environ["X"]`` — the two uses that read nothing.

    An augmented assignment (``os.environ["X"] += ":more"``) stores into the item too, but reads it first.
    """
    item = parents.get(node)
    if not isinstance(item, ast.Subscript) or item.value is not node:
        return False
    return isinstance(item.ctx, ast.Del) or (isinstance(item.ctx, ast.Store) and not isinstance(parents.get(item), ast.AugAssign))


def _environment_accesses(source: str) -> EnvironmentAccesses:
    """Every read and write of the process environment in ``source``, as defined in (a) of the module docstring.

    ``ast.walk`` visits every node, so a function-level import or a read inside a nested function counts like a
    top-level one. ``source`` comes from ``read_text``, whose universal newlines leave only ``\\n``: its lines are the
    lines the parser numbers.
    """
    tree = ast.parse(source)
    lines = source.split("\n")
    modules = _names_bound_to_os(tree)
    names = _names_bound_to_environment(tree)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    reads = [(node.lineno, lines[node.lineno - 1].strip()) for node in _environment_imports(tree)]
    writes: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        member = _environment_member(node, modules, names)
        if member is None:
            continue
        access = (node.lineno, lines[node.lineno - 1].strip())
        if member in ENVIRONMENT_MAPPINGS and _is_item_write(node, parents):
            writes.append(access)
        else:
            reads.append(access)
    return EnvironmentAccesses(sorted(reads), sorted(writes))


def _accesses_of(module: str) -> EnvironmentAccesses:
    """The environment accesses of ``backend/app/<module>``."""
    return _environment_accesses((APP_ROOT / module).read_text(encoding="utf-8"))


# =============================================================================
# The detector sees what it looks for
# =============================================================================

# Every shape (a) must flag as a read: (source, lines of its reads). None of them may count as a write.
_READ_SHAPES = (
    ('import os\nvalue = os.environ["X"]\n', [2]),
    ('import os\nvalue = os.environ.get("X")\n', [2]),
    ('import os\nvalue = os.environ.get("X", "fallback")\n', [2]),
    ('import os\nvalue = os.getenv("X")\n', [2]),
    ("import os\nsnapshot = os.environ.copy()\n", [2]),
    ("import os\npairs = os.environ.items()\n", [2]),
    ("import os\nnames = os.environ.keys()\n", [2]),
    ("import os\nvalues = os.environ.values()\n", [2]),
    ('import os\npresent = "X" in os.environ\n', [2]),
    ('import os\nabsent = "X" not in os.environ\n', [2]),
    ("import os\nsnapshot = dict(os.environ)\n", [2]),
    ("import os\nfor name in os.environ:\n    print(name)\n", [2]),
    ("import os\nnames = [name for name in os.environ]\n", [2]),
    ('import os\nmerged = {**os.environ, "X": "1"}\n', [2]),
    ("import os\nenvironment = os.environ\n", [2]),
    ('import os\nimport subprocess\n\nsubprocess.run(["true"], env=os.environ, check=False)\n', [4]),
    ("import os\nread = os.getenv\n", [2]),
    ('import os\nlookup = {}\nlookup[os.environ["X"]] = 1\n', [3]),
    ('import os\nos.environ["X"] += ":more"\n', [2]),
    ('import os\nvalue = os.environ.setdefault("X", "1")\n', [2]),
    ('import os\nvalue = os.environ.pop("X", None)\n', [2]),
    ('import os\nraw = os.environb[b"X"]\n', [2]),
    ('import os\nraw = os.getenvb(b"X")\n', [2]),
    ('import os.path\nvalue = os.environ.get("X")\n', [2]),
    ('import os as operating_system\nvalue = operating_system.environ["X"]\n', [2]),
    ('import os as operating_system\nvalue = operating_system.getenv("X")\n', [2]),
    ("from os import environ\n", [1]),
    ('from os import environ\nvalue = environ.get("X")\n', [1, 2]),
    ('from os import environ as env\nvalue = env["X"]\n', [1, 2]),
    ('from os import getenv\nvalue = getenv("X")\n', [1, 2]),
    ('from os import getenv as read\nvalue = read("X")\n', [1, 2]),
    ('from os import *\nvalue = getenv("X")\n', [1, 2]),
    ('def load():\n    import os\n\n    return os.environ.get("X")\n', [4]),
    ('import os\n\n\ndef load():\n    return os.environ["A"] or os.getenv("B")\n', [5, 5]),
)

# What (a) lets through: (source, lines of the writes it must see in it). None of them may count as a read.
_ALLOWED_SHAPES = (
    ('import os\nos.environ["X"] = "1"\n', [2]),
    ('import os\ndel os.environ["X"]\n', [2]),
    ('import os\nos.environ["A"], os.environ["B"] = "1", "2"\n', [2, 2]),
    ('import os as operating_system\noperating_system.environ["X"] = "1"\n', [2]),
    ('import os\nos.environb[b"X"] = b"1"\n', [2]),
    ('import os\npath = os.path.join("a")\n', []),
    ("import os\n", []),
    ("import os\npid = os.getpid()\n", []),
    ("from os import getpid, path\n", []),
    ('environ = {"X": "1"}\nvalue = environ.get("X")\n', []),  # a name is the environment only when an import from os binds it
    ('def getenv(name):\n    return name\n\n\nvalue = getenv("X")\n', []),
)


def test_the_detector_flags_every_read_shape_and_lets_writes_through():
    print_section("Config package: the environment-read detector")
    for source, lines in _READ_SHAPES:
        accesses = _environment_accesses(source)
        assert ([line for line, _ in accesses.reads], accesses.writes) == (lines, []), source
    for source, lines in _ALLOWED_SHAPES:
        accesses = _environment_accesses(source)
        assert (accesses.reads, [line for line, _ in accesses.writes]) == ([], lines), source
    assert _environment_accesses('import os\n\nsecret = os.environ.get("JWT_SECRET") or None\n') == EnvironmentAccesses(reads=[(3, 'secret = os.environ.get("JWT_SECRET") or None')], writes=[])
    print_success(f"{len(_READ_SHAPES)} read shapes flagged, {len(_ALLOWED_SHAPES)} allowed ones left alone, writes seen as writes")


def test_the_scan_reaches_the_application_and_tells_writes_from_reads():
    print_section("Config package: the scan reaches the application")
    assert (CONFIG_ROOT / "__init__.py").is_file(), f"{CONFIG_ROOT} is not the config package: the repository root derived from this file is wrong"
    missing = sorted(set(KNOWN_MODULES) - set(SCANNED_MODULES))
    assert not missing, f"the scan of {APP_ROOT} outside config/ missed known modules: {missing}"

    writer = _accesses_of(ENVIRONMENT_WRITER)
    assert writer.writes, f"{ENVIRONMENT_WRITER} pins the native thread pools by writing os.environ, yet the detector saw no write there"
    assert writer.reads == [], f"{ENVIRONMENT_WRITER} only writes the environment, yet the detector saw reads there: {writer.reads}"

    config_reads = [f"{module}:{line}" for module in CONFIG_MODULES for line, _ in _accesses_of(module).reads]
    assert config_reads, f"the detector found no read in {CONFIG_ROOT}, the one place the environment is read: it cannot see a real read"
    print_success(f"{len(SCANNED_MODULES)} modules scanned outside config/; {len(writer.writes)} writes and no read in {ENVIRONMENT_WRITER}; {len(config_reads)} reads inside config/")


# =============================================================================
# The rule
# =============================================================================


@pytest.mark.parametrize("module", SCANNED_MODULES)
def test_a_module_outside_the_config_package_reads_no_environment_variable(module):
    """(b) A module outside backend/app/config/ calls an accessor of the package; it never reads the environment itself."""
    reads = _accesses_of(module).reads
    reason = ENVIRONMENT_READ_EXCEPTIONS.get(Path(module).name)
    if reason is not None:
        print_success(f"backend/app/{module}: {len(reads)} read(s) excused by a declared exception — {reason}")
        return
    offenders = [f"backend/app/{module}:{line} {text}" for line, text in reads]
    assert not offenders, "every environment variable of the application is read inside backend/app/config/: add an accessor to the config section of the variable's owner and call it here:\n" + "\n".join(offenders)
    print_success(f"backend/app/{module}: no environment read")


@pytest.mark.parametrize("basename", sorted(ENVIRONMENT_READ_EXCEPTIONS))
def test_a_declared_exception_still_has_reads_to_excuse(basename):
    """(b) An exception is a debt: it goes as soon as its file stops reading the environment."""
    modules = [module for module in SCANNED_MODULES if Path(module).name == basename]
    assert modules, f"no {basename} is left under backend/app/ outside config/: remove its entry from ENVIRONMENT_READ_EXCEPTIONS"
    reads = [f"backend/app/{module}:{line}" for module in modules for line, _ in _accesses_of(module).reads]
    assert reads, f"{', '.join(modules)} no longer read the environment: remove the {basename} entry from ENVIRONMENT_READ_EXCEPTIONS so the rule covers it again"
    print_success(f"{basename}: {len(reads)} read(s) still excused in {', '.join(modules)}")


# =============================================================================
# The section accessors keep the semantics of the call sites they replaced
# =============================================================================


def _set_variable(monkeypatch: pytest.MonkeyPatch, name: str, value: str | None) -> None:
    """``None`` unsets ``name``; any string, the empty one included, sets it."""
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, False, id="unset"),
        pytest.param("", False, id="empty"),
        pytest.param("1", True, id="1"),
        pytest.param("true", True, id="true"),
        pytest.param("0", True, id="0-disables-too"),
        pytest.param("false", True, id="false-disables-too"),
        pytest.param(" ", True, id="blank-disables-too"),
    ],
)
def test_scheduler_disabled_by_any_non_empty_value(monkeypatch, value, expected):
    """(c) ``LIBREFOLIO_NO_SCHEDULER``: any non-empty value keeps the scheduler off, ``0`` and ``false`` included (kept on purpose)."""
    _set_variable(monkeypatch, "LIBREFOLIO_NO_SCHEDULER", value)
    assert scheduler_disabled() is expected
    print_success(f"LIBREFOLIO_NO_SCHEDULER={value!r}: scheduler_disabled() is {expected}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="unset"),
        pytest.param("", None, id="empty-is-none"),
        pytest.param("  ", "  ", id="whitespace-returned-as-is"),
        pytest.param(" padded ", " padded ", id="never-stripped"),
        pytest.param("s3cret-signing-key", "s3cret-signing-key", id="set"),
    ],
)
def test_configured_jwt_secret_treats_only_the_empty_value_as_none(monkeypatch, value, expected):
    """(c) ``JWT_SECRET``: unset or empty is no secret; anything else, whitespace included, is the secret as written."""
    _set_variable(monkeypatch, "JWT_SECRET", value)
    assert configured_jwt_secret() == expected
    print_success(f"JWT_SECRET={value!r}: configured_jwt_secret() == {expected!r}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="unset"),
        pytest.param("", "", id="empty-returned-as-is"),
        pytest.param("lane-0123456789abcdef", "lane-0123456789abcdef", id="set"),
    ],
)
def test_owning_test_lane_id_is_the_variable_as_set(monkeypatch, value, expected):
    """(c) ``LIBREFOLIO_TEST_LANE_ID``: the value as the environment holds it, ``None`` when unset."""
    _set_variable(monkeypatch, "LIBREFOLIO_TEST_LANE_ID", value)
    assert owning_test_lane_id() == expected
    print_success(f"LIBREFOLIO_TEST_LANE_ID={value!r}: owning_test_lane_id() == {expected!r}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, False, id="unset"),
        pytest.param("", False, id="empty"),
        pytest.param("1", True, id="1"),
        pytest.param("true", True, id="true"),
        pytest.param("yes", True, id="yes"),
        pytest.param("TRUE", True, id="TRUE-any-case"),
        pytest.param("Yes", True, id="Yes-any-case"),
        pytest.param("0", False, id="0"),
        pytest.param("false", False, id="false"),
        pytest.param("on", False, id="on-is-not-accepted"),
        pytest.param(" 1", False, id="never-stripped"),
    ],
)
def test_donation_popup_disabled_by_1_true_or_yes_in_any_case(monkeypatch, value, expected):
    """(c) ``LIBREFOLIO_DISABLE_DONATION_POPUP``: ``1``, ``true`` or ``yes`` in any case turns the popup off; nothing else does."""
    _set_variable(monkeypatch, "LIBREFOLIO_DISABLE_DONATION_POPUP", value)
    assert donation_popup_disabled() is expected
    print_success(f"LIBREFOLIO_DISABLE_DONATION_POPUP={value!r}: donation_popup_disabled() is {expected}")


# =============================================================================
# The base moved one directory deeper
# =============================================================================


def test_project_root_is_the_repository_root():
    """(d) config.py became config/__init__.py, so PROJECT_ROOT climbs one more directory to stay the repository root."""
    print_section("Config package: PROJECT_ROOT")
    assert (PROJECT_ROOT / "backend" / "app" / "config" / "__init__.py").is_file(), f"{PROJECT_ROOT} holds no backend/app/config/__init__.py"
    assert (PROJECT_ROOT / "dev.py").is_file(), f"{PROJECT_ROOT} holds no dev.py: it is not the repository root"
    assert PROJECT_ROOT.resolve() == REPO_ROOT, f"backend.app.config was imported from {PROJECT_ROOT}, not from the checkout of this test ({REPO_ROOT})"
    print_success(f"PROJECT_ROOT = {PROJECT_ROOT}")
