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
  was being handled (``logging_config.LibreFolioBoundLogger``). The mark is per request (H-60r): one object can reach
  several requests (the portfolio engine and the risk engines hand the failure of one build to every request waiting
  on it), so the mark keeps, in order, the ``request_id`` of each request whose log has a line about the exception
  (``None`` for a line outside any request), and whether such a line carried its traceback. The safety net reads
  ``chain_reported_for`` and ``is_reported_for`` so as not to write a failure twice in a request, and ``chain_reported``
  and ``is_reported`` to write only a short line, pointing to the first one, in a request the failure reached after
  another. ``mark_traceback_reported`` marks the exceptions a traceback shows. The mark is an attribute of the
  exception object: exceptions cannot be weakly referenced.
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


def _entries(error: BaseException) -> tuple[tuple[str | None, bool], ...]:
    """The mark of ``error``: one ``(request_id, traceback)`` per request whose log has a line about it, in order."""
    entries = getattr(error, _MARK, ())
    return entries if isinstance(entries, tuple) else ()


def mark_reported(error: BaseException, request_id: str | None = None, *, traceback: bool = False) -> None:
    """Mark ``error`` as in the log of request ``request_id`` (None: a line outside any request), with its traceback
    when ``traceback``. A request already in the mark is not added again; ``traceback`` upgrades its entry. An object
    that refuses attributes stays unmarked: never an error here."""
    entries = _entries(error)
    for index, (marked_request, marked_traceback) in enumerate(entries):
        if marked_request == request_id:
            if not traceback or marked_traceback:
                return
            entries = (*entries[:index], (request_id, True), *entries[index + 1 :])
            break
    else:
        entries = (*entries, (request_id, traceback))
    try:
        setattr(error, _MARK, entries)
    except (AttributeError, TypeError):
        pass


def _rendered_errors(error: BaseException) -> list[BaseException]:
    """``error`` and the exceptions its traceback shows, as Python renders it: ``__cause__`` when set, else an
    unsuppressed ``__context__``, step by step; never a ``cause`` attribute."""
    chain = [error]
    seen = {id(error)}
    current = error
    while len(chain) < _LIMIT:
        follows = current.__cause__ if current.__cause__ is not None else (None if current.__suppress_context__ else current.__context__)
        if follows is None or id(follows) in seen:
            break
        chain.append(follows)
        seen.add(id(follows))
        current = follows
    return chain


def mark_traceback_reported(error: BaseException, request_id: str | None = None) -> None:
    """Mark ``error`` and every exception its traceback shows as in the log of ``request_id``, traceback included."""
    for item in _rendered_errors(error):
        mark_reported(item, request_id, traceback=True)


def is_reported(error: BaseException) -> bool:
    """Whether the log has a line about ``error`` itself, in any request or outside one."""
    return bool(_entries(error))


def is_reported_for(error: BaseException, request_id: str | None) -> bool:
    """Whether the log of request ``request_id`` (None: outside any request) has a line about ``error`` itself."""
    return any(marked_request == request_id for marked_request, _ in _entries(error))


def chain_reported(error: BaseException) -> bool:
    """Whether ``error`` or an exception linked to it (``linked_errors``) is in the log, in any request."""
    return any(is_reported(item) for item in linked_errors(error))


def chain_reported_for(error: BaseException, request_id: str | None) -> bool:
    """Whether ``error`` or an exception linked to it (``linked_errors``) is in the log of request ``request_id``."""
    return any(is_reported_for(item, request_id) for item in linked_errors(error))


def traceback_reported(error: BaseException) -> bool:
    """Whether a line carried the traceback of ``error`` itself."""
    return any(marked_traceback for _, marked_traceback in _entries(error))


def first_reporting_request(error: BaseException) -> str | None:
    """The request of the first line about ``error`` or a linked exception: the first entry of the first marked one
    along ``linked_errors``; None when nothing is marked or that line was written outside any request."""
    for item in linked_errors(error):
        entries = _entries(item)
        if entries:
            return entries[0][0]
    return None


def traceback_reporting_request(error: BaseException) -> str | None:
    """The request of the first line that carried the traceback of ``error``; None when no line did or it was written
    outside any request."""
    for marked_request, marked_traceback in _entries(error):
        if marked_traceback:
            return marked_request
    return None
