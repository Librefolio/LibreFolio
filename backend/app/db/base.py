"""
Database base module.
SQLModel base classes and metadata.
Import all models here so Alembic can detect them.
"""

from sqlmodel import SQLModel

# Import all models so Alembic can detect them
from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetEventType,
    AssetProviderAssignment,
    AssetType,
    Broker,
    BrokerUserAccess,
    FxConversionRoute,
    FxRate,
    # Enums
    IdentifierType,
    PriceHistory,
    ProviderInputType,
    Transaction,
    TransactionType,
    # Models
    User,
    UserRole,
    UserSettings,
)

__all__ = [  # noqa: RUF022 — grouped by domain with section comments; sorting would scatter related names
    "SQLModel",
    # Enums
    "IdentifierType",
    "AssetType",
    "AssetEventType",
    "TransactionType",
    "UserRole",
    "ProviderInputType",
    # Models
    "User",
    "UserSettings",
    "Broker",
    "BrokerUserAccess",
    "Asset",
    "Transaction",
    "PriceHistory",
    "AssetEvent",
    "FxRate",
    "FxConversionRoute",
    "AssetProviderAssignment",
]
