"""The test-only shared group ``mock``: read by ``mockprov``, so that the shared-backend tests and the interface tests
can exercise a group end to end (catalogue, writes, delivery, the group's tab). Never listed to users, never required:
mockprov stays callable without it (project 76, G2)."""

from __future__ import annotations

from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType
from backend.app.services.plugin_settings.groups import SettingsGroup, register_group

MOCK_GROUP = SettingsGroup(
    name="mock",
    label="Mock group (testing)",
    description="A group for the tests: a secret and a plan, read by the mock provider.",
    test_only=True,
    fields=(
        PluginSettingField(
            key="account_token",
            type=SettingType.STRING,
            scope=SettingScope.SYSTEM,
            secret=True,
            label="Account token (testing)",
            description="A secret the tests set: the mock only reports whether it is set.",
        ),
        PluginSettingField(
            key="tier",
            type=SettingType.SELECT,
            scope=SettingScope.SYSTEM,
            label="Tier (testing)",
            default="free",
            options=(SettingOption("free", "Free"), SettingOption("paid", "Paid")),
        ),
    ),
)

register_group(MOCK_GROUP)
