"""Configuration checks of the email section, in the shape of the platform's (``config_audit.ConfigCheck``).

Three checks: whether the SMTP configuration can be used, whether it sends in clear to a server outside the local
network, and whether emails can carry links (``LIBREFOLIO_PUBLIC_URL``, developer decision 45). Like every
configuration check, they read the configuration, change nothing, never raise, and never put a secret in their result;
their ``detail`` (shown to administrators) never names the host, the user nor the sender either: the SMTP configuration
is never shown in the interface. The i18n keys are ``email.checks.*``.

They are part of the platform's ``CONFIG_CHECKS``: the startup audit logs them, and ``GET /email/status`` shows them.
``config_audit`` imports this module to build that list, so this module imports ``ConfigCheck`` (and the links, which
bring in the accounts services) only when a check runs: either module can then be imported first.
"""

from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING

from backend.app.services.email.delivery import email_config_state
from backend.app.utils.runtime.network import classify_ip

if TYPE_CHECKING:
    from backend.app.services.platform.config_audit import ConfigCheck

#: Name suffixes of a local network: mDNS, the usual home and lab domains, and the loopback names.
_LOCAL_SUFFIXES = (".local", ".lan", ".home.arpa", ".internal", ".localhost")


def _host_is_local(host: str) -> bool:
    """Whether ``host`` is this machine or the local network: loopback, private and VPN ranges, single-label names
    (a Docker service, a host of the LAN) and the local suffixes. Names are judged as written: nothing is resolved."""
    name = host.strip().rstrip(".").lower()
    try:
        ipaddress.ip_address(name)
    except ValueError:
        return name == "localhost" or "." not in name or name.endswith(_LOCAL_SUFFIXES)
    return classify_ip(name) in ("loopback", "lan", "vpn")


def check_smtp_configuration() -> ConfigCheck:
    """The SMTP configuration: off (the default), usable, or set with a value that cannot be used (email stays off)."""
    from backend.app.services.platform.config_audit import ConfigCheck  # noqa: PLC0415 — config_audit imports this module

    check_id = "email.smtp"
    state = email_config_state()
    if not state.configured:
        return ConfigCheck(check_id, "ok", "email.checks.smtp.off")
    if state.problem is not None:
        return ConfigCheck(
            check_id,
            "error",
            "email.checks.smtp.invalid",
            {"problem": state.problem, "variable": state.variable or ""},
            f"{state.variable} cannot be used ({state.problem}): email stays off until it is fixed",
        )
    return ConfigCheck(check_id, "ok", "email.checks.smtp.ok")


def check_smtp_encryption() -> ConfigCheck:
    """``LIBREFOLIO_SMTP_TLS=none`` towards a server outside the local network: emails, links and password in clear."""
    from backend.app.services.platform.config_audit import ConfigCheck  # noqa: PLC0415 — config_audit imports this module

    check_id = "email.smtp_encryption"
    state = email_config_state()
    server = state.server
    if not state.usable or server is None or server.tls != "none":
        return ConfigCheck(check_id, "ok", "email.checks.smtpEncryption.ok")
    if _host_is_local(server.host):
        return ConfigCheck(check_id, "ok", "email.checks.smtpEncryption.localPlain")
    return ConfigCheck(
        check_id,
        "warning",
        "email.checks.smtpEncryption.plain",
        summary=f"LIBREFOLIO_SMTP_TLS=none with {server.host}: emails, their links and the SMTP password travel unencrypted; use starttls or tls",
    )


def check_email_links() -> ConfigCheck:
    """Emails can carry links only with ``LIBREFOLIO_PUBLIC_URL``: said when email works and the variable is missing
    (``info``) or cannot start a link (``warning``: not http(s), no host, a user name, a password, a ``?`` or ``#``,
    a space, a bad port). Email off: nothing to say."""
    from backend.app.services.email.links import links_state  # noqa: PLC0415 — keeps config_audit's imports light
    from backend.app.services.platform.config_audit import ConfigCheck  # noqa: PLC0415 — config_audit imports this module

    check_id = "email.links"
    links = links_state()
    if links.ready or not email_config_state().usable:
        return ConfigCheck(check_id, "ok", "email.checks.links.ok")
    if links.problem == "PUBLIC_URL_INVALID":
        return ConfigCheck(
            check_id,
            "warning",
            "email.checks.links.invalid",
            summary="LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out",
        )
    return ConfigCheck(
        check_id,
        "info",
        "email.checks.links.missing",
        summary="LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out",
    )


EMAIL_CONFIG_CHECKS = (check_smtp_configuration, check_smtp_encryption, check_email_links)
