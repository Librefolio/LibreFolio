#!/usr/bin/env python3
"""
Database mock data population script for LibreFolio.

This script populates the database with comprehensive MOCK data
for testing purposes (especially useful for frontend development).
The data demonstrates all features of the schema with realistic examples.

⚠️  WARNING: This is MOCK DATA for testing only!
    - Brokers: Interactive Brokers, Degiro, Recrowd
    - Assets: AAPL, MSFT, TSLA, VWCE, etc.
    - Transactions: Buy, sell, dividends, etc.
    - FX Rates: Last 30 days for USD, GBP, CHF, JPY

⚠️  DATABASE BEHAVIOR:
    - If database already has data → script ABORTS with error
    - Use --force flag to DELETE and recreate database
    - Example: python -m backend.test_scripts.test_db.populate_mock_data --force

Usage:
    python -m backend.test_scripts.test_db.populate_mock_data
    python -m backend.test_scripts.test_db.populate_mock_data --force  # Delete and recreate
    python test_runner.py db populate
    python test_runner.py db populate --force  # Delete and recreate
"""

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database, initialize_test_database

setup_test_database()

# Get database path from config
from backend.app.config import get_settings

import argparse
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlmodel import Session, select, delete
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from backend.app.db import (
    # DON'T import sync_engine - it was created before setup_test_database()!
    Broker,
    Asset,
    AssetProviderAssignment,
    Transaction,
    PriceHistory,
    FxRate,
    FxCurrencyPairSource,
    CashAccount,
    CashMovement,
    IdentifierType,
    AssetType,
    ValuationModel,
    TransactionType,
    CashMovementType,
    )
from backend.app.services.provider_registry import FXProviderRegistry

# Create engine AFTER setup_test_database() has set DATABASE_URL
# This ensures we use the test database, not the production one
_settings = get_settings()
engine = create_engine(
    _settings.DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    )


def cleanup_all_tables(session: Session):
    """Delete all existing data from all tables (in correct order for FK constraints)."""
    print("\n🗑️  Cleaning up existing data...")
    print("-" * 60)

    try:
        # Delete in order: child tables first, then parent tables
        # This respects foreign key constraints
        tables_to_clean = [
            CashMovement,
            Transaction,
            PriceHistory,
            AssetProviderAssignment,
            FxRate,
            FxCurrencyPairSource,
            CashAccount,
            Asset,
            Broker,
            ]

        for model in tables_to_clean:
            # Count existing rows
            count_before = len(session.exec(select(model)).all())

            if count_before > 0:
                # Delete all rows from this table
                session.exec(delete(model))
                print(f"  ✅ Cleared {model.__tablename__} ({count_before} rows)")
            else:
                print(f"  ℹ️  {model.__tablename__} already empty")

        session.commit()
        print("  ✅ Cleanup completed\n")

    except Exception as e:
        print(f"  ⚠️  Cleanup error: {e}")
        session.rollback()
        raise


def populate_brokers(session: Session):
    """Create realistic broker accounts."""
    print("\n📊 Creating Brokers...")
    print("-" * 60)

    brokers_data = [
        {
            "name": "Interactive Brokers",
            "description": "Global multi-asset broker with low fees",
            "portal_url": "https://www.interactivebrokers.com",
            },
        {
            "name": "Degiro",
            "description": "European discount broker",
            "portal_url": "https://www.degiro.com",
            },
        {
            "name": "Recrowd",
            "description": "Italian P2P real estate lending platform",
            "portal_url": "https://www.recrowd.it",
            },
        ]

    for data in brokers_data:
        broker = Broker(**data)
        session.add(broker)
        print(f"  ✅ {broker.name}")

    session.commit()


def populate_assets(session: Session):
    """Create diverse asset types."""
    print("\n📈 Creating Assets...")
    print("-" * 60)

    assets_data = [
        # Stocks
        {
            "display_name": "Apple Inc.",
            "identifier": "AAPL",
            "identifier_type": IdentifierType.TICKER,
            "currency": "USD",
            "asset_type": AssetType.STOCK,
            "valuation_model": ValuationModel.MARKET_PRICE,
            },
        {
            "display_name": "Microsoft Corporation",
            "identifier": "MSFT",
            "identifier_type": IdentifierType.TICKER,
            "currency": "USD",
            "asset_type": AssetType.STOCK,
            "valuation_model": ValuationModel.MARKET_PRICE,
            },
        {
            "display_name": "Tesla, Inc.",
            "identifier": "TSLA",
            "identifier_type": IdentifierType.TICKER,
            "currency": "USD",
            "asset_type": AssetType.STOCK,
            "valuation_model": ValuationModel.MARKET_PRICE,
            },
        # ETFs
        {
            "display_name": "Vanguard FTSE All-World UCITS ETF",
            "identifier": "VWCE",
            "identifier_type": IdentifierType.TICKER,
            "currency": "EUR",
            "asset_type": AssetType.ETF,
            "valuation_model": ValuationModel.MARKET_PRICE,
            },
        {
            "display_name": "iShares Core S&P 500 UCITS ETF",
            "identifier": "CSPX",
            "identifier_type": IdentifierType.TICKER,
            "currency": "EUR",
            "asset_type": AssetType.ETF,
            "valuation_model": ValuationModel.MARKET_PRICE,
            },
        # HOLD assets (manual valuation)
        {
            "display_name": "Apartment - Milano Navigli",
            "identifier": "REALESTATE-001",
            "identifier_type": IdentifierType.OTHER,
            "currency": "EUR",
            "asset_type": AssetType.HOLD,
            "valuation_model": ValuationModel.MANUAL,
            # No plugins - manual valuation only
            },
        # P2P Loans
        {
            "display_name": "Real Estate Loan - Milano Centro",
            "identifier": "RECROWD-12345",
            "identifier_type": IdentifierType.OTHER,
            "currency": "EUR",
            "asset_type": AssetType.CROWDFUND_LOAN,
            "valuation_model": ValuationModel.SCHEDULED_YIELD,
            "face_value": Decimal("10000.00"),
            "maturity_date": date.today() + timedelta(days=365),
            "interest_schedule": json.dumps([
                {
                    "start_date": str(date.today()),
                    "end_date": str(date.today() + timedelta(days=365)),
                    "annual_rate": 0.085,
                    "compounding": "SIMPLE",
                    "compound_frequency": "MONTHLY",
                    "day_count": "ACT/365",
                    }
                ]),
            "late_interest": json.dumps({
                "annual_rate": 0.12,
                "grace_days": 0,
                }),
            },
        {
            "display_name": "Real Estate Loan - Roma Parioli",
            "identifier": "RECROWD-12346",
            "identifier_type": IdentifierType.OTHER,
            "currency": "EUR",
            "asset_type": AssetType.CROWDFUND_LOAN,
            "valuation_model": ValuationModel.SCHEDULED_YIELD,
            "face_value": Decimal("5000.00"),
            "maturity_date": date.today() + timedelta(days=540),
            "interest_schedule": json.dumps([
                {
                    "start_date": str(date.today()),
                    "end_date": str(date.today() + timedelta(days=540)),
                    "annual_rate": 0.095,
                    "compounding": "SIMPLE",
                    "compound_frequency": "MONTHLY",
                    "day_count": "ACT/365",
                    }
                ]),
            "late_interest": json.dumps({
                "annual_rate": 0.12,
                "grace_days": 0,
                }),
            },
        ]

    for data in assets_data:
        asset = Asset(**data)
        session.add(asset)
        asset_desc = f"{data['display_name']} ({data['identifier']})"
        if data.get('face_value'):
            asset_desc += f" - €{data['face_value']}"
        print(f"  ✅ {asset_desc}")

    session.commit()


def populate_asset_provider_assignments(session: Session):
    """
    Assign pricing providers to market-priced assets.

    This demonstrates the asset_provider_assignments table functionality.
    Assets with MARKET_PRICE valuation get automatic pricing providers.
    """
    print("\n🔧 Creating Asset Provider Assignments...")
    print("-" * 60)

    # Map: identifier → (provider_code, provider_params)
    # provider_params is JSON configuration for the provider
    assignments = [
        ("AAPL", "yfinance", json.dumps({"symbol": "AAPL"})),
        ("MSFT", "yfinance", json.dumps({"symbol": "MSFT"})),
        ("TSLA", "yfinance", json.dumps({"symbol": "TSLA"})),
        ("VWCE", "yfinance", json.dumps({"symbol": "VWCE.MI"})),
        ("CSPX", "yfinance", json.dumps({"symbol": "CSPX.L"})),
        # Note: HOLD assets and SCHEDULED_YIELD loans don't need providers
        ]

    for identifier, provider_code, provider_params in assignments:
        asset = session.exec(select(Asset).where(Asset.identifier == identifier)).first()
        if not asset:
            print(f"  ⚠️  Asset {identifier} not found, skipping assignment")
            continue

        assignment = AssetProviderAssignment(
            asset_id=asset.id,
            provider_code=provider_code,
            provider_params=provider_params,
            last_fetch_at=None,  # Never fetched yet
            )
        session.add(assignment)
        print(f"  ✅ {identifier} → {provider_code}")

    session.commit()
    print(f"\n  📊 Assigned providers to {len(assignments)} assets")


def populate_cash_accounts(session: Session):
    """Create cash accounts for each broker."""
    print("\n💵 Creating Cash Accounts...")
    print("-" * 60)

    # Interactive Brokers - multi-currency
    ib = session.exec(select(Broker).where(Broker.name == "Interactive Brokers")).first()
    if ib:
        for currency in ["EUR", "USD"]:
            account = CashAccount(
                broker_id=ib.id,
                currency=currency,
                display_name=f"Interactive Brokers {currency} Account",
                )
            session.add(account)
            print(f"  ✅ {account.display_name}")

    # Degiro - EUR only
    degiro = session.exec(select(Broker).where(Broker.name == "Degiro")).first()
    if degiro:
        account = CashAccount(
            broker_id=degiro.id,
            currency="EUR",
            display_name="Degiro EUR Account",
            )
        session.add(account)
        print(f"  ✅ {account.display_name}")

    # Recrowd - EUR only
    recrowd = session.exec(select(Broker).where(Broker.name == "Recrowd")).first()
    if recrowd:
        account = CashAccount(
            broker_id=recrowd.id,
            currency="EUR",
            display_name="Recrowd EUR Account",
            )
        session.add(account)
        print(f"  ✅ {account.display_name}")

    session.commit()


def populate_deposits(session: Session):
    """Initial deposits to fund the accounts."""
    print("\n💰 Creating Initial Deposits...")
    print("-" * 60)

    deposits = [
        ("Interactive Brokers", "EUR", Decimal("15000.00"), "Initial funding from bank"),
        ("Interactive Brokers", "USD", Decimal("10000.00"), "USD funding from bank"),
        ("Degiro", "EUR", Decimal("5000.00"), "Initial deposit"),
        ("Recrowd", "EUR", Decimal("15000.00"), "P2P lending capital"),
        ]

    for broker_name, currency, amount, note in deposits:
        broker = session.exec(select(Broker).where(Broker.name == broker_name)).first()
        if not broker:
            continue

        cash_account = session.exec(
            select(CashAccount).where(
                CashAccount.broker_id == broker.id,
                CashAccount.currency == currency
                )
            ).first()

        if cash_account:
            deposit = CashMovement(
                cash_account_id=cash_account.id,
                type=CashMovementType.DEPOSIT,
                amount=amount,
                trade_date=date.today() - timedelta(days=30),
                note=note,
                )
            session.add(deposit)
            print(f"  ✅ {broker_name} {currency}: +{amount} {currency}")

    session.commit()


def populate_transactions_and_cash(session: Session):
    """Create realistic transaction history with automatic cash movements."""
    print("\n📊 Creating Transactions & Cash Movements...")
    print("-" * 60)

    # Get brokers and assets
    ib = session.exec(select(Broker).where(Broker.name == "Interactive Brokers")).first()
    degiro = session.exec(select(Broker).where(Broker.name == "Degiro")).first()
    recrowd = session.exec(select(Broker).where(Broker.name == "Recrowd")).first()

    apple = session.exec(select(Asset).where(Asset.identifier == "AAPL")).first()
    msft = session.exec(select(Asset).where(Asset.identifier == "MSFT")).first()
    tsla = session.exec(select(Asset).where(Asset.identifier == "TSLA")).first()
    vwce = session.exec(select(Asset).where(Asset.identifier == "VWCE")).first()
    cspx = session.exec(select(Asset).where(Asset.identifier == "CSPX")).first()
    loan1 = session.exec(select(Asset).where(Asset.identifier == "RECROWD-12345")).first()
    loan2 = session.exec(select(Asset).where(Asset.identifier == "RECROWD-12346")).first()

    # Transaction history (most recent first)
    transactions = [
        # Day -30: Buy AAPL on Interactive Brokers
        {
            "broker": ib,
            "asset": apple,
            "type": TransactionType.BUY,
            "quantity": Decimal("15.0"),
            "price": Decimal("175.50"),
            "currency": "USD",
            "fees": Decimal("1.00"),
            "days_ago": 30,
            "note": "Initial AAPL purchase",
            },
        # Day -25: Buy VWCE on Degiro
        {
            "broker": degiro,
            "asset": vwce,
            "type": TransactionType.BUY,
            "quantity": Decimal("50.0"),
            "price": Decimal("95.30"),
            "currency": "EUR",
            "fees": Decimal("0.00"),
            "days_ago": 25,
            "note": "Start ETF accumulation plan",
            },
        # Day -20: Invest in loan 1 on Recrowd
        {
            "broker": recrowd,
            "asset": loan1,
            "type": TransactionType.BUY,
            "quantity": Decimal("1.0"),
            "price": Decimal("10000.00"),
            "currency": "EUR",
            "fees": Decimal("0.00"),
            "days_ago": 20,
            "note": "P2P lending - Milano Centro",
            },
        # Day -18: Buy MSFT on Interactive Brokers
        {
            "broker": ib,
            "asset": msft,
            "type": TransactionType.BUY,
            "quantity": Decimal("10.0"),
            "price": Decimal("380.25"),
            "currency": "USD",
            "fees": Decimal("1.00"),
            "days_ago": 18,
            "note": "Diversification into MSFT",
            },
        # Day -15: Invest in loan 2 on Recrowd
        {
            "broker": recrowd,
            "asset": loan2,
            "type": TransactionType.BUY,
            "quantity": Decimal("1.0"),
            "price": Decimal("5000.00"),
            "currency": "EUR",
            "fees": Decimal("0.00"),
            "days_ago": 15,
            "note": "P2P lending - Roma Parioli",
            },
        # Day -10: Buy more VWCE on Degiro
        {
            "broker": degiro,
            "asset": vwce,
            "type": TransactionType.BUY,
            "quantity": Decimal("30.0"),
            "price": Decimal("96.10"),
            "currency": "EUR",
            "fees": Decimal("0.00"),
            "days_ago": 10,
            "note": "Monthly ETF purchase",
            },
        # Day -8: Receive dividend from AAPL
        {
            "broker": ib,
            "asset": apple,
            "type": TransactionType.DIVIDEND,
            "quantity": Decimal("0.0"),
            "price": Decimal("3.75"),
            "currency": "USD",
            "fees": Decimal("0.00"),
            "taxes": Decimal("1.13"),
            "days_ago": 8,
            "note": "Q4 dividend payment",
            },
        # Day -5: Sell some AAPL (taking profit)
        {
            "broker": ib,
            "asset": apple,
            "type": TransactionType.SELL,
            "quantity": Decimal("5.0"),
            "price": Decimal("182.00"),
            "currency": "USD",
            "fees": Decimal("1.00"),
            "days_ago": 5,
            "note": "Taking profits",
            },
        # Day -3: Interest payment from loan 1
        {
            "broker": recrowd,
            "asset": loan1,
            "type": TransactionType.INTEREST,
            "quantity": Decimal("0.0"),
            "price": Decimal("70.83"),
            "currency": "EUR",
            "fees": Decimal("0.00"),
            "days_ago": 3,
            "note": "Monthly interest payment",
            },
        # Day -1: Buy CSPX on Degiro
        {
            "broker": degiro,
            "asset": cspx,
            "type": TransactionType.BUY,
            "quantity": Decimal("20.0"),
            "price": Decimal("485.50"),
            "currency": "EUR",
            "fees": Decimal("0.00"),
            "days_ago": 1,
            "note": "S&P 500 exposure",
            },
        ]

    for tx_data in transactions:
        # Determine if this transaction type requires a cash movement
        requires_cash = tx_data["type"] in [
            TransactionType.BUY,
            TransactionType.SELL,
            TransactionType.DIVIDEND,
            TransactionType.INTEREST,
            TransactionType.FEE,
            TransactionType.TAX,
        ]

        cash_movement_id = None

        # Create CashMovement FIRST if required (before Transaction due to CHECK constraint)
        if requires_cash:
            cash_account = session.exec(
                select(CashAccount).where(
                    CashAccount.broker_id == tx_data["broker"].id,
                    CashAccount.currency == tx_data["currency"]
                )
            ).first()

            if cash_account:
                cash_type = None
                cash_amount = Decimal("0.00")

                if tx_data["type"] == TransactionType.BUY:
                    cash_type = CashMovementType.BUY_SPEND
                    cash_amount = tx_data["quantity"] * tx_data["price"] + tx_data.get("fees", Decimal("0.00"))
                elif tx_data["type"] == TransactionType.SELL:
                    cash_type = CashMovementType.SALE_PROCEEDS
                    cash_amount = tx_data["quantity"] * tx_data["price"] - tx_data.get("fees", Decimal("0.00"))
                elif tx_data["type"] == TransactionType.DIVIDEND:
                    cash_type = CashMovementType.DIVIDEND_INCOME
                    cash_amount = tx_data["price"] - tx_data.get("taxes", Decimal("0.00"))
                elif tx_data["type"] == TransactionType.INTEREST:
                    cash_type = CashMovementType.INTEREST_INCOME
                    cash_amount = tx_data["price"]
                elif tx_data["type"] == TransactionType.FEE:
                    cash_type = CashMovementType.FEE
                    cash_amount = tx_data["price"]
                elif tx_data["type"] == TransactionType.TAX:
                    cash_type = CashMovementType.TAX
                    cash_amount = tx_data["price"]

                if cash_type:
                    cash_mov = CashMovement(
                        cash_account_id=cash_account.id,
                        type=cash_type,
                        amount=cash_amount,
                        trade_date=date.today() - timedelta(days=tx_data["days_ago"]),
                    )
                    session.add(cash_mov)
                    session.flush()  # Get cash_movement ID
                    cash_movement_id = cash_mov.id

        # Now create Transaction with cash_movement_id already set
        tx = Transaction(
            asset_id=tx_data["asset"].id,
            broker_id=tx_data["broker"].id,
            type=tx_data["type"],
            quantity=tx_data["quantity"],
            price=tx_data["price"],
            currency=tx_data["currency"],
            cash_movement_id=cash_movement_id,  # Set from CashMovement created above
            trade_date=date.today() - timedelta(days=tx_data["days_ago"]),
            note=tx_data["note"],
        )
        session.add(tx)
        session.flush()  # Get transaction ID

        tx_type_emoji = {
            TransactionType.BUY: "🛒",
            TransactionType.SELL: "💰",
            TransactionType.DIVIDEND: "💵",
            TransactionType.INTEREST: "📈",
        }.get(tx_data["type"], "📊")

        print(f"  {tx_type_emoji} {tx_data['type'].value}: {tx_data['asset'].identifier} "
              f"(qty: {tx_data['quantity']}, price: {tx_data['price']} {tx_data['currency']})")

    session.commit()


def populate_price_history(session: Session):
    """Create price history for market-priced assets."""
    print("\n📈 Creating Price History...")
    print("-" * 60)

    assets_with_prices = [
        ("AAPL", Decimal("175.00"), Decimal("0.50")),  # base price, daily change
        ("MSFT", Decimal("380.00"), Decimal("1.20")),
        ("TSLA", Decimal("242.00"), Decimal("2.50")),
        ("VWCE", Decimal("95.00"), Decimal("0.30")),
        ("CSPX", Decimal("485.00"), Decimal("0.80")),
        ]

    for identifier, base_price, daily_change in assets_with_prices:
        asset = session.exec(select(Asset).where(Asset.identifier == identifier)).first()
        if not asset:
            continue

        # Create 7 days of price history
        for i in range(7):
            price_date = date.today() - timedelta(days=i)
            day_price = base_price + (daily_change * Decimal(str(i)))

            price = PriceHistory(
                asset_id=asset.id,
                date=price_date,
                open=day_price - Decimal("0.50"),
                high=day_price + Decimal("1.00"),
                low=day_price - Decimal("0.75"),
                close=day_price,
                adjusted_close=day_price,
                currency=asset.currency,
                source_plugin_key="yfinance",
                )
            session.add(price)

        print(f"  ✅ {identifier}: 7 days of prices")

    session.commit()


def populate_fx_rates(session: Session):
    """Create FX rates for currency conversion."""
    print("\n💱 Creating FX Rates...")
    print("-" * 60)

    # Realistic base rates for different currencies (as of 2025)
    # Format: 1 base = rate * quote (alphabetically ordered)
    currencies_rates = [
        ("EUR", "USD", Decimal("1.0850")),  # 1 EUR = 1.0850 USD
        ("EUR", "GBP", Decimal("0.8520")),  # 1 EUR = 0.8520 GBP
        ("CHF", "EUR", Decimal("1.0650")),  # 1 CHF = 1.0650 EUR (inverted storage)
        ("EUR", "JPY", Decimal("163.45")),  # 1 EUR = 163.45 JPY
        ]

    # Create 30 days of rates with small daily variations
    for base, quote, base_rate in currencies_rates:
        for i in range(30):
            rate_date = date.today() - timedelta(days=i)

            # Simulate realistic daily variation (±0.5%)
            variation = (i % 7 - 3) * Decimal("0.005")  # Oscillates between -0.015 and +0.015
            rate = base_rate * (Decimal("1") + variation)

            fx = FxRate(
                date=rate_date,
                base=base,
                quote=quote,
                rate=rate,
                source="ECB",
                )
            session.add(fx)

        print(f"  ✅ {base}/{quote}: 30 days of rates (base: {base_rate})")

    session.commit()


def populate_fx_currency_pair_sources(session: Session):
    """
    Create default FX provider configuration.

    By default, ECB is used for all EUR/* pairs since it's the only provider
    currently implemented. When new providers (FED, BOE, etc.) are added,
    this function should be updated to assign appropriate providers.
    """
    print("\n🔧 Creating FX Provider Configuration...")
    print("-" * 60)

    # Get all registered providers
    try:
        available_providers = FXProviderRegistry.list_providers()
        if not available_providers:
            print("  ⚠️  No FX providers registered - skipping configuration")
            return
    except Exception as e:
        print(f"  ⚠️  Could not load providers: {e}")
        return

    # For now, we only have ECB, so configure all EUR/* pairs with ECB
    # In the future, when FED/BOE are added, update this logic

    # Get ECB provider info
    ecb_provider = next((p for p in available_providers if p['code'] == 'ECB'), None)
    if not ecb_provider:
        print("  ⚠️  ECB provider not found - skipping configuration")
        return

    # Common currency pairs that ECB should handle
    # These match the test currencies from ECBProvider
    eur_pairs = [
        ("EUR", "USD"),  # Euro / US Dollar
        ("EUR", "GBP"),  # Euro / British Pound
        ("CHF", "EUR"),  # Swiss Franc / Euro (inverted)
        ("EUR", "JPY"),  # Euro / Japanese Yen
        ("CAD", "EUR"),  # Canadian Dollar / Euro (inverted)
        ("AUD", "EUR"),  # Australian Dollar / Euro (inverted)
        ]

    for base, quote in eur_pairs:
        pair_source = FxCurrencyPairSource(
            base=base,
            quote=quote,
            provider_code="ECB",
            priority=1  # Primary source
            )
        session.add(pair_source)
        print(f"  ✅ {base}/{quote} → ECB (priority=1)")

    session.commit()
    print(f"\n  📊 Configured {len(eur_pairs)} currency pairs with ECB as provider")


def check_existing_data(session: Session) -> tuple[bool, dict]:
    """Check if database already contains data.

    Returns:
        Tuple of (has_data, counts_dict)
    """
    counts = {
        'brokers': len(session.exec(select(Broker)).all()),
        'assets': len(session.exec(select(Asset)).all()),
        'asset_providers': len(session.exec(select(AssetProviderAssignment)).all()),
        'transactions': len(session.exec(select(Transaction)).all()),
        'cash_accounts': len(session.exec(select(CashAccount)).all()),
        'cash_movements': len(session.exec(select(CashMovement)).all()),
        'price_history': len(session.exec(select(PriceHistory)).all()),
        'fx_rates': len(session.exec(select(FxRate)).all()),
        'fx_pair_sources': len(session.exec(select(FxCurrencyPairSource)).all()),
        }

    has_data = any(count > 0 for count in counts.values())
    return has_data, counts


def main():
    """Populate database with mock data for testing."""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Populate database with mock data')
    parser.add_argument('--force', action='store_true',
                        help='Delete existing database and create fresh one')
    args = parser.parse_args()

    print("=" * 60)
    print("LibreFolio Database - Mock Data Population")
    print("=" * 60)
    print("\n⚠️  Populating database with MOCK DATA for testing...")
    print("This data is for development/testing purposes only.\n")

    settings = get_settings()
    # Extract path from sqlite URL
    # Note: setup_test_database() already set DATABASE_URL to TEST_DATABASE_URL
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite:///'):
        db_path = Path(db_url.replace('sqlite:///', ''))
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
    else:
        print("❌ Error: This script only works with SQLite databases")
        return 1

    # Check if database file exists
    if db_path.exists() and db_path.stat().st_size > 0:
        # Database exists and is not empty
        if args.force:
            print(f"⚠️  Database file exists: {db_path}")
            print(f"     Size: {db_path.stat().st_size} bytes")
            print(f"\n🗑️  --force flag detected: Deleting database file...")

            # Delete the database file
            db_path.unlink()
            print(f"  ✅ Database deleted\n")
        else:
            print(f"❌ Error: Database file already exists!")
            print(f"     Path: {db_path}")
            print(f"     Size: {db_path.stat().st_size} bytes")
            print(f"\n💡 Solutions:")
            print(f"  1. Use --force flag to delete and recreate:")
            print(f"     python -m backend.test_scripts.test_db.populate_mock_data --force")
            print(f"  2. Delete database manually:")
            print(f"     rm {db_path}")
            print(f"  3. Use test_runner.py with --force:")
            print(f"     python test_runner.py db populate --force")
            return 1

    # Create fresh database with safety checks
    print("\n🔧 Initializing database...")
    if not initialize_test_database():
        return 1
    print()

    with Session(engine) as session:
        try:
            # Clean up any existing data (migrations might have created some)
            cleanup_all_tables(session)

            populate_brokers(session)
            populate_assets(session)
            populate_asset_provider_assignments(session)
            populate_cash_accounts(session)
            populate_deposits(session)
            populate_transactions_and_cash(session)
            populate_price_history(session)
            populate_fx_rates(session)
            populate_fx_currency_pair_sources(session)

            # ✅ CRITICAL: Final commit to persist all data
            print("\n💾 Committing all data to database...")
            session.commit()
            print("✅ Data committed successfully")

            print("\n" + "=" * 60)
            print("✅ Mock data population completed successfully!")
            print("=" * 60)

            # Verify data persistence by re-querying
            print("\n🔍 Verifying data persistence...")
            counts = {
                'brokers': len(session.exec(select(Broker)).all()),
                'assets': len(session.exec(select(Asset)).all()),
                'asset_providers': len(session.exec(select(AssetProviderAssignment)).all()),
                'cash_accounts': len(session.exec(select(CashAccount)).all()),
                'cash_movements': len(session.exec(select(CashMovement)).all()),
                'transactions': len(session.exec(select(Transaction)).all()),
                'price_history': len(session.exec(select(PriceHistory)).all()),
                'fx_rates': len(session.exec(select(FxRate)).all()),
                'fx_pair_sources': len(session.exec(select(FxCurrencyPairSource)).all()),
                }

            # Print summary
            print("\n📊 Summary:")
            print(f"  • {counts['brokers']} brokers")
            print(f"  • {counts['assets']} assets")
            print(f"  • {counts['asset_providers']} asset provider assignments")
            print(f"  • {counts['cash_accounts']} cash accounts")
            print(f"  • {counts['transactions']} transactions")
            print(f"  • {counts['cash_movements']} cash movements")
            print(f"  • {counts['price_history']} price history records")
            print(f"  • {counts['fx_rates']} FX rates")
            print(f"  • {counts['fx_pair_sources']} FX pair sources")

            # Verify at least some data was created
            total_records = sum(counts.values())
            if total_records == 0:
                print("\n❌ WARNING: No data found in database after population!")
                print("   This indicates a commit issue or data creation problem.")
                return 1

            print(f"\n✅ Total records: {total_records}")

            # Print sample queries for manual verification
            print(f"\n💡 Verify data in database ({db_path}):")
            print("\n" + "=" * 60)
            print("Sample SQL Queries for Manual Verification")
            print("=" * 60)
            print("\n# View brokers")
            print("SELECT * FROM brokers LIMIT 5;")
            print("\n# View assets")
            print("SELECT id, display_name, identifier, currency, asset_type, valuation_model FROM assets LIMIT 5;")
            print("\n# View asset provider assignments")
            print("SELECT a.identifier, apa.provider_code, apa.provider_params")
            print("FROM asset_provider_assignments apa")
            print("JOIN assets a ON apa.asset_id = a.id;")
            print("\n# View cash accounts")
            print("SELECT ca.id, b.name as broker, ca.currency, ca.display_name")
            print("FROM cash_accounts ca JOIN brokers b ON ca.broker_id = b.id;")
            print("\n# View transactions")
            print("SELECT t.id, t.transaction_type, a.identifier, t.quantity, t.price, t.transaction_date")
            print("FROM transactions t JOIN assets a ON t.asset_id = a.id")
            print("LIMIT 5;")
            print("\n# View cash movements")
            print("SELECT cm.id, cm.movement_type, cm.amount, cm.currency, cm.movement_date")
            print("FROM cash_movements cm LIMIT 5;")
            print("\n# View price history")
            print("SELECT ph.date, a.identifier, ph.close, ph.currency")
            print("FROM price_history ph JOIN assets a ON ph.asset_id = a.id")
            print("LIMIT 5;")
            print("\n# View FX rates")
            print("SELECT date, base, quote, rate, source FROM fx_rates")
            print("ORDER BY date DESC LIMIT 5;")
            print("\n# View FX pair sources")
            print("SELECT base, quote, provider_code, priority, fetch_interval FROM fx_currency_pair_sources;")
            print("\n" + "=" * 60)
            print("\n📚 See database-schema.md for explanation of all tables!")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
            return 1

    # ========================================================================
    # FINAL VERIFICATION: Independent connection to verify data persistence
    # ========================================================================
    print("\n" + "=" * 60)
    print("🔍 FINAL VERIFICATION: Data Persistence Check")
    print("=" * 60)
    print("ℹ️  Creating independent SQLite connection to verify data was saved...")

    import sqlite3
    try:
        # Get database path from settings
        # Note: setup_test_database() already set DATABASE_URL to TEST_DATABASE_URL at script start
        verification_settings = get_settings()
        verification_db_url = verification_settings.DATABASE_URL

        if not verification_db_url.startswith('sqlite:///'):
            print(f"❌ ERROR: Only SQLite databases are supported for verification")
            return 1

        test_db_path = Path(verification_db_url.replace('sqlite:///', ''))
        if not test_db_path.is_absolute():
            test_db_path = Path.cwd() / test_db_path

        if not test_db_path.exists():
            print(f"❌ ERROR: Test database file not found: {test_db_path}")
            return 1

        print(f"ℹ️  Database path: {test_db_path}")
        print(f"ℹ️  Database size: {test_db_path.stat().st_size} bytes")

        # Create independent connection
        conn = sqlite3.connect(str(test_db_path))
        cursor = conn.cursor()

        # Verify each table has data
        tables_to_check = [
            ('brokers', 'name'),
            ('assets', 'identifier'),
            ('asset_provider_assignments', 'provider_code'),
            ('cash_accounts', 'display_name'),
            ('transactions', 'type'),
            ('cash_movements', 'type'),
            ('price_history', 'close'),
            ('fx_rates', 'rate'),
            ('fx_currency_pair_sources', 'provider_code'),
            ]

        print("\n📊 Verifying data in each table:")
        verification_failed = False

        for table_name, sample_column in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]

                if count > 0:
                    # Get sample data
                    cursor.execute(f"SELECT {sample_column} FROM {table_name} LIMIT 3")
                    samples = [row[0] for row in cursor.fetchall()]
                    samples_str = ", ".join(str(s)[:30] for s in samples)
                    print(f"  ✅ {table_name}: {count} records (sample: {samples_str})")
                else:
                    print(f"  ❌ {table_name}: 0 records - DATA NOT SAVED!")
                    verification_failed = True

            except sqlite3.Error as e:
                print(f"  ❌ {table_name}: Query failed - {e}")
                verification_failed = True

        conn.close()

        if verification_failed:
            print("\n" + "=" * 60)
            print("❌ VERIFICATION FAILED: Some tables have no data!")
            print("=" * 60)
            print("\n💡 Possible causes:")
            print("  1. Session.commit() not called properly")
            print("  2. Database file path mismatch")
            print("  3. Transaction rolled back due to error")
            print("  4. Using wrong database (prod instead of test)")
            return 1

        print("\n" + "=" * 60)
        print("✅ VERIFICATION PASSED: All tables have data!")
        print("=" * 60)
        print("\n🎉 Mock data population completed and verified successfully!")

        return 0

    except Exception as e:
        print(f"\n❌ Verification error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
