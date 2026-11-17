"""A field's own phrase for the «to configure» window (project 76, lot N3a2; the developer's choice B, option b).

The window says what is missing in a sentence: «CoinGecko va configurato: manca la chiave API». The noun phrase, with its
article, depends on the language, so a field may declare the i18n key of that phrase (``missing_key``), owned by the
plugin as its ``label_key`` is. The contract pinned here:

1. ``PluginSettingField.missing_key``: optional, None by default; a declaration with it validates.
2. The catalogue's field read carries it (``PluginSettingFieldRead.missing_key``), as it carries ``label_key``; None when
   the field declares none (the interface then names the field by its label).

The plugin i18n ownership gate reads it as a key (``utils gate-plugin-i18n-ownership``, its own test file).
Pure: no database, no server.
Red on HEAD bd98f031b: the field has no such attribute.
"""

from __future__ import annotations

from backend.app.schemas.plugin_settings import PluginSettingFieldRead
from backend.app.services.plugin_settings import service
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingScope, SettingType, validate_declaration
from backend.app.services.plugin_settings.resolver import FieldState


def _key_field(**extra) -> PluginSettingField:
    return PluginSettingField(key="api_key", type=SettingType.STRING, scope=SettingScope.SYSTEM, label="API key", secret=True, required=True, **extra)


def test_n3a2_a_field_may_declare_its_missing_phrase_key_and_none_is_the_default():
    assert _key_field().missing_key is None
    declared = _key_field(missing_key="pluginSettings.asset.keyed.missing.api_key")
    assert declared.missing_key == "pluginSettings.asset.keyed.missing.api_key"
    validate_declaration((declared,), family="asset")


def test_n3a2_the_catalogue_field_read_carries_the_phrase_key():
    assert "missing_key" in PluginSettingFieldRead.model_fields
    with_phrase = service._field_read(FieldState(field=_key_field(missing_key="pluginSettings.asset.keyed.missing.api_key"), source="none"), is_admin=True)
    without = service._field_read(FieldState(field=_key_field(), source="none"), is_admin=True)
    assert (with_phrase.missing_key, without.missing_key) == ("pluginSettings.asset.keyed.missing.api_key", None)
