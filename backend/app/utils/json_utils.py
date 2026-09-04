"""
JSON-safety helpers for LibreFolio.

Two deliberately different semantics live side by side:

- :func:`ensure_json_safe` — **validator**: recursively checks a value is natively
  JSON-serializable and raises ``ValueError`` otherwise. Used by Pydantic
  ``field_validator``s on contract boundaries (signals, AI Export payloads) where
  a non-JSON value means the producer is broken and must be rejected.
- ``_json_safe_details`` in ``backend.app.services.asset_source`` — **sanitizer**:
  stringifies anything non-primitive and never raises. Kept local to that module
  because it exists for one field (``AssetSourceError.details``), preserves
  ``None``/empty as "omit the field", and only sanitizes one list level deep —
  exactly what the localized provider-error resolver needs, no more.

Do not "merge" them: rejecting vs stringifying are opposite error policies
(audit 08, report 03 §N-03-A).
"""

import math
from typing import Any


def ensure_json_safe(value: Any, path: str = "value") -> Any:
    """Validate that ``value`` is natively JSON-serializable, recursively.

    Accepts ``None``, ``str``, ``bool``, ``int``, finite ``float``, and lists /
    dicts (string keys only) thereof. Raises ``ValueError`` with the offending
    ``path`` on anything else (Decimal, date, non-finite float, non-string key).

    Returns the value unchanged so Pydantic validators can ``return`` it directly.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, list):
        for index, item in enumerate(value):
            ensure_json_safe(item, f"{path}[{index}]")
        return value
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string key")
            ensure_json_safe(item, f"{path}.{key}")
        return value
    raise ValueError(f"{path} contains a non-JSON value of type {type(value).__name__}")
