"""What the BRIM parse pool's forkserver imports once, so that every worker is born with it (W-B53).

The forkserver (``brim_parse_pool._PRELOAD``) imports this module in its own process at application startup: the BRIM
module and every plugin, discovered, so the first parse forks a ready worker instead of starting an interpreter that
imports them. Nothing imports it in the server process. A failure of the discovery is logged here and left to the worker's
first parse, which reports it as it always did: the forkserver only survives an ``ImportError`` in a preload, so nothing
may escape.
"""

import structlog

from backend.app.services.brim import brim_provider  # noqa: F401 - the preload is the import itself
from backend.app.services.brim.registry import BRIMProviderRegistry

logger = structlog.get_logger(__name__)

try:
    BRIMProviderRegistry.auto_discover()
except Exception as exc:  # noqa: BLE001 - the worker's first parse raises it again, where it is reported
    logger.warning("BRIM plugin discovery failed in the parse pool's forkserver; the first parse reports it", error=str(exc))
