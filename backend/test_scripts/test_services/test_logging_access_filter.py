"""
Credentials in the request lines uvicorn logs (workstream H, lot "credentials in access logs").

Under test: ``backend/app/logging_config.py``. uvicorn logs each HTTP request on ``uvicorn.access`` with
``record.args = (client, method, path, http_version, status)``, and each WebSocket handshake on ``uvicorn.error`` with
``(client, path[, status])``; ``path`` holds the query string as the client sent it. The contract:

(a) ``mask_query_credentials(text)`` reads every query parameter after ``?`` or ``&``; a value ends at ``&``, ``#``,
    ``?`` or a blank, so a URL nested unencoded in a value is read parameter by parameter. It replaces with ``***`` the
    value of every parameter whose name, percent-decoded as the app reads it, is exactly ``code`` or holds ``token``,
    ``secret``, ``password``, ``passwd``, ``api_key``/``apikey``/``api-key``, ``signature`` or ``ticket``, in any case;
    the name stays as written. ``ticket`` since workstream B's lot B5c: the one-time ticket of a restore's outcome
    (``outcome_ticket`` in the restart's answer) travels in a header, and one typed by hand into a URL must not reach the
    log in clear either. Everything else is kept: other parameters, one whose value says ``token`` or ``ticket``, a
    ``ticker`` (a word of this finance app that only looks like it), the path, a fragment. An empty credential value
    shows ``***``. A text with no query comes back as it is. A limit, pinned: a value is not decoded, so a URL encoded
    inside another parameter's value is not read.
(b) ``_QUERY_CREDENTIAL_FILTER`` lets every record through. With a tuple of args it masks every string argument where it
    stands, at any position and for any number of args, so they keep their number and order; the other args are the
    same objects, a non-string one (bytes, ``None``, an int) is not read, and with nothing to mask the args object itself
    is kept. A mapping passes unchanged. A message logged without args (``()`` or ``None``) is masked itself when it is a
    string. A format string with args is never rewritten, so its placeholders keep matching them.
(c) On the records uvicorn itself logs, each with its negative control, the same request without the filter showing the
    value: an HTTP request through h11 and httptools gives the ``uvicorn.access`` line, read through uvicorn's
    ``AccessFormatter``, ``"GET /setup?token=***&next=/home HTTP/1.1" 200 OK``; a WebSocket handshake through the same
    two protocols, handed over as uvicorn does to the WebSocket protocol ``--ws auto`` picks and refused by the app,
    gives the ``uvicorn.error`` line ``"WebSocket /ws?token=***&next=/home" 403``. uvicorn's two other handshake
    messages, ``[accepted]`` and a status of the app's own, are checked on records built as uvicorn builds them.
(d) ``configure_logging()`` adds that one filter object to ``uvicorn.access`` and ``uvicorn.error``: called twice, each
    logger holds it once, and the lines uvicorn then logs on the two loggers it picks itself come out masked.
(e) ``configure_logging()`` closes every handler it takes off the root logger (H-9): called twice, the log file the first
    call opened is closed and the second call's handlers are on the root, their log file open; a file handler it finds
    on the root is closed too.

A limit, not tested: with uvicorn at ``--log-level trace``, its ``MessageLoggerMiddleware`` logs the whole ASGI scope on
``uvicorn.asgi``, the query string in clear. That logger has no filter, and the scope is a dict argument, which the filter
does not read. Neither ``dev.py`` nor the image passes ``--log-level``.

Pure: no server, no socket, no database, no network, and no file written outside a test's own ``tmp_path``, where the
tests of (e) open their log files: the lane's ``logs/`` is never opened. A request is fed to uvicorn's protocol objects in
memory, through a transport that only collects what is written to it. The tests of (b) and the HTTP tests of (c) log on
private ``logging.Logger`` objects, outside the logging tree; the tests that use the real ``uvicorn.error`` or call
``configure_logging()`` put every logger, the root handlers pytest attached for the test and structlog's configuration
back before they end. Every value standing for a credential is a placeholder.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import copy
import inspect
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import pytest
import structlog
from uvicorn.config import Config
from uvicorn.logging import AccessFormatter, DefaultFormatter
from uvicorn.protocols.http.auto import AutoHTTPProtocol
from uvicorn.protocols.http.h11_impl import H11Protocol
from uvicorn.protocols.http.httptools_impl import HttpToolsProtocol
from uvicorn.protocols.websockets.auto import AutoWebSocketsProtocol
from uvicorn.server import ServerState

from backend.app.config import get_data_dir
from backend.app.logging_config import _QUERY_CREDENTIAL_FILTER, _QueryCredentialFilter, configure_logging, get_log_directory, mask_query_credentials
from backend.test_scripts.test_utils import print_section, print_success

#: Stands for every credential value in this file: obviously not one.
PLACEHOLDER = "placeholder-value"
#: The message uvicorn's HTTP protocols (``h11_impl``, ``httptools_impl``) log on ``uvicorn.access`` for each request.
UVICORN_ACCESS_MESSAGE = '%s - "%s %s HTTP/%s" %d'
#: The message uvicorn's WebSocket protocols log on ``uvicorn.error`` when the app refuses the handshake.
UVICORN_WEBSOCKET_REFUSED = '%s - "WebSocket %s" 403'
#: uvicorn's default access format (``uvicorn.config.LOGGING_CONFIG``) without its level prefix.
ACCESS_FORMAT = '%(client_addr)s - "%(request_line)s" %(status_code)s'
#: The two loggers ``configure_logging()`` filters.
UVICORN_LOGGERS = ("uvicorn.access", "uvicorn.error")
#: The peer of the in-memory connection, and the client uvicorn logs for it.
PEER = ("127.0.0.1", 54321)
CLIENT = "127.0.0.1:54321"
#: The HTTP request of the protocol tests: a credential first, an ordinary parameter after it.
TARGET = f"/setup?token={PLACEHOLDER}&next=/home"
MASKED_TARGET = "/setup?token=***&next=/home"
MASKED_LINE = f'{CLIENT} - "GET {MASKED_TARGET} HTTP/1.1" 200 OK'
#: The WebSocket handshake of the protocol tests, and the line uvicorn logs for it once masked.
WS_TARGET = f"/ws?token={PLACEHOLDER}&next=/home"
WS_MASKED_TARGET = "/ws?token=***&next=/home"
WS_MASKED_LINE = f'{CLIENT} - "WebSocket {WS_MASKED_TARGET}" 403'
#: RFC 6455's ``Sec-WebSocket-Key``: 16 bytes in base64, a nonce of the handshake and not a secret.
WEBSOCKET_NONCE = base64.b64encode(b"sixteen-byte-key").decode("ascii")


# ── (a) the rule ─────────────────────────────────────────────────────────────

#: Parameter names whose value is masked: every word, as a whole name, inside a longer one, in another case, with a hyphen.
MASKED_NAMES = ["token", "reset_token", "TOKEN", "api_key", "apikey", "API_KEY", "api-key", "API-KEY", "client_secret", "password", "passwd", "signature", "code", "CODE", "ticket", "outcome_ticket", "TICKET", "Restore-Ticket"]

#: Where a parameter sits: right after ``?``, or after ``&`` between two ordinary parameters that must be kept.
POSITIONS = [
    pytest.param("/api/v1/items?{}", id="first-after-question-mark"),
    pytest.param("/api/v1/items?page=2&{}&size=50", id="later-after-ampersand"),
]


@pytest.mark.parametrize("position", POSITIONS)
@pytest.mark.parametrize("name", MASKED_NAMES)
def test_the_value_of_a_credential_parameter_is_masked(name, position):
    path = position.format(f"{name}={PLACEHOLDER}")

    masked = mask_query_credentials(path)

    assert masked == position.format(f"{name}=***")


@pytest.mark.parametrize("position", POSITIONS)
@pytest.mark.parametrize(
    "name",
    [
        pytest.param("tok%65n", id="token"),
        pytest.param("api%5Fkey", id="api_key"),
        pytest.param("c%6Fde", id="code"),
        pytest.param("tick%65t", id="ticket"),
    ],
)
def test_a_percent_encoded_name_is_judged_decoded_and_kept_as_written(name, position):
    path = position.format(f"{name}={PLACEHOLDER}")

    masked = mask_query_credentials(path)

    assert masked == position.format(f"{name}=***")


@pytest.mark.parametrize("position", POSITIONS)
@pytest.mark.parametrize(
    "parameter",
    [
        pytest.param("currency_code=EUR", id="code-ends-the-name"),
        pytest.param("currency%5Fcode=EUR", id="code-ends-the-decoded-name"),
        pytest.param("codes=a,b", id="code-starts-the-name"),
        pytest.param("q=token", id="the-value-says-token"),
        pytest.param("q=ticket", id="the-value-says-ticket"),
        pytest.param("ticker=AAPL", id="ticker-is-not-ticket"),
        pytest.param("sort=name", id="sort"),
    ],
)
def test_a_parameter_that_is_not_a_credential_is_kept(parameter, position):
    path = position.format(parameter)

    assert mask_query_credentials(path) == path


def test_several_credentials_in_one_query_are_masked_and_the_others_kept():
    path = f"/api/v1/items?token={PLACEHOLDER}&sort=name&Password={PLACEHOLDER}&currency_code=EUR&x_signature={PLACEHOLDER}&API-KEY={PLACEHOLDER}&c%6Fde={PLACEHOLDER}&token={PLACEHOLDER}"

    masked = mask_query_credentials(path)

    assert masked == "/api/v1/items?token=***&sort=name&Password=***&currency_code=EUR&x_signature=***&API-KEY=***&c%6Fde=***&token=***"


def test_the_path_and_the_fragment_are_kept():
    # The path segments hold credential words, the fragment follows the value: only the value goes.
    assert mask_query_credentials(f"/api/v1/auth/password/reset_token?token={PLACEHOLDER}#section") == "/api/v1/auth/password/reset_token?token=***#section"
    assert mask_query_credentials("/api/v1/auth/password/reset_token?lang=en#section") == "/api/v1/auth/password/reset_token?lang=en#section"


def test_an_empty_credential_value_shows_the_mask_and_an_empty_ordinary_value_is_kept():
    assert mask_query_credentials("/setup?token=&next=/home") == "/setup?token=***&next=/home"
    assert mask_query_credentials("/setup?next=&token=") == "/setup?next=&token=***"


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/", id="root"),
        pytest.param("/api/v1/system/info", id="plain"),
        pytest.param("/api/v1/auth/password/reset_token", id="credential-words-in-the-path"),
        pytest.param("/setup?", id="empty-query"),
    ],
)
def test_a_path_without_a_query_comes_back_as_it_is(path):
    assert mask_query_credentials(path) == path


@pytest.mark.parametrize(
    ("path", "masked"),
    [
        pytest.param(f"/setup?next=/a?token={PLACEHOLDER}&x=1", "/setup?next=/a?token=***&x=1", id="token-in-next"),
        pytest.param(f"/login?next=/oauth?code={PLACEHOLDER}&state=s1", "/login?next=/oauth?code=***&state=s1", id="code-in-next"),
    ],
)
def test_a_url_nested_unencoded_in_a_value_is_read_parameter_by_parameter(path, masked):
    assert mask_query_credentials(path) == masked


def test_limit_a_url_encoded_inside_a_value_is_not_read():
    encoded = f"%2Fsetup%3Ftoken%3D{PLACEHOLDER}"
    # Barrier: the same URL, decoded, is masked; what keeps it below is the encoding alone.
    assert mask_query_credentials(f"/login?redirect={unquote(encoded)}") == "/login?redirect=/setup?token=***"

    masked = mask_query_credentials(f"/login?redirect={encoded}")

    assert masked == f"/login?redirect={encoded}", "a value is not decoded: a documented limit, which only a decision changes"


# ── (b) the filter on a record ───────────────────────────────────────────────


def _record(args: Any, msg: Any = "a message that is not uvicorn's", name: str = "uvicorn.access") -> logging.LogRecord:
    """A record of ``name`` whose ``args`` are exactly ``args``: set after construction, so a mapping stays one."""
    record = logging.LogRecord(name, logging.INFO, __file__, 1, msg, None, None)
    record.args = args
    return record


#: The arguments around the credential path: strings with nothing to mask, and arguments that are not strings.
OTHER_ARGS = (CLIENT, 403, "GET", None, b"/raw", "/plain?sort=name")


def _arities_and_positions() -> Iterator[Any]:
    """Every position of the credential path in a tuple of one to six args."""
    for arity in range(1, len(OTHER_ARGS) + 1):
        for position in range(arity):
            yield pytest.param(arity, position, id=f"{arity}-args-path-at-{position}")


@pytest.mark.parametrize(("arity", "position"), list(_arities_and_positions()))
def test_a_string_argument_is_masked_where_it_stands_and_the_others_are_kept(arity, position):
    others = OTHER_ARGS[: arity - 1]
    args = (*others[:position], TARGET, *others[position:])
    record = _record(args)

    kept = _QUERY_CREDENTIAL_FILTER.filter(record)

    assert kept is True, "the filter must never drop a record"
    assert record.args == (*others[:position], MASKED_TARGET, *others[position:])
    assert all(after is before for before, after in zip(args, record.args, strict=True) if not isinstance(before, str)), "an argument that is not a string was replaced"


@pytest.mark.parametrize(
    "args",
    [
        pytest.param((CLIENT, "GET", "/api/v1/system/info", "1.1", 200), id="uvicorn-record-without-query"),
        pytest.param((CLIENT, "GET", "/api/v1/items?sort=name&currency_code=EUR", "1.1", 200), id="uvicorn-record-ordinary-query"),
        pytest.param((403, None, b"/raw"), id="no-string-arg"),
    ],
)
def test_with_nothing_to_mask_the_args_object_is_kept(args):
    record = _record(args)

    kept = _QUERY_CREDENTIAL_FILTER.filter(record)

    assert kept is True, "the filter must never drop a record"
    assert record.args is args, "the filter replaced args it had nothing to mask in"


def test_an_argument_that_is_not_a_string_is_not_read():
    raw = f"/raw?token={PLACEHOLDER}".encode("ascii")
    args = (raw, None, 403, TARGET)
    record = _record(args)

    _QUERY_CREDENTIAL_FILTER.filter(record)

    assert record.args == (raw, None, 403, MASKED_TARGET)
    assert all(record.args[index] is args[index] for index in range(3)), "bytes, None and an int must pass as the same objects"


def test_a_mapping_passes_unchanged():
    mapping = {"path": TARGET}
    record = _record(mapping, msg="%(path)s")

    kept = _QUERY_CREDENTIAL_FILTER.filter(record)

    # uvicorn never logs with a mapping.
    assert kept is True, "the filter must never drop a record"
    assert record.args is mapping and mapping == {"path": TARGET}, "the filter changed a mapping"
    assert record.msg == "%(path)s"


@pytest.mark.parametrize("args", [pytest.param((), id="empty-tuple"), pytest.param(None, id="none")])
def test_a_message_logged_without_args_is_masked_itself(args):
    record = _record(args, msg=f'{CLIENT} - "GET {TARGET} HTTP/1.1" 200')

    kept = _QUERY_CREDENTIAL_FILTER.filter(record)

    assert kept is True, "the filter must never drop a record"
    assert record.msg == f'{CLIENT} - "GET {MASKED_TARGET} HTTP/1.1" 200'
    assert record.args is args
    assert record.getMessage() == record.msg


def test_a_message_that_is_not_a_string_is_untouched():
    message = {"event": "request", "path": TARGET}
    record = _record(None, msg=message)

    _QUERY_CREDENTIAL_FILTER.filter(record)

    assert record.msg is message and message == {"event": "request", "path": TARGET}, "the filter changed a message that is not a string"


def test_a_format_string_with_args_keeps_its_placeholders_matching_their_args():
    # Rewritten, ``token=%s`` would become ``token=***`` and leave ``%d`` with two args: getMessage() would raise.
    message = "GET /setup?token=%s&attempt=%d"
    args = (PLACEHOLDER, 2)
    record = _record(args, msg=message)

    _QUERY_CREDENTIAL_FILTER.filter(record)

    assert record.msg is message, "the filter rewrote a format string that has args"
    assert record.args is args, "the filter replaced args it had nothing to mask in"
    try:
        record.getMessage()
    except (TypeError, ValueError) as error:
        pytest.fail(f"the placeholders of the format string no longer match its args: {error}")


# ── (c) the filter on the records uvicorn logs ───────────────────────────────


class _CapturedLines(logging.Handler):
    """Keeps every record it handles, and its line as ``formatter`` writes it."""

    def __init__(self, formatter: logging.Formatter) -> None:
        super().__init__()
        self.setFormatter(formatter)
        self.records: list[logging.LogRecord] = []
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)
        self.lines.append(self.format(record))

    def lines_of(self, message: str) -> list[str]:
        """The lines of the records logged with ``message``."""
        return [line for record, line in zip(self.records, self.lines, strict=True) if record.msg == message]


def _access_lines() -> _CapturedLines:
    """The ``uvicorn.access`` lines as uvicorn's ``AccessFormatter`` writes them, without colours."""
    return _CapturedLines(AccessFormatter(ACCESS_FORMAT, use_colors=False))


def _error_lines() -> _CapturedLines:
    """The ``uvicorn.error`` lines as uvicorn's ``DefaultFormatter`` writes them, without colours or level prefix."""
    return _CapturedLines(DefaultFormatter("%(message)s", use_colors=False))


class _MemoryTransport:
    """What uvicorn's protocols need of a transport: the peer, a sink for the response, ``close``, the protocol it feeds. Nothing leaves the process."""

    def __init__(self, protocol: asyncio.Protocol) -> None:
        self.protocol = protocol
        self.closed = False
        self.sent = bytearray()

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        return {"peername": PEER, "sockname": ("127.0.0.1", 6040)}.get(name, default)

    def write(self, data: bytes) -> None:
        self.sent += data

    def is_closing(self) -> bool:
        return self.closed

    def close(self) -> None:
        self.closed = True

    def pause_reading(self) -> None:
        """Flow control has nothing to pause: the request is already in memory."""

    def resume_reading(self) -> None:
        """Flow control has nothing to resume."""

    def set_protocol(self, protocol: asyncio.Protocol) -> None:
        """Called by the HTTP protocol when it hands the connection over to the WebSocket one."""
        self.protocol = protocol

    def get_protocol(self) -> asyncio.Protocol:
        return self.protocol


async def _app(scope: dict, receive: Any, send: Any) -> None:
    """Answers an HTTP request with 200 and an empty body; refuses a WebSocket handshake, which uvicorn answers with 403."""
    if scope["type"] == "websocket":
        connect = await receive()
        assert connect["type"] == "websocket.connect", f"the first WebSocket event is {connect['type']!r}"
        await send({"type": "websocket.close", "code": 1000})
        return
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b""})


def _http_request(target: str) -> bytes:
    return f"GET {target} HTTP/1.1\r\nHost: librefolio.invalid\r\n\r\n".encode("ascii")


def _websocket_request(target: str) -> bytes:
    headers = ["Host: librefolio.invalid", "Upgrade: websocket", "Connection: Upgrade", f"Sec-WebSocket-Key: {WEBSOCKET_NONCE}", "Sec-WebSocket-Version: 13"]
    return "\r\n".join([f"GET {target} HTTP/1.1", *headers, "", ""]).encode("ascii")


@dataclass(frozen=True)
class _Served:
    """What the client got back, and the protocol the connection ended with."""

    sent: bytes
    protocol: asyncio.Protocol


def _serve(protocol_class: type, request: bytes, access_logger: logging.Logger | None = None) -> _Served:
    """Feed ``request`` to a new connection of ``protocol_class`` in memory, run the ASGI cycle it starts to its end, close the connection.

    An upgrade request is handed over to the WebSocket protocol ``--ws auto`` picks, as uvicorn does: the transport then
    feeds that one. With ``access_logger`` the HTTP protocol logs on it, instead of on the ``uvicorn.access`` it picks itself.
    """

    async def serve() -> _Served:
        config = Config(app=_app, log_config=None, lifespan="off", proxy_headers=False, ws="auto")
        state = ServerState()
        protocol = protocol_class(config=config, server_state=state, app_state={}, _loop=asyncio.get_running_loop())
        if access_logger is not None:
            protocol.access_logger, protocol.access_log = access_logger, True
        transport = _MemoryTransport(protocol)
        protocol.connection_made(transport)
        protocol.data_received(request)
        cycles = list(state.tasks)
        assert len(cycles) == 1, f"the request started {len(cycles)} ASGI cycles, not one"
        await asyncio.wait_for(asyncio.gather(*cycles), timeout=10)
        transport.protocol.connection_lost(None)
        return _Served(bytes(transport.sent), transport.protocol)

    return asyncio.run(serve())


def _private_access_logger(*filters: logging.Filter) -> tuple[logging.Logger, _CapturedLines]:
    """A logger named like uvicorn's but outside the logging tree (no parent, no other handler), with ``filters`` and a capture."""
    logger = logging.Logger("uvicorn.access", logging.INFO)
    for log_filter in filters:
        logger.addFilter(log_filter)
    captured = _access_lines()
    logger.addHandler(captured)
    return logger, captured


@pytest.fixture(params=[H11Protocol, HttpToolsProtocol], ids=["h11", "httptools"])
def protocol_class(request) -> type:
    """Each HTTP protocol uvicorn can run: ``--http auto`` picks httptools when installed, h11 otherwise."""
    return request.param


def test_negative_control_without_the_filter_the_access_line_shows_the_value(protocol_class):
    print_section(f"Access log, {protocol_class.__name__}: no filter")
    logger, captured = _private_access_logger()

    served = _serve(protocol_class, _http_request(TARGET), access_logger=logger)

    assert served.sent.startswith(b"HTTP/1.1 200 "), "the request was not served"
    assert len(captured.records) == 1, f"one request, {len(captured.records)} access records"
    record = captured.records[0]
    # The record the filter is written for: uvicorn's message, the path with its query third, as the client sent it.
    assert (record.name, record.msg) == ("uvicorn.access", UVICORN_ACCESS_MESSAGE)
    assert record.args == (CLIENT, "GET", TARGET, "1.1", 200)
    assert captured.lines == [f'{CLIENT} - "GET {TARGET} HTTP/1.1" 200 OK'], "without the filter the line must show the value, or the masked line proves nothing"
    print_success("✓ uvicorn's record has the path third, and the plain line shows the value")


def test_a_real_access_line_shows_the_token_masked_and_the_rest_unchanged(protocol_class):
    print_section(f"Access log, {protocol_class.__name__}: filter installed")
    logger, captured = _private_access_logger(_QUERY_CREDENTIAL_FILTER)

    served = _serve(protocol_class, _http_request(TARGET), access_logger=logger)

    assert served.sent.startswith(b"HTTP/1.1 200 "), "the request was not served"
    assert captured.lines == [MASKED_LINE]
    print_success("✓ token=*** in the line, the rest of the request line unchanged")


# ── the real uvicorn loggers: the logging state, saved and put back ──────────


@dataclass(frozen=True)
class _LoggerState:
    """What ``configure_logging()`` and these tests can change on a logger."""

    level: int
    handlers: tuple[logging.Handler, ...]
    filters: tuple[Any, ...]
    propagate: bool
    disabled: bool

    @classmethod
    def of(cls, logger: logging.Logger) -> _LoggerState:
        return cls(logger.level, tuple(logger.handlers), tuple(logger.filters), logger.propagate, logger.disabled)

    def restore(self, logger: logging.Logger) -> None:
        logger.handlers[:] = self.handlers
        logger.filters[:] = self.filters
        logger.propagate, logger.disabled = self.propagate, self.disabled
        # setLevel, not an assignment: it also clears the cached answers of isEnabledFor.
        logger.setLevel(self.level)


#: A logger as ``logging.getLogger`` creates it.
_NEW_LOGGER = _LoggerState(logging.NOTSET, (), (), True, False)


def _every_logger() -> dict[str, logging.Logger]:
    """The root logger, under ``""``, and every logger registered by name."""
    registered = {name: logger for name, logger in logging.Logger.manager.loggerDict.items() if isinstance(logger, logging.Logger)}
    return {"": logging.getLogger(), **registered}


@contextlib.contextmanager
def _logging_state_restored() -> Iterator[None]:
    """Every logger and structlog's configuration put back, on the way out, as they were when the block began.

    ``configure_logging()`` replaces the root handlers, sets levels, adds filters and reconfigures structlog. Used in a
    test body, so the root handlers put back are the ones pytest attached for that very phase. A logger the block created
    goes back to the state of a new one; a handler the block left attached, and no logger held before, is closed.
    structlog gets back the same processor list, the one loggers cached with ``cache_logger_on_first_use`` hold.
    """
    before = {name: _LoggerState.of(logger) for name, logger in _every_logger().items()}
    held_before = {handler for state in before.values() for handler in state.handlers}
    structlog_configured, structlog_config = structlog.is_configured(), structlog.get_config()
    try:
        yield
    finally:
        left_attached = set()
        for name, logger in _every_logger().items():
            state = before.get(name, _NEW_LOGGER)
            left_attached.update(handler for handler in logger.handlers if handler not in held_before)
            state.restore(logger)
        for handler in left_attached:
            handler.close()
        if structlog_configured:
            structlog.configure(**structlog_config)
        else:
            structlog.reset_defaults()


@contextlib.contextmanager
def _uvicorn_error_captured(*filters: logging.Filter) -> Iterator[_CapturedLines]:
    """uvicorn's own ``uvicorn.error``, with exactly ``filters``, at INFO, writing to a capture only; put back on the way out."""
    with _logging_state_restored():
        error = logging.getLogger("uvicorn.error")
        error.filters[:] = filters
        captured = _error_lines()
        error.handlers[:] = [captured]
        error.propagate = False
        error.setLevel(logging.INFO)
        yield captured


def test_negative_control_without_the_filter_the_websocket_line_shows_the_value(protocol_class):
    print_section(f"WebSocket handshake, {protocol_class.__name__}: no filter on uvicorn.error")

    with _uvicorn_error_captured() as captured:
        served = _serve(protocol_class, _websocket_request(WS_TARGET))

    assert isinstance(served.protocol, AutoWebSocketsProtocol), f"the handshake went to {type(served.protocol).__name__}, not to the WebSocket protocol --ws auto picks"
    assert served.sent.startswith(b"HTTP/1.1 403 "), "the app's refusal did not reach the client"
    refused = [record for record in captured.records if record.msg == UVICORN_WEBSOCKET_REFUSED]
    # The record the filter is written for: the client, then the path with its query as the client sent it.
    assert [(record.name, record.args) for record in refused] == [("uvicorn.error", (CLIENT, WS_TARGET))]
    assert captured.lines_of(UVICORN_WEBSOCKET_REFUSED) == [f'{CLIENT} - "WebSocket {WS_TARGET}" 403'], "without the filter the line must show the value, or the masked line proves nothing"
    print_success("✓ uvicorn's handshake record has the path second, and the plain line shows the value")


def test_a_real_websocket_handshake_line_shows_the_token_masked_and_the_rest_unchanged(protocol_class):
    print_section(f"WebSocket handshake, {protocol_class.__name__}: filter on uvicorn.error")

    with _uvicorn_error_captured(_QUERY_CREDENTIAL_FILTER) as captured:
        served = _serve(protocol_class, _websocket_request(WS_TARGET))

    assert isinstance(served.protocol, AutoWebSocketsProtocol), f"the handshake went to {type(served.protocol).__name__}, not to the WebSocket protocol --ws auto picks"
    assert served.sent.startswith(b"HTTP/1.1 403 "), "the app's refusal did not reach the client"
    assert captured.lines_of(UVICORN_WEBSOCKET_REFUSED) == [WS_MASKED_LINE]
    showing = sum(PLACEHOLDER in line for line in captured.lines)
    assert showing == 0, f"{showing} of the {len(captured.lines)} uvicorn.error lines of the handshake show the value"
    print_success("✓ token=*** in the handshake line, nowhere in clear on uvicorn.error")


@pytest.mark.parametrize(
    ("message", "extra_args", "outcome"),
    [
        pytest.param('%s - "WebSocket %s" [accepted]', (), "[accepted]", id="accepted"),
        pytest.param(UVICORN_WEBSOCKET_REFUSED, (), "403", id="refused"),
        pytest.param('%s - "WebSocket %s" %d', (404,), "404", id="status-of-the-app"),
    ],
)
def test_each_websocket_handshake_message_of_uvicorn_is_masked(message, extra_args, outcome):
    source = inspect.getsource(inspect.getmodule(AutoWebSocketsProtocol))
    assert message in source, f"not a message of {AutoWebSocketsProtocol.__module__}: the record below is not one uvicorn logs"
    record = _record((CLIENT, WS_TARGET, *extra_args), msg=message, name="uvicorn.error")

    _QUERY_CREDENTIAL_FILTER.filter(record)

    assert record.getMessage() == f'{CLIENT} - "WebSocket {WS_MASKED_TARGET}" {outcome}'


# ── (d) configure_logging installs the filter once on each logger ────────────


def _credential_filters(logger: logging.Logger) -> list[logging.Filter]:
    """The credential filters on ``logger``, whichever instance they are."""
    return [log_filter for log_filter in logger.filters if isinstance(log_filter, _QueryCredentialFilter)]


def test_configure_logging_twice_installs_one_filter_on_each_logger_and_masks_uvicorns_own_lines():
    print_section("configure_logging() twice: one filter on uvicorn.access and on uvicorn.error")
    loggers = {name: logging.getLogger(name) for name in UVICORN_LOGGERS}
    filters_before = {name: copy.copy(logger.filters) for name, logger in loggers.items()}
    processors_before = structlog.get_config()["processors"]

    with _logging_state_restored():
        for logger in loggers.values():
            logger.removeFilter(_QUERY_CREDENTIAL_FILTER)
        assert not any(_credential_filters(logger) for logger in loggers.values()), "precondition: the two loggers must start without a credential filter, or the calls below prove nothing"

        configure_logging(enable_file_logging=False)
        configure_logging(enable_file_logging=False)

        for name, logger in loggers.items():
            installed = _credential_filters(logger)
            assert len(installed) == 1, f"two calls left {len(installed)} credential filters on {name}"
            assert installed[0] is _QUERY_CREDENTIAL_FILTER, f"the filter on {name} is not the module-level instance"

        # uvicorn picks both loggers itself: the lines prove the filter sits where uvicorn writes.
        captures = {"uvicorn.access": _access_lines(), "uvicorn.error": _error_lines()}
        for name, captured in captures.items():
            loggers[name].addHandler(captured)
            loggers[name].propagate = False
            loggers[name].setLevel(logging.INFO)
        http = _serve(AutoHTTPProtocol, _http_request(TARGET))
        websocket = _serve(AutoHTTPProtocol, _websocket_request(WS_TARGET))

        assert http.sent.startswith(b"HTTP/1.1 200 ") and websocket.sent.startswith(b"HTTP/1.1 403 "), "a request was not served"
        assert captures["uvicorn.access"].lines == [MASKED_LINE], "uvicorn's own uvicorn.access line was not masked after configure_logging()"
        assert captures["uvicorn.error"].lines_of(UVICORN_WEBSOCKET_REFUSED) == [WS_MASKED_LINE], "uvicorn's own uvicorn.error handshake line was not masked after configure_logging()"
        showing = sum(PLACEHOLDER in line for captured in captures.values() for line in captured.lines)
        assert showing == 0, f"{showing} uvicorn lines show the value after configure_logging()"

    for name, logger in loggers.items():
        assert logger.filters == filters_before[name], f"the test left {name} with other filters than it found"
    assert structlog.get_config()["processors"] is processors_before, "the test left structlog another processor list: loggers cached on the old one would no longer reach capture_logs"
    print_success("✓ One filter on each logger after two calls; uvicorn's own lines masked on both; logging state put back")


# ── (e) configure_logging closes the handlers it takes off the root ──────────


@pytest.fixture
def private_log_directory(tmp_path, monkeypatch) -> Path:
    """The folder ``configure_logging(enable_file_logging=True)`` opens its log file in, moved under ``tmp_path``.

    The file is ``get_log_directory() / "librefolio.log"``, and ``get_log_directory()`` is ``get_data_dir() / "logs"``:
    in test mode the data directory is ``LIBREFOLIO_TEST_DATA_DIR``, read at each call. The lane's ``logs/`` is shared by
    every unit of the lane and is never opened here; pytest removes ``tmp_path``.
    """
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    data_dir = get_data_dir()
    assert data_dir.is_relative_to(tmp_path.resolve()), f"the data directory must be this test's own, under {tmp_path}, not {data_dir}"
    return get_log_directory()


def _log_files(handlers: list[logging.Handler]) -> list[logging.FileHandler]:
    """The handlers among ``handlers`` that write to a file."""
    return [handler for handler in handlers if isinstance(handler, logging.FileHandler)]


def test_a_second_configure_logging_closes_the_handlers_of_the_first(private_log_directory):
    print_section("configure_logging() twice: the first call's log file closed, the second call's on the root and open")
    root = logging.getLogger()
    first: list[logging.Handler] = []
    try:
        with _logging_state_restored():
            # Only handlers configure_logging() installs: the block puts pytest's back, never closed by the calls below.
            root.handlers[:] = []
            configure_logging(enable_file_logging=True)
            first = list(root.handlers)
            first_files = _log_files(first)
            assert [Path(handler.baseFilename) for handler in first_files] == [private_log_directory / "librefolio.log"], f"precondition: the first call must open one log file, in {private_log_directory}: {first}"
            first_stream = first_files[0].stream
            assert first_stream is not None and not first_stream.closed, "precondition: the first call's log file must be open, or its closing proves nothing"

            configure_logging(enable_file_logging=True)
            second = list(root.handlers)

            assert first_stream.closed, "the first call's log file is still open after the second call: configure_logging() took its handler off the root without closing it"
            assert not set(first) & set(second), f"the second call must leave on the root handlers of its own, none of the first call's: {second}"
            second_files = _log_files(second)
            assert len(second_files) == 1 and second_files[0].stream is not None and not second_files[0].stream.closed, f"the second call's log file must be on the root and open: {second}"
    finally:
        for handler in first:
            handler.close()  # a no-op once configure_logging() closes them itself: today it leaves them open
    print_success("✓ The first call's log file closed by the second call; the second call's handlers on the root, open")


def test_configure_logging_closes_a_file_handler_it_finds_on_the_root(tmp_path):
    print_section("configure_logging(): a file handler found on the root is taken off and closed")
    own = logging.FileHandler(tmp_path / "own.log", encoding="utf-8")
    own_stream = own.stream
    try:
        with _logging_state_restored():
            root = logging.getLogger()
            # This handler alone: the block puts pytest's back, never closed by the call below.
            root.handlers[:] = [own]
            assert own_stream is not None and not own_stream.closed, "precondition: the handler's file must be open before the call, or its closing proves nothing"

            configure_logging(enable_file_logging=False)

            assert own not in root.handlers, f"configure_logging() must take every handler it finds off the root: {root.handlers}"
            assert own_stream.closed, "a file handler found on the root is still open after configure_logging(): taken off without being closed"
    finally:
        own.close()  # a no-op once configure_logging() closes it itself: today it leaves it open
    print_success("✓ The file handler found on the root taken off and closed")
