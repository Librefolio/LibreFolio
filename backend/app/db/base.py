"""
Database base module.
SQLModel base classes and metadata.
Import all models here so Alembic can detect them.
"""
from sqlmodel import SQLModel

# Import all models so Alembic can detect them
from backend.app.db.models import (
    # Enums
    IdentifierType,
    AssetType,
    TransactionType,
    UserRole,
    # Models
    User,
    UserSettings,
    Broker,
    BrokerUserAccess,
    Asset,
    Transaction,
    PriceHistory,
    FxRate,
    FxCurrencyPairSource,
    AssetProviderAssignment,
    )

__all__ = [
    "SQLModel",
    # Enums
    "IdentifierType",
    "AssetType",
    "TransactionType",
    "UserRole",
    # Models
    "User",
    "UserSettings",
    "Broker",
    "BrokerUserAccess",
    "Asset",
    "Transaction",
    "PriceHistory",
    "FxRate",
    "FxCurrencyPairSource",
    "AssetProviderAssignment",
    ]
