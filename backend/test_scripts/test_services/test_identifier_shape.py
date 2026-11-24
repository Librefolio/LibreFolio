"""ENR-3 (R12): ``utils/asset/identifier_shape.py`` tells a text with the form of an ISIN or a LEI, check digits included.

The enrichers' search across sources asks an enricher without a search (ESMA) only when the text typed is an identifier
it accepts, so a typo in the last character must be refused here and cost no call:

1. **ISIN** (ISO 6166): two letters, nine letters or digits, one check digit (Luhn over the expanded digits). Real ISINs
   pass; a wrong check digit, a wrong length, a digit in the country part or a symbol fail. Spaces around and lower case
   are ignored.
2. **LEI** (ISO 17442): eighteen letters or digits and two check digits (MOD 97-10). The valid LEIs are the real ones
   and ones the test builds with its own computation of the check digits; any change to one character breaks it.
3. **IDENTIFIER_SHAPES** names exactly the two types and their checks.

Pure: no database, no server, no network.
"""

from __future__ import annotations

import pytest

from backend.app.utils.asset.identifier_shape import IDENTIFIER_SHAPES, isin_shaped, lei_shaped

REAL_ISINS = ["US0378331005", "IE00B4L5Y983", "DE000BAY0017", "GB0002634946", "IT0003128367", "XS0000000009"]
REAL_LEIS = ["HWUPKR0MPOU8FGXBT394", "5493001KJTIIGC8Y1R12"]


def _digits(text: str) -> str:
    return "".join(str(int(char, 36)) for char in text)


def _lei_with_check_digits(base: str) -> str:
    """An 18-character base completed with its two MOD 97-10 check digits, computed here, not by the product."""
    return f"{base}{98 - int(_digits(base + '00')) % 97:02d}"


def _flip_last_digit(text: str) -> str:
    return text[:-1] + str((int(text[-1]) + 1) % 10)


@pytest.mark.parametrize("isin", REAL_ISINS)
def test_a_real_isin_passes(isin):
    assert isin_shaped(isin) is True


@pytest.mark.parametrize("isin", REAL_ISINS)
def test_an_isin_with_a_wrong_check_digit_fails(isin):
    assert isin_shaped(isin) is True, "barrier: the unbroken one passes"
    assert isin_shaped(_flip_last_digit(isin)) is False


@pytest.mark.parametrize("isin", REAL_ISINS)
def test_an_isin_in_lower_case_or_with_spaces_passes(isin):
    assert isin_shaped(isin.lower()) is True
    assert isin_shaped(f"  {isin}  ") is True
    assert isin_shaped(f"\t{isin.lower()}\n") is True


@pytest.mark.parametrize(
    "text",
    ["", "   ", "US037833100", "US03783310055", "U0378331005", "1S0378331005", "US-378331005", "US0378331 05", "US037833100A", "ÙS0378331005"],
    ids=["empty", "blank", "short", "long", "one-letter-country", "digit-in-country", "symbol", "inner-space", "letter-check-digit", "accented"],
)
def test_a_text_with_the_wrong_length_or_charset_is_not_an_isin(text):
    assert isin_shaped(text) is False


@pytest.mark.parametrize("lei", REAL_LEIS)
def test_a_real_lei_passes(lei):
    assert lei_shaped(lei) is True


@pytest.mark.parametrize("base", ["ABCDEFGHIJKLMNOPQR", "123456789012345678", "5493001KJTIIGC8Y1R", "LABRECOGLEI0000000"])
def test_a_lei_built_with_its_check_digits_passes_and_breaks_with_any_change(base):
    lei = _lei_with_check_digits(base)
    assert lei_shaped(lei) is True, "the product agrees with the independent computation"
    assert lei_shaped(lei.lower()) is True
    assert lei_shaped(f" {lei} ") is True
    assert lei_shaped(_flip_last_digit(lei)) is False, "a wrong check digit"
    swapped = ("B" if lei[0] != "B" else "C") + lei[1:]
    assert lei_shaped(swapped) is False, "a changed character in the body"


@pytest.mark.parametrize(
    "text",
    ["", "   ", "HWUPKR0MPOU8FGXBT39", "HWUPKR0MPOU8FGXBT3944", "HWUPKR0MPOU8FGXBT39A", "HWUPKR0MPOU8FGXB-394", "HWUPKR0MPOU8 FGXBT394"],
    ids=["empty", "blank", "short", "long", "letter-check-digit", "symbol", "inner-space"],
)
def test_a_text_with_the_wrong_length_or_charset_is_not_a_lei(text):
    assert lei_shaped(text) is False


def test_a_lei_is_not_an_isin_and_an_isin_is_not_a_lei():
    assert isin_shaped(REAL_LEIS[0]) is False
    assert all(lei_shaped(isin) is False for isin in REAL_ISINS)


def test_the_shapes_table_names_the_two_types_and_their_checks():
    assert set(IDENTIFIER_SHAPES) == {"ISIN", "LEI"}
    assert IDENTIFIER_SHAPES["ISIN"] is isin_shaped
    assert IDENTIFIER_SHAPES["LEI"] is lei_shaped
