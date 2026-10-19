"""What an exception says about the failure behind it, and whether the log already has it (lot H-60).

The developer's rule (19/10/2026): when something fails, the useful information is printed, once, where the failure is
caught. These helpers serve the code that logs a failure and the platform's safety net: the 5xx handler
(``api/server_errors.py``), the unhandled 500 (``services/platform/security_headers.py``) and the filter on
``uvicorn.error`` (``logging_config.py``).

- ``visible_causes`` walks the causes of an exception as a reader of its traceback does — ``__cause__``, then
  ``__context__`` unless suppressed — and also through the ``cause`` attribute that the AI Export wrappers
  (``RequiredComponentBuildError``, ``ResourceLoadError``) carry instead of ``__cause__``.
- ``root_cause`` is the failure itself; ``shown_error`` is the exception whose rendered traceback says the most: Python
  renders an exception's own ``__cause__``/``__context__`` chain, never a ``cause`` attribute, so it is the last
  exception reached through such an attribute.
- ``mark_reported`` marks an exception the log already has: a warning or a higher line was written with it, or while it
  was being handled (``logging_config.LibreFolioBoundLogger``). The safety net reads ``is_reported`` and
  ``chain_reported`` so as not to write it twice. The mark is an attribute of the exception object: exceptions cannot be
  weakly referenced.
"""

#: No chain is walked further: a guard against a cycle the links were built into, or a runaway chain.
_LIMIT = 50
_MARK = "_librefolio_reported"


def _cause_attribute(error: BaseException) -> BaseException | None:
    """The exception an AI-Export-style wrapper carries in its ``cause`` attribute, if any."""
    cause = getattr(error, "cause", None)
    return cause if isinstance(cause, BaseException) and cause is not error else None


def _next_visible(error: BaseException) -> tuple[BaseException | None, bool]:
    """The cause a reader follows next, and whether it was reached through a ``cause`` attribute."""
    cause = _cause_attribute(error)
    if cause is not None:
        return cause, True
    if error.__cause__ is not None:
        return error.__cause__, False
    if error.__context__ is not None and not error.__suppress_context__:
        return error.__context__, False
    return None, False


def visible_causes(error: BaseException) -> list[BaseException]:
    """``error``, then each cause a reader follows: the ``cause`` attribute, ``__cause__``, an unsuppressed ``__context__``."""
    chain = [error]
    seen = {id(error)}
    current = error
    while len(chain) < _LIMIT:
        cause, _ = _next_visible(current)
        if cause is None or id(cause) in seen:
            break
        chain.append(cause)
        seen.add(id(cause))
        current = cause
    return chain


def root_cause(error: BaseException) -> BaseException:
    """The deepest visible cause of ``error``: ``error`` itself when it has none."""
    return visible_causes(error)[-1]


def shown_error(error: BaseException) -> BaseException:
    """The last exception reached through a ``cause`` attribute, else ``error``: the traceback that says the most."""
    shown = error
    current = error
    seen = {id(error)}
    for _ in range(_LIMIT - 1):
        cause, through_attribute = _next_visible(current)
        if cause is None or id(cause) in seen:
            break
        if through_attribute:
            shown = cause
        seen.add(id(cause))
        current = cause
    return shown


def reason_code_of(error: BaseException) -> str | None:
    """The first non-empty ``reason_code`` attribute along the visible causes of ``error``, if any."""
    for item in visible_causes(error):
        code = getattr(item, "reason_code", None)
        if isinstance(code, str) and code:
            return code
    return None


def linked_errors(error: BaseException) -> list[BaseException]:
    """``error`` and every exception linked to it, by a ``cause`` attribute, ``__cause__`` or ``__context__``, suppressed
    contexts included: what was in flight when the failure was answered, whether a traceback shows it or not."""
    found: list[BaseException] = []
    seen: set[int] = set()
    pending = [error]
    while pending and len(found) < _LIMIT:
        item = pending.pop(0)
        if id(item) in seen:
            continue
        seen.add(id(item))
        found.append(item)
        pending.extend(link for link in (_cause_attribute(item), item.__cause__, item.__context__) if link is not None and id(link) not in seen)
    return found


def mark_reported(error: BaseException) -> None:
    """Mark ``error`` as already in the log. An object that refuses attributes stays unmarked: never an error here."""
    try:
        setattr(error, _MARK, True)
    except (AttributeError, TypeError):
        pass


def is_reported(error: BaseException) -> bool:
    """Whether ``error`` itself was marked by ``mark_reported``."""
    return getattr(error, _MARK, False) is True


def chain_reported(error: BaseException) -> bool:
    """Whether ``error`` or an exception linked to it (``linked_errors``) was marked by ``mark_reported``."""
    return any(is_reported(item) for item in linked_errors(error))
