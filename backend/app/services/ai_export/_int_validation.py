"""Integer validation shared by the AI Export spec validators.

## Why this module exists

Five modules — `temporal/policy`, `datasets/spec`, `components/spec`,
`components/types` and `analyses/spec` — each carried their own
``_require_positive_int``. They agreed on the rule and disagreed on everything
around it: the exception raised, three different message formats, four different
signatures, and whether to return the value or ``None``.

None of that variety was load bearing. These exceptions are all `ValueError`
subclasses that say "a *declaration* is internally inconsistent" — they are
raised when a plugin author writes a bad spec, they never reach the API, and no
test pins their wording. So the five are unified here, and the only thing kept
configurable is the exception class, because a caller that has a typed error for
its own subsystem should still raise it.

The subtle part, which every one of the five remembered and a sixth author might
not: ``bool`` is a subclass of ``int``. ``isinstance(True, int)`` is ``True``, so
a version field annotated ``int`` accepts ``True`` and quietly stores ``1`` — a
caller's typo turned into a real version number, attached to real data.
"""

from __future__ import annotations

__all__ = ["is_int_not_bool", "is_positive_int", "require_positive_int"]


def is_int_not_bool(value: object) -> bool:
    """True when `value` is a real ``int``.

    ``bool`` is excluded on purpose: it is a subclass of ``int``, so ``True``
    would otherwise pass every ``isinstance(value, int)`` check and be stored as
    ``1``. A version, a count or an identifier that arrives as ``True`` is a
    caller mistake, and turning it into ``1`` hides it.
    """
    return isinstance(value, int) and not isinstance(value, bool)


def is_positive_int(value: object) -> bool:
    """True when `value` is a real ``int`` of at least 1."""
    return is_int_not_bool(value) and value >= 1


def require_positive_int(
    value: object,
    field_name: str,
    *,
    owner_id: str | None = None,
    error_cls: type[Exception] | None = None,
) -> int:
    """Return `value` when it is a positive ``int``, otherwise raise.

    Args:
        value: the thing to check.
        field_name: what to call it in the message.
        owner_id: prefixed to the message when given, so a spec error names the
            plugin it came from.
        error_cls: raised for both failures when given. When omitted the wrong
            *type* raises ``TypeError`` and the wrong *value* raises
            ``ValueError`` — which is what Python means by those two, and what
            callers without a typed error of their own should get.
    """
    prefix = f"{owner_id}: " if owner_id else ""
    if not is_int_not_bool(value):
        raise (error_cls or TypeError)(f"{prefix}{field_name} must be an int, got {type(value).__name__}")
    if value < 1:
        raise (error_cls or ValueError)(f"{prefix}{field_name} must be >= 1")
    return value
