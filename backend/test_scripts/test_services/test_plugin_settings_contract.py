"""Plugin settings, the contract: what a plugin declares, the values it accepts, and what the core binds (plan 03, CP10).

Modules under test: ``services/plugin_settings/fields.py`` and ``contract.py``, and the checks at registration in
``services/provider_registry.py``. The contract pinned here, hardened after the security review:

1. **Declarations** (``validate_declaration``), per family (``FAMILY_RULES``): an asset plugin may declare ``user`` fields
   and secrets; an FX plugin only ``system`` fields, secrets included; a family without rules declares nothing. A
   ``user`` field is never ``required``, plain or secret, whatever its default: the calls made for nobody (prices,
   history, scheduled jobs) never receive it, so it would leave them ``NOT_CONFIGURED`` for ever while every user's
   catalogue says «configured»; the same field optional, or required at the ``system`` scope, is accepted. A key is
   lowercase letters, digits and ``_``, a letter first, at most 64 characters, never ending in ``_file`` (that suffix
   belongs to the ``_FILE`` variables), declared once. ``type`` and ``scope`` are the enum values, an English label is
   required. A secret is a string, has no default and accepts at least 8 characters, a floor no declaration lowers. An
   ``env`` alias belongs to a **secret system** field only: ``LIBREFOLIO_`` and uppercase letters, digits and ``_``,
   never ``LIBREFOLIO_PLUGIN_…`` (the derived names) and never ending in ``_FILE``. Only a string has lengths
   (``1 <= min <= max <= 4096``), only a number has bounds (finite, ``minimum <= maximum``), only a select has options
   (distinct, non-empty values, each with a label). A default must be a value the field accepts.
2. **Registration**: a registry refuses a plugin whose declaration fails, like one that does not import; a registry
   whose plugins cannot declare settings (``settings_family() is None``) refuses any declaration; a plugin without
   fields registers anywhere. Right before storing a plugin the registry **claims its variables**
   (``claim_env_variables``): a derived name or an alias another ``(family, plugin_code)`` already claimed — the derived
   names of asset ``foo_bar``/``baz`` and asset ``foo``/``bar_baz`` are one and the same —, or one that appears twice
   in the plugin, refuses the claim and the plugin is not stored. A successful claim replaces the owner's previous
   claims, a refused one changes nothing; ``claimed_env_variables`` hands out a copy and ``release_env_variables``
   drops an owner's claims (the tests' teardown).
3. **Values** (``validate_value``, ``parse_env_value``): one rule per type; booleans from the environment are ``1``,
   ``true``, ``yes``, ``on`` / ``0``, ``false``, ``no``, ``off`` in any case; a secret from the environment is taken as
   written, any other text stripped. **No refusal message ever contains the value** it judged: each case carries a
   unique marker and the message is searched for it.
4. **Environment names**: ``LIBREFOLIO_PLUGIN_<FAMILY>_<CODE>_<FIELD>``, uppercase, every other character ``_``;
   ``env_variables`` (now in ``fields.py``, still importable from ``resolver.py``) lists the derived name and then the
   alias, for a ``system`` field only.
5. **BoundSettings** and the mixin: ``get`` reads plain fields and refuses a secret, ``secret`` reads secrets and
   refuses a plain field, an undeclared key is a ``KeyError``; ``missing``, ``fingerprint``, ``secret_values`` and
   ``plain_values``; the ``repr`` names the secret fields and never shows their values; an unbound instance sees the
   declared defaults and no secret. The test doubles declare what the other suites rely on.

6. **The BRIM family** (W-BS): ``FAMILY_RULES["brim"]`` is the price sources' (personal and instance-wide fields, secrets of
   both scopes); ``BRIMProviderRegistry.settings_family()`` is ``brim`` and ``BRIMProvider`` inherits the mixin, so every
   real BRIM plugin declares nothing and sees the unbound defaults; a BRIM plugin declaring valid fields registers and claims
   ``LIBREFOLIO_PLUGIN_BRIM_<CODE>_<FIELD>`` (and its alias), one whose variable another plugin claimed is refused, a bad
   declaration is refused with its reason; a ``test_only`` one is served in test mode only; the family's title key
   ``pluginSettings.families.brim`` exists in the four catalogues. No real plugin declares a field: the tests use
   ``_brim_settings_lab.SettingsBrimPlugin``, registered for the length of a test and taken out again.

**X-R43** (workstream X): an integer above ``MAX_SAFE_INTEGER`` (2**53 - 1) in absolute value is «too large» for a number
field, judged before its bounds, never an ``OverflowError``; a bound or a default past it is a declaration error. «Red
today» is the state before the cure; a guard passes before and after.

Pure: no database, no server, no network, no environment read. The registries that refuse or store plugins here are
throwaway subclasses with their own storage; every claim a test makes is released at its teardown, and the test proves
the real registries untouched.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import replace

import pytest

from backend.app.services.asset_source_providers.mockprov.plugin import SETTINGS_ECHO_QUERY, MockProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.fx_providers.mockfx.plugin import MockFXFailProvider, MockFXProvider
from backend.app.services.plugin_settings import fields as fields_module
from backend.app.services.plugin_settings import resolver
from backend.app.services.plugin_settings.contract import BoundSettings, PluginSettingsMixin
from backend.app.services.plugin_settings.fields import (
    FAMILY_RULES,
    SECRET_MIN_LENGTH_DEFAULT,
    SECRET_MIN_LENGTH_FLOOR,
    STRING_MAX_LENGTH,
    FamilyRules,
    PluginSettingField,
    SettingOption,
    SettingScope,
    SettingsDeclarationError,
    SettingType,
    SettingValueError,
    claim_env_variables,
    claimed_env_variables,
    env_name,
    env_variables,
    parse_env_value,
    release_env_variables,
    validate_declaration,
    validate_value,
)
from backend.app.services.provider_registry import AbstractPluginRegistry, AbstractProviderRegistry, register_provider
from backend.test_scripts.test_services import _brim_settings_lab as brim_lab
from backend.test_scripts.test_utils import print_section, print_success
from scripts.i18n_catalog import load_catalog

SYSTEM, USER = SettingScope.SYSTEM, SettingScope.USER
STRING, NUMBER, INTEGER, BOOLEAN, SELECT = SettingType.STRING, SettingType.NUMBER, SettingType.INTEGER, SettingType.BOOLEAN, SettingType.SELECT
#: Every plugin code of this module starts with it: the teardown releases the claims of exactly these owners.
LAB = "lab_"
#: The largest integer a double — and the settings page, a JavaScript number — holds with its successor: X-R43's
#: ``fields.MAX_SAFE_INTEGER``, written out here so that the module still imports before the cure.
SAFE_INTEGER = 2**53 - 1
#: What X-R43's refusal of an integer past it says.
TOO_LARGE = "too large"


def _marker(prefix: str = "LFMARK") -> str:
    """A value no message, bound or default of this module can contain by chance."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _shows_digits_of(value: int, text: str) -> bool:
    """Whether ``text`` shows ``value``: its digits whole, or any run of 20 of them (all of them when it has fewer)."""
    digits = str(abs(value))
    width = min(20, len(digits))
    return any(digits[start : start + width] in text for start in range(len(digits) - width + 1))


def _field(key: str = "api_key", type: SettingType = STRING, scope: SettingScope = SYSTEM, **extra) -> PluginSettingField:  # noqa: A002 — mirrors the dataclass field
    return PluginSettingField(key=key, type=type, scope=scope, label=extra.pop("label", f"Label of {key}"), **extra)


def _secret(key: str = "api_key", scope: SettingScope = SYSTEM, **extra) -> PluginSettingField:
    return _field(key, STRING, scope, secret=True, **extra)


def _options(*values: str) -> tuple[SettingOption, ...]:
    return tuple(SettingOption(value, f"Option {value}") for value in values)


def _lab_owners() -> set[tuple[str, str]]:
    return {owner for owner in claimed_env_variables().values() if owner[1].startswith(LAB)}


@pytest.fixture(autouse=True)
def _release_lab_claims():
    """No claim of this module's plugins survives a test, whatever the test did or how it ended."""
    yield
    for family, code in _lab_owners():
        release_env_variables(family, code)


# =============================================================================
# 1. DECLARATIONS
# =============================================================================


def test_every_type_declares_cleanly_for_the_asset_family():
    """1: one field of each type and scope, a secret with an alias among them, passes for ``asset``."""
    print_section("1: a valid asset declaration")
    fields = (
        _secret("api_key", required=True, env="LIBREFOLIO_LAB_API_KEY"),
        _field("region", SELECT, SYSTEM, default="eu", options=_options("eu", "us")),
        _field("tolerance", NUMBER, SYSTEM, default=0.5, minimum=0, maximum=10),
        _field("verbose", BOOLEAN, SYSTEM, default=False),
        _field("limit", INTEGER, USER, default=10, minimum=1, maximum=50),
        _secret("token", USER, min_length=SECRET_MIN_LENGTH_FLOOR),
        _field("note", STRING, USER, default="x", max_length=STRING_MAX_LENGTH),
    )

    validate_declaration(fields, family="asset")
    validate_declaration((), family="asset")
    print_success("seven fields of every kind, and the empty declaration, pass")


def test_the_family_rules_are_the_documented_ones():
    """1: assets and BRIM take user fields and secrets; FX takes secrets but no user field; no other family is open yet.

    Red today (W-BS): ``brim`` has no rules, so a BRIM plugin cannot declare a setting."""
    assert FAMILY_RULES == {"asset": FamilyRules(user_scope=True, secrets=True), "fx": FamilyRules(user_scope=False, secrets=True), "brim": FamilyRules(user_scope=True, secrets=True)}


def test_an_fx_plugin_declares_system_fields_and_secrets_but_no_user_field():
    """1: an FX sync serves every user, so only the instance's values reach an FX provider."""
    print_section("1: the FX family rules")
    validate_declaration((_secret("api_key"), _field("decimals", INTEGER, SYSTEM, default=6, minimum=0, maximum=10)), family="fx")

    with pytest.raises(SettingsDeclarationError, match="'limit'"):
        validate_declaration((_field("limit", INTEGER, USER, default=10),), family="fx")
    print_success("FX: system and secret accepted, a user field refused")


@pytest.mark.parametrize(
    "declared",
    [
        pytest.param(_field("nickname", STRING, USER, required=True, max_length=40), id="a-plain-text"),
        pytest.param(_field("language", SELECT, USER, required=True, default="all", options=_options("all", "it")), id="a-select-with-a-default"),
        pytest.param(_secret("token", USER, required=True), id="a-secret"),
    ],
)
def test_a_personal_field_cannot_be_required(declared: PluginSettingField):
    """1: the calls made for nobody — prices, history, scheduled jobs — never receive a user's values: a required
    personal field would leave them ``NOT_CONFIGURED`` for ever, while every user's catalogue says «configured». Refused,
    plain or secret, a default or not. The controls, so that ``required`` alone is what is refused: the same field
    optional, and the same field required at the instance's scope, declare cleanly."""
    print_section(f"1: a required personal field, {declared.key}")
    assert (declared.scope, declared.required) == (USER, True), "setup: a personal field, required"

    with pytest.raises(SettingsDeclarationError, match=f"field '{declared.key}': a personal field cannot be required"):
        validate_declaration((declared,), family="asset")

    validate_declaration((replace(declared, required=False),), family="asset")
    validate_declaration((replace(declared, scope=SYSTEM),), family="asset")
    print_success(f"{declared.key}: refused when personal and required; optional, or the instance's, accepted")


@pytest.mark.parametrize("family", ["tools", "signal", "risk", "", "ASSET", "BRIM"])
def test_a_family_without_rules_cannot_declare_settings(family):
    """1: only the families of ``FAMILY_RULES`` may declare settings."""
    with pytest.raises(SettingsDeclarationError, match="cannot declare settings"):
        validate_declaration((_field(default="x"),), family=family)


def test_a_family_that_keeps_no_secret_refuses_a_secret_field(monkeypatch):
    """1: the ``secrets`` rule (a Tool calls no external source) refuses a secret, and only a secret."""
    monkeypatch.setitem(FAMILY_RULES, "lab", FamilyRules(user_scope=True, secrets=False))

    validate_declaration((_field("plain", STRING, USER, default="x"),), family="lab")
    with pytest.raises(SettingsDeclarationError, match="'token'"):
        validate_declaration((_secret("token"),), family="lab")


@pytest.mark.parametrize("fields", [pytest.param([_field(default="x")], id="a-list"), pytest.param(_field(default="x"), id="a-bare-field"), pytest.param(({"key": "x"},), id="a-dict-inside"), pytest.param(None, id="none")])
def test_settings_fields_must_be_a_tuple_of_fields(fields):
    """1: ``settings_fields`` is a tuple of ``PluginSettingField``; anything else is refused before a field is read."""
    with pytest.raises(SettingsDeclarationError, match="tuple of PluginSettingField"):
        validate_declaration(fields, family="asset")


@pytest.mark.parametrize(
    "key",
    [
        pytest.param("", id="empty"),
        pytest.param("Api_key", id="uppercase"),
        pytest.param("1key", id="digit-first"),
        pytest.param("_key", id="underscore-first"),
        pytest.param("api-key", id="dash"),
        pytest.param("api key", id="space"),
        pytest.param("a" * 65, id="65-characters"),
    ],
)
def test_a_bad_key_is_refused(key):
    """1: a key is ``[a-z][a-z0-9_]{0,63}``."""
    with pytest.raises(SettingsDeclarationError, match="a key is lowercase letters"):
        validate_declaration((_field(key, default="x"),), family="asset")


@pytest.mark.parametrize("key", ["api_key_file", "token_file", "x_file"])
def test_a_key_ending_in__file_is_refused(key):
    """1: ``<key>_file`` would derive ``…_<KEY>_FILE``, the file variable of the field ``<key>``: refused."""
    with pytest.raises(SettingsDeclarationError, match=f"'{key}'"):
        validate_declaration((_field(key, default="x"),), family="asset")


@pytest.mark.parametrize("key", ["file", "profile", "file_name", "a" * 64])
def test_a_key_that_merely_contains_file_or_is_64_long_is_accepted(key):
    """1: the controls of the two rules above: only the ``_file`` suffix and the 65th character are refused."""
    validate_declaration((_field(key, default="x"),), family="asset")


def test_a_key_declared_twice_is_refused():
    with pytest.raises(SettingsDeclarationError, match="'region' is declared twice"):
        validate_declaration((_field("region", default="a"), _field("region", default="b")), family="asset")


@pytest.mark.parametrize(
    ("type_", "scope"),
    [pytest.param("string", SYSTEM, id="type-as-text"), pytest.param(STRING, "system", id="scope-as-text"), pytest.param(None, SYSTEM, id="no-type")],
)
def test_type_and_scope_must_be_the_enum_values(type_, scope):
    with pytest.raises(SettingsDeclarationError, match="SettingType and SettingScope"):
        validate_declaration((PluginSettingField(key="x", type=type_, scope=scope, label="X"),), family="asset")


@pytest.mark.parametrize("label", ["", "   ", None])
def test_an_english_label_is_required(label):
    with pytest.raises(SettingsDeclarationError, match="an English label is required"):
        validate_declaration((PluginSettingField(key="x", type=STRING, scope=SYSTEM, label=label, default="x"),), family="asset")


@pytest.mark.parametrize(
    ("extra", "rule"),
    [
        pytest.param({"type": INTEGER}, "only a string can be secret", id="integer"),
        pytest.param({"type": BOOLEAN}, "only a string can be secret", id="boolean"),
        pytest.param({"type": SELECT, "options": _options("a")}, "only a string can be secret", id="select"),
        pytest.param({"default": "a-default-secret"}, "a secret has no default", id="with-a-default"),
        pytest.param({"min_length": SECRET_MIN_LENGTH_FLOOR - 1}, f"at least {SECRET_MIN_LENGTH_FLOOR} characters", id="below-the-floor"),
        pytest.param({"min_length": 4}, f"at least {SECRET_MIN_LENGTH_FLOOR} characters", id="the-old-floor-of-4"),
        pytest.param({"min_length": 0}, f"at least {SECRET_MIN_LENGTH_FLOOR} characters", id="zero"),
    ],
)
def test_the_secret_rules(extra, rule):
    """1: a secret is a string without a default, never accepting fewer than 8 characters."""
    declared = PluginSettingField(key="token", type=extra.pop("type", STRING), scope=SYSTEM, label="Token", secret=True, **extra)
    with pytest.raises(SettingsDeclarationError, match=rule):
        validate_declaration((declared,), family="asset")


def test_a_secret_accepts_8_characters_by_default_and_no_declaration_lowers_it():
    """1: the default and the floor are both 8: a short secret would be masked wherever those few characters appear."""
    assert SECRET_MIN_LENGTH_DEFAULT == 8 and SECRET_MIN_LENGTH_FLOOR == 8
    assert _secret().effective_min_length == 8
    assert _secret(min_length=12).effective_min_length == 12
    assert _field(default="x").effective_min_length == 1, "a plain text accepts one character unless it declares otherwise"
    validate_declaration((_secret("a", min_length=SECRET_MIN_LENGTH_FLOOR), _secret("b", min_length=32)), family="asset")


@pytest.mark.parametrize(
    "alias",
    [
        pytest.param("LAB_API_KEY", id="without-the-prefix"),
        pytest.param("librefolio_lab_key", id="lowercase"),
        pytest.param("LIBREFOLIO_", id="prefix-alone"),
        pytest.param("LIBREFOLIO_LAB-KEY", id="dash"),
        pytest.param("LIBREFOLIO_LAB_KEY_FILE", id="ending-in-_FILE"),
        pytest.param("LIBREFOLIO_" + "K" * 101, id="too-long"),
        pytest.param("LIBREFOLIO_PLUGIN_ASSET_LAB_OTHER_KEY", id="reserved-derived-prefix"),
        pytest.param("LIBREFOLIO_PLUGIN_X", id="reserved-prefix-short"),
    ],
)
def test_a_bad_env_alias_is_refused(alias):
    """1: ``LIBREFOLIO_`` + ``[A-Z0-9_]{1,100}``, never ending in ``_FILE``, never in the derived names' ``LIBREFOLIO_PLUGIN_``."""
    with pytest.raises(SettingsDeclarationError, match="'api_key'"):
        validate_declaration((_secret("api_key", env=alias),), family="asset")


@pytest.mark.parametrize(
    "declared",
    [
        pytest.param(_secret("api_key", USER, env="LIBREFOLIO_LAB_API_KEY"), id="user-secret"),
        pytest.param(_field("api_key", STRING, SYSTEM, default="x", env="LIBREFOLIO_LAB_API_KEY"), id="system-plain-text"),
        pytest.param(_field("api_key", SELECT, SYSTEM, default="a", options=_options("a"), env="LIBREFOLIO_LAB_API_KEY"), id="system-select"),
        pytest.param(_field("api_key", INTEGER, SYSTEM, default=1, env="LIBREFOLIO_LAB_API_KEY"), id="system-integer"),
    ],
)
def test_only_a_secret_system_field_has_an_env_alias(declared):
    """1: an alias exists for the keys a hoster already passes under a name of its own; a plain field has its derived name only."""
    with pytest.raises(SettingsDeclarationError, match="'api_key'"):
        validate_declaration((declared,), family="asset")


def test_a_secret_system_field_takes_a_valid_alias():
    validate_declaration((_secret("api_key", env="LIBREFOLIO_LAB_API_KEY"),), family="asset")
    validate_declaration((_secret("api_key", env="LIBREFOLIO_LAB_API_KEY"),), family="fx")


@pytest.mark.parametrize(
    ("declared", "rule"),
    [
        pytest.param(_field("n", INTEGER, min_length=1), "only a string has a length", id="length-on-an-integer"),
        pytest.param(_field("b", BOOLEAN, max_length=4), "only a string has a length", id="length-on-a-boolean"),
        pytest.param(_field("s", STRING, minimum=0), "only a number has bounds", id="bound-on-a-string"),
        pytest.param(_field("s", SELECT, options=_options("a"), maximum=1), "only a number has bounds", id="bound-on-a-select"),
        pytest.param(_field("s", min_length=0), "lengths must satisfy", id="min-length-0"),
        pytest.param(_field("s", max_length=STRING_MAX_LENGTH + 1), "lengths must satisfy", id="max-length-over-4096"),
        pytest.param(_field("s", min_length=5, max_length=4), "lengths must satisfy", id="min-above-max"),
        pytest.param(_field("s", min_length=2.5), "lengths must satisfy", id="fractional-length"),
        pytest.param(_field("n", NUMBER, minimum=math.inf), "bounds are finite numbers", id="infinite-bound"),
        pytest.param(_field("n", NUMBER, maximum=math.nan), "bounds are finite numbers", id="nan-bound"),
        pytest.param(_field("n", INTEGER, minimum=True), "bounds are finite numbers", id="boolean-bound"),
        pytest.param(_field("n", NUMBER, minimum="0"), "bounds are finite numbers", id="text-bound"),
        pytest.param(_field("n", NUMBER, minimum=2, maximum=1), "minimum is above maximum", id="minimum-above-maximum"),
    ],
)
def test_lengths_and_bounds(declared, rule):
    """1: lengths for strings only, ``1 <= min <= max <= 4096``; bounds for numbers only, finite and ordered."""
    with pytest.raises(SettingsDeclarationError, match=rule):
        validate_declaration((declared,), family="asset")


@pytest.mark.parametrize(
    ("options", "rule"),
    [
        pytest.param((), "a select needs a tuple of SettingOption", id="no-option"),
        pytest.param(("a", "b"), "a select needs a tuple of SettingOption", id="plain-strings"),
        pytest.param((SettingOption("a", "A"), "b"), "a select needs a tuple of SettingOption", id="one-plain-string"),
        pytest.param((SettingOption("a", "A"), SettingOption("a", "Again")), "distinct, non-empty strings", id="duplicate-value"),
        pytest.param((SettingOption("", "Empty"),), "distinct, non-empty strings", id="empty-value"),
        pytest.param((SettingOption(1, "One"),), "distinct, non-empty strings", id="non-text-value"),
        pytest.param((SettingOption("a", "  "),), "every option needs an English label", id="blank-label"),
    ],
)
def test_the_options_of_a_select(options, rule):
    with pytest.raises(SettingsDeclarationError, match=rule):
        validate_declaration((_field("choice", SELECT, options=options),), family="asset")


def test_only_a_select_has_options():
    with pytest.raises(SettingsDeclarationError, match="only a select has options"):
        validate_declaration((_field("text", STRING, options=_options("a")),), family="asset")


@pytest.mark.parametrize(
    "declared",
    [
        pytest.param(_field("choice", SELECT, default="c", options=_options("a", "b")), id="select-default-not-an-option"),
        pytest.param(_field("count", INTEGER, default=2.5), id="integer-default-fractional"),
        pytest.param(_field("count", INTEGER, default=11, maximum=10), id="integer-default-above-the-maximum"),
        pytest.param(_field("ratio", NUMBER, default="0.5"), id="number-default-as-text"),
        pytest.param(_field("flag", BOOLEAN, default=1), id="boolean-default-as-1"),
        pytest.param(_field("text", STRING, default="ab", min_length=3), id="text-default-too-short"),
    ],
)
def test_a_default_must_be_a_value_the_field_accepts(declared):
    with pytest.raises(SettingsDeclarationError, match="invalid default"):
        validate_declaration((declared,), family="asset")


# -----------------------------------------------------------------------------
# X-R43: a bound or a default past what a double holds
# -----------------------------------------------------------------------------


def _declaration_refusal(declared: PluginSettingField) -> str:
    """The message of the refusal of a declaration of ``declared`` alone. Any other outcome fails the test, naming it."""
    try:
        validate_declaration((declared,), family="asset")
    except SettingsDeclarationError as refused:
        return str(refused)
    except Exception as error:  # noqa: BLE001 — any other exception is the defect under test
        pytest.fail(f"validate_declaration raised {type(error).__name__} ({error}) for the field {declared.key!r} instead of SettingsDeclarationError (X-R43): a registry passes it on unwrapped, so the plugin's import fails with an error that names neither the plugin nor the field")
    pytest.fail(f"the declaration of the field {declared.key!r} was accepted (X-R43): past {SAFE_INTEGER} in absolute value, the settings page, a JavaScript number, no longer tells an integer from the next")


@pytest.mark.parametrize(
    "declared",
    [
        pytest.param(_field("count", INTEGER, maximum=10**400), id="integer-maximum-of-401-digits"),
        pytest.param(_field("count", INTEGER, minimum=-(10**400)), id="integer-minimum-of-401-digits"),
        pytest.param(_field("ratio", NUMBER, maximum=10**400), id="number-maximum-of-401-digits"),
    ],
)
def test_a_bound_past_the_double_range_is_refused_not_an_overflow(declared: PluginSettingField):
    """Red today (X-R43): ``OverflowError`` — ``math.isfinite`` cannot convert a bound of 401 digits to a double — instead
    of ``SettingsDeclarationError``: a registry passes it on as it is, and the plugin's import fails with «int too large
    to convert to float», naming neither the plugin nor the field.

    Contract: a bound is a finite float or an integer within ``MAX_SAFE_INTEGER``; any other is refused «bounds are
    finite numbers, an integer within 9007199254740991», naming the field."""
    print_section(f"X-R43: a bound of 401 digits on {declared.key}")
    message = _declaration_refusal(declared)

    assert f"field {declared.key!r}: bounds are finite numbers" in message, message
    print_success(message)


@pytest.mark.parametrize(
    "declared",
    [
        pytest.param(_field("count", INTEGER, maximum=2**53), id="integer-maximum-2**53"),
        pytest.param(_field("ratio", NUMBER, minimum=-(2**53)), id="number-minimum-minus-2**53"),
    ],
)
def test_a_bound_just_past_the_safe_limit_is_refused(declared: PluginSettingField):
    """Red today (X-R43): accepted — 2**53 is a finite number — although past ``MAX_SAFE_INTEGER`` the settings page, a
    JavaScript number, no longer tells an integer from the next (2**53 + 1 reads 2**53).

    Contract: refused like any bound past ``MAX_SAFE_INTEGER`` in absolute value: «bounds are finite numbers, an integer
    within 9007199254740991», naming the field."""
    message = _declaration_refusal(declared)

    assert f"field {declared.key!r}: bounds are finite numbers" in message, message


@pytest.mark.parametrize(
    "declared",
    [
        pytest.param(_field("count", INTEGER, minimum=-SAFE_INTEGER, maximum=SAFE_INTEGER, default=SAFE_INTEGER), id="integer-bounds-and-default-at-the-limit"),
        pytest.param(_field("ratio", NUMBER, minimum=-SAFE_INTEGER, maximum=SAFE_INTEGER, default=-SAFE_INTEGER), id="number-bounds-and-default-at-the-limit"),
        pytest.param(_field("ratio", NUMBER, minimum=-1e300, maximum=1e300, default=1e300), id="number-float-bounds-and-default-of-1e300"),
    ],
)
def test_bounds_and_a_default_at_the_safe_limit_declare_cleanly(declared: PluginSettingField):
    """Guard: green today and after (X-R43). ``MAX_SAFE_INTEGER`` of either sign is a valid bound and a valid default; a
    float bound or default is judged by its finiteness only, 1e300 included."""
    validate_declaration((declared,), family="asset")


@pytest.mark.parametrize(
    "declared",
    [
        pytest.param(_field("count", INTEGER, default=10**400), id="integer-default-of-401-digits"),
        pytest.param(_field("ratio", NUMBER, default=-(10**400)), id="number-default-of-401-digits-negative"),
        pytest.param(_field("count", INTEGER, default=2**53), id="integer-default-2**53"),
    ],
)
def test_a_default_past_the_safe_limit_is_an_invalid_default(declared: PluginSettingField):
    """Red today (X-R43): ``OverflowError`` for a default of 401 digits — the default goes through ``validate_value``,
    whose refusals alone are caught — and a default of 2**53 is accepted.

    Contract: ``SettingsDeclarationError`` «invalid default (too large: …)», naming the field, never the value."""
    message = _declaration_refusal(declared)

    assert f"field {declared.key!r}: invalid default ({TOO_LARGE}" in message, message
    assert not _shows_digits_of(declared.default, message), f"the refusal repeats the default: {message!r}"


# =============================================================================
# 2. REGISTRATION AND VARIABLE CLAIMS
# =============================================================================


class _AssetLabRegistry(AbstractProviderRegistry):
    """A throwaway registry of the asset family: its own storage, a folder that does not exist."""

    @classmethod
    def _get_provider_folder(cls) -> str:
        return "plugin_settings_contract_lab_assets"

    @classmethod
    def settings_family(cls) -> str:
        return "asset"


class _FXLabRegistry(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "plugin_settings_contract_lab_fx"

    @classmethod
    def settings_family(cls) -> str:
        return "fx"


class _NoSettingsLabRegistry(AbstractProviderRegistry):
    """A registry whose plugins cannot declare settings (signals, risk, tools)."""

    @classmethod
    def _get_provider_folder(cls) -> str:
        return "plugin_settings_contract_lab_none"


_LAB_REGISTRIES = (_AssetLabRegistry, _FXLabRegistry, _NoSettingsLabRegistry)


@pytest.fixture(autouse=True)
def _empty_lab_registries():
    """Every test starts and ends with the throwaway registries empty and already 'discovered'."""
    for registry in _LAB_REGISTRIES:
        registry._providers = {}
        registry._discovery_done = True
        registry._discovery_errors = ()
    yield
    for registry in _LAB_REGISTRIES:
        registry._providers = {}


def _plugin_class(code: str, fields: tuple) -> type:
    """A plugin class with ``provider_code`` and ``settings_fields``, as a family base would give it."""
    assert code.startswith(LAB), "setup: the teardown releases the claims of the lab_ codes only"
    return type(f"LabPlugin_{code}", (PluginSettingsMixin,), {"provider_code": code, "settings_fields": fields})


def _owned_by(family: str, code: str) -> set[str]:
    return {variable for variable, owner in claimed_env_variables().items() if owner == (family, code)}


def test_the_real_registries_name_their_settings_family():
    """2: the asset registry is ``asset``, the FX registry ``fx``; any other registry declares none yet."""
    assert AssetProviderRegistry.settings_family() == "asset"
    assert FXProviderRegistry.settings_family() == "fx"
    assert AbstractPluginRegistry.settings_family() is None and _NoSettingsLabRegistry.settings_family() is None


@pytest.mark.parametrize(
    ("registry", "fields", "rule"),
    [
        pytest.param(_AssetLabRegistry, (_field("Bad-Key", default="x"),), "a key is lowercase letters", id="asset-bad-key"),
        pytest.param(_AssetLabRegistry, (_secret("token", default="s3cret-default"),), "a secret has no default", id="asset-secret-with-default"),
        pytest.param(_AssetLabRegistry, (_field("limit", INTEGER, USER, default=10), _secret("token", USER, required=True)), "a personal field cannot be required", id="asset-required-personal-field"),
        pytest.param(_FXLabRegistry, (_field("limit", INTEGER, USER, default=1),), "'limit'", id="fx-user-field"),
        pytest.param(_NoSettingsLabRegistry, (_field("key", default="x"),), "cannot declare settings", id="registry-without-family"),
    ],
)
def test_a_registry_refuses_a_plugin_with_a_bad_declaration(registry, fields, rule):
    """2: ``register`` raises ``SettingsDeclarationError`` naming the class; the plugin is not stored and claims nothing."""
    print_section(f"2: {registry.__name__} refuses a bad declaration")
    plugin = _plugin_class("lab_bad", fields)

    with pytest.raises(SettingsDeclarationError, match=rule) as refused:
        registry.register(plugin)

    assert plugin.__qualname__ in str(refused.value), f"the error must name the plugin class: {refused.value}"
    assert registry.get_plugin("lab_bad") is None and registry.list_plugin_codes() == [], "a refused plugin must not be stored"
    assert not _owned_by("asset", "lab_bad") and not _owned_by("fx", "lab_bad"), "a refused plugin must claim no variable"
    print_success(f"refused ({refused.value}), nothing stored, nothing claimed")


def test_the_decorator_refuses_the_same_way():
    """2: ``@register_provider(registry)`` goes through ``register``: the class is never registered."""
    with pytest.raises(SettingsDeclarationError):

        @register_provider(_AssetLabRegistry)
        class _Decorated(PluginSettingsMixin):
            provider_code = "lab_decorated"
            settings_fields = (_field("x", NUMBER, minimum=3, maximum=1),)

    assert _AssetLabRegistry.list_plugin_codes() == []


@pytest.mark.parametrize(
    ("fields", "rule"),
    [
        pytest.param((_field("limit", INTEGER, SYSTEM, default=1, maximum=10**400),), "bounds are finite numbers", id="a-bound-of-401-digits"),
        pytest.param((_field("limit", INTEGER, SYSTEM, default=10**400),), "invalid default", id="a-default-of-401-digits"),
    ],
)
def test_a_registry_refuses_a_number_past_the_safe_limit_like_any_bad_declaration(fields, rule):
    """Red today (X-R43): ``register`` lets the ``OverflowError`` of the finiteness check through as it is («int too
    large to convert to float»): the plugin is not stored, but the discovery log names neither the plugin nor the field.

    Contract: ``SettingsDeclarationError`` naming the class, the field and the rule, as for any bad declaration; the
    plugin is not stored and claims nothing."""
    plugin = _plugin_class("lab_huge", fields)
    try:
        _AssetLabRegistry.register(plugin)
    except SettingsDeclarationError as refused:
        message = str(refused)
    except Exception as error:  # noqa: BLE001 — any other exception is the defect under test
        pytest.fail(f"register raised {type(error).__name__} ({error}) instead of SettingsDeclarationError (X-R43): the discovery log names neither the plugin nor the field")
    else:
        pytest.fail("the plugin was registered with a number past the safe limit in its declaration (X-R43)")

    assert plugin.__qualname__ in message and "field 'limit'" in message and rule in message, message
    assert _AssetLabRegistry.get_plugin("lab_huge") is None and not _owned_by("asset", "lab_huge"), "a refused plugin is not stored and claims nothing"


def test_a_registered_plugin_claims_its_variables_and_one_without_fields_registers_anywhere():
    """2: a valid declaration registers and claims each system field's derived name and alias; a plugin without fields registers even where settings are not supported."""
    good = _plugin_class("lab_good", (_secret("api_key", env="LIBREFOLIO_LAB_GOOD_API_KEY"), _field("region", default="eu"), _field("limit", INTEGER, USER, default=3)))
    plain = _plugin_class("lab_plain", ())

    _AssetLabRegistry.register(good)
    _NoSettingsLabRegistry.register(plain)

    assert _AssetLabRegistry.get_plugin("lab_good") is good
    assert _NoSettingsLabRegistry.get_plugin("lab_plain") is plain
    assert _owned_by("asset", "lab_good") == {"LIBREFOLIO_PLUGIN_ASSET_LAB_GOOD_API_KEY", "LIBREFOLIO_LAB_GOOD_API_KEY", "LIBREFOLIO_PLUGIN_ASSET_LAB_GOOD_REGION"}, "a user field has no variable to claim"
    assert all(owner[1] != "lab_plain" for owner in claimed_env_variables().values())


def test_registering_the_same_plugin_again_keeps_its_claims():
    """2: a second registration of the same class re-claims its own variables: no conflict with itself."""
    plugin = _plugin_class("lab_again", (_field("region", default="eu"),))

    _AssetLabRegistry.register(plugin)
    _AssetLabRegistry.register(plugin)

    assert _AssetLabRegistry.get_plugin("lab_again") is plugin
    assert _owned_by("asset", "lab_again") == {"LIBREFOLIO_PLUGIN_ASSET_LAB_AGAIN_REGION"}


def test_a_registry_refuses_a_plugin_whose_derived_name_another_plugin_claimed():
    """2: asset ``lab_foo_bar``/``baz`` and asset ``lab_foo``/``bar_baz`` derive one variable: the second plugin is not stored."""
    print_section("2: two plugins, one derived variable")
    first = _plugin_class("lab_foo_bar", (_field("baz", default="x"),))
    second = _plugin_class("lab_foo", (_field("bar_baz", default="y"),))
    assert env_name("asset", "lab_foo_bar", "baz") == env_name("asset", "lab_foo", "bar_baz") == "LIBREFOLIO_PLUGIN_ASSET_LAB_FOO_BAR_BAZ", "setup: the collision"

    _AssetLabRegistry.register(first)
    with pytest.raises(SettingsDeclarationError, match="LIBREFOLIO_PLUGIN_ASSET_LAB_FOO_BAR_BAZ"):
        _AssetLabRegistry.register(second)

    assert _AssetLabRegistry.list_plugin_codes() == ["lab_foo_bar"], "the second plugin must not be stored"
    assert claimed_env_variables()["LIBREFOLIO_PLUGIN_ASSET_LAB_FOO_BAR_BAZ"] == ("asset", "lab_foo_bar"), "the first claim stands"
    print_success("the second plugin refused, the first one's claim intact")


def test_a_claim_refuses_a_variable_another_owner_holds_in_any_family():
    """2: an alias is one name for the whole process: an FX plugin cannot take an asset plugin's."""
    claim_env_variables("asset", "lab_owner", (_secret("api_key", env="LIBREFOLIO_LAB_SHARED_KEY"),))

    with pytest.raises(SettingsDeclarationError, match="LIBREFOLIO_LAB_SHARED_KEY"):
        claim_env_variables("fx", "lab_rival", (_secret("token", env="LIBREFOLIO_LAB_SHARED_KEY"),))

    assert claimed_env_variables()["LIBREFOLIO_LAB_SHARED_KEY"] == ("asset", "lab_owner")
    assert not _owned_by("fx", "lab_rival"), "a refused claim claims nothing"


def test_the_same_code_in_two_families_derives_distinct_names():
    """2: the family is part of the derived name: asset ``lab_twin`` and FX ``lab_twin`` coexist."""
    claim_env_variables("asset", "lab_twin", (_field("region", default="eu"),))
    claim_env_variables("fx", "lab_twin", (_field("region", default="eu"),))

    assert _owned_by("asset", "lab_twin") == {"LIBREFOLIO_PLUGIN_ASSET_LAB_TWIN_REGION"}
    assert _owned_by("fx", "lab_twin") == {"LIBREFOLIO_PLUGIN_FX_LAB_TWIN_REGION"}


def test_a_variable_twice_in_one_plugin_is_refused():
    """2: two secrets of one plugin with one alias: the declaration is refused, and so is the claim, which keeps nothing."""
    fields = (_secret("api_key", env="LIBREFOLIO_LAB_TWICE"), _secret("token", env="LIBREFOLIO_LAB_TWICE"))

    with pytest.raises(SettingsDeclarationError, match="two fields declare the same env alias"):
        validate_declaration(fields, family="asset")
    with pytest.raises(SettingsDeclarationError, match="two fields read the same environment variable"):
        claim_env_variables("asset", "lab_twice", fields)

    assert not _owned_by("asset", "lab_twice")


def test_a_successful_claim_replaces_the_owners_previous_ones_and_a_refused_one_changes_nothing():
    """2: the claim of a reloaded plugin is its new declaration; a refusal keeps the old one in place."""
    claim_env_variables("asset", "lab_reload", (_field("old_key", default="x"),))
    claim_env_variables("asset", "lab_reload", (_field("new_key", default="x"),))
    assert _owned_by("asset", "lab_reload") == {"LIBREFOLIO_PLUGIN_ASSET_LAB_RELOAD_NEW_KEY"}

    claim_env_variables("asset", "lab_holder", (_secret("api_key", env="LIBREFOLIO_LAB_HELD"),))
    with pytest.raises(SettingsDeclarationError):
        claim_env_variables("asset", "lab_reload", (_field("third_key", default="x"), _secret("api_key", env="LIBREFOLIO_LAB_HELD")))

    assert _owned_by("asset", "lab_reload") == {"LIBREFOLIO_PLUGIN_ASSET_LAB_RELOAD_NEW_KEY"}, "a refused claim must leave the owner's claims as they were"


def test_claimed_variables_are_a_copy_and_release_drops_one_owner_only():
    claim_env_variables("asset", "lab_kept", (_field("region", default="eu"),))
    claim_env_variables("asset", "lab_dropped", (_field("region", default="eu"),))

    copy = claimed_env_variables()
    copy.clear()
    assert _owned_by("asset", "lab_kept"), "clearing the copy must not touch the claims"

    release_env_variables("asset", "lab_dropped")
    assert not _owned_by("asset", "lab_dropped") and _owned_by("asset", "lab_kept") == {"LIBREFOLIO_PLUGIN_ASSET_LAB_KEPT_REGION"}
    release_env_variables("asset", "lab_never_claimed")


def test_the_real_registries_are_left_untouched():
    """2: the throwaway registries have their own storage: none of their codes reaches the real registries."""
    _AssetLabRegistry.register(_plugin_class("lab_isolated", (_field("key", default="x"),)))

    assert AssetProviderRegistry.get_plugin("lab_isolated") is None
    assert FXProviderRegistry.get_plugin("lab_isolated") is None
    assert "lab_isolated" not in AssetProviderRegistry.list_plugin_codes()


# =============================================================================
# 3. VALUES
# =============================================================================


def _refusal(declared: PluginSettingField, value: object) -> str:
    """The message of the refusal of ``value``: the test fails if the value is accepted."""
    with pytest.raises(SettingValueError) as refused:
        validate_value(declared, value)
    return str(refused.value)


@pytest.mark.parametrize(
    ("declared", "value"),
    [
        pytest.param(_field("text", default="x"), "plain text", id="string"),
        pytest.param(_field("text", default="x"), "x", id="string-of-one-character"),
        pytest.param(_secret("token"), "12345678", id="secret-of-8"),
        pytest.param(_secret("token"), "pässwörd with spaces ✓", id="secret-unicode-and-spaces"),
        pytest.param(_field("choice", SELECT, options=_options("eu", "us")), "us", id="select"),
        pytest.param(_field("flag", BOOLEAN), True, id="true"),
        pytest.param(_field("flag", BOOLEAN), False, id="false"),
        pytest.param(_field("ratio", NUMBER, minimum=0, maximum=10), 0, id="number-at-the-minimum"),
        pytest.param(_field("ratio", NUMBER, minimum=0, maximum=10), 10.0, id="number-at-the-maximum"),
        pytest.param(_field("ratio", NUMBER), 1.25, id="number-unbounded"),
        pytest.param(_field("count", INTEGER, minimum=1, maximum=50), 50, id="integer-at-the-maximum"),
    ],
)
def test_a_value_the_field_accepts_comes_back_as_it_is(declared, value):
    assert validate_value(declared, value) == value


@pytest.mark.parametrize(
    ("declared", "value", "reason"),
    [
        pytest.param(_field("text", default="x"), 12345, "expected text", id="string-given-a-number"),
        pytest.param(_field("text", default="x", min_length=3), "ab", "too short: at least 3", id="string-too-short"),
        pytest.param(_field("text", default="x", max_length=4), "abcde", "too long: at most 4", id="string-too-long"),
        pytest.param(_field("text", default="x"), "", "too short: at least 1", id="string-empty"),
        pytest.param(_field("text", default="x"), "line\nbreak", "control characters", id="string-newline"),
        pytest.param(_field("text", default="x"), "tab\there", "control characters", id="string-tab"),
        pytest.param(_field("text", default="x"), "nul\x00", "control characters", id="string-nul"),
        pytest.param(_field("text", default="x"), "del\x7f", "control characters", id="string-del"),
        pytest.param(_secret("token"), "1234567", "too short: at least 8", id="secret-of-7"),
        pytest.param(_field("choice", SELECT, options=_options("eu")), "de", "not one of the options", id="select-other-value"),
        pytest.param(_field("choice", SELECT, options=_options("eu")), 1, "expected text", id="select-given-a-number"),
        pytest.param(_field("flag", BOOLEAN), 1, "expected true or false", id="boolean-given-1"),
        pytest.param(_field("flag", BOOLEAN), "true", "expected true or false", id="boolean-given-text"),
        pytest.param(_field("flag", BOOLEAN), None, "expected true or false", id="boolean-given-none"),
        pytest.param(_field("ratio", NUMBER), True, "expected a number", id="number-given-a-boolean"),
        pytest.param(_field("ratio", NUMBER), "1.5", "expected a number", id="number-given-text"),
        pytest.param(_field("ratio", NUMBER), math.nan, "expected a finite number", id="number-nan"),
        pytest.param(_field("ratio", NUMBER), -math.inf, "expected a finite number", id="number-minus-infinity"),
        pytest.param(_field("ratio", NUMBER, minimum=0.5), 0.25, "below the minimum of 0.5", id="number-below"),
        pytest.param(_field("ratio", NUMBER, maximum=10), 10.5, "above the maximum of 10", id="number-above"),
        pytest.param(_field("count", INTEGER), 3.0, "expected a whole number", id="integer-given-3.0"),
        pytest.param(_field("count", INTEGER), False, "expected a number", id="integer-given-a-boolean"),
        pytest.param(_field("count", INTEGER, minimum=1), 0, "below the minimum of 1", id="integer-below"),
        pytest.param(_field("count", INTEGER, maximum=50), 51, "above the maximum of 50", id="integer-above"),
    ],
)
def test_a_value_the_field_refuses_gets_a_reason(declared, value, reason):
    """3: each type refuses with a reason: the declared bound, never the value."""
    assert reason in _refusal(declared, value)


@pytest.mark.parametrize(
    ("declared", "build"),
    [
        pytest.param(_field("text", default="x", max_length=20), lambda marker: marker + "x" * 30, id="too-long"),
        pytest.param(_field("text", default="x"), lambda marker: marker + "\n", id="control-character"),
        pytest.param(_secret("token", min_length=40), lambda marker: marker, id="secret-too-short"),
        pytest.param(_field("choice", SELECT, options=_options("eu")), lambda marker: marker, id="select"),
        pytest.param(_field("flag", BOOLEAN), lambda marker: marker, id="boolean"),
        pytest.param(_field("ratio", NUMBER), lambda marker: marker, id="number-given-text"),
    ],
)
def test_a_refusal_never_contains_the_value(declared, build):
    """3: a 422 or a log line built from the message must never carry a secret back."""
    marker = _marker()
    message = _refusal(declared, build(marker))
    assert marker not in message, f"the refusal repeats the value: {message!r}"


def test_a_refused_number_is_not_in_its_message():
    """3: a number out of bounds is named by its bound only."""
    assert "987654.321" not in _refusal(_field("ratio", NUMBER, maximum=10), 987654.321)
    assert "8642" not in _refusal(_field("count", INTEGER, minimum=10000), 8642)


# -----------------------------------------------------------------------------
# X-R43: an integer past what a double holds
# -----------------------------------------------------------------------------

#: A number field of each type without bounds: whatever refuses an integer there is not a bound.
_UNBOUNDED = [pytest.param(_field("count", INTEGER), id="integer"), pytest.param(_field("ratio", NUMBER), id="number")]


def _too_large(declared: PluginSettingField, value: int) -> str:
    """The message of the refusal of ``value``. Any other outcome fails the test, naming it: an exception that is no
    ``SettingValueError`` (a write of it answers 500, a variable or a row holding it breaks its plugin), or the value accepted."""
    digits = len(str(abs(value)))
    try:
        accepted = validate_value(declared, value)
    except SettingValueError as refused:
        return str(refused)
    except Exception as error:  # noqa: BLE001 — any other exception is the defect under test
        pytest.fail(
            f"validate_value raised {type(error).__name__} ({error}) for an integer of {digits} digits on the {declared.type.value} field {declared.key!r}, instead of SettingValueError «too large» (X-R43): "
            "a write of it answers 500, and a variable or a stored row holding it makes the resolution of its plugin raise"
        )
    pytest.fail(
        f"validate_value accepted an integer of {digits} digits on the {declared.type.value} field {declared.key!r} (it returned a {type(accepted).__name__}), instead of refusing it «too large» (X-R43): "
        f"past {SAFE_INTEGER} the settings page, a JavaScript number, no longer tells an integer from the next"
    )


@pytest.mark.parametrize("value", [pytest.param(10**400, id="10**400"), pytest.param(-(10**400), id="minus-10**400")])
@pytest.mark.parametrize("declared", _UNBOUNDED)
def test_an_integer_past_the_double_range_is_too_large_not_an_overflow(declared: PluginSettingField, value: int):
    """Red today (X-R43): ``OverflowError`` — ``math.isfinite`` cannot convert an integer of 401 digits to a double (the
    range ends near 309 digits) — and nobody catches it: a member's write of it answers 500, and a variable or a stored
    row holding it makes the resolution of its plugin raise.

    Contract: ``SettingValueError`` «too large: at most 9007199254740991 in absolute value», on an integer field and a
    number field alike: the limit named, the value never."""
    print_section(f"X-R43: the {declared.type.value} field given {'minus ' if value < 0 else ''}10**400")
    message = _too_large(declared, value)

    assert TOO_LARGE in message and str(SAFE_INTEGER) in message, f"the refusal says {message!r}: expected «too large», naming the limit {SAFE_INTEGER}"
    assert not _shows_digits_of(value, message), f"the refusal repeats the value: {message!r}"
    print_success(message)


@pytest.mark.parametrize("value", [pytest.param(2**53, id="2**53"), pytest.param(-(2**53), id="minus-2**53")])
@pytest.mark.parametrize("declared", _UNBOUNDED)
def test_the_first_integer_past_the_safe_limit_is_too_large(declared: PluginSettingField, value: int):
    """Red today (X-R43): accepted and returned as it is — 2**53 is well inside the double range, so no check refuses
    it — although past ``MAX_SAFE_INTEGER`` the settings page, a JavaScript number, no longer tells an integer from the
    next (2**53 + 1 reads 2**53).

    Contract: «too large», as any integer above ``MAX_SAFE_INTEGER`` in absolute value, on both types; the message holds
    the limit, 9007199254740991, never the value, 9007199254740992."""
    message = _too_large(declared, value)

    assert TOO_LARGE in message, f"the refusal says {message!r}: expected «too large»"
    assert not _shows_digits_of(value, message), f"the refusal repeats the value: {message!r}"


@pytest.mark.parametrize(
    ("declared", "value", "bound"),
    [
        pytest.param(_field("count", INTEGER, minimum=1, maximum=50), 10**400, "above the maximum", id="integer-1-to-50-given-10**400"),
        pytest.param(_field("count", INTEGER, minimum=1, maximum=50), -(10**400), "below the minimum", id="integer-1-to-50-given-minus-10**400"),
        pytest.param(_field("ratio", NUMBER, minimum=0, maximum=10), 2**53, "above the maximum", id="number-0-to-10-given-2**53"),
    ],
)
def test_on_a_bounded_field_too_large_is_judged_before_the_bounds(declared: PluginSettingField, value: int, bound: str):
    """Red today (X-R43): ``OverflowError`` for the integers of 401 digits — the finiteness check comes before the
    bounds —; 2**53 on a number field of maximum 10 is refused «above the maximum of 10».

    Contract: «too large» is judged before the bounds: the user learns that the number cannot be held at all, not that
    it passes a bound."""
    message = _too_large(declared, value)

    assert TOO_LARGE in message and bound not in message, f"the refusal says {message!r}: expected «too large», judged before the bounds"


@pytest.mark.parametrize("value", [pytest.param(SAFE_INTEGER, id="2**53-1"), pytest.param(-SAFE_INTEGER, id="minus-2**53-1")])
@pytest.mark.parametrize("declared", _UNBOUNDED)
def test_the_largest_safe_integer_is_accepted_as_it_is(declared: PluginSettingField, value: int):
    """Guard: green today and after (X-R43). ``MAX_SAFE_INTEGER`` itself, of either sign, comes back unchanged — the very
    int — on an integer field and a number field without bounds."""
    accepted = validate_value(declared, value)

    assert accepted == value and type(accepted) is int, f"{value} came back as {accepted!r}"


def test_a_float_is_judged_by_its_finiteness_only():
    """Guard: green today and after (X-R43). 1e300, a finite float far past 2**53, is accepted as it is by a number
    field without bounds; on an integer field it is «expected a whole number», never «too large»."""
    assert validate_value(_field("ratio", NUMBER), 1e300) == 1e300
    message = _refusal(_field("count", INTEGER), 1e300)
    assert "expected a whole number" in message and TOO_LARGE not in message, message


@pytest.mark.parametrize(
    ("declared", "value", "reason"),
    [
        pytest.param(_field("ratio", NUMBER), math.inf, "expected a finite number", id="number-inf"),
        pytest.param(_field("ratio", NUMBER), -math.inf, "expected a finite number", id="number-minus-inf"),
        pytest.param(_field("ratio", NUMBER), math.nan, "expected a finite number", id="number-nan"),
        pytest.param(_field("ratio", NUMBER), True, "expected a number", id="number-given-true"),
        pytest.param(_field("count", INTEGER), True, "expected a number", id="integer-given-true"),
    ],
)
def test_the_checks_before_too_large_keep_their_reasons(declared: PluginSettingField, value: object, reason: str):
    """Guard: green today and after (X-R43). The type and finiteness checks come first and keep their reasons: a
    boolean — an int to Python — is «expected a number», an infinite or NaN float «expected a finite number»."""
    message = _refusal(declared, value)

    assert reason in message and TOO_LARGE not in message, message


def test_fields_publishes_the_safe_limit():
    """Red today (X-R43): ``fields`` has no ``MAX_SAFE_INTEGER``.

    Contract: ``fields.MAX_SAFE_INTEGER`` is 2**53 - 1, 9007199254740991, the limit of every number field, bound and
    default. Read when the test runs, so that before the cure this test alone fails on the name."""
    assert getattr(fields_module, "MAX_SAFE_INTEGER", None) == SAFE_INTEGER == 9007199254740991, "fields.MAX_SAFE_INTEGER must be 2**53 - 1 (X-R43)"


@pytest.mark.parametrize(
    ("text", "expected"),
    [*(pytest.param(word, True, id=f"{word!r}-is-true") for word in ("1", "true", "TRUE", "Yes", "on", " on ")), *(pytest.param(word, False, id=f"{word!r}-is-false") for word in ("0", "false", "False", "NO", "off", "\toff\n"))],
)
def test_a_boolean_from_the_environment(text, expected):
    """3: ``1``, ``true``, ``yes``, ``on`` and ``0``, ``false``, ``no``, ``off``, in any case, stripped."""
    assert parse_env_value(_field("flag", BOOLEAN), text) is expected


@pytest.mark.parametrize("text", ["", "2", "y", "enabled", "truthy"])
def test_any_other_boolean_word_is_refused(text):
    with pytest.raises(SettingValueError, match="expected 1, true, yes, on or 0, false, no, off"):
        parse_env_value(_field("flag", BOOLEAN), text)


@pytest.mark.parametrize(
    ("declared", "text", "expected"),
    [
        pytest.param(_field("ratio", NUMBER), " 1.5 ", 1.5, id="number-stripped"),
        pytest.param(_field("ratio", NUMBER), "1e1", 10.0, id="number-exponent"),
        pytest.param(_field("ratio", NUMBER), "3", 3.0, id="number-from-a-whole-text"),
        pytest.param(_field("count", INTEGER, minimum=1), " 7 ", 7, id="integer-stripped"),
        pytest.param(_field("choice", SELECT, options=_options("it", "en")), " it ", "it", id="select-stripped"),
        pytest.param(_field("text", default="x"), "  padded  ", "padded", id="text-stripped"),
        pytest.param(_secret("token"), "  s3cret with spaces  ", "  s3cret with spaces  ", id="secret-as-written"),
    ],
)
def test_a_value_from_the_environment(declared, text, expected):
    """3: numbers, selects and plain text are stripped; a secret is taken as written."""
    parsed = parse_env_value(declared, text)
    assert parsed == expected and type(parsed) is type(expected)


@pytest.mark.parametrize(
    ("declared", "text", "reason"),
    [
        pytest.param(_field("ratio", NUMBER), "abc", "expected a number", id="number-not-a-number"),
        pytest.param(_field("ratio", NUMBER), "nan", "expected a finite number", id="number-nan"),
        pytest.param(_field("ratio", NUMBER), "inf", "expected a finite number", id="number-inf"),
        pytest.param(_field("count", INTEGER), "7.0", "expected a whole number", id="integer-7.0"),
        pytest.param(_field("count", INTEGER, maximum=5), "6", "above the maximum of 5", id="integer-above"),
        pytest.param(_field("choice", SELECT, options=_options("it")), "de", "not one of the options", id="select-other"),
        pytest.param(_field("text", default="x"), "   ", "too short", id="text-blank"),
    ],
)
def test_a_refused_environment_value(declared, text, reason):
    with pytest.raises(SettingValueError, match=reason):
        parse_env_value(declared, text)


@pytest.mark.parametrize(
    "declared",
    [
        pytest.param(_field("ratio", NUMBER), id="number"),
        pytest.param(_field("count", INTEGER), id="integer"),
        pytest.param(_field("flag", BOOLEAN), id="boolean"),
        pytest.param(_field("choice", SELECT, options=_options("it")), id="select"),
        pytest.param(_secret("token", min_length=64), id="secret"),
    ],
)
def test_an_environment_refusal_never_contains_the_value(declared):
    marker = _marker()
    with pytest.raises(SettingValueError) as refused:
        parse_env_value(declared, marker)
    assert marker not in str(refused.value), f"the refusal repeats the variable's value: {refused.value}"


# =============================================================================
# 4. ENVIRONMENT NAMES
# =============================================================================


@pytest.mark.parametrize(
    ("family", "code", "key", "expected"),
    [
        pytest.param("asset", "borsa_italiana", "api_key", "LIBREFOLIO_PLUGIN_ASSET_BORSA_ITALIANA_API_KEY", id="documented-example"),
        pytest.param("fx", "MOCKFX", "decimals", "LIBREFOLIO_PLUGIN_FX_MOCKFX_DECIMALS", id="fx-uppercase-code"),
        pytest.param("asset", "my-provider.v2", "key", "LIBREFOLIO_PLUGIN_ASSET_MY_PROVIDER_V2_KEY", id="dash-and-dot"),
        pytest.param("asset", "mockprov", "price_tolerance", "LIBREFOLIO_PLUGIN_ASSET_MOCKPROV_PRICE_TOLERANCE", id="mockprov"),
    ],
)
def test_the_derived_variable_name(family, code, key, expected):
    """4: ``LIBREFOLIO_PLUGIN_<FAMILY>_<CODE>_<FIELD>``, uppercase, every non-alphanumeric character ``_``."""
    assert env_name(family, code, key) == expected


def test_env_variables_lists_the_derived_name_then_the_alias_for_a_system_field_only():
    """4: the order in which they are read; nothing for a user field."""
    derived = "LIBREFOLIO_PLUGIN_ASSET_LAB_KEY"
    assert env_variables("asset", "lab", _field("key", default="x")) == (derived,)
    assert env_variables("asset", "lab", _secret("key", env="LIBREFOLIO_LAB_KEY")) == (derived, "LIBREFOLIO_LAB_KEY")
    assert env_variables("asset", "lab", _field("key", STRING, USER, default="x")) == ()
    assert env_variables("asset", "lab", _secret("key", USER)) == ()


def test_env_variables_moved_to_fields_and_the_old_import_still_works():
    """4: ``fields.env_variables`` is the one function; ``resolver.env_variables`` names the same object."""
    assert resolver.env_variables is env_variables


def test_the_mockprov_secret_has_its_derived_name_and_its_alias():
    api_key = next(declared for declared in MockProvider.settings_fields if declared.key == "api_key")
    assert env_variables("asset", "mockprov", api_key) == ("LIBREFOLIO_PLUGIN_ASSET_MOCKPROV_API_KEY", "LIBREFOLIO_MOCKPROV_API_KEY")


# =============================================================================
# 5. BOUND SETTINGS AND THE MIXIN
# =============================================================================

_BOUND_FIELDS = (
    _secret("api_key", required=True),
    _field("region", SELECT, default="eu", options=_options("eu", "us")),
    _field("limit", INTEGER, USER, default=10, minimum=1),
    _field("endpoint", required=True),
    _secret("token", USER),
)


def test_get_reads_a_plain_field_and_refuses_a_secret_or_an_undeclared_key():
    bound = BoundSettings(_BOUND_FIELDS, {"region": "us"}, {"api_key": "s3cret-value"})

    assert bound.get("region") == "us"
    assert bound.get("limit") is None and bound.get("limit", 7) == 7, "a plain field without a value gives the default argument"
    with pytest.raises(KeyError, match="settings.secret"):
        bound.get("api_key")
    with pytest.raises(KeyError, match="not a declared setting"):
        bound.get("undeclared")


def test_secret_reads_a_secret_and_refuses_a_plain_field_or_an_undeclared_key():
    bound = BoundSettings(_BOUND_FIELDS, {"region": "us"}, {"api_key": "s3cret-value"})

    assert bound.secret("api_key") == "s3cret-value"
    assert bound.secret("token") is None
    with pytest.raises(KeyError, match="settings.get"):
        bound.secret("region")
    with pytest.raises(KeyError, match="not a declared setting"):
        bound.secret("undeclared")


def test_missing_fingerprint_and_the_value_views():
    """5: ``missing`` and ``fingerprint`` as bound; ``secret_values`` skips the empty ones; ``plain_values`` is a copy."""
    bound = BoundSettings(_BOUND_FIELDS, {"region": "us"}, {"api_key": "s3cret-value", "token": ""}, ("endpoint",), fingerprint="f" * 32)

    assert bound.missing == ("endpoint",)
    assert bound.fingerprint == "f" * 32
    assert bound.secret_values() == frozenset({"s3cret-value"})
    copy = bound.plain_values()
    copy["region"] = "changed"
    assert bound.get("region") == "us", "plain_values must hand out a copy"
    assert BoundSettings(_BOUND_FIELDS, {}, {}).fingerprint == "", "nothing fingerprinted: the empty string"


def test_the_repr_names_the_secrets_and_never_shows_them():
    """5: a log line or a traceback that prints the settings never shows a secret."""
    marker = _marker("SECRET")
    bound = BoundSettings(_BOUND_FIELDS, {"region": "us"}, {"api_key": marker, "token": marker + "-2"})

    text = repr(bound)
    assert marker not in text, f"the repr shows a secret: {text}"
    assert "api_key" in text and "token" in text and "'region': 'us'" in text


def test_an_unbound_instance_sees_the_defaults_and_no_secret():
    """5: ``BoundSettings.unbound``: each plain default, no secret, the required fields without a default as missing."""
    unbound = BoundSettings.unbound(_BOUND_FIELDS)

    assert unbound.plain_values() == {"region": "eu", "limit": 10}
    assert unbound.secret_values() == frozenset() and unbound.secret("api_key") is None
    assert unbound.missing == ("api_key", "endpoint")
    assert unbound.fingerprint == ""


def test_the_mixin_gives_defaults_until_the_core_binds_values():
    """5: ``settings`` is the unbound view until ``bind_settings``; a binding belongs to its instance only."""
    plugin_class = _plugin_class("lab_mixin", _BOUND_FIELDS)
    configured, other = plugin_class(), plugin_class()
    bound = BoundSettings(_BOUND_FIELDS, {"region": "us"}, {"api_key": "s3cret-value"}, fingerprint="abc")

    assert configured.settings.get("region") == "eu" and configured.settings.fingerprint == ""
    configured.bind_settings(bound)

    assert configured.settings is bound
    assert other.settings.get("region") == "eu" and other.settings.secret("api_key") is None, "binding one instance must not reach another"
    assert PluginSettingsMixin.settings_fields == () and PluginSettingsMixin.test_only is False


# -----------------------------------------------------------------------------
# The test doubles the other suites rely on
# -----------------------------------------------------------------------------


def test_mockprov_declares_one_field_of_every_kind():
    """5: ``mockprov`` is test-only and declares the seven fields the service and API suites write."""
    shape = [(declared.key, declared.type, declared.scope, declared.secret, declared.default, declared.env) for declared in MockProvider.settings_fields]

    assert MockProvider.test_only is True
    assert shape == [
        ("api_key", STRING, SYSTEM, True, None, "LIBREFOLIO_MOCKPROV_API_KEY"),
        ("region", SELECT, SYSTEM, False, "eu", None),
        ("price_tolerance", NUMBER, SYSTEM, False, 0.5, None),
        ("verbose", BOOLEAN, SYSTEM, False, False, None),
        ("preferred_language", SELECT, USER, False, "all", None),
        ("results_limit", INTEGER, USER, False, 10, None),
        ("personal_token", STRING, USER, True, None, None),
    ]
    assert SETTINGS_ECHO_QUERY == "lf-settings-echo"
    validate_declaration(MockProvider.settings_fields, family="asset")


def test_the_fx_doubles_are_test_only_and_mockfx_declares_two_system_fields():
    shape = [(declared.key, declared.type, declared.scope, declared.secret, declared.default) for declared in MockFXProvider.settings_fields]

    assert MockFXProvider.test_only is True and MockFXFailProvider.test_only is True
    assert shape == [("api_key", STRING, SYSTEM, True, None), ("decimals", INTEGER, SYSTEM, False, 6)]
    assert MockFXFailProvider.settings_fields == ()
    assert not any(declared.required for declared in MockFXProvider.settings_fields), "MOCKFX must stay callable without settings: the FX suites call it"
    validate_declaration(MockFXProvider.settings_fields, family="fx")


# =============================================================================
# 6. THE BRIM FAMILY (W-BS): the price sources' rules; no real plugin declares a field yet
# =============================================================================

BRIM_CODE = brim_lab.CODE
BRIM_DERIVED = {env_name("brim", BRIM_CODE, key) for key in ("region", "api_key")}


def _brim_registered_in_test_mode(monkeypatch: pytest.MonkeyPatch):
    """The lab BRIM plugin registered in the real registry, which serves a ``test_only`` plugin in test mode only."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    return brim_lab.registered_settings_brim()


def test_a_brim_plugin_declares_every_kind_of_field():
    """6: a personal select, a personal secret, an instance select with a default, an instance secret with an alias — and
    none at all — pass for ``brim``; the lab plugin's own declaration is valid."""
    print_section("6: a valid BRIM declaration")
    validate_declaration(brim_lab.SETTINGS_FIELDS, family="brim")
    validate_declaration((), family="brim")
    validate_declaration((_field("limit", INTEGER, USER, default=10, minimum=1, maximum=50), _secret("token", USER), _secret("api_key", env="LIBREFOLIO_LAB_BRIM_API_KEY")), family="brim")
    print_success("BRIM takes user fields, system fields and secrets of both scopes")


def test_brim_applies_the_rules_of_the_price_sources():
    """6: the same refusals as for ``asset``: a required personal field, a secret with a default, a secret under 8
    characters, a user field with an alias."""
    assert FAMILY_RULES.get("brim") == FAMILY_RULES["asset"], "BRIM has the price sources' rules"
    with pytest.raises(SettingsDeclarationError, match="a personal field cannot be required"):
        validate_declaration((_field("nickname", STRING, USER, required=True),), family="brim")
    with pytest.raises(SettingsDeclarationError, match="a secret has no default"):
        validate_declaration((_secret("token", default="s3cret-default"),), family="brim")
    with pytest.raises(SettingsDeclarationError, match="a secret accepts at least 8 characters"):
        validate_declaration((_secret("token", min_length=4),), family="brim")
    with pytest.raises(SettingsDeclarationError, match="only a secret system field has an env alias"):
        validate_declaration((_field("region", STRING, USER, default="eu", env="LIBREFOLIO_LAB_BRIM_REGION"),), family="brim")


def test_the_brim_registry_names_its_settings_family():
    assert BRIMProviderRegistry.settings_family() == "brim"


def test_the_brim_base_inherits_the_settings_mixin_with_no_field_and_not_test_only():
    """6: ``BRIMProvider`` is a plugin base like the other two: the mixin, no field, never ``test_only``."""
    assert issubclass(BRIMProvider, PluginSettingsMixin)
    assert BRIMProvider.settings_fields == () and BRIMProvider.test_only is False


def test_every_real_brim_plugin_declares_nothing_and_sees_the_unbound_defaults():
    """6: no real BRIM plugin declares a field (so none is ever in the catalogue); each one's ``settings`` is the
    unbound view: no value, no secret, nothing missing, an empty fingerprint."""
    BRIMProviderRegistry.auto_discover()
    codes = BRIMProviderRegistry.list_plugin_codes()
    assert codes, "barrier: the BRIM registry holds plugins"

    declaring = {code: BRIMProviderRegistry.get_plugin(code).settings_fields for code in codes if BRIMProviderRegistry.get_plugin(code).settings_fields}
    assert declaring == {}, f"a real BRIM plugin declares settings: no concrete field is declared in this lot: {sorted(declaring)}"
    for code in codes:
        unbound = BRIMProviderRegistry.get_provider_instance(code).settings
        assert (unbound.plain_values(), unbound.secret_values(), unbound.missing, unbound.fingerprint) == ({}, frozenset(), (), ""), code


def test_a_brim_plugin_sees_its_defaults_and_no_secret_until_the_core_binds_values():
    """6: ``settings`` is the unbound view (declared defaults, no secret) until ``bind_settings``; the binding belongs to
    one instance, and a secret reads only through ``secret()``."""
    plugin, other = brim_lab.SettingsBrimPlugin(), brim_lab.SettingsBrimPlugin()
    secret = _marker("SECRET")
    bound = BoundSettings(brim_lab.SETTINGS_FIELDS, {"region": "us", "statement_language": "it"}, {"api_key": secret, "personal_token": secret + "-2"})

    assert (plugin.settings.get("region"), plugin.settings.get("statement_language")) == ("eu", "all")
    assert plugin.settings.secret("api_key") is None and plugin.settings.secret("personal_token") is None
    plugin.bind_settings(bound)

    assert plugin.settings is bound and (bound.get("region"), bound.secret("api_key")) == ("us", secret)
    assert other.settings.get("region") == "eu" and other.settings.secret("api_key") is None, "binding one instance must not reach another"
    with pytest.raises(KeyError, match="settings.secret"):
        plugin.settings.get("api_key")


def test_a_brim_plugin_with_valid_fields_registers_and_claims_its_variables(monkeypatch: pytest.MonkeyPatch):
    """6: ``register`` accepts the declaration and claims each system field's derived name
    ``LIBREFOLIO_PLUGIN_BRIM_<CODE>_<FIELD>`` and the alias, none for a personal field; out again, the claims are released."""
    print_section("6: a BRIM plugin registers")
    assert BRIMProviderRegistry.get_plugin(BRIM_CODE) is None, "barrier: not registered before"

    with _brim_registered_in_test_mode(monkeypatch) as plugin_class:
        assert BRIMProviderRegistry.get_plugin(BRIM_CODE) is plugin_class
        assert BRIM_CODE in BRIMProviderRegistry.list_plugin_codes()
        assert _owned_by("brim", BRIM_CODE) == {*BRIM_DERIVED, brim_lab.API_KEY_ALIAS}, "a user field has no variable to claim"
        assert BRIM_DERIVED == {"LIBREFOLIO_PLUGIN_BRIM_TEST_BRIM_SETTINGS_REGION", "LIBREFOLIO_PLUGIN_BRIM_TEST_BRIM_SETTINGS_API_KEY"}

    assert BRIMProviderRegistry.get_plugin(BRIM_CODE) is None and not _owned_by("brim", BRIM_CODE)
    print_success("registered, claimed, and taken out cleanly")


def test_a_test_only_brim_plugin_is_served_in_test_mode_only(monkeypatch: pytest.MonkeyPatch):
    """6: ``is_test_mode()`` is read at each call: outside it no lookup finds the plugin and no list names it."""
    with _brim_registered_in_test_mode(monkeypatch) as plugin_class:
        assert BRIMProviderRegistry.get_plugin(BRIM_CODE) is plugin_class, "barrier: served in test mode"

        monkeypatch.delenv("LIBREFOLIO_TEST_MODE")

        assert BRIMProviderRegistry.get_plugin(BRIM_CODE) is None and BRIMProviderRegistry.get_provider_instance(BRIM_CODE) is None
        assert BRIM_CODE not in BRIMProviderRegistry.list_plugin_codes()
        assert BRIM_CODE not in [provider["code"] for provider in BRIMProviderRegistry.list_providers()]


def test_the_brim_registry_refuses_a_bad_declaration_with_its_reason_and_stores_nothing(monkeypatch: pytest.MonkeyPatch):
    """6: a secret with a default is refused with the rule's own words, naming the class; not stored, nothing claimed."""
    bad = type("BadBrimSettings", (brim_lab.SettingsBrimPlugin,), {"settings_fields": (_secret("token", default="s3cret-default"),)})
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    try:
        with pytest.raises(SettingsDeclarationError, match="a secret has no default") as refused:
            with brim_lab.registered_settings_brim(bad):
                pass

        assert bad.__qualname__ in str(refused.value), f"the error must name the plugin class: {refused.value}"
        assert BRIMProviderRegistry.get_plugin(BRIM_CODE) is None and not _owned_by("brim", BRIM_CODE)
    finally:
        BRIMProviderRegistry._get_storage().pop(BRIM_CODE, None)
        release_env_variables("brim", BRIM_CODE)


@pytest.mark.parametrize("squatter", ["derived-name", "alias"])
def test_a_brim_plugin_whose_variable_another_plugin_claimed_is_refused(squatter: str, monkeypatch: pytest.MonkeyPatch):
    """6: the derived name of ``test_brim_settings``/``region`` is also the one of ``test_brim``/``settings_region``; the
    alias is any plugin's, in any family. Either refuses the BRIM plugin, naming the variable; the claim that was there
    stands and the plugin is not stored."""
    print_section(f"6: a BRIM plugin against a claimed {squatter}")
    if squatter == "derived-name":
        owner, claimed = ("brim", "test_brim"), "LIBREFOLIO_PLUGIN_BRIM_TEST_BRIM_SETTINGS_REGION"
        claim_env_variables(*owner, (_field("settings_region", default="x"),))
    else:
        owner, claimed = ("asset", "lab_alias_owner"), brim_lab.API_KEY_ALIAS
        claim_env_variables(*owner, (_secret("token", env=claimed),))
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    try:
        assert claimed_env_variables()[claimed] == owner, "setup: the squatter holds the variable"

        with pytest.raises(SettingsDeclarationError, match=claimed):
            with brim_lab.registered_settings_brim():
                pass

        assert BRIMProviderRegistry.get_plugin(BRIM_CODE) is None, "a refused plugin is not stored"
        assert claimed_env_variables()[claimed] == owner, "the first claim stands"
        assert not _owned_by("brim", BRIM_CODE), "a refused claim claims nothing"
    finally:
        BRIMProviderRegistry._get_storage().pop(BRIM_CODE, None)
        release_env_variables("brim", BRIM_CODE)
        release_env_variables(*owner)


def test_the_derived_variable_of_a_brim_field_is_the_family_name_then_the_code_then_the_key():
    """6, guard: ``env_name`` is generic: ``LIBREFOLIO_PLUGIN_BRIM_<CODE>_<FIELD>``, every other character ``_``."""
    assert env_name("brim", "test_brim_settings", "api_key") == "LIBREFOLIO_PLUGIN_BRIM_TEST_BRIM_SETTINGS_API_KEY"
    assert env_name("brim", "broker-x.csv", "token") == "LIBREFOLIO_PLUGIN_BRIM_BROKER_X_CSV_TOKEN"
    assert env_variables("brim", BRIM_CODE, brim_lab.SETTINGS_FIELDS[3]) == (env_name("brim", BRIM_CODE, "api_key"), brim_lab.API_KEY_ALIAS)
    assert env_variables("brim", BRIM_CODE, brim_lab.SETTINGS_FIELDS[0]) == (), "a personal field has no variable"


def _title(catalogue: dict, family: str) -> object:
    families = catalogue.get("pluginSettings", {}).get("families", {})
    return families.get(family)


@pytest.mark.parametrize("language", ["en", "it", "fr", "es"])
@pytest.mark.parametrize("family", ["asset", "fx", "brim"])
def test_every_settings_family_has_its_title_in_every_language(family: str, language: str):
    """6: the Plugins tab titles each family group with ``pluginSettings.families.<family>``, read from the catalogue the
    sources really hold (no English fallback). ``asset`` and ``fx`` are the controls; ``brim`` is red until its key is added."""
    title = _title(load_catalog(language, fallback=False), family)

    assert isinstance(title, str) and title.strip(), f"pluginSettings.families.{family} has no text in {language}"
