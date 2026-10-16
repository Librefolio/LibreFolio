"""What a process of the BRIM parse pool finds already imported: the probe of ``test_brim_parse_pool.py`` (W-B53, J-30).

``test_brim_parse_pool.py`` submits ``worker_report`` to the pool ``brim_parse_pool._get_pool()`` builds, in a fresh
interpreter. Unpickling it imports this module in the worker, and nothing else of the app: its imports are the standard
library only, and its packages import nothing (``backend`` is a namespace package, the two ``__init__.py`` of
``backend.test_scripts`` and ``backend.test_scripts.test_services`` are empty). So what a worker answers True for, it got
from the forkserver it was forked from, never from this probe. The registry's discovery state is read the same way, through
``sys.modules``, without importing the registry. The test checks both directions in the fresh interpreter: this module alone
finds nothing, and once the interpreter itself has imported the BRIM module and run the discovery, it finds everything.

A helper, not a test: pytest never collects it and the runner's orphan check never lists it, since its name does not start
with ``test_``.
"""

import os
import sys

#: Unpickling ``brim_provider.parse_file`` drags this module into a worker that lacks it, and the first parse pays for it.
BRIM_MODULE = "backend.app.services.brim.brim_provider"
#: The module of ``BRIMProviderRegistry``, read here through ``sys.modules`` only.
REGISTRY_MODULE = "backend.app.services.brim.registry"
#: A plugin module, loaded only by the registry's discovery: the one the parse tests use. The first parse discovers every
#: plugin unless the worker was born with them.
PLUGIN_MODULE = "backend.app.services.brim_providers.broker_schwab.plugin"
#: The module the cure has the forkserver preload: reported, never required, to tell a missing preload from a preload that
#: did not do its job.
PRELOAD_MODULE = "backend.app.services.brim.brim_parse_preload"


def brim_module_loaded() -> bool:
    """Whether ``BRIM_MODULE`` is already imported in the process that runs this."""
    return BRIM_MODULE in sys.modules


def plugin_module_loaded() -> bool:
    """Whether ``PLUGIN_MODULE`` is already imported in the process that runs this."""
    return PLUGIN_MODULE in sys.modules


def registry_discovery_done() -> bool:
    """Whether ``BRIMProviderRegistry`` has run its discovery in the process that runs this; False while its module is not
    even imported. ``_discovery_done`` is the registry's own class attribute: true once every plugin module was executed."""
    registry = getattr(sys.modules.get(REGISTRY_MODULE), "BRIMProviderRegistry", None)
    return getattr(registry, "_discovery_done", False) is True


def loaded_report() -> dict[str, bool]:
    """What the process that runs this has already imported or done, of what the first parse needs."""
    return {
        "brim_module_loaded": brim_module_loaded(),
        "plugin_module_loaded": plugin_module_loaded(),
        "registry_discovery_done": registry_discovery_done(),
        "preload_module_loaded": PRELOAD_MODULE in sys.modules,
    }


def worker_report() -> dict[str, object]:
    """What the worker that runs this found as it started (``loaded_report``), its pid, and the pid of its parent, the
    process that forked it (a forkserver, unless the pool spawned it)."""
    return {**loaded_report(), "pid": os.getpid(), "ppid": os.getppid()}
