"""Hosting panel section of the configuration: the credentials a hosting panel calls the instance with (lot H-61).

Owner: workstream H (platform). Read from the process environment only, at each call: ``./dev.py`` and Docker Compose
put the variables there. Every default leaves an install as it was: unset, a scope of the panel is off and its routes
answer 404, as if they did not exist.

The panel has three scopes, each with a token of its own (decision Q2 of H-61): the backup routes
(``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN``, ``config/backup.py``, workstream B), the scheduled wake-up
(``LIBREFOLIO_WAKE_TOKEN``, ``config/sleep_wake.py``, workstream Z) and the status of the instance
(``LIBREFOLIO_PANEL_STATUS_TOKEN``, here). The three follow the same rules: the variable or its ``_FILE``, as Docker
secrets mount it; visible ASCII characters only; at least ``PANEL_TOKEN_MIN_LENGTH`` characters. The shared access to
the routes is ``services/platform/hosting_panel/access.py``.
"""

from backend.app.config import env_secret
from backend.app.config.backup import PANEL_TOKEN_CHARACTERS, PANEL_TOKEN_MIN_LENGTH

#: The variable of the panel's token for the status route; ``env_secret`` also reads it from ``<name>_FILE``.
PANEL_STATUS_TOKEN_VARIABLE = "LIBREFOLIO_PANEL_STATUS_TOKEN"


class HostingPanelConfigError(ValueError):
    """A hosting panel value that cannot be used: ``variable`` names it, ``code`` says what is wrong.

    The message names the variable and the rule, never the value of a secret.
    """

    def __init__(self, variable: str, code: str, message: str):
        super().__init__(f"{variable}: {message}")
        self.variable = variable
        self.code = code


def panel_status_token() -> str | None:
    """``LIBREFOLIO_PANEL_STATUS_TOKEN``, or the content of its ``_FILE``: the token of the panel's status route, as written.

    ``None`` when neither is set: ``GET /api/v1/panel/status`` is off and answers 404. The rules are those of the backup
    and wake-up tokens: a token holding anything but visible ASCII characters raises ``HostingPanelConfigError``
    ``PANEL_STATUS_TOKEN_NOT_VISIBLE_ASCII``, one shorter than ``PANEL_TOKEN_MIN_LENGTH`` characters
    ``PANEL_STATUS_TOKEN_TOO_SHORT``; a ``_FILE`` that cannot give its secret raises ``SecretFileError``
    (``env_secret``). The value is never in a message.
    """
    token = env_secret(PANEL_STATUS_TOKEN_VARIABLE)
    if token is None:
        return None
    if not PANEL_TOKEN_CHARACTERS.issuperset(token):
        raise HostingPanelConfigError(
            PANEL_STATUS_TOKEN_VARIABLE,
            "PANEL_STATUS_TOKEN_NOT_VISIBLE_ASCII",
            "expected visible ASCII characters only, without spaces: a request header carries nothing else as written",
        )
    if len(token) < PANEL_TOKEN_MIN_LENGTH:
        raise HostingPanelConfigError(
            PANEL_STATUS_TOKEN_VARIABLE,
            "PANEL_STATUS_TOKEN_TOO_SHORT",
            f"expected at least {PANEL_TOKEN_MIN_LENGTH} characters, for example the output of `openssl rand -hex 32`",
        )
    return token
