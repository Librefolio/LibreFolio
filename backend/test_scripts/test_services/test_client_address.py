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
    usable or absent header re-arms nothing; ``reset_client_address_cache()`` re-arms the warning.
(e) The configured name is read once per process: after the first call, a change of the environment changes nothing
    until ``reset_client_address_cache()``, and the next call reads it. Every way: another name, set, unset.
(f) ``client_rate_key(address)``, the key of an address for a per-client limit, today's rule of ``address_key`` in
    ``backend/app/services/email/flows.py`` (workstream E switches to this one in its own lot): no key for ``None`` nor
    ``""``; an IPv4 address as is; an IPv4-mapped one as its IPv4; any other IPv6 address by its /64, in canonical form,
    a zone ignored; anything else as written. The values are pinned here: E's function is not imported.
(g) ``mask_client_address(address)``, the form an address may take in a log: nothing for ``None`` nor ``""``; an IPv4
    address by its /24; an IPv4-mapped one as its IPv4, so by its /24; any other IPv6 address by its /48; anything else
    as written.

How. Every test runs with ``LIBREFOLIO_TEST_MODE=1`` (``get_settings()`` reads no ``.env``), ``LIBREFOLIO_TEST_DATA_DIR``
under ``tmp_path`` (``get_settings()`` never looks at the lane's data), the profile and the setting removed, all through
``monkeypatch``. ``reset_client_address_cache()`` runs before and after each test, the last time with the environment of
the run put back, so that no test inherits the name another read nor the warning another spent. A case that configures
the setting checks first that ``get_settings()`` reads it so (a barrier), then resets the cache: it holds whether the
reset reads the name again at once or leaves it to the next call. ``Settings`` itself is built with ``_env_file=None``.
A connection is a Starlette ``Request`` or ``WebSocket`` on a raw scope, no server: header names in lower case, as
uvicorn puts them there (h11 and httptools lower-case every name, and Starlette's ``Headers`` compares lower-case names),
a repeated header as repeated lines, another header between them as when a proxy appends its own. The module's
``logger`` is replaced by a recorder of ``(level, summary, fields)``. The module is imported when a test runs and the
setting is looked up in ``Settings.model_fields``, so this file collects before either exists and each test fails on its
own barrier: ``backend/app/services/platform/client_address.py is missing (P17)``, or ``LIBREFOLIO_CLIENT_IP_HEADER is
not a Settings field (P17)``. Red until P17 lands. No DB, no server, no network, no clock.
"""

from __future__ import annotations

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


def _reset_if_there() -> None:
    """``reset_client_address_cache()``, once the module and the function exist. Before they do, nothing: each test then
    fails on its own barrier, never in a fixture."""
    try:
        module = importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != MODULE:  # the module is there and something it imports is not: that error is the finding
            raise
        return
    reset = getattr(module, "reset_client_address_cache", None)
    if callable(reset):
        reset()


@pytest.fixture
def fresh_client_address_cache() -> Iterator[None]:
    """The module's cache started over before and after the test: no test inherits the name another read nor the warning
    another spent, and whatever runs after this file finds the cache as a new process does."""
    _reset_if_there()
    yield
    _reset_if_there()


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
    """``client_address`` and ``reset_client_address_cache``, the module's logger recorded."""
    module = client_address_module()
    return UnderTest(function_of(module, "client_address"), function_of(module, "reset_client_address_cache"), record_logs(monkeypatch, module))


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
    so, then start the module's cache over: whether its reset reads the name at once or at the next call, it is this one."""
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
    print_section("One warning per process, re-armed by reset_client_address_cache()")
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
    assert api.log.at("warning") == [unusable(FLY_LOWER, first), unusable(FLY_LOWER, rearmed)], f"reset_client_address_cache() re-arms the warning: the next malformed header warns again, with its own counts: {api.log.at('warning')}"
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

    assert exactly(kept, before), f"{HEADER_VARIABLE} went from {first!r} to {then!r} after the first call, and client_address gives {kept!r}, not {before!r}: the name is read once per process, and a change waits for reset_client_address_cache()"
    api.reset()
    renewed = api.client_address(http_request(EVERY_CLIENT_HEADER))
    assert exactly(renewed, after), f"after reset_client_address_cache(), with {HEADER_VARIABLE}={then!r}, client_address gives {renewed!r}, not {after!r}: the next call reads the name again"
    print_success(f"✓ {initial!r}, still {kept!r}, after the reset {renewed!r}")


# =============================================================================
# (f) client_rate_key: THE KEY OF AN ADDRESS FOR A PER-CLIENT LIMIT
# =============================================================================


#: The address, and its key. Today's rule of address_key (backend/app/services/email/flows.py), pinned value by value.
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
# (g) mask_client_address: THE FORM AN ADDRESS MAY TAKE IN A LOG
# =============================================================================


#: The address, and its masked form.
MASKS = [
    pytest.param(None, None, id="no-address"),
    pytest.param("", None, id="an-empty-address"),
    pytest.param("testclient", "testclient", id="a-name-as-written"),
    pytest.param("/run/librefolio/zq.sock", "/run/librefolio/zq.sock", id="a-socket-path-as-written"),
    pytest.param("203.0.113.7", "203.0.113.0/24", id="ipv4-by-its-24"),
    pytest.param("10.0.0.255", "10.0.0.0/24", id="ipv4-another-24"),
    pytest.param("::ffff:203.0.113.7", "203.0.113.0/24", id="ipv4-mapped-as-its-ipv4-by-its-24"),
    pytest.param("2001:db8:1:2::7", "2001:db8:1::/48", id="ipv6-by-its-48"),
    pytest.param("2001:0DB8:0001:FFFF:0000:0000:0000:0007", "2001:db8:1::/48", id="ipv6-in-full-and-in-capitals"),
    pytest.param("2001:db8:2::1", "2001:db8:2::/48", id="ipv6-the-next-48"),
    pytest.param("::1", "::/48", id="ipv6-loopback"),
]


@pytest.mark.parametrize(("address", "masked"), MASKS)
def test_the_masked_form_of_an_address(address: str | None, masked: str | None) -> None:
    print_section(f"mask_client_address({address!r})")
    mask_client_address = function_of(client_address_module(), "mask_client_address")

    result = mask_client_address(address)

    assert exactly(result, masked), f"mask_client_address({address!r}) is {result!r}, expected {masked!r}: an IPv4 address by its /24, an IPv4-mapped one as its IPv4, any other IPv6 address by its /48, anything else as written, nothing without an address"
    print_success(f"✓ {address!r} → {result!r}")
