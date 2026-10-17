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
- ``forwarded_by_untrusted_proxy(request)``: whether the request came through a reverse proxy LibreFolio does not trust
  (decision N70), whose address every visitor would share: a forwarding header (``X-Forwarded-For``, ``Forwarded``,
  ``X-Real-IP``) from a local peer, as ``classify_ip`` says (loopback, private, link-local, unique-local, CGNAT), whose
  address neither ``LIBREFOLIO_CLIENT_IP_HEADER`` nor uvicorn replaced. A limit per client address skips such a request
  rather than count every visitor together. A client on the internet can send the headers, not connect from a local
  address: from a public peer they are only noted.
- ``rate_limit_address(request)``: the address a per-client limit counts the request by, ``None`` (no count per address)
  behind such a proxy, else ``client_address(request)``. Every per-address limit takes its address here.
- ``untrusted_forwarding_seen(peer_class)``: the forwarding headers met so far from untrusted ``local`` or ``public``
  peers, which the configuration check ``platform.client_address`` reports; the first of each class is logged once.

No log record LibreFolio writes holds a client's address (decision N58): the warning names the header and its size,
never its value, and the forwarding notes hold the names of the headers alone.
"""

from __future__ import annotations

import functools
import ipaddress
from typing import Literal

from starlette.requests import HTTPConnection

from backend.app.config import get_settings
from backend.app.logging_config import get_logger
from backend.app.utils.runtime.network import classify_ip, parse_ip

logger = get_logger(__name__)

#: Holds one entry once the malformed-header warning has been logged in this process.
_warned: list[bool] = []

#: The headers in which a reverse proxy forwards a request, written as the log and the configuration check name them.
_FORWARDING_HEADERS = ("X-Forwarded-For", "Forwarded", "X-Real-IP")

#: Logged the first time in a process that a local peer nobody trusts sends forwarding headers, and the summary of the
#: configuration check ``platform.client_address`` from then on: a reverse proxy, whose address every visitor shares.
UNTRUSTED_PROXY_SUMMARY = "Requests come through a reverse proxy that LibreFolio does not trust: the limits per client address skip them. List the proxy in FORWARDED_ALLOW_IPS, or name the header it sets in LIBREFOLIO_CLIENT_IP_HEADER"
#: The same for a public peer: a client's own headers, or those of a proxy on a public address.
PUBLIC_FORWARDING_SUMMARY = "Forwarding headers from a public address were ignored: if a proxy on a public address forwards the requests, list it in FORWARDED_ALLOW_IPS"

#: The forwarding headers met in this process from peers nobody trusts, by class of peer: ``local`` (a reverse proxy
#: LibreFolio does not trust) and ``public``. Names only, never an address (decision N58).
_untrusted_forwarding: dict[str, set[str]] = {"local": set(), "public": set()}


@functools.cache
def _configured_header() -> str | None:
    """``LIBREFOLIO_CLIENT_IP_HEADER`` in lower case, ``None`` when unset: read once per process, never per request."""
    return get_settings().LIBREFOLIO_CLIENT_IP_HEADER.lower() or None


def client_address(request: HTTPConnection) -> str | None:
    """The address of the client that sent ``request``; ``None`` when the connection has none."""
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


def forwarded_by_untrusted_proxy(request: HTTPConnection) -> bool:
    """Whether ``request`` came through a reverse proxy LibreFolio does not trust, so that its address is the proxy's,
    which every visitor shares: a limit per client address skips such a request rather than count them all together
    (decision N70).

    True when the request carries a forwarding header (``X-Forwarded-For``, ``Forwarded``, ``X-Real-IP``),
    ``LIBREFOLIO_CLIENT_IP_HEADER`` does not give its address, uvicorn did not take its address from
    ``X-Forwarded-For`` (it does only for the peers ``FORWARDED_ALLOW_IPS`` trusts, and then keeps one of the header's
    addresses) and the peer is local, as ``classify_ip`` says: loopback, private, link-local, unique-local or CGNAT. A
    client on the internet can send the headers but cannot connect from a local address. From a public peer the headers
    are only noted, for the configuration check; a peer without a readable address gives ``False`` and no note.
    """
    names = [name for name in _FORWARDING_HEADERS if name in request.headers]
    if not names:
        return False
    header = _configured_header()
    if header is not None and _one_address(request.headers.getlist(header)) is not None:
        return False
    peer = request.client.host if request.client else None
    peer_class = classify_ip(peer)
    if peer_class == "unknown" or _followed_by_uvicorn(peer, request.headers.getlist("x-forwarded-for")):
        return False
    local = peer_class != "public"
    _note_untrusted_forwarding(local, names)
    return local


def rate_limit_address(request: HTTPConnection) -> str | None:
    """The address a limit per client counts ``request`` by: ``None``, which every such limit reads as «no count per
    address», when it came through a reverse proxy LibreFolio does not trust (``forwarded_by_untrusted_proxy``), whose
    address every visitor shares (decision N70); otherwise ``client_address(request)``. That one is read first, so that
    its warning on a malformed header is never hidden."""
    address = client_address(request)
    return None if forwarded_by_untrusted_proxy(request) else address


def _followed_by_uvicorn(peer: str | None, forwarded_for: list[str]) -> bool:
    """Whether uvicorn put an address of ``X-Forwarded-For`` in place of the peer, as it does for the proxies it trusts:
    the peer is then one of the header's addresses, read as uvicorn reads them (a port and brackets dropped)."""
    address = parse_ip(peer)
    return address is not None and any(parse_ip(value) == address for line in forwarded_for for value in line.split(","))


def _note_untrusted_forwarding(local: bool, names: list[str]) -> None:
    """Note the forwarding headers of a request from an untrusted peer, local or public. The first note of each class in
    this process is logged, with the names of the headers alone (N58)."""
    seen = _untrusted_forwarding["local" if local else "public"]
    first = not seen
    seen.update(names)
    if not first:
        return
    if local:
        logger.warning(UNTRUSTED_PROXY_SUMMARY, headers=", ".join(names))
    else:
        logger.info(PUBLIC_FORWARDING_SUMMARY, headers=", ".join(names))


def untrusted_forwarding_seen(peer_class: Literal["local", "public"]) -> tuple[str, ...]:
    """The forwarding headers met so far in this process from untrusted ``peer_class`` peers, in a fixed order: what the
    configuration check ``platform.client_address`` reports."""
    seen = _untrusted_forwarding[peer_class]
    return tuple(name for name in _FORWARDING_HEADERS if name in seen)
