"""The catalogue of the asset profile (plan 68, §3.6): every voice, and the stored form of its values.

A voice is the closed description of one fact (``FAProfileVoice`` in ``schemas/assets/profile.py``). A new voice is one
entry here, with its labels in the frontend: the database stores ``key`` as plain text, with no list to migrate.

``normalize_value(key, value)`` is the one gate a value passes before it is stored: it checks the shape and the sign of
the voice and returns the **stored form** — JSON-ready (strings, dicts, lists), deterministic and idempotent. The store
compares two values by their stored forms («different from now», plan §3.7), so two readings of the same fact give the
same form whatever their spelling: ``"1.780"`` and ``"1.78"``, a map with its keys in another order or another
rounding. ``None`` stays ``None``: a value left empty on purpose.

The codes of a choice voice stay in the stored rows for ever: a code is added freely, never renamed. Each enricher
translates its source's text into them, and a text it cannot translate leaves the voice empty (plan §3.6).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any

import pycountry
from pydantic import ValidationError

from backend.app.schemas.assets.metadata import FAGeographicArea, FASectorArea
from backend.app.schemas.assets.profile import FAProfileVoice, ProfileGroup, ProfileMapKeys, ProfilePeriod, ProfileShape, ProfileSign, ProfileTopic
from backend.app.schemas.common import check_decimal_exponent, iso_currency_code
from backend.app.utils.asset.geo import normalize_country_to_iso3
from backend.app.utils.asset.sector import normalize_sector

#: The value as stored in ``asset_profile_updates.value``: a string, a dict or a list of dicts, or None.
StoredValue = str | dict[str, Any] | list[dict[str, Any]] | None


class ProfileValueError(ValueError):
    """A voice the catalogue does not list, or a value that does not fit its voice. ``key`` names the voice."""

    def __init__(self, key: str, reason: str):
        super().__init__(f"{key}: {reason}")
        self.key = key
        self.reason = reason


# =============================================================================
# THE VOICES
# =============================================================================

_CLASSIFICATION = (ProfileGroup.CLASSIFICATION,)
_KEY_FIGURES = (ProfileGroup.KEY_FIGURES,)
_FUND = (ProfileGroup.FUND,)
_COMPANY = (ProfileGroup.COMPANY,)
_BOND = (ProfileGroup.BOND,)
_CRYPTO = (ProfileGroup.CRYPTO,)
_IDENTITY = (ProfileGroup.IDENTITY,)

_NON_NEGATIVE = ProfileSign.NON_NEGATIVE
#: Each voice says what it is about (E7b): the enrichers' window names what an enricher fills by these.
_T = ProfileTopic


def _voice(key: str, shape: ProfileShape, **fields: Any) -> FAProfileVoice:
    return FAProfileVoice(key=key, shape=shape, **fields)


_VOICES: tuple[FAProfileVoice, ...] = (
    # Classification: what the old classification_params held (migration 006 copies it, A4, then drops the column, D7b)
    _voice("geography", ProfileShape.MAP, topic=_T.COUNTRIES, map_keys=ProfileMapKeys.COUNTRY, groups=_CLASSIFICATION),
    _voice("sector", ProfileShape.MAP, topic=_T.SECTORS, map_keys=ProfileMapKeys.SECTOR, groups=(ProfileGroup.CLASSIFICATION, ProfileGroup.COMPANY)),
    _voice("description", ProfileShape.TEXT, topic=_T.DESCRIPTION),
    # Key figures: one card each, a chart of its history unless said otherwise
    _voice("withholding_tax", ProfileShape.PERCENTAGE, topic=_T.COSTS, sign=_NON_NEGATIVE, groups=_KEY_FIGURES, key_figure=True),
    _voice("ter", ProfileShape.PERCENTAGE, topic=_T.COSTS, sign=_NON_NEGATIVE, groups=_KEY_FIGURES, key_figure=True, charted=True),
    _voice("fund_size", ProfileShape.AMOUNT, topic=_T.SIZE, sign=_NON_NEGATIVE, groups=_KEY_FIGURES, key_figure=True, charted=True, volatile=True),
    _voice("market_cap", ProfileShape.AMOUNT, topic=_T.SIZE, sign=_NON_NEGATIVE, groups=_KEY_FIGURES, key_figure=True, charted=True, volatile=True),
    _voice("yield_gross", ProfileShape.PERCENTAGE, topic=_T.YIELD, sign=ProfileSign.ANY, groups=_KEY_FIGURES, key_figure=True, charted=True, volatile=True),
    _voice("modified_duration", ProfileShape.NUMBER, topic=_T.DURATION, sign=_NON_NEGATIVE, unit="years", groups=_KEY_FIGURES, key_figure=True, charted=True, volatile=True),
    _voice("coupon_rate", ProfileShape.PERCENTAGE, topic=_T.COUPONS, sign=_NON_NEGATIVE, groups=_KEY_FIGURES, key_figure=True, charted=True),
    _voice("maturity_date", ProfileShape.DATE, topic=_T.MATURITY, groups=_KEY_FIGURES, key_figure=True),
    # The fund
    _voice("fund_provider", ProfileShape.TEXT, topic=_T.MANAGER, groups=_FUND),
    _voice("index_name", ProfileShape.TEXT, topic=_T.STRUCTURE, groups=_FUND),
    _voice(
        "replication",
        ProfileShape.CHOICE,
        topic=_T.STRUCTURE,
        groups=_FUND,
        choices=("physical_full", "physical_sampling", "physical_backed", "synthetic_unfunded_swap", "synthetic_funded_swap"),
    ),
    _voice("distribution_policy", ProfileShape.CHOICE, topic=_T.STRUCTURE, groups=_FUND, choices=("accumulating", "distributing")),
    _voice("fund_domicile", ProfileShape.COUNTRY, topic=_T.STRUCTURE, groups=_FUND),
    _voice("fund_currency", ProfileShape.CURRENCY, topic=_T.STRUCTURE, groups=_FUND),
    _voice("inception_date", ProfileShape.DATE, topic=_T.STRUCTURE, groups=(ProfileGroup.FUND, ProfileGroup.CRYPTO)),
    # The fund's management fee (C2e, the developer's «voce sua»): only a part of the TER, so a detail of the fund and
    # never a key figure; a source that gives it never writes it as «ter»
    _voice("management_fee", ProfileShape.PERCENTAGE, topic=_T.COSTS, sign=_NON_NEGATIVE, groups=_FUND),
    # The company (its sector is the «sector» map above, one sector at 100 %)
    _voice("industry", ProfileShape.TEXT, topic=_T.SECTORS, groups=_COMPANY),
    _voice("issuer_country", ProfileShape.COUNTRY, topic=_T.ISSUER, groups=_COMPANY),
    # The company's own site, and its two headline figures of the last fiscal year (BI-PROF): each figure is dated by
    # the end of its fiscal year (``source_date``), which the tab shows beside it
    _voice("website", ProfileShape.TEXT, topic=_T.ISSUER, groups=(ProfileGroup.COMPANY, ProfileGroup.CRYPTO)),
    _voice("revenue", ProfileShape.AMOUNT, topic=_T.FINANCIALS, sign=_NON_NEGATIVE, groups=_COMPANY, period=ProfilePeriod.FISCAL_YEAR),
    _voice("net_income", ProfileShape.AMOUNT, topic=_T.FINANCIALS, sign=ProfileSign.ANY, groups=_COMPANY, period=ProfilePeriod.FISCAL_YEAR),
    # The coin (82 CG-D, D-27): the categories of its source, in the source's words, one text. A coin's site is the
    # «website» above, its launch day the «inception_date»: their first group is where the profile editor puts them
    _voice("crypto_categories", ProfileShape.TEXT, topic=_T.CATEGORIES, groups=_CRYPTO),
    # The bond
    _voice("coupon_period_rate", ProfileShape.PERCENTAGE, topic=_T.COUPONS, sign=_NON_NEGATIVE, groups=_BOND),
    _voice("coupon_frequency", ProfileShape.CHOICE, topic=_T.COUPONS, groups=_BOND, choices=("monthly", "quarterly", "semiannual", "annual", "at_maturity")),
    _voice("coupon_type", ProfileShape.CHOICE, topic=_T.COUPONS, groups=_BOND, choices=("fixed", "floating", "step_up", "structured", "zero_coupon", "inflation_linked")),
    _voice("day_count", ProfileShape.CHOICE, topic=_T.COUPONS, groups=_BOND, choices=("act_act_icma", "act_act_isda", "act_360", "act_365", "30_360")),
    _voice("yield_net", ProfileShape.PERCENTAGE, topic=_T.YIELD, sign=ProfileSign.ANY, groups=_BOND, volatile=True),
    _voice("accrued_interest", ProfileShape.NUMBER, topic=_T.COUPONS, sign=ProfileSign.ANY, unit="per_100_nominal", groups=_BOND, volatile=True),
    _voice("issuer_name", ProfileShape.TEXT, topic=_T.ISSUER, groups=_BOND),
    _voice("min_lot", ProfileShape.NUMBER, topic=_T.STRUCTURE, sign=ProfileSign.POSITIVE, groups=_BOND),
    _voice("interest_start_date", ProfileShape.DATE, topic=_T.COUPONS, groups=_BOND),
    _voice("loyalty_bonus", ProfileShape.PERCENTAGE, topic=_T.COUPONS, sign=_NON_NEGATIVE, groups=_BOND),
    _voice("coupon_schedule", ProfileShape.TABLE, topic=_T.COUPONS, sign=_NON_NEGATIVE, groups=_BOND),
    _voice("payout_description", ProfileShape.TEXT, topic=_T.COUPONS, groups=_BOND),
    # Identity: what the instrument is and who issues it, neutral to any country's tax rules
    _voice(
        "legal_form",
        ProfileShape.CHOICE,
        topic=_T.LEGAL_FORM,
        groups=_IDENTITY,
        choices=("share", "bond", "ucits_fund", "non_ucits_fund", "etc_etn", "certificate", "derivative", "crypto", "other"),
    ),
    _voice("issuer_type", ProfileShape.CHOICE, topic=_T.ISSUER, groups=_IDENTITY, choices=("sovereign", "supranational", "corporate", "vehicle")),
    # No cell of their own: the cascade of identifiers, and the voices lane 62 asked for
    _voice("issuer_lei", ProfileShape.TEXT, topic=_T.ISSUER),
    _voice("outstanding_amount", ProfileShape.AMOUNT, topic=_T.SIZE, sign=_NON_NEGATIVE),
    _voice("reference_price_date", ProfileShape.DATE, topic=_T.YIELD),
)

#: Every voice of the profile, by key, in the order of plan §3.6.
CATALOGUE: Mapping[str, FAProfileVoice] = MappingProxyType({voice.key: voice for voice in _VOICES})


def get_voice(key: str) -> FAProfileVoice:
    """The voice of ``key``; ``ProfileValueError`` when the catalogue does not list it."""
    voice = CATALOGUE.get(key)
    if voice is None:
        raise ProfileValueError(key, "not a voice of the profile catalogue")
    return voice


# =============================================================================
# THE STORED FORM, ONE RULE PER SHAPE
# =============================================================================

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_TABLE_ROW_KEYS = frozenset({"from", "to", "rate"})
_AMOUNT_KEYS = frozenset({"amount", "currency"})


def _decimal(key: str, value: Any, sign: ProfileSign | None) -> Decimal:
    # A float carries a binary approximation (0.1 is 0.1000000000000000055…): refused, a decimal comes as text.
    # bool is an int: refused too, True is not a number.
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ProfileValueError(key, f"a number is a decimal string, an int or a Decimal, not {type(value).__name__}")
    try:
        number = Decimal(value.strip()) if isinstance(value, str) else Decimal(value)
    except InvalidOperation as exc:
        raise ProfileValueError(key, "not a decimal number") from exc
    if not number.is_finite():
        raise ProfileValueError(key, "not a finite number")
    try:
        check_decimal_exponent(number)
    except ValueError as exc:
        raise ProfileValueError(key, str(exc)) from exc
    if sign is ProfileSign.NON_NEGATIVE and number < 0:
        raise ProfileValueError(key, "must not be negative")
    if sign is ProfileSign.POSITIVE and number <= 0:
        raise ProfileValueError(key, "must be greater than zero")
    return number


def _fixed(number: Decimal) -> str:
    """Plain fixed-point text with no trailing zeros: ``1.780`` → ``"1.78"``, ``1E+2`` → ``"100"``, ``-0`` → ``"0"``."""
    if number.is_zero():
        return "0"
    return format(number.normalize(), "f")


def _number(voice: FAProfileVoice, value: Any) -> str:
    return _fixed(_decimal(voice.key, value, voice.sign))


def _amount(voice: FAProfileVoice, value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != _AMOUNT_KEYS:
        raise ProfileValueError(voice.key, "an amount is an object with exactly «amount» and «currency»")
    return {"amount": _number(voice, value["amount"]), "currency": _currency(voice, value["currency"])}


def _iso_date(key: str, value: Any) -> str:
    # datetime is a date subclass: refused, a profile date has no time
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        raise ProfileValueError(key, "a date is written YYYY-MM-DD")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ProfileValueError(key, "not a calendar date") from exc


def _date(voice: FAProfileVoice, value: Any) -> str:
    return _iso_date(voice.key, value)


def _text(voice: FAProfileVoice, value: Any) -> str:
    if not isinstance(value, str):
        raise ProfileValueError(voice.key, f"a text is a string, not {type(value).__name__}")
    text = value.strip()
    if not text:
        raise ProfileValueError(voice.key, "an empty text is written as null («Lascia vuoto»)")
    return text


def _choice(voice: FAProfileVoice, value: Any) -> str:
    if not isinstance(value, str) or value not in voice.choices:
        raise ProfileValueError(voice.key, f"one of {', '.join(voice.choices)}")
    return value


def _country(voice: FAProfileVoice, value: Any) -> str:
    # A country voice holds an ISO 3166 alpha-3 code only: translating a name or an alpha-2 code is the enricher's work
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z]{3}", value.strip()):
        raise ProfileValueError(voice.key, "a country is an ISO 3166 alpha-3 code")
    code = value.strip().upper()
    if pycountry.countries.get(alpha_3=code) is None:
        raise ProfileValueError(voice.key, "not an ISO 3166 alpha-3 code")
    return code


def _currency(voice: FAProfileVoice, value: Any) -> str:
    try:
        return iso_currency_code(value)
    except ValueError as exc:
        raise ProfileValueError(voice.key, str(exc)) from exc


_DISTRIBUTIONS = {ProfileMapKeys.COUNTRY: FAGeographicArea, ProfileMapKeys.SECTOR: FASectorArea}
_CANONICAL_KEY = {ProfileMapKeys.COUNTRY: normalize_country_to_iso3, ProfileMapKeys.SECTOR: normalize_sector}


def _canonical_order(map_keys: ProfileMapKeys, name: str) -> tuple[str, str]:
    """Sort key of a map entry: its canonical key («Germany» and «de» sort as «DEU»), then its spelling. A key the
    normalizer refuses sorts by its spelling: the distribution model refuses it right after, with today's message."""
    try:
        return (_CANONICAL_KEY[map_keys](name), name)
    except ValueError:
        return (name, name)


def _map(voice: FAProfileVoice, value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise ProfileValueError(voice.key, "a map is a non-empty object of key → weight")
    # Entries sorted by canonical key before the weights are renormalized: the rounding remainder goes to the smallest
    # weight, and between equal weights to the first one met, so neither the input's order nor a key's spelling may
    # choose it
    ordered = sorted(value.items(), key=lambda item: _canonical_order(voice.map_keys, str(item[0])))
    weights = {str(name): _decimal(voice.key, weight, ProfileSign.NON_NEGATIVE) for name, weight in ordered}
    try:
        distribution = _DISTRIBUTIONS[voice.map_keys](distribution=weights).distribution
    except ValidationError as exc:
        raise ProfileValueError(voice.key, "; ".join(error["msg"] for error in exc.errors())) from exc
    return {name: format(weight, "f") for name, weight in sorted(distribution.items())}


def _table(voice: FAProfileVoice, value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ProfileValueError(voice.key, "a table is a non-empty list of rows")
    rows = []
    for row in value:
        if not isinstance(row, Mapping) or set(row) != _TABLE_ROW_KEYS:
            raise ProfileValueError(voice.key, "a row has exactly «from», «to» and «rate»")
        start, end = _iso_date(voice.key, row["from"]), _iso_date(voice.key, row["to"])
        if end < start:
            raise ProfileValueError(voice.key, f"a row ends ({end}) before it starts ({start})")
        rows.append({"from": start, "to": end, "rate": _fixed(_decimal(voice.key, row["rate"], voice.sign))})
    rows.sort(key=lambda row: row["from"])
    for previous, current in zip(rows, rows[1:], strict=False):
        if current["from"] <= previous["to"]:
            raise ProfileValueError(voice.key, f"the row from {current['from']} overlaps the one ending {previous['to']}")
    return rows


_NORMALIZERS: dict[ProfileShape, Callable[[FAProfileVoice, Any], StoredValue]] = {
    ProfileShape.NUMBER: _number,
    ProfileShape.PERCENTAGE: _number,
    ProfileShape.AMOUNT: _amount,
    ProfileShape.DATE: _date,
    ProfileShape.TEXT: _text,
    ProfileShape.CHOICE: _choice,
    ProfileShape.COUNTRY: _country,
    ProfileShape.CURRENCY: _currency,
    ProfileShape.MAP: _map,
    ProfileShape.TABLE: _table,
}


def normalize_value(key: str, value: Any) -> StoredValue:
    """The stored form of ``value`` for the voice ``key``; ``ProfileValueError`` when it does not fit."""
    voice = get_voice(key)
    if value is None:
        return None
    return _NORMALIZERS[voice.shape](voice, value)
