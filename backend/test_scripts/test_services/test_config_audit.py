"""
Configuration checks at startup (workstream H, platform, checkpoint CP3).

Under test: ``backend/app/services/platform/config_audit.py``. Each check reads the configuration and returns a
``ConfigCheck``: an id, a severity, the i18n key of its message for the admin interface, the parameters of that message
and an English summary for the log. ``log_configuration_audit()`` runs them at startup, from the lifespan of
``backend/app/services/platform/app_lifespan.py``. The contract:

(a) Every check in every state: id, severity, i18n key and detail. ``JWT_SECRET`` unset, empty or blank is only info (a
    new signing key at every start is the default), shorter than 32 characters a warning naming where the key comes from
    (``JWT_SECRET`` or ``JWT_SECRET_FILE (<path>)``), a ``JWT_SECRET_FILE`` that cannot be read an error; a secret set
    both as ``NAME`` and as ``NAME_FILE``, neither blank, a warning; an unusable instance key an error (a key file that
    cannot be reached included), a generated one open to group or others a warning; ``SESSION_COOKIE_SECURE=never`` a
    warning; a ``DEBUG`` or ``TRACE`` log level info. Every other state of these checks is ok; (f) and (g) give the
    states of the client address check and of the two managed switches.
(b) A check never puts a secret in its result: recognisable values for ``JWT_SECRET``, the instance key and the content
    of the secret files appear in no field of any result, in no log record and in no startup error, with the test mode
    check of (h) speaking beside them too (H-46).
(c) A check changes nothing: ``run_config_checks`` evaluates every check in the order of ``CONFIG_CHECKS``, leaves the
    environment as it was and generates no key file. ``CONFIG_CHECKS`` is the platform's checks (the two of (g) right
    after the client address check, the test mode check of (h) last), then workstream B's ``BACKUP_CONFIG_CHECKS``, then
    workstream A's ``ACCOUNTS_CONFIG_CHECKS``, then E's three, which end it; it holds no check without an id here (a new
    check comes with its tests), and each result carries the id of its check.
(d) ``log_configuration_audit``: a ``JWT_SECRET_FILE`` that cannot be read stops the start (``SecretFileError``), and so
    does a configured instance key that cannot be used (``InstanceKeyError``), since the admin asked for that source and
    the server must not start without it; nothing is logged first, and a blank ``NAME`` beside the file hides nothing. A
    generated key file gone bad, or one that cannot be reached, is logged as an error and the start goes on. Every check
    that is not ok is logged at the level of its severity, in order, with its id and detail; an ok check is not logged.
(e) The profile and the instance block (CP6). ``check_jwt_secret`` gives a short ``JWT_SECRET`` the severity of the
    profile: an error in ``managed``, a warning in ``selfhosted``. At startup, in ``managed``, a short key stops the start
    (``WeakSecretError``, a ``ValueError``) with a message naming its origin and length and never the key, nothing logged
    first; in ``selfhosted`` it is a warning and the start goes on. A ``LIBREFOLIO_BLOCKED`` or ``LIBREFOLIO_DELETION_DATE``
    that cannot be read stops the start (``ValueError`` naming the variable), blocked or not, nothing logged first. A
    blocked instance is logged as a warning carrying the deletion date (ISO, or ``None``) before the checks; an instance
    that is not blocked logs nothing about the block, a deletion date alone included.
(f) The client address check (H-36, decision N70). ``check_client_address`` reads what ``forwarded_by_untrusted_proxy``
    noted (``untrusted_forwarding_seen`` of ``backend/app/services/platform/client_address.py``) and changes nothing.
    Forwarding headers noted from a local peer are a warning, ``instance.checks.clientAddress.untrustedProxy``, whose
    summary is ``UNTRUSTED_PROXY_SUMMARY`` word for word: requests come through a reverse proxy LibreFolio does not trust,
    and the limits per client address skip them. Noted from a public peer only, they are info,
    ``instance.checks.clientAddress.publicForwarding``, summary ``PUBLIC_FORWARDING_SUMMARY``. The detail ``headers``
    lists the noted names in the order X-Forwarded-For, Forwarded, X-Real-IP, joined by ``", "``; when both classes are
    noted the warning wins, with the local names only. Nothing noted is ok, ``instance.checks.clientAddress.ok`` with no
    detail: the state at startup, since nothing is noted before the first request. The check runs right after
    ``check_session_cookie``. Its tests set what was noted with ``monkeypatch.setitem`` on ``_untrusted_forwarding``, put
    back after each test (H-22: no production reset). ``_configure`` starts every test with nothing noted (H-35),
    whatever another test of the same process left behind.
(g) The switches the managed profile turns on (H-39, security reviewer E after H-37). ``PROFILE_DEFAULTS`` gives the
    ``managed`` profile ``LIBREFOLIO_FRAME_PROTECTION`` and ``LIBREFOLIO_CSP_REPORT_ONLY`` on, while their code defaults
    are off: an entry lost from that table, or a hosting panel that switches one off by mistake, would silently leave a
    managed instance without that protection. Nothing switches them back on at runtime; two checks show it instead, in
    the startup log and in the admin's security checks. ``check_frame_protection`` (``platform.frame_protection``) reads
    ``get_settings()``: the switch on is ok, ``instance.checks.frameProtection.on``, whatever the profile; off in the
    ``managed`` profile, a warning, ``instance.checks.frameProtection.offManaged``, whose summary is this file's
    ``FRAME_PROTECTION_OFF_MANAGED`` word for word; off otherwise (``selfhosted``, the profile unset included), ok,
    ``instance.checks.frameProtection.offSelfHosted``. ``check_csp_report_only`` (``platform.csp_report_only``) is the
    same on ``LIBREFOLIO_CSP_REPORT_ONLY``, with ``instance.checks.cspReportOnly.on``, ``.offManaged`` and
    ``.offSelfHosted``, but off in ``managed`` it is info, summary ``CSP_REPORT_ONLY_OFF_MANAGED``. The detail is empty
    in every state. A switch is read as ``Settings`` reads it (``true``/``false``, ``1``/``0``, ``yes``/``no``,
    ``on``/``off``, in any case), and so is the profile (``MANAGED`` and `` Managed `` are ``managed``); in ``managed``
    a switch left unset takes the profile's default, on, so its check is ok with its ``.on`` key. The managed
    expectation is written in the checks, not read from ``PROFILE_DEFAULTS``: read from the table, a lost entry would
    change the expectation along with the value, and the check would stay ok on the very instance it is for. One test
    removes such an entry with ``monkeypatch.delitem``, put back after it. A check changes nothing: no variable, no
    entry of the table, no file. Both run right after ``check_client_address``, frame protection first, then the
    report-only policy, before ``check_log_level``. At startup, in ``managed`` with both switches off, the warning then
    the info are logged, in that order, and the start goes on; self-hosted with both off, its default, logs neither.
(h) Test mode outside a test lane (H-46). A test lane always owns ``LIBREFOLIO_TEST_LANE_ID``
    (``scripts/cli_base.configure_test_runtime``) and ``dev.py server`` turns test mode off, but the Docker image starts
    uvicorn itself: a ``LIBREFOLIO_TEST_MODE`` left on in a container's environment serves the test-only providers, keeps
    the data in the test data directory and stops ``.env`` from being read. ``check_test_mode`` (``platform.test_mode``)
    gives the same result in every profile. Test mode off, as ``is_test_mode()`` reads it (unset, ``0``, ``on``, `` 1``
    included), is ok, ``instance.checks.testMode.off``, whatever the lane id holds; on in a test lane, ok,
    ``instance.checks.testMode.testLane``; on outside one — the lane id unset, empty or blank, or, since H-49, out of the
    bounds of (i) —, an error, ``instance.checks.testMode.outsideTestLane``, whose detail ``data_dir`` is the test data
    directory (``get_data_dir()``) and whose summary is ``TEST_MODE_OUTSIDE_LANE_SUMMARY`` filled with it. An ok state
    has no detail and no summary. The check runs last of the platform's, right after ``check_log_level``. At startup, in
    ``managed``, its error stops the start (``ManagedTestModeError``, a ``RuntimeError``, its message word for word)
    right after the short-key stop of (e), which stays first: before the block's warning, nothing logged first.
    Self-hosted, the profile unset included, it is logged as an error and the start goes on. ``_configure`` puts every
    test-mode configuration in this file's own lane, ``FAKE_LANE_ID``, and production in none, so no case depends on the
    runner's environment.
(i) The test lane id within the readiness probe's bounds (H-49). The runner makes the lane id with
    ``secrets.token_hex(16)``, 32 characters (``scripts/cli_base.ensure_test_lane_id``), and the readiness probe
    ``GET /api/v1/system/test-lane-health`` (``backend/app/api/v1/system/health.py``) takes a ``token`` of 16 to 128
    characters: a lane id the probe would refuse is no working lane. ``backend/app/config/platform.py`` holds the two
    bounds beside ``owning_test_lane_id()``, which stays the variable as set: ``TEST_LANE_ID_MIN_LENGTH``, 16, and
    ``TEST_LANE_ID_MAX_LENGTH``, 128; the ``Query`` of the probe's ``token`` takes the same values. Test mode on is in a
    test lane when the lane id, stripped, holds between the two bounds of characters, both included: 16 and 128
    characters are a lane, 15 and 129 are not, a 16-character id padded with spaces to 20 is one, a 15-character id
    padded to 20 is not. Out of the bounds the check is the error of (h), its detail and its summary as there, and a
    managed start stops with the ``ManagedTestModeError`` of (h), its message word for word, nothing logged first;
    within them the check is ok, ``testLane``, and a managed start goes on with nothing logged about test mode.
    ``FAKE_LANE_ID``, 30 characters, is within the bounds, so no case of (h) changes its outcome.

Pure: the data directory is in ``tmp_path``, every variable the checks read is set or removed through ``monkeypatch``
(environment values win over a ``.env``), the forwarding notes of (f) are emptied the same way, and the module's logger
is replaced by a recorder. No database, no server, no network, nothing written in the repository. A key file that cannot
be reached is set up in a production data directory in ``tmp_path`` (``LIBREFOLIO_TEST_MODE=0``): in test mode the guard
of test roots stops on it first, by a rule of its own. The names H-46 adds to the module (``check_test_mode``,
``ManagedTestModeError``, ``TEST_MODE_OUTSIDE_LANE_SUMMARY``) are read by name, with ``getattr``, in the tests that need
them (``_h46``), as ``test_managed_headers.py`` reads H-42's ``PAGE_POLICY``: before H-46 those tests fail naming it,
while every other test still collects and runs. So are the two bounds H-49 adds to ``backend/app/config/platform.py``
(``_h49``). The probe's own bounds are read from the ``Annotated`` metadata of the ``token`` parameter of
``test_lane_health``, imported and never called, so no request is made: FastAPI's ``Query`` is a pydantic ``FieldInfo``,
which keeps ``min_length`` and ``max_length`` as ``annotated_types.MinLen`` and ``MaxLen``.
"""

from __future__ import annotations

import errno
import os
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, get_args, get_origin, get_type_hints

import pytest
from annotated_types import MaxLen, MinLen
from fastapi import params as fastapi_params

from backend.app.api.v1.system import health as health_api
from backend.app.config import PROFILE_DEFAULTS, SECRET_FILE_MAX_BYTES, SecretFileError, get_data_dir, get_settings, is_test_mode
from backend.app.config import platform as platform_config
from backend.app.config.platform import instance_blocked
from backend.app.services.accounts.checks import ACCOUNTS_CONFIG_CHECKS, check_login_limit
from backend.app.services.email.checks import EMAIL_CONFIG_CHECKS, check_email_links, check_smtp_configuration, check_smtp_encryption
from backend.app.services.platform import config_audit
from backend.app.services.platform.client_address import PUBLIC_FORWARDING_SUMMARY, UNTRUSTED_PROXY_SUMMARY, _untrusted_forwarding
from backend.app.services.platform.config_audit import (
    CONFIG_CHECKS,
    JWT_SECRET_MIN_LENGTH,
    ConfigCheck,
    WeakSecretError,
    check_client_address,
    check_csp_report_only,
    check_frame_protection,
    check_instance_key,
    check_jwt_secret,
    check_log_level,
    check_secrets_set_twice,
    check_session_cookie,
    log_configuration_audit,
    run_config_checks,
)
from backend.app.services.platform.instance_backup.checks import BACKUP_CONFIG_CHECKS, check_panel_token, check_restore_limit, check_upload_limit
from backend.app.services.platform.instance_key import INSTANCE_KEY_FILE, InstanceKeyError, derive_key, instance_key_path
from backend.test_scripts.test_utils import print_section, print_success

POSIX = os.name != "nt"
needs_posix_modes = pytest.mark.skipif(not POSIX, reason="file modes are POSIX only")
needs_permission_checks = pytest.mark.skipif(not POSIX or os.geteuid() == 0, reason="needs POSIX permissions, which root bypasses")
needs_posix_paths = pytest.mark.skipif(not POSIX, reason="Windows reports a path below a file as missing, not as ENOTDIR")

#: H-46: the test mode check of (h), read by name so that this file collects before the module has it. ``None`` until
#: then: ``CHECK_IDS`` leaves it out, and the tests of its place, in (c) and (h), fail naming H-46 (``_h46``).
_TEST_MODE_CHECK: Callable[[], ConfigCheck] | None = getattr(config_audit, "check_test_mode", None)

#: The id of every check, in the order of ``CONFIG_CHECKS`` (c): the platform's, then workstream B's, A's and E's.
CHECK_IDS: dict[Callable[[], ConfigCheck], str] = {
    check_jwt_secret: "platform.jwt_secret",
    check_secrets_set_twice: "platform.secrets_set_twice",
    check_instance_key: "platform.instance_key",
    check_session_cookie: "platform.session_cookie",
    check_client_address: "platform.client_address",
    check_frame_protection: "platform.frame_protection",
    check_csp_report_only: "platform.csp_report_only",
    check_log_level: "platform.log_level",
    # H-46: the platform's last check, right after the log level's; left out while the module has no check_test_mode
    **({_TEST_MODE_CHECK: "platform.test_mode"} if _TEST_MODE_CHECK is not None else {}),
    check_panel_token: "backup.panel_token",
    check_upload_limit: "backup.upload_limit",
    check_restore_limit: "backup.restore_limit",
    check_login_limit: "accounts.login_limit",
    check_smtp_configuration: "email.smtp",
    check_smtp_encryption: "email.smtp_encryption",
    check_email_links: "email.links",
}
SEVERITIES = ("ok", "info", "warning", "error")
I18N_PREFIX = "instance.checks."

GOOD_JWT_SECRET = "jwt-signing-key-of-a-careful-admin-0123456789"
GOOD_INSTANCE_KEY = "instance-key-of-a-careful-admin-0123456789"
#: Marks every secret of the leak tests: no field of a result, no log record, no startup error may contain it.
CANARY = "Zq7canary"
#: H-46: the lane of every test-mode configuration here (``_configure``), so that no case depends on the runner's
#: environment; clearly fake, and not the 32 hexadecimal characters ``ensure_test_lane_id()`` makes. H-49: 30
#: characters, within the bounds of (i), so it stays a lane.
FAKE_LANE_ID = "h46-fake-lane-0123456789abcdef"
#: H-46: the names the module gains, each with what it is, for the message of a test that reads one before it exists.
H46_NAMES = {
    "check_test_mode": "the check of LIBREFOLIO_TEST_MODE outside a test lane (platform.test_mode), the platform's last check, right after check_log_level",
    "ManagedTestModeError": "the RuntimeError that stops a managed start with LIBREFOLIO_TEST_MODE on outside a test lane, right after the short-key stop",
    "TEST_MODE_OUTSIDE_LANE_SUMMARY": "the summary of check_test_mode outside a test lane, with the data directory as {data_dir}",
}
#: H-49: the bounds ``backend/app/config/platform.py`` gains beside ``owning_test_lane_id()``, each with what it is, for
#: the message of a test that reads one before it exists.
H49_NAMES = {
    "TEST_LANE_ID_MIN_LENGTH": "the fewest characters of a LIBREFOLIO_TEST_LANE_ID, once stripped, that make a test lane: 16, the min_length of the token of GET /api/v1/system/test-lane-health",
    "TEST_LANE_ID_MAX_LENGTH": "the most characters of a LIBREFOLIO_TEST_LANE_ID, once stripped, that make a test lane: 128, the max_length of the token of GET /api/v1/system/test-lane-health",
}


@dataclass
class Configuration:
    """What one test configures: variables through ``monkeypatch``, files in ``tmp_path``, and its own data directory."""

    monkeypatch: pytest.MonkeyPatch
    tmp_path: Path
    data_dir: Path

    @property
    def key_file(self) -> Path:
        return self.data_dir / INSTANCE_KEY_FILE

    def set(self, **variables: str) -> None:
        for name, value in variables.items():
            self.monkeypatch.setenv(name, value)

    def file(self, name: str, content: bytes) -> Path:
        path = self.tmp_path / name
        path.write_bytes(content)
        return path

    def generated_key(self) -> Path:
        """Generate the key file as the first use of the instance key does."""
        derive_key("config.audit.v1")
        return self.key_file

    def damaged_key(self, content: bytes) -> Path:
        """A generated key file whose content went bad, in a folder and with a mode as generated."""
        self.key_file.parent.mkdir(mode=0o700, parents=True)
        self.key_file.write_bytes(content)
        self.key_file.chmod(0o600)
        return self.key_file


def _configure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, production: bool) -> Configuration:
    """No secret set either way, cookie ``auto``, log level ``INFO``, profile ``selfhosted``, frame protection and the report-only policy unset, not blocked, nothing noted about forwarding headers, no key yet, a data directory in ``tmp_path``.
    H-46: test mode in this file's own lane, ``FAKE_LANE_ID``, production in none, whatever the runner exported."""
    for variable in [name for name in os.environ if name.endswith("_FILE") and (name == "JWT_SECRET_FILE" or name.startswith("LIBREFOLIO_"))]:
        monkeypatch.delenv(variable)
    for variable in ("JWT_SECRET", "LIBREFOLIO_INSTANCE_KEY", "LIBREFOLIO_LOG_LEVEL", "LIBREFOLIO_DATA_DIR", "LIBREFOLIO_TEST_DATA_DIR", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_DELETION_DATE"):
        monkeypatch.delenv(variable, raising=False)
    # Workstream E: email off whatever the environment holds, so its three checks are ok
    for variable in [name for name in os.environ if name.startswith("LIBREFOLIO_SMTP_")]:
        monkeypatch.delenv(variable)
    # Workstream B: no panel token, no upload limit and no restore limit (B-35) whatever the environment holds, so its
    # three checks are ok
    for variable in ("LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN", "LIBREFOLIO_BACKUP_MAX_UPLOAD_MB", "LIBREFOLIO_BACKUP_MAX_RESTORE_MB"):
        monkeypatch.delenv(variable, raising=False)
    # Workstream A: the login limit on whatever the environment holds (the lane's server runs with it off), so its check
    # is ok and the variable cannot stop the audit
    monkeypatch.delenv("LIBREFOLIO_LOGIN_LIMIT", raising=False)
    # H-39: the two switches the managed profile turns on, unset whatever the environment holds, so the profile's default
    # decides them and no shell can switch one off under a managed case
    for variable in ("LIBREFOLIO_FRAME_PROTECTION", "LIBREFOLIO_CSP_REPORT_ONLY"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "0" if production else "1")
    # H-46: test mode in a lane of this file's own, production in none, whatever the runner exported, so the test mode
    # check is ok
    if production:
        monkeypatch.delenv("LIBREFOLIO_TEST_LANE_ID", raising=False)
    else:
        monkeypatch.setenv("LIBREFOLIO_TEST_LANE_ID", FAKE_LANE_ID)
    monkeypatch.setenv("LIBREFOLIO_DATA_DIR" if production else "LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "auto")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    # Set, not removed: a .env may name a profile, and the environment wins over it
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    # H-35: nothing noted about forwarding headers, whatever another test of this process left, so the client address
    # check is ok; monkeypatch puts the module's own sets back after the test
    monkeypatch.setitem(_untrusted_forwarding, "local", set())
    monkeypatch.setitem(_untrusted_forwarding, "public", set())
    configuration = Configuration(monkeypatch, tmp_path, (tmp_path / "data").resolve())
    assert instance_key_path() == configuration.key_file, f"the key file must live in the data directory of this test, not at {instance_key_path()}"
    return configuration


@pytest.fixture
def configuration(monkeypatch, tmp_path) -> Configuration:
    """Test mode, in a test lane: every check is ok but JWT_SECRET, which is unset (info)."""
    return _configure(monkeypatch, tmp_path, production=False)


@pytest.fixture
def production_configuration(monkeypatch, tmp_path) -> Configuration:
    """The same, on a production data directory in ``tmp_path``: the guard of test roots stays out of the way."""
    return _configure(monkeypatch, tmp_path, production=True)


class LogRecorder:
    """Stands in for the module's structlog logger: one ``(level, summary, fields)`` per call."""

    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict]] = []

    def info(self, event: str, **fields) -> None:
        self.records.append(("info", event, fields))

    def warning(self, event: str, **fields) -> None:
        self.records.append(("warning", event, fields))

    def error(self, event: str, **fields) -> None:
        self.records.append(("error", event, fields))


@pytest.fixture
def logged(monkeypatch) -> list[tuple[str, str, dict]]:
    recorder = LogRecorder()
    monkeypatch.setattr(config_audit, "logger", recorder)
    return recorder.records


def _assert_check(result: ConfigCheck, check: Callable[[], ConfigCheck], severity: str, message: str, detail: dict) -> None:
    """``result`` is the expected state of ``check``, and has what the admin interface and the log need. For the platform's checks only: ``message`` is a key under ``I18N_PREFIX``."""
    actual = (result.check_id, result.severity, result.i18n_key, result.detail)
    expected = (CHECK_IDS[check], severity, I18N_PREFIX + message, detail)
    assert actual == expected, f"{check.__name__}() must be {expected}, not {actual}"
    assert all(isinstance(value, str | int) for value in result.detail.values()), f"the parameters of an i18n message are strings or integers: {result.detail}"
    if severity != "ok":
        assert result.summary.strip(), f"{check.__name__}() is {severity} without a summary for the log"


def _h46(name: str) -> Any:
    """``config_audit.<name>``, a name H-46 adds, read when the test runs (as ``test_managed_headers.py`` reads H-42's ``PAGE_POLICY``): until the module has it, the test fails naming H-46, while the rest of this file collects and runs."""
    value = getattr(config_audit, name, None)
    assert value is not None, f"H-46: config_audit has no {name}, {H46_NAMES[name]}"
    return value


def _h49(name: str) -> Any:
    """``backend.app.config.platform.<name>``, a bound H-49 adds, read when the test runs, as ``_h46`` reads H-46's names: until the module has it, the test fails naming H-49, while the rest of this file collects and runs."""
    value = getattr(platform_config, name, None)
    assert value is not None, f"H-49: backend.app.config.platform has no {name}, {H49_NAMES[name]}"
    return value


# =============================================================================
# (a) Every check in every state
# =============================================================================


@pytest.mark.parametrize(
    ("check", "variables", "severity", "message", "detail"),
    [
        pytest.param(check_jwt_secret, {}, "info", "jwtSecret.ephemeral", {}, id="jwt-secret-unset"),
        pytest.param(check_jwt_secret, {"JWT_SECRET": ""}, "info", "jwtSecret.ephemeral", {}, id="jwt-secret-empty-is-unset"),
        pytest.param(check_jwt_secret, {"JWT_SECRET": "   "}, "info", "jwtSecret.ephemeral", {}, id="jwt-secret-blank-is-unset"),
        pytest.param(check_jwt_secret, {"JWT_SECRET": " " * 64}, "info", "jwtSecret.ephemeral", {}, id="jwt-secret-blank-of-any-length-is-unset"),
        pytest.param(check_jwt_secret, {"JWT_SECRET": "x" * 31}, "warning", "jwtSecret.short", {"source": "JWT_SECRET", "length": 31, "minimum": 32}, id="jwt-secret-31-characters"),
        pytest.param(check_jwt_secret, {"JWT_SECRET": "x" * 32}, "ok", "jwtSecret.ok", {}, id="jwt-secret-32-characters"),
        pytest.param(check_secrets_set_twice, {}, "ok", "secretsSetTwice.ok", {}, id="nothing-set-twice"),
        pytest.param(check_secrets_set_twice, {"JWT_SECRET": "   ", "JWT_SECRET_FILE": "/run/secrets/jwt"}, "ok", "secretsSetTwice.ok", {}, id="blank-name-beside-a-file-is-not-set-twice"),
        pytest.param(check_secrets_set_twice, {"JWT_SECRET": GOOD_JWT_SECRET, "JWT_SECRET_FILE": "/run/secrets/jwt"}, "warning", "secretsSetTwice.found", {"variables": "JWT_SECRET"}, id="jwt-secret-set-twice"),
        pytest.param(
            check_secrets_set_twice,
            {"LIBREFOLIO_INSTANCE_KEY": GOOD_INSTANCE_KEY, "LIBREFOLIO_INSTANCE_KEY_FILE": "/run/secrets/key", "JWT_SECRET": GOOD_JWT_SECRET, "JWT_SECRET_FILE": "/run/secrets/jwt"},
            "warning",
            "secretsSetTwice.found",
            {"variables": "JWT_SECRET, LIBREFOLIO_INSTANCE_KEY"},
            id="two-secrets-set-twice-sorted",
        ),
        pytest.param(check_instance_key, {}, "ok", "instanceKey.ok", {"source": "not_created"}, id="instance-key-not-created-yet"),
        pytest.param(check_instance_key, {"LIBREFOLIO_INSTANCE_KEY": GOOD_INSTANCE_KEY}, "ok", "instanceKey.ok", {"source": "configured"}, id="instance-key-configured"),
        pytest.param(
            check_instance_key,
            {"LIBREFOLIO_INSTANCE_KEY": "short-key"},
            "error",
            "instanceKey.unusable",
            {"source": "configured", "reason": "LIBREFOLIO_INSTANCE_KEY: the instance key is 9 characters long, it needs at least 32"},
            id="instance-key-configured-too-short",
        ),
        pytest.param(check_session_cookie, {"SESSION_COOKIE_SECURE": "never"}, "warning", "sessionCookie.never", {}, id="session-cookie-never"),
        pytest.param(check_session_cookie, {"SESSION_COOKIE_SECURE": " NEVER "}, "warning", "sessionCookie.never", {}, id="session-cookie-never-in-any-case"),
        pytest.param(check_session_cookie, {"SESSION_COOKIE_SECURE": "auto"}, "ok", "sessionCookie.ok", {}, id="session-cookie-auto"),
        pytest.param(check_session_cookie, {"SESSION_COOKIE_SECURE": "always"}, "ok", "sessionCookie.ok", {}, id="session-cookie-always"),
        pytest.param(check_log_level, {"LOG_LEVEL": "DEBUG"}, "info", "logLevel.verbose", {"log_level": "DEBUG"}, id="log-level-debug"),
        pytest.param(check_log_level, {"LOG_LEVEL": "debug"}, "info", "logLevel.verbose", {"log_level": "DEBUG"}, id="log-level-debug-in-any-case"),
        pytest.param(check_log_level, {"LOG_LEVEL": "TRACE"}, "info", "logLevel.verbose", {"log_level": "TRACE"}, id="log-level-trace"),
        pytest.param(check_log_level, {"LOG_LEVEL": "INFO"}, "ok", "logLevel.ok", {}, id="log-level-info"),
        pytest.param(check_log_level, {"LOG_LEVEL": "WARNING"}, "ok", "logLevel.ok", {}, id="log-level-warning"),
        pytest.param(check_log_level, {"LOG_LEVEL": "INFO", "LIBREFOLIO_LOG_LEVEL": "debug"}, "info", "logLevel.verbose", {"log_level": "DEBUG"}, id="log-level-debug-from-librefolio-log-level"),
        pytest.param(check_log_level, {"LOG_LEVEL": "DEBUG", "LIBREFOLIO_LOG_LEVEL": "info"}, "ok", "logLevel.ok", {}, id="log-level-librefolio-log-level-wins"),
    ],
)
def test_a_check_in_each_of_its_states(configuration, check, variables, severity, message, detail):
    """(a) The states a variable alone decides."""
    configuration.set(**variables)
    result = check()
    _assert_check(result, check, severity, message, detail)
    print_success(f"{check.__name__} with {sorted(variables)}: {severity} {result.i18n_key}")


@pytest.mark.parametrize(
    ("jwt_secret", "content", "severity", "message", "detail"),
    [
        pytest.param(None, b"y" * 64 + b"\n", "ok", "jwtSecret.ok", {}, id="from-the-file"),
        pytest.param("   ", b"y" * 64 + b"\n", "ok", "jwtSecret.ok", {}, id="a-blank-variable-falls-through-to-the-file"),
        pytest.param(None, b"short-from-the-file\n", "warning", "jwtSecret.short", {"source": "JWT_SECRET_FILE (<file>)", "length": 19, "minimum": 32}, id="short-from-the-file"),
        pytest.param("   ", b"short-from-the-file\n", "warning", "jwtSecret.short", {"source": "JWT_SECRET_FILE (<file>)", "length": 19, "minimum": 32}, id="short-from-the-file-beside-a-blank-variable"),
        pytest.param(None, None, "error", "jwtSecret.unreadable", {"reason": "JWT_SECRET_FILE: <file> does not exist"}, id="file-missing"),
        pytest.param("   ", None, "error", "jwtSecret.unreadable", {"reason": "JWT_SECRET_FILE: <file> does not exist"}, id="a-blank-variable-hides-no-broken-file"),
        pytest.param(None, b"\n", "error", "jwtSecret.unreadable", {"reason": "JWT_SECRET_FILE: <file> is empty or blank"}, id="file-empty"),
        pytest.param(None, b"   \n", "error", "jwtSecret.unreadable", {"reason": "JWT_SECRET_FILE: <file> is empty or blank"}, id="file-blank"),
        pytest.param("x" * 32, None, "ok", "jwtSecret.ok", {}, id="the-variable-wins-over-a-broken-file"),
    ],
)
def test_check_jwt_secret_with_jwt_secret_file(configuration, jwt_secret, content, severity, message, detail):
    """(a) The secret of JWT_SECRET_FILE is checked like the variable, which a blank value does not hide; a file that cannot be read is an error naming it."""
    secret_file = configuration.tmp_path / "jwt-secret" if content is None else configuration.file("jwt-secret", content)
    configuration.set(JWT_SECRET_FILE=str(secret_file))
    if jwt_secret is not None:
        configuration.set(JWT_SECRET=jwt_secret)
    detail = {name: value.replace("<file>", str(secret_file)) if isinstance(value, str) else value for name, value in detail.items()}

    result = check_jwt_secret()

    _assert_check(result, check_jwt_secret, severity, message, detail)
    print_success(f"JWT_SECRET={jwt_secret!r}, JWT_SECRET_FILE {content!r:.30}: {severity} {result.i18n_key}")


@pytest.mark.parametrize("source", ["variable", "file"])
def test_the_summary_of_a_short_jwt_secret_names_where_it_comes_from(configuration, source):
    """(a) The log line of a short signing key says where the admin set it: the variable, or the file variable with its path."""
    if source == "variable":
        configuration.set(JWT_SECRET="x" * 20)
        origin = "JWT_SECRET"
    else:
        secret_file = configuration.file("jwt-secret", b"x" * 20 + b"\n")
        configuration.set(JWT_SECRET_FILE=str(secret_file))
        origin = f"JWT_SECRET_FILE ({secret_file})"

    summary = check_jwt_secret().summary

    expected = f"The session signing key from {origin} is 20 characters long: use at least 32 random characters"
    assert summary == expected, f"the summary of a short JWT secret must name its origin:\n  expected {expected!r}\n  got      {summary!r}"
    print_success(summary)


def test_check_instance_key_of_a_generated_key(configuration):
    """(a) A generated key, as generated: ok, from the generated source."""
    configuration.generated_key()
    _assert_check(check_instance_key(), check_instance_key, "ok", "instanceKey.ok", {"source": "generated"})
    print_success("generated key: ok")


@pytest.mark.parametrize(
    ("damage", "reason"),
    [
        pytest.param(b"", "instance key file: <file> is empty or blank", id="empty"),
        pytest.param(b" " * 40 + b"\n", "instance key file: <file> is empty or blank", id="blank"),
        pytest.param(b"too-short-key\n", "<file>: the instance key is 13 characters long, it needs at least 32", id="too-short"),
    ],
)
def test_check_instance_key_of_a_damaged_generated_key(configuration, damage, reason):
    """(a) A generated key file gone bad is an error, with the reason naming the file; the file is left as it is."""
    key_file = configuration.damaged_key(damage)
    _assert_check(check_instance_key(), check_instance_key, "error", "instanceKey.unusable", {"source": "generated", "reason": reason.replace("<file>", str(key_file))})
    assert key_file.read_bytes() == damage, "a check must not touch the key file"
    print_success(f"damaged key file {damage!r}: error")


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        pytest.param(None, "LIBREFOLIO_INSTANCE_KEY_FILE: <file> does not exist", id="missing"),
        pytest.param(b"short-key\n", "LIBREFOLIO_INSTANCE_KEY_FILE (<file>): the instance key is 9 characters long, it needs at least 32", id="too-short"),
    ],
)
def test_check_instance_key_of_a_key_file_variable_that_cannot_be_used(configuration, content, reason):
    """(a) A configured LIBREFOLIO_INSTANCE_KEY_FILE missing or too short: an error from the configured source, naming the file."""
    key_file = configuration.tmp_path / "instance-key" if content is None else configuration.file("instance-key", content)
    configuration.set(LIBREFOLIO_INSTANCE_KEY_FILE=str(key_file))
    _assert_check(check_instance_key(), check_instance_key, "error", "instanceKey.unusable", {"source": "configured", "reason": reason.replace("<file>", str(key_file))})
    print_success(f"LIBREFOLIO_INSTANCE_KEY_FILE {content!r}: error")


@pytest.mark.parametrize(
    "shape",
    [
        pytest.param("unsearchable-secrets-folder", marks=needs_permission_checks),
        pytest.param("secrets-is-a-file", marks=needs_posix_paths),
    ],
)
def test_a_key_file_that_cannot_be_reached_is_an_error_and_the_start_goes_on(production_configuration, logged, shape):
    """(a)(d) The key may be there but the server cannot reach it: the check is an error, logged at startup, which goes on."""
    configuration = production_configuration
    if shape == "unsearchable-secrets-folder":
        configuration.generated_key()
        configuration.key_file.parent.chmod(0o000)
        reason = f"{configuration.key_file}: the instance key cannot be reached ({os.strerror(errno.EACCES)})"
    else:
        configuration.data_dir.mkdir()
        (configuration.data_dir / "secrets").write_bytes(b"a file where the key folder should be\n")
        reason = f"{configuration.key_file}: the instance key cannot be reached ({os.strerror(errno.ENOTDIR)})"
    try:
        result = check_instance_key()
        log_configuration_audit()
    finally:
        if shape == "unsearchable-secrets-folder":
            configuration.key_file.parent.chmod(0o700)

    _assert_check(result, check_instance_key, "error", "instanceKey.unusable", {"source": "generated", "reason": reason})
    errors = [(fields["check"], fields["detail"]) for level, _, fields in logged if level == "error"]
    assert errors == [("platform.instance_key", {"source": "generated", "reason": reason})], f"an unreachable key file must be logged once as an error, and the start go on: {logged}"
    print_success(f"{shape}: error logged, the start went on")


@needs_posix_modes
def test_check_instance_key_of_a_generated_key_open_to_others(configuration):
    """(a) A usable generated key in a folder or file group and others can reach: a warning with the modes and the path."""
    key_file = configuration.generated_key()
    key_file.chmod(0o644)
    key_file.parent.chmod(0o755)
    try:
        result = check_instance_key()
    finally:
        key_file.parent.chmod(0o700)
        key_file.chmod(0o600)
    _assert_check(result, check_instance_key, "warning", "instanceKey.permissions", {"path": str(key_file), "directory": "0755", "file": "0644"})
    print_success(f"open key file: {result.summary}")


# =============================================================================
# (b) No secret in any result
# =============================================================================


def _secrets_in_the_variables(configuration: Configuration) -> list[str]:
    """Too-short secrets set both ways: warned about by length and by name only."""
    secrets = [f"jwt-{CANARY}", f"jwt-file-{CANARY}", f"key-{CANARY}", f"key-file-{CANARY}"]
    configuration.set(
        JWT_SECRET=secrets[0],
        JWT_SECRET_FILE=str(configuration.file("jwt-secret", secrets[1].encode() + b"\n")),
        LIBREFOLIO_INSTANCE_KEY=secrets[2],
        LIBREFOLIO_INSTANCE_KEY_FILE=str(configuration.file("instance-key", secrets[3].encode() + b"\n")),
    )
    return secrets


def _secrets_in_files_that_cannot_be_read(configuration: Configuration) -> list[str]:
    """Secret files too large or not UTF-8: refused without being read out."""
    secrets = [f"jwt-file-{CANARY}", f"key-file-{CANARY}"]
    too_large = (secrets[0] * (SECRET_FILE_MAX_BYTES // len(secrets[0]) + 1)).encode()[: SECRET_FILE_MAX_BYTES + 1]
    configuration.set(
        JWT_SECRET_FILE=str(configuration.file("jwt-secret", too_large)),
        LIBREFOLIO_INSTANCE_KEY_FILE=str(configuration.file("instance-key", secrets[1].encode() + b"\xff\xfe")),
    )
    return secrets


def _secret_in_a_damaged_key_file(configuration: Configuration) -> list[str]:
    """A generated key file holding a key too short: an error by length only."""
    secret = f"generated-{CANARY}"
    configuration.damaged_key(secret.encode() + b"\n")
    return [secret]


def _generated_key_open_to_others(configuration: Configuration) -> list[str]:
    """A usable generated key in a loose folder: a warning naming the path and the modes, never the key."""
    key_file = configuration.generated_key()
    if POSIX:
        key_file.parent.chmod(0o755)
    return [key_file.read_text(encoding="ascii").rstrip("\n")]


def _damaged_key_file_outside_a_test_lane(configuration: Configuration) -> list[str]:
    """H-46: the damaged generated key, with test mode on outside a test lane: the test mode check speaks too, naming a path, and the start goes on, so its log is read as well."""
    configuration.monkeypatch.delenv("LIBREFOLIO_TEST_LANE_ID", raising=False)
    return _secret_in_a_damaged_key_file(configuration)


@pytest.mark.parametrize(
    "configure",
    [
        pytest.param(_secrets_in_the_variables, id="short-secrets-set-both-ways"),
        pytest.param(_secrets_in_files_that_cannot_be_read, id="files-that-cannot-be-read"),
        pytest.param(_secret_in_a_damaged_key_file, id="damaged-generated-key"),
        pytest.param(_generated_key_open_to_others, id="generated-key-open-to-others"),
        pytest.param(_damaged_key_file_outside_a_test_lane, id="damaged-generated-key-outside-a-test-lane"),
    ],
)
def test_no_secret_value_reaches_a_result_a_log_record_or_a_startup_error(configuration, logged, configure):
    """(b) Results, log records and the error that stops the start name variables, paths, lengths and modes; never a secret."""
    secrets = configure(configuration)
    try:
        results = run_config_checks()
        try:
            log_configuration_audit()
            startup = repr(logged)
        except (SecretFileError, InstanceKeyError) as exc:
            startup = "".join(traceback.format_exception(exc))
    finally:
        if configuration.key_file.exists():
            configuration.key_file.parent.chmod(0o700)

    flagged = [result.check_id for result in results if result.severity != "ok"]
    assert flagged, "the configuration must make some check speak, or the absence of secrets proves nothing"
    leaks = [f"{result.check_id}: {secret}" for result in results for secret in secrets if secret in repr(result)]
    assert not leaks, f"a configuration check put a secret in its result: {leaks}"
    shown = [secret for secret in secrets if secret in startup]
    assert not shown, f"the startup audit showed a secret in its log or its error: {shown}"
    print_success(f"{len(secrets)} secret(s) behind {flagged}: none shown")


# =============================================================================
# (c) run_config_checks
# =============================================================================


def test_run_config_checks_evaluates_every_check_in_order_and_changes_nothing(configuration):
    """(c) The order of CONFIG_CHECKS, each result what the check alone returns, the test mode check's right after the log level's (H-46); no variable changed, no key generated. Which checks CONFIG_CHECKS holds, where, with which ids: the next test."""
    print_section("Configuration checks: run_config_checks")
    environment = dict(os.environ)

    results = run_config_checks()

    assert results == [check() for check in CONFIG_CHECKS], "run_config_checks must return what each check returns on its own, in the order of CONFIG_CHECKS"
    ids = [result.check_id for result in results]
    log_level = ids.index("platform.log_level")
    assert ids[log_level + 1 : log_level + 2] == ["platform.test_mode"], f"H-46: run_config_checks must evaluate the test mode check, platform.test_mode, right after the log level check, last of the platform's: {ids}"
    assert all(result.severity in SEVERITIES for result in results), f"unknown severity in {results}"
    assert dict(os.environ) == environment, "a configuration check changed the environment"
    assert not configuration.data_dir.exists(), f"a configuration check created files: {list(configuration.data_dir.rglob('*'))}"
    print_success(f"{len(results)} checks in order, nothing changed")


def test_config_checks_holds_every_check_in_its_place_with_its_id(configuration):
    """(c) ``CONFIG_CHECKS`` is the platform's checks, the test mode check last (H-46), then workstream B's ``BACKUP_CONFIG_CHECKS``, then workstream A's ``ACCOUNTS_CONFIG_CHECKS``, then E's three, which end it (``test_email_checks.py``, EMK-010); it holds every check with an id here, in the order of ``CHECK_IDS``, and no other — a new check comes with its tests —; ``run_config_checks`` gives each result the id of its check."""
    print_section("Configuration checks: CONFIG_CHECKS whole")
    # H-46: CHECK_IDS holds the test mode check, the platform's last, only once the module has it
    _h46("check_test_mode")
    sections = (*BACKUP_CONFIG_CHECKS, *ACCOUNTS_CONFIG_CHECKS, *EMAIL_CONFIG_CHECKS)
    platform = tuple(check for check in CHECK_IDS if check not in sections)

    results = run_config_checks()

    names = [check.__name__ for check in CONFIG_CHECKS]
    assert tuple(CONFIG_CHECKS) == (*platform, *BACKUP_CONFIG_CHECKS, *ACCOUNTS_CONFIG_CHECKS, *EMAIL_CONFIG_CHECKS), f"CONFIG_CHECKS must be the platform's checks, then B's BACKUP_CONFIG_CHECKS, then A's ACCOUNTS_CONFIG_CHECKS, then E's three email checks: {names}"
    missing = [check.__name__ for check in CHECK_IDS if check not in CONFIG_CHECKS]
    untested = [check.__name__ for check in CONFIG_CHECKS if check not in CHECK_IDS]
    assert tuple(CONFIG_CHECKS) == tuple(CHECK_IDS), f"CONFIG_CHECKS must hold every check with an id here, in the order of CHECK_IDS, and no other: missing {missing}; without an id here, give it its tests: {untested}; CONFIG_CHECKS is {names}"
    assert [result.check_id for result in results] == list(CHECK_IDS.values()), f"each result must carry the id of its check: {[result.check_id for result in results]}"
    print_success(f"{len(results)} checks in their places: {', '.join(names)}")


# =============================================================================
# (d) log_configuration_audit
# =============================================================================


@pytest.mark.parametrize("jwt_secret", [pytest.param(None, id="jwt-secret-unset"), pytest.param("   ", id="jwt-secret-blank")])
@pytest.mark.parametrize(
    ("content", "problem"),
    [
        pytest.param(None, "does not exist", id="missing"),
        pytest.param(b"", "is empty or blank", id="empty"),
        pytest.param(b"\xff\xfe", "is not UTF-8 text", id="not-utf8"),
    ],
)
def test_startup_stops_on_a_jwt_secret_file_that_cannot_be_read(configuration, logged, content, problem, jwt_secret):
    """(d) The admin asked for that file: without it the server must not start with a signing key of its own, a blank JWT_SECRET beside it or not."""
    secret_file = configuration.tmp_path / "jwt-secret" if content is None else configuration.file("jwt-secret", content)
    configuration.set(JWT_SECRET_FILE=str(secret_file))
    if jwt_secret is not None:
        configuration.set(JWT_SECRET=jwt_secret)

    with pytest.raises(SecretFileError) as raised:
        log_configuration_audit()

    assert str(raised.value) == f"JWT_SECRET_FILE: {secret_file} {problem}", f"the startup error must name JWT_SECRET_FILE, the path and the problem: {raised.value}"
    assert logged == [], f"nothing is logged before the start is stopped: {logged}"
    print_success(f"start stopped: {raised.value}")


@pytest.mark.parametrize(
    ("variables", "problem"),
    [
        pytest.param({"LIBREFOLIO_INSTANCE_KEY": "short-key"}, "LIBREFOLIO_INSTANCE_KEY: the instance key is 9 characters long, it needs at least 32", id="key-too-short"),
        pytest.param({"LIBREFOLIO_INSTANCE_KEY_FILE": "<short file>"}, "LIBREFOLIO_INSTANCE_KEY_FILE (<short file>): the instance key is 9 characters long, it needs at least 32", id="key-file-too-short"),
        pytest.param({"LIBREFOLIO_INSTANCE_KEY_FILE": "<missing file>"}, "LIBREFOLIO_INSTANCE_KEY_FILE: <missing file> does not exist", id="key-file-missing"),
        pytest.param({"LIBREFOLIO_INSTANCE_KEY": "   ", "LIBREFOLIO_INSTANCE_KEY_FILE": "<missing file>"}, "LIBREFOLIO_INSTANCE_KEY_FILE: <missing file> does not exist", id="key-file-missing-beside-a-blank-key"),
    ],
)
def test_startup_stops_on_a_configured_instance_key_that_cannot_be_used(configuration, logged, variables, problem):
    """(d) A configured key the server cannot use stops the start: generating another would encrypt with the wrong key."""
    files = {"<short file>": str(configuration.file("short-instance-key", b"short-key\n")), "<missing file>": str(configuration.tmp_path / "missing-instance-key")}
    configuration.set(**{name: files.get(value, value) for name, value in variables.items()})
    for placeholder, path in files.items():
        problem = problem.replace(placeholder, path)

    with pytest.raises(InstanceKeyError) as raised:
        log_configuration_audit()

    assert str(raised.value) == problem, f"the startup error must say which source and why:\n  expected {problem!r}\n  got      {raised.value!r}"
    assert logged == [], f"nothing is logged before the start is stopped: {logged}"
    assert not configuration.data_dir.exists(), "a configured key that cannot be used must not make the start generate a key file"
    print_success(f"start stopped: {raised.value}")


def test_startup_goes_on_with_a_damaged_generated_key_and_logs_an_error(configuration, logged):
    """(d) A generated key file gone bad is an error in the log, not a stop: the file is left for the admin to restore."""
    key_file = configuration.damaged_key(b"")

    log_configuration_audit()

    errors = [(fields["check"], fields["detail"]["source"]) for level, _, fields in logged if level == "error"]
    assert errors == [("platform.instance_key", "generated")], f"a damaged generated key must be logged once as an error of the instance key check: {logged}"
    assert key_file.read_bytes() == b"", "the startup audit must not touch the key file"
    print_success("logged as an error, the start went on")


def test_startup_logs_nothing_when_every_check_is_ok(configuration, logged):
    """(d) An ok check is not logged: a well-configured instance starts with a quiet log."""
    configuration.set(JWT_SECRET=GOOD_JWT_SECRET, LIBREFOLIO_INSTANCE_KEY=GOOD_INSTANCE_KEY)
    assert all(result.severity == "ok" for result in run_config_checks()), f"the configuration of this test must be all ok: {run_config_checks()}"

    log_configuration_audit()

    assert logged == [], f"ok checks must not be logged: {logged}"
    print_success("all ok, nothing logged")


def test_startup_logs_every_check_that_is_not_ok_at_the_level_of_its_severity(configuration, logged):
    """(d) In the order of the checks, each with its summary, its id and its detail."""
    print_section("Configuration checks: the startup log")
    configuration.set(
        LIBREFOLIO_INSTANCE_KEY=GOOD_INSTANCE_KEY,
        LIBREFOLIO_INSTANCE_KEY_FILE=str(configuration.file("instance-key", GOOD_INSTANCE_KEY.encode())),
        SESSION_COOKIE_SECURE="never",
        LOG_LEVEL="DEBUG",
    )

    log_configuration_audit()

    levels = [(level, fields["check"]) for level, _, fields in logged]
    assert levels == [("info", "platform.jwt_secret"), ("warning", "platform.secrets_set_twice"), ("warning", "platform.session_cookie"), ("info", "platform.log_level")], f"each check that is not ok must be logged once, in order, at the level of its severity: {levels}"
    expected = [(result.severity, result.summary, {"check": result.check_id, "detail": result.detail}) for result in run_config_checks() if result.severity != "ok"]
    assert logged == expected, "each record must carry the summary of its check, its id and its detail"
    print_success(f"{len(logged)} records: {levels}")


def test_startup_does_not_generate_the_instance_key(configuration, logged):
    """(d) The key is generated by its first use, not by the audit: no key yet is fine and not logged."""
    configuration.set(JWT_SECRET=GOOD_JWT_SECRET)

    log_configuration_audit()

    assert logged == [], f"no key yet is the normal state of a new instance: nothing to log, got {logged}"
    assert not configuration.data_dir.exists(), f"the startup audit must not generate the key: {list(configuration.data_dir.rglob('*'))}"
    print_success("no key generated, nothing logged")


@pytest.mark.parametrize(("variable", "value"), [pytest.param("JWT_SECRET", GOOD_JWT_SECRET, id="jwt-secret"), pytest.param("LIBREFOLIO_INSTANCE_KEY", GOOD_INSTANCE_KEY, id="instance-key")])
def test_a_set_variable_wins_over_its_broken_file_at_startup(configuration, logged, variable, value):
    """(d) NAME wins, so its broken NAME_FILE is never read and stops nothing; being set twice is still a warning."""
    configuration.set(**{variable: value, f"{variable}_FILE": str(configuration.tmp_path / "missing")})

    log_configuration_audit()

    warnings = [fields["detail"] for level, _, fields in logged if level == "warning"]
    assert warnings == [{"variables": variable}], f"{variable} set both ways must be one warning naming it: {logged}"
    print_success(f"{variable} won over its broken file, warned as set twice")


# =============================================================================
# (e) The profile and the instance block
# =============================================================================


@pytest.mark.parametrize(
    ("profile", "jwt_secret", "severity", "message", "detail"),
    [
        pytest.param("selfhosted", "x" * 31, "warning", "jwtSecret.short", {"source": "JWT_SECRET", "length": 31, "minimum": 32}, id="selfhosted-31-characters-warning"),
        pytest.param("managed", "x" * 31, "error", "jwtSecret.short", {"source": "JWT_SECRET", "length": 31, "minimum": 32}, id="managed-31-characters-error"),
        pytest.param("managed", "x", "error", "jwtSecret.short", {"source": "JWT_SECRET", "length": 1, "minimum": 32}, id="managed-1-character-error"),
        pytest.param("managed", "x" * 32, "ok", "jwtSecret.ok", {}, id="managed-32-characters-ok"),
        pytest.param("managed", None, "info", "jwtSecret.ephemeral", {}, id="managed-unset-info"),
        pytest.param(" MANAGED ", "x" * 31, "error", "jwtSecret.short", {"source": "JWT_SECRET", "length": 31, "minimum": 32}, id="managed-in-any-case-error"),
    ],
)
def test_the_severity_of_a_short_jwt_secret_follows_the_profile(configuration, profile, jwt_secret, severity, message, detail):
    """(e) The same short key, the same detail: an error in the managed profile, a warning in selfhosted; the profile changes nothing else."""
    configuration.set(LIBREFOLIO_PROFILE=profile)
    if jwt_secret is not None:
        configuration.set(JWT_SECRET=jwt_secret)

    result = check_jwt_secret()

    _assert_check(result, check_jwt_secret, severity, message, detail)
    print_success(f"LIBREFOLIO_PROFILE={profile!r}, JWT_SECRET of {len(jwt_secret or '')} characters: {severity}")


@pytest.mark.parametrize("source", ["variable", "file"])
def test_startup_stops_on_a_short_jwt_secret_in_the_managed_profile(configuration, logged, source):
    """(e) Managed: a short key stops the start, nothing logged first; the message names the origin and the length, never the key."""
    secret = f"jwt-{CANARY}"
    assert len(secret) < JWT_SECRET_MIN_LENGTH, f"Precondition: the key of this test must be short, it is {len(secret)} characters"
    configuration.set(LIBREFOLIO_PROFILE="managed")
    if source == "variable":
        configuration.set(JWT_SECRET=secret)
        origin = "JWT_SECRET"
    else:
        secret_file = configuration.file("jwt-secret", secret.encode() + b"\n")
        configuration.set(JWT_SECRET_FILE=str(secret_file))
        origin = f"JWT_SECRET_FILE ({secret_file})"

    with pytest.raises(WeakSecretError) as raised:
        log_configuration_audit()

    expected = f"In the managed profile the session signing key from {origin} must be at least 32 characters long; it is {len(secret)}"
    assert str(raised.value) == expected, f"the startup error must name the origin and the length:\n  expected {expected!r}\n  got      {str(raised.value)!r}"
    assert isinstance(raised.value, ValueError), "WeakSecretError is a ValueError: a caller stopping on configuration errors stops on it too"
    shown = "".join(traceback.format_exception(raised.value))
    assert CANARY not in shown, f"the startup error showed the key: {shown}"
    assert logged == [], f"nothing is logged before the start is stopped: {logged}"
    print_success(f"start stopped: {raised.value}")


def test_startup_goes_on_with_a_short_jwt_secret_in_the_selfhosted_profile(configuration, logged):
    """(e) Selfhosted: the same short key is a warning in the log, without the key, and the start goes on."""
    secret = f"jwt-{CANARY}"
    configuration.set(LIBREFOLIO_PROFILE="selfhosted", JWT_SECRET=secret)

    log_configuration_audit()

    flagged = [(level, fields["check"], fields["detail"]) for level, _, fields in logged]
    assert flagged == [("warning", "platform.jwt_secret", {"source": "JWT_SECRET", "length": len(secret), "minimum": 32})], f"a short key in selfhosted must be logged once, as a warning of its check: {logged}"
    assert CANARY not in repr(logged), f"the startup log showed the key: {logged}"
    print_success("selfhosted: warned, the start went on")


@pytest.mark.parametrize(
    ("variables", "variable"),
    [
        pytest.param({"LIBREFOLIO_BLOCKED": "maybe"}, "LIBREFOLIO_BLOCKED", id="blocked-maybe"),
        pytest.param({"LIBREFOLIO_BLOCKED": "2"}, "LIBREFOLIO_BLOCKED", id="blocked-2"),
        pytest.param({"LIBREFOLIO_BLOCKED": "maybe", "LIBREFOLIO_DELETION_DATE": "2026-11-14"}, "LIBREFOLIO_BLOCKED", id="blocked-maybe-with-a-good-date"),
        pytest.param({"LIBREFOLIO_DELETION_DATE": "14/11/2026"}, "LIBREFOLIO_DELETION_DATE", id="date-day-first-not-blocked"),
        pytest.param({"LIBREFOLIO_BLOCKED": "false", "LIBREFOLIO_DELETION_DATE": "2026-02-30"}, "LIBREFOLIO_DELETION_DATE", id="date-out-of-range-not-blocked"),
        pytest.param({"LIBREFOLIO_BLOCKED": "true", "LIBREFOLIO_DELETION_DATE": "next month"}, "LIBREFOLIO_DELETION_DATE", id="date-a-word-blocked"),
    ],
)
def test_startup_stops_on_a_block_variable_that_cannot_be_read(configuration, logged, variables, variable):
    """(e) A typo in either variable stops the start, blocked or not, before anything is logged: the block is never left to chance."""
    configuration.set(JWT_SECRET=GOOD_JWT_SECRET, LIBREFOLIO_INSTANCE_KEY=GOOD_INSTANCE_KEY, **variables)

    with pytest.raises(ValueError, match=variable) as raised:
        log_configuration_audit()

    assert not isinstance(raised.value, WeakSecretError), f"the stop must come from the block variables, not from the key: {raised.value!r}"
    assert logged == [], f"nothing is logged before the start is stopped: {logged}"
    print_success(f"start stopped: {raised.value}")


@pytest.mark.parametrize(
    ("blocked", "deletion_date", "logged_date"),
    [
        pytest.param("true", "2026-11-14", "2026-11-14", id="blocked-with-a-date"),
        pytest.param(" ON ", " 2026-11-14 ", "2026-11-14", id="blocked-with-a-date-stripped"),
        pytest.param("1", None, None, id="blocked-without-a-date"),
        pytest.param("yes", "   ", None, id="blocked-with-a-blank-date"),
    ],
)
def test_startup_logs_a_blocked_instance_with_its_deletion_date(configuration, logged, blocked, deletion_date, logged_date):
    """(e) A blocked instance is one warning naming LIBREFOLIO_BLOCKED, with the deletion date in ISO or None; the start goes on."""
    configuration.set(JWT_SECRET=GOOD_JWT_SECRET, LIBREFOLIO_INSTANCE_KEY=GOOD_INSTANCE_KEY, LIBREFOLIO_BLOCKED=blocked)
    if deletion_date is not None:
        configuration.set(LIBREFOLIO_DELETION_DATE=deletion_date)
    assert all(result.severity == "ok" for result in run_config_checks()), f"Precondition: every check ok, so the block is the only record: {run_config_checks()}"

    log_configuration_audit()

    assert [(level, fields) for level, _, fields in logged] == [("warning", {"deletion_date": logged_date})], f"a blocked instance must be logged once, as a warning with its deletion date: {logged}"
    assert "LIBREFOLIO_BLOCKED" in logged[0][1], f"the warning must name the variable that blocks: {logged[0][1]!r}"
    print_success(f"LIBREFOLIO_BLOCKED={blocked!r}: {logged[0][1]} {logged[0][2]}")


def test_startup_logs_the_block_before_the_checks(configuration, logged):
    """(e) The block comes first in the log, then the checks that are not ok, in their order."""
    configuration.set(LIBREFOLIO_INSTANCE_KEY=GOOD_INSTANCE_KEY, LIBREFOLIO_BLOCKED="true", LIBREFOLIO_DELETION_DATE="2026-11-14")

    log_configuration_audit()

    order = [(level, fields.get("check", "block")) for level, _, fields in logged]
    assert order == [("warning", "block"), ("info", "platform.jwt_secret")], f"the block, then the unset key's info: {logged}"
    print_success(f"{order}")


@pytest.mark.parametrize(
    "variables",
    [
        pytest.param({}, id="unset"),
        pytest.param({"LIBREFOLIO_BLOCKED": ""}, id="blank"),
        pytest.param({"LIBREFOLIO_BLOCKED": "off"}, id="off"),
        pytest.param({"LIBREFOLIO_BLOCKED": "false", "LIBREFOLIO_DELETION_DATE": "2026-11-14"}, id="false-with-a-date"),
        pytest.param({"LIBREFOLIO_DELETION_DATE": "2026-11-14"}, id="a-date-alone"),
    ],
)
def test_startup_logs_nothing_about_the_block_when_not_blocked(configuration, logged, variables):
    """(e) Not blocked: no record about the block, a valid deletion date alone included."""
    configuration.set(JWT_SECRET=GOOD_JWT_SECRET, LIBREFOLIO_INSTANCE_KEY=GOOD_INSTANCE_KEY, **variables)

    log_configuration_audit()

    assert logged == [], f"an instance that is not blocked logs nothing about the block: {logged}"
    print_success(f"{variables or 'unset'}: nothing logged")


# =============================================================================
# (f) The client address check (H-36)
# =============================================================================


#: (f) The forwarding headers, as the check names them.
XFF, FORWARDED, REAL_IP = "X-Forwarded-For", "Forwarded", "X-Real-IP"
#: (f) The summaries of the check, word for word: the module's own texts, by the name the cases give them.
SUMMARIES = {"UNTRUSTED_PROXY_SUMMARY": UNTRUSTED_PROXY_SUMMARY, "PUBLIC_FORWARDING_SUMMARY": PUBLIC_FORWARDING_SUMMARY}


def _noted(monkeypatch: pytest.MonkeyPatch, local: set[str], public: set[str]) -> None:
    """(f) What ``forwarded_by_untrusted_proxy`` noted, for this test only: both sets replaced by copies, put back after it."""
    monkeypatch.setitem(_untrusted_forwarding, "local", set(local))
    monkeypatch.setitem(_untrusted_forwarding, "public", set(public))


@pytest.mark.parametrize(
    ("local", "public", "severity", "message", "detail", "summary"),
    [
        pytest.param(set(), set(), "ok", "clientAddress.ok", {}, None, id="nothing-noted-ok-as-at-startup"),
        pytest.param({REAL_IP}, set(), "warning", "clientAddress.untrustedProxy", {"headers": REAL_IP}, "UNTRUSTED_PROXY_SUMMARY", id="local-one-header-warning"),
        pytest.param({REAL_IP, XFF, FORWARDED}, set(), "warning", "clientAddress.untrustedProxy", {"headers": "X-Forwarded-For, Forwarded, X-Real-IP"}, "UNTRUSTED_PROXY_SUMMARY", id="local-every-header-in-order"),
        pytest.param(set(), {XFF}, "info", "clientAddress.publicForwarding", {"headers": XFF}, "PUBLIC_FORWARDING_SUMMARY", id="public-only-info"),
        pytest.param(set(), {REAL_IP, XFF}, "info", "clientAddress.publicForwarding", {"headers": "X-Forwarded-For, X-Real-IP"}, "PUBLIC_FORWARDING_SUMMARY", id="public-two-headers-in-order"),
        pytest.param({FORWARDED}, {XFF, REAL_IP}, "warning", "clientAddress.untrustedProxy", {"headers": FORWARDED}, "UNTRUSTED_PROXY_SUMMARY", id="local-wins-over-public-with-the-local-names-only"),
    ],
)
def test_check_client_address_in_each_of_its_states(configuration, monkeypatch, local, public, severity, message, detail, summary):
    """(f) What was noted decides: local a warning, public alone info, nothing ok; the detail lists the names in order, the
    local ones only when both are noted, and the summary is the module's own text."""
    _noted(monkeypatch, local, public)

    result = check_client_address()

    _assert_check(result, check_client_address, severity, message, detail)
    if summary is not None:
        expected = SUMMARIES[summary]
        assert result.summary == expected, f"check_client_address() is {severity}: its summary must be {summary}, word for word:\n  expected {expected!r}\n  got      {result.summary!r}"
    print_success(f"local {sorted(local)}, public {sorted(public)}: {severity} {result.i18n_key}")


@pytest.mark.parametrize(
    ("local", "public"),
    [
        pytest.param(set(), set(), id="nothing-noted"),
        pytest.param({XFF, REAL_IP}, set(), id="local"),
        pytest.param(set(), {FORWARDED}, id="public"),
        pytest.param({FORWARDED}, {XFF, REAL_IP}, id="both"),
    ],
)
def test_check_client_address_changes_nothing(configuration, monkeypatch, local, public):
    """(f) The check reads what was noted and leaves it as it was: the same sets, holding the same names."""
    _noted(monkeypatch, local, public)
    state = _untrusted_forwarding
    held = {peer_class: state[peer_class] for peer_class in ("local", "public")}
    before = {peer_class: set(names) for peer_class, names in state.items()}

    results = [check_client_address(), check_client_address()]

    assert results[0] == results[1], f"the same state gives the same result: {results}"
    after = {peer_class: set(names) for peer_class, names in state.items()}
    assert after == before, f"check_client_address() changed what was noted: {before} became {after}"
    replaced = [peer_class for peer_class, names in held.items() if state[peer_class] is not names]
    assert not replaced, f"check_client_address() replaced the set of {replaced} in _untrusted_forwarding"
    print_success(f"local {sorted(local)}, public {sorted(public)}: unchanged")


def test_the_client_address_check_runs_right_after_the_session_cookie_check():
    """(f) Registered in CONFIG_CHECKS right after check_session_cookie; what follows it is pinned by (g) (H-39)."""
    index = CONFIG_CHECKS.index(check_session_cookie)

    following = CONFIG_CHECKS[index + 1 : index + 2]

    assert following == (check_client_address,), f"CONFIG_CHECKS must run check_client_address right after check_session_cookie: {[check.__name__ for check in CONFIG_CHECKS]}"
    print_success(f"{[check.__name__ for check in CONFIG_CHECKS[index : index + 2]]}")


def test_a_forwarding_note_left_by_another_test_does_not_reach_the_audit(monkeypatch, tmp_path):
    """(f) H-35: notes another test of the same process left behind, local and public, do not reach the checks of this
    file: ``_configure`` starts from nothing noted, so the client address check is ok and the audit is this
    configuration's own, every check ok but the unset JWT secret's info. Not through the ``configuration`` fixture: the
    notes come first, as they would."""
    # Left behind as another test could leave them: X-Forwarded-For from a local peer, X-Real-IP from a public one. In
    # sets of this test's own, so the module's sets are never written to
    monkeypatch.setitem(_untrusted_forwarding, "local", {XFF})
    monkeypatch.setitem(_untrusted_forwarding, "public", {REAL_IP})
    left = check_client_address()
    assert (left.severity, left.i18n_key) == ("warning", "instance.checks.clientAddress.untrustedProxy"), f"Precondition: the notes left behind must make the check a warning, or its silence after _configure proves nothing: {left}"

    # _configure empties both with monkeypatch.setitem too. Monkeypatch undoes in reverse order: _configure's two first,
    # back to the sets above, then the two above, back to the module's own sets, untouched
    _configure(monkeypatch, tmp_path, production=False)

    _assert_check(check_client_address(), check_client_address, "ok", "clientAddress.ok", {})
    flagged = [(result.check_id, result.severity) for result in run_config_checks() if result.severity != "ok"]
    assert flagged == [("platform.jwt_secret", "info")], f"with the notes left behind emptied, every check must be ok but the unset JWT secret's info: {flagged}"
    print_success(f"{XFF} from a local peer, {REAL_IP} from a public one, left behind: emptied, not ok only {flagged}")


# =============================================================================
# (g) The switches the managed profile turns on (H-39)
# =============================================================================


#: (g) The summary of each check with its switch off in the managed profile, word for word.
FRAME_PROTECTION_OFF_MANAGED = "LIBREFOLIO_FRAME_PROTECTION is off in the managed profile: any site can show LibreFolio in a frame; the managed profile turns it on"
CSP_REPORT_ONLY_OFF_MANAGED = "LIBREFOLIO_CSP_REPORT_ONLY is off in the managed profile: browsers list no Content-Security-Policy violation; the managed profile turns it on"


@dataclass(frozen=True)
class Switch:
    """(g) A setting the managed profile turns on, as its check reports it: the variable, the stem of the check's i18n
    keys, and the severity and the summary of the switch off in the managed profile."""

    variable: str
    stem: str
    severity: str
    summary: str


#: (g) The switch of each check.
SWITCHES: dict[Callable[[], ConfigCheck], Switch] = {
    check_frame_protection: Switch("LIBREFOLIO_FRAME_PROTECTION", "frameProtection", "warning", FRAME_PROTECTION_OFF_MANAGED),
    check_csp_report_only: Switch("LIBREFOLIO_CSP_REPORT_ONLY", "cspReportOnly", "info", CSP_REPORT_ONLY_OFF_MANAGED),
}
#: (g) The two checks, one case each.
SWITCH_CHECKS = [pytest.param(check_frame_protection, id="frame-protection"), pytest.param(check_csp_report_only, id="csp-report-only")]


def _profile(configuration: Configuration, profile: str | None) -> None:
    """(g) ``LIBREFOLIO_PROFILE`` as the case writes it; ``None`` removes it, and test mode reads no ``.env``, so the profile is the code default, ``selfhosted``."""
    if profile is None:
        configuration.monkeypatch.delenv("LIBREFOLIO_PROFILE")
    else:
        configuration.set(LIBREFOLIO_PROFILE=profile)


@pytest.mark.parametrize(
    ("profile", "value", "state"),
    [
        pytest.param(None, None, "offSelfHosted", id="profile-unset-switch-unset"),
        pytest.param(None, "true", "on", id="profile-unset-true"),
        pytest.param(None, "false", "offSelfHosted", id="profile-unset-false"),
        pytest.param("selfhosted", None, "offSelfHosted", id="selfhosted-switch-unset"),
        pytest.param("selfhosted", "true", "on", id="selfhosted-true"),
        pytest.param("selfhosted", "YES", "on", id="selfhosted-yes-in-any-case"),
        pytest.param("selfhosted", "false", "offSelfHosted", id="selfhosted-false"),
        pytest.param("selfhosted", "0", "offSelfHosted", id="selfhosted-0"),
        pytest.param("selfhosted", "off", "offSelfHosted", id="selfhosted-off"),
        pytest.param("managed", None, "on", id="managed-switch-unset-on-by-the-profile"),
        pytest.param("managed", "true", "on", id="managed-true"),
        pytest.param("managed", "YES", "on", id="managed-yes-in-any-case"),
        pytest.param("managed", "false", "offManaged", id="managed-false"),
        pytest.param("managed", "0", "offManaged", id="managed-0"),
        pytest.param("managed", "off", "offManaged", id="managed-off"),
        pytest.param("MANAGED", None, "on", id="managed-in-capitals-switch-unset-on-by-the-profile"),
        pytest.param("MANAGED", "false", "offManaged", id="managed-in-capitals-false"),
        pytest.param(" Managed ", None, "on", id="managed-padded-switch-unset-on-by-the-profile"),
        pytest.param(" Managed ", "off", "offManaged", id="managed-padded-off"),
    ],
)
@pytest.mark.parametrize("check", SWITCH_CHECKS)
def test_the_switch_checks_in_each_of_their_states(configuration, check, profile, value, state):
    """(g) On is ok whatever the profile; off is the switch's severity in the managed profile, with its summary word for
    word, and ok otherwise; unset takes the profile's default, on in managed, off elsewhere. No detail in any state."""
    switch = SWITCHES[check]
    _profile(configuration, profile)
    if value is not None:
        configuration.set(**{switch.variable: value})
    expected_on = state == "on"
    assert getattr(get_settings(), switch.variable) is expected_on, f"Precondition: with LIBREFOLIO_PROFILE={profile!r} and {switch.variable}={value!r}, Settings must read the switch as {expected_on}"

    result = check()

    severity = switch.severity if state == "offManaged" else "ok"
    _assert_check(result, check, severity, f"{switch.stem}.{state}", {})
    if severity != "ok":
        assert result.summary == switch.summary, f"{check.__name__}() is {severity}: its summary must be, word for word:\n  expected {switch.summary!r}\n  got      {result.summary!r}"
    print_success(f"LIBREFOLIO_PROFILE={profile!r}, {switch.variable}={value!r}: {severity} {result.i18n_key}")


@pytest.mark.parametrize("check", SWITCH_CHECKS)
def test_a_switch_lost_from_the_managed_profile_defaults_is_still_reported(configuration, monkeypatch, check):
    """(g) The managed expectation is the check's own: with its entry lost from ``PROFILE_DEFAULTS``, a managed instance
    that leaves the switch unset falls back to the code default, off, and the check reports it instead of following the
    table that lost it."""
    switch = SWITCHES[check]
    monkeypatch.delitem(PROFILE_DEFAULTS["managed"], switch.variable, raising=False)
    configuration.set(LIBREFOLIO_PROFILE="managed")
    assert getattr(get_settings(), switch.variable) is False, f"Precondition: without its managed entry, {switch.variable} unset must fall back to its code default, off"

    result = check()

    _assert_check(result, check, switch.severity, f"{switch.stem}.offManaged", {})
    assert result.summary == switch.summary, f"{check.__name__}() is {switch.severity}: its summary must be, word for word:\n  expected {switch.summary!r}\n  got      {result.summary!r}"
    print_success(f"{switch.variable} lost from the managed defaults: {result.severity} {result.i18n_key}")


@pytest.mark.parametrize(
    ("profile", "value"),
    [
        pytest.param("managed", "false", id="managed-off"),
        pytest.param("managed", None, id="managed-unset-on-by-the-profile"),
        pytest.param("selfhosted", "false", id="selfhosted-off"),
        pytest.param("selfhosted", "true", id="selfhosted-on"),
    ],
)
@pytest.mark.parametrize("check", SWITCH_CHECKS)
def test_the_switch_checks_change_nothing(configuration, check, profile, value):
    """(g) A check reads the settings and leaves everything as it was: the environment (no switch turned on, no profile
    changed), the profiles' table, and no file written; the same configuration gives the same result."""
    switch = SWITCHES[check]
    configuration.set(LIBREFOLIO_PROFILE=profile)
    if value is not None:
        configuration.set(**{switch.variable: value})
    environment = dict(os.environ)
    table = {name: dict(values) for name, values in PROFILE_DEFAULTS.items()}

    results = [check(), check()]

    assert results[0] == results[1], f"the same configuration gives the same result: {results}"
    assert dict(os.environ) == environment, f"{check.__name__}() changed the environment"
    assert {name: dict(values) for name, values in PROFILE_DEFAULTS.items()} == table, f"{check.__name__}() changed PROFILE_DEFAULTS"
    assert not configuration.data_dir.exists(), f"{check.__name__}() created files: {list(configuration.data_dir.rglob('*'))}"
    print_success(f"LIBREFOLIO_PROFILE={profile!r}, {switch.variable}={value!r}: unchanged")


def test_the_switch_checks_run_right_after_the_client_address_check():
    """(g) Registered in CONFIG_CHECKS right after check_client_address, frame protection first, then the report-only
    policy, before check_log_level."""
    index = CONFIG_CHECKS.index(check_client_address)

    following = CONFIG_CHECKS[index + 1 : index + 4]

    assert following == (check_frame_protection, check_csp_report_only, check_log_level), f"CONFIG_CHECKS must run check_frame_protection, then check_csp_report_only, right after check_client_address and before check_log_level: {[check.__name__ for check in CONFIG_CHECKS]}"
    print_success(f"{[check.__name__ for check in CONFIG_CHECKS[index : index + 4]]}")


def test_startup_logs_the_switches_off_in_the_managed_profile_and_goes_on(configuration, logged, monkeypatch):
    """(g)(d) Managed, both switches off: the frame protection warning, then the report-only info, in the order of
    CONFIG_CHECKS, each once with its summary word for word, its id and no detail; the start goes on."""
    print_section("Configuration checks: the managed profile's switches at startup")
    _noted(monkeypatch, set(), set())
    configuration.set(LIBREFOLIO_PROFILE="managed", JWT_SECRET=GOOD_JWT_SECRET, LIBREFOLIO_FRAME_PROTECTION="false", LIBREFOLIO_CSP_REPORT_ONLY="false")
    switch_ids = {CHECK_IDS[check] for check in SWITCHES}
    others = [(result.check_id, result.severity) for result in run_config_checks() if result.severity != "ok" and result.check_id not in switch_ids]
    assert others == [], f"Precondition: every other check ok, so the two switches are the only records: {others}"

    log_configuration_audit()

    expected = [
        ("warning", FRAME_PROTECTION_OFF_MANAGED, {"check": "platform.frame_protection", "detail": {}}),
        ("info", CSP_REPORT_ONLY_OFF_MANAGED, {"check": "platform.csp_report_only", "detail": {}}),
    ]
    assert logged == expected, f"managed with both switches off: the frame protection warning, then the report-only info, each once, with its summary, id and detail:\n  expected {expected}\n  got      {logged}"
    print_success(f"{[(level, fields['check']) for level, _, fields in logged]}")


@pytest.mark.parametrize(
    ("profile", "variables"),
    [
        pytest.param("selfhosted", {}, id="selfhosted-both-unset-the-default"),
        pytest.param("selfhosted", {"LIBREFOLIO_FRAME_PROTECTION": "false", "LIBREFOLIO_CSP_REPORT_ONLY": "false"}, id="selfhosted-both-false"),
        pytest.param(None, {"LIBREFOLIO_FRAME_PROTECTION": "off", "LIBREFOLIO_CSP_REPORT_ONLY": "0"}, id="profile-unset-both-off"),
    ],
)
def test_startup_logs_neither_switch_off_in_the_selfhosted_profile(configuration, logged, monkeypatch, profile, variables):
    """(g)(d) Self-hosted, both switches off, as by default: both checks are ok, and neither is logged. Barriers: the
    audit runs both checks, and its record of the unset JWT secret reaches the recorder, so the silence about the
    switches is heard, not assumed."""
    _noted(monkeypatch, set(), set())
    _profile(configuration, profile)
    configuration.set(**variables)
    states = {result.check_id: (result.severity, result.i18n_key) for result in run_config_checks() if result.check_id in ("platform.frame_protection", "platform.csp_report_only")}
    expected_states = {"platform.frame_protection": ("ok", "instance.checks.frameProtection.offSelfHosted"), "platform.csp_report_only": ("ok", "instance.checks.cspReportOnly.offSelfHosted")}
    assert states == expected_states, f"Precondition: the audit runs both checks, ok since off is the self-hosted default: {states}"

    log_configuration_audit()

    flagged = [(level, fields.get("check")) for level, _, fields in logged]
    assert flagged == [("info", "platform.jwt_secret")], f"self-hosted with both switches off: neither check is logged, only the unset JWT secret's info: {logged}"
    print_success(f"LIBREFOLIO_PROFILE={profile!r}, {variables or 'both unset'}: neither switch logged")


# =============================================================================
# (h) Test mode outside a test lane (H-46)
# =============================================================================


#: (h) The summary of the test mode check outside a test lane, word for word, its ``{data_dir}`` to fill
#: (``config_audit.TEST_MODE_OUTSIDE_LANE_SUMMARY``).
TEST_MODE_OUTSIDE_LANE = "LIBREFOLIO_TEST_MODE is on outside a test lane: test-only providers are served, the data are kept in the test data directory {data_dir} and .env is not read; unset it on a production instance"
#: (h) The error that stops a managed start with test mode on outside a test lane, word for word, its ``{data_dir}`` to
#: fill (``config_audit.ManagedTestModeError``). Since H-49 it names the lane id's bounds: an id can be set and still
#: give no lane.
MANAGED_TEST_MODE_STOP = "In the managed profile LIBREFOLIO_TEST_MODE must not be on outside a test lane (no LIBREFOLIO_TEST_LANE_ID of 16 to 128 characters): test-only providers would be served and the data kept in the test data directory {data_dir}; unset LIBREFOLIO_TEST_MODE"
#: (h) A lane id that gives no lane: unset, empty or blank; (i) has the lane ids out of the bounds (H-49).
NO_LANE = [pytest.param(None, id="lane-unset"), pytest.param("", id="lane-empty"), pytest.param("   ", id="lane-blank")]


def _outside_a_test_lane(configuration: Configuration, lane: str | None = None) -> str:
    """(h) Test mode on without a lane: ``LIBREFOLIO_TEST_LANE_ID`` removed (``None``) or set to ``lane``, empty or blank.
    Returns the data directory the check names, verified to be this test's own test data directory."""
    if lane is None:
        configuration.monkeypatch.delenv("LIBREFOLIO_TEST_LANE_ID", raising=False)
    else:
        configuration.set(LIBREFOLIO_TEST_LANE_ID=lane)
    assert is_test_mode(), f"Precondition: LIBREFOLIO_TEST_MODE={os.environ.get('LIBREFOLIO_TEST_MODE')!r} must turn test mode on"
    data_dir = str(get_data_dir())
    assert data_dir == str(configuration.data_dir), f"Precondition: in test mode the data directory must be this test's test data directory, {configuration.data_dir}, not {data_dir}"
    return data_dir


def test_the_test_mode_summary_is_pinned_by_value():
    """(h) H-46: ``TEST_MODE_OUTSIDE_LANE_SUMMARY`` is this string, word for word: what test mode outside a lane serves,
    where it keeps the data, and what the admin must do."""
    print_section("H-46: test mode outside a test lane")

    summary = _h46("TEST_MODE_OUTSIDE_LANE_SUMMARY")

    assert summary == TEST_MODE_OUTSIDE_LANE, f"H-46: config_audit.TEST_MODE_OUTSIDE_LANE_SUMMARY must be, word for word:\n  expected {TEST_MODE_OUTSIDE_LANE!r}\n  got      {summary!r}"
    print_success(f"TEST_MODE_OUTSIDE_LANE_SUMMARY = {summary!r}")


def test_managed_test_mode_error_is_a_runtime_error():
    """(h) H-46: ``ManagedTestModeError``, the managed start's stop on test mode outside a lane, is a ``RuntimeError``,
    as ``SecretFileError`` and ``InstanceKeyError`` are."""
    error = _h46("ManagedTestModeError")

    assert isinstance(error, type) and issubclass(error, RuntimeError), f"H-46: config_audit.ManagedTestModeError must be a class derived from RuntimeError, not {error!r}"
    print_success(f"{error.__name__}: {[cls.__name__ for cls in error.__mro__]}")


def test_the_test_mode_check_runs_last_of_the_platform_checks():
    """(h) H-46: registered in CONFIG_CHECKS right after check_log_level, so the platform's last check, right before
    workstream B's first."""
    check_test_mode = _h46("check_test_mode")
    index = CONFIG_CHECKS.index(check_log_level)

    following = CONFIG_CHECKS[index + 1 : index + 3]

    assert following == (check_test_mode, BACKUP_CONFIG_CHECKS[0]), f"H-46: CONFIG_CHECKS must run check_test_mode right after check_log_level, then B's first check, {BACKUP_CONFIG_CHECKS[0].__name__}: {[check.__name__ for check in CONFIG_CHECKS]}"
    print_success(f"{[check.__name__ for check in CONFIG_CHECKS[index : index + 3]]}")


@pytest.mark.parametrize("lane", [pytest.param(FAKE_LANE_ID, id="with-a-lane"), pytest.param(None, id="without-a-lane")])
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(None, id="test-mode-unset"),
        pytest.param("", id="test-mode-empty"),
        pytest.param("0", id="test-mode-0"),
        pytest.param("false", id="test-mode-false"),
        pytest.param("no", id="test-mode-no"),
        pytest.param("on", id="test-mode-on-is-not-a-true-spelling"),
        pytest.param(" 1", id="test-mode-padded-1-is-not-stripped"),
    ],
)
def test_the_test_mode_check_is_ok_with_test_mode_off(production_configuration, value, lane):
    """(h) H-46: test mode off, as ``is_test_mode()`` reads it (``on`` and `` 1`` included), is ok,
    ``instance.checks.testMode.off``, with no detail and no summary, whatever the lane id holds."""
    check_test_mode = _h46("check_test_mode")
    configuration = production_configuration
    if value is None:
        configuration.monkeypatch.delenv("LIBREFOLIO_TEST_MODE", raising=False)
    else:
        configuration.set(LIBREFOLIO_TEST_MODE=value)
    if lane is None:
        configuration.monkeypatch.delenv("LIBREFOLIO_TEST_LANE_ID", raising=False)
    else:
        configuration.set(LIBREFOLIO_TEST_LANE_ID=lane)
    assert not is_test_mode(), f"Precondition: is_test_mode() must read LIBREFOLIO_TEST_MODE={value!r} as off"

    result = check_test_mode()

    _assert_check(result, check_test_mode, "ok", "testMode.off", {})
    assert result.summary == "", f"an ok check has no summary: {result.summary!r}"
    print_success(f"LIBREFOLIO_TEST_MODE={value!r}, LIBREFOLIO_TEST_LANE_ID={lane!r}: ok {result.i18n_key}")


@pytest.mark.parametrize("value", [pytest.param(value, id=f"test-mode-{value}") for value in ("1", "true", "TRUE", "yes", "Yes")])
def test_the_test_mode_check_is_ok_in_a_test_lane(configuration, value):
    """(h) H-46: test mode on, in each spelling ``is_test_mode()`` reads as on, in a lane, as the runner always gives it:
    ok, ``instance.checks.testMode.testLane``, with no detail and no summary."""
    check_test_mode = _h46("check_test_mode")
    configuration.set(LIBREFOLIO_TEST_MODE=value)
    assert is_test_mode(), f"Precondition: is_test_mode() must read LIBREFOLIO_TEST_MODE={value!r} as on"
    assert os.environ.get("LIBREFOLIO_TEST_LANE_ID") == FAKE_LANE_ID, "Precondition: _configure puts every test-mode configuration in this file's own lane"

    result = check_test_mode()

    _assert_check(result, check_test_mode, "ok", "testMode.testLane", {})
    assert result.summary == "", f"an ok check has no summary: {result.summary!r}"
    print_success(f"LIBREFOLIO_TEST_MODE={value!r} in a test lane: ok {result.i18n_key}")


@pytest.mark.parametrize("lane", NO_LANE)
@pytest.mark.parametrize("value", [pytest.param("1", id="test-mode-1"), pytest.param("TRUE", id="test-mode-TRUE")])
def test_the_test_mode_check_is_an_error_outside_a_test_lane(configuration, value, lane):
    """(h) H-46: test mode on with the lane id unset, empty or blank, as in a container started with it: an error,
    ``instance.checks.testMode.outsideTestLane``, naming the test data directory in its detail and in its summary."""
    check_test_mode = _h46("check_test_mode")
    summary = _h46("TEST_MODE_OUTSIDE_LANE_SUMMARY")
    configuration.set(LIBREFOLIO_TEST_MODE=value)
    data_dir = _outside_a_test_lane(configuration, lane)

    result = check_test_mode()

    _assert_check(result, check_test_mode, "error", "testMode.outsideTestLane", {"data_dir": data_dir})
    expected = summary.format(data_dir=data_dir)
    assert result.summary == expected, f"check_test_mode() outside a test lane: its summary must be TEST_MODE_OUTSIDE_LANE_SUMMARY with the data directory, word for word:\n  expected {expected!r}\n  got      {result.summary!r}"
    print_success(f"LIBREFOLIO_TEST_MODE={value!r}, LIBREFOLIO_TEST_LANE_ID={lane!r}: error {result.i18n_key}")


@pytest.mark.parametrize("profile", [pytest.param(None, id="profile-unset"), pytest.param("selfhosted", id="selfhosted"), pytest.param("managed", id="managed")])
def test_the_profile_does_not_change_the_test_mode_check(configuration, profile):
    """(h) H-46: outside a lane the check is the same ``ConfigCheck`` in every profile, managed included: the profile
    decides what the start does with it, not what it says."""
    check_test_mode = _h46("check_test_mode")
    summary = _h46("TEST_MODE_OUTSIDE_LANE_SUMMARY")
    data_dir = _outside_a_test_lane(configuration)
    _profile(configuration, profile)
    assert get_settings().LIBREFOLIO_PROFILE == (profile or "selfhosted"), f"Precondition: Settings must read LIBREFOLIO_PROFILE={profile!r} as {profile or 'selfhosted'}"

    result = check_test_mode()

    expected = ConfigCheck("platform.test_mode", "error", "instance.checks.testMode.outsideTestLane", {"data_dir": data_dir}, summary.format(data_dir=data_dir))
    assert result == expected, f"LIBREFOLIO_PROFILE={profile!r}: check_test_mode() outside a test lane must be the same in every profile:\n  expected {expected}\n  got      {result}"
    print_success(f"LIBREFOLIO_PROFILE={profile!r}: {result.severity} {result.i18n_key}")


@pytest.mark.parametrize("state", [pytest.param("off", id="test-mode-off"), pytest.param("testLane", id="in-a-test-lane"), pytest.param("outsideTestLane", id="outside-a-test-lane")])
def test_the_test_mode_check_changes_nothing(monkeypatch, tmp_path, state):
    """(h) H-46: the check reads the environment and, outside a lane, the test data directory, and leaves both as they
    were: no variable changed, no file written, the same result twice."""
    check_test_mode = _h46("check_test_mode")
    configuration = _configure(monkeypatch, tmp_path, production=state == "off")
    if state == "outsideTestLane":
        _outside_a_test_lane(configuration)
    environment = dict(os.environ)

    results = [check_test_mode(), check_test_mode()]

    assert results[0] == results[1], f"the same configuration gives the same result: {results}"
    assert results[0].i18n_key == f"instance.checks.testMode.{state}", f"the check must be in the state of this case, {state}: {results[0]}"
    assert dict(os.environ) == environment, "check_test_mode() changed the environment"
    assert not configuration.data_dir.exists(), f"check_test_mode() created files: {list(configuration.data_dir.rglob('*'))}"
    print_success(f"{state}: unchanged")


@pytest.mark.parametrize("profile", [pytest.param(None, id="profile-unset"), pytest.param("selfhosted", id="selfhosted")])
def test_startup_logs_test_mode_outside_a_test_lane_as_an_error_and_goes_on(configuration, logged, profile):
    """(h)(d) H-46: self-hosted, the profile unset included, test mode outside a lane is logged once as an error, with its
    summary and the data directory, in the order of the checks; the start goes on."""
    print_section("Configuration checks: test mode outside a test lane at startup")
    summary = _h46("TEST_MODE_OUTSIDE_LANE_SUMMARY")
    data_dir = _outside_a_test_lane(configuration)
    _profile(configuration, profile)
    assert get_settings().LIBREFOLIO_PROFILE == "selfhosted", f"Precondition: Settings must read LIBREFOLIO_PROFILE={profile!r} as selfhosted"

    returned = log_configuration_audit()

    assert returned is None, f"self-hosted, the start goes on: log_configuration_audit() returns None, not {returned!r}"
    order = [(level, fields.get("check")) for level, _, fields in logged]
    assert order == [("info", "platform.jwt_secret"), ("error", "platform.test_mode")], f"the unset JWT secret's info, then the test mode error, each once, in the order of the checks: {logged}"
    expected = ("error", summary.format(data_dir=data_dir), {"check": "platform.test_mode", "detail": {"data_dir": data_dir}})
    records = [record for record in logged if record[2].get("check") == "platform.test_mode"]
    assert records == [expected], f"one error record for platform.test_mode, with its summary, its id and its detail:\n  expected {[expected]}\n  got      {records}"
    print_success(f"LIBREFOLIO_PROFILE={profile!r}: {order}, the start went on")


@pytest.mark.parametrize(
    ("profile", "production", "state"),
    [
        pytest.param(None, False, "testLane", id="profile-unset-in-a-test-lane"),
        pytest.param("selfhosted", False, "testLane", id="selfhosted-in-a-test-lane"),
        pytest.param("managed", False, "testLane", id="managed-in-a-test-lane"),
        pytest.param("selfhosted", True, "off", id="selfhosted-test-mode-off"),
        pytest.param("managed", True, "off", id="managed-test-mode-off"),
    ],
)
def test_startup_goes_on_and_logs_nothing_about_test_mode_in_a_test_lane_or_off(monkeypatch, tmp_path, logged, profile, production, state):
    """(h)(d) H-46: in a test lane, or with test mode off as in production, the start goes on in every profile, managed
    included, with nothing logged about test mode; barriers: the check evaluated ok, the JWT secret's info heard."""
    _h46("check_test_mode")
    configuration = _configure(monkeypatch, tmp_path, production=production)
    _profile(configuration, profile)
    states = {result.check_id: (result.severity, result.i18n_key) for result in run_config_checks() if result.check_id == "platform.test_mode"}
    expected_states = {"platform.test_mode": ("ok", f"instance.checks.testMode.{state}")}
    assert states == expected_states, f"Precondition: the audit evaluates check_test_mode, ok here as {state}: {states}"

    returned = log_configuration_audit()

    assert returned is None, f"the start goes on: log_configuration_audit() returns None, not {returned!r}"
    checks = [fields.get("check") for _, _, fields in logged]
    assert "platform.jwt_secret" in checks, f"Barrier: the audit's record of the unset JWT secret must reach the recorder, or the silence about test mode proves nothing: {logged}"
    assert "platform.test_mode" not in checks, f"test mode {state}: nothing about it is logged: {logged}"
    print_success(f"LIBREFOLIO_PROFILE={profile!r}, test mode {state}: the start went on, nothing logged about it")


@pytest.mark.parametrize(
    ("lane", "blocked", "profile"),
    [
        pytest.param(None, None, "managed", id="lane-unset"),
        pytest.param("", None, "managed", id="lane-empty"),
        pytest.param("   ", None, "managed", id="lane-blank"),
        pytest.param(None, "true", "managed", id="lane-unset-instance-blocked"),
        pytest.param(None, None, " MANAGED ", id="lane-unset-managed-in-any-case"),
    ],
)
def test_startup_stops_on_test_mode_outside_a_test_lane_in_the_managed_profile(configuration, logged, lane, blocked, profile):
    """(h)(e) H-46: managed, as Settings reads it, test mode outside a lane stops the start with ``ManagedTestModeError``,
    its message word for word, right after the short-key stop: before the block's warning, with nothing logged."""
    error = _h46("ManagedTestModeError")
    data_dir = _outside_a_test_lane(configuration, lane)
    configuration.set(LIBREFOLIO_PROFILE=profile)
    if blocked is not None:
        configuration.set(LIBREFOLIO_BLOCKED=blocked)
    assert get_settings().LIBREFOLIO_PROFILE == "managed", f"Precondition: Settings must read LIBREFOLIO_PROFILE={profile!r} as managed"
    assert instance_blocked() == (blocked is not None), f"Precondition: with LIBREFOLIO_BLOCKED={blocked!r} instance_blocked() must be {blocked is not None}: a blocked instance logs a warning unless the stop comes first"
    assert getattr(config_audit.logger, "records", None) is logged, "Precondition: the module's logger is this test's recorder, so a record logged before the stop would be heard"

    with pytest.raises(error) as raised:
        log_configuration_audit()

    expected = MANAGED_TEST_MODE_STOP.format(data_dir=data_dir)
    assert str(raised.value) == expected, f"the startup error must say why and what to do, word for word:\n  expected {expected!r}\n  got      {str(raised.value)!r}"
    assert logged == [], f"nothing is logged before the start is stopped, the block's warning included: {logged}"
    print_success(f"start stopped: {raised.value}")


def test_a_short_jwt_secret_stops_a_managed_start_before_test_mode_outside_a_test_lane(configuration, logged):
    """(h)(e) H-46: managed with both stops armed, a JWT_SECRET of 31 characters and test mode outside a lane: the short
    key's ``WeakSecretError`` still comes first, with nothing logged."""
    check_test_mode = _h46("check_test_mode")
    stops = (WeakSecretError, _h46("ManagedTestModeError"))
    _outside_a_test_lane(configuration)
    configuration.set(LIBREFOLIO_PROFILE="managed", JWT_SECRET="x" * 31)
    armed = [(result.check_id, result.severity) for result in (check_jwt_secret(), check_test_mode())]
    assert armed == [("platform.jwt_secret", "error"), ("platform.test_mode", "error")], f"Precondition: both stops armed, each check an error on its own: {armed}"

    with pytest.raises(stops) as raised:
        log_configuration_audit()

    assert isinstance(raised.value, WeakSecretError), f"the short key's stop stays first, before the test mode's: {raised.value!r}"
    expected = "In the managed profile the session signing key from JWT_SECRET must be at least 32 characters long; it is 31"
    assert str(raised.value) == expected, f"the startup error must be the short key's:\n  expected {expected!r}\n  got      {str(raised.value)!r}"
    assert logged == [], f"nothing is logged before the start is stopped: {logged}"
    print_success(f"start stopped first by the short key: {raised.value}")


# =============================================================================
# (i) The test lane id within the readiness probe's bounds (H-49)
# =============================================================================


def _lane_id(length: int) -> str:
    """(i) A lane id of ``length`` characters, clearly fake and without whitespace: ``h49-lane-``, then hexadecimal digits."""
    return ("h49-lane-" + "0123456789abcdef" * 8)[:length]


#: (i) Lane ids within the bounds, so a test lane: each with its length as set and once stripped.
LANES_WITHIN_THE_BOUNDS = [
    pytest.param(_lane_id(16), 16, 16, id="16-characters-the-minimum"),
    pytest.param(_lane_id(128), 128, 128, id="128-characters-the-maximum"),
    pytest.param(f"  {_lane_id(16)}  ", 20, 16, id="16-characters-padded-with-spaces-to-20"),
]
#: (i) Lane ids out of the bounds, so no test lane: the same shape.
LANES_OUT_OF_THE_BOUNDS = [
    pytest.param(_lane_id(15), 15, 15, id="15-characters-one-below-the-minimum"),
    pytest.param(_lane_id(129), 129, 129, id="129-characters-one-above-the-maximum"),
    pytest.param(f"  {_lane_id(15)}   ", 20, 15, id="15-characters-padded-with-spaces-to-20"),
]


def _with_lane_id(configuration: Configuration, lane: str, length: int, stripped: int) -> str:
    """(i) Test mode on with ``LIBREFOLIO_TEST_LANE_ID`` set to ``lane``, verified to hold ``length`` characters as set and
    ``stripped`` once stripped. Returns the data directory the check names, verified to be this test's own test data
    directory."""
    configuration.set(LIBREFOLIO_TEST_LANE_ID=lane)
    assert (len(lane), len(lane.strip())) == (length, stripped), f"Precondition: the lane id of this case must hold {length} characters, {stripped} once stripped, not {len(lane)} and {len(lane.strip())}"
    assert is_test_mode(), f"Precondition: LIBREFOLIO_TEST_MODE={os.environ.get('LIBREFOLIO_TEST_MODE')!r} must turn test mode on"
    data_dir = str(get_data_dir())
    assert data_dir == str(configuration.data_dir), f"Precondition: in test mode the data directory must be this test's test data directory, {configuration.data_dir}, not {data_dir}"
    return data_dir


@pytest.mark.parametrize(("name", "expected"), [pytest.param("TEST_LANE_ID_MIN_LENGTH", 16, id="minimum-16"), pytest.param("TEST_LANE_ID_MAX_LENGTH", 128, id="maximum-128")])
def test_the_lane_id_bounds_are_pinned_by_value(name, expected):
    """(i) H-49: the bounds of a test lane id are these integers, the bounds the readiness probe has always given its
    token: 16 and 128 characters."""
    print_section("H-49: the test lane id within the readiness probe's bounds")

    bound = _h49(name)

    assert (type(bound), bound) == (int, expected), f"H-49: backend.app.config.platform.{name} must be the integer {expected}, not {bound!r}"
    print_success(f"{name} = {bound}")


def test_the_readiness_probe_takes_a_token_within_the_same_bounds():
    """(i) H-49: the ``token`` of ``GET /api/v1/system/test-lane-health`` is a ``str`` whose ``Query`` has
    ``TEST_LANE_ID_MIN_LENGTH`` as its ``min_length`` and ``TEST_LANE_ID_MAX_LENGTH`` as its ``max_length``: a lane id
    the check counts as a lane is a token the probe takes, and one the probe refuses is no lane. Read from the
    ``Annotated`` metadata of the parameter, where pydantic keeps the two as ``MinLen`` and ``MaxLen``;
    ``test_lane_health`` is never called."""
    bounds = (_h49("TEST_LANE_ID_MIN_LENGTH"), _h49("TEST_LANE_ID_MAX_LENGTH"))
    token = get_type_hints(health_api.test_lane_health, include_extras=True).get("token")
    assert get_origin(token) is Annotated, f"Precondition: the token of test_lane_health must be Annotated with its Query, not {token!r}"
    queries = [extra for extra in get_args(token)[1:] if isinstance(extra, fastapi_params.Query)]
    assert get_args(token)[0] is str and len(queries) == 1, f"Precondition: the token of test_lane_health must be a str with one Query: {token!r}"

    metadata = queries[0].metadata
    probe = ([item.min_length for item in metadata if isinstance(item, MinLen)], [item.max_length for item in metadata if isinstance(item, MaxLen)])

    assert probe == ([bounds[0]], [bounds[1]]), f"H-49: the probe must take a token of TEST_LANE_ID_MIN_LENGTH to TEST_LANE_ID_MAX_LENGTH characters, {bounds[0]} to {bounds[1]}: its Query has the minimum lengths {probe[0]} and the maximum lengths {probe[1]}"
    print_success(f"test_lane_health's token: {bounds[0]} to {bounds[1]} characters, the bounds of a lane id")


def test_the_lane_of_this_file_stays_within_the_bounds():
    """(i) H-49: ``FAKE_LANE_ID``, the lane ``_configure`` gives every test-mode configuration of this file, is within the
    bounds: every case of (h) in a test lane stays in one, and none changes its outcome."""
    minimum, maximum = _h49("TEST_LANE_ID_MIN_LENGTH"), _h49("TEST_LANE_ID_MAX_LENGTH")

    length = len(FAKE_LANE_ID.strip())

    assert minimum <= length <= maximum, f"FAKE_LANE_ID must stay a test lane: it holds {length} characters once stripped, the bounds are {minimum} to {maximum}"
    print_success(f"FAKE_LANE_ID: {length} characters, within {minimum} to {maximum}")


@pytest.mark.parametrize(("lane", "length", "stripped"), LANES_WITHIN_THE_BOUNDS)
def test_the_test_mode_check_is_ok_with_a_lane_id_within_the_bounds(configuration, lane, length, stripped):
    """(i) H-49: test mode on with a lane id that holds, once stripped, between the two bounds of characters, both
    included, is in a test lane: ok, ``instance.checks.testMode.testLane``, with no detail and no summary. A control,
    green before H-49 and after: a cure off by one at a bound, or refusing an id padded with spaces, turns it red."""
    check_test_mode = _h46("check_test_mode")
    _with_lane_id(configuration, lane, length, stripped)

    result = check_test_mode()

    _assert_check(result, check_test_mode, "ok", "testMode.testLane", {})
    assert result.summary == "", f"an ok check has no summary: {result.summary!r}"
    print_success(f"LIBREFOLIO_TEST_LANE_ID of {length} characters, {stripped} once stripped: ok {result.i18n_key}")


@pytest.mark.parametrize(("lane", "length", "stripped"), LANES_OUT_OF_THE_BOUNDS)
def test_the_test_mode_check_is_an_error_with_a_lane_id_out_of_the_bounds(configuration, lane, length, stripped):
    """(i) H-49: test mode on with a lane id that holds, once stripped, fewer characters than the minimum or more than the
    maximum is outside a test lane, as without a lane id (h): an error, ``instance.checks.testMode.outsideTestLane``,
    naming the test data directory in its detail and in its summary."""
    check_test_mode = _h46("check_test_mode")
    summary = _h46("TEST_MODE_OUTSIDE_LANE_SUMMARY")
    data_dir = _with_lane_id(configuration, lane, length, stripped)

    result = check_test_mode()

    _assert_check(result, check_test_mode, "error", "testMode.outsideTestLane", {"data_dir": data_dir})
    expected = summary.format(data_dir=data_dir)
    assert result.summary == expected, f"check_test_mode() outside a test lane: its summary must be TEST_MODE_OUTSIDE_LANE_SUMMARY with the data directory, word for word:\n  expected {expected!r}\n  got      {result.summary!r}"
    print_success(f"LIBREFOLIO_TEST_LANE_ID of {length} characters, {stripped} once stripped: error {result.i18n_key}")


@pytest.mark.parametrize(("lane", "length", "stripped"), LANES_OUT_OF_THE_BOUNDS)
def test_startup_stops_on_a_lane_id_out_of_the_bounds_in_the_managed_profile(configuration, logged, lane, length, stripped):
    """(i)(h) H-49: managed, test mode on with a lane id out of the bounds stops the start as outside a test lane:
    ``ManagedTestModeError``, the message of (h) word for word, nothing logged first."""
    error = _h46("ManagedTestModeError")
    data_dir = _with_lane_id(configuration, lane, length, stripped)
    configuration.set(LIBREFOLIO_PROFILE="managed")
    assert get_settings().LIBREFOLIO_PROFILE == "managed", "Precondition: Settings must read LIBREFOLIO_PROFILE=managed as managed"
    assert getattr(config_audit.logger, "records", None) is logged, "Precondition: the module's logger is this test's recorder, so a record logged before the stop would be heard"

    with pytest.raises(error) as raised:
        log_configuration_audit()

    expected = MANAGED_TEST_MODE_STOP.format(data_dir=data_dir)
    assert str(raised.value) == expected, f"the startup error must be the one of test mode outside a test lane, word for word:\n  expected {expected!r}\n  got      {str(raised.value)!r}"
    assert logged == [], f"nothing is logged before the start is stopped: {logged}"
    print_success(f"LIBREFOLIO_TEST_LANE_ID of {length} characters, {stripped} once stripped: start stopped")


@pytest.mark.parametrize(("lane", "length", "stripped"), LANES_WITHIN_THE_BOUNDS)
def test_a_managed_start_goes_on_with_a_lane_id_within_the_bounds(configuration, logged, lane, length, stripped):
    """(i)(h) H-49: managed, test mode on with a lane id within the bounds is in a test lane: the start goes on, with
    nothing logged about test mode. Barriers: the check evaluated ok, the unset JWT secret's info heard. A control, green
    before H-49 and after."""
    _h46("check_test_mode")
    _with_lane_id(configuration, lane, length, stripped)
    configuration.set(LIBREFOLIO_PROFILE="managed")
    assert get_settings().LIBREFOLIO_PROFILE == "managed", "Precondition: Settings must read LIBREFOLIO_PROFILE=managed as managed"
    states = {result.check_id: (result.severity, result.i18n_key) for result in run_config_checks() if result.check_id == "platform.test_mode"}
    assert states == {"platform.test_mode": ("ok", "instance.checks.testMode.testLane")}, f"Precondition: the audit evaluates check_test_mode, ok in a test lane: {states}"

    returned = log_configuration_audit()

    assert returned is None, f"the start goes on: log_configuration_audit() returns None, not {returned!r}"
    checks = [fields.get("check") for _, _, fields in logged]
    assert "platform.jwt_secret" in checks, f"Barrier: the audit's record of the unset JWT secret must reach the recorder, or the silence about test mode proves nothing: {logged}"
    assert "platform.test_mode" not in checks, f"in a test lane, nothing about test mode is logged: {logged}"
    print_success(f"LIBREFOLIO_TEST_LANE_ID of {length} characters, {stripped} once stripped: the start went on, nothing logged about test mode")
