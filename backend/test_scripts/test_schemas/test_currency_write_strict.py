"""
Strict ISO 4217 codes on the write paths, tolerant reads — MF-SEC9b, lot E-18 (workstream E).

Before: every currency field goes through ``Currency.validate_code`` (``schemas/common.py``). It upper-cases and strips
the input, asks ``pycountry.currencies.lookup`` (an alpha-3 code, a numeric code or a name, any case) and returns the
normalised INPUT, not the alpha-3 code. So ``"978"``, ``"999"``, ``"EURO"``, ``"us dollar"`` (as ``"US DOLLAR"``) and the
five ISO names three letters long (``Lek``, ``Yen``, ``Som``, ``Won``, ``Sol``, none of them a code) are accepted and
stored as they came. A transaction's cash and cost basis are a ``Currency``, whose code has no length limit: every form
passes there. The asset and FX request fields are ``min_length=3, max_length=3``: only the three-character forms (the
numeric codes, the five names) pass there, and the longer ones are refused by length already (guards here, not reds).

Now, as the release coordinator decided on 17/10:

1. ``backend.app.schemas.common`` gains ``iso_currency_code(value) -> str`` and
   ``IsoCurrencyCode = Annotated[str, BeforeValidator(iso_currency_code)]``. Whitespace around the code (NBSP included)
   is stripped and the code upper-cased. What is left must be an ISO 4217 alpha-3 code: ``" eur "`` gives ``"EUR"``,
   ``"GBp"`` gives ``"GBP"``, ``XXX``, ``XTS`` and ``XAU`` are accepted. Everything else is a ``ValueError`` (a
   ``ValidationError`` through the type): a name, a numeric code, a ticker that is no ISO code, a look-alike letter, an
   empty or spaced text, a non-string. The message names the rule (``ISO 4217``) and never echoes more than 16
   characters of the input.
2. The write paths take that rule:
   - ``TXCreateItem`` and ``TXUpdateItem``: cash and cost basis;
   - the promote cost basis: ``TXPromoteResolvedFields`` and ``TXTransferPromoteRequest``;
   - ``FAAssetCreateItem`` and ``FAAssetPatchItem``: currency;
   - the value of ``FAEventUpsertPoint``, alone and in ``FAEventUpsert.events``;
   - ``FXUpsertItem``: base and quote;
   - ``FXConversionRouteItem``: base, quote and every step of its chain.
   The Investimental BRIM plugin also reads an account's currency with that rule (``_extract_currency_from_account``):
   a lenient code there is no currency, so it gives ``None``. An accepted code comes back upper-cased, and the wire shape
   does not change (``model_dump()`` holds ``"EUR"`` where ``" eur "`` was given).
3. The read paths stay as tolerant as today: a row stored as ``"978"`` or ``"US DOLLAR"`` still loads, lists and can be
   deleted. They are ``Currency``, ``Currency.validate_code``, ``CurrencyCode``, ``TXReadItem``, ``FXRouteStep`` (the
   routes listing rebuilds steps from stored JSON), ``FXConversionRouteReadItem`` (the routes listing builds it from
   every stored route: E-18 makes ``FXConversionRouteItem`` strict without its read subclass inheriting the check),
   ``FXDeleteItem``, ``FXDeleteRouteItem``, ``FAAssetEventPoint``
   (provider events), ``BRIMTruthCash``, ``FAPricePoint`` and the read/filter requests (``TXQueryParams``,
   ``FAAinfoFiltersRequest``, ``FAEventQueryItem``, ``FXPeriodChangesRequest``, ``FXConversionRequest``). The global
   settings rule (``settings._check_currency``) was strict already and stays so.

The expected values are written out here, not computed from the module: they are the contract, and a test that read them
from ``Currency.validate_code`` would follow any change of it.

"RED" tests (marked ``# red until E-18``) fail on the code before E-18 for two reasons. ``iso_currency_code`` and
``IsoCurrencyCode`` do not exist yet: they are looked up inside each test, so the file collects and each red fails on
its own. And the write paths accept the lenient forms. Each test of a write path first validates the same payload with
``"EUR"`` (the positive control), so a refusal can only be about the code under test, and a red can only fail because
the lenient code is accepted. "Guard" tests pass before and after: what the write paths accept or refuse today and still
do, and the read paths unchanged.

Pure: no database, no server, no network, no file. Pydantic models and plain functions only.
"""

import json
from dataclasses import dataclass
from itertools import pairwise
from typing import Annotated, Any, Callable, get_args, get_origin

import pytest
from pydantic import BaseModel, BeforeValidator, TypeAdapter, ValidationError, create_model

from backend.app.schemas import common as common_module
from backend.app.schemas.assets.assets import FAAinfoFiltersRequest, FAAssetCreateItem, FAAssetPatchItem
from backend.app.schemas.assets.events import FAAssetEventPoint, FAEventQueryItem, FAEventUpsert, FAEventUpsertPoint
from backend.app.schemas.brim import BRIMTruthCash
from backend.app.schemas.common import Currency, CurrencyCode
from backend.app.schemas.fx import FXConversionRequest, FXConversionRouteItem, FXConversionRouteReadItem, FXDeleteItem, FXDeleteRouteItem, FXPeriodChangesRequest, FXRouteStep, FXUpsertItem
from backend.app.schemas.prices import FAPricePoint
from backend.app.schemas.settings import _check_currency
from backend.app.schemas.transactions.batch import TXPromoteResolvedFields
from backend.app.schemas.transactions.promotion import TXTransferPromoteRequest
from backend.app.schemas.transactions.transactions import TXCreateItem, TXQueryParams, TXReadItem, TXUpdateItem
from backend.app.services.brim_providers.broker_investimental.plugin import _extract_currency_from_account

# =============================================================================
# THE VALUES (the contract of 17/10, written out)
# =============================================================================

#: Accepted by the strict rule: the input, and the code it gives back.
STRICT_ACCEPTS = (
    ("EUR", "EUR"),
    ("eur", "EUR"),
    (" eur ", "EUR"),
    ("EUR\u00a0", "EUR"),
    ("\tchf\n", "CHF"),
    ("GBp", "GBP"),
    ("XXX", "XXX"),
    ("XTS", "XTS"),
    ("XAU", "XAU"),
)

#: Lenient forms ``Currency.validate_code`` accepts today, three characters long: the numeric codes of EUR and XXX, and
#: the five ISO names three letters long. The strict rule refuses them, and so do the write paths once E-18 lands.
LENIENT_THREE_CHARS = ("978", "999", "YEN", "LEK", "SOM", "WON", "SOL")

#: Lenient forms longer than three characters: currency names. A field limited to three characters refuses them by
#: length today already (a guard there); a field with no length limit accepts them today (a red there).
LENIENT_LONGER = ("EURO", "euro", "US DOLLAR", "Pound Sterling")

#: What ``Currency.validate_code`` refuses today already, and the strict rule too: no ISO code at all (a crypto ticker,
#: the pence of GBP, an unknown code), an empty or blank text, a look-alike letter (Cyrillic, fullwidth), spaced letters.
REFUSED_TODAY = ("BTC", "GBX", "ZZZ", "", "   ", "\u0415UR", "\uff25\uff35\uff32", "E U R")

#: Every text the strict rule refuses: the lenient forms, then what is refused today already.
STRICT_REFUSES = LENIENT_THREE_CHARS + LENIENT_LONGER + REFUSED_TODAY

#: Not a string: refused by the strict rule.
NON_STRINGS = (978, None)

#: Readable test ids for the values whose text would not be.
_IDS: dict[Any, str] = {
    "": "empty",
    "   ": "blank",
    " eur ": "spaced-eur",
    "EUR\u00a0": "eur-nbsp",
    "\tchf\n": "tab-chf-newline",
    "\u0415UR": "cyrillic-E",
    "\uff25\uff35\uff32": "fullwidth-EUR",
    "E U R": "spaced-letters",
    978: "int-978",
    None: "None",
}


def _slug(value: Any) -> str:
    """The id of a value in a test name."""
    return _IDS.get(value, str(value).replace(" ", "_"))


# =============================================================================
# THE STRICT RULE, LOOKED UP WHEN A TEST RUNS (absent before E-18)
# =============================================================================


def _strict_function() -> Callable[[Any], str]:
    """``iso_currency_code``, or the test fails. Looked up here, not imported, so the file collects before E-18."""
    function = getattr(common_module, "iso_currency_code", None)
    if function is None:
        pytest.fail("red until E-18: backend.app.schemas.common.iso_currency_code does not exist yet")
    return function


def _strict_type() -> Any:
    """``IsoCurrencyCode``, or the test fails, as for ``_strict_function``."""
    annotated = getattr(common_module, "IsoCurrencyCode", None)
    if annotated is None:
        pytest.fail("red until E-18: backend.app.schemas.common.IsoCurrencyCode does not exist yet")
    return annotated


def _strict_model() -> type[BaseModel]:
    """A model with one ``IsoCurrencyCode`` field, ``code``."""
    return create_model("IsoCurrencyCodeProbe", code=(_strict_type(), ...))


#: An input of 10 000 characters: the message must not echo it.
LONG_INPUT = "Q" * 10_000


# =============================================================================
# 1. THE STRICT RULE: iso_currency_code and IsoCurrencyCode
# =============================================================================


@pytest.mark.parametrize("value,expected", [pytest.param(value, expected, id=_slug(value)) for value, expected in STRICT_ACCEPTS])
def test_iso_currency_code_accepts_and_uppercases(value, expected):  # red until E-18
    """CWS-001 — RED: an ISO 4217 code in any case, with whitespace around (NBSP included), comes back as its upper-case code."""
    assert _strict_function()(value) == expected


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in STRICT_REFUSES])
def test_iso_currency_code_refuses_what_is_no_iso_code(value):  # red until E-18
    """CWS-002 — RED: a ValueError for anything that is no ISO 4217 alpha-3 code.

    That covers a numeric code, a name (three letters long or not), a ticker or a pence code, an unknown code, an empty
    or blank text, a look-alike letter (Cyrillic, fullwidth) and spaced letters.
    """
    function = _strict_function()
    assert function("EUR") == "EUR", "positive control"
    with pytest.raises(ValueError):
        function(value)


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in NON_STRINGS])
def test_iso_currency_code_refuses_a_non_string(value):  # red until E-18
    """CWS-003 — RED: a non-string (the number 978, None) is a ValueError, not a TypeError or an AttributeError."""
    function = _strict_function()
    assert function("EUR") == "EUR", "positive control"
    with pytest.raises(ValueError):
        function(value)


def test_iso_currency_code_message_is_bounded():  # red until E-18
    """CWS-004 — RED: refusing 10 000 characters, the message names the rule and echoes at most 16 characters of them."""
    function = _strict_function()
    with pytest.raises(ValueError) as refused:
        function(LONG_INPUT)
    message = str(refused.value)
    assert "Q" * 17 not in message, f"the message echoes the input ({len(message)} characters)"
    assert "ISO 4217" in message, message


def test_iso_currency_code_type_is_a_string_checked_before_validation():  # red until E-18
    """CWS-005 — RED: ``IsoCurrencyCode`` is ``Annotated[str, BeforeValidator(iso_currency_code)]``, a JSON string on the wire."""
    function = _strict_function()
    annotated = _strict_type()
    assert get_origin(annotated) is Annotated, annotated
    base, *metadata = get_args(annotated)
    assert base is str, base
    assert any(isinstance(item, BeforeValidator) and item.func is function for item in metadata), metadata
    assert TypeAdapter(annotated).json_schema()["type"] == "string"


@pytest.mark.parametrize("value,expected", [pytest.param(value, expected, id=_slug(value)) for value, expected in STRICT_ACCEPTS])
def test_iso_currency_code_type_accepts_and_uppercases_in_a_model(value, expected):  # red until E-18
    """CWS-006 — RED: through ``IsoCurrencyCode``, a model holds the upper-case code, and so does its dump."""
    item = _strict_model()(code=value)
    assert item.code == expected
    assert item.model_dump() == {"code": expected}


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in STRICT_REFUSES + NON_STRINGS])
def test_iso_currency_code_type_refuses_in_a_model(value):  # red until E-18
    """CWS-007 — RED: through ``IsoCurrencyCode``, whatever the rule refuses is a ValidationError on the field."""
    model = _strict_model()
    assert model(code="EUR").code == "EUR", "positive control"
    with pytest.raises(ValidationError) as refused:
        model(code=value)
    assert [error["loc"] for error in refused.value.errors()] == [("code",)], refused.value.errors()


def test_iso_currency_code_type_message_is_bounded():  # red until E-18
    """CWS-008 — RED: through ``IsoCurrencyCode``, the message of the refusal is bounded as in CWS-004."""
    model = _strict_model()
    with pytest.raises(ValidationError) as refused:
        model(code=LONG_INPUT)
    messages = [error["msg"] for error in refused.value.errors()]
    assert all("Q" * 17 not in message for message in messages), [len(message) for message in messages]
    assert any("ISO 4217" in message for message in messages), messages


# =============================================================================
# 2. THE WRITE PATHS: the strict rule, the same wire shape
# =============================================================================


@dataclass(frozen=True)
class WriteSite:
    """A currency field of a write path: its model built around one code, and where the code lands in the dump."""

    name: str
    build: Callable[[Any], BaseModel]  # the minimum valid payload, with the code in the field under test
    path: tuple[str | int, ...]  # where the code lands in model_dump(by_alias=True)
    length_limited: bool = False  # min_length=3, max_length=3: a longer form is refused by length, today already
    raw_length: bool = False  # the length is checked on the raw input, before any strip: a whitespace form fails it

    def code_in_dump(self, item: BaseModel) -> Any:
        value: Any = item.model_dump(by_alias=True)
        for key in self.path:
            value = value[key]
        return value


def _money(code: Any, amount: str = "100") -> dict:
    return {"code": code, "amount": amount}


def _route(base: Any, quote: Any, nodes: list) -> FXConversionRouteItem:
    """A route from ``base`` to ``quote`` through ``nodes``, one MOCKFX step per edge (``validate_chain`` holds)."""
    steps = [{"from": source, "to": target, "provider": "MOCKFX"} for source, target in pairwise(nodes)]
    return FXConversionRouteItem.model_validate({"base": base, "quote": quote, "priority": 1, "chain_steps": steps})


# A DEPOSIT takes cash (positive, no asset, quantity 0). An ADJUSTMENT received (quantity > 0) and a TRANSFER received
# (quantity > 0, link_uuid) take a cost basis: required_qty_pos in TX_TYPE_METADATA. A route's middle code is the `to`
# of one step and the `from` of the next: with valid base and quote, a lenient code can only sit there and still pass
# validate_chain, whose endpoints must match the pair. The fixed codes around it (RON, SEK, USD) are none of the codes
# tested, so no step ever goes from a code to itself.
WRITE_SITES = (
    WriteSite("TXCreateItem.cash", lambda code: TXCreateItem.model_validate({"broker_id": 1, "type": "DEPOSIT", "date": "2025-01-15", "cash": _money(code)}), ("cash", "code")),
    WriteSite("TXCreateItem.cost_basis_override-ADJUSTMENT", lambda code: TXCreateItem.model_validate({"broker_id": 1, "asset_id": 1, "type": "ADJUSTMENT", "date": "2025-01-15", "quantity": "5", "cost_basis_override": _money(code, "42.50")}), ("cost_basis_override", "code")),
    WriteSite("TXCreateItem.cost_basis_override-TRANSFER", lambda code: TXCreateItem.model_validate({"broker_id": 1, "asset_id": 1, "type": "TRANSFER", "date": "2025-01-15", "quantity": "5", "link_uuid": "cws-pair", "cost_basis_override": _money(code, "42.50")}), ("cost_basis_override", "code")),
    WriteSite("TXUpdateItem.cash", lambda code: TXUpdateItem.model_validate({"id": 1, "cash": _money(code)}), ("cash", "code")),
    WriteSite("TXUpdateItem.cost_basis_override", lambda code: TXUpdateItem.model_validate({"id": 1, "cost_basis_override": _money(code, "42.50")}), ("cost_basis_override", "code")),
    WriteSite("TXPromoteResolvedFields.cost_basis_override", lambda code: TXPromoteResolvedFields.model_validate({"cost_basis_override": _money(code, "42.50")}), ("cost_basis_override", "code")),
    WriteSite("TXTransferPromoteRequest.cost_basis_override", lambda code: TXTransferPromoteRequest.model_validate({"from_tx_id": 1, "to_tx_id": 2, "new_type": "TRANSFER", "asset_id": 1, "quantity": "5", "cost_basis_override": _money(code, "42.50")}), ("cost_basis_override", "code")),
    WriteSite("FAAssetCreateItem.currency", lambda code: FAAssetCreateItem.model_validate({"display_name": "CWS asset", "currency": code}), ("currency",), length_limited=True, raw_length=True),
    WriteSite("FAAssetPatchItem.currency", lambda code: FAAssetPatchItem.model_validate({"asset_id": 1, "currency": code}), ("currency",), length_limited=True, raw_length=True),
    WriteSite("FAEventUpsertPoint.value", lambda code: FAEventUpsertPoint.model_validate({"date": "2025-01-15", "type": "DIVIDEND", "value": _money(code, "1.5")}), ("value", "code")),
    WriteSite("FAEventUpsert.events.value", lambda code: FAEventUpsert.model_validate({"asset_id": 1, "events": [{"date": "2025-01-15", "type": "DIVIDEND", "value": _money(code, "1.5")}]}), ("events", 0, "value", "code")),
    WriteSite("FXUpsertItem.base", lambda code: FXUpsertItem.model_validate({"date": "2025-01-15", "base": code, "quote": "USD", "rate": "1.1"}), ("base",), length_limited=True),
    WriteSite("FXUpsertItem.quote", lambda code: FXUpsertItem.model_validate({"date": "2025-01-15", "base": "USD", "quote": code, "rate": "1.1"}), ("quote",), length_limited=True),
    WriteSite("FXConversionRouteItem.base", lambda code: _route(code, "USD", [code, "USD"]), ("base",), length_limited=True),
    WriteSite("FXConversionRouteItem.quote", lambda code: _route("RON", code, ["RON", code]), ("quote",), length_limited=True),
    WriteSite("FXConversionRouteItem.chain_steps-middle-of-2", lambda code: _route("RON", "USD", ["RON", code, "USD"]), ("chain_steps", 0, "to"), length_limited=True),
    WriteSite("FXConversionRouteItem.chain_steps-1st-middle-of-3", lambda code: _route("RON", "USD", ["RON", code, "SEK", "USD"]), ("chain_steps", 0, "to"), length_limited=True),
    WriteSite("FXConversionRouteItem.chain_steps-2nd-middle-of-3", lambda code: _route("RON", "USD", ["RON", "SEK", code, "USD"]), ("chain_steps", 1, "to"), length_limited=True),
)


def _positive_control(site: WriteSite) -> None:
    """The same payload with ``"EUR"`` validates and holds ``"EUR"``: a refusal of another code is about that code alone."""
    try:
        item = site.build("EUR")
    except ValidationError as error:
        pytest.fail(f"positive control: {site.name} refuses 'EUR', the payload is malformed: {error.errors()}")
    assert site.code_in_dump(item) == "EUR", f"positive control: {site.name} holds {site.code_in_dump(item)!r} for 'EUR'"


def _write_params(sites, values) -> list:
    return [pytest.param(site, value, id=f"{site.name}-{_slug(value)}") for site in sites for value in values]


#: Reds: every write site, with the lenient forms it accepts today (no longer forms where the length refuses them).
WRITE_REDS = [pytest.param(site, value, id=f"{site.name}-{_slug(value)}") for site in WRITE_SITES for value in (LENIENT_THREE_CHARS if site.length_limited else LENIENT_THREE_CHARS + LENIENT_LONGER)]

#: Guards: what the strict rule accepts, where the write site accepts it today (a raw length check refuses whitespace).
WRITE_ACCEPTS = [pytest.param(site, value, expected, id=f"{site.name}-{_slug(value)}") for site in WRITE_SITES for value, expected in STRICT_ACCEPTS if not site.raw_length or len(value) == 3]


@pytest.mark.parametrize("site,value", WRITE_REDS)
def test_write_path_refuses_lenient_code(site, value):  # red until E-18
    """CWS-010 — RED: a write path refuses a lenient code (numeric, an ISO name) with a ValidationError, its positive control passing."""
    _positive_control(site)
    try:
        item = site.build(value)
    except ValidationError:
        return
    pytest.fail(f"red until E-18: {site.name} accepted the lenient code {value!r} and holds {site.code_in_dump(item)!r}")


@pytest.mark.parametrize("site,value,expected", WRITE_ACCEPTS)
def test_write_path_accepts_and_uppercases_what_the_strict_rule_accepts(site, value, expected):
    """CWS-011 — Guard: a write path accepts an ISO code in any case, and its dump holds the upper-case code (the wire shape is unchanged)."""
    assert site.code_in_dump(site.build(value)) == expected


@pytest.mark.parametrize("site,value", _write_params([site for site in WRITE_SITES if site.length_limited], LENIENT_LONGER))
def test_length_limited_write_path_refuses_longer_forms_already(site, value):
    """CWS-012 — Guard: a field limited to three characters refuses a currency name by length today already, and still does."""
    _positive_control(site)
    with pytest.raises(ValidationError):
        site.build(value)


@pytest.mark.parametrize("site,value", _write_params(WRITE_SITES, REFUSED_TODAY))
def test_write_path_still_refuses_what_it_refuses_today(site, value):
    """CWS-013 — Guard: what no write path accepts today (an unknown code, empty, a look-alike letter, spaced letters) stays refused."""
    _positive_control(site)
    with pytest.raises(ValidationError):
        site.build(value)


# The Investimental plugin takes an account's currency from its name, as in 'JOHN DOE [RON]': BRIM input, a write path.

#: Accounts whose currency is the same before and after E-18: a code in any case, and no currency at all.
BRIM_ACCOUNTS_UNCHANGED = (
    ("JOHN DOE [RON]", "RON"),
    ("JOHN DOE [eur]", "EUR"),
    ("JOHN DOE [ eur ]", "EUR"),
    ("no brackets", None),
    ("JOHN DOE []", None),
    ("JOHN DOE [BTC]", None),
    ("JOHN DOE [GBX]", None),
)


def _brim_positive_control() -> None:
    assert _extract_currency_from_account("JOHN DOE [EUR]") == "EUR", "positive control: the account 'JOHN DOE [EUR]' gives no 'EUR'"


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in LENIENT_THREE_CHARS + LENIENT_LONGER])
def test_brim_account_currency_refuses_lenient_code(value):  # red until E-18
    """CWS-014 — RED: an account named with a lenient code ('JOHN DOE [978]', '[YEN]', '[EURO]') has no currency: None."""
    _brim_positive_control()
    account = f"JOHN DOE [{value}]"
    taken = _extract_currency_from_account(account)
    if taken is not None:
        pytest.fail(f"red until E-18: {account!r} gives the currency {taken!r}; a lenient code is no currency (None)")


@pytest.mark.parametrize("account,expected", [pytest.param(account, expected, id=_slug(account)) for account, expected in BRIM_ACCOUNTS_UNCHANGED])
def test_brim_account_currency_unchanged(account, expected):
    """CWS-015 — Guard: an ISO code in any case gives its upper-case code; no brackets, empty brackets, a code that is not ISO give None."""
    _brim_positive_control()
    assert _extract_currency_from_account(account) == expected


# =============================================================================
# 3. THE READ PATHS: as tolerant as today
# =============================================================================


@dataclass(frozen=True)
class ReadSite:
    """A currency field of a read path: what it holds for one code. A refusal is a ValueError (ValidationError is one)."""

    name: str
    read: Callable[[Any], Any]
    length_limited: bool = False  # min_length=3, max_length=3 (after the strip of a before-validator)


_STAMP = "2025-01-15T10:00:00Z"
_CURRENCY_CODE = TypeAdapter(CurrencyCode)


def _tx_read(field: str, code: Any) -> Any:
    """``TXReadItem`` with its minimum fields and ``field`` (cash or cost basis) in ``code``, as a stored row lists."""
    item = TXReadItem.model_validate({"id": 1, "broker_id": 1, "type": "DEPOSIT", "date": "2025-01-15", "quantity": "0", field: _money(code), "created_at": _STAMP, "updated_at": _STAMP})
    return getattr(item, field).code


READ_SITES = (
    ReadSite("Currency.code", lambda code: Currency(code=code, amount="1").code),
    ReadSite("Currency.validate_code", Currency.validate_code),
    ReadSite("CurrencyCode", _CURRENCY_CODE.validate_python),
    ReadSite("TXReadItem.cash", lambda code: _tx_read("cash", code)),
    ReadSite("TXReadItem.cost_basis_override", lambda code: _tx_read("cost_basis_override", code)),
    ReadSite("FXRouteStep.from", lambda code: FXRouteStep.model_validate({"from": code, "to": "USD", "provider": "MOCKFX"}).from_currency, length_limited=True),
    ReadSite("FXRouteStep.to", lambda code: FXRouteStep.model_validate({"from": "USD", "to": code, "provider": "MOCKFX"}).to_currency, length_limited=True),
    ReadSite("FXDeleteItem.from", lambda code: FXDeleteItem.model_validate({"from": code, "to": "USD", "delete_all": True}).from_currency, length_limited=True),
    ReadSite("FXDeleteItem.to", lambda code: FXDeleteItem.model_validate({"from": "USD", "to": code, "delete_all": True}).to_currency, length_limited=True),
    ReadSite("FXDeleteRouteItem.base", lambda code: FXDeleteRouteItem.model_validate({"base": code, "quote": "USD"}).base, length_limited=True),
    ReadSite("FXDeleteRouteItem.quote", lambda code: FXDeleteRouteItem.model_validate({"base": "USD", "quote": code}).quote, length_limited=True),
    ReadSite("FAAssetEventPoint.value", lambda code: FAAssetEventPoint.model_validate({"date": "2025-01-15", "type": "DIVIDEND", "value": _money(code, "1.5")}).value.code),
    ReadSite("BRIMTruthCash.currency", lambda code: BRIMTruthCash(currency=code, amount="10").currency),
    ReadSite("FAPricePoint.currency", lambda code: FAPricePoint.model_validate({"date": "2025-01-15", "close": "10", "currency": code}).currency),
    ReadSite("TXQueryParams.currency", lambda code: TXQueryParams.model_validate({"currency": code}).currency, length_limited=True),
    ReadSite("FAAinfoFiltersRequest.currency", lambda code: FAAinfoFiltersRequest.model_validate({"currency": code}).currency),
    ReadSite("FAEventQueryItem.target_currency", lambda code: FAEventQueryItem.model_validate({"asset_id": 1, "date_range": {"start": "2025-01-01", "end": "2025-01-31"}, "target_currency": code}).target_currency),
    ReadSite("FXPeriodChangesRequest.base", lambda code: FXPeriodChangesRequest.model_validate({"base": code, "quote": "USD", "as_of": "2025-01-15"}).base, length_limited=True),
    ReadSite("FXPeriodChangesRequest.quote", lambda code: FXPeriodChangesRequest.model_validate({"base": "USD", "quote": code, "as_of": "2025-01-15"}).quote, length_limited=True),
    ReadSite("FXConversionRequest.from_amount", lambda code: FXConversionRequest.model_validate({"from_amount": _money(code, "1"), "to": "USD", "date_range": {"start": "2025-01-15"}}).from_amount.code),
    ReadSite("FXConversionRequest.to", lambda code: FXConversionRequest.model_validate({"from_amount": _money("USD", "1"), "to": code, "date_range": {"start": "2025-01-15"}}).to_currency, length_limited=True),
)

#: What a read path with no length limit holds today, and keeps: what ``Currency.validate_code`` returns today.
READ_KEEPS = (
    ("978", "978"),
    ("999", "999"),
    ("YEN", "YEN"),
    ("SOL", "SOL"),
    ("EURO", "EURO"),
    ("euro", "EURO"),
    ("US DOLLAR", "US DOLLAR"),
    ("us dollar", "US DOLLAR"),
    ("Pound Sterling", "POUND STERLING"),
    (" eur ", "EUR"),
    ("GBp", "GBP"),
)

#: What a read path limited to three characters holds today, and keeps.
READ_KEEPS_THREE_CHARS = (("978", "978"), ("999", "999"), ("YEN", "YEN"), ("SOL", "SOL"), (" eur ", "EUR"), ("GBp", "GBP"))

#: Refused by every read path today, and still: no ISO 4217 code in any form. The longer forms too, where the length is limited.
READ_REFUSES = ("BTC", "GBX", "ZZZ")
READ_REFUSES_LONGER = ("EURO", "US DOLLAR", "Pound Sterling")


def _read_positive_control(site: ReadSite) -> None:
    assert site.read("EUR") == "EUR", f"positive control: {site.name} does not hold 'EUR'"


@pytest.mark.parametrize(
    "site,value,expected",
    [pytest.param(site, value, expected, id=f"{site.name}-{_slug(value)}") for site in READ_SITES for value, expected in (READ_KEEPS_THREE_CHARS if site.length_limited else READ_KEEPS)],
)
def test_read_path_keeps_what_it_accepts_today(site, value, expected):
    """CWS-020 — Guard: a read path accepts a stored lenient code ('978', 'US DOLLAR'…) and returns what it returns today."""
    assert site.read(value) == expected


@pytest.mark.parametrize(
    "site,value",
    [pytest.param(site, value, id=f"{site.name}-{_slug(value)}") for site in READ_SITES for value in READ_REFUSES + (READ_REFUSES_LONGER if site.length_limited else ())],
)
def test_read_path_refuses_what_it_refuses_today(site, value):
    """CWS-021 — Guard: what a read path refuses today it still refuses: tolerant means unchanged, not looser."""
    _read_positive_control(site)
    with pytest.raises(ValueError):
        site.read(value)


def test_stored_route_step_from_a_numeric_code_to_its_alpha_code_still_loads():
    """CWS-022 — Guard: a step stored as 978 → EUR (EUR's numeric code, then EUR) loads as stored, as the routes listing rebuilds it.

    A read path that turned '978' into 'EUR' would refuse it: ``FXRouteStep`` requires from and to to differ.
    """
    step = FXRouteStep(**{"from": "978", "to": "EUR", "provider": "MOCKFX"})
    assert step.model_dump(by_alias=True) == {"from": "978", "to": "EUR", "provider": "MOCKFX"}


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in ("978", "YEN", "EURO", "US DOLLAR", "BTC")])
def test_global_setting_currency_refuses_what_is_no_iso_code(value):
    """CWS-023 — Guard: the global settings rule was strict already, and stays so: a numeric code or a name is a ValueError."""
    assert _check_currency("EUR") == "EUR", "positive control"
    with pytest.raises(ValueError):
        _check_currency(value)


@pytest.mark.parametrize("value", ["eur", "EUR"])
def test_global_setting_currency_accepts_and_uppercases(value):
    """CWS-024 — Guard: the global settings rule accepts an ISO code in any case and stores it upper-case."""
    assert _check_currency(value) == "EUR"


#: Routes as the table holds them after a lenient write (before E-18), with "978" (EUR's numeric code) as the base, the
#: quote or a middle step. The pair is stored in alphabetical order (``base < quote``, CHECK
#: ``ck_route_base_less_than_quote``): a digit sorts before every letter, so "978" is the quote only beside another
#: numeric code ("826", GBP's). The steps are the JSON text ``create_routes_bulk`` writes; the metadata is what
#: ``_route_metadata`` derives from them: ``is_chain`` for more than one step, ``providers_used`` the steps' providers,
#: unique and sorted.
STORED_ROUTES_WITH_978 = (
    pytest.param(
        {"base": "978", "quote": "USD", "priority": 1, "chain_steps": '[{"from": "978", "to": "USD", "provider": "ECB"}]'},
        {"is_chain": False, "providers_used": ["ECB"]},
        id="base-978",
    ),
    pytest.param(
        {"base": "826", "quote": "978", "priority": 1, "chain_steps": '[{"from": "826", "to": "978", "provider": "BOE"}]'},
        {"is_chain": False, "providers_used": ["BOE"]},
        id="quote-978",
    ),
    pytest.param(
        {"base": "RON", "quote": "USD", "priority": 2, "chain_steps": '[{"from": "RON", "to": "978", "provider": "ECB"}, {"from": "978", "to": "USD", "provider": "FED"}]'},
        {"is_chain": True, "providers_used": ["ECB", "FED"]},
        id="middle-step-978",
    ),
)


@pytest.mark.parametrize("row,metadata", STORED_ROUTES_WITH_978)
def test_stored_route_with_a_numeric_code_still_lists(row, metadata):
    """CWS-025 — Guard: a stored route holding "978" (base, quote or a middle step) still lists, every value as stored.

    The routes listing (``list_routes``, ``api/v1/fx/providers.py``) builds an ``FXConversionRouteReadItem`` from every
    stored row, exactly as here: one row it refuses turns the whole listing into a 500. ``FXConversionRouteReadItem``
    subclasses ``FXConversionRouteItem``, which E-18 makes strict (CWS-010), so E-18 must do that without the read
    subclass inheriting the check. It is the only read-side subclass of the strict targets (verified by the release
    coordinator on 17/10). The stored values are what ``Currency.validate_code`` returns today, and they are kept.
    """
    item = FXConversionRouteReadItem(
        base=row["base"],
        quote=row["quote"],
        priority=row["priority"],
        chain_steps=[FXRouteStep(**s) for s in json.loads(row["chain_steps"])],
        **metadata,
    )
    expected = {"base": row["base"], "quote": row["quote"], "priority": row["priority"], "chain_steps": json.loads(row["chain_steps"]), **metadata}
    assert item.model_dump(by_alias=True) == expected
