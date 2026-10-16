"""
The profile defaults of the settings (workstream H, platform, checkpoint CP7b-2; developer decisions D5 and F27).

Under test: ``PROFILE_DEFAULTS`` and the validator of ``Settings`` that applies it, both in ``backend/app/config/__init__.py``,
and the two fields D5 adds there. The contract:

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

``Settings`` is built with ``_env_file=None`` after the profile and every listed field are removed from the environment
with ``monkeypatch``, so neither the shell nor the instance's ``.env`` reaches a case. The one case about ``.env`` writes
its own file under ``tmp_path`` and turns test mode off for the call: in test mode ``Settings`` reads no ``.env`` at all
(``settings_customise_sources``). ``PROFILE_DEFAULTS`` is read with ``getattr`` when a test runs, so this file collects
before it exists and each test fails on its own. No DB, no server, no network.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import get_args

import pytest
from pydantic import TypeAdapter, ValidationError
from pydantic.fields import FieldInfo

from backend.app import config
from backend.test_scripts.test_utils import print_section, print_success

PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
#: What LIBREFOLIO_PROFILE accepts today, and so the keys PROFILE_DEFAULTS must have.
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


def _collected_table() -> dict[str, dict[str, object]]:
    """``PROFILE_DEFAULTS`` as it is when this file is collected; empty before it exists."""
    table = getattr(config, "PROFILE_DEFAULTS", None)
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
