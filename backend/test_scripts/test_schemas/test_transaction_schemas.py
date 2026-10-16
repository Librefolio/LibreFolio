"""
Tests for Transaction Pydantic schemas.

Tests TXCreateItem, TXReadItem, TXUpdateItem validation rules.
See checklist: 01_test_broker_transaction_subsystem.md - Category 1

Reference: backend/app/schemas/transactions/transactions.py
"""

from datetime import date
from decimal import Decimal
from itertools import product
from typing import Optional

import pytest
from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from backend.app.db.models import TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.batch import TXPromoteBatchItem, TXSplitBatchItem
from backend.app.schemas.transactions.transactions import TXCreateItem, TXUpdateItem, tags_to_csv, validate_tags_list, validate_transaction_business_rules
from backend.app.schemas.transactions.type_metadata import TX_TYPE_METADATA

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
        with pytest.raises(ValidationError, match="assetRequired|multipleBusinessRuleErrors"):
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
        with pytest.raises(ValidationError, match="fxConversionCashRequired|multipleBusinessRuleErrors"):
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

    @pytest.mark.parametrize(
        "transaction_type",
        [TransactionType.DIVIDEND, TransactionType.INTEREST],
    )
    def test_income_zero_cash_valid(self, transaction_type):
        """TX-S-056: Zero cash stays valid for retained YOC `net_zero` semantics."""
        tx = TXCreateItem(
            broker_id=1,
            asset_id=1,
            type=transaction_type,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("0")),
        )
        assert tx.cash.amount == Decimal("0")


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


# ============================================================================
# 1.9 ASSET EVENT LINK (Phase 7 Part 1)
# ============================================================================


class TestAssetEventLink:
    """Validation of asset_event_id field on TXCreateItem / TXUpdateItem + metadata."""

    def test_asset_event_id_on_dividend_ok(self):
        """DIVIDEND accepts asset_event_id."""
        tx = TXCreateItem(
            broker_id=1,
            asset_id=10,
            type=TransactionType.DIVIDEND,
            date=date.today(),
            cash=Currency(code="USD", amount=Decimal("1.25")),
            asset_event_id=42,
        )
        assert tx.asset_event_id == 42

    def test_asset_event_id_on_buy_rejected(self):
        """BUY is not event_compatible → asset_event_id must be rejected."""
        with pytest.raises(ValidationError, match="cannot be linked to an asset_event"):
            TXCreateItem(
                broker_id=1,
                asset_id=10,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("1"),
                cash=Currency(code="USD", amount=Decimal("-100")),
                asset_event_id=42,
            )

    def test_asset_event_id_without_asset_id_rejected(self):
        """asset_event_id requires asset_id even for event-compatible types."""
        # INTEREST has asset_mode=OPTIONAL, so the only way asset_id is missing
        # is when caller explicitly omits it.
        with pytest.raises(ValidationError, match="asset_event_id requires asset_id"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.INTEREST,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("5")),
                asset_event_id=42,
            )

    def test_tx_read_item_roundtrip_with_asset_event_id(self):
        """TXReadItem.from_db_model propagates asset_event_id."""
        from backend.app.db.models import Transaction  # noqa: PLC0415
        from backend.app.schemas.transactions.transactions import TXReadItem  # noqa: PLC0415
        from backend.app.utils.datetime_utils import utcnow  # noqa: PLC0415

        tx = Transaction(
            id=1,
            broker_id=1,
            asset_id=10,
            type=TransactionType.DIVIDEND,
            date=date.today(),
            quantity=Decimal("0"),
            amount=Decimal("1.25"),
            currency="USD",
            asset_event_id=42,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        read = TXReadItem.from_db_model(tx)
        assert read.asset_event_id == 42

    def test_tx_update_sentinel_zero_unlinks(self):
        """TXUpdateItem accepts asset_event_id=0 as unlink sentinel."""
        from backend.app.schemas.transactions.transactions import TXUpdateItem  # noqa: PLC0415

        upd = TXUpdateItem(id=1, asset_event_id=0)
        assert upd.asset_event_id == 0
        # None = no change
        upd_none = TXUpdateItem(id=1)
        assert upd_none.asset_event_id is None
        # Positive value = relink
        upd_relink = TXUpdateItem(id=1, asset_event_id=99)
        assert upd_relink.asset_event_id == 99

    def test_tx_type_metadata_event_compatible_flags(self):
        """Only DIVIDEND, INTEREST, ADJUSTMENT are event_compatible in TX_TYPE_METADATA, and rule 9's ``allowed`` names exactly them.

        Reads only names that outlived W-B36, which removed ``EVENT_COMPATIBLE_TYPES`` (rule 9 and ``event_suggestions.py``
        read the table instead): the table's flags, and the ``allowed`` param of eventTypeIncompatible on a DEPOSIT linked
        to an asset event, the list the user is shown.
        """
        expected_true = {TransactionType.DIVIDEND, TransactionType.INTEREST, TransactionType.ADJUSTMENT}
        assert set(TX_TYPE_METADATA) == set(TransactionType), "TX_TYPE_METADATA must have exactly one entry per TransactionType"

        true_in_meta = {t for t, m in TX_TYPE_METADATA.items() if m.event_compatible}
        assert true_in_meta == expected_true

        errors = validate_transaction_business_rules(
            tx_type=TransactionType.DEPOSIT,
            asset_id=None,
            quantity=Decimal("0"),
            cash=Currency(code="EUR", amount=Decimal("100")),
            asset_event_id=1,
            cost_basis_mode=None,
        )
        refusals = [(error.type, error.context) for error in errors if error.type == "eventTypeIncompatible"]
        assert refusals == [("eventTypeIncompatible", {"type": "DEPOSIT", "allowed": "ADJUSTMENT, DIVIDEND, INTEREST"})], f"Rule 9 must refuse a DEPOSIT linked to an asset event once, its allowed naming exactly the event-compatible types; got {refusals}"


# ============================================================================
# STRUCTURED ERROR CODES — verify PydanticCustomError codes propagate to
# ValidationError detail so frontend can extract code + params for i18n.
# ============================================================================


class TestStructuredErrorCodes:
    """Verify PydanticCustomError codes appear in ValidationError.errors()."""

    @staticmethod
    def _get_first_error(create_kwargs: dict) -> dict:
        """Try to create a TXCreateItem and return the first validation error dict."""
        with pytest.raises(ValidationError) as exc_info:
            TXCreateItem(**create_kwargs)
        errors = exc_info.value.errors()
        assert len(errors) >= 1
        return errors[0]

    def test_asset_required_code(self):
        """BUY without asset_id → code='assetRequired', ctx has type='BUY'."""
        err = self._get_first_error(
            {
                "broker_id": 1,
                "type": TransactionType.BUY,
                "date": date.today(),
                "quantity": Decimal("5"),
                "cash": Currency(code="USD", amount=Decimal("-100")),
            }
        )
        assert err["type"] == "assetRequired"
        assert err["ctx"]["type"] == "BUY"

    def test_qty_positive_code(self):
        """BUY with quantity=0 → code='qtyPositive'."""
        err = self._get_first_error(
            {
                "broker_id": 1,
                "asset_id": 1,
                "type": TransactionType.BUY,
                "date": date.today(),
                "quantity": Decimal("0"),
                "cash": Currency(code="USD", amount=Decimal("-50")),
            }
        )
        assert err["type"] == "qtyPositive"
        assert err["ctx"]["type"] == "BUY"

    def test_cash_sign_negative_code(self):
        """BUY with positive cash → code='cashSignNegative'."""
        err = self._get_first_error(
            {
                "broker_id": 1,
                "asset_id": 1,
                "type": TransactionType.BUY,
                "date": date.today(),
                "quantity": Decimal("5"),
                "cash": Currency(code="USD", amount=Decimal("100")),
            }
        )
        assert err["type"] == "cashSignNegative"
        assert err["ctx"]["type"] == "BUY"

    def test_cash_forbidden_code(self):
        """ADJUSTMENT with cash → code='cashForbidden'."""
        err = self._get_first_error(
            {
                "broker_id": 1,
                "asset_id": 1,
                "type": TransactionType.ADJUSTMENT,
                "date": date.today(),
                "quantity": Decimal("5"),
                "cash": Currency(code="USD", amount=Decimal("100")),
            }
        )
        assert err["type"] == "cashForbidden"

    def test_event_type_incompatible_code(self):
        """BUY with asset_event_id → code='eventTypeIncompatible', ctx has allowed."""
        err = self._get_first_error(
            {
                "broker_id": 1,
                "asset_id": 1,
                "type": TransactionType.BUY,
                "date": date.today(),
                "quantity": Decimal("5"),
                "cash": Currency(code="USD", amount=Decimal("-100")),
                "asset_event_id": 99,
            }
        )
        assert err["type"] == "eventTypeIncompatible"
        assert "allowed" in err["ctx"]

    def test_qty_zero_code(self):
        """DIVIDEND with quantity != 0 → code='qtyZero'."""
        err = self._get_first_error(
            {
                "broker_id": 1,
                "asset_id": 1,
                "type": TransactionType.DIVIDEND,
                "date": date.today(),
                "quantity": Decimal("5"),
                "cash": Currency(code="USD", amount=Decimal("100")),
            }
        )
        assert err["type"] == "qtyZero"
        assert err["ctx"]["type"] == "DIVIDEND"

    def test_link_uuid_required_code(self):
        """TRANSFER without link_uuid → code='linkUuidRequired'."""
        err = self._get_first_error(
            {
                "broker_id": 1,
                "asset_id": 1,
                "type": TransactionType.TRANSFER,
                "date": date.today(),
                "quantity": Decimal("5"),
            }
        )
        assert err["type"] == "linkUuidRequired"


# ============================================================================
# UPDATE / SPLIT / PROMOTE BATCH ITEMS
# ============================================================================


class TestTXUpdateItemValidation:
    """Direct branch coverage for TXUpdateItem validator."""

    def test_update_item_id_must_be_positive(self):
        with pytest.raises(ValidationError, match="Transaction id must be > 0"):
            TXUpdateItem(id=0)


class TestTXSplitBatchItem:
    """Direct branch coverage for split batch validator."""

    def test_ids_must_differ(self):
        with pytest.raises(ValidationError, match="id_a and id_b must be different transactions"):
            TXSplitBatchItem(id_a=1, id_b=1)

    def test_valid_distinct_ids(self):
        item = TXSplitBatchItem(id_a=1, id_b=2)
        assert item.id_a == 1
        assert item.id_b == 2


class TestTXPromoteBatchItem:
    """Direct branch coverage for promote reference validator."""

    def test_valid_mixed_refs(self):
        item = TXPromoteBatchItem(link_uuid_a="create-a", id_b=2)
        assert item.link_uuid_a == "create-a"
        assert item.id_b == 2

    def test_missing_ref_for_tx_a(self):
        with pytest.raises(ValidationError, match="Either id_a or link_uuid_a must be provided for TX A"):
            TXPromoteBatchItem(id_b=2)

    def test_missing_ref_for_tx_b(self):
        with pytest.raises(ValidationError, match="Either id_b or link_uuid_b must be provided for TX B"):
            TXPromoteBatchItem(id_a=1)

    def test_duplicate_ref_for_tx_a(self):
        with pytest.raises(ValidationError, match="Provide either id_a or link_uuid_a for TX A, not both"):
            TXPromoteBatchItem(id_a=1, link_uuid_a="create-a", id_b=2)

    def test_duplicate_ref_for_tx_b(self):
        with pytest.raises(ValidationError, match="Provide either id_b or link_uuid_b for TX B, not both"):
            TXPromoteBatchItem(id_a=1, id_b=2, link_uuid_b="create-b")


# ============================================================================
# 1.10 COST BASIS MODE — RULE 12 READS TX_TYPE_METADATA (W-B31)
# ============================================================================


COST_BASIS_MODE_INCOMPATIBLE = "costBasisModeIncompatible"
RULE12_QUANTITIES = (Decimal("-1"), Decimal("0"), Decimal("1"))


def _metadata_cost_basis_rule(tx_type: TransactionType, quantity: Decimal) -> str:
    """The cost basis rule ``TX_TYPE_METADATA`` gives ``tx_type`` on the side of ``quantity``, read when called.

    The side as ``cost_basis_required()`` picks it: a paired type reads ``cost_basis_pair[1]`` for quantity > 0 (the
    receiving side) and ``cost_basis_pair[0]`` otherwise (the sending side); any other type reads ``cost_basis_mode``.
    (The frontend reads a quantity of 0 as the ``self`` side, ``cost_basis_mode``: on today's table the two agree.)
    """
    entry = TX_TYPE_METADATA[tx_type]
    return entry.cost_basis_pair[1 if quantity > 0 else 0] if entry.cost_basis_pair else entry.cost_basis_mode


def _metadata_admits_cost_basis(tx_type: TransactionType, quantity: Decimal) -> bool:
    """Whether ``TX_TYPE_METADATA`` admits a cost basis for ``tx_type`` with ``quantity``: the frontend's ``cbAllowed``.

    ``txPayloadHelpers.ts`` sends a ``cost_basis_mode`` only when the rule of the side is neither ``forbidden`` nor
    ``required_qty_pos`` with quantity <= 0. Computed here from the table, not imported: the expectation must not take
    the word of the code under test.
    """
    rule = _metadata_cost_basis_rule(tx_type, quantity)
    return rule != "forbidden" and not (rule == "required_qty_pos" and quantity <= 0)


def _rule12_refusals(tx_type: TransactionType, quantity: Decimal, cost_basis_mode: Optional[str]) -> list[PydanticCustomError]:
    """The ``costBasisModeIncompatible`` errors ``validate_transaction_business_rules`` returns for this type, quantity and mode.

    Every other input is neutral (no asset, no cash, no event), so rules 5-11 fire on most types (``assetRequired``,
    ``cashRequired``, the sign rules). They are not the subject: only rule 12's code is kept.
    """
    errors = validate_transaction_business_rules(
        tx_type=tx_type,
        asset_id=None,
        quantity=quantity,
        cash=None,
        asset_event_id=None,
        cost_basis_mode=cost_basis_mode,
    )
    return [error for error in errors if error.type == COST_BASIS_MODE_INCOMPATIBLE]


def _replace_metadata_entry(monkeypatch: pytest.MonkeyPatch, tx_type: TransactionType, **update: object) -> None:
    """Replace ``TX_TYPE_METADATA[tx_type]`` with a copy carrying ``update``, for this test only.

    ``monkeypatch.setitem`` swaps the dict's value and puts the original entry back at teardown; the original object is
    never touched. A rule that reads ``TX_TYPE_METADATA`` when it runs sees the copy; one that never reads it (rule 12
    before W-B31, rules 5-11 before W-B36), or that copied the table at import time, does not.
    """
    monkeypatch.setitem(TX_TYPE_METADATA, tx_type, TX_TYPE_METADATA[tx_type].model_copy(update=update))
    replaced = TX_TYPE_METADATA[tx_type]
    assert all(getattr(replaced, field) == value for field, value in update.items()), f"scaffold: TX_TYPE_METADATA[{tx_type.value}] does not show {update}"


class TestCostBasisModeRule12:
    """Rule 12 of ``validate_transaction_business_rules`` (``costBasisModeIncompatible``) against ``TX_TYPE_METADATA``.

    A ``cost_basis_mode`` belongs only where the metadata admits a cost basis: the rule of the side (``cost_basis_pair``
    for a paired type, ``cost_basis_mode`` otherwise) neither ``forbidden`` nor ``required_qty_pos`` with quantity <= 0,
    the frontend's ``cbAllowed``. Before W-B31 rule 12 was a second copy written by hand (TRANSFER and ADJUSTMENT with
    quantity > 0); since W-B31 it reads the table (``cost_basis_allowed``).

    - TX-S-090, TX-S-091, TX-S-094: guards, green before W-B31 (the copy matched the table) and since.
    - TX-S-092, TX-S-093: red before W-B31, now its guards. An entry of ``TX_TYPE_METADATA`` is replaced for one test and
      rule 12 must follow it; a hand-written copy never reads the table, so it would answer as before.

    Pure: no database, no server. The only module state touched is one ``TX_TYPE_METADATA`` entry, through
    ``monkeypatch``, which puts the original back.
    """

    def test_rule12_follows_metadata_for_every_type_and_side(self):
        """TX-S-090: cost_basis_mode is refused exactly where TX_TYPE_METADATA admits no cost basis, every type × sign.

        Guard: green before W-B31 because the hand-written rule happened to match the table, and since because the rule
        reads it. A rule reading the wrong side of a pair, the mode of a paired type, or ``required_qty_pos`` without its
        quantity sign, turns a cell red. One table, one assertion: a failure shows every wrong cell at once.
        """
        refused: dict[tuple[str, str], bool] = {}
        expected: dict[tuple[str, str], bool] = {}
        rules: dict[tuple[str, str], str] = {}
        for tx_type in TransactionType:
            for quantity in RULE12_QUANTITIES:
                cell = (tx_type.value, str(quantity))
                refused[cell] = bool(_rule12_refusals(tx_type, quantity, "auto"))
                expected[cell] = not _metadata_admits_cost_basis(tx_type, quantity)
                rules[cell] = _metadata_cost_basis_rule(tx_type, quantity)

        wrong = {cell: f"refused={refused[cell]}, metadata rule {rules[cell]!r} says refused={expected[cell]}" for cell in expected if refused[cell] != expected[cell]}
        assert refused == expected, f"Rule 12 must refuse cost_basis_mode='auto' (costBasisModeIncompatible) exactly where TX_TYPE_METADATA admits no cost basis. Wrong cells (type, quantity): {wrong}"

    def test_rule12_silent_without_cost_basis_mode(self):
        """TX-S-091: with cost_basis_mode=None no type and no sign gets costBasisModeIncompatible.

        Guard, green before and since W-B31: the metadata says WHERE a cost_basis_mode may go, never that leaving it out is
        a fault (a missing cost is ``costBasisRequired``, a batch rule, not rule 12).
        """
        refused = [(tx_type.value, str(quantity)) for tx_type in TransactionType for quantity in RULE12_QUANTITIES if _rule12_refusals(tx_type, quantity, None)]

        assert refused == [], f"With cost_basis_mode=None rule 12 has nothing to judge, yet it refused (type, quantity): {refused}"

    def test_rule12_admits_cost_basis_mode_where_metadata_opens_it(self, monkeypatch):
        """TX-S-092: red before W-B31, now its guard. A BUY made ``optional`` in TX_TYPE_METADATA is admitted with a cost_basis_mode.

        Before W-B31 rule 12 never read the table: its hand-written list (TRANSFER and ADJUSTMENT with quantity > 0)
        refused the BUY with costBasisModeIncompatible whatever the metadata said. Red again means rule 12 stopped reading it.
        """
        quantity = Decimal("1")
        _replace_metadata_entry(monkeypatch, TransactionType.BUY, cost_basis_mode="optional")
        assert _metadata_admits_cost_basis(TransactionType.BUY, quantity), "scaffold: the replaced BUY entry does not admit a cost basis, so this test proves nothing about rule 12"

        refusals = _rule12_refusals(TransactionType.BUY, quantity, "auto")

        assert refusals == [], f"W-B31: with TX_TYPE_METADATA[BUY].cost_basis_mode = 'optional', rule 12 must admit cost_basis_mode='auto' on a BUY with quantity {quantity}; it refused it {[error.context for error in refusals]}: rule 12 no longer reads the table"

    def test_rule12_refuses_cost_basis_mode_where_metadata_closes_it(self, monkeypatch):
        """TX-S-093: red before W-B31, now its guard. An ADJUSTMENT made ``forbidden`` in TX_TYPE_METADATA is refused a cost_basis_mode.

        Before W-B31 the hand-written list admitted every ADJUSTMENT with quantity > 0 whatever the metadata said, so no
        costBasisModeIncompatible came back. Red again means rule 12 stopped reading the table.
        """
        quantity = Decimal("1")
        _replace_metadata_entry(monkeypatch, TransactionType.ADJUSTMENT, cost_basis_mode="forbidden")
        assert TX_TYPE_METADATA[TransactionType.ADJUSTMENT].cost_basis_pair is None, "scaffold: ADJUSTMENT has a cost_basis_pair, which overrides the cost_basis_mode this test replaces"
        assert not _metadata_admits_cost_basis(TransactionType.ADJUSTMENT, quantity), "scaffold: the replaced ADJUSTMENT entry still admits a cost basis, so this test proves nothing about rule 12"

        refusals = _rule12_refusals(TransactionType.ADJUSTMENT, quantity, "auto")

        assert refusals, f"W-B31: with TX_TYPE_METADATA[ADJUSTMENT].cost_basis_mode = 'forbidden', rule 12 must refuse cost_basis_mode='auto' on an ADJUSTMENT with quantity {quantity} (costBasisModeIncompatible); it admitted it: rule 12 no longer reads the table"

    def test_rule12_create_path_refuses_cost_basis_mode_on_buy(self):
        """TX-S-094: TXCreateItem refuses a BUY that is valid in every other respect, for its cost_basis_mode alone.

        Guard, green before and since W-B31: the create path hands cost_basis_mode to rule 12, and the refusal kept its
        code and params (``type``, ``qty``); W-B31 changed only the English message.
        """
        with pytest.raises(ValidationError) as exc_info:
            TXCreateItem(
                broker_id=1,
                asset_id=1,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("-500")),
                cost_basis_mode="auto",
            )

        errors = [(error["type"], error.get("ctx")) for error in exc_info.value.errors()]
        assert errors == [(COST_BASIS_MODE_INCOMPATIBLE, {"type": "BUY", "qty": "10"})], f"A BUY with cost_basis_mode='auto' must be refused by rule 12 alone, with code and params unchanged; got {errors}"


# ============================================================================
# 1.11 RULES 5-11 READ TX_TYPE_METADATA (W-B36)
# ============================================================================


CASH_EUR_ZERO = Currency(code="EUR", amount=Decimal("0"))
CASH_EUR_PLUS_100 = Currency(code="EUR", amount=Decimal("100"))
CASH_EUR_MINUS_100 = Currency(code="EUR", amount=Decimal("-100"))

# The cells of TX-S-095: every TransactionType × these asset ids × cashes × quantities × asset_event ids.
PARITY_ASSET_IDS = (None, 1)
PARITY_CASHES = {"none": None, "EUR 0": CASH_EUR_ZERO, "EUR +100": CASH_EUR_PLUS_100, "EUR -100": CASH_EUR_MINUS_100}
PARITY_QUANTITIES = (Decimal("-1"), Decimal("0"), Decimal("1"))
PARITY_EVENT_IDS = (None, 1)

# The codes of each of rules 5-11: a red keeps only those of the rule it is about.
RULE_CODES: dict[int, frozenset[str]] = {
    5: frozenset({"assetRequired"}),
    7: frozenset({"cashRequired"}),
    8: frozenset({"cashForbidden"}),
    9: frozenset({"eventTypeIncompatible", "eventRequiresAsset"}),
    10: frozenset({"qtyPositive", "qtyNegative", "qtyZero", "qtyNonzero"}),
    11: frozenset({"cashSignNegative", "cashSignPositive"}),
}

# Rule 10: the quantity each quantity_sign of TX_TYPE_METADATA refuses, and the code it refuses it with ("free": none).
QUANTITY_SIGN_REFUSALS = {
    "positive": ("qtyPositive", lambda quantity: quantity <= 0),
    "negative": ("qtyNegative", lambda quantity: quantity >= 0),
    "zero": ("qtyZero", lambda quantity: quantity != 0),
    "nonzero": ("qtyNonzero", lambda quantity: quantity == 0),
}

# Rule 11: the amount each cash_sign refuses, and the code, judged on a non-zero cash only: a zero amount is never refused
# by its sign (TX-S-056 keeps a DIVIDEND or INTEREST netting to zero valid). "zero" is rule 8's business (cash_mode
# "forbidden"); "nonzero" and "free" refuse no non-zero amount.
CASH_SIGN_REFUSALS = {
    "negative": ("cashSignNegative", lambda amount: amount > 0),
    "positive": ("cashSignPositive", lambda amount: amount < 0),
}

# P6 — a decision pending with the developer (2026-10-16): should rules 5-11, which with rule 12 are all the UPDATE path
# runs (``batch_edits._validate_updated_final_state``), enforce the stricter modes TX_TYPE_METADATA gives TRANSFER,
# FX_CONVERSION and CASH_TRANSFER, as CREATE already does with its create-only rules 2, 3 and 3b? Until it is taken they
# keep the behaviour of before W-B36: W-B36 reads the table with these four cases as explicit exceptions.
# Key: the (type, field) of TX_TYPE_METADATA that rules 5-11 do not enforce; value: the case, and what they do instead.
# Case 4 moves no cell of TX-S-095 (rule 11 judges a non-zero cash only, where "nonzero" has nothing to refuse): only its
# guard sees it. An entry leaves only with P6, and its guard (TX-S-104 … TX-S-107) flips with it.
_P6_PENDING: dict[tuple[TransactionType, str], str] = {
    (TransactionType.TRANSFER, "cash_mode"): "case 1: 'forbidden', yet rule 8 refuses cash on ADJUSTMENT only, no cashForbidden",
    (TransactionType.FX_CONVERSION, "quantity_sign"): "case 2: 'zero', yet rule 10 leaves FX_CONVERSION out of qtyZero",
    (TransactionType.TRANSFER, "quantity_sign"): "case 3: 'nonzero', yet rule 10 checks ADJUSTMENT only, no qtyNonzero",
    (TransactionType.FX_CONVERSION, "cash_sign"): "case 4: 'nonzero', yet a zero cash gets no code from rules 5-11",
    (TransactionType.CASH_TRANSFER, "cash_sign"): "case 4: 'nonzero', yet a zero cash gets no code from rules 5-11",
}

# TX-S-108: one violation of each code of rules 5-11 on today's table. The cell, otherwise valid, then the code, the
# message template, the rendered message (the text the user reads, alone or packed in ``multipleBusinessRuleErrors``
# since W-B38) and the params it gets today.
VISIBLE_RULE_MESSAGES = [
    pytest.param({"tx_type": TransactionType.BUY, "quantity": Decimal("1"), "cash": CASH_EUR_MINUS_100}, ("assetRequired", "{type} requires asset_id", "BUY requires asset_id", {"type": "BUY"}), id="assetRequired"),
    pytest.param({"tx_type": TransactionType.DEPOSIT}, ("cashRequired", "{type} requires cash (amount + currency)", "DEPOSIT requires cash (amount + currency)", {"type": "DEPOSIT"}), id="cashRequired"),
    pytest.param(
        {"tx_type": TransactionType.ADJUSTMENT, "asset_id": 1, "quantity": Decimal("1"), "cash": CASH_EUR_PLUS_100},
        ("cashForbidden", "ADJUSTMENT should not have cash movement", "ADJUSTMENT should not have cash movement", {"type": "ADJUSTMENT"}),
        id="cashForbidden",
    ),
    pytest.param(
        {"tx_type": TransactionType.BUY, "asset_id": 1, "quantity": Decimal("1"), "cash": CASH_EUR_MINUS_100, "asset_event_id": 1},
        ("eventTypeIncompatible", "{type} cannot be linked to an asset_event (only {allowed} can)", "BUY cannot be linked to an asset_event (only ADJUSTMENT, DIVIDEND, INTEREST can)", {"type": "BUY", "allowed": "ADJUSTMENT, DIVIDEND, INTEREST"}),
        id="eventTypeIncompatible",
    ),
    pytest.param(
        {"tx_type": TransactionType.INTEREST, "cash": CASH_EUR_PLUS_100, "asset_event_id": 1},
        ("eventRequiresAsset", "asset_event_id requires asset_id", "asset_event_id requires asset_id", {"type": "INTEREST"}),
        id="eventRequiresAsset",
    ),
    pytest.param({"tx_type": TransactionType.BUY, "asset_id": 1, "quantity": Decimal("0"), "cash": CASH_EUR_MINUS_100}, ("qtyPositive", "BUY requires quantity > 0", "BUY requires quantity > 0", {"type": "BUY"}), id="qtyPositive"),
    pytest.param({"tx_type": TransactionType.SELL, "asset_id": 1, "quantity": Decimal("1"), "cash": CASH_EUR_PLUS_100}, ("qtyNegative", "SELL requires quantity < 0", "SELL requires quantity < 0", {"type": "SELL"}), id="qtyNegative"),
    pytest.param({"tx_type": TransactionType.DIVIDEND, "asset_id": 1, "quantity": Decimal("1"), "cash": CASH_EUR_PLUS_100}, ("qtyZero", "{type} requires quantity = 0", "DIVIDEND requires quantity = 0", {"type": "DIVIDEND"}), id="qtyZero"),
    pytest.param({"tx_type": TransactionType.ADJUSTMENT, "asset_id": 1, "quantity": Decimal("0")}, ("qtyNonzero", "ADJUSTMENT requires quantity != 0", "ADJUSTMENT requires quantity != 0", {"type": "ADJUSTMENT"}), id="qtyNonzero"),
    pytest.param({"tx_type": TransactionType.WITHDRAWAL, "cash": CASH_EUR_PLUS_100}, ("cashSignNegative", "{type} requires cash.amount < 0", "WITHDRAWAL requires cash.amount < 0", {"type": "WITHDRAWAL"}), id="cashSignNegative"),
    pytest.param({"tx_type": TransactionType.DEPOSIT, "cash": CASH_EUR_MINUS_100}, ("cashSignPositive", "{type} requires cash.amount > 0", "DEPOSIT requires cash.amount > 0", {"type": "DEPOSIT"}), id="cashSignPositive"),
]


def _run_rules(*, tx_type: TransactionType, asset_id: Optional[int] = None, quantity: Decimal = Decimal("0"), cash: Optional[Currency] = None, asset_event_id: Optional[int] = None) -> list[PydanticCustomError]:
    """``validate_transaction_business_rules`` on this final state, with cost_basis_mode=None: rule 12 (W-B31's) is silent."""
    return validate_transaction_business_rules(tx_type=tx_type, asset_id=asset_id, quantity=quantity, cash=cash, asset_event_id=asset_event_id, cost_basis_mode=None)


def _returned_violations(codes: Optional[frozenset[str]], **cell) -> list[tuple[str, dict]]:
    """The (code, params) ``validate_transaction_business_rules`` returns for ``cell``, in its order, kept to ``codes``.

    ``codes=None`` keeps every code but rule 12's ``costBasisModeIncompatible`` (W-B31's): a code a rule would add shows.
    """
    errors = _run_rules(**cell)
    if codes is None:
        return [(error.type, dict(error.context or {})) for error in errors if error.type != COST_BASIS_MODE_INCOMPATIBLE]
    return [(error.type, dict(error.context or {})) for error in errors if error.type in codes]


def _metadata_mode(tx_type: TransactionType, field: str) -> Optional[str]:
    """What ``TX_TYPE_METADATA``, read when called, says of ``field`` for ``tx_type``; ``None`` where P6 keeps it out of rules 5-11."""
    return None if (tx_type, field) in _P6_PENDING else getattr(TX_TYPE_METADATA[tx_type], field)


def _metadata_event_allowed() -> str:
    """The ``allowed`` param of eventTypeIncompatible as ``TX_TYPE_METADATA`` has it: its event-compatible types, sorted, joined."""
    return ", ".join(sorted(tx_type.value for tx_type, entry in TX_TYPE_METADATA.items() if entry.event_compatible))


def _metadata_violations(codes: Optional[frozenset[str]], *, tx_type: TransactionType, asset_id: Optional[int] = None, quantity: Decimal = Decimal("0"), cash: Optional[Currency] = None, asset_event_id: Optional[int] = None) -> list[tuple[str, dict]]:
    """The (code, params) of rules 5-11 that ``TX_TYPE_METADATA``, read when called, implies for this final state.

    Computed here from the table with the formulas of W-B36, not imported: the expectation must not take the word of the
    code under test.

    - rule 5, assetRequired: asset_mode ``required`` and no asset (``forbidden`` is the create-only rules 3, 3b, 4's);
    - rule 7, cashRequired: cash_mode ``required`` and no cash (a zero cash is a cash);
    - rule 8, cashForbidden: cash_mode ``forbidden`` and a non-zero cash;
    - rule 9, on an asset event: eventTypeIncompatible for a type not ``event_compatible``, ``allowed`` listing those that
      are; eventRequiresAsset without an asset, whatever the type;
    - rules 10 and 11: ``QUANTITY_SIGN_REFUSALS`` by quantity_sign, ``CASH_SIGN_REFUSALS`` by cash_sign on a non-zero cash;

    less the P6 cases (``_P6_PENDING``). Params are ``{"type": <type>}``, plus ``allowed`` for eventTypeIncompatible. Kept
    to ``codes``; ``None`` keeps them all.
    """
    params = {"type": tx_type.value}
    cash_mode = _metadata_mode(tx_type, "cash_mode")
    nonzero_cash = cash is not None and cash.amount != 0
    violations: list[tuple[str, dict]] = []
    if _metadata_mode(tx_type, "asset_mode") == "required" and asset_id is None:
        violations.append(("assetRequired", dict(params)))
    if cash_mode == "required" and cash is None:
        violations.append(("cashRequired", dict(params)))
    if cash_mode == "forbidden" and nonzero_cash:
        violations.append(("cashForbidden", dict(params)))
    if asset_event_id is not None and not TX_TYPE_METADATA[tx_type].event_compatible:
        violations.append(("eventTypeIncompatible", {**params, "allowed": _metadata_event_allowed()}))
    if asset_event_id is not None and asset_id is None:
        violations.append(("eventRequiresAsset", dict(params)))
    quantity_refusal = QUANTITY_SIGN_REFUSALS.get(_metadata_mode(tx_type, "quantity_sign"))
    if quantity_refusal and quantity_refusal[1](quantity):
        violations.append((quantity_refusal[0], dict(params)))
    cash_refusal = CASH_SIGN_REFUSALS.get(_metadata_mode(tx_type, "cash_sign"))
    if nonzero_cash and cash_refusal and cash_refusal[1](cash.amount):
        violations.append((cash_refusal[0], dict(params)))
    return [violation for violation in violations if codes is None or violation[0] in codes]


def _sorted_violations(violations: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
    """``violations`` in a fixed order, so two lists compare as multisets: the order is not the subject, a duplicate is."""
    return sorted(violations, key=lambda violation: (violation[0], sorted(violation[1].items())))


def _metadata_expects(codes: Optional[frozenset[str]], cells: dict[str, dict]) -> dict[str, list[tuple[str, dict]]]:
    """``_metadata_violations`` of every labelled cell: what the table, as it is when called, implies."""
    return {label: _metadata_violations(codes, **cell) for label, cell in cells.items()}


def _rules_return(codes: Optional[frozenset[str]], cells: dict[str, dict]) -> dict[str, list[tuple[str, dict]]]:
    """``_returned_violations`` of every labelled cell: what the function under test answers."""
    return {label: _returned_violations(codes, **cell) for label, cell in cells.items()}


class TestRules5To11FollowMetadata:
    """Rules 5-11 of ``validate_transaction_business_rules`` against ``TX_TYPE_METADATA`` (W-B36).

    Before W-B36 they were hand-written copies of the table: the types that want an asset (rule 5, ``asset_mode``) and a
    cash (7, ``cash_mode``), the cash refused to ADJUSTMENT (8, ``cash_mode`` ``forbidden``), the types an asset event may
    link (9, ``event_compatible``, copied once more as ``EVENT_COMPATIBLE_TYPES``), the quantity and cash signs (10 and 11,
    ``quantity_sign`` and ``cash_sign``). Since W-B36 they read the table when they run, keeping the four cases where the
    table is stricter than the rules as explicit exceptions until P6 (``_P6_PENDING``, ``TestRules5To11P6Pending``).

    - TX-S-095: parity guard, green before W-B36 (the copies matched the table, less the P6 cases) and since.
    - TX-S-096 … TX-S-103: red before W-B36, now its guards. One entry of ``TX_TYPE_METADATA`` is replaced for one test
      and the rule must follow it; a hand-written copy never reads the table, nor would a copy taken from it at import
      time. Each checks first that the real table and the replaced one disagree on its cells (``today`` / ``expected``),
      and keeps only the codes of its rule: a rule that stopped reading the table would answer ``today`` again.

    Pure: no database, no server. The only module state touched is one ``TX_TYPE_METADATA`` entry per red, through
    ``monkeypatch`` (``_replace_metadata_entry``), which puts the original back.
    """

    def test_rules_5_11_match_metadata_on_every_cell(self):
        """TX-S-095: rules 5-11 return exactly what TX_TYPE_METADATA implies, less the P6 cases, on every cell.

        Every type × asset (none, 1) × cash (none, EUR 0, +100, -100) × quantity (-1, 0, 1) × asset event (none, 1), with
        cost_basis_mode=None: the (code, params) the function returns against those ``_metadata_violations`` derives from
        the table. Guard: green before W-B36 because the hand-written rules matched the table once the four P6 cases were
        set aside, and since because the rules read it. Every code but rule 12's is compared, so a code a rule would add,
        or return twice, shows; the order of the list is not compared. One table, one assertion: a failure shows every
        wrong cell at once.
        """
        returned: dict[str, list[tuple[str, dict]]] = {}
        expected: dict[str, list[tuple[str, dict]]] = {}
        for tx_type, asset_id, (cash_label, cash), quantity, asset_event_id in product(TransactionType, PARITY_ASSET_IDS, PARITY_CASHES.items(), PARITY_QUANTITIES, PARITY_EVENT_IDS):
            cell = {"tx_type": tx_type, "asset_id": asset_id, "quantity": quantity, "cash": cash, "asset_event_id": asset_event_id}
            label = f"{tx_type.value} asset={asset_id} cash={cash_label} qty={quantity} event={asset_event_id}"
            returned[label] = _sorted_violations(_returned_violations(None, **cell))
            expected[label] = _sorted_violations(_metadata_violations(None, **cell))

        wrong = {label: f"returned {returned[label]}, TX_TYPE_METADATA says {expected[label]}" for label in expected if returned[label] != expected[label]}
        assert returned == expected, f"Rules 5-11 must return what TX_TYPE_METADATA implies, less the P6 cases (_P6_PENDING): {len(wrong)} of {len(expected)} cells differ: {wrong}"

    def test_rule5_asset_required_follows_metadata(self, monkeypatch):
        """TX-S-096: red before W-B36, now its guard. A BUY made ``asset_mode="optional"`` in TX_TYPE_METADATA gets no assetRequired without asset.

        Before W-B36 rule 5 listed the asset-required types by hand, BUY among them, and refused the BUY whatever the
        table said. Red again means rule 5 stopped reading the table. The BUY is otherwise valid (quantity 1, cash
        -100 EUR) and only rule 5's code is kept.
        """
        cells = {"BUY without asset": {"tx_type": TransactionType.BUY, "quantity": Decimal("1"), "cash": CASH_EUR_MINUS_100}}
        today = {"BUY without asset": [("assetRequired", {"type": "BUY"})]}
        expected = {"BUY without asset": []}
        assert _metadata_expects(RULE_CODES[5], cells) == today, "scaffold: today's table already lets this BUY through rule 5, so the replacement below proves nothing"
        _replace_metadata_entry(monkeypatch, TransactionType.BUY, asset_mode="optional")
        assert _metadata_expects(RULE_CODES[5], cells) == expected, "scaffold: the replaced BUY entry still wants an asset"

        returned = _rules_return(RULE_CODES[5], cells)

        assert returned == expected, f"W-B36: with TX_TYPE_METADATA[BUY].asset_mode = 'optional', rule 5 must not refuse a BUY without asset_id; it returned {returned}: rule 5 no longer reads the table"

    def test_rule7_cash_required_follows_metadata(self, monkeypatch):
        """TX-S-097: red before W-B36, now its guard. A DEPOSIT made ``cash_mode="optional"`` in TX_TYPE_METADATA gets no cashRequired without cash.

        Before W-B36 rule 7 listed the cash-required types by hand, DEPOSIT among them, and refused the DEPOSIT whatever
        the table said. Red again means rule 7 stopped reading the table. The DEPOSIT is otherwise valid (no asset,
        quantity 0) and only rule 7's code is kept.
        """
        cells = {"DEPOSIT without cash": {"tx_type": TransactionType.DEPOSIT}}
        today = {"DEPOSIT without cash": [("cashRequired", {"type": "DEPOSIT"})]}
        expected = {"DEPOSIT without cash": []}
        assert _metadata_expects(RULE_CODES[7], cells) == today, "scaffold: today's table already lets this DEPOSIT through rule 7, so the replacement below proves nothing"
        _replace_metadata_entry(monkeypatch, TransactionType.DEPOSIT, cash_mode="optional")
        assert _metadata_expects(RULE_CODES[7], cells) == expected, "scaffold: the replaced DEPOSIT entry still wants a cash"

        returned = _rules_return(RULE_CODES[7], cells)

        assert returned == expected, f"W-B36: with TX_TYPE_METADATA[DEPOSIT].cash_mode = 'optional', rule 7 must not refuse a DEPOSIT without cash; it returned {returned}: rule 7 no longer reads the table"

    def test_rule8_cash_forbidden_follows_metadata(self, monkeypatch):
        """TX-S-098: red before W-B36, now its guard. An ADJUSTMENT made ``cash_mode="optional"`` in TX_TYPE_METADATA gets no cashForbidden for its cash.

        Before W-B36 rule 8 refused cash on ADJUSTMENT by name, whatever the table said. Red again means rule 8 stopped
        reading the table. The ADJUSTMENT is otherwise valid (asset, quantity 1) with 100 EUR of cash, and only rule 8's
        code is kept.
        """
        cells = {"ADJUSTMENT with EUR +100": {"tx_type": TransactionType.ADJUSTMENT, "asset_id": 1, "quantity": Decimal("1"), "cash": CASH_EUR_PLUS_100}}
        today = {"ADJUSTMENT with EUR +100": [("cashForbidden", {"type": "ADJUSTMENT"})]}
        expected = {"ADJUSTMENT with EUR +100": []}
        assert _metadata_expects(RULE_CODES[8], cells) == today, "scaffold: today's table already lets this ADJUSTMENT keep its cash, so the replacement below proves nothing"
        _replace_metadata_entry(monkeypatch, TransactionType.ADJUSTMENT, cash_mode="optional")
        assert _metadata_expects(RULE_CODES[8], cells) == expected, "scaffold: the replaced ADJUSTMENT entry still forbids its cash"

        returned = _rules_return(RULE_CODES[8], cells)

        assert returned == expected, f"W-B36: with TX_TYPE_METADATA[ADJUSTMENT].cash_mode = 'optional', rule 8 must not refuse an ADJUSTMENT its cash; it returned {returned}: rule 8 no longer reads the table"

    def test_rule9_event_admitted_where_metadata_makes_type_compatible(self, monkeypatch):
        """TX-S-099: red before W-B36, now its guard. A DEPOSIT made ``event_compatible=True`` in TX_TYPE_METADATA may be linked to an asset event.

        Before W-B36 rule 9 asked ``EVENT_COMPATIBLE_TYPES``, a hand-written copy of the table since removed, and refused
        the DEPOSIT with eventTypeIncompatible whatever the table said. Red again means rule 9 stopped reading the table.
        The DEPOSIT has an asset, so eventRequiresAsset has nothing to say (the asset itself is the create-only rule 4's
        business), and only rule 9's codes are kept.
        """
        cells = {"DEPOSIT linked to an event": {"tx_type": TransactionType.DEPOSIT, "asset_id": 1, "cash": CASH_EUR_PLUS_100, "asset_event_id": 1}}
        today = {"DEPOSIT linked to an event": [("eventTypeIncompatible", {"type": "DEPOSIT", "allowed": "ADJUSTMENT, DIVIDEND, INTEREST"})]}
        expected = {"DEPOSIT linked to an event": []}
        assert _metadata_expects(RULE_CODES[9], cells) == today, "scaffold: today's table already lets this DEPOSIT link an asset event, so the replacement below proves nothing"
        _replace_metadata_entry(monkeypatch, TransactionType.DEPOSIT, event_compatible=True)
        assert _metadata_expects(RULE_CODES[9], cells) == expected, "scaffold: the replaced DEPOSIT entry is still not event-compatible"

        returned = _rules_return(RULE_CODES[9], cells)

        assert returned == expected, f"W-B36: with TX_TYPE_METADATA[DEPOSIT].event_compatible = True, rule 9 must let a DEPOSIT with an asset link an asset event; it returned {returned}: rule 9 no longer reads the table"

    def test_rule9_event_refused_where_metadata_makes_type_incompatible(self, monkeypatch):
        """TX-S-100: red before W-B36, now its guard. An ADJUSTMENT made ``event_compatible=False`` is refused an asset event, and ``allowed`` drops it.

        Before W-B36 ``EVENT_COMPATIBLE_TYPES`` held ADJUSTMENT whatever the table said, so rule 9 returned nothing (and its
        ``allowed`` listed ADJUSTMENT). Red again means rule 9 stopped reading the table. The ADJUSTMENT is otherwise valid
        (asset, quantity 1, no cash) and only rule 9's codes are kept.
        """
        cells = {"ADJUSTMENT linked to an event": {"tx_type": TransactionType.ADJUSTMENT, "asset_id": 1, "quantity": Decimal("1"), "asset_event_id": 1}}
        today = {"ADJUSTMENT linked to an event": []}
        expected = {"ADJUSTMENT linked to an event": [("eventTypeIncompatible", {"type": "ADJUSTMENT", "allowed": "DIVIDEND, INTEREST"})]}
        assert _metadata_expects(RULE_CODES[9], cells) == today, "scaffold: today's table already refuses this ADJUSTMENT its asset event, so the replacement below proves nothing"
        _replace_metadata_entry(monkeypatch, TransactionType.ADJUSTMENT, event_compatible=False)
        assert _metadata_expects(RULE_CODES[9], cells) == expected, "scaffold: the replaced ADJUSTMENT entry is still event-compatible, or the table's allowed list still names it"

        returned = _rules_return(RULE_CODES[9], cells)

        assert returned == expected, f"W-B36: with TX_TYPE_METADATA[ADJUSTMENT].event_compatible = False, rule 9 must refuse an ADJUSTMENT linked to an asset event, allowed 'DIVIDEND, INTEREST'; it returned {returned}: rule 9 no longer reads the table"

    def test_rule10_positive_negative_follow_metadata(self, monkeypatch):
        """TX-S-101: red before W-B36, now its guard. A BUY made ``quantity_sign="negative"`` in TX_TYPE_METADATA wants a quantity < 0.

        Before W-B36 rule 10 wanted quantity > 0 from BUY by name, whatever the table said: -1 got qtyPositive, 1 nothing.
        Red again means rule 10 stopped reading the table. The BUY is otherwise valid (asset, cash -100 EUR) and only
        rule 10's codes are kept.
        """
        cells = {
            "BUY quantity -1": {"tx_type": TransactionType.BUY, "asset_id": 1, "quantity": Decimal("-1"), "cash": CASH_EUR_MINUS_100},
            "BUY quantity 1": {"tx_type": TransactionType.BUY, "asset_id": 1, "quantity": Decimal("1"), "cash": CASH_EUR_MINUS_100},
        }
        today = {"BUY quantity -1": [("qtyPositive", {"type": "BUY"})], "BUY quantity 1": []}
        expected = {"BUY quantity -1": [], "BUY quantity 1": [("qtyNegative", {"type": "BUY"})]}
        assert _metadata_expects(RULE_CODES[10], cells) == today, "scaffold: today's table does not want quantity > 0 from BUY, so the replacement below proves nothing"
        _replace_metadata_entry(monkeypatch, TransactionType.BUY, quantity_sign="negative")
        assert _metadata_expects(RULE_CODES[10], cells) == expected, "scaffold: the replaced BUY entry does not want quantity < 0"

        returned = _rules_return(RULE_CODES[10], cells)

        assert returned == expected, f"W-B36: with TX_TYPE_METADATA[BUY].quantity_sign = 'negative', rule 10 must admit BUY quantity -1 and refuse 1 (qtyNegative); it returned {returned}: rule 10 no longer reads the table"

    def test_rule10_zero_nonzero_follow_metadata(self, monkeypatch):
        """TX-S-102: red before W-B36, now its guard. An ADJUSTMENT made ``quantity_sign="zero"`` in TX_TYPE_METADATA wants a quantity = 0.

        The other half of rule 10, where the P6 cases 2 and 3 live: ``zero`` and ``nonzero`` must come from the table too,
        not only ``positive`` and ``negative`` (TX-S-101). Before W-B36 rule 10 wanted quantity != 0 from ADJUSTMENT by
        name, whatever the table said: 0 got qtyNonzero, 1 nothing. Red again means rule 10 stopped reading the table.
        Only rule 10's codes are kept.
        """
        cells = {
            "ADJUSTMENT quantity 0": {"tx_type": TransactionType.ADJUSTMENT, "asset_id": 1, "quantity": Decimal("0")},
            "ADJUSTMENT quantity 1": {"tx_type": TransactionType.ADJUSTMENT, "asset_id": 1, "quantity": Decimal("1")},
        }
        today = {"ADJUSTMENT quantity 0": [("qtyNonzero", {"type": "ADJUSTMENT"})], "ADJUSTMENT quantity 1": []}
        expected = {"ADJUSTMENT quantity 0": [], "ADJUSTMENT quantity 1": [("qtyZero", {"type": "ADJUSTMENT"})]}
        assert _metadata_expects(RULE_CODES[10], cells) == today, "scaffold: today's table does not want quantity != 0 from ADJUSTMENT, so the replacement below proves nothing"
        _replace_metadata_entry(monkeypatch, TransactionType.ADJUSTMENT, quantity_sign="zero")
        assert _metadata_expects(RULE_CODES[10], cells) == expected, "scaffold: the replaced ADJUSTMENT entry does not want quantity = 0"

        returned = _rules_return(RULE_CODES[10], cells)

        assert returned == expected, f"W-B36: with TX_TYPE_METADATA[ADJUSTMENT].quantity_sign = 'zero', rule 10 must admit ADJUSTMENT quantity 0 and refuse 1 (qtyZero); it returned {returned}: rule 10 no longer reads the table"

    def test_rule11_cash_sign_follows_metadata(self, monkeypatch):
        """TX-S-103: red before W-B36, now its guard. A DEPOSIT made ``cash_sign="negative"`` in TX_TYPE_METADATA wants a cash amount < 0.

        Before W-B36 rule 11 wanted a positive amount from DEPOSIT by name, whatever the table said: +100 EUR passed,
        -100 EUR got cashSignPositive. Red again means rule 11 stopped reading the table. The DEPOSIT is otherwise valid
        (no asset, quantity 0) and only rule 11's codes are kept.
        """
        cells = {
            "DEPOSIT EUR +100": {"tx_type": TransactionType.DEPOSIT, "cash": CASH_EUR_PLUS_100},
            "DEPOSIT EUR -100": {"tx_type": TransactionType.DEPOSIT, "cash": CASH_EUR_MINUS_100},
        }
        today = {"DEPOSIT EUR +100": [], "DEPOSIT EUR -100": [("cashSignPositive", {"type": "DEPOSIT"})]}
        expected = {"DEPOSIT EUR +100": [("cashSignNegative", {"type": "DEPOSIT"})], "DEPOSIT EUR -100": []}
        assert _metadata_expects(RULE_CODES[11], cells) == today, "scaffold: today's table does not want a positive cash from DEPOSIT, so the replacement below proves nothing"
        _replace_metadata_entry(monkeypatch, TransactionType.DEPOSIT, cash_sign="negative")
        assert _metadata_expects(RULE_CODES[11], cells) == expected, "scaffold: the replaced DEPOSIT entry does not want a negative cash"

        returned = _rules_return(RULE_CODES[11], cells)

        assert returned == expected, f"W-B36: with TX_TYPE_METADATA[DEPOSIT].cash_sign = 'negative', rule 11 must refuse DEPOSIT +100 EUR (cashSignNegative) and admit -100 EUR; it returned {returned}: rule 11 no longer reads the table"


class TestRules5To11P6Pending:
    """The four cases where ``TX_TYPE_METADATA`` is stricter than rules 5-11 today: P6, a decision pending with the developer.

    These guards pin a pending developer decision (P6, 2026-10-16): should the UPDATE path, which runs rules 5-12 alone,
    enforce the table's stricter modes as CREATE does with its create-only rules 2, 3 and 3b? Until it is taken the
    behaviour of before W-B36 stays: W-B36 keeps these cases as explicit exceptions. Green before and since W-B36; each
    flips only with P6, together with its entry in ``_P6_PENDING``. Each checks first that the table still says the
    stricter thing and that the case is still pending. Every cell is otherwise valid for rules 5-11, so nothing at all
    comes back.
    """

    def test_p6_case1_transfer_cash_not_refused(self):
        """TX-S-104: P6 case 1. A TRANSFER with 100 EUR of cash gets no cashForbidden, though TX_TYPE_METADATA forbids its cash.

        Pins a pending developer decision (P6, 2026-10-16); it must flip only with it. Rule 8 refuses cash on ADJUSTMENT
        only. CREATE refuses this TRANSFER anyway (create-only rule 2); an UPDATE lets it through.
        """
        assert TX_TYPE_METADATA[TransactionType.TRANSFER].cash_mode == "forbidden", "scaffold: TX_TYPE_METADATA no longer forbids cash on TRANSFER: P6 case 1 is gone, retire this guard"
        assert (TransactionType.TRANSFER, "cash_mode") in _P6_PENDING, "scaffold: P6 case 1 has left _P6_PENDING, so the decision is taken: flip this guard with it"

        returned = _returned_violations(None, tx_type=TransactionType.TRANSFER, asset_id=1, quantity=Decimal("1"), cash=CASH_EUR_PLUS_100)

        assert returned == [], f"P6 case 1 is pending: until the developer decides, rules 5-11 must keep admitting a TRANSFER with cash (no cashForbidden); got {returned}"

    def test_p6_case2_fx_conversion_quantity_not_refused(self):
        """TX-S-105: P6 case 2. An FX_CONVERSION with quantity 1 gets no qtyZero, though TX_TYPE_METADATA gives it quantity_sign ``zero``.

        Pins a pending developer decision (P6, 2026-10-16); it must flip only with it. Rule 10 leaves FX_CONVERSION out of
        qtyZero. CREATE refuses it anyway (create-only rule 3, fxConversionQtyZero); an UPDATE lets it through.
        """
        assert TX_TYPE_METADATA[TransactionType.FX_CONVERSION].quantity_sign == "zero", "scaffold: TX_TYPE_METADATA no longer wants quantity = 0 from FX_CONVERSION: P6 case 2 is gone, retire this guard"
        assert (TransactionType.FX_CONVERSION, "quantity_sign") in _P6_PENDING, "scaffold: P6 case 2 has left _P6_PENDING, so the decision is taken: flip this guard with it"

        returned = _returned_violations(None, tx_type=TransactionType.FX_CONVERSION, quantity=Decimal("1"), cash=CASH_EUR_PLUS_100)

        assert returned == [], f"P6 case 2 is pending: until the developer decides, rules 5-11 must keep admitting an FX_CONVERSION with a quantity (no qtyZero); got {returned}"

    def test_p6_case3_transfer_zero_quantity_not_refused(self):
        """TX-S-106: P6 case 3. A TRANSFER with quantity 0 gets no qtyNonzero, though TX_TYPE_METADATA gives it quantity_sign ``nonzero``.

        Pins a pending developer decision (P6, 2026-10-16); it must flip only with it. Rule 10 wants quantity != 0 from
        ADJUSTMENT only. CREATE refuses this TRANSFER anyway (create-only rule 2); an UPDATE lets it through.
        """
        assert TX_TYPE_METADATA[TransactionType.TRANSFER].quantity_sign == "nonzero", "scaffold: TX_TYPE_METADATA no longer wants quantity != 0 from TRANSFER: P6 case 3 is gone, retire this guard"
        assert (TransactionType.TRANSFER, "quantity_sign") in _P6_PENDING, "scaffold: P6 case 3 has left _P6_PENDING, so the decision is taken: flip this guard with it"

        returned = _returned_violations(None, tx_type=TransactionType.TRANSFER, asset_id=1, quantity=Decimal("0"))

        assert returned == [], f"P6 case 3 is pending: until the developer decides, rules 5-11 must keep admitting a TRANSFER with quantity 0 (no qtyNonzero); got {returned}"

    def test_p6_case4_zero_cash_not_refused_on_fx_conversion_and_cash_transfer(self):
        """TX-S-107: P6 case 4. FX_CONVERSION and CASH_TRANSFER with a zero cash get no code, though their cash_sign is ``nonzero``.

        Pins a pending developer decision (P6, 2026-10-16); it must flip only with it. Rule 11 judges a non-zero cash only
        and rule 7 wants a cash, which a zero cash is: none of rules 5-11 refuses it. CREATE refuses both anyway (create-only
        rules 3 and 3b: fxConversionCashRequired, cashRequired); an UPDATE lets them through. The parity table (TX-S-095)
        cannot see this case: only this guard does.
        """
        types = (TransactionType.FX_CONVERSION, TransactionType.CASH_TRANSFER)
        not_nonzero = [tx_type.value for tx_type in types if TX_TYPE_METADATA[tx_type].cash_sign != "nonzero"]
        assert not not_nonzero, f"scaffold: TX_TYPE_METADATA no longer gives {not_nonzero} cash_sign 'nonzero': that part of P6 case 4 is gone, retire it here"
        not_pending = [tx_type.value for tx_type in types if (tx_type, "cash_sign") not in _P6_PENDING]
        assert not not_pending, f"scaffold: P6 case 4 has left _P6_PENDING for {not_pending}, so the decision is taken: flip this guard with it"

        returned = {tx_type.value: _returned_violations(None, tx_type=tx_type, cash=CASH_EUR_ZERO) for tx_type in types}

        assert returned == {"FX_CONVERSION": [], "CASH_TRANSFER": []}, f"P6 case 4 is pending: until the developer decides, rules 5-11 must keep admitting a zero cash on FX_CONVERSION and CASH_TRANSFER (no code at all); got {returned}"


class TestRules5To11VisibleMessages:
    """What the user reads of rules 5-11: code, message and params, one violation of each code (W-B36, W-B38).

    TX-S-108 is a guard, green before and since W-B36: W-B36 changed where the rules find their types, not what they
    tell the user (the developer's decision, 2026-10-16: the texts stay identical). It pins both texts of every code,
    ``message_template`` and the rendered ``message()``. The four messages written before W-B36 with their type in the
    text (qtyPositive "BUY requires quantity > 0", qtyNegative "SELL ...", qtyNonzero and cashForbidden "ADJUSTMENT
    ...") keep it in the template too, a text per type rather than ``{type}``; the other codes keep their ``{type}``
    templates.

    TX-S-109 pins the packing (W-B38). The user reads the rendered text however many rules a create breaks. A single
    violation is raised as it is and rendered, ``message()``; two or more are packed by ``TXCreateItem`` into one
    ``multipleBusinessRuleErrors``, each with its code, its rendered ``message()`` and its params still in ``ctx``,
    which batch validation (``TXValidationIssue.error``) and broker import (``BRIMValidationIssue.message``) pass on.
    Before W-B38 the pack carried each ``message_template``, so a ``{type}`` template reached the user unresolved:
    "{type} requires asset_id".
    """

    @pytest.mark.parametrize(("cell", "violation"), VISIBLE_RULE_MESSAGES)
    def test_rule_message_unchanged(self, cell, violation):
        """TX-S-108: a cell otherwise valid on today's table gets exactly one violation, with this code, template, message and params."""
        returned = [(error.type, error.message_template, error.message(), error.context) for error in _run_rules(**cell)]

        assert returned == [violation], f"Rules 5-11 must keep the code, the message template, the rendered message and the params the user gets: expected {[violation]}, got {returned}"

    def test_packed_messages_rendered(self):
        """TX-S-109: two violations on one create reach the user packed, each with its message rendered (W-B38).

        A BUY with no asset and quantity 0, otherwise valid: ``TXCreateItem`` raises one ``multipleBusinessRuleErrors``
        whose ``ctx.errors`` holds the code, the rendered ``message()`` and the params of each violation, the text batch
        validation and broker import show. A ``{type}`` template (assetRequired) must come out resolved, exactly as a
        single violation of it is (TX-S-108), and a text written per type (qtyPositive) unchanged; code and params stay
        as they were. Red before W-B38, which packed ``message_template`` and leaked "{type} requires asset_id"; the
        order of the list is not the subject.
        """
        with pytest.raises(ValidationError) as exc_info:
            TXCreateItem(broker_id=1, type=TransactionType.BUY, date=date.today(), quantity=Decimal("0"), cash=CASH_EUR_MINUS_100)

        errors = exc_info.value.errors()
        assert [error["type"] for error in errors] == ["multipleBusinessRuleErrors"], f"A BUY with no asset and quantity 0 must fail on two business rules at once, packed in one multipleBusinessRuleErrors; got {errors}"
        packed = sorted(errors[0]["ctx"]["errors"], key=lambda entry: entry["code"])
        unresolved = [entry["msg"] for entry in packed if "{" in entry["msg"]]
        assert unresolved == [], f"Each packed text is what the user reads in batch validation and broker import, so it must be rendered (W-B38): the user would read {unresolved}"
        expected = [
            {"code": "assetRequired", "msg": "BUY requires asset_id", "ctx": {"type": "BUY"}},
            {"code": "qtyPositive", "msg": "BUY requires quantity > 0", "ctx": {"type": "BUY"}},
        ]
        assert packed == expected, f"Two violations must be packed with the code, the rendered message and the params of each (W-B38): expected {expected}, got {packed}"
