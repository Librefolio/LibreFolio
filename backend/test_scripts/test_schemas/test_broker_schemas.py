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
    BRReadItem,
    BRUpdateItem,
    BRDeleteItem,
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
            ]
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
            ]
        )
        assert len(broker.initial_balances) == 1
        assert broker.initial_balances[0].code == "EUR"

    def test_initial_balances_negative_filtered(self):
        """BR-S-014: Negative amounts should be filtered out."""
        broker = BRCreateItem(
            name="Test Broker",
            initial_balances=[
                Currency(code="EUR", amount=Decimal("-1000")),  # Should be filtered
            ]
        )
        # All filtered out, becomes None
        assert broker.initial_balances is None

    def test_initial_balances_mixed(self):
        """BR-S-015: Mixed amounts should keep only positive."""
        broker = BRCreateItem(
            name="Test Broker",
            initial_balances=[
                Currency(code="EUR", amount=Decimal("5000")),   # Keep
                Currency(code="USD", amount=Decimal("-1000")),  # Filter
                Currency(code="GBP", amount=Decimal("0")),      # Filter
                Currency(code="CHF", amount=Decimal("2000")),   # Keep
            ]
        )
        assert len(broker.initial_balances) == 2
        codes = [c.code for c in broker.initial_balances]
        assert "EUR" in codes
        assert "CHF" in codes


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

    def test_update_name_empty(self):
        """BR-S-021: BRUpdateItem with empty name should fail."""
        # min_length=1 constraint catches this before custom validator
        with pytest.raises(ValidationError, match="at least 1 character"):
            BRUpdateItem(name="")

    def test_update_name_valid(self):
        """BR-S-022: BRUpdateItem with valid name should pass."""
        update = BRUpdateItem(name="New Broker Name")
        assert update.name == "New Broker Name"

    def test_update_description(self):
        """Update description should work."""
        update = BRUpdateItem(description="New description")
        assert update.description == "New description"

    def test_update_portal_url(self):
        """Update portal_url should work."""
        update = BRUpdateItem(portal_url="https://broker.com")
        assert update.portal_url == "https://broker.com"

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
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        broker = BRReadItem(**data)
        assert broker.id == 1
        assert broker.name == "Test Broker"

    def test_read_item_optional_fields(self):
        """BRReadItem optional fields can be None."""
        data = {
            "id": 1,
            "name": "Test Broker",
            "description": None,
            "portal_url": None,
            "allow_cash_overdraft": True,
            "allow_asset_shorting": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        broker = BRReadItem(**data)
        assert broker.description is None
        assert broker.portal_url is None

