"""
The client address behind a trusted proxy (workstream H, platform, item P17 of release 1.3.0).

Under test: the setting ``LIBREFOLIO_CLIENT_IP_HEADER`` of ``Settings`` (``backend/app/config/__init__.py``) and the new
module ``backend/app/services/platform/client_address.py``. The contract:

(a) The setting is a ``str``, ``""`` in the code. It is stripped, and empty or blank means unset. Otherwise it must be an
    HTTP header name, a token (a fullmatch of ``^[!#$%&'*+.^_`|~0-9A-Za-z-]+$``, ASCII only): a space, a colon, a slash,
    a comma, a tab or a line break inside, quotes, ``=``, a non-ASCII letter or digit make ``Settings`` raise a
    ``pydantic.ValidationError`` whose message names ``LIBREFOLIO_CLIENT_IP_HEADER``. ``X-Forwarded-For`` and
    ``Forwarded``, in any case, are refused the same way, the message naming ``FORWARDED_ALLOW_IPS`` too: they are lists
    whose first value the client chooses, and uvicorn already reads them from the proxies it trusts. A valid name is kept
    as written, stripped, its case kept.
(b) No profile sets it (decision P17, point 4: the cloud sets it in its own environment). ``PROFILE_DEFAULTS`` lists it
    for no profile; unset, it is ``""`` under every profile, ``managed`` included, and ``client_address`` then reads the
    peer whatever client-address headers a request carries.
(c) ``client_address(connection)``, for a Starlette ``HTTPConnection``: a ``Request`` and a ``WebSocket`` alike. Unset
    (also empty or blank): ``connection.client.host`` exactly as it is, never normalised (``testclient`` as written), or
    ``None`` without a client, and no header is read. Set: the configured name matches the header whatever the case it
    is written in; one line whose stripped value is one IP address gives that address normalised,
    ``str(ipaddress.ip_address(value))`` (an IPv4-mapped IPv6 address as its IPv4, IPv6 compressed, in lower case), with a
    client or without; the header absent gives the peer as it is (``None`` without a client), without a warning.
(d) A malformed header gives the peer as it is (``None`` without a client) and one warning per process, through the
    module's ``logger``: ``logger.warning("Client address header unusable: using the connection's address",
    header=<the configured name in lower case>, lines=<its number of lines>, length=<the characters of their values>)``,
    word for word, and no other field. Malformed: two lines or more (even valid, even identical, even one of them empty),
    a comma-separated list, an address with a port, brackets (with a port or without), a zone id, a leading zero, empty
    or blank, text, a space inside, a network. ``length`` counts the values as received, spaces included. No log record,
    at any level, holds a value of the header nor an address inside one. Another malformed request warns no more, and a
    usable or absent header re-arms nothing: a new process starts over, and warns again. The tests reproduce one by
    clearing ``_configured_header()``'s cache and emptying ``_warned`` (N58: no production reset).
(e) The configured name is read once per process: after the first call, a change of the environment changes nothing
    until a new process starts over, and its first call reads it; the tests reproduce one as in (d). Every way: another
    name, set, unset.
(f) ``client_rate_key(address)``, the key of an address for a per-client limit: no key for ``None`` nor ``""``; an
    IPv4 address as is; an IPv4-mapped one as its IPv4; any other IPv6 address by its /64, in canonical form, a zone
    ignored; anything else as written. The values are pinned here, one by one.
(g) Nothing in the module exists only for the tests (N58, H-22): no ``reset_client_address_cache()``, since the tests
    start the module's state over themselves, and no ``mask_client_address()``, since no log writes a client's address,
    so it has no caller. Red until H-22 removes both.
(h) ``forwarded_by_untrusted_proxy(connection)`` (H-36, decision N70), a ``Request`` and a ``WebSocket`` alike: whether
    the request came through a local reverse proxy LibreFolio does not trust, behind which every visitor has the proxy's
    address (R13-SEC6), so that the per-address limits skip it. In order: no forwarding header (``X-Forwarded-For``,
    ``Forwarded``, ``X-Real-IP``: a line of any of them, in any case, whatever its value, even empty) is ``False``; the
    configured header carried once and holding one IP address, as ``client_address`` reads it, is ``False``, while
    absent or unusable it is as if unset, and only ``client_address`` warns about it; a peer ``classify_ip`` calls
    ``unknown`` (no client, ``testclient``, ``0.0.0.0``, ``::``, multicast) is ``False``; a peer uvicorn took from
    ``X-Forwarded-For``, equal through ``parse_ip`` to one value of its lines (brackets, a port and an IPv4-mapped form
    undone), is ``False``; then a loopback, LAN or VPN peer (an IPv4-mapped one as its IPv4) is ``True`` and a public
    one ``False``. Only these two last outcomes note the forwarding headers the request carries, in
    ``_untrusted_forwarding["local"]`` or ``["public"]``, and the first noting of each class in the process logs one
    record through the module's ``logger``, word for word: ``logger.warning(UNTRUSTED_PROXY_SUMMARY, headers=...)`` for
    ``local``, ``logger.info(PUBLIC_FORWARDING_SUMMARY, headers=...)`` for ``public``, ``headers`` being this request's
    names in the order X-Forwarded-For, Forwarded, X-Real-IP, joined by ``", "``, and no other field. A later noting of
    a class logs nothing and only adds its names; each class logs its own first one. The names noted come back from
    ``untrusted_forwarding_seen(peer_class)`` in that order, ``()`` before any. ``rate_limit_address(connection)``, the
    address every per-address limit counts a request by: ``None`` when the request came through such a proxy,
    otherwise exactly ``client_address(connection)``, which it calls first, so the warning of (d) is never hidden;
    nothing else is logged. Behind uvicorn's own ``ProxyHeadersMiddleware``, a proxy ``FORWARDED_ALLOW_IPS`` trusts
    gives ``False`` and one it does not trust gives ``True``, and the configuration check ``check_client_address`` then
    warns the admin. No log record holds an address (N58). Red until H-36 lands; (a) to (g) do not depend on it.

How. Every test runs with ``LIBREFOLIO_TEST_MODE=1`` (``get_settings()`` reads no ``.env``), ``LIBREFOLIO_TEST_DATA_DIR``
under ``tmp_path`` (``get_settings()`` never looks at the lane's data), the profile and the setting removed, all through
``monkeypatch``. Before and after each test the module's state starts over as a new process finds it, the last time
with the environment of the run put back, so that no test inherits the name another read nor the warning another
spent: the tests clear ``_configured_header()``'s cache and empty ``_warned``, the module's own list, in place (N58: no
production reset). A case that configures the setting checks first that ``get_settings()`` reads it so (a barrier),
then starts the module's state over: the next call reads the name. ``Settings`` itself is built with ``_env_file=None``.
A connection is a Starlette ``Request`` or ``WebSocket`` on a raw scope, no server: header names in lower case, as
uvicorn puts them there (h11 and httptools lower-case every name, and Starlette's ``Headers`` compares lower-case names),
a repeated header as repeated lines, another header between them as when a proxy appends its own. The module's
``logger`` is replaced by a recorder of ``(level, summary, fields)``. The module is imported when a test runs and the
setting is looked up in ``Settings.model_fields``, so this file collects before either exists and each test fails on its
own barrier: ``backend/app/services/platform/client_address.py is missing (P17)``, or ``LIBREFOLIO_CLIENT_IP_HEADER is
not a Settings field (P17)``. Red until P17 lands. The tests of (h) also start ``_untrusted_forwarding`` over themselves,
emptying its two sets in place before and after each test (their own fixture; H-22: no production reset), and drive
uvicorn's ``ProxyHeadersMiddleware`` on a raw scope with ``asyncio.run``. Before H-36 that fixture fails on its barrier,
``backend/app/services/platform/client_address.py has no _untrusted_forwarding, ... (H-36, N70)``, and only the (h) tests
use it. No DB, no server, no network, no clock.
"""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pydantic import ValidationError
from pydantic.fields import FieldInfo
from starlette.requests import HTTPConnection, Request
from starlette.websockets import WebSocket
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from backend.app import config
from backend.test_scripts.test_utils import print_section, print_success

HEADER_VARIABLE = "LIBREFOLIO_CLIENT_IP_HEADER"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
#: uvicorn's own variable: the proxies whose X-Forwarded-For and Forwarded it follows.
TRUSTED_PROXIES_VARIABLE = "FORWARDED_ALLOW_IPS"

MODULE = "backend.app.services.platform.client_address"
MODULE_PATH = "backend/app/services/platform/client_address.py"
#: The two barriers of the red run, word for word.
MISSING_MODULE = f"{MODULE_PATH} is missing (P17)"
MISSING_FIELD = f"{HEADER_VARIABLE} is not a Settings field (P17)"

#: (d): the summary of the one warning, word for word.
UNUSABLE = "Client address header unusable: using the connection's address"
#: The levels a header that is usable, absent or not read at all must not reach.
ALERT_LEVELS = ("warning", "error", "exception", "critical")

#: The TCP peer of most cases, as uvicorn gives it: (host, port).
PEER: tuple[str, int] = ("10.0.0.1", 1234)
PEER_HOST = PEER[0]
#: The header of most cases, as an operator writes it, and as the warning names it.
FLY = "Fly-Client-IP"
FLY_LOWER = "fly-client-ip"

Header = tuple[str, str]
Record = tuple[str, str, dict[str, Any]]

#: The client-address headers of other proxies and CDNs, each with an address of its own, and the two lists uvicorn reads.
OTHER_CLIENT_HEADERS: tuple[Header, ...] = (
    ("CF-Connecting-IP", "198.51.100.9"),
    ("X-Real-IP", "192.0.2.1"),
    ("True-Client-IP", "192.0.2.55"),
    ("X-Forwarded-For", "192.0.2.44, 198.51.100.200"),
    ("Forwarded", "for=192.0.2.66"),
)
#: Those and Fly-Client-IP: the answer to a request carrying them all tells which one, if any, was read.
EVERY_CLIENT_HEADER: tuple[Header, ...] = ((FLY, "203.0.113.7"), *OTHER_CLIENT_HEADERS)


# =============================================================================
# FIXTURES
# =============================================================================


def start_over() -> None:
    """The module's state as a new process finds it: ``_configured_header()``'s cache cleared, so the next call reads the
    name again, and ``_warned`` emptied, so the next malformed header warns again. The module's own list, emptied in
    place: whatever runs next finds it empty too. No production function does this for the tests (N58): they start the
    module's state over themselves. Before the module exists, nothing: each test then fails on its own barrier, never in
    a fixture."""
    try:
        module = importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != MODULE:  # the module is there and something it imports is not: that error is the finding
            raise
        return
    module._configured_header.cache_clear()
    module._warned.clear()


@pytest.fixture
def fresh_client_address_cache() -> Iterator[None]:
    """The module's state started over before and after the test (``start_over``): no test inherits the name another read
    nor the warning another spent, and whatever runs after this file finds the module as a new process does."""
    start_over()
    yield
    start_over()


@pytest.fixture(autouse=True)
def environment(fresh_client_address_cache: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test mode, a data directory under ``tmp_path``, the profile and the setting unset. Set up after
    ``fresh_client_address_cache`` (its first argument), and so put back before it: the last reset of a test runs with the
    environment of the run restored."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")  # get_settings() reads no .env in test mode: only this environment
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))  # get_settings() never looks at the lane's data
    for name in (HEADER_VARIABLE, PROFILE_VARIABLE):
        monkeypatch.delenv(name, raising=False)


# =============================================================================
# THE MODULE OF P17, IMPORTED WHEN A TEST RUNS
# =============================================================================


def client_address_module() -> ModuleType:
    """The module of P17: before it exists, the test that asks for it fails here, and only that test."""
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != MODULE:  # the module is there and something it imports is not: that error is the finding
            raise
        raise AssertionError(MISSING_MODULE) from None


def function_of(module: ModuleType, name: str) -> Callable[..., Any]:
    """The function ``name`` of the module of P17."""
    function = getattr(module, name, None)
    assert callable(function), f"{MODULE_PATH} has no function {name}() (P17)"
    return function


class LogRecorder:
    """Stands in for the module's structlog logger: one ``(level, summary, fields)`` per call, at every level."""

    def __init__(self) -> None:
        self.records: list[Record] = []

    def debug(self, event: str, **fields: Any) -> None:
        self.records.append(("debug", event, fields))

    def info(self, event: str, **fields: Any) -> None:
        self.records.append(("info", event, fields))

    def warning(self, event: str, **fields: Any) -> None:
        self.records.append(("warning", event, fields))

    def error(self, event: str, **fields: Any) -> None:
        self.records.append(("error", event, fields))

    def exception(self, event: str, **fields: Any) -> None:
        self.records.append(("exception", event, fields))

    def critical(self, event: str, **fields: Any) -> None:
        self.records.append(("critical", event, fields))

    def at(self, *levels: str) -> list[Record]:
        """The records of these levels, in the order they were logged."""
        return [record for record in self.records if record[0] in levels]


def record_logs(monkeypatch: pytest.MonkeyPatch, module: ModuleType) -> LogRecorder:
    """The module's ``logger`` replaced by a recorder, for this test only."""
    assert hasattr(module, "logger"), f"{MODULE_PATH} has no module-level logger: its warning goes through the module's structlog logger (P17)"
    recorder = LogRecorder()
    monkeypatch.setattr(module, "logger", recorder)
    return recorder


@dataclass(frozen=True)
class UnderTest:
    """What the cases of ``client_address`` call, and the recorder in place of the module's logger."""

    client_address: Callable[[HTTPConnection], str | None]
    reset: Callable[[], None]
    log: LogRecorder


def under_test(monkeypatch: pytest.MonkeyPatch) -> UnderTest:
    """``client_address``, and ``start_over`` as its reset (N58: the module has none for the tests), the module's logger
    recorded."""
    module = client_address_module()
    return UnderTest(function_of(module, "client_address"), start_over, record_logs(monkeypatch, module))


# =============================================================================
# THE SETTING, LOOKED UP WHEN A TEST RUNS
# =============================================================================


def header_field() -> FieldInfo:
    """The field of P17 in ``Settings``: before it exists, the test that asks for it fails here, and only that test."""
    fields = config.Settings.model_fields
    assert HEADER_VARIABLE in fields, MISSING_FIELD
    return fields[HEADER_VARIABLE]


def set_or_unset(monkeypatch: pytest.MonkeyPatch, name: str, value: str | None) -> None:
    """``name`` set to ``value``, or removed when ``value`` is ``None``."""
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def settings_from_the_environment() -> config.Settings:
    """``Settings`` from this environment alone: the instance's ``.env`` is never read."""
    return config.Settings(_env_file=None)


def setting_of(settings: config.Settings) -> object:
    """The value of the setting in ``settings``."""
    assert HEADER_VARIABLE in type(settings).model_fields, MISSING_FIELD
    return getattr(settings, HEADER_VARIABLE)


def refusal_of(written: str) -> str:
    """The message of the ``ValidationError`` ``Settings`` raises with the setting written so; a failure if it is accepted."""
    try:
        settings = settings_from_the_environment()
    except ValidationError as exc:
        return str(exc)
    pytest.fail(f"{HEADER_VARIABLE}={written!r} was accepted, kept as {setting_of(settings)!r}: Settings must refuse it when it is built", pytrace=False)


def configure(monkeypatch: pytest.MonkeyPatch, api: UnderTest, written: str | None, profile: str | None = None) -> None:
    """Make ``written`` the setting and ``profile`` the profile (``None``: unset), check that ``get_settings()`` reads them
    so, then start the module's state over, as in a new process: the next call reads the name, and it is this one."""
    set_or_unset(monkeypatch, HEADER_VARIABLE, written)
    set_or_unset(monkeypatch, PROFILE_VARIABLE, profile)

    settings = config.get_settings()

    resolved, expected = setting_of(settings), (written or "").strip()
    assert resolved == expected, f"barrier: with {HEADER_VARIABLE}={written!r}, get_settings() reads {resolved!r}, not {expected!r}"
    assert settings.LIBREFOLIO_PROFILE == (profile or "selfhosted"), f"barrier: with {PROFILE_VARIABLE}={profile!r}, get_settings() reads the profile {settings.LIBREFOLIO_PROFILE!r}"
    api.reset()


# =============================================================================
# CONNECTIONS ON A RAW SCOPE, NO SERVER
# =============================================================================


def raw_headers(headers: Sequence[Header]) -> list[tuple[bytes, bytes]]:
    """Header lines as uvicorn puts them in the scope: the name in lower case (h11 and httptools lower-case every name, and
    Starlette's ``Headers`` compares lower-case names), the value as sent, every line kept, in order."""
    return [(name.lower().encode("latin-1"), value.encode("latin-1")) for name, value in headers]


def http_request(headers: Sequence[Header] = (), client: tuple[str, int] | None = PEER) -> Request:
    """A ``GET /`` from ``client`` (``None``: no client), carrying ``headers``."""
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw_headers(headers), "client": client, "query_string": b""})


async def _never_receive() -> dict[str, Any]:
    raise AssertionError("client_address must not read from the WebSocket")


async def _never_send(message: dict[str, Any]) -> None:
    raise AssertionError(f"client_address must not write to the WebSocket: {message}")


def websocket(headers: Sequence[Header] = (), client: tuple[str, int] | None = PEER) -> WebSocket:
    """A WebSocket handshake on ``/`` from ``client``, carrying ``headers``: it is never read nor written."""
    return WebSocket({"type": "websocket", "path": "/", "headers": raw_headers(headers), "client": client, "query_string": b""}, receive=_never_receive, send=_never_send)


def header_lines(name: str, lines: Sequence[str]) -> list[Header]:
    """``lines`` of the header ``name``, with another header before the first and after each: a proxy appends its own line
    after the client's, so a header is never assumed to come first, nor its lines to be adjacent."""
    headers: list[Header] = [("Accept", "*/*")]
    for line in lines:
        headers.extend([(name, line), ("User-Agent", "librefolio-test")])
    return headers


# =============================================================================
# ASSERTION HELPERS
# =============================================================================


def exactly(actual: object, expected: object) -> bool:
    """Equal, and of the very same type: a ``str`` and never an ``IPv4Address`` for an address, ``None`` and never ``""``."""
    return type(actual) is type(expected) and actual == expected


def unusable(header: str, lines: Sequence[str]) -> Record:
    """The warning of a malformed header: the configured name in lower case, the number of lines, and the characters of
    their values as received, spaces included."""
    return ("warning", UNUSABLE, {"header": header, "lines": len(lines), "length": sum(len(line) for line in lines)})


def leaks(records: Sequence[Record], lines: Sequence[str], hidden: Sequence[str]) -> list[tuple[str, Record]]:
    """Every ``(text, record)`` where a record holds a value of the header (one that is not blank) or an address inside one."""
    texts = sorted({line.strip() for line in lines if line.strip()} | set(hidden))
    return [(text, record) for record in records for text in texts if text in record[1] or any(text in f"{key}={value}" for key, value in record[2].items())]


# =============================================================================
# (a) THE SETTING
# =============================================================================


def test_the_setting_is_a_string_empty_in_the_code() -> None:
    print_section(f"Settings.{HEADER_VARIABLE}")

    info = header_field()

    assert info.annotation is str, f"Settings.{HEADER_VARIABLE} is a {info.annotation!r}, not a str"
    assert exactly(info.default, "") and not info.is_required(), f"Settings.{HEADER_VARIABLE} defaults to {info.default!r} in the code (required: {info.is_required()}): unset is the empty string, and the peer is used"
    print_success("✓ str, ''")


#: The setting while it is unset: removed, empty, blank.
UNSET = [
    pytest.param(None, id="unset"),
    pytest.param("", id="empty"),
    pytest.param("   ", id="blank"),
    pytest.param(" \t ", id="spaces-and-a-tab"),
]


@pytest.mark.parametrize("written", UNSET)
def test_empty_or_blank_is_unset(monkeypatch: pytest.MonkeyPatch, written: str | None) -> None:
    print_section(f"{HEADER_VARIABLE}={written!r}")
    header_field()
    set_or_unset(monkeypatch, HEADER_VARIABLE, written)

    settings = settings_from_the_environment()

    value = setting_of(settings)
    assert exactly(value, ""), f"{HEADER_VARIABLE}={written!r} is read as {value!r}: empty or blank means unset, the empty string"
    print_success("✓ ''")


#: Header names as an operator writes them, and as the setting keeps them: stripped, the case kept.
HEADER_NAMES = [
    pytest.param("Fly-Client-IP", "Fly-Client-IP", id="fly"),
    pytest.param("fly-client-ip", "fly-client-ip", id="lower-case-kept"),
    pytest.param("CF-CONNECTING-IP", "CF-CONNECTING-IP", id="upper-case-kept"),
    pytest.param("  X-Real-IP\t", "X-Real-IP", id="stripped"),
    pytest.param("True-Client-IP", "True-Client-IP", id="true-client-ip"),
    pytest.param("X_Client.IP~2", "X_Client.IP~2", id="underscore-dot-tilde"),
    pytest.param("!#$%&'*+-.^_`|~09AZaz", "!#$%&'*+-.^_`|~09AZaz", id="every-kind-of-token-character"),
]


@pytest.mark.parametrize(("written", "kept"), HEADER_NAMES)
def test_a_header_name_is_kept_as_written_stripped(monkeypatch: pytest.MonkeyPatch, written: str, kept: str) -> None:
    print_section(f"{HEADER_VARIABLE}={written!r}")
    header_field()
    monkeypatch.setenv(HEADER_VARIABLE, written)

    settings = settings_from_the_environment()

    value = setting_of(settings)
    assert exactly(value, kept), f"{HEADER_VARIABLE}={written!r} is kept as {value!r}, not {kept!r}: stripped, and in the case it is written in"
    print_success(f"✓ {value!r}")


#: Not an HTTP header name: a token is made of ASCII letters, digits and !#$%&'*+-.^_`|~ only.
NOT_A_HEADER_NAME = [
    pytest.param("Client IP", id="a-space"),
    pytest.param("Client-IP:", id="a-colon"),
    pytest.param("Client/IP", id="a-slash"),
    pytest.param("Client,IP", id="a-comma"),
    pytest.param("Client\tIP", id="a-tab-inside"),
    pytest.param("Client\nIP", id="a-line-break-inside"),
    pytest.param('"Client-IP"', id="quotes"),
    pytest.param("Client=IP", id="an-equals-sign"),
    pytest.param("Cl\u00efent-IP", id="a-non-ascii-letter"),
    pytest.param("Client-IP\u0663", id="a-non-ascii-digit"),
]


@pytest.mark.parametrize("written", NOT_A_HEADER_NAME)
def test_a_value_that_is_not_a_header_name_is_refused(monkeypatch: pytest.MonkeyPatch, written: str) -> None:
    print_section(f"{HEADER_VARIABLE}={written!r}")
    header_field()
    monkeypatch.setenv(HEADER_VARIABLE, written)

    message = refusal_of(written)

    assert HEADER_VARIABLE in message, f"{HEADER_VARIABLE}={written!r} is refused, but the message does not name the variable: {message}"
    print_success("✓ refused, naming the variable")


#: The two lists uvicorn reads itself, from the proxies it trusts, in any case.
FORWARDED_LISTS = [
    pytest.param("X-Forwarded-For", id="x-forwarded-for"),
    pytest.param("x-forwarded-for", id="x-forwarded-for-lower-case"),
    pytest.param("X-FORWARDED-FOR", id="x-forwarded-for-upper-case"),
    pytest.param("  X-Forwarded-For ", id="x-forwarded-for-spaces-around"),
    pytest.param("Forwarded", id="forwarded"),
    pytest.param("forwarded", id="forwarded-lower-case"),
    pytest.param("FORWARDED", id="forwarded-upper-case"),
    pytest.param("\tForwarded  ", id="forwarded-spaces-around"),
]


@pytest.mark.parametrize("written", FORWARDED_LISTS)
def test_the_forwarded_lists_are_refused_naming_forwarded_allow_ips(monkeypatch: pytest.MonkeyPatch, written: str) -> None:
    print_section(f"{HEADER_VARIABLE}={written!r}")
    header_field()
    monkeypatch.setenv(HEADER_VARIABLE, written)

    message = refusal_of(written)

    unnamed = [name for name in (HEADER_VARIABLE, TRUSTED_PROXIES_VARIABLE) if name not in message]
    assert not unnamed, f"{HEADER_VARIABLE}={written!r} is refused, but the message does not name {unnamed}: a list whose first value the client chooses is for uvicorn to read, from the proxies of {TRUSTED_PROXIES_VARIABLE}. {message}"
    print_success(f"✓ refused, naming {HEADER_VARIABLE} and {TRUSTED_PROXIES_VARIABLE}")


# =============================================================================
# (b) NO PROFILE SETS IT
# =============================================================================


def test_no_profile_lists_the_setting() -> None:
    print_section(f"PROFILE_DEFAULTS: no profile lists {HEADER_VARIABLE}")
    header_field()

    listing = sorted(profile for profile, values in config.PROFILE_DEFAULTS.items() if HEADER_VARIABLE in values)

    assert not listing, f"PROFILE_DEFAULTS lists {HEADER_VARIABLE} for {listing}: no profile sets it (decision P17, point 4), the cloud sets it in its own environment"
    print_success(f"✓ none of {sorted(config.PROFILE_DEFAULTS)}")


@pytest.mark.parametrize("profile", [pytest.param(None, id="profile-unset"), pytest.param("selfhosted", id="selfhosted"), pytest.param("managed", id="managed")])
def test_unset_the_setting_is_empty_under_every_profile(monkeypatch: pytest.MonkeyPatch, profile: str | None) -> None:
    print_section(f"{PROFILE_VARIABLE}={profile or '(unset)'}, {HEADER_VARIABLE} unset")
    header_field()
    set_or_unset(monkeypatch, PROFILE_VARIABLE, profile)

    settings = settings_from_the_environment()

    assert settings.LIBREFOLIO_PROFILE == (profile or "selfhosted"), f"barrier: the profile read is {settings.LIBREFOLIO_PROFILE!r}"
    value = setting_of(settings)
    assert exactly(value, ""), f"{PROFILE_VARIABLE}={profile!r} and {HEADER_VARIABLE} unset: it is {value!r}, not '': no profile sets it (decision P17, point 4)"
    print_success("✓ ''")


def test_under_the_managed_profile_the_peer_is_read_whatever_the_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    print_section(f"{PROFILE_VARIABLE}=managed, {HEADER_VARIABLE} unset: client_address")
    api = under_test(monkeypatch)
    configure(monkeypatch, api, None, profile="managed")

    result = api.client_address(http_request(EVERY_CLIENT_HEADER))

    assert exactly(result, PEER_HOST), f"managed, {HEADER_VARIABLE} unset: client_address gives {result!r}, not the peer {PEER_HOST!r}: no profile names a header, whatever the request carries ({[name for name, _ in EVERY_CLIENT_HEADER]})"
    assert not api.log.at(*ALERT_LEVELS), f"nothing to warn about: {api.log.records}"
    print_success(f"✓ {result!r}")


# =============================================================================
# (c) client_address: THE PEER, OR THE CONFIGURED HEADER
# =============================================================================


#: TCP peers as uvicorn gives them, and the host client_address gives back while no header is used: as it is.
PEERS = [
    pytest.param(("10.0.0.1", 1234), "10.0.0.1", id="ipv4"),
    pytest.param(("testclient", 50000), "testclient", id="a-name-as-written"),
    pytest.param(("::ffff:203.0.113.7", 1234), "::ffff:203.0.113.7", id="ipv4-mapped-not-normalised"),
    pytest.param(("2001:0db8:0000:0000:0000:0000:0000:0001", 1234), "2001:0db8:0000:0000:0000:0000:0000:0001", id="ipv6-not-compressed"),
    pytest.param(None, None, id="no-client"),
]


@pytest.mark.parametrize(("client", "expected"), PEERS)
@pytest.mark.parametrize("written", UNSET)
def test_unset_the_peer_comes_back_as_it_is_and_no_header_is_read(monkeypatch: pytest.MonkeyPatch, written: str | None, client: tuple[str, int] | None, expected: str | None) -> None:
    print_section(f"{HEADER_VARIABLE}={written!r}: client_address from {client!r}")
    api = under_test(monkeypatch)
    configure(monkeypatch, api, written)

    result = api.client_address(http_request(EVERY_CLIENT_HEADER, client))

    assert exactly(result, expected), f"{HEADER_VARIABLE}={written!r}: client_address gives {result!r}, not {expected!r}, the peer exactly as it is: no header is read ({[name for name, _ in EVERY_CLIENT_HEADER]}), nothing is normalised"
    assert not api.log.at(*ALERT_LEVELS), f"nothing to warn about: {api.log.records}"
    print_success(f"✓ {result!r}")


#: One line of the configured header, and the address client_address gives: the stripped value, normalised.
USABLE = [
    pytest.param("203.0.113.7", "203.0.113.7", id="ipv4"),
    pytest.param("  203.0.113.7  ", "203.0.113.7", id="ipv4-spaces-around"),
    pytest.param("\t203.0.113.7 ", "203.0.113.7", id="ipv4-tab-and-space-around"),
    pytest.param("127.0.0.1", "127.0.0.1", id="ipv4-loopback"),
    pytest.param("::ffff:203.0.113.7", "203.0.113.7", id="ipv4-mapped-as-its-ipv4"),
    pytest.param("::ffff:cb00:7107", "203.0.113.7", id="ipv4-mapped-in-hexadecimal-as-its-ipv4"),
    pytest.param("2001:0db8:0000:0000:0000:0000:0000:0001", "2001:db8::1", id="ipv6-compressed"),
    pytest.param("2001:DB8::1", "2001:db8::1", id="ipv6-in-lower-case"),
    pytest.param("::1", "::1", id="ipv6-loopback"),
]


@pytest.mark.parametrize(("line", "expected"), USABLE)
def test_one_line_of_one_address_gives_that_address_normalised(monkeypatch: pytest.MonkeyPatch, line: str, expected: str) -> None:
    print_section(f"{HEADER_VARIABLE}={FLY}, {FLY}: {line!r}")
    api = under_test(monkeypatch)
    configure(monkeypatch, api, FLY)

    result = api.client_address(http_request([*OTHER_CLIENT_HEADERS, (FLY, line)]))

    assert exactly(result, expected), f"{FLY}: {line!r}: client_address gives {result!r}, not {expected!r}: the stripped value normalised (str(ipaddress.ip_address(value)), an IPv4-mapped address as its IPv4), and no other header read"
    assert not api.log.at(*ALERT_LEVELS), f"a usable header is nothing to warn about: {api.log.records}"
    print_success(f"✓ {result!r}")


def test_a_usable_header_needs_no_peer(monkeypatch: pytest.MonkeyPatch) -> None:
    print_section(f"{HEADER_VARIABLE}={FLY}, no client, {FLY}: 203.0.113.7")
    api = under_test(monkeypatch)
    configure(monkeypatch, api, FLY)

    result = api.client_address(http_request([(FLY, "203.0.113.7")], client=None))

    assert exactly(result, "203.0.113.7"), f"without a client, a usable {FLY} still gives its address, not {result!r}"
    assert not api.log.at(*ALERT_LEVELS), f"a usable header is nothing to warn about: {api.log.records}"
    print_success(f"✓ {result!r}")


#: The setting as an operator may write it, and the address of the header it names, in a request carrying them all.
SPELLINGS = [
    pytest.param("Fly-Client-IP", "203.0.113.7", id="as-documented"),
    pytest.param("fly-client-ip", "203.0.113.7", id="lower-case"),
    pytest.param("FLY-CLIENT-IP", "203.0.113.7", id="upper-case"),
    pytest.param("  fLy-ClIeNt-Ip ", "203.0.113.7", id="mixed-case-spaces-around"),
    pytest.param("CF-Connecting-IP", "198.51.100.9", id="another-header"),
    pytest.param("x-real-ip", "192.0.2.1", id="another-header-in-lower-case"),
]


@pytest.mark.parametrize(("written", "expected"), SPELLINGS)
def test_the_configured_name_matches_the_header_whatever_the_case(monkeypatch: pytest.MonkeyPatch, written: str, expected: str) -> None:
    print_section(f"{HEADER_VARIABLE}={written!r}")
    api = under_test(monkeypatch)
    configure(monkeypatch, api, written)

    result = api.client_address(http_request(EVERY_CLIENT_HEADER))

    assert exactly(result, expected), f"{HEADER_VARIABLE}={written!r}: client_address gives {result!r}, not {expected!r}, the address of the header it names: a header name matches whatever the case it is written in"
    assert not api.log.at(*ALERT_LEVELS), f"nothing to warn about: {api.log.records}"
    print_success(f"✓ {result!r}")


@pytest.mark.parametrize("headers", [pytest.param((), id="no-header-at-all"), pytest.param(OTHER_CLIENT_HEADERS, id="only-other-client-address-headers")])
def test_an_absent_header_gives_the_peer_without_a_warning(monkeypatch: pytest.MonkeyPatch, headers: tuple[Header, ...]) -> None:
    print_section(f"{HEADER_VARIABLE}={FLY}, no {FLY} line, {[name for name, _ in headers]}")
    api = under_test(monkeypatch)
    configure(monkeypatch, api, FLY)

    result = api.client_address(http_request(headers))

    assert exactly(result, PEER_HOST), f"{FLY} absent: client_address gives {result!r}, not the peer {PEER_HOST!r}: only the configured header is read, and without it the connection's address is used"
    assert not api.log.at(*ALERT_LEVELS), f"an absent header is not a malformed one: nothing to warn about: {api.log.records}"
    print_success(f"✓ {result!r}")


#: A configured header that gives no address: absent, without a warning, and malformed, with one.
NO_USABLE_HEADER = [
    pytest.param((), 0, id="header-absent"),
    pytest.param(("203.0.113.7", "198.51.100.9"), 1, id="header-malformed"),
]


@pytest.mark.parametrize(("client", "expected"), PEERS)
@pytest.mark.parametrize(("lines", "warnings"), NO_USABLE_HEADER)
def test_without_a_usable_header_the_peer_comes_back_as_it_is(monkeypatch: pytest.MonkeyPatch, lines: tuple[str, ...], warnings: int, client: tuple[str, int] | None, expected: str | None) -> None:
    print_section(f"{HEADER_VARIABLE}={FLY}, {FLY} lines {list(lines)!r}, from {client!r}")
    api = under_test(monkeypatch)
    configure(monkeypatch, api, FLY)

    result = api.client_address(http_request(header_lines(FLY, lines), client))

    assert exactly(result, expected), f"{FLY} lines {list(lines)!r}: client_address gives {result!r}, not {expected!r}, the peer exactly as it is (None without a client)"
    assert len(api.log.at("warning")) == warnings, f"{warnings} warning(s) expected: {api.log.records}"
    print_success(f"✓ {result!r}")


#: (setting, lines of Fly-Client-IP, what client_address gives, how many warnings).
WEBSOCKET_CASES = [
    pytest.param(None, ("203.0.113.7",), PEER_HOST, 0, id="unset-the-peer"),
    pytest.param(FLY, ("203.0.113.7",), "203.0.113.7", 0, id="set-the-address"),
    pytest.param(FLY, ("203.0.113.7", "198.51.100.9"), PEER_HOST, 1, id="set-malformed-the-peer-and-a-warning"),
]


@pytest.mark.parametrize(("written", "lines", "expected", "warnings"), WEBSOCKET_CASES)
def test_a_websocket_is_read_as_a_request_is(monkeypatch: pytest.MonkeyPatch, written: str | None, lines: tuple[str, ...], expected: str, warnings: int) -> None:
    print_section(f"{HEADER_VARIABLE}={written!r}: a WebSocket, {FLY} lines {list(lines)!r}")
    api = under_test(monkeypatch)
    configure(monkeypatch, api, written)

    result = api.client_address(websocket(header_lines(FLY, lines)))

    assert exactly(result, expected), f"a WebSocket is an HTTPConnection as a Request is: client_address gives {result!r}, not {expected!r}"
    assert len(api.log.at("warning")) == warnings, f"{warnings} warning(s) expected: {api.log.records}"
    print_success(f"✓ {result!r}")


# =============================================================================
# (d) A MALFORMED HEADER: THE PEER, AND ONE WARNING PER PROCESS
# =============================================================================


#: Configured headers client_address cannot use: their lines, and the addresses inside them. Neither a line (one that is
#: not blank) nor such an address may reach a log record.
MALFORMED: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "two-lines-both-valid": (("203.0.113.7", "198.51.100.9"), ("203.0.113.7", "198.51.100.9")),
    "two-identical-lines": (("203.0.113.7", "203.0.113.7"), ("203.0.113.7",)),
    "a-valid-line-and-an-empty-one": (("203.0.113.7", ""), ("203.0.113.7",)),
    "a-comma-separated-list": (("203.0.113.7, 198.51.100.9",), ("203.0.113.7", "198.51.100.9")),
    "an-address-with-a-port": (("203.0.113.7:5678",), ("203.0.113.7",)),
    "brackets": (("[2001:db8::1]",), ("2001:db8::1",)),
    "brackets-and-a-port": (("[2001:db8::1]:443",), ("2001:db8::1",)),
    "a-zone-id": (("fe80::1%eth0",), ("fe80::1",)),
    "a-leading-zero": (("01.2.3.4",), ("1.2.3.4",)),
    "empty": (("",), ()),
    "blank": (("   ",), ()),
    "text": (("not-an-ip",), ()),
    "a-space-inside": (("203.0.113.7 x",), ("203.0.113.7",)),
    "a-network": (("203.0.113.0/24",), ("203.0.113.0",)),
}


@pytest.mark.parametrize(("lines", "hidden"), MALFORMED.values(), ids=list(MALFORMED))
def test_a_malformed_header_gives_the_peer_and_one_warning_without_the_value(monkeypatch: pytest.MonkeyPatch, lines: tuple[str, ...], hidden: tuple[str, ...]) -> None:
    print_section(f"{HEADER_VARIABLE}={FLY}, {FLY} lines {list(lines)!r}")
    api = under_test(monkeypatch)
    configure(monkeypatch, api, FLY)

    result = api.client_address(http_request(header_lines(FLY, lines)))

    assert exactly(result, PEER_HOST), f"{FLY} lines {list(lines)!r}: client_address gives {result!r}, not the peer {PEER_HOST!r}: a malformed header is never half-read"
    expected = unusable(FLY_LOWER, lines)
    assert api.log.at("warning") == [expected], f"one warning, word for word, with the header in lower case, the number of lines and the characters of their values as received, and no other field: expected {[expected]}, got {api.log.at('warning')}"
    assert not api.log.at("error", "exception", "critical"), f"a malformed header is a warning and nothing more: {api.log.records}"
    leaked = leaks(api.log.records, lines, hidden)
    assert not leaked, f"the header's value, or an address inside it, reached the log ((text, record)): {leaked}. The client writes that header, and its address is personal data"
    print_success(f"✓ {result!r}, one warning: lines={expected[2]['lines']}, length={expected[2]['length']}")


#: The setting as written, and the header the request carries, as the warning must name it: in lower case.
LOWER_CASE_NAMES = [
    pytest.param("Fly-Client-IP", "fly-client-ip", id="as-documented"),
    pytest.param("FLY-CLIENT-IP", "fly-client-ip", id="upper-case"),
    pytest.param("  fLy-ClIeNt-Ip ", "fly-client-ip", id="mixed-case-spaces-around"),
    pytest.param("CF-Connecting-IP", "cf-connecting-ip", id="another-header"),
]


@pytest.mark.parametrize(("written", "lower"), LOWER_CASE_NAMES)
def test_the_warning_names_the_configured_header_in_lower_case(monkeypatch: pytest.MonkeyPatch, written: str, lower: str) -> None:
    print_section(f"{HEADER_VARIABLE}={written!r}, {lower}: 'not-an-ip'")
    api = under_test(monkeypatch)
    configure(monkeypatch, api, written)
    lines = ("not-an-ip",)

    result = api.client_address(http_request(header_lines(lower, lines)))

    assert exactly(result, PEER_HOST), f"{lower}: 'not-an-ip': client_address gives {result!r}, not the peer {PEER_HOST!r}"
    assert api.log.at("warning") == [unusable(lower, lines)], f"{HEADER_VARIABLE}={written!r}: the warning names the header in lower case, {lower!r}: {api.log.at('warning')}"
    print_success(f"✓ header={lower!r}")


def test_a_malformed_header_warns_once_per_process_until_the_cache_is_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    print_section("One warning per process; a new process warns again")
    api = under_test(monkeypatch)
    configure(monkeypatch, api, FLY)
    first = ("203.0.113.7", "198.51.100.9")
    calls = [
        (first, PEER_HOST),  # malformed: the one warning
        (("203.0.113.7, 198.51.100.9",), PEER_HOST),  # malformed again
        (("198.51.100.9",), "198.51.100.9"),  # usable: re-arms nothing
        ((), PEER_HOST),  # absent: re-arms nothing
        (("203.0.113.7:5678",), PEER_HOST),  # malformed once more
    ]

    results = [api.client_address(http_request(header_lines(FLY, lines))) for lines, _ in calls]

    assert results == [expected for _, expected in calls], f"every call gives its own answer, warned or not: {results}"
    assert api.log.at("warning") == [unusable(FLY_LOWER, first)], f"five calls, three of them malformed: one warning per process, the first one's: {api.log.at('warning')}"
    api.reset()
    rearmed = ("not-an-ip",)
    again = api.client_address(http_request(header_lines(FLY, rearmed)))
    assert exactly(again, PEER_HOST), f"after the reset, a malformed header still gives the peer, not {again!r}"
    assert api.log.at("warning") == [
        unusable(FLY_LOWER, first),
        unusable(FLY_LOWER, rearmed),
    ], f"a new process warns again: with the module's state started over as in one (_configured_header()'s cache cleared, _warned emptied), the next malformed header warns again, with its own counts: {api.log.at('warning')}"
    print_success("✓ three malformed headers, one warning; after the reset, one more")


# =============================================================================
# (e) THE NAME, READ ONCE PER PROCESS
# =============================================================================


#: The setting before the first call and after it, and what client_address gives for a request carrying every header,
#: before the reset and after it.
CHANGES = [
    pytest.param(FLY, "CF-Connecting-IP", "203.0.113.7", "198.51.100.9", id="one-header-then-another"),
    pytest.param(None, FLY, PEER_HOST, "203.0.113.7", id="unset-then-set"),
    pytest.param(FLY, None, "203.0.113.7", PEER_HOST, id="set-then-unset"),
]


@pytest.mark.parametrize(("first", "then", "before", "after"), CHANGES)
def test_the_name_is_read_once_per_process_until_the_cache_is_reset(monkeypatch: pytest.MonkeyPatch, first: str | None, then: str | None, before: str, after: str) -> None:
    print_section(f"{HEADER_VARIABLE}={first!r}, then {then!r}")
    api = under_test(monkeypatch)
    configure(monkeypatch, api, first)
    initial = api.client_address(http_request(EVERY_CLIENT_HEADER))
    assert exactly(initial, before), f"barrier: with {HEADER_VARIABLE}={first!r}, the first call gives {initial!r}, not {before!r}"
    set_or_unset(monkeypatch, HEADER_VARIABLE, then)
    resolved = setting_of(config.get_settings())
    assert resolved == (then or ""), f"barrier: with {HEADER_VARIABLE}={then!r}, get_settings() reads {resolved!r}"

    kept = api.client_address(http_request(EVERY_CLIENT_HEADER))

    assert exactly(kept, before), f"{HEADER_VARIABLE} went from {first!r} to {then!r} after the first call, and client_address gives {kept!r}, not {before!r}: the name is read once per process, and a change waits for a new process"
    api.reset()
    renewed = api.client_address(http_request(EVERY_CLIENT_HEADER))
    assert exactly(renewed, after), f"with the module's state started over as in a new process (_configured_header()'s cache cleared, _warned emptied) and {HEADER_VARIABLE}={then!r}, client_address gives {renewed!r}, not {after!r}: the first call of a new process reads the name"
    print_success(f"✓ {initial!r}, still {kept!r}, after the reset {renewed!r}")


# =============================================================================
# (f) client_rate_key: THE KEY OF AN ADDRESS FOR A PER-CLIENT LIMIT
# =============================================================================


#: The address, and its key, pinned value by value.
RATE_KEYS = [
    pytest.param(None, None, id="no-address"),
    pytest.param("", None, id="an-empty-address"),
    pytest.param("testclient", "testclient", id="a-name-as-written"),
    pytest.param("/run/librefolio/zq.sock", "/run/librefolio/zq.sock", id="a-socket-path-as-written"),
    pytest.param("203.0.113.7", "203.0.113.7", id="ipv4-as-is"),
    pytest.param("::ffff:203.0.113.7", "203.0.113.7", id="ipv4-mapped-as-its-ipv4"),
    pytest.param("2001:db8:1:2:3:4:5:6", "2001:db8:1:2::/64", id="ipv6-by-its-64"),
    pytest.param("2001:db8:1:2::abcd", "2001:db8:1:2::/64", id="ipv6-another-address-of-the-same-64"),
    pytest.param("2001:0DB8:0001:0002:0000:0000:0000:0001", "2001:db8:1:2::/64", id="ipv6-in-full-and-in-capitals"),
    pytest.param("2001:db8:1:3::1", "2001:db8:1:3::/64", id="ipv6-the-next-64"),
    pytest.param("fe80::1%eth0", "fe80::/64", id="ipv6-with-a-zone-the-zone-ignored"),
    pytest.param("::1", "::/64", id="ipv6-loopback"),
]


@pytest.mark.parametrize(("address", "key"), RATE_KEYS)
def test_the_rate_key_of_an_address(address: str | None, key: str | None) -> None:
    print_section(f"client_rate_key({address!r})")
    client_rate_key = function_of(client_address_module(), "client_rate_key")

    result = client_rate_key(address)

    assert exactly(result, key), f"client_rate_key({address!r}) is {result!r}, expected {key!r}: an IPv4 address as is, an IPv4-mapped one as its IPv4, any other IPv6 address by its /64 (a zone ignored), anything else as written, no key without an address"
    print_success(f"✓ {address!r} → {result!r}")


# =============================================================================
# (g) NOTHING IN THE MODULE ONLY FOR THE TESTS (N58, H-22)
# =============================================================================


#: A function the module must not have, and why: these tests were its only callers.
ONLY_FOR_THE_TESTS = [
    pytest.param("reset_client_address_cache", "a production function only the tests call: the tests start the module's state over themselves", id="reset_client_address_cache"),
    pytest.param("mask_client_address", "no log writes a client's address, so mask_client_address has no caller", id="mask_client_address"),
]


@pytest.mark.parametrize(("name", "why"), ONLY_FOR_THE_TESTS)
def test_the_module_has_no_function_only_for_the_tests(name: str, why: str) -> None:
    print_section(f"{MODULE_PATH}: no {name}() (N58, H-22)")
    module = client_address_module()
    # Barrier: the module's own functions are in place, so an absence below is a removal, not an emptied module.
    function_of(module, "client_address")
    function_of(module, "client_rate_key")

    present = hasattr(module, name)

    assert not present, f"{MODULE_PATH} still has {name}() (N58, H-22): {why}"
    print_success(f"✓ no {name}()")


# =============================================================================
# (h) forwarded_by_untrusted_proxy: A LOCAL PROXY NOBODY TRUSTS (H-36, N70)
# =============================================================================


#: (h) The three forwarding headers, written as the contract writes them, in its order: the order of the log record and of
#: untrusted_forwarding_seen().
XFF = "X-Forwarded-For"
FORWARDED = "Forwarded"
REAL_IP = "X-Real-IP"
FORWARDING_HEADERS = (XFF, FORWARDED, REAL_IP)
#: (h) The two classes of peer whose forwarding headers are noted.
PEER_CLASSES = ("local", "public")
#: (h) The two texts, word for word: the warning of the first local noting, the info of the first public one.
UNTRUSTED_PROXY = "Requests come through a reverse proxy that LibreFolio does not trust: the limits per client address skip them. List the proxy in FORWARDED_ALLOW_IPS, or name the header it sets in LIBREFOLIO_CLIENT_IP_HEADER"
PUBLIC_FORWARDING = "Forwarding headers from a public address were ignored: if a proxy on a public address forwards the requests, list it in FORWARDED_ALLOW_IPS"
#: (h) A reverse proxy in front of the container, as the Docker network gives it (R13-SEC6), and the one proxy uvicorn
#: trusts by default (FORWARDED_ALLOW_IPS), as the Docker image keeps it.
DOCKER_PROXY: tuple[str, int] = ("172.18.0.2", 40000)
TRUSTED_BY_DEFAULT = "127.0.0.1"
#: (h) Every address the headers of (h) carry inside a longer value (a list, a for= pair, brackets, a port): with the peer
#: and the values themselves, what no log record may hold (N58).
CARRIED = ("198.51.100.4", "198.51.100.5", "192.0.2.1", "192.0.2.77", "203.0.113.7", "10.0.0.1", "10.0.0.9", "2001:db8::5", "2001:db8::7", "fd7a:115c:a1e0::5")
#: (h) Where H-36 adds the configuration check that reads what was noted.
CONFIG_AUDIT = "backend.app.services.platform.config_audit"
CONFIG_AUDIT_PATH = "backend/app/services/platform/config_audit.py"

#: (h) A connection from a peer, carrying headers: a Request or a WebSocket.
Connect = Callable[[Sequence[Header], tuple[str, int] | None], HTTPConnection]
#: (h) A Request and a WebSocket alike.
CONNECTIONS = [pytest.param(http_request, id="request"), pytest.param(websocket, id="websocket")]


def untrusted_forwarding() -> dict[str, set[str]]:
    """(h) The module's own ``_untrusted_forwarding``, where ``forwarded_by_untrusted_proxy`` notes the forwarding headers
    it sees, by the class of the peer. Before H-36, the (h) test that asks for it fails here, and only that test."""
    module = client_address_module()
    assert hasattr(module, "_untrusted_forwarding"), f"{MODULE_PATH} has no _untrusted_forwarding, where forwarded_by_untrusted_proxy() notes the forwarding headers it sees by the class of the peer (H-36, N70)"
    state = module._untrusted_forwarding
    assert isinstance(state, dict) and all(isinstance(state.get(peer_class), set) for peer_class in PEER_CLASSES), f"{MODULE_PATH}: _untrusted_forwarding is {state!r}, not a dict of the two sets 'local' and 'public' (H-36, N70)"
    return state


def forget_untrusted_forwarding() -> None:
    """(h) Both sets emptied in place, as a new process finds them: the next noting of each class is the first again, and
    logs. No production function does this for the tests (N58, H-22): they start the state over themselves."""
    state = untrusted_forwarding()
    for peer_class in PEER_CLASSES:
        state[peer_class].clear()


@pytest.fixture
def fresh_untrusted_forwarding() -> Iterator[None]:
    """(h) Nothing noted before the test and nothing left after it: no test inherits the names another noted, nor finds the
    first noting of a class spent, and whatever runs after this file finds the state as a new process does. It is also
    the red barrier of the (h) tests, and of them only: before H-36 it fails on ``untrusted_forwarding()``."""
    forget_untrusted_forwarding()
    yield
    forget_untrusted_forwarding()


#: (h) Every test of (h) starts with nothing noted and leaves nothing noted.
untrusted_forwarding_started_over = pytest.mark.usefixtures("fresh_untrusted_forwarding")


@dataclass(frozen=True)
class ProxyUnderTest(UnderTest):
    """``UnderTest``, and what the cases of (h) call: the predicate, and the names it noted."""

    forwarded_by_untrusted_proxy: Callable[[HTTPConnection], bool]
    untrusted_forwarding_seen: Callable[[str], tuple[str, ...]]


def h36_function_of(module: ModuleType, name: str, path: str = MODULE_PATH) -> Callable[..., Any]:
    """The function ``name`` H-36 adds to ``module``: before it lands, the (h) test that asks for it fails here, naming it."""
    function = getattr(module, name, None)
    assert callable(function), f"{path} has no function {name}() (H-36, N70)"
    return function


def noted(api: ProxyUnderTest, local: Sequence[str], public: Sequence[str], when: str) -> None:
    """(h) What ``untrusted_forwarding_seen`` gives for each class ``when``: the names noted under it, a tuple in the
    contract's order, ``()`` when none."""
    for peer_class, names in (("local", local), ("public", public)):
        seen, expected = api.untrusted_forwarding_seen(peer_class), tuple(names)
        assert exactly(seen, expected), f"{when}: untrusted_forwarding_seen({peer_class!r}) is {seen!r}, not {expected!r}: the names noted under {peer_class!r}, a tuple in the order {FORWARDING_HEADERS}, () when none"


def proxy_under_test(monkeypatch: pytest.MonkeyPatch, written: str | None = None) -> ProxyUnderTest:
    """``forwarded_by_untrusted_proxy`` and ``untrusted_forwarding_seen``, with ``client_address``, ``start_over`` as the
    reset and the module's logger recorded; the setting made ``written`` (``None``: unset) through ``configure`` and its
    barrier. Nothing is noted yet: the fixture emptied both sets, and ``untrusted_forwarding_seen`` must say so."""
    module = client_address_module()
    api = ProxyUnderTest(
        client_address=function_of(module, "client_address"),
        reset=start_over,
        log=record_logs(monkeypatch, module),
        forwarded_by_untrusted_proxy=h36_function_of(module, "forwarded_by_untrusted_proxy"),
        untrusted_forwarding_seen=h36_function_of(module, "untrusted_forwarding_seen"),
    )
    configure(monkeypatch, api, written)
    noted(api, (), (), "at the start of the test, both sets emptied in place")
    return api


def rate_limit_address_function() -> Callable[[HTTPConnection], str | None]:
    """(h) ``rate_limit_address``, the address every per-address limit counts a request by."""
    return h36_function_of(client_address_module(), "rate_limit_address")


def untrusted_proxy(names: Sequence[str]) -> Record:
    """(h) The warning of the first local noting, word for word: this request's names in the contract's order, joined by
    ``", "``, and no other field."""
    return ("warning", UNTRUSTED_PROXY, {"headers": ", ".join(names)})


def public_forwarding(names: Sequence[str]) -> Record:
    """(h) The info of the first public noting, word for word, as the warning is."""
    return ("info", PUBLIC_FORWARDING, {"headers": ", ".join(names)})


def first_noting(local: Sequence[str], public: Sequence[str]) -> list[Record]:
    """(h) What one request logs when it is the first of its class to be noted: the warning, the info, or nothing."""
    if local:
        return [untrusted_proxy(local)]
    if public:
        return [public_forwarding(public)]
    return []


def no_address_logged(api: ProxyUnderTest, headers: Sequence[Header], client: tuple[str, int] | None) -> None:
    """(h) No record, at any level, holds the peer, a value of ``headers`` (one that is not blank) nor an address carried
    inside one (N58): the peer and the forwarding headers hold a client's address."""
    peer = [client[0]] if client else []
    leaked = leaks(api.log.records, [value for _, value in headers], [*peer, *CARRIED])
    assert not leaked, f"an address reached the log ((text, record)): {leaked}. The peer and the forwarding headers hold a client's address, and no log record may hold one (N58)"


async def _nothing_to_receive() -> dict[str, Any]:
    raise AssertionError("the app behind ProxyHeadersMiddleware reads nothing from the connection")


async def _nothing_to_send(message: dict[str, Any]) -> None:
    raise AssertionError(f"the app behind ProxyHeadersMiddleware sends nothing: {message}")


def through_uvicorn(api: ProxyUnderTest, trusted_hosts: str, headers: Sequence[Header], client: tuple[str, int] | None) -> tuple[str | None, bool]:
    """``forwarded_by_untrusted_proxy`` called by an app behind uvicorn's own ``ProxyHeadersMiddleware``, as uvicorn wraps
    the app with ``FORWARDED_ALLOW_IPS=<trusted_hosts>``: the host of the client the app sees, and the answer. A raw http
    scope driven by ``asyncio.run``, no server."""
    seen: list[tuple[str | None, bool]] = []

    async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        request = Request(scope)
        seen.append((request.client.host if request.client else None, api.forwarded_by_untrusted_proxy(request)))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "query_string": b"",
        "headers": raw_headers(headers),
        "client": client,
        "server": ("172.18.0.3", 8000),
    }
    asyncio.run(ProxyHeadersMiddleware(app, trusted_hosts=trusted_hosts)(scope, _nothing_to_receive, _nothing_to_send))
    assert len(seen) == 1, f"barrier: the app behind ProxyHeadersMiddleware ran {len(seen)} times, not once"
    return seen[0]


# --- The two texts -----------------------------------------------------------


@untrusted_forwarding_started_over
@pytest.mark.parametrize(("name", "text"), [pytest.param("UNTRUSTED_PROXY_SUMMARY", UNTRUSTED_PROXY, id="untrusted-proxy"), pytest.param("PUBLIC_FORWARDING_SUMMARY", PUBLIC_FORWARDING, id="public-forwarding")])
def test_the_two_summaries_word_for_word(name: str, text: str) -> None:
    print_section(f"{MODULE_PATH}: {name} (H-36)")
    module = client_address_module()

    value = getattr(module, name, None)

    assert exactly(value, text), f"{MODULE_PATH}: {name} is {value!r}, not, word for word, {text!r} (H-36, N70): the log record and the configuration check of the admin both show it"
    print_success(f"✓ {name}")


# --- Step 1: no forwarding header, no proxy ------------------------------------


#: (h) Headers that are not forwarding headers: the client-address headers of other proxies (Fly-Client-IP not configured
#: here), and the X-Forwarded-* headers that carry no address.
NOT_FORWARDING: tuple[Header, ...] = (
    ("CF-Connecting-IP", "198.51.100.9"),
    ("True-Client-IP", "192.0.2.55"),
    (FLY, "203.0.113.70"),
    ("X-Forwarded-Proto", "https"),
    ("X-Forwarded-Host", "librefolio.example"),
)


@untrusted_forwarding_started_over
@pytest.mark.parametrize("headers", [pytest.param((), id="no-header-at-all"), pytest.param(NOT_FORWARDING, id="only-headers-that-are-not-forwarding-ones")])
@pytest.mark.parametrize(
    "client",
    [
        pytest.param(("10.0.0.1", 50000), id="lan"),
        pytest.param(("127.0.0.1", 50000), id="loopback"),
        pytest.param(("::1", 50000), id="ipv6-loopback"),
        pytest.param(DOCKER_PROXY, id="the-docker-network"),
        pytest.param(("203.0.113.7", 50000), id="public"),
        pytest.param(("2001:db8::1", 50000), id="public-ipv6"),
    ],
)
@pytest.mark.parametrize("connect", CONNECTIONS)
def test_without_a_forwarding_header_no_proxy_is_suspected(monkeypatch: pytest.MonkeyPatch, connect: Connect, client: tuple[str, int], headers: tuple[Header, ...]) -> None:
    print_section(f"{[name for name, _ in headers]} from {client[0]}")
    api = proxy_under_test(monkeypatch)

    result = api.forwarded_by_untrusted_proxy(connect(headers, client))

    assert result is False, f"no forwarding header ({', '.join(FORWARDING_HEADERS)}) from {client[0]}: forwarded_by_untrusted_proxy gives {result!r}, not False: without one, no proxy forwarded the request"
    noted(api, (), (), "without a forwarding header")
    assert api.log.records == [], f"nothing noted, nothing to log: {api.log.records}"
    print_success("✓ False, nothing noted")


# --- Step 5: a local peer is a proxy nobody trusts, a public one is not --------


#: (h) Peers of every local class, as uvicorn gives them: loopback, LAN (private, link-local, unique-local) and VPN (the
#: CGNAT range and Tailscale's prefix), the edges of the ranges included, and an IPv4-mapped form, read as its IPv4.
LOCAL_PEERS = [
    pytest.param(("127.0.0.1", 50000), id="loopback"),
    pytest.param(("127.1.2.3", 50000), id="loopback-anywhere-in-127-8"),
    pytest.param(("::1", 50000), id="ipv6-loopback"),
    pytest.param(("10.0.0.1", 50000), id="lan-10-8"),
    pytest.param(("172.16.0.1", 50000), id="lan-172-16-12-first"),
    pytest.param(("172.31.255.254", 50000), id="lan-172-16-12-last"),
    pytest.param(("192.168.1.10", 50000), id="lan-192-168-16"),
    pytest.param(("169.254.10.20", 50000), id="link-local"),
    pytest.param(("100.64.0.1", 50000), id="vpn-cgnat-first"),
    pytest.param(("100.127.255.254", 50000), id="vpn-cgnat-last"),
    pytest.param(("fd00::1", 50000), id="ipv6-unique-local"),
    pytest.param(("fd7a:115c:a1e0::1", 50000), id="vpn-tailscale-ipv6"),
    pytest.param(("fe80::1", 50000), id="ipv6-link-local"),
    pytest.param(("::ffff:10.0.0.1", 50000), id="ipv4-mapped-lan"),
]

#: (h) Public peers, the edges just outside the local ranges included, and an IPv4-mapped public address.
PUBLIC_PEERS = [
    pytest.param(("203.0.113.7", 50000), id="ipv4-documentation"),
    pytest.param(("8.8.8.8", 50000), id="8-8-8-8"),
    pytest.param(("1.1.1.1", 50000), id="1-1-1-1"),
    pytest.param(("2001:db8::1", 50000), id="ipv6-documentation"),
    pytest.param(("2606:4700::1111", 50000), id="ipv6-public"),
    pytest.param(("::ffff:8.8.8.8", 50000), id="ipv4-mapped-public"),
    pytest.param(("172.32.0.1", 50000), id="just-above-172-16-12"),
    pytest.param(("100.128.0.1", 50000), id="just-above-the-cgnat-range"),
    pytest.param(("11.0.0.1", 50000), id="just-above-10-8"),
    pytest.param(("192.169.0.1", 50000), id="just-above-192-168-16"),
    pytest.param(("169.255.0.1", 50000), id="just-above-link-local"),
]

#: (h) The three forwarding headers as a proxy sets them, in another order than the contract's, and the names noted.
ALL_THREE: tuple[Header, ...] = ((REAL_IP, "192.0.2.1"), (FORWARDED, 'for="[2001:db8::5]:4711"'), (XFF, "198.51.100.4, 192.0.2.77"))
#: (h) Forwarding headers, and the names noted. No value is the address of a peer of these cases: uvicorn followed none.
FORWARDING = [
    pytest.param(((XFF, "198.51.100.4"),), (XFF,), id="x-forwarded-for"),
    pytest.param(((FORWARDED, "for=198.51.100.5;proto=https"),), (FORWARDED,), id="forwarded"),
    pytest.param(((REAL_IP, "192.0.2.1"),), (REAL_IP,), id="x-real-ip"),
    pytest.param(ALL_THREE, FORWARDING_HEADERS, id="all-three-in-another-order"),
]


@untrusted_forwarding_started_over
@pytest.mark.parametrize(("headers", "names"), FORWARDING)
@pytest.mark.parametrize("client", LOCAL_PEERS)
def test_forwarding_headers_from_a_local_peer_mean_a_proxy_nobody_trusts(monkeypatch: pytest.MonkeyPatch, client: tuple[str, int], headers: tuple[Header, ...], names: tuple[str, ...]) -> None:
    print_section(f"{list(names)} from the local peer {client[0]}")
    api = proxy_under_test(monkeypatch)

    result = api.forwarded_by_untrusted_proxy(http_request(headers, client))

    assert result is True, f"{list(names)} from {client[0]}, a loopback, LAN or VPN peer uvicorn did not take from X-Forwarded-For: forwarded_by_untrusted_proxy gives {result!r}, not True: a local proxy LibreFolio does not trust forwarded the request (R13-SEC6)"
    noted(api, names, (), f"after {list(names)} from {client[0]}")
    assert api.log.records == [untrusted_proxy(names)], f"the first local noting logs one warning, word for word, with headers={', '.join(names)!r} and no other field: {api.log.records}"
    no_address_logged(api, headers, client)
    print_success(f"✓ True, noted local: {', '.join(names)}")


#: (h) A forwarding header holding no address at all: present all the same.
WHATEVER_THE_VALUE = [
    pytest.param(XFF, "", id="x-forwarded-for-empty"),
    pytest.param(XFF, "   ", id="x-forwarded-for-blank"),
    pytest.param(XFF, "unknown", id="x-forwarded-for-unknown"),
    pytest.param(FORWARDED, "", id="forwarded-empty"),
    pytest.param(FORWARDED, "for=unknown", id="forwarded-for-unknown"),
    pytest.param(REAL_IP, "", id="x-real-ip-empty"),
    pytest.param(REAL_IP, "not-an-ip", id="x-real-ip-text"),
]


@untrusted_forwarding_started_over
@pytest.mark.parametrize(("name", "value"), WHATEVER_THE_VALUE)
def test_a_forwarding_header_is_present_whatever_its_value(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    print_section(f"{name}: {value!r} from {DOCKER_PROXY[0]}")
    api = proxy_under_test(monkeypatch)

    result = api.forwarded_by_untrusted_proxy(http_request([(name, value)], DOCKER_PROXY))

    assert result is True, f"{name}: {value!r} from {DOCKER_PROXY[0]}: forwarded_by_untrusted_proxy gives {result!r}, not True: a line of a forwarding header is present whatever its value, even empty"
    noted(api, (name,), (), f"after {name}: {value!r}")
    assert api.log.records == [untrusted_proxy((name,))], f"one warning, word for word: {api.log.records}"
    print_success(f"✓ True, noted local: {name}")


@untrusted_forwarding_started_over
@pytest.mark.parametrize("connect", CONNECTIONS)
def test_the_names_are_noted_as_the_contract_writes_them_whatever_the_case(monkeypatch: pytest.MonkeyPatch, connect: Connect) -> None:
    print_section("The three forwarding headers written in any case")
    api = proxy_under_test(monkeypatch)
    # As the client wrote them; in the scope in lower case, as uvicorn puts every name there (raw_headers)
    headers = (("x-REAL-ip", "192.0.2.1"), ("FORWARDED", "for=198.51.100.5"), ("x-forwarded-FOR", "198.51.100.4"))

    result = api.forwarded_by_untrusted_proxy(connect(headers, DOCKER_PROXY))

    assert result is True, f"{[name for name, _ in headers]} from {DOCKER_PROXY[0]}: forwarded_by_untrusted_proxy gives {result!r}, not True: a header name matches whatever the case it is written in"
    noted(api, FORWARDING_HEADERS, (), "after the three headers written in any case")
    assert api.log.records == [untrusted_proxy(FORWARDING_HEADERS)], f"the names are noted and logged as the contract writes them, {FORWARDING_HEADERS}, not as the request did: {api.log.records}"
    no_address_logged(api, headers, DOCKER_PROXY)
    print_success(f"✓ True, noted local: {', '.join(FORWARDING_HEADERS)}")


@untrusted_forwarding_started_over
@pytest.mark.parametrize(("headers", "names"), FORWARDING)
@pytest.mark.parametrize("client", PUBLIC_PEERS)
def test_forwarding_headers_from_a_public_peer_are_ignored_and_noted_public(monkeypatch: pytest.MonkeyPatch, client: tuple[str, int], headers: tuple[Header, ...], names: tuple[str, ...]) -> None:
    print_section(f"{list(names)} from the public peer {client[0]}")
    api = proxy_under_test(monkeypatch)

    result = api.forwarded_by_untrusted_proxy(http_request(headers, client))

    assert result is False, f"{list(names)} from {client[0]}, a public peer: forwarded_by_untrusted_proxy gives {result!r}, not False: only a local proxy is one the per-address limits skip; a public peer is counted by its own address"
    noted(api, (), names, f"after {list(names)} from {client[0]}")
    assert api.log.records == [public_forwarding(names)], f"the first public noting logs one info, word for word, with headers={', '.join(names)!r} and no other field: {api.log.records}"
    no_address_logged(api, headers, client)
    print_success(f"✓ False, noted public: {', '.join(names)}")


# --- Step 3: a peer classify_ip cannot class ------------------------------------


#: (h) Peers classify_ip calls unknown: no client, the test client's name, the unspecified addresses, a multicast one.
UNKNOWN_PEERS = [
    pytest.param(None, id="no-client"),
    pytest.param(("testclient", 50000), id="testclient"),
    pytest.param(("0.0.0.0", 50000), id="ipv4-unspecified"),
    pytest.param(("::", 50000), id="ipv6-unspecified"),
    pytest.param(("224.0.0.1", 50000), id="multicast"),
]


@untrusted_forwarding_started_over
@pytest.mark.parametrize("client", UNKNOWN_PEERS)
@pytest.mark.parametrize("connect", CONNECTIONS)
def test_a_peer_classify_ip_cannot_class_is_never_a_proxy(monkeypatch: pytest.MonkeyPatch, connect: Connect, client: tuple[str, int] | None) -> None:
    print_section(f"The three forwarding headers from {client!r}")
    api = proxy_under_test(monkeypatch)

    result = api.forwarded_by_untrusted_proxy(connect(ALL_THREE, client))

    assert result is False, f"the three forwarding headers from {client!r}, a peer classify_ip calls unknown: forwarded_by_untrusted_proxy gives {result!r}, not False"
    noted(api, (), (), f"after a request from {client!r}")
    assert api.log.records == [], f"a peer that cannot be classed is noted nowhere and logs nothing: {api.log.records}"
    print_success("✓ False, nothing noted")


# --- Step 4: uvicorn already followed X-Forwarded-For --------------------------


#: (h) A peer uvicorn took from X-Forwarded-For, trusting the proxy that set it: equal, both read by parse_ip, to one value
#: of its lines. (peer, the lines of X-Forwarded-For.)
FOLLOWED = [
    pytest.param(("10.0.0.9", 0), ("198.51.100.4, 10.0.0.9",), id="a-private-client-the-last-of-the-list"),
    pytest.param(("192.168.1.10", 0), ("192.168.1.10",), id="a-private-client-the-only-value"),
    pytest.param(("127.0.0.1", 0), ("127.0.0.1",), id="a-loopback-client"),
    pytest.param(("10.0.0.9", 0), ("198.51.100.4", "10.0.0.9"), id="two-lines-the-peer-in-the-second"),
    pytest.param(("10.0.0.9", 0), ("  198.51.100.4 ,   10.0.0.9  ",), id="spaces-around-the-values"),
    pytest.param(("203.0.113.7", 51000), ("203.0.113.7:51000",), id="a-port"),
    pytest.param(("2001:db8::7", 443), ("[2001:db8::7]:443",), id="ipv6-brackets-and-a-port"),
    pytest.param(("fd7a:115c:a1e0::5", 0), ("[fd7a:115c:a1e0::5]",), id="ipv6-brackets-without-a-port"),
    pytest.param(("2001:db8::7", 0), ("2001:0DB8:0000:0000:0000:0000:0000:0007",), id="ipv6-written-another-way"),
    pytest.param(("::ffff:203.0.113.7", 0), ("203.0.113.7",), id="an-ipv4-mapped-peer"),
    pytest.param(("10.0.0.9", 0), ("::ffff:10.0.0.9",), id="an-ipv4-mapped-value"),
]
#: (h) The other forwarding headers beside X-Forwarded-For: once uvicorn followed it, they change nothing.
BESIDE = [
    pytest.param((), id="x-forwarded-for-alone"),
    pytest.param(((REAL_IP, "192.0.2.1"), (FORWARDED, "for=192.0.2.1")), id="with-x-real-ip-and-forwarded"),
]


@untrusted_forwarding_started_over
@pytest.mark.parametrize("beside", BESIDE)
@pytest.mark.parametrize(("client", "lines"), FOLLOWED)
def test_a_peer_uvicorn_took_from_x_forwarded_for_is_no_proxy(monkeypatch: pytest.MonkeyPatch, client: tuple[str, int], lines: tuple[str, ...], beside: tuple[Header, ...]) -> None:
    print_section(f"Peer {client[0]}, X-Forwarded-For lines {list(lines)!r}, {[name for name, _ in beside]}")
    api = proxy_under_test(monkeypatch)
    headers = [*header_lines(XFF, lines), *beside]

    result = api.forwarded_by_untrusted_proxy(http_request(headers, client))

    assert result is False, f"peer {client[0]}, X-Forwarded-For lines {list(lines)!r}: forwarded_by_untrusted_proxy gives {result!r}, not False: the peer is one of the values (both read by parse_ip), so uvicorn already followed X-Forwarded-For from a proxy it trusts"
    noted(api, (), (), "after a request uvicorn followed")
    assert api.log.records == [], f"a request uvicorn followed is noted nowhere and logs nothing: {api.log.records}"
    print_success("✓ False, nothing noted")


#: (h) A local peer that is none of the X-Forwarded-For values: uvicorn followed nothing. (headers, the names noted.)
NOT_FOLLOWED = [
    pytest.param(((XFF, "10.0.0.90"),), (XFF,), id="a-longer-address"),
    pytest.param(((XFF, "198.51.100.4, 10.0.0.1"),), (XFF,), id="other-addresses-only"),
    pytest.param(((REAL_IP, "10.0.0.9"),), (REAL_IP,), id="x-real-ip-naming-the-peer-which-uvicorn-never-follows"),
    pytest.param(((FORWARDED, "for=10.0.0.9"),), (FORWARDED,), id="forwarded-naming-the-peer-which-uvicorn-never-follows"),
]


@untrusted_forwarding_started_over
@pytest.mark.parametrize(("headers", "names"), NOT_FOLLOWED)
def test_a_local_peer_uvicorn_did_not_take_from_x_forwarded_for_is_a_proxy(monkeypatch: pytest.MonkeyPatch, headers: tuple[Header, ...], names: tuple[str, ...]) -> None:
    client = ("10.0.0.9", 50000)
    print_section(f"Peer {client[0]}, {headers!r}")
    api = proxy_under_test(monkeypatch)

    result = api.forwarded_by_untrusted_proxy(http_request(headers, client))

    assert result is True, f"peer {client[0]}, {headers!r}: forwarded_by_untrusted_proxy gives {result!r}, not True: the peer is none of the X-Forwarded-For values, so uvicorn followed nothing, and only X-Forwarded-For is one uvicorn follows"
    noted(api, names, (), f"after {headers!r}")
    assert api.log.records == [untrusted_proxy(names)], f"one warning, word for word: {api.log.records}"
    no_address_logged(api, headers, client)
    print_success(f"✓ True, noted local: {', '.join(names)}")


# --- Step 2: the configured header ---------------------------------------------


#: (h) LIBREFOLIO_CLIENT_IP_HEADER and a request: (setting, peer, headers, what forwarded_by_untrusted_proxy says, the names
#: noted local). Carried once, holding one IP address, the configured header vouches for the address; absent or unusable,
#: it is as if unset.
CONFIGURED = [
    pytest.param(FLY, DOCKER_PROXY, ((FLY, "203.0.113.7"), (XFF, "203.0.113.7")), False, (), id="fly-client-ip-usable"),
    pytest.param("  fLy-ClIeNt-Ip ", DOCKER_PROXY, ((FLY, "203.0.113.7"), (XFF, "203.0.113.7")), False, (), id="fly-client-ip-usable-the-name-in-any-case"),
    pytest.param(REAL_IP, DOCKER_PROXY, ((REAL_IP, "203.0.113.7"),), False, (), id="x-real-ip-usable"),
    pytest.param(FLY, ("203.0.113.9", 50000), ((FLY, "198.51.100.4"), (XFF, "198.51.100.4")), False, (), id="fly-client-ip-usable-from-a-public-peer-not-even-noted-public"),
    pytest.param(FLY, DOCKER_PROXY, ((XFF, "203.0.113.7"),), True, (XFF,), id="fly-client-ip-absent"),
    pytest.param(FLY, DOCKER_PROXY, (*header_lines(FLY, ("203.0.113.7", "198.51.100.9")), (XFF, "203.0.113.7")), True, (XFF,), id="fly-client-ip-on-two-lines"),
    pytest.param(FLY, DOCKER_PROXY, ((FLY, "203.0.113.7:80"), (XFF, "203.0.113.7")), True, (XFF,), id="fly-client-ip-with-a-port"),
    pytest.param(REAL_IP, DOCKER_PROXY, tuple(header_lines(REAL_IP, ("203.0.113.7", "203.0.113.7"))), True, (REAL_IP,), id="x-real-ip-on-two-lines"),
]


@untrusted_forwarding_started_over
@pytest.mark.parametrize(("written", "client", "headers", "expected", "local"), CONFIGURED)
def test_the_configured_header_vouches_for_the_address_only_when_usable(monkeypatch: pytest.MonkeyPatch, written: str, client: tuple[str, int], headers: tuple[Header, ...], expected: bool, local: tuple[str, ...]) -> None:
    print_section(f"{HEADER_VARIABLE}={written!r}: {[name for name, _ in headers]} from {client[0]}")
    api = proxy_under_test(monkeypatch, written)

    result = api.forwarded_by_untrusted_proxy(http_request(headers, client))

    assert result is expected, f"{HEADER_VARIABLE}={written!r}, {headers!r} from {client[0]}: forwarded_by_untrusted_proxy gives {result!r}, not {expected!r}: the configured header carried once and holding one IP address vouches for the address; absent or unusable, it is as if unset"
    noted(api, local, (), f"with {HEADER_VARIABLE}={written!r}")
    warned = [record for record in api.log.records if record[1] == UNUSABLE]
    assert not warned, f"forwarded_by_untrusted_proxy never logs the warning of an unusable header: only client_address does, once per process: {warned}"
    assert api.log.records == first_noting(local, ()), f"only the first local noting logs, its one warning: {api.log.records}"
    no_address_logged(api, headers, client)
    print_success(f"✓ {result!r}")


# --- Noting and logging --------------------------------------------------------


@untrusted_forwarding_started_over
def test_the_first_local_noting_warns_once_and_later_ones_only_add_their_names(monkeypatch: pytest.MonkeyPatch) -> None:
    print_section("Three requests through local proxies nobody trusts: one warning")
    api = proxy_under_test(monkeypatch)
    first, first_peer = [(REAL_IP, "192.0.2.1"), *header_lines(XFF, ("198.51.100.4", "192.0.2.77"))], DOCKER_PROXY
    second, second_peer = [(FORWARDED, "for=198.51.100.5")], ("10.0.0.1", 50000)
    third, third_peer = [(XFF, "203.0.113.7")], ("::1", 50000)

    assert api.forwarded_by_untrusted_proxy(http_request(first, first_peer)) is True, "barrier: X-Real-IP and two X-Forwarded-For lines from the proxy on the Docker network come through a proxy nobody trusts"
    assert api.log.records == [untrusted_proxy((XFF, REAL_IP))], f"the first local noting logs one warning, word for word, with this request's names, each once, in the contract's order, and no other field: {api.log.records}"
    noted(api, (XFF, REAL_IP), (), "after the first request")

    later = [api.forwarded_by_untrusted_proxy(http_request(second, second_peer)), api.forwarded_by_untrusted_proxy(websocket(third, third_peer))]

    assert later == [True, True], f"barrier: Forwarded from 10.0.0.1 and X-Forwarded-For from ::1 come through proxies nobody trusts too: {later}"
    assert api.log.records == [untrusted_proxy((XFF, REAL_IP))], f"a later local noting logs nothing more, even with another header: {api.log.records}"
    noted(api, FORWARDING_HEADERS, (), "after the three requests")
    for headers, client in ((first, first_peer), (second, second_peer), (third, third_peer)):
        no_address_logged(api, headers, client)
    print_success(f"✓ one warning; noted local: {', '.join(FORWARDING_HEADERS)}")


@untrusted_forwarding_started_over
def test_the_first_public_noting_logs_one_info_and_later_ones_only_add_their_names(monkeypatch: pytest.MonkeyPatch) -> None:
    print_section("Two requests with forwarding headers from public peers: one info")
    api = proxy_under_test(monkeypatch)
    first, first_peer = [(XFF, "198.51.100.4")], ("203.0.113.9", 50000)
    second, second_peer = [(REAL_IP, "192.0.2.1"), (FORWARDED, "for=192.0.2.1")], ("8.8.8.8", 50000)

    assert api.forwarded_by_untrusted_proxy(http_request(first, first_peer)) is False, "barrier: X-Forwarded-For from a public peer is no proxy to skip"
    assert api.log.records == [public_forwarding((XFF,))], f"the first public noting logs one info, word for word, with this request's names and no other field: {api.log.records}"
    noted(api, (), (XFF,), "after the first request")

    again = api.forwarded_by_untrusted_proxy(http_request(second, second_peer))

    assert again is False, "barrier: X-Real-IP and Forwarded from a public peer are no proxy to skip either"
    assert api.log.records == [public_forwarding((XFF,))], f"a later public noting logs nothing more, even with other headers: {api.log.records}"
    noted(api, (), FORWARDING_HEADERS, "after the two requests")
    for headers, client in ((first, first_peer), (second, second_peer)):
        no_address_logged(api, headers, client)
    print_success(f"✓ one info; noted public: {', '.join(FORWARDING_HEADERS)}")


@untrusted_forwarding_started_over
@pytest.mark.parametrize("order", [pytest.param(("local", "public"), id="local-first"), pytest.param(("public", "local"), id="public-first")])
def test_each_class_logs_its_own_first_noting(monkeypatch: pytest.MonkeyPatch, order: tuple[str, str]) -> None:
    print_section(f"A {order[0]} noting, then a {order[1]} one, then both again")
    api = proxy_under_test(monkeypatch)
    # Each class: (headers, peer, what forwarded_by_untrusted_proxy says, the record of its first noting)
    requests: dict[str, tuple[list[Header], tuple[str, int], bool, Record]] = {
        "local": ([(XFF, "198.51.100.4")], DOCKER_PROXY, True, untrusted_proxy((XFF,))),
        "public": ([(REAL_IP, "192.0.2.1")], ("203.0.113.9", 50000), False, public_forwarding((REAL_IP,))),
    }
    results: list[bool] = []

    for peer_class in (*order, *order):
        headers, client, _, _ = requests[peer_class]
        results.append(api.forwarded_by_untrusted_proxy(http_request(headers, client)))

    assert results == [requests[peer_class][2] for peer_class in (*order, *order)], f"barrier: the local request comes through a proxy nobody trusts, the public one does not: {results}"
    assert api.log.records == [requests[peer_class][3] for peer_class in order], f"each class logs its own first noting, whichever came first, and nothing more: {api.log.records}"
    noted(api, (XFF,), (REAL_IP,), "after both classes, twice each")
    for headers, client, _, _ in requests.values():
        no_address_logged(api, headers, client)
    print_success(f"✓ {[record[0] for record in api.log.records]}")


#: (h) Names as the module may hold them, in any order, and as untrusted_forwarding_seen gives them back.
HELD = [
    pytest.param({REAL_IP}, (REAL_IP,), id="one"),
    pytest.param({REAL_IP, FORWARDED}, (FORWARDED, REAL_IP), id="two"),
    pytest.param({REAL_IP, XFF, FORWARDED}, FORWARDING_HEADERS, id="all-three"),
]


@untrusted_forwarding_started_over
@pytest.mark.parametrize("peer_class", PEER_CLASSES)
@pytest.mark.parametrize(("held", "given"), HELD)
def test_untrusted_forwarding_seen_gives_the_names_in_the_contracts_order(monkeypatch: pytest.MonkeyPatch, peer_class: str, held: set[str], given: tuple[str, ...]) -> None:
    print_section(f"untrusted_forwarding_seen({peer_class!r}) with {sorted(held)} noted")
    api = proxy_under_test(monkeypatch)
    untrusted_forwarding()[peer_class].update(held)  # emptied in place again after the test, by its fixture

    expected = {peer_class: given, **{other: () for other in PEER_CLASSES if other != peer_class}}

    noted(api, expected["local"], expected["public"], f"with {sorted(held)} noted under {peer_class!r}")
    print_success(f"✓ {given}")


# --- A Request and a WebSocket alike ---------------------------------------------


#: (h) The core cases: (setting, peer, headers, what forwarded_by_untrusted_proxy says, the names noted local and public).
CORE = [
    pytest.param(None, DOCKER_PROXY, ((XFF, "203.0.113.7"),), True, (XFF,), (), id="a-proxy-on-the-docker-network"),
    pytest.param(None, ("127.0.0.1", 50000), ((REAL_IP, "203.0.113.7"),), True, (REAL_IP,), (), id="a-proxy-on-the-same-host-x-real-ip"),
    pytest.param(None, ("10.0.0.1", 50000), ((FORWARDED, "for=203.0.113.7"),), True, (FORWARDED,), (), id="a-proxy-on-the-lan-forwarded"),
    pytest.param(None, ("203.0.113.9", 50000), ((XFF, "198.51.100.4"),), False, (), (XFF,), id="a-public-peer"),
    pytest.param(None, ("10.0.0.9", 0), ((XFF, "198.51.100.4, 10.0.0.9"),), False, (), (), id="a-client-uvicorn-took-from-x-forwarded-for"),
    pytest.param(None, None, ((XFF, "203.0.113.7"),), False, (), (), id="no-client"),
    pytest.param(None, DOCKER_PROXY, (), False, (), (), id="no-forwarding-header"),
    pytest.param(FLY, DOCKER_PROXY, ((FLY, "203.0.113.7"), (XFF, "203.0.113.7")), False, (), (), id="the-configured-header-usable"),
    pytest.param(FLY, DOCKER_PROXY, ((FLY, "203.0.113.7:80"), (XFF, "203.0.113.7")), True, (XFF,), (), id="the-configured-header-unusable"),
]


@untrusted_forwarding_started_over
@pytest.mark.parametrize(("written", "client", "headers", "expected", "local", "public"), CORE)
@pytest.mark.parametrize("connect", CONNECTIONS)
def test_a_request_and_a_websocket_alike(monkeypatch: pytest.MonkeyPatch, connect: Connect, written: str | None, client: tuple[str, int] | None, headers: tuple[Header, ...], expected: bool, local: tuple[str, ...], public: tuple[str, ...]) -> None:
    print_section(f"{HEADER_VARIABLE}={written!r}: {[name for name, _ in headers]} from {client!r}")
    api = proxy_under_test(monkeypatch, written)

    result = api.forwarded_by_untrusted_proxy(connect(headers, client))

    assert result is expected, f"{HEADER_VARIABLE}={written!r}, {headers!r} from {client!r}: forwarded_by_untrusted_proxy gives {result!r}, not {expected!r}: a WebSocket is an HTTPConnection as a Request is"
    noted(api, local, public, f"after {headers!r} from {client!r}")
    assert api.log.records == first_noting(local, public), f"the first noting of its class logs, and only it: {api.log.records}"
    no_address_logged(api, headers, client)
    print_success(f"✓ {result!r}")


# --- Behind uvicorn's own ProxyHeadersMiddleware -----------------------------------


#: (h) uvicorn's own ProxyHeadersMiddleware in front of the app, as the server runs it: (FORWARDED_ALLOW_IPS, the peer, the
#: headers, the host of the client the app sees, what forwarded_by_untrusted_proxy says, the names noted local and public).
THROUGH_UVICORN = [
    pytest.param(TRUSTED_BY_DEFAULT, ("127.0.0.1", 50000), ((XFF, "203.0.113.7"),), "203.0.113.7", False, (), (), id="by-default-a-proxy-on-the-same-host-is-trusted"),
    pytest.param(TRUSTED_BY_DEFAULT, DOCKER_PROXY, ((XFF, "203.0.113.7"),), "172.18.0.2", True, (XFF,), (), id="by-default-a-proxy-on-the-docker-network-is-not-r13-sec6"),
    pytest.param("172.16.0.0/12", DOCKER_PROXY, ((XFF, "203.0.113.7"),), "203.0.113.7", False, (), (), id="the-docker-network-trusted"),
    pytest.param("172.16.0.0/12", DOCKER_PROXY, ((XFF, "203.0.113.7:51000"),), "203.0.113.7", False, (), (), id="the-docker-network-trusted-a-port"),
    pytest.param("*", DOCKER_PROXY, ((XFF, "198.51.100.4, 203.0.113.7"),), "198.51.100.4", False, (), (), id="every-proxy-trusted-the-first-value"),
    pytest.param(TRUSTED_BY_DEFAULT, DOCKER_PROXY, ((REAL_IP, "203.0.113.7"),), "172.18.0.2", True, (REAL_IP,), (), id="x-real-ip-alone-which-uvicorn-ignores"),
    pytest.param(TRUSTED_BY_DEFAULT, ("127.0.0.1", 50000), ((FORWARDED, "for=203.0.113.7"),), "127.0.0.1", True, (FORWARDED,), (), id="forwarded-alone-which-uvicorn-ignores-even-from-a-proxy-it-trusts"),
    pytest.param(TRUSTED_BY_DEFAULT, ("203.0.113.9", 50000), ((XFF, "198.51.100.4"),), "203.0.113.9", False, (), (XFF,), id="by-default-a-public-peer-is-not-trusted"),
]


@untrusted_forwarding_started_over
@pytest.mark.parametrize(("trusted_hosts", "client", "headers", "host", "expected", "local", "public"), THROUGH_UVICORN)
def test_behind_uvicorns_own_proxy_headers_middleware(monkeypatch: pytest.MonkeyPatch, trusted_hosts: str, client: tuple[str, int], headers: tuple[Header, ...], host: str, expected: bool, local: tuple[str, ...], public: tuple[str, ...]) -> None:
    print_section(f"FORWARDED_ALLOW_IPS={trusted_hosts!r}: {[name for name, _ in headers]} from {client[0]}")
    api = proxy_under_test(monkeypatch)

    seen_host, result = through_uvicorn(api, trusted_hosts, headers, client)

    assert seen_host == host, f"barrier: behind ProxyHeadersMiddleware(trusted_hosts={trusted_hosts!r}) the app sees the client {seen_host!r}, not {host!r}: uvicorn no longer does what this case describes"
    assert result is expected, f"FORWARDED_ALLOW_IPS={trusted_hosts!r}, {headers!r} from {client[0]}, the app seeing {seen_host!r}: forwarded_by_untrusted_proxy gives {result!r}, not {expected!r}"
    noted(api, local, public, f"after {headers!r} from {client[0]} through uvicorn")
    assert api.log.records == first_noting(local, public), f"the first noting of its class logs, and only it: {api.log.records}"
    no_address_logged(api, headers, client)
    print_success(f"✓ the app sees {seen_host!r}: {result!r}")


# --- rate_limit_address: the address the per-address limits count -------------------


#: (h) Requests through a local proxy nobody trusts: (peer, headers, the names noted local).
THROUGH_A_PROXY_NOBODY_TRUSTS = [
    pytest.param(DOCKER_PROXY, ((XFF, "203.0.113.7"),), (XFF,), id="x-forwarded-for-from-the-docker-network"),
    pytest.param(("127.0.0.1", 50000), ((REAL_IP, "203.0.113.7"),), (REAL_IP,), id="x-real-ip-from-the-same-host"),
    pytest.param(("10.0.0.1", 50000), ((FORWARDED, "for=203.0.113.7"),), (FORWARDED,), id="forwarded-from-the-lan"),
]


@untrusted_forwarding_started_over
@pytest.mark.parametrize(("client", "headers", "names"), THROUGH_A_PROXY_NOBODY_TRUSTS)
@pytest.mark.parametrize("connect", CONNECTIONS)
def test_rate_limit_address_is_none_through_a_proxy_nobody_trusts(monkeypatch: pytest.MonkeyPatch, connect: Connect, client: tuple[str, int], headers: tuple[Header, ...], names: tuple[str, ...]) -> None:
    print_section(f"rate_limit_address: {list(names)} from {client[0]}")
    api = proxy_under_test(monkeypatch)
    rate_limit_address = rate_limit_address_function()
    connection = connect(headers, client)

    first, again = rate_limit_address(connection), rate_limit_address(connection)

    assert first is None and again is None, f"{list(names)} from {client[0]}, through a local proxy nobody trusts: rate_limit_address gives {first!r}, then {again!r}, not None: no per-address limit counts a request whose address is the proxy's"
    assert api.log.records == [untrusted_proxy(names)], f"the warning of the proxy nobody trusts, once: a second call logs nothing more, and rate_limit_address logs nothing of its own: {api.log.records}"
    assert api.forwarded_by_untrusted_proxy(connection) is True, "barrier: forwarded_by_untrusted_proxy says the same of this request"
    noted(api, names, (), "after two calls of rate_limit_address")
    no_address_logged(api, headers, client)
    print_success("✓ None twice, one warning")


#: (h) Requests the per-address limits count: (setting, peer, headers, the address, the names noted public). The address is
#: each time exactly what client_address gives.
COUNTED = [
    pytest.param(None, ("10.0.0.1", 50000), (), "10.0.0.1", (), id="no-forwarding-header-the-peer"),
    pytest.param(None, ("testclient", 50000), (), "testclient", (), id="no-forwarding-header-a-name-as-written"),
    pytest.param(None, None, (), None, (), id="no-forwarding-header-no-client"),
    pytest.param(None, ("203.0.113.9", 50000), ((XFF, "198.51.100.4"),), "203.0.113.9", (XFF,), id="a-public-peer-its-own-address-noted-public"),
    pytest.param(None, ("10.0.0.9", 0), ((XFF, "198.51.100.4, 10.0.0.9"),), "10.0.0.9", (), id="the-client-uvicorn-took-from-x-forwarded-for"),
    pytest.param(FLY, DOCKER_PROXY, ((FLY, "2001:db8::7"), (XFF, "2001:db8::7")), "2001:db8::7", (), id="the-configured-header-its-address"),
    pytest.param(FLY, DOCKER_PROXY, ((FLY, "2001:0DB8:0000:0000:0000:0000:0000:0007"), (XFF, "203.0.113.7")), "2001:db8::7", (), id="the-configured-header-its-address-normalised"),
]


@untrusted_forwarding_started_over
@pytest.mark.parametrize(("written", "client", "headers", "address", "public"), COUNTED)
@pytest.mark.parametrize("connect", CONNECTIONS)
def test_rate_limit_address_is_exactly_the_client_address_otherwise(monkeypatch: pytest.MonkeyPatch, connect: Connect, written: str | None, client: tuple[str, int] | None, headers: tuple[Header, ...], address: str | None, public: tuple[str, ...]) -> None:
    print_section(f"rate_limit_address: {HEADER_VARIABLE}={written!r}, {[name for name, _ in headers]} from {client!r}")
    api = proxy_under_test(monkeypatch, written)
    rate_limit_address = rate_limit_address_function()
    connection = connect(headers, client)

    result = rate_limit_address(connection)

    given = api.client_address(connection)
    assert exactly(given, address), f"barrier: client_address gives {given!r}, not {address!r}"
    assert exactly(result, given), f"{HEADER_VARIABLE}={written!r}, {headers!r} from {client!r}, no proxy nobody trusts: rate_limit_address gives {result!r}, not exactly client_address's {given!r}"
    assert api.forwarded_by_untrusted_proxy(connection) is False, "barrier: this request did not come through a local proxy nobody trusts"
    noted(api, (), public, "after rate_limit_address")
    assert api.log.records == first_noting((), public), f"rate_limit_address logs nothing of its own: only the first public noting logs, its one info: {api.log.records}"
    no_address_logged(api, headers, client)
    print_success(f"✓ {result!r}")


@untrusted_forwarding_started_over
@pytest.mark.parametrize("connect", CONNECTIONS)
def test_rate_limit_address_hides_neither_warning(monkeypatch: pytest.MonkeyPatch, connect: Connect) -> None:
    print_section(f"rate_limit_address: {FLY} malformed and X-Forwarded-For from {DOCKER_PROXY[0]}")
    api = proxy_under_test(monkeypatch, FLY)
    rate_limit_address = rate_limit_address_function()
    lines = ("203.0.113.7:80",)
    headers = [*header_lines(FLY, lines), (XFF, "203.0.113.7")]
    connection = connect(headers, DOCKER_PROXY)

    first, again = rate_limit_address(connection), rate_limit_address(connection)

    assert first is None and again is None, f"{FLY} unusable, so as if unset, and X-Forwarded-For from {DOCKER_PROXY[0]}: rate_limit_address gives {first!r}, then {again!r}, not None"
    expected = [unusable(FLY_LOWER, lines), untrusted_proxy((XFF,))]
    assert api.log.records == expected, f"exactly two warnings, each once, word for word: client_address's (called first, so never hidden), then the one of the proxy nobody trusts:\n  expected {expected}\n  got      {api.log.records}"
    no_address_logged(api, headers, DOCKER_PROXY)
    print_success("✓ None twice; the two warnings, once each")


# --- What the admin sees ------------------------------------------------------------


@untrusted_forwarding_started_over
def test_the_admin_check_warns_once_a_request_came_through_a_proxy_nobody_trusts(monkeypatch: pytest.MonkeyPatch) -> None:
    print_section("check_client_address, before and after a request through a proxy nobody trusts")
    api = proxy_under_test(monkeypatch)
    check_client_address = h36_function_of(importlib.import_module(CONFIG_AUDIT), "check_client_address", CONFIG_AUDIT_PATH)
    before = check_client_address()
    assert (before.check_id, before.severity, before.i18n_key, before.detail) == ("platform.client_address", "ok", "instance.checks.clientAddress.ok", {}), f"nothing noted yet, as at startup: the check is ok, not {before}"
    request = http_request([(XFF, "203.0.113.7")], DOCKER_PROXY)
    assert api.forwarded_by_untrusted_proxy(request) is True, "barrier: X-Forwarded-For from the proxy on the Docker network comes through a proxy nobody trusts"

    after = check_client_address()

    actual = (after.check_id, after.severity, after.i18n_key, after.detail, after.summary)
    expected = ("platform.client_address", "warning", "instance.checks.clientAddress.untrustedProxy", {"headers": XFF}, UNTRUSTED_PROXY)
    assert actual == expected, f"after a request through a proxy nobody trusts, the admin's check warns, naming its header:\n  expected {expected}\n  got      {actual}"
    shown = [address for address in (DOCKER_PROXY[0], "203.0.113.7") if address in repr(after)]
    assert not shown, f"the check holds no address (N58): {shown} in {after}"
    print_success(f"✓ ok, then {after.severity} {after.i18n_key}")
