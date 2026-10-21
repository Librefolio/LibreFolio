"""The origin of an http(s) address, in the one canonical form the server compares and writes it in.

``scheme://host[:port]``: lower case, the scheme's default port (80 for http, 443 for https) left out, an IPv6 host in
brackets, an international name in punycode, nothing of the path, the query, the fragment or a user info. A host holding
anything else (a ``;``, a quote) gives no origin: the origin is written into a header. Used for the audience of the hosting panel's
tickets (``config/hosting_panel.py``) and for the ``connect-src`` of the Content-Security-Policy
(``services/platform/security_headers.py``).
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

#: A host name as it may stand in a header: letters, digits, dots and hyphens (an international name in punycode).
_HOST_NAME = re.compile(r"[a-z0-9.-]+")
_DEFAULT_PORTS = {"https": 443, "http": 80}


def canonical_origin(url: str | None) -> str | None:
    """The canonical origin of ``url``, or None when it is not an http(s) address with a host (or its port is not one)."""
    if not url:
        return None
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in _DEFAULT_PORTS or not parts.hostname:
        return None
    host = parts.hostname.lower()
    if ":" in host:
        try:
            address = ipaddress.IPv6Address(host)
        except ValueError:
            return None
        # A zone id (fe80::1%eth0) names an interface of the client, never an origin a header may carry
        if address.scope_id is not None:
            return None
        host = f"[{host}]"
    else:
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError:
            return None
        # Nothing else may reach a header: no ';', no space, no quote (H-55 v2: the origin goes into connect-src)
        if not _HOST_NAME.fullmatch(host):
            return None
    return f"{scheme}://{host}" if port in (None, _DEFAULT_PORTS[scheme]) else f"{scheme}://{host}:{port}"
