"""The emails LibreFolio sends: their texts in the four languages of the interface, and the message with its headers.

Each kind of email has a builder (``build_password_reset``, ``build_password_reset_after_restore``, ``build_invite``, ``build_verification``,
``build_admin_setup``, ``build_test_message``, ``build_email_changed``, ``build_email_changed_new_address``, ``build_email_change_confirmation``,
``build_email_change_request_confirmation``, ``build_email_change_requested``) that returns an ``EmailContent``: a subject, a plain-text part and an
HTML part, in the language asked for (``email_language``: an unknown one is English). The texts live in
``templates/<language>.json``, one file per language with the same keys and the same ``$placeholders``; the HTML layout
in ``templates/layout.html``, whose green header shows the logo (``templates/logo.png``, attached inline by ``compose_message``). Every value that comes from a person — a user name, the name of the instance, who sent an
invitation — is escaped in the HTML part, and none goes into a subject. The emails a stranger can have sent to an
address of their choice (a password reset, an email verification, the notice and the confirmation of an email change, the
confirmation and the notice of a change asked from Profile) carry no text of
theirs: their builders take no user name and nothing of the other address (night decision N62). ``compose_message`` adds
the headers.

Nothing here sends anything, reads the configuration or logs: ``delivery.send_email`` does.
"""

from __future__ import annotations

import html
import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from enum import StrEnum
from pathlib import Path
from string import Template

from babel.dates import format_timedelta

from backend.app.utils.datetime_utils import ensure_utc, utcnow

#: The languages of the emails: the ``default_language`` choices of the global settings, the languages of the interface.
EMAIL_LANGUAGES: tuple[str, ...] = ("en", "it", "fr", "es")

_TEMPLATES = Path(__file__).with_name("templates")


class EmailKind(StrEnum):
    """What an email is for."""

    PASSWORD_RESET = "password_reset"
    INVITE = "invite"
    EMAIL_VERIFICATION = "email_verification"
    ADMIN_SETUP = "admin_setup"
    TEST = "test"
    EMAIL_CHANGED = "email_changed"
    EMAIL_CHANGE_CONFIRMATION = "email_change_confirmation"
    EMAIL_CHANGE_REQUEST = "email_change_request"


@dataclass(frozen=True)
class EmailContent:
    """One email, rendered in one language: the subject, the plain-text part and the HTML part."""

    kind: EmailKind
    language: str
    subject: str
    text: str
    html: str


def _load_catalogs() -> dict[str, dict[str, dict[str, str]]]:
    """The texts of every language, read once when the module is imported."""
    return {language: json.loads((_TEMPLATES / f"{language}.json").read_text(encoding="utf-8")) for language in EMAIL_LANGUAGES}


_CATALOGS = _load_catalogs()
_LAYOUT = Template((_TEMPLATES / "layout.html").read_text(encoding="utf-8"))

#: The logo in the green header: a small PNG that travels inside the message as an inline attachment, which the HTML part
#: names with ``cid:``. A ``data:`` image is blocked by Gmail, and a link to the site would need ``LIBREFOLIO_PUBLIC_URL``.
LOGO_CONTENT_ID = "librefolio-logo@librefolio.local"
_LOGO_PNG = (_TEMPLATES / "logo.png").read_bytes()

_PARAGRAPH = '<p style="margin:0 0 16px;">{}</p>'
_BUTTON = '<p style="margin:24px 0;"><a href="{href}" style="display:inline-block;background-color:#1b4334;color:#ffffff;text-decoration:none;font-weight:bold;padding:12px 22px;border-radius:8px;">{label}</a></p>'
_FALLBACK = '<p style="margin:0 0 16px;font-size:13px;color:#4b5563;">{hint}<br><a href="{href}" style="color:#1b4334;word-break:break-all;">{text}</a></p>'


def supported_email_language(language: str | None) -> str | None:
    """The email language ``language`` names (``it``, ``it-IT``, ``it_IT`` and ``IT`` are ``it``), or ``None`` when it
    names none of the four."""
    code = (language or "").strip().lower().replace("_", "-").split("-", 1)[0]
    return code if code in EMAIL_LANGUAGES else None


def email_language(language: str | None) -> str:
    """The language of an email: ``it``, ``it-IT``, ``it_IT`` and ``IT`` are ``it``; an unknown one, or none, is ``en``."""
    return supported_email_language(language) or "en"


def _checked_link(link: str) -> str:
    """A link an email may carry: http(s) only, on one line, without spaces."""
    if not isinstance(link, str) or not link.lower().startswith(("http://", "https://")) or any(char.isspace() for char in link):
        raise ValueError("an email link must be an http:// or https:// address without spaces")
    return link


def _fill(template: str, values: Mapping[str, str]) -> str:
    return Template(template).substitute(values)


#: Bidirectional embeddings, overrides and isolates: removed, so a value cannot reorder the text around it.
_BIDI_CONTROLS = frozenset("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")


def _one_line(value: str) -> str:
    """A value as a single line of plain text: control characters and line or paragraph separators become spaces.

    A username may hold any character: without this, it could add lines of its own to the plain-text part.
    """
    return "".join(" " if unicodedata.category(char) in ("Cc", "Zl", "Zp") else char for char in value if char not in _BIDI_CONTROLS)


def _render(
    kind: EmailKind,
    language: str,
    *,
    greeting: str,
    before: list[str],
    after: list[str],
    values: Mapping[str, str],
    link: str | None = None,
    subject_key: str = "subject",
) -> EmailContent:
    """Assemble the two parts of an email from the keys of its section, filled with ``values`` (each on one line)."""
    catalog = _CATALOGS[language]
    section = catalog[kind.value]
    values = {key: _one_line(value) for key, value in values.items()}
    lines_before = [_fill(section[key], values) for key in before]
    lines_after = [_fill(section[key], values) for key in after]
    opening = _fill(catalog["common"][greeting], values)
    footer = _fill(catalog["common"]["footer"], values)

    text_blocks = [opening, *lines_before]
    html_blocks = [_PARAGRAPH.format(html.escape(line)) for line in (opening, *lines_before)]
    if link is not None:
        action = section["action"]
        href = html.escape(link, quote=True)
        text_blocks.append(f"{action}\n{link}")
        html_blocks.append(_BUTTON.format(href=href, label=html.escape(action)))
        html_blocks.append(_FALLBACK.format(hint=html.escape(catalog["common"]["button_fallback"]), href=href, text=href))
    text_blocks.extend(lines_after)
    html_blocks.extend(_PARAGRAPH.format(html.escape(line)) for line in lines_after)

    text = "\n\n".join(text_blocks) + f"\n\n-- \n{footer}\n"
    page = _LAYOUT.substitute(lang=language, subject=html.escape(section[subject_key]), body="\n".join(html_blocks), footer=html.escape(footer), logo_cid=LOGO_CONTENT_ID)
    return EmailContent(kind=kind, language=language, subject=section[subject_key], text=text, html=page)


def _duration(ttl: timedelta, language: str) -> str:
    return format_timedelta(ttl, locale=language)


def build_password_reset(*, language: str | None, link: str, ttl: timedelta, instance: str) -> EmailContent:
    """The link to choose a new password, for the owner of an account. No user name: a stranger can have it sent (N62)."""
    lang = email_language(language)
    values = {"instance": instance, "duration": _duration(ttl, lang)}
    return _render(EmailKind.PASSWORD_RESET, lang, greeting="greeting_anonymous", before=["intro"], after=["expiry", "ignore"], values=values, link=_checked_link(link))


def build_password_reset_after_restore(*, language: str | None, link: str, ttl: timedelta, instance: str) -> EmailContent:
    """The reset link for the owner of an instance restored from a backup (A5-5): the same email, with why the password is gone.

    The password of the owner's account was revoked at the restore, for the owner's security, whoever asked for the restore:
    the text says so, offers the link, and names «forgot password» for when the link expires. All its words are the keys
    ``restore_*`` of the ``password_reset`` section, one place for the four languages. Like the plain reset it takes no user name and
    no address, and it does not say who restored the backup.
    """
    lang = email_language(language)
    values = {"instance": instance, "duration": _duration(ttl, lang)}
    return _render(
        EmailKind.PASSWORD_RESET,
        lang,
        greeting="greeting_anonymous",
        before=["restore_intro", "restore_note"],
        after=["expiry", "restore_fallback", "restore_unexpected"],
        values=values,
        link=_checked_link(link),
        subject_key="restore_subject",
    )


def build_invite(
    *,
    language: str | None,
    link: str,
    ttl: timedelta,
    instance: str,
    inviter: str | None = None,
    grants_admin: bool = False,
) -> EmailContent:
    """An invitation to create an account: who sent it when known, and whether the account will be an administrator."""
    lang = email_language(language)
    values = {"instance": instance, "duration": _duration(ttl, lang), "inviter": inviter or ""}
    before = ["intro" if inviter else "intro_anonymous"] + (["admin_role"] if grants_admin else [])
    return _render(EmailKind.INVITE, lang, greeting="greeting_anonymous", before=before, after=["expiry", "ignore"], values=values, link=_checked_link(link))


def build_verification(*, language: str | None, link: str, ttl: timedelta, instance: str) -> EmailContent:
    """The link that confirms the address of an account. No user name: whoever registers chooses both (N62)."""
    lang = email_language(language)
    values = {"instance": instance, "duration": _duration(ttl, lang)}
    return _render(EmailKind.EMAIL_VERIFICATION, lang, greeting="greeting_anonymous", before=["intro"], after=["expiry", "ignore"], values=values, link=_checked_link(link))


def build_admin_setup(*, language: str | None, username: str, link: str, ttl: timedelta, instance: str) -> EmailContent:
    """The link that activates the first administrator of a new instance."""
    lang = email_language(language)
    values = {"username": username, "instance": instance, "duration": _duration(ttl, lang)}
    return _render(EmailKind.ADMIN_SETUP, lang, greeting="greeting", before=["intro"], after=["expiry", "ignore"], values=values, link=_checked_link(link))


def build_test_message(*, language: str | None, username: str, instance: str) -> EmailContent:
    """The test email an administrator sends to themselves: no link."""
    lang = email_language(language)
    values = {"username": username, "instance": instance}
    return _render(EmailKind.TEST, lang, greeting="greeting", before=["intro"], after=["outro"], values=values)


def build_email_changed(*, language: str | None, instance: str, by_host: bool = False) -> EmailContent:
    """The notice to the address an account had before, when its email address changes. No link, no user name and
    nothing of the new address, which whoever changes it chooses, down to the last label of its domain (N62).

    ``by_host``: the host of a managed instance decided the change (A-64 (c)): the advice is to ask the host, not to
    change the password — nobody else has the account.
    """
    lang = email_language(language)
    values = {"instance": instance}
    if by_host:
        return _render(EmailKind.EMAIL_CHANGED, lang, greeting="greeting_anonymous", before=["intro_host"], after=["advice_host"], values=values)
    return _render(EmailKind.EMAIL_CHANGED, lang, greeting="greeting_anonymous", before=["intro"], after=["advice"], values=values)


def build_email_changed_new_address(*, language: str | None, instance: str, by_host: bool = False) -> EmailContent:
    """The confirmation to the address an account has now, once its email address changed (UA2): this address is the
    account's now. No link, no user name and nothing of the old address: whoever changes the address chooses this
    recipient, so a stranger may receive it (N62).

    ``by_host``: the host of a managed instance asked for the change and the owner confirmed it from this address.
    """
    lang = email_language(language)
    values = {"instance": instance}
    if by_host:
        return _render(EmailKind.EMAIL_CHANGED, lang, greeting="greeting_anonymous", before=["new_intro_host"], after=["new_advice_host"], values=values, subject_key="new_subject")
    return _render(EmailKind.EMAIL_CHANGED, lang, greeting="greeting_anonymous", before=["new_intro"], after=["new_advice"], values=values, subject_key="new_subject")


def build_email_change_confirmation(*, language: str | None, username: str, link: str, ttl: timedelta, instance: str) -> EmailContent:
    """The link that completes the change of the owner's address (A5-1b), sent to the NEW address the host named.

    Its sender is trusted (the host's own variable, not a user), so it greets the owner by name, like the setup link.
    """
    lang = email_language(language)
    values = {"username": username, "instance": instance, "duration": _duration(ttl, lang)}
    return _render(EmailKind.EMAIL_CHANGE_CONFIRMATION, lang, greeting="greeting", before=["intro"], after=["expiry", "ignore"], values=values, link=_checked_link(link))


def build_email_change_request_confirmation(*, language: str | None, link: str, ttl: timedelta, instance: str) -> EmailContent:
    """The link that completes a change of address a user asked for from Profile, sent to the NEW address.

    Whoever asks chooses this recipient, so a stranger may read it: no user name and nothing of the old address (N62).
    It says that the link confirms only from inside the account that asked (D10): a stranger who clicks it can do nothing.
    """
    lang = email_language(language)
    values = {"instance": instance, "duration": _duration(ttl, lang)}
    return _render(EmailKind.EMAIL_CHANGE_REQUEST, lang, greeting="greeting_anonymous", before=["intro"], after=["expiry", "signin", "ignore"], values=values, link=_checked_link(link))


def build_email_change_requested(*, language: str | None, instance: str) -> EmailContent:
    """The notice to the address an account has now, when a change of address is asked from Profile (D5.1): nothing has
    changed yet, and changing the password cancels the request. No link, no user name and nothing of the new address (N62).
    """
    lang = email_language(language)
    values = {"instance": instance}
    return _render(EmailKind.EMAIL_CHANGE_REQUEST, lang, greeting="greeting_anonymous", before=["requested_intro"], after=["requested_advice"], values=values, subject_key="requested_subject")


class EmailRecipientError(ValueError):
    """The recipient is not exactly one bare address: nothing is composed, nothing is spent."""


def _single_address(to: str) -> str:
    """``to`` when it is exactly one bare address; ``EmailRecipientError`` otherwise: two addresses, a line break or any
    other whitespace, even at an end — nothing is trimmed, so nothing can smuggle a second header or recipient."""
    value = to if isinstance(to, str) else ""
    local, at, domain = value.rpartition("@")
    if not at or not local or not domain or "@" in local or any(char.isspace() or char in ',<>"' for char in value):
        raise EmailRecipientError("an email goes to exactly one address")
    return value


def compose_message(
    content: EmailContent,
    *,
    to: str,
    sender: tuple[str, str],
    reply_to: tuple[str, str] | None = None,
    now: datetime | None = None,
) -> EmailMessage:
    """The message to send: ``content`` with its headers, as ``multipart/alternative``: the plain text, then the HTML as ``multipart/related`` with the logo it names by ``cid:``.

    ``sender`` and ``reply_to`` are ``(display name, address)``. ``Auto-Submitted`` keeps auto-responders from
    answering; the ``Message-ID`` takes the domain of the sender.
    """
    recipient = _single_address(to)
    message = EmailMessage()
    message["Subject"] = content.subject
    message["From"] = Address(display_name=sender[0], addr_spec=sender[1])
    message["To"] = recipient
    if reply_to is not None:
        message["Reply-To"] = Address(display_name=reply_to[0], addr_spec=reply_to[1])
    message["Date"] = formatdate(ensure_utc(now or utcnow()).timestamp(), usegmt=True)
    message["Message-ID"] = make_msgid(domain=sender[1].rpartition("@")[2])
    message["Auto-Submitted"] = "auto-generated"
    message["X-Auto-Response-Suppress"] = "All"
    message.set_content(content.text)
    message.add_alternative(content.html, subtype="html")
    # The logo the HTML part shows: attached to the HTML part, so a client that shows only the plain text never sees it.
    message.get_payload()[1].add_related(_LOGO_PNG, "image", "png", cid=f"<{LOGO_CONTENT_ID}>", disposition="inline", filename="librefolio-logo.png")
    # After the body: setting it clears every Content-* header, and making it multipart moves them into the first part.
    message["Content-Language"] = content.language
    return message
