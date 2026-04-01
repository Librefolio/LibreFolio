"""
Database module exports.
"""

from backend.app.db.base import (
    SQLModel,
    # Enums
    IdentifierType,
    AssetType,
    AssetEventType,
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
    AssetEvent,
    FxRate,
    FxConversionRoute,
    AssetProviderAssignment,
    )
from backend.app.db.session import get_sync_engine, get_async_engine, get_session_generator

__all__ = [
    "SQLModel",
    "get_sync_engine",  # For sync scripts (migrations, populate, checks)
    "get_async_engine",  # For async FastAPI app
    "get_session_generator",
    # Enums
    "IdentifierType",
    "AssetType",
    "AssetEventType",
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
    "AssetEvent",
    "FxRate",
    "FxConversionRoute",
    "AssetProviderAssignment",
    ]
