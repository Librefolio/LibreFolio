"""Configuration checks of the email section, in the shape of the platform's (``config_audit.ConfigCheck``).

Two checks: whether the SMTP configuration can be used, and whether it sends in clear to a server outside the local
network. Like every configuration check, they read the configuration, change nothing, never raise, and never put a
secret in their result; their ``detail`` (shown to administrators) never names the host, the user nor the sender
either: the SMTP configuration is never shown in the interface. The i18n keys are ``email.checks.*``.

They join the platform's ``CONFIG_CHECKS`` in lot E2. ``config_audit`` is imported as a module, and ``ConfigCheck`` read
when a check runs, so that ``config_audit`` can import this module in turn.
"""

from __future__ import annotations

import ipaddress

from backend.app.services.email.delivery import email_config_state
from backend.app.services.platform import config_audit
from backend.app.utils.runtime.network import classify_ip

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


def check_smtp_configuration() -> config_audit.ConfigCheck:
    """The SMTP configuration: off (the default), usable, or set with a value that cannot be used (email stays off)."""
    check_id = "email.smtp"
    state = email_config_state()
    if not state.configured:
        return config_audit.ConfigCheck(check_id, "ok", "email.checks.smtp.off")
    if state.problem is not None:
        return config_audit.ConfigCheck(
            check_id,
            "error",
            "email.checks.smtp.invalid",
            {"problem": state.problem, "variable": state.variable or ""},
            f"{state.variable} cannot be used ({state.problem}): email stays off until it is fixed",
        )
    return config_audit.ConfigCheck(check_id, "ok", "email.checks.smtp.ok")


def check_smtp_encryption() -> config_audit.ConfigCheck:
    """``LIBREFOLIO_SMTP_TLS=none`` towards a server outside the local network: emails, links and password in clear."""
    check_id = "email.smtp_encryption"
    state = email_config_state()
    server = state.server
    if not state.usable or server is None or server.tls != "none":
        return config_audit.ConfigCheck(check_id, "ok", "email.checks.smtpEncryption.ok")
    if _host_is_local(server.host):
        return config_audit.ConfigCheck(check_id, "ok", "email.checks.smtpEncryption.localPlain")
    return config_audit.ConfigCheck(
        check_id,
        "warning",
        "email.checks.smtpEncryption.plain",
        summary=f"LIBREFOLIO_SMTP_TLS=none with {server.host}: emails, their links and the SMTP password travel unencrypted; use starttls or tls",
    )


EMAIL_CONFIG_CHECKS = (check_smtp_configuration, check_smtp_encryption)
