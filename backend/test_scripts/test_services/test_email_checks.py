"""``backend.app.services.email.checks``: the configuration checks of the optional e-mail (plan phase01Email §3.2, decision D-E4, lot E1).

An invalid SMTP configuration does not stop the start: e-mail stays off, the log says so once, and the admin's
«Security» tab says it again through a ``ConfigCheck`` of the platform's configuration audit (``config_audit``, owned
by workstream H). Lot E1 writes the checks only: they join ``CONFIG_CHECKS`` in E2, so ``run_config_checks`` is not
under test here. The contract pinned here:

1. ``check_smtp_configuration`` (``email.smtp``): no host is ``ok`` / ``email.checks.smtp.off`` — e-mail is optional —;
   a usable configuration ``ok`` / ``email.checks.smtp.ok``; an invalid one ``error`` / ``email.checks.smtp.invalid``,
   with ``detail == {"problem": <code>, "variable": <name>}`` and a summary naming the variable and saying that e-mail
   stays off.
2. ``check_smtp_encryption`` (``email.smtp_encryption``): nothing to say about e-mail that is not usable, nor about
   ``starttls`` and ``tls`` (``ok`` / ``email.checks.smtpEncryption.ok``); ``none`` towards a local relay — loopback,
   private and CGNAT/VPN ranges, single-label names, ``.localhost``, ``.local``, ``.lan``, ``.home.arpa``,
   ``.internal`` — ``ok`` / ``email.checks.smtpEncryption.localPlain``; ``none`` towards anything else a ``warning`` /
   ``email.checks.smtpEncryption.plain`` with an empty detail.
3. ``EMAIL_CONFIG_CHECKS`` is the two checks, in that order.
4. No result holds the SMTP password, in any field; no detail holds the host, the user or the sender's address — the
   detail travels to the admin interface as the parameters of a translated message.

Pure: no database, no server, no network. An autouse fixture removes every inherited ``LIBREFOLIO_SMTP_*`` (until C-96
lands a lane carries the developer's ``.env``); each test sets its own with ``monkeypatch``; password files live in
``tmp_path``.

Red until ``backend/app/services/email/checks.py`` exists: the package does not import.
"""

from __future__ import annotations

import dataclasses
import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from backend.app.services.email.checks import EMAIL_CONFIG_CHECKS, check_smtp_configuration, check_smtp_encryption
from backend.app.services.platform.config_audit import ConfigCheck
from backend.test_scripts.test_utils import print_section, print_success

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

#: Distinctive values: found in a detail, each would be a leak. Their cores are searched, so that a local host
#: (``zq-relay.lan``) is caught as surely as a public one.
HOST_VALUE = "zq-relay.example.com"
USER_VALUE = "zq-mailer"
SENDER_ADDRESS = "zq-sender@example.com"
NOT_IN_A_DETAIL = ("zq-relay", "zq-mailer", "zq-sender")
SMTP_PASSWORD = "c4nary-SMTP-p4ss-never-in-a-check"

BASE = {"host": HOST_VALUE, "from": f"LibreFolio <{SENDER_ADDRESS}>"}
CREDENTIALS = {"user": USER_VALUE, "password": SMTP_PASSWORD}
MISSING_FILE = "<a password file that does not exist>"
EMPTY_FILE = "<an empty password file>"
#: One fault each, on top of ``BASE``: the problem and the variable the check reports.
PROBLEMS = [
    pytest.param({"host": "smtp://zq-relay.example.com"}, "SMTP_HOST_INVALID", HOST, id="host-invalid"),
    pytest.param({"tls": "ssl"}, "SMTP_TLS_INVALID", TLS, id="tls-invalid"),
    pytest.param({"port": "65536"}, "SMTP_PORT_INVALID", PORT, id="port-invalid"),
    pytest.param({"from": None}, "SMTP_FROM_MISSING", FROM, id="from-missing"),
    pytest.param({"from": "noreply"}, "SMTP_FROM_INVALID", FROM, id="from-invalid"),
    pytest.param({"reply_to": "a@example.com, b@example.com"}, "SMTP_REPLY_TO_INVALID", REPLY_TO, id="reply-to-invalid"),
    pytest.param({"max_per_hour": "0"}, "SMTP_MAX_PER_HOUR_INVALID", MAX_PER_HOUR, id="max-per-hour-invalid"),
    pytest.param({"user": USER_VALUE, "password_file": MISSING_FILE}, "SMTP_PASSWORD_UNREADABLE", PASSWORD_FILE, id="password-file-missing"),
    pytest.param({"user": USER_VALUE, "password_file": EMPTY_FILE}, "SMTP_PASSWORD_UNREADABLE", PASSWORD_FILE, id="password-file-empty"),
    pytest.param({"user": USER_VALUE}, "SMTP_CREDENTIALS_INCOMPLETE", USER, id="user-without-password"),
    pytest.param({"password": SMTP_PASSWORD}, "SMTP_CREDENTIALS_INCOMPLETE", PASSWORD, id="password-without-user"),
]

LOCAL_HOSTS = [
    "localhost",
    "x.localhost",
    "127.0.0.1",
    "::1",
    "10.1.2.3",
    "192.168.1.5",
    "172.16.0.1",
    "100.64.0.1",
    "postfix",
    "mailrelay",
    "mail.local",
    "nas.lan",
    "relay.home.arpa",
    "smtp.corp.internal",
]
PUBLIC_HOSTS = ["smtp.example.com", "203.0.113.7", "relay.tailnet.ts.net"]


@pytest.fixture(autouse=True)
def _no_inherited_smtp_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*`` the lane inherited is removed: a test sees only the variables it sets itself."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX):
            monkeypatch.delenv(name, raising=False)


def _configure(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str | None], tmp_path: Path | None = None) -> None:
    """Set ``LIBREFOLIO_SMTP_<NAME>`` for each ``name: value``, ``None`` leaving it unset; the file markers become files in ``tmp_path``."""
    for name, value in variables.items():
        if value == MISSING_FILE:
            value = str(tmp_path / "no-such-password-file")
        elif value == EMPTY_FILE:
            value = str(tmp_path / "empty-password-file")
            Path(value).write_text("", encoding="utf-8")
        variable = SMTP_PREFIX + name.upper()
        if value is None:
            monkeypatch.delenv(variable, raising=False)
        else:
            monkeypatch.setenv(variable, value)


def _texts(value: object) -> Iterator[str]:
    """Every piece of text in a value, nested containers included: the ``str`` and the ``repr`` of each leaf."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _texts(item)
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            yield from _texts(item)
    else:
        yield str(value)
        yield repr(value)


def _state(result: ConfigCheck) -> tuple[str, str, str]:
    return (result.check_id, result.severity, result.i18n_key)


# =============================================================================
# 1. check_smtp_configuration
# =============================================================================


@pytest.mark.parametrize("host", [None, "", "   "], ids=["unset", "empty", "blank"])
def test_without_a_host_the_configuration_check_says_email_is_off(monkeypatch: pytest.MonkeyPatch, host: str | None) -> None:
    """EMK-001 — contract 1: no host is ``ok`` — e-mail is optional — with the key that says it is off."""
    print_section(f"EMK-001: host {host!r}")
    _configure(monkeypatch, {"host": host})

    result = check_smtp_configuration()

    assert isinstance(result, ConfigCheck)
    assert _state(result) == ("email.smtp", "ok", "email.checks.smtp.off")
    print_success("ok: off")


def test_a_usable_configuration_is_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """EMK-002 — contract 1: a usable configuration is ``ok`` with the key that says so."""
    print_section("EMK-002: usable")
    _configure(monkeypatch, {**BASE, **CREDENTIALS})

    result = check_smtp_configuration()

    assert isinstance(result, ConfigCheck)
    assert _state(result) == ("email.smtp", "ok", "email.checks.smtp.ok")
    print_success("ok")


@pytest.mark.parametrize(("overrides", "problem", "variable"), PROBLEMS)
def test_an_invalid_configuration_is_an_error_naming_problem_and_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, overrides: dict, problem: str, variable: str) -> None:
    """EMK-003 — contract 1: ``error`` with ``detail == {"problem", "variable"}``; the summary names the variable and says e-mail stays off ("off" or "disabled")."""
    print_section(f"EMK-003: {problem}")
    _configure(monkeypatch, {**BASE, **overrides}, tmp_path)

    result = check_smtp_configuration()

    assert _state(result) == ("email.smtp", "error", "email.checks.smtp.invalid")
    assert result.detail == {"problem": problem, "variable": variable}
    assert variable in result.summary, f"the summary does not name {variable}: {result.summary!r}"
    assert re.search(r"\b(off|disabled)\b", result.summary, flags=re.IGNORECASE), f"the summary does not say e-mail stays off: {result.summary!r}"
    print_success(f"error: {result.summary}")


# =============================================================================
# 2. check_smtp_encryption
# =============================================================================


@pytest.mark.parametrize(
    "variables",
    [
        pytest.param({}, id="email-off"),
        pytest.param({"host": "smtp.example.com", "tls": "none"}, id="plain-to-public-host-but-no-sender"),
        pytest.param({"host": "smtp.example.com", "tls": "none", "from": "noreply@example.com", "port": "0"}, id="plain-to-public-host-but-invalid-port"),
    ],
)
def test_encryption_says_nothing_about_email_that_is_not_usable(monkeypatch: pytest.MonkeyPatch, variables: dict) -> None:
    """EMK-004 — contract 2: e-mail off, or invalid even towards a public host in plain text, is ``ok``: the configuration check already speaks for it."""
    print_section(f"EMK-004: not usable {variables}")
    _configure(monkeypatch, variables)

    result = check_smtp_encryption()

    assert isinstance(result, ConfigCheck)
    assert _state(result) == ("email.smtp_encryption", "ok", "email.checks.smtpEncryption.ok")
    print_success("ok")


@pytest.mark.parametrize("tls", [None, "starttls", "tls"], ids=["default", "starttls", "tls"])
def test_encrypted_delivery_is_ok(monkeypatch: pytest.MonkeyPatch, tls: str | None) -> None:
    """EMK-005 — contract 2: ``starttls`` (the default) and ``tls`` are ``ok``, towards any host."""
    print_section(f"EMK-005: tls {tls!r}")
    _configure(monkeypatch, {**BASE, "host": "smtp.example.com", "tls": tls})

    assert _state(check_smtp_encryption()) == ("email.smtp_encryption", "ok", "email.checks.smtpEncryption.ok")
    print_success("ok")


@pytest.mark.parametrize("host", LOCAL_HOSTS)
def test_plain_text_to_a_local_relay_is_ok(monkeypatch: pytest.MonkeyPatch, host: str) -> None:
    """EMK-006 — contract 2: ``none`` towards loopback, a private or CGNAT/VPN address, a single-label name or a local suffix is ``ok`` — the relay on the same machine or network is the common self-hosted case."""
    print_section(f"EMK-006: plain to {host}")
    _configure(monkeypatch, {**BASE, "host": host, "tls": "none"})

    assert _state(check_smtp_encryption()) == ("email.smtp_encryption", "ok", "email.checks.smtpEncryption.localPlain")
    print_success("ok: local plain")


@pytest.mark.parametrize("host", PUBLIC_HOSTS)
def test_plain_text_to_any_other_host_is_a_warning(monkeypatch: pytest.MonkeyPatch, host: str) -> None:
    """EMK-007 — contract 2: ``none`` towards a public name or address — a tailnet name included — is a ``warning``, with an empty detail."""
    print_section(f"EMK-007: plain to {host}")
    _configure(monkeypatch, {**BASE, "host": host, "tls": "none"})

    result = check_smtp_encryption()

    assert _state(result) == ("email.smtp_encryption", "warning", "email.checks.smtpEncryption.plain")
    assert result.detail == {}
    print_success("warning")


# =============================================================================
# 3-4. THE LIST, AND NO SECRET
# =============================================================================


def test_email_config_checks_lists_the_two_checks_in_order() -> None:
    """EMK-008 — contract 3: the tuple E2 will add to ``CONFIG_CHECKS``."""
    print_section("EMK-008: EMAIL_CONFIG_CHECKS")

    assert EMAIL_CONFIG_CHECKS == (check_smtp_configuration, check_smtp_encryption)
    print_success("configuration, encryption")


@pytest.mark.parametrize(
    "variables",
    [
        pytest.param({**CREDENTIALS}, id="off-with-credentials"),
        pytest.param({**BASE, **CREDENTIALS}, id="usable"),
        pytest.param({**BASE, **CREDENTIALS, "tls": "none"}, id="plain-public"),
        pytest.param({**BASE, **CREDENTIALS, "host": "zq-relay.lan", "tls": "none"}, id="plain-local"),
        pytest.param({**BASE, **CREDENTIALS, "tls": "ssl"}, id="invalid-tls"),
        pytest.param({**BASE, **CREDENTIALS, "host": f"smtp://{HOST_VALUE}"}, id="invalid-host"),
        pytest.param({**BASE, "password": SMTP_PASSWORD}, id="password-without-user"),
        pytest.param({**BASE, "user": USER_VALUE}, id="user-without-password"),
        pytest.param({**BASE, **CREDENTIALS, "from": f"<{SENDER_ADDRESS}>, b@example.com"}, id="invalid-from"),
    ],
)
def test_no_check_holds_the_password_and_no_detail_names_host_user_or_sender(monkeypatch: pytest.MonkeyPatch, variables: dict) -> None:
    """EMK-009 — contract 4: in every state, no field of either result holds the SMTP password, and no detail holds the host, the user or the sender's address."""
    print_section("EMK-009: no secret in the checks")
    _configure(monkeypatch, variables)

    results = [check_smtp_configuration(), check_smtp_encryption()]

    for result in results:
        assert not [text for text in _texts(dataclasses.asdict(result)) if SMTP_PASSWORD in text], f"{result.check_id} holds the SMTP password"
        detail = list(_texts(result.detail))
        assert [core for core in NOT_IN_A_DETAIL if any(core in text for text in detail)] == [], f"{result.check_id}: {result.detail}"
    print_success(", ".join(f"{result.check_id}={result.severity}" for result in results))
