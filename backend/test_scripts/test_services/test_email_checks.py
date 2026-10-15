"""``backend.app.services.email.checks``: the configuration checks of the optional e-mail (plan phase01Email §3.2, decisions D-E4 and 45, lots E1, E2b and E3).

An invalid SMTP configuration does not stop the start: e-mail stays off, the log says so once, and the admin's
«Security» tab says it again through a ``ConfigCheck`` of the platform's configuration audit (``config_audit``, owned
by workstream H). Since lot E2b the email checks end the platform's ``CONFIG_CHECKS``: the startup audit logs them like
any other check, and ``GET /email/status`` shows them. Lot E3 adds the third, ``email.links``: a missing or wrong
``LIBREFOLIO_PUBLIC_URL`` must not be silent. The contract pinned here:

1. ``check_smtp_configuration`` (``email.smtp``): no host is ``ok`` / ``email.checks.smtp.off`` — e-mail is optional —;
   a usable configuration ``ok`` / ``email.checks.smtp.ok``; an invalid one ``error`` / ``email.checks.smtp.invalid``,
   with ``detail == {"problem": <code>, "variable": <name>}`` and a summary naming the variable and saying that e-mail
   stays off.
2. ``check_smtp_encryption`` (``email.smtp_encryption``): nothing to say about e-mail that is not usable, nor about
   ``starttls`` and ``tls`` (``ok`` / ``email.checks.smtpEncryption.ok``); ``none`` towards a local relay — loopback,
   private and CGNAT/VPN ranges, single-label names, ``.localhost``, ``.local``, ``.lan``, ``.home.arpa``,
   ``.internal`` — ``ok`` / ``email.checks.smtpEncryption.localPlain``; ``none`` towards anything else a ``warning`` /
   ``email.checks.smtpEncryption.plain`` with an empty detail.
3. ``EMAIL_CONFIG_CHECKS`` is the three checks, in that order: configuration, encryption, links.
4. No result holds the SMTP password, in any field; no detail holds the host, the user or the sender's address — the
   detail travels to the admin interface as the parameters of a translated message.
5. ``config_audit.CONFIG_CHECKS`` ends with exactly ``EMAIL_CONFIG_CHECKS`` — the same functions, in that order, and
   nowhere else in the tuple —, so ``run_config_checks()`` ends with the three email results, equal to what each check
   returns on its own.
6. Either module can be imported first: in a fresh interpreter, ``checks`` then ``config_audit``, ``config_audit`` then
   ``checks``, ``links`` first and ``backend.app.api.v1.email`` first all import, end ``CONFIG_CHECKS`` with the three
   email checks — the very objects of ``EMAIL_CONFIG_CHECKS`` — and run them (``checks`` imports ``ConfigCheck`` and the
   links when a check runs, never at import, so the modules never meet half-initialised).
7. ``log_configuration_audit()`` logs the email checks as it logs every check that is not ``ok``, and never stops the
   start for them: an unusable SMTP configuration is one ``error`` record, ``check="email.smtp"``, with the check's
   summary and detail; ``LIBREFOLIO_SMTP_TLS=none`` towards a public host one ``warning``,
   ``check="email.smtp_encryption"``, whose summary names the variable and the host (the log only: the interface gets
   the key and the detail); usable email without ``LIBREFOLIO_PUBLIC_URL`` one ``info``, with a value that is not
   http(s) one ``warning``, ``check="email.links"``; email off, no email record at all. The SMTP password is in no
   record of the audit — its own, nor the e-mail delivery's, which reports an unusable configuration once per process.
8. ``check_email_links`` (``email.links``): ``ok`` / ``email.checks.links.ok`` when email is not usable — off or
   invalid: nothing to say, whatever the variable — or when links are ready; with usable email, ``info`` /
   ``email.checks.links.missing`` for ``LIBREFOLIO_PUBLIC_URL`` unset or blank and ``warning`` /
   ``email.checks.links.invalid`` for a value that is not an http(s) address, or one no link can start from (no host,
   a user name or a password, a ``?`` or a ``#`` even with nothing after it, a space inside, a bad port) — each with a
   summary for the log that names the variable, never its value. Never a detail.

Pure: no database, no server, no network. An autouse fixture removes every inherited ``LIBREFOLIO_SMTP_*`` and
``LIBREFOLIO_PUBLIC_URL`` (C-96 removes them from the lanes; a developer's shell may still carry them); each test sets
its own with ``monkeypatch``; password files live in ``tmp_path``. The audit runs with the platform isolated as
``test_config_audit.py`` isolates it — test mode, its data directory in ``tmp_path`` (no instance key there), no JWT
secret, no instance key, no block — and with ``config_audit``'s logger replaced by a recorder. The fresh interpreters
run in test mode, their data directory in ``tmp_path``, without any ``LIBREFOLIO_SMTP_*`` nor ``LIBREFOLIO_PUBLIC_URL``,
bounded by a timeout that is never a wait.

Red until ``backend/app/services/email/checks.py`` exists: the package does not import.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import subprocess
import sys
import textwrap
from collections.abc import Iterator
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from backend.app.services.email import delivery
from backend.app.services.email.checks import EMAIL_CONFIG_CHECKS, check_email_links, check_smtp_configuration, check_smtp_encryption
from backend.app.services.platform import config_audit
from backend.app.services.platform.config_audit import ConfigCheck
from backend.app.services.platform.instance_key import INSTANCE_KEY_FILE, instance_key_path
from backend.test_scripts.test_utils import print_section, print_success

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
#: A public address of the instance, and a value of the variable that is not an http(s) address: recognisable, so that
#: a summary or a detail echoing either would show it.
PUBLIC_URL = "https://folio.zq-public.example.com"
NOT_A_PUBLIC_URL = "ftp://zq-not-public.example.com"
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
PASSWORD_IN_FILE = "<a file holding the SMTP password>"
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

EMAIL_CHECK_IDS = ["email.smtp", "email.smtp_encryption", "email.links"]
EMAIL_CHECK_NAMES = ["check_smtp_configuration", "check_smtp_encryption", "check_email_links"]
#: One unusable configuration each, the SMTP password set beside the fault — in the variable, or in a file that can be
#: read — wherever the fault leaves room for it: the problem and the variable ``email.smtp`` reports.
UNUSABLE_FOR_THE_AUDIT = [
    pytest.param({**CREDENTIALS, "port": "65536"}, "SMTP_PORT_INVALID", PORT, id="port-invalid-password-in-the-variable"),
    pytest.param({"user": USER_VALUE, "password_file": PASSWORD_IN_FILE, "port": "65536"}, "SMTP_PORT_INVALID", PORT, id="port-invalid-password-in-a-file"),
    pytest.param({**CREDENTIALS, "tls": "ssl"}, "SMTP_TLS_INVALID", TLS, id="tls-invalid"),
    pytest.param({**CREDENTIALS, "from": None}, "SMTP_FROM_MISSING", FROM, id="from-missing"),
    pytest.param({"user": USER_VALUE, "password_file": MISSING_FILE}, "SMTP_PASSWORD_UNREADABLE", PASSWORD_FILE, id="password-file-missing"),
]

#: The working directory of the fresh interpreters: the project root, where ``import backend`` resolves.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
#: A bound for a fresh interpreter that hangs, never a wait: one of them imports the whole API.
FRESH_INTERPRETER_TIMEOUT_SECONDS = 300
FRESH_IMPORT_MARKER = "FRESH-IMPORT "
#: What a fresh interpreter runs: it imports the modules named on its command line, in that order, then reports the end
#: of ``CONFIG_CHECKS`` — as many checks as ``EMAIL_CONFIG_CHECKS`` holds — and what they return; ``preloaded`` proves
#: that no watched module was there before.
FRESH_IMPORT = textwrap.dedent("""
    import importlib
    import json
    import sys

    watched = ("backend.app.services.email.checks", "backend.app.services.email.links", "backend.app.services.platform.config_audit")
    preloaded = [name for name in watched if name in sys.modules]
    for name in sys.argv[1:]:
        importlib.import_module(name)
    from backend.app.services.email.checks import EMAIL_CONFIG_CHECKS
    from backend.app.services.platform.config_audit import CONFIG_CHECKS, run_config_checks

    count = len(EMAIL_CONFIG_CHECKS)
    report = {
        "preloaded": preloaded,
        "last": [check.__name__ for check in CONFIG_CHECKS[-count:]],
        "same_objects": len(CONFIG_CHECKS) > count and all(a is b for a, b in zip(CONFIG_CHECKS[-count:], EMAIL_CONFIG_CHECKS, strict=True)),
        "ran": [result.check_id for result in run_config_checks()[-count:]],
    }
    print("FRESH-IMPORT " + json.dumps(report))
    """)


@pytest.fixture(autouse=True)
def _no_inherited_email_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*`` and ``LIBREFOLIO_PUBLIC_URL`` the lane inherited is removed: a test sees only the variables it sets itself."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX) or name == PUBLIC_URL_VARIABLE:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _nothing_reported_yet() -> Iterator[None]:
    """``delivery._report_invalid`` remembers for the whole process what it logged: each test starts, and leaves, with nothing reported."""
    delivery._report_invalid.cache_clear()
    yield
    delivery._report_invalid.cache_clear()


@pytest.fixture
def platform(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """The platform's side of the startup audit, isolated as ``test_config_audit.py``'s ``_configure`` isolates it: test mode, a data directory in ``tmp_path`` with no instance key yet, no JWT secret, no instance key, no block, cookie ``auto``, log level ``INFO``, profile ``selfhosted`` — every platform check is ok but the unset JWT secret (info). The data directory, verified to be the one the instance key is looked for in."""
    for variable in [name for name in os.environ if name.endswith("_FILE") and (name == "JWT_SECRET_FILE" or name.startswith("LIBREFOLIO_"))]:
        monkeypatch.delenv(variable)
    for variable in ("JWT_SECRET", "LIBREFOLIO_INSTANCE_KEY", "LIBREFOLIO_LOG_LEVEL", "LIBREFOLIO_DATA_DIR", "LIBREFOLIO_TEST_DATA_DIR", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_DELETION_DATE"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "auto")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    data_dir = (tmp_path / "data").resolve()
    assert instance_key_path() == data_dir / INSTANCE_KEY_FILE, f"the instance key must be looked for in the data directory of this test, not at {instance_key_path()}"
    return data_dir


class LogRecorder:
    """Stands in for ``config_audit``'s structlog logger, as in ``test_config_audit.py``: one ``(level, summary, fields)`` per call."""

    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict]] = []

    def info(self, event: str, **fields) -> None:
        self.records.append(("info", event, fields))

    def warning(self, event: str, **fields) -> None:
        self.records.append(("warning", event, fields))

    def error(self, event: str, **fields) -> None:
        self.records.append(("error", event, fields))


@pytest.fixture
def logged(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, dict]]:
    """The records of the startup audit: ``config_audit.logger`` replaced by a recorder."""
    recorder = LogRecorder()
    monkeypatch.setattr(config_audit, "logger", recorder)
    return recorder.records


def _email_records(records: list[tuple[str, str, dict]]) -> list[tuple[str, str, dict]]:
    """The records of the audit about an email check."""
    return [record for record in records if str(record[2].get("check", "")).startswith("email.")]


def _as_logged(result: ConfigCheck) -> tuple[str, str, dict]:
    """The record ``log_configuration_audit`` writes for a check that is not ok: its severity, its summary, its id and detail."""
    return (result.severity, result.summary, {"check": result.check_id, "detail": result.detail})


def _fresh_environment(tmp_path: Path) -> dict[str, str]:
    """This process's environment for a fresh interpreter: no ``LIBREFOLIO_SMTP_*`` nor ``LIBREFOLIO_PUBLIC_URL``, test mode, its data directory in ``tmp_path``, the project root importable."""
    environment = {name: value for name, value in os.environ.items() if not name.startswith(SMTP_PREFIX) and name != PUBLIC_URL_VARIABLE}
    environment["LIBREFOLIO_TEST_MODE"] = "1"
    environment["LIBREFOLIO_TEST_DATA_DIR"] = str(tmp_path / "data")
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, [str(PROJECT_ROOT), environment.get("PYTHONPATH")]))
    return environment


def _configure(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str | None], tmp_path: Path | None = None) -> None:
    """Set ``LIBREFOLIO_SMTP_<NAME>`` for each ``name: value``, ``None`` leaving it unset; the file markers become files in ``tmp_path``."""
    for name, value in variables.items():
        if value == MISSING_FILE:
            value = str(tmp_path / "no-such-password-file")
        elif value == EMPTY_FILE:
            value = str(tmp_path / "empty-password-file")
            Path(value).write_text("", encoding="utf-8")
        elif value == PASSWORD_IN_FILE:
            value = str(tmp_path / "password-file")
            Path(value).write_text(f"{SMTP_PASSWORD}\n", encoding="utf-8")
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


def test_email_config_checks_lists_the_three_checks_in_order() -> None:
    """EMK-008 — contract 3: the three checks, in that order — configuration, encryption, links —: the tuple ``config_audit.CONFIG_CHECKS`` ends with (EMK-010)."""
    print_section("EMK-008: EMAIL_CONFIG_CHECKS")

    assert EMAIL_CONFIG_CHECKS == (check_smtp_configuration, check_smtp_encryption, check_email_links)
    print_success("configuration, encryption, links")


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
    """EMK-009 — contract 4: in every state, no field of any of the three results holds the SMTP password, and no detail holds the host, the user or the sender's address."""
    print_section("EMK-009: no secret in the checks")
    _configure(monkeypatch, variables)

    results = [check() for check in EMAIL_CONFIG_CHECKS]

    for result in results:
        assert not [text for text in _texts(dataclasses.asdict(result)) if SMTP_PASSWORD in text], f"{result.check_id} holds the SMTP password"
        detail = list(_texts(result.detail))
        assert [core for core in NOT_IN_A_DETAIL if any(core in text for text in detail)] == [], f"{result.check_id}: {result.detail}"
    print_success(", ".join(f"{result.check_id}={result.severity}" for result in results))


# =============================================================================
# 5-6. IN THE PLATFORM'S CONFIG_CHECKS, WHICHEVER MODULE COMES FIRST
# =============================================================================


def test_config_checks_ends_with_exactly_the_email_checks() -> None:
    """EMK-010 — contract 5: the last three functions of ``config_audit.CONFIG_CHECKS`` are the very objects of ``EMAIL_CONFIG_CHECKS``, in that order, and none of them appears earlier in the tuple."""
    print_section("EMK-010: the end of CONFIG_CHECKS")
    checks = config_audit.CONFIG_CHECKS
    tail, others = checks[-3:], checks[:-3]

    assert len(EMAIL_CONFIG_CHECKS) == 3 and len(checks) > 3, f"precondition: three email checks after the platform's own: {checks}"
    assert all(ours is theirs for ours, theirs in zip(tail, EMAIL_CONFIG_CHECKS, strict=True)), f"CONFIG_CHECKS must end with EMAIL_CONFIG_CHECKS itself: {[check.__name__ for check in tail]}"
    assert not [check.__name__ for check in others if check in EMAIL_CONFIG_CHECKS], f"an email check appears before the end of CONFIG_CHECKS: {[check.__name__ for check in checks]}"
    print_success(f"{len(others)} platform checks, then {', '.join(check.__name__ for check in tail)}")


@pytest.mark.parametrize(
    ("variables", "public_url"),
    [
        pytest.param({}, None, id="off"),
        pytest.param({**BASE, **CREDENTIALS}, PUBLIC_URL, id="usable-links-ready"),
        pytest.param({**BASE, **CREDENTIALS}, None, id="usable-links-missing"),
        pytest.param({**BASE, **CREDENTIALS, "tls": "none"}, NOT_A_PUBLIC_URL, id="plain-to-a-public-host-links-invalid"),
        pytest.param({**BASE, **CREDENTIALS, "port": "65536"}, None, id="invalid-port"),
    ],
)
def test_run_config_checks_ends_with_the_three_email_results(platform: Path, monkeypatch: pytest.MonkeyPatch, variables: dict, public_url: str | None) -> None:
    """EMK-011 — contract 5: whatever the SMTP configuration and ``LIBREFOLIO_PUBLIC_URL`` — off, usable with links ready or missing, plain text to a public host with links invalid, invalid —, ``run_config_checks()`` ends with ``email.smtp``, ``email.smtp_encryption`` and ``email.links``, each once, equal to what the three checks return on their own."""
    print_section(f"EMK-011: run_config_checks with {sorted(variables)}, LIBREFOLIO_PUBLIC_URL={public_url!r}")
    _configure(monkeypatch, variables)
    if public_url is not None:
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)

    results = config_audit.run_config_checks()

    ids = [result.check_id for result in results]
    assert ids[-3:] == EMAIL_CHECK_IDS and [ids.count(check_id) for check_id in EMAIL_CHECK_IDS] == [1, 1, 1], f"run_config_checks must end with the three email results, once each: {ids}"
    assert results[-3:] == [check() for check in EMAIL_CONFIG_CHECKS], "run_config_checks must carry what the email checks return on their own"
    print_success(", ".join(f"{result.check_id}={result.severity}" for result in results[-3:]))


@pytest.mark.parametrize(
    "order",
    [
        pytest.param(("backend.app.services.email.checks", "backend.app.services.platform.config_audit"), id="checks-then-config-audit"),
        pytest.param(("backend.app.services.platform.config_audit", "backend.app.services.email.checks"), id="config-audit-then-checks"),
        pytest.param(("backend.app.services.email.links", "backend.app.services.platform.config_audit"), id="links-first"),
        pytest.param(("backend.app.api.v1.email", "backend.app.services.platform.config_audit"), id="email-api-first"),
    ],
)
def test_either_module_can_be_imported_first_in_a_fresh_interpreter(tmp_path: Path, order: tuple[str, ...]) -> None:
    """EMK-012 — contract 6: a fresh interpreter — no ``LIBREFOLIO_SMTP_*`` nor ``LIBREFOLIO_PUBLIC_URL``, test mode, its data directory in ``tmp_path`` — imports ``order`` in that order and exits 0; it reports ``check_smtp_configuration``, ``check_smtp_encryption`` and ``check_email_links`` as the last three checks of ``CONFIG_CHECKS``, the very objects of ``EMAIL_CONFIG_CHECKS``, and runs them: ``email.smtp``, ``email.smtp_encryption``, ``email.links`` (the last importing the links when it runs).

    Barrier first: no watched module was loaded before the first import, so the order is the one the case names.
    """
    print_section(f"EMK-012: {' then '.join(order)}")

    completed = subprocess.run([sys.executable, "-c", FRESH_IMPORT, *order], cwd=PROJECT_ROOT, env=_fresh_environment(tmp_path), capture_output=True, text=True, timeout=FRESH_INTERPRETER_TIMEOUT_SECONDS, check=False)

    assert completed.returncode == 0, f"importing {' then '.join(order)} in a fresh interpreter failed with {completed.returncode}:\n{completed.stderr[-4000:]}"
    reports = [line.removeprefix(FRESH_IMPORT_MARKER) for line in completed.stdout.splitlines() if line.startswith(FRESH_IMPORT_MARKER)]
    assert len(reports) == 1, f"the fresh interpreter must report once: {completed.stdout[-4000:]}"
    report = json.loads(reports[0])
    assert report["preloaded"] == [], f"barrier: a fresh interpreter loads no watched module before the first import: {report['preloaded']}"
    assert report == {"preloaded": [], "last": EMAIL_CHECK_NAMES, "same_objects": True, "ran": EMAIL_CHECK_IDS}, f"{' then '.join(order)}: {report}"
    print_success(f"{' then '.join(order)}: {', '.join(report['last'])}")


# =============================================================================
# 7. THE STARTUP LOG
# =============================================================================


@pytest.mark.parametrize(("overrides", "problem", "variable"), UNUSABLE_FOR_THE_AUDIT)
def test_the_startup_audit_logs_an_unusable_configuration_once_as_an_error_and_goes_on(platform: Path, logged: list, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, overrides: dict, problem: str, variable: str) -> None:
    """EMK-013 — contract 7: an unusable SMTP configuration, the password set beside the fault where it can be, ``LIBREFOLIO_PUBLIC_URL`` unset: ``log_configuration_audit()`` returns — the start goes on — after one email record, the ``error`` of ``email.smtp`` with the check's summary and its detail ``{problem, variable}``; none of ``email.smtp_encryption``, none of ``email.links`` (email is not usable: the missing links are not news). Neither its records nor the events of the e-mail delivery hold the SMTP password.

    Barriers: the delivery reported the unusable configuration during the audit (its event names the problem), so the
    capture of its events is not blind; the record is the check's own result, so it is the check that spoke.
    """
    print_section(f"EMK-013: {problem} at startup")
    _configure(monkeypatch, {**BASE, **overrides}, tmp_path)

    with capture_logs() as events:
        returned = config_audit.log_configuration_audit()

    expected = check_smtp_configuration()
    assert (expected.severity, expected.detail) == ("error", {"problem": problem, "variable": variable}), f"precondition: the configuration must be unusable by {problem}: {expected}"
    assert returned is None
    assert _email_records(logged) == [_as_logged(expected)], f"one error record of email.smtp, nothing about the encryption: {logged}"
    assert any(problem in repr(event) for event in events), f"barrier: the e-mail delivery's report of the unusable configuration is not among the captured events: {events}"
    assert SMTP_PASSWORD not in repr(logged) and SMTP_PASSWORD not in repr(events), "the startup audit logged the SMTP password"
    print_success(f"error: {expected.summary}")


def test_the_startup_audit_warns_about_plain_text_to_a_public_host(platform: Path, logged: list, monkeypatch: pytest.MonkeyPatch) -> None:
    """EMK-014 — contract 7: a usable configuration, ``LIBREFOLIO_SMTP_TLS=none`` towards a public host, credentials set, links ready: one email record, the ``warning`` of ``email.smtp_encryption`` with the check's summary — naming ``LIBREFOLIO_SMTP_TLS`` and the host — and its empty detail; nothing about ``email.smtp`` nor ``email.links``, both ok; no record holds the SMTP password."""
    print_section("EMK-014: plain text to a public host at startup")
    _configure(monkeypatch, {**BASE, **CREDENTIALS, "tls": "none"})
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)

    config_audit.log_configuration_audit()

    expected = check_smtp_encryption()
    assert (expected.severity, expected.detail) == ("warning", {}), f"precondition: plain text to {HOST_VALUE} must be a warning: {expected}"
    assert _email_records(logged) == [_as_logged(expected)], f"one warning record of email.smtp_encryption, nothing about email.smtp nor email.links: {logged}"
    assert TLS in expected.summary and HOST_VALUE in expected.summary, f"the log must name the variable and the host it sends to in clear: {expected.summary!r}"
    assert SMTP_PASSWORD not in repr(logged), "the startup audit logged the SMTP password"
    print_success(f"warning: {expected.summary}")


@pytest.mark.parametrize(
    ("variables", "public_url"),
    [
        pytest.param({}, None, id="nothing-set"),
        pytest.param({**BASE, **CREDENTIALS, "host": None, "tls": "ssl"}, NOT_A_PUBLIC_URL, id="everything-but-the-host-links-invalid"),
    ],
)
def test_the_startup_audit_says_nothing_about_email_that_is_off(platform: Path, logged: list, monkeypatch: pytest.MonkeyPatch, variables: dict, public_url: str | None) -> None:
    """EMK-015 — contract 7: no host — even with the other variables set, an invalid TLS mode and a ``LIBREFOLIO_PUBLIC_URL`` that is not http(s) included —: no email record, and no record holds the SMTP password.

    Barrier first: the audit logged the platform's unset JWT secret, so the recorder hears it and «no email record» is
    an absence, not a deaf recorder.
    """
    print_section(f"EMK-015: email off at startup, {sorted(variables)}, LIBREFOLIO_PUBLIC_URL={public_url!r}")
    _configure(monkeypatch, variables)
    if public_url is not None:
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)

    config_audit.log_configuration_audit()

    assert any(fields.get("check") == "platform.jwt_secret" for _, _, fields in logged), f"barrier: the audit's record of the unset JWT secret must reach the recorder: {logged}"
    assert _email_records(logged) == [], f"email off is the default: nothing to log about it: {logged}"
    assert SMTP_PASSWORD not in repr(logged), "the startup audit logged the SMTP password"
    print_success("nothing logged about email")


@pytest.mark.parametrize(
    ("public_url", "level", "key"),
    [
        pytest.param(None, "info", "email.checks.links.missing", id="unset-info"),
        pytest.param(NOT_A_PUBLIC_URL, "warning", "email.checks.links.invalid", id="not-http-warning"),
    ],
)
def test_the_startup_audit_says_when_email_works_without_its_links(platform: Path, logged: list, monkeypatch: pytest.MonkeyPatch, public_url: str | None, level: str, key: str) -> None:
    """EMK-017 — contract 7: usable email (``starttls`` to a public host, credentials set) and ``LIBREFOLIO_PUBLIC_URL`` unset or not http(s): ``log_configuration_audit()`` returns after one email record, the ``level`` of ``email.links`` with the check's summary and its empty detail; nothing about ``email.smtp`` nor ``email.smtp_encryption``, both ok; no record holds the SMTP password nor the variable's value."""
    print_section(f"EMK-017: links {key.rsplit('.', 1)[-1]} at startup")
    _configure(monkeypatch, {**BASE, **CREDENTIALS})
    if public_url is not None:
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)

    returned = config_audit.log_configuration_audit()

    expected = check_email_links()
    assert (expected.severity, expected.i18n_key) == (level, key), f"precondition: the links must be {key}: {expected}"
    assert returned is None
    assert _email_records(logged) == [_as_logged(expected)], f"one {level} record of email.links, nothing about the configuration nor the encryption: {logged}"
    assert SMTP_PASSWORD not in repr(logged) and "zq-not-public" not in repr(logged), f"the startup audit logged the SMTP password or the variable's value: {logged}"
    print_success(f"{level}: {expected.summary}")


# =============================================================================
# 8. check_email_links
# =============================================================================


@pytest.mark.parametrize(
    ("variables", "public_url", "severity", "key"),
    [
        pytest.param({}, None, "ok", "email.checks.links.ok", id="email-off-links-unset"),
        pytest.param({}, NOT_A_PUBLIC_URL, "ok", "email.checks.links.ok", id="email-off-links-invalid"),
        pytest.param({}, PUBLIC_URL, "ok", "email.checks.links.ok", id="email-off-links-ready"),
        pytest.param({**BASE, "tls": "ssl"}, None, "ok", "email.checks.links.ok", id="email-invalid-links-unset"),
        pytest.param({**BASE, "tls": "ssl"}, NOT_A_PUBLIC_URL, "ok", "email.checks.links.ok", id="email-invalid-links-invalid"),
        pytest.param(BASE, PUBLIC_URL, "ok", "email.checks.links.ok", id="email-usable-links-ready"),
        pytest.param(BASE, f"{PUBLIC_URL}/", "ok", "email.checks.links.ok", id="email-usable-links-ready-trailing-slash"),
        pytest.param(BASE, None, "info", "email.checks.links.missing", id="email-usable-links-unset"),
        pytest.param(BASE, "   ", "info", "email.checks.links.missing", id="email-usable-links-blank"),
        pytest.param(BASE, NOT_A_PUBLIC_URL, "warning", "email.checks.links.invalid", id="email-usable-links-not-http"),
        pytest.param(BASE, "zq-not-public.example.com", "warning", "email.checks.links.invalid", id="email-usable-links-without-a-scheme"),
        pytest.param(BASE, "https://", "warning", "email.checks.links.invalid", id="email-usable-links-the-scheme-alone"),
        pytest.param(BASE, "https://folio.zq-space.example.com/my folio", "warning", "email.checks.links.invalid", id="email-usable-links-a-space-inside"),
        pytest.param(BASE, "https://folio.zq-query.example.com/app?lang=it", "warning", "email.checks.links.invalid", id="email-usable-links-a-query"),
        pytest.param(BASE, "https://folio.zq-fragment.example.com/app#top", "warning", "email.checks.links.invalid", id="email-usable-links-a-fragment"),
        pytest.param(BASE, "https://folio.zq-qmark.example.com/app?", "warning", "email.checks.links.invalid", id="email-usable-links-an-empty-query"),
        pytest.param(BASE, "https://zq-user:zq-secret@folio.example.com/app", "warning", "email.checks.links.invalid", id="email-usable-links-credentials"),
        pytest.param(BASE, "https://folio.zq-port.example.com:99999/app", "warning", "email.checks.links.invalid", id="email-usable-links-a-port-out-of-range"),
        pytest.param({}, "https://folio.zq-space.example.com/my folio", "ok", "email.checks.links.ok", id="email-off-links-a-space-inside"),
    ],
)
def test_the_links_check_in_each_state(monkeypatch: pytest.MonkeyPatch, variables: dict, public_url: str | None, severity: str, key: str) -> None:
    """EMK-016 — contract 8: ``check_email_links`` is ``ok`` when email is not usable — off or invalid —, whatever ``LIBREFOLIO_PUBLIC_URL`` says, and when links are ready; with usable email, ``info`` / ``missing`` for the variable unset or blank, ``warning`` / ``invalid`` for a value that is not http(s) or an http(s) address no link can start from (the scheme alone, a space inside, a query or a fragment — even an empty one —, credentials, a port out of range). Never a detail; a summary for the log when it speaks, naming the variable and never its value nor the SMTP host."""
    print_section(f"EMK-016: email {sorted(variables) or 'off'}, LIBREFOLIO_PUBLIC_URL={public_url!r}")
    _configure(monkeypatch, variables)
    if public_url is not None:
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)

    result = check_email_links()

    assert isinstance(result, ConfigCheck)
    assert (result.check_id, result.severity, result.i18n_key, result.detail) == ("email.links", severity, key, {}), result
    if severity != "ok":
        assert PUBLIC_URL_VARIABLE in result.summary, f"the summary must name the variable: {result.summary!r}"
        assert "zq-" not in result.summary, f"the summary names a configured value: {result.summary!r}"
    print_success(f"{result.severity} {result.i18n_key}")
