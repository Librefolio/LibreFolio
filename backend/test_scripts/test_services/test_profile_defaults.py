"""
The profile defaults of the settings (workstream H, platform, checkpoint CP7b-2; developer decisions D5 and F27), and of
the variables read outside them (H-17), whose type must be their reader's (H-27), and which every profile but
``selfhosted`` must list (H-37).

Under test: ``PROFILE_DEFAULTS`` and the validator of ``Settings`` that applies it, both in ``backend/app/config/__init__.py``,
and the two fields D5 adds there; next to them, ``ENVIRONMENT_PROFILE_DEFAULTS`` and ``profile_default()`` (H-17), and
``ProfileDefaultError``, which ``profile_default()`` raises for an entry of the wrong type (H-27) and, under any profile
but ``selfhosted``, for a variable the profile does not list (H-37). The contract:

(a) ``PROFILE_DEFAULTS`` maps each profile ``LIBREFOLIO_PROFILE`` accepts, and no other, to the values that profile gives
    the fields it lists. ``selfhosted`` lists none: an install run by its owner keeps every code default. ``managed``
    lists four: ``RISK_SIMULATION_IDLE_TIMEOUT_SECONDS`` and ``RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS`` at 60.0 (F27),
    ``LIBREFOLIO_FRAME_PROTECTION`` and ``LIBREFOLIO_CSP_REPORT_ONLY`` on (D5). Those two are new fields of ``Settings``:
    booleans, ``False`` in the code.
(b) The active profile's value goes to every field it lists that was not set, neither in the environment nor in ``.env``
    (``model_fields_set``). A set value always wins, whatever the profile: also one equal to the code default (``600``,
    ``false``), and ``0`` (idle workers never stop). The other listed fields still take the profile's value.
(c) Self-hosted, the profile unset or ``selfhosted``: every field any profile lists keeps its code default. Parametrised
    over the union of the profiles' fields, read when this file is collected, so a field added later to any profile is
    covered without touching this file.
(d) Guards on the table. Every key is a field of ``Settings``. Every value is valid for its field in strict mode: it is
    written in the field's own type, as a code default is (``60.0``, ``True``), never as the text an environment variable
    carries (``"60"``) nor as ``1`` for a flag. Every listed field has a code default: no required field.
(e) The profile is read as today, spaces and case aside: ``MANAGED`` and `` Managed `` give the managed defaults.
(f) ``ENVIRONMENT_PROFILE_DEFAULTS`` does for the variables a section module of ``backend/app/config/`` reads from the
    environment outside ``Settings`` what ``PROFILE_DEFAULTS`` does for the fields: for each profile, the value such a
    variable takes while it is unset. The section module keeps its own parsing (what blank or invalid means) and calls
    ``profile_default(name, fallback)`` only while the variable is unset. The table has one entry per profile
    ``LIBREFOLIO_PROFILE`` accepts; ``selfhosted`` lists none; ``managed`` lists ``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`` at
    ``500`` (decision 43), an ``int``: never ``"500"``, ``500.0`` nor ``True``. No key is a field of ``Settings`` (those
    belong in ``PROFILE_DEFAULTS``) and no name is in both tables. Every key is written as a string constant in the code
    of a section module, any module of ``backend/app/config/`` but ``__init__.py`` (a comment or a docstring does not
    count), and has a variable line in ``.env.example`` (``NAME=`` or ``# NAME=``, as ``test_env_example.py`` reads them).
    ``profile_default(name, fallback)`` gives ``fallback`` itself, always, when self-hosted (the profile unset or
    ``selfhosted``). Under any other profile it gives the profile's entry for ``name``, as the table holds it, when that
    entry is of the very type of ``fallback`` (any other entry: see (g)); a name the profile does not list raises
    ``ProfileDefaultError`` (H-37; E, R13-SEC7), whose message names the variable, the profile and
    ``ENVIRONMENT_PROFILE_DEFAULTS``: the fallback never comes back, whatever it is (``object()``, ``0``, ``0.0``,
    ``""``, ``False``, ``None``). The reader fails closed, since a managed upload limit missing from the table would
    otherwise come back from ``backup_max_upload_mb()`` as its own ``0``, no limit at all; self-hosted, that reader still
    gets its ``0``, with or without the managed entry. The profile is ``get_settings().LIBREFOLIO_PROFILE``, read at
    each call: ``MANAGED`` and `` Managed `` are managed, for a name the profile lists as for one it does not, and a
    profile changed between two calls is followed.
(g) The type of an entry is checked when a reader asks for it (H-27; E, R13-SEC3). ``profile_default(name, fallback)``
    gives a listed entry only when it is of the very type of ``fallback``, the reader's own default: ``type(entry) is
    type(fallback)``, so ``True`` is no ``int``, ``1`` no ``bool``, ``60`` no ``float``, ``"500"`` no ``int``, and
    ``None`` fits no reader whose default is a number, a flag or a text. Any other entry raises ``ProfileDefaultError``,
    a ``TypeError`` whose message names the variable, the profile, both types and ``ENVIRONMENT_PROFILE_DEFAULTS``: the
    reader stops rather than read a value of the wrong type. Unchecked, a ``None`` for the upload limit in the managed
    table comes back from ``backup_max_upload_mb()`` (``config/backup.py``, workstream B) as the limit, and
    ``_upload_limit()`` of ``api/v1/backup/restore.py`` reads it as no limit at all: a fail-open. Every name, when
    self-hosted, still gives the fallback itself, with no check: whatever the managed table holds, a self-hosted install
    is unchanged. A name another profile does not list has no entry to check, and raises all the same (H-37, see (f)).
    An entry equal to its reader's own default, of its very type (``0`` for ``0``, ``False`` for ``False``), is given as
    any other: a profile other than ``selfhosted`` lists such an entry to keep a variable at the self-hosted behaviour,
    now that it must list every variable a reader asks for (H-37).
(h) The same rules on the source, before anything runs (H-27, H-37). Every call ``profile_default(<name>, <fallback>)``
    of a section module, by that name or as an attribute, states its variable as a string literal or as a name the
    module binds once, at its top level, to a string literal, and its fallback as a literal (``0``, ``-1``, ``60.0``,
    ``""``, ``False``), so that ``ast`` reads both; every variable a profile lists is read by such a call; every profile
    that lists a call's variable gives it a value of the very type of the call's fallback; and every call's variable is
    listed by every profile but ``selfhosted`` (H-37), which lists none (f): no reader meets, when it runs, the
    ``ProfileDefaultError`` of a missing entry. The two guards, of the type and of the listing, each have a self-test that
    checks it reports what it is for: one writes ``None`` for the upload limit into the managed table, the other removes
    the managed entry of the upload limit.

``Settings`` is built with ``_env_file=None`` after the profile and every listed field are removed from the environment
with ``monkeypatch``, so neither the shell nor the instance's ``.env`` reaches a case. The one case about ``.env`` writes
its own file under ``tmp_path`` and turns test mode off for the call: in test mode ``Settings`` reads no ``.env`` at all
(``settings_customise_sources``). ``profile_default()`` reads ``get_settings()``, which takes no ``_env_file``: the cases
that call it set ``LIBREFOLIO_TEST_MODE=1`` (no ``.env``) and ``LIBREFOLIO_TEST_DATA_DIR`` under ``tmp_path`` (never the
lane's data), remove the profile and every variable of the environment table, set the profile they mean, all with
``monkeypatch``, and check that ``get_settings()`` reads it so. Where no type is checked (self-hosted) their fallback is
a fresh ``object()``, for which only the very object can pass; for a name the managed profile does not list it is such
an object, and each falsy default a reader may have (``0``, ``0.0``, ``""``, ``False``, ``None``), none of which may
come back (H-37); for a name the managed profile lists it is a value of the entry's own type that is not the entry
(``fallback_like()``: the empty value, ``0``, ``0.0``, ``False``, ``""``, or ``1``, ``1.0``, ``True``, ``"x"`` for an
entry that is that empty value, legitimate since H-37; a pure case checks the helper itself), since (g) refuses any
other. The cases of (g) and (h) write into the managed table, a test-only variable or ``None`` for the upload limit,
with ``monkeypatch.setitem``; the cases of H-37 remove the managed entry of the upload limit with
``monkeypatch.delitem``; both put the real table back after each case. ``PROFILE_DEFAULTS``,
``ENVIRONMENT_PROFILE_DEFAULTS``, ``profile_default`` and ``ProfileDefaultError`` are read with ``getattr`` when a test
runs, so this file collects before ``ProfileDefaultError`` exists and each test fails on its own; the cases of (g) and
of H-37 that expect it call ``profile_default()`` or its reader first, so that when nothing is raised they report the
value that came back. ``backend.app.config.backup``, the reader of workstream B, is imported and only called. The
sources of ``backend/app/config/`` and ``.env.example`` are only read, as text or as an ``ast`` tree. No DB, no server,
no network.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import get_args

import pytest
from pydantic import TypeAdapter, ValidationError
from pydantic.fields import FieldInfo

from backend.app import config
from backend.app.config import backup as backup_config
from backend.test_scripts.test_services.test_env_example import ENV_EXAMPLE, _variable_lines
from backend.test_scripts.test_utils import print_section, print_success

PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
#: What LIBREFOLIO_PROFILE accepts today, and so the keys PROFILE_DEFAULTS and ENVIRONMENT_PROFILE_DEFAULTS must have.
PROFILES = ("selfhosted", "managed")

#: D5 and F27: the value the managed profile gives each field it lists, when nobody set the field.
MANAGED_DEFAULTS: dict[str, object] = {
    "RISK_SIMULATION_IDLE_TIMEOUT_SECONDS": 60.0,
    "RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS": 60.0,
    "LIBREFOLIO_FRAME_PROTECTION": True,
    "LIBREFOLIO_CSP_REPORT_ONLY": True,
}
#: The two switches D5 adds to Settings, off in the code.
NEW_SWITCHES = ("LIBREFOLIO_FRAME_PROTECTION", "LIBREFOLIO_CSP_REPORT_ONLY")
#: (f), (g): the largest archive a restore accepts, read by backup_max_upload_mb() (workstream B, config/backup.py).
UPLOAD_LIMIT_VARIABLE = "LIBREFOLIO_BACKUP_MAX_UPLOAD_MB"
#: H-17 (decision 43): the value the managed profile gives each variable a section module of backend/app/config/ reads
#: from the environment outside Settings, while that variable is unset.
ENVIRONMENT_MANAGED_DEFAULTS: dict[str, object] = {UPLOAD_LIMIT_VARIABLE: 500}
#: (f): a variable no profile lists: profile_default() gives its fallback back when self-hosted, and raises
#: ProfileDefaultError under managed (H-37).
UNLISTED_VARIABLE = "LIBREFOLIO_NO_PROFILE_LISTS_THIS"
#: (f): one variable of the decided table, for the cases about how the profile is read.
SAMPLE_VARIABLE = next(iter(ENVIRONMENT_MANAGED_DEFAULTS))
#: (g) H-27: a variable no section module reads and no profile lists, which the cases of the type check write into the
#: managed table for themselves alone (list_the_test_variable_in_managed).
H27_VARIABLE = "LIBREFOLIO_H27_TEST_ONLY_VARIABLE"

REPO_ROOT = Path(__file__).resolve().parents[3]
#: (f): the section modules of the configuration are the modules of this folder but __init__.py, where both tables live.
CONFIG_ROOT = REPO_ROOT / "backend" / "app" / "config"


def _collected_table(name: str = "PROFILE_DEFAULTS") -> dict[str, dict[str, object]]:
    """The table ``name`` of ``backend.app.config`` as it is when this file is collected; empty before it exists."""
    table = getattr(config, name, None)
    if not isinstance(table, Mapping):
        return {}
    return {profile: dict(values) for profile, values in table.items() if isinstance(values, Mapping)}


_COLLECTED = _collected_table()
#: (c) and (d): every field any profile lists, and the contract's. The contract's are always there: before the table
#: exists each case fails on its own, and the list is never empty (an empty parametrisation is a skip, not a failure).
LISTED_FIELDS = sorted({name for values in _COLLECTED.values() for name in values} | set(MANAGED_DEFAULTS))
#: (b): every field the managed profile lists, and the contract's.
MANAGED_FIELDS = sorted(set(_COLLECTED.get("managed", {})) | set(MANAGED_DEFAULTS))
#: (d): every entry (profile, field) of the table, and the managed entries of the contract.
TABLE_ENTRIES = sorted({(profile, name) for profile, values in _COLLECTED.items() for name in values} | {("managed", name) for name in MANAGED_DEFAULTS})

_COLLECTED_ENVIRONMENT = _collected_table("ENVIRONMENT_PROFILE_DEFAULTS")
#: (f): every variable any profile of the environment table lists, and the decided ones: never empty, so that before the
#: table exists each case fails on its own.
ENVIRONMENT_VARIABLES = sorted({name for values in _COLLECTED_ENVIRONMENT.values() for name in values} | set(ENVIRONMENT_MANAGED_DEFAULTS))
#: (f): every variable the managed profile of the environment table lists, and the decided ones.
ENVIRONMENT_MANAGED_VARIABLES = sorted(set(_COLLECTED_ENVIRONMENT.get("managed", {})) | set(ENVIRONMENT_MANAGED_DEFAULTS))


# =============================================================================
# HELPERS
# =============================================================================


def profile_defaults() -> Mapping[str, Mapping[str, object]]:
    """``PROFILE_DEFAULTS``: before it exists, the test that asks for it fails here, and only that test."""
    table = getattr(config, "PROFILE_DEFAULTS", None)
    assert isinstance(table, Mapping), f"backend.app.config has no PROFILE_DEFAULTS mapping (found {table!r}): the profile defaults of D5 are not there yet"
    return table


def profile_values(profile: str) -> Mapping[str, object]:
    """The values ``profile`` gives the fields it lists."""
    table = profile_defaults()
    values = table.get(profile)
    assert isinstance(values, Mapping), f"PROFILE_DEFAULTS has no mapping for the profile {profile!r} (found {values!r}); its keys: {sorted(table)}"
    return values


def listed_by_any_profile() -> set[str]:
    return {name for values in profile_defaults().values() for name in values}


def field(name: str) -> FieldInfo:
    """The field ``name`` of ``Settings``."""
    fields = config.Settings.model_fields
    assert name in fields, f"Settings has no field {name}"
    return fields[name]


def code_default(info: FieldInfo) -> object:
    """What the code gives the field: its default (``Settings.model_fields[name].default``), or what its factory makes."""
    return info.get_default(call_default_factory=True)


def same(actual: object, expected: object) -> bool:
    """Equal, and a flag only where a flag is expected: ``1 == True`` and ``0.0 == False`` would hide a wrong type."""
    return isinstance(actual, bool) == isinstance(expected, bool) and actual == expected


def unset_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neither the shell nor the lane reaches ``Settings``: the profile and every field a profile lists are unset."""
    for name in {PROFILE_VARIABLE, *LISTED_FIELDS}:
        monkeypatch.delenv(name, raising=False)


def settings_from_the_environment() -> config.Settings:
    """``Settings`` from the environment alone: the instance's ``.env`` is never read."""
    return config.Settings(_env_file=None)


def value_of(settings: config.Settings, name: str) -> object:
    assert name in type(settings).model_fields, f"Settings has no field {name}"
    return getattr(settings, name)


def wrong_values(settings: config.Settings, expected: Mapping[str, object]) -> dict[str, tuple[object, object]]:
    """``{field: (value, expected)}`` for every field of ``expected`` whose value is not the expected one."""
    return {name: (value_of(settings, name), value) for name, value in expected.items() if not same(value_of(settings, name), value)}


def environment_defaults() -> Mapping[str, Mapping[str, object]]:
    """``ENVIRONMENT_PROFILE_DEFAULTS`` (H-17): before it exists, the test that asks for it fails here, and only that test."""
    table = getattr(config, "ENVIRONMENT_PROFILE_DEFAULTS", None)
    assert table is not None, "ENVIRONMENT_PROFILE_DEFAULTS is missing from backend/app/config/__init__.py (H-17)"
    assert isinstance(table, Mapping), f"ENVIRONMENT_PROFILE_DEFAULTS is a {type(table).__name__}, not a mapping of profiles: {table!r}"
    return table


def environment_values(profile: str) -> Mapping[str, object]:
    """The values ``profile`` gives the variables it lists in ``ENVIRONMENT_PROFILE_DEFAULTS``."""
    table = environment_defaults()
    values = table.get(profile)
    assert isinstance(values, Mapping), f"ENVIRONMENT_PROFILE_DEFAULTS has no mapping for the profile {profile!r} (found {values!r}); its keys: {sorted(table)}"
    return values


def listed_in_the_environment_table() -> set[str]:
    return {name for values in environment_defaults().values() for name in values}


def profile_default_function() -> Callable[[str, object], object]:
    """``profile_default`` (H-17): before it exists, the test that calls it fails here, and only that test."""
    function = getattr(config, "profile_default", None)
    assert function is not None, "profile_default is missing from backend/app/config/__init__.py (H-17)"
    assert callable(function), f"profile_default is a {type(function).__name__}, not a function: {function!r}"
    return function


def profile_default_error() -> type[TypeError]:
    """``ProfileDefaultError`` (H-27), read when the test asks for it: before it exists, that test fails here, and only
    that test."""
    error = getattr(config, "ProfileDefaultError", None)
    if error is None:
        pytest.fail("H-27: backend.app.config has no ProfileDefaultError")
    assert isinstance(error, type) and issubclass(error, TypeError), f"backend.app.config.ProfileDefaultError is {error!r}, not a subclass of TypeError: an entry of the wrong type is a TypeError, and a caller catching TypeError must catch it too"
    return error


def configure_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, written: str | None, profile: str) -> None:
    """Make ``get_settings()`` read ``LIBREFOLIO_PROFILE`` as ``written`` (``None``: unset) from this environment alone, and
    check that it reads the profile ``profile``. Every variable of the environment table, and the one the cases of (g)
    write into it, is unset, as it is whenever a section module asks ``profile_default()``."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")  # get_settings() reads no .env in test mode: only this environment
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))  # get_settings() never looks at the lane's data
    for name in (PROFILE_VARIABLE, *ENVIRONMENT_VARIABLES, UNLISTED_VARIABLE, H27_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    if written is not None:
        monkeypatch.setenv(PROFILE_VARIABLE, written)

    resolved = config.get_settings().LIBREFOLIO_PROFILE

    assert resolved == profile, f"barrier: with {PROFILE_VARIABLE}={written!r}, get_settings() reads the profile {resolved!r}, not {profile!r}"


def exactly(actual: object, expected: object) -> bool:
    """Equal, and of the very same type: ``500``, never ``"500"``, ``500.0`` nor ``True``. Stricter than ``same()``."""
    return type(actual) is type(expected) and actual == expected


def described(result: object, fallback: object) -> str:
    """``result`` for a message: the fallback named as such, any other value with its type."""
    return "the fallback itself" if result is fallback else f"{result!r} ({type(result).__name__})"


#: fallback_like(): for each type a reader's own default may have, a value of that very type that is not its empty value,
#: for an entry that is (H-37 makes such an entry legitimate: a profile other than selfhosted lists every variable a reader
#: asks for, also one it leaves at the self-hosted behaviour).
NON_EMPTY_VALUES: dict[type, object] = {int: 1, float: 1.0, bool: True, str: "x"}


def fallback_like(entry: object) -> object:
    """A reader's own default for a variable a profile lists at ``entry``: of the very type of the entry, as (g) requires,
    and not the entry, so that a case can tell the two apart. The empty value of that type first (``type(entry)()``:
    ``0``, ``0.0``, ``False``, ``""``); for an entry that is that empty value, legitimate since H-37, a non-empty one
    (``NON_EMPTY_VALUES``: ``1``, ``1.0``, ``True``, ``"x"``). An entry of a type with no empty value fails its case
    here, on this barrier, never on the product."""
    try:
        fallback = type(entry)()
    except TypeError:
        pytest.fail(f"barrier: the entry {entry!r} is a {type(entry).__name__}, a type with no empty value to stand for its reader's own default")
    if fallback == entry:
        fallback = NON_EMPTY_VALUES.get(type(entry), fallback)
    assert type(fallback) is type(entry) and fallback != entry, f"barrier: for the entry {entry!r} ({type(entry).__name__}) this helper finds no other value of its very type (found {fallback!r}, a {type(fallback).__name__}), so this case could not tell the entry from the fallback"
    return fallback


def list_the_test_variable_in_managed(monkeypatch: pytest.MonkeyPatch, value: object) -> None:
    """Make ``ENVIRONMENT_PROFILE_DEFAULTS['managed']`` list ``H27_VARIABLE`` at ``value``, for this case alone (g): no
    profile lists that name before, and ``monkeypatch.setitem`` puts the real table back after the case."""
    listing = sorted(profile for profile, values in environment_defaults().items() if H27_VARIABLE in values)
    assert not listing, f"barrier: the profiles {listing} of ENVIRONMENT_PROFILE_DEFAULTS list {H27_VARIABLE}, the name the cases of (g) write for themselves"
    monkeypatch.setitem(environment_values("managed"), H27_VARIABLE, value)


def section_modules() -> list[Path]:
    """The section modules of the configuration: every module of ``backend/app/config/`` but ``__init__.py``."""
    return sorted(path for path in CONFIG_ROOT.glob("*.py") if path.name != "__init__.py")


def _docstring_node(scope: ast.AST) -> ast.Constant | None:
    """The docstring of a module, a class or a function, as its node; ``None`` for any other node, and for one without."""
    if not isinstance(scope, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) or not scope.body:
        return None
    first = scope.body[0]
    return first.value if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str) else None


def string_constants(path: Path) -> set[str]:
    """The strings the code of the module at ``path`` writes: its ``ast.Constant`` nodes, its docstrings aside (a comment is
    not in the tree at all). A variable name a module passes to ``os.environ`` or to ``profile_default()`` is one of them."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings = {id(docstring) for docstring in map(_docstring_node, ast.walk(tree)) if docstring is not None}
    return {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings}


#: (h): the fallback of a call whose second argument the source does not state as a literal.
NOT_A_LITERAL = object()


@dataclass(frozen=True)
class ProfileDefaultCall:
    """A call of ``profile_default`` in a section module (h), with its two arguments as the source states them."""

    where: str  # backend/app/config/<module>.py:<line>
    source: str  # the call, as ast.unparse writes it
    name: str | None  # the variable; None when the source states no string for it (a literal, or a top-level constant)
    fallback: object  # the reader's own default; NOT_A_LITERAL when the source does not state it as a literal

    def problems(self) -> list[str]:
        """Why the type of this call's fallback cannot be compared with the table: nothing when it can."""
        problems = []
        if self.name is None:
            problems.append("its first argument is neither a string literal nor a name the module binds once, at its top level, to a string literal")
        if self.fallback is NOT_A_LITERAL:
            problems.append("its second argument, the reader's own default, is not a literal such as 0, -1, 60.0, '' or False")
        return problems

    @property
    def readable(self) -> bool:
        return not self.problems()


@dataclass(frozen=True)
class Mismatch:
    """A profile that gives the variable of a call a value not of the very type of the call's fallback (h)."""

    call: ProfileDefaultCall
    profile: str
    value: object

    def __str__(self) -> str:
        return f"{self.call.where} {self.call.source} reads a {type(self.call.fallback).__name__}, and ENVIRONMENT_PROFILE_DEFAULTS[{self.profile!r}][{self.call.name!r}] is {self.value!r}, a {type(self.value).__name__}"


def _top_level_bindings(statement: ast.stmt) -> list[tuple[str, ast.expr | None]]:
    """The plain names a top-level statement binds by assignment, each with the value it gives them (``None`` for ``+=``
    and the like, whose result this guard does not compute)."""
    if isinstance(statement, ast.Assign):
        return [(target.id, statement.value) for target in statement.targets if isinstance(target, ast.Name)]
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return [(statement.target.id, statement.value)]
    if isinstance(statement, ast.AugAssign) and isinstance(statement.target, ast.Name):
        return [(statement.target.id, None)]
    return []


def module_string_constants(tree: ast.Module) -> dict[str, str]:
    """The names a module binds once, at its top level, to a string literal (``NAME = "..."``, ``NAME: str = "..."``). A
    name bound twice there is left out: which of its values a call sees would depend on when it runs."""
    bindings: dict[str, list[ast.expr | None]] = {}
    for statement in tree.body:
        for name, value in _top_level_bindings(statement):
            bindings.setdefault(name, []).append(value)
    constants: dict[str, str] = {}
    for name, (value, *rebound) in bindings.items():
        if not rebound and isinstance(value, ast.Constant) and isinstance(value.value, str):
            constants[name] = value.value
    return constants


def _names_profile_default(function: ast.expr) -> bool:
    """``profile_default(...)``, or ``<anything>.profile_default(...)``."""
    if isinstance(function, ast.Attribute):
        return function.attr == "profile_default"
    return isinstance(function, ast.Name) and function.id == "profile_default"


def _argument(call: ast.Call, position: int, keyword: str) -> ast.expr | None:
    """The argument ``call`` passes at ``position``, or else as ``keyword``; ``None`` when it passes neither."""
    if len(call.args) > position:
        return call.args[position]
    return next((item.value for item in call.keywords if item.arg == keyword), None)


def _variable_name(node: ast.expr | None, constants: Mapping[str, str]) -> str | None:
    """The variable the first argument names: a string literal, or a name the module binds once, at its top level, to one."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _literal_fallback(node: ast.expr | None) -> object:
    """The reader's own default, when the second argument is a literal (``0``, ``60.0``, ``""``, ``False``) or a negative
    number (``-1``, which ``ast`` reads as a minus applied to ``1``); otherwise ``NOT_A_LITERAL``."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
        number = node.operand.value
        if isinstance(number, int | float) and not isinstance(number, bool):
            return -number
    return NOT_A_LITERAL


def profile_default_calls() -> list[ProfileDefaultCall]:
    """Every call of ``profile_default`` in the section modules (h), by that name or as an attribute, read from their
    source with ``ast``: nothing is imported nor run."""
    calls: list[ProfileDefaultCall] = []
    for path in section_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        constants = module_string_constants(tree)
        calls += [
            ProfileDefaultCall(
                where=f"{path.relative_to(REPO_ROOT).as_posix()}:{node.lineno}",
                source=ast.unparse(node),
                name=_variable_name(_argument(node, 0, "name"), constants),
                fallback=_literal_fallback(_argument(node, 1, "fallback")),
            )
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _names_profile_default(node.func)
        ]
    return calls


def type_mismatches(calls: Iterable[ProfileDefaultCall]) -> list[Mismatch]:
    """For every call whose arguments the source states, every profile of ``ENVIRONMENT_PROFILE_DEFAULTS``, as the table
    is when this runs, that lists the call's variable at a value not of the very type of the call's fallback (h): the rule
    ``profile_default()`` applies when the reader runs (g). The real case and its self-test both ask this function."""
    table = environment_defaults()
    return [Mismatch(call, profile, values[call.name]) for call in calls if call.readable and call.name is not None for profile, values in table.items() if call.name in values and type(values[call.name]) is not type(call.fallback)]


@dataclass(frozen=True)
class MissingEntry:
    """A profile other than ``selfhosted`` that does not list the variable of a call (h, H-37)."""

    call: ProfileDefaultCall
    profile: str

    def __str__(self) -> str:
        return f"{self.call.where} {self.call.source} reads {self.call.name}, which ENVIRONMENT_PROFILE_DEFAULTS[{self.profile!r}] does not list"


def missing_entries(calls: Iterable[ProfileDefaultCall]) -> list[MissingEntry]:
    """For every call whose arguments the source states, every profile of ``ENVIRONMENT_PROFILE_DEFAULTS`` but
    ``selfhosted``, as the table is when this runs, that does not list the call's variable (h): there
    ``profile_default()`` raises ``ProfileDefaultError`` when the reader runs (H-37). The real case and its self-test
    both ask this function."""
    table = environment_defaults()
    return [MissingEntry(call, profile) for call in calls if call.readable and call.name is not None for profile, values in table.items() if profile != "selfhosted" and call.name not in values]


# =============================================================================
# (a) THE TABLE, AS DECIDED
# =============================================================================


def test_the_table_has_one_entry_per_profile_settings_accepts() -> None:
    print_section("PROFILE_DEFAULTS: one entry per profile")
    accepted = get_args(field(PROFILE_VARIABLE).annotation)
    assert set(accepted) == set(PROFILES), f"barrier: LIBREFOLIO_PROFILE accepts {accepted}, this file knows {PROFILES}"

    table = profile_defaults()

    assert set(table) == set(PROFILES), f"PROFILE_DEFAULTS has the profiles {sorted(table)}: it must have exactly those LIBREFOLIO_PROFILE accepts, {sorted(PROFILES)}, so that a misspelt profile cannot stand in for one"
    print_success(f"✓ {sorted(table)}")


def test_selfhosted_lists_no_field() -> None:
    print_section("PROFILE_DEFAULTS['selfhosted']")

    values = profile_values("selfhosted")

    assert dict(values) == {}, f"PROFILE_DEFAULTS['selfhosted'] lists {dict(values)}: an install run by its owner keeps every code default"
    print_success("✓ empty")


def test_managed_lists_the_values_of_d5_and_f27() -> None:
    print_section("PROFILE_DEFAULTS['managed']")

    values = profile_values("managed")

    assert dict(values) == MANAGED_DEFAULTS, f"PROFILE_DEFAULTS['managed'] is {dict(values)}, decided {MANAGED_DEFAULTS}"
    mistyped = {name: values[name] for name, expected in MANAGED_DEFAULTS.items() if not same(values[name], expected)}
    assert not mistyped, f"equal but not of the decided type (a flag must be a flag): {mistyped}"
    print_success(f"✓ {MANAGED_DEFAULTS}")


@pytest.mark.parametrize("name", NEW_SWITCHES)
def test_the_new_switch_is_a_boolean_off_in_the_code(name: str) -> None:
    print_section(f"Settings.{name}")

    info = field(name)

    assert info.annotation is bool, f"Settings.{name} is a {info.annotation!r}, not a bool"
    assert info.default is False, f"Settings.{name} defaults to {info.default!r} in the code: it is off unless a profile or the environment turns it on"
    print_success("✓ bool, False")


# =============================================================================
# (b) MANAGED: A FIELD NOBODY SET, A FIELD SOMEBODY SET
# =============================================================================


@pytest.mark.parametrize("name", MANAGED_FIELDS)
def test_managed_gives_its_value_to_a_field_nobody_set(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    print_section(f"LIBREFOLIO_PROFILE=managed, {name} unset")
    values = profile_values("managed")
    assert name in values, f"barrier: PROFILE_DEFAULTS['managed'] does not list {name}: {dict(values)}"
    expected, default = values[name], code_default(field(name))
    assert not same(expected, default), f"barrier: the managed value of {name} is its code default, {default!r}: the entry changes nothing, and this case could not tell the profile from no profile"
    unset_everything(monkeypatch)
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")

    settings = settings_from_the_environment()

    assert settings.LIBREFOLIO_PROFILE == "managed", f"barrier: the profile read is {settings.LIBREFOLIO_PROFILE!r}"
    actual = value_of(settings, name)
    assert same(actual, expected), f"LIBREFOLIO_PROFILE=managed and {name} unset: {name} is {actual!r}, not the managed {expected!r} (code default {default!r})"
    print_success(f"✓ {name} = {actual!r}")


#: Set in the environment under managed: (variable, as written, the value the setting must keep). Each differs from the
#: managed value; three equal the code default (600, false); 0 keeps idle workers running, and is falsy.
SET_UNDER_MANAGED: dict[str, tuple[str, str, object]] = {
    "simulation-idle-90": ("RISK_SIMULATION_IDLE_TIMEOUT_SECONDS", "90", 90.0),
    "simulation-idle-600-the-code-default": ("RISK_SIMULATION_IDLE_TIMEOUT_SECONDS", "600", 600.0),
    "optimization-idle-600-the-code-default": ("RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS", "600", 600.0),
    "optimization-idle-0-never-stop": ("RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS", "0", 0.0),
    "frame-protection-false-the-code-default": ("LIBREFOLIO_FRAME_PROTECTION", "false", False),
    "csp-report-only-false-the-code-default": ("LIBREFOLIO_CSP_REPORT_ONLY", "false", False),
}


@pytest.mark.parametrize(("variable", "written", "expected"), SET_UNDER_MANAGED.values(), ids=list(SET_UNDER_MANAGED))
def test_managed_keeps_a_value_the_environment_sets(monkeypatch: pytest.MonkeyPatch, variable: str, written: str, expected: object) -> None:
    print_section(f"LIBREFOLIO_PROFILE=managed, {variable}={written}")
    values = profile_values("managed")
    assert variable in values and not same(values[variable], expected), f"barrier: PROFILE_DEFAULTS['managed'] must list {variable} with a value other than {expected!r}, or this case proves nothing: {dict(values)}"
    unset_everything(monkeypatch)
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    monkeypatch.setenv(variable, written)

    settings = settings_from_the_environment()

    assert settings.LIBREFOLIO_PROFILE == "managed", f"barrier: the profile read is {settings.LIBREFOLIO_PROFILE!r}"
    actual = value_of(settings, variable)
    assert same(actual, expected), f"{variable}={written} is set in the environment, yet the managed profile made it {actual!r}: a set value always wins, even one equal to the code default"
    others = wrong_values(settings, {name: value for name, value in values.items() if name != variable})
    assert not others, f"with {variable} set, the other fields the managed profile lists lost their managed value ({{field: (value, managed)}}): {others}"
    print_success(f"✓ {variable} = {actual!r}; the others managed")


#: Set in the environment under selfhosted, the profile unset: the switches work without the managed profile.
SET_UNDER_SELFHOSTED: dict[str, tuple[str, str, object]] = {
    "frame-protection-true": ("LIBREFOLIO_FRAME_PROTECTION", "true", True),
    "csp-report-only-true": ("LIBREFOLIO_CSP_REPORT_ONLY", "true", True),
    "simulation-idle-60": ("RISK_SIMULATION_IDLE_TIMEOUT_SECONDS", "60", 60.0),
}


@pytest.mark.parametrize(("variable", "written", "expected"), SET_UNDER_SELFHOSTED.values(), ids=list(SET_UNDER_SELFHOSTED))
def test_selfhosted_keeps_a_value_the_environment_sets(monkeypatch: pytest.MonkeyPatch, variable: str, written: str, expected: object) -> None:
    print_section(f"LIBREFOLIO_PROFILE unset, {variable}={written}")
    assert variable in listed_by_any_profile(), f"barrier: no profile of PROFILE_DEFAULTS lists {variable}"
    default = code_default(field(variable))
    assert not same(default, expected), f"barrier: {expected!r} is the code default of {variable}: this case could not tell a set value from no value"
    unset_everything(monkeypatch)
    monkeypatch.setenv(variable, written)

    settings = settings_from_the_environment()

    assert settings.LIBREFOLIO_PROFILE == "selfhosted", f"barrier: the profile read is {settings.LIBREFOLIO_PROFILE!r}"
    actual = value_of(settings, variable)
    assert same(actual, expected), f"{variable}={written} under selfhosted gives {actual!r}, not {expected!r}"
    print_success(f"✓ {variable} = {actual!r}")


def test_a_value_set_in_the_env_file_wins_too(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    print_section("LIBREFOLIO_PROFILE=managed in .env, two fields set there")
    values = profile_values("managed")
    in_the_file = {"RISK_SIMULATION_IDLE_TIMEOUT_SECONDS": ("600", 600.0), "LIBREFOLIO_FRAME_PROTECTION": ("false", False)}
    for name, (_, expected) in in_the_file.items():
        assert name in values and not same(values[name], expected), f"barrier: PROFILE_DEFAULTS['managed'] must list {name} with a value other than {expected!r}: {dict(values)}"
    unset_everything(monkeypatch)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "0")  # in test mode Settings reads no .env at all (settings_customise_sources)
    env_file = tmp_path / ".env"
    env_file.write_text("".join(f"{line}\n" for line in [f"{PROFILE_VARIABLE}=managed", *(f"{name}={written}" for name, (written, _) in in_the_file.items())]), encoding="utf-8")

    settings = config.Settings(_env_file=env_file)

    assert settings.LIBREFOLIO_PROFILE == "managed", f"barrier: the profile is set only in {env_file}, and was read as {settings.LIBREFOLIO_PROFILE!r}: the file was not read"
    kept = wrong_values(settings, {name: expected for name, (_, expected) in in_the_file.items()})
    assert not kept, f"a value set in .env must win over the managed profile, as one set in the environment does ({{field: (value, set)}}): {kept}"
    others = wrong_values(settings, {name: value for name, value in values.items() if name not in in_the_file})
    assert not others, f"the fields .env leaves unset must take their managed value ({{field: (value, managed)}}): {others}"
    print_success("✓ .env wins where it sets a value; the profile from .env gives the rest")


# =============================================================================
# (c) SELF-HOSTED: NOTHING CHANGES
# =============================================================================


@pytest.mark.parametrize("profile", [pytest.param(None, id="profile-unset"), pytest.param("selfhosted", id="selfhosted")])
@pytest.mark.parametrize("name", LISTED_FIELDS)
def test_selfhosted_keeps_the_code_default_of_every_field_a_profile_lists(monkeypatch: pytest.MonkeyPatch, name: str, profile: str | None) -> None:
    print_section(f"LIBREFOLIO_PROFILE={profile or '(unset)'}, {name} unset")
    assert name in listed_by_any_profile(), f"barrier: no profile of PROFILE_DEFAULTS lists {name}"
    default = code_default(field(name))
    unset_everything(monkeypatch)
    if profile is not None:
        monkeypatch.setenv(PROFILE_VARIABLE, profile)

    settings = settings_from_the_environment()

    assert settings.LIBREFOLIO_PROFILE == "selfhosted", f"barrier: the profile read is {settings.LIBREFOLIO_PROFILE!r}"
    actual = value_of(settings, name)
    assert same(actual, default), f"self-hosted, {name} unset: {name} is {actual!r}, not its code default {default!r}; a self-hosted install changes nothing"
    print_success(f"✓ {name} = {actual!r}, the code default")


# =============================================================================
# (d) GUARDS ON THE TABLE
# =============================================================================


@pytest.mark.parametrize(("profile", "name"), TABLE_ENTRIES, ids=[f"{profile}-{name}" for profile, name in TABLE_ENTRIES])
def test_every_entry_names_a_field_and_holds_a_valid_value_for_it(profile: str, name: str) -> None:
    print_section(f"PROFILE_DEFAULTS[{profile!r}][{name!r}]")
    values = profile_values(profile)
    assert name in values, f"barrier: PROFILE_DEFAULTS[{profile!r}] does not list {name}: {dict(values)}"
    fields = config.Settings.model_fields
    assert name in fields, f"PROFILE_DEFAULTS[{profile!r}] lists {name}, which is not a field of Settings: a misspelt name is a setting no profile reaches"
    info, value = fields[name], values[name]

    try:
        validated = TypeAdapter(info.rebuild_annotation()).validate_python(value, strict=True)
    except ValidationError as exc:
        pytest.fail(f"PROFILE_DEFAULTS[{profile!r}][{name!r}] = {value!r} is not a valid {info.rebuild_annotation()!r} in strict mode: write it in the field's own type, as its code default is ({code_default(info)!r}). {exc}")

    assert same(validated, value), f"PROFILE_DEFAULTS[{profile!r}][{name!r}] = {value!r} validates as {validated!r}: write the value the field holds"
    print_success(f"✓ {value!r}")


@pytest.mark.parametrize("name", LISTED_FIELDS)
def test_every_field_a_profile_lists_has_a_code_default(name: str) -> None:
    print_section(f"Settings.{name}: a code default")
    assert name in listed_by_any_profile(), f"barrier: no profile of PROFILE_DEFAULTS lists {name}"

    info = field(name)

    assert not info.is_required(), f"Settings.{name} is required: a profile default only stands in for a code default, so that self-hosted keeps a value for every field a profile lists"
    print_success(f"✓ {code_default(info)!r}")


# =============================================================================
# (e) THE PROFILE, IN ANY CASE
# =============================================================================


@pytest.mark.parametrize("written", [pytest.param("MANAGED", id="upper-case"), pytest.param(" Managed ", id="spaces-and-mixed-case")])
def test_a_profile_written_in_another_case_gives_the_managed_defaults(monkeypatch: pytest.MonkeyPatch, written: str) -> None:
    print_section(f"LIBREFOLIO_PROFILE={written!r}")
    values = profile_values("managed")
    assert values, "barrier: PROFILE_DEFAULTS['managed'] lists no field"
    unset_everything(monkeypatch)
    monkeypatch.setenv(PROFILE_VARIABLE, written)

    settings = settings_from_the_environment()

    assert settings.LIBREFOLIO_PROFILE == "managed", f"barrier: LIBREFOLIO_PROFILE={written!r} is read as {settings.LIBREFOLIO_PROFILE!r}, not managed as today"
    wrong = wrong_values(settings, values)
    assert not wrong, f"LIBREFOLIO_PROFILE={written!r} is the managed profile, yet these fields lack its value ({{field: (value, managed)}}): {wrong}"
    print_success(f"✓ {sorted(values)} managed")


# =============================================================================
# (f) THE ENVIRONMENT TABLE AND profile_default() (H-17)
# =============================================================================


def test_the_environment_table_has_one_entry_per_profile_settings_accepts() -> None:
    print_section("ENVIRONMENT_PROFILE_DEFAULTS: one entry per profile")
    accepted = get_args(field(PROFILE_VARIABLE).annotation)
    assert set(accepted) == set(PROFILES), f"barrier: LIBREFOLIO_PROFILE accepts {accepted}, this file knows {PROFILES}"

    table = environment_defaults()

    assert set(table) == set(accepted), f"ENVIRONMENT_PROFILE_DEFAULTS has the profiles {sorted(table)}: it must have exactly those LIBREFOLIO_PROFILE accepts, {sorted(accepted)}, as PROFILE_DEFAULTS does"
    print_success(f"✓ {sorted(table)}")


def test_selfhosted_lists_no_variable() -> None:
    print_section("ENVIRONMENT_PROFILE_DEFAULTS['selfhosted']")

    values = environment_values("selfhosted")

    assert dict(values) == {}, f"ENVIRONMENT_PROFILE_DEFAULTS['selfhosted'] lists {dict(values)}: an install run by its owner keeps the fallback of every section module"
    print_success("✓ empty")


def test_managed_lists_the_decided_variables_with_their_types() -> None:
    print_section("ENVIRONMENT_PROFILE_DEFAULTS['managed']")

    values = environment_values("managed")

    assert dict(values) == ENVIRONMENT_MANAGED_DEFAULTS, f"ENVIRONMENT_PROFILE_DEFAULTS['managed'] is {dict(values)}, decided {ENVIRONMENT_MANAGED_DEFAULTS}"
    mistyped = {name: type(values[name]).__name__ for name, expected in ENVIRONMENT_MANAGED_DEFAULTS.items() if not exactly(values[name], expected)}
    assert not mistyped, f"equal but not of the decided type ({{variable: type found}}): {mistyped}. Write each value as its section module returns it once parsed, {ENVIRONMENT_MANAGED_DEFAULTS}: not as text, a float or a flag"
    print_success(f"✓ {ENVIRONMENT_MANAGED_DEFAULTS}")


def test_no_variable_of_the_environment_table_is_a_setting() -> None:
    print_section("ENVIRONMENT_PROFILE_DEFAULTS: no field of Settings, no name of PROFILE_DEFAULTS")
    variables = listed_in_the_environment_table()
    assert variables, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS lists no variable, so this case would prove nothing: {dict(environment_defaults())}"
    fields, settings_listed = set(config.Settings.model_fields), listed_by_any_profile()
    assert settings_listed and settings_listed <= fields, f"barrier: PROFILE_DEFAULTS must list fields of Settings, and only fields, for this case to recognise one: {sorted(settings_listed)}, not fields: {sorted(settings_listed - fields)}"

    fields_listed = sorted(variables & fields)
    in_both = sorted(variables & settings_listed)

    assert not fields_listed, f"ENVIRONMENT_PROFILE_DEFAULTS lists fields of Settings: {fields_listed}. Settings reads them itself, so their profile values go in PROFILE_DEFAULTS, which its validator applies"
    assert not in_both, f"in both ENVIRONMENT_PROFILE_DEFAULTS and PROFILE_DEFAULTS: {in_both}. One table per name: two would be two defaults that can disagree"
    print_success(f"✓ {sorted(variables)}: none is a setting")


@pytest.mark.parametrize("name", ENVIRONMENT_VARIABLES)
def test_every_variable_of_the_environment_table_is_read_by_a_section_module(name: str) -> None:
    print_section(f"{name}: written in a section module of backend/app/config/")
    assert name in listed_in_the_environment_table(), f"barrier: no profile of ENVIRONMENT_PROFILE_DEFAULTS lists {name}"
    modules = section_modules()
    assert modules, f"barrier: {CONFIG_ROOT} holds no module but __init__.py"

    writers = [path.name for path in modules if name in string_constants(path)]

    assert writers, f"no section module of backend/app/config/ ({', '.join(path.name for path in modules)}) writes the string {name!r} in its code, docstrings and comments aside: a profile value for a variable no module reads is a default nobody asks for"
    print_success(f"✓ {name} in {writers}")


@pytest.mark.parametrize("name", ENVIRONMENT_VARIABLES)
def test_every_variable_of_the_environment_table_is_in_env_example(name: str) -> None:
    print_section(f"{name}: {ENV_EXAMPLE.name}")
    assert name in listed_in_the_environment_table(), f"barrier: no profile of ENVIRONMENT_PROFILE_DEFAULTS lists {name}"
    lines = _variable_lines(ENV_EXAMPLE.read_text(encoding="utf-8"))
    assert lines, f"barrier: {ENV_EXAMPLE} yields no variable line"

    numbers = [line.number for line in lines if line.name == name]

    assert numbers, f"{ENV_EXAMPLE.name} has no line {name}= nor # {name}=: a variable a profile changes is an option, and every option LibreFolio reads is listed there"
    print_success(f"✓ {ENV_EXAMPLE.name}, line {numbers}")


#: (f) Asked under selfhosted: every variable of the environment table, listed by a profile; and one no profile lists.
ASKED_UNDER_SELFHOSTED = [*(pytest.param(name, True, id=name) for name in ENVIRONMENT_VARIABLES), pytest.param(UNLISTED_VARIABLE, False, id="unlisted")]


@pytest.mark.parametrize("profile", [pytest.param(None, id="profile-unset"), pytest.param("selfhosted", id="selfhosted")])
@pytest.mark.parametrize(("name", "listed"), ASKED_UNDER_SELFHOSTED)
def test_selfhosted_gives_back_the_fallback_itself(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, listed: bool, profile: str | None) -> None:
    print_section(f"LIBREFOLIO_PROFILE={profile or '(unset)'}, profile_default({name!r}, fallback)")
    profile_default = profile_default_function()
    listing = sorted(table_profile for table_profile, values in environment_defaults().items() if name in values)
    assert bool(listing) is listed, f"barrier: {name} is listed by the profiles {listing} of ENVIRONMENT_PROFILE_DEFAULTS, and this row expects it listed by {'some' if listed else 'none'}"
    configure_profile(monkeypatch, tmp_path, profile, "selfhosted")
    fallback = object()

    result = profile_default(name, fallback)

    assert result is fallback, f"self-hosted ({PROFILE_VARIABLE}={profile!r}): profile_default({name!r}, fallback) gives {described(result, fallback)}, not the fallback itself: a self-hosted install keeps the fallback of every section module"
    print_success("✓ the fallback itself")


#: fallback_like() (f): entries that are the empty value of their type, legitimate since H-37, and entries that are not.
FALLBACK_LIKE_ENTRIES: dict[str, object] = {
    "int-0": 0,
    "float-0.0": 0.0,
    "bool-False": False,
    "str-empty": "",
    "int-500": 500,
    "float-60.0": 60.0,
    "bool-True": True,
    "str-a": "a",
}


@pytest.mark.parametrize("entry", FALLBACK_LIKE_ENTRIES.values(), ids=list(FALLBACK_LIKE_ENTRIES))
def test_fallback_like_gives_a_value_of_the_entry_s_type_that_is_not_the_entry(entry: object) -> None:
    print_section(f"fallback_like({entry!r}): the reader's own default the cases of (f) pass")

    fallback = fallback_like(entry)

    assert type(fallback) is type(entry), f"fallback_like({entry!r}) gives {fallback!r}, a {type(fallback).__name__}, not a {type(entry).__name__}: (g) would refuse the entry to such a reader, and its case would fail on the helper, not on the product"
    assert fallback != entry, f"fallback_like({entry!r}) gives {fallback!r}, equal to the entry: a case could not tell the entry from the fallback"
    print_success(f"✓ {fallback!r} ({type(fallback).__name__})")


@pytest.mark.parametrize("name", ENVIRONMENT_MANAGED_VARIABLES)
def test_managed_gives_the_value_it_lists_as_the_table_holds_it(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str) -> None:
    print_section(f"LIBREFOLIO_PROFILE=managed, profile_default({name!r}, fallback)")
    profile_default = profile_default_function()
    values = environment_values("managed")
    assert name in values, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] does not list {name}: {dict(values)}"
    expected = values[name]
    configure_profile(monkeypatch, tmp_path, "managed", "managed")
    fallback = fallback_like(expected)  # H-27: a reader's own default is of the entry's type; (g) refuses any other

    result = profile_default(name, fallback)

    assert exactly(result, expected), f"{PROFILE_VARIABLE}=managed: profile_default({name!r}, fallback) gives {described(result, fallback)}, not the managed {expected!r} ({type(expected).__name__}) as the table holds it"
    print_success(f"✓ {name} = {result!r}")


#: (f) H-37: the own default a reader may pass for a variable the managed profile does not list. None of them comes
#: back: a fresh object, which only the very object would match, and the falsy defaults, each of which a reader may
#: take for "no limit", "off" or "nothing".
UNLISTED_FALLBACKS: dict[str, object] = {
    "object": object(),
    "int-0": 0,
    "float-0.0": 0.0,
    "str-empty": "",
    "bool-False": False,
    "None": None,
}


@pytest.mark.parametrize("fallback", UNLISTED_FALLBACKS.values(), ids=list(UNLISTED_FALLBACKS))
def test_managed_refuses_a_variable_it_does_not_list(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fallback: object) -> None:
    print_section(f"LIBREFOLIO_PROFILE=managed, profile_default({UNLISTED_VARIABLE!r}, {fallback!r}): not listed (H-37)")
    profile_default = profile_default_function()
    values = environment_values("managed")
    assert values and UNLISTED_VARIABLE not in values, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] must list some variables, and not {UNLISTED_VARIABLE}: {dict(values)}"
    configure_profile(monkeypatch, tmp_path, "managed", "managed")

    with pytest.raises(TypeError) as refused:
        result = profile_default(UNLISTED_VARIABLE, fallback)
        # reached only when nothing was raised: say what came back
        pytest.fail(
            f"{PROFILE_VARIABLE}=managed: profile_default({UNLISTED_VARIABLE!r}, {fallback!r}) gives {described(result, fallback)} for a variable the managed profile does not list, instead of raising ProfileDefaultError (H-37; E, R13-SEC7): a reader whose entry is missing stops, as a managed upload limit missing from the table would otherwise be 0, no limit at all"
        )

    error = profile_default_error()
    assert isinstance(refused.value, error), f"profile_default({UNLISTED_VARIABLE!r}, {fallback!r}) under managed raises {refused.value!r}, a TypeError but not ProfileDefaultError"
    message = str(refused.value)
    missing = [part for part in (UNLISTED_VARIABLE, "managed", "ENVIRONMENT_PROFILE_DEFAULTS") if part not in message]
    assert not missing, f"the message of ProfileDefaultError names the variable, the profile and the table, so that whoever reads the log knows which entry to add: {missing} missing from {message!r}"
    print_success(f"✓ ProfileDefaultError: {message}")


@pytest.mark.parametrize("written", [pytest.param("MANAGED", id="upper-case"), pytest.param(" Managed ", id="spaces-and-mixed-case")])
def test_a_profile_written_in_another_case_is_managed_for_profile_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, written: str) -> None:
    print_section(f"LIBREFOLIO_PROFILE={written!r}, profile_default({SAMPLE_VARIABLE!r}, fallback)")
    profile_default = profile_default_function()
    values = environment_values("managed")
    assert SAMPLE_VARIABLE in values, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] does not list {SAMPLE_VARIABLE}: {dict(values)}"
    expected = values[SAMPLE_VARIABLE]
    configure_profile(monkeypatch, tmp_path, written, "managed")
    fallback = fallback_like(expected)  # H-27: a reader's own default is of the entry's type; (g) refuses any other

    result = profile_default(SAMPLE_VARIABLE, fallback)

    assert exactly(result, expected), f"{PROFILE_VARIABLE}={written!r} is the managed profile, as Settings reads it, yet profile_default({SAMPLE_VARIABLE!r}, fallback) gives {described(result, fallback)}, not the managed {expected!r}: read the profile from get_settings()"
    print_success(f"✓ {SAMPLE_VARIABLE} = {result!r}")


@pytest.mark.parametrize("written", [pytest.param("MANAGED", id="upper-case"), pytest.param(" Managed ", id="spaces-and-mixed-case")])
def test_a_profile_written_in_another_case_refuses_a_variable_it_does_not_list(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, written: str) -> None:
    print_section(f"LIBREFOLIO_PROFILE={written!r}, profile_default({UNLISTED_VARIABLE!r}, fallback): not listed (H-37)")
    profile_default = profile_default_function()
    values = environment_values("managed")
    assert values and UNLISTED_VARIABLE not in values, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] must list some variables, and not {UNLISTED_VARIABLE}: {dict(values)}"
    configure_profile(monkeypatch, tmp_path, written, "managed")
    fallback = object()

    with pytest.raises(TypeError) as refused:
        result = profile_default(UNLISTED_VARIABLE, fallback)
        # reached only when nothing was raised: say what came back
        pytest.fail(
            f"{PROFILE_VARIABLE}={written!r} is the managed profile, as Settings reads it, yet profile_default({UNLISTED_VARIABLE!r}, fallback) gives {described(result, fallback)} for a variable the managed profile does not list, instead of raising ProfileDefaultError (H-37) as for {PROFILE_VARIABLE}=managed"
        )

    error = profile_default_error()
    assert isinstance(refused.value, error), f"{PROFILE_VARIABLE}={written!r}: profile_default({UNLISTED_VARIABLE!r}, fallback) raises {refused.value!r}, a TypeError but not ProfileDefaultError"
    message = str(refused.value)
    missing = [part for part in (UNLISTED_VARIABLE, "managed", "ENVIRONMENT_PROFILE_DEFAULTS") if part not in message]
    assert not missing, f"{PROFILE_VARIABLE}={written!r}: the message of ProfileDefaultError names the variable, the profile as Settings reads it and the table: {missing} missing from {message!r}"
    print_success(f"✓ ProfileDefaultError: {message}")


def test_profile_default_reads_the_profile_at_each_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    print_section(f"profile_default({SAMPLE_VARIABLE!r}, fallback): managed, then selfhosted")
    profile_default = profile_default_function()
    values = environment_values("managed")
    assert SAMPLE_VARIABLE in values, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] does not list {SAMPLE_VARIABLE}: {dict(values)}"
    expected = values[SAMPLE_VARIABLE]
    fallback = fallback_like(expected)  # H-27: a reader's own default is of the entry's type; (g) refuses any other
    configure_profile(monkeypatch, tmp_path, "managed", "managed")

    first = profile_default(SAMPLE_VARIABLE, fallback)

    assert exactly(first, expected), f"{PROFILE_VARIABLE}=managed: profile_default({SAMPLE_VARIABLE!r}, fallback) gives {described(first, fallback)}, not the managed {expected!r}"
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")  # between the two calls, and nothing else changes
    resolved = config.get_settings().LIBREFOLIO_PROFILE
    assert resolved == "selfhosted", f"barrier: with {PROFILE_VARIABLE}=selfhosted, get_settings() reads the profile {resolved!r}"

    second = profile_default(SAMPLE_VARIABLE, fallback)

    assert second is fallback, f"{PROFILE_VARIABLE} went from managed to selfhosted between two calls, yet profile_default({SAMPLE_VARIABLE!r}, fallback) still gives {described(second, fallback)}: the profile is read at each call, never kept"
    print_success("✓ managed, then the fallback itself")


# =============================================================================
# (g) THE TYPE OF AN ENTRY, CHECKED WHEN A READER ASKS FOR IT (H-27)
# =============================================================================

#: (g): a reader's own default, and an entry of another type the managed table might hold for its variable. ``True`` is
#: no ``int`` and ``1`` no ``bool`` (though ``bool`` subclasses ``int``), ``60`` no ``float``, ``"500"`` no ``int``, and
#: ``None`` fits none of them.
WRONG_TYPES: dict[str, tuple[object, object]] = {
    "int-default-None": (0, None),
    "int-default-text-500": (0, "500"),
    "int-default-float-500.0": (0, 500.0),
    "int-default-flag-True": (0, True),
    "bool-default-int-1": (False, 1),
    "bool-default-None": (False, None),
    "float-default-int-60": (60.0, 60),
    "str-default-None": ("", None),
    "str-default-int-0": ("", 0),
}
#: (g): a reader's own default, and an entry of its very type, other than the default.
RIGHT_TYPES: dict[str, tuple[object, object]] = {
    "int-7": (0, 7),
    "bool-True": (False, True),
    "float-1.5": (60.0, 1.5),
    "str-x": ("", "x"),
}


def test_profile_default_error_is_a_type_error() -> None:
    print_section("ProfileDefaultError (H-27)")

    error = profile_default_error()

    print_success(f"✓ {error.__module__}.{error.__qualname__}, a TypeError")


@pytest.mark.parametrize(("fallback", "entry"), WRONG_TYPES.values(), ids=list(WRONG_TYPES))
def test_managed_refuses_an_entry_not_of_the_type_of_its_reader_s_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fallback: object, entry: object) -> None:
    print_section(f"LIBREFOLIO_PROFILE=managed, the table gives {entry!r}: profile_default({H27_VARIABLE!r}, {fallback!r})")
    profile_default = profile_default_function()
    assert type(entry) is not type(fallback), f"barrier: {entry!r} and {fallback!r} are both {type(entry).__name__}: this row proves nothing"
    list_the_test_variable_in_managed(monkeypatch, entry)
    configure_profile(monkeypatch, tmp_path, "managed", "managed")

    with pytest.raises(TypeError) as refused:
        result = profile_default(H27_VARIABLE, fallback)
        # reached only when nothing was raised: say what came back
        pytest.fail(f"managed, the table giving {H27_VARIABLE} {entry!r}: profile_default({H27_VARIABLE!r}, {fallback!r}) gives {described(result, fallback)} to a reader whose own default is a {type(fallback).__name__}, instead of raising ProfileDefaultError (H-27)")

    error = profile_default_error()
    assert isinstance(refused.value, error), f"profile_default({H27_VARIABLE!r}, {fallback!r}) with {entry!r} in the managed table raises {refused.value!r}, a TypeError but not ProfileDefaultError"
    message = str(refused.value)
    missing = [part for part in (H27_VARIABLE, "managed", type(entry).__name__, type(fallback).__name__, "ENVIRONMENT_PROFILE_DEFAULTS") if part not in message]
    assert not missing, f"the message of ProfileDefaultError names the variable, the profile, the entry's type, the reader's type and the table, so that whoever reads the log knows what to fix: {missing} missing from {message!r}"
    print_success(f"✓ ProfileDefaultError: {message}")


@pytest.mark.parametrize("profile", [pytest.param(None, id="profile-unset"), pytest.param("selfhosted", id="selfhosted")])
@pytest.mark.parametrize(("fallback", "entry"), WRONG_TYPES.values(), ids=list(WRONG_TYPES))
def test_selfhosted_gives_back_the_fallback_itself_whatever_the_managed_table_holds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fallback: object, entry: object, profile: str | None) -> None:
    print_section(f"LIBREFOLIO_PROFILE={profile or '(unset)'}, the managed table gives {entry!r}: profile_default({H27_VARIABLE!r}, {fallback!r})")
    profile_default = profile_default_function()
    list_the_test_variable_in_managed(monkeypatch, entry)  # only the managed profile lists it
    configure_profile(monkeypatch, tmp_path, profile, "selfhosted")

    try:
        result = profile_default(H27_VARIABLE, fallback)
    except TypeError as exc:
        pytest.fail(f"self-hosted ({PROFILE_VARIABLE}={profile!r}): profile_default({H27_VARIABLE!r}, {fallback!r}) raises {exc!r}, because the managed table gives {entry!r}: the selfhosted profile lists no variable, so the reader gets its own default, with nothing to check")

    assert result is fallback, f"self-hosted ({PROFILE_VARIABLE}={profile!r}): profile_default({H27_VARIABLE!r}, {fallback!r}) gives {described(result, fallback)}, not the fallback itself, though only the managed table lists {H27_VARIABLE}"
    print_success("✓ the fallback itself, no error")


@pytest.mark.parametrize(("fallback", "entry"), RIGHT_TYPES.values(), ids=list(RIGHT_TYPES))
def test_managed_gives_an_entry_of_its_reader_s_type_as_the_table_holds_it(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fallback: object, entry: object) -> None:
    print_section(f"LIBREFOLIO_PROFILE=managed, the table gives {entry!r}: profile_default({H27_VARIABLE!r}, {fallback!r})")
    profile_default = profile_default_function()
    assert type(entry) is type(fallback) and entry != fallback, f"barrier: {entry!r} must be of the type of {fallback!r} and differ from it, or this row cannot tell the entry from the fallback"
    list_the_test_variable_in_managed(monkeypatch, entry)
    configure_profile(monkeypatch, tmp_path, "managed", "managed")

    try:
        result = profile_default(H27_VARIABLE, fallback)
    except TypeError as exc:
        pytest.fail(f"{PROFILE_VARIABLE}=managed: profile_default({H27_VARIABLE!r}, {fallback!r}) raises {exc!r} for the entry {entry!r}, a {type(entry).__name__} like the reader's own default: only another type is refused")

    assert exactly(result, entry), f"{PROFILE_VARIABLE}=managed: profile_default({H27_VARIABLE!r}, {fallback!r}) gives {described(result, fallback)}, not the managed {entry!r} ({type(entry).__name__}) as the table holds it"
    print_success(f"✓ {result!r}")


#: (g) H-37: entries equal to their reader's own default, of its very type, which a profile other than selfhosted lists
#: for a variable it leaves at the self-hosted behaviour, now that it must list every variable a reader asks for.
ENTRIES_AT_THE_READER_S_DEFAULT: dict[str, object] = {"int-0": 0, "float-0.0": 0.0, "bool-False": False, "str-empty": ""}


@pytest.mark.parametrize("entry", ENTRIES_AT_THE_READER_S_DEFAULT.values(), ids=list(ENTRIES_AT_THE_READER_S_DEFAULT))
def test_managed_gives_an_entry_equal_to_its_reader_s_own_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, entry: object) -> None:
    print_section(f"LIBREFOLIO_PROFILE=managed, the table gives {entry!r}: profile_default({H27_VARIABLE!r}, {entry!r}) (H-37)")
    profile_default = profile_default_function()
    fallback = type(entry)()
    assert exactly(fallback, entry), f"barrier: the reader's own default {fallback!r} must equal the entry {entry!r}, of its very type: this row is about an entry at that default"
    list_the_test_variable_in_managed(monkeypatch, entry)
    configure_profile(monkeypatch, tmp_path, "managed", "managed")

    try:
        result = profile_default(H27_VARIABLE, fallback)
    except TypeError as exc:
        pytest.fail(f"{PROFILE_VARIABLE}=managed: profile_default({H27_VARIABLE!r}, {fallback!r}) raises {exc!r} for the entry {entry!r}, of the reader's own type and value: a profile other than selfhosted lists such an entry to keep the self-hosted behaviour (H-37), and nothing in it is wrong")

    assert exactly(result, entry), f"{PROFILE_VARIABLE}=managed: profile_default({H27_VARIABLE!r}, {fallback!r}) gives {result!r} ({type(result).__name__}), not the managed {entry!r} ({type(entry).__name__}) as the table holds it"
    print_success(f"✓ {result!r}")


def test_none_for_the_upload_limit_in_the_managed_table_stops_its_reader(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    print_section(f"LIBREFOLIO_PROFILE=managed, {UPLOAD_LIMIT_VARIABLE} unset, None in the managed table: backup_max_upload_mb()")
    assert backup_config.MAX_UPLOAD_VARIABLE == UPLOAD_LIMIT_VARIABLE, f"barrier: backup_max_upload_mb() reads {backup_config.MAX_UPLOAD_VARIABLE}, not {UPLOAD_LIMIT_VARIABLE}"
    managed = environment_values("managed")
    assert UPLOAD_LIMIT_VARIABLE in managed, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] does not list {UPLOAD_LIMIT_VARIABLE}: {dict(managed)}"
    monkeypatch.delenv(UPLOAD_LIMIT_VARIABLE, raising=False)  # unset: the reader asks the profile
    configure_profile(monkeypatch, tmp_path, "managed", "managed")
    monkeypatch.setitem(managed, UPLOAD_LIMIT_VARIABLE, None)  # E, R13-SEC3: the entry a wrong edit of the table leaves

    with pytest.raises(TypeError) as refused:
        limit = backup_config.backup_max_upload_mb()
        # reached only when nothing was raised: say what came back
        pytest.fail(f"backup_max_upload_mb() returns {limit!r} ({type(limit).__name__}) with None in the managed table; _upload_limit() of api/v1/backup/restore.py reads None or 0 as no limit at all (fail-open): profile_default() must raise ProfileDefaultError instead (H-27)")

    error = profile_default_error()
    assert isinstance(refused.value, error), f"backup_max_upload_mb() with None in the managed table raises {refused.value!r}, a TypeError but not ProfileDefaultError"
    assert UPLOAD_LIMIT_VARIABLE in str(refused.value), f"the ProfileDefaultError of the upload limit does not name {UPLOAD_LIMIT_VARIABLE}: {refused.value}"
    print_success(f"✓ ProfileDefaultError: {refused.value}")


def test_a_missing_managed_upload_limit_stops_its_reader(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    print_section(f"LIBREFOLIO_PROFILE=managed, {UPLOAD_LIMIT_VARIABLE} unset, its managed entry removed: backup_max_upload_mb() (H-37)")
    assert backup_config.MAX_UPLOAD_VARIABLE == UPLOAD_LIMIT_VARIABLE, f"barrier: backup_max_upload_mb() reads {backup_config.MAX_UPLOAD_VARIABLE}, not {UPLOAD_LIMIT_VARIABLE}"
    managed = environment_values("managed")
    assert UPLOAD_LIMIT_VARIABLE in managed, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] does not list {UPLOAD_LIMIT_VARIABLE}: {dict(managed)}"
    monkeypatch.delenv(UPLOAD_LIMIT_VARIABLE, raising=False)  # unset: the reader asks the profile
    configure_profile(monkeypatch, tmp_path, "managed", "managed")
    monkeypatch.delitem(managed, UPLOAD_LIMIT_VARIABLE)  # E, R13-SEC7: the entry a wrong edit of the table removes

    with pytest.raises(TypeError) as refused:
        limit = backup_config.backup_max_upload_mb()
        # reached only when nothing was raised: say what came back
        pytest.fail(
            f"backup_max_upload_mb() returns {limit!r} ({type(limit).__name__}) with {UPLOAD_LIMIT_VARIABLE} missing from the managed table, instead of stopping: its own default, 0, is no limit at all for _upload_limit() of api/v1/backup/restore.py, so a managed instance whose table lost the entry would lose its {ENVIRONMENT_MANAGED_DEFAULTS[UPLOAD_LIMIT_VARIABLE]} MB limit in silence (fail-open); profile_default() must raise ProfileDefaultError for a variable the managed profile does not list (H-37; E, R13-SEC7)"
        )

    error = profile_default_error()
    assert isinstance(refused.value, error), f"backup_max_upload_mb() with {UPLOAD_LIMIT_VARIABLE} missing from the managed table raises {refused.value!r}, a TypeError but not ProfileDefaultError"
    assert UPLOAD_LIMIT_VARIABLE in str(refused.value), f"the ProfileDefaultError of the missing upload limit does not name {UPLOAD_LIMIT_VARIABLE}: {refused.value}"
    print_success(f"✓ ProfileDefaultError: {refused.value}")


@pytest.mark.parametrize("profile", [pytest.param(None, id="profile-unset"), pytest.param("selfhosted", id="selfhosted")])
def test_a_missing_managed_upload_limit_leaves_selfhosted_unchanged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile: str | None) -> None:
    print_section(f"LIBREFOLIO_PROFILE={profile or '(unset)'}, {UPLOAD_LIMIT_VARIABLE} unset, its managed entry removed: backup_max_upload_mb() (H-37)")
    assert backup_config.MAX_UPLOAD_VARIABLE == UPLOAD_LIMIT_VARIABLE, f"barrier: backup_max_upload_mb() reads {backup_config.MAX_UPLOAD_VARIABLE}, not {UPLOAD_LIMIT_VARIABLE}"
    managed = environment_values("managed")
    assert UPLOAD_LIMIT_VARIABLE in managed, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] does not list {UPLOAD_LIMIT_VARIABLE}: {dict(managed)}"
    monkeypatch.delenv(UPLOAD_LIMIT_VARIABLE, raising=False)  # unset: the reader asks the profile
    configure_profile(monkeypatch, tmp_path, profile, "selfhosted")
    monkeypatch.delitem(managed, UPLOAD_LIMIT_VARIABLE)  # only the managed profile listed it

    try:
        limit = backup_config.backup_max_upload_mb()
    except TypeError as exc:
        pytest.fail(
            f"self-hosted ({PROFILE_VARIABLE}={profile!r}): backup_max_upload_mb() raises {exc!r} because the managed table lost {UPLOAD_LIMIT_VARIABLE}: H-37 stops a reader only under a profile other than selfhosted, and a self-hosted install keeps its own default, whatever the managed table holds"
        )

    assert exactly(limit, 0), f"self-hosted ({PROFILE_VARIABLE}={profile!r}), {UPLOAD_LIMIT_VARIABLE} unset: backup_max_upload_mb() gives {limit!r} ({type(limit).__name__}), not 0 (int), the self-hosted default: no limit, as before H-37"
    print_success("✓ 0, no limit, as before")


def test_the_upload_limit_is_the_managed_entry_as_the_table_holds_it(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    print_section(f"LIBREFOLIO_PROFILE=managed, {UPLOAD_LIMIT_VARIABLE} unset, the real table: backup_max_upload_mb()")
    assert backup_config.MAX_UPLOAD_VARIABLE == UPLOAD_LIMIT_VARIABLE, f"barrier: backup_max_upload_mb() reads {backup_config.MAX_UPLOAD_VARIABLE}, not {UPLOAD_LIMIT_VARIABLE}"
    expected = ENVIRONMENT_MANAGED_DEFAULTS[UPLOAD_LIMIT_VARIABLE]
    entry = environment_values("managed").get(UPLOAD_LIMIT_VARIABLE)
    assert exactly(entry, expected), f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] gives {UPLOAD_LIMIT_VARIABLE} {entry!r} ({type(entry).__name__}), not the decided {expected!r}"
    monkeypatch.delenv(UPLOAD_LIMIT_VARIABLE, raising=False)  # unset: the reader asks the profile
    configure_profile(monkeypatch, tmp_path, "managed", "managed")

    limit = backup_config.backup_max_upload_mb()

    assert exactly(limit, expected), f"{PROFILE_VARIABLE}=managed, {UPLOAD_LIMIT_VARIABLE} unset: backup_max_upload_mb() gives {limit!r} ({type(limit).__name__}), not the managed {expected!r} ({type(expected).__name__}): an entry of the reader's type comes back as the table holds it"
    print_success(f"✓ {limit!r} MB")


# =============================================================================
# (h) THE SAME RULES, ON THE SOURCE (H-27, H-37)
# =============================================================================


def test_every_reader_s_default_is_of_the_type_every_profile_gives_its_variable() -> None:
    print_section("profile_default(<name>, <literal>) in the section modules: every profile's entry of the literal's type")
    calls = profile_default_calls()
    assert calls, f"barrier: no section module of backend/app/config/ ({', '.join(path.name for path in section_modules())}) calls profile_default, not even backup.py for {UPLOAD_LIMIT_VARIABLE}: this guard would compare nothing"
    unreadable = {f"{call.where} {call.source}": call.problems() for call in calls if not call.readable}
    assert not unreadable, f"profile_default calls whose arguments the source does not state ({{call: problems}}): {unreadable}. Write the name as a string literal or a top-level constant, and the reader's default as a literal, so that (h) can read its type"
    unread = sorted(listed_in_the_environment_table() - {call.name for call in calls})
    assert not unread, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS lists {unread}, and no call of profile_default in a section module reads it: the type of its entries would be compared with no reader's default"

    mismatches = type_mismatches(calls)

    assert not mismatches, "entries not of the type of their reader's own default, so profile_default() raises ProfileDefaultError when the reader runs (g): " + "; ".join(map(str, mismatches)) + ". Write each entry in its reader's type"
    print_success("✓ " + "; ".join(f"{call.source} reads a {type(call.fallback).__name__}" for call in calls))


def test_the_type_guard_reports_an_entry_of_another_type(monkeypatch: pytest.MonkeyPatch) -> None:
    print_section(f"(h) self-test: None for {UPLOAD_LIMIT_VARIABLE} in the managed table")
    readers = [call for call in profile_default_calls() if call.readable and call.name == UPLOAD_LIMIT_VARIABLE]
    assert readers, f"barrier: no call of profile_default in a section module reads {UPLOAD_LIMIT_VARIABLE} with arguments its source states: this self-test has no reader to trip"
    assert all(call.fallback is not None for call in readers), f"barrier: a reader of {UPLOAD_LIMIT_VARIABLE} has None for its own default, so None would be the right type: {[call.source for call in readers]}"
    before = [mismatch for mismatch in type_mismatches(readers) if mismatch.profile == "managed"]
    assert not before, f"barrier: with the real table the guard already reports {UPLOAD_LIMIT_VARIABLE} in managed ({'; '.join(map(str, before))}): this self-test could not tell its own entry from that one"
    monkeypatch.setitem(environment_values("managed"), UPLOAD_LIMIT_VARIABLE, None)

    after = [mismatch for mismatch in type_mismatches(readers) if mismatch.profile == "managed"]

    unreported = [call.where for call in readers if not any(mismatch.call == call and mismatch.value is None for mismatch in after)]
    assert not unreported, f"with None for {UPLOAD_LIMIT_VARIABLE} in ENVIRONMENT_PROFILE_DEFAULTS['managed'], type_mismatches() does not report the reader at {unreported}: the guard of (h) would let that entry through"
    print_success("✓ " + "; ".join(map(str, after)))


def test_every_reader_s_variable_is_listed_by_every_profile_but_selfhosted() -> None:
    print_section("profile_default(<name>, <literal>) in the section modules: <name> listed by every profile but selfhosted (H-37)")
    calls = profile_default_calls()
    assert calls, f"barrier: no section module of backend/app/config/ ({', '.join(path.name for path in section_modules())}) calls profile_default, not even backup.py for {UPLOAD_LIMIT_VARIABLE}: this guard would check nothing"
    unreadable = sorted(f"{call.where} {call.source}" for call in calls if not call.readable)
    assert not unreadable, f"barrier: profile_default calls whose arguments the source does not state, so this guard cannot read their variable: {unreadable} (test_every_reader_s_default_is_of_the_type_every_profile_gives_its_variable says how to write them)"
    profiles = sorted(profile for profile in environment_defaults() if profile != "selfhosted")
    assert profiles, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS has no profile but selfhosted ({sorted(environment_defaults())}): this guard would check nothing"

    missing = missing_entries(calls)

    assert not missing, (
        "variables a reader asks for that a profile other than selfhosted does not list, so profile_default() raises ProfileDefaultError there when the reader runs (H-37): " + "; ".join(map(str, missing)) + ". List each in every profile but selfhosted, at a value of its reader's type"
    )
    print_success("✓ " + "; ".join(f"{call.name} listed by {profiles}" for call in calls))


def test_the_coverage_guard_reports_a_missing_managed_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    print_section(f"(h) self-test: {UPLOAD_LIMIT_VARIABLE} removed from the managed table (H-37)")
    readers = [call for call in profile_default_calls() if call.readable and call.name == UPLOAD_LIMIT_VARIABLE]
    assert readers, f"barrier: no call of profile_default in a section module reads {UPLOAD_LIMIT_VARIABLE} with arguments its source states: this self-test has no reader to trip"
    managed = environment_values("managed")
    before = missing_entries(readers)
    assert not before, f"barrier: with the real table the guard already reports the readers of {UPLOAD_LIMIT_VARIABLE} ({'; '.join(map(str, before))}): this self-test could not tell its own removal from that"
    monkeypatch.delitem(managed, UPLOAD_LIMIT_VARIABLE)

    after = [entry for entry in missing_entries(readers) if entry.profile == "managed"]

    unreported = [call.where for call in readers if not any(entry.call == call for entry in after)]
    assert not unreported, f"with {UPLOAD_LIMIT_VARIABLE} removed from ENVIRONMENT_PROFILE_DEFAULTS['managed'], missing_entries() does not report the reader at {unreported}: the guard of (h) would let that table through"
    print_success("✓ " + "; ".join(map(str, after)))
