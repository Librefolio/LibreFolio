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
    ValuationModel,
    TransactionType,
    CashMovementType,
    PayloadType,
    # Models
    Broker,
    Asset,
    Transaction,
    PriceHistory,
    PriceRawPayload,
    FxRate,
    CashAccount,
    CashMovement,
)

__all__ = [
    "SQLModel",
    # Enums
    "IdentifierType",
    "AssetType",
    "ValuationModel",
    "TransactionType",
    "CashMovementType",
    "PayloadType",
    # Models
    "Broker",
    "Asset",
    "Transaction",
    "PriceHistory",
    "PriceRawPayload",
    "FxRate",
    "CashAccount",
    "CashMovement",
]

