"""The address of the client that sent a request, for the per-client limits: decision P17.

Owner: workstream H (platform). Behind a reverse proxy the connection comes from the proxy, so every visitor would share
its address and a limit per client would count them all together. A proxy LibreFolio can trust passes the visitor's
address in a header it sets itself and never takes from the client: Fly.io's ``Fly-Client-IP``, or ``X-Real-IP`` that
Nginx sets from ``$remote_addr``. ``LIBREFOLIO_CLIENT_IP_HEADER`` names that header. Empty, the default, the address is
the connection's, as uvicorn gives it: uvicorn already follows ``X-Forwarded-For`` from the proxies that
``FORWARDED_ALLOW_IPS`` trusts.

Set it only when every request crosses that proxy: a client that reached LibreFolio directly could send the header
itself and choose any address. No profile sets it: a hosting provider names the header of its own proxy (the cloud on
Fly.io sets ``Fly-Client-IP``, decision P17).

- ``client_address(request)``: the header's address when the request carries the header once, holding one IP address;
  otherwise the connection's address. A malformed header logs one warning per process, which never holds the value.
- ``client_rate_key(address)``: the key of an address for a per-client limit. An IPv6 client counts by its /64, which
  one subscriber usually holds whole.
- ``mask_client_address(address)``: the form an address may take in a log, IPv4 by its /24 and IPv6 by its /48. An IP
  address is personal data, and a log does not need it whole.
"""

from __future__ import annotations

import functools
import ipaddress

from starlette.requests import HTTPConnection

from backend.app.config import get_settings
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

#: Holds one entry once the malformed-header warning has been logged in this process.
_warned: list[bool] = []


@functools.cache
def _configured_header() -> str | None:
    """``LIBREFOLIO_CLIENT_IP_HEADER`` in lower case, ``None`` when unset: read once per process, never per request."""
    return get_settings().LIBREFOLIO_CLIENT_IP_HEADER.lower() or None


def reset_client_address_cache() -> None:
    """Read the variable again at the next call, and re-arm the warning: for the tests."""
    _configured_header.cache_clear()
    _warned.clear()


def client_address(request: HTTPConnection) -> str | None:
    """The address of the client that sent ``request``; ``None`` when the connection has none (a test client)."""
    peer = request.client.host if request.client else None
    header = _configured_header()
    if header is None:
        return peer
    values = request.headers.getlist(header)
    if not values:
        return peer
    address = _one_address(values)
    if address is None:
        _report_unusable(header, values)
        return peer
    return address


def _one_address(values: list[str]) -> str | None:
    """The one IP address the header lines hold, normalised; ``None`` for anything else."""
    if len(values) != 1:
        return None
    raw = values[0].strip()
    # A zone names an interface of the proxy's own host, never a remote client
    if not raw or "%" in raw:
        return None
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return str(ip.ipv4_mapped)
    return str(ip)


def _report_unusable(header: str, values: list[str]) -> None:
    """Log once per process that the header cannot be used: its name and size, never its value."""
    if _warned:
        return
    _warned.append(True)
    logger.warning("Client address header unusable: using the connection's address", header=header, lines=len(values), length=sum(len(value) for value in values))


def client_rate_key(address: str | None) -> str | None:
    """The key of ``address`` for a per-client limit: an IPv4 address as is, an IPv6 one by its /64, anything else
    (a name, a unix socket) as written; ``None`` without an address, an empty one included."""
    if not address:
        return None
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return address
    if not isinstance(ip, ipaddress.IPv6Address):
        return str(ip)
    if ip.ipv4_mapped is not None:
        return str(ip.ipv4_mapped)
    # From the integer, so a zone (``fe80::1%eth0``) does not get in the way.
    return str(ipaddress.IPv6Network((int(ip) >> 64 << 64, 64)))


def mask_client_address(address: str | None) -> str | None:
    """The form of ``address`` for a log: an IPv4 address by its /24, an IPv6 one by its /48, anything else as written;
    ``None`` without an address."""
    if not address:
        return None
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return address
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if isinstance(ip, ipaddress.IPv4Address):
        return str(ipaddress.IPv4Network((int(ip) >> 8 << 8, 24)))
    return str(ipaddress.IPv6Network((int(ip) >> 80 << 80, 48)))
