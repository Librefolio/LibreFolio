"""
Tests for Broker Pydantic schemas.

Tests BRCreateItem, BRReadItem, BRUpdateItem, BRDeleteItem validation rules.
See checklist: 01_test_broker_transaction_subsystem.md - Category 2

Reference: backend/app/schemas/brokers.py
"""

from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.schemas.brokers import (
    BRCreateItem,
    BRDeleteItem,
    BRReadItem,
    BRUpdateItem,
)
from backend.app.schemas.common import Currency

# ============================================================================
# 2.1 NAME VALIDATION
# ============================================================================


class TestBrokerNameValidation:
    """Test broker name validation rules."""

    def test_broker_name_required(self):
        """BR-S-001: Broker without name should fail."""
        with pytest.raises(ValidationError):
            BRCreateItem()  # name is required

    def test_broker_name_empty(self):
        """BR-S-002: Broker with empty name should fail."""
        # min_length=1 constraint catches this before custom validator
        with pytest.raises(ValidationError, match="at least 1 character"):
            BRCreateItem(name="")

    def test_broker_name_whitespace(self):
        """BR-S-003: Broker with whitespace-only name should fail."""
        with pytest.raises(ValidationError, match="Broker name cannot be empty"):
            BRCreateItem(name="   ")

    def test_broker_name_valid(self):
        """BR-S-004: Broker with valid name should pass."""
        broker = BRCreateItem(name="Interactive Brokers")
        assert broker.name == "Interactive Brokers"

    def test_broker_name_max_length(self):
        """BR-S-005: Broker with name > 100 chars should fail."""
        long_name = "A" * 101
        with pytest.raises(ValidationError, match="at most 100"):
            BRCreateItem(name=long_name)

    def test_broker_name_trimmed(self):
        """Broker name should be trimmed of leading/trailing whitespace."""
        broker = BRCreateItem(name="  Degiro  ")
        assert broker.name == "Degiro"


# ============================================================================
# 2.2 INITIAL BALANCES VALIDATION
# ============================================================================


class TestInitialBalancesValidation:
    """Test initial_balances validation rules."""

    def test_initial_balances_none(self):
        """BR-S-010: Broker without initial_balances should pass."""
        broker = BRCreateItem(name="Test Broker")
        assert broker.initial_balances is None

    def test_initial_balances_explicit_none(self):
        """Explicit None should be preserved by validator."""
        broker = BRCreateItem(name="Test Broker", initial_balances=None)
        assert broker.initial_balances is None

    def test_initial_balances_empty_list(self):
        """BR-S-011: Broker with empty list should pass (becomes None)."""
        broker = BRCreateItem(name="Test Broker", initial_balances=[])
        assert broker.initial_balances is None

    def test_initial_balances_positive(self):
        """BR-S-012: Broker with positive amounts should keep them."""
        broker = BRCreateItem(
            name="Test Broker",
            initial_balances=[
                Currency(code="EUR", amount=Decimal("5000")),
                Currency(code="USD", amount=Decimal("3000")),
            ],
        )
        assert len(broker.initial_balances) == 2
        assert broker.initial_balances[0].amount == Decimal("5000")

    def test_initial_balances_zero_filtered(self):
        """BR-S-013: Zero amounts should be filtered out."""
        broker = BRCreateItem(
            name="Test Broker",
            initial_balances=[
                Currency(code="EUR", amount=Decimal("5000")),
                Currency(code="USD", amount=Decimal("0")),  # Should be filtered
            ],
        )
        assert len(broker.initial_balances) == 1
        assert broker.initial_balances[0].code == "EUR"

    def test_initial_balances_negative_filtered(self):
        """BR-S-014: Negative amounts should be filtered out."""
        broker = BRCreateItem(
            name="Test Broker",
            initial_balances=[
                Currency(code="EUR", amount=Decimal("-1000")),  # Should be filtered
            ],
        )
        # All filtered out, becomes None
        assert broker.initial_balances is None

    def test_initial_balances_mixed(self):
        """BR-S-015: Mixed amounts should keep only positive."""
        broker = BRCreateItem(
            name="Test Broker",
            initial_balances=[
                Currency(code="EUR", amount=Decimal("5000")),  # Keep
                Currency(code="USD", amount=Decimal("-1000")),  # Filter
                Currency(code="GBP", amount=Decimal("0")),  # Filter
                Currency(code="CHF", amount=Decimal("2000")),  # Keep
            ],
        )
        assert len(broker.initial_balances) == 2
        codes = [c.code for c in broker.initial_balances]
        assert "EUR" in codes
        assert "CHF" in codes


# ============================================================================
# 2.2b R13-SEC7-3 — AN INITIAL BALANCE PAST THE EXPONENT BOUND IS REFUSED
# ============================================================================


class TestInitialBalanceExponentBound:
    """R13-SEC7-3 (E's R13-SEC7, finding 3): an initial balance is a ``Currency``, so the cure's bound applies to it —
    an amount whose ``Decimal.adjusted()`` lies outside [-100, 100] is refused when ``POST /brokers`` validates its body:
    a ``ValidationError`` on ``initial_balances.<i>.amount``, the route's 422, before ``BrokerService.create_bulk``
    could build the deposit's raw row with ``format(amount, "f")`` (a billion digits for ``1E+999999999``).

    Red today: accepted, the amount positive, so the broker would get a deposit of it.
    """

    @pytest.mark.parametrize("amount", ["1E+101", "1E+5000000", "1E+999999999"])
    def test_an_initial_balance_past_the_exponent_bound_is_refused_on_its_amount(self, amount):
        """Contract: refused on the second balance's amount, behind a valid one; the item is never built."""
        try:
            BRCreateItem(name="Exponent Bound Broker", initial_balances=[{"code": "EUR", "amount": "100"}, {"code": "USD", "amount": amount}])
        except ValidationError as exc:
            locs = [tuple(error["loc"]) for error in exc.errors()]
            assert ("initial_balances", 1, "amount") in locs, f"R13-SEC7-3: the initial balance of {amount} USD was refused, but not on its amount: {locs}"
            return
        pytest.fail(f"R13-SEC7-3: BRCreateItem accepted an initial balance of {amount} USD (adjusted() = {Decimal(amount).adjusted()}); an amount whose exponent lies outside [-100, 100] must be refused at the boundary: POST /brokers answers 422")

    def test_guard_an_initial_balance_at_the_bound_is_kept(self):
        """Guard: green today and after. 1E+100 is inside the bound: the schema keeps it (the batch, not the schema,
        refuses its digits later), next to an ordinary balance."""
        broker = BRCreateItem(name="Exponent Bound Broker", initial_balances=[{"code": "EUR", "amount": "100"}, {"code": "USD", "amount": "1E+100"}])

        assert [(balance.code, balance.amount) for balance in broker.initial_balances] == [("EUR", Decimal("100")), ("USD", Decimal("1E+100"))]


# ============================================================================
# 2.3 UPDATE SCHEMA
# ============================================================================


class TestBrokerUpdateSchema:
    """Test BRUpdateItem validation rules."""

    def test_update_all_fields_optional(self):
        """BR-S-020: BRUpdateItem with no fields should pass."""
        update = BRUpdateItem()
        assert update.name is None
        assert update.description is None
        assert update.allow_cash_overdraft is None

    def test_update_name_explicit_none(self):
        """Explicit None should pass through name validator."""
        update = BRUpdateItem(name=None)
        assert update.name is None

    def test_update_name_empty(self):
        """BR-S-021: BRUpdateItem with empty name should fail."""
        # min_length=1 constraint catches this before custom validator
        with pytest.raises(ValidationError, match="at least 1 character"):
            BRUpdateItem(name="")

    def test_update_name_valid(self):
        """BR-S-022: BRUpdateItem with valid name should pass."""
        update = BRUpdateItem(name="New Broker Name")
        assert update.name == "New Broker Name"

    def test_update_name_whitespace(self):
        """Whitespace-only update name should fail."""
        with pytest.raises(ValidationError, match="Broker name cannot be empty"):
            BRUpdateItem(name="   ")

    def test_update_description(self):
        """Update description should work."""
        update = BRUpdateItem(description="New description")
        assert update.description == "New description"

    def test_update_portal_url(self):
        """Update portal_url should work."""
        update = BRUpdateItem(portal_url="https://broker.com")
        assert update.portal_url == "https://broker.com"

    def test_update_url_explicit_none(self):
        """Explicit None should mean no update for URL fields."""
        update = BRUpdateItem(portal_url=None, icon_url=None)
        assert update.portal_url is None
        assert update.icon_url is None

    def test_update_empty_url_clears_field(self):
        """Empty or whitespace URLs should become explicit clear markers."""
        update = BRUpdateItem(portal_url="   ", icon_url="\n\t")
        assert update.portal_url == ""
        assert update.icon_url == ""

    def test_update_overdraft_flag(self):
        """Update allow_cash_overdraft should work."""
        update = BRUpdateItem(allow_cash_overdraft=True)
        assert update.allow_cash_overdraft is True

    def test_update_shorting_flag(self):
        """Update allow_asset_shorting should work."""
        update = BRUpdateItem(allow_asset_shorting=True)
        assert update.allow_asset_shorting is True


# ============================================================================
# 2.4 DELETE SCHEMA
# ============================================================================


class TestBrokerDeleteSchema:
    """Test BRDeleteItem validation rules."""

    def test_delete_force_default(self):
        """BR-S-030: BRDeleteItem with only id should have force=False."""
        delete = BRDeleteItem(id=1)
        assert delete.id == 1
        assert delete.force is False

    def test_delete_force_true(self):
        """BR-S-031: BRDeleteItem with force=True should pass."""
        delete = BRDeleteItem(id=1, force=True)
        assert delete.force is True

    def test_delete_id_required(self):
        """BR-S-032: BRDeleteItem without id should fail."""
        with pytest.raises(ValidationError):
            BRDeleteItem()  # id is required

    def test_delete_id_positive(self):
        """BRDeleteItem with id <= 0 should fail."""
        with pytest.raises(ValidationError, match="greater than 0"):
            BRDeleteItem(id=0)

        with pytest.raises(ValidationError, match="greater than 0"):
            BRDeleteItem(id=-1)


# ============================================================================
# CREATE ITEM FLAGS
# ============================================================================


class TestBrokerCreateFlags:
    """Test flag defaults in BRCreateItem."""

    def test_overdraft_default_false(self):
        """allow_cash_overdraft defaults to False."""
        broker = BRCreateItem(name="Test")
        assert broker.allow_cash_overdraft is False

    def test_shorting_default_false(self):
        """allow_asset_shorting defaults to False."""
        broker = BRCreateItem(name="Test")
        assert broker.allow_asset_shorting is False

    def test_overdraft_explicit_true(self):
        """allow_cash_overdraft can be set to True."""
        broker = BRCreateItem(name="Margin Broker", allow_cash_overdraft=True)
        assert broker.allow_cash_overdraft is True

    def test_shorting_explicit_true(self):
        """allow_asset_shorting can be set to True."""
        broker = BRCreateItem(name="Short Broker", allow_asset_shorting=True)
        assert broker.allow_asset_shorting is True


# ============================================================================
# READ ITEM (from_attributes)
# ============================================================================


class TestBrokerReadItem:
    """Test BRReadItem validation."""

    def test_read_item_from_dict(self):
        """BRReadItem can be created from dict."""
        data = {
            "id": 1,
            "name": "Test Broker",
            "description": "A test broker",
            "portal_url": "https://test.com",
            "allow_cash_overdraft": False,
            "allow_asset_shorting": False,
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        broker = BRReadItem(**data)
        assert broker.id == 1
        assert broker.name == "Test Broker"
        assert broker.is_active is True

    def test_read_item_optional_fields(self):
        """BRReadItem optional fields can be None."""
        data = {
            "id": 1,
            "name": "Test Broker",
            "description": None,
            "portal_url": None,
            "allow_cash_overdraft": True,
            "allow_asset_shorting": False,
            "is_active": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        broker = BRReadItem(**data)
        assert broker.description is None
        assert broker.portal_url is None
        assert broker.is_active is False


# ============================================================================
# THE BROKER'S OPERATING PROFILE (P1 of project 67, contract §7; decisioni-REB §2, M6, M18, M21)
#
# The account keeps its order modes, fees, conversion mode and tax regime as one JSON document in
# ``brokers.operating_profile``, read and written through one Pydantic class that refuses extra keys. Its order mode
# and fee shapes are the planner request's own (D2: imported, never copied). One row per currency (M21);
# ``conversion_mode`` and ``tax_regime`` belong to the broker. An absent ``tax_regime`` reads as ``declarative`` in one
# place only, ``effective_tax_regime`` (M6, M18).
# ============================================================================

import hashlib  # noqa: E402
import json  # noqa: E402
from itertools import product  # noqa: E402
from string import ascii_uppercase  # noqa: E402

from backend.app.schemas.broker_profile import (  # noqa: E402
    OPERATING_PROFILE_MAX_BYTES,
    BrokerOperatingProfile,
    BrokerProfileAmountFeeCap,
    BrokerProfileAmountMode,
    BrokerProfileFeeSchedule,
    BrokerProfileMoney,
    BrokerProfileNoFeeCap,
    BrokerProfileWholeQuantityMode,
    OperatingProfileTooLarge,
    operating_profile_text,
    stored_operating_profile,
)
from backend.app.schemas.pac_allocator.base import PlannerMoneyInput  # noqa: E402
from backend.app.schemas.pac_allocator.request import AmountFeeCap, BrokerFeeScheduleInput, MonetaryAmountCapability, NoFeeCap, PlannerBrokerInput, WholeQuantityCapability  # noqa: E402

#: The contract's example (P1 plan): a whole-quantity mode in EUR with a buy and a sell fee, an amount mode in USD,
#: the broker's conversion mode and tax regime.
PROFILE_DOCUMENT: dict = {
    "profile_version": 1,
    "order_modes": [
        {
            "currency": "EUR",
            "capability": {"kind": "whole_quantity", "capability_id": "mode:EUR", "quantity_unit": "asset_unit", "quantity_step": "1"},
            "fees": [
                {
                    "fee_schedule_id": "fee:EUR:buy",
                    "capability_id": "mode:EUR",
                    "side": "buy",
                    "rate": "0.0019",
                    "variable_floor": {"amount": "2.95", "currency": "EUR"},
                    "variable_cap": {"kind": "amount", "amount": {"amount": "19", "currency": "EUR"}},
                },
                {"fee_schedule_id": "fee:EUR:sell", "capability_id": "mode:EUR", "side": "sell", "fixed_fee": {"amount": "5", "currency": "EUR"}},
            ],
        },
        {
            "currency": "USD",
            "capability": {"kind": "monetary_amount", "capability_id": "mode:USD", "order_amount_step": {"amount": "0.01", "currency": "USD"}},
            "fees": [{"fee_schedule_id": "fee:USD:buy", "capability_id": "mode:USD", "side": "buy", "fixed_fee": {"amount": "1", "currency": "USD"}}],
        },
    ],
    "conversion_mode": "automatic",
    "tax_regime": "administered",
}

#: SHA-256 of the profile's JSON schema, version 1. A change of shape or meaning of a field is a new version (D15):
#: a lot that edits the request's mode or fee classes changes the documents already saved, and this pin says so.
#: TL-6 of project 67 moves it in version 1: ``conversion_mode`` defaults to ``automatic``. Every saved text carries the
#: key (``operating_profile_text``), so no saved profile changes meaning: the two tests below pin both readings.
PROFILE_SCHEMA_FINGERPRINT = "477d05eec4c14cdc8c3e8a06c4caf6399a4ef35535d4a9b8ee4e28661d03036d"


def _document(**changes) -> dict:
    document = json.loads(json.dumps(PROFILE_DOCUMENT))
    document.update(changes)
    return document


def _valid_currency_codes() -> list[str]:
    """Every three-letter code the schema accepts as a currency, in order."""
    codes = []
    for letters in product(ascii_uppercase, repeat=3):
        code = "".join(letters)
        try:
            Currency.validate_code(code)
        except (ValueError, TypeError):
            continue
        codes.append(code)
    return codes


def _schema_fingerprint() -> str:
    return hashlib.sha256(json.dumps(BrokerOperatingProfile.model_json_schema(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _two_modes_in_one_currency(_eur: dict, usd: dict) -> None:
    usd["currency"] = "EUR"
    usd["capability"]["order_amount_step"]["currency"] = "EUR"
    usd["fees"][0]["fixed_fee"]["currency"] = "EUR"


#: What the profile refuses because it can recognise it (decision D4 (b)): each case edits the EUR and USD rows in place.
REFUSALS = {
    "two modes in one currency": _two_modes_in_one_currency,
    "a fee names another mode": lambda eur, _usd: eur["fees"][0].update(capability_id="mode:USD"),
    "two fees on one side": lambda eur, _usd: eur["fees"][1].update(side="buy"),
    "a whole step of zero": lambda eur, _usd: eur["capability"].update(quantity_step="0"),
    "a negative whole step": lambda eur, _usd: eur["capability"].update(quantity_step="-1"),
    "an amount step of zero": lambda _eur, usd: usd["capability"]["order_amount_step"].update(amount="0"),
    "a negative fixed fee": lambda eur, _usd: eur["fees"][1]["fixed_fee"].update(amount="-5"),
    "a negative rate": lambda eur, _usd: eur["fees"][0].update(rate="-0.001"),
    "a negative floor": lambda eur, _usd: eur["fees"][0]["variable_floor"].update(amount="-1"),
    "a negative cap": lambda eur, _usd: eur["fees"][0]["variable_cap"]["amount"].update(amount="-1"),
    "a fee amount in another currency": lambda eur, _usd: eur["fees"][0]["variable_floor"].update(currency="USD"),
    "an amount step in another currency": lambda _eur, usd: usd["capability"]["order_amount_step"].update(currency="EUR"),
}


#: The request class each profile class stands for (D2 (c)): a ``$ref`` is compared by the class it means.
_SAME_SHAPE = {
    "PlannerMoneyInput": "BrokerProfileMoney",
    "WholeQuantityCapability": "BrokerProfileWholeQuantityMode",
    "MonetaryAmountCapability": "BrokerProfileAmountMode",
    "NoFeeCap": "BrokerProfileNoFeeCap",
    "AmountFeeCap": "BrokerProfileAmountFeeCap",
    "BrokerFeeScheduleInput": "BrokerProfileFeeSchedule",
    # The two unions, by name: their members are the classes above, compared one by one.
    "FeeCap": "BrokerProfileFeeCap",
    "BrokerOrderCapability": "BrokerProfileOrderCapability",
}
_IGNORED_SCHEMA_KEYS = {"title", "description", "enum", "default"}


def _comparable(schema):
    """A JSON schema with the keys that do not constrain a value removed, and every ``$ref`` read as the profile class it means."""
    if isinstance(schema, dict):
        out = {}
        for key, value in schema.items():
            if key in _IGNORED_SCHEMA_KEYS:
                continue
            if key == "$ref" and isinstance(value, str):
                name = value.rsplit("/", 1)[-1]
                out[key] = _SAME_SHAPE.get(name, name)
            else:
                out[key] = _comparable(value)
        return out
    if isinstance(schema, list):
        return [_comparable(item) for item in schema]
    if isinstance(schema, str) and schema.startswith("#/$defs/"):
        name = schema.rsplit("/", 1)[-1]
        return _SAME_SHAPE.get(name, name)
    return schema


class TestBrokerOperatingProfile:
    """The operating profile document: shape, refusals, tolerant read, canonical text."""

    def test_profile_accepts_the_document_of_the_contract(self):
        profile = BrokerOperatingProfile.model_validate(PROFILE_DOCUMENT)
        assert [row.currency for row in profile.order_modes] == ["EUR", "USD"]
        assert profile.conversion_mode == "automatic"
        assert stored_operating_profile(operating_profile_text(profile)) == profile

    @pytest.mark.parametrize(
        "where",
        ["root", "order mode row", "capability", "fee", "fee cap", "money"],
    )
    def test_profile_refuses_an_unknown_key_at_every_level(self, where):
        document = _document()
        row = document["order_modes"][0]
        target = {
            "root": document,
            "order mode row": row,
            "capability": row["capability"],
            "fee": row["fees"][0],
            "fee cap": row["fees"][0]["variable_cap"],
            "money": row["fees"][0]["variable_floor"],
        }[where]
        target["unexpected"] = "x"
        with pytest.raises(ValidationError) as caught:
            BrokerOperatingProfile.model_validate(document)
        assert "extra_forbidden" in {error["type"] for error in caught.value.errors()}

    @pytest.mark.parametrize("version", [0, 2, "1", None, 1.0, True])
    def test_profile_refuses_an_unknown_version(self, version):
        with pytest.raises(ValidationError):
            BrokerOperatingProfile.model_validate(_document(profile_version=version))

    @pytest.mark.parametrize(
        ("profile_class", "request_class"),
        [
            (BrokerProfileMoney, PlannerMoneyInput),
            (BrokerProfileWholeQuantityMode, WholeQuantityCapability),
            (BrokerProfileAmountMode, MonetaryAmountCapability),
            (BrokerProfileNoFeeCap, NoFeeCap),
            (BrokerProfileAmountFeeCap, AmountFeeCap),
            (BrokerProfileFeeSchedule, BrokerFeeScheduleInput),
        ],
    )
    def test_profile_shapes_have_the_planner_request_fields(self, profile_class, request_class):
        """D2 (c): each profile class has the request class's fields, with the same requiredness and defaults."""
        profile_fields, request_fields = profile_class.model_fields, request_class.model_fields
        assert set(profile_fields) == set(request_fields)
        for name, field in request_fields.items():
            assert profile_fields[name].is_required() == field.is_required(), name
            if not field.is_required():
                ours = profile_fields[name].get_default(call_default_factory=True)
                theirs = field.get_default(call_default_factory=True)
                assert (ours.model_dump() if hasattr(ours, "model_dump") else ours) == (theirs.model_dump() if hasattr(theirs, "model_dump") else theirs), name

    @pytest.mark.parametrize(
        ("profile_class", "request_class"),
        [
            (BrokerProfileMoney, PlannerMoneyInput),
            (BrokerProfileWholeQuantityMode, WholeQuantityCapability),
            (BrokerProfileAmountMode, MonetaryAmountCapability),
            (BrokerProfileNoFeeCap, NoFeeCap),
            (BrokerProfileAmountFeeCap, AmountFeeCap),
            (BrokerProfileFeeSchedule, BrokerFeeScheduleInput),
        ],
    )
    def test_profile_fields_have_the_planner_request_constraints(self, profile_class, request_class):
        """Every field's JSON schema — type, pattern, lengths, the shape it nests — is the request's, so a lot that tightens
        a rule in ``schemas/pac_allocator`` turns this red. Ignored: titles, descriptions, the ``enum`` the profile adds
        beside a ``const`` (for the client generator), defaults (compared above) and the class names a ``$ref`` points to."""
        ours = _comparable(profile_class.model_json_schema()["properties"])
        theirs = _comparable(request_class.model_json_schema()["properties"])
        assert ours == theirs

    def test_profile_shapes_are_the_planner_request_shapes(self):
        """A row's capability and fees, taken as they are, validate as a request broker's ``capabilities`` and
        ``fee_schedules``; and the request's own capabilities and fees, dumped, validate as profile rows: the same JSON."""
        rows = PROFILE_DOCUMENT["order_modes"]
        request_broker = PlannerBrokerInput.model_validate(
            {
                "broker_id": "broker:1",
                "identity": {"kind": "manual_broker", "name": "Probe"},
                "provenance_id": "manual:broker:1",
                "capabilities": [row["capability"] for row in rows],
                "fee_schedules": [fee for row in rows for fee in row["fees"]],
                "conversion_mode": PROFILE_DOCUMENT["conversion_mode"],
            }
        )
        dumped_rows = []
        for row in rows:
            capability = next(item for item in request_broker.capabilities if item.capability_id == row["capability"]["capability_id"])
            fees = [fee for fee in request_broker.fee_schedules if fee.capability_id == capability.capability_id]
            dumped_rows.append({"currency": row["currency"], "capability": capability.model_dump(mode="json"), "fees": [fee.model_dump(mode="json") for fee in fees]})
        profile = BrokerOperatingProfile.model_validate({**PROFILE_DOCUMENT, "order_modes": dumped_rows})
        assert profile == BrokerOperatingProfile.model_validate(PROFILE_DOCUMENT)

    def test_profile_document_shape_is_frozen_for_version_1(self):
        assert _schema_fingerprint() == PROFILE_SCHEMA_FINGERPRINT, "the operating profile's shape changed: a new optional field keeps version 1, a change of shape or meaning is a new " "version whose reader converts the old one (decision D15); then pin the new fingerprint"

    def test_a_profile_saved_with_manual_still_reads_manual(self):
        """TL-6: a text as the old code saved it — rules and ``manual``, the old default, written out — reads ``manual``, and
        is written back with it: the user changes it by hand."""
        saved = operating_profile_text(BrokerOperatingProfile.model_validate(_document(conversion_mode="manual")))
        assert json.loads(saved)["conversion_mode"] == "manual"
        profile = stored_operating_profile(saved)
        assert profile is not None and profile.conversion_mode == "manual"
        assert json.loads(operating_profile_text(profile))["conversion_mode"] == "manual"

    def test_a_profile_without_the_conversion_reads_the_broker_converting(self):
        """TL-6: no conversion said reads ``automatic`` (the developer, 23/11), and the saved text says it."""
        document = _document()
        del document["conversion_mode"]
        profile = BrokerOperatingProfile.model_validate(document)
        assert profile.conversion_mode == "automatic"
        assert json.loads(operating_profile_text(profile))["conversion_mode"] == "automatic"
        empty = stored_operating_profile(json.dumps({"profile_version": 1}))
        assert empty is not None and empty.conversion_mode == "automatic"

    @pytest.mark.parametrize("case", list(REFUSALS))
    def test_profile_refuses_what_it_can_recognise(self, case):
        document = _document()
        REFUSALS[case](*document["order_modes"])
        with pytest.raises(ValidationError):
            BrokerOperatingProfile.model_validate(document)

    @pytest.mark.parametrize(
        "raw",
        [None, "", "not json", "[1, 2]", '"text"', json.dumps(_document(profile_version=2)), json.dumps(_document(extra=1)), '{"profile_version": 1, "order_modes": [{"currency": "EUR"}]}'],
    )
    def test_stored_profile_read_is_tolerant(self, raw):
        assert stored_operating_profile(raw) is None

    def test_stored_profile_reads_a_valid_text(self):
        assert stored_operating_profile(json.dumps(PROFILE_DOCUMENT)) == BrokerOperatingProfile.model_validate(PROFILE_DOCUMENT)

    def test_profile_text_is_canonical_and_capped(self):
        profile = BrokerOperatingProfile.model_validate(PROFILE_DOCUMENT)
        reordered = BrokerOperatingProfile.model_validate(json.loads(json.dumps(PROFILE_DOCUMENT, sort_keys=True)))
        assert operating_profile_text(profile) == operating_profile_text(reordered)
        assert len(operating_profile_text(profile).encode()) < OPERATING_PROFILE_MAX_BYTES
        assert OPERATING_PROFILE_MAX_BYTES == 16_384
        many = _document(
            order_modes=[
                {
                    "currency": code,
                    "capability": {"kind": "whole_quantity", "capability_id": f"mode:{code}:{'x' * 100}", "quantity_unit": "asset_unit", "quantity_step": "1"},
                    "fees": [],
                }
                for code in _valid_currency_codes()[:120]
            ]
        )
        with pytest.raises(OperatingProfileTooLarge):
            operating_profile_text(BrokerOperatingProfile.model_validate(many))

    @pytest.mark.parametrize("regime", ["administered", "declarative"])
    def test_tax_regime_has_two_values(self, regime):
        assert BrokerOperatingProfile.model_validate(_document(tax_regime=regime)).effective_tax_regime == regime

    def test_an_absent_tax_regime_means_declarative(self):
        document = _document()
        del document["tax_regime"]
        profile = BrokerOperatingProfile.model_validate(document)
        assert profile.tax_regime is None
        assert profile.effective_tax_regime == "declarative"
        assert "tax_regime" not in json.loads(operating_profile_text(profile))

    @pytest.mark.parametrize("value", [True, None, "unknown", "", "withholds"])
    def test_tax_regime_refuses_any_other_value(self, value):
        with pytest.raises(ValidationError):
            BrokerOperatingProfile.model_validate(_document(tax_regime=value))

    def test_the_old_withholds_taxes_field_is_refused(self):
        with pytest.raises(ValidationError):
            BrokerOperatingProfile.model_validate(_document(withholds_taxes=True))

    def test_each_currency_row_is_one_rule_set(self):
        """M21: a row holds the order mode, its step and its fees; conversion and tax regime are the broker's."""
        for key, value in (("conversion_mode", "manual"), ("tax_regime", "declarative")):
            document = _document()
            document["order_modes"][0][key] = value
            with pytest.raises(ValidationError):
                BrokerOperatingProfile.model_validate(document)


class TestBrokerProfileInTheBrokerSchemas:
    """The profile in the broker DTOs (P1, steps 3 and 4): read tolerantly, written through ``PATCH`` only (D5, D7)."""

    @staticmethod
    def _read_data(**changes) -> dict:
        data = {
            "id": 1,
            "name": "Profile probe",
            "allow_cash_overdraft": False,
            "allow_asset_shorting": False,
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        data.update(changes)
        return data

    def test_update_item_tells_an_absent_profile_from_null(self):
        absent = BRUpdateItem(name="Renamed")
        cleared = BRUpdateItem(operating_profile=None)
        written = BRUpdateItem(operating_profile=PROFILE_DOCUMENT)
        assert "operating_profile" not in absent.model_fields_set
        assert "operating_profile" in cleared.model_fields_set and cleared.operating_profile is None
        assert written.operating_profile == BrokerOperatingProfile.model_validate(PROFILE_DOCUMENT)

    def test_update_item_refuses_an_unknown_profile_key(self):
        with pytest.raises(ValidationError):
            BRUpdateItem(operating_profile=_document(unexpected=1))

    def test_create_item_refuses_a_profile(self):
        """D7: no profile at creation; a guard, green before and after the lot."""
        with pytest.raises(ValidationError) as caught:
            BRCreateItem(name="New broker", operating_profile=PROFILE_DOCUMENT)
        assert "extra_forbidden" in {error["type"] for error in caught.value.errors()}

    def test_read_item_parses_a_stored_profile_and_survives_a_bad_one(self):
        class StoredBroker:
            def __init__(self, text):
                for key, value in self_data.items():
                    setattr(self, key, value)
                self.operating_profile = text

        self_data = self._read_data()
        read = BRReadItem.model_validate(StoredBroker(operating_profile_text(BrokerOperatingProfile.model_validate(PROFILE_DOCUMENT))))
        assert read.operating_profile == BrokerOperatingProfile.model_validate(PROFILE_DOCUMENT)
        for broken in ("not json", '{"profile_version": 9}', "[]"):
            assert BRReadItem.model_validate(StoredBroker(broken)).operating_profile is None
        assert BRReadItem.model_validate(StoredBroker(None)).operating_profile is None
        assert BRReadItem(**self._read_data()).operating_profile is None

    @pytest.mark.parametrize("with_regime", [True, False])
    def test_what_get_serves_patch_takes_back(self, with_regime):
        """The broker panel and «Save to the broker's profile» (D18) send back what they read: the served profile, a
        profile without a tax regime included, is a valid update. An absent regime is served absent, never as null."""
        document = _document()
        if not with_regime:
            del document["tax_regime"]
        served = json.loads(BRReadItem(**self._read_data(operating_profile=document)).model_dump_json())["operating_profile"]

        assert ("tax_regime" in served) is with_regime
        assert BRUpdateItem(operating_profile=served).operating_profile == BrokerOperatingProfile.model_validate(document)
