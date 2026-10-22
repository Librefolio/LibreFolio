"""A test-only BRIM plugin that declares settings, and the way to register it for the length of one test.

No real BRIM plugin declares a setting yet: the settings of the BRIM family (``FAMILY_RULES["brim"]``, the same rules as
the price sources: personal and instance-wide fields, secrets of both scopes) are exercised with this plugin, which lives
in the tests only. It is **never** a folder under ``backend/app/services/brim_providers/``: the suites that loop over every
real plugin (row skips, report sets, providers) must never meet it.

``registered_settings_brim`` puts the class in the real ``BRIMProviderRegistry`` through ``register`` (so that the family
rules and the claims of its environment variables are really applied) and, at exit, takes it out again — the class and
the claims — whatever the test did. ``test_only`` plugins are served only in test mode (``is_test_mode()``): the test sets
``LIBREFOLIO_TEST_MODE`` itself.

The plugin records what it receives (``seen``) and can be told to fail (``fail_with``): both are class attributes the test
sets through ``monkeypatch``, because the registry hands out a new instance for each call.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, ClassVar

from backend.app.schemas.brim import BRIMParseOutput
from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType, release_env_variables

CODE = "test_brim_settings"
NAME = "Settings BRIM plugin (TESTING ONLY)"
ICON = "https://icons.example.test/test-brim-settings.png"
#: The alias of the instance secret: another plugin that claims it first makes the registration refuse this one.
API_KEY_ALIAS = "LIBREFOLIO_TEST_BRIM_SETTINGS_API_KEY"

#: A personal select, a personal secret, an instance-wide select with a default, an instance-wide secret with an alias.
SETTINGS_FIELDS = (
    PluginSettingField(
        key="statement_language",
        type=SettingType.SELECT,
        scope=SettingScope.USER,
        label="Statement language (testing)",
        default="all",
        options=(SettingOption("all", "All"), SettingOption("it", "Italian"), SettingOption("en", "English")),
    ),
    PluginSettingField(key="personal_token", type=SettingType.STRING, scope=SettingScope.USER, secret=True, label="Personal token (testing)"),
    PluginSettingField(
        key="region",
        type=SettingType.SELECT,
        scope=SettingScope.SYSTEM,
        label="Region (testing)",
        default="eu",
        options=(SettingOption("eu", "Europe"), SettingOption("us", "United States")),
    ),
    PluginSettingField(key="api_key", type=SettingType.STRING, scope=SettingScope.SYSTEM, secret=True, label="API key (testing)", env=API_KEY_ALIAS),
)


class SettingsBrimPlugin(BRIMProvider):
    """A BRIM plugin of the tests: four settings, a parse that does nothing but record what it was given."""

    test_only = True
    settings_fields = SETTINGS_FIELDS

    #: What each ``parse`` saw: the bound settings of that instance (the one the plugin reads, ``self.settings``).
    seen: ClassVar[list[BoundSettings]] = []
    #: When set, ``parse`` calls it with the instance's settings instead of returning: the hook that raises or logs.
    on_parse: ClassVar[Callable[[BoundSettings], Any] | None] = None

    @property
    def provider_code(self) -> str:
        return CODE

    @property
    def provider_name(self) -> str:
        return NAME

    @property
    def description(self) -> str:
        return "Test-only BRIM plugin that declares settings."

    @property
    def icon_url(self) -> str | None:
        return ICON

    def can_parse(self, file_path: Path) -> bool:
        return True

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        bound = self.settings
        type(self).seen.append(bound)
        if type(self).on_parse is not None:
            type(self).on_parse(bound)
        return BRIMParseOutput(transactions=[], warnings=[], extracted_assets={})


@contextmanager
def registered_settings_brim(plugin_class: type[BRIMProvider] = SettingsBrimPlugin) -> Iterator[type[BRIMProvider]]:
    """``plugin_class`` registered in the real BRIM registry; out again, with its claims, when the block ends.

    ``register`` raises ``SettingsDeclarationError`` when the family cannot take its declaration: nothing is left behind.
    """
    code = plugin_class().provider_code
    BRIMProviderRegistry.auto_discover()
    BRIMProviderRegistry.register(plugin_class)
    try:
        yield plugin_class
    finally:
        BRIMProviderRegistry._get_storage().pop(code, None)
        release_env_variables("brim", code)
