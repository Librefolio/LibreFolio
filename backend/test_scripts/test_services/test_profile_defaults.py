"""
The profile defaults of the settings (workstream H, platform, checkpoint CP7b-2; developer decisions D5 and F27), and of
the variables read outside them (H-17).

Under test: ``PROFILE_DEFAULTS`` and the validator of ``Settings`` that applies it, both in ``backend/app/config/__init__.py``,
and the two fields D5 adds there; next to them, ``ENVIRONMENT_PROFILE_DEFAULTS`` and ``profile_default()`` (H-17). The
contract:

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
    ``profile_default(name, fallback)`` gives the active profile's entry for ``name``, as the table holds it, or else
    ``fallback`` itself: always when self-hosted (the profile unset or ``selfhosted``), and in managed for a name it does
    not list. The profile is ``get_settings().LIBREFOLIO_PROFILE``, read at each call: ``MANAGED`` and `` Managed `` are
    managed, and a profile changed between two calls is followed.

``Settings`` is built with ``_env_file=None`` after the profile and every listed field are removed from the environment
with ``monkeypatch``, so neither the shell nor the instance's ``.env`` reaches a case. The one case about ``.env`` writes
its own file under ``tmp_path`` and turns test mode off for the call: in test mode ``Settings`` reads no ``.env`` at all
(``settings_customise_sources``). ``profile_default()`` reads ``get_settings()``, which takes no ``_env_file``: the cases
that call it set ``LIBREFOLIO_TEST_MODE=1`` (no ``.env``) and ``LIBREFOLIO_TEST_DATA_DIR`` under ``tmp_path`` (never the
lane's data), remove the profile and every variable of the environment table, set the profile they mean, all with
``monkeypatch``, and check that ``get_settings()`` reads it so; their fallback is a fresh ``object()``, for which only the
very object can pass. ``PROFILE_DEFAULTS``, ``ENVIRONMENT_PROFILE_DEFAULTS`` and ``profile_default`` are read with
``getattr`` when a test runs, so this file collects before they exist and each test fails on its own. The sources of
``backend/app/config/`` and ``.env.example`` are only read, as text. No DB, no server, no network.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import get_args

import pytest
from pydantic import TypeAdapter, ValidationError
from pydantic.fields import FieldInfo

from backend.app import config
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
#: H-17 (decision 43): the value the managed profile gives each variable a section module of backend/app/config/ reads
#: from the environment outside Settings, while that variable is unset.
ENVIRONMENT_MANAGED_DEFAULTS: dict[str, object] = {"LIBREFOLIO_BACKUP_MAX_UPLOAD_MB": 500}
#: (f): a variable no profile lists: profile_default() gives its fallback back, whatever the profile.
UNLISTED_VARIABLE = "LIBREFOLIO_NO_PROFILE_LISTS_THIS"
#: (f): one variable of the decided table, for the cases about how the profile is read.
SAMPLE_VARIABLE = next(iter(ENVIRONMENT_MANAGED_DEFAULTS))

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


def configure_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, written: str | None, profile: str) -> None:
    """Make ``get_settings()`` read ``LIBREFOLIO_PROFILE`` as ``written`` (``None``: unset) from this environment alone, and
    check that it reads the profile ``profile``. Every variable of the environment table is unset, as it is whenever a
    section module asks ``profile_default()``."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")  # get_settings() reads no .env in test mode: only this environment
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))  # get_settings() never looks at the lane's data
    for name in (PROFILE_VARIABLE, *ENVIRONMENT_VARIABLES, UNLISTED_VARIABLE):
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


@pytest.mark.parametrize("name", ENVIRONMENT_MANAGED_VARIABLES)
def test_managed_gives_the_value_it_lists_as_the_table_holds_it(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str) -> None:
    print_section(f"LIBREFOLIO_PROFILE=managed, profile_default({name!r}, fallback)")
    profile_default = profile_default_function()
    values = environment_values("managed")
    assert name in values, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] does not list {name}: {dict(values)}"
    expected = values[name]
    configure_profile(monkeypatch, tmp_path, "managed", "managed")
    fallback = object()

    result = profile_default(name, fallback)

    assert exactly(result, expected), f"{PROFILE_VARIABLE}=managed: profile_default({name!r}, fallback) gives {described(result, fallback)}, not the managed {expected!r} ({type(expected).__name__}) as the table holds it"
    print_success(f"✓ {name} = {result!r}")


def test_managed_gives_back_the_fallback_itself_for_a_variable_it_does_not_list(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    print_section(f"LIBREFOLIO_PROFILE=managed, profile_default({UNLISTED_VARIABLE!r}, fallback)")
    profile_default = profile_default_function()
    values = environment_values("managed")
    assert values and UNLISTED_VARIABLE not in values, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] must list some variables, and not {UNLISTED_VARIABLE}: {dict(values)}"
    configure_profile(monkeypatch, tmp_path, "managed", "managed")
    fallback = object()

    result = profile_default(UNLISTED_VARIABLE, fallback)

    assert result is fallback, f"{PROFILE_VARIABLE}=managed: profile_default({UNLISTED_VARIABLE!r}, fallback) gives {described(result, fallback)}, not the fallback itself, for a variable the managed profile does not list"
    print_success("✓ the fallback itself")


@pytest.mark.parametrize("written", [pytest.param("MANAGED", id="upper-case"), pytest.param(" Managed ", id="spaces-and-mixed-case")])
def test_a_profile_written_in_another_case_is_managed_for_profile_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, written: str) -> None:
    print_section(f"LIBREFOLIO_PROFILE={written!r}, profile_default({SAMPLE_VARIABLE!r}, fallback)")
    profile_default = profile_default_function()
    values = environment_values("managed")
    assert SAMPLE_VARIABLE in values, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] does not list {SAMPLE_VARIABLE}: {dict(values)}"
    expected = values[SAMPLE_VARIABLE]
    configure_profile(monkeypatch, tmp_path, written, "managed")
    fallback = object()

    result = profile_default(SAMPLE_VARIABLE, fallback)

    assert exactly(result, expected), f"{PROFILE_VARIABLE}={written!r} is the managed profile, as Settings reads it, yet profile_default({SAMPLE_VARIABLE!r}, fallback) gives {described(result, fallback)}, not the managed {expected!r}: read the profile from get_settings()"
    print_success(f"✓ {SAMPLE_VARIABLE} = {result!r}")


def test_profile_default_reads_the_profile_at_each_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    print_section(f"profile_default({SAMPLE_VARIABLE!r}, fallback): managed, then selfhosted")
    profile_default = profile_default_function()
    values = environment_values("managed")
    assert SAMPLE_VARIABLE in values, f"barrier: ENVIRONMENT_PROFILE_DEFAULTS['managed'] does not list {SAMPLE_VARIABLE}: {dict(values)}"
    expected, fallback = values[SAMPLE_VARIABLE], object()
    configure_profile(monkeypatch, tmp_path, "managed", "managed")

    first = profile_default(SAMPLE_VARIABLE, fallback)

    assert exactly(first, expected), f"{PROFILE_VARIABLE}=managed: profile_default({SAMPLE_VARIABLE!r}, fallback) gives {described(first, fallback)}, not the managed {expected!r}"
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")  # between the two calls, and nothing else changes
    resolved = config.get_settings().LIBREFOLIO_PROFILE
    assert resolved == "selfhosted", f"barrier: with {PROFILE_VARIABLE}=selfhosted, get_settings() reads the profile {resolved!r}"

    second = profile_default(SAMPLE_VARIABLE, fallback)

    assert second is fallback, f"{PROFILE_VARIABLE} went from managed to selfhosted between two calls, yet profile_default({SAMPLE_VARIABLE!r}, fallback) still gives {described(second, fallback)}: the profile is read at each call, never kept"
    print_success("✓ managed, then the fallback itself")
