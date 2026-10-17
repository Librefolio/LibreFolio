"""The links an email carries: built only from ``LIBREFOLIO_PUBLIC_URL`` (developer decision 45).

Every link inside an email, the ones an administrator sends included, is ``LIBREFOLIO_PUBLIC_URL`` followed by the path
of the page that takes the token (``token_path``, the token in the fragment). Nothing in a request — its host, its
``Origin``, a link the browser sends — ever becomes part of an emailed link: a stranger could otherwise have a real token
sent to a user inside a link to a site of theirs. Without the variable, no email with a link goes out; the links an
administrator copies from the interface stay as they are.

Whether the address really reaches this instance is checked by the administrator's browser, with the address probe of
workstream A: the server cannot know how its users reach it.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from backend.app.config.accounts import public_url
from backend.app.db.models import AccountTokenPurpose
from backend.app.schemas.email import EmailInstanceConfig
from backend.app.services.accounts import token_service
from backend.app.services.accounts.registration_service import public_link
from backend.app.services.email.delivery import EmailError, email_config_state, sending_blocked


class EmailLinksUnavailableError(EmailError):
    """No email with a link can go out: ``LIBREFOLIO_PUBLIC_URL`` is not set, or cannot start a link (``_usable_base``)."""


@dataclass(frozen=True)
class LinksState:
    """Whether emails can carry links: ``base`` is ``LIBREFOLIO_PUBLIC_URL``, ``problem`` says why not."""

    base: str | None
    problem: str | None

    @property
    def ready(self) -> bool:
        return self.base is not None and self.problem is None

    @property
    def instance(self) -> str:
        """The instance as an email names it: the host of ``LIBREFOLIO_PUBLIC_URL``, with its port."""
        return urlsplit(self.base).netloc if self.base else ""


def _usable_base(base: str) -> bool:
    """Whether ``base`` can start an emailed link: http(s), a host and a valid port, no credentials, no whitespace, and
    no ``?`` or ``#`` at all (even an empty query or fragment would swallow the path that follows).

    ``public_url()`` (``config.env_url``) already refuses whitespace, any scheme but http(s), an address without a host
    name and, since X-R35, user info. This check adds what it leaves, ``?``, ``#`` and an invalid port, and keeps the
    others as a second guard: the base starts every link of every email, and credentials would travel in all of them.
    """
    if any(char.isspace() for char in base) or "?" in base or "#" in base:
        return False
    try:
        parts = urlsplit(base)
        parts.port  # noqa: B018 — reading it is what validates the port
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.hostname) and parts.username is None and parts.password is None


def links_state() -> LinksState:
    """``LIBREFOLIO_PUBLIC_URL`` as read now: ready, missing or invalid. Never raises."""
    try:
        base = public_url()
    except ValueError:
        return LinksState(base=None, problem="PUBLIC_URL_INVALID")
    if base is None:
        return LinksState(base=None, problem="PUBLIC_URL_MISSING")
    if not _usable_base(base):
        return LinksState(base=None, problem="PUBLIC_URL_INVALID")
    return LinksState(base=base, problem=None)


def require_links() -> LinksState:
    """The state of the links when emails can carry them; ``EmailLinksUnavailableError`` otherwise."""
    state = links_state()
    if not state.ready:
        raise EmailLinksUnavailableError(state.problem or "PUBLIC_URL_MISSING")
    return state


def email_link(purpose: AccountTokenPurpose, token: str) -> str:
    """The link to the page that takes ``token``, on ``LIBREFOLIO_PUBLIC_URL``; ``EmailLinksUnavailableError`` without
    a usable one."""
    require_links()
    link = public_link(token_service.token_path(purpose, token))
    if link is None:
        raise EmailLinksUnavailableError(links_state().problem or "PUBLIC_URL_MISSING")
    return link


def email_instance_config() -> EmailInstanceConfig:
    """The email part of ``GET /system/instance``: whether email works, and whether emails with a link can go out.

    A blocked instance sends nothing, so both are false while the hosting provider blocks it. It may read the password
    file of ``LIBREFOLIO_SMTP_PASSWORD_FILE``: an async caller runs it in a worker thread.
    """
    available = email_config_state().usable and not sending_blocked()
    return EmailInstanceConfig(available=available, links=available and links_state().ready)
