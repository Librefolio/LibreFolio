"""Masking of the secrets a plugin call carries: in the errors it raises and in the log lines written while it runs.

The plugin-settings core (``services/plugin_settings/``) hands a plugin its secrets right before a call. For the length
of that call they are «in flight» (``secrets_in_flight``): a ``ContextVar`` holds them, and ``asyncio.to_thread`` copies
it into the provider's thread, so every line logged there is masked by value, by the structlog processor
(``mask_event_dict``) and, for the records of libraries that log through the standard ``logging`` module, by the handler
filter (``SecretMaskingFilter``). When the call raises, the boundary masks the exception and its whole chain in place
(``mask_exception``): a message built later from ``str(error)`` — an API result, a stored error, a traceback in the
log — no longer carries the secret.

A value is replaced by ``***``, and so are its URL-encoded forms, the way a provider that puts a key in a query string
would see it written in an error. Any value is judged by the text it shows (``str()`` and ``repr()``): a URL object,
bytes or an exception kept as a detail that shows a secret becomes its masked text. This is a last line of defence: a
plugin never returns, logs or raises a secret on purpose. Threads a library starts by itself do not inherit the
``ContextVar``; their records are not masked by context. An exception whose text a ``__str__`` of its own builds from
private state cannot be rewritten: ``exception_renders_secret`` tells, and the boundaries raise a new error in its place.

A leaf of the standard library only: ``logging_config.py`` imports it.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any
from urllib.parse import quote, quote_plus

MASK = "***"

_ACTIVE: ContextVar[frozenset[str]] = ContextVar("lf_secrets_in_flight", default=frozenset())


@contextmanager
def secrets_in_flight(values: frozenset[str]) -> Iterator[None]:
    """Mask ``values`` in this context's log lines and in the threads it starts, until the block ends."""
    if not values:
        yield
        return
    token = _ACTIVE.set(_ACTIVE.get() | values)
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def active_secrets() -> frozenset[str]:
    """The secrets in flight in this context."""
    return _ACTIVE.get()


def _forms(values: frozenset[str]) -> list[str]:
    """Each value and its URL-encoded forms, the longest first, so a value inside another is replaced last."""
    forms = set()
    for value in values:
        if value:
            forms.update({value, quote(value, safe=""), quote_plus(value)})
    return sorted(forms, key=len, reverse=True)


def mask_text(text: str, values: frozenset[str] | None = None) -> str:
    """``text`` with every secret of ``values`` (by default, those in flight) replaced by ``***``."""
    secrets = active_secrets() if values is None else values
    if not secrets or not text:
        return text
    for form in _forms(secrets):
        if form in text:
            text = text.replace(form, MASK)
    return text


def _rendered(value: Any) -> Iterator[str]:
    """The texts a value shows: its ``str()`` and its ``repr()``, those that can be computed."""
    for render in (str, repr):
        try:
            yield render(value)
        except Exception:  # noqa: BLE001 — a value that cannot be rendered shows nothing
            continue


def _mask_value(value: Any, values: frozenset[str]) -> Any:
    """``value`` with its secrets masked.

    Strings are masked; dicts, lists, tuples and sets are copied with their keys and items masked. Any other value that
    shows a secret in its text or its representation (a URL object, bytes, a number, an exception kept as a detail, a
    dict subclass) becomes its masked text; one that shows none is returned as it is.
    """
    if isinstance(value, str):
        return mask_text(value, values)
    if type(value) is dict:
        return {_mask_value(key, values): _mask_value(item, values) for key, item in value.items()}
    if type(value) in (list, tuple, set, frozenset):
        return type(value)(_mask_value(item, values) for item in value)
    for text in _rendered(value):
        masked = mask_text(text, values)
        if masked != text:
            return masked
    return value


def _chain(error: BaseException) -> Iterator[BaseException]:
    """``error``, the links of its cause and context chain and the members of its exception groups, once each."""
    seen: set[int] = set()
    pending: list[BaseException] = [error]
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        pending.extend(link for link in (current.__cause__, current.__context__) if link is not None)
        if isinstance(current, BaseExceptionGroup):
            pending.extend(current.exceptions)


#: Attributes that build the text of an exception without being in its ``__dict__``.
_TEXT_ATTRIBUTES = ("message", "details")
_OS_ERROR_TEXT_ATTRIBUTES = ("strerror", "filename", "filename2")


def mask_exception(error: BaseException, values: frozenset[str]) -> None:
    """Mask ``values`` in place in ``error``, in its cause and context chain and in the members of an exception group.

    The arguments are rewritten, and so is every attribute that shows a secret: ``message`` and ``details`` (an
    ``AssetSourceError``), the notes, an ``OSError``'s text and file names, an attribute of a plugin's own exception.
    The type and the traceback stay, so the callers' ``except`` clauses behave as before.
    """
    if not values:
        return
    for current in _chain(error):
        try:
            current.args = tuple(_mask_value(argument, values) for argument in current.args)
        except (AttributeError, TypeError):
            pass
        names = [*getattr(current, "__dict__", {}), *_TEXT_ATTRIBUTES]
        if isinstance(current, OSError):
            names.extend(_OS_ERROR_TEXT_ATTRIBUTES)
        for name in dict.fromkeys(names):
            try:
                attribute = getattr(current, name)
            except Exception:  # noqa: BLE001 — an attribute that cannot be read shows nothing
                continue
            masked = _mask_value(attribute, values)
            if masked is attribute:
                continue
            try:
                setattr(current, name, masked)
            except (AttributeError, TypeError):
                pass


def exception_renders_secret(error: BaseException, values: frozenset[str]) -> bool:
    """Whether ``error``, or a link of its chain, still shows one of ``values`` in its text or in its notes."""
    if not values:
        return False
    for current in _chain(error):
        texts = list(_rendered(current))
        notes = getattr(current, "__notes__", None)
        if isinstance(notes, (list, tuple)):
            texts.extend(str(note) for note in notes)
        if any(mask_text(text, values) != text for text in texts):
            return True
    return False


def masked_description(error: BaseException, values: frozenset[str]) -> str:
    """``Type: text`` of ``error``, masked: what a boundary says of an error it has to replace."""
    text = next(_rendered(error), "")
    return mask_text(f"{type(error).__name__}: {text}" if text else type(error).__name__, values)


def mask_event_dict(_logger: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """structlog processor: mask the secrets in flight in every value of the event, the formatted traceback included."""
    secrets = active_secrets()
    if not secrets:
        return event_dict
    return {key: _mask_value(value, secrets) for key, value in event_dict.items()}


class SecretMaskingFilter(logging.Filter):
    """Mask the secrets in flight in the records of the standard ``logging`` module, before a handler writes them.

    The message is formatted once and replaced by its masked text; a traceback is formatted and masked too. A record
    with nothing to mask is left exactly as it is.
    """

    _formatter = logging.Formatter()

    def filter(self, record: logging.LogRecord) -> bool:
        secrets = active_secrets()
        if not secrets:
            return True
        message = record.getMessage()
        masked = mask_text(message, secrets)
        if masked != message:
            record.msg, record.args = masked, None
        if record.exc_info and not record.exc_text:
            record.exc_text = self._formatter.formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = mask_text(record.exc_text, secrets)
        return True
