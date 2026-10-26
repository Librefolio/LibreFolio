"""The settings of the Tools a batch calls, resolved in the parent for the user who asks (CP12, X5-4b).

A Tool's ``compute`` runs in an isolated worker with no database and no request, so the values of its fields are read here,
before the jobs start, and travel with each job (``ToolWorkerJob.settings``) like the BRIM parse's. The instance's values
always reach the tool; the user's personal ones are those of ``user_id``, who asks. They are resolved again for every batch,
never kept between calls.
"""

from __future__ import annotations

from backend.app.schemas.tools import ToolComputeBatchRequest
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.runtime import bound_settings_for
from backend.app.services.tools.registry import ToolPluginRegistry


async def bound_settings_for_batch(batch: ToolComputeBatchRequest, *, user_id: int | None, registry: type[ToolPluginRegistry] = ToolPluginRegistry) -> dict[str, BoundSettings]:
    """The bound values of each tool code of ``batch`` whose plugin declares fields, by tool code.

    A tool without fields, or one the registry does not know, is absent: no database read, no key. One resolution per distinct
    tool code, however many items of the batch call it.
    """
    bound_by_code: dict[str, BoundSettings] = {}
    for tool_code in dict.fromkeys(item.tool_code for item in batch.items):
        bound = await bound_settings_for(registry, tool_code, user_id=user_id)
        if bound is not None:
            bound_by_code[tool_code] = bound
    return bound_by_code
