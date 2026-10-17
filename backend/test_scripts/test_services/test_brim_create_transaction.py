"""
Tests for BRIMProvider._create_transaction() helper method.

Covers:
  - Valid transaction → appended to transactions list
  - Invalid transaction (validation error) → structured BRIMValidationIssue
  - Multiple validation errors → multiple issues appended
  - Context parameter preservation
  - Fee transaction pattern (same helper, different kwargs)
  - W-B75 (written by H, for W): a refused transaction's params. A field's error (a value_error, whose context holds
    the exception itself; string_too_long) carries none, and the parse output holding it serializes; a lone
    model-level business rule keeps its plain context, a packed one each rule's; BRIMProvider._lone_error_params,
    the transaction batch's rule (W-B72)
"""

import json
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from backend.app.schemas.brim import BRIMParseOutput, BRIMParseResponse, BRIMValidationIssue
from backend.app.schemas.common import MAX_DECIMAL_EXPONENT, Currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.brim_provider import BRIMProvider


class ConcreteBRIMProvider(BRIMProvider):
    """Minimal concrete implementation for testing base class methods."""

    @property
    def provider_code(self) -> str:
        return "test_provider"

    @property
    def provider_name(self) -> str:
        return "Test Provider"

    @property
    def description(self) -> str:
        return "Test provider for unit tests"

    def can_parse(self, file_path):
        return True

    def parse(self, file_path, broker_id):
        return BRIMParseOutput(transactions=[], warnings=[], extracted_assets={})


class TestCreateTransaction:
    """Tests for BRIMProvider._create_transaction()."""

    @pytest.fixture
    def provider(self):
        return ConcreteBRIMProvider()

    def test_valid_transaction_returns_item(self, provider):
        """Valid kwargs → TXCreateItem returned and appended to transactions."""
        transactions = []
        issues = []
        result = provider._create_transaction(
            row_num=5,
            transactions=transactions,
            validation_issues=issues,
            broker_id=1,
            asset_id=100,
            type="BUY",
            date=date(2024, 1, 15),
            quantity=Decimal("10"),
            cash=Currency(code="EUR", amount=Decimal("-1000")),
            tags=["import", "test"],
        )
        assert result is not None
        assert isinstance(result, TXCreateItem)
        assert len(transactions) == 1
        assert transactions[0] is result
        assert len(issues) == 0

    def test_invalid_cash_sign_produces_issue(self, provider):
        """DIVIDEND with negative cash → cashSignPositive validation issue."""
        transactions = []
        issues = []
        result = provider._create_transaction(
            row_num=13,
            transactions=transactions,
            validation_issues=issues,
            context="DIVIDEND: ACME Corp",
            broker_id=1,
            asset_id=100,
            type="DIVIDEND",
            date=date(2024, 6, 1),
            quantity=Decimal("0"),
            cash=Currency(code="EUR", amount=Decimal("-50")),
        )
        assert result is None
        assert len(transactions) == 0
        assert len(issues) >= 1
        issue = issues[0]
        assert isinstance(issue, BRIMValidationIssue)
        assert issue.row == 13
        assert issue.code == "cashSignPositive"
        assert issue.context == "DIVIDEND: ACME Corp"

    def test_missing_cash_produces_issue(self, provider):
        """BUY without cash → cashRequired validation issue."""
        transactions = []
        issues = []
        result = provider._create_transaction(
            row_num=7,
            transactions=transactions,
            validation_issues=issues,
            broker_id=1,
            asset_id=100,
            type="BUY",
            date=date(2024, 1, 15),
            quantity=Decimal("10"),
            cash=None,
        )
        assert result is None
        assert len(transactions) == 0
        assert len(issues) >= 1
        # Should have cashRequired
        codes = {i.code for i in issues}
        assert "cashRequired" in codes

    def test_multiple_errors_produce_multiple_issues(self, provider):
        """Transaction with several violations → one issue per error (unpacked from multipleBusinessRuleErrors)."""
        transactions = []
        issues = []
        # SELL with positive quantity AND negative cash (two violations)
        result = provider._create_transaction(
            row_num=20,
            transactions=transactions,
            validation_issues=issues,
            broker_id=1,
            asset_id=100,
            type="SELL",
            date=date(2024, 3, 10),
            quantity=Decimal("5"),  # Should be negative for SELL
            cash=Currency(code="EUR", amount=Decimal("-500")),  # Should be positive for SELL
        )
        assert result is None
        assert len(transactions) == 0
        assert len(issues) == 2  # qtyNegative + cashSignPositive
        codes = {i.code for i in issues}
        assert "qtyNegative" in codes
        assert "cashSignPositive" in codes
        # W-B38: each issue's message is what the user reads on import, rendered like a single violation's.
        unreadable = [i.message for i in issues if "{" in i.message or "SELL" not in i.message]
        assert unreadable == [], f"Each import issue's message must be rendered and name the type SELL (W-B38): the user would read {unreadable}"

    def test_context_preserved_in_issues(self, provider):
        """Context string is stored in each validation issue."""
        transactions = []
        issues = []
        provider._create_transaction(
            row_num=1,
            transactions=transactions,
            validation_issues=issues,
            context="FEE: Annual custody fee",
            broker_id=1,
            type="FEE",
            date=date(2024, 1, 1),
            quantity=Decimal("0"),
            cash=Currency(code="EUR", amount=Decimal("100")),  # Wrong sign: FEE needs negative
        )
        assert len(issues) >= 1
        for issue in issues:
            assert issue.context == "FEE: Annual custody fee"

    def test_fee_transaction_valid(self, provider):
        """Fee transaction with correct sign → success."""
        transactions = []
        issues = []
        result = provider._create_transaction(
            row_num=99,
            transactions=transactions,
            validation_issues=issues,
            broker_id=1,
            type="FEE",
            date=date(2024, 1, 1),
            quantity=Decimal("0"),
            cash=Currency(code="USD", amount=Decimal("-25.50")),
            description="Trading fee",
            tags=["import", "fee"],
        )
        assert result is not None
        assert len(transactions) == 1
        assert len(issues) == 0

    def test_issue_params_contain_type(self, provider):
        """Validation issue params should contain the transaction type."""
        transactions = []
        issues = []
        provider._create_transaction(
            row_num=1,
            transactions=transactions,
            validation_issues=issues,
            broker_id=1,
            asset_id=100,
            type="INTEREST",
            date=date(2024, 1, 1),
            quantity=Decimal("0"),
            cash=Currency(code="EUR", amount=Decimal("-10")),  # Wrong sign
        )
        assert len(issues) >= 1
        # The params should have 'type' from Pydantic's ctx
        cash_sign_issues = [i for i in issues if i.code == "cashSignPositive"]
        assert len(cash_sign_issues) == 1
        assert cash_sign_issues[0].params is not None
        assert cash_sign_issues[0].params.get("type") == "INTEREST"


class TestLocToField:
    """Tests for BRIMProvider._loc_to_field() static method."""

    def test_simple_field(self):
        assert BRIMProvider._loc_to_field(("cash", "amount")) == "cash.amount"

    def test_with_indices(self):
        assert BRIMProvider._loc_to_field(("body", 0, "cash", "amount")) == "body.cash.amount"

    def test_empty_tuple(self):
        assert BRIMProvider._loc_to_field(()) is None

    def test_single_field(self):
        assert BRIMProvider._loc_to_field(("type",)) == "type"


class TestBRIMValidationIssueSchema:
    """Tests for BRIMValidationIssue Pydantic schema."""

    def test_minimal(self):
        issue = BRIMValidationIssue(row=1, code="cashRequired", message="Cash is required")
        assert issue.row == 1
        assert issue.code == "cashRequired"
        assert issue.field is None
        assert issue.params is None
        assert issue.context is None

    def test_full(self):
        issue = BRIMValidationIssue(
            row=13,
            code="cashSignPositive",
            message="DIVIDEND requires cash.amount > 0",
            field="cash.amount",
            params={"type": "DIVIDEND"},
            context="DIVIDEND: ACME Corp",
        )
        assert issue.row == 13
        assert issue.field == "cash.amount"
        assert issue.params == {"type": "DIVIDEND"}
        assert issue.context == "DIVIDEND: ACME Corp"

    def test_serialization(self):
        issue = BRIMValidationIssue(
            row=5,
            code="qtyNegative",
            message="SELL requires quantity < 0",
            field="quantity",
            params={"type": "SELL"},
        )
        data = issue.model_dump()
        assert data["row"] == 5
        assert data["code"] == "qtyNegative"
        assert data["field"] == "quantity"
        assert data["params"] == {"type": "SELL"}
        # Roundtrip
        issue2 = BRIMValidationIssue.model_validate(data)
        assert issue2 == issue


# =============================================================================
# W-B75: the params of a refused transaction's issue (written by H, for W)
# =============================================================================

# A model-level error's context made only of plain data: str, int, float, bool and None.
_PLAIN_CONTEXT = {"type": "BUY", "qty": "1.5", "count": 2, "ratio": 0.5, "flag": True, "none": None}


def _buy_kwargs(**overrides) -> dict:
    """The kwargs of a valid BUY for ``TXCreateItem``, with ``overrides`` applied: each case changes only what it is about."""
    kwargs = {"broker_id": 1, "asset_id": 100, "type": "BUY", "date": date(2024, 1, 15), "quantity": Decimal("10"), "cash": Currency(code="EUR", amount=Decimal("-1000"))}
    kwargs.update(overrides)
    return kwargs


def _pydantic_errors(kwargs: dict) -> list:
    """The errors pydantic itself reports for ``TXCreateItem(**kwargs)``: the premise a case checks before it reads the issue."""
    with pytest.raises(ValidationError) as exc_info:
        TXCreateItem(**kwargs)
    return exc_info.value.errors()


def _json_or_fail(what: str, dump) -> dict:
    """``dump()``. A ``PydanticSerializationError`` is W-B75's red, reported as what the user meets rather than as a crash."""
    try:
        return dump()
    except PydanticSerializationError as exc:
        failure = str(exc)
    pytest.fail(
        f"W-B75: {what} raises PydanticSerializationError ({failure}). The issue's params hold pydantic's context of a value_error, the ValueError object itself, "
        "and the parse route saves its response with model_dump(mode='json'): today the user's parse fails with a 400 carrying that serializer message "
        "(the route's `except ValueError` catches it) instead of listing the row's issue."
    )


def _serialized_issue(issue: BRIMValidationIssue) -> dict:
    """``issue`` through every JSON path of the parse, which must agree: the issue alone (``model_dump(mode="json")``,
    ``model_dump_json()``), inside the plugin's ``BRIMParseOutput`` and inside the route's ``BRIMParseResponse``."""
    alone = _json_or_fail("BRIMValidationIssue.model_dump(mode='json')", lambda: issue.model_dump(mode="json"))
    as_json = _json_or_fail("BRIMValidationIssue.model_dump_json()", lambda: json.loads(issue.model_dump_json()))
    in_output = _json_or_fail("BRIMParseOutput.model_dump(mode='json')", lambda: BRIMParseOutput(validation_issues=[issue]).model_dump(mode="json"))
    in_response = _json_or_fail("BRIMParseResponse.model_dump(mode='json')", lambda: BRIMParseResponse(file_id="file-1", plugin_code="test_provider", broker_id=1, validation_issues=[issue]).model_dump(mode="json"))
    assert as_json == alone
    assert in_output["validation_issues"] == [alone]
    assert in_response["validation_issues"] == [alone]
    return alone


def _lone_error_params_or_fail():
    """``BRIMProvider._lone_error_params``; its absence, before the cure, is W-B75's red rather than a collection error."""
    lone_error_params = getattr(BRIMProvider, "_lone_error_params", None)
    if lone_error_params is None:
        pytest.fail("W-B75: BRIMProvider._lone_error_params does not exist yet: the static method, beside _loc_to_field, that gives an error raised alone its params, by the transaction batch's rule (W-B72).")
    return lone_error_params


class TestCreateTransactionIssueParams:
    """W-B75: the ``params`` of the issue a refused transaction becomes, and the parse output carrying it serializing.

    The transaction batch's rule (``_lone_error_params``, W-B72): an error ``TXCreateItem`` raises alone keeps its context
    as ``params`` only when it is model-level (``loc`` empty) and plain data; a field's error is named by its field. A
    packed one (``multipleBusinessRuleErrors``) keeps each rule's context.
    """

    @pytest.fixture
    def provider(self):
        return ConcreteBRIMProvider()

    @pytest.mark.parametrize(
        ("overrides", "field", "validator_message"),
        [
            pytest.param({"cash": {"code": "EUR", "amount": Decimal(f"-1E+{MAX_DECIMAL_EXPONENT + 1}")}}, "cash.amount", f"Value out of range: its exponent must be within ±{MAX_DECIMAL_EXPONENT}", id="cash-amount-exponent"),
            pytest.param({"cash": {"code": "", "amount": Decimal("-1000")}}, "cash.code", "Currency code cannot be empty", id="cash-code-empty"),
            pytest.param({"tags": ("import", "test")}, "tags", "tags must be a list of strings or comma-separated string", id="tags-not-a-list"),
        ],
    )
    def test_value_error_issue_carries_no_params_and_serializes(self, provider, overrides, field, validator_message):
        """Red before the W-B75 cure. A value its validator refuses with a ``ValueError`` (``cash`` handed over as a dict, not a
        ``Currency``, past the exponent bound or with an empty code; tags as a tuple) is pydantic's ``value_error``,
        whose context holds the exception itself. Its issue names the field and carries no params, and the parse output
        holding it serializes: before, the issue carried the exception and the parse failed."""
        kwargs = _buy_kwargs(**overrides)
        errors = _pydantic_errors(kwargs)
        assert [error["type"] for error in errors] == ["value_error"], f"premise: a single value_error; pydantic reports {errors}"
        assert isinstance((errors[0].get("ctx") or {}).get("error"), ValueError), f"premise: the value_error's context holds the exception itself; pydantic reports {errors}"

        transactions = []
        issues = []
        result = provider._create_transaction(row_num=42, transactions=transactions, validation_issues=issues, context="BUY: ACME Corp", **kwargs)

        assert result is None
        assert transactions == []
        assert len(issues) == 1, f"one refused field, one issue: {issues}"
        issue = issues[0]
        assert (issue.row, issue.code, issue.field, issue.context) == (42, "value_error", field, "BUY: ACME Corp")
        assert issue.message == f"Value error, {validator_message}"
        serialized = _serialized_issue(issue)
        assert issue.params is None, f"W-B75: a field's error is named by its field and carries no params; got {issue.params!r}"
        assert serialized == {"row": 42, "code": "value_error", "message": f"Value error, {validator_message}", "field": field, "params": None, "context": "BUY: ACME Corp"}

    def test_field_error_with_plain_context_carries_no_params(self, provider):
        """Red before the W-B75 cure. A field's error is named by its field even when its context is plain data: ``description``
        past its 500 characters is pydantic's ``string_too_long``, context ``{max_length: 500}``; its issue carries no
        params, as the transaction batch's does (W-B72). Before, it carried that context."""
        kwargs = _buy_kwargs(description="x" * 501)
        errors = _pydantic_errors(kwargs)
        assert [(error["type"], error["loc"], error.get("ctx")) for error in errors] == [("string_too_long", ("description",), {"max_length": 500})], f"premise: pydantic reports {errors}"

        transactions = []
        issues = []
        result = provider._create_transaction(row_num=8, transactions=transactions, validation_issues=issues, context="BUY: ACME Corp", **kwargs)

        assert result is None
        assert transactions == []
        assert len(issues) == 1, f"one refused field, one issue: {issues}"
        issue = issues[0]
        assert (issue.row, issue.code, issue.field, issue.message, issue.context) == (8, "string_too_long", "description", errors[0]["msg"], "BUY: ACME Corp")
        assert issue.params is None, f"W-B75: a field's error is named by its field and carries no params, as in the transaction batch; got {issue.params!r}"
        assert _serialized_issue(issue)["params"] is None

    @pytest.mark.parametrize(
        ("overrides", "code", "params"),
        [
            pytest.param({"broker_id": 0}, "brokerRequired", {"broker_id": 0}, id="broker-required"),
            pytest.param({"type": "DEPOSIT", "asset_id": None, "quantity": Decimal("0"), "cash": Currency(code="EUR", amount=Decimal("100")), "cost_basis_mode": "manual"}, "costBasisModeIncompatible", {"type": "DEPOSIT", "qty": "0"}, id="cost-basis-mode-incompatible"),
        ],
    )
    def test_lone_business_rule_keeps_plain_params(self, provider, overrides, code, params):
        """Guard, green before and after W-B75. A single business rule, which ``TXCreateItem`` raises alone rather than
        packed, keeps its plain context as params (an int value; two keys) without a field, and its issue serializes.
        ``test_issue_params_contain_type`` holds the ``{type}`` one."""
        kwargs = _buy_kwargs(**overrides)
        errors = _pydantic_errors(kwargs)
        assert [(error["type"], error["loc"], error.get("ctx")) for error in errors] == [(code, (), params)], f"premise: one model-level rule, raised alone; pydantic reports {errors}"

        transactions = []
        issues = []
        result = provider._create_transaction(row_num=3, transactions=transactions, validation_issues=issues, context="row 3", **kwargs)

        assert result is None
        assert transactions == []
        assert len(issues) == 1, f"one rule, one issue: {issues}"
        issue = issues[0]
        assert (issue.row, issue.code, issue.field, issue.message, issue.context) == (3, code, None, errors[0]["msg"], "row 3")
        assert issue.params == params
        assert _serialized_issue(issue)["params"] == params

    def test_packed_business_rules_keep_their_params(self, provider):
        """Guard, green before and after W-B75. Several rules at once are packed (``multipleBusinessRuleErrors``): each
        becomes an issue keeping its own rule's context as params, an int one included, without a field, and they
        serialize. ``test_multiple_errors_produce_multiple_issues`` holds their codes and messages."""
        kwargs = _buy_kwargs(broker_id=0, cash=Currency(code="EUR", amount=Decimal("1000")))
        errors = _pydantic_errors(kwargs)
        assert [error["type"] for error in errors] == ["multipleBusinessRuleErrors"], f"premise: two rules, packed; pydantic reports {errors}"

        transactions = []
        issues = []
        result = provider._create_transaction(row_num=21, transactions=transactions, validation_issues=issues, context="BUY: ACME Corp", **kwargs)

        assert result is None
        assert transactions == []
        assert len(issues) == 2, f"two rules, two issues: {issues}"
        expected = {"brokerRequired": ({"broker_id": 0}, None, 21, "BUY: ACME Corp"), "cashSignNegative": ({"type": "BUY"}, None, 21, "BUY: ACME Corp")}
        assert {issue.code: (issue.params, issue.field, issue.row, issue.context) for issue in issues} == expected
        assert {issue.code: _serialized_issue(issue)["params"] for issue in issues} == {"brokerRequired": {"broker_id": 0}, "cashSignNegative": {"type": "BUY"}}


class TestLoneErrorParams:
    """W-B75: ``BRIMProvider._lone_error_params`` on synthetic pydantic errors, the twin of the transaction batch's
    (``transaction_batch_stages._lone_error_params``, W-B72). An error's context becomes its params only when the error
    is model-level (``loc`` empty) and every value is plain data: str, int, float, bool or None. Red before the cure."""

    def test_plain_model_level_context_is_copied(self):
        """A model-level error with a plain context: a new dict, equal to it, and the error's own left as it was."""
        lone_error_params = _lone_error_params_or_fail()
        context = dict(_PLAIN_CONTEXT)
        params = lone_error_params({"type": "someRule", "loc": (), "msg": "m", "ctx": context})
        assert isinstance(params, dict)
        assert params == _PLAIN_CONTEXT
        assert params is not context, "a new dict, not pydantic's context itself"
        assert context == _PLAIN_CONTEXT, "the error's context is left as it was"

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(ValueError("Value out of range"), id="exception"),
            pytest.param(Decimal("1.5"), id="decimal"),
            pytest.param(date(2024, 1, 15), id="date"),
            pytest.param(["BUY", "SELL"], id="list"),
            pytest.param({"type": "BUY"}, id="dict"),
        ],
    )
    def test_one_value_not_plain_gives_none(self, value):
        """One value that is not plain data, among plain ones, and the whole context stays out: ``None``."""
        lone_error_params = _lone_error_params_or_fail()
        assert lone_error_params({"type": "someRule", "loc": (), "msg": "m", "ctx": {**_PLAIN_CONTEXT, "extra": value}}) is None

    @pytest.mark.parametrize("loc", [pytest.param(("description",), id="field"), pytest.param(("cash", "amount"), id="nested-field")])
    def test_field_error_gives_none(self, loc):
        """A field's error is named by its field, even with a plain context: ``None``."""
        lone_error_params = _lone_error_params_or_fail()
        assert lone_error_params({"type": "string_too_long", "loc": loc, "msg": "m", "ctx": dict(_PLAIN_CONTEXT)}) is None

    @pytest.mark.parametrize(
        "error",
        [
            pytest.param({"type": "someRule", "loc": (), "msg": "m"}, id="ctx-missing"),
            pytest.param({"type": "someRule", "loc": (), "msg": "m", "ctx": None}, id="ctx-none"),
            pytest.param({"type": "someRule", "loc": (), "msg": "m", "ctx": {}}, id="ctx-empty"),
        ],
    )
    def test_no_context_gives_none(self, error):
        """No context, or an empty one: ``None``, never an empty dict."""
        lone_error_params = _lone_error_params_or_fail()
        assert lone_error_params(error) is None
