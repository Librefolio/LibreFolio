"""
Asset profile catalogue (project 68, lot A1): ``backend/app/services/assets/profile/catalogue.py``.

The catalogue lists every voice of the asset profile and ``normalize_value`` turns a raw value into its stored form.
Pure: no database, no server, no network.

(a) The catalogue: exactly the 42 voices (the 37 of plan §3.6, ``management_fee`` of C2e, ``website``, ``revenue`` and
    ``net_income`` of BI-PROF, ``crypto_categories`` of 82 CG-D), in order, each with its shape, sign, unit, groups, flags, choices, map keys, topic and
    period (``fiscal_year`` for the two figures of a fiscal year, None for every other voice); the structural invariants (numeric shapes carry a sign, only choice voices carry codes, only
    map voices carry map keys, charted implies key figure, the key figure and volatile sets).
(b) ``get_voice`` returns the voice, and refuses an unknown key with ``ProfileValueError.key`` set.
(c) ``normalize_value``, one block per shape: number, percentage, amount, date, text, choice, country, currency, map,
    table — what is accepted and its stored form, what is refused.
(d) The stored form is deterministic (same fact, same form whatever its spelling) and idempotent, also after a JSON
    round trip.
(e) The labels of the windows (lot E10c2; topics, E7b): every voice, choice, group, unit and topic has its label in the four languages, in
    ``frontend/src/lib/features/assets/profile/i18n/``.

Every expectation is driven by the tables of this file, never by iterating ``CATALOGUE``: an empty or partial
catalogue must turn these tests red, not collect zero cases.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from backend.app.schemas.assets.profile import FAProfileVoice, ProfileGroup, ProfileMapKeys, ProfilePeriod, ProfileShape, ProfileSign, ProfileTopic
from backend.app.services.assets.profile.catalogue import CATALOGUE, ProfileValueError, get_voice, normalize_value

# ============================================================================
# THE EXPECTED CATALOGUE
# ============================================================================

#: The codes of every choice voice, in one place (plan §3.6, confirmed by the design consultant).
CHOICES: dict[str, tuple[str, ...]] = {
    "replication": ("physical_full", "physical_sampling", "physical_backed", "synthetic_unfunded_swap", "synthetic_funded_swap"),
    "distribution_policy": ("accumulating", "distributing"),
    "coupon_frequency": ("monthly", "quarterly", "semiannual", "annual", "at_maturity"),
    "coupon_type": ("fixed", "floating", "step_up", "structured", "zero_coupon", "inflation_linked"),
    "day_count": ("act_act_icma", "act_act_isda", "act_360", "act_365", "30_360"),
    "legal_form": ("share", "bond", "ucits_fund", "non_ucits_fund", "etc_etn", "certificate", "derivative", "crypto", "other"),
    "issuer_type": ("sovereign", "supranational", "corporate", "vehicle"),
}

#: The topic of every voice (plan 68, E7b: PROF, round 43): what an enricher's row in the enrichers' window says it
#: fills («costi, struttura, paesi, settori»), a short word for a family of voices. Declared where the voice is born.
T = ProfileTopic
TOPICS: dict[str, ProfileTopic] = {
    "geography": T.COUNTRIES,
    "sector": T.SECTORS,
    "description": T.DESCRIPTION,
    "withholding_tax": T.COSTS,
    "ter": T.COSTS,
    "fund_size": T.SIZE,
    "market_cap": T.SIZE,
    "yield_gross": T.YIELD,
    "modified_duration": T.DURATION,
    "coupon_rate": T.COUPONS,
    "maturity_date": T.MATURITY,
    "fund_provider": T.MANAGER,
    "index_name": T.STRUCTURE,
    "replication": T.STRUCTURE,
    "distribution_policy": T.STRUCTURE,
    "fund_domicile": T.STRUCTURE,
    "fund_currency": T.STRUCTURE,
    "inception_date": T.STRUCTURE,
    "management_fee": T.COSTS,
    "industry": T.SECTORS,
    "issuer_country": T.ISSUER,
    # BI-PROF: the company's site is about the issuer; its two figures of a fiscal year are its own topic
    "website": T.ISSUER,
    "revenue": T.FINANCIALS,
    "net_income": T.FINANCIALS,
    # 82 CG-D: the source's own words on a coin's kind, a topic of its own
    "crypto_categories": T.CATEGORIES,
    "coupon_period_rate": T.COUPONS,
    "coupon_frequency": T.COUPONS,
    "coupon_type": T.COUPONS,
    "day_count": T.COUPONS,
    "yield_net": T.YIELD,
    "accrued_interest": T.COUPONS,
    "issuer_name": T.ISSUER,
    "min_lot": T.STRUCTURE,
    "interest_start_date": T.COUPONS,
    "loyalty_bonus": T.COUPONS,
    "coupon_schedule": T.COUPONS,
    "payout_description": T.COUPONS,
    "legal_form": T.LEGAL_FORM,
    "issuer_type": T.ISSUER,
    "issuer_lei": T.ISSUER,
    "outstanding_amount": T.SIZE,
    "reference_price_date": T.YIELD,
}

S = ProfileShape
G = ProfileGroup
NN = ProfileSign.NON_NEGATIVE


def _v(key, shape, *, sign=None, unit=None, groups=(), key_figure=False, charted=False, volatile=False, map_keys=None, period=None):
    return FAProfileVoice(
        key=key,
        shape=shape,
        sign=sign,
        unit=unit,
        groups=groups,
        key_figure=key_figure,
        charted=charted,
        volatile=volatile,
        choices=CHOICES.get(key, ()),
        map_keys=map_keys,
        topic=TOPICS[key],
        period=period,
    )


KF = (G.KEY_FIGURES,)

#: The 42 voices (plan §3.6, C2e, BI-PROF), in the catalogue's order.
EXPECTED_VOICES: tuple[FAProfileVoice, ...] = (
    _v("geography", S.MAP, groups=(G.CLASSIFICATION,), map_keys=ProfileMapKeys.COUNTRY),
    _v("sector", S.MAP, groups=(G.CLASSIFICATION, G.COMPANY), map_keys=ProfileMapKeys.SECTOR),
    _v("description", S.TEXT),
    _v("withholding_tax", S.PERCENTAGE, sign=NN, groups=KF, key_figure=True),
    _v("ter", S.PERCENTAGE, sign=NN, groups=KF, key_figure=True, charted=True),
    _v("fund_size", S.AMOUNT, sign=NN, groups=KF, key_figure=True, charted=True, volatile=True),
    _v("market_cap", S.AMOUNT, sign=NN, groups=KF, key_figure=True, charted=True, volatile=True),
    _v("yield_gross", S.PERCENTAGE, sign=ProfileSign.ANY, groups=KF, key_figure=True, charted=True, volatile=True),
    _v("modified_duration", S.NUMBER, sign=NN, unit="years", groups=KF, key_figure=True, charted=True, volatile=True),
    _v("coupon_rate", S.PERCENTAGE, sign=NN, groups=KF, key_figure=True, charted=True),
    _v("maturity_date", S.DATE, groups=KF, key_figure=True),
    _v("fund_provider", S.TEXT, groups=(G.FUND,)),
    _v("index_name", S.TEXT, groups=(G.FUND,)),
    _v("replication", S.CHOICE, groups=(G.FUND,)),
    _v("distribution_policy", S.CHOICE, groups=(G.FUND,)),
    _v("fund_domicile", S.COUNTRY, groups=(G.FUND,)),
    _v("fund_currency", S.CURRENCY, groups=(G.FUND,)),
    _v("inception_date", S.DATE, groups=(G.FUND, G.CRYPTO)),
    # C2e (developer, «voce sua»): the fund's management fee, only a part of the TER: a detail of the fund, not a key figure
    _v("management_fee", S.PERCENTAGE, sign=NN, groups=(G.FUND,)),
    _v("industry", S.TEXT, groups=(G.COMPANY,)),
    _v("issuer_country", S.COUNTRY, groups=(G.COMPANY,)),
    # BI-PROF: the company's site and the two headline figures of its last fiscal year, each dated by that year's end
    _v("website", S.TEXT, groups=(G.COMPANY, G.CRYPTO)),
    _v("revenue", S.AMOUNT, sign=NN, groups=(G.COMPANY,), period=ProfilePeriod.FISCAL_YEAR),
    _v("net_income", S.AMOUNT, sign=ProfileSign.ANY, groups=(G.COMPANY,), period=ProfilePeriod.FISCAL_YEAR),
    _v("crypto_categories", S.TEXT, groups=(G.CRYPTO,)),
    _v("coupon_period_rate", S.PERCENTAGE, sign=NN, groups=(G.BOND,)),
    _v("coupon_frequency", S.CHOICE, groups=(G.BOND,)),
    _v("coupon_type", S.CHOICE, groups=(G.BOND,)),
    _v("day_count", S.CHOICE, groups=(G.BOND,)),
    _v("yield_net", S.PERCENTAGE, sign=ProfileSign.ANY, groups=(G.BOND,), volatile=True),
    _v("accrued_interest", S.NUMBER, sign=ProfileSign.ANY, unit="per_100_nominal", groups=(G.BOND,), volatile=True),
    _v("issuer_name", S.TEXT, groups=(G.BOND,)),
    _v("min_lot", S.NUMBER, sign=ProfileSign.POSITIVE, groups=(G.BOND,)),
    _v("interest_start_date", S.DATE, groups=(G.BOND,)),
    _v("loyalty_bonus", S.PERCENTAGE, sign=NN, groups=(G.BOND,)),
    _v("coupon_schedule", S.TABLE, sign=NN, groups=(G.BOND,)),
    _v("payout_description", S.TEXT, groups=(G.BOND,)),
    _v("legal_form", S.CHOICE, groups=(G.IDENTITY,)),
    _v("issuer_type", S.CHOICE, groups=(G.IDENTITY,)),
    _v("issuer_lei", S.TEXT),
    _v("outstanding_amount", S.AMOUNT, sign=NN),
    _v("reference_price_date", S.DATE),
)

EXPECTED_KEYS = tuple(v.key for v in EXPECTED_VOICES)
EXPECTED_BY_KEY = {v.key: v for v in EXPECTED_VOICES}

NUMERIC_SHAPES = {S.NUMBER, S.PERCENTAGE, S.AMOUNT, S.TABLE}
KEY_FIGURE_KEYS = {"withholding_tax", "ter", "fund_size", "market_cap", "yield_gross", "modified_duration", "coupon_rate", "maturity_date"}
VOLATILE_KEYS = {"fund_size", "market_cap", "yield_gross", "yield_net", "modified_duration", "accrued_interest"}
#: BI-PROF: the voices whose value is a figure of a fiscal year (the tab names the year beside it).
FISCAL_YEAR_KEYS = {"revenue", "net_income"}
#: The amount voices that may be negative (a loss); every other amount is non-negative.
SIGNED_AMOUNT_KEYS = {"net_income"}

UNKNOWN_KEY = "not_a_profile_voice"


def _refused(key: str, value) -> ProfileValueError:
    """``normalize_value(key, value)`` is refused with a ProfileValueError naming ``key``."""
    with pytest.raises(ProfileValueError) as info:
        normalize_value(key, value)
    assert info.value.key == key
    assert isinstance(info.value, ValueError)
    assert info.value.reason
    return info.value


def _keys_of_shape(shape: ProfileShape) -> list[str]:
    return [v.key for v in EXPECTED_VOICES if v.shape == shape]


# ============================================================================
# (a) THE CATALOGUE
# ============================================================================


def test_expected_table_is_self_consistent():
    """Guard on this file's own table: 42 distinct keys (37 of plan §3.6, ``management_fee`` of C2e, ``website``,
    ``revenue`` and ``net_income`` of BI-PROF), the choice dict covers exactly the choice voices."""
    assert len(EXPECTED_KEYS) == 42
    assert len(set(EXPECTED_KEYS)) == 42
    assert set(CHOICES) == set(_keys_of_shape(S.CHOICE))


def test_catalogue_keys_and_order():
    assert list(CATALOGUE) == list(EXPECTED_KEYS)


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_voice_matches_plan(key):
    voice = CATALOGUE[key]
    assert isinstance(voice, FAProfileVoice)
    assert voice.key == key
    assert voice == EXPECTED_BY_KEY[key]


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_numeric_shapes_carry_a_sign(key):
    voice = CATALOGUE[key]
    if voice.shape in NUMERIC_SHAPES:
        assert voice.sign is not None
    else:
        assert voice.sign is None


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_only_choice_voices_carry_codes(key):
    voice = CATALOGUE[key]
    if voice.shape == S.CHOICE:
        assert len(voice.choices) > 0
        assert len(set(voice.choices)) == len(voice.choices)
    else:
        assert voice.choices == ()


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_only_map_voices_carry_map_keys(key):
    voice = CATALOGUE[key]
    if voice.shape == S.MAP:
        assert voice.map_keys is not None
    else:
        assert voice.map_keys is None


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_charted_implies_key_figure(key):
    voice = CATALOGUE[key]
    if voice.charted:
        assert voice.key_figure


def test_key_figure_set():
    assert {k for k in EXPECTED_KEYS if CATALOGUE[k].key_figure} == KEY_FIGURE_KEYS
    assert {k for k, v in CATALOGUE.items() if v.key_figure} == KEY_FIGURE_KEYS


def test_volatile_set():
    assert {k for k in EXPECTED_KEYS if CATALOGUE[k].volatile} == VOLATILE_KEYS
    assert {k for k, v in CATALOGUE.items() if v.volatile} == VOLATILE_KEYS


def test_charted_set():
    expected = {"ter", "fund_size", "market_cap", "yield_gross", "modified_duration", "coupon_rate"}
    assert {k for k in EXPECTED_KEYS if CATALOGUE[k].charted} == expected


def test_fiscal_year_set():
    """BI-PROF: exactly the revenue and the net income are figures of a fiscal year; every other voice has no period."""
    assert {k for k in EXPECTED_KEYS if CATALOGUE[k].period == ProfilePeriod.FISCAL_YEAR} == FISCAL_YEAR_KEYS
    assert {k for k in EXPECTED_KEYS if CATALOGUE[k].period is not None} == FISCAL_YEAR_KEYS
    assert {k for k in EXPECTED_KEYS if CATALOGUE[k].shape == S.AMOUNT} >= FISCAL_YEAR_KEYS, "a fiscal year's figure is an amount"


def test_period_is_serialized_and_defaults_to_none():
    """The period travels with the voice as its code (the frontend reads ``period === 'fiscal_year'``), None otherwise."""
    assert CATALOGUE["revenue"].model_dump(mode="json")["period"] == "fiscal_year"
    assert CATALOGUE["net_income"].model_dump(mode="json")["period"] == "fiscal_year"
    assert CATALOGUE["market_cap"].model_dump(mode="json")["period"] is None
    assert [period.value for period in ProfilePeriod] == ["fiscal_year"]


# ============================================================================
# (b) get_voice
# ============================================================================


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_get_voice_known(key):
    assert get_voice(key) == EXPECTED_BY_KEY[key]


@pytest.mark.parametrize("key", [UNKNOWN_KEY, "", "TER", "geography "])
def test_get_voice_unknown_refused(key):
    with pytest.raises(ProfileValueError) as info:
        get_voice(key)
    assert info.value.key == key


# ============================================================================
# (c) normalize_value — unknown key, None
# ============================================================================


@pytest.mark.parametrize("value", [None, "x", "0.1", {"amount": "1", "currency": "EUR"}])
def test_unknown_key_refused(value):
    _refused(UNKNOWN_KEY, value)


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_none_stays_none(key):
    assert normalize_value(key, None) is None


# ============================================================================
# number / percentage
# ============================================================================

#: One voice per numeric scalar shape and sign used by the normalization examples (all accept zero and positives).
SCALAR_KEYS = ["modified_duration", "ter", "yield_gross", "accrued_interest"]


@pytest.mark.parametrize("key", SCALAR_KEYS)
@pytest.mark.parametrize(
    "raw, stored",
    [
        ("1.780", "1.78"),
        ("1.78", "1.78"),
        (Decimal("1.780"), "1.78"),
        (Decimal("1E+2"), "100"),
        ("1E+2", "100"),
        ("0.00", "0"),
        ("0", "0"),
        ("-0", "0"),
        (Decimal("-0.000"), "0"),
        (5, "5"),
        (0, "0"),
        ("0.0022", "0.0022"),
        ("2.5E-3", "0.0025"),
        ("100.000", "100"),
    ],
)
def test_scalar_stored_form(key, raw, stored):
    assert normalize_value(key, raw) == stored


@pytest.mark.parametrize("key", SCALAR_KEYS)
@pytest.mark.parametrize(
    "raw",
    [
        1.5,
        0.0,
        True,
        False,
        {},
        {"amount": "1"},
        [],
        ["1"],
        "NaN",
        "nan",
        Decimal("NaN"),
        "Infinity",
        "-Infinity",
        "inf",
        Decimal("Infinity"),
        Decimal("-Infinity"),
        "abc",
        "",
        "1E+999",
        "1E-999",
        Decimal("1E+999"),
    ],
    ids=lambda v: f"{type(v).__name__}:{v!r}",
)
def test_scalar_refused(key, raw):
    _refused(key, raw)


@pytest.mark.parametrize(
    "key, raw, stored",
    [
        ("ter", "0", "0"),
        ("ter", "0.0007", "0.0007"),
        ("withholding_tax", "0.15", "0.15"),
        ("coupon_rate", "0.0325", "0.0325"),
        ("min_lot", "1000", "1000"),
        ("min_lot", "0.01", "0.01"),
        ("yield_gross", "-0.0012", "-0.0012"),
        ("yield_net", "-0.0035", "-0.0035"),
        ("accrued_interest", "-0.42", "-0.42"),
        ("modified_duration", "0", "0"),
    ],
)
def test_sign_accepted(key, raw, stored):
    assert normalize_value(key, raw) == stored


@pytest.mark.parametrize(
    "key, raw",
    [
        ("ter", "-0.001"),
        ("ter", -1),
        ("withholding_tax", "-0.15"),
        ("coupon_rate", "-0.0001"),
        ("loyalty_bonus", "-0.01"),
        ("coupon_period_rate", "-0.01"),
        ("modified_duration", "-1"),
        ("min_lot", "0"),
        ("min_lot", "-0"),
        ("min_lot", 0),
        ("min_lot", "-1"),
    ],
)
def test_sign_refused(key, raw):
    _refused(key, raw)


# ============================================================================
# amount
# ============================================================================


@pytest.mark.parametrize("key", _keys_of_shape(S.AMOUNT))
@pytest.mark.parametrize(
    "raw, stored",
    [
        ({"amount": "55173000000", "currency": "EUR"}, {"amount": "55173000000", "currency": "EUR"}),
        ({"amount": "1.50", "currency": "eur"}, {"amount": "1.5", "currency": "EUR"}),
        ({"amount": Decimal("5.5E+9"), "currency": "Usd"}, {"amount": "5500000000", "currency": "USD"}),
        ({"amount": 100, "currency": "CHF"}, {"amount": "100", "currency": "CHF"}),
        ({"amount": "0", "currency": "GBP"}, {"amount": "0", "currency": "GBP"}),
    ],
)
def test_amount_stored_form(key, raw, stored):
    assert normalize_value(key, raw) == stored


@pytest.mark.parametrize("key", _keys_of_shape(S.AMOUNT))
@pytest.mark.parametrize(
    "raw",
    [
        {"amount": 1.5, "currency": "EUR"},
        {"amount": True, "currency": "EUR"},
        {"amount": "abc", "currency": "EUR"},
        {"amount": "NaN", "currency": "EUR"},
        {"amount": "1E+999", "currency": "EUR"},
        {"amount": "1", "currency": "EURO"},
        {"amount": "1", "currency": "978"},
        {"amount": "1", "currency": "XX"},
        {"amount": "1", "currency": ""},
        {"amount": "1", "currency": 978},
        {"amount": "1", "currency": "EUR", "extra": "x"},
        {"amount": "1"},
        {"currency": "EUR"},
        {},
        "1 EUR",
        "100",
        ["1", "EUR"],
    ],
    ids=lambda v: repr(v),
)
def test_amount_refused(key, raw):
    _refused(key, raw)


@pytest.mark.parametrize("key", sorted(set(_keys_of_shape(S.AMOUNT)) - SIGNED_AMOUNT_KEYS))
def test_negative_amount_refused(key):
    _refused(key, {"amount": "-1", "currency": "EUR"})


def test_signed_amount_keys_are_amounts_of_any_sign():
    """Guard on this file's own set: the amounts that may be negative are those whose sign is ANY."""
    assert {k for k in _keys_of_shape(S.AMOUNT) if EXPECTED_BY_KEY[k].sign == ProfileSign.ANY} == SIGNED_AMOUNT_KEYS


@pytest.mark.parametrize(("raw", "stored"), [({"amount": "-1", "currency": "EUR"}, {"amount": "-1", "currency": "EUR"}), ({"amount": Decimal("-2.92E+9"), "currency": "eur"}, {"amount": "-2920000000", "currency": "EUR"})])
def test_net_income_may_be_a_loss(raw, stored):
    """BI-PROF: a company's net income of a fiscal year may be negative (a loss), its revenue may not."""
    assert normalize_value("net_income", raw) == stored
    _refused("revenue", raw)


# ============================================================================
# date
# ============================================================================


@pytest.mark.parametrize("key", _keys_of_shape(S.DATE))
@pytest.mark.parametrize("raw", [date(2028, 10, 10), "2028-10-10"], ids=["date", "iso"])
def test_date_stored_form(key, raw):
    assert normalize_value(key, raw) == "2028-10-10"


@pytest.mark.parametrize("key", _keys_of_shape(S.DATE))
@pytest.mark.parametrize(
    "raw",
    [
        datetime(2028, 10, 10),
        datetime(2028, 10, 10, 12, 30),
        "20281010",
        "2028-10-10T00:00:00",
        "10/10/2028",
        "2028-02-30",
        "2028-1-5",
        " 2028-10-10",
        "",
        20281010,
        ["2028-10-10"],
    ],
    ids=lambda v: repr(v),
)
def test_date_refused(key, raw):
    _refused(key, raw)


# ============================================================================
# text
# ============================================================================


@pytest.mark.parametrize("key", _keys_of_shape(S.TEXT))
@pytest.mark.parametrize(
    "raw, stored",
    [
        ("iShares Core MSCI World", "iShares Core MSCI World"),
        ("  Vanguard  ", "Vanguard"),
        ("\tRepubblica Italiana\n", "Repubblica Italiana"),
    ],
)
def test_text_stored_form(key, raw, stored):
    assert normalize_value(key, raw) == stored


@pytest.mark.parametrize("key", _keys_of_shape(S.TEXT))
@pytest.mark.parametrize("raw", ["", "   ", "\n\t ", 5, True, ["text"], {"text": "x"}], ids=lambda v: repr(v))
def test_text_refused(key, raw):
    _refused(key, raw)


# ============================================================================
# choice
# ============================================================================


@pytest.mark.parametrize("key, code", [(k, c) for k, codes in CHOICES.items() for c in codes])
def test_choice_accepted(key, code):
    assert normalize_value(key, code) == code


def test_choice_codes_match_catalogue():
    for key, codes in CHOICES.items():
        assert CATALOGUE[key].choices == codes, key


@pytest.mark.parametrize("key", list(CHOICES))
@pytest.mark.parametrize("raw", ["not_a_code", "", " ", 1, True], ids=lambda v: repr(v))
def test_choice_refused(key, raw):
    _refused(key, raw)


@pytest.mark.parametrize("raw", ["Accumulating", "ACCUMULATING", " accumulating", "accumulating ", "acc"])
def test_choice_is_exact(raw):
    _refused("distribution_policy", raw)
    assert normalize_value("distribution_policy", "accumulating") == "accumulating"


def test_choice_codes_of_another_voice_refused():
    _refused("distribution_policy", "physical_full")
    _refused("replication", "accumulating")


# ============================================================================
# country
# ============================================================================


@pytest.mark.parametrize("key", _keys_of_shape(S.COUNTRY))
@pytest.mark.parametrize("raw, stored", [("IRL", "IRL"), ("irl", "IRL"), ("Lux", "LUX"), ("USA", "USA")])
def test_country_stored_form(key, raw, stored):
    assert normalize_value(key, raw) == stored


@pytest.mark.parametrize("key", _keys_of_shape(S.COUNTRY))
@pytest.mark.parametrize("raw", ["IE", "ie", "Ireland", "ZZZ", "IR", "", "372", 372, ["IRL"]], ids=lambda v: repr(v))
def test_country_refused(key, raw):
    _refused(key, raw)


# ============================================================================
# currency
# ============================================================================


@pytest.mark.parametrize("key", _keys_of_shape(S.CURRENCY))
@pytest.mark.parametrize("raw, stored", [("USD", "USD"), ("usd", "USD"), ("eUr", "EUR"), ("CHF", "CHF")])
def test_currency_stored_form(key, raw, stored):
    assert normalize_value(key, raw) == stored


@pytest.mark.parametrize("key", _keys_of_shape(S.CURRENCY))
@pytest.mark.parametrize("raw", ["EURO", "978", "XX", "ZZZ", "", "$", 978, ["EUR"]], ids=lambda v: repr(v))
def test_currency_refused(key, raw):
    _refused(key, raw)


# ============================================================================
# map
# ============================================================================


def test_map_geography_stored_form():
    out = normalize_value("geography", {"USA": "0.6", "JPN": "0.4"})
    assert out == {"JPN": "0.4000", "USA": "0.6000"}
    assert list(out) == sorted(out)


def test_map_sector_stored_form():
    out = normalize_value("sector", {"Technology": "0.35", "Financials": Decimal("0.25"), "Health Care": "0.40"})
    assert out == {"Financials": "0.2500", "Health Care": "0.4000", "Technology": "0.3500"}
    assert list(out) == sorted(out)


def test_map_int_weight_accepted():
    assert normalize_value("geography", {"USA": 1}) == {"USA": "1.0000"}


def test_map_key_order_does_not_change_the_form():
    a = normalize_value("geography", {"USA": "0.6", "JPN": "0.4"})
    b = normalize_value("geography", {"JPN": "0.4", "USA": "0.6"})
    assert a == b
    assert json.dumps(a) == json.dumps(b)


def test_map_rounding_does_not_change_the_form():
    a = normalize_value("geography", {"USA": "0.60331", "JPN": "0.39669"})
    b = normalize_value("geography", {"USA": "0.6033", "JPN": "0.3967"})
    assert a == b
    assert json.dumps(a) == json.dumps(b)


def test_map_thirds_tie_does_not_depend_on_input_order():
    third = "0.33333333"
    a = normalize_value("geography", {"USA": third, "JPN": third, "ITA": third})
    b = normalize_value("geography", {"ITA": third, "JPN": third, "USA": third})
    c = normalize_value("geography", {"JPN": third, "USA": third, "ITA": third})
    assert a == b == c
    assert json.dumps(a) == json.dumps(b) == json.dumps(c)
    assert list(a) == ["ITA", "JPN", "USA"]
    for weight in a.values():
        assert isinstance(weight, str)
        assert len(weight.split(".")[1]) == 4
    assert sum(Decimal(w) for w in a.values()) == Decimal("1")


@pytest.mark.parametrize(
    "key, spellings",
    [
        # "US" sorts where "USA" does among FRA and ITA: same tie whichever key breaks it
        ("geography", [("USA", "ITA", "FRA"), ("US", "ITA", "FRA"), ("ITA", "FRA", "US")]),
        # "Germany" and "de" sort elsewhere than "DEU": a tie broken on the spelling moves the remainder
        ("geography", [("DEU", "FRA", "ITA"), ("Germany", "FRA", "ITA"), ("FRA", "ITA", "de")]),
        # "healthcare" sorts after "Technology" and "Energy", but "Energy" is first either way
        ("sector", [("Health Care", "Technology", "Energy"), ("healthcare", "Technology", "Energy"), ("Technology", "Energy", "healthcare")]),
        # "healthcare" sorts after "Utilities" while "Health Care" sorts first: the spelling decides the tie
        ("sector", [("Health Care", "Technology", "Utilities"), ("healthcare", "Technology", "Utilities"), ("Utilities", "Technology", "healthcare")]),
    ],
    ids=["geography-US", "geography-Germany-de", "sector-healthcare-energy", "sector-healthcare-utilities"],
)
def test_map_thirds_tie_does_not_depend_on_key_spelling(key, spellings):
    """The renormalization tie is broken on the canonical key, not on how (or where) the input spelled it."""
    third = "0.33333333"
    forms = [normalize_value(key, dict.fromkeys(keys, third)) for keys in spellings]
    assert forms == [forms[0]] * len(forms)
    assert len({json.dumps(form) for form in forms}) == 1
    assert sum(Decimal(w) for w in forms[0].values()) == Decimal("1")


@pytest.mark.parametrize("key", _keys_of_shape(S.MAP))
def test_map_weights_four_decimals_summing_to_one(key):
    raw = {"USA": "0.6", "JPN": "0.4"} if key == "geography" else {"Technology": "0.6", "Energy": "0.4"}
    out = normalize_value(key, raw)
    assert all(isinstance(w, str) and len(w.split(".")[1]) == 4 for w in out.values())
    assert sum(Decimal(w) for w in out.values()) == Decimal("1")


@pytest.mark.parametrize(
    "key, raw",
    [
        ("geography", {}),
        ("sector", {}),
        ("geography", {"USA": "1", "JPN": "1", "ITA": "1"}),
        ("sector", {"Technology": "1.5", "Energy": "1.5"}),
        ("geography", {"USA": 0.6, "JPN": 0.4}),
        ("sector", {"Technology": 0.5, "Energy": 0.5}),
        ("geography", {"USA": True}),
        ("geography", {"USA": "abc"}),
        ("geography", {"USA": "NaN"}),
        ("geography", {"USA": "1.2", "JPN": "-0.2"}),
        ("geography", {"USA": "0", "JPN": "0"}),
        ("geography", {"distribution": {"USA": "0.6", "JPN": "0.4"}}),
        ("geography", [{"USA": "1"}]),
        ("geography", "USA"),
        ("sector", "Technology"),
    ],
    ids=lambda v: repr(v),
)
def test_map_refused(key, raw):
    _refused(key, raw)


# ============================================================================
# table (coupon_schedule)
# ============================================================================

TABLE_KEY = "coupon_schedule"


def test_table_stored_form():
    raw = [
        {"from": "2025-01-01", "to": "2025-12-31", "rate": "0.0300"},
        {"from": date(2026, 1, 1), "to": date(2026, 12, 31), "rate": Decimal("0.0350")},
    ]
    assert normalize_value(TABLE_KEY, raw) == [
        {"from": "2025-01-01", "to": "2025-12-31", "rate": "0.03"},
        {"from": "2026-01-01", "to": "2026-12-31", "rate": "0.035"},
    ]


def test_table_unordered_rows_sorted_by_from():
    raw = [
        {"from": "2027-01-01", "to": "2027-12-31", "rate": "0.04"},
        {"from": "2025-01-01", "to": "2025-12-31", "rate": "0.03"},
        {"from": "2026-01-01", "to": "2026-12-31", "rate": "0.035"},
    ]
    out = normalize_value(TABLE_KEY, raw)
    assert [row["from"] for row in out] == ["2025-01-01", "2026-01-01", "2027-01-01"]
    assert out[0] == {"from": "2025-01-01", "to": "2025-12-31", "rate": "0.03"}
    assert json.dumps(out) == json.dumps(normalize_value(TABLE_KEY, list(reversed(raw))))


def test_table_single_day_row_and_zero_rate_accepted():
    out = normalize_value(TABLE_KEY, [{"from": "2028-10-10", "to": "2028-10-10", "rate": "0"}])
    assert out == [{"from": "2028-10-10", "to": "2028-10-10", "rate": "0"}]


def test_table_row_starting_the_day_after_accepted():
    raw = [
        {"from": "2025-01-01", "to": "2025-06-30", "rate": "0.02"},
        {"from": "2025-07-01", "to": "2025-12-31", "rate": "0.025"},
    ]
    assert len(normalize_value(TABLE_KEY, raw)) == 2


ROW = {"from": "2025-01-01", "to": "2025-12-31", "rate": "0.03"}


@pytest.mark.parametrize(
    "raw",
    [
        [],
        ROW,
        "2025-01-01",
        [["2025-01-01", "2025-12-31", "0.03"]],
        [{"from": "2025-01-01", "to": "2025-12-31", "rate": "0.03", "extra": "x"}],
        [{"from": "2025-01-01", "to": "2025-12-31"}],
        [{"from": "2025-01-01", "rate": "0.03"}],
        [{"to": "2025-12-31", "rate": "0.03"}],
        [{"from_": "2025-01-01", "to": "2025-12-31", "rate": "0.03"}],
        [{"from": "2025-12-31", "to": "2025-01-01", "rate": "0.03"}],
        [{"from": "2025-01-01", "to": "2025-12-31", "rate": "-0.01"}],
        [{"from": "2025-01-01", "to": "2025-12-31", "rate": 0.03}],
        [{"from": "2025-01-01", "to": "2025-12-31", "rate": True}],
        [{"from": "2025-01-01", "to": "2025-12-31", "rate": "NaN"}],
        [{"from": "20250101", "to": "2025-12-31", "rate": "0.03"}],
        [{"from": "2025-01-01", "to": "2025-02-30", "rate": "0.03"}],
        [{"from": datetime(2025, 1, 1), "to": "2025-12-31", "rate": "0.03"}],
        # overlap: the second row starts on the first row's last day
        [ROW, {"from": "2025-12-31", "to": "2026-12-31", "rate": "0.035"}],
        # overlap: the second row starts inside the first
        [ROW, {"from": "2025-06-01", "to": "2026-12-31", "rate": "0.035"}],
        # overlap given out of order
        [{"from": "2025-06-01", "to": "2026-12-31", "rate": "0.035"}, ROW],
        # one row contained in another
        [ROW, {"from": "2025-03-01", "to": "2025-04-30", "rate": "0.035"}],
        # the same row twice
        [ROW, dict(ROW)],
    ],
    ids=lambda v: repr(v)[:80],
)
def test_table_refused(raw):
    _refused(TABLE_KEY, raw)


# ============================================================================
# (d) IDEMPOTENCY
# ============================================================================

#: One valid example of every shape (the stored form of each is checked above).
IDEMPOTENCY_EXAMPLES = [
    ("modified_duration", "6.780"),
    ("ter", Decimal("0.0022")),
    ("fund_size", {"amount": "55173000000.00", "currency": "eur"}),
    ("maturity_date", date(2028, 10, 10)),
    ("description", "  An index fund.  "),
    ("replication", "physical_sampling"),
    ("fund_domicile", "irl"),
    ("fund_currency", "usd"),
    ("geography", {"USA": "0.60331", "JPN": "0.39669"}),
    ("sector", {"Technology": "0.5", "Financials": "0.5"}),
    ("coupon_schedule", [{"from": "2026-01-01", "to": "2026-12-31", "rate": "0.0350"}, {"from": date(2025, 1, 1), "to": date(2025, 12, 31), "rate": "0.030"}]),
]


def test_idempotency_examples_cover_every_shape():
    shapes = {EXPECTED_BY_KEY[key].shape for key, _ in IDEMPOTENCY_EXAMPLES}
    assert shapes == set(ProfileShape)


@pytest.mark.parametrize("key, raw", IDEMPOTENCY_EXAMPLES, ids=[k for k, _ in IDEMPOTENCY_EXAMPLES])
def test_idempotent(key, raw):
    once = normalize_value(key, raw)
    assert once is not None
    assert normalize_value(key, once) == once
    round_trip = json.loads(json.dumps(once))
    assert normalize_value(key, round_trip) == once
    assert json.dumps(normalize_value(key, round_trip)) == json.dumps(once)


# ============================================================================
# (e) The labels of the windows (lot E10c2): every voice, choice, group and unit has a label in the four languages
# ============================================================================

#: The frontend folder that holds the profile's labels (``assets.profile.*``, its ``prefixes.txt``).
LABELS_DIR = Path(__file__).resolve().parents[3] / "frontend" / "src" / "lib" / "features" / "assets" / "profile" / "i18n"
LANGUAGES = ("en", "it", "fr", "es")


def _labels(language: str) -> dict:
    return json.loads((LABELS_DIR / f"{language}.json").read_text(encoding="utf-8"))["assets"]["profile"]


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_voice_has_a_label(language):
    """The catalogue drives the expectation here on purpose: a voice added to the backend without its label turns
    this red (C2e's ``management_fee`` included)."""
    labels = _labels(language)
    assert set(labels["voices"]) == set(EXPECTED_KEYS) == set(CATALOGUE), "voices without a label, or labels without a voice"
    assert all(isinstance(text, str) and text.strip() for text in labels["voices"].values())


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_choice_has_a_label(language):
    labels = _labels(language)["choices"]
    assert set(labels) == {key for key, voice in CATALOGUE.items() if voice.choices}
    for key, voice in CATALOGUE.items():
        if voice.choices:
            assert set(labels[key]) == set(voice.choices), key
            assert all(text.strip() for text in labels[key].values()), key


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_group_and_unit_has_a_label(language):
    """The six groups, plus ``other`` for the voices with no group (the LEI, the amount outstanding)."""
    labels = _labels(language)
    assert set(labels["groups"]) == {group.value for group in ProfileGroup} | {"other"}
    assert set(labels["units"]) == {voice.unit for voice in CATALOGUE.values() if voice.unit}


def test_every_voice_has_a_topic_and_every_topic_a_voice():
    """E7b: each voice declares its topic in the catalogue (the table above is the expectation), and no topic is left
    without a voice."""
    assert set(TOPICS) == set(EXPECTED_KEYS)
    assert {voice.topic for voice in CATALOGUE.values()} == set(ProfileTopic)


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_topic_has_a_label(language):
    """The enrichers' window says what each enricher fills in topics: every topic has its label in the four languages."""
    assert set(_labels(language)["topics"]) == {topic.value for topic in ProfileTopic}
