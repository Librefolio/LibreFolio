"""
What of a pydantic validation error an issue may carry: the field it names and its plain parameters.

One home for the rule (W-B77). The transaction batch's lenient parse (``transaction_batch_stages._parse_lenient``) and
the BRIM parse (``BRIMProvider._create_transaction``) turn the same refusal into the same issue, so a row the parse
refuses and the same row the batch refuses carry the same ``field`` and the same ``params``.
"""

from __future__ import annotations

from typing import Optional

# What an error's context may hold to become its params: a business rule's ``{type, qty, …}``, a field constraint's
# ``{max_length}``, ``{gt}``, ``{ge}`` (W-B70). pydantic's ``value_error`` holds the exception itself, which no response
# can carry: copied as it was, it made the BRIM parse answer 400 «Unable to serialize» (W-B75).
PLAIN_PARAM_TYPES = (str, int, float, bool, type(None))


def loc_to_field(loc: tuple | list) -> Optional[str]:
    """A pydantic location as a dotted field path, its list indices skipped; ``None`` for a location naming no field.

    A promotion's merged value is named by its own field — ``resolved_fields.date`` is ``date`` (H-41) — so the issue
    carries that field's label.
    """
    parts = [str(part) for part in loc if not isinstance(part, int)]
    if len(parts) > 1 and parts[0] == "resolved_fields":
        parts = parts[1:]
    return ".".join(parts) if parts else None


def error_params(error: dict) -> Optional[dict]:
    """The ``params`` of an error: a copy of its context when every value is plain data, ``None`` otherwise.

    The same for a model's business rule (``{type}``, ``{type, qty}``), a field's constraint (``string_too_long``'s
    ``{max_length}``, ``greater_than``'s ``{gt}``: W-B70, so the message can name the limit) and each sub-error of a
    packed ``multipleBusinessRuleErrors``. A ``value_error`` keeps ``None``: its context holds the exception.
    """
    context = error.get("ctx")
    if not context or not all(isinstance(value, PLAIN_PARAM_TYPES) for value in context.values()):
        return None
    return dict(context)
