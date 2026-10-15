"""``backend.app.config.email``: the SMTP configuration of release 1.3, read from ``LIBREFOLIO_SMTP_*`` (plan phase01Email §3.1, lot E1).

E-mail is optional: without ``LIBREFOLIO_SMTP_HOST`` an instance behaves as it always has. The configuration lives in
variables or files only — never the database, the interface or a backup (F04) — and the section's accessors read the
process environment at every call. The contract pinned here:

1. The vocabulary: ``SMTP_ENV_PREFIX``; ``TLS_MODES`` ``starttls``, ``tls``, ``none``; ``DEFAULT_SMTP_PORTS`` 587, 465,
   25; ``DEFAULT_SMTP_MAX_PER_HOUR`` 50. ``EmailConfigError`` is a ``ValueError``.
2. Blank is unset: an empty or blank variable is the variable not set, and every value is stripped.
3. ``smtp_host``: letters, digits, ``.``, ``-``, ``_`` and ``:`` only, and never ``name:port``: one colon is a port,
   which has a variable of its own, while an IPv6 address has two or more. A URL, a space, an ``@`` or a ``name:port``
   is ``SMTP_HOST_INVALID``, never a guess at what was meant.
4. ``smtp_tls_mode``: ``starttls`` by default, case-insensitive, one of the three modes; ``ssl``, ``true`` or ``yes`` is
   ``SMTP_TLS_INVALID``.
5. ``smtp_port``: the mode's port by default; otherwise ASCII digits only, 1 to 65535, else ``SMTP_PORT_INVALID``.
6. ``smtp_user`` is stripped; ``smtp_password`` is exactly ``env_secret("LIBREFOLIO_SMTP_PASSWORD")``: the value as
   written, spaces kept, else the file named by ``LIBREFOLIO_SMTP_PASSWORD_FILE``, else ``None``; a file that cannot
   give it raises ``SecretFileError``.
7. ``smtp_sender`` and ``smtp_reply_to``: one mailbox, as ``(display name, address)``. Two addresses, no ``@``, an empty
   local or domain part, whitespace inside the address, or a CR or LF anywhere in the raw value is
   ``SMTP_FROM_INVALID`` / ``SMTP_REPLY_TO_INVALID``: a header injection never reaches a message.
8. ``smtp_max_per_hour``: 50 by default; ASCII digits, at least 1, else ``SMTP_MAX_PER_HOUR_INVALID``.
9. ``EmailConfigError`` carries ``variable`` and ``code``; its message names the variable and never holds the SMTP
   password, set in the same environment.
10. Every accessor reads the environment at each call: a change is seen at once, nothing is cached.

Pure: no database, no server, no network. An autouse fixture removes every ``LIBREFOLIO_SMTP_*`` the lane may have
inherited (until C-96 lands a lane carries the developer's ``.env``); each test sets only what it needs, with
``monkeypatch``; password files live in ``tmp_path``.

Red until ``backend/app/config/email.py`` exists: the module does not import.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import pytest

from backend.app.config import SecretFileError, env_secret
from backend.app.config.email import (
    DEFAULT_SMTP_MAX_PER_HOUR,
    DEFAULT_SMTP_PORTS,
    SMTP_ENV_PREFIX,
    TLS_MODES,
    EmailConfigError,
    smtp_host,
    smtp_max_per_hour,
    smtp_password,
    smtp_port,
    smtp_reply_to,
    smtp_sender,
    smtp_tls_mode,
    smtp_user,
)
from backend.test_scripts.test_utils import print_section, print_success

#: Written out, not imported: the fixture that empties the environment must not trust the module under test.
SMTP_PREFIX = "LIBREFOLIO_SMTP_"
HOST = "LIBREFOLIO_SMTP_HOST"
TLS = "LIBREFOLIO_SMTP_TLS"
PORT = "LIBREFOLIO_SMTP_PORT"
USER = "LIBREFOLIO_SMTP_USER"
PASSWORD = "LIBREFOLIO_SMTP_PASSWORD"
PASSWORD_FILE = "LIBREFOLIO_SMTP_PASSWORD_FILE"
FROM = "LIBREFOLIO_SMTP_FROM"
REPLY_TO = "LIBREFOLIO_SMTP_REPLY_TO"
MAX_PER_HOUR = "LIBREFOLIO_SMTP_MAX_PER_HOUR"

#: Recognisable password: a message that holds it would show it.
CANARY_PASSWORD = "c4nary-SMTP-p4ss-must-never-reach-a-message"

#: ``None`` stands for the variable not set at all.
BLANK_VALUES = [pytest.param(None, id="unset"), pytest.param("", id="empty"), pytest.param("   ", id="spaces"), pytest.param("\t", id="tab")]

#: The two mailbox variables share their rules, each with its own accessor and code.
MAILBOX_VARIABLES = [
    pytest.param(FROM, smtp_sender, "SMTP_FROM_INVALID", id="from"),
    pytest.param(REPLY_TO, smtp_reply_to, "SMTP_REPLY_TO_INVALID", id="reply-to"),
]


@pytest.fixture(autouse=True)
def _no_inherited_smtp_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*`` the lane inherited is removed: a test sees only the variables it sets itself."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX):
            monkeypatch.delenv(name, raising=False)


def _set(monkeypatch: pytest.MonkeyPatch, variable: str, value: str | None) -> None:
    """Set ``variable`` to ``value``, or leave it unset for ``None``."""
    if value is None:
        monkeypatch.delenv(variable, raising=False)
    else:
        monkeypatch.setenv(variable, value)


def _config_error(accessor: Callable[[], object]) -> EmailConfigError:
    """The ``EmailConfigError`` ``accessor`` raises; failing if it returns, or raises anything else."""
    with pytest.raises(EmailConfigError) as caught:
        result = accessor()
        pytest.fail(f"{accessor.__name__}() returned {result!r} instead of raising EmailConfigError")
    return caught.value


# =============================================================================
# 1. THE VOCABULARY
# =============================================================================


def test_the_constants_have_their_values() -> None:
    """EMC-001 — contract 1: the prefix, the three TLS modes in order, their default ports and the default hourly limit."""
    print_section("EMC-001: constants")

    assert SMTP_ENV_PREFIX == SMTP_PREFIX
    assert TLS_MODES == ("starttls", "tls", "none")
    assert DEFAULT_SMTP_PORTS == {"starttls": 587, "tls": 465, "none": 25}
    assert DEFAULT_SMTP_MAX_PER_HOUR == 50
    print_success("prefix, modes, ports 587/465/25, 50 per hour")


def test_email_config_error_is_a_value_error() -> None:
    """EMC-002 — contract 1: a configuration value that cannot be used is a ``ValueError``, like any bad value."""
    print_section("EMC-002: EmailConfigError")

    assert issubclass(EmailConfigError, ValueError)
    print_success("EmailConfigError ⊂ ValueError")


# =============================================================================
# 2. BLANK IS UNSET
# =============================================================================


@pytest.mark.parametrize("value", BLANK_VALUES)
@pytest.mark.parametrize(
    ("variable", "accessor", "unset_result"),
    [
        pytest.param(HOST, smtp_host, None, id="host"),
        pytest.param(TLS, smtp_tls_mode, "starttls", id="tls"),
        pytest.param(PORT, smtp_port, 587, id="port"),
        pytest.param(USER, smtp_user, None, id="user"),
        pytest.param(PASSWORD, smtp_password, None, id="password"),
        pytest.param(FROM, smtp_sender, None, id="from"),
        pytest.param(REPLY_TO, smtp_reply_to, None, id="reply-to"),
        pytest.param(MAX_PER_HOUR, smtp_max_per_hour, 50, id="max-per-hour"),
    ],
)
def test_a_blank_variable_is_an_unset_one(monkeypatch: pytest.MonkeyPatch, variable: str, accessor: Callable[[], object], unset_result: object, value: str | None) -> None:
    """EMC-003 — contract 2: unset, empty or blank, each accessor gives its default — ``None``, ``starttls``, 587 (the port of ``starttls``) or 50 — and never an error."""
    print_section(f"EMC-003: {variable} = {value!r}")
    _set(monkeypatch, variable, value)

    assert accessor() == unset_result
    print_success(f"{accessor.__name__}() → {unset_result!r}")


# =============================================================================
# 3. HOST
# =============================================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("smtp.example.com", "smtp.example.com"),
        ("  smtp.example.com  ", "smtp.example.com"),
        ("127.0.0.1", "127.0.0.1"),
        ("::1", "::1"),
        ("fe80::1", "fe80::1"),
        ("2001:db8::25", "2001:db8::25"),
        ("mail-relay", "mail-relay"),
        ("mail_relay", "mail_relay"),
    ],
)
def test_smtp_host_accepts_a_host_name_or_an_address(monkeypatch: pytest.MonkeyPatch, value: str, expected: str) -> None:
    """EMC-004 — contract 3: a name or an address made of letters, digits, ``.``, ``-``, ``_`` and ``:``, stripped; an IPv6 address, with its two colons or more, included."""
    print_section(f"EMC-004: host {value!r}")
    monkeypatch.setenv(HOST, value)

    assert smtp_host() == expected
    print_success(f"→ {expected!r}")


@pytest.mark.parametrize("value", ["smtp://x", "a b", "user@host", "mail.example.com/relay", "smtp.exa\tmple.com", "smtp.example.com:587", "127.0.0.1:25"])
def test_smtp_host_refuses_anything_but_a_host(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """EMC-005 — contract 3: a URL, whitespace inside, an ``@``, a path or a ``name:port`` — exactly one colon: the port has ``LIBREFOLIO_SMTP_PORT`` — is ``SMTP_HOST_INVALID`` on ``LIBREFOLIO_SMTP_HOST``."""
    print_section(f"EMC-005: host {value!r}")
    monkeypatch.setenv(HOST, value)

    error = _config_error(smtp_host)

    assert (error.variable, error.code) == (HOST, "SMTP_HOST_INVALID")
    print_success("SMTP_HOST_INVALID")


# =============================================================================
# 4. TLS MODE
# =============================================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [("starttls", "starttls"), ("STARTTLS", "starttls"), (" tls ", "tls"), ("TLS", "tls"), ("none", "none"), ("None", "none")],
)
def test_smtp_tls_mode_is_one_of_three_whatever_the_case(monkeypatch: pytest.MonkeyPatch, value: str, expected: str) -> None:
    """EMC-006 — contract 4: stripped and lowercased, the value is one of ``TLS_MODES``."""
    print_section(f"EMC-006: tls {value!r}")
    monkeypatch.setenv(TLS, value)

    assert smtp_tls_mode() == expected
    print_success(f"→ {expected!r}")


@pytest.mark.parametrize("value", ["ssl", "true", "yes", "off", "start tls"])
def test_smtp_tls_mode_refuses_any_other_word(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """EMC-007 — contract 4: ``ssl``, ``true``, ``yes``… are ``SMTP_TLS_INVALID``: a mode is never guessed, least of all a weaker one."""
    print_section(f"EMC-007: tls {value!r}")
    monkeypatch.setenv(TLS, value)

    error = _config_error(smtp_tls_mode)

    assert (error.variable, error.code) == (TLS, "SMTP_TLS_INVALID")
    print_success("SMTP_TLS_INVALID")


# =============================================================================
# 5. PORT
# =============================================================================


@pytest.mark.parametrize(("tls", "expected"), [(None, 587), ("starttls", 587), ("tls", 465), ("none", 25), ("NONE", 25)])
def test_smtp_port_defaults_to_the_port_of_the_mode(monkeypatch: pytest.MonkeyPatch, tls: str | None, expected: int) -> None:
    """EMC-008 — contract 5: without a port, the mode's: 587 for ``starttls`` (the default mode), 465 for ``tls``, 25 for ``none``."""
    print_section(f"EMC-008: port for tls {tls!r}")
    _set(monkeypatch, TLS, tls)

    assert smtp_port() == expected
    print_success(f"→ {expected}")


@pytest.mark.parametrize(("value", "expected"), [("2525", 2525), (" 2525 ", 2525), ("1", 1), ("65535", 65535)])
def test_smtp_port_reads_ascii_digits_from_1_to_65535(monkeypatch: pytest.MonkeyPatch, value: str, expected: int) -> None:
    """EMC-009 — contract 5: a port in ASCII digits, stripped, at both ends of the range."""
    print_section(f"EMC-009: port {value!r}")
    monkeypatch.setenv(PORT, value)

    assert smtp_port() == expected
    print_success(f"→ {expected}")


@pytest.mark.parametrize("value", ["0", "65536", "-1", "+25", "25.0", "abc", "25 25", "2_525", "\uff12\uff15", "99999999999999999999"])
def test_smtp_port_refuses_anything_else(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """EMC-010 — contract 5: out of range, signed, decimal, words — and what ``int()`` would take but is not ASCII digits: ``2_525``, fullwidth ``２５`` — are ``SMTP_PORT_INVALID``."""
    print_section(f"EMC-010: port {value!r}")
    monkeypatch.setenv(PORT, value)

    error = _config_error(smtp_port)

    assert (error.variable, error.code) == (PORT, "SMTP_PORT_INVALID")
    print_success("SMTP_PORT_INVALID")


# =============================================================================
# 6. USER AND PASSWORD
# =============================================================================


@pytest.mark.parametrize(("value", "expected"), [("mailer", "mailer"), ("  mailer  ", "mailer"), ("mailer@example.com", "mailer@example.com")])
def test_smtp_user_is_stripped(monkeypatch: pytest.MonkeyPatch, value: str, expected: str) -> None:
    """EMC-011 — contract 6: the user as written, without the spaces around it; an address is a user like any other."""
    print_section(f"EMC-011: user {value!r}")
    monkeypatch.setenv(USER, value)

    assert smtp_user() == expected
    print_success(f"→ {expected!r}")


@pytest.mark.parametrize(
    ("direct", "file_content", "expected"),
    [
        pytest.param("  s3cret with spaces  ", None, "  s3cret with spaces  ", id="direct-spaces-kept"),
        pytest.param(None, "file-s3cret\n", "file-s3cret", id="file"),
        pytest.param("direct-s3cret", "file-s3cret\n", "direct-s3cret", id="direct-wins-over-file"),
        pytest.param("   ", "file-s3cret\n", "file-s3cret", id="blank-direct-falls-through"),
        pytest.param(None, None, None, id="none"),
    ],
)
def test_smtp_password_is_env_secret(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, direct: str | None, file_content: str | None, expected: str | None) -> None:
    """EMC-012 — contract 6: ``LIBREFOLIO_SMTP_PASSWORD`` as written, spaces kept, wins; else the file of ``_FILE`` without its trailing line break; else ``None`` — exactly what ``env_secret`` says."""
    print_section("EMC-012: smtp_password = env_secret")
    _set(monkeypatch, PASSWORD, direct)
    if file_content is not None:
        secret_file = tmp_path / "smtp_password"
        secret_file.write_text(file_content, encoding="utf-8")
        monkeypatch.setenv(PASSWORD_FILE, str(secret_file))

    assert smtp_password() == expected
    assert smtp_password() == env_secret(PASSWORD)
    print_success(f"→ {'None' if expected is None else 'the expected secret'}")


@pytest.mark.parametrize("problem", ["missing", "empty"])
def test_smtp_password_raises_on_a_file_that_cannot_give_it(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, problem: str) -> None:
    """EMC-013 — contract 6: a ``_FILE`` that is missing or empty raises ``SecretFileError``, as ``env_secret`` does — never a silent ``None``."""
    print_section(f"EMC-013: password file {problem}")
    secret_file = tmp_path / "smtp_password"
    if problem == "empty":
        secret_file.write_text("", encoding="utf-8")
    monkeypatch.setenv(PASSWORD_FILE, str(secret_file))

    with pytest.raises(SecretFileError):
        smtp_password()
    print_success("SecretFileError")


# =============================================================================
# 7. SENDER AND REPLY-TO
# =============================================================================


@pytest.mark.parametrize(("variable", "accessor", "code"), MAILBOX_VARIABLES)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("LibreFolio <noreply@example.com>", ("LibreFolio", "noreply@example.com"), id="name-and-address"),
        pytest.param("noreply@example.com", ("", "noreply@example.com"), id="address-only"),
        pytest.param("  LibreFolio <noreply@example.com>  ", ("LibreFolio", "noreply@example.com"), id="stripped"),
        pytest.param("Libre Folìo <noreply@example.com>", ("Libre Folìo", "noreply@example.com"), id="non-ascii-name"),
        pytest.param('"Folio, Family" <noreply@example.com>', ("Folio, Family", "noreply@example.com"), id="quoted-name-with-comma"),
    ],
)
def test_a_mailbox_variable_gives_its_display_name_and_address(monkeypatch: pytest.MonkeyPatch, variable: str, accessor: Callable[[], object], code: str, value: str, expected: tuple[str, str]) -> None:
    """EMC-014 — contract 7: ``Name <address>`` or ``address`` is one mailbox, ``(display name, address)``; a comma inside a quoted name is part of the name, not a second address."""
    print_section(f"EMC-014: {variable} = {value!r}")
    monkeypatch.setenv(variable, value)

    assert accessor() == expected
    print_success(f"→ {expected!r}")


@pytest.mark.parametrize(("variable", "accessor", "code"), MAILBOX_VARIABLES)
@pytest.mark.parametrize(
    "value",
    [
        pytest.param("a@example.com, b@example.com", id="two-addresses"),
        pytest.param("noreply", id="no-at"),
        pytest.param("LibreFolio <>", id="empty-address"),
        pytest.param("@example.com", id="empty-local-part"),
        pytest.param("noreply@", id="empty-domain"),
        pytest.param("no reply@example.com", id="space-inside"),
        pytest.param("LibreFolio <no reply@example.com>", id="space-inside-brackets"),
        pytest.param("noreply@example.com\r\nBcc: eve@example.org", id="crlf-injection"),
        pytest.param("Libre\rFolio <noreply@example.com>", id="cr-in-name"),
        pytest.param("noreply@example.com\n", id="lf-at-the-end-of-the-raw-value"),
    ],
)
def test_a_mailbox_variable_refuses_anything_but_one_clean_mailbox(monkeypatch: pytest.MonkeyPatch, variable: str, accessor: Callable[[], object], code: str, value: str) -> None:
    """EMC-015 — contract 7: two addresses, no ``@``, an empty local or domain part, whitespace inside the address, a CR or LF anywhere in the raw value — even where stripping would remove it — is the variable's ``*_INVALID`` code."""
    print_section(f"EMC-015: {variable} = {value!r}")
    monkeypatch.setenv(variable, value)

    error = _config_error(accessor)

    assert (error.variable, error.code) == (variable, code)
    print_success(code)


# =============================================================================
# 8. HOURLY LIMIT
# =============================================================================


@pytest.mark.parametrize(("value", "expected"), [("10", 10), (" 7 ", 7), ("1", 1), ("100000", 100000)])
def test_smtp_max_per_hour_reads_a_positive_integer(monkeypatch: pytest.MonkeyPatch, value: str, expected: int) -> None:
    """EMC-016 — contract 8: ASCII digits, stripped, at least 1."""
    print_section(f"EMC-016: max per hour {value!r}")
    monkeypatch.setenv(MAX_PER_HOUR, value)

    assert smtp_max_per_hour() == expected
    print_success(f"→ {expected}")


@pytest.mark.parametrize("value", ["0", "-5", "ten", "1.5", "+5", "1_0", "\uff11\uff10"])
def test_smtp_max_per_hour_refuses_anything_else(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """EMC-017 — contract 8: zero, negative, words, decimals, signs, ``1_0`` and fullwidth digits are ``SMTP_MAX_PER_HOUR_INVALID``."""
    print_section(f"EMC-017: max per hour {value!r}")
    monkeypatch.setenv(MAX_PER_HOUR, value)

    error = _config_error(smtp_max_per_hour)

    assert (error.variable, error.code) == (MAX_PER_HOUR, "SMTP_MAX_PER_HOUR_INVALID")
    print_success("SMTP_MAX_PER_HOUR_INVALID")


# =============================================================================
# 9. THE ERROR
# =============================================================================


@pytest.mark.parametrize(
    ("variable", "value", "accessor", "code"),
    [
        pytest.param(HOST, "smtp://x", smtp_host, "SMTP_HOST_INVALID", id="host"),
        pytest.param(TLS, "ssl", smtp_tls_mode, "SMTP_TLS_INVALID", id="tls"),
        pytest.param(PORT, "65536", smtp_port, "SMTP_PORT_INVALID", id="port"),
        pytest.param(FROM, "noreply", smtp_sender, "SMTP_FROM_INVALID", id="from"),
        pytest.param(REPLY_TO, "noreply", smtp_reply_to, "SMTP_REPLY_TO_INVALID", id="reply-to"),
        pytest.param(MAX_PER_HOUR, "0", smtp_max_per_hour, "SMTP_MAX_PER_HOUR_INVALID", id="max-per-hour"),
    ],
)
def test_the_error_names_its_variable_and_never_the_password(monkeypatch: pytest.MonkeyPatch, variable: str, value: str, accessor: Callable[[], object], code: str) -> None:
    """EMC-018 — contract 9: ``variable`` and ``code`` on the exception, the variable in its message, and not the SMTP password, set beside it — the message reaches the startup log."""
    print_section(f"EMC-018: the error of {variable}")
    monkeypatch.setenv(USER, "mailer")
    monkeypatch.setenv(PASSWORD, CANARY_PASSWORD)
    monkeypatch.setenv(variable, value)

    error = _config_error(accessor)

    assert isinstance(error, ValueError)
    assert (error.variable, error.code) == (variable, code)
    assert variable in str(error), f"the message does not name {variable}: {str(error)!r}"
    assert CANARY_PASSWORD not in str(error) and CANARY_PASSWORD not in repr(error), "the SMTP password reached the error"
    print_success(f"{code}, names {variable}, no password")


# =============================================================================
# 10. READ AT EVERY CALL
# =============================================================================


@pytest.mark.parametrize(
    ("variable", "accessor", "first", "first_result", "second", "second_result", "unset_result"),
    [
        pytest.param(HOST, smtp_host, "smtp.example.com", "smtp.example.com", "relay.example.org", "relay.example.org", None, id="host"),
        pytest.param(TLS, smtp_tls_mode, "tls", "tls", "none", "none", "starttls", id="tls"),
        pytest.param(PORT, smtp_port, "2525", 2525, "2526", 2526, 587, id="port"),
        pytest.param(USER, smtp_user, "alice", "alice", "bob", "bob", None, id="user"),
        pytest.param(PASSWORD, smtp_password, "first-s3cret", "first-s3cret", "second-s3cret", "second-s3cret", None, id="password"),
        pytest.param(FROM, smtp_sender, "a@example.com", ("", "a@example.com"), "B <b@example.org>", ("B", "b@example.org"), None, id="from"),
        pytest.param(REPLY_TO, smtp_reply_to, "a@example.com", ("", "a@example.com"), "B <b@example.org>", ("B", "b@example.org"), None, id="reply-to"),
        pytest.param(MAX_PER_HOUR, smtp_max_per_hour, "5", 5, "6", 6, 50, id="max-per-hour"),
    ],
)
def test_every_accessor_reads_the_environment_at_each_call(
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
    accessor: Callable[[], object],
    first: str,
    first_result: object,
    second: str,
    second_result: object,
    unset_result: object,
) -> None:
    """EMC-019 — contract 10: set, changed, removed — each call sees the environment of that moment, so nothing is cached at import or first use."""
    print_section(f"EMC-019: {accessor.__name__} at each call")

    monkeypatch.setenv(variable, first)
    assert accessor() == first_result
    monkeypatch.setenv(variable, second)
    assert accessor() == second_result
    monkeypatch.delenv(variable)
    assert accessor() == unset_result
    print_success("set, changed, removed: seen each time")
