"""The asset profile (FA): the voice of its catalogue and the shapes of their values (plan 68, §3.6).

A voice is one fact of an asset's profile (its TER, its countries, the maturity of a bond…), stored as one row per change in
``asset_profile_updates`` with a JSON ``value``. The catalogue (``services/assets/profile/catalogue.py``) lists every voice
with its :class:`FAProfileVoice` and turns a raw value into its stored form; a voice it does not list is refused.

How a value is stored, one rule per shape:

========== ========================================== =======================================================
Shape      Example                                    Rule
========== ========================================== =======================================================
number     ``"1.78"``                                 a decimal as a string, never a float
percentage ``"0.0022"`` (0.22 %)                      a fraction, like the rest of the project
amount     ``{"amount": "55173000000", "currency": "EUR"}``  a decimal as a string plus the source's ISO 4217 code
date       ``"2028-10-10"``                           ISO
text       ``"…"``                                    as the source gives it, in its language
choice     ``"physical_sampling"``                    one of the voice's codes
country    ``"IRL"``                                  ISO 3166 alpha-3
currency   ``"USD"``                                  ISO 4217
map        ``{"JPN": "0.0604", "USA": "0.9396"}``     key → weight, four decimals summing to 1 (``metadata.py``)
table      ``[{"from": …, "to": …, "rate": …}]``      rows in order
========== ========================================== =======================================================

``null`` is a value left empty on purpose («Lascia vuoto»).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import ConfigDict, Field

from backend.app.schemas.common import StrictModel


class ProfileShape(StrEnum):
    """The shape of a voice's value: how it is written in ``value`` and checked."""

    NUMBER = "number"
    PERCENTAGE = "percentage"
    AMOUNT = "amount"
    DATE = "date"
    TEXT = "text"
    CHOICE = "choice"
    COUNTRY = "country"
    CURRENCY = "currency"
    MAP = "map"
    TABLE = "table"


class ProfileSign(StrEnum):
    """Which signs a numeric voice (number, percentage, amount, the rate of a table row) accepts."""

    ANY = "any"
    NON_NEGATIVE = "non_negative"
    POSITIVE = "positive"


class ProfileGroup(StrEnum):
    """Where the «Profilo» tab shows a voice. A voice with no group has a place of its own (the description) or is read
    by someone else only (the issuer's LEI, the lane 62 voices)."""

    CLASSIFICATION = "classification"
    KEY_FIGURES = "key_figures"
    FUND = "fund"
    COMPANY = "company"
    BOND = "bond"
    IDENTITY = "identity"


class ProfileMapKeys(StrEnum):
    """What the keys of a map voice are: ISO 3166 alpha-3 countries, or the standard sectors."""

    COUNTRY = "country"
    SECTOR = "sector"


class FAProfileVoice(StrictModel):
    """One voice of the catalogue: its key, the shape of its value and how the «Profilo» tab shows it."""

    model_config = ConfigDict(frozen=True)

    key: str = Field(..., description="The voice's key, stored in asset_profile_updates.key")
    shape: ProfileShape = Field(..., description="How the value is written and checked")
    sign: Optional[ProfileSign] = Field(None, description="Signs accepted by a numeric voice; None for the others")
    unit: Optional[str] = Field(None, description="What the number counts, when the shape does not say it (years, per_100_nominal)")
    groups: tuple[ProfileGroup, ...] = Field((), description="The tab groups that show it; empty for a voice with no cell of its own")
    key_figure: bool = Field(False, description="Shown as a key figure card")
    charted: bool = Field(False, description="A key figure with a chart of its history")
    volatile: bool = Field(False, description="Changes at every read (fund size, yields, duration…): «Ultime variazioni» leaves its source rows out")
    choices: tuple[str, ...] = Field((), description="The codes a choice voice accepts; empty for the others")
    map_keys: Optional[ProfileMapKeys] = Field(None, description="What a map voice's keys are; None for the others")
