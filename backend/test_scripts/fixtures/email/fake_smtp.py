"""A fake SMTP server for the e-mail tests: standard library only, on 127.0.0.1, on a port the OS picks.

Python 3.13 has no ``smtpd`` and ``aiosmtpd`` declares support up to 3.12 (plan phase01Email, decision D-E2), so the
tests bring their own server. ``FakeSmtpServer`` speaks the part of SMTP that ``smtplib`` uses, records what reaches it
and can be told to refuse at each step, so that every error code of ``backend.app.services.email.smtp`` has a server
that provokes it:

- the greeting ``220``; ``EHLO`` answers on several lines and advertises ``AUTH PLAIN LOGIN``, then ``8BITMIME`` and
  ``SMTPUTF8`` unless ``smtputf8=False``, and, only when the server holds an ``ssl.SSLContext``, ``STARTTLS``; ``HELO``,
  ``RSET``, ``NOOP`` and ``QUIT``; ``502`` to anything else;
- ``AUTH PLAIN`` (initial response, or after a ``334``) and ``AUTH LOGIN`` (with or without the initial response): every
  attempt lands in ``auth_attempts`` as ``(user, password)``; with ``credentials`` a mismatch is ``535`` and ``MAIL``
  before a successful ``AUTH`` is ``530``;
- ``MAIL FROM``, ``RCPT TO`` and ``DATA`` (dot-unstuffing, end at ``<CRLF>.<CRLF>``): an accepted message lands in
  ``messages`` with its envelope — ``mail_options`` holding the parameters that followed the address on ``MAIL``, in the
  order received, whatever they are: none is refused —, its raw bytes and the ``EmailMessage`` parsed from them
  (``BytesParser(policy=email.policy.default)``, which reads every byte beyond ASCII as a surrogate escape: an
  internationalized address is read in ``rcpt_tos`` or in ``data``, not in ``message``);
- ``refuse_sender`` answers ``550`` to ``MAIL``; ``refuse_recipients`` ``550`` to ``RCPT`` for the addresses it holds,
  quoting the refused address as received, the way real servers do (Postfix:
  ``550 5.1.1 <alice@example.com>: Recipient address rejected: …``), so that the server's words carry the recipient's
  address as theirs do; ``refuse_data`` ``554`` once the data is in (the message is then not recorded); ``quit_code`` is
  the reply to ``QUIT`` (``221`` by default); ``greet=False`` accepts connections and never says a word;
- ``smtputf8`` (on by default): ``8BITMIME`` and ``SMTPUTF8`` (RFC 6531) in the ``EHLO`` answer, as Postfix advertises
  them, for the internationalized addresses: towards a server that does not advertise ``SMTPUTF8``, ``smtplib`` refuses
  an address beyond ASCII on its own side, before ``MAIL`` (``SMTPNotSupportedError``); towards one that does, it sends
  ``SMTPUTF8 BODY=8BITMIME`` on ``MAIL`` and the headers in UTF-8. It asks for the extension for such an address only,
  so an all-ASCII message goes out the same with the option or without — only the ``EHLO`` answer differs;
  ``smtputf8=False`` is the server without the extension;
- ``tls_context``: ``STARTTLS`` upgrades the session, which then starts over: ``EHLO`` again, nobody authenticated.

Use it as a context manager::

    with FakeSmtpServer(credentials=("mailer", "s3cret")) as fake:
        ...  # an SMTP client connects to fake.host, fake.port
    assert fake.messages[0].rcpt_tos == ["alice@example.com"]

Leaving the block stops it: the listening socket and every open connection are closed, every thread it started is
joined. A thread still alive after that, or a failure of the server's own code (anything but a network error), raises
``AssertionError`` there, unless the block is already leaving on an exception, which is never masked: a fake that fails
in silence would pass its own defects off as the implementation's. ``connections`` counts the connections accepted, so
that a test can prove that none was opened. The listener is bound without ``SO_REUSEADDR``: a port the OS picks never
needs it, and without it the fake can never be handed a port that ``closed_port()`` holds, on macOS either.

``closed_port()`` is a context manager yielding a port of 127.0.0.1 that refuses connections, held for the whole block
so that no listener can be handed it meanwhile — for the connection that must be refused::

    with closed_port() as port:
        ...  # a connection to 127.0.0.1:port is refused at once

The port belongs to a socket that never listens: bound, then connected to a private listener, which is closed as soon
as the pair is established. A connection to the port finds no listener and is refused at once, on Linux and on macOS
alike. A socket that is only bound would not do: Linux refuses a connection to it, but macOS, like the BSDs it comes
from, silently drops the SYN sent to a bound socket that never listened, so the client would wait for its timeout and
read ``TIMEOUT`` where the test expects a refusal. While the block runs, no ``bind`` without ``SO_REUSEADDR``, whether to
that port or to a port the OS picks, gets the port, on either system, and on Linux no ``bind`` at all does. On macOS a
``bind`` with ``SO_REUSEADDR`` still could, so that race is narrowed there, not closed. ``closed_port()`` proves its
port refuses a connection before yielding it, and leaving the block closes the holder abortively, without a
``TIME_WAIT``, so the port is free again at once.
"""

from __future__ import annotations

import base64
import binascii
import contextlib
import selectors
import socket
import ssl
import struct
import threading
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from types import TracebackType

__all__ = ["HOSTNAME", "FakeSmtpServer", "ReceivedMessage", "closed_port"]

#: The name the fake gives itself in its greeting and in its ``EHLO`` answer.
HOSTNAME = "fake-smtp.example.com"

#: The longest line read in one piece: far beyond any command ``smtplib`` sends, small enough to bound garbage.
_MAX_LINE = 64 * 1024

#: How long ``stop()`` waits for each of its threads, and the TLS handshake for its client: a bound, never a pause.
_JOIN_TIMEOUT_SECONDS = 10.0

#: What a command handler returns to end the session.
_CLOSE = object()

#: The ``334`` challenges of ``AUTH LOGIN``: ``Username:`` and ``Password:`` in base64.
_USERNAME_PROMPT = base64.b64encode(b"Username:").decode("ascii")
_PASSWORD_PROMPT = base64.b64encode(b"Password:").decode("ascii")

#: How long ``closed_port()`` lets its own refusal check take: refused at once, it never waits; a platform that dropped
#: the connection instead would fail the check after this bound, never pass it.
_REFUSAL_TIMEOUT_SECONDS = 2.0

#: ``SO_LINGER`` on, zero seconds: ``close()`` resets the connection, so the port is released at once, with no ``TIME_WAIT``.
_ABORT_ON_CLOSE = struct.pack("ii", 1, 0)


@dataclass(frozen=True)
class ReceivedMessage:
    """A message the fake accepted: its envelope, its raw bytes as received (dot-unstuffed) and their parsing."""

    mail_from: str
    #: The parameters that followed the address on ``MAIL``, in the order received: ``("SMTPUTF8", "BODY=8BITMIME")``
    #: for a message ``smtplib`` sent with the extension, ``()`` for an all-ASCII envelope.
    mail_options: tuple[str, ...]
    rcpt_tos: list[str]
    data: bytes
    message: EmailMessage
    #: The user who authenticated in the session that sent it, ``None`` without ``AUTH``.
    user: str | None
    #: Whether the session had been upgraded by ``STARTTLS`` when the message arrived.
    tls: bool


@contextlib.contextmanager
def closed_port(host: str = "127.0.0.1") -> Iterator[int]:
    """A TCP port of ``host`` (IPv4) that refuses connections, held until the block is left: see the module docstring."""
    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    peer: socket.socket | None = None
    try:
        with socket.create_server((host, 0)) as anchor:
            # Bound by bind(), not by connect(): Linux then never picks the port as the source of an outgoing
            # connection, which to this very port would connect to itself (a TCP self-connect) instead of being refused.
            holder.bind((host, 0))
            holder.connect(anchor.getsockname())
            peer, _ = anchor.accept()
        port = holder.getsockname()[1]
        _check_refused(host, port)
        yield port
    finally:
        with contextlib.suppress(OSError):
            holder.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, _ABORT_ON_CLOSE)
        holder.close()
        if peer is not None:
            peer.close()


def _check_refused(host: str, port: int) -> None:
    """The premise of ``closed_port()``, proven: a connection to ``port`` is refused — neither accepted nor left waiting."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(_REFUSAL_TIMEOUT_SECONDS)
        try:
            client.connect((host, port))
        except ConnectionRefusedError:
            return
        except OSError as exc:
            raise AssertionError(f"closed_port: a connection to {host}:{port} was not refused: {exc!r}") from exc
    raise AssertionError(f"closed_port: a connection to {host}:{port} was accepted: something listens on the port it holds")


def _listening_socket(host: str) -> socket.socket:
    """A listener on a port of ``host`` the OS picks, without ``SO_REUSEADDR`` (unlike ``socket.create_server``): see the module docstring."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind((host, 0))
        listener.listen()
    except OSError:
        listener.close()
        raise
    return listener


class FakeSmtpServer:
    """A threaded SMTP server on 127.0.0.1 for one test: one thread accepts, one thread per connection talks."""

    def __init__(
        self,
        *,
        credentials: tuple[str, str] | None = None,
        refuse_sender: bool = False,
        refuse_recipients: Iterable[str] = (),
        refuse_data: bool = False,
        quit_code: int = 221,
        greet: bool = True,
        tls_context: ssl.SSLContext | None = None,
        smtputf8: bool = True,
    ) -> None:
        self.credentials = credentials
        self.refuse_sender = refuse_sender
        self.refuse_recipients = frozenset(refuse_recipients)
        self.refuse_data = refuse_data
        self.quit_code = quit_code
        self.greet = greet
        self.tls_context = tls_context
        self.smtputf8 = smtputf8
        self.host = "127.0.0.1"
        self.port = 0
        self.messages: list[ReceivedMessage] = []
        self.auth_attempts: list[tuple[str, str]] = []
        self.connections = 0
        #: Every exception that ended a session. Network errors (``OSError``, ``ssl.SSLError`` included) are expected
        #: when a client gives up; anything else is a defect of the fake and fails the test when the server stops.
        self.errors: list[BaseException] = []
        self._lock = threading.Lock()
        self._listener: socket.socket | None = None
        self._wake_reader: socket.socket | None = None
        self._wake_writer: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._session_threads: list[threading.Thread] = []
        self._open_sockets: set[socket.socket] = set()
        self._stopping = False

    # ------------------------------------------------------------------ lifecycle

    def __enter__(self) -> FakeSmtpServer:
        return self.start()

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None) -> None:
        self.stop(check=exc_type is None)

    def start(self) -> FakeSmtpServer:
        """Listen on a port of 127.0.0.1 the OS picks, and accept connections on a thread of the fake's own."""
        if self._listener is not None or self._stopping:
            raise RuntimeError("a FakeSmtpServer runs once: this one is running or has been stopped")
        self._listener = _listening_socket(self.host)
        self.port = self._listener.getsockname()[1]
        self._wake_reader, self._wake_writer = socket.socketpair()
        self._accept_thread = threading.Thread(target=self._accept_loop, name=f"fake-smtp-{self.port}-accept", daemon=True)
        self._accept_thread.start()
        return self

    def stop(self, *, check: bool = True) -> None:
        """Close every connection and the listening socket, join every thread; with ``check``, fail on a leak or a defect."""
        if self._listener is None or self._accept_thread is None:
            return
        threads = self._close_everything()
        if check:
            self._check_stopped(threads)

    def _close_everything(self) -> list[threading.Thread]:
        with self._lock:
            self._stopping = True
            for open_socket in self._open_sockets:
                with contextlib.suppress(OSError):
                    open_socket.shutdown(socket.SHUT_RDWR)
            threads = [self._accept_thread, *self._session_threads]
        with contextlib.suppress(OSError):
            self._wake_writer.send(b"\0")
        for thread in threads:
            thread.join(_JOIN_TIMEOUT_SECONDS)
        for own_socket in (self._listener, self._wake_reader, self._wake_writer):
            with contextlib.suppress(OSError):
                own_socket.close()
        self._listener = None
        return threads

    def _check_stopped(self, threads: list[threading.Thread]) -> None:
        alive = [thread.name for thread in threads if thread.is_alive()]
        if alive:
            raise AssertionError(f"FakeSmtpServer on port {self.port}: threads still running after stop: {alive}")
        defects = [error for error in self.errors if not isinstance(error, OSError)]
        if defects:
            raise AssertionError(f"FakeSmtpServer on port {self.port} failed in its own code: {defects!r}") from defects[0]

    # ------------------------------------------------------------------ threads

    def _accept_loop(self) -> None:
        with selectors.DefaultSelector() as selector:
            selector.register(self._listener, selectors.EVENT_READ)
            selector.register(self._wake_reader, selectors.EVENT_READ)
            while True:
                ready = {key.fileobj for key, _ in selector.select()}
                if self._wake_reader in ready:
                    return
                try:
                    connection, _ = self._listener.accept()
                except OSError as exc:
                    self._record(self.errors, exc)
                    continue
                self._start_session(connection)

    def _start_session(self, connection: socket.socket) -> None:
        with self._lock:
            if self._stopping:
                connection.close()
                return
            self.connections += 1
            self._open_sockets.add(connection)
            thread = threading.Thread(target=self._run_session, args=(connection,), name=f"fake-smtp-{self.port}-session-{self.connections}", daemon=True)
            self._session_threads.append(thread)
            thread.start()

    def _run_session(self, connection: socket.socket) -> None:
        session = _Session(self, connection)
        try:
            session.run()
        except Exception as exc:  # any error ends the session; stop() tells network errors from defects of the fake
            self._record(self.errors, exc)
        finally:
            session.close()

    # ------------------------------------------------------------------ shared state, under the lock

    def _record(self, sink: list, item: object) -> None:
        with self._lock:
            sink.append(item)

    def _replace_socket(self, old: socket.socket, new: socket.socket) -> None:
        with self._lock:
            self._open_sockets.discard(old)
            self._open_sockets.add(new)
            if self._stopping:
                with contextlib.suppress(OSError):
                    new.shutdown(socket.SHUT_RDWR)

    def _close_socket(self, own_socket: socket.socket) -> None:
        with self._lock:
            self._open_sockets.discard(own_socket)
            with contextlib.suppress(OSError):
                own_socket.close()


def _decode_base64(text: str) -> str | None:
    """The UTF-8 text a base64 SASL response holds, ``None`` when it is not valid base64 or not UTF-8."""
    try:
        return base64.b64decode(text.encode("ascii"), validate=True).decode("utf-8")
    except (UnicodeError, binascii.Error, ValueError):
        return None


def _reverse_path(argument: str, keyword: str) -> tuple[str, tuple[str, ...]] | None:
    """The address of ``FROM:<address> [parameters]`` or ``TO:<address> [parameters]`` and the parameters after it, in the order received: ``None`` when the keyword or the address is missing."""
    if argument[: len(keyword)].upper() != keyword:
        return None
    rest = argument[len(keyword) :].strip()
    if rest.startswith("<"):
        end = rest.find(">")
        return None if end < 0 else (rest[1:end], tuple(rest[end + 1 :].split()))
    words = rest.split()
    return (words[0], tuple(words[1:])) if words else None


class _Session:
    """One SMTP conversation, on the thread the server started for its connection."""

    def __init__(self, server: FakeSmtpServer, connection: socket.socket) -> None:
        self.server = server
        self.sock: socket.socket = connection
        self.reader = connection.makefile("rb")
        self.tls = False
        self.greeted = False
        self.user: str | None = None
        self.mail_from: str | None = None
        self.mail_options: tuple[str, ...] = ()
        self.rcpt_tos: list[str] = []
        self.commands: dict[str, Callable[[str], object]] = {
            "EHLO": self.ehlo,
            "HELO": self.helo,
            "STARTTLS": self.starttls,
            "AUTH": self.auth,
            "MAIL": self.mail,
            "RCPT": self.rcpt,
            "DATA": self.data,
            "RSET": self.rset,
            "NOOP": self.noop,
            "QUIT": self.quit,
        }

    # ------------------------------------------------------------------ wire

    def reply(self, line: str) -> None:
        self.sock.sendall(line.encode("utf-8") + b"\r\n")

    def read_line(self) -> str | None:
        raw = self.reader.readline(_MAX_LINE)
        if not raw:
            return None
        return raw.rstrip(b"\r\n").decode("utf-8", errors="replace")

    def challenge(self, text: str) -> str | None:
        """Send a ``334`` challenge and read the client's answer, ``None`` if it hung up."""
        self.reply(f"334 {text}")
        answer = self.read_line()
        return None if answer is None else answer.strip()

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self.reader.close()
        self.server._close_socket(self.sock)

    # ------------------------------------------------------------------ conversation

    def run(self) -> None:
        if not self.server.greet:
            # Accepted, never greeted: wait in silence until the client gives up and hangs up, or the server stops.
            while self.sock.recv(4096):
                pass
            return
        self.reply(f"220 {HOSTNAME} ESMTP LibreFolio fake server")
        while True:
            line = self.read_line()
            if line is None:
                return
            verb, _, argument = line.partition(" ")
            command = self.commands.get(verb.upper())
            if command is None:
                self.reply("502 5.5.2 Command not recognized")
            elif command(argument.strip()) is _CLOSE:
                return

    def reset_transaction(self) -> None:
        self.mail_from = None
        self.mail_options = ()
        self.rcpt_tos = []

    def ehlo(self, argument: str) -> None:
        if not argument:
            self.reply("501 5.5.4 EHLO needs a domain")
            return
        self.greeted = True
        self.reset_transaction()
        lines = [HOSTNAME, "AUTH PLAIN LOGIN"]
        if self.server.smtputf8:
            lines += ["8BITMIME", "SMTPUTF8"]
        if self.server.tls_context is not None and not self.tls:
            lines.append("STARTTLS")
        for line in lines[:-1]:
            self.reply(f"250-{line}")
        self.reply(f"250 {lines[-1]}")

    def helo(self, argument: str) -> None:
        if not argument:
            self.reply("501 5.5.4 HELO needs a domain")
            return
        self.greeted = True
        self.reset_transaction()
        self.reply(f"250 {HOSTNAME}")

    def starttls(self, argument: str) -> object:
        if self.server.tls_context is None or self.tls:
            self.reply("502 5.5.1 STARTTLS not offered")
            return None
        if argument:
            self.reply("501 5.5.4 STARTTLS takes no argument")
            return None
        self.reply("220 2.0.0 Ready to start TLS")
        self.reader.close()
        plain = self.sock
        plain.settimeout(_JOIN_TIMEOUT_SECONDS)
        try:
            upgraded = self.server.tls_context.wrap_socket(plain, server_side=True)
        except OSError as exc:  # the handshake failed: the client did not trust the certificate, or gave up
            self.server._record(self.server.errors, exc)
            return _CLOSE
        upgraded.settimeout(None)
        self.server._replace_socket(plain, upgraded)
        self.sock = upgraded
        self.reader = upgraded.makefile("rb")
        self.tls = True
        self.greeted = False
        self.user = None
        self.reset_transaction()
        return None

    def auth(self, argument: str) -> object:
        if not self.greeted or self.user is not None or self.mail_from is not None:
            self.reply("503 5.5.1 AUTH only after EHLO, once, outside a mail transaction")
            return None
        mechanism, _, initial = argument.partition(" ")
        read_credentials = {"PLAIN": self.sasl_plain, "LOGIN": self.sasl_login}.get(mechanism.upper())
        if read_credentials is None:
            self.reply("504 5.5.4 Unrecognized authentication type")
            return None
        outcome = read_credentials(initial.strip())
        if outcome is _CLOSE:
            return _CLOSE
        if isinstance(outcome, str):
            self.reply(outcome)
            return None
        user, password = outcome
        self.server._record(self.server.auth_attempts, (user, password))
        if self.server.credentials is not None and (user, password) != tuple(self.server.credentials):
            self.reply("535 5.7.8 Authentication credentials invalid")
            return None
        self.user = user
        self.reply("235 2.7.0 Authentication successful")
        return None

    def sasl_plain(self, initial: str) -> object:
        """``(user, password)`` from an ``AUTH PLAIN`` response, the error reply when it cannot be read, or ``_CLOSE``."""
        response = initial or self.challenge("")
        if response is None:
            return _CLOSE
        if response == "*":
            return "501 5.0.0 AUTH cancelled"
        decoded = _decode_base64(response)
        parts = decoded.split("\0") if decoded is not None else []
        if len(parts) != 3:
            return "501 5.5.2 Cannot decode the AUTH PLAIN response"
        return parts[1], parts[2]

    def sasl_login(self, initial: str) -> object:
        """``(user, password)`` from the two answers of ``AUTH LOGIN``, the error reply when one cannot be read, or ``_CLOSE``."""
        answer = initial or self.challenge(_USERNAME_PROMPT)
        if answer is None:
            return _CLOSE
        user = _decode_base64(answer)
        if user is None:
            return "501 5.5.2 Cannot decode the AUTH LOGIN user"
        answer = self.challenge(_PASSWORD_PROMPT)
        if answer is None:
            return _CLOSE
        password = _decode_base64(answer)
        if password is None:
            return "501 5.5.2 Cannot decode the AUTH LOGIN password"
        return user, password

    def mail(self, argument: str) -> None:
        if not self.greeted:
            self.reply("503 5.5.1 Send EHLO first")
            return
        path = _reverse_path(argument, "FROM:")
        if path is None:
            self.reply("501 5.5.4 Syntax: MAIL FROM:<address>")
            return
        if self.server.credentials is not None and self.user is None:
            self.reply("530 5.7.0 Authentication required")
            return
        if self.mail_from is not None:
            self.reply("503 5.5.1 Nested MAIL command")
            return
        if self.server.refuse_sender:
            self.reply("550 5.7.1 Sender refused by the fake server")
            return
        self.mail_from, self.mail_options = path
        self.reply("250 2.1.0 Sender OK")

    def rcpt(self, argument: str) -> None:
        if self.mail_from is None:
            self.reply("503 5.5.1 Need MAIL before RCPT")
            return
        address, _ = _reverse_path(argument, "TO:") or ("", ())
        if not address:
            self.reply("501 5.5.4 Syntax: RCPT TO:<address>")
            return
        if address in self.server.refuse_recipients:
            self.reply(f"550 5.1.1 <{address}>: Recipient address rejected: refused by the fake server")
            return
        self.rcpt_tos.append(address)
        self.reply("250 2.1.5 Recipient OK")

    def data(self, argument: str) -> object:
        if self.mail_from is None or not self.rcpt_tos:
            self.reply("503 5.5.1 Need RCPT before DATA")
            return None
        self.reply("354 End data with <CR><LF>.<CR><LF>")
        lines: list[bytes] = []
        while True:
            raw = self.reader.readline(_MAX_LINE)
            if not raw:
                return _CLOSE  # the client hung up in the middle of the message: nothing is recorded
            if raw in (b".\r\n", b".\n"):
                break
            lines.append(raw[1:] if raw.startswith(b".") else raw)
        data = b"".join(lines)
        if self.server.refuse_data:
            self.reset_transaction()
            self.reply("554 5.6.0 Message refused by the fake server")
            return None
        received = ReceivedMessage(
            mail_from=self.mail_from,
            mail_options=self.mail_options,
            rcpt_tos=list(self.rcpt_tos),
            data=data,
            message=BytesParser(policy=policy.default).parsebytes(data),
            user=self.user,
            tls=self.tls,
        )
        self.server._record(self.server.messages, received)
        self.reset_transaction()
        self.reply("250 2.0.0 Message accepted")
        return None

    def rset(self, argument: str) -> None:
        self.reset_transaction()
        self.reply("250 2.0.0 OK")

    def noop(self, argument: str) -> None:
        self.reply("250 2.0.0 OK")

    def quit(self, argument: str) -> object:
        self.reply(f"{self.server.quit_code} 2.0.0 Closing connection")
        return _CLOSE
