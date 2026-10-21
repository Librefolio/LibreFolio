"""``backend.app.utils.runtime.origins.canonical_origin``: the one canonical form of an http(s) origin (H-55 v2).

The origin of an address is compared by the server (the audience of the hosting panel's tickets) and written into a
header (the ``connect-src`` of the Content-Security-Policy). The contract pinned here:

1. ``scheme://host[:port]``: scheme and host in lower case, the scheme's default port (80 for http, 443 for https)
   left out, any other port kept, nothing of the path, the query, the fragment, a trailing slash or a user info.
2. An IPv4 host stays as it is; an IPv6 host stays in brackets with its port; an international name is given in
   punycode (``https://münchen.de`` → ``https://xn--mnchen-3ya.de``).
3. ``None`` for nothing, blank, a scheme that is not http(s) (or no scheme), no host, a port that is not a number or out
   of range.
4. The hardening: the origin is written into a header, so a host holding anything outside letters, digits, dots and
   hyphens (a ``;``, a space, a quote, a comma) gives no origin, and neither does an IPv6-looking host that is not an
   address. A directive injection such as ``http://a;script-src *`` therefore never reaches the policy.
5. Property: an accepted origin holds no character outside ``[a-z0-9.:/\\[\\]-]``, and canonicalising it again changes
   nothing.

Pure: no database, no server, no network, no environment read. The hardening is already in the module: this file is its
regression test and is green on arrival.
"""

from __future__ import annotations

import re

import pytest

from backend.app.utils.runtime.origins import canonical_origin
from backend.test_scripts.test_utils import print_section, print_success

#: The only characters an accepted origin may hold (a letter, a digit, a dot, a colon, a slash, a bracket, a hyphen).
SAFE_ORIGIN = re.compile(r"[a-z0-9.:/\[\]-]+")

#: (input, canonical origin): every case the module accepts, each pinned to its exact answer.
ACCEPTED = [
    pytest.param("https://folio.example.com", "https://folio.example.com", id="plain-https"),
    pytest.param("http://folio.example.com", "http://folio.example.com", id="plain-http"),
    pytest.param("HTTPS://Folio.Example.COM", "https://folio.example.com", id="scheme-and-host-lower-cased"),
    pytest.param("https://folio.example.com:443", "https://folio.example.com", id="https-default-port-dropped"),
    pytest.param("http://folio.example.com:80", "http://folio.example.com", id="http-default-port-dropped"),
    pytest.param("http://folio.example.com:443", "http://folio.example.com:443", id="https-port-kept-on-http"),
    pytest.param("https://folio.example.com:80", "https://folio.example.com:80", id="http-port-kept-on-https"),
    pytest.param("https://folio.example.com:8443", "https://folio.example.com:8443", id="other-port-kept"),
    pytest.param("http://localhost:6040", "http://localhost:6040", id="localhost-port-kept"),
    pytest.param("http://folio.example.com:65535", "http://folio.example.com:65535", id="highest-port-kept"),
    pytest.param("https://folio.example.com/", "https://folio.example.com", id="trailing-slash-dropped"),
    pytest.param("https://folio.example.com/a/b/c", "https://folio.example.com", id="path-dropped"),
    pytest.param("https://folio.example.com?next=%2Fx", "https://folio.example.com", id="query-dropped"),
    pytest.param("https://folio.example.com#section", "https://folio.example.com", id="fragment-dropped"),
    pytest.param("https://folio.example.com:8443/a/b?x=1&y=2#f", "https://folio.example.com:8443", id="path-query-fragment-dropped"),
    pytest.param("https://user:secret@folio.example.com/x", "https://folio.example.com", id="user-info-dropped"),
    pytest.param("http://192.168.1.10", "http://192.168.1.10", id="ipv4"),
    pytest.param("http://192.168.1.10:8080/x", "http://192.168.1.10:8080", id="ipv4-with-port"),
    pytest.param("https://10.0.0.1:443", "https://10.0.0.1", id="ipv4-default-port-dropped"),
    pytest.param("http://[::1]", "http://[::1]", id="ipv6-loopback-in-brackets"),
    pytest.param("http://[::1]:6040", "http://[::1]:6040", id="ipv6-with-port"),
    pytest.param("http://[::1]:80/x", "http://[::1]", id="ipv6-default-port-dropped"),
    pytest.param("https://[2001:DB8::1]:8443", "https://[2001:db8::1]:8443", id="ipv6-lower-cased"),
    pytest.param("https://münchen.de", "https://xn--mnchen-3ya.de", id="international-name-in-punycode"),
    pytest.param("https://MÜNCHEN.de:8443/x", "https://xn--mnchen-3ya.de:8443", id="international-name-lower-cased-first"),
    pytest.param("https://xn--mnchen-3ya.de", "https://xn--mnchen-3ya.de", id="punycode-name-unchanged"),
    pytest.param("https://my-host.example.com", "https://my-host.example.com", id="hyphen-in-name"),
]

#: Inputs that give no origin: nothing, not http(s), no host, a bad port.
REFUSED_SHAPE = [
    pytest.param(None, id="none"),
    pytest.param("", id="empty"),
    pytest.param("ftp://folio.example.com", id="ftp"),
    pytest.param("ftp://x", id="ftp-short"),
    pytest.param("ws://folio.example.com", id="websocket"),
    pytest.param("javascript:alert(1)", id="javascript-scheme"),
    pytest.param("folio.example.com", id="no-scheme"),
    pytest.param("folio.example.com:8080", id="no-scheme-with-port"),
    pytest.param("//folio.example.com", id="scheme-relative"),
    pytest.param("https://", id="no-host"),
    pytest.param("https:///path", id="no-host-with-path"),
    pytest.param("https://:443", id="port-without-host"),
    pytest.param("https://folio.example.com:abc", id="port-not-a-number"),
    pytest.param("https://folio.example.com:-1", id="port-negative"),
    pytest.param("https://folio.example.com:65536", id="port-above-range"),
    pytest.param("https://folio.example.com:99999", id="port-far-above-range"),
]

#: Hosts that must never reach a Content-Security-Policy header (H-55 v2).
REFUSED_HARDENING = [
    pytest.param("http://a;script-src *", id="directive-injection"),
    pytest.param("http://a;script-src", id="directive-injection-no-space"),
    pytest.param("https://folio.example.com;script-src", id="semicolon-after-name"),
    pytest.param("https://a;b.example.com:8443", id="semicolon-with-port"),
    pytest.param("http://a;b", id="semicolon"),
    pytest.param("https://evil.com;connect-src *;", id="semicolon-trailing"),
    pytest.param('https://a"b.example.com', id="double-quote"),
    pytest.param("https://a'b.example.com", id="single-quote"),
    pytest.param("https://a,b.example.com", id="comma"),
    pytest.param("https://a.example.com,https://b.example.com", id="two-hosts-with-comma"),
    pytest.param("https://a b.example.com", id="space"),
    pytest.param("https://folio.example.com'", id="trailing-single-quote"),
    pytest.param("https://user@a;b.com", id="semicolon-behind-user-info"),
]

#: IPv6-looking hosts that are not an IPv6 address.
REFUSED_IPV6 = [
    pytest.param("http://[not:an:address]", id="words-in-brackets"),
    pytest.param("http://[1:2:3]", id="too-few-groups"),
    pytest.param("http://[zz::1]:80", id="non-hex-group"),
    pytest.param("http://[::1;script-src]", id="directive-in-brackets"),
    pytest.param("http://[::1", id="unclosed-bracket"),
    pytest.param("http://[fe80::1%25eth0]", id="a-zone-id-percent-encoded"),
    pytest.param("http://[fe80::1%eth0]:80", id="a-zone-id"),
    pytest.param("http://[v1.fe80::a+en1]", id="ipvfuture-literal"),
]


@pytest.mark.parametrize(("url", "expected"), ACCEPTED)
def test_canonical_form(url: str, expected: str) -> None:
    """ORG-001: an http(s) address with a host gives its canonical origin."""
    print_section(f"ORG-001: canonical origin of {url!r}")
    assert canonical_origin(url) == expected
    print_success(f"{url!r} → {expected!r}")


@pytest.mark.parametrize("url", REFUSED_SHAPE)
def test_no_origin_for_a_wrong_shape(url: str | None) -> None:
    """ORG-002: nothing, a scheme that is not http(s), no host or a bad port gives None."""
    print_section(f"ORG-002: no origin for {url!r}")
    assert canonical_origin(url) is None
    print_success(f"{url!r} → None")


@pytest.mark.parametrize("url", REFUSED_HARDENING)
def test_no_origin_for_a_host_that_could_inject_into_a_header(url: str) -> None:
    """ORG-003: a host holding ``;``, a space, a quote or a comma gives None (H-55 v2)."""
    print_section(f"ORG-003: hardening, no origin for {url!r}")
    assert canonical_origin(url) is None
    print_success(f"{url!r} → None")


@pytest.mark.parametrize("url", REFUSED_IPV6)
def test_no_origin_for_an_ipv6_looking_host_that_is_not_an_address(url: str) -> None:
    """ORG-004: a host in brackets that is not an IPv6 address gives None."""
    print_section(f"ORG-004: no origin for {url!r}")
    assert canonical_origin(url) is None
    print_success(f"{url!r} → None")


def test_an_accepted_origin_holds_only_safe_characters() -> None:
    """ORG-005: for every accepted case, the result holds nothing outside ``[a-z0-9.:/\\[\\]-]``."""
    print_section("ORG-005: accepted origins hold only header-safe characters")
    for case in ACCEPTED:
        url = case.values[0]
        origin = canonical_origin(url)
        assert origin is not None, f"{url!r} should be accepted"
        assert SAFE_ORIGIN.fullmatch(origin), f"{url!r} → {origin!r} holds a character outside the safe set"
    print_success(f"{len(ACCEPTED)} accepted origins checked")


def test_canonicalising_an_origin_again_changes_nothing() -> None:
    """ORG-006: an origin is a fixed point: the stored form compares equal to itself."""
    print_section("ORG-006: canonical_origin is idempotent")
    for case in ACCEPTED:
        url = case.values[0]
        origin = canonical_origin(url)
        assert origin is not None, f"{url!r} should be accepted"
        assert canonical_origin(origin) == origin, f"{url!r} → {origin!r} is not stable"
    print_success(f"{len(ACCEPTED)} origins stable")


def test_equivalent_spellings_give_one_origin() -> None:
    """ORG-007: the spellings the server compares (case, default port, trailing path) meet in one string."""
    print_section("ORG-007: equivalent spellings meet in one origin")
    spellings = [
        "https://folio.example.com",
        "HTTPS://FOLIO.EXAMPLE.COM/",
        "https://folio.example.com:443",
        "https://Folio.Example.com:443/dashboard?tab=1#top",
    ]
    assert {canonical_origin(s) for s in spellings} == {"https://folio.example.com"}
    print_success("four spellings → https://folio.example.com")
