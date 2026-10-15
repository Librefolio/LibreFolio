"""Platform section of the configuration: switches of the runtime itself.

Owner: workstream H (platform). Every environment variable of the application is read inside this package,
``backend/app/config/``: a module elsewhere calls a function here instead of reading ``os.environ``. The base
(constants, data directories, test mode, ``Settings``) is in ``__init__.py``; each owner keeps its variables in its own
section module.

The variables below are read from the process environment only, never from ``.env``: ``./dev.py`` and Docker Compose
put them there. Each function keeps the exact semantics the call site had before it moved here, except that a blank
secret counts as unset.
"""

import os


def scheduler_disabled() -> bool:
    """``LIBREFOLIO_NO_SCHEDULER``: any non-empty value keeps the scheduler loop from starting.

    ``./dev.py server --no-scheduler`` sets it for test servers and the gallery. Every non-empty value counts, ``0``
    included.
    """
    return bool(os.environ.get("LIBREFOLIO_NO_SCHEDULER"))


def configured_jwt_secret() -> str | None:
    """``JWT_SECRET``: the key that signs session tokens, when the environment provides one.

    An empty or blank value is none, so a stray space is never used as a key and the server makes a random one.
    """
    value = os.environ.get("JWT_SECRET", "")
    return value if value.strip() else None


def owning_test_lane_id() -> str | None:
    """``LIBREFOLIO_TEST_LANE_ID``: the token of the test process tree that owns this server, set by the test runner."""
    return os.environ.get("LIBREFOLIO_TEST_LANE_ID")
