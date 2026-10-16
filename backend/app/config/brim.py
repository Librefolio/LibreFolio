"""Broker-import (BRIM) section of the configuration: whether the import workers are made ready at startup.

Owner: workstream W (import and transactions, release 1.3). Read from the process environment at the moment of use,
never from ``.env`` nor from the database.

``LIBREFOLIO_BRIM_PREWARM`` starts the BRIM parse pool's forkserver at application startup, preloaded with the BRIM
module and its plugins (W-B53, ``services/brim/brim_parse_pool.prewarm``): the first import of a broker file after a
start then forks a ready worker instead of starting an interpreter, ~4 s sooner on an idle machine. The price is ~80 MB
held from the start and ~1.4 s of CPU at every start of the server (a deploy, a restart, the wake of a machine that was
stopped rather than suspended): a bad trade for small cloud machines (decision N56, 16/10/2026). So it is **off by
default**, and **on in test mode**, where an overloaded test machine paid 30-50 s for that first import (a test lane
keeps no other variable, so the mode decides there).

``1``/``true``/``yes``/``on`` turn it on, ``0``/``false``/``no``/``off`` off, case-insensitive; unset or blank follows
the mode. Any other value raises ``BrimConfigError``, which names the variable; the caller decides what follows (the
startup step logs it and leaves the pool lazy, and the pool counts it as off). With it off nothing changes from before
W-B53: the first parse starts the forkserver with nothing preloaded, and each worker imports the BRIM module and its
plugins itself, at its first parse, away from the event loop (W-B59: preloading on that path held the loop for the whole
import).
"""

import os

from backend.app.config import is_test_mode

#: The variable that makes the BRIM import workers ready at startup.
BRIM_PREWARM_VARIABLE = "LIBREFOLIO_BRIM_PREWARM"

_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"0", "false", "no", "off"})


class BrimConfigError(ValueError):
    """A value of this section that cannot be used: ``variable`` names it."""

    def __init__(self, variable: str, message: str):
        super().__init__(f"{variable}: {message}")
        self.variable = variable


def brim_prewarm_enabled() -> bool:
    """Whether the application startup makes the BRIM import workers ready (``LIBREFOLIO_BRIM_PREWARM``; see the module).

    Raises:
        BrimConfigError: a value that is neither a true nor a false spelling.
    """
    raw = os.environ.get("LIBREFOLIO_BRIM_PREWARM", "").strip().lower()  # the literal name: the .env.example guard sees it
    if not raw:
        return is_test_mode()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    raise BrimConfigError(BRIM_PREWARM_VARIABLE, f"{raw!r} is not one of {sorted(_TRUE | _FALSE)}")
