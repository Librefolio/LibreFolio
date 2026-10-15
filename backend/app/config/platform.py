"""Platform section of the configuration: switches of the runtime itself.

Owner: workstream H (platform). Every environment variable of the application is read inside this package,
``backend/app/config/``: a module elsewhere calls a function here instead of reading ``os.environ``. The base
(constants, data directories, test mode, ``Settings``, the ``NAME_FILE`` reader of secrets) is in ``__init__.py``; each
owner keeps its variables in its own section module.

The variables below are read from the process environment only, never from ``.env``: ``./dev.py`` and Docker Compose
put them there. Each function keeps the exact semantics the call site had before it moved here, except that a blank
secret counts as unset.
"""

import os

from backend.app.config import env_secret, env_secret_origin


def scheduler_disabled() -> bool:
    """``LIBREFOLIO_NO_SCHEDULER``: any non-empty value keeps the scheduler loop from starting.

    ``./dev.py server --no-scheduler`` sets it for test servers and the gallery. Every non-empty value counts, ``0``
    included.
    """
    return bool(os.environ.get("LIBREFOLIO_NO_SCHEDULER"))


def configured_jwt_secret() -> str | None:
    """``JWT_SECRET``, the key that signs session tokens, or else the content of the file named by ``JWT_SECRET_FILE``.

    ``None`` when neither is set: an empty or blank value counts as unset, so a stray space is never used as a key and
    the server makes a random one. A ``JWT_SECRET_FILE`` that cannot give its secret raises ``SecretFileError``
    (``env_secret``).
    """
    return env_secret("JWT_SECRET")


def configured_jwt_secret_origin() -> str | None:
    """Where the JWT secret comes from, for messages: ``JWT_SECRET``, ``JWT_SECRET_FILE (<path>)`` or ``None``."""
    return env_secret_origin("JWT_SECRET")


def configured_instance_key() -> str | None:
    """``LIBREFOLIO_INSTANCE_KEY``, or else the content of ``LIBREFOLIO_INSTANCE_KEY_FILE``; ``None`` when neither is set.

    Without one, ``services/platform/instance_key.py`` generates the key in the data directory on first use.
    """
    return env_secret("LIBREFOLIO_INSTANCE_KEY")


def configured_instance_key_origin() -> str | None:
    """Where the configured instance key comes from, for messages: the variable, or the ``_FILE`` one with its path."""
    return env_secret_origin("LIBREFOLIO_INSTANCE_KEY")


def owning_test_lane_id() -> str | None:
    """``LIBREFOLIO_TEST_LANE_ID``: the token of the test process tree that owns this server, set by the test runner."""
    return os.environ.get("LIBREFOLIO_TEST_LANE_ID")
