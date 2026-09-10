"""Bounded Unicode-safe JSON at the Tool transport and process boundary."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping

from pydantic import ValidationError

from backend.app.schemas.tools import ToolError, ToolErrorCode, ToolValidationIssue
from backend.app.services.tools.base import ToolExecutionError

_SAFE_PATH_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
_SAFE_VALIDATION_CODE = re.compile(r"[A-Za-z0-9_.-]{1,64}")


def _validate_scalar(node: object) -> None:
    if isinstance(node, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in node):
            raise ValueError("Tool JSON must contain valid Unicode scalars")
    elif node is None or type(node) in (bool, int):
        return
    elif type(node) is float:
        if not math.isfinite(node):
            raise ValueError("Tool JSON numbers must be finite")
    else:
        raise ValueError("Tool values must be JSON values, not Python objects")


def validate_json_value(value: object, *, max_depth: int = 32) -> None:
    """Reject invalid scalars before encoding can replace or fail on surrogates."""
    pending = [(value, 0)]
    while pending:
        node, depth = pending.pop()
        if depth > max_depth:
            raise ValueError("Tool JSON exceeds the permitted nesting depth")
        if isinstance(node, list):
            pending.extend((child, depth + 1) for child in node)
        elif isinstance(node, dict):
            for key, child in node.items():
                if not isinstance(key, str):
                    raise ValueError("Tool JSON object keys must be strings")
                pending.append((key, depth))
                pending.append((child, depth + 1))
        else:
            _validate_scalar(node)


def encode_json(value: object, *, max_depth: int = 32, max_bytes: int | None = None, limit_code: ToolErrorCode = "input_limit_exceeded") -> bytes:
    validate_json_value(value, max_depth=max_depth)
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    output = bytearray()
    for chunk in encoder.iterencode(value):
        encoded = chunk.encode("utf-8")
        if max_bytes is not None and len(output) + len(encoded) > max_bytes:
            raise ToolExecutionError(limit_code)
        output.extend(encoded)
    return bytes(output)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object keys are not permitted")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("Nonfinite JSON numbers are not permitted")


def _finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("JSON number exceeds the finite transport range")
    return result


def parse_json(payload: bytes) -> object:
    """Parse syntax without prematurely validating heterogeneous parameter strings."""
    return json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant, parse_float=_finite_float)


def decode_json(payload: bytes, *, max_depth: int = 32) -> object:
    value = parse_json(payload)
    validate_json_value(value, max_depth=max_depth)
    return value


def validation_error(error: ValidationError, *, code: ToolErrorCode) -> ToolError:
    """Only schema error codes and safe field paths leave the validation boundary."""
    raw_issues = error.errors(include_url=False, include_context=False, include_input=False)
    issues: list[ToolValidationIssue] = []
    for issue in raw_issues[:32]:
        path: list[str | int] = []
        for token in issue["loc"][:16]:
            if type(token) is int and token >= 0:
                path.append(token)
            elif isinstance(token, str) and _SAFE_PATH_TOKEN.fullmatch(token):
                path.append(token)
            else:
                break
        issue_code = issue["type"]
        issues.append(ToolValidationIssue(code=issue_code if _SAFE_VALIDATION_CODE.fullmatch(issue_code) else "validation_error", path=path))
    return ToolError(code=code, retryable=False, issues=issues, issue_count=len(raw_issues))


def plain_json_object(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError("Expected a JSON object")
    return value
