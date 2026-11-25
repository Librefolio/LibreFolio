"""The shared group ``coingecko``: one CoinGecko account, read by the price provider (project 76) and by the
enricher of the same source (82 CG-B). The key and the plan are set once, here, and the plugins that read the group
spend one account's credits: their calls are counted, and limited, on the group (``shares_credits``, project 76 U2).

The API key is required: without it every plugin that reads the group is «to configure» (N1) and answers its calls
with NOT_CONFIGURED. The plan picks the API root (Demo: ``api.coingecko.com``, Pro: ``pro-api.coingecko.com``).
"""

from __future__ import annotations

from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType
from backend.app.services.plugin_settings.groups import SettingsGroup, register_group

#: The group's name: its rows (``family="group"``), its variables (``LIBREFOLIO_PLUGIN_GROUP_COINGECKO_*``), its texts.
COINGECKO_GROUP_NAME = "coingecko"
#: The plans, as the field stores them: they pick the API root and the header the key travels in.
PLAN_DEMO = "demo"
PLAN_PRO = "pro"

COINGECKO_GROUP = SettingsGroup(
    name=COINGECKO_GROUP_NAME,
    label="CoinGecko",
    description="The CoinGecko account the CoinGecko plugins share: its API key and its plan.",
    label_key="pluginSettings.group.coingecko.name",
    description_key="pluginSettings.group.coingecko.about",
    shares_credits=True,
    fields=(
        PluginSettingField(
            key="api_key",
            type=SettingType.STRING,
            scope=SettingScope.SYSTEM,
            secret=True,
            required=True,
            label="API key",
            description="The key of a CoinGecko account. A free Demo key is enough.",
            label_key="pluginSettings.group.coingecko.label.api_key",
            description_key="pluginSettings.group.coingecko.description.api_key",
            missing_key="pluginSettings.group.coingecko.missing.api_key",
        ),
        PluginSettingField(
            key="plan",
            type=SettingType.SELECT,
            scope=SettingScope.SYSTEM,
            label="Plan",
            description="The plan of the key: a Demo key answers on the public API, a paid key on the Pro API.",
            default=PLAN_DEMO,
            options=(
                SettingOption(PLAN_DEMO, "Demo (free)", label_key="pluginSettings.group.coingecko.option.plan.demo"),
                SettingOption(PLAN_PRO, "Pro (paid)", label_key="pluginSettings.group.coingecko.option.plan.pro"),
            ),
            label_key="pluginSettings.group.coingecko.label.plan",
            description_key="pluginSettings.group.coingecko.description.plan",
        ),
    ),
)

register_group(COINGECKO_GROUP)
