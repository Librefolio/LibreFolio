"""Whether a text has the shape of a strong identifier: an ISIN or a LEI, check digits included.

The enrichers' search across sources (ENR-3, R12) asks an enricher that has no search of its own only when the text
typed is an identifier it accepts: ESMA answers an ISIN, never a name. A text that only looks like one (a typo in the
last character) asks nothing, so it costs no call to the source.

- **ISIN** (ISO 6166): two letters, nine letters or digits, one check digit (Luhn over the digits the letters expand
  to, A=10 … Z=35).
- **LEI** (ISO 17442): eighteen letters or digits, two check digits (ISO 7064 MOD 97-10: the number the letters expand
  to, modulo 97, is 1).

Leaf functions: no service, no I/O.
"""

from __future__ import annotations

import re

_ISIN = re.compile(r"[A-Z]{2}[A-Z0-9]{9}[0-9]")
_LEI = re.compile(r"[A-Z0-9]{18}[0-9]{2}")


def _expand(text: str) -> str:
    """The digits a text expands to: a digit stays, a letter becomes its number (A=10 … Z=35)."""
    return "".join(str(int(char, 36)) for char in text)


def isin_shaped(text: str) -> bool:
    """``text`` (spaces around ignored, any case) is an ISIN whose check digit is right."""
    value = text.strip().upper()
    if not _ISIN.fullmatch(value):
        return False
    digits = _expand(value)
    total = 0
    for position, char in enumerate(reversed(digits)):
        digit = int(char)
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def lei_shaped(text: str) -> bool:
    """``text`` (spaces around ignored, any case) is a LEI whose check digits are right."""
    value = text.strip().upper()
    return bool(_LEI.fullmatch(value)) and int(_expand(value)) % 97 == 1


#: The identifier types whose shape can be checked, and the check.
IDENTIFIER_SHAPES = {"ISIN": isin_shaped, "LEI": lei_shaped}
