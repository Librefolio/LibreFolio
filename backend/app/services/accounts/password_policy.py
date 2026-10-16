"""The password rules of LibreFolio, in one place (decision 37): applied to every new password, published to the app.

The five rules of release 1.3 — a minimum length and one character of each class — are checked here for registration,
password changes, reset links and the command line. ``GET /system/instance`` publishes them, so the app draws and checks
the same list (``PasswordStrength``), and a change made here reaches the interface without a change of its own. A stored
password is never checked again: the rules apply only when a new one is chosen.

The character classes are Unicode, the same the app's regular expressions use: uppercase ``Lu``, lowercase ``Ll``, digit
``Nd``, and a symbol is any character that is not a letter, a number or whitespace. So an uppercase «É» counts, and an
Arabic-Indic digit does too. Length counts characters (code points).
"""

import unicodedata
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class PasswordRule:
    """One rule: its code, as the API and the app name it, and its value when it has one (the minimum length)."""

    code: str
    value: Optional[int] = None


MIN_LENGTH = 8

PASSWORD_RULES: tuple[PasswordRule, ...] = (
    PasswordRule("min_length", MIN_LENGTH),
    PasswordRule("uppercase"),
    PasswordRule("lowercase"),
    PasswordRule("digit"),
    PasswordRule("special"),
)


def _has_category(password: str, category: str) -> bool:
    return any(unicodedata.category(char) == category for char in password)


def _is_symbol(char: str) -> bool:
    """Neither a letter nor a number, and not whitespace."""
    return unicodedata.category(char)[0] not in ("L", "N") and not char.isspace()


_CHECKS: dict[str, Callable[[str, PasswordRule], bool]] = {
    "min_length": lambda password, rule: len(password) >= (rule.value or 0),
    "uppercase": lambda password, _rule: _has_category(password, "Lu"),
    "lowercase": lambda password, _rule: _has_category(password, "Ll"),
    "digit": lambda password, _rule: _has_category(password, "Nd"),
    "special": lambda password, _rule: any(_is_symbol(char) for char in password),
}


def failed_rules(password: str) -> list[str]:
    """The codes of the rules ``password`` does not meet, in the rules' order; empty when it meets them all."""
    return [rule.code for rule in PASSWORD_RULES if not _CHECKS[rule.code](password, rule)]


def password_rules_public() -> list[dict]:
    """The rules as ``GET /system/instance`` publishes them: ``code``, and ``value`` for the rule that has one."""
    return [{"code": rule.code, "value": rule.value} for rule in PASSWORD_RULES]
