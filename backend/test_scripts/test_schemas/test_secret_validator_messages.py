"""A-38: a validator of a secret field never puts the value in its message (release 1.3, workstream A).

The handler of the ``422`` (``api/validation_errors.py``) drops ``input`` from every validation error but keeps ``msg``
and ``ctx`` as Pydantic wrote them. A validator that formats the value into its message — ``raise ValueError(f"… {v}")`` —
would send part of a password or a token back. The rule (``security.md#validation-errors``): the validator of a secret
field says what is wrong, never with what. The lane test ``test_validation_errors_api.py`` looks for the secret in the
answer of the routes that exist today; this test imposes the rule on the code, so a validator added tomorrow to such a
field cannot break it.

A secret field is one whose name holds ``password``, ``token``, ``secret``, ``key`` or ``credential``. Pure: it reads
the source of ``backend/app/schemas`` with ``ast`` and runs nothing. The positive control feeds the scanner a validator
that breaks the rule, and one that keeps it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

SCHEMAS = Path(__file__).resolve().parents[2] / "app" / "schemas"
SECRET_NAME = re.compile(r"password|token|secret|key|credential", re.IGNORECASE)


def _validated_fields(function: ast.FunctionDef) -> list[str]:
    """The field names a ``@field_validator("a", "b", ...)`` decorator lists."""
    names: list[str] = []
    for decorator in function.decorator_list:
        if isinstance(decorator, ast.Call) and getattr(decorator.func, "id", getattr(decorator.func, "attr", "")) in {"field_validator", "validator"}:
            names.extend(arg.value for arg in decorator.args if isinstance(arg, ast.Constant) and isinstance(arg.value, str))
    return names


def _message_formats(function: ast.FunctionDef, value_names: set[str]) -> bool:
    """Whether a ``raise ...(<message>)`` of the function puts one of ``value_names`` into its message (an f-string, ``%`` or ``.format``)."""
    for node in ast.walk(function):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        for argument in node.exc.args:
            for part in ast.walk(argument):
                if isinstance(part, ast.Name) and part.id in value_names and isinstance(argument, (ast.JoinedStr, ast.BinOp, ast.Call)):
                    return True
    return False


def violations(source: str, label: str) -> list[str]:
    """The ``field_validator`` functions of ``source`` that validate a secret field and format its value into a message."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef):
            continue
        secret_fields = [name for name in _validated_fields(node) if SECRET_NAME.search(name)]
        if not secret_fields:
            continue
        parameters = {argument.arg for argument in node.args.args if argument.arg not in {"cls", "self"}}
        if _message_formats(node, parameters):
            found.append(f"{label}:{node.lineno} {node.name} ({', '.join(secret_fields)})")
    return found


def test_the_scanner_sees_a_validator_that_formats_a_secret_and_lets_one_that_does_not() -> None:
    """SVM-001 — positive control: the scanner reports a password validator that formats the value, and none that keeps the message plain or validates a public field."""
    bad = 'class M:\n    @field_validator("password")\n    @classmethod\n    def check(cls, value):\n        raise ValueError(f"bad password {value}")\n'
    plain = 'class M:\n    @field_validator("password")\n    @classmethod\n    def check(cls, value):\n        raise ValueError("password is too weak")\n'
    public = 'class M:\n    @field_validator("currency")\n    @classmethod\n    def check(cls, value):\n        raise ValueError(f"Invalid currency {value}")\n'

    assert len(violations(bad, "bad")) == 1, "the scanner must see a formatted secret"
    assert violations(plain, "plain") == [] and violations(public, "public") == [], "a plain message and a public field are fine"


def test_no_validator_of_a_secret_field_puts_the_value_in_its_message() -> None:
    """SVM-002 — A-38: no ``field_validator`` of a field named like a secret in ``backend/app/schemas`` formats the value into the message of what it raises."""
    found: list[str] = []
    for path in sorted(SCHEMAS.rglob("*.py")):
        found.extend(violations(path.read_text(encoding="utf-8"), str(path.relative_to(SCHEMAS))))

    assert found == [], "a validator of a secret field must not put the value in its message (the 422 keeps msg and ctx):\n" + "\n".join(found)
