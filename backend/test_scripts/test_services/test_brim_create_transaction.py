"""
Tests for BRIMProvider._create_transaction() helper method.

Covers:
  - Valid transaction → appended to transactions list
  - Invalid transaction (validation error) → structured BRIMValidationIssue
  - Multiple validation errors → multiple issues appended
  - Context parameter preservation
  - Fee transaction pattern (same helper, different kwargs)
"""

from datetime import date
from decimal import Decimal

import pytest

from backend.app.schemas.brim import BRIMParseOutput, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMProvider


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
