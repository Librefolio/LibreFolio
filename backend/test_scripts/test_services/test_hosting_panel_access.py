"""
H-61 checkpoint 1 · how a hosting panel gets in (LibreFolio 1.3, workstream H, platform): the token of the panel's status
route, and the one FastAPI dependency every route of the hosting panel takes, for its three scopes — the instance backup,
the scheduled wake-up and the status. The contract is H-61 CP1's, §1 and §2.

Under test:

- ``backend/app/config/hosting_panel.py`` (§1, new). ``PANEL_STATUS_TOKEN_VARIABLE`` is ``LIBREFOLIO_PANEL_STATUS_TOKEN``.
  ``HostingPanelConfigError(ValueError)`` is shaped like ``BackupConfigError``: built from a variable, a code and a
  message, it carries ``variable`` and ``code``. ``panel_status_token()`` follows the rules of ``backup_download_token()``
  and ``wake_token()``, read at each call: the variable as written, or else the text of its ``_FILE`` without a leading BOM
  and its trailing line breaks (``env_secret``); the variable wins, a blank one counts as unset, neither set is None.
  Anything but visible ASCII, a space or a tab included, checked first: ``PANEL_STATUS_TOKEN_NOT_VISIBLE_ASCII``; under
  ``PANEL_TOKEN_MIN_LENGTH`` (32): ``PANEL_STATUS_TOKEN_TOO_SHORT``; the variable named, never the value. A ``_FILE`` that
  cannot give its secret: ``SecretFileError``.
- ``backend/app/services/platform/hosting_panel/access.py`` (§2, new). ``PanelScope`` (``backup``, ``wake``, ``status``)
  and ``panel_access(scope)``, the dependency, the same object for the same scope, on the scope's
  ``HTTPBearer(auto_error=False)`` (``BackupPanelToken``, ``WakeToken``, ``PanelStatusToken``), returning
  ``PanelCaller(scope, credential="token")``, a frozen dataclass. In order: (1) the scope's token — unusable: its error
  line as today, one ``Hosting panel request`` WARNING (``unavailable``, ``unusable``), 503; unset: 404 ``Not Found``, no
  line, nothing counted, the limiter not read; (2) the limiter, keyed by ``client_rate_key(rate_limit_address(request))``
  and skipped without a key — over its limit: one WARNING (``limited``, ``retry_after``), 429 ``panel_too_many_attempts``
  with ``Retry-After`` the seconds rounded up, at least 1, the credential not looked at; (3) the credential,
  ``Authorization: Bearer`` through ``hmac.compare_digest`` on the UTF-8 bytes — missing or different: ``hit``, one
  WARNING (``refused``, ``missing`` or ``mismatch``), the scope's 401 with ``WWW-Authenticate: Bearer``; (4) accepted: one
  INFO line, the caller, never counted. One limiter for the module, ``PANEL_ATTEMPTS = new_panel_attempts()`` (a new
  ``SlidingWindowLimiter(limit=20, window_seconds=600)`` at each call of the factory), shared by the three scopes and
  read at each call. A line carries ``scope``, ``method``, ``path`` (``scope["path"]``, never the query), ``outcome``,
  ``credential`` and, where its outcome has one, ``reason`` or ``retry_after``, plus the request's ``request_id`` from
  structlog's contextvars; never a token, a value sent, a header, the query nor the client's address.

The tests:

- HPA-001..009, ``panel_status_token()`` (§1): the variable's name and the error's shape (001); unset or blank, None
  (002); the variable as written, read at each call (003); the ``_FILE`` (004); both set, a blank variable beside a file
  (005); 31 characters ``PANEL_STATUS_TOKEN_TOO_SHORT``, 32 taken (006); anything but visible ASCII
  ``PANEL_STATUS_TOKEN_NOT_VISIBLE_ASCII``, checked before the length (007); a ``_FILE`` that cannot give it,
  ``SecretFileError`` (008); value for value the outcome of ``backup_download_token()`` and ``wake_token()``, and the
  edges of visible ASCII taken as written (009).
- HPA-010..017, the dependency (§2): the module's names, the same dependency for the same scope, the frozen caller, the
  limiter's factory and constants (010); each scope's own bearer scheme in OpenAPI (011); a scope whose token is unset
  (012), unusable (013); a request without a bearer credential (014), with another one (015), with the scope's token,
  from the variable or the ``_FILE`` (016); no scope's token opens another scope (017).
- HPA-020..029, the limiter: 20 refusals, then 429 even to the right token (020); ``Retry-After`` rounded up, at least 1
  (021); the window passed, served again (022); another address served meanwhile (023); the three scopes add up (024); a
  right credential never counted (025); an IPv6 client by its /64 (026); an address read as None never limited (027);
  the token read before the limiter (028); the key is the address ``rate_limit_address`` gives (029).
- HPA-030..032, the lines: the path, never the query (030); the request id behind the request-id middleware (031); no
  secret in a line, a field or an answer, every outcome at once (032).
- HPA-040..042, constant time, structurally: one ``hmac.compare_digest`` of the UTF-8 bytes (040); its answer is the
  decision (041); over the limit, no comparison at all (042).

How. Pure: no server, no database, no network, no file outside ``tmp_path``. A fresh ``FastAPI()`` holds one test route per
scope, each taking ``Depends(panel_access(PanelScope(<scope>)))`` and recording the caller it gets; the backup one has a
path parameter, so a line's path is the request's own, never the route's template. The requests go through
``httpx.ASGITransport`` in this process, its ``client`` the peer; every request carries a canary header, and ends on the
check that no configured token, no value sent, no header value, no query value and not the client's address shows in the
answer, its headers or a captured line. The log of each request is captured with
``structlog.testing.capture_logs(processors=[merge_contextvars])`` behind a barrier, a canary logged through the access
module's own ``logger``; lines are compared whole, keys included. The variables of the three tokens and their ``_FILE``s
are deleted before each test, then set through ``monkeypatch``. ``PANEL_ATTEMPTS``, practically unlimited in every test
process (the shared conftest), is replaced through ``monkeypatch`` by a ``SlidingWindowLimiter(20, 600)`` on a fake clock
which also records the calls the dependency makes (``peek``, ``hit``); the test reads it without recording. Nothing
sleeps: the fake clock moves. The address ``client_address`` reads is made deterministic: its ``_configured_header`` is
replaced through ``monkeypatch`` (``LIBREFOLIO_CLIENT_IP_HEADER`` unset, or HPA-029's header), and what a request notes in
that module's process state (the forwarding headers of a proxy nobody trusts, the warned flag) is put back as it was
after each test. ``hmac`` is spied through ``monkeypatch`` on the access module's own ``hmac`` attribute, delegating to
the real one. The test routes are built once per process and kept, as FastAPI caches the context of an endpoint by its
``id()``. This file does not use ``from __future__ import annotations``: a test route's ``Annotated[..., Depends(...)]``
is built from a local dependency.

Red today: neither module exists. The §1 tests fail on «H-61 CP1: backend/app/config/hosting_panel.py is missing»; HPA-010
on «H-61 CP1: backend/app/services/platform/hosting_panel/access.py is missing», and every other §2 test on that same
message, at the setup of its ``panel`` fixture. The file itself collects: it imports only what exists today. Since the
factory of the limiter (20/10), HPA-010 is red on «H-61 CP1: backend.app.services.platform.hosting_panel.access gives no
new_panel_attempts» until ``new_panel_attempts`` exists.
"""

import asyncio
import dataclasses
import enum
import hmac
import importlib
import math
import re
import secrets
import uuid
from collections.abc import Callable, Hashable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Annotated, Any

import httpx
import pytest
from fastapi import Depends, FastAPI, Request
from structlog.contextvars import merge_contextvars
from structlog.testing import capture_logs

from backend.app.config import SecretFileError
from backend.app.config.backup import PANEL_TOKEN_CHARACTERS, PANEL_TOKEN_MIN_LENGTH, BackupConfigError, backup_download_token
from backend.app.config.sleep_wake import SleepWakeConfigError, wake_token
from backend.app.services.platform import client_address as client_address_module
from backend.app.services.platform.request_id import RequestIdMiddleware
from backend.app.utils.runtime.rate_window import RateDecision, SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section, print_success

# =============================================================================
# THE CONTRACT, SPELLED OUT
# =============================================================================

#: The modules of H-61 CP1, imported when a test needs them, and their files for the red message.
HOSTING_CONFIG_MODULE = "backend.app.config.hosting_panel"
ACCESS_MODULE = "backend.app.services.platform.hosting_panel.access"
_MODULE_FILES = {
    HOSTING_CONFIG_MODULE: "backend/app/config/hosting_panel.py",
    ACCESS_MODULE: "backend/app/services/platform/hosting_panel/access.py",
}

#: The three scopes of the panel, as ``PanelScope``'s values.
BACKUP, WAKE, STATUS = "backup", "wake", "status"
SCOPES = (BACKUP, WAKE, STATUS)

#: The variables of the tokens, as .env.example and the deployments write them: spelled out here, so a rename shows.
STATUS_VARIABLE = "LIBREFOLIO_PANEL_STATUS_TOKEN"
FILE_SUFFIX = "_FILE"
STATUS_FILE_VARIABLE = STATUS_VARIABLE + FILE_SUFFIX
VARIABLES = {BACKUP: "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN", WAKE: "LIBREFOLIO_WAKE_TOKEN", STATUS: STATUS_VARIABLE}
#: Every variable of the three tokens: none is inherited from the runner's environment.
TOKEN_VARIABLES = tuple(name for variable in VARIABLES.values() for name in (variable, variable + FILE_SUFFIX))
#: The shortest token the server takes.
MIN_LENGTH = 32
#: The characters a token may hold, in order: the visible ASCII ones, from "!" (0x21) to "~" (0x7E).
VISIBLE_ASCII = "".join(chr(code) for code in range(0x21, 0x7F))

#: The bearer scheme of each scope in OpenAPI.
SCHEMES = {BACKUP: "BackupPanelToken", WAKE: "WakeToken", STATUS: "PanelStatusToken"}

#: The answers, whole: status and body. The 401 and 503 of backup and wake are those of today.
OFF_ANSWER = (404, {"detail": "Not Found"})
UNAUTHORIZED = {
    BACKUP: (401, {"detail": {"code": "backup_panel_unauthorized", "message": "A valid panel token is required"}}),
    WAKE: (401, {"detail": {"code": "wake_unauthorized", "message": "A valid wake-up token is required"}}),
    STATUS: (401, {"detail": {"code": "panel_status_unauthorized", "message": "A valid panel status token is required"}}),
}
UNAVAILABLE = {
    BACKUP: (503, {"detail": {"code": "backup_panel_unavailable", "message": "The panel token of this instance cannot be used"}}),
    WAKE: (503, {"detail": {"code": "wake_unavailable", "message": "The wake-up token of this instance cannot be used"}}),
    STATUS: (503, {"detail": {"code": "panel_status_unavailable", "message": "The panel status token of this instance cannot be used"}}),
}
TOO_MANY = (429, {"detail": {"code": "panel_too_many_attempts", "message": "Too many refused panel credentials from this address"}})

#: The line of every request the dependency decides, and the error line of each scope's unusable token, word for word.
PANEL_LINE = "Hosting panel request"
UNUSABLE_LINES = {
    BACKUP: "The hosting panel's backup token cannot be used: its routes refuse every request",
    WAKE: "The wake-up token cannot be used: the scheduled wake-up refuses every request",
    STATUS: "The panel status token cannot be used: the status route refuses every request",
}
#: The keys a line of the dependency may hold: its fields, the request id the contextvars give it, and what the capture adds.
LINE_KEYS = frozenset({"event", "log_level", "scope", "method", "path", "outcome", "credential", "reason", "retry_after", "request_id"})
CAPTURE_CANARY = "H-61 test: the capture sees the access module's logger"

#: The limiter of the contract: 20 refused credentials per address in any 600 seconds.
PANEL_LIMIT = 20
PANEL_WINDOW_SECONDS = 600
#: When the fake clock starts: whole seconds, so a Retry-After counted from a hit at the start is a whole number.
START = 1_000.0

#: The test routes, one per scope: method and path. The backup one has a path parameter, so the line's path is the
#: request's own; the three methods differ, so the line's method is the request's own.
ROUTES = {
    BACKUP: ("DELETE", "/hp-test/backup/panel/jobs/{job_id}"),
    WAKE: ("POST", "/hp-test/system/wake-sync"),
    STATUS: ("GET", "/hp-test/panel/status"),
}
NOWHERE = "/hp-test/nowhere"

#: The peers of the requests (``httpx.ASGITransport``'s ``client``): public addresses, each a key of its own.
PEER = ("203.0.113.50", 50000)
OTHER_PEER = ("198.51.100.60", 50001)
#: A reverse proxy in front of the container, on the Docker network, which LibreFolio does not trust, and the address it
#: forwards: ``rate_limit_address`` reads such a request as None (decision N70).
DOCKER_PROXY = ("172.18.0.2", 40000)
FORWARDED_CLIENT = "198.51.100.4"
#: HPA-029: the header a trusted proxy would set with the client's address (``LIBREFOLIO_CLIENT_IP_HEADER``).
CLIENT_IP_HEADER = "X-Hp-Client-Ip"
#: Three IPv6 clients: the first two in one /64, which ``client_rate_key`` makes one key, the third in the next /64.
IPV6_PEER = ("2001:db8:1:2::10", 50002)
IPV6_SAME_64 = ("2001:db8:1:2::99", 50003)
IPV6_NEXT_64 = ("2001:db8:1:3::10", 50004)
IPV6_KEY = "2001:db8:1:2::/64"

#: A header every request carries, whose value no line nor answer may hold.
CANARY_HEADER = "X-Hp-Canary"
BASE_URL = "http://hp.test"
#: Every in-process call ends within this, or the test fails instead of hanging.
CALL_SECONDS = 10.0
REQUEST_ID_SHAPE = re.compile(r"[0-9a-f]{16}")

#: Files that cannot give a token, by what is wrong with them: each builder leaves such a thing at ``path``.
BROKEN_FILES: dict[str, Callable[[Path], object]] = {
    "file-missing": lambda path: None,
    "file-unreadable": lambda path: path.mkdir(),
    "file-empty": lambda path: path.write_bytes(b""),
    "file-blank": lambda path: path.write_bytes(b" \n\r\n"),
}
#: Tokens the server cannot use, by kind: too short; a space inside (not visible ASCII); a ``_FILE`` that gives none.
UNUSABLE_KINDS = ("too-short", "a-space-inside", "file-missing", "file-unreadable")
#: A scope's token unset: neither variable, a blank variable, a blank ``_FILE`` variable.
UNSET_KINDS = ("neither-variable", "blank-variable", "blank-file-variable")


def a_token() -> str:
    """A token as the documentation suggests one (``openssl rand -hex 32``): 64 characters, new at each call."""
    return secrets.token_hex(32)


# =============================================================================
# THE MODULES OF H-61, IMPORTED WHEN A TEST RUNS
# =============================================================================


def _module(name: str) -> ModuleType:
    """The new module ``name``, imported when a test needs it: before H-61 neither it nor its package exists, and the rest
    of this file must still be collected and run."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        # The module or its package missing is the red; a module it imports missing is a finding, raised as it is.
        if error.name not in (name, name.rpartition(".")[0]):
            raise
    pytest.fail(f"H-61 CP1: {_MODULE_FILES[name]} is missing")


def _given(module: ModuleType, name: str) -> Any:
    """``module.name``, the test failing when the module does not give it."""
    value = getattr(module, name, None)
    if value is None:
        pytest.fail(f"H-61 CP1: {module.__name__} gives no {name}")
    return value


def hosting_config() -> ModuleType:
    """``config/hosting_panel.py`` (§1): before it exists, the test that asks for it fails here, and only that test."""
    return _module(HOSTING_CONFIG_MODULE)


def access_module() -> ModuleType:
    """``services/platform/hosting_panel/access.py`` (§2): before it exists, the test that asks for it fails here."""
    return _module(ACCESS_MODULE)


def status_reader() -> Callable[[], str | None]:
    """``panel_status_token``, the reader of §1."""
    return _given(hosting_config(), "panel_status_token")


def status_refusal() -> type[Exception]:
    """``HostingPanelConfigError``, what ``panel_status_token`` raises for a value it cannot use."""
    return _given(hosting_config(), "HostingPanelConfigError")


@pytest.fixture(autouse=True)
def no_inherited_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts with no variable of the three tokens, nor of their ``_FILE``s: nothing comes from the runner's
    environment."""
    for name in TOKEN_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def write_token_file(tmp_path: Path, text: str) -> Path:
    """A file holding ``text``, as a Docker secret mounts one."""
    path = tmp_path / "status-token"
    path.write_bytes(text.encode("utf-8"))
    return path


def set_status_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source: str, value: str) -> None:
    """``value`` as the status token, from the variable or (followed by a line break) from the file of its ``_FILE``."""
    if source == "variable":
        monkeypatch.setenv(STATUS_VARIABLE, value)
    else:
        monkeypatch.setenv(STATUS_FILE_VARIABLE, str(write_token_file(tmp_path, value + "\n")))


# =============================================================================
# HPA-001..009 (§1): panel_status_token()
# =============================================================================


def test_the_status_token_has_its_variable_and_an_error_shaped_like_the_backup_tokens() -> None:
    """HPA-001 (§1): ``PANEL_STATUS_TOKEN_VARIABLE`` is ``LIBREFOLIO_PANEL_STATUS_TOKEN``. ``HostingPanelConfigError`` is
    a ``ValueError`` shaped like ``BackupConfigError``: built from the variable, a code and a message, it carries
    ``variable`` and ``code``, and its message names the variable and says what is wrong."""
    print_section("H-61 §1: PANEL_STATUS_TOKEN_VARIABLE and HostingPanelConfigError")
    hosting = hosting_config()
    variable = getattr(hosting, "PANEL_STATUS_TOKEN_VARIABLE", None)
    error_class = status_refusal()

    assert variable == STATUS_VARIABLE, f"PANEL_STATUS_TOKEN_VARIABLE is {variable!r}, not {STATUS_VARIABLE!r}"
    assert isinstance(error_class, type) and issubclass(error_class, ValueError), f"HostingPanelConfigError is a ValueError, as BackupConfigError is: {error_class!r}"
    error = error_class(STATUS_VARIABLE, "PANEL_STATUS_TOKEN_TOO_SHORT", "expected at least 32 characters")
    assert (error.variable, error.code) == (STATUS_VARIABLE, "PANEL_STATUS_TOKEN_TOO_SHORT"), f"built from (variable, code, message), it carries variable and code: {(error.variable, error.code)}"
    assert STATUS_VARIABLE in str(error) and "expected at least 32 characters" in str(error), f"its message names the variable and says what is wrong: {error}"
    print_success("LIBREFOLIO_PANEL_STATUS_TOKEN; HostingPanelConfigError(ValueError) with variable and code")


@pytest.mark.parametrize(
    "variables",
    [
        pytest.param({}, id="neither-variable"),
        pytest.param({STATUS_VARIABLE: ""}, id="empty-variable"),
        pytest.param({STATUS_VARIABLE: " \t "}, id="blank-variable"),
        pytest.param({STATUS_FILE_VARIABLE: ""}, id="empty-file-variable"),
        pytest.param({STATUS_FILE_VARIABLE: "   "}, id="blank-file-variable"),
        pytest.param({STATUS_VARIABLE: " ", STATUS_FILE_VARIABLE: " "}, id="both-blank"),
    ],
)
def test_no_status_token_when_neither_variable_gives_one(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str]) -> None:
    """HPA-002 (§1): neither variable set, or blank, is no token at all: None, the status route is off."""
    panel_status_token = status_reader()
    for name, value in variables.items():
        monkeypatch.setenv(name, value)

    assert panel_status_token() is None, f"{sorted(variables)} set to blank values must count as unset"


def test_the_variable_is_the_status_token_as_written_and_read_at_every_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """HPA-003 (§1): the variable, when not blank, is the token as written; it is read at every call, as the backup and
    wake tokens are, so a new value is the token at the next call."""
    panel_status_token = status_reader()
    first, second = a_token(), a_token()
    monkeypatch.setenv(STATUS_VARIABLE, first)
    read_first = panel_status_token()
    monkeypatch.setenv(STATUS_VARIABLE, second)
    read_second = panel_status_token()

    assert read_first == first, f"{STATUS_VARIABLE} must be the token as written"
    assert read_second == second, "the variable is read at every call: a new value is the token at the next one"


@pytest.mark.parametrize(
    ("before", "after"),
    [
        pytest.param("", "\n", id="line-break"),
        pytest.param("", "\r\n", id="crlf"),
        pytest.param("", "\n\n", id="two-line-breaks"),
        pytest.param("\ufeff", "\n", id="bom-and-line-break"),
        pytest.param("", "", id="no-line-break"),
    ],
)
def test_the_file_gives_the_status_token_without_its_bom_and_trailing_line_breaks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, before: str, after: str) -> None:
    """HPA-004 (§1): the file named by ``_FILE`` holds the token; a leading BOM and the trailing line breaks are not part
    of it (``env_secret``)."""
    panel_status_token = status_reader()
    token = a_token()
    monkeypatch.setenv(STATUS_FILE_VARIABLE, str(write_token_file(tmp_path, before + token + after)))

    assert panel_status_token() == token, f"the token of a file holding {before!r} + token + {after!r}"


def test_the_variable_wins_over_the_file_and_a_blank_one_leaves_it_the_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """HPA-005 (§1): both set, the variable is the token; blank, it counts as unset and the file is the token."""
    panel_status_token = status_reader()
    from_variable, from_file = a_token(), a_token()
    monkeypatch.setenv(STATUS_FILE_VARIABLE, str(write_token_file(tmp_path, from_file + "\n")))
    monkeypatch.setenv(STATUS_VARIABLE, from_variable)
    both = panel_status_token()
    monkeypatch.setenv(STATUS_VARIABLE, "  ")
    blank_variable = panel_status_token()

    assert both == from_variable, "both set: the variable wins over the file"
    assert blank_variable == from_file, "a blank variable counts as unset: the file gives the token"


@pytest.mark.parametrize("source", ["variable", "file"])
def test_31_characters_are_refused_without_the_value_and_32_are_a_status_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source: str) -> None:
    """HPA-006 (§1): under ``PANEL_TOKEN_MIN_LENGTH`` (32) characters, ``HostingPanelConfigError`` with the code
    ``PANEL_STATUS_TOKEN_TOO_SHORT`` and ``variable`` the variable, its message naming the variable, never the value; 32
    characters are a token. From the file, the line break that follows the value is not counted."""
    print_section(f"H-61 §1: 31 and 32 characters, from the {source}")
    panel_status_token, refusal = status_reader(), status_refusal()
    assert PANEL_TOKEN_MIN_LENGTH == MIN_LENGTH, "Precondition: the length of the rule is the one documented"
    too_short, long_enough = a_token()[: MIN_LENGTH - 1], a_token()[:MIN_LENGTH]
    set_status_token(monkeypatch, tmp_path, source, too_short)
    with pytest.raises(refusal) as refused:
        panel_status_token()
    set_status_token(monkeypatch, tmp_path, source, long_enough)
    taken = panel_status_token()

    error = refused.value
    assert (error.code, error.variable) == ("PANEL_STATUS_TOKEN_TOO_SHORT", STATUS_VARIABLE), f"the error's code and variable: {(error.code, error.variable)}"
    assert STATUS_VARIABLE in str(error), f"the message names the variable: {error}"
    assert too_short not in f"{error} {error!r} {error.args}", "the message must never carry the value"
    assert taken == long_enough, f"{MIN_LENGTH} characters are a token"
    print_success(f"{source}: {MIN_LENGTH - 1} characters refused (code, variable, no value), {MIN_LENGTH} taken")


#: A character no token may hold, put on an otherwise valid token of 40 characters (``spoil(token)``): before it, after
#: it, or between its two halves. From the variable; and from the file, whose line break after the token goes
#: (``env_secret``) while the spaces before it stay.
NOT_VISIBLE_ASCII = [
    pytest.param("variable", lambda token: f" {token}", id="leading-space"),
    pytest.param("variable", lambda token: f"{token} ", id="trailing-space"),
    pytest.param("variable", lambda token: f"{token}\t", id="trailing-tab"),
    pytest.param("variable", lambda token: f"{token[:20]} {token[20:]}", id="inner-space"),
    pytest.param("variable", lambda token: f"{token[:20]}\u00e9{token[20:]}", id="e-acute-u00e9"),
    pytest.param("variable", lambda token: f"{token[:20]}\u20ac{token[20:]}", id="euro-sign-u20ac"),
    pytest.param("variable", lambda token: f"{token[:20]}\u00a0{token[20:]}", id="no-break-space-u00a0"),
    pytest.param("variable", lambda token: f"{token[:20]}\x7f{token[20:]}", id="del-0x7f"),
    pytest.param("variable", lambda token: f"{token[:20]}\x01{token[20:]}", id="control-0x01"),
    pytest.param("file", lambda token: f"{token}  ", id="file-spaces-before-the-line-break"),
]


@pytest.mark.parametrize(("source", "spoil"), NOT_VISIBLE_ASCII)
def test_a_status_token_holding_anything_but_visible_ascii_is_refused_without_the_value(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source: str, spoil: Callable[[str], str]) -> None:
    """HPA-007 (§1): a token holds visible ASCII characters only. A space or a tab (around it or inside it), a character
    outside ASCII, DEL or another control character raises ``HostingPanelConfigError`` with the code
    ``PANEL_STATUS_TOKEN_NOT_VISIBLE_ASCII`` and ``variable`` the variable; its message names the variable, never the value
    nor a part of it. Each value is an otherwise valid token of 40 characters, so its length is never the reason."""
    panel_status_token, refusal = status_reader(), status_refusal()
    valid = a_token()[:40]
    value = spoil(valid)
    set_status_token(monkeypatch, tmp_path, source, value)
    with pytest.raises(refusal) as refused:
        panel_status_token()

    error = refused.value
    shown = [part for part in (value, valid[:20], valid[20:]) if part in f"{error} {error!r} {error.args}"]
    assert (error.code, error.variable) == ("PANEL_STATUS_TOKEN_NOT_VISIBLE_ASCII", STATUS_VARIABLE), f"the error's code and variable: {(error.code, error.variable)}"
    assert STATUS_VARIABLE in str(error), f"the message names the variable: {error}"
    assert shown == [], f"the message must never carry the value, nor a part of it: {len(shown)} part(s) shown"


@pytest.mark.parametrize(
    "spoil",
    [
        pytest.param(lambda token: f"{token}\u00e9", id="short-and-non-ascii"),
        pytest.param(lambda token: f" {token}", id="short-with-a-leading-space"),
    ],
)
def test_the_characters_of_a_status_token_are_checked_before_its_length(monkeypatch: pytest.MonkeyPatch, spoil: Callable[[str], str]) -> None:
    """HPA-007 (§1): a value too short that also holds a character outside visible ASCII raises the code of the
    characters, ``PANEL_STATUS_TOKEN_NOT_VISIBLE_ASCII``, checked first, as for the backup and wake tokens; never with the
    value."""
    panel_status_token, refusal = status_reader(), status_refusal()
    short = a_token()[:10]
    value = spoil(short)
    assert len(value) < MIN_LENGTH, "Precondition: the value is too short as well"
    monkeypatch.setenv(STATUS_VARIABLE, value)
    with pytest.raises(refusal) as refused:
        panel_status_token()

    error = refused.value
    assert error.code == "PANEL_STATUS_TOKEN_NOT_VISIBLE_ASCII", f"the characters are checked before the length: {error.code}"
    assert short not in f"{error} {error!r} {error.args}", "the message must never carry the value"


@pytest.mark.parametrize("problem", sorted(BROKEN_FILES))
def test_a_file_that_cannot_give_the_status_token_raises_secret_file_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, problem: str) -> None:
    """HPA-008 (§1): a ``_FILE`` that is missing, a folder, empty or blank cannot give the token: ``SecretFileError``,
    naming the ``_FILE`` variable."""
    panel_status_token = status_reader()
    path = tmp_path / "status-token"
    BROKEN_FILES[problem](path)
    monkeypatch.setenv(STATUS_FILE_VARIABLE, str(path))
    with pytest.raises(SecretFileError) as raised:
        panel_status_token()

    assert STATUS_FILE_VARIABLE in str(raised.value), f"the error names the variable: {raised.value}"


#: Values set as the three tokens at once, with the outcome the one rule gives each: taken as written, or refused for
#: the reason its code names after ``_TOKEN_``.
SHARED_RULE = [
    pytest.param(a_token, "taken", id="64-hex-characters"),
    pytest.param(lambda: a_token()[:MIN_LENGTH], "taken", id="32-characters"),
    pytest.param(lambda: VISIBLE_ASCII, "taken", id="every-visible-ascii-character"),
    pytest.param(lambda: "!" + "+/=-_." + "0123456789abcdefABCDEFGH" + "~", "taken", id="32-characters-from-0x21-to-0x7e"),
    pytest.param(lambda: a_token()[: MIN_LENGTH - 1], "TOO_SHORT", id="31-characters"),
    pytest.param(lambda: f" {a_token()}", "NOT_VISIBLE_ASCII", id="leading-space"),
    pytest.param(lambda: f"{a_token()[:20]}\t{a_token()[:20]}", "NOT_VISIBLE_ASCII", id="inner-tab"),
    pytest.param(lambda: f"{a_token()[:20]}\x7f{a_token()[:20]}", "NOT_VISIBLE_ASCII", id="del-0x7f"),
    pytest.param(lambda: f"{a_token()[:20]}\u00e9{a_token()[:20]}", "NOT_VISIBLE_ASCII", id="e-acute-u00e9"),
    pytest.param(lambda: f"{a_token()[:10]}\u00e9", "NOT_VISIBLE_ASCII", id="short-and-non-ascii"),
]


def outcome(read: Callable[[], str | None], refusal: type[Exception], value: str) -> str:
    """``taken`` when ``read()`` returns ``value``; for a refusal, the reason its code names after ``_TOKEN_``."""
    try:
        token = read()
    except refusal as refused:
        return getattr(refused, "code", "").partition("_TOKEN_")[2] or f"refused without a code: {type(refused).__name__}"
    return "taken" if token == value else "another value"


@pytest.mark.parametrize(("make", "expected"), SHARED_RULE)
def test_the_status_token_follows_the_rule_of_the_backup_and_wake_tokens_value_for_value(monkeypatch: pytest.MonkeyPatch, make: Callable[[], str], expected: str) -> None:
    """HPA-009 (§1): «the rules of ``backup_download_token()`` and ``wake_token()``», one definition
    (``PANEL_TOKEN_CHARACTERS``, ``PANEL_TOKEN_MIN_LENGTH``): the same value set as the three tokens is taken as written by
    the three readers, or refused by the three for the same reason, ``PANEL_STATUS_TOKEN_*`` beside
    ``BACKUP_DOWNLOAD_TOKEN_*`` and ``WAKE_TOKEN_*``. The edges of visible ASCII (``!``, ``~``, the punctuation of a
    generated token, every visible character) are taken as written."""
    assert (PANEL_TOKEN_MIN_LENGTH, PANEL_TOKEN_CHARACTERS) == (MIN_LENGTH, frozenset(VISIBLE_ASCII)), "Precondition: the panel's rule is the rule documented"
    read_status, status_error = status_reader(), status_refusal()
    value = make()
    for variable in VARIABLES.values():
        monkeypatch.setenv(variable, value)

    outcomes = {
        "status": outcome(read_status, status_error, value),
        "backup": outcome(backup_download_token, BackupConfigError, value),
        "wake": outcome(wake_token, SleepWakeConfigError, value),
    }

    assert outcomes == dict.fromkeys(outcomes, expected), f"the status token and the backup and wake tokens share one rule: {outcomes}, expected {expected}"


@pytest.mark.parametrize("source", ["variable", "file"])
@pytest.mark.parametrize(
    "token",
    [
        pytest.param("!" + "+/=-_." + "0123456789abcdefABCDEFGH" + "~", id="32-characters-from-0x21-to-0x7e"),
        pytest.param(VISIBLE_ASCII, id="every-visible-ascii-character"),
    ],
)
def test_status_tokens_at_the_edges_of_visible_ascii_are_taken_as_written(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, token: str, source: str) -> None:
    """HPA-009 (§1): the edges are inside the rule, from the variable and from the file alike."""
    panel_status_token = status_reader()
    assert len(token) >= MIN_LENGTH and set(token) <= set(VISIBLE_ASCII), "Precondition: a token of visible ASCII characters, long enough"
    set_status_token(monkeypatch, tmp_path, source, token)

    assert panel_status_token() == token, f"{source}: a token of visible ASCII characters is returned as written"


# =============================================================================
# §2: THE LIMITER ON A FAKE CLOCK, THE TEST ROUTES, THE PANEL OF A TEST
# =============================================================================


class FakeClock:
    """The limiter's clock: it moves only when the test moves it."""

    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RecordingLimiter(SlidingWindowLimiter):
    """``SlidingWindowLimiter(20, 600)`` as the contract builds ``PANEL_ATTEMPTS``, on the fake clock, recording each call
    the code under test makes, as ``(method, key)``. What the test reads goes through ``held`` and ``len``, which record
    nothing."""

    def __init__(self, clock: FakeClock) -> None:
        super().__init__(PANEL_LIMIT, PANEL_WINDOW_SECONDS, clock=clock)
        self.calls: list[tuple[str, Any]] = []

    def peek(self, key: Hashable = None, *, limit: int | None = None) -> RateDecision:
        self.calls.append(("peek", key))
        return super().peek(key, limit=limit)

    def hit(self, key: Hashable = None, *, limit: int | None = None) -> RateDecision:
        self.calls.append(("hit", key))
        return super().hit(key, limit=limit)

    def count(self, key: Hashable = None) -> int:
        self.calls.append(("count", key))
        return super().count(key)

    def reset(self, key: Hashable = None) -> None:
        self.calls.append(("reset", key))
        super().reset(key)

    def clear(self) -> None:
        self.calls.append(("clear", None))
        super().clear()

    def held(self, key: Hashable) -> int:
        """The hits of ``key`` in the window now, read by the test: not recorded."""
        return SlidingWindowLimiter.count(self, key)


#: The test routes' endpoints, built once per process from the access module (``panel_access`` gives the same object
#: for the same scope) and kept: FastAPI caches the context of an endpoint by its ``id()``, which a freed one could lend.
_ENDPOINTS: dict[str, Callable[..., Any]] = {}


def _served(request: Request, scope: str, caller: Any) -> dict[str, str]:
    """What a test route does once the dependency let the request through: record the caller it got, answer its scope."""
    request.app.state.served.append((scope, caller))
    return {"served": scope}


def _endpoint(access: ModuleType, scope: str) -> Callable[..., Any]:
    """The test route of ``scope``: its caller is ``Depends(panel_access(PanelScope(scope)))``."""
    if scope not in _ENDPOINTS:
        dependency = access.panel_access(access.PanelScope(scope))

        async def route(request: Request, caller: Annotated[Any, Depends(dependency)]) -> dict[str, str]:
            return _served(request, scope, caller)

        route.__name__ = route.__qualname__ = f"hp_test_{scope}_route"
        _ENDPOINTS[scope] = route
    return _ENDPOINTS[scope]


def panel_app(access: ModuleType, *, request_ids: bool = False) -> FastAPI:
    """A fresh app holding the three test routes and nothing else; with ``request_ids``, ``RequestIdMiddleware`` around
    them, as the app's stack puts it outside its routes."""
    app = FastAPI()
    app.state.served = []
    for scope in SCOPES:
        method, path = ROUTES[scope]
        app.add_api_route(path, _endpoint(access, scope), methods=[method])
    if request_ids:
        app.add_middleware(RequestIdMiddleware)
    return app


def request_line(scope: str) -> tuple[str, str]:
    """The method and a path of ``scope``'s test route: the backup one with a job id of its own at each call."""
    method, template = ROUTES[scope]
    return method, template.replace("{job_id}", f"job-{uuid.uuid4().hex[:12]}")


def rate_key(client: tuple[str, int]) -> str | None:
    """The key of a peer, as ``client_rate_key`` gives it."""
    return client_address_module.client_rate_key(client[0])


@dataclass(frozen=True)
class Unusable:
    """A token the server cannot use, as a test set it: what a caller may present as written, and its file, if any."""

    presentable: list[str]
    path: Path | None


@dataclass
class Panel:
    """What a §2 test works with: the access module, its fresh app, the fake clock, the recording limiter in place of
    ``PANEL_ATTEMPTS``, and the tokens it configured, which no answer nor line may ever hold."""

    access: ModuleType
    app: FastAPI
    clock: FakeClock
    limiter: RecordingLimiter
    monkeypatch: pytest.MonkeyPatch
    tmp_path: Path
    header_canary: str = field(default_factory=lambda: f"hp-header-{uuid.uuid4().hex}")
    configured: list[str] = field(default_factory=list)

    def set_token(self, scope: str, value: str, *, source: str = "variable") -> str:
        """``value`` as ``scope``'s token, from its variable or (followed by a line break) from the file of its ``_FILE``."""
        variable = VARIABLES[scope]
        if source == "variable":
            self.monkeypatch.setenv(variable, value)
        else:
            path = self.tmp_path / f"{scope}-token"
            path.write_bytes(f"{value}\n".encode())
            self.monkeypatch.setenv(variable + FILE_SUFFIX, str(path))
        self.configured.append(value)
        return value

    def new_token(self, scope: str, *, source: str = "variable") -> str:
        """A new token for ``scope``, set."""
        return self.set_token(scope, a_token(), source=source)

    def set_unusable(self, scope: str, kind: str) -> Unusable:
        """A token of ``scope`` the server cannot use, by ``kind`` (``UNUSABLE_KINDS``)."""
        valid = a_token()[:40]
        if kind == "too-short":
            return Unusable([self.set_token(scope, valid[: MIN_LENGTH - 1])], None)
        if kind == "a-space-inside":
            self.configured.extend([valid[:20], valid[20:]])
            return Unusable([self.set_token(scope, f"{valid[:20]} {valid[20:]}")], None)
        path = self.tmp_path / f"{scope}-token"
        BROKEN_FILES[kind](path)
        self.monkeypatch.setenv(VARIABLES[scope] + FILE_SUFFIX, str(path))
        return Unusable([], path)

    def unset(self, scope: str, kind: str) -> None:
        """``scope``'s token unset, by ``kind`` (``UNSET_KINDS``)."""
        variable = VARIABLES[scope]
        self.monkeypatch.delenv(variable, raising=False)
        self.monkeypatch.delenv(variable + FILE_SUFFIX, raising=False)
        if kind == "blank-variable":
            self.monkeypatch.setenv(variable, "   ")
        elif kind == "blank-file-variable":
            self.monkeypatch.setenv(variable + FILE_SUFFIX, " ")

    def caller(self, scope: str) -> Any:
        """The caller the contract has the dependency return for ``scope``."""
        return self.access.PanelCaller(self.access.PanelScope(scope), credential="token")


@contextmanager
def client_address_state_kept() -> Iterator[None]:
    """What a request leaves in ``client_address``'s process state, put back as it was: the forwarding headers noted from
    peers nobody trusts (HPA-027's requests come through such a proxy, and the configuration check
    ``platform.client_address`` reports them) and the warned flag. The module's own containers, in place."""
    module = client_address_module
    noted = {peer_class: set(names) for peer_class, names in module._untrusted_forwarding.items()}
    warned = list(module._warned)
    try:
        yield
    finally:
        for peer_class, names in module._untrusted_forwarding.items():
            names.clear()
            names.update(noted.get(peer_class, set()))
        module._warned[:] = warned


@pytest.fixture
def panel(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Panel]:
    """The access module with ``PANEL_ATTEMPTS`` replaced by a recording limiter on a fake clock, a fresh app of the three
    test routes, and ``LIBREFOLIO_CLIENT_IP_HEADER`` read as unset whatever the lane sets (``_configured_header``
    replaced, its cache never filled); ``client_address``'s process state put back after the test. Before H-61 it fails
    on the missing module."""
    access = access_module()
    for name in ("PanelScope", "PanelCaller", "panel_access"):
        _given(access, name)
    if not hasattr(access, "PANEL_ATTEMPTS"):
        pytest.fail(f"H-61 CP1 §2: {_MODULE_FILES[ACCESS_MODULE]} has no PANEL_ATTEMPTS, the limiter the dependency reads at each call")
    clock = FakeClock(START)
    limiter = RecordingLimiter(clock)
    monkeypatch.setattr(access, "PANEL_ATTEMPTS", limiter)
    monkeypatch.setattr(client_address_module, "_configured_header", lambda: None)
    with client_address_state_kept():
        yield Panel(access=access, app=panel_app(access), clock=clock, limiter=limiter, monkeypatch=monkeypatch, tmp_path=tmp_path)


# =============================================================================
# §2: ONE REQUEST, ITS ANSWER AND ITS LINES
# =============================================================================


@dataclass(frozen=True)
class Exchange:
    """One request to an app of the test: the answer, the events logged while it ran, the calls the limiter received and
    the callers the test routes got meanwhile."""

    scope: str
    method: str
    path: str
    response: httpx.Response
    events: list[dict[str, Any]]
    limiter_calls: list[tuple[str, Any]]
    served: list[tuple[str, Any]]

    @property
    def answer(self) -> tuple[int, object]:
        """Status and body: the JSON of a JSON answer, the first bytes of any other, so a red always reads."""
        if self.response.headers.get("content-type", "").startswith("application/json"):
            return self.response.status_code, self.response.json()
        return self.response.status_code, self.response.content[:200]

    @property
    def challenge(self) -> str | None:
        return self.response.headers.get("www-authenticate")

    @property
    def request_id(self) -> str | None:
        return self.response.headers.get("x-request-id")

    @property
    def panel_lines(self) -> list[dict[str, Any]]:
        """The ``Hosting panel request`` lines, in order."""
        return self.lines(PANEL_LINE)

    def lines(self, *names: str) -> list[dict[str, Any]]:
        """The captured lines whose event is one of ``names``, in order."""
        return [event for event in self.events if event.get("event") in names]

    def shows(self, values: Iterable[str]) -> list[str]:
        """Where a value of ``values`` shows: the body, the headers (names and values), the log (every key and value of
        every line). Empty values are skipped, and a value is named by its position, never written out."""
        headers = "\n".join(f"{name}: {value}" for name, value in self.response.headers.multi_items())
        log = "\n".join([repr(self.events), *(f"{key}={value}" for event in self.events for key, value in event.items())])
        places = []
        for index, value in enumerate(values):
            if not value:
                continue
            found = {"body": value.encode("utf-8") in self.response.content, "headers": value in headers, "log": value in log}
            places.extend(f"value #{index} in the {place}" for place, shown in found.items() if shown)
        return places


def module_logger(access: ModuleType) -> Any:
    """The access module's own logger, on which the contract logs ``Hosting panel request``."""
    logger = getattr(access, "logger", None)
    if logger is None or not callable(getattr(logger, "debug", None)):
        pytest.fail(f"H-61 CP1 §2: {_MODULE_FILES[ACCESS_MODULE]} has no module-level logger, on which «{PANEL_LINE}» is logged")
    return logger


def secret_values(panel: Panel, authorization: str | None, headers: Mapping[str, str], params: Mapping[str, str] | None, client: tuple[str, int]) -> list[str]:
    """What no answer and no line may hold: the tokens the test configured, the credential presented (and the whole
    ``Authorization`` value with it), every other header value sent, the query's values, the client's address and its
    key."""
    presented = authorization.partition(" ")[2].strip() if authorization else ""
    whole = [authorization] if presented else []
    sent = [value for name, value in headers.items() if name != "Authorization"]
    return [*panel.configured, presented, *whole, *sent, *(params or {}).values(), client[0], rate_key(client) or ""]


async def _request(transport: httpx.ASGITransport, method: str, path: str, headers: Mapping[str, str], params: Mapping[str, str] | None) -> httpx.Response:
    """One request through ``transport``, within ``CALL_SECONDS``."""
    try:
        async with asyncio.timeout(CALL_SECONDS):
            async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as http:
                return await http.request(method, path, headers=headers, params=params)
    except TimeoutError:
        pytest.fail(f"{method} {path}: no answer within {CALL_SECONDS} s")


async def exchange_with(
    panel: Panel,
    scope: str,
    method: str,
    path: str,
    *,
    authorization: str | None = None,
    params: Mapping[str, str] | None = None,
    client: tuple[str, int] = PEER,
    headers: Mapping[str, str] | None = None,
    app: FastAPI | None = None,
) -> Exchange:
    """``method path`` on the app (the panel's by default) from ``client``, in this process: ``Authorization`` only when
    given, the canary header always, ``headers`` besides; the log captured meanwhile, behind a canary logged through the
    access module's own logger. Ends on what every request of this module must hold: no configured token, no value sent,
    no header value, no query value and not the client's address in the answer, its headers or a line."""
    target = panel.app if app is None else app
    sent = {CANARY_HEADER: panel.header_canary, **(headers or {})}
    if authorization is not None:
        sent["Authorization"] = authorization
    calls_mark, served_mark = len(panel.limiter.calls), len(target.state.served)
    transport = httpx.ASGITransport(app=target, raise_app_exceptions=False, client=client)
    with capture_logs(processors=[merge_contextvars]) as events:
        module_logger(panel.access).debug(CAPTURE_CANARY)
        assert any(event.get("event") == CAPTURE_CANARY for event in events), f"barrier: the access module's logger does not reach capture_logs, so what this test reads of the log proves nothing: {events}"
        response = await _request(transport, method, path, sent, params)
    captured = [event for event in events if event.get("event") != CAPTURE_CANARY]
    exchange = Exchange(scope, method, path, response, captured, panel.limiter.calls[calls_mark:], target.state.served[served_mark:])
    leaked = exchange.shows(secret_values(panel, authorization, sent, params, client))
    assert not leaked, f"{method} {path}: a secret left the server (a token, a value sent, a header, the query or the client's address): {leaked}"
    return exchange


async def send(panel: Panel, scope: str, **options: Any) -> Exchange:
    """A request to ``scope``'s test route (``exchange_with``)."""
    method, path = request_line(scope)
    return await exchange_with(panel, scope, method, path, **options)


async def refuse(panel: Panel, scopes: Sequence[str], **options: Any) -> list[Exchange]:
    """A request with another token on each scope of ``scopes``, in order, each refused with its scope's 401: refusals the
    limiter counts."""
    exchanges = [await send(panel, scope, authorization=f"Bearer {a_token()}", **options) for scope in scopes]
    answers = [exchange.answer for exchange in exchanges]
    assert answers == [UNAUTHORIZED[scope] for scope in scopes], f"Precondition: each request with another token gets its scope's 401: {answers}"
    return exchanges


def panel_line(exchange: Exchange, outcome: str, **fields: Any) -> dict[str, Any]:
    """The ``Hosting panel request`` line the contract writes for ``exchange`` and ``outcome``, whole: INFO for
    ``accepted``, WARNING otherwise; the request's scope, method and path (never the query), the credential ``token``, and
    ``fields`` (``reason``, ``retry_after``, ``request_id``)."""
    level = "info" if outcome == "accepted" else "warning"
    return {"event": PANEL_LINE, "log_level": level, "scope": exchange.scope, "method": exchange.method, "path": exchange.path, "outcome": outcome, "credential": "token", **fields}


def error_line(scope: str, error: str, **fields: Any) -> dict[str, Any]:
    """The error line of ``scope``'s unusable token, whole, as today: backup with ``error``; wake and status with
    ``variable`` and ``error``."""
    line = {"event": UNUSABLE_LINES[scope], "log_level": "error", "error": error, **fields}
    if scope != BACKUP:
        line["variable"] = VARIABLES[scope]
    return line


def reader_error(scope: str) -> str:
    """The text of the error ``scope``'s token reader raises for the token the test set: the ``error`` of its line."""
    if scope == BACKUP:
        read, refusals = backup_download_token, (SecretFileError, BackupConfigError)
    elif scope == WAKE:
        read, refusals = wake_token, (SecretFileError, SleepWakeConfigError)
    else:
        read, refusals = status_reader(), (SecretFileError, status_refusal())
    try:
        read()
    except refusals as error:
        return str(error)
    pytest.fail(f"Precondition: the {scope} token this test set is one its reader refuses")


def numeric(value: object) -> bool:
    """A number of seconds: an int or a float, never a bool nor a text."""
    return isinstance(value, int | float) and not isinstance(value, bool)


class HmacSpy:
    """The access module's ``hmac``, replaced: ``compare_digest`` records its two arguments and answers as the real one
    does, or ``answer`` when the test sets one; anything else is the real module's."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, Any]] = []
        self.answer: bool | None = None

    def compare_digest(self, first: Any, second: Any) -> bool:
        self.calls.append((first, second))
        real = hmac.compare_digest(first, second)
        return real if self.answer is None else self.answer

    def __getattr__(self, name: str) -> Any:
        return getattr(hmac, name)


def spy_on_hmac(monkeypatch: pytest.MonkeyPatch, access: ModuleType) -> HmacSpy:
    """The spy in place of the access module's ``hmac``, for the test: the module compares through the ``hmac`` it
    imports, its attribute."""
    held = getattr(access, "hmac", None)
    assert held is hmac, f"H-61 CP1 §2: {_MODULE_FILES[ACCESS_MODULE]} compares the credential with hmac.compare_digest, through the hmac module it imports: its attribute hmac is {held!r}"
    spy = HmacSpy()
    monkeypatch.setattr(access, "hmac", spy)
    return spy


# =============================================================================
# HPA-010..017 (§2): the dependency
# =============================================================================


def test_the_module_gives_the_scopes_one_dependency_per_scope_a_frozen_caller_and_one_limiter() -> None:
    """HPA-010 (§2): ``PanelScope`` is a ``StrEnum`` of exactly ``backup``, ``wake`` and ``status``. ``panel_access(scope)``
    returns the same object for the same scope, and one of its own for each. ``PanelCaller`` is a frozen dataclass of
    ``scope``, then ``credential``. ``PANEL_ATTEMPT_LIMIT`` is 20 and ``PANEL_ATTEMPT_WINDOW_SECONDS`` 600.
    ``new_panel_attempts()``, the factory the module builds ``PANEL_ATTEMPTS`` with, gives a new ``SlidingWindowLimiter``
    of that limit and window at each call: what the module ships is pinned through it. ``PANEL_ATTEMPTS`` itself is only
    pinned to be a ``SlidingWindowLimiter``, never its limit: the shared conftest gives every test a practically unlimited
    one, as it turns the sign-in limit off, and the limiter's own tests replace it again."""
    print_section("H-61 §2: PanelScope, panel_access, PanelCaller, new_panel_attempts")
    access = access_module()
    scope_class, panel_access, caller_class = _given(access, "PanelScope"), _given(access, "panel_access"), _given(access, "PanelCaller")
    limits = {name: getattr(access, name, None) for name in ("PANEL_ATTEMPT_LIMIT", "PANEL_ATTEMPT_WINDOW_SECONDS")}
    new_panel_attempts = _given(access, "new_panel_attempts")
    current = getattr(access, "PANEL_ATTEMPTS", None)

    assert isinstance(scope_class, type) and issubclass(scope_class, enum.StrEnum), f"PanelScope is a StrEnum: {scope_class!r}"
    members = {member.name: member.value for member in scope_class}
    # H-62 (contract L3 §5): the restore's scope, ticket only, joins the three; red until H-62
    assert members == {"BACKUP": BACKUP, "WAKE": WAKE, "STATUS": STATUS, "BACKUP_RESTORE": "backup:restore"}, f"PanelScope holds exactly backup, wake, status and backup:restore: {members}"
    dependencies = {scope: panel_access(scope_class(scope)) for scope in SCOPES}
    again = {scope: panel_access(scope_class(scope)) for scope in SCOPES}
    assert all(callable(dependency) for dependency in dependencies.values()), f"panel_access gives a FastAPI dependency, a callable: {dependencies}"
    assert all(again[scope] is dependencies[scope] for scope in SCOPES), "panel_access returns the same object for the same scope"
    assert len({id(dependency) for dependency in dependencies.values()}) == len(SCOPES), "panel_access gives each scope a dependency of its own"
    names = [item.name for item in dataclasses.fields(caller_class)] if dataclasses.is_dataclass(caller_class) else []
    assert names[:2] == ["scope", "credential"], f"PanelCaller is a dataclass of scope, then credential: {names}"
    caller = caller_class(scope_class.WAKE, credential="token")
    with pytest.raises(dataclasses.FrozenInstanceError):
        caller.credential = "ticket"
    assert caller == caller_class(scope_class.WAKE, credential="token"), "two callers of one scope and one credential are equal"
    assert caller != caller_class(scope_class.STATUS, credential="token"), "callers of two scopes differ"
    assert limits == {"PANEL_ATTEMPT_LIMIT": PANEL_LIMIT, "PANEL_ATTEMPT_WINDOW_SECONDS": PANEL_WINDOW_SECONDS}, f"the limiter's constants: {limits}"
    assert callable(new_panel_attempts), f"new_panel_attempts is the factory of the module's limiter: {new_panel_attempts!r}"
    built = [new_panel_attempts(), new_panel_attempts()]
    assert all(isinstance(limiter, SlidingWindowLimiter) for limiter in built), f"new_panel_attempts() builds a SlidingWindowLimiter: {built!r}"
    assert built[0] is not built[1], "new_panel_attempts() builds a new limiter at each call, never a shared one"
    shapes = [(limiter.limit, limiter.window_seconds) for limiter in built]
    assert shapes == [(PANEL_LIMIT, PANEL_WINDOW_SECONDS)] * len(built), f"each limiter new_panel_attempts() builds has limit 20 and window 600: {shapes}"
    assert isinstance(current, SlidingWindowLimiter), f"PANEL_ATTEMPTS is a SlidingWindowLimiter, whatever its limit: {current!r}"
    print_success("PanelScope backup/wake/status; one dependency per scope; frozen PanelCaller; new_panel_attempts() a new (20, 600) at each call")


def test_each_scope_asks_for_its_own_bearer_scheme_and_no_other(panel: Panel) -> None:
    """HPA-011 (§2): in the OpenAPI document of the test app, each scope's route asks for its own HTTP bearer scheme and
    nothing else: ``BackupPanelToken`` and ``WakeToken`` as today, ``PanelStatusToken`` for the status."""
    document = panel.app.openapi()
    schemes = document.get("components", {}).get("securitySchemes", {})
    kinds = {name: (schemes.get(name, {}).get("type"), schemes.get(name, {}).get("scheme")) for name in SCHEMES.values()}
    asking = {f"{method.upper()} {path}": operation.get("security") for path, item in document["paths"].items() for method, operation in item.items() if isinstance(operation, dict)}
    expected = {f"{ROUTES[scope][0]} {ROUTES[scope][1]}": [{SCHEMES[scope]: []}] for scope in SCOPES}

    assert kinds == dict.fromkeys(SCHEMES.values(), ("http", "bearer")), f"each scope's scheme is an HTTP bearer scheme: {kinds}"
    assert asking == expected, f"each route asks for its scope's scheme, and nothing else: {asking}"


@pytest.mark.asyncio
@pytest.mark.parametrize("unset", UNSET_KINDS)
@pytest.mark.parametrize("scope", SCOPES)
async def test_a_scope_whose_token_is_unset_answers_as_a_path_that_does_not_exist(panel: Panel, scope: str, unset: str) -> None:
    """HPA-012 (§2): a scope whose token is unset (neither variable, or blank) answers 404 ``{"detail": "Not Found"}``,
    whatever the request presents — its former token, the token of another scope, which is set, ``Basic`` —, with no line
    at all, nothing counted and the limiter not read; its route never runs. Barriers: with its token set, the same route
    answers the scope's 401 to another token, its line captured and the refusal counted on this test's limiter; a path
    that does not exist answers that very 404."""
    print_section(f"H-61 §2: the {scope} scope off ({unset})")
    others = {other: panel.new_token(other) for other in SCOPES if other != scope}
    former = panel.new_token(scope)
    key = rate_key(PEER)
    mounted = await send(panel, scope, authorization=f"Bearer {a_token()}")
    panel.unset(scope, unset)
    requests = [("no Authorization", None), ("Bearer, its former token", f"Bearer {former}"), ("Basic, its former token", f"Basic {former}")]
    requests += [(f"Bearer, the {other} token", f"Bearer {token}") for other, token in others.items()]

    nowhere = await exchange_with(panel, "-", "GET", NOWHERE)
    exchanges = {label: await send(panel, scope, authorization=authorization) for label, authorization in requests}

    assert mounted.answer == UNAUTHORIZED[scope] and mounted.panel_lines == [panel_line(mounted, "refused", reason="mismatch")], f"Barrier: with its token set, the route answers the scope's 401 and logs its line: {mounted.answer}, {mounted.events}"
    assert mounted.limiter_calls == [("peek", key), ("hit", key)], f"Barrier: the refusal is counted on this test's limiter, which the dependency reads at each call: {mounted.limiter_calls}"
    assert nowhere.answer == OFF_ANSWER, f"Barrier: a path that does not exist answers {OFF_ANSWER}: {nowhere.answer}"
    answers = {label: exchange.answer for label, exchange in exchanges.items()}
    assert answers == dict.fromkeys(answers, OFF_ANSWER), f"the scope off answers as a path that does not exist, {OFF_ANSWER}: {answers}"
    lines = {label: exchange.events for label, exchange in exchanges.items()}
    assert lines == dict.fromkeys(lines, []), f"the scope off writes no line at all: {lines}"
    reads = {label: exchange.limiter_calls for label, exchange in exchanges.items()}
    assert reads == dict.fromkeys(reads, []), f"the scope off never reads the limiter: {reads}"
    assert panel.limiter.held(key) == 1, f"nothing counted but the barrier's refusal: {panel.limiter.held(key)}"
    assert all(exchange.served == [] for exchange in exchanges.values()), "the route never runs while its scope is off"
    print_success(f"{len(exchanges)} requests: 404 Not Found, no line, the limiter untouched")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", UNUSABLE_KINDS)
@pytest.mark.parametrize("scope", SCOPES)
async def test_a_token_the_server_cannot_use_answers_503_with_its_error_line_and_one_warning(panel: Panel, scope: str, kind: str) -> None:
    """HPA-013 (§2): a token of the scope the server cannot use (too short, a space inside, its file missing or a folder)
    answers the scope's 503, body as today, whatever the request presents, the configured value itself included. Each
    request logs, in this order, the scope's error line as today, word for word with its fields (backup ``error``; wake
    and status ``variable`` and ``error``), and one WARNING ``Hosting panel request`` (``unavailable``, ``unusable``), and
    no other scope's error line. The token is read first: the limiter is never read, nothing is counted, the route never
    runs; the file's path, which the log may hold, never reaches an answer."""
    print_section(f"H-61 §2: the {scope} token unusable ({kind})")
    unusable = panel.set_unusable(scope, kind)
    error = reader_error(scope)
    requests = [("no Authorization", None), ("Bearer, a token of the right length", f"Bearer {a_token()}")]
    requests += [(f"Bearer, the configured value #{index}", f"Bearer {value}") for index, value in enumerate(unusable.presentable)]

    exchanges = {label: await send(panel, scope, authorization=authorization) for label, authorization in requests}

    answers = {label: exchange.answer for label, exchange in exchanges.items()}
    assert answers == dict.fromkeys(answers, UNAVAILABLE[scope]), f"the scope's 503, whatever the request presents: {answers}"
    logged = {label: exchange.lines(*UNUSABLE_LINES.values(), PANEL_LINE) for label, exchange in exchanges.items()}
    expected = {label: [error_line(scope, error), panel_line(exchange, "unavailable", reason="unusable")] for label, exchange in exchanges.items()}
    assert logged == expected, f"each request: the scope's error line as today, then one WARNING unavailable/unusable:\n  expected {expected}\n  got      {logged}"
    reads = {label: exchange.limiter_calls for label, exchange in exchanges.items()}
    assert reads == dict.fromkeys(reads, []), f"the token is read before the limiter: a 503 never reads it: {reads}"
    assert len(panel.limiter) == 0, "nothing counted"
    assert all(exchange.served == [] for exchange in exchanges.values()), "the route never runs with an unusable token"
    paths_shown = [label for label, exchange in exchanges.items() if unusable.path is not None and str(unusable.path) in f"{exchange.response.text}\n{exchange.response.headers}"]
    assert paths_shown == [], f"the path of the token's file may be in the log, never in an answer: {paths_shown}"
    print_success(f"{len(exchanges)} requests: {UNAVAILABLE[scope][0]}, the error line and one warning each, the limiter untouched")


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", SCOPES)
async def test_without_a_bearer_credential_the_scope_answers_401_missing_and_counts_it(panel: Panel, scope: str) -> None:
    """HPA-014 (§2): the token set, a request with no bearer credential — no ``Authorization``, the token under
    ``Basic``, ``Bearer`` with nothing, the token in the query string only — answers the scope's 401 (body as today) with
    ``WWW-Authenticate: Bearer``; one WARNING ``Hosting panel request`` (``refused``, ``missing``), the path without the
    query; the limiter peeked, then hit, with the address's key; the route never runs. Barrier: the token then opens the
    route."""
    print_section(f"H-61 §2: the {scope} scope, no bearer credential")
    token = panel.new_token(scope)
    key = rate_key(PEER)
    requests = [("no Authorization", None, None), ("Basic, the token", f"Basic {token}", None), ("Bearer with nothing", "Bearer", None)]
    requests.append(("the token in the query string only", None, {"token": token, "access_token": token}))

    exchanges = {label: await send(panel, scope, authorization=authorization, params=params) for label, authorization, params in requests}
    counted = panel.limiter.held(key)
    opened = await send(panel, scope, authorization=f"Bearer {token}")

    answers = {label: exchange.answer for label, exchange in exchanges.items()}
    assert answers == dict.fromkeys(answers, UNAUTHORIZED[scope]), f"the scope's 401 without a bearer credential: {answers}"
    challenges = {label: exchange.challenge for label, exchange in exchanges.items()}
    assert challenges == dict.fromkeys(challenges, "Bearer"), f"each 401 asks for a bearer token: {challenges}"
    logged = {label: exchange.panel_lines for label, exchange in exchanges.items()}
    assert logged == {label: [panel_line(exchange, "refused", reason="missing")] for label, exchange in exchanges.items()}, f"one WARNING refused/missing each: {logged}"
    reads = {label: exchange.limiter_calls for label, exchange in exchanges.items()}
    assert reads == dict.fromkeys(reads, [("peek", key), ("hit", key)]), f"the limiter peeked, then the refusal hit: {reads}"
    assert counted == len(requests), f"each refusal counted once: {counted}"
    assert all(exchange.served == [] for exchange in exchanges.values()), "the route never runs without the credential"
    assert opened.answer == (200, {"served": scope}), f"Barrier: the token then opens the route: {opened.answer}"
    print_success(f"{len(exchanges)} requests: 401 Bearer, refused/missing, counted")


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", SCOPES)
async def test_a_different_bearer_credential_answers_401_mismatch_and_counts_it(panel: Panel, scope: str) -> None:
    """HPA-015 (§2): another token, a prefix of the token, an extension of it, the token in capitals: the scope's 401 with
    ``WWW-Authenticate: Bearer``, one WARNING ``Hosting panel request`` (``refused``, ``mismatch``), the limiter peeked then
    hit; the route never runs."""
    print_section(f"H-61 §2: the {scope} scope, another credential")
    token = panel.new_token(scope)
    key = rate_key(PEER)
    wrong = [("another token", a_token()), ("a prefix of the token", token[:-1]), ("an extension of the token", f"{token}0"), ("the token in capitals", token.upper())]

    exchanges = {label: await send(panel, scope, authorization=f"Bearer {value}") for label, value in wrong}

    answers = {label: (exchange.answer, exchange.challenge) for label, exchange in exchanges.items()}
    assert answers == dict.fromkeys(answers, (UNAUTHORIZED[scope], "Bearer")), f"the scope's 401 and a bearer challenge: {answers}"
    logged = {label: exchange.panel_lines for label, exchange in exchanges.items()}
    assert logged == {label: [panel_line(exchange, "refused", reason="mismatch")] for label, exchange in exchanges.items()}, f"one WARNING refused/mismatch each: {logged}"
    reads = {label: exchange.limiter_calls for label, exchange in exchanges.items()}
    assert reads == dict.fromkeys(reads, [("peek", key), ("hit", key)]), f"the limiter peeked, then the refusal hit: {reads}"
    assert panel.limiter.held(key) == len(wrong), f"each refusal counted once: {panel.limiter.held(key)}"
    assert all(exchange.served == [] for exchange in exchanges.values()), "the route never runs with another credential"
    print_success(f"{len(exchanges)} requests: 401 Bearer, refused/mismatch, counted")


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["variable", "file"])
@pytest.mark.parametrize("scope", SCOPES)
async def test_the_scopes_token_lets_the_request_through_with_its_caller_and_one_info_line(panel: Panel, scope: str, source: str) -> None:
    """HPA-016 (§2): the scope's token, from its variable or its ``_FILE``, under ``Bearer``: the route runs once, its
    caller ``PanelCaller(scope, credential="token")``, the scope a ``PanelScope``; one INFO ``Hosting panel request``
    (``accepted``, credential ``token``); the limiter peeked and never hit: a right credential is never counted."""
    print_section(f"H-61 §2: the {scope} token from its {source}")
    token = panel.new_token(scope, source=source)
    key = rate_key(PEER)

    exchange = await send(panel, scope, authorization=f"Bearer {token}")

    assert exchange.answer == (200, {"served": scope}), f"the scope's token lets the request through: {exchange.answer}, {exchange.events}"
    assert exchange.served == [(scope, panel.caller(scope))], f"the dependency's value is PanelCaller({scope}, credential='token'): {exchange.served}"
    caller = exchange.served[0][1]
    assert isinstance(caller, panel.access.PanelCaller) and isinstance(caller.scope, panel.access.PanelScope), f"a PanelCaller, its scope a PanelScope: {caller!r}"
    assert exchange.panel_lines == [panel_line(exchange, "accepted")], f"one INFO line, accepted: {exchange.panel_lines}"
    assert exchange.limiter_calls == [("peek", key)], f"the limiter peeked, never hit: {exchange.limiter_calls}"
    assert len(panel.limiter) == 0, "a right credential is never counted"
    print_success("200, PanelCaller, one INFO line, nothing counted")


@pytest.mark.asyncio
async def test_a_scopes_token_never_opens_another_scope(panel: Panel) -> None:
    """HPA-017 (§2): the three tokens set, each presented to the three routes: a route opens to its own scope's token only;
    the token of another scope gets the route's 401 and its line ``refused``/``mismatch`` names the route's scope. Six
    refusals counted."""
    print_section("H-61 §2: no scope's token opens another scope")
    tokens = {scope: panel.new_token(scope) for scope in SCOPES}

    exchanges = {(route, holder): await send(panel, route, authorization=f"Bearer {tokens[holder]}") for route in SCOPES for holder in SCOPES}

    answers = {f"the {route} route, the {holder} token": exchange.answer for (route, holder), exchange in exchanges.items()}
    expected = {f"the {route} route, the {holder} token": (200, {"served": route}) if route == holder else UNAUTHORIZED[route] for route, holder in exchanges}
    assert answers == expected, f"a route opens to its own scope's token only:\n  expected {expected}\n  got      {answers}"
    lines = {f"the {route} route, the {holder} token": exchange.panel_lines for (route, holder), exchange in exchanges.items()}
    expected_lines = {f"the {route} route, the {holder} token": [panel_line(exchange, "accepted") if route == holder else panel_line(exchange, "refused", reason="mismatch")] for (route, holder), exchange in exchanges.items()}
    assert lines == expected_lines, f"each line names the route's scope: {lines}"
    assert panel.limiter.held(rate_key(PEER)) == len(SCOPES) * (len(SCOPES) - 1), f"the six refusals counted: {panel.limiter.held(rate_key(PEER))}"
    print_success("3 accepted, 6 refused")


# =============================================================================
# HPA-020..029 (§2): the limiter
# =============================================================================


@pytest.mark.asyncio
async def test_twenty_refusals_from_one_address_then_429_even_to_the_right_token(panel: Panel) -> None:
    """HPA-020 (§2): 20 refusals from one address, missing and mismatched alike, all in the same instant of the fake
    clock; then the next request — with the right token, with another one, with none — answers 429
    ``panel_too_many_attempts`` with ``Retry-After: 600`` (the window, whole), one WARNING ``Hosting panel request``
    (``limited``, ``retry_after`` 600); the limiter peeked, never hit, the count still 20; the route never runs."""
    print_section("H-61 §2: 20 refusals, then 429")
    token = panel.new_token(BACKUP)
    key = rate_key(PEER)
    refusals = [await send(panel, BACKUP, authorization=None if index % 2 else f"Bearer {a_token()}") for index in range(PANEL_LIMIT)]
    reasons = [line.get("reason") for exchange in refusals for line in exchange.panel_lines]
    counted = panel.limiter.held(key)

    limited = {label: await send(panel, BACKUP, authorization=authorization) for label, authorization in (("the right token", f"Bearer {token}"), ("another token", f"Bearer {a_token()}"), ("no Authorization", None))}

    assert [exchange.answer for exchange in refusals] == [UNAUTHORIZED[BACKUP]] * PANEL_LIMIT, "Precondition: the 20 requests were refused"
    assert sorted(set(reasons)) == ["mismatch", "missing"] and counted == PANEL_LIMIT, f"Precondition: missing and mismatched credentials, 20 counted: {sorted(set(reasons))}, {counted}"
    answers = {label: (exchange.answer, exchange.response.headers.get("retry-after")) for label, exchange in limited.items()}
    assert answers == dict.fromkeys(answers, (TOO_MANY, str(PANEL_WINDOW_SECONDS))), f"429 panel_too_many_attempts with Retry-After 600, whatever the credential: {answers}"
    logged = {label: exchange.panel_lines for label, exchange in limited.items()}
    assert logged == {label: [panel_line(exchange, "limited", retry_after=PANEL_WINDOW_SECONDS)] for label, exchange in limited.items()}, f"one WARNING limited, with retry_after, each: {logged}"
    reads = {label: exchange.limiter_calls for label, exchange in limited.items()}
    assert reads == dict.fromkeys(reads, [("peek", key)]), f"over the limit the limiter is peeked, and nothing more is counted: {reads}"
    assert panel.limiter.held(key) == PANEL_LIMIT, f"the count stays 20: {panel.limiter.held(key)}"
    assert all(exchange.served == [] for exchange in limited.values()), "the route never runs over the limit"
    print_success("the 21st request, the right token included: 429, Retry-After 600, one warning")


@pytest.mark.asyncio
async def test_retry_after_is_the_seconds_left_rounded_up_and_at_least_one(panel: Panel) -> None:
    """HPA-021 (§2): 20 refusals at the start of the fake clock. 0.75 s later 599.25 s are left: ``Retry-After: 600``,
    rounded up (not 599); 599.75 s later 0.25 s are left: ``Retry-After: 1``, at least 1. The line is the limited one,
    whole but for ``retry_after``, a number of seconds that rounds up to the header's."""
    print_section("H-61 §2: Retry-After rounded up, at least 1")
    token = panel.new_token(STATUS)
    await refuse(panel, [STATUS] * PANEL_LIMIT)
    panel.clock.advance(0.75)
    early = await send(panel, STATUS, authorization=f"Bearer {token}")
    panel.clock.advance(599.0)
    late = await send(panel, STATUS, authorization=f"Bearer {token}")

    for label, exchange, left, header in (("0.75 s after the refusals", early, 599.25, 600), ("599.75 s after them", late, 0.25, 1)):
        assert (exchange.answer, exchange.response.headers.get("retry-after")) == (TOO_MANY, str(header)), f"{label}: {left} s left, Retry-After {header} (rounded up, at least 1): {exchange.answer}, {exchange.response.headers.get('retry-after')!r}"
        lines = exchange.panel_lines
        assert len(lines) == 1, f"{label}: one line: {lines}"
        value = lines[0].get("retry_after")
        assert numeric(value) and left <= value <= header and math.ceil(value) == header, f"{label}: the line's retry_after, {value!r}, is the seconds left, {left}, or their rounding up, {header}"
        assert {name: item for name, item in lines[0].items() if name != "retry_after"} == panel_line(exchange, "limited"), f"{label}: the limited line, whole: {lines[0]}"
    print_success("599.25 s left: Retry-After 600; 0.25 s left: Retry-After 1")


@pytest.mark.asyncio
async def test_once_the_window_has_passed_the_address_is_served_again(panel: Panel) -> None:
    """HPA-022 (§2): 20 refusals, then 429; the fake clock moves 600 s: the right token is served, accepted and not
    counted; another one is refused with 401, not 429, and counts from 1 again."""
    print_section("H-61 §2: the window passes")
    token = panel.new_token(WAKE)
    key = rate_key(PEER)
    await refuse(panel, [WAKE] * PANEL_LIMIT)
    limited = await send(panel, WAKE, authorization=f"Bearer {token}")
    panel.clock.advance(PANEL_WINDOW_SECONDS)
    served = await send(panel, WAKE, authorization=f"Bearer {token}")
    after_the_window = panel.limiter.held(key)
    refused = await send(panel, WAKE, authorization=f"Bearer {a_token()}")

    assert limited.answer == TOO_MANY, f"Barrier: before the window passed, the address was over its limit: {limited.answer}"
    assert served.answer == (200, {"served": WAKE}) and served.served == [(WAKE, panel.caller(WAKE))], f"600 s later the right token is served: {served.answer}"
    assert served.panel_lines == [panel_line(served, "accepted")], f"one INFO line, accepted: {served.panel_lines}"
    assert after_the_window == 0, f"the refusals have left the window: {after_the_window}"
    assert refused.answer == UNAUTHORIZED[WAKE] and panel.limiter.held(key) == 1, f"a new refusal is a 401 and counts from 1: {refused.answer}, {panel.limiter.held(key)}"
    print_success("429, then 600 s later 200; a new refusal counts from 1")


@pytest.mark.asyncio
async def test_while_one_address_is_limited_another_is_served_and_counted_on_its_own(panel: Panel) -> None:
    """HPA-023 (§2): one address over its limit; meanwhile another address is served with the right token, and its own
    refusal is a 401 counted on its own key; the first address still meets 429."""
    print_section("H-61 §2: another address")
    token = panel.new_token(BACKUP)
    await refuse(panel, [BACKUP] * PANEL_LIMIT)
    limited = await send(panel, BACKUP, authorization=f"Bearer {token}")

    other_served = await send(panel, BACKUP, authorization=f"Bearer {token}", client=OTHER_PEER)
    other_refused = await send(panel, BACKUP, authorization=f"Bearer {a_token()}", client=OTHER_PEER)
    still = await send(panel, BACKUP, authorization=f"Bearer {token}")

    assert limited.answer == TOO_MANY, f"Barrier: the first address is over its limit: {limited.answer}"
    assert other_served.answer == (200, {"served": BACKUP}) and other_served.limiter_calls == [("peek", rate_key(OTHER_PEER))], f"another address is served, on its own key: {other_served.answer}, {other_served.limiter_calls}"
    assert other_refused.answer == UNAUTHORIZED[BACKUP], f"another address's refusal is a 401, not a 429: {other_refused.answer}"
    assert (panel.limiter.held(rate_key(PEER)), panel.limiter.held(rate_key(OTHER_PEER))) == (PANEL_LIMIT, 1), "each address counts on its own key"
    assert still.answer == TOO_MANY, f"the first address is still over its limit: {still.answer}"
    print_success("one address limited, another served and counted apart")


@pytest.mark.asyncio
async def test_refusals_on_the_three_scopes_add_up_for_one_address(panel: Panel) -> None:
    """HPA-024 (§2): one limiter for the three scopes: 7 refusals on the backup route, 7 on the wake-up, 6 on the status
    make 20 for the address, and each scope then answers it 429, its right token included. Barrier: from another address
    each scope's token opens its route."""
    print_section("H-61 §2: the three scopes add up")
    tokens = {scope: panel.new_token(scope) for scope in SCOPES}
    await refuse(panel, [BACKUP] * 7 + [WAKE] * 7 + [STATUS] * 6)
    counted = panel.limiter.held(rate_key(PEER))

    limited = {scope: await send(panel, scope, authorization=f"Bearer {tokens[scope]}") for scope in SCOPES}
    elsewhere = {scope: await send(panel, scope, authorization=f"Bearer {tokens[scope]}", client=OTHER_PEER) for scope in SCOPES}

    assert counted == PANEL_LIMIT, f"7 + 7 + 6 refusals on three scopes count together for one address: {counted}"
    answers = {scope: exchange.answer for scope, exchange in limited.items()}
    assert answers == dict.fromkeys(SCOPES, TOO_MANY), f"each scope answers the address 429, its right token included: {answers}"
    served = {scope: exchange.answer for scope, exchange in elsewhere.items()}
    assert served == {scope: (200, {"served": scope}) for scope in SCOPES}, f"Barrier: from another address each token opens its route: {served}"
    print_success("7 + 7 + 6 refusals: every scope limited for the address")


@pytest.mark.asyncio
async def test_a_right_credential_is_never_counted(panel: Panel) -> None:
    """HPA-025 (§2): 19 refusals across the scopes, then 5 requests with the right tokens, each served and only peeked:
    the count stays 19. A 20th refusal is still a 401; only then the address meets 429."""
    print_section("H-61 §2: a right credential is never counted")
    tokens = {scope: panel.new_token(scope) for scope in SCOPES}
    key = rate_key(PEER)
    await refuse(panel, [SCOPES[index % len(SCOPES)] for index in range(PANEL_LIMIT - 1)])

    accepted = [await send(panel, scope, authorization=f"Bearer {tokens[scope]}") for scope in (BACKUP, WAKE, STATUS, BACKUP, WAKE)]
    after_accepted = panel.limiter.held(key)
    twentieth = await send(panel, STATUS, authorization=f"Bearer {a_token()}")
    limited = await send(panel, BACKUP, authorization=f"Bearer {tokens[BACKUP]}")

    assert [exchange.answer for exchange in accepted] == [(200, {"served": exchange.scope}) for exchange in accepted], f"the right tokens are served: {[exchange.answer for exchange in accepted]}"
    assert [exchange.limiter_calls for exchange in accepted] == [[("peek", key)]] * len(accepted), "a right credential is peeked, never hit"
    assert after_accepted == PANEL_LIMIT - 1, f"5 right credentials add nothing to the 19 refusals: {after_accepted}"
    assert twentieth.answer == UNAUTHORIZED[STATUS], f"the 20th refusal is still a 401: {twentieth.answer}"
    assert limited.answer == TOO_MANY, f"after the 20th refusal, the address meets 429: {limited.answer}"
    print_success("19 refusals + 5 accepted: count 19; the 20th refusal a 401, then 429")


@pytest.mark.asyncio
async def test_an_ipv6_client_counts_by_its_64(panel: Panel) -> None:
    """HPA-026 (§2): the key is ``client_rate_key`` of the address: an IPv6 client counts by its /64. 20 refusals from one
    address of a /64, then another address of that /64 meets 429, while an address of the next /64 is served."""
    print_section("H-61 §2: an IPv6 client counts by its /64")
    token = panel.new_token(STATUS)
    assert (rate_key(IPV6_PEER), rate_key(IPV6_SAME_64), rate_key(IPV6_NEXT_64)) == (IPV6_KEY, IPV6_KEY, "2001:db8:1:3::/64"), "Precondition: client_rate_key groups an IPv6 address by its /64"
    refusals = await refuse(panel, [STATUS] * PANEL_LIMIT, client=IPV6_PEER)

    same_64 = await send(panel, STATUS, authorization=f"Bearer {token}", client=IPV6_SAME_64)
    next_64 = await send(panel, STATUS, authorization=f"Bearer {token}", client=IPV6_NEXT_64)

    assert [exchange.limiter_calls for exchange in refusals] == [[("peek", IPV6_KEY), ("hit", IPV6_KEY)]] * PANEL_LIMIT, "each refusal counted on the /64's key"
    assert same_64.answer == TOO_MANY, f"another address of the same /64 meets 429: {same_64.answer}"
    assert next_64.answer == (200, {"served": STATUS}), f"an address of the next /64 is served: {next_64.answer}"
    print_success("one /64 limited, the next one served")


@pytest.mark.asyncio
async def test_an_address_read_as_none_is_never_limited(panel: Panel) -> None:
    """HPA-027 (§2): a request through a local reverse proxy LibreFolio does not trust (a Docker-network peer carrying
    ``X-Forwarded-For``) has no address for a limit (``rate_limit_address`` gives None, decision N70): the limiter is
    skipped, never read nor hit. 25 refusals are 401 each, with their lines; then the right token is served. Barrier: the
    same peer without the forwarding header is counted, on its own key."""
    print_section("H-61 §2: an address read as None")
    token = panel.new_token(BACKUP)
    proxy_key = rate_key(DOCKER_PROXY)
    forwarded = {"X-Forwarded-For": FORWARDED_CLIENT}
    counted = await send(panel, BACKUP, authorization=f"Bearer {a_token()}", client=DOCKER_PROXY)

    refusals = await refuse(panel, [BACKUP] * (PANEL_LIMIT + 5), client=DOCKER_PROXY, headers=forwarded)
    served = await send(panel, BACKUP, authorization=f"Bearer {token}", client=DOCKER_PROXY, headers=forwarded)

    assert counted.limiter_calls == [("peek", proxy_key), ("hit", proxy_key)], f"Barrier: without the forwarding header the peer's own address is counted: {counted.limiter_calls}"
    assert [exchange.limiter_calls for exchange in refusals] == [[]] * len(refusals), "without an address, the limiter is never read"
    assert [exchange.panel_lines for exchange in refusals] == [[panel_line(exchange, "refused", reason="mismatch")] for exchange in refusals], "each refusal still logs its line"
    assert served.answer == (200, {"served": BACKUP}) and served.limiter_calls == [] and served.panel_lines == [panel_line(served, "accepted")], f"the right token is served, the limiter skipped: {served.answer}, {served.limiter_calls}"
    assert (panel.limiter.held(proxy_key), len(panel.limiter)) == (1, 1), "nothing counted but the barrier's refusal"
    print_success(f"{len(refusals)} refusals through a proxy nobody trusts: never limited")


@pytest.mark.asyncio
async def test_the_scopes_token_is_read_before_the_limiter(panel: Panel) -> None:
    """HPA-028 (§2): an address over its limit. A scope whose token is unset still answers it 404, and one whose token is
    unusable 503 with its two lines, neither reading the limiter: the token comes first. Barrier: the address is over its
    limit, and the same scope, once its token is set, answers it 429."""
    print_section("H-61 §2: the token before the limiter")
    token = panel.new_token(BACKUP)
    panel.set_unusable(STATUS, "too-short")
    error = reader_error(STATUS)
    await refuse(panel, [BACKUP] * PANEL_LIMIT)
    limited = await send(panel, BACKUP, authorization=f"Bearer {token}")

    off = await send(panel, WAKE, authorization=f"Bearer {a_token()}")
    unavailable = await send(panel, STATUS, authorization=f"Bearer {a_token()}")
    wake_now = panel.new_token(WAKE)
    wake_limited = await send(panel, WAKE, authorization=f"Bearer {wake_now}")

    assert limited.answer == TOO_MANY, f"Barrier: the address is over its limit: {limited.answer}"
    assert (off.answer, off.events, off.limiter_calls) == (OFF_ANSWER, [], []), f"a scope off answers 404 before the limiter, no line: {off.answer}, {off.events}, {off.limiter_calls}"
    assert (unavailable.answer, unavailable.limiter_calls) == (UNAVAILABLE[STATUS], []), f"an unusable token answers 503 before the limiter: {unavailable.answer}, {unavailable.limiter_calls}"
    assert unavailable.lines(*UNUSABLE_LINES.values(), PANEL_LINE) == [error_line(STATUS, error), panel_line(unavailable, "unavailable", reason="unusable")], f"the two lines of the 503: {unavailable.events}"
    assert wake_limited.answer == TOO_MANY, f"Barrier: the wake-up's token set, the shared limiter answers the address 429: {wake_limited.answer}"
    print_success("over the limit: 404 off, 503 unusable, before the limiter")


@pytest.mark.asyncio
async def test_the_key_is_the_address_rate_limit_address_gives(panel: Panel, monkeypatch: pytest.MonkeyPatch) -> None:
    """HPA-029 (§2): the key is ``client_rate_key(rate_limit_address(request))``, never the peer's own address: behind a
    proxy whose client header LibreFolio reads (``LIBREFOLIO_CLIENT_IP_HEADER``, here replaced through ``monkeypatch``),
    the two clients the proxy forwards count apart. 20 refusals for the first, then 429 for it, while the second is
    served; the proxy's own address is never counted."""
    print_section("H-61 §2: the key, the address rate_limit_address gives")
    monkeypatch.setattr(client_address_module, "_configured_header", lambda: CLIENT_IP_HEADER.lower())
    token = panel.new_token(WAKE)
    first, second = "198.51.100.71", "198.51.100.72"
    refusals = await refuse(panel, [WAKE] * PANEL_LIMIT, client=DOCKER_PROXY, headers={CLIENT_IP_HEADER: first})

    limited = await send(panel, WAKE, authorization=f"Bearer {token}", client=DOCKER_PROXY, headers={CLIENT_IP_HEADER: first})
    other = await send(panel, WAKE, authorization=f"Bearer {token}", client=DOCKER_PROXY, headers={CLIENT_IP_HEADER: second})

    assert [exchange.limiter_calls for exchange in refusals] == [[("peek", first), ("hit", first)]] * PANEL_LIMIT, "each refusal counted on the forwarded client's key"
    assert limited.answer == TOO_MANY, f"the first client is over its limit: {limited.answer}"
    assert other.answer == (200, {"served": WAKE}) and other.limiter_calls == [("peek", second)], f"the second client is served, on its own key: {other.answer}, {other.limiter_calls}"
    assert panel.limiter.held(rate_key(DOCKER_PROXY)) == 0, "the proxy's own address is never counted"
    print_success("two clients behind one proxy, counted apart")


# =============================================================================
# HPA-030..032 (§2): the lines
# =============================================================================


@pytest.mark.asyncio
async def test_a_line_names_the_requests_path_never_its_query(panel: Panel) -> None:
    """HPA-030 (§2): every outcome of a request sent with ``?token=<canary>`` — accepted; refused, the token in the query
    only (missing); refused, another token (mismatch); limited; unavailable — logs its line whole, the path
    (``scope["path"]``) without the query; the canary is in no line and no answer (each request checks it)."""
    print_section("H-61 §2: the path, never the query")
    token = panel.new_token(STATUS)
    panel.set_unusable(WAKE, "too-short")
    error = reader_error(WAKE)
    query = {"token": f"canary-q-{uuid.uuid4().hex}"}

    accepted = await send(panel, STATUS, authorization=f"Bearer {token}", params=query)
    missing = await send(panel, STATUS, params={"token": token, "access_token": token})
    mismatch = await send(panel, STATUS, authorization=f"Bearer {a_token()}", params=query)
    await refuse(panel, [STATUS] * (PANEL_LIMIT - 2), params=query)
    limited = await send(panel, STATUS, authorization=f"Bearer {token}", params=query)
    unavailable = await send(panel, WAKE, authorization=f"Bearer {token}", params=query)

    cases = {
        "accepted": (accepted, 200, [panel_line(accepted, "accepted")]),
        "refused, missing": (missing, 401, [panel_line(missing, "refused", reason="missing")]),
        "refused, mismatch": (mismatch, 401, [panel_line(mismatch, "refused", reason="mismatch")]),
        "limited": (limited, 429, [panel_line(limited, "limited", retry_after=PANEL_WINDOW_SECONDS)]),
        "unavailable": (unavailable, 503, [error_line(WAKE, error), panel_line(unavailable, "unavailable", reason="unusable")]),
    }
    statuses = {label: exchange.response.status_code for label, (exchange, _, _) in cases.items()}
    assert statuses == {label: status for label, (_, status, _) in cases.items()}, f"Precondition: each outcome reached: {statuses}"
    logged = {label: exchange.lines(*UNUSABLE_LINES.values(), PANEL_LINE) for label, (exchange, _, _) in cases.items()}
    assert logged == {label: lines for label, (_, _, lines) in cases.items()}, f"each line whole, its path without the query: {logged}"
    print_success("five outcomes, five paths without their query")


@pytest.mark.asyncio
async def test_behind_the_request_id_middleware_every_line_carries_its_requests_id(panel: Panel) -> None:
    """HPA-031 (§2): the test routes behind ``RequestIdMiddleware``: the lines of an accepted, a refused and an unavailable
    request — the error line included — carry the ``request_id`` of their own request, the one its answer's
    ``X-Request-Id`` carries, from structlog's contextvars. Without the middleware, the other tests' lines carry none."""
    print_section("H-61 §2: the request id in the lines")
    app = panel_app(panel.access, request_ids=True)
    token = panel.new_token(BACKUP)
    panel.set_unusable(WAKE, "too-short")
    error = reader_error(WAKE)

    accepted = await send(panel, BACKUP, authorization=f"Bearer {token}", app=app)
    refused = await send(panel, BACKUP, authorization=f"Bearer {a_token()}", app=app)
    unavailable = await send(panel, WAKE, app=app)

    exchanges = {"accepted": accepted, "refused": refused, "unavailable": unavailable}
    statuses = {label: exchange.response.status_code for label, exchange in exchanges.items()}
    assert statuses == {"accepted": 200, "refused": 401, "unavailable": 503}, f"Precondition: each outcome reached: {statuses}"
    ids = {label: exchange.request_id for label, exchange in exchanges.items()}
    assert all(isinstance(value, str) and REQUEST_ID_SHAPE.fullmatch(value) for value in ids.values()) and len(set(ids.values())) == len(ids), f"Barrier: each answer carries an id of its own: {ids}"
    expected = {
        "accepted": [panel_line(accepted, "accepted", request_id=ids["accepted"])],
        "refused": [panel_line(refused, "refused", reason="mismatch", request_id=ids["refused"])],
        "unavailable": [error_line(WAKE, error, request_id=ids["unavailable"]), panel_line(unavailable, "unavailable", reason="unusable", request_id=ids["unavailable"])],
    }
    logged = {label: exchange.lines(*UNUSABLE_LINES.values(), PANEL_LINE) for label, exchange in exchanges.items()}
    assert logged == expected, f"each line carries its own request's id:\n  expected {expected}\n  got      {logged}"
    print_success("each line with its request's id")


@pytest.mark.asyncio
async def test_no_secret_reaches_a_line_a_field_or_an_answer(panel: Panel) -> None:
    """HPA-032 (§2): every outcome at once — accepted, refused with another scope's token, refused under ``Basic``,
    unavailable to the configured value itself, limited, off — each request sent with a query canary and the canary header.
    No configured token, no value sent, no ``Authorization``, no header value, no query value and not the client's address
    in any answer, its headers, any line or any field (each request checks it). Barriers: each outcome reached, one line
    for each request but the 404, every line holding nothing but the contract's fields."""
    print_section("H-61 §2: no secret anywhere")
    tokens = {BACKUP: panel.new_token(BACKUP), STATUS: panel.new_token(STATUS)}
    unusable = panel.set_unusable(WAKE, "too-short")
    query = {"token": f"canary-q-{uuid.uuid4().hex}"}

    exchanges = [
        await send(panel, STATUS, authorization=f"Bearer {tokens[STATUS]}", params=query),
        await send(panel, STATUS, authorization=f"Bearer {tokens[BACKUP]}", params=query),
        await send(panel, BACKUP, authorization=f"Basic {tokens[BACKUP]}", params=query),
        await send(panel, WAKE, authorization=f"Bearer {unusable.presentable[0]}", params=query),
    ]
    exchanges += await refuse(panel, [BACKUP] * (PANEL_LIMIT - 2), params=query)
    exchanges.append(await send(panel, BACKUP, authorization=f"Bearer {tokens[BACKUP]}", params=query))
    panel.unset(STATUS, "neither-variable")
    exchanges.append(await send(panel, STATUS, authorization=f"Bearer {tokens[STATUS]}", params=query))

    statuses = [exchange.response.status_code for exchange in exchanges]
    assert statuses == [200, 401, 401, 503, *[401] * (PANEL_LIMIT - 2), 429, 404], f"Precondition: each outcome reached: {statuses}"
    lines = [line for exchange in exchanges for line in exchange.panel_lines]
    assert len(lines) == len(exchanges) - 1, f"Barrier: one line for each request but the 404, so the secrets were looked for in real lines: {len(lines)}"
    outcomes = {(line.get("outcome"), line.get("reason")) for line in lines}
    assert outcomes == {("accepted", None), ("refused", "mismatch"), ("refused", "missing"), ("unavailable", "unusable"), ("limited", None)}, f"Barrier: every outcome logged: {outcomes}"
    stray = [sorted(set(line) - LINE_KEYS) for line in lines if set(line) - LINE_KEYS]
    assert stray == [], f"a line holds nothing but the contract's fields: {stray}"
    print_success(f"{len(exchanges)} requests, {len(lines)} lines: no secret anywhere")


# =============================================================================
# HPA-040..042 (§2): constant time, structurally
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", SCOPES)
async def test_the_credential_is_compared_with_hmac_compare_digest_on_its_utf8_bytes(panel: Panel, monkeypatch: pytest.MonkeyPatch, scope: str) -> None:
    """HPA-040 (§2): the right token and another one are each compared once, through the access module's
    ``hmac.compare_digest``, with two ``bytes``: the UTF-8 bytes of the credential presented and of the scope's token."""
    print_section(f"H-61 §2: hmac.compare_digest for the {scope} scope")
    token = panel.new_token(scope)
    spy = spy_on_hmac(monkeypatch, panel.access)
    wrong = a_token()

    right = await send(panel, scope, authorization=f"Bearer {token}")
    right_calls = list(spy.calls)
    refused = await send(panel, scope, authorization=f"Bearer {wrong}")
    refused_calls = spy.calls[len(right_calls) :]

    assert (right.answer, refused.answer) == ((200, {"served": scope}), UNAUTHORIZED[scope]), f"Precondition: the right token served, another refused: {right.answer}, {refused.answer}"
    for label, calls, presented in (("the right token", right_calls, token), ("another token", refused_calls, wrong)):
        kinds = [(type(first).__name__, type(second).__name__) for first, second in calls]
        assert kinds == [("bytes", "bytes")], f"{label}: one comparison, of two bytes: {kinds}"
        assert sorted(calls[0]) == sorted([presented.encode("utf-8"), token.encode("utf-8")]), f"{label}: the UTF-8 bytes of the credential presented and of the token are compared (lengths {[len(value) for value in calls[0]]})"
    print_success("one compare_digest of two bytes per credential")


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", SCOPES)
async def test_the_decision_is_hmac_compare_digests(panel: Panel, monkeypatch: pytest.MonkeyPatch, scope: str) -> None:
    """HPA-041 (§2): the answer of ``hmac.compare_digest`` is the decision, nothing else: made to answer False, the right
    token is refused (``mismatch``, counted); made to answer True, another token is let through (``accepted``, the
    caller)."""
    print_section(f"H-61 §2: compare_digest decides, {scope} scope")
    token = panel.new_token(scope)
    spy = spy_on_hmac(monkeypatch, panel.access)
    spy.answer = False
    vetoed = await send(panel, scope, authorization=f"Bearer {token}")
    spy.answer = True
    let_through = await send(panel, scope, authorization=f"Bearer {a_token()}")

    assert len(spy.calls) == 2, f"each credential compared once: {len(spy.calls)} comparison(s)"
    assert vetoed.answer == UNAUTHORIZED[scope] and vetoed.panel_lines == [panel_line(vetoed, "refused", reason="mismatch")], f"compare_digest False: the right token refused: {vetoed.answer}, {vetoed.panel_lines}"
    assert let_through.answer == (200, {"served": scope}) and let_through.served == [(scope, panel.caller(scope))], f"compare_digest True: the request let through: {let_through.answer}"
    assert let_through.panel_lines == [panel_line(let_through, "accepted")], f"accepted: {let_through.panel_lines}"
    assert panel.limiter.held(rate_key(PEER)) == 1, "the refusal counted, the acceptance not"
    print_success("False refuses the right token, True lets another through")


@pytest.mark.asyncio
async def test_over_the_limit_the_credential_is_never_compared(panel: Panel, monkeypatch: pytest.MonkeyPatch) -> None:
    """HPA-042 (§2): over the limit «the credential is not looked at»: 20 refusals, each compared once (barrier), then the
    right token and another one meet 429 without a single comparison."""
    print_section("H-61 §2: over the limit, no comparison")
    token = panel.new_token(WAKE)
    spy = spy_on_hmac(monkeypatch, panel.access)
    await refuse(panel, [WAKE] * PANEL_LIMIT)
    compared = len(spy.calls)

    limited = [await send(panel, WAKE, authorization=f"Bearer {token}"), await send(panel, WAKE, authorization=f"Bearer {a_token()}")]

    assert compared == PANEL_LIMIT, f"Barrier: each refusal compared its credential once: {compared}"
    assert [exchange.answer for exchange in limited] == [TOO_MANY, TOO_MANY], f"over the limit: 429: {[exchange.answer for exchange in limited]}"
    assert spy.calls[compared:] == [], f"over the limit the credential is not looked at: {len(spy.calls) - compared} comparison(s)"
    print_success("429 twice, no comparison")
