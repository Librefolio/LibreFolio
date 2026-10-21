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

Level L2 (H-61, checkpoint 2) adds signed tickets beside the tokens, for all three scopes: the panel's Ed25519 public
keys (``LIBREFOLIO_PANEL_PUBLIC_KEYS``, not a secret, so no ``_FILE``), the tolerance on the tickets' times
(``LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS``) and the audience a ticket must name, the origin of ``LIBREFOLIO_PUBLIC_URL``
(``panel_audience``). The verification is ``services/platform/hosting_panel/tickets.py``.
"""

import base64
import os
import re
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from backend.app.config import env_secret
from backend.app.config.accounts import public_url
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


# L2: the signed tickets (H-61, checkpoint 2)
PANEL_PUBLIC_KEYS_VARIABLE = "LIBREFOLIO_PANEL_PUBLIC_KEYS"
PANEL_CLOCK_SKEW_VARIABLE = "LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
#: The most keys the variable holds: enough for a rotation (the old key and the new one), with room to spare.
PANEL_PUBLIC_KEYS_MAX = 4
DEFAULT_PANEL_CLOCK_SKEW_SECONDS = 60
PANEL_CLOCK_SKEW_MAX_SECONDS = 300
_KID = re.compile(r"[A-Za-z0-9._-]{1,64}")
#: A raw Ed25519 public key (32 bytes) in base64url without padding.
_KEY = re.compile(r"[A-Za-z0-9_-]{43}")
_DEFAULT_PORTS = {"https": 443, "http": 80}


def _keys_error(message: str) -> HostingPanelConfigError:
    return HostingPanelConfigError(PANEL_PUBLIC_KEYS_VARIABLE, "PANEL_KEYS_INVALID", message)


def panel_public_keys() -> dict[str, Ed25519PublicKey] | None:
    """``LIBREFOLIO_PANEL_PUBLIC_KEYS``: the hosting panel's public keys by label, or None when unset or blank (L2 off).

    ``kid:key[,kid:key…]``: 1 to ``PANEL_PUBLIC_KEYS_MAX`` entries, spaces around them ignored; ``kid`` 1 to 64 letters,
    digits, ``.``, ``_`` or ``-``, each once; ``key`` a raw Ed25519 public key (32 bytes) in base64url without padding,
    43 characters. Not a secret: no ``_FILE``. Anything else raises ``HostingPanelConfigError`` ``PANEL_KEYS_INVALID``,
    naming the entry by its position (from 1), never a key. Read at each call, so a rotation needs no restart of the
    code that reads it.
    """
    raw = os.environ.get(PANEL_PUBLIC_KEYS_VARIABLE, "")
    if not raw.strip():
        return None
    entries = [entry.strip() for entry in raw.split(",")]
    if len(entries) > PANEL_PUBLIC_KEYS_MAX:
        raise _keys_error(f"expected at most {PANEL_PUBLIC_KEYS_MAX} entries, found {len(entries)}")
    keys: dict[str, Ed25519PublicKey] = {}
    for position, entry in enumerate(entries, start=1):
        kid, separator, text = entry.partition(":")
        if not separator or not _KID.fullmatch(kid) or not _KEY.fullmatch(text):
            raise _keys_error(f"entry {position} is not kid:key, a kid of 1 to 64 letters, digits, '.', '_' or '-' and a 43-character base64url key without padding")
        if kid in keys:
            raise _keys_error(f"entry {position} repeats the kid of an earlier entry")
        try:
            keys[kid] = Ed25519PublicKey.from_public_bytes(base64.urlsafe_b64decode(text + "="))
        except ValueError:
            raise _keys_error(f"entry {position} is not an Ed25519 public key") from None
    return keys


def panel_clock_skew_seconds() -> int:
    """``LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS``: how far a ticket's times may be off this instance's clock, 60 when unset.

    A whole number of seconds from 0 to ``PANEL_CLOCK_SKEW_MAX_SECONDS``; anything else raises
    ``HostingPanelConfigError`` ``PANEL_CLOCK_SKEW_INVALID``. Read at each call.
    """
    raw = os.environ.get(PANEL_CLOCK_SKEW_VARIABLE, "").strip()
    if not raw:
        return DEFAULT_PANEL_CLOCK_SKEW_SECONDS
    if not (raw.isascii() and raw.isdigit()) or int(raw) > PANEL_CLOCK_SKEW_MAX_SECONDS:
        raise HostingPanelConfigError(PANEL_CLOCK_SKEW_VARIABLE, "PANEL_CLOCK_SKEW_INVALID", f"expected whole seconds from 0 to {PANEL_CLOCK_SKEW_MAX_SECONDS}")
    return int(raw)


def panel_audience() -> str:
    """The audience of a ticket for this instance: the origin of ``LIBREFOLIO_PUBLIC_URL``, ``scheme://host[:port]``.

    Lower case, without the scheme's default port, a path, a query or a fragment. Without a usable public address
    (unset, not http(s), no host) it raises ``HostingPanelConfigError`` ``PANEL_AUDIENCE_UNAVAILABLE``: the tickets
    need it. The message never quotes the address.
    """
    error = HostingPanelConfigError(PUBLIC_URL_VARIABLE, "PANEL_AUDIENCE_UNAVAILABLE", "the hosting panel's tickets need LIBREFOLIO_PUBLIC_URL, an http(s) address with a host")
    try:
        url = public_url()
        parts = urlsplit(url) if url else None
        port = parts.port if parts is not None else None
    except ValueError:
        raise error from None
    if parts is None or parts.scheme.lower() not in _DEFAULT_PORTS or not parts.hostname:
        raise error
    scheme = parts.scheme.lower()
    host = parts.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    return f"{scheme}://{host}" if port in (None, _DEFAULT_PORTS[scheme]) else f"{scheme}://{host}:{port}"


def panel_public_url_path() -> str | None:
    """The path of ``LIBREFOLIO_PUBLIC_URL`` beyond the root, as written without its one trailing slash, or None.

    A ticket's audience is the origin only (``panel_audience``), so two instances on one origin under different paths
    would accept each other's tickets: one origin per instance. The startup check warns on a path. None too when the
    address is unset or cannot be used: ``panel_audience`` reports that.
    """
    try:
        url = public_url()
        path = urlsplit(url).path if url else ""
    except ValueError:
        return None
    return path if path not in ("", "/") else None
