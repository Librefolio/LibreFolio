"""
Tests for Transaction Pydantic schemas.

Tests TXCreateItem, TXReadItem, TXUpdateItem validation rules.
See checklist: 01_test_broker_transaction_subsystem.md - Category 1

Reference: backend/app/schemas/transactions.py
"""
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.db.models import TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem, tags_to_csv, validate_tags_list


# ============================================================================
# 1.1 LINK UUID REQUIREMENTS
# ============================================================================

class TestLinkUuidRequirements:
    """Test link_uuid requirements for TRANSFER and FX_CONVERSION."""

    def test_transfer_requires_link_uuid(self):
        """TX-S-001: TRANSFER without link_uuid should fail."""
        with pytest.raises(ValidationError, match="TRANSFER requires link_uuid"):
            TXCreateItem(
                broker_id=1,
                asset_id=1,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("10"),
                )

    def test_fx_conversion_requires_link_uuid(self):
        """TX-S-002: FX_CONVERSION without link_uuid should fail."""
        with pytest.raises(ValidationError, match="FX_CONVERSION requires link_uuid"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.FX_CONVERSION,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                )

    def test_transfer_with_link_uuid_valid(self):
        """TX-S-003: TRANSFER with link_uuid should pass."""
        tx = TXCreateItem(
            broker_id=1,
            asset_id=1,
            type=TransactionType.TRANSFER,
            date=date.today(),
            quantity=Decimal("10"),
            link_uuid="550e8400-e29b-41d4-a716-446655440000",
            )
        assert tx.link_uuid == "550e8400-e29b-41d4-a716-446655440000"

    def test_fx_conversion_with_link_uuid_valid(self):
        """TX-S-004: FX_CONVERSION with link_uuid should pass."""
        tx = TXCreateItem(
            broker_id=1,
            type=TransactionType.FX_CONVERSION,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("100")),
            link_uuid="550e8400-e29b-41d4-a716-446655440000",
            )
        assert tx.link_uuid == "550e8400-e29b-41d4-a716-446655440000"


# ============================================================================
# 1.2 TRANSFER SPECIFIC RULES
# ============================================================================

class TestTransferRules:
    """Test TRANSFER-specific validation rules."""

    def test_transfer_requires_asset_id(self):
        """TX-S-010: TRANSFER without asset_id should fail."""
        with pytest.raises(ValidationError, match="TRANSFER requires asset_id"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("10"),
                link_uuid="uuid-123",
                )

    def test_transfer_requires_nonzero_quantity(self):
        """TX-S-011: TRANSFER with quantity=0 should fail."""
        with pytest.raises(ValidationError, match="TRANSFER requires quantity != 0"):
            TXCreateItem(
                broker_id=1,
                asset_id=1,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("0"),
                link_uuid="uuid-123",
                )

    def test_transfer_no_cash_allowed(self):
        """TX-S-012: TRANSFER with cash movement should fail."""
        with pytest.raises(ValidationError, match="TRANSFER should not have cash movement"):
            TXCreateItem(
                broker_id=1,
                asset_id=1,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("100")),
                link_uuid="uuid-123",
                )

    def test_transfer_valid(self):
        """TX-S-013: Valid TRANSFER should pass."""
        tx = TXCreateItem(
            broker_id=1,
            asset_id=1,
            type=TransactionType.TRANSFER,
            date=date.today(),
            quantity=Decimal("-10"),  # Negative = outgoing
            link_uuid="uuid-123",
            )
        assert tx.type == TransactionType.TRANSFER
        assert tx.quantity == Decimal("-10")
        assert tx.cash is None


# ============================================================================
# 1.3 FX_CONVERSION SPECIFIC RULES
# ============================================================================

class TestFxConversionRules:
    """Test FX_CONVERSION-specific validation rules."""

    def test_fx_no_asset_allowed(self):
        """TX-S-020: FX_CONVERSION with asset_id should fail."""
        with pytest.raises(ValidationError, match="FX_CONVERSION should not have asset_id"):
            TXCreateItem(
                broker_id=1,
                asset_id=1,
                type=TransactionType.FX_CONVERSION,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                link_uuid="uuid-123",
                )

    def test_fx_requires_zero_quantity(self):
        """TX-S-021: FX_CONVERSION with quantity!=0 should fail."""
        with pytest.raises(ValidationError, match="FX_CONVERSION should have quantity = 0"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.FX_CONVERSION,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("100")),
                link_uuid="uuid-123",
                )

    def test_fx_requires_cash(self):
        """TX-S-022: FX_CONVERSION without cash should fail."""
        with pytest.raises(ValidationError, match="FX_CONVERSION requires cash with amount != 0"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.FX_CONVERSION,
                date=date.today(),
                link_uuid="uuid-123",
                )

    def test_fx_cash_zero_not_allowed(self):
        """TX-S-023: FX_CONVERSION with cash.amount=0 should fail."""
        with pytest.raises(ValidationError, match="FX_CONVERSION requires cash with amount != 0"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.FX_CONVERSION,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("0")),
                link_uuid="uuid-123",
                )

    def test_fx_valid(self):
        """TX-S-024: Valid FX_CONVERSION should pass."""
        tx = TXCreateItem(
            broker_id=1,
            type=TransactionType.FX_CONVERSION,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("-100")),  # Negative = outgoing
            link_uuid="uuid-123",
            )
        assert tx.type == TransactionType.FX_CONVERSION
        assert tx.cash.amount == Decimal("-100")


# ============================================================================
# 1.4 DEPOSIT/WITHDRAWAL RULES
# ============================================================================

class TestDepositWithdrawalRules:
    """Test DEPOSIT/WITHDRAWAL validation rules."""

    def test_deposit_no_asset_allowed(self):
        """TX-S-030: DEPOSIT with asset_id should fail."""
        with pytest.raises(ValidationError, match="DEPOSIT should not have asset_id"):
            TXCreateItem(
                broker_id=1,
                asset_id=1,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("1000")),
                )

    def test_withdrawal_no_asset_allowed(self):
        """TX-S-031: WITHDRAWAL with asset_id should fail."""
        with pytest.raises(ValidationError, match="WITHDRAWAL should not have asset_id"):
            TXCreateItem(
                broker_id=1,
                asset_id=1,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-1000")),
                )

    def test_deposit_requires_cash(self):
        """TX-S-032: DEPOSIT without cash should fail."""
        with pytest.raises(ValidationError, match="DEPOSIT requires cash"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                )

    def test_withdrawal_requires_cash(self):
        """TX-S-033: WITHDRAWAL without cash should fail."""
        with pytest.raises(ValidationError, match="WITHDRAWAL requires cash"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                )

    def test_deposit_valid(self):
        """TX-S-034: Valid DEPOSIT should pass."""
        tx = TXCreateItem(
            broker_id=1,
            type=TransactionType.DEPOSIT,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("5000")),
            )
        assert tx.type == TransactionType.DEPOSIT
        assert tx.cash.amount == Decimal("5000")

    def test_withdrawal_valid(self):
        """TX-S-035: Valid WITHDRAWAL should pass."""
        tx = TXCreateItem(
            broker_id=1,
            type=TransactionType.WITHDRAWAL,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("-2000")),
            )
        assert tx.type == TransactionType.WITHDRAWAL
        assert tx.cash.amount == Decimal("-2000")


# ============================================================================
# 1.5 ASSET REQUIRED TYPES
# ============================================================================

class TestAssetRequiredTypes:
    """Test types that require asset_id."""

    def test_buy_requires_asset(self):
        """TX-S-040: BUY without asset_id should fail."""
        with pytest.raises(ValidationError, match="BUY requires asset_id"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("-500")),
                )

    def test_sell_requires_asset(self):
        """TX-S-041: SELL without asset_id should fail."""
        with pytest.raises(ValidationError, match="SELL requires asset_id"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.SELL,
                date=date.today(),
                quantity=Decimal("-10"),
                cash=Currency(code="EUR", amount=Decimal("500")),
                )

    def test_dividend_requires_asset(self):
        """TX-S-042: DIVIDEND without asset_id should fail."""
        with pytest.raises(ValidationError, match="DIVIDEND requires asset_id"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.DIVIDEND,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("50")),
                )

    def test_adjustment_requires_asset(self):
        """TX-S-043: ADJUSTMENT without asset_id should fail."""
        with pytest.raises(ValidationError, match="ADJUSTMENT requires asset_id"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.ADJUSTMENT,
                date=date.today(),
                quantity=Decimal("5"),
                )

    def test_buy_valid(self):
        """TX-S-044: Valid BUY should pass."""
        tx = TXCreateItem(
            broker_id=1,
            asset_id=1,
            type=TransactionType.BUY,
            date=date.today(),
            quantity=Decimal("10"),
            cash=Currency(code="EUR", amount=Decimal("-500")),
            )
        assert tx.type == TransactionType.BUY
        assert tx.asset_id == 1

    def test_sell_valid(self):
        """TX-S-045: Valid SELL should pass."""
        tx = TXCreateItem(
            broker_id=1,
            asset_id=1,
            type=TransactionType.SELL,
            date=date.today(),
            quantity=Decimal("-10"),
            cash=Currency(code="EUR", amount=Decimal("500")),
            )
        assert tx.type == TransactionType.SELL


# ============================================================================
# 1.6 CASH REQUIRED TYPES
# ============================================================================

class TestCashRequiredTypes:
    """Test types that require cash."""

    def test_buy_requires_cash(self):
        """TX-S-050: BUY without cash should fail."""
        with pytest.raises(ValidationError, match="BUY requires cash"):
            TXCreateItem(
                broker_id=1,
                asset_id=1,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("10"),
                )

    def test_sell_requires_cash(self):
        """TX-S-051: SELL without cash should fail."""
        with pytest.raises(ValidationError, match="SELL requires cash"):
            TXCreateItem(
                broker_id=1,
                asset_id=1,
                type=TransactionType.SELL,
                date=date.today(),
                quantity=Decimal("-10"),
                )

    def test_dividend_requires_cash(self):
        """TX-S-052: DIVIDEND without cash should fail."""
        with pytest.raises(ValidationError, match="DIVIDEND requires cash"):
            TXCreateItem(
                broker_id=1,
                asset_id=1,
                type=TransactionType.DIVIDEND,
                date=date.today(),
                )

    def test_interest_requires_cash(self):
        """TX-S-053: INTEREST without cash should fail."""
        with pytest.raises(ValidationError, match="INTEREST requires cash"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.INTEREST,
                date=date.today(),
                )

    def test_fee_requires_cash(self):
        """TX-S-054: FEE without cash should fail."""
        with pytest.raises(ValidationError, match="FEE requires cash"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.FEE,
                date=date.today(),
                )

    def test_tax_requires_cash(self):
        """TX-S-055: TAX without cash should fail."""
        with pytest.raises(ValidationError, match="TAX requires cash"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.TAX,
                date=date.today(),
                )


# ============================================================================
# 1.7 ASSET OPTIONAL TYPES
# ============================================================================

class TestAssetOptionalTypes:
    """Test types where asset is optional (INTEREST, FEE, TAX)."""

    def test_interest_with_asset_valid(self):
        """TX-S-060: INTEREST with asset_id (bond interest) should pass."""
        tx = TXCreateItem(
            broker_id=1,
            asset_id=1,  # Bond asset
            type=TransactionType.INTEREST,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("50")),
            )
        assert tx.asset_id == 1

    def test_interest_without_asset_valid(self):
        """TX-S-061: INTEREST without asset_id (deposit interest) should pass."""
        tx = TXCreateItem(
            broker_id=1,
            type=TransactionType.INTEREST,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("10")),
            )
        assert tx.asset_id is None

    def test_fee_with_asset_valid(self):
        """TX-S-062: FEE with asset_id (trading commission) should pass."""
        tx = TXCreateItem(
            broker_id=1,
            asset_id=1,
            type=TransactionType.FEE,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("-5")),
            )
        assert tx.asset_id == 1

    def test_fee_without_asset_valid(self):
        """TX-S-063: FEE without asset_id (annual fee) should pass."""
        tx = TXCreateItem(
            broker_id=1,
            type=TransactionType.FEE,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("-20")),
            )
        assert tx.asset_id is None

    def test_tax_with_asset_valid(self):
        """TX-S-064: TAX with asset_id (capital gain tax) should pass."""
        tx = TXCreateItem(
            broker_id=1,
            asset_id=1,
            type=TransactionType.TAX,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("-100")),
            )
        assert tx.asset_id == 1

    def test_tax_without_asset_valid(self):
        """TX-S-065: TAX without asset_id (stamp duty) should pass."""
        tx = TXCreateItem(
            broker_id=1,
            type=TransactionType.TAX,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("-50")),
            )
        assert tx.asset_id is None


# ============================================================================
# 1.8 ADJUSTMENT RULES
# ============================================================================

class TestAdjustmentRules:
    """Test ADJUSTMENT-specific validation rules."""

    def test_adjustment_no_cash_allowed(self):
        """TX-S-070: ADJUSTMENT with cash should fail."""
        with pytest.raises(ValidationError, match="ADJUSTMENT should not have cash movement"):
            TXCreateItem(
                broker_id=1,
                asset_id=1,
                type=TransactionType.ADJUSTMENT,
                date=date.today(),
                quantity=Decimal("5"),
                cash=Currency(code="EUR", amount=Decimal("100")),
                )

    def test_adjustment_valid(self):
        """TX-S-071: Valid ADJUSTMENT should pass."""
        tx = TXCreateItem(
            broker_id=1,
            asset_id=1,
            type=TransactionType.ADJUSTMENT,
            date=date.today(),
            quantity=Decimal("5"),
            )
        assert tx.type == TransactionType.ADJUSTMENT
        assert tx.quantity == Decimal("5")
        assert tx.cash is None


# ============================================================================
# 1.9 HELPER METHODS
# ============================================================================

class TestHelperMethods:
    """Test TXCreateItem helper methods."""

    def test_get_amount_with_cash(self):
        """TX-S-080: get_amount() with cash should return cash.amount."""
        tx = TXCreateItem(
            broker_id=1,
            type=TransactionType.DEPOSIT,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("1234.56")),
            )
        assert tx.get_amount() == Decimal("1234.56")

    def test_get_amount_without_cash(self):
        """TX-S-081: get_amount() without cash should return 0."""
        tx = TXCreateItem(
            broker_id=1,
            asset_id=1,
            type=TransactionType.ADJUSTMENT,
            date=date.today(),
            quantity=Decimal("10"),
            )
        assert tx.get_amount() == Decimal("0")

    def test_get_currency_with_cash(self):
        """TX-S-082: get_currency() with cash should return cash.code."""
        tx = TXCreateItem(
            broker_id=1,
            type=TransactionType.DEPOSIT,
            date=date.today(),
            cash=Currency(code="USD", amount=Decimal("100")),
            )
        assert tx.get_currency() == "USD"

    def test_get_currency_without_cash(self):
        """TX-S-083: get_currency() without cash should return None."""
        tx = TXCreateItem(
            broker_id=1,
            asset_id=1,
            type=TransactionType.ADJUSTMENT,
            date=date.today(),
            quantity=Decimal("10"),
            )
        assert tx.get_currency() is None

    def test_get_tags_csv(self):
        """TX-S-084: get_tags_csv() should convert list to CSV."""
        tx = TXCreateItem(
            broker_id=1,
            type=TransactionType.DEPOSIT,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("100")),
            tags=["income", "salary", "monthly"],
            )
        assert tx.get_tags_csv() == "income,salary,monthly"

    def test_get_tags_csv_none(self):
        """get_tags_csv() with no tags should return None."""
        tx = TXCreateItem(
            broker_id=1,
            type=TransactionType.DEPOSIT,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("100")),
            )
        assert tx.get_tags_csv() is None


# ============================================================================
# TAGS UTILITY FUNCTIONS
# ============================================================================

class TestTagsUtilities:
    """Test tags utility functions."""

    def test_validate_tags_list_from_list(self):
        """validate_tags_list with list input."""
        result = validate_tags_list(["tag1", "tag2", "tag3"])
        assert result == ["tag1", "tag2", "tag3"]

    def test_validate_tags_list_from_csv(self):
        """validate_tags_list with CSV string input."""
        result = validate_tags_list("tag1, tag2, tag3")
        assert result == ["tag1", "tag2", "tag3"]

    def test_validate_tags_list_empty(self):
        """validate_tags_list with empty list."""
        result = validate_tags_list([])
        assert result is None

    def test_validate_tags_list_none(self):
        """validate_tags_list with None."""
        result = validate_tags_list(None)
        assert result is None

    def test_tags_to_csv(self):
        """tags_to_csv converts list to CSV."""
        result = tags_to_csv(["a", "b", "c"])
        assert result == "a,b,c"

    def test_tags_to_csv_empty(self):
        """tags_to_csv with empty list returns None."""
        result = tags_to_csv([])
        assert result is None

    def test_tags_to_csv_none(self):
        """tags_to_csv with None returns None."""
        result = tags_to_csv(None)
        assert result is None
