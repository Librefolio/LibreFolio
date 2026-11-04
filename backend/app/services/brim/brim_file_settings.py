"""A BRIM parse is stale when a setting of its plugin changed since it was drawn (CP12, W5-8).

``brim_provider._build_file_info_from_metadata`` already marks a parse stale when the plugin's version moved. A setting that
changes the output (the order of day and month of the generic CSV) must say the same, or the user reads yesterday's dates.
That cannot be decided there: it is synchronous and knows no user, while the values a parse would receive depend on who looks
(the instance's and that user's own). So the file routes call ``apply_settings_staleness`` on the infos they return.

The rule is ``plugin_settings.resolver.settings_changed_since``; this module only feeds it: the fingerprint the parse saved
(``BRIMFileInfo.parsed_settings_fingerprint``) and the values of the user who looks now.
"""

from __future__ import annotations

from collections.abc import Iterable

from backend.app.schemas.brim import BRIMFileInfo
from backend.app.services.brim.brim_provider import BRIMFileStatus
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.resolver import settings_changed_since
from backend.app.services.plugin_settings.runtime import bound_settings_for


async def apply_settings_staleness(files: Iterable[BRIMFileInfo], user_id: int | None) -> None:
    """Set ``parse_is_stale`` on every PARSED file whose plugin's settings changed for ``user_id`` since its parse.

    Adds to the flag of the plugin version (``or``): a flag already true stays true. A plugin without fields, a file that is not
    PARSED and a file that records no plugin are left alone, with no database read. The values of a plugin are read once for all
    the files of the call.
    """
    current: dict[str, BoundSettings | None] = {}
    for info in files:
        code = info.parsed_plugin_code
        if info.status != BRIMFileStatus.PARSED or not code or info.parse_is_stale:
            continue
        plugin_class = BRIMProviderRegistry.get_plugin(code)
        fields = getattr(plugin_class, "settings_fields", ())
        if not fields:
            continue
        if code not in current:
            current[code] = await bound_settings_for(BRIMProviderRegistry, code, user_id=user_id)
        if settings_changed_since(info.parsed_settings_fingerprint, current[code], fields):
            info.parse_is_stale = True
