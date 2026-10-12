"""Classify a client address for the connection-security indicator.

Only the class ever leaves the server: the address itself is neither returned nor logged.
"""

from __future__ import annotations

import ipaddress
from typing import Literal

ClientClass = Literal["loopback", "vpn", "lan", "public", "unknown"]

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address

# Tailscale and Headscale hand out the CGNAT range and one IPv6 unique-local prefix.
_VPN_NETWORKS = (ipaddress.ip_network("100.64.0.0/10"), ipaddress.ip_network("fd7a:115c:a1e0::/48"))
_LAN_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("fc00::/7"),
)


def _parse_ip(text: str | None) -> IPAddress | None:
    """An address from a header or a socket: brackets, a port and a zone id stripped; IPv4-mapped as IPv4."""
    candidate = (text or "").strip()
    if candidate.startswith("["):
        candidate = candidate[1:].split("]", 1)[0]
    elif candidate.count(":") == 1:
        candidate = candidate.split(":", 1)[0]
    candidate = candidate.split("%", 1)[0]
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


def classify_ip(address: str | None) -> ClientClass:
    """Class of an IP address, as the indicator combines it with what the browser sees.

    ``loopback`` (127/8, ::1), ``vpn`` (the CGNAT 100.64/10 of Tailscale and Headscale, and
    Tailscale's fd7a:115c:a1e0::/48), ``lan`` (private, link-local and the other unique-local
    ranges), ``public`` for every other address, ``unknown`` when there is none or it cannot be
    read. Brackets, a zone id and an IPv4-mapped IPv6 form are normalised first.
    """
    ip = _parse_ip(address)
    if ip is None or ip.is_unspecified or ip.is_multicast:
        return "unknown"
    if ip.is_loopback:
        return "loopback"
    if any(ip in network for network in _VPN_NETWORKS):
        return "vpn"
    if any(ip in network for network in _LAN_NETWORKS):
        return "lan"
    return "public"


def client_address(forwarded_for: str | None, peer: str | None) -> str | None:
    """The address to classify: the last X-Forwarded-For value when it is an IP, else the peer.

    The last value is the one the nearest proxy appended. It is advisory, never trusted: a forged
    header misleads only the sender's own indicator. Spaces, brackets and a port are stripped.
    """
    values = [value.strip() for value in (forwarded_for or "").split(",") if value.strip()]
    if values:
        last = _parse_ip(values[-1])
        if last is not None:
            return str(last)
    return peer
