"""The contract of a field in a BRIM plugin (CP12, X5-4a): how one is declared, what the plugin sees, when a parse is stale.

The first real field is the order of the day and the month in the generic CSV plugin (written by workstream W on this
contract). This module is the worked example of the developer guide (``backend/brim/architecture.md``, «A field in a
BRIM plugin») made executable. It pins four things:

1. **A BRIM plugin declares a field the way every family does**: ``settings_fields`` with a ``PluginSettingField``,
   checked when the plugin registers against the rules of the ``brim`` family (``FAMILY_RULES``).
2. **The default of a field is the behaviour before the field existed.** An instance nobody configured, a user who
   chose nothing, and a call made where the settings are not delivered (detection, report sets, gap fix: only the parse
   delivers them) all see the default, so the output of an unchanged file is the one it always was.
3. **The parse sees the value of the user who imports** (the instance's value, then that user's own), and another user's
   value does not reach it.
4. **A parse is stale when the settings changed** (``resolver.settings_changed_since``): the fingerprint of the values the
   parse received is saved with its result, and the file is stale as soon as the values a re-parse would receive differ.
   A result drawn before the field existed (nothing saved) is compared with the defaults, so it is not stale until a value
   moves away from the default. The code that saves the fingerprint and reads the rule on the file listing is W's
   (lot W5-8, ``brim_provider.py`` and the files route); the rule itself, and this test, are here.

Pure: no database, no server, no file. The values are built the way the core builds them (``build_bound_settings``) from
the rows the database would hold (``StoredValue``).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.app.schemas.brim import BRIMParseOutput
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.plugin_settings import resolver
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.crypto import encrypt_secret, key_id_of, secret_aad, settings_subkey
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingsDeclarationError, SettingType
from backend.app.services.plugin_settings.resolver import StoredValue, build_bound_settings, default_settings_fingerprint, settings_changed_since
from backend.test_scripts.test_services import _brim_settings_lab as brim_lab

CODE = "test_brim_date_order"
KEY = "LibreFolio-brim-field-contract-test-key-0123456789"

#: The field of the worked example: personal, a select, and its default is what the plugin did before the field existed.
DATE_ORDER = PluginSettingField(
    key="date_order",
    type=SettingType.SELECT,
    scope=SettingScope.USER,
    label="Order of day and month",
    description="How a date such as 03/04/2025 is read: the day first (3 April) or the month first (4 March).",
    default="day_first",
    options=(SettingOption("day_first", "Day first"), SettingOption("month_first", "Month first")),
)


class DateOrderExample(brim_lab.SettingsBrimPlugin):
    """The worked example: a plugin that reads a date with the order its user chose. ``parse`` is the real shape (a
    plugin reads ``self.settings`` inside it, never in ``__init__``)."""

    settings_fields = (DATE_ORDER,)

    @property
    def provider_code(self) -> str:
        return CODE

    def read_day_and_month(self, text: str) -> tuple[int, int]:
        """``03/04/2025`` read with the order the settings give: ``(3, 4)`` day first, ``(4, 3)`` month first."""
        first, second = (int(part) for part in text.split("/")[:2])
        return (first, second) if self.settings.get("date_order") == "day_first" else (second, first)

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        return BRIMParseOutput(transactions=[], warnings=[], extracted_assets={})


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test mode (the example is ``test_only``), a test instance key, no ambient variable of the example's field."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY)
    monkeypatch.setattr(resolver, "_warned_unreadable", set())
    monkeypatch.setattr(resolver, "_warned_invalid_env", set())
    monkeypatch.setattr(resolver, "_warned_key_unavailable", [])


@pytest.fixture
def registered() -> Iterator[type[DateOrderExample]]:
    with brim_lab.registered_settings_brim(DateOrderExample) as plugin_class:
        yield plugin_class


def _stored(value: str) -> StoredValue:
    return StoredValue(value_json=json.dumps(value), secret_ciphertext=None, key_id=None, updated_at=datetime.now(UTC))


def _bound(*, user_choice: str | None = None, user_id: int | None = 7, fields: tuple[PluginSettingField, ...] = (DATE_ORDER,)) -> BoundSettings:
    """What the core would bind for a parse run for ``user_id``, who saved ``user_choice`` (None: nothing saved)."""
    user_rows = {"date_order": _stored(user_choice)} if user_choice is not None else {}
    return build_bound_settings("brim", CODE, fields, {}, user_rows, user_id=user_id)


# =============================================================================
# 1. THE DECLARATION
# =============================================================================


def test_a_brim_plugin_declares_a_field_like_every_family_and_registers(registered: type[DateOrderExample]):
    """The family takes the declaration: the plugin is in the real registry, with its field, and the family is ``brim``."""
    assert BRIMProviderRegistry.settings_family() == "brim"
    assert BRIMProviderRegistry.get_plugin(CODE) is registered
    assert registered.settings_fields == (DATE_ORDER,)


def test_a_declaration_the_family_refuses_is_refused_when_the_plugin_registers():
    """A personal secret cannot be required (it would lock out every user who has not set one), so this declaration is
    invalid, and the plugin is not registered: the example would fail the same way a real plugin does."""

    class Broken(DateOrderExample):
        settings_fields = (PluginSettingField(key="token", type=SettingType.STRING, scope=SettingScope.USER, secret=True, required=True, label="Token"),)

    with pytest.raises(SettingsDeclarationError):
        with brim_lab.registered_settings_brim(Broken):
            pass
    assert BRIMProviderRegistry.get_plugin(CODE) is None


# =============================================================================
# 2. THE DEFAULT IS THE OLD BEHAVIOUR
# =============================================================================


def test_a_plugin_nobody_configured_reads_the_default_and_keeps_its_old_output(registered: type[DateOrderExample]):
    """``03/04/2025`` read by an instance the core did not configure (detection, report sets, gap fix) is day first, as
    the plugin always did: the default of the field is the behaviour before the field."""
    plugin = BRIMProviderRegistry.get_provider_instance(CODE)

    assert plugin.settings.get("date_order") == "day_first"
    assert plugin.read_day_and_month("03/04/2025") == (3, 4)


def test_a_user_who_chose_nothing_gets_the_default_through_the_core():
    """The binding the core makes for a user with no row is the default, and its fingerprint is the baseline of a result
    drawn before the field existed (``default_settings_fingerprint``)."""
    bound = _bound(user_choice=None)

    assert bound.get("date_order") == "day_first"
    assert bound.fingerprint == default_settings_fingerprint((DATE_ORDER,))


# =============================================================================
# 3. THE PARSE SEES THE VALUE OF THE USER WHO IMPORTS
# =============================================================================


def test_the_parse_reads_the_value_the_importing_user_chose(registered: type[DateOrderExample]):
    """The core binds the values on the plugin right before the parse; the plugin reads them inside ``parse``."""
    plugin = BRIMProviderRegistry.get_provider_instance(CODE)
    plugin.bind_settings(_bound(user_choice="month_first"))

    assert plugin.read_day_and_month("03/04/2025") == (4, 3)


def test_another_users_choice_does_not_reach_the_parse():
    """The rows of a user are read for that user only: the same instance, two users, two bindings."""
    alice = build_bound_settings("brim", CODE, (DATE_ORDER,), {}, {"date_order": _stored("month_first")}, user_id=1)
    bob = build_bound_settings("brim", CODE, (DATE_ORDER,), {}, {}, user_id=2)

    assert (alice.get("date_order"), bob.get("date_order")) == ("month_first", "day_first")
    assert alice.fingerprint != bob.fingerprint


# =============================================================================
# 4. WHEN A PARSE IS STALE
# =============================================================================


def test_a_plugin_that_declares_no_field_is_never_stale_for_its_settings():
    """``bound_settings_for`` answers None for it: nothing a setting can change."""
    assert settings_changed_since(None, None, ()) is False
    assert settings_changed_since("a-saved-fingerprint", None, ()) is False


def test_a_parse_is_stale_exactly_when_the_values_a_re_parse_would_receive_differ():
    parsed_with = _bound(user_choice="day_first")
    saved = parsed_with.fingerprint

    assert settings_changed_since(saved, _bound(user_choice="day_first"), (DATE_ORDER,)) is False
    assert settings_changed_since(saved, _bound(user_choice="month_first"), (DATE_ORDER,)) is True
    # Chosen and then chosen back: the same values, the same fingerprint, no longer stale.
    assert settings_changed_since(saved, _bound(user_choice="month_first"), (DATE_ORDER,)) is True
    assert settings_changed_since(saved, _bound(user_choice="day_first"), (DATE_ORDER,)) is False


def test_a_parse_drawn_before_the_field_existed_is_compared_with_the_defaults():
    """Nothing saved: the result was drawn over the defaults. A user still on the default sees no stale file; the one who
    moved away from it does."""
    assert settings_changed_since(None, _bound(user_choice=None), (DATE_ORDER,)) is False
    assert settings_changed_since("", _bound(user_choice=None), (DATE_ORDER,)) is False, "an empty record is no record"
    assert settings_changed_since(None, _bound(user_choice="month_first"), (DATE_ORDER,)) is True


def test_the_user_who_looks_decides_not_the_one_who_parsed():
    """The file was parsed for alice (day first, saved); bob would re-parse with month first: for bob it is stale, for
    alice it is not. The rule is applied with the bound values of the person who asks."""
    saved = build_bound_settings("brim", CODE, (DATE_ORDER,), {}, {"date_order": _stored("day_first")}, user_id=1).fingerprint
    alice = build_bound_settings("brim", CODE, (DATE_ORDER,), {}, {"date_order": _stored("day_first")}, user_id=1)
    bob = build_bound_settings("brim", CODE, (DATE_ORDER,), {}, {"date_order": _stored("month_first")}, user_id=2)

    assert (settings_changed_since(saved, alice, (DATE_ORDER,)), settings_changed_since(saved, bob, (DATE_ORDER,))) == (False, True)


def test_a_secret_set_since_the_parse_makes_it_stale():
    """A secret takes part in the fingerprint (as an HMAC under the instance key, never in clear): a token set after the
    parse changes what a re-parse would receive, and the fingerprint does not show it."""
    token_field = PluginSettingField(key="personal_token", type=SettingType.STRING, scope=SettingScope.USER, secret=True, label="Token")
    fields = (DATE_ORDER, token_field)
    secret = "lfsecret-contract-0123456789abcdef"
    subkey = settings_subkey()
    ciphertext = encrypt_secret(subkey, secret_aad("brim", CODE, "personal_token", "user", 7), secret)
    with_token = {"personal_token": StoredValue(value_json=None, secret_ciphertext=ciphertext, key_id=key_id_of(subkey), updated_at=datetime.now(UTC))}

    without = build_bound_settings("brim", CODE, fields, {}, {}, user_id=7)
    with_it = build_bound_settings("brim", CODE, fields, {}, with_token, user_id=7)
    saved = without.fingerprint

    assert saved == default_settings_fingerprint(fields), "no secret bound: the baseline of the defaults"
    assert settings_changed_since(saved, without, fields) is False
    assert settings_changed_since(saved, with_it, fields) is True, "a token set after the parse"
    assert secret not in with_it.fingerprint
    # Once recorded, the parse is current again for the same values.
    assert settings_changed_since(with_it.fingerprint, with_it, fields) is False
